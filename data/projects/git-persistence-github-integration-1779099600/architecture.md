# 🏗️ Solution Architecture: Git Persistence — GitHub Integration

## Architecture Overview

This architecture introduces a three-layer storage model that transforms Specview containers from stateful to fully stateless. GitHub becomes the permanent durable store for all spec content — not a backup destination, but the source of truth. Neon Postgres serves as the coordination layer: it tracks users, projects, metadata, and hosts a `pending_writes` table that acts as a write-ahead log guaranteeing no content is lost between the moment of creation and the moment GitHub confirms receipt. The local filesystem demotes to an ephemeral read/write cache — useful for speed during a session, disposable on restart.

The key architectural insight is that this entire integration hides behind the existing `git_store` module boundary at `api/modules/data/git_store/`. Feature code continues to call `git_store.write_file()` and `git_store.read_file()` with zero knowledge of GitHub, Neon WAL entries, or sync state machines. The `test_pygit2_isolation.py` test that enforces this boundary continues to pass unchanged. This means every task in the epic can be built incrementally — write path, read path, auth flow, backfill — without modifying a single line of feature code. The integration is invisible to everything above the data layer.

The sync engine is deliberately unsophisticated. A single daemon thread processes the `pending_writes` table, pushing files to GitHub one at a time and advancing a four-state machine per project. On container boot, the worker picks up any rows that were pending when the previous container died, ensuring crash recovery is automatic and requires no operator intervention. Complexity is deferred until usage patterns demand it: per-file pushes instead of batched trees, overwrite-on-conflict instead of merge UI, one repo per user instead of configurable topology. Every simplification has a clear revisit trigger documented in the design decisions.

## Design Principles

| Principle | Application in This Feature |
|---|---|
| **P1 — Adapter Boundary** | A new `github_client` adapter at `api/modules/data/github_client/` is the sole module that imports any GitHub library. Neither `git_store`, the sync worker, nor any feature module references GitHub internals directly. Token exchange, API calls, and error mapping are fully encapsulated. |
| **P2 — Thin HTTP Layer** | The GitHub App callback route validates the installation ID from the redirect, calls a service function that stores credentials and provisions the repo, and returns a redirect. No business logic in the handler. |
| **P3 — Async 202 + Polling** | File writes return immediately after the local commit and Neon WAL insert (~5ms added latency). The GitHub push happens asynchronously via background worker. The existing `sync_status` field on Project serves as the poll target for the frontend when status bar UI is added later. |
| **P4 — No Speculative Abstractions** | Per-file push via Contents API — not batched tree commits. One repo per user — not configurable repo topology. Overwrite on conflict — not merge UI. Each simplification has a stated revisit threshold. |
| **P5 — OpenAPI-First** | New endpoints (GitHub callback, sync status, manual retry) are defined in `openapi.yaml` before implementation. The sync status response shape is the contract the future status bar UI will consume. |
| **P7 — File Size & Structure** | The GitHub integration splits across four focused modules: `github_client/adapter.py` (API boundary), `github_client/token_manager.py` (credential lifecycle), `sync/worker.py` (background push loop), and `sync/service.py` (state transitions and WAL operations). Each stays under 200 lines. |

## Storage Model

The three layers serve distinct roles and carry different durability guarantees.

| Layer | Module Location | Role | Durability | Failure Mode |
|---|---|---|---|---|
| **GitHub** | `github_client/adapter.py` | Permanent content store — source of truth for all markdown files | Permanent (GitHub SLA) | API outage delays sync; data safe in Neon WAL |
| **Neon Postgres** | Existing DB via SQLAlchemy | Structured metadata, user/project records, write-ahead log for pending pushes | Permanent (managed Postgres) | Connection failure blocks new WAL inserts; local write still succeeds |
| **Local filesystem** | `git_store/service.py` (existing) | Ephemeral read/write cache with full local git history via pygit2 | None — container-scoped | Container restart means cold cache; lazy-fetch from GitHub restores on demand |

A write is durable the instant it lands in the Neon `pending_writes` table. It is complete when GitHub confirms receipt and the pending row is deleted. The local filesystem accelerates reads but is never required for recovery.

## Component Design

### GitHub Client Adapter

**Purpose**: Single boundary for all GitHub API interaction, enforcing P1.

**Location**: `api/modules/data/github_client/adapter.py` and `api/modules/data/github_client/token_manager.py`

This adapter is the only module in the codebase that knows how to authenticate with GitHub, push content, fetch files, or create repositories. It exposes four operations: provision a repository for a user, push a single file to a path within the repo, fetch a file's content by path, and retrieve the current SHA of a file (needed for update operations via the Contents API). The token manager handles the two-step authentication flow unique to GitHub Apps: it signs a JWT with the App's private key, exchanges it for a short-lived installation token scoped to the user's installation, and caches that token with a TTL just under the one-hour expiry. Every call through the adapter checks token freshness before making the request.

The adapter translates GitHub-specific errors into domain errors that the sync worker understands: rate-limited, unauthorized, not-found, conflict (SHA mismatch), and transient failure. This mapping means the sync worker's retry logic is decoupled from GitHub's error format — if the backing store changed, only the adapter would change.

### Enhanced Write Path in git_store

**Purpose**: Make every file write durable without changing the interface that feature code depends on.

**Location**: `api/modules/data/git_store/service.py` (enhanced), `api/modules/data/sync/service.py` (new)

The existing `write_file(project_id, filename, content, message)` function currently writes to the local filesystem, stages, commits via pygit2, and returns a commit SHA. The enhancement adds one step after the local commit: if the project's owner has a GitHub connection, the sync service inserts a row into the `pending_writes` table containing the project ID, filename, full content, and the local commit SHA. This Neon INSERT adds approximately 5ms of latency — imperceptible to the user, but it means the content now survives container death.

The separation matters: `git_store` calls into `sync/service.py` for the WAL insert, not into `github_client` directly. The sync service owns the `pending_writes` table and the Project sync state fields. This keeps `git_store` focused on local git operations and prevents the GitHub concern from bleeding into the commit logic.

For users without a GitHub connection, the write path is identical to today. The sync service check is a single conditional on the user's `github_installation_id` — null means skip, non-null means insert into WAL. Zero regressions for unconnected users.

### Cache-Through Read Path

**Purpose**: Make container restarts invisible by lazily hydrating files from GitHub on cache miss.

**Location**: `api/modules/data/git_store/service.py` (enhanced)

The existing `read_file(project_id, filename)` reads from the local pygit2 repository. The enhancement adds a fallback: when the local read fails (file not found, which happens after every container restart since the filesystem is empty), and the project's owner has a GitHub connection, the function fetches the file from GitHub via the `github_client` adapter, writes it to the local filesystem and git repo (re-establishing the cache), and returns the content. Subsequent reads for the same file hit the local cache with no network cost.

This lazy-load design means container boot requires zero pre-population. The project list comes from Neon (already the case), and file content arrives on demand. The first read of any file after a restart pays approximately 200–300ms for the GitHub round-trip; every read after that is local. There is no bulk restore step, no boot-time sync job, and no ordering dependency on which projects get loaded first.

The `list_files` operation follows the same pattern. If the local repo is empty or missing, it falls back to querying the Neon project metadata (which tracks filenames via existing columns) or, as a last resort, listing the GitHub directory contents. This ensures the sidebar file navigator works immediately after a restart even before any individual file has been fetched.

### Sync Worker

**Purpose**: Background delivery of pending writes to GitHub with retry and state management.

**Location**: `api/modules/data/sync/worker.py`

The sync worker is a single daemon thread (`daemon=True`, per code rules) that starts when the Flask app boots. It follows the existing background job pattern already used for AI generation — `threading.Thread` with module-level state, no external queue, no Redis. The worker polls the `pending_writes` table on a short interval. For each row, it acquires an installation token via the `github_client` adapter, pushes the file to the appropriate path in the user's repo, and on success deletes the pending row and updates the project's `sync_status` to `synced` and `remote_push_sha` to the GitHub commit SHA.

On failure, the worker applies exponential backoff starting at 5 seconds, doubling up to a cap of 5 minutes. After three consecutive failures for the same row, it marks the project's `sync_status` as `failed` and writes the error details to `last_push_error`. The row stays in `pending_writes` — it is never deleted on failure. A manual retry (future endpoint) or the next successful write to the same project clears the failed state.

On container boot, the worker's first action is to scan `pending_writes` for any rows left over from the previous container's lifetime. These represent writes that were durable in Neon but never confirmed by GitHub — the exact crash-recovery scenario this architecture is built for. The worker processes them in creation order, oldest first, ensuring that if multiple versions of the same file are pending, the final state on GitHub matches the latest write.

The worker handles one file at a time, sequentially. This is intentional: it avoids concurrent GitHub API calls that could cause SHA conflicts on the same file, and it keeps the implementation simple enough for a solo developer to debug. At current scale (single-digit concurrent users, 5–6 files per pipeline run), sequential processing clears the pending queue well within the 60-second success criterion. The revisit trigger for parallelism is 50+ concurrent users, as stated in the epic scope.

### GitHub App Auth Flow

**Purpose**: Connect a user's GitHub account and provision their spec repository.

**Location**: `api/modules/auth/github_routes.py` (new route file), `api/modules/data/github_client/adapter.py` (repo provisioning)

The flow begins when a user clicks "Connect GitHub" in the Specview settings. The frontend redirects to the GitHub App installation URL (a static URL specific to the registered Specview App). The user installs the App on their personal account, granting `contents: write` permission on a single repository. GitHub redirects back to a callback URL on the Specview API with an `installation_id` parameter.

The callback route follows P2 strictly: it validates the installation_id, calls a service function that stores `github_installation_id` and `github_connected_at` on the User model, provisions the repository (see below), and redirects the user back to the Specview UI. No business logic in the handler.

A GitHub App is chosen over a standard OAuth App for three reasons. First, installation-level tokens are scoped to the specific repos the user granted access to, not to the user's entire GitHub account — this is the minimum-privilege principle. Second, installation tokens survive password changes and personal access token rotations, since they are tied to the App installation, not to user credentials. Third, GitHub Apps receive higher API rate limits (5,000 requests per hour per installation versus 5,000 per user across all OAuth apps), which provides headroom as usage grows.

### Repo Provisioning

**Purpose**: Create and initialize the user's spec repository on GitHub.

The provisioning step runs once, immediately after the GitHub App callback stores the installation ID. The service checks whether a repository named `specview-projects` already exists under the user's account. If it does not, the `github_client` adapter creates a private repository with that name. The adapter then pushes an initial commit containing a `.specview/config.json` file at the repo root with minimal metadata: the user identifier and the provisioning timestamp.

The repository name is fixed — `specview-projects` — not user-configurable. This eliminates a configuration surface, simplifies the read path (the adapter always knows where to look), and avoids edge cases around repo renaming or deletion. The `github_repo_full_name` stored on the User model (for example, `bytesbysamu/specview-projects`) is the canonical reference used by the adapter for all subsequent operations.

The repo structure mirrors the existing local filesystem layout exactly. Each project is a directory named by its slug, containing the same markdown files that exist locally: `project.json`, `braindump.md`, `analysis.md`, `epic.md`, `architecture.md`, `timeline.md`, and `implementation-guide.md`. No transformation, no renaming, no restructuring. A user who clones their repo sees the exact same file tree that Specview's data directory contains.

### Backfill Service

**Purpose**: One-time migration of existing projects to GitHub after a user connects their account.

**Location**: `api/modules/data/sync/backfill.py`

After repo provisioning, any projects that existed before the GitHub connection need to be pushed. The backfill service queries all projects belonging to the user, reads each project's files from the local cache (or from the existing filesystem if the container hasn't restarted since those files were generated), and inserts each file as a row in `pending_writes`. The sync worker handles the actual push — the backfill service does not call GitHub directly.

This design reuses the existing write path entirely. The backfill is just a batch insert into the WAL table, and the sync worker's normal processing loop delivers the files to GitHub. This means backfill gets retry logic, error handling, and state tracking for free. It also means backfill is idempotent: running it twice inserts duplicate pending rows, but the sync worker's push-and-delete cycle handles duplicates gracefully since pushing the same content to GitHub with the correct SHA is a no-op.

The backfill runs asynchronously. For a user with 10 projects averaging 6 files each, the backfill inserts 60 rows into `pending_writes`. The sync worker processes these sequentially, taking roughly 60–90 seconds to push all files (each GitHub API call takes about 1–1.5 seconds). The user can continue using Specview normally during this process — new writes from the pipeline flow through the same pending queue and are processed in order.

## Sync State Machine

Each project carries a `sync_status` field that tracks its relationship to GitHub. The machine has four states with well-defined transitions.

| State | Meaning | Transition Trigger | Next State |
|---|---|---|---|
| **pending** | Content written to Neon WAL, not yet attempted on GitHub | Sync worker picks up the row and begins push | pushing |
| **pushing** | GitHub API call is in flight | Push succeeds with confirmed SHA | synced |
| **pushing** | GitHub API call is in flight | Push fails (network, auth, rate limit) | failed (after 3 retries) |
| **synced** | `remote_push_sha` matches latest content; WAL row deleted | New file write creates a new pending_writes row | pending |
| **failed** | Push exhausted retries; `last_push_error` contains details | Manual retry or next successful write to the project | pushing |

The state is per-project, not per-file. When any file in a project has a pending write, the project is `pending`. When the sync worker is actively pushing any file for that project, it is `pushing`. A project only reaches `synced` when its `pending_writes` row count is zero. This simplification keeps the state query trivial (one column on Project, no joins) and matches the granularity that a future status bar UI would display.

The `failed` state is sticky — it does not auto-clear. The `last_push_error` field contains the error message from the final retry attempt. This surfaces actionable diagnostics: expired installation (user needs to re-authorize), repository deleted (user needs to reinstall), rate limited (transient, will resolve). A future retry endpoint allows the user to manually trigger a re-push, which transitions the project back to `pushing`.

## Schema Design

Three schema changes support the integration. All are additive — no existing columns are modified or removed, ensuring backward compatibility.

**User table additions**: Three new columns. `github_installation_id` (nullable bigint) stores the GitHub App installation identifier returned by the callback. `github_repo_full_name` (nullable string, max 255 characters) stores the owner/repo-name pair used by the adapter for all API calls. `github_connected_at` (nullable timestamp) records when the connection was established. All three are null for users who have not connected GitHub, and the null check on `github_installation_id` is the gate that determines whether sync behavior activates for a given user.

**Project table additions**: Four new columns. `remote_push_sha` (nullable string, 40 characters) stores the SHA of the last commit confirmed by GitHub. `sync_status` (string, 20 characters, default "pending") holds the current state machine value. `last_push_at` (nullable timestamp) records the most recent successful push. `last_push_error` (nullable text) captures the error from the most recent failed push attempt. For projects belonging to users without GitHub connections, `sync_status` remains at its default and is ignored by all code paths.

**New `pending_writes` table**: Five columns. Auto-incrementing integer primary key. `project_id` (foreign key to Project) identifies which project the write belongs to. `filename` (string, 255 characters) is the relative file path within the project directory. `content` (text) holds the full file body — markdown content is typically 2–20KB, well within Postgres text column limits. `created_at` (timestamp, defaulting to now) determines processing order. Rows are deleted after successful GitHub push. The table's steady-state size under normal operation is near zero — rows exist only during the window between local write and GitHub confirmation, typically under 60 seconds.

## Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| **GitHub API client** | PyGithub library behind `github_client/adapter.py` | Handles GitHub App JWT signing, installation token exchange, and token caching natively. The adapter boundary (P1) means PyGithub is an implementation detail — swappable without touching any consumer. Saves significant implementation time versus raw HTTP for the App auth flow. |
| **Write-ahead log** | Neon Postgres `pending_writes` table | Already the project database. Adding a table is zero new infrastructure. WAL insert latency is ~5ms. Neon's managed Postgres SLA provides the durability guarantee. No Redis, no external queue (per constraints). |
| **Background sync** | `threading.Thread` with daemon=True | Matches the existing background job pattern used by AI generation in `modules/ai/`. Module-level dict for worker state. Single worker thread — no concurrency framework needed. `gunicorn --workers 1 --worker-class gthread` (existing deploy pattern from references) ensures the thread coexists with the WSGI server. |
| **GitHub push API** | Contents API (per-file PUT) | Each pipeline run generates 5–6 files. Per-file push means 5–6 API calls — simple, debuggable, well within the 5,000 requests/hour rate limit. The Git Data API (batch tree commits) would reduce to 1 call but requires constructing tree objects, managing base trees, and handling blob SHAs — complexity that is not justified until pipeline throughput exceeds several hundred runs per hour. |
| **Token caching** | In-process dict with expiry check | GitHub installation tokens last 1 hour. The token manager caches the token and its expiry timestamp in a module-level dict (matching the existing in-process state pattern). Before each API call, the adapter checks whether the cached token is still valid (with a 5-minute safety margin) and refreshes if needed. No external cache layer required. |
| **Schema migration** | Alembic (if already in use) or raw SQL migration file | Additive-only changes: three new nullable columns on User, four new columns on Project, one new table. No data transformation, no column renames, no index rebuilds. Safe to run against production with zero downtime. |

## Design Decisions

| Decision | Rationale | Trade-off |
|---|---|---|
| **GitHub App over OAuth App** | Installation-scoped tokens (not user-scoped), fine-grained permissions (`contents: write` only), higher rate limits, survives user password changes. Requires more setup (App registration, private key management) but the security and reliability benefits are non-negotiable for a feature that manages user data. | More complex initial registration — must generate and securely store an App private key. One-time cost, paid during Task 1. |
| **Neon WAL over synchronous GitHub push** | Decouples durability from GitHub availability. A write is durable in ~5ms (Neon INSERT) instead of ~1.5s (GitHub API round-trip). The pipeline generates 5–6 files in sequence — synchronous push would add 8–10 seconds of total latency. The WAL also provides crash recovery: if the container dies mid-pipeline, completed files are safe in Neon. | Adds a table, a background worker, and a state machine. More moving parts than a synchronous push. Accepted because the latency and reliability improvements are essential for production use. |
| **Per-file Contents API over Git Data API** | The Contents API requires one PUT per file — straightforward, stateless, and easy to retry individually. The Git Data API batches files into a single commit via tree construction, which is more efficient at scale but requires managing tree SHAs, base trees, and blob references. At 5–6 files per pipeline run, the simplicity of per-file push outweighs the round-trip savings of batching. | More API calls per pipeline run (5–6 vs 1). GitHub history on the remote shows individual file commits rather than atomic pipeline commits. Both are acceptable at current scale. Revisit trigger: consistent rate-limit pressure or a user requirement for atomic multi-file commits. |
| **Lazy-load reads over bulk restore on boot** | A bulk restore would need to fetch every file for every project at startup — potentially hundreds of files for an active user. Lazy-load means boot is instant (project metadata comes from Neon) and each file pays ~200–300ms on its first access. This keeps container startup fast and predictable regardless of data volume. | The first read after a restart is slower than a warm-cache read. Users may notice a brief delay when opening a project for the first time after a deploy. Acceptable because subsequent reads are instant and the alternative (bulk restore) creates an unpredictable, potentially slow boot. |
| **Single repo per user over repo-per-project** | One repository keeps provisioning simple (create once, push to subdirectories) and avoids proliferating repos on the user's GitHub account. The directory-per-project structure inside the repo mirrors the existing local filesystem layout, so no path transformation is needed. | At very high project counts (100+), the repository could become unwieldy to browse on GitHub. Revisit trigger is stated in the epic: 100+ projects per user. Migration path: split into per-project repos with a one-time reorganization script. |
| **Overwrite-and-log for conflicts over merge UI** | Specview is the single writer. Users are told their GitHub repo is a durable store, not a collaboration workspace. If a user edits a file directly on GitHub and Specview overwrites it, Specview logs a warning. Building a merge UI for a conflict that should rarely occur violates P4. | External edits to the GitHub repo are silently overwritten. Users who edit specs directly on GitHub will lose those edits. Accepted because the value proposition is "Specview writes, GitHub stores" — not bidirectional sync. Revisit trigger: user feedback indicating meaningful external edit loss, or 409 conflict rate exceeding 1% of pushes. |
| **git_store enhanced internally over new write/read module** | Feature code calls `git_store.write_file()` and `git_store.read_file()` today. Enhancing these functions internally (adding WAL insert on write, GitHub fallback on read) means zero changes to any feature module. The `test_pygit2_isolation.py` boundary test continues to pass. The alternative — a new module that wraps `git_store` — would require updating every call site and introduce an unnecessary layer. | `git_store/service.py` grows in responsibility. Mitigated by delegating the sync concern to `sync/service.py` — `git_store` calls into the sync module for WAL operations but does not contain sync logic itself. |
| **pending_writes rows kept indefinitely on failure** | A failed row represents content that the user generated but GitHub never received. Deleting it means silent data loss — the worst possible outcome for a durability feature. Keeping it means the table could accumulate rows if a user's GitHub connection breaks permanently, but the storage cost is negligible (text content in Postgres) and the operational signal is valuable. | The `pending_writes` table may contain stale rows for permanently broken connections. Mitigation: a future admin endpoint or scheduled job can clean up rows older than a configurable threshold, but only with explicit operator action. |

## Graceful Degradation

The architecture must ensure that users without a GitHub connection experience zero regressions — this is an explicit success criterion.

The gate is a single null check: if a user's `github_installation_id` is null, the sync layer is completely bypassed. Write path behavior is identical to today's: local filesystem commit, no WAL insert, no sync worker involvement. Read path behavior is identical: local filesystem read, no GitHub fallback. The `sync_status` column defaults to `pending` but is never read or displayed for unconnected users.

If GitHub's API is unavailable for a connected user, the Neon WAL guarantees that writes are durable. The sync worker retries on its exponential backoff schedule. Reads that hit the local cache succeed normally; reads that require a GitHub fetch will fail with a clear error indicating that the remote store is temporarily unavailable and the file will be accessible when the connection recovers.

If Neon is unavailable, the system degrades to the current behavior: files are written to the local filesystem only. The WAL insert fails, but the local write has already succeeded. A Neon outage during a write means that specific file is not durably stored beyond the container's lifetime — the same risk that exists today for all files. This is an accepted degradation mode, not a new risk.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **GitHub API rate limit exhaustion** | Low at current scale. 5,000 requests/hour allows ~800 pipeline runs (6 pushes each) before pressure. | Sync delays; pending_writes accumulate until rate limit resets. | Sync worker respects `Retry-After` headers. Rate-limit errors are transient — the worker backs off and retries. Monitor rate-limit remaining header to get early warning. |
| **GitHub outage during push** | Rare but possible (GitHub reports ~99.9% uptime). | Pushes fail; pending_writes accumulate. No data loss — content is safe in Neon WAL. | Sync worker retries with exponential backoff. Once GitHub recovers, the backlog clears automatically. |
| **Installation token expiry mid-batch** | Possible during large backfills (60+ files taking 60–90 seconds while token lasts 1 hour). | Individual push fails with 401. | Token manager proactively refreshes when the cached token has less than 5 minutes remaining. A 401 response triggers an immediate token refresh and retry. |
| **User revokes GitHub App installation** | Possible at any time — user has full control. | All pushes fail. `sync_status` moves to `failed` for all projects. Content remains safe in Neon WAL. | Detect the `installation_deleted` webhook (future enhancement) or detect consistent 401 errors and surface a "reconnect GitHub" prompt. For v1, the `last_push_error` field provides the diagnostic. |
| **pending_writes table grows unbounded** | Only if GitHub connection is permanently broken and user keeps generating specs. | Postgres storage grows slowly (spec files are 2–20KB). No performance impact on other queries. | Acceptable for v1. A future admin cleanup job can purge rows older than a configurable age, but only with explicit action — never silent deletion of user content. |
| **Neon unavailable during write** | Rare (Neon provides managed Postgres with high availability). | WAL insert fails; file exists only on local filesystem. If container restarts before Neon recovers, that specific file is lost. | This is the pre-existing risk for all files today. The architecture does not make it worse. A future enhancement could buffer failed WAL inserts to a local file for retry, but this adds complexity for an unlikely scenario. |

## Related Documents

- [Analysis](./analysis.md) — Data loss scenarios and existing infrastructure that drive this architecture
- [Epic](./epic.md) — Scope boundaries, task breakdown, and success criteria this architecture fulfills
- [Timeline](./timeline.md) — Task sequencing, dependencies, and progress tracking