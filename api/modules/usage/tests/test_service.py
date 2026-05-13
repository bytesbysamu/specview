"""Service-layer tests for usage metering.

Covers:
  - LIMITS dict matches locked decision
  - increment: insert path, upsert path, isolation by user / feature / date
  - get_count: zero default, post-increment, isolation
  - get_remaining: full limit, decrement, clamp at zero, unmetered (-1)
  - reset_at_utc: tomorrow's UTC midnight, timezone-aware
  - Race condition: concurrent increments from multiple threads do not
    double-count (the upsert is atomic).

Imports are aliased to non-test-name patterns so pytest's
`python_functions = ["test_*", "*_*"]` rule does not collect them as tests.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy
from sqlmodel import Session, SQLModel

from modules.auth.models import User  # noqa: F401 — needed for FK target
from modules.usage import service as svc
from modules.usage.models import UsageCounter

# Single-word aliases avoid pytest's `python_functions = ["test_*", "*_*"]`
# rule which would otherwise collect bare imports as test functions.
bump = svc.increment
peek = svc.get_count
remaining = svc.get_remaining
resetts = svc.reset_at_utc
CAPS = svc.LIMITS


# --- LIMITS constant --------------------------------------------------------


def test_limits_contains_only_three_locked_features():
    assert CAPS == {"bootstrap": 30, "task_gen": 100, "spec_gen": 50}


@pytest.mark.parametrize(
    "feature,expected",
    [("bootstrap", 30), ("task_gen", 100), ("spec_gen", 50)],
)
def test_limits_individual_caps(feature, expected):
    assert CAPS[feature] == expected


# --- increment --------------------------------------------------------------


def test_increment_creates_row_with_count_one(session):
    assert bump(1, "bootstrap", session) == 1


def test_increment_existing_row_returns_two(session):
    bump(1, "bootstrap", session)
    assert bump(1, "bootstrap", session) == 2


def test_increment_persists_count_in_db(session):
    bump(1, "bootstrap", session)
    bump(1, "bootstrap", session)
    bump(1, "bootstrap", session)
    from sqlmodel import select as _select
    row = session.exec(
        _select(UsageCounter).where(UsageCounter.user_id == 1)
    ).first()
    assert row is not None
    assert row.count == 3


def test_increment_isolates_by_user(session):
    bump(1, "bootstrap", session)
    bump(1, "bootstrap", session)
    assert bump(2, "bootstrap", session) == 1


def test_increment_isolates_by_feature(session):
    bump(1, "bootstrap", session)
    bump(1, "bootstrap", session)
    assert bump(1, "task_gen", session) == 1


# --- get_count -------------------------------------------------------------


def test_get_count_zero_when_no_row(session):
    assert peek(1, "bootstrap", session) == 0


def test_get_count_after_increments(session):
    for _ in range(4):
        bump(1, "task_gen", session)
    assert peek(1, "task_gen", session) == 4


def test_get_count_isolated_by_user(session):
    bump(1, "bootstrap", session)
    assert peek(2, "bootstrap", session) == 0


# --- get_remaining ---------------------------------------------------------


def test_get_remaining_returns_full_limit_for_fresh_user(session):
    assert remaining(1, "bootstrap", session) == CAPS["bootstrap"]


def test_get_remaining_decrements_after_each_increment(session):
    bump(1, "spec_gen", session)
    assert remaining(1, "spec_gen", session) == CAPS["spec_gen"] - 1


def test_get_remaining_clamps_at_zero_when_over_limit(session):
    for _ in range(CAPS["bootstrap"] + 5):
        bump(1, "bootstrap", session)
    assert remaining(1, "bootstrap", session) == 0


def test_get_remaining_returns_minus_one_for_unmetered_feature(session):
    assert remaining(1, "not_a_real_feature", session) == -1


# --- reset_at_utc ----------------------------------------------------------


def test_reset_at_utc_returns_tomorrow_midnight_utc():
    result = resetts()
    assert result.tzinfo is not None, "must be timezone-aware"
    assert result.utcoffset() == timedelta(0), "must be UTC"
    today_utc = datetime.now(timezone.utc).date()
    assert result.date() == today_utc + timedelta(days=1)
    assert (result.hour, result.minute, result.second) == (0, 0, 0)


def test_reset_at_utc_returns_datetime_not_string():
    """reset_at_utc returns a datetime so the DTO can serialise it canonically."""
    assert isinstance(resetts(), datetime)


# --- race condition (concurrency) ------------------------------------------


def test_increment_is_atomic_under_concurrent_threads(tmp_path):
    """Concurrent increments from multiple threads must not double-count.

    Uses a file-backed SQLite database (WAL mode) so each thread can hold
    its own connection without StaticPool contention. If the
    `INSERT ... ON CONFLICT DO UPDATE` upsert were not atomic, two
    interleaved reads of `count` followed by two writes would lose one
    increment and the final count would drift below `threads_count *
    per_thread`.
    """
    db_path = tmp_path / "race.db"
    engine = sqlalchemy.create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    SQLModel.metadata.create_all(engine)
    # WAL allows concurrent readers; writes still serialise but no
    # "SQL statements in progress" error from sharing a connection.
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")

    threads_count = 5
    per_thread = 20
    expected = threads_count * per_thread
    barrier = threading.Barrier(threads_count)
    errors: list[BaseException] = []

    def worker():
        try:
            barrier.wait()
            for _ in range(per_thread):
                with Session(engine) as s:
                    bump(42, "task_gen", s)
        except BaseException as exc:  # noqa: BLE001 — record for assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(threads_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"worker raised: {errors[0]!r}"
    with Session(engine) as s:
        final = peek(42, "task_gen", s)
    assert final == expected, (
        f"race detected: expected {expected} increments, got {final}"
    )
