# 🎯 Epic: SaaS Reliability

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Real users will hit every one of these failure modes the moment paid API spend lands. Bootstrap timeouts cost ~25 minutes of wall-clock time and the entire chain's API spend; spec-gen timeouts cost 6–9 minutes; truncation silently ships broken docs that the user only discovers when they open the file. Without retry-recovery the only fix is "kick off a fresh chain at full cost". Without cancellation, a runaway 25-minute chain cannot be aborted. The cost of *not* shipping these is one funded support ticket per user per week and a measurable share of the org's API budget burned on chains the user already abandoned.

The four features bundle because they share the same backbone (`WorkflowRuntime` + `WorkflowExecution` + the existing 3-second polling endpoint). Splitting them across four epics duplicates the test scaffolding, the Angular wiring, and the runtime extension points; bundling amortises every line of those costs across four real consumer cases. None of the four is large alone (~4 hours each); together they are two days of focused work whose surface area is the same in either grouping.

The longer-term value is a runtime that absorbs every future long-running AI feature for free. Once cancellation, streaming, and per-step retry are runtime concerns, every new workflow inherits them by definition — the next consumer (impl-guide-stream, multi-spec batch) writes zero reliability code.

**Value Proposition**: Make every long-running AI generation in spec-doc cancellable, recoverable, and visibly progressing — without inventing a parallel state machine per feature.

---

## Scope

### What This Epic Covers

- **Bootstrap async via WorkflowRuntime** — the inline three-call orchestration in `ai/routes/text.py` is replaced by a `bootstrap-project` workflow run through `WorkflowRuntime`; the route only constructs `WorkflowExecution` and polls.
- **Streaming partial buffer** — opt-in `stream=True` on `AICall` accumulates chunks; the rolling 500-char tail is surfaced through the existing 3-second polling response as a `partial` field.
- **Per-step retry / regenerate** — the bootstrap workflow ships alongside three sub-workflows (`bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`) so an architecture-only retry costs one AI call, not three; `task_gen` regenerate is the equivalent for task guides.
- **Cooperative cancellation** — `WorkflowRuntime.run` reads `execution.status == CANCELLING` between every step and transitions to `CANCELLED`; per-feature `cancel` routes call `execution.request_cancel()`.
- **Angular surface** — live `<pre>` partial preview, "Cancel" button next to the spinner, "Regenerate" button on any spec file with `size === 0`, `warnings.length > 0`, or `error != null`.

### What This Epic Does NOT Cover

- ❌ Persistent job storage (DB-backed `WorkflowExecution`) — in-process is sufficient until a multi-process worker tier is named
- ❌ Mid-step cancellation — requires subprocess kill / SDK abort; race-y; defer
- ❌ SSE / WebSocket transport — Phase 2 lever for sub-second updates; existing 3s polling is enough
- ❌ CLI provider streaming — CLI is dev-only after the SDK provider lands
- ❌ Auto-retry on transient failures — SDK `max_retries=2` covers HTTP transients; user-initiated retry is the only kind here
- ❌ Cancellation propagation to sub-workflows (Composite step kind) — Workflows epic Phase 2
- ❌ Per-token cost tracking during streaming — multi-provider-cost-visibility brain dump owns it
- ❌ Diff view between original and regenerated content — persistence brain dump owns it via two SHAs

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Cooperative Cancellation in WorkflowRuntime** | None | — | 0.3 days | High |
| 2 | **Streaming Partial Buffer in AICall** | None | Task 1 | 0.5 days | High |
| 3 | **Bootstrap Workflow + Per-Step Sub-Workflows** | Task 1 | Task 2 | 0.5 days | High |
| 4 | **Retry, Regenerate, Cancel Routes + Polling Surface** | Tasks 1, 2, 3 | — | 0.4 days | High |
| 5 | **Angular Live Preview, Cancel, Regenerate** | Task 4 | — | 0.3 days | High |

### Task 1: Cooperative Cancellation in WorkflowRuntime

Wire the existing `WorkflowExecution.request_cancel()` into the runtime loop. Between every step iteration the runtime checks `execution.status == ExecutionStatus.CANCELLING` and, if so, calls `execution.cancel()` and returns. No mid-step interruption — the in-flight `chain_adapter.generate()` completes; cancellation latency is at most one full step.

**Port budget**: One `if` in `runtime.py`, four runtime tests covering the cancel-between-steps path, no new modules.

### Task 2: Streaming Partial Buffer in AICall

Add a `stream: bool = False` field to `AICall`. When `True`, `_invoke` calls `chain_adapter.stream_generate(...)`, accumulates chunks, and pushes a rolling 500-char tail through a `_partial_callback` keyed by step name on `StepContext.outputs["_partials"]`. The route's polling response surfaces `_partials[current_step_name]` as `partial`. CLI provider keeps the synchronous path (CLI is dev-only after the SDK provider lands).

**Port budget**: One field on `AICall`, one provider method (`stream_generate`) on the SDK provider, one rolling-tail accumulator, polling response surfaces `partial`.

### Task 3: Bootstrap Workflow + Per-Step Sub-Workflows

The existing `_run_bootstrap_thread` orchestration in `ai/routes/text.py` is replaced by `WorkflowRuntime.run()` over the existing `spec_gen/bootstrap-project` workflow (already shipped). Three new sub-workflows ship alongside: `bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`. Each sub-workflow accepts the prior outputs as inputs so an architecture-only retry pays for one call, not three. Architecture step opts into `stream=True` (longest, most useful preview).

**Port budget**: Four workflow registrations under `modules/ai/workflows/spec_gen/`; route handler now drains the runtime generator instead of calling `bootstrap_*_prompt` inline. No new prompt constants — sub-workflows reuse `BOOTSTRAP_ARCHITECTURE_USER` etc.

### Task 4: Retry, Regenerate, Cancel Routes + Polling Surface

Add three routes per affected feature: `POST /bootstrap-project/{job_id}/cancel`, `POST /bootstrap-project/{job_id}/retry`, and the equivalent for `task_gen` (`POST /generate-task/{project_id}/cancel`, `POST /generate-task/{project_id}/regenerate-task`). Polling response gains `current_step`, `partial`, `warnings`, and `error` fields. Truncation heuristic (unclosed code fence, suspiciously short output) populates `execution.warnings` after each step completes — feeds the regenerate trigger.

**Port budget**: Six new routes total (three for bootstrap, three for task_gen mirror), one truncation helper in `modules/quality/`, polling response shape updated.

### Task 5: Angular Live Preview, Cancel, Regenerate

`new-project.component.ts` adds a `<pre>` block showing `partial` while running, a red "Cancel" button next to the spinner that flips to "Cancelling…" until status flips to `CANCELLED`, and a "Regenerate" button on any spec file with `size === 0`, `warnings.length > 0`, or `error != null`. Existing 3-second poll loop already drives all four; only the rendering changes.

**Port budget**: One component, two new buttons, one `<pre>` block; no new service methods (existing `AiService.bootstrapStatus()` already covers polling).

---

## Success Criteria

- ✅ `bootstrap-project` route handler contains zero inline AI calls — only `WorkflowRuntime.run()` drain logic
- ✅ Cancelling a 25-minute bootstrap returns within at most one step duration; `WorkflowExecution.status` ends in `CANCELLED`
- ✅ Architecture-only retry consumes exactly one AI call (verified by mock chain adapter call-count assertion)
- ✅ Polling response carries non-empty `partial` field within the first chunk after `stream=True` is enabled on the architecture step
- ✅ The structural test `featureModules_mustNotImportProvidersDirectly` remains green throughout — streaming is added inside `chain.adapter`, not at call sites
- ✅ Zero new state machines: `WorkflowExecution`'s status enum is the only lifecycle store across all four features
- ✅ Angular renders live progress, cancel, and regenerate without a new HTTP transport (still 3-second polling)

---

## Non-Goals

- ❌ DB-backed `WorkflowExecution` persistence — explicit Phase 2 trigger is multi-worker deployment
- ❌ SSE transport — Phase 2 lever; 3s polling is the v1 surface
- ❌ Mid-step interruption — race-y; SDK abort is a separate epic
- ❌ Auto-retry on transient errors — SDK retries handle HTTP transients; only user-initiated retry here
- ❌ Per-token cost during streaming — multi-provider-cost-visibility brain dump owns it
- ❌ `chain.adapter` rename or signature widening — separate cleanup epic
- ❌ Cancellation refund / pro-rated billing — cancel counts as a usage call; pro-rate later if needed

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
