"""UsageCounter SQLModel entity.

The column shape is locked by `migrations/versions/0001_initial_schema.py`
(Pers-T1). This class is the SQLModel projection of that table — adding,
removing, or renaming any column here drifts from the migration and must
not happen without a new Alembic revision.
"""
from datetime import date as date_type
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class UsageCounter(SQLModel, table=True):
    """One row per (user_id, feature, UTC date).

    The unique constraint on (user_id, feature, date) is what makes the
    `INSERT ... ON CONFLICT DO UPDATE` upsert in service.increment atomic
    and concurrent-safe on both SQLite (>= 3.24) and Postgres.
    """

    __tablename__ = "usage_counter"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "feature",
            "date",
            name="uq_usage_counter_user_feature_date",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    feature: str = Field(index=True)
    date: date_type = Field(default_factory=date_type.today, index=True)
    count: int = Field(default=0)
