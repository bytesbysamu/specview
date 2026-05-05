# Solution Architecture: Chain Primitive

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The chain primitive introduces a sequential execution engine that sits between route handlers and the existing adapter boundary. The adapter (`modules/chain/adapter.py`) already exists and handles single AI calls; what is missing is the orchestration layer above it — something that calls the adapter once per step, threads the previous step's output into the next step's inputs, and emits structured events as it goes. `run_chain` is that layer: a generator that consumes a `ChainDefinition` and a flat `inputs` dict and yields `ChainEvent`s until the chain completes or halts on error.

The key insight is that every multi-step AI workflow in spec-doc is already a chain in behavior — the bootstrap loop in `new-project.component.ts` calls five endpoints in sequence, each consuming the previous output. The chain primitive does not introduce a new execution model; it names and enforces the model that already exists, moves ownership server-side, and eliminates the structural risk of route handlers assembling their own ad-hoc sequences. Once the runner exists, a new workflow is a Python value declaration, not a new module.

The v1 transport contract is a polling pair (`POST` spawns, `GET /status/{id}` reports). This matches the shape of every existing endpoint in the surface, requires no new transport machinery on either side, and closes the browser-tab reliability problem that motivated the work. `ChainEvent`s are produced by the runner and consumed by logging and tests; they do not cross the HTTP boundary. Finer-grained progress is a follow-on upgrade with a clear user-complaint trigger, not a v1 requirement.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| One adapter boundary | All AI calls flow through `modules/chain/adapter.py`. The runner calls the adapter once per step; no route handler calls it directly more than once. |
| Inputs over coupling | Each step declares its dependencies as `input_keys`; the runner resolves `$`-prefixed references from the accumulated outputs dict. Steps do not reference each other directly. |
| Pure runner, context outside | The runner receives a flat `inputs` dict. Context loading is the route handler's responsibility. This keeps `run_chain` testable against a plain dict with `CHAIN_PROVIDER=mock`. |
| Flatten over recurse | `BOOTSTRAP_CHAIN` inlines the four spec sub-steps rather than calling `run_chain(SPEC_CHAIN, ...)` recursively. One generator, nine steps, no nested async boundary to reason about. The two chains share step prompt *functions*, not a shared `run_chain` invocation. |
| Structural guard ships with the primitive | The AST test `pipelinedFeatures_useRunChain` is introduced at the same commit as the runner, because that is the first moment the violation class — a route handler calling the adapter more than once — becomes possible. |
| Polling over SSE | v1 serves progress via a 1–2 s polling loop against `/status/{id}`. This matches the existing synchronous endpoint shape and requires no new transport machinery. SSE is a well-scoped follow-on upgrade, not a v1 requirement. |

---

## System Boundaries

### What This System Includes

- **Chain runner** — `ChainStep`, `ChainDefinition`, `ChainEvent`, `_resolve_inputs`, `run_chain`; the foundational primitive consumed by both `SPEC_CHAIN` and `BOOTSTRAP_CHAIN`
- **`SPEC_CHAIN` declaration** — four step-prompt functions wired into a chain definition; consumed internally by the refactored `POST /api/ai/text/generate-spec` handler
- **`BOOTSTRAP_CHAIN` declaration** — nine-step flat chain; consumed by `POST /api/capability/bootstrap`
- **In-memory bootstrap status tracker** — keyed by project ID; consumed by the polling pair
- **Bootstrap polling pair** — `POST /api/capability/bootstrap` (spawns chain, returns project ID) and `GET /api/capability/bootstrap/{id}/status` (step name, done flag, error, final payload); consumed by Angular `BootstrapService`
- **Angular `BootstrapService`** — one POST plus a `setInterval` polling loop; replaces the five-call JS sequence in `new-project.component.ts`
- **Structural test `pipelinedFeatures_useRunChain`** — AST guard; consumed by CI on every PR in this epic and forward
- **`openapi.yaml` final surface** — bootstrap polling pair added, per-step bootstrap paths removed after soak; consumed by `make check-dtos` and the `everyOpenapiPath_hasRouteHandler` structural test

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| JSON chain definitions loadable from disk | Two chains, both stable Python values; a loader is warranted at five chains or user-editable chains |
| `STEP_HANDLERS` dispatch over op names | All current chains are single-op-type; dispatch buys nothing until two chains share atomic-op vocabulary |
| Chain-of-chains runtime (`run_chain` calling `run_chain`) | `BOOTSTRAP_CHAIN` flattens spec sub-steps inline; recursive invocation deferred until a third pipeline shares ≥2 steps with both existing chains |
| SSE / `text/event-stream` transport | Polling at 1–2 s covers the UX gap; SSE adds new transport machinery on both sides for a problem polling already solves |
| Per-token streaming inside a step | The default `CHAIN_PROVIDER=cli` blocks until subprocess exit; token streaming requires upgrading the CLI provider or switching to the SDK provider — both deferred until SSE triggers |
| Database-backed bootstrap status tracking | In-memory dict is correct for a single-user dev tool; upgrade trigger is auth + multi-user state |
| `ChainEvent` serialization over HTTP | Events are server-side artifacts for logging and tests; bootstrap progress is surfaced via the polling pair, not event push |
| `GENERATE_TASK_CHAIN` declaration | Single-consumer, single-step today; the chain wrapper adds no value until a second task-gen step exists |
| Retry/backoff per step | No failure data to calibrate; trigger is first production rate-limit incident |
| Provider routing per step | No cost signal yet; routing Haiku for analysis and Sonnet for architecture is a follow-on optimization |
| Observer / `chainCompleted` events for analytics | Stdout structlog is sufficient; upgrade trigger is cost analytics or usage-limit enforcement |
| Removal of per-step batch endpoints | Soak window of ≥1 week on the polling pair before deletion; separate PR |

---

## Component Design

### Chain Runner (`modules/chain/runner.py`)

**Purpose**: Provides the single reusable primitive that all server-side multi-step AI workflows in spec-doc build on. Without it, every workflow either runs client-side (fragile) or hand-rolls its own adapter-calling loop (duplicated, untestable, structurally unguarded).

**Key Parts**:
- `ChainStep` — frozen dataclass carrying a step name, a `prompt_fn` reference, and an `input_keys` list; `SPEC_CHAIN` and `BOOTSTRAP_CHAIN` both declare their steps in this shape
- `ChainDefinition` — a name plus an ordered list of `ChainStep`s; `SPEC_CHAIN` and `BOOTSTRAP_CHAIN` are the two concrete instances
- `ChainEvent` — Pydantic model with a type field (`step_start`, `step_end`, `chain_complete`, `chain_error`), an optional step name, and a data payload; consumed by tests and structlog, never serialized over HTTP in v1
- `_resolve_inputs` — resolves `$`-prefixed references from the accumulated outputs dict; the mechanism that threads one step's output into the next step's `prompt_fn` arguments without coupling steps to each other
- `run_chain` — sequential generator; calls the adapter once per step, accumulates outputs, yields `ChainEvent`s, and halts on the first error without silent truncation; consumed by `POST /api/ai/text/generate-spec` and `POST /api/capability/bootstrap`

**Patterns**: Generator-as-protocol (caller drains the generator; no eager evaluation); Input-resolution-by-convention (`$`-prefix separates step references from literal values); Halt-on-error (the chain does not continue past a failed step — partial output is worse than a clean error in a document-generation context).

---

### Structural Guard (`pipelinedFeatures_useRunChain`)

**Purpose**: Prevents the violation class — a route handler calling `chain_adapter.generate` or `chain_adapter.stream` more than once — from silently re-appearing after the runner ships. The guard is as important as the primitive itself: without it, the runner exists but the anti-pattern it replaces remains possible.

**Key Parts**:
- AST grep over `modules/*/routes.py` counting adapter call sites per handler function; fails CI if any handler exceeds one call; `modules/chain/runner.py` itself is excluded from scope since it is the one legitimate multi-call site

**Patterns**: Structural testing (behavioral tests confirm correctness; structural tests confirm architectural discipline; neither substitutes for the other).

---

### Chain Declarations (`modules/ai/chains.py`)

**Purpose**: The single home for chain definitions. Both `SPEC_CHAIN` and `BOOTSTRAP_CHAIN` live here so that their step-prompt function dependencies are visible in one place and the relationship between the two chains — shared prompt functions, separate `run_chain` invocations — is explicit.

