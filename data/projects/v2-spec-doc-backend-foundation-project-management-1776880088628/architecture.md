# 🏗️ Solution Architecture: V2 Spec Doc Backend — Foundation + Project Management

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The core architectural insight is that the frontend is already working — the Express monolith delivers the right API, the Angular app consumes it correctly, and 64 project directories exist in a known layout. This migration's only job is to rebuild what's under the surface without disturbing what's above it. The API contract is not a design problem; it's a constraint. Flask must satisfy it exactly.

The structure mirrors the Bubls backend: an app factory owns startup and module registration, each domain area is a Blueprint with its own route handlers and helpers, and all modules register into the factory rather than importing from a shared global. This pattern works at scale because adding a new capability means adding a folder, not editing a shared file. Phase 2 AI endpoints register the same way — the factory doesn't change, only the module list does.

The chain module occupies a different tier from the CRUD modules. Where Project CRUD and Context File expose HTTP routes, the chain module exposes no endpoints in Phase 1 — it's internal infrastructure that Phase 2 will wire up. This separation is intentional: it lets the chain module be ported and tested in isolation from any endpoint behavior, and it means Phase 2 AI work starts on a tested foundation rather than code written in the middle of an integration effort.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| API contract is the ceiling, not the floor | Flask must match the Express response shapes exactly. Any deviation breaks Angular without a code change. The contract is reverse-engineered from the live Express server before a single Flask route is written. |
| Ship the car, not the engine | Chain module ships as internal infrastructure only. No endpoints wrap it in Phase 1 because no Phase 1 feature calls it. Endpoints land in Phase 2 when there's an actual consumer. |
| Port proven patterns, don't invent parallel ones | App factory, Blueprint registration, CORS config, and the chain adapter are copied from Bubls. They're already tested against production workloads. Inventing spec-doc-specific equivalents adds risk with no upside. |
| Parallel runnability over in-place replacement | Flask runs on 3101 so both backends serve simultaneously during migration. Cutover is a one-line ENV change in the Angular dev proxy, not a deployment gate or a code change. |
| Test isolation over integration speed | CRUD endpoints have zero AI dependency, so their tests run without any Claude call. The chain module tests run in mock-provider mode. Nothing in Phase 1 requires a live AI call to pass. |

---

## System Boundaries

### What This System Includes

- App factory and Blueprint module registry, adapted from Bubls for spec-doc's port and CORS origins
- Project CRUD module: create, list, get, update-file, delete against the `projects/` filesystem layout
- Context file module: read and write for builder profile, principles, codebase context, and reference files
- Chain module ported from Bubls: adapter interface, three provider implementations (Claude SDK, CLI subprocess, mock), file marker parser, context block loader — internal only, no HTTP surface

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| AI text endpoints (rewrite, generate, iterate) | No Phase 1 consumer exists. The chain module provides the internal capability; endpoints land in Phase 2 when AI features are defined. |
| Walker (filesystem scanner) | Named in the brain dump as Phase 2 scope. The scan endpoint that calls it doesn't exist yet; building Walker now solves a problem that won't exist until Phase 2. |
| Streaming (SSE) | Deferred until AI endpoints are defined in Phase 2 and their streaming behavior can be specified against a real consumer. |
| Database, auth, user management | spec-doc is a single-user filesystem tool. Solving multi-user persistence now violates the "ship the car" principle and adds complexity with no Phase 1 user. |
| Frontend changes | Zero Angular modifications is a hard constraint, not a goal. If any Flask route requires a frontend change to work, the Flask route is wrong. |
| Projects/ directory migration | All 64 existing directories load as-is. This is verified before Flask is written, not assumed. If any directory fails to load, the bug is in the route handler, not the data. |

---

## Component Design

### App Factory and Module Registry

**Purpose**: Provides the startup entry point and the registration mechanism that all modules plug into. This is what allows Phase 2 modules to be added without touching existing code.

**Key Parts**:
- `create_app` function — instantiates the Flask app, applies CORS for `localhost:4201`, registers Blueprints from the enabled module list, and mounts the health route. This is the only place that knows about all modules; modules don't know about each other.
- `ENABLED_MODULES` config — a list that controls which Blueprints are registered at startup. In Phase 1, this contains the project and context modules. Phase 2 AI modules are added to this list, not to any existing module.
- Health route — `GET /health` returns a minimal response that confirms the Flask process is alive. The Angular frontend doesn't call this, but it's the integration test baseline that verifies the factory wired up correctly.

**Consumers**: Task 1 (API Contract + Flask Scaffold) defines and builds this component. Tasks 2, 3, and 4 each register their Blueprints into it.

**Patterns**: App factory pattern (same as Bubls `create_app`). CORS applied at factory level, not per-Blueprint, because the origin policy is the same for all routes.

---

### Project CRUD Module

**Purpose**: Serves the Angular sidebar and editor by exposing create, list, get, update-file, and delete operations over the `projects/` directory. This is the highest-traffic module — every sidebar load and every auto-save call passes through it.

**Key Parts**:
- Project Blueprint — five route handlers that map to the five operations. Each handler is thin: validate the path, dispatch to a filesystem helper, return the response shape.
- Filesystem helpers — read directory structure, read/write individual files, delete directories. These are plain functions, not classes, because they have exactly one consumer (the Blueprint's route handlers) and no shared state.
- Path resolution — all operations anchor to the `projects/` root and reject traversal attempts. This is a security boundary: user-supplied project IDs must resolve to paths within `projects/`, never above it.

**Consumers**: Task 2 (Project CRUD Module) builds this. The Angular `ProjectsService` and sidebar component are the runtime consumers — their behavior against Flask must be identical to their behavior against Express.

**Patterns**: Blueprint registration into the app factory. Thin route handlers with extracted filesystem helpers, not business logic in handlers.

---

### Context File Module

**Purpose**: Serves the four context panels in the Angular frontend — builder profile, principles, codebase context, and reference files. Each panel reads and writes a fixed path; this module is a thin filesystem read/write layer with no transformation logic.

**Key Parts**:
- Context Blueprint — eight route handlers (read + write per context type). The paths are fixed and known; there's no dynamic routing over context file types.
- Path map — a static mapping from context type name to filesystem path. Centralizing this in one place means if a path changes, it changes in one location, not in every handler.

**Consumers**: Task 3 (Context File Module) builds this. The Angular context panels are the runtime consumers.

**Patterns**: Blueprint registration. Static path map rather than dynamic path construction, because the four context types are named in the epic and no fifth type is anticipated.

---

### Chain Module

**Purpose**: Provides the internal AI call infrastructure that Phase 2 endpoint modules will use. Ported from the Bubls backend where it powers text chains and braindump-to-docs generation. Exposes no HTTP surface in Phase 1.

**Key Parts**:
- Chain adapter interface — the single boundary between feature code and provider implementations. Any module that makes an AI call goes through the adapter; it never calls a provider directly. This is ELA Pattern #1: one adapter, provider implementations behind it.
- Claude SDK provider — calls the Anthropic Python SDK directly. This is the production path.
- CLI subprocess provider — shells out to `claude -p`. This is the fallback path and the current Express approach; it exists so the chain module can be substituted for the current mechanism without behavioral regression.
- Mock provider — returns deterministic responses for test execution. This is what makes chain module tests fast and dependency-free.
- File marker parser — parses the `<!-- FILE: path -->` marker format that the existing Express backend uses to split generated content into named files. Ported from Bubls, where the same format is used for braindump output.
- Context block loader — loads builder profile, principles, and codebase context files into a structured object that gets injected into prompts. Phase 2 AI endpoints will call this before constructing their chain inputs.

**Consumers**: Task 4 (Chain Module Port) builds and tests this. Phase 2 AI operation endpoints are the first runtime consumers. No Phase 1 endpoint calls into this module.

**Patterns**: Adapter pattern with provider implementations. Mock provider as a first-class citizen, not an afterthought — tests pass without a live Claude call.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend runtime | Python + Flask | Direct port from Bubls. Flask's Blueprint system is the foundation of the modular pattern this migration is built around. The pattern is proven; switching languages at the module level would require re-proving it. |
| API framework | Flask Blueprints | Blueprint-per-module is how Bubls achieves isolation. Each module registers itself; they don't import from each other. This is the pattern that makes Phase 2 additions safe. |
| Filesystem | Python `pathlib` | The `projects/` layout is already established. No ORM, no migration, no schema — the filesystem is the database. `pathlib` handles path construction and traversal rejection cleanly. |
| CORS | `flask-cors` | Applied at factory level for `localhost:4201`. Angular's dev proxy points there; no other origin is in scope. |
| AI providers | Anthropic Python SDK + subprocess fallback + mock | Three providers behind one adapter boundary. SDK is production. CLI subprocess is the current mechanism, preserved as a fallback. Mock is for tests. The adapter hides which is in use. |
| Test runner | pytest | Matches the Bubls backend. Chain module tests are ported as-is and run with pytest; no test framework change needed. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Flask on 3101, not 3100 | Running both backends simultaneously during migration is safer than replacing in-place. If Flask has a regression, the Express backend is still running and the frontend can revert with a one-line proxy change. Debugging with both live is faster than debugging a black-box replacement. | Angular's `proxy.conf.json` must point to 3101 during testing; at cutover it switches to 3100 (or Flask takes 3100). This adds one ENV swap step to the migration plan. |
| Contract locked before Flask is written | Express is the source of truth for what Angular expects. Documenting every route, method, payload, and response shape before writing Flask means regressions are caught at the contract level, not discovered when an Angular panel fails silently. | This adds a contract-documentation step before any Flask code exists. The cost is one day; the benefit is that Flask is built to a known spec, not reverse-engineered during debugging. |
| No migration for `projects/` | The 64 existing directories are loaded against Flask before any route code is written, confirming the filesystem layout is already compatible. Migration is only added if this verification fails. | If a directory structure assumption is wrong, this surfaces as a failed load test before Flask routes are built, not as a runtime error after. The cost of the verification step is one day of investigation risk; the cost of skipping it is silent data loss. |
| Chain module ships with no endpoints | Phase 1 has no AI consumer. Exposing endpoints before there's a feature that calls them means writing, testing, and maintaining a surface that delivers no user value. Phase 2 defines what that surface looks like; it's better to let Phase 2 drive the endpoint shape than to constrain it now. | The chain module sits in the codebase with no public surface until Phase 2 wires it up. This is intentional — it's infrastructure, not a feature. |
| Four context types as a static path map, not dynamic routing | The epic names exactly four context types: builder profile, principles, codebase context, reference files. There is no fifth type in scope. Dynamic routing over content types would be an abstraction of one concrete case, which the builder principles explicitly forbid. | If a fifth context type is added later, the path map gets a fifth entry. This is a one-line change, not a refactor. The static map is not a constraint; it's the right level of complexity for what exists. |

---

## Patterns

### App Factory with Blueprint Registration

**When to use**: At the startup boundary, and every time a new module is added.

**How it works**: `create_app` is the single entry point. It applies CORS, iterates `ENABLED_MODULES`, imports each module's Blueprint, and calls `register_blueprint`. No module is imported at the file level; all imports happen inside the factory function. This means module registration failures surface at startup with a clear error, not at first request.

**Example in this system**: Task 1 builds the factory with Project and Context Blueprints in `ENABLED_MODULES`. Task 4's Chain module is registered as an internal package but adds no Blueprint. Phase 2 AI endpoint modules each add their Blueprint to the list.

---

### Adapter + Provider (ELA Pattern #1)

**When to use**: At every AI call boundary — any module that generates text or invokes Claude goes through this boundary, never directly to a provider.

**How it works**: The adapter defines an interface (a call shape: input text, system prompt, context) and delegates to whichever provider is configured. The calling code doesn't know whether it's talking to the SDK, the CLI, or the mock. Provider selection happens at factory startup based on configuration, not at call time.

**Example in this system**: Task 4 ports the adapter and three providers. Phase 2 AI endpoint modules call the adapter; they never import a provider directly. Mock provider is always available for tests — no environment setup, no API key, no latency.

---

### Thin Route Handlers with Extracted Helpers

**When to use**: In every Blueprint, for every route.

**How it works**: Route handlers validate inputs, call a helper function, and return the response shape. Business logic and filesystem operations live in helper functions, not in handlers. This keeps handlers testable at the HTTP level (mock the helper) and keeps helpers testable at the unit level (call them directly).

**Example in this system**: Project CRUD Blueprint — each of the five handlers calls a filesystem helper. Context Blueprint — each of the eight handlers calls a read or write helper. Helpers are module-private functions, not shared utilities, because each module's filesystem operations are specific to its data layout.

---

## Execution Flow

```
[Phase 1]
  Task 1: Scaffold ──→ Task 2: Project CRUD
  (app factory,        (consumer: Angular sidebar)
   CORS, health)   ──→ Task 3: Context Files
                        (consumer: Angular panels)
                   ──→ Task 4: Chain Module
                        (internal, no endpoints)

[Phase 2]
  Chain Module ──→ AI Endpoint Modules
  (Task 4)          (register into factory,
                     call adapter for AI ops)
```

Tasks 2, 3, and 4 all depend on Task 1's scaffold because they all register into the app factory. Tasks 2 and 3 are independent of each other and of Task 4, so they can proceed in parallel once Task 1 is complete. Task 4 is independent of 2 and 3 — it's an internal port with its own test suite and no HTTP surface to verify against the Angular frontend.

The Phase 1 → Phase 2 boundary is the chain module. Phase 2 inherits a tested adapter and three providers, a working app factory, and a verified API contract. It adds endpoints — it doesn't retrofit infrastructure.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview