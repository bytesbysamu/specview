# 🎯 Epic: Workflows as a Domain Layer

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Every multi-step AI pipeline in the codebase today lives inline in a route handler. Adding a new spec section, a new analysis pass, or a new generation mode means duplicating orchestration logic across handlers — no shared retry behaviour, no shared cost tracking, no shared observability. The cost of each new feature compounds instead of amortising. This epic eliminates that tax by making a workflow a first-class named object that routes invoke rather than inline.

The one-way door is the GUI workflow builder. The product's durable differentiation is the ability for users to compose AI pipelines visually — that capability is only possible if workflows are data that can be serialised, stored, and loaded. Shipping a code-only workflow layer now is the minimum step that makes the GUI builder a follow-on engineering task rather than a ground-up rearchitecture. Each phase of this epic delivers standalone value; Phase 1 alone eliminates the inline-orchestration anti-pattern and provides the named execution model that Phase 3's GUI reads from.

The immediate revenue case is feature velocity on the existing product: new spec generation modes, cost visibility per workflow run, and live progress to the browser are each one workflow definition away once this layer exists. The medium-term case is the GUI builder as a product differentiator in the AI tooling market where workflow composition is becoming table stakes.

**Value Proposition**: Replace inline route orchestration with named, observable, composable workflows so that each new AI feature is a workflow definition rather than new spaghetti.

---

## Scope

### What This Epic Covers

- **`workflows` module** — canonical name for the new layer; resolves the open naming question in [Analysis](./analysis.md)
- **Step foundation** — the atomic unit of composition with a sealed event lifecycle; absorbs the in-flight chain-primitive epic rather than shipping it as a separate artefact
- **Workflow container** — named, immutable collection of steps with declared inputs and outputs; the object a route handler invokes
- **Workflow runtime** — generator-based execution engine turning a Workflow into a stream of typed domain events; replaces `task_gen`'s threading + status-dict in the same move
- **WorkflowRepository (filesystem adapter)** — port + FS implementation so workflows are loadable by name; git-trackable JSON files are the Phase 1 storage medium
- **Migration of one existing feature** — validates the full stack end-to-end with a concrete consumer; not a prototype

### What This Epic Does NOT Cover

- ❌ Multi-modal providers (Bridge + ProviderPool) — Phase 2; no current feature requires a second modality
- ❌ Decorator wrappers (Retry, RateLimit, CostTracked) — Phase 2; composable once the Step foundation is stable
- ❌ Composite (workflows-of-workflows) — Phase 2; requires Phase 1's Workflow container to be stable first
- ❌ JSON workflow format and GUI builder endpoints — Phase 3; trigger is a named GUI consumer
- ❌ `WorkflowRepositoryDb` — deferred until a multi-user persistence requirement is named
- ❌ Async execution — deferred until a `Parallel` step ships with a concrete latency SLA
- ❌ `chain.adapter` rename — a separate cleanup epic owns that and the structural test update it triggers
- ❌ Chain of Responsibility middleware (auth → quota → execute) — no current workflow-level pre-execute consumer

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel With | Effort | Priority |
|---|------|--------------|---------------|--------|----------|
| 1.1 | **AbstractStep Foundation** | None | — | 1d | High |
| 1.2 | **Concrete Step Kinds (AICall + Compute)** | Task 1.1 | — | 1d | High |
| 2 | **Workflow Container** | Task 1.2 | — | 2d | High |
| 3 | **Workflow Runtime** | Task 2 | Task 4 | 3d | High |
| 4 | **WorkflowRepository (FS Adapter)** | Task 2 | Task 3 | 1d | High |
| 5 | **Migrate spec_gen to WorkflowRuntime** | Tasks 3, 4 | — | 1d | High |

---

### Task 1.1: AbstractStep Foundation

Establish `AbstractStep` as the sealed unit of composition in the new `workflows` module. A step is an immutable value object; its event lifecycle (`StepStarted`, `StepCompleted`, `StepFailed`) is enforced at the framework level so no concrete step can omit it. `StepContext` carries the shared execution bag (inputs, outputs, run_id). This is the structural contract every concrete step kind depends on.

**Port budget**: `AbstractStep`, `StepContext`, the three `StepEvent` types, and the `steps/` package skeleton (`__init__.py`, `base.py`). No concrete step implementations in this task.

---

### Task 1.2: Concrete Step Kinds (AICall + Compute)

Implement the two concrete step kinds on top of the `AbstractStep` base from Task 1.1. `AICall` wraps a single `chain_adapter.generate()` call and absorbs the chain-primitive epic — `ChainStep` becomes `AICall` here, avoiding a parallel in-flight artefact. `Compute` wraps a registered pure-Python callable, with no `eval` or anonymous functions permitted (registered by name only).

**Port budget**: `AICall` step, `Compute` step, the callable registry, and unit tests for both. The Decorator suite (Retry, Log, Cost) is Phase 2 and must not be added here.

---

### Task 2: Workflow Container

Define `Workflow` as a named, immutable aggregate that owns its ordered Step list with declared inputs and outputs. The fluent builder is the only construction path. Nothing outside the aggregate may hold a reference to an individual Step. This is the object every route handler will eventually invoke in place of inline orchestration.

**Port budget**: `Workflow`, its builder, and the `WorkflowRef` identifier type. The JSON serialisation schema is Phase 3 and must not be added here.

---

### Task 3: Workflow Runtime

Implement the generator-based execution engine that turns a `Workflow` into a stream of typed domain events (`StepStarted`, `StepCompleted`, `StepFailed`). Replace `task_gen`'s threading and status dictionary in this same task — two status-tracking systems in parallel is the explicit risk called out in [Analysis](./analysis.md). The `WorkflowExecution` command type and its state machine (statuses matching ELA's `TaskInfo.Status` model) live here. See [Solution Architecture](./architecture.md) for the event and state machine design.

**Port budget**: The runtime generator, `WorkflowExecution`, the status state machine, and the `StepEvent` domain event types. Async execution and the full Observer subscriber suite are Phase 2.

---

### Task 4: WorkflowRepository (FS Adapter)

Implement the `WorkflowRepository` port and its filesystem adapter so a workflow can be loaded by name from `api/modules/<feature>/workflows/*.json` at startup. The port must be the only import path for feature modules; direct filesystem reads from outside the adapter are structurally equivalent to the `featureModules_mustNotImportProvidersDirectly` violation. See [Solution Architecture](./architecture.md) for the hexagonal boundary design.

**Port budget**: The port interface, the FS adapter, and the startup registration walk. `WorkflowRepositoryDb` is an explicit non-goal above.

---

### Task 5: Migrate spec_gen to WorkflowRuntime

Replace the inline multi-step orchestration in the `spec_gen` route handler with a named workflow loaded through `WorkflowRepository` and executed through `WorkflowRuntime`. This is the validation that every prior task's contract holds end-to-end under real conditions — not a proof of concept. The route handler after migration invokes one workflow; it does not inspect steps.

**Port budget**: One route handler refactored, one workflow definition file added under `api/modules/spec_gen/workflows/`. No new abstractions.

---

## Success Criteria

- ✅ The `featureModules_mustNotImportProvidersDirectly` structural test remains green throughout every task
- ✅ `task_gen`'s threading and status dictionary are removed; a single status-tracking path exists via `WorkflowExecution`
- ✅ The migrated `spec_gen` route handler contains no inline multi-step orchestration logic
- ✅ Every `Step` kind emits `StepStarted` and `StepCompleted` (or `StepFailed`) events — verified by the `AbstractStep` contract, not by per-step assertions
- ✅ Adding a new `StepKind` or a new feature workflow requires zero edits to central runtime code
- ✅ The chain-primitive epic is absorbed into Task 1 with no parallel in-flight artefact

---

## Non-Goals

- ❌ A DSL or expression language in workflow definitions — the Interpreter pattern is an explicit hard line; see [Analysis](./analysis.md)
- ❌ Anonymous callables in JSON workflows — `Compute` steps are registered by name only; security and discoverability depend on this
- ❌ GUI builder or provider palette endpoints — Phase 3 only; no GUI consumer is named yet
- ❌ Async execution — ships only alongside a `Parallel` step kind with a concrete latency SLA
- ❌ `chain.adapter` rename — a separate cleanup epic; adding it here couples two unrelated blast radii

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design and pattern decisions
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview