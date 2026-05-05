# Task 3: Write and run `capture.py`

## 1. Context

`capture.py` is a one-time data collection script that calls every read endpoint on the live Express server (port 3100) and writes simplified JSON to `flask/tests/fixtures/`. These committed fixture files become the stable seed data for `test_contract.py` (Task 4): `project.json` supplies the project ID that CRUD tests use to call Flask without creating and tearing down their own state. Because Express and Flask share the same `projects/` directory, any project captured by this script is immediately addressable by Flask on port 3101. Once the fixtures are committed, Express can be decommissioned without affecting the test suite.

**Trade-offs considered:**
- **Capture all 14 routes (including PUT/POST/DELETE)** — rejected because write operations produce side effects; capturing happy-path GET responses is sufficient for shape validation and CRUD seeding
- **Inline Express response verbatim as fixture** — rejected because `createdAt` timestamps make fixtures stale on every write, coupling test_contract.py to Express's exact output
- **Capture read-only endpoints, strip volatile fields** — preferred because it produces minimal, stable seed data; the DTO layer in Task 4 handles shape enforcement, not the fixture bytes

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From workspace root: spec-doc/
git status
git diff HEAD -- flask/requirements.txt flask/tests/

# Baseline test count
cd flask && python -m pytest tests/ -q
```

**Expected baseline**: 58/58 passing (test_health.py: 10, test_project.py: 29, test_context_files.py: 19).

**If working tree is dirty on target files**: stash or commit unrelated changes first. The `M references.md` in git status is unrelated — do not touch it.

---

## 3. Files

### To Create (new)
- `flask/tests/capture.py` — standalone fixture generator; calls Express GET endpoints on port 3100; not imported by pytest
- `flask/tests/fixtures/` — directory for committed fixture JSON files (output of running capture.py)
- `flask/tests/fixtures/health.json` — `{"status": "ok"}` from `GET /health`
- `flask/tests/fixtures/builder.json` — `{"content": string, "exists": bool}` from `GET /api/builder`
- `flask/tests/fixtures/principles.json` — same shape from `GET /api/principles`
- `flask/tests/fixtures/codebase.json` — same shape from `GET /api/codebase`
- `flask/tests/fixtures/references.json` — same shape from `GET /api/references`
- `flask/tests/fixtures/projects.json` — stripped list `[{id, name, specs[]}]` from `GET /api/projects`
- `flask/tests/fixtures/project.json` — stripped single detail `{id, name, specs[{filename,label,content}]}` from `GET /api/projects/:id`
- `flask/tests/test_fixtures.py` — pytest suite validating committed fixtures have expected shapes

### To Modify (cite CODEBASE CONTEXT)
- `flask/requirements.txt` (currently 4 lines: flask, flask-cors, pytest, anthropic) — add `requests>=2.31.0`; needed by capture.py at runtime and by test_contract.py in Task 4

### To Leave Alone
- `flask/tests/conftest.py` — no new fixtures needed; test_fixtures.py loads JSON directly via `pathlib`
- `flask/tests/test_health.py`, `test_project.py`, `test_context_files.py` — pre-existing; must not drift
- `flask/modules/` — no module changes in this task
- `server.js` — Express source; read-only reference for endpoint URLs
- `.gitignore` — does not ignore `flask/tests/fixtures/`; no change needed

---

## 4. Implementation Steps

### Step 1: Add `requests` to requirements.txt

**Action**: Append one line to `flask/requirements.txt`

**File**: `flask/requirements.txt`

**Pattern**:
```
flask>=3.0.0
flask-cors>=4.0.0
pytest>=8.0.0
anthropic
requests>=2.31.0
```

**Verify**: `pip show requests` — confirms it's installed; if not, run `pip install requests>=2.31.0`

---

### Step 2: Write `flask/tests/capture.py`

**Action**: Create the capture script. Targets 7 GET endpoints, writes 7 fixture files. `strip_project` removes `createdAt` (volatile). If no projects exist in Express, creates a seed project and leaves it (it will exist in the shared `projects/` directory that Flask also reads).

**File**: `flask/tests/capture.py` (new)

**Pattern** — full implementation, ~55 lines:
```python
#!/usr/bin/env python3
"""
capture.py — One-time fixture generator for flask/tests/fixtures/.
Run while Express is live on port 3100. NOT part of CI or the test suite.
"""

import json
import sys
from pathlib import Path

import requests

BASE = "http://localhost:3100"
OUT = Path(__file__).parent / "fixtures"


def get(path: str):
    r = requests.get(f"{BASE}{path}", timeout=5)
    r.raise_for_status()
    return r.json()


def save(name: str, data) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"  wrote {name}.json")


def strip_project(p: dict, *, content: bool = True) -> dict:
    """Remove volatile fields (createdAt); keep id, name, specs."""
    specs = p.get("specs", [])
    if not content:
        specs = [{"filename": s["filename"], "label": s["label"]} for s in specs]
    return {"id": p["id"], "name": p["name"], "specs": specs}


def main() -> None:
    print(f"Connecting to Express on {BASE} ...")

    save("health", get("/health"))

    for key in ("builder", "principles", "codebase", "references"):
        save(key, get(f"/api/{key}"))

    projects = get("/api/projects")
    if not projects:
        print("  no projects found — creating fixture seed project")
        r = requests.post(f"{BASE}/api/projects", json={
            "name": "Fixture Seed",
            "files": [{"filename": "epic.md", "content": "# Epic\nSeed project for contract tests."}],
        }, timeout=5)
        r.raise_for_status()
        project_id = r.json()["id"]
        projects = get("/api/projects")
    else:
        project_id = projects[0]["id"]

    save("projects", [strip_project(p, content=False) for p in projects])
    save("project", strip_project(get(f"/api/projects/{project_id}")))

    print("\nDone. Commit flask/tests/fixtures/ to the repository.")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot reach Express on port 3100. Start it with: npm run api", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"ERROR: HTTP {exc.response.status_code} from Express — {exc}", file=sys.stderr)
        sys.exit(1)
```

**Verify**: `python -m py_compile flask/tests/capture.py` — no output means no syntax errors

---

### Step 3: Run `capture.py` while Express is live

**Action**: Start Express (if not already running), execute the script, inspect output.

**File**: n/a (runtime step)

**Pattern**:
```bash
# Terminal 1 — start Express
npm run api   # starts server.js on port 3100

# Terminal 2 — run capture (from workspace root)
python flask/tests/capture.py
```

Expected output:
```
Connecting to Express on http://localhost:3100 ...
  wrote health.json
  wrote builder.json
  wrote principles.json
  wrote codebase.json
  wrote references.json
  wrote projects.json
  wrote project.json

Done. Commit flask/tests/fixtures/ to the repository.
```

**Verify**: `ls flask/tests/fixtures/` — expect exactly 7 `.json` files

---

### Step 4: Inspect fixtures for correctness

**Action**: Verify fixture content before committing. Check that `project.json` has a non-empty `id` (critical for Task 4's CRUD seeding), and that context files have `content`/`exists` keys.

**File**: n/a (inspection step)

**Pattern**:
```bash
python -c "
import json, pathlib
d = pathlib.Path('flask/tests/fixtures')
for f in sorted(d.glob('*.json')):
    data = json.loads(f.read_text())
    print(f.name, list(data.keys()) if isinstance(data, dict) else f'list[{len(data)}]')
"
```

Expected output (exact keys may vary for context files based on whether files exist):
```
builder.json ['content', 'exists']
codebase.json ['content', 'exists']
health.json ['status']
principles.json ['content', 'exists']
project.json ['id', 'name', 'specs']
projects.json list[N]
references.json ['content', 'exists']
```

**Verify**: `python -c "import json; p = json.load(open('flask/tests/fixtures/project.json')); assert p['id'], 'id is empty'"` — no output means `id` is non-empty

---

### Step 5: Write `flask/tests/test_fixtures.py`

**Action**: Create a pytest file that validates committed fixtures have expected shapes. These tests run in CI to catch accidental fixture deletion or corruption before Task 4's tests depend on them.

**File**: `flask/tests/test_fixtures.py` (new)

**Pattern** — full implementation, see Tests section below

**Verify**: `cd flask && python -m pytest tests/test_fixtures.py -v` — expect 8 passing

---

## 5. Tests

Framework: `pytest` — matches `flask/tests/conftest.py` pattern. No Flask `client` fixture needed; tests load JSON directly via `pathlib`.

```python
# flask/tests/test_fixtures.py
"""Validate committed fixture files exist and have expected shapes."""
import json
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    path = FIXTURES / f"{name}.json"
    assert path.exists(), f"Fixture missing: {name}.json — run flask/tests/capture.py first"
    return json.loads(path.read_text())


def test_health_fixture():
    data = load("health")
    assert data.get("status") == "ok", "health.json must have status: ok"


def test_project_fixture_has_nonempty_id():
    data = load("project")
    assert isinstance(data.get("id"), str) and len(data["id"]) > 0, (
        "project.json must have a non-empty id string for CRUD seeding"
    )


def test_project_fixture_has_name():
    data = load("project")
    assert isinstance(data.get("name"), str) and len(data["name"]) > 0


def test_project_fixture_has_specs_list():
    data = load("project")
    assert isinstance(data.get("specs"), list), "project.json specs must be a list"


def test_projects_fixture_is_nonempty_list():
    data = load("projects")
    assert isinstance(data, list) and len(data) > 0, (
        "projects.json must be a non-empty list"
    )


def test_projects_items_have_required_fields():
    data = load("projects")
    for item in data:
        assert "id" in item, f"projects.json item missing id: {item}"
        assert "name" in item, f"projects.json item missing name: {item}"
        assert "specs" in item, f"projects.json item missing specs: {item}"


@pytest.mark.parametrize("key", ["builder", "principles", "codebase", "references"])
def test_context_fixture_shape(key):
    data = load(key)
    assert "content" in data, f"{key}.json missing 'content' key"
    assert "exists" in data, f"{key}.json missing 'exists' key"
    assert isinstance(data["content"], str), f"{key}.json content must be a string"
    assert isinstance(data["exists"], bool), f"{key}.json exists must be a boolean"
```

**Test count**: 7 test functions; `test_context_fixture_shape` is parametrized × 4 = 10 total test cases.

---

## 6. Commit Plan

1. `chore(flask): add requests to requirements.txt` — `flask/requirements.txt`: adds `requests>=2.31.0` for capture script and Task 4 test suite
2. `feat(tests): add capture.py — one-time Express fixture generator` — `flask/tests/capture.py`: the script itself
3. `chore(tests): commit captured Express fixtures` — `flask/tests/fixtures/*.json`: 7 committed JSON files; run capture.py before this commit
4. `test(fixtures): add fixture shape validation suite` — `flask/tests/test_fixtures.py`: 10 pytest assertions guarding fixture integrity in CI

**Deviation logging**: if any step deviates (e.g., fixture directory path changed, context file content empty), prefix the relevant commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd flask && python -m pytest tests/ -v
```

**Expected delta**: 58 → 68 passing (10 new from `test_fixtures.py`). Zero pre-existing tests broken.

Spot-check the fixture ID is usable by Flask:

```bash
PROJECT_ID=$(python -c "import json; print(json.load(open('flask/tests/fixtures/project.json'))['id'])")
curl -s http://localhost:3101/api/projects/$PROJECT_ID | python -m json.tool
```

Expect a well-formed JSON response with `id`, `name`, `specs` — confirms the captured project exists in Flask's filesystem too.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` in reverse order.
- **Fixture re-generation**: if fixtures need to be regenerated (e.g., the seed project was deleted), re-run `python flask/tests/capture.py` while Express is live, then `git add flask/tests/fixtures/ && git commit`.
- **Per-branch catastrophic failure**: `git reset --hard <pre-task-sha>` — no production system is affected; all changes are local files and pytest additions.

---

## 9. Deviations Allowed

- **Express not running on port 3100**: start it with `npm run api` before running capture.py; the script provides a clear error message if unreachable.
- **`GET /api/builder` or `/api/codebase` returns `exists: false, content: ""`**: expected — both files are gitignored (`builder.md`, `codebase.md`); the fixture captures the empty state, which is valid for shape testing.
- **Express already has many projects**: the script picks `projects[0]` (newest-first sort); if that project has no `.md` files, `project.json` will have an empty `specs` array — acceptable, but note the deviation in the commit body.
- **`requests` already installed** (not in requirements.txt yet): skip Step 1 installation, but still add it to `requirements.txt` so CI environments get it.
- **Step N unlocks an obvious simplification for Step N+1**: take it and log in commit body.
- **Side-effect required** (push, publish, remote DB change): STOP, mark `[REQUIRES APPROVAL]`, and ask.

---

## 10. Out of Scope

This task produces fixture files and the script that generates them. It does not build the DTO layer (`flask/dto.py`) or the integration test suite (`flask/tests/test_contract.py`) — those are Task 1 and Task 4 respectively. The capture script's job ends when 7 JSON files are committed; verifying that Flask's responses match those shapes is Task 4's responsibility.

- **`openapi.yaml` and `flask/dto.py`** — Task 1; capture.py has no dependency on DTOs and must not wait for them
- **`flask/tests/test_contract.py`** — Task 4; uses `fixtures/project.json` as seed data but is authored separately
- **Error-response fixtures** (4xx/5xx shapes from Express) — explicitly excluded per the epic; happy-path only
- **Fixture re-capture in CI** — deferred until Express decommission is scoped; no trigger condition exists today
- **Authentication flow capture** — no auth layer in Express or Flask Phase 1; out of scope entirely
- **Parametrized or edge-case fixtures** — belongs in a dedicated error-contract suite, scoped separately from this capability

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale (Capture Phase, fixture design decisions)
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Update status to `done` after verification passes