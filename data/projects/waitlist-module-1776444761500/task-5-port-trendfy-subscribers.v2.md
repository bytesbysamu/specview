# 🛠️ Task 5: Port Trendfy subscribers

**Purpose**: Create an Alembic data migration that reads all rows from `bubls_subscribers` (same Neon Postgres instance) and inserts them into `waitlist_signups` with `source='trendfy'`, skipping duplicates via `ON CONFLICT (email) DO NOTHING`, and logging ported vs skipped counts.

**Effort**: 30m

**Dependencies**: Task 1 (model + migration — `waitlist_signups` table must exist), Task 4 (module registration — Alembic must be aware of the waitlist migration chain)

**Parallel With**: Task 6 (delete `email-api/`)

**Blocks**: —

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Tasks 1–4 stood up the `waitlist_signups` table, the endpoint, and the module registration. This task completes the data story by porting every email in the existing `bubls_subscribers` table (Trendfy's signup table on the same Neon instance) into `waitlist_signups` with `source='trendfy'`. The migration is an Alembic data migration — no DDL, read-only against `bubls_subscribers`, write-only to `waitlist_signups`. `ON CONFLICT (email) DO NOTHING` makes it idempotent: if someone signed up via the landing page before the migration runs, their row is preserved untouched and the Trendfy duplicate is silently skipped. A `downgrade()` deletes only rows with `source='trendfy'`, leaving landing-page signups intact. The shape is ported directly from the Trendfy user migration pattern (`trendfy-port/task-1-user-migration-script.v2.md`) — same SELECT → loop → INSERT → log structure, simplified because `waitlist_signups` has fewer columns than `superapp_users`.

**Trade-offs considered**:
- **Standalone script in `server/scripts/`** — rejected. An Alembic migration runs exactly once, is tracked in version history, and executes in the normal deploy pipeline. A standalone script must be remembered and manually invoked.
- **Batch INSERT with a single `INSERT INTO ... SELECT FROM`** — rejected. The row-by-row loop lets us normalize emails (`.strip().lower()`), preserve `created_at` from the source, and log individual skips. For the small volume expected in `bubls_subscribers` (dozens, not millions), the per-row approach is clearer and the performance difference is negligible.
- **Alembic data migration with per-row loop and logging** — chosen. Matches the proven pattern from the Trendfy port (task-1-user-migration-script.v2.md), idempotent, auditable via stdout.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/server
git status                                                 # Flag any unrelated M/?? entries
git diff HEAD -- server/migrations/ server/tests/          # Confirm target area clean
git log -1 --format=%H                                     # Record pre-task SHA for §8 rollback
```

Discover current Alembic head (should be the Task 1 migration or later):

```bash
cd {WORKSPACE}/server
alembic heads 2>&1                                         # Record head revision ID for down_revision
```

Confirm `waitlist_signups` table exists (Task 1 deliverable):

```bash
cd {WORKSPACE}/server
python -c "
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ['DATABASE_URL'])
tables = inspect(engine).get_table_names()
assert 'waitlist_signups' in tables, f'waitlist_signups missing — Task 1 not applied. Tables: {tables}'
print('OK: waitlist_signups exists')
"
```

Confirm `bubls_subscribers` table exists and inspect its schema:

```bash
cd {WORKSPACE}/server
python -c "
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ['DATABASE_URL'])
cols = inspect(engine).get_columns('bubls_subscribers')
print([c['name'] for c in cols])
"
# Expected columns include at least: email, created_at
```

Baseline test count:

```bash
cd {WORKSPACE}/server
pytest -q 2>&1 | tail -3                                   # Record backend "N passed" as N_b
```

**If working tree is dirty on target files**: stash or commit unrelated changes on a separate branch BEFORE starting.

**Baseline recorded**: capture backend count `[N_b]` — goes into commit bodies.

---

## 3. Files

### To Create (new)
- `server/migrations/versions/20260417_port_trendfy_subscribers.py` (new) — Alembic data migration: read `bubls_subscribers`, insert into `waitlist_signups` with `source='trendfy'`. Idempotent via `ON CONFLICT (email) DO NOTHING`. Ported from `trendfy-port/task-1-user-migration-script.v2.md` shape.
- `server/tests/test_port_trendfy_subscribers.py` (new) — Pytest tests: module structure assertions + logic-level tests seeding a mock `bubls_subscribers` table in the SQLite test DB.

### To Modify
- None — this task only creates new files.

### To Leave Alone
- `server/modules/waitlist/models.py` — Task 1 deliverable. Do not modify.
- `server/modules/waitlist/routes.py` — Task 3 deliverable. Do not modify.
- `server/modules/waitlist/service.py` — Task 3 deliverable. Do not modify.
- `server/modules/waitlist/repository.py` — Task 3 deliverable. Do not modify.
- `server/modules/waitlist/dto.py` — Task 2 deliverable. Do not modify.
- `server/modules/waitlist/__init__.py` — Task 1 deliverable. Do not modify.
- `server/app.py` — Task 4 deliverable. Do not modify.
- `server/migrations/versions/20260417_create_waitlist_signups.py` — Task 1 migration. Never edit past migrations.
- `server/modules/photoshoot/**` — unrelated feature module.
- `server/modules/user/**` — unrelated feature module.
- `server/modules/chain/**` — unrelated infrastructure module.
- All frontend files (`src/app/**`) — no frontend changes in this task.

---

## 4. Implementation Steps

### Step 1: Discover current Alembic head and `bubls_subscribers` schema

**Action**: Execute the discovery commands from §2. Record: (a) the current Alembic head revision ID string (expected to be the Task 4 migration or the Task 1 migration `20260417_create_waitlist_signups`), (b) the column names in `bubls_subscribers` (expected at minimum: `email`, `created_at`).

**File**: read-only (no edits).

**Pattern**: (discovery only — informs Step 2).

**Verify**: both values recorded. If `bubls_subscribers` does not exist in the database, STOP and flag — the source table is required.

### Step 2: Create the Alembic data migration

**Action**: Create the data migration file. Set `down_revision` to the head revision discovered in Step 1. The migration reads every row from `bubls_subscribers` via `sa.text()` SELECT (read-only cross-table access — the caveats allow `sa.text()` SELECT for this), normalizes email to lowercase/trimmed, and inserts into `waitlist_signups` with `source='trendfy'` and `ON CONFLICT (email) DO NOTHING`. Logs ported and skipped counts to stdout. Ported from `trendfy-port/task-1-user-migration-script.v2.md:121-170` — same SELECT → loop → INSERT → log shape, simplified for 3-column target.

**File**: `server/migrations/versions/20260417_port_trendfy_subscribers.py` (new)

**Pattern**:

```python
"""port trendfy subscribers into waitlist_signups

Revision ID: 20260417_port_trendfy_subscribers
Revises: {CURRENT_HEAD}
Create Date: 2026-04-17

Data migration: reads every row from `bubls_subscribers` (same Neon instance)
and inserts a `waitlist_signups` row per unique email with source='trendfy'.
Preserves original created_at. Idempotent: ON CONFLICT (email) DO NOTHING.

No DDL changes. No writes to bubls_subscribers.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260417_port_trendfy_subscribers"
down_revision = "{CURRENT_HEAD}"  # discovered in Step 1
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Read Trendfy subscribers ────────────────────────────────────
    rows = conn.execute(
        sa.text("SELECT email, created_at FROM bubls_subscribers ORDER BY id")
    ).fetchall()

    ported = 0
    skipped = 0

    for row in rows:
        email = row.email.strip().lower()

        result = conn.execute(
            sa.text(
                """
                INSERT INTO waitlist_signups (email, source, created_at)
                VALUES (:email, 'trendfy', :created_at)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
                """
            ),
            {"email": email, "created_at": row.created_at},
        ).fetchone()

        if result is not None:
            ported += 1
            print(f"  [port] {email} -> waitlist_signups (id={result.id})")
        else:
            skipped += 1
            print(f"  [port] {email} skipped (already exists)")

    print(f"\n  [port] trendfy subscriber port complete: {ported} ported, {skipped} skipped")


def downgrade() -> None:
    """Remove waitlist_signups rows ported from trendfy.

    Only deletes rows with source='trendfy'. Landing-page signups are
    untouched.
    """
    conn = op.get_bind()
    result = conn.execute(
        sa.text("DELETE FROM waitlist_signups WHERE source = 'trendfy' RETURNING email")
    ).fetchall()
    print(f"  [rollback] removed {len(result)} trendfy-ported rows from waitlist_signups")
```

Replace `{CURRENT_HEAD}` with the actual Alembic head from Step 1.

**Verify**:

```bash
cd {WORKSPACE}/server
python -c "
import importlib
m = importlib.import_module('migrations.versions.20260417_port_trendfy_subscribers')
assert m.revision == '20260417_port_trendfy_subscribers'
assert callable(m.upgrade)
assert callable(m.downgrade)
print('OK: migration module imports cleanly')
"
```

### Step 3: Write tests

**Action**: Create `server/tests/test_port_trendfy_subscribers.py` with module structure assertions and logic-level tests. The migration uses Postgres-specific SQL, so logic tests exercise the equivalent behavior via direct SQLAlchemy operations against the SQLite test DB (same pattern as `trendfy-port/task-1-user-migration-script.v2.md:239-446`). Tests create a temporary `bubls_subscribers` table in the test DB, seed it, exercise the port logic, and clean up.

**File**: `server/tests/test_port_trendfy_subscribers.py` (new)

**Pattern**: See §5 for full assertion bodies.

**Verify**:

```bash
cd {WORKSPACE}/server
pytest tests/test_port_trendfy_subscribers.py -v
# expect: 7 tests passing
```

### Step 4: Run full backend suite

**Action**: Execute the complete pytest suite to confirm zero regressions.

**Verify**:

```bash
cd {WORKSPACE}/server
pytest -q
# expect: N_b + 7 passing, 0 failures introduced
```

---

## 5. Tests

Pytest, SQLAlchemy SQLite fixtures from `server/tests/conftest.py`. Names follow the repo's `condition_expectedOutcome` convention (no "should"). All tests wrapped in classes to avoid the `python_functions = ["*_*"]` caveat. Ported from `trendfy-port/task-1-user-migration-script.v2.md:239-446` — same mock-table-in-SQLite pattern, adapted for `waitlist_signups` target.

```python
# server/tests/test_port_trendfy_subscribers.py
"""Tests for the Trendfy subscriber port migration.

Validates the migration module structure and the idempotent port logic.
Uses the in-memory SQLite test DB from conftest. Because the migration
reads from `bubls_subscribers`, we create that table in the test DB as
a fixture.

Note: The actual migration uses Postgres-specific ON CONFLICT ... RETURNING.
Tests exercise equivalent logic via the WaitlistSignup ORM model, which
handles dialect variance across Postgres and SQLite.
"""
from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from modules.waitlist.models import WaitlistSignup


# ── Helpers: create/seed/cleanup the mock bubls_subscribers table ─────


def _create_bubls_subscribers_table(engine):
    """Create a minimal bubls_subscribers table in the test DB."""
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS bubls_subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    city VARCHAR(100),
                    token VARCHAR(36),
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _seed_bubls_subscribers(engine, emails: list[str]):
    """Insert rows into the mock bubls_subscribers table."""
    with engine.begin() as conn:
        for email in emails:
            conn.execute(
                sa.text(
                    "INSERT INTO bubls_subscribers (email, created_at) VALUES (:email, :ts)"
                ),
                {"email": email, "ts": datetime.now(timezone.utc)},
            )


def _cleanup_bubls_subscribers(engine):
    """Drop the mock bubls_subscribers table to avoid leaking between tests."""
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS bubls_subscribers"))


# ── Module structure tests ────────────────────────────────────────────


class TestMigrationModule:
    def test_declaresCorrectRevision(self):
        mod = importlib.import_module(
            "migrations.versions.20260417_port_trendfy_subscribers"
        )
        assert mod.revision == "20260417_port_trendfy_subscribers"

    def test_exposesUpgradeAndDowngrade(self):
        mod = importlib.import_module(
            "migrations.versions.20260417_port_trendfy_subscribers"
        )
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)


# ── Logic tests (exercise via ORM to avoid Postgres-specific SQL) ─────


class TestPortLogic:
    def test_newEmails_insertedWithSourceTrendfy(self, _test_engine, db_session):
        _create_bubls_subscribers_table(_test_engine)
        try:
            _seed_bubls_subscribers(
                _test_engine, ["alice@trendfy.ch", "bob@trendfy.ch"]
            )

            rows = db_session.execute(
                sa.text("SELECT email, created_at FROM bubls_subscribers ORDER BY id")
            ).fetchall()

            for row in rows:
                email = row.email.strip().lower()
                existing = (
                    db_session.query(WaitlistSignup)
                    .filter(WaitlistSignup.email == email)
                    .one_or_none()
                )
                if existing is None:
                    signup = WaitlistSignup(
                        email=email, source="trendfy", created_at=row.created_at
                    )
                    db_session.add(signup)

            db_session.commit()

            results = (
                db_session.query(WaitlistSignup)
                .filter(WaitlistSignup.source == "trendfy")
                .all()
            )
            assert len(results) == 2
            assert {r.email for r in results} == {"alice@trendfy.ch", "bob@trendfy.ch"}
        finally:
            _cleanup_bubls_subscribers(_test_engine)

    def test_existingEmail_skippedWithoutDuplicate(self, _test_engine, db_session):
        _create_bubls_subscribers_table(_test_engine)
        try:
            # Pre-existing landing page signup
            existing = WaitlistSignup(
                email="overlap@test.ch", source="landing_page"
            )
            db_session.add(existing)
            db_session.commit()

            _seed_bubls_subscribers(
                _test_engine, ["overlap@test.ch", "fresh@trendfy.ch"]
            )

            rows = db_session.execute(
                sa.text("SELECT email, created_at FROM bubls_subscribers ORDER BY id")
            ).fetchall()

            ported = 0
            for row in rows:
                email = row.email.strip().lower()
                exists = (
                    db_session.query(WaitlistSignup)
                    .filter(WaitlistSignup.email == email)
                    .one_or_none()
                )
                if exists is None:
                    signup = WaitlistSignup(
                        email=email, source="trendfy", created_at=row.created_at
                    )
                    db_session.add(signup)
                    ported += 1

            db_session.commit()

            assert ported == 1, "only fresh@trendfy.ch should be ported"
            overlap_row = (
                db_session.query(WaitlistSignup)
                .filter(WaitlistSignup.email == "overlap@test.ch")
                .one()
            )
            assert overlap_row.source == "landing_page", (
                "existing landing_page signup must not be overwritten"
            )
        finally:
            _cleanup_bubls_subscribers(_test_engine)

    def test_emailNormalized_toLowercaseTrimmed(self, _test_engine, db_session):
        _create_bubls_subscribers_table(_test_engine)
        try:
            _seed_bubls_subscribers(_test_engine, ["  Alice@Trendfy.CH  "])

            rows = db_session.execute(
                sa.text("SELECT email, created_at FROM bubls_subscribers ORDER BY id")
            ).fetchall()

            for row in rows:
                email = row.email.strip().lower()
                signup = WaitlistSignup(
                    email=email, source="trendfy", created_at=row.created_at
                )
                db_session.add(signup)

            db_session.commit()

            result = db_session.query(WaitlistSignup).filter(
                WaitlistSignup.source == "trendfy"
            ).one()
            assert result.email == "alice@trendfy.ch", (
                "email must be lowercased and trimmed"
            )
        finally:
            _cleanup_bubls_subscribers(_test_engine)

    def test_createdAtPreservedFromSource(self, _test_engine, db_session):
        _create_bubls_subscribers_table(_test_engine)
        try:
            original_ts = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
            with _test_engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "INSERT INTO bubls_subscribers (email, created_at) VALUES (:email, :ts)"
                    ),
                    {"email": "dated@trendfy.ch", "ts": original_ts},
                )

            rows = db_session.execute(
                sa.text("SELECT email, created_at FROM bubls_subscribers ORDER BY id")
            ).fetchall()

            for row in rows:
                signup = WaitlistSignup(
                    email=row.email.strip().lower(),
                    source="trendfy",
                    created_at=row.created_at,
                )
                db_session.add(signup)

            db_session.commit()

            result = db_session.query(WaitlistSignup).filter(
                WaitlistSignup.email == "dated@trendfy.ch"
            ).one()
            assert result.created_at is not None, "created_at must be preserved from source"
        finally:
            _cleanup_bubls_subscribers(_test_engine)

    def test_downgradeLogic_removesOnlyTrendfyRows(self, _test_engine, db_session):
        """Simulates downgrade: delete WHERE source='trendfy'."""
        landing = WaitlistSignup(email="keep@landing.ch", source="landing_page")
        trendfy = WaitlistSignup(email="remove@trendfy.ch", source="trendfy")
        db_session.add_all([landing, trendfy])
        db_session.commit()

        db_session.query(WaitlistSignup).filter(
            WaitlistSignup.source == "trendfy"
        ).delete()
        db_session.commit()

        remaining = db_session.query(WaitlistSignup).all()
        assert len(remaining) == 1
        assert remaining[0].email == "keep@landing.ch"
        assert remaining[0].source == "landing_page"
```

---

## 6. Commit Plan

One commit — migration + tests are one logical unit (the migration has no value without its tests, and the tests have no value without the migration).

1. `feat(waitlist): port trendfy subscribers via Alembic data migration` — `server/migrations/versions/20260417_port_trendfy_subscribers.py`, `server/tests/test_port_trendfy_subscribers.py`: reads `bubls_subscribers`, inserts into `waitlist_signups` with `source='trendfy'`, idempotent via ON CONFLICT. 7 tests covering module structure, port logic, email normalization, timestamp preservation, and downgrade safety.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with:
```
Deviations:
- <one line per deviation>
```

---

## 7. Verification

```bash
cd {WORKSPACE}/server
pytest -q
```

**Expected delta**: backend `N_b → N_b + 7` passing (2 module structure + 5 logic tests). Zero pre-existing tests broken.

Confirm the migration module imports cleanly:

```bash
cd {WORKSPACE}/server
python -c "from migrations.versions.20260417_port_trendfy_subscribers import upgrade, downgrade; print('import OK')"
```

If running against the real Neon database (post-deploy verification):

```bash
cd {WORKSPACE}/server
DATABASE_URL=$DATABASE_URL alembic upgrade head
# expect: stdout shows "[port] <email> -> waitlist_signups" lines and final summary
```

Then verify the rows landed:

```bash
cd {WORKSPACE}/server
python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    total = conn.execute(text(\"SELECT COUNT(*) FROM waitlist_signups WHERE source = 'trendfy'\")).scalar()
    print(f'trendfy rows in waitlist_signups: {total}')
"
```

---

## 8. Rollback

- **Per-step** (revert the one commit):
  ```bash
  git revert <sha-of-commit>
  ```
  If the migration was already applied to the database:
  ```bash
  cd {WORKSPACE}/server
  DATABASE_URL=$DATABASE_URL alembic downgrade -1    # runs downgrade() — deletes source='trendfy' rows only
  ```
- **Per-branch** (if verification fails catastrophically):
  ```bash
  git reset --hard <pre-task-sha>    # [REQUIRES APPROVAL — discards all task work]
  ```
  Plus `alembic downgrade -1` if the migration was applied.

---

## 9. Deviations Allowed

- **`bubls_subscribers` table has different column names** — If the table doesn't have a column literally named `email` or `created_at`, update the SELECT query to match the actual column names. Log the actual schema in the commit body under `Deviations:`.
- **`bubls_subscribers` table does not exist** — STOP and flag. The source table is a prerequisite. Do not create it, do not invent test data.
- **Current Alembic head is not the expected revision** — Set `down_revision` to whatever `alembic heads` reports; log under `Deviations:`. Do not guess.
- **`_test_engine` fixture not available in conftest** — Check if the fixture is named differently (e.g., `engine`, `test_engine`, `db_engine`). Adopt the existing fixture name; log under `Deviations:`.
- **`db_session` fixture not available or named differently** — Inspect `server/tests/conftest.py` for the actual session fixture name. Adopt it; log under `Deviations:`.
- **SQLite test DB cannot create `bubls_subscribers` table** — If conftest creates an isolated schema, create the table within the test's own connection. The helper functions already handle this via `_create_bubls_subscribers_table`.
- **Migration date conflicts with Task 1 migration filename** — If both use `20260417_` prefix, differentiate with the suffix (Task 1 is `_create_waitlist_signups`, this task is `_port_trendfy_subscribers`). Alembic distinguishes by revision ID, not filename date.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log deviation in the commit.
- **Side effect required** (pushing, applying migration to production, dropping tables) → STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task creates a one-time data migration that copies emails from `bubls_subscribers` to `waitlist_signups`. It does NOT modify the source table, build email infrastructure, or change any endpoint behavior.

- **Writing to `bubls_subscribers`** — This migration is read-only against the source table. If data cleanup is needed in `bubls_subscribers`, that's a separate task.
- **Deleting `email-api/`** — Task 6. Do not touch any files outside `server/migrations/versions/` and `server/tests/`.
- **Sending welcome/notification emails to ported subscribers** — No email service exists in the waitlist module. Manual process for now.
- **Porting `city`, `interests`, `token`, or `active` fields** — `waitlist_signups` only has `email`, `source`, `created_at`. Richer subscriber data is not in scope for the waitlist funnel. If a future task needs these fields, it should add columns via a new migration.
- **Frontend changes** — No Angular, Ionic, or Capacitor work in this task.
- **Modifying `server/app.py` or any module registration** — Task 4 deliverable. Do not touch.
- **Running the migration against production** — The executor creates the migration file and tests. Applying to production happens via the normal deploy pipeline and is outside this task's blast radius. `[REQUIRES APPROVAL]` if the executor is tempted to run `alembic upgrade head` against the production DATABASE_URL.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for Alembic data migration approach and `source` column strategy.
- [Epic](./epic.md) — Task scope (Task 5 at line 102-107).
- [Timeline](./timeline.md) — Mark `In Progress` at Step 1, `Done` after commit merges.

---

##### Post-generation review (auto)

_Review returned non-structured output:_

Error: Claude exited with code 1
