# Task 1 — Surface SDK Token Usage on ChainResult

**Effort**: 0.3 days

## 1. Context

`runtime/chain/providers/claude.py` already calls the Anthropic SDK and returns the assistant's text, but it discards `response.usage.input_tokens` and `response.usage.output_tokens`. The `ChainResult` dataclass already declares `tokens_in` / `tokens_out` (currently always `None`), so the fields exist but never carry real numbers. Until the SDK provider populates them, the cost accumulator (Task 3) has nothing to read and `/api/ai/stats` (Task 3) cannot return a non-zero `cost_usd`.

This task widens the SDK provider so `create_message` returns `(text, input_tokens, output_tokens)` and threads those numbers through the adapter into `ChainResult`. CLI and mock providers continue to return `(text, None, None)` because they cannot observe token usage — `cost_usd` for those calls stays at zero, which is the right answer.

The change is local to `runtime/chain/`. No feature module is touched. No DTO drifts. The structural test that pins the adapter boundary continues to pass.

---

## 2. Pre-flight

```bash
# Working tree is clean on api/modules/runtime/chain/
git status -- api/modules/runtime/chain/

# Baseline test count — record this number; all later steps reference the delta
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
```

If the working tree is dirty under `api/modules/runtime/chain/`, stash unrelated changes before starting. The recorded test count is the baseline `N` — every later success criterion is expressed as `N → N+K passing`.

---

## 3. Files

### To Modify

- `{WORKSPACE}/api/modules/runtime/chain/providers/claude.py` — widen `create_message` return signature; widen `stream_message` so the final yield optionally carries usage when SDK exposes it
- `{WORKSPACE}/api/modules/runtime/chain/providers/cli.py` — match new return signature, returning `(text, None, None)`
- `{WORKSPACE}/api/modules/runtime/chain/providers/mock.py` — match new return signature, returning `(text, None, None)`
- `{WORKSPACE}/api/modules/runtime/chain/adapter.py` — unpack the tuple from each provider call and populate `ChainResult.tokens_in` / `ChainResult.tokens_out`
- `{WORKSPACE}/api/modules/runtime/chain/tests/test_adapter.py` — extend existing tests to assert tokens flow through; add one new test for the SDK happy path with mocked SDK response

### To Create (new)

- `{WORKSPACE}/api/modules/runtime/chain/providers/tests/__init__.py` (new) — empty package marker if not already present
- `{WORKSPACE}/api/modules/runtime/chain/providers/tests/test_claude_tokens.py` (new) — unit test that mocks the Anthropic SDK and asserts the provider returns `(text, input_tokens, output_tokens)` correctly

### To Leave Alone

- `{WORKSPACE}/api/modules/runtime/chain/types.py` — `ChainResult.tokens_in` / `tokens_out` already declared as `Optional[int] = None`; no schema change
- `{WORKSPACE}/api/modules/ai/**` — no feature-side changes; the new tokens are populated upstream of the adapter boundary
- `{WORKSPACE}/api/openapi.yaml` — no contract change; tokens are an internal `ChainResult` concern, not exposed over HTTP yet (Task 3 exposes the aggregate)

---

## 4. Implementation Steps

### Step 1: Update SDK provider to return token usage

**Action**: Change `create_message` to return `(text, input_tokens, output_tokens)`. Pull the usage off `response.usage` after the SDK call succeeds. On error paths, the provider raises (no return) — token accounting only happens on success.

**File**: `{WORKSPACE}/api/modules/runtime/chain/providers/claude.py`

**Pattern** (apply inside the `try` block of `create_message`, after `response = client.messages.create(...)`):

```python
def create_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096):
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
```

`stream_message` keeps yielding text deltas as today; do not block on usage in the streaming path (deferred per architecture's "What This System Does NOT Include").

---

### Step 2: Update CLI and mock providers to match the wider signature

**Action**: Both providers return a 3-tuple; tokens are `None` because neither has access to usage data.

**File**: `{WORKSPACE}/api/modules/runtime/chain/providers/cli.py`

**Pattern** (locate the existing `def create_message(...)` and change the return statement):

```python
def create_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096):
    # ... existing subprocess invocation unchanged ...
    return text, None, None
```

**File**: `{WORKSPACE}/api/modules/runtime/chain/providers/mock.py`

**Pattern**:

```python
def create_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096):
    # ... existing canned text construction unchanged ...
    return text, None, None
```

---

### Step 3: Unpack tokens in the adapter

**Action**: `adapter.generate` and `adapter.rewrite` currently call `provider.create_message(...)` and bind the return to `text`. Bind to a 3-tuple instead, and pass the tokens to `ChainResult`.

**File**: `{WORKSPACE}/api/modules/runtime/chain/adapter.py`

**Pattern** (replace the `text = provider.create_message(...)` lines):

```python
def generate(system, prompt, *, builder="", principles="", model=DEFAULT_MODEL, max_tokens=4096):
    effective_system = with_context(system, builder=builder, principles=principles)
    provider = _select_provider()
    t0 = time.monotonic()
    text, tokens_in, tokens_out = provider.create_message(
        effective_system, prompt, model=model, max_tokens=max_tokens
    )
    result = ChainResult(
        text=text,
        latency_ms=int((time.monotonic() - t0) * 1000),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    logger.info("generate provider=%s latency_ms=%d", provider.__name__, result.latency_ms)
    return result
```

Apply the same change to `rewrite`. `stream` is unchanged in this task — it already yields strings; aggregate token reporting from streams is out of scope.

---

### Step 4: Update existing adapter tests for the new tuple shape

**Action**: Any test that does `monkeypatch.setattr(providers.<x>, "create_message", lambda ...: "fake")` must now return a 3-tuple. Search and update.

**File**: `{WORKSPACE}/api/modules/runtime/chain/tests/test_adapter.py`

**Pattern** (search for monkeypatched provider stubs and rewrite them):

```python
def test_generate_returns_chain_result(monkeypatch):
    monkeypatch.setattr(
        "modules.runtime.chain.providers.cli.create_message",
        lambda system, prompt, *, model, max_tokens: ("hello", None, None),
    )
    result = adapter.generate("sys", "user")
    assert result.text == "hello"
    assert result.tokens_in is None
    assert result.tokens_out is None
    assert result.latency_ms >= 0
```

Add the assertions on `tokens_in is None` and `tokens_out is None` to every existing CLI/mock-backed test. They are part of the contract.

---

### Step 5: New SDK provider test for token surfacing

**Action**: Mock the `Anthropic` client, return a fake `Message` whose `.usage.input_tokens=42` and `.usage.output_tokens=17`, assert the provider returns `("text", 42, 17)`.

**File**: `{WORKSPACE}/api/modules/runtime/chain/providers/tests/test_claude_tokens.py` **(new)**

```python
"""Verify the SDK provider surfaces input/output tokens on the success path."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.runtime.chain.providers import claude


def test_create_message_returns_text_and_token_counts(monkeypatch):
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


def test_create_message_rate_limit_still_raises_provider_error(monkeypatch):
    from anthropic import RateLimitError
    from modules.runtime.chain.errors import ProviderError

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RateLimitError(
        message="busy", response=MagicMock(status_code=429), body=None
    )
    monkeypatch.setattr(claude, "_make_client", lambda: fake_client)

    with pytest.raises(ProviderError) as excinfo:
        claude.create_message("s", "p", model="claude-sonnet-4-5", max_tokens=128)

    assert excinfo.value.status == 503
    assert "busy" in str(excinfo.value).lower() or "AI service" in str(excinfo.value)
```

---

## 5. Tests

Run the focused suite first to keep iteration fast, then the full suite to confirm no regressions outside `runtime/chain/`.

```bash
cd {WORKSPACE}/api && python -m pytest modules/runtime/chain/ -q
cd {WORKSPACE}/api && python -m pytest -q
```

**Expected delta**: `N → N+2 passing` (the two new tests in `test_claude_tokens.py`); zero pre-existing tests broken; one already-existing skip remains skipped.

If any test under `modules/runtime/chain/tests/` fails with a tuple-unpacking error, Step 2 missed a provider — re-grep for `def create_message` under `providers/` and confirm all three return 3-tuples.

---

## 6. Commit Plan

This task is one focused commit.

```bash
cd {WORKSPACE}
git add api/modules/runtime/chain/providers/claude.py \
        api/modules/runtime/chain/providers/cli.py \
        api/modules/runtime/chain/providers/mock.py \
        api/modules/runtime/chain/adapter.py \
        api/modules/runtime/chain/tests/test_adapter.py \
        api/modules/runtime/chain/providers/tests/__init__.py \
        api/modules/runtime/chain/providers/tests/test_claude_tokens.py

git commit -m "$(cat <<'EOF'
feat(chain): surface SDK token usage on ChainResult

The Anthropic SDK provider now returns (text, input_tokens, output_tokens);
adapter populates ChainResult.tokens_in/tokens_out so Task 3's cost
accumulator has real numbers to read. CLI and mock providers return
(text, None, None) — accumulator handles None as zero-cost.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: `N → N+2 passing`; one pre-existing skip preserved.

Manual sanity check (only on a dev box that has the SDK key):

```bash
cd {WORKSPACE}/api && CHAIN_PROVIDER=claude python -c "
from modules.runtime.chain import adapter
r = adapter.generate('You are concise.', 'Say hi in two words.')
print('text=', r.text); print('tokens_in=', r.tokens_in); print('tokens_out=', r.tokens_out)
assert r.tokens_in and r.tokens_in > 0
assert r.tokens_out and r.tokens_out > 0
"
```

Skip the manual check in CI; it requires a network call.

---

## 8. Rollback

```bash
git revert <sha-of-this-task>
```

The revert restores the prior `text`-only return type. No DTO regeneration is required (no openapi change). No data migration is required (no persistence). Other capabilities are unaffected because `tokens_in`/`tokens_out` were already optional.

---

## 9. Deviations Allowed

- **SDK response shape varies between Anthropic library versions**: if `response.usage` has different field names (e.g., `prompt_tokens` instead of `input_tokens`), check the installed `anthropic` version against `requirements.txt`, use the names that exist, and add a comment naming the version. Do not pin a new `anthropic` version in this task — pinning belongs in its own commit.
- **Existing CLI provider already returns text plus latency in some forks**: if its current return shape is unexpectedly `(text, latency)` rather than `text`, apply the 3-tuple shape `(text, None, None)` and drop the latency from the return — latency is computed in the adapter, not in providers.
- **Stream usage**: the brain dump notes stream usage arrives at end-of-stream; if you find the SDK's `text_stream` sibling that yields usage, do NOT add it in this task — it belongs to a streaming-cost capability not yet scoped.

---

## 10. Out of Scope

- Cost accumulator and `/api/ai/stats` endpoint — Task 3
- Adapter auto-detection on `ANTHROPIC_API_KEY` — Task 2
- Per-step model routing in workflow definitions — Task 4
- Production startup gate in `create_app.py` — Task 5
- Streaming token accounting — deferred entirely (architecture exclusion)
- Per-user / per-tenant attribution — usage-metering capability owns this

---

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
