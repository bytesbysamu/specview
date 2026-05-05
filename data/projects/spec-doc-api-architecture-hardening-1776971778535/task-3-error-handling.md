# Task 3: Error Handling — Implementation Guide

## 1. Context

This task introduces three per-module domain exception types (`ProjectNotFoundError`, `ContextReadError`, `AIProviderError`), rewrites five project route handlers to replace bare `except Exception` blocks with typed raises-and-catches, patches the AI route to translate infrastructure-layer `ProviderError` into the feature-layer `AIProviderError` before mapping to HTTP 502, and registers a single `@app.errorhandler(Exception)` in `create_app.py` as the fallback for anything unexpected. The result is that every error path has a distinct name, every HTTP status code is intentional, and no bare `except Exception` remains in any route handler.

**Trade-offs considered:**
- `SpecDocError` base class with single errorhandler dispatch — rejected: three exception types at three modules, no second consumer for the hierarchy; add the base class when the fourth module lands.
- All domain exceptions escape routes and are dispatched in the global handler — rejected: the architecture explicitly says "route maps this to HTTP [code]"; routes own the mapping, global handler is only the surprise fallback.
- `ContextReadError(OSError)` as an OSError subclass vs plain `Exception` — chosen: write_context lets `Path.write_text` raise `OSError` naturally; wrapping it as a named subclass means existing `except OSError` in context routes catch it with zero route-file modification.

---

## 2. Pre-flight

```bash
cd {WORKSPACE}                                          # {WORKSPACE} = repo root containing flask/
git status                                              # flag any unrelated M/?? entries
git diff HEAD -- flask/modules/projects/routes.py \
                 flask/modules/ai/routes.py \
                 flask/modules/context/service.py \
                 flask/create_app.py                    # confirm target files are clean
cd flask && python -m pytest --tb=no -q                 # record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**Baseline recorded**: ___/N passing (executor fills in actual count before editing).

---

## 3. Files

### To Create (new)
- `flask/modules/projects/errors.py` — `ProjectNotFoundError(Exception)`, ~5 lines
- `flask/modules/context/errors.py` — `ContextReadError(OSError)`, ~5 lines; OSError subclass so existing `except OSError` in context routes catches it without touching those handlers
- `flask/modules/ai/errors.py` — `AIProviderError(Exception)`, ~5 lines

### To Modify (cite CODEBASE CONTEXT)
- `flask/modules/projects/routes.py` (93 lines) — swap hand-rolled `data.get(...)` parsing for `ProjectCreateRequest` / `FileUpdateRequest` / `SuccessResponse` from `dtos.models`; remove five bare `except Exception` blocks; add `ProjectNotFoundError` raise-and-catch for None/False returns; `list_projects_route` and `create_project_route` go bare (unexpected errors fall through to global handler)
- `flask/modules/context/routes.py` (~60 lines) — replace `from .dto import ...` with `from dtos.models import ContextResponse, ContextUpdateRequest, SuccessResponse`; rename `GetContextResponse`→`ContextResponse`, `PutContextRequest`→`ContextUpdateRequest`, `PutContextResponse`→`SuccessResponse`; remove the route-local `except ValidationError` catch — global handler owns 422
- `flask/modules/ai/routes.py` (19 lines) — swap hand-rolled `request.get_json()` parsing for `RewriteRequest.model_validate()` (depends on Task 1 Step 4 generating the DTO); construct response via `RewriteResponse(...).model_dump()`; add nested try/except: inner catches `ProviderError` and re-raises as `AIProviderError`; outer catches `AIProviderError` and returns 502
- `flask/modules/context/service.py` (34 lines) — `write_context`: wrap `write_text` in try/except OSError; raise `ContextReadError` so callers get a named type instead of raw stdlib exception
- `flask/create_app.py` (33 lines) — add `@app.errorhandler(ValidationError)` → 422 with `exc.errors()` detail; add `@app.errorhandler(Exception)` that logs `exc_info=True` and returns `{"error": ..., "status": 500}`

### To Delete
- `flask/modules/context/dto.py` — hand-written per-module DTO shim (`GetContextResponse`, `PutContextRequest`, `PutContextResponse`). Redundant with generated `dtos.models.ContextResponse` / `ContextUpdateRequest` / `SuccessResponse`. No other file in the repo imports from it after Step 3 edits — confirm with `grep -rn "modules.context.dto\|from .dto" flask/` showing zero results before deletion.

### To Leave Alone
- `flask/modules/projects/service.py` — still returns `None`/`False` for not-found; routes translate these to `ProjectNotFoundError`; the service stays filesystem-pure with no exception imports
- `flask/modules/chain/errors.py` — `ProviderError` already exists (lines 5–9); do not touch; it is the infrastructure-layer signal that routes translate upward
- `flask/modules/chain/adapter.py` — propagates `ProviderError` unchanged; no modification needed
- `flask/dtos/models.py` — generated by Task 1 Step 4; do not hand-edit; consumed here but not modified

---

## 4. Implementation Steps

### Step 1: Create per-module exception types

**Action**: Create three exception files, one per module.

**File**: `flask/modules/projects/errors.py` (new)

```python
"""Domain exceptions for the projects module."""
from __future__ import annotations


