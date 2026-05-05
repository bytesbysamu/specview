"""Tests for AbstractStep Template Method, StepContext, and StepEvent types.

Concrete helper steps defined here are minimal stubs — no provider, no filesystem.
Every test drains the execute() generator directly.
"""
from __future__ import annotations

from typing import Any

import pytest

from modules.runtime.workflows.steps import (
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
    collect(EchoStep(name="echo"), context)
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
