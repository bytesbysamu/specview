# Task 2: Model Migration Script

Alembic data migration that reads Trendfy's `models` table (7 rows with real Replicate model IDs), creates `superapp_lora_models` rows in Bubls linked to the corresponding `superapp_users` created in Task 1.

---

## 1. Context

Trendfy's `models` table has rows for 7 users with real trained LoRA models on Replicate: Sam v1, Sam v2, Sam v3a, Milky, Serina, Isabell, and Lea. The table uses SERIAL integer PKs and stores the Replicate version string in `replicate_version`. Bubls uses UUID PKs and stores the same string in `replicate_model_id`.

This migration maps each Trendfy model to its owner's `superapp_users` row (matched by email via the Trendfy `users` table) and creates a `superapp_lora_models` row. For users with multiple models (Sam has 3), the most recently created model is marked as the one returned by `find_active_lora_for_user()` -- which already sorts by `created_at DESC` and returns the first row. No `is_active` column exists or is needed; the repository's ordering convention handles it.

### Trade-offs considered

- **Add an `is_active` boolean column to `superapp_lora_models`** -- rejected. The existing repository function `find_active_lora_for_user()` already returns the most recent model by `created_at DESC`. Adding a column would require a DDL migration, a model change, and updating the repository. The ordering convention is sufficient for 7 models across 7 users (max 3 per user).
- **Copy all Trendfy models including those without a Replicate version** -- rejected. Models without `replicate_version` are incomplete training attempts that cannot generate images. Migrating them would create unusable rows and confuse the UI.
- **Use the `MODELS` dict in `core/config.py` instead of reading from Trendfy's DB** -- rejected. The config dict maps friendly names to version strings, but lacks per-user ownership and `created_at` timestamps. The Trendfy `models` table is the authoritative source for who owns which model.

---

## 2. Pre-flight

Before writing any code, the executor must record baseline state:

```bash
cd /projects/bubls/server
git status
git diff HEAD
```

Verify current Alembic head (should include Task 1 if already applied, or the prior head):

```bash
cd /projects/bubls/server
DATABASE_URL=$DATABASE_URL alembic current
```

The `down_revision` for this migration is `20260421_migrate_trendfy_users` (Task 1). If Task 1 has not been merged yet, this migration can still be written -- it chains correctly in the revision graph and will apply after Task 1.

Run existing tests to confirm green baseline:

```bash
cd /projects/bubls/server
python -m pytest tests/ -q
```

Record the test count.

---

## 3. Files

### To Create

| Path | Purpose |
|------|---------|
| `server/migrations/versions/20260422_migrate_trendfy_models.py` | Alembic data migration: read Trendfy `models` where `replicate_version IS NOT NULL`, insert `superapp_lora_models` |
| `server/tests/test_trendfy_model_migration.py` | Pytest tests for the migration module and logic |

### To Modify

None. The `superapp_lora_models` table already has all required columns (`replicate_model_id`, `trigger_word`, `default_style_prompt`, `created_at`). No ORM model changes needed.

### To Leave Alone

| Path | Reason |
|------|--------|
| `server/modules/photoshoot/models.py` | LoraModel ORM entity already matches the target schema |
| `server/modules/photoshoot/repository.py` | `find_active_lora_for_user()` already returns most recent by `created_at` -- no change needed |
| `server/core/config.py` | The `MODELS` dict is for inference config, not for migration source data |
| `server/seed.py` | Dev seeder is independent of migration scripts |
| `server/migrations/env.py` | No new module import needed |

---

## 4. Implementation Steps

### Step 1: Create the Alembic migration file

**Action**: Create `server/migrations/versions/20260422_migrate_trendfy_models.py`.

**File**: `server/migrations/versions/20260422_migrate_trendfy_models.py`

**Pattern**: Data migration (no DDL). Read Trendfy `models` joined to `users` for email, look up the `superapp_users` row by email, insert a `superapp_lora_models` row. Skip if a model with the same `replicate_model_id` already exists for that user (idempotent). Preserve the original `created_at` timestamp so that `find_active_lora_for_user()` ordering reflects the real training date.

```python
"""migrate trendfy lora models into superapp_lora_models

Revision ID: 20260422_migrate_trendfy_models
Revises: 20260421_migrate_trendfy_users
Create Date: 2026-04-22

Data migration: reads Trendfy's `models` table (7 rows with real
Replicate version strings), joins to `users` for email, looks up the
matching `superapp_users` row, and inserts a `superapp_lora_models`
row per model. Idempotent: skips if a row with the same
`replicate_model_id` + `user_id` already exists.

No DDL changes. No writes to Trendfy tables.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "20260422_migrate_trendfy_models"
down_revision = "20260421_migrate_trendfy_users"
branch_labels = None
depends_on = None

# Trendfy's default trigger word (same as TRIGGER_WORD_DEFAULT in config).
_TRIGGER_WORD_FALLBACK = "WRDRB1PERSON"
_DEFAULT_STYLE_PROMPT = "professional portrait, cinematic lighting"


def upgrade() -> None:
    conn = op.get_bind()

    # ── Read Trendfy models with real Replicate versions ─────────────
    trendfy_models = conn.execute(
        sa.text(
            """
            SELECT m.id, m.user_id, m.name, m.replicate_version,
                   m.trigger_word, m.created_at, u.email
            FROM models m
            JOIN users u ON m.user_id = u.id
            WHERE m.replicate_version IS NOT NULL
              AND m.replicate_version != ''
            ORDER BY m.created_at ASC
            """
        )
    ).fetchall()

    migrated = 0
    skipped = 0
    users_with_models = set()

    for row in trendfy_models:
        trendfy_email = row.email.strip().lower()

        # Look up the Bubls user by email.
        bubls_user = conn.execute(
            sa.text("SELECT id FROM superapp_users WHERE email = :email"),
            {"email": trendfy_email},
        ).fetchone()

        if bubls_user is None:
            print(f"  [migrate] WARN: no superapp_users row for {trendfy_email} -- skipping model {row.name}")
            skipped += 1
            continue

        bubls_user_id = bubls_user.id

        # Check if this exact model already exists for this user.
        existing = conn.execute(
            sa.text(
                """
                SELECT id FROM superapp_lora_models
                WHERE user_id = :user_id
                  AND replicate_model_id = :replicate_model_id
                """
            ),
            {"user_id": str(bubls_user_id), "replicate_model_id": row.replicate_version},
        ).fetchone()

        if existing is not None:
            skipped += 1
            continue

        new_id = uuid.uuid4()
        trigger_word = row.trigger_word if row.trigger_word else _TRIGGER_WORD_FALLBACK

        conn.execute(
            sa.text(
                """
                INSERT INTO superapp_lora_models
                    (id, user_id, replicate_model_id, trigger_word, default_style_prompt, created_at)
                VALUES
                    (:id, :user_id, :replicate_model_id, :trigger_word, :style, :created_at)
                """
            ),
            {
                "id": str(new_id),
                "user_id": str(bubls_user_id),
                "replicate_model_id": row.replicate_version,
                "trigger_word": trigger_word,
                "style": _DEFAULT_STYLE_PROMPT,
                "created_at": row.created_at,
            },
        )

        users_with_models.add(trendfy_email)
        print(f"  [migrate] model '{row.name}' ({row.replicate_version[:40]}...) -> user {trendfy_email}")
        migrated += 1

    print(f"\n  [migrate] trendfy model migration complete: {migrated} models migrated, {skipped} skipped, {len(users_with_models)} users with models")


def downgrade() -> None:
    """Remove superapp_lora_models rows whose replicate_model_id matches
    a Trendfy model's replicate_version.

    Only deletes models that have no dependent superapp_generations rows
    to avoid orphaning generation history.
    """
    conn = op.get_bind()

    trendfy_versions = conn.execute(
        sa.text(
            """
            SELECT replicate_version FROM models
            WHERE replicate_version IS NOT NULL AND replicate_version != ''
            """
        )
    ).fetchall()

    deleted = 0
    for row in trendfy_versions:
        result = conn.execute(
            sa.text(
                """
                DELETE FROM superapp_lora_models
                WHERE replicate_model_id = :version
                  AND id NOT IN (SELECT DISTINCT lora_model_id FROM superapp_generations WHERE lora_model_id IS NOT NULL)
                RETURNING id
                """
            ),
            {"version": row.replicate_version},
        ).fetchone()
        if result is not None:
            deleted += 1

    print(f"  [rollback] removed {deleted} migrated lora models (skipped models with generations)")
```

**Verify**:

```bash
cd /projects/bubls/server
python -c "import importlib; m = importlib.import_module('migrations.versions.20260422_migrate_trendfy_models'); assert m.revision == '20260422_migrate_trendfy_models'; assert m.down_revision == '20260421_migrate_trendfy_users'; print('OK')"
```

### Step 2: Create the test file

**Action**: Create `server/tests/test_trendfy_model_migration.py`.

**File**: `server/tests/test_trendfy_model_migration.py`

**Pattern**: Create Trendfy `users` and `models` tables in the SQLite test DB as fixtures. Seed with known data. Exercise the migration logic via the ORM. Assert correct `superapp_lora_models` rows appear.

See Section 5 for full test bodies.

**Verify**:

```bash
cd /projects/bubls/server
python -m pytest tests/test_trendfy_model_migration.py -v
```

---

## 5. Tests

File: `server/tests/test_trendfy_model_migration.py`

```python
"""Tests for the Trendfy model migration (20260422).

Validates migration module structure and the model-mapping logic.
Creates Trendfy `users` + `models` tables in the SQLite test DB as
fixtures, seeds them, and verifies correct `superapp_lora_models` rows.
"""
from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from modules.photoshoot.models import LoraModel, User


def _create_trendfy_tables(engine):
    """Create minimal Trendfy `users` + `models` tables."""
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
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    replicate_version VARCHAR(512),
                    trigger_word VARCHAR(100),
                    status VARCHAR(20) NOT NULL DEFAULT 'ready',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                )
                """
            )
        )


def _cleanup_trendfy_tables(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS models"))
        conn.execute(sa.text("DROP TABLE IF EXISTS users"))


def _seed_trendfy_user(engine, email: str) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            sa.text("INSERT INTO users (email, created_at) VALUES (:email, :ts)"),
            {"email": email, "ts": datetime.now(timezone.utc)},
        )
        return result.lastrowid


def _seed_trendfy_model(engine, user_id: int, name: str, replicate_version: str | None, trigger_word: str = "TOK", created_at: datetime | None = None):
    ts = created_at or datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO models (user_id, name, replicate_version, trigger_word, created_at) VALUES (:uid, :name, :rv, :tw, :ts)"
            ),
            {"uid": user_id, "name": name, "rv": replicate_version, "tw": trigger_word, "ts": ts},
        )


class TestMigrationModule:
    def migration_declaresCorrectRevisionChain(self):
        mod = importlib.import_module(
            "migrations.versions.20260422_migrate_trendfy_models"
        )
        assert mod.revision == "20260422_migrate_trendfy_models"
        assert mod.down_revision == "20260421_migrate_trendfy_users"

    def migration_exposesUpgradeAndDowngrade(self):
        mod = importlib.import_module(
            "migrations.versions.20260422_migrate_trendfy_models"
        )
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)


class TestModelMigrationLogic:
    def realModels_createsSuperappLoraModels(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            # Seed Trendfy user + model.
            tid = _seed_trendfy_user(_test_engine, "milky@test.ch")
            _seed_trendfy_model(_test_engine, tid, "milky-v1", "bytesbysamu/milky-v1:abc123", "WRDRB1PERSON")

            # Create corresponding Bubls user.
            bubls_user = User(
                email="milky@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
            )
            db_session.add(bubls_user)
            db_session.commit()
            db_session.refresh(bubls_user)

            # Simulate migration logic.
            trendfy_rows = db_session.execute(
                sa.text(
                    """
                    SELECT m.name, m.replicate_version, m.trigger_word, m.created_at, u.email
                    FROM models m JOIN users u ON m.user_id = u.id
                    WHERE m.replicate_version IS NOT NULL AND m.replicate_version != ''
                    """
                )
            ).fetchall()

            for row in trendfy_rows:
                target_user = db_session.query(User).filter(User.email == row.email.strip().lower()).one_or_none()
                if target_user is None:
                    continue
                lora = LoraModel(
                    user_id=target_user.id,
                    replicate_model_id=row.replicate_version,
                    trigger_word=row.trigger_word or "WRDRB1PERSON",
                    default_style_prompt="professional portrait, cinematic lighting",
                )
                db_session.add(lora)

            db_session.commit()

            models = db_session.query(LoraModel).filter(LoraModel.user_id == bubls_user.id).all()
            assert len(models) == 1
            assert models[0].replicate_model_id == "bytesbysamu/milky-v1:abc123"
            assert models[0].trigger_word == "WRDRB1PERSON"
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def nullReplicateVersion_skipped(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            tid = _seed_trendfy_user(_test_engine, "nomodel@test.ch")
            _seed_trendfy_model(_test_engine, tid, "failed-training", None)

            bubls_user = User(
                email="nomodel@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
            )
            db_session.add(bubls_user)
            db_session.commit()
            db_session.refresh(bubls_user)

            trendfy_rows = db_session.execute(
                sa.text(
                    """
                    SELECT m.name, m.replicate_version, m.trigger_word, m.created_at, u.email
                    FROM models m JOIN users u ON m.user_id = u.id
                    WHERE m.replicate_version IS NOT NULL AND m.replicate_version != ''
                    """
                )
            ).fetchall()

            assert len(trendfy_rows) == 0

            models = db_session.query(LoraModel).filter(LoraModel.user_id == bubls_user.id).all()
            assert len(models) == 0
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def multipleModelsPerUser_allMigratedAndNewestIsActive(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            tid = _seed_trendfy_user(_test_engine, "sam@test.ch")
            now = datetime.now(timezone.utc)
            _seed_trendfy_model(_test_engine, tid, "sam_v1", "owner/v1:aaa", "TOK", now - timedelta(days=30))
            _seed_trendfy_model(_test_engine, tid, "sam_v2", "owner/v2:bbb", "TOK", now - timedelta(days=15))
            _seed_trendfy_model(_test_engine, tid, "sam_v3a", "owner/v3a:ccc", "WRDRB1PERSON", now)

            bubls_user = User(
                email="sam@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
            )
            db_session.add(bubls_user)
            db_session.commit()
            db_session.refresh(bubls_user)

            trendfy_rows = db_session.execute(
                sa.text(
                    """
                    SELECT m.name, m.replicate_version, m.trigger_word, m.created_at, u.email
                    FROM models m JOIN users u ON m.user_id = u.id
                    WHERE m.replicate_version IS NOT NULL AND m.replicate_version != ''
                    ORDER BY m.created_at ASC
                    """
                )
            ).fetchall()

            for row in trendfy_rows:
                target_user = db_session.query(User).filter(User.email == row.email.strip().lower()).one_or_none()
                if target_user is None:
                    continue
                lora = LoraModel(
                    user_id=target_user.id,
                    replicate_model_id=row.replicate_version,
                    trigger_word=row.trigger_word or "WRDRB1PERSON",
                    default_style_prompt="professional portrait, cinematic lighting",
                    created_at=row.created_at,
                )
                db_session.add(lora)

            db_session.commit()

            all_models = (
                db_session.query(LoraModel)
                .filter(LoraModel.user_id == bubls_user.id)
                .order_by(LoraModel.created_at.desc())
                .all()
            )
            assert len(all_models) == 3

            # The repository's find_active_lora_for_user returns the most recent.
            newest = all_models[0]
            assert newest.replicate_model_id == "owner/v3a:ccc"
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def noBublsUser_modelSkipped(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            tid = _seed_trendfy_user(_test_engine, "orphan@test.ch")
            _seed_trendfy_model(_test_engine, tid, "orphan-model", "owner/orphan:xyz")

            # Do NOT create a Bubls user for orphan@test.ch.
            trendfy_rows = db_session.execute(
                sa.text(
                    """
                    SELECT m.name, m.replicate_version, m.trigger_word, m.created_at, u.email
                    FROM models m JOIN users u ON m.user_id = u.id
                    WHERE m.replicate_version IS NOT NULL AND m.replicate_version != ''
                    """
                )
            ).fetchall()

            migrated = 0
            for row in trendfy_rows:
                target_user = db_session.query(User).filter(User.email == row.email.strip().lower()).one_or_none()
                if target_user is None:
                    continue
                migrated += 1

            assert migrated == 0
        finally:
            _cleanup_trendfy_tables(_test_engine)
```

---

## 6. Commit Plan

### Commit 1: Alembic migration + tests

**Files**:
- `server/migrations/versions/20260422_migrate_trendfy_models.py`
- `server/tests/test_trendfy_model_migration.py`

**Message**: `feat(migration): add Trendfy model migration script (task 2)`

**Gate**: `python -m pytest tests/test_trendfy_model_migration.py -v` passes.

---

## 7. Verification

```bash
cd /projects/bubls/server
python -m pytest tests/ -v
```

**Expected delta**: +6 new tests (TestMigrationModule: 2, TestModelMigrationLogic: 4). Zero failures. The new test file is fully green.

Confirm the migration module imports cleanly and chains correctly:

```bash
cd /projects/bubls/server
python -c "
from migrations.versions.20260422_migrate_trendfy_models import revision, down_revision
from migrations.versions.20260421_migrate_trendfy_users import revision as prev
assert down_revision == prev, f'{down_revision} != {prev}'
print('chain OK')
"
```

---

## 8. Rollback

### Per-step rollback

If the migration has been applied to a live database:

```bash
cd /projects/bubls/server
DATABASE_URL=$DATABASE_URL alembic downgrade 20260421_migrate_trendfy_users
```

This runs the `downgrade()` function which deletes `superapp_lora_models` rows whose `replicate_model_id` matches a Trendfy model's `replicate_version`, but only if those models have no dependent `superapp_generations` rows.

### Full rollback (both Task 1 and Task 2)

```bash
cd /projects/bubls/server
DATABASE_URL=$DATABASE_URL alembic downgrade 20260420_drop_onboarding_fields
```

### Per-branch rollback

```bash
git revert <commit-sha>
```

---

## 9. Deviations Allowed

- **Trendfy `models` table has a column named differently than `replicate_version`**: If the column is named `replicate_model_id` or similar, update the SELECT query. Note the deviation in the commit body.
- **A Trendfy model has an empty string for `trigger_word`**: The migration falls back to `WRDRB1PERSON`. This is the expected behavior per `core/config.py`.
- **Sam already has a `superapp_lora_models` row from `seed.py`**: The idempotency check (same `user_id` + `replicate_model_id`) will skip that row. If Sam's seed model uses a different `replicate_model_id` string than Trendfy's, both rows will coexist -- this is acceptable because `find_active_lora_for_user()` returns the most recent by `created_at`.
- **Fewer or more than 7 models have `replicate_version IS NOT NULL`**: The migration handles any count. Log output reflects the actual number.

---

## 10. Out of Scope

The executor must **STOP and flag** if any of these become necessary:

- **Adding an `is_active` column to `superapp_lora_models`**: Not needed. The repository's ordering convention handles active-model selection. If a model picker is requested, that is a separate task.
- **Creating or modifying `superapp_generations` rows**: That is Task 3.
- **Retraining or updating Replicate model versions**: This migration copies existing version strings verbatim.
- **Building a model picker or model management UI**: Out of scope per the epic.
- **Modifying Trendfy tables**: This migration is read-only against Trendfy.
- **Migrating Trendfy orders or payment data**: Explicitly excluded in the epic's non-goals.
- **Changing `core/config.py` MODELS dict**: The config dict is for inference routing, not migration. Leave it unchanged.
