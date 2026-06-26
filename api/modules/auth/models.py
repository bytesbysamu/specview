"""User + magic-link SQLModel entities."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    auth_user_id: Optional[str] = Field(default=None, unique=True, index=True)
    email: str = Field(unique=True)
    # Legacy column — retained for migration safety only. The product is
    # magic-link only; no code path reads or writes this. Do not drop (live
    # data risk); it is simply left NULL for every new user.
    password_hash: Optional[str] = Field(default=None)
    plan: str = Field(default="free")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MagicLinkToken(SQLModel, table=True):
    __tablename__ = "magic_link_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    # SHA-256 hex digest of the single-use token — the raw token is emailed and
    # never persisted, so a DB leak cannot be replayed into a sign-in.
    token_hash: str = Field(unique=True, index=True)
    email: str = Field(index=True)
    # Populated when the requesting email already has a User row; left NULL for
    # first-time addresses (the User is created lazily on verify).
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    expires_at: datetime
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
