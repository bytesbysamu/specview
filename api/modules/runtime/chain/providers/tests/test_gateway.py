"""Verify the oll-model gateway provider: it posts messages to the gateway,
returns ``(text, tokens_in, tokens_out)``, sends the service token, forwards
``model`` / ``provider`` ONLY when targeted (omitted on the default path so the
gateway applies its own default), and maps failures to ProviderError.

The HTTP boundary (``requests.post``) is mocked — no real network call.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from modules.runtime.chain.errors import ProviderError
from modules.runtime.chain.providers import gateway


def okResponse(body: dict):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = body
    return resp


def test_createMessage_postsMessagesAndReturnsTextAndTokens(monkeypatch):
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    monkeypatch.setenv("OLL_MODEL_SERVICE_TOKEN", "tok-123")
    captured = {}

    def fake_post(url, headers, json, timeout):  # noqa: A002 — mirror requests.post kwargs
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return okResponse({"text": "  a gateway rewrite  ", "provider": "groq",
                             "model": "llama-3.3-70b-versatile", "tokens_in": 9, "tokens_out": 13})

    monkeypatch.setattr(requests, "post", fake_post)

    text, tin, tout = gateway.create_message("be terse", "fix this")

    assert text == "a gateway rewrite"  # trimmed
    assert (tin, tout) == (9, 13)
    assert captured["url"].endswith("/api/text/complete")
    assert captured["headers"]["X-Service-Token"] == "tok-123"
    assert [m["role"] for m in captured["json"]["messages"]] == ["system", "user"]


def test_createMessage_omitsModelAndProvider_whenNotTargeted(monkeypatch):
    """Default path: no model/provider given -> payload carries ONLY messages,
    so the gateway applies its own configured default ("any model, pay once")."""
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    captured = {}

    def fake_post(url, headers, json, timeout):  # noqa: A002
        captured.update(json=json)
        return okResponse({"text": "ok"})

    monkeypatch.setattr(requests, "post", fake_post)

    gateway.create_message("s", "p")

    assert set(captured["json"]) == {"messages"}  # only messages, nothing else


def test_createMessage_forwardsModelAndProvider_whenTargeted(monkeypatch):
    """Targeting a specific provider/model (e.g. local Ollama) forwards both
    fields in the POSTed JSON so the gateway routes to them."""
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    captured = {}

    def fake_post(url, headers, json, timeout):  # noqa: A002
        captured.update(json=json)
        return okResponse({"text": "ok"})

    monkeypatch.setattr(requests, "post", fake_post)

    gateway.create_message("s", "p", provider="ollama", model="llama3.2")

    assert captured["json"]["provider"] == "ollama"
    assert captured["json"]["model"] == "llama3.2"
    assert [m["role"] for m in captured["json"]["messages"]] == ["system", "user"]


def test_createMessage_tolerates_null_tokens(monkeypatch):
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    monkeypatch.setattr(requests, "post", lambda *a, **k: okResponse({"text": "ok"}))
    text, tin, tout = gateway.create_message("s", "p", model="m")
    assert text == "ok" and tin is None and tout is None


def test_unconfigured_base_url_raises_providererror(monkeypatch):
    monkeypatch.delenv("OLL_MODEL_BASE_URL", raising=False)
    with pytest.raises(ProviderError):
        gateway.create_message("s", "p", model="m")


def test_empty_output_raises_providererror(monkeypatch):
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    monkeypatch.setattr(requests, "post", lambda *a, **k: okResponse({"text": "   "}))
    with pytest.raises(ProviderError):
        gateway.create_message("s", "p", model="m")


def test_transport_failure_raises_providererror(monkeypatch):
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")

    def boom(*a, **k):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(ProviderError):
        gateway.create_message("s", "p", model="m")


def test_stream_message_yields_full_text(monkeypatch):
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    monkeypatch.setattr(requests, "post", lambda *a, **k: okResponse({"text": "streamed once"}))
    chunks = list(gateway.stream_message("s", "p", model="m"))
    assert chunks == ["streamed once"]
