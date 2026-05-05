# Task 4: Expose `warnings` in OpenAPI Contract

**Purpose**: Add the `warnings` array to the `GenerateTaskStatusResponse` schema in `openapi.yaml` and regenerate `dtos/models.py`, making `warnings` a first-class, stable API contract field that frontend consumers can treat as reliable rather than undocumented.

**Effort**: 0.5 days

**Dependencies**: Task 3 (truncation heuristic) logically precedes this, but the schema change is independent of whether the service populates the field; they can be merged separately.

**Parallel With**: —

**Blocks**: Angular warning badge (future epic); any frontend consumer reading `warnings` from the polling endpoint.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The task-generation polling endpoint (`GET /api/projects/{id}/generate-task/status`) returns a JSON object whose shape is governed by the `GenerateTaskStatusResponse` schema in `openapi.yaml`. Task 3 adds a truncation heuristic that writes a `warnings` list into the execution output; without this task, that field would be returned in the HTTP response but undeclared in the contract — invisible to any code-generated client, undocumented for future consumers, and excluded from the existing OpenAPI response-shape contract test. This task makes `warnings` first-class: one schema addition, one `make generate-dtos` run, and a suite of targeted tests confirm the field is present at every layer. No new route handlers are needed because the field is a backwards-compatible addition to an existing response schema.

**Trade-offs considered** (≤3 bullets):
- **`boolean` flag instead of `array`** — rejected; a boolean encodes only presence or absence, forcing a schema version bump when a second warning type appears. A list allows future heuristics to append without any breaking change.
- **Required field (always present, default `[]`)** — rejected for this task; `snapshot()` does not yet emit `warnings` (Task 3's job), so declaring it `required` would immediately break the existing response-shape contract test. Making it optional is backwards-compatible and correct: the field is absent on idle responses and will be populated by Task 3.
- **Optional `array` of strings, absent when no warnings** — preferred; matches every existing optional field in the schema (`allDone`, `filename`, `taskNum`, `taskName`, `error`), keeps existing tests green, and allows Task 3 to emit the field without any further schema change.

---

## 2. Pre-flight

Run BEFORE editing any file. Work from `{WORKSPACE}/spec-doc/api/`.

```bash
# 1. Confirm working tree is clean on the target files
git status
git diff HEAD -- openapi.yaml dtos/models.py \
    tests/test_openapi_spec.py tests/test_dtos.py

# 2. Create and switch to a feature branch (no direct push to master per repo rules)
git checkout -b feat/task4-warnings-contract

# 3. Record the baseline test count — expect 192 passing, 0 failing
make test 2>&1 | tail -5
```

**If working tree is dirty on any target file**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: 192/192 passing (per CLAUDE.md). Record the actual count you observe in the commit body if it differs.

---

## 3. Files

### To Create (new)
_None._ All changes go into existing files.

### To Modify (cite CODEBASE CONTEXT)
- `spec-doc/api/openapi.yaml` — `GenerateTaskStatusResponse` schema at lines 940–964 currently has no `warnings` property; add it as an optional `array` of `string` items.
- `spec-doc/api/dtos/models.py` — auto-generated; regenerate via `make generate-dtos` after `openapi.yaml` is updated. Never hand-edit. Commit with `git add -f dtos/models.py`.
- `spec-doc/api/tests/test_openapi_spec.py` — add one schema-field assertion function following the existing camelCase naming convention.
- `spec-doc/api/tests/test_dtos.py` — add three DTO behavioral assertion functions covering field acceptance, default absence, and list validation.

### To Leave Alone
- `spec-doc/api/modules/task_gen/routes.py` — no new route handler is needed; the field is a backwards-compatible addition to an existing response.
- `spec-doc/api/modules/task_gen/service.py` — `snapshot()` does not yet emit `warnings`; that is Task 3's scope. Do not touch.
- `spec-doc/api/modules/task_gen/tests/test_routes.py` — no changes required; existing route integration tests remain green because `warnings` is optional.
- `spec-doc/api/Makefile` — the `generate-dtos` and `check-dtos` targets are already correct; do not modify.
- `spec-doc/api/create_app.py` — blueprint registration is unaffected.

---

## 4. Implementation Steps

### Step 1: Add `warnings` property to `GenerateTaskStatusResponse` in `openapi.yaml`

**Action**: Insert the `warnings` property block immediately after the `error` property (line 964) in the `GenerateTaskStatusResponse` schema. Do not add `warnings` to the `required` list (line 942) — the field is optional.

**File**: `spec-doc/api/openapi.yaml` (CODEBASE CONTEXT — `GenerateTaskStatusResponse` schema, lines 940–964)

**Pattern**:
```yaml
    GenerateTaskStatusResponse:
      type: object
      required: [running, done]
      properties:
        running:
          type: boolean
          description: True while the background thread is in progress.
        done:
          type: boolean
          description: True once the thread has terminated (successfully or not).
        allDone:
          type: boolean
          description: Present and true when every task in the epic already has a matching guide on disk.
        filename:
          type: string
          description: Name of the task-N-*.md file that was written (only when done and not allDone).
        taskNum:
          type: string
          description: Task number from the epic table (e.g., "2").
        taskName:
          type: string
          description: Task name from the epic table.
        error:
          type: string
          description: Error message captured from the background thread.
        warnings:
          type: array
          items:
            type: string
          description: >-
            Quality-gate warnings produced after generation (e.g., likely truncation
            detected). Absent when idle or when no warnings were raised; empty list
            when generation completed cleanly.
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "
import yaml
from openapi_spec_validator import validate
spec = yaml.safe_load(open('openapi.yaml'))
validate(spec)
schema = spec['components']['schemas']['GenerateTaskStatusResponse']
assert 'warnings' in schema['properties'], 'warnings missing from schema'
assert schema['properties']['warnings']['type'] == 'array', 'warnings must be array'
assert schema['properties']['warnings']['items']['type'] == 'string', 'items must be string'
assert 'warnings' not in schema.get('required', []), 'warnings must NOT be required'
print('OK')
"
```

Expected output: `OK`

**Commit** (run before moving to Step 2):
```bash
git add openapi.yaml
git commit -m "feat(contract): add warnings array to GenerateTaskStatusResponse schema

Adds optional warnings property (array of strings) to the
GenerateTaskStatusResponse schema in openapi.yaml. Field is not
required — absent when idle or when no warnings were raised —
matching the pattern of all other optional fields in this schema.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Step 2: Regenerate `dtos/models.py`

**Action**: Run `make generate-dtos` to rebuild `dtos/models.py` from the updated `openapi.yaml`. The generator is `datamodel-codegen` with the flags already defined in the Makefile (lines 22–28 of `Makefile`). After regeneration, verify `warnings` appears on the class, then stage and commit using `git add -f` per repo rules.

**File**: `spec-doc/api/dtos/models.py` (CODEBASE CONTEXT — auto-generated, `GenerateTaskStatusResponse` class at lines 225–247 pre-change)

**Pattern** — expected shape after regeneration (do not hand-edit; verify the generator produces this):
```python
class GenerateTaskStatusResponse(BaseModel):
    running: bool = Field(
        ..., description='True while the background thread is in progress.'
    )
    done: bool = Field(
        ..., description='True once the thread has terminated (successfully or not).'
    )
    allDone: Optional[bool] = Field(
        None,
        description='Present and true when every task in the epic already has a matching guide on disk.',
    )
    filename: Optional[str] = Field(
        None,
        description='Name of the task-N-*.md file that was written (only when done and not allDone).',
    )
    taskNum: Optional[str] = Field(
        None, description='Task number from the epic table (e.g., "2").'
    )
    taskName: Optional[str] = Field(None, description='Task name from the epic table.')
    error: Optional[str] = Field(
        None, description='Error message captured from the background thread.'
    )
    warnings: Optional[List[str]] = Field(
        None,
        description='Quality-gate warnings produced after generation ...',
    )
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api

# Regenerate
make generate-dtos

# Confirm warnings field is present in the regenerated class
python -c "
from dtos.models import GenerateTaskStatusResponse
import inspect, typing

hints = typing.get_type_hints(GenerateTaskStatusResponse, include_extras=True)
assert 'warnings' in hints, f'warnings not in type hints: {list(hints)}'

# Field must be Optional (i.e., NoneType is a valid value)
obj = GenerateTaskStatusResponse(running=False, done=False)
assert obj.warnings is None, 'warnings must default to None when absent'

obj_with = GenerateTaskStatusResponse(running=True, done=False, warnings=['truncation likely'])
assert obj_with.warnings == ['truncation likely'], 'warnings must accept a list of strings'
print('OK')
"

# Confirm check-dtos passes (generated file matches schema)
make check-dtos
```

Expected: `OK` followed by a clean `make check-dtos` exit (no diff output, exit code 0).

**Commit** (run before moving to Step 3):
```bash
git add -f dtos/models.py
git commit -m "chore(dtos): regenerate models.py after warnings field addition

make generate-dtos run after openapi.yaml was updated in the
previous commit. dtos/models.py is committed per repo rules
(git add -f required). make check-dtos passes cleanly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Step 3: Add schema-level test to `test_openapi_spec.py`

**Action**: Append one test function to `spec-doc/api/tests/test_openapi_spec.py` following the existing naming convention (`camelCase_withDescription`). The function takes the module-scoped `spec` fixture and asserts the field's presence, type, and optional status.

**File**: `spec-doc/api/tests/test_openapi_spec.py` (CODEBASE CONTEXT — existing schema tests follow `spec` fixture pattern, lines 18–21)

**Pattern** — append after the last existing function in the file:
```python
def generateTaskStatusResponse_hasWarningsArrayOfStrings(spec):
    """GenerateTaskStatusResponse schema must declare warnings as an optional array of strings."""
    schema = spec['components']['schemas']['GenerateTaskStatusResponse']
    props = schema.get('properties', {})
    assert 'warnings' in props, (
        "warnings property missing from GenerateTaskStatusResponse schema. "
        "Add it to openapi.yaml components/schemas/GenerateTaskStatusResponse."
    )
    warnings_prop = props['warnings']
    assert warnings_prop.get('type') == 'array', (
        f"warnings must have type: array, got type: {warnings_prop.get('type')!r}"
    )
    items = warnings_prop.get('items', {})
    assert items.get('type') == 'string', (
        f"warnings.items must have type: string, got: {items.get('type')!r}"
    )
    required = schema.get('required', [])
    assert 'warnings' not in required, (
        "warnings must NOT appear in the required list — it is an optional field. "
        "Remove it from required[] in openapi.yaml."
    )
```

**Verify**: `cd {WORKSPACE}/spec-doc/api && python -m pytest tests/test_openapi_spec.py -v -k generateTaskStatusResponse_hasWarningsArrayOfStrings`

Expected: `1 passed`.

**Commit** (run before moving to Step 4):
```bash
git add tests/test_openapi_spec.py
git commit -m "test(contract): assert warnings field declared in openapi schema

Structural test on openapi.yaml: GenerateTaskStatusResponse must
have a warnings property of type array[string] and must NOT list
it in required[]. Catches any future accidental removal.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Step 4: Add DTO behavioral tests to `test_dtos.py`

**Action**: Append three test functions to `spec-doc/api/tests/test_dtos.py` following the existing naming convention. Cover: (a) field absent by default yields `None`; (b) field accepts a populated list; (c) field accepts an empty list.

**File**: `spec-doc/api/tests/test_dtos.py` (CODEBASE CONTEXT — existing behavioral tests at lines 91–216; append after the last function)

**Pattern** — append after the last existing function in the file:
```python
# ---------------------------------------------------------------------------
# Behavioral: GenerateTaskStatusResponse.warnings field
# ---------------------------------------------------------------------------

def generateTaskStatusResponse_warningsAbsentByDefault():
    """warnings must default to None when the key is not supplied."""
    from dtos.models import GenerateTaskStatusResponse

    status = GenerateTaskStatusResponse(running=False, done=False)
    data = status.model_dump()
    assert data.get("warnings") is None, (
        "warnings must be None (absent) when not provided — "
        "it is an optional field; got: " + repr(data.get("warnings"))
    )


def generateTaskStatusResponse_warningsAcceptsPopulatedList():
    """warnings must accept a non-empty list of strings and round-trip through model_dump."""
    from dtos.models import GenerateTaskStatusResponse

    messages = ["likely truncated: output ended mid-block", "second warning"]
    status = GenerateTaskStatusResponse(running=False, done=True, warnings=messages)
    data = status.model_dump()
    assert data["warnings"] == messages, (
        f"warnings list did not round-trip through model_dump. "
        f"Expected {messages!r}, got {data.get('warnings')!r}"
    )


def generateTaskStatusResponse_warningsAcceptsEmptyList():
    """warnings must accept an explicit empty list (generation completed with no warnings)."""
    from dtos.models import GenerateTaskStatusResponse

    status = GenerateTaskStatusResponse(running=False, done=True, warnings=[])
    data = status.model_dump()
    assert data["warnings"] == [], (
        "warnings=[] must round-trip as an empty list, not None or absent. "
        f"Got: {data.get('warnings')!r}"
    )
```

**Verify**: `cd {WORKSPACE}/spec-doc/api && python -m pytest tests/test_dtos.py -v -k warnings`

Expected: `3 passed`.

**Commit** (run before moving to Verification):
```bash
git add tests/test_dtos.py
git commit -m "test(dtos): behavioral coverage for GenerateTaskStatusResponse.warnings

Three tests: absent-by-default yields None; populated list round-trips
through model_dump; explicit empty list serialises as [] not None.
Exercises the Optional[List[str]] field shape produced by datamodel-codegen.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## 5. Tests

Complete assertion bodies, matching the repo's pytest convention (`python_functions = ["test_*", "*_*"]` per `pyproject.toml` line 5; module-scoped `spec` fixture from `test_openapi_spec.py`).

### Schema-level test — add to `spec-doc/api/tests/test_openapi_spec.py`

```python
def generateTaskStatusResponse_hasWarningsArrayOfStrings(spec):
    """GenerateTaskStatusResponse schema must declare warnings as an optional array of strings."""
    schema = spec['components']['schemas']['GenerateTaskStatusResponse']
    props = schema.get('properties', {})
    assert 'warnings' in props, (
        "warnings property missing from GenerateTaskStatusResponse schema. "
        "Add it to openapi.yaml components/schemas/GenerateTaskStatusResponse."
    )
    warnings_prop = props['warnings']
    assert warnings_prop.get('type') == 'array', (
        f"warnings must have type: array, got type: {warnings_prop.get('type')!r}"
    )
    items = warnings_prop.get('items', {})
    assert items.get('type') == 'string', (
        f"warnings.items must have type: string, got: {items.get('type')!r}"
    )
    required = schema.get('required', [])
    assert 'warnings' not in required, (
        "warnings must NOT appear in the required list — it is an optional field. "
        "Remove it from required[] in openapi.yaml."
    )
```

### DTO behavioral tests — add to `spec-doc/api/tests/test_dtos.py`

```python
# ---------------------------------------------------------------------------
# Behavioral: GenerateTaskStatusResponse.warnings field
# ---------------------------------------------------------------------------

def generateTaskStatusResponse_warningsAbsentByDefault():
    """warnings must default to None when the key is not supplied."""
    from dtos.models import GenerateTaskStatusResponse

    status = GenerateTaskStatusResponse(running=False, done=False)
    data = status.model_dump()
    assert data.get("warnings") is None, (
        "warnings must be None (absent) when not provided — "
        "it is an optional field; got: " + repr(data.get("warnings"))
    )


def generateTaskStatusResponse_warningsAcceptsPopulatedList():
    """warnings must accept a non-empty list of strings and round-trip through model_dump."""
    from dtos.models import GenerateTaskStatusResponse

    messages = ["likely truncated: output ended mid-block", "second warning"]
    status = GenerateTaskStatusResponse(running=False, done=True, warnings=messages)
    data = status.model_dump()
    assert data["warnings"] == messages, (
        f"warnings list did not round-trip through model_dump. "
        f"Expected {messages!r}, got {data.get('warnings')!r}"
    )


def generateTaskStatusResponse_warningsAcceptsEmptyList():
    """warnings must accept an explicit empty list (generation completed with no warnings)."""
    from dtos.models import GenerateTaskStatusResponse

    status = GenerateTaskStatusResponse(running=False, done=True, warnings=[])
    data = status.model_dump()
    assert data["warnings"] == [], (
        "warnings=[] must round-trip as an empty list, not None or absent. "
        f"Got: {data.get('warnings')!r}"
    )
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task.

| # | Message | After Step | Files |
|---|---------|------------|-------|
| 1 | `feat(contract): add warnings array to GenerateTaskStatusResponse schema` | Step 1 | `openapi.yaml` |
| 2 | `chore(dtos): regenerate models.py after warnings field addition` | Step 2 | `dtos/models.py` |
| 3 | `test(contract): assert warnings field declared in openapi schema` | Step 3 | `tests/test_openapi_spec.py` |
| 4 | `test(dtos): behavioral coverage for GenerateTaskStatusResponse.warnings` | Step 4 | `tests/test_dtos.py` |

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api

# Full suite
make test

# DTO sync check (CI gate — must exit 0)
make check-dtos
```

**Expected delta**: 192 → **196** passing. The four new functions match `python_functions = ["*_*"]` and are collected automatically. Zero pre-existing tests broken (the `warnings` field is optional; no existing response body changes).

---

## 8. Rollback

- **Per-step**: each step is a separate commit and is independently revertible.
  - Step 1 revert: `git revert <sha-of-commit-1>` — removes `warnings` from `openapi.yaml`
  - Step 2 revert: `git revert <sha-of-commit-2>` — restores old `dtos/models.py`; run `make check-dtos` to confirm sync.
  - Steps 3–4 revert: `git revert <sha>` independently — removes only the test additions.
- **Per-branch**: if full-suite verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch, or delete the branch (`git branch -D feat/task4-warnings-contract`) and re-open from the base. [REQUIRES APPROVAL] before force-resetting if the branch has been pushed to the remote.

---

## 9. Deviations Allowed

- **`datamodel-codegen` produces `Optional[List[str]]` vs. `list[str] | None`** — both are functionally equivalent in Pydantic v2; accept either and update the test import/assertion to match the actual generated type annotation.
- **Generator description text differs from the `openapi.yaml` description** — `datamodel-codegen` may collapse or reformat multi-line descriptions; do not hand-edit `dtos/models.py` to match the description exactly. Description content is not tested.
- **Baseline test count is not 192** — record the actual count in the Step 1 commit body as `Deviations: baseline was N, not 192`. The delta of +4 still applies.
- **Test framework mismatch** — if a future `pyproject.toml` change removes `"*_*"` from `python_functions`, prefix the new test functions with `test_` (e.g., `test_generateTaskStatusResponse_warningsAbsentByDefault`). Note the deviation in the commit body.
- **`make check-dtos` fails after regeneration** — this indicates the generator binary version differs from the one that produced the committed file. Run `make generate-dtos` a second time; if the diff is purely formatting, commit the result and note the deviation. If semantically different, stop and flag [REQUIRES APPROVAL].
- **Side-effect required** (push to remote, merge to master) → STOP, mark [REQUIRES APPROVAL].

---

## 10. Out of Scope

This task ends at the API contract layer. It declares `warnings` in the schema and confirms the generated DTO matches; it does not touch the service that populates the field or any frontend consumer that reads it. An eager executor might be tempted to wire up the field end-to-end, but that work is explicitly split across two other tasks:

- **Task 3 truncation heuristic** — `_looks_truncated` and the `warnings` annotation in `modules/task_gen/service.py` → `snapshot()`; the field remains `None` in every real response until Task 3 ships.
- **Task 3 `snapshot()` emission** — the `snapshot()` function (lines 74–101 of `modules/task_gen/service.py`) does not yet emit `warnings`; adding that emit is Task 3's final step.
- **Route-level integration test for warnings in the HTTP response** — verifying that a real status poll returns `warnings: [...]` requires the heuristic (Task 3) to be live; adding that test here would require monkeypatching the not-yet-existing heuristic, producing coupling with uncommitted code.
- **Angular warning badge** — explicitly deferred by the architecture; this is a frontend deliverable in a future epic, separate from the API contract.
- **Timeout increases** — deferred until a concrete inventory exists, per the architecture's exclusions.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, `warnings` field decisions
- [Epic](./epic.md) – Full task scope and dependency graph
- [Timeline](./timeline.md) – Update status to `done` after verification passes