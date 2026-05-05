# 🔍 Architecture Cleanup — Analysis

## The Problem
Three categories of business logic live in the Angular frontend where they don't belong: system prompt construction (`implementation-guide.service.ts:165–368`), bootstrap workflow orchestration (5 chained HTTP calls in `new-project.component.ts`), and markdown template generation. Four near-identical context services duplicate the same GET/PUT contract across separate files. The fix moves all three categories server-side and collapses the context services to one parametrised interface.

## Hard Constraints
- **Blocked on Test Enhancement epic** — E2E coverage must exist before refactoring the endpoints it exercises. Not negotiable.
- **Backend runtime is unresolved and gates every task**: `spec-doc/CLAUDE.md` says Express (`server.js`, port 3100); builder profile says "Express for tooling"; brain dump writes `flask/modules/` throughout. Flag as the first decision to make.
- **`openapi.yaml` is the contract source** — DTOs are generated, not hand-written; any endpoint change starts there, not in route files.
- **No third-party auth or external services** for status tracking. In-memory dict for MVP is consistent with builder defaults.

## Open Questions
- **Flask or Express?** The brain dump adds a full Flask module tree (`flask/modules/capability/`, `flask/modules/templates/`) to a codebase that runs Express today. Options: (A) add Flask as a second process alongside Express, (B) rewrite Express in Flask, (C) keep Express and port the same patterns there. This decision gates every backend task.
- **Bootstrap status persistence**: In-memory dict loses state on restart. Options: (A) accept the loss — restart means retry, acceptable for a dev tool, (B) persist to a flat JSON sidecar file, (C) defer to DB when auth lands. Pick A or B before writing the task; C is already correctly deferred.
- **PromptBuilder versioning**: Brain dump mentions `PromptBuilder(version="2")`. Options: (A) ship v1 only, add the version param when a second prompt format has a named user, (B) build versioning in from day one. Option A is consistent with "second consumer triggers extraction."

## Dependencies & Sequencing
- Tasks 1–3 (context unification, prompt migration, template extraction) have no mutual dependency — can run in parallel.
- Task 4 (Bootstrap Facade) depends on Task 2: prompts must live server-side before bootstrap orchestrates them server-side.
- Task 5 (OpenAPI flattening) depends on Tasks 1 and 4: routes must be consolidated before DTOs are regenerated.
- Task 6 (tests + docs) depends on all prior tasks completing.

## Explicitly Out of Scope
- **`ProjectRepository` interface with swappable implementations** (`FilesystemProjectRepository`, `InMemoryProjectRepository`, future `PgProjectRepository`) — one consumer today (filesystem CRUD), no second backend named. Defer until auth + multi-user lands.
- **`BootstrapResult` Anti-Corruption Layer DTO** — `file_parser.py` works; no second caller of the bootstrap result exists yet. Defer until a second consumer requires the normalised shape.
- **Strategy pattern for capability types** (web app / CLI / library) — correctly self-deferred in the brain dump. Re-scope when a user explicitly requests type-specific scaffolding.
- **PromptBuilder multi-version support** — ship the concrete v1 builder; extract versioning when a second prompt format has a named user.
- **Week-by-week implementation timeline and effort estimates** — belongs in `epic.md`, not analysis.
- **Code blocks with implementation snippets** (TypeScript + Python throughout the brain dump) — belongs in implementation guides, not here.