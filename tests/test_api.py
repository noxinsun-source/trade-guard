from fastapi.testclient import TestClient

from app.main import create_app


def payload(**overrides):
    data = {
        "account_id": "ACC-001",
        "instrument": "600000.SH",
        "side": "BUY",
        "quantity": 100,
        "price": "10.00",
        "reference_price": "10.00",
        "current_position": 100,
        "portfolio_value": "100000",
        "daily_traded_notional": "10000",
        "idempotency_key": "order-key-0001",
    }
    data.update(overrides)
    return data


def client():
    return TestClient(create_app(":memory:"))


def test_pass_order_and_fetch_audit_record():
    with client() as api:
        response = api.post("/v1/risk/check", json=payload())
        assert response.status_code == 200
        decision = response.json()
        assert decision["status"] == "PASS"
        fetched = api.get(f"/v1/risk/decisions/{decision['decision_id']}")
        assert fetched.json() == decision


def test_rejects_short_sell_beyond_available_position():
    with client() as api:
        response = api.post(
            "/v1/risk/check",
            json=payload(side="SELL", quantity=101, idempotency_key="order-key-short"),
        )
        assert response.json()["status"] == "REJECT"
        failed = [rule["rule_code"] for rule in response.json()["rules"] if not rule["passed"]]
        assert "SELL_POSITION_CHECK" in failed


def test_rejects_extreme_price_deviation():
    with client() as api:
        response = api.post(
            "/v1/risk/check",
            json=payload(price="11.20", idempotency_key="order-key-price"),
        )
        assert response.json()["status"] == "REJECT"


def test_routes_concentration_breach_to_review():
    with client() as api:
        response = api.post(
            "/v1/risk/check",
            json=payload(
                quantity=2000,
                price="10.00",
                current_position=1000,
                portfolio_value="100000",
                idempotency_key="order-key-review",
            ),
        )
        assert response.json()["status"] == "REVIEW"


def test_idempotent_retry_returns_same_decision():
    with client() as api:
        first = api.post("/v1/risk/check", json=payload()).json()
        second = api.post("/v1/risk/check", json=payload()).json()
        assert first["decision_id"] == second["decision_id"]


def test_idempotency_key_conflict_is_rejected():
    with client() as api:
        assert api.post("/v1/risk/check", json=payload()).status_code == 200
        response = api.post("/v1/risk/check", json=payload(quantity=200))
        assert response.status_code == 409


def test_metrics_exposes_decision_counts():
    with client() as api:
        api.post("/v1/risk/check", json=payload())
        response = api.get("/metrics")
        assert response.status_code == 200
        assert 'trade_guard_decisions_total{status="PASS"} 1' in response.text
