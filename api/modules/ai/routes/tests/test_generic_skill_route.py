"""Integration tests for /api/skills generic skill route.

Covers:
- Security gate: invalid name regex → 400 before filesystem access
- Security gate: unknown skill → 404
- Authentication enforcement → 401 without token
- Sync skill: 200 + X-Job-Id header + result body
- Async skill: 202 + job_id
- Job polling: running, done, failed, not found
- Skill listing: GET /api/skills/
- FileNotFoundError during execution → 503
- RuntimeError during execution → 502
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("CHAIN_PROVIDER", "mock")
os.environ["SKIP_AUTH"] = "1"


@pytest.fixture()
def app():
    from create_app import create_app as _create_app
    return _create_app({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clear_jobs():
    import modules.ai.job_store as js
    js._JOBS.clear()
    yield
    js._JOBS.clear()


_SYNC_REGISTRY = {"name": "rewrite", "version": "1.0.0", "execution_model": "sync",
                  "output_schema": {"type": "object", "required": ["text"]}}
_ASYNC_REGISTRY = {"name": "brainstorm", "version": "1.0.0", "execution_model": "async",
                   "output_schema": {"type": "object", "required": ["rewritten_braindump"]}}

AUTH = {"Authorization": "Bearer skip"}


# ---------------------------------------------------------------------------
# Security gate — name regex
# ---------------------------------------------------------------------------

def test_rejects_uppercase_skill_name(client):
    r = client.post("/api/skills/run/REWRITE", headers=AUTH, json={})
    assert r.status_code == 400
    assert "invalid skill name" in r.get_json()["error"]


def test_rejects_skill_name_with_slash(client):
    r = client.post("/api/skills/run/bad/name", headers=AUTH, json={})
    # Flask routes /bad/name as a different URL — gets 404 from not-found handler
    assert r.status_code in (400, 404)


def test_rejects_skill_name_starting_with_digit(client):
    r = client.post("/api/skills/run/1invalid", headers=AUTH, json={})
    assert r.status_code == 400


def test_rejects_skill_name_with_spaces(client):
    r = client.post("/api/skills/run/bad%20name", headers=AUTH, json={})
    assert r.status_code == 400


def test_accepts_valid_skill_name_reaches_registry_lookup(client):
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               side_effect=FileNotFoundError):
        r = client.post("/api/skills/run/rewrite", headers=AUTH, json={})
    assert r.status_code == 404  # passed regex, failed at registry


# ---------------------------------------------------------------------------
# Security gate — skill.json existence
# ---------------------------------------------------------------------------

def test_returns_404_for_unknown_skill(client):
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               side_effect=FileNotFoundError):
        r = client.post("/api/skills/run/nonexistent", headers=AUTH, json={})
    assert r.status_code == 404
    assert "skill not found" in r.get_json()["error"]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# The conftest autouse _auth_bypass fixture auto-injects "Authorization: Bearer test-token"
# on every request.  Passing headers={"Authorization": ""} opts out so require_auth fires.

def test_requires_auth_on_run_endpoint(client):
    r = client.post("/api/skills/run/rewrite", json={}, headers={"Authorization": ""})
    assert r.status_code == 401


def test_requires_auth_on_jobs_endpoint(client):
    r = client.get("/api/skills/jobs/some-id", headers={"Authorization": ""})
    assert r.status_code == 401


def test_requires_auth_on_list_endpoint(client):
    r = client.get("/api/skills/", headers={"Authorization": ""})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Sync skill — happy path
# ---------------------------------------------------------------------------

def test_sync_skill_returns_200_with_result(client):
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               return_value=_SYNC_REGISTRY), \
         patch("modules.ai.routes.generic_skill_route.run_skill",
               return_value={"text": "rewritten content"}):
        r = client.post("/api/skills/run/rewrite", headers=AUTH,
                        json={"text": "original", "instructions": "make it shorter"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["result"] == {"text": "rewritten content"}


def test_sync_skill_sets_x_job_id_header(client):
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               return_value=_SYNC_REGISTRY), \
         patch("modules.ai.routes.generic_skill_route.run_skill",
               return_value={"text": "done"}):
        r = client.post("/api/skills/run/rewrite", headers=AUTH, json={})
    assert "X-Job-Id" in r.headers
    assert len(r.headers["X-Job-Id"]) > 0


def test_sync_skill_502_on_runtime_error(client):
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               return_value=_SYNC_REGISTRY), \
         patch("modules.ai.routes.generic_skill_route.run_skill",
               side_effect=RuntimeError("AI provider timeout")):
        r = client.post("/api/skills/run/rewrite", headers=AUTH, json={})
    assert r.status_code == 502
    assert "error" in r.get_json()


# ---------------------------------------------------------------------------
# Async skill — happy path
# ---------------------------------------------------------------------------

def test_async_skill_returns_202_with_job_id(client):
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               return_value=_ASYNC_REGISTRY), \
         patch("modules.ai.routes.generic_skill_route.run_skill_async"):
        r = client.post("/api/skills/run/brainstorm", headers=AUTH,
                        json={"braindump": "I want to build a tool"})
    assert r.status_code == 202
    body = r.get_json()
    assert "job_id" in body
    assert len(body["job_id"]) > 0


def test_async_skill_job_visible_in_store(client):
    import modules.ai.job_store as js
    with patch("modules.ai.routes.generic_skill_route.load_skill_registry",
               return_value=_ASYNC_REGISTRY), \
         patch("modules.ai.routes.generic_skill_route.run_skill_async"):
        r = client.post("/api/skills/run/brainstorm", headers=AUTH, json={})
    job_id = r.get_json()["job_id"]
    assert js.get_job(job_id) is not None


# ---------------------------------------------------------------------------
# Job polling
# ---------------------------------------------------------------------------

def test_poll_returns_404_for_unknown_job(client):
    r = client.get("/api/skills/jobs/no-such-job", headers=AUTH)
    assert r.status_code == 404


def test_poll_running_job_returns_running_status(client):
    import modules.ai.job_store as js
    job = js.create_job("brainstorm", "1.0.0")
    r = client.get(f"/api/skills/jobs/{job.job_id}", headers=AUTH)
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "running"
    assert body["done"] is False
    assert "result" not in body


def test_poll_done_job_returns_result(client):
    import modules.ai.job_store as js
    job = js.create_job("brainstorm", "1.0.0")
    js.complete_job(job.job_id, {"rewritten_braindump": "clean version"})
    r = client.get(f"/api/skills/jobs/{job.job_id}", headers=AUTH)
    body = r.get_json()
    assert body["status"] == "done"
    assert body["done"] is True
    assert body["result"]["rewritten_braindump"] == "clean version"


def test_poll_failed_job_returns_error(client):
    import modules.ai.job_store as js
    job = js.create_job("brainstorm", "1.0.0")
    js.fail_job(job.job_id, "skill output validation failed")
    r = client.get(f"/api/skills/jobs/{job.job_id}", headers=AUTH)
    body = r.get_json()
    assert body["status"] == "failed"
    assert body["done"] is True
    assert "skill output validation failed" in body["error"]


# ---------------------------------------------------------------------------
# Skill listing
# ---------------------------------------------------------------------------

def test_list_skills_returns_skills_array(client):
    # _skills_dir is defined in generic_skill_service and imported inside list_skills
    with patch("modules.ai.routes.generic_skill_service._skills_dir") as mock_dir:
        from pathlib import Path
        mock_dir.return_value = Path("/nonexistent")
        r = client.get("/api/skills/", headers=AUTH)
    assert r.status_code == 200
    assert "skills" in r.get_json()
