I now have full context on the prior tasks and the exact file shapes. Let me generate the implementation guide.

# Task 3: Extend DTOs and Service Layer

**Purpose**: Plumb the `meta` sidecar field from the runner's `ChainRunResult` through the Pydantic DTO and service layer to the API response, and update the frontend interface to accept it without type errors.

**Effort**: 0.25 day

**Dependencies**: Task 2 (Add `meta` field to `ChainRunResult`) must be merged — the runner must already accumulate sidecar results into `ChainRunResult.meta`.

**Parallel With**: —

**Blocks**: Task 4 (Unit + regression tests — needs the full plumbing in place to test end-to-end)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 2 added a `meta: dict[str, str] | None` field to `ChainRunResult` and taught the runner to accumulate sidecar `outputKey` step results there instead of forwarding them through the pipeline. But the data stops at the runner's return value — `chain_service.py` doesn't forward `meta` to the response dict, `chain_dto.py`'s `ChainResponse` doesn't declare the field, and the frontend `ChainResponse` interface in `chain.mock.ts` doesn't accept it. This task closes the gap across all three layers so that `braindump-to-docs` responses include `{ files: [...], meta: { "lint": "...", "score": "..." } }` and `deep-humanize` responses omit `meta` entirely (backward-compatible). Three files, three one-line additions, zero new modules.

**Trade-offs considered**:
- **Add `meta` to OpenAPI YAML and regenerate DTOs** — rejected because the chain DTOs were hand-authored in Task 2 (text-chains), not generated from OpenAPI. Regenerating would overwrite hand-tuned aliases and validation. OpenAPI sync deferred to a future codegen-alignment pass.
- **Parse sidecar JSON values into typed objects in the DTO layer** — rejected because the runner deliberately stores raw strings (per architecture: "no JSON parsing in the runner"). The frontend (or a future presenter) decides how to interpret sidecar values. Keeping `dict[str, str]` preserves this boundary.
- **Single `meta` field on the DTO (chosen)** — preferred because it mirrors the dataclass shape 1:1, adds zero new types, and serializes cleanly with Pydantic's `exclude_none` behavior. Backward-compatible: existing consumers that don't read `meta` are unaffected.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}
git status                                                    # Flag any unrelated M/?? entries
git diff HEAD -- server/modules/text/chain_dto.py \
                 server/modules/text/chain_service.py \
                 src/app/mocks/chain.mock.ts                  # Confirm target files are clean
cd server && python -m pytest --tb=short -q 2>&1 | tail -5   # Record baseline pass count
cd {WORKSPACE} && npx tsc --noEmit 2>&1 | tail -5            # Record baseline TS errors
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**If Task 2 is not merged**: STOP — `ChainRunResult.meta` must exist before this task can plumb it. Verify:
```bash
cd {WORKSPACE}/server
python -c "from modules.chain.definition_runner import ChainRunResult; assert hasattr(ChainRunResult, '__dataclass_fields__') and 'meta' in ChainRunResult.__dataclass_fields__, 'Task 2 not merged: ChainRunResult missing meta field'; print('OK: ChainRunResult.meta exists')"
```

**Baseline recorded**: `[N]/[N] passing` (pytest), `[M] errors` or `0 errors` (tsc).

---

## 3. Files

### To Create
- (none)

### To Modify
- `server/modules/text/chain_dto.py` — add `meta: dict[str, str] | None = None` to `ChainResponse` (currently has `generation_id`, `result`, `files` per text-chains Task 2)
- `server/modules/text/chain_service.py` — add conditional `meta` forwarding in `execute_chain()` after the existing `files`/`result` branch (currently builds response dict without `meta`)
- `src/app/mocks/chain.mock.ts` — add `meta?: Record<string, string>` to `ChainResponse` interface; add sample `meta` to `MOCK_CHAIN_MULTI` constant

### To Leave Alone
- `server/modules/chain/definition_runner.py` — Task 2 already added `meta` to `ChainRunResult` and the runner accumulation logic; no changes needed here
- `server/modules/chain/adapter.py` — adapter boundary intact; this is a DTO/service-layer change only
- `server/modules/text/chain_routes.py` — routes call `chain_service.execute_chain()` and `jsonify()` the result; the dict shape change flows through automatically
- `server/modules/text/chain_dto.py`'s `ChainRequest` and `ChainErrorResponse` classes — unaffected; only `ChainResponse` changes
- `src/app/services/text-api.service.ts` — the service imports `ChainResponse` from `chain.mock.ts` (or declares its own). If it declares its own copy, the mock update handles the mock-mode path; the service-level type may need a separate sync (check and log as deviation if so)

---

## 4. Implementation Steps

### Step 1: Add `meta` field to `ChainResponse` DTO

**Action**: Add one field to the `ChainResponse` Pydantic model in the DTO file. Place it after `files` to maintain field order consistency with `ChainRunResult`.

**File**: `server/modules/text/chain_dto.py`

**Pattern**:

Read the file first. Locate the `ChainResponse` class. It currently looks like (per text-chains Task 2):

```python
class ChainResponse(BaseModel):
    generation_id: str = Field(..., alias="generationId")
    result: str | None = None
    files: list[ChainFileOutput] | None = None

    model_config = {"populate_by_name": True, "by_alias": True}
```

Add `meta` after `files`:

```python
class ChainResponse(BaseModel):
    generation_id: str = Field(..., alias="generationId")
    result: str | None = None
    files: list[ChainFileOutput] | None = None
    meta: dict[str, str] | None = None

    model_config = {"populate_by_name": True, "by_alias": True}
```

**Verify**:
```bash
cd {WORKSPACE}/server
python -c "
from modules.text.chain_dto import ChainResponse

# With meta
resp = ChainResponse(generation_id='abc', meta={'lint': '{\"issues\": []}', 'score': '{\"scores\": {}}'})
d = resp.model_dump(by_alias=True, exclude_none=True)
assert 'meta' in d, f'meta missing from serialized output: {d}'
assert d['meta']['lint'] == '{\"issues\": []}', f'meta.lint wrong: {d[\"meta\"]}'
print(f'With meta: {d}')

# Without meta (backward compat)
resp2 = ChainResponse(generation_id='def', result='text')
d2 = resp2.model_dump(by_alias=True, exclude_none=True)
assert 'meta' not in d2, f'meta should be excluded when None: {d2}'
print(f'Without meta: {d2}')

print('OK')
"
```

Expected: `meta` present when set, absent when `None` (with `exclude_none=True`).

---

### Step 2: Forward `meta` in chain service

**Action**: Add conditional `meta` forwarding in the `execute_chain()` function, after the existing `files`/`result` branch.

**File**: `server/modules/text/chain_service.py`

**Pattern**:

Read the file first. Locate the response-building block in `execute_chain()`. It currently looks like (per text-chains Task 2):

```python
    response: dict = {"generationId": str(row.id)}
    if run_result.files is not None:
        response["files"] = run_result.files
    else:
        response["result"] = run_result.result
    return response
```

Add `meta` forwarding before the `return`:

```python
    response: dict = {"generationId": str(row.id)}
    if run_result.files is not None:
        response["files"] = run_result.files
    else:
        response["result"] = run_result.result
    if run_result.meta:
        response["meta"] = run_result.meta
    return response
```

The truthy check (`if run_result.meta`) handles both `None` (no sidecar steps) and `{}` (empty dict, shouldn't happen but defensive). Only chains with actual sidecar data get `meta` in the response.

**Verify**:
```bash
cd {WORKSPACE}/server
python -c "
from modules.text.chain_service import execute_chain
print('import OK — meta forwarding added')
"
```

Functional verification deferred to Task 4 (requires DB session and mock provider).

---

### Step 3: Add `meta` to frontend `ChainResponse` interface and mock data

**Action**: Add `meta` as an optional property on the `ChainResponse` TypeScript interface. Update `MOCK_CHAIN_MULTI` to include sample sidecar data for mock-mode testing.

**File**: `src/app/mocks/chain.mock.ts`

**Pattern**:

Read the file first. The interface currently looks like (per text-chains Task 6):

```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
}
```

Add `meta`:

```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
  meta?: Record<string, string>;
}
```

Update `MOCK_CHAIN_MULTI` to include sample meta (matching the `braindump-to-docs` sidecar shape):

```typescript
export const MOCK_CHAIN_MULTI: ChainResponse = {
  generationId: '00000000-0000-0000-0000-000000000011',
  files: [
    { name: 'analysis.md', content: '# Analysis\n\nProblem: the braindump needs structure.' },
    { name: 'epic.md', content: '# Epic\n\nScope: three tasks, two weeks.' },
    { name: 'architecture.md', content: '# Architecture\n\nFlask + Angular + Neon.' },
  ],
  meta: { lint: '{"issues": []}', score: '{"scores": {"structure": 0.9}}' },
};
```

`MOCK_CHAIN_SINGLE` is left unchanged — deep-humanize has no sidecar steps, so no `meta`.

**Verify**:
```bash
cd {WORKSPACE}
npx tsc --noEmit 2>&1 | tail -5
```

Expected: zero new type errors. If `ChainResponse` is also declared in `src/app/services/text-api.service.ts`, that copy needs the same `meta` addition — check and handle as deviation if so.

**Secondary check** — verify the interface is consumed without errors:
```bash
cd {WORKSPACE}
grep -rn "ChainResponse" src/app/ --include="*.ts" | head -10
```

If `ChainResponse` is imported from `chain.mock.ts` in other files, the type change propagates automatically. If it's redeclared elsewhere, update that copy too and log as deviation.

---

## 5. Tests

### Backend: `server/modules/text/tests/test_chain_dto.py` (new or extend existing)

Match the repo's existing test framework (pytest, per `server/modules/chain/tests/test_definition_runner.py`).

```python
"""Tests for ChainResponse meta field serialization."""
from __future__ import annotations

from modules.text.chain_dto import ChainResponse


def test_chainResponse_withMeta_serializesMetaField():
    resp = ChainResponse(
        generation_id="abc-123",
        files=[{"name": "analysis.md", "content": "# Analysis"}],
        meta={"lint": '{"issues": []}', "score": '{"scores": {"structure": 0.9}}'},
    )
    d = resp.model_dump(by_alias=True, exclude_none=True)
    assert d["generationId"] == "abc-123"
    assert d["meta"] == {"lint": '{"issues": []}', "score": '{"scores": {"structure": 0.9}}'}
    assert "files" in d


def test_chainResponse_withoutMeta_omitsMetaFromSerialization():
    resp = ChainResponse(generation_id="def-456", result="humanized text")
    d = resp.model_dump(by_alias=True, exclude_none=True)
    assert "meta" not in d, f"meta should be excluded when None, got: {d}"
    assert d["result"] == "humanized text"


def test_chainResponse_emptyMeta_serializesAsEmptyDict():
    resp = ChainResponse(generation_id="ghi-789", result="text", meta={})
    d = resp.model_dump(by_alias=True, exclude_none=True)
    assert d["meta"] == {}, "Empty meta dict should serialize (truthy in Pydantic, excluded only when None)"
```

### Frontend: type-check verification

No Jasmine/Karma test file needed for this change — the mock data and interface update are verified by `tsc --noEmit`. The mock constants serve as type-level assertions: if `MOCK_CHAIN_MULTI.meta` doesn't match `Record<string, string>`, TypeScript rejects it.

---

## 6. Commit Plan

One commit for this task (three files, one logical unit):

1. `feat(text): plumb meta sidecar field through DTO + service + frontend interface` — `server/modules/text/chain_dto.py`, `server/modules/text/chain_service.py`, `src/app/mocks/chain.mock.ts`, `server/modules/text/tests/test_chain_dto.py`: add optional `meta: dict[str, str]` to ChainResponse DTO, forward from ChainRunResult in service, update frontend interface and mock data, add serialization tests.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/server
python -m pytest --tb=short -q 2>&1 | tail -10
```

```bash
cd {WORKSPACE}
npx tsc --noEmit 2>&1 | tail -5
```

**Expected delta**: `[N] → [N+3] passing` (3 new DTO serialization tests). Zero pre-existing tests broken. Zero new TypeScript errors.

---

## 8. Rollback

- **Per-step**: single commit — `git revert <sha>` removes all three file changes atomically.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (the sha recorded in Pre-flight) or delete the feature branch.

---

## 9. Deviations Allowed

- **`ChainResponse` interface declared in `text-api.service.ts` instead of (or in addition to) `chain.mock.ts`** — if the interface exists in the service file, update that copy too and log in commit body. The mock file's interface is the canonical source for mock-mode; the service file's is the canonical source for real-mode. Both must have `meta`.
- **`chain_dto.py` has different field order or additional fields** — preserve existing order; insert `meta` after `files`. Log any field-order deviation.
- **`chain_service.py` uses `response = ChainResponse(...)` instead of a raw dict** — if the service constructs the response via the Pydantic model (not a dict), the `meta` field is already available via the DTO change in Step 1; just pass `meta=run_result.meta` to the constructor. Log as deviation.
- **Test file location differs** — if `server/modules/text/tests/` doesn't exist, create it with `__init__.py`. If DTO tests live elsewhere (e.g., `server/tests/test_chain_dto.py`), follow the existing convention. Log location in commit.
- **Side-effect required** (push, publish, migration) — STOP, mark `[REQUIRES APPROVAL]` and ask. This task should not need any.

---

## 10. Out of Scope

This task plumbs the `meta` field from runner to API response. It does NOT render, parse, or act on sidecar data.

- **UI rendering of `meta` (collapsible panels, badge tabs)** — separate UX task; frontend now accepts the field without type errors, but no component reads it yet.
- **OpenAPI YAML update for `ChainResponse`** — the chain DTOs were hand-authored (not code-generated) in text-chains Task 2. Syncing the OpenAPI spec is deferred to a codegen-alignment pass when `npm run gen:all` is enforced for the text module. Trigger: when a second consumer (e.g., mobile client, external integration) needs a machine-readable contract.
- **Structured JSON parsing of `meta` values** — runner stores raw strings; parsing is the frontend's responsibility per architecture ("no JSON parsing in the runner").
- **`chainCompleted` signal payload** — `meta` is a response concern, not an analytics concern. Signal shape unchanged.
- **Regression tests for `deep-humanize` and `rewrite-review`** — covered by Task 4 (Unit + regression tests), not this task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) — Design rationale for `meta` field shape and sidecar semantics
- [Epic](./epic.md) — Task scope and dependencies
- [Timeline](./timeline.md) — Status tracking (update after done)
- [Analysis](./analysis.md) — Root cause and resolved questions about `outputKey` behavior