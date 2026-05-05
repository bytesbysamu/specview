# Task 5: Migrate spec_gen to WorkflowRuntime — Implementation Guide

## 1. Context

`bootstrap_project` in `modules/ai/routes.py` (lines 169–228) hard-codes a three-AI-call pipeline — analysis → epic → architecture — directly in the route handler. Task 5 extracts this orchestration into a named `Workflow` loaded from `WorkflowRepository` and executed through `WorkflowRuntime`, housed in a new `modules/spec_gen/` feature module. The route handler after migration contains no inline AI calls and no step awareness: it constructs a `WorkflowExecution`, drains the generator, and serialises the result. This is the end-to-end validation that the Layer B–E contracts from Tasks 1–4 compose correctly under real conditions.

**The existing `POST /api/ai/text/generate-spec` single-pass endpoint is not touched.** The migration adds `POST /api/spec-gen/generate` as a new endpoint. `bootstrap_project` in `ai/routes.py` is also left untouched — it is the reference implementation being structurally superseded, not deleted.

**Prompt format decision:** The existing `bootstrap_*_prompt` functions in `modules/ai/prompts/__init__.py` use Python f-strings with conditional builder/principles blocks. `AICall.system` is a static string (no template interpolation) and `AICall.prompt_template` is a Python format string rendered via `.format_map({**context.outputs, **context.inputs})` — so each step's user-prompt template can reference any prior step's output by name. The new `modules/spec_gen/prompts.py` provides constants that include builder and principles unconditionally (empty strings render as blank sections — harmless for structural validation). Prompt fidelity parity with bootstrap_project is explicitly out of scope.

---

## 2. Pre-flight

All commands from `{WORKSPACE}/spec-doc/api/`.

```bash
# 1. Confirm clean working tree
git status

# 2. Tasks 1–4 prerequisite check — all four must print "OK"
python -c "from modules.workflows.workflow import Workflow, WorkflowBuilder, WorkflowRef; print('OK')"
python -c "from modules.workflows.steps.ai_call import AICall; print('OK')"
python -c "from modules.workflows.execution import WorkflowExecution, ExecutionStatus; print('OK')"
python -c "from modules.workflows.runtime import WorkflowRuntime; print('OK')"
python -c "from modules.workflows.repository import WorkflowRepository; print('OK')"
python -c "from modules.workflows.events import StepCompleted, StepFailed; print('OK')"

# 3. Confirm spec_gen does not yet exist
ls modules/ | grep spec_gen && echo "EXISTS — skip creation steps" || echo "ABSENT — proceed"

# 4. Confirm app.workflow_repository is wired (Task 4 post-condition)
python -c "
from create_app import create_app
app = create_app({'TESTING': True})
with app.app_context():
    from flask import current_app
    assert hasattr(current_app._get_current_object(), 'workflow_repository'), 'Task 4 not complete'
    print('workflow_repository present')
"

# 5. Record baseline test count
python -m pytest -q 2>&1 | tail -3
```

**If any Task 1–4 import fails:** stop; those tasks are prerequisite. Record which import failed in the commit body as a deviation.

**If `app.workflow_repository` is absent:** perform the `create_app.py` wiring from Task 4's Step 5 before continuing here.

**Baseline recorded:** record the actual `make test` pass count as **N**. This task adds **+22 tests** with zero pre-existing failures — verification is `N → N+22`. Do not rely on absolute counts.

---

## 3. Files

### To Create (new)

| Path | Purpose |
|---|---|
| `modules/spec_gen/__init__.py` | Package marker |
| `modules/spec_gen/prompts.py` | Format-string prompt constants for all three AI steps |
| `modules/spec_gen/workflows/__init__.py` | Workflows sub-package marker |
| `modules/spec_gen/workflows/generate_spec.py` | `register_workflows(repo)` — defines the `generate-spec` Workflow |
| `modules/spec_gen/routes.py` | `spec_gen_bp` Blueprint; single `POST /api/spec-gen/generate` handler |
| `modules/spec_gen/tests/__init__.py` | Test sub-package marker |
| `modules/spec_gen/tests/test_routes.py` | Full pytest suite for the route and workflow integration |

### To Modify

| Path | Change | Lines |
|---|---|---|
| `create_app.py` | Add `('modules.spec_gen.routes', 'spec_gen_bp')` to `ENABLED_MODULES` | 19–25 |
| `openapi.yaml` | Add `POST /api/spec-gen/generate` path referencing existing schemas | After last path block |
| `tests/test_structural.py` | Append `featureModules_mustNotLoadWorkflowsDirectly` bare function | After line 46 |

### To Leave Alone

- `modules/ai/routes.py` — `bootstrap_project` and `generate_spec` stay as-is; this task adds, does not remove
- `modules/ai/prompts/__init__.py` — existing prompt functions unchanged; the new spec_gen prompts are separate constants
- `dtos/models.py` — auto-generated; `BootstrapProjectRequest` and `BootstrapProjectResponse` are reused as-is; no new schemas → no `make generate-dtos` run needed
- `modules/workflows/` — Tasks 1–4 output; consumed here, not edited
- `modules/task_gen/` — separate module; not touched in this task

---

## 4. Implementation Steps

### Step 1 — Scaffold the `spec_gen` package

**File:** `modules/spec_gen/__init__.py` (new)

```python
"""spec_gen — AI-backed specification generation via WorkflowRuntime."""
```

**File:** `modules/spec_gen/workflows/__init__.py` (new)

```python
```

*(empty — makes pytest and the FS adapter discover the sub-package)*

**File:** `modules/spec_gen/tests/__init__.py` (new)

```python
```

**Verify:**
```bash
python -c "import modules.spec_gen; print('ok')"
```

---

### Step 2 — Write prompt constants

**File:** `modules/spec_gen/prompts.py` (new)

These are the format strings `AICall` renders. Every `{variable}` must appear in the step's `input_keys`.

```python
"""Prompt constants for the spec_gen generate-spec workflow.

Each constant is a Python format string. AICall renders it with:
    template.format(**{k: context[k] for k in step.input_keys})

Convention: SYSTEM strings end in ``_SYSTEM``; user prompt strings end in ``_USER``.
"""
from __future__ import annotations

# ── Shared ──────────────────────────────────────────────────────────────────

_CONTENT_ROUTING = """\
## CONTENT ROUTING RULES
- Business value and market analysis → ONLY in epic.md
- Design decisions and tech stack → ONLY in architecture.md
- Problem identification → ONLY in analysis.md
- Cross-references MUST be bidirectional\
"""

# ── Step 1: Analysis ─────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = "You are a markdown spec writer."

ANALYSIS_USER = """\
You are a filter between a messy brain dump and a structured epic.
Keep it SHORT — 30-40 lines max. No severity tables. No analogies.

## BUILDER CONTEXT
{builder}

{_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🔍 {project_name} — Analysis

## The Problem
[2-3 sentences. What exists today, why it's broken, what changes.]

## Hard Constraints
[Decisions already made. Deadlines. Budget limits.]

## Open Questions
[Things the brain dump left ambiguous.]

## Dependencies & Sequencing
[What blocks what.]

## Explicitly Out of Scope
[Things mentioned that should NOT be in the epic.]

---

INPUT:
{braindump}""".format(_CONTENT_ROUTING=_CONTENT_ROUTING,
                      builder="{builder}",
                      project_name="{project_name}",
                      braindump="{braindump}")

# ── Step 2: Epic ─────────────────────────────────────────────────────────────

EPIC_SYSTEM = "You are a markdown spec writer."

EPIC_USER = """\
You are generating an Epic document. Define scope, tasks, and success criteria.
NO implementation details. NO status. 3-5 tasks for MVP.

## BUILDER CONTEXT
{builder}

## PRINCIPLES
{principles}

## CONTEXT FROM ANALYSIS
{analysis}

{_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🎯 Epic: {project_name}

## Business Value
[Why build this? Market opportunity.]

## Scope

### What This Epic Covers
- [Feature]

### What This Epic Does NOT Cover
- ❌ [Feature] — [Reason]

## Tasks

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **[Name]** | None | Xd | High |

## Success Criteria
- ✅ [Measurable criterion]

---

INPUT:
{braindump}""".format(_CONTENT_ROUTING=_CONTENT_ROUTING,
                      builder="{builder}",
                      principles="{principles}",
                      analysis="{analysis}",
                      project_name="{project_name}",
                      braindump="{braindump}")

# ── Step 3: Architecture ──────────────────────────────────────────────────────

ARCHITECTURE_SYSTEM = "You are a markdown spec writer."

ARCHITECTURE_USER = """\
Write a Solution Architecture document. Design decisions and tech stack ONLY.
No implementation steps. No status.

## BUILDER CONTEXT
{builder}

## PRINCIPLES
{principles}

## CONTEXT FROM EPIC
{epic}

## CODEBASE CONTEXT
{codebase}

## REFERENCES
{references}

{_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🏗️ Solution Architecture: {project_name}

## Overview
[2-3 sentences.]

## Component Design
[Key components and their responsibilities.]

## Technology Stack
| Layer | Choice | Rationale |

## Design Decisions
| Decision | Rationale | Trade-offs |

---

INPUT:
{braindump}""".format(_CONTENT_ROUTING=_CONTENT_ROUTING,
                      builder="{builder}",
                      principles="{principles}",
                      epic="{epic}",
                      codebase="{codebase}",
                      references="{references}",
                      project_name="{project_name}",
                      braindump="{braindump}")
```

**Why the `.format()` pre-call:** `_CONTENT_ROUTING` is a shared constant, not a workflow input. Pre-rendering it at module load time keeps `AICall.input_keys` clean (no `_CONTENT_ROUTING` key in the execution inputs). The `{variable}` placeholders for actual inputs survive because they are double-escaped in the `.format()` call above.

**Verify:**
```bash
python -c "
from modules.spec_gen.prompts import ANALYSIS_SYSTEM, ANALYSIS_USER, EPIC_USER, ARCHITECTURE_USER
ctx = dict(braindump='b', project_name='p', builder='', principles='', analysis='a', epic='e', codebase='', references='')
print(ANALYSIS_USER.format(**ctx)[:40])
print(EPIC_USER.format(**ctx)[:40])
print(ARCHITECTURE_USER.format(**ctx)[:40])
print('prompts ok')
"
```

---

### Step 3 — Define the workflow

**File:** `modules/spec_gen/workflows/generate_spec.py` (new)

```python
"""Registers the spec_gen/generate-spec workflow.

Convention required by WorkflowRepositoryFs:
    Every workflow file must expose register_workflows(repo) at module level.
    The FS adapter calls this with a _PrefixedRepo that namespaces all saves
    under 'spec_gen/<workflow.name>'.
"""
from __future__ import annotations

from modules.workflows.steps.ai_call import AICall
from modules.workflows.workflow import Workflow
from modules.spec_gen.prompts import (
    ANALYSIS_SYSTEM,
    ANALYSIS_USER,
    ARCHITECTURE_SYSTEM,
    ARCHITECTURE_USER,
    EPIC_SYSTEM,
    EPIC_USER,
)


def _build_workflow() -> Workflow:
    return (
        Workflow.builder("generate-spec")
        .inputs(
            "braindump",
            "project_name",
            "builder",
            "principles",
            "codebase",
            "references",
        )
        .outputs("analysis", "epic", "architecture")
        .step(
            AICall(
                name="analysis",
                system=ANALYSIS_SYSTEM,
                prompt_template=ANALYSIS_USER,
                input_keys=("braindump", "project_name", "builder"),
            )
        )
        .step(
            AICall(
                name="epic",
                system=EPIC_SYSTEM,
                prompt_template=EPIC_USER,
                input_keys=("braindump", "project_name", "builder", "principles", "analysis"),
            )
        )
        .step(
            AICall(
                name="architecture",
                system=ARCHITECTURE_SYSTEM,
                prompt_template=ARCHITECTURE_USER,
                input_keys=(
                    "braindump",
                    "project_name",
                    "builder",
                    "principles",
                    "epic",
                    "codebase",
                    "references",
                ),
            )
        )
        .build()
    )


def register_workflows(repo) -> None:
    """Called by WorkflowRepositoryFs during app startup.

    The repo argument is a _PrefixedRepo that prepends 'spec_gen/' to all
    names; saving as 'generate-spec' is accessible as 'spec_gen/generate-spec'.
    """
    repo.save(_build_workflow())
```

**Verify:**
```bash
python -c "
from modules.spec_gen.workflows.generate_spec import _build_workflow
w = _build_workflow()
assert w.name == 'generate-spec'
assert len(w.steps) == 3
assert w.steps[0].name == 'analysis'
assert w.steps[1].name == 'epic'
assert w.steps[2].name == 'architecture'
print('workflow ok:', w.name, len(w.steps), 'steps')
"
```

---

### Step 4 — Write the route handler

**File:** `modules/spec_gen/routes.py` (new)

```python
"""spec_gen Blueprint — POST /api/spec-gen/generate.

The handler:
  1. Validates the request.
  2. Loads the named Workflow from app.workflow_repository.
  3. Constructs a WorkflowExecution and drains WorkflowRuntime.
  4. Returns the accumulated step outputs as a list of named files.

The handler inspects no steps and contains no AI call logic.
"""
from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request

from dtos.models import BootstrapFile, BootstrapProjectRequest, BootstrapProjectResponse
from modules.chain.context import read_context
from modules.workflows.events import StepCompleted, StepFailed
from modules.workflows.execution import WorkflowExecution
from modules.workflows.runtime import WorkflowRuntime
from modules.workflows.workflow import WorkflowRef

spec_gen_bp = Blueprint("spec_gen", __name__, url_prefix="/api/spec-gen")

_WORKFLOW_NAME = "spec_gen/generate-spec"

_STEP_TO_FILENAME: dict[str, str] = {
    "analysis": "analysis.md",
    "epic": "epic.md",
    "architecture": "architecture.md",
}


@spec_gen_bp.post("/generate")
def generate():
    req = BootstrapProjectRequest.model_validate(
        request.get_json(force=True, silent=False) or {}
    )

    # Merge request context with filesystem fallbacks
    inputs = {
        "braindump": req.braindump.strip(),
        "project_name": req.project_name.strip(),
        "builder": req.builder or read_context("builder"),
        "principles": req.principles or read_context("principles"),
        "codebase": req.codebase or read_context("codebase"),
        "references": req.references or read_context("references"),
    }

    repo = current_app.workflow_repository
    workflow = repo.get(_WORKFLOW_NAME)

    execution = WorkflowExecution(
        workflow_ref=_WORKFLOW_NAME,    # str, not WorkflowRef — Task 3 ships this typed loose
        inputs=inputs,
    )

    t0 = time.monotonic()
    runtime = WorkflowRuntime()
    outputs: dict[str, str] = {}

    for event in runtime.run(execution, workflow):
        if isinstance(event, StepCompleted):
            outputs[event.step_name] = event.output
        elif isinstance(event, StepFailed):
            return (
                jsonify({"error": event.error, "step": event.step_name, "status": 502}),
                502,
            )

    latency_ms = int((time.monotonic() - t0) * 1000)
    files = [
        BootstrapFile(filename=filename, content=outputs.get(step_name, ""))
        for step_name, filename in _STEP_TO_FILENAME.items()
    ]
    return jsonify(BootstrapProjectResponse(files=files, latencyMs=latency_ms).model_dump())
```

**Verify (import only — no server needed):**
```bash
python -c "from modules.spec_gen.routes import spec_gen_bp; print('blueprint ok:', spec_gen_bp.name)"
```

---

### Step 5 — Register the blueprint

**File:** `create_app.py` — edit `ENABLED_MODULES` list (lines 19–25):

```python
ENABLED_MODULES = [
    ('modules.projects.routes',  'projects_bp'),
    ('modules.context.routes',   'context_bp'),
    ('modules.ai.routes',        'ai_bp'),
    ('modules.templates.routes', 'templates_bp'),
    ('modules.task_gen.routes',  'task_gen_bp'),
    ('modules.spec_gen.routes',  'spec_gen_bp'),   # Task 5
]
```

**Verify:**
```bash
python -c "
from create_app import create_app
app = create_app({'TESTING': True})
rules = [r.rule for r in app.url_map.iter_rules()]
assert '/api/spec-gen/generate' in rules, f'route missing; got: {[r for r in rules if \"spec\" in r]}'
print('route registered ok')
"
```

---

### Step 6 — Add OpenAPI path

**File:** `openapi.yaml` — append after the last `paths` entry (before `components:`):

```yaml
  /api/spec-gen/generate:
    post:
      operationId: specGenGenerate
      summary: >
        Generate analysis, epic, and architecture documents via the
        spec_gen WorkflowRuntime (three sequential AI steps).
      tags:
        - spec-gen
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BootstrapProjectRequest'
      responses:
        '200':
          description: >
            Three generated spec files: analysis.md, epic.md, architecture.md.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BootstrapProjectResponse'
        '400':
          description: Validation error — missing required fields.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '502':
          description: AI provider error during a workflow step.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

**No `make generate-dtos` needed** — the request/response schemas already exist in `dtos/models.py`; no new component schemas were added.

**Verify:**
```bash
make check-dtos   # must pass; dtos/models.py must not be stale
```

---

### Step 7 — Add structural test

**File:** `tests/test_structural.py` — append after `gunicorn_inProdRequirements` (after line 46):

```python

def featureModules_mustNotLoadWorkflowsDirectly():
    """Feature route files must not import from modules.workflows.repository directly.

    Rule: feature code touches only WorkflowRuntime (Layer D) and app.workflow_repository
          (injected at app startup). Direct imports of WorkflowRepositoryFs or the
          repository sub-package from inside a feature module bypass the port and
          break the Bounded Context.
    Fix:  Use current_app.workflow_repository inside the route handler, not a
          direct import of the FS adapter.
    """
    feature_dirs = [
        p for p in (_REPO_ROOT / "modules").iterdir()
        if p.is_dir() and p.name not in {"workflows", "__pycache__"}
    ]
    violations = []
    for feature_dir in feature_dirs:
        for py_file in feature_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if "modules.workflows.repository" in text or "from modules.workflows import repository" in text:
                violations.append(str(py_file.relative_to(_REPO_ROOT)))

    assert not violations, (
        "Feature modules must not import modules.workflows.repository directly.\n"
        "Use current_app.workflow_repository (injected by WorkflowRepositoryFs at startup).\n"
        "Violations:\n" + "\n".join(f"  {v}" for v in violations)
    )
```

**Verify:**
```bash
python -m pytest tests/test_structural.py -v
```

---

## 5. Tests

**File:** `modules/spec_gen/tests/test_routes.py` (new)

Uses `pytest`, `unittest.mock`, and the app's existing test infrastructure. Mirrors the pattern in `modules/task_gen/tests/test_routes.py`.

```python
"""Tests for POST /api/spec-gen/generate.

Strategy:
- Unit tests mock WorkflowRuntime to avoid AI calls.
- Integration smoke test uses CHAIN_PROVIDER=mock if present.
- All tests use a minimal Flask test client from create_app().
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from create_app import create_app
from modules.workflows.events import StepCompleted, StepFailed
from modules.workflows.workflow import Workflow


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    """Flask app in test mode with a stubbed workflow_repository."""
    application = create_app({"TESTING": True})

    stub_repo = MagicMock()
    stub_workflow = MagicMock(spec=Workflow)
    stub_workflow.name = "generate-spec"
    stub_repo.get.return_value = stub_workflow

    application.workflow_repository = stub_repo
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _valid_body(**overrides) -> dict:
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


def _make_events(outputs: dict[str, str]) -> list:
    """Produce StepCompleted events for each step name → output mapping."""
    return [
        StepCompleted(
            execution_id="test-exec-id",
            step_name=name,
            output=text,
            duration_ms=100,
        )
        for name, text in outputs.items()
    ]


# ── Happy path ────────────────────────────────────────────────────────────────

def test_generate_returns_200_with_three_files(client):
    events = _make_events({
        "analysis": "# Analysis",
        "epic": "# Epic",
        "architecture": "# Architecture",
    })
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=_valid_body())

    assert resp.status_code == 200
    data = resp.get_json()
    assert "files" in data
    filenames = {f["filename"] for f in data["files"]}
    assert filenames == {"analysis.md", "epic.md", "architecture.md"}


def test_generate_file_contents_match_step_outputs(client):
    events = _make_events({
        "analysis": "# Analysis content",
        "epic": "# Epic content",
        "architecture": "# Architecture content",
    })
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=_valid_body())

    files = {f["filename"]: f["content"] for f in resp.get_json()["files"]}
    assert files["analysis.md"] == "# Analysis content"
    assert files["epic.md"] == "# Epic content"
    assert files["architecture.md"] == "# Architecture content"


def test_generate_returns_latency_ms(client):
    events = _make_events({"analysis": "a", "epic": "e", "architecture": "ar"})
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        resp = client.post("/api/spec-gen/generate", json=_valid_body())

    data = resp.get_json()
    assert isinstance(data["latencyMs"], int)
    assert data["latencyMs"] >= 0


def test_generate_passes_inputs_to_execution(client, app):
    """WorkflowExecution receives all six input keys."""
    events = _make_events({"analysis": "a", "epic": "e", "architecture": "ar"})
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime, \
         patch("modules.spec_gen.routes.WorkflowExecution") as MockExec:
        MockRuntime.return_value.run.return_value = iter(events)
        MockExec.new.return_value = MagicMock()
        client.post(
            "/api/spec-gen/generate",
            json=_valid_body(builder="my builder", principles="p", codebase="c", references="r"),
        )

    call_kwargs = MockExec.new.call_args.kwargs
    inputs = call_kwargs["inputs"]
    assert inputs["project_name"] == "Test Project"
    assert inputs["braindump"] == "We need to build a thing."
    assert inputs["builder"] == "my builder"
    assert inputs["principles"] == "p"
    assert inputs["codebase"] == "c"
    assert inputs["references"] == "r"


def test_generate_loads_correct_workflow_name(client, app):
    events = _make_events({"analysis": "a", "epic": "e", "architecture": "ar"})
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter(events)
        client.post("/api/spec-gen/generate", json=_valid_body())

    app.workflow_repository.get.assert_called_once_with("spec_gen/generate-spec")


def test_generate_uses_context_fallback_when_request_fields_empty(client, app):
    """Empty builder/principles/codebase/references fall back to read_context()."""
    events = _make_events({"analysis": "a", "epic": "e", "architecture": "ar"})
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime, \
         patch("modules.spec_gen.routes.read_context") as mock_ctx, \
         patch("modules.spec_gen.routes.WorkflowExecution") as MockExec:
        mock_ctx.side_effect = lambda key: f"ctx-{key}"
        MockRuntime.return_value.run.return_value = iter(events)
        MockExec.new.return_value = MagicMock()
        client.post("/api/spec-gen/generate", json=_valid_body())  # all context fields ""

    inputs = MockExec.new.call_args.kwargs["inputs"]
    assert inputs["builder"] == "ctx-builder"
    assert inputs["principles"] == "ctx-principles"
    assert inputs["codebase"] == "ctx-codebase"
    assert inputs["references"] == "ctx-references"


# ── Step failure ──────────────────────────────────────────────────────────────

def test_generate_returns_502_on_step_failed(client):
    fail_event = StepFailed(
        execution_id="test-exec-id",
        step_name="analysis",
        error="provider timeout",
        duration_ms=50,
    )
    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = iter([fail_event])
        resp = client.post("/api/spec-gen/generate", json=_valid_body())

    assert resp.status_code == 502
    data = resp.get_json()
    assert data["error"] == "provider timeout"
    assert data["step"] == "analysis"


def test_generate_halts_after_first_step_failed(client):
    """Runtime generator is not further drained after a StepFailed."""
    fail_event = StepFailed(
        execution_id="x", step_name="analysis", error="boom", duration_ms=10
    )
    exhausted = []

    def gen():
        yield fail_event
        exhausted.append(True)   # must not reach here

    with patch("modules.spec_gen.routes.WorkflowRuntime") as MockRuntime:
        MockRuntime.return_value.run.return_value = gen()
        client.post("/api/spec-gen/generate", json=_valid_body())

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


# ── Workflow registration ─────────────────────────────────────────────────────

def test_register_workflows_saves_generate_spec(app):
    """register_workflows calls repo.save with the correct workflow name."""
    from modules.spec_gen.workflows.generate_spec import register_workflows

    stub_repo = MagicMock()
    register_workflows(stub_repo)

    stub_repo.save.assert_called_once()
    saved_workflow = stub_repo.save.call_args.args[0]
    assert saved_workflow.name == "generate-spec"


def test_workflow_has_three_steps():
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    assert len(w.steps) == 3
    assert w.steps[0].name == "analysis"
    assert w.steps[1].name == "epic"
    assert w.steps[2].name == "architecture"


def test_workflow_declares_required_inputs():
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    assert set(w.inputs) == {"braindump", "project_name", "builder", "principles", "codebase", "references"}


def test_workflow_declares_outputs():
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    assert set(w.outputs) == {"analysis", "epic", "architecture"}


def test_analysis_step_input_keys_subset_of_workflow_inputs():
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    analysis_step = w.steps[0]
    assert set(analysis_step.input_keys) <= set(w.inputs)


def test_epic_step_takes_analysis_output():
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    epic_step = w.steps[1]
    assert "analysis" in epic_step.input_keys


def test_architecture_step_takes_epic_output():
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    arch_step = w.steps[2]
    assert "epic" in arch_step.input_keys


def test_each_step_has_distinct_name():
    """Step names double as output keys in context.outputs — they must be unique."""
    from modules.spec_gen.workflows.generate_spec import _build_workflow

    w = _build_workflow()
    names = [s.name for s in w.steps]
    assert len(names) == len(set(names)), f"duplicate step name across steps: {names}"


# ── Prompt format strings ────────────────────────────────────────────────────

def test_analysis_user_template_renders_without_error():
    from modules.spec_gen.prompts import ANALYSIS_USER

    ctx = {"braindump": "test dump", "project_name": "My Project", "builder": ""}
    rendered = ANALYSIS_USER.format(**ctx)
    assert "My Project" in rendered
    assert "test dump" in rendered


def test_epic_user_template_renders_with_prior_analysis():
    from modules.spec_gen.prompts import EPIC_USER

    ctx = {
        "braindump": "bd", "project_name": "P", "builder": "", "principles": "", "analysis": "# Analysis"
    }
    rendered = EPIC_USER.format(**ctx)
    assert "# Analysis" in rendered
    assert "Epic: P" in rendered


def test_architecture_user_template_renders_with_epic():
    from modules.spec_gen.prompts import ARCHITECTURE_USER

    ctx = {
        "braindump": "bd", "project_name": "P", "builder": "", "principles": "",
        "epic": "# Epic", "codebase": "", "references": "",
    }
    rendered = ARCHITECTURE_USER.format(**ctx)
    assert "# Epic" in rendered
```

---

## 6. Commit Plan

Three atomic commits. Each must pass `make test` before the next begins.

**Commit A — Prompt constants and workflow definition**
```
git add modules/spec_gen/__init__.py \
        modules/spec_gen/prompts.py \
        modules/spec_gen/workflows/__init__.py \
        modules/spec_gen/workflows/generate_spec.py
git commit -m "feat(spec_gen): add prompts and generate-spec workflow definition

Introduces modules/spec_gen with AICall-based three-step workflow
(analysis → epic → architecture). register_workflows() convention
satisfies WorkflowRepositoryFs discovery. No routes wired yet."
```

**Commit B — Route, blueprint registration, openapi path**
```
git add modules/spec_gen/routes.py \
        modules/spec_gen/tests/__init__.py \
        modules/spec_gen/tests/test_routes.py \
        create_app.py \
        openapi.yaml
git commit -m "feat(spec_gen): wire POST /api/spec-gen/generate via WorkflowRuntime

Route handler loads spec_gen/generate-spec from app.workflow_repository,
drains WorkflowRuntime generator, returns analysis/epic/architecture files.
No inline AI calls in the handler. Adds 22 tests."
```

**Commit C — Structural test**
```
git add tests/test_structural.py
git commit -m "test(structural): featureModules_mustNotLoadWorkflowsDirectly

Enforces the Bounded Context invariant: feature route files may not
import modules.workflows.repository directly; they use the injected
app.workflow_repository. Mirrors the existing provider-boundary guardrail."
```

---

## 7. Verification

Run in order. Each step must pass before proceeding to the next.

```bash
# 1. All new tests green
python -m pytest modules/spec_gen/tests/ -v

# 2. Structural tests all pass
python -m pytest tests/test_structural.py -v

# 3. Full suite — expect +22 vs baseline N captured in §2 Pre-flight, zero pre-existing failures
python -m pytest -q 2>&1 | tail -5

# 4. DTOs still in sync with openapi.yaml
make check-dtos

# 5. Route exists in the running app
python -c "
from create_app import create_app
app = create_app({'TESTING': True})
rules = [r.rule for r in app.url_map.iter_rules()]
assert '/api/spec-gen/generate' in rules
print('OK — /api/spec-gen/generate registered')
"

# 6. End-to-end smoke (requires CHAIN_PROVIDER=mock in environment)
CHAIN_PROVIDER=mock python -c "
from create_app import create_app
app = create_app({'TESTING': True})
with app.test_client() as c:
    r = c.post('/api/spec-gen/generate', json={
        'project_name': 'Smoke Test',
        'braindump': 'We are building a thing to test workflows.',
    })
    assert r.status_code == 200, f'got {r.status_code}: {r.data}'
    data = r.get_json()
    assert len(data['files']) == 3
    print('smoke ok — files:', [f[\"filename\"] for f in data[\"files\"]])
"
```

---

## 8. Rollback

If any step fails and the commit has not been pushed:

```bash
# Revert create_app.py to remove spec_gen from ENABLED_MODULES
git checkout -- create_app.py openapi.yaml tests/test_structural.py

# Remove the new module entirely
rm -rf modules/spec_gen/
```

If Commit B has been pushed to a branch (not `master` — direct push is blocked):

```bash
git revert HEAD   # revert Commit B; keep Commit A (pure additions, no breakage)
```

The existing `bootstrap_project` in `ai/routes.py` and `generate_spec` in `ai/routes.py` are untouched throughout; existing callers are unaffected by rollback.

---

## 9. Deviations Allowed

| Deviation | Condition |
|---|---|
| Field name on `WorkflowExecution` differs from constructor signature shown above | Task 3 ships only the dataclass constructor (no factory `.new()`), with `workflow_ref: str`. Adjust the call in `routes.py` if the dataclass field set has changed since this guide was written. |
| `StepCompleted.output` field is named differently (e.g. `result`, `value`) | Per the contract settled in Task 1.1 the field is `output`. If a downstream change renames it, replace `event.output` with the new name in `routes.py` and the `_make_events` helper. |
| `StepFailed.error` field is named differently (e.g. `message`) | Same — Task 1.1 names it `error`. Adjust if a downstream change renames it. |
| `WorkflowRepositoryFs` discovery uses `def workflows(repo)` instead of `register_workflows(repo)` | Rename the function in `generate_spec.py`; keep the internal logic identical |
| Tasks 1.1, 1.2, 2, 3, 4 not yet implemented | This task cannot proceed without them. Stop and unblock those first — do not stub the runtime or repository here. |

---

## 10. Out of Scope

- Modifying or deleting `modules/ai/routes.py` — `bootstrap_project` and `generate_spec` stay; this task adds a parallel implementation, it does not retire the old one
- Streaming SSE responses from `WorkflowRuntime` — the route drains the generator synchronously and returns a single JSON response; SSE is a Phase 1 follow-up tied to the GUI progress indicator
- `spec-doc-spec.md` as a fourth AI step — the bootstrap_project reference implementation omits it from AI calls; it is out of scope here and may be added in a follow-on task when the prompt is defined
- `WorkflowRepositoryDb` — the port exists; no database adapter is built here
- Retiring `task_gen`'s threading status dict — Task 3 absorbs this; Task 5 does not modify `task_gen`
- JSON workflow format — Phase 3; the `generate_spec.py` Python Builder definition is the Phase 1 form
- GUI integration or frontend changes — backend contract only
- Prompt quality parity with `bootstrap_project` — the new prompts are structurally correct format strings; prompt tuning is a separate concern