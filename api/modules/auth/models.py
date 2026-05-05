"""User SQLModel entity."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    auth_user_id: Optional[str] = Field(default=None, unique=True, index=True)
    email: str = Field(unique=True)
    password_hash: Optional[str] = Field(default=None)
    plan: str = Field(default="free")
    created_at: datetime = Field(default_factory=datetime.utcnow)
