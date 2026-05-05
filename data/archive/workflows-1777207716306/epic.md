# 🎯 Epic: Workflows

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Every multi-step AI feature in `spec-doc-api` today is a private threading exercise: each route handler owns its own sequencing logic, its own status dictionary, and its own error-recovery shape. The cost compounds invisibly — each new feature re-pays the same implementation tax, with slightly different semantics, no shared observability, and no path to reuse. The moment a second feature needs the same sub-sequence a first feature already solved, the duplication is structural, not accidental.

A typed workflow layer converts that tax into an asset. Each step added to the library is available to every subsequent feature at zero marginal design cost. The step composition grows monotonically; the per-feature implementation cost falls toward the cost of configuration. This is the infrastructure that makes a portfolio of AI features viable without a proportional growth in backend complexity.

The terminal consumer of this layer is a GUI workflow builder (a separate downstream epic). That GUI cannot exist without workflows being serializable data. This epic installs the backend contract — typed steps, a named execution runtime, a repository port, and a live event stream — that the GUI epic will call. Shipping this layer unblocks that consumer without waiting on its timeline.

**Value Proposition**: Replace per-route inline orchestration with a typed, composable Workflow layer that eliminates reinvented multi-step execution and establishes the serializable data contract a GUI workflow builder requires.

---

## Scope

### What This Epic Covers

- **Step type foundation** — named, registered step kinds (`AICall`, `Compute`, `Persist`) and a StepKind Registry as the dispatch surface for the JSON loader
- **Workflow container** — `Workflow` as an Aggregate Root with a fluent Builder API and per-feature filesystem ownership
- **WorkflowRepository** — port (domain interface) plus filesystem adapter; workflows are git-trackable JSON files under each feature module
- **Execution runtime** — `WorkflowExecution` Command type, a named status state machine, and a synchronous generator runtime that yields typed `StepEvent`s (`StepStarted`, `StepCompleted`, `StepFailed`)
- **One concrete route migration** — the highest-complexity existing inline route replaced by a Workflow facade call, proving the layer end-to-end

### Open Decisions (must resolve before Phase 1 scope locks)

- **`chain-primitive` epic disposition** — re-scope as Phase 1 Step 1 of this epic (its `ChainStep` becomes a registered step kind) or ship standalone first. Blocks task 1 start.
- **Layer name** — `workflows` recommended; must ratify before routes and tests are written.
- **Cross-feature workflow ownership** — defer: no second cross-feature composition case exists yet; revisit when it does.

### What This Epic Does NOT Cover

- ❌ **GUI workflow builder** — this epic is the backend contract the GUI consumes; the GUI is a separate consumer epic gated on Phase 3 delivery
- ❌ **JSON workflow loader** — Phase 3; the filesystem adapter stores JSON, but the loader that deserializes JSON into a live Workflow is out of scope until the StepKind Registry is proven stable
- ❌ **Database adapter for `WorkflowRepository`** — no multi-user persistence requirement exists; re-scope trigger is a second user context or a persistence SLA
- ❌ **Async / parallel step branches** — synchronous generators carry Phase 1; re-scope trigger is a parallel step use case with a named deadline
- ❌ **Workflow-level middleware** — no auth/quota pipeline consumer is named; re-scope trigger is a second workflow-level pre-execute concern
- ❌ **Workflow versioning and migration** — speculative infrastructure until a breaking schema change occurs

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel With | Effort | Priority |
|---|------|--------------|---------------|--------|----------|
| 1 | **Step Type Foundation** | `chain-primitive` disposition resolved | — | 2 days | High |
| 2 | **Workflow Container & Repository** | Task 1 | Task 3 | 2 days | High |
| 3 | **Execution Runtime** | Task 1 | Task 2 | 2 days | High |
| 4 | **Route Migration** | Tasks 2, 3 | — | 1 day | High |

---

### Task 1: Step Type Foundation

Define the named step kinds (`AICall`, `Compute`, `Persist`) as immutable value types and register them in a StepKind Registry. The Registry is the single dispatch surface the JSON workflow loader will call in Phase 3; populating it now with the three Phase 1 kinds proves the extension contract without building the loader. The `AbstractStep` execution skeleton seals the event lifecycle at the framework level — no step can be added later without emitting the correct `StepEvent` sequence.

**Scope boundary**: three concrete step kinds only; the event types they emit; the Registry entry point. Defer `Parallel`, `Branch`, and `Workflow`-as-step (Composite) to Phase 2. See [Solution Architecture](./architecture.md) for the pattern decisions behind this layer.

---

### Task 2: Workflow Container & Repository

Define `Workflow` as an Aggregate Root that owns its ordered step list and exposes a fluent Builder API for construction and variation. Implement `WorkflowRepository` as a domain port with a filesystem adapter that reads and writes workflow definitions under `modules/{feature}/workflows/`. Per-feature ownership is enforced structurally: the Repository aggregates across feature directories at startup; no global workflow namespace exists.

**Scope boundary**: port interface, filesystem adapter, Builder, one concrete workflow definition per existing feature with a multi-step route. Defer the database adapter and the JSON deserializing loader; the filesystem adapter stores JSON as a serialization format without a loader yet. See [Solution Architecture](./architecture.md) for Repository and Bounded Context design.

---

### Task 3: Execution Runtime

Define `WorkflowExecution` as a typed Command carrying execution ID, workflow reference, inputs, and timeout. Implement the named status state machine (`PENDING → RUNNING → COMPLETED | FAILED | TIMED_OUT`) with enforced transitions. Implement the synchronous generator runtime that accepts a named workflow and inputs, resolves it from the Repository, sequences steps through the StepKind Registry, and yields `StepStarted`, `StepCompleted`, and `StepFailed` events. The runtime replaces the per-feature `task_gen` threading pattern with a single shared execution surface.

**Scope boundary**: single-threaded sequential execution only; the three Phase 1 step kinds; typed events with execution ID for correlation. Defer parallel branches, cancellation, and event fan-out to listeners. See [Solution Architecture](./architecture.md) for Command, State, and Observer pattern decisions.

---

### Task 4: Route Migration

Replace the highest-complexity existing inline multi-step route with a Workflow facade call that delegates entirely to the runtime from Task 3. This is the concrete proof that the layer eliminates inline orchestration rather than adding a layer alongside it. One route is the scope; the migration pattern it establishes guides subsequent feature routes.

**Scope boundary**: one route; the Adapter boundary test must remain green throughout. No other routes are in scope for this task. See [Analysis](./analysis.md) for the inline orchestration anti-pattern this task resolves.

---

## Success Criteria

- ✅ The `featureModules_mustNotImportProvidersDirectly` structural test remains green across all four tasks
- ✅ `WorkflowRuntime.run(name, inputs)` accepts a named workflow and returns a typed event stream without the caller knowing step count or step kinds
- ✅ Adding a new step kind requires a new registered class and zero edits to the runtime
- ✅ Every `WorkflowExecution` event carries an `execution_id` that correlates `StepStarted` to `StepCompleted` across a full run
- ✅ The migrated route's test coverage is equal to or higher than the inline route it replaces
- ✅ The status state machine rejects illegal transitions with a named exception, verified by test

---

## Non-Goals

- ❌ **GUI palette APIs (`GET /api/step-kinds`, `GET /api/providers`)** — Phase 3; no GUI consumer is in scope for this epic
- ❌ **DSL, expression language, or `eval` in workflow templates** — hard line; see [Analysis](./analysis.md) for rationale
- ❌ **Anonymous callables in JSON workflow definitions** — compute steps must be registered by name; unregistered callables are rejected by the loader when it ships
- ❌ **Migrating all existing inline routes** — one route is the concrete case; bulk migration is a separate cleanup task after the pattern is proven

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design and pattern decisions
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview