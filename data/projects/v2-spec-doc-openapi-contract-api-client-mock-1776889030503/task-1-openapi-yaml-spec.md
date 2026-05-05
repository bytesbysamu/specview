Now I have everything I need. Let me write the guide.

# Implementation Guide: Task 1 — OpenAPI YAML Spec

## 1. Context

This task produces `openapi.yaml` at the `spec-doc/` repository root — the single source of truth that both the Flask implementation and the Python `ApiClient` dataclasses (Task 2) are derived from. It covers all 13 Phase 1 routes confirmed in `flask/api-contract.md`: one health check, four context GET/PUT pairs (`/api/builder`, `/api/principles`, `/api/codebase`, `/api/references`), and five project CRUD routes. Writing the spec first means any drift between Flask and the client becomes a detectable validation error rather than a runtime surprise.

**Trade-offs considered:**
- **Code-generation from existing Flask routes** — rejected because Flask routes don't exist yet (Tasks 2/3 write them); generating from nothing is circular.
- **JSON Schema only (no OpenAPI wrapper)** — rejected because the OpenAPI envelope provides operationId, server declarations, and tooling compatibility at zero extra cost; `openapi-spec-validator` can then prove the document is structurally sound.
- **Hand-written YAML (chosen)** — 13 routes is well below the ~25-route threshold where a code-gen pipeline saves more than it costs; hand-written keeps the spec readable, avoids a build step, and matches the architecture's stated preference.

---

## 2. Pre-flight

```bash
cd {WORKSPACE}/spec-doc

# 1. Confirm working tree state
git status

# 2. Confirm no openapi.yaml already exists
ls openapi.yaml 2>/dev/null && echo "EXISTS — STOP" || echo "ok: file is new"

# 3. Confirm target test file does not already exist
ls flask/tests/test_openapi_spec.py 2>/dev/null && echo "EXISTS — STOP" || echo "ok: file is new"

# 4. Baseline test suite
cd flask && python -m pytest --tb=short -q
# Record the passing count from the summary line, e.g. "47 passed"
cd ..

# 5. Check for openapi-spec-validator (optional but enables full-validation test)
python -c "import openapi_spec_validator; print(openapi_spec_validator.__version__)" 2>/dev/null \
  || echo "not installed — run: pip install openapi-spec-validator"
```

**If working tree is dirty on target files:** `git stash` or commit unrelated changes first.

**Baseline recorded:** run step 4 and note the passing count before editing anything.

---

## 3. Files

### To Create (new)
- `openapi.yaml` — the complete OpenAPI 3.0 contract; 13 routes, shared schema components, no auth/pagination/streaming
- `flask/tests/test_openapi_spec.py` — structural validation suite; asserts all 13 routes and all schema components are present; one full-validation test using `openapi-spec-validator`

### To Modify
- None — this task creates two new files only.

### To Leave Alone
- `flask/api-contract.md` — the prose contract this spec formalises; do not alter it; use it as the reference for field names and status codes
- `flask/modules/projects/routes.py`, `flask/modules/context/routes.py` — Flask implementation is not touched in this task
- `flask/tests/test_health.py`, `flask/tests/test_project.py`, `flask/tests/test_context_files.py` — existing test suites; must not regress
- `flask/modules/chain/` — chain infrastructure is irrelevant to this task

---

## 4. Implementation Steps

### Step 1: Write `openapi.yaml`

**Action:** Create `openapi.yaml` at the `spec-doc/` root. Hand-write all 13 Phase 1 routes and all shared schema components. Do not include any Phase 2 routes (AI, container, streaming) — they appear in `flask/api-contract.md` under "Phase 2 — NOT implemented in Flask Phase 1" and are explicitly out of scope.

**File:** `openapi.yaml` (new, at `spec-doc/` root)

