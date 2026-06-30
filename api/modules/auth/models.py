"""User SQLModel entity — the live SSO identity row.

The ``User`` row is loaded by ``@require_auth`` (via the JWT ``sub``) so a
token minted by the remote oll-core resolves to a local user for product
routes. Magic-link token minting/verification was retired from this product
container (it now lives in oll-core), so the ``MagicLinkToken`` model was
removed. The ``magic_link_tokens`` table is left intact in the migrations —
the shared ``oll_core`` DB is dual-owned, and an unused table is harmless.
"""
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
