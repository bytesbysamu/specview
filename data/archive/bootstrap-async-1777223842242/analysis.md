# 🔍 Bootstrap Async — Analysis

## The Problem
`POST /api/ai/text/bootstrap-project` holds an HTTP connection open for 10–25 minutes while three sequential AI calls run synchronously. Proxies and OS connection-tracking kill that connection regardless of gunicorn timeout settings; the timeout has been raised three times already with no structural improvement. Migrating to HTTP 202 + polling via the existing `WorkflowRuntime`/`WorkflowExecution` infrastructure eliminates the held connection entirely.

## Hard Constraints
- `WorkflowRuntime` and `WorkflowExecution` (Workflows-as-a-Domain-Layer epic) are prerequisites — this work cannot start until that epic is merged.
- Hard cutover only; no feature flag. Decision made in brain dump and stands.
- In-process job storage only — single-user dev tool; no persistence requirement until multi-user is scoped.
- `architecture` step `max_tokens=16384` already decided in `braindump-raise-max-tokens.md`; not re-opened here.

## Open Questions
- **"No new dict store" is contradicted by `_BOOTSTRAP_JOBS`.** The brain dump claims to avoid a new dict-backed store but then introduces exactly one. The distinction drawn is that `WorkflowExecution` owns state while the dict owns lifetime only. Is that distinction firm enough to hold, or does this need a `WorkflowExecutionRepository` lookup? Options: (a) keep the lifetime-only dict as written; (b) route through the existing workflow repo; (c) defer the question to the persistent-store epic.
- **Purge-on-first-read creates a data-loss window.** If Angular's HTTP client retries a status GET after a network blip, the job is already gone and the files are unrecoverable. Options: (a) require Angular to cache the response before navigating away; (b) TTL-based purge (e.g., 5 min post-completion); (c) purge only on explicit DELETE.
- **"Third consumer" promotion scope.** The brain dump names three WorkflowRuntime consumers as the trigger for promoting `chain.adapter` to first-class infrastructure. Does that happen in this epic or a follow-on?

## Dependencies & Sequencing
- Workflows-as-a-Domain-Layer epic must be merged first — `WorkflowRuntime`, `WorkflowExecution`, `ExecutionStatus` are all prerequisites.
- `openapi.yaml` changes precede `make generate-dtos`; `make test` will fail between the schema edit and the new route handler addition (`everyOpenapiPath_hasRouteHandler`).
- Hard cutover means Angular and backend **must deploy atomically**. Backend-first exposes old Angular to a 202 it cannot parse; Angular-first exposes new Angular to the old synchronous response shape. Deploy sequencing is unaddressed in the brain dump.

## Explicitly Out of Scope
- **SSE progress streaming** — covered by `braindump-streaming-task-gen.md`; bootstrap inherits the partial field once that lands.
- **Persistent job storage / `WorkflowExecutionStore` adapter** — deferred until multi-user or multi-instance deployment is scoped.
- **Cancellation surface** — `WorkflowExecution.request_cancel()` exists; runtime doesn't yet check between steps; defer until a user-facing abort UX is defined.
- **Promoting `chain.adapter` to first-class infrastructure** — third-consumer trigger noted; separate epic unless scope is explicitly expanded.
- **`chain.adapter.generate` max_tokens default** — handled by `braindump-raise-max-tokens.md`.