Now I have everything I need. Let me write the guide.

# Task 2: Abstract Client + Dataclasses — Implementation Guide

## 1. Context

Task 2 defines the shared interface contract that Tasks 3 and 4 both implement: an `ApiClient` ABC with typed return dataclasses covering all 14 Phase 1 routes (health, 5 project CRUD, 4 context reads, 4 context writes). This is the adapter boundary — once it exists, `MockApiClient` (Task 3) and `FlaskApiClient` (Task 4) can be written in parallel, and any test typed against `ApiClient` runs against either implementation without modification. Nothing else in `flask/` changes; this task is additive only.

**Trade-offs considered:**
- **Pydantic models instead of dataclasses** — rejected because Pydantic is already in the context module as a validation tool, not a serialization tool; the client shapes need no validation, only field access, and standard dataclasses have zero extra dependencies.
- **Module-level functions with env-var provider selection** (the `chain/adapter.py` approach) — rejected for this task because the adapter module dispatches to AI providers at runtime, whereas the client dispatches at construction time; ABC is the more natural contract for a dependency-injected HTTP client.
- **Plain dataclasses as Python ABC** — preferred because it matches the architecture's stated adapter pattern, costs nothing to import, and lets task test suites type their fixture as `ApiClient` with no runtime overhead.

---

## 2. Pre-flight

```bash
# Run from {WORKSPACE} root (spec-doc/)
git status                             # flag any M/?? on flask/ files before starting
git diff HEAD -- flask/                # confirm no uncommitted changes in target tree
cd flask && python -m pytest . -q     # record baseline pass count before ANY edits
```

**Note on Task 1 dependency:** `openapi.yaml` is the architectural prerequisite but is not required for this task to proceed. Dataclass field names are derived directly from the Flask route response shapes documented in CODEBASE CONTEXT below. If `openapi.yaml` exists at `{WORKSPACE}/openapi.yaml`, verify field names match before writing; if absent, proceed from route analysis.

**Baseline recorded**: run and record — do not proceed until you know the pre-task count.

**`flask/client/` does not exist** — the entire `flask/client/` tree is new. `git status` will show nothing under that path.

---

## 3. Files

### To Create (new)
- `flask/client/__init__.py` — empty package marker; makes `from client.client import ...` work when `flask/` is on `sys.path`
- `flask/client/client.py` — `ApiClient` ABC + all response/request dataclasses; the sole adapter boundary for all HTTP client code
- `flask/client/tests/__init__.py` — empty package marker for the test sub-package
- `flask/client/tests/conftest.py` — inserts `flask/` onto `sys.path` so `from client.client import ...` resolves correctly in pytest
- `flask/client/tests/test_client_types.py` — tests for all dataclass constructors, required-field enforcement, ABC instantiation guard, and structural purity of `client.py`

### To Modify (cite CODEBASE CONTEXT)
None. This task is purely additive.

### To Leave Alone
- `flask/modules/chain/adapter.py` — ELA Pattern #1 for AI; the client module mirrors its pattern but does not touch it
- `flask/modules/projects/routes.py` — route shapes are the source of truth for dataclass field names; read-only reference
- `flask/modules/context/routes.py` and `flask/modules/context/dto.py` — same; read-only reference
- `flask/tests/conftest.py` — existing test fixtures; do not alter
- `flask/requirements.txt` — no new dependencies; `abc` and `dataclasses` are stdlib

---

## 4. Implementation Steps

### Step 1: Create the `flask/client/` package skeleton

**Action**: Create two empty `__init__.py` files to establish the package and test sub-package.

**Files**: `flask/client/__init__.py` (new), `flask/client/tests/__init__.py` (new)

**Pattern**:
```python
# flask/client/__init__.py
# empty — package marker only
```

**Verify**: `python -c "import sys; sys.path.insert(0,'flask'); import client"` from `{WORKSPACE}` — expect no error.

---

### Step 2: Write `ApiClient` ABC and all response dataclasses

**Action**: Create `flask/client/client.py` with the adapter boundary. All dataclass field names use Python `snake_case`; `FlaskApiClient` (Task 4) is responsible for translating `createdAt` → `created_at` from JSON. This mirrors `flask/modules/chain/types.py:1–19` for the dataclass style and `flask/modules/chain/adapter.py:1–8` for the adapter boundary docstring.

**File**: `flask/client/client.py` (new)

**Pattern**:
```python
"""ApiClient — abstract base class and response dataclasses.

ELA Pattern #1 Adapter: consumers type their dependency as ApiClient.
MockApiClient (flask/client/mock_client.py) and
FlaskApiClient (flask/client/flask_client.py) subclass this.

INVARIANT: No Flask import here. No I/O. Pure Python contract only.
Enforced by flask/client/tests/test_client_types.py (structural test).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Request shapes
# ---------------------------------------------------------------------------

@dataclass
class FileInput:
    """One file to include when bootstrapping a project."""
    filename: str
    content: str


# ---------------------------------------------------------------------------
# Response shapes — derived from Flask route response payloads
# (projects/routes.py, context/routes.py, context/dto.py)
# ---------------------------------------------------------------------------

@dataclass
class SpecRecord:
    """One .md file within a project.

    content is None in list responses (GET /api/projects),
    str in detail responses (GET /api/projects/{id}).
    """
    filename: str
    label: str
    content: str | None = None


@dataclass
class ProjectRecord:
    """Full project shape — list and detail responses both use this.

    Derived from: projects/service.py list_projects/get_project return dicts.
    JSON key createdAt maps to created_at here; FlaskApiClient handles the rename.
    """
    id: str
    name: str
    created_at: str          # ISO-8601 with Z suffix, e.g. "2024-01-15T10:00:00.000Z"
    specs: list[SpecRecord]


@dataclass
class CreateProjectResult:
    """POST /api/projects response — id, name, created_at only; no specs field.

    Distinct from ProjectRecord because create returns a trimmed shape.
    Derived from: projects/service.py create_project return dict.
    """
    id: str
    name: str
    created_at: str


@dataclass
class UpdateResult:
    """PUT /api/projects/{id}/files/{filename} response."""
    success: bool


@dataclass
class DeleteResult:
    """DELETE /api/projects/{id} response."""
    success: bool


@dataclass
class ContextFileRecord:
    """GET /api/{key} response — mirrors context/dto.py GetContextResponse.

    Keys: builder | principles | codebase | references
    """
    content: str
    exists: bool


@dataclass
class WriteResult:
    """PUT /api/{key} response — mirrors context/dto.py PutContextResponse."""
    success: bool


@dataclass
class HealthStatus:
    """GET /health response."""
    status: str


# ---------------------------------------------------------------------------
# Abstract client — adapter boundary (14 routes total)
# ---------------------------------------------------------------------------

class ApiClient(ABC):
    """Interface for all Flask API interactions.

    Do not instantiate directly. Concrete implementations:
      - MockApiClient  (flask/client/mock_client.py)   — in-memory, zero I/O
      - FlaskApiClient (flask/client/flask_client.py)  — HTTP via requests
    """

    # Health ------------------------------------------------------------------

    @abstractmethod
    def health(self) -> HealthStatus:
        """GET /health"""

    # Projects ----------------------------------------------------------------

    @abstractmethod
    def list_projects(self) -> list[ProjectRecord]:
        """GET /api/projects"""

    @abstractmethod
    def get_project(self, project_id: str) -> ProjectRecord | None:
        """GET /api/projects/{project_id} — None if not found"""

    @abstractmethod
    def create_project(self, name: str, files: list[FileInput]) -> CreateProjectResult:
        """POST /api/projects"""

    @abstractmethod
    def update_file(self, project_id: str, filename: str, content: str) -> UpdateResult:
        """PUT /api/projects/{project_id}/files/{filename}"""

    @abstractmethod
    def delete_project(self, project_id: str) -> DeleteResult:
        """DELETE /api/projects/{project_id}"""

    # Context -----------------------------------------------------------------

    @abstractmethod
    def get_context(self, key: str) -> ContextFileRecord:
        """GET /api/{key}  — key: builder | principles | codebase | references"""

    @abstractmethod
    def write_context(self, key: str, content: str) -> WriteResult:
        """PUT /api/{key}  — key: builder | principles | codebase | references"""
```

**Verify**:
```bash
cd flask && python -c "from client.client import ApiClient, ProjectRecord, HealthStatus; print('ok')"
```
Expect: `ok`.

---

### Step 3: Write `flask/client/tests/conftest.py`

**Action**: Mirror the path-insertion pattern from `flask/tests/conftest.py:1–5`, adjusting depth (two levels up to reach `flask/`).

**File**: `flask/client/tests/conftest.py` (new)

**Pattern**:
```python
import sys
import os

# Insert flask/ onto sys.path so "from client.client import ..." resolves.
# Two levels up from flask/client/tests/ → flask/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
```

**Verify**: `cd flask && python -m pytest client/tests/ --collect-only 2>&1 | head -5` — expect collection without ImportError.

---

### Step 4: Write the test suite

**Action**: Create `flask/client/tests/test_client_types.py` with complete assertions covering dataclass construction, required-field enforcement, ABC guard, field absence checks, and one structural purity test (no Flask import in `client.py`).

**File**: `flask/client/tests/test_client_types.py` (new) — see §5 below for complete test body.

**Verify**: `cd flask && python -m pytest client/tests/test_client_types.py -v` — all tests pass.

---

## 5. Tests

Complete assertion bodies. Framework: `pytest` (matches `flask/tests/`, `flask/modules/chain/tests/`).

```python
"""Tests for ApiClient dataclasses and ABC contract.

Run from {WORKSPACE}: python -m pytest flask/client/tests/ -v
"""
from __future__ import annotations

import pathlib
import sys
import os

import pytest

# conftest.py inserts flask/ onto sys.path; explicit insert here for IDE support
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from client.client import (
    ApiClient,
    ContextFileRecord,
    CreateProjectResult,
    DeleteResult,
    FileInput,
    HealthStatus,
    ProjectRecord,
    SpecRecord,
    UpdateResult,
    WriteResult,
)


# ---------------------------------------------------------------------------
# ABC contract
# ---------------------------------------------------------------------------

def test_api_client_cannot_be_instantiated_directly():
    """ApiClient is abstract; instantiating it must raise TypeError."""
    with pytest.raises(TypeError):
        ApiClient()  # type: ignore[abstract]


def test_api_client_has_all_required_abstract_methods():
    """Exactly the expected 8 abstract methods — no more, no fewer."""
    expected = frozenset({
        'health',
        'list_projects',
        'get_project',
        'create_project',
        'update_file',
        'delete_project',
        'get_context',
        'write_context',
    })
    assert ApiClient.__abstractmethods__ == expected, (
        f"Abstract method mismatch. "
        f"Extra: {ApiClient.__abstractmethods__ - expected}. "
        f"Missing: {expected - ApiClient.__abstractmethods__}."
    )


def test_concrete_subclass_with_all_methods_is_instantiable():
    """A subclass that implements every abstract method can be instantiated."""
    class ConcreteClient(ApiClient):
        def health(self): ...
        def list_projects(self): ...
        def get_project(self, project_id): ...
        def create_project(self, name, files): ...
        def update_file(self, project_id, filename, content): ...
        def delete_project(self, project_id): ...
        def get_context(self, key): ...
        def write_context(self, key, content): ...

    assert isinstance(ConcreteClient(), ApiClient)


def test_partial_subclass_is_not_instantiable():
    """A subclass missing even one abstract method is still abstract."""
    class PartialClient(ApiClient):
        def health(self): ...
        # all other methods omitted intentionally

    with pytest.raises(TypeError):
        PartialClient()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# SpecRecord
# ---------------------------------------------------------------------------

def test_spec_record_content_defaults_to_none():
    s = SpecRecord(filename="epic.md", label="Epic")
    assert s.filename == "epic.md"
    assert s.label == "Epic"
    assert s.content is None, "content must default to None (absent from list responses)"


def test_spec_record_accepts_content():
    s = SpecRecord(filename="analysis.md", label="Analysis", content="# Analysis")
    assert s.content == "# Analysis"


def test_spec_record_requires_filename_and_label():
    with pytest.raises(TypeError):
        SpecRecord()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ProjectRecord
# ---------------------------------------------------------------------------

def test_project_record_instantiation():
    pr = ProjectRecord(
        id="my-project-1700000000000",
        name="My Project",
        created_at="2024-01-15T10:00:00.000Z",
        specs=[SpecRecord(filename="epic.md", label="Epic")],
    )
    assert pr.id == "my-project-1700000000000"
    assert pr.name == "My Project"
    assert pr.created_at == "2024-01-15T10:00:00.000Z"
    assert len(pr.specs) == 1
    assert pr.specs[0].filename == "epic.md"


def test_project_record_requires_all_four_fields():
    with pytest.raises(TypeError):
        ProjectRecord(id="x", name="y", created_at="z")  # type: ignore[call-arg]


def test_project_record_specs_can_be_empty_list():
    pr = ProjectRecord(id="x", name="y", created_at="2024-01-01T00:00:00.000Z", specs=[])
    assert pr.specs == []


# ---------------------------------------------------------------------------
# CreateProjectResult
# ---------------------------------------------------------------------------

def test_create_project_result_has_exactly_three_fields():
    result = CreateProjectResult(
        id="brand-new-1700000000000",
        name="Brand New",
        created_at="2024-01-15T10:00:00.000Z",
    )
    assert result.id == "brand-new-1700000000000"
    assert result.name == "Brand New"
    assert result.created_at.endswith("Z"), "created_at must use Z suffix (UTC)"


def test_create_project_result_has_no_specs_field():
    """POST /api/projects returns id/name/createdAt only — no specs."""
    result = CreateProjectResult(id="x", name="y", created_at="2024-01-01T00:00:00.000Z")
    assert not hasattr(result, "specs"), (
        "CreateProjectResult must not have a specs field; "
        "create response is a trimmed shape distinct from ProjectRecord"
    )


def test_create_project_result_requires_all_three_fields():
    with pytest.raises(TypeError):
        CreateProjectResult(id="x", name="y")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# UpdateResult / DeleteResult
# ---------------------------------------------------------------------------

def test_update_result_success_true():
    assert UpdateResult(success=True).success is True


def test_update_result_success_false():
    assert UpdateResult(success=False).success is False


def test_delete_result_success_true():
    assert DeleteResult(success=True).success is True


def test_delete_result_success_false():
    assert DeleteResult(success=False).success is False


# ---------------------------------------------------------------------------
# ContextFileRecord
# ---------------------------------------------------------------------------

def test_context_file_record_present():
    r = ContextFileRecord(content="# Builder profile", exists=True)
    assert r.content == "# Builder profile"
    assert r.exists is True


def test_context_file_record_absent():
    r = ContextFileRecord(content="", exists=False)
    assert r.content == ""
    assert r.exists is False


def test_context_file_record_requires_both_fields():
    with pytest.raises(TypeError):
        ContextFileRecord(content="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# WriteResult
# ---------------------------------------------------------------------------

def test_write_result_success():
    assert WriteResult(success=True).success is True


def test_write_result_requires_success_field():
    with pytest.raises(TypeError):
        WriteResult()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------

def test_health_status_ok():
    h = HealthStatus(status="ok")
    assert h.status == "ok"


def test_health_status_requires_status_field():
    with pytest.raises(TypeError):
        HealthStatus()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# FileInput
# ---------------------------------------------------------------------------

def test_file_input_instantiation():
    f = FileInput(filename="epic.md", content="# Epic")
    assert f.filename == "epic.md"
    assert f.content == "# Epic"


def test_file_input_requires_both_fields():
    with pytest.raises(TypeError):
        FileInput(filename="only-name.md")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Structural: client.py must not import Flask
# ---------------------------------------------------------------------------

def test_client_module_has_no_flask_import():
    """client.py is pure Python — no Flask, no requests, no I/O.

    If this fails, the adapter boundary is compromised:
    implementations (MockApiClient, FlaskApiClient) must handle I/O,
    not the abstract interface.
    """
    client_py = pathlib.Path(__file__).parent.parent / "client.py"
    assert client_py.exists(), f"client.py not found at {client_py}"
    text = client_py.read_text(encoding="utf-8")
    assert "from flask" not in text, "client.py must not import Flask"
    assert "import flask" not in text, "client.py must not import Flask"
    assert "import requests" not in text, "client.py must not import requests"
```

**Test count delta**: 30 new tests in this file.

---

## 6. Commit Plan

One logical unit → one commit:

1. `feat(client): add ApiClient ABC and response dataclasses` — `flask/client/__init__.py`, `flask/client/client.py`: adapter boundary, all 8 abstract methods, 9 dataclasses (FileInput, SpecRecord, ProjectRecord, CreateProjectResult, UpdateResult, DeleteResult, ContextFileRecord, WriteResult, HealthStatus)

2. `test(client): add dataclass and ABC contract test suite` — `flask/client/tests/__init__.py`, `flask/client/tests/conftest.py`, `flask/client/tests/test_client_types.py`: 30 tests covering instantiation, required fields, ABC guard, structural purity

**Deviation logging**: if any step diverges from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# From {WORKSPACE} root
cd flask && python -m pytest . -v
```

**Expected delta**: baseline → baseline + 30 passing. Zero pre-existing tests broken. The only new path under collection is `flask/client/tests/test_client_types.py`.

To run the new suite in isolation:
```bash
cd flask && python -m pytest client/tests/test_client_types.py -v
```
Expect: `30 passed`.

---

## 8. Rollback

**Per-commit**: each of the two commits above is independently revertible.
```bash
git revert <commit-sha>   # creates a new revert commit; safe on shared branches
```

**Per-branch**: if verification fails and you need a clean slate:
```bash
git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destructive; confirm with user first
```
The `flask/client/` directory contains only new files — no existing file has been touched — so a targeted delete is also safe:
```bash
rm -rf flask/client/              # removes all new files; leaves existing tree intact
```

---

## 9. Deviations Allowed

- **`openapi.yaml` exists at `{WORKSPACE}/openapi.yaml`** → compare its `ProjectRecord`, `ContextFileRecord`, and other schema component field names against the dataclasses written here; if names differ, the spec is authoritative — update the dataclasses and log as a deviation in the commit body.
- **`openapi.yaml` does not exist** → proceed as written; dataclasses are derived from Flask route payloads in CODEBASE CONTEXT.
- **Test framework mismatch** → the repo uses plain `pytest`; if a future conftest introduces fixtures that conflict, adapt silently and note in commit body.
- **`created_at` vs `createdAt` naming conflict** → if `openapi.yaml` uses `createdAt` as the Python field name (unusual but possible), rename to match; log deviation. The default here is `created_at` (Python convention).
- **Step N reveals an obvious simplification for Step N+1** → take it, log in commit body.
- **Side-effect required** (push, publish, schema migration) → STOP, mark `[REQUIRES APPROVAL]`, ask user before proceeding.

---

## 10. Out of Scope

This task delivers only the abstract interface and dataclasses. It does not implement any method body, make any HTTP call, or hold any in-memory state. An eager executor might try to extend scope into:

- **`MockApiClient` implementation** (`flask/client/mock_client.py`) — Task 3; requires understanding of how the mock should behave across method sequences, which is its own design surface.
- **`FlaskApiClient` implementation** (`flask/client/flask_client.py`) — Task 4; requires `requests` as a dependency and a live Flask server to test against; blocked on Tasks 2 and 3.
- **`openapi.yaml` authoring** — Task 1; if it doesn't exist, note it as a missing dependency but do not write it here.
- **Retry logic, timeout configuration, or request middleware** — explicitly deferred in the epic port budget; belongs in `FlaskApiClient` only.
- **Parametrized shared test runner across mock and real clients** — deferred per architecture; assertion functions are owned by each task's test suite, not this interface module.
- **`flask/client/__init__.py` re-exports** — do not add `from client.client import *` or convenience re-exports; keep the `__init__.py` empty until a second consumer exists that names a convenience import.

**Rule for the executor**: if a change appears helpful but is listed here, stop and flag as a deviation rather than expanding scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) — adapter pattern rationale, component design
- [Epic](./epic.md) — task scope and port budget
- [Timeline](./timeline.md) — update task status to `done` after verification passes