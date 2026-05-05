# Task 1 Implementation Guide: Define `BOOTSTRAP_WORKFLOW`

## 1. Context

The bootstrap endpoint today drives three sequential AI calls synchronously over a held HTTP connection — a structural failure mode the architecture traces to 10–25 minute `braindump` chain durations that no timeout tuning can fix. The fix decouples HTTP from chain execution: the POST returns a job ID in milliseconds, and a daemon thread owns the chain. For that pattern to work, bootstrap must be a typed `WorkflowRuntime` consumer — the same contract already satisfied by `task_gen` and `spec_gen/generate-spec`. This task produces exactly that: a four-step `Workflow` registered under `spec_gen/bootstrap-project`, using `AICall` for each AI phase (analysis → epic → architecture) and a `Compute` step that marshals `ChainResult` outputs into the `BootstrapFile` list the status endpoint will surface. No routes change here; this is the workflow object and its compute callable only.

**Trade-offs considered:**
- **Use three `Compute` steps (one per AI call) to call `bootstrap_*_prompt` functions unchanged** — preserves existing signatures but collapses the AICall/Compute semantic split and forces each step to import `chain_adapter` directly; rejected because it defeats the purpose of `AICall` as a typed, uniform AI step.
- **Inline all six prompt strings directly in `bootstrap.py`** — eliminates a file-to-modify but duplicates prompt text already owned by `modules/ai/prompts/__init__.py`; rejected.
- **Extract named constants from `modules/ai/prompts/__init__.py`, consumed by `AICall` steps** — prompt text lives in one place, workflow definition stays ≤50 lines, and the existing `bootstrap_*_prompt` functions are left unchanged; chosen.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
cd {WORKSPACE}/spec-doc/api

git status                                      # Flag any unrelated M/?? entries
git diff HEAD -- modules/ai/prompts/__init__.py \
                 modules/spec_gen/workflows/ \
                 modules/spec_gen/tests/        # Confirm target scope is clean
make test                                       # Record baseline — expect 192 passing
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 192/192 passing.

---

## 3. Files

### To Create (new)
- `spec-doc/api/modules/spec_gen/workflows/bootstrap.py` — four-step workflow definition + `marshal_files` compute callable registered under `"bootstrap.marshal_files"`; ~48 lines; depends on `AICall`/`Compute`/`Workflow` from `modules/workflows/`, six prompt constants from `modules/ai/prompts/`, `BootstrapFile` from `dtos/models.py`, `StepContext` from `modules/workflows/steps/base.py`
- `spec-doc/api/modules/spec_gen/tests/test_bootstrap_workflow.py` — 13 pytest tests covering workflow shape, `marshal_files` behaviour, and registration; depends on the workflow file above and `ChainResult` from `modules/chain/types.py`

### To Modify (cite CODEBASE CONTEXT)
- `spec-doc/api/modules/ai/prompts/__init__.py` — current state: only `_REWRITE_SYSTEM` and `_GENERATE_BASE` top-level constants; target state: add six `BOOTSTRAP_*` named constants above the first `bootstrap_*_prompt` function (lines 127+); the three existing `bootstrap_*_prompt` functions are **not changed**

### To Leave Alone
- `spec-doc/api/modules/spec_gen/workflows/generate_spec.py` — reference implementation; do not modify
- `spec-doc/api/create_app.py` — `WorkflowRepositoryFs.from_modules_dir` auto-discovers any `register_workflows` in `modules/*/workflows/*.py`; no registration code required for this task
- `spec-doc/api/openapi.yaml` — no route changes in this task
- `spec-doc/api/dtos/models.py` — generated; never hand-edit; only **read** the `BootstrapFile` definition (confirmed: `filename: str`, `content: str`)
- `spec-doc/api/modules/ai/routes.py` — async POST handler and status endpoint are Task 2/3 scope
- `spec-doc/api/modules/spec_gen/tests/test_routes.py` — existing spec_gen route tests; do not touch

---

## 4. Implementation Steps

### Step 1: Read the three bootstrap prompt functions and extract named constants

**Action**: Read `modules/ai/prompts/__init__.py` lines 127–439. For each of the three `bootstrap_*_prompt` functions, identify:

