"""Integration tests for the /api/auth/* blueprint."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests
from flask import Flask

from modules.auth import decorators, routes
from modules.auth.models import User


@pytest.fixture
def app():
    application = Flask(__name__)
    application.user_repository = MagicMock()
    application.user_repository.get_by_auth_user_id.return_value = User(
        id=99, auth_user_id="u-99", email="e@f.co"
    )
    application.register_blueprint(routes.auth_bp)
    return application


def test_login_returns202WithRequestId(app, monkeypatch):
    monkeypatch.setattr(routes, "send_magic_link", lambda email: {"request_id": "req-1"})
    client = app.test_client()
    resp = client.post("/api/auth/login", json={"email": "a@b.co"})
    assert resp.status_code == 202
    assert resp.get_json() == {"request_id": "req-1"}


def test_login_returns502WhenNeonAuthRejects(app, monkeypatch):
    def boom(email):
        raise requests.HTTPError("500 Server Error")

    monkeypatch.setattr(routes, "send_magic_link", boom)
    client = app.test_client()
    resp = client.post("/api/auth/login", json={"email": "a@b.co"})
    assert resp.status_code == 502
    assert "neon auth rejected" in resp.get_json()["error"]


def test_verify_returns200WithJwtAndUser(app, monkeypatch):
    monkeypatch.setattr(routes, "verify_magic_link", lambda t: {
        "jwt": "abc.def.ghi",
        "claims": {"sub": "u-99", "email": "e@f.co"},
    })
    monkeypatch.setattr(
        routes,
        "get_or_create_user_from_claims",
        lambda claims, repo: User(id=99, auth_user_id=claims["sub"], email=claims["email"]),
    )
    client = app.test_client()
    resp = client.post("/api/auth/verify", json={"token": "one-time"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["jwt"] == "abc.def.ghi"
    assert body["user"]["id"] == 99
    assert body["user"]["auth_user_id"] == "u-99"


def test_verify_returns400WhenTokenInvalid(app, monkeypatch):
    def boom(token):
        raise requests.HTTPError("400 Bad Request")

    monkeypatch.setattr(routes, "verify_magic_link", boom)
    client = app.test_client()
    resp = client.post("/api/auth/verify", json={"token": "bad"})
    assert resp.status_code == 400
    assert "invalid or expired token" in resp.get_json()["error"]


def test_logout_returns204(app):
    client = app.test_client()
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert resp.data == b""


def test_me_returnsCurrentUser(app, monkeypatch):
    monkeypatch.setattr(decorators, "verify_jwt", lambda t: {"sub": "u-99", "email": "e@f.co"})
    monkeypatch.setattr(
        decorators,
        "get_or_create_user_from_claims",
        lambda claims, repo: User(id=99, auth_user_id=claims["sub"], email=claims["email"]),
    )
    client = app.test_client()
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer good"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == 99
    assert body["email"] == "e@f.co"
    assert body["auth_user_id"] == "u-99"
