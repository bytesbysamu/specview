# Task 2: OpenAPI + DTO Update

**Purpose**: Extend the `generateFromImage` request contract with `mode` (enum) and `custom_style` (string) fields, then regenerate both TypeScript types and Pydantic DTOs from the updated YAML — no hand-editing of generated files.

**Effort**: 0.5 day

**Dependencies**: None — the existing `server/openapi/photoshoot.yaml` with the `POST /photoshoot/generate-from-image` endpoint was established by the bubls2 epic (task-3). This task extends that schema.

**Parallel With**: Task 1 (Prompt config module) — no dependency in either direction.

**Blocks**: Task 3 (Backend mode resolution — needs the regenerated `dto.py` with mode fields) and Task 4 (Frontend mode picker — needs the regenerated `photoshoot.api.d.ts` with mode types).

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The current `photoshoot.yaml` defines `POST /photoshoot/generate-from-image` with a `multipart/form-data` body containing a single `image` field. This task adds two properties to that request schema: `mode` — a string enum (`portrait`, `outfit`, `custom`) defaulting to `portrait` — and `custom_style` — an optional string (max 500 chars) that carries the user's freeform style prompt when `mode=custom`. After editing the YAML, both downstream type files are regenerated: `src/app/models/photoshoot.api.d.ts` via `npx openapi-typescript` and `server/modules/photoshoot/dto.py` via `datamodel-codegen`. The generated files are never hand-edited — if the output is wrong, the YAML is wrong. This follows the architecture principle "OpenAPI-first with Generated DTOs" and the prior art established by the waitlist module's task-2 guide.

**Trade-offs considered**:
- **Inline `mode`/`custom_style` vs separate `$ref` component** — rejected separate component because the request schema is already inline and has exactly 3 fields. A `$ref` adds indirection with zero reuse benefit at this scale.
- **`default: portrait` in YAML vs default in application code** — chose YAML-level default so the contract is self-documenting and codegen tools emit the default. Backend still applies `portrait` as fallback (defense-in-depth), but the spec is the authority.
- **Conditional required (`custom_style` required when `mode=custom`)** — OpenAPI 3.0.3 cannot express conditional requirements. `custom_style` is marked optional in the spec; the conditional validation lives in `routes.py` (Task 3). This is the standard pattern — the spec defines the shape, the route enforces business rules.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                                      # Flag any unrelated M/?? entries
git diff HEAD -- server/openapi/photoshoot.yaml src/app/models/photoshoot.api.d.ts server/modules/photoshoot/dto.py
git log -1 --format='%H %s'                                                     # Record pre-task SHA for rollback

# Baseline tests
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -5              # Record frontend pass count
(cd server && pytest -q 2>&1 | tail -3)                                         # Record backend pass count

# Confirm existing YAML is parseable
python -c "import yaml; yaml.safe_load(open('server/openapi/photoshoot.yaml')); print('YAML valid')"

# Confirm codegen tools are available
which npx && npx openapi-typescript --version 2>&1 | head -1
which datamodel-codegen && datamodel-codegen --version 2>&1 | head -1
pip show datamodel-code-generator 2>&1 | head -3

# Confirm pydantic version
python -c "import pydantic; print(f'pydantic {pydantic.__version__}')"          # Expect 2.x
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: `F` frontend specs passing, `B` backend tests passing.

---

## 3. Files

### To Create (new)
- None — this task only modifies existing files and runs codegen.

### To Modify (cite CODEBASE CONTEXT)
- `server/openapi/photoshoot.yaml` — current state: `generateFromImage` request has `image` field only → target state: add `mode` (string enum, default `portrait`) and `custom_style` (string, optional, maxLength 500) to the request body properties.
- `src/app/models/photoshoot.api.d.ts` — regenerated via `npx openapi-typescript`; current state: types for `image`-only request → target state: types include `mode` and `custom_style` fields. **Do not hand-edit.**
- `server/modules/photoshoot/dto.py` — regenerated via `datamodel-codegen`; current state: Pydantic models for `image`-only request → target state: models include `mode` and `custom_style` fields. **Do not hand-edit.**

### To Leave Alone
- `server/modules/photoshoot/routes.py` — Task 3 wires mode extraction from the request. Do not modify.
- `server/modules/photoshoot/service.py` — Task 3 adds `resolve_prompt` call. Do not modify.
- `server/modules/photoshoot/prompts.py` — Task 1 deliverable. Do not create or modify.
- `src/app/pages/photoshoot/photoshoot.page.ts` — Task 4 adds the mode picker. Do not modify.
- `src/app/services/photoshoot-api.service.ts` — Task 4 adds mode to the FormData payload. Do not modify.
- `server/modules/photoshoot/models.py` — no schema change; `mode` is not persisted (the resolved prompt is already stored in `superapp_generations.prompt`).
- All migration files — no database changes in this task.

---

## 4. Implementation Steps

### Step 1: Read the current YAML to understand existing structure

**Action**: Inspect `server/openapi/photoshoot.yaml` to identify the exact location where `mode` and `custom_style` properties must be added — under `paths > /photoshoot/generate-from-image > post > requestBody > content > multipart/form-data > schema > properties`.

**File**: `server/openapi/photoshoot.yaml` (read-only in this step)

**Pattern**: Locate the `generateFromImage` request body schema. It should look like:
```yaml
requestBody:
  required: true
  content:
    multipart/form-data:
      schema:
        type: object
        required: [image]
        properties:
          image: { type: string, format: binary }
```

**Verify**: `cat server/openapi/photoshoot.yaml` — confirm the `properties` block under `generateFromImage` contains only `image`. Note the exact indentation level for Step 2.

### Step 2: Add `mode` and `custom_style` to the YAML request schema

**Action**: Add two properties to the `generateFromImage` request body schema. `mode` is a string enum with a default; `custom_style` is an optional string with a max length. Do NOT add either field to the `required` array — `mode` has a default (so omitting it is valid) and `custom_style` is only conditionally required (enforced by routes, not the spec).

**File**: `server/openapi/photoshoot.yaml`

**Pattern** — add these two properties alongside the existing `image` property:
```yaml
                mode:
                  type: string
                  enum:
                    - portrait
                    - outfit
                    - custom
                  default: portrait
                  description: Generation style mode
                custom_style:
                  type: string
                  maxLength: 500
                  description: User-written style prompt. Required when mode is custom.
```

The resulting `properties` block should contain exactly three keys: `image`, `mode`, `custom_style`. The `required` array stays as `[image]` — `mode` has a default and `custom_style` is conditionally required (business rule, not schema rule).

**Verify**:
```bash
python -c "
import yaml
with open('server/openapi/photoshoot.yaml') as f:
    spec = yaml.safe_load(f)

# Navigate to the generateFromImage request schema
paths = spec['paths']
op = paths['/photoshoot/generate-from-image']['post']
schema = op['requestBody']['content']['multipart/form-data']['schema']
props = schema['properties']

# Verify all three properties exist
assert 'image' in props, 'missing image property'
assert 'mode' in props, 'missing mode property'
assert 'custom_style' in props, 'missing custom_style property'

# Verify mode enum values
assert props['mode']['enum'] == ['portrait', 'outfit', 'custom'], f'wrong enum: {props[\"mode\"][\"enum\"]}'
assert props['mode']['default'] == 'portrait', 'mode default must be portrait'

# Verify custom_style constraints
assert props['custom_style']['maxLength'] == 500, 'custom_style maxLength must be 500'

# Verify required array unchanged
assert schema.get('required') == ['image'], f'required should be [image], got {schema.get(\"required\")}'

print('YAML schema valid — 3 properties, correct enum, correct default, correct maxLength')
"
```

### Step 3: Regenerate TypeScript types

**Action**: Run `openapi-typescript` against the updated YAML to regenerate the TypeScript type definitions. This follows the architecture principle (principles.md line 76): `npx openapi-typescript server/openapi/{module}.yaml -o src/app/models/{module}.api.d.ts`.

**File**: `src/app/models/photoshoot.api.d.ts` (regenerated, not hand-edited)

**Pattern**:
```bash
npx openapi-typescript server/openapi/photoshoot.yaml -o src/app/models/photoshoot.api.d.ts
```

**Verify**:
```bash
grep -q "mode" src/app/models/photoshoot.api.d.ts && echo "mode field present in TS types" || echo "FAIL: mode missing"
grep -q "custom_style" src/app/models/photoshoot.api.d.ts && echo "custom_style field present in TS types" || echo "FAIL: custom_style missing"
grep -q "portrait" src/app/models/photoshoot.api.d.ts && echo "portrait enum value present" || echo "FAIL: portrait missing"
```

Additionally, verify the TS types compile:
```bash
npx tsc --noEmit src/app/models/photoshoot.api.d.ts 2>&1 | head -5
```

### Step 4: Regenerate Pydantic DTOs

**Action**: Run `datamodel-codegen` against the updated YAML to regenerate the Pydantic v2 models. This follows the architecture principle (principles.md line 79): `datamodel-codegen --input server/openapi/{module}.yaml --output server/modules/{module}/dto.py --output-model-type pydantic_v2`.

**File**: `server/modules/photoshoot/dto.py` (regenerated, not hand-edited)

**Pattern**:
```bash
datamodel-codegen \
  --input server/openapi/photoshoot.yaml \
  --output server/modules/photoshoot/dto.py \
  --output-model-type pydantic_v2 \
  --target-python-version 3.11
```

