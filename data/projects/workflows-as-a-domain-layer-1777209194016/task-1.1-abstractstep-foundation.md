# Task 1.1: AbstractStep Foundation

---

## 1. Context

**Repo**: `{WORKSPACE}/spec-doc/api` — Flask backend, port 3101, `make test` runs 192 pytest tests.

**What this task delivers**: The structural contract every concrete step kind in Tasks 1.2+ depends on. Three things land:
- `StepContext` — the mutable execution bag (`run_id`, `inputs`, `outputs`) threaded through every step.
- `StepStarted`, `StepCompleted`, `StepFailed` — frozen Pydantic v2 domain events. These are the Observer contract between the runtime (Task 3) and listeners (cost tracker, SSE pusher). Frozen so they can be safely cached and serialised.
- `AbstractStep` — a **frozen Pydantic v2 BaseModel + ABC** that seals the event lifecycle. `name: str` is a Pydantic field (subclasses pass it as a constructor kwarg, not as a property override). Subclasses implement `_invoke(self, context: StepContext)`; the `execute(self, context: StepContext)` generator is sealed: validate → emit `StepStarted` → invoke → emit `StepCompleted | StepFailed` → re-raise on failure. No concrete step can break this contract.

**No concrete step implementations** (`AICall`, `Compute`) in this task. Those are Task 1.2.

**Test framework**: pytest, `pyproject.toml` `python_functions = ["test_*", "*_*"]` — functions named `lowerCamelCase_description` are auto-collected. Any function name containing an underscore is collected; helper names must have no underscore to avoid accidental collection.

---

## 2. Pre-flight

```bash
cd {WORKSPACE}/spec-doc/api
make test 2>&1 | tail -3            # record baseline N (must be green before you start)
python -c "import pydantic; print(pydantic.__version__)"  # expect 2.x
python -c "from modules.chain.adapter import generate; print('adapter ok')"
ls modules/workflows 2>/dev/null && echo "EXISTS — stop" || echo "absent — proceed"
```

**Baseline recorded:** record the actual `make test` pass count as **N**. This task adds **+24 tests** with zero pre-existing failures — verification is `N → N+24`. Do not rely on the absolute number 192; sibling tasks may have shifted the baseline.

All four commands must succeed and the last must print `absent — proceed`. If `modules/workflows` already exists, do **not** proceed until the directory state is understood.

---

## 3. Files

| Path | Status | Purpose |
|------|--------|---------|
| `modules/workflows/__init__.py` | **(new)** | Package root; re-exports public surface |
| `modules/workflows/steps/__init__.py` | **(new)** | Steps sub-package exports |
| `modules/workflows/steps/events.py` | **(new)** | `StepStarted`, `StepCompleted`, `StepFailed`, `StepEvent` |
| `modules/workflows/steps/base.py` | **(new)** | `StepContext`, `AbstractStep` |
| `modules/workflows/tests/__init__.py` | **(new)** | Empty; makes directory a pytest package |
| `modules/workflows/tests/test_abstract_step.py` | **(new)** | 23 tests covering all branches |
| `tests/test_structural.py` | **modify** | Add one structural invariant: `execute` is concrete |

---

## 4. Implementation Steps

### Step 1 — Create the directory skeleton

```bash
mkdir -p modules/workflows/steps
mkdir -p modules/workflows/tests
touch modules/workflows/tests/__init__.py
```

Verify:
```bash
ls modules/workflows/steps modules/workflows/tests
# steps output: (empty — files come next)
# tests output: __init__.py
```

---

### Step 2 — Write `modules/workflows/steps/events.py`

Create the file with this exact content:

```python
"""StepEvent domain types — Observer contract for AbstractStep lifecycle.

Every AbstractStep.execute() call yields exactly two events:
  success path  → StepStarted, StepCompleted
  failure path  → StepStarted, StepFailed

All three are frozen Pydantic v2 models: safe to cache, compare by value,
and serialise directly to SSE payloads without a separate DTO layer.
"""
from __future__ import annotations

from typing import Any, Union

from pydantic import BaseModel, ConfigDict


class StepStarted(BaseModel):
    """Emitted after input validation passes, before _invoke is called."""

    model_config = ConfigDict(frozen=True)

    step_name: str
    run_id: str
    started_at: float  # time.monotonic() snapshot at execution entry


class StepCompleted(BaseModel):
    """Emitted after _invoke returns successfully."""

    model_config = ConfigDict(frozen=True)

    step_name: str
    run_id: str
    started_at: float
    completed_at: float
    latency_ms: int
    output: Any


class StepFailed(BaseModel):
    """Emitted after _invoke raises; the exception is re-raised after emission."""

    model_config = ConfigDict(frozen=True)

    step_name: str
    run_id: str
    started_at: float
    failed_at: float
    latency_ms: int
    error: str


#: Union alias consumed by AbstractStep.execute() return annotation and the runtime.
StepEvent = Union[StepStarted, StepCompleted, StepFailed]
```

---

### Step 3 — Write `modules/workflows/steps/base.py`

```python
"""AbstractStep — Template Method foundation for all workflow step kinds.

AbstractStep is a frozen Pydantic v2 BaseModel + ABC. Concrete step kinds
(AICall, Compute — Task 1.2) inherit from it and add their own fields; they
remain frozen value objects with equality-by-value semantics.

Execute lifecycle (sealed — subclasses must NOT override `execute`):
  1. _validate_inputs → raises ValueError on missing keys; no events emitted
  2. StepStarted      → yielded
  3. _invoke          → subclass-defined; result stored in context.outputs[name]
  4a. StepCompleted   → yielded (success)
  4b. StepFailed      → yielded then original exception re-raised (failure)
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict

from .events import StepCompleted, StepEvent, StepFailed, StepStarted


@dataclass
class StepContext:
    """Shared execution bag threaded through every step in a workflow run.

    Attributes:
        run_id:  Stable identifier for the enclosing WorkflowExecution.
        inputs:  Caller-supplied data; treat as read-only inside _invoke.
        outputs: Accumulated step results; written by AbstractStep.execute(),
                 keyed by step name.  Read by later steps to chain results.
    """

    run_id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] = field(default_factory=dict)


class AbstractStep(BaseModel, ABC):
    """Template Method base for all step kinds.

    Frozen Pydantic v2 BaseModel — subclass instances are immutable and compare
    equal by field values. ``name`` is a Pydantic field; subclasses pass it as
    a constructor kwarg (no property override required).

    Subclasses MUST implement:
        _invoke       — the step's work; return value becomes the step output

    Subclasses MAY override:
        required_inputs — frozenset of input keys that must exist in context.inputs
    """

    model_config = ConfigDict(frozen=True)

    name: str

    @property
    def required_inputs(self) -> frozenset[str]:
        """Input keys required before _invoke is called.

        Default: empty (no validation).  Override to declare dependencies.
        Validation failure raises ValueError *before* any event is emitted.
        """
        return frozenset()

    def _validate_inputs(self, context: StepContext) -> None:
        """Raise ValueError if any key in required_inputs is absent from context.inputs."""
        missing = self.required_inputs - context.inputs.keys()
        if missing:
            raise ValueError(
                f"Step '{self.name}' missing required inputs: {sorted(missing)}"
            )

    @abstractmethod
    def _invoke(self, context: StepContext) -> Any:
        """Perform the step's work and return the output.

        - Read from context.inputs and context.outputs (prior step results).
        - Do NOT write to context.outputs — execute() does that after invoke returns.
        - Raise any exception to trigger the StepFailed branch.
        """

    def execute(self, context: StepContext) -> Iterator[StepEvent]:
        """Sealed Template Method — emits lifecycle events around _invoke.

        Yields:
            StepStarted   — always (after validation succeeds)
            StepCompleted — on success; context.outputs[self.name] is set before yield
            StepFailed    — on failure; the original exception is re-raised after yield

        Raises:
            ValueError  — if required_inputs are missing (no events emitted)
            Exception   — re-raised from _invoke after StepFailed has been yielded
        """
        self._validate_inputs(context)

        started_at = time.monotonic()
        yield StepStarted(
            step_name=self.name,
            run_id=context.run_id,
            started_at=started_at,
        )

        try:
            output = self._invoke(context)
            completed_at = time.monotonic()
            context.outputs[self.name] = output
            yield StepCompleted(
                step_name=self.name,
                run_id=context.run_id,
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=int((completed_at - started_at) * 1000),
                output=output,
            )
        except Exception as exc:
            failed_at = time.monotonic()
            yield StepFailed(
                step_name=self.name,
                run_id=context.run_id,
                started_at=started_at,
                failed_at=failed_at,
                latency_ms=int((failed_at - started_at) * 1000),
                error=str(exc),
            )
            raise
```

---

### Step 4 — Write `modules/workflows/steps/__init__.py`

```python
"""Public surface of the steps sub-package."""
from .base import AbstractStep, StepContext
from .events import StepCompleted, StepEvent, StepFailed, StepStarted

__all__ = [
    "AbstractStep",
    "StepContext",
    "StepStarted",
    "StepCompleted",
    "StepFailed",
    "StepEvent",
]
```

---

### Step 5 — Write `modules/workflows/__init__.py`

```python
"""workflows — domain layer for multi-step AI pipelines (Phase 1).

Public surface after Task 1.1:
    AbstractStep, StepContext, StepStarted, StepCompleted, StepFailed, StepEvent
"""
from .steps import (
    AbstractStep,
    StepCompleted,
    StepContext,
    StepEvent,
    StepFailed,
    StepStarted,
)

__all__ = [
    "AbstractStep",
    "StepContext",
    "StepStarted",
    "StepCompleted",
    "StepFailed",
    "StepEvent",
]
```

---

### Step 6 — Write `modules/workflows/tests/test_abstract_step.py`

> **Naming note**: helper names must have no underscore to avoid pytest collection under `*_*`. All three test-helper functions below (`ctx`, `collect`, `collectfailing`) contain no underscore and are not collected. Test classes (`EchoStep` etc.) don't start with `Test` so they're not collected as test classes.

```python
"""Tests for AbstractStep Template Method, StepContext, and StepEvent types.

Concrete helper steps defined here are minimal stubs — no provider, no filesystem.
Every test drains the execute() generator directly.
"""
from __future__ import annotations

from typing import Any

import pytest

from modules.workflows.steps import (
    AbstractStep,
    StepCompleted,
    StepContext,
    StepFailed,
    StepStarted,
)


# ---------------------------------------------------------------------------
# Concrete test implementations (not test classes — no "Test" prefix)
# ---------------------------------------------------------------------------

class EchoStep(AbstractStep):
    """Returns context.inputs['value'] or 'ok' if absent."""

    def _invoke(self, context: StepContext) -> Any:
        return context.inputs.get("value", "ok")


class BombStep(AbstractStep):
    """Always raises RuntimeError — exercises the failure path."""

    def _invoke(self, context: StepContext) -> Any:
        raise RuntimeError("deliberate failure")


class GuardedStep(AbstractStep):
    """Declares 'text' and 'count' as required inputs."""

    @property
    def required_inputs(self) -> frozenset[str]:
        return frozenset({"text", "count"})

    def _invoke(self, context: StepContext) -> Any:
        return context.inputs["text"]


# ---------------------------------------------------------------------------
# Helper callables (no underscores — not collected by pytest *_* pattern)
# ---------------------------------------------------------------------------

def ctx(**kwargs: Any) -> StepContext:
    return StepContext(run_id="run-001", inputs=kwargs)


def collect(step: AbstractStep, context: StepContext) -> list:
    """Drain execute() to a list; raises on step failure."""
    return list(step.execute(context))


def collectfailing(step: AbstractStep, context: StepContext) -> tuple[list, Exception]:
    """Drain execute() for a failing step; return (events, exception)."""
    events: list = []
    caught: Exception | None = None
    try:
        for ev in step.execute(context):
            events.append(ev)
    except Exception as exc:
        caught = exc
    assert caught is not None, "expected step to raise but it did not"
    return events, caught


# ---------------------------------------------------------------------------
# 1. Happy path — event sequence and types
# ---------------------------------------------------------------------------

def successfulStep_yieldsExactlyTwoEvents():
    events = collect(EchoStep(name="echo"), ctx(value="hello"))
    assert len(events) == 2, f"expected 2 events, got {len(events)}: {events}"


def successfulStep_firstEventIsStepStarted():
    events = collect(EchoStep(name="echo"), ctx(value="hello"))
    assert isinstance(events[0], StepStarted), (
        f"expected StepStarted at index 0, got {type(events[0])}"
    )


def successfulStep_secondEventIsStepCompleted():
    events = collect(EchoStep(name="echo"), ctx(value="hello"))
    assert isinstance(events[1], StepCompleted), (
        f"expected StepCompleted at index 1, got {type(events[1])}"
    )


# ---------------------------------------------------------------------------
# 2. Happy path — StepStarted field values
# ---------------------------------------------------------------------------

def stepStarted_carriesStepNameAndRunId():
    events = collect(EchoStep(name="echo"), ctx(value="x"))
    started: StepStarted = events[0]  # type: ignore[assignment]
    assert started.step_name == "echo"
    assert started.run_id == "run-001"


def stepStarted_startedAt_isNonNegativeFloat():
    events = collect(EchoStep(name="echo"), ctx())
    started: StepStarted = events[0]  # type: ignore[assignment]
    assert isinstance(started.started_at, float)
    assert started.started_at >= 0.0


# ---------------------------------------------------------------------------
# 3. Happy path — StepCompleted field values
# ---------------------------------------------------------------------------

def stepCompleted_outputMatchesInvokeReturnValue():
    events = collect(EchoStep(name="echo"), ctx(value="payload"))
    completed: StepCompleted = events[1]  # type: ignore[assignment]
    assert completed.output == "payload"


def stepCompleted_latencyMs_isNonNegativeInt():
    events = collect(EchoStep(name="echo"), ctx())
    completed: StepCompleted = events[1]  # type: ignore[assignment]
    assert isinstance(completed.latency_ms, int)
    assert completed.latency_ms >= 0


def stepCompleted_completedAt_isAfterOrEqualStartedAt():
    events = collect(EchoStep(name="echo"), ctx())
    completed: StepCompleted = events[1]  # type: ignore[assignment]
    assert completed.completed_at >= completed.started_at


def stepCompleted_populatesContextOutputsUnderStepName():
    context = ctx(value="stored")
    collect(EchoStep(), context)
    assert "echo" in context.outputs
    assert context.outputs["echo"] == "stored"


# ---------------------------------------------------------------------------
# 4. Failure path — event sequence and types
# ---------------------------------------------------------------------------

def failingStep_yieldsExactlyTwoEventsBeforeRaise():
    events, _ = collectfailing(BombStep(name="bomb"), ctx())
    assert len(events) == 2, f"expected 2 events before raise, got {len(events)}: {events}"


def failingStep_firstEventIsStepStarted():
    events, _ = collectfailing(BombStep(name="bomb"), ctx())
    assert isinstance(events[0], StepStarted), (
        f"expected StepStarted at index 0, got {type(events[0])}"
    )


def failingStep_secondEventIsStepFailed():
    events, _ = collectfailing(BombStep(name="bomb"), ctx())
    assert isinstance(events[1], StepFailed), (
        f"expected StepFailed at index 1, got {type(events[1])}"
    )


def failingStep_reraisesOriginalException():
    _, exc = collectfailing(BombStep(name="bomb"), ctx())
    assert isinstance(exc, RuntimeError)
    assert "deliberate failure" in str(exc)


def failingStep_stepFailed_errorContainsExceptionMessage():
    events, _ = collectfailing(BombStep(name="bomb"), ctx())
    failed: StepFailed = events[1]  # type: ignore[assignment]
    assert "deliberate failure" in failed.error


def failingStep_stepFailed_latencyMs_isNonNegativeInt():
    events, _ = collectfailing(BombStep(name="bomb"), ctx())
    failed: StepFailed = events[1]  # type: ignore[assignment]
    assert isinstance(failed.latency_ms, int)
    assert failed.latency_ms >= 0


# ---------------------------------------------------------------------------
# 5. Input validation — ValueError before any event
# ---------------------------------------------------------------------------

def missingAllRequiredInputs_raisesValueErrorBeforeAnyEvent():
    step = GuardedStep(name="guarded")
    events: list = []
    with pytest.raises(ValueError, match="guarded"):
        for ev in step.execute(ctx()):  # neither 'text' nor 'count' supplied
            events.append(ev)
    assert events == [], (
        f"no events should be emitted before a validation error, got: {events}"
    )


def missingOneRequiredInput_raisesValueErrorNamingMissingKey():
    with pytest.raises(ValueError, match="count"):
        list(GuardedStep(name="guarded").execute(ctx(text="hello")))  # 'count' absent


def allRequiredInputsPresent_doesNotRaiseAndYieldsTwoEvents():
    events = collect(GuardedStep(name="guarded"), ctx(text="hello", count=3))
    assert len(events) == 2


# ---------------------------------------------------------------------------
# 6. Immutability of event models
# ---------------------------------------------------------------------------

def stepStarted_isFrozen():
    event = StepStarted(step_name="s", run_id="r", started_at=0.0)
    with pytest.raises(Exception):
        event.step_name = "mutated"  # type: ignore[misc]


def stepCompleted_isFrozen():
    event = StepCompleted(
        step_name="s", run_id="r",
        started_at=0.0, completed_at=0.1, latency_ms=100, output=None,
    )
    with pytest.raises(Exception):
        event.step_name = "mutated"  # type: ignore[misc]


def stepFailed_isFrozen():
    event = StepFailed(
        step_name="s", run_id="r",
        started_at=0.0, failed_at=0.1, latency_ms=100, error="boom",
    )
    with pytest.raises(Exception):
        event.step_name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 7. StepContext defaults
# ---------------------------------------------------------------------------

def stepContext_outputsDefaultToEmptyDict():
    context = StepContext(run_id="x", inputs={})
    assert context.outputs == {}


def stepContext_outputsAreMutable():
    context = StepContext(run_id="x", inputs={})
    context.outputs["result"] = "value"
    assert context.outputs["result"] == "value"
```

---

### Step 7 — Add structural invariant to `tests/test_structural.py`

Open `tests/test_structural.py` and append this function after the existing `gunicorn_inProdRequirements` function:

```python
def abstractStep_execute_isConcreteTemplateMethod():
    """AbstractStep.execute must be a concrete method, not abstract.

    Rule: the sealed event lifecycle (StepStarted / StepCompleted / StepFailed)
          is only guaranteed when execute() is the Template Method and subclasses
          override only _invoke.  If execute() were abstract, any subclass could
          omit event emission.
    Fix:  Do not mark execute() with @abstractmethod in AbstractStep.
    """
    from modules.workflows.steps import AbstractStep

    is_abstract = getattr(AbstractStep.execute, "__isabstractmethod__", False)
    assert not is_abstract, (
        "AbstractStep.execute must be concrete (the Template Method). "
        "Subclasses implement _invoke, not execute. "
        "Remove @abstractmethod from execute() in modules/workflows/steps/base.py."
    )
```

---

## 5. Tests

**Run target** (from `{WORKSPACE}/spec-doc/api`):

```bash
CHAIN_PROVIDER=mock python -m pytest modules/workflows/ tests/test_structural.py -v
```

**Expected output** — 24 tests collected and passing:

| Test | Assertion |
|------|-----------|
| `successfulStep_yieldsExactlyTwoEvents` | `len(events) == 2` |
| `successfulStep_firstEventIsStepStarted` | `isinstance(events[0], StepStarted)` |
| `successfulStep_secondEventIsStepCompleted` | `isinstance(events[1], StepCompleted)` |
| `stepStarted_carriesStepNameAndRunId` | `started.step_name == "echo"`, `started.run_id == "run-001"` |
| `stepStarted_startedAt_isNonNegativeFloat` | `isinstance(…, float) and … >= 0.0` |
| `stepCompleted_outputMatchesInvokeReturnValue` | `completed.output == "payload"` |
| `stepCompleted_latencyMs_isNonNegativeInt` | `isinstance(…, int) and … >= 0` |
| `stepCompleted_completedAt_isAfterOrEqualStartedAt` | `completed_at >= started_at` |
| `stepCompleted_populatesContextOutputsUnderStepName` | `context.outputs["echo"] == "stored"` |
| `failingStep_yieldsExactlyTwoEventsBeforeRaise` | `len(events) == 2` |
| `failingStep_firstEventIsStepStarted` | `isinstance(events[0], StepStarted)` |
| `failingStep_secondEventIsStepFailed` | `isinstance(events[1], StepFailed)` |
| `failingStep_reraisesOriginalException` | `isinstance(exc, RuntimeError)`, message matches |
| `failingStep_stepFailed_errorContainsExceptionMessage` | `"deliberate failure" in failed.error` |
| `failingStep_stepFailed_latencyMs_isNonNegativeInt` | `isinstance(…, int) and … >= 0` |
| `missingAllRequiredInputs_raisesValueErrorBeforeAnyEvent` | `pytest.raises(ValueError)`, `events == []` |
| `missingOneRequiredInput_raisesValueErrorNamingMissingKey` | `pytest.raises(ValueError, match="count")` |
| `allRequiredInputsPresent_doesNotRaiseAndYieldsTwoEvents` | `len(events) == 2` |
| `stepStarted_isFrozen` | `pytest.raises(Exception)` on attribute set |
| `stepCompleted_isFrozen` | `pytest.raises(Exception)` on attribute set |
| `stepFailed_isFrozen` | `pytest.raises(Exception)` on attribute set |
| `stepContext_outputsDefaultToEmptyDict` | `context.outputs == {}` |
| `stepContext_outputsAreMutable` | `context.outputs["result"] == "value"` |
| `abstractStep_execute_isConcreteTemplateMethod` | `not is_abstract` |

**Full-suite regression** — run after confirming new tests pass:

```bash
CHAIN_PROVIDER=mock python -m pytest -v
```

**Expected delta**: **+24 new tests passing, zero pre-existing failures vs the baseline N captured in §2 Pre-flight.** Do not rely on absolute counts — sibling tasks may have shifted the baseline.

---

## 6. Commit Plan

Single commit (all files are one logical unit — the step foundation contract):

```
feat(workflows): add AbstractStep foundation — StepContext, StepEvent types, Template Method

Introduces modules/workflows with the sealed event-lifecycle base for all step kinds.
AbstractStep.execute() is the Template Method that guarantees StepStarted/StepCompleted/
StepFailed emission without relying on subclass discipline.  No concrete step
implementations; those land in Task 1.2.

Files added:
  modules/workflows/__init__.py
  modules/workflows/steps/__init__.py
  modules/workflows/steps/events.py
  modules/workflows/steps/base.py
  modules/workflows/tests/__init__.py
  modules/workflows/tests/test_abstract_step.py

Files modified:
  tests/test_structural.py  — add abstractStep_execute_isConcreteTemplateMethod
```

Stage exactly these files:

```bash
git add modules/workflows/ tests/test_structural.py
git status  # verify: only the 7 paths above are staged
git commit -m "$(cat <<'EOF'
feat(workflows): add AbstractStep foundation — StepContext, StepEvent types, Template Method

Introduces modules/workflows with the sealed event-lifecycle base for all step kinds.
AbstractStep.execute() is the Template Method that guarantees StepStarted/StepCompleted/
StepFailed emission without relying on subclass discipline. No concrete step
implementations; those land in Task 1.2.

EOF
)"
```

---

## 7. Verification

**Checklist — tick each before marking task done:**

