I now have full context on the epic, architecture, analysis, and the shipped Task 3 guide. Let me generate the implementation guide.

# Task 2: Add `meta` field to `ChainRunResult`

**Purpose**: Capture sidecar `outputKey` step results into a `meta` dictionary on `ChainRunResult` so the runner preserves lint/score data alongside the pipeline's main output, enabling Task 3's DTO plumbing to expose it in the API response.

**Effort**: 0.25 day

**Dependencies**: Task 1 (Fix runner step-forwarding logic) must be merged — the conditional `if step.output_key is None: current_text = result.text` must already exist in `run_definition`.

**Parallel With**: —

**Blocks**: Task 3 (Extend DTOs and service layer — already shipped as spec, depends on `ChainRunResult.meta` existing), Task 4 (Unit + regression tests)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 1 fixed the unconditional `current_text = result.text` line so that steps with `output_key` no longer clobber the pipeline's main data flow. But the sidecar output is simply discarded — no code captures it. This task adds a `meta: dict[str, str] | None` field to `ChainRunResult` and wires the runner's step loop to accumulate sidecar results there. After this change, a `braindump-to-docs` run returns `meta={"lint": "...", "score": "..."}` alongside the generated spec files, while `deep-humanize` and `rewrite-review` return `meta=None` (no sidecar steps). Task 3 (already spec'd) then plumbs `meta` from the runner through the DTO and service layers to the API response. The change is confined to a single file: `definition_runner.py`.

**Trade-offs considered**:
- **Store meta as `dict[str, Any]` and parse sidecar JSON in the runner** — rejected because the architecture mandates raw strings ("no JSON parsing in the runner"); the frontend decides how to interpret sidecar values. Keeping `dict[str, str]` preserves the Anti-Corruption Layer boundary.
- **Add meta to `ChainResult` (provider-level type) instead of `ChainRunResult` (runner-level type)** — rejected because sidecar accumulation is a runner concern, not a provider concern. `ChainResult` (from `server/modules/chain/types.py`) normalizes a single provider response; `ChainRunResult` aggregates an entire chain execution. meta belongs on the aggregate.
- **Add `meta` field to `ChainRunResult` and accumulate in the step loop (chosen)** — preferred because it is the minimal change: one dataclass field, three lines in the loop, one line in result construction. Matches the architecture's fixed-behavior pseudocode exactly.

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

**If Task 1 is not merged**: STOP — the conditional forwarding logic must exist. Verify:

```bash
cd {WORKSPACE}/server
grep -n "if step.output_key is None" modules/chain/definition_runner.py
```

Expected: one match in `run_definition`, around line 246. If missing, Task 1 has not shipped — do not proceed.

**Baseline recorded**: `[N]/[N] passing`.

---

## 3. Files

### To Create
- (none)

### To Modify
- `server/modules/chain/definition_runner.py` — add `meta: dict[str, str] | None = None` field to `ChainRunResult` dataclass; add meta accumulation dict before the step loop; collect sidecar results in the `output_key is not None` branch; pass `meta` to `ChainRunResult` construction

### To Leave Alone
- `server/modules/chain/adapter.py` — adapter boundary intact; meta is a runner-level concern, not a provider concern
- `server/modules/chain/types.py` — `ChainResult` is the per-step provider return type; meta lives on the per-chain `ChainRunResult`, not here
- `server/modules/chain/definitions/braindump-to-docs.json` — chain definition already declares `outputKey` on lint and score steps; no changes needed
- `server/modules/text/chain_dto.py` — DTO extension is Task 3's responsibility (already spec'd)
- `server/modules/text/chain_service.py` — service plumbing is Task 3's responsibility (already spec'd)
- `src/app/mocks/chain.mock.ts` — frontend interface update is Task 3's responsibility (already spec'd)
- `server/modules/chain/tests/test_definition_runner.py` — existing tests must not be modified; new tests added only

---

## 4. Implementation Steps

### Step 1: Add `meta` field to `ChainRunResult` dataclass

**Action**: Add one field to the `ChainRunResult` dataclass, positioned after `files` and before `step_count` to maintain field grouping (output fields together, metrics fields together).

**File**: `server/modules/chain/definition_runner.py` (around line 186 per analysis)

**Pattern**:

The dataclass currently looks like (per architecture, confirmed by analysis line reference):

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

Add `meta` after `files`:

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

### Step 2: Initialize meta accumulation dict in `run_definition`

**Action**: Add `meta: dict[str, str] = {}` before the step loop in `run_definition`. Place it after the existing `step_outputs: list[str] = []` initialization (or similar local setup) so the two accumulation variables are adjacent.

**File**: `server/modules/chain/definition_runner.py`, function `run_definition`

**Pattern**:

Locate the step loop setup. After Task 1, the area around line 240 looks approximately like:

```python
step_outputs: list[str] = []
current_text = user_input
```

Add `meta` alongside:

```python
step_outputs: list[str] = []
current_text = user_input
meta: dict[str, str] = {}
```

**Verify**: visual inspection — no runtime check needed at this point; Step 3 will exercise it.

---

### Step 3: Accumulate sidecar results in the step loop

**Action**: Restructure the Task 1 conditional to also store sidecar output in `meta`. Task 1 left a guard-clause form (`if step.output_key is None: current_text = result.text`). Replace it with an if/else that captures sidecar results in the positive branch.

**File**: `server/modules/chain/definition_runner.py`, inside the `for i, step in enumerate(steps):` loop (around line 246)

**Pattern**:

Task 1's current code:

```python
result: ChainResult = handler(effective_text, step, context_blocks, user=user)
step_outputs.append(result.text)
if step.output_key is None:
    current_text = result.text
```

Replace the conditional with:

```python
result: ChainResult = handler(effective_text, step, context_blocks, user=user)
step_outputs.append(result.text)
if step.output_key is not None:
    meta[step.output_key] = result.text
else:
    current_text = result.text
```

Note the inversion: Task 1 tested `is None` (guard clause). This task tests `is not None` first so the sidecar branch is explicit and the else is the default pipeline path. The behavior is identical for the `current_text` assignment; the only addition is `meta[step.output_key] = result.text`.

**Why `step_outputs.append` stays above the conditional**: fix-mode injection (`step.mode == "fix"`) looks back at `step_outputs[i-1]` and `step_outputs[i-2]`. Sidecar steps must still append to `step_outputs` to keep indices stable. The architecture confirms this: "Sidecar steps still append to `step_outputs` (the append happens before the `output_key` check)."

**Verify**:

```bash
cd {WORKSPACE}/server
python -c "
from modules.chain.definition_runner import run_definition
print('import OK — run_definition has meta accumulation')
"
```

Functional verification deferred to Step 4's verify and the test in Section 5.

---

### Step 4: Pass `meta` to `ChainRunResult` construction

**Action**: Find the `ChainRunResult(...)` construction at the end of `run_definition` and add `meta=meta or None`. Using `meta or None` converts an empty dict (no sidecar steps ran) to `None`, matching the dataclass default and keeping the response clean for chains without sidecar steps.

**File**: `server/modules/chain/definition_runner.py`, end of `run_definition` (after the step loop, around the final return)

**Pattern**:

The current construction looks approximately like:

```python
run_result = ChainRunResult(
    chain_id=definition.id,
    output_mode=definition.output_mode,
    result=...,
    files=...,
    step_count=len(steps),
    total_tokens=...,
    input_length=len(user_input),
    output_length=len(current_text),
)
```

Add `meta`:

```python
run_result = ChainRunResult(
    chain_id=definition.id,
    output_mode=definition.output_mode,
    result=...,
    files=...,
    meta=meta or None,
    step_count=len(steps),
    total_tokens=...,
    input_length=len(user_input),
    output_length=len(current_text),
)
```

**Verify**:

```bash
cd {WORKSPACE}/server
python -m pytest modules/chain/tests/ --tb=short -q 2>&1 | tail -5
```

Expected: all existing chain tests pass. The `meta` field defaults to `None` so existing `ChainRunResult` constructions (in tests or elsewhere) that don't pass `meta` remain valid.

---

## 5. Tests

Add to `server/modules/chain/tests/test_definition_runner.py` (extend existing file). Match the repo's test framework: pytest, `condition_expectedOutcome` naming, Arrange/Act/Assert.

These tests verify the meta accumulation logic specifically. Full regression tests (deep-humanize unchanged, rewrite-review unchanged, fix-mode injection compatibility) are Task 4's scope.

