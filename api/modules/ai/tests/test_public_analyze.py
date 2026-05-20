"""Tests for public_analyze service and route guardrails.

Covers:
- Input validation in the route handler (empty, whitespace, over-length)
- TTL-based job pruning in start_analysis
- Stripped braindump is passed to the service
"""
from __future__ import annotations

import time
import unittest.mock as mock

import pytest

import modules.ai.services.public_analyze as svc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_jobs():
    """Isolate each test — clear shared job state before and after."""
    svc._JOBS.clear()
    yield
    svc._JOBS.clear()


# ---------------------------------------------------------------------------
# Service: TTL pruning
# ---------------------------------------------------------------------------

def test_prune_removes_expired_entries():
    """Entries older than TTL_SECONDS are removed on the next start_analysis call."""
    old_time = time.time() - (svc._TTL_SECONDS + 1)
    with svc._LOCK:
        svc._JOBS["old-job"] = {
            "running": False,
            "done": True,
            "analysis": "result",
            "error": None,
            "started_at": old_time,
        }

    # A fresh call should trigger pruning
    with mock.patch("threading.Thread") as mock_thread:
        mock_thread.return_value = mock.MagicMock()
        svc.start_analysis("some braindump")  # return value intentionally unused here

    assert "old-job" not in svc._JOBS


def test_prune_keeps_recent_entries():
    """Entries younger than TTL_SECONDS are NOT removed."""
    with svc._LOCK:
        svc._JOBS["recent-job"] = {
            "running": False,
            "done": True,
            "analysis": "result",
            "error": None,
            "started_at": time.time(),
        }

    with mock.patch("threading.Thread") as mock_thread:
        mock_thread.return_value = mock.MagicMock()
        svc.start_analysis("some braindump")  # return value intentionally unused here

    assert "recent-job" in svc._JOBS


def test_start_analysis_adds_started_at():
    """Newly created jobs include a started_at timestamp."""
    with mock.patch("threading.Thread") as mock_thread:
        mock_thread.return_value = mock.MagicMock()
        job_id, _slug = svc.start_analysis("hello world")

    job = svc.get_job(job_id)
    assert job is not None
    assert "started_at" in job
    assert isinstance(job["started_at"], float)


def test_start_analysis_new_job_initial_state():
    """New job entries start with running=True, done=False."""
    with mock.patch("threading.Thread") as mock_thread:
        mock_thread.return_value = mock.MagicMock()
        job_id, _slug = svc.start_analysis("a valid braindump")

    job = svc.get_job(job_id)
    assert job["running"] is True
    assert job["done"] is False
    assert job["analysis"] is None
    assert job["error"] is None


# ---------------------------------------------------------------------------
# Route: input validation
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Minimal Flask app with the public_analyze blueprint registered."""
    from flask import Flask
    from modules.ai.routes.public_analyze import public_analyze_bp
    import modules.auth.rate_limit as _rl

    flask_app = Flask(__name__ + "_test")
    flask_app.register_blueprint(public_analyze_bp)

    # Clear rate-limit state between tests
    _rl._ip_timestamps.clear()

    return flask_app


_PATCH = "modules.ai.routes.public_analyze.start_analysis"


def test_empty_braindump_returns_400(app):
    """POST with an empty string returns 400 without triggering analysis."""
    with mock.patch(_PATCH) as mock_start:
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": ""},
        )
    assert resp.status_code == 400
    assert "braindump" in resp.get_json()["error"].lower()
    mock_start.assert_not_called()


def test_whitespace_only_braindump_returns_400(app):
    """POST with a whitespace-only string returns 400 without triggering analysis."""
    with mock.patch(_PATCH) as mock_start:
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": "   \n\t  "},
        )
    assert resp.status_code == 400
    mock_start.assert_not_called()


def test_missing_braindump_returns_400(app):
    """POST with no braindump key returns 400."""
    with mock.patch(_PATCH) as mock_start:
        resp = app.test_client().post(
            "/api/public/analyze",
            json={},
        )
    assert resp.status_code == 400
    mock_start.assert_not_called()


def test_over_limit_braindump_returns_400(app):
    """POST with a braindump exceeding 10000 chars returns 400."""
    long_input = "a" * 10001
    with mock.patch(_PATCH) as mock_start:
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": long_input},
        )
    assert resp.status_code == 400
    assert "10000" in resp.get_json()["error"]
    mock_start.assert_not_called()


def test_exact_limit_braindump_is_accepted(app):
    """POST with exactly 10000 chars is accepted."""
    exact_input = "a" * 10000
    patch_target = "modules.ai.routes.public_analyze.start_analysis"
    with mock.patch(patch_target, return_value=("test-job-id", "slug-abc")) as mock_start:
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": exact_input},
        )
    assert resp.status_code == 202
    mock_start.assert_called_once_with(exact_input)


def test_valid_braindump_is_stripped_before_service_call(app):
    """Leading/trailing whitespace is stripped before start_analysis is called."""
    patch_target = "modules.ai.routes.public_analyze.start_analysis"
    with mock.patch(patch_target, return_value=("job-123", "slug-xyz")) as mock_start:
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": "  hello world  "},
        )
    assert resp.status_code == 202
    mock_start.assert_called_once_with("hello world")


def test_valid_braindump_returns_202_with_job_id(app):
    """A valid POST returns 202 with a job_id and share_slug."""
    patch_target = "modules.ai.routes.public_analyze.start_analysis"
    with mock.patch(patch_target, return_value=("abc-123", "slug-def")):
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": "I want to build a thing"},
        )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["job_id"] == "abc-123"
    assert body["share_slug"] == "slug-def"
