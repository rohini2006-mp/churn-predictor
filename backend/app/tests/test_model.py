"""Tests for the trained model and its explanations. Needs data/telco_clean.csv (run prepare_telco.py first)."""
from app.services.store import store


def _result(name: str):
    customer = next(c for c in store.customers.values() if c["name"] == name)
    return store.predict_for(customer["features"], customer["id"])


def test_factors_are_ranked_and_labelled():
    factors = _result("Jordan Lee")["important_factors"]
    assert 1 <= len(factors) <= 5
    assert [f["rank"] for f in factors] == list(range(1, len(factors) + 1))
    assert all(f["direction"] in {"increases_risk", "decreases_risk"} for f in factors)
    assert [f["impact"] for f in factors] == sorted((f["impact"] for f in factors), reverse=True)


def test_short_monthly_contract_is_riskier_than_long_two_year_contract():
    assert _result("Noah Kim")["probability"] > _result("Maya Singh")["probability"]


def test_model_reports_real_metrics():
    assert 0.5 < store.model.metrics["roc_auc"] <= 1.0
