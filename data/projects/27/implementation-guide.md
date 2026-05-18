# Implementation Guide: SaaS Phase 2a — Project Isolation & Multi-Tenancy

## Overview
This epic wires together existing architectural seams — the `Project` SQLModel with `user_id`, the `ProjectRepository` protocol, `SqlProjectRepository`, `@require_auth`, and the `current_app` DI pattern — so that every project route enforces per-user ownership. Tasks sequence linearly at first: Task 1 (repository wiring) unblocks Tasks 2 and 3 in parallel (route-layer ownership and migration script), Task 4 (tests) follows once all production code is in place, and Task 5 (frontend 403 handling) runs in parallel with Task 4. The end state is that `GET /api/projects` returns only owned projects, single-resource routes return 403 for non-owners, new projects dual-write to DB and filesystem, and all 41 existing projects are backfilled to Sam's user record.

## Shared Pre-flight
- Verify Phase 1 auth is fully wired: confirm `g.current_user.id` returns a real integer user ID (not a stub or None) on an authenticated request
- Confirm the `project` table exists in the SQLite database with a `user_id` foreign key referencing the `user` table via the `0001_initial_schema.py` migration
- Confirm `SqlProjectRepository` in `modules/data/projects/repository.py` implements all five `ProjectRepository` protocol methods: `create()`, `get_by_slug()`, `list_for_user()`, `touch()`, `delete()`
- Confirm `current_app.workflow_repository` is wired in `create_app.py` as the reference pattern for DI
- Confirm `_resolve_project()` in file-history routes uses `current_app.project_repository` with a `getattr` fallback
- Run the existing 146-test suite and verify all tests pass as the baseline: `pytest`
- Confirm Sam's user record exists in the `user` table with a known email address
- Verify the `data/projects/` directory contains the 41 filesystem project directories

---

## Task 1: SQL ProjectRepository Implementation  [Effort: 0.3 days]

### What
Wire the existing `SqlProjectRepository` into the Flask application context so that all routes can access it via `current_app.project_repository`. This is the foundational wiring step — every subsequent task depends on the repository being available at runtime. The class and its five protocol methods already exist; only the app-level binding is missing.

### Files
- **Modify**: `create_app.py` — add `app.project_repository = SqlProjectRepository(...)` following the same pattern used for `app.workflow_repository`
- **Modify**: `modules/data/projects/repository.py` — verify the constructor signature matches what `create_app.py` will pass (session factory or engine reference); adjust if the DI wiring needs a database session parameter

### Steps
1. Open `create_app.py` and locate where `app.workflow_repository` is assigned to the Flask app object — this is the pattern to replicate.
2. Import `SqlProjectRepository` from `modules/data/projects/repository.py` at the top of `create_app.py`.
3. Add a line assigning `app.project_repository` to a new `SqlProjectRepository` instance, passing the same session or engine dependency that `workflow_repository` receives.
4. Verify that `SqlProjectRepository.__init__` accepts the parameters being passed from `create_app.py`; if the constructor expects a `git_store` or session factory, ensure the same object used elsewhere is passed here.
5. Confirm that the file-history routes' `_resolve_project()` function, which already references `current_app.project_repository` via a `getattr` fallback, will now resolve to the real repository instance instead of returning None.

### Verify
- Start the Flask app and confirm it boots without import or instantiation errors
- Set a breakpoint or add a temporary log in `_resolve_project()` and hit a file-history endpoint to confirm `current_app.project_repository` returns the `SqlProjectRepository` instance
- Run `pytest` and confirm the 146-test baseline still passes
- Confirm `current_app.project_repository.get_by_slug("any-slug")` returns None (not an error) when called with a slug that has no DB row yet

---

## Task 2: Ownership-Checking Route Layer  [Effort: 0.4 days]

### What
Add a `@require_project_ownership` decorator and apply it to every project route that accepts a slug parameter, so that non-owners receive 403. Convert the project listing route to use `repository.list_for_user()` instead of the filesystem scan, and convert project creation to use the repository's dual-write `create()` method. This is the core security enforcement task.

### Files
- **Create**: `modules/data/projects/ownership.py` — the `@require_project_ownership` decorator that loads the project by slug, checks `project.user_id == g.current_user.id`, returns 403 on mismatch, and sets `g.project` on success
- **Modify**: `modules/data/projects/routes.py` — import and apply `@require_project_ownership` after `@require_auth` on all slug-accepting routes (GET, PUT, DELETE single project, POST repair, POST coherence, GET file history, GET file diff, POST file revert); refactor the listing route to call `repository.list_for_user(g.current_user.id)`; refactor the create route to call `repository.create(user_id=g.current_user.id, ...)`
- **Modify**: `openapi.yaml` — add 403 response definitions to all project routes that accept a slug parameter

