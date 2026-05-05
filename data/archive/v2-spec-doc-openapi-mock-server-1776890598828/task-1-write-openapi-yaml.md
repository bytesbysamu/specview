# Implementation Guide: Task 1 — Write openapi.yaml

---

## 1. Context

This task produces `flask/openapi.yaml` — the single contract artifact that gates everything downstream in this epic. Tasks 2 (DTO generation) and 3 (mock server) cannot begin without a validated spec, because both consume it directly: `datamodel-codegen` generates the Pydantic models from it, and `mock_server.py` will implement exactly the routes it defines. The spec is written against the routes already deployed in the Flask app (confirmed by reading `flask/modules/projects/routes.py` and `flask/modules/context/routes.py`), so it is descriptive of reality, not aspirational.

**Important deviation from the epic**: The epic describes context routes as `GET /PUT /api/context/{key}`. The actual implementation uses four flat paths (`/api/builder`, `/api/principles`, `/api/codebase`, `/api/references`) with no path parameter. The spec documents the actual routes. Changing to the parameterized pattern would be a breaking change to the Angular frontend and is explicitly out of scope for this task.

**Trade-offs considered**:
- `/api/context/{key}` parameterized route (epic's described shape) — rejected because the Angular frontend and Flask implementation already use flat paths; retrofitting would break Task 4 validation before it starts
- OpenAPI 3.1 (JSON Schema alignment) — rejected; `datamodel-codegen` and `openapi-spec-validator` both have more stable 3.0 support, which is the safer choice for a one-day task
- Separate YAML files per module — rejected; a single ~220-line file is the appropriate surface for 14 endpoints and one human reader; splitting adds tooling complexity with no consumer for the modular form

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/spec-doc

# Confirm no openapi.yaml already exists
ls flask/openapi.yaml 2>/dev/null && echo "EXISTS — review before overwriting" || echo "Clean — proceed"

# Confirm no flask/dtos/ directory (Task 2 hasn't run)
ls flask/dtos/ 2>/dev/null && echo "dtos/ EXISTS — unexpected" || echo "Clean — proceed"

# Record baseline test count
cd flask && python -m pytest --tb=no -q 2>&1 | tail -5

# Confirm openapi-spec-validator is NOT yet installed (expected)
pip show openapi-spec-validator 2>/dev/null && echo "already installed" || echo "not installed — will add"

# Flag any unrelated dirty files
git status
```

**If working tree is dirty on `flask/openapi.yaml` or `flask/requirements.txt`**: stash or commit those changes separately before starting.

**Baseline recorded**: The existing suite has **~31+ tests** across `flask/tests/` and `flask/modules/chain/tests/`. Record the exact count from the pytest output above.

---

## 3. Files

### To Create (new)
- `flask/openapi.yaml` — OpenAPI 3.0.3 contract; the build artifact for Tasks 2 and 3
- `flask/tests/test_openapi_spec.py` — pytest suite validating spec structure and coverage

### To Modify
- `flask/requirements.txt` — add `openapi-spec-validator>=0.5` (currently has `flask`, `flask-cors`, `pytest`, `anthropic`; no spec validator present)

### To Leave Alone
- `flask/modules/projects/routes.py` — source of truth for project route shapes; do not change routes to match the spec
- `flask/modules/context/routes.py` — source of truth for context route shapes; flat paths are correct
- `flask/modules/context/dto.py` — existing Pydantic models; Task 2 generates a new layer in `flask/dtos/`, does not replace this
- `flask/tests/conftest.py` — existing pytest fixtures; new test file will import from it
- `flask/modules/chain/` — chain infrastructure; unrelated to this task

---

## 4. Implementation Steps

### Step 1: Add openapi-spec-validator to requirements.txt

**Action**: Append `openapi-spec-validator>=0.5` to `flask/requirements.txt`, then install it.

**File**: `flask/requirements.txt`

**Pattern**:
```
flask>=3.0.0
flask-cors>=4.0.0
pytest>=8.0.0
anthropic
openapi-spec-validator>=0.5
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/flask
pip install -r requirements.txt
python -c "import openapi_spec_validator; print('ok')"
```
Expect: `ok` with no import errors.

---

### Step 2: Write flask/openapi.yaml

**Action**: Create `flask/openapi.yaml` with the exact content below. The route shapes are ported verbatim from the live code — `flask/modules/projects/routes.py` (lines 1–80) and `flask/modules/context/routes.py` (lines 33–63). Every field name is confirmed against the running service tests in `flask/tests/test_project.py` and `flask/tests/test_context_files.py`.

**File**: `flask/openapi.yaml` (new)

**Full content to write verbatim**:

```yaml
openapi: "3.0.3"

info:
  title: Spec Doc API
  version: "1.0.0"
  description: >
    Phase 1 contract — health check, projects CRUD, and context
    read/write for four named keys (builder, principles, codebase,
    references). This file is the build artifact; flask/dtos/ and
    mock_server.py are derived from it.

servers:
  - url: http://localhost:3101
    description: Flask development server
  - url: http://localhost:3102
    description: Mock server (Task 3)

paths:

  /health:
    get:
      summary: Health check
      operationId: getHealth
      responses:
        "200":
          description: Server is healthy
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/HealthResponse"

  /api/projects:
    get:
      summary: List all projects, newest first
      operationId: listProjects
      responses:
        "200":
          description: Array of project summaries
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/ProjectSummary"
        "500":
          $ref: "#/components/responses/InternalError"
    post:
      summary: Create a new project
      operationId: createProject
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ProjectCreateRequest"
      responses:
        "201":
          description: Project created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProjectCreateResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "500":
          $ref: "#/components/responses/InternalError"

  /api/projects/{id}:
    get:
      summary: Get project detail with full file contents
      operationId: getProject
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Project detail
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProjectDetail"
        "404":
          $ref: "#/components/responses/NotFound"
        "500":
          $ref: "#/components/responses/InternalError"
    delete:
      summary: Delete a project
      operationId: deleteProject
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
                $ref: "#/components/schemas/SuccessResponse"
        "404":
          $ref: "#/components/responses/NotFound"
        "500":
          $ref: "#/components/responses/InternalError"

  /api/projects/{id}/files/{filename}:
    put:
      summary: Update a file within a project
      operationId: updateProjectFile
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
              $ref: "#/components/schemas/FileUpdateRequest"
      responses:
        "200":
          description: File updated
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "404":
          $ref: "#/components/responses/NotFound"
        "500":
          $ref: "#/components/responses/InternalError"

  /api/builder:
    get:
      summary: Read builder context file
      operationId: getBuilder
      responses:
        "200":
          description: Builder context
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextResponse"
    put:
      summary: Write builder context file
      operationId: putBuilder
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextUpdateRequest"
      responses:
        "200":
          description: Context updated
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "500":
          $ref: "#/components/responses/InternalError"

  /api/principles:
    get:
      summary: Read principles context file
      operationId: getPrinciples
      responses:
        "200":
          description: Principles context
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextResponse"
    put:
      summary: Write principles context file
      operationId: putPrinciples
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextUpdateRequest"
      responses:
        "200":
          description: Context updated
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "500":
          $ref: "#/components/responses/InternalError"

  /api/codebase:
    get:
      summary: Read codebase context file
      operationId: getCodebase
      responses:
        "200":
          description: Codebase context
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextResponse"
    put:
      summary: Write codebase context file
      operationId: putCodebase
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextUpdateRequest"
      responses:
        "200":
          description: Context updated
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "500":
          $ref: "#/components/responses/InternalError"

  /api/references:
    get:
      summary: Read references context file
      operationId: getReferences
      responses:
        "200":
          description: References context
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextResponse"
    put:
      summary: Write references context file
      operationId: putReferences
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextUpdateRequest"
      responses:
        "200":
          description: Context updated
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "500":
          $ref: "#/components/responses/InternalError"

components:

  schemas:

    HealthResponse:
      type: object
      required: [status]
      properties:
        status:
          type: string
          enum: [ok]

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
            $ref: "#/components/schemas/SpecSummary"

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
            $ref: "#/components/schemas/SpecDetail"

    ProjectCreateRequest:
      type: object
      required: [name, files]
      properties:
        name:
          type: string
        files:
          type: array
          items:
            $ref: "#/components/schemas/FileInput"

    FileInput:
      type: object
      required: [filename, content]
      properties:
        filename:
          type: string
        content:
          type: string

    ProjectCreateResponse:
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

    FileUpdateRequest:
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

    ContextResponse:
      type: object
      required: [content, exists]
      properties:
        content:
          type: string
        exists:
          type: boolean

    ContextUpdateRequest:
      type: object
      required: [content]
      properties:
        content:
          type: string

    ErrorResponse:
      type: object
      required: [error]
      properties:
        error:
          type: string

  responses:

    BadRequest:
      description: Missing or invalid request fields
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"

    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"

    InternalError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/flask
python -m openapi_spec_validator openapi.yaml
```
Expect: zero output, exit code 0. Any output is an error — fix before proceeding.

---

### Step 3: Validate with CLI and confirm line count

**Action**: Run the validator, confirm exit code is 0, and note the line count.

**File**: `flask/openapi.yaml`

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/flask
python -m openapi_spec_validator openapi.yaml && echo "VALID"
wc -l openapi.yaml
```
Expect: `VALID` on stdout. Line count will be ~220 (higher than the epic's 150–200 estimate because the actual context routes are flat, not parameterized — see Context section above).

---

### Step 4: Write the pytest test file

**Action**: Create `flask/tests/test_openapi_spec.py`. Tests load the YAML and assert structural correctness — no HTTP calls. The test style mirrors `flask/tests/test_health.py`: plain `def test_*` functions with direct `assert` statements and f-string failure messages.

**File**: `flask/tests/test_openapi_spec.py` (new)

See **Section 5** for the complete test body.

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/flask
python -m pytest tests/test_openapi_spec.py -v
```
Expect: all tests in that file pass.

---

## 5. Tests

```python
"""
Structural validation tests for flask/openapi.yaml.

These tests load and parse the spec but make no HTTP calls.
They ensure the spec covers the required routes and schemas before
datamodel-codegen (Task 2) or mock_server.py (Task 3) consume it.
"""
from __future__ import annotations

import pathlib
import pytest
import yaml
from openapi_spec_validator import validate

SPEC_PATH = pathlib.Path(__file__).parent.parent / "openapi.yaml"


@pytest.fixture(scope="module")
def spec() -> dict:
    with SPEC_PATH.open() as f:
        return yaml.safe_load(f)


# ── File existence ──────────────────────────────────────────────────────────

def test_openapi_yaml_exists():
    assert SPEC_PATH.exists(), f"openapi.yaml not found at {SPEC_PATH}"


def test_openapi_yaml_is_non_empty():
    assert SPEC_PATH.stat().st_size > 0, "openapi.yaml is empty"


# ── Spec-validator passes ────────────────────────────────────────────────────

def test_spec_is_valid_openapi_30(spec):
    # validate() raises openapi_spec_validator.exceptions.OpenAPISpecValidatorError on failure
    validate(spec)  # no assertion needed — exception = failure


# ── Top-level structure ──────────────────────────────────────────────────────

def test_openapi_version_is_3(spec):
    version = spec.get("openapi", "")
    assert version.startswith("3."), \
        f"expected openapi 3.x, got '{version}'"


def test_info_title_present(spec):
    assert "title" in spec.get("info", {}), \
        "info.title is required"


def test_info_version_present(spec):
    assert "version" in spec.get("info", {}), \
        "info.version is required"


# ── Required paths present ───────────────────────────────────────────────────

REQUIRED_PATHS = [
    "/health",
    "/api/projects",
    "/api/projects/{id}",
    "/api/projects/{id}/files/{filename}",
    "/api/builder",
    "/api/principles",
    "/api/codebase",
    "/api/references",
]


@pytest.mark.parametrize("path", REQUIRED_PATHS)
def test_required_path_present(spec, path):
    paths = spec.get("paths", {})
    assert path in paths, \
        f"path '{path}' missing from spec — Tasks 2 and 3 depend on this"


# ── Required HTTP methods ────────────────────────────────────────────────────

@pytest.mark.parametrize("path,method", [
    ("/health", "get"),
    ("/api/projects", "get"),
    ("/api/projects", "post"),
    ("/api/projects/{id}", "get"),
    ("/api/projects/{id}", "delete"),
    ("/api/projects/{id}/files/{filename}", "put"),
    ("/api/builder", "get"),
    ("/api/builder", "put"),
    ("/api/principles", "get"),
    ("/api/principles", "put"),
    ("/api/codebase", "get"),
    ("/api/codebase", "put"),
    ("/api/references", "get"),
    ("/api/references", "put"),
])
def test_method_present(spec, path, method):
    paths = spec.get("paths", {})
    assert path in paths, f"path '{path}' missing"
    assert method in paths[path], \
        f"method '{method}' missing from '{path}'"


# ── Required schema components present ──────────────────────────────────────

REQUIRED_SCHEMAS = [
    "HealthResponse",
    "ProjectSummary",
    "ProjectDetail",
    "SpecSummary",
    "SpecDetail",
    "ProjectCreateRequest",
    "ProjectCreateResponse",
    "FileInput",
    "FileUpdateRequest",
    "SuccessResponse",
    "ContextResponse",
    "ContextUpdateRequest",
    "ErrorResponse",
]


@pytest.mark.parametrize("schema_name", REQUIRED_SCHEMAS)
def test_schema_component_present(spec, schema_name):
    schemas = spec.get("components", {}).get("schemas", {})
    assert schema_name in schemas, \
        f"schema '{schema_name}' missing from components/schemas — datamodel-codegen needs this"


# ── Schema field coverage ────────────────────────────────────────────────────

def test_project_summary_has_required_fields(spec):
    schema = spec["components"]["schemas"]["ProjectSummary"]
    required = set(schema.get("required", []))
    assert required == {"id", "name", "createdAt", "specs"}, \
        f"ProjectSummary.required mismatch: got {required}"


def test_project_detail_has_required_fields(spec):
    schema = spec["components"]["schemas"]["ProjectDetail"]
    required = set(schema.get("required", []))
    assert required == {"id", "name", "createdAt", "specs"}, \
        f"ProjectDetail.required mismatch: got {required}"


def test_spec_detail_includes_content_field(spec):
    schema = spec["components"]["schemas"]["SpecDetail"]
    required = set(schema.get("required", []))
    assert "content" in required, \
        "SpecDetail must require 'content' — SpecSummary omits it; this is the distinguishing field"


def test_spec_summary_omits_content_field(spec):
    schema = spec["components"]["schemas"]["SpecSummary"]
    properties = schema.get("properties", {})
    assert "content" not in properties, \
        "SpecSummary must NOT have 'content' — that belongs to SpecDetail only"


def test_context_response_has_exists_field(spec):
    schema = spec["components"]["schemas"]["ContextResponse"]
    required = set(schema.get("required", []))
    assert "exists" in required, \
        "ContextResponse must require 'exists' — matches GetContextResponse DTO in flask/modules/context/dto.py"


def test_project_create_returns_201(spec):
    operation = spec["paths"]["/api/projects"]["post"]
    responses = operation.get("responses", {})
    assert "201" in responses, \
        "POST /api/projects must declare 201 response — Flask route returns 201, not 200"


def test_error_response_has_error_field(spec):
    schema = spec["components"]["schemas"]["ErrorResponse"]
    required = set(schema.get("required", []))
    assert required == {"error"}, \
        f"ErrorResponse.required must be exactly {{'error'}}, got {required}"


# ── Response references ──────────────────────────────────────────────────────

REQUIRED_RESPONSE_COMPONENTS = ["BadRequest", "NotFound", "InternalError"]


@pytest.mark.parametrize("response_name", REQUIRED_RESPONSE_COMPONENTS)
def test_response_component_present(spec, response_name):
    responses = spec.get("components", {}).get("responses", {})
    assert response_name in responses, \
        f"components/responses/{response_name} missing — referenced by route definitions"
```

---

## 6. Commit Plan

1. `chore(flask): add openapi-spec-validator to requirements.txt` — `flask/requirements.txt`: adds the CLI and Python API needed for Task 1 validation and Task 2 tooling
2. `feat(flask): write openapi.yaml — Phase 1 contract` — `flask/openapi.yaml`: 14 endpoints, 13 schema objects, 3 reusable error responses; validated with openapi-spec-validator
3. `test(flask): structural pytest suite for openapi.yaml` — `flask/tests/test_openapi_spec.py`: path coverage, method coverage, schema field assertions, spec-validator integration

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/flask

# Spec validator (gating criterion — must be zero output, exit 0)
python -m openapi_spec_validator openapi.yaml && echo "SPEC VALID"

# Full suite
python -m pytest --tb=short -q

# Count only
python -m pytest --tb=no -q 2>&1 | tail -3
```

**Expected delta**: Baseline → Baseline + 28 passing (14 parametrized method tests + 8 parametrized path tests + 13 parametrized schema tests + 8 non-parametrized unit tests = 43 new assertions, but pytest counts parametrize expansions individually — total new test *items* is approximately 43). Zero pre-existing tests broken.

If the baseline was, e.g., 42 passing, expect ≥ 85 passing after this task.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible: `git revert <sha>` — no shared state between commits in this task
- **Spec only**: `git revert <feat-commit-sha>` removes `flask/openapi.yaml` without touching `requirements.txt` or tests
- **Full task rollback**: `git revert <sha-3> <sha-2> <sha-1>` in order, or `git reset --hard <pre-task-sha>` on a feature branch [REQUIRES APPROVAL if on master]
- **Installed package**: `pip uninstall openapi-spec-validator -y` undoes the install; removing the line from `requirements.txt` prevents re-installation

---

## 9. Deviations Allowed

- **`openapi-spec-validator` version conflict** — if `>=0.5` conflicts with another dependency, try `>=0.3`; the API surface used (`validate()` and the CLI) is stable across minor versions. Log the pinned version in the commit body.
- **Test framework mismatch** — the tests above use plain pytest with no fixtures beyond `spec` (module-scoped). If the existing `conftest.py` conflicts, `test_openapi_spec.py` defines its own `spec` fixture locally (no import from conftest needed) — this is already the case in the test body above.
- **Spec validator CLI invocation** — if `python -m openapi_spec_validator` fails, try `openapi-spec-validator` (the installed script). Both are equivalent; use whichever resolves.
- **Line count** — the spec is ~220 lines, not 150–200 as the epic estimated. This is a consequence of the flat context routes vs. the parameterized pattern the epic anticipated. Do not compress the spec to hit the line budget — accuracy over brevity.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log deviation in the commit.
- **Side-effect required** (push, publish, schema migration) — STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

This task produces only the spec file and its validation suite. It does not generate DTOs, implement the mock server, or touch the Angular frontend — those are Tasks 2, 3, and 4 respectively. The spec is a static artifact; no Flask route is changed to match it (the spec was written to match the routes).

- **DTO generation (`flask/dtos/`)** — Task 2; requires the validated spec as input, runs `datamodel-codegen`; not started here even though the tool is now available
- **`mock_server.py`** — Task 3; parallel with Task 2; not started here
- **Angular base URL configuration** — Task 4; the env var swap is documented in the architecture but not executed until the mock is running
- **Changing context routes to `/api/context/{key}`** — would require modifying `flask/modules/context/routes.py`, updating Angular service calls, and re-running existing tests; this is a separate refactor decision, not a correction to be absorbed here
- **Swagger UI or spec serving** — explicitly excluded per the architecture; no `/api-docs` route, no `flask-swagger-ui` dependency
- **Auth schemes, streaming endpoints, AI routes** — Phase 2 scope; adding them to the spec now expands the contract surface before the Phase 1 frontend validation has run
- **CI/CD integration for DTO re-generation** — no pipeline consumer exists; re-scoped when Tasks 2 and 3 require repeatable builds

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale, component responsibilities
- [Epic](./epic.md) — task scope and port budget
- [Timeline](./timeline.md) — update status to "done" after `python -m openapi_spec_validator openapi.yaml` exits 0