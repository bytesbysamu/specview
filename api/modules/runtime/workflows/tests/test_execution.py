"""Unit tests for ExecutionStatus + WorkflowExecution.

Cover every valid transition arc, every illegal transition, the
predicates (is_running / is_terminal), and the side-effect on .error
when fail() is called.
"""
from __future__ import annotations

import pytest

from modules.runtime.workflows.execution import (
    ExecutionStatus,
    InvalidStatusTransition,
    WorkflowExecution,
)


def buildExec() -> WorkflowExecution:
    return WorkflowExecution(workflow_ref="test/wf", inputs={})


# ── Status transitions ──────────────────────────────────────────────────────

def newExecution_hasNewStatus():
    assert buildExec().status is ExecutionStatus.NEW


def newToInProgress_succeeds():
    exc = buildExec()
    exc.start()
    assert exc.status is ExecutionStatus.IN_PROGRESS


def inProgressToCompleted_succeeds():
    exc = buildExec()
    exc.start()
    exc.complete()
    assert exc.status is ExecutionStatus.COMPLETED


def inProgressToError_succeeds():
    exc = buildExec()
    exc.start()
    exc.fail("oops")
    assert exc.status is ExecutionStatus.ERROR
    assert exc.error == "oops"


def inProgressToTimeout_succeeds():
    exc = buildExec()
    exc.start()
    exc.timeout()
    assert exc.status is ExecutionStatus.TIMEOUT


def inProgressToCancelling_succeeds():
    exc = buildExec()
    exc.start()
    exc.request_cancel()
    assert exc.status is ExecutionStatus.CANCELLING


def cancellingToCancelled_succeeds():
    exc = buildExec()
    exc.start()
    exc.request_cancel()
    exc.cancel()
    assert exc.status is ExecutionStatus.CANCELLED


# ── Invalid transitions ─────────────────────────────────────────────────────

def newToCompleted_raisesInvalidTransition():
    exc = buildExec()
    with pytest.raises(InvalidStatusTransition, match="NEW"):
        exc.complete()


def newToError_raisesInvalidTransition():
    exc = buildExec()
    with pytest.raises(InvalidStatusTransition, match="NEW"):
        exc.fail("never started")


def completedToFail_raisesInvalidTransition():
    exc = buildExec()
    exc.start()
    exc.complete()
    with pytest.raises(InvalidStatusTransition):
        exc.fail("late error")


def errorToComplete_raisesInvalidTransition():
    exc = buildExec()
    exc.start()
    exc.fail("err")
    with pytest.raises(InvalidStatusTransition):
        exc.complete()


def cancelledToAny_raisesInvalidTransition():
    exc = buildExec()
    exc.start()
    exc.request_cancel()
    exc.cancel()
    with pytest.raises(InvalidStatusTransition):
        exc.complete()


def inProgressToCancelled_raisesInvalidTransition():
    """Direct IN_PROGRESS -> CANCELLED is illegal; must request_cancel first."""
    exc = buildExec()
    exc.start()
    with pytest.raises(InvalidStatusTransition):
        exc.cancel()


# ── Predicates ──────────────────────────────────────────────────────────────

def isRunning_trueWhenInProgress():
    exc = buildExec()
    exc.start()
    assert exc.is_running is True


def isRunning_falseWhenNew():
    assert buildExec().is_running is False


def isRunning_falseWhenCompleted():
    exc = buildExec()
    exc.start()
    exc.complete()
    assert exc.is_running is False


def isTerminal_trueForCompleted():
    exc = buildExec()
    exc.start()
    exc.complete()
    assert exc.is_terminal is True


def isTerminal_trueForError():
    exc = buildExec()
    exc.start()
    exc.fail("x")
    assert exc.is_terminal is True


def isTerminal_trueForTimeout():
    exc = buildExec()
    exc.start()
    exc.timeout()
    assert exc.is_terminal is True


def isTerminal_trueForCancelled():
    exc = buildExec()
    exc.start()
    exc.request_cancel()
    exc.cancel()
    assert exc.is_terminal is True


def isTerminal_falseWhenInProgress():
    exc = buildExec()
    exc.start()
    assert exc.is_terminal is False


def isTerminal_falseWhenCancelling():
    """CANCELLING is in-flight, not terminal."""
    exc = buildExec()
    exc.start()
    exc.request_cancel()
    assert exc.is_terminal is False


# ── Misc ─────────────────────────────────────────────────────────────────────

def fail_setsErrorField():
    exc = buildExec()
    exc.start()
    exc.fail("database gone")
    assert exc.error == "database gone"


def executionId_isUniquePerInstance():
    a, b = buildExec(), buildExec()
    assert a.execution_id != b.execution_id
