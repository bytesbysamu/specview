"""Top-level pytest fixtures shared across tests/ and modules/*/tests/.

Auth bypass for protected routes
================================

SaaS Auth Task 3 wraps every existing protected route in
`@require_auth`, which inspects the `Authorization: Bearer <jwt>` header
and hydrates `g.current_user` via `verify_jwt` + `get_or_create_user_from_claims`.
Existing tests across the suite hit those routes without a real JWT and
without a real user repository attached to the Flask app. To keep the
decorator-sprinkle pass green without rewriting every integration test,
this conftest installs a session-scoped autouse fixture that:

  1. monkeypatches `modules.auth.decorators.verify_jwt` to return a
     synthetic claims dict — no JWKS HTTP call, no signature check;
  2. monkeypatches `modules.auth.decorators.get_or_create_user_from_claims`
     to return a fixed `User` row without touching the (often unset)
     `current_app.user_repository` attribute;
  3. attaches a default `user_repository` to `flask.Flask` as a class
     attribute so `current_app.user_repository` access in the wrapper
     never AttributeErrors before the patched function is invoked;
  4. wraps `werkzeug.test.Client.open` so every test-client request
     gets a default `Authorization: Bearer test-token` header — unless
     the caller explicitly passes its own `Authorization` header (so
     401-asserting tests can opt out by passing `headers={"Authorization": ""}`
     or by calling `client.open(... headers=[])`).

Tests that explicitly verify the decorator's negative paths (missing /
malformed bearer, JWKS error → 401) live in
`modules/auth/tests/test_decorators.py` and use their own
monkeypatches; pytest's `monkeypatch` fixture is function-scoped, so the
test-local patches override these session-level stubs for the duration
of that single test.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask.testing import FlaskClient


_FAKE_CLAIMS = {"sub": "test-user", "email": "test@example.com"}


def _fake_verify_jwt(token: str) -> dict:
    """Bypass for the real PyJWKClient + RS256 verifier.

    Honours the legacy `X-User-Id` / `X-User-Email` headers used by the
    pre-auth billing tests (originally consumed by the now-removed
    `modules/billing/decorators.py` AUTH_BYPASS path) so those tests can
    keep targeting specific user rows without a rewrite.
    """
    from flask import request
    claims = dict(_FAKE_CLAIMS)
    try:
        sub = request.headers.get("X-User-Id")
        email = request.headers.get("X-User-Email")
    except RuntimeError:
        sub = email = None
    if sub:
        claims["sub"] = sub
    if email:
        claims["email"] = email
    return claims


def _fake_get_or_create_user_from_claims(claims: dict, _user_repo) -> object:
    """Return a fixed User without hitting `current_app.user_repository`.

    Importing `User` lazily so this conftest stays import-safe even if a
    test environment hasn't yet built the SQLModel registry.

    `plan="pro"` is intentional: `@check_usage_limit` short-circuits for
    Pro users without opening a DB session, which keeps the auth-bypass
    test path away from the metering DB (test envs that haven't seeded
    `usage_counter` would otherwise raise `OperationalError`). Tests that
    exercise the free-tier metering branch live under
    `modules/usage/tests/` and supply their own user fixture there.
    """
    from modules.auth.models import User
    return User(
        id=1,
        auth_user_id=claims.get("sub", "test-user"),
        email=claims.get("email", "test@example.com"),
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
    """Session-stable auth bypass for every test in the suite.

    Function-scoped (matching pytest's default) so individual tests can
    rebind the same attributes via their own monkeypatch fixture; the
    teardown restores our defaults, not the originals from the module.

    Tests under `modules/auth/tests/` exercise the real decorator's
    negative paths (missing / malformed bearer, JWKS errors → 401) and
    own their own JWT-verifier stubs. Skip the bypass for them so those
    assertions keep firing.
    """
    test_path = str(request.fspath)
    if "/modules/auth/tests/" in test_path:
        # Auth tests exercise the real decorator; clear SKIP_AUTH so the
        # decorator's bypass path doesn't interfere even if .env has it set.
        monkeypatch.delenv("SKIP_AUTH", raising=False)
        yield
        return

    # Clear SKIP_AUTH — this bypass provides its own JWT injection, so the
    # env-based shortcut must be off to avoid g.current_user=None crashes.
    monkeypatch.delenv("SKIP_AUTH", raising=False)

    # Patch the names the decorator's wrapper looks up at call time.
    import modules.auth.decorators as _decorators
    monkeypatch.setattr(_decorators, "verify_jwt", _fake_verify_jwt)
    monkeypatch.setattr(
        _decorators,
        "get_or_create_user_from_claims",
        _fake_get_or_create_user_from_claims,
    )

    # `current_app.user_repository` is evaluated by the wrapper before
    # the patched function is called. Provide a class-level default so
    # any Flask app instance the test creates carries one without the
    # test having to attach it manually.
    monkeypatch.setattr(Flask, "user_repository", MagicMock(), raising=False)

    # Auto-inject the bearer header on every test-client call. Tests
    # that need to assert "no token => 401" can pass an explicit
    # `Authorization` header (empty string or anything non-Bearer) to
    # opt out of the default.
    # Patch `FlaskClient.open` (not werkzeug `Client.open`) because Flask's
    # subclass collapses path/headers/etc into a Request object before
    # delegating to super().open — patching the werkzeug parent would see
    # only a Request positional and a (buffered, follow_redirects) kwargs
    # pair, with no `headers` to inject.
    original_open = FlaskClient.open

    def _open_with_auth(self, *args, **kwargs):
        # When the caller hands a pre-built EnvironBuilder / dict environ
        # / Request straight to `client.open(...)`, the headers are
        # already baked in — adding a `headers=` kwarg would force Flask
        # down a different code path. Leave those calls alone.
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
