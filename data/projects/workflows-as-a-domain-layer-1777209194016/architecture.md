# 🏗️ Solution Architecture: Workflows as a Domain Layer

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The workflows layer introduces a five-layer pattern stack that turns multi-step AI pipelines from inline route logic into named, observable, composable domain objects. Today every route handler in `spec_gen` and adjacent modules is both the orchestrator and the executor of its AI calls; adding a new pass means copying orchestration scaffolding, not defining a new step. The new layer cleanses that coupling by making the Workflow the object a route invokes, rather than the logic it contains.

The design commits to one irreversible decision: workflows are data. Not executable Python closures, not LangChain chains, not DSL expressions — serialisable, git-trackable descriptions of steps that Python and, eventually, a JSON loader can both produce. This is the precondition for the GUI workflow builder described in the [Epic](./epic.md). Every other pattern choice in this document flows from that commitment: Value Objects for steps, Builder for construction, Repository for persistence, Registry for named step-kind dispatch.

The five layers are strictly ordered by dependency. Provider (Layer A) knows nothing of the layers above it. Step (Layer B) knows Provider and nothing else. Workflow (Layer C) knows Step. Execution (Layer D) knows Workflow and emits events that any listener can observe. Discovery (Layer E) loads Workflows so that Execution can invoke them. A feature route handler touches only Layers D and E — it submits a `WorkflowExecution` and receives an event stream; it never sees a step, a provider, or a file path.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| One adapter boundary for all AI calls | Feature code imports `modules.chain.adapter` exclusively; direct provider imports are structurally forbidden and caught by `featureModules_mustNotImportProvidersDirectly` |
| Workflows are data, Python is an escape hatch | Steps and workflows are frozen value objects; anonymous callables are legal in Python workflows but cannot appear in JSON workflows or the GUI |
| Per-feature ownership, no global registry | Each feature module owns its workflow definitions under its own `workflows/` subdirectory; there is no central workflow registry |
| Event lifecycle sealed at the framework level | `AbstractStep`'s Template Method seals `StepStarted` / `StepCompleted` / `StepFailed` emission; no concrete step can omit it |
| One status-tracking path | `WorkflowExecution`'s State machine replaces `task_gen`'s threading and status-dict; two parallel status systems is the explicit risk identified in [Analysis](./analysis.md) |
| Interpreter pattern is a hard line | No DSL, no expression language, no `eval` in workflow definitions; the moment step templates gain arithmetic, this layer collapses into LangChain |
| Open/closed via Registry, not edits | New providers, step kinds, and decorators are registered components; adding them requires zero edits to central runtime code |

---

## System Boundaries

### What This System Includes

- `workflows` module — the canonical domain layer; resolves the naming question deferred in [Analysis](./analysis.md)
- `AbstractStep` and concrete step kinds `AICall` and `Compute` — the atomic units of composition as frozen value objects
- `Workflow` aggregate with its fluent Builder — the named container that owns its steps
- `WorkflowRuntime` — the generator-based execution engine producing typed domain events
- `WorkflowExecution` command type and its status State machine
- `StepEvent` domain event types — `StepStarted`, `StepCompleted`, `StepFailed`
- `WorkflowRepository` port and `WorkflowRepositoryFs` adapter — filesystem-backed workflow loading by name
- Migration of `spec_gen`'s inline orchestration to the new runtime — the end-to-end validation

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Bridge pattern (`Modality × Vendor`), `ProviderPool`, multi-modal providers | No current feature requires a second modality; Phase 2 trigger is a named multi-modal consumer |
| Decorator step wrappers (`RetryStep`, `LoggedStep`, `CostTrackedStep`, `RateLimitedStep`) | Phase 2; the Step foundation must be stable before wrapping it |
| Composite (workflows-of-workflows) | Phase 2; requires Phase 1's `Workflow` container to be proven stable first |
| JSON workflow format and JSON loader | Phase 3; trigger is a named GUI consumer, not speculative need |
| `WorkflowRepositoryDb` | Deferred until a multi-user persistence requirement is named; the port exists so the swap is a binding change, not a rewrite |
| Async execution | Ships alongside `Parallel` step kind with a concrete latency SLA; synchronous generators handle all current features |
| `chain.adapter` rename | A separate cleanup epic; coupling it here merges two unrelated blast radii |
| Chain of Responsibility middleware (auth → quota → execute) | No current workflow-level pre-execute pipeline consumer; Decorator covers per-step concerns adequately |
| Interpreter / DSL / expression language | Permanently excluded; this is the firewall against turning the workflow layer into LangChain |
| `WorkflowMediator` coordination object | Observer pattern via domain events already provides decoupled coordination; a central Mediator would become a god object |

---

## Component Design

### Layer A — Provider (the I/O Boundary)

**Purpose**: Isolate all AI vendor I/O behind a single adapter so feature code never couples to a provider library.

**Key Parts**:

- `chain.adapter` — the existing Adapter ([ELA Pattern #6]) that is the only legal import path for AI calls; widened from `generate(system, prompt)` to `invoke(invocation)` to accommodate typed invocation shapes, while preserving `generate` as a thin convenience wrapper over the new form
- `Invocation` and `Result` value objects — the Anti-Corruption Layer ([ELA Pattern #24]) that hides raw `anthropic.Message` and similar vendor shapes behind clean domain types; `ChainResult` is already this pattern and is generalised here to per-modality result types
- `MockProvider` — the Null Object ([ELA Pattern #18]) used by tests and offline development; the `CHAIN_PROVIDER=mock` flag activates it, ensuring every test gets deterministic fixture responses and no null-checks
- `ConditionalProviderRegistration` — a provider is registered only when its credentials or feature flag are present; the deployment's provider set is determined at startup, not at call time

**Patterns**: Adapter, Anti-Corruption Layer, Null Object, Conditional Registration.

**Why this shape**: The `featureModules_mustNotImportProvidersDirectly` structural test is the enforcement mechanism for the single-boundary invariant. Without it, every new feature is one direct import away from coupling to an SDK version. The adapter makes provider upgrades and provider swaps invisible to feature code. `MockProvider` as Null Object (not a conditional stub or a mock framework artifact) means tests never branch on whether a provider is configured — they always have a real, if deterministic, implementation.

---

### Layer B — Step (the Unit of Composition)

**Purpose**: Define the atomic, immutable, composable unit of pipeline work whose event lifecycle is sealed and whose cross-cutting concerns are addable without modifying the step body.

**Key Parts**:

- `AbstractStep` — the Template Method ([ELA Pattern #13]) skeleton that defines the final `execute(inputs, context)` method; it validates inputs, emits `StepStarted`, calls subclass-defined `_invoke`, emits `StepCompleted` or `StepFailed`, and halts on error; subclasses override only `_invoke`; the `WorkflowRuntime` is the consumer of every `AbstractStep` implementation
- `AICall` — a frozen Value Object ([ELA Pattern #21]) describing a provider invocation by modality, provider reference, and prompt template; `WorkflowRuntime` executes it by resolving its provider reference against `chain.adapter` and invoking it
- `Compute` — a frozen Value Object naming a registered callable by name; the Registry (Layer E) resolves the name to an implementation at workflow load time; this is the escape hatch for non-AI steps without allowing anonymous callables in serialised form
- `StepKind` discriminator — the field in a step's value object that the JSON loader (Phase 3) dispatches on to select the correct constructor from the Registry; in Phase 1 this is implicit in Python type dispatch

**Patterns**: Value Object, Template Method.

**Why this shape**: Making steps Value Objects rather than executable callables is what makes workflows serialisable. An `AICall` value object can round-trip through JSON; a lambda cannot. The Template Method seals the event lifecycle at the framework level so the Observer contract (Layer D) cannot be violated by a step that forgets to emit events — the test assertion is on `AbstractStep`, not replicated per step kind. The separation between "what a step describes" (Value Object) and "how it executes" (Template Method on `AbstractStep`) is the same separation ELA uses between `Amount` (data) and `AmountCalculator` (behaviour).

---

### Layer C — Workflow (the Container)

**Purpose**: Name, aggregate, and describe an ordered collection of steps as a first-class domain object that routes invoke and repositories persist.

**Key Parts**:

- `Workflow` — the Aggregate Root ([ELA Pattern #20]) that owns its ordered Step list; nothing outside the aggregate holds a reference to an individual step; `WorkflowRuntime` and `WorkflowRepository` are the two consumers of `Workflow`
- `WorkflowRef` — the identifier type used by `WorkflowExecution` to name the workflow being run; it is the stable reference external callers hold, not the `Workflow` object itself
- `Workflow.builder(name)` — the fluent Builder ([ELA Pattern #1]) that is the only legal construction path; it enforces declared inputs and outputs before `build()` is called; `to_builder()` allows variations without mutation; the JSON loader (Phase 3) feeds the same Builder from a deserialized schema
- Per-workflow Facade ([ELA Pattern #8]) — each named `Workflow` is itself a Facade over its steps; the route handler invoking `WorkflowRuntime.run("generate-spec", inputs)` sees one operation, not four AI calls; this is the mechanism by which inline orchestration in `spec_gen` is eliminated

**Patterns**: Aggregate Root, Builder, Facade.

**Why this shape**: The Aggregate Root boundary is what prevents the GUI from evolving into a step editor that bypasses workflow-level constraints. Dragging a step in the GUI is a Workflow mutation, not a Step create — the aggregate enforces that. The Builder as the sole construction path means Python workflows and JSON-deserialized workflows are produced by the same code path, which is why the JSON loader in Phase 3 requires no new construction logic. The Facade is why routes become single-invocation callers: the multi-step complexity is inside the Workflow, not the route.

---

### Layer D — Execution (the Runtime)

**Purpose**: Turn a `Workflow` into a controlled, observable, long-lived operation with a defined status lifecycle.

**Key Parts**:

- `WorkflowExecution` — the Command ([ELA Pattern #15]) encapsulating a workflow run request: execution ID, workflow reference, inputs, start time, timeout, and submitting principal; the `spec_gen` route handler is the Phase 1 consumer that constructs and submits this command
- `WorkflowExecution.status` — the State machine ([ELA Pattern #16]) with transitions mirroring ELA's `TaskInfo.Status`: `NEW → IN_PROGRESS → COMPLETED | ERROR | TIMEOUT | CANCELLING → CANCELLED`; invalid transitions raise explicitly; this replaces `task_gen`'s flat status dictionary, which is the concrete source of the status-tracking duplication identified in [Analysis](./analysis.md)
- `WorkflowRuntime` — the generator-based Iterator ([ELA Pattern #17]) that takes a `Workflow` and yields a stream of `StepEvent` domain objects; the HTTP layer wraps this generator in SSE; tests drain it directly without an HTTP layer; `spec_gen`'s route handler is the primary consumer
- `StepStarted`, `StepCompleted`, `StepFailed` — typed Domain Events ([ELA Pattern #14, #25]) emitted by the runtime as frozen Pydantic models; each carries the execution ID, step name, timing, and relevant outputs; the cost tracker, audit logger, and GUI SSE pusher are the three named listener kinds — none of them touch the runtime, and none of them know about each other

**Patterns**: Command, State, Iterator/Generator, Observer/Domain Events.

**Why this shape**: The Command pattern is why `WorkflowExecution` can eventually be queued, persisted, and cancelled without changing the runtime. The State machine is why status is auditable — an illegal transition raises rather than silently corrupting the status dict. The generator is synchronous deliberately: the CLI subprocess provider used by `spec_gen` runs in a subprocess, not an async context, and async execution adds complexity without a concrete latency SLA to justify it. The Observer shape is why adding a cost-tracking listener or a GUI progress listener requires no runtime changes — the events are already being emitted; new listeners subscribe.

---

### Layer E — Discovery & Persistence

**Purpose**: Load workflows by name at startup, make feature modules the owners of their own workflow definitions, and provide an extension point for new step kinds and providers without central edits.

**Key Parts**:

- `WorkflowRepository` port — the hexagonal boundary ([ELA Pattern #23]) with `get(name)`, `list()`, and `save(workflow)`; domain code uses only the port; `WorkflowRuntime` is the primary consumer
- `WorkflowRepositoryFs` — the filesystem adapter that reads workflow definitions from `api/modules/<feature>/workflows/` at startup; in Phase 1 these are Python-constructed `Workflow` objects registered by name; in Phase 3 they are JSON files deserialized through the same Builder; git-trackable and dev-machine-friendly by default
- Bounded Context constraint ([ELA Pattern #26]) — each feature module owns its workflows; `api/modules/spec_gen/workflows/` belongs to `spec_gen`; the `WorkflowRepository` aggregates across feature modules at startup but does not centralise ownership; cross-feature workflow composition (Phase 2 Composite) happens through named references, not shared module imports
- Registry for step kinds and providers ([ELA Pattern #27]) — auto-discovered lists of `StepKind` constructors and `Provider` implementations are registered at startup; the JSON loader (Phase 3) dispatches on `kind` names against the `StepKind` registry; `ProviderPool` dispatches on modality against the `Provider` registry; neither registry requires a central edit when a new member is added

**Patterns**: Repository (Hexagonal), Bounded Context, Registry.

**Why this shape**: The Repository port is what makes switching from filesystem to database a binding change rather than a feature change — `WorkflowRepositoryDb` is a new adapter that satisfies the same port. The Bounded Context constraint is what prevents the `workflows` module from becoming the god module that [Analysis](./analysis.md) identifies as the current risk with `chain.adapter`. The Registry open/closed property is why adding a new `Compute` step kind requires only a new registered component — zero edits in the loader, the runtime, or the repository.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Step value objects | Python frozen dataclasses or Pydantic frozen models | Equal-by-value semantics without identity; round-trippable to JSON for Phase 3 without a schema migration |
| Workflow runtime | Synchronous Python generators | Compatible with the existing CLI subprocess provider; avoids async complexity until a `Parallel` step with a concrete latency SLA demands it |
| Domain events | Pydantic frozen models | Type-safe, serialisable to SSE payloads without a separate DTO layer; consistent with the existing `ChainResult` ACL shape |
| Workflow persistence (Phase 1) | Filesystem JSON under `api/modules/<feature>/workflows/` | Git-trackable, dev-machine-friendly, zero infrastructure dependency; the Repository port makes it swappable when multi-user persistence is named |
| HTTP streaming | Server-Sent Events wrapping the runtime generator | Already in use for `spec_gen`; the generator yields events; the HTTP layer is a thin wrapper; no new transport decision required |
| Provider boundary | `chain.adapter` (existing) | The structural test already enforces the single-boundary invariant; widening the signature is less disruptive than introducing a parallel boundary |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Workflows are data, not callables | The GUI workflow builder requires workflows to be serialisable; a closure cannot be serialised; this is the one-way door the brain dump names explicitly | Python workflows that use anonymous callables are not GUI-portable; power users writing Python workflows accept that asymmetry |
| No anonymous callables in JSON workflows | Security (no `eval` from untrusted input), discoverability (the GUI can enumerate registered step kinds), testability (each step kind is independently testable) | Workflow authors must register a named `Compute` step kind before they can reference it in JSON; slightly higher ceremony for simple transformations |
| Generator runtime, not async | The CLI subprocess provider is synchronous; changing the transport requires an async rewrite of the subprocess layer, which has no current latency SLA to justify it | Intra-workflow parallelism (running steps concurrently) requires async; deferred to Phase 2 alongside `Parallel` step kind |
| Absorb chain-primitive epic into Task 1 | Shipping `ChainStep` as a standalone artefact and then immediately superseding it with `AbstractStep` creates a mid-flight pivot with two competing primitives; absorbing it makes `ChainStep` one concrete `Step` kind rather than a parallel foundation | The chain-primitive epic's prior work must be re-scoped; any work already merged on that branch needs to be reconciled with the new `AbstractStep` boundary |
| Replace `task_gen` threading in the same move as runtime | Two concurrent status-tracking systems — `task_gen`'s dict and `WorkflowExecution`'s State machine — is the explicit risk identified in [Analysis](./analysis.md); running them in parallel doubles the observability surface and creates divergence bugs | The `task_gen` module is removed rather than coexisted with; any feature depending on it must migrate in Task 5 or be listed as an explicit out-of-scope dependency |
| Per-feature workflow ownership (Bounded Context) | Prevents the `workflows` module from centralising all AI pipeline definitions and becoming a god module; each feature's workflow files are co-located with the feature's routes and service code | Cross-feature workflow composition (Composite, Phase 2) requires naming workflows by a qualified reference (`feature/workflow-name`) rather than a bare name; a small naming convention cost for a significant ownership benefit |
| Phase 1 is Python-only, JSON is Phase 3 | Python workflows via the Builder are sufficient for eliminating inline orchestration; committing to a JSON schema before the GUI consumer is named produces a schema that will break when the GUI's requirements are known | There is no GUI palette or JSON loader in Phase 1; any team member wanting to add a workflow must write Python; the schema is deferred until its consumer drives it |
| Repository port now, `WorkflowRepositoryDb` never in Phase 1 | The port costs one interface definition; without it, switching to database persistence later requires touching every consumer; with it, the switch is a binding change | The filesystem adapter has no transactions, no optimistic locking, no multi-writer safety; for a single-user development tool this is acceptable; multi-user requirements must name a concrete scenario before `WorkflowRepositoryDb` is scheduled |
| Interpreter pattern permanently excluded | A DSL or expression language in workflow step templates is the pattern that turns this layer into LangChain; once `{{ inputs.x + 5 }}` is permitted in a step template, the boundary between data and code collapses and the security, testability, and discoverability properties listed above become unenforceable | Workflow authors who need conditional logic between steps must express it as a registered `Compute` step kind, not inline in the workflow definition; this is a deliberate constraint, not a limitation |

---

## Execution Flow

The flow below describes Phase 1 end-to-end from a route handler's perspective. No step detail or provider detail is visible to the route.

```
Route Handler
  │
  ├─ Constructs WorkflowExecution (Command)
  │     workflow_ref: "spec_gen/generate-spec"
  │     inputs: {braindump, project_name}
  │
  ├─ WorkflowRepository.get("spec_gen/generate-spec")
  │     WorkflowRepositoryFs walks api/modules/spec_gen/workflows/
  │     Returns Workflow aggregate
  │
  ├─ WorkflowRuntime.run(execution) → Iterator[StepEvent]
  │     Status: NEW → IN_PROGRESS
  │     For each Step in Workflow:
  │       AbstractStep.execute() →
  │         emit StepStarted
  │         _invoke() via chain.adapter
  │         emit StepCompleted | StepFailed
  │     Status: IN_PROGRESS → COMPLETED | ERROR
  │
  └─ HTTP layer wraps Iterator in SSE
        StepStarted → SSE event to browser
        StepCompleted → SSE event to browser
        WorkflowCompleted → SSE close
```

Observers (cost tracker, audit logger, GUI SSE pusher) subscribe to `StepEvent`s without touching the runtime. The route handler is blind to which observers are active.

---

## Phase Delivery Boundaries

Each phase delivers standalone value. Later phases do not invalidate earlier ones; they extend them.

**Phase 1 — Workflows as code (this epic)**
Layers A (existing Adapter widened), B (Value Object + Template Method for `AICall` and `Compute`), C (Aggregate Root + Builder), D (Command + State + Iterator + Observer), and E (Repository FS adapter + Bounded Context + Registry for step kinds) all ship. The `spec_gen` route handler migration validates the full stack. The chain-primitive epic is absorbed here rather than shipping as a parallel artefact.

**Phase 2 — Multi-modal providers and parallelism**
Layer A gains Bridge (Modality × Vendor axes) and `ProviderPool` as the palette mechanism. Layer B gains Decorator step wrappers (`RetryStep`, `LoggedStep`, `CostTrackedStep`) and Composite (a `Workflow` used as a `Step`). Layer D gains async execution alongside `Parallel` step kind when a concrete latency SLA is named.

**Phase 3 — JSON workflows and GUI builder**
Layer E gains the JSON loader that feeds the existing Builder from a Pydantic schema. `WorkflowRepository` exposes its `list()` and `get()` results through new API endpoints. The GUI palette is `GET /api/step-kinds` returning the Registry's registered kinds and `GET /api/providers` returning `ProviderPool`'s registered providers — no new registry; these are the Phase 2 pools surfaced over HTTP.

---

## Patterns Deliberately Excluded

| Pattern | Reason |
|---------|--------|
| Interpreter | Hard line; see Design Decisions above; the day step templates gain expression evaluation is the day this layer becomes LangChain |
| Mediator | Spring events / Observer already provide decoupled coordination; a `WorkflowMediator` would centralise all event routing and become a god object |
| Visitor | No traversal use case; polymorphism on `Step` subclasses through `AbstractStep._invoke` covers all dispatch needs |
| Memento | No undo requirement; execution history is served by Domain Events (an implicit event-sourcing shape), not snapshots |
| Prototype / clone | Builder's `to_builder()` covers workflow variations; `clone()` on frozen value objects adds no value |
| Classic Singleton | Python module-level objects are singletons by import; `WorkflowRuntime.instance()` accessors are unnecessary and obscure the dependency |
| Flyweight | No memory pressure justifies it for workflow definitions; frozen dataclasses at startup scale is negligible |

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design; the inline-orchestration anti-pattern, the dual status-tracking risk, and the provider-boundary violations that this architecture resolves
- [Epic](./epic.md) – Scope, tasks, success criteria, and explicit non-goals; the five tasks map directly to the five layers described above
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview