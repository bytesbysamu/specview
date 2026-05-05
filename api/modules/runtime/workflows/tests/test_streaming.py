"""Tests for AICall streaming path.

Covers:
  - stream=False: synchronous generate is called; no partials written
  - stream=True:  stream_generate is iterated; rolling 500-char tail written
  - Rolling tail truncates at 500 chars regardless of total output length
  - Multi-step workflow: each streamed step writes its own _partials entry
  - Adapter raises NotImplementedError when active provider lacks streaming
"""
from __future__ import annotations

import pytest

from modules.runtime.chain.types import ChainResult
from modules.runtime.workflows import (
    ExecutionStatus,
    WorkflowExecution,
    WorkflowRuntime,
)
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.steps.base import StepContext
from modules.runtime.workflows.workflow import Workflow


def aiCall_streamFalse_callsGenerateAndWritesNoPartials(monkeypatch):
    """Default stream=False path must call adapter.generate and not touch _partials."""
    calls = {"generate": 0, "stream": 0}

    def _fake_generate(system, prompt, *, model, max_tokens):
        calls["generate"] += 1
        return ChainResult(text="sync-output", latency_ms=42)

    def _fake_stream(*args, **kwargs):
        calls["stream"] += 1
        return iter(())

    monkeypatch.setattr("modules.runtime.chain.adapter.generate", _fake_generate)
    monkeypatch.setattr("modules.runtime.chain.adapter.stream_generate", _fake_stream)

    wf = (
        Workflow.builder("test-sync")
        .inputs("seed").outputs("only")
        .step(AICall(
            name="only",
            system="sys",
            prompt_template="prompt {seed}",
            input_keys=("seed",),
        ))
        .build()
    )
    execution = WorkflowExecution(workflow_ref="test/sync", inputs={"seed": "x"})
    list(WorkflowRuntime().run(execution, wf))

    assert calls["generate"] == 1, f"adapter.generate must be called once; got {calls}"
    assert calls["stream"] == 0, f"stream_generate must not be called; got {calls}"
    assert "_partials" not in execution.outputs, (
        f"No _partials when stream=False; outputs were {list(execution.outputs)}"
    )


def aiCall_streamTrue_writesRollingTailToPartials(monkeypatch):
    """stream=True must populate context.outputs['_partials'][step.name] per chunk
    and surface the full join on the returned ChainResult."""
    chunks = ["hello ", "world ", "from ", "stream"]

    def _fake_stream(system, prompt, *, model, max_tokens):
        for c in chunks:
            yield c

    monkeypatch.setattr("modules.runtime.chain.adapter.stream_generate", _fake_stream)

    wf = (
        Workflow.builder("test-stream")
        .inputs("seed").outputs("streamed")
        .step(AICall(
            name="streamed",
            system="sys",
            prompt_template="prompt {seed}",
            input_keys=("seed",),
            stream=True,
        ))
        .build()
    )
    execution = WorkflowExecution(workflow_ref="test/stream", inputs={"seed": "x"})
    list(WorkflowRuntime().run(execution, wf))

    assert execution.status is ExecutionStatus.COMPLETED, (
        f"Expected COMPLETED, got {execution.status}"
    )
    final_text = execution.outputs["streamed"].text
    assert final_text == "hello world from stream", (
        f"Final ChainResult.text must be the full join; got {final_text!r}"
    )


