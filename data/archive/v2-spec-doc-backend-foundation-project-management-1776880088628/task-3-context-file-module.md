Now I have everything I need. Let me write the guide.

# Task 3: Context File Module — Implementation Guide

**Purpose**: Implement the `context_files` Blueprint in the Flask V2 backend. Eight route handlers (GET + PUT for each of the four context files: `builder.md`, `principles.md`, `codebase.md`, `references.md`) that replicate the Express contract exactly, allowing the Angular frontend's four context panels to read and write against Flask without any code change on the frontend.

**Effort**: 1 day

**Dependencies**: Task 1 (Flask scaffold + app factory). Verify `flask/app.py` exists before starting.

**Parallel With**: Task 2 (Project CRUD Module), Task 4 (Chain Module Port)

**Blocks**: Phase 2 AI endpoints — context injection depends on these files being reliably readable by Flask.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 3 builds the `context_files` Blueprint: eight thin route handlers that read and write the four context files (`builder.md`, `principles.md`, `codebase.md`, `references.md`) sitting at the `spec-doc/` workspace root. These files are the source of truth for every AI generation call in Phase 2 — every prompt that involves the builder profile, architecture principles, codebase summary, or reference code pulls from them. The Angular frontend's `BuilderService`, `PrinciplesService`, `CodebaseService`, and `ReferencesService` all call `GET` and `PUT` on these routes directly; the Flask implementation must replicate the Express response shapes at `server.js:352–462` exactly or the Angular panels break silently. The module follows the Bubls layered pattern from `references.md`: `routes.py` (HTTP boundary) → `service.py` (filesystem helpers) → `dto.py` (Pydantic validation). No AI calls, no async, no diffing — this is a filesystem thin-wrapper and nothing else.

**Trade-offs considered**:
- **Dynamic route over a `/:type` parameter** (`GET /api/context/:type`) — rejected. The epic names exactly four types; adding a parameter abstracts one concrete case, which the architecture explicitly forbids ("static path map, not dynamic routing").
- **Inline file paths per handler** (no central map) — rejected. If one file moves, eight handlers need updating instead of one map entry.
- **Single service with a path map + shared `_get_handler` / `_put_handler` helpers** — preferred. Keeps routes.py under 45 lines (within 80-line budget), centralizes the one decision that can change (file paths), and keeps each route explicitly declared (no dynamic dispatch).

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm git state — flag unrelated changes
git status

# 2. Confirm target files are clean (nothing to collide with)
git diff HEAD -- flask/modules/context_files/ flask/app.py

# 3. Confirm Task 1 scaffold exists
ls flask/app.py flask/requirements.txt flask/modules/__init__.py
# STOP if any of these are missing — Task 1 is not complete

# 4. Confirm the four context files exist at workspace root
ls builder.md principles.md codebase.md references.md

# 5. Baseline: run existing tests (record the pass count)
cd flask && pytest --tb=short -q 2>&1 | tail -5
```

**If Task 1 files are missing**: do not proceed. Task 1 must be complete before Task 3 starts. Flag the dependency gap.

**If context files are missing**: the context panels will return `exists: false` and empty content — this is valid behavior. Do not create placeholder files.

**Baseline recorded**: N passing (record before starting).

---

## 3. Files

### To Create (new)
- `flask/modules/context_files/__init__.py` — package marker; empty file
- `flask/modules/context_files/dto.py` — Pydantic models for GET response, PUT request, PUT response
- `flask/modules/context_files/service.py` — static path map + `read_context` / `write_context` helpers
- `flask/modules/context_files/routes.py` — eight route handlers registered on `bp = Blueprint("context_files", __name__)`
- `flask/tests/test_context_files.py` — pytest test suite; no AI dependency

### To Modify (cite CODEBASE CONTEXT)
- `flask/app.py` (Task 1 deliverable) — add `"modules.context_files"` to `ENABLED_MODULES` list, ported from `references.md:33–37`

### To Leave Alone
- `server.js` — Express continues to run on 3100 throughout migration; zero changes
- `builder.md`, `principles.md`, `codebase.md`, `references.md` — the actual context files at workspace root; routes read/write them as-is, no migration needed
- All `src/app/` Angular files — the API contract is a constraint. If Flask must change to match Angular, the Flask route is wrong; Angular is never wrong here
- `flask/modules/project/` (Task 2 deliverable) — do not touch

---

## 4. Implementation Steps

### Step 1: Confirm Task 1 ENABLED_MODULES list

**Action**: Open `flask/app.py` and read the current `ENABLED_MODULES` list. Confirm it follows the pattern from `references.md:33–37`. Note the exact format — you will add one entry in Step 6.

**File**: `flask/app.py` (Task 1 deliverable; cite `references.md:33–37`)

**Pattern** (what you should see):
```python
ENABLED_MODULES: list[str] = [
    "modules.project",   # Task 2 may or may not be in here yet; either is fine
]
```

**Verify**: `python -c "from app import create_app; app = create_app(); print(app.url_map)"` — should show `/api/health` and project routes (if Task 2 is done). No context routes yet.

---

### Step 2: Create the package marker

**Action**: Create an empty `__init__.py` to make `context_files` a Python package.

**File**: `flask/modules/context_files/__init__.py` (new)

**Pattern**:
```python
# context_files package — thin filesystem read/write layer for the four context files
```

**Verify**: `python -c "import modules.context_files"` from within `flask/` — no import error.

---

### Step 3: Create dto.py — Pydantic request/response models

**Action**: Define three Pydantic v2 models. These are the only types that cross the HTTP boundary. No business logic here.

**File**: `flask/modules/context_files/dto.py` (new)

**Pattern** (port the module-structure shape from `references.md:82–87`):
```python
from pydantic import BaseModel


class GetContextResponse(BaseModel):
    content: str
    exists: bool


class PutContextRequest(BaseModel):
    content: str  # Pydantic raises ValidationError if field is missing or not a str


class PutContextResponse(BaseModel):
    success: bool
```

**Verify**: `python -c "from modules.context_files.dto import GetContextResponse, PutContextRequest, PutContextResponse; print('ok')"` from within `flask/`.

---

### Step 4: Create service.py — path map + read/write helpers

**Action**: Implement the static path map (one source of truth for file locations) and the two helper functions. `_WORKSPACE_ROOT` anchors to the `spec-doc/` directory using `Path.parents[3]` — three directories up from `service.py` (`context_files/` → `modules/` → `flask/` → `spec-doc/`). This matches `server.js:325` where `BUILDER_FILE = path.join(__dirname, 'builder.md')` and `__dirname` is `spec-doc/`.

**File**: `flask/modules/context_files/service.py` (new)

**Pattern** (mirrors `server.js:325–410`; follows static-map principle from `architecture.md`):
```python
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Anchor to spec-doc/ workspace root:
#   service.py → context_files/ → modules/ → flask/ → spec-doc/
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]

CONTEXT_PATHS: dict[str, Path] = {
    "builder":    _WORKSPACE_ROOT / "builder.md",
    "principles": _WORKSPACE_ROOT / "principles.md",
    "codebase":   _WORKSPACE_ROOT / "codebase.md",
    "references": _WORKSPACE_ROOT / "references.md",
}


def read_context(key: str) -> str:
    """Return file content or '' if the file does not exist."""
    path = CONTEXT_PATHS[key]
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        logger.error("Error reading %s: %s", key, exc)
        return ""


def write_context(key: str, content: str) -> None:
    """Overwrite the context file. Raises OSError on failure."""
    CONTEXT_PATHS[key].write_text(content, encoding="utf-8")
    logger.info("[Context] %s updated (%d chars)", key, len(content))
```

**Verify**: 
```bash
cd flask
python -c "
from modules.context_files.service import read_context, CONTEXT_PATHS
print(CONTEXT_PATHS['builder'])   # should end in spec-doc/builder.md
content = read_context('builder')
print(f'builder.md: {len(content)} chars')
"
```
Expected: path ends in `spec-doc/builder.md`, content is the current builder profile (non-zero chars if builder.md exists).

---

### Step 5: Create routes.py — eight handlers

**Action**: Declare the Blueprint and eight route handlers. Use two private helpers (`_get_handler`, `_put_handler`) to share validation and response-building logic without dynamic dispatch. Every route is explicitly declared — no `url_for` magic, no dynamic routing. Response shape matches `server.js:353–396` exactly: GET returns `{content, exists}`, PUT returns `{success: true}` or 400 on invalid input.

**File**: `flask/modules/context_files/routes.py` (new)

**Pattern** (mirrors `server.js:352–462`, follows thin-handler principle from `architecture.md`):
```python
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from .dto import GetContextResponse, PutContextRequest, PutContextResponse
from .service import read_context, write_context

logger = logging.getLogger(__name__)
bp = Blueprint("context_files", __name__)


def _get_handler(key: str):
    content = read_context(key)
    return jsonify(GetContextResponse(content=content, exists=len(content) > 0).model_dump())


def _put_handler(key: str):
    try:
        payload = PutContextRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError:
        return jsonify({"error": "content must be a string"}), 400
    try:
        write_context(key, payload.content)
    except OSError:
        logger.error("Failed to write context file: %s", key)
        return jsonify({"error": f"Failed to save {key}"}), 500
    return jsonify(PutContextResponse(success=True).model_dump())


@bp.get("/api/builder")
def get_builder():
    return _get_handler("builder")

@bp.put("/api/builder")
def put_builder():
    return _put_handler("builder")

@bp.get("/api/principles")
def get_principles():
    return _get_handler("principles")

@bp.put("/api/principles")
def put_principles():
    return _put_handler("principles")

@bp.get("/api/codebase")
def get_codebase():
    return _get_handler("codebase")

@bp.put("/api/codebase")
def put_codebase():
    return _put_handler("codebase")

@bp.get("/api/references")
def get_references():
    return _get_handler("references")

@bp.put("/api/references")
def put_references():
    return _put_handler("references")
```

**Verify**: `python -c "from modules.context_files.routes import bp; print([r.rule for r in bp.deferred_functions])"` — no import error. (Route rules aren't accessible until registered; absence of ImportError is sufficient here.)

---

### Step 6: Register Blueprint in app.py

**Action**: Add `"modules.context_files"` to `ENABLED_MODULES` in the app factory. This is the only file modified in this task that was created by Task 1. Make a surgical one-line edit.

**File**: `flask/app.py` (Task 1 deliverable; port pattern from `references.md:33–37`)

**Pattern** — add one entry:
```python
ENABLED_MODULES: list[str] = [
    "modules.project",       # Task 2
    "modules.context_files", # Task 3  ← add this line
]
```

**Verify**:
```bash
cd flask
python -c "
from app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
assert '/api/builder' in rules, '/api/builder missing'
assert '/api/principles' in rules, '/api/principles missing'
assert '/api/codebase' in rules, '/api/codebase missing'
assert '/api/references' in rules, '/api/references missing'
print('All 8 context routes registered:', [r for r in rules if '/api/builder' in r or '/api/principles' in r or '/api/codebase' in r or '/api/references' in r])
"
```
Expected: prints all 8 routes without error.

---

### Step 7: Smoke-test against the live Angular frontend

**Action**: Start Flask on 3101 (or 3100 if cutover has happened) and load the Angular app. Open each of the four context panels and confirm they load existing content and can save a one-character change.

**File**: n/a — runtime verification only

**Pattern**:
```bash
# Terminal 1: start Flask
cd flask && FLASK_APP=app:create_app flask run --port 3101

# Terminal 2: verify each context GET directly
curl -s http://localhost:3101/api/builder | python -m json.tool
curl -s http://localhost:3101/api/principles | python -m json.tool
curl -s http://localhost:3101/api/codebase | python -m json.tool
curl -s http://localhost:3101/api/references | python -m json.tool

# Verify PUT round-trip for builder
ORIGINAL=$(curl -s http://localhost:3101/api/builder | python -c "import sys,json; print(json.load(sys.stdin)['content'][:50])")
curl -s -X PUT http://localhost:3101/api/builder \
  -H "Content-Type: application/json" \
  -d '{"content":"smoke test content"}' | python -m json.tool
# Should return {"success": true}
# Restore original content via PUT (or git checkout builder.md)
```

**Verify**: Each GET returns `{"content": "...", "exists": true/false}`. PUT returns `{"success": true}`. Non-JSON PUT body returns 400. After PUT, a subsequent GET reflects the new content.

---

## 5. Tests

Framework: pytest + Flask test client. No AI dependency. Run from `flask/` directory.

```python
# flask/tests/test_context_files.py
"""
Tests for the context_files Blueprint.

Run: cd flask && pytest tests/test_context_files.py -v

Validates:
  - GET returns {content, exists} shape matching server.js:353-354
  - PUT saves content and returns {success: true} matching server.js:366
  - PUT with non-string body returns 400 matching server.js:362-363
  - All four context types are routed correctly
  - CONTEXT_PATHS resolves to workspace-root files (path sanity check)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure flask/ is on the path regardless of where pytest is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """Flask test client with CONTEXT_PATHS redirected to tmp_path.

    Each test gets isolated temp files — no cross-contamination and no
    dependency on the real builder.md / principles.md / codebase.md /
    references.md on disk.
    """
    from modules.context_files import service
    from app import create_app

    # Redirect all four paths to tmp_path files (may or may not exist yet)
    original_paths = dict(service.CONTEXT_PATHS)
    for key in original_paths:
        service.CONTEXT_PATHS[key] = tmp_path / f"{key}.md"

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as c:
        yield c

    # Restore original paths (module is imported once per process)
    service.CONTEXT_PATHS.update(original_paths)


# ---------------------------------------------------------------------------
# Path map sanity
# ---------------------------------------------------------------------------

def test_context_paths_resolve_to_workspace_root():
    """CONTEXT_PATHS must resolve to spec-doc/ root, not inside flask/."""
    from modules.context_files.service import CONTEXT_PATHS, _WORKSPACE_ROOT

    for key, path in CONTEXT_PATHS.items():
        assert path.parent == _WORKSPACE_ROOT, (
            f"CONTEXT_PATHS['{key}'] = {path} — expected parent {_WORKSPACE_ROOT}"
        )

    expected_filenames = {"builder.md", "principles.md", "codebase.md", "references.md"}
    actual_filenames = {p.name for p in CONTEXT_PATHS.values()}
    assert actual_filenames == expected_filenames, (
        f"Unexpected filenames in CONTEXT_PATHS: {actual_filenames}"
    )


# ---------------------------------------------------------------------------
# GET — file does not exist
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route", [
    "/api/builder",
    "/api/principles",
    "/api/codebase",
    "/api/references",
])
def test_get_returns_empty_content_when_file_missing(client, route):
    """GET on a missing context file returns {content: '', exists: false}."""
    resp = client.get(route)
    assert resp.status_code == 200, f"{route}: expected 200, got {resp.status_code}"
    body = json.loads(resp.data)
    assert body["content"] == "", f"{route}: expected empty content, got {body['content']!r}"
    assert body["exists"] is False, f"{route}: expected exists=false, got {body['exists']}"


# ---------------------------------------------------------------------------
# GET — file exists with content
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key,route", [
    ("builder",    "/api/builder"),
    ("principles", "/api/principles"),
    ("codebase",   "/api/codebase"),
    ("references", "/api/references"),
])
def test_get_returns_content_when_file_exists(client, tmp_path, key, route):
    """GET on an existing context file returns {content: <text>, exists: true}."""
    from modules.context_files.service import CONTEXT_PATHS

    expected = f"# {key.title()} context file\nSome content here."
    CONTEXT_PATHS[key].write_text(expected, encoding="utf-8")

    resp = client.get(route)
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["content"] == expected, f"{route}: content mismatch"
    assert body["exists"] is True, f"{route}: expected exists=true"


# ---------------------------------------------------------------------------
# PUT — valid content
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key,route", [
    ("builder",    "/api/builder"),
    ("principles", "/api/principles"),
    ("codebase",   "/api/codebase"),
    ("references", "/api/references"),
])
def test_put_saves_content_and_returns_success(client, key, route):
    """PUT with valid content writes the file and returns {success: true}."""
    from modules.context_files.service import CONTEXT_PATHS

    new_content = f"Updated {key} content — {key} test."
    resp = client.put(
        route,
        data=json.dumps({"content": new_content}),
        content_type="application/json",
    )
    assert resp.status_code == 200, f"{route}: expected 200, got {resp.status_code}"
    body = json.loads(resp.data)
    assert body == {"success": True}, f"{route}: unexpected body {body}"

    # Confirm the file was actually written
    saved = CONTEXT_PATHS[key].read_text(encoding="utf-8")
    assert saved == new_content, (
        f"{route}: file content '{saved[:40]}' does not match sent content"
    )


def test_put_overwrites_existing_content(client, key="builder", route="/api/builder"):
    """PUT replaces existing content, not appending."""
    from modules.context_files.service import CONTEXT_PATHS

    CONTEXT_PATHS["builder"].write_text("original content", encoding="utf-8")
    client.put(
        "/api/builder",
        data=json.dumps({"content": "replaced content"}),
        content_type="application/json",
    )
    saved = CONTEXT_PATHS["builder"].read_text(encoding="utf-8")
    assert saved == "replaced content", f"Expected 'replaced content', got '{saved}'"


# ---------------------------------------------------------------------------
# PUT — invalid input (400 responses)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body,description", [
    ({},                          "missing content field"),
    ({"content": 42},             "content is integer, not string"),
    ({"content": None},           "content is null"),
    ({"content": ["a", "list"]},  "content is array"),
])
def test_put_returns_400_for_invalid_body(client, body, description):
    """PUT with non-string content returns 400 (mirrors server.js:362-363)."""
    resp = client.put(
        "/api/builder",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert resp.status_code == 400, (
        f"Expected 400 for {description}, got {resp.status_code}"
    )
    error_body = json.loads(resp.data)
    assert "error" in error_body, f"Expected error field in response: {error_body}"


def test_put_returns_400_for_empty_json_body(client):
    """PUT with no JSON body (empty) returns 400."""
    resp = client.put("/api/builder", data="", content_type="application/json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PUT/GET round-trip
# ---------------------------------------------------------------------------

def test_get_reflects_put_content(client):
    """PUT then GET returns the exact same content."""
    written = "# Builder\n\nThis is the round-trip test content.\n"
    client.put(
        "/api/builder",
        data=json.dumps({"content": written}),
        content_type="application/json",
    )
    resp = client.get("/api/builder")
    body = json.loads(resp.data)
    assert body["content"] == written, "GET did not reflect PUT content"
    assert body["exists"] is True


# ---------------------------------------------------------------------------
# Blueprint registration (structural)
# ---------------------------------------------------------------------------

def test_all_eight_routes_are_registered():
    """All 8 context routes exist in the Flask app's URL map."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import create_app

    app = create_app()
    rules = {r.rule for r in app.url_map.iter_rules()}

    expected_routes = {
        "/api/builder",
        "/api/principles",
        "/api/codebase",
        "/api/references",
    }
    for route in expected_routes:
        assert route in rules, f"Route {route} not registered in Flask app"
```

---

## 6. Commit Plan

All from within the `flask/` working directory. Commit only what this task touches.

1. `feat(context-files): add context_files module — dto, service, routes` — `flask/modules/context_files/__init__.py`, `flask/modules/context_files/dto.py`, `flask/modules/context_files/service.py`, `flask/modules/context_files/routes.py`: the full four-file module
2. `feat(app): register context_files Blueprint in ENABLED_MODULES` — `flask/app.py`: the one-line addition to `ENABLED_MODULES`
3. `test(context-files): pytest suite for all 8 context routes` — `flask/tests/test_context_files.py`: full test suite covering GET/PUT for all four types, 400 validation, round-trip, and structural registration check

**Deviation logging**: if any step deviates from this guide, prefix the relevant commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd flask && pytest tests/test_context_files.py -v --tb=short
```

**Expected delta**: baseline N → N+16 passing (16 parametrized + direct tests across 10 test functions). Zero pre-existing tests broken.

Full smoke verification against Angular:
```bash
# Start Flask on 3101 (parallel with Express on 3100)
FLASK_APP=app:create_app flask run --port 3101

# Change Angular proxy to 3101 temporarily:
# In angular.json or proxy.conf.json, set target to http://localhost:3101

# Load http://localhost:4201, open each of the four context panels:
# 1. Builder Profile panel — loads existing builder.md content, saves a change
# 2. Principles Editor panel — loads principles.md, saves a change
# 3. Codebase Editor panel — loads codebase.md, saves a change
# 4. References panel — loads references.md, saves a change

# Revert proxy target back to 3100 after verification
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. The order matters: revert commit 2 before commit 1 (Blueprint registration depends on module existence).
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` [REQUIRES APPROVAL] on a feature branch, or delete the feature branch. The Express backend (`server.js`) is unchanged and still running on 3100 — Angular is unaffected.
- **CONTEXT_PATHS mismatch**: if `_WORKSPACE_ROOT` resolves to the wrong directory (e.g., if the `flask/` directory was placed differently than this guide assumes), fix `parents[3]` to the correct index. Run the path sanity test `test_context_paths_resolve_to_workspace_root` to catch this before the module goes live.

---

## 9. Deviations Allowed

- **`flask/` directory has a different name** (e.g., `backend/`, `server_py/`) → update all paths in this guide accordingly. The module structure (`modules/context_files/`) is invariant; only the root directory name changes. Update `parents[3]` in `service.py` if depth changes.
- **Task 1 used `pydantic` v1 instead of v2** → replace `.model_validate()` with `.parse_obj()` and `.model_dump()` with `.dict()`. Note in commit body.
- **Test framework mismatch** (Task 1 set up a different pytest config) → match what's there. If conftest.py defines a shared `app` fixture, use it instead of defining one locally. Note in commit body.
- **Step unlocks simplification** (e.g., Task 2 already wrote `_put_handler` as a shared utility in `core/`) → use it, log the deviation.
- **Side-effect required** (pushing to remote, dropping a table, editing shared CI config) → STOP. Mark [REQUIRES APPROVAL] and wait.

---

## 10. Out of Scope

This task is strictly the filesystem read/write layer. It does not inject context into prompts, does not validate file content against schemas, does not add caching, and does not implement the scan endpoint (which auto-populates `codebase.md` via filesystem walk). The scan endpoint calls `/api/ai/text/scan` which lives in the AI operations module, not here — the context_files module only stores what was already scanned. Any change that isn't one of the eight route handlers or the path map is out of scope.

- **`/api/ai/text/scan` endpoint** — deferred to Phase 2 AI endpoints module. The scan operation is an AI call (walks the filesystem, summarizes via Claude), not a context file operation. It writes to `codebase.md` as a side effect, which this module handles correctly — but the scan trigger itself is out of scope.
- **Context injection into prompts** — deferred to Phase 2. The chain module (Task 4) and AI endpoint modules consume `read_context()` calls; Task 3 only exposes the HTTP surface.
- **Caching / in-memory reads** — deferred. Single-user tool, file sizes are small, and no Phase 1 feature has a latency requirement that justifies cache complexity.
- **Validation of file content** (e.g., enforcing markdown structure in `builder.md`) — deferred. The content is user-controlled and injected verbatim into prompts. Schema enforcement belongs in Phase 2 if at all.
- **Fifth or sixth context type** — explicitly out of scope per the epic ("exactly four context types"). If a new type appears, add one entry to `CONTEXT_PATHS` and two route handlers in `routes.py` — do not add dynamic dispatch or a generic `/api/context/:type` route.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than absorbing it into this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale (static path map decision, thin-handler pattern)
- [Epic](./epic.md) – Task scope and port budget (~80 lines)
- [Timeline](./timeline.md) – Update Task 3 status to "Done" after verification passes