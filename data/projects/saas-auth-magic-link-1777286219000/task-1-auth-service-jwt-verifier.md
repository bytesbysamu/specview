# Task 1: Auth Service + JWT Verifier

## 1. Context

Task 1 builds the pure-Python core of `modules/auth/`. Three concerns: verify a Neon Auth JWT (`verify_jwt`), proxy to Neon Auth's REST API for the magic-link send/verify pair, and idempotently upsert a `User` row keyed by the JWT's `sub` claim. No Flask imports, no `g` access, no decorator. Task 2 builds the decorator and the four-route blueprint that consume this service; Task 3 adds the decorator to every existing protected route; Task 4 builds the Angular surface.

The `User` SQLModel and `auth_user_id` column already exist from saas-persistence (`modules/auth/models.py`). The user repository is also already present from saas-persistence. This task adds three files: `service.py`, `tests/__init__.py`, `tests/test_service.py`. It also adds two new lines to `requirements.txt` (`pyjwt[crypto]` and `cryptography`, the latter being pyjwt[crypto]'s peer dependency for RS256 signing in tests).

**Trade-offs considered:**
- **Inline `verify_jwt` in the decorator file** — rejected; couples Flask to crypto; keeps the function untestable without a Flask app context.
- **One file per function (`service/verify.py`, `service/magic_link.py`, `service/users.py`)** — rejected; ~80 lines fits one file; promote to a package when a function passes ~40 lines.
- **`PyJWKClient` per call vs module-level singleton** — module-level singleton chosen; PyJWKClient internally caches signing keys with a TTL; per-call instantiation discards the cache every request.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
git status
git diff HEAD -- {WORKSPACE}/api/requirements.txt
cd {WORKSPACE}/api && python -m pytest --tb=short -q 2>&1 | tail -3
```

Record the passing test count from the last command as **N**.

**If `{WORKSPACE}/api/requirements.txt` is dirty**: stash or commit unrelated changes before starting.

Confirm `{WORKSPACE}/api/modules/auth/models.py` exists and exports a `User` SQLModel with an `auth_user_id` column. If absent, stop — the saas-persistence migration has not been applied to this branch and Task 1 cannot proceed.

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/api/modules/auth/service.py` (new) — three pure functions: `verify_jwt`, `send_magic_link`, `verify_magic_link`, plus the user-row upsert helper `get_or_create_user_from_claims`
- `{WORKSPACE}/api/modules/auth/tests/__init__.py` (new) — empty package marker
- `{WORKSPACE}/api/modules/auth/tests/test_service.py` (new) — 8 unit tests using a local RSA keypair to mint synthetic JWTs

### To Modify
- `{WORKSPACE}/api/requirements.txt` — append `pyjwt[crypto]>=2.8.0` and `cryptography>=42.0.0`

### To Leave Alone
- `{WORKSPACE}/api/modules/auth/models.py` — the `User` SQLModel from saas-persistence; do not touch
- `{WORKSPACE}/api/modules/auth/__init__.py` — already present from saas-persistence; do not modify
- `{WORKSPACE}/api/dtos/models.py` — generated from `openapi.yaml`; openapi changes belong in Task 2

---

## 4. Implementation Steps

### Step 1: Add the pyjwt[crypto] dependency

**Action**: Append two lines to `requirements.txt`. `pyjwt[crypto]` provides RS256 verification; `cryptography` is its peer dependency and is needed by the test fixture to sign synthetic JWTs.

**File**: `{WORKSPACE}/api/requirements.txt` (modify — append at end)

Add at the bottom of the file:
```
pyjwt[crypto]>=2.8.0
cryptography>=42.0.0
```

**Verify**:
```bash
cd {WORKSPACE}/api && pip install -r requirements.txt 2>&1 | tail -3
python -c "import jwt; from jwt import PyJWKClient; print(jwt.__version__)"
```
Expect a version `>=2.8.0` printed and no import errors.

---

### Step 2: Create the test package marker

**Action**: Create an empty `__init__.py` so pytest treats `tests/` as a package.

**File**: `{WORKSPACE}/api/modules/auth/tests/__init__.py` (new)

```python
```
*(empty — zero bytes)*

**Verify**:
```bash
test -f {WORKSPACE}/api/modules/auth/tests/__init__.py && echo "ok"
```
Expect `ok`.

---

### Step 3: Write `service.py`

**Action**: Create `service.py` with `verify_jwt`, `send_magic_link`, `verify_magic_link`, `get_or_create_user_from_claims`. Read `NEON_AUTH_JWKS_URL`, `NEON_AUTH_AUDIENCE`, `NEON_AUTH_PROJECT_ID`, `NEON_AUTH_API_BASE`, `NEON_AUTH_API_KEY` from `os.environ`. The PyJWKClient is module-level (single instance, internal caching).

**File**: `{WORKSPACE}/api/modules/auth/service.py` (new)

```python
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
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "from modules.auth.service import verify_jwt, send_magic_link, verify_magic_link, get_or_create_user_from_claims; print('ok')"
```
Expect `ok`.

---

### Step 4: Write `test_service.py`

**Action**: Create the unit tests. Use a per-test RSA keypair to mint synthetic JWTs and monkeypatch `_JWKS_CLIENT` with a fake whose `get_signing_key_from_jwt` returns the matching public key. The Neon Auth REST proxies are tested with `requests_mock` (already a transitive dev dep via pytest plugins).

**File**: `{WORKSPACE}/api/modules/auth/tests/test_service.py` (new)

```python
"""Unit tests for modules.auth.service.

Each test mints a synthetic RS256 JWT signed with a freshly-generated keypair
and monkeypatches modules.auth.service._JWKS_CLIENT with a stub whose
get_signing_key_from_jwt returns the matching public key. No network calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from modules.auth import service
from modules.auth.models import User


def _make_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def _install_jwks_stub(monkeypatch, public_key):
    stub = MagicMock()
    stub.get_signing_key_from_jwt.return_value = MagicMock(key=public_key)
    monkeypatch.setattr(service, "_JWKS_CLIENT", stub)


def _mint_jwt(private_key, claims):
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_verify_jwt_returnsClaimsForValidToken(monkeypatch):
    private_key, public_key = _make_keypair()
    _install_jwks_stub(monkeypatch, public_key)
    token = _mint_jwt(private_key, {"sub": "u-123", "email": "a@b.co", "aud": "authenticated"})

    claims = service.verify_jwt(token)

    assert claims["sub"] == "u-123"
    assert claims["email"] == "a@b.co"


def test_verify_jwt_raisesOnExpiredToken(monkeypatch):
    private_key, public_key = _make_keypair()
    _install_jwks_stub(monkeypatch, public_key)
    token = _mint_jwt(
        private_key,
        {"sub": "u-1", "aud": "authenticated", "exp": 1},  # epoch 1970-01-01
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        service.verify_jwt(token)


def test_verify_jwt_raisesOnWrongAudience(monkeypatch):
    private_key, public_key = _make_keypair()
    _install_jwks_stub(monkeypatch, public_key)
    token = _mint_jwt(private_key, {"sub": "u-1", "aud": "not-authenticated"})

    with pytest.raises(jwt.InvalidAudienceError):
        service.verify_jwt(token)


def test_verify_jwt_raisesOnTamperedSignature(monkeypatch):
    real_private, _ = _make_keypair()
    _, decoy_public = _make_keypair()
    _install_jwks_stub(monkeypatch, decoy_public)
    token = _mint_jwt(real_private, {"sub": "u-1", "aud": "authenticated"})

    with pytest.raises(jwt.InvalidSignatureError):
        service.verify_jwt(token)


def test_send_magic_link_postsToNeonAuthEndpoint(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        resp = MagicMock()
        resp.json.return_value = {"request_id": "req-abc"}
        resp.raise_for_status = lambda: None
        return resp

    monkeypatch.setattr(service.requests, "post", fake_post)
    monkeypatch.setattr(service, "_NEON_AUTH_API_BASE", "https://auth.example")
    monkeypatch.setattr(service, "_NEON_AUTH_PROJECT_ID", "proj-1")

    result = service.send_magic_link("a@b.co")

    assert result == {"request_id": "req-abc"}
    assert captured["url"] == "https://auth.example/v1/projects/proj-1/auth/magic-link/send"
    assert captured["json"]["email"] == "a@b.co"


def test_verify_magic_link_returnsJwtAndClaims(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        resp = MagicMock()
        resp.json.return_value = {"jwt": "abc.def.ghi", "claims": {"sub": "u-1"}}
        resp.raise_for_status = lambda: None
        return resp

    monkeypatch.setattr(service.requests, "post", fake_post)

    result = service.verify_magic_link("one-time-token")

    assert result["jwt"] == "abc.def.ghi"
    assert result["claims"]["sub"] == "u-1"


def test_get_or_create_user_returnsExistingRow():
    existing = User(id=42, auth_user_id="u-1", email="a@b.co")
    repo = MagicMock()
    repo.get_by_auth_user_id.return_value = existing

    result = service.get_or_create_user_from_claims(
        {"sub": "u-1", "email": "a@b.co"}, repo
    )

    assert result is existing
    repo.create.assert_not_called()


def test_get_or_create_user_createsRowWhenAbsent():
    created = User(id=7, auth_user_id="u-2", email="c@d.co")
    repo = MagicMock()
    repo.get_by_auth_user_id.return_value = None
    repo.create.return_value = created

    result = service.get_or_create_user_from_claims(
        {"sub": "u-2", "email": "c@d.co"}, repo
    )

    assert result is created
    repo.create.assert_called_once_with(auth_user_id="u-2", email="c@d.co")
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest modules/auth/tests/test_service.py -v
```
Expect 8 tests, all `PASSED`.

---

## 5. Tests

The 8 unit tests in `modules/auth/tests/test_service.py` cover:

1. `test_verify_jwt_returnsClaimsForValidToken` — happy path with synthetic keypair
2. `test_verify_jwt_raisesOnExpiredToken` — `exp: 1` triggers `ExpiredSignatureError`
3. `test_verify_jwt_raisesOnWrongAudience` — `aud` mismatch triggers `InvalidAudienceError`
4. `test_verify_jwt_raisesOnTamperedSignature` — wrong public key triggers `InvalidSignatureError`
5. `test_send_magic_link_postsToNeonAuthEndpoint` — URL + body shape asserted
6. `test_verify_magic_link_returnsJwtAndClaims` — response payload pass-through
7. `test_get_or_create_user_returnsExistingRow` — idempotent upsert path
8. `test_get_or_create_user_createsRowWhenAbsent` — first-login row creation

Every assertion has a concrete value or instance check; no `assert True`, no `# TODO`.

---

## 6. Commit Plan

**Commit 1** — `feat(auth): add pyjwt[crypto] dependency for RS256 JWT verification`
- Files: `api/requirements.txt`
- What: append `pyjwt[crypto]>=2.8.0` + `cryptography>=42.0.0`

**Commit 2** — `feat(auth/service): add Neon Auth verify_jwt + magic-link proxies + user upsert`
- Files: `api/modules/auth/service.py`
- What: four pure functions; no Flask imports

**Commit 3** — `test(auth): unit tests for service.verify_jwt, magic-link, user upsert`
- Files: `api/modules/auth/tests/__init__.py`, `api/modules/auth/tests/test_service.py`
- What: 8 unit tests with synthetic RSA keypairs

**Co-Authored-By trailer** (verbatim, every commit):
```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

**Deviation logging**: if any step deviates, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: N → N+8 passing (8 new service tests). Zero pre-existing tests broken.

```bash
cd {WORKSPACE}/api && python -m flake8 modules/auth/service.py modules/auth/tests/test_service.py
```

Expect zero flake8 violations.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` in reverse order (commit 3 → 2 → 1).
- **Per-branch**: if verification fails, `git reset --hard <pre-task-sha>`. The only file modified outside `modules/auth/` is `api/requirements.txt` — diff is two appended lines.

---

## 9. Deviations Allowed

- **`requirements.txt` already pins `pyjwt`** (without `[crypto]`) — replace the existing pin with `pyjwt[crypto]>=2.8.0`; log in commit 1 body.
- **`UserRepository.get_by_auth_user_id` is named differently** in saas-persistence (e.g., `find_by_auth_user_id`) — adopt the existing name in `get_or_create_user_from_claims` and update the test; log in commit 2 body.
- **`User.auth_user_id` field is named differently** (e.g., `auth_id`) — adopt the existing name across `service.py` and tests; log in commit 2 body.
- **Side-effect required** (network call, schema change) — STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.

---

## 10. Out of Scope

Task 1 ships only the pure-Python service. Decorator, routes, and any Flask wiring belong in Task 2.

- **`@require_auth` decorator** — Task 2; depends on `verify_jwt` being importable, which Task 1 delivers
- **`auth_bp` Flask blueprint** — Task 2
- **`/api/auth/login`, `/verify`, `/logout`, `/me` route handlers** — Task 2
- **OpenAPI schema entries for the four routes** — Task 2 (after handlers exist)
- **Decorator additions to existing routes** — Task 3
- **Angular auth service / interceptor / login components** — Task 4

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for this module
- [Epic](./epic.md) — Task scope and ordering
- [Timeline](./timeline.md) — Update status to `done` after verification passes

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
