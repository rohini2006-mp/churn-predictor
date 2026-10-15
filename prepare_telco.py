"""Turn the raw Kaggle "Telco Customer Churn" CSV into the cleaned file the app trains on.

How to use:
  1. Download the dataset from Kaggle (search "Telco Customer Churn").
  2. Save the CSV as  data/raw/telco_raw.csv  inside this project folder.
  3. Run:  python prepare_telco.py
  4. The cleaned file is written to  data/telco_clean.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "data" / "raw" / "telco_raw.csv"
CLEAN_PATH = ROOT / "data" / "telco_clean.csv"

# 1. Our app's column names  <-  the names used in the Telco file
RENAME = {
    "customerID": "customer_id",
    "MonthlyCharges": "monthly_charges",
    "TotalCharges": "total_charges",
    "Contract": "contract",
    "InternetService": "internet_service",
    "PaymentMethod": "payment_method",
    "PhoneService": "phone_service",
    "OnlineSecurity": "online_security",
    "TechSupport": "tech_support",
    "Churn": "churn",
}

# 2. Our app's wording  <-  the wording used in the Telco file
YES_NO = {"Yes": "yes", "No": "no"}
YES_NO_NOINTERNET = {"Yes": "yes", "No": "no", "No internet service": "no_internet_service"}
VALUE_MAPS = {
    "contract": {"Month-to-month": "month-to-month", "One year": "one_year", "Two year": "two_year"},
    "internet_service": {"DSL": "dsl", "Fiber optic": "fiber_optic", "No": "none"},
    "payment_method": {
        "Electronic check": "electronic_check",
        "Mailed check": "mailed_check",
        "Bank transfer (automatic)": "bank_transfer",
        "Credit card (automatic)": "credit_card",
    },
    "phone_service": YES_NO,
    "online_security": YES_NO_NOINTERNET,
    "tech_support": YES_NO_NOINTERNET,
    "churn": YES_NO,
}

KEEP = [
    "customer_id", "tenure", "monthly_charges", "total_charges",
    "contract", "internet_service", "payment_method",
    "phone_service", "online_security", "tech_support", "churn",
]


def main() -> None:
    if not RAW_PATH.exists():
        raise SystemExit(
            f"Could not find {RAW_PATH}\n"
            "Download the Telco Customer Churn CSV from Kaggle and save it there first."
        )

    df = pd.read_csv(RAW_PATH).rename(columns=RENAME)

    missing_columns = [c for c in KEEP if c not in df.columns]
    if missing_columns:
        raise SystemExit(f"The raw file is missing these columns: {missing_columns}")

    # TotalCharges has a few blank cells saved as text. Those customers are brand new
    # (tenure 0), so they have been charged nothing yet.
    df["total_charges"] = pd.to_numeric(df["total_charges"], errors="coerce").fillna(0)

    df = df[KEEP].copy()

    for column, mapping in VALUE_MAPS.items():
        original = df[column]
        df[column] = original.map(mapping)
        unknown = sorted(original[df[column].isna()].dropna().unique())
        if unknown:
            raise SystemExit(f"Column '{column}' has values this script does not know about: {unknown}")

    print("Missing values per column (every number should be 0):")
    print(df.isna().sum().to_string())

    df.to_csv(CLEAN_PATH, index=False)
    print(f"\nSaved {CLEAN_PATH.relative_to(ROOT)} with {len(df)} rows and {df.shape[1]} columns")
    print("Churn counts:")
    print(df["churn"].value_counts().to_string())


if __name__ == "__main__":
    main()
