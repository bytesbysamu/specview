"""Claude provider — ported verbatim from references.md:107–176.

The Anthropic client is created lazily per-call (rather than at module import)
so test infrastructure can redirect SDK HTTP traffic via
``monkeypatch.setenv("ANTHROPIC_BASE_URL", ...)`` without ``importlib.reload``.
"""
from __future__ import annotations

import logging
import os

from anthropic import Anthropic, APIConnectionError, APIError, RateLimitError

from ..errors import ProviderError

logger = logging.getLogger(__name__)


def _make_client() -> Anthropic:
    """Create a fresh Anthropic client per call.

    Reads ``ANTHROPIC_BASE_URL`` at call time so test fixtures using
    ``monkeypatch.setenv`` can redirect SDK HTTP traffic to a stub server
    without forcing a module reload.
    """
    kwargs: dict = {"timeout": 60.0, "max_retries": 2}
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return Anthropic(**kwargs)


def create_message(
    system: str, prompt: str, *, model: str, max_tokens: int = 4096
) -> tuple[str, int | None, int | None]:
    """Single-shot SDK call. Returns ``(text, input_tokens, output_tokens)``.

    Token counts come straight off ``response.usage`` (anthropic SDK >=0.40
    field names ``input_tokens`` / ``output_tokens``). Caller is the chain
    adapter, which threads the numbers into ``ChainResult`` so the cost
    accumulator can read them. Error paths raise ``ProviderError`` and never
    return a partial tuple — token accounting only happens on success.
    """
    client = _make_client()
    try:
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        return text, input_tokens, output_tokens
    except RateLimitError:
        logger.warning("claude rate_limit model=%s", model)
        raise ProviderError("AI service is busy. Please try again in a moment.", 503)
    except APIConnectionError:
        logger.error("claude connection_failed model=%s", model, exc_info=True)
        raise ProviderError("Cannot connect to AI service. Please try again.", 502)
    except APIError as e:
        logger.error("claude api_error model=%s", model, exc_info=True)
        raise ProviderError(f"AI service error: {e.message}", 502)


def stream_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096):
    client = _make_client()
    try:
        with client.messages.stream(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                yield text
    except RateLimitError:
        logger.warning("claude stream rate_limit model=%s", model)
        yield "\n\n[Error: AI service is busy. Please try again.]"
    except APIConnectionError:
        logger.error("claude stream connection_failed model=%s", model, exc_info=True)
        yield "\n\n[Error: Cannot connect to AI service.]"
    except APIError as e:
        logger.error("claude stream api_error model=%s", model, exc_info=True)
        yield f"\n\n[Error: {e.message}]"


def stream_generate(*, system: str, prompt: str, model: str, max_tokens: int = 4096):
    """Stream text chunks from the Anthropic Messages API.

    Counterpart to :func:`create_message` for the streaming path. Errors are
    raised as :class:`ProviderError` (matching ``create_message`` semantics)
    rather than yielded inline as fake chunks — the AICall streaming branch
    relies on exceptions to halt the step and surface ``StepFailed``.
    """
    client = _make_client()
    try:
        with client.messages.stream(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                yield text
    except RateLimitError:
        logger.warning("claude stream_generate rate_limit model=%s", model)
        raise ProviderError("AI service is busy. Please try again in a moment.", 503)
    except APIConnectionError:
        logger.error("claude stream_generate connection_failed model=%s", model, exc_info=True)
        raise ProviderError("Cannot connect to AI service. Please try again.", 502)
    except APIError as e:
        logger.error("claude stream_generate api_error model=%s", model, exc_info=True)
        raise ProviderError(f"AI service error: {e.message}", 502)
