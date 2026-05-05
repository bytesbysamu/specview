# 🏗️ Solution Architecture: Architecture Cleanup

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Spec-doc's current shape inherited a critical antipattern from its Express predecessor: the Angular frontend accumulated business logic — prompt construction, workflow orchestration, and markdown template generation — that has no business being in the browser. This is not a minor style issue. System prompts that live in TypeScript string literals cannot be version-controlled independently of the UI bundle, cannot be snapshot-tested in isolation, and balloon every request body with context that the server could own once and reuse across calls. The five-call bootstrap loop in the component layer forces the user's browser to stay open for up to ninety seconds, offers no transactional safety, and makes the client responsible for rate-limiting itself with a `CONCURRENCY` cap — a client-side workaround for a server-side concern.

The architectural correction is conceptually simple: move all business logic to Flask, reduce Angular to a rendering shell. The Flask backend gains three new modules — `capability/` for bootstrap orchestration, `templates/` for markdown generation, and `ai/prompts/builder.py` for fluent prompt assembly — while the Angular service layer collapses from seven services to four, three of which become thin HTTP wrappers. The fourth, `BootstrapService`, handles one call and a polling loop, which is the correct amount of client-side orchestration.

The secondary gain is API surface clarity. Four near-identical context endpoints collapse into one parameterised route. Five bootstrap calls collapse into one `POST` plus a status poll. The AI text operation endpoints are left untouched — they are correctly shaped already and have no redundancy to eliminate. The result is a 21-to-16 route reduction that improves comprehensibility without removing any capability.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Business logic belongs on the server | Prompts, template generation, and workflow orchestration move to Flask. The Angular frontend becomes a rendering shell — it renders state, it does not compute it. |
| Contracts over conventions | `openapi.yaml` is updated first; DTOs on both sides are regenerated from it. No manual DTO maintenance. CI drift-checks enforce this on every build. |
| Don't build abstractions of one concrete case | `ProjectRepository`, `BootstrapResult` ACL, and `CapabilityStrategy` are all deferred — each has exactly one current consumer. They are named in "What This System Does NOT Include" with explicit trigger conditions. |
| SDK over subprocess | The `chain/` adapter boundary is unchanged. `CHAIN_PROVIDER=cli` remains for this iteration; the prompt migration makes the eventual SDK switch cheaper by centralising all prompt construction behind `PromptBuilder`. |
| Structural tests as architecture | Three structural invariants are added as violations are encountered: no prompt strings in route handlers, no cross-module imports between bounded contexts, and no routes absent from `openapi.yaml`. |

---

## System Boundaries

### What This System Includes

- **Context service unification** — one `ContextService` with a `ContextKey` parameter replaces four near-identical Angular services; one `GET /api/context/{key}` / `PUT /api/context/{key}` endpoint replaces four separate Flask routes
- **Prompt migration to Flask** — all prompt construction moves to `flask/modules/ai/prompts/`, assembled by a `PromptBuilder` class; no prompt strings remain in any TypeScript file
- **Template extraction to Flask** — `generate_spec_index()`, `generate_timeline()`, and `generate_readme()` move to `flask/modules/templates/generators.py` as pure, snapshot-tested Python functions
- **Bootstrap facade** — the five-call orchestration loop in `NewProjectComponent` is replaced by `POST /api/capability/bootstrap` (accepts name and braindump, returns a project ID) and `GET /api/capability/bootstrap/{id}/status` (returns step, done flag, and any error); state is tracked in an in-memory dict
- **OpenAPI consolidation** — `flask/openapi.yaml` updated from 21 to 16 routes; DTOs regenerated on both sides; CI drift check validated

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| `ProjectRepository` interface with filesystem and in-memory implementations | One consumer today: the filesystem CRUD in `flask/modules/projects/routes.py`. Extract when a second backend (Postgres, in-memory test double) is explicitly named. |
| `BootstrapResult` Anti-Corruption Layer DTO | `file_parser.py` has one caller (the bootstrap service). The ACL shape cannot be calibrated by a single use case. Introduce when a second consumer of the parsed result appears. |
| `CapabilityStrategy` pattern for project types (web app, CLI, library) | Bootstrap v1 is generic. Strategy extraction is triggered when a user explicitly requests type-specific scaffolding. Shipping it now locks in a shape before the pull exists. |
| `PromptBuilder` versioning parameter | One prompt format exists. Add versioning when a second named format has a user. |
| Database-backed job status | In-memory dict is correct for a single-user dev tool. Upgrade to a `bootstrap_jobs` table when auth introduces multi-user state. |
| Claude SDK migration (`CHAIN_PROVIDER=sdk`) | The `chain/` adapter boundary already isolates the provider. SDK migration is a separate epic triggered by production deployment. |

---

## Component Design

### Context Endpoint

**Purpose**: Eliminate four structurally identical Angular services and their corresponding Flask routes. All four context types — builder, principles, codebase, references — share the same two-method contract (`get`, `put`) and differ only in path. A single parameterised service and a single parameterised endpoint express this without duplication.

**Key Parts**:
- `ContextService` (Angular) — accepts a `ContextKey` enum parameter; called by every component that previously injected one of the four individual services
- `flask/modules/context/routes.py` — single route file handling `GET /api/context/{key}` and `PUT /api/context/{key}`; validates key against an enum at the route boundary

**Patterns**: Parametric service — same interface, key-dispatched behaviour. This is not a Registry (no auto-discovery, no self-registration); it is a deliberate simplification of copy-paste repetition.

**Consumer**: Task 1 (Unify Context Services) and every component that currently injects `BuilderService`, `PrinciplesService`, `CodebaseService`, or `ReferencesService`.

---

### PromptBuilder

**Purpose**: Move system prompt construction from the Angular frontend to the Flask backend and make it independently testable. `buildImplementationGuidePrompt()` in `implementation-guide.service.ts` (lines 165–368) currently concatenates six context blocks into a 5–50 KB string. This string cannot be snapshot-tested without running the browser. It drifts silently when context files change. It travels over the wire on every request even when the context has not changed.

**Key Parts**:
- `flask/modules/ai/prompts/builder.py` — `PromptBuilder` class; fluent section-by-section assembly; `build()` returns a plain string; no I/O, no side effects — a pure domain service
- `flask/modules/ai/prompts/__init__.py` — `generate_spec_prompt()`, `review_prompt()`, and `lint_braindump_prompt()` refactored to use `PromptBuilder`; the only callers of the builder in this module
- `flask/modules/implementation_guide/prompts.py` — `build_implementation_guide_prompt()` using `PromptBuilder`; called by the implementation guide route handler; receives context values already loaded server-side

**Patterns**: Builder — fluent construction of a complex object (the prompt string) from discrete, named sections. The sections are the units of snapshot testing. A section-level change produces a visible, attributable diff.

**Why not string templates or Jinja2**: Jinja2 would introduce a second templating layer with its own syntax and failure modes. The prompt sections are not HTML; they are structured text assembled in a fixed order. A fluent builder captures that fixed order explicitly and is testable without a template engine.

**Consumer**: Task 2 (Migrate Prompts to Flask), Task 4 (Bootstrap Facade — `BootstrapService` calls `build_implementation_guide_prompt()` as part of the spec-generation step).

---

### Template Generators

**Purpose**: Remove markdown generation from `new-project.component.ts`. `generateSpecIndex()`, `generateTimeline()`, and `generateReadme()` are template engines embedded in a UI component. They produce file content, not UI state. Their correct home is a server-side module where their output format can be locked by snapshot tests.

**Key Parts**:
- `flask/modules/templates/generators.py` — three stateless pure functions producing markdown strings; no I/O, no AI calls; output is deterministic given the same inputs
- Snapshot tests using `syrupy` — lock the exact output format; a format change produces a failing test, not a silent regression

**Patterns**: Pure function — no state, no side effects, deterministic output. Snapshot testing is the correct validation strategy for template generators because the value being protected is exact format stability, not a computed property.

**Why not Jinja2 here either**: Same reasoning as `PromptBuilder`. The templates are short, fixed-structure markdown strings. The Python f-string or concatenation approach already works and is directly readable. Introducing a templating engine adds a dependency and a failure mode without a proportionate benefit at this scale.

**Consumer**: Task 3 (Extract Template Generators), Task 4 (Bootstrap Facade — `BootstrapService` calls the timeline and readme generators as steps 3 and 4 of the orchestration sequence).

---

### Bootstrap Facade

**Purpose**: Replace the five-call orchestration loop in `NewProjectComponent.bootstrap()` with a single server-side workflow. The current loop requires the browser to remain open, offers no transactional recovery if a step fails, and places a `CONCURRENCY = 2` cap on the client — a server concern solved in the wrong layer.

**Key Parts**:
- `flask/modules/capability/routes.py` — two endpoints: `POST /api/capability/bootstrap` (accepts name and braindump, starts the workflow asynchronously, returns a project ID immediately) and `GET /api/capability/bootstrap/{id}/status` (returns current step, done flag, and optional error string)
- `flask/modules/capability/service.py` — `BootstrapService`; orchestrates the lint → spec generation → timeline → readme → project save sequence; calls `PromptBuilder` and template generators; this is an Application Service in the domain sense — it coordinates I/O and AI calls but contains no business logic of its own
- `flask/modules/capability/status.py` — in-memory dict keyed by project ID; stores step name, completion flag, and error; no persistence, no retry logic
- `BootstrapService` (Angular) — calls `POST /api/capability/bootstrap` once; polls `GET /api/capability/bootstrap/{id}/status` until `done` is true or `error` is set; exposes an observable that the component subscribes to

**Patterns**: Facade — a single entry point hides a multi-step internal workflow from the caller. The client's contract is simple: POST once, poll until done. Application Service — `BootstrapService` on the Flask side is the orchestration layer; it calls domain services (`PromptBuilder`, template generators) without containing business rules itself.

**Why in-memory status and not a database**: The tool has no auth, no multi-user state, and no persistence requirement for job history. An in-memory dict is correct for a single-user dev tool running on localhost. The trigger for a database upgrade is explicit: auth lands, multi-user state becomes real. Building a `bootstrap_jobs` table before that point is infrastructure nobody has asked for.

**Why polling and not SSE**: SSE would require an additional Flask extension, connection lifecycle management, and Angular `EventSource` handling. Polling with a short interval (one to two seconds) achieves the same user experience for a workflow that completes in under two minutes. SSE is the correct upgrade when real-time streaming of step output becomes a named user requirement.

**Consumer**: Task 4 (Implement Bootstrap Facade). Also consumes `PromptBuilder` (Task 2) and template generators (Task 3), so Task 4 depends on both.

---

### OpenAPI Consolidation

**Purpose**: Update `flask/openapi.yaml` to reflect the actual route surface after Tasks 1–4 complete, regenerate DTOs on both sides, and verify the CI drift check passes. This task is not architectural invention — it is accounting. It ensures the contract stays ahead of the implementation rather than trailing it.

**Key Parts**:
- `flask/openapi.yaml` — updated to 16 routes; four individual context paths removed, one parameterised context path added; four bootstrap-step paths removed, two capability paths added
- `make dto` — regenerates `flask/dtos/models.py` via `datamodel-codegen` and `src/app/models/api.d.ts` via `openapi-typescript`; both are gitignored; CI runs `make dto && git diff --exit-code` to catch drift before merge

**Consumer**: Task 5 (Flatten OpenAPI Surface), which depends on Tasks 1 and 4 completing first.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend services | Angular `ContextService`, `BootstrapService` | Thin HTTP wrappers. `ContextService` is parametric; `BootstrapService` adds polling. No business logic remains in TypeScript. |
| Backend orchestration | Flask `BootstrapService` in `capability/` module | Application Service pattern: coordinates AI calls and file operations without encoding business rules. ~80 lines. |
| Prompt assembly | `PromptBuilder` Python class | Pure domain service. Fluent API, no I/O, snapshot-testable. Replaces string concatenation in two places: the implementation guide and the spec generator. |
| Template generation | Pure Python functions in `templates/generators.py` | Stateless, deterministic, snapshot-tested. No templating engine needed at this scale. |
| Job status | In-memory Python dict | Correct for single-user dev tool. Zero dependencies. Explicit upgrade trigger: auth and multi-user state. |
| API contract | `openapi.yaml` → generated DTOs | Both sides generated from one source of truth. Drift caught by CI before merge. |
| Snapshot testing | `syrupy` (Python) | Purpose-built for snapshot assertions. Produces readable diffs when format changes. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| In-memory status tracking for bootstrap jobs | No auth, no multi-user state, no persistence requirement. A database table before those conditions exist is speculative infrastructure. | Job state is lost on server restart. Acceptable for a sub-two-minute workflow on a dev tool. Not acceptable once auth and multi-tenancy land — that is the named upgrade trigger. |
| Polling over SSE for bootstrap status | Polling requires no additional Flask extension, no connection lifecycle management, and no Angular `EventSource` setup. The user experience difference for a two-minute workflow is negligible. | SSE would give finer-grained step streaming. Polling gives one-to-two second granularity. At this scale, the implementation cost of SSE is not justified by the UX delta. |
| Keep AI text operation endpoints unchanged | The seven AI text endpoints (`rewrite`, `generate`, `iterate`, `generate-spec`, `review`, `lint-braindump`, `scan`) are correctly shaped and non-redundant. Flattening them further would require renaming without gaining clarity. | The surface stays slightly larger than the minimum. The alternative (a single `POST /api/ai/text/transform` with an operation enum) would require DTO changes, route renames, and component updates for no user-facing benefit. |
| `PromptBuilder` as a plain class, not a module-level function | Fluent construction requires accumulated state (sections appended in order). A class is the correct container for that state. | A pure function would require passing all sections as arguments simultaneously, losing the readability benefit of fluent assembly. |
| No `CapabilityStrategy` for project types | Bootstrap v1 is generic. A Strategy abstraction calibrated by one concrete case locks in a shape before a second case exists to validate it. | If a user asks for type-specific scaffolding (CLI vs. web app), the Strategy extraction must happen then. The cost of retrofitting is one additional class and one enum field — low enough that deferring is correct. |
| Delete the four context services, do not deprecate | The tool has no external API consumers. Deprecation shims add maintenance surface with no benefit. | A hard delete means any missed import reference fails at compile time, not silently at runtime. This is the desired failure mode. |

---

## Patterns

### Facade (Bootstrap Endpoint)

**When to use**: A workflow involves multiple sequential steps, each of which can fail independently, and the caller should not be responsible for orchestrating the sequence.

**How it works**: The caller submits a single request and receives a handle (in this case, a project ID). The facade executes the internal steps in order, tracking progress and failure state. The caller polls the status endpoint until the workflow completes or errors. The internal step sequence is invisible to the caller.

**Example in this system**: `POST /api/capability/bootstrap` hides the lint → spec → timeline → readme → save sequence. The Angular `BootstrapService` knows the facade exists but not what it contains. If the internal sequence changes (a new step is added, retry logic is introduced), the Angular service is unaffected.

---

### Builder (Prompt Assembly)

**When to use**: A complex object (here, a structured text string) is assembled from discrete, named parts in a fixed order, and each part must be independently testable.

**How it works**: A `PromptBuilder` instance accumulates sections via chained method calls. `build()` combines them in declaration order. Each section is a named unit — snapshot tests assert its exact content. A section change produces an attributable diff.

**Example in this system**: `PromptBuilder` replaces the `buildImplementationGuidePrompt()` concatenation chain in `implementation-guide.service.ts`. The builder lives in `flask/modules/ai/prompts/builder.py`; its caller (`build_implementation_guide_prompt()`) lives in `flask/modules/implementation_guide/prompts.py`. No prompt construction exists in any route handler or TypeScript file.

---

### Structural Test as Architecture Enforcer

**When to use**: After a violation is encountered (or a rule is established that would have prevented a past violation). Not pre-emptively.

**How it works**: One grep + one assertion + one failure message naming the rule and the fix. Fast, no framework needed. Catches drift that code review misses.

**Example in this system**: After prompt migration, a structural test greps `src/app/` for `"You are "` in TypeScript files and fails if any match is found. A second test greps route handler files for prompt string literals. These tests are added once the migration is complete — they encode the state the cleanup achieved, not the state it aspired to.

---

## Execution Flow

```
[Phase 1 — Parallel]
  Task 1: Unify Context Services ─────────────────────────────┐
  Task 2: Migrate Prompts to Flask ────────────────────────────┤
  Task 3: Extract Template Generators ─────────────────────────┘
                                                               │
[Phase 2 — Sequential, depends on Task 2]                      ▼
  Task 4: Implement Bootstrap Facade
  (consumes PromptBuilder from Task 2 and generators from Task 3)
                                                               │
[Phase 3 — Sequential, depends on Tasks 1 and 4]              ▼
  Task 5: Flatten OpenAPI Surface
  (reflects all route changes from Tasks 1 and 4)
```

Tasks 1, 2, and 3 share no dependencies and can be executed in parallel. Task 4 depends on Task 2 (the bootstrap service calls `PromptBuilder` and template generators that must exist server-side first) and benefits from Task 3 completing first, though it can start with stub generators if needed. Task 5 is a consolidation step and must follow both Task 1 (context route changes) and Task 4 (bootstrap route changes) to produce an accurate final surface.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview