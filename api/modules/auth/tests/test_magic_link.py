"""Integration tests for passwordless magic-link auth.

Covers POST /api/auth/magic-link and POST /api/auth/verify end-to-end against
an in-memory SQLite DB. The product has no passwords; these replace the old
register/login tests.
"""
from __future__ import annotations

import os

import pytest
from sqlmodel import Session, SQLModel, select

# Register all tables (User + MagicLinkToken) before app creation.
import modules.auth.models  # noqa: F401


@pytest.fixture(scope="module")
def _mem_engine():
    from sqlalchemy import create_engine as _ce
    engine = _ce("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def app(_mem_engine):
    os.environ.setdefault("CHAIN_PROVIDER", "mock")
    # Point the auth routes at the in-memory DB.
    import modules.auth.routes as _routes
    _orig = _routes.get_engine
    _routes.get_engine = lambda: _mem_engine

    from create_app import create_app as _ca
    flask_app = _ca({"TESTING": True})

    yield flask_app

    _routes.get_engine = _orig


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _reset_state(_mem_engine, monkeypatch):
    """Clear user/token rows and rate-limit buckets between tests, and capture
    the magic link instead of sending a real email."""
    from modules.auth.models import MagicLinkToken, User
    import modules.auth.rate_limit as _rl
    _rl._ip_timestamps.clear()
    with Session(_mem_engine) as session:
        for row in session.exec(select(MagicLinkToken)).all():
            session.delete(row)
        for user in session.exec(select(User)).all():
            session.delete(user)
        session.commit()
    yield
    _rl._ip_timestamps.clear()


@pytest.fixture
def captured_links(monkeypatch):
    """Patch the email sender used by the route to record issued links."""
    links: list[tuple[str, str]] = []

    def _capture(email: str, link: str) -> bool:
        links.append((email, link))
        return True

    import modules.auth.routes as _routes
    monkeypatch.setattr(_routes, "send_magic_link", _capture)
    return links


class _Link:
    """Namespace for link helpers; pytest does not collect non-Test classes."""

    @staticmethod
    def token(link: str) -> str:
        from urllib.parse import urlparse, parse_qs
        return parse_qs(urlparse(link).query)["token"][0]


_EMAIL = "newuser@example.com"


# ── POST /api/auth/magic-link ───────────────────────────────────────────────

def test_magic_link_returns_200_sent_true(client, captured_links):
    resp = client.post(
        "/api/auth/magic-link",
        json={"email": _EMAIL},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}
    assert len(captured_links) == 1
    to, link = captured_links[0]
    assert to == _EMAIL
    assert "/auth/verify?token=" in link


def test_magic_link_unknown_email_still_returns_200(client, captured_links):
    # No account exists yet — must not reveal that via the response.
    resp = client.post(
        "/api/auth/magic-link",
        json={"email": "stranger@example.com"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}


def test_magic_link_invalid_email_returns_200_no_enumeration(client, captured_links):
    resp = client.post(
        "/api/auth/magic-link",
        json={"email": "not-an-email"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}
    # Malformed address: no link issued.
    assert captured_links == []


# ── POST /api/auth/verify ───────────────────────────────────────────────────

def test_verify_valid_token_issues_jwt_and_creates_user(client, captured_links, _mem_engine):
    client.post("/api/auth/magic-link", json={"email": _EMAIL}, headers={"Authorization": ""})
    token = _Link.token(captured_links[0][1])

    resp = client.post(
        "/api/auth/verify",
        json={"token": token},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["email"] == _EMAIL
    assert isinstance(body["token"], str) and len(body["token"]) > 10

    # User was find-or-created.
    from modules.auth.models import User
    with Session(_mem_engine) as session:
        user = session.exec(select(User).where(User.email == _EMAIL)).first()
        assert user is not None
        assert user.password_hash is None


def test_verify_token_is_single_use(client, captured_links):
    client.post("/api/auth/magic-link", json={"email": _EMAIL}, headers={"Authorization": ""})
    token = _Link.token(captured_links[0][1])

    first = client.post("/api/auth/verify", json={"token": token}, headers={"Authorization": ""})
    assert first.status_code == 200

    second = client.post("/api/auth/verify", json={"token": token}, headers={"Authorization": ""})
    assert second.status_code == 401
    assert second.get_json()["code"] == "INVALID_TOKEN"


def test_verify_unknown_token_returns_401(client):
    resp = client.post(
        "/api/auth/verify",
        json={"token": "totally-bogus"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401
    assert resp.get_json()["code"] == "INVALID_TOKEN"


def test_verify_missing_token_returns_401(client):
    resp = client.post(
        "/api/auth/verify",
        json={},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401


def test_verify_expired_token_returns_401(client, captured_links, _mem_engine):
    from datetime import datetime, timedelta, timezone
    from modules.auth.models import MagicLinkToken

    client.post("/api/auth/magic-link", json={"email": _EMAIL}, headers={"Authorization": ""})
    token = _Link.token(captured_links[0][1])

    # Force the stored token to be expired.
    with Session(_mem_engine) as session:
        row = session.exec(select(MagicLinkToken)).first()
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.add(row)
        session.commit()

    resp = client.post("/api/auth/verify", json={"token": token}, headers={"Authorization": ""})
    assert resp.status_code == 401


# ── product key → per-product verify base ───────────────────────────────────

def test_magic_link_default_base_when_no_product(client, captured_links, monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://specview.dev")
    resp = client.post(
        "/api/auth/magic-link",
        json={"email": _EMAIL},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    _, link = captured_links[0]
    assert link.startswith("https://specview.dev/auth/verify?token=")


def test_magic_link_known_product_uses_configured_base(client, captured_links, monkeypatch):
    monkeypatch.setenv("PRODUCT_VERIFY_BASE_FOTO", "https://foto.ch")
    resp = client.post(
        "/api/auth/magic-link",
        json={"email": _EMAIL, "product": "foto"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    _, link = captured_links[0]
    assert link.startswith("https://foto.ch/auth/verify?token=")


def test_magic_link_unknown_product_rejected_400(client, captured_links, monkeypatch):
    monkeypatch.delenv("PRODUCT_VERIFY_BASE_NOPE", raising=False)
    resp = client.post(
        "/api/auth/magic-link",
        json={"email": _EMAIL, "product": "nope"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_PRODUCT"
    # No token minted, no link issued — the unknown product is rejected before
    # any account-state side effect, so nothing about the email is revealed.
    assert captured_links == []


def test_existing_user_reused_on_verify(client, captured_links, _mem_engine):
    from modules.auth.models import User
    with Session(_mem_engine) as session:
        session.add(User(email=_EMAIL, plan="pro"))
        session.commit()

    client.post("/api/auth/magic-link", json={"email": _EMAIL}, headers={"Authorization": ""})
    token = _Link.token(captured_links[0][1])
    resp = client.post("/api/auth/verify", json={"token": token}, headers={"Authorization": ""})
    assert resp.status_code == 200

    with Session(_mem_engine) as session:
        users = session.exec(select(User).where(User.email == _EMAIL)).all()
        assert len(users) == 1  # no duplicate created
        assert users[0].plan == "pro"  # existing plan preserved
