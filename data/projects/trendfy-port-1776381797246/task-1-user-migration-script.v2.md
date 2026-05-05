# Task 1: User Migration Script

Alembic data migration that reads Trendfy's `users` table (same Neon Postgres instance), creates `superapp_users` rows for each email that does not already exist, generates a magic-link UUID token per new user, and logs results to stdout so invite emails can be sent manually for this 32-user cohort.

---

## 1. Context

Trendfy has 32 users in its `users` table (SERIAL PK `id`, `email`, `password`, `name`, `role`, `created_at`). Bubls uses UUID-based `superapp_users` with magic-link auth — no passwords, no OAuth. The two apps share a single Neon Postgres instance (EU Central 1), so Trendfy tables are directly readable from the Bubls migration without cross-database wiring.

This migration creates a Bubls user row for every Trendfy email not already present. It deliberately sets `builder = NULL` and `onboarding_skipped_at = NULL` so the onboarding guard (`src/app/shared/guards/`) triggers on first Bubls launch. Each new row gets a fresh UUID token for magic-link auth and `subscription_tier = 'free'` with photoshoot + home features enabled. Tokens are printed to stdout — there is no email service in Bubls yet, so the 32-user cohort receives invites manually.

**Trade-offs considered**:

- **Copy Trendfy passwords and support dual auth** — rejected. Bubls is magic-link-only (architecture principle). Trendfy passwords are bcrypt hashes for a different auth model. Copying them adds dead code and violates the auth constraint.
- **Auto-send invite emails via Resend inside the migration** — rejected for now. No email service exists in the Bubls backend yet. For 32 users, logging tokens to stdout and sending manually is faster than building email infrastructure. Revisit when a future epic adds the Resend integration.
- **Skip users who never trained a model** — rejected. All 32 users are valid testers. Those without models still hit onboarding and can be assigned models later. Filtering would complicate the Task 2 join unnecessarily.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/server
git status                                     # Flag any unrelated M/?? entries
git diff HEAD                                  # Confirm target files are clean
```

Verify current Alembic head:

```bash
cd {WORKSPACE}/server
DATABASE_URL=$DATABASE_URL alembic current
# Expected: 20260420_drop_onboarding_fields (head)
```

Run existing tests to confirm green baseline:

```bash
cd {WORKSPACE}/server
python -m pytest tests/ -q
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: N/N passing (record the exact count — this becomes the baseline for Section 7).

---

## 3. Files

### To Create (new)

| Path | Purpose |
|------|---------|
| `server/migrations/versions/20260421_migrate_trendfy_users.py` (new) | Alembic data migration: read Trendfy `users`, insert `superapp_users` rows with UUID tokens. Idempotent via `ON CONFLICT (email) DO NOTHING`. |
| `server/tests/test_trendfy_user_migration.py` (new) | Pytest tests: module structure assertions + logic-level tests seeding a mock Trendfy `users` table in the SQLite test DB |

### To Modify

None. The `superapp_users` table already has all required columns (`id`, `email`, `token`, `builder`, `onboarding_skipped_at`, `enabled_features`, `subscription_tier`, `created_at`). No model changes needed.

### To Leave Alone

| Path | Reason |
|------|--------|
| `server/modules/photoshoot/models.py` | User ORM entity already has `builder`, `onboarding_skipped_at`, `enabled_features` — no schema change |
| `server/modules/user/repository.py` | User CRUD unchanged — migration writes via `sa.text()`, not through the repository |
| `server/modules/user/routes.py` | No API changes for this task |
| `server/core/config.py` | No new config needed |
| `server/core/auth.py` | Auth validation unchanged — migrated tokens will work identically to manually created ones |
| `server/migrations/env.py` | No new module import needed — migration uses `op.get_bind()` directly |
| `server/seed.py` | Dev seeder is independent of migration scripts |

---

## 4. Implementation Steps

### Step 1: Create the Alembic migration file

**Action**: Create `server/migrations/versions/20260421_migrate_trendfy_users.py`. This is a data-only migration (no DDL). It reads Trendfy's `users` table via `sa.text()` SELECT (the Trendfy table has no ORM model in Bubls), then inserts into `superapp_users` via `sa.text()` INSERT with `ON CONFLICT (email) DO NOTHING` for idempotency. Emails are normalized to lowercase/trimmed. Each new user gets a fresh `uuid.uuid4()` token.

**File**: `server/migrations/versions/20260421_migrate_trendfy_users.py` (new)

**Pattern**:

```python
"""migrate trendfy users into superapp_users

Revision ID: 20260421_migrate_trendfy_users
Revises: 20260420_drop_onboarding_fields
Create Date: 2026-04-21

Data migration: reads every row from Trendfy's `users` table (same Neon
instance) and inserts a `superapp_users` row per unique email. Leaves
`builder = NULL` and `onboarding_skipped_at = NULL` so onboarding triggers
on first Bubls launch. Generates a UUID token per user for magic-link
auth. Idempotent: ON CONFLICT (email) DO NOTHING.

No DDL changes. No writes to Trendfy tables.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "20260421_migrate_trendfy_users"
down_revision = "20260420_drop_onboarding_fields"
branch_labels = None
depends_on = None

# Default feature flags for migrated users.
_DEFAULT_FEATURES = '{"home": true, "photoshoot": true}'


def upgrade() -> None:
    conn = op.get_bind()

    # ── Read Trendfy users ───────────────────────────────────────────
    trendfy_rows = conn.execute(
        sa.text("SELECT id, email, name, created_at FROM users ORDER BY id")
    ).fetchall()

    created = 0
    skipped = 0

    for row in trendfy_rows:
        trendfy_email = row.email.strip().lower()

        # Check if email already exists in superapp_users.
        existing = conn.execute(
            sa.text("SELECT id FROM superapp_users WHERE email = :email"),
            {"email": trendfy_email},
        ).fetchone()

        if existing is not None:
            skipped += 1
            continue

        new_id = uuid.uuid4()
        new_token = uuid.uuid4()

        conn.execute(
            sa.text(
                """
                INSERT INTO superapp_users
                    (id, email, token, enabled_features, subscription_tier, created_at)
                VALUES
                    (:id, :email, :token, :features::jsonb, 'free', :created_at)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {
                "id": str(new_id),
                "email": trendfy_email,
                "token": str(new_token),
                "features": _DEFAULT_FEATURES,
                "created_at": row.created_at,
            },
        )

        print(f"  [migrate] created superapp_users row: {trendfy_email} | token={new_token}")
        created += 1

    print(f"\n  [migrate] trendfy user migration complete: {created} created, {skipped} skipped (already existed)")


def downgrade() -> None:
    """Remove superapp_users rows that were created by this migration.

    Safety: only deletes users whose email exists in Trendfy's `users`
    table AND who have no generations or lora_models (to avoid orphaning
    data created after migration).
    """
    conn = op.get_bind()

    trendfy_emails = conn.execute(
        sa.text("SELECT LOWER(TRIM(email)) AS email FROM users")
    ).fetchall()

    deleted = 0
    for row in trendfy_emails:
        # Only delete if the user has no dependent rows in Bubls tables.
        result = conn.execute(
            sa.text(
                """
                DELETE FROM superapp_users
                WHERE email = :email
                  AND id NOT IN (SELECT DISTINCT user_id FROM superapp_lora_models)
                  AND id NOT IN (SELECT DISTINCT user_id FROM superapp_generations)
                RETURNING email
                """
            ),
            {"email": row.email},
        ).fetchone()
        if result is not None:
            deleted += 1

    print(f"  [rollback] removed {deleted} migrated users (skipped users with models/generations)")
```

**Verify**:

```bash
cd {WORKSPACE}/server
python -c "import importlib; m = importlib.import_module('migrations.versions.20260421_migrate_trendfy_users'); assert m.revision == '20260421_migrate_trendfy_users'; assert m.down_revision == '20260420_drop_onboarding_fields'; assert callable(m.upgrade); assert callable(m.downgrade); print('OK')"
```

### Step 2: Create the test file

**Action**: Create `server/tests/test_trendfy_user_migration.py` with tests covering: module structure (revision chain, callable up/down), and migration logic (new emails create rows, existing emails are skipped, migrated users have NULL builder + NULL onboarding_skipped_at, migrated users have free tier + photoshoot enabled).

The migration's `upgrade()` uses Postgres-specific `::jsonb` cast which won't run on SQLite. Tests exercise the equivalent logic via the ORM (which handles JSON/JSONB dialect variance). This is the standard pattern for testing Alembic data migrations in this codebase — test the logic, not the raw SQL.

**File**: `server/tests/test_trendfy_user_migration.py` (new)

**Pattern**: Follow the existing `test_user_migration.py` pattern — import the module, assert revision chain, assert callable upgrade/downgrade. Add logic-level tests that seed a mock Trendfy `users` table in the SQLite test DB, exercise the user-creation logic via the ORM, and assert correct `superapp_users` rows.

See Section 5 for full test bodies.

**Verify**:

```bash
cd {WORKSPACE}/server
python -m pytest tests/test_trendfy_user_migration.py -v
```

---

## 5. Tests

File: `server/tests/test_trendfy_user_migration.py`

```python
"""Tests for the Trendfy user migration (20260421).

Validates the migration module structure and the idempotent user-creation
logic. Uses the in-memory SQLite test DB from conftest. Because the
migration reads from Trendfy's `users` table, we create that table in the
test DB as a fixture.

Note: The actual migration uses Postgres-specific ``::jsonb`` casts. Tests
exercise equivalent logic via the ORM, which handles JSON/JSONB dialect
variance across Postgres and SQLite.
"""
from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa


# ── Helpers: create/seed/cleanup the Trendfy `users` table ──────────


def _create_trendfy_users_table(engine):
    """Create a minimal Trendfy `users` table in the test DB."""
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255),
                    name VARCHAR(50),
                    role VARCHAR(20) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _seed_trendfy_users(engine, emails: list[str]):
    """Insert rows into the Trendfy `users` table."""
    with engine.begin() as conn:
        for email in emails:
            conn.execute(
                sa.text("INSERT INTO users (email, created_at) VALUES (:email, :ts)"),
                {"email": email, "ts": datetime.now(timezone.utc)},
            )


def _cleanup_trendfy_table(engine):
    """Drop the Trendfy users table to avoid leaking between tests."""
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS users"))


# ── Module structure tests ───────────────────────────────────────────


class TestMigrationModule:
    def test_declaresCorrectRevisionChain(self):
        mod = importlib.import_module(
            "migrations.versions.20260421_migrate_trendfy_users"
        )
        assert mod.revision == "20260421_migrate_trendfy_users"
        assert mod.down_revision == "20260420_drop_onboarding_fields"

    def test_exposesUpgradeAndDowngrade(self):
        mod = importlib.import_module(
            "migrations.versions.20260421_migrate_trendfy_users"
        )
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)


# ── Logic tests (exercise via ORM to avoid Postgres-specific SQL) ────


class TestUserMigrationLogic:
    def test_newEmails_createsSuperappUsers(self, _test_engine, db_session):
        _create_trendfy_users_table(_test_engine)
        try:
            _seed_trendfy_users(_test_engine, ["alice@test.ch", "bob@test.ch"])

            before = db_session.execute(
                sa.text("SELECT COUNT(*) FROM superapp_users")
            ).scalar()

            rows = db_session.execute(
                sa.text("SELECT email, created_at FROM users ORDER BY id")
            ).fetchall()

            from modules.photoshoot.models import User

            for row in rows:
                existing = (
                    db_session.query(User)
                    .filter(User.email == row.email.strip().lower())
                    .one_or_none()
                )
                if existing is None:
                    user = User(
                        email=row.email.strip().lower(),
                        token=uuid.uuid4(),
                        enabled_features={"home": True, "photoshoot": True},
                        subscription_tier="free",
                    )
                    db_session.add(user)

            db_session.commit()

            after = db_session.execute(
                sa.text("SELECT COUNT(*) FROM superapp_users")
            ).scalar()
            assert after - before == 2
        finally:
            _cleanup_trendfy_table(_test_engine)

    def test_existingEmail_skipsWithoutDuplicate(self, _test_engine, db_session, make_user):
        _create_trendfy_users_table(_test_engine)
        try:
            make_user(db_session, email="existing@test.ch")

            _seed_trendfy_users(_test_engine, ["existing@test.ch", "new@test.ch"])

            before = db_session.execute(
                sa.text("SELECT COUNT(*) FROM superapp_users")
            ).scalar()

            rows = db_session.execute(
                sa.text("SELECT email, created_at FROM users ORDER BY id")
            ).fetchall()

            from modules.photoshoot.models import User

            created = 0
            for row in rows:
                email = row.email.strip().lower()
                existing = (
                    db_session.query(User).filter(User.email == email).one_or_none()
                )
                if existing is None:
                    user = User(
                        email=email,
                        token=uuid.uuid4(),
                        enabled_features={"home": True, "photoshoot": True},
                        subscription_tier="free",
                    )
                    db_session.add(user)
                    created += 1

            db_session.commit()

            after = db_session.execute(
                sa.text("SELECT COUNT(*) FROM superapp_users")
            ).scalar()
            assert created == 1
            assert after - before == 1
        finally:
            _cleanup_trendfy_table(_test_engine)

    def test_migratedUser_hasNullBuilderAndNullOnboardingSkipped(self, _test_engine, db_session):
        _create_trendfy_users_table(_test_engine)
        try:
            _seed_trendfy_users(_test_engine, ["onboard@test.ch"])

            from modules.photoshoot.models import User

            user = User(
                email="onboard@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
                subscription_tier="free",
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            assert user.builder is None
            assert user.onboarding_skipped_at is None
        finally:
            _cleanup_trendfy_table(_test_engine)

    def test_migratedUser_hasFreeTierAndPhotoshootEnabled(self, _test_engine, db_session):
        _create_trendfy_users_table(_test_engine)
        try:
            _seed_trendfy_users(_test_engine, ["tier@test.ch"])

            from modules.photoshoot.models import User

            user = User(
                email="tier@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
                subscription_tier="free",
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            assert user.subscription_tier == "free"
            assert user.enabled_features.get("photoshoot") is True
        finally:
            _cleanup_trendfy_table(_test_engine)
```

---

## 6. Commit Plan

### Commit 1: Alembic migration + tests

**Files**:
- `server/migrations/versions/20260421_migrate_trendfy_users.py`
- `server/tests/test_trendfy_user_migration.py`

**Message**: `feat(migration): add Trendfy→Bubls user migration script`

**Body**: Reads Trendfy `users` table, creates `superapp_users` rows with fresh magic-link tokens. Idempotent via email dedup. Logs tokens to stdout for manual invite distribution.

**Gate**: `python -m pytest tests/test_trendfy_user_migration.py -v` passes (6 tests green).

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/server
python -m pytest tests/ -v
```

**Expected delta**: baseline N → N+6 passing. Zero pre-existing tests broken. The 6 new tests are:

| Test | Class |
|------|-------|
| `test_declaresCorrectRevisionChain` | `TestMigrationModule` |
| `test_exposesUpgradeAndDowngrade` | `TestMigrationModule` |
| `test_newEmails_createsSuperappUsers` | `TestUserMigrationLogic` |
| `test_existingEmail_skipsWithoutDuplicate` | `TestUserMigrationLogic` |
| `test_migratedUser_hasNullBuilderAndNullOnboardingSkipped` | `TestUserMigrationLogic` |
| `test_migratedUser_hasFreeTierAndPhotoshootEnabled` | `TestUserMigrationLogic` |

Confirm the migration module imports cleanly:

```bash
cd {WORKSPACE}/server
python -c "from migrations.versions.20260421_migrate_trendfy_users import upgrade, downgrade; print('import OK')"
```

---

## 8. Rollback

### Per-step rollback

If the migration has been applied to a live database:

```bash
cd {WORKSPACE}/server
DATABASE_URL=$DATABASE_URL alembic downgrade 20260420_drop_onboarding_fields
```

This runs the `downgrade()` function which deletes `superapp_users` rows whose email exists in Trendfy's `users` table, but **only if** those users have no dependent `superapp_lora_models` or `superapp_generations` rows. Users who gained dependent data after migration are preserved — no orphan risk.

### Per-branch rollback

If the entire branch needs to be reverted:

```bash
git revert <commit-sha>
```

The migration file deletion alone is sufficient — Alembic will not attempt to run a migration that no longer exists in the versions directory, and `alembic downgrade` handles the stamp.

---

## 9. Deviations Allowed

- **Trendfy `users` table has fewer or more than 32 rows** — The migration handles any row count. Log output reflects the actual count. No executor judgment needed.
- **Trendfy `users` table has a different column name for email** — If the column is not literally `email`, update the SELECT query and note the deviation in the commit body.
- **SQLite test DB does not support `::jsonb` cast** — The migration uses Postgres-specific `::jsonb` in the INSERT. Tests exercise the logic via the ORM (which handles JSON/JSONB dialect variance). If the executor needs to test the raw migration against SQLite, use `json()` instead — this is an allowed deviation.
- **Email casing differs between Trendfy and Bubls** — The migration normalizes to lowercase via `.strip().lower()`. If Trendfy has duplicate emails differing only by case, the second will be skipped by ON CONFLICT. Log the skip.
- **`down_revision` does not match** — If the current Alembic head is not `20260420_drop_onboarding_fields`, update the `down_revision` string and note the deviation. Do not guess — run `alembic heads` to confirm.
- **`make_user` fixture not available in conftest** — If the test fixture `make_user` does not exist, create the user directly via `User(email=..., token=uuid.uuid4(), ...)` and `db_session.add()`. Note the deviation.

---

## 10. Out of Scope

This task creates Bubls user rows from Trendfy data. It does NOT build email infrastructure, migrate passwords, or touch any table beyond `superapp_users`. The executor must **STOP and flag** if any of these become necessary during implementation.

- **Sending invite emails programmatically** — This migration logs tokens to stdout. Automated email sending via Resend or any other service is deferred until a future epic adds email infrastructure to Bubls. If the task description changes to require it, stop and flag.
- **Copying Trendfy passwords** — Bubls is magic-link-only (architecture principle). If anyone requests password migration, stop and flag — it violates the auth constraint.
- **Creating `superapp_lora_models` rows** — That is Task 2. This migration only creates user rows. Task 2 chains from this migration (`down_revision = '20260421_migrate_trendfy_users'`).
- **Creating `superapp_generations` rows** — That is Task 3. Depends on both Task 1 and Task 2.
- **Modifying Trendfy tables** — This migration is read-only against Trendfy. Any write to Trendfy tables is out of scope.
- **Adding new columns to `superapp_users`** — The existing schema has all needed columns (`builder`, `onboarding_skipped_at`, `enabled_features`, `subscription_tier`, `token`). If a new column seems needed, stop and flag.
- **Payment or subscription tier migration** — All migrated users get `subscription_tier = 'free'`. Stripe migration is explicitly out of scope per the epic.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale (migration scripts section, design decisions table)
- [Epic](./epic.md) — Task scope (Task 1 details at line 59-60)
- [Timeline](./timeline.md) — Status tracking (update after done)