```bash
# 1. New tests pass in isolation
CHAIN_PROVIDER=mock python -m pytest modules/workflows/ -v
# Expected: 23 passed

# 2. Structural invariant passes
CHAIN_PROVIDER=mock python -m pytest tests/test_structural.py -v
# Expected: 3 passed (2 existing + 1 new)

# 3. Full suite green (no regressions)
CHAIN_PROVIDER=mock python -m pytest -v
# Expected: 216 passed, 0 failed, 0 errors

# 4. Public surface importable from top-level package
python -c "
from modules.workflows import (
    AbstractStep, StepContext,
    StepStarted, StepCompleted, StepFailed, StepEvent
)
print('imports ok')
"
# Expected: imports ok

# 5. AbstractStep cannot be instantiated directly (abstract method is unimplemented)
python -c "
from modules.workflows import AbstractStep
try:
    AbstractStep(name='x')
    print('FAIL — should have raised TypeError for abstract _invoke')
except TypeError as e:
    assert '_invoke' in str(e) or 'abstract' in str(e).lower(), str(e)
    print('ok — abstract class cannot be instantiated')
"
# Expected: ok — abstract class cannot be instantiated

# 6. StepEvent union type is correct
python -c "
from modules.workflows import StepStarted, StepEvent
import typing
args = typing.get_args(StepEvent)
assert len(args) == 3, args
print('StepEvent union ok:', [a.__name__ for a in args])
"
# Expected: StepEvent union ok: ['StepStarted', 'StepCompleted', 'StepFailed']
```

---

## 8. Rollback

If any verification step fails:

```bash
# Remove all new files
rm -rf modules/workflows/

# Restore test_structural.py to pre-task state
git restore tests/test_structural.py

# Confirm suite returns to baseline
CHAIN_PROVIDER=mock python -m pytest -v
# Expected: 192 passed (original count)
```

If you have already committed: `git revert HEAD --no-edit` then re-run the verification baseline.

---

## 9. Deviations Allowed

| Deviation | Condition |
|-----------|-----------|
| Use `dataclasses.dataclass(frozen=True)` instead of Pydantic `BaseModel` for event types | Only if a downstream task (1.3 runtime, 1.4 SSE layer) explicitly cannot accept Pydantic models. SSE serialisation uses `model.model_dump()` — frozen dataclasses would require a manual `asdict` call. Default to Pydantic. |
| Add `model_config = ConfigDict(arbitrary_types_allowed=True)` to event models | Only if `StepCompleted.output: Any` causes a Pydantic v2 validation error in practice. Should not be needed — `Any` disables field validation. |
| Move `StepContext` to its own file (`steps/context.py`) | Acceptable if `base.py` line count exceeds 120. Keep `StepContext` importable from `modules.workflows.steps` regardless of file location. |
| Rename `required_inputs` → `declared_inputs` | Only with explicit sign-off from Task 1.2 implementor — this property is the input-validation contract those concrete steps depend on. |

---

## 10. Out of Scope

| Item | Reason |
|------|--------|
| `AICall`, `Compute` concrete step kinds | Task 1.2; depends on this task's `AbstractStep` |
| `WorkflowRuntime` generator that drives steps | Task 3; depends on both Task 1.1, 1.2 and Task 2 |
| `WorkflowExecution` Command and State machine | Task 3 |
| `Workflow` aggregate and Builder | Task 2 |
| `WorkflowRepositoryFs` | Task 4 |
| `spec_gen` route handler migration | Task 5 (end-to-end validation) |
| `task_gen` removal | Task 3 absorbs the threading model; Task 5 retires the inline orchestration |
| `RetryStep`, `LoggedStep`, `CostTrackedStep` Decorator wrappers | Phase 2; `AbstractStep` foundation must be stable first |
| JSON workflow format and loader | Phase 3; no GUI consumer yet named |
| `execute()` made `final` via metaclass or `__init_subclass__` | Python has no `final` for methods; the structural test `abstractStep_execute_isConcreteTemplateMethod` is the enforcement mechanism; a metaclass would be over-engineering for the current risk level |
| `async def execute()` | Phase 2 alongside `Parallel` step kind; synchronous generators are compatible with the existing CLI subprocess provider |