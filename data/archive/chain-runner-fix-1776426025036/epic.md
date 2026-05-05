---
sidebar_position: 2
---

# Epic -- Chain Runner Fix

**Purpose**: Define scope and tasks for fixing the outputKey sidecar bug in the chain runner.

**Source Analysis**: See [Analysis](./analysis.md) for root cause and resolved questions.

---

## Business Value

This is the most visible bug in the shipped Text Chains epic. A user taps Brain Dump, waits through 3 chain steps, and sees a quality-score JSON blob instead of their generated spec files. The chain worked in backend tests (mock provider returns predictable strings) but the real flow exposes the forwarding problem. Every chain that uses a review step with `outputKey` as anything other than the final step hits this. Fixing it unblocks the braindump-to-docs pipeline -- the differentiator nobody else ships (multi-file generation from a single brain dump).

Secondary value: plumbing `meta` to the frontend enables future UX for lint warnings and quality scores (collapsible panels, badge tabs), turning sidecar steps from invisible backend operations into user-visible quality signals.

---

## Scope

### What This Epic Covers

- **Runner fix**: conditional `current_text` update -- skip when `step.output_key` is set
- **Sidecar accumulation**: collect `outputKey` step results into a `meta: dict[str, str]` on `ChainRunResult`
- **DTO extension**: add optional `meta` field to `ChainResponse` (Pydantic), `ChainResponse` (frontend interface), and `ChainResponse` mock
- **Service plumbing**: forward `meta` from `ChainRunResult` through `chain_service.py` to the API response
- **Tests**: unit tests for sidecar behavior, regression tests for chains without `outputKey`

### What This Epic Does NOT Cover

- UI rendering of `meta` data (collapsible panels, tabs with badge) -- separate UX task
- Structured parsing of review JSON in the runner
- Changes to `chainCompleted` signal payload
- Changes to chain definition JSON files
- Retry/backoff on sidecar step failures

---

## Tasks

**Note**: Task status tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **Fix runner step-forwarding logic** | None | 0.5 day | High |
| 2 | **Add `meta` field to `ChainRunResult`** | 1 | 0.25 day | High |
| 3 | **Extend DTOs and service layer** | 2 | 0.25 day | High |
| 4 | **Unit + regression tests** | 1, 2, 3 | 0.5 day | High |

### Task Details

#### Task 1: Fix runner step-forwarding logic

**File**: `server/modules/chain/definition_runner.py`, function `run_definition`, lines 244-246.

**Current code** (buggy):
```python
result: ChainResult = handler(effective_text, step, context_blocks, user=user)
step_outputs.append(result.text)
current_text = result.text
```

**Fixed code**:
```python
result: ChainResult = handler(effective_text, step, context_blocks, user=user)
step_outputs.append(result.text)
if step.output_key is None:
    current_text = result.text
```

When `step.output_key` is set, the step's output goes to `step_outputs` (for fix-injection lookback) but does NOT replace `current_text`. The pipeline's main data flow continues with whatever `current_text` was before this step ran.

**Behavior change for `braindump-to-docs`**:
- Step 1 (lint, `outputKey: "lint"`): receives `user_input` via `current_text`, produces lint JSON, sidecars it. `current_text` remains `user_input`.
- Step 2 (generate): receives `user_input` via `current_text` (correct -- not lint JSON), produces spec files. `current_text` becomes the generated specs.
- Step 3 (score, `outputKey: "score"`): receives generated specs via `current_text`, produces quality JSON, sidecars it. `current_text` remains the generated specs.
- Final output: the generated spec files (correct -- not quality JSON).

**No impact on `deep-humanize` or `rewrite-review`**: neither chain uses `outputKey`, so every step sets `current_text = result.text` as before.

#### Task 2: Add `meta` field to `ChainRunResult`

**File**: `server/modules/chain/definition_runner.py`.

Add `meta` field to the `ChainRunResult` dataclass:

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

In `run_definition`, accumulate sidecar results:

```python
meta: dict[str, str] = {}

for i, step in enumerate(steps):
    # ... handler call ...
    step_outputs.append(result.text)
    if step.output_key is not None:
        meta[step.output_key] = result.text
    else:
        current_text = result.text
```

Pass `meta` (or `None` if empty) into `ChainRunResult`:

```python
run_result = ChainRunResult(
    ...,
    meta=meta or None,
    ...
)
```

#### Task 3: Extend DTOs and service layer

**Three files to modify**:

1. **`server/modules/text/chain_dto.py`** -- add optional `meta` to `ChainResponse`:
```python
class ChainResponse(BaseModel):
    generation_id: str = Field(..., alias="generationId")
    result: str | None = None
    files: list[ChainFileOutput] | None = None
    meta: dict[str, str] | None = None

    model_config = {"populate_by_name": True, "by_alias": True}
```

2. **`server/modules/text/chain_service.py`** -- forward `meta` from `ChainRunResult` to response dict:
```python
if run_result.meta:
    response["meta"] = run_result.meta
```

3. **`src/app/mocks/chain.mock.ts`** -- add optional `meta` to frontend `ChainResponse` interface:
```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
  meta?: Record<string, string>;
}
```

Update `MOCK_CHAIN_MULTI` to include sample meta for testing:
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

#### Task 4: Unit + regression tests

**File**: `server/modules/chain/tests/test_definition_runner.py` (extend existing).

**New test cases**:

| Test | Assertion |
|------|-----------|
| `outputKeyStep_doesNotReplacePipelineInput` | Step with `outputKey` does not change `current_text`; next step receives the pre-sidecar value |
| `outputKeyStep_resultStoredInMeta` | `ChainRunResult.meta` contains `{outputKey: result.text}` for each sidecar step |
| `multipleOutputKeys_allCollectedInMeta` | Chain with two `outputKey` steps has both keys in `meta` |
| `noOutputKeys_metaIsNone` | Chain with no `outputKey` steps returns `meta=None` |
| `braindumpChain_finalOutputIsGenerateStep` | Simulated braindump-to-docs chain returns Step 2's generate output, not Step 3's review JSON |
| `braindumpChain_generateReceivesUserInput` | Step 2 of braindump-to-docs receives the original user input, not Step 1's lint JSON |
| `deepHumanize_unchanged` | Deep Humanize chain produces the same result as before the fix (regression) |
| `rewriteReview_unchanged` | Rewrite+Review chain produces the same result as before the fix (regression) |
| `fixModeInjection_worksWithSidecarSteps` | Fix-injection lookback into `step_outputs` still works when sidecar steps are present |

---

## Success Criteria

- `braindump-to-docs` chain returns generated spec files as the main output, not quality-score JSON
- Step 2 (generate) receives the user's braindump, not Step 1's lint JSON
- `ChainRunResult.meta` contains `{"lint": "...", "score": "..."}` after a braindump-to-docs run
- `meta` field appears in the API response JSON when sidecar steps are present
- `meta` field is omitted from the API response when no sidecar steps ran
- `deep-humanize` chain output is identical before and after the fix
- `rewrite-review` chain output is identical before and after the fix
- Fix-mode injection still works correctly in `rewrite-review`
- All existing chain tests pass without modification

---

## Non-Goals

- UI rendering of sidecar metadata
- Structured JSON parsing of sidecar values in the runner
- Changes to chain definition files
- Changes to `chainCompleted` signal payload
- New chain definitions

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
