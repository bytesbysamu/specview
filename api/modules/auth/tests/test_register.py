"""Tests for POST /api/auth/register."""
from __future__ import annotations

import os
import pytest
from sqlmodel import Session, SQLModel

# Register all tables before app creation.
import modules.auth.models  # noqa: F401 — ensures User table is registered


@pytest.fixture(scope="module")
def _mem_engine():
    # Import create_engine locally to prevent pytest collecting it as a test
    # (pyproject.toml uses python_functions = ["test_*", "*_*"]).
    from sqlalchemy import create_engine as _ce
    engine = _ce("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def app(_mem_engine):
    os.environ.setdefault("CHAIN_PROVIDER", "mock")
    # Patch get_engine on the routes module so register/login use the in-memory DB.
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
def _reset_state(_mem_engine):
    """Clear user rows and rate-limit buckets between tests."""
    from modules.auth.models import User
    import modules.auth.rate_limit as _rl
    _rl._ip_timestamps.clear()
    with Session(_mem_engine) as session:
        from sqlmodel import select
        for user in session.exec(select(User)).all():
            session.delete(user)
        session.commit()
    yield
    _rl._ip_timestamps.clear()


_VALID_EMAIL = "newuser@example.com"
_VALID_PASSWORD = "strongpass123"


def test_valid_registration_returns_201_with_token_and_email(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": _VALID_EMAIL, "password": _VALID_PASSWORD},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert "token" in body
    assert body["email"] == _VALID_EMAIL
    assert isinstance(body["token"], str)
    assert len(body["token"]) > 10


def test_duplicate_email_returns_409(client):
    # First registration succeeds.
    r1 = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": _VALID_PASSWORD},
        headers={"Authorization": ""},
    )
    assert r1.status_code == 201

    # Second registration with same email returns 409.
    resp = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": _VALID_PASSWORD},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 409
    body = resp.get_json()
    assert "error" in body


def test_missing_email_returns_400(client):
    resp = client.post(
        "/api/auth/register",
        json={"password": _VALID_PASSWORD},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_missing_password_returns_400(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": _VALID_EMAIL},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_empty_body_returns_400(client):
    resp = client.post(
        "/api/auth/register",
        json={},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_short_password_returns_400(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "abc"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body
    assert "password" in body["error"].lower()
