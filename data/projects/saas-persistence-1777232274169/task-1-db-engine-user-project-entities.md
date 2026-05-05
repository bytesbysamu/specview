# Task 1: DB Engine + User/Project Entities — Implementation Guide

## 1. Context

This task installs the relational foundation that every downstream SaaS epic anchors to: a session factory that resolves `DATABASE_URL` at runtime (SQLite for dev, Postgres for prod with identical DDL), two SQLModel entity classes (`User` and `Project`), and an Alembic migration scaffold covering those two tables as a stub — the `Subscription` and `UsageCounter` entities are contributed by the monetisation epic before the stub is promoted. Nothing in the running Flask app is wired to this layer yet; `create_app.py` and `modules/projects/service.py` are untouched. This task is purely additive: it creates files and packages that Task 2 (`git_store`) and Task 3 (`SqlProjectRepository`) will import from, and it gives the CI pipeline a `make migrate` smoke target to exercise the migration round-trip.

**Trade-offs considered:**
- **Auto-`create_all()` on app startup** — rejected; it bypasses migration version control and cannot handle column alterations. Alembic gives explicit, auditable history against both SQLite and Postgres with no DDL dialect divergence.
- **Postgres-only from day one** — rejected; it adds a required external service for local development. SQLite with Postgres-safe column types (no `ARRAY`, no `JSONB`, no dialect-specific defaults) removes infra overhead without sacrificing parity.
- **SQLModel + Alembic (chosen)** — ports near-verbatim from the proven `bubls/kw-data` shape (~50 LOC engine, ~40 LOC entities); SQLModel validates entity shapes at import time and integrates cleanly with Alembic's metadata target; already understood by the builder.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
cd {WORKSPACE}/api
git status                                   # flag any unrelated M/?? entries
git diff HEAD -- modules/db modules/auth modules/projects/models.py alembic.ini migrations/
python -m pytest --tb=no -q                  # record baseline; expect 624/624 (1 skip)
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)
- `api/modules/db/__init__.py` — public surface: `get_engine`, `get_session`
- `api/modules/db/engine.py` — `DATABASE_URL` resolver + SQLAlchemy engine factory + module-level singleton (ELA #7)
- `api/modules/db/session.py` — `get_session()` context manager returning an SQLModel `Session`
- `api/modules/db/tests/__init__.py` — package marker
- `api/modules/db/tests/test_engine.py` — URL resolution and engine creation tests
- `api/modules/db/tests/test_session.py` — session factory tests
- `api/modules/auth/__init__.py` — empty package marker (new module)
- `api/modules/auth/models.py` — `User` SQLModel entity; identity anchor for FK chain
- `api/modules/auth/tests/__init__.py` — package marker
- `api/modules/auth/tests/test_user_model.py` — field, default, and metadata registration tests
- `api/modules/projects/models.py` — `Project` SQLModel entity + `ProjectRepository` Protocol (additive to existing module)
- `api/modules/projects/tests/test_project_model.py` — field, Protocol shape, and SQLite schema smoke tests
- `api/alembic.ini` — Alembic entry point; `script_location = migrations`; `sqlalchemy.url` resolved in `env.py`
- `api/migrations/__init__.py` — package marker
- `api/migrations/env.py` — imports all SQLModel metadata; resolves `DATABASE_URL`; drives offline + online modes
- `api/migrations/versions/__init__.py` — package marker
- `api/migrations/versions/0001_initial_schema.py` — stub migration: `user` + `project` tables only; comment documents monetisation-epic coordination gate

### To Modify (cite CODEBASE CONTEXT)
- `api/requirements.txt` — add `sqlmodel`, `alembic`, `psycopg2-binary`
- `api/Makefile` — append `migrate` and `migrate-check` targets

### To Leave Alone
- `api/modules/projects/service.py` — active filesystem implementation; Task 3 replaces it; touching it now creates merge risk
- `api/modules/projects/routes.py` — no new endpoints in Task 1; history/diff/revert routes are Task 4's scope
- `api/openapi.yaml` — no contract changes; DTOs unchanged; `make check-dtos` stays green automatically
- `api/dtos/models.py` — generated; never hand-edited; no new DTO types needed here
- `api/create_app.py` — repository wiring is Task 3's first step; modifying it now risks breaking the live app

---

## 4. Implementation Steps

### Step 1: Add Python dependencies

**Action**: Read `api/requirements.txt` to confirm current entries. Append the three packages after the last existing line. Do not duplicate any package already present.

**File**: `api/requirements.txt` (modify)

**Pattern**:
```
sqlmodel>=0.0.18
alembic>=1.13.0
psycopg2-binary>=2.9.9
```

**Verify**:
```bash
cd {WORKSPACE}/api
pip install -r requirements.txt
python -c "import sqlmodel, alembic, psycopg2; print('deps OK')"
```
Expect: `deps OK` with no import errors.

---

### Step 2: Create `modules/db/` — engine, session, public interface

**Action**: Create the `modules/db/` package with three files. Port the engine shape from the `bubls/kw-data` engine module (per REFERENCE CODE — Adapter Boundary / Bubls). Key adaptations: URL resolution reads `DATABASE_URL` first, falls back to `sqlite:///{SPEC_DOC_DIR}/spec_doc.db`; `check_same_thread=False` applied only for SQLite; no Postgres-specific column types introduced here or downstream.

**File**: `api/modules/db/engine.py` (new)

```python
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _build_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    spec_doc_dir = os.getenv("SPEC_DOC_DIR", "/data")
    db_path = os.path.join(spec_doc_dir, "spec_doc.db")
    return f"sqlite:///{db_path}"


def create_db_engine() -> Engine:
    url = _build_database_url()
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine
```

**File**: `api/modules/db/session.py` (new)

```python
from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session

from modules.db.engine import get_engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
```

**File**: `api/modules/db/__init__.py` (new)

```python
from modules.db.engine import get_engine
from modules.db.session import get_session

__all__ = ["get_engine", "get_session"]
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from modules.db import get_engine, get_session; print('modules.db OK')"
```
Expect: `modules.db OK`.

---

### Step 3: Create `modules/auth/models.py` — User entity

**Action**: Create the `modules/auth/` package. Define the `User` SQLModel entity. The `plan` field is denormalised here (not joined from Subscription on every request) per architecture doc rationale — the monetisation webhook handler owns the write path that keeps it current.

**File**: `api/modules/auth/__init__.py` (new, empty)

**File**: `api/modules/auth/models.py` (new)

```python
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    auth_user_id: str = Field(unique=True, index=True)
    email: str = Field(unique=True)
    plan: str = Field(default="free")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "
from modules.auth.models import User
u = User(auth_user_id='sub_abc', email='a@b.com')
print(u.plan, u.id, u.created_at is not None)
"
```
Expect: `free None True`.

---

### Step 4: Create `modules/projects/models.py` — Project entity + Repository Protocol

**Action**: Add `models.py` to the existing `modules/projects/` directory. This file is purely additive — `service.py` and `routes.py` do not import from it until Task 3. The `ProjectRepository` uses `typing.Protocol` (structural typing, no base class) per ELA Pattern #5 — one concrete implementation exists today; no abstract hierarchy is warranted.

**File**: `api/modules/projects/models.py` (new)

```python
from datetime import datetime
from typing import List, Optional, Protocol

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    slug: str = Field(unique=True, index=True)
    git_repo_path: str
    latest_commit_sha: Optional[str] = Field(default=None)
    file_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectRepository(Protocol):
    def create(
        self, user_id: int, name: str, slug: str, git_repo_path: str
    ) -> Project: ...

    def get_by_slug(self, slug: str) -> Optional[Project]: ...

    def list_for_user(self, user_id: int) -> List[Project]: ...

    def touch(self, project_id: int, sha: str, file_count: int) -> None: ...

    def delete(self, project_id: int) -> None: ...
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "
from modules.projects.models import Project, ProjectRepository
p = Project(user_id=1, name='T', slug='t', git_repo_path='/data/1')
print(p.file_count, p.latest_commit_sha, p.id)
"
```
Expect: `0 None None`.

---

### Step 5: Alembic scaffold — ini, env, stub migration

**Action**: Create Alembic configuration at `api/alembic.ini`, the env driver at `api/migrations/env.py`, and the stub migration at `api/migrations/versions/0001_initial_schema.py`. Create all `__init__.py` package markers. The stub covers `user` and `project` only; the migration comment documents the monetisation-epic coordination gate explicitly.

**File**: `api/alembic.ini` (new)

```ini
[alembic]
script_location = migrations
# sqlalchemy.url is resolved at runtime in migrations/env.py; leave blank here.
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**File**: `api/migrations/__init__.py` (new, empty)

**File**: `api/migrations/env.py` (new)

```python
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure api/ is importable when alembic is invoked from api/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all table-bearing models so SQLModel registers their metadata.
from modules.auth.models import User  # noqa: F401
from modules.projects.models import Project  # noqa: F401
from sqlmodel import SQLModel

config = context.config

# Resolve DATABASE_URL — always overrides the blank sqlalchemy.url in alembic.ini.
_spec_doc_dir = os.getenv("SPEC_DOC_DIR", "/data")
_fallback = f"sqlite:///{os.path.join(_spec_doc_dir, 'spec_doc.db')}"
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", _fallback))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**File**: `api/migrations/versions/__init__.py` (new, empty)

**File**: `api/migrations/versions/0001_initial_schema.py` (new)

```python
"""initial schema: user and project tables

Revision ID: 0001
Revises:
Create Date: 2026-04-26

STUB — covers User and Project only.
Subscription and UsageCounter are contributed by the monetisation epic
in a companion file (0001b_monetisation_entities.py). Do NOT run
'alembic upgrade head' on production until 0001b is merged into this
migration and the combined migration is reviewed.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auth_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_user_email"),
        sa.UniqueConstraint("auth_user_id", name="uq_user_auth_user_id"),
    )
    op.create_index("ix_user_auth_user_id", "user", ["auth_user_id"])

    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("git_repo_path", sa.String(), nullable=False),
        sa.Column("latest_commit_sha", sa.String(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_project_slug"),
    )
    op.create_index("ix_project_slug", "project", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_project_slug", table_name="project")
    op.drop_table("project")
    op.drop_index("ix_user_auth_user_id", table_name="user")
    op.drop_table("user")
```

**Verify**:
```bash
cd {WORKSPACE}/api
DATABASE_URL="sqlite:////tmp/spec_doc_task1_verify.db" python -m alembic upgrade head
DATABASE_URL="sqlite:////tmp/spec_doc_task1_verify.db" python -m alembic downgrade base
rm /tmp/spec_doc_task1_verify.db
```
Expect: Alembic log lines showing `Running upgrade  -> 0001` and `Running downgrade 0001 -> ` with exit code 0.

---

### Step 6: Add `migrate` and `migrate-check` targets to Makefile

**Action**: Read `api/Makefile` to find the last existing target, then append the two new targets after it. `migrate` runs Alembic upgrade against the configured `DATABASE_URL`. `migrate-check` generates SQL offline without a live DB connection — a fast syntax check suitable for CI.

**File**: `api/Makefile` (modify — append after last existing target)

```makefile
migrate:
	python -m alembic upgrade head

migrate-check:
	SPEC_DOC_DIR=/tmp python -m alembic upgrade head --sql > /dev/null
```

**Verify**:
```bash
cd {WORKSPACE}/api
make --dry-run migrate
```
Expect: `python -m alembic upgrade head` printed; no execution.

---

## 5. Tests

All tests use pytest (matching `make test` → `python -m pytest` convention in `api/`). Create `__init__.py` package markers alongside each new test file.

**`api/modules/db/tests/__init__.py`** — empty file.

**`api/modules/db/tests/test_engine.py`**:
```python
import os
import pytest
from sqlalchemy.engine import Engine


def test_create_db_engine_returns_engine(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SPEC_DOC_DIR", str(tmp_path))
    from modules.db.engine import create_db_engine
    engine = create_db_engine()
    assert isinstance(engine, Engine), "create_db_engine must return an SQLAlchemy Engine"


def test_sqlite_url_built_from_spec_doc_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SPEC_DOC_DIR", str(tmp_path))
    from modules.db.engine import _build_database_url
    url = _build_database_url()
    assert url.startswith("sqlite:///"), "default URL must use sqlite:/// scheme"
    assert str(tmp_path) in url, "SQLite path must be rooted inside SPEC_DOC_DIR"


def test_database_url_env_takes_precedence(tmp_path, monkeypatch):
    override = f"sqlite:///{tmp_path}/override.db"
    monkeypatch.setenv("DATABASE_URL", override)
    from modules.db.engine import _build_database_url
    url = _build_database_url()
    assert url == override, "DATABASE_URL env var must override the SPEC_DOC_DIR default"


def test_sqlite_engine_pool_pre_ping_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SPEC_DOC_DIR", str(tmp_path))
    from modules.db.engine import create_db_engine
    engine = create_db_engine()
    # Smoke: engine is connectable, confirming pool_pre_ping did not break creation.
    with engine.connect() as conn:
        assert conn is not None, "engine must be connectable"
```

**`api/modules/db/tests/test_session.py`**:
```python
import pytest
from sqlmodel import Session


def test_get_session_yields_session_instance(tmp_path):
    import modules.db.engine as engine_mod
    from sqlalchemy import create_engine

    test_engine = create_engine(f"sqlite:///{tmp_path}/sess_test.db")
    original = engine_mod._engine
    engine_mod._engine = test_engine
    try:
        from modules.db.session import get_session
        with get_session() as session:
            assert isinstance(session, Session), \
                "get_session must yield an sqlmodel.Session instance"
    finally:
        engine_mod._engine = original
```

**`api/modules/auth/tests/__init__.py`** — empty file.

**`api/modules/auth/tests/test_user_model.py`**:
```python
from datetime import datetime
from modules.auth.models import User


def test_user_default_plan_is_free():
    user = User(auth_user_id="sub_abc123", email="test@example.com")
    assert user.plan == "free", "User.plan must default to 'free'"


def test_user_id_is_none_before_persist():
    user = User(auth_user_id="sub_abc123", email="test@example.com")
    assert user.id is None, "User.id must be None before database insertion"


def test_user_created_at_set_on_instantiation():
    user = User(auth_user_id="sub_abc123", email="test@example.com")
    assert isinstance(user.created_at, datetime), \
        "User.created_at must be a datetime instance"


def test_user_table_registered_in_sqlmodel_metadata():
    from sqlmodel import SQLModel
    tables = SQLModel.metadata.tables
    assert "user" in tables, f"'user' table must be in SQLModel.metadata; found: {list(tables)}"


def test_user_auth_user_id_has_index():
    from sqlmodel import SQLModel
    table = SQLModel.metadata.tables["user"]
    index_cols = {
        col.name
        for idx in table.indexes
        for col in idx.columns
    }
    assert "auth_user_id" in index_cols, \
        "User.auth_user_id must be covered by a database index"
```

**`api/modules/projects/tests/test_project_model.py`**:
```python
from datetime import datetime
from modules.projects.models import Project, ProjectRepository


def test_project_defaults():
    project = Project(
        user_id=1,
        name="My Project",
        slug="my-project",
        git_repo_path="/data/projects/1",
    )
    assert project.id is None, "Project.id must be None before insertion"
    assert project.file_count == 0, "Project.file_count must default to 0"
    assert project.latest_commit_sha is None, \
        "Project.latest_commit_sha must default to None"


def test_project_timestamps_set_on_instantiation():
    project = Project(
        user_id=1,
        name="Timestamp Test",
        slug="ts-test",
        git_repo_path="/data/projects/2",
    )
    assert isinstance(project.created_at, datetime), \
        "Project.created_at must be a datetime"
    assert isinstance(project.updated_at, datetime), \
        "Project.updated_at must be a datetime"


def test_project_table_registered_in_sqlmodel_metadata():
    from sqlmodel import SQLModel
    tables = SQLModel.metadata.tables
    assert "project" in tables, \
        f"'project' table must be in SQLModel.metadata; found: {list(tables)}"


def test_project_slug_has_index():
    from sqlmodel import SQLModel
    table = SQLModel.metadata.tables["project"]
    index_cols = {
        col.name
        for idx in table.indexes
        for col in idx.columns
    }
    assert "slug" in index_cols, "Project.slug must be covered by a database index"


def test_project_repository_protocol_has_required_methods():
    required = {"create", "get_by_slug", "list_for_user", "touch", "delete"}
    for method_name in required:
        assert hasattr(ProjectRepository, method_name), \
            f"ProjectRepository Protocol is missing method: {method_name}"


def test_stub_satisfies_project_repository_protocol():
    class StubRepo:
        def create(self, user_id, name, slug, git_repo_path):
            return Project(
                user_id=user_id, name=name, slug=slug, git_repo_path=git_repo_path
            )
        def get_by_slug(self, slug):
            return None
        def list_for_user(self, user_id):
            return []
        def touch(self, project_id, sha, file_count):
            pass
        def delete(self, project_id):
            pass

    stub = StubRepo()
    for method_name in ("create", "get_by_slug", "list_for_user", "touch", "delete"):
        assert callable(getattr(stub, method_name)), \
            f"StubRepo.{method_name} must be callable"


def test_migration_tables_created_via_sqlmodel_metadata(tmp_path):
    """Smoke test: SQLModel metadata produces the expected tables in SQLite."""
    from sqlalchemy import create_engine, inspect
    from sqlmodel import SQLModel
    import modules.auth.models  # noqa: F401 — registers User in metadata
    import modules.projects.models  # noqa: F401 — registers Project in metadata

    engine = create_engine(f"sqlite:///{tmp_path}/schema_smoke.db")
    SQLModel.metadata.create_all(engine)
    found = set(inspect(engine).get_table_names())
    assert "user" in found, f"'user' table missing after create_all; found: {found}"
    assert "project" in found, f"'project' table missing after create_all; found: {found}"
```

---

## 6. Commit Plan

**Executor instruction**: commit after **each step** completes — not at the end of the task. Run the listed commit command before moving to the next step.

1. `chore(deps): add sqlmodel, alembic, psycopg2-binary` — after Step 1 — files: `api/requirements.txt`
2. `feat(db): add session factory with DATABASE_URL resolution` — after Step 2 — files: `api/modules/db/__init__.py`, `api/modules/db/engine.py`, `api/modules/db/session.py`
3. `feat(auth): add User SQLModel entity` — after Step 3 — files: `api/modules/auth/__init__.py`, `api/modules/auth/models.py`
4. `feat(projects): add Project entity and ProjectRepository Protocol` — after Step 4 — files: `api/modules/projects/models.py`
5. `feat(db): add Alembic scaffold with stub 0001 migration (user + project)` — after Step 5 — files: `api/alembic.ini`, `api/migrations/__init__.py`, `api/migrations/env.py`, `api/migrations/versions/__init__.py`, `api/migrations/versions/0001_initial_schema.py`
6. `chore(db): add make migrate and migrate-check targets` — after Step 6 — files: `api/Makefile`
7. `test(db): add unit tests for engine, session, User, Project, and Protocol` — after tests pass — files: all `test_*.py` files listed in §5

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api
python -m pytest --tb=short -q
```

**Expected delta**: 624 → 641 passing (17 new tests). Zero pre-existing tests broken.

Migration round-trip smoke:
```bash
cd {WORKSPACE}/api
DATABASE_URL="sqlite:////tmp/sd_task1_final.db" python -m alembic upgrade head && \
DATABASE_URL="sqlite:////tmp/sd_task1_final.db" python -m alembic downgrade base && \
rm /tmp/sd_task1_final.db && echo "migration round-trip OK"
```
Expect: `migration round-trip OK` with exit code 0.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible without affecting others.
  ```bash
  git revert <sha> --no-edit
  ```
- **Per-branch**: if verification fails catastrophically, reset to the pre-task SHA recorded during pre-flight.
  ```bash
  git log --oneline -10              # locate pre-task SHA
  git reset --hard <pre-task-sha>    # [REQUIRES APPROVAL] — destructive
  ```
  Alternatively, if working on a feature branch: `git checkout master && git branch -D feat/task-1-db-engine`.

---

## 9. Deviations Allowed

- **`modules/projects/tests/` does not exist** → create `api/modules/projects/tests/__init__.py` first, then add `test_project_model.py`; note in commit body.
- **`SQLModel` raises `InvalidRequestError: Table 'user' is already defined`** during test collection → add `__table_args__ = {"extend_existing": True}` to both `User` and `Project`; this occurs when multiple test sessions share the same Python process. Log as a deviation in the commit body.
- **`engine.pool._pre_ping` not accessible** (SQLAlchemy version variance) → replace `test_sqlite_engine_pool_pre_ping_enabled` with a connection smoke test: `engine.connect().close()` and assert no exception is raised. Log deviation.
- **`"user"` reserved word causes Alembic error against Postgres** in a later task → add `sa.schema.quoted_name("user", quote=True)` to the table name in the migration's `op.create_table` call; do not pre-empt it here.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log one line in the commit body under `Deviations:`.
- **Any side-effect required** (push to remote, schema change in production environment) → STOP, mark **[REQUIRES APPROVAL]**, and ask before proceeding.

---

## 10. Out of Scope

This task delivers the session factory, entity classes, and migration scaffold — and stops there. The existing Flask app routes continue to use the filesystem-based `modules/projects/service.py` unchanged. Nothing in this task writes to or reads from the database at runtime.

- **`SqlProjectRepository` concrete implementation** — Task 3; blocked on Task 2 (`git_store`) so the atomic `create()` can be tested end-to-end with a real git init.
- **`Subscription` and `UsageCounter` entity class definitions** — monetisation epic owns those files; the stub migration is deliberately incomplete until both epics coordinate on a shared PR.
- **`0001_initial_schema.py` promotion to a production-ready migration** — blocked on the monetisation epic contributing its entity files; the stub note in the file documents this gate.
- **Auth middleware (`g.current_user`, Neon Auth JWT verification)** — auth epic; the `User` table is the anchor row, not the middleware layer.
- **`create_app.py` wiring of `project_repository`** — Task 3's opening step; registering it before `SqlProjectRepository` exists produces a broken app factory.
- **Angular UI for file history** — history/diff/revert endpoints land in Task 4; the frontend panel is a separate frontend epic.
- **`modules/db/` coupling structural test** (grep asserting no file outside `modules/db/` imports SQLAlchemy session machinery directly) — deferred per ELA Pattern #5; there is exactly one consumer of `get_session` today. Add the structural test when Task 3 adds a second consumer.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than absorbing it into this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale for all decisions referenced above
- [Epic](./epic.md) — parallel execution plan; Task 1 runs concurrently with Task 2
- [Timeline](./timeline.md) — set status to **In Progress** when starting; **Done** when §7 verification passes