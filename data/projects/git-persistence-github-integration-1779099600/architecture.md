# 🏗️ Solution Architecture: Git Persistence — GitHub Integration

## Architecture Overview

Specview's core durability problem is a mismatch between the value of its output and the fragility of its storage. The AI pipeline spends 1–3 minutes generating each spec document, yet every generated file lives on ephemeral container storage with no off-box backup. The solution is to treat GitHub as a durable mirror: every local file write triggers an asynchronous push to a user-owned GitHub repository, making the user's own GitHub account the authoritative backup. Local storage remains the hot path for reads and writes; GitHub is the persistence layer that survives infrastructure failures.

The design leans heavily on what already exists. The `git_store` service already produces per-project commits with full history. The `Project` model already tracks `latest_commit_sha`. The module isolation test already enforces that no feature code imports pygit2 directly — meaning a new GitHub adapter can slot in behind the existing `git_store` boundary without touching any upstream caller. The new work is a GitHub adapter module, an authentication flow, a background push worker, and sync state columns on the existing database models.

The architecture follows a strict layering: the GitHub API is accessed only through a dedicated adapter (P1), the HTTP layer delegates all logic to services (P2), long-running pushes use the 202 + polling pattern already proven in the spec generation pipeline (P3), and every component is built for the single concrete use case of push-to-GitHub with no speculative abstractions for future providers (P4).

## Design Principles

| Principle | Application in This Epic |
|-----------|--------------------------|
| P1 — Adapter Boundary | All GitHub API calls go through a single `github_adapter` module. No route, service, or worker imports PyGithub, `requests`, or any GitHub client directly. Swapping from GitHub App tokens to OAuth tokens (or a different git host) changes one file. |
| P2 — Thin HTTP Layer | The "Connect GitHub" callback route validates the installation ID, passes it to the auth service, and returns a redirect. The sync status endpoint reads a DB column and returns JSON. Zero business logic in any route handler. |
| P3 — Async 202 + Polling | Push-on-write runs in a daemon background thread. The existing `snapshot(job_id)` pattern extends to sync state: the `sync_status` column on Project is the poll target. No HTTP connection held open during a GitHub push. |
| P4 — No Speculative Abstractions | One adapter for one provider (GitHub). No generic "remote storage" interface. No registry of push targets. If a second provider ever materializes, extract the interface then — not now. |
| P5 — OpenAPI-First | New endpoints (GitHub callback, sync status, disconnect) are defined in `openapi.yaml` first. The route implementations match the contract. |
| P7 — File Size & Structure | The GitHub adapter, the push worker, and the auth service are each separate files under 200 lines. No god module that handles auth + push + repo provisioning in one file. |

## Component Design

### GitHub Authentication Service

**Purpose**: Exchange a GitHub App installation event for a stored credential, and produce short-lived API tokens on demand for any downstream caller.

When a user clicks "Connect GitHub," Specview redirects to the GitHub App installation page. GitHub redirects back with an `installation_id`. The auth service validates this ID, stores it on the User model alongside `github_connected_at`, and returns control to the frontend. For every subsequent API call, the auth service exchanges the stored `installation_id` for a short-lived installation access token (valid ~1 hour) using the GitHub App's private key. This token is never persisted — it is generated on demand and passed to the adapter.

The auth service owns the GitHub App's private key (loaded from environment config, never committed to source). It exposes two operations: `connect(user_id, installation_id)` for the OAuth callback, and `get_token(user_id)` for any module that needs to call GitHub. If the user has no `installation_id`, `get_token` returns `None` and the caller skips the push gracefully.

### GitHub Adapter

**Purpose**: Single boundary for all GitHub REST API calls. The only module that knows GitHub's API shape.

The adapter exposes four operations: `create_repo(token, repo_name)`, `push_file(token, repo, path, content, commit_message, sha)`, `get_file(token, repo, path)`, and `repo_exists(token, repo_name)`. Every operation accepts an already-resolved token — the adapter has no knowledge of how tokens are obtained. Every operation returns a simple result object or raises a typed exception that the caller can handle.

