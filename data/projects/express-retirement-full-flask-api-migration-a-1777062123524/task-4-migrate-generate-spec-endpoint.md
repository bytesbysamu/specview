# Task 4: Migrate `generate-spec` Endpoint

## 1. Context

`POST /api/ai/text/generate-spec` is the last AI endpoint still served by Express. It accepts a brain dump, injects builder profile and principles via `generate_spec_prompt()`, calls Claude, and returns raw text containing `===FILE: filename===` markers that the Angular `new-project` component splits into individual spec files. The Angular parser expects the raw marker text directly — no JSON wrapping of the content string. The Flask route is a passthrough: validate input, load context, build prompt, call `chain_adapter.generate()`, return `{text, latencyMs}` where `text` is Claude's output verbatim. The proxy entry ships in the same commit as the Flask route; until both land, Angular still hits Express for this path.

**Trade-offs considered:**
- **Pass `builder`/`principles` to `chain_adapter.generate()` and let `with_context` inject them** — rejected because `generate_spec_prompt()` already injects them into the system string; passing them again would double-inject and is inconsistent with how the prompt function was designed.
- **Use `chain_adapter.rewrite()` since context is pre-injected** — rejected on semantics; `generate()` is the correct call for new-content generation, and calling it with empty `builder`/`principles` is a documented no-op in `with_context`.
- **Call `chain_adapter.generate(system, prompt)` with defaults (empty builder/principles), after `generate_spec_prompt` pre-injects** — chosen: correct semantics, no double injection, consistent with the adapter contract.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}                                        # repo root: ~/Projects/2026/spec-doc
git status                                            # flag any M or ?? on target files
git diff HEAD -- openapi.yaml dtos/models.py modules/ai/routes.py tests/test_ai_rewrite.py proxy.conf.json
python -m pytest --tb=short -q 2>&1 | tail -5   # record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: [record N]/[N] passing before editing.

---

## 3. Files

### To Create (new)
- `tests/test_ai_generate_spec.py` — HTTP endpoint tests, prompt unit tests, and error-handling tests for `POST /api/ai/text/generate-spec`

### To Modify (cite CODEBASE CONTEXT)
- `openapi.yaml` — add `GenerateSpecRequest` and `GenerateSpecResponse` schemas to `components.schemas`; add `/api/ai/text/generate-spec` path entry
- `dtos/models.py` — regenerated artifact; never hand-edited; regenerated via `make generate-dtos` after `openapi.yaml` changes; committed because this repo tracks the generated file
- `modules/ai/routes.py` — currently has only `rewrite` handler and a placeholder comment; add `generate_spec` handler below the comment
- `tests/test_ai_rewrite.py:221` — `allRoutes_importFromDtosModels` expected dict currently declares only `["RewriteRequest", "RewriteResponse"]` for `modules/ai/routes.py`; extend to include `GenerateSpecRequest` and `GenerateSpecResponse`
- `proxy.conf.json` — currently has six explicit Flask entries and one Express fallback; add `/api/ai/text/generate-spec` entry pointing to `:3101` before the fallback

### To Leave Alone
- `modules/ai/prompts/__init__.py` — `generate_spec_prompt()` is fully implemented at line 69; no changes needed
- `modules/chain/adapter.py` — `generate()` is the correct function; adapter is unchanged
- `modules/context/service.py` — `read_context(key)` is the correct way to load `builder` and `principles`; unchanged
- `modules/ai/errors.py` — `AIProviderError` is already defined; unchanged
- `create_app.py` — `ai_bp` is already registered; unchanged

---

## 4. Implementation Steps

### Step 1: Add OpenAPI Schema Entries

**Action**: Insert two new schema definitions and one new path entry into `openapi.yaml`. Schemas go in `components.schemas` after `RewriteResponse`; path goes after `/api/ai/text/rewrite`.

**File**: `openapi.yaml`

