"""Subscription SQLModel entity.

Column shape is locked by api/migrations/versions/0001_initial_schema.py
(SaaS Persistence Task 1). This class only adds the SQLModel binding —
do NOT add a new migration; the table already exists.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Subscription(SQLModel, table=True):
    """One row per User. Written exclusively by Stripe webhook handlers.

    Field semantics:
      - plan: denormalised mirror of User.plan; both are written together
        in a single transaction by upsert_with_plan().
      - status: Stripe subscription status — active | past_due | canceled.
      - stripe_customer_id / stripe_subscription_id: Stripe IDs for portal
        and webhook lookup; both nullable until first checkout completes.
      - current_period_*: billing-period bounds; surfaced via /billing/status.
      - canceled_at: set only when cancel_at_period_end is true.
    """

    __tablename__ = "subscription"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    plan: str = Field(default="free")
    status: str = Field(default="active")
    stripe_customer_id: Optional[str] = Field(default=None)
    stripe_subscription_id: Optional[str] = Field(default=None)
    current_period_start: Optional[datetime] = Field(default=None)
    current_period_end: Optional[datetime] = Field(default=None)
    canceled_at: Optional[datetime] = Field(default=None)
