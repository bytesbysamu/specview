"""Tests for the bootstrap workflow registry.

Asserts that all four workflows register, that each sub-workflow has
exactly one AICall step, that the input declarations match the
prompt-template format-map keys, and that the architecture step (parent
and architecture-only sub-workflow) opts into streaming.

Route-side wiring (`bootstrap_project()` loading the workflow from
`current_app.workflow_repository`) belongs to Rel-T4 and is not covered
here; this task ships only the workflow definitions.
"""
from __future__ import annotations

import pytest

import create_app as createAppModule
from modules.runtime.workflows.steps.ai_call import AICall


@pytest.fixture
def app():
    return createAppModule.create_app()


def bootstrapProject_isRegisteredWithFourSteps(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-project")
    step_names = [s.name for s in wf.steps]
    assert step_names == ["analysis", "epic", "architecture", "files"], (
        f"Expected 4-step parent workflow; got {step_names}"
    )


def analysisOnly_isRegisteredWithSingleStep(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-analysis-only")
    step_names = [s.name for s in wf.steps]
    assert step_names == ["analysis"], (
        f"Expected single-step analysis-only workflow; got {step_names}"
    )
    assert isinstance(wf.steps[0], AICall), (
        "analysis-only single step must be an AICall instance"
    )


def analysisOnly_inputsMatchParentAnalysisStep(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-analysis-only")
    assert wf.inputs == frozenset({"braindump", "project_name", "builder"}), (
        f"analysis-only workflow inputs must match the parent's analysis step; "
        f"got {wf.inputs}"
    )


def epicOnly_isRegisteredWithSingleStep(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-epic-only")
    step_names = [s.name for s in wf.steps]
    assert step_names == ["epic"], (
        f"Expected single-step epic-only workflow; got {step_names}"
    )
    assert isinstance(wf.steps[0], AICall), (
        "epic-only single step must be an AICall instance"
    )


def epicOnly_declaresAnalysisAsInput(app):
    """Epic-only must accept 'analysis' as an input so the retry route can pass-through."""
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-epic-only")
    assert "analysis" in wf.inputs, (
        f"epic-only must accept 'analysis' as input; declared inputs: {wf.inputs}"
    )
    # Epic step's required inputs (input_keys) must NOT list "analysis" — it
    # flows through prompt_template, not context.inputs validation.
    epic_step = wf.steps[0]
    assert "analysis" not in epic_step.input_keys, (
        "epic step input_keys must list workflow-level inputs only; "
        "'analysis' flows via prompt_template, not _validate_inputs"
    )


def architectureOnly_isRegisteredWithSingleStreamingStep(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-architecture-only")
    step_names = [s.name for s in wf.steps]
    assert step_names == ["architecture"], (
        f"Expected single-step architecture-only workflow; got {step_names}"
    )
    arch_step = wf.steps[0]
    assert isinstance(arch_step, AICall), (
        "architecture-only single step must be an AICall instance"
    )
    assert arch_step.stream is True, (
        "architecture-only step must opt into streaming (stream=True) — "
        f"got stream={arch_step.stream!r}"
    )


def architectureOnly_declaresAnalysisAndEpicAsInputs(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-architecture-only")
    for required in ("analysis", "epic"):
        assert required in wf.inputs, (
            f"architecture-only must accept {required!r} as input; "
            f"declared inputs: {wf.inputs}"
        )


def parentWorkflow_architectureStepStreamsToo(app):
    """The parent workflow's architecture step shares the streaming opt-in
    with the architecture-only sub-workflow (single source of truth via
    `_architecture_step()` helper)."""
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-project")
    arch_step = next(s for s in wf.steps if s.name == "architecture")
    assert arch_step.stream is True, (
        "Parent workflow's architecture step must opt into streaming; "
        f"got stream={arch_step.stream!r}"
    )


def allFourBootstrapWorkflows_appearInRepositoryList(app):
    """The repository must list exactly the four bootstrap workflows after registration."""
    with app.app_context():
        names = sorted(
            n for n in app.workflow_repository.list() if n.startswith("spec_gen/bootstrap")
        )
    assert names == [
        "spec_gen/bootstrap-analysis-only",
        "spec_gen/bootstrap-architecture-only",
        "spec_gen/bootstrap-epic-only",
        "spec_gen/bootstrap-project",
    ], f"Unexpected bootstrap workflow registry; got {names}"
