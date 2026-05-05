"""Unit tests for the @require_auth decorator."""
from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest
from flask import Flask, g, jsonify

from modules.auth import decorators
from modules.auth.models import User


@pytest.fixture
def app():
    application = Flask(__name__)
    application.user_repository = MagicMock()
    application.user_repository.get_by_auth_user_id.return_value = User(
        id=1, auth_user_id="u-1", email="a@b.co"
    )

    @application.route("/protected")
    @decorators.require_auth
    def protected():
        return jsonify({"user_id": g.current_user.id})

    return application


def test_require_auth_returns401WhenHeaderMissing(app):
    client = app.test_client()
    resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "missing bearer token"}


def test_require_auth_returns401WhenHeaderNotBearer(app):
    client = app.test_client()
    resp = client.get("/protected", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "missing bearer token"}


def test_require_auth_returns401OnInvalidToken(app, monkeypatch):
    def bad_verify(token):
        raise jwt.InvalidSignatureError("bad sig")

    monkeypatch.setattr(decorators, "verify_jwt", bad_verify)
    client = app.test_client()
    resp = client.get("/protected", headers={"Authorization": "Bearer xxx"})
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "invalid token: InvalidSignatureError"}


def test_require_auth_setsCurrentUserAndDispatches(app, monkeypatch):
    monkeypatch.setattr(decorators, "verify_jwt", lambda t: {"sub": "u-1", "email": "a@b.co"})
    monkeypatch.setattr(
        decorators,
        "get_or_create_user_from_claims",
        lambda claims, repo: User(id=1, auth_user_id=claims["sub"], email=claims["email"]),
    )
    client = app.test_client()
    resp = client.get("/protected", headers={"Authorization": "Bearer good"})
    assert resp.status_code == 200
    assert resp.get_json() == {"user_id": 1}
