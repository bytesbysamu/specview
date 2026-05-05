# 🛠️ Task 1: Model + migration

**Purpose**: Create the `WaitlistSignup` SQLAlchemy model and Alembic migration that establishes the `waitlist_signups` table, so Tasks 2–4 can build the endpoint and data-access layers on top of a known schema.

**Effort**: 1h

**Dependencies**: None

**Parallel With**: Task 2 (OpenAPI + DTOs)

**Blocks**: Task 3 (routes + service + repository need the model to import), Task 4 (module registration needs the model to exist), Task 5 (Trendfy data migration targets this table)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task creates the bottom layer of the waitlist module: one SQLAlchemy model and one Alembic migration. The `waitlist_signups` table stores email signups from the landing page and (later, via Task 5) ported Trendfy subscribers. The model is deliberately simple — four columns, no foreign keys, no JSONB — because a waitlist is an append-only funnel with exactly one write pattern (insert-or-conflict) and two read patterns (check existence, count by source). The module skeleton (`server/modules/waitlist/__init__.py`) is created here so Tasks 2–4 have a package to import from. No routes, no service, no repository, no DTOs — those are Tasks 2–3.

**Trade-offs considered**:
- **Integer PK vs UUID** — Integer chosen. Waitlist signups are append-only, never referenced by ID from external systems. Simpler, smaller, faster. Matches architecture decision.
- **Separate `source` index vs relying on unique constraint alone** — The unique constraint on `email` gives an implicit index there, but `source` has no uniqueness and needs its own index for filtered counts ("how many from Trendfy vs landing page"). Architecture specifies `idx_waitlist_source`.
- **`waitlist_signups` vs `superapp_waitlist_signups`** — Architecture chose `waitlist_signups` (no `superapp_` prefix). Waitlist is a standalone funnel table with no joins to `superapp_users`. If the executor discovers a project convention enforcing the prefix on every table, add it and log a deviation.

---

## 2. Pre-flight

Run BEFORE editing any file.

```bash
git status                                                 # flag unrelated M/?? entries; stash if dirty
git log -1 --format=%H                                     # record pre-task SHA (needed for §8 rollback)
git diff HEAD -- server/ 2>&1 | head -50                   # confirm target area clean

# Discover current state
ls server/modules/                                         # confirm modules/ dir structure
ls server/modules/waitlist/ 2>/dev/null || echo "waitlist module does not exist yet — expected"
ls server/migrations/versions/                             # list all migrations to find current head

# Identify the current Alembic head revision
cd server && alembic heads 2>&1                            # record the head revision ID for down_revision
cd ..

# Locate Base import — needed for the model
rg -l "class.*Base.*:" server/ --type py | head -5         # find where DeclarativeBase or declarative_base lives
rg "from.*import.*Base" server/modules/photoshoot/models.py server/modules/user/model.py 2>/dev/null   # check existing model import patterns

# Baseline test count
cd server && pytest -q 2>&1 | tail -3                     # record backend "N passed"
```

**If working tree is dirty on any target path**: stash or commit unrelated changes on a separate branch BEFORE starting.

**Baseline recorded**: capture backend count `[N_b]` — goes into commit bodies.

---

## 3. Files

### To Create (new)
- `server/modules/waitlist/__init__.py` (new) — module docstring only; package marker so other files can import from the module.
- `server/modules/waitlist/models.py` (new) — `WaitlistSignup` SQLAlchemy model. Depends on `Base` from wherever existing models import it (Pre-flight discovers the path).
- `server/migrations/versions/20260417_create_waitlist_signups.py` (new) — Alembic migration creating the `waitlist_signups` table with four columns and the `source` index. `down_revision` set to whatever Pre-flight discovers as the current head.
- `server/tests/test_waitlist_model.py` (new) — model instantiation + column-level assertions.

### To Modify
- None — this task only creates new files. Module registration in `server/app.py` is Task 4.

