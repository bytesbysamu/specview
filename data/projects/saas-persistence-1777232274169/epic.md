# 🎯 Epic: SaaS Persistence

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

spec-doc currently stores every markdown file on the filesystem with no user ownership. Every other SaaS capability — authentication, billing, per-tenant query — requires a `user_id` foreign key, and that foreign key has nowhere to land until a relational entity exists. This epic creates the two-tier foundation: SQL for row-level metadata (users, projects, subscriptions) and a per-project git repository for markdown content. Once the foundation is in place, auth and monetisation epics can ship without waiting for a painful retrofit of an entire call-site surface.

The git-backed content layer does more than replace a flat folder. Every file write becomes a commit, making version history, per-file diff, and one-click revert available as soon as the storage layer lands — features that would otherwise require a custom SQL versioning schema. The same per-project repository also defines the future "Connect GitHub" upsell: the export mechanism is a `git push`, not a purpose-built data-export pipeline. Competitors on SQL-blob storage would need a dedicated migration to reach this capability.

The bubls SQLModel + Alembic shape is in production and ports near-verbatim, capping the DB layer at roughly half a day. The net-new git layer is small. The cost of delay is compounding: every new route written against the filesystem is another call site to retrofit once auth lands.

**Value Proposition**: Establishes user-scoped project ownership and append-only file history so that auth, billing, and version-control features can ship without data-layer retrofits.

---

## Scope

### What This Epic Covers

- **DB engine module** (`modules/db/`) — session factory and `DATABASE_URL` resolution targeting SQLite for dev and Postgres for prod with the same DDL
- **User entity** (`modules/auth/models.py`) — Neon-Auth-linked identity record; the anchor for every other foreign key
- **Project entity** (`modules/projects/models.py`) — per-user project row with git-repo pointer and `latest_commit_sha` field
- **Alembic configuration** — `alembic.ini`, `migrations/env.py`, and `0001_initial_schema.py` covering User + Project + Subscription + UsageCounter atomically (sister entity files co-authored with the monetisation epic)
- **Git store module** (`modules/git_store/`) — per-project working repository; seven public operations: init, write, read, list, history, diff, revert, and delete (internal use only)
- **ProjectRepository SQL implementation** — concrete implementation of the repository protocol; `create()` is atomic across DB insert and git init, with rollback on git failure
- **Three file-history endpoints** — `GET history`, `GET diff`, `POST revert` wired into the projects blueprint; no Angular UI required in this epic
- **Filesystem migration script** (`scripts/migrate_filesystem_to_git_db.py`) — one-shot, idempotent import of existing on-disk projects into the new DB and git layer

### What This Epic Does NOT Cover

- ❌ **Subscription and UsageCounter entity class definitions** — authored in the monetisation epic; included in the shared migration only, not defined here
- ❌ **Neon Auth JWT middleware / `g.current_user`** — auth epic owns this; routes in this epic assume the middleware exists at wire-up time
- ❌ **Angular history UI** — endpoints land here; the editor panel consuming them is a separate frontend epic
- ❌ **`delete_file()` HTTP endpoint** — the git op ships as an internal operation for retry-recovery; no public route belongs here until a concrete UI consumer exists
- ❌ **FS repository as a post-migration fallback** — once the migration runs, the filesystem implementation is deleted; keeping it is dead code
- ❌ **GitHub OAuth and remote push** — Phase 4; re-scopes when that brain dump exists
- ❌ **Collaborator / ProjectShare model** — single owner per project for v1; join table has no consumer yet
- ❌ **Soft delete** — hard delete cascades to git repo deletion; restore-from-trash has no consumer yet

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **DB Engine + User/Project Entities** | None | Task 2 | 0.5 days | High |
| 2 | **Git Store Module** | None | Task 1 | 0.5 days | High |
| 3 | **ProjectRepository SQL Implementation** | Tasks 1, 2 | — | 0.5 days | High |
| 4 | **File History Endpoints** | Task 3 | — | 0.25 days | High |
| 5 | **Filesystem Migration Script** | Tasks 1, 2, 3 | — | 0.25 days | Low |

### Task 1: DB Engine + User/Project Entities

Creates `modules/db/` with the session factory and `DATABASE_URL` resolution. Defines the `User` and `Project` SQLModel classes. Delivers `alembic.ini`, `migrations/env.py`, and a stub `0001_initial_schema.py` that is completed once the monetisation epic contributes its Subscription and UsageCounter class files; both epics commit the finalised migration together. The open question from the Analysis — SQLite-only versus Neon from day one — is resolved here as SQLite for dev and Postgres for prod with identical DDL, accepting Postgres as an explicit external dependency for SaaS mode.

**Port budget**: Near-verbatim from the bubls `kw-data` shape (~50 LOC for engine, ~40 LOC for the two entities). Subscription and UsageCounter class definitions are deferred to the monetisation epic.

### Task 2: Git Store Module

Creates `modules/git_store/` with seven public operations. All writes are auto-committed with a structured message and a fixed system author. The Docker image change required for the `pygit2` native dependency (`libgit2`) is part of this task's definition of done — without it, the image builds but git ops fail at runtime. Per-project repository isolation is the chosen shape; the shared-monorepo alternative is closed per the Analysis. The `delete_file()` operation ships here for internal retry-recovery use; no HTTP route is added.

**Port budget**: Net-new (~150 LOC). No equivalent in bubls.

### Task 3: ProjectRepository SQL Implementation

Delivers the concrete SQL implementation of the `ProjectRepository` protocol and registers it on the app factory as `current_app.project_repository`. The `create()` method must be atomic: the DB insert rolls back if `git_store.init_repo()` fails, ensuring no orphaned rows. Replaces the current filesystem-based project resolution in all existing routes. The filesystem implementation is deleted in this PR, not deprecated — the Analysis explicitly flags keeping it as dead code and scope inflation.

**Port budget**: ~60 LOC for the five protocol methods. Filesystem implementation is removed.

### Task 4: File History Endpoints

Adds three routes to the projects blueprint: file commit history, unified diff between two SHAs, and revert-to-SHA. Each route resolves the project through `current_app.project_repository` and delegates content operations to `git_store`. No Angular UI is in scope — endpoints are exercised through the test suite and available for a future frontend PR without further backend work.

**Port budget**: ~30 LOC across three route handlers. Angular integration deferred.

### Task 5: Filesystem Migration Script

One-shot, idempotent script that imports all existing on-disk projects into the new DB and git layer. Skips any slug that already exists as a row, making it safe to re-run. Once verified against the dev dataset, `PROJECT_REPOSITORY=sql` is set in `.env` and the filesystem path is retired. The Analysis flags the migration trigger as undefined — this task resolves it as a manual CLI step per environment; production should reject `PROJECT_REPOSITORY=fs` post-migration.

**Port budget**: ~60 LOC. No cron, no CI job, no automation — runs once per environment.

---

## Success Criteria

- ✅ All existing project routes (`list`, `get`, `update_file`) pass the full test suite against the SQL + git backend with no filesystem reads
- ✅ `POST /projects` creates a DB row and a git repository atomically; a forced git-init failure produces no orphaned DB row
- ✅ `GET .../files/<filename>/history` returns a commit log for a file written at least twice
- ✅ `POST .../files/<filename>/revert` restores a previous version and advances `latest_commit_sha` on the Project row
- ✅ Migration script runs idempotently against the existing dev dataset; re-running produces no duplicate rows or repositories
- ✅ `make test` passes with `DATABASE_URL=sqlite:///./test.db` — no Postgres instance required in CI
- ✅ `make check-dtos` passes after `0001_initial_schema.py` is committed alongside all four entity files

---

## Non-Goals

- ❌ **Markdown content in SQL** — git is the canonical store for all file content; SQL never holds markdown blobs
- ❌ **Multi-region / read replicas** — single database instance for v1; revisit at first paid customer
- ❌ **`User.plan` sync mechanism** — the field is denormalised for read convenience; the write path that keeps it current is owned by the monetisation epic's subscription webhook handler, as flagged in the Analysis
- ❌ **Vector search across projects** — speculative; no consumer exists
- ❌ **Branching / merge requests within spec-doc** — git supports it; no UI consumer exists and no second use case justifies the abstraction
- ❌ **Custom commit signing** — Phase 4+ enterprise concern

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview