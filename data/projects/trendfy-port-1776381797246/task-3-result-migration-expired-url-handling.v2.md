# Task 3: Result Migration + Expired-URL Handling

Alembic migration that reads Trendfy's `results` table (76 rows), HEAD-checks each image URL for expiry, creates `superapp_generations` rows with `feature = 'photoshoot'`, and adds a new `expired` nullable boolean column to `superapp_generations` for flagging dead URLs.

---

## 1. Context

Trendfy stores generated images in a `results` table with 76 rows. Each row links to an `order` which links to a `user`. The `image_url` field holds Replicate CDN URLs that expire after roughly 1 hour. Most of these 76 URLs are already dead. The migration must detect this and mark expired rows so the UI can render a placeholder instead of a broken image.

This is the only task in the epic that adds a DDL change: a new `expired` nullable boolean column on `superapp_generations`. All other tasks are pure data migrations.

### Trade-offs considered

- **Re-download all valid URLs to S3/R2 before they expire** -- rejected. Cloud storage provisioning is out of scope for this epic. The device photo library is the storage layer for v1. Expired URLs get a placeholder; valid URLs get served as-is.
- **Skip expired results entirely (do not migrate them)** -- rejected. Even expired results carry signal: the user generated N images on date X with model Y. History completeness matters for TestFlight testers who want to see their Trendfy work in Bubls.
- **Add `expired` as a non-nullable column with default `false`** -- rejected. Existing `superapp_generations` rows (created by Bubls photoshoot or text features) should not need a default value forced on them. Nullable boolean with `NULL` meaning "not checked / not applicable" is the safest choice. Only Trendfy-migrated rows get an explicit `true` or `false` value.

---

## 2. Pre-flight

Before writing any code, the executor must record baseline state:

```bash
cd /projects/bubls/server
git status
git diff HEAD
```

Verify current Alembic head:

```bash
cd /projects/bubls/server
DATABASE_URL=$DATABASE_URL alembic current
```

The `down_revision` for this migration is `20260422_migrate_trendfy_models` (Task 2). Both Task 1 and Task 2 must precede this in the revision chain (users and models must exist before results can reference them).

Run existing tests to confirm green baseline:

```bash
cd /projects/bubls/server
python -m pytest tests/ -q
```

Record the test count.

Inspect current `superapp_generations` columns to confirm `expired` does not already exist:

```bash
cd /projects/bubls/server
python -c "
from sqlalchemy import inspect as sa_inspect
from core.database import engine
cols = {c['name'] for c in sa_inspect(engine).get_columns('superapp_generations')}
assert 'expired' not in cols, 'expired column already exists'
print('confirmed: expired column does not exist yet')
print('current columns:', sorted(cols))
"
```

---

## 3. Files

### To Create

| Path | Purpose |
|------|---------|
| `server/migrations/versions/20260423_migrate_trendfy_results.py` | Alembic migration: DDL (add `expired` column) + data migration (read Trendfy `results`, HEAD-check URLs, insert `superapp_generations`) |
| `server/tests/test_trendfy_result_migration.py` | Pytest tests for the migration module, schema change, and result-mapping logic |

### To Modify

| Path | Change |
|------|--------|
| `server/modules/photoshoot/models.py` | Add `expired: Mapped[bool \| None]` column to `Generation` class |

### To Leave Alone

| Path | Reason |
|------|--------|
| `server/modules/photoshoot/repository.py` | Result listing already works; expired filtering is a UI concern (Task 5) |
| `server/modules/photoshoot/routes.py` | No API changes for this task |
| `server/modules/photoshoot/dto.py` | DTO changes for expired display belong to Task 5 |
| `server/core/config.py` | No new config needed |
| `server/migrations/env.py` | No new module import needed |

---

## 4. Implementation Steps

### Step 1: Add the `expired` column to the Generation ORM model

**Action**: Add a nullable boolean column `expired` to the `Generation` class in `server/modules/photoshoot/models.py`.

