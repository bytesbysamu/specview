---
sidebar_position: 1
---

# Analysis -- Chain Runner Fix

**Purpose**: Surface root cause, constraints, and resolved decisions before scoping the fix.

**Date**: 2026-04-17

---

## Problem

The chain runner's step loop unconditionally overwrites `current_text` with every step's output (line 246: `current_text = result.text`). Steps with `outputKey` -- designed as sidecar operations that produce metadata without altering the pipeline's main data flow -- still replace the pipeline input. The `braindump-to-docs` chain is the most visible victim: the user sees quality-score JSON instead of generated spec files because Step 3 (review with `outputKey: "score"`) overwrites the generated output from Step 2.

## Hard Constraints

- **Chain adapter is the only Claude boundary** -- the fix lives entirely in the runner and DTO layers; no changes to `adapter.py` or provider code.
- **Existing chains must not regress** -- `deep-humanize` (no `outputKey`) and `rewrite-review` (no `outputKey`) must produce identical results before and after the fix.
- **`outputKey` semantics are already declared in chain definitions** -- the JSON schema already supports `outputKey` on steps; the runner just ignores it. No definition changes needed.
- **Observer event shape is stable** -- `chainCompleted` signal already emits `{ chainId, stepCount, inputLength, outputLength, totalTokens }`. Adding `meta` to the run result does not change the signal payload.
- **OpenAPI YAML is source of truth** -- `ChainResponse` DTO changes must be reflected in the OpenAPI spec and both-sides DTOs regenerated.

## Open Questions (resolved)

| Question | Resolution | Rationale |
|---|---|---|
| Should sidecar results be returned to the frontend? | Yes -- add `meta: dict[str, str]` to `ChainRunResult` and `ChainResponse`. | The braindump says "return them in the response as `{ result, files, meta: { lint: {...}, score: {...} } }` so the frontend can choose to display or ignore." The UI already has a tabbed output component; sidecars could be additional tabs with a "meta" badge. |
| Should `outputKey` steps receive `user_input` or `current_text`? | `current_text` (the output of the most recent non-sidecar step, or `user_input` if none). | This preserves the sequential pipeline contract: each step sees the output of the last step that contributed to the main flow. For `braindump-to-docs`, Step 1 (lint) receives `user_input` via `current_text` and sidecars its result; Step 2 (generate) also receives `user_input` because no non-sidecar step has run yet; Step 3 (score) receives Step 2's output (the generated specs), which is the text that should be scored. |
| Does fix-mode injection need changes? | No. Fix-mode (`step.mode == "fix"`) looks back at `step_outputs[i-1]` and `step_outputs[i-2]`. Sidecar steps still append to `step_outputs`, so indices are stable. The fix-injection logic reads the correct prior outputs regardless. |
| Should `meta` values be strings or parsed JSON? | Strings. The runner stores `result.text` (raw LLM output) in `meta[outputKey]`. Parsing review JSON is the frontend's responsibility -- or a future enhancement. Keeping it as strings avoids adding a JSON-parse failure mode in the runner. |

## Dependencies

| Dependency | Status | Location |
|---|---|---|
| Chain runner (`definition_runner.py`) | Shipped (buggy) | `server/modules/chain/definition_runner.py` |
| Chain definitions with `outputKey` | Shipped | `server/modules/chain/definitions/braindump-to-docs.json` |
| `ChainRunResult` dataclass | Shipped (missing `meta`) | `server/modules/chain/definition_runner.py` line 186 |
| `ChainResponse` DTO (Pydantic) | Shipped (missing `meta`) | `server/modules/text/chain_dto.py` line 24 |
| `ChainResponse` interface (frontend) | Shipped (missing `meta`) | `src/app/mocks/chain.mock.ts` line 1 |
| Chain service (`chain_service.py`) | Shipped (doesn't forward `meta`) | `server/modules/text/chain_service.py` |
| Text Chains epic (parent) | Done | [Text Chains spec set](../text-chains-1776379250140/spec-index.md) |

## Explicitly Out of Scope

- UI rendering of sidecar `meta` data (collapsible panels, badge tabs) -- separate UX task after the data plumbing ships
- Retry/backoff on sidecar step failures -- deferred infrastructure per Engineering Discipline
- Structured parsing of review JSON in the runner -- frontend responsibility
- Changes to `chainCompleted` signal payload -- `meta` is a response-layer concern, not an analytics concern
- Changes to chain definitions -- the JSON is already correct; only the runner interpretation is wrong

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