1. **The base system string** — the literal passed as the first positional argument to `PromptBuilder(...)` before any `.section()` call appends dynamic content. This is the `AICall.system` value; it must be a static string with no `{}` placeholders.
2. **The user prompt body** — the string returned as the second element of the tuple. Convert any f-string (`f"…{var}…"`) into a `format_map`-compatible template (`"…{var}…"`). For references to a **prior step's AI output** (i.e., where the function receives `analysis: str` or `epic: str`), use attribute-access syntax: `{analysis.text}` and `{epic.text}`. Python's `str.format_map` natively resolves `{field.attr}` via `getattr`, and `ChainResult` (the object `AICall._invoke` stores in `context.outputs`) exposes `.text`.

Add the six constants **above** the first `bootstrap_*_prompt` function definition. Do not alter the functions themselves.

**File**: `spec-doc/api/modules/ai/prompts/__init__.py`

**Pattern**:
```python
# ── Bootstrap workflow prompt constants ───────────────────────────────────────
# Consumed by spec_gen/bootstrap-project AICall steps via format_map substitution.
# The existing bootstrap_*_prompt functions are NOT changed.

BOOTSTRAP_ANALYSIS_SYSTEM = (
    # Extract: the literal string passed to PromptBuilder() in bootstrap_analysis_prompt,
    # BEFORE any .section() calls.  Must be a plain string — no {}-placeholders.
    "<base system string from bootstrap_analysis_prompt>"
)

BOOTSTRAP_ANALYSIS_USER = (
    # Extract: the user prompt body from bootstrap_analysis_prompt.
    # Convert f-string vars to {key} format-map placeholders.
    # Active keys: {braindump}, {project_name}, {builder}
    "<user template extracted from bootstrap_analysis_prompt>"
)

BOOTSTRAP_EPIC_SYSTEM = (
    "<base system string from bootstrap_epic_prompt>"
)

BOOTSTRAP_EPIC_USER = (
    # Active keys: {braindump}, {project_name}, {builder}, {principles}
    # Prior-step output: {analysis.text}  ← ChainResult.text via format_map attr access
    # Where the function body contains the f-var `analysis` (a plain str),
    # the template uses {analysis.text} (ChainResult attribute access).
    "<user template — replace the f-var `analysis` with {analysis.text}>"
)

BOOTSTRAP_ARCHITECTURE_SYSTEM = (
    "<base system string from bootstrap_architecture_prompt>"
)

BOOTSTRAP_ARCHITECTURE_USER = (
    # Active keys: {braindump}, {project_name}, {builder}, {principles},
    #              {codebase}, {references}
    # Prior-step output: {epic.text}  ← ChainResult.text via format_map attr access
    "<user template — replace the f-var `epic` with {epic.text}>"
)
```

**Key adaptation — PromptBuilder user prompts**: If the user body is assembled via `PromptBuilder` rather than a direct f-string, unroll each `.section("Heading", var)` call into `"\n\n## Heading\n{var}"` in the template. The semantics are identical; `PromptBuilder.section` is a convenience wrapper around that exact pattern.

**Verify**:
```bash
python -c "
from modules.ai.prompts import (
    BOOTSTRAP_ANALYSIS_SYSTEM, BOOTSTRAP_ANALYSIS_USER,
    BOOTSTRAP_EPIC_SYSTEM,     BOOTSTRAP_EPIC_USER,
    BOOTSTRAP_ARCHITECTURE_SYSTEM, BOOTSTRAP_ARCHITECTURE_USER,
)
for name, val in [
    ('BOOTSTRAP_ANALYSIS_SYSTEM',     BOOTSTRAP_ANALYSIS_SYSTEM),
    ('BOOTSTRAP_ANALYSIS_USER',       BOOTSTRAP_ANALYSIS_USER),
    ('BOOTSTRAP_EPIC_SYSTEM',         BOOTSTRAP_EPIC_SYSTEM),
    ('BOOTSTRAP_EPIC_USER',           BOOTSTRAP_EPIC_USER),
    ('BOOTSTRAP_ARCHITECTURE_SYSTEM', BOOTSTRAP_ARCHITECTURE_SYSTEM),
    ('BOOTSTRAP_ARCHITECTURE_USER',   BOOTSTRAP_ARCHITECTURE_USER),
]:
    assert isinstance(val, str) and len(val) > 0, f'{name} must be a non-empty string'
print('OK — 6 constants imported, all non-empty strings')
"
```
Expect: `OK — 6 constants imported, all non-empty strings`

> **Commit after this step** — see Commit Plan item 1.

---

### Step 2: Create the workflow file

