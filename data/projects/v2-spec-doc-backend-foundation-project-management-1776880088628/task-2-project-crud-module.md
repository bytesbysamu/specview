Now I have all the exact server.js handler code. Writing the guide.

# Task 2: Project CRUD Module

**Purpose**: Implement five Flask route handlers that replicate the Express project CRUD API exactly, so the Angular sidebar and editor work identically against Flask as against Express. The module is the highest-traffic backend surface — every sidebar load and every auto-save call passes through it.

**Effort**: 1 day

**Dependencies**: Task 1 (Flask Scaffold + Core Config) must be complete — requires `server/app.py`, `server/core/config.py`, and the pytest harness.

**Parallel With**: Task 3 (Context File Module) — independent modules, share only the app factory registration step.

**Blocks**: End-to-end Angular ↔ Flask smoke test; Task 3 Context File Module (same pattern); Phase 2 cutover from Express to Flask.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task ports five Express route handlers (lines 469–612 of `server.js`) into a Flask Blueprint at `server/modules/project/`. The 68 existing project directories under `projects/` are the ground truth — no migration, no schema change. The contract is locked by reading the live Express handlers verbatim: response key is `specs` (not `files`), label is derived by stripping `.md`, replacing hyphens with spaces, and title-casing, and the list is sorted by `createdAt` descending. Flask must match every field name, status code, and sort order or Angular breaks silently. The module follows the Bubls layered pattern from `references.md`: thin route handlers in `routes.py` call pure filesystem helpers in `service.py`; helpers accept `projects_dir: Path` as a parameter so tests pass `tmp_path` without monkeypatching globals. A path traversal guard anchors all operations to `projects/` root — Express omits this check, Flask adds it as a security boundary.

**Trade-offs considered**:
- **Pydantic DTOs** — rejected; the five response shapes are flat dicts with 3–4 fields each. Pydantic adds ~50 lines of ceremony and a dependency for zero runtime benefit over `jsonify()`.
- **Single `projects.py` module (flat, no subpackage)** — rejected; `references.md` Bubls pattern uses `modules/{name}/routes.py` + `service.py`. The flat approach breaks the pattern every Phase 2 module will follow.
- **Blueprint + service.py with injected `projects_dir` (chosen)** — preferred because it matches Bubls exactly, keeps handlers to ≤10 lines each, and lets tests run without any real filesystem state.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm Task 1 scaffold exists
ls server/app.py server/core/config.py server/requirements.txt

# Confirm working tree is clean on target files
git status
git diff HEAD -- server/modules/ server/app.py server/core/config.py

# Run existing pytest baseline — record the count
cd {WORKSPACE}/spec-doc && python -m pytest server/tests/ -v 2>&1 | tail -5

# Verify the 68 existing project dirs are well-formed (no missing project.json)
python3 -c "
import json
from pathlib import Path
root = Path('projects')
ok, bad = 0, []
for d in root.iterdir():
    if d.is_dir():
        meta = d / 'project.json'
        if meta.exists():
            try:
                data = json.loads(meta.read_text())
                assert 'name' in data and 'createdAt' in data
                ok += 1
            except Exception as e:
                bad.append((d.name, str(e)))
        else:
            bad.append((d.name, 'missing project.json'))
print(f'OK: {ok}, BAD: {len(bad)}')
for name, err in bad:
    print(f'  BAD: {name}: {err}')
"
```

**Expected**: `server/app.py` and `server/core/config.py` exist. Pytest baseline is 15 passing (from Task 1). All 68 project dirs pass the well-formedness check (0 BAD).

**If any project dir is BAD**: do not proceed. Investigate that directory — it may contain manually created content without `project.json`. The route handler must handle the missing-metadata case gracefully (skip in list, return 404 on get).

**If working tree is dirty on target files**: stash or commit unrelated changes first. The current `git status` shows `references.md` and `src/app/components/new-project/new-project.component.ts` modified — these are pre-existing and should NOT be touched by this task.

---

## 3. Files

### To Create (new)
- `server/modules/__init__.py` (new) — empty package marker; required for `importlib.import_module("modules.project.routes")` to resolve
- `server/modules/project/__init__.py` (new) — empty package marker
- `server/modules/project/service.py` (new) — pure filesystem helpers: list, get, create, update_file, delete; all accept `projects_dir: Path`; no Flask imports
- `server/modules/project/routes.py` (new) — Blueprint `bp`; five thin route handlers that call service functions with `PROJECTS_DIR` from config; all business logic in service
- `server/tests/test_project.py` (new) — pytest tests for both service functions and HTTP endpoints

### To Modify (cite CODEBASE CONTEXT)
- `server/app.py` (Task 1 output) — add `"modules.project"` to `ENABLED_MODULES` list; currently `[]`
- `server/core/config.py` (Task 1 output) — add `PROJECTS_DIR: Path` constant if not already present; Task 1 plan mentions it but verify the actual file

### To Leave Alone
- `projects/` — all 68 project directories; no migration, no writes during this task
- `server.js` — Express continues running on port 3100 during migration; Flask runs on 3101
- `src/app/services/projects.service.ts` — zero Angular changes; if Flask requires an Angular change to work, the Flask route is wrong
- `server/core/walker.py` — Task 1 output; not consumed by this module
- `server/tests/test_walker.py`, `server/tests/test_app.py` — Task 1 tests; must remain passing after this task

---

## 4. Implementation Steps

### Step 1: Verify `server/core/config.py` has `PROJECTS_DIR`

**Action**: Read `server/core/config.py`. If `PROJECTS_DIR` is absent, add it. The path must resolve to `spec-doc/projects/` regardless of where Flask is started from.

**File**: `server/core/config.py` (Task 1 output — verify before editing)

**Pattern**:
```python
# Add to server/core/config.py if not present
import os
from pathlib import Path
from dotenv import load_dotenv

_SERVER_ROOT = Path(__file__).resolve().parent.parent     # server/
_WORKSPACE_ROOT = _SERVER_ROOT.parent                     # spec-doc/

load_dotenv(_SERVER_ROOT / ".env", override=False)

PORT: int = int(os.environ.get("PORT", "3101"))           # 3101 = Flask dev port
WEB_ORIGIN: str = os.environ.get("WEB_ORIGIN", "http://localhost:4201")
AI_PROVIDER: str = os.environ.get("CHAIN_PROVIDER",
                    os.environ.get("AI_PROVIDER", "cli"))
CONTEXT_PROVIDER: str = os.environ.get("CONTEXT_PROVIDER", "")

PROJECTS_DIR: Path = Path(os.environ.get(
    "PROJECTS_DIR",
    str(_WORKSPACE_ROOT / "projects")
)).resolve()
```

**Verify**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'server')
from core.config import PROJECTS_DIR
print(PROJECTS_DIR)
assert PROJECTS_DIR.exists(), f'projects dir not found: {PROJECTS_DIR}'
print('OK')
"
```
Expect: prints the absolute path ending in `spec-doc/projects` and `OK`.

---

### Step 2: Create module package structure

**Action**: Create four empty files to establish the package hierarchy.

**Files**: `server/modules/__init__.py`, `server/modules/project/__init__.py` (both new, empty)

**Pattern**:
```bash
mkdir -p server/modules/project
touch server/modules/__init__.py
touch server/modules/project/__init__.py
```

**Verify**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'server')
import modules.project
print('OK')
"
```
Expect: `OK` with no import errors.

---

### Step 3: Implement `service.py` — filesystem helpers

**Action**: Write five pure functions that replicate the Express handler logic exactly. Port the label derivation from `server.js:484` (`f.replace('.md', '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())`), the slug logic from `server.js:546–548`, and the ID format from `server.js:550`.

**File**: `server/modules/project/service.py` (new)

**Pattern** (complete implementation — port from `server.js:469–612`):
```python
"""Project CRUD service — pure filesystem helpers.

Ported from server.js lines 469–612. No Flask imports.
All functions accept projects_dir: Path for test isolation.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers — ported verbatim from server.js logic
# ---------------------------------------------------------------------------

def _filename_to_label(filename: str) -> str:
    """Port of server.js:484 label derivation.

    JS: f.replace('.md', '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    """
    return filename.replace(".md", "").replace("-", " ").title()


def _make_id(name: str) -> str:
    """Port of server.js:546–550 slug+timestamp ID.

    JS: slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
        id   = `${slug}-${Date.now()}`
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    timestamp = int(time.time() * 1000)  # milliseconds, matches Date.now()
    return f"{slug}-{timestamp}"


def _safe_path(projects_dir: Path, project_id: str) -> Path:
    """Resolve project path and reject traversal attempts.

    Express omits this check; Flask adds it as a security boundary.
    Raises ValueError if resolved path escapes projects_dir.
    """
    resolved = (projects_dir / project_id).resolve()
    if not str(resolved).startswith(str(projects_dir.resolve())):
        raise ValueError(f"Path traversal attempt: {project_id!r}")
    return resolved


def _read_specs(project_path: Path, *, include_content: bool) -> list[dict]:
    """Read .md files from a project directory and build specs list."""
    specs = []
    for f in sorted(project_path.glob("*.md")):
        spec: dict = {
            "filename": f.name,
            "label": _filename_to_label(f.name),
        }
        if include_content:
            spec["content"] = f.read_text(encoding="utf-8")
        specs.append(spec)
    return specs


# ---------------------------------------------------------------------------
# Public API — one function per route
# ---------------------------------------------------------------------------

def list_projects(projects_dir: Path) -> list[dict]:
    """GET /api/projects — port of server.js:469–503."""
    results = []
    for d in projects_dir.iterdir():
        meta_path = d / "project.json"
        if not d.is_dir() or not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue  # skip corrupt/unreadable entries gracefully
        results.append({
            "id": d.name,
            "name": meta["name"],
            "createdAt": meta["createdAt"],
            "specs": _read_specs(d, include_content=False),
        })
    # Sort newest first — port of server.js:497
    results.sort(key=lambda p: p["createdAt"], reverse=True)
    return results


def get_project(projects_dir: Path, project_id: str) -> dict | None:
    """GET /api/projects/:id — port of server.js:506–534.

    Returns None if project not found (caller returns 404).
    """
    project_path = _safe_path(projects_dir, project_id)
    meta_path = project_path / "project.json"
    if not project_path.exists() or not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "id": project_id,
        "name": meta["name"],
        "createdAt": meta["createdAt"],
        "specs": _read_specs(project_path, include_content=True),
    }


def create_project(projects_dir: Path, name: str, files: list[dict]) -> dict:
    """POST /api/projects — port of server.js:537–578.

    files: [{"filename": str, "content": str}]
    Returns: {"id": str, "name": str, "createdAt": str}
    """
    project_id = _make_id(name)
    project_path = projects_dir / project_id
    project_path.mkdir(parents=True, exist_ok=True)

    created_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    meta = {"name": name, "createdAt": created_at}
    (project_path / "project.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    for f in files:
        (project_path / f["filename"]).write_text(f["content"], encoding="utf-8")

    return {"id": project_id, "name": name, "createdAt": created_at}


def update_file(projects_dir: Path, project_id: str, filename: str, content: str) -> bool:
    """PUT /api/projects/:id/files/:filename — port of server.js:581–596.

    Returns False if project directory not found (caller returns 404).
    """
    project_path = _safe_path(projects_dir, project_id)
    if not project_path.exists():
        return False
    (project_path / filename).write_text(content, encoding="utf-8")
    return True


def delete_project(projects_dir: Path, project_id: str) -> bool:
    """DELETE /api/projects/:id — port of server.js:599–613.

    Returns False if not found (caller returns 404).
    """
    project_path = _safe_path(projects_dir, project_id)
    if not project_path.exists():
        return False
    shutil.rmtree(project_path)
    return True
```

**Verify**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'server')
from modules.project.service import (
    list_projects, get_project, create_project, update_file, delete_project
)
print('imports OK')
"
```
Expect: `imports OK` with no errors.

---

### Step 4: Implement `routes.py` — Blueprint with five handlers

**Action**: Write the Blueprint with five thin route handlers. Each handler validates input, calls the matching service function with `PROJECTS_DIR`, and returns the correct status code. Match Express status codes: 201 for create, 404 for not-found, 400 for missing required fields, 500 for unexpected errors.

**File**: `server/modules/project/routes.py` (new)

**Pattern** (complete implementation):
```python
"""Project Blueprint — thin route handlers.

Each handler: validate → service call → jsonify. No filesystem logic here.
Ported from server.js:469–613.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.config import PROJECTS_DIR
from .service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_file,
)

bp = Blueprint("project", __name__)


@bp.get("/api/projects")
def list_projects_route():
    try:
        return jsonify(list_projects(PROJECTS_DIR))
    except Exception as exc:
        return jsonify({"error": "Failed to list projects"}), 500


@bp.get("/api/projects/<project_id>")
def get_project_route(project_id: str):
    try:
        project = get_project(PROJECTS_DIR, project_id)
        if project is None:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project)
    except ValueError:
        return jsonify({"error": "Project not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to get project"}), 500


@bp.post("/api/projects")
def create_project_route():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    files = data.get("files")
    if not name or not isinstance(files, list):
        return jsonify({"error": "Name and files are required"}), 400
    try:
        result = create_project(PROJECTS_DIR, name, files)
        return jsonify(result), 201
    except Exception:
        return jsonify({"error": "Failed to create project"}), 500


@bp.put("/api/projects/<project_id>/files/<filename>")
def update_file_route(project_id: str, filename: str):
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    try:
        found = update_file(PROJECTS_DIR, project_id, filename, content)
        if not found:
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"success": True})
    except ValueError:
        return jsonify({"error": "Project not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to update file"}), 500


@bp.delete("/api/projects/<project_id>")
def delete_project_route(project_id: str):
    try:
        found = delete_project(PROJECTS_DIR, project_id)
        if not found:
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"success": True})
    except ValueError:
        return jsonify({"error": "Project not found"}), 404
    except Exception:
        return jsonify({"error": "Failed to delete project"}), 500
```

**Verify**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'server')
from modules.project.routes import bp
print(f'Blueprint: {bp.name}, routes: {[r.rule for r in bp.deferred_functions]}')
print('imports OK')
"
```
Expect: `imports OK` (route inspection may show empty list before app registration — that's normal for Blueprints before `register_blueprint`).

---

### Step 5: Register module in `server/app.py`

**Action**: Add `"modules.project"` to `ENABLED_MODULES`. This is the single line that wires the Blueprint into the factory.

**File**: `server/app.py` (Task 1 output — read before editing)

**Pattern** (edit the `ENABLED_MODULES` list):
```python
# Before (Task 1 output):
ENABLED_MODULES: list[str] = []

# After:
ENABLED_MODULES: list[str] = [
    "modules.project",
]
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc
PORT=3101 python3 -c "
import sys; sys.path.insert(0, 'server')
from app import create_app
app = create_app()
client = app.test_client()
r = client.get('/api/health')
import json
data = json.loads(r.data)
assert data['status'] == 'ok'
assert 'project' in data['modules'], f\"modules={data['modules']}\"
print('Health OK:', data)
"
```
Expect: prints `Health OK:` with `project` in the modules list.

---

### Step 6: Smoke-test the 68 existing projects load correctly

**Action**: Use Flask's test client to call `GET /api/projects` and verify all existing directories load.

```bash
cd {WORKSPACE}/spec-doc
python3 -c "
import sys; sys.path.insert(0, 'server')
from app import create_app
app = create_app()
client = app.test_client()
r = client.get('/api/projects')
assert r.status_code == 200, f'status={r.status_code}'
import json
projects = json.loads(r.data)
print(f'Loaded {len(projects)} projects')
assert len(projects) >= 68, f'Expected 68+, got {len(projects)}'
# Verify every project has required fields
for p in projects:
    assert 'id' in p and 'name' in p and 'createdAt' in p and 'specs' in p, f'bad shape: {p}'
    assert isinstance(p[\"specs\"], list), f'specs must be list: {p[\"id\"]}'
print('All projects loaded OK')
"
```
Expect: `Loaded 68 projects` and `All projects loaded OK`.

**If any project fails**: the project directory likely has a malformed `project.json`. The service's `except (json.JSONDecodeError, OSError): continue` will skip it silently — update the count assertion if warranted and log which directories were skipped.

---

## 5. Tests

Framework: **pytest** (same as Task 1 — `server/tests/test_walker.py` uses pytest). Run with `python -m pytest server/tests/` from workspace root.

**File**: `server/tests/test_project.py` (new)

```python
"""Tests for Project CRUD — service functions and HTTP endpoints.

Run: python -m pytest server/tests/test_project.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure 'server/' is on sys.path (matches Task 1 test setup)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.project.service import (
    _filename_to_label,
    _make_id,
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Single project directory with project.json and two .md files."""
    d = tmp_path / "my-project-1700000000000"
    d.mkdir()
    (d / "project.json").write_text(
        json.dumps({"name": "My Project", "createdAt": "2024-01-15T10:00:00.000Z"}),
        encoding="utf-8",
    )
    (d / "epic.md").write_text("# Epic", encoding="utf-8")
    (d / "analysis.md").write_text("# Analysis", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def app(tmp_path: Path):
    """Flask test client with PROJECTS_DIR pointed at tmp_path."""
    import os
    os.environ["PROJECTS_DIR"] = str(tmp_path)
    # Re-import config to pick up new PROJECTS_DIR
    import importlib
    import core.config
    importlib.reload(core.config)
    import modules.project.routes
    importlib.reload(modules.project.routes)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client

    os.environ.pop("PROJECTS_DIR", None)


# ---------------------------------------------------------------------------
# Label derivation — port from server.js:484
# ---------------------------------------------------------------------------

def test_label_plain_filename():
    assert _filename_to_label("epic.md") == "Epic"


def test_label_hyphenated():
    assert _filename_to_label("spec-index.md") == "Spec Index"


def test_label_task_file():
    assert _filename_to_label("task-1-flask-scaffold.md") == "Task 1 Flask Scaffold"


def test_label_versioned_file():
    # .v2 suffix: "task-1-something.v2.md" → "Task 1 Something.V2"
    assert _filename_to_label("task-1-something.v2.md") == "Task 1 Something.V2"


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def test_make_id_format():
    name = "My New Project"
    project_id = _make_id(name)
    parts = project_id.rsplit("-", 1)
    assert parts[0] == "my-new-project", f"slug wrong: {parts[0]}"
    assert parts[1].isdigit(), f"timestamp must be digits: {parts[1]}"
    assert len(parts[1]) == 13, f"timestamp must be 13 digits (ms): {parts[1]}"


def test_make_id_strips_special_chars():
    project_id = _make_id("Hello! World?")
    assert project_id.startswith("hello-world-")


# ---------------------------------------------------------------------------
# Service — list_projects
# ---------------------------------------------------------------------------

def test_list_returns_all_projects(project_dir: Path):
    results = list_projects(project_dir)
    assert len(results) == 1
    assert results[0]["id"] == "my-project-1700000000000"
    assert results[0]["name"] == "My Project"
    assert results[0]["createdAt"] == "2024-01-15T10:00:00.000Z"


def test_list_specs_shape(project_dir: Path):
    results = list_projects(project_dir)
    specs = results[0]["specs"]
    assert isinstance(specs, list)
    assert len(specs) == 2
    filenames = [s["filename"] for s in specs]
    assert "epic.md" in filenames
    assert "analysis.md" in filenames
    for s in specs:
        assert "label" in s, "each spec must have a label"
        assert "content" not in s, "list must NOT include content"


def test_list_skips_dir_without_project_json(tmp_path: Path):
    # Directory with no project.json — should be skipped, not raise
    (tmp_path / "orphan-dir").mkdir()
    results = list_projects(tmp_path)
    assert results == []


def test_list_sorted_newest_first(tmp_path: Path):
    for i, ts in enumerate(["2024-01-01T00:00:00.000Z", "2024-06-01T00:00:00.000Z"]):
        d = tmp_path / f"proj-{i}"
        d.mkdir()
        (d / "project.json").write_text(
            json.dumps({"name": f"Proj {i}", "createdAt": ts}), encoding="utf-8"
        )
    results = list_projects(tmp_path)
    assert results[0]["createdAt"] == "2024-06-01T00:00:00.000Z", "newest must be first"


# ---------------------------------------------------------------------------
# Service — get_project
# ---------------------------------------------------------------------------

def test_get_returns_project_with_content(project_dir: Path):
    result = get_project(project_dir, "my-project-1700000000000")
    assert result is not None
    assert result["id"] == "my-project-1700000000000"
    specs = result["specs"]
    epic = next(s for s in specs if s["filename"] == "epic.md")
    assert epic["content"] == "# Epic"
    assert epic["label"] == "Epic"


def test_get_returns_none_for_missing_project(tmp_path: Path):
    result = get_project(tmp_path, "nonexistent-project")
    assert result is None


def test_get_rejects_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match="traversal"):
        get_project(tmp_path, "../../../etc")


# ---------------------------------------------------------------------------
# Service — create_project
# ---------------------------------------------------------------------------

def test_create_writes_project_json(tmp_path: Path):
    result = create_project(
        tmp_path,
        "New Project",
        [{"filename": "epic.md", "content": "# Epic content"}],
    )
    project_path = tmp_path / result["id"]
    assert project_path.exists()
    meta = json.loads((project_path / "project.json").read_text())
    assert meta["name"] == "New Project"
    assert meta["createdAt"] == result["createdAt"]


def test_create_writes_files(tmp_path: Path):
    result = create_project(
        tmp_path,
        "New Project",
        [
            {"filename": "epic.md", "content": "# Epic"},
            {"filename": "analysis.md", "content": "# Analysis"},
        ],
    )
    project_path = tmp_path / result["id"]
    assert (project_path / "epic.md").read_text() == "# Epic"
    assert (project_path / "analysis.md").read_text() == "# Analysis"


def test_create_returns_correct_shape(tmp_path: Path):
    result = create_project(tmp_path, "Test", [{"filename": "spec.md", "content": ""}])
    assert set(result.keys()) == {"id", "name", "createdAt"}
    assert result["name"] == "Test"
    assert result["id"].startswith("test-")
    assert result["createdAt"].endswith("Z")


# ---------------------------------------------------------------------------
# Service — update_file
# ---------------------------------------------------------------------------

def test_update_file_writes_content(project_dir: Path):
    found = update_file(
        project_dir, "my-project-1700000000000", "epic.md", "# Updated Epic"
    )
    assert found is True
    path = project_dir / "my-project-1700000000000" / "epic.md"
    assert path.read_text() == "# Updated Epic"


def test_update_file_returns_false_for_missing_project(tmp_path: Path):
    found = update_file(tmp_path, "nonexistent", "epic.md", "content")
    assert found is False


def test_update_file_can_create_new_file_in_existing_project(project_dir: Path):
    # Express behavior: PUT can create new files, not just update existing ones
    found = update_file(
        project_dir, "my-project-1700000000000", "timeline.md", "# Timeline"
    )
    assert found is True
    path = project_dir / "my-project-1700000000000" / "timeline.md"
    assert path.read_text() == "# Timeline"


# ---------------------------------------------------------------------------
# Service — delete_project
# ---------------------------------------------------------------------------

def test_delete_removes_directory(project_dir: Path):
    found = delete_project(project_dir, "my-project-1700000000000")
    assert found is True
    assert not (project_dir / "my-project-1700000000000").exists()


def test_delete_returns_false_for_missing_project(tmp_path: Path):
    found = delete_project(tmp_path, "nonexistent")
    assert found is False


# ---------------------------------------------------------------------------
# HTTP endpoints (integration via Flask test client)
# ---------------------------------------------------------------------------

def _seed_project(tmp_path: Path, project_id: str = "p-1700000000000"):
    d = tmp_path / project_id
    d.mkdir(exist_ok=True)
    (d / "project.json").write_text(
        json.dumps({"name": "HTTP Project", "createdAt": "2024-03-01T00:00:00.000Z"}),
        encoding="utf-8",
    )
    (d / "epic.md").write_text("# Epic", encoding="utf-8")
    return project_id


def test_http_list_200(app, tmp_path):
    _seed_project(tmp_path)
    r = app.get("/api/projects")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert isinstance(data, list)
    assert data[0]["id"] == "p-1700000000000"
    assert data[0]["name"] == "HTTP Project"
    assert isinstance(data[0]["specs"], list)


def test_http_get_200(app, tmp_path):
    _seed_project(tmp_path)
    r = app.get("/api/projects/p-1700000000000")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["id"] == "p-1700000000000"
    assert any(s["filename"] == "epic.md" and "content" in s for s in data["specs"])


def test_http_get_404_for_missing(app):
    r = app.get("/api/projects/does-not-exist")
    assert r.status_code == 404
    assert "error" in json.loads(r.data)


def test_http_create_201(app):
    payload = json.dumps({"name": "Brand New", "files": [{"filename": "epic.md", "content": "# Epic"}]})
    r = app.post("/api/projects", data=payload, content_type="application/json")
    assert r.status_code == 201
    data = json.loads(r.data)
    assert set(data.keys()) == {"id", "name", "createdAt"}
    assert data["name"] == "Brand New"
    assert data["id"].startswith("brand-new-")


def test_http_create_400_missing_name(app):
    payload = json.dumps({"files": [{"filename": "f.md", "content": ""}]})
    r = app.post("/api/projects", data=payload, content_type="application/json")
    assert r.status_code == 400


def test_http_create_400_missing_files(app):
    payload = json.dumps({"name": "No Files"})
    r = app.post("/api/projects", data=payload, content_type="application/json")
    assert r.status_code == 400


def test_http_update_file_200(app, tmp_path):
    _seed_project(tmp_path)
    payload = json.dumps({"content": "# Updated"})
    r = app.put(
        "/api/projects/p-1700000000000/files/epic.md",
        data=payload,
        content_type="application/json",
    )
    assert r.status_code == 200
    assert json.loads(r.data) == {"success": True}
    assert (tmp_path / "p-1700000000000" / "epic.md").read_text() == "# Updated"


def test_http_update_file_404(app):
    payload = json.dumps({"content": "x"})
    r = app.put(
        "/api/projects/nonexistent/files/epic.md",
        data=payload,
        content_type="application/json",
    )
    assert r.status_code == 404


def test_http_delete_200(app, tmp_path):
    _seed_project(tmp_path)
    r = app.delete("/api/projects/p-1700000000000")
    assert r.status_code == 200
    assert json.loads(r.data) == {"success": True}
    assert not (tmp_path / "p-1700000000000").exists()


def test_http_delete_404(app):
    r = app.delete("/api/projects/nonexistent")
    assert r.status_code == 404
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(server/config): add PROJECTS_DIR to core config` — `server/core/config.py`: adds `PROJECTS_DIR: Path` constant pointing to workspace `projects/` with `PROJECTS_DIR` env var override.

2. `feat(server/project): add modules package structure` — `server/modules/__init__.py`, `server/modules/project/__init__.py`: empty package markers.

3. `feat(server/project): implement project CRUD service` — `server/modules/project/service.py`: five filesystem helpers ported from `server.js:469–613`; includes path traversal guard.

4. `feat(server/project): implement project Blueprint` — `server/modules/project/routes.py`: five thin route handlers wiring service functions to HTTP.

5. `feat(server/app): register project module` — `server/app.py`: adds `"modules.project"` to `ENABLED_MODULES`.

6. `test(server/project): add project CRUD pytest suite` — `server/tests/test_project.py`: 30 tests covering label derivation, ID generation, all five service functions, and all five HTTP endpoints including error paths.

**Deviation logging**: if any step deviates from this guide, prefix the affected commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc

# Full pytest suite — must include all Task 1 tests still passing
python -m pytest server/tests/ -v

# Smoke-test Flask serves existing 68 projects
PORT=3101 python3 -c "
import sys; sys.path.insert(0, 'server')
from app import create_app
app = create_app()
client = app.test_client()
import json
r = client.get('/api/projects')
projects = json.loads(r.data)
assert r.status_code == 200
assert len(projects) >= 68, f'Expected 68+, got {len(projects)}'
print(f'PASS: {len(projects)} projects loaded')
"

# Side-by-side contract check: compare Flask vs Express response shapes
# (run with Express on 3100 AND Flask on 3101 simultaneously)
python3 -c "
import urllib.request, json
express = json.loads(urllib.request.urlopen('http://localhost:3100/api/projects').read())
flask   = json.loads(urllib.request.urlopen('http://localhost:3101/api/projects').read())
assert len(express) == len(flask), f'count mismatch: express={len(express)} flask={len(flask)}'
for e, f in zip(express[:3], flask[:3]):
    assert set(e.keys()) == set(f.keys()), f'key mismatch: {e.keys()} vs {f.keys()}'
    assert e['id'] == f['id'], f'id mismatch'
    assert e['name'] == f['name'], f'name mismatch'
print('Contract check PASS: shapes identical for first 3 projects')
"
```

**To start Flask on 3101**:
```bash
PORT=3101 python3 server/app.py
```

**Expected delta**: 15 → 45 passing (30 new project tests). Zero pre-existing Task 1 tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. Steps 2–5 are additive (new files); reverting any one of them does not break the others except Step 5 (removing the module registration leaves `server/app.py` clean but the Blueprint unused).
- **Per-branch**: if verification fails catastrophically — `git reset --hard <pre-task-2-sha>`. The `projects/` directory is never written to by this task (no new project directories are created during implementation), so no data is at risk.
- **Flask process cleanup**: `pkill -f "python3 server/app.py"` if needed.

---

## 9. Deviations Allowed

- **`server/core/config.py` already has `PROJECTS_DIR`** (Task 1 may have added it) → skip Step 1 edit, verify the value is correct, proceed.
- **Test framework differs from Task 1** (e.g., Task 1 used `unittest` instead of pytest) → translate test file to match; log deviation in commit body. Do not introduce a second test framework.
- **`sys.path.insert(0, 'server')` not needed** (Task 1 conftest.py may already configure paths) → remove it from test file, use whatever path pattern Task 1 established.
- **`app` fixture reload approach fails** (module caching makes env var injection unreliable) → use `monkeypatch.setattr` on `modules.project.routes.PROJECTS_DIR` and `modules.project.service` if needed; log deviation.
- **Side-effect required** (any `git push`, `npm publish`, schema migration) → STOP, mark `[REQUIRES APPROVAL]` and surface to user.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task only ports the five Express project CRUD routes. It does not touch AI endpoints, context files, the chain module, or any Angular code. Any change that requires a frontend modification is a sign the Flask route is wrong, not that the frontend needs updating.

Deferred:

- **Pagination and search** — the current Express handler returns all projects unsorted beyond createdAt. No Angular component requests pagination. Defer until a real consumer exists.
- **Project archive/restore** — not in the Express contract, not in the Angular service; out of scope by definition.
- **Schema validation beyond field presence** — Express validates only that `name` exists and `files` is an array. Adding Pydantic or jsonschema validation to Flask routes is an addition, not a port. Defer to a hardening pass if needed.
- **Walker integration** — the Task 1 walker is not called by any project CRUD route. The `POST /api/ai/text/scan` endpoint in Express calls the walker, but that's an AI endpoint deferred to Phase 2.
- **SSE streaming** — `POST /api/ai/implement` is an Express-only endpoint with a complex SSE protocol. Not part of this task.
- **Container management routes** — explicitly excluded from Phase 1 per architecture doc.
- **Port 3100 cutover** — Flask runs on 3101 during this task. Switching to 3100 (and retiring Express) is a cutover step after all Phase 1 modules are verified (Tasks 2, 3, 4 complete).

**Rule for the executor**: if a change appears helpful but is listed here, flag it as a deviation rather than absorbing it into this task's scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, component design, security boundary
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Update task status to `done` after verification passes
- [References](./references.md) – Bubls module pattern, app factory, ELA adapter