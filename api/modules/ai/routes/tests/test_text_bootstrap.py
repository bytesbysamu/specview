"""Integration tests for the bootstrap-project endpoints in modules/ai/routes/text.py.

Tests verify:
  - Authentication enforcement (401 without token)
  - Input validation (422 on missing required fields)
  - Happy-path 202 acceptance
  - Status and cancel/retry route guards
  - Usage limit enforcement on retry endpoint
  - Cooperative cancellation state machine
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# Force mock provider before create_app imports the chain module.
os.environ.setdefault("CHAIN_PROVIDER", "mock")

from modules.runtime.workflows.execution import WorkflowExecution


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    from create_app import create_app as _create_app
    return _create_app({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_jobs():
    """Ensure _BOOTSTRAP_JOBS is empty before and after each test."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    _BOOTSTRAP_JOBS.clear()
    yield
    _BOOTSTRAP_JOBS.clear()


class _H:
    """Non-test helper namespace."""

    @staticmethod
    def body(**overrides) -> dict:
        base = {
            "project_name": "Test Bootstrap",
            "braindump": "We need to build a widget factory.",
        }
        base.update(overrides)
        return base


# ---------------------------------------------------------------------------
# POST /api/ai/text/bootstrap-project — auth
# ---------------------------------------------------------------------------

def test_bootstrap_project_returns_401_without_auth_token(client):
    """POST without Authorization header returns 401."""
    response = client.post(
        "/api/ai/text/bootstrap-project",
        json=_H.body(),
        headers={"Authorization": ""},  # opts out of the autouse bypass
    )
    assert response.status_code == 401, (
        f"Expected 401; got {response.status_code} body={response.get_json()}"
    )


# ---------------------------------------------------------------------------
# POST /api/ai/text/bootstrap-project — validation
# ---------------------------------------------------------------------------

def test_bootstrap_project_returns_422_when_project_name_missing(client):
    """Missing project_name triggers Pydantic ValidationError → 422."""
    response = client.post(
        "/api/ai/text/bootstrap-project",
        json={"braindump": "some text"},
    )
    assert response.status_code == 422, (
        f"Expected 422; got {response.status_code} body={response.get_json()}"
    )


def test_bootstrap_project_returns_422_when_braindump_missing(client):
    """Missing braindump triggers Pydantic ValidationError → 422."""
    response = client.post(
        "/api/ai/text/bootstrap-project",
        json={"project_name": "Test"},
    )
    assert response.status_code == 422, (
        f"Expected 422; got {response.status_code} body={response.get_json()}"
    )


# ---------------------------------------------------------------------------
# POST /api/ai/text/bootstrap-project — happy path
# ---------------------------------------------------------------------------

def test_bootstrap_project_returns_202_with_job_id(client):
    """Valid request returns 202 and a job_id string."""
    with patch("modules.ai.routes.text.threading.Thread") as MockThread:
        instance = MagicMock()
        MockThread.return_value = instance

        response = client.post(
            "/api/ai/text/bootstrap-project",
            json=_H.body(),
        )

    assert response.status_code == 202, (
        f"Expected 202; got {response.status_code} body={response.get_json()}"
    )
    body = response.get_json()
    assert "job_id" in body
    assert isinstance(body["job_id"], str)
    assert len(body["job_id"]) > 0


def test_bootstrap_project_creates_job_entry_in_bootstrap_jobs(client):
    """After a valid POST, a WorkflowExecution is stored in _BOOTSTRAP_JOBS."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    with patch("modules.ai.routes.text.threading.Thread") as MockThread:
        instance = MagicMock()
        MockThread.return_value = instance

        response = client.post(
            "/api/ai/text/bootstrap-project",
            json=_H.body(),
        )

    body = response.get_json()
    job_id = body["job_id"]

    assert job_id in _BOOTSTRAP_JOBS
    execution = _BOOTSTRAP_JOBS[job_id]
    assert isinstance(execution, WorkflowExecution)


# ---------------------------------------------------------------------------
# GET /api/ai/text/bootstrap-project/status/<job_id>
# ---------------------------------------------------------------------------

def test_bootstrap_status_returns_404_for_unknown_job_id(client):
    """GET status for an unregistered job_id returns 404."""
    response = client.get("/api/ai/text/bootstrap-project/status/no-such-job-xyz")
    assert response.status_code == 404, (
        f"Expected 404; got {response.status_code}"
    )


def test_bootstrap_status_returns_running_and_done_keys(client):
    """GET status for a known running job returns running and done keys."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    execution = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    execution.start()
    _BOOTSTRAP_JOBS["test-status-job"] = execution

    response = client.get("/api/ai/text/bootstrap-project/status/test-status-job")
    assert response.status_code == 200, (
        f"Expected 200; got {response.status_code}"
    )
    body = response.get_json()
    assert "running" in body
    assert "done" in body
    assert body["running"] is True
    assert body["done"] is False


# ---------------------------------------------------------------------------
# DELETE /api/ai/text/bootstrap-project/<job_id>/cancel — auth guard
# ---------------------------------------------------------------------------

def test_bootstrap_cancel_returns_401_without_auth(client):
    """POST cancel without Authorization header returns 401 (Critical fix verification)."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    execution = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={},
    )
    execution.start()
    _BOOTSTRAP_JOBS["cancel-auth-test"] = execution

    response = client.post(
        "/api/ai/text/bootstrap-project/cancel-auth-test/cancel",
        headers={"Authorization": ""},  # opts out of autouse bypass
    )
    assert response.status_code == 401, (
        f"Expected 401 (auth guard); got {response.status_code} body={response.get_json()}"
    )


# ---------------------------------------------------------------------------
# POST /api/ai/text/bootstrap-project/<job_id>/retry — auth guard
# ---------------------------------------------------------------------------

def test_bootstrap_retry_returns_401_without_auth(client):
    """POST retry without Authorization header returns 401 (Critical fix verification)."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    prior = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={},
    )
    _BOOTSTRAP_JOBS["retry-auth-test"] = prior

    response = client.post(
        "/api/ai/text/bootstrap-project/retry-auth-test/retry",
        json={"step": "analysis"},
        headers={"Authorization": ""},  # opts out of autouse bypass
    )
    assert response.status_code == 401, (
        f"Expected 401 (auth guard); got {response.status_code} body={response.get_json()}"
    )


# ---------------------------------------------------------------------------
# POST /api/ai/text/bootstrap-project/<job_id>/retry — Task 3: usage limit
# ---------------------------------------------------------------------------

def test_bootstrap_retry_returns_429_when_usage_limit_hit(client, monkeypatch):
    """Retry endpoint returns 429 when free-tier user has exhausted daily quota.

    The autouse _auth_bypass fixture returns plan='pro'; we override _load_user
    here to return a free-tier user so check_usage_limit actually enforces the cap.
    """
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    import modules.auth.decorators as _decorators
    from modules.auth.models import User

    def _free_user(user_id: int):
        return User(id=user_id, auth_user_id="free-test", email="free@example.com", plan="free")

    monkeypatch.setattr(_decorators, "_load_user", _free_user)

    prior = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    prior.start()
    _BOOTSTRAP_JOBS["retry-limit-test"] = prior

    mock_session = MagicMock()

    @contextmanager
    def _fake_session_ctx():
        yield mock_session

    with patch("modules.usage.decorators.get_remaining", return_value=0), \
         patch("modules.usage.decorators.get_session", _fake_session_ctx):
        response = client.post(
            "/api/ai/text/bootstrap-project/retry-limit-test/retry",
            json={"step": "analysis"},
        )

    assert response.status_code == 429, (
        f"Expected 429; got {response.status_code} body={response.get_json()}"
    )
    body = response.get_json()
    assert body.get("error") == "free_tier_limit_reached"


def test_bootstrap_retry_returns_404_when_job_not_found(client):
    """Retry endpoint returns 404 when job_id does not exist."""
    response = client.post(
        "/api/ai/text/bootstrap-project/no-such-job/retry",
        json={"step": "analysis"},
    )
    assert response.status_code == 404, (
        f"Expected 404; got {response.status_code} body={response.get_json()}"
    )


def test_bootstrap_retry_returns_202_with_new_job_id(client):
    """Retry endpoint returns 202 with a fresh job_id distinct from the original."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    prior = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    prior.start()
    # Seed prior analysis output so epic retry has its dependency
    prior.outputs["analysis"] = MagicMock(text="analysis content")
    prior.outputs["epic"] = MagicMock(text="epic content")
    _BOOTSTRAP_JOBS["retry-202-test"] = prior

    mock_workflow = MagicMock()
    mock_thread = MagicMock()

    with patch("modules.ai.routes.text.threading.Thread", return_value=mock_thread), \
         patch.object(client.application, "workflow_repository") as mock_repo:
        mock_repo.get.return_value = mock_workflow
        response = client.post(
            "/api/ai/text/bootstrap-project/retry-202-test/retry",
            json={"step": "epic"},
        )

    assert response.status_code == 202, (
        f"Expected 202; got {response.status_code} body={response.get_json()}"
    )
    body = response.get_json()
    assert "job_id" in body
    assert body["job_id"] != "retry-202-test", "New job_id must differ from original"
    mock_thread.start.assert_called_once()


# ---------------------------------------------------------------------------
# Task 4: Cooperative cancellation — status endpoint state machine
# ---------------------------------------------------------------------------

def test_bootstrap_status_reflects_cancelling_state(client):
    """Status endpoint returns 'cancelling' status when execution is in CANCELLING state."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    execution = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    execution.start()
    execution.request_cancel()  # IN_PROGRESS -> CANCELLING
    _BOOTSTRAP_JOBS["cancelling-test"] = execution

    response = client.get("/api/ai/text/bootstrap-project/status/cancelling-test")
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("status") == "CANCELLING"


def test_bootstrap_status_reflects_cancelled_terminal_state(client):
    """Status endpoint returns done=true and status='cancelled' after cancellation completes."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    execution = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    execution.start()
    execution.request_cancel()  # IN_PROGRESS -> CANCELLING
    execution.cancel()          # CANCELLING -> CANCELLED
    _BOOTSTRAP_JOBS["cancelled-test"] = execution

    response = client.get("/api/ai/text/bootstrap-project/status/cancelled-test")
    assert response.status_code == 200
    body = response.get_json()
    assert body["done"] is True
    assert body.get("status") == "CANCELLED"


def test_bootstrap_status_includes_failed_step_on_error(client):
    """Status endpoint includes 'failed_step' when execution is in ERROR state."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    execution = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    execution.start()
    execution.current_step_name = "epic"
    execution.fail("chain call failed")
    _BOOTSTRAP_JOBS["error-step-test"] = execution

    response = client.get("/api/ai/text/bootstrap-project/status/error-step-test")
    assert response.status_code == 200
    body = response.get_json()
    assert body["done"] is True
    assert body.get("failed_step") == "epic"


def test_bootstrap_cancel_returns_409_when_already_completed(client):
    """Cancel endpoint returns 409 when job has already completed."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    execution = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P"},
    )
    execution.start()
    execution.complete()  # IN_PROGRESS -> COMPLETED
    _BOOTSTRAP_JOBS["cancel-completed-test"] = execution

    response = client.post(
        "/api/ai/text/bootstrap-project/cancel-completed-test/cancel"
    )
    assert response.status_code == 409, (
        f"Expected 409; got {response.status_code} body={response.get_json()}"
    )
