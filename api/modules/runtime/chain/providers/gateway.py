"""oll-model gateway provider — route the model call through the frozen
model-call relay (model.oll.am) instead of a direct Anthropic SDK call.

Same provider contract as ``claude.py`` (``create_message`` / ``stream_message`` /
``stream_generate``), so the chain adapter selects it with no call-site changes.
The HTTP discipline (one boundary module, single auth header, explicit timeout,
``raise_for_status``, narrowed return) is lifted from oll-am's
``services/write/text_client.py`` — the rule moves with the call.

The gateway is identity-free + internal-only: specview authenticates the user
itself; here we send only the shared ``X-Service-Token``. The gateway owns the
provider switch ("any model, pay once" — default Groq): when ``provider`` /
``model`` are omitted the gateway applies its configured default, so the default
call still sends only ``messages``. When the caller DOES target a specific
provider/model (e.g. a local Ollama model), those fields are forwarded — added to
the payload ONLY when non-None, mirroring oll-am's ``text_client.complete``.
Token counts come back in the response body and thread into ``ChainResult``
exactly like the SDK path.

Env:
  OLL_MODEL_BASE_URL       base URL of the gateway (e.g. http://oll-model:5003)
  OLL_MODEL_SERVICE_TOKEN  shared secret sent as X-Service-Token
"""
from __future__ import annotations

import logging
import os

import requests

from ..errors import ProviderError

logger = logging.getLogger(__name__)

_TIMEOUT = 65.0


def _base_url() -> str:
    return (os.environ.get("OLL_MODEL_BASE_URL") or "").rstrip("/")


def _service_token() -> str:
    return os.environ.get("OLL_MODEL_SERVICE_TOKEN", "")


def _post(
    messages: list[dict], *, provider: str | None = None, model: str | None = None
) -> dict:
    """POST messages to the gateway's /api/text/complete; return the parsed body.

    ``provider`` / ``model`` are optional per-call targeting overrides — added to
    the JSON body ONLY when non-None, so the default call sends just ``messages``
    and the gateway applies its own configured default. This conditional-key
    build mirrors oll-am's ``text_client.complete`` (the same gateway client on
    the product side).

    Maps every failure to ProviderError (never leaks a raw stack or a gateway
    5xx straight through) — mirroring claude.py's error contract so the chain
    adapter handles all providers identically.
    """
    base = _base_url()
    if not base:
        raise ProviderError("Model gateway not configured (OLL_MODEL_BASE_URL).", 502)
    payload: dict = {"messages": messages}
    if provider is not None:
        payload["provider"] = provider
    if model is not None:
        payload["model"] = model
    try:
        resp = requests.post(
            f"{base}/api/text/complete",
            headers={"X-Service-Token": _service_token()},
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        logger.error("gateway timeout base=%s", base)
        raise ProviderError("AI service timed out. Please try again.", 504)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", 502)
        logger.error("gateway http_error status=%s base=%s", status, base)
        raise ProviderError("AI service error. Please try again.", 503 if status == 503 else 502)
    except requests.RequestException:
        logger.error("gateway connection_failed base=%s", base, exc_info=True)
        raise ProviderError("Cannot connect to AI service. Please try again.", 502)


def create_message(
    system: str,
    prompt: str,
    *,
    model: str | None = None,
    provider: str | None = None,
    max_tokens: int = 4096,
) -> tuple[str, int | None, int | None]:
    """Single-shot relay. Returns ``(text, input_tokens, output_tokens)``.

    ``model`` / ``provider`` are optional targeting overrides. When omitted
    (None) nothing is sent and the gateway applies its own configured default
    (Groq) — the "any model, pay once" behaviour. When set, they're forwarded so
    the caller can target a specific provider/model (e.g. a local Ollama model).
    Token counts may be null when a backend doesn't report usage; the adapter
    tolerates that.
    """
    data = _post(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        provider=provider,
        model=model,
    )
    text = (data.get("text") or "").strip()
    if not text:
        raise ProviderError("AI service returned no output. Please try again.", 502)
    return text, data.get("tokens_in"), data.get("tokens_out")


def stream_message(
    system: str,
    prompt: str,
    *,
    model: str | None = None,
    provider: str | None = None,
    max_tokens: int = 4096,
):
    """The gateway's /complete is single-shot, so streaming degrades to one
    chunk — the full text yielded once. Keeps the streaming call-path working
    without the gateway needing a streaming endpoint."""
    text, _, _ = create_message(
        system, prompt, model=model, provider=provider, max_tokens=max_tokens
    )
    yield text


def stream_generate(
    *,
    system: str,
    prompt: str,
    model: str | None = None,
    provider: str | None = None,
    max_tokens: int = 4096,
):
    """Match claude.py's stream_generate surface (keyword-only) for the adapter."""
    yield from stream_message(
        system, prompt, model=model, provider=provider, max_tokens=max_tokens
    )
