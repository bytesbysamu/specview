# 🔍 Raise max_tokens — Analysis

## The Problem
The CLI provider (`modules/chain/providers/cli.py`) accepts `max_tokens` as a parameter but never forwards the `--max-tokens` flag to the subprocess — every call runs at the CLI binary's default ceiling regardless of what callers request. Long-form generators (implementation guides, architecture step) silently truncate mid-document. No error is raised; the executor writes whatever the model produced and the user has no signal that the output is incomplete.

## Hard Constraints
- CLI binary must support `--max-tokens` before the code change ships; if not, the CLI install is a prerequisite, not optional.
- Provider fix must land in its own PR before any caller passes 16k — a caller change deployed first is a no-op on the live binary.
- Truncation detected → write the file and append a warning (option a). Options b and c are explicitly rejected; the decision is closed.
- `analysis` and `epic` prompts stay at 4096; only the architecture step and impl-guide generation get 16k.
- No direct push to `master` — PR required per repo rules.

## Open Questions
- **`warnings` field in the polling response:** Does `openapi.yaml` already include a `warnings` array on the task-status response? If not, the schema needs updating and DTOs must be regenerated before the Angular badge can consume the field. [Already exists / Needs schema addition / Unknown]
- **`AICall.max_tokens` plumbing:** The brain dump references "Task 1.2" from the bootstrap brain dump for this wiring. Does `AICall` already thread `max_tokens` through to the chain call, or does this epic need to add it? [Already wired / Needs to be added here / Owned by bootstrap epic]
- **Timeout increase:** "increase timeouts by 2x everywhere" — which timeouts, which files, current values? Completely unspecified. [Subprocess timeout in `cli.py` only / HTTP timeout in `adapter.py` / Both / Some other layer]

## Dependencies & Sequencing
- CLI binary `--max-tokens` support → CLI provider code fix → caller changes (strict order; each is a prerequisite for the next).
- `warnings` schema in `openapi.yaml` → DTO regeneration → Angular polling integration (required only if the field is new).
- `AICall.max_tokens` plumbing (bootstrap epic) → architecture-step and task-gen caller changes.

## Explicitly Out of Scope
- **Timeout increase** — no locations, no current values, no acceptance criteria specified; re-scope after a concrete list exists.
- **Streaming output** — `braindump-streaming-task-gen.md` owns this; it supersedes the synchronous fix once shipped.
- **Token-cost accounting** — `braindump-multi-provider-cost-visibility.md`.
- **Anthropic SDK provider** — `max_tokens` already works there; no change needed.
- **Auto-retry on truncation (option b)** — deferred to a future auto-recovery brain dump.