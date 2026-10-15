from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Customer Churn Prediction API")
    environment: str = os.getenv("ENVIRONMENT", "development")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

settings = Settings()
