---
sidebar_position: 3
---

# Architecture -- Chain Runner Fix

**Purpose**: Technical design for the outputKey sidecar fix.

**References**: See [Epic](./epic.md) for scope. See [Analysis](./analysis.md) for root cause.

---

## Overview

Four surgical changes across four files. No new modules, no new database tables, no new endpoints. The fix adds a conditional branch in the runner's step loop and plumbs an optional `meta` field from the runner dataclass through the DTO layer to the API response.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Anti-Corruption Layer | Sidecar results stay as raw strings in `meta` -- no JSON parsing in the runner. The frontend (or a future presenter layer) decides how to interpret them. |
| Adapter (every feature service) | No changes to `adapter.py`. The fix is purely in the runner and DTO layers. Provider boundary stays intact. |
| Explicit Over Implicit | The `output_key` field on `ChainStep` already declares sidecar intent explicitly. The fix honors that declaration instead of ignoring it. |
| Observer (cross-feature events) | `chainCompleted` signal is unchanged. Sidecar metadata is a response concern, not an analytics concern. |

---

## Affected Components

### 1. Chain Runner (`server/modules/chain/definition_runner.py`)

**Current behavior** (buggy):
```
for each step:
    result = handler(current_text, ...)
    step_outputs.append(result.text)
    current_text = result.text          # <-- unconditional
```

Every step's output replaces `current_text`, regardless of `output_key`.

**Fixed behavior**:
```
meta = {}

for each step:
    result = handler(effective_text, ...)
    step_outputs.append(result.text)
    if step.output_key is not None:
        meta[step.output_key] = result.text   # sidecar: store, don't forward
    else:
        current_text = result.text             # pipeline: forward as before
```

Steps with `output_key` store their result in `meta` and leave `current_text` unchanged. Steps without `output_key` behave exactly as before.

**Data flow for `braindump-to-docs` after fix**:

```
user_input = "# My Braindump\n## What\n..."

Step 1 (lint, outputKey="lint"):
  input:  current_text = user_input
  output: '{"issues": ["missing Why section"]}'
  action: meta["lint"] = output; current_text unchanged (still user_input)

Step 2 (generate, no outputKey):
  input:  current_text = user_input       <-- CORRECT (was lint JSON before fix)
  output: "===FILE: analysis.md===\n..."
  action: current_text = output

Step 3 (score, outputKey="score"):
  input:  current_text = generated specs
  output: '{"scores": {"structure": 0.85}}'
  action: meta["score"] = output; current_text unchanged (still generated specs)

final_output = current_text               <-- generated specs (CORRECT)
meta = {"lint": "...", "score": "..."}    <-- sidecar data preserved
```

**Data flow for `deep-humanize` after fix** (unchanged):

```
Step 1 (rewrite, no outputKey): current_text = pass-1 output
Step 2 (rewrite, no outputKey): current_text = pass-2 output
Step 3 (rewrite, no outputKey): current_text = pass-3 output
final_output = pass-3 output              <-- identical to before
meta = {}                                 <-- no sidecar steps
```

**Data flow for `rewrite-review` after fix** (unchanged):

```
Step 1 (rewrite, no outputKey): current_text = rewritten text
Step 2 (review, no outputKey):  current_text = review JSON
Step 3 (rewrite, mode=fix):    reads step_outputs[1] for issues, fixes them
final_output = fixed text                 <-- identical to before
meta = {}                                 <-- no sidecar steps
```

Note: `rewrite-review` Step 2 has NO `outputKey` -- it's intentionally part of the pipeline (its output feeds the fix-injection logic). Only steps that explicitly declare `outputKey` are sidecared.

### 2. `ChainRunResult` dataclass (`definition_runner.py`)

Add one field:

```python
@dataclass
class ChainRunResult:
    chain_id: str
    output_mode: str
    result: str | None = None
    files: list[dict[str, str]] | None = None
    meta: dict[str, str] | None = None        # NEW
    step_count: int = 0
    total_tokens: int | None = None
    input_length: int = 0
    output_length: int = 0
```

`meta` is `None` when no steps have `output_key` (deep-humanize, rewrite-review). Contains `{"lint": "...", "score": "..."}` for braindump-to-docs.

### 3. `ChainResponse` DTO (`server/modules/text/chain_dto.py`)

Add one field:

```python
class ChainResponse(BaseModel):
    generation_id: str = Field(..., alias="generationId")
    result: str | None = None
    files: list[ChainFileOutput] | None = None
    meta: dict[str, str] | None = None        # NEW

    model_config = {"populate_by_name": True, "by_alias": True}
```

Pydantic will omit `meta` from serialized JSON when it is `None` (using `exclude_none=True` in the route handler, or the field's default). Backward-compatible: existing consumers that don't read `meta` are unaffected.

### 4. Chain service (`server/modules/text/chain_service.py`)

Forward `meta` from `ChainRunResult` to the response dict:

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

### 5. Frontend interface (`src/app/mocks/chain.mock.ts`)

Add optional `meta` to the TypeScript interface:

```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
  meta?: Record<string, string>;
}
```

The frontend does not need to render `meta` in this epic. It just needs to accept it without type errors. UI rendering is a separate UX task.

---

## Fix-Mode Injection Compatibility

The fix-injection logic (lines 239-242) reads `step_outputs[i-1]` and `step_outputs[i-2]`:

```python
if step.mode == "fix" and i >= 2 and steps[i - 1].op == "review":
    review_output = step_outputs[i - 1]
    pre_review_text = step_outputs[i - 2] if i >= 2 else user_input
    effective_text = _inject_fix_instructions(review_output, pre_review_text)
```

Sidecar steps still append to `step_outputs` (the append happens before the `output_key` check). This means `step_outputs` indices remain stable. The fix-injection lookback reads the correct values regardless of whether prior steps were sidecared.

For `rewrite-review`, no steps have `outputKey`, so behavior is identical.

For a hypothetical future chain with both `outputKey` and `mode="fix"` steps: fix-injection would correctly look back through `step_outputs` even if some of those outputs were sidecared. The `step_outputs` list is an ordered log of every step's raw output; `current_text` is the pipeline's filtered main flow. These two concerns are now cleanly separated.

---

## API Response Shape

**Before fix** (braindump-to-docs):
```json
{
  "generationId": "abc-123",
  "files": null,
  "result": "{\"scores\": {\"structure\": 0.85}, \"issues\": []}"
}
```
The user sees quality-score JSON. Wrong.

**After fix** (braindump-to-docs):
```json
{
  "generationId": "abc-123",
  "files": [
    { "name": "analysis.md", "content": "# Analysis\n..." },
    { "name": "epic.md", "content": "# Epic\n..." }
  ],
  "meta": {
    "lint": "{\"issues\": [\"missing Why section\"]}",
    "score": "{\"scores\": {\"structure\": 0.85}, \"issues\": []}"
  }
}
```
The user sees generated spec files. Correct. Lint and score data available for future UI.

**After fix** (deep-humanize, no outputKey steps):
```json
{
  "generationId": "def-456",
  "result": "Honestly, the quick brown fox..."
}
```
No `meta` field. Backward-compatible.

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Fix-injection lookback breaks with sidecar steps | `step_outputs` append is unchanged; indices stable. Unit test `fixModeInjection_worksWithSidecarSteps` confirms. |
| Existing tests fail | No `outputKey` steps in `deep-humanize` or `rewrite-review`; their behavior is unchanged. Regression tests confirm. |
| Frontend breaks on unexpected `meta` field | TypeScript interface updated; `meta` is optional. JSON serialization omits it when `None`. |
| `meta` values contain sensitive data | Sidecar steps run the same prompts as pipeline steps, through the same adapter. No new security surface. |

---

## Tech Stack (no changes)

```
Backend:  Flask + chain adapter (existing) + runner (fix) + DTOs (extend)
Frontend: Angular 19 (interface update only, no rendering changes)
```

No new dependencies. No new services. No new database tables. No migrations.

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)

===END===
