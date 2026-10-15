from typing import Any
from pydantic import BaseModel, Field

class ErrorBody(BaseModel):
    success: bool = False
    error: dict[str, Any]

class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

class SignupRequest(AuthRequest):
    display_name: str = Field(min_length=1, max_length=160)

class CustomerCreate(BaseModel):
    external_customer_id: str = Field(min_length=1, max_length=120)
    name: str | None = Field(default=None, max_length=160)
    email: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)

class CustomerResponse(CustomerCreate):
    id: str
    created_at: str
    last_prediction: dict[str, Any] | None = None

class PredictionRequest(BaseModel):
    customer_id: str | None = None
    features: dict[str, Any] | None = None
    model_id: str | None = None

class Factor(BaseModel):
    feature_name: str
    display_name: str
    impact: float
    direction: str
    value: str | None = None
    rank: int

class PredictionResponse(BaseModel):
    prediction: bool
    probability: float
    risk_level: str
    important_factors: list[Factor]
    model_version: str
    prediction_id: str

class TrainRequest(BaseModel):
    dataset_id: str
    target_column: str = "churn"
    candidate_models: list[str] = ["logistic_regression"]
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)
    random_seed: int = 42
