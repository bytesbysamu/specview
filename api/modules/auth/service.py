"""Pure-Python auth core — bcrypt password hashing + HS256 JWT.

No Flask imports. All Flask-aware logic lives in decorators.py and routes.py.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import bcrypt
import jwt
from sqlmodel import Session, select

_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_SECONDS = 72 * 3600  # 72 hours
_MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + _JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate HS256 JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])


def normalize_email(email: str) -> str:
    """Lowercase and strip whitespace from an email address."""
    return email.strip().lower()


def validate_password_policy(password: str) -> str | None:
    """Return an error message if the password violates policy, else None."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f"password must be at least {_MIN_PASSWORD_LENGTH} characters"
    return None


def refresh_token_for_user(user_id: int, email: str) -> str:
    """Issue a fresh JWT with a new 72-hour expiry for the given user identity."""
    return create_token(user_id, email)


def token_expires_at_iso(token: str) -> str:
    """Decode a JWT and return its exp claim as an ISO 8601 UTC timestamp."""
    claims = verify_token(token)
    exp_dt = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    return exp_dt.isoformat()


def create_user(session: Session, email: str, password_hash: str):
    """Insert a new User row, commit, and return the refreshed instance.

    Owns the transaction boundary — callers must not call session.commit().
    Raises sqlalchemy.exc.IntegrityError if the email is already registered.
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
