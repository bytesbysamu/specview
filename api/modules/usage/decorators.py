"""Flask decorator: `check_usage_limit(feature)`.

Stacking order is fixed by contract — `@require_auth` outer, then
`@check_usage_limit` inner. The decorator reads `g.current_user`,
short-circuits for Pro users without touching the database, returns a
structured 429 (matching `dtos.models.UsageLimitError`) when the daily
cap is hit, and increments the counter only after the wrapped handler
returns a sub-400 response.
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import current_app, g, jsonify

from dtos.models import UsageLimitError
from modules.data.db.session import get_session
from modules.usage.service import LIMITS, get_remaining, increment, reset_at_utc

# Stable error code surfaced in the 429 body. Frozen by openapi.yaml example.
_ERROR_CODE = "free_tier_limit_reached"


def _status_code(response: Any) -> int:
    """Extract the HTTP status code from a Flask handler return value.

    Handles tuple returns `(body, status[, headers])` and Response objects.
    Defaults to 200 when the handler returns a bare body — same convention
    Flask itself uses when materialising the response.
    """
    if isinstance(response, tuple):
        if len(response) >= 2 and isinstance(response[1], int):
            return response[1]
        return 200
    return int(getattr(response, "status_code", 200))


def _resolve_user_id() -> int:
    """Resolve the integer `user.id` from `g.current_user`.

    The auth layer is expected to populate `g.current_user` with a User
    SQLModel instance whose `id` is the integer PK. We accept either
    that or a plain int for testability.
    """
    user = g.current_user
    if isinstance(user, int):
        return user
    return int(getattr(user, "id"))


def _resolve_plan() -> str:
    """Resolve the plan string from `g.current_user`. Defaults to 'free'."""
    user = g.current_user
    return str(getattr(user, "plan", "free") or "free")


def _build_429_body(feature: str) -> dict:
    """Construct the canonical UsageLimitError body for a feature.

    Routes through the Pydantic DTO so the wire shape cannot drift from
    `openapi.yaml` without `make check-dtos` failing first.
    """
    limit = LIMITS.get(feature, 0)
    upgrade_url = current_app.config.get("UPGRADE_URL", "/upgrade")
    body = UsageLimitError(
        error=_ERROR_CODE,
        feature=feature,
        limit=limit,
        reset_at=reset_at_utc(),
        upgrade_url=upgrade_url,
    )
    return body.model_dump(mode="json")


def check_usage_limit(feature: str) -> Callable:
    """Enforce the daily free-tier cap for `feature`.

    Pro users bypass all DB access. Free users are rejected pre-handler
    with a 429 once their counter reaches the cap. On a sub-400 response
    the counter is incremented atomically (single round-trip upsert).

    Auth dependency: reads `g.current_user`. The decorator is intended to
    be stacked INSIDE `@require_auth` (auth outer, gate inner). If
    `g.current_user` is absent (auth layer not yet deployed) the
    decorator is a no-op so the route remains callable in pre-auth
    test environments. Once auth ships, missing `g.current_user` can
    only mean the auth decorator was forgotten — the upstream
    `require_auth` itself will short-circuit before this wrapper runs.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not hasattr(g, "current_user") or g.current_user is None:
                # Auth layer absent — metering cannot resolve a user; pass through.
                return fn(*args, **kwargs)

            plan = _resolve_plan()
            if plan == "pro":
                return fn(*args, **kwargs)

            user_id = _resolve_user_id()

            with get_session() as session:
                remaining = get_remaining(user_id, feature, session)

            if remaining == 0:
                return jsonify(_build_429_body(feature)), 429

            response = fn(*args, **kwargs)

            if _status_code(response) < 400:
                with get_session() as session:
                    increment(user_id, feature, session)

            return response

        return wrapper

    return decorator