**Action**: Create `modules/spec_gen/workflows/bootstrap.py`. Port the four-step shape directly from `modules/spec_gen/workflows/generate_spec.py`, substituting bootstrap imports, step names, `input_keys`, `max_tokens=16384` on the architecture step, and appending the `Compute` step. Register `marshal_files` with `@register_compute` at module level so it lands in `CallableRegistry` when the auto-discovery import fires.

Import `ChainResult` from `modules.chain.types` (confirmed: `modules/chain/adapter.py` line 18 reads `from .types import ChainResult`). Import `BootstrapFile` from `dtos.models` (confirmed: `filename: str`, `content: str`).

**File**: `spec-doc/api/modules/spec_gen/workflows/bootstrap.py` (new)

**Pattern** (ported from `generate_spec.py`):
```python
"""Registers the spec_gen/bootstrap-project workflow."""
from __future__ import annotations

from dtos.models import BootstrapFile
from modules.ai.prompts import (
    BOOTSTRAP_ANALYSIS_SYSTEM,
    BOOTSTRAP_ANALYSIS_USER,
    BOOTSTRAP_EPIC_SYSTEM,
    BOOTSTRAP_EPIC_USER,
    BOOTSTRAP_ARCHITECTURE_SYSTEM,
    BOOTSTRAP_ARCHITECTURE_USER,
)
from modules.chain.types import ChainResult  # noqa: F401 — used in marshal_files type context
from modules.workflows.steps.ai_call import AICall
from modules.workflows.steps.base import StepContext
from modules.workflows.steps.compute import Compute
from modules.workflows.steps.registry import register_compute
from modules.workflows.workflow import Workflow


@register_compute("bootstrap.marshal_files")
def marshal_files(context: StepContext) -> list[BootstrapFile]:
    """Convert AICall ChainResult outputs into a BootstrapFile list."""
    return [
        BootstrapFile(filename="analysis.md",    content=context.outputs["analysis"].text),
        BootstrapFile(filename="epic.md",         content=context.outputs["epic"].text),
        BootstrapFile(filename="architecture.md", content=context.outputs["architecture"].text),
    ]


def _build_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-project")   # _PrefixedRepo prepends spec_gen/
        .inputs(
            "braindump",
            "project_name",
            "builder",
            "principles",
            "codebase",
            "references",
        )
        .outputs("analysis", "epic", "architecture", "files")
        .step(
            AICall(
                name="analysis",
                system=BOOTSTRAP_ANALYSIS_SYSTEM,
                prompt_template=BOOTSTRAP_ANALYSIS_USER,
                input_keys=("braindump", "project_name", "builder"),
            )
        )
        .step(
            AICall(
                name="epic",
                system=BOOTSTRAP_EPIC_SYSTEM,
                prompt_template=BOOTSTRAP_EPIC_USER,
                input_keys=("braindump", "project_name", "builder", "principles"),
            )
        )
        .step(
            AICall(
                name="architecture",
                system=BOOTSTRAP_ARCHITECTURE_SYSTEM,
                prompt_template=BOOTSTRAP_ARCHITECTURE_USER,
                input_keys=(
                    "braindump",
                    "project_name",
                    "builder",
                    "principles",
                    "codebase",
                    "references",
                ),
                max_tokens=16384,               # per braindump-raise-max-tokens.md
            )
        )
        .step(Compute(name="files", fn_name="bootstrap.marshal_files"))
        .build()
    )


def register_workflows(repo) -> None:
    """Called by WorkflowRepositoryFs auto-discovery at app startup."""
    repo.save(_build_workflow())
```

**Verify**:
```bash
python -c "
from modules.spec_gen.workflows.bootstrap import _build_workflow
wf = _build_workflow()
assert wf.step_count == 4, f'Expected 4 steps, got {wf.step_count}'
assert str(wf.ref) == 'bootstrap-project', f'Got ref: {wf.ref}'
print('PASS: ref=%s  steps=%d' % (wf.ref, wf.step_count))
"
```
Expect: `PASS: ref=bootstrap-project  steps=4`

> **Commit after this step** — see Commit Plan item 2.

---

### Step 3: Write and run tests

**Action**: Create `modules/spec_gen/tests/test_bootstrap_workflow.py` (the directory and `__init__.py` already exist). Run the suite to confirm all 13 tests pass before committing.

**File**: `spec-doc/api/modules/spec_gen/tests/test_bootstrap_workflow.py` (new)

**Pattern**:
```python
"""Tests for the spec_gen/bootstrap-project workflow definition."""
from __future__ import annotations

import pytest

from dtos.models import BootstrapFile
from modules.chain.types import ChainResult
from modules.spec_gen.workflows.bootstrap import _build_workflow, marshal_files, register_workflows
from modules.workflows.steps.ai_call import AICall
from modules.workflows.steps.base import StepContext
from modules.workflows.steps.compute import Compute
from modules.workflows.steps.registry import get as registry_get


class TestBootstrapWorkflowShape:
    def test_step_count_is_four(self):
        wf = _build_workflow()
        assert wf.step_count == 4, f"Expected 4 steps, got {wf.step_count}"

    def test_step_0_is_aicall_named_analysis(self):
        wf = _build_workflow()
        step = wf.steps[0]
        assert isinstance(step, AICall)
        assert step.name == "analysis"

    def test_step_1_is_aicall_named_epic(self):
        wf = _build_workflow()
        step = wf.steps[1]
        assert isinstance(step, AICall)
        assert step.name == "epic"

    def test_step_2_is_aicall_named_architecture_with_max_tokens_16384(self):
        wf = _build_workflow()
        step = wf.steps[2]
        assert isinstance(step, AICall)
        assert step.name == "architecture"
        assert step.max_tokens == 16384, (
            f"architecture step must carry max_tokens=16384 per braindump-raise-max-tokens.md; "
            f"got {step.max_tokens}"
        )

    def test_step_3_is_compute_named_files(self):
        wf = _build_workflow()
        step = wf.steps[3]
        assert isinstance(step, Compute)
        assert step.name == "files"
        assert step.fn_name == "bootstrap.marshal_files"

    def test_workflow_ref_name_is_bootstrap_project(self):
        wf = _build_workflow()
        assert str(wf.ref) == "bootstrap-project"

    def test_workflow_inputs_are_complete(self):
        wf = _build_workflow()
        assert wf.inputs == frozenset(
            {"braindump", "project_name", "builder", "principles", "codebase", "references"}
        )

    def test_analysis_input_keys(self):
        wf = _build_workflow()
        step = wf.steps[0]
        assert set(step.input_keys) == {"braindump", "project_name", "builder"}

    def test_architecture_input_keys_include_codebase_and_references(self):
        wf = _build_workflow()
        step = wf.steps[2]
        keys = set(step.input_keys)
        assert "codebase" in keys, "architecture step must declare codebase as required input"
        assert "references" in keys, "architecture step must declare references as required input"


class TestMarshalFiles:
    def _ctx(self, analysis: str = "a", epic: str = "b", arch: str = "c") -> StepContext:
        return StepContext(
            run_id="test-run",
            inputs={},
            outputs={
                "analysis":     ChainResult(text=analysis, latency_ms=1),
                "epic":         ChainResult(text=epic,     latency_ms=1),
                "architecture": ChainResult(text=arch,     latency_ms=1),
            },
        )

    def test_returns_three_bootstrap_file_instances(self):
        result = marshal_files(self._ctx())
        assert len(result) == 3
        assert all(isinstance(f, BootstrapFile) for f in result)

    def test_filenames_in_order(self):
        result = marshal_files(self._ctx())
        assert result[0].filename == "analysis.md"
        assert result[1].filename == "epic.md"
        assert result[2].filename == "architecture.md"

    def test_content_comes_from_chainresult_text(self):
        result = marshal_files(self._ctx(analysis="alpha", epic="beta", arch="gamma"))
        assert result[0].content == "alpha"
        assert result[1].content == "beta"
        assert result[2].content == "gamma"


class TestWorkflowRegistration:
    def test_register_workflows_saves_under_bootstrap_project(self):
        saved: dict = {}

        class _MockRepo:
            def save(self, workflow) -> None:
                saved[str(workflow.ref)] = workflow

        register_workflows(_MockRepo())

        assert "bootstrap-project" in saved, (
            "register_workflows must save a workflow whose ref.name is 'bootstrap-project'"
        )
        wf = saved["bootstrap-project"]
        assert wf.step_count == 4
```

**Verify**:
```bash
python -m pytest modules/spec_gen/tests/test_bootstrap_workflow.py -v
```
Expect: **13 collected, 13 passed, 0 errors**.

> **Commit after this step** — see Commit Plan item 3.

---

## 5. Tests

Covered in full in Step 3 above. All 13 assertion bodies are complete — no stubs. The test file uses bare `assert` with failure messages, matching the repo's existing `modules/workflows/tests/` convention. No `autouse` registry-clearing fixture is needed here because `modules/spec_gen/tests/conftest.py` does not define one (the clearing fixture lives only in `modules/workflows/tests/conftest.py`), and `marshal_files` is registered once at import time — which is the correct production behaviour.

---

## 6. Commit Plan

**Executor instruction**: commit after **each step** completes — not at the end of the task. Run the commit command before moving to the next step.

1. `feat(prompts): extract BOOTSTRAP_*_SYSTEM and BOOTSTRAP_*_USER constants` — after Step 1 passes verify — file: `modules/ai/prompts/__init__.py`; adds six named constants above existing `bootstrap_*_prompt` functions; functions unchanged
2. `feat(spec_gen): add BOOTSTRAP_WORKFLOW definition and marshal_files compute step` — after Step 2 passes verify — file: `modules/spec_gen/workflows/bootstrap.py` (new); registers workflow `bootstrap-project` and callable `bootstrap.marshal_files`
3. `test(spec_gen): bootstrap workflow shape, marshal_files, and registration` — after Step 3 suite passes — file: `modules/spec_gen/tests/test_bootstrap_workflow.py` (new); 13 tests, 0 stubs

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
make test
```

**Expected delta**: 192 → 205 passing (13 new tests). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` undoes exactly one step.
- **Per-branch**: if verification fails catastrophically:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destructive
  ```
  or delete the feature branch entirely and re-branch from the pre-task SHA.

---

## 9. Deviations Allowed

- **`ChainResult` import path differs from `modules.chain.types`** → read `modules/chain/adapter.py` line 18 (confirmed: `from .types import ChainResult`); if the module has been relocated, grep for `class ChainResult` and adjust both the workflow file and the test file; note in commit body.
- **`ChainResult` constructor signature differs** → if `ChainResult` is not a dataclass with `text` and `latency_ms`, read `modules/chain/types.py` and adjust `self._ctx()` in the test accordingly; note in commit body.
- **`modules/spec_gen/tests/` does not exist** → create the directory and an empty `__init__.py` before creating the test file; flag as deviation.
- **User prompt body is assembled via `PromptBuilder` rather than an f-string** → unroll each `.section("Heading", var)` call into `"\n\n## Heading\n{var}"` in the template string; semantics are identical; note the unrolling in the commit body.
- **`Compute` constructor does not accept `fn_name` as a keyword arg** → read `modules/workflows/steps/compute.py` to find the correct field name; adjust accordingly.
- **`WorkflowRepositoryFs` auto-discovery does not pick up the new file** → read `create_app.py` discovery logic; if it requires explicit registration, add an import or registration call to `create_app.py` and document as a deviation.
- **Side-effect required** (push, publish, schema change, `make generate-dtos`) → STOP, mark `[REQUIRES APPROVAL]` and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log in the commit body.

---

## 10. Out of Scope

This task delivers only the `Workflow` object and its compute callable. Nothing routes through `BOOTSTRAP_WORKFLOW` yet — the workflow cannot be exercised end-to-end until the POST handler (Task 2) dispatches it via `WorkflowRuntime`. The following items are explicitly out of scope and must not be absorbed:

- **Async POST handler (`bootstrap_project` route)** — Task 2 scope; creates and dispatches `WorkflowExecution` in a daemon thread; lives in `modules/ai/routes.py`
- **Status endpoint (`bootstrap_status` route)** — Task 3 scope; reads `WorkflowExecution` state and evicts on first terminal read
- **`_BOOTSTRAP_JOBS` in-process registry dict** — Task 2 scope; module-scope dict co-located with both route handlers
- **OpenAPI `BootstrapJobStatus` schema and new path entries** — Task 3/4 scope; deferred until routes are defined
- **`make generate-dtos` re-run** — depends on openapi.yaml changes, which are not in this task
- **Angular polling client (`startBootstrapProject`, `getBootstrapStatus`)** — frontend scope; separate repo
- **SSE progress streaming for bootstrap** — `braindump-streaming-task-gen.md` epic; arrives after this epic lands
- **Refactoring `bootstrap_*_prompt` functions to reference the new constants internally** — optional maintainability follow-up; the functions work unchanged and the refactor is a separate pass with its own test impact
- **Promoting `chain.adapter` to first-class infrastructure with a formal adapter boundary** — three consumers is the named trigger; deferred to a follow-on epic

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale and component descriptions this guide implements
- [Epic](./epic.md) — Task list and scope boundaries
- [Timeline](./timeline.md) — Update task status to `done` after `make test` shows 192 → 205