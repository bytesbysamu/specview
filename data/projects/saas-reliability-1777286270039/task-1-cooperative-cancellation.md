# Task 1: Cooperative Cancellation in WorkflowRuntime

**Effort**: 0.3 days

## Overview

Wire the existing `WorkflowExecution.request_cancel()` API into `WorkflowRuntime.run()` by reading `execution.status` between every step iteration. When the status is `ExecutionStatus.CANCELLING`, the runtime transitions to `CANCELLED` and returns before the next step runs. The change is one `if` in the runtime loop plus four tests covering the cancel-between-steps path. No new domain types are introduced; the existing `request_cancel()` and `cancel()` transition helpers on `WorkflowExecution` (already shipped via the Workflows epic) are the only mutation surface.

Cancellation is cooperative: the in-flight `chain_adapter.generate()` call still completes (no subprocess kill, no SDK abort). Cancellation latency is bounded by the longest single step (currently the architecture step at 16k tokens, ~3-9 minutes). This is the deliberate trade — preemptive cancellation is a separate epic with race-y SDK abort plumbing and no current SLA driving it. See [Solution Architecture](./architecture.md) § Cancellation Read for the rationale.

## Prerequisites

- `{WORKSPACE}/api/modules/runtime/workflows/runtime.py` exists with `WorkflowRuntime.run(execution, workflow)` (Workflows epic Task 3 — shipped)
- `{WORKSPACE}/api/modules/runtime/workflows/execution.py` exposes `ExecutionStatus.CANCELLING`, `ExecutionStatus.CANCELLED`, `WorkflowExecution.request_cancel()`, and `WorkflowExecution.cancel()` (Workflows epic Task 3 — shipped)
- `make test` is green on master before this task starts
- Working tree is clean on `api/modules/runtime/workflows/runtime.py` and `api/modules/runtime/workflows/tests/`

Run from `{WORKSPACE}/api/`:

```bash
git status
python -m pytest -q 2>&1 | tail -5
python -c "from modules.runtime.workflows import WorkflowExecution, ExecutionStatus, WorkflowRuntime; e = WorkflowExecution('x', {}); e.start(); e.request_cancel(); e.cancel(); print(e.status)"
```

The third command must print `ExecutionStatus.CANCELLED`. If it fails, the Workflows epic Task 3 is not complete — stop and resolve before continuing.

## Implementation Steps

### Step 1: Import ExecutionStatus into runtime.py

**File**: `{WORKSPACE}/api/modules/runtime/workflows/runtime.py`

Replace the existing line:

```python
from .execution import WorkflowExecution
```

with:

```python
from .execution import ExecutionStatus, WorkflowExecution
```

### Step 2: Add cancellation read at the top of each step iteration

**File**: `{WORKSPACE}/api/modules/runtime/workflows/runtime.py`

Locate the `for step in workflow.steps:` block inside `WorkflowRuntime.run`. At the very top of that loop body — before `last_event: StepEvent | None = None` — insert the cancellation check:

```python
        for step in workflow.steps:
            if execution.status is ExecutionStatus.CANCELLING:
                execution.cancel()
                return
            last_event: StepEvent | None = None
            try:
                for event in step.execute(context):
                    last_event = event
                    yield event
            except Exception as exc:
                if not execution.is_terminal:
                    execution.fail(str(exc))
                return

            if step.name in context.outputs:
                execution.outputs[step.name] = context.outputs[step.name]

        execution.complete()
```

### Step 3: Document the cancellation contract in the runtime docstring

**File**: `{WORKSPACE}/api/modules/runtime/workflows/runtime.py`

Update the `WorkflowRuntime.run` docstring to add a "Cancellation" subsection after the existing "Lifecycle" block:

```
        Cancellation:
            Between every step iteration the runtime checks
            ``execution.status is ExecutionStatus.CANCELLING``.  If a caller
            invoked ``execution.request_cancel()`` from another thread, the
            runtime transitions ``CANCELLING -> CANCELLED`` and returns
            before the next step starts.  Cancellation is cooperative
            (between-steps); an in-flight ``step.execute()`` always runs to
            completion.  Cancellation latency is at most one full step.
```

### Step 4: Verify existing failure handling is preserved

The new check is a no-op when `execution.status is ExecutionStatus.IN_PROGRESS`. No changes to the `try`/`except` block or the step output mirroring. Run the existing runtime tests to confirm:

```bash
cd {WORKSPACE}/api
python -m pytest modules/runtime/workflows/tests/test_runtime.py -q
```

All previously-passing runtime tests must still pass. If any fails, the new `if` is in the wrong place — verify it sits at the top of the `for` body, above `last_event: StepEvent | None = None`.

## Tests

Append four new test functions to the existing `{WORKSPACE}/api/modules/runtime/workflows/tests/test_runtime.py`. Use the same naming convention as the existing tests in that file (`category_description` style; collected via `python_functions = ["test_*", "*_*"]` in `pyproject.toml`).

