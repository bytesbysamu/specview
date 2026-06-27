"""Boot test for the Core-only app factory (``create_core_app``).

Proves the slice that becomes oll-core: it boots with ONLY auth/billing/email/
health mounted, the product surface is absent, and the full
magic-link → verify → checkout → email path runs green against an in-memory DB
(Stripe + Resend mocked at the route boundary). This is the behaviour that gets
lifted verbatim into oll-core.
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel

# Registering these modules puts User + MagicLinkToken + Subscription on
# SQLModel.metadata so create_all() builds the Core tables.
import modules.auth.models  # noqa: F401
import modules.billing.models  # noqa: F401

# NOTE: imports whose name contains an underscore (create_engine, parse_qs) are
# done INSIDE functions, not at module level — this repo sets
# python_functions = ["test_*", "*_*"], so a module-level `create_engine` would
# be mis-collected as a test. (Same pattern as modules/auth/tests/test_magic_link.py.)


@pytest.fixture
def _engine():
    from sqlalchemy import create_engine

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def app(_engine, monkeypatch):
    # Hermetic secrets so the boot gate is satisfied without a developer .env.
    monkeypatch.setenv("AUTH_JWT_SECRET", "core-boot-test-secret-32-bytes-long!")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_core_boot_test")

    # Point every Core module at the one in-memory engine.
    import modules.auth.decorators as auth_decorators
    import modules.auth.routes as auth_routes

    monkeypatch.setattr(auth_routes, "get_engine", lambda: _engine)
    monkeypatch.setattr(auth_decorators, "get_engine", lambda: _engine)

    @contextmanager
    def _session():
        with Session(_engine) as s:
            yield s

    monkeypatch.setattr("modules.data.db.session.get_session", _session)
    monkeypatch.setattr("modules.billing.routes.get_session", _session)

    from create_core_app import create_core_app

    return create_core_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


def test_core_app_boots(app):
    assert app is not None


def test_core_surface_mounted(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    for path in (
        "/api/auth/magic-link",
        "/api/auth/verify",
        "/api/auth/me",
        "/api/billing/create-checkout-session",
        "/api/billing/webhook",
        "/api/email/send",
        "/api/health",
    ):
        assert path in rules, f"Core route missing: {path}"


def test_product_surface_absent(app):
    """Core must not mount any of specview's product blueprints."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    product_segments = (
        "/api/projects",
        "/api/context",
        "/api/templates",
        "/api/generate",
        "/api/specs",
        "/api/skill",
        "/api/actions",
        "/api/public",
        "/api/analyze",
    )
    leaked = [r for r in rules if any(seg in r for seg in product_segments)]
    assert leaked == [], f"product routes leaked into Core: {leaked}"


def test_magic_link_to_jwt_flow(client, monkeypatch):
    captured: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "modules.auth.routes.send_magic_link",
        lambda email, link: captured.append((email, link)) or True,
    )

    r = client.post(
        "/api/auth/magic-link",
        json={"email": "boot@example.com"},
        headers={"Authorization": ""},
    )
    assert r.status_code == 200
    from urllib.parse import parse_qs, urlparse

    token = parse_qs(urlparse(captured[0][1]).query)["token"][0]

    v = client.post(
        "/api/auth/verify",
        json={"token": token},
        headers={"Authorization": ""},
    )
    assert v.status_code == 200
    assert isinstance(v.get_json()["token"], str)


def test_checkout_and_email_flow_green(client, monkeypatch):
    # Stripe + Resend mocked at the route boundary — this proves Core's wiring,
    # not the third-party SDKs. The global conftest bypass authenticates these
    # routes as the fixed test user (test@example.com).
    monkeypatch.setattr(
        "modules.billing.routes.create_checkout_session",
        lambda user, product, plan: "https://checkout.stripe.com/pay/boot",
    )
    c = client.post(
        "/api/billing/create-checkout-session",
        json={"product": "oll_pro", "plan": "monthly"},
    )
    assert c.status_code == 200
    assert c.get_json()["url"].startswith("https://checkout.stripe.com/")

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "modules.email.routes.send_subscription_activated",
        lambda to, plan: sent.append((to, plan)) or True,
    )
    e = client.post(
        "/api/email/send",
        json={
            "to": "test@example.com",
            "template": "subscription_activated",
            "ctx": {"plan": "Pro"},
        },
    )
    assert e.status_code == 200
    assert sent == [("test@example.com", "Pro")]
