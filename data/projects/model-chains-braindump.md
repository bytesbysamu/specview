# Brain dump — Workflows as a Domain Layer (v3 — pattern-driven)

> Replaces v2. v2 was structural ("here are three layers"). v3 is pattern-driven —
> for each problem the chain model has to solve, name which GoF/DDD/Spring pattern
> solves it and why. Source for the pattern vocabulary: ELA codebase exploration
> (`learnings/lesson-03-design-patterns.md`).

---

## Lineage (compressed)

humanize-me's 3-pass Claude pipeline → bubls's `sequential(steps, initial)` runner with one-adapter-boundary discipline → spec-doc-api's `chain.adapter` (no runner yet, every multi-step pipeline is inline in a route handler) → Two Separate Levers (background thread + per-project status dict + polling endpoint).

Constants across the lineage: **one Adapter boundary for all AI calls** (ELA Pattern #6); **`ChainResult` as the Anti-Corruption Layer** (ELA Pattern #24); **mock provider as the Null Object** (ELA Pattern #18); **chains-as-code, not chains-as-data** (deliberately deferred declarative types).

The user's GUI workflow-builder vision flips that last constant. The rest survives.

---

## Current shape on master (compressed)

`api/modules/chain/{adapter,context,types,errors,providers/{claude,cli,mock}}` — text-only, single-call, no runner. Routes do their own multi-step orchestration inline. The `featureModules_mustNotImportProvidersDirectly` structural test pins the Adapter invariant; nothing else is enforced.

---

## The inflection

A GUI consumer requires workflows to be *data*. Once that consumer is named, "chains-as-code" is no longer the right default. The new default: workflows ARE data; Python remains an escape hatch for steps the data form can't express.

This is a one-way door. v3 commits to walking through it.

---

# The pattern stack

Five layers. Each pattern in this section is named with a `[Pattern #N — Name]` tag pointing at its entry in `learnings/lesson-03-design-patterns.md`.

## Layer A — Provider (the I/O boundary)

**Problem**: Multiple AI vendors, multiple modalities (text-in→text-out, text-in→image-out, image-in→text-out, audio-in→text-out, text-in→audio-out). Feature code must not couple to any of them.

### Adapter [#6 — Adapter] (already shipped)

The existing `chain.adapter.generate(system, prompt) -> ChainResult` is exactly the ELA Adapter pattern. It is the load-bearing invariant: *feature code only ever imports `from modules.chain import adapter`*. Direct `from .providers.claude import …` is structurally forbidden. This stays.

The signature widens to `adapter.invoke(invocation: Invocation) -> Result` where `Invocation` and `Result` are typed Value Objects discriminated by modality. The text-shaped `generate(system, prompt)` becomes a thin convenience over `invoke(TextInvocation(...))`.

### Bridge [#11 — Bridge] (the multi-modal shape)

This is the pattern v2 missed. Strategy [#12] picks *one algorithm from a family*. Bridge separates an *abstraction hierarchy* from an *implementation hierarchy*, so they can vary independently.

Multi-modal providers are exactly that:

- **Abstraction axis** (Modality): `TextToText`, `TextToImage`, `ImageToText`, `AudioToText`, `TextToAudio`
- **Implementation axis** (Vendor): `Anthropic`, `OpenAI`, `Gemini`, `Replicate`, `Flux`, `Whisper`, `Deepgram`, `ElevenLabs`

The two axes vary independently. A new modality (TextToVideo) doesn't force every existing vendor to implement it. A new vendor (Mistral) doesn't force every modality to support it. Strategy can't model this — it would force one giant interface that every vendor implements partially. Bridge models it correctly.

Implementation: each `Modality` has its own `Provider` subprotocol. A vendor *contributes* implementations for the modalities it supports. The runtime resolves `(modality, vendor) -> concrete provider`.

### Object Pool [#5 — Object Pool] (provider discovery, **THE GUI palette mechanism**)

`AdviceServicePool` in ELA: inject `List<ConsultationService>`, each implementation declares `canHandle(adviceType)`, lookup is `pool.stream().filter(canHandle).findFirst()`. Polymorphic dispatch pooling.

For chains: `ProviderPool.providersFor(modality) -> list[Provider]`. Each provider declares its modalities. The pool is the open/closed extension point — adding Stable Diffusion is a new `@Component`, no central edit.

**The GUI palette IS this pool.** GUI fetches `GET /api/providers` → backend returns `pool.all()` → GUI renders draggable nodes. No separate registry; the pool *is* the registry.

### Conditional Bean Registration [#30] (per-deployment provider activation)

ELA's `@ConditionalOnProperty(prefix="management.health.qdb", havingValue="true")`. For us: a provider is loaded only if its credentials/feature flag are present. `ReplicateProvider` only registered if `REPLICATE_API_TOKEN` is set. Same code, different deployments expose different palettes.

### Anti-Corruption Layer [#24] (`Result` types are the ACL)

ELA's `AdviceCreditDossierUpdateMapperImpl` translates external system DTOs into clean domain models. For us: every provider returns a typed `Result` (`TextResult`, `ImageResult`, `TranscriptResult`) that hides the raw `anthropic.Message` / `replicate.Output` shape. **`ChainResult` is already this**. Generalize it to per-modality `Result` types.

### Null Object [#18] (mock provider)

The existing `MockProvider` is precisely the Null Object pattern. ELA's `FallbackAuditingDetailsServiceImpl` is the analogue. Keep using it the same way: tests + offline development run with `CHAIN_PROVIDER=mock`, get deterministic fixture responses, never null-check.

---

## Layer B — Step (the unit of composition)

**Problem**: A step has one job — take inputs, optionally call a provider, produce outputs. Steps must compose (sequential, parallel, conditional). Cross-cutting concerns (retry, logging, cost tracking, locale) must be addable without touching step bodies.

### Value Object [#21 — Value Object] (Step is immutable data)

Every Step is a `@Value`-equivalent (Python frozen dataclass / Pydantic frozen model). Equality by value, no mutation, no identity. ELA's `Amount`, `Percent`, `CustomerId` are the model. A `Step` exists *as a description*, not *as an executable* — execution is a separate concern (Layer D).

```python
@dataclass(frozen=True)
class AICall:
    provider_ref: ProviderRef        # ("text-to-text", "anthropic")
    invocation_template: dict        # {system: "...", prompt: "{prev.text}"}
    outputs: list[str]
```

### Template Method [#13 — Template Method] (`AbstractStep` skeleton)

ELA's `AbstractAuditableJpaEntity` provides a final `compareTo` skeleton; subclasses just add fields. For us: `AbstractStep` provides a final `execute(inputs, context) -> Iterator[StepEvent]` skeleton — validates inputs, emits `StepStarted`, calls subclass-defined `_invoke(inputs)`, emits `StepCompleted` or `StepFailed`, halts on error.

Subclasses override only `_invoke`. The event lifecycle is sealed. This pins the Observer contract (Layer D) at the framework level — no step can forget to emit events.

### Decorator [#7 — Decorator] (cross-cutting concerns on steps)

ELA's `I18nTaskDecorator` adds locale propagation around any task without the task knowing. For us:

- `RetryStep(inner_step, max_attempts=3, backoff=exp)` — wraps any step with retry+backoff
- `LoggedStep(inner_step)` — adds structured logging at start/end
- `CostTrackedStep(inner_step)` — measures tokens-in / tokens-out and publishes a CostEvent
- `RateLimitedStep(inner_step, rps=10)` — applies a token bucket
- `TimedStep(inner_step, max_seconds=900)` — caller-defined timeout (separate from the underlying provider's timeout)

These are *opt-in per step*, configurable in the workflow definition. Crucially, they compose: `RetryStep(LoggedStep(CostTrackedStep(AICall(...))))`. ELA's pattern is precisely this — wrap the same `Runnable` in successive decorators.

In the JSON workflow form, decorators become a `wrappers: ["retry", "log", "cost-track"]` field on the step — the workflow loader composes them at instantiation time.

### Strategy [#12 — Strategy] (vendor selection within a modality)

Within a single modality (e.g., text-to-text), multiple vendors compete. `@Order(1) ClaudeProvider`, `@Order(2) GPTProvider`. Strategy with fallback: if `@Order(1)` errors with a non-retryable failure, try the next.

Selection happens at the *step* level: a step says "this modality + this preferred vendor". The pool resolves it.

### Composite [#10 — Composite] (workflows-as-steps, the recursion door)

ELA's `FolderEntity`: a folder contains files and subfolders, treated uniformly. For us: a `Workflow` *is* a `Step`. A workflow can appear as a step inside another workflow. The runtime treats `AICall` and `Workflow` identically — both are something `execute()`-able.

This is the natural way to build "the spec-generation workflow uses the analysis-only sub-workflow as step 1" without inventing new machinery. ELA's photoshoot epic considered and deferred this (`run_chain` recursively calling `run_chain`); the GUI consumer makes it inevitable, because users will compose workflows from saved workflows.

---

## Layer C — Workflow (the container)

**Problem**: A workflow is a named, declared collection of steps with inputs and outputs. It's the unit users save, share, run, and (eventually) build in a GUI.

### Aggregate Root [#20 — Aggregate Root] (Workflow owns its Steps)

ELA's `LoanAdvice` owns `Financing`, `Partner`, `Conclusion`, etc. with `OrphanRemoval=true`. Nothing outside `LoanAdvice` can hold a `Financing` reference and stay valid.

For us: a `Workflow` owns its `Step`s. Steps don't have independent identity. Modifying a Workflow's step list is the only legal way to change its steps. The `WorkflowRepository` (below) loads/saves Workflows as units, not Steps.

This matters for the GUI: dragging a step into a workflow is a Workflow update, not a Step create.

### Builder [#1 — Builder] (Workflow construction)

ELA uses Lombok `@Builder(toBuilder = true)` everywhere. For Python: a fluent constructor with `@Singular`-style step accumulation, plus `to_builder()` for variations.

```python
spec_chain = (Workflow.builder("generate-spec")
              .input("braindump", "project_name")
              .step(AICall(...).as_step("analysis"))
              .step(AICall(...).as_step("epic"))
              .step(AICall(...).as_step("architecture"))
              .output("analysis", "epic", "architecture")
              .build())

# variation: same chain with extra logging step
debug_chain = spec_chain.to_builder().step(LoggedStep(...)).build()
```

This shape is what the JSON form deserializes into. Same Builder, different entry points.

### Facade [#8 — Facade] (each Workflow IS a facade)

ELA's `LoanAdviceModuleConfiguration` hides 9 sub-modules behind one `@Import`. For us: `WorkflowRuntime.run("generate-spec", inputs)` hides 4 AI calls + 4 file writes + context loading + error handling behind one method call. The route handler doesn't see the steps; it sees one Workflow execution.

This is what eliminates the "every route does its own multi-step orchestration" anti-pattern that's on master today.

---

## Layer D — Execution (turning a Workflow into a state change)

**Problem**: Running a workflow is a long-lived operation that can succeed, fail, time out, be cancelled, or be observed mid-flight. Today's threading + status-dict pattern in `task_gen` is a primitive instance of what this layer formalizes.

### Command [#15 — Command] (`WorkflowExecution` is the queueable Command)

ELA's `PreparedTaskExecution<R>` is the model:

```python
@dataclass(frozen=True)
class WorkflowExecution:
    id: ExecutionId
    workflow_ref: WorkflowRef
    inputs: dict
    started_at: Instant
    timeout: Duration
    error_handler: Callable | None
    submitted_by: PrincipalId | None
```

This is what gets queued, persisted (when persistence is added), cancelled, and tracked. The `task_gen` module today inlines this into a per-project dict; promoting it to a typed Command makes "queue 5 workflow runs" a one-liner instead of a per-feature reinvention.

### State [#16 — State] (execution status as a state machine)

ELA's `TaskInfo.Status`: `NEW → IN_PROGRESS → COMPLETED | ERROR | TIMEOUT | CANCELLING → CANCELLED`. Service-enforced transitions; can't go from `COMPLETED` back to `NEW`.

For us, the same machine for `WorkflowExecution.status`. `task_gen`'s status dict is currently `{running, done, allDone, error}` — a flattened version. Promote it to the named state machine with explicit transitions and an `IllegalStateException` (Python: `InvalidTransition`) when violated.

### Iterator / Stream [#17] (the runtime is a generator)

ELA returns `Stream<T>` from repositories for lazy evaluation. The chain-primitive epic already uses this shape: `run_chain(definition, inputs) -> Iterator[ChainEvent]`. Keep it. The HTTP layer wraps the generator in SSE; tests drain it directly.

The workflow runtime is a generator yielding events. It is not async by default — synchronous generators carry through the existing CLI subprocess provider without a runtime rewrite. Async lands when concurrent intra-workflow execution (parallel step branches sharing a thread pool) demands it.

### Observer / Domain Events [#14, #25] (per-step events, listeners subscribe)

ELA's `MortgagePartnerRatingUpdateEvent` is a Java `record` published via `ApplicationEventPublisher`. For us: every step emits typed `StepEvent`s as Pydantic frozen models:

```python
class StepStarted(BaseModel):
    execution_id: ExecutionId
    step_name: str
    inputs: dict
    started_at: Instant

class StepCompleted(BaseModel):
    execution_id: ExecutionId
    step_name: str
    duration_ms: int
    cost: Cost | None
    result: dict
```

Listeners subscribe without coupling: cost tracker writes to a metrics store, audit logger writes to disk, GUI status pusher emits SSE to connected browsers. None of them touch the runtime; none of them know about each other.

This is the mechanism by which the GUI gets live progress without polling: the GUI's `EventSource` listens for `StepStarted` / `StepCompleted` events for its execution_id.

### Chain of Responsibility [#19] (middleware on execution, optional)

ELA's Spring Security filter chain is the canonical example. For workflows, this is *optional* — the Decorator pattern (Layer B) covers per-step concerns. Reach for Chain of Responsibility only when there's a *workflow-level* pre-execute pipeline (auth check → rate limit → quota check → tenant resolution → execute). Today there's no consumer for that; defer.

---

## Layer E — Discovery & Persistence

**Problem**: Where do Workflows live? How are they loaded? Who owns them?

### Repository (Hexagonal) [#23] (`WorkflowRepository` port + adapters)

ELA's `CustomerRepository` (domain interface) + `CustomerRepositoryImpl` (adapter that uses `CustomerRepositoryJpa`). Domain code uses the port; the adapter chooses the persistence technology.

For us:
- **Port**: `WorkflowRepository.get(name) -> Workflow`, `list() -> [WorkflowRef]`, `save(workflow) -> WorkflowRef`
- **Adapter A**: `WorkflowRepositoryFs` — reads/writes JSON files under `api/workflows/*.json` (the natural shape for v1, dev-machine-friendly, git-trackable)
- **Adapter B (later)**: `WorkflowRepositoryDb` — reads/writes a `workflow` table when multi-user persistence becomes a requirement

The GUI's "save this workflow" goes through the Repository port, not the adapter. Switching from filesystem to database is a one-binding change.

### Bounded Context [#26] (workflows belong to features)

ELA's bounded contexts: `kw-customer`, `kw-loan`, `kw-credit` each own their domain models. "Customer" means different things in each.

For us: there is **no global workflow registry**. Each feature module owns its workflows (`api/modules/spec_gen/workflows/`, `api/modules/photoshoot/workflows/`, etc.). The Repository aggregates across them at startup; cross-feature composition happens via the Composite pattern (a workflow in feature X can reference a saved workflow from feature Y as a sub-step) but they remain owned by their feature.

This is the constraint that prevents the workflow layer from becoming a god module.

### Registry [#27] (auto-discovered providers, decorators, step kinds)

ELA's `List<CustomerSearchProvider>` injection. For us:
- `List[Provider]` auto-discovered → fed into `ProviderPool`
- `List[StepKind]` auto-discovered → fed into the JSON workflow loader's dispatch table (loader sees `{kind: "ai-call", ...}`, looks up the registered constructor)
- `List[StepDecorator]` auto-discovered → registered by name for the `wrappers: [...]` JSON field

Open/closed: adding a new `Provider`, `StepKind`, or `StepDecorator` is a new `@Component`. Zero edits in central code.

---

# Patterns deliberately NOT used

From Lesson 3's "Patterns NOT Found (Interesting Absences)" + my read on what would damage this layer:

| Pattern | Why we don't use it |
|---|---|
| **Visitor** | No traversal use case — polymorphism on `Step` subclasses is enough. Don't build a `WorkflowVisitor` interface. |
| **Memento** | No undo requirement. If we ever need execution history, use Domain Events (event sourcing in disguise) — not a snapshot mechanism. |
| **Mediator** | Tempting (`WorkflowMediator` coordinates everything). Spring events already do this implicitly via Observer. A central Mediator would become a god object. |
| **Interpreter** | **Hard line.** The user said "GUI to construct workflows" — that's *data-described workflows*, not a DSL. The data IS the contract. No `parse_workflow_string()`, no expression language, no `eval`. The day someone proposes "let's allow `{{ inputs.x + 5 }}` in step templates" is the day this layer collapses into LangChain. |
| **Prototype (Cloneable)** | Use Builder's `to_builder()` for variations. No `clone()` method. |
| **Singleton (classic Java)** | Module-level Python objects are singletons by import. Don't add a `WorkflowRuntime.instance()` accessor. |
| **Flyweight** | No memory pressure justifies it for chain definitions. Frozen dataclasses are fine. |

---

# The data-vs-code duality through the pattern lens

The brain dump's central tension is "function flavor vs data flavor" steps. Through the patterns above, the answer is sharper:

- **Data flavor** (`AICall`, `Compute(name="extract-tasks", inputs=[...])`) — Value Object. Lives in JSON or Python. Equal-by-value. The GUI emits these.
- **Function flavor** — only the pre-registered `Compute` step kinds. Each is a `@Component` with a registered name. The JSON workflow says `{kind: "compute", name: "extract-tasks", inputs: [...]}`; the loader resolves `name → registered callable` via the Registry pattern.

**No anonymous lambdas in JSON workflows.** Compute steps are *named* and *registered*. Python workflows can use anonymous callables (escape hatch for power users); the GUI form is restricted to the registered set. This keeps:

- Security (no `eval` from untrusted JSON)
- Discoverability (the GUI can list available compute steps)
- Testability (each compute step is a `@Component` with its own unit tests)

The asymmetry from v2 holds: every JSON workflow is expressible in Python; not every Python workflow is GUI-portable. That's correct.

---

# What changes from v2

| v2 said | v3 says |
|---|---|
| Layer A "Provider Protocol" | Bridge pattern — abstraction (Modality) and implementation (Vendor) are independent axes. ProviderPool with `canHandle(modality)` is the GUI palette mechanism. |
| Layer B "Step is a data declaration or a callable" | Both are Value Objects. `AICall` is data. `Compute` is data referencing a registered callable by name. No anonymous functions in JSON. AbstractStep + Template Method seals the event lifecycle. |
| Cross-cutting per-step concerns | Decorator pattern. `RetryStep(inner)`, `LoggedStep(inner)`, etc. Compose freely. |
| Composition primitives | Composite pattern: a Workflow IS a Step. Workflows-of-workflows is the recursion door — already needed (the spec-doc bootstrap chain calls a sub-workflow per spec section). |
| "Workflow definition format" decision | Both — Python first via Builder pattern, JSON later via the same Builder fed by a JSON loader. |
| Test discipline | (was underweight) — covered by lesson 2; main implication: snapshot/approval tests with scrubbers for chain output, MockWebServer for provider tests, Mockito-style adapter mocks at every layer boundary. |
| Workflow execution shape | Command pattern (`WorkflowExecution`), State machine for status (full ELA `TaskInfo.Status` model), Domain Events for observability. |
| Persistence | Repository (Hexagonal) — port in domain, FS adapter first, DB adapter when multi-user comes. |
| LangChain firewall | Reinforced — Interpreter pattern is the explicit hard line. No DSL, no expression language, no `eval`. |

---

# Naming (now that the patterns name themselves)

The triple-booking of "chain" is unchanged; v3 doesn't move the needle on this. The layer this brain dump describes is **`workflows`** (the user's word). The runner becomes `WorkflowRuntime`. The provider boundary stays `chain.adapter` for now and gets renamed in a separate cleanup epic.

Steps inside a workflow keep the name `Step`. Specific kinds are `AICall`, `Compute`, `Persist`, `Parallel`, `Branch`, `Workflow` (when used as a sub-step via Composite).

---

# Three-phase delivery (unchanged from v2 but now with named patterns per phase)

**Phase 1 — Workflows-as-code (sequential + Compute + Persist)**
Patterns shipped: Adapter (existing), Anti-Corruption Layer (existing `ChainResult`, generalized), Null Object (existing mock), Value Object (Step types), Template Method (`AbstractStep`), Builder (`Workflow.builder()`), Aggregate Root (`Workflow` owns Steps), Facade (per-feature workflow), Command (`WorkflowExecution`), State (status enum), Iterator (generator runtime), Observer (StepEvents), Repository (FS adapter), Bounded Context (per-feature ownership), Registry (auto-discovered StepKinds).

**Phase 2 — Multi-modal + parallelism**
Patterns added: Bridge (Modality × Vendor), Object Pool (`ProviderPool`), Strategy (vendor selection within modality), Conditional Bean Registration (per-deployment provider activation), Composite (workflows-of-workflows), Decorator (Retry/Log/Cost/RateLimit step wrappers).

**Phase 3 — JSON workflows + GUI builder**
Patterns added: Repository's loader contract finalized (Pydantic schema for JSON form), Registry's StepKind dispatch is what the loader calls, the GUI's palette is `GET /api/providers` + `GET /api/step-kinds` returning the contents of the two pools.

Each phase ships independently. Each phase's value is real without the next.

---

# Open decisions (compressed, replaces v2 §11)

The patterns above answered most of v2's 10 questions. Three remain genuinely open:

1. **Workflow definition format** — answer is *both*, but: Python first (Phase 1), JSON in Phase 3 via the same Builder. Confirmed by the data-vs-code framing above.
2. **Naming of the layer** — `workflows` is recommended; ratify or reject.
3. **Backward compatibility with the in-flight `chain-primitive` epic** — re-scope as Phase 1 of this work, OR ship it standalone first. Re-scoping is cleaner; the epic's `ChainStep` becomes one of the new `Step` kinds. Confirm.

The other 7 v2 questions have pattern-driven answers now (Bridge for parallelism transport, Pool for provider registry, Pydantic for typing, generator for streaming, etc.) — see the relevant Layer section above.

---

*v3 generated 2026-04-26 after deep read of `learnings/lesson-03-design-patterns.md`. v1 and v2 superseded.*
