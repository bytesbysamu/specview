"""Route-level coverage for the three billing handlers.

Stripe SDK calls are patched; the focus here is HTTP shape — auth gating,
JSON contract, status codes — not Stripe behaviour.
"""
from datetime import datetime
from unittest.mock import patch

import pytest
from flask import Flask

from modules.billing.routes import billing_bp


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("AUTH_BYPASS", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_PRO_PRICE_ID", "price_pro_x")
    flask_app = Flask(__name__)
    flask_app.testing = True
    flask_app.register_blueprint(billing_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ── POST /api/billing/create-checkout-session ───────────────────────────────


def test_create_checkout_session_returns_url(client):
    with patch(
        "modules.billing.routes.create_checkout_session",
        return_value="https://checkout.stripe.com/pay/test",
    ) as create:
        resp = client.post(
            "/api/billing/create-checkout-session",
            headers={"X-User-Id": "auth-r1", "X-User-Email": "r1@example.com"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"url": "https://checkout.stripe.com/pay/test"}
    create.assert_called_once()


def test_create_checkout_session_returns_401_without_auth(client, monkeypatch):
    # Conftest's auth bypass auto-injects a Bearer token; pass an explicit
    # empty `Authorization` header to opt out and reach the
    # @require_auth "missing bearer token" branch.
    resp = client.post(
        "/api/billing/create-checkout-session",
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "missing bearer token"}


# ── POST /api/billing/webhook ───────────────────────────────────────────────


def test_webhook_returns_200_received_true_on_valid_signature(client):
    with patch("modules.billing.routes.handle_webhook", return_value=None):
        resp = client.post(
            "/api/billing/webhook",
            data=b'{"type":"checkout.session.completed","data":{"object":{}}}',
            headers={
                "Stripe-Signature": "valid-sig",
                "Content-Type": "application/json",
            },
        )
    assert resp.status_code == 200
    assert resp.get_json() == {"received": True}


def test_webhook_returns_400_on_invalid_signature(client):
    from modules.billing.service import BillingSignatureError

    with patch(
        "modules.billing.routes.handle_webhook",
        side_effect=BillingSignatureError("bad sig"),
    ):
        resp = client.post(
            "/api/billing/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "bad-sig"},
        )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "invalid_signature"}


def test_webhook_does_not_require_auth(client, monkeypatch):
    """Stripe is the caller; webhook must NOT require a bearer token."""
    monkeypatch.delenv("AUTH_BYPASS", raising=False)
    with patch("modules.billing.routes.handle_webhook", return_value=None):
        resp = client.post(
            "/api/billing/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "ok"},
        )
    assert resp.status_code == 200


# ── GET /api/billing/status ─────────────────────────────────────────────────


def test_status_for_free_user_returns_free_plan_and_null_manage_url(client):
    resp = client.get(
        "/api/billing/status",
        headers={"X-User-Id": "free-1", "X-User-Email": "free@example.com"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["plan"] == "free"
    assert body["status"] is None
    assert body["current_period_end"] is None
    assert body["manage_url"] is None


def test_status_for_pro_user_returns_pro_plan_with_manage_url(client, db_session, make_user):
    from modules.billing.models import Subscription

    # Must match the auth_user_id injected by the conftest _auth_bypass fixture.
    user = make_user(auth_user_id="test-user", email="test@example.com")
    sub = Subscription(
        user_id=user.id,
        plan="pro",
        status="active",
        stripe_customer_id="cus_pro_1",
        stripe_subscription_id="sub_pro_1",
        current_period_end=datetime(2026, 5, 26, 12, 0, 0),
    )
    db_session.add(sub)
    db_session.commit()

    with patch(
        "modules.billing.routes.create_portal_session",
        return_value="https://billing.stripe.com/p/session/abc",
    ) as portal:
        resp = client.get("/api/billing/status")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["plan"] == "pro"
    assert body["status"] == "active"
    assert body["current_period_end"].startswith("2026-05-26")
    assert body["manage_url"] == "https://billing.stripe.com/p/session/abc"
    portal.assert_called_once_with("cus_pro_1")


def test_status_returns_401_without_auth(client, monkeypatch):
    # See test_create_checkout_session_returns_401_without_auth for the
    # explicit-empty-Authorization opt-out rationale.
    resp = client.get("/api/billing/status", headers={"Authorization": ""})
    assert resp.status_code == 401


def test_status_for_lapsed_user_surfaces_as_free_plan(client, db_session, make_user):
    """A lapsed user (plan='lapsed') must be represented as plan='free' in the response.

    The BillingStatusResponse DTO only accepts 'free' | 'pro' — 'lapsed' is an
    internal DB state not exposed via the openapi contract.
    """
    from modules.billing.models import Subscription

    user = make_user(auth_user_id="test-user", email="test@example.com")
    sub = Subscription(
        user_id=user.id,
        plan="lapsed",
        status="past_due",
        stripe_customer_id=None,
        stripe_subscription_id="sub_lapsed",
    )
    db_session.add(sub)
    db_session.commit()

    resp = client.get("/api/billing/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["plan"] == "free"
    assert body["status"] == "past_due"


# ── GET /api/billing/verify-session ─────────────────────────────────────────


class TestVerifySession:
    def test_returns_400_when_session_id_missing(self, client):
        resp = client.get("/api/billing/verify-session")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing session_id"

    def test_returns_200_with_plan_pro_on_paid_session(self, client, make_user):
        from modules.billing.routes import verify_session as vs

        with patch(
            "modules.billing.routes.verify_session",
            return_value={"plan": "pro", "payment_status": "paid"},
        ) as mock_vs:
            resp = client.get(
                "/api/billing/verify-session?session_id=cs_test_abc"
            )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["plan"] == "pro"
        assert body["payment_status"] == "paid"
        mock_vs.assert_called_once()

    def test_returns_403_when_session_belongs_to_other_user(self, client):
        from modules.billing.service import BillingOwnershipError

        with patch(
            "modules.billing.routes.verify_session",
            side_effect=BillingOwnershipError("session does not belong to this user"),
        ):
            resp = client.get(
                "/api/billing/verify-session?session_id=cs_other"
            )

        assert resp.status_code == 403
        assert "belong" in resp.get_json()["error"]

    def test_returns_400_when_session_is_invalid(self, client):
        from modules.billing.service import BillingSessionError

        with patch(
            "modules.billing.routes.verify_session",
            side_effect=BillingSessionError("No such session"),
        ):
            resp = client.get(
                "/api/billing/verify-session?session_id=cs_bad"
            )

        assert resp.status_code == 400
        body = resp.get_json()
        assert "No such session" in body["error"]

    def test_returns_401_without_auth(self, client):
        resp = client.get(
            "/api/billing/verify-session?session_id=cs_test_abc",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401
