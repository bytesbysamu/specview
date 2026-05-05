"""Unit tests for `modules.observability.health` — per-dependency probes.

These tests stand up a minimal Flask app and register `health_bp` directly
rather than going through `create_app()`. Reasoning: the consolidated
wrap-up that registers `health_bp` in `create_app.py` ships in a separate
commit (it is intentionally out of scope for SaaS Operations & Infra
Task 3 — see the task contract and the create_app.py exclusion in the
DO NOT TOUCH list). Testing the blueprint in isolation guarantees the
test suite is green at the moment Task 3 lands and stays green when the
wrap-up commit registers it later.

The CHAIN_PROVIDER env var is intentionally not touched here because this
blueprint does not go through the chain adapter (locked decision: probe
calls the Anthropic SDK directly to avoid generation credits and to keep
the probe out of the rest of the request lifecycle).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Ensure api/ is importable regardless of pytest invocation directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from modules.observability.health import (  # noqa: E402
    _MAX_ERROR_CHARS,
    health_bp,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal Flask app with the blueprint registered in isolation.
# ---------------------------------------------------------------------------


@pytest.fixture()
def app() -> Flask:
    """Flask test app with only health_bp registered.

    Deliberately bypasses create_app() because Task 3 does not yet wire the
    blueprint into the factory; that wiring is the wrap-up commit's job.
    """
    flask_app = Flask(__name__)
    flask_app.register_blueprint(health_bp)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


# ---------------------------------------------------------------------------
# Neon stub — permanent skipped contract.
# ---------------------------------------------------------------------------


class TestNeonHealth:
    def test_returnsSkipped_status(self, client):
        resp = client.get("/api/health/neon")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "skipped"}

    def test_responseHasNoExtraKeys(self, client):
        resp = client.get("/api/health/neon")
        assert set(resp.get_json().keys()) == {"status"}

    def test_returnsJsonContentType(self, client):
        resp = client.get("/api/health/neon")
        assert "application/json" in resp.content_type


# ---------------------------------------------------------------------------
# Stripe stub — permanent skipped contract.
# ---------------------------------------------------------------------------


class TestStripeHealth:
    def test_returnsSkipped_status(self, client):
        resp = client.get("/api/health/stripe")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "skipped"}

    def test_responseHasNoExtraKeys(self, client):
        resp = client.get("/api/health/stripe")
        assert set(resp.get_json().keys()) == {"status"}

    def test_returnsJsonContentType(self, client):
        resp = client.get("/api/health/stripe")
        assert "application/json" in resp.content_type


# ---------------------------------------------------------------------------
# Anthropic — live probe, three branches: skipped / ok / degraded.
# ---------------------------------------------------------------------------


class TestAnthropicHealth:
    def test_skipped_whenApiKeyUnset(self, client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        resp = client.get("/api/health/anthropic")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "skipped"}

    def test_ok_whenSdkCallSucceeds(self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

        fake_client = MagicMock()
        fake_client.messages.count_tokens.return_value = MagicMock(input_tokens=2)

        with patch("anthropic.Anthropic", return_value=fake_client) as ctor:
            resp = client.get("/api/health/anthropic")

        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}
        # Probe must use the 5.0s timeout — that is the load-bearing SLO.
        ctor.assert_called_once_with(timeout=5.0)
        fake_client.messages.count_tokens.assert_called_once()
        kwargs = fake_client.messages.count_tokens.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"
        assert kwargs["messages"] == [{"role": "user", "content": "ping"}]

    def test_degraded_whenSdkRaises(self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

        fake_client = MagicMock()
        fake_client.messages.count_tokens.side_effect = RuntimeError(
            "connection refused"
        )

        with patch("anthropic.Anthropic", return_value=fake_client):
            resp = client.get("/api/health/anthropic")

        assert resp.status_code == 503
        body = resp.get_json()
        assert body["status"] == "degraded"
        assert body["error"] == "connection refused"

    def test_degraded_truncatesLongErrorMessage(self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

        long_message = "x" * 500
        fake_client = MagicMock()
        fake_client.messages.count_tokens.side_effect = RuntimeError(long_message)

        with patch("anthropic.Anthropic", return_value=fake_client):
            resp = client.get("/api/health/anthropic")

        assert resp.status_code == 503
        body = resp.get_json()
        assert body["status"] == "degraded"
        assert len(body["error"]) == _MAX_ERROR_CHARS
        assert body["error"] == "x" * _MAX_ERROR_CHARS

    def test_degraded_whenSdkConstructorRaises(self, client, monkeypatch):
        """Auth/config errors raised by Anthropic(...) itself must also degrade."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

        with patch(
            "anthropic.Anthropic",
            side_effect=ValueError("bad api key format"),
        ):
            resp = client.get("/api/health/anthropic")

        assert resp.status_code == 503
        body = resp.get_json()
        assert body["status"] == "degraded"
        assert body["error"] == "bad api key format"

    def test_responseHasOnlyStatusKey_onOk(self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        fake_client = MagicMock()
        with patch("anthropic.Anthropic", return_value=fake_client):
            resp = client.get("/api/health/anthropic")
        assert set(resp.get_json().keys()) == {"status"}

    def test_responseHasOnlyStatusKey_onSkipped(self, client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        resp = client.get("/api/health/anthropic")
        assert set(resp.get_json().keys()) == {"status"}


# ---------------------------------------------------------------------------
# Blueprint structural — name + url_prefix are part of the wrap-up contract.
# ---------------------------------------------------------------------------


class TestHealthBlueprintWiring:
    def test_blueprintName_isHealth(self):
        assert health_bp.name == "health"

    def test_urlPrefix_matchesContract(self):
        assert health_bp.url_prefix == "/api/health"

    def test_allThreeRoutes_registered(self, app):
        rules = {r.rule for r in app.url_map.iter_rules() if r.rule.startswith("/api/health")}
        assert rules == {
            "/api/health/anthropic",
            "/api/health/neon",
            "/api/health/stripe",
        }
