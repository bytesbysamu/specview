"""Usage metering service — atomic per-day counter upsert + free-tier caps.

The `LIMITS` dict is the single tuneable for daily free-tier caps. All other
helpers (`increment`, `get_count`, `get_remaining`, `reset_at_utc`) are
pure functions that take an open Session.

Concurrency model
-----------------
`increment` issues a single `INSERT ... ON CONFLICT DO UPDATE RETURNING count`
statement per call. The unique constraint on
(user_id, feature, date) (locked in 0001) is the conflict target. The
statement is dialect-aware:

  - SQLite (>= 3.24, dev) uses native `INSERT OR ... ON CONFLICT` syntax
    via SQLAlchemy's `sqlite.insert`.
  - PostgreSQL (prod) uses `INSERT ... ON CONFLICT` via `postgresql.insert`.

Both dialects perform the upsert atomically inside a single statement, so
two concurrent requests from the same user session cannot double-count.
No application-level lock is taken.
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlmodel import Session, select

from modules.usage.models import UsageCounter

# Daily free-tier caps.
# Pro plan is unmetered — see `decorators.check_usage_limit`.
LIMITS: Dict[str, int] = {
    "bootstrap": 30,
    "task_gen": 100,
    "spec_gen": 50,
    "text": 50,
    "skill": 20,
}


def _utc_today() -> date_type:
    """Today's date in UTC. The counter row partition key."""
    return datetime.now(timezone.utc).date()


def increment(user_id: int, feature: str, session: Session) -> int:
    """Atomic upsert: insert (count=1) or increment count by 1 on conflict.

    Returns the new count after the operation. Concurrent callers from the
    same user session cannot double-count; the unique constraint on
    (user_id, feature, date) is the conflict target.

    The statement is built per-dialect so it lowers to native
    `ON CONFLICT DO UPDATE` on both SQLite (>= 3.24) and PostgreSQL.
    """
    today = _utc_today()
    dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    else:
        # Default to sqlite — also covers in-memory test engines.
        from sqlalchemy.dialects.sqlite import insert as dialect_insert

    table = UsageCounter.__table__
    stmt = dialect_insert(table).values(
        user_id=user_id,
        feature=feature,
        date=today,
        count=1,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[table.c.user_id, table.c.feature, table.c.date],
        set_={"count": table.c.count + 1},
    ).returning(table.c.count)

    result = session.execute(stmt)
    row = result.fetchone()
    session.commit()
    return int(row[0]) if row is not None else 1


def get_count(user_id: int, feature: str, session: Session) -> int:
    """Return today's call count for (user_id, feature). Zero if no row."""
    today = _utc_today()
    row = session.exec(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.feature == feature,
            UsageCounter.date == today,
        )
    ).first()
    return int(row.count) if row is not None else 0


def get_remaining(user_id: int, feature: str, session: Session) -> int:
    """Remaining calls for today.

    Returns -1 for features absent from `LIMITS` (treated as unmetered).
    Never returns negative — clamps to 0 once the limit is reached.
    """
    limit = LIMITS.get(feature)
    if limit is None:
        return -1
    used = get_count(user_id, feature, session)
    return max(0, limit - used)


def reset_at_utc() -> datetime:
    """Tomorrow's UTC midnight as a timezone-aware datetime.

    Returned in 429 bodies so clients know when to retry. Returning a
    `datetime` (not a string) lets the caller serialise via the
    `UsageLimitError` Pydantic DTO and emit the canonical RFC 3339 form.
    """
    tomorrow = _utc_today() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)
