# Task 3: Usage Metering Module — Implementation Guide

## 1. Context

This task builds `modules/usage/` — a self-contained metering layer that enforces daily free-tier call caps on three AI endpoints. It exposes two public surfaces: a `UsageCounter` SQLModel entity (one row per user × feature × UTC date) and a `check_usage_limit(feature)` Flask decorator that reads `g.current_user.plan`, short-circuits for Pro users, returns a structured 429 before work is started when the cap is reached, and increments the counter atomically only after a sub-400 response. The module has no HTTP routes of its own in v1; all state is in the database via a dialect-safe `ON CONFLICT DO UPDATE` upsert that avoids any in-process counter dict (ELA #7). Caps live in a single constant dict (`DAILY_FREE_TIER_LIMITS`) so they can be tuned in one line without touching routes or tests.

**Trade-offs considered:**
- **In-process counter dict (module-level, like `task_gen` STATE)** — rejected; concurrent requests from the same session would race and the counter would not survive a gunicorn worker restart. The DB row is the durable, concurrent-safe unit.
- **Application-level lock + ORM select-then-update** — rejected; still races without `SELECT FOR UPDATE`, adds locking complexity, and is unnecessary when SQLite 3.24+ / Postgres both support `INSERT … ON CONFLICT DO UPDATE RETURNING` natively.
- **Atomic SQL upsert via `session.execute(text(…))` + `RETURNING count`** — preferred; single round-trip, no ORM row-lock overhead, identical semantics on SQLite (dev) and Postgres (prod), and the count is returned atomically so callers know the new value without a second read.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm clean working tree on target files
git status
git diff HEAD -- \
  api/create_app.py \
  api/modules/ai/routes.py \
  api/modules/task_gen/routes.py \
  api/modules/spec_gen/routes.py

# 2. Check whether Task 2 already created the shared DB layer
ls api/db.py 2>/dev/null && echo "db.py EXISTS — skip Step 1" || echo "db.py ABSENT — create it"

# 3. Confirm require_auth exists (hard dependency for decorator stacking)
grep -r "def require_auth" api/modules/ || echo "BLOCKER: require_auth not found — stop here"

# 4. Record baseline test count
cd api && python -m pytest --tb=no -q 2>&1 | tail -3
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**If `require_auth` is missing**: this task is blocked. The decorator stacking order `@require_auth → @check_usage_limit` requires auth to be in place. File the gap as a deviation and do not apply `@check_usage_limit` to routes until auth ships.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)

| Path | Purpose |
|---|---|
| `api/db.py` | SQLModel engine, `get_session()` context manager, `init_db()`. Shared by billing (Task 2) and usage. Create only if absent. |
| `api/modules/usage/__init__.py` | Package marker. No Blueprint — no HTTP routes in v1. |
| `api/modules/usage/models.py` | `UsageCounter` SQLModel with unique constraint on `(user_id, feature, date)`. |
| `api/modules/usage/service.py` | `DAILY_FREE_TIER_LIMITS` dict; `increment`, `get_count`, `get_remaining`, `reset_at_utc`. |
| `api/modules/usage/middleware.py` | `check_usage_limit(feature)` decorator; `_status_code` helper. |
| `api/modules/usage/tests/__init__.py` | Test package marker. |
| `api/modules/usage/tests/test_service.py` | 12 unit tests for service layer. |
| `api/modules/usage/tests/test_middleware.py` | 7 unit tests for the decorator. |

### To Modify (cite CODEBASE CONTEXT)

| Path | Change |
|---|---|
| `api/create_app.py` | Import `UsageCounter` (registers table with SQLModel metadata) and call `init_db()` after blueprint registration. |
| `api/modules/ai/routes.py` | Add `@check_usage_limit("bootstrap")` inside `@require_auth` on the bootstrap-project handler. |
| `api/modules/task_gen/routes.py` | Add `@check_usage_limit("task_gen")` inside `@require_auth` on the start-generation handler. |
| `api/modules/spec_gen/routes.py` | Add `@check_usage_limit("spec_gen")` inside `@require_auth` on the generate handler. |
| `api/.env` | Append `DATABASE_URL=sqlite:///./spec_doc.db` if key is absent. This is the only env change; it has a safe code default. |

### To Leave Alone

| Path | Reason |
|---|---|
| `api/openapi.yaml` | Owned by Task 1. The 429 body shape is already committed there; do not re-edit. |
| `api/dtos/models.py` | Generated from `openapi.yaml` via `make generate-dtos`. Never hand-edit. |
| `api/modules/chain/adapter.py` | AI provider boundary (ELA #1). This task has no AI calls. |
| `api/modules/workflows/` | Workflow domain layer. Usage metering does not enter the workflow graph. |
| `api/modules/task_gen/service.py` | `STATE` dict and async job logic are unrelated to metering. |

---

## 4. Implementation Steps

### Step 1: Create `api/db.py` — shared SQLModel engine

**Action**: Create the file only if `api/db.py` does not already exist. If Task 2 created it, inspect it and confirm it exports `get_session()` and `init_db()`; if so, skip to Step 2.

**File**: `api/db.py` (new)

**Pattern**:
```python
import os
from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./spec_doc.db")

_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)


def init_db() -> None:
    """Create all registered SQLModel tables. Call once from create_app()."""
    SQLModel.metadata.create_all(_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Request-scoped session context manager. Closes automatically on exit."""
    with Session(_engine) as session:
        yield session
```

**Verify**: `cd api && python -c "from db import get_session, init_db; print('OK')"` — expect `OK`.

---

### Step 2: Create `api/modules/usage/models.py` — `UsageCounter` SQLModel

**Action**: Create the `modules/usage/` package and its data model.

**File**: `api/modules/usage/__init__.py` (new) — empty except for one comment:
```python
# Usage metering — no Blueprint; no HTTP routes in v1.
```

**File**: `api/modules/usage/models.py` (new)

**Pattern**:
```python
from datetime import date, datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class UsageCounter(SQLModel, table=True):
    __tablename__ = "spec_doc_usage_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "feature", "date", name="uq_usage_counter"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    feature: str = Field(max_length=64)
    date: date = Field(default_factory=date.today)
    count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Verify**: `cd api && python -c "from modules.usage.models import UsageCounter; print(UsageCounter.__tablename__)"` — expect `spec_doc_usage_counters`.

---

### Step 3: Create `api/modules/usage/service.py` — atomic increment and free-tier limits

**Action**: Implement the service layer. The `increment` function uses a single raw SQL `INSERT … ON CONFLICT DO UPDATE RETURNING count` — no Python-level lock, safe for concurrent callers on both SQLite ≥ 3.24 and Postgres.

**File**: `api/modules/usage/service.py` (new)

**Pattern**:
```python
from datetime import date, datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import text
from sqlmodel import Session, select

from modules.usage.models import UsageCounter

DAILY_FREE_TIER_LIMITS: Dict[str, int] = {
    "bootstrap": 3,
    "task_gen": 20,
    "spec_gen": 10,
}


def increment(user_id: str, feature: str, session: Session) -> int:
    """
    Atomic upsert: insert count=1 or increment by 1 on conflict.
    Returns the new count after the operation.
    """
    today = date.today().isoformat()
    now = datetime.utcnow().isoformat()
    result = session.execute(
        text(
            "INSERT INTO spec_doc_usage_counters "
            "(user_id, feature, date, count, created_at, updated_at) "
            "VALUES (:user_id, :feature, :date, 1, :now, :now) "
            "ON CONFLICT (user_id, feature, date) "
            "DO UPDATE SET count = spec_doc_usage_counters.count + 1, "
            "updated_at = :now "
            "RETURNING count"
        ),
        {"user_id": user_id, "feature": feature, "date": today, "now": now},
    )
    session.commit()
    row = result.fetchone()
    return row[0] if row else 1


def get_count(user_id: str, feature: str, session: Session) -> int:
    """Returns today's call count for (user_id, feature). Returns 0 if no row exists."""
    today = date.today()
    row = session.exec(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.feature == feature,
            UsageCounter.date == today,
        )
    ).first()
    return row.count if row else 0


def get_remaining(user_id: str, feature: str, session: Session) -> int:
    """
    Returns remaining calls for today.
    Returns -1 if feature is not in DAILY_FREE_TIER_LIMITS (unmetered).
    Returns 0 when at or past the limit (never negative).
    """
    limit = DAILY_FREE_TIER_LIMITS.get(feature)
    if limit is None:
        return -1
    used = get_count(user_id, feature, session)
    return max(0, limit - used)


def reset_at_utc() -> str:
    """ISO 8601 UTC timestamp for midnight tonight (start of tomorrow).
    Used in 429 bodies so clients know when to retry."""
    tomorrow_midnight = datetime.combine(
        date.today() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    return tomorrow_midnight.isoformat()
```

**Verify**:
```bash
cd api && python -c "
from modules.usage.service import DAILY_FREE_TIER_LIMITS, reset_at_utc
assert DAILY_FREE_TIER_LIMITS == {'bootstrap': 3, 'task_gen': 20, 'spec_gen': 10}
ts = reset_at_utc()
assert ts.endswith('+00:00'), f'expected UTC offset, got {ts}'
print('service OK')
"
```

---

### Step 4: Create `api/modules/usage/middleware.py` — `check_usage_limit` decorator

**Action**: Implement the decorator. Stacking order is `@require_auth` (outer) → `@check_usage_limit` (inner). The decorator reads `g.current_user.plan` set by `require_auth`. Pro plan short-circuits before any DB access. The counter increments only after `_status_code(response) < 400`.

**File**: `api/modules/usage/middleware.py` (new)

**Pattern**:
```python
from functools import wraps
from typing import Any, Callable

from flask import g, jsonify

from db import get_session
from modules.usage.service import (
    DAILY_FREE_TIER_LIMITS,
    get_remaining,
    increment,
    reset_at_utc,
)


def check_usage_limit(feature: str) -> Callable:
    """
    Decorator: enforce the daily free-tier cap for `feature`.

    Usage:
        @blueprint.route("/endpoint", methods=["POST"])
        @require_auth                       # outer — sets g.current_user
        @check_usage_limit("feature_key")  # inner — gates and meters
        def handler(): ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = g.current_user

            # Pro users are not metered — no DB access.
            if getattr(user, "plan", "free") == "pro":
                return fn(*args, **kwargs)

            # Pre-check: reject if already at limit before doing any work.
            with get_session() as session:
                remaining = get_remaining(user.id, feature, session)

            if remaining <= 0:
                limit = DAILY_FREE_TIER_LIMITS.get(feature, 0)
                return jsonify({
                    "error": "usage_limit_reached",
                    "feature": feature,
                    "limit": limit,
                    "reset_at": reset_at_utc(),
                    "upgrade_url": "/upgrade",
                }), 429

            response = fn(*args, **kwargs)

            # Increment only on successful responses — failed calls don't consume quota.
            if _status_code(response) < 400:
                with get_session() as session:
                    increment(user.id, feature, session)

            return response

        return wrapper
    return decorator


def _status_code(response: Any) -> int:
    """Extract the HTTP status code from a Flask handler return value.
    Handles both tuple returns (body, status[, headers]) and Response objects."""
    if isinstance(response, tuple):
        return response[1] if len(response) >= 2 else 200
    return getattr(response, "status_code", 200)
```

**Verify**: `cd api && python -c "from modules.usage.middleware import check_usage_limit, _status_code; print('middleware OK')"` — expect `middleware OK`.

---

### Step 5: Wire `init_db()` into `api/create_app.py`

**Action**: Import `UsageCounter` (so SQLModel registers its table in `metadata`) and call `init_db()` once in the factory. If Task 2 already added a `Subscription` import and `init_db()` call, add only the missing `UsageCounter` import line; do not duplicate `init_db()`.

**File**: `api/create_app.py` (existing — app factory per CODEBASE CONTEXT)

**Pattern** — add at the top of `create_app.py` (after existing imports, before `create_app` function):
```python
# SQLModel table registration — import order matters for metadata.create_all()
from modules.usage.models import UsageCounter  # noqa: F401
# from modules.billing.models import Subscription  # noqa: F401 — uncomment when Task 2 ships

from db import init_db
```

And inside the `create_app()` function body, after blueprint registration:
```python
    init_db()   # idempotent — safe to call on every startup
    return app
```

**Verify**:
```bash
cd api && python -c "
from create_app import create_app
app = create_app()
import sqlite3, os
conn = sqlite3.connect('spec_doc.db')
tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
assert 'spec_doc_usage_counters' in tables, f'table missing; found: {tables}'
conn.close()
print('init_db OK — spec_doc_usage_counters created')
"
```

---

### Step 6: Apply `@check_usage_limit` to gated routes

**Action**: Add the decorator to the three gated route handlers. For each file: open it, find the target handler, and insert `@check_usage_limit("feature_key")` between `@require_auth` and `def handler_name()`. Import `check_usage_limit` at the top of each routes file.

**Add to imports in each target routes file**:
```python
from modules.usage.middleware import check_usage_limit
```

**File**: `api/modules/ai/routes.py` — bootstrap-project handler (existing, per CODEBASE CONTEXT)

```python
# Before:
@ai_bp.route("/bootstrap-project", methods=["POST"])
@require_auth
def bootstrap_project():

# After:
@ai_bp.route("/bootstrap-project", methods=["POST"])
@require_auth
@check_usage_limit("bootstrap")
def bootstrap_project():
```

**File**: `api/modules/task_gen/routes.py` — generate-task handler (existing, per CODEBASE CONTEXT)

```python
# Before:
@task_gen_bp.route("/generate-task", methods=["POST"])
@require_auth
def start_generation():

# After:
@task_gen_bp.route("/generate-task", methods=["POST"])
@require_auth
@check_usage_limit("task_gen")
def start_generation():
```

**File**: `api/modules/spec_gen/routes.py` — spec-gen generate handler (existing, per CODEBASE CONTEXT)

```python
# Before:
@spec_gen_bp.route("/generate", methods=["POST"])
@require_auth
def generate():

# After:
@spec_gen_bp.route("/generate", methods=["POST"])
@require_auth
@check_usage_limit("spec_gen")
def generate():
```

**Verify** (one command — confirms decorators are applied, no import errors, and the test suite still sees the same number of routes):
```bash
cd api && python -c "
from create_app import create_app
app = create_app()
rules = [str(r) for r in app.url_map.iter_rules()]
print('routes registered:', len(rules))
" && python -m pytest --tb=short -q -x 2>&1 | tail -5
```

---

## 5. Tests

Create `api/modules/usage/tests/__init__.py` (empty) and the two test files below. The repo's framework is pytest (confirmed by `make test` → `python -m pytest`). No mocks framework other than `unittest.mock` is required.

### `api/modules/usage/tests/test_service.py`

```python
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from modules.usage.models import UsageCounter
from modules.usage.service import (
    DAILY_FREE_TIER_LIMITS,
    get_count,
    get_remaining,
    increment,
    reset_at_utc,
)


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# --- increment ---

def test_increment_creates_row_with_count_one(session):
    count = increment("u1", "bootstrap", session)
    assert count == 1, "first call should return count=1"


def test_increment_adds_to_existing_row(session):
    increment("u1", "bootstrap", session)
    count = increment("u1", "bootstrap", session)
    assert count == 2, "second call should return count=2"


def test_increment_isolates_by_user(session):
    increment("u1", "bootstrap", session)
    count = increment("u2", "bootstrap", session)
    assert count == 1, "different user should start at 1"


def test_increment_isolates_by_feature(session):
    increment("u1", "bootstrap", session)
    count = increment("u1", "task_gen", session)
    assert count == 1, "different feature should start at 1"


# --- get_count ---

def test_get_count_returns_zero_for_new_user(session):
    assert get_count("u1", "bootstrap", session) == 0


def test_get_count_returns_current_value(session):
    increment("u1", "bootstrap", session)
    increment("u1", "bootstrap", session)
    assert get_count("u1", "bootstrap", session) == 2


# --- get_remaining ---

def test_get_remaining_fresh_user_returns_full_limit(session):
    remaining = get_remaining("u1", "bootstrap", session)
    assert remaining == DAILY_FREE_TIER_LIMITS["bootstrap"]


def test_get_remaining_decrements_after_increment(session):
    increment("u1", "bootstrap", session)
    remaining = get_remaining("u1", "bootstrap", session)
    assert remaining == DAILY_FREE_TIER_LIMITS["bootstrap"] - 1


def test_get_remaining_returns_zero_at_limit(session):
    limit = DAILY_FREE_TIER_LIMITS["bootstrap"]
    for _ in range(limit):
        increment("u1", "bootstrap", session)
    assert get_remaining("u1", "bootstrap", session) == 0, "should not go negative"


def test_get_remaining_returns_minus_one_for_unknown_feature(session):
    assert get_remaining("u1", "not_a_feature", session) == -1


# --- reset_at_utc ---

def test_reset_at_utc_returns_tomorrows_midnight_utc():
    result = reset_at_utc()
    dt = datetime.fromisoformat(result)
    tomorrow = date.today() + timedelta(days=1)
    assert dt.tzinfo is not None, "must be timezone-aware"
    assert dt.utcoffset().total_seconds() == 0, "must be UTC"
    assert dt.date() == tomorrow, "must be tomorrow's date"
    assert dt.hour == 0 and dt.minute == 0 and dt.second == 0, "must be midnight"


# --- DAILY_FREE_TIER_LIMITS constant ---

def test_daily_free_tier_limits_has_all_gated_features():
    assert DAILY_FREE_TIER_LIMITS == {
        "bootstrap": 3,
        "task_gen": 20,
        "spec_gen": 10,
    }, "cap values must match architecture decision"
```

### `api/modules/usage/tests/test_middleware.py`

```python
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g, jsonify

from modules.usage.middleware import _status_code, check_usage_limit


def make_user(plan: str = "free", user_id: str = "u1") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.plan = plan
    return user


@pytest.fixture
def app():
    _app = Flask(__name__)
    _app.config["TESTING"] = True
    return _app


@pytest.fixture
def fake_get_session():
    mock_session = MagicMock()

    @contextmanager
    def _ctx():
        yield mock_session

    return _ctx


# --- pro user ---

def test_pro_user_bypasses_all_limit_checks(app, fake_get_session):
    with app.test_request_context("/"):
        g.current_user = make_user(plan="pro")
        with patch("modules.usage.middleware.get_session", fake_get_session):
            with patch("modules.usage.middleware.get_remaining") as mock_remaining:

                @check_usage_limit("bootstrap")
                def handler():
                    return jsonify({}), 200

                body, status = handler()
                assert status == 200
                mock_remaining.assert_not_called()


# --- free user at limit ---

def test_free_user_at_limit_returns_429(app, fake_get_session):
    with app.test_request_context("/"):
        g.current_user = make_user(plan="free")
        with patch("modules.usage.middleware.get_session", fake_get_session):
            with patch("modules.usage.middleware.get_remaining", return_value=0):
                with patch("modules.usage.middleware.increment") as mock_inc:

                    @check_usage_limit("bootstrap")
                    def handler():
                        return jsonify({}), 200

                    body, status = handler()
                    assert status == 429
                    data = body.get_json()
                    assert data["error"] == "usage_limit_reached"
                    assert data["feature"] == "bootstrap"
                    assert isinstance(data["limit"], int) and data["limit"] > 0
                    assert "reset_at" in data
                    assert data["upgrade_url"] == "/upgrade"
                    mock_inc.assert_not_called()


# --- free user under limit ---

def test_free_user_under_limit_calls_handler_and_increments(app, fake_get_session):
    with app.test_request_context("/"):
        g.current_user = make_user(plan="free")
        with patch("modules.usage.middleware.get_session", fake_get_session):
            with patch("modules.usage.middleware.get_remaining", return_value=2):
                with patch("modules.usage.middleware.increment") as mock_inc:

                    @check_usage_limit("bootstrap")
                    def handler():
                        return jsonify({"result": "ok"}), 200

                    body, status = handler()
                    assert status == 200
                    assert body.get_json()["result"] == "ok"
                    mock_inc.assert_called_once()


# --- no increment on error responses ---

def test_counter_not_incremented_on_400_response(app, fake_get_session):
    with app.test_request_context("/"):
        g.current_user = make_user(plan="free")
        with patch("modules.usage.middleware.get_session", fake_get_session):
            with patch("modules.usage.middleware.get_remaining", return_value=2):
                with patch("modules.usage.middleware.increment") as mock_inc:

                    @check_usage_limit("bootstrap")
                    def handler():
                        return jsonify({"error": "bad input"}), 400

                    _, status = handler()
                    assert status == 400
                    mock_inc.assert_not_called()


def test_counter_not_incremented_on_500_response(app, fake_get_session):
    with app.test_request_context("/"):
        g.current_user = make_user(plan="free")
        with patch("modules.usage.middleware.get_session", fake_get_session):
            with patch("modules.usage.middleware.get_remaining", return_value=3):
                with patch("modules.usage.middleware.increment") as mock_inc:

                    @check_usage_limit("bootstrap")
                    def handler():
                        return jsonify({"error": "internal"}), 500

                    _, status = handler()
                    assert status == 500
                    mock_inc.assert_not_called()


# --- _status_code helper ---

def test_status_code_from_two_tuple():
    assert _status_code((MagicMock(), 200)) == 200
    assert _status_code((MagicMock(), 429)) == 429


def test_status_code_from_three_tuple():
    assert _status_code((MagicMock(), 400, {})) == 400


def test_status_code_from_response_object():
    resp = MagicMock()
    resp.status_code = 201
    assert _status_code(resp) == 201
```

---

## 6. Commit Plan

**Executor instruction**: run the commit for each step immediately after completing that step — not at the end of the task.

1. **`feat(db): add SQLModel engine, session factory, and init_db`** — after Step 1 completes — files: `api/db.py`

2. **`feat(usage): add UsageCounter model`** — after Step 2 completes — files: `api/modules/usage/__init__.py`, `api/modules/usage/models.py`

3. **`feat(usage): add service layer — atomic increment, free-tier caps`** — after Step 3 completes — files: `api/modules/usage/service.py`

4. **`feat(usage): add check_usage_limit decorator`** — after Step 4 completes — files: `api/modules/usage/middleware.py`

5. **`feat(usage): wire init_db and register UsageCounter table`** — after Step 5 completes — files: `api/create_app.py`

6. **`feat(usage): gate bootstrap, task_gen, and spec_gen routes`** — after Step 6 completes — files: `api/modules/ai/routes.py`, `api/modules/task_gen/routes.py`, `api/modules/spec_gen/routes.py`

7. **`test(usage): add service and middleware test coverage`** — after all tests pass — files: `api/modules/usage/tests/__init__.py`, `api/modules/usage/tests/test_service.py`, `api/modules/usage/tests/test_middleware.py`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation (e.g., `Deviations: require_auth absent — @check_usage_limit skipped on ai/routes.py`).

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q 2>&1 | tail -5
```

**Expected delta**: 624 → 643 passing (19 new tests: 12 service + 7 middleware). Zero pre-existing tests broken.

Secondary check — confirm structural isolation (no module outside usage+tests imports `modules.usage.middleware` or `db` directly except through the allowed callers):
```bash
grep -r "from modules.usage.middleware" api/ \
  --include="*.py" \
  | grep -v "modules/usage/" \
  | grep -v "modules/ai/routes.py" \
  | grep -v "modules/task_gen/routes.py" \
  | grep -v "modules/spec_gen/routes.py"
# Expect: no output. Any unexpected line is a coupling violation.
```

---

## 8. Rollback

**Per-step rollback**: each commit above is independently revertible:
```bash
git revert <sha> --no-edit
```
Commits are fine-grained, so reverting Step 6 (route gating) removes the decorators without touching the module itself. Reverting Step 5 (`init_db`) drops the table-creation call without losing the model.

**Per-branch rollback**: if verification fails catastrophically after all steps:
```bash
git reset --hard <pre-task-sha>   # recover to the exact state before Step 1
```
Record `<pre-task-sha>` by running `git rev-parse HEAD` during pre-flight before touching any file.

**Database cleanup**: if a `spec_doc.db` was created during development and you want a clean state:
```bash
rm -f api/spec_doc.db   # sqlite file only; no schema migration is required on restart
```

---

## 9. Deviations Allowed

- **`api/db.py` already exists (Task 2 created it)** → verify it exports `get_session()` and `init_db()` with matching signatures; if so, skip Step 1 entirely. If signatures differ, reconcile and log the deviation.
- **`require_auth` not yet applied to a target route** → add `@require_auth` as the outermost decorator in the same commit as `@check_usage_limit`. Log the deviation in the commit body. Do NOT apply `@check_usage_limit` without `@require_auth` — accessing `g.current_user` without auth in place will raise `AttributeError` at runtime.
- **Route handler names differ from the patterns shown in Step 6** → identify the correct handler by reading the routes file; apply the decorator to the correct function. Log the name discrepancy in the commit body.
- **`spec_gen/routes.py` is not at the expected path** → run `grep -r "spec-gen/generate" api/` to locate the actual handler; apply decorator there. Log the path difference.
- **Step 6 unlocks a simplification** (e.g., all three imports can be batched in one line) → take it; log deviation.
- **Side-effect required** (e.g., Postgres migration file, `git push`) → STOP, mark `[REQUIRES APPROVAL]`, and surface it before proceeding.

---

## 10. Out of Scope

This task ships the metering module and wires it to the three AI endpoints. It does not build any user-facing quota display, billing integration, or additional route guards. The following work is explicitly deferred and should not be absorbed by an executor who finds it "obvious":

- **Angular usage-meter pill and 429 interceptor** — belong to Task 4 (Angular billing surface); Task 3 only produces the 429 JSON body those components will consume.
- **`invoice.payment_failed` → `User.plan` write** (the open "past-due access rule" question from the architecture) — must be resolved as a pre-condition of Task 2's webhook handler table; Task 3 reads `User.plan` as given and does not define the write path.
- **Env-variable-driven cap values** — `DAILY_FREE_TIER_LIMITS` is a constant dict; moving it to env vars is deferred until conversion-rate data from the first 50 free users justifies a no-redeploy tuning workflow.
- **`UsageCounter` daily date-rollover cleanup** — counters accumulate indefinitely; archiving or pruning old rows is deferred until table size becomes observable (well beyond v1 user volume).
- **Per-org / shared usage pools** — single-user counters only; a workspaces epic would own this if ever requested.
- **Sixth webhook event confirmation** (Task 2 pre-condition) — out of scope here; only affects `modules/billing/`.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding the blast radius of this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for the metering + billing split
- [Epic](./epic.md) – Full task scope and parallel-task ordering
- [Timeline](./timeline.md) – Update task status to ✅ after verification passes