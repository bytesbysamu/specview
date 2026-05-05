# Task 2: `@require_auth` Decorator + `auth_bp` Routes

## 1. Context

Task 2 adds the Flask-aware seam over Task 1's pure service. Two files: `decorators.py` (the single `@require_auth` decorator that hydrates `g.current_user`) and `routes.py` (the `auth_bp` blueprint with four endpoints — login, verify, logout, me). Register `auth_bp` in `create_app.py`. Add the four endpoints to `openapi.yaml` and regenerate `dtos/models.py`. The structural test `everyOpenapiPath_hasRouteHandler` enforces that every OpenAPI path has a corresponding handler.

The decorator is the contract every other capability depends on. Mon-T2/T3 usage decorator and the billing webhook handler both expect `g.current_user` to be a hydrated `User` SQLModel instance. Setting `g.current_user` (not `g.user_id`) keeps a single round-trip to fetch the row; downstream consumers read `email`, `plan`, `id` from the same object without re-fetching.

**Trade-offs considered:**
- **Before-request hook instead of decorator** — rejected; per-route opt-in is explicit; `/health` and `/api/auth/*` stay public without conditional logic; matches the bubls Spring Security shape.
- **Decorator returns 403 vs 401 on missing token** — 401 chosen; "missing or invalid credentials" maps to 401, "credentials valid but lacking permission" maps to 403; this capability has no permission tier yet.
- **`/api/auth/me` lazy-creates the user vs requires verify-first** — lazy-create chosen; the decorator already calls `get_or_create_user_from_claims`, so `/api/auth/me` is the simplest possible handler.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
git status
git diff HEAD -- {WORKSPACE}/api/openapi.yaml {WORKSPACE}/api/create_app.py
cd {WORKSPACE}/api && python -m pytest --tb=short -q 2>&1 | tail -3
```

Record the passing test count from the last command as **N**.

Confirm `modules.auth.service` exposes `verify_jwt`, `get_or_create_user_from_claims`, `send_magic_link`, `verify_magic_link`. If not, Task 1 is incomplete; stop.

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/api/modules/auth/decorators.py` (new) — the `@require_auth` decorator
- `{WORKSPACE}/api/modules/auth/routes.py` (new) — `auth_bp` blueprint with four route handlers
- `{WORKSPACE}/api/modules/auth/tests/test_decorators.py` (new) — 4 unit tests for the decorator
- `{WORKSPACE}/api/modules/auth/tests/test_routes.py` (new) — 6 integration tests for the four routes

### To Modify
- `{WORKSPACE}/api/create_app.py` — append `('modules.auth.routes', 'auth_bp')` to `ENABLED_MODULES`
- `{WORKSPACE}/api/openapi.yaml` — add four `paths` entries (`/api/auth/login`, `/api/auth/verify`, `/api/auth/logout`, `/api/auth/me`) and the matching request/response component schemas (`MagicLinkRequest`, `MagicLinkResponse`, `VerifyRequest`, `VerifyResponse`, `MeResponse`)
- `{WORKSPACE}/api/dtos/models.py` — regenerated from openapi via `make generate-dtos`; do NOT hand-edit

### To Leave Alone
- `{WORKSPACE}/api/modules/auth/service.py` — Task 1 deliverable; consumed but not modified
- `{WORKSPACE}/api/modules/auth/models.py` — saas-persistence `User` model; consumed but not modified

---

## 4. Implementation Steps

### Step 1: Add the four OpenAPI path entries

**Action**: Edit `openapi.yaml`. Add four `paths` entries and the five component schemas. Run `make generate-dtos` after the edit. The structural test `everyOpenapiPath_hasRouteHandler` will fail until Step 4 adds the route handlers — that is expected; do not run `make test` between this step and Step 4.

**File**: `{WORKSPACE}/api/openapi.yaml` (modify)

Under `paths:`, add:

```yaml
  /api/auth/login:
    post:
      operationId: requestMagicLink
      tags: [auth]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MagicLinkRequest'
      responses:
        '202':
          description: Magic-link dispatch accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MagicLinkResponse'
  /api/auth/verify:
    post:
      operationId: verifyMagicLink
      tags: [auth]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VerifyRequest'
      responses:
        '200':
          description: Token exchanged for JWT
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VerifyResponse'
  /api/auth/logout:
    post:
      operationId: signOut
      tags: [auth]
      responses:
        '204':
          description: Client-side discard acknowledged
  /api/auth/me:
    get:
      operationId: getCurrentUser
      tags: [auth]
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Current authenticated user
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MeResponse'
```

Under `components: schemas:`, add:

```yaml
    MagicLinkRequest:
      type: object
      required: [email]
      properties:
        email:
          type: string
          format: email
    MagicLinkResponse:
      type: object
      required: [request_id]
      properties:
        request_id:
          type: string
    VerifyRequest:
      type: object
      required: [token]
      properties:
        token:
          type: string
    VerifyResponse:
      type: object
      required: [jwt, user]
      properties:
        jwt:
          type: string
        user:
          $ref: '#/components/schemas/MeResponse'
    MeResponse:
      type: object
      required: [id, email, auth_user_id]
      properties:
        id:
          type: integer
        email:
          type: string
        auth_user_id:
          type: string
```

If `bearerAuth` is not yet declared in `components: securitySchemes:`, add:

```yaml
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

**Verify**:
```bash
cd {WORKSPACE}/api && make generate-dtos && python -c "from dtos.models import MagicLinkRequest, MagicLinkResponse, VerifyRequest, VerifyResponse, MeResponse; print('ok')"
```
Expect `ok`.

---

### Step 2: Write the `@require_auth` decorator

**Action**: Create `decorators.py`. Read `Authorization` header, return 401 on missing/non-Bearer/invalid, else call `verify_jwt`, hydrate `g.current_user`, dispatch.

**File**: `{WORKSPACE}/api/modules/auth/decorators.py` (new)

```python
"""@require_auth decorator — the only Flask-aware seam in modules/auth/.

Reads Authorization: Bearer <token>, validates via service.verify_jwt, hydrates
g.current_user via service.get_or_create_user_from_claims, dispatches to the
wrapped handler. Returns 401 on missing or invalid credentials.

g.current_user is the contract every downstream capability (Mon-T2/T3 usage
decorator, billing webhook handler) reads from. Do not change the attribute
name without coordinating with those consumers.
"""
from __future__ import annotations

from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from modules.auth.service import get_or_create_user_from_claims, verify_jwt


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401

        token = header[len("Bearer "):]
        try:
            claims = verify_jwt(token)
        except jwt.PyJWTError as exc:
            return jsonify({"error": f"invalid token: {exc.__class__.__name__}"}), 401

        g.current_user = get_or_create_user_from_claims(
            claims, current_app.user_repository
        )
        return fn(*args, **kwargs)

    return wrapper
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "from modules.auth.decorators import require_auth; print('ok')"
```
Expect `ok`.

---

### Step 3: Write the `auth_bp` blueprint with four route handlers

**Action**: Create `routes.py`. Four handlers; each parses with the generated DTOs, calls the appropriate service function, serializes via the response DTO. `/api/auth/me` is the only route guarded by `@require_auth`.

**File**: `{WORKSPACE}/api/modules/auth/routes.py` (new)

```python
"""Flask blueprint for /api/auth/* — login, verify, logout, me.

Routes are thin: parse via DTO, call service, serialize. The @require_auth
decorator is mounted only on /api/auth/me; the other three routes must remain
public so unauthenticated users can request and exchange a magic link.
"""
from __future__ import annotations

import requests
from flask import Blueprint, g, jsonify, request

from dtos.models import (
    MagicLinkRequest,
    MagicLinkResponse,
    MeResponse,
    VerifyRequest,
    VerifyResponse,
)
from modules.auth.decorators import require_auth
from modules.auth.service import (
    get_or_create_user_from_claims,
    send_magic_link,
    verify_magic_link,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    req = MagicLinkRequest.model_validate(request.get_json() or {})
    try:
        result = send_magic_link(req.email)
    except requests.HTTPError as exc:
        return jsonify({"error": f"neon auth rejected request: {exc}"}), 502
    return jsonify(MagicLinkResponse(request_id=result["request_id"]).model_dump()), 202


@auth_bp.post("/verify")
def verify():
    req = VerifyRequest.model_validate(request.get_json() or {})
    try:
        exchange = verify_magic_link(req.token)
    except requests.HTTPError as exc:
        return jsonify({"error": f"invalid or expired token: {exc}"}), 400

    user = get_or_create_user_from_claims(
        exchange["claims"], current_app_user_repository()
    )
    payload = VerifyResponse(
        jwt=exchange["jwt"],
        user=MeResponse(id=user.id, email=user.email, auth_user_id=user.auth_user_id),
    )
    return jsonify(payload.model_dump()), 200


@auth_bp.post("/logout")
def logout():
    # Server-side no-op — Neon Auth owns session lifecycle. The client clears
    # localStorage; we acknowledge with 204.
    return ("", 204)


@auth_bp.get("/me")
@require_auth
def me():
    user = g.current_user
    payload = MeResponse(id=user.id, email=user.email, auth_user_id=user.auth_user_id)
    return jsonify(payload.model_dump()), 200


# ── helper ───────────────────────────────────────────────────────────────────

def current_app_user_repository():
    """Indirection so tests can monkeypatch a repo without app context tricks."""
    from flask import current_app
    return current_app.user_repository
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "from modules.auth.routes import auth_bp; print(auth_bp.url_prefix)"
```
Expect `/api/auth`.

---

### Step 4: Register `auth_bp` in `ENABLED_MODULES`

**Action**: Append the auth blueprint entry. The exact `ENABLED_MODULES` shape varies — current entries look like `('modules.<feature>.routes', '<feature>_bp')` — preserve the existing convention.

**File**: `{WORKSPACE}/api/create_app.py` (modify)

Append `('modules.auth.routes', 'auth_bp')` to the `ENABLED_MODULES` list (after the last existing entry).

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "from create_app import create_app; app = create_app(); print('auth' in app.blueprints)"
```
Expect `True`.

---

### Step 5: Write `test_decorators.py`

**Action**: Four unit tests. Each builds a Flask test app, mounts a single `@require_auth`-decorated handler, and asserts the response code and body shape.

**File**: `{WORKSPACE}/api/modules/auth/tests/test_decorators.py` (new)

```python
"""Unit tests for the @require_auth decorator."""
from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest
from flask import Flask, g, jsonify

from modules.auth import decorators, service
from modules.auth.models import User


@pytest.fixture
def app(monkeypatch):
    application = Flask(__name__)
    application.user_repository = MagicMock()
    application.user_repository.get_by_auth_user_id.return_value = User(
        id=1, auth_user_id="u-1", email="a@b.co"
    )

    @application.route("/protected")
    @decorators.require_auth
    def protected():
        return jsonify({"user_id": g.current_user.id})

    return application


def test_require_auth_returns401WhenHeaderMissing(app):
    client = app.test_client()
    resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "missing bearer token"}


def test_require_auth_returns401WhenHeaderNotBearer(app):
    client = app.test_client()
    resp = client.get("/protected", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "missing bearer token"}


def test_require_auth_returns401OnInvalidToken(app, monkeypatch):
    def bad_verify(token):
        raise jwt.InvalidSignatureError("bad sig")

    monkeypatch.setattr(decorators, "verify_jwt", bad_verify)
    client = app.test_client()
    resp = client.get("/protected", headers={"Authorization": "Bearer xxx"})
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "invalid token: InvalidSignatureError"}


def test_require_auth_setsCurrentUserAndDispatches(app, monkeypatch):
    monkeypatch.setattr(decorators, "verify_jwt", lambda t: {"sub": "u-1", "email": "a@b.co"})
    client = app.test_client()
    resp = client.get("/protected", headers={"Authorization": "Bearer good"})
    assert resp.status_code == 200
    assert resp.get_json() == {"user_id": 1}
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest modules/auth/tests/test_decorators.py -v
```
Expect 4 tests, all `PASSED`.

---

### Step 6: Write `test_routes.py`

**Action**: Six integration tests for the four routes — login (success + Neon Auth error), verify (success + bad token), logout, me (success).

**File**: `{WORKSPACE}/api/modules/auth/tests/test_routes.py` (new)

```python
"""Integration tests for the /api/auth/* blueprint."""
from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest
import requests
from flask import Flask

from modules.auth import decorators, routes, service
from modules.auth.models import User


@pytest.fixture
def app():
    application = Flask(__name__)
    application.user_repository = MagicMock()
    application.user_repository.get_by_auth_user_id.return_value = User(
        id=99, auth_user_id="u-99", email="e@f.co"
    )
    application.register_blueprint(routes.auth_bp)
    return application


def test_login_returns202WithRequestId(app, monkeypatch):
    monkeypatch.setattr(routes, "send_magic_link", lambda email: {"request_id": "req-1"})
    client = app.test_client()
    resp = client.post("/api/auth/login", json={"email": "a@b.co"})
    assert resp.status_code == 202
    assert resp.get_json() == {"request_id": "req-1"}


def test_login_returns502WhenNeonAuthRejects(app, monkeypatch):
    def boom(email):
        err = requests.HTTPError("500 Server Error")
        raise err

    monkeypatch.setattr(routes, "send_magic_link", boom)
    client = app.test_client()
    resp = client.post("/api/auth/login", json={"email": "a@b.co"})
    assert resp.status_code == 502
    assert "neon auth rejected" in resp.get_json()["error"]


def test_verify_returns200WithJwtAndUser(app, monkeypatch):
    monkeypatch.setattr(routes, "verify_magic_link", lambda t: {
        "jwt": "abc.def.ghi",
        "claims": {"sub": "u-99", "email": "e@f.co"},
    })
    client = app.test_client()
    resp = client.post("/api/auth/verify", json={"token": "one-time"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["jwt"] == "abc.def.ghi"
    assert body["user"]["id"] == 99
    assert body["user"]["auth_user_id"] == "u-99"


def test_verify_returns400WhenTokenInvalid(app, monkeypatch):
    def boom(token):
        raise requests.HTTPError("400 Bad Request")

    monkeypatch.setattr(routes, "verify_magic_link", boom)
    client = app.test_client()
    resp = client.post("/api/auth/verify", json={"token": "bad"})
    assert resp.status_code == 400
    assert "invalid or expired token" in resp.get_json()["error"]


def test_logout_returns204(app):
    client = app.test_client()
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert resp.data == b""


def test_me_returnsCurrentUser(app, monkeypatch):
    monkeypatch.setattr(decorators, "verify_jwt", lambda t: {"sub": "u-99", "email": "e@f.co"})
    client = app.test_client()
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer good"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == 99
    assert body["email"] == "e@f.co"
    assert body["auth_user_id"] == "u-99"
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest modules/auth/tests/test_routes.py -v
```
Expect 6 tests, all `PASSED`.

---

## 5. Tests

10 new tests added in this task:

- 4 in `test_decorators.py`: missing header, non-Bearer scheme, invalid token, success path
- 6 in `test_routes.py`: login success, login Neon Auth error, verify success, verify bad token, logout 204, me success

Plus the structural test `everyOpenapiPath_hasRouteHandler` continues to pass once Step 4 lands.

Every assertion has a concrete value or status code; no `assert True`, no `# TODO`.

---

## 6. Commit Plan

**Commit 1** — `feat(auth): add openapi entries and DTOs for /api/auth/* routes`
- Files: `api/openapi.yaml`, `api/dtos/models.py` (regenerated)
- What: four path entries, five component schemas, regenerate DTOs

**Commit 2** — `feat(auth): add @require_auth decorator hydrating g.current_user`
- Files: `api/modules/auth/decorators.py`, `api/modules/auth/tests/test_decorators.py`
- What: decorator + 4 unit tests

**Commit 3** — `feat(auth): add auth_bp routes (login, verify, logout, me)`
- Files: `api/modules/auth/routes.py`, `api/create_app.py`, `api/modules/auth/tests/test_routes.py`
- What: blueprint + ENABLED_MODULES registration + 6 integration tests

**Co-Authored-By trailer** (verbatim, every commit):
```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

**Deviation logging**: if any step deviates, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api && make check-dtos
cd {WORKSPACE}/api && python -m pytest --tb=short -q
cd {WORKSPACE}/api && python -m flake8 modules/auth/decorators.py modules/auth/routes.py modules/auth/tests/test_decorators.py modules/auth/tests/test_routes.py
```

**Expected delta**: N → N+10 passing (4 decorator + 6 route tests). Zero pre-existing tests broken.

`make check-dtos` exits 0 (DTOs match openapi). flake8 reports zero violations.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` in reverse order (commit 3 → 2 → 1).
- **Per-branch**: if verification fails entirely, `git reset --hard <pre-task-sha>`. The only files modified outside `modules/auth/` are `api/openapi.yaml`, `api/dtos/models.py` (regenerable), and `api/create_app.py` (one-line append).

---

## 9. Deviations Allowed

- **`bearerAuth` security scheme already exists** in openapi.yaml — skip the `securitySchemes` block in Step 1; log in commit 1 body.
- **`current_app.user_repository` is named differently** (e.g., `current_app.users`) — adopt the existing attribute in `decorators.py` and `routes.py`; log in commit 2/3 body.
- **DTO name collision** (`MagicLinkRequest` etc. already exist) — rename the new schemas with an `Auth` prefix (`AuthMagicLinkRequest`); log in commit 1 body.
- **Side-effect required** (network call, schema change) — STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.

---

## 10. Out of Scope

Task 2 ships only the auth surface itself. Decorating existing routes belongs to Task 3; Angular work belongs to Task 4.

- **Adding `@require_auth` to `modules/ai/`, `modules/data/projects/`, etc. routes** — Task 3
- **Repository call rewrites (`list()` → `list_for_user(g.current_user.id)`)** — Task 3
- **Angular auth service / interceptor / login components** — Task 4
- **`/api/me` endpoint** — superseded by `/api/auth/me` in this task; the brain dump's `/api/me` is the same endpoint under a different path
- **Server-side session table or refresh-token store** — out of scope; Neon Auth owns session lifecycle

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for this module
- [Epic](./epic.md) — Task scope and ordering
- [Task 1](./task-1-auth-service-jwt-verifier.md) — Service layer this task wires
- [Timeline](./timeline.md) — Update status to `done` after verification passes

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
