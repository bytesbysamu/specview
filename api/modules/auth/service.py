"""Pure-Python auth core — passwordless magic-link + HS256 JWT.

No Flask imports. All Flask-aware logic lives in decorators.py and routes.py.

The product is magic-link only: there are no passwords. A single-use token is
emailed to the address, only its SHA-256 hash is stored, and verifying it
issues a JWT. The legacy ``password_hash`` column is retained for migration
safety but is never read or written here.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from sqlmodel import Session, select

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_SECONDS = 72 * 3600  # 72 hours
_MAGIC_LINK_TTL_SECONDS = 15 * 60  # 15 minutes


def _jwt_secret() -> str:
    """Resolve the JWT signing secret from the environment, lazily.

    No hardcoded fallback: a missing secret raises rather than silently
    signing tokens with a publicly-known value. Read at call time (not import)
    so the production boot gate and tests can set it before first use.
    Prefers AUTH_JWT_SECRET (the Core standard name); falls back to the legacy
    JWT_SECRET for compatibility with existing deploys.
    """
    secret = os.environ.get("AUTH_JWT_SECRET") or os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "AUTH_JWT_SECRET (or JWT_SECRET) is not set — refusing to sign or "
            "verify tokens with an insecure default."
        )
    return secret


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + _JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate HS256 JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])


def normalize_email(email: str) -> str:
    """Lowercase and strip whitespace from an email address."""
    return email.strip().lower()


def refresh_token_for_user(user_id: int, email: str) -> str:
    """Issue a fresh JWT with a new 72-hour expiry for the given user identity."""
    return create_token(user_id, email)


def token_expires_at_iso(token: str) -> str:
    """Decode a JWT and return its exp claim as an ISO 8601 UTC timestamp."""
    claims = verify_token(token)
    exp_dt = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    return exp_dt.isoformat()


def create_user(session: Session, email: str, password_hash: str | None = None):
    """Insert a new User row, commit, and return the refreshed instance.

    Owns the transaction boundary — callers must not call session.commit().
    Raises sqlalchemy.exc.IntegrityError if the email is already registered.
    ``password_hash`` is always None for magic-link sign-ups; the parameter is
    retained only so the legacy column can stay nullable-populated if ever
    needed.
    """
    from modules.auth.models import User

    new_user = User(email=email, password_hash=password_hash)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


def get_user_by_email(session: Session, email: str):
    """Return the User row for the given email, or None if not found."""
    from modules.auth.models import User

    return session.exec(select(User).where(User.email == email)).first()


def find_or_create_user(session: Session, email: str):
    """Return the existing User for ``email`` or create one (magic-link sign-up).

    Owns the transaction boundary. ``email`` must already be normalized.
    """
    user = get_user_by_email(session, email)
    if user is not None:
        return user
    return create_user(session, email)


# ── magic-link tokens ───────────────────────────────────────────────────────


def _hash_token(raw_token: str) -> str:
    """SHA-256 hex digest used as the at-rest representation of a magic-link
    token. The raw token is only ever emailed; the DB stores the hash so a
    leaked row cannot be replayed."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_magic_link_token(session: Session, email: str) -> str:
    """Mint a single-use magic-link token for ``email``, persist its hash with a
    15-minute expiry, and return the raw token to embed in the sign-in link.

    Owns the transaction boundary. ``email`` must already be normalized.
    Associates the token with an existing User row when one exists; otherwise
    ``user_id`` stays NULL and the User is created lazily on verify.
    """
    from modules.auth.models import MagicLinkToken

    raw_token = secrets.token_urlsafe(32)
    existing = get_user_by_email(session, email)
    record = MagicLinkToken(
        token_hash=_hash_token(raw_token),
        email=email,
        user_id=existing.id if existing else None,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_MAGIC_LINK_TTL_SECONDS),
        used=False,
    )
    session.add(record)
    session.commit()
    return raw_token


def consume_magic_link_token(session: Session, raw_token: str) -> str | None:
    """Validate a magic-link token and atomically mark it used.

    Returns the associated (normalized) email on success, or None when the
    token is unknown, already used, or expired. Owns the transaction boundary.
    """
    from modules.auth.models import MagicLinkToken

    token_hash = _hash_token(raw_token)
    record = session.exec(
        select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash)
    ).first()

    if record is None or record.used:
        return None

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        # SQLite round-trips naive datetimes; treat stored values as UTC.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    record.used = True
    session.add(record)
    session.commit()
    return record.email
