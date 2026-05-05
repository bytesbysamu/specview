---
sidebar_position: 3
---

# Architecture -- Chain Output Fix

**Purpose**: Technical design for the file-marker guard and CLI provider audit that prevent the braindump-to-docs chain from silently producing garbage output.

**References**: See [Epic](./epic.md) for scope. See [Analysis](./analysis.md) for root cause.

---

## Overview

Two changes: (1) a file-marker guard in the chain runner's step loop that aborts multi-file chains when the generate step produces no `===FILE:===` markers, and (2) an audit/fix of the CLI provider to ensure context blocks are passed as system messages. No new modules, no new endpoints, no schema changes.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Explicit Over Implicit | The guard checks for `===FILE:` markers explicitly instead of relying on `parse_multi_file_output()` returning an empty list silently. Failure is loud and debuggable. |
| Anti-Corruption Layer | The runner does not parse or interpret file content -- it only checks for the presence of markers. Content parsing remains in `file_parser.py`. |
| Adapter (every feature service) | No changes to `adapter.py`. The guard lives in the runner. The CLI provider audit ensures the adapter contract (system prompt vs user message) is honored. |
| Fail fast | Invalid intermediate output aborts the chain immediately instead of cascading through review and producing misleading zero scores. |

---

## Affected Components

### 1. Chain Runner -- File-Marker Guard (`server/modules/chain/definition_runner.py`)

**Location**: Inside the step loop, after `result = handler(...)` and `step_outputs.append(result.text)`, before the `output_key` sidecar check.

**Current behavior** (no guard):
```python
result: ChainResult = handler(effective_text, step, context_blocks, user=user)
step_outputs.append(result.text)
if step.output_key is not None:
    meta[step.output_key] = result.text
else:
    current_text = result.text
```

**Fixed behavior** (with guard):
```python
result: ChainResult = handler(effective_text, step, context_blocks, user=user)
step_outputs.append(result.text)

# File-marker guard: in multi-file chains, non-sidecar steps must produce markers
if (definition.output_mode == "multi-file"
        and step.output_key is None
        and "===FILE:" not in result.text):
    logger.error(
        "Generate step %d produced no ===FILE: markers. "
        "Raw output (first 200 chars): %s",
        i, result.text[:200]
    )
    return ChainRunResult(
        chain_id=definition.id,
        output_mode=definition.output_mode,
        result=f"[Chain Error] Step {i + 1} ({step.op}) failed to produce "
               f"file markers. The braindump-to-docs prompt may need updating. "
               f"Raw output preview: {result.text[:200]}",
        step_count=i + 1,
        total_tokens=total_tokens or None,
        input_length=len(user_input),
        output_length=len(result.text),
    )

if step.output_key is not None:
    meta[step.output_key] = result.text
else:
    current_text = result.text
```

**Guard conditions**:
- `definition.output_mode == "multi-file"` -- only multi-file chains expect file markers
- `step.output_key is None` -- sidecar steps (lint, review) are not expected to produce markers
- `"===FILE:" not in result.text` -- the generate step's output must contain at least one marker

**Guard action**: return a `ChainRunResult` with the error as `result` (not `files`), so the frontend receives a text error instead of an empty file list or garbage.

**Why not raise an exception**: the runner returns `ChainRunResult` for all outcomes. An exception would require changes to the service layer's error handling. Returning a result with an error message is consistent with the existing contract and lets the frontend display the error in the same output area.

### 2. CLI Provider Audit (`server/modules/chain/providers/cli_provider.py`)

**Hypothesis**: the CLI provider may be appending context blocks to the user message instead of passing them as a `--system-prompt` flag (or `-s` shorthand) to the Claude CLI. This would explain the LLM responding conversationally -- it sees the format instructions as part of the user's message and engages in dialogue rather than following a system directive.

**Audit steps**:

1. Read `cli_provider.py` and trace how context blocks from `context.py` are assembled into the CLI command
2. Verify the Claude CLI invocation uses `--system-prompt` (or `echo ... | claude -p --system-prompt "..."`) to pass context as system-level instructions
3. If context is concatenated into the user prompt, move it to `--system-prompt`
4. Add debug logging that prints the full CLI command (redacted user input) when `LOG_LEVEL=DEBUG`

**Expected fix** (if needed):
```python
# Before (buggy -- context as user message):
prompt = f"{context_text}\n\n{user_text}"
cmd = ["claude", "-p", prompt]

# After (fixed -- context as system prompt):
cmd = ["claude", "-p", user_text, "--system-prompt", context_text]
```

### 3. Data Flow After Fix

**Braindump-to-docs chain -- generate step succeeds**:
```
Step 1 (lint, outputKey="lint"):
  input:  user braindump
  output: lint JSON
  action: meta["lint"] = output; current_text unchanged

Step 2 (generate, no outputKey):
  input:  user braindump (current_text)
  output: "===FILE: spec-index.md===\n..."
  guard:  "===FILE:" found in output -- PASS
  action: current_text = output

Step 3 (score, outputKey="score"):
  input:  generated specs (current_text)
  output: quality score JSON
  action: meta["score"] = output; current_text unchanged

final_output = generated specs (CORRECT)
meta = {"lint": "...", "score": "..."} (CORRECT)
```

**Braindump-to-docs chain -- generate step fails**:
```
Step 1 (lint, outputKey="lint"):
  input:  user braindump
  output: lint JSON
  action: meta["lint"] = output; current_text unchanged

Step 2 (generate, no outputKey):
  input:  user braindump (current_text)
  output: "Alright, here's what I'm seeing..."
  guard:  "===FILE:" NOT found -- ABORT
  action: return ChainRunResult with error message

Step 3 (score): NEVER RUNS

final_output = "[Chain Error] Step 2 (generate) failed to produce file markers..."
```

---

## Execution Flow

```
[Task 1]  Audit CLI provider
              |
[Task 2]  Add file-marker guard in runner
              |
[Task 3]  Unit tests for guard
              |
[Task 4]  Integration test: end-to-end braindump chain
```

Tasks 1 and 2 are independent and can run in parallel. Task 3 depends on 2. Task 4 depends on both 1 and 2.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Guard returns error result vs raising exception | Return `ChainRunResult` with error | Consistent with existing runner contract; no service-layer changes needed; frontend displays error in same output area |
| Guard checks string presence vs regex | Simple `"===FILE:" in result.text` | File markers are a fixed string format; regex adds complexity with no benefit. A single marker is sufficient proof the LLM followed the template. |
| Guard applies to all non-sidecar steps vs only "generate" | All non-sidecar steps in multi-file chains | Future chains might have multiple non-sidecar steps that produce file output. The guard is general: any step that contributes to `current_text` in a multi-file chain must produce markers. |
| Error message includes raw output preview | Yes, first 200 chars | Debugging aid -- the developer can see whether the LLM produced conversational text, an error, or something else entirely. Truncated to avoid flooding logs. |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Guard fires on valid output that uses different marker format | The marker format `===FILE:` is standardized in all templates. No chain uses a different format. |
| CLI provider fix changes behavior for all chains | The system-prompt fix is correct behavior -- context blocks should always be system messages. Non-braindump chains benefit from the same fix. |
| Guard hides useful partial output | The error message includes a 200-char preview. The full output is logged at ERROR level for debugging. |
| Existing tests break | No existing chain uses multi-file output mode with mock steps that lack markers. Guard only fires on the specific failure condition. |

---

## Tech Stack (no changes)

```
Backend:  Flask + chain runner (guard addition) + CLI provider (audit/fix)
Frontend: No changes in this epic
```

No new dependencies. No new services. No new database tables.

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)

===END===
