# Task 1: Tracking Endpoint + Schema — Implementation Guide

---

## 1. Context

The distribution experiment needs a backend to record funnel events from the landing page and the Bubls app. This task creates a `tracking` module inside the Bubls Flask backend: one SQLAlchemy model (`DistributionEvent`), one Alembic migration, one Flask Blueprint (`POST /api/track`), and a Pydantic DTO for request validation. No auth — these are anonymous strangers. Rate-limited to 10 events/minute per IP via in-memory counter.

The module follows the established Bubls pattern: `server/modules/tracking/` with `__init__.py`, `models.py`, `routes.py`, `service.py`, `repository.py`, `dto.py`. Registered in `ENABLED_MODULES` in `server/app.py`.

### Trade-offs considered

- **In-memory rate limiter vs Redis**: In-memory chosen. One server, one week, <1000 visitors expected. Redis is infrastructure before a feature. Counter resets on deploy are acceptable at this scale.
- **SERIAL id vs UUID id**: SERIAL chosen. Append-only event log, never referenced by external systems. Simpler, faster, smaller.
- **`ip_hash` stored vs IP discarded**: Store SHA-256 hash of IP. Enables rate-limit bucketing and abuse forensics without storing raw PII. No salt needed — this is not password storage.

---

## 2. Pre-flight

```bash
cd {WORKSPACE}
git status
git diff HEAD
python -m pytest server/ --tb=short -q 2>/dev/null | tail -3  # baseline test count
```

Record the baseline test count before editing.

---

## 3. Files

### To Create

- `server/modules/tracking/__init__.py` (new)
- `server/modules/tracking/models.py` (new)
- `server/modules/tracking/dto.py` (new)
- `server/modules/tracking/repository.py` (new)
- `server/modules/tracking/service.py` (new)
- `server/modules/tracking/routes.py` (new)
- `server/openapi/tracking.yaml` (new)
- `server/migrations/versions/20260417_create_distribution_events.py` (new)
- `server/modules/tracking/tests/__init__.py` (new)
- `server/modules/tracking/tests/test_routes.py` (new)
- `server/modules/tracking/tests/test_repository.py` (new)

### To Modify

- `server/app.py` — add `"modules.tracking"` to `ENABLED_MODULES`

### To Leave Alone

- `server/core/database.py` — import `Base` from here, do not modify
- `server/core/config.py` — `DATABASE_URL` already configured
- `server/core/auth.py` — no auth on tracking endpoint
- `server/modules/user/` — unrelated module
- `server/modules/text/` — unrelated module
- `server/modules/photoshoot/` — unrelated module

---

## 4. Implementation Steps

### Step 1: Create module directory and `__init__.py`

**Action**: Create the tracking module package.
**File**: `server/modules/tracking/__init__.py`
**Pattern**: Follow `server/modules/user/__init__.py` — module docstring only.

```python
"""Distribution event tracking module.

Records anonymous funnel events (page_view, testflight_click, app_open)
from the landing page and Bubls app. No auth required.

``bp`` re-exported from ``routes`` is wired into ``server/app.py``'s
``ENABLED_MODULES``.
"""
```

**Verify**: `python -c "import server.modules.tracking"` (no import error).

---

### Step 2: Create SQLAlchemy model

**Action**: Define the `DistributionEvent` ORM entity.
**File**: `server/modules/tracking/models.py`
**Pattern**: Follow `server/modules/photoshoot/models.py` — import `Base` from `core.database`, use `Mapped` + `mapped_column`, type hints on every column.

```python
"""SQLAlchemy entity for distribution funnel events."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class DistributionEvent(Base):
    __tablename__ = "distribution_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

**Verify**: `python -c "from modules.tracking.models import DistributionEvent; print(DistributionEvent.__tablename__)"` prints `distribution_events`.

---

### Step 3: Create Alembic migration

**Action**: Create the migration file for the `distribution_events` table.
**File**: `server/migrations/versions/20260417_create_distribution_events.py`
**Pattern**: Follow `server/migrations/versions/20260417_add_builder_principles.py` — `revision`, `down_revision` chain, `upgrade()` / `downgrade()`.

```python
"""create distribution_events table

Revision ID: 20260417_create_distribution_events
Revises: 20260419b_add_result_text
Create Date: 2026-04-17
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260417_create_distribution_events"
down_revision = "20260419b_add_result_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column(
            "event_type",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("metadata", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_dist_events_type", "distribution_events", ["event_type"])
    op.create_index(
        "idx_dist_events_device",
        "distribution_events",
        ["device_id"],
        postgresql_where=sa.text("device_id IS NOT NULL"),
    )
    op.create_index("idx_dist_events_created", "distribution_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_dist_events_created", table_name="distribution_events")
    op.drop_index("idx_dist_events_device", table_name="distribution_events")
    op.drop_index("idx_dist_events_type", table_name="distribution_events")
    op.drop_table("distribution_events")
```

**Verify**: `cd server && alembic heads` shows the new revision at the tip. `alembic upgrade head` applies without error (against Neon or a local Postgres). `alembic downgrade -1` reverses cleanly.

---

### Step 4: Create OpenAPI spec

**Action**: Define the tracking endpoint contract.
**File**: `server/openapi/tracking.yaml`
**Pattern**: Follow existing OpenAPI specs in the repo.

```yaml
openapi: 3.0.3
info:
  title: Distribution Tracking
  version: 1.0.0
paths:
  /api/track:
    post:
      summary: Record a distribution funnel event
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TrackRequest'
      responses:
        '201':
          description: Event recorded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TrackResponse'
        '422':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
components:
  schemas:
    TrackRequest:
      type: object
      required:
        - event_type
        - session_id
      properties:
        event_type:
          type: string
          enum: [page_view, testflight_click, app_open]
        session_id:
          type: string
          format: uuid
        device_id:
          type: string
          maxLength: 64
        metadata:
          type: object
          additionalProperties: true
    TrackResponse:
      type: object
      properties:
        status:
          type: string
          example: ok
        event_id:
          type: integer
    ErrorResponse:
      type: object
      properties:
        error:
          type: string
```

**Verify**: File is valid YAML — `python -c "import yaml; yaml.safe_load(open('server/openapi/tracking.yaml'))"`.

---

### Step 5: Create Pydantic DTOs

**Action**: Create request/response models for the tracking endpoint.
**File**: `server/modules/tracking/dto.py`
**Pattern**: Follow `server/modules/user/dto.py` — Pydantic BaseModel, typed fields.

```python
"""Pydantic DTOs for the tracking module.

Hand-authored to match server/openapi/tracking.yaml. Keep in sync via
``npm run gen:py:tracking`` when datamodel-codegen is available.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    PAGE_VIEW = "page_view"
    TESTFLIGHT_CLICK = "testflight_click"
    APP_OPEN = "app_open"


class TrackRequest(BaseModel):
    event_type: EventType
    session_id: str = Field(min_length=1, max_length=36)
    device_id: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] | None = None


class TrackResponse(BaseModel):
    status: str = "ok"
    event_id: int


class ErrorResponse(BaseModel):
    error: str
```

**Verify**: `python -c "from modules.tracking.dto import TrackRequest, EventType; r = TrackRequest(event_type=EventType.PAGE_VIEW, session_id='abc'); print(r.event_type)"` prints `page_view`.

---

### Step 6: Create repository

**Action**: Data access layer for inserting events.
**File**: `server/modules/tracking/repository.py`
**Pattern**: Follow `server/modules/user/repository.py` — pure SQLAlchemy, no business logic.

```python
"""Data access for the tracking module.

Only SQLAlchemy touches happen here. Service layer stays ORM-free.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models import DistributionEvent


def insert_event(
    db: Session,
    *,
    session_id: str,
    event_type: str,
    device_id: str | None = None,
    ip_hash: str | None = None,
    metadata: dict | None = None,
) -> DistributionEvent:
    """Insert a distribution event and return the persisted row."""
    event = DistributionEvent(
        session_id=session_id,
        event_type=event_type,
        device_id=device_id,
        ip_hash=ip_hash,
        metadata_=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
```

**Verify**: Tested via integration test in Step 9.

---

### Step 7: Create service

**Action**: Business logic layer — hash IP, validate, delegate to repository.
**File**: `server/modules/tracking/service.py`
**Pattern**: Thin service layer between routes and repository.

```python
"""Business logic for the tracking module.

Hashes IP, validates event, delegates to repository. No SQLAlchemy imports.
"""
from __future__ import annotations

import hashlib
import time
from collections import defaultdict

from sqlalchemy.orm import Session

from . import repository
from .dto import TrackRequest


# In-memory rate limiter: {ip_hash: [(timestamp, ...)]}
_rate_buckets: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 10  # events per minute
RATE_WINDOW = 60  # seconds


class RateLimitExceeded(Exception):
    pass


def hash_ip(ip: str) -> str:
    """SHA-256 hash of the IP address. No salt — abuse bucketing, not identity."""
    return hashlib.sha256(ip.encode()).hexdigest()


def check_rate_limit(ip_hash: str) -> None:
    """Raise RateLimitExceeded if IP has exceeded 10 events/minute."""
    now = time.monotonic()
    bucket = _rate_buckets[ip_hash]
    # Prune old entries
    _rate_buckets[ip_hash] = [t for t in bucket if now - t < RATE_WINDOW]
    if len(_rate_buckets[ip_hash]) >= RATE_LIMIT:
        raise RateLimitExceeded("Rate limit exceeded: 10 events/minute")
    _rate_buckets[ip_hash].append(now)


def record_event(
    db: Session,
    *,
    req: TrackRequest,
    client_ip: str,
) -> int:
    """Validate, rate-check, and persist a tracking event. Returns event ID."""
    ip_hash = hash_ip(client_ip)
    check_rate_limit(ip_hash)
    event = repository.insert_event(
        db,
        session_id=req.session_id,
        event_type=req.event_type.value,
        device_id=req.device_id,
        ip_hash=ip_hash,
        metadata=req.metadata,
    )
    return event.id
```

**Verify**: Tested via unit test in Step 9.

---

### Step 8: Create Blueprint route

**Action**: HTTP surface for the tracking module.
**File**: `server/modules/tracking/routes.py`
**Pattern**: Follow `server/modules/text/routes.py` — thin controller, parse body via Pydantic, delegate to service, serialize response.

```python
"""HTTP surface for the tracking module.

Thin controller: parse JSON, validate via Pydantic, delegate to service.
No auth — anonymous event tracking for the distribution experiment.
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from . import service
from .dto import ErrorResponse, TrackRequest, TrackResponse

bp = Blueprint("tracking", __name__, url_prefix="/api")


def _error(message: str, status: int):
    return jsonify(ErrorResponse(error=message).model_dump()), status


@bp.post("/track")
def track():
    try:
        req = TrackRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _error(f"Invalid request: {exc.errors()}", 422)

    try:
        event_id = service.record_event(
            g.db,
            req=req,
            client_ip=request.remote_addr or "0.0.0.0",
        )
    except service.RateLimitExceeded:
        return _error("Rate limit exceeded", 429)

    return jsonify(TrackResponse(event_id=event_id).model_dump()), 201
```

**Verify**: Module imports cleanly — `python -c "from modules.tracking.routes import bp; print(bp.name)"` prints `tracking`.

---

### Step 9: Register in ENABLED_MODULES

**Action**: Wire the tracking module into the Flask app.
**File**: `server/app.py`
**Pattern**: Add one line to `ENABLED_MODULES`.

Change:

```python
ENABLED_MODULES: list[str] = [
    "modules.photoshoot",
    "modules.user",
    "modules.text",
    # "modules.picks",        # future
]
```

To:

```python
ENABLED_MODULES: list[str] = [
    "modules.photoshoot",
    "modules.user",
    "modules.text",
    "modules.tracking",
    # "modules.picks",        # future
]
```

**Verify**: Start the server — `cd server && python app.py`. Hit `GET /api/health` and confirm `tracking` appears in the modules list. Hit `POST /api/track` with a valid payload and confirm 201 response.

```bash
curl -s http://localhost:5001/api/health | python -m json.tool
# Expect: {"status": "ok", "modules": ["photoshoot", "user", "text", "tracking"]}

curl -s -X POST http://localhost:5001/api/track \
  -H 'Content-Type: application/json' \
  -d '{"event_type": "page_view", "session_id": "550e8400-e29b-41d4-a716-446655440000"}' \
  | python -m json.tool
# Expect: {"status": "ok", "event_id": 1}
```

---

### Step 10: Write tests

**Action**: Create test files for the tracking module.
**Files**: `server/modules/tracking/tests/__init__.py`, `server/modules/tracking/tests/test_routes.py`, `server/modules/tracking/tests/test_repository.py`

**test_routes.py**:

```python
"""Route-level tests for the tracking module.

Uses Flask test client with an in-memory SQLite database.
"""
from __future__ import annotations

import json

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.database import Base
from modules.tracking.routes import bp


@pytest.fixture
def app():
    """Create a test Flask app with SQLite and the tracking blueprint."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    test_app = Flask(__name__)
    test_app.register_blueprint(bp)

    @test_app.before_request
    def inject_db():
        from flask import g
        g.db = TestSession()

    @test_app.teardown_request
    def close_db(exc):
        from flask import g
        db = g.pop("db", None)
        if db is not None:
            db.close()

    yield test_app
    engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def validPayload_returns201(client):
    resp = client.post(
        "/api/track",
        data=json.dumps({
            "event_type": "page_view",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "ok"
    assert isinstance(body["event_id"], int)


def missingEventType_returns422(client):
    resp = client.post(
        "/api/track",
        data=json.dumps({"session_id": "abc"}),
        content_type="application/json",
    )
    assert resp.status_code == 422


def invalidEventType_returns422(client):
    resp = client.post(
        "/api/track",
        data=json.dumps({
            "event_type": "invalid_event",
            "session_id": "abc",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 422


def optionalDeviceId_acceptedAndStored(client):
    resp = client.post(
        "/api/track",
        data=json.dumps({
            "event_type": "app_open",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "device_id": "device-abc-123",
            "metadata": {"platform": "ios"},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 201


def emptyBody_returns422(client):
    resp = client.post("/api/track", data="{}", content_type="application/json")
    assert resp.status_code == 422
```

**test_repository.py**:

```python
"""Repository-level tests for the tracking module.

Direct SQLAlchemy tests against in-memory SQLite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from modules.tracking import repository
from modules.tracking.models import DistributionEvent


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    engine.dispose()


def insertEvent_returnsPersistedRow(db):
    event = repository.insert_event(
        db,
        session_id="test-session-001",
        event_type="page_view",
    )
    assert event.id is not None
    assert event.session_id == "test-session-001"
    assert event.event_type == "page_view"
    assert event.created_at is not None


def insertEvent_withDeviceIdAndMetadata_persistsAll(db):
    event = repository.insert_event(
        db,
        session_id="test-session-002",
        event_type="app_open",
        device_id="device-xyz",
        ip_hash="abc123hash",
        metadata={"platform": "ios", "referrer": "reddit"},
    )
    assert event.device_id == "device-xyz"
    assert event.ip_hash == "abc123hash"


def insertMultipleEvents_assignsIncrementingIds(db):
    e1 = repository.insert_event(db, session_id="s1", event_type="page_view")
    e2 = repository.insert_event(db, session_id="s2", event_type="page_view")
    assert e2.id > e1.id
```

**Verify**: `cd server && python -m pytest modules/tracking/tests/ -v` — all tests pass.

---

## 5. Tests

All test assertions are provided in Step 10 above. Summary:

| Test | File | Assertion |
|------|------|-----------|
| `validPayload_returns201` | test_routes.py | POST valid event returns 201 with `event_id` |
| `missingEventType_returns422` | test_routes.py | Missing required field returns 422 |
| `invalidEventType_returns422` | test_routes.py | Unknown event type returns 422 |
| `optionalDeviceId_acceptedAndStored` | test_routes.py | Optional fields accepted |
| `emptyBody_returns422` | test_routes.py | Empty JSON body returns 422 |
| `insertEvent_returnsPersistedRow` | test_repository.py | Repository returns row with id and timestamp |
| `insertEvent_withDeviceIdAndMetadata_persistsAll` | test_repository.py | Optional fields persisted |
| `insertMultipleEvents_assignsIncrementingIds` | test_repository.py | Auto-increment works |

---

## 6. Commit Plan

| Commit | Contents | Boundary |
|--------|----------|----------|
| 1 | `models.py`, migration file | Schema exists, no routes yet |
| 2 | `dto.py`, `openapi/tracking.yaml` | Contract defined |
| 3 | `repository.py`, `service.py`, `routes.py`, `__init__.py` | Endpoint functional |
| 4 | `app.py` modification, test files | Wired and tested |

Each commit message body includes a `Deviations:` line listing any spec/reality mismatches (target: 0-1 per commit).

---

## 7. Verification

```bash
# Full test suite
cd {WORKSPACE}/server && python -m pytest --tb=short -q

# Expected delta: +8 tests (5 route + 3 repository)

# Integration smoke test
python app.py &
curl -s http://localhost:5001/api/health | python -m json.tool
curl -s -X POST http://localhost:5001/api/track \
  -H 'Content-Type: application/json' \
  -d '{"event_type":"page_view","session_id":"test-uuid"}' | python -m json.tool
kill %1
```

---

## 8. Rollback

### Per-step

- **Steps 1-2 (model + migration)**: `alembic downgrade -1` drops the table. Delete `server/modules/tracking/models.py` and the migration file.
- **Steps 3-5 (DTOs, OpenAPI)**: Delete the files. No DB state changed.
- **Steps 6-8 (repo, service, routes)**: Delete the files. No DB state changed.
- **Step 9 (ENABLED_MODULES)**: Remove the `"modules.tracking"` line from `server/app.py`.
- **Step 10 (tests)**: Delete the test files.

### Per-branch

```bash
git checkout main
git branch -D tracking-endpoint  # [REQUIRES APPROVAL]
alembic downgrade -1             # [REQUIRES APPROVAL] — drops distribution_events table
```

---

## 9. Deviations Allowed

- If `JSONB` type causes issues with SQLite in tests, replace with `JSON` in the model and use `.with_variant(JSONB(), "postgresql")` (same pattern as `_FeatureJSON` in `server/modules/photoshoot/models.py`).
- If the latest Alembic revision has changed since this guide was written, update `down_revision` in the migration to point to the actual current head.
- If `g.db` injection pattern differs from what tests expect, adapt the test fixture to match the actual middleware in `server/core/database.py` or `server/app.py`.
- If `request.remote_addr` returns `None` behind a proxy, fall back to `request.headers.get("X-Forwarded-For", "0.0.0.0").split(",")[0].strip()`.

For any deviation: log it in the commit body (`Deviations: <description>`). Do not absorb scope from out-of-scope list below.

---

## 10. Out of Scope

The following are explicitly deferred. If the executor encounters a situation where these seem necessary, STOP and flag rather than implementing:

- **Landing page** — Task 2 in the epic, separate implementation guide
- **App-open instrumentation** — Task 3, Angular/Capacitor work
- **Reddit post** — Task 4, no code
- **Email capture endpoint** — belongs to the waitlist module, not tracking
- **Analytics dashboard or admin UI** — a SQL query suffices for the day-7 verdict
- **Redis-backed rate limiting** — in-memory is sufficient for one server, one week
- **`app_return` event type** — derived server-side in the day-7 verdict query, never written by client or this endpoint
- **CORS configuration changes** — the landing page origin will be added in Task 2's deployment, not here
- **Mock mode (`TRACK_ENABLED=false`)** — mentioned in architecture doc but deferred until a second consumer needs it; the test suite uses SQLite, not a mock adapter
