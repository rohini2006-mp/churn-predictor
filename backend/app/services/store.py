from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import io
import uuid
import pandas as pd
from pathlib import Path
from app.ml.pipeline import train_model, predict, validate_csv, ModelBundle

# The cleaned Telco dataset, created by running prepare_telco.py in the project folder.
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "telco_clean.csv"


def _load_training_frame() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training data not found at {DATA_PATH}. Download the Telco Customer Churn CSV from Kaggle, "
            "save it as data/raw/telco_raw.csv, then run `python prepare_telco.py` from the project folder."
        )
    return pd.read_csv(DATA_PATH)

class DemoStore:
    def __init__(self):
        self.customers: dict[str, dict[str, Any]] = {}
        self.datasets: dict[str, dict[str, Any]] = {}
        self.predictions: dict[str, dict[str, Any]] = {}
        self.training_runs: dict[str, dict[str, Any]] = {}
        self.model: ModelBundle = train_model(_load_training_frame())
        self._seed_customers()

    def _seed_customers(self):
        seed = [
            ("CUS-10042", "Jordan Lee", {"tenure": 8, "contract": "month-to-month", "monthly_charges": 94, "total_charges": 752, "internet_service": "fiber_optic", "payment_method": "electronic_check", "phone_service": "yes", "online_security": "no", "tech_support": "no"}),
            ("CUS-10043", "Maya Singh", {"tenure": 48, "contract": "two_year", "monthly_charges": 58, "total_charges": 2784, "internet_service": "dsl", "payment_method": "bank_transfer", "phone_service": "yes", "online_security": "yes", "tech_support": "yes"}),
            ("CUS-10044", "Eli Carter", {"tenure": 21, "contract": "one_year", "monthly_charges": 72, "total_charges": 1512, "internet_service": "fiber_optic", "payment_method": "credit_card", "phone_service": "yes", "online_security": "no", "tech_support": "yes"}),
            ("CUS-10045", "Noah Kim", {"tenure": 3, "contract": "month-to-month", "monthly_charges": 112, "total_charges": 336, "internet_service": "fiber_optic", "payment_method": "electronic_check", "phone_service": "yes", "online_security": "no", "tech_support": "no"}),
            ("CUS-10046", "Ana Silva", {"tenure": 61, "contract": "two_year", "monthly_charges": 44, "total_charges": 2684, "internet_service": "none", "payment_method": "bank_transfer", "phone_service": "yes", "online_security": "no_internet_service", "tech_support": "no_internet_service"}),
            ("CUS-10047", "Sam Patel", {"tenure": 15, "contract": "month-to-month", "monthly_charges": 86, "total_charges": 1290, "internet_service": "dsl", "payment_method": "credit_card", "phone_service": "yes", "online_security": "no", "tech_support": "no"}),
        ]
        for external_id, name, features in seed:
            self.create_customer(external_id, name, features)

    def create_customer(self, external_id: str, name: str | None, features: dict[str, Any]):
        customer_id = str(uuid.uuid4())
        item = {"id": customer_id, "external_customer_id": external_id, "name": name, "email": None, "features": features, "created_at": datetime.now(timezone.utc).isoformat(), "last_prediction": None}
        self.customers[customer_id] = item
        return item

    def predict_for(self, features: dict[str, Any], customer_id: str | None = None):
        prediction, probability, risk, factors = predict(self.model, features)
        prediction_id = str(uuid.uuid4())
        result = {"prediction": prediction, "probability": probability, "risk_level": risk, "important_factors": factors, "model_version": self.model.version, "prediction_id": prediction_id, "customer_id": customer_id, "created_at": datetime.now(timezone.utc).isoformat()}
        self.predictions[prediction_id] = result
        if customer_id in self.customers:
            self.customers[customer_id]["last_prediction"] = result
        return result

    def upload_dataset(self, name: str, content: bytes, target_column: str | None):
        if len(content) > 10 * 1024 * 1024: raise ValueError("File is too large")
        frame = pd.read_csv(io.BytesIO(content))
        report = validate_csv(frame, training=bool(target_column))
        dataset_id = str(uuid.uuid4())
        self.datasets[dataset_id] = {"id": dataset_id, "name": name, "status": "validated" if not report["errors"] else "failed", "row_count": report["row_count"], "columns": list(frame.columns), "validation_summary": report, "target_column": target_column, "frame": frame}
        return self.datasets[dataset_id]

store = DemoStore()
