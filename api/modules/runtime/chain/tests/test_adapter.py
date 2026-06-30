"""Adapter tests — generate, stream, provider selection, usage accumulator."""
import threading

import pytest
from modules.runtime.chain import adapter as _adapter
from modules.runtime.chain import adapter
from modules.runtime.chain import providers
from modules.runtime.chain.adapter import generate, stream
from modules.runtime.chain.types import ChainResult

# Alias with no underscores avoids pytest collection under python_functions=["test_*", "*_*"]
selectProvider = _adapter._select_provider


def resetUsage() -> None:
    """Test helper: clear the module-level accumulator. Lock-protected."""
    with _adapter._USAGE_LOCK:
        _adapter._USAGE["calls"] = 0
        _adapter._USAGE["input_tokens"] = 0
        _adapter._USAGE["output_tokens"] = 0
        _adapter._USAGE["by_model"].clear()


def mockProvider_generateReturnsChainResult(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    result = generate("system", "user prompt")
    # Mock returns valid JSON; verify the ChainResult wraps it correctly.
    import json
    parsed = json.loads(result.text)
    assert "text" in parsed, f"expected 'text' key in mock JSON: {result.text}"
    assert result.latency_ms >= 0
    # Mock provider has no usage data — tokens stay None so the cost
    # accumulator treats this call as zero-cost.
    assert result.tokens_in is None
    assert result.tokens_out is None


def customModel_generatePassesModelToProvider(monkeypatch):
    """generate() forwards the model param to create_message."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    captured = {}

    def spy(system, prompt, *, model="mock", max_tokens=4096):
        captured["model"] = model
        from modules.runtime.chain.providers.mock import _MOCK_PAYLOAD
        return _MOCK_PAYLOAD, None, None

    monkeypatch.setattr(providers.mock, "create_message", spy)
    generate("sys", "p", model="custom-model")
    assert captured["model"] == "custom-model"


def builderContext_generatePrependsToSystem(monkeypatch):
    """with_context injects builder text before the system prompt."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    captured = {}

    def spy(system, prompt, *, model="mock", max_tokens=4096):
        captured["system"] = system
        from modules.runtime.chain.providers.mock import _MOCK_PAYLOAD
        return _MOCK_PAYLOAD, None, None

    monkeypatch.setattr(providers.mock, "create_message", spy)
    generate("base", "p", builder="BuilderText")
    assert "BUILDER" in captured["system"], f"builder not in system: {captured['system']}"


def principles_generatePrependsToSystem(monkeypatch):
    """with_context injects principles text before the system prompt."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    captured = {}

    def spy(system, prompt, *, model="mock", max_tokens=4096):
        captured["system"] = system
        from modules.runtime.chain.providers.mock import _MOCK_PAYLOAD
        return _MOCK_PAYLOAD, None, None

    monkeypatch.setattr(providers.mock, "create_message", spy)
    generate("sys", "p", principles="Keep it short")
    assert "PRINCIPL" in captured["system"], f"principles not in system: {captured['system']}"


def mockProvider_streamYieldsChunks(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    chunks = list(stream("sys", "p"))
    assert len(chunks) >= 1, f"expected at least 1 chunk, got {len(chunks)}"
    full = "".join(chunks)
    import json
    parsed = json.loads(full)
    assert "text" in parsed, f"expected 'text' key in streamed mock JSON: {full}"


def unknownProvider_selectProviderRaisesValueError(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "nonexistent")
    with pytest.raises(ValueError, match="nonexistent"):
        selectProvider()


def chainResult_isImmutable(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    result = generate("sys", "p")
    with pytest.raises((AttributeError, TypeError)):
        result.text = "mutation attempt"  # type: ignore[misc]


def test_resolve_provider_uses_explicit_chain_provider(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
    assert adapter._resolve_provider_name() == "mock"


def test_resolve_provider_picks_claude_when_api_key_present(monkeypatch):
    monkeypatch.delenv("CHAIN_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
    assert adapter._resolve_provider_name() == "claude"


def test_resolve_provider_falls_back_to_cli_without_key(monkeypatch):
    monkeypatch.delenv("CHAIN_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert adapter._resolve_provider_name() == "cli"


def test_anthropic_alias_resolves_to_claude_provider(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "anthropic")
    selected = adapter._select_provider()
    assert selected is providers.claude


def test_unknown_chain_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "openai")
    with pytest.raises(ValueError) as excinfo:
        adapter._select_provider()
    assert "openai" in str(excinfo.value)


# ── Usage accumulator (Task 3 — SaaS Anthropic SDK Provider) ──────────────


def recordUsage_accumulatesTokensAcrossCalls():
    resetUsage()
    r = ChainResult(text="ok", latency_ms=1, tokens_in=100, tokens_out=20)
    _adapter._record_usage("claude-sonnet-4-5", r)
    _adapter._record_usage("claude-sonnet-4-5", r)
    summary = _adapter.get_usage_summary()
    assert summary["calls"] == 2
    assert summary["input_tokens"] == 200
    assert summary["output_tokens"] == 40
    # 200/1e6 * 3 + 40/1e6 * 15 = 0.0006 + 0.0006 = 0.0012
    assert summary["cost_usd"] == 0.0012


def getUsageSummary_usesPerModelPricing():
    resetUsage()
    _adapter._record_usage(
        "claude-haiku-4-5",
        ChainResult(text="x", latency_ms=1, tokens_in=1_000_000, tokens_out=0),
    )
    _adapter._record_usage(
        "claude-opus-4-7",
        ChainResult(text="x", latency_ms=1, tokens_in=0, tokens_out=1_000_000),
    )
    summary = _adapter.get_usage_summary()
    # haiku in: 1e6/1e6 * 0.80 = 0.80
    # opus  out: 1e6/1e6 * 75.00 = 75.00
    assert summary["cost_usd"] == 75.80
    assert summary["calls"] == 2


def recordUsage_handlesNoneTokensFromCliProvider():
    resetUsage()
    r = ChainResult(text="cli result", latency_ms=1, tokens_in=None, tokens_out=None)
    _adapter._record_usage("claude-sonnet-4-5", r)
    summary = _adapter.get_usage_summary()
    assert summary["calls"] == 1
    assert summary["input_tokens"] == 0
    assert summary["output_tokens"] == 0
    assert summary["cost_usd"] == 0.0


def recordUsage_unknownModelDoesNotCrash():
    resetUsage()
    r = ChainResult(text="x", latency_ms=1, tokens_in=10, tokens_out=10)
    _adapter._record_usage("claude-future-99", r)
    summary = _adapter.get_usage_summary()
    assert summary["calls"] == 1
    # Unknown-model pricing is (0, 0) — usage logged, cost contribution 0.
    assert summary["cost_usd"] == 0.0


def recordUsage_isThreadSafeSmoke():
    resetUsage()

    def worker():
        for _ in range(100):
            _adapter._record_usage(
                "claude-sonnet-4-5",
                ChainResult(text="x", latency_ms=1, tokens_in=1, tokens_out=1),
            )

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summary = _adapter.get_usage_summary()
    assert summary["calls"] == 800
    assert summary["input_tokens"] == 800
    assert summary["output_tokens"] == 800


def generate_recordsUsageAfterEverySuccessfulCall(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    resetUsage()
    generate("sys", "prompt")
    generate("sys", "prompt")
    summary = _adapter.get_usage_summary()
    # Mock provider returns no token counts yet (T1 not cherry-picked) but
    # the call counter still advances every time — proves the wiring.
    assert summary["calls"] == 2


def getUsageSummary_includesResolvedProviderName(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    resetUsage()
    summary = _adapter.get_usage_summary()
    assert summary["provider"] == "mock"


# ── Model / provider forwarding through to the oll-model gateway ───────────


def gatewayCaptureJson(monkeypatch):
    """Route the adapter at the gateway provider and capture the POSTed JSON."""
    import requests
    monkeypatch.setenv("CHAIN_PROVIDER", "gateway")
    monkeypatch.setenv("OLL_MODEL_BASE_URL", "http://oll-model:5003")
    captured = {}

    def fake_post(url, headers, json, timeout):  # noqa: A002
        captured.update(json=json)
        resp = type("R", (), {})()
        resp.raise_for_status = lambda: None
        resp.json = lambda: {"text": "ok"}
        return resp

    monkeypatch.setattr(requests, "post", fake_post)
    return captured


def generate_defaultProvider_omitsProviderFromGatewayPayload(monkeypatch):
    """No provider override -> the gateway payload carries no provider key
    (default path is unchanged; the gateway picks its own provider)."""
    captured = gatewayCaptureJson(monkeypatch)
    resetUsage()
    generate("sys", "p")
    assert "provider" not in captured["json"]


def generate_forwardsModelAndProvider_toGatewayPayload(monkeypatch):
    """generate(model=..., provider=...) reaches the gateway /api/text/complete
    body — proving the chain adapter forwards both end to end."""
    captured = gatewayCaptureJson(monkeypatch)
    resetUsage()
    generate("sys", "p", model="llama3.2", provider="ollama")
    assert captured["json"]["model"] == "llama3.2"
    assert captured["json"]["provider"] == "ollama"


# ── Gateway-only guard: a provider override is SAFE on non-gateway backends ──
# Only the gateway provider's create_message accepts a `provider` kwarg;
# claude/cli/mock do NOT. Passing `provider=` while the active backend is one of
# those must NOT raise TypeError -> 500; the adapter drops the meaningless
# override instead.


def providerOverride_onNonGatewayBackend_doesNotCrash_andIsDropped(monkeypatch):
    """generate(provider=...) with a non-gateway active provider (mock) must not
    TypeError — the adapter drops the override rather than forwarding a kwarg the
    mock provider can't accept."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    captured = {}

    # Spy with the REAL mock signature — no `provider` kwarg. If the adapter
    # forwarded provider= here, this call would TypeError.
    def spy(system, prompt, *, model="mock", max_tokens=4096):
        captured["model"] = model
        captured["called"] = True
        from modules.runtime.chain.providers.mock import _MOCK_PAYLOAD
        return _MOCK_PAYLOAD, None, None

    monkeypatch.setattr(providers.mock, "create_message", spy)
    resetUsage()
    # Would raise TypeError before the guard; must succeed now.
    result = generate("sys", "p", provider="ollama")
    assert captured["called"] is True
    assert result.latency_ms >= 0


def providerKwarg_dropsOverride_whenActiveIsNotGateway():
    """Unit-level: _provider_kwarg honours provider only for the gateway module."""
    # Non-gateway active provider -> override dropped (empty kwargs).
    assert adapter._provider_kwarg("ollama", providers.mock) == {}
    assert adapter._provider_kwarg("ollama", providers.claude) == {}
    # Gateway active provider -> override forwarded.
    assert adapter._provider_kwarg("ollama", providers.gateway) == {"provider": "ollama"}
    # No override requested -> always empty, regardless of backend.
    assert adapter._provider_kwarg(None, providers.gateway) == {}
    assert adapter._provider_kwarg(None, providers.mock) == {}


def defaultPath_onNonGatewayBackend_unchanged_noProviderKwarg(monkeypatch):
    """Omitting provider on a non-gateway backend is byte-for-byte unchanged:
    create_message is called with no provider kwarg."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    seen = {}

    def spy(system, prompt, *, model="mock", max_tokens=4096, **extra):
        seen["extra"] = extra
        from modules.runtime.chain.providers.mock import _MOCK_PAYLOAD
        return _MOCK_PAYLOAD, None, None

    monkeypatch.setattr(providers.mock, "create_message", spy)
    resetUsage()
    generate("sys", "p")
    assert seen["extra"] == {}  # no provider kwarg leaked on the default path
