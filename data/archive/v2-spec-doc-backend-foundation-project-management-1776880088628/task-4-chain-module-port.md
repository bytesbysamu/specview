Now I have all the context I need. Let me write the guide.

# Task 4: Chain Module Port — Implementation Guide

**Purpose**: Port the AI call infrastructure (adapter, three providers, file marker parser, context block loader) from the Bubls backend into the spec-doc Flask backend as internal-only infrastructure — no HTTP surface. Phase 2 AI endpoints inherit a tested foundation instead of retrofitting it.

**Effort**: 1 day

**Dependencies**: Task 1 (Flask scaffold + `server/app.py` + `server/core/config.py` + `server/requirements.txt`) must be complete.

**Parallel With**: Tasks 2 and 3 are independent of this task and may run concurrently.

**Blocks**: Phase 2 AI operation endpoints (rewrite, generate, iterate, generate-spec, review).

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task ports `server/modules/chain/` from the Bubls backend verbatim (with Bubls-specific user/feature/entitlement types stripped), landing internal AI call infrastructure that Phase 2 will wire up. The chain module exposes no Blueprint and registers no HTTP routes — it is a pure Python package that Phase 2 endpoint modules will import via the adapter boundary. The ELA Adapter Pattern (Pattern #1 from `references.md:571–643`) is the structural invariant: `adapter.py` is the sole import point for AI calls; feature code never touches `providers.*` directly. Three providers sit behind the adapter — `claude` (Anthropic SDK for production), `cli` (subprocess fallback, the current Express path), `mock` (deterministic, for tests). A file marker parser handles `===FILE: {name}===` splits from multi-file LLM output; a context loader reads the four workspace-root context files into plain strings for prompt injection. All tests run with `CHAIN_PROVIDER=mock` — no live Claude call, no API key, no network.

**Trade-offs considered**:
- **Port `context.py` verbatim with user objects** — rejected; spec-doc has no user system. `with_context()` is adapted to accept plain `builder: str` and `principles: str` instead of a user profile object, reducing coupling to a Bubls-specific type that doesn't exist here.
- **Use the Bubls manifest.json-based context loader** — rejected for Phase 1; the four spec-doc context files are fixed paths at workspace root, making manifest.json an abstraction of exactly one concrete case. The loader is adapted to read directly from fixed paths with an optional `CONTEXT_PROVIDER=mock` override.
- **Adapter + providers pattern (chosen)** — preferred because it's verbatim from `references.md:571–643`, already battle-tested (164 Bubls tests), and the structural test enforces the coupling rule automatically.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm working tree state
git status
git diff HEAD -- server/modules/ server/requirements.txt

# Confirm Task 1 scaffold exists — STOP if any are missing
ls server/app.py server/core/config.py server/requirements.txt server/core/__init__.py

# Confirm tests run from server/ directory (import convention check)
cd {WORKSPACE}/spec-doc/server && python -m pytest --collect-only -q 2>&1 | tail -10

# Record baseline pass count
cd {WORKSPACE}/spec-doc/server && python -m pytest -q 2>&1 | tail -5
```

**If Task 1 files are missing**: stop. Task 1 must be complete before this task starts.

**If `server/modules/__init__.py` is missing** (Task 2 not yet done): create it as an empty file in Step 1. The chain package requires the `modules` namespace package to exist.

**If working tree is dirty on target files**: stash or commit unrelated changes before proceeding. The current `git status` shows `references.md` and `src/app/components/new-project/new-project.component.ts` as modified — leave both untouched.

**Baseline recorded**: N/N passing (record count before starting).

---

## 3. Files

### To Create (new)

- `server/modules/__init__.py` — namespace package marker for `modules`; empty; create only if absent (Task 2 may have created it)
- `server/modules/chain/__init__.py` — package marker; empty
- `server/modules/chain/errors.py` — `ProviderError(Exception)` with `message` and `status_code`; ported from `references.md:347–350`
- `server/modules/chain/types.py` — `ChainResult` and `ReviewResult` frozen dataclasses; ported from `references.md:347–362`
- `server/modules/chain/context.py` — `with_context()` prompt assembly; adapted from `references.md:363–376` (plain strings instead of user objects)
- `server/modules/chain/providers/__init__.py` — re-exports `claude`, `cli`, `mock` submodules
- `server/modules/chain/providers/claude.py` — Anthropic SDK wrapper; ported verbatim from `references.md:107–176`
- `server/modules/chain/providers/cli.py` — `claude -p` subprocess wrapper; ported verbatim from `references.md:178–225`
- `server/modules/chain/providers/mock.py` — deterministic echo provider; ported verbatim from `references.md:227–261`
- `server/modules/chain/adapter.py` — ELA adapter boundary; adapted from `references.md:583–620` (replaces `user/feature` with `builder/principles` plain strings)
- `server/modules/chain/file_parser.py` — `===FILE: {name}===` parser; ported verbatim from `references.md:263–341`
- `server/modules/chain/context_loader.py` — reads `builder.md`, `principles.md`, `codebase.md`, `references.md` from workspace root; adapted from `references.md:383–460` (no manifest.json)
- `server/modules/chain/tests/__init__.py` — empty package marker
- `server/modules/chain/tests/test_adapter.py` — adapter generate/stream/provider-selection tests
- `server/modules/chain/tests/test_file_parser.py` — file marker parse + multi-chain output tests
- `server/modules/chain/tests/test_context_loader.py` — mock mode, file reading, missing file tests
- `server/modules/chain/tests/test_structural.py` — adapter-boundary coupling test; ported verbatim from `references.md:624–643`

### To Modify (cite CODEBASE CONTEXT)

- `server/requirements.txt` (Task 1 deliverable) — add `anthropic` package; currently contains Flask, flask-cors, pytest, python-dotenv

### To Leave Alone

- `server/app.py` (Task 1) — chain module has no Blueprint; `ENABLED_MODULES` is NOT modified
- `server/core/config.py` (Task 1) — `CHAIN_PROVIDER` and `CONTEXT_PROVIDER` are already declared there; no changes needed
- `server/modules/project/` (Task 2 deliverable, if exists) — do not touch
- `server/modules/context_files/` (Task 3 deliverable, if exists) — do not touch
- `server.js` — Express continues running on 3100; zero modifications
- `builder.md`, `principles.md`, `codebase.md`, `references.md` — workspace-root context files; read only by `context_loader.py`, never written by this task
- `src/app/` — zero Angular changes; this task has no HTTP surface at all

---

## 4. Implementation Steps

### Step 1: Create package skeleton and add `anthropic` to requirements

**Action**: Create all empty `__init__.py` files and add `anthropic` to `server/requirements.txt`.

**Files**: `server/modules/__init__.py` (create only if absent), `server/modules/chain/__init__.py`, `server/modules/chain/providers/__init__.py`, `server/modules/chain/tests/__init__.py`, `server/requirements.txt`

**Pattern**:
```bash
# Run from {WORKSPACE}/spec-doc
mkdir -p server/modules/chain/providers server/modules/chain/tests
touch server/modules/chain/__init__.py
touch server/modules/chain/providers/__init__.py
touch server/modules/chain/tests/__init__.py
# Create server/modules/__init__.py only if absent:
[ -f server/modules/__init__.py ] || touch server/modules/__init__.py
```

Then add to `server/requirements.txt`:
```
anthropic
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && python -c "import modules.chain; import modules.chain.providers; print('OK')"
pip show anthropic || pip install anthropic
```
Expect: `OK` with no errors.

---

### Step 2: Port `errors.py` and `types.py`

**Action**: Create the two domain type files. Port verbatim from `references.md:347–362`.

**File**: `server/modules/chain/errors.py` (new)

```python
"""Provider-layer failure — ported from references.md:347–350."""
from __future__ import annotations


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
```

**File**: `server/modules/chain/types.py` (new)

```python
"""Domain-level return types (ACL) — ported from references.md:347–362."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChainResult:
    text: str
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None


@dataclass(frozen=True)
class ReviewResult:
    scores: dict[str, float]
    issues: list[str]
    raw: str
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && python -c "from modules.chain.types import ChainResult; from modules.chain.errors import ProviderError; print(ChainResult(text='ok', latency_ms=5))"
```
Expect: `ChainResult(text='ok', latency_ms=5, tokens_in=None, tokens_out=None)`.

---

### Step 3: Port `context.py` (adapted — plain strings, not user objects)

**Action**: Create `context.py`. Port the shape from `references.md:363–376` but replace the user-object accessors (`getattr(user, "builder", None)`) with plain `str` parameters. Spec-doc has no user system.

**File**: `server/modules/chain/context.py` (new)

```python
"""Prompt context assembly — adapted from references.md:363–376.

Spec-doc adaptation: accepts plain strings for builder and principles,
not Bubls user objects. Context injection happens at the adapter boundary only.
"""
from __future__ import annotations


def with_context(system: str, builder: str = "", principles: str = "") -> str:
    """Prepend builder profile and principles to system prompt if provided."""
    parts = [system]
    if builder:
        parts.append(f"\n\n## BUILDER CONTEXT\n{builder}")
    if principles:
        parts.append(f"\n\n## PRINCIPLES\n{principles}")
    return "".join(parts)
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && python -c "
from modules.chain.context import with_context
result = with_context('base system', builder='my profile')
assert '## BUILDER CONTEXT' in result
assert 'my profile' in result
print('OK')
"
```
Expect: `OK`.

---

### Step 4: Port three providers + `providers/__init__.py`

**Action**: Port all three provider files verbatim from `references.md`. No modifications except the relative import path for `ProviderError`.

**File**: `server/modules/chain/providers/claude.py` — port verbatim from `references.md:107–176`

```python
"""Claude provider — ported verbatim from references.md:107–176."""
from __future__ import annotations

from anthropic import Anthropic, APIConnectionError, APIError, RateLimitError

from ..errors import ProviderError

_client = Anthropic(timeout=60.0, max_retries=2)


def create_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096) -> str:
    try:
        response = _client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except RateLimitError:
        raise ProviderError("AI service is busy. Please try again in a moment.", 503)
    except APIConnectionError:
        raise ProviderError("Cannot connect to AI service. Please try again.", 502)
    except APIError as e:
        raise ProviderError(f"AI service error: {e.message}", 502)


def stream_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096):
    try:
        with _client.messages.stream(
            model=model, max_tokens=max_tokens, system=system,
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

**File**: `server/modules/chain/providers/cli.py` — port verbatim from `references.md:178–225`

```python
"""CLI provider — ported verbatim from references.md:178–225."""
from __future__ import annotations

import subprocess

from ..errors import ProviderError


def create_message(system: str, prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 4096) -> str:
    cmd = ["claude", "-p", "--output-format", "text"]
    if system:
        cmd.extend(["--system-prompt", system])
    try:
        result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise ProviderError(
                f"claude CLI exited with code {result.returncode}: {result.stderr[:200]}", 502
            )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise ProviderError("claude CLI timed out after 600s", 504)
    except FileNotFoundError:
        raise ProviderError("claude CLI not found — install Claude Code", 500)


def stream_message(system: str, prompt: str, *, model: str = "claude-sonnet-4-5", max_tokens: int = 4096):
    # CLI does not stream; run single-shot and yield the full result as one chunk
    yield create_message(system, prompt, model=model, max_tokens=max_tokens)
```

**File**: `server/modules/chain/providers/mock.py` — port verbatim from `references.md:227–261`

```python
"""Deterministic mock provider — ported verbatim from references.md:227–261."""
from __future__ import annotations

from typing import Iterator


def create_message(system: str, prompt: str, *, model: str = "mock", max_tokens: int = 4096) -> str:
    return f"MOCK[{model}]::sys={system[:20]}::prompt={prompt[:40]}"


def stream_message(system: str, prompt: str, *, model: str = "mock", max_tokens: int = 4096) -> Iterator[str]:
    yield f"MOCK[{model}]"
    yield "::"
    yield f"sys={system[:20]}"
    yield "::"
    yield f"prompt={prompt[:40]}"
```

**File**: `server/modules/chain/providers/__init__.py`

```python
"""Re-export provider modules so adapter.py can use providers.claude / providers.cli / providers.mock."""
from . import claude, cli, mock

__all__ = ["claude", "cli", "mock"]
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && python -c "
from modules.chain.providers import mock
result = mock.create_message('sys', 'prompt', model='test')
assert result.startswith('MOCK[test]')
chunks = list(mock.stream_message('sys', 'prompt', model='test'))
assert len(chunks) == 5
print('OK')
"
```
Expect: `OK`.

---

### Step 5: Port `adapter.py` (ELA Pattern #1 — critical)

**Action**: Port the adapter from `references.md:583–620`. Replace the `user/feature` parameter design with `builder/principles` plain strings (spec-doc adaptation). This file is the single import point for all AI calls; feature modules never import `providers.*` directly.

**File**: `server/modules/chain/adapter.py` (new)

```python
"""AI call adapter — ELA Pattern #1. Sole import for AI operations.

Adapted from references.md:583–620. Spec-doc change: no user objects.
builder and principles are plain strings loaded by context_loader or passed directly.

INVARIANT: Feature modules import ONLY from this file. Never from providers.*.
Enforced by test_structural.py.
"""
from __future__ import annotations

import os
import time
from typing import Iterator

from . import providers
from .context import with_context
from .types import ChainResult

DEFAULT_MODEL = "claude-sonnet-4-5"


def _select_provider():
    """Select provider module based on CHAIN_PROVIDER env var."""
    name = os.environ.get("CHAIN_PROVIDER", "cli")
    mapping = {"claude": providers.claude, "cli": providers.cli, "mock": providers.mock}
    if name not in mapping:
        raise ValueError(
            f"Unknown CHAIN_PROVIDER={name!r}; expected one of {sorted(mapping)}"
        )
    return mapping[name]


def generate(
    system: str,
    prompt: str,
    *,
    builder: str = "",
    principles: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> ChainResult:
    """Single-shot AI completion. Returns ChainResult with text and latency."""
    effective_system = with_context(system, builder=builder, principles=principles)
    provider = _select_provider()
    t0 = time.monotonic()
    text = provider.create_message(effective_system, prompt, model=model, max_tokens=max_tokens)
    return ChainResult(text=text, latency_ms=int((time.monotonic() - t0) * 1000))


def stream(
    system: str,
    prompt: str,
    *,
    builder: str = "",
    principles: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> Iterator[str]:
    """Streaming AI completion. Yields text chunks."""
    effective_system = with_context(system, builder=builder, principles=principles)
    provider = _select_provider()
    yield from provider.stream_message(effective_system, prompt, model=model, max_tokens=max_tokens)
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && CHAIN_PROVIDER=mock python -c "
from modules.chain.adapter import generate, stream
r = generate('system prompt', 'user prompt')
assert r.text.startswith('MOCK['), f'unexpected: {r.text}'
assert r.latency_ms >= 0
chunks = list(stream('sys', 'p'))
assert ''.join(chunks).startswith('MOCK[')
print('OK')
"
```
Expect: `OK`.

---

### Step 6: Port `file_parser.py`

**Action**: Port verbatim from `references.md:263–341`. No modifications — the marker format is identical to spec-doc's existing `===FILE: {name}===` convention.

**File**: `server/modules/chain/file_parser.py` (new)

```python
"""Anti-corruption layer: parse ===FILE: {name}=== markers — ported verbatim from references.md:263–341."""
from __future__ import annotations

import re

_FILE_MARKER = re.compile(r"^===FILE:\s*(.+?)\s*===$", re.MULTILINE)
_END_MARKER = re.compile(r"^===END===$", re.MULTILINE)
_LINT_MARKER = re.compile(r"^===LINT===$", re.MULTILINE)
_SCORE_MARKER = re.compile(r"^===SCORE===$", re.MULTILINE)


def parse_file_markers(text: str) -> list[dict[str, str]]:
    """Split marker-delimited text into structured file objects.

    Returns:
        List of {"name": str, "content": str} dicts.

    Raises:
        ValueError: if no ===FILE: {name}=== markers found.
    """
    text = _END_MARKER.sub("", text).rstrip()
    markers = list(_FILE_MARKER.finditer(text))
    if not markers:
        raise ValueError(
            "No ===FILE: {name}=== markers found in output. "
            "Expected multi-file format but got plain text."
        )
    files: list[dict[str, str]] = []
    for i, match in enumerate(markers):
        name = match.group(1).strip()
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        if content:
            files.append({"name": name, "content": content})
    return files


def parse_multi_chain_output(text: str) -> dict:
    """Parse single-call output: ===LINT===, ===FILE:===, ===SCORE===.

    Returns:
        {"files": [{"name": str, "content": str}, ...], "meta": {"lint": str, "score": str}}
    """
    meta: dict[str, str] = {}

    lint_match = _LINT_MARKER.search(text)
    first_file = _FILE_MARKER.search(text)
    if lint_match and first_file and lint_match.start() < first_file.start():
        meta["lint"] = text[lint_match.end():first_file.start()].strip()

    score_match = _SCORE_MARKER.search(text)
    end_match = _END_MARKER.search(text)
    if score_match:
        score_end = (
            end_match.start()
            if end_match and end_match.start() > score_match.start()
            else len(text)
        )
        meta["score"] = text[score_match.end():score_end].strip()

    clean = text
    if lint_match and first_file:
        clean = text[:lint_match.start()] + text[first_file.start():]
    if score_match:
        score_end_pos = (
            end_match.end()
            if end_match and end_match.start() > score_match.start()
            else len(text)
        )
        clean = (
            clean[:clean.find("===SCORE===")] + clean[score_end_pos:]
            if "===SCORE===" in clean
            else clean
        )

    try:
        files = parse_file_markers(clean)
    except ValueError:
        files = [{"name": "output.md", "content": text.strip()}]

    return {"files": files, "meta": meta}
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && python -c "
from modules.chain.file_parser import parse_file_markers
files = parse_file_markers('===FILE: test.md===\nhello world\n===END===')
assert files[0]['name'] == 'test.md'
assert files[0]['content'] == 'hello world'
print('OK')
"
```
Expect: `OK`.

---

### Step 7: Create `context_loader.py` (adapted from Bubls — no manifest.json)

**Action**: Create the context loader. Adapt from `references.md:383–460`: replace the manifest.json indirection with a fixed path map for the four spec-doc context files at workspace root. Keep mock mode (`CONTEXT_PROVIDER=mock`). The workspace root is the parent of `server/` (i.e., `spec-doc/`).

**File**: `server/modules/chain/context_loader.py` (new)

```python
"""Context file loader for spec-doc V2.

Adapted from references.md:383–460 (Bubls context/loader.py).
Spec-doc change: no manifest.json — four fixed files at workspace root.
Mock mode: set CONTEXT_PROVIDER=mock.

Structural invariant: this is the ONLY module that reads the four workspace
context files. Feature modules call load_context() / load_all_context() here.
"""
from __future__ import annotations

import os
from pathlib import Path

# Workspace root = spec-doc/ = parent of server/
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_CONTEXT_FILES: dict[str, Path] = {
    "builder": _WORKSPACE_ROOT / "builder.md",
    "principles": _WORKSPACE_ROOT / "principles.md",
    "codebase": _WORKSPACE_ROOT / "codebase.md",
    "references": _WORKSPACE_ROOT / "references.md",
}


def _is_mock() -> bool:
    return os.environ.get("CONTEXT_PROVIDER", "").lower() == "mock"


def load_context(name: str) -> str:
    """Load a single context file by name.

    Returns empty string if the file does not exist (panels may not be populated).
    Raises KeyError for unknown names.
    """
    if _is_mock():
        return f"MOCK_CONTEXT[{name}]"
    path = _CONTEXT_FILES.get(name)
    if path is None:
        raise KeyError(
            f"Unknown context file {name!r}. Available: {sorted(_CONTEXT_FILES)}"
        )
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_all_context() -> dict[str, str]:
    """Load all four context files. Missing files return empty string."""
    return {name: load_context(name) for name in _CONTEXT_FILES}
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/server && CONTEXT_PROVIDER=mock python -c "
from modules.chain.context_loader import load_context, load_all_context
assert load_context('builder') == 'MOCK_CONTEXT[builder]'
ctx = load_all_context()
assert set(ctx.keys()) == {'builder', 'principles', 'codebase', 'references'}
print('OK')
"
```
Expect: `OK`.

---

## 5. Tests

Framework: pytest. Run from `{WORKSPACE}/spec-doc/server`. All tests use `CHAIN_PROVIDER=mock` or `CONTEXT_PROVIDER=mock` via `monkeypatch` — no live AI calls, no API key required.

**File**: `server/modules/chain/tests/test_adapter.py` (new)

```python
"""Adapter tests — generate, stream, provider selection."""
import pytest
from modules.chain.adapter import generate, stream, _select_provider


def test_generate_with_mock_provider_returns_chain_result(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    result = generate("system", "user prompt")
    assert result.text.startswith("MOCK["), f"unexpected text: {result.text}"
    assert result.latency_ms >= 0


def test_generate_embeds_model_in_mock_text(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    result = generate("sys", "p", model="custom-model")
    assert "custom-model" in result.text


def test_generate_prepends_builder_context_to_system(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    # with_context prepends "## BUILDER CONTEXT\n..." to system
    # mock echoes sys[:20]; effective system starts with "base\n\n## BUILDER CO"
    result = generate("base", "p", builder="BuilderText")
    assert "BUILDER" in result.text, f"builder context not reflected: {result.text}"


def test_generate_prepends_principles_to_system(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    result = generate("sys", "p", principles="Keep it short")
    assert "PRINCIPL" in result.text, f"principles not reflected: {result.text}"


def test_stream_with_mock_yields_multiple_chunks(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    chunks = list(stream("sys", "p"))
    assert len(chunks) >= 3, f"expected >=3 chunks, got {len(chunks)}"
    full = "".join(chunks)
    assert full.startswith("MOCK["), f"unexpected stream start: {full}"


def test_unknown_chain_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "nonexistent")
    with pytest.raises(ValueError, match="nonexistent"):
        _select_provider()


def test_chain_result_is_immutable(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    result = generate("sys", "p")
    with pytest.raises((AttributeError, TypeError)):
        result.text = "mutation attempt"  # type: ignore[misc]
```

**File**: `server/modules/chain/tests/test_file_parser.py` (new)

```python
"""File parser tests — single file, multi-file, meta sections, edge cases."""
import pytest
from modules.chain.file_parser import parse_file_markers, parse_multi_chain_output


def test_single_file_extracted():
    text = "===FILE: output.md===\nHello world\n===END==="
    files = parse_file_markers(text)
    assert len(files) == 1
    assert files[0]["name"] == "output.md"
    assert files[0]["content"] == "Hello world"


def test_multiple_files_extracted_in_order():
    text = (
        "===FILE: a.md===\nContent A\n"
        "===FILE: b.md===\nContent B\n"
        "===END==="
    )
    files = parse_file_markers(text)
    assert len(files) == 2
    assert files[0]["name"] == "a.md"
    assert "Content A" in files[0]["content"]
    assert files[1]["name"] == "b.md"
    assert "Content B" in files[1]["content"]


def test_no_markers_raises_value_error():
    with pytest.raises(ValueError, match="===FILE:"):
        parse_file_markers("plain text with no markers here")


def test_end_marker_not_in_content():
    text = "===FILE: doc.md===\nBody\n===END==="
    files = parse_file_markers(text)
    assert "===END===" not in files[0]["content"]


def test_whitespace_around_filename_trimmed():
    text = "===FILE:   spaced.md   ===\nContent\n===END==="
    files = parse_file_markers(text)
    assert files[0]["name"] == "spaced.md"


def test_parse_multi_chain_output_extracts_lint_meta():
    text = (
        "===LINT===\nlint advisory here\n"
        "===FILE: out.md===\nfile content\n"
        "===END==="
    )
    result = parse_multi_chain_output(text)
    assert result["meta"].get("lint") == "lint advisory here"
    assert result["files"][0]["name"] == "out.md"
    assert result["files"][0]["content"] == "file content"


def test_parse_multi_chain_output_extracts_score_meta():
    text = (
        "===FILE: out.md===\ncontent\n"
        "===SCORE===\n8.5/10\n"
        "===END==="
    )
    result = parse_multi_chain_output(text)
    assert result["meta"].get("score") == "8.5/10"
    assert result["files"][0]["content"] == "content"


def test_parse_multi_chain_output_plain_text_fallback():
    text = "no markers here at all, just plain text output"
    result = parse_multi_chain_output(text)
    assert len(result["files"]) == 1
    assert result["files"][0]["name"] == "output.md"
    assert result["files"][0]["content"] == text.strip()
```

**File**: `server/modules/chain/tests/test_context_loader.py` (new)

```python
"""Context loader tests — mock mode, file reading, missing file, key error."""
import pytest
from modules.chain import context_loader
from modules.chain.context_loader import load_context, load_all_context


def test_mock_mode_returns_mock_string(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")
    assert load_context("builder") == "MOCK_CONTEXT[builder]"
    assert load_context("principles") == "MOCK_CONTEXT[principles]"


def test_load_all_context_mock_returns_four_keys(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")
    result = load_all_context()
    assert set(result.keys()) == {"builder", "principles", "codebase", "references"}
    assert all(v.startswith("MOCK_CONTEXT[") for v in result.values())


def test_unknown_context_name_raises_key_error(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    with pytest.raises(KeyError, match="unknown_key"):
        load_context("unknown_key")


def test_load_context_reads_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    monkeypatch.setattr(context_loader, "_CONTEXT_FILES", {
        "builder": tmp_path / "builder.md",
        "principles": tmp_path / "principles.md",
        "codebase": tmp_path / "codebase.md",
        "references": tmp_path / "references.md",
    })
    (tmp_path / "builder.md").write_text("# My Builder Profile\nContent here")
    result = load_context("builder")
    assert "My Builder Profile" in result
    assert "Content here" in result


def test_missing_file_returns_empty_string(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    monkeypatch.setattr(context_loader, "_CONTEXT_FILES", {
        "builder": tmp_path / "nonexistent.md",
        "principles": tmp_path / "principles.md",
        "codebase": tmp_path / "codebase.md",
        "references": tmp_path / "references.md",
    })
    result = load_context("builder")
    assert result == ""


def test_load_context_strips_trailing_whitespace(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "")
    monkeypatch.setattr(context_loader, "_CONTEXT_FILES", {
        "builder": tmp_path / "builder.md",
        "principles": tmp_path / "principles.md",
        "codebase": tmp_path / "codebase.md",
        "references": tmp_path / "references.md",
    })
    (tmp_path / "builder.md").write_text("  content with whitespace  \n\n")
    result = load_context("builder")
    assert result == "content with whitespace"
```

**File**: `server/modules/chain/tests/test_structural.py` (new)

```python
"""Adapter-boundary structural test — ported verbatim from references.md:624–643.

INVARIANT: No file outside adapter.py, providers/, or tests/ may import providers directly.
This test greps the chain module tree and fails on any violation.
"""
import pathlib
from modules.chain import adapter as _adapter


def test_feature_modules_must_not_import_providers_directly():
    """Greps the chain module tree for direct provider imports.

    Any file outside adapter.py / providers/ / tests/ that imports from
    providers fails. Catches coupling that code review can miss.
    """
    infra_dir = pathlib.Path(_adapter.__file__).parent
    offenders = []
    for py in infra_dir.rglob("*.py"):
        rel = py.relative_to(infra_dir)
        # Skip: adapter.py (allowed), providers/ tree (allowed), tests/ tree (allowed)
        if rel.parts[0] in ("providers", "tests") or rel.name == "adapter.py":
            continue
        text = py.read_text()
        if "from .providers" in text or "from modules.chain.providers" in text:
            offenders.append(str(rel))
    assert offenders == [], (
        f"Adapter-boundary violation: {offenders}. "
        "Only adapter.py may import providers."
    )
```

---

## 6. Commit Plan

**Commit 1** — `feat(chain): port chain infrastructure — types, errors, context, providers, adapter`
- Files: `server/modules/chain/__init__.py`, `server/modules/chain/errors.py`, `server/modules/chain/types.py`, `server/modules/chain/context.py`, `server/modules/chain/providers/__init__.py`, `server/modules/chain/providers/claude.py`, `server/modules/chain/providers/cli.py`, `server/modules/chain/providers/mock.py`, `server/modules/chain/adapter.py`, `server/requirements.txt`
- Also: `server/modules/__init__.py` (create if absent)
- What: Core chain infrastructure — domain types, provider implementations, ELA adapter boundary

**Commit 2** — `feat(chain): add file_parser and context_loader`
- Files: `server/modules/chain/file_parser.py`, `server/modules/chain/context_loader.py`
- What: Anti-corruption layer for multi-file LLM output; workspace context file reader

**Commit 3** — `test(chain): pytest suite — adapter, file_parser, context_loader, structural coupling`
- Files: `server/modules/chain/tests/__init__.py`, `server/modules/chain/tests/test_adapter.py`, `server/modules/chain/tests/test_file_parser.py`, `server/modules/chain/tests/test_context_loader.py`, `server/modules/chain/tests/test_structural.py`
- What: 20 tests covering all public interfaces and the adapter-boundary invariant

**Deviation logging**: if any step deviates from this guide (different directory name, modified file shapes), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/server && python -m pytest -v 2>&1 | tail -30
```

**Expected delta**: N → N+20 passing. Zero pre-existing tests broken. The structural test (`test_feature_modules_must_not_import_providers_directly`) must pass — if it fails, a provider import was added to a file outside the allowed set.

To run chain tests in isolation:
```bash
cd {WORKSPACE}/spec-doc/server && python -m pytest modules/chain/tests/ -v
```
Expect: 20 passed.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` — no HTTP surface means no frontend regression risk.
- **Per-branch**: `git reset --hard <pre-task-sha>` removes all three commits. Since this task creates only new files and one line in `requirements.txt`, a reset is clean.
- **Infrastructure note**: this task adds no Blueprint to `ENABLED_MODULES` and registers no routes, so rolling it back has zero runtime effect on the running Flask server.

---

## 9. Deviations Allowed

- **`server/` vs `flask/` directory name**: Tasks 2 and 3 may have been implemented with `flask/` (Task 3 guide uses that prefix). If so, use `flask/modules/chain/` throughout and adjust all `sys.path` references accordingly. Log deviation in commit body.
- **`server/modules/__init__.py` already exists**: if Task 2 ran first, this file exists; skip creation silently.
- **`anthropic` already in `requirements.txt`**: if Task 1 or an earlier task added it, skip; verify with `pip show anthropic`.
- **Test framework mismatch**: if Task 1 used a different runner (e.g., `unittest`), translate the test files to match. Log the translation in the commit body.
- **Reference code shape mismatch**: if `references.md` was updated since this guide was written, port from the current `references.md` state; flag specific line-range differences in the commit body.
- **Step N unlocks simplification for Step N+1**: take it, log in commit.
- **Side-effect required** (push, pip publish, schema change): STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task delivers internal infrastructure only. No HTTP routes are registered, no Angular behavior changes, and no Phase 2 features are partially implemented. The following are explicitly deferred — if the executor encounters any of these as seemingly obvious extensions, stop and flag rather than absorbing them.

- **AI text endpoints** (rewrite, generate, iterate, generate-spec, review, lint-braindump) — Phase 2's first task. The chain module is the foundation they build on; the endpoints themselves are out of scope here.
- **`definition_runner.py` (schema-driven chain runner)** — cited in `codebase.md` as part of the Bubls chain module; no Phase 1 spec-doc feature uses it. Port only when a Phase 2 endpoint requires it.
- **Retry/backoff logic and circuit-breaker patterns** — epic explicitly defers these: "no retry/backoff logic, no circuit-breaker patterns — those ship when Phase 2 defines failure modes for real AI calls."
- **Blinker signals** (`chain.signals` in Bubls) — observer pattern for chain events; no Phase 1 consumer.
- **`stream_message` on the CLI provider** — the implementation above yields the full response as one chunk (CLI doesn't stream). True CLI streaming via `--stream` flag is a Phase 2 concern when SSE endpoints are defined.
- **Walker integration** — `server/core/walker.py` exists from Task 1; chain module does not call it; no wiring needed here.
- **Registration in `ENABLED_MODULES`** — chain has no Blueprint; `server/app.py` is not modified by this task.

**Rule for the executor**: if a change appears helpful but is listed above, flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, ELA Pattern #1
- [Epic](./epic.md) – Task scope and port budget
- [Timeline](./timeline.md) – Update status to `done` after verification passes
- [`references.md`](../../references.md) – Source code for all ports (line ranges cited inline above)