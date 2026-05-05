# Braindump: Audit Issues (2026-04-28)

Found during the full codebase audit. Deployment issues excluded — those are in `braindump-deployment-config-fragmentation.md`.

---

## 1. Runtime wiring bugs (will 500 in production)

### `app.user_repository` not attached in `create_app.py`

`@require_auth` calls `current_app.user_repository.get_by_auth_user_id(...)` on every authenticated request. `create_app.py` sets `app.workflow_repository` but never sets `app.user_repository`. Every `@require_auth`-guarded route outside of `SKIP_AUTH=1` raises `AttributeError` at runtime.

Fix: implement `SqlUserRepository` (mirrors `SqlProjectRepository` shape, keyed on `User`) and add `app.user_repository = SqlUserRepository()` in `create_app.py`.

### `app.project_repository` not attached in `create_app.py`

File history/diff/revert routes call `current_app.project_repository.get_by_slug()` and `.touch()`. Not attached. History + diff routes silently return 404; revert route raises `AttributeError` after the git operation succeeds.

Fix: add `app.project_repository = SqlProjectRepository()` in `create_app.py`.

### DB schema never created at startup

`create_app.py` does not call `alembic upgrade head` or `SQLModel.metadata.create_all()`. On a fresh deploy the four tables (`user`, `project`, `subscription`, `usage_counter`) don't exist and every DB-touching route fails.

Fix: add `SQLModel.metadata.create_all(get_engine())` in `create_app.py` (or wire Alembic into the Dockerfile entrypoint).

---

## 2. Auth gaps on routes

Routes that should require auth but don't:

- `GET /api/context/<key>` and `PUT /api/context/<key>` — any unauthenticated caller can read or overwrite the global `builder.md`, `principles.md`, etc.
- `POST /api/ai/text/bootstrap-project/<job_id>/cancel` and `/retry` — any caller who knows a job_id can cancel or retry a bootstrap job
- `POST /api/projects/<project_id>/cancel` and `POST /api/projects/<project_id>/regenerate-task` — same issue for task-gen
- `GET /api/templates/*` and `POST /api/templates/timeline` — low risk (read-only generation) but inconsistent

Fix: add `@require_auth` to all of the above. Context routes need a decision on ownership model first (currently global, not user-scoped).

---

## 3. Frontend: critical pre-launch bugs

### No `<router-outlet>` in `AppComponent`

`AppComponent` template has no `<router-outlet>` and does not import `RouterOutlet`. The three routed pages (`/login`, `/auth/callback`, `/upgrade`) are architecturally complete but permanently unreachable. The router is configured; the outlet is just missing.

Fix: add `<router-outlet>` to `app.component.html`, import `RouterOutlet` in `app.component.ts`.

### No `environment.prod.ts`

`angular.json` has no `fileReplacements` in the production build config. `apiUrl: 'http://localhost:3101'` ships to production unchanged. Every API call in the deployed app hits localhost.

Fix: create `web/src/environments/environment.prod.ts` with production `apiUrl` (relative `/api` once the two-container deploy lands), add `fileReplacements` to `angular.json` production config.

### Auth callback redirects to `/projects` (route doesn't exist)

`AuthCallbackComponent` default redirect target is `/projects`. That route is not defined anywhere in the app. Post-login lands on a blank screen.

Fix: change default redirect to `'/'`.

### Hardcoded default project ID in `AppComponent.ngOnInit`

`AppComponent.ngOnInit` loads project `'architecture-cleanup-1777112358103'` by default. This is a dev artifact — every new user's editor will open pointing at a non-existent project.

Fix: remove the hardcoded ID; default to the first project in the list or an empty state.

### Hardcoded path `/Users/sam/Projects/bubls` in `CodebaseEditorComponent`

`workspacePath` is initialised to `/Users/sam/Projects/bubls`. Ships to production as-is.

Fix: initialise to `''` or derive from a user setting.

---

## 4. Frontend: unmounted/orphaned components

### `UsageMeterPillComponent` not mounted anywhere

The component exists, is tested, and the `SubscriptionService` feeds it correctly — but it is never imported or rendered in any parent component. Users never see their usage quota.

Fix: mount it in the sidebar footer or operation bar.

### `TimelineViewComponent.navigateToTask` output never handled

`TimelineViewComponent` emits a `navigateToTask` `@Output`. `AppComponent` never binds to it. The "View Spec" button on the kanban board is a no-op.

Fix: listen to `(navigateToTask)` in `AppComponent` and scroll/select the relevant spec file.

### `LivePreviewComponent` — orphaned

Not mounted anywhere. Calls `/api/container/*` endpoints that don't exist in the Flask API. Either connect it to a real container API or delete it.

### `TemplatesService` — dead code

Declared, never injected anywhere. `GET /api/templates/spec-index`, `GET /api/templates/readme`, `POST /api/templates/timeline` have zero callers in the Angular app.

Fix: wire it up or delete it.

---

## 5. Backend: dead code

### `modules/billing/decorators.py`

Legacy `@require_auth` stub using `X-User-Id`/`X-User-Email` bypass headers. `billing/routes.py` now imports from `modules.auth.decorators`. This file is dead and should be deleted to avoid confusion.

---

## 6. Backend: minor gaps

### `/api/health/neon` and `/api/health/stripe` are stubs

Both always return `{"status": "skipped"}`. Should perform actual connectivity probes once those dependencies are confirmed live.

### `SqlProjectRepository.delete()` does not clean up the git repo

DB row is deleted; the on-disk git repository under `GIT_REPOS_DIR` is left as an orphan. Source comment: "git_store.delete_repo does not yet exist (Task-2 follow-up)."

Fix: implement `git_store.delete_repo(project_id)` and call it in `SqlProjectRepository.delete()`.

### `GET /api/ai/stats` always returns cost 0.0

`chain_adapter._record_usage()` note says providers do not yet populate `tokens_in`/`tokens_out` on `ChainResult`. The in-process cost accumulator is wired correctly but fed zeros.

Fix: ensure the Anthropic SDK provider reads `response.usage.input_tokens` and `response.usage.output_tokens` and populates `ChainResult` fields before returning.

### Alembic has no downgrade script

`0001_initial_schema.py` is the only revision and has no `downgrade()` implementation. Not a blocker but means rollback requires manual intervention.

---

## Priority order

| # | Issue | Severity |
|---|-------|----------|
| 1 | `app.user_repository` not set | 🔴 Blocker — all auth routes 500 |
| 2 | DB schema not created at startup | 🔴 Blocker — all DB routes fail |
| 3 | `app.project_repository` not set | 🔴 Blocker — history/revert broken |
| 4 | No `<router-outlet>` in AppComponent | 🔴 Blocker — login/upgrade unreachable |
| 5 | No `environment.prod.ts` | 🔴 Blocker — API calls hit localhost in prod |
| 6 | Auth callback redirect to `/projects` | 🟠 High — post-login blank screen |
| 7 | Context routes missing auth | 🟠 High — global context unprotected |
| 8 | Bootstrap/task-gen cancel routes missing auth | 🟠 High |
| 9 | Hardcoded default project ID | 🟠 High — bad first impression |
| 10 | Hardcoded `/Users/sam/Projects/bubls` path | 🟠 High |
| 11 | `UsageMeterPillComponent` not mounted | 🟡 Medium — billing feature invisible |
| 12 | `navigateToTask` output unhandled | 🟡 Medium |
| 13 | `GET /api/ai/stats` always 0.0 | 🟡 Medium — cost visibility broken |
| 14 | `SqlProjectRepository.delete()` orphans git repo | 🟡 Medium |
| 15 | Dead code cleanup (billing/decorators, TemplatesService, LivePreviewComponent) | 🟢 Low |
| 16 | Health probe stubs | 🟢 Low |
| 17 | Alembic no downgrade | 🟢 Low |
