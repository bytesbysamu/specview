"""Pure-Python auth core — HS256 JWT verification (the live SSO spine).

No Flask imports. All Flask-aware logic lives in decorators.py.

The product is magic-link only and there are no passwords. Token *minting*
(magic-link issue/verify, JWT creation, refresh) now lives in the remote
oll-core (core.oll.am); this product container only needs to *verify* the JWTs
oll-core issues, so that the shared SSO token grants access to product routes.
The legacy ``password_hash`` column on User is retained for migration safety
but is never read or written here.
"""
from __future__ import annotations

import os

import jwt

_JWT_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    """Resolve the JWT signing secret from the environment, lazily.

    No hardcoded fallback: a missing secret raises rather than silently
    verifying tokens against a publicly-known value. Read at call time (not
    import) so the production boot gate and tests can set it before first use.
    Prefers AUTH_JWT_SECRET (the Core standard name); falls back to the legacy
    JWT_SECRET for compatibility with existing deploys. This is the shared
    secret that lets a JWT minted by oll-core be trusted here (SSO).
    """
    secret = os.environ.get("AUTH_JWT_SECRET") or os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "AUTH_JWT_SECRET (or JWT_SECRET) is not set — refusing to sign or "
            "verify tokens with an insecure default."
        )
    return secret


def verify_token(token: str) -> dict:
    """Decode and validate HS256 JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
