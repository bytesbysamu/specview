# spec-doc — SaaS Data Layer (SQLModel + Alembic, metadata only)

> **MERGED** into `braindump-saas-persistence.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.
> Read the consolidated version instead.

---

## (Original brain dump below — do not act on)

> **Priority**: P1 — foundational for all multi-tenant work.
> **Effort**: ~1 day (engine + Project + repo + Alembic env + migration script).
> **Blocks**: every other SaaS brain dump (auth, billing, metering all need `user_id` FKs).
> **Depends on**: nothing — can ship in parallel with the SDK provider track.
> **Siblings**: `braindump-saas-git-storage-layer.md` (paired — DB stores metadata, git stores content),
>               `braindump-saas-auth-magic-link.md` (User entity ships from auth, joined here),
>               `braindump-saas-stripe-billing.md` + `braindump-saas-usage-metering.md` (consumers).
> **Port from**: bubls `kw-data` module + `superapp_*` table convention. Near-verbatim.

## What

Add a SQLModel + Alembic data layer that stores **metadata only** — no markdown content. User accounts, project ownership, subscription state, usage counters, audit rows. Local dev uses SQLite; production uses Postgres (Neon).

**Markdown content lives in git, not in the database** — see the sibling `braindump-saas-git-storage-layer.md`. The data layer references the git repo by `Project.git_repo_path` and tracks the working-tree state via `Project.latest_commit_sha`. Diffs, history, blame, and revert are all served by git directly.

This split is the load-bearing decision: the relational store handles "who owns what, when did they pay, how many calls today"; git handles "what does the spec say, what did it say last week, why did it change". Both are best-of-breed at their job; trying to make the DB do versioning OR trying to make git do auth would be a worse system.

Port the metadata-only DDL pattern from bubls (`kw-data` module + `superapp_*` table convention with `spec_doc_*` prefix). Trendfy's Alembic migration pattern (idempotent + skip-if-exists) is the reference.

### 1. New module — `api/modules/db/`

```
modules/db/
├── __init__.py
├── engine.py           # SQLAlchemy engine + sessionmaker
├── base.py             # SQLModel base class
└── tests/test_engine.py
```

```python
# modules/db/engine.py
import os
from sqlmodel import create_engine, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./spec_doc.db")
ENGINE = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

def get_session() -> Session:
    return Session(ENGINE)
```

### 2. Entities (metadata only — NO markdown content)

```python
# modules/auth/models.py
class User(SQLModel, table=True):
    __tablename__ = "spec_doc_users"
    id: int | None = Field(default=None, primary_key=True)
    supabase_id: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    plan: str = Field(default="free")           # denormalised from Subscription
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


# modules/projects/models.py
class Project(SQLModel, table=True):
    __tablename__ = "spec_doc_projects"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="spec_doc_users.id", index=True)
    name: str
    slug: str = Field(unique=True, index=True)              # URL-safe; immutable

    # Git storage pointer — the actual files live in a git repo at this path.
    git_repo_path: str                                       # e.g. /data/projects/42/.git
    latest_commit_sha: str | None = None                    # advances on every update_file
    file_count: int = Field(default=0)                      # cached counter; rehydrated on git push

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# modules/billing/models.py — see braindump-saas-stripe-billing.md
# modules/usage/models.py   — see braindump-saas-usage-metering.md
```

**No `ProjectFile` table.** Project file content is read from git via the git-storage layer. The DB knows *that* a project exists, *who* owns it, and *which commit* is current; git knows *what* it contains.

### 3. Repository pattern — metadata-only

```python
# modules/projects/repository.py
class ProjectRepository(Protocol):
    def create(self, user_id: int, name: str) -> Project: ...
    def get_by_slug(self, user_id: int, slug: str) -> Project | None: ...
    def list_for_user(self, user_id: int) -> list[Project]: ...
    def touch(self, project_id: int, new_commit_sha: str) -> None: ...
    def delete(self, project_id: int) -> None: ...
```

`create()` does two things atomically: insert the `Project` row, then call `git_store.init_repo(project_id)` to create the git repo. If the git init fails, the row is rolled back.

`touch()` is called by the git-storage layer after every successful commit, advancing `latest_commit_sha` and `updated_at`. The route handler doesn't update these directly.

The Workflows epic's `WorkflowRepository` shape is the pattern (port → adapter); same hexagonal layout.

### 4. Alembic migrations — `api/migrations/`

Standard Alembic layout with `migrations/env.py` reading `DATABASE_URL`. Migration files git-tracked. `make migrate` runs `alembic upgrade head`. Production deploys run migrations as the first container step.

Initial migration `0001_initial_schema.py` creates: `spec_doc_users`, `spec_doc_projects`, `spec_doc_subscriptions`, `spec_doc_usage_counters`. (The latter two have their own brain dumps; the migration ships them all together for atomicity.)

### 5. Filesystem-to-git+DB migration script — one-shot

```python
# scripts/migrate_filesystem_to_git_db.py
"""For each existing /data/projects/<slug>/ directory:
  1. Insert a Project row (owner = configured admin user).
  2. Call git_store.init_repo(project_id) — creates the .git dir.
  3. Copy existing markdown files into the working tree.
  4. git add . && git commit -m "chore: import from filesystem".
  5. Update Project.latest_commit_sha.
"""
```

Idempotent: skips projects whose slug already exists. Run once, verify, switch `PROJECT_REPOSITORY=sql` in `.env`. The original FS layout can be deleted after the migration is verified.

### 6. Backward-compat — dual repository for the dev loop

```python
# create_app.py
backend = os.environ.get("PROJECT_REPOSITORY", "sql")
app.project_repository = (
    ProjectRepositorySql() if backend == "sql"
    else ProjectRepositoryFs()  # legacy — read/write directly to filesystem
)
```

The FS adapter still works for dev environments that haven't migrated. Production refuses to start with `PROJECT_REPOSITORY=fs`.

### 7. openapi.yaml

`Project` schema gains `latest_commit_sha`, `file_count`. Loses anything resembling a `files` field (clients fetch file content via the git-store endpoints, not via the project read).

## Why now

Every other SaaS brain dump (auth, billing, metering) needs `user_id` foreign keys. The data layer is the foundation. **The git-store decision keeps the DB small** — no markdown content means no large rows, no full-text search pressure, no version-table migration on every text edit.

The bubls Alembic + SQLModel shape is in production and ports near-verbatim. The only spec-doc-specific bit is dropping bubls's text-content tables in favour of git pointers — which is the right shape for the product's actual content model.

Order: **data-layer + git-store (parallel) → auth → billing → metering**.

## What's missing

One decision: **SQLite or Postgres in dev?** Options:
- (a) SQLite for dev, Postgres for prod (proposed) — zero local infrastructure; matches bubls
- (b) Postgres in both via Docker compose — full parity but adds a dev dependency
- (c) Neon serverless free tier even in dev — no local infra; costs nothing

(a) is right. The DDL stays portable as long as Postgres-specific types are avoided (no JSONB, no array columns, no `gen_random_uuid()`).

## Explicitly out of scope

- **Markdown content in the DB** — git-storage brain dump owns this entirely.
- **Project file versioning in the DB** — git's commit history is the version log; no `ProjectFileVersion` table needed.
- **Multi-region replication / read replicas** — single Postgres instance for v1.
- **Vector store / semantic search across projects** — speculative; needs a named consumer.
- **Hibernate Envers-style audit trail on metadata** — `created_at`/`updated_at` is sufficient; full audit logging waits for a real compliance trigger.
- **Per-project access sharing (collaborator model)** — single owner per project; `ProjectShare` row joins later when shared workspaces are scoped.
- **Soft delete** — hard delete cascades to git repo deletion for v1; restore-from-trash needs a real consumer first.