**Key Parts**:
- `SPEC_CHAIN` — four-step chain: `spec_analysis_prompt` → `spec_epic_prompt` → `spec_architecture_prompt` → `spec_doc_spec_prompt`; each step function uses `PromptBuilder`; consumed by the refactored `POST /api/ai/text/generate-spec` handler
- `BOOTSTRAP_CHAIN` — nine-step flat chain: lint → analysis → epic → architecture → spec-doc-spec (the four spec sub-steps inlined rather than delegated) → timeline → readme → save; shares the four spec step-prompt functions with `SPEC_CHAIN`; consumed by `POST /api/capability/bootstrap`
- Step-prompt functions — four functions split from the current `generate_spec_prompt`; used by both chains; this is where the sharing lives, not in nested `run_chain` calls

**Patterns**: Declaration over orchestration (chains are values, not imperative sequences; declaring `BOOTSTRAP_CHAIN` as a Python value is why the bootstrap route handler stays ~30 lines); Shared functions, separate chains (the two chains reuse prompt functions but run independently — flat `BOOTSTRAP_CHAIN` avoids a nested generator boundary while preserving the prompt function reuse that matters).

---

### Bootstrap Status Tracker

**Purpose**: Bridges the background thread running `BOOTSTRAP_CHAIN` and the polling endpoint reading its progress. The chain runs in a background thread and writes state; the GET handler reads state. The tracker is the shared boundary between them.

**Key Parts**:
- In-memory dict keyed by project ID; each entry holds the current step name, a done flag, an error field, and (when done) the final payload; consumed by `POST /api/capability/bootstrap` (writer) and `GET /api/capability/bootstrap/{id}/status` (reader)

**Patterns**: Shared-state concurrency with a narrow write surface (only the background thread writes step and done; only the route handler reads them — no bidirectional mutation); Ephemeral-by-design (in-memory is not a simplification of a real persistence requirement; it is correct for a sub-2-minute workflow on a single-user dev tool where job state expiring on restart is acceptable).

---

### Bootstrap Polling Pair (`modules/capability/routes.py`)

**Purpose**: Exposes the bootstrap chain over HTTP in a shape that closes the browser-tab reliability problem without introducing new transport machinery. The POST spawns the chain and returns immediately; the GET reports progress at whatever polling interval the frontend chooses.

**Key Parts**:
- `POST /api/capability/bootstrap` — accepts `{name, braindump}`, loads context, builds a flat `inputs` dict, spawns `run_chain(BOOTSTRAP_CHAIN, inputs)` in a background thread, writes initial state to the status tracker, and returns `{project_id}` within one second; consumed by Angular `BootstrapService`
- `GET /api/capability/bootstrap/{id}/status` — reads from the status tracker and returns the current step name, done flag, error field, and (when done) the final payload; consumed by Angular `BootstrapService` on a 1–2 s `setInterval`

**Patterns**: Polling pair (POST-to-spawn plus GET-to-poll is the established pattern for long-running operations without streaming infrastructure; it is not a temporary approximation of SSE — it is the correct v1 design given the polling-granularity UX requirements and the absence of a streaming transport trigger).

---

### Angular `BootstrapService`

**Purpose**: Moves the five-call JS orchestration in `new-project.component.ts` behind a typed service boundary. The component should not know about endpoint URLs, polling intervals, or step-count arithmetic. `BootstrapService` owns that contract; the component reads `current_step` for the progress label and navigates on `done: true`.

**Key Parts**:
- One POST call to `/api/capability/bootstrap`; a `setInterval` polling loop against `/api/capability/bootstrap/{id}/status`; exposes `current_step` (string) and `done` (boolean) as observable state; consumed exclusively by `new-project.component.ts`
- The `CONCURRENCY` cap and per-step call logic in the component are removed — bootstrap concurrency is now a server-side concern, not a client-side throttle

**Patterns**: Service-encapsulated polling (the component is a display layer; the service owns transport, interval management, and teardown on completion or error).

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Runner | Python generator function | Lazy evaluation matches the step-by-step event model; generators compose naturally with the existing iterator-based adapter boundary; no async runtime required for a synchronous subprocess-backed provider |
| Step dataclasses | Python frozen dataclasses | Immutable step definitions prevent accidental mutation; value equality makes chain declarations testable as plain data |
| `ChainEvent` shape | Pydantic BaseModel | Consistent with existing `ChainResult` and `ReviewResult` types in `types.py`; JSON roundtrip is testable as a first-class requirement |
| Bootstrap status | In-memory Python dict | Correct for a sub-2-minute single-user workflow; no dependency on a persistence layer that would complicate the runner's pure design |
| Bootstrap transport | HTTP polling pair | Matches the existing endpoint shape; no new transport machinery; upgrade path to SSE is clear and non-breaking |
| Angular transport | `HttpClient` + `setInterval` | Reuses existing Angular HTTP infrastructure; no new frontend dependencies; `EventSource` is the SSE upgrade path when the trigger is met |
| Structural testing | AST grep (Python `ast` module) | Enforces architectural constraints that behavioral tests cannot — a route handler calling the adapter twice is behaviorally testable but the constraint is architectural; AST inspection is the right tool |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Flatten `BOOTSTRAP_CHAIN` to nine steps rather than calling `run_chain(SPEC_CHAIN, ...)` recursively | One generator, one status tracker entry per step, no nested async boundary to reason about; simpler error attribution when a step fails mid-bootstrap | Less reuse at the `run_chain` level — if `SPEC_CHAIN` changes step count, `BOOTSTRAP_CHAIN` must be updated separately; mitigated by sharing step-prompt functions, where the real reuse lives |
| `ChainEvent`s are server-side only in v1 | Serializing events over HTTP is the SSE upgrade, not a v1 requirement; keeping events server-side means the runner's output contract is stable and the HTTP boundary stays simple | Bootstrap progress is coarser than step-level event push — the polling pair reports the current step name, not intra-step token progress; acceptable at 1–2 s polling granularity |
| Context loading outside the runner | Keeps `run_chain` testable with a plain dict and `CHAIN_PROVIDER=mock`; the runner is a pure function of `(definition, inputs)` — it does not need to know about workspace paths or file I/O | Each route handler that spawns a chain is responsible for loading context before calling `run_chain`; this is a consistent responsibility, not scattered logic |
| `POST /api/ai/text/generate-spec` keeps its current response shape | The refactored handler calls `run_chain(SPEC_CHAIN, inputs)` internally but the client-visible envelope is unchanged; existing client tests pass without modification | The decision between returning `===FILE:===` markers vs. a structured `{spec_index, analysis, epic, architecture}` object must be made before the handler is touched — the architecture does not resolve this; the spec phase must |
| In-memory status tracker rather than a `chain_run` table | A sub-2-minute workflow on a dev tool has no multi-user or restart-recovery requirement; a database table would introduce a persistence dependency for a problem that does not need it | Job state is lost on server restart; the frontend must re-trigger bootstrap if the server restarts mid-run; acceptable for the current single-user dev-tool context |
| Structural test ships with the runner | The violation class — a route handler calling the adapter more than once — first becomes possible at the moment the runner exists; waiting to ship the guard separately creates a window where the pattern can re-appear in review | The AST test must explicitly exclude `runner.py` itself from the constraint, which is a small but non-obvious carve-out |
| `modules/ai/chains.py` as the single home for chain declarations | One file makes the relationship between `SPEC_CHAIN` and `BOOTSTRAP_CHAIN` — shared prompt functions, separate invocations — explicit; move to `modules/chains/` when count reaches three or non-AI chains appear | `chains.py` living inside `modules/ai/` implies chains are an AI concern; true today, may need revisiting when non-AI chains (e.g. file-only save chains) appear |

---

## Execution Flow

```
Phase A — Runner
  Task 1: Port chain runner + structural guard

Phase B — SPEC_CHAIN
  Task 2: Split step-prompt functions + declare SPEC_CHAIN
       └→ Task 2 (cont): Refactor generate-spec handler

Phase C — BOOTSTRAP_CHAIN
  Task 3: Declare BOOTSTRAP_CHAIN + status tracker + polling pair
       └→ Task 4: Angular BootstrapService (parallel with Task 5)
  Task 5: Flatten OpenAPI + DTO drift check (parallel with Task 4)

Phase D — Soak
  ≥1 week green dev traffic on polling pair
       └→ Separate PR: remove per-step batch endpoints
```

Tasks 4 and 5 depend on Task 3's polling pair endpoints existing; they do not depend on each other and may proceed in parallel once Task 3 merges.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview