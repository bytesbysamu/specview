---
sidebar_position: 2
---

# Waitlist Module — Epic

**Purpose**: Define scope and tasks for replacing `email-api/` with a proper waitlist module.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and open questions resolved.

---

## Business Value

The waitlist captures demand signal before and after launch. Trendfy already collected ~N subscribers in `bubls_subscribers` who expressed interest in Bubls before the app existed. New landing page visitors sign up through the same endpoint. Merging both into one table with a `source` column gives a single view of everyone waiting for the product.

The standalone `email-api/` violates two architecture principles and creates operational overhead that compounds with every deploy. Fixing it now (30 minutes of refactoring) prevents it from becoming load-bearing technical debt that costs hours later.

---

## Scope

### What This Epic Covers

- SQLAlchemy model `WaitlistSignup` with `id`, `email`, `created_at`, `source`
- Flask Blueprint `POST /api/waitlist/signup` registered in `ENABLED_MODULES`
- Alembic migration creating `waitlist_signups` table
- Data migration porting `bubls_subscribers` rows into `waitlist_signups` with `source='trendfy'`
- OpenAPI spec and generated Pydantic DTOs
- Pytest tests for the endpoint and repository layer
- Deletion of the standalone `email-api/` directory

### What This Epic Does NOT Cover

- Email sending (confirmation, welcome, drip campaigns)
- Admin dashboard or UI for viewing signups
- Frontend waitlist form (owned by the landing page / distribution experiment)
- Deduplication beyond the unique email DB constraint
- Analytics or funnel metrics

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Model + migration** | None | 2 | 1h | High |
| 2 | **OpenAPI spec + DTOs** | None | 1 | 30m | High |
| 3 | **Blueprint route + service + repository** | 1, 2 | — | 1h | High |
| 4 | **Register in ENABLED_MODULES + smoke test** | 3 | — | 15m | High |
| 5 | **Port Trendfy subscribers** | 1 | 3, 4 | 30m | Medium |
| 6 | **Delete email-api/** | 4 | 5 | 10m | Medium |

### Task Details

#### Task 1: Model + migration

Create `server/modules/waitlist/models.py` with a SQLAlchemy model:

```python
class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"

    id          = mapped_column(Integer, primary_key=True, autoincrement=True)
    email       = mapped_column(String, unique=True, nullable=False)
    source      = mapped_column(String(30), nullable=False, default="landing_page")
    created_at  = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Create Alembic migration `server/migrations/versions/20260417_create_waitlist_signups.py`. Table: `waitlist_signups` with columns `id` (SERIAL PK), `email` (VARCHAR UNIQUE NOT NULL), `source` (VARCHAR(30) NOT NULL DEFAULT 'landing_page'), `created_at` (TIMESTAMPTZ DEFAULT NOW()). Index on `email` (unique constraint covers it) and `source`.

#### Task 2: OpenAPI spec + DTOs

Create `server/openapi/waitlist.yaml` defining the `POST /api/waitlist/signup` endpoint. Request body: `{ email: string (required) }`. Response 201: `{ id: int, email: string, source: string, created_at: string }`. Response 409: `{ error: "Email already registered" }`. Response 422: `{ error: string }`.

Generate DTOs:

```bash
datamodel-codegen --input server/openapi/waitlist.yaml \
  --output server/modules/waitlist/dto.py \
  --output-model-type pydantic_v2
```

If `datamodel-codegen` is not installed, hand-author the Pydantic models to match (following the pattern in `modules/user/dto.py`).

#### Task 3: Blueprint route + service + repository

Create three files following the existing module pattern:

- `server/modules/waitlist/routes.py` — Blueprint `bp` with `POST /api/waitlist/signup`. Parse JSON via Pydantic DTO, delegate to service, return 201 on success or 409 on duplicate.
- `server/modules/waitlist/service.py` — Business logic. Validate email format, call repository. Raise `DuplicateEmail` on conflict.
- `server/modules/waitlist/repository.py` — SQLAlchemy insert. Catch `IntegrityError` for duplicate email.

No auth required. Rate-limit to 5 signups/minute per IP (in-memory counter, same pattern as distribution tracking).

#### Task 4: Register in ENABLED_MODULES + smoke test

Add `"modules.waitlist"` to the `ENABLED_MODULES` list in `server/app.py`. Create `server/modules/waitlist/__init__.py` with module docstring. Run the server, `curl -X POST http://localhost:5001/api/waitlist/signup -H 'Content-Type: application/json' -d '{"email":"test@example.com"}'` and verify 201 response. Verify `/api/health` includes `waitlist` in the modules list.

#### Task 5: Port Trendfy subscribers

Create a one-time migration or management script that reads all rows from `bubls_subscribers` on the same Neon instance and inserts them into `waitlist_signups` with `source='trendfy'`. Skip duplicates (ON CONFLICT DO NOTHING on email). Log the count of ported vs skipped rows.

This can be an Alembic data migration (preferred, since it runs in the normal deploy pipeline) or a standalone script in `server/scripts/`. The migration approach is preferred because it executes exactly once and is tracked by Alembic's version history.

#### Task 6: Delete email-api/

Remove the standalone `email-api/` directory (Dockerfile, raw psycopg2 code, etc.). If any landing page code references `email-api` endpoints, update those references to point to `POST /api/waitlist/signup` on the main backend. Commit the deletion separately so it's easy to revert if something was missed.

---

## Success Criteria

- `POST /api/waitlist/signup` returns 201 with a valid email and 409 on duplicate
- `waitlist_signups` table exists in Neon with correct schema
- Trendfy subscribers appear in `waitlist_signups` with `source='trendfy'`
- New landing page signups appear with `source='landing_page'`
- `email-api/` directory is deleted
- `/api/health` lists `waitlist` in enabled modules
- All existing tests still pass (no regressions)

---

## Non-Goals

- Building a full CRM or subscriber management system
- Email verification or double opt-in
- Exposing a GET endpoint to list signups (SQL query for now)
- Rate limiting beyond basic IP-based abuse prevention
- Frontend form — owned by the landing page task

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