**Pattern** — schemas (insert after `RewriteResponse` block, before the `responses:` block):
```yaml
    GenerateSpecRequest:
      type: object
      required: [input]
      properties:
        input:
          type: string
          minLength: 1
          description: Brain dump text. Whitespace-only values are rejected by the server.

    GenerateSpecResponse:
      type: object
      required: [text, latencyMs]
      properties:
        text:
          type: string
          description: >
            Raw multi-file output with ===FILE: filename=== markers. Not JSON-wrapped.
            The Angular parser splits on this exact string; wrapping breaks the parser.
        latencyMs:
          type: integer
          minimum: 0
```

**Pattern** — path entry (insert after the `/api/ai/text/rewrite` block, before `components:`):
```yaml
  /api/ai/text/generate-spec:
    post:
      summary: Generate specification documents from a brain dump
      operationId: generateSpec
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenerateSpecRequest'
      responses:
        '200':
          description: Raw multi-file spec text with ===FILE: filename=== markers
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GenerateSpecResponse'
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '502':
          description: Upstream AI provider failure
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

**Verify**: `python -c "import yaml; yaml.safe_load(open('openapi.yaml'))" && echo "valid YAML"` — expect `valid YAML` with no exception.

---

### Step 2: Regenerate DTOs

**Action**: Run `make generate-dtos` from `` to regenerate `dtos/models.py` from the updated `openapi.yaml`. Do NOT hand-edit `dtos/models.py`.

**File**: `dtos/models.py` — regenerated; do not edit

**Pattern**:
```bash
make generate-dtos
```

**Verify**: `grep -q "GenerateSpecRequest\|GenerateSpecResponse" dtos/models.py && echo "DTOs present"` — expect `DTOs present`. If the grep fails, the `openapi.yaml` schema section was not added correctly — re-check Step 1 before continuing.

---

### Step 3: Add Route Handler

**Action**: Add `generate_spec` route handler to `modules/ai/routes.py`. Replace the placeholder comment with the handler. Extend the `import` line from `dtos.models` to include the new DTOs. Add `generate_spec_prompt` and `read_context` imports.

**File**: `modules/ai/routes.py`

**Pattern** — full file after changes:
```python
from flask import Blueprint, request, jsonify

from dtos.models import RewriteRequest, RewriteResponse, GenerateSpecRequest, GenerateSpecResponse
from modules.chain import adapter as chain_adapter
from modules.chain.errors import ProviderError
from modules.ai.prompts import rewrite_prompt, generate_spec_prompt
from modules.context.service import read_context
from .errors import AIProviderError

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai/text")


@ai_bp.post("/rewrite")
def rewrite():
    req = RewriteRequest.model_validate(request.get_json(force=True, silent=False) or {})
    text = req.text.strip()
    instructions = (req.instructions or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    system, prompt = rewrite_prompt(text, instructions)
    try:
        try:
            result = chain_adapter.rewrite(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = RewriteResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


@ai_bp.post("/generate-spec")
def generate_spec():
    req = GenerateSpecRequest.model_validate(request.get_json(force=True, silent=False) or {})
    input_text = req.input.strip()
    if not input_text:
        return jsonify({"error": "input is required"}), 400
    builder = read_context("builder")
    principles = read_context("principles")
    system, prompt = generate_spec_prompt(input_text, builder, principles)
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = GenerateSpecResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502
```

**Verify**: `python -c "from modules.ai.routes import ai_bp; print('import OK')"` — expect `import OK`. If a `NameError` or `ImportError` occurs on `GenerateSpecRequest`/`GenerateSpecResponse`, `make generate-dtos` was not run — return to Step 2.

---

### Step 4: Update Structural Test

**Action**: Extend the `allRoutes_importFromDtosModels` expected dict in `tests/test_ai_rewrite.py` to include `GenerateSpecRequest` and `GenerateSpecResponse` for `modules/ai/routes.py`. This pins the contract: future commits that remove the DTO import will fail the structural test.

**File**: `tests/test_ai_rewrite.py:221`

**Pattern** — change this line:
```python
    "modules/ai/routes.py":       ["RewriteRequest", "RewriteResponse"],
```
to:
```python
    "modules/ai/routes.py":       ["RewriteRequest", "RewriteResponse", "GenerateSpecRequest", "GenerateSpecResponse"],
```

**Verify**: `CHAIN_PROVIDER=mock python -m pytest tests/test_ai_rewrite.py::allRoutes_importFromDtosModels tests/test_ai_rewrite.py::everyOpenapiPath_hasRouteHandler -v` — both structural tests must pass. `everyOpenapiPath_hasRouteHandler` validates that the new path exists in both `openapi.yaml` and Flask's `url_map`.

---

### Step 5: Add Proxy Entry

**Action**: Insert a new entry for `/api/ai/text/generate-spec` in `proxy.conf.json`, pointing to Flask at `:3101`. Insert it immediately after the `/api/ai/text/rewrite` entry, before the Express fallback `/api` entry. JSON must remain valid after the edit.

**File**: `proxy.conf.json`

**Pattern** — insert this block after the closing `}` of `/api/ai/text/rewrite`:
```json
  "/api/ai/text/generate-spec": {
    "target": "http://localhost:3101",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "info"
  },
```

**Verify**: `python -c "import json; d = json.load(open('proxy.conf.json')); assert '/api/ai/text/generate-spec' in d; print('proxy OK')"` — expect `proxy OK`.

**Commit now** (Steps 1–5 are one logical unit; all five files must land together for structural tests to pass and Angular routing to be correct):

```
git add openapi.yaml dtos/models.py modules/ai/routes.py tests/test_ai_rewrite.py proxy.conf.json
git commit
```

See Commit Plan for the message.

---

### Step 6: Write Tests

**Action**: Create `tests/test_ai_generate_spec.py` with HTTP endpoint tests, prompt unit tests, and error-handling tests. Match the naming convention from `tests/test_ai_rewrite.py`: `condition_expectedOutcome`, no `test_` prefix, `_` separator between camelCase condition and outcome.

**File**: `tests/test_ai_generate_spec.py` (new)

See Section 5 for the complete file.

**Verify**: `CHAIN_PROVIDER=mock python -m pytest tests/test_ai_generate_spec.py -v` — all tests in the new file pass.

---

## 5. Tests

```python
# tests/test_ai_generate_spec.py
"""Tests for POST /api/ai/text/generate-spec.

Covers: HTTP validation, mock-provider smoke, prompt unit, error handling.
Run: python -m pytest tests/test_ai_generate_spec.py -v
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

def validInput_returns200WithEnvelope(client):
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": "A SaaS app for tracking daily habits"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "text" in body, "response must include 'text'"
    assert "latencyMs" in body, "response must include 'latencyMs'"
    assert isinstance(body["latencyMs"], int)
    assert len(body["text"]) > 0


def missingInputKey_returns422(client):
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 422
    body = json.loads(r.data)
    assert "error" in body


def whitespaceOnlyInput_returns400(client):
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": "   "}),
        content_type="application/json",
    )
    assert r.status_code == 400
    body = json.loads(r.data)
    assert "error" in body


def nonStringInput_returns422(client):
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": 123}),
        content_type="application/json",
    )
    assert r.status_code == 422
    body = json.loads(r.data)
    assert "error" in body


# ---------------------------------------------------------------------------
# HTTP endpoint — mock provider smoke
# ---------------------------------------------------------------------------

def mockProvider_responseTextStartsWithMockMarker(client):
    """Mock provider echoes system[:20]; confirms CHAIN_PROVIDER=mock is active."""
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": "My product brain dump"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["text"].startswith("MOCK["), (
        f"Expected MOCK[ prefix from mock provider; got: {body['text'][:40]!r}"
    )


def mockProvider_responseTextIsPlainString_notJsonWrapped(client):
    """generate-spec returns text verbatim — no JSON wrapping — so Angular parser
    can split on ===FILE: markers. body['text'] must be a plain string, not a dict."""
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": "My product brain dump"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["text"], str), (
        "text field must be a plain string; JSON-wrapping the content would break "
        "the Angular parser's ===FILE: marker splitting"
    )


# ---------------------------------------------------------------------------
# Prompt function — unit tests (no HTTP, no Flask)
# ---------------------------------------------------------------------------

def generateSpecPrompt_inputBecomesUserPromptVerbatim():
    from modules.ai.prompts import generate_spec_prompt
    _, prompt = generate_spec_prompt("my brain dump text", "", "")
    assert prompt == "my brain dump text", (
        "user prompt must be the raw input text; route passes it to Claude unchanged"
    )


def generateSpecPrompt_systemContainsFileMarkerInstruction():
    from modules.ai.prompts import generate_spec_prompt
    system, _ = generate_spec_prompt("x", "", "")
    assert "===FILE:" in system, "system must contain ===FILE: to enforce the marker format"


def generateSpecPrompt_withBuilder_embedsBuilderInSystem():
    from modules.ai.prompts import generate_spec_prompt
    system, _ = generate_spec_prompt("x", "I am a solo founder", "")
    assert "I am a solo founder" in system
    assert "Builder Profile" in system


def generateSpecPrompt_withPrinciples_embedsPrinciplesInSystem():
    from modules.ai.prompts import generate_spec_prompt
    system, _ = generate_spec_prompt("x", "", "ship fast, validate first")
    assert "ship fast, validate first" in system
    assert "Principles" in system


def generateSpecPrompt_emptyBuilder_omitsBuilderProfileSection():
    from modules.ai.prompts import generate_spec_prompt
    system, _ = generate_spec_prompt("x", "", "")
    assert "Builder Profile" not in system, (
        "empty builder must not inject a Builder Profile section into the system prompt"
    )


def generateSpecPrompt_emptyPrinciples_omitsPrinciplesSection():
    from modules.ai.prompts import generate_spec_prompt
    system, _ = generate_spec_prompt("x", "", "")
    assert "Principles" not in system, (
        "empty principles must not inject a Principles section into the system prompt"
    )


# ---------------------------------------------------------------------------
# Error handling — ProviderError → AIProviderError → 502
# ---------------------------------------------------------------------------

def providerError_generateSpec_returns502WithStatusEnvelope(monkeypatch):
    """ProviderError from chain adapter -> AIProviderError -> 502 with {error, status} envelope."""
    from modules.chain.errors import ProviderError

    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    # Purge cached modules so monkeypatch.setenv takes effect on import
    import sys as _sys
    for mod in list(_sys.modules.keys()):
        if "modules.chain.adapter" in mod or "modules.ai.routes" in mod:
            del _sys.modules[mod]

    def raise_provider_error(system, prompt, **kwargs):
        raise ProviderError("Rate limited", status_code=503)

    monkeypatch.setattr("modules.chain.adapter.generate", raise_provider_error)

    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        r = c.post(
            "/api/ai/text/generate-spec",
            data=json.dumps({"input": "My product brain dump"}),
            content_type="application/json",
        )
    assert r.status_code == 502
    body = json.loads(r.data)
    assert "error" in body, "502 response must include 'error' key"
    assert body.get("status") == 502, "502 response must include status: 502"
    assert "Rate limited" in body["error"], "error message must preserve ProviderError.message"
```

---

## 6. Commit Plan

**Executor instruction**: Steps 1–5 are one logical unit — the structural test `everyOpenapiPath_hasRouteHandler` fails if OpenAPI and the Flask route are in separate commits. Commit all five files together after Step 5 passes its verify command, then commit tests separately after Step 6.

**Commit 1** — after Steps 1–5 verify commands pass:
```
feat(ai): port generate-spec to Flask, wire proxy

- Add GenerateSpecRequest/GenerateSpecResponse schemas to openapi.yaml
- Regenerate dtos/models.py (GenerateSpecRequest, GenerateSpecResponse)
- Add generate_spec route handler to modules/ai/routes.py
- Extend allRoutes_importFromDtosModels structural test to pin new DTOs
- Add /api/ai/text/generate-spec proxy entry to proxy.conf.json

Angular parser contract: text is returned verbatim (no JSON wrapping);
===FILE: markers are preserved unchanged. Prompt function (generate_spec_prompt)
injects builder/principles into the system prompt; adapter.generate() is called
with default empty builder/principles to avoid double-injection.

Files: openapi.yaml, dtos/models.py, modules/ai/routes.py,
       tests/test_ai_rewrite.py, proxy.conf.json
```

**Commit 2** — after all tests in `test_ai_generate_spec.py` pass:
```
test(ai): add generate-spec HTTP and prompt unit tests

HTTP validation, mock-provider smoke, prompt unit tests, and ProviderError → 502
error-handling test. Naming convention: condition_expectedOutcome (no test_ prefix).

Files: tests/test_ai_generate_spec.py
```

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
CHAIN_PROVIDER=mock python -m pytest --tb=short -q
```

**Expected delta**: baseline N → N+9 passing (9 new tests in `test_ai_generate_spec.py`). Zero pre-existing tests broken. The two structural tests (`everyOpenapiPath_hasRouteHandler` and `allRoutes_importFromDtosModels`) must both remain green.

**Acceptance test** (behavioral — required before marking task done): start Flask (`make dev`) and the Angular dev server (`npm start`), submit a brain dump via the Angular `new-project` component, and confirm the response is split into four spec files. If the Angular UI shows the files, the `===FILE:` marker contract is intact.

---

## 8. Rollback

**Per-step**: each commit is independently revertible.
```bash
git revert <sha>   # reverts one commit cleanly; no manual cleanup needed
```

**Per-branch**: if verification fails catastrophically after Commit 1:
```bash
git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — discards both commits
make generate-dtos                # restore dtos/models.py to pre-task state
```

---

## 9. Deviations Allowed

- **`GenerateSpecRequest` or `GenerateSpecResponse` not generated by `make generate-dtos`** — the schema section names must match exactly; verify Step 1's YAML indentation is correct (2-space, aligned with `RewriteRequest`) and re-run Step 2.
- **`read_context` import path differs** — if `from modules.context.service import read_context` fails, check `modules/context/service.py` exists; the function signature is `read_context(key: str) -> str` with keys `"builder"` and `"principles"`.
- **`ProviderError` has no `.message` attribute** — inspect `modules/chain/errors.py` and match the attribute name used in the existing `rewrite` handler; adapt the `generate_spec` handler to match.
- **`make generate-dtos` fails with `datamodel-codegen missing`** — install via `pip install datamodel-code-generator` (dev dependency); if `requirements-dev.txt` lists it under a different name, use that package name. Do not hand-edit `dtos/models.py`.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log the deviation in the commit body.
- **Side effect required** (push, drop, publish) — STOP, mark `[REQUIRES APPROVAL]`, and ask.

---

## 10. Out of Scope

This task ports the `generate-spec` endpoint to Flask with behavioral parity to Express and wires the proxy. It does not modify the Angular client, the prompt content, or the context loading mechanism. The Express fallback entry (`/api` → `:3100`) remains until Task 5 — removing it here would cut off any remaining Express-only paths before they are confirmed migrated.

- **Express fallback removal** — deferred to Task 5; removing it before all endpoints are migrated would silently 404 any unported paths
- **Streaming the generate-spec response** — Express served this buffered; Flask matches that behavior; streaming is a separate feature decision not scoped to this migration
- **Angular parser changes** — the `===FILE: filename===` split logic in `new-project.component.ts` is unchanged; this task preserves the wire format, not modifies it
- **Shared fence-stripping or JSON-extraction utilities** — `generate-spec` has no JSON parsing; no shared utility applies here; deferred if a second consumer ever needs it
- **`generate` endpoint (generic generation)** — `POST /api/ai/text/generate` is Phase 2 work per the Epic; do not absorb it here

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for atomic proxy + route commits and passthrough contract
- [Epic](./epic.md) — Task scope and parallel/serial dependencies
- [Timeline](./timeline.md) — Update status to ✅ after Verification passes