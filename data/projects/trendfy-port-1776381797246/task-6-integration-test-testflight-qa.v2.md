Now I have the full picture. The spec-doc project generates implementation guides for the **Bubls** codebase. The CODEBASE CONTEXT and PRIOR TASKS describe the Bubls project structure. Let me generate the Task 6 implementation guide.

# 🛠️ Task 6: Integration Test + TestFlight QA

**Purpose**: End-to-end verification that all three Trendfy→Bubls migrations compose correctly across user→model→result boundaries, plus manual device QA confirming photo-library save, unified history rendering, and zero regression on the existing photoshoot flow.

**Effort**: 0.5 day

**Dependencies**: Tasks 1-5 (all three migrations shipped, photo-library adapter shipped, history UI + model label shipped)

**Parallel With**: —

**Blocks**: Epic closure — this is the final gate before marking "Port Trendfy into Bubls Photoshoot" complete.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Tasks 1-3 each have unit tests but none prove the migrations **compose**: user migration creates `superapp_users`, model migration creates `superapp_lora_models` referencing those users, result migration creates `superapp_generations` referencing both — with expired-URL detection via HTTP HEAD. A single user's data traverses all three migrations, and a defect in ordering, FK-like references, or idempotency would only surface when the three run in sequence against the same DB. Task 6 seeds a SQLite test DB with representative Trendfy fixture data (3 users, 3 models, 5 results with a mix of valid and expired URLs), runs all three migrations in order, and asserts cross-migration referential integrity, correct counts, expired-URL flags, and idempotency (second run changes nothing). The second half is manual: build a TestFlight binary, verify photo-library save on a physical iOS device, confirm the history UI shows both Trendfy-migrated and Bubls-native results sorted by date with expired placeholders, and smoke-test the existing photoshoot flow (immersive mode, contact sheet, progress portrait) for regressions.

**Trade-offs considered**:
- **Full Alembic runner (`alembic upgrade head`) in tests** — rejected because the test DB is SQLite and the Alembic migrations may contain Postgres-specific DDL (`JSONB`, `UUID`); importing the migration logic functions directly is simpler and already proven in Tasks 1-3's unit tests.
- **Cypress/Playwright e2e for frontend history + expired placeholder** — rejected because the app is Ionic+Capacitor with no web-accessible prod URL; photo-library save requires device APIs that browser e2e tools cannot exercise. Manual TestFlight QA is the only valid device-level verification.
- **Skip the e2e, trust existing unit tests** — rejected because cross-migration referential integrity (every generation's user exists in `superapp_users`, every model's user exists, idempotency across the full chain) is not covered by any individual task's tests.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}
git status                                                  # flag unrelated M/?? entries
git log -1 --format='%H' > /tmp/bubls-pretask6-sha          # rollback anchor

# Verify Tasks 1-5 migrations + test files exist
ls server/migrations/versions/20260421_migrate_trendfy_users.py
ls server/migrations/versions/20260422_migrate_trendfy_models.py
ls server/migrations/versions/20260423_migrate_trendfy_results.py
ls server/tests/test_trendfy_user_migration.py
ls server/tests/test_trendfy_model_migration.py
ls server/tests/test_trendfy_result_migration.py
ls src/app/services/photo-library.service.ts
ls src/app/pages/photoshoot/components/contact-sheet.component.spec.ts
ls src/app/pages/photoshoot/photoshoot.page.spec.ts

# Baseline test counts
cd server && python -m pytest -q 2>&1 | tail -3             # record backend pass count
cd {WORKSPACE} && npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -5  # record frontend pass count
```

**If any Task 1-5 file is missing**: STOP. That task has not shipped. This task cannot proceed without all five predecessors.

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: Backend [N]/[N] passing. Frontend [M]/[M] passing.

---

## 3. Files

### To Create (new)
- `server/tests/test_migration_e2e.py` (new) — E2E integration test: creates Trendfy source tables + Bubls target tables in SQLite, seeds fixture data (3 users, 3 models, 5 results), runs all 3 migration logic functions in order, asserts cross-migration referential integrity, correct counts, expired-URL flags, and idempotency

### To Modify (cite codebase.md)
- `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts` — Add regression tests: mixed history with expired + non-expired tiles renders correctly; expired tiles show `data-test="tile-expired"` placeholder overlay; non-expired tiles show `<img>`
- `src/app/pages/photoshoot/photoshoot.page.spec.ts` — Add regression tests: mixed history (Trendfy-migrated + Bubls-native + expired) maps correctly into `GenerationTile` array; tiles sort by `created_at` descending; model label displays from `/api/photoshoot/active-model`

### To Leave Alone
- `server/migrations/versions/20260421_migrate_trendfy_users.py` — Task 1 shipped; not modified
- `server/migrations/versions/20260422_migrate_trendfy_models.py` — Task 2 shipped; not modified
- `server/migrations/versions/20260423_migrate_trendfy_results.py` — Task 3 shipped; not modified
- `server/modules/photoshoot/models.py` — Schema changes from Tasks 3/5 (`expired`, `model_name`, `is_active`); not modified here
- `server/modules/photoshoot/routes.py` — Task 5 already includes `expired` in response DTO; not modified
- `server/modules/photoshoot/lora_routes.py` — Task 5's active-model endpoint; not modified
- `src/app/services/photo-library.service.ts` — Task 4's adapter; tested separately in its own spec
- `src/app/services/photoshoot-api.service.ts` — API service unchanged
- `src/app/pages/photoshoot/components/contact-sheet.component.ts` — Task 5 added expired overlay; not modified here, only tested
- `src/app/pages/photoshoot/photoshoot.page.ts` — Task 5 added model label + expired mapping; not modified here, only tested
- `server/app.py` — No module registration changes
- `scripts/architecture-acl-check.mjs` — No new ACL concerns in this task
- `server/tests/test_trendfy_user_migration.py` — Task 1's unit tests; not modified
- `server/tests/test_trendfy_model_migration.py` — Task 2's unit tests; not modified
- `server/tests/test_trendfy_result_migration.py` — Task 3's unit tests; not modified

---

## 4. Implementation Steps

### Step 1: Identify importable migration logic functions

**Action**: Read each of the three migration files to identify their core data-transformation functions. Each migration should expose an importable function that takes a SQLAlchemy `Connection` (or `Engine`) and performs the data transformation — separate from the Alembic `upgrade()` wrapper that calls `op.get_bind()`. Record the function names and signatures.

**Files**:
- `server/migrations/versions/20260421_migrate_trendfy_users.py`
- `server/migrations/versions/20260422_migrate_trendfy_models.py`
- `server/migrations/versions/20260423_migrate_trendfy_results.py`

**Pattern**: Each migration should have a shape like:
```python
def _migrate_users(connection):
    """Core logic — callable from both upgrade() and tests."""
    ...

def upgrade():
    connection = op.get_bind()
    _migrate_users(connection)
```

**Verify**: Confirm each migration has an importable function by running:
```bash
grep -n "^def " server/migrations/versions/20260421_migrate_trendfy_users.py
grep -n "^def " server/migrations/versions/20260422_migrate_trendfy_models.py
grep -n "^def " server/migrations/versions/20260423_migrate_trendfy_results.py
```

**Deviation**: If a migration does NOT expose a standalone function (all logic is inside `upgrade()`), extract the body into a `_migrate_*` function that takes a `connection` argument, call it from `upgrade()`, and note the deviation in the commit body. This extraction is safe — `upgrade()` becomes a one-line wrapper.

---

### Step 2: Write the E2E migration integration test

**Action**: Create `server/tests/test_migration_e2e.py` with fixture data, table creation, migration execution, and assertions.

**File**: `server/tests/test_migration_e2e.py` (new)

**Pattern**:
```python
import importlib.util
import sqlalchemy as sa
from unittest.mock import patch
import pytest

# --- Fixture data ---
TRENDFY_USERS = [
    {"id": 1, "email": "alice@test.com", "password_hash": "bcrypt_1", "created_at": "2025-11-01"},
    {"id": 2, "email": "bob@test.com", "password_hash": "bcrypt_2", "created_at": "2025-12-15"},
    {"id": 3, "email": "existing@test.com", "password_hash": "bcrypt_3", "created_at": "2026-01-01"},
]

TRENDFY_MODELS = [
    {"id": 1, "user_id": 1, "replicate_model_id": "owner/model:v1", "replicate_version": "abc123",
     "trigger_word": "ALICESTYLE", "model_name": "Alice v1", "created_at": "2025-11-15"},
    {"id": 2, "user_id": 1, "replicate_model_id": "owner/model:v2", "replicate_version": "def456",
     "trigger_word": "ALICESTYLE2", "model_name": "Alice v2", "created_at": "2026-01-01"},
    {"id": 3, "user_id": 2, "replicate_model_id": None, "replicate_version": None,
     "trigger_word": None, "model_name": None, "created_at": "2025-12-20"},
]

TRENDFY_RESULTS = [
    {"id": 1, "user_id": 1, "model_id": 1, "result_url": "https://replicate.delivery/valid1.png",
     "prompt": "photo of alice", "created_at": "2025-11-20"},
    {"id": 2, "user_id": 1, "model_id": 2, "result_url": "https://replicate.delivery/valid2.png",
     "prompt": "alice v2 photo", "created_at": "2026-01-05"},
    {"id": 3, "user_id": 2, "model_id": 3, "result_url": "https://replicate.delivery/expired1.png",
     "prompt": "photo of bob", "created_at": "2025-12-25"},
    {"id": 4, "user_id": 1, "model_id": 1, "result_url": "https://replicate.delivery/expired2.png",
     "prompt": "another photo", "created_at": "2025-11-25"},
    {"id": 5, "user_id": 2, "model_id": 3, "result_url": "https://replicate.delivery/valid3.png",
     "prompt": "bob photo 2", "created_at": "2026-01-10"},
]

VALID_URLS = {"https://replicate.delivery/valid1.png",
              "https://replicate.delivery/valid2.png",
              "https://replicate.delivery/valid3.png"}

# --- Helpers ---
def _load_migration(filename):
    """Import a migration module by filename from the versions directory."""
    ...

def _mock_head(url, **kwargs):
    """Mock requests.head: 200 for valid URLs, 404 for expired."""
    ...

@pytest.fixture
def e2e_engine():
    """SQLite in-memory engine with Trendfy source + Bubls target tables seeded."""
    ...
```

**Verify**: `cd server && python -m pytest tests/test_migration_e2e.py -v` — expect all assertions green.

---

### Step 3: Add contact-sheet regression tests

**Action**: Add tests to `contact-sheet.component.spec.ts` verifying expired tile rendering with mixed data.

**File**: `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts` (modify)

**Pattern**:
```typescript
// Add to existing describe block
it('mixedHistory_expiredTilesShowPlaceholder', () => {
    // Arrange: set input with mix of expired and non-expired tiles
    // Act: trigger change detection
    // Assert: data-test="tile-expired" elements count matches expired tile count
    // Assert: non-expired tiles render <img> elements
});

it('mixedHistory_nonExpiredTilesShowImage', () => {
    // Arrange: same mixed input
    // Act: trigger change detection
    // Assert: non-expired tiles have <img> with src set
});
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless --include='**/contact-sheet*'` — new tests pass alongside existing.

---

### Step 4: Add photoshoot page regression tests

**Action**: Add tests to `photoshoot.page.spec.ts` verifying mixed history sort order and model label display.

**File**: `src/app/pages/photoshoot/photoshoot.page.spec.ts` (modify)

**Pattern**:
```typescript
// Add to existing describe block
it('mixedHistory_sortsNewestFirst', () => {
    // Arrange: mock API returns unsorted mix of Trendfy + Bubls generations
    // Act: component initializes
    // Assert: rendered tiles are in created_at DESC order
});

it('modelLabel_displaysActiveModelName', () => {
    // Arrange: mock /api/photoshoot/active-model returns { model_name: "Sam v3a" }
    // Act: component initializes
    // Assert: data-test="model-label" contains "Sam v3a"
});

it('expiredGeneration_mapsExpiredFlag', () => {
    // Arrange: mock API returns generation with expired: true
    // Act: component initializes
    // Assert: corresponding GenerationTile has expired === true
});
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless --include='**/photoshoot.page*'` — new tests pass alongside existing.

---

### Step 5: Run full test suites — zero regression

**Action**: Run the complete backend and frontend test suites. Verify zero pre-existing tests broken.

**Verify**:
```bash
cd {WORKSPACE}/server && python -m pytest -q
cd {WORKSPACE} && npx ng test --no-watch --browsers=ChromeHeadless
```

Expect: backend [N] → [N+6] passing (6 new assertions in e2e test). Frontend [M] → [M+5] passing (5 new tests across 2 spec files). Zero failures in pre-existing tests.

---

### Step 6: TestFlight build + manual device QA [REQUIRES APPROVAL]

**Action**: Build the iOS app, push to TestFlight, and execute the manual QA checklist on a physical iOS device.

**Build**:
```bash
cd {WORKSPACE}
npx cap sync ios                                          # sync web assets to native
cd ios/App
xcodebuild -workspace App.xcworkspace -scheme App \
  -sdk iphoneos -configuration Release archive \
  -archivePath build/Bubls.xcarchive                      # [REQUIRES APPROVAL]