### To Leave Alone
- `server/modules/photoshoot/**` — unrelated feature module.
- `server/modules/user/**` — unrelated feature module.
- `server/modules/chain/**` — unrelated infrastructure module.
- `server/app.py` — module registration is Task 4; do NOT add `"waitlist"` to `ENABLED_MODULES` here.
- Any existing migration file — never edit past migrations.
- All frontend files (`src/app/**`) — no frontend changes in this task.

---

## 4. Implementation Steps

### Step 1: Discover Base import path and current Alembic head

**Action**: Execute the discovery commands from §2. Record: (a) the import path for `Base` (e.g., `from server.db import Base` or `from core.database import Base`), (b) the current Alembic head revision ID string.

**File**: read-only (no edits).

**Pattern**: (discovery only — informs Step 2 and Step 3).

**Verify**: both values recorded. If `Base` cannot be found, STOP and flag — the model cannot be created without knowing the declarative base.

### Step 2: Create the waitlist module package

**Action**: Create the module directory and `__init__.py`.

**File**: `server/modules/waitlist/__init__.py` (new)

**Pattern**:
```python
"""Waitlist module — email signup capture for landing page and ported subscribers."""
```

**Verify**: `python -c "import server.modules.waitlist"` or `python -c "from modules.waitlist import __doc__; print(__doc__)"` — expect no `ImportError`.

### Step 3: Create the WaitlistSignup model

**Action**: Create the SQLAlchemy model with four columns. Import `Base` from the path discovered in Step 1. Use `Mapped` + `mapped_column` (SQLAlchemy 2.x style, matching the existing model pattern from the codebase). Port the column definitions from the architecture doc's model spec.

**File**: `server/modules/waitlist/models.py` (new)

**Pattern**:
```python
"""WaitlistSignup SQLAlchemy model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from {BASE_IMPORT_PATH} import Base  # e.g., from core.database import Base — discovered in Step 1


class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="landing_page")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    def __repr__(self) -> str:
        return f"<WaitlistSignup id={self.id} email={self.email!r} source={self.source!r}>"
```

Replace `{BASE_IMPORT_PATH}` with the actual import discovered in Step 1. If the existing photoshoot model uses `from db import Base`, use that. Log the resolved path in the commit body.

**Verify**:
```bash
cd server && python -c "from modules.waitlist.models import WaitlistSignup; print(sorted(WaitlistSignup.__table__.columns.keys()))"
# expect: ['created_at', 'email', 'id', 'source']
```

### Step 4: Create the Alembic migration

**Action**: Create the migration that builds the `waitlist_signups` table. Set `down_revision` to the head revision discovered in Step 1. Include the `idx_waitlist_source` index on the `source` column. The unique constraint on `email` implicitly creates an index — no separate index needed.

**File**: `server/migrations/versions/20260417_create_waitlist_signups.py` (new)

**Pattern**:
```python
"""create waitlist_signups table

Revision ID: 20260417_create_waitlist_signups
Revises: {CURRENT_HEAD}
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260417_create_waitlist_signups"
down_revision = "{CURRENT_HEAD}"  # discovered in Step 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waitlist_signups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="landing_page"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_waitlist_source", "waitlist_signups", ["source"])


def downgrade() -> None:
    op.drop_index("idx_waitlist_source", table_name="waitlist_signups")
    op.drop_table("waitlist_signups")
```

Replace `{CURRENT_HEAD}` with the actual Alembic head from Step 1. If the head has changed since the architecture was written, use the actual current head and log the deviation.

**Verify**:
```bash
cd server && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
# expect: no errors; table exists after final upgrade
python -c "
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ.get('DATABASE_URL', 'sqlite:///dev.db'))
cols = {c['name'] for c in inspect(engine).get_columns('waitlist_signups')}
print(cols)
assert cols == {'id', 'email', 'source', 'created_at'}, f'unexpected columns: {cols}'
print('OK: all 4 columns present')
"
```

### Step 5: Write model tests

**Action**: Create `server/tests/test_waitlist_model.py` with assertions for column defaults, unique constraint, and repr. Match the existing pytest + SQLite-in-memory conftest convention used by other tests in `server/tests/`.

**File**: `server/tests/test_waitlist_model.py` (new)

**Pattern**: see §5 for full assertion bodies.

**Verify**:
```bash
cd server && pytest tests/test_waitlist_model.py -q
# expect: 6 tests passing
```

### Step 6: Run full backend suite

**Action**: Execute the complete pytest suite to confirm zero regressions.

**Verify**:
```bash
cd server && pytest -q
# expect: N_b + 6 passing, 0 failures introduced
```

---

## 5. Tests

Pytest, SQLAlchemy SQLite fixtures from `server/tests/conftest.py`. Names follow the repo's `condition_expectedOutcome` convention (no "should"). All tests wrapped in a class to avoid the `python_functions = ["*_*"]` caveat that collects bare helpers as tests.

```python
# server/tests/test_waitlist_model.py
from modules.waitlist.models import WaitlistSignup
from sqlalchemy.exc import IntegrityError
import pytest


class TestWaitlistSignup:

    def test_newSignup_sourceDefaultsToLandingPage(self, db_session):
        signup = WaitlistSignup(email="test@example.com")
        db_session.add(signup)
        db_session.commit()
        db_session.refresh(signup)
        assert signup.source == "landing_page", "default source must be 'landing_page'"

    def test_newSignup_createdAtPopulatedByServer(self, db_session):
        """Note: SQLite uses Python-side func.now() approximation. If this fails,
        §9 deviation for server_default=sa.text(\"(datetime('now'))\") applies."""
        signup = WaitlistSignup(email="ts@example.com")
        db_session.add(signup)
        db_session.commit()
        db_session.refresh(signup)
        assert signup.created_at is not None, "server_default func.now() must populate created_at"

    def test_newSignup_idAutoIncrements(self, db_session):
        s1 = WaitlistSignup(email="a@example.com")
        s2 = WaitlistSignup(email="b@example.com")
        db_session.add_all([s1, s2])
        db_session.commit()
        db_session.refresh(s1)
        db_session.refresh(s2)
        assert s1.id is not None
        assert s2.id is not None
        assert s2.id > s1.id, "autoincrement must produce monotonically increasing IDs"

    def test_duplicateEmail_raisesIntegrityError(self, db_session):
        s1 = WaitlistSignup(email="dupe@example.com", source="landing_page")
        db_session.add(s1)
        db_session.commit()
        s2 = WaitlistSignup(email="dupe@example.com", source="trendfy")
        db_session.add(s2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_customSource_persisted(self, db_session):
        signup = WaitlistSignup(email="tf@example.com", source="trendfy")
        db_session.add(signup)
        db_session.commit()
        db_session.refresh(signup)
        assert signup.source == "trendfy"

    def test_repr_containsEmailAndSource(self, db_session):
        signup = WaitlistSignup(email="repr@example.com", source="landing_page")
        db_session.add(signup)
        db_session.commit()
        r = repr(signup)
        assert "repr@example.com" in r
        assert "landing_page" in r
```

---

## 6. Commit Plan

Two commits — one for the schema (model + migration), one for tests.

1. `feat(waitlist): create WaitlistSignup model and Alembic migration` — `server/modules/waitlist/__init__.py`, `server/modules/waitlist/models.py`, `server/migrations/versions/20260417_create_waitlist_signups.py`: creates the module package, SQLAlchemy model with 4 columns (id, email, source, created_at), and migration with `idx_waitlist_source` index.
2. `test(waitlist): cover model defaults, unique email constraint, autoincrement` — `server/tests/test_waitlist_model.py`: 6 tests covering source default, created_at population, autoincrement, duplicate rejection, custom source, and repr.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with:
```
Deviations:
- <one line per deviation>
```

---

## 7. Verification

```bash
cd server && pytest -q
```

**Expected delta**: backend `N_b → N_b + 6` passing (6 model tests). Zero pre-existing tests broken. No frontend changes — frontend count unchanged.

---

## 8. Rollback

- **Per-step** (each commit is independently revertible):
  ```bash
  git revert <sha-of-commit-2>            # drop tests
  git revert <sha-of-commit-1>            # drop model + migration + module __init__
  cd server && alembic downgrade -1        # only if upgrade ran on your local DB
  ```
- **Per-branch** (if verification fails catastrophically):
  ```bash
  git reset --hard <pre-task-sha>          # [REQUIRES APPROVAL — discards all task work]
  ```
  Or delete the feature branch if one was created: `git branch -D <branch>` (local only, safe).

---

## 9. Deviations Allowed

- **`Base` import path differs from expected** → use whatever path `rg` discovers in Pre-flight (e.g., `from db import Base`, `from core.database import Base`, `from server.db import Base`); log in commit 1 body.
- **Current Alembic head is not the expected revision** → set `down_revision` to whatever `alembic heads` reports; log under `Deviations:`.
- **SQLite rejects `sa.func.now()` as server_default** → switch to `server_default=sa.text("(datetime('now'))")` for SQLite compatibility in tests; log under `Deviations:`.
- **`conftest.py` exposes `db_session` under a different fixture name** → adopt the existing fixture name (inspect `server/tests/conftest.py`); log under `Deviations:`.
- **`python_functions` pytest config collects bare test functions** → tests are already wrapped in `TestWaitlistSignup` class per the caveat; no deviation expected.
- **Existing `server/modules/waitlist/` directory already exists from a prior attempt** → inspect contents; if empty or stale, overwrite; if it contains real work, STOP and flag.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log under `Deviations:`.
- **Side effect required** (pushing, publishing, dropping existing tables, `rm -rf`) → STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task creates only the model and migration. It does NOT stand up the endpoint, wire the module into Flask, or move any data. Those are separate tasks with their own blast radii.

- **OpenAPI spec (`server/openapi/waitlist.yaml`)** — Task 2. Do not create or modify any YAML spec.
- **Pydantic DTOs (`server/modules/waitlist/dto.py`)** — Task 2. Do not generate DTOs.
- **Routes, service, repository (`routes.py`, `service.py`, `repository.py`)** — Task 3. Do not create any endpoint or business-logic files.
- **Module registration in `ENABLED_MODULES`** — Task 4. Do not modify `server/app.py`.
- **Trendfy data migration (`INSERT INTO waitlist_signups ... FROM bubls_subscribers`)** — Task 5. Do not read from or reference `bubls_subscribers`.
- **Deleting `email-api/`** — Task 6. Do not touch any files outside `server/modules/waitlist/`, `server/migrations/versions/`, and `server/tests/`.
- **Rate limiting** — Task 3 (routes layer). No rate-limit logic in the model.
- **Frontend changes** — no Angular, Ionic, or Capacitor work in this task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for table schema and integer PK.
- [Epic](./epic.md) — Task scope and dependency graph.
- [Timeline](./timeline.md) — Mark `In Progress` at Step 1, `Done` after commit 2 merges.

---

##### Post-generation review (auto)

**Overall**: 5/5 (gold)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 5/5 | Document type is task-spec (implementation guide), not Analysis/Epic/Architecture — standard section checklists don't directly apply |
| Content routing | 4/5 | §1 Context restates three design decisions (Integer PK vs UUID, index strategy, table naming) that belong in architecture.md — should cross-reference rather than restate rationale |
| Pattern application | 4/5 | Trade-offs in §1 are prose paragraphs — should be formalized as Decision Justification Tables (Option | Pros | Cons | Chosen) |
| Rule compliance | 5/5 | No violations detected |
| Content quality | 5/5 | Highly opinionated: integer PK chosen with clear rationale, not left as executor's choice |
| Usefulness | 5/5 | No significant gaps — a developer or Claude Code agent could implement directly from this spec |

**Top fixes**:
- Convert the three trade-off discussions in §1 Context into formal Decision Justification Tables (Option | Chosen | Rationale) — or replace them entirely with cross-references to specific sections in architecture.md to avoid content duplication
- Add a compact verification matrix at the end mapping each acceptance criterion to its verification command and expected output, enabling quick pass/fail scanning without re-reading full steps
- Ensure bidirectional cross-references: confirm architecture.md and epic.md link back to this task spec (not verifiable from this document alone — flag for pipeline-level check)
