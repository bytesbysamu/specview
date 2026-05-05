Now I have complete context. Let me write the implementation guide.

# Task 1: Flask Scaffold + Core Config + Walker

**Purpose**: Stand up the Flask app factory with CORS, module registry, health endpoint, config, and a Python port of the filesystem walker — the foundation every subsequent task depends on.

**Effort**: 0.5 days

**Dependencies**: None

**Parallel With**: —

**Blocks**: Task 2 (Project CRUD — needs `walker.py` for file tree listing), Task 3 (Context Files — needs app factory + config), Task 4 (Chain Module — needs `core/` package structure)

**Related**:
- [Epic](projects/v2-spec-doc-backend-foundation-project-management-1776868958774/epic.md)
- [Analysis](projects/v2-spec-doc-backend-foundation-project-management-1776868958774/analysis.md)
- [References](references.md) — bubls app factory, config pattern

---

## 1. Context

This task creates the Python backend skeleton that replaces the 1,652-line Express monolith in `server.js`. It ports two things: the Flask app factory pattern from Bubls (`references.md` → `bubls/server/app.py`, 70 lines) and the filesystem walker from `server/walker.js` (74 lines). The app factory uses a module registry (`ENABLED_MODULES` list) so future tasks add features by creating a folder and appending one import string. The walker converts JS `fs.readdirSync` + recursive traversal into Python `os.scandir` with the same output shape: `{ tree, sourceFiles, entryPoints }`. Config resolves the Analysis open question on env var naming: `CHAIN_PROVIDER` is canonical (matches Bubls), `AI_PROVIDER` is accepted as a fallback alias.

**Trade-offs considered**:
- **FastAPI instead of Flask** — rejected because the builder's primary stack is Flask, Bubls infrastructure is Flask, and there's no async requirement for filesystem I/O
- **Reuse `server/walker.js` via subprocess from Python** — rejected because it adds a Node dependency to the Python backend and makes testing harder; the walker is 74 lines, porting is cheaper than bridging
- **Flask app factory with `ENABLED_MODULES` (chosen)** — preferred because it's a proven pattern from Bubls (164 tests, 3 shipped epics), makes adding modules a one-line change, and the reference code is verbatim-portable

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- server/                      # Confirm server/ dir has only walker.js
node --test server.test.js                    # Record baseline: expect 60+ passing
python3 --version                             # Confirm Python 3.10+
pip3 show flask flask-cors                    # Check if already installed
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting. Note: `server.js` and `references.md` show as modified in the current git status — these are unrelated to this task and should be committed or stashed first.

**Baseline recorded**: server.test.js should show all existing tests passing. Python tests start at 0.

---

## 3. Files

### To Create (new)
- `server/core/__init__.py` (new) — empty package marker for the `core` module
- `server/core/config.py` (new) — env var loading: PORT, WEB_ORIGIN, CHAIN_PROVIDER (with AI_PROVIDER fallback), PROJECTS_DIR, CONTEXT_PROVIDER; ported from `references.md` → bubls `core/config.py`
- `server/core/walker.py` (new) — Python port of `server/walker.js`; `os.scandir` recursive walk with same `IGNORE_DIRS`, `SOURCE_EXT`, `ENTRY_FILES`; returns `{ root_path, tree, source_files, entry_points }`
- `server/app.py` (new) — Flask app factory with CORS, `ENABLED_MODULES` registry, `/api/health` endpoint; ported from `references.md` → bubls `app.py`
- `server/__init__.py` (new) — empty package marker so `server` is importable
- `server/tests/__init__.py` (new) — empty package marker for test discovery
- `server/tests/test_walker.py` (new) — pytest tests for walker: ignore dirs, source extension filtering, entry point capture, depth limiting
- `server/tests/test_app.py` (new) — pytest tests for app factory: health endpoint returns modules list, CORS headers present, module registry loads
- `server/requirements.txt` (new) — Flask, flask-cors, pytest, python-dotenv
- `server/.env.example` (new) — documented env vars with defaults

### To Modify
- `.gitignore` — add `__pycache__/`, `.venv/`, `*.pyc`, `server/.env` entries for Python

### To Leave Alone
- `server.js` — still the production Express backend; runs alongside Flask during migration
- `server/walker.js` — JS version stays until V2 is fully migrated; Express still imports it
- `server.test.js` — Express-specific tests, unaffected by Python backend
- `package.json` — Node scripts stay; Python uses its own `requirements.txt`
- `src/` — Angular frontend, zero changes
- `references.md` — read-only reference for port sources

---

## 4. Implementation Steps

### Step 1: Create Python package structure

**Action**: Create the directory skeleton and empty `__init__.py` files.

**Files**: `server/__init__.py` (new), `server/core/__init__.py` (new), `server/tests/__init__.py` (new)

**Pattern**:
```python
# server/__init__.py, server/core/__init__.py, server/tests/__init__.py
# Empty — package markers only
```

**Verify**: `python3 -c "import server; import server.core"` — expect no errors

### Step 2: Port config from Bubls

**Action**: Create `server/core/config.py` porting from `references.md` → bubls `core/config.py` (lines 497–513). Resolve the env var naming open question: `CHAIN_PROVIDER` is canonical, `AI_PROVIDER` accepted as fallback via `os.environ.get("CHAIN_PROVIDER") or os.environ.get("AI_PROVIDER", "cli")`.

**File**: `server/core/config.py` (new)

**Pattern** (ported from `references.md` → bubls `core/config.py`):
```python
"""Env loading + pinned constants for spec-doc V2 backend."""
import os
from pathlib import Path

from dotenv import load_dotenv

_SERVER_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _SERVER_ROOT.parent

load_dotenv(_SERVER_ROOT / ".env", override=False)

# Server
PORT: int = int(os.environ.get("PORT", "3100"))
WEB_ORIGIN: str = os.environ.get("WEB_ORIGIN", "http://localhost:4201")

# AI provider: CHAIN_PROVIDER is canonical (matches Bubls),
# AI_PROVIDER accepted as fallback for backwards compat with Express.
CHAIN_PROVIDER: str = os.environ.get("CHAIN_PROVIDER") or os.environ.get("AI_PROVIDER", "cli")
CONTEXT_PROVIDER: str = os.environ.get("CONTEXT_PROVIDER", "")

# Filesystem paths
PROJECTS_DIR: Path = _PROJECT_ROOT / "projects"
```

**Verify**: `CHAIN_PROVIDER=mock python3 -c "from server.core.config import CHAIN_PROVIDER; assert CHAIN_PROVIDER == 'mock'"` — expect no errors. Then: `AI_PROVIDER=mock python3 -c "from server.core.config import CHAIN_PROVIDER; assert CHAIN_PROVIDER == 'mock'"` — confirms fallback works.

### Step 3: Port walker from JS to Python

**Action**: Port `server/walker.js` (74 lines) to Python using `os.scandir` for recursive traversal. Preserve the same constants: `IGNORE_DIRS`, `SOURCE_EXT`, `ENTRY_FILES`. Return a dict with same shape: `{ root_path, tree, source_files, entry_points }`.

**File**: `server/core/walker.py` (new), porting from `server/walker.js` lines 1–74

**Pattern**:
```python
"""Filesystem walker — port of server/walker.js to Python os.scandir.

Walks a project directory, collecting:
- tree: list of {path, type, depth} nodes
- source_files: list of {path, lines, head} for source code files
- entry_points: dict of filename → content for known entry files
"""
from __future__ import annotations

import os
from pathlib import Path

IGNORE_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "dist", "www", "ios", "android",
    ".angular", "__pycache__", ".venv", "migrations/versions",
    "build", ".next", ".cache",
})

SOURCE_EXT: frozenset[str] = frozenset({".ts", ".tsx", ".js", ".jsx", ".py"})

ENTRY_FILES: tuple[str, ...] = (
    "package.json", "requirements.txt", "pyproject.toml",
    "src/app/app.routes.ts", "src/app/shell/feature-registry.ts",
    "server/app.py", "angular.json", "capacitor.config.ts",
)


def walk_project(root_path: str | Path, max_depth: int = 3) -> dict:
    root = Path(root_path)
    tree: list[dict] = []
    source_files: list[dict] = []
    entry_points: dict[str, str] = {}

    # Collect entry points
    for ef in ENTRY_FILES:
        full = root / ef
        if full.is_file():
            try:
                entry_points[ef] = full.read_text(encoding="utf-8")
            except OSError:
                pass

    def _walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(os.scandir(directory), key=lambda e: e.name)
        except OSError:
            return
        for entry in entries:
            rel = str(Path(entry.path).relative_to(root))
            if entry.is_dir(follow_symlinks=False):
                if entry.name in IGNORE_DIRS:
                    continue
                tree.append({"path": rel, "type": "dir", "depth": depth})
                _walk(Path(entry.path), depth + 1)
            elif entry.is_file(follow_symlinks=False):
                ext = os.path.splitext(entry.name)[1]
                if ext in SOURCE_EXT:
                    try:
                        content = Path(entry.path).read_text(encoding="utf-8")
                        lines = content.count("\n") + 1
                        head = "\n".join(content.split("\n")[:10])
                        source_files.append({"path": rel, "lines": lines, "head": head})
                        tree.append({"path": rel, "type": "file", "depth": depth})
                    except OSError:
                        pass

    _walk(root, 0)
    return {
        "root_path": str(root),
        "tree": tree,
        "source_files": source_files,
        "entry_points": entry_points,
    }
```

**Verify**: `python3 -c "from server.core.walker import walk_project; r = walk_project('.'); print(len(r['source_files']), 'source files')"` — should find source files and print a count > 0

### Step 4: Create Flask app factory

**Action**: Create the Flask app factory porting from `references.md` → bubls `app.py` (lines 18–71). `ENABLED_MODULES` starts empty (Tasks 2–4 add modules). Health endpoint returns `{ status, modules }`.

**File**: `server/app.py` (new), porting from `references.md` → bubls `app.py`

**Pattern**:
```python
"""Flask app factory with module registry.

Modules are self-contained feature folders under ``modules/``. Toggle a feature
by adding/removing its import path in ``ENABLED_MODULES``. Each module exposes
a Blueprint named ``bp`` in its ``routes`` submodule.

Ported from: references.md → bubls/server/app.py (70 lines)
"""
from __future__ import annotations

import importlib

from flask import Flask
from flask_cors import CORS

from .core.config import WEB_ORIGIN

# Module registry — Tasks 2-4 add entries here.
ENABLED_MODULES: list[str] = []


def create_app() -> Flask:
    app = Flask(__name__)

    CORS(
        app,
        origins=[
            origin
            for origin in [
                "http://localhost:4201",
                WEB_ORIGIN,
            ]
            if origin
        ],
        supports_credentials=False,
    )

    for module_path in ENABLED_MODULES:
        bp = importlib.import_module(f"server.{module_path}.routes").bp
        app.register_blueprint(bp)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "modules": [m.split(".")[-1] for m in ENABLED_MODULES],
        }

    return app


if __name__ == "__main__":
    from .core.config import PORT
    create_app().run(port=PORT, debug=True)
```

**Verify**: `cd {WORKSPACE} && FLASK_APP=server.app python3 -m flask run --port 3101` then `curl http://localhost:3101/api/health` — expect `{"modules":[],"status":"ok"}`

### Step 5: Create requirements.txt

**Action**: Pin Flask and test dependencies.

**File**: `server/requirements.txt` (new)

**Pattern**:
```
flask>=3.0,<4.0
flask-cors>=5.0,<6.0
python-dotenv>=1.0,<2.0
pytest>=8.0,<9.0
```

**Verify**: `pip3 install -r server/requirements.txt` — expect clean install with no errors

### Step 6: Create .env.example

**Action**: Document env vars with defaults for developer onboarding.

**File**: `server/.env.example` (new)

**Pattern**:
```bash
# Flask V2 backend — copy to .env and edit as needed

# Server
PORT=3100
WEB_ORIGIN=http://localhost:4201

# AI provider: cli (default) | claude | mock
# CHAIN_PROVIDER is canonical; AI_PROVIDER accepted as fallback
CHAIN_PROVIDER=cli

# Context provider: leave empty for filesystem (default), "mock" for tests
# CONTEXT_PROVIDER=
```

**Verify**: file exists and is readable

### Step 7: Update .gitignore for Python

**Action**: Add Python-specific ignores.

**File**: `.gitignore` (modify — add after the existing `# Node` section)

**Pattern**:
```gitignore
# Python
__pycache__/
*.pyc
.venv/
server/.env
*.egg-info/
```

**Verify**: `git diff .gitignore` — shows only the new Python entries

### Step 8: Write walker tests

**Action**: Write pytest tests for `walk_project` that mirror the assertions in `server.test.js` lines 449–486 (section 12: Codebase Context). Tests use the spec-doc repo itself as the test fixture — same approach as the JS tests.

**File**: `server/tests/test_walker.py` (new)

**Pattern**:
```python
"""Walker tests — mirrors server.test.js section 12 (Codebase Context)."""
import pytest
from pathlib import Path

from server.core.walker import walk_project, IGNORE_DIRS, SOURCE_EXT, ENTRY_FILES

# Use the spec-doc project root as the fixture (same as JS tests)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestWalkProject:
    """Port of server.test.js walker assertions."""

    def test_excludes_ignored_directories(self):
        """Mirrors: 'walker excludes node_modules, .git, dist'."""
        result = walk_project(PROJECT_ROOT, max_depth=2)
        ignored_present = any(
            node["path"].startswith(d)
            for node in result["tree"]
            for d in ("node_modules", ".git", "dist")
        )
        assert not ignored_present, "walker should skip ignored directories"

    def test_returns_tree_source_files_entry_points(self):
        """Mirrors: 'walker returns tree, sourceFiles, entryPoints'."""
        result = walk_project(PROJECT_ROOT, max_depth=2)
        assert isinstance(result["tree"], list), "result.tree should be a list"
        assert isinstance(result["source_files"], list), "result.source_files should be a list"
        assert isinstance(result["entry_points"], dict), "result.entry_points should be a dict"
        assert "package.json" in result["entry_points"], "should capture package.json as entry point"
        assert any(f["path"] == "server.js" for f in result["source_files"]), \
            "should find server.js among source files"

    def test_source_files_have_required_fields(self):
        """Each source file entry has path, lines, head."""
        result = walk_project(PROJECT_ROOT, max_depth=2)
        assert len(result["source_files"]) > 0, "should find at least one source file"
        for sf in result["source_files"]:
            assert "path" in sf, "source file should have 'path'"
            assert "lines" in sf, "source file should have 'lines'"
            assert "head" in sf, "source file should have 'head'"
            assert isinstance(sf["lines"], int), "lines should be an int"
            assert sf["lines"] > 0, "lines should be positive"

    def test_respects_max_depth(self):
        """max_depth=0 should only capture top-level entries."""
        result = walk_project(PROJECT_ROOT, max_depth=0)
        for node in result["tree"]:
            assert node["depth"] == 0, \
                f"with max_depth=0, no entry should exceed depth 0, got {node['path']} at depth {node['depth']}"

    def test_tree_nodes_have_correct_types(self):
        """Tree nodes are either 'dir' or 'file'."""
        result = walk_project(PROJECT_ROOT, max_depth=1)
        for node in result["tree"]:
            assert node["type"] in ("dir", "file"), \
                f"node type should be 'dir' or 'file', got {node['type']}"

    def test_only_source_extensions_collected(self):
        """Only .ts, .tsx, .js, .jsx, .py files appear in source_files."""
        result = walk_project(PROJECT_ROOT, max_depth=3)
        for sf in result["source_files"]:
            ext = Path(sf["path"]).suffix
            assert ext in SOURCE_EXT, \
                f"source file {sf['path']} has extension {ext} not in SOURCE_EXT"

    def test_head_contains_first_10_lines(self):
        """head field should have at most 10 lines."""
        result = walk_project(PROJECT_ROOT, max_depth=2)
        for sf in result["source_files"][:5]:  # spot-check first 5
            head_lines = sf["head"].split("\n")
            assert len(head_lines) <= 10, \
                f"head for {sf['path']} has {len(head_lines)} lines, expected <= 10"

    def test_nonexistent_path_returns_empty(self):
        """Nonexistent root path returns empty collections gracefully."""
        result = walk_project("/nonexistent/path/that/does/not/exist", max_depth=3)
        assert result["tree"] == []
        assert result["source_files"] == []
        # entry_points may be empty since the path doesn't exist
        assert isinstance(result["entry_points"], dict)
```

**Verify**: `cd {WORKSPACE} && python3 -m pytest server/tests/test_walker.py -v` — expect 8 passing

### Step 9: Write app factory tests

**Action**: Write pytest tests for the Flask app factory and health endpoint.

**File**: `server/tests/test_app.py` (new)

**Pattern**:
```python
"""App factory tests — validates Flask scaffold, CORS, health endpoint."""
import pytest
from server.app import create_app, ENABLED_MODULES


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestHealthEndpoint:

    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_health_returns_modules_list(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        assert isinstance(data["modules"], list)

    def test_health_modules_matches_enabled(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        expected = [m.split(".")[-1] for m in ENABLED_MODULES]
        assert data["modules"] == expected


class TestCORS:

    def test_cors_allows_localhost_4201(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:4201",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:4201"

    def test_cors_blocks_unknown_origin(self, client):
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # flask-cors returns no Allow-Origin header for disallowed origins
        allow_origin = resp.headers.get("Access-Control-Allow-Origin")
        assert allow_origin != "http://evil.example.com"


class TestAppFactory:

    def test_create_app_returns_flask_instance(self):
        app = create_app()
        assert app is not None
        assert hasattr(app, "test_client")

    def test_404_for_unknown_route(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
```

**Verify**: `cd {WORKSPACE} && python3 -m pytest server/tests/test_app.py -v` — expect 7 passing

---

## 5. Tests

The repo uses `node:test` + `assert/strict` for the Express backend. The Python backend introduces `pytest` (matches Bubls convention per `references.md`). All tests above have complete assertion bodies — no stubs.

Test files:
- `server/tests/test_walker.py` — 8 tests: ignore dirs, source extension filter, entry points, max depth, node types, head truncation, nonexistent path, required fields
- `server/tests/test_app.py` — 7 tests: health status, health modules list, modules match registry, CORS allow, CORS block, factory returns Flask, 404 for unknown route

Total new tests: **15**

To run all Python tests:
```bash
cd {WORKSPACE} && python3 -m pytest server/tests/ -v
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(server): add Python package structure + config` — `server/__init__.py`, `server/core/__init__.py`, `server/core/config.py`, `server/.env.example`, `.gitignore`: scaffold Python packages and env var config with CHAIN_PROVIDER/AI_PROVIDER fallback
2. `feat(server): port walker.js to Python os.scandir` — `server/core/walker.py`: port JS walker preserving IGNORE_DIRS, SOURCE_EXT, ENTRY_FILES constants and output shape
3. `feat(server): Flask app factory with module registry` — `server/app.py`, `server/requirements.txt`: app factory with CORS, ENABLED_MODULES, /api/health; ported from bubls
4. `test(server): walker + app factory pytest suite` — `server/tests/`: 15 tests covering walker behavior and health endpoint

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Python tests
cd {WORKSPACE} && python3 -m pytest server/tests/ -v

# Existing JS tests still pass (no changes to Express)
node --test server.test.js

# Smoke test: health endpoint
FLASK_APP=server.app python3 -m flask run --port 3101 &
curl -s http://localhost:3101/api/health | python3 -m json.tool
kill %1
```

**Expected delta**: Python tests: 0 → 15 passing. JS tests: unchanged (all existing tests still pass). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch. [REQUIRES APPROVAL]
- **Dependency note**: No existing code depends on the new Python files. Reverting any or all commits has zero impact on the running Express backend.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it, do not invent.
- **Test framework mismatch** → match the repo's convention; Python code uses pytest (matches Bubls), JS stays on `node:test`. Translate silently but note in commit body.
- **Flask or flask-cors version differs** → accept any version within the pinned range in `requirements.txt`.
- **`os.scandir` unavailable on target Python** → fall back to `os.listdir`; flag as deviation.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task ships only the scaffold: app factory, config, walker, and health endpoint. It does NOT create any module folders under `server/modules/`, wire any real endpoints beyond `/api/health`, or install AI dependencies. The `ENABLED_MODULES` list is intentionally empty.

- **`server/modules/project/`** — deferred to Task 2; this task only creates the registry pattern that Task 2 plugs into
- **`server/modules/context_files/`** — deferred to Task 3
- **`server/modules/chain/`** — deferred to Task 4; no AI infrastructure before a consumer exists
- **`server/core/database.py`** — explicitly out of scope per epic ("no DB in V1")
- **Auth middleware** — explicitly out of scope per epic ("single-user")
- **Logging configuration** — Flask defaults suffice; add structured logging when production deployment is planned
- **`__main__.py` runner script** — the `if __name__ == "__main__"` block in `app.py` suffices for development; a proper entrypoint script is a Task 2+ concern when the server needs to be started with modules loaded
- **npm script for Python** — do not add `"api:v2"` to `package.json`; the Python backend runs via flask CLI or python directly

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Epic](projects/v2-spec-doc-backend-foundation-project-management-1776868958774/epic.md) – Task scope
- [Analysis](projects/v2-spec-doc-backend-foundation-project-management-1776868958774/analysis.md) – Open questions resolved (env var naming, chain module deferral)
- [References](references.md) – Port source code (bubls app.py, config.py, walker.js)
- Timeline – Update status to `done` after verification passes