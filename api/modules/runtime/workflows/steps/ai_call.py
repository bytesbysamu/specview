"""AICall — concrete Step that wraps a single chain_adapter.generate() call.

AICall absorbs the chain-primitive epic: ChainStep becomes AICall here.
``ChainStep`` must not be introduced as a separate artefact.

Prompt construction
-------------------
``prompt_template`` is a str.format_map template.  At _invoke time the merged
dict ``{**context.outputs, **context.inputs}`` is substituted — inputs win on
key collision so workflow callers can override prior step outputs explicitly
when needed. Only ``context.inputs`` and ``context.outputs`` keys are in
scope; no arithmetic, no eval.

Value-object semantics
----------------------
AICall is a frozen Pydantic model.  Two AICall instances with the same field
values compare equal and hash equal (suitable for use as dict keys / set members).
"""
from __future__ import annotations

from modules.runtime.chain import adapter as chain_adapter
from modules.runtime.chain.types import ChainResult

from .base import AbstractStep, StepContext


class AICall(AbstractStep):
    """Frozen value object: one ``chain_adapter.generate()`` invocation.

    Fields
    ------
    name              Step identity string; must be unique within a Workflow.
                      Inherited from AbstractStep (Pydantic field, kwarg-only).
    system            Static system prompt — no template substitution applied.
    prompt_template   User prompt template; ``{key}`` placeholders are resolved
                      from the merged inputs+outputs dict at execution time.
    input_keys        Workflow-level inputs the step depends on — keys that
                      must exist in ``context.inputs`` before the step runs.
                      Backs ``required_inputs`` for validation. Defaults to
                      empty (no validation).
                      NOTE: List ONLY workflow-level inputs here, not prior
                      step outputs. Prior outputs flow via ``prompt_template``
                      substitution (the merged ``{**outputs, **inputs}`` dict)
                      and are not subject to ``required_inputs`` validation —
                      listing an output key here will fail validation since
                      ``required_inputs`` is checked against ``context.inputs``
                      only, not ``context.outputs``.
    model             Provider model identifier.  Defaults to the adapter's
                      ``DEFAULT_MODEL`` constant so callers need not hard-code it.
    max_tokens        Provider token ceiling.
    stream            Per-step opt-in to streaming. Default ``False`` keeps the
                      synchronous ``chain_adapter.generate`` path (matches the
                      non-stream tests verbatim). When ``True`` the step calls
                      ``chain_adapter.stream_generate``, accumulates chunks,
                      and writes a rolling 500-char tail to
                      ``context.outputs["_partials"][self.name]`` after every
                      chunk so a polling consumer (Rel-T4) can surface live
                      progress without a second HTTP transport.
    """

    system: str
    prompt_template: str
    input_keys: tuple[str, ...] = ()
    model: str = chain_adapter.DEFAULT_MODEL
    max_tokens: int = 4096
    stream: bool = False

    @property
    def required_inputs(self) -> frozenset[str]:
        return frozenset(self.input_keys)

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

        # Streaming path: accumulate chunks, push the rolling 500-char tail
        # into context.outputs["_partials"][self.name] after every chunk so a
        # polling consumer (Rel-T4) can read live progress. If the caller
        # placed a callable under context.inputs["_partial_callback"], invoke
        # it with the same tail per chunk so push-style consumers (e.g. SSE
        # later) need not re-read the dict. Callback is OPTIONAL — the
        # default no-op keeps existing call sites unchanged.
        partials: dict = context.outputs.setdefault("_partials", {})
        partial_callback = context.inputs.get("_partial_callback") or (lambda *_a, **_k: None)
        chunks: list[str] = []
        for delta in chain_adapter.stream_generate(
            self.system,
            prompt,
            model=self.model,
            max_tokens=self.max_tokens,
        ):
            chunks.append(delta)
            tail = "".join(chunks)[-500:]  # rolling 500-char window
            partials[self.name] = tail
            partial_callback(self.name, tail)

        return ChainResult(text="".join(chunks), latency_ms=0)