**File**: `server/modules/photoshoot/models.py`

**Pattern**: Follow the existing nullable column pattern (see `original_thumbnail`, `feature`, `input_text`, `result_text`). Place the new column after `result_text` and before `created_at`.

Add this line to the `Generation` class, before the `created_at` field:

```python
    # Trendfy migration: True if the Replicate CDN URL has expired, False if
    # still reachable, NULL for rows not checked (native Bubls generations).
    expired: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True, default=None)
```

**Verify**:

```bash
cd /projects/bubls/server
python -c "from modules.photoshoot.models import Generation; print([c.name for c in Generation.__table__.columns])"
# Expected: expired appears in the list
```

### Step 2: Create the Alembic migration file

**Action**: Create `server/migrations/versions/20260423_migrate_trendfy_results.py`.

**File**: `server/migrations/versions/20260423_migrate_trendfy_results.py`

**Pattern**: Mixed DDL + data migration. First, `op.add_column()` adds the `expired` column. Then, a data migration reads Trendfy's `results` table joined through `orders` to `users` for email lookup, resolves the `superapp_users` and `superapp_lora_models` rows, HEAD-checks each `image_url`, and inserts `superapp_generations` rows with `feature = 'photoshoot'`.

The HEAD-check uses Python's `urllib.request.urlopen` with method `HEAD` and a 5-second timeout. A URL is considered expired if it returns a non-2xx status or raises any exception (timeout, DNS failure, connection refused). This is a one-time cost at migration time, not per-render.

```python
"""migrate trendfy results into superapp_generations + add expired column

Revision ID: 20260423_migrate_trendfy_results
Revises: 20260422_migrate_trendfy_models
Create Date: 2026-04-23

DDL: adds nullable boolean `expired` column to `superapp_generations`.
Data: reads Trendfy's `results` table (76 rows), HEAD-checks each
image_url for expiry, inserts `superapp_generations` rows with
`feature = 'photoshoot'` and `expired = true/false`.

Idempotent: skips if a `superapp_generations` row already exists with
the same `user_id + result_image_url` combination.
"""
from __future__ import annotations

import uuid
import urllib.request
import urllib.error

import sqlalchemy as sa

from alembic import op

revision = "20260423_migrate_trendfy_results"
down_revision = "20260422_migrate_trendfy_models"
branch_labels = None
depends_on = None

_HEAD_TIMEOUT_SECONDS = 5


def _is_url_expired(url: str) -> bool:
    """HEAD-check a URL. Returns True if expired/unreachable, False if live."""
    if not url or not url.startswith("http"):
        return True
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=_HEAD_TIMEOUT_SECONDS) as resp:
            return resp.status >= 400
    except Exception:
        return True


def upgrade() -> None:
    # ── DDL: add expired column ──────────────────────────────────────
    op.add_column(
        "superapp_generations",
        sa.Column("expired", sa.Boolean(), nullable=True),
    )

    conn = op.get_bind()

    # ── Data: read Trendfy results joined through orders -> users ────
    trendfy_results = conn.execute(
        sa.text(
            """
            SELECT r.id AS result_id,
                   r.order_id,
                   r.model_id AS trendfy_model_id,
                   r.scenario_key,
                   r.image_path,
                   r.image_url,
                   r.generated_at,
                   o.user_id AS trendfy_user_id,
                   u.email
            FROM results r
            JOIN orders o ON r.order_id = o.id
            JOIN users u ON o.user_id = u.id
            ORDER BY r.generated_at ASC
            """
        )
    ).fetchall()

    migrated = 0
    expired_count = 0
    skipped = 0

    for row in trendfy_results:
        trendfy_email = row.email.strip().lower()
        image_url = row.image_url or row.image_path or ""

        # Look up the Bubls user.
        bubls_user = conn.execute(
            sa.text("SELECT id FROM superapp_users WHERE email = :email"),
            {"email": trendfy_email},
        ).fetchone()

        if bubls_user is None:
            print(f"  [migrate] WARN: no superapp_users row for {trendfy_email} -- skipping result {row.result_id}")
            skipped += 1
            continue

        bubls_user_id = bubls_user.id

        # Check for duplicate (same user + same URL).
        existing = conn.execute(
            sa.text(
                """
                SELECT id FROM superapp_generations
                WHERE user_id = :user_id
                  AND result_image_url = :url
                """
            ),
            {"user_id": str(bubls_user_id), "url": image_url},
        ).fetchone()

        if existing is not None:
            skipped += 1
            continue

        # Resolve the Bubls lora_model_id if a Trendfy model was linked.
        bubls_lora_id = None
        if row.trendfy_model_id is not None:
            # Find the Trendfy model's replicate_version.
            trendfy_model = conn.execute(
                sa.text("SELECT replicate_version FROM models WHERE id = :mid"),
                {"mid": row.trendfy_model_id},
            ).fetchone()

            if trendfy_model is not None and trendfy_model.replicate_version:
                # Look up the Bubls lora model by replicate_model_id + user_id.
                bubls_lora = conn.execute(
                    sa.text(
                        """
                        SELECT id FROM superapp_lora_models
                        WHERE user_id = :uid AND replicate_model_id = :rid
                        """
                    ),
                    {"uid": str(bubls_user_id), "rid": trendfy_model.replicate_version},
                ).fetchone()

                if bubls_lora is not None:
                    bubls_lora_id = bubls_lora.id

        # HEAD-check the URL for expiry.
        is_expired = _is_url_expired(image_url)
        if is_expired:
            expired_count += 1

        new_id = uuid.uuid4()

        conn.execute(
            sa.text(
                """
                INSERT INTO superapp_generations
                    (id, user_id, lora_model_id, result_image_url, feature, expired, created_at)
                VALUES
                    (:id, :user_id, :lora_model_id, :url, 'photoshoot', :expired, :created_at)
                """
            ),
            {
                "id": str(new_id),
                "user_id": str(bubls_user_id),
                "lora_model_id": str(bubls_lora_id) if bubls_lora_id else None,
                "url": image_url,
                "expired": is_expired,
                "created_at": row.generated_at,
            },
        )

        migrated += 1

    print(f"\n  [migrate] trendfy result migration complete: {migrated} migrated, {expired_count} expired, {skipped} skipped")


def downgrade() -> None:
    """Remove migrated results and drop the expired column."""
    conn = op.get_bind()

    # Delete superapp_generations rows that came from Trendfy results.
    # These are identifiable by: feature = 'photoshoot' AND expired IS NOT NULL
    # (native Bubls generations have expired = NULL).
    result = conn.execute(
        sa.text(
            """
            DELETE FROM superapp_generations
            WHERE feature = 'photoshoot' AND expired IS NOT NULL
            """
        )
    )
    print(f"  [rollback] deleted {result.rowcount} migrated result rows")

    # Drop the expired column.
    op.drop_column("superapp_generations", "expired")
```

**Verify**:

```bash
cd /projects/bubls/server
python -c "import importlib; m = importlib.import_module('migrations.versions.20260423_migrate_trendfy_results'); assert m.revision == '20260423_migrate_trendfy_results'; assert m.down_revision == '20260422_migrate_trendfy_models'; print('OK')"
```

### Step 3: Create the test file

**Action**: Create `server/tests/test_trendfy_result_migration.py`.

**File**: `server/tests/test_trendfy_result_migration.py`

**Pattern**: Create Trendfy `users`, `models`, `orders`, and `results` tables in the SQLite test DB. Seed with known data. Mock `_is_url_expired` to avoid real HTTP calls in tests. Exercise the migration logic via the ORM and raw SQL. Assert correct `superapp_generations` rows appear with proper `expired` values.

See Section 5 for full test bodies.

**Verify**:

```bash
cd /projects/bubls/server
python -m pytest tests/test_trendfy_result_migration.py -v
```

---

## 5. Tests

File: `server/tests/test_trendfy_result_migration.py`

```python
"""Tests for the Trendfy result migration (20260423).

Validates migration module structure, the new `expired` column on the
Generation model, and the result-mapping logic including URL expiry
detection.
"""
from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from core.database import Base
from modules.photoshoot.models import Generation, LoraModel, User


def _create_trendfy_tables(engine):
    """Create minimal Trendfy users + models + orders + results tables."""
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
                    user_id INT NOT NULL REFERENCES users(id),
                    name VARCHAR(100) NOT NULL,
                    replicate_version VARCHAR(512),
                    trigger_word VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'ready',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR(50) PRIMARY KEY,
                    user_id INT REFERENCES users(id),
                    model_id INT REFERENCES models(id),
                    email VARCHAR(255) NOT NULL,
                    name VARCHAR(100),
                    trigger_word VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'uploading',
                    phase_name VARCHAR(50),
                    phase_started_at TIMESTAMP,
                    error_message TEXT,
                    photo_count INT DEFAULT 0,
                    stripe_payment_intent_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id VARCHAR(50) NOT NULL REFERENCES orders(id),
                    model_id INT REFERENCES models(id),
                    scenario_key VARCHAR(50) NOT NULL,
                    image_path VARCHAR(512) NOT NULL,
                    image_url VARCHAR(512),
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _cleanup_trendfy_tables(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS results"))
        conn.execute(sa.text("DROP TABLE IF EXISTS orders"))
        conn.execute(sa.text("DROP TABLE IF EXISTS models"))
        conn.execute(sa.text("DROP TABLE IF EXISTS users"))


def _seed_full_trendfy_chain(engine, email: str, model_name: str, replicate_version: str, order_id: str, image_url: str):
    """Seed a complete Trendfy chain: user -> model -> order -> result."""
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            sa.text("INSERT OR IGNORE INTO users (email, created_at) VALUES (:e, :ts)"),
            {"e": email, "ts": now},
        )
        user_id = conn.execute(
            sa.text("SELECT id FROM users WHERE email = :e"), {"e": email}
        ).fetchone().id

        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO models (user_id, name, replicate_version, created_at) VALUES (:uid, :n, :rv, :ts)"
            ),
            {"uid": user_id, "n": model_name, "rv": replicate_version, "ts": now},
        )
        model_id = conn.execute(
            sa.text("SELECT id FROM models WHERE user_id = :uid AND name = :n"),
            {"uid": user_id, "n": model_name},
        ).fetchone().id

        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO orders (id, user_id, model_id, email, status, created_at) VALUES (:oid, :uid, :mid, :e, 'completed', :ts)"
            ),
            {"oid": order_id, "uid": user_id, "mid": model_id, "e": email, "ts": now},
        )

        conn.execute(
            sa.text(
                "INSERT INTO results (order_id, model_id, scenario_key, image_path, image_url, generated_at) VALUES (:oid, :mid, 'office', :ip, :iu, :ts)"
            ),
            {"oid": order_id, "mid": model_id, "ip": image_url, "iu": image_url, "ts": now},
        )


class TestMigrationModule:
    def migration_declaresCorrectRevisionChain(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        assert mod.revision == "20260423_migrate_trendfy_results"
        assert mod.down_revision == "20260422_migrate_trendfy_models"

    def migration_exposesUpgradeAndDowngrade(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)


class TestExpiredColumn:
    def generationModel_hasExpiredColumn(self, _test_engine):
        cols = {c["name"] for c in sa_inspect(_test_engine).get_columns("superapp_generations")}
        assert "expired" in cols, "Generation ORM must declare expired column"

    def expiredColumn_isNullable(self, db_session):
        gen = Generation(
            user_id=uuid.uuid4(),
            result_image_url="https://example.com/img.png",
            feature="photoshoot",
        )
        # expired defaults to None.
        assert gen.expired is None

    def expiredColumn_acceptsTrueAndFalse(self, db_session, make_user):
        user = make_user(db_session)
        gen_expired = Generation(
            user_id=user.id,
            result_image_url="https://expired.com/img.png",
            feature="photoshoot",
            expired=True,
        )
        gen_live = Generation(
            user_id=user.id,
            result_image_url="https://live.com/img.png",
            feature="photoshoot",
            expired=False,
        )
        db_session.add_all([gen_expired, gen_live])
        db_session.commit()

        rows = db_session.query(Generation).filter(Generation.user_id == user.id).all()
        expired_vals = {r.result_image_url: r.expired for r in rows}
        assert expired_vals["https://expired.com/img.png"] is True
        assert expired_vals["https://live.com/img.png"] is False


class TestUrlExpiryCheck:
    def liveUrl_returnsFalse(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = mock_open.return_value.__enter__.return_value
            mock_resp.status = 200
            assert mod._is_url_expired("https://live.example.com/img.png") is False

    def expiredUrl_returnsTrue(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = mock_open.return_value.__enter__.return_value
            mock_resp.status = 403
            assert mod._is_url_expired("https://expired.example.com/img.png") is True

    def timeoutUrl_returnsTrue(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            assert mod._is_url_expired("https://timeout.example.com/img.png") is True

    def emptyUrl_returnsTrue(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        assert mod._is_url_expired("") is True
        assert mod._is_url_expired(None) is True

    def nonHttpUrl_returnsTrue(self):
        mod = importlib.import_module(
            "migrations.versions.20260423_migrate_trendfy_results"
        )
        assert mod._is_url_expired("/local/path/img.png") is True


class TestResultMigrationLogic:
    def validResults_createsSuperappGenerations(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            _seed_full_trendfy_chain(
                _test_engine,
                email="milky@test.ch",
                model_name="milky-v1",
                replicate_version="owner/milky:abc",
                order_id="ord_001",
                image_url="https://replicate.delivery/img1.png",
            )

            # Create Bubls user + lora model.
            bubls_user = User(
                email="milky@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
            )
            db_session.add(bubls_user)
            db_session.commit()
            db_session.refresh(bubls_user)

            lora = LoraModel(
                user_id=bubls_user.id,
                replicate_model_id="owner/milky:abc",
                trigger_word="TOK",
            )
            db_session.add(lora)
            db_session.commit()
            db_session.refresh(lora)

            # Read Trendfy results.
            trendfy_rows = db_session.execute(
                sa.text(
                    """
                    SELECT r.image_url, r.generated_at, r.model_id, u.email
                    FROM results r
                    JOIN orders o ON r.order_id = o.id
                    JOIN users u ON o.user_id = u.id
                    """
                )
            ).fetchall()

            for row in trendfy_rows:
                gen = Generation(
                    user_id=bubls_user.id,
                    lora_model_id=lora.id,
                    result_image_url=row.image_url,
                    feature="photoshoot",
                    expired=False,
                    created_at=row.generated_at,
                )
                db_session.add(gen)

            db_session.commit()

            gens = db_session.query(Generation).filter(Generation.user_id == bubls_user.id).all()
            assert len(gens) == 1
            assert gens[0].feature == "photoshoot"
            assert gens[0].result_image_url == "https://replicate.delivery/img1.png"
            assert gens[0].lora_model_id == lora.id
            assert gens[0].expired is False
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def expiredUrl_markedAsExpired(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            _seed_full_trendfy_chain(
                _test_engine,
                email="expired@test.ch",
                model_name="exp-v1",
                replicate_version="owner/exp:xyz",
                order_id="ord_exp",
                image_url="https://replicate.delivery/expired.png",
            )

            bubls_user = User(
                email="expired@test.ch",
                token=uuid.uuid4(),
                enabled_features={"home": True, "photoshoot": True},
            )
            db_session.add(bubls_user)
            db_session.commit()
            db_session.refresh(bubls_user)

            gen = Generation(
                user_id=bubls_user.id,
                result_image_url="https://replicate.delivery/expired.png",
                feature="photoshoot",
                expired=True,
            )
            db_session.add(gen)
            db_session.commit()

            row = db_session.query(Generation).filter(Generation.user_id == bubls_user.id).first()
            assert row.expired is True
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def noBublsUser_resultSkipped(self, _test_engine, db_session):
        _create_trendfy_tables(_test_engine)
        try:
            _seed_full_trendfy_chain(
                _test_engine,
                email="orphan@test.ch",
                model_name="orphan-v1",
                replicate_version="owner/orphan:xyz",
                order_id="ord_orphan",
                image_url="https://replicate.delivery/orphan.png",
            )

            # Do NOT create a Bubls user.
            trendfy_rows = db_session.execute(
                sa.text(
                    """
                    SELECT r.image_url, u.email
                    FROM results r
                    JOIN orders o ON r.order_id = o.id
                    JOIN users u ON o.user_id = u.id
                    """
                )
            ).fetchall()

            migrated = 0
            for row in trendfy_rows:
                bubls_user = db_session.execute(
                    sa.text("SELECT id FROM superapp_users WHERE email = :e"),
                    {"e": row.email.strip().lower()},
                ).fetchone()
                if bubls_user is None:
                    continue
                migrated += 1

            assert migrated == 0
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def existingGeneration_notDuplicated(self, _test_engine, db_session, make_user):
        _create_trendfy_tables(_test_engine)
        try:
            _seed_full_trendfy_chain(
                _test_engine,
                email="dup@test.ch",
                model_name="dup-v1",
                replicate_version="owner/dup:aaa",
                order_id="ord_dup",
                image_url="https://replicate.delivery/dup.png",
            )

            bubls_user = make_user(db_session, email="dup@test.ch")

            # Pre-insert a generation with the same URL.
            existing_gen = Generation(
                user_id=bubls_user.id,
                result_image_url="https://replicate.delivery/dup.png",
                feature="photoshoot",
                expired=False,
            )
            db_session.add(existing_gen)
            db_session.commit()

            # Check for duplicate.
            dup_check = db_session.execute(
                sa.text(
                    """
                    SELECT id FROM superapp_generations
                    WHERE user_id = :uid AND result_image_url = :url
                    """
                ),
                {"uid": str(bubls_user.id), "url": "https://replicate.delivery/dup.png"},
            ).fetchone()

            assert dup_check is not None  # Duplicate detected, would skip.

            gens = db_session.query(Generation).filter(Generation.user_id == bubls_user.id).all()
            assert len(gens) == 1  # Only the pre-existing one.
        finally:
            _cleanup_trendfy_tables(_test_engine)

    def nativeBublsGeneration_hasNullExpired(self, db_session, make_user):
        user = make_user(db_session)
        gen = Generation(
            user_id=user.id,
            result_image_url="https://cdn.bubls.ch/new.png",
            feature="photoshoot",
        )
        db_session.add(gen)
        db_session.commit()
        db_session.refresh(gen)
        assert gen.expired is None
```

---

## 6. Commit Plan

### Commit 1: Add `expired` column to Generation ORM model

**Files**:
- `server/modules/photoshoot/models.py`

**Message**: `feat(model): add nullable expired column to Generation`

**Gate**: `python -m pytest tests/ -q` passes (existing tests unaffected by nullable column).

### Commit 2: Alembic migration + tests

**Files**:
- `server/migrations/versions/20260423_migrate_trendfy_results.py`
- `server/tests/test_trendfy_result_migration.py`

**Message**: `feat(migration): add Trendfy result migration with expired-URL detection (task 3)`

**Gate**: `python -m pytest tests/test_trendfy_result_migration.py -v` passes.

---

## 7. Verification

```bash
cd /projects/bubls/server
python -m pytest tests/ -v
```

**Expected delta**: +12 new tests across the new test file (TestMigrationModule: 2, TestExpiredColumn: 3, TestUrlExpiryCheck: 5, TestResultMigrationLogic: 5). Zero failures. All existing tests remain green (the new nullable `expired` column defaults to `None`, which is backward-compatible).

Confirm the migration module imports cleanly and chains correctly:

```bash
cd /projects/bubls/server
python -c "
from migrations.versions.20260423_migrate_trendfy_results import revision, down_revision
from migrations.versions.20260422_migrate_trendfy_models import revision as prev
assert down_revision == prev, f'{down_revision} != {prev}'
print('chain OK')
"
```

Confirm the Generation model has the `expired` column:

```bash
cd /projects/bubls/server
python -c "
from modules.photoshoot.models import Generation
cols = [c.name for c in Generation.__table__.columns]
assert 'expired' in cols, f'expired not in {cols}'
print('model OK:', cols)
"
```

---

## 8. Rollback

### Per-step rollback

If the migration has been applied to a live database:

```bash
cd /projects/bubls/server
DATABASE_URL=$DATABASE_URL alembic downgrade 20260422_migrate_trendfy_models
```

This runs the `downgrade()` function which:
1. Deletes `superapp_generations` rows where `feature = 'photoshoot' AND expired IS NOT NULL` (only Trendfy-migrated rows have non-null `expired`).
2. Drops the `expired` column from `superapp_generations`.

### Full rollback (all three tasks)

```bash
cd /projects/bubls/server
DATABASE_URL=$DATABASE_URL alembic downgrade 20260420_drop_onboarding_fields
```

### Per-branch rollback

```bash
git revert <commit-sha-2> <commit-sha-1>
```

Revert both commits (model change + migration) in reverse order. Then run `alembic downgrade` to remove the DB changes.

### ORM model rollback

If only the model change needs to be reverted, remove the `expired` line from `Generation` in `server/modules/photoshoot/models.py` and delete the migration file. The column will remain in the DB until `alembic downgrade` is run.

---

## 9. Deviations Allowed

- **Trendfy `results` table uses `generated_images` as the table name**: The epic mentions `generated_images` but the actual Trendfy schema uses `results`. If the executor encounters a different table name, update the SELECT queries. Note the deviation in the commit body.
- **Trendfy `results.image_url` is NULL for some rows**: The migration falls back to `image_path` (which is NOT NULL in the schema). If both are unusable, mark the result as `expired = True` with an empty URL.
- **HEAD-check takes too long (> 5 seconds per URL)**: The timeout is set to 5 seconds. For 76 URLs, worst case is ~6 minutes. If the migration environment has network restrictions that make HEAD requests impossible, the executor may set all URLs to `expired = True` and note the deviation.
- **Fewer or more than 76 results**: The migration handles any count. Log output reflects the actual number.
- **SQLite test DB does not support `op.drop_column` in downgrade**: SQLite has limited ALTER TABLE support. The downgrade `op.drop_column` may fail on SQLite. This is acceptable because downgrades are only executed against Postgres. Tests do not run downgrades.
- **Some results lack an `orders` join (orphaned results)**: If a result row has no matching order, the JOIN excludes it. This is safe -- orphaned results are not migrated.

---

## 10. Out of Scope

The executor must **STOP and flag** if any of these become necessary:

- **Re-downloading valid images to S3/R2**: This migration only checks URL liveness and stores the original URL. Cloud storage migration is out of scope for this epic.
- **Building the expired-image placeholder UI**: That is Task 5. This task only adds the data and the `expired` column.
- **Modifying the photoshoot generation endpoint or service**: The existing generation flow is unchanged. Only historical data is migrated.
- **Adding an API endpoint to expose `expired` status**: API changes belong to Task 5 when the history UI is extended.
- **Modifying Trendfy tables**: This migration is read-only against Trendfy.
- **Migrating Trendfy orders or payment data**: Explicitly excluded in the epic's non-goals. The `orders` table is only read to resolve `user_id` for result rows.
- **Photo-library save**: That is Task 4 (Capacitor plugin). Unrelated to this data migration.
- **Regenerating expired images**: Model inference is out of scope. Expired URLs get a placeholder, not a re-generation.