### Steps
1. Create `modules/data/projects/ownership.py` with a `require_project_ownership` decorator function. The decorator should extract the slug parameter from the route kwargs, call `current_app.project_repository.get_by_slug(slug)`, return a 404 JSON response if no project is found, compare `project.user_id` against `g.current_user.id`, return a 403 JSON response with an "access denied" message on mismatch, and attach the verified project to `g.project` before calling the wrapped function.
2. Add a guard at the top of the decorator that checks whether `g.current_user` is None and returns 401 if so — this protects against the case where `SKIP_AUTH=1` is set in development.
3. Open `modules/data/projects/routes.py` and import `require_project_ownership` from the new ownership module.
4. Stack `@require_project_ownership` immediately after `@require_auth` on every route that accepts a slug or project ID parameter: the single-project GET, PUT, and DELETE handlers, the `repair` POST handler, the `coherence` POST handler, and all three file-history route handlers (history, diff, revert).
5. Refactor each decorated route handler to use `g.project` instead of calling the service to look up the project — the decorator has already verified existence and ownership.
6. Refactor the project listing route (`GET /api/projects`) to call `current_app.project_repository.list_for_user(g.current_user.id)` instead of scanning the filesystem, then pass the returned project slugs to `service.py` for content retrieval.
7. Refactor the project creation route (`POST /api/projects`) to call `current_app.project_repository.create(user_id=g.current_user.id, name=..., slug=..., git_repo_path=...)` for the dual-write, then delegate to `service.py` for writing initial content files (braindump, project.json) into the newly created directory.
8. Update `openapi.yaml` to add 403 response schemas to every project route that now returns 403 on ownership mismatch.

### Verify
- Start the app, authenticate as a user, and confirm `GET /api/projects` returns only projects with matching `user_id` in the database (will return empty until migration runs)
- Manually insert a test project row with a different `user_id` and confirm `GET /api/projects/<slug>` returns 403
- Confirm `POST /api/projects` creates both a DB row with the correct `user_id` and a filesystem directory
- Run `pytest` and confirm no regressions in the 146-test baseline

---

## Task 3: Filesystem-to-DB Migration Script  [Effort: 0.3 days]

### What
Build (or extend) an idempotent migration script that backfills `project` table rows for all 41 existing filesystem projects, assigning ownership to a user looked up by email. This must run before ownership-enforced routes go live, or Sam gets locked out of every project.

### Files
- **Modify**: `api/scripts/migrate_filesystem_to_git_db.py` — extend the existing script to accept a `--owner-email` CLI argument, look up the corresponding user record, iterate over all `data/projects/<slug>/` directories, read each `project.json` for metadata, insert a `Project` row with the user's ID if one does not already exist for that slug, and print a post-run verification comparing DB row count to filesystem directory count

### Steps
1. Open `api/scripts/migrate_filesystem_to_git_db.py` and review its current functionality — it already handles DB row creation and git repo initialization for filesystem projects.
2. Add a `--owner-email` CLI argument using argparse (or extend the existing argument parser) that accepts the email address of the user who should own all migrated projects.
3. At script startup, query the `user` table for a record matching the provided email. If no user is found, print a clear error message and exit with a non-zero code — do not silently assign to a nonexistent user.
4. Iterate over every subdirectory in `data/projects/`. For each directory, read `project.json` to extract the project name and slug.
5. Before inserting, query the `project` table for an existing row with the same slug. If a row exists, skip it and log that it was skipped — this is the idempotency guarantee.
6. For each new project, insert a `Project` row with the slug, name, and the looked-up user's ID.
7. After processing all directories, count the total rows in the `project` table and the total directories in `data/projects/`. Print both counts. If they do not match, print a warning indicating partial failure and exit with a non-zero code.
8. Ensure the script can be invoked standalone via `python -m api.scripts.migrate_filesystem_to_git_db --owner-email sam@example.com` (adjust the module path to match the project's actual invocation pattern).

### Verify
- Run the script with `--owner-email` set to Sam's email and confirm it creates 41 rows in the `project` table
- Run the script a second time and confirm it skips all 41 projects (idempotency) and exits cleanly
- Query the `project` table and confirm every row has `user_id` matching Sam's user record
- Confirm the post-run verification output shows matching counts (41 DB rows, 41 filesystem directories)

---

## Task 4: Test Coverage for Isolation Logic  [Effort: 0.3 days]

### What
Add pytest cases covering the repository methods, ownership decorator enforcement (403 for wrong user, 404 for missing project), migration idempotency, and dual-write creation. This task validates that the security boundary works correctly and prevents regressions.

### Files
- **Create**: `api/modules/data/projects/tests/test_project_ownership.py` — test cases for the `@require_project_ownership` decorator: 403 when `project.user_id` does not match `g.current_user.id`, 404 when the project slug does not exist, 200 when the owner accesses their own project, and 401 when `g.current_user` is None
- **Modify**: `api/modules/data/projects/tests/test_repository.py` (existing file) — test cases for `SqlProjectRepository` methods: `list_for_user()` returns only projects for the given user ID, `get_by_slug()` returns the correct project, `create()` inserts a DB row and creates a filesystem directory, `create()` rolls back the DB row if filesystem creation fails, and `delete()` removes both the row and the directory
- **Modify**: `api/modules/runtime/chain/tests/test_structural.py` — add a structural assertion that every route function in `modules/data/projects/routes.py` accepting a slug parameter is decorated with `@require_project_ownership`
- **Create**: `api/modules/data/projects/tests/test_migration_idempotency.py` — test that running the migration script twice against a test fixture produces the same row count with no duplicates

### Steps
1. Create `tests/test_project_ownership.py`. Use the existing test fixture pattern where `app.project_repository` is replaced with a `MagicMock`. Create two mock user objects with different IDs. Write a test where user A owns a project and user B requests it — assert 403. Write a test where user A owns a project and user A requests it — assert 200. Write a test where the slug does not exist in the repository — assert 404. Write a test where `g.current_user` is None — assert 401. Do not use `SKIP_AUTH=1` in these tests.
2. Create `tests/test_project_repository.py`. Use a real test database (not mocks) for repository integration tests. Write a test for `list_for_user()` that inserts projects for two different users and asserts only the queried user's projects are returned. Write a test for `create()` that verifies both a DB row and a filesystem directory are created. Write a test for `create()` failure rollback by mocking the filesystem operation to raise an exception and asserting no DB row persists. Write a test for `delete()` that verifies both the row and directory are removed.
3. Open `tests/test_structural.py` and add a test that introspects `modules/data/projects/routes.py`, collects all route functions that accept a slug parameter, and asserts each one has `require_project_ownership` in its decorator chain.
4. Create `tests/test_migration_idempotency.py`. Set up a test fixture with a few filesystem project directories and an empty project table. Run the migration function once and assert the correct row count. Run it again and assert the row count is unchanged and no integrity errors occur.
5. Run the full test suite and confirm all new tests pass alongside the original 146 tests.

### Verify
- Run `pytest api/modules/data/projects/tests/test_project_ownership.py -v` and confirm all four ownership scenarios pass (403, 404, 200, 401)
- Run `pytest api/modules/data/projects/tests/test_repository.py -v` and confirm repository integration tests pass including the rollback scenario
- Run `pytest api/modules/runtime/chain/tests/test_structural.py -v` and confirm the structural assertion for ownership decorator coverage passes
- Run `pytest` to verify the full suite passes with no regressions against the 146-test baseline

---

## Task 5: Frontend 403 Handling  [Effort: 0.2 days]

### What
Update the Angular project service to recognize 403 responses as distinct from 404, so the UI can display an "access denied" message instead of a generic "not found" error. The project list already scopes correctly because `GET /api/projects` returns only owned projects — no frontend filtering is needed.

### Files
- **Modify**: `web-ng/src/app/services/projects.service.ts` — add a 403 case to the HTTP error interceptor or error handling in project API calls, mapping it to a distinct error state or message
- **Modify**: `web-ng/src/app/app.component.ts` — handle the "access denied" error state from the service, displaying an appropriate message to the user instead of the "not found" template
- **Modify**: `web-ng/src/app/app.component.html` — add a conditional template block for the 403/access-denied state with a user-friendly message

### Steps
1. Open `web-ng/src/app/services/projects.service.ts` and locate the error handling logic for project API calls (likely in an RxJS `catchError` or HTTP interceptor).
2. Add a branch that checks for HTTP status 403 and maps it to a distinct error type or state (such as an `AccessDenied` enum value or a specific error message string) that is distinguishable from the existing 404 handling.
3. Open `web-ng/src/app/app.component.ts` and add a component state for "access denied" alongside the existing "not found" state, populated when the service returns the 403-specific error.
4. Open the corresponding template file `project-detail.component.html` and add a conditional block that renders an "access denied" message when the component is in the access-denied state — something like "You don't have access to this project" with a link back to the project list.
5. Verify that the project list page requires no changes — it naturally shows only owned projects because the API already filters by user.

### Verify
- Run `ng build --configuration production` from the `web-ng/` directory and confirm the build succeeds with no errors
- Start the dev server and navigate to a project the authenticated user owns — confirm it loads normally
- Manually change the URL to a slug belonging to another user (or a slug that triggers a 403 from the API) and confirm the "access denied" message appears instead of "not found"
- Confirm the project list page shows only the authenticated user's projects with no UI regressions