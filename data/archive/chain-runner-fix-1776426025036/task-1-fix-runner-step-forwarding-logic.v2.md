# Task 1: Fix Runner Step-Forwarding Logic

**Purpose**: Stop `outputKey` steps from clobbering the pipeline's main data flow. After this fix, sidecar steps store their result in a `meta` dict and leave `current_text` unchanged, so the `braindump-to-docs` chain returns generated spec files instead of quality-score JSON.

**Effort**: 0.5 day

**Dependencies**: None (first task in the epic)

**Parallel With**: ---

**Blocks**: Task 2 (Add `meta` field to `ChainRunResult`), Task 3 (Extend DTOs and service layer), Task 4 (Unit + regression tests)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)
- [Analysis](./analysis.md)

---

## 1. Context

The chain runner in `definition_runner.py` executes steps sequentially, passing each step's output to the next via `current_text`. Line 246 (`current_text = result.text`) runs unconditionally -- even for steps that declare `output_key`, which are designed as sidecar operations (lint, score) that produce metadata without altering the pipeline's main data flow.

The `braindump-to-docs` chain has three steps:
1. **lint** (`outputKey: "lint"`) -- receives user input, produces lint JSON
2. **generate** (no `outputKey`) -- should receive user input, produces spec files
3. **score** (`outputKey: "score"`) -- receives generated specs, produces quality JSON

Because every step overwrites `current_text`, Step 2 receives lint JSON instead of user input, and the final output is quality-score JSON instead of generated specs. The user sees a JSON blob.

The fix adds a `meta: dict[str, str] = {}` accumulation dict to the run loop. Steps with `output_key` store their result in `meta` and skip the `current_text` assignment. Steps without `output_key` behave exactly as before. The `meta` dict is passed to `ChainRunResult` (via `meta or None`) so downstream layers can forward it. The `step_outputs` append remains unconditional (before the branch) to keep fix-injection lookback indices stable.

**Trade-offs considered**:
- **Skip sidecar output entirely (don't store in `meta`)** -- rejected because the epic requires `meta` to be plumbed to the API response for future UX (lint warnings, quality scores). Discarding the output wastes the LLM call.
- **Store `meta` in a separate data structure outside `ChainRunResult`** -- rejected because `ChainRunResult` is the single return type from `run_definition`; adding a parallel return channel creates coupling the dataclass already solves.
- **Conditional `current_text` update + `meta` accumulation in the step loop (chosen)** -- preferred because it is the minimal change: one dict init, one if/else branch replacing an unconditional assignment, one field addition to the dataclass, one kwarg in result construction. Matches the architecture's fixed-behavior pseudocode exactly.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}
git status                                                    # Flag any unrelated M/?? entries
git diff HEAD -- server/modules/chain/definition_runner.py    # Confirm target file is clean
cd server && python -m pytest --tb=short -q 2>&1 | tail -5   # Record baseline pass count
```

**If working tree is dirty on target file**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: `[N]/[N] passing`.

---

## 3. Files

### To Create
- (none)

### To Modify
- `server/modules/chain/definition_runner.py` -- four changes:
  1. Add `meta: dict[str, str] | None = None` field to `ChainRunResult` dataclass (after `files`, before `step_count`)
  2. Add `meta: dict[str, str] = {}` initialization in `run_definition`, after `step_outputs` initialization
  3. Replace the unconditional `current_text = result.text` (line 246) with an if/else that branches on `step.output_key`
  4. Pass `meta=meta or None` to both `ChainRunResult(...)` construction sites (multi-file branch and single branch)

### To Leave Alone
- `server/modules/chain/adapter.py` -- adapter boundary intact; meta is a runner concern
- `server/modules/chain/types.py` -- `ChainResult` is the per-step provider type; meta belongs on the per-chain `ChainRunResult`
- `server/modules/chain/definitions/braindump-to-docs.json` -- definition already declares `outputKey` correctly; no changes needed
- `server/modules/chain/definitions/deep-humanize.json` -- no `outputKey` steps; unaffected
- `server/modules/chain/definitions/rewrite-review.json` -- no `outputKey` steps; unaffected
- `server/modules/chain/runner.py` -- legacy sequential runner; not used by definition_runner
- `server/modules/text/chain_dto.py` -- DTO extension is Task 3's responsibility
- `server/modules/text/chain_service.py` -- service plumbing is Task 3's responsibility
- `src/app/mocks/chain.mock.ts` -- frontend interface update is Task 3's responsibility
- `server/modules/chain/tests/test_definition_runner.py` -- existing tests must not be modified; new tests are Task 4's responsibility

---

## 4. Implementation Steps

### Step 1: Add `meta` field to `ChainRunResult` dataclass

**Action**: Add `meta: dict[str, str] | None = None` to the `ChainRunResult` dataclass, positioned after `files` and before `step_count`.

**File**: `server/modules/chain/definition_runner.py`, around line 186

**Pattern**:

Current:

```python
@dataclass
class ChainRunResult:
    """Result of a full chain execution."""
    chain_id: str
    output_mode: str
    result: str | None = None
    files: list[dict[str, str]] | None = None
    step_count: int = 0
    total_tokens: int | None = None
    input_length: int = 0
    output_length: int = 0
```

After:

```python
@dataclass
class ChainRunResult:
    """Result of a full chain execution."""
    chain_id: str
    output_mode: str
    result: str | None = None
    files: list[dict[str, str]] | None = None
    meta: dict[str, str] | None = None
    step_count: int = 0
    total_tokens: int | None = None
    input_length: int = 0
    output_length: int = 0
```

**Verify**:

```bash
cd {WORKSPACE}/server
python -c "
from modules.chain.definition_runner import ChainRunResult
r = ChainRunResult(chain_id='test', output_mode='single', meta={'lint': 'ok'})
assert r.meta == {'lint': 'ok'}, f'meta not set: {r.meta}'
r2 = ChainRunResult(chain_id='test', output_mode='single')
assert r2.meta is None, f'meta default should be None: {r2.meta}'
print('OK: ChainRunResult.meta field works')
"
```

---

### Step 2: Initialize `meta` accumulation dict in `run_definition`

**Action**: Add `meta: dict[str, str] = {}` in `run_definition`, immediately after the `step_outputs: list[str] = []` line. The two accumulation variables should be adjacent.

**File**: `server/modules/chain/definition_runner.py`, function `run_definition`, around line 221

**Pattern**:

Current (around lines 218-223):

```python
current_text = user_input
total_tokens: int = 0
# step_outputs[i] = output of step i; used for fix-injection lookback
step_outputs: list[str] = []
steps = definition.steps
```

After:

```python
current_text = user_input
total_tokens: int = 0
# step_outputs[i] = output of step i; used for fix-injection lookback
step_outputs: list[str] = []
meta: dict[str, str] = {}
steps = definition.steps
```

**Verify**: visual inspection -- no runtime check needed; Step 3 exercises it.

---

### Step 3: Replace unconditional `current_text` assignment with conditional branch

**Action**: Replace the two lines at the end of the step loop body (lines 245-246):

```python
step_outputs.append(result.text)
current_text = result.text
```

with:

```python
step_outputs.append(result.text)
if step.output_key is not None:
    meta[step.output_key] = result.text
else:
    current_text = result.text
```

**File**: `server/modules/chain/definition_runner.py`, inside the `for i, step in enumerate(steps):` loop, around line 245

**Why `step_outputs.append` stays above the conditional**: the fix-injection logic (lines 239-242) reads `step_outputs[i-1]` and `step_outputs[i-2]`. Sidecar steps must still append to `step_outputs` to keep indices stable. The architecture confirms: "Sidecar steps still append to `step_outputs` (the append happens before the `output_key` check)."

**Why test `is not None` first (not `is None` guard clause)**: the sidecar branch is the new, explicit path. Putting it first makes the diff read as "here's what changed" rather than burying it in an else. The `else` is the default pipeline path (unchanged behavior).

**Verify**:

```bash
cd {WORKSPACE}/server
python -c "
from modules.chain.definition_runner import run_definition
r = run_definition('deep-humanize', 'test input')
assert r.result is not None, 'deep-humanize should still produce output'
print(f'OK: deep-humanize still works (output length={r.output_length})')
"
```

---

### Step 4: Pass `meta` to `ChainRunResult` construction (multi-file branch)

**Action**: Add `meta=meta or None,` to the `ChainRunResult(...)` construction in the `if definition.output_mode == "multi-file":` branch.

**File**: `server/modules/chain/definition_runner.py`, around line 254

**Pattern**:

Current:

```python
if definition.output_mode == "multi-file":
    files = parse_multi_file_output(final_output)
    run_result = ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        files=files,
        step_count=len(definition.steps),
        total_tokens=total_tokens or None,
        input_length=len(user_input),
        output_length=output_length,
    )
```

After:

```python
if definition.output_mode == "multi-file":
    files = parse_multi_file_output(final_output)
    run_result = ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        files=files,
        meta=meta or None,
        step_count=len(definition.steps),
        total_tokens=total_tokens or None,
        input_length=len(user_input),
        output_length=output_length,
    )
```

**Why `meta or None`**: converts an empty dict (no sidecar steps ran) to `None`, matching the dataclass default. Chains without `outputKey` steps (deep-humanize, rewrite-review) get `meta=None`, which keeps the response clean and backward-compatible.

**Verify**: deferred to Step 5.

---

### Step 5: Pass `meta` to `ChainRunResult` construction (single branch)

**Action**: Add `meta=meta or None,` to the `ChainRunResult(...)` construction in the `else` branch.

**File**: `server/modules/chain/definition_runner.py`, around line 264

**Pattern**:

Current:

```python
else:
    run_result = ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        result=final_output,
        step_count=len(definition.steps),
        total_tokens=total_tokens or None,
        input_length=len(user_input),
        output_length=output_length,
    )
```

After:

```python
else:
    run_result = ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        result=final_output,
        meta=meta or None,
        step_count=len(definition.steps),
        total_tokens=total_tokens or None,
        input_length=len(user_input),
        output_length=output_length,
    )
```

**Verify**:

```bash
cd {WORKSPACE}/server
python -m pytest modules/chain/tests/ --tb=short -q 2>&1 | tail -5
```

Expected: all existing chain tests pass. The `meta` field defaults to `None`, so existing `ChainRunResult` constructions that don't pass `meta` remain valid.

Secondary check -- run the full braindump-to-docs and deep-humanize chains with the mock provider to confirm the fix doesn't break either:

```bash
cd {WORKSPACE}/server
python -c "
from modules.chain.definition_runner import run_definition
# deep-humanize: no outputKey steps, should behave identically
dh = run_definition('deep-humanize', 'AI text to humanize')
assert dh.result is not None, 'deep-humanize result is None'
assert dh.meta is None, f'deep-humanize should have meta=None, got {dh.meta}'
print(f'deep-humanize: OK (result length={len(dh.result)})')

# braindump-to-docs: has outputKey steps, meta should be populated
bd = run_definition('braindump-to-docs', '# My Braindump')
assert bd.meta is not None, 'braindump-to-docs should have meta'
assert 'lint' in bd.meta, f'meta missing lint key: {bd.meta.keys()}'
assert 'score' in bd.meta, f'meta missing score key: {bd.meta.keys()}'
print(f'braindump-to-docs: OK (meta keys={list(bd.meta.keys())})')

# rewrite-review: no outputKey steps, should behave identically
rr = run_definition('rewrite-review', 'text to review')
assert rr.result is not None, 'rewrite-review result is None'
assert rr.meta is None, f'rewrite-review should have meta=None, got {rr.meta}'
print(f'rewrite-review: OK (result length={len(rr.result)})')
"
```

---

## 5. Tests

No new test file is created in this task. The existing tests in `server/modules/chain/tests/test_definition_runner.py` must pass without modification -- they exercise `deep-humanize` and `rewrite-review` chains which have no `outputKey` steps, so their behavior is unchanged.

Full test coverage for the sidecar logic (meta accumulation, pipeline input preservation, regression for all three chains) is Task 4's scope. This task's verification relies on:
1. All existing tests passing (Step 5 verify command)
2. The inline Python checks in Steps 1, 3, and 5 that exercise both sidecar and non-sidecar chains

---

## 6. Commit Plan

One commit (single file modified, one logical unit):

```
feat(chain): fix outputKey step forwarding — sidecar to meta, don't replace current_text

