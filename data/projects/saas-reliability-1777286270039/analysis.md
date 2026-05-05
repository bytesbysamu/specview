# 🔍 SaaS Reliability — Analysis

## The Problem

Long-running AI generations today either burn the user (no progress, no cancel, lost spend on timeout) or burn the host (proxies, load balancers, OS connection-tracking kill 25-min HTTP holds regardless of gunicorn's 3600s ceiling). `bootstrap-project` already fixed the first half by returning 202 + `job_id`, but the runtime substrate is hand-rolled in the route — it cannot stream partials, retry a single step, or honour `WorkflowExecution.request_cancel()`. Four operational capabilities now share the same backbone (`WorkflowRuntime` + `WorkflowExecution` + 3-second polling) and ship as one capability so the testing and Angular wiring amortise.

## Hard Constraints

- `WorkflowRuntime` and `WorkflowExecution` from `modules/runtime/workflows/` are the backbone — no parallel state machine. Workflows epic shipped both; this capability extends, never duplicates.
- `WorkflowExecution.request_cancel()` already exists; the runtime loop must read it cooperatively (between steps, never mid-`generate`).
- No SSE in v1 — the existing 3-second polling endpoint is the only client transport. SSE is a Phase 2 lever for sub-second updates.
- Job storage is in-process (`_BOOTSTRAP_JOBS: dict[str, WorkflowExecution]`), purged on first done-read. No Redis, no DB. Matches ELA #7 (in-process state).
- Module placement per modular-restructure: workflow-runtime extensions (cancellation read, streaming flag) live under `api/modules/runtime/workflows/`; per-feature workflow definitions and route handlers under `api/modules/ai/workflows/{bootstrap,task_gen,spec_gen}/` and `api/modules/ai/routes/`.
- Streaming relies on Anthropic SDK `stream_generate`; the CLI provider stays non-streaming (CLI is dev-only after the SDK provider lands).
- Cancellation refund: cancel counts as a usage call (no refund) — the metering decorator only charges on `< 400` responses, but the original 202 already counted; pro-rate later if needed.
- Cancellation latency budget: at most one full step (cooperative; in-flight `chain_adapter.generate()` completes).
- Path convention: `api/X` (never `flask/X`); commit signing via `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.

## Open Questions

All decisions baked into the brain dump are settled; the two leftover knobs below are noted only so a re-decision trigger is recorded.

- Job TTL — purge-on-first-done-read (chosen) vs cap-50 LRU vs 1-hour TTL. Re-decide if a second polling client appears (e.g. CLI tool reading the same job).
- Streaming opt-in surface — per-step `stream=True` flag on `AICall` (chosen) vs workflow-level toggle. Re-decide when a third long step (>4k tokens) joins architecture and impl-guide and the flag becomes per-workflow boilerplate.

## Dependencies & Sequencing

- Cooperative cancellation is the prerequisite for retry: a partial-but-cancelled execution must be readable from `_BOOTSTRAP_JOBS` for the user's regenerate decision.
- Streaming buffer requires the rolling-tail callback in `StepContext` before any feature opts in via `stream=True`.
- Per-step sub-workflows (`bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`) ship alongside the main `bootstrap-project` workflow — same registration site, no separate epic.
- `task_gen` and `spec_gen` (already 202 + polling) inherit streaming, retry, and cancel for free once the runtime gains those capabilities.

## Explicitly Out of Scope

- Persistent job storage (DB-backed `WorkflowExecution`) — single-user dev pattern; in-process is sufficient until a multi-process worker tier is named.
- Mid-step cancellation (interrupting an in-flight `generate()` call) — race-y; requires subprocess kill / SDK abort; defer.
- WebSocket / `text/event-stream` transport — polling is enough for 3s updates; SSE is a Phase 2 lever paired with sub-second progress.
- CLI provider streaming — CLI is dev-only after the SDK provider lands; no consumer.
- Auto-retry on transient failures — explicit user click only; SDK's `max_retries=2` covers HTTP transients at the right layer.
- Cancellation propagation to sub-workflows (Composite step kind) — Phase 2 of the Workflows epic; no Composite consumer today.
- Cancellation deadline / orphan-cleanup TTL — defer; cost case is user-initiated, not abandoned-tab.
- Per-token cost tracking during streaming — token counts arrive end-of-stream; mid-stream is a different surface (multi-provider-cost-visibility owns it).
- Diff view between original and regenerated content — `git diff` between two SHAs is one endpoint away in the persistence epic.
