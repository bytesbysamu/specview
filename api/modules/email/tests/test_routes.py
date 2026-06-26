"""Route-level coverage for POST /api/email/send.

The Resend send functions are patched; the focus is HTTP shape — auth gating,
recipient scoping, template dispatch, validation, and the unified error
envelope. The top-level conftest `_auth_bypass` injects a Bearer token and a
fake user whose email is `test@example.com`.
"""
import pytest
from flask import Flask

from modules.email.routes import email_bp

_OWN = "test@example.com"  # matches the conftest fake user's email


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    flask_app.testing = True
    flask_app.register_blueprint(email_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ── happy paths ─────────────────────────────────────────────────────────────


def test_custom_template_sends(client, monkeypatch):
    sent = {}

    def _send(to, subject, html, from_email=None):
        sent.update(to=to, subject=subject, html=html)
        return True

    monkeypatch.setattr("modules.email.routes.send_email", _send)
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "custom", "subject": "Hi", "html": "<p>x</p>"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}
    assert sent == {"to": _OWN, "subject": "Hi", "html": "<p>x</p>"}


def test_magic_link_template_sends(client, monkeypatch):
    captured = {}

    def _send_magic(to, link):
        captured.update(to=to, link=link)
        return True

    monkeypatch.setattr("modules.email.routes.send_magic_link", _send_magic)
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "magic_link", "ctx": {"link": "https://x/y"}},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}
    assert captured == {"to": _OWN, "link": "https://x/y"}


def test_subscription_activated_template_sends(client, monkeypatch):
    monkeypatch.setattr(
        "modules.email.routes.send_subscription_activated",
        lambda to, plan="Pro": True,
    )
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "subscription_activated", "ctx": {"plan": "Pro"}},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}


# ── validation / scoping ────────────────────────────────────────────────────


def test_recipient_must_be_own_email(client):
    resp = client.post(
        "/api/email/send",
        json={"to": "someone-else@example.com", "template": "subscription_activated"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["code"] == "FORBIDDEN_RECIPIENT"


def test_custom_template_missing_subject_returns_400(client):
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "custom", "html": "<p>x</p>"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "MISSING_FIELD"


def test_magic_link_missing_link_returns_400(client):
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "magic_link", "ctx": {}},
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "MISSING_FIELD"


def test_missing_to_returns_400(client):
    resp = client.post("/api/email/send", json={"template": "custom"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_REQUEST"


def test_unknown_template_returns_400(client):
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "not_a_template"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_REQUEST"


def test_provider_failure_returns_500(client, monkeypatch):
    monkeypatch.setattr(
        "modules.email.routes.send_subscription_activated", lambda to, plan="Pro": False
    )
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "subscription_activated"},
    )
    assert resp.status_code == 500
    assert resp.get_json()["code"] == "EMAIL_FAILED"


def test_returns_401_without_auth(client):
    resp = client.post(
        "/api/email/send",
        json={"to": _OWN, "template": "custom", "subject": "s", "html": "<p>x</p>"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401
