from __future__ import annotations
from typing import Any
import uuid
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.common import AuthRequest, CustomerCreate, CustomerResponse, PredictionRequest, PredictionResponse, SignupRequest, TrainRequest
from app.services import local_auth
from app.services.store import store

app = FastAPI(title=settings.app_name, version="0.1.0", description="Customer churn prediction API — implementation slice")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def public_customer(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k != "email"}

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "churn-api", "version": app.version, "mode": "demo-in-memory"}

@app.post("/api/auth/signup", status_code=201)
def signup(payload: SignupRequest):
    try:
        user = local_auth.signup(payload.email, payload.password, payload.display_name)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": "EMAIL_EXISTS", "message": str(exc)}) from exc
    return {"access_token": local_auth.create_session(user), "token_type": "bearer", "user": user}

@app.post("/api/auth/login")
def login(payload: AuthRequest):
    user = local_auth.login(payload.email, payload.password)
    if user is None:
        raise HTTPException(401, detail={"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect"})
    return {"access_token": local_auth.create_session(user), "token_type": "bearer", "user": user}

@app.get("/api/auth/me")
def auth_me(authorization: str | None = Header(default=None)):
    token = authorization.split(" ", 1)[1] if authorization and authorization.lower().startswith("bearer ") else None
    user = local_auth.get_session(token)
    if user is None:
        raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "Please sign in"})
    return {"user": user}

@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = authorization.split(" ", 1)[1] if authorization and authorization.lower().startswith("bearer ") else None
    local_auth.delete_session(token)
    return {"success": True}

@app.get("/api/dashboard/summary")
def dashboard_summary():
    results = list(store.predictions.values())
    counts = {level: sum(1 for x in results if x["risk_level"] == level) for level in ["low", "medium", "high"]}
    return {"customer_count": len(store.customers), "dataset_count": len(store.datasets), "prediction_count": len(results), "high_risk_count": counts["high"], "medium_risk_count": counts["medium"], "low_risk_count": counts["low"], "predicted_churn_rate": sum(1 for x in results if x["prediction"]) / len(results) if results else 0, "average_probability": sum(x["probability"] for x in results) / len(results) if results else 0, "active_model": {"id": store.model.model_id, "version": store.model.version, "metrics": store.model.metrics}, "recent_predictions": sorted(results, key=lambda x: x["created_at"], reverse=True)[:6]}

@app.get("/api/customers")
def list_customers(search: str | None = None, limit: int = 50):
    items = list(store.customers.values())
    if search: items = [x for x in items if search.lower() in x["external_customer_id"].lower() or search.lower() in (x["name"] or "").lower()]
    return {"items": [public_customer(x) for x in items[: min(limit, 100)]], "total": len(items)}

@app.post("/api/customers", response_model=CustomerResponse, status_code=201)
def create_customer(payload: CustomerCreate):
    if any(x["external_customer_id"] == payload.external_customer_id for x in store.customers.values()): raise HTTPException(409, detail={"code": "DUPLICATE_CUSTOMER", "message": "Customer ID already exists"})
    return store.create_customer(payload.external_customer_id, payload.name, payload.features)

@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str):
    if customer_id not in store.customers: raise HTTPException(404, detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found"})
    return public_customer(store.customers[customer_id])

@app.get("/api/datasets")
def list_datasets():
    return {"items": [{k: v for k, v in x.items() if k != "frame"} for x in store.datasets.values()], "total": len(store.datasets)}

@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...), target_column: str | None = None):
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(400, detail={"code": "UNSUPPORTED_FILE_FORMAT", "message": "Only CSV files are supported"})
    content = await file.read()
    try: result = store.upload_dataset(file.filename, content, target_column)
    except Exception as exc: raise HTTPException(422, detail={"code": "INVALID_DATASET", "message": str(exc)}) from exc
    return {k: v for k, v in result.items() if k != "frame"}

@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    if dataset_id not in store.datasets: raise HTTPException(404, detail={"code": "DATASET_NOT_FOUND", "message": "Dataset not found"})
    return {k: v for k, v in store.datasets[dataset_id].items() if k != "frame"}

@app.get("/api/datasets/{dataset_id}/preview")
def preview_dataset(dataset_id: str, limit: int = 10):
    dataset = store.datasets.get(dataset_id)
    if not dataset:
        raise HTTPException(404, detail={"code": "DATASET_NOT_FOUND", "message": "Dataset not found"})
    frame = dataset["frame"].head(min(max(limit, 1), 50)).fillna("")
    return {"id": dataset_id, "columns": list(frame.columns), "rows": frame.to_dict(orient="records"), "validation_summary": dataset["validation_summary"]}

