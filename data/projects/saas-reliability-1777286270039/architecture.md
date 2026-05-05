# 🏗️ Solution Architecture: SaaS Reliability

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

This capability adds three orthogonal concerns to `WorkflowRuntime` — cooperative cancellation, streaming partials, and per-step sub-workflows — without forking the existing engine. Every concern is implemented as the smallest possible extension to a domain object that already exists in `modules/runtime/workflows/`. Cancellation is one `if` in the runtime loop; streaming is one boolean field on `AICall` and one rolling-tail accumulator written into `StepContext.outputs["_partials"]`; retry is three sub-workflow registrations in the same `register_workflows(repo)` call site as the main bootstrap workflow. No new state machine, no new domain layer.

The user-facing surface stays on the existing 3-second polling endpoint: `GET /api/ai/text/bootstrap-project/status/{job_id}` gains `current_step`, `partial`, `warnings`, and `error` fields populated from the same `WorkflowExecution` instance the runtime mutates. Angular keeps its current poll loop and renders the new fields. SSE is intentionally absent in v1 — sub-second updates have no consumer yet, and adding a second transport doubles the test surface for a UX delta the brain dump scopes out.

The four features bundle because they are four windows onto the same backbone. Cancellation reads `WorkflowExecution.status`; streaming writes `WorkflowExecution.outputs["_partials"]`; retry constructs new `WorkflowExecution` instances against scoped sub-workflows; the polling endpoint serialises whichever fields are populated. Splitting them into four epics would require four sets of route tests, four Angular component changes, and four runtime patches — bundling them into one capability folds that surface into a single PR.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #1 — Adapter Boundary | Streaming lives inside `modules/runtime/chain/adapter.py` as a new `stream_generate` function; no feature module imports a provider; structural test `featureModules_mustNotImportProvidersDirectly` stays green |
| ELA #4 — Async 202 + Polling | Bootstrap, task_gen, and spec_gen all keep the 202 + `job_id` shape; this epic adds *fields* to the polling response, never a new transport |
| ELA #5 — Not-Yet-Built | Persistent `WorkflowExecution`, mid-step cancellation, and SSE are deferred until a named consumer exists; in-process dict and cooperative cancel are the concrete shapes |
| ELA #6 — Workflow Domain Layer | Four new workflows (`bootstrap-project` consumer migration plus three `bootstrap-*-only` sub-workflows) ship under `modules/ai/workflows/spec_gen/`; no orchestration in route handlers |
| ELA #7 — In-Process State | `_BOOTSTRAP_JOBS: dict[str, WorkflowExecution]` keyed by `job_id`; purge-on-first-done-read; matches the existing `task_gen` STATE pattern |

---

## System Boundaries

### What This System Includes

- One-line cancellation read in `modules/runtime/workflows/runtime.py`
- `stream: bool` field on `modules/runtime/workflows/steps/ai_call.py` and a `_partial_callback` plumbing through `StepContext`
- New `stream_generate` function on `modules/runtime/chain/adapter.py` and on the SDK provider
- Three sub-workflow registrations under `modules/ai/workflows/spec_gen/` (`bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`)
- Cancel and retry routes for bootstrap and task_gen under `modules/ai/routes/text.py` and `modules/ai/routes/task_gen.py`
- Polling response shape extension: `current_step`, `partial`, `warnings`, `error`
- Truncation heuristic helper in `modules/quality/` populating `execution.warnings`
- Angular live-preview `<pre>`, Cancel button, Regenerate button on `web/src/app/components/new-project/`

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| DB-backed `WorkflowExecution` persistence | Single-user dev pattern; in-process is sufficient until a multi-process worker tier is named |
| Mid-step cancellation (interrupt in-flight `generate`) | Requires subprocess kill / SDK abort; race-y; defer |
| SSE / WebSocket transport | Phase 2 lever for sub-second updates; existing 3s polling covers all four features |
| CLI provider streaming | CLI is dev-only after the SDK provider lands; no consumer |
| Auto-retry on transient failures | Anthropic SDK `max_retries=2` covers HTTP transients at the right layer |
| Composite step kind (workflow-of-workflows) cancellation propagation | Workflows epic Phase 2; no Composite consumer today |
| Cancellation deadline / orphan-cleanup TTL | Cost case is user-initiated; abandoned-tab cleanup is speculative |
| Per-token cost tracking during streaming | multi-provider-cost-visibility brain dump owns mid-stream tokens |
| Diff view between original and regenerated content | Persistence brain dump owns it via two SHAs |
| New `WorkflowExecution` status values | The existing seven (`NEW`, `IN_PROGRESS`, `COMPLETED`, `ERROR`, `TIMEOUT`, `CANCELLING`, `CANCELLED`) cover every new transition |

---

## Component Design

### Cancellation Read in `WorkflowRuntime`

**Purpose**: Honour the existing `WorkflowExecution.request_cancel()` API by reading `execution.status` between every step.

**Key Parts**:

- `WorkflowRuntime.run` — adds one `if execution.status is ExecutionStatus.CANCELLING: execution.cancel(); return` at the top of each iteration of `for step in workflow.steps`
- `WorkflowExecution.cancel()` — already exists; transitions `CANCELLING → CANCELLED`; the runtime is now the named consumer
- Per-feature `cancel` route — calls `execution.request_cancel()`; status flips on the next step boundary

**Patterns**: Cooperative cancellation (Pattern from POSIX threads); the runtime polls a flag rather than receiving a signal. Named consumer for `request_cancel()` is `WorkflowRuntime`; named consumer for `cancel()` is the runtime's between-steps check.

**Why this shape**: Mid-step cancellation requires subprocess kill or SDK abort plumbing; both are race-y and have no current SLA driving them. Cooperative cancellation is one `if` and bounds latency to one full step (already known at workflow design time). The state machine already exists — adding a new transition surface would duplicate it.

---

### Streaming Partial Buffer in `AICall`

**Purpose**: Surface a rolling tail of in-flight model output without changing the HTTP transport.

**Key Parts**:

- `AICall.stream` — frozen Pydantic field, default `False`; opt-in per step
- `AICall._invoke` — when `stream=True`, calls `chain_adapter.stream_generate(...)`, accumulates chunks into a list, slices the rolling 500-char tail, and writes it to `context.outputs["_partials"][self.name]` after each chunk
- `chain_adapter.stream_generate(system, prompt, *, model, max_tokens) -> Iterator[str]` — new public function on the adapter; routes to the SDK provider's streaming method; CLI provider raises `NotImplementedError` (CLI is dev-only after SDK lands)
- `StepContext.outputs["_partials"]: dict[str, str]` — dict-of-step-name → rolling tail; the polling endpoint reads `_partials[execution.current_step_name]` (where `current_step_name` is derived from the most recent `StepStarted` event)
- Bootstrap architecture step opts in (`stream=True`) — longest of the three (16k tokens), highest UX value

**Patterns**: Producer/consumer (the AI call produces chunks; the polling endpoint consumes the tail); rolling buffer (fixed 500-char window keeps the response payload bounded). Named consumers: the polling endpoint reads the tail; Angular's `<pre>` block renders it.

**Why this shape**: The 500-char tail is the smallest payload that gives a useful preview (last paragraph ish). Per-step opt-in (rather than workflow-level) keeps short steps from paying streaming overhead. Routing through `StepContext.outputs` (rather than a sidecar) keeps the runtime ignorant of streaming — the runtime just iterates steps; only `AICall._invoke` knows about chunks.

---

### Per-Step Sub-Workflows for Retry

**Purpose**: Enable an architecture-only retry that pays for one AI call, not three, by registering scoped sub-workflows alongside the main `bootstrap-project` workflow.

**Key Parts**:

- `modules/ai/workflows/spec_gen/bootstrap.py` — already registers `bootstrap-project` (analysis → epic → architecture → marshal_files); extends `register_workflows(repo)` to also register `bootstrap-analysis-only`, `bootstrap-epic-only`, and `bootstrap-architecture-only`
- `bootstrap-analysis-only` — single `AICall` step; inputs `(braindump, project_name, builder)`; outputs `analysis`
- `bootstrap-epic-only` — single `AICall` step; inputs include `analysis` from prior run; outputs `epic`
- `bootstrap-architecture-only` — single `AICall(stream=True)` step; inputs include `analysis`, `epic`; outputs `architecture`
- Retry route — `POST /api/ai/text/bootstrap-project/{job_id}/retry` reads the prior `WorkflowExecution.outputs`, constructs a new execution against the named sub-workflow, returns a fresh `job_id`
- `task_gen` regenerate — `POST /api/ai/text/generate-task/{project_id}/regenerate-task` deletes the prior generated task file and re-runs the `task_gen` workflow with the same `task_num`

**Patterns**: Sub-workflow as facade (each `bootstrap-*-only` is a one-step Workflow that satisfies the same `WorkflowProtocol` as the multi-step parent); workflow registry as discovery (no central edit when new sub-workflows are added — they register from the same `register_workflows(repo)` call). Named consumer for each sub-workflow is the retry route.

**Why this shape**: Sub-workflows reuse the existing `Workflow` aggregate, runtime, repository, and step kinds. No new mechanism. Cost amortisation is the user-visible value — one click, one AI call, instead of paying for analysis + epic the user already accepted.

---

### `_BOOTSTRAP_JOBS` Job Registry

**Purpose**: Hold `WorkflowExecution` instances for the three minutes between async start and the first done-read.

**Key Parts**:

- `_BOOTSTRAP_JOBS: dict[str, WorkflowExecution]` — module-level dict in `modules/ai/routes/text.py`; already exists from the bootstrap-async work; this epic widens its surface (cancel, retry, status-with-partial)
- Purge-on-first-done-read — `bootstrap_status` pops the entry once `execution.is_terminal` is read for the first time; matches the consumer pattern (Angular reads, navigates)
- Threading model — `daemon=True` thread per execution; matches the existing `task_gen` pattern; no new threading primitives
- Concurrent access — Python's GIL plus dict atomicity is enough; status reads are single attribute lookups; no `_LOCK` required for the new fields (matches the existing dict's behaviour)

**Patterns**: In-process state per ELA #7; module-level dict keyed by `job_id` (UUID). Named consumers: `bootstrap_status`, `bootstrap_cancel`, `bootstrap_retry`.

**Why this shape**: The dict is the same shape `task_gen` already uses. Persistence (DB-backed `WorkflowExecution`) is a Phase 2 trigger when multi-worker deployment is named — it's a binding change against `WorkflowRepository`, not a feature change.

---

### Truncation Heuristic for `warnings`

**Purpose**: Detect malformed step output (unclosed code fence, suspiciously short text) and populate `WorkflowExecution.warnings` so the regenerate trigger can fire automatically in the Angular surface.

**Key Parts**:

- `modules/quality/truncation.py` (new) — pure function `detect_truncation(output: str) -> list[str]`; returns one warning string per heuristic that fired
- Heuristics — unclosed code fence (count of triple-backticks is odd), suspiciously short (< 200 chars when `max_tokens >= 4096`), missing terminal newline on a markdown doc
- `WorkflowExecution.warnings: list[str]` — new field added to the existing `WorkflowExecution` dataclass; default `[]`; mutated by the runtime after each successful step
- Runtime hook — after `step.execute(context)` succeeds, call `detect_truncation(context.outputs[step.name].text)` and extend `execution.warnings`

**Patterns**: Strategy (each heuristic is a callable; the list is iterated); single-writer (only the runtime writes to `warnings`). Named consumers: polling endpoint reads `warnings`; Angular regenerate button conditions on `warnings.length > 0`.

**Why this shape**: Truncation is a per-step concern (one bad step shouldn't poison neighbours), but warnings accumulate per-execution (the user wants one regenerate-pivot view, not per-step badges). The heuristic lives in `modules/quality/` so future quality checks (lint, structural) compose with it.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Workflow runtime | Existing `WorkflowRuntime` from `modules/runtime/workflows/` | Backbone is shipped; this epic extends, never duplicates |
| Cancellation | Cooperative between-steps check on `execution.status` | One `if`, bounded latency; mid-step is race-y and has no SLA |
| Streaming | Anthropic SDK `messages.stream` via new `chain_adapter.stream_generate` | SDK is the prod provider per `versions.md`; CLI is dev-only and stays non-streaming |
| Job storage | `dict[str, WorkflowExecution]` in `modules/ai/routes/text.py` | Matches the existing `task_gen` STATE pattern; ELA #7 (in-process state) |
| Polling transport | Existing `GET /api/ai/text/bootstrap-project/status/{job_id}` | No new transport; adds fields, not endpoints |
| Truncation detection | Pure-Python heuristics in `modules/quality/truncation.py` | Composes with existing `lint_task_guide()` quality module |
| Angular state | Signals + the existing 3-second poll loop in `new-project.component.ts` | No new service, no new transport; only render layer changes |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Cooperative cancellation, not preemptive | Mid-step requires subprocess kill / SDK abort; both are race-y and have no SLA driving them; cooperative is one `if` and bounds latency to one full step | Cancelling during the 16k-token architecture step still waits for that step to finish (~3-9 minutes); acceptable because the user accepts the trade explicitly when they click Cancel during a long step |
| Per-step streaming opt-in via `stream: bool` field | Short steps (analysis, epic at 4k tokens) finish in <30s — streaming overhead is wasted; opt-in keeps the cost local to the step that benefits | Workflow authors must remember to flip the flag on long steps; mitigated because only architecture and impl-guide cross the threshold today |
| Rolling 500-char tail, not full buffer | Polling response payload stays bounded regardless of step output size; matches what the user can actually read in a `<pre>` window | Last 500 chars of a 16k-token output may cut a sentence mid-word; the user sees "live progress", not full-document scrub |
| Per-step sub-workflows for retry, not partial-state replay | Sub-workflows reuse the entire workflow + runtime + repository machinery; partial-state replay would add a new "resume from step N" code path with its own bugs | Three extra workflow registrations under `bootstrap.py`; harmless because they share the same prompt constants |
| In-process `_BOOTSTRAP_JOBS` dict, purge on first done-read | Single-user dev pattern; matches `task_gen` STATE; ELA #7; no Redis | Job is lost if the process restarts mid-execution — acceptable because the user can re-bootstrap (the brain dump is still in their tab) |
| Cancel counts as a usage call (no refund) | Metering decorator only charges on `< 400` responses; the original 202 already counted; pro-rate later if needed | A user who cancels at second 1 still loses one bootstrap call; mitigated because the daily free-tier cap is 3 — one wasted slot on intentional cancel is in noise |
| Truncation heuristic in `modules/quality/`, not in the runtime | Future quality checks (structural lint, citation check) compose with it; the runtime stays a control-flow engine, not a content judge | Two reads of step output (runtime to mirror onto `execution.outputs`, then truncation check) — negligible cost on text payloads |
| No SSE in v1 | Sub-second updates have no consumer yet; adding a second transport doubles the test surface; 3s polling already drives all four features | Live preview updates at 3-second granularity, not per-chunk; matches the brain dump's explicit "rolling 500-char tail surfaced via existing 3-second polling endpoint" |

---

## Execution Flow

```
Bootstrap async path (Task 3 + Task 4)
─────────────────────────────────────
  POST /api/ai/text/bootstrap-project
    ↓
  WorkflowExecution(workflow_ref="spec_gen/bootstrap-project", inputs={...})
    ↓
  _BOOTSTRAP_JOBS[job_id] = execution; threading.Thread(target=_run).start()
    ↓
  return 202 + {"job_id": ...}

  Background thread:
    WorkflowRuntime.run(execution, workflow) →
      for step in workflow.steps:
        if execution.status is CANCELLING: execution.cancel(); return
        for event in step.execute(context):  # AICall(stream=True) writes _partials[step.name]
          ...
        execution.warnings += detect_truncation(context.outputs[step.name])

  Polling: GET /api/ai/text/bootstrap-project/status/{job_id}
    → {running, done, current_step, partial, warnings, error[, files]}
    → on first done-read: _BOOTSTRAP_JOBS.pop(job_id)

Cancel path
───────────
  POST /api/ai/text/bootstrap-project/{job_id}/cancel
    ↓
  execution.request_cancel()  # IN_PROGRESS → CANCELLING
    ↓
  return 202; runtime sees CANCELLING on next step boundary

Retry path
──────────
  POST /api/ai/text/bootstrap-project/{job_id}/retry  body={"step": "architecture"}
    ↓
  prior = _BOOTSTRAP_JOBS.get(job_id)  # contains analysis + epic outputs
    ↓
  new_inputs = {**prior.inputs, "analysis": prior.outputs["analysis"].text, "epic": prior.outputs["epic"].text}
    ↓
  new_execution = WorkflowExecution(workflow_ref="spec_gen/bootstrap-architecture-only", inputs=new_inputs)
    ↓
  return 202 + {"job_id": new_id}
```

---

## Open Questions

Two minor knobs remain; both have a default chosen and a re-decision trigger named, so neither blocks any task.

- Job TTL — purge-on-first-done-read (chosen) vs cap-50 LRU vs 1-hour TTL — re-decide if a second polling client appears (e.g. CLI tool reading the same job)
- Streaming opt-in surface — per-step `stream=True` flag (chosen) vs workflow-level toggle — re-decide when a third long step (>4k tokens) joins architecture and impl-guide and the flag becomes per-workflow boilerplate

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview

---

**Length budget**: target ≤ 250 lines including all tables. If you need more, the architecture is doing too much — split into a follow-on capability.
