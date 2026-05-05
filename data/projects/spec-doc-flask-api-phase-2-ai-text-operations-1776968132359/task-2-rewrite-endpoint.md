# Task 2: Rewrite Endpoint

**Purpose**: Wire `POST /api/ai/text/rewrite` through a new `chain.adapter.rewrite()` function using the `{ text, instructions }` request shape and `{ text, latencyMs }` response envelope — smoke test for the entire AI wiring pattern.

**Effort**: 0.5 days

**Dependencies**: Task 1 (Module scaffold + prompt functions) — must create `flask/modules/ai/`, `flask/modules/ai/routes.py` with `ai_bp`, `flask/modules/ai/prompts/rewrite.py` with `rewrite_prompt()`, and register `('modules.ai.routes', 'ai_bp')` in `flask/create_app.py` ENABLED_MODULES before this task runs.

**Parallel With**: Tasks 3 and 4 once Task 1 is done.

**Blocks**: Tasks 3 and 4 (validate wiring pattern before they follow the same path).

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 2 wires the simplest of the seven AI endpoints so the full stack — Angular client → Flask route → chain adapter → Claude provider — can be validated end-to-end before Tasks 3 and 4 expand on the same pattern. The rewrite endpoint is deliberately chosen as the smoke test because it has no context injection (no filesystem reads, no builder profile lookup), making the failure surface as small as possible: if it breaks, the bug is in the route wiring or the adapter, not in context loading. Task 2 adds exactly two code units: `adapter.rewrite()` (a peer of `adapter.generate()` that skips `with_context()`) and the `POST /rewrite` handler in the `ai_bp` blueprint scaffold created by Task 1.

**Trade-offs considered:**
- **Call `chain.adapter.generate()` directly from the route** — rejected because the epic explicitly names `adapter.rewrite()` and the architecture doc calls out that rewrite intentionally skips context injection; naming this distinction at the adapter boundary makes it explicit and structural tests can enforce it separately later.
- **Inline `rewrite_prompt()` logic in the route handler** — rejected; architecture doc mandates prompt logic lives in `prompts/` submodule so it is unit-testable without an HTTP fixture; Task 1 already places it there.
- **Add `adapter.rewrite()` in Task 1 as part of the scaffold** — reasonable, but Task 2 is the first actual consumer; adding it here keeps Task 1 focused on the module structure and makes Task 2 genuinely self-contained.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm Task 1 is complete — all four outputs must exist
ls flask/modules/ai/__init__.py
ls flask/modules/ai/routes.py
ls flask/modules/ai/prompts/__init__.py
ls flask/modules/ai/prompts/rewrite.py

# 2. Confirm ai_bp is registered in ENABLED_MODULES
grep -n "ai_bp" flask/create_app.py

# 3. Confirm rewrite_prompt signature
python3 -c "from modules.ai.prompts.rewrite import rewrite_prompt; print(rewrite_prompt('t','i'))"

# 4. Confirm working tree is clean on target files
git diff HEAD -- flask/modules/chain/adapter.py flask/modules/ai/routes.py

# 5. Baseline test count
cd flask && python -m pytest -q 2>&1 | tail -3
```

**If any of the four `ls` commands fail**: Task 1 is incomplete. STOP — do not proceed until Task 1 is done.

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: \_\_/\_\_ passing. (Record actual output of step 5.)

---

## 3. Files

### To Create (new)
- `flask/tests/test_ai_rewrite.py` — 9 pytest tests covering HTTP validation, mock provider smoke, prompt unit, and adapter unit assertions

### To Modify (cite CODEBASE CONTEXT)
- `flask/modules/chain/adapter.py` — add `rewrite()` function after `generate()` (currently: `generate` + `stream`; no `rewrite`)
- `flask/modules/ai/routes.py` — add `POST /rewrite` handler to the `ai_bp` blueprint scaffold that Task 1 created

### To Leave Alone
- `flask/modules/ai/prompts/rewrite.py` — Task 1 owns this; Task 2 imports `rewrite_prompt` from it but does not modify it
- `flask/create_app.py` — Task 1 registered `ai_bp`; Task 2 must not touch ENABLED_MODULES
- `flask/modules/chain/` (all files except `adapter.py`) — Phase 1 work; stable
- `flask/modules/chain/tests/test_adapter.py` — existing adapter tests; do not modify (new adapter tests go in `test_ai_rewrite.py`)
- `flask/modules/chain/tests/test_structural.py` — structural invariant; must still pass after this task

---

## 4. Implementation Steps

### Step 1: Add `adapter.rewrite()` to `flask/modules/chain/adapter.py`

**Action**: Append `rewrite()` directly after the `generate()` function. The function is identical to `generate()` except it skips `with_context()` — rewrite is instruction-driven by the caller, so prepending builder profile or principles would change user-facing output unpredictably.

**File**: `flask/modules/chain/adapter.py` (CODEBASE CONTEXT: `flask/modules/chain/`)

**Pattern** (add after line 47, before `def stream`):
```python
def rewrite(
    system: str,
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
) -> ChainResult:
    """Instruction-driven text rewrite. No context injection — rewrite is caller-driven.

    Contrast with generate(), which prepends builder/principles via with_context().
    """
    provider = _select_provider()
    t0 = time.monotonic()
    text = provider.create_message(system, prompt, model=model, max_tokens=max_tokens)
    return ChainResult(text=text, latency_ms=int((time.monotonic() - t0) * 1000))
```

**Verify**:
```bash
cd {WORKSPACE}/flask && python -m pytest modules/chain/tests/test_adapter.py -q
```
Expect: same count as before (new `rewrite` tests added in Step 3).

---

### Step 2: Wire `POST /rewrite` in `flask/modules/ai/routes.py`

**Action**: Add the `/rewrite` route handler to the blueprint scaffold. Follows the four-step protocol: validate → (no context load — rewrite is instruction-driven) → adapter → envelope. Import `chain.adapter` as `chain_adapter` (never import from `chain.providers.*` directly).

**File**: `flask/modules/ai/routes.py` (CODEBASE CONTEXT: Task 1 creates this file)

**Pattern**:
```python
from flask import Blueprint, request, jsonify
from modules.chain import adapter as chain_adapter
from modules.ai.prompts.rewrite import rewrite_prompt

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai/text')


@ai_bp.post('/rewrite')
def rewrite():
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    instructions = (data.get('instructions') or '').strip()
    if not text:
        return jsonify({'error': 'text is required'}), 400
    system, prompt = rewrite_prompt(text, instructions)
    result = chain_adapter.rewrite(system, prompt)
    return jsonify({'text': result.text, 'latencyMs': result.latency_ms})
```

If Task 1 already placed a `rewrite()` stub in `routes.py`, fill it in rather than appending. If `ai_bp = Blueprint(...)` is already present, keep the existing declaration and add only the route handler.

**Verify** (requires Flask app to start cleanly with CHAIN_PROVIDER=mock):
```bash
cd {WORKSPACE}/flask && CHAIN_PROVIDER=mock python -m pytest -q -k "health" 2>&1 | tail -3
```
Expect: health tests still pass (blueprint registered, no import error).

Then spot-check manually:
```bash
cd {WORKSPACE}/flask && CHAIN_PROVIDER=mock flask --app app.py run --port 3101 &
sleep 1
curl -s -X POST http://localhost:3101/api/ai/text/rewrite \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello world","instructions":"make it formal"}' | python3 -m json.tool
# Expect: {"latencyMs": <int>, "text": "MOCK[...]"}
kill %1
```

---

### Step 3: Write tests in `flask/tests/test_ai_rewrite.py`

**Action**: Create the test file. The `client` fixture in this file overrides the global `conftest.py` client by monkeypatching `CHAIN_PROVIDER=mock` before `create_app()` is called — same pattern as `test_project.py`'s `app` fixture overriding `_PROJECTS_PATH`.

**File**: `flask/tests/test_ai_rewrite.py` (new)

See **Section 5** for complete test bodies.

**Verify**:
```bash
cd {WORKSPACE}/flask && python -m pytest tests/test_ai_rewrite.py -v
```
Expect: 9 passed, 0 failed.

---

## 5. Tests

Framework: `pytest` (matches `flask/tests/test_project.py`, `flask/modules/chain/tests/test_adapter.py`). Test naming: `condition_expectedOutcome` per architecture principles.

```python
"""Tests for POST /api/ai/text/rewrite — validate, mock-provider smoke, prompt unit, adapter unit.

Run: python -m pytest flask/tests/test_ai_rewrite.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    """Flask test client with CHAIN_PROVIDER=mock set before app creation."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# HTTP endpoint — validation
# ---------------------------------------------------------------------------

def test_validTextAndInstructions_returns200WithEnvelope(client):
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"text": "Hello world", "instructions": "make it formal"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "text" in body, "response must include 'text'"
    assert "latencyMs" in body, "response must include 'latencyMs'"
    assert isinstance(body["latencyMs"], int)
    assert len(body["text"]) > 0


def test_missingTextKey_returns400WithError(client):
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"instructions": "make formal"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    body = json.loads(r.data)
    assert "error" in body


def test_whitespaceOnlyText_returns400(client):
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"text": "   ", "instructions": "expand"}),
        content_type="application/json",
    )
    assert r.status_code == 400


def test_missingInstructions_returns200(client):
    """instructions field is optional — route must not 400 when absent."""
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"text": "Hello world"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "text" in body


def test_emptyJsonBody_returns400(client):
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# HTTP endpoint — mock provider smoke
# ---------------------------------------------------------------------------

def test_mockProvider_textStartsWithMockMarker(client):
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"text": "Some text to rewrite", "instructions": "expand"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["text"].startswith("MOCK["), (
        f"Expected MOCK[ prefix from mock provider, got: {body['text'][:40]}"
    )


# ---------------------------------------------------------------------------
# Prompt function — unit tests (no HTTP, no Flask)
# ---------------------------------------------------------------------------

def test_rewritePrompt_withInstructions_includesTextAndInstructions():
    from modules.ai.prompts.rewrite import rewrite_prompt
    system, prompt = rewrite_prompt("Hello world", "make it formal")
    assert "Hello world" in prompt, "prompt must contain the source text"
    assert "make it formal" in prompt, "prompt must contain the instructions"
    assert len(system) > 0, "system must be non-empty"


def test_rewritePrompt_withoutInstructions_stillIncludesText():
    from modules.ai.prompts.rewrite import rewrite_prompt
    system, prompt = rewrite_prompt("Hello world", "")
    assert "Hello world" in prompt, "prompt must contain the source text even without instructions"
    assert len(system) > 0


# ---------------------------------------------------------------------------
# Adapter unit — rewrite() must not inject builder context
# ---------------------------------------------------------------------------

def test_adapterRewrite_withMock_returnsChainResult(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    from modules.chain.adapter import rewrite
    from modules.chain.types import ChainResult
    result = rewrite("system text", "user prompt")
    assert isinstance(result, ChainResult)
    assert result.text.startswith("MOCK[")
    assert result.latency_ms >= 0


def test_adapterRewrite_noBuilderContext_textExcludesBuilderMarker(monkeypatch):
    """rewrite() must NOT call with_context(). Mock echoes sys[:20]; if
    with_context were called on 'base', effective system would start with
    'base\n\n## BUILDER CO' and the mock text would contain 'BUILDER'.
    """
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    from modules.chain.adapter import rewrite
    result = rewrite("base", "prompt")
    assert "BUILDER" not in result.text, (
        "adapter.rewrite() must not call with_context(); builder context must be absent"
    )
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(chain): add adapter.rewrite() — instruction-driven, no context injection` — `flask/modules/chain/adapter.py`: add `rewrite()` function (10 lines)
2. `feat(ai): wire POST /api/ai/text/rewrite route` — `flask/modules/ai/routes.py`: add `/rewrite` handler using `rewrite_prompt` + `chain_adapter.rewrite`
3. `test(ai): pytest suite for rewrite endpoint — 9 tests` — `flask/tests/test_ai_rewrite.py`: validation, mock smoke, prompt unit, adapter unit

**Deviation logging**: if a step deviates from this guide (e.g. Task 1 already defined `adapter.rewrite()`, or `routes.py` shape differs), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/flask && python -m pytest -q
```

**Expected delta**: N → N+9 passing (9 new tests in `test_ai_rewrite.py`). Zero pre-existing tests broken.

Also run the structural test explicitly to confirm the adapter boundary is intact:
```bash
cd {WORKSPACE}/flask && python -m pytest modules/chain/tests/test_structural.py -v
```
Expect: 1 passed (no provider imports leaked into feature modules).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Revert commit 3 (tests): `git revert <sha3>` — removes test file
  - Revert commit 2 (route): `git revert <sha2>` — removes `/rewrite` handler from routes.py
  - Revert commit 1 (adapter): `git revert <sha1>` — removes `adapter.rewrite()` function
- **Per-branch**: `git reset --hard <pre-task-sha>` [REQUIRES APPROVAL] or delete the feature branch.

---

## 9. Deviations Allowed

- **`flask/modules/ai/` is missing after pre-flight** → Task 1 is incomplete. STOP. Do not create `modules/ai/` here — that is Task 1's scope. Flag to the user.
- **`rewrite_prompt` returns a single string instead of `tuple[str, str]`** → Adapt the route handler call (`system, prompt = rewrite_prompt(...)` → `prompt = rewrite_prompt(...)`; use a hardcoded system string). Log in commit body.
- **`ai_bp` not in `ENABLED_MODULES` after Task 1** → Add `('modules.ai.routes', 'ai_bp')` to `create_app.py` and log as a Task 1 omission in the commit body. This is the only case where `create_app.py` may be touched.
- **Task 1 already defined `adapter.rewrite()`** → Skip Step 1; verify the existing function has no `with_context()` call. Log deviation.
- **Test framework mismatch** → Match the repo convention (`pytest`); translate silently but note in commit body.
- **Side-effect required** (push, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task wires exactly one route using one prompt function. It does not touch the other six endpoints, does not change Angular code, and does not add or validate context loading. All of the following are explicitly deferred — if any of them appear useful during this task, STOP and flag rather than absorbing scope.

- **Context injection** (`builder`, `principles` kwargs on the adapter) — rewrite is intentionally context-free; generate/iterate/generate-spec need it; that's Task 3's scope.
- **Remaining 6 routes** (`/generate`, `/iterate`, `/generate-spec`, `/review`, `/lint-braindump`, `/scan`) — Tasks 3 and 4.
- **Streaming on the rewrite endpoint** — `chain.adapter.stream()` exists but Angular's `ai.service.ts` uses standard HTTP; no SSE consumer exists; ship when a caller exists.
- **Rate limiting** — no usage dashboard, no second product sharing the API; revisit when a second consumer or usage cap is needed.
- **OpenAPI spec update** for `/api/ai/text/rewrite` — no YAML entry exists yet; add when all Phase 2 routes are wired so the spec is updated once.
- **Angular integration test** — the `ai.service.ts` already points at `/api/ai/text/rewrite`; an end-to-end test with the Angular dev server running is deferred to a QA pass after all seven routes land.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)