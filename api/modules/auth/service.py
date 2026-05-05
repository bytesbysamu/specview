"""Pure-Python auth core — bcrypt password hashing + HS256 JWT.

No Flask imports. All Flask-aware logic lives in decorators.py and routes.py.
"""
from __future__ import annotations

import os
import time

import bcrypt
import jwt

_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_SECONDS = 72 * 3600  # 72 hours


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