**Full file:**
```yaml
openapi: "3.0.3"
info:
  title: Spec Doc API
  version: "1.0.0"
  description: >
    Phase 1 contract — 13 routes: health, context (×8), projects (×4).
    Auth, pagination, streaming, and AI routes are deferred to Phase 2.

servers:
  - url: http://localhost:3101
    description: Flask development server

paths:
  /health:
    get:
      operationId: getHealth
      summary: Health check
      tags: [health]
      responses:
        "200":
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/HealthStatus"

  /api/builder:
    get:
      operationId: getBuilder
      summary: Read builder profile context file
      tags: [context]
      responses:
        "200":
          description: Builder profile content and existence flag
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextFileResponse"
    put:
      operationId: putBuilder
      summary: Write builder profile context file
      tags: [context]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextFileRequest"
      responses:
        "200":
          description: Content written
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem write failed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /api/principles:
    get:
      operationId: getPrinciples
      summary: Read principles context file
      tags: [context]
      responses:
        "200":
          description: Principles content and existence flag
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextFileResponse"
    put:
      operationId: putPrinciples
      summary: Write principles context file
      tags: [context]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextFileRequest"
      responses:
        "200":
          description: Content written
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem write failed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /api/codebase:
    get:
      operationId: getCodebase
      summary: Read codebase context file
      tags: [context]
      responses:
        "200":
          description: Codebase content and existence flag
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextFileResponse"
    put:
      operationId: putCodebase
      summary: Write codebase context file
      tags: [context]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextFileRequest"
      responses:
        "200":
          description: Content written
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem write failed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /api/references:
    get:
      operationId: getReferences
      summary: Read references context file
      tags: [context]
      responses:
        "200":
          description: References content and existence flag
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextFileResponse"
    put:
      operationId: putReferences
      summary: Write references context file
      tags: [context]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextFileRequest"
      responses:
        "200":
          description: Content written
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          description: content field missing or not a string
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem write failed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /api/projects:
    get:
      operationId: listProjects
      summary: List all projects sorted newest-first
      tags: [projects]
      responses:
        "200":
          description: Array of project summaries ordered by createdAt descending
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/ProjectSummary"
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
    post:
      operationId: createProject
      summary: Create a new project with initial spec files
      tags: [projects]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateProjectRequest"
      responses:
        "201":
          description: Project created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/CreateProjectResponse"
        "400":
          description: name or files missing, or files is not an array
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /api/projects/{id}:
    parameters:
      - name: id
        in: path
        required: true
        description: Project directory name (slug-timestamp format)
        schema:
          type: string
    get:
      operationId: getProject
      summary: Get project with full spec file contents
      tags: [projects]
      responses:
        "200":
          description: Project detail including full spec file contents
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProjectDetail"
        "404":
          description: Project directory or project.json not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
    delete:
      operationId: deleteProject
      summary: Delete a project and all its files recursively
      tags: [projects]
      responses:
        "200":
          description: Project deleted
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "404":
          description: Project directory not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /api/projects/{id}/files/{filename}:
    parameters:
      - name: id
        in: path
        required: true
        description: Project directory name (slug-timestamp format)
        schema:
          type: string
      - name: filename
        in: path
        required: true
        description: Target filename within the project directory (e.g. epic.md)
        schema:
          type: string
    put:
      operationId: updateProjectFile
      summary: Write or overwrite a file within a project
      tags: [projects]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/UpdateFileRequest"
      responses:
        "200":
          description: File written
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "404":
          description: Project directory not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "500":
          description: Filesystem error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

components:
  schemas:
    HealthStatus:
      type: object
      required: [status]
      properties:
        status:
          type: string
          enum: [ok]

    ContextFileResponse:
      type: object
      required: [content, exists]
      properties:
        content:
          type: string
          description: Raw file content; empty string when file does not exist
        exists:
          type: boolean
          description: "True when content is non-empty (content.length > 0)"

    ContextFileRequest:
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
          description: Human-readable error message; Angular frontend checks this key

    SpecFileSummary:
      type: object
      required: [filename, label]
      properties:
        filename:
          type: string
          description: Markdown filename (e.g. epic.md)
        label:
          type: string
          description: >
            Display label derived from filename: strip .md, replace hyphens with
            spaces, title-case each word

    SpecFileDetail:
      allOf:
        - $ref: "#/components/schemas/SpecFileSummary"
        - type: object
          required: [content]
          properties:
            content:
              type: string
              description: Full UTF-8 content of the file

    ProjectSummary:
      type: object
      required: [id, name, createdAt, specs]
      properties:
        id:
          type: string
          description: Directory name under projects/ (slug-timestamp)
        name:
          type: string
        createdAt:
          type: string
          format: date-time
          description: ISO-8601 UTC timestamp written to project.json at creation
        specs:
          type: array
          items:
            $ref: "#/components/schemas/SpecFileSummary"
          description: All .md files in the project directory; no content field

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
            $ref: "#/components/schemas/SpecFileDetail"
          description: All .md files with full content populated

    FileInput:
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
            $ref: "#/components/schemas/FileInput"

    CreateProjectResponse:
      type: object
      required: [id, name, createdAt]
      properties:
        id:
          type: string
          description: Generated project ID (slug-timestamp)
        name:
          type: string
        createdAt:
          type: string
          format: date-time

    UpdateFileRequest:
      type: object
      required: [content]
      properties:
        content:
          type: string
```

**Verify:**
```bash
# Must print a dict (not an error):
python3 -c "import yaml; d = yaml.safe_load(open('openapi.yaml')); print('paths:', list(d['paths'].keys()))"

# Must show exactly 13:
python3 -c "
import yaml
d = yaml.safe_load(open('openapi.yaml'))
count = sum(len([m for m in ops if m in ('get','post','put','delete','patch')]) for ops in d['paths'].values())
print(f'route count: {count}')
"
# expect: route count: 13
```

---

### Step 2: Write the validation test suite

**Action:** Create `flask/tests/test_openapi_spec.py`. This is a pure structural test — no Flask `client` fixture needed. It validates YAML parse, route coverage, schema coverage, and key status codes. The final test calls `openapi-spec-validator` and skips gracefully if the package is absent.

**File:** `flask/tests/test_openapi_spec.py` (new)

**Full file:**
```python
"""Structural validation for openapi.yaml — 13 Phase 1 routes.

Run from flask/:
    pytest tests/test_openapi_spec.py -v

Full spec validation requires:
    pip install openapi-spec-validator
"""
import pathlib
import yaml
import pytest

# openapi.yaml is at spec-doc/openapi.yaml
# __file__ resolves to flask/tests/test_openapi_spec.py
# parents[2] = spec-doc/
SPEC_PATH = pathlib.Path(__file__).resolve().parents[2] / "openapi.yaml"

_REQUIRED_ROUTES = [
    ("/health",                             "get"),
    ("/api/builder",                        "get"),
    ("/api/builder",                        "put"),
    ("/api/principles",                     "get"),
    ("/api/principles",                     "put"),
    ("/api/codebase",                       "get"),
    ("/api/codebase",                       "put"),
    ("/api/references",                     "get"),
    ("/api/references",                     "put"),
    ("/api/projects",                       "get"),
    ("/api/projects",                       "post"),
    ("/api/projects/{id}",                  "get"),
    ("/api/projects/{id}",                  "delete"),
    ("/api/projects/{id}/files/{filename}", "put"),
]

_REQUIRED_SCHEMAS = [
    "HealthStatus",
    "ContextFileResponse",
    "ContextFileRequest",
    "SuccessResponse",
    "ErrorResponse",
    "SpecFileSummary",
    "SpecFileDetail",
    "ProjectSummary",
    "ProjectDetail",
    "FileInput",
    "CreateProjectRequest",
    "CreateProjectResponse",
    "UpdateFileRequest",
]


@pytest.fixture(scope="module")
def spec():
    assert SPEC_PATH.exists(), f"openapi.yaml not found at {SPEC_PATH}"
    return yaml.safe_load(SPEC_PATH.read_text())


def test_spec_file_exists():
    assert SPEC_PATH.exists(), \
        f"openapi.yaml missing — expected at {SPEC_PATH}"


def test_spec_is_openapi_30(spec):
    version = spec.get("openapi", "")
    assert version.startswith("3.0"), \
        f"expected OpenAPI 3.0.x, got {version!r}"


def test_spec_has_info_block(spec):
    info = spec.get("info", {})
    assert "title" in info, "spec.info must have a title"
    assert "version" in info, "spec.info must have a version"


def test_all_13_routes_declared(spec):
    paths = spec.get("paths", {})
    missing = [
        f"{method.upper()} {path}"
        for path, method in _REQUIRED_ROUTES
        if path not in paths or method not in paths[path]
    ]
    assert missing == [], \
        f"Missing route declarations in openapi.yaml: {missing}"


def test_route_count_is_exactly_13(spec):
    paths = spec.get("paths", {})
    count = sum(
        len([m for m in ops if m in ("get", "post", "put", "delete", "patch")])
        for ops in paths.values()
    )
    assert count == 13, (
        f"Expected exactly 13 route+method pairs, found {count}. "
        "Phase 2 AI/container routes must not appear in this spec."
    )


def test_required_schemas_declared(spec):
    schemas = spec.get("components", {}).get("schemas", {})
    missing = [s for s in _REQUIRED_SCHEMAS if s not in schemas]
    assert missing == [], \
        f"Missing schema components: {missing}"


def test_health_returns_200(spec):
    responses = spec["paths"]["/health"]["get"]["responses"]
    assert "200" in responses, \
        "GET /health must declare a 200 response"


def test_create_project_uses_201_not_200(spec):
    responses = spec["paths"]["/api/projects"]["post"]["responses"]
    assert "201" in responses, \
        "POST /api/projects must declare 201 Created (per api-contract.md)"
    assert "200" not in responses, \
        "POST /api/projects must not declare 200 — the contract specifies 201"


def test_context_puts_declare_400(spec):
    context_keys = ("builder", "principles", "codebase", "references")
    offenders = [
        f"/api/{k}"
        for k in context_keys
        if "400" not in spec["paths"][f"/api/{k}"]["put"]["responses"]
    ]
    assert offenders == [], \
        f"Context PUT routes missing 400 declaration (required by api-contract.md): {offenders}"


def test_project_detail_and_list_use_different_spec_schemas(spec):
    schemas = spec["components"]["schemas"]
    summary_props = set(schemas["ProjectSummary"]["properties"].get("specs", {})
                        .get("items", {}).get("$ref", "SpecFileSummary").split("/"))
    detail_props = set(schemas["ProjectDetail"]["properties"].get("specs", {})
                       .get("items", {}).get("$ref", "SpecFileDetail").split("/"))
    assert summary_props != detail_props, \
        "ProjectSummary.specs and ProjectDetail.specs must reference different schemas " \
        "(SpecFileSummary vs SpecFileDetail — content field only in detail)"


def test_project_routes_declare_404(spec):
    routes = [
        ("/api/projects/{id}",                  "get"),
        ("/api/projects/{id}",                  "delete"),
        ("/api/projects/{id}/files/{filename}", "put"),
    ]
    offenders = [
        f"{m.upper()} {p}"
        for p, m in routes
        if "404" not in spec["paths"][p][m]["responses"]
    ]
    assert offenders == [], \
        f"Routes missing 404 response declaration (per api-contract.md): {offenders}"


def test_openapi_spec_is_valid():
    """Full OpenAPI 3.0 validation. Requires: pip install openapi-spec-validator"""
    osv = pytest.importorskip(
        "openapi_spec_validator",
        reason="pip install openapi-spec-validator to enable full spec validation",
    )
    spec_dict = yaml.safe_load(SPEC_PATH.read_text())
    # validate_spec() raises OpenAPISpecValidatorError on failure; silent on success
    osv.validate_spec(spec_dict)
```

**Verify:**
```bash
cd flask
python -m pytest tests/test_openapi_spec.py -v
# Expect: 12 passed (test_openapi_spec_is_valid skips if package absent, or passes if installed)
```

---

## 5. Tests

Framework: pytest, plain `def test_*` functions, no class wrappers — matches `flask/tests/test_health.py` (lines 1–29) and `flask/tests/test_project.py` conventions.

The full test file is given verbatim in Step 2. Complete assertion bodies for all 12 tests are reproduced below for reference:

```python
def test_spec_file_exists():
    assert SPEC_PATH.exists(), \
        f"openapi.yaml missing — expected at {SPEC_PATH}"

def test_spec_is_openapi_30(spec):
    version = spec.get("openapi", "")
    assert version.startswith("3.0"), \
        f"expected OpenAPI 3.0.x, got {version!r}"

def test_spec_has_info_block(spec):
    info = spec.get("info", {})
    assert "title" in info, "spec.info must have a title"
    assert "version" in info, "spec.info must have a version"

def test_all_13_routes_declared(spec):
    paths = spec.get("paths", {})
    missing = [
        f"{method.upper()} {path}"
        for path, method in _REQUIRED_ROUTES
        if path not in paths or method not in paths[path]
    ]
    assert missing == [], \
        f"Missing route declarations in openapi.yaml: {missing}"

def test_route_count_is_exactly_13(spec):
    paths = spec.get("paths", {})
    count = sum(
        len([m for m in ops if m in ("get", "post", "put", "delete", "patch")])
        for ops in paths.values()
    )
    assert count == 13, (
        f"Expected exactly 13 route+method pairs, found {count}."
    )

def test_required_schemas_declared(spec):
    schemas = spec.get("components", {}).get("schemas", {})
    missing = [s for s in _REQUIRED_SCHEMAS if s not in schemas]
    assert missing == [], f"Missing schema components: {missing}"

def test_health_returns_200(spec):
    responses = spec["paths"]["/health"]["get"]["responses"]
    assert "200" in responses, "GET /health must declare a 200 response"

def test_create_project_uses_201_not_200(spec):
    responses = spec["paths"]["/api/projects"]["post"]["responses"]
    assert "201" in responses, "POST /api/projects must declare 201 Created"
    assert "200" not in responses, "POST /api/projects must not declare 200"

def test_context_puts_declare_400(spec):
    offenders = [
        f"/api/{k}"
        for k in ("builder", "principles", "codebase", "references")
        if "400" not in spec["paths"][f"/api/{k}"]["put"]["responses"]
    ]
    assert offenders == [], f"Context PUT routes missing 400: {offenders}"

def test_project_detail_and_list_use_different_spec_schemas(spec):
    schemas = spec["components"]["schemas"]
    summary_ref = schemas["ProjectSummary"]["properties"]["specs"]["items"].get("$ref", "")
    detail_ref   = schemas["ProjectDetail"]["properties"]["specs"]["items"].get("$ref", "")
    assert summary_ref != detail_ref, \
        "ProjectSummary and ProjectDetail must reference different spec-item schemas"

def test_project_routes_declare_404(spec):
    routes = [
        ("/api/projects/{id}",                  "get"),
        ("/api/projects/{id}",                  "delete"),
        ("/api/projects/{id}/files/{filename}", "put"),
    ]
    offenders = [f"{m.upper()} {p}" for p, m in routes
                 if "404" not in spec["paths"][p][m]["responses"]]
    assert offenders == [], f"Routes missing 404: {offenders}"

def test_openapi_spec_is_valid():
    osv = pytest.importorskip("openapi_spec_validator",
                               reason="pip install openapi-spec-validator")
    osv.validate_spec(yaml.safe_load(SPEC_PATH.read_text()))
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(api): add openapi.yaml — 13 Phase 1 routes` — `openapi.yaml`: health check, four context GET/PUT pairs, five project CRUD routes, all schema components; no Phase 2 routes included
2. `test(api): validate openapi.yaml structure and route coverage` — `flask/tests/test_openapi_spec.py`: 12-test suite asserting YAML parse, all 13 routes, all schema components, key status codes (201, 400, 404)

