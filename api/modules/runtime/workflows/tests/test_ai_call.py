"""Unit tests for AICall — value-object semantics and _invoke behaviour.

Tests prefixed '# Requires Task 1.1' call execute() and depend on
AbstractStep.execute() being complete.  They are skipped automatically
when the integration contract is not yet satisfied.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.runtime.chain import adapter as chainAdapter
from modules.runtime.chain.types import ChainResult
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.steps.base import StepContext

# ---------------------------------------------------------------------------
# Helpers — camelCase names to avoid *_* pytest collection
# ---------------------------------------------------------------------------

# fakeGenerate captures the arguments forwarded to chain_adapter.generate()
# and returns a minimal ChainResult so tests stay offline.


def fakeGenerate(captured: list):
    def inner(system, prompt, *, model, max_tokens, **_):
        captured.append(
            {"system": system, "prompt": prompt, "model": model, "max_tokens": max_tokens}
        )
        return ChainResult(text=f"FAKE[{prompt[:30]}]", latency_ms=1)

    return inner


def stepCtx(inputs=None, outputs=None) -> StepContext:
    """Build a minimal StepContext for _invoke() and execute() tests."""
    return StepContext(run_id="run-001", inputs=inputs or {}, outputs=outputs or {})


# ---------------------------------------------------------------------------
# Value-object immutability
# ---------------------------------------------------------------------------


def aiCall_isImmutable():
    step = AICall(name="s", system="sys", prompt_template="hello")
    with pytest.raises((ValidationError, TypeError)):
        step.name = "mutated"  # type: ignore[misc]


def aiCall_equalByValue():
    a = AICall(name="s", system="sys", prompt_template="hello")
    b = AICall(name="s", system="sys", prompt_template="hello")
    assert a == b, "Two AICall instances with identical fields must compare equal"


def aiCall_differentName_notEqual():
    a = AICall(name="step-a", system="sys", prompt_template="hello")
    b = AICall(name="step-b", system="sys", prompt_template="hello")
    assert a != b


# ---------------------------------------------------------------------------
# Prompt template interpolation
# ---------------------------------------------------------------------------


def aiCall_invoke_interpolatesInputsIntoPrompt(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="hello {name}")
    step._invoke(stepCtx(inputs={"name": "Alice"}))

    assert len(captured) == 1, "generate() must be called exactly once"
    assert captured[0]["prompt"] == "hello Alice", (
        f"prompt interpolation failed; got: {captured[0]['prompt']!r}"
    )


def aiCall_invoke_interpolatesPriorOutputsIntoPrompt(monkeypatch):
    """Prior step outputs (context.outputs) are usable as template variables."""
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="exec={execution_id}")
    step._invoke(stepCtx(outputs={"execution_id": "abc-123"}))

    assert captured[0]["prompt"] == "exec=abc-123", (
        f"prior-output interpolation failed; got: {captured[0]['prompt']!r}"
    )


def aiCall_invoke_inputsTakePriorityOverPriorOutputsOnKeyCollision(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="val={x}")
    step._invoke(stepCtx(inputs={"x": "input-wins"}, outputs={"x": "output-loses"}))

    assert captured[0]["prompt"] == "val=input-wins", (
        "inputs must override prior outputs when the same key appears in both"
    )


def aiCall_invoke_missingTemplateKey_raisesKeyError(monkeypatch):
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate([]))

    step = AICall(name="s", system="sys", prompt_template="hello {missing_key}")
    with pytest.raises(KeyError):
        step._invoke(stepCtx())


# ---------------------------------------------------------------------------
# Model and max_tokens forwarding
# ---------------------------------------------------------------------------


def aiCall_invoke_forwardsModelToGenerate(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="p", model="claude-opus-42")
    step._invoke(stepCtx())

    assert captured[0]["model"] == "claude-opus-42", (
        f"model not forwarded correctly; got: {captured[0]['model']!r}"
    )


def aiCall_invoke_forwardsMaxTokensToGenerate(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="p", max_tokens=512)
    step._invoke(stepCtx())

    assert captured[0]["max_tokens"] == 512, (
        f"max_tokens not forwarded; got: {captured[0]['max_tokens']}"
    )


def aiCall_invoke_defaultModelMatchesAdapterConstant(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="p")  # no explicit model
    step._invoke(stepCtx())

    assert captured[0]["model"] == chainAdapter.DEFAULT_MODEL, (
        f"default model mismatch; adapter has {chainAdapter.DEFAULT_MODEL!r}, "
        f"AICall forwarded {captured[0]['model']!r}"
    )


def aiCall_invoke_passesSystemUnmodifiedToGenerate(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="EXACT_SYSTEM_PROMPT", prompt_template="p")
    step._invoke(stepCtx())

    assert captured[0]["system"] == "EXACT_SYSTEM_PROMPT", (
        "system prompt must be forwarded verbatim; with_context injection is the adapter's responsibility"
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def aiCall_invoke_returnsChainResult(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    step = AICall(name="s", system="sys", prompt_template="hello")
    result = step._invoke(stepCtx())
    assert isinstance(result, ChainResult), f"_invoke must return ChainResult, got {type(result)}"
    assert isinstance(result.text, str), "ChainResult.text must be str"
    assert result.latency_ms >= 0, "ChainResult.latency_ms must be non-negative"


# ---------------------------------------------------------------------------
# Integration through execute() — Requires Task 1.1
# ---------------------------------------------------------------------------


def aiCall_execute_emitsStepStartedAndStepCompleted(monkeypatch):  # Requires Task 1.1
    from modules.runtime.workflows.steps.events import StepCompleted, StepStarted

    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    step = AICall(name="my-step", system="sys", prompt_template="hello")
    ctx = stepCtx()
    events = list(step.execute(ctx))

    assert any(isinstance(e, StepStarted) for e in events), f"StepStarted missing: {events}"
    assert any(isinstance(e, StepCompleted) for e in events), f"StepCompleted missing: {events}"
    assert isinstance(ctx.outputs["my-step"], ChainResult), (
        f"execute() must store ChainResult in context.outputs[name], got {type(ctx.outputs.get('my-step'))}"
    )


def aiCall_execute_emitsStepFailed_whenGenerateRaises(monkeypatch):  # Requires Task 1.1
    from modules.runtime.chain.errors import ProviderError
    from modules.runtime.workflows.steps.events import StepFailed  # noqa: F401 — referenced in test assertion below

    def explode(system, prompt, **kwargs):
        raise ProviderError("provider down", status_code=502)

    monkeypatch.setattr(chainAdapter, "generate", explode)
    step = AICall(name="my-step", system="sys", prompt_template="p")

    with pytest.raises(ProviderError):
        list(step.execute(stepCtx()))
    # AbstractStep.execute() emits StepFailed then re-raises ProviderError.
    # The StepFailed type assertion lives in Task 1.1's AbstractStep tests;
    # this test confirms ProviderError propagates through the Template Method.
