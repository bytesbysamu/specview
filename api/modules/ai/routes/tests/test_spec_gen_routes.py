"""Tests for POST /api/spec-gen/generate.

Strategy:
- Unit tests mock WorkflowRuntime to avoid AI calls.
- All tests use a minimal Flask test client from create_app().
- The fixture stubs app.workflow_repository so workflow loading is deterministic.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from modules.runtime.workflows.steps import StepCompleted, StepFailed
from modules.runtime.workflows.workflow import Workflow


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def app():
    """Flask app in test mode with a stubbed workflow_repository."""
    from create_app import create_app as createApp

    application = createApp({"TESTING": True})

    stub_repo = MagicMock()
    stub_workflow = MagicMock(spec=Workflow)
    stub_repo.get.return_value = stub_workflow

    application.workflow_repository = stub_repo
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def validBody(**overrides) -> dict:
    base = {
        "project_name": "Test Project",
        "braindump": "We need to build a thing.",
        "builder": "",
        "principles": "",
        "codebase": "",
        "references": "",
    }
    base.update(overrides)
    return base


def makeCompletedEvents(outputs: dict) -> list:
    """Produce StepCompleted events for each step name → output mapping."""
    return [
        StepCompleted(
            step_name=name,
            run_id="test-run-id",
            started_at=0.0,
            completed_at=0.1,
            latency_ms=100,
            output=text,
        )
        for name, text in outputs.items()
    ]


# ── Happy path ────────────────────────────────────────────────────────────────


def test_generate_returns_200_with_three_files(client):
    events = makeCompletedEvents(
        {
            "analysis": "# Analysis",
            "epic": "# Epic",
            "architecture": "# Architecture",
        }
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=validBody())

    assert resp.status_code == 200
    data = resp.get_json()
    assert "files" in data
    filenames = {f["filename"] for f in data["files"]}
    assert filenames == {"analysis.md", "epic.md", "architecture.md"}


def test_generate_file_contents_match_step_outputs(client):
    events = makeCompletedEvents(
        {
            "analysis": "# Analysis content",
            "epic": "# Epic content",
            "architecture": "# Architecture content",
        }
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=validBody())

    files = {f["filename"]: f["content"] for f in resp.get_json()["files"]}
    assert files["analysis.md"] == "# Analysis content"
    assert files["epic.md"] == "# Epic content"
    assert files["architecture.md"] == "# Architecture content"


def test_generate_returns_latency_ms(client):
    events = makeCompletedEvents(
        {"analysis": "a", "epic": "e", "architecture": "ar"}
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=validBody())

    data = resp.get_json()
    assert isinstance(data["latencyMs"], int)
    assert data["latencyMs"] >= 0


def test_generate_passes_inputs_to_execution(client, app):
    """WorkflowExecution receives all six input keys."""
    events = makeCompletedEvents(
        {"analysis": "a", "epic": "e", "architecture": "ar"}
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime, patch(
        "modules.ai.routes.spec_gen.WorkflowExecution"
    ) as MockExec:
        MockRuntime.return_value.run.return_value = iter(events)
        MockExec.return_value = MagicMock()
        client.post(
            "/api/spec-gen/generate",
            json=validBody(
                builder="my builder",
                principles="p",
                codebase="c",
                references="r",
            ),
        )

    call_kwargs = MockExec.call_args.kwargs
    inputs = call_kwargs["inputs"]
    assert inputs["project_name"] == "Test Project"
    assert inputs["braindump"] == "We need to build a thing."
    assert inputs["builder"] == "my builder"
    assert inputs["principles"] == "p"
    assert inputs["codebase"] == "c"
    assert inputs["references"] == "r"


def test_generate_loads_correct_workflow_name(client, app):
    events = makeCompletedEvents(
        {"analysis": "a", "epic": "e", "architecture": "ar"}
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        client.post("/api/spec-gen/generate", json=validBody())

    app.workflow_repository.get.assert_called_once_with("spec_gen/generate-spec")


def test_generate_uses_context_fallback_when_request_fields_empty(client, app):
    """Empty builder/principles/codebase/references fall back to read_context()."""
    events = makeCompletedEvents(
        {"analysis": "a", "epic": "e", "architecture": "ar"}
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime, patch(
        "modules.ai.routes.spec_gen.read_context"
    ) as mock_ctx, patch(
        "modules.ai.routes.spec_gen.WorkflowExecution"
    ) as MockExec:
        mock_ctx.side_effect = lambda key: f"ctx-{key}"
        MockRuntime.return_value.run.return_value = iter(events)
        MockExec.return_value = MagicMock()
        client.post("/api/spec-gen/generate", json=validBody())

    inputs = MockExec.call_args.kwargs["inputs"]
    assert inputs["builder"] == "ctx-builder"
    assert inputs["principles"] == "ctx-principles"
    assert inputs["codebase"] == "ctx-codebase"
    assert inputs["references"] == "ctx-references"


def test_generate_extracts_text_from_chain_result_output(client):
    """AICall._invoke returns a ChainResult; the route reads .text for each file."""

    class _FakeChainResult:
        def __init__(self, text: str) -> None:
            self.text = text

    events = makeCompletedEvents(
        {
            "analysis": _FakeChainResult("# Analysis from CR"),
            "epic": _FakeChainResult("# Epic from CR"),
            "architecture": _FakeChainResult("# Arch from CR"),
        }
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=validBody())

    files = {f["filename"]: f["content"] for f in resp.get_json()["files"]}
    assert files["analysis.md"] == "# Analysis from CR"
    assert files["epic.md"] == "# Epic from CR"
    assert files["architecture.md"] == "# Arch from CR"


# ── Step failure ──────────────────────────────────────────────────────────────


def test_generate_returns_502_on_step_failed(client):
    fail_event = StepFailed(
        step_name="analysis",
        run_id="test-run-id",
        started_at=0.0,
        failed_at=0.05,
        latency_ms=50,
        error="provider timeout",
    )
    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter([fail_event])
        resp = client.post("/api/spec-gen/generate", json=validBody())

    assert resp.status_code == 502
    data = resp.get_json()
    assert data["error"] == "provider timeout"
    assert data["step"] == "analysis"


def test_generate_halts_after_first_step_failed(client):
    """Runtime generator is not further drained after a StepFailed."""
    fail_event = StepFailed(
        step_name="analysis",
        run_id="x",
        started_at=0.0,
        failed_at=0.01,
        latency_ms=10,
        error="boom",
    )
    exhausted = []

    def gen():
        yield fail_event
        exhausted.append(True)  # must not reach here

    with patch("modules.ai.routes.spec_gen.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = gen()
        client.post("/api/spec-gen/generate", json=validBody())

    assert not exhausted, "generator was drained past StepFailed"


# ── Validation ────────────────────────────────────────────────────────────────


def test_generate_returns_422_when_braindump_missing(client):
    resp = client.post("/api/spec-gen/generate", json={"project_name": "P"})
    assert resp.status_code == 422


def test_generate_returns_422_when_project_name_missing(client):
    resp = client.post("/api/spec-gen/generate", json={"braindump": "B"})
    assert resp.status_code == 422


def test_generate_returns_422_when_body_empty(client):
    resp = client.post("/api/spec-gen/generate", json={})
    assert resp.status_code == 422


# ── Workflow not found ────────────────────────────────────────────────────────


def test_generate_returns_404_when_workflow_not_registered(app, client):
    """Missing workflow → WorkflowNotFound → 404 via blueprint error handler."""
    from modules.runtime.workflows.repository import WorkflowNotFound

    app.workflow_repository.get.side_effect = WorkflowNotFound(
        "spec_gen/generate-spec"
    )
    resp = client.post("/api/spec-gen/generate", json=validBody())
    assert resp.status_code == 404
    assert "spec_gen/generate-spec" in resp.get_json()["error"]


# ── Workflow registration ─────────────────────────────────────────────────────


def test_register_workflows_saves_generate_spec():
    """register_workflows calls repo.save with the correct workflow name."""
    from modules.ai.workflows.spec_gen.generate_spec import register_workflows

    stub_repo = MagicMock()
    register_workflows(stub_repo)

    stub_repo.save.assert_called_once()
    saved_workflow = stub_repo.save.call_args.args[0]
    assert saved_workflow.ref.name == "generate-spec"


def test_workflow_has_three_steps():
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    assert w.step_count == 3
    assert w.steps[0].name == "analysis"
    assert w.steps[1].name == "epic"
    assert w.steps[2].name == "architecture"


def test_workflow_declares_required_inputs():
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    assert set(w.inputs) == {
        "braindump",
        "project_name",
        "builder",
        "principles",
        "codebase",
        "references",
    }


def test_workflow_declares_outputs():
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    assert set(w.outputs) == {"analysis", "epic", "architecture"}


def test_analysis_step_input_keys_subset_of_workflow_inputs():
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    analysis_step = w.steps[0]
    assert set(analysis_step.input_keys) <= set(w.inputs)


def test_epic_step_takes_analysis_output():
    """The epic prompt template references {analysis} from the prior step's output.

    Prior-step outputs are resolved at AICall._invoke time via the merged
    ``{outputs, inputs}`` dict; they intentionally do not appear in the
    step's input_keys (which gates only workflow-level inputs).
    """
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    epic_step = w.steps[1]
    assert "{analysis}" in epic_step.prompt_template


def test_architecture_step_takes_epic_output():
    """The architecture prompt template references {epic} from the prior step."""
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    arch_step = w.steps[2]
    assert "{epic}" in arch_step.prompt_template


def test_each_step_has_distinct_name():
    """Step names double as output keys in context.outputs — they must be unique."""
    from modules.ai.workflows.spec_gen.generate_spec import _build_workflow

    w = _build_workflow()
    names = [s.name for s in w.steps]
    assert len(names) == len(set(names)), (
        f"duplicate step name across steps: {names}"
    )


# ── Prompt format strings ────────────────────────────────────────────────────


def test_analysis_user_template_renders_without_error():
    from modules.ai.prompts.spec_gen import ANALYSIS_USER

    ctx = {"braindump": "test dump", "project_name": "My Project", "builder": ""}
    rendered = ANALYSIS_USER.format(**ctx)
    assert "My Project" in rendered
    assert "test dump" in rendered


def test_epic_user_template_renders_with_prior_analysis():
    from modules.ai.prompts.spec_gen import EPIC_USER

    ctx = {
        "braindump": "bd",
        "project_name": "P",
        "builder": "",
        "principles": "",
        "analysis": "# Analysis",
    }
    rendered = EPIC_USER.format(**ctx)
    assert "# Analysis" in rendered
    assert "Epic: P" in rendered


def test_architecture_user_template_renders_with_epic():
    from modules.ai.prompts.spec_gen import ARCHITECTURE_USER

    ctx = {
        "braindump": "bd",
        "project_name": "P",
        "builder": "",
        "principles": "",
        "epic": "# Epic",
        "codebase": "",
        "references": "",
    }
    rendered = ARCHITECTURE_USER.format(**ctx)
    assert "# Epic" in rendered
