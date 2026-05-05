# Task 4: File History Endpoints — Implementation Guide

## 1. Context

Task 4 grafts three read/write endpoints onto the existing `projects_bp` Blueprint: `GET …/history` returns the commit log for a named file; `GET …/diff` returns a unified diff between two SHAs; `POST …/revert` creates a forward commit that restores a file to a past state. Each handler resolves the project through `current_app.project_repository` (shipped by Task 3) and delegates every git operation to `modules/git_store/service.py` (shipped by Task 2), keeping `pygit2` behind the adapter wall mandated by the architecture. No Angular UI ships here — the endpoints are exercised through the test suite and left available for a future frontend PR.

**Trade-offs considered:**

- **Separate `history_bp` Blueprint** — rejected; these routes are a natural extension of the project resource (`/api/projects/{id}/files/{filename}/…`) and share its project-resolution logic; a second blueprint adds a registration entry and import without any isolation benefit.
- **SHA parameters as path segments** (`/diff/{from_sha}/{to_sha}`) — rejected; unified diffs are reads, not sub-resources; query parameters keep the URL pronounceable and avoid double-encoding of 40-char hex strings in path position.
- **Extend existing projects blueprint routes** — preferred; ~30 LOC, no new modules, immediate benefit of Task 3's `project_repository` and Task 2's `git_store` without inventing new infrastructure.

---

## 2. Pre-flight

```bash
# From {WORKSPACE}/api/
git status                                              # Confirm clean working tree on target files
git diff HEAD -- openapi.yaml modules/projects/routes.py dtos/models.py
python -m pytest --tb=short -q 2>&1 | tail -5          # Record baseline; expect 624 passed
```

**Hard gate — confirm prior tasks are merged:**

```bash
python -c "from modules.git_store import service"           # Task 2 — must succeed
python -c "from modules.projects.models import Project"     # Task 3 — must succeed
python -c "from create_app import create_app; a=create_app(); print(hasattr(a,'project_repository'))"
# Must print True (Task 3 wires project_repository onto the app)
```

**If any check fails**: stop; merge Task 2 and Task 3 branches first. Do not proceed on a red gate.

**Baseline recorded**: 624 / 624 passing.

---

## 3. Files

### To Create (new)

- `api/tests/test_file_history_routes.py` — pytest test module; 13 tests covering history, diff, revert happy paths + 404/400 error paths + git_store adapter-boundary structural test

### To Modify (cite CODEBASE CONTEXT)

- `api/openapi.yaml` — add 5 schemas (`CommitEntry`, `FileHistoryResponse`, `FileDiffResponse`, `FileRevertRequest`, `FileRevertResponse`) and 3 path entries; source of truth per ELA Pattern #3
- `api/dtos/models.py` — regenerated via `make generate-dtos`; **never hand-edited**
- `api/modules/projects/routes.py` — add `current_app` to Flask imports; add `from modules.git_store import service as git_store`; add DTO imports; append 3 handler functions

### To Leave Alone

- `api/modules/projects/service.py` — filesystem CRUD; not involved in git history operations
- `api/modules/projects/errors.py` — `ProjectNotFoundError` not raised by `project_repository.get_by_slug()` (returns `None`); no change needed
- `api/modules/git_store/service.py` — owned by Task 2; executor must not touch it
- `api/create_app.py` — `project_repository` registration owned by Task 3; no change needed
- `api/tests/conftest.py` — existing `app`/`client`/`spec_doc_dir` fixtures are reused as-is; the new test module supplies its own `project_repository` stub fixture to avoid widening conftest scope

---

## 4. Implementation Steps

### Step 1: Declare schemas in `openapi.yaml`

**Action**: Append 5 new schema objects to the `components/schemas` section of `openapi.yaml`.

**File**: `api/openapi.yaml` (CODEBASE CONTEXT — `openapi.yaml` is the contract; generate-dtos reads only this file)

**Pattern**:

```yaml
    CommitEntry:
      type: object
      required: [sha, message, author, timestamp]
      properties:
        sha:
          type: string
        message:
          type: string
        author:
          type: string
        timestamp:
          type: string
          format: date-time

    FileHistoryResponse:
      type: object
      required: [history]
      properties:
        history:
          type: array
          items:
            $ref: '#/components/schemas/CommitEntry'

    FileDiffResponse:
      type: object
      required: [diff]
      properties:
        diff:
          type: string

    FileRevertRequest:
      type: object
      required: [to_sha]
      properties:
        to_sha:
          type: string

    FileRevertResponse:
      type: object
      required: [sha, message]
      properties:
        sha:
          type: string
        message:
          type: string
```

Insert these in alphabetical order within `components/schemas` (after `FileUpdateRequest`, before `GenerateTaskStartResponse`).

**Verify**: `grep -c 'CommitEntry\|FileHistoryResponse\|FileDiffResponse\|FileRevertRequest\|FileRevertResponse' api/openapi.yaml` — expect `10` (5 definition keys + 5 `$ref` usages to come in Step 2).

---

### Step 2: Declare path entries in `openapi.yaml`

**Action**: Append 3 path entries to the `paths` section of `openapi.yaml`, immediately after the `PUT /api/projects/{id}/files/{filename}` entry.

**File**: `api/openapi.yaml`

**Pattern**:

```yaml
  /api/projects/{project_id}/files/{filename}/history:
    get:
      operationId: getFileHistory
      summary: Commit history for a project file
      parameters:
        - name: project_id
          in: path
          required: true
          schema: {type: string}
        - name: filename
          in: path
          required: true
          schema: {type: string}
        - name: limit
          in: query
          required: false
          schema: {type: integer, default: 20}
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: {$ref: '#/components/schemas/FileHistoryResponse'}
        '404':
          description: Project not found
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ErrorResponse'}

  /api/projects/{project_id}/files/{filename}/diff:
    get:
      operationId: getFileDiff
      summary: Unified diff between two SHAs for a project file
      parameters:
        - name: project_id
          in: path
          required: true
          schema: {type: string}
        - name: filename
          in: path
          required: true
          schema: {type: string}
        - name: from_sha
          in: query
          required: true
          schema: {type: string}
        - name: to_sha
          in: query
          required: true
          schema: {type: string}
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: {$ref: '#/components/schemas/FileDiffResponse'}
        '400':
          description: Missing query parameters
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ErrorResponse'}
        '404':
          description: Project not found
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ErrorResponse'}

  /api/projects/{project_id}/files/{filename}/revert:
    post:
      operationId: revertFile
      summary: Revert a project file to a specific commit SHA (forward commit)
      parameters:
        - name: project_id
          in: path
          required: true
          schema: {type: string}
        - name: filename
          in: path
          required: true
          schema: {type: string}
      requestBody:
        required: true
        content:
          application/json:
            schema: {$ref: '#/components/schemas/FileRevertRequest'}
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: {$ref: '#/components/schemas/FileRevertResponse'}
        '400':
          description: Validation error
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ErrorResponse'}
        '404':
          description: Project not found
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ErrorResponse'}
```

**Verify**: `python -c "import yaml; d=yaml.safe_load(open('openapi.yaml')); print(list(d['paths'].keys())[-3:])"` (from `api/`) — expect the three new paths in the output.

> ⚠️ The structural test `everyOpenapiPath_hasRouteHandler` will **fail** until Step 4 completes. Do not run `make test` between Steps 2 and 4. Run `make check-dtos` only.

---

### Step 3: Regenerate DTOs

**Action**: Run codegen to update `dtos/models.py` from the amended contract.

**File**: `api/dtos/models.py` (generated; never hand-edited — ELA Pattern #3)

```bash
cd {WORKSPACE}/api && make generate-dtos
```

**Verify**:

```bash
make check-dtos        # must exit 0
grep "CommitEntry\|FileHistoryResponse\|FileDiffResponse\|FileRevertRequest\|FileRevertResponse" dtos/models.py
# expect 5 class definitions
```

**Commit after this step** (see Commit Plan — commit 1).

---

### Step 4: Add route handlers to the projects blueprint

**Action**: Add `current_app` to the Flask import line, add the `git_store` module import, add the five new DTO imports, then append three handler functions at the bottom of `routes.py`.

**File**: `api/modules/projects/routes.py` (CODEBASE CONTEXT)

**Pattern — import additions** (modify the existing Flask import line and add two new import lines):

```python
# existing line — add current_app
from flask import Blueprint, current_app, jsonify, request

# new lines — add below existing service import
from modules.git_store import service as git_store  # adapter boundary: only import point for pygit2 ops
from dtos.models import (
    CommitEntry,
    FileDiffResponse,
    FileHistoryResponse,
    FileRevertRequest,
    FileRevertResponse,
)
```

**Pattern — three handler functions** (append after the last existing handler):

```python
@projects_bp.get("/<project_id>/files/<filename>/history")
def get_file_history(project_id: str, filename: str):
    project = current_app.project_repository.get_by_slug(project_id)
    if project is None:
        return jsonify({"error": "Project not found"}), 404
    limit = request.args.get("limit", 20, type=int)
    history = git_store.get_history(project.id, filename, limit)
    return jsonify(FileHistoryResponse(history=[CommitEntry(**e) for e in history]).dict())


@projects_bp.get("/<project_id>/files/<filename>/diff")
def get_file_diff(project_id: str, filename: str):
    project = current_app.project_repository.get_by_slug(project_id)
    if project is None:
        return jsonify({"error": "Project not found"}), 404
    from_sha = request.args.get("from_sha")
    to_sha = request.args.get("to_sha")
    if not from_sha or not to_sha:
        return jsonify({"error": "from_sha and to_sha query parameters are required"}), 400
    diff = git_store.get_diff(project.id, filename, from_sha, to_sha)
    return jsonify(FileDiffResponse(diff=diff).dict())


@projects_bp.post("/<project_id>/files/<filename>/revert")
def revert_file(project_id: str, filename: str):
    project = current_app.project_repository.get_by_slug(project_id)
    if project is None:
        return jsonify({"error": "Project not found"}), 404
    body = request.get_json(silent=True) or {}
    try:
        req = FileRevertRequest(**body)
    except Exception:
        return jsonify({"error": "to_sha is required"}), 400
    result = git_store.revert_file(project.id, filename, req.to_sha)
    return jsonify(FileRevertResponse(**result).dict())
```

**Verify**:

```bash
cd {WORKSPACE}/api
python -c "
from create_app import create_app
app = create_app()
rules = [str(r) for r in app.url_map.iter_rules()]
assert any('history' in r for r in rules), 'history route missing'
assert any('diff' in r for r in rules), 'diff route missing'
assert any('revert' in r for r in rules), 'revert route missing'
print('All three routes registered')
"
```

**Commit after this step** (see Commit Plan — commit 2).

---

### Step 5: Write tests

**Action**: Create the test module. It provides its own `project_repo_stub` and `git_patch` fixtures so it does not widen `conftest.py`.

**File**: `api/tests/test_file_history_routes.py` (new)

See §5 Tests below for the complete file body.

**Verify**:

```bash
cd {WORKSPACE}/api
python -m pytest tests/test_file_history_routes.py -v
# expect 13 passed, 0 failed
```

**Commit after this step** (see Commit Plan — commit 3).

---

## 5. Tests

**File**: `api/tests/test_file_history_routes.py`

```python
"""
Tests for file history/diff/revert route handlers (Task 4).
Framework: pytest + Flask test client (matches existing suite in tests/).
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal stub that mimics modules/projects/models.py::Project (Task 3)
# ---------------------------------------------------------------------------
class _StubProject:
    id = "proj-abc123"
    slug = "my-project"


_HISTORY_ROW = {
    "sha": "deadbeef1234",
    "message": "Update brain-dump.md",
    "author": "Sam",
    "timestamp": "2026-04-26T10:00:00+00:00",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def project_repo_stub(app):
    """Override app.project_repository with a stub that returns _StubProject."""
    stub = MagicMock()
    stub.get_by_slug.return_value = _StubProject()
    app.project_repository = stub
    return stub


@pytest.fixture()
def git_patch():
    """Patch modules.projects.routes.git_store for all history route tests."""
    with patch("modules.projects.routes.git_store") as mock_gs:
        yield mock_gs


# ---------------------------------------------------------------------------
# GET …/history
# ---------------------------------------------------------------------------
class TestGetFileHistory:
    def test_returns_history_list(self, client, project_repo_stub, git_patch):
        git_patch.get_history.return_value = [_HISTORY_ROW]
        r = client.get("/api/projects/my-project/files/brain-dump.md/history")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "history" in body, "response must have 'history' key"
        assert len(body["history"]) == 1, "expected exactly one commit entry"
        entry = body["history"][0]
        assert entry["sha"] == "deadbeef1234"
        assert entry["message"] == "Update brain-dump.md"
        assert entry["author"] == "Sam"
        assert "timestamp" in entry

    def test_default_limit_is_20(self, client, project_repo_stub, git_patch):
        git_patch.get_history.return_value = []
        client.get("/api/projects/my-project/files/brain-dump.md/history")
        git_patch.get_history.assert_called_once_with("proj-abc123", "brain-dump.md", 20)

    def test_custom_limit_forwarded(self, client, project_repo_stub, git_patch):
        git_patch.get_history.return_value = []
        client.get("/api/projects/my-project/files/brain-dump.md/history?limit=5")
        git_patch.get_history.assert_called_once_with("proj-abc123", "brain-dump.md", 5)

    def test_404_unknown_project(self, client, project_repo_stub, git_patch):
        project_repo_stub.get_by_slug.return_value = None
        r = client.get("/api/projects/no-such/files/brain-dump.md/history")
        assert r.status_code == 404
        assert "error" in json.loads(r.data)


# ---------------------------------------------------------------------------
# GET …/diff
# ---------------------------------------------------------------------------
class TestGetFileDiff:
    def test_returns_diff_string(self, client, project_repo_stub, git_patch):
        git_patch.get_diff.return_value = (
            "--- a/brain-dump.md\n+++ b/brain-dump.md\n@@ -1 +1 @@\n-old\n+new"
        )
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/diff"
            "?from_sha=aaa111&to_sha=bbb222"
        )
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "diff" in body, "response must have 'diff' key"
        assert "@@" in body["diff"], "diff string must contain hunk header"

    def test_forwards_shas_to_git_store(self, client, project_repo_stub, git_patch):
        git_patch.get_diff.return_value = ""
        client.get(
            "/api/projects/my-project/files/brain-dump.md/diff"
            "?from_sha=aaa111&to_sha=bbb222"
        )
        git_patch.get_diff.assert_called_once_with(
            "proj-abc123", "brain-dump.md", "aaa111", "bbb222"
        )

    def test_400_missing_from_sha(self, client, project_repo_stub, git_patch):
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/diff?to_sha=bbb222"
        )
        assert r.status_code == 400
        assert "error" in json.loads(r.data)

    def test_400_missing_to_sha(self, client, project_repo_stub, git_patch):
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/diff?from_sha=aaa111"
        )
        assert r.status_code == 400
        assert "error" in json.loads(r.data)

    def test_404_unknown_project(self, client, project_repo_stub, git_patch):
        project_repo_stub.get_by_slug.return_value = None
        r = client.get(
            "/api/projects/no-such/files/brain-dump.md/diff"
            "?from_sha=aaa111&to_sha=bbb222"
        )
        assert r.status_code == 404
        assert "error" in json.loads(r.data)


# ---------------------------------------------------------------------------
# POST …/revert
# ---------------------------------------------------------------------------
class TestRevertFile:
    def test_returns_new_sha_and_message(self, client, project_repo_stub, git_patch):
        git_patch.revert_file.return_value = {
            "sha": "newsha9999",
            "message": "Revert brain-dump.md to deadbeef1234",
        }
        r = client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef1234"},
        )
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["sha"] == "newsha9999"
        assert "message" in body

    def test_forwards_args_to_git_store(self, client, project_repo_stub, git_patch):
        git_patch.revert_file.return_value = {"sha": "x", "message": "y"}
        client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef1234"},
        )
        git_patch.revert_file.assert_called_once_with(
            "proj-abc123", "brain-dump.md", "deadbeef1234"
        )

    def test_404_unknown_project(self, client, project_repo_stub, git_patch):
        project_repo_stub.get_by_slug.return_value = None
        r = client.post(
            "/api/projects/no-such/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef1234"},
        )
        assert r.status_code == 404
        assert "error" in json.loads(r.data)

    def test_400_missing_to_sha(self, client, project_repo_stub, git_patch):
        r = client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={},
        )
        assert r.status_code == 400
        assert "error" in json.loads(r.data)


# ---------------------------------------------------------------------------
# Structural: adapter boundary
# ---------------------------------------------------------------------------
class TestGitStoreAdapterBoundary:
    def test_no_direct_pygit2_import_outside_git_store(self):
        """
        No .py file outside modules/git_store/ may import pygit2 directly.
        This enforces ELA Pattern #1 (Adapter Boundary) for the git layer.
        """
        api_root = Path(__file__).parent.parent  # {WORKSPACE}/api/
        violations = []
        for py_file in api_root.rglob("*.py"):
            if "git_store" in py_file.parts:
                continue  # git_store itself is allowed to use pygit2
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if "import pygit2" in text or "from pygit2" in text:
                violations.append(str(py_file.relative_to(api_root)))
        assert violations == [], (
            "Direct pygit2 imports found outside modules/git_store/ — "
            "all pygit2 calls must go through modules/git_store/service.py. "
            "Offending files: " + ", ".join(violations)
        )
```

---

## 6. Commit Plan

**Executor instruction**: run each commit command immediately after the corresponding step completes. Do not batch commits at the end.

1. `feat(openapi): declare file history/diff/revert schemas and paths` — **after Steps 1–3** — files: `openapi.yaml`, `dtos/models.py`

   ```bash
   cd {WORKSPACE}/api
   git add openapi.yaml dtos/models.py
   git commit -m "feat(openapi): declare file history/diff/revert schemas and paths"
   ```

2. `feat(projects): add get_file_history, get_file_diff, revert_file route handlers` — **after Step 4** — files: `modules/projects/routes.py`

   ```bash
   cd {WORKSPACE}/api
   git add modules/projects/routes.py
   git commit -m "feat(projects): add get_file_history, get_file_diff, revert_file route handlers"
   ```

3. `test(projects): file history/diff/revert endpoints + git_store boundary check` — **after Step 5 passes** — files: `tests/test_file_history_routes.py`

   ```bash
   cd {WORKSPACE}/api
   git add tests/test_file_history_routes.py
   git commit -m "test(projects): file history/diff/revert endpoints + git_store boundary check"
   ```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation, e.g.:

```
feat(projects): add get_file_history, get_file_diff, revert_file route handlers

Deviations: project_repository.get_by_slug raises ProjectNotFoundError instead of returning None — caught and mapped to 404.
```

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → 637 passing (13 new tests). Zero pre-existing tests broken.

Cross-check the structural `everyOpenapiPath_hasRouteHandler` test passes — it verifies all three new openapi paths are backed by Flask route rules.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # creates a counter-commit; does not rewrite history
  ```
- **Per-branch**: if verification fails and you need a clean slate:
  ```bash
  git reset --hard <pre-task-sha>   # destructive — confirm SHA first
  # or delete the feature branch and re-open from master
  ```
  The pre-task SHA is the HEAD recorded during Pre-flight.

---

## 9. Deviations Allowed

- **`project_repository.get_by_slug()` raises instead of returning `None`** → catch `ProjectNotFoundError` (from `modules/projects/errors.py`) and map to 404; log deviation in commit body.
- **`git_store.revert_file()` returns a SHA string, not a dict** → wrap it: `{"sha": result, "message": f"Revert {filename} to {req.to_sha}"}` before constructing `FileRevertResponse`; log deviation.
- **`dtos/models.py` DTO name collision** with a Task-3-generated class → rename with `FileHistory` prefix (e.g., `FileHistoryCommitEntry`); update the handler and test imports in the same commit; log deviation.
- **Step N unlocks simplification for Step N+1** → take it; log in commit body.
- **Side-effect required** (push, schema migration, publish) → STOP; mark `[REQUIRES APPROVAL]` and surface to the operator.

---

## 10. Out of Scope

This task delivers the three backend endpoints and their tests. It does not build any UI, does not extend the migration script, and does not address any authentication concern. An eager executor may notice the handlers lack `g.current_user` guards or file-ownership assertions — these are intentionally absent because the auth middleware epic has not shipped and adding partial guards now would either be a no-op or silently break when auth lands.

- **Angular file-history panel** — deferred; a separate frontend epic owns the editor sidebar; the endpoints are ready when that work starts.
- **`g.current_user` ownership check on `project_repository.get_by_slug()`** — deferred; auth middleware (Neon Auth JWT) is a blocking prerequisite; add the guard in the auth epic's task that wires up `g.current_user`.
- **`delete_file` HTTP route** — explicitly excluded by the architecture; the operation exists in `git_store` for retry-recovery use only; no route until a UI consumer exists.
- **Pagination cursor on the history endpoint** — the `limit` parameter satisfies current needs; cursor-based pagination requires a second concrete consumer use case before it enters scope (ELA Pattern #5).
- **`0001_initial_schema.py` migration** — co-owned with the monetisation epic; Task 4 has no migration dependency; do not touch `migrations/`.

**Rule for the executor**: if a change appears helpful but appears in this list, stop and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)