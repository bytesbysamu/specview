# Epic: Chain Primitive

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The bootstrap workflow is the first experience every user has with spec-doc — it produces the spec index, analysis, epic, architecture doc, and timeline from a single brain dump. Today that workflow runs as five sequential AI calls in the browser. The tab must stay open; any interruption discards partial work; progress feedback is per-step JavaScript state, untestable server-side. Moving it behind a server-side chain eliminates all three failure modes at once and makes the most user-visible workflow in the product reliable.

The chain primitive is the enabling infrastructure. Every multi-step AI workflow — spec generation, bootstrap, and the task-gen pipelines that follow — shares the same runner, the same input-resolution contract, and the same structural guard against ad-hoc copy-paste chaining. Building it once here means each subsequent workflow is a Python value declaration, not a new module. That compounds: the fifth pipeline costs a fraction of the first.

The polling-pair transport (`POST` + `GET /status/{id}`) ships v1 without new streaming machinery, matching the shape of every other endpoint in the surface today. It closes the browser-tab problem, exposes step-level progress for the UI, and leaves SSE as a well-scoped follow-on upgrade with a clear trigger rather than speculative infrastructure.

**Value Proposition**: Server-side chain execution makes spec-doc's core workflow reliable, testable, and the foundation every future AI pipeline builds on.

---

## Scope

### What This Epic Covers

- **Chain runner** (`ChainStep`, `ChainDefinition`, `run_chain`, input resolution) — the primitive that all subsequent chains consume
- **Structural guard** (`pipelinedFeatures_useRunChain`) — AST test that prevents multi-call chain-by-copy-paste in route handlers; ships with the runner because this is the first moment the violation class exists
- **`SPEC_CHAIN` declaration** — four step-prompt functions wired into a chain definition; `POST /api/ai/text/generate-spec` internally calls `run_chain` while keeping its current request/response shape
- **`BOOTSTRAP_CHAIN` declaration** — flat nine-step chain replacing the JS loop; in-memory status tracker keyed by project ID
- **Bootstrap polling pair** — `POST /api/capability/bootstrap` (spawns chain, returns project ID) and `GET /api/capability/bootstrap/{id}/status` (step name, done flag, error, final payload)
- **Angular `BootstrapService`** — one POST plus a 1–2 s polling loop replacing the five-call JS sequence in `new-project.component.ts`; surfaces `current_step` for progress UI
- **OpenAPI flattening and DTO drift check** — `openapi.yaml` updated to the final post-cleanup surface; `make check-dtos` passes clean in CI

### What This Epic Does NOT Cover

- ❌ JSON chain definitions loadable from disk — Python values are sufficient; trigger: five or more chains, or user-editable chains
- ❌ `STEP_HANDLERS` dispatch over op names — all current chains are single-op-type; trigger: two chains share atomic-op vocabulary
- ❌ Chain-of-chains as a runtime concept — `BOOTSTRAP_CHAIN` flattens spec sub-steps inline; trigger: a third pipeline shares two or more steps with both existing chains
- ❌ SSE / `text/event-stream` transport — polling at 1–2 s covers the UX gap; trigger: user-reported wait-time complaint polling granularity cannot address
- ❌ Per-token streaming inside a step — the default CLI provider blocks until exit; deferred with SSE
- ❌ Database-backed bootstrap status tracking — in-memory dict is correct for a single-user dev tool; trigger: auth and multi-user state
- ❌ Observer / `chainCompleted` events for analytics — structlog stdout is sufficient; trigger: cost analytics or usage-limit enforcement
- ❌ Retry/backoff per step — no failure data; trigger: first production rate-limit incident
- ❌ Provider routing per step — no cost signal yet
- ❌ `GENERATE_TASK_CHAIN` declaration — one consumer with no imminent second step; re-scope when a second task-gen step appears
- ❌ Removal of per-step batch endpoints — separate PR after at least one week of green dev traffic on the polling pair; soak first, delete later

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Port Chain Runner** | None | — | 1 day | High |
| 2 | **Declare SPEC_CHAIN + Refactor generate-spec** | 1 | — | 1 day | High |
| 3 | **Declare BOOTSTRAP_CHAIN + Polling Endpoints** | 1, 2 | — | 1.5 days | High |
| 4 | **Angular BootstrapService** | 3 | 5 | 0.5 days | High |
| 5 | **Flatten OpenAPI + DTO Drift Check** | 2, 3 | 4 | 0.5 days | High |

---

### Task 1: Port Chain Runner

The foundational primitive: `ChainStep`, `ChainDefinition`, `run_chain`, and `$`-prefixed input resolution. Ships alongside the structural test `pipelinedFeatures_useRunChain`, which AST-greps route handlers for multi-call adapter usage — the guard must exist the moment the violation becomes possible. Unit tests cover full event sequence, two-step chain, step-failure halt, missing-ref error, and `ChainEvent` JSON roundtrip, all against `CHAIN_PROVIDER=mock`.

**Port budget**: runner module plus unit and structural tests; `ChainEvent` stays server-side (logging and tests only, not serialized over HTTP in v1).

---

### Task 2: Declare SPEC_CHAIN + Refactor generate-spec

`generate_spec_prompt` splits into four step-prompt functions, each using the `PromptBuilder` already shipped in Task 2 of architecture-cleanup. `SPEC_CHAIN` wires the four functions with explicit input references. The `POST /api/ai/text/generate-spec` handler is rewritten to drain `run_chain(SPEC_CHAIN, inputs)` into the existing response envelope — same URL, same client-visible shape. `ChainEvent`s are logged per step and consumed in tests; they are not serialized to the caller.

**Port budget**: four prompt functions, one chain declaration, one refactored route handler; the outbound response shape decision (markers vs. structured object) must be made before the route is touched — see [Analysis](./analysis.md) for the open question.

---

### Task 3: Declare BOOTSTRAP_CHAIN + Polling Endpoints

`BOOTSTRAP_CHAIN` is declared as a flat nine-step chain — lint, four spec sub-steps inlined, timeline, readme, save — sharing step-prompt functions with `SPEC_CHAIN` but not a shared `run_chain` call. An in-memory status tracker module keys `{step, done, error, payload}` by project ID. `POST /api/capability/bootstrap` spawns the chain in a background thread and returns `{project_id}` immediately; `GET /api/capability/bootstrap/{id}/status` returns the current step name, done flag, error, and (when done) the final payload.

**Port budget**: chain declaration, status tracker module, two route handlers; context loading stays outside the runner — the route reads context and passes a flat `inputs` dict.

---

### Task 4: Angular BootstrapService

`BootstrapService` replaces the five-call JS sequence in `new-project.component.ts` with one `POST /api/capability/bootstrap` followed by a `setInterval` poll against `/status/{id}`. The component reads `current_step` for the "Step N of 9" progress label; `done: true` triggers project navigation. The `CONCURRENCY` cap and per-step orchestration logic in the component are removed.

**Port budget**: one Angular service, one updated component; no new transport primitives — polling reuses `HttpClient`.

---

### Task 5: Flatten OpenAPI + DTO Drift Check

`openapi.yaml` is updated to the final post-cleanup surface: bootstrap polling pair added, individual bootstrap-step paths consumed only by the JS loop removed, context and template paths from Tasks 1–3 of architecture-cleanup confirmed present. `make generate-dtos` is re-run; `make check-dtos` passes clean in CI. The structural test `everyOpenapiPath_hasRouteHandler` stays green throughout.

**Port budget**: `openapi.yaml` edits plus a `make generate-dtos` run; `dtos/models.py` is committed with `git add -f`.

---

## Success Criteria

- `run_chain` unit tests pass against `CHAIN_PROVIDER=mock`: full sequence, two-step chain, step-failure halt, missing-ref error, `ChainEvent` roundtrip
- `pipelinedFeatures_useRunChain` structural test is present and fails on a synthetic multi-call route handler
- `POST /api/ai/text/generate-spec` returns the same response shape before and after the Phase B refactor; existing client tests pass without modification
- `POST /api/capability/bootstrap` returns `{project_id}` within one second; `GET /api/capability/bootstrap/{id}/status` reflects the running step name and `done: true` on completion
- `new-project.component.ts` contains no direct AI or template endpoint calls; all bootstrap traffic flows through `BootstrapService`
- `make check-dtos` passes clean in CI after `openapi.yaml` flattening
- `everyOpenapiPath_hasRouteHandler` stays green on every merged PR in this epic

---

## Non-Goals

- ❌ SSE transport — polling at 1–2 s is sufficient for v1; adding `EventSource` is a follow-on upgrade with a clear user-complaint trigger
- ❌ Database-backed job state — in-memory is correct for a single-user dev tool; multi-user persistence triggers the upgrade
- ❌ Chain-of-chains runtime — `BOOTSTRAP_CHAIN` flattens spec sub-steps; recursive `run_chain` calls are deferred until a third pipeline shares steps with both existing chains
- ❌ JSON chain definitions — Python values cover two chains; a loader is warranted at five chains or user-editable chains, not before
- ❌ `GENERATE_TASK_CHAIN` — single-consumer, single-step today; re-scope when a second task-gen step exists
- ❌ Removal of per-step batch endpoints — soak window of at least one week on the polling pair before deletion; separate PR

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview