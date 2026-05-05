# 🏗️ Solution Architecture: Bootstrap Async

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The core insight is that a held HTTP connection is not a configuration problem — it is a structural one. No gunicorn timeout, Angular `timeout()` operator, or proxy tuning can prevent infrastructure the application does not own from terminating a connection that has been open for 25 minutes. The only fix is to eliminate the held connection entirely. The POST returns a job ID in milliseconds; a background thread owns the chain; Angular polls a status endpoint until the job resolves. There is no long-lived connection to kill.

This architecture reuses `WorkflowRuntime` + `WorkflowExecution` wholesale, making bootstrap the third consumer of the same pattern proven by `task_gen` and `spec_gen`. That reuse is not incidental — it means bootstrap inherits `WorkflowExecution`'s state machine, its status transitions, and the test coverage built for those two prior consumers rather than reinventing a parallel implementation. The only new artifacts are the workflow definition, two route handlers, and the Angular polling client.

The lifetime boundary between the in-process job registry (`_BOOTSTRAP_JOBS`) and `WorkflowExecution` is a deliberate design choice. The dict owns only one thing: whether the job is reachable. `WorkflowExecution` owns all state. This keeps the registry trivially simple — it has no status logic to get wrong — and means the status endpoint is always reading from a single authoritative source.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Eliminate the structural failure mode, not the symptom | Replace the held connection; do not raise another timeout ceiling |
| Reuse proven infrastructure | `WorkflowRuntime` + `WorkflowExecution` carry test coverage from two prior consumers; bootstrap inherits rather than reinvents |
| Single source of truth for state | `WorkflowExecution`'s state machine is the only status authority; the job registry is a lifetime handle, not a second status dict |
| Purge on first terminal read | The consumer reads exactly once after completion; eviction on that read keeps the registry bounded without a TTL background process |
| Hard cutover, no flag | The old shape's failure mode is silent connection termination, not slowness; preserving it behind a flag preserves broken behavior |

---

## System Boundaries

### What This System Includes

- **`BOOTSTRAP_WORKFLOW` definition** — four-step workflow registered under `spec_gen/bootstrap-project`; wraps the existing bootstrap prompt functions as `AICall` steps with a `Compute` step for file marshalling
- **Async POST handler** — issues a 202 with a `job_id`, registers the execution in `_BOOTSTRAP_JOBS`, and dispatches a daemon thread through `WorkflowRuntime`
- **Status endpoint** — reads `WorkflowExecution` state and surfaces `running`, `done`, `files`, `error`, and `latencyMs`; evicts the job on the first terminal read
- **In-process job registry** — `_BOOTSTRAP_JOBS` dict at module scope in `modules/ai/routes.py`; sole responsibility is lifetime management
- **OpenAPI contract update** — revised POST response shape, new status path, `BootstrapJobStatus` schema, regenerated DTOs
- **Angular polling client** — `startBootstrapProject` and `getBootstrapStatus` in `ai.service.ts`; start-then-poll loop in `new-project.component.ts`

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| SSE progress streaming for bootstrap | Covered by `braindump-streaming-task-gen.md`; the `partial` field arrives via that epic once it lands |
| Persistent job storage | Single-user dev tool; in-process is sufficient; `WorkflowExecutionStore` adapter path is deferred until multi-user deployment is scoped |
| Cancellation surface | `WorkflowExecution.request_cancel()` exists but the runtime does not check between steps; wiring requires a user-facing abort UX first |
| `chain.adapter` promotion to first-class infrastructure | Three consumers is the named trigger for that promotion; it is a follow-on epic |
| `chain.adapter.generate` max_tokens default | Handled by `braindump-raise-max-tokens.md` |
| Shared workflow definition with `spec_gen/generate-spec` | Prompt constants may be shared; the workflows serve different step shapes and are not merged |
| Feature flag for the synchronous shape | The old shape's failure is silent connection termination, not degraded performance; there is nothing useful to preserve |

---

## Component Design

### `BOOTSTRAP_WORKFLOW`
**Purpose**: Encodes the four-phase bootstrap chain as a typed, replayable workflow that `WorkflowRuntime` can execute without knowing anything about bootstrap semantics.

**Key Parts**:
- `AICall("analysis")` — runs the analysis prompt; input keys are `braindump`, `project_name`, `builder`
- `AICall("epic")` — runs the epic prompt; adds `principles` to inputs
- `AICall("architecture")` — runs the architecture prompt; adds `codebase` and `references`; carries `max_tokens=16384` because the architecture step is where truncation occurs today
- `Compute("files")` via `bootstrap.marshal_files` — converts the three `AICall` outputs into the `BootstrapFile` list that the status endpoint surfaces

**Patterns**: Command pattern (each step is a self-describing unit of work); `Compute` step as pure data transformation with no I/O side effects.

**Consumer**: `WorkflowRuntime`, invoked from the async POST handler's daemon thread.

---

### Async POST Handler
**Purpose**: Decouples the HTTP lifecycle from the chain execution lifetime. The request returns in milliseconds regardless of chain duration.

**Key Parts**:
- `BootstrapProjectRequest` DTO — validates and normalizes the incoming payload; falls back to context-loaded values for optional fields
- `WorkflowExecution` construction — created before thread dispatch so that `_BOOTSTRAP_JOBS` registration and thread start are atomic from the caller's perspective
- Daemon thread — marked daemon so it does not block process shutdown; `WorkflowRuntime` handles step failures internally; the outer thread function calls `execution.fail()` only for failures outside the chain (e.g., context-loading I/O errors)

**Patterns**: Fire-and-forget with a handle (202 + job ID); the handle is the only coupling between the HTTP layer and the background execution.

**Consumer**: `new-project.component.ts` via `ai.service.startBootstrapProject`.

---

### Status Endpoint
**Purpose**: Gives the Angular polling client a stable read surface over `WorkflowExecution` state without exposing the execution object directly.

**Key Parts**:
- `_BOOTSTRAP_JOBS.get(job_id)` — 404 if the job is unknown or already evicted; this is the expected response after a successful first terminal read
- State projection — maps `ExecutionStatus` enum values to the `BootstrapJobStatus` wire shape; `files` and `latencyMs` are present only on `COMPLETED`; `error` is present only on `ERROR`
- Purge-on-first-read — `_BOOTSTRAP_JOBS.pop(job_id, None)` executes on the first response where `done` is true; subsequent polls receive 404, signalling that the result has been consumed

**Patterns**: Read-once resource; the consumer is responsible for caching the response before navigating away.

**Consumer**: `new-project.component.ts` via `ai.service.getBootstrapStatus`.

---

### In-Process Job Registry (`_BOOTSTRAP_JOBS`)
**Purpose**: Provides a reachability handle from the status endpoint to the `WorkflowExecution` for an in-flight or just-completed job. It owns nothing else.

**Key Parts**:
- Module-scope dict in `modules/ai/routes.py` — co-located with both handlers that use it
- Keyed by UUID `job_id` — generated at POST time, never reused
- Value is a `WorkflowExecution` reference — the execution carries all state; the dict carries only presence

**Why not a `WorkflowExecutionRepository`**: The repository pattern is the right migration path for multi-user persistence. For a single-user dev tool running in one process, a dict is the honest implementation — no accidental complexity, nothing to test beyond presence/absence, and the migration path is clear when the requirement for persistence is named.

**Consumer**: Both `bootstrap_project` (write) and `bootstrap_status` (read + evict) handlers in `modules/ai/routes.py`.

---

### Angular Polling Client
**Purpose**: Bridges the 202 async backend contract to a synchronous-feeling UX in `new-project.component.ts` — the component awaits a result, not a job ID.

**Key Parts**:
- `ai.service.startBootstrapProject` — no Angular `timeout()` operator; the POST is expected to return in milliseconds
- `ai.service.getBootstrapStatus` — 10 s `timeout()` per poll; guards against a hung status endpoint without treating a slow chain as an error
- Start-then-poll loop in `new-project.component.ts` — 3 s interval; resolves when `status.done` is true; re-throws on `status.error`; navigates after exactly one successful terminal read (not a second GET)

**Patterns**: Polling with exponential-backoff eligibility (the 3 s fixed interval is intentional for v1; the pattern accommodates jitter if needed); the loop terminates on the first terminal response, which is also the eviction trigger on the server.

**Consumer**: `new-project.component.ts`'s project-creation flow.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Background execution | Python `threading.Thread` (daemon) | No new dependency; sufficient for single-user in-process execution; `WorkflowRuntime` already abstracts the execution model |
| State machine | `WorkflowExecution` (`modules/workflows/execution.py`) | Proven by two prior consumers; carries `IN_PROGRESS`, `COMPLETED`, `ERROR` transitions and timing data |
| Workflow definition | `Workflow.builder` + `AICall` + `Compute` steps | Consistent with `task_gen` and `spec_gen` workflow shape; `Compute` step avoids bespoke marshalling logic in the route handler |
| HTTP async contract | HTTP 202 + polling GET | Stateless polling is simpler to test and cache than SSE or WebSocket; consistent with `task_gen` |
| Angular polling | `setTimeout` loop + `firstValueFrom` | Minimal rxjs footprint; the loop shape makes backoff straightforward to add later |
| API contract | OpenAPI 3 + generated DTOs | `make generate-dtos` keeps Angular types in sync; no manual DTO maintenance |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Reuse `WorkflowRuntime` + `WorkflowExecution` rather than a new async mechanism | Three consumers using the same infrastructure is more maintainable than two parallel async patterns; bootstrap inherits all existing test coverage | Bootstrap is bound to the `WorkflowRuntime` execution model; if that model needs to change, it changes for all three consumers |
| `_BOOTSTRAP_JOBS` dict owns lifetime; `WorkflowExecution` owns state | Separates two orthogonal concerns; the dict cannot have stale status because it has no status | A process restart drops all in-flight jobs silently; acceptable for a dev tool, not for multi-user production |
| Purge on first terminal read | Keeps the registry naturally bounded without a TTL background task; the consumer has exactly one chance to read the result | If the Angular client crashes after receiving `done: true` but before persisting the files, the result is gone; Angular is responsible for caching before navigating |
| Hard cutover, no feature flag | The old shape fails silently on long requests; a flag preserving it preserves broken behavior, not a fallback | Zero rollback path if the new shape introduces a regression; acceptable because the old shape was not functionally usable |
| 3 s poll interval, no jitter in v1 | Simple to reason about; the chain takes 10–25 minutes, so poll timing within a few seconds is irrelevant to UX | Under load from multiple users, synchronized polls could spike the status endpoint; fixed interval is the correct starting point for a single-user tool |
| `architecture` step at `max_tokens=16384` | Truncation is observed in the architecture step specifically (see `braindump-raise-max-tokens.md`); other steps are budgeted conservatively | Higher token limit increases per-call latency and cost for the architecture step; the trade-off is correctness over speed |

---

## Execution Flow

```
POST /bootstrap-project
  │
  ├─ Validate BootstrapProjectRequest
  ├─ Resolve context fallbacks (builder, principles, codebase, references)
  ├─ Construct WorkflowExecution
  ├─ Register in _BOOTSTRAP_JOBS[job_id]
  ├─ Dispatch daemon thread → WorkflowRuntime.run()
  └─ Return 202 { job_id }

Background Thread (WorkflowRuntime)
  │
  ├─ Step: AICall("analysis")
  ├─ Step: AICall("epic")       ← depends on analysis output
  ├─ Step: AICall("architecture") ← depends on epic output; max_tokens=16384
  ├─ Step: Compute("files") via bootstrap.marshal_files
  └─ WorkflowExecution transitions → COMPLETED / ERROR

GET /bootstrap-project/status/{job_id}   (polled every 3 s by Angular)
  │
  ├─ Lookup _BOOTSTRAP_JOBS[job_id] → 404 if absent
  ├─ Project ExecutionStatus → { running, done, files?, error?, latencyMs? }
  ├─ If done: pop job_id from _BOOTSTRAP_JOBS
  └─ Return 200 BootstrapJobStatus

Angular (new-project.component.ts)
  │
  ├─ startBootstrapProject → job_id
  ├─ poll getBootstrapStatus every 3 s
  ├─ status.done = false → continue polling
  ├─ status.error → throw
  └─ status.done + files → navigate to project
```

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview