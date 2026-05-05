# Task 3: MockApiClient + Tests — Implementation Guide

## 1. Context

This task delivers `MockApiClient`, an in-memory `ApiClient` implementation that holds project state in Python dicts and drives the test suites for Tasks 3 and 4 without spinning up a live Flask process. `MockApiClient` is the unblocking artifact: once it exists, any test suite can instantiate it, call methods, and assert on the returned dataclasses in isolation. It follows the same provider/adapter separation already established in `flask/modules/chain/` — the abstract boundary is `ApiClient` (Task 2's deliverable in `flask/client/client.py`), and `MockApiClient` is the in-memory provider behind that boundary.

**Trade-offs considered:**
- **Shared parametrized runner across mock and real clients** — rejected because assertion functions belong to the downstream task test suites (2/3/4), not this epic; building a shared runner here would pre-empt decisions those tasks haven't made yet
- **Pydantic models for internal mock state** — rejected because the mock only needs to hold and return the correct shapes, not validate inputs; plain dataclasses are zero-dependency and match the chain pattern exactly
- **In-memory dicts + incrementing IDs (chosen)** — deterministic, no I/O, fast; mirrors `flask/modules/chain/providers/mock.py` which already proves this pattern in the repo

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From the spec-doc workspace root
git status                                       # flag any unrelated M/?? entries
git diff HEAD -- flask/client/                   # must be clean (directory should not exist yet)
git diff HEAD -- flask/modules/chain/            # confirm chain module is undisturbed

# Verify Task 2 prerequisite is complete
ls flask/client/client.py                        # must exist before Task 3 starts
python -c "from client.client import ApiClient, ProjectRecord, ProjectDetail, SpecFileRecord, ContextFileRecord, HealthStatus; print('OK')" 2>&1

# Record baseline test count
cd flask && python -m pytest --co -q 2>&1 | tail -5
```

**If Task 2 is not complete** (`flask/client/client.py` missing): STOP. This task cannot proceed.

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: executor records N passing before any edits.

---

## 3. Files

### To Create (new)

- `flask/client/__init__.py` — empty package marker for `flask/client/`
- `flask/client/tests/__init__.py` — empty package marker for `flask/client/tests/`
- `flask/client/tests/conftest.py` — adds `flask/` to `sys.path` so `from client.X import ...` resolves; mirrors `flask/tests/conftest.py`
- `flask/client/mock_client.py` — `MockApiClient` subclassing `ApiClient`; holds `_projects: dict[str, ProjectDetail]` and `_context: dict[str, str]`; auto-incrementing integer IDs
- `flask/client/tests/test_mock_client.py` — 26 pytest assertions covering all `ApiClient` methods

### To Modify (cite CODEBASE CONTEXT)

_None._ This task only creates new files.

### To Leave Alone

- `flask/client/client.py` — Task 2 deliverable; `MockApiClient` subclasses it but does not modify it
- `flask/client/flask_client.py` — Task 4 deliverable; do not create or modify
- `flask/modules/chain/` — chain module is the pattern reference, not a modification target
- `flask/tests/conftest.py` — existing conftest; the new `flask/client/tests/conftest.py` is a separate file, not a modification
- `flask/modules/projects/service.py` — existing projects module; `MockApiClient` replaces it in tests, does not call it

---

## 4. Implementation Steps

### Step 1: Verify Task 2 deliverable shapes

**Action**: Read `flask/client/client.py` and confirm the exact class and dataclass names before writing any code that imports them. The rest of this guide assumes the names below — if Task 2 used different names, adjust the `from client.client import ...` line and note it as a deviation.

**File**: `flask/client/client.py` (Task 2 deliverable — must exist)

**Expected shape** (executor must verify against actual file):

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SpecFileRecord:
    filename: str
    content: str

@dataclass
class ProjectRecord:
    id: str
    name: str
    createdAt: str
    files: list[str]            # filenames only — used by list endpoint

@dataclass
class ProjectDetail:
    id: str
    name: str
    createdAt: str
    files: list[SpecFileRecord] # full file objects — used by get endpoint

@dataclass
class ContextFileRecord:
    content: str
    exists: bool

@dataclass
class HealthStatus:
    status: str

class ApiClient(ABC):
    @abstractmethod
    def health(self) -> HealthStatus: ...
    @abstractmethod
    def list_projects(self) -> list[ProjectRecord]: ...
    @abstractmethod
    def get_project(self, project_id: str) -> ProjectDetail | None: ...
    @abstractmethod
    def create_project(self, name: str, files: list[dict]) -> ProjectRecord: ...
    @abstractmethod
    def update_file(self, project_id: str, filename: str, content: str) -> bool: ...
    @abstractmethod
    def delete_project(self, project_id: str) -> bool: ...
    @abstractmethod
    def get_context(self, key: str) -> ContextFileRecord: ...
    @abstractmethod
    def put_context(self, key: str, content: str) -> bool: ...
```

**Verify**: `python -c "from client.client import ApiClient, ProjectRecord, ProjectDetail, SpecFileRecord, ContextFileRecord, HealthStatus"` — expect no import error.

---

### Step 2: Create package markers

**Action**: Create two empty `__init__.py` files to make `flask/client/` and `flask/client/tests/` Python packages.

**File**: `flask/client/__init__.py` (new)

```python
```

**File**: `flask/client/tests/__init__.py` (new)

```python
```

**Verify**: `ls flask/client/__init__.py flask/client/tests/__init__.py` — both exist, both empty.

---

### Step 3: Create test conftest

**Action**: Create `flask/client/tests/conftest.py` that inserts `flask/` into `sys.path` so `from client.X import ...` resolves when pytest is invoked from any directory. Port the pattern from `flask/tests/conftest.py` (which does the same for the main test tree).

**File**: `flask/client/tests/conftest.py` (new)

```python
import os
import sys

# Add flask/ to path so `from client.X import ...` resolves.
# Mirrors flask/tests/conftest.py which does the same for the main test tree.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
```

**Verify**: `cd flask && python -m pytest client/tests/ --co -q 2>&1` — expect collection to run (no ImportError on conftest).

---

### Step 4: Implement MockApiClient

**Action**: Create `flask/client/mock_client.py`. Hold all project state in `_projects: dict[str, ProjectDetail]` and all context state in `_context: dict[str, str]`. Generate IDs as stringified auto-incrementing integers starting at `"1"`. Use full-replacement (not mutation) when updating files so the implementation is safe regardless of whether Task 2's dataclasses are `frozen=True`.

This is the in-memory provider pattern from `flask/modules/chain/providers/mock.py` — same role, same determinism, different domain.

**File**: `flask/client/mock_client.py` (new)

```python
from __future__ import annotations

from datetime import datetime, timezone

from .client import (
    ApiClient,
    ContextFileRecord,
    HealthStatus,
    ProjectDetail,
    ProjectRecord,
    SpecFileRecord,
)


class MockApiClient(ApiClient):
    """In-memory ApiClient for test suites.

    State lives in plain dicts. IDs are auto-incrementing integers ("1", "2", …).
    Zero I/O, zero network. Deterministic by default.
    """

    def __init__(self) -> None:
        self._projects: dict[str, ProjectDetail] = {}
        self._context: dict[str, str] = {}
        self._next_id: int = 1

    def _new_id(self) -> str:
        id_ = str(self._next_id)
        self._next_id += 1
        return id_

    # ── health ────────────────────────────────────────────────────────────

    def health(self) -> HealthStatus:
        return HealthStatus(status="ok")

    # ── projects ──────────────────────────────────────────────────────────

    def list_projects(self) -> list[ProjectRecord]:
        return [
            ProjectRecord(
                id=p.id,
                name=p.name,
                createdAt=p.createdAt,
                files=[f.filename for f in p.files],
            )
            for p in self._projects.values()
        ]

    def get_project(self, project_id: str) -> ProjectDetail | None:
        return self._projects.get(project_id)

    def create_project(self, name: str, files: list[dict]) -> ProjectRecord:
        project_id = self._new_id()
        created_at = datetime.now(tz=timezone.utc).isoformat()
        spec_files = [
            SpecFileRecord(filename=f["filename"], content=f["content"])
            for f in files
        ]
        self._projects[project_id] = ProjectDetail(
            id=project_id,
            name=name,
            createdAt=created_at,
            files=spec_files,
        )
        return ProjectRecord(
            id=project_id,
            name=name,
            createdAt=created_at,
            files=[f.filename for f in spec_files],
        )

    def update_file(self, project_id: str, filename: str, content: str) -> bool:
        detail = self._projects.get(project_id)
        if detail is None:
            return False
        found = False
        new_files = []
        for f in detail.files:
            if f.filename == filename:
                new_files.append(SpecFileRecord(filename=filename, content=content))
                found = True
            else:
                new_files.append(f)
        if not found:
            return False
        self._projects[project_id] = ProjectDetail(
            id=detail.id,
            name=detail.name,
            createdAt=detail.createdAt,
            files=new_files,
        )
        return True

    def delete_project(self, project_id: str) -> bool:
        if project_id not in self._projects:
            return False
        del self._projects[project_id]
        return True

    # ── context files ─────────────────────────────────────────────────────

    def get_context(self, key: str) -> ContextFileRecord:
        content = self._context.get(key, "")
        return ContextFileRecord(content=content, exists=key in self._context)

    def put_context(self, key: str, content: str) -> bool:
        self._context[key] = content
        return True
```

**Verify**:
```bash
cd flask && python -c "from client.mock_client import MockApiClient; c = MockApiClient(); print(c.health())"
# expect: HealthStatus(status='ok')
```

---

### Step 5: Write the test suite

**Action**: Create `flask/client/tests/test_mock_client.py` with complete assertions covering all `ApiClient` methods plus two structural checks. Use `pytest` fixtures, `monkeypatch`-free (the mock has no env-var dependencies), and `@pytest.mark.parametrize` for the four context file keys. Match the existing test style from `flask/modules/chain/tests/test_adapter.py` — direct `assert`, `pytest.raises` for error paths, fixtures as function parameters.

**File**: `flask/client/tests/test_mock_client.py` (new)

---

## 5. Tests

```python
from __future__ import annotations

import pathlib

import pytest

from client.client import (
    ApiClient,
    ContextFileRecord,
    HealthStatus,
    ProjectDetail,
    ProjectRecord,
    SpecFileRecord,
)
from client.mock_client import MockApiClient


@pytest.fixture
def client() -> MockApiClient:
    return MockApiClient()


# ── structural ────────────────────────────────────────────────────────────────


def test_mock_client_subclasses_api_client() -> None:
    assert issubclass(MockApiClient, ApiClient), (
        "MockApiClient must subclass ApiClient to be usable as a drop-in for FlaskApiClient"
    )


def test_no_feature_modules_import_mock_client_directly() -> None:
    """Routes and services must never import the mock — that coupling prevents
    swapping in the real client for integration tests."""
    modules_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "modules"
    violations = [
        str(py)
        for py in modules_dir.rglob("*.py")
        if "mock_client" in py.read_text(encoding="utf-8")
    ]
    assert violations == [], (
        f"Feature modules must not import mock_client directly: {violations}"
    )


# ── health ────────────────────────────────────────────────────────────────────


def test_health_returns_health_status(client: MockApiClient) -> None:
    result = client.health()
    assert isinstance(result, HealthStatus), "health() must return a HealthStatus instance"


def test_health_status_is_ok(client: MockApiClient) -> None:
    assert client.health().status == "ok"


# ── projects — list ───────────────────────────────────────────────────────────


def test_list_projects_empty_on_new_client(client: MockApiClient) -> None:
    assert client.list_projects() == []


def test_list_projects_returns_project_records(client: MockApiClient) -> None:
    client.create_project("alpha", [{"filename": "epic.md", "content": "# Epic"}])
    records = client.list_projects()
    assert len(records) == 1
    assert isinstance(records[0], ProjectRecord)


def test_list_projects_files_are_filename_strings_not_spec_file_records(
    client: MockApiClient,
) -> None:
    client.create_project("alpha", [{"filename": "epic.md", "content": "content here"}])
    record = client.list_projects()[0]
    assert record.files == ["epic.md"], (
        "list_projects must return filename strings, not SpecFileRecord objects"
    )


def test_list_projects_reflects_all_created_projects(client: MockApiClient) -> None:
    client.create_project("alpha", [])
    client.create_project("beta", [])
    assert len(client.list_projects()) == 2


# ── projects — create ─────────────────────────────────────────────────────────


def test_create_project_returns_project_record(client: MockApiClient) -> None:
    result = client.create_project("my-proj", [])
    assert isinstance(result, ProjectRecord)


def test_create_project_assigns_incrementing_ids(client: MockApiClient) -> None:
    first = client.create_project("alpha", [])
    second = client.create_project("beta", [])
    assert first.id == "1"
    assert second.id == "2"


def test_create_project_record_preserves_name(client: MockApiClient) -> None:
    result = client.create_project("my-project-name", [])
    assert result.name == "my-project-name"


def test_create_project_record_created_at_is_nonempty_string(client: MockApiClient) -> None:
    result = client.create_project("proj", [])
    assert isinstance(result.createdAt, str)
    assert len(result.createdAt) > 0


def test_create_project_record_files_lists_filenames(client: MockApiClient) -> None:
    result = client.create_project(
        "proj",
        [
            {"filename": "epic.md", "content": "..."},
            {"filename": "arch.md", "content": "..."},
        ],
    )
    assert set(result.files) == {"epic.md", "arch.md"}


# ── projects — get ────────────────────────────────────────────────────────────


def test_get_project_returns_none_for_unknown_id(client: MockApiClient) -> None:
    assert client.get_project("999") is None


def test_get_project_returns_project_detail(client: MockApiClient) -> None:
    record = client.create_project("alpha", [{"filename": "epic.md", "content": "# Epic"}])
    detail = client.get_project(record.id)
    assert isinstance(detail, ProjectDetail)


def test_get_project_detail_files_contain_spec_file_records(client: MockApiClient) -> None:
    record = client.create_project(
        "alpha", [{"filename": "epic.md", "content": "# Epic\nline2"}]
    )
    detail = client.get_project(record.id)
    assert detail is not None
    assert len(detail.files) == 1
    assert isinstance(detail.files[0], SpecFileRecord)
    assert detail.files[0].filename == "epic.md"
    assert detail.files[0].content == "# Epic\nline2"


# ── projects — update_file ────────────────────────────────────────────────────


def test_update_file_returns_false_for_unknown_project(client: MockApiClient) -> None:
    assert client.update_file("999", "epic.md", "new content") is False


def test_update_file_returns_false_for_unknown_filename(client: MockApiClient) -> None:
    record = client.create_project("alpha", [{"filename": "epic.md", "content": "old"}])
    assert client.update_file(record.id, "missing.md", "new content") is False


def test_update_file_returns_true_and_mutates_content(client: MockApiClient) -> None:
    record = client.create_project("alpha", [{"filename": "epic.md", "content": "old content"}])
    result = client.update_file(record.id, "epic.md", "updated content")
    assert result is True
    detail = client.get_project(record.id)
    assert detail is not None
    updated = next(f for f in detail.files if f.filename == "epic.md")
    assert updated.content == "updated content"


def test_update_file_does_not_affect_sibling_files(client: MockApiClient) -> None:
    record = client.create_project(
        "alpha",
        [
            {"filename": "epic.md", "content": "epic content"},
            {"filename": "arch.md", "content": "arch content"},
        ],
    )
    client.update_file(record.id, "epic.md", "updated epic")
    detail = client.get_project(record.id)
    assert detail is not None
    arch = next(f for f in detail.files if f.filename == "arch.md")
    assert arch.content == "arch content", "update_file must not touch sibling files"


# ── projects — delete ─────────────────────────────────────────────────────────


def test_delete_project_returns_false_for_unknown_id(client: MockApiClient) -> None:
    assert client.delete_project("999") is False


def test_delete_project_returns_true_for_existing_project(client: MockApiClient) -> None:
    record = client.create_project("alpha", [])
    assert client.delete_project(record.id) is True


def test_delete_project_removes_from_list(client: MockApiClient) -> None:
    record = client.create_project("alpha", [])
    client.delete_project(record.id)
    assert client.list_projects() == []


def test_delete_project_makes_get_return_none(client: MockApiClient) -> None:
    record = client.create_project("alpha", [])
    client.delete_project(record.id)
    assert client.get_project(record.id) is None


# ── context files ─────────────────────────────────────────────────────────────


def test_get_context_returns_context_file_record(client: MockApiClient) -> None:
    result = client.get_context("builder")
    assert isinstance(result, ContextFileRecord)


def test_get_context_unknown_key_returns_empty_content(client: MockApiClient) -> None:
    result = client.get_context("builder")
    assert result.content == ""


def test_get_context_unknown_key_exists_is_false(client: MockApiClient) -> None:
    result = client.get_context("builder")
    assert result.exists is False


def test_put_context_then_get_reflects_content(client: MockApiClient) -> None:
    client.put_context("builder", "# Builder\nSolo founder.")
    result = client.get_context("builder")
    assert result.content == "# Builder\nSolo founder."
    assert result.exists is True


def test_put_context_overwrites_existing_value(client: MockApiClient) -> None:
    client.put_context("principles", "first value")
    client.put_context("principles", "second value")
    assert client.get_context("principles").content == "second value"


@pytest.mark.parametrize("key", ["builder", "principles", "codebase", "references"])
def test_all_four_context_keys_round_trip(client: MockApiClient, key: str) -> None:
    client.put_context(key, f"content for {key}")
    result = client.get_context(key)
    assert result.content == f"content for {key}"
    assert result.exists is True
```

---

## 6. Commit Plan

1. `feat(client): add MockApiClient — in-memory ApiClient implementation` — `flask/client/__init__.py`, `flask/client/mock_client.py`: all project + context methods, incrementing IDs, full-replacement update pattern
2. `test(client): add test suite for MockApiClient — 26 assertions` — `flask/client/tests/__init__.py`, `flask/client/tests/conftest.py`, `flask/client/tests/test_mock_client.py`: structural checks, health, projects CRUD, context read/write

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd flask && python -m pytest client/tests/ -v
```

Expected output: 26 passed (22 plain + 4 parametrize cases for `test_all_four_context_keys_round_trip`), 0 failed, 0 errors.

```bash
# Full suite — confirm no pre-existing tests broken
cd flask && python -m pytest -q
```

**Expected delta**: N → N+26 passing. Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` to undo without touching adjacent commits.
- **Full task rollback**: `git reset --hard <pre-task-sha>` or `git checkout master && git branch -D <feature-branch>` if verification fails and the commits are on a feature branch.
- The task creates no database tables, no network resources, and no files outside `flask/client/` — blast radius is limited to those two commits.

---

## 9. Deviations Allowed

- **Task 2 used different dataclass names** (e.g., `ProjectSummary` instead of `ProjectRecord`, or no `ProjectDetail`) → read `flask/client/client.py`, use the actual names, update `from client.client import ...` in both `mock_client.py` and `test_mock_client.py`. Note in commit body under `Deviations:`.
- **Task 2 dataclasses are `frozen=True`** → the `update_file` full-replacement approach already handles this; no change needed.
- **Task 2 `ApiClient` has additional abstract methods not listed here** → implement them as stubs in `MockApiClient` that raise `NotImplementedError("not implemented in mock")`. Add a matching test asserting the stub raises. Note in commit body.
- **Test framework mismatch** (Task 2 used `unittest` instead of `pytest`) → translate silently to match; note in commit body.
- **`flask/modules/` directory doesn't exist at test time** (structural test in step 5) → the structural test should pass trivially; if the directory doesn't exist, replace with an existence check and log the deviation.
- **Side-effect required** (push, publish, schema migration) → STOP, mark `[REQUIRES APPROVAL]` and wait.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit body.

---

## 10. Out of Scope

This task proves that `MockApiClient` is internally consistent — correct shapes, correct ID generation, correct state transitions. It does not validate that `MockApiClient` and `FlaskApiClient` are behaviorally equivalent (that proof is assembled when both are run against the same assertion functions in Tasks 2/4). It also does not write the Flask routes that the real client will call.

- **`FlaskApiClient` implementation** — Task 4 deliverable; requires live Flask routes from the project and context modules; do not create `flask/client/flask_client.py` here
- **Shared parametrized test runner across mock and real clients** — assertion functions that run against both `MockApiClient` and `FlaskApiClient` belong to the downstream task test suites (2/3/4), not this task; do not build a shared runner here
- **`openapi.yaml` validation in tests** — verifying that the dataclasses in `client.py` match the spec is a Task 2 responsibility; this task only imports the dataclasses, it does not re-validate their shapes against the YAML
- **Auth, pagination, streaming endpoints** — Phase 2 routes; `MockApiClient` implements only the 13 Phase 1 methods in `ApiClient`; do not add methods beyond those

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Adapter pattern, component design, dataclass names
- [Epic](./epic.md) – Task scope and port budget
- [Timeline](./timeline.md) – Update Task 3 status to Done after verification passes