class ProjectNotFoundError(Exception):
    """Raised when a project directory or project.json does not exist."""
```

**File**: `flask/modules/context/errors.py` (new)

```python
"""Domain exceptions for the context module."""
from __future__ import annotations


class ContextReadError(OSError):
    """Raised when a context file cannot be written.
    Subclasses OSError so existing except OSError clauses in routes catch it.
    """
```

**File**: `flask/modules/ai/errors.py` (new)

```python
"""Domain exceptions for the AI module."""
from __future__ import annotations


class AIProviderError(Exception):
    """Feature-layer signal that the AI provider failed.
    Translated from chain.errors.ProviderError at the route boundary.
    """
```

**Verify**: `python -m pytest flask/ --tb=short -q` — count must equal baseline (no tests affected by empty files).

---

### Step 2: Rewrite `projects/routes.py` — validate with generated DTOs, remove bare excepts

**Action**: Import `ProjectCreateRequest` + `FileUpdateRequest` + `SuccessResponse` from `dtos.models` (generated by Task 1 Step 4 from openapi.yaml). Replace hand-rolled `data.get("name")` / `data.get("files")` / `data.get("content")` with `DTO.model_validate(...)`. Pydantic `ValidationError` is caught by the global errorhandler (Step 5) as 422. Remove bare `except Exception` from all five handlers; keep `except ValueError` catches (path-traversal guard). Raise `ProjectNotFoundError` on `None`/`False` returns.

**File**: `flask/modules/projects/routes.py` (CODEBASE CONTEXT: 93 lines, five routes)

```python
from dtos.models import ProjectCreateRequest, FileUpdateRequest, SuccessResponse
from .errors import ProjectNotFoundError

# list_projects_route — unchanged; no request body
@projects_bp.get("")
def list_projects_route():
    return jsonify(list_projects(_PROJECTS_PATH))


# create_project_route — generated DTO validates input shape
@projects_bp.post("")
def create_project_route():
    req = ProjectCreateRequest.model_validate(request.get_json(force=True) or {})
    result = create_project(_PROJECTS_PATH, req.name, [f.model_dump() for f in req.files])
    return jsonify(result), 201


# get_project_route — raise ProjectNotFoundError; catch with ValueError (path traversal)
@projects_bp.get("/<project_id>")
def get_project_route(project_id: str):
    try:
        project = get_project(_PROJECTS_PATH, project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return jsonify(project)
    except (ProjectNotFoundError, ValueError):
        return jsonify({"error": "Project not found"}), 404


# update_file_route — generated DTO validates content; SuccessResponse for output
@projects_bp.put("/<project_id>/files/<filename>")
def update_file_route(project_id: str, filename: str):
    req = FileUpdateRequest.model_validate(request.get_json(force=True) or {})
    try:
        found = update_file(_PROJECTS_PATH, project_id, filename, req.content)
        if not found:
            raise ProjectNotFoundError(project_id)
        return jsonify(SuccessResponse(success=True).model_dump())
    except (ProjectNotFoundError, ValueError):
        return jsonify({"error": "Project not found"}), 404


# delete_project_route — same pattern; SuccessResponse envelope
@projects_bp.delete("/<project_id>")
def delete_project_route(project_id: str):
    try:
        found = delete_project(_PROJECTS_PATH, project_id)
        if not found:
            raise ProjectNotFoundError(project_id)
        return jsonify(SuccessResponse(success=True).model_dump())
    except (ProjectNotFoundError, ValueError):
        return jsonify({"error": "Project not found"}), 404
```

**Verify**: `python -m pytest flask/tests/test_project.py -v` — all existing tests pass. `ValidationError` paths now return 422 via the global handler (Step 5) rather than 400; update any test expecting 400-on-bad-body to expect 422. Existing happy-path tests are unaffected — shape is identical.

---

### Step 3: Rewire `context/routes.py` off per-module DTOs, patch `context/service.py`

**Action (DTOs)**: The existing `context/routes.py` imports from `.dto` — a hand-written per-module shim (`GetContextResponse`, `PutContextRequest`, `PutContextResponse`) that duplicates types already in the generated `dtos.models` (`ContextResponse`, `ContextUpdateRequest`, `SuccessResponse`). Swap every import to the generated module and delete the shim. The generated `ContextResponse` has the same shape as `GetContextResponse`; `ContextUpdateRequest` matches `PutContextRequest`; `SuccessResponse` replaces `PutContextResponse`. Also remove the route-local `except ValidationError` handler — the global handler (Step 5) now owns that path.

**Action (service)**: In `write_context`, wrap `write_text` in a try/except; re-raise as `ContextReadError`. Read context remains unchanged (returns `""` on missing file — this is not an error).

**Files**:

- `flask/modules/context/dto.py` — **DELETE** (redundant with `dtos/models.py`)
- `flask/modules/context/routes.py` — replace imports and type references

```python
# Before (line 8):
from .dto import GetContextResponse, PutContextRequest, PutContextResponse

# After:
from dtos.models import ContextResponse, ContextUpdateRequest, SuccessResponse
```

Then search-and-replace across the file:
- `GetContextResponse` → `ContextResponse`
- `PutContextRequest`  → `ContextUpdateRequest`
- `PutContextResponse` → `SuccessResponse`

Remove the `try: payload = ContextUpdateRequest.model_validate(...) except ValidationError: return 400` block — let `ValidationError` bubble to the global handler as 422. Simplifies the handler to a single `payload = ContextUpdateRequest.model_validate(request.get_json(force=True) or {})`.

- `flask/modules/context/service.py` (CODEBASE CONTEXT: 34 lines, `write_context` at line 30)

```python
from .errors import ContextReadError

def write_context(key: str, content: str) -> None:
    """Overwrite the context file. Raises ContextReadError on I/O failure."""
    try:
        CONTEXT_PATHS[key].write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ContextReadError(str(exc)) from exc
    logger.info("[Context] %s updated (%d chars)", key, len(content))
```

`ContextReadError` is a subclass of `OSError`. The existing `except OSError` in `context/routes.py` PUT handlers catches it automatically.

**Verify**:
```bash
test ! -e flask/modules/context/dto.py    # shim is gone
grep -rn "from .dto\|modules.context.dto" flask/modules/context/ && echo "LEAKS FOUND" || echo "clean"
python -m pytest flask/tests/test_context_files.py -v  # all tests pass
```

---

### Step 4: Rewrite `ai/routes.py` — validate with `RewriteRequest`, translate ProviderError → AIProviderError → 502

**Action**: Replace the hand-rolled `request.get_json()` parsing with `RewriteRequest.model_validate()` — the generated DTO (produced by Task 1 Step 4) becomes the input contract. Pydantic's `ValidationError` is handled by the global errorhandler (Step 5) as a 400 JSON envelope. The whitespace-only-text rule stays explicit (empty after `.strip()` is semantically empty even though the schema's `minLength: 1` catches only totally-empty strings). Response is constructed as `RewriteResponse(...).model_dump()`.

Import `ProviderError` (chain layer) and `AIProviderError` (feature layer); wrap `chain_adapter.rewrite` in a nested try — inner translates `ProviderError` to `AIProviderError`, outer maps `AIProviderError` to 502.

**Prerequisite**: Task 1 Step 4 has landed — `from dtos.models import RewriteRequest, RewriteResponse` must resolve. Verify with `python -c "from dtos.models import RewriteRequest, RewriteResponse"` before editing.

**File**: `flask/modules/ai/routes.py` (CODEBASE CONTEXT: 19 lines, single route)

```python
from flask import Blueprint, request, jsonify

from dtos.models import RewriteRequest, RewriteResponse
from modules.chain import adapter as chain_adapter
from modules.chain.errors import ProviderError
from modules.ai.prompts import rewrite_prompt
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


# Route handlers for other operations are registered in tasks 3–4.
```

**Why DTO here, hand-parsed elsewhere**: `/rewrite` is the only AI route that exists today and gets its schema in openapi.yaml from Task 1 Step 4. Projects/context routes keep their current parsing under this task — Phase 2's DTO migration covers them uniformly when every endpoint has an openapi schema. Swapping `/rewrite` now establishes the pattern and kills the hand-rolled-validation gap on the only AI endpoint that's gone live.

The nested try is deliberate: in Python, an exception raised inside an `except` clause is not caught by sibling `except` clauses in the same try block. The inner try translates the infrastructure error; the outer try catches the named domain error and maps to HTTP.

**Verify**: `python -m pytest flask/tests/test_ai_rewrite.py -v` — all 15 existing tests pass.

---

### Step 5: Add global errorhandler to `create_app.py`

**Action**: Register two errorhandlers inside the factory. `ValidationError` (pydantic) maps to 422 with the validation details so `RewriteRequest.model_validate()` failures surface cleanly. `Exception` is the catch-all for anything else that escapes a handler — 500 with stack trace logged.

**File**: `flask/create_app.py` (CODEBASE CONTEXT: 33 lines, no existing errorhandler)

```python
import importlib
from flask import Flask, jsonify
from flask_cors import CORS
from pydantic import ValidationError

ENABLED_MODULES = [
    ('modules.projects.routes', 'projects_bp'),
    ('modules.context.routes',  'context_bp'),
    ('modules.ai.routes',       'ai_bp'),
]

def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.update(config)

    CORS(app, origins=['http://localhost:4201'])

    for module_path, blueprint_attr in ENABLED_MODULES:
        module = importlib.import_module(module_path)
        bp = getattr(module, blueprint_attr)
        app.register_blueprint(bp)

    @app.get('/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return jsonify({"error": "validation_failed", "details": exc.errors(), "status": 422}), 422

    @app.errorhandler(Exception)
    def handle_unhandled_exception(exc: Exception):
        app.logger.error("Unhandled exception", exc_info=True)
        return jsonify({"error": "Internal server error", "status": 500}), 500

    return app
```

**Verify**: `python -m pytest flask/ --tb=short -q` — full suite passes at or above baseline count.

---

## 5. Tests

Add to existing test files. Match the `condition_expectedOutcome` naming convention already present in `test_ai_rewrite.py`. Each function is a self-contained addition — do not replace existing tests.

### `flask/tests/test_project.py` — add after existing tests

```python
import json
import importlib

# --- error handling: global handler catches unexpected service failures ---

def test_serviceRaises_listProjects_returns500WithEnvelope(client, monkeypatch):
    def explode(_path):
        raise RuntimeError("disk failed")
    monkeypatch.setattr("modules.projects.routes.list_projects", explode)
    r = client.get("/api/projects")
    assert r.status_code == 500
    body = json.loads(r.data)
    assert "error" in body, "global handler must return JSON with 'error' key"
    assert body.get("status") == 500, "global handler must include status: 500"


def test_serviceRaises_createProject_returns500WithEnvelope(client, monkeypatch):
    def explode(_path, _name, _files):
        raise RuntimeError("disk failed")
    monkeypatch.setattr("modules.projects.routes.create_project", explode)
    r = client.post(
        "/api/projects",
        data=json.dumps({"name": "Test", "files": []}),
        content_type="application/json",
    )
    assert r.status_code == 500
    body = json.loads(r.data)
    assert "error" in body
    assert body.get("status") == 500


def test_projectNotFoundError_getProject_returns404(client, tmp_path, monkeypatch):
    """ProjectNotFoundError raised when get_project returns None → 404."""
    import modules.projects.routes as routes_mod
    original_path = routes_mod._PROJECTS_PATH
    monkeypatch.setattr(routes_mod, "_PROJECTS_PATH", tmp_path)
    r = client.get("/api/projects/nonexistent-id-99999")
    assert r.status_code == 404
    body = json.loads(r.data)
    assert "error" in body
    assert "not found" in body["error"].lower()
```

### `flask/tests/test_ai_rewrite.py` — add after existing tests

```python
def test_providerError_rewrite_returns502WithStatusEnvelope(monkeypatch):
    """ProviderError from chain adapter → AIProviderError → 502 with status envelope."""
    from modules.chain.errors import ProviderError

    monkeypatch.setenv("CHAIN_PROVIDER", "mock")  # use mock client; patch adapter.rewrite directly
    import importlib, sys
    # Force fresh import so monkeypatch.setenv takes effect
    for mod in list(sys.modules.keys()):
        if "modules.chain.adapter" in mod or "modules.ai.routes" in mod:
            del sys.modules[mod]

    def raise_provider_error(system, prompt, **kwargs):
        raise ProviderError("Rate limited", status_code=503)

    monkeypatch.setattr("modules.chain.adapter.rewrite", raise_provider_error)

    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        r = c.post(
            "/api/ai/text/rewrite",
            data=json.dumps({"text": "Hello world", "instructions": "expand"}),
            content_type="application/json",
        )
    assert r.status_code == 502
    body = json.loads(r.data)
    assert "error" in body, "502 response must include 'error' key"
    assert body.get("status") == 502, "502 response must include status: 502"
    assert "Rate limited" in body["error"], "error message must preserve ProviderError message"
```

Add three more tests after the `ProviderError → 502` one above — DTO validation now owns input shape, so the route-level contract needs explicit coverage:

```python
def test_nonStringText_rewrite_returns422ValidationError(client):
    """RewriteRequest.model_validate rejects non-string text → ValidationError → 422 envelope."""
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"text": 123, "instructions": "expand"}),
        content_type="application/json",
    )
    assert r.status_code == 422, "Pydantic ValidationError must surface as 422, not 400 or 500"
    body = json.loads(r.data)
    assert "error" in body


def test_missingTextKey_rewrite_returns422(client):
    """text is a required RewriteRequest field → missing key → ValidationError → 422."""
    r = client.post(
        "/api/ai/text/rewrite",
        data=json.dumps({"instructions": "expand"}),
        content_type="application/json",
    )
    assert r.status_code == 422
    body = json.loads(r.data)
    assert "error" in body


def test_allRoutes_importFromDtosModels():
    """Structural test: every route handler with a request body must validate via generated DTOs.

    Pins principles.md "Validate at the Route Boundary" across all modules. Failure means
    a future commit regressed to `data.get(...) or ""` patterns or reintroduced a per-module
    DTO shim like the old modules/context/dto.py.
    """
    from pathlib import Path
    import re

    expected = {
        "modules/ai/routes.py":       ["RewriteRequest", "RewriteResponse"],
        "modules/context/routes.py":  ["ContextUpdateRequest", "ContextResponse"],
        "modules/projects/routes.py": ["ProjectCreateRequest", "FileUpdateRequest"],
    }
    for rel_path, dtos in expected.items():
        src = Path(rel_path).read_text()
        assert "from dtos.models import" in src, (
            f"{rel_path} must import from dtos.models (generated by make generate-dtos)"
        )
        for dto in dtos:
            assert dto in src, f"{rel_path} must reference {dto} from dtos.models"
        # Negative assertion: no hand-rolled .get(...) parsing on request bodies
        assert not re.search(r'request\.get_json\([^)]*\)\s*(or\s*\{\})?[^.]*\.get\(', src), (
            f"{rel_path} appears to hand-parse request.get_json() with .get(...); "
            f"use DTO.model_validate(request.get_json(force=True)) instead"
        )


def test_noPerModuleDtoShims():
    """No module under flask/modules/ may contain a dto.py — generated dtos.models is canonical."""
    from pathlib import Path
    shims = list(Path("modules").rglob("dto.py"))
    assert shims == [], (
        f"Per-module DTO shims found: {shims}. "
        f"Delete them and import from dtos.models instead. "
        f"Generated DTOs are the single contract; per-module shims drift from openapi.yaml."
    )


def test_everyOpenapiPath_hasRouteHandler():
    """Every openapi.yaml path must have a registered Flask route, and vice versa.

    The server-side equivalent of Spring's "controller implements generated interface" —
    drift between openapi.yaml and the actual Flask url_map fails here, not in production.
    """
    import yaml
    from create_app import create_app

    spec = yaml.safe_load(open("openapi.yaml"))
    declared = set(spec.get("paths", {}).keys())
    # Convert Flask rules (/api/projects/<id>) to openapi form (/api/projects/{id})
    import re
    app = create_app({"TESTING": True})
    registered = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api") and rule.rule != "/health":
            continue
        registered.add(re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule))

    only_in_openapi = declared - registered
    only_in_flask = registered - declared
    assert not only_in_openapi and not only_in_flask, (
        f"openapi ↔ Flask route drift:\n"
        f"  declared in openapi.yaml but no Flask route: {sorted(only_in_openapi)}\n"
        f"  Flask route but not in openapi.yaml:        {sorted(only_in_flask)}"
    )
```

Note: the `test_whitespaceOnlyText_returns400` case in the existing test_ai_rewrite.py still passes — the `if not text:` guard after `.strip()` covers semantic-empty input even after `minLength: 1` lets whitespace through.

### `flask/tests/test_context_files.py` — add after existing tests

```python
def test_contextReadError_putBuilder_returns500(client, monkeypatch):
    """ContextReadError (OSError subclass) from write_context → caught by route's except OSError → 500."""
    from modules.context.errors import ContextReadError

    def raise_context_error(key, content):
        raise ContextReadError("disk full")

    monkeypatch.setattr("modules.context.service.write_context", raise_context_error)

    r = client.put(
        "/api/builder",
        data=json.dumps({"content": "test content"}),
        content_type="application/json",
    )
    assert r.status_code == 500
    body = json.loads(r.data)
    assert "error" in body, "500 response must include 'error' key"
```

---

## 6. Commit Plan

One commit per logical unit. If a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

1. `feat(errors): add per-module domain exception types` — `flask/modules/projects/errors.py`, `flask/modules/context/errors.py`, `flask/modules/ai/errors.py`: three new files, three classes
2. `refactor(projects): validate via generated DTOs, replace bare excepts` — `flask/modules/projects/routes.py`: import `ProjectCreateRequest` / `FileUpdateRequest` / `SuccessResponse` from `dtos.models`; swap hand-rolled `data.get(...)` for `DTO.model_validate(...)`; remove five bare `except Exception`; raise+catch `ProjectNotFoundError`
3. `refactor(context): use generated DTOs, delete per-module shim` — delete `flask/modules/context/dto.py`; `flask/modules/context/routes.py`: replace `from .dto import ...` with `from dtos.models import ContextResponse, ContextUpdateRequest, SuccessResponse`; rename all three type references; remove route-local `except ValidationError` (global handler owns 422)
4. `fix(context): wrap write_context OSError as ContextReadError` — `flask/modules/context/service.py`: named exception on I/O failure; subclasses OSError so context routes catch it unchanged
5. `refactor(ai): validate via RewriteRequest DTO, translate ProviderError → 502` — `flask/modules/ai/routes.py`: import `RewriteRequest` / `RewriteResponse` from `dtos.models`; swap hand-rolled parsing for DTO validation; nested try anti-corruption layer for 502
6. `feat(app): register global errorhandlers for ValidationError + Exception` — `flask/create_app.py`: `@app.errorhandler(ValidationError)` → 422 with details; `@app.errorhandler(Exception)` → 500 envelope + `exc_info=True`
7. `test(errors): add route-level error-handling + structural DTO/openapi tests` — `flask/tests/test_project.py`, `flask/tests/test_ai_rewrite.py`, `flask/tests/test_context_files.py`: 8 new test functions including `test_allRoutes_importFromDtosModels`, `test_noPerModuleDtoShims`, and `test_everyOpenapiPath_hasRouteHandler` — pins validate-at-boundary, no-shim, and openapi ↔ route parity invariants

---

## 7. Verification

```bash
cd {WORKSPACE}/flask
python -m pytest --tb=short -q
```

**Expected delta**: baseline → baseline + 5 passing. Zero pre-existing tests broken.

Spot-check: confirm the five tests added in step 6 appear in the output with their `condition_expectedOutcome` names.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` undoes the change without touching other commits.
- **Per-branch**: if verification fails after all commits, `git reset --hard <pre-task-sha>` or delete the feature branch. The pre-task SHA is recorded in the pre-flight `git diff HEAD` output.

---

## 9. Deviations Allowed

- **`except OSError` not present in `context/routes.py`** — before Step 3, read `flask/modules/context/routes.py` to confirm the `except OSError` clause exists on PUT handlers. If it catches a different type (e.g., `Exception`), make `ContextReadError` a subclass of that type instead, and log the deviation.
- **`chain_adapter.rewrite` signature differs** — if `adapter.rewrite` takes different positional args than `(system, prompt)`, adapt the mock's signature in the 502 test to match; log deviation.
- **`test_context_files.py` PUT fixture uses a different path** — if the existing PUT test fixture redirects `write_context` via a different mechanism, adapt the monkeypatch target to `modules.context.routes.write_context` instead; log deviation.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log the deviation in the commit body.
- **Side-effect required** (push, schema drop, publish) → STOP, mark [REQUIRES APPROVAL] and flag.

---

## 10. Out of Scope

This task delivers typed exception names, bare-except removal, and a global 500 fallback. It does not change any observable API contract, add retry logic, modify the chain adapter's provider selection, or touch any Phase 2 AI routes that do not yet exist. The following are explicitly deferred:

- **`SpecDocError` base class** — add when the fourth module registers its own exception type; the hierarchy earns its indirection at that point
- **Per-type `@app.errorhandler` registrations** — currently one catch-all suffices; when modules want different HTTP semantics from the global handler without touching each route, introduce per-type registrations
- **`read_context` raising `ContextReadError` on OSError** — `read_context` currently returns `""` on missing/unreadable files (graceful fallback). Changing this behavior affects GET route responses and requires GET handler modifications; defer to a focused context-hardening task
- **Logging config / `logging.basicConfig`** — `create_app.py`'s `app.logger` is sufficient for the global handler; a root-logger config belongs in the Observability task (Task 4)
- **CI pipeline wiring** — no GitHub Actions workflow exists for this backend yet; `check-dtos` and test gating in CI belong in Task 1 (Build tooling)

**Rule for the executor**: if a change appears useful but appears in this list, STOP and flag it as an out-of-scope deviation rather than absorbing it.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Error handling design rationale (Component Design: Error Handling section)
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Update task status to Done after verification passes