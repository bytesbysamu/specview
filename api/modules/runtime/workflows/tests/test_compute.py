"""Unit tests for Compute step — value-object semantics and _invoke behaviour."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.runtime.workflows.steps.base import StepContext
from modules.runtime.workflows.steps.compute import Compute
from modules.runtime.workflows.steps.registry import register


def stepCtx(inputs=None, outputs=None) -> StepContext:
    """Build a minimal StepContext for _invoke() and execute() tests."""
    return StepContext(run_id="run-001", inputs=inputs or {}, outputs=outputs or {})


# ---------------------------------------------------------------------------
# Value-object immutability
# ---------------------------------------------------------------------------


def compute_isImmutable():
    step = Compute(name="s", fn_name="my-fn")
    with pytest.raises((ValidationError, TypeError)):
        step.fn_name = "mutated"  # type: ignore[misc]


def compute_equalByValue():
    a = Compute(name="s", fn_name="my-fn")
    b = Compute(name="s", fn_name="my-fn")
    assert a == b, "Two Compute instances with identical fields must compare equal"


def compute_differentFnName_notEqual():
    a = Compute(name="s", fn_name="fn-a")
    b = Compute(name="s", fn_name="fn-b")
    assert a != b


# ---------------------------------------------------------------------------
# Registry dispatch
# ---------------------------------------------------------------------------


def compute_invoke_dispatchesToRegisteredCallable():
    def double(context):
        return context.inputs["x"] * 2

    register("double", double)
    step = Compute(name="s", fn_name="double")
    result = step._invoke(stepCtx(inputs={"x": 5}))
    assert result == 10, f"expected 10 from double(5), got {result}"


def compute_invoke_passesContextToCallable():
    received: dict = {}

    def capture(context):
        received["inputs"] = context.inputs
        received["outputs"] = context.outputs
        received["run_id"] = context.run_id
        return "done"

    register("capture", capture)
    step = Compute(name="s", fn_name="capture")
    step._invoke(stepCtx(inputs={"key": "val"}, outputs={"prior": "x"}))

    assert received["inputs"] == {"key": "val"}, (
        f"context.inputs not passed correctly; got: {received.get('inputs')}"
    )
    assert received["outputs"] == {"prior": "x"}, (
        f"context.outputs not passed correctly; got: {received.get('outputs')}"
    )
    assert received["run_id"] == "run-001"


def compute_invoke_returnsCallableReturnValue():
    register("identity", lambda c: c.inputs)
    step = Compute(name="s", fn_name="identity")
    result = step._invoke(stepCtx(inputs={"a": 1}))
    assert result == {"a": 1}, f"_invoke must return the callable's return value; got {result}"


def compute_invoke_unregisteredFnName_raisesKeyError():
    step = Compute(name="s", fn_name="not-registered")
    with pytest.raises(KeyError, match="not-registered"):
        step._invoke(stepCtx())


def compute_invoke_callableException_propagatesUnwrapped():
    def explode(context):
        raise RuntimeError("boom")

    register("exploder", explode)
    step = Compute(name="s", fn_name="exploder")
    with pytest.raises(RuntimeError, match="boom"):
        step._invoke(stepCtx())


def compute_construction_doesNotValidateFnName():
    """Compute must NOT validate fn_name against the registry at construction time.

    Reason: workflows may be defined before their callables are registered
    (e.g. workflow Python file imported before the feature module's startup
    registers its callables).  Resolution is deferred to _invoke time.
    """
    # Should not raise even though "deferred-fn" is not registered yet
    step = Compute(name="s", fn_name="deferred-fn")
    assert step.fn_name == "deferred-fn"

    # Registering after construction must make _invoke succeed
    register("deferred-fn", lambda c: "ok")
    result = step._invoke(stepCtx())
    assert result == "ok"


# ---------------------------------------------------------------------------
# Integration through execute() — Requires Task 1.1
# ---------------------------------------------------------------------------


def compute_execute_emitsStepStartedAndStepCompleted():  # Requires Task 1.1
    from modules.runtime.workflows.steps.events import StepCompleted, StepStarted

    register("noop", lambda c: {"processed": True})
    step = Compute(name="my-compute", fn_name="noop")
    ctx = StepContext(run_id="r", inputs={})
    events = list(step.execute(ctx))

    assert any(isinstance(e, StepStarted) for e in events), f"StepStarted missing: {events}"
    assert any(isinstance(e, StepCompleted) for e in events), f"StepCompleted missing: {events}"
    assert ctx.outputs["my-compute"] == {"processed": True}, (
        f"execute() must store callable result in context.outputs[name]; got {ctx.outputs}"
    )
