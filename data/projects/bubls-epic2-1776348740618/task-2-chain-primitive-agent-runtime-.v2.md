# 🛠️ Task 2: Chain primitive (`server/modules/chain/`)

**Purpose**: Port humanize-me's Claude wrapper + spec-doc's adapter-boundary context injection into a minimal, reusable chain module that Task 3 (spec) and Task 6 (photoshoot retrofit) consume.

**Effort**: 3 days

**Dependencies**: Task 1 (user model with `builder` + `principles` JSONB) — context injection reads those columns. If Task 1 is incomplete, this task can still ship against a stubbed `User` shape and wire up real reads when Task 1 lands.

**Parallel With**: Task 4 (spec frontend) can begin against the mock provider before Task 3 backend is ready.

**Blocks**: Task 3 (spec module), Task 6 (photoshoot retrofit).

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Bubls needs one place where AI feature pipelines run — builder/principles injected once, providers swapped by strategy, mocks first-class for tests. The architecture doc sketched a declarative `ChainDefinition` / `ChainStep` / `ChainEvent` design with `chain_call` + `chain_signal` tables, retry/backoff, and SSE event streaming. The reference-code block then explicitly walks that back to a ~200-line port of humanize-me's `claude.py` plus a `sequential(steps, initial)` helper, with no declarative types, no new DB tables, no retry machinery beyond the Anthropic SDK's built-ins. We follow the reference-code budget. Chains become *code* (a list of callables), not data; logging goes to Python's `logging` module until real cost-attribution signal demands a table; signal capture is deferred to the task that first needs it (Task 3's `/api/spec/signal` route). This keeps Task 2's surface area small enough that Task 6 can retrofit photoshoot without swimming against premature abstractions.

**Trade-offs considered**:
- **Full declarative `ChainDefinition` + `chain_call`/`chain_signal` tables** (per architecture.md) — rejected: the reference-code port budget explicitly forbids it ("Zero declarative types for chain definitions", "Zero new DB tables"), and Task 6 is the validation that a two-chain primitive is even warranted. Shipping a declarative abstraction of one chain is the anti-pattern the reference calls out.
- **Async `AsyncIterator[ChainEvent]` from day one** (per epic text) — rejected: humanize-me's working port uses synchronous generators yielding strings with `Response(generator(), content_type=...)` for streaming. That shape is sufficient for Task 3's SSE route; async gives us nothing until concurrent calls matter.
- **Port verbatim from humanize-me + add `with_context` helper** (chosen) — preferred because the Python is already production-tested, the port is <200 lines, and `spec-doc/server.js:26-313` gives us the exact adapter-boundary context-prepending shape to mirror.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/bubls
git status                                           # flag unrelated M/?? entries
git log -1 --format='%H' > /tmp/bubls-pretask-sha    # rollback anchor
cd server && python -m pytest -q 2>&1 | tail -5      # baseline pass count
grep -r "agent_runtime\|modules/chain" --include="*.py" . || echo "clean"
grep "^anthropic" requirements.txt || echo "anthropic NOT pinned — Step 1 will add"
```

**If `git status` shows unrelated dirty files on the target paths** (`server/modules/chain/**`, `server/requirements.txt`, `server/app.py`): stash or commit them separately before starting.

**Baseline recorded**: [write the pytest pass count from the command above into the first commit body].

---

## 3. Files

### To Create (new)
- `server/modules/chain/__init__.py` — package marker + re-exports (`generate`, `stream`, `sequential`, `run_chain`, `with_context`, `ChainResult`, `ProviderError`)
- `server/modules/chain/adapter.py` — **ELA Adapter pattern boundary**. `generate(system, prompt, *, user, feature, model, max_tokens) -> ChainResult` + `stream(...)`. Provider selected via `CHAIN_PROVIDER` env flag (default `"claude"`, `"mock"` in tests). Calls `with_context` internally so context injection happens **once at the boundary**, never at the call site. Feature modules import from here — NEVER from `providers.*` directly.
- `server/modules/chain/types.py` — `ChainResult` frozen dataclass (`text`, `latency_ms`, `tokens_in | None`, `tokens_out | None`). Anti-Corruption Layer (ELA pattern #5): the domain-level return type, so callers never depend on a specific provider's response shape.
- `server/modules/chain/runner.py` — `sequential(steps, initial)` generator; `run_chain(steps, user, initial)` convenience wrapper that delegates to `sequential`. Each `step` is a callable receiving the prior step's output — step bodies call `adapter.generate(...)`, NOT provider functions directly.
- `server/modules/chain/context.py` — `with_context(system, builder, principles_slice) -> str`; formatters for builder dict + principles dict. Used internally by `adapter.py`; feature modules should not call it directly (all context injection goes through the adapter).
- `server/modules/chain/providers/__init__.py` — package marker
- `server/modules/chain/providers/claude.py` — `create_message` + `stream_message` ported verbatim from `humanize-me/backend/services/claude.py` with `model` lifted to an argument
- `server/modules/chain/providers/mock.py` — deterministic `create_message` / `stream_message` returning a fixture string that echoes inputs; selected via `CHAIN_PROVIDER=mock` env flag
- `server/modules/chain/errors.py` — `ProviderError(Exception)` with `status_code` attribute, ported from humanize-me's `ServiceError`
- `server/modules/chain/tests/__init__.py` — package marker
- `server/modules/chain/tests/conftest.py` — pytest fixture that sets `CHAIN_PROVIDER=mock` and clears it after
- `server/modules/chain/tests/test_adapter.py` — tests for `generate`/`stream`: provider selection, context injection at boundary, `ChainResult` shape, no direct provider access leaking through
- `server/modules/chain/tests/test_runner.py` — tests for `sequential` + `run_chain`
- `server/modules/chain/tests/test_context.py` — tests for `with_context` + formatters
- `server/modules/chain/tests/test_providers.py` — tests for mock provider; Claude provider covered by one integration test skipped-by-default unless `ANTHROPIC_API_KEY` is set

### To Modify (cite codebase.md)
- `server/requirements.txt` — add `anthropic>=0.39.0` if not already present. **Verify with** `grep '^anthropic' server/requirements.txt` (Pre-flight step above)
- *Nothing else.* `server/app.py` is **not** modified — chain is an internal library, not a Flask blueprint, so it has no place in `ENABLED_MODULES`

### To Leave Alone
- `server/modules/photoshoot/**` — retrofit is Task 6; leaving it untouched keeps Task 2 free of cross-feature coupling
- `server/app.py` / `server/core/**` — no registration, no config changes; chain is consumed, not registered
- `server/modules/user/**` — Task 1 owns the `builder` / `principles` columns; Task 2 only *reads* whatever Task 1 lands, via duck-typing on `user.builder` / `user.principles.get('<feature>')`
- `src/app/**` (Angular) — zero frontend work in Task 2

---

## 4. Implementation Steps

**Hard Rule for every step below**: feature modules (`modules/spec/**`, `modules/photoshoot/**`, future modules) MUST import chain functionality through `modules.chain.adapter` and nothing else. Direct imports of `modules.chain.providers.*` from feature code are forbidden — that's the ELA Pattern #1 (Adapter) invariant. Inside the chain module itself, `adapter.py` is the single consumer of `providers.*`; runner/context are adapter-adjacent. Violations appear as `from modules.chain.providers.claude import create_message` showing up anywhere outside `modules/chain/adapter.py` or `modules/chain/tests/`.

### Step 1: Scaffold package + pin Anthropic SDK

**Action**: Create the empty package tree and ensure `anthropic` is pinned in requirements.

**File**: `server/modules/chain/__init__.py`, `server/modules/chain/providers/__init__.py`, `server/modules/chain/tests/__init__.py` (all new); `server/requirements.txt` (modify only if `anthropic` is missing).

**Pattern**:
```python
# server/modules/chain/__init__.py
from .adapter import generate, stream
from .runner import sequential, run_chain
from .types import ChainResult
from .errors import ProviderError
# NOTE: with_context is intentionally NOT re-exported. Feature modules must
# not call it directly — all context injection goes through the adapter.

__all__ = [
    "generate",
    "stream",
    "sequential",
    "run_chain",
    "ChainResult",
    "ProviderError",
]
```

**Verify**: `cd server && python -c "import modules.chain"` — exits 0 after Steps 2–4 land.

### Step 2: Port the Claude provider verbatim

**Action**: Port `humanize-me/backend/services/claude.py` (lines 1–54 of the REFERENCE CODE block), lifting the `model` constant to a function argument so the provider is feature-agnostic. Split `ServiceError` out into `errors.py` as `ProviderError`.

**File**: `server/modules/chain/providers/claude.py` (new), `server/modules/chain/errors.py` (new). Source: `humanize-me/backend/services/claude.py:1-54` (see REFERENCE CODE).

**Pattern** (port shape — match the REFERENCE CODE line-for-line except for the `model` parameter and the renamed error class):
```python
# server/modules/chain/providers/claude.py
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from ..errors import ProviderError

_client = Anthropic(timeout=60.0, max_retries=2)

def create_message(system: str, prompt: str, model: str, max_tokens: int = 4096) -> str:
    try:
        response = _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except RateLimitError:
        raise ProviderError("AI service is busy. Please try again in a moment.", 503)
    except APIConnectionError:
        raise ProviderError("Cannot connect to AI service. Please try again.", 502)
    except APIError as e:
        raise ProviderError(f"AI service error: {e.message}", 502)

def stream_message(system: str, prompt: str, model: str, max_tokens: int = 4096):
    try:
        with _client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                yield text
    except RateLimitError:
        yield "\n\n[Error: AI service is busy. Please try again.]"
    except APIConnectionError:
        yield "\n\n[Error: Cannot connect to AI service.]"
    except APIError as e:
        yield f"\n\n[Error: {e.message}]"
```

```python
# server/modules/chain/errors.py
class ProviderError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
```

**Verify**: `cd server && python -c "from modules.chain.providers.claude import create_message, stream_message"` — exits 0.

### Step 3: Write the mock provider

**Action**: Create a deterministic `create_message` / `stream_message` that echoes `model` + the first 40 chars of the prompt. The mock is selected by importing from `providers.mock` directly; no global strategy registry yet (chains-are-code means the test picks the provider).

**File**: `server/modules/chain/providers/mock.py` (new).

**Pattern**:
```python
# server/modules/chain/providers/mock.py
def create_message(system: str, prompt: str, model: str = "mock", max_tokens: int = 4096) -> str:
    return f"MOCK[{model}]::sys={system[:20]}::prompt={prompt[:40]}"

def stream_message(system: str, prompt: str, model: str = "mock", max_tokens: int = 4096):
    for chunk in ("MOCK[", model, "]::", prompt[:40]):
        yield chunk
```

**Verify**: `cd server && python -c "from modules.chain.providers.mock import create_message; print(create_message('s','p','m'))"` prints `MOCK[m]::sys=s::prompt=p`.

### Step 4: Port the `sequential` helper + thin `run_chain` wrapper

**Action**: Port the `sequential(steps, initial)` generator from the REFERENCE CODE "Suggested port" block verbatim. Add a `run_chain(steps, user, initial)` convenience that calls `with_context` (Step 5) on each step's system prompt before dispatching. Chains are lists of plain callables — no `ChainDefinition` class, no `ChainStep` enum, no `ChainEvent` tagged union.

**File**: `server/modules/chain/runner.py` (new). Source: REFERENCE CODE "Suggested port as a generalized helper" block.

**Pattern**:
```python
# server/modules/chain/runner.py
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")

def sequential(
    steps: list[Callable[[T | None], T]],
    initial: T | None = None,
) -> Iterator[T]:
    """Run a list of step-callables, yielding each output as it arrives.

    Ported from humanize-me/backend/services/humanizer.py (3-pass flow)
    generalized into a variable-step helper. Each step receives the prior
    output (or ``initial`` for step 0).
    """
    prev: T | None = initial
    for step in steps:
        prev = step(prev)
        yield prev

def run_chain(
    steps: list[Callable[[T | None], T]],
    user=None,
    initial: T | None = None,
) -> Iterator[T]:
    """Convenience wrapper — steps are expected to have already bound their
    system prompt via ``with_context(system, user.builder, user.principles.get(feature))``.
    ``run_chain`` adds no magic; it exists so feature modules have one obvious entry point.
    """
    yield from sequential(steps, initial)
```

**Verify**:
```bash
cd server && python -c "
from modules.chain.runner import sequential
out = list(sequential([lambda x: (x or '') + 'a', lambda x: x + 'b'], ''))
assert out == ['a', 'ab'], out
print('ok')
"
```

### Step 5: Context helper + `ChainResult` domain type

**Action**: Port `with_context(system, builder, principles_slice)` as an **internal helper** used by the adapter (Step 6). Feature modules do NOT import `with_context` — they go through `adapter.generate` which calls it. Also define `ChainResult` (frozen dataclass) so the adapter exposes a domain-level return type rather than a raw provider `str`.

**File**: `server/modules/chain/context.py` (new), `server/modules/chain/types.py` (new). Source shape: `spec-doc/server.js:26-313` "Two invariants to preserve" (context at adapter boundary, mock selectable via flag).

**Pattern**:
```python
# server/modules/chain/context.py
from typing import Any

def _format_builder(builder: dict[str, Any]) -> str:
    lines = []
    for key, value in builder.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(str(v) for v in value)}")
        elif isinstance(value, dict):
            nested = "; ".join(f"{k}={v}" for k, v in value.items())
            lines.append(f"- {key}: {nested}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)

def _format_principles(principles: dict[str, Any]) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in principles.items())

def with_context(
    system: str,
    builder: dict[str, Any] | None = None,
    principles: dict[str, Any] | None = None,
) -> str:
    """Prepend builder + principles blocks to a system prompt. Called from
    adapter.generate/stream — feature code should NOT call this directly.
    """
    parts = [system]
    if builder:
        parts.append(f"\n\n## BUILDER CONTEXT\n{_format_builder(builder)}")
    if principles:
        parts.append(f"\n\n## PRINCIPLES\n{_format_principles(principles)}")
    return "".join(parts)
```

```python
# server/modules/chain/types.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ChainResult:
    """Domain-level result. Anti-Corruption Layer (ELA pattern #5) — providers
    may return any shape; the adapter normalizes to this. Callers read
    ``result.text`` without knowing whether Claude, Replicate, or a mock
    produced it.
    """
    text: str
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
```

**Verify**:
```bash
cd server && python -c "
from modules.chain.context import with_context
from modules.chain.types import ChainResult
out = with_context('BASE', builder={'role': 'solo'}, principles={'p1': 'x'})
assert 'BASE' in out and 'BUILDER CONTEXT' in out and 'solo' in out and 'PRINCIPLES' in out, out
assert with_context('BASE') == 'BASE', 'no-context case must pass through unchanged'
r = ChainResult(text='hi', latency_ms=10)
assert r.text == 'hi' and r.tokens_in is None
print('ok')
"
```

### Step 6: Adapter — the ELA Pattern #1 boundary

**Action**: Create `adapter.py` exposing `generate(system, prompt, *, user, feature, model, max_tokens) -> ChainResult` and `stream(...)`. This is the **only** module feature code imports for chain calls. Inside, `_select_provider()` dispatches by `CHAIN_PROVIDER` env var. Context injection happens here once — callers pass the raw system prompt + the user object, and the adapter handles `with_context(..., builder=user.builder, principles=user.principles.get(feature))`.

This closes a pattern miss the earlier draft of this task had: providers without a unifying adapter forced feature modules to couple directly to `providers.claude` (violates Adapter, violates Strategy). The amendment encodes `principles.md` "Patterns to Apply > Adapter (every feature service)": **Same interface regardless of data source.**

**File**: `server/modules/chain/adapter.py` (new). Source shape: `spec-doc/server.js:288-313` (the `aiAdapter` Strategy dispatch).

**Pattern**:
```python
# server/modules/chain/adapter.py
import os
import time
from typing import Any, Iterator

from . import providers
from .context import with_context
from .types import ChainResult

DEFAULT_MODEL = "claude-opus-4-6-20250805"


def _select_provider():
    """Provider Strategy — selection via env flag. Default Claude; mock in tests."""
    name = os.environ.get("CHAIN_PROVIDER", "claude")
    mapping = {"claude": providers.claude, "mock": providers.mock}
    if name not in mapping:
        raise ValueError(f"Unknown CHAIN_PROVIDER={name!r}; expected one of {sorted(mapping)}")
    return mapping[name]


def _effective_system(
    system: str,
    user: Any | None = None,
    feature: str | None = None,
) -> str:
    """Resolve the full system prompt — builder + principles slice prepended once."""
    builder = getattr(user, "builder", None) if user is not None else None
    principles_all = getattr(user, "principles", None) if user is not None else None
    principles_slice = (principles_all or {}).get(feature) if feature else None
    return with_context(system, builder=builder, principles=principles_slice)


def generate(
    system: str,
    prompt: str,
    *,
    user: Any | None = None,
    feature: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> ChainResult:
    """Unified entry point. Feature modules call this; NEVER import providers directly."""
    effective = _effective_system(system, user, feature)
    provider = _select_provider()
    t0 = time.monotonic()
    text = provider.create_message(effective, prompt, model=model, max_tokens=max_tokens)
    return ChainResult(text=text, latency_ms=int((time.monotonic() - t0) * 1000))


def stream(
    system: str,
    prompt: str,
    *,
    user: Any | None = None,
    feature: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> Iterator[str]:
    """Streaming variant. Yields text chunks. Same adapter-boundary invariants as `generate`."""
    effective = _effective_system(system, user, feature)
    provider = _select_provider()
    yield from provider.stream_message(effective, prompt, model=model, max_tokens=max_tokens)
```

**Verify**:
```bash
cd server && CHAIN_PROVIDER=mock python -c "
from modules.chain.adapter import generate, stream
from modules.chain.types import ChainResult
r = generate('SYS', 'PROMPT', model='x')
assert isinstance(r, ChainResult) and 'MOCK[' in r.text
assert r.latency_ms >= 0

class FakeUser:
    builder = {'role': 'solo'}
    principles = {'spec': {'p1': 'v'}}

r = generate('SYS', 'PROMPT', user=FakeUser(), feature='spec')
# effective system prompt (not returned) was extended; chunks-of-stream show it
chunks = list(stream('SYS', 'PROMPT', user=FakeUser(), feature='spec'))
assert ''.join(chunks).startswith('MOCK[')
print('ok')
"
```

### Step 7: Tests — adapter, runner, context, providers

**Action**: Write pytest tests matching the repo convention (`server/tests/test_*.py` uses plain `pytest` + in-memory SQLite per `conftest`). These tests don't touch DB, so a minimal `conftest.py` in `server/modules/chain/tests/` that forces `CHAIN_PROVIDER=mock` is enough. **The `test_adapter.py` suite is the load-bearing one** — it pins the ELA Adapter invariant (provider selection via env, context injection at boundary, ChainResult as domain type).

**File**: `server/modules/chain/tests/test_adapter.py`, `test_runner.py`, `test_context.py`, `test_providers.py`, `conftest.py` (all new). See Section 5 for full bodies.

**Verify**: `cd server && python -m pytest modules/chain/tests/ -v` — all new tests pass, zero failures in other suites.

### Step 8: Run the full suite, record delta

**Action**: Run the full server test suite and confirm baseline tests still pass + new tests are additive.

**File**: none (test execution only).

**Verify**: `cd server && python -m pytest -q` — expected delta is `baseline → baseline + ≥8` passing; zero previously-passing tests fail.

---

## 5. Tests

Repo convention: pytest with plain `assert` (per `server/tests/test_routes.py`, `test_service.py`, `test_repository.py`). No `unittest.TestCase`, no `pytest-mock` required beyond stdlib.

```python
# server/modules/chain/tests/conftest.py
import os
import pytest

@pytest.fixture(autouse=True)
def _force_mock_provider(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    yield
```

```python
# server/modules/chain/tests/test_adapter.py
# ELA Adapter pattern tests — the load-bearing contract
import os
import pytest
from modules.chain import generate, stream, ChainResult
from modules.chain import adapter as adapter_module


def test_generate_returnsChainResult_notRawString():
    r = generate("SYS", "PROMPT", model="x")
    assert isinstance(r, ChainResult), "adapter must wrap provider output in ChainResult (ACL)"
    assert isinstance(r.text, str) and len(r.text) > 0
    assert isinstance(r.latency_ms, int) and r.latency_ms >= 0


def test_generate_mockProviderSelectedByEnvFlag():
    # conftest sets CHAIN_PROVIDER=mock — verify it's respected
    r = generate("SYS", "prompt text", model="test-model")
    assert "MOCK[test-model]" in r.text


def test_generate_unknownProvider_raises(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "nonexistent-provider-xyz")
    with pytest.raises(ValueError, match="Unknown CHAIN_PROVIDER"):
        generate("SYS", "p", model="x")


def test_generate_contextInjectedAtBoundary_oncePerCall():
    """When user has builder + principles, the effective system prompt contains
    both blocks. Mock provider echoes the prompt prefix so we can inspect it."""
    class FakeUser:
        builder = {"role": "solo founder", "stack": "Flask"}
        principles = {"spec": {"p1": "always ORM"}}

    r = generate("BASE SYS", "prompt", user=FakeUser(), feature="spec", model="m")
    # Mock echoes `sys={system[:20]}` — system was extended with the context blocks
    # so the first 20 chars should still start with BASE SYS (blocks prepended after it)
    assert "sys=BASE SYS" in r.text


def test_generate_noUser_noContextInjection_systemPassesThrough():
    r = generate("BARE", "p", model="m")
    assert "sys=BARE" in r.text


def test_generate_userWithoutPrinciplesForFeature_onlyBuilderInjected():
    class FakeUser:
        builder = {"role": "solo"}
        principles = {"other_feature": {"x": 1}}

    # Should not crash on the missing feature slice
    r = generate("S", "p", user=FakeUser(), feature="spec", model="m")
    assert "MOCK[" in r.text


def test_stream_yieldsChunks_fromMockProvider():
    chunks = list(stream("S", "p", model="m"))
    assert len(chunks) >= 2, "stream must yield multiple chunks"
    assert "".join(chunks).startswith("MOCK[m]")


def test_stream_respectsProviderSelection():
    chunks = list(stream("S", "p", model="test"))
    joined = "".join(chunks)
    assert "test" in joined, "selected provider's model argument must reach the stream output"


def test_featureModules_mustNotImportProvidersDirectly():
    """Structural invariant: adapter.py is the ONLY module inside chain/ that
    imports from providers/*. This test greps the package tree.

    If this test fails, someone bypassed the adapter boundary — revert that
    import and route through `from modules.chain import generate/stream`."""
    import pathlib
    chain_dir = pathlib.Path(adapter_module.__file__).parent
    offenders = []
    for py in chain_dir.rglob("*.py"):
        rel = py.relative_to(chain_dir)
        # adapter.py + providers/* + tests/* are allowed to touch providers
        if rel.parts[0] in ("providers", "tests") or rel.name == "adapter.py":
            continue
        text = py.read_text()
        if "from .providers" in text or "from modules.chain.providers" in text:
            offenders.append(str(rel))
    assert offenders == [], (
        f"adapter-boundary violation: files inside modules/chain/ imported "
        f"from providers directly: {offenders}. Only adapter.py may. See Section 4."
    )
```

```python
# server/modules/chain/tests/test_runner.py
from modules.chain.runner import sequential, run_chain

def test_sequential_emptySteps_yieldsNothing():
    assert list(sequential([], initial="seed")) == []

def test_sequential_singleStep_yieldsOneOutput():
    out = list(sequential([lambda x: (x or "") + "A"], initial=""))
    assert out == ["A"]

def test_sequential_threeSteps_forwardsEachOutputToNext():
    steps = [
        lambda x: (x or "") + "1",
        lambda x: x + "2",
        lambda x: x + "3",
    ]
    assert list(sequential(steps, initial="")) == ["1", "12", "123"]

def test_sequential_initialNone_firstStepReceivesNone():
    received = []
    def step(x):
        received.append(x)
        return "out"
    list(sequential([step]))
    assert received == [None]

def test_runChain_delegatesToSequential_sameOutput():
    steps = [lambda x: (x or "") + "a", lambda x: x + "b"]
    assert list(run_chain(steps, user=None, initial="")) == ["a", "ab"]

def test_sequential_stepRaises_propagatesException():
    import pytest
    def boom(_):
        raise RuntimeError("step failed")
    with pytest.raises(RuntimeError, match="step failed"):
        list(sequential([boom], initial=""))
```

```python
# server/modules/chain/tests/test_context.py
from modules.chain.context import with_context

def test_withContext_noBuilderNoPrinciples_returnsSystemUnchanged():
    assert with_context("BASE") == "BASE"

def test_withContext_builderOnly_prependsBuilderBlock():
    out = with_context("BASE", builder={"role": "solo founder", "stack": "Flask"})
    assert out.startswith("BASE")
    assert "## BUILDER CONTEXT" in out
    assert "role: solo founder" in out
    assert "stack: Flask" in out
    assert "## PRINCIPLES" not in out

def test_withContext_principlesOnly_prependsPrinciplesBlock():
    out = with_context("BASE", principles={"p1": "always use ORM"})
    assert "## PRINCIPLES" in out
    assert "p1: always use ORM" in out
    assert "## BUILDER CONTEXT" not in out

def test_withContext_both_builderBeforePrinciples():
    out = with_context("BASE", builder={"k": "v"}, principles={"p": "q"})
    assert out.index("## BUILDER CONTEXT") < out.index("## PRINCIPLES")

def test_withContext_builderListValue_formatsAsCommaJoined():
    out = with_context("BASE", builder={"langs": ["Python", "TypeScript"]})
    assert "langs: Python, TypeScript" in out

def test_withContext_emptyDicts_treatedAsAbsent():
    assert with_context("BASE", builder={}, principles={}) == "BASE"
```

```python
# server/modules/chain/tests/test_providers.py
import os
import pytest
from modules.chain.providers import mock as mock_provider

def test_mock_createMessage_echoesModelAndPromptPrefix():
    out = mock_provider.create_message("system prompt", "user prompt text", model="test-model")
    assert "MOCK[test-model]" in out
    assert "user prompt text"[:40] in out

def test_mock_streamMessage_yieldsChunks():
    chunks = list(mock_provider.stream_message("sys", "prompt abc", model="m"))
    assert len(chunks) >= 2
    assert "".join(chunks).startswith("MOCK[m]")

def test_mock_createMessage_defaultModelIsMock():
    out = mock_provider.create_message("s", "p")
    assert "MOCK[mock]" in out

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live Claude integration — requires ANTHROPIC_API_KEY",
)
def test_claude_createMessage_returnsNonEmptyString():
    from modules.chain.providers import claude as claude_provider
    out = claude_provider.create_message(
        system="Reply with exactly: OK",
        prompt="ping",
        model="claude-haiku-4-5-20251001",
        max_tokens=16,
    )
    assert isinstance(out, str) and len(out) > 0
```

---

## 6. Commit Plan

One commit per logical unit. Conventional-commits style matching recent repo history.

1. `feat(chain): scaffold module + port ProviderError + ChainResult type` — `server/modules/chain/__init__.py`, `server/modules/chain/errors.py`, `server/modules/chain/types.py`, `server/modules/chain/providers/__init__.py`, `server/modules/chain/tests/__init__.py`, `server/modules/chain/tests/conftest.py`, `server/requirements.txt` (if anthropic pin added): empty package tree + error class + domain return type + SDK pinned.
2. `feat(chain): port Claude + mock providers from humanize-me` — `server/modules/chain/providers/claude.py`, `server/modules/chain/providers/mock.py`: model-as-argument port of `humanize-me/backend/services/claude.py`; deterministic mock for tests.
3. `feat(chain): sequential runner + context helper` — `server/modules/chain/runner.py`, `server/modules/chain/context.py`: `sequential`/`run_chain` + `with_context` for builder+principles prepending (internal helper; called from adapter, not features).
4. `feat(chain): adapter boundary — ELA Pattern #1 (Adapter)` — `server/modules/chain/adapter.py`: `generate`/`stream` unified interface, provider selected via `CHAIN_PROVIDER` env flag, context injection at the boundary, returns `ChainResult`. **This is the module feature code will import** — providers.* stays internal.
5. `test(chain): cover adapter boundary, runner, context, and mock provider` — `server/modules/chain/tests/test_adapter.py`, `test_runner.py`, `test_context.py`, `test_providers.py`: full assertion bodies; Claude live test skipped unless key present. `test_adapter.py` includes the structural "no feature imports providers directly" check.

**Deviation logging**: if any step is skipped or merged (e.g., you land `requirements.txt` because `anthropic` was already pinned — no change, no commit), prefix the next commit's body with `Deviations:` and one line explaining.

---

## 7. Verification

```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -m pytest -q
python -c "from modules.chain import generate, stream, sequential, run_chain, ChainResult, ProviderError; print('exports ok')"
```

**Expected delta**: baseline → baseline + **≥24** passing (9 adapter + 6 runner + 6 context + 3 mock-provider, minimum). Claude live test remains skipped by default.

**Zero pre-existing tests broken** — if any previously-green test in `server/tests/` fails, STOP and investigate before committing.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` in reverse order (commit 4 → 1). Reverting commit 3 before commit 4 leaves the test module importing non-existent symbols; revert tests first.
- **Per-branch**: `git reset --hard $(cat /tmp/bubls-pretask-sha)` restores the pre-task anchor recorded in Pre-flight. If the branch is ephemeral, deleting it is equivalent: `git checkout main && git branch -D <task-branch>`.
- **Dependency rollback**: if `server/requirements.txt` was modified and the anthropic pin causes conflicts, revert that file specifically — the rest of the module still imports (import is lazy until `providers.claude` is touched).

---

## 9. Deviations Allowed

- **`anthropic` already pinned** → skip the `requirements.txt` edit and note in commit 1's body (`Deviations: anthropic already pinned at <version>, no req change`).
- **Test framework mismatch** — if `server/tests/` turns out to use `unittest.TestCase` (contradicting current codebase.md signal) → translate the assertion bodies to `self.assert*` silently but note in the test-commit body.
- **`CHAIN_PROVIDER` env flag is load-bearing — do NOT delete.** It's how `adapter._select_provider()` chooses between Claude and mock. Tests rely on it (conftest sets `CHAIN_PROVIDER=mock`); production leaves it unset so the default `"claude"` branch is taken. This is the ELA Strategy pattern's selector — removing it collapses the adapter back to direct provider coupling.
- **`user.builder` / `user.principles` schema uncertain** — adapter duck-types: `_effective_system` uses `getattr(user, "builder", None)` and `(getattr(user, "principles", None) or {}).get(feature)`. If Task 1 lands a typed `BuilderProfile` SQLModel, the adapter still works (SQLAlchemy dicts satisfy the duck-typed access). No changes to `adapter.py` or `context.py` required.
- **Missing `anthropic` SDK during local test run** — mock provider has zero imports from `anthropic`. Live Claude test is already `@pytest.mark.skipif`-guarded. Running `pytest modules/chain/tests/` without the SDK installed is acceptable as a fast path; `pip install anthropic` required only for the live-key path.
- **Reality vs. architecture.md (declarative types, `chain_call`/`chain_signal` tables, SSE `ChainEvent` union, retry/backoff)** — these are **deliberately out of scope per the reference-code port budget**. See Section 10. If the executor feels compelled to add any of them, **STOP and flag — do not absorb.**

---

## 10. Out of Scope

Task 2 ships a ~240-line port of humanize-me's Claude wrapper plus a `sequential` helper, an `adapter.py` boundary (ELA Pattern #1), and a minimal `ChainResult` domain type (ELA Pattern #5). It does not ship the declarative chain-definition machinery, persistence layer, or event-streaming types that `architecture.md` describes — those are deferred because (a) the reference-code "Port budget" explicitly forbids them at this stage, (b) Task 6 (photoshoot retrofit) is the validation that a two-chain primitive is even warranted, and (c) shipping an abstraction of one chain is the premature-generalization anti-pattern the builder principles call out.

- **`ChainDefinition` / `ChainStep` / `ChainEvent` declarative types** — deferred indefinitely; chains are code (lists of callables). `ChainResult` is the ONE declarative type this task ships because it's the Anti-Corruption Layer between providers and domain code — nothing more. Revisit the bigger declarative surface only if Task 6 produces genuine duplication that a shared type would eliminate.
- **`chain_call` + `chain_signal` tables + `capture_signal()` endpoint** — deferred to Task 3 or Epic 3; Task 3's `POST /api/spec/signal` is the first place that actually needs signal persistence, so the schema belongs with *that* task's migration, not Task 2's.
- **Per-call cost/latency logging to DB** — deferred; use `logging.getLogger("chain").info(...)` in a future step if debugging requires it. Retrofitting a log table once real cost signal exists is cheap.
- **Retry + exponential backoff machinery** — deferred; the Anthropic SDK's built-in `max_retries=2` + `timeout=60.0` (already in the port source) cover transient faults. Custom backoff waits until a provider that lacks SDK retries is introduced (Replicate, OpenAI).
- **`providers/replicate.py`** — deferred; Task 6 (photoshoot retrofit) ports the existing Replicate client into this folder. Task 2 only ships Claude + mock because Task 3 only needs Claude.
- **SSE wire format** — deferred; Task 3's route will wrap `sequential(...)` output in `Response(generator(), content_type="text/event-stream")` and format each yielded item as an SSE event. Task 2 yields plain strings/outputs — the route layer is the encoder.
- **Async / `AsyncIterator`** — deferred; synchronous generators are sufficient for SSE per the humanize-me port (`backend/app.py:182-241`). Async is a rewrite that happens when concurrency demands it.
- **Provider Protocol / registered plugin system** — deferred. This task ships a two-element dict lookup (`{"claude": providers.claude, "mock": providers.mock}`) inside `adapter._select_provider`. A formal `Protocol` class + discovery mechanism lands when a third provider exists (likely Replicate in Task 6) AND the dict grows unwieldy (more than ~5 entries).

**Rule for the executor**: if a change appears helpful but is listed above, STOP and surface it as a deviation — do not silently expand this task's blast radius. The port budget is load-bearing.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale (note: this task deliberately simplifies vs. the architecture's declarative design; see Section 1 Trade-offs)
- [Epic](./epic.md) — Task 2 scope
- [Timeline](./timeline.md) — update status to Done after Verification (Section 7) passes