definition_runner.py:
- Add meta: dict[str, str] | None = None field to ChainRunResult
- Init meta: dict[str, str] = {} before step loop in run_definition
- Replace unconditional current_text = result.text with if/else:
  outputKey steps store in meta; others forward as before
- Pass meta or None to both ChainRunResult construction sites

Fixes: braindump-to-docs returns generated specs (not score JSON)
No impact: deep-humanize, rewrite-review (no outputKey steps)
```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/server
python -m pytest --tb=short -q 2>&1 | tail -10
```

**Expected delta**: `[N] → [N] passing` (zero new tests in this task; zero existing tests broken).

Secondary check -- confirm the dataclass field exists and chains behave correctly:

```bash
cd {WORKSPACE}/server
python -c "
import dataclasses
from modules.chain.definition_runner import ChainRunResult
fields = {f.name for f in dataclasses.fields(ChainRunResult)}
assert 'meta' in fields, f'meta not in ChainRunResult fields: {fields}'
print(f'ChainRunResult fields: {sorted(fields)}')
"
```

---

## 8. Rollback

- **Per-step**: single file modified. `git revert <sha>` undoes all changes atomically. `ChainRunResult` callers that don't pass `meta` continue to work (field has default `None`). The revert restores the unconditional `current_text = result.text` line.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (the sha recorded in Pre-flight) or delete the feature branch.

---

## 9. Deviations Allowed

- **Line numbers differ from documented** -- the guide references lines 218-246 based on the analyzed file. If the file has been reformatted or other tasks have shifted line numbers, locate the equivalent code by searching for `current_text = result.text` (the unconditional assignment) and `class ChainRunResult`. Log the actual line numbers in the commit body.
- **`step_outputs` variable named differently** -- the architecture references `step_outputs` but the actual variable may be `outputs`, `results`, etc. Use whatever name exists. The invariant: the append happens *before* the `output_key` conditional.
- **`total_tokens` accumulation line is between `step_outputs.append` and `current_text = result.text`** -- the guide's code blocks show the append and assignment as adjacent. If there's a `total_tokens +=` line between them, place the if/else branch after the token accumulation line (it must remain unconditional). Log as deviation.
- **`run_definition` signature includes additional parameters** (e.g., `db`, `context_blocks`) -- adapt verify commands accordingly. Log as deviation.
- **Side-effect required** (push, publish, migration) -- STOP, mark `[REQUIRES APPROVAL]` and ask. This task should not need any.

---

## 10. Out of Scope

This task fixes the forwarding logic and adds the `meta` accumulation infrastructure. It does NOT plumb meta through downstream layers, add tests, or render it.

- **DTO/service/frontend plumbing** -- Task 3 adds `meta` to `ChainResponse` DTO (`server/modules/text/chain_dto.py`), forwards it in `chain_service.py`, and updates the frontend `ChainResponse` interface in `src/app/mocks/chain.mock.ts`. Do not touch those files.
- **Unit + regression tests** -- Task 4 covers `outputKeyStep_doesNotReplacePipelineInput`, `braindumpChain_finalOutputIsGenerateStep`, `deepHumanize_unchanged`, `rewriteReview_unchanged`, and `fixModeInjection_worksWithSidecarSteps`. This task verifies only via existing tests + inline Python checks.
- **UI rendering of sidecar data** -- separate UX task; no frontend component reads `meta` yet.
- **Structured parsing of `meta` values** -- runner stores raw strings per architecture ("no JSON parsing in the runner"). Parsing is the frontend's responsibility.
- **`chainCompleted` signal payload** -- `meta` is a response concern, not an analytics concern. Signal shape unchanged.
- **Retry/backoff on sidecar step failures** -- deferred infrastructure per Engineering Discipline ("not-yet-built is the right state for infrastructure nobody's asked for").
- **Changes to chain definition JSON files** -- the definitions already declare `outputKey` correctly; only the runner interpretation was wrong.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) -- Design rationale for sidecar semantics and data flow diagrams for all three chains
- [Epic](./epic.md) -- Task scope, dependencies (Task 1 -> Task 2 -> Task 3 -> Task 4), and success criteria
- [Analysis](./analysis.md) -- Root cause: unconditional `current_text` overwrite; resolved decisions on `outputKey` input semantics and meta value format
- [Timeline](./timeline.md) -- Status tracking (update after done)
