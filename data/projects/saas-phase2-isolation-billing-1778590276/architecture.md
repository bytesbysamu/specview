# 🏗️ Solution Architecture: SaaS Phase 2a — Project Isolation & Multi-Tenancy

## Architecture Overview

This is a wiring job, not a design job. Every architectural seam required for project isolation already exists in the codebase: the `Project` SQLModel carries a `user_id` foreign key, the `ProjectRepository` protocol defines `list_for_user()` and `get_by_slug()`, the `SqlProjectRepository` implements all five protocol methods with atomic create and rollback semantics, the `@require_auth` decorator populates `g.current_user` on every request, and the file-history routes already demonstrate the `current_app.project_repository` dependency-injection pattern. The work is connecting these pre-laid wires so that every project route enforces ownership — not inventing new abstractions.

The key architectural insight is a **dual-store separation of concerns**. After this change, the system has two clearly bounded stores: the **database** owns identity and ownership (who created the project, who can access it), while the **filesystem** owns content (the markdown spec files that make up a project). Today `service.py` conflates both responsibilities — it reads `project.json` from disk for metadata and serves file content, with no user awareness. Post-change, `service.py` is scoped down to its real job (file content operations), and the repository becomes the authoritative source for project existence and access control. Routes flow through the repository first for ownership verification, then delegate to `service.py` for content when the caller is authorized.

The security model is belt-and-suspenders, converging on the same pattern proven across Trendfy, Bubls, and Springular: **filter at the data layer** (repository methods scope queries by `user_id`) AND **verify at the route layer** (an ownership-checking decorator returns 403 on mismatch). Neither layer alone is sufficient — query filtering prevents data leaks in listings, while explicit ownership checks on single-resource routes give clear error signals and prevent direct-URL attacks.

## Design Principles

| Principle | Application in This Epic |
|-----------|--------------------------|
| **P1 — Adapter Boundary** | The `SqlProjectRepository` is the only module that touches the `project` table. Routes never import SQLModel or run queries directly. `service.py` never touches the database. The repository is the single adapter for project identity and ownership. |
| **P2 — Thin HTTP Layer** | Route handlers validate input, call the ownership decorator, delegate to the repository or `service.py`, and return a response. No business logic in routes — ownership verification lives in a shared decorator, not inline in each handler. |
| **P4 — No Speculative Abstractions** | No `project_member` join table (one role, one user — a join table for one case is premature). No admin bypass flag (direct DB access suffices). No per-user slug namespacing (zero collision probability with one real user). No feature flag for cutover (1.5 days, one user, deploy-and-verify beats flag infrastructure). |
| **P5 — OpenAPI-First** | The 403 response code is added to project route definitions in `openapi.yaml`. The contract change is minimal — existing 200/404 responses stay, 403 is additive. |
| **P7 — File Size & Structure** | The ownership decorator is a single-purpose module. The repository implementation stays under 200 lines. No god-file accumulation — `routes.py` gets simpler (less filesystem logic), not more complex. |

## Component Design

### Dual-Store Model

**Purpose**: Separate project identity (who owns it) from project content (what's in it), using the right store for each concern.

The database `project` table becomes the system of record for which projects exist and who owns them. Every project listing, existence check, and access-control decision goes through the `SqlProjectRepository`. The filesystem directory at `data/projects/<slug>/` remains the content store for braindumps, analyses, epics, and all other markdown artifacts. This split means a project "exists" when it has a DB row — the filesystem directory is a content detail managed downstream.

This is not a new architectural concept for specview. The file-history feature (Pers-T4) already treats the repository as the authority for project resolution via `_resolve_project()` and delegates to `git_store` for content operations. Phase 2a extends this same pattern to every project route.

### SQL Project Repository Wiring

**Purpose**: Connect the existing `SqlProjectRepository` implementation to the Flask app context so all routes can access it.

The `SqlProjectRepository` class in `modules/data/projects/repository.py` already implements all five `ProjectRepository` protocol methods: `create()`, `get_by_slug()`, `list_for_user()`, `touch()`, and `delete()`. The `create()` method already implements DB-first ordering with rollback on git-store failure. None of this code needs to change — it was built for this moment.

The wiring follows the established pattern from `create_app.py` where `app.workflow_repository` is set as a Flask app attribute and accessed in routes via `current_app.workflow_repository`. Adding `app.project_repository = SqlProjectRepository()` in `create_app.py` (currently missing — this is the critical first step) completes the circuit. The file-history routes that already reference `current_app.project_repository` via `_resolve_project()` will begin working against a real implementation instead of returning `None` from the `getattr` fallback.

### Ownership Enforcement Decorator

**Purpose**: Make it structurally impossible to forget an ownership check on any project route.

Rather than repeating ownership verification inline in each route handler, a `@require_project_ownership` decorator encapsulates the pattern: load the project by slug from the repository, compare `project.user_id` against `g.current_user.id`, return 403 on mismatch, and attach the verified project to Flask's request context (`g.project`) for downstream use. Routes stack this decorator after `@require_auth`, which guarantees `g.current_user` is populated before the ownership check runs.

This decorator approach mirrors how `@require_auth` already works — it's a guard that short-circuits the request before the handler body executes. The decorator lives in the projects module alongside the repository it depends on. Routes that operate on a specific project (GET, PUT, DELETE by slug) use the decorator. The listing route (`GET /api/projects`) does not use the decorator — instead it calls `repository.list_for_user(g.current_user.id)` directly, which scopes the query at the data layer.

The decorator must cover ALL project routes that accept a slug parameter — not just CRUD routes. This includes `POST /<id>/repair`, `POST /<id>/coherence`, and the three file-history routes (`GET /<slug>/files/<filename>/history`, `GET /<slug>/files/<filename>/diff`, `POST /<slug>/files/<filename>/revert`). The file-history routes use `_resolve_project()` which only does a slug lookup — it does NOT check ownership, so the decorator is required on these routes as well.

The decorator also provides a natural hook for a future structural test: assert that every route function in `projects/routes.py` that accepts a project slug parameter is decorated with `@require_project_ownership`. This follows the same enforcement pattern as `test_structural.py` uses for adapter boundary guards.

### Route Layer Transition

**Purpose**: Move project routes from filesystem-only service calls to repository-backed ownership-aware calls.

The current route flow is: request → `@require_auth` → `service.py` filesystem function → response. The new flow is: request → `@require_auth` → `@require_project_ownership` (for single-project routes) → repository for identity/ownership → `service.py` for content operations → response.

This changes the **control flow**, not the data model. The `service.py` functions for reading and writing file content remain unchanged — they still accept a filesystem path and operate on markdown files. What changes is that `service.py` is no longer the entry point for determining which projects exist or who can access them. It becomes a downstream content utility called only after the repository has confirmed the project exists and the caller is authorized.

For the listing route, the repository's `list_for_user()` replaces the filesystem scan. The returned `Project` records carry the slug, which the route uses to read content from the filesystem path. This means the listing response still includes file content — the data source for "which projects" shifts from filesystem to database, but the data source for "what's in them" stays on disk.

### Dual-Write Project Creation

**Purpose**: Ensure new projects are recorded in both the database (for ownership) and the filesystem (for content) atomically.

The `SqlProjectRepository.create()` method already implements the correct ordering: DB insert first, then git-store initialization, with DB rollback if the filesystem operation fails. This means `POST /api/projects` delegates to `repository.create(user_id=g.current_user.id, ...)` and the atomic dual-write is handled inside the repository — the route does not orchestrate the two-phase write.

The failure mode is clean: if the filesystem operation fails, the DB row is deleted and the caller receives an error. No orphan DB rows, no orphan directories. The inverse ordering (filesystem first, DB second) would leave orphan directories that block future creation attempts due to slug collision on retry. DB-first avoids this because a failed DB row leaves no trace.

### Filesystem-to-DB Migration

**Purpose**: Backfill `project` table rows for all 41 existing filesystem-only projects so they're visible under the new ownership model.

The migration script in `scripts/` reads each `data/projects/<slug>/project.json`, creates a corresponding `Project` row in the database, and assigns all projects to a user looked up by `--user-email` parameter rather than a hardcoded user ID. This protects against DB rebuilds or re-seeding where Sam's ID might change.

Idempotency is critical: the script checks whether a row with the given slug already exists before inserting. Running the script twice produces the same result. Post-run verification compares the count of DB rows against the count of filesystem project directories — a mismatch indicates partial failure.

**Deployment ordering matters.** The migration script must run and verify successfully before ownership-enforced routes are deployed. If ownership enforcement activates before the migration runs, Sam is locked out of all 41 projects because none have DB rows and the repository returns nothing. The deployment sequence is: deploy code with migration script → run migration → verify row count → deploy ownership-enforced routes. In practice, since this is a single deploy, the migration script runs as part of the deployment process before the app starts serving traffic.

### Frontend 403 Handling

**Purpose**: Ensure the Angular SPA distinguishes between "project doesn't exist" (404) and "you don't have access" (403) in the UI.

The Angular project service currently handles 404 responses for missing projects. Adding 403 handling means the service can surface a distinct "access denied" message rather than a generic "not found" error. The project list naturally scopes to the authenticated user's projects because `GET /api/projects` returns only owned projects — no frontend filtering logic is needed.

This is the lowest-effort component because the behavioral change is server-side. The frontend simply needs to recognize a new HTTP status code and display the appropriate message.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Ownership store | SQLite via SQLModel (existing `project` table) | Table and FK already exist in `0001_initial_schema.py`. No new infrastructure — just rows in an empty table. |
| Content store | Filesystem at `data/projects/<slug>/` | Markdown files stay on disk. Git-backed history already works against this layout. No reason to move content into the database. |
| Repository pattern | `SqlProjectRepository` implementing `ProjectRepository` protocol | Already implemented with all five methods. Follows the same protocol-based DI pattern as `WorkflowRepository`. |
| DI mechanism | Flask app attribute via `current_app` | Proven pattern — `current_app.workflow_repository` already ships. Test fixtures stub via `app.project_repository = MagicMock()` as file-history tests demonstrate. |
| Auth context | `g.current_user` from `@require_auth` | Already populated on every authenticated request. Decorator reads JWT claims, loads `User` from DB, sets `g.current_user`. |
| Ownership enforcement | Decorator + query scoping | Decorator for single-resource routes, `list_for_user(user_id)` for listings. Belt-and-suspenders matches Trendfy and Bubls patterns. |
| Migration runner | Standalone Python script with CLI args | `api/scripts/migrate_filesystem_to_git_db.py` already exists and handles both DB rows and git repo initialization. `--owner-email` parameter for user lookup. |
| Frontend | Angular 17 (existing SPA) | Minimal change — add 403 response handling to project service. No new components. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **403 Forbidden for unauthorized access** (not 404) | Small user base where debuggability matters more than information hiding. Frontend can show "access denied" distinctly from "not found." Trendfy uses the same pattern successfully. | Reveals that a project with that slug exists to unauthorized callers. Acceptable risk at current scale — revisit if specview becomes public-facing with competitive sensitivity. |
| **Global slug uniqueness** (defer per-user to Phase 4) | Zero collision probability with one real user. Per-user slugs would require filesystem restructuring to `data/projects/<user_id>/<slug>/`, composite unique constraints, and URL path changes — significant work for a problem that doesn't exist yet. | Two users can never both have a project called `my-api-spec`. This becomes a real issue at Phase 4 onboarding when new users create projects. Flagged as a known debt with a clear trigger for re-scoping. |
| **DB-first dual-write with filesystem rollback** | Clean failure mode — if filesystem creation fails, the DB row is deleted and nothing is created. The alternative (filesystem-first) leaves orphan directories that block retry due to slug uniqueness collision. `SqlProjectRepository.create()` already implements this ordering. | Requires explicit rollback code in the repository. A partial failure between DB commit and filesystem create leaves a brief window where the project "exists" in the DB but has no content directory. This window is milliseconds and self-corrects via rollback. |
| **Migration by email parameter** (not hardcoded user ID) | User IDs are database-assigned integers that can change across DB rebuilds, re-seeding, or environment recreation. Email is a stable human identifier. Costs ten minutes of implementation for significant safety against a class of silent failure. | Requires a valid user record in the `user` table before migration can run. If auth setup (Phase 1) is incomplete, the migration fails with a clear error rather than silently assigning to a wrong or nonexistent user. |
| **Decorator for ownership checks** (not inline per-route) | Eliminates the "forgot a route" failure mode — the most likely security regression. Makes ownership enforcement visible in the route definition (decorator stack) rather than buried in handler bodies. Follows the same pattern as `@require_auth`. Enables structural test enforcement. | Adds one decorator to import and stack. Slightly less flexible than inline checks for routes that need conditional ownership logic — but no such route exists in the current scope (P4: build for the concrete case). |
| **No `project_member` join table** | One user, one role (`owner`), one relationship. A join table for a single case is a speculative abstraction (violates P4). When collaboration becomes a real requirement, adding the table and migrating `project.user_id` into it is a straightforward schema evolution. | Future collaboration features will require a migration on a table with real data. Accepted because the migration is simple (insert one `owner` row per existing project) and the alternative (building unused infrastructure now) contradicts the project's engineering principles. |
| **No admin/superuser bypass** | No admin user exists. No support workflow exists. Direct DB access handles any administrative need at current scale. Building an `is_admin` flag or role check is speculative. | If a support workflow materializes, the ownership decorator needs modification. The decorator's single-responsibility design (check one thing: owner match) makes this extension straightforward — add an early-return for admin users before the ownership comparison. |
| **No feature flag for cutover** | With 1.5 days of effort, one user, and the ability to run the migration before deploying ownership-enforced routes, the deploy-and-verify approach is simpler than flag infrastructure. The rollback path is a single deploy reverting the ownership decorator — routes fall back to filesystem-only behavior. | No instant rollback without deploy. Acceptable because the migration is idempotent (can re-run), the rollback deploy is one commit revert, and the blast radius is one user. |

## Data Flow

### Project Listing

Request arrives at `GET /api/projects`. The `@require_auth` decorator validates the JWT and populates `g.current_user`. The route calls `repository.list_for_user(g.current_user.id)`, which queries the `project` table filtered by `user_id`. The returned `Project` records carry slugs, which the route uses to read content summaries from the filesystem via `service.py`. The response includes only projects owned by the authenticated user.

### Single-Project Access

Request arrives at `GET /api/projects/<slug>`. The `@require_auth` decorator runs first. The `@require_project_ownership` decorator runs second: it calls `repository.get_by_slug(slug)`, returns 404 if no project exists, then compares `project.user_id` against `g.current_user.id` and returns 403 on mismatch. If both checks pass, the verified project is attached to `g.project` and the route handler reads content from the filesystem via `service.py`. The same flow applies to PUT and DELETE routes.

### Project Creation

Request arrives at `POST /api/projects`. The `@require_auth` decorator runs. The route calls `repository.create(user_id=g.current_user.id, name=..., slug=..., git_repo_path=...)`. Inside the repository, the DB row is inserted first, then the filesystem directory is created. If the filesystem operation fails, the DB row is rolled back. On success, the route delegates to `service.py` to write initial content files (braindump, project.json) into the new directory.

## Structural Safeguards

The existing `test_structural.py` enforces adapter boundaries — feature modules cannot import chain providers directly. This epic extends the structural testing philosophy to ownership enforcement. A new structural assertion verifies that every route function in `modules/data/projects/routes.py` that accepts a project slug parameter is decorated with `@require_project_ownership`. This makes "forgot a route" a test failure, not a security incident.

The test fixture pattern is already proven by file-history tests: `app.project_repository` is stubbed with a `MagicMock` that returns controlled `Project` records. Ownership tests create two mock users and verify that user A's request for user B's project receives 403, while user A's request for their own project receives 200.

## Migration Sequencing

The deployment has a critical ordering constraint. The migration script must complete before ownership-enforced routes begin serving traffic. The sequence:

1. Deploy the codebase including the repository wiring and migration script
2. Run the migration script with `--user-email` pointing to Sam's email
3. Verify the row count matches the filesystem project count
4. Start the application with ownership enforcement active

In the Docker Compose deployment model, this means the migration runs as an entrypoint step before gunicorn starts. The migration is idempotent, so re-running it on subsequent deploys is safe and adds no overhead (it skips existing rows).

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| `g.current_user` returns a stub or None (Phase 1 auth incomplete) | The ownership decorator checks for `g.current_user` being None and returns 401 before attempting the ownership comparison. Integration test verifies a real `User` record is loaded. **Important:** `SKIP_AUTH=1` sets `g.current_user = None`, so tests for the ownership decorator must NOT use `SKIP_AUTH` — they must provide a real or mocked `g.current_user`. |
| Migration runs after route enforcement, locking Sam out | Migration is an entrypoint step that runs before the app serves traffic. Post-run verification fails the deploy if row count mismatches filesystem count. |
| A route skips the ownership decorator | Structural test asserts every slug-accepting route in `projects/routes.py` is decorated. New routes without the decorator fail CI. |
| Dual-write partial failure leaves orphaned state | DB-first ordering with explicit rollback. Test cases cover both failure modes (DB fails, filesystem fails) and verify no state leaks. |
| File-history routes silently skip ownership checks | `_resolve_project()` only does a slug lookup — it does NOT perform ownership checks. The `@require_project_ownership` decorator must be explicitly added to all three file-history routes (`history`, `diff`, `revert`) plus `repair` and `coherence`. Repository wiring alone is insufficient. |

## Related Documents

- [Analysis](./analysis.md) — Problems and evidence driving this design
- [Epic](./epic.md) — Scope, tasks, success criteria, and exclusions
- [Timeline](./timeline.md) — Execution sequencing and delivery tracking
- [Implementation Guide](./implementation-guide.md) — Step-by-step build instructions with file paths and test commands