# 🎯 Epic: Bootstrap Async

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The `bootstrap-project` endpoint is the most consequential call in the tool: it converts a raw brain dump into a complete spec folder. It also holds an HTTP connection open for 10–25 minutes while doing so. That connection is not under the application's control — proxies, load balancers, and OS connection-tracking enforce their own limits, and three successive gunicorn timeout raises have not changed that. The endpoint will keep timing out on infrastructure the team does not own until the held connection is eliminated entirely.

Migrating to HTTP 202 + polling removes the connection entirely. The POST returns in milliseconds; a background thread owns the chain; Angular polls a lightweight status endpoint until the job completes. This is the same pattern that resolved timeout failures in `task_gen`, and reusing `WorkflowRuntime` + `WorkflowExecution` means bootstrap inherits that infrastructure's test coverage rather than introducing a parallel implementation.

Bootstrap reliability is table stakes for any user who depends on the tool daily. A workflow that cannot be trusted to complete is a workflow that gets abandoned. Fixing the structural failure mode — not raising the next timeout ceiling — is the only investment that makes the feature durable.

**Value Proposition**: Eliminate bootstrap connection timeouts permanently by removing the held HTTP connection from the critical path.

---

## Scope

### What This Epic Covers

- **`BOOTSTRAP_WORKFLOW` definition** — wraps the four existing bootstrap prompt functions as typed workflow steps, registered under `spec_gen/bootstrap-project`
- **Async POST handler** — replaces the synchronous route with a 202 response and background thread dispatch through `WorkflowRuntime`
- **Status endpoint** — `GET /api/ai/text/bootstrap-project/status/{job_id}` reads state from `WorkflowExecution` and returns `{running, done, files?, error?, latencyMs?}`
- **In-process job lifetime registry** — a dict keyed by `job_id` whose sole responsibility is lifetime management; `WorkflowExecution` owns all status state
- **Purge-on-first-read** — the completed job is evicted from the registry on the first terminal status read; Angular is responsible for consuming the result before navigating away
- **OpenAPI contract update** — new 202 response shape for POST, new status path and `BootstrapJobStatus` schema, regenerated DTOs
- **Angular polling client** — `startBootstrapProject` + `getBootstrapStatus` service methods; `new-project.component` replaces its inline call with a start-then-poll loop
- **Hard cutover** — no feature flag; old and new ship atomically

### What This Epic Does NOT Cover

- ❌ **SSE progress streaming** — covered by `braindump-streaming-task-gen.md`; bootstrap inherits the `partial` field once that lands
- ❌ **Persistent job storage** — in-process is sufficient for a single-user tool; the `WorkflowExecutionStore` adapter path is deferred until multi-user deployment is scoped
- ❌ **Cancellation surface** — `WorkflowExecution.request_cancel()` exists; wiring the runtime to check between steps requires a user-facing abort UX first
- ❌ **`chain.adapter` promotion to first-class infrastructure** — the third-consumer trigger is noted; that promotion is a follow-on epic unless scope is explicitly expanded here
- ❌ **`chain.adapter.generate` max_tokens default** — handled by `braindump-raise-max-tokens.md`

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Define `BOOTSTRAP_WORKFLOW`** | Workflows-as-a-Domain-Layer epic | — | 0.5 days | High |
| 2 | **Update OpenAPI contract** | None | With T1 | 0.5 days | High |
| 3 | **Async backend — route + status endpoint** | T1, T2 | — | 1 day | High |
| 4 | **Angular polling client** | T2, T3 | — | 1 day | High |

### Task 1: Define `BOOTSTRAP_WORKFLOW`

Register a four-step workflow under `spec_gen/bootstrap-project` that wraps the existing bootstrap prompt functions as `AICall` steps (analysis → epic → architecture) followed by a `Compute` step that marshals outputs into the `BootstrapFile` list. The `architecture` step carries `max_tokens=16384` per `braindump-raise-max-tokens.md`. This task produces no route changes — it is the workflow definition only.

**Port budget**: ~40 lines in `modules/spec_gen/workflows/bootstrap.py`; registration wired into `create_app.py`.

---

### Task 2: Update OpenAPI contract

Modify `openapi.yaml` to reflect the new POST response shape (`{job_id: string}`, status 202), add the `GET /bootstrap-project/status/{job_id}` path, and define the `BootstrapJobStatus` schema (`running`, `done`, `files?`, `error?`, `latencyMs?`) mirroring the existing `task_gen` status shape. Run `make generate-dtos` to regenerate `dtos/models.py`. Note: `everyOpenapiPath_hasRouteHandler` will fail between this task and T3 — expected, per project rules.

**Port budget**: schema edits to `openapi.yaml`; generated `dtos/models.py` is the only output file.

---

### Task 3: Async backend — route + status endpoint

Replace the synchronous `bootstrap_project` route with a 202 handler that creates a `WorkflowExecution`, registers it in the in-process lifetime dict, and dispatches a daemon thread through `WorkflowRuntime`. Add the `bootstrap_status` GET handler that reads status from `WorkflowExecution`'s state machine, surfaces `files` and `latencyMs` on completion, `error` on failure, and evicts the job from the registry on the first terminal read.

**Port budget**: ~50 lines across the two handlers in `modules/ai/routes.py`; `_BOOTSTRAP_JOBS` dict declared at module scope; no new modules.

---

### Task 4: Angular polling client

Add `startBootstrapProject` (no timeout — POST returns in milliseconds) and `getBootstrapStatus` (10 s timeout per poll) to `ai.service.ts`. Replace the synchronous bootstrap call in `new-project.component.ts` with a start-then-poll loop on a 3 s interval that resolves when `status.done` is true, re-throwing on `status.error`. This task includes updating the `BootstrapProject` DTO type to the new 202 response shape generated in T2.

**Port budget**: ~30 lines across `ai.service.ts` and `new-project.component.ts`; no new Angular modules.

---

## Success Criteria

- ✅ `POST /api/ai/text/bootstrap-project` returns HTTP 202 with `{job_id}` in under 500 ms on a cold request
- ✅ `GET /api/ai/text/bootstrap-project/status/{job_id}` returns the completed `files` array on the first poll after chain completion
- ✅ A completed job is absent from `_BOOTSTRAP_JOBS` after the first terminal status read
- ✅ A failed chain step surfaces `{done: true, error: "..."}` with no 500 from the status endpoint
- ✅ `make test` passes with no new skips after T3 ships (the structural test failure between T2 and T3 is expected and temporary)
- ✅ Angular navigates to the project after a successful poll without a second GET to the status endpoint
- ✅ No gunicorn timeout configuration change is required for bootstrap to complete on a 25-minute chain

---

## Non-Goals

- ❌ **Feature flag for the old synchronous shape** — the old shape's failure mode is connection termination with no error, not slowness; there is nothing to preserve behind a flag
- ❌ **TTL-based or DELETE-based job purge** — purge-on-first-read is the chosen policy; retry-safety is Angular's responsibility via response caching before navigation
- ❌ **`WorkflowExecutionRepository` lookup as the lifetime authority** — the dict owns lifetime only; `WorkflowExecution` owns state; that boundary is the explicit design choice per [Solution Architecture](./architecture.md)
- ❌ **Shared workflow definition with `spec_gen/generate-spec`** — prompt constants may be shared; workflows are not

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview