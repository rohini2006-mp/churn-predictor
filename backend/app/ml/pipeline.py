from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib
import uuid
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split

NUMERIC = ["tenure", "monthly_charges", "total_charges", "usage", "support_tickets", "complaints", "satisfaction_score"]
CATEGORICAL = ["contract", "internet_service", "payment_method", "phone_service", "online_security", "tech_support"]
DISPLAY_NAMES = {
    "tenure": "Tenure",
    "monthly_charges": "Monthly charges",
    "total_charges": "Total charges",
    "usage": "Usage",
    "support_tickets": "Support tickets",
    "complaints": "Complaints",
    "satisfaction_score": "Satisfaction score",
    "contract": "Contract type",
    "internet_service": "Internet service",
    "payment_method": "Payment method",
    "phone_service": "Phone service",
    "online_security": "Online security",
    "tech_support": "Technical support",
}

@dataclass
class ModelBundle:
    model_id: str
    version: str
    pipeline: Pipeline
    metrics: dict[str, float]
    feature_columns: list[str]
    threshold_low: float = 0.33
    threshold_high: float = 0.66
    transformed_means: np.ndarray | None = None  # average of each model input over the training rows
    owners: list[str] | None = None  # which original column each model input came from


def _make_pipeline(numeric: list[str], categorical: list[str]) -> Pipeline:
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric_pipe, numeric),
        ("categorical", categorical_pipe, categorical),
    ], remainder="drop")
    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])


def _owner(name: str, categorical: list[str]) -> str:
    """Map a model input name such as 'categorical__contract_one_year' back to the column 'contract'."""
    _, _, rest = name.partition("__")
    if name.startswith("numeric__"):
        return rest.removeprefix("missingindicator_")
    matches = [col for col in categorical if rest.startswith(col + "_")]
    return max(matches, key=len) if matches else rest


def _to_dense(matrix: Any) -> np.ndarray:
    return np.asarray(matrix.toarray() if hasattr(matrix, "toarray") else matrix)


def _explain(bundle: "ModelBundle", frame: pd.DataFrame, row: dict[str, Any]) -> list[dict[str, Any]]:
    """Real, model-based explanation for a logistic regression.

    For each model input: contribution = weight x (this customer's value - the average value).
    A positive contribution pushes this customer towards churn compared with an average customer.
    Contributions of one-hot columns (e.g. contract_one_year, contract_two_year) are added back
    together so each original column gets a single number.
    """
    preprocessor = bundle.pipeline.named_steps["preprocessor"]
    model = bundle.pipeline.named_steps["model"]
    values = _to_dense(preprocessor.transform(frame))[0]
    contributions = model.coef_[0] * (values - bundle.transformed_means)
    per_feature: dict[str, float] = {}
    for owner, contribution in zip(bundle.owners, contributions):
        per_feature[owner] = per_feature.get(owner, 0.0) + float(contribution)
    factors = []
    for key, impact in per_feature.items():
        value = row.get(key)
        if value is None or pd.isna(value) or abs(impact) < 0.01:
            continue  # the customer did not provide it, or it barely matters
        factors.append({
            "feature_name": key,
            "display_name": DISPLAY_NAMES.get(key, key),
            "impact": round(abs(impact), 4),
            "direction": "increases_risk" if impact > 0 else "decreases_risk",
            "value": str(value),
            "rank": 0,
        })
    factors.sort(key=lambda item: item["impact"], reverse=True)
    return factors[:5]


def train_model(frame: pd.DataFrame, target: str = "churn", seed: int = 42) -> ModelBundle:
    if target not in frame.columns:
        raise ValueError(f"Missing target column: {target}")
    y = frame[target].map({True: 1, False: 0, "true": 1, "false": 0, "yes": 1, "no": 0, "Yes": 1, "No": 0})
    if y.isna().any() or y.nunique() != 2:
        raise ValueError("Target must contain exactly two valid classes")
    usable_numeric = [c for c in NUMERIC if c in frame.columns]
    usable_categorical = [c for c in CATEGORICAL if c in frame.columns]
    features = usable_numeric + usable_categorical
    if not features:
        raise ValueError("No usable feature columns found")
    X = frame[features].copy()
    X_train, X_test, y_train, y_test = train_test_split(X, y.astype(int), test_size=0.2, random_state=seed, stratify=y)
    pipeline = _make_pipeline(usable_numeric, usable_categorical)
    pipeline.fit(X_train, y_train)
    preprocessor = pipeline.named_steps["preprocessor"]
    transformed_means = _to_dense(preprocessor.transform(X_train)).mean(axis=0)
    owners = [_owner(name, usable_categorical) for name in preprocessor.get_feature_names_out()]
    probs = pipeline.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_test, preds)),
        "precision": float(precision_score(y_test, preds, zero_division=0)),
        "recall": float(recall_score(y_test, preds, zero_division=0)),
        "f1": float(f1_score(y_test, preds, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probs)),
        "pr_auc": float(average_precision_score(y_test, probs)),
    }
    return ModelBundle(
        model_id=str(uuid.uuid4()),
        version="logreg-0.2.0",
        pipeline=pipeline,
        metrics=metrics,
        feature_columns=features,
        transformed_means=transformed_means,
        owners=owners,
    )


def predict(bundle: ModelBundle, features: dict[str, Any]) -> tuple[bool, float, str, list[dict[str, Any]]]:
    row = {key: features.get(key) for key in bundle.feature_columns}
    frame = pd.DataFrame([row])
    probability = float(bundle.pipeline.predict_proba(frame)[0, 1])
    prediction = probability >= 0.5
    risk = "low" if probability < bundle.threshold_low else "medium" if probability < bundle.threshold_high else "high"
    factors = _explain(bundle, frame, row)
    for index, factor in enumerate(factors, start=1): factor["rank"] = index
    if not factors:
        factors = [{"feature_name": "model_probability", "display_name": "Combined model signal", "impact": probability, "direction": "increases_risk" if prediction else "decreases_risk", "value": f"{probability:.2f}", "rank": 1}]
    return prediction, probability, risk, factors


def validate_csv(frame: pd.DataFrame, training: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if frame.empty: errors.append("Dataset is empty")
    if training and "churn" not in frame.columns: errors.append("Dataset is missing required target column: churn")
    if "customer_id" in frame.columns and frame["customer_id"].duplicated().any(): errors.append("Duplicate customer_id values detected")
    if training and "churn" in frame.columns:
        values = set(frame["churn"].dropna().astype(str).str.lower().unique())
        if not values.issubset({"true", "false", "yes", "no", "0", "1"}): errors.append("Target contains unsupported values")
        if len(values) == 2:
            counts = frame["churn"].value_counts(normalize=True)
            if counts.min() < 0.1: warnings.append("Target classes are imbalanced")
    for column in ["tenure", "monthly_charges", "total_charges", "usage", "support_tickets", "complaints"]:
        if column in frame.columns:
            numeric = pd.to_numeric(frame[column], errors="coerce")
            if numeric.isna().any() and frame[column].notna().any(): warnings.append(f"Some values in {column} are not numeric")
            if (numeric < 0).any(): errors.append(f"{column} contains impossible negative values")
    return {"status": "rejected" if errors else "accepted_with_warnings" if warnings else "accepted", "row_count": int(len(frame)), "column_count": int(len(frame.columns)), "recognized_features": [c for c in NUMERIC + CATEGORICAL if c in frame.columns], "warnings": warnings, "errors": errors, "preview": frame.head(5).fillna("").to_dict(orient="records")}
