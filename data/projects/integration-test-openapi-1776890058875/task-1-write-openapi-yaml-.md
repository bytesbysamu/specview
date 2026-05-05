# Implementation Guide: Task 1 — Write `openapi.yaml`

---

## 1. Context

This task translates the prose API contract in `flask/api-contract.md` into a machine-readable OpenAPI 3.1 YAML schema covering all 14 route operations across 9 paths. The file is a build-phase artifact: `datamodel-codegen` (Task 2) reads it to generate `flask/dto.py`, and the Pydantic models in that file become the primary assertion mechanism in `flask/tests/test_contract.py` (Task 4). Accuracy here is load-bearing — a missing `required` field or misnamed property will produce a DTO that silently accepts invalid Flask responses downstream.

**Trade-offs considered:**
- Hand-authoring Pydantic models directly — rejected because manual DTOs drift from the spec and require ongoing discipline to keep aligned; codegen from a single YAML source is authoritative by construction.
- Generating the YAML from live Express responses at runtime — rejected because Express is the server being decommissioned; coupling schema generation to its availability reintroduces the dependency the architecture explicitly eliminates.
- OpenAPI 3.1 YAML (chosen) — `datamodel-codegen` has first-class OpenAPI 3.1 support with Pydantic v2 output; the YAML is human-readable enough to review line-by-line against `api-contract.md`.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From the spec-doc/ root
git status                                          # flag unrelated M entries
git diff HEAD -- flask/openapi.yaml                 # should show "no such path" (file doesn't exist yet)
cd flask && python -m pytest tests/ -q              # record baseline pass count
```

**If working tree is dirty on any `flask/` file**: stash or commit those changes separately before starting.

**Baseline recorded**: Run `python -m pytest tests/ -q` from `flask/` and note the passing count. Based on the committed test files (`test_health.py` = 9, `test_project.py` = 31, `test_context_files.py` ≈ 21) the floor is approximately 61 passing tests; the exact number is authoritative.

---

## 3. Files

### To Create (new)
- `flask/openapi.yaml` — OpenAPI 3.1 schema for all routes in `flask/api-contract.md`; consumed by `datamodel-codegen` in Task 2
- `flask/tests/test_openapi_yaml.py` — pytest suite validating YAML structure and required-field coverage

### To Modify (cite CODEBASE CONTEXT)
- `flask/requirements.txt` — currently `flask, flask-cors, pytest, anthropic`; add `pyyaml>=6.0` (required to load the YAML in tests)

### To Leave Alone
- `flask/api-contract.md` — source of truth; read only, never edit
- `flask/modules/**` — no Flask route changes in this task
- `flask/tests/conftest.py` — no new fixtures needed; `test_openapi_yaml.py` uses no Flask app fixture
- `flask/create_app.py` — no changes; this task adds no blueprints

---

## 4. Implementation Steps

### Step 1: Add `pyyaml` to requirements

**Action**: Append `pyyaml>=6.0` to `flask/requirements.txt`

**File**: `flask/requirements.txt` (existing — 4 lines)

**Pattern**:
```text
flask>=3.0.0
flask-cors>=4.0.0
pytest>=8.0.0
anthropic
pyyaml>=6.0
```

**Verify**: `pip install pyyaml>=6.0` installs without error; `python -c "import yaml; print(yaml.__version__)"` prints a version ≥ 6.0.

---

### Step 2: Write `flask/openapi.yaml`

**Action**: Create the file. Translate every row in `flask/api-contract.md` into paths + schema components. Do not add routes from the "AI Routes (Phase 2)" section — those are explicitly deferred.

**File**: `flask/openapi.yaml` (new)

**Pattern** — full content to write verbatim:

```yaml
openapi: "3.1.0"
info:
  title: Spec Doc API
  version: "1.0.0"
  description: >
    Contract for Express (3100) → Flask (3101) migration.
    Derived strictly from flask/api-contract.md. Do not add routes not
    present in that file.

paths:

  /health:
    get:
      operationId: getHealth
      summary: Health check
      responses:
        "200":
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /api/builder:
    get:
      operationId: getBuilder
      summary: Get builder profile content
      responses:
        "200":
          description: Builder profile file content and existence flag
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ContextResponse'
    put:
      operationId: putBuilder
      summary: Overwrite builder profile content
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PutContextRequest'
      responses:
        "200":
          description: Write successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SuccessResponse'
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/principles:
    get:
      operationId: getPrinciples
      summary: Get principles content
      responses:
        "200":
          description: Principles file content and existence flag
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ContextResponse'
    put:
      operationId: putPrinciples
      summary: Overwrite principles content
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PutContextRequest'
      responses:
        "200":
          description: Write successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SuccessResponse'
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/codebase:
    get:
      operationId: getCodebase
      summary: Get codebase context content
      responses:
        "200":
          description: Codebase file content and existence flag
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ContextResponse'
    put:
      operationId: putCodebase
      summary: Overwrite codebase context content
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PutContextRequest'
      responses:
        "200":
          description: Write successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SuccessResponse'
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/references:
    get:
      operationId: getReferences
      summary: Get references content
      responses:
        "200":
          description: References file content and existence flag
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ContextResponse'
    put:
      operationId: putReferences
      summary: Overwrite references content
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PutContextRequest'
      responses:
        "200":
          description: Write successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SuccessResponse'
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/projects:
    get:
      operationId: listProjects
      summary: List all projects sorted newest-first
      responses:
        "200":
          description: Array of project summaries; empty array if no projects exist
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ProjectSummary'
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
    post:
      operationId: createProject
      summary: Create a new project with initial files
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateProjectRequest'
      responses:
        "201":
          description: Project created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProjectCreated'
        "400":
          description: name missing, files missing, or files not an array
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/projects/{id}:
    get:
      operationId: getProject
      summary: Get a single project with full file content
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Project with full spec content
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProjectDetail'
        "404":
          description: Project not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
    delete:
      operationId: deleteProject
      summary: Delete a project and all its files
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Project deleted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SuccessResponse'
        "404":
          description: Project not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/projects/{id}/files/{filename}:
    put:
      operationId: updateProjectFile
      summary: Write or overwrite a single file within a project
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
        - name: filename
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateFileRequest'
      responses:
        "200":
          description: File written
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SuccessResponse'
        "404":
          description: Project not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:

    HealthResponse:
      type: object
      required: [status]
      properties:
        status:
          type: string
          example: ok

    ContextResponse:
      type: object
      required: [content, exists]
      properties:
        content:
          type: string
        exists:
          type: boolean

    PutContextRequest:
      type: object
      required: [content]
      properties:
        content:
          type: string

    SuccessResponse:
      type: object
      required: [success]
      properties:
        success:
          type: boolean

    ErrorResponse:
      type: object
      required: [error]
      properties:
        error:
          type: string

    SpecSummary:
      type: object
      required: [filename, label]
      properties:
        filename:
          type: string
        label:
          type: string

    SpecDetail:
      type: object
      required: [filename, label, content]
      properties:
        filename:
          type: string
        label:
          type: string
        content:
          type: string

    ProjectSummary:
      type: object
      required: [id, name, createdAt, specs]
      properties:
        id:
          type: string
        name:
          type: string
        createdAt:
          type: string
          format: date-time
        specs:
          type: array
          items:
            $ref: '#/components/schemas/SpecSummary'

    ProjectDetail:
      type: object
      required: [id, name, createdAt, specs]
      properties:
        id:
          type: string
        name:
          type: string
        createdAt:
          type: string
          format: date-time
        specs:
          type: array
          items:
            $ref: '#/components/schemas/SpecDetail'

    ProjectCreated:
      type: object
      required: [id, name, createdAt]
      properties:
        id:
          type: string
        name:
          type: string
        createdAt:
          type: string
          format: date-time

    NewProjectFile:
      type: object
      required: [filename, content]
      properties:
        filename:
          type: string
        content:
          type: string

    CreateProjectRequest:
      type: object
      required: [name, files]
      properties:
        name:
          type: string
        files:
          type: array
          items:
            $ref: '#/components/schemas/NewProjectFile'

    UpdateFileRequest:
      type: object
      required: [content]
      properties:
        content:
          type: string
```

**Verify**: `python -c "import yaml; yaml.safe_load(open('openapi.yaml'))"` from `flask/` — expect no exception.

---

### Step 3: Write `flask/tests/test_openapi_yaml.py`

**Action**: Create the test file. Use `pyyaml` to load `flask/openapi.yaml` and assert structural correctness.

**File**: `flask/tests/test_openapi_yaml.py` (new)

**Pattern** — see Section 5 (Tests) for the complete file.

**Verify**: `cd flask && python -m pytest tests/test_openapi_yaml.py -v` — expect 12 tests collected, 12 passed.

---

## 5. Tests

Full test file for `flask/tests/test_openapi_yaml.py`:

```python
"""Structural validation of flask/openapi.yaml.

Verifies that the YAML is well-formed and that all paths, operations, and
schema components required by api-contract.md are present with correct
required-field declarations.

Run: cd flask && python -m pytest tests/test_openapi_yaml.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Resolve flask/openapi.yaml relative to this test file:
#   tests/test_openapi_yaml.py  →  parent = tests/  →  parent.parent = flask/
_OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


@pytest.fixture(scope="module")
def spec() -> dict:
    """Load and parse openapi.yaml once for the entire module."""
    assert _OPENAPI_PATH.exists(), (
        f"openapi.yaml not found at {_OPENAPI_PATH} — run Step 2 first"
    )
    with _OPENAPI_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_yaml_parses_without_error(spec):
    """File must be valid YAML and produce a non-empty dict."""
    assert isinstance(spec, dict), "openapi.yaml must parse to a mapping"
    assert spec, "openapi.yaml must not be empty"


def test_openapi_version_is_3_1(spec):
    """openapi field must be 3.1.x — required for datamodel-codegen v2 output."""
    version = spec.get("openapi", "")
    assert version.startswith("3.1"), (
        f"expected openapi: '3.1.x', got '{version}'"
    )


def test_all_paths_present(spec):
    """All 9 paths from api-contract.md must be defined."""
    paths = set(spec.get("paths", {}).keys())
    expected = {
        "/health",
        "/api/builder",
        "/api/principles",
        "/api/codebase",
        "/api/references",
        "/api/projects",
        "/api/projects/{id}",
        "/api/projects/{id}/files/{filename}",
    }
    missing = expected - paths
    assert not missing, f"Paths missing from openapi.yaml: {missing}"


def test_context_paths_have_get_and_put(spec):
    """Each of the four context paths must define both GET and PUT operations."""
    context_paths = ["/api/builder", "/api/principles", "/api/codebase", "/api/references"]
    paths = spec.get("paths", {})
    for path in context_paths:
        ops = set(paths.get(path, {}).keys())
        assert "get" in ops, f"{path}: missing GET operation"
        assert "put" in ops, f"{path}: missing PUT operation"


def test_projects_path_has_get_and_post(spec):
    """/api/projects must define both GET (list) and POST (create)."""
    ops = set(spec.get("paths", {}).get("/api/projects", {}).keys())
    assert "get" in ops, "/api/projects: missing GET operation"
    assert "post" in ops, "/api/projects: missing POST operation"


def test_project_id_path_has_get_and_delete(spec):
    """/api/projects/{id} must define GET (detail) and DELETE."""
    ops = set(spec.get("paths", {}).get("/api/projects/{id}", {}).keys())
    assert "get" in ops, "/api/projects/{id}: missing GET operation"
    assert "delete" in ops, "/api/projects/{id}: missing DELETE operation"


def test_all_schema_components_present(spec):
    """All 13 named schemas required for DTO generation must be defined."""
    schemas = set(spec.get("components", {}).get("schemas", {}).keys())
    expected = {
        "HealthResponse",
        "ContextResponse",
        "PutContextRequest",
        "SuccessResponse",
        "ErrorResponse",
        "SpecSummary",
        "SpecDetail",
        "ProjectSummary",
        "ProjectDetail",
        "ProjectCreated",
        "NewProjectFile",
        "CreateProjectRequest",
        "UpdateFileRequest",
    }
    missing = expected - schemas
    assert not missing, f"Schema components missing: {missing}"


def test_context_response_required_fields(spec):
    """ContextResponse must require both content and exists — mirrors dto.py GetContextResponse."""
    schema = spec["components"]["schemas"]["ContextResponse"]
    required = set(schema.get("required", []))
    assert "content" in required, "ContextResponse: 'content' must be in required"
    assert "exists" in required, "ContextResponse: 'exists' must be in required"


def test_spec_detail_requires_content(spec):
    """SpecDetail must require content — distinguishes it from SpecSummary (list vs detail)."""
    schema = spec["components"]["schemas"]["SpecDetail"]
    required = set(schema.get("required", []))
    assert "content" in required, (
        "SpecDetail: 'content' must be required — "
        "GET /api/projects/:id includes file content, GET /api/projects does not"
    )


def test_project_summary_required_fields(spec):
    """ProjectSummary must declare all four fields as required."""
    schema = spec["components"]["schemas"]["ProjectSummary"]
    required = set(schema.get("required", []))
    for field in ("id", "name", "createdAt", "specs"):
        assert field in required, f"ProjectSummary: '{field}' must be required"


def test_create_project_request_required_fields(spec):
    """CreateProjectRequest must require both name and files."""
    schema = spec["components"]["schemas"]["CreateProjectRequest"]
    required = set(schema.get("required", []))
    assert "name" in required, "CreateProjectRequest: 'name' must be required"
    assert "files" in required, "CreateProjectRequest: 'files' must be required"


def test_error_response_requires_error_field(spec):
    """ErrorResponse must require 'error' — Angular frontend checks this key."""
    schema = spec["components"]["schemas"]["ErrorResponse"]
    required = set(schema.get("required", []))
    assert "error" in required, "ErrorResponse: 'error' must be required"
```

---

## 6. Commit Plan

Two commits, each independently revertible:

1. `feat(openapi): add openapi.yaml from api-contract.md` — `flask/openapi.yaml`, `flask/requirements.txt`: schema covering all 14 operations across 9 paths; pyyaml dependency added for test consumption
2. `test(openapi): validate yaml structure and required fields` — `flask/tests/test_openapi_yaml.py`: 12 tests asserting path coverage, operation presence, and schema required-field declarations

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd flask && python -m pytest tests/ -q
```

**Expected delta**: baseline → baseline + 12 passing. Zero pre-existing tests broken.

Additionally verify the YAML is consumable by the codegen tool (preview only — do not commit the generated output):
```bash
pip install datamodel-code-generator
cd flask && datamodel-codegen --input openapi.yaml --input-file-type openapi --output /tmp/dto_preview.py --output-model-type pydantic_v2.BaseModel
cat /tmp/dto_preview.py   # confirm 13 model classes appear
```

This preview step is informational — the generated file goes to `/tmp`, not to `flask/dto.py`. Task 2 owns that commit.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` with no cascade risk — neither commit touches existing Python modules or tests.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` restores the exact pre-task state. The only new files are `flask/openapi.yaml` and `flask/tests/test_openapi_yaml.py`; both can also be deleted individually without side effects.

---

## 9. Deviations Allowed

- **Path doesn't exist in codebase**: `flask/api-contract.md` is the authoritative source. If a route appears in the Flask `routes.py` files but not in `api-contract.md`, do not add it to `openapi.yaml` — flag the discrepancy in the commit body instead.
- **Test framework mismatch**: `test_openapi_yaml.py` uses plain `pytest` + `assert`; this matches `flask/tests/test_health.py` and `flask/tests/test_project.py`. If the project's convention changes, translate silently and note in commit body.
- **pyyaml version conflict**: if `pyyaml>=6.0` conflicts with an existing transitive dependency, use `pyyaml` without the version pin and note the deviation.
- **datamodel-codegen preview fails**: this is informational only and does not block the commit. Log the failure, note the specific error, and let Task 2 resolve it — the openapi.yaml commit stands.
- **Side-effect required** (pip publish, pushing to remote): STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

This task produces the YAML schema file and a test suite that validates its static structure. It does not execute the codegen pipeline, write any Python, or integrate with the Flask test client. The following items are explicitly deferred and must not be absorbed into this task even if they seem like natural next steps:

- `flask/dto.py` generation via `datamodel-codegen` — owned by Task 2; the codegen command and its output are out of scope here
- `flask/tests/fixtures/` and `flask/tests/capture.py` — owned by Task 3; capturing Express responses requires Express to be live, which is a separate operational concern
- `flask/tests/test_contract.py` — owned by Task 4; the full integration suite depends on both `dto.py` and `fixtures/` being present
- AI routes (`/api/ai/text/*`, `/api/ai/implement`, `/api/container/*`) — explicitly marked "Phase 2" in `flask/api-contract.md`; adding them to `openapi.yaml` now would generate DTOs with no test coverage and no Flask implementation to validate against
- Swagger UI or any documentation portal — `openapi.yaml` is a codegen input, not a consumer-facing document; no UI is wired in this capability

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for the DTO + fixture + test pipeline
- [Epic](./epic.md) — Task scope and effort estimates
- [Timeline](./timeline.md) — Update Task 1 status to `done` after verification passes
- `flask/api-contract.md` — Primary source for every route, field, and response shape in the schema