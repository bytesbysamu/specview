"""AI call adapter — ELA Pattern #1. Sole import for AI operations.

Adapted from references.md:583–620. Spec-doc change: no user objects.
builder and principles are plain strings loaded by context_loader or passed directly.

INVARIANT: Feature modules import ONLY from this file. Never from providers.*.
Enforced by test_structural.py.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Iterator

from . import providers
from .context import with_context
from .types import ChainResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-6"


def _resolve_provider_name() -> str:
    """Return the provider name to use given the current environment.

    Precedence:
      1. CHAIN_PROVIDER explicitly set -> use it as-is.
      2. OLL_MODEL_BASE_URL present -> "gateway" (route the model call through the
         frozen oll-model gateway: "any model, pay once", keyless).
      3. ANTHROPIC_API_KEY present -> "claude" (SDK, direct).
      4. Otherwise -> "cli" (uses Claude Code credential file / keychain).
    """
    explicit = os.environ.get("CHAIN_PROVIDER")
    if explicit:
        return explicit
    if os.environ.get("OLL_MODEL_BASE_URL"):
        return "gateway"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return "cli"


def _select_provider():
    """Select provider module based on CHAIN_PROVIDER env var.

    Accepts ``"anthropic"`` as an alias for ``"claude"`` so the brain dump's
    naming and the existing module name both work.
    """
    name = _resolve_provider_name()
    mapping = {
        "claude": providers.claude,
        "anthropic": providers.claude,  # alias - brain dump uses this name
        "gateway": providers.gateway,
        "cli": providers.cli,
        "mock": providers.mock,
    }
    if name not in mapping:
        raise ValueError(
            f"Unknown CHAIN_PROVIDER={name!r}; expected one of "
            f"{sorted(set(mapping))}"
        )
    return mapping[name]


# In-process org-wide AI usage accumulator. Resets on process restart.
# ELA #7 — single consumer (the /api/ai/stats route), no Redis, no DB.
_USAGE_LOCK = threading.Lock()
_USAGE: dict = {
    "calls": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    # Per-model cumulative totals so cost can be recomputed if pricing changes.
    "by_model": {},  # model_id -> {"input_tokens": int, "output_tokens": int}
}

# Per-million-token pricing in USD. Hard-coded; revisit when Anthropic
# changes prices. Keep in sync with the model ids referenced in
# modules/ai/workflows/* AICall steps.
_PRICING: dict = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5":  (0.80, 4.00),
    "claude-opus-4-6":   (15.00, 75.00),
    "claude-opus-4-7":   (15.00, 75.00),
}

# Used when a model id has no entry in _PRICING — usage is still recorded,
# cost contribution is zero rather than a crash.
_UNKNOWN_MODEL_PRICING = (0.0, 0.0)


def _record_usage(model: str, result: ChainResult) -> None:
    """Add this result's tokens to the org-wide accumulator. Lock-protected.

    Open seam (Task 1): providers do not yet populate ``tokens_in`` /
    ``tokens_out`` on ChainResult, so until T1 lands these contribute zero
    cost. The ``or 0`` defaults keep the accumulator math correct in the
    interim.
    """
    with _USAGE_LOCK:
        _USAGE["calls"] += 1
        _USAGE["input_tokens"] += result.tokens_in or 0
        _USAGE["output_tokens"] += result.tokens_out or 0
        bucket = _USAGE["by_model"].setdefault(
            model, {"input_tokens": 0, "output_tokens": 0}
        )
        bucket["input_tokens"] += result.tokens_in or 0
        bucket["output_tokens"] += result.tokens_out or 0


def get_usage_summary() -> dict:
    """Return a snapshot of cumulative usage. Cost is computed from _PRICING."""
    with _USAGE_LOCK:
        cost_usd = 0.0
        for model_id, totals in _USAGE["by_model"].items():
            in_rate, out_rate = _PRICING.get(model_id, _UNKNOWN_MODEL_PRICING)
            cost_usd += totals["input_tokens"] / 1_000_000 * in_rate
            cost_usd += totals["output_tokens"] / 1_000_000 * out_rate
        return {
            "calls": _USAGE["calls"],
            "input_tokens": _USAGE["input_tokens"],
            "output_tokens": _USAGE["output_tokens"],
            "cost_usd": round(cost_usd, 4),
            "provider": _resolve_provider_name(),
        }


def _get_active_provider():
    """Return the currently selected provider module/object.

    Thin alias over ``_select_provider`` so streaming-aware callers (and the
    structural test that monkeypatches the active provider) have a stable
    name decoupled from the env-var selection mechanism.
    """
    return _select_provider()


def _provider_kwarg(provider: str | None, active) -> dict:
    """Build the optional ``provider=`` kwarg for a call on the ``active`` provider.

    Returned empty when no provider override is requested, so the kwarg is never
    passed on the default path — keeping every existing provider call site
    untouched.

    GATEWAY-ONLY GUARD: only the oll-model gateway provider's ``create_message`` /
    ``stream_*`` accept a ``provider`` kwarg; ``claude`` / ``cli`` / ``mock`` do
    NOT, so forwarding ``provider`` to them would raise ``TypeError`` -> 500. The
    override is also meaningless for those backends (they speak to a single model
    family). So when the active provider is not the gateway we DROP the override
    (logged once) rather than crash — the active backend's own model is used.
    This keeps a ``provider=`` argument safe to pass regardless of which backend
    ``CHAIN_PROVIDER`` selects.
    """
    if provider is None:
        return {}
    if active is not providers.gateway:
        logger.warning(
            "provider override %r ignored: active provider %s does not support a "
            "provider switch (only the oll-model gateway does)",
            provider, getattr(active, "__name__", active),
        )
        return {}
    return {"provider": provider}


def generate(
    system: str,
    prompt: str,
    *,
    builder: str = "",
    principles: str = "",
    model: str = DEFAULT_MODEL,
    provider: str | None = None,
    max_tokens: int = 4096,
) -> ChainResult:
    """Single-shot AI completion. Returns ChainResult with text, latency, tokens.

    ``model`` / ``provider`` are forwarded to the active provider; the oll-model
    gateway relays them onward only when set (default path is unchanged).
    """
    effective_system = with_context(system, builder=builder, principles=principles)
    active = _select_provider()
    t0 = time.monotonic()
    text, tokens_in, tokens_out = active.create_message(
        effective_system, prompt, model=model, max_tokens=max_tokens,
        **_provider_kwarg(provider, active),
    )
    result = ChainResult(
        text=text,
        latency_ms=int((time.monotonic() - t0) * 1000),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    logger.info("generate provider=%s latency_ms=%d", active.__name__, result.latency_ms)
    _record_usage(model, result)
    return result


def rewrite(
    system: str,
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    provider: str | None = None,
    max_tokens: int = 4096,
) -> ChainResult:
    """Instruction-driven text rewrite. No context injection — rewrite is caller-driven.

    Contrast with generate(), which prepends builder/principles via with_context().
    """
    active = _select_provider()
    t0 = time.monotonic()
    text, tokens_in, tokens_out = active.create_message(
        system, prompt, model=model, max_tokens=max_tokens,
        **_provider_kwarg(provider, active),
    )
    result = ChainResult(
        text=text,
        latency_ms=int((time.monotonic() - t0) * 1000),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    logger.info("rewrite provider=%s latency_ms=%d", active.__name__, result.latency_ms)
    _record_usage(model, result)
    return result


def stream(
    system: str,
    prompt: str,
    *,
    builder: str = "",
    principles: str = "",
    model: str = DEFAULT_MODEL,
    provider: str | None = None,
    max_tokens: int = 4096,
) -> Iterator[str]:
    """Streaming AI completion. Yields text chunks."""
    effective_system = with_context(system, builder=builder, principles=principles)
    active = _select_provider()
    yield from active.stream_message(
        effective_system, prompt, model=model, max_tokens=max_tokens,
        **_provider_kwarg(provider, active),
    )


def stream_generate(
    system: str,
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    provider: str | None = None,
    max_tokens: int = 4096,
) -> Iterator[str]:
    """Yield text chunks from the active provider's streaming endpoint.

    Counterpart to :func:`generate` for the streaming case. ``AICall(stream=True)``
    is the named consumer (see ``modules/runtime/workflows/steps/ai_call.py``).
    Unlike :func:`stream`, this function does NOT inject ``builder`` /
    ``principles`` context — workflow steps already pass a fully-formed system
    prompt (the architecture step composes its own context up-front).

    Raises
    ------
    NotImplementedError
        If the active provider does not implement ``stream_generate`` (the
        CLI subprocess provider is dev-only and never streams).
    """
    active = _get_active_provider()
    if not hasattr(active, "stream_generate"):
        raise NotImplementedError(
            f"Provider {getattr(active, '__name__', type(active).__name__)} "
            f"does not support streaming"
        )
    yield from active.stream_generate(
        system=system, prompt=prompt, model=model, max_tokens=max_tokens,
        **_provider_kwarg(provider, active),
    )
