"""Tests for the ip_rate_limit decorator."""
from __future__ import annotations

import time
import pytest
from flask import Flask, jsonify

import modules.auth.rate_limit as _rl


@pytest.fixture(autouse=True)
def _clear_timestamps():
    """Reset the shared rate-limit state before each test."""
    _rl._ip_timestamps.clear()
    yield
    _rl._ip_timestamps.clear()


def _build_limited_app():
    """Return a minimal Flask app with a single rate-limited POST /test route."""
    app = Flask(__name__ + "_rate_limit_test")

    @app.post("/test")
    @_rl.ip_rate_limit
    def _endpoint():
        return jsonify({"ok": True}), 200

    return app


class _AppFactory:
    """Namespace for app-builder helpers; pytest does not collect non-Test classes."""

    @staticmethod
    def custom(n_req: int, n_win: int) -> Flask:
        """Return a Flask app rate-limited to n_req requests per n_win seconds."""
        app = Flask(__name__ + "_rate_limit_custom_test")

        @app.post("/test")
        @_rl.ip_rate_limit(max_requests=n_req, window_seconds=n_win)
        def _endpoint():
            return jsonify({"ok": True}), 200

        return app


# ---------------------------------------------------------------------------
# Existing tests — bare-decorator (@ip_rate_limit) usage
# ---------------------------------------------------------------------------

def test_requests_within_limit_succeed():
    """First N requests (up to _MAX_REQUESTS) all return 200."""
    app = _build_limited_app()
    with app.test_client() as client:
        for _ in range(_rl._MAX_REQUESTS):
            resp = client.post("/test", environ_base={"REMOTE_ADDR": "1.2.3.4"})
            assert resp.status_code == 200


def test_request_exceeding_limit_returns_429():
    """The (_MAX_REQUESTS + 1)th request from the same IP returns 429."""
    app = _build_limited_app()
    with app.test_client() as client:
        for _ in range(_rl._MAX_REQUESTS):
            client.post("/test", environ_base={"REMOTE_ADDR": "5.5.5.5"})

        resp = client.post("/test", environ_base={"REMOTE_ADDR": "5.5.5.5"})
        assert resp.status_code == 429
        body = resp.get_json()
        assert "error" in body
        assert "Retry-After" in resp.headers


def test_different_ips_have_independent_limits():
    """Rate-limit buckets are per-IP — one IP exhausted does not block another."""
    app = _build_limited_app()
    with app.test_client() as client:
        for _ in range(_rl._MAX_REQUESTS + 1):
            client.post("/test", environ_base={"REMOTE_ADDR": "10.0.0.1"})

        # 10.0.0.2 has not been seen yet — its first request must succeed.
        resp = client.post("/test", environ_base={"REMOTE_ADDR": "10.0.0.2"})
        assert resp.status_code == 200


def test_old_timestamps_outside_window_are_pruned():
    """Timestamps older than _WINDOW_SECONDS are pruned and don't count."""
    app = _build_limited_app()
    ip = "20.0.0.1"
    past = time.time() - _rl._WINDOW_SECONDS - 1

    # Manually inject stale timestamps that fill the bucket.
    _rl._ip_timestamps[ip].extend([past] * _rl._MAX_REQUESTS)

    with app.test_client() as client:
        # The stale timestamps are outside the window; this request should succeed.
        resp = client.post("/test", environ_base={"REMOTE_ADDR": ip})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# New tests — factory (@ip_rate_limit(max_requests=..., window_seconds=...))
# ---------------------------------------------------------------------------

def test_factory_requests_within_custom_limit_succeed():
    """Requests up to the custom max_requests threshold all return 200."""
    app = _AppFactory.custom(3, 86400)
    with app.test_client() as client:
        for _ in range(3):
            resp = client.post("/test", environ_base={"REMOTE_ADDR": "30.0.0.1"})
            assert resp.status_code == 200


def test_factory_fourth_request_returns_429():
    """The 4th request from the same IP is rejected when limit is 3."""
    app = _AppFactory.custom(3, 86400)
    with app.test_client() as client:
        for _ in range(3):
            client.post("/test", environ_base={"REMOTE_ADDR": "30.0.0.2"})

        resp = client.post("/test", environ_base={"REMOTE_ADDR": "30.0.0.2"})
        assert resp.status_code == 429
        body = resp.get_json()
        assert "error" in body
        assert "Retry-After" in resp.headers


def test_factory_retry_after_uses_window_seconds():
    """Retry-After header reflects the custom window_seconds, not the default 3600."""
    app = _AppFactory.custom(1, 86400)
    with app.test_client() as client:
        # First request fills the bucket.
        client.post("/test", environ_base={"REMOTE_ADDR": "30.0.0.3"})

        # Second request should be rejected with Retry-After <= 86400.
        resp = client.post("/test", environ_base={"REMOTE_ADDR": "30.0.0.3"})
        assert resp.status_code == 429
        retry_after = int(resp.headers["Retry-After"])
        assert retry_after <= 86400
        # Ensure it is NOT based on the default 3600-second window.
        assert retry_after > 3600


def test_factory_stale_timestamps_pruned_with_custom_window():
    """Timestamps older than the custom window_seconds are pruned correctly."""
    window = 7200
    app = _AppFactory.custom(2, window)
    ip = "30.0.0.4"
    past = time.time() - window - 1

    # Inject stale timestamps that exceed the custom limit.
    _rl._ip_timestamps[ip].extend([past] * 2)

    with app.test_client() as client:
        resp = client.post("/test", environ_base={"REMOTE_ADDR": ip})
        assert resp.status_code == 200
