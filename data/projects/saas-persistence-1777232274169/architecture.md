# 🏗️ Solution Architecture: SaaS Persistence

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Two-tier storage separates concerns by what each tier handles best. SQL (SQLite for dev, Postgres for prod with identical DDL) owns row-level metadata — user identity, project ownership, subscription state, usage counters — where relational constraints, foreign keys, and indexed queries provide value. Git (one working repository per project, via `pygit2`) owns markdown content, where line-level history, unified diff, and atomic rollback are native operations that a SQL versioning schema would have to reinvent at significant cost.

The join between tiers is lightweight: the `Project` row carries `git_repo_path` and `latest_commit_sha`. Every file write goes through `git_store.write_file()`, which commits and returns a SHA; the route handler calls `ProjectRepository.touch()` to advance that field. DB and git repo stay consistent because `touch()` only runs after a successful git commit — a failed write leaves the DB row unchanged.

This design makes three SaaS capabilities structural rather than bolt-on: version history and diff are free git operations (no SQL versioning schema), the future "Connect GitHub" export is `git push` to a user-supplied remote (no custom export pipeline), and user-scoped data isolation is a foreign-key constraint on `project.user_id` (no middleware filter). Every blocked epic — auth, monetisation, reliability — gains an unambiguous anchor once this layer ships.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #2 — Blueprint Module Structure | `modules/db/`, `modules/git_store/`, `modules/projects/` each own `service.py` with no cross-module imports beyond defined interfaces |
| ELA #3 — OpenAPI-First | Three new history/diff/revert endpoints declared in `openapi.yaml` first; DTOs regenerated before routes are written |
| ELA #5 — Not-Yet-Built | `ProjectRepository` has one concrete SQL implementation; no abstract base class until a second implementation exists |
| ELA #7 — In-Process State | Migration is a one-shot CLI invocation, not a background worker; no persistent job state required |
| Adapter boundary for git | All `pygit2` calls go through `modules/git_store/service.py`; no other module imports the library directly |
| Atomic create | DB insert and `git_store.init_repo()` are wrapped in a single try/except; a git failure triggers session rollback — no orphaned rows |

---

## System Boundaries

### What This System Includes

- `modules/db/` — session factory and `DATABASE_URL` resolution
- `modules/auth/models.py` — `User` SQLModel entity; the foreign-key anchor for Project, Subscription, UsageCounter
- `modules/projects/models.py` — `Project` SQLModel entity with `git_repo_path` and `latest_commit_sha`
- `ProjectRepository` protocol and its concrete SQL implementation, registered on the app factory
- `modules/git_store/service.py` — seven public git operations (init, write, read, list, history, diff, revert, delete)
- `alembic.ini`, `migrations/env.py`, `migrations/0001_initial_schema.py` — covers User + Project + Subscription + UsageCounter atomically
- Three HTTP endpoints: file history, unified diff, revert-to-SHA — wired into the projects blueprint
- `scripts/migrate_filesystem_to_git_db.py` — one-shot idempotent import of on-disk projects

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Subscription + UsageCounter entity definitions | Monetisation epic owns the class files; this epic owns the shared migration only |
| Neon Auth JWT middleware / `g.current_user` | Auth epic owns request-level identity; this epic assumes the middleware exists at wire-up time |
| Angular file-history UI | Endpoints land here; the editor panel is a separate frontend epic |
| `delete_file()` HTTP route | Ships as an internal git op for retry-recovery; no route until a UI consumer exists |
| Filesystem `ProjectRepository` after migration | Deleted, not deprecated — keeping it is dead code |
| GitHub OAuth and remote push | Phase 4; separate brain dump |
| Collaborator / ProjectShare model | Single owner per project for v1; join table has no consumer |
| Soft delete | Hard delete cascades to repo removal; restore-from-trash has no consumer |
| Markdown content in SQL | Git is the canonical store; SQL never holds markdown blobs |

---

## Component Design

### `modules/db/` — Session Factory

**Purpose**: Centralises `DATABASE_URL` resolution and session lifecycle so every other module gets a session without importing SQLAlchemy directly.

**Key Parts**:
- `engine.py` — creates the SQLAlchemy engine with `pool_pre_ping=True`; applies `check_same_thread=False` for SQLite only; avoids Postgres-specific column types so DDL is portable across both targets
- `session.py` — `get_session()` factory used wherever a DB session is needed

**Consumers**: `SqlProjectRepository` (Task 3), Alembic `migrations/env.py` (Task 1).

---

### `modules/auth/models.py` — User Entity

**Purpose**: Provides the identity anchor for every other foreign key. `auth_user_id` links the SQL row to the Neon Auth JWT without duplicating auth logic in this layer.

**Key Parts**:
- `User` SQLModel — `id` (PK), `auth_user_id` (unique, indexed), `email` (unique), `plan` (denormalised from Subscription for read convenience), `created_at`

**Why denormalise `plan`**: The auth middleware needs plan-level information on every request without a live join to Subscription. The monetisation epic's webhook handler owns the write path that keeps this field current — flagged as a non-goal for this epic.

**Consumers**: `SqlProjectRepository` (foreign key source), auth middleware (read), monetisation subscription webhook handler (write `plan` field).

---

### `modules/projects/models.py` — Project Entity + Repository Protocol

**Purpose**: Rows record project ownership and serve as the index into the git layer. The repository protocol decouples route handlers from storage implementation, enabling test stubs without a real DB or git repo.

**Key Parts**:
- `Project` SQLModel — `id`, `user_id` (FK → User), `name`, `slug` (unique, indexed), `git_repo_path`, `latest_commit_sha`, `file_count`, `created_at`, `updated_at`
- `ProjectRepository` Protocol — five methods: `create()`, `get_by_slug()`, `list_for_user()`, `touch()`, `delete()`
- `SqlProjectRepository` — the one concrete implementation; registered as `current_app.project_repository` in `create_app.py`

**Why a protocol with one implementation**: Not for future-proofing multiple backends — the filesystem implementation is deleted. The boundary exists for testability: fixtures supply a stub without standing up a real DB or git directory.

**Consumers**: All projects blueprint routes, Task 4 history endpoints, migration script.

---

### `modules/git_store/service.py` — Git Operations

**Purpose**: Encapsulates all `pygit2` calls behind a stable interface. No other module depends on the git library directly. Every write auto-commits; history is a free by-product.

**Key Parts**:
- `init_repo(project_id)` — creates a working repository at `/data/projects/<id>/`; writes an initial commit so HEAD is always valid
- `write_file(project_id, filename, content, msg)` — writes to the working tree and commits; returns the new SHA
- `read_file(project_id, filename, ref)` — reads a blob at any ref; defaults to HEAD
- `list_files(project_id, ref)` — lists blobs at a given tree ref
- `get_history(project_id, filename, limit)` — walks the commit log filtered to entries touching the named file
- `get_diff(project_id, filename, from_sha, to_sha)` — returns a unified diff string between two SHAs
- `revert_file(project_id, filename, to_sha)` — reads the blob at `to_sha` and writes it as a new commit; never rewrites history
- `delete_file(project_id, filename, msg)` — removes the blob and commits; internal use only, no HTTP route

**Why `pygit2` over subprocess**: Native libgit2 bindings eliminate shell-injection risk and subprocess overhead on every file write. The Docker image must include `libgit2` — this is part of Task 2's definition of done.

**Why revert creates a forward commit**: Rewriting history breaks any external clone or future GitHub mirror. A forward commit preserves the audit trail and keeps HEAD always advanceable without `--force`.

**Consumers**: `SqlProjectRepository.create()` (init), all update-file routes (write), Task 4 history/diff/revert endpoints, migration script.

---

### `migrations/` — Alembic Configuration

**Purpose**: Schema evolution without manual DDL. The initial migration is co-authored with the monetisation epic so all four entities land atomically.

**Key Parts**:
- `alembic.ini` — reads `DATABASE_URL` from environment
- `migrations/env.py` — imports all SQLModel metadata; runs against the configured engine
- `migrations/0001_initial_schema.py` — covers User + Project + Subscription + UsageCounter; committed only after the monetisation epic contributes its entity files

**Why one atomic migration**: Splitting across two PRs risks a state where User exists but Subscription does not, breaking foreign-key constraints in Postgres. Both epics co-commit the migration; each epic owns its own entity class files.

**Consumers**: `make migrate` (dev/prod), CI pipeline (DDL smoke check against SQLite).

---

### `scripts/migrate_filesystem_to_git_db.py` — One-Shot Import

**Purpose**: Imports all on-disk projects into the new DB and git layer without disrupting the existing dataset. Idempotent so re-runs are safe.

**Key Parts**:
- Iterates `/data/projects/` slugs; skips any slug already present as a DB row
- For each new project: inserts a `Project` row (owner = configured admin user), calls `git_store.init_repo()`, copies markdown files into the working tree, commits them, and calls `ProjectRepository.touch()` with the resulting SHA
- Exits non-zero on any per-project failure, leaving partial work visible for manual recovery

**Trigger**: Manual CLI invocation per environment. Production refuses `PROJECT_REPOSITORY=fs` after migration is verified. There is no automated trigger — one run per environment, not a recurring job.

**Consumers**: Developer (one invocation per environment).

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Relational DB | SQLite (dev) / Postgres on Neon (prod) | Same DDL avoids dialect drift; SQLite removes dev infrastructure; Neon is serverless Postgres with no instance to manage |
| ORM / schema | SQLModel + SQLAlchemy | Ports near-verbatim from bubls `kw-data`; validates model shapes at import time; Alembic-compatible |
| Schema migrations | Alembic | Proven in bubls; supports both SQLite and Postgres targets without DDL changes |
| Git operations | `pygit2` | Native libgit2 bindings; no shell injection risk; faster than subprocess per write |
| Git storage shape | Per-project working repository | Clean isolation; independent GitHub export; garbage-collect on delete; no cross-project blast radius |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Per-project git repo, not shared monorepo | Isolation, independent export, no single-repo blast radius | More inodes; higher init cost per project — acceptable at single-tenant scale |
| SQLite for dev, Postgres for prod | Removes dev infrastructure dependency; same DDL with Postgres-safe column types | Developers must avoid SQLite-only behaviour in migrations; pool config differs slightly |
| `latest_commit_sha` on Project row | Avoids a git HEAD read on every project-list query | Field can lag if `touch()` fails after a successful git write — mitigated by wrapping both in the same try/except |
| Revert creates a forward commit | Preserves audit trail; compatible with future GitHub mirror (no `--force` needed) | History is longer; no "clean" rollback — acceptable in an append-only content model |
| `ProjectRepository` protocol with one concrete implementation | Testability without real DB or git; no inheritance hierarchy | Protocol and implementation must be kept in sync manually — enforced by the structural test suite |
| Filesystem implementation deleted post-migration | Eliminates dead code and call-site ambiguity; forces a clean cut-over | No fallback — a failed migration must be resolved before switching `PROJECT_REPOSITORY=sql` |
| `0001_initial_schema.py` co-committed with monetisation epic | Ensures all four entities land atomically in Postgres; avoids broken FK state between PRs | Neither epic can finalise the migration independently — requires explicit coordination |

---

## Execution Flow

```
Phase 1 — Parallel foundation (Tasks 1 + 2 run simultaneously)
  Task 1: DB engine + User/Project entities + stub migration
  Task 2: git_store module + Docker image libgit2 change
                                   ↓
Phase 2 — Integration (Task 3, depends on both)
  Task 3: SqlProjectRepository + atomic create + filesystem impl deleted
                                   ↓
Phase 3 — Endpoints + migration (Tasks 4 + 5, both depend on Task 3)
  Task 4: history / diff / revert endpoints
  Task 5: migration script → manual run per environment → flip PROJECT_REPOSITORY=sql
```

---

## Open Questions

- **`0001_initial_schema.py` coordination** — the migration cannot be committed until the monetisation epic contributes `Subscription` and `UsageCounter` entity files. If the epics ship in separate PRs, Task 1's implementation guide must specify a stub-migration path (User + Project only, then a `0001b` addendum) so Task 3 is not blocked. Re-decide if both epics cannot be scheduled within the same sprint.

All other decisions from the brain dump are settled.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview