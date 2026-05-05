# Task 4: Retry, Regenerate, Cancel Routes + Polling Surface

**Effort**: 0.4 days

## Overview

Add three new routes per affected feature: cancel, retry (bootstrap) / regenerate (task_gen), and extend the existing polling response with `current_step`, `partial`, `warnings`, and `error` fields. Add a truncation heuristic helper in `modules/quality/` that populates `WorkflowExecution.warnings` after each step completes. See [Solution Architecture](./architecture.md) § Truncation Heuristic for `warnings` and § `_BOOTSTRAP_JOBS` Job Registry.

This task wires together the runtime extensions from [Task 1](./task-1-cooperative-cancellation.md), the streaming partials from [Task 2](./task-2-streaming-partial-buffer.md), and the sub-workflows from [Task 3](./task-3-bootstrap-sub-workflows.md). After this task lands the backend exposes the full reliability surface; only the Angular render layer ([Task 5](./task-5-angular-live-preview.md)) remains.

## Prerequisites

- [Task 1](./task-1-cooperative-cancellation.md), [Task 2](./task-2-streaming-partial-buffer.md), [Task 3](./task-3-bootstrap-sub-workflows.md) all merged
- `{WORKSPACE}/api/modules/ai/routes/text.py` and `{WORKSPACE}/api/modules/ai/routes/task_gen.py` exist (modular-restructure — shipped)
- `{WORKSPACE}/api/modules/quality/` exists as a package (modular-restructure — shipped)
- `{WORKSPACE}/api/openapi.yaml` is the contract; new routes must be declared there before route handlers ship (the structural test `everyOpenapiPath_hasRouteHandler` enforces this)

Run from `{WORKSPACE}/api/`:

```bash
git status
python -m pytest -q 2>&1 | tail -5
ls modules/quality/
ls modules/ai/routes/
```

## Implementation Steps

### Step 1: Add warnings field to WorkflowExecution

**File**: `{WORKSPACE}/api/modules/runtime/workflows/execution.py`

Add a `warnings: list[str]` field to the `WorkflowExecution` dataclass, defaulting to an empty list.

Insert below `error: str | None = None`:

```python
    warnings: list[str] = field(default_factory=list)
```

No state-machine change. The runtime appends to this list (Step 3) after each successful step.

### Step 2: Add the truncation heuristic helper

**File**: `{WORKSPACE}/api/modules/quality/truncation.py` (new)

```python
"""Pure-function heuristics that flag malformed step output.

Each heuristic returns a warning string (or None). The public
`detect_truncation` function fans them out and returns the non-empty
list. Callers append the result to WorkflowExecution.warnings.
"""
from __future__ import annotations

_MIN_REASONABLE_LENGTH = 200


def _odd_triple_backticks(text: str) -> str | None:
    fence_count = text.count("```")
    if fence_count % 2 == 1:
        return f"unclosed_code_fence: {fence_count} triple-backticks (odd)"
    return None


def _too_short(text: str, max_tokens: int) -> str | None:
    if max_tokens >= 4096 and len(text) < _MIN_REASONABLE_LENGTH:
        return (
            f"suspiciously_short: {len(text)} chars with max_tokens={max_tokens}"
        )
    return None


def _missing_terminal_newline(text: str) -> str | None:
    if text and not text.endswith("\n"):
        return "missing_terminal_newline"
    return None


def detect_truncation(text: str, *, max_tokens: int = 4096) -> list[str]:
    """Return a list of warning strings for each heuristic that fired.

    Empty list means no warnings detected. Callers extend
    WorkflowExecution.warnings with the result.
    """
    warnings: list[str] = []
    for fn in (
        lambda: _odd_triple_backticks(text),
        lambda: _too_short(text, max_tokens),
        lambda: _missing_terminal_newline(text),
    ):
        warning = fn()
        if warning is not None:
            warnings.append(warning)
    return warnings
```

### Step 3: Have the runtime apply the truncation heuristic per step

**File**: `{WORKSPACE}/api/modules/runtime/workflows/runtime.py`

After the existing `if step.name in context.outputs:` mirror, append the truncation check. The runtime does not know each step's `max_tokens`, but it can introspect via `getattr(step, "max_tokens", 4096)`. Step kinds without `max_tokens` (e.g. `Compute`) skip the heuristic by virtue of the default.

Add the import at the top:

```python
from modules.quality.truncation import detect_truncation
```

Inside the `for step in workflow.steps:` block, after the output mirror:

```python
            if step.name in context.outputs:
                output = context.outputs[step.name]
                execution.outputs[step.name] = output
                # Truncation heuristic — only on text-bearing outputs (ChainResult)
                output_text = getattr(output, "text", None)
                if isinstance(output_text, str):
                    max_tokens = getattr(step, "max_tokens", 4096)
                    execution.warnings.extend(
                        detect_truncation(output_text, max_tokens=max_tokens)
                    )
```

### Step 4: Track current_step on WorkflowExecution

**File**: `{WORKSPACE}/api/modules/runtime/workflows/execution.py`

Add `current_step_name: str | None = None`. The runtime sets this at the top of each step iteration (Step 5).

Insert below the new `warnings` field:

```python
    current_step_name: str | None = None
```

### Step 5: Have the runtime set current_step_name per iteration

**File**: `{WORKSPACE}/api/modules/runtime/workflows/runtime.py`

In the `for step in workflow.steps:` loop, immediately after the cancellation check (added in Task 1), set `execution.current_step_name = step.name`. The polling endpoint reads it.

```python
        for step in workflow.steps:
            if execution.status is ExecutionStatus.CANCELLING:
                execution.cancel()
                return
            execution.current_step_name = step.name
            last_event: StepEvent | None = None
            ...
```

After the loop completes, clear it: `execution.current_step_name = None`.

### Step 6: Extend bootstrap_status response with new fields

**File**: `{WORKSPACE}/api/modules/ai/routes/text.py`

Update `bootstrap_status` to surface the new fields. The `partial` value reads from `execution.outputs.get("_partials", {}).get(execution.current_step_name, "")`.

```python
@ai_bp.get("/bootstrap-project/status/<job_id>")
def bootstrap_status(job_id: str):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None:
        return jsonify({"error": "job not found"}), 404

    done = execution.is_terminal
    partials = execution.outputs.get("_partials", {})
    body: dict = {
        "running": execution.is_running,
        "done": done,
        "current_step": execution.current_step_name,
        "partial": partials.get(execution.current_step_name, ""),
        "warnings": list(execution.warnings),
    }

    if done:
        _BOOTSTRAP_JOBS.pop(job_id, None)
        if execution.status is ExecutionStatus.COMPLETED:
            outputs = execution.outputs
            project_name = execution.inputs["project_name"]
            epic = outputs.get("epic", "")
            if hasattr(epic, "text"):  # ChainResult vs raw str backward-compat
                epic = epic.text
            tasks = bootstrap_extract_tasks(epic)
            files = [
                BootstrapFile(filename="spec-index.md", content=generate_spec_index(project_name)),
                BootstrapFile(filename="analysis.md", content=_text_of(outputs.get("analysis", ""))),
                BootstrapFile(filename="epic.md", content=epic),
                BootstrapFile(filename="architecture.md", content=_text_of(outputs.get("architecture", ""))),
                BootstrapFile(filename="timeline.md", content=generate_timeline(project_name, tasks)),
                BootstrapFile(filename="README.md", content=generate_readme(project_name)),
            ]
            body["files"] = [f.model_dump() for f in files]
            body["latencyMs"] = outputs.get("latency_ms", 0)
        elif execution.error:
            body["error"] = execution.error
        elif execution.status is ExecutionStatus.CANCELLED:
            body["status"] = "cancelled"

    return jsonify(body)


def _text_of(value) -> str:
    """ChainResult-or-str adapter for backward compat."""
    return value.text if hasattr(value, "text") else value
```

### Step 7: Add the bootstrap cancel route

**File**: `{WORKSPACE}/api/modules/ai/routes/text.py`

```python
@ai_bp.post("/bootstrap-project/<job_id>/cancel")
def bootstrap_cancel(job_id: str):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None:
        return jsonify({"error": "job not found"}), 404
    if execution.status not in (ExecutionStatus.NEW, ExecutionStatus.IN_PROGRESS):
        return jsonify({
            "error": "cannot cancel",
            "status": execution.status.value,
        }), 409
    execution.request_cancel()
    return jsonify({"status": execution.status.value}), 202
```

### Step 8: Add the bootstrap retry route

**File**: `{WORKSPACE}/api/modules/ai/routes/text.py`

```python
_RETRY_WORKFLOW_REFS = {
    "analysis": "spec_gen/bootstrap-analysis-only",
    "epic": "spec_gen/bootstrap-epic-only",
    "architecture": "spec_gen/bootstrap-architecture-only",
}


@ai_bp.post("/bootstrap-project/<job_id>/retry")
def bootstrap_retry(job_id: str):
    body = request.get_json(force=True, silent=False) or {}
    step = (body.get("step") or "").strip()
    workflow_ref = _RETRY_WORKFLOW_REFS.get(step)
    if workflow_ref is None:
        return jsonify({
            "error": "invalid step",
            "allowed": sorted(_RETRY_WORKFLOW_REFS.keys()),
        }), 400

    prior = _BOOTSTRAP_JOBS.get(job_id)
    if prior is None:
        return jsonify({"error": "job not found"}), 404

    new_inputs = dict(prior.inputs)
    if step in ("epic", "architecture"):
        analysis = prior.outputs.get("analysis")
        new_inputs["analysis"] = _text_of(analysis) if analysis else ""
    if step == "architecture":
        epic = prior.outputs.get("epic")
        new_inputs["epic"] = _text_of(epic) if epic else ""

    workflow = current_app.workflow_repository.get(workflow_ref)
    new_id = str(uuid.uuid4())
    new_execution = WorkflowExecution(workflow_ref=workflow_ref, inputs=new_inputs)
    _BOOTSTRAP_JOBS[new_id] = new_execution
    threading.Thread(
        target=_run_bootstrap_via_runtime,
        args=(new_execution, workflow),
        name=f"retry-{step}[{new_id[:8]}]",
        daemon=True,
    ).start()
    return jsonify({"job_id": new_id}), 202
```

### Step 9: Mirror cancel + regenerate routes for task_gen

**File**: `{WORKSPACE}/api/modules/ai/routes/task_gen.py`

Add a cancel route that pulls the `WorkflowExecution` from the existing `task_gen` `_EXECUTIONS` dict (the `task_gen` service already keys by `project_id`):

```python
@task_gen_bp.post("/<project_id>/cancel")
def task_gen_cancel(project_id: str):
    from modules.ai.services import task_gen as svc
    execution = svc._EXECUTIONS.get(project_id)
    if execution is None:
        return jsonify({"error": "no execution for project"}), 404
    if execution.status not in (ExecutionStatus.NEW, ExecutionStatus.IN_PROGRESS):
        return jsonify({
            "error": "cannot cancel",
            "status": execution.status.value,
        }), 409
    execution.request_cancel()
    return jsonify({"status": execution.status.value}), 202
```

Regenerate route — deletes the prior generated task file, re-starts:

```python
import re


@task_gen_bp.post("/<project_id>/regenerate-task")
def regenerate_task(project_id: str):
    from modules.ai.services import task_gen as svc
    body = request.get_json(force=True, silent=False) or {}
    task_num = (body.get("task_num") or "").strip()
    if not task_num:
        return jsonify({"error": "task_num is required"}), 400

    project = current_app.project_repository.get(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404

    pattern = re.compile(rf"^task-{re.escape(task_num)}-")
    for filename in current_app.git_store.list_files(project.id):
        if pattern.match(filename):
            current_app.git_store.delete_file(
                project.id, filename,
                message=f"chore: regenerate task {task_num}",
            )
    started = svc.start(project.id, task_num=task_num)
    return jsonify({"started": started}), 202 if started else 409
```

(If `current_app.project_repository` and `current_app.git_store` are not yet on the app — they ship via the persistence brain dump — gate the deletion behind `if hasattr(current_app, "git_store")` and skip the file purge. The regenerate path still re-runs the workflow against the same `task_num`.)

### Step 10: Declare new endpoints in openapi.yaml

**File**: `{WORKSPACE}/api/openapi.yaml`

Add four new path entries. Reuse existing `BootstrapFile` and `BootstrapProjectResponse` schemas where possible.

```yaml
  /api/ai/text/bootstrap-project/{job_id}/cancel:
    post:
      operationId: cancelBootstrap
      summary: Request cooperative cancellation of an in-flight bootstrap job
      parameters:
        - in: path
          name: job_id
          required: true
          schema: { type: string }
      responses:
        '202': { description: Cancellation requested }
        '404': { description: Job not found }
        '409': { description: Job is not cancellable in its current state }

  /api/ai/text/bootstrap-project/{job_id}/retry:
    post:
      operationId: retryBootstrap
      summary: Retry a single bootstrap step (analysis | epic | architecture)
      parameters:
        - in: path
          name: job_id
          required: true
          schema: { type: string }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [step]
              properties:
                step:
                  type: string
                  enum: [analysis, epic, architecture]
      responses:
        '202':
          description: New job started for the targeted step
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id: { type: string }
        '400': { description: Invalid step name }
        '404': { description: Prior job not found }

  /api/ai/text/generate-task/{project_id}/cancel:
    post:
      operationId: cancelTaskGen
      summary: Request cooperative cancellation of an in-flight task_gen job
      parameters:
        - in: path
          name: project_id
          required: true
          schema: { type: string }
      responses:
        '202': { description: Cancellation requested }
        '404': { description: No execution for project }
        '409': { description: Not cancellable }

  /api/ai/text/generate-task/{project_id}/regenerate-task:
    post:
      operationId: regenerateTask
      summary: Delete and re-run a previously generated task guide
      parameters:
        - in: path
          name: project_id
          required: true
          schema: { type: string }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [task_num]
              properties:
                task_num: { type: string }
      responses:
        '202': { description: Regeneration started }
        '404': { description: Project not found }
        '409': { description: Already running }
```

After editing `openapi.yaml`, run `make generate-dtos` from `{WORKSPACE}/api/` and stage the regenerated `dtos/models.py` (force-add via `git add -f` per `api/CLAUDE.md`).

## Tests

**File**: `{WORKSPACE}/api/modules/ai/routes/tests/test_text_reliability.py` (new)

```python
"""Tests for the cancel, retry, and extended polling response on bootstrap."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from create_app import create_app
from modules.runtime.workflows import (
    ExecutionStatus,
    WorkflowExecution,
)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_jobs():
    from modules.ai.routes.text import _BOOTSTRAP_JOBS
    _BOOTSTRAP_JOBS.clear()
    yield
    _BOOTSTRAP_JOBS.clear()


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

    started_inputs: dict = {}

    def _capture_thread_target(target, *, args, name, daemon):
        # Capture the new execution's inputs without launching the thread
        execution = args[0]
        started_inputs.update(execution.inputs)
        return type("T", (), {"start": lambda self: None})()

    with patch(
        "modules.ai.routes.text.threading.Thread",
        side_effect=lambda **kw: _capture_thread_target(**kw),
    ):
        response = client.post(
            "/api/ai/text/bootstrap-project/job-5/retry",
            json={"step": "architecture"},
        )

    assert response.status_code == 202
    assert started_inputs.get("analysis") == "analysis-text", (
        f"Architecture retry must pass prior analysis text; got {started_inputs}"
    )
    assert started_inputs.get("epic") == "epic-text", (
        f"Architecture retry must pass prior epic text; got {started_inputs}"
    )
```

**File**: `{WORKSPACE}/api/modules/quality/tests/test_truncation.py` (new)

```python
from modules.quality.truncation import detect_truncation


def detectTruncation_unclosedCodeFence_emitsWarning():
    text = "```python\nprint('x')\n"  # one opening fence, no closing
    warnings = detect_truncation(text, max_tokens=4096)
    assert any("unclosed_code_fence" in w for w in warnings), (
        f"Expected unclosed_code_fence warning; got {warnings}"
    )


def detectTruncation_balancedCodeFences_emitsNoFenceWarning():
    text = "```python\nprint('x')\n```\n"
    warnings = detect_truncation(text, max_tokens=4096)
    assert not any("unclosed_code_fence" in w for w in warnings), (
        f"Balanced fences must not warn; got {warnings}"
    )


def detectTruncation_shortOutputAtHighMaxTokens_emitsSuspiciouslyShort():
    text = "tiny output\n"  # < 200 chars with max_tokens=16384
    warnings = detect_truncation(text, max_tokens=16384)
    assert any("suspiciously_short" in w for w in warnings), (
        f"Expected suspiciously_short warning; got {warnings}"
    )


def detectTruncation_shortOutputAtLowMaxTokens_emitsNoShortWarning():
    text = "tiny output\n"
    warnings = detect_truncation(text, max_tokens=512)
    assert not any("suspiciously_short" in w for w in warnings), (
        f"Low max_tokens must not flag short output; got {warnings}"
    )


def detectTruncation_missingTerminalNewline_emitsWarning():
    text = "no trailing newline"
    warnings = detect_truncation(text, max_tokens=4096)
    assert any("missing_terminal_newline" in w for w in warnings), (
        f"Expected missing_terminal_newline warning; got {warnings}"
    )


def detectTruncation_cleanLongOutput_emitsEmptyList():
    text = ("clean line\n" * 100)  # >> 200 chars, balanced (no fences), trailing \n
    warnings = detect_truncation(text, max_tokens=16384)
    assert warnings == [], f"Clean output must not warn; got {warnings}"
```

Verify in isolation:

```bash
cd {WORKSPACE}/api
python -m pytest modules/ai/routes/tests/test_text_reliability.py modules/quality/tests/test_truncation.py -v
```

All thirteen tests must pass.

## Verification

Run from `{WORKSPACE}/api/`:

```bash
make generate-dtos
git diff dtos/models.py | head -50  # confirm new DTOs present, generated cleanly
make check-dtos
```

DTOs must be regenerated and the check-dtos diff must be clean.

```bash
python -m pytest -q
```

Expected delta: **N → N+13 passing** (seven route tests + six truncation tests; zero existing tests broken).

```bash
python -m pytest tests/test_structural.py -v
```

Confirms: `everyOpenapiPath_hasRouteHandler` stays green (each new path has a registered handler); `featureModules_mustNotImportProvidersDirectly` stays green.

```bash
make lint
```

Confirms: flake8 clean.

Spot-check the new fields are present in a manual status response:

```bash
curl -s -X POST http://localhost:3101/api/ai/text/bootstrap-project \
  -H 'Content-Type: application/json' \
  -d '{"project_name":"smoke","braindump":"x"}' | jq .
# capture job_id, then:
curl -s http://localhost:3101/api/ai/text/bootstrap-project/status/<job_id> | jq .
```

Response must include `current_step`, `partial`, and `warnings` fields.

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
