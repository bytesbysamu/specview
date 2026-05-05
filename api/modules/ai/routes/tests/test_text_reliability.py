"""Tests for the cancel, retry, and extended polling response on bootstrap.

Covers Task 4 (saas-reliability):
  - bootstrap_cancel transitions IN_PROGRESS -> CANCELLING and returns 202
  - bootstrap_status surfaces current_step, partial, warnings on running jobs
  - bootstrap_retry validates step name, copies prior outputs as inputs,
    and spawns a new execution against the matching sub-workflow.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# Force the mock chain provider before create_app imports anything that
# touches the chain — matches the convention in test_task_gen_routes.py.
os.environ.setdefault("CHAIN_PROVIDER", "mock")

import create_app as _create_app_module  # noqa: E402
from modules.runtime.workflows.execution import (  # noqa: E402
    ExecutionStatus,
    WorkflowExecution,
)

# Alias without underscores avoids pytest collecting the imported callable.
createApp = _create_app_module.create_app


@pytest.fixture()
def app():
    return createApp({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_jobs():
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    _BOOTSTRAP_JOBS.clear()
    yield
    _BOOTSTRAP_JOBS.clear()


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def cancel_unknownJob_returns404(client):
    response = client.post("/api/ai/text/bootstrap-project/no-such-id/cancel")
    assert response.status_code == 404, (
        f"Expected 404 for unknown job; got {response.status_code}"
    )


def cancel_runningJob_returns202AndFlipsCancelling(client):
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    execution = WorkflowExecution(workflow_ref="spec_gen/bootstrap-project", inputs={})
    execution.start()
    _BOOTSTRAP_JOBS["job-1"] = execution

    response = client.post("/api/ai/text/bootstrap-project/job-1/cancel")
    assert response.status_code == 202, (
        f"Expected 202; got {response.status_code} body={response.get_json()}"
    )
    assert execution.status is ExecutionStatus.CANCELLING, (
        f"Expected CANCELLING; got {execution.status}"
    )


def cancel_completedJob_returns409(client):
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    execution = WorkflowExecution(workflow_ref="spec_gen/bootstrap-project", inputs={})
    execution.start()
    execution.complete()
    _BOOTSTRAP_JOBS["job-2"] = execution

    response = client.post("/api/ai/text/bootstrap-project/job-2/cancel")
    assert response.status_code == 409, (
        f"Expected 409 for completed job; got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Status (extended polling shape)
# ---------------------------------------------------------------------------

def status_runningJob_returnsCurrentStepAndPartial(client):
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    execution = WorkflowExecution(
        workflow_ref="spec_gen/bootstrap-project", inputs={"project_name": "p"},
    )
    execution.start()
    execution.current_step_name = "architecture"
    execution.outputs["_partials"] = {"architecture": "live tail text"}
    execution.warnings.append("unclosed_code_fence: 3 triple-backticks (odd)")
    _BOOTSTRAP_JOBS["job-3"] = execution

    response = client.get("/api/ai/text/bootstrap-project/status/job-3")
    body = response.get_json()
    assert response.status_code == 200, f"Expected 200; got {response.status_code}"
    assert body["running"] is True
    assert body["done"] is False
    assert body["current_step"] == "architecture"
    assert body["partial"] == "live tail text"
    assert "unclosed_code_fence" in body["warnings"][0]


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

def retry_invalidStep_returns400(client):
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    _BOOTSTRAP_JOBS["job-4"] = WorkflowExecution(
        workflow_ref="spec_gen/bootstrap-project", inputs={},
    )
    response = client.post(
        "/api/ai/text/bootstrap-project/job-4/retry",
        json={"step": "files"},
    )
    assert response.status_code == 400, (
        f"Expected 400 for invalid step; got {response.status_code}"
    )
    body = response.get_json()
    assert "analysis" in body["allowed"]
    assert "architecture" in body["allowed"]


def retry_unknownJob_returns404(client):
    response = client.post(
        "/api/ai/text/bootstrap-project/no-such/retry",
        json={"step": "architecture"},
    )
    assert response.status_code == 404


def retry_architectureStep_passesPriorOutputsAsInputs(client, app):
    """Verify retry constructs new_inputs from the prior execution's outputs.

    The retry handler reads ``prior.outputs`` and assigns ``analysis`` +
    ``epic`` text into the new execution's inputs before launching a thread.
    We capture the new execution at thread construction time without actually
    spawning the thread.
    """
    from modules.ai.routes.text import _BOOTSTRAP_JOBS

    class _FakeChainResult:
        def __init__(self, text: str):
            self.text = text

    prior = WorkflowExecution(
        workflow_ref="spec_gen/bootstrap-project",
        inputs={
            "braindump": "bd", "project_name": "p", "builder": "b",
            "principles": "pr", "codebase": "cb", "references": "rf",
        },
    )
    prior.outputs["analysis"] = _FakeChainResult("analysis-text")
    prior.outputs["epic"] = _FakeChainResult("epic-text")
    _BOOTSTRAP_JOBS["job-5"] = prior

    captured: dict = {}

    class _FakeThread:
        def __init__(self, **kwargs):
            execution = kwargs["args"][0]
            captured["inputs"] = dict(execution.inputs)

        def start(self):
            return None

    # Stub the workflow_repository.get so retry doesn't blow up in 503 land
    # when the Rel-T3 sub-workflows are not registered.
    class _StubWorkflow:
        ref = type("R", (), {"name": "bootstrap-architecture-only"})()

    with patch.object(
        app.workflow_repository, "get", return_value=_StubWorkflow(),
    ), patch("modules.ai.routes.text.threading.Thread", _FakeThread):
        response = client.post(
            "/api/ai/text/bootstrap-project/job-5/retry",
            json={"step": "architecture"},
        )

    assert response.status_code == 202, (
        f"Expected 202; got {response.status_code} body={response.get_json()}"
    )
    started_inputs = captured["inputs"]
    assert started_inputs.get("analysis") == "analysis-text", (
        f"Architecture retry must pass prior analysis text; got {started_inputs}"
    )
    assert started_inputs.get("epic") == "epic-text", (
        f"Architecture retry must pass prior epic text; got {started_inputs}"
    )
