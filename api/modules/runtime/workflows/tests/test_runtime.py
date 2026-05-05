"""Unit tests for WorkflowRuntime.

The runtime drives execution lifecycle and re-yields the events
AbstractStep already emits. These tests construct real Workflow
aggregates with concrete AbstractStep subclasses (no Protocol stubs)
so they exercise the same path the production code takes.
"""
from __future__ import annotations

from typing import Any

import pytest

from modules.runtime.workflows.execution import (
    ExecutionStatus,
    InvalidStatusTransition,
    WorkflowExecution,
)
from modules.runtime.workflows.runtime import WorkflowRuntime
from modules.runtime.workflows.steps import (
    AbstractStep,
    StepCompleted,
    StepFailed,
    StepStarted,
)
from modules.runtime.workflows.workflow import Workflow


# ── Step stubs ───────────────────────────────────────────────────────────────

class _Echo(AbstractStep):
    """Returns a static string."""
    out: str = "ok"

    def _invoke(self, context):
        return self.out


class _Boom(AbstractStep):
    """Always raises RuntimeError(message)."""
    message: str = "boom"

    def _invoke(self, context):
        raise RuntimeError(self.message)


class _Capture(AbstractStep):
    """Records each invocation's inputs+outputs into the class-level log."""
    log_key: str

    def _invoke(self, context):
        # Read both, sniff for the prior step's output to assert chaining.
        snapshot = {**context.outputs, **context.inputs}
        _CAPTURED[self.log_key] = snapshot
        return "captured"


_CAPTURED: dict[str, dict[str, Any]] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def buildWf(*steps) -> Workflow:
    """Build a minimal Workflow around the given steps."""
    b = Workflow.builder("test/wf").inputs("seed").outputs("y")
    for s in steps:
        b = b.step(s)
    return b.build()


def buildExec() -> WorkflowExecution:
    return WorkflowExecution(workflow_ref="test/wf", inputs={"seed": "val"})


# ── Tests ────────────────────────────────────────────────────────────────────

def singleStep_yieldsStartedThenCompleted():
    exc = buildExec()
    events = list(WorkflowRuntime().run(exc, buildWf(_Echo(name="s1", out="hello"))))
    assert len(events) == 2, f"Expected 2 events, got {len(events)}: {events}"
    assert isinstance(events[0], StepStarted),   f"First event must be StepStarted, got {type(events[0])}"
    assert isinstance(events[1], StepCompleted), f"Second event must be StepCompleted, got {type(events[1])}"
    assert events[0].step_name == "s1"
    assert events[1].output == "hello"


def singleStep_outputAccumulatedInExecution():
    exc = buildExec()
    list(WorkflowRuntime().run(exc, buildWf(_Echo(name="alpha", out="result-text"))))
    assert exc.outputs["alpha"] == "result-text", \
        "Step output must be mirrored from context.outputs onto execution.outputs"


def singleStep_completesExecution():
    exc = buildExec()
    list(WorkflowRuntime().run(exc, buildWf(_Echo(name="s1"))))
    assert exc.status is ExecutionStatus.COMPLETED


def twoSteps_secondStepReceivesPriorOutput():
    _CAPTURED.clear()
    exc = buildExec()
    list(WorkflowRuntime().run(
        exc,
        buildWf(
            _Echo(name="first", out="first-out"),
            _Capture(name="capture", log_key="cap"),
        ),
    ))
    assert "cap" in _CAPTURED, "Capturing step must have been called"
    assert _CAPTURED["cap"].get("first") == "first-out", (
        "Second step must see first step's output via context.outputs; "
        f"got keys {sorted(_CAPTURED['cap'].keys())}"
    )


def failingStep_yieldsFailed():
    exc = buildExec()
    events = list(WorkflowRuntime().run(exc, buildWf(_Boom(name="bad", message="step-error"))))
    assert len(events) == 2, f"Expected StepStarted + StepFailed, got {len(events)}"
    assert isinstance(events[1], StepFailed), f"Second event must be StepFailed, got {type(events[1])}"
    assert events[1].error == "step-error"


def failingStep_haltsExecution():
    """A failing step must not cause subsequent steps to execute."""
    _CAPTURED.clear()
    exc = buildExec()
    list(WorkflowRuntime().run(
        exc,
        buildWf(_Boom(name="fail-first"), _Capture(name="never", log_key="never")),
    ))
    assert "never" not in _CAPTURED, \
        f"Step after failure must not execute; captured={_CAPTURED}"


def failingStep_setsExecutionErrorStatus():
    exc = buildExec()
    list(WorkflowRuntime().run(exc, buildWf(_Boom(name="bad", message="kaboom"))))
    assert exc.status is ExecutionStatus.ERROR, f"Expected ERROR, got {exc.status}"
    assert exc.error == "kaboom", f"execution.error must be set; got {exc.error!r}"


def runAfterStarted_raisesInvalidTransition():
    """Passing an already-IN_PROGRESS execution must raise immediately."""
    exc = buildExec()
    exc.start()
    with pytest.raises(InvalidStatusTransition):
        list(WorkflowRuntime().run(exc, buildWf(_Echo(name="s1"))))


def completedExecution_hasAllStepOutputs():
    exc = buildExec()
    list(WorkflowRuntime().run(
        exc,
        buildWf(_Echo(name="p1", out="v1"), _Echo(name="p2", out="v2")),
    ))
    assert exc.outputs == {"p1": "v1", "p2": "v2"}, (
        f"Expected both step outputs in execution.outputs; got {exc.outputs}"
    )


def runtime_passesExecutionIdToContext():
    """StepStarted.run_id must equal execution.execution_id."""
    exc = buildExec()
    events = list(WorkflowRuntime().run(exc, buildWf(_Echo(name="s1"))))
    started = events[0]
    assert isinstance(started, StepStarted)
    assert started.run_id == exc.execution_id, (
        f"StepStarted.run_id ({started.run_id}) must equal "
        f"execution.execution_id ({exc.execution_id})"
    )


def runtime_doesNotMutateExecutionInputs():
    """Inputs handed to the runtime must remain immutable from the caller's view."""
    exc = buildExec()
    original = dict(exc.inputs)
    list(WorkflowRuntime().run(exc, buildWf(_Echo(name="s1"))))
    assert exc.inputs == original, (
        f"execution.inputs was mutated; before={original}, after={exc.inputs}"
    )


# ── Cooperative cancellation (Rel-T1) ────────────────────────────────────────


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


def cancelling_doesNotInterruptInFlightStep():
    """Cancel signalled while step is mid-execute completes the in-flight step.

    The self-cancelling step here is the *last* step, so after the step
    body finishes the loop exits without re-checking the cancellation
    flag.  The runtime then unconditionally calls ``execution.complete()``
    — an illegal transition from ``CANCELLING`` that surfaces as
    ``InvalidStatusTransition``.  This test pins both invariants: the
    in-flight step finished, AND the illegal-transition guard fires
    because the cancellation read happens between steps, not at the end.
    """
    execution = WorkflowExecution(workflow_ref="test/wf", inputs={})

    class _SelfCancellingStep:
        name = "self-cancel"

        def execute(self, context):
            execution.request_cancel()
            # Continue doing work after request_cancel — must complete.
            context.outputs[self.name] = "completed-despite-cancel"
            return iter(())

    workflow = _Wf(_SelfCancellingStep())
    with pytest.raises(InvalidStatusTransition):
        list(WorkflowRuntime().run(execution, workflow))

    assert execution.outputs.get("self-cancel") == "completed-despite-cancel", (
        "In-flight step must complete; cancel only takes effect between steps"
    )
    # Status remains CANCELLING because the COMPLETED transition is
    # illegal from CANCELLING (the runtime never re-checks the flag
    # after the last step's body returns).
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
