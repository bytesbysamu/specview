"""Tests for the ip_rate_limit decorator."""
from __future__ import annotations

import time
import pytest

import modules.auth.rate_limit as _rl


@pytest.fixture(autouse=True)
def _clear_timestamps():
    """Reset the shared rate-limit state before each test."""
    _rl._ip_timestamps.clear()
    yield
    _rl._ip_timestamps.clear()


def _build_limited_app():
    """Return a minimal Flask app with a single rate-limited POST /test route."""
    from flask import Flask, jsonify
    app = Flask(__name__ + "_rate_limit_test")

    @app.post("/test")
    @_rl.ip_rate_limit
    def _endpoint():
        return jsonify({"ok": True}), 200

    return app


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
