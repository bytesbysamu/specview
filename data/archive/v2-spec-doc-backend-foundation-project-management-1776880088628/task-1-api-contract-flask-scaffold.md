# Task 1: API Contract + Flask Scaffold — Implementation Guide

## 1. Context

This task establishes the two foundations every subsequent Phase 1 task depends on: a complete API
contract document reverse-engineered from the live Express server, and a Flask application skeleton
that can run alongside Express on port 3101 without touching the Angular frontend. The contract
document is written first so that Tasks 2 and 3 build against a known spec rather than discovering
response shapes mid-implementation. The scaffold provides the app factory, CORS config, Blueprint
registration mechanism, and health route — roughly 80 lines of Python with no business logic — so Tasks
2, 3, and 4 each have a factory to plug into.

Trade-offs considered:
- Replace Express in-place on 3100 — rejected because a regression in any Flask route takes down the
entire frontend with no easy rollback path; parallel ports let both backends live simultaneously
- Single-file Flask app (no factory, no Blueprints) — rejected because Tasks 2, 3, and 4 each add
routes; a monolithic single-file structure forces merge conflicts and couples unrelated modules
- App factory + Blueprint-per-module, Flask on 3101 — chosen because it matches the Bubls pattern cited
in the architecture, enables parallel migration, and makes Phase 2 module additions a folder-add
rather than an edit to existing code

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm working tree state
git status

# Confirm target directory doesn't already exist
ls flask/ 2>/dev/null && echo "EXISTS — investigate before proceeding" || echo "clean"

# Baseline: record passing count
npm run test:server
# Record output: e.g., "pass 23, fail 0"

# Confirm Express is reachable (confirms port 3100 is live)
curl -s http://localhost:3100/health || echo "Express not running — start with: npm run api"

# Confirm projects/ directory exists and has content
ls projects/ | wc -l
# Expect: non-zero (currently 63 directories)
```

If working tree is dirty on target files: stash or commit unrelated changes before starting.

Baseline recorded: existing JS test suite passes (record count before editing).

---

## 3. Files

### To Create (new)

- `flask/api-contract.md` — full API contract document: all routes, HTTP methods, request bodies,
response shapes; reverse-engineered from server.js before any Flask code is written
- `flask/requirements.txt` — Python dependencies: flask, flask-cors
- `flask/config.py` — path constants: BASE_DIR, PROJECTS_DIR, CONTEXT_FILES map; consumed by Tasks 2 and 3
- `flask/create_app.py` — app factory: create_app(), ENABLED_MODULES list, CORS at localhost:4201, health
route, Blueprint registration loop
- `flask/app.py` — entry point: calls create_app(), binds to PORT env var defaulting to 3101
- `flask/modules/__init__.py` — package marker (empty)
- `flask/modules/projects/__init__.py` — package marker (empty)
- `flask/modules/projects/routes.py` — projects Blueprint stub; routes are stubs, implementation is Task 2
- `flask/modules/context/__init__.py` — package marker (empty)
- `flask/modules/context/routes.py` — context Blueprint stub; routes are stubs, implementation is Task 3
- `flask/tests/__init__.py` — package marker (empty)
- `flask/tests/conftest.py` — pytest fixtures: app and client
- `flask/tests/test_health.py` — health + CORS + Blueprint registration tests

### To Modify (cite CODEBASE CONTEXT)

None. Task 1 creates new files only. Zero edits to existing files.

### To Leave Alone

- `server.js` — live Express backend; must remain untouched; it is the ground truth for the API contract
- `src/app/services/` (all services) — Angular services hardcode localhost:3100; no change until cutover
- `projects/` — 63 existing project directories; loaded as-is by Task 2; no migration, no modification
- `builder.md`, `principles.md`, `codebase.md`, `references.md` — context files at workspace root; consumed by Tasks 3 and 4
- `server.test.js`, `server.integration.test.js` — existing JS test suite; must continue to pass after this task
- `specs/` — specification documents; not changed by implementation tasks

---

## 4. Implementation Steps

### Step 1: Verify Projects Directory

**Action:** Confirm the projects/ directory structure matches what Flask will serve before writing a single route.

**File:** `projects/` (existing, do not modify)

**Pattern:**
```bash
# Spot-check three projects to confirm structure
ls projects/bubls-1776180149743/
# Expect: project.json + *.md files

cat projects/bubls-1776180149743/project.json
# Expect: {"name": "...", "createdAt": "..."}
```

**Verify:** `ls projects/ | wc -l` — expect 63 (or current count). `cat projects/$(ls projects | head -1)/project.json` — expect valid JSON with name and createdAt fields. If any project directory lacks project.json, note it; do not fix it in this task (see Out of Scope).

---

### Step 2: Create the API Contract Document

**Action:** Write the full contract for all routes currently served by Express. This document is the implementation spec for Tasks 2 and 3.

**File:** `flask/api-contract.md` (new)

**Pattern:**
```markdown
# Spec-Doc API Contract

Reverse-engineered from `server.js` on 2026-04-22.
Flask must match every route, method, payload field, and response shape exactly.
Any deviation breaks Angular without a frontend code change.

**Express port:** 3100 (source of truth)
**Flask port:** 3101 (migration target)

---

## Health

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/health` | GET | — | `{"status": "ok"}` |

> Flask adds this route. Express does not expose it.

---

## Context Routes

All context routes share the same response shapes.

### Builder Profile

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/builder` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/builder` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `builder.md` at workspace root

### Principles

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/principles` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/principles` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `principles.md` at workspace root

### Codebase

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/codebase` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/codebase` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `codebase.md` at workspace root

### References

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/references` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/references` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `references.md` at workspace root

---

## Project Routes

### List Projects

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/api/projects` | GET | — | `ProjectSummary[]` sorted newest-first |

**ProjectSummary shape:**
{
  "id": "string",
  "name": "string",
  "createdAt": "ISO-8601 string",
  "specs": [{ "filename": "string", "label": "string" }]
}

id = directory name under projects/. specs = all .md files in the directory (filename only, no
content). label = filename without extension. Sort: descending by createdAt from project.json.

### Get Project

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/api/projects/:id` | GET | — | ProjectDetail |

ProjectDetail shape: same as ProjectSummary but specs[].content is populated (full file contents).

### Create Project

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/projects` | POST | `{"name": string, "files": [{"filename": string, "content": string}]}` | `{"id": string, "name": string, "createdAt": string}` |

id = {slugified-name}-{Date.now()}. Creates directory at projects/{id}/, writes project.json + each file.

### Update Project File

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/projects/:id/files/:filename` | PUT | `{"content": string}` | `{"success": boolean}` |

Writes content to projects/{id}/{filename}. Returns 404 if project directory does not exist.

### Delete Project

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/api/projects/:id` | DELETE | — | `{"success": boolean}` |

Removes projects/{id}/ recursively.

---

## AI Routes (Phase 2 — NOT implemented in Flask Phase 1)

These routes exist in Express. Flask Phase 1 does not expose them.

| Route | Method | Notes |
|-------|--------|-------|
| `/api/ai/text/rewrite` | POST | Phase 2 |
| `/api/ai/text/generate` | POST | Phase 2 |
| `/api/ai/text/iterate` | POST | Phase 2 |
| `/api/ai/text/generate-spec` | POST | Phase 2 |
| `/api/ai/text/review` | POST | Phase 2 |
| `/api/ai/text/lint-braindump` | POST | Phase 2 |
| `/api/ai/text/scan` | POST | Phase 2 + Walker |
| `/api/ai/implement` | POST (SSE) | Phase 2 |
| `/api/container/*` | GET/POST/DELETE | Phase 2+ |

---

## Error Conventions (reverse-engineered from Express)

| Condition | Status | Body |
|-----------|--------|------|
| Missing required field | 400 | `{"error": "descriptive message"}` |
| Resource not found | 404 | `{"error": "not found"}` |
| Filesystem error | 500 | `{"error": string}` |
```

**Verify:** File exists at `flask/api-contract.md`. Manually cross-check three routes from `server.js` against the document (e.g., line ~400 for project list, line ~450 for create). Counts must match.

---

### Step 3: Create requirements.txt

**Action:** Declare Python dependencies.

**File:** `flask/requirements.txt` (new)

**Pattern:**
```
flask>=3.0.0
flask-cors>=4.0.0
pytest>=8.0.0
```

**Verify:** `cat flask/requirements.txt` — three lines. `pip install -r flask/requirements.txt` — exits 0. `python -c "import flask; import flask_cors; import pytest; print('ok')"` — prints `ok`.

---

### Step 4: Create config.py

**Action:** Define workspace-anchored path constants used by Tasks 2 and 3. Centralise path resolution here so route handlers never construct paths.

**File:** `flask/config.py` (new)

**Pattern:**
```python
import os

# Anchor to spec-doc/ (parent of flask/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')

# Static map: context type → filesystem path
# Architecture decision: four types, static map, no dynamic routing
CONTEXT_FILES = {
    'builder':    os.path.join(BASE_DIR, 'builder.md'),
    'principles': os.path.join(BASE_DIR, 'principles.md'),
    'codebase':   os.path.join(BASE_DIR, 'codebase.md'),
    'references': os.path.join(BASE_DIR, 'references.md'),
}
```

**Verify:** `cd flask && python -c "from config import PROJECTS_DIR, CONTEXT_FILES; import os; assert os.path.isdir(PROJECTS_DIR), f'projects dir missing: {PROJECTS_DIR}'; print('PROJECTS_DIR ok:', PROJECTS_DIR)"` — prints path without assertion error.

---

### Step 5: Create Blueprint Stubs

**Action:** Create the projects and context Blueprints with no routes. These are plugged into the factory in Step 6 and filled in by Tasks 2 and 3.

**File:** `flask/modules/__init__.py` (new, empty)

**File:** `flask/modules/projects/__init__.py` (new, empty)

**File:** `flask/modules/projects/routes.py` (new)

**Pattern:**
```python
from flask import Blueprint

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

# Routes implemented in Task 2: Project CRUD Module
```

**File:** `flask/modules/context/__init__.py` (new, empty)

**File:** `flask/modules/context/routes.py` (new)

**Pattern:**
```python
from flask import Blueprint

context_bp = Blueprint('context', __name__)

# Routes implemented in Task 3: Context File Module
# Covers: /api/builder, /api/principles, /api/codebase, /api/references
```

**Verify:** `cd flask && python -c "from modules.projects.routes import projects_bp; from modules.context.routes import context_bp; print(projects_bp.name, context_bp.name)"` — prints `projects context`.

---

### Step 6: Create the App Factory

**Action:** Write create_app() — CORS at localhost:4201, Blueprint registration loop over ENABLED_MODULES, health route.

**File:** `flask/create_app.py` (new)

**Pattern:**
```python
import importlib
from flask import Flask, jsonify
from flask_cors import CORS

# Add module path + exported blueprint name here to register a new module.
# Tasks 2 and 3 do NOT edit this file — they are already in this list.
ENABLED_MODULES = [
    ('modules.projects.routes', 'projects_bp'),
    ('modules.context.routes',  'context_bp'),
]

def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.update(config)

    # CORS: Angular dev server is the only permitted origin
    CORS(app, origins=['http://localhost:4201'])

    # Register all modules. Import inside factory so failures surface at startup.
    for module_path, blueprint_attr in ENABLED_MODULES:
        module = importlib.import_module(module_path)
        bp = getattr(module, blueprint_attr)
        app.register_blueprint(bp)

    @app.get('/health')
    def health():
        return jsonify({'status': 'ok'})

    return app
```

**Verify:** `cd flask && python -c "from create_app import create_app; app = create_app(); print('blueprints:', list(app.blueprints.keys()))"` — prints `blueprints: ['projects', 'context']`.

---

### Step 7: Create the Entry Point

**Action:** Write app.py — calls create_app(), reads PORT env var (default 3101).

**File:** `flask/app.py` (new)

**Pattern:**
```python
import os
import sys

