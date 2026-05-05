"""Subscription model defaults and SQLModel registration."""
from datetime import datetime

from modules.billing.models import Subscription


def test_subscription_defaults_are_safe():
    sub = Subscription(user_id=1)
    assert sub.plan == "free"
    assert sub.status == "active"
    assert sub.stripe_customer_id is None
    assert sub.stripe_subscription_id is None
    assert sub.canceled_at is None


def test_subscription_table_registered_in_metadata():
    from sqlmodel import SQLModel

    assert "subscription" in SQLModel.metadata.tables, (
        "Subscription must register the 'subscription' table on SQLModel.metadata "
        "so pers-T1's 0001 migration aligns with the SQLModel class."
    )


def test_subscription_columns_match_locked_migration_shape():
    from sqlmodel import SQLModel

    cols = {c.name for c in SQLModel.metadata.tables["subscription"].columns}
    expected = {
        "id",
        "user_id",
        "plan",
        "status",
        "stripe_customer_id",
        "stripe_subscription_id",
        "current_period_start",
        "current_period_end",
        "canceled_at",
    }
    assert expected.issubset(cols), (
        f"Subscription columns drifted from 0001_initial_schema.py.\n"
        f"  expected (subset): {sorted(expected)}\n"
        f"  actual:            {sorted(cols)}"
    )


def test_subscription_user_id_is_unique_index():
    from sqlmodel import SQLModel

    table = SQLModel.metadata.tables["subscription"]
    user_id_col = table.columns["user_id"]
    assert user_id_col.unique or any(
        "user_id" in {c.name for c in idx.columns} for idx in table.indexes
    ), "Subscription.user_id must carry a unique index (one row per user)."


def test_subscription_period_fields_accept_datetime():
    sub = Subscription(
        user_id=42,
        current_period_start=datetime(2026, 1, 1),
        current_period_end=datetime(2026, 2, 1),
    )
    assert sub.current_period_start.year == 2026
    assert sub.current_period_end.month == 2
