# Task 3: Workflow Runtime — Implementation Guide

## 1. Context

This task builds Layer D of the five-layer workflow architecture: the execution engine that turns a `Workflow` aggregate into a controlled, observable stream of typed domain events. `WorkflowExecution` is the Command object encapsulating a workflow run request; its embedded `ExecutionStatus` state machine (NEW → IN_PROGRESS → COMPLETED | ERROR | TIMEOUT | CANCELLING → CANCELLED) is the single status-tracking path for all workflow runs. `WorkflowRuntime` is a synchronous Python generator that iterates a workflow's steps in order, wrapping each invocation to yield `StepStarted`, `StepCompleted`, and `StepFailed` frozen Pydantic models. As a structural side-effect of building this layer, `task_gen`'s flat module-level `STATE` dict is replaced by a `dict[str, WorkflowExecution]` — eliminating the second, parallel status-tracking system that the Analysis document names as the primary divergence risk. The existing `task_gen` HTTP routes stay functional throughout; their internal implementation is re-backed by `WorkflowExecution` so callers see no change.

**Trade-offs considered:**

- **Generator-per-call vs. shared event bus** — a shared in-process event bus (e.g., blinker signals) would let observers subscribe at module load time, but it introduces global mutable state and implicit coupling that is harder to test in isolation; the generator is explicit, easily drained in tests without any HTTP layer, and directly composable with SSE.
- **Async generator vs. synchronous generator** — the existing `chain.adapter` CLI subprocess provider is synchronous; converting it requires an async rewrite with no concrete latency SLA to justify it; synchronous generators handle every current feature and the switch to async is a targeted Phase 2 decision tied to the `Parallel` step kind.
- **WorkflowRuntime emitting events vs. AbstractStep emitting events via injected collector** — the architecture describes AbstractStep's Template Method as sealing event emission; in Phase 1, before AbstractStep ships, placing emission in the runtime is the simplest testable design that satisfies the port budget; the protocol boundary (`StepProtocol.execute → str`) is narrow enough that it can be refined when Tasks 1/2 deliver the full AbstractStep without changing the runtime's external shape.

---

## 2. Pre-flight

Run BEFORE editing any file. All commands from `{WORKSPACE}/spec-doc/api/`.

```bash
# Confirm working tree is clean on target files
git status

git diff HEAD -- \
  modules/task_gen/service.py \
  modules/task_gen/tests/test_routes.py \
  tests/test_structural.py

# Confirm Tasks 1 + 2 contracts are present (this task depends on them)
# If either check fails, STOP — raise the dependency gap before continuing.
python -m pytest --collect-only -q 2>&1 | grep -E "workflows|AbstractStep|AICall|Workflow" || true
ls modules/ | sort

# Baseline test count — record the integer before any edits
python -m pytest -q 2>&1 | tail -5
```

**If working tree is dirty on target files**: `git stash` unrelated changes first.

**Dependency check**: Tasks 1 and 2 deliver `AbstractStep`, `AICall`, `Compute`, and `Workflow` (Layers B and C). If `modules/workflows/` does not yet contain those, the runtime tests use `StepProtocol`-conformant stubs (created in Step 1). Flag in the Step 4 commit body if `AbstractStep` is absent and the stubs are being used for the whole test run.

**Baseline recorded**: 192 / 192 passing.

---

## 3. Files

### To Create (new)

- `modules/workflows/__init__.py` — public API surface; imports from all sibling modules
- `modules/workflows/types.py` — `StepProtocol` and `WorkflowProtocol` (`typing.Protocol`); make the runtime independently testable before Tasks 1/2 ship concrete step types
- `modules/workflows/events.py` — `StepStarted`, `StepCompleted`, `StepFailed` frozen Pydantic models; `StepEvent` union alias
- `modules/workflows/execution.py` — `ExecutionStatus` enum, `InvalidStatusTransition` exception, `WorkflowExecution` dataclass with `.start()`, `.complete()`, `.fail()`, `.timeout()`, `.request_cancel()`, `.cancel()` transition helpers
- `modules/workflows/runtime.py` — `WorkflowRuntime` class with `run(execution, workflow) → Iterator[StepEvent]`
- `modules/workflows/tests/__init__.py` — empty package marker
- `modules/workflows/tests/conftest.py` — shared fixtures: `mock_step`, `two_step_workflow`, `fresh_execution`
- `modules/workflows/tests/test_events.py` — immutability, field presence, union coverage
- `modules/workflows/tests/test_execution.py` — every valid transition, every invalid transition, `is_running`/`is_terminal` predicates, `fail` sets `error`
- `modules/workflows/tests/test_runtime.py` — generator drain, step output propagation, failure halt, status progression

### To Modify (cite CODEBASE CONTEXT)

- `modules/task_gen/service.py` — currently line 36 `STATE: dict[str, dict] = {}` + `_LOCK` + `_initial_state()` + `_set_state()` pattern; replace with `_EXECUTIONS: dict[str, WorkflowExecution]` + updated `is_running`, `snapshot`, `start`, `run_generation` to use `WorkflowExecution` state machine
- `modules/task_gen/tests/test_routes.py` — currently line 79/81 `_svc.STATE.clear()` and line 122 `_svc.STATE[project_id] = {...}`; update to `_svc._EXECUTIONS.clear()` and inject a `WorkflowExecution` in IN_PROGRESS status
- `tests/test_structural.py` — currently has 2 structural invariant functions (`noPromptStrings_inRouteHandlers`, `gunicorn_inProdRequirements`); add `workflowsModule_doesNotImportChainProvidersDirectly`

### To Leave Alone

- `modules/chain/adapter.py` — runtime reaches AI only through AbstractStep._invoke → chain.adapter; no runtime-level AI imports
- `modules/chain/providers/` — internal to chain module; structural test enforces this boundary
- `dtos/models.py` — auto-generated from `openapi.yaml`; never hand-edit
- `openapi.yaml` — no new endpoints in this task; HTTP layer migration is Task 5
- `modules/ai/routes.py` — route migration (the "spec_gen" migration in the Architecture doc) is explicitly Task 5
- `modules/task_gen/routes.py` — routes delegate to `service.snapshot()` / `service.start()` whose external contracts are preserved; zero changes needed
- `modules/task_gen/tests/test_service_helpers.py` — tests only pure helper functions (`find_next_missing_task`, `extract_task_desc`, etc.) which are not touched by this task

---

## 4. Implementation Steps

### Step 1: Create `StepProtocol` and `WorkflowProtocol`

**Action**: Create the narrow Protocol definitions the runtime depends on. These decouple `WorkflowRuntime` from the concrete `AbstractStep` / `Workflow` types that Tasks 1/2 will produce. Any object satisfying the protocol — including the test stubs in `conftest.py` — is a valid runtime input.

**File**: `modules/workflows/types.py` (new)

**Pattern**:
```python
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StepProtocol(Protocol):
    """Minimal interface WorkflowRuntime requires from a step."""
    name: str

    def execute(self, inputs: dict[str, Any]) -> str:
        ...


@runtime_checkable
class WorkflowProtocol(Protocol):
    """Minimal interface WorkflowRuntime requires from a workflow."""
    name: str
    steps: list[StepProtocol]
```

**Verify**: `python -c "from modules.workflows.types import StepProtocol, WorkflowProtocol; print('ok')"` — prints `ok`.

---

### Step 2: Create domain event types

**Action**: Create the three frozen Pydantic domain events plus the `StepEvent` union alias. Frozen models enforce immutability so observers cannot mutate events in flight.

**File**: `modules/workflows/events.py` (new)

**Pattern**:
```python
from __future__ import annotations
from datetime import datetime
from typing import Union

from pydantic import BaseModel, ConfigDict


class StepStarted(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    step_name: str
    step_index: int
    started_at: datetime


class StepCompleted(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    step_name: str
    step_index: int
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    output: str


class StepFailed(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    step_name: str
    step_index: int
    started_at: datetime
    failed_at: datetime
    duration_ms: int
    error: str


StepEvent = Union[StepStarted, StepCompleted, StepFailed]
```

**Verify**: `python -c "from modules.workflows.events import StepStarted, StepCompleted, StepFailed, StepEvent; print('ok')"` — prints `ok`.

---

### Step 3: Create `ExecutionStatus` state machine and `WorkflowExecution`

**Action**: Implement the status enum with explicit valid-transition map, the `InvalidStatusTransition` exception, and the `WorkflowExecution` dataclass with convenience transition helpers. The transition map is the single authoritative encoding of the state machine; no other code branches on status strings.

**File**: `modules/workflows/execution.py` (new)

**Pattern**:
```python
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    NEW        = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED  = "COMPLETED"
    ERROR      = "ERROR"
    TIMEOUT    = "TIMEOUT"
    CANCELLING = "CANCELLING"
    CANCELLED  = "CANCELLED"


_VALID_TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    ExecutionStatus.NEW:        frozenset({ExecutionStatus.IN_PROGRESS}),
    ExecutionStatus.IN_PROGRESS: frozenset({
        ExecutionStatus.COMPLETED,
        ExecutionStatus.ERROR,
        ExecutionStatus.TIMEOUT,
        ExecutionStatus.CANCELLING,
    }),
    ExecutionStatus.CANCELLING: frozenset({ExecutionStatus.CANCELLED}),
    ExecutionStatus.COMPLETED:  frozenset(),
    ExecutionStatus.ERROR:      frozenset(),
    ExecutionStatus.TIMEOUT:    frozenset(),
    ExecutionStatus.CANCELLED:  frozenset(),
}


class InvalidStatusTransition(Exception):
    """Raised when a status transition not in _VALID_TRANSITIONS is attempted."""


@dataclass
class WorkflowExecution:
    """Command object encapsulating a workflow run request."""

    workflow_ref: str
    inputs: dict[str, Any]
    execution_id: str            = field(default_factory=lambda: str(uuid.uuid4()))
    submitted_at: datetime       = field(default_factory=datetime.utcnow)
    status: ExecutionStatus      = ExecutionStatus.NEW
    error: str | None            = None
    outputs: dict[str, Any]      = field(default_factory=dict)

    def transition(self, new_status: ExecutionStatus) -> None:
        allowed = _VALID_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidStatusTransition(
                f"Cannot transition {self.status.value} → {new_status.value}. "
                f"Allowed: {sorted(s.value for s in allowed) or '[]'}"
            )
        self.status = new_status

    def start(self)               -> None: self.transition(ExecutionStatus.IN_PROGRESS)
    def complete(self)            -> None: self.transition(ExecutionStatus.COMPLETED)
    def timeout(self)             -> None: self.transition(ExecutionStatus.TIMEOUT)
    def request_cancel(self)      -> None: self.transition(ExecutionStatus.CANCELLING)
    def cancel(self)              -> None: self.transition(ExecutionStatus.CANCELLED)

    def fail(self, error: str)    -> None:
        self.transition(ExecutionStatus.ERROR)
        self.error = error

    @property
    def is_running(self) -> bool:
        return self.status is ExecutionStatus.IN_PROGRESS

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ERROR,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
        }
```

**Verify**: `python -c "from modules.workflows.execution import WorkflowExecution, ExecutionStatus; e = WorkflowExecution('ref', {}); e.start(); e.complete(); print(e.status)"` — prints `ExecutionStatus.COMPLETED`.

---

### Step 4: Create `WorkflowRuntime`

**Action**: Implement the generator engine. It accepts a `WorkflowExecution` in NEW status and a `WorkflowProtocol`-conformant workflow, transitions the execution through its lifecycle, and yields one `StepStarted` + one `StepCompleted | StepFailed` per step. A failing step yields `StepFailed`, calls `execution.fail()`, and halts (`return`); the runtime never silently swallows step errors.

**File**: `modules/workflows/runtime.py` (new)

**Pattern**:
```python
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Iterator

from modules.workflows.events import (
    StepCompleted, StepEvent, StepFailed, StepStarted,
)
from modules.workflows.execution import WorkflowExecution
from modules.workflows.types import WorkflowProtocol


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _ms(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() * 1000))


class WorkflowRuntime:
    """Synchronous generator-based execution engine.

    Drainable directly in tests without an HTTP layer:
        for event in runtime.run(execution, workflow):
            ...
    The HTTP (SSE) layer is a thin wrapper over this iterator (Task 5).
    """

    def run(
        self,
        execution: WorkflowExecution,
        workflow: WorkflowProtocol,
    ) -> Iterator[StepEvent]:
        """Drive *execution* through *workflow*, yielding StepEvents.

        Precondition: execution.status is NEW.
        Raises InvalidStatusTransition if execution is not NEW.
        """
        execution.start()                        # NEW → IN_PROGRESS
        accumulated: dict[str, Any] = dict(execution.inputs)

        for index, step in enumerate(workflow.steps):
            started_at = _now()

            yield StepStarted(
                execution_id=execution.execution_id,
                step_name=step.name,
                step_index=index,
                started_at=started_at,
            )

            try:
                output = step.execute(accumulated)
                completed_at = _now()

                yield StepCompleted(
                    execution_id=execution.execution_id,
                    step_name=step.name,
                    step_index=index,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=_ms(started_at, completed_at),
                    output=output,
                )

                # Propagate output so subsequent steps can consume it
                accumulated[step.name] = output
                execution.outputs[step.name] = output

            except Exception as exc:
                failed_at = _now()

                yield StepFailed(
                    execution_id=execution.execution_id,
                    step_name=step.name,
                    step_index=index,
                    started_at=started_at,
                    failed_at=failed_at,
                    duration_ms=_ms(started_at, failed_at),
                    error=str(exc),
                )

                execution.fail(str(exc))
                return            # Halt on first failure

        execution.complete()      # IN_PROGRESS → COMPLETED
```

**Verify**: `python -c "from modules.workflows.runtime import WorkflowRuntime; print('ok')"` — prints `ok`.

---

### Step 5: Create `modules/workflows/__init__.py`

**Action**: Expose the public surface. Callers import from `modules.workflows`, not from its sub-modules.

**File**: `modules/workflows/__init__.py` (new)

**Pattern**:
```python
"""Workflow execution domain — Layer D of the workflow architecture.

Public surface:
    WorkflowExecution   — command object; owns the lifecycle state machine
    ExecutionStatus     — status enum (NEW → IN_PROGRESS → COMPLETED | ERROR | …)
    InvalidStatusTransition — raised on illegal transition
    WorkflowRuntime     — generator-based execution engine
    StepStarted         — domain event emitted when a step begins
    StepCompleted       — domain event emitted on step success
    StepFailed          — domain event emitted on step failure
    StepEvent           — union alias: StepStarted | StepCompleted | StepFailed
    StepProtocol        — structural protocol for step types (Tasks 1/2)
    WorkflowProtocol    — structural protocol for workflow aggregates (Task 2)
"""
from modules.workflows.events import StepCompleted, StepEvent, StepFailed, StepStarted
from modules.workflows.execution import (
    ExecutionStatus,
    InvalidStatusTransition,
    WorkflowExecution,
)
from modules.workflows.runtime import WorkflowRuntime
from modules.workflows.types import StepProtocol, WorkflowProtocol

__all__ = [
    "ExecutionStatus",
    "InvalidStatusTransition",
    "StepCompleted",
    "StepEvent",
    "StepFailed",
    "StepProtocol",
    "StepStarted",
    "WorkflowExecution",
    "WorkflowProtocol",
    "WorkflowRuntime",
]
```

**Verify**: `python -c "from modules.workflows import WorkflowRuntime, WorkflowExecution, StepStarted; print('ok')"` — prints `ok`.

---

### Step 6: Replace `task_gen/service.py` STATE dict with `WorkflowExecution`

**Action**: Delete `STATE`, `_initial_state`, and `_set_state`. Add `_EXECUTIONS: dict[str, WorkflowExecution]`. Rewrite `is_running`, `snapshot`, and `start`. Update `run_generation` signature to accept `execution: WorkflowExecution`; replace every `_set_state(...)` call with the corresponding `execution` mutation.

**File**: `modules/task_gen/service.py` (currently 291 lines)

The key replacements, cited by current line:

| Current code (line range) | Replacement |
|---|---|
| Lines 36–49: `STATE`, `_LOCK`, `_initial_state` | `_EXECUTIONS: dict[str, WorkflowExecution] = {}` + keep `_LOCK` |
| Lines 52–55: `is_running` reads `STATE` | `exc = _EXECUTIONS.get(project_id); return exc is not None and exc.is_running` |
| Lines 58–78: `snapshot` reads `STATE` | Build dict from `exc.is_running`, `exc.is_terminal`, `exc.outputs`, `exc.error` |
| Lines 81–85: `_set_state` helper | **Delete entirely** |
| Line 189: `run_generation(project_id, projects_dir)` | Add `execution: WorkflowExecution` third parameter |
| Lines 199, 206, 212: early `_set_state(…, error=…)` exits | `execution.fail("<message>"); return` |
| Line 219: `_set_state(…, allDone=True)` | `execution.outputs["allDone"] = True; execution.complete(); return` |
| Lines 257–263: success `_set_state` | `execution.outputs["filename"] = …; execution.outputs["taskNum"] = …; execution.outputs["taskName"] = …; execution.complete()` |
| Lines 265–267: `except` block | `execution.fail(str(exc))` (guarded: `if not execution.is_terminal`) |
| Lines 270–290: `start` function | Construct `WorkflowExecution`, call `exc.start()` inside lock, pass `exc` to thread |

**Pattern** (full replacement for the state-management and public functions):
```python
from modules.workflows.execution import ExecutionStatus, WorkflowExecution  # add at top

_EXECUTIONS: dict[str, WorkflowExecution] = {}
_LOCK = threading.Lock()


def is_running(project_id: str) -> bool:
    with _LOCK:
        exc = _EXECUTIONS.get(project_id)
        return exc is not None and exc.is_running


def snapshot(project_id: str) -> dict:
    with _LOCK:
        exc = _EXECUTIONS.get(project_id)
        if exc is None:
            return {"running": False, "done": False}
        out: dict = {
            "running": exc.is_running,
            "done": exc.is_terminal,
        }
        for key in ("filename", "taskNum", "taskName"):
            if (val := exc.outputs.get(key)) is not None:
                out[key] = val
        if exc.outputs.get("allDone"):          # only emit when truthy — matches old behaviour
            out["allDone"] = True
        if exc.error is not None:
            out["error"] = exc.error
        return out


def run_generation(project_id: str, projects_dir: Path, execution: WorkflowExecution) -> None:
    try:
        # Step 1 — early exit pattern (replaces _set_state + return):
        project = get_project(projects_dir, project_id)
        if project is None:
            execution.fail("project not found")
            return
        # ... steps 2–9 unchanged except _set_state calls removed ...
        # Step 10: write output file (unchanged)
        # Step 11: mark done (replaces final _set_state):
        execution.outputs["filename"] = filename
        execution.outputs["taskNum"] = task["num"]
        execution.outputs["taskName"] = task["name"]
        execution.complete()
    except Exception as exc:
        logger.exception("generate-task thread failed project_id=%s", project_id)
        if not execution.is_terminal:           # guard against double-transition
            execution.fail(str(exc))


def start(project_id: str, projects_dir: Path) -> bool:
    with _LOCK:
        existing = _EXECUTIONS.get(project_id)
        if existing and existing.is_running:
            return False
        exc = WorkflowExecution(
            workflow_ref=f"task_gen/{project_id}",
            inputs={"project_id": project_id, "projects_dir": str(projects_dir)},
        )
        exc.start()                              # NEW → IN_PROGRESS inside the lock
        _EXECUTIONS[project_id] = exc

    thread = threading.Thread(
        target=run_generation,
        args=(project_id, projects_dir, exc),
        name=f"generate-task[{project_id}]",
        daemon=True,
    )
    thread.start()
    return True
```

**Verify**: `python -m pytest modules/task_gen/tests/ -q` — expect the 7 existing task_gen test functions to all pass (they will fail before Step 7 because `reset_state` still references `_svc.STATE`; that is expected and resolved in Step 7).

---

### Step 7: Update `task_gen/tests/test_routes.py` STATE references

**Action**: Update three locations that directly reference the old `STATE` dict. The test contract (response shapes, status codes, polling behaviour) does not change — only the internal fixture setup changes.

**File**: `modules/task_gen/tests/test_routes.py`

**Change 1 — `reset_state` fixture (lines 79, 81)**:

```python
# Before:
_svc.STATE.clear()

# After:
_svc._EXECUTIONS.clear()
```

Apply to both the setup (line 79) and teardown (line 81).

**Change 2 — `post_generateTask_alreadyRunning_returns409AndAlreadyRunning` (lines 122–125)**:

```python
# Before:
_svc.STATE[project_id] = {
    "running": True, "done": False, "allDone": False,
    "filename": None, "taskNum": None, "taskName": None, "error": None,
}

# After:
from modules.workflows.execution import WorkflowExecution
exc = WorkflowExecution(workflow_ref=f"task_gen/{project_id}", inputs={})
exc.start()                          # NEW → IN_PROGRESS; is_running=True
_svc._EXECUTIONS[project_id] = exc
```

**Verify**: `python -m pytest modules/task_gen/tests/ -q` — all 7 existing task_gen test functions pass.

---

### Step 8: Add adapter-boundary structural test

**Action**: Append a third structural invariant to `tests/test_structural.py` that fails if any non-test file inside `modules/workflows/` imports `modules.chain.providers` directly. Matches the existing naming convention (`word_word`) and style (Path.rglob + assert with fix message).

**File**: `tests/test_structural.py` (currently 47 lines)

**Pattern** — append after `gunicorn_inProdRequirements`:
```python
def workflowsModule_doesNotImportChainProvidersDirectly():
    """modules/workflows must route AI calls only through modules.chain.adapter.

    Rule: ELA Adapter Pattern — feature code imports adapter, never providers.
    Fix:  Replace any 'from modules.chain.providers' import with
          'from modules.chain import adapter as chain_adapter'.
    """
    source_files = [
        p for p in (_REPO_ROOT / "modules" / "workflows").rglob("*.py")
        if "tests" not in p.parts
    ]
    violations = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "from modules.chain.providers" in line or \
               "import modules.chain.providers" in line:
                violations.append(
                    f"{path.relative_to(_REPO_ROOT)}:{lineno}: {line.strip()}"
                )
    assert not violations, (
        "modules/workflows must not import chain.providers directly.\n"
        "Use 'from modules.chain import adapter as chain_adapter' instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
```

**Verify**: `python -m pytest tests/test_structural.py -v` — three structural tests pass; `workflowsModule_doesNotImportChainProvidersDirectly` is green because `modules/workflows/runtime.py` imports from `modules.workflows.types`, not from providers.

---

## 5. Tests

Framework: `pytest`, collected via `python_functions = ["test_*", "*_*"]` (see `pyproject.toml`). Name tests in `category_description` style. All assertions are complete — no stubs.

### `modules/workflows/tests/conftest.py`

```python
from __future__ import annotations
from typing import Any

import pytest

from modules.workflows.execution import WorkflowExecution


class _MockStep:
    """Minimal StepProtocol-conformant stub."""

    def __init__(self, name: str, output: str = "mock-output"):
        self.name = name
        self._output = output

    def execute(self, inputs: dict[str, Any]) -> str:
        return self._output


class _FailingStep:
    """StepProtocol stub that always raises."""

    def __init__(self, name: str, message: str = "step-error"):
        self.name = name
        self._message = message

    def execute(self, inputs: dict[str, Any]) -> str:
        raise RuntimeError(self._message)


class _MockWorkflow:
    """Minimal WorkflowProtocol-conformant stub."""

    def __init__(self, name: str, steps):
        self.name = name
        self.steps = steps


@pytest.fixture
def mock_step():
    return _MockStep("alpha", "alpha-out")


@pytest.fixture
def two_step_workflow():
    return _MockWorkflow(
        name="two-step",
        steps=[
            _MockStep("step-one", "out-one"),
            _MockStep("step-two", "out-two"),
        ],
    )


@pytest.fixture
def fresh_execution():
    return WorkflowExecution(workflow_ref="test/wf", inputs={"x": "1"})
```

---

### `modules/workflows/tests/test_events.py`

```python
from __future__ import annotations
from datetime import datetime, timezone

import pytest

from modules.workflows.events import StepCompleted, StepEvent, StepFailed, StepStarted

_NOW = datetime.now(tz=timezone.utc)


def stepStarted_isFrozen():
    event = StepStarted(
        execution_id="eid", step_name="s", step_index=0, started_at=_NOW
    )
    with pytest.raises(Exception):
        event.execution_id = "mutated"  # type: ignore[misc]


def stepCompleted_isFrozen():
    event = StepCompleted(
        execution_id="eid", step_name="s", step_index=0,
        started_at=_NOW, completed_at=_NOW, duration_ms=10, output="x"
    )
    with pytest.raises(Exception):
        event.output = "mutated"  # type: ignore[misc]


def stepFailed_isFrozen():
    event = StepFailed(
        execution_id="eid", step_name="s", step_index=0,
        started_at=_NOW, failed_at=_NOW, duration_ms=5, error="boom"
    )
    with pytest.raises(Exception):
        event.error = "mutated"  # type: ignore[misc]


def stepStarted_hasRequiredFields():
    event = StepStarted(
        execution_id="abc", step_name="my-step", step_index=2, started_at=_NOW
    )
    assert event.execution_id == "abc"
    assert event.step_name == "my-step"
    assert event.step_index == 2
    assert event.started_at == _NOW


def stepCompleted_hasRequiredFields():
    event = StepCompleted(
        execution_id="abc", step_name="my-step", step_index=0,
        started_at=_NOW, completed_at=_NOW, duration_ms=42, output="result"
    )
    assert event.output == "result"
    assert event.duration_ms == 42


def stepFailed_hasRequiredFields():
    event = StepFailed(
        execution_id="abc", step_name="bad-step", step_index=1,
        started_at=_NOW, failed_at=_NOW, duration_ms=3, error="timeout"
    )
    assert event.error == "timeout"
    assert event.step_index == 1


def stepEvent_unionCoversAllTypes():
    # Union alias is purely a type hint — verify the three members are importable
    # and that each satisfies the same duck-type shape used by the runtime.
    for cls in (StepStarted, StepCompleted, StepFailed):
        assert hasattr(cls, "execution_id"), f"{cls.__name__} missing execution_id"
        assert hasattr(cls, "step_name"),    f"{cls.__name__} missing step_name"
        assert hasattr(cls, "step_index"),   f"{cls.__name__} missing step_index"
```

---

### `modules/workflows/tests/test_execution.py`

```python
from __future__ import annotations

import pytest

from modules.workflows.execution import (
    ExecutionStatus,
    InvalidStatusTransition,
    WorkflowExecution,
)


def _new_exec() -> WorkflowExecution:
    return WorkflowExecution(workflow_ref="test/wf", inputs={})


# ── Status transitions ──────────────────────────────────────────────────────

def newExecution_hasNewStatus():
    assert _new_exec().status is ExecutionStatus.NEW


def newToInProgress_succeeds():
    exc = _new_exec()
    exc.start()
    assert exc.status is ExecutionStatus.IN_PROGRESS


def inProgressToCompleted_succeeds():
    exc = _new_exec(); exc.start()
    exc.complete()
    assert exc.status is ExecutionStatus.COMPLETED


def inProgressToError_succeeds():
    exc = _new_exec(); exc.start()
    exc.fail("oops")
    assert exc.status is ExecutionStatus.ERROR
    assert exc.error == "oops"


def inProgressToTimeout_succeeds():
    exc = _new_exec(); exc.start()
    exc.timeout()
    assert exc.status is ExecutionStatus.TIMEOUT


def inProgressToCancelling_succeeds():
    exc = _new_exec(); exc.start()
    exc.request_cancel()
    assert exc.status is ExecutionStatus.CANCELLING


def cancellingToCancelled_succeeds():
    exc = _new_exec(); exc.start(); exc.request_cancel()
    exc.cancel()
    assert exc.status is ExecutionStatus.CANCELLED


# ── Invalid transitions ─────────────────────────────────────────────────────

def newToCompleted_raisesInvalidTransition():
    exc = _new_exec()
    with pytest.raises(InvalidStatusTransition, match="NEW"):
        exc.complete()


def completedToAny_raisesInvalidTransition():
    exc = _new_exec(); exc.start(); exc.complete()
    with pytest.raises(InvalidStatusTransition):
        exc.fail("late error")


def errorToAny_raisesInvalidTransition():
    exc = _new_exec(); exc.start(); exc.fail("err")
    with pytest.raises(InvalidStatusTransition):
        exc.complete()


# ── Predicates ──────────────────────────────────────────────────────────────

def isRunning_trueWhenInProgress():
    exc = _new_exec(); exc.start()
    assert exc.is_running is True


def isRunning_falseWhenNew():
    assert _new_exec().is_running is False


def isTerminal_trueForCompleted():
    exc = _new_exec(); exc.start(); exc.complete()
    assert exc.is_terminal is True


def isTerminal_trueForError():
    exc = _new_exec(); exc.start(); exc.fail("x")
    assert exc.is_terminal is True


def isTerminal_falseWhenInProgress():
    exc = _new_exec(); exc.start()
    assert exc.is_terminal is False


# ── Misc ─────────────────────────────────────────────────────────────────────

def fail_setsErrorField():
    exc = _new_exec(); exc.start()
    exc.fail("database gone")
    assert exc.error == "database gone"


def executionId_isUniquePerInstance():
    a, b = _new_exec(), _new_exec()
    assert a.execution_id != b.execution_id
```

---

### `modules/workflows/tests/test_runtime.py`

```python
from __future__ import annotations
from typing import Any

import pytest

from modules.workflows.execution import ExecutionStatus, InvalidStatusTransition, WorkflowExecution
from modules.workflows.events import StepCompleted, StepFailed, StepStarted
from modules.workflows.runtime import WorkflowRuntime


# ── Helpers ──────────────────────────────────────────────────────────────────

class _Step:
    def __init__(self, name: str, output: str = "ok"):
        self.name = name; self._out = output

    def execute(self, inputs: dict[str, Any]) -> str:
        return self._out


class _FailStep:
    def __init__(self, name: str, msg: str = "boom"):
        self.name = name; self._msg = msg

    def execute(self, inputs: dict[str, Any]) -> str:
        raise RuntimeError(self._msg)


class _Wf:
    def __init__(self, *steps):
        self.name = "test-wf"; self.steps = list(steps)


def _exec(ref: str = "test/wf") -> WorkflowExecution:
    return WorkflowExecution(workflow_ref=ref, inputs={"seed": "val"})


# ── Tests ─────────────────────────────────────────────────────────────────────

def emptyWorkflow_completesExecution():
    exc = _exec()
    events = list(WorkflowRuntime().run(exc, _Wf()))
    assert events == [], f"Expected no events, got {events}"
    assert exc.status is ExecutionStatus.COMPLETED


def singleStep_yieldsStartedThenCompleted():
    exc = _exec()
    events = list(WorkflowRuntime().run(exc, _Wf(_Step("s1", "hello"))))
    assert len(events) == 2, f"Expected 2 events, got {len(events)}: {events}"
    assert isinstance(events[0], StepStarted),   f"First event must be StepStarted, got {type(events[0])}"
    assert isinstance(events[1], StepCompleted), f"Second event must be StepCompleted, got {type(events[1])}"
    assert events[0].step_name == "s1"
    assert events[1].output == "hello"


def singleStep_outputAccumulatedInExecution():
    exc = _exec()
    list(WorkflowRuntime().run(exc, _Wf(_Step("alpha", "result-text"))))
    assert exc.outputs["alpha"] == "result-text", "Step output must be stored in execution.outputs"


def twoSteps_secondStepReceivesPriorOutput():
    captured: list[dict] = []

    class _CapturingStep:
        name = "capture"
        def execute(self, inputs: dict[str, Any]) -> str:
            captured.append(dict(inputs))
            return "captured"

    exc = _exec()
    list(WorkflowRuntime().run(exc, _Wf(_Step("first", "first-out"), _CapturingStep())))
    assert len(captured) == 1, "Capturing step must have been called once"
    assert captured[0]["first"] == "first-out", (
        "Second step must see first step's output in inputs; "
        f"got keys {list(captured[0].keys())}"
    )


def failingStep_yieldsFailed():
    exc = _exec()
    events = list(WorkflowRuntime().run(exc, _Wf(_FailStep("bad", "step-error"))))
    assert len(events) == 2, f"Expected StepStarted + StepFailed, got {len(events)}"
    assert isinstance(events[1], StepFailed), f"Second event must be StepFailed, got {type(events[1])}"
    assert events[1].error == "step-error"


def failingStep_haltsExecution():
    """A failing step must not cause subsequent steps to execute."""
    executed = []

    class _TrackStep:
        name = "track"
        def execute(self, inputs: dict[str, Any]) -> str:
            executed.append(True); return "ok"

    exc = _exec()
    list(WorkflowRuntime().run(exc, _Wf(_FailStep("fail-first"), _TrackStep())))
    assert executed == [], f"Step after failure must not execute; got {executed}"


def failingStep_setsExecutionErrorStatus():
    exc = _exec()
    list(WorkflowRuntime().run(exc, _Wf(_FailStep("bad"))))
    assert exc.status is ExecutionStatus.ERROR, f"Expected ERROR, got {exc.status}"
    assert exc.error is not None, "execution.error must be set after step failure"


def runAfterStarted_raisesInvalidTransition():
    """Passing an already-IN_PROGRESS execution must raise immediately."""
    exc = _exec(); exc.start()
    with pytest.raises(InvalidStatusTransition):
        list(WorkflowRuntime().run(exc, _Wf()))


def completedExecution_hasAllOutputs():
    exc = _exec()
    list(WorkflowRuntime().run(exc, _Wf(_Step("p1", "v1"), _Step("p2", "v2"))))
    assert exc.outputs == {"p1": "v1", "p2": "v2"}, (
        f"Expected both step outputs in execution.outputs; got {exc.outputs}"
    )
```

---

### `modules/workflows/tests/__init__.py`

Empty file — package marker only.

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after completing **each step** before moving to the next. Do not batch.

1. `feat(workflows): add step and workflow protocol types` — after Step 1 — `modules/workflows/types.py`: StepProtocol, WorkflowProtocol
2. `feat(workflows): add step domain event types` — after Step 2 — `modules/workflows/events.py`: StepStarted, StepCompleted, StepFailed, StepEvent
3. `feat(workflows): add execution status state machine` — after Step 3 — `modules/workflows/execution.py`: ExecutionStatus, InvalidStatusTransition, WorkflowExecution
4. `feat(workflows): add workflow runtime generator` — after Step 4 — `modules/workflows/runtime.py`: WorkflowRuntime
5. `feat(workflows): expose public module interface` — after Step 5 — `modules/workflows/__init__.py`
6. `refactor(task_gen): replace STATE dict with WorkflowExecution` — after Step 6 — `modules/task_gen/service.py`: delete STATE/\_initial\_state/\_set\_state, add \_EXECUTIONS, update is\_running/snapshot/start/run\_generation
7. `fix(task_gen/tests): update STATE references to _EXECUTIONS` — after Step 7 — `modules/task_gen/tests/test_routes.py`: reset\_state fixture + alreadyRunning pre-seed
8. `test(structural): enforce adapter boundary for workflows module` — after Step 8 — `tests/test_structural.py`: workflowsModule\_doesNotImportChainProvidersDirectly
9. `test(workflows): add event, execution, runtime unit tests` — after tests pass — `modules/workflows/tests/`: conftest.py + test\_events.py + test\_execution.py + test\_runtime.py + \_\_init\_\_.py

**Deviation logging**: if a step requires a deviation from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api
python -m pytest -v
```

**Expected delta**: 192 → 225 passing (33 new tests across test\_events: 7, test\_execution: 16, test\_runtime: 9, test\_structural: 1). Zero pre-existing tests broken.

Spot-check the three key groups explicitly:
```bash
# New workflow tests
python -m pytest modules/workflows/tests/ -v

# task_gen integration tests must be green (all 7 functions)
python -m pytest modules/task_gen/tests/ -v

# Structural invariants (all 3 functions)
python -m pytest tests/test_structural.py -v
```

---

## 8. Rollback

- **Per-step rollback**: each commit above is independently revertible.
  ```bash
  git revert <sha>   # creates a new revert commit; safe on a branch
  ```
- **Full-task rollback**: if verification fails catastrophically after multiple commits:
  ```bash
  git log --oneline -10          # find the sha before Step 1
  git reset --hard <pre-task-sha>  # [REQUIRES APPROVAL] — discards all task commits
  ```
  Or delete the feature branch: `git checkout main && git branch -D <feature-branch>` [REQUIRES APPROVAL].

---

## 9. Deviations Allowed

- **`modules/workflows/` partially exists** (Tasks 1/2 partially shipped) → read what's there before creating files; if `types.py` already exists with conflicting definitions, reconcile rather than overwrite, and log the deviation in commit 1.
- **`AbstractStep.execute` has a different signature** (e.g., `execute(inputs, context)`) → update `StepProtocol` to match and thread `context` through `WorkflowRuntime.run`; log the deviation in commit 4.
- **`_svc.STATE` referenced in test files not listed here** → grep `modules/ tests/` for `service.STATE` before Step 7; update every occurrence; log each file in commit 7.
  ```bash
  grep -rn "service\.STATE\|_svc\.STATE" modules/ tests/
  ```
- **Test framework mismatch** (e.g., `pytest-asyncio` required) → translate silently; note in commit body.
- **Step N simplification unlocks Step N+1** → take it; log the deviation.
- **Side-effect required** (push, publish, schema migration, database drop) → STOP, mark **[REQUIRES APPROVAL]**, and surface to the reviewer.

---

## 10. Out of Scope

This task delivers the execution engine (Layer D) and replaces `task_gen`'s status dict. It does not touch the HTTP surface, observer subscriptions, the provider boundary, or the persistence layer. An eager executor encountering any of the items below should flag them as out-of-scope rather than absorbing them.

- **Route migration of `modules/ai/routes.py`** (the "spec_gen" migration) — Task 5; requires WorkflowRepository (Layer E) and the Workflow aggregate (Tasks 1/2) to be fully proven before the multi-step `bootstrap_project` orchestration is replaced.
- **Full removal of `modules/task_gen/`** — Task 5; task_gen's HTTP routes remain the only entry point until the Angular client is updated to use the new SSE endpoint; deleting the module here breaks existing callers.
- **SSE / HTTP streaming wrapper around `WorkflowRuntime.run`** — Task 5; the generator is already drainable directly; the HTTP layer is a thin wrap that belongs in the route migration step.
- **Observer subscriber implementations** (cost tracker, audit logger, GUI SSE pusher) — Phase 2; the events are emitted; new listeners subscribe without touching the runtime; scheduling them before named consumers exist is speculative.
- **Async execution** — Phase 2, paired with the `Parallel` step kind; deferred until a concrete intra-workflow latency SLA is named.
- **`WorkflowRepository` and `WorkflowRepositoryFs`** — Layer E; a separate task; the runtime currently receives a `WorkflowProtocol`-conformant object from the caller; how that object is loaded is out of scope here.
- **`chain.adapter` signature widening** (`invoke(Invocation)`)  — the Architecture describes widening `generate(system, prompt)` to `invoke(invocation)` for typed invocation shapes; this is a separate cleanup with its own blast radius and must not be absorbed here.
- **`WorkflowExecution` persistence / restart after process death** — the `_EXECUTIONS` dict is still in-process; `WorkflowRepositoryDb` (Phase 2+) is the named trigger for persistence; adding it here is premature.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a proposed deviation rather than expanding this task's scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Layer D design rationale, state machine diagram, event lifecycle
- [Epic](./epic.md) — Task scope, phase boundaries, success criteria
- [Timeline](./timeline.md) — Update status to "in progress" when branch is cut; "done" after verification passes