def aiCall_streamTrue_tailNeverExceeds500Chars(monkeypatch):
    """Rolling tail must clip at the last 500 chars, regardless of stream length."""
    chunk = "x" * 100  # ten chunks of 100 -> 1000 total chars

    def _fake_stream(system, prompt, *, model, max_tokens):
        for _ in range(10):
            yield chunk

    monkeypatch.setattr("modules.runtime.chain.adapter.stream_generate", _fake_stream)

    wf = (
        Workflow.builder("test-clip")
        .inputs("seed").outputs("clipped")
        .step(AICall(
            name="clipped",
            system="sys",
            prompt_template="p {seed}",
            input_keys=("seed",),
            stream=True,
        ))
        .build()
    )
    execution = WorkflowExecution(workflow_ref="test/clip", inputs={"seed": "y"})
    list(WorkflowRuntime().run(execution, wf))

    final_text = execution.outputs["clipped"].text
    assert len(final_text) == 1000, f"Expected 1000-char output; got {len(final_text)}"

    # Verify the slice expression by feeding through a fresh execution whose
    # StepContext we observe directly. The rolling tail after a 1000-char
    # stream of 'x' must be exactly 500 'x' chars.
    ctx = StepContext(run_id="t", inputs={"seed": "y"}, outputs={})
    step = AICall(
        name="probe", system="sys", prompt_template="p {seed}",
        input_keys=("seed",), stream=True,
    )
    step._invoke(ctx)
    assert len(ctx.outputs["_partials"]["probe"]) == 500, (
        f"Rolling tail must be exactly 500 chars after 1000-char stream; "
        f"got {len(ctx.outputs['_partials']['probe'])}"
    )
    assert ctx.outputs["_partials"]["probe"] == "x" * 500, (
        "Tail must be the LAST 500 chars (all 'x' here)"
    )


def aiCall_streamTrue_multiStepKeepsPerStepPartials(monkeypatch):
    """Two streaming steps must write to distinct keys under _partials."""
    counter = {"calls": 0}

    def _fake_stream(system, prompt, *, model, max_tokens):
        counter["calls"] += 1
        yield f"chunk-from-call-{counter['calls']}"

    monkeypatch.setattr("modules.runtime.chain.adapter.stream_generate", _fake_stream)

    wf = (
        Workflow.builder("test-multi")
        .inputs("seed").outputs("a", "b")
        .step(AICall(
            name="a", system="s", prompt_template="p {seed}",
            input_keys=("seed",), stream=True,
        ))
        .step(AICall(
            name="b", system="s", prompt_template="p {seed}",
            input_keys=("seed",), stream=True,
        ))
        .build()
    )
    # Probe via direct _invoke on a shared StepContext so we can inspect the
    # per-step _partials entries; the runtime mirrors only step outputs onto
    # execution.outputs, not the auxiliary _partials key.
    ctx = StepContext(run_id="t", inputs={"seed": "z"}, outputs={})
    for step in wf.steps:
        step._invoke(ctx)

    partials = ctx.outputs["_partials"]
    assert set(partials.keys()) == {"a", "b"}, (
        f"Expected partials for both steps; got {sorted(partials.keys())}"
    )
    assert partials["a"] == "chunk-from-call-1"
    assert partials["b"] == "chunk-from-call-2"


def chainAdapter_streamGenerate_raisesOnNonStreamingProvider(monkeypatch):
    """A provider without stream_generate must surface NotImplementedError clearly."""
    from modules.runtime.chain import adapter as chain_adapter

    class _NoStreamProvider:
        def generate(self, system, prompt, *, model, max_tokens):
            return ChainResult(text="x", latency_ms=0)

    monkeypatch.setattr(chain_adapter, "_get_active_provider", lambda: _NoStreamProvider())

    with pytest.raises(NotImplementedError, match="does not support streaming"):
        list(chain_adapter.stream_generate("sys", "prompt", model="m", max_tokens=10))


def aiCall_streamTrue_invokesPartialCallbackPerChunk(monkeypatch):
    """If context.inputs['_partial_callback'] is supplied, AICall must call it
    with (step_name, rolling_tail) once per chunk so push-style consumers do
    not have to poll context.outputs['_partials']."""
    def _fake_stream(system, prompt, *, model, max_tokens):
        for c in ("a", "bb", "ccc"):
            yield c

    monkeypatch.setattr("modules.runtime.chain.adapter.stream_generate", _fake_stream)

    received: list[tuple[str, str]] = []

    def _cb(name, tail):
        received.append((name, tail))

    step = AICall(
        name="cb-step", system="s", prompt_template="p {seed}",
        input_keys=("seed",), stream=True,
    )
    ctx = StepContext(
        run_id="t",
        inputs={"seed": "x", "_partial_callback": _cb},
        outputs={},
    )
    step._invoke(ctx)

    # One callback per chunk; tails are progressive accumulations clipped at 500.
    assert received == [("cb-step", "a"), ("cb-step", "abb"), ("cb-step", "abbccc")], (
        f"callback must fire per chunk with (name, rolling_tail); got {received}"
    )
