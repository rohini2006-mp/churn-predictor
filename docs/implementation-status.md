# Implementation status — 0.1.0

## Implemented

- FastAPI health endpoint
- Demo in-memory store
- Logistic Regression pipeline trained on the real Telco Customer Churn dataset (see `prepare_telco.py`)
- Model-based factor explanations (weight x deviation from the average customer)
- CSV validation/upload endpoint
- Customer list/create/detail endpoints
- Single prediction endpoint
- Prediction history endpoint
- Dashboard summary and factor analytics endpoints
- React dashboard shell
- Responsive customer workspace
- Recharts risk and factor charts
- Backend pytest smoke tests
- Frontend production build

## Deliberate demo-mode limitations

- No Supabase Auth/JWT verification yet
- No PostgreSQL/SQLAlchemy persistence yet
- No RLS yet
- No private Storage yet
- No SHAP library yet; factors use logistic regression weights directly, which is exact for this model type but would not carry over to tree models
- No XGBoost/Random Forest comparison yet

## Next slice

Replace `app.services.store.DemoStore` with repositories backed by the database schema, then add authentication and model artifact persistence without changing the API contracts.