```

**Upload to TestFlight**: via Xcode Organizer or `fastlane pilot upload` — [REQUIRES APPROVAL]

**Manual QA Checklist** (execute on physical iOS device):

| # | Check | Expected | Pass? |
|---|-------|----------|-------|
| 1 | Open photoshoot tab | Contact sheet loads with history tiles | |
| 2 | Verify migrated Trendfy results appear | Old Trendfy generations visible alongside any new Bubls generations | |
| 3 | Verify sort order | Newest results appear first (top-left of contact sheet) | |
| 4 | Verify expired placeholder | Trendfy results with expired URLs show "Image expired" overlay, not broken image | |
| 5 | Tap expired tile | No crash; placeholder or detail view with expired notice | |
| 6 | Verify model label | Header shows active model name (e.g., "Model: Sam v3a") or "No model" | |
| 7 | Run new generation | Full photoshoot flow: immersive mode → progress portrait → result renders | |
| 8 | Verify photo-library save | After generation completes, check iOS Photos app — new image saved to camera roll | |
| 9 | Verify new result in history | New generation appears at top of contact sheet alongside migrated results | |
| 10 | Kill + reopen app | History persists; no data loss on cold start | |

**Verify**: All 10 checks pass. Any failure → file as a defect against the responsible task (1-5), not this task.

---

## 5. Tests

### Backend: `server/tests/test_migration_e2e.py`

Complete test bodies using pytest. Follows the repo's existing framework (`server/tests/test_routes.py` et al.).

```python
"""E2E integration test: runs all three Trendfy→Bubls migrations in sequence.

Verifies cross-migration referential integrity, correct counts,
expired-URL detection, and idempotency.
"""
import importlib.util
import pathlib
from unittest.mock import patch, MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect

# ── Fixture data ──────────────────────────────────────────────

TRENDFY_USERS = [
    {"id": 1, "email": "alice@test.com", "password_hash": "bcrypt_1", "created_at": "2025-11-01"},
    {"id": 2, "email": "bob@test.com", "password_hash": "bcrypt_2", "created_at": "2025-12-15"},
    {"id": 3, "email": "existing@test.com", "password_hash": "bcrypt_3", "created_at": "2026-01-01"},
]

TRENDFY_MODELS = [
    {"id": 1, "user_id": 1, "replicate_model_id": "owner/model:v1", "replicate_version": "abc123",
     "trigger_word": "ALICESTYLE", "model_name": "Alice v1", "created_at": "2025-11-15"},
    {"id": 2, "user_id": 1, "replicate_model_id": "owner/model:v2", "replicate_version": "def456",
     "trigger_word": "ALICESTYLE2", "model_name": "Alice v2", "created_at": "2026-01-01"},
    {"id": 3, "user_id": 2, "replicate_model_id": None, "replicate_version": None,
     "trigger_word": None, "model_name": None, "created_at": "2025-12-20"},
]

TRENDFY_RESULTS = [
    {"id": 1, "user_id": 1, "model_id": 1, "result_url": "https://replicate.delivery/valid1.png",
     "prompt": "photo of alice", "created_at": "2025-11-20"},
    {"id": 2, "user_id": 1, "model_id": 2, "result_url": "https://replicate.delivery/valid2.png",
     "prompt": "alice v2 photo", "created_at": "2026-01-05"},
    {"id": 3, "user_id": 2, "model_id": 3, "result_url": "https://replicate.delivery/expired1.png",
     "prompt": "photo of bob", "created_at": "2025-12-25"},
    {"id": 4, "user_id": 1, "model_id": 1, "result_url": "https://replicate.delivery/expired2.png",
     "prompt": "another photo", "created_at": "2025-11-25"},
    {"id": 5, "user_id": 2, "model_id": 3, "result_url": "https://replicate.delivery/valid3.png",
     "prompt": "bob photo 2", "created_at": "2026-01-10"},
]

VALID_URLS = {
    "https://replicate.delivery/valid1.png",
    "https://replicate.delivery/valid2.png",
    "https://replicate.delivery/valid3.png",
}


# ── Helpers ───────────────────────────────────────────────────

def _load_migration(name: str):
    """Import a migration module from server/migrations/versions/ by filename prefix."""
    versions_dir = pathlib.Path(__file__).resolve().parent.parent / "migrations" / "versions"
    matches = list(versions_dir.glob(f"{name}*.py"))
    assert len(matches) == 1, f"Expected exactly 1 migration matching '{name}', found {len(matches)}: {matches}"
    spec = importlib.util.spec_from_file_location(name, matches[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_head_response(url, **kwargs):
    """Return 200 for valid URLs, 404 for expired."""
    resp = MagicMock()
    resp.status_code = 200 if url in VALID_URLS else 404
    return resp


def _create_trendfy_tables(conn):
    """Create mock Trendfy source tables in the test DB."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TEXT
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS lora_models (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            replicate_model_id TEXT,
            replicate_version TEXT,
            trigger_word TEXT,
            model_name TEXT,
            created_at TEXT
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS generated_images (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            model_id INTEGER,
            result_url TEXT,
            prompt TEXT,
            created_at TEXT
        )
    """))
    conn.commit()


def _create_bubls_tables(conn):
    """Create Bubls target tables in the test DB."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS superapp_users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            token TEXT,
            builder TEXT,
            onboarding_skipped_at TEXT,
            enabled_features TEXT,
            subscription_tier TEXT DEFAULT 'free',
            created_at TEXT
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS superapp_lora_models (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            replicate_model_id TEXT,
            trigger_word TEXT,
            model_name TEXT,
            default_style_prompt TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TEXT
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS superapp_generations (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            feature TEXT DEFAULT 'photoshoot',
            result_image_url TEXT,
            prompt TEXT,
            expired INTEGER,
            created_at TEXT
        )
    """))
    conn.commit()


def _seed_trendfy(conn):
    """Insert Trendfy fixture data into source tables."""
    for u in TRENDFY_USERS:
        conn.execute(text(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (:id, :email, :password_hash, :created_at)"
        ), u)
    for m in TRENDFY_MODELS:
        conn.execute(text(
            "INSERT INTO lora_models (id, user_id, replicate_model_id, replicate_version, trigger_word, model_name, created_at) "
            "VALUES (:id, :user_id, :replicate_model_id, :replicate_version, :trigger_word, :model_name, :created_at)"
        ), m)
    for r in TRENDFY_RESULTS:
        conn.execute(text(
            "INSERT INTO generated_images (id, user_id, model_id, result_url, prompt, created_at) "
            "VALUES (:id, :user_id, :model_id, :result_url, :prompt, :created_at)"
        ), r)
    conn.commit()


def _seed_existing_bubls_user(conn):
    """Pre-seed one superapp_user that overlaps with Trendfy data (idempotency test)."""
    conn.execute(text(
        "INSERT INTO superapp_users (id, email, token, created_at) "
        "VALUES ('existing-uuid', 'existing@test.com', 'existing-token', '2026-02-01')"
    ))
    conn.commit()


@pytest.fixture
def e2e_engine():
    """SQLite in-memory engine with all tables created and Trendfy data seeded."""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        _create_trendfy_tables(conn)
        _create_bubls_tables(conn)
        _seed_trendfy(conn)
        _seed_existing_bubls_user(conn)
    return engine


# ── Tests ─────────────────────────────────────────────────────

class TestMigrationE2E:
    """Run all three migrations in sequence and verify end-to-end integrity."""

    def _run_all_migrations(self, engine):
        """Execute user → model → result migration logic in order."""
        user_mod = _load_migration("20260421_migrate_trendfy_users")
        model_mod = _load_migration("20260422_migrate_trendfy_models")
        result_mod = _load_migration("20260423_migrate_trendfy_results")

        with engine.connect() as conn:
            # Identify the core function in each module.
            # Convention from Tasks 1-3: a private _migrate_* function taking a connection.
            # Fallback: look for a run() or migrate() function.
            for mod, fallback_name in [
                (user_mod, "_migrate_users"),
                (model_mod, "_migrate_models"),
                (result_mod, "_migrate_results"),
            ]:
                fn_name = None
                for candidate in [fallback_name, "run", "migrate"]:
                    if hasattr(mod, candidate):
                        fn_name = candidate
                        break
                assert fn_name is not None, (
                    f"Migration {mod.__name__} has no importable logic function. "
                    f"Expected one of: {fallback_name}, run, migrate"
                )
                getattr(mod, fn_name)(conn)

    def test_userCount_afterFullMigration(self, e2e_engine):
        """3 Trendfy users + 1 pre-existing → 3 total (ON CONFLICT skips existing@test.com)."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM superapp_users")).scalar()
            assert count == 3, f"Expected 3 superapp_users (2 new + 1 pre-existing), got {count}"

    def test_existingUser_notOverwritten(self, e2e_engine):
        """Pre-existing superapp_user retains its original token after migration."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            token = conn.execute(
                text("SELECT token FROM superapp_users WHERE email = 'existing@test.com'")
            ).scalar()
            assert token == "existing-token", f"Pre-existing user's token was overwritten: {token}"

    def test_modelCount_skipsNullReplicate(self, e2e_engine):
        """Only models with replicate_version NOT NULL are migrated (2 of 3)."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM superapp_lora_models")).scalar()
            assert count == 2, f"Expected 2 superapp_lora_models (skipped null replicate), got {count}"

    def test_mostRecentModel_isActive(self, e2e_engine):
        """Alice v2 (created 2026-01-01) is marked is_active=1; Alice v1 is not."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            active = conn.execute(
                text("SELECT model_name FROM superapp_lora_models WHERE is_active = 1")
            ).fetchall()
            assert len(active) == 1, f"Expected exactly 1 active model, got {len(active)}"
            assert active[0][0] == "Alice v2", f"Expected 'Alice v2' active, got '{active[0][0]}'"

    @patch("requests.head", side_effect=_mock_head_response)
    def test_resultCount_allMigrated(self, mock_head, e2e_engine):
        """All 5 Trendfy results are migrated regardless of model validity."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM superapp_generations")).scalar()
            assert count == 5, f"Expected 5 superapp_generations, got {count}"

    @patch("requests.head", side_effect=_mock_head_response)
    def test_expiredUrls_flaggedCorrectly(self, mock_head, e2e_engine):
        """3 valid URLs → expired=0; 2 expired URLs → expired=1."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            expired_count = conn.execute(
                text("SELECT COUNT(*) FROM superapp_generations WHERE expired = 1")
            ).scalar()
            valid_count = conn.execute(
                text("SELECT COUNT(*) FROM superapp_generations WHERE expired = 0 OR expired IS NULL")
            ).scalar()
            assert expired_count == 2, f"Expected 2 expired generations, got {expired_count}"
            assert valid_count == 3, f"Expected 3 non-expired generations, got {valid_count}"

    @patch("requests.head", side_effect=_mock_head_response)
    def test_crossMigration_generationUsersExist(self, mock_head, e2e_engine):
        """Every generation's user_id references an existing superapp_user email."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            # Get all user_ids from generations
            gen_user_ids = {row[0] for row in conn.execute(
                text("SELECT DISTINCT user_id FROM superapp_generations")
            ).fetchall()}
            # Get all user ids from superapp_users
            user_ids = {row[0] for row in conn.execute(
                text("SELECT id FROM superapp_users")
            ).fetchall()}
            orphans = gen_user_ids - user_ids
            assert orphans == set(), f"Generations reference non-existent users: {orphans}"

    @patch("requests.head", side_effect=_mock_head_response)
    def test_idempotency_secondRunChangesNothing(self, mock_head, e2e_engine):
        """Running all three migrations twice produces the same counts."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            users_before = conn.execute(text("SELECT COUNT(*) FROM superapp_users")).scalar()
            models_before = conn.execute(text("SELECT COUNT(*) FROM superapp_lora_models")).scalar()
            gens_before = conn.execute(text("SELECT COUNT(*) FROM superapp_generations")).scalar()

        # Run again
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            users_after = conn.execute(text("SELECT COUNT(*) FROM superapp_users")).scalar()
            models_after = conn.execute(text("SELECT COUNT(*) FROM superapp_lora_models")).scalar()
            gens_after = conn.execute(text("SELECT COUNT(*) FROM superapp_generations")).scalar()

        assert users_before == users_after, f"User count changed on second run: {users_before} → {users_after}"
        assert models_before == models_after, f"Model count changed on second run: {models_before} → {models_after}"
        assert gens_before == gens_after, f"Generation count changed on second run: {gens_before} → {gens_after}"

    @patch("requests.head", side_effect=_mock_head_response)
    def test_allGenerations_haveFeaturePhotoshoot(self, mock_head, e2e_engine):
        """Every migrated generation has feature='photoshoot'."""
        self._run_all_migrations(e2e_engine)
        with e2e_engine.connect() as conn:
            non_photoshoot = conn.execute(
                text("SELECT COUNT(*) FROM superapp_generations WHERE feature != 'photoshoot'")
            ).scalar()
            assert non_photoshoot == 0, f"{non_photoshoot} generations have wrong feature value"
```

**Deviation note**: The `@patch("requests.head", ...)` target may need adjustment depending on where the result migration imports `requests`. If the migration imports `requests` at module level, the patch target is `migrations.versions.20260423_migrate_trendfy_results.requests.head`. Inspect the import in the migration file and adjust the patch path accordingly. Log the adjustment in the commit body as a deviation.

---

### Frontend: contact-sheet regression tests

Add to `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts`:

```typescript
describe('ContactSheetComponent — migration regression', () => {
    // Assumes existing TestBed setup from Task 5 — reuse the same
    // ComponentFixture and page-object pattern.

    const MIXED_TILES = [
        { id: '1', result_image_url: 'https://example.com/img1.png', created_at: '2026-01-10', expired: false },
        { id: '2', result_image_url: 'https://example.com/img2.png', created_at: '2025-12-25', expired: true },
        { id: '3', result_image_url: 'https://example.com/img3.png', created_at: '2026-01-05', expired: false },
    ];

    it('expiredTile_showsPlaceholderOverlay', () => {
        // Arrange
        component.generations = MIXED_TILES;
        fixture.detectChanges();

        // Assert
        const expiredOverlays = fixture.nativeElement.querySelectorAll('[data-test="tile-expired"]');
        expect(expiredOverlays.length).toBe(1);
        expect(expiredOverlays[0].textContent).toContain('Image expired');
    });

    it('nonExpiredTiles_renderImages', () => {
        // Arrange
        component.generations = MIXED_TILES;
        fixture.detectChanges();

        // Assert
        const images = fixture.nativeElement.querySelectorAll('[data-test="tile-image"] img');
        expect(images.length).toBe(2);
        expect(images[0].src).toContain('img1.png');
    });
});
```

### Frontend: photoshoot page regression tests

Add to `src/app/pages/photoshoot/photoshoot.page.spec.ts`:

```typescript
describe('PhotoshootPage — migration regression', () => {
    // Assumes existing TestBed setup from Task 5 — reuse the same
    // mock PhotoshootApiService and page-object pattern.

    const MIXED_API_RESPONSE = [
        { id: '1', result_image_url: 'https://replicate.delivery/new.png', prompt: 'new gen',
          feature: 'photoshoot', expired: false, created_at: '2026-04-15T10:00:00Z' },
        { id: '2', result_image_url: 'https://replicate.delivery/old.png', prompt: 'trendfy gen',
          feature: 'photoshoot', expired: false, created_at: '2025-11-20T08:00:00Z' },
        { id: '3', result_image_url: 'https://replicate.delivery/gone.png', prompt: 'expired gen',
          feature: 'photoshoot', expired: true, created_at: '2025-12-01T14:00:00Z' },
    ];

    it('mixedHistory_sortsNewestFirst', async () => {
        // Arrange
        mockPhotoshootApi.getHistory.and.returnValue(Promise.resolve(MIXED_API_RESPONSE));

        // Act
        fixture.detectChanges();
        await fixture.whenStable();
        fixture.detectChanges();

        // Assert
        const tiles = fixture.nativeElement.querySelectorAll('[data-test="generation-tile"]');
        expect(tiles.length).toBe(3);
        // First tile is the newest (2026-04-15)
        expect(tiles[0].getAttribute('data-generation-id')).toBe('1');
    });

    it('modelLabel_displaysActiveModelName', async () => {
        // Arrange
        mockPhotoshootApi.getActiveModel.and.returnValue(
            Promise.resolve({ model_name: 'Sam v3a' })
        );

        // Act
        fixture.detectChanges();
        await fixture.whenStable();
        fixture.detectChanges();

        // Assert
        const label = fixture.nativeElement.querySelector('[data-test="model-label"]');
        expect(label.textContent).toContain('Sam v3a');
    });

    it('expiredGeneration_mapsExpiredFlag', async () => {
        // Arrange
        mockPhotoshootApi.getHistory.and.returnValue(Promise.resolve(MIXED_API_RESPONSE));

        // Act
        fixture.detectChanges();
        await fixture.whenStable();
        fixture.detectChanges();

        // Assert
        const expiredTiles = fixture.nativeElement.querySelectorAll('[data-test="tile-expired"]');
        expect(expiredTiles.length).toBe(1);
    });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. **`test(migration): e2e integration test — all 3 Trendfy→Bubls migrations in sequence`** — `server/tests/test_migration_e2e.py`: fixture data, table setup, migration chaining, count + integrity + expiry + idempotency assertions
2. **`test(photoshoot): regression tests for mixed history + expired tiles + model label`** — `contact-sheet.component.spec.ts`, `photoshoot.page.spec.ts`: expired overlay, sort order, model label, mixed data rendering
3. **`chore(qa): TestFlight build + manual device verification`** — no code changes; commit the QA checklist result as a note in the commit body (all 10 checks pass / which failed)

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/server && python -m pytest -q
cd {WORKSPACE} && npx ng test --no-watch --browsers=ChromeHeadless
```

**Expected delta**: Backend [N] → [N+10] passing (10 new assertions in `test_migration_e2e.py`). Frontend [M] → [M+5] passing (2 contact-sheet + 3 photoshoot page tests). Zero pre-existing tests broken.

**Manual QA**: All 10 TestFlight checklist items pass (see Step 6 table).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any of the 2 test commits.
- **Per-branch**: if verification fails catastrophically, `git reset --hard $(cat /tmp/bubls-pretask6-sha)` restores the pre-task state.
- **TestFlight**: if the build is defective, do not submit to App Store Review. TestFlight builds expire after 90 days; no manual cleanup needed.

---

## 9. Deviations Allowed

- **Migration logic not extractable** → if a migration has no standalone `_migrate_*` / `run` / `migrate` function and all logic is inside `upgrade()`, extract it into a private function taking a `connection` argument. This is a safe refactor (one-line wrapper). Log in commit body: `Deviations: extracted _migrate_X from upgrade() for testability`.
- **`requests.head` patch target differs** → the `@patch` decorator target depends on where the result migration imports `requests`. Inspect the import and adjust. Log: `Deviations: patch target adjusted to X`.
- **Frontend mock service API differs** → Task 5 may have named the mock methods differently (e.g., `fetchHistory` vs `getHistory`). Match the existing mock interface. Translate silently but note in commit body.
- **SQLite-vs-Postgres DDL mismatch** → if the migration uses Postgres-specific constructs (e.g., `gen_random_uuid()`, `JSONB` casts) that fail on SQLite, replace with SQLite equivalents in the test setup. Log: `Deviations: substituted SQLite-compatible DDL for X`.
- **TestFlight build blocked by signing** → if the Xcode signing certificate or provisioning profile is expired, STOP and flag as [REQUIRES APPROVAL] rather than generating new credentials.

---

## 10. Out of Scope

This task is the verification gate, not a feature task. It does NOT add new functionality, modify existing behavior, or touch migration logic. Any defect discovered during testing is filed against the responsible predecessor task (1-5), not fixed inline here.

- **Fixing migration bugs found during e2e testing** — if a count assertion fails, the defect is in the migration code (Tasks 1-3). STOP, report which assertion failed and which migration is responsible. Do not patch the migration in this task's branch.
- **Fixing expired-placeholder rendering bugs** — if the placeholder doesn't render, the defect is in Task 5's contact-sheet changes. Report and defer.
- **Photo-library save failure on device** — if images don't save to the camera roll, the defect is in Task 4's `PhotoLibraryService`. Report and defer.
- **Performance optimization of history loading** — if the history endpoint is slow with migrated data, that's a follow-up task. Not in scope.
- **Automated device testing (XCUITest, Detox)** — the 0.5-day budget covers manual QA only. Automated device tests are a future investment if the manual checklist keeps growing.
- **Alembic upgrade-path testing** (running `alembic upgrade head` end-to-end against a test Postgres instance) — valuable but requires Postgres in CI. Deferred until CI pipeline includes a Postgres service container.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)