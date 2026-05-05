# Task 1 — Migrate `iterate` Endpoint

## 1. Context

This task ports `POST /api/ai/text/iterate` from Express to Flask, establishing the four-part module pattern — OpenAPI contract, generated DTO, route handler, proxy entry — that Tasks 2 and 3 will follow verbatim. The `iterate_prompt` function already exists in `modules/ai/prompts/__init__.py:46-52`; the `chain.adapter.generate()` call path is already wired and tested in `modules/chain/adapter.py:41-56`. This task is wiring, not invention: add the OpenAPI schemas, regenerate DTOs, add one route handler, add one proxy entry.

**Trade-offs considered:**
- **`chain_adapter.rewrite()` vs `chain_adapter.generate()`** — `iterate_prompt` manually bakes builder/principles into the system string, so `with_context()` is a no-op either way when called without kwargs. Architecture doc explicitly lists `iterate` as a `generate()` caller; `generate()` is used here for consistency with the declared intent, even though the runtime result is identical.
- **`instruction` as required vs optional field** — Making it required would force callers to send an empty string; optional with `default: ''` matches the `rewrite.instructions` precedent in this codebase and lets callers omit the field cleanly.
- **Proxy entry in this task vs Task 4 batch** — Architecture §proxy says Task 4 batches all four entries, but that leaves `/api/ai/text/iterate` routing to Express during Tasks 1-3 local testing. Adding the proxy entry here keeps the endpoint reachable through `ng serve` immediately, matching Express-parity behavior.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}

git status                                    # flag any unrelated M/?? entries
git diff HEAD -- openapi.yaml \
                 dtos/models.py \
                 modules/ai/routes.py \
                 tests/test_ai_iterate.py \
                 proxy.conf.json              # confirm all target files are clean

python -m pytest -q 2>&1 | tail -5   # record passing count
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: ___/___  passing. (Record this number — the Verification section expects it.)

---

## 3. Files

### To Create (new)
- `tests/test_ai_iterate.py` — route tests for `POST /api/ai/text/iterate`, mirroring `tests/test_ai_rewrite.py`

### To Modify (cite Codebase Context)
- `openapi.yaml` — add `/api/ai/text/iterate` path entry + `IterateRequest`/`IterateResponse` schemas (currently ends at `RewriteResponse`)
- `dtos/models.py` — regenerated via `make generate-dtos`; never hand-edited
- `modules/ai/routes.py` — add `iterate()` handler + extend the `from dtos.models import` line (currently `modules/ai/routes.py:1-32`)
- `proxy.conf.json` — add `/api/ai/text/iterate` entry pointing to Flask 3101 (currently `proxy.conf.json:1-45`)

### To Leave Alone
- `modules/ai/prompts/__init__.py` — `iterate_prompt` already exists at line 46; do not touch
- `modules/chain/adapter.py` — `generate()` already exists; this task adds a caller, not a new function
- `modules/ai/errors.py` — `AIProviderError` already defined; reused unchanged
- `modules/chain/errors.py` — `ProviderError` already defined; reused unchanged
- `tests/test_ai_rewrite.py` — the `allRoutes_importFromDtosModels` structural test checks that `RewriteRequest`/`RewriteResponse` appear in `routes.py`; adding new DTOs to the same import line satisfies it without modification
- `create_app.py` — `ENABLED_MODULES` already includes `modules.ai.routes`; no change needed

---

## 4. Implementation Steps

### Step 1: Add OpenAPI schemas and path entry

**Action**: Append `IterateRequest` and `IterateResponse` to `components/schemas` in `openapi.yaml`, then add the `/api/ai/text/iterate` path entry.

**File**: `openapi.yaml`

**Pattern** — schemas block (append after `RewriteResponse`):
```yaml
    IterateRequest:
      type: object
      required:
        - document
      properties:
        document:
          type: string
          minLength: 1
          description: >
            Document content to iterate on. Whitespace-only values are
            rejected by the server.
        instruction:
          type: string
          default: ''
          description: >
            Optional editing instruction. Empty string means clean/improve
            with no specific directive.

    IterateResponse:
      type: object
      required:
        - text
        - latencyMs
      properties:
        text:
          type: string
        latencyMs:
          type: integer
          minimum: 0
```

**Pattern** — paths block (add alongside `/api/ai/text/rewrite`):
```yaml
  /api/ai/text/iterate:
    post:
      summary: Iterate on a document with an instruction
      operationId: iterateText
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IterateRequest'
      responses:
        '200':
          description: Iterated document text
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IterateResponse'
        '400':
          description: document is empty after whitespace stripping
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '422':
          description: Request validation failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '502':
          description: AI provider error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

**Verify**: `python -c "import yaml; yaml.safe_load(open('openapi.yaml'))"` — expect no output (valid YAML). Do NOT run `make test` yet — `everyOpenapiPath_hasRouteHandler` will fail until the route handler is added in Step 3.

---

### Step 2: Regenerate DTOs

**Action**: Regenerate `dtos/models.py` from the updated `openapi.yaml`.

**File**: `dtos/models.py` (generated — do not hand-edit)

**Pattern**:
```bash
make generate-dtos
```

Expected additions to `dtos/models.py` (appended by codegen, exact field names are codegen output):
```python
class IterateRequest(BaseModel):
    document: constr(min_length=1) = Field(
        ...,
        description='Document content to iterate on...',
    )
    instruction: str | None = Field(
        '',
        description='Optional editing instruction...',
    )


class IterateResponse(BaseModel):
    text: str
    latencyMs: conint(ge=0)
```

**Verify**: `make check-dtos` — expect exit 0 (no diff between committed file and what codegen would produce).

**Commit after this step** — see Commit Plan entry 1.

---

### Step 3: Add `iterate` route handler

**Action**: Extend the imports in `routes.py` to include `IterateRequest`, `IterateResponse`, and `iterate_prompt`, then add the `iterate()` handler below the existing `rewrite()` handler. Port the handler shape from `modules/ai/routes.py:8-31` (the `rewrite` handler).

**File**: `modules/ai/routes.py`

**Pattern**:
```python
# extend existing import lines:
from dtos.models import RewriteRequest, RewriteResponse, IterateRequest, IterateResponse
from modules.ai.prompts import rewrite_prompt, iterate_prompt

# add after the rewrite() handler, removing the "# Route handlers registered in tasks 3–4" comment:
@ai_bp.post("/iterate")
def iterate():
    req = IterateRequest.model_validate(request.get_json(force=True, silent=False) or {})
    document = req.document.strip()
    instruction = (req.instruction or "").strip()
    if not document:
        return jsonify({"error": "document is required"}), 400
    system, prompt = iterate_prompt(instruction, document, "", "")
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = IterateResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502
```

**Verify**: `python -m pytest tests/test_ai_rewrite.py -v -q` — all existing rewrite tests pass. The `everyOpenapiPath_hasRouteHandler` test now has `/api/ai/text/iterate` registered on both sides — it should pass.

**Commit after this step** — see Commit Plan entry 2.

---

### Step 4: Add proxy entry

**Action**: Add `/api/ai/text/iterate` to `proxy.conf.json`, pointing to Flask 3101.

**File**: `proxy.conf.json` (currently `proxy.conf.json:1-45`)

**Pattern** — insert before the existing `/api/ai/text/rewrite` entry (or alongside it; order within the JSON object does not affect routing):
```json
  "/api/ai/text/iterate": {
    "target": "http://localhost:3101",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "info"
  },
```

**Verify**: `node -e "JSON.parse(require('fs').readFileSync('proxy.conf.json','utf8'))"` — expect no output (valid JSON).

---

### Step 5: Write route tests

**Action**: Create `tests/test_ai_iterate.py`. Mirror the structure of `tests/test_ai_rewrite.py` — a local `client` fixture with `CHAIN_PROVIDER=mock`, validation cases, mock-provider smoke, prompt unit calls, and the ProviderError → 502 path. (Ported from `tests/test_ai_rewrite.py`.)

**File**: `tests/test_ai_iterate.py` (new)

See Section 5 for the complete file.

**Verify**: `python -m pytest tests/test_ai_iterate.py -v` — all tests in the new file pass.

**Commit after this step** — see Commit Plan entry 3.

---

## 5. Tests

Complete file — `tests/test_ai_iterate.py`:

```python
"""Tests for POST /api/ai/text/iterate — validate, mock-provider smoke, prompt unit, error handling.

Run: python -m pytest tests/test_ai_iterate.py -v
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

def validDocumentAndInstruction_returns200WithEnvelope(client):
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": "# My Spec\n\nSection.", "instruction": "Add a timeline section"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "text" in body, "response must include 'text'"
    assert "latencyMs" in body, "response must include 'latencyMs'"
    assert isinstance(body["latencyMs"], int)
    assert len(body["text"]) > 0


def missingDocument_returns422(client):
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"instruction": "Add a section"}),
        content_type="application/json",
    )
    assert r.status_code == 422
    body = json.loads(r.data)
    assert "error" in body


def whitespaceOnlyDocument_returns400(client):
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": "   ", "instruction": "improve"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    body = json.loads(r.data)
    assert "error" in body


def missingInstruction_returns200(client):
    """instruction is optional — route must not 400 when absent."""
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": "# Spec content"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "text" in body


def emptyJsonBody_returns422(client):
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 422
    body = json.loads(r.data)
    assert "error" in body


def nonStringDocument_returns422(client):
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": 42, "instruction": "expand"}),
        content_type="application/json",
    )
    assert r.status_code == 422, "Pydantic ValidationError must surface as 422, not 400 or 500"
    body = json.loads(r.data)
    assert "error" in body


# ---------------------------------------------------------------------------
# HTTP endpoint — mock provider smoke
# ---------------------------------------------------------------------------

def mockProvider_textStartsWithMockMarker(client):
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": "# Spec", "instruction": "Add a risks section"}),
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

def iteratePrompt_withInstruction_instructionAppearsInPrompt():
    from modules.ai.prompts import iterate_prompt
    _, prompt = iterate_prompt("Add a timeline section", "# Spec\n\nContent.", "", "")
    assert "Add a timeline section" in prompt, "instruction must appear in the user prompt"


def iteratePrompt_withDocument_documentAppearsInPrompt():
    from modules.ai.prompts import iterate_prompt
    _, prompt = iterate_prompt("", "# Current document body", "", "")
    assert "# Current document body" in prompt, "document must appear in the user prompt"


def iteratePrompt_emptyInstruction_systemNonEmpty():
    from modules.ai.prompts import iterate_prompt
    system, prompt = iterate_prompt("", "# Doc", "", "")
    assert len(system) > 0, "system prompt must be non-empty even when instruction is empty"
    assert "# Doc" in prompt


# ---------------------------------------------------------------------------
# Error handling — ProviderError -> AIProviderError -> 502
# ---------------------------------------------------------------------------

def providerError_iterate_returns502WithStatusEnvelope(monkeypatch):
    """ProviderError from chain adapter -> AIProviderError -> 502 with status envelope."""
    from modules.chain.errors import ProviderError

    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    import sys
    for mod in list(sys.modules.keys()):
        if "modules.chain.adapter" in mod or "modules.ai.routes" in mod:
            del sys.modules[mod]

    def raise_provider_error(system, prompt, **kwargs):
        raise ProviderError("Rate limited", status_code=503)

    monkeypatch.setattr("modules.chain.adapter.generate", raise_provider_error)

    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        r = c.post(
            "/api/ai/text/iterate",
            data=json.dumps({"document": "# Spec", "instruction": "expand"}),
            content_type="application/json",
        )
    assert r.status_code == 502
    body = json.loads(r.data)
    assert "error" in body, "502 response must include 'error' key"
    assert body.get("status") == 502, "502 response must include status: 502"
    assert "Rate limited" in body["error"], "error message must preserve ProviderError message"
```

---

## 6. Commit Plan

**Executor instruction**: commit after each step as listed. Do not batch at the end. Each commit boundary is listed with the files it contains.

1. `feat(ai): add IterateRequest/IterateResponse to OpenAPI contract and regenerate DTOs` — after Steps 1 + 2 — files: `openapi.yaml`, `dtos/models.py`
2. `feat(ai): add POST /api/ai/text/iterate route handler and proxy entry` — after Steps 3 + 4 — files: `modules/ai/routes.py`, `proxy.conf.json`
3. `test(ai): add iterate endpoint tests` — after Step 5 — files: `tests/test_ai_iterate.py`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

**Note on test stability between commits**: `everyOpenapiPath_hasRouteHandler` in `tests/test_ai_rewrite.py` will fail between commit 1 and commit 2 (openapi has the path; Flask does not yet). Do not run `make test` between those two commits. Per-step verify commands (YAML parse, `make check-dtos`) are safe to run after commit 1.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/flask && python -m pytest -q
```

**Expected delta**: baseline (recorded during pre-flight) → baseline + 11 passing. Zero pre-existing tests broken.

The `everyOpenapiPath_hasRouteHandler` test in `tests/test_ai_rewrite.py` must pass — it confirms `/api/ai/text/iterate` is declared in `openapi.yaml` and registered in Flask's url map.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` in reverse order (commit 3 → 2 → 1) restores pre-task state.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch, or delete and recreate from the base commit.
- **DTO rollback**: `git checkout HEAD -- dtos/models.py` restores the last committed generated file; `make check-dtos` confirms it matches `openapi.yaml`.

---

## 9. Deviations Allowed

- **`datamodel-codegen` output field names differ from expected** — the generated field types (`constr`, `conint`, `Field(...)`) may differ slightly across codegen versions; accept whatever codegen produces as long as `make check-dtos` exits 0 and the route handler compiles without import errors.
- **`iterate_prompt` argument order** — if the existing function signature differs from what this guide assumes (`base_spec`, `current_content`, `builder`, `principles`), read `modules/ai/prompts/__init__.py:46-52` directly and adapt the call site; log the deviation in the commit body.
- **`everyOpenapiPath_hasRouteHandler` expects `{id}` param syntax** — the structural test converts Flask `<id>` to `{id}` via regex before comparing; the iterate path has no path params, so no conversion is needed. If the test fails for a different reason, read its assertion message and fix the openapi path string.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log it in the commit body.
- **Side-effect required** (push, publish, schema change, drop) — STOP, mark `[REQUIRES APPROVAL]`, and flag before proceeding.

---

## 10. Out of Scope

This task establishes the module pattern for `iterate` only — no other endpoints, no UI changes, and no context injection beyond what the prompt function already supports. The route returns buffered (non-streaming) text, matching Express behavior. Builder and principles context fields are wired to empty strings in the route; they are supported by `iterate_prompt` but are not exposed in the DTO until a consuming feature demonstrates the need.

- **Wiring `builder`/`principles` from context module into the iterate DTO** — deferred; zero callers need it today; add when a real consumer pulls builder context through this endpoint
- **Streaming response for iterate** — deferred; Express served this buffered; streaming is a separate feature decision that does not belong in a parity migration
- **Tasks 2–4 endpoints** (`lint-braindump`, `review`, `generate-spec`) — follow this guide as the pattern; do not start them in this task
- **Express fallback removal from `proxy.conf.json`** — deferred to Task 5; the `/api` fallback entry remains until all four endpoints are confirmed

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale
- [Epic](./epic.md) — task scope and ordering
- [Timeline](./timeline.md) — update status to `in-progress` when starting, `done` when verification passes