The adapter uses the GitHub Contents API for individual file pushes. This is a deliberate trade-off: the Contents API requires one HTTP call per file (versus the Git Data API which can batch an entire tree into one commit), but it is dramatically simpler to implement, debug, and reason about. A six-file pipeline run produces six sequential API calls, each taking roughly 200–400ms. The total added latency of ~2 seconds is invisible to the user because it runs in a background thread. The Git Data API's batching advantage only matters at scale levels Specview will not hit in its current single-user-at-a-time model — and P4 says we do not build for hypothetical scale.

The adapter also handles GitHub's conflict detection. Every file on GitHub has a blob SHA. To update a file, you must send the current SHA. If the SHA doesn't match (because someone edited the file on GitHub directly), the adapter detects the 409 response, fetches the current SHA, and retries with Specview's version. Specview is the authoritative writer; external edits are overwritten with a logged warning. This is not a merge strategy — it is a deliberate simplification. A merge UI is a different product surface that belongs in a future epic if user demand justifies it.

### Push Worker

**Purpose**: Decouple GitHub push latency from the user-facing write path.

The push worker is a daemon thread (P2 compliance: `daemon=True`, never blocks server shutdown) that processes push requests from an in-process queue. When `git_store.write_file()` completes a local commit, the calling service enqueues a push job containing `user_id`, `project_id`, `filename`, `content`, and `commit_sha`. The worker picks up jobs sequentially, sets `sync_status = 'pushing'` on the Project row, calls the GitHub adapter, and on success updates `remote_push_sha` and `sync_status = 'synced'`. On failure, it retries up to three times with exponential backoff (1s, 4s, 16s), then sets `sync_status = 'failed'` and writes the error to `last_push_error`.

The queue is an in-process `collections.deque` protected by a `threading.Lock`. This is sufficient because Specview runs with `--workers 1` (required for in-process state) and the push volume is low — a heavy user generates maybe 30 files per hour. No Redis, no external queue, no Celery. The deque drains in order, which means files pushed during a pipeline run arrive at GitHub in generation order.

If the user has not connected GitHub (`installation_id` is null), the enqueue call is a no-op. The push path adds zero overhead to disconnected users.

### Repo Provisioning Logic

**Purpose**: Ensure every connected user has exactly one GitHub repository in a known state.

When a user first connects GitHub, the provisioning logic checks whether a repo named `specview-projects` already exists under the user's account. If it exists (perhaps from a previous connection), Specview adopts it — no duplicate repos. If it doesn't exist, Specview creates it as a private repository via the adapter. The repo's full name (e.g., `sambekar/specview-projects`) is stored on the User model as `github_repo_full_name`.

After provisioning, the logic writes a `.specview/config.json` metadata file to the repo root containing the user identifier and connection timestamp. This file serves as a format marker: any future restore logic can verify that a repo is a Specview-managed repo by checking for this file.

Provisioning also triggers an immediate backfill: every existing project for the user is queued for push. This ensures that users who already have projects before connecting GitHub see their entire history appear in the repo within minutes of connecting.

### Sync State Tracking

**Purpose**: Give the frontend a reliable signal for whether each project's GitHub mirror is current.

The `sync_status` column on the Project table is the single source of truth for push state. It moves through four values: `pending` (local commit exists, not yet pushed), `pushing` (worker is actively calling GitHub), `synced` (GitHub has the latest commit), and `failed` (push failed after retries). The state machine is simple and acyclic except for the retry path: `failed` transitions back to `pushing` when the worker retries or the user manually triggers a retry.

The frontend reads `sync_status` from the existing project detail API — no new endpoint needed for the indicator itself. The status bar component gains a small sync badge: green check for `synced`, animated spinner for `pushing`, red warning for `failed` with a clickable retry action. The retry action calls a new `POST /projects/{id}/sync/retry` endpoint that re-enqueues the latest commit for push.

A consistency invariant: `sync_status = 'synced'` if and only if `remote_push_sha == latest_commit_sha`. The push worker enforces this on every successful push. A background sweep (cheap, runs every 60 seconds on the existing worker thread) catches any project where the invariant is violated and re-enqueues it. This prevents the "stuck in pushing" failure mode identified in the epic's success criteria.

### Schema Migration

**Purpose**: Extend the existing Neon Postgres schema to support GitHub connection and sync tracking.

The User table gains three columns: `github_installation_id` (bigint, nullable — null means not connected), `github_repo_full_name` (varchar, nullable), and `github_connected_at` (timestamp, nullable). These are all additive, nullable columns — no existing data is affected, no backfill needed, no downtime.

The Project table gains four columns: `remote_push_sha` (varchar 40, nullable — null means never pushed), `sync_status` (varchar 20, default `'pending'`), `last_push_at` (timestamp, nullable), and `last_push_error` (text, nullable). Again, fully additive. Existing projects will have `sync_status = 'pending'` and `remote_push_sha = null`, which correctly represents "not yet pushed to GitHub."

The migration runs as a single Alembic revision with six `ADD COLUMN` statements. No table rewrites, no index changes, no data migration. The entire migration completes in under one second on the current schema size.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Auth mechanism | GitHub App (not OAuth App) | Fine-grained permissions — Specview requests only `contents:write` and `metadata:read`, not blanket repo access. Installation tokens survive user password changes. Higher rate limits per installation. Can act on behalf of the user to create repos. |
| GitHub API surface | Contents API (not Git Data API) | One call per file is simpler to implement, debug, and retry. The added latency (~200ms per file) is invisible in a background thread. Batching via Git Data API is a premature optimization for current volume (P4). |
| Background execution | `threading.Thread` with `daemon=True` | Already proven in the spec generation pipeline. In-process queue avoids external dependencies (no Redis, no Celery). Single gunicorn worker (`--workers 1`) guarantees queue visibility across all requests. |
| State storage | Existing Neon Postgres (additive columns) | No new database. No new table. Six nullable columns on two existing tables. The sync state query is a single column read on an already-fetched Project row — no joins, no new indexes. |
| HTTP client | `httpx` (already in dependencies) or `requests` | Standard HTTP client for GitHub REST API calls. Wrapped entirely inside the adapter — no other module sees HTTP calls to GitHub. |
| Token signing | PyJWT (for GitHub App JWT generation) | GitHub App authentication requires signing a JWT with the app's private key. PyJWT is a lightweight, well-maintained library. The JWT is generated on demand and never stored. |
| Frontend indicator | Existing `status-bar.component.ts` | No new component. The status bar already shows generation state; sync state is a natural addition. Reads `sync_status` from the project object already returned by the API. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **One repo per user, not one repo per project** | A single `specview-projects` repo keeps provisioning simple (create once, push forever), avoids repo sprawl on the user's GitHub account, and makes the backfill-on-connect operation a single repo target. The repo structure mirrors the local filesystem exactly — one directory per project. | Large repos (100+ projects) may slow GitHub's web UI for browsing. Mitigation: revisit if any user crosses 50 projects. Splitting later is a data migration, not an architecture change. |
| **GitHub App over OAuth App** | Installation tokens are scoped to specific permissions and repos, not the user's entire GitHub identity. They survive password resets and don't expire when users revoke browser sessions. The GitHub App model also allows Specview to request only `contents:write` — users never grant more access than needed. | GitHub App setup requires generating and storing a private key, and the JWT-based token exchange is more complex than a simple OAuth token. But this complexity lives entirely inside the auth service — no other module is affected. |
| **Contents API over Git Data API** | The Contents API is a single PUT per file with built-in conflict detection (SHA-based). It maps 1:1 to the existing `write_file` call pattern. Implementation is roughly 20 lines of adapter logic per operation. | Cannot atomically commit multiple files — a pipeline run that generates 6 files produces 6 separate GitHub commits instead of one. This means the GitHub history is noisier than the local git history. Acceptable because GitHub is a mirror, not the primary interface. If atomic multi-file commits become important, switching to Git Data API is a change in one adapter method. |
| **Async push with in-process queue, not synchronous push** | The user's hot path (viewing and generating specs) must not be affected by GitHub's API latency. A synchronous push would add 200ms–2s per file write to every pipeline step. The background thread makes GitHub latency invisible. | If the server crashes mid-push, queued items are lost. Mitigation: the consistency sweep detects `remote_push_sha != latest_commit_sha` and re-enqueues. Data is never lost — only the push is delayed until the next server start. |
| **Specview-wins conflict resolution, not merge** | Specview is the only writer by design. Users are told to treat the GitHub repo as read-only. Implementing a merge UI for the edge case of direct GitHub edits would triple the scope of this epic for a scenario that should rarely occur. | Users who edit files on GitHub will have their changes silently overwritten. A warning is logged server-side. If this becomes a real user complaint, a merge UI is a self-contained future epic — the adapter already detects conflicts via SHA mismatch. |
| **Push-on-connect backfill as foreground queue drain, not background migration job** | When a user connects GitHub, all existing projects are enqueued for push immediately. The push worker drains them in order. No separate migration job, no separate queue, no separate retry logic. One path for all pushes. | A user with 30 existing projects will see pushes trickling in over ~60 seconds after connecting. The sync indicator shows progress per-project. This is a better UX than a loading spinner that blocks until all projects finish. |
| **No pull-based restore in this epic** | The epic scope explicitly excludes pull recovery. Push-first proves the repo format and directory structure in production. Restore logic depends on the push format being stable — shipping both simultaneously risks building restore for a format that changes. | Users who lose local data before restore ships must manually clone from GitHub. This is acceptable because the persistent volume fix (shipping independently) prevents the most common data loss scenario, and GitHub access provides manual recovery. |

## Integration Points

### Where the push hooks into the existing write path

The `git_store.write_file()` function is the single point where content reaches disk. Today it returns a commit SHA. The integration adds one call after the commit succeeds: the calling service (not `git_store` itself) enqueues a push job with the returned SHA. This keeps `git_store` pure — it remains a local git operations module with no knowledge of GitHub. The enqueue call lives in the service layer (`project_service` or equivalent), which already orchestrates the write-then-update-DB sequence.

This placement means the push trigger is co-located with the DB update that sets `latest_commit_sha`, ensuring both happen in the same logical operation. If the DB update fails, the push is not enqueued — which is correct, because a project whose DB state is inconsistent should not push to GitHub.

### Where auth connects to the existing user model

The User model gains three nullable columns. The `require_auth` decorator already resolves `current_user` on every authenticated request. The GitHub auth service reads `current_user.github_installation_id` to determine whether to generate a token. No changes to the auth middleware — the new columns are read by the GitHub-specific service, not by the auth flow.

### Where sync status connects to the existing frontend

The project detail API already returns the full Project object. Adding `sync_status`, `remote_push_sha`, `last_push_at`, and `last_push_error` to the response requires no new endpoint — just four more fields in the serializer. The Angular `projects.service.ts` already polls for project state during generation; the same polling mechanism picks up sync state changes without any new polling logic.

## Module Layout

The new modules follow the existing directory convention. All GitHub-related logic lives under a new `modules/github/` directory, parallel to `modules/auth/`, `modules/data/`, and `modules/ai/`.

- **`modules/github/adapter.py`** — GitHub REST API wrapper. The only file that imports an HTTP client for GitHub calls. Exposes `create_repo`, `push_file`, `get_file`, `repo_exists`.
- **`modules/github/auth_service.py`** — GitHub App JWT generation, installation token exchange, connect/disconnect logic. Reads the app private key from config.
- **`modules/github/push_worker.py`** — Background daemon thread, in-process deque, retry logic, sync state updates. Exposes `enqueue(user_id, project_id, filename, content, sha)` and `start_worker()`.
- **`modules/github/routes.py`** — Thin HTTP handlers: installation callback, disconnect endpoint, manual retry endpoint. Each handler validates input, calls a service, returns a response.
- **`modules/github/provisioning.py`** — Repo creation/adoption logic, `.specview/config.json` generation, connect-time backfill orchestration.

Each file targets under 200 lines. The adapter handles raw HTTP. The auth service handles credentials. The push worker handles async execution. The routes handle HTTP. The provisioning module handles first-connect setup. No file has two responsibilities.

## Security Considerations

The GitHub App private key is the most sensitive credential in this system. It must be loaded from an environment variable or a mounted secret file — never committed to source, never stored in the database. The key is used only inside `auth_service.py` to sign JWTs, and the resulting installation tokens are short-lived (1 hour) and never persisted.

Installation tokens are scoped to the permissions granted during app installation. Specview requests `contents:write` (to push files) and `metadata:read` (to check repo existence). It does not request `admin`, `workflows`, `actions`, or any other permission. Users can verify this on their GitHub App installation settings page.

The installation callback endpoint must validate that the `installation_id` corresponds to a real GitHub App installation before storing it. A malicious actor sending a fake installation ID would cause all subsequent pushes to fail (token exchange would be rejected by GitHub), but the validation prevents storing garbage data.

User disconnection (`DELETE /github/connection`) removes `github_installation_id` and `github_repo_full_name` from the User row and stops all future pushes. It does not delete the GitHub repo or its contents — the user's data on GitHub is theirs to manage.

## Rate Limits and Capacity

GitHub App installation tokens allow 5,000 API requests per hour per installation. A single pipeline run generates approximately 6 files, consuming 6 API calls for push plus 1 for the initial file SHA fetch per update (the Contents API requires the current blob SHA to update). That is roughly 12 calls per pipeline run in the worst case (all files already exist and need SHA lookups). At 5,000 calls per hour, a single user could run approximately 400 pipeline runs per hour — far beyond any realistic usage pattern.

The consistency sweep adds at most one API call per project per sweep cycle (checking whether the remote SHA matches). With a 60-second sweep interval and typical project counts under 50, this adds fewer than 50 calls per minute — negligible against the 5,000/hour budget.

For multi-tenant growth, each user gets their own GitHub App installation, and each installation has its own 5,000/hour quota. User A's heavy usage does not affect User B's rate limits.

## Failure Modes and Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| GitHub API unreachable (outage, network partition) | Pushes fail, `sync_status` moves to `failed` after 3 retries | Consistency sweep re-enqueues failed projects when GitHub recovers. User sees "sync failed" indicator with manual retry option. |
| Server crash mid-push | In-process queue is lost; some projects may be in `pushing` state | On restart, the consistency sweep detects `pushing` state with stale timestamps (older than 5 minutes) and re-enqueues. No data is lost — local commits are durable on disk. |
| GitHub App token expired mid-push | Single push call returns 401 | The adapter detects 401, requests a fresh token from the auth service, and retries the call once before counting it as a failure. |
| User revokes GitHub App installation | All pushes fail with 403 | The auth service detects the revocation on the next token exchange attempt, clears `github_installation_id` from the User model, and the frontend shows "GitHub disconnected." |
| Neon DB unavailable | Cannot update `sync_status` after successful push | The push succeeded on GitHub but the local DB is stale. On DB recovery, the consistency sweep reconciles by comparing `remote_push_sha` against `latest_commit_sha`. |

## Related Documents

- [Analysis](./analysis.md) — Data-loss scenarios and infrastructure gaps driving this design
- [Epic](./epic.md) — Scope boundaries, task breakdown, and success criteria
- [Timeline](./timeline.md) — Phase delivery tracking and dependency sequencing