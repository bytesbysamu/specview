"""Integration tests for the bootstrap-project endpoints in modules/ai/routes/text.py.

Tests verify:
  - Authentication enforcement (401 without token)
  - Input validation (422 on missing required fields)
  - Happy-path 202 acceptance
  - Status and cancel/retry route guards
  - Retry usage-limit enforcement (429 on quota exhaustion)
  - Retry 404 when job_id not registered
  - Retry 202 with fresh job_id on valid request
"""
from __future__ import annotations

import os
import time as _time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# Force mock provider before create_app imports the chain module.
os.environ.setdefault("CHAIN_PROVIDER", "mock")

from modules.runtime.chain.adapter import DEFAULT_MODEL
from modules.runtime.workflows.execution import WorkflowExecution
from modules.runtime.workflows.workflow import Workflow


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
# POST /api/ai/text/bootstrap-project/<job_id>/retry — usage limit
# ---------------------------------------------------------------------------

def test_bootstrap_retry_returns_429_when_quota_exhausted(client, monkeypatch):
    """Free-tier user with no remaining quota gets 429 from the retry route."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    from modules.auth.models import User

    # Seed a prior job so we get past the job-lookup guard.
    prior = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={"project_name": "P", "braindump": "b"},
    )
    _BOOTSTRAP_JOBS["quota-retry-job"] = prior

    # Override the fake user injected by conftest with a free-tier user so
    # check_usage_limit will not short-circuit for pro plan.
    free_user = User(id=99, auth_user_id="free-user", email="free@example.com", plan="free")
    import modules.auth.decorators as _decorators
    monkeypatch.setattr(_decorators, "_load_user", lambda uid: free_user)

    # Drive the usage decorator: DB session is mocked; remaining = 0 triggers 429.
    @contextmanager
    def _fake_get_session():
        yield MagicMock()

    monkeypatch.setattr("modules.usage.decorators.get_session", _fake_get_session)
    monkeypatch.setattr("modules.usage.decorators.get_remaining", lambda uid, feat, sess: 0)

    response = client.post(
        "/api/ai/text/bootstrap-project/quota-retry-job/retry",
        json={"step": "analysis"},
    )
    assert response.status_code == 429, (
        f"Expected 429; got {response.status_code} body={response.get_json()}"
    )
    body = response.get_json()
    assert body.get("error") == "free_tier_limit_reached"
    assert body.get("feature") == "bootstrap"


def test_bootstrap_retry_returns_404_when_job_not_found(client):
    """Retry for an unknown job_id returns 404 — _BOOTSTRAP_JOBS miss."""
    response = client.post(
        "/api/ai/text/bootstrap-project/no-such-job-xyz/retry",
        json={"step": "epic"},
    )
    assert response.status_code == 404, (
        f"Expected 404; got {response.status_code} body={response.get_json()}"
    )
    body = response.get_json()
    assert "job not found" in body.get("error", "")


def test_bootstrap_retry_returns_202_with_new_job_id(client, app):
    """Valid retry against a completed job returns 202 with a fresh job_id."""
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    # Seed a completed prior execution that has an analysis output — the
    # "epic" retry step needs this as its upstream dependency.
    prior = WorkflowExecution(
        workflow_ref="ai/bootstrap-project",
        inputs={
            "project_name": "RetryP",
            "braindump": "build a thing",
            "builder": "",
            "principles": "",
            "codebase": "",
            "references": "",
        },
    )
    prior.outputs["analysis"] = MagicMock(text="## Analysis content")
    _BOOTSTRAP_JOBS["prior-complete-job"] = prior

    # Stub workflow_repository so the route can resolve the sub-workflow ref.
    stub_workflow = MagicMock(spec=Workflow)
    app.workflow_repository = MagicMock()
    app.workflow_repository.get.return_value = stub_workflow

    with patch("modules.ai.routes.text.threading.Thread") as MockThread:
        MockThread.return_value = MagicMock()

        response = client.post(
            "/api/ai/text/bootstrap-project/prior-complete-job/retry",
            json={"step": "epic"},
        )

    assert response.status_code == 202, (
        f"Expected 202; got {response.status_code} body={response.get_json()}"
    )
    body = response.get_json()
    assert "job_id" in body
    new_job_id = body["job_id"]
    assert isinstance(new_job_id, str) and len(new_job_id) > 0
    # The new job_id must differ from the original.
    assert new_job_id != "prior-complete-job"
    # A new WorkflowExecution must be registered for the returned job_id.
    assert new_job_id in _BOOTSTRAP_JOBS
    # The retry route must have constructed and started exactly one daemon thread.
    assert MockThread.call_count == 1, (
        f"Expected 1 Thread construction; got {MockThread.call_count}"
    )
    MockThread.return_value.start.assert_called_once()


# ---------------------------------------------------------------------------
# Cooperative cancellation — Task 4
# ---------------------------------------------------------------------------

class TestCancellation:
    """Tests for cooperative cancellation wiring in _run_bootstrap_thread and bootstrap_status."""

    def test_status_response_includes_status_field_when_cancelling(self, client):
        """Poll response always includes `status` field; CANCELLING is visible before terminal."""
        from modules.ai.routes.text import _BOOTSTRAP_JOBS
        from modules.runtime.workflows.execution import ExecutionStatus

        execution = WorkflowExecution(
            workflow_ref="ai/bootstrap-project",
            inputs={"project_name": "CancelP"},
        )
        execution.start()
        execution.request_cancel()  # IN_PROGRESS -> CANCELLING
        _BOOTSTRAP_JOBS["cancelling-job"] = execution

        response = client.get("/api/ai/text/bootstrap-project/status/cancelling-job")
        assert response.status_code == 200
        body = response.get_json()
        assert "status" in body, "poll response must always include 'status'"
        assert body["status"] == ExecutionStatus.CANCELLING.value
        # Not yet terminal — done must be False.
        assert body["done"] is False

    def test_status_response_done_true_and_status_cancelled_on_terminal(self, client):
        """Once cancelled (terminal), done=true and status=CANCELLED in poll response."""
        from modules.ai.routes.text import _BOOTSTRAP_JOBS
        from modules.runtime.workflows.execution import ExecutionStatus

        execution = WorkflowExecution(
            workflow_ref="ai/bootstrap-project",
            inputs={"project_name": "CancelP"},
        )
        execution.start()
        execution.request_cancel()  # IN_PROGRESS -> CANCELLING
        execution.cancel()          # CANCELLING -> CANCELLED
        _BOOTSTRAP_JOBS["cancelled-job"] = execution

        response = client.get("/api/ai/text/bootstrap-project/status/cancelled-job")
        assert response.status_code == 200
        body = response.get_json()
        assert body["done"] is True
        assert body["status"] == ExecutionStatus.CANCELLED.value

    def test_status_response_includes_failed_step_on_error(self, client):
        """When status is ERROR, poll response contains `failed_step` set to current_step_name."""
        from modules.ai.routes.text import _BOOTSTRAP_JOBS
        from modules.runtime.workflows.execution import ExecutionStatus

        execution = WorkflowExecution(
            workflow_ref="ai/bootstrap-project",
            inputs={"project_name": "ErrorP"},
        )
        execution.start()
        execution.current_step_name = "epic"
        execution.fail("chain timeout")  # IN_PROGRESS -> ERROR
        _BOOTSTRAP_JOBS["error-job"] = execution

        response = client.get("/api/ai/text/bootstrap-project/status/error-job")
        assert response.status_code == 200
        body = response.get_json()
        assert body["done"] is True
        assert body["status"] == ExecutionStatus.ERROR.value
        assert "failed_step" in body, "ERROR response must include 'failed_step'"
        assert body["failed_step"] == "epic"
        assert body.get("error") == "chain timeout"

    def test_cancel_returns_409_when_job_already_completed(self, client):
        """POST cancel on a COMPLETED job returns 409 — cannot cancel a terminal execution."""
        from modules.ai.routes.text import _BOOTSTRAP_JOBS
        from modules.runtime.workflows.execution import ExecutionStatus

        execution = WorkflowExecution(
            workflow_ref="ai/bootstrap-project",
            inputs={"project_name": "DoneP"},
        )
        execution.start()
        execution.complete()  # IN_PROGRESS -> COMPLETED
        _BOOTSTRAP_JOBS["completed-job"] = execution

        response = client.post(
            "/api/ai/text/bootstrap-project/completed-job/cancel"
        )
        assert response.status_code == 409, (
            f"Expected 409 for completed job; got {response.status_code} body={response.get_json()}"
        )
        body = response.get_json()
        assert "cannot cancel" in body.get("error", "")
        assert body.get("status") == ExecutionStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# Provider/model selection — completes #125 (route exposure) + gateway guard
# ---------------------------------------------------------------------------
#
# These exercise the per-request provider/model override threaded from the
# bootstrap routes through chain_adapter.generate to the oll-model gateway
# payload, plus the gateway-only guard (a provider override on a non-gateway
# backend must not crash). They run the REAL bootstrap thread (no Thread mock)
# with requests.post patched, then poll the status endpoint until done.
#
# Helper names are camelCase with NO underscores so pytest's
# python_functions=["test_*", "*_*"] does not collect them as tests.


def pollUntilDone(client, statusUrl: str, timeoutS: float = 5.0) -> dict:
    """Poll a bootstrap status endpoint until done=true (or timeout). Returns the body.

    The status route evicts the job on the first terminal read, so the first
    done=true body is the one to assert on.
    """
    deadline = _time.monotonic() + timeoutS
    body: dict = {}
    while _time.monotonic() < deadline:
        body = client.get(statusUrl).get_json() or {}
        if body.get("done"):
            return body
        _time.sleep(0.02)
    return body


@contextmanager
def gatewayCapture(monkeypatch):
    """Point the chain at the gateway provider and capture every POSTed JSON body."""
    import requests

    monkeypatch.setenv("CHAIN_PROVIDER", "gateway")
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    posts: list[dict] = []

    def fake_post(url, headers, json, timeout):  # noqa: A002
        posts.append(json)
        resp = type("R", (), {})()
        resp.raise_for_status = lambda: None
        resp.json = lambda: {"text": "generated body", "tokens_in": 1, "tokens_out": 1}
        return resp

    monkeypatch.setattr(requests, "post", fake_post)
    yield posts


def provider_omitted_route_keepsGatewayPayloadDefault(client, monkeypatch):
    """(a) Omitting provider/model leaves the gateway payload at the chain
    default — no provider override key, model == chain DEFAULT_MODEL — proven
    end to end through the route (default behaviour unchanged)."""
    with gatewayCapture(monkeypatch) as posts:
        resp = client.post("/api/ai/text/bootstrap-project", json=_H.body())
        assert resp.status_code == 202, resp.get_json()
        job_id = resp.get_json()["job_id"]
        body = pollUntilDone(client, f"/api/ai/text/bootstrap-project/status/{job_id}")

    assert body.get("done") is True, body
    assert posts, "expected the bootstrap thread to call the gateway"
    for payload in posts:
        assert "provider" not in payload          # no caller provider override
        assert payload["model"] == DEFAULT_MODEL   # chain default, not a caller value


def provider_and_model_route_forwardsToGatewayPayload(client, monkeypatch):
    """(b) provider=ollama + model=... selected on the route reach the gateway
    /api/text/complete payload for every chain step."""
    with gatewayCapture(monkeypatch) as posts:
        resp = client.post(
            "/api/ai/text/bootstrap-project",
            json=_H.body(provider="ollama", model="llama3.2"),
        )
        assert resp.status_code == 202, resp.get_json()
        job_id = resp.get_json()["job_id"]
        body = pollUntilDone(client, f"/api/ai/text/bootstrap-project/status/{job_id}")

    assert body.get("done") is True, body
    assert posts, "expected the bootstrap thread to call the gateway"
    for payload in posts:
        assert payload["provider"] == "ollama"
        assert payload["model"] == "llama3.2"


def invalidProvider_route_returns400(client):
    """(c) An unknown provider is rejected with a clean 400 before any work starts."""
    resp = client.post(
        "/api/ai/text/bootstrap-project",
        json=_H.body(provider="gpt-4"),
    )
    assert resp.status_code == 400, resp.get_json()
    body = resp.get_json()
    assert body.get("error") == "invalid provider"
    assert sorted(body.get("allowed", [])) == ["claude", "groq", "ollama"]


def invalidProvider_anonymousRoute_returns400(client):
    """(c) Same 400 guard on the anonymous landing-page bootstrap route."""
    resp = client.post(
        "/api/ai/text/anonymous/bootstrap-project",
        json=_H.body(provider="nope"),
        headers={"Authorization": ""},  # anonymous route needs no auth
    )
    assert resp.status_code == 400, resp.get_json()
    assert resp.get_json().get("error") == "invalid provider"


def providerOverride_nonGatewayBackend_route_doesNotCrash(client, monkeypatch):
    """(d) The guard at the route level: a provider override while the active
    backend is the (non-gateway) mock provider must NOT 500 — the override is
    dropped and the bootstrap completes successfully."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    resp = client.post(
        "/api/ai/text/bootstrap-project",
        json=_H.body(provider="ollama", model="llama3.2"),
    )
    assert resp.status_code == 202, resp.get_json()
    job_id = resp.get_json()["job_id"]
    body = pollUntilDone(client, f"/api/ai/text/bootstrap-project/status/{job_id}")
    # done=true with files (not an error) proves no TypeError->500 in the thread.
    assert body.get("done") is True, body
    assert body.get("status") != "ERROR", body
    assert "files" in body, body
