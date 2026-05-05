---
sidebar_position: 1
---

# Waitlist Module -- Analysis

**Purpose**: Catch contradictions, surface decisions, kill scope before the epic inflates.

---

## Problem

The executor built a standalone `email-api/` microservice with raw psycopg2 for landing page email capture. This contradicts two non-negotiable principles: always ORM (SQLAlchemy, never raw SQL) and module pattern (everything inside `server/modules/`, registered via Blueprint in `ENABLED_MODULES`). The standalone service creates operational debt: separate Dockerfile, separate deploy, separate connection pool, no shared middleware. Rolling it into the existing backend is a 30-minute refactor that eliminates all of that.

---

## Hard Constraints

| Constraint | Source | Implication |
|------------|--------|-------------|
| Always ORM, never raw SQL | principles.md | SQLAlchemy model, not raw psycopg2 |
| Module pattern | principles.md, app.py | `server/modules/waitlist/`, Blueprint registered in `ENABLED_MODULES` |
| Neon Postgres for everything | principles.md | Same Neon instance as all other Bubls data |
| Alembic for migrations | principles.md | Migration file in `server/migrations/versions/` |
| OpenAPI-first with generated DTOs | principles.md | `server/openapi/waitlist.yaml` as source of truth |

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Merge `bubls_subscribers` into `waitlist_signups` or keep separate? | Merge. One table, one source of truth. `source` column distinguishes origin (`trendfy` vs `landing_page`). |
| Delete `email-api/` or keep as fallback? | Delete after module is wired and verified. No fallback needed for a one-endpoint service. |
| Auth on the signup endpoint? | No auth. Anonymous strangers signing up for a waitlist. Rate-limit per IP instead. |

---

## Dependencies

| Dependency | Status | Blocks |
|------------|--------|--------|
| Neon Postgres instance | Provisioned | Nothing blocked |
| `bubls_subscribers` table (Trendfy) | Exists on same Neon instance | Data migration task |
| `email-api/` standalone service | Exists, to be deleted | Cleanup task |

---

## Explicitly Out of Scope

- Email sending (confirmation, welcome, drip) -- future capability
- Admin dashboard for viewing signups -- a SQL query suffices
- Deduplication logic beyond unique email constraint -- DB handles it
- Analytics or funnel tracking -- covered by the Distribution Experiment epic
- Landing page changes -- this epic is backend-only