```python
from modules.runtime.workflows import (
    ExecutionStatus,
    WorkflowExecution,
    WorkflowRuntime,
)


class _PassThroughStep:
    """Minimal StepProtocol stub: writes a fixed string to context.outputs[name]."""

    def __init__(self, name: str, output: str = "ok"):
        self.name = name
        self._output = output

    def execute(self, context):
        context.outputs[self.name] = self._output
        return iter(())


class _Wf:
    def __init__(self, *steps):
        self.name = "test-cancel-wf"
        self.steps = list(steps)


def cancellingBetweenSteps_haltsBeforeNextStep():
    """A cancel signalled after step 1 finishes must skip step 2 entirely."""
    execution = WorkflowExecution(workflow_ref="test/wf", inputs={})
    executed_after_cancel: list[str] = []

    class _RecordStep:
        name = "record"

        def execute(self, context):
            executed_after_cancel.append(self.name)
            context.outputs[self.name] = "ran"
            return iter(())

    class _StepThenCancel:
        name = "step1"

        def execute(self, context):
            context.outputs[self.name] = "first-out"
            execution.request_cancel()
            return iter(())

    workflow = _Wf(_StepThenCancel(), _RecordStep())
    list(WorkflowRuntime().run(execution, workflow))

    assert execution.status is ExecutionStatus.CANCELLED, (
        f"Expected CANCELLED, got {execution.status}"
    )
    assert executed_after_cancel == [], (
        f"Step after cancel must not run; executed: {executed_after_cancel}"
    )
    assert execution.outputs.get("step1") == "first-out", (
        "Output from the step that triggered cancel must still be preserved"
    )


def cancellingDoesNotInterruptInFlightStep():
    """Cancel signalled while step is mid-execute completes the in-flight step."""
    execution = WorkflowExecution(workflow_ref="test/wf", inputs={})

    class _SelfCancellingStep:
        name = "self-cancel"

        def execute(self, context):
            execution.request_cancel()
            # Continue doing work after request_cancel — must complete.
            context.outputs[self.name] = "completed-despite-cancel"
            return iter(())

    workflow = _Wf(_SelfCancellingStep())
    list(WorkflowRuntime().run(execution, workflow))

    assert execution.outputs.get("self-cancel") == "completed-despite-cancel", (
        "In-flight step must complete; cancel only takes effect between steps"
    )
    # The self-cancelling step is the last step, so the runtime exits the
    # loop without checking the cancellation flag again. Status remains
    # CANCELLING because the COMPLETED transition is illegal from CANCELLING.
    assert execution.status is ExecutionStatus.CANCELLING, (
        f"Expected CANCELLING after self-cancel on last step "
        f"(loop never re-checks); got {execution.status}"
    )


def noCancelSignal_completesNormally():
    """Without a cancel signal, the cancellation check must be a no-op."""
    execution = WorkflowExecution(workflow_ref="test/wf", inputs={})
    workflow = _Wf(_PassThroughStep("a", "out-a"), _PassThroughStep("b", "out-b"))

    list(WorkflowRuntime().run(execution, workflow))

    assert execution.status is ExecutionStatus.COMPLETED, (
        f"Expected COMPLETED with no cancel signal; got {execution.status}"
    )
    assert execution.outputs == {"a": "out-a", "b": "out-b"}, (
        f"Both step outputs expected; got {execution.outputs}"
    )


def cancelOnFirstIteration_yieldsZeroEventsAndStops():
    """A cancel set after .start() but before any step runs must skip all steps."""
    execution = WorkflowExecution(workflow_ref="test/wf", inputs={})
    # Pre-arrange: run a no-op step that flips cancel before the next step.
    flag = {"second_ran": False}

    class _FirstStep:
        name = "first"

        def execute(self, context):
            execution.request_cancel()
            return iter(())

    class _SecondStep:
        name = "second"

        def execute(self, context):
            flag["second_ran"] = True
            return iter(())

    workflow = _Wf(_FirstStep(), _SecondStep())
    list(WorkflowRuntime().run(execution, workflow))

    assert flag["second_ran"] is False, (
        "Second step must not run after first step requested cancellation"
    )
    assert execution.status is ExecutionStatus.CANCELLED, (
        f"Expected CANCELLED, got {execution.status}"
    )
```

Verify by running the tests in isolation first:

```bash
cd {WORKSPACE}/api
python -m pytest modules/runtime/workflows/tests/test_runtime.py -v -k "cancel or noCancel"
```

All four new tests must pass plus all previously-existing runtime tests.

## Verification

Run from `{WORKSPACE}/api/`:

```bash
python -m pytest -q
```

Expected delta: **N → N+4 passing** (four new cancellation tests in `test_runtime.py`; zero existing tests broken). Record the pre-task baseline as N before edits.

Spot-check the target file:

```bash
grep -n "ExecutionStatus.CANCELLING" modules/runtime/workflows/runtime.py
```

Must print exactly one line, in the body of `WorkflowRuntime.run`.

```bash
python -m pytest modules/runtime/workflows/tests/test_runtime.py -v
```

Confirms: all runtime tests green, including the four new tests.

```bash
make lint
```

Confirms: flake8 clean (max-line-length 120; no unused imports).

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
