"""Auth decorator stub for billing routes.

Reads X-User-Id / X-User-Email request headers when AUTH_BYPASS=true (dev/test);
otherwise validates a Bearer JWT via _verify_jwt. The JWT path is a stub for
the future Neon Auth epic — production deployments should replace _verify_jwt
with real RS256 verification.

Lives in modules/billing/ rather than modules/auth/ because billing ships
before the auth epic; modules/auth/decorators.py is reserved for the proper
implementation when it lands.
"""
import os
from functools import wraps
from typing import Optional, Tuple

from flask import g, jsonify, request


class _CurrentUser:
    """Minimal user context attached to flask.g for the request lifecycle."""

    __slots__ = ("auth_user_id", "email")

    def __init__(self, auth_user_id: str, email: str):
        self.auth_user_id = auth_user_id
        self.email = email


def _verify_jwt(token: str) -> Tuple[str, str]:
    """Stub: decode a Neon Auth JWT and return (auth_user_id, email).

    This implementation is intentionally minimal. The real Neon Auth wrapper
    (auth epic) replaces this with JWKS-cached RS256 verification.
    """
    raise NotImplementedError(
        "JWT verification not yet wired — set AUTH_BYPASS=true in dev/test "
        "or implement Neon Auth verification in modules/auth/."
    )


def _current_user_from_request() -> Optional[_CurrentUser]:
    if os.environ.get("AUTH_BYPASS", "").lower() == "true":
        return _CurrentUser(
            auth_user_id=request.headers.get("X-User-Id", "test-user"),
            email=request.headers.get("X-User-Email", "test@example.com"),
        )
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        auth_user_id, email = _verify_jwt(auth[7:])
    except Exception:
        return None
    return _CurrentUser(auth_user_id=auth_user_id, email=email)


def require_auth(fn):
    """Populate g.current_user or return 401."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _current_user_from_request()
        if user is None:
            return jsonify({"error": "unauthorized"}), 401
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper
