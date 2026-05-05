# Task 3: Bootstrap Workflow + Per-Step Sub-Workflows

**Effort**: 0.5 days

## Overview

The existing `_run_bootstrap_thread` orchestration in `api/modules/ai/routes/text.py` calls three `bootstrap_*_prompt` functions inline and drives `chain_adapter.generate` directly. This task replaces that loop with `WorkflowRuntime.run()` over the existing `spec_gen/bootstrap-project` workflow (already registered by `api/modules/ai/workflows/spec_gen/bootstrap.py`) and adds three new sub-workflows alongside: `bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`. Each sub-workflow accepts the prior outputs as inputs so an architecture-only retry pays for one AI call instead of three. See [Solution Architecture](./architecture.md) § Per-Step Sub-Workflows for Retry.

The existing `bootstrap-project` workflow already includes the `marshal_files` Compute step. The retry route in [Task 4](./task-4-retry-cancel-routes.md) wires the sub-workflows; this task only ships the workflow definitions.

## Prerequisites

- [Task 1](./task-1-cooperative-cancellation.md) merged — `WorkflowRuntime` honours cancellation
- [Task 2](./task-2-streaming-partial-buffer.md) merged — `AICall(stream=True)` opt-in works (architecture sub-workflow uses it)
- `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py` exists with `register_workflows(repo)` and `_build_workflow()` (modular-restructure — shipped)
- `{WORKSPACE}/api/modules/runtime/workflows/repository/` exposes `WorkflowRepository.get(name)` and the FS adapter walks `modules/<feature>/workflows/` at app startup (Workflows epic Task 4 — shipped)
- `current_app.workflow_repository` is wired in `create_app.py`

Run from `{WORKSPACE}/api/`:

```bash
git status
python -m pytest -q 2>&1 | tail -5
python -c "
from create_app import create_app
app = create_app()
with app.app_context():
    repo = app.workflow_repository
    wf = repo.get('spec_gen/bootstrap-project')
    print('steps:', [s.name for s in wf.steps])
"
```

The third command must print `steps: ['analysis', 'epic', 'architecture', 'files']`.

## Implementation Steps

### Step 1: Extract a shared step builder helper

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

Refactor the three `AICall` literals in `_build_workflow()` so they can be reused across the four workflows. Add private builder functions above `_build_workflow`:

```python
def _analysis_step() -> AICall:
    return AICall(
        name="analysis",
        system=BOOTSTRAP_ANALYSIS_SYSTEM,
        prompt_template=BOOTSTRAP_ANALYSIS_USER,
        input_keys=("braindump", "project_name", "builder"),
    )


def _epic_step() -> AICall:
    return AICall(
        name="epic",
        system=BOOTSTRAP_EPIC_SYSTEM,
        prompt_template=BOOTSTRAP_EPIC_USER,
        input_keys=("braindump", "project_name", "builder", "principles"),
    )


def _architecture_step() -> AICall:
    return AICall(
        name="architecture",
        system=BOOTSTRAP_ARCHITECTURE_SYSTEM,
        prompt_template=BOOTSTRAP_ARCHITECTURE_USER,
        input_keys=(
            "braindump", "project_name", "builder", "principles",
            "codebase", "references",
        ),
        max_tokens=16384,
        stream=True,  # added in Task 2
    )
```

Update `_build_workflow()` to call the helpers:

```python
def _build_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-project")
        .inputs(
            "braindump", "project_name", "builder",
            "principles", "codebase", "references",
        )
        .outputs("analysis", "epic", "architecture", "files")
        .step(_analysis_step())
        .step(_epic_step())
        .step(_architecture_step())
        .step(Compute(name="files", fn_name=_MARSHAL_FILES_NAME))
        .build()
    )
```

### Step 2: Register the analysis-only sub-workflow

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

Add a builder for the analysis-only sub-workflow. Inputs and outputs match the parent workflow's analysis step exactly so the retry route can pass-through the same input keys.

```python
def _build_analysis_only_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-analysis-only")
        .inputs("braindump", "project_name", "builder")
        .outputs("analysis")
        .step(_analysis_step())
        .build()
    )
```

### Step 3: Register the epic-only sub-workflow

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

The epic step's prompt template references `{analysis.text}`, so the retry route supplies `analysis` as a workflow input rather than re-running the analysis step. Declare `analysis` in the workflow inputs so `AbstractStep._validate_inputs` accepts the prompt's reference.

The epic step's `input_keys` lists workflow-level inputs only (per the existing comment in `bootstrap.py`); `analysis` flows through `prompt_template.format_map` via the merged outputs+inputs dict.

```python
def _build_epic_only_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-epic-only")
        .inputs("braindump", "project_name", "builder", "principles", "analysis")
        .outputs("epic")
        .step(_epic_step())
        .build()
    )
```

### Step 4: Register the architecture-only sub-workflow

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

Mirror Step 3 for the architecture sub-workflow. Both `analysis` and `epic` flow as workflow inputs (the prompt template references `{epic.text}`).

```python
def _build_architecture_only_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-architecture-only")
        .inputs(
            "braindump", "project_name", "builder", "principles",
            "codebase", "references", "analysis", "epic",
        )
        .outputs("architecture")
        .step(_architecture_step())
        .build()
    )
```

### Step 5: Register all four workflows from register_workflows

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

Update `register_workflows(repo)` to save all four:

```python
def register_workflows(repo) -> None:
    """Called by WorkflowRepositoryFs auto-discovery at app startup.

    Registers the parent bootstrap-project workflow plus three per-step
    sub-workflows used by the retry route (Task 4).  All four save under
    'spec_gen/' via the _PrefixedRepo wrapper.
    """
    repo.save(_build_workflow())
    repo.save(_build_analysis_only_workflow())
    repo.save(_build_epic_only_workflow())
    repo.save(_build_architecture_only_workflow())
```

### Step 6: Convert the bootstrap route to drain WorkflowRuntime

**File**: `{WORKSPACE}/api/modules/ai/routes/text.py`

Replace `_run_bootstrap_thread` with a thin runtime drain. The new function loads the workflow once at app startup via `current_app.workflow_repository`, but the thread body itself just iterates the runtime:

```python
def _run_bootstrap_via_runtime(execution: WorkflowExecution, workflow) -> None:
    """Background thread body: drain WorkflowRuntime over a Workflow.

    Replaces the inline three-call orchestration. Streaming partials
    land in execution.outputs['_partials'] (Task 2). Cancellation
    is read by the runtime between steps (Task 1).
    """
    t0 = time.monotonic()
    try:
        from modules.runtime.workflows import WorkflowRuntime
        for _event in WorkflowRuntime().run(execution, workflow):
            pass  # events already mirrored onto execution.outputs by the runtime
        execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
        if not execution.is_terminal:
            execution.fail(str(exc))
```

Update `bootstrap_project()` to load the workflow and pass it to the thread:

```python
@ai_bp.post("/bootstrap-project")
def bootstrap_project():
    req = BootstrapProjectRequest.model_validate(
        request.get_json(force=True, silent=False) or {}
    )
    project_name = req.project_name.strip()
    braindump = req.braindump.strip()
    if not project_name or not braindump:
        return jsonify({"error": "project_name and braindump are required"}), 400

    job_id = str(uuid.uuid4())
    inputs = {
        "braindump": braindump,
        "project_name": project_name,
        "builder": req.builder or read_context("builder"),
        "principles": req.principles or read_context("principles"),
        "codebase": req.codebase or read_context("codebase"),
        "references": req.references or read_context("references"),
    }
    workflow = current_app.workflow_repository.get("spec_gen/bootstrap-project")
    execution = WorkflowExecution(
        workflow_ref="spec_gen/bootstrap-project", inputs=inputs,
    )
    _BOOTSTRAP_JOBS[job_id] = execution
    threading.Thread(
        target=_run_bootstrap_via_runtime,
        args=(execution, workflow),
        name=f"bootstrap[{job_id[:8]}]",
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id}), 202
```

Add `from flask import current_app` to the existing imports if not already present.

Delete the old `_run_bootstrap_thread` function (lines 176–209 of the current file). The `bootstrap_*_prompt` imports from `modules.ai.prompts` may stay (they remain used by other routes) — verify with `grep` before deleting.

### Step 7: Confirm marshal_files still produces BootstrapFile records

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

The existing `marshal_files(context)` reads `context.outputs["analysis"].text`, etc. The runtime-driven path populates these the same way; no change required. Sanity-check by inspecting the function — if its signature or contract differs from what `bootstrap_status` expects in [Task 4](./task-4-retry-cancel-routes.md), reconcile here.

## Tests

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/tests/test_bootstrap_workflows.py` (new — `tests/__init__.py` already exists in the parent `spec_gen/` package)

```python
"""Tests for the bootstrap workflow registry.

Asserts that all four workflows register, that each sub-workflow has
exactly one AICall step, and that the input declarations match the
prompt-template format-map keys.
"""
from __future__ import annotations

import pytest

from create_app import create_app


@pytest.fixture
def app():
    return create_app()


def bootstrapProject_isRegistered(app):
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


def epicOnly_isRegisteredWithSingleStep(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-epic-only")
    step_names = [s.name for s in wf.steps]
    assert step_names == ["epic"], (
        f"Expected single-step epic-only workflow; got {step_names}"
    )


def epicOnly_declaresAnalysisAsInput(app):
    """Epic-only must accept 'analysis' as an input so the retry route can pass-through."""
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-epic-only")
    assert "analysis" in wf.inputs, (
        f"epic-only must accept 'analysis' as input; declared inputs: {wf.inputs}"
    )


def architectureOnly_isRegisteredWithSingleStreamingStep(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-architecture-only")
    step_names = [s.name for s in wf.steps]
    assert step_names == ["architecture"], (
        f"Expected single-step architecture-only workflow; got {step_names}"
    )
    arch_step = wf.steps[0]
    assert getattr(arch_step, "stream", False) is True, (
        "architecture-only step must opt into streaming (stream=True)"
    )


def architectureOnly_declaresAnalysisAndEpicAsInputs(app):
    with app.app_context():
        wf = app.workflow_repository.get("spec_gen/bootstrap-architecture-only")
    for required in ("analysis", "epic"):
        assert required in wf.inputs, (
            f"architecture-only must accept {required!r} as input; "
            f"declared inputs: {wf.inputs}"
        )


def bootstrapProject_routeUsesWorkflowRepository(monkeypatch, app):
    """The bootstrap_project route must load the workflow from the repository."""
    from modules.ai.routes import text as text_routes

    captured: dict = {}
    real_get = app.workflow_repository.get

    def _spy_get(name):
        captured["name"] = name
        return real_get(name)

    monkeypatch.setattr(app.workflow_repository, "get", _spy_get)

    # Prevent the daemon thread from actually running by stubbing it.
    monkeypatch.setattr(
        text_routes.threading, "Thread",
        lambda *a, **kw: type("T", (), {"start": lambda self: None})(),
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/text/bootstrap-project",
        json={"project_name": "test-proj", "braindump": "some braindump text"},
    )
    assert response.status_code == 202, (
        f"Expected 202; got {response.status_code} body={response.get_json()}"
    )
    assert captured.get("name") == "spec_gen/bootstrap-project", (
        f"Route must load 'spec_gen/bootstrap-project'; got {captured}"
    )
```

(Create `{WORKSPACE}/api/modules/ai/workflows/spec_gen/tests/__init__.py` as an empty file if it does not yet exist.)

Verify in isolation:

```bash
cd {WORKSPACE}/api
python -m pytest modules/ai/workflows/spec_gen/tests/test_bootstrap_workflows.py -v
```

All seven tests must pass.

## Verification

Run from `{WORKSPACE}/api/`:

```bash
python -m pytest -q
```

Expected delta: **N → N+7 passing** (seven new bootstrap-workflow tests; zero existing tests broken). Record the pre-task baseline as N before edits.

```bash
python -c "
from create_app import create_app
app = create_app()
with app.app_context():
    names = sorted(app.workflow_repository.list())
print('\n'.join(names))
" | grep "^spec_gen/bootstrap"
```

Must print exactly four lines:

```
spec_gen/bootstrap-analysis-only
spec_gen/bootstrap-architecture-only
spec_gen/bootstrap-epic-only
spec_gen/bootstrap-project
```

```bash
grep -n "_run_bootstrap_thread" modules/ai/routes/text.py
```

Must print no matches — the old function is deleted.

```bash
grep -n "WorkflowRuntime" modules/ai/routes/text.py
```

Must print at least one line — the new `_run_bootstrap_via_runtime` references it.

```bash
make lint
```

Confirms: flake8 clean.

```bash
python -m pytest tests/test_structural.py -v
```

Confirms: all structural invariants stay green.

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
