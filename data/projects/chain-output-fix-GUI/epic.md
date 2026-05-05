---
sidebar_position: 2
---

# Epic -- Chain Output Fix

**Purpose**: Define scope and tasks for fixing the three interacting bugs in the braindump-to-docs chain that cause the Brain Dump button to show quality JSON or conversational text instead of generated spec files.

**Source Analysis**: See [Analysis](./analysis.md) for root cause and resolved questions.

---

## Business Value

The Brain Dump button is the flagship feature of the Bubls GUI -- it turns a freeform braindump into a structured 5-file spec set in one tap. Right now it is effectively broken: users see either conversational prose ("Alright, here's what I'm seeing...") or a quality-score JSON blob instead of their generated specs. The single-shot rewrite modes (Humanize, Expand, etc.) work correctly, so users who hit Brain Dump and get garbage output assume the product is broken rather than understanding this is a chain-specific bug.

The outputKey sidecar fix (Chain Runner Fix epic) solved the data-flow problem -- sidecar steps no longer overwrite the pipeline. But the upstream generate step itself is unreliable. Without this fix, the sidecar plumbing is correct but the data flowing through it is garbage. This epic fixes the source: make the generate step produce valid file-marker output, and add a guard so failures surface clearly instead of cascading silently.

---

## Scope

### What This Epic Covers

- **File-marker guard in runner**: detect when a multi-file chain's intermediate step produces no `===FILE:===` markers and abort with a clear error instead of forwarding to review
- **CLI provider system-prompt audit**: verify that context blocks are passed as system messages, not user messages, to prevent conversational LLM responses
- **Integration with template port**: ensure the runner guard works correctly with both the current underspecified prompt and the improved prompt from the Port Spec-Doc Template epic
- **Tests**: unit tests for the guard, integration test for end-to-end braindump chain

### What This Epic Does NOT Cover

- Detailed prompt content (section headings, format instructions, word-count rules) -- scoped in Port Spec-Doc Template epic
- UI rendering of chain error states
- Retry/backoff when the generate step fails
- Changes to chain definition JSON files
- Review step changes (it correctly scores whatever it receives; the fix is upstream)

---

## Tasks

**Note**: Task status tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **Audit CLI provider system-prompt handling** | None | 0.25 day | High |
| 2 | **Add file-marker guard in definition runner** | None | 0.5 day | High |
| 3 | **Unit tests for file-marker guard** | 2 | 0.25 day | High |
| 4 | **Integration test: braindump chain end-to-end** | 1, 2 | 0.5 day | Medium |

### Task Details

#### Task 1: Audit CLI provider system-prompt handling

Inspect `server/modules/chain/providers/cli_provider.py` to verify that context blocks loaded by `context.py` are passed as `--system-prompt` (or equivalent) to the Claude CLI, not appended to the user message. If context is being passed as user message content, the LLM will treat format instructions as conversational input and respond conversationally. Fix: ensure context blocks are injected as system-level instructions.

**Verify**: run the braindump-to-docs chain with debug logging enabled and confirm the CLI invocation includes the context as a system prompt parameter.

#### Task 2: Add file-marker guard in definition runner

In `definition_runner.py`, after a step completes in a `multi-file` chain, check whether the step's output contains at least one `===FILE:` marker when the step is expected to produce file output (i.e., it is the non-sidecar generate step in a multi-file chain). If no markers are found:

1. Log a clear error: `"Generate step {i} produced no ===FILE: markers. Raw output: {first 200 chars}"`
2. Abort the chain and return a `ChainRunResult` with `result` set to an error message and `files` set to `None`
3. Do NOT forward the invalid output to subsequent steps (review would score garbage)

The guard applies only when `definition.output_mode == "multi-file"` and the step does NOT have an `output_key` (sidecar steps are not expected to produce file markers).

**Verify**: mock a generate step that returns conversational text, confirm the chain aborts with the error message instead of forwarding to review.

#### Task 3: Unit tests for file-marker guard

Add tests to `server/modules/chain/tests/test_definition_runner.py`:

| Test | Assertion |
|------|-----------|
| `multiFileChain_generateWithMarkers_continues` | Chain proceeds normally when generate step produces valid `===FILE:===` markers |
| `multiFileChain_generateWithoutMarkers_abortsWithError` | Chain aborts and returns error when generate step produces no markers |
| `multiFileChain_sidecarStep_noMarkerCheckNeeded` | Sidecar steps (with `outputKey`) are not subject to the marker guard |
| `singleOutputChain_noMarkerGuard` | Single-output chains skip the marker guard entirely |

#### Task 4: Integration test: braindump chain end-to-end

Run the braindump-to-docs chain with a real braindump input (use the chain-output-fix braindump itself as test input). Verify:

1. With the current underspecified prompt: the guard catches the missing markers and returns a clear error
2. After the Port Spec-Doc Template epic ships: the generate step produces valid markers and the chain completes successfully
3. The review step receives valid file-marker output and produces non-zero scores
4. The final API response contains `files` (not `result`) and `meta` with lint + score data

---

## Success Criteria

- The file-marker guard catches generate-step failures and aborts with a clear error instead of forwarding garbage to review
- CLI provider passes context blocks as system messages, not user messages
- Brain Dump button shows either valid spec files OR a clear error message -- never quality JSON, never conversational text
- All existing chain tests pass without modification (deep-humanize, rewrite-review unaffected)
- Guard does not fire for single-output chains or sidecar steps

---

## Non-Goals

- Making the generate step reliable via prompt changes (that is Port Spec-Doc Template)
- Rendering error states in the GUI
- Adding retry logic to the runner
- Modifying chain definitions

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
