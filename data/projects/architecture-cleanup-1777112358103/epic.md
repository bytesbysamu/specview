# 🎯 Epic: Architecture Cleanup

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Spec-doc's current architecture places business logic — system prompt construction, workflow orchestration, and markdown template generation — in the Angular frontend. This is a pattern inherited from the defunct Express backend: the client owns configuration that belongs on the server. At single-user localhost scale this works, but it creates three compounding liabilities. System prompts are unversioned TypeScript string literals that drift silently with each Angular rebuild. Bootstrap orchestration (five sequential HTTP calls managed by the component) offers no retry safety and requires the browser to stay open for up to ninety seconds. Four parallel context services implementing the same two-method contract represent copy-paste debt that multiplies every time a new context type is needed.

Fixing this before the launch-prep epic removes the architectural drag from a product that is otherwise ready to scale. Moving prompts, orchestration, and templates server-side costs two weeks. Not moving them means every future feature (auth, multi-tenancy, rate limiting) is built on top of a client that knows too much.

The secondary benefit is a smaller Angular codebase. Collapsing four identical context services into one parametrised interface and removing `~400` lines of prompt-building and template-generation code leaves services that are thin HTTP wrappers — exactly the right shape for a frontend that should be a rendering layer, not a business logic layer.

**Value Proposition**: Move all business logic server-side so the Angular frontend becomes a thin rendering shell, enabling reliable bootstrap, testable prompts, and a clean foundation for the launch-prep epic.

---

## Scope

### What This Epic Covers

- **Context service unification** — collapse four near-identical Angular services (`BuilderService`, `PrinciplesService`, `CodebaseService`, `ReferencesService`) into one parametrised `ContextService`, backed by a single `GET /api/context/{key}` / `PUT /api/context/{key}` endpoint
- **Prompt migration to Flask** — extract `buildImplementationGuidePrompt()` and all helper methods from `implementation-guide.service.ts:165–368` into a server-side `PromptBuilder` class at `flask/modules/ai/prompts/builder.py`
- **Template extraction to Flask** — move `generateSpecIndex()`, `generateTimeline()`, and `generateReadme()` from `new-project.component.ts` to `flask/modules/templates/generators.py` as pure Python functions with snapshot tests
- **Bootstrap facade** — replace the five-call orchestration loop in `NewProjectComponent.bootstrap()` with a single `POST /api/capability/bootstrap` endpoint and a `GET /api/capability/bootstrap/{id}/status` polling endpoint, backed by an in-memory status tracker
- **OpenAPI consolidation** — update `flask/openapi.yaml` to reflect the new surface (21 → 16 routes), regenerate DTOs on both sides, verify CI drift check passes

### What This Epic Does NOT Cover

- ❌ **Database-backed status persistence** — in-memory dict is sufficient for a dev tool; upgrade deferred until auth lands
- ❌ **`ProjectRepository` interface with swappable implementations** — one consumer today (filesystem CRUD); extract when a second backend is named
- ❌ **Strategy pattern for capability types** (web app / CLI / library) — bootstrap v1 is generic; extract when a user explicitly requests type-specific scaffolding
- ❌ **`BootstrapResult` Anti-Corruption Layer DTO** — `file_parser.py` works; no second caller of the bootstrap result exists yet
- ❌ **PromptBuilder multi-version support** — ship the concrete v1 builder; add versioning when a second prompt format has a named user
- ❌ **Claude SDK migration** — `CHAIN_PROVIDER=cli` is the current runtime; SDK migration is a separate epic triggered by production deployment

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Unify Context Services** | None | 2 | 1 day | High |
| 2 | **Migrate Prompts to Flask** | None | 1, 3 | 1.5 days | High |
| 3 | **Extract Template Generators** | None | 1, 2 | 1 day | Low |
| 4 | **Implement Bootstrap Facade** | 2 | — | 2 days | High |
| 5 | **Flatten OpenAPI Surface** | 1, 4 | — | 0.5 days | High |

### Task 1: Unify Context Services

Collapse `BuilderService`, `PrinciplesService`, `CodebaseService`, and `ReferencesService` into a single `ContextService` that accepts a `ContextKey` parameter. On the backend, replace four separate Flask routes with one `GET /api/context/{key}` / `PUT /api/context/{key}` route. Update every component that currently injects the four individual services.

**Port budget**: ~1 new Angular service file (~40 lines) + 1 new Flask route file (~30 lines) + updates to importing components; no caching layer, no key validation beyond an enum, no registry auto-discovery — second context type triggers none of that.

### Task 2: Migrate Prompts to Flask

Create `flask/modules/ai/prompts/builder.py` with a `PromptBuilder` class that assembles sections fluently. Refactor `generate_spec_prompt()`, `review_prompt()`, and `lint_braindump_prompt()` in `flask/modules/ai/prompts/__init__.py` to use the builder. Add a new `build_implementation_guide_prompt()` in `flask/modules/implementation_guide/prompts.py`. Remove `buildImplementationGuidePrompt()` and all helper methods from `implementation-guide.service.ts`; replace with a call to the new Flask endpoint.

**Port budget**: ~120-line `PromptBuilder` class + snapshot tests for each section; no versioning parameter, no provider-routing, no prompt-caching — those ship when a second prompt format or a named second consumer exists.

### Task 3: Extract Template Generators

Move `generateSpecIndex()`, `generateTimeline()`, and `generateReadme()` from `new-project.component.ts` to `flask/modules/templates/generators.py` as stateless pure functions. Add snapshot tests using `syrupy` to lock the exact output format. Update the Angular component to call a new `GET /api/templates/{name}` endpoint instead of running the generation locally.

**Port budget**: ~80 lines of Python across three generator functions + snapshot fixture files; no Jinja2 templating engine, no user-customisable template variables — those are a second-consumer concern.

### Task 4: Implement Bootstrap Facade

Add `flask/modules/capability/routes.py` with `POST /api/capability/bootstrap` (accepts `{name, braindump}`, returns `{projectId}`) and `GET /api/capability/bootstrap/{id}/status` (returns `{step, done, error}`). Implement `BootstrapService` in `flask/modules/capability/service.py` to orchestrate the lint → spec → timeline → readme → save sequence. Track job state in an in-memory dict in `flask/modules/capability/status.py`. Create a new Angular `BootstrapService` that calls the single endpoint and polls status. Remove the five-call loop and `CONCURRENCY = 2` cap from `new-project.component.ts`.

**Port budget**: ~80-line Flask module (routes + service + status tracker) + ~60-line Angular service; no retry/backoff logic, no persistent job table, no SSE streaming — in-memory dict is correct for a dev tool until auth introduces multi-user state.

### Task 5: Flatten OpenAPI Surface

Update `flask/openapi.yaml` to reflect the consolidated surface: add `/api/context/{key}`, `/api/capability/bootstrap`, `/api/capability/bootstrap/{id}/status`; remove the four individual context paths and the four bootstrap-step paths. Run `make dto` to regenerate `flask/dtos/models.py` and `src/app/models/api.d.ts`. Verify CI drift check (`make dto && git diff --exit-code`) passes clean.

**Port budget**: YAML edits to ~16 paths + DTO regeneration on both sides; no new authentication schemes, no versioning prefix (`/v2/`), no deprecation shims — the tool has no external API consumers.

---

## Success Criteria

This epic is complete when:

- ✅ Zero prompt construction strings exist in any TypeScript file (verified by structural test: `grep -r "You are" src/app/ --include="*.ts"` returns no matches)
- ✅ Zero template generation functions exist in Angular components (verified by structural test: `grep -r "generateSpecIndex\|generateTimeline\|generateReadme" src/app/` returns no matches)
- ✅ Four individual context services are deleted; all component imports resolve to `ContextService`
- ✅ `POST /api/capability/bootstrap` completes a full lint → spec → timeline → readme → save flow end-to-end in a passing integration test
- ✅ `make dto && git diff --exit-code` passes clean (no DTO drift from the updated OpenAPI spec)
- ✅ All pre-existing E2E tests pass without modification (UI behavior is unchanged; only the HTTP layer changed)
- ✅ Backend route handlers are ≤30 lines each (new routes included)

---

## Non-Goals

- ❌ **Auth, rate limiting, or multi-tenancy** — this cleanup is pre-auth; those belong in the launch-prep epic
- ❌ **SDK migration (`CHAIN_PROVIDER=sdk`)** — deferred until production deployment; CLI subprocess is acceptable for a dev tool
- ❌ **Performance optimisation of prompt assembly** — the bottleneck is AI latency, not context loading; optimise when profiling shows otherwise
- ❌ **Effort estimates and week-by-week timeline** — tracked in [Timeline](./timeline.md), not here

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview