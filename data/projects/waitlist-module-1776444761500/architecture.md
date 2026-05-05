---
sidebar_position: 3
---

# Waitlist Module — Solution Architecture

**Purpose**: Technical design for the waitlist module inside the Bubls Flask backend.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

A single Flask module at `server/modules/waitlist/` following the established Bubls pattern: SQLAlchemy model, Pydantic DTOs generated from OpenAPI, Blueprint routes, repository for data access, service for business logic. Registered in `ENABLED_MODULES` in `server/app.py`. One Alembic migration creates the table; a second data migration ports Trendfy subscribers.

The module is intentionally minimal. One endpoint (`POST /api/waitlist/signup`), one table (`waitlist_signups`), one model (`WaitlistSignup`). No auth, no admin surface, no email sending. Those capabilities can be added later as separate tasks without changing the module's structure.

```
Landing Page / App
    │
    ▼
POST /api/waitlist/signup
    │ (Flask Blueprint, no auth)
    ▼
waitlist/routes.py → service.py → repository.py
    │
    ▼
Neon Postgres: waitlist_signups
    │
    ├── source='landing_page' (new signups)
    └── source='trendfy' (ported from bubls_subscribers)
```

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Module pattern | `server/modules/waitlist/` with `__init__.py`, `models.py`, `routes.py`, `service.py`, `repository.py`, `dto.py` |
| Always ORM | SQLAlchemy model `WaitlistSignup`, no raw SQL |
| Alembic for migrations | Schema migration + data migration for Trendfy port |
| OpenAPI-first | `server/openapi/waitlist.yaml` generates `dto.py` |
| Flask, minimal | One endpoint, ~20 lines in routes.py |
| Neon Postgres for everything | Same instance as all other Bubls data |

---

## Component Design

### Module Layout

```
server/modules/waitlist/
├── __init__.py          # Module docstring
├── models.py            # SQLAlchemy: WaitlistSignup
├── routes.py            # Blueprint: POST /api/waitlist/signup
├── service.py           # Business logic: validate + delegate
├── repository.py        # Data access: insert, check duplicate
└── dto.py               # Pydantic: SignupRequest, SignupResponse, ErrorResponse
```

### SQLAlchemy Model

```python
class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="landing_page")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

Uses `Integer` primary key (not UUID) because waitlist signups are append-only, never referenced by ID from external systems. Auto-increment is simpler and more efficient for a monotonically growing table.

### Database Schema

```sql
CREATE TABLE waitlist_signups (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR NOT NULL UNIQUE,
    source      VARCHAR(30) NOT NULL DEFAULT 'landing_page',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_waitlist_source ON waitlist_signups(source);
```

The unique constraint on `email` prevents duplicates at the DB level. The `source` index supports filtering queries (e.g., "how many Trendfy subscribers vs landing page signups").

### OpenAPI Spec

```yaml
openapi: 3.0.3
info:
  title: Waitlist Module
  version: 1.0.0
paths:
  /api/waitlist/signup:
    post:
      summary: Register email for waitlist
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email]
              properties:
                email:
                  type: string
                  format: email
      responses:
        '201':
          description: Signup created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SignupResponse'
        '409':
          description: Email already registered
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '422':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
components:
  schemas:
    SignupResponse:
      type: object
      properties:
        id:
          type: integer
        email:
          type: string
        source:
          type: string
        created_at:
          type: string
          format: date-time
    ErrorResponse:
      type: object
      properties:
        error:
          type: string
```

### Blueprint Route

```python
bp = Blueprint("waitlist", __name__, url_prefix="/api/waitlist")

@bp.post("/signup")
def signup():
    # Parse → validate → delegate → serialize
    # ~15 lines total
```

No auth decorators. Rate-limited to 5 requests/minute per IP using an in-memory counter (same rationale as distribution tracking: one server, low traffic, counter resets on deploy are acceptable).

### Trendfy Data Migration

Alembic data migration reads from `bubls_subscribers` and inserts into `waitlist_signups`:

```python
def upgrade():
    conn = op.get_bind()
    rows = conn.execute(text("SELECT email, created_at FROM bubls_subscribers"))
    for row in rows:
        conn.execute(
            text("""
                INSERT INTO waitlist_signups (email, source, created_at)
                VALUES (:email, 'trendfy', :created_at)
                ON CONFLICT (email) DO NOTHING
            """),
            {"email": row.email, "created_at": row.created_at}
        )
```

This runs exactly once as part of the normal Alembic upgrade. `ON CONFLICT DO NOTHING` handles any emails that were already captured by the landing page before the migration runs.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module vs standalone service | Module | Principles require it. Shared middleware, single deploy, one connection pool. |
| Merge tables vs keep separate | Merge with `source` column | One table, one source of truth. `source` column distinguishes origin without schema duplication. |
| Integer PK vs UUID | Integer (SERIAL) | Append-only table, no external references. Simpler, smaller, faster. |
| Auth on signup endpoint | None | Anonymous strangers signing up. Rate limiting per IP is sufficient. |
| Rate limit implementation | In-memory counter | Same pattern as distribution tracking. No Redis for a low-traffic endpoint. |
| Data migration approach | Alembic data migration | Runs in normal deploy pipeline, tracked in version history, executes exactly once. |
| Delete email-api/ | Yes, after wiring | No value in keeping a principles-violating service as fallback. Separate commit for easy revert. |

---

## Execution Flow

```
[Phase 1 — Schema]  (Tasks 1-2 parallel, ~1.5h)
   Task 1 (model + migration)    ──┐
   Task 2 (OpenAPI + DTOs)        ──┘

[Phase 2 — Endpoint]  (Task 3, ~1h)
   Task 3 (routes + service + repository)

[Phase 3 — Wire + Verify]  (Task 4, ~15m)
   Task 4 (register in ENABLED_MODULES, smoke test)

[Phase 4 — Port + Cleanup]  (Tasks 5-6 parallel, ~40m)
   Task 5 (port Trendfy subscribers)  ──┐
   Task 6 (delete email-api/)          ──┘
```

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)
