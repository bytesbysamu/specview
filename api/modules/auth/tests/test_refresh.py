"""Tests for POST /api/auth/refresh."""
from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("CHAIN_PROVIDER", "mock")
    from create_app import create_app as _ca
    return _ca({"TESTING": True})


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def test_valid_token_returns_200_with_new_token(client, monkeypatch):
    """A request with a valid JWT returns 200 and a fresh token."""
    from modules.auth.models import User
    import modules.auth.decorators as _dec

    fake_user = User(id=42, auth_user_id="sub-42", email="refresh@example.com", plan="free")

    monkeypatch.setattr(_dec, "verify_token", lambda t: {"sub": "42", "email": fake_user.email})
    monkeypatch.setattr(_dec, "_load_user", lambda uid: fake_user)

    resp = client.post(
        "/api/auth/refresh",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "token" in body
    assert body["email"] == fake_user.email
    assert isinstance(body["token"], str)
    assert len(body["token"]) > 10


def test_missing_token_returns_401(client, monkeypatch):
    """A request with no Authorization header returns 401."""
    import jwt
    import modules.auth.decorators as _dec

    monkeypatch.setattr(
        _dec,
        "verify_token",
        lambda t: (_ for _ in ()).throw(jwt.PyJWTError("missing")),
    )

    resp = client.post(
        "/api/auth/refresh",
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401


def test_no_current_user_returns_401(client, monkeypatch):
    """If _load_user returns None (user deleted), /refresh returns 401."""
    import modules.auth.decorators as _dec

    monkeypatch.setattr(_dec, "verify_token", lambda t: {"sub": "99", "email": "gone@example.com"})
    monkeypatch.setattr(_dec, "_load_user", lambda uid: None)

    resp = client.post(
        "/api/auth/refresh",
        headers={"Authorization": "Bearer orphaned-token"},
    )
    assert resp.status_code == 401