# Allow running from flask/ or from spec-doc/flask/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from create_app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3101))
    print(f'[Flask] Starting on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=True)
```

**Verify:** In one terminal, `cd flask && python app.py`. In another: `curl -s http://localhost:3101/health` — returns `{"status":"ok"}`. Kill the Flask process after verifying.

---

### Step 8: Create Test Fixtures and Tests

**Action:** Write pytest conftest and health tests.

**File:** `flask/tests/__init__.py` (new, empty)

**File:** `flask/tests/conftest.py` (new)

**Pattern:**
```python
import sys
import os

# Ensure flask/ is on the path regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from create_app import create_app

@pytest.fixture
def app():
    return create_app({'TESTING': True})

@pytest.fixture
def client(app):
    return app.test_client()
```

**File:** `flask/tests/test_health.py` (new)

**Pattern:**
```python
def test_health_status_200(client):
    response = client.get('/health')
    assert response.status_code == 200

def test_health_body_is_ok(client):
    response = client.get('/health')
    data = response.get_json()
    assert data == {'status': 'ok'}, f'expected {{"status": "ok"}}, got {data}'

def test_health_content_type_is_json(client):
    response = client.get('/health')
    assert 'application/json' in response.content_type

def test_cors_header_present_for_angular_origin(client):
    response = client.get('/health', headers={'Origin': 'http://localhost:4201'})
    assert 'Access-Control-Allow-Origin' in response.headers, \
        'CORS header missing — flask-cors may not be applied at factory level'

def test_cors_allows_angular_origin_exactly(client):
    response = client.get('/health', headers={'Origin': 'http://localhost:4201'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao == 'http://localhost:4201', \
        f'expected "http://localhost:4201", got "{acao}"'

def test_cors_does_not_allow_unknown_origin(client):
    response = client.get('/health', headers={'Origin': 'http://evil.example.com'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao != 'http://evil.example.com', \
        'Flask must not reflect arbitrary origins'

def test_projects_blueprint_registered(app):
    assert 'projects' in app.blueprints, \
        'projects Blueprint not registered — check ENABLED_MODULES in create_app.py'

def test_context_blueprint_registered(app):
    assert 'context' in app.blueprints, \
        'context Blueprint not registered — check ENABLED_MODULES in create_app.py'

def test_both_blueprints_registered(app):
    registered = set(app.blueprints.keys())
    assert {'projects', 'context'}.issubset(registered), \
        f'expected projects + context, got {registered}'
```

**Verify:** `cd flask && pytest tests/test_health.py -v` — 9 tests pass, 0 fail.

---

## 5. Tests

Framework: pytest (Python). Run from `flask/` directory.

```python
# flask/tests/test_health.py — complete assertion bodies

def test_health_status_200(client):
    response = client.get('/health')
    assert response.status_code == 200

def test_health_body_is_ok(client):
    response = client.get('/health')
    data = response.get_json()
    assert data == {'status': 'ok'}, f'expected {{"status": "ok"}}, got {data}'

def test_health_content_type_is_json(client):
    response = client.get('/health')
    assert 'application/json' in response.content_type

def test_cors_header_present_for_angular_origin(client):
    response = client.get('/health', headers={'Origin': 'http://localhost:4201'})
    assert 'Access-Control-Allow-Origin' in response.headers, \
        'CORS header missing — flask-cors may not be applied at factory level'

def test_cors_allows_angular_origin_exactly(client):
    response = client.get('/health', headers={'Origin': 'http://localhost:4201'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao == 'http://localhost:4201', \
        f'expected "http://localhost:4201", got "{acao}"'

def test_cors_does_not_allow_unknown_origin(client):
    response = client.get('/health', headers={'Origin': 'http://evil.example.com'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao != 'http://evil.example.com', \
        'Flask must not reflect arbitrary origins'

def test_projects_blueprint_registered(app):
    assert 'projects' in app.blueprints, \
        'projects Blueprint not registered — check ENABLED_MODULES in create_app.py'

def test_context_blueprint_registered(app):
    assert 'context' in app.blueprints, \
        'context Blueprint not registered — check ENABLED_MODULES in create_app.py'

def test_both_blueprints_registered(app):
    registered = set(app.blueprints.keys())
    assert {'projects', 'context'}.issubset(registered), \
        f'expected projects + context, got {registered}'
```

---

## 6. Commit Plan

One commit per logical unit:

1. `docs(flask): add full API contract document` — flask/api-contract.md: all Phase 1 routes, request/response shapes, error conventions, Phase 2 routes explicitly listed as deferred
2. `feat(flask): app factory, CORS, health route, Blueprint stubs` — flask/requirements.txt, flask/config.py, flask/create_app.py, flask/app.py, flask/modules/__init__.py, flask/modules/projects/__init__.py, flask/modules/projects/routes.py, flask/modules/context/__init__.py, flask/modules/context/routes.py
3. `test(flask): health, CORS, and Blueprint registration tests` — flask/tests/__init__.py, flask/tests/conftest.py, flask/tests/test_health.py

Deviation logging: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Python tests (from flask/ directory)
cd flask && pytest tests/ -v
# Expected: 9 passed, 0 failed, 0 errors

# Manual smoke test (Flask on 3101, Express on 3100 simultaneously)
python app.py &
FLASK_PID=$!
curl -s http://localhost:3101/health
# Expected: {"status":"ok"}
curl -s http://localhost:3100/api/projects | python3 -m json.tool | head -5
# Expected: valid JSON array from Express (confirms coexistence)
kill $FLASK_PID

# JS test suite must be unaffected (run from spec-doc/ root)
cd .. && npm run test:server
# Expected: same pass count as baseline recorded in Pre-flight
```

Expected delta: 0 → 9 Python tests passing. Zero pre-existing JS tests broken.

---

## 8. Rollback

Per-step:
- Each commit is independently revertible: `git revert <sha>`
- Task 1 creates only new files; revert removes them cleanly with no side effects on existing code

Per-branch (catastrophic failure):
- `git reset --hard <pre-task-sha>` returns to the state before Task 1 started
- Or: `rm -rf flask/` if commits haven't been made yet (no data loss — all files are new)

Express is unaffected in all rollback scenarios because Task 1 does not modify server.js or any existing file.

---

## 9. Deviations Allowed

- **flask-cors CORS header behavior differs from expected** — CORS behavior varies by version. If `test_cors_does_not_allow_unknown_origin` fails because flask-cors is reflecting origins despite configuration, pass `supports_credentials=False` and `origins=['http://localhost:4201']` explicitly to `CORS()`. Log deviation in commit body.
- **Python version incompatibility** — if flask>=3.0.0 requires Python 3.10+ and the environment has an older Python, pin `flask>=2.3.0,<3.0` and `flask-cors>=4.0`. Log in commit body.
- **Test framework mismatch** — guide specifies pytest; if the environment lacks pytest and cannot install it, translate to unittest with unittest.TestCase. Note translation in commit body.
- **Step N simplification for Step N+1** — if the importlib.import_module loop in create_app.py can be replaced with a simpler direct import pattern without losing extensibility, take it, log the deviation.
- **Side-effect required (pip install outside virtualenv, system-level change)** → STOP, mark [REQUIRES APPROVAL] and flag to the user.
- **projects/ directory count differs** — if `ls projects/ | wc -l` returns a different number than expected, note it in the Step 1 verify output; do not abort. The count is informational, not a gate.

---

## 10. Out of Scope

This task scaffolds the Flask application shell and documents the API contract. It does not implement any of the routes it documents. Tasks 2 and 3 fill in the Blueprint bodies; Task 4 ports the chain module. Any code that touches actual business logic, filesystem reads/writes, or AI calls is explicitly deferred.

- Project CRUD route implementations (GET/POST /api/projects, GET/DELETE /api/projects/:id, PUT /api/projects/:id/files/:filename) — deferred to Task 2; the Blueprint stub is the only deliverable here
- Context file route implementations (GET/PUT /api/builder, /api/principles, /api/codebase, /api/references) — deferred to Task 3
- Chain module port (adapter, providers, file marker parser, context block loader) — deferred to Task 4; not referenced from any Task 1 file
- AI text endpoints (/api/ai/text/*) — Phase 2; not documented as Task 1 deliverables and not stubbed out (no half-finished surfaces)
- SSE streaming (/api/ai/implement) — Phase 2; Flask-SSE setup is a separate concern
- Container routes (/api/container/*) — Phase 2+; Docker integration is not in Phase 1 scope
- Angular proxy setup — the Angular services hardcode localhost:3100; no proxy config exists and none is created in this task; the cutover strategy (ENV swap or port reassignment) is a Phase 1 completion decision, not a Task 1 decision
- projects/ directory anomalies — if Step 1 finds malformed project.json files, note them and move on; remediation is Task 2's concern during route implementation
- Virtualenv / Python environment management — the executor installs into whatever Python environment is active; environment setup is a prerequisite, not a task deliverable

Rule for the executor: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- `specs/architecture.md` — component design rationale, ENABLED_MODULES pattern
- `specs/epic.md` — task scope and port budget (~80 lines)
- `specs/timeline.md` — update Task 1 status to done after verification passes
