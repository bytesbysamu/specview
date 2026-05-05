# Task 3: Protect Existing Routes With `@require_auth`

## 1. Context

Task 3 closes the per-tenant gap. Every existing handler in `modules/ai/routes/`, `modules/data/projects/routes.py`, `modules/data/context/routes.py`, `modules/data/templates/routes.py` gains the `@require_auth` decorator from Task 2. Where a handler currently calls a global repository method (`list_projects()`), it switches to the user-scoped variant (`list_for_user(g.current_user.id)`); the saas-persistence migration already added these `_for_user` methods, but no caller was wired. The `/health` route and the `/api/auth/*` routes stay public.

The integration tests for every protected route gain a single `auth_headers` pytest fixture that mints a synthetic RS256 JWT signed by a test keypair and monkeypatches `service._JWKS_CLIENT` and `current_app.user_repository` to return a known user. Tests change once via the fixture; route behaviour changes once per route via the decorator.

This is a low-risk decorator-sprinkle pass — every change is a one-line addition above the route function plus, where applicable, a one-line repository call swap. The risk surface is the test fixture: if it doesn't honour the decorator's contract, every protected-route test breaks.

**Trade-offs considered:**
- **Conditional decorator (decorator no-ops on `/health`)** — rejected; explicit decorator placement is clearer; one-line addition per route is acceptable.
- **Apply decorator via `before_request` on the blueprint** — rejected; `auth_bp` and `health_bp` are separate, and per-route opt-in keeps the contract visible at the call site.
- **Mint test JWT inside each test** — rejected; one fixture is shorter, less repetitive, and makes future JWT-shape changes a single-file edit.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
git status
cd {WORKSPACE}/api && python -m pytest --tb=short -q 2>&1 | tail -3
```

Record the passing test count from the last command as **N**.

Confirm Task 2 is complete: `from modules.auth.decorators import require_auth` works from `{WORKSPACE}/api`.

Inventory the routes to protect:

```bash
grep -rEn "@\w+_bp\.(get|post|put|delete|patch)\(" {WORKSPACE}/api/modules/ai/routes {WORKSPACE}/api/modules/data
```

Expect a list of every route handler. The decorator goes immediately after the `@<bp>.<verb>(...)` line on every route in `modules/ai/routes/` and `modules/data/{projects,context,templates}/routes.py`.

---

## 3. Files

### To Modify
- `{WORKSPACE}/api/modules/ai/routes/*.py` — every handler gains `@require_auth`
- `{WORKSPACE}/api/modules/data/projects/routes.py` — every handler gains `@require_auth`; `list_projects()` → `list_for_user(g.current_user.id)`; `create_project(...)` accepts `user_id=g.current_user.id`
- `{WORKSPACE}/api/modules/data/context/routes.py` — every handler gains `@require_auth`
- `{WORKSPACE}/api/modules/data/templates/routes.py` — every handler gains `@require_auth`

### To Create (new)
- `{WORKSPACE}/api/tests/conftest.py` (modify if exists, create if not) — add `auth_headers` fixture that mints a test JWT and monkeypatches the JWKS client + user repository

### To Leave Alone
- `{WORKSPACE}/api/modules/health/routes.py` — `/health` stays public
- `{WORKSPACE}/api/modules/auth/routes.py` — `/api/auth/login`, `/verify`, `/logout` stay public; `/me` is already decorated by Task 2
- `{WORKSPACE}/api/openapi.yaml` — every existing protected path schema needs `security: - bearerAuth: []` added; do this in Step 4

---

## 4. Implementation Steps

### Step 1: Add the `auth_headers` test fixture

**Action**: Add a fixture to `tests/conftest.py` that generates a per-session RSA keypair, monkeypatches `service._JWKS_CLIENT` to a stub returning the matching public key, mints a JWT, and returns `{"Authorization": "Bearer <jwt>"}`. Also monkeypatch `current_app.user_repository` to return a known `User` for `get_by_auth_user_id`.

**File**: `{WORKSPACE}/api/tests/conftest.py` (modify — append fixture; create file if absent)

```python
"""Shared pytest fixtures."""
from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask

from modules.auth import service
from modules.auth.models import User


@pytest.fixture
def test_user():
    return User(id=1, auth_user_id="u-test", email="test@example.com")


@pytest.fixture
def auth_headers(monkeypatch, test_user):
    """Mint a synthetic RS256 JWT and wire JWKS + user repo stubs.

    Usage:
        def test_protected(client, auth_headers):
            resp = client.get('/api/projects', headers=auth_headers)
            assert resp.status_code == 200
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    jwks_stub = MagicMock()
    jwks_stub.get_signing_key_from_jwt.return_value = MagicMock(key=public_key)
    monkeypatch.setattr(service, "_JWKS_CLIENT", jwks_stub)

    token = jwt.encode(
        {"sub": test_user.auth_user_id, "email": test_user.email, "aud": "authenticated"},
        private_key,
        algorithm="RS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patch_user_repository(monkeypatch, test_user):
    """Replace current_app.user_repository with a stub returning test_user."""
    repo = MagicMock()
    repo.get_by_auth_user_id.return_value = test_user
    repo.create.return_value = test_user

    # Late-bind so the patch fires inside the request context.
    def _set(app: Flask):
        app.user_repository = repo

    return _set
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest tests/conftest.py --collect-only -q 2>&1 | tail -3
```
Expect no collection errors.

---

### Step 2: Decorate every route in `modules/ai/routes/`

**Action**: For each `*.py` file under `modules/ai/routes/`, add `from modules.auth.decorators import require_auth` and apply `@require_auth` immediately after the `@<bp>.<verb>(...)` line on every handler.

**Example** (representative; apply the same pattern to every file):

```python
# Before
@ai_bp.post("/rewrite")
def rewrite():
    ...

# After
from modules.auth.decorators import require_auth

@ai_bp.post("/rewrite")
@require_auth
def rewrite():
    ...
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "
import inspect
from modules.ai.routes import ai_bp
import modules.ai.routes as r
for rule in r.__loader__.get_data  # noqa
"
# Simpler functional check:
cd {WORKSPACE}/api && python -m pytest modules/ai/tests -k "test_" -q 2>&1 | tail -5
```
Expect existing AI tests to either pass with `auth_headers` injected or fail with 401 — both confirm the decorator is wired. Step 6 updates the tests; this step only confirms the decorator is in place.

---

### Step 3: Decorate every route in `modules/data/projects/routes.py` and switch to user-scoped repository calls

**Action**: Apply `@require_auth` to every handler. Where the handler currently calls `current_app.project_repository.list()`, replace with `current_app.project_repository.list_for_user(g.current_user.id)`. Where the handler creates a project, pass `user_id=g.current_user.id` as a keyword argument.

**File**: `{WORKSPACE}/api/modules/data/projects/routes.py` (modify)

For each route:

```python
# Before
@projects_bp.get("/")
def list_projects():
    return jsonify(current_app.project_repository.list())

# After
from flask import g
from modules.auth.decorators import require_auth

@projects_bp.get("/")
@require_auth
def list_projects():
    return jsonify(current_app.project_repository.list_for_user(g.current_user.id))
```

```python
# Before
@projects_bp.post("/")
def create_project():
    req = CreateProjectRequest.model_validate(request.get_json())
    project = current_app.project_repository.create(name=req.name, files=req.files)
    return jsonify(project)

# After
@projects_bp.post("/")
@require_auth
def create_project():
    req = CreateProjectRequest.model_validate(request.get_json())
    project = current_app.project_repository.create(
        user_id=g.current_user.id, name=req.name, files=req.files
    )
    return jsonify(project)
```

Apply the same pattern to `get_project`, `update_project`, `delete_project`, and any file-level read/write handlers — every route gains both the decorator and the user-scoped repository call.

**Verify**:
```bash
cd {WORKSPACE}/api && grep -E "@projects_bp\.(get|post|put|delete)" -A 1 modules/data/projects/routes.py
```
Every `@projects_bp.<verb>` line is followed by `@require_auth`.

---

### Step 4: Decorate every route in `modules/data/context/routes.py` and `modules/data/templates/routes.py`

**Action**: Apply `@require_auth` to every handler. Context and templates are read-only from the user's perspective in v1; no repository call swap needed yet (single user → single context set). The decorator still goes on so the `g.current_user.id` is available for future per-user context overrides.

**File**: `{WORKSPACE}/api/modules/data/context/routes.py` (modify)
**File**: `{WORKSPACE}/api/modules/data/templates/routes.py` (modify)

```python
# Before
@context_bp.get("/<key>")
def get_context(key: str):
    return jsonify({"content": read_context(key)})

# After
from modules.auth.decorators import require_auth

@context_bp.get("/<key>")
@require_auth
def get_context(key: str):
    return jsonify({"content": read_context(key)})
```

**Verify**:
```bash
cd {WORKSPACE}/api && grep -E "@(context|templates)_bp\.(get|post|put|delete)" -A 1 modules/data/context/routes.py modules/data/templates/routes.py
```
Every blueprint route line is followed by `@require_auth`.

---

### Step 5: Add `security: - bearerAuth: []` to every protected path in `openapi.yaml`

**Action**: Edit `openapi.yaml`. For every `paths` entry under `/api/projects/*`, `/api/context/*`, `/api/templates/*`, `/api/ai/*`, add a top-level `security: [- bearerAuth: []]` to the operation. Do not touch `/health` or `/api/auth/login`, `/api/auth/verify`, `/api/auth/logout`.

**Example pattern**:

```yaml
  /api/projects:
    get:
      operationId: listProjects
      security:
        - bearerAuth: []
      responses:
        '200':
          ...
```

After editing, regenerate DTOs (no shape change expected; the regen confirms the YAML is still valid):

```bash
cd {WORKSPACE}/api && make generate-dtos
```

**Verify**:
```bash
cd {WORKSPACE}/api && make check-dtos && grep -c "bearerAuth" openapi.yaml
```
`make check-dtos` exits 0; the bearerAuth count exceeds the number of `auth_bp` routes (one per protected path, plus the `securitySchemes` declaration).

---

### Step 6: Update existing integration tests to inject `auth_headers`

**Action**: For every existing test that calls `client.get("/api/...")` or `client.post(...)` against a now-protected route, add `headers=auth_headers` to the call and add the `auth_headers` and `patch_user_repository` fixtures to the test signature. Where the test uses an in-process Flask app fixture, call `patch_user_repository(app)` to attach the stub repository.

**Representative diff** (apply to every existing test that hits a protected route):

```python
# Before
def test_list_projects_returnsArray(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)

# After
def test_list_projects_returnsArray(client, app, auth_headers, patch_user_repository):
    patch_user_repository(app)
    resp = client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q 2>&1 | tail -5
```
Expect zero pre-existing tests broken; every protected-route test passes with the auth_headers fixture.

---

### Step 7: Add a "no token = 401" smoke test per blueprint

**Action**: Add one negative test per protected blueprint asserting an unauthenticated request returns 401. This guards against accidental decorator removal.

**File**: `{WORKSPACE}/api/tests/test_route_protection.py` (new)

```python
"""Smoke tests asserting every protected blueprint rejects unauthenticated requests."""


def test_projects_routes_reject_anonymous(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 401


def test_context_routes_reject_anonymous(client):
    resp = client.get("/api/context/builder")
    assert resp.status_code == 401


def test_templates_routes_reject_anonymous(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 401


def test_ai_text_rewrite_rejects_anonymous(client):
    resp = client.post("/api/ai/text/rewrite", json={"text": "x", "instructions": "y"})
    assert resp.status_code == 401


def test_health_remains_public(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_auth_login_remains_public(client):
    # No body required to assert the route exists and is reachable without a JWT.
    # Neon Auth call is monkeypatched in the auth tests; here we assert the
    # route does NOT return 401 — the absence of auth-rejection is the assertion.
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code != 401
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest tests/test_route_protection.py -v
```
Expect 6 tests, all `PASSED`.

---

## 5. Tests

This task adds 6 new tests in `tests/test_route_protection.py` (one per protected blueprint + two public smoke tests) and modifies every existing protected-route test to inject `auth_headers`. The fixture itself is a single addition to `tests/conftest.py`.

Test count delta: N → N+6. Modified tests do not change count.

Every assertion is concrete (status code or instance check); no `assert True`, no `# TODO`.

---

## 6. Commit Plan

**Commit 1** — `test(auth): add auth_headers fixture for protected-route integration tests`
- Files: `api/tests/conftest.py`
- What: `auth_headers`, `patch_user_repository`, `test_user` fixtures

**Commit 2** — `feat(ai): protect every /api/ai/text/* route with @require_auth`
- Files: `api/modules/ai/routes/*.py`
- What: decorator on every handler; tests updated to inject auth_headers

**Commit 3** — `feat(data): protect projects/context/templates routes with @require_auth and switch to per-user repository calls`
- Files: `api/modules/data/projects/routes.py`, `api/modules/data/context/routes.py`, `api/modules/data/templates/routes.py`
- What: decorator + `list_for_user(g.current_user.id)` swap on projects routes

**Commit 4** — `feat(openapi): add bearerAuth security requirement to every protected path`
- Files: `api/openapi.yaml`, `api/dtos/models.py` (regenerated)
- What: security: [- bearerAuth: []] on every protected operation

**Commit 5** — `test(auth): smoke tests asserting protected blueprints reject anonymous requests`
- Files: `api/tests/test_route_protection.py`
- What: 6 new tests

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
cd {WORKSPACE}/api && python -m flake8 modules/data modules/ai/routes tests/conftest.py tests/test_route_protection.py
```

**Expected delta**: N → N+6 passing (6 new protection smoke tests). Zero pre-existing tests broken.

`make check-dtos` exits 0; flake8 reports zero violations.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` in reverse order (commit 5 → 4 → 3 → 2 → 1).
- **Per-route revert**: removing `@require_auth` from a single handler is a one-line revert; the decorator has no side effects beyond setting `g.current_user`.

---

## 9. Deviations Allowed

- **A protected route already has its own decorator stack** (e.g., `@cache_page`) — apply `@require_auth` *outermost* so authentication happens before any other concern; log in commit body.
- **`current_app.project_repository.list_for_user` does not exist** — saas-persistence may have shipped a differently-named user-scoped method (e.g., `list_owned_by`); adopt the existing name; log in commit 3 body.
- **`current_app.project_repository.create` does not accept `user_id` kwarg** — inspect the signature; if the column is `owner_id`, use that; log in commit 3 body.
- **An integration test is xfailed/xskipped** — leave as-is; log in commit body if a new failure mode appears.
- **Side-effect required** (network call, schema change) — STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.

---

## 10. Out of Scope

Task 3 ships only the decorator pass and per-user repo-call swap. New features, new routes, new context overrides are out of scope.

- **Per-user context overrides** (different `builder.md` per user) — single user owns single context set in v1; re-scope when a paying user asks
- **Workspace / org / team primitives** — explicitly out of scope per the architecture
- **Angular auth surface** — Task 4
- **Billing webhook handler / usage decorator** — those are downstream consumers; this task only ensures the contract (`g.current_user`) is honoured everywhere
- **Removing the `/health` public exemption** — `/health` is consumed by uptime checks and CI; stays public

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for this module
- [Epic](./epic.md) — Task scope and ordering
- [Task 1](./task-1-auth-service-jwt-verifier.md) — Service layer
- [Task 2](./task-2-require-auth-decorator-routes.md) — Decorator + auth_bp this task consumes
- [Timeline](./timeline.md) — Update status to `done` after verification passes

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
