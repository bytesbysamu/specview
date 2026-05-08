# modules/task_gen/tests/test_routes.py
"""Integration tests for /api/projects/<id>/generate-task and /status.

Uses CHAIN_PROVIDER=mock so no real AI call is made. Each test sets
PROJECTS_DIR to tmp_path and seeds a project directory by hand to keep
the tests independent of higher-level service plumbing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from modules.ai.services import task_gen as _svc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EPIC_FIXTURE = """\
# Epic: Two Levers

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Raise CLI Timeout** | None | — | 0.5 days | High |
| 2 | **Generate-Task Routes** | Task 1 | — | 2 days | High |

### Task 1: Raise CLI Timeout
Single-line change in cli.py.

### Task 2: Generate-Task Routes
Two Flask routes plus a background thread.
"""


@pytest.fixture()
def project_id() -> str:
    return "two-levers-1700000000000"


@pytest.fixture()
def seeded_project(tmp_path: Path, project_id: str, monkeypatch) -> Path:
    """Create a project directory with epic.md and project.json. Returns tmp_path (projects root)."""
    proj = tmp_path / project_id
    proj.mkdir()
    (proj / "project.json").write_text(
        json.dumps({"name": "Two Levers", "createdAt": "2024-01-15T10:00:00.000Z"}),
        encoding="utf-8",
    )
    (proj / "epic.md").write_text(EPIC_FIXTURE, encoding="utf-8")
    (proj / "architecture.md").write_text("# Architecture\nSome arch.\n", encoding="utf-8")
    # Repoint the route module's _PROJECTS_PATH to the tmp dir
    import modules.ai.routes.task_gen as routes_module
    monkeypatch.setattr(routes_module, "_PROJECTS_PATH", tmp_path)
    return tmp_path


@pytest.fixture()
def app(seeded_project: Path):
    from create_app import create_app
    flask_app = create_app({"TESTING": True})
    return flask_app


@pytest.fixture()
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state(project_id: str):
    """Wipe in-process state between tests so they don't leak."""
    _svc._EXECUTIONS.clear()
    yield
    _svc._EXECUTIONS.clear()


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch):
    """Force the chain adapter to use the mock provider — no real CLI call."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")


def waitForDone(client, project_id, timeout_s=5.0):
    """Poll /status until done=True. Returns final body."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        r = client.get(f"/api/projects/{project_id}/generate-task/status")
        body = r.get_json()
        if body.get("done"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"Thread did not finish within {timeout_s}s; last body={body}")


# ---------------------------------------------------------------------------
# POST /api/projects/<id>/generate-task — happy path
# ---------------------------------------------------------------------------

def post_generateTask_validProject_returns202AndStarted(client, project_id, seeded_project):
    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202, r.get_data(as_text=True)
    body = r.get_json()
    assert body == {"started": True}
    # Wait for the thread to settle so it doesn't bleed into other tests
    waitForDone(client, project_id)


def post_generateTask_unknownProject_returns404(client):
    r = client.post("/api/projects/does-not-exist/generate-task")
    assert r.status_code == 404


def post_generateTask_alreadyRunning_returns409AndAlreadyRunning(client, project_id, seeded_project, monkeypatch):
    """Double-POST: simulate an in-flight thread by pre-seeding _EXECUTIONS."""
    from modules.runtime.workflows.execution import WorkflowExecution

    exc = WorkflowExecution(workflow_ref=f"task_gen/{project_id}", inputs={})
    exc.start()  # NEW → IN_PROGRESS so is_running == True
    _svc._EXECUTIONS[_svc._slot(project_id, "__pending__")] = exc

    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 409
    body = r.get_json()
    assert body.get("started") is False
    assert body.get("alreadyRunning") is True


# ---------------------------------------------------------------------------
# GET /api/projects/<id>/generate-task/status — shape + state transitions
# ---------------------------------------------------------------------------

def status_noJobEverStarted_returnsRunningFalseDoneFalse(client, project_id):
    r = client.get(f"/api/projects/{project_id}/generate-task/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body == {"running": False, "done": False}


def status_afterCompletion_includesFilenameAndTaskMeta(client, project_id, seeded_project):
    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert body["running"] is False
    assert body["filename"] == "task-1-raise-cli-timeout.md"
    assert body["taskNum"] == "1"
    assert body["taskName"] == "Raise CLI Timeout"
    # Output file actually written
    out = (seeded_project / project_id / "task-1-raise-cli-timeout.md").read_text(encoding="utf-8")
    assert out.strip()  # mock provider wrote valid non-empty content


def status_allTasksAlreadyHaveFiles_returnsAllDoneTrue(client, project_id, seeded_project):
    """Pre-create both task files so the thread should immediately set allDone."""
    proj = seeded_project / project_id
    (proj / "task-1-raise-cli-timeout.md").write_text("done", encoding="utf-8")
    (proj / "task-2-generate-task-routes.md").write_text("done", encoding="utf-8")

    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert body.get("allDone") is True
    # No filename/taskNum when allDone
    assert "filename" not in body


def status_threadCapturesError_returnsErrorString(client, project_id, seeded_project, monkeypatch):
    """Force the chain adapter to raise; the thread should catch and surface error."""
    from modules.runtime.chain import adapter as chain_adapter

    def _boom(system, prompt, **kwargs):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(chain_adapter, "generate", _boom)

    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert body["running"] is False
    assert "synthetic failure" in body.get("error", "")
