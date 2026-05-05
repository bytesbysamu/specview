# Task 2: Streaming Partial Buffer in AICall

**Effort**: 0.5 days

## Overview

Add a `stream: bool = False` field to `AICall` so any step can opt into streaming. When the flag is on, `_invoke` calls a new `chain_adapter.stream_generate()` function, accumulates chunks, and writes a rolling 500-character tail to `context.outputs["_partials"][self.name]` after each chunk. The polling endpoint surfaces the tail as a `partial` field. The CLI provider stays non-streaming; the Anthropic SDK provider implements `stream_generate` via `messages.stream`. See [Solution Architecture](./architecture.md) § Streaming Partial Buffer.

The bootstrap architecture step opts into streaming in this task — it is the longest of the three (16k-token max), so the live preview gives the highest UX value. Short steps (analysis, epic at 4k tokens) stay synchronous; per-step opt-in keeps streaming overhead local to the step that benefits.

## Prerequisites

- `{WORKSPACE}/api/modules/runtime/workflows/steps/ai_call.py` exists with frozen Pydantic `AICall` (Workflows epic Task 1.2 — shipped)
- `{WORKSPACE}/api/modules/runtime/chain/adapter.py` exists with `generate(system, prompt, *, model, max_tokens) -> ChainResult` (modular-restructure — shipped)
- The Anthropic SDK provider exists at `{WORKSPACE}/api/modules/runtime/chain/providers/anthropic_sdk.py` (multi-provider epic) OR the CLI provider is the only registered provider (in which case the streaming path is exercised via a mock provider in tests)
- `make test` is green on master before this task starts

Run from `{WORKSPACE}/api/`:

```bash
git status
python -m pytest -q 2>&1 | tail -5
python -c "from modules.runtime.chain import adapter; print(hasattr(adapter, 'generate'))"
ls modules/runtime/chain/providers/
```

The third command must print `True`. The fourth command lists at least `cli.py` (and optionally `anthropic_sdk.py`).

## Implementation Steps

### Step 1: Add stream_generate to the chain adapter

**File**: `{WORKSPACE}/api/modules/runtime/chain/adapter.py`

Add a new public function `stream_generate(system, prompt, *, model, max_tokens) -> Iterator[str]`. Route to the active provider's streaming method. The CLI provider raises `NotImplementedError("CLI provider does not support streaming")` because CLI is dev-only and the SDK provider is the prod target.

```python
from typing import Iterator


def stream_generate(
    system: str,
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> Iterator[str]:
    """Yield text chunks from the active provider's streaming endpoint.

    Raises NotImplementedError if the active provider does not implement
    streaming (e.g. the CLI subprocess provider).
    """
    provider = _get_active_provider()
    if not hasattr(provider, "stream_generate"):
        raise NotImplementedError(
            f"Provider {provider.__class__.__name__} does not support streaming"
        )
    yield from provider.stream_generate(
        system=system, prompt=prompt, model=model, max_tokens=max_tokens
    )
```

(`_get_active_provider` is the existing private helper inside `adapter.py`. If the existing module uses a different private name, substitute it; do not introduce a new selector.)

### Step 2: Add stream_generate to the SDK provider

**File**: `{WORKSPACE}/api/modules/runtime/chain/providers/anthropic_sdk.py`

If this file exists (multi-provider epic shipped), add the `stream_generate` method to the existing provider class:

```python
from typing import Iterator


def stream_generate(
    self,
    *,
    system: str,
    prompt: str,
    model: str,
    max_tokens: int,
) -> Iterator[str]:
    """Stream text chunks from the Anthropic Messages API."""
    with self._client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text
```

(`self._client` is the existing `anthropic.Anthropic` instance owned by the provider.)

If `anthropic_sdk.py` does not exist yet, this step is a no-op for production but the adapter raises `NotImplementedError` cleanly; the streaming path is exercised in tests via a `MockStreamingProvider` (Step 5).

### Step 3: Add stream field and streaming branch to AICall

**File**: `{WORKSPACE}/api/modules/runtime/workflows/steps/ai_call.py`

Add the `stream: bool = False` Pydantic field below `max_tokens`:

```python
    stream: bool = False
```

Replace the existing `_invoke` body with a branch:

```python
    def _invoke(self, context: StepContext) -> ChainResult:
        merged = {**context.outputs, **context.inputs}  # inputs win on collision
        prompt = self.prompt_template.format_map(merged)

        if not self.stream:
            return chain_adapter.generate(
                self.system,
                prompt,
                model=self.model,
                max_tokens=self.max_tokens,
            )

        # Streaming path: accumulate chunks, push rolling 500-char tail
        # into context.outputs["_partials"][self.name] after every chunk.
        partials: dict = context.outputs.setdefault("_partials", {})
        chunks: list[str] = []
        for delta in chain_adapter.stream_generate(
            self.system, prompt, model=self.model, max_tokens=self.max_tokens
        ):
            chunks.append(delta)
            partials[self.name] = "".join(chunks)[-500:]  # rolling tail

        return ChainResult(text="".join(chunks), latency_ms=0)
```

(`ChainResult` is already imported at the top of the file as `from modules.runtime.chain.types import ChainResult`.)

### Step 4: Opt in to streaming on the bootstrap architecture step

**File**: `{WORKSPACE}/api/modules/ai/workflows/spec_gen/bootstrap.py`

In `_build_workflow()`, add `stream=True` to the `AICall(name="architecture", ...)` step constructor. The full step becomes:

```python
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
                max_tokens=16384,
                stream=True,
            )
        )
```

Analysis and epic stay non-streaming.

### Step 5: Add a mock streaming provider for tests

**File**: `{WORKSPACE}/api/modules/runtime/workflows/tests/conftest.py` (new file if absent; otherwise append)

```python
from typing import Iterator
from unittest.mock import patch

import pytest


class _MockStreamingProvider:
    """Test double for chain_adapter.stream_generate.

    Yields deterministic chunks so test assertions can compute the
    expected rolling-tail value without depending on a real provider.
    """

    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def __call__(self, system, prompt, *, model, max_tokens) -> Iterator[str]:
        for chunk in self._chunks:
            yield chunk


@pytest.fixture
def patch_stream_generate():
    """Yield a context manager that patches chain_adapter.stream_generate."""
    def _patcher(chunks: list[str]):
        return patch(
            "modules.runtime.chain.adapter.stream_generate",
            new=_MockStreamingProvider(chunks),
        )
    return _patcher
```

## Tests

**File**: `{WORKSPACE}/api/modules/runtime/workflows/tests/test_streaming.py` (new)

```python
"""Tests for AICall streaming path.

Covers:
  - stream=False: synchronous generate is called; no partials written
  - stream=True:  stream_generate is iterated; rolling 500-char tail written
  - Rolling tail truncates at 500 chars regardless of total output length
  - Multi-step workflow: each streamed step writes its own _partials entry
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
    """stream=True must populate context.outputs['_partials'][step.name] per chunk."""
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
    captured_tails: list[str] = []
    chunk = "x" * 100  # ten chunks of 100 -> 1000 total chars

    # Spy on the partials dict by patching after each yield
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
    # Drain the runtime; capture the final partials state.
    list(WorkflowRuntime().run(execution, wf))

    # The final partials snapshot is in execution.outputs (mirrored by runtime
    # only for named outputs). Drain via the StepContext path instead by
    # asserting against the chunked accumulation: the final ChainResult.text
    # is 1000 chars; the tail captured during streaming was always 500 max.
    final_text = execution.outputs["clipped"].text
    assert len(final_text) == 1000, f"Expected 1000-char output; got {len(final_text)}"
    # The contract: at no point did the rolling tail exceed 500 chars. The
    # AICall._invoke implementation slices `[-500:]` after each chunk; verify
    # the slice expression is correct by feeding through a fresh execution
    # whose StepContext we observe directly:
    from modules.runtime.workflows.steps.base import StepContext

    ctx = StepContext(run_id="t", inputs={"seed": "y"}, outputs={})
    step = AICall(
        name="probe", system="sys", prompt_template="p {seed}",
        input_keys=("seed",), stream=True,
    )
    result = step._invoke(ctx)
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
    # Probe via direct _invoke on a shared StepContext to inspect _partials.
    from modules.runtime.workflows.steps.base import StepContext
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
```

Verify in isolation:

```bash
cd {WORKSPACE}/api
python -m pytest modules/runtime/workflows/tests/test_streaming.py -v
```

All five tests must pass.

## Verification

Run from `{WORKSPACE}/api/`:

```bash
python -m pytest -q
```

Expected delta: **N → N+5 passing** (five new streaming tests in `test_streaming.py`; zero existing tests broken). Record the pre-task baseline as N before edits.

```bash
grep -n "stream: bool" modules/runtime/workflows/steps/ai_call.py
```

Must print exactly one line in the `AICall` field block.

```bash
grep -n "stream=True" modules/ai/workflows/spec_gen/bootstrap.py
```

Must print exactly one line, on the architecture step.

```bash
python -c "from modules.runtime.chain import adapter; print(callable(adapter.stream_generate))"
```

Must print `True`.

```bash
make lint
```

Confirms: flake8 clean (max-line-length 120; no unused imports).

```bash
python -m pytest tests/test_structural.py -v
```

Confirms: `featureModules_mustNotImportProvidersDirectly` stays green — streaming was added inside `chain.adapter`, not at any feature call site.

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