**Verify**:
```bash
cd server && python -c "
from modules.photoshoot.dto import *
import inspect

# Find the request model class that contains 'mode'
# datamodel-codegen may name it differently depending on YAML structure
members = {name: cls for name, cls in inspect.getmembers(
    __import__('modules.photoshoot.dto', fromlist=['*']),
    predicate=inspect.isclass
)}
print(f'Generated classes: {list(members.keys())}')

# Check at least one class has mode and custom_style fields
found_mode = False
for name, cls in members.items():
    if hasattr(cls, 'model_fields'):
        fields = list(cls.model_fields.keys())
        if 'mode' in fields:
            found_mode = True
            print(f'{name} has fields: {fields}')
            assert 'custom_style' in fields, f'{name} missing custom_style'
            print(f'{name}: mode + custom_style present')
            break

assert found_mode, 'No generated class contains mode field — check YAML structure'
print('Pydantic DTOs valid')
"
```

**If `datamodel-codegen` is not installed**: install it first with `pip install datamodel-code-generator` and retry. If installation fails, STOP and flag — do NOT hand-edit `dto.py`. The architecture principle is "no hand-editing of generated files." The prior waitlist task-2 guide allowed a hand-authored fallback, but this task's epic explicitly states "No hand-editing of generated files."

### Step 5: Verify generated files match the YAML contract

**Action**: Cross-check that the generated TS types and Pydantic models both reflect the three enum values (`portrait`, `outfit`, `custom`), the default (`portrait`), and the `maxLength` constraint (500) on `custom_style`. This catches codegen tools that silently drop constraints.

**File**: read-only (no edits)

**Pattern**:
```bash
# TS types: verify enum values are present
grep "portrait" src/app/models/photoshoot.api.d.ts
grep "outfit" src/app/models/photoshoot.api.d.ts
grep "custom" src/app/models/photoshoot.api.d.ts

# Python DTOs: verify enum values and constraints
cd server && python -c "
from modules.photoshoot.dto import *
import inspect

# Find the enum class for mode
for name, obj in inspect.getmembers(
    __import__('modules.photoshoot.dto', fromlist=['*'])
):
    if inspect.isclass(obj) and issubclass(obj, str) and hasattr(obj, '__members__'):
        # It's a string enum
        members = list(obj.__members__.keys()) if hasattr(obj, '__members__') else []
        print(f'Enum {name}: {members}')

print('Cross-check complete')
"
```

**Verify**: All three enum values appear in both generated files. If any are missing, the YAML is malformed — go back to Step 2.

### Step 6: Run existing test suites to confirm no regressions

**Action**: Run both frontend and backend test suites. The YAML change and regenerated types should not break any existing tests — the new fields are optional (mode has a default, custom_style is not required).

**File**: no edits

**Pattern**:
```bash
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -10
(cd server && pytest -q 2>&1 | tail -5)
```

**Verify**: Same pass counts as Pre-flight baseline (`F` frontend, `B` backend). Zero new failures. If a test breaks, the regenerated types changed an existing type shape — inspect the diff in the generated file and adjust the YAML if needed.

---

## 5. Tests

No new tests in this task. The YAML is validated by the verify commands in Steps 2 and 5. The generated files are validated by the import checks in Steps 3–5. The regenerated types do not change behavior — they add optional fields to existing contracts.

Task 5 (Integration test + TestFlight QA) covers end-to-end validation of the mode field flowing through the full pipeline. Task 3 covers backend extraction of mode from the request. Task 4 covers frontend sending of mode in the FormData.

Testing the YAML spec structure itself is covered inline by the Step 2 verify command, which asserts:
- All three properties exist (`image`, `mode`, `custom_style`)
- Enum values are exactly `[portrait, outfit, custom]`
- Default is `portrait`
- `maxLength` is 500
- `required` array is unchanged (`[image]` only)

---

## 6. Commit Plan

One commit — the YAML change and both regenerated files are a single logical unit. Splitting them would leave the repo in an inconsistent state (YAML says one thing, generated types say another).

1. `feat(photoshoot): add mode and custom_style to OpenAPI contract` — `server/openapi/photoshoot.yaml`, `src/app/models/photoshoot.api.d.ts`, `server/modules/photoshoot/dto.py`: Add `mode` (enum: portrait/outfit/custom, default portrait) and `custom_style` (string, maxLength 500) to the `generateFromImage` request body. TS types regenerated via `openapi-typescript`, Pydantic DTOs regenerated via `datamodel-codegen`.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with:
```
Deviations:
- <one line per deviation>
```

---

## 7. Verification

```bash
# YAML is valid and has the right shape
python -c "
import yaml
spec = yaml.safe_load(open('server/openapi/photoshoot.yaml'))
props = spec['paths']['/photoshoot/generate-from-image']['post']['requestBody']['content']['multipart/form-data']['schema']['properties']
assert set(props.keys()) >= {'image', 'mode', 'custom_style'}
print('YAML: OK')
"

# TS types compile and contain mode
grep -c "mode" src/app/models/photoshoot.api.d.ts

# Python DTOs importable and contain mode
cd server && python -c "from modules.photoshoot import dto; print('DTO import: OK')"

# Full test suites
npm test -- --watch=false --browsers=ChromeHeadless
(cd server && pytest -q)
```

**Expected delta**: `F → F` frontend, `B → B` backend. Zero new tests (testing deferred to Tasks 3–5). Zero regressions — new fields are optional/defaulted.

---

## 8. Rollback

- **Per-step**: the single commit is independently revertible.
  ```bash
  git revert <sha-of-commit-1>
  ```
  After reverting, regenerate the types to restore the pre-task state:
  ```bash
  npx openapi-typescript server/openapi/photoshoot.yaml -o src/app/models/photoshoot.api.d.ts
  datamodel-codegen --input server/openapi/photoshoot.yaml --output server/modules/photoshoot/dto.py --output-model-type pydantic_v2
  ```
- **Per-branch**: if verification fails catastrophically:
  ```bash
  git reset --hard <pre-task-sha>    # [REQUIRES APPROVAL — discards all task work]
  ```
  Or delete the feature branch if one was created: `git branch -D <branch>` (local only, safe).

---

## 9. Deviations Allowed

- **`datamodel-codegen` not installed** → install via `pip install datamodel-code-generator` and retry. If installation fails (e.g., system pip restrictions), STOP and flag. Do NOT hand-edit `dto.py` — the epic explicitly prohibits hand-editing generated files.
- **`openapi-typescript` not installed** → install via `npm install -D openapi-typescript` and retry. If it's already a devDependency, `npx` will find it.
- **`datamodel-codegen` generates unexpected class names** → the class names depend on YAML structure (inline vs `$ref`). Accept whatever names codegen produces — Task 3's routes will import by the generated name. Note the mapping in the commit body under `Deviations:`.
- **`datamodel-codegen` generates `Optional[str]` for `mode` instead of an enum class** → acceptable. The enum constraint is in the YAML; Pydantic will validate against the `Literal` or `Enum` type that codegen emits. If codegen emits plain `str`, the validation moves to the route layer (Task 3). Note under `Deviations:`.
- **`pyyaml` not installed** → use the file-existence check fallback (verify the YAML file is well-formed by attempting codegen directly — codegen tools parse YAML internally). Note under `Deviations:`.
- **Existing `photoshoot.yaml` structure differs from the expected layout** → read the actual file structure, locate the `generateFromImage` operation's request body schema, and add the two fields at the correct indentation level. The property definitions are the same regardless of where in the YAML tree they go. Note structural differences under `Deviations:`.
- **Generated TS file uses different syntax than expected** (e.g., `openapi-typescript` v7 uses `components["schemas"]` paths vs v6 interfaces) → accept the output as-is. Task 4 will adapt imports to whatever the codegen produced. Note the version under `Deviations:`.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log under `Deviations:`.

---

## 10. Out of Scope

This task modifies only the OpenAPI contract and regenerates types. It does NOT wire the new fields into any runtime code path. The `mode` and `custom_style` fields exist in the YAML and generated types after this task, but no backend route reads them and no frontend component sends them — that's Tasks 3 and 4 respectively.

- **Route-level validation of `mode=custom` + empty `custom_style`** — Task 3. The 422 response for this case is already defined in the YAML, but the enforcement logic belongs in `routes.py`.
- **Service-level `resolve_prompt` call** — Task 3. The service does not change in this task.
- **Frontend `ion-segment` mode picker** — Task 4. No Angular components are modified.
- **Frontend `FormData.append('mode', ...)` call** — Task 4. The API service is not modified.
- **Integration tests for mode-aware generation** — Task 5. End-to-end coverage is deferred.
- **`npm run gen:all` script creation** — if no such script exists in `package.json`, run the two codegen commands individually. Creating a convenience script is nice-to-have but not in scope.
- **`custom_style` content moderation** — explicitly excluded by the epic. TestFlight-only audience of 15 known testers.
- **Additional modes beyond portrait/outfit/custom** — the enum is fixed at 3 values. New modes require a new YAML edit + regen cycle.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for OpenAPI-first DTOs and the mode enum
- [Epic](./epic.md) – Task scope, dependency graph, success criteria
- [Timeline](./timeline.md) – Update status after commit merges
- [Waitlist Task 2](../waitlist-module-1776444761500/task-2-openapi-spec-dtos.v2.md) – Prior art for OpenAPI + DTO generation pattern