"""Top-level pytest fixtures shared across tests/ and modules/*/tests/.

Auth bypass for protected routes
================================

Every protected route is wrapped in `@require_auth`, which:
  1. Reads ``Authorization: Bearer <token>`` from the request header.
  2. Calls ``verify_token(token)`` (HS256 decode) to get ``{"sub": "<user_id>", ...}``.
  3. Calls ``_load_user(int(claims["sub"]))`` to fetch the User from DB.
  4. Sets ``g.current_user = user``.

Existing tests hit protected routes without a real JWT and without a real
DB.  To keep every integration test green this conftest installs a
function-scoped autouse fixture that:

  1. Monkeypatches ``modules.auth.decorators.verify_token`` to return a
     synthetic claims dict — no HS256 decode, no signature check.
  2. Monkeypatches ``modules.auth.decorators._load_user`` to return a
     fixed ``User`` row without opening a DB session.
  3. Wraps ``FlaskClient.open`` so every test-client request carries a
     default ``Authorization: Bearer test-token`` header — unless the
     caller explicitly passes its own ``Authorization`` header (tests that
     assert 401 pass ``headers={"Authorization": ""}`` to opt out).

Tests that exercise the real decorator's negative paths (missing bearer,
bad token → 401) live in ``modules/auth/tests/test_decorators.py`` and
provide their own monkeypatches; pytest's ``monkeypatch`` fixture is
function-scoped so test-local patches override these stubs only for that
single test.
"""
from __future__ import annotations

import pytest
from flask.testing import FlaskClient


_FAKE_USER_ID = 1


def _fake_verify_token(token: str) -> dict:
    """Bypass for the real HS256 verifier.

    Returns a claims dict whose ``sub`` matches ``_FAKE_USER_ID`` so that
    ``_load_user(int(claims["sub"]))`` receives a valid integer without a
    real JWT decode.
    """
    return {"sub": str(_FAKE_USER_ID), "email": "test@example.com"}


def _fake_load_user(user_id: int):
    """Return a fixed User without opening a DB session.

    ``plan="pro"`` is intentional: ``@check_usage_limit`` short-circuits
    for Pro users without querying the usage_counter table, which keeps
    the bypass path away from the metering DB.  Tests that exercise the
    free-tier metering branch live under ``modules/usage/tests/`` and
    provide their own user fixture there.
    """
    from modules.auth.models import User
    return User(
        id=user_id,
        auth_user_id="test-user",
        email="test@example.com",
        plan="pro",
    )


def _has_authorization(headers) -> bool:
    """Tolerate every shape Flask test_client accepts for `headers=`."""
    if headers is None:
        return False
    if isinstance(headers, dict):
        return any(k.lower() == "authorization" for k in headers)
    try:
        return any(str(k).lower() == "authorization" for k, _v in headers)
    except (TypeError, ValueError):
        return False


@pytest.fixture(autouse=True)
def _auth_bypass(request, monkeypatch):
    """Function-scoped auth bypass for every test in the suite.

    Patches the two internal seams of ``require_auth``:
      - ``modules.auth.decorators.verify_token``  → returns fake claims
      - ``modules.auth.decorators._load_user``    → returns fake User

    Tests under ``modules/auth/tests/`` exercise the real decorator's
    negative paths (missing bearer, bad token → 401) and own their own
    stubs.  Skip the bypass for them so those assertions keep firing.
    """
    test_path = str(request.fspath)
    if "/modules/auth/tests/" in test_path:
        # Auth tests exercise the real decorator; clear SKIP_AUTH so the
        # env-based bypass path doesn't interfere.
        monkeypatch.delenv("SKIP_AUTH", raising=False)
        yield
        return

    # Clear SKIP_AUTH — this bypass provides its own JWT injection.
    monkeypatch.delenv("SKIP_AUTH", raising=False)

    # Patch the two names require_auth's wrapper resolves at call time.
    import modules.auth.decorators as _decorators
    monkeypatch.setattr(_decorators, "verify_token", _fake_verify_token)
    monkeypatch.setattr(_decorators, "_load_user", _fake_load_user)

    # Auto-inject the bearer header on every test-client call.  Tests
    # that need "no token => 401" pass ``headers={"Authorization": ""}``
    # to opt out of the default injection.
    #
    # Patch FlaskClient.open (not werkzeug Client.open) because Flask's
    # subclass collapses path/headers/etc into a Request before calling
    # super().open — patching the werkzeug parent sees only a positional
    # Request with headers already baked in.
    original_open = FlaskClient.open

    def _open_with_auth(self, *args, **kwargs):
        # Pre-built EnvironBuilder / environ dict / Request objects have
        # headers baked in — leave them untouched.
        from werkzeug.test import EnvironBuilder
        from werkzeug.wrappers import Request as _WzRequest
        if args and isinstance(args[0], (EnvironBuilder, dict, _WzRequest)):
            return original_open(self, *args, **kwargs)

        headers = kwargs.get("headers")
        if not _has_authorization(headers):
            if isinstance(headers, dict):
                new_headers = dict(headers)
                new_headers["Authorization"] = "Bearer test-token"
            elif headers is None:
                new_headers = {"Authorization": "Bearer test-token"}
            else:
                new_headers = list(headers)
                new_headers.append(("Authorization", "Bearer test-token"))
            kwargs["headers"] = new_headers
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(FlaskClient, "open", _open_with_auth)
    yield


@pytest.fixture
def auth_headers() -> dict:
    """Explicit headers helper for tests that prefer to spell out the
    Authorization token at the call site (matches the architecture-doc
    contract). The autouse `_auth_bypass` fixture already injects the
    same header for tests that omit one.
    """
    return {"Authorization": "Bearer test-token"}
