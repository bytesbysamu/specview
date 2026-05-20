"""Tests for public_analyze service and route guardrails.

Covers:
- Input validation in the route handler (empty, whitespace, over-length)
- TTL-based job pruning in start_analysis
- Stripped braindump is passed to the service
- Filesystem persistence: project directory, braindump.md, project.json
- Disk fallback in get_job()
- Route responses include project_id and share_slug
"""
from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Service: filesystem persistence
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_projects_dir(tmp_path, monkeypatch):
    """Redirect PROJECTS_DIR to a per-test tmp directory.

    Patches svc.PROJECTS_DIR via the config module so all code paths
    in public_analyze.py see the same temporary directory.
    """
    projects = tmp_path / "projects"
    projects.mkdir()
    import config
    monkeypatch.setattr(config, "PROJECTS_DIR", projects)
    # Also patch the reference used inside the module's already-imported namespace.
    monkeypatch.setattr("modules.ai.services.public_analyze.PROJECTS_DIR", projects)
    return projects


def startwithmocks(braindump: str):
    """Call start_analysis with Thread, generate_slug, register_slug,
    and DB write all mocked so no side-effects escape the test."""
    with (
        mock.patch("threading.Thread") as mock_thread,
        mock.patch(
            "modules.ai.services.public_analyze.generate_slug",
            return_value="test-share-slug",
        ),
        mock.patch("modules.ai.services.public_analyze.register_slug"),
        mock.patch(
            "modules.data.projects.repository.SqlProjectRepository.create_anonymous"
        ),
    ):
        mock_thread.return_value = mock.MagicMock()
        return svc.start_analysis(braindump)


def test_start_analysis_creates_project_directory(isolated_projects_dir):
    """start_analysis must create a per-project directory under PROJECTS_DIR."""
    job_id, _slug = startwithmocks("Build a todo app")
    assert (isolated_projects_dir / job_id).is_dir(), (
        f"Expected project directory at {isolated_projects_dir / job_id}"
    )


def test_start_analysis_writes_braindump_md(isolated_projects_dir):
    """start_analysis must write braindump.md with the exact input content."""
    braindump = "Build a todo app with reminders"
    job_id, _slug = startwithmocks(braindump)
    braindump_path = isolated_projects_dir / job_id / "braindump.md"
    assert braindump_path.exists(), "braindump.md must be written by start_analysis"
    assert braindump_path.read_text(encoding="utf-8") == braindump


def test_start_analysis_writes_project_json_with_share_slug(isolated_projects_dir):
    """project.json must contain name, createdAt, anonymous=True, and shareSlug."""
    braindump = "Launch a landing page"
    job_id, _slug = startwithmocks(braindump)
    meta_path = isolated_projects_dir / job_id / "project.json"
    assert meta_path.exists(), "project.json must be written by start_analysis"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "name" in meta, "project.json must contain 'name'"
    assert "createdAt" in meta, "project.json must contain 'createdAt'"
    assert meta.get("anonymous") is True, "project.json must set anonymous=True"
    assert "shareSlug" in meta, "project.json must contain 'shareSlug'"
    assert meta["shareSlug"] == "test-share-slug"


def test_start_analysis_returns_project_id_and_share_slug(isolated_projects_dir):
    """start_analysis must return a (project_id, share_slug) tuple."""
    result = startwithmocks("Some braindump text")
    assert isinstance(result, tuple), "start_analysis must return a tuple"
    assert len(result) == 2, "start_analysis must return exactly two values"
    project_id, share_slug = result
    assert isinstance(project_id, str) and project_id, "project_id must be a non-empty string"
    assert isinstance(share_slug, str) and share_slug, "share_slug must be a non-empty string"


# ---------------------------------------------------------------------------
# Service: disk fallback in get_job()
# ---------------------------------------------------------------------------

def test_get_job_disk_fallback(isolated_projects_dir):
    """When job is not in _JOBS but analysis.md exists, get_job returns a
    synthetic dict with done=True, the analysis text, braindump text,
    project_id, and share_slug."""
    job_id = "test-disk-fallback-123"
    project_dir = isolated_projects_dir / job_id
    project_dir.mkdir()

    analysis_text = "# Analysis\n\n## The Problem\nSomething is broken."
    braindump_text = "Everything is broken, please fix."
    meta = {
        "name": "Test Project",
        "createdAt": "2025-01-01T00:00:00.000Z",
        "anonymous": True,
        "shareSlug": "fallback-share-slug",
    }
    (project_dir / "analysis.md").write_text(analysis_text, encoding="utf-8")
    (project_dir / "braindump.md").write_text(braindump_text, encoding="utf-8")
    (project_dir / "project.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )

    # Ensure the job is not in the in-memory store.
    svc._JOBS.pop(job_id, None)

    result = svc.get_job(job_id)
    assert result is not None, "get_job must return a dict when analysis.md exists on disk"
    assert result["done"] is True
    assert result["running"] is False
    assert result["analysis"] == analysis_text
    assert result["braindump"] == braindump_text
    assert result["project_id"] == job_id
    assert result["share_slug"] == "fallback-share-slug"
    assert result["error"] is None


def test_get_job_disk_fallback_missing_project(isolated_projects_dir):
    """When job is not in _JOBS and no directory exists, get_job returns None."""
    job_id = "non-existent-project-xyz"
    svc._JOBS.pop(job_id, None)
    assert svc.get_job(job_id) is None


# ---------------------------------------------------------------------------
# Route: POST returns project_id and share_slug
# ---------------------------------------------------------------------------

def test_post_returns_project_id_and_share_slug(app):
    """POST /api/public/analyze must return 202 with job_id, project_id,
    and share_slug in the response body."""
    patch_target = "modules.ai.routes.public_analyze.start_analysis"
    with mock.patch(patch_target, return_value=("my-project-id", "my-share-slug")):
        resp = app.test_client().post(
            "/api/public/analyze",
            json={"braindump": "Build something interesting"},
        )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["job_id"] == "my-project-id"
    assert body["project_id"] == "my-project-id"
    assert body["share_slug"] == "my-share-slug"


# ---------------------------------------------------------------------------
# Route: GET status includes project_id and share_slug
# ---------------------------------------------------------------------------

def test_get_status_includes_project_id_and_share_slug(app):
    """GET /api/public/analyze/<job_id> must include project_id and share_slug
    in the response JSON."""
    job_id = "status-test-job-abc"
    with svc._LOCK:
        svc._JOBS[job_id] = {
            "running": False,
            "done": True,
            "analysis": "# Analysis\n\nDone.",
            "error": None,
            "project_id": job_id,
            "braindump": "My braindump",
            "share_slug": "status-share-slug",
            "started_at": time.time(),
        }

    resp = app.test_client().get(f"/api/public/analyze/{job_id}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["project_id"] == job_id
    assert body["share_slug"] == "status-share-slug"
    assert body["done"] is True