@app.delete("/api/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str):
    if dataset_id not in store.datasets:
        raise HTTPException(404, detail={"code": "DATASET_NOT_FOUND", "message": "Dataset not found"})
    del store.datasets[dataset_id]
    return None

@app.post("/api/models/train")
def train_model(payload: TrainRequest):
    dataset = store.datasets.get(payload.dataset_id)
    if not dataset: raise HTTPException(404, detail={"code": "DATASET_NOT_FOUND", "message": "Dataset not found"})
    if dataset["status"] == "failed": raise HTTPException(422, detail={"code": "INVALID_DATASET", "message": "Dataset validation failed"})
    from app.ml.pipeline import train_model as train
    try: store.model = train(dataset["frame"], payload.target_column, payload.random_seed)
    except ValueError as exc: raise HTTPException(422, detail={"code": "TRAINING_FAILED", "message": str(exc)}) from exc
    run_id = str(uuid.uuid4())
    store.training_runs[run_id] = {"id": run_id, "dataset_id": payload.dataset_id, "status": "succeeded", "model_id": store.model.model_id, "metrics": store.model.metrics}
    return {"training_run_id": run_id, "status": "succeeded", "model_id": store.model.model_id, "model_version": store.model.version, "metrics": store.model.metrics}

@app.get("/api/models")
def list_models():
    return {"items": [{"id": store.model.model_id, "version": store.model.version, "algorithm": "logistic_regression", "status": "active", "is_active": True, "metrics": store.model.metrics}], "total": 1}

@app.get("/api/models/{model_id}")
def get_model(model_id: str):
    if model_id != store.model.model_id: raise HTTPException(404, detail={"code": "MODEL_NOT_FOUND", "message": "Model not found"})
    return {"id": store.model.model_id, "version": store.model.version, "algorithm": "logistic_regression", "status": "active", "metrics": store.model.metrics, "feature_schema": store.model.feature_columns}

@app.post("/api/predict", response_model=PredictionResponse, status_code=201)
def predict_customer(payload: PredictionRequest):
    customer_id = payload.customer_id
    features = payload.features
    if customer_id:
        customer = store.customers.get(customer_id)
        if not customer: raise HTTPException(404, detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found"})
        features = customer["features"]
    if not features: raise HTTPException(422, detail={"code": "INVALID_CUSTOMER_FEATURES", "message": "Provide customer_id or features"})
    return store.predict_for(features, customer_id)

@app.get("/api/predictions")
def list_predictions(limit: int = 50, risk_level: str | None = None):
    items = list(store.predictions.values())
    if risk_level: items = [x for x in items if x["risk_level"] == risk_level]
    return {"items": sorted(items, key=lambda x: x["created_at"], reverse=True)[: min(limit, 100)], "total": len(items)}

@app.get("/api/predictions/{prediction_id}")
def get_prediction(prediction_id: str):
    if prediction_id not in store.predictions: raise HTTPException(404, detail={"code": "PREDICTION_NOT_FOUND", "message": "Prediction not found"})
    return store.predictions[prediction_id]

@app.get("/api/analytics/churn")
def churn_analytics():
    summary = dashboard_summary()
    return {"total_predictions": summary["prediction_count"], "predicted_churn": sum(1 for x in store.predictions.values() if x["prediction"]), "risk_distribution": {level: summary[f"{level}_risk_count"] for level in ["low", "medium", "high"]}, "series": []}

@app.get("/api/analytics/features")
def feature_analytics():
    counts: dict[str, dict[str, Any]] = {}
    for prediction in store.predictions.values():
        for factor in prediction["important_factors"]:
            item = counts.setdefault(factor["feature_name"], {"feature_name": factor["feature_name"], "display_name": factor["display_name"], "occurrences": 0, "avg_absolute_impact": 0.0})
            item["occurrences"] += 1
            item["avg_absolute_impact"] += abs(factor["impact"])
    for item in counts.values(): item["avg_absolute_impact"] /= item["occurrences"]
    return {"items": sorted(counts.values(), key=lambda x: x["occurrences"], reverse=True)}

@app.get("/api/training-runs")
def training_runs():
    return {"items": list(store.training_runs.values()), "total": len(store.training_runs)}
