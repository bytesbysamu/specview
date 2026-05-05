# 🛠️ Task 2: OpenAPI spec + DTOs

**Purpose**: Create the `server/openapi/waitlist.yaml` OpenAPI specification and generate (or hand-author) Pydantic v2 DTOs in `server/modules/waitlist/dto.py`, establishing the single source of truth for request/response shapes used by Task 3's routes and any future frontend codegen.

**Effort**: 30m

**Dependencies**: None (runs independently of Task 1 — the DTOs don't import the SQLAlchemy model)

**Parallel With**: Task 1 (Model + migration)

**Blocks**: Task 3 (routes import DTOs for request parsing and response serialization)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task creates the contract layer for the waitlist endpoint. An OpenAPI YAML spec defines the exact shape of `POST /api/waitlist/signup` — request body, three response codes (201, 409, 422), and their schemas. From this spec, Pydantic v2 models are generated (via `datamodel-codegen`) or hand-authored to match. The DTOs live in `server/modules/waitlist/dto.py` and will be imported by Task 3's `routes.py` for request parsing and response serialization. This follows the architecture principle "OpenAPI-First with Generated DTOs" — one YAML is the source of truth, both sides generate from it.

The OpenAPI spec in the architecture doc omits `required` arrays on `SignupResponse`, which would cause `datamodel-codegen` to generate all fields as `Optional`. This task adds the `required` arrays so the generated code matches the intended contract: all four response fields are always present.

**Trade-offs considered**:
- **`datamodel-codegen` vs hand-authored DTOs**: Architecture says "generate from OpenAPI." Epic says "if `datamodel-codegen` is not installed, hand-author." This guide provides both paths — Step 3a tries generation, Step 3b is the fallback. The hand-authored version is pinned to the YAML spec so drift is detectable.
- **Inline request schema vs `$ref` component**: The request has exactly one field (`email`). A `$ref` component for a single-field object adds indirection with zero reuse benefit. The request schema stays inline; only `SignupResponse` and `ErrorResponse` are `$ref`'d components because they appear in multiple response blocks and will be consumed by codegen.
- **`EmailStr` vs plain `str` for email field**: `EmailStr` (from `pydantic[email]`) provides free format validation but adds a dependency (`email-validator`). The hand-authored fallback uses `EmailStr` if available, `str` otherwise. The generated path uses whatever `datamodel-codegen` emits for `format: email`. Either way, server-side email validation also exists in Task 3's service layer — the DTO validation is defense-in-depth, not the only gate.

---

## 2. Pre-flight

Run BEFORE editing any file.

```bash
git status                                                 # flag unrelated M/?? entries; stash if dirty
git log -1 --format=%H                                     # record pre-task SHA (needed for §8 rollback)
git diff HEAD -- server/ 2>&1 | head -50                   # confirm target area clean

# Discover current state
ls server/openapi/ 2>/dev/null || echo "openapi/ does not exist yet — will create"
ls server/modules/waitlist/ 2>/dev/null || echo "waitlist module does not exist yet — Task 1 may not have run"
ls server/modules/user/dto.py 2>/dev/null && head -30 server/modules/user/dto.py   # inspect existing DTO pattern

# Check datamodel-codegen availability
pip show datamodel-code-generator 2>&1 | head -5           # if installed, note version
which datamodel-codegen 2>&1                               # confirm binary on PATH

# Check pydantic version
python -c "import pydantic; print(pydantic.__version__)" 2>&1   # expect 2.x

# Check email-validator availability (needed for EmailStr)
python -c "import email_validator; print(email_validator.__version__)" 2>&1

# Baseline test count
cd server && pytest -q 2>&1 | tail -3                     # record backend "N passed"
```

**If working tree is dirty on any target path**: stash or commit unrelated changes on a separate branch BEFORE starting.

**Baseline recorded**: capture backend count `[N_b]` — goes into commit bodies.

---

## 3. Files

### To Create (new)
- `server/openapi/waitlist.yaml` (new) — OpenAPI 3.0.3 spec defining `POST /api/waitlist/signup` with request body, 201/409/422 responses, and `SignupResponse`/`ErrorResponse` component schemas.
- `server/modules/waitlist/dto.py` (new) — Pydantic v2 models: `SignupRequest`, `SignupResponse`, `ErrorResponse`. Generated from the YAML or hand-authored to match.
- `server/tests/test_waitlist_dto.py` (new) — 6 tests covering request validation, response serialization, and error shape.

### To Modify
- None — this task only creates new files.

### To Leave Alone
- `server/modules/waitlist/models.py` — Task 1 deliverable (SQLAlchemy model). DTOs do not import the model.
- `server/modules/waitlist/__init__.py` — Task 1 deliverable. Do not modify.
- `server/modules/waitlist/routes.py` — Task 3. Do not create.
- `server/modules/waitlist/service.py` — Task 3. Do not create.
- `server/modules/waitlist/repository.py` — Task 3. Do not create.
- `server/app.py` — Task 4. Do not modify.
- `server/modules/photoshoot/**` — unrelated feature module.
- `server/modules/user/**` — unrelated feature module (but inspect `user/dto.py` in Pre-flight for pattern reference).
- Any existing migration file — never edit past migrations.
- All frontend files (`src/app/**`) — no frontend changes in this task.

---

## 4. Implementation Steps

### Step 1: Create the `server/openapi/` directory

**Action**: Create the directory if it doesn't exist. This is the canonical location for all OpenAPI specs per the architecture principle "OpenAPI-First with Generated DTOs."

**File**: `server/openapi/` (new directory)

**Pattern**: `mkdir -p server/openapi`

**Verify**: `ls server/openapi/` — expect empty directory, no errors.

### Step 2: Create the OpenAPI spec

**Action**: Write `server/openapi/waitlist.yaml` defining the waitlist signup endpoint. This follows the architecture doc's spec (architecture.md §Component Design > OpenAPI Spec) with two corrections: (a) add `required` arrays to `SignupResponse` so codegen doesn't emit `Optional` fields, (b) add `example` values for documentation.

**File**: `server/openapi/waitlist.yaml` (new)

**Pattern**:
```yaml
openapi: 3.0.3
info:
  title: Waitlist Module
  version: 1.0.0
  description: Email signup capture for landing page and ported subscribers.
paths:
  /api/waitlist/signup:
    post:
      operationId: createWaitlistSignup
      summary: Register email for waitlist
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
              properties:
                email:
                  type: string
                  format: email
                  example: "user@example.com"
      responses:
        "201":
          description: Signup created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SignupResponse"
        "409":
          description: Email already registered
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "422":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
components:
  schemas:
    SignupResponse:
      type: object
      required:
        - id
        - email
        - source
        - created_at
      properties:
        id:
          type: integer
          example: 1
        email:
          type: string
          format: email
          example: "user@example.com"
        source:
          type: string
          example: "landing_page"
        created_at:
          type: string
          format: date-time
          example: "2026-04-17T12:00:00Z"
    ErrorResponse:
      type: object
      required:
        - error
      properties:
        error:
          type: string
          example: "Email already registered"
```

**Verify**:
```bash
python -c "import yaml; yaml.safe_load(open('server/openapi/waitlist.yaml')); print('YAML valid')"
# expect: "YAML valid"
```

If `pyyaml` is not available, fall back to:
```bash
python -c "
import json, subprocess
result = subprocess.run(['python', '-c', 'import yaml'], capture_output=True)
if result.returncode != 0:
    # No pyyaml — just check the file exists and is non-empty
    with open('server/openapi/waitlist.yaml') as f:
        content = f.read()
    assert len(content) > 100, 'YAML file too small'
    assert 'openapi: 3.0.3' in content
    print('YAML file exists and looks correct')
"
```

### Step 3a: Generate DTOs via `datamodel-codegen` (primary path)

**Action**: Run `datamodel-codegen` against the YAML spec to produce Pydantic v2 models. This is the preferred path per the architecture principle.

**File**: `server/modules/waitlist/dto.py` (new, generated)

**Pattern**:
```bash
datamodel-codegen \
  --input server/openapi/waitlist.yaml \
  --output server/modules/waitlist/dto.py \
  --output-model-type pydantic_v2 \
  --target-python-version 3.11
```

**Verify**:
```bash
cd server && python -c "
from modules.waitlist.dto import SignupResponse, ErrorResponse
print('SignupResponse fields:', list(SignupResponse.model_fields.keys()))
print('ErrorResponse fields:', list(ErrorResponse.model_fields.keys()))
"
# expect: SignupResponse fields: ['id', 'email', 'source', 'created_at']
# expect: ErrorResponse fields: ['error']
```

**If `datamodel-codegen` is not installed or the output is incorrect**: proceed to Step 3b.

### Step 3b: Hand-author DTOs (fallback path)

**Action**: If `datamodel-codegen` is unavailable or produces incorrect output, hand-author the Pydantic models to match the YAML spec exactly. Follow the pattern in `modules/user/dto.py` (discovered in Pre-flight). If `modules/user/dto.py` does not exist, follow the pattern below.

**File**: `server/modules/waitlist/dto.py` (new)

**Pattern**:
```python
"""Waitlist DTOs — generated from server/openapi/waitlist.yaml.

If regenerating:
    datamodel-codegen --input server/openapi/waitlist.yaml \
      --output server/modules/waitlist/dto.py \
      --output-model-type pydantic_v2
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

try:
    from pydantic import EmailStr
except ImportError:
    # email-validator not installed — fall back to plain str
    EmailStr = str  # type: ignore[misc,assignment]


class SignupRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr


class SignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    source: str
    created_at: datetime


class ErrorResponse(BaseModel):
    error: str
```

Key decisions in this fallback:
- `SignupRequest` is hand-added (not in the YAML `components/schemas` because the request schema is inline) — Task 3 needs it for request parsing.
- `from_attributes=True` on `SignupResponse` enables `SignupResponse.model_validate(sqlalchemy_instance)` in Task 3.
- `strict=True` on `SignupRequest` rejects non-string email values at the Pydantic layer.

**Verify**:
```bash
cd server && python -c "
from modules.waitlist.dto import SignupRequest, SignupResponse, ErrorResponse
# Validate SignupRequest
req = SignupRequest(email='test@example.com')
print(f'SignupRequest: {req.email}')

# Validate SignupResponse
from datetime import datetime, timezone
resp = SignupResponse(id=1, email='test@example.com', source='landing_page', created_at=datetime.now(timezone.utc))
print(f'SignupResponse fields: {list(resp.model_fields.keys())}')

# Validate ErrorResponse
err = ErrorResponse(error='Email already registered')
print(f'ErrorResponse: {err.error}')
print('All DTOs valid')
"
# expect: All DTOs valid
```

### Step 4: Verify generated DTOs match YAML spec

**Action**: Regardless of whether Step 3a or 3b was used, verify the DTOs match the spec. Check field names, types, and required-ness.

**File**: read-only (no edits).

**Pattern**:
```bash
cd server && python -c "
from modules.waitlist.dto import SignupResponse, ErrorResponse

# All SignupResponse fields must be required (not Optional)
for name, field in SignupResponse.model_fields.items():
    assert field.is_required(), f'{name} should be required, not Optional'
    print(f'  {name}: required=True ✓')

# ErrorResponse.error must be required
assert ErrorResponse.model_fields['error'].is_required(), 'error field must be required'
print('  error: required=True ✓')
print('All fields match YAML spec')
"
```

**Verify**: all fields print `required=True ✓`. If any field is `Optional` after Step 3a (codegen), the YAML `required` array is wrong — go back and fix the YAML, then regenerate.

### Step 5: Add SignupRequest if codegen omitted it

**Action**: `datamodel-codegen` generates models from `components/schemas` only — it will not generate `SignupRequest` because the request body schema is inline (not a `$ref`). If Step 3a was used and `SignupRequest` is missing, add it manually to `dto.py`.

**File**: `server/modules/waitlist/dto.py` (modify if needed)

**Pattern**: Check and add if missing:
```bash
cd server && python -c "from modules.waitlist.dto import SignupRequest" 2>&1
# If ImportError: add SignupRequest class to dto.py
```

If missing, append to `dto.py`:
```python
class SignupRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
```

Ensure the necessary imports (`EmailStr`, `ConfigDict`) are present at the top of the file. If `datamodel-codegen` already imported `BaseModel` and `ConfigDict`, only add `EmailStr` (with the try/except fallback).

**Verify**:
```bash
cd server && python -c "
from modules.waitlist.dto import SignupRequest
req = SignupRequest(email='hello@example.com')
assert req.email == 'hello@example.com'
print('SignupRequest importable and functional')
"
```

### Step 6: Write DTO tests

**Action**: Create `server/tests/test_waitlist_dto.py` with assertions for validation, serialization, and error shapes. Match the existing pytest convention: class-wrapped tests, `condition_expectedOutcome` names, no "should".

**File**: `server/tests/test_waitlist_dto.py` (new)

**Pattern**: see §5 for full assertion bodies.

**Verify**:
```bash
cd server && pytest tests/test_waitlist_dto.py -q
# expect: 6 tests passing
```

### Step 7: Run full backend suite

**Action**: Execute the complete pytest suite to confirm zero regressions.

**Verify**:
```bash
cd server && pytest -q
# expect: N_b + 6 passing, 0 failures introduced
```

---

## 5. Tests

Pytest with Pydantic model validation. No database fixtures needed — DTOs are pure data classes. Tests are wrapped in a class to avoid the `python_functions = ["*_*"]` caveat. Names follow the repo's `condition_expectedOutcome` convention.

```python
# server/tests/test_waitlist_dto.py
"""Tests for waitlist Pydantic DTOs."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from modules.waitlist.dto import SignupRequest, SignupResponse, ErrorResponse


class TestSignupRequest:

    def test_validEmail_parsesSuccessfully(self):
        req = SignupRequest(email="user@example.com")
        assert req.email == "user@example.com"

    def test_missingEmail_raisesValidationError(self):
        with pytest.raises(ValidationError) as exc_info:
            SignupRequest()
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "email" in field_names, "email is required"

    def test_emptyStringEmail_raisesValidationError(self):
        with pytest.raises(ValidationError):
            SignupRequest(email="")


class TestSignupResponse:

    def test_allFieldsPresent_serializesToDict(self):
        now = datetime.now(timezone.utc)
        resp = SignupResponse(id=42, email="test@example.com", source="landing_page", created_at=now)
        data = resp.model_dump()
        assert data["id"] == 42
        assert data["email"] == "test@example.com"
        assert data["source"] == "landing_page"
        assert data["created_at"] == now

    def test_fromAttributes_populatesFromObject(self):
        """Simulates SignupResponse.model_validate(sqlalchemy_row) — the pattern Task 3 will use."""

        class FakeRow:
            id = 7
            email = "row@example.com"
            source = "trendfy"
            created_at = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)

        resp = SignupResponse.model_validate(FakeRow(), from_attributes=True)
        assert resp.id == 7
        assert resp.email == "row@example.com"
        assert resp.source == "trendfy"


class TestErrorResponse:

    def test_errorMessage_serializesToDict(self):
        err = ErrorResponse(error="Email already registered")
        data = err.model_dump()
        assert data == {"error": "Email already registered"}
```

---

## 6. Commit Plan

Two commits — one for the spec + DTOs, one for tests.

1. `feat(waitlist): add OpenAPI spec and Pydantic DTOs` — `server/openapi/waitlist.yaml`, `server/modules/waitlist/dto.py`: OpenAPI 3.0.3 spec for `POST /api/waitlist/signup` with 201/409/422 responses. Pydantic v2 DTOs: `SignupRequest`, `SignupResponse` (with `from_attributes=True`), `ErrorResponse`. [Generated via `datamodel-codegen` | Hand-authored — note which path was taken.]
2. `test(waitlist): cover DTO validation, serialization, and from_attributes` — `server/tests/test_waitlist_dto.py`: 6 tests covering valid/invalid email parsing, missing field rejection, response serialization, from_attributes round-trip, and error shape.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with:
```
Deviations:
- <one line per deviation>
```

---

## 7. Verification

```bash
cd server && pytest -q
```

**Expected delta**: backend `N_b → N_b + 6` passing (6 DTO tests). Zero pre-existing tests broken. No frontend changes — frontend count unchanged.

Additionally, verify the YAML spec is well-formed:
```bash
python -c "import yaml; d = yaml.safe_load(open('server/openapi/waitlist.yaml')); assert 'paths' in d; assert 'components' in d; print('spec OK')"
```

---

## 8. Rollback

- **Per-step** (each commit is independently revertible):
  ```bash
  git revert <sha-of-commit-2>            # drop tests
  git revert <sha-of-commit-1>            # drop spec + DTOs
  ```
- **Per-branch** (if verification fails catastrophically):
  ```bash
  git reset --hard <pre-task-sha>          # [REQUIRES APPROVAL — discards all task work]
  ```
  Or delete the feature branch if one was created: `git branch -D <branch>` (local only, safe).

---

## 9. Deviations Allowed

- **`datamodel-codegen` not installed** → use Step 3b (hand-authored DTOs); log in commit 1 body under `Deviations:`.
- **`datamodel-codegen` generates `Optional` fields** → the YAML `required` arrays are wrong; fix the YAML, regenerate. If regeneration still fails, fall back to Step 3b.
- **`datamodel-codegen` does not generate `SignupRequest`** → expected behavior (inline schema, not a `$ref`). Step 5 handles this — add it manually, log under `Deviations:`.
- **`datamodel-codegen` generates extra imports or classes** → keep what matches the spec, delete the rest. Log under `Deviations:`.
- **`email-validator` not installed** → `EmailStr` import fails. The try/except fallback in Step 3b handles this. If using codegen and it emits `EmailStr`, install `email-validator` or replace with `str`. Log under `Deviations:`.
- **`modules/user/dto.py` uses a different pattern** (e.g., `model_config` dict syntax vs class attribute) → match the existing pattern for consistency; log under `Deviations:`.
- **`pyyaml` not installed** → YAML validation in Step 2 verify uses the fallback check (file exists, correct header). Log under `Deviations:`.
- **Pydantic v1 instead of v2** → this changes the entire DTO surface (`BaseModel` methods, `Config` class vs `model_config`). STOP and flag — the architecture requires Pydantic v2.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log under `Deviations:`.
- **Side effect required** (pushing, publishing, schema changes, `rm -rf`) → STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task creates only the OpenAPI spec and DTOs. It does NOT create routes, services, or any runtime endpoint. The DTOs are passive data containers — they validate and serialize, nothing more. Task 3 is responsible for wiring them into Flask.

- **Routes (`server/modules/waitlist/routes.py`)** — Task 3. Do not create any Blueprint or endpoint.
- **Service layer (`server/modules/waitlist/service.py`)** — Task 3. Do not create business logic.
- **Repository (`server/modules/waitlist/repository.py`)** — Task 3. Do not create data-access code.
- **Module registration in `ENABLED_MODULES`** — Task 4. Do not modify `server/app.py`.
- **Rate limiting** — Task 3 (routes layer). No rate-limit logic in DTOs.
- **TypeScript DTO generation** (`npx openapi-typescript`) — deferred until a frontend consumes the waitlist endpoint. No Angular/TypeScript work in this task.
- **OpenAPI spec validation tooling** (e.g., `spectral`, `swagger-cli`) — nice-to-have but not required for a single-endpoint spec. Add when the `server/openapi/` directory has 3+ specs.
- **Model + migration (`server/modules/waitlist/models.py`)** — Task 1. Do not create or modify the SQLAlchemy model. DTOs import from `pydantic`, not from `models.py`.
- **Trendfy data migration** — Task 5. Do not reference `bubls_subscribers`.
- **Frontend changes** — no Angular, Ionic, or Capacitor work in this task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — OpenAPI spec design and DTO generation commands.
- [Epic](./epic.md) — Task scope and dependency graph.
- [Timeline](./timeline.md) — Mark `In Progress` at Step 1, `Done` after commit 2 merges.

---

##### Post-generation review (auto)

**Overall**: 5/5 (gold)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 5/5 | All required sections for a task-spec are present: Purpose, Context, Pre-flight, Files, Implementation Steps, Tests, Commit Plan, Verification, Rollback, Deviations Allowed, Out of Scope, Related Documents |
| Content routing | 5/5 | No violations detected — status tracking correctly deferred to Timeline ('mark In Progress at Step 1, Done after commit 2 merges'), trade-offs in §1 are implementation-level decisions appropriate for a task spec (codegen vs hand-auth, inline vs $ref, EmailStr vs str), code blocks are the correct medium for an implementation guide |
| Pattern application | 4/5 | Trade-offs in §1 Context are discussed in prose paragraphs rather than a Decision Justification Table with columns (Option / Pros / Cons / Verdict) — three trade-offs would read faster as a table |
| Rule compliance | 5/5 | No violations — status directed to Timeline only, doc has single responsibility (contract layer creation), 'Solution Architecture' naming used correctly in Related Documents, Out of Scope enforces blast-radius discipline with explicit stop-and-flag rule |
| Content quality | 5/5 | Exceptionally opinionated: makes clear calls on inline-vs-$ref, EmailStr fallback, strict=True on request, from_attributes=True on response — each with reasoning |
| Usefulness | 5/5 | No gaps — a developer or Claude Code executor could follow this verbatim: pre-flight checks establish baseline, exact file contents are provided, verification commands confirm each step, rollback is granular per-commit, and the 6-test suite is copy-pasteable with clear expected output |

**Top fixes**:
- Convert the three trade-offs in §1 Context into a Decision Justification Table (Option | Pros | Cons | Verdict) for faster scanning — the prose is thorough but table format matches the methodology's prescribed pattern
- Verify bidirectional cross-references: confirm architecture.md and epic.md link back to this task spec (or to a task index that includes it)
- Minor: the spec is ~400 lines for a 30m task — consider whether the dual-path (3a/3b) could be collapsed with a single 'prefer codegen, fall back to hand-authored' instruction block to reduce executor cognitive load