**Deviation logging:** if any step deviates, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/flask
python -m pytest --tb=short -q
```

**Expected delta:** baseline N → N+12 passing. Zero pre-existing tests broken.

If `openapi-spec-validator` is installed, `test_openapi_spec_is_valid` counts as a passing test (not a skip). If absent it shows as `1 skipped` — that is acceptable; the other 11 tests fully cover structural correctness.

---

## 8. Rollback

- **Per-step:** each commit is independently revertible:
  ```bash
  git revert <sha>   # reverts a single commit cleanly
  ```
- **Per-branch:** if verification fails and the branch is the right scope:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destroys local commits
  ```
  Or simply delete the feature branch if working on one.

The two new files (`openapi.yaml`, `flask/tests/test_openapi_spec.py`) have no side effects on running code — reverting them leaves the Flask server and all other tests unaffected.

---

## 9. Deviations Allowed

- **`SpecFileDetail` uses `allOf` vs explicit properties** — either approach is valid YAML; use whichever passes `openapi-spec-validator`. If `allOf` causes validator issues (some versions complain about `required` inside `allOf`), rewrite as an explicit object with all three properties declared directly.
- **`test_project_detail_and_list_use_different_spec_schemas` fails** — if the `$ref` resolution path in the test doesn't match the actual YAML structure after schema changes, adjust the accessor chain to traverse the actual YAML structure; the semantic intent (summary schema ≠ detail schema) must still be asserted.
- **`openapi-spec-validator` API mismatch** — the `validate_spec()` function name is stable through version 0.6.x. If the installed version uses a different entrypoint (e.g. `OpenAPIV30SpecValidator(d).validate()`), adapt the call in `test_openapi_spec_is_valid` and log in the commit body.
- **Phase 2 route accidentally included** — `test_route_count_is_exactly_13` will fail; remove the extra route and recommit.

---

## 10. Out of Scope

This task writes the contract document and proves it is structurally sound. It does not write any Python client code, Flask routes, or mock implementations. An eager executor might reasonably start on the `ApiClient` dataclasses while the spec is fresh — that work belongs to Task 2 and must not be absorbed here.

- **`flask/client/client.py`** — Task 2; blocked on this spec being complete first
- **`flask/client/mock_client.py`** — Task 3; blocked on Task 2
- **`flask/client/flask_client.py`** — Task 4; blocked on Tasks 2 and 3
- **Auth schemes (`securitySchemes`)** — Phase 2; not referenced by any Phase 1 route handler
- **Pagination parameters (`limit`, `offset`, `cursor`)** — Phase 2; `GET /api/projects` returns all projects in Phase 1
- **Streaming response types (`text/event-stream`)** — Phase 2; not in the 13-route scope
- **`openapi-spec-validator` added to `requirements.txt`** — optional tooling dependency; the test skips gracefully without it; adding it to requirements is a separate decision for the executor to flag rather than absorb silently

**Rule for the executor:** if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, component boundaries, adapter pattern
- [Epic](./epic.md) — Task scope and port budget
- [API Contract](flask/api-contract.md) — Authoritative route/field reference for this spec
- [Timeline](./timeline.md) — Update status to ✅ after verification passes