```python
# --- meta accumulation tests (Task 2) ---

def test_outputKeyStep_resultStoredInMeta(mock_provider):
    """Step with outputKey stores its result in meta, not in current_text."""
    # Arrange: a 2-step chain where step 0 has outputKey="lint"
    definition = make_definition(
        steps=[
            make_step(op="review", output_key="lint"),
            make_step(op="generate"),
        ],
        output_mode="single",
    )
    mock_provider.responses = ["lint-result", "generated-output"]

    # Act
    result = run_definition(definition, "user input", user=None)

    # Assert
    assert result.meta is not None, "meta should be populated when outputKey steps exist"
    assert result.meta["lint"] == "lint-result"
    assert result.result == "generated-output", "pipeline output should be from the generate step"


def test_multipleOutputKeys_allCollectedInMeta(mock_provider):
    """Chain with two outputKey steps collects both in meta."""
    definition = make_definition(
        steps=[
            make_step(op="review", output_key="lint"),
            make_step(op="generate"),
            make_step(op="review", output_key="score"),
        ],
        output_mode="single",
    )
    mock_provider.responses = ["lint-json", "spec-files", "score-json"]

    # Act
    result = run_definition(definition, "braindump text", user=None)

    # Assert
    assert result.meta == {"lint": "lint-json", "score": "score-json"}
    assert result.result == "spec-files"


def test_noOutputKeys_metaIsNone(mock_provider):
    """Chain with no outputKey steps returns meta=None."""
    definition = make_definition(
        steps=[
            make_step(op="rewrite"),
            make_step(op="rewrite"),
        ],
        output_mode="single",
    )
    mock_provider.responses = ["pass-1", "pass-2"]

    # Act
    result = run_definition(definition, "original text", user=None)

    # Assert
    assert result.meta is None, "meta should be None when no outputKey steps exist"
    assert result.result == "pass-2"


def test_outputKeyStep_doesNotReplacePipelineInput(mock_provider):
    """Sidecar step leaves current_text unchanged; next step receives pre-sidecar value."""
    definition = make_definition(
        steps=[
            make_step(op="review", output_key="lint"),
            make_step(op="generate"),
        ],
        output_mode="single",
    )
    # Track what each handler receives
    received_inputs = []
    original_handler = mock_provider.handler

    def tracking_handler(text, step, context_blocks, *, user=None):
        received_inputs.append(text)
        return original_handler(text, step, context_blocks, user=user)

    mock_provider.handler = tracking_handler
    mock_provider.responses = ["lint-json", "generated-specs"]

    # Act
    run_definition(definition, "user braindump", user=None)

    # Assert: step 1 (lint) receives user input; step 2 (generate) also receives user input
    # because step 1's sidecar output did NOT replace current_text
    assert received_inputs[0] == "user braindump", "lint step should receive user input"
    assert received_inputs[1] == "user braindump", (
        "generate step should receive user input (not lint output), "
        "because the lint step has outputKey and should not replace current_text"
    )
```

**Note on test helpers**: The tests above use `make_definition`, `make_step`, and `mock_provider` fixtures. If these do not exist in the current test file, the executor should:

1. Check the existing test file for equivalent helpers (e.g., `create_definition`, `build_step`, a mock provider fixture).
2. If helpers exist under different names, use them and log the name difference as a deviation.
3. If no helpers exist, create minimal ones:

```python
from dataclasses import dataclass, field
from modules.chain.definition_runner import run_definition, ChainRunResult

# Minimal test helpers — adapt to match existing test patterns

def make_step(*, op: str, output_key: str | None = None, mode: str | None = None):
    """Build a ChainStep-compatible object for testing."""
    from modules.chain.definition_runner import ChainStep  # or wherever it lives
    return ChainStep(op=op, output_key=output_key, mode=mode)

def make_definition(*, steps: list, output_mode: str = "single"):
    """Build a ChainDefinition-compatible object for testing."""
    from modules.chain.definition_runner import ChainDefinition  # or wherever it lives
    return ChainDefinition(id="test-chain", steps=steps, output_mode=output_mode)
```

The mock provider fixture should set `CHAIN_PROVIDER=mock` via `monkeypatch` or use the existing test convention. Check `server/modules/chain/tests/` for the pattern in use.

---

## 6. Commit Plan

One commit (single file modified, one logical unit):

1. `feat(chain): add meta sidecar accumulation to ChainRunResult` — `server/modules/chain/definition_runner.py`: add `meta: dict[str, str] | None` field to `ChainRunResult` dataclass; accumulate `outputKey` step results in `meta` dict during `run_definition`; pass `meta or None` to result construction. Tests: 4 new assertions covering sidecar storage, multiple keys, no-key chains, and pipeline input preservation.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/server
python -m pytest --tb=short -q 2>&1 | tail -10
```

**Expected delta**: `[N] → [N+4] passing` (4 new meta accumulation tests). Zero pre-existing tests broken.

Secondary check — confirm the dataclass field is accessible downstream:

```bash
cd {WORKSPACE}/server
python -c "
from modules.chain.definition_runner import ChainRunResult
import dataclasses
fields = {f.name for f in dataclasses.fields(ChainRunResult)}
assert 'meta' in fields, f'meta not in ChainRunResult fields: {fields}'
print(f'ChainRunResult fields: {sorted(fields)}')
"
```

---

## 8. Rollback

- **Per-step**: single commit is independently revertible. `git revert <sha>` removes all changes atomically. `ChainRunResult` callers that don't pass `meta` continue to work (field has default `None`).
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (the sha recorded in Pre-flight) or delete the feature branch.

---

## 9. Deviations Allowed

- **Task 1 used `if step.output_key is None` without an else** — this guide inverts to `if step.output_key is not None ... else`. If the executor finds Task 1 already used an if/else structure (e.g., `if step.output_key is not None: pass / else: current_text = result.text`), add the `meta` accumulation line inside the existing positive branch. Log the structural difference in the commit body.
- **`ChainRunResult` field order differs from documented** — insert `meta` after `files` regardless of the surrounding field order. If `files` doesn't exist yet (Task 1 didn't add it), insert `meta` after `result`. Log in commit.
- **Test helpers have different names or signatures** — match the existing test file's conventions. If `make_definition`/`make_step` don't exist, check for alternatives (`create_*`, `build_*`, direct dataclass construction). Translate test bodies silently; log the naming difference in the commit.
- **`step_outputs` variable named differently** — the architecture references `step_outputs` but the actual variable may be named `outputs`, `results`, etc. Use whatever name exists. The invariant is: append happens *before* the `output_key` conditional.
- **`run_definition` signature differs** — the guide assumes `run_definition(definition, user_input, *, user=None)`. If the actual signature has additional parameters (e.g., `db`, `context_blocks`), adapt the test calls accordingly. Log as deviation.
- **Side-effect required** (push, publish, migration) — STOP, mark `[REQUIRES APPROVAL]` and ask. This task should not need any.

---

## 10. Out of Scope

This task adds the `meta` field to `ChainRunResult` and wires the runner to populate it. It does NOT plumb meta through downstream layers, render it, or test the full pipeline end-to-end.

- **DTO/service/frontend plumbing** — Task 3 (already spec'd) adds `meta` to `ChainResponse` DTO, forwards it in `chain_service.py`, and updates the frontend `ChainResponse` interface. Do not touch those files.
- **UI rendering of sidecar data** — separate UX task; no frontend component reads `meta` yet.
- **Full regression tests** — Task 4 covers `deepHumanize_unchanged`, `rewriteReview_unchanged`, `fixModeInjection_worksWithSidecarSteps`, and the `braindump-to-docs` end-to-end flow. This task includes only targeted meta-accumulation unit tests.
- **Structured parsing of `meta` values** — runner stores raw strings per architecture ("no JSON parsing in the runner"). Parsing is the frontend's responsibility.
- **`chainCompleted` signal payload** — `meta` is a response concern, not an analytics concern. Signal shape unchanged.
- **Retry/backoff on sidecar step failures** — deferred infrastructure per Engineering Discipline ("not-yet-built is the right state for infrastructure nobody's asked for").

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) — Design rationale for `meta` field shape and sidecar semantics
- [Epic](./epic.md) — Task scope and dependencies (Task 1 → Task 2 → Task 3 → Task 4)
- [Analysis](./analysis.md) — Root cause: unconditional `current_text` overwrite; resolved decision that `meta` values are raw strings
- [Timeline](./timeline.md) — Status tracking (update after done)