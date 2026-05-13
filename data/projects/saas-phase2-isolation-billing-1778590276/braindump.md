# SaaS Phase 2a: Project Isolation & Multi-Tenancy

> **Priority**: P1 — the multi-tenancy security gate. Without this, User A sees User B's projects.
> **Effort**: ~1.5 days.
> **Blocks**: Phase 2b (billing UI assumes per-user state), Phase 4 (onboarding needs per-user project creation).
> **Depends on**: Phase 1 (auth — `@require_auth` + `g.current_user` must be wired).

## The problem

Every authenticated user sees all 41 projects. The `Project` model has a `user_id` FK and a `ProjectRepository` protocol with `list_for_user()`, `get_by_slug()`, etc. — but the actual routes bypass all of it. They call a filesystem-only `service.py` that reads `project.json` files from disk with zero user filtering. The `g.current_user` is set on every request by `@require_auth` but never consulted for project access.

This is the single biggest blocker for multi-user specview. Ship this before anything else.

---

## Current state (fact-checked 2026-05-12)

**What exists:**
- `api/modules/data/projects/models.py` — `Project` SQLModel with `user_id` FK, `slug` (unique), `name`, `git_repo_path`, `file_count`, timestamps.
- `ProjectRepository` protocol defined with methods: `create()`, `get_by_slug()`, `list_for_user()`, `touch()`, `delete()`. This is the intended interface — no SQL implementation wired yet.
- `api/modules/data/projects/routes.py` — all routes use `@require_auth` (so `g.current_user` is populated) but every route delegates to `service.py` functions that ignore the user entirely.
- `api/modules/data/projects/service.py` — pure filesystem: `list_projects(projects_dir)` iterates `data/projects/*/project.json`. No user_id parameter, no ownership check, no DB queries.
- Database: `project` table exists in migration `0001_initial_schema.py` with `user_id` FK to `user` table. Table is empty — no rows for the 41 filesystem projects.
- File history routes (Pers-T4) already reference `current_app.project_repository` — they're designed for the repository seam but it's not connected.

**What's broken:**
- `GET /api/projects` returns all 41 projects regardless of who's logged in.
- `GET /api/projects/<id>`, `PUT`, `DELETE` — no ownership verification. Any authenticated user can read/modify/delete any project.
- `POST /api/projects` creates on filesystem but doesn't write a `Project` row to DB with `user_id`.
- The 41 existing filesystem projects have no corresponding rows in the `project` table.

---

## Learnings from other projects

**Trendfy (Flask + Angular, closest stack):**
Trendfy uses an explicit `_check_ownership(record)` helper in routes that returns 403 if `record.user_id != g.user_id`. This is better than only filtering at query level — it gives a clear 403 "Forbidden" instead of a silent 404 or empty result, which is important for debugging and for the frontend to show the right error. Every route that touches an order calls this check after loading the record.

Database queries also filter by user_id: `SELECT * FROM orders WHERE user_id = %s`. Belt and suspenders — filter at query time AND verify ownership after load.

**Springular (Spring Boot SaaS template):**
Uses `AuthenticatedUserProvider.getAuthenticatedUser()` (equivalent to our `g.current_user`) to scope every query. Every controller that touches user-scoped data calls this. The provider is injected as a dependency — clean pattern, easy to test. User lookup supports multiple keys: `findByEmail`, `findByStripeCustomerId`, `findByEmailAndProvider` — useful when webhooks need to find users by different identifiers.

**Bubls (Flask, similar middleware):**
Repository functions take `user_id` as an explicit parameter: `find_active_lora_for_user(db, user_id)`, `list_generations_for_user(db, user_id)`. Routes extract `g.user.id` and pass it down. No implicit filtering — the user scoping is visible in every call signature.

---

## Architecture direction

**DB as ownership source of truth, filesystem for content.** The `ProjectRepository` protocol already defines the right interface. Wire a SQL implementation that stores project metadata + `user_id` in the `project` table. The filesystem (`data/projects/<slug>/`) stays as the content store for markdown files. Routes go through the repository for listing/ownership, then read files from the filesystem path.

**Ownership check on every route.** Not just filtering — explicit 403 when a user tries to access a project they don't own. Following trendfy's pattern: load record, check `record.user_id == g.current_user.id`, return 403 if not.

**Migration script for existing projects.** One-shot idempotent script that reads each `data/projects/<slug>/project.json`, creates a `Project` row in the DB with `user_id=1` (Sam). Skip if slug already exists. Run once after deploy.

**Project creation writes to both.** `POST /api/projects` creates the filesystem directory AND inserts a `Project` row with the authenticated user's ID.

---

## Testing baseline to maintain

Phase 3 established 146 tests across 9 spec files (39% statement coverage, 21% branch coverage). Any new code in this project must maintain or improve that baseline:

- **Backend:** New repository implementation needs pytest coverage. Ownership check logic (403 on wrong user, 404 on missing project) needs test cases. The migration script needs a test verifying idempotency.
- **Frontend:** If any Angular service changes are needed (e.g. handling 403 responses), add cases to the relevant `.spec.ts` file following the co-located mock convention.
- **Structural:** `test_structural.py` enforces adapter boundaries — make sure repository imports don't leak into route handlers in a way that violates conventions.
- **E2E:** `e2e/features/` has 5 feature files covering core flows. Project isolation should not break any existing scenarios. Consider adding a scenario to `billing-gate.feature` or a new feature file verifying that user A cannot see user B's projects.

---

## Files involved

- `api/modules/data/projects/routes.py` — wire repository, add ownership checks
- `api/modules/data/projects/repository.py` — SQL implementation of ProjectRepository protocol
- `api/modules/data/projects/service.py` — filesystem functions stay for file content reads
- `scripts/migrate_filesystem_to_db.py` — one-shot migration of 41 projects to DB

## Success criteria

- User A cannot see User B's projects via any route
- User A gets 403 trying to access User B's project by ID
- All 41 existing projects have rows in `project` table assigned to Sam
- `POST /api/projects` creates both filesystem dir and DB row with user_id
- `DELETE /api/projects/<id>` verifies ownership before deleting
- Existing E2E test suite passes without regression
- New repository logic has pytest coverage
