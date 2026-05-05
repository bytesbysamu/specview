"""Pure-Python core for Neon Auth integration.

verify_jwt: RS256 + JWKS validation against Neon Auth's well-known endpoint.
send_magic_link / verify_magic_link: thin proxies over Neon Auth's REST API.
get_or_create_user_from_claims: idempotent User upsert keyed by claims["sub"].

No Flask imports. No `g` access. The decorator (modules/auth/decorators.py)
and routes (modules/auth/routes.py) are the only Flask-aware seams.
"""
from __future__ import annotations

import os
from typing import Optional

import jwt
import requests
from jwt import PyJWKClient

from modules.auth.models import User


# ── Module-level config (read once) ───────────────────────────────────────────

_NEON_AUTH_JWKS_URL = os.environ.get("NEON_AUTH_JWKS_URL", "")
_NEON_AUTH_AUDIENCE = os.environ.get("NEON_AUTH_AUDIENCE", "authenticated")
_NEON_AUTH_API_BASE = os.environ.get("NEON_AUTH_API_BASE", "https://auth.neon.tech")
_NEON_AUTH_PROJECT_ID = os.environ.get("NEON_AUTH_PROJECT_ID", "")
_NEON_AUTH_API_KEY = os.environ.get("NEON_AUTH_API_KEY", "")
_REDIRECT_URL = os.environ.get("NEON_AUTH_REDIRECT_URL", "http://localhost:4201/auth/callback")

# Single PyJWKClient instance — internally caches signing keys with a TTL.
# Re-resolved lazily (first call) so import never raises in test envs that
# leave NEON_AUTH_JWKS_URL unset.
_JWKS_CLIENT: Optional[PyJWKClient] = None


def _jwks_client() -> PyJWKClient:
    global _JWKS_CLIENT
    if _JWKS_CLIENT is None:
        if not _NEON_AUTH_JWKS_URL:
            raise RuntimeError("NEON_AUTH_JWKS_URL is not set")
        _JWKS_CLIENT = PyJWKClient(_NEON_AUTH_JWKS_URL)
    return _JWKS_CLIENT


# ── JWT verification ─────────────────────────────────────────────────────────

def verify_jwt(token: str) -> dict:
    """Validate a Neon Auth JWT and return the claims dict.

    Raises:
        jwt.PyJWTError: if the token is malformed, expired, or fails signature
            verification. Callers (the @require_auth decorator) translate this
            to HTTP 401.
    """
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=_NEON_AUTH_AUDIENCE,
    )


# ── Magic-link send / verify (Neon Auth REST proxies) ────────────────────────

def send_magic_link(email: str) -> dict:
    """Request that Neon Auth dispatch a magic-link email.

    Returns the Neon Auth response body (`{"request_id": "..."}`). Raises
    requests.HTTPError if Neon Auth returns a non-2xx response.
    """
    resp = requests.post(
        f"{_NEON_AUTH_API_BASE}/v1/projects/{_NEON_AUTH_PROJECT_ID}/auth/magic-link/send",
        headers={"Authorization": f"Bearer {_NEON_AUTH_API_KEY}"},
        json={"email": email, "redirect_url": _REDIRECT_URL},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def verify_magic_link(token: str) -> dict:
    """Exchange a one-time magic-link token for an issued JWT + claims.

    Returns `{"jwt": "...", "claims": {...}}`. Raises requests.HTTPError on
    non-2xx response (the route handler translates to HTTP 400).
    """
    resp = requests.post(
        f"{_NEON_AUTH_API_BASE}/v1/projects/{_NEON_AUTH_PROJECT_ID}/auth/magic-link/verify",
        headers={"Authorization": f"Bearer {_NEON_AUTH_API_KEY}"},
        json={"token": token},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── User upsert ──────────────────────────────────────────────────────────────

def get_or_create_user_from_claims(claims: dict, user_repo) -> User:
    """Idempotently upsert a User row keyed by claims['sub'] -> User.auth_user_id.

    user_repo is the saas-persistence UserRepository; this function depends on
    it exposing get_by_auth_user_id(auth_user_id) and create(auth_user_id, email).
    """
    auth_user_id = claims["sub"]
    user = user_repo.get_by_auth_user_id(auth_user_id)
    if user is None:
        user = user_repo.create(auth_user_id=auth_user_id, email=claims.get("email", ""))
    return user
