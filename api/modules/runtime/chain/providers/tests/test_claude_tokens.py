"""Verify the SDK provider surfaces input/output tokens on the success path.

These tests pin the contract that ``claude.create_message`` returns a
3-tuple ``(text, input_tokens, output_tokens)`` so the chain adapter can
populate ``ChainResult.tokens_in`` / ``ChainResult.tokens_out`` for the
cost accumulator (Task 3). Error paths still raise ``ProviderError``
without returning a partial tuple.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.runtime.chain.providers import claude


def test_createMessage_returnsTextAndTokenCounts(monkeypatch):
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(text="hello world")],
        usage=SimpleNamespace(input_tokens=42, output_tokens=17),
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(claude, "_make_client", lambda: fake_client)

    text, tokens_in, tokens_out = claude.create_message(
        "system", "prompt", model="claude-sonnet-4-5", max_tokens=128
    )

    assert text == "hello world"
    assert tokens_in == 42
    assert tokens_out == 17
    fake_client.messages.create.assert_called_once_with(
        model="claude-sonnet-4-5",
        max_tokens=128,
        system="system",
        messages=[{"role": "user", "content": "prompt"}],
    )


def test_createMessage_rateLimitStillRaisesProviderError(monkeypatch):
    from anthropic import RateLimitError

    from modules.runtime.chain.errors import ProviderError

    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.status_code = 429
    fake_response.headers = {}
    fake_response.request = MagicMock()
    fake_client.messages.create.side_effect = RateLimitError(
        message="busy", response=fake_response, body=None
    )
    monkeypatch.setattr(claude, "_make_client", lambda: fake_client)

    with pytest.raises(ProviderError) as excinfo:
        claude.create_message("s", "p", model="claude-sonnet-4-5", max_tokens=128)

    # ProviderError uses ``status_code`` (see modules/runtime/chain/errors.py).
    assert excinfo.value.status_code == 503
    assert "AI service" in excinfo.value.message
