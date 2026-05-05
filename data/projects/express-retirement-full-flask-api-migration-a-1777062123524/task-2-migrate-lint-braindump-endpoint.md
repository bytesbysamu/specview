# Implementation Guide: Task 2 — Migrate `lint-braindump` Endpoint

## 1. Context

Ports `POST /api/ai/text/lint-braindump` from Express to Flask. `lint_braindump_prompt` already exists in `modules/ai/prompts/__init__.py` as a pure function returning `(system, prompt)`. The route validates a `LintBraindumpRequest` DTO, calls `chain_adapter.generate()`, parses the JSON response inline, and returns a typed `LintBraindumpResponse` with `{ready: bool, flags: list}`. All wiring — no new infrastructure.

**Trade-offs considered:**
- Shared JSON parsing helper — rejected; one consumer; second consumer is the trigger (architecture decision, Design Decisions table)
- Fence-stripping on Claude's output — deferred; `_LINT_SYSTEM` explicitly prohibits markdown fences; add only when production evidence shows Claude ignoring it
- Using `chain_adapter.rewrite()` — rejected; `rewrite()` is for instruction-driven text transformation; `generate()` is correct for analysis that produces its own structured output

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status
git diff HEAD -- modules/ai/routes.py openapi.yaml dtos/models.py proxy.conf.json
python -m pytest --tb=no -q          # Record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: [N]/[N] passing.

---

## 3. Files

### To Create (new)
- `tests/test_lint_braindump_route.py` — six route tests covering happy path, validation, provider error, and parse failure
- `tests/conftest.py` — Flask test client fixture; create if absent; if it exists and already has a `client` fixture, do not duplicate it

### To Modify (cite CODEBASE CONTEXT)
- `openapi.yaml` — add `LintBraindumpFlag`, `LintBraindumpRequest`, `LintBraindumpResponse` schemas + `/api/ai/text/lint-braindump` path entry
- `dtos/models.py` — regenerate via `make generate-dtos`; never edit by hand
- `modules/ai/routes.py` — add `import json`, new DTO imports, `lint_braindump_prompt` import, and `lint_braindump()` handler
- `proxy.conf.json` — add `/api/ai/text/lint-braindump` entry targeting `http://localhost:3101`

### To Leave Alone
- `modules/ai/prompts/__init__.py` — `lint_braindump_prompt` already exists and is correct; do not touch
- `modules/chain/adapter.py` — gains a new caller; is not modified
- `create_app.py` — error handling already registered; do not modify
- `modules/ai/errors.py` — `AIProviderError` already exists and is used by the existing `rewrite` handler; do not modify

---

## 4. Implementation Steps

### Step 1: Add schemas and path to `openapi.yaml`

**Action**: Add three schema definitions to `components/schemas` (insert after `HealthResponse`, before `ProjectCreateRequest` — alphabetical order). Add the path entry after `/api/ai/text/rewrite`.

**File**: `openapi.yaml`

**Pattern** — schemas block additions:
```yaml
    LintBraindumpFlag:
      type: object
      required: [severity, message]
      properties:
        severity:
          type: string
          enum: [error, warning, info]
        message:
          type: string

    LintBraindumpRequest:
      type: object
      required: [braindump]
      properties:
        braindump:
          type: string
          minLength: 1
          description: Brain dump text to analyse for spec readiness.

    LintBraindumpResponse:
      type: object
      required: [ready, flags]
      properties:
        ready:
          type: boolean
        flags:
          type: array
          items:
            $ref: '#/components/schemas/LintBraindumpFlag'
```

**Pattern** — paths block addition (after `/api/ai/text/rewrite`):
```yaml
  /api/ai/text/lint-braindump:
    post:
      summary: Analyse a brain dump for spec readiness
      operationId: lintBraindump
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LintBraindumpRequest'
      responses:
        '200':
          description: Readiness assessment
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LintBraindumpResponse'
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '502':
          description: Upstream AI provider failure or JSON parse failure
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

**Verify**: `python3 -c "import yaml; yaml.safe_load(open('openapi.yaml')); print('OK')"` — expect `OK` with no output.

---

### Step 2: Regenerate DTOs

**Action**: Regenerate `dtos/models.py` from the updated YAML. Never edit this file manually.

**File**: `dtos/models.py` (generated)

**Pattern**:
```bash
make generate-dtos
```

**Verify**: `grep -c "LintBraindump" dtos/models.py` — expect `3` (one line each for `LintBraindumpFlag`, `LintBraindumpRequest`, `LintBraindumpResponse`).

---

### Step 3: Add route handler to `modules/ai/routes.py`

**Action**: Add `import json` at the top. Extend the existing `from dtos.models import ...` line to include `LintBraindumpRequest, LintBraindumpResponse`. Extend the `from modules.ai.prompts import ...` line to include `lint_braindump_prompt`. Add the handler after `rewrite()`. Pattern mirrors the existing `rewrite` handler exactly: validate DTO → call adapter → parse inline → return typed response.

**File**: `modules/ai/routes.py`

**Pattern** — full file after changes (26 lines for the new handler):
```python
import json

from flask import Blueprint, request, jsonify

from dtos.models import RewriteRequest, RewriteResponse, LintBraindumpRequest, LintBraindumpResponse
from modules.chain import adapter as chain_adapter
from modules.chain.errors import ProviderError
from modules.ai.prompts import rewrite_prompt, lint_braindump_prompt
from .errors import AIProviderError

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai/text")


@ai_bp.post("/rewrite")
def rewrite():
    # ... unchanged ...


@ai_bp.post("/lint-braindump")
def lint_braindump():
    req = LintBraindumpRequest.model_validate(request.get_json(force=True, silent=False) or {})
    braindump = req.braindump.strip()
    if not braindump:
        return jsonify({"error": "braindump is required"}), 400
    system, prompt = lint_braindump_prompt(braindump)
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        try:
            parsed = json.loads(result.text)
        except (ValueError, KeyError) as exc:
            raise AIProviderError("lint_braindump_parse_failed") from exc
        response = LintBraindumpResponse(
            ready=parsed["ready"],
            flags=parsed.get("flags", []),
        )
        return jsonify(response.model_dump(mode="json"))
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502
```

Note: `mode="json"` on `model_dump` ensures the `severity` enum in `LintBraindumpFlag` serializes to its string value (`"error"`, `"warning"`, `"info"`) rather than the enum instance.

**Verify**: `python3 -c "from modules.ai.routes import ai_bp; print('OK')"` — expect `OK`.

---

### Step 4: Update `proxy.conf.json`

**Action**: Add the `/api/ai/text/lint-braindump` entry after the existing `/api/ai/text/rewrite` entry. Same shape, same target.

**File**: `proxy.conf.json`

**Pattern** — insert this block after `/api/ai/text/rewrite`:
```json
  "/api/ai/text/lint-braindump": {
    "target": "http://localhost:3101",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "info"
  },
```

**Verify**: `python3 -c "import json; json.load(open('proxy.conf.json')); print('OK')"` — expect `OK`.

---

### Step 5: Write route tests

**Action**: Check whether `tests/conftest.py` exists and has a `client` fixture. If absent, create it. Then create `tests/test_lint_braindump_route.py` with six tests. Naming convention matches `modules/ai/tests/test_prompts.py` — no `test_` prefix; underscored names are collected via `python_functions = ["*_*"]` in pytest config.

**File**: `tests/conftest.py` (create if absent)

```python
# tests/conftest.py
import os
import pytest

os.environ.setdefault("CHAIN_PROVIDER", "mock")

from create_app import create_app  # noqa: E402 — env var must be set before import


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    return app.test_client()
```

**File**: `tests/test_lint_braindump_route.py` (new)

```python
# tests/test_lint_braindump_route.py
import json
import pytest

from modules.chain import adapter as chain_adapter
from modules.chain.types import ChainResult

_FLAGS_RESPONSE = json.dumps({
    "ready": False,
    "flags": [{"severity": "error", "message": "Missing target audience"}],
})

_READY_RESPONSE = json.dumps({
    "ready": True,
    "flags": [],
})


def validBraindump_returnsReadyFalseWithFlags(client, monkeypatch):
    monkeypatch.setattr(
        chain_adapter,
        "generate",
        lambda system, prompt, **kw: ChainResult(text=_FLAGS_RESPONSE, latency_ms=10),
    )
    rv = client.post(
        "/api/ai/text/lint-braindump",
        json={"braindump": "build a task manager app for teams"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ready"] is False
    assert len(data["flags"]) == 1
    assert data["flags"][0]["severity"] == "error"
    assert data["flags"][0]["message"] == "Missing target audience"


def completeBraindump_returnsReadyTrueEmptyFlags(client, monkeypatch):
    monkeypatch.setattr(
        chain_adapter,
        "generate",
        lambda system, prompt, **kw: ChainResult(text=_READY_RESPONSE, latency_ms=5),
    )
    rv = client.post(
        "/api/ai/text/lint-braindump",
        json={"braindump": "complete well-specified product brief with scope and users"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ready"] is True
    assert data["flags"] == []


def missingBraindumpField_returns422(client):
    rv = client.post("/api/ai/text/lint-braindump", json={})
    assert rv.status_code == 422
    assert "error" in rv.get_json()


def whitespaceBraindump_returns400(client):
    rv = client.post("/api/ai/text/lint-braindump", json={"braindump": "   "})
    assert rv.status_code == 400
    assert "braindump" in rv.get_json()["error"]


def providerError_returns502(client, monkeypatch):
    from modules.chain.errors import ProviderError

    def raise_provider_error(system, prompt, **kw):
        raise ProviderError("Claude unavailable")

    monkeypatch.setattr(chain_adapter, "generate", raise_provider_error)
    rv = client.post(
        "/api/ai/text/lint-braindump",
        json={"braindump": "my product braindump"},
    )
    assert rv.status_code == 502
    assert "error" in rv.get_json()


def invalidJsonFromProvider_returns502(client, monkeypatch):
    monkeypatch.setattr(
        chain_adapter,
        "generate",
        lambda system, prompt, **kw: ChainResult(text="not valid json at all", latency_ms=5),
    )
    rv = client.post(
        "/api/ai/text/lint-braindump",
        json={"braindump": "my product braindump"},
    )
    assert rv.status_code == 502
    assert "error" in rv.get_json()
```

**Verify**: `python -m pytest tests/test_lint_braindump_route.py -v` — expect 6 passing.

---

## 5. Tests

Complete test bodies are in Step 5 above. Summary of coverage:

| Test | Scenario | Expected |
|------|----------|----------|
| `validBraindump_returnsReadyFalseWithFlags` | Claude returns `{ready: false, flags: [...]}`| 200, shape verified |
| `completeBraindump_returnsReadyTrueEmptyFlags` | Claude returns `{ready: true, flags: []}` | 200, empty flags |
| `missingBraindumpField_returns422` | Request body missing `braindump` key | 422 from Pydantic errorhandler |
| `whitespaceBraindump_returns400` | `braindump` is whitespace-only | 400 from route strip check |
| `providerError_returns502` | Chain adapter raises `ProviderError` | 502 |
| `invalidJsonFromProvider_returns502` | Claude returns non-JSON text | 502 |

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end. Each commit maps to the step(s) it closes.

1. `feat(openapi): add lint-braindump request/response schemas` — after **Step 1** — `openapi.yaml`: three new schemas + path entry
2. `chore(dtos): regenerate models with LintBraindump types` — after **Step 2** — `dtos/models.py`: generated output only
3. `feat(ai): add lint-braindump route and proxy entry` — after **Steps 3 + 4** (commit both atomically) — `modules/ai/routes.py`, `proxy.conf.json`
4. `test(ai): add lint-braindump route tests` — after **Step 5** passes — `tests/test_lint_braindump_route.py`, `tests/conftest.py` (if created)

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
python -m pytest --tb=short -q
```

**Expected delta**: N → N+6 passing. Zero pre-existing tests broken.

Additionally, smoke-test the live endpoint against Flask directly:

```bash
CHAIN_PROVIDER=mock python app.py &
curl -s -X POST http://localhost:3101/api/ai/text/lint-braindump \
  -H 'Content-Type: application/json' \
  -d '{"braindump": "test"}' | python3 -m json.tool
# expect {"ready": ..., "flags": [...]} or mock provider's response shape
kill %1
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` without touching other commits
- **Step 2 specifically**: `git revert <dto-commit-sha>` rolls back the generated file; re-run `make generate-dtos` to restore if needed
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch, or delete the branch and re-cut from the Task 1 commit

---

## 9. Deviations Allowed

- **`tests/conftest.py` already exists with a `client` fixture** → do not duplicate; use the existing fixture; add only if missing
- **`tests/conftest.py` exists with a different app factory signature** → adapt `create_app({"TESTING": True})` to match what's there; log in commit body
- **`datamodel-codegen` generates `StringConstraints` instead of `constr` for `minLength`** → accept the generated output; do not hand-edit; the behavior is equivalent
- **`ProviderError` lacks a `.message` attribute** → inspect `modules/chain/errors.py` and use the correct attribute name (`str(exc)` if no `.message`); log deviation
- **Pytest does not collect functions without `test_` prefix** → check `pytest.ini` or `pyproject.toml`; if `python_functions` is not set to include `*_*`, rename test functions to add `test_` prefix and log the deviation
- **Side-effect required** (push, publish, schema drop) → STOP, mark `[REQUIRES APPROVAL]`, and ask

---

## 10. Out of Scope

This task ports a single buffered endpoint that returns JSON. It does not introduce any new infrastructure, shared utilities, or configuration changes beyond the four files modified above. The proxy fallback to Express at `/api` remains in place — Task 5 removes it after all four endpoints have migrated.

- **Fence-stripping on Claude's JSON output** — deferred; add only when production evidence shows Claude wrapping with markdown despite the prompt instruction
- **Express route removal for `lint-braindump`** — deferred to Task 5; removing the fallback before all four endpoints are ported would break the other three
- **Streaming variant** — Express served this buffered; Flask matches; streaming is a separate feature decision not in this epic
- **Shared parse-failure utility** — deferred until `review` (Task 3) ships; extract only when two consumers exist; the second consumer is the trigger
- **`generate-spec` proxy atomicity** — the architecture flags Task 4's proxy update as needing special atomic treatment; Task 2's proxy entry is a straightforward addition and does not require that treatment

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, component design, execution flow
- [Epic](./epic.md) — Task scope and dependencies
- [Timeline](./timeline.md) — Update status to `done` after verification passes