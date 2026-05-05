"""User SQLModel entity — identity anchor for FK chain.

The plan field is denormalised (not joined from Subscription on every request);
the monetisation webhook handler owns the write path that keeps it current.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    auth_user_id: str = Field(unique=True, index=True)
    email: str = Field(unique=True)
    plan: str = Field(default="free")
    created_at: datetime = Field(default_factory=datetime.utcnow)
