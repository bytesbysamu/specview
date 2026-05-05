# Task 4: Contract Integration Tests

## 1. Context

Task 4 adds four integration test classes that close structural gaps the existing 250-test suite cannot reach: every test today runs `CHAIN_PROVIDER=mock` through the Flask test client, which bypasses CORS middleware, never enforces a consistent error-envelope shape across all registered routes, never validates response JSON against `server/openapi/*.yaml` at runtime, and leaves the `CHAIN_PROVIDER=claude` SDK path entirely untested. The `pytest-httpserver` Claude stub is the most consequential addition — it is the first test in the entire suite that exercises the actual Anthropic SDK HTTP layer. Registering the `real_claude` marker in `pyproject.toml` is the infrastructure deliverable; no test body carries it in this task.

**Trade-offs considered:**
- **Per-route test duplication** (one function per route, hardcoded) — rejected; every new blueprint registration would silently miss coverage. App-`url_map` introspection and parametrize cover the full registered surface automatically.
- **Patching the Anthropic SDK client directly via `unittest.mock.patch`** — rejected; patches the mock shape, not the HTTP wire. `pytest-httpserver` intercepts at the network layer, proving the full `_make_client() → SDK → WSGI → route` path. The "mock provider passes, real provider broken" failure mode is only caught at the network layer.
- **`pytest-httpserver` with a lazy `_make_client()` factory in `claude.py`** — preferred; `monkeypatch.setenv("ANTHROPIC_BASE_URL", stub_url)` is sufficient to redirect the SDK without `importlib.reload`, the change is four lines to an existing file, and the adapter boundary (`server/modules/chain/adapter.py`) is untouched.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
git status
git diff HEAD -- \
  server/modules/chain/providers/claude.py \
  server/tests/conftest.py \
  server/requirements-dev.txt \
  pyproject.toml
cd server && pytest --tb=no -q 2>&1 | tail -3   # record baseline pass count
```

**Before writing error-envelope and OpenAPI test cases, read these files to confirm exact URL patterns:**

```bash
grep -n "def test_\|client\.\(get\|post\|put\|delete\)" \
  server/tests/test_text_routes.py \
  server/tests/test_waitlist_routes.py \
  server/modules/tracking/tests/*.py
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: \_\_/\_\_ passing.

---

## 3. Files

### To Create (new)
- `server/tests/test_contracts.py` — four contract test classes (~90 lines); imports payload factories established in Task 1

### To Modify (cite CODEBASE CONTEXT)
- `server/modules/chain/providers/claude.py` — replace module-level `client = Anthropic(...)` singleton with `_make_client()` factory that reads `ANTHROPIC_BASE_URL` at call time; allows `monkeypatch.setenv` to redirect SDK HTTP without `importlib.reload`
- `server/requirements-dev.txt` — add `pytest-httpserver>=1.1`; `jsonschema` and `pyyaml` may already be present — verify before adding
- `pyproject.toml` — add `integration` and `real_claude` markers under `[tool.pytest.ini_options]`; do not remove any markers Task 1 already registered
- `server/tests/conftest.py` — add function-scoped `auth_headers` fixture that inserts a test user + valid magic-link token via SQLAlchemy ORM, returns `{"Authorization": "Bearer <token>"}` dict

### To Leave Alone
- `server/modules/chain/adapter.py` — adapter boundary; the `_make_client()` change is internal to the provider; the `generate` / `stream` interface signatures are unchanged
- `server/tests/test_routes.py`, `server/tests/test_text_routes.py`, `server/tests/test_text_chain_routes.py` — existing 250-test suite; must not break
- `server/tests/test_structural.py` — structural invariant tests; no coupling changes here
- `server/app.py` — Flask factory and CORS registration; this task verifies correctness without touching the source

---

## 4. Implementation Steps

### Step 1: Make claude provider client lazy

**Action**: In `server/modules/chain/providers/claude.py`, remove the module-level `client = Anthropic(...)` singleton. Replace with a `_make_client()` factory called at the top of both `create_message` and `stream_message`. Read `ANTHROPIC_BASE_URL` inside the factory so `monkeypatch.setenv` in Step 5's test takes effect at call time rather than import time.

**File**: `server/modules/chain/providers/claude.py` (existing — `server/modules/chain/` per CODEBASE CONTEXT)

**Pattern** (port from `humanize-me/backend/services/claude.py`, lines 1–15, with lazy-client addition):
```python
import os
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
# ServiceError import: from server.core.errors import ServiceError
# (or wherever it is centralised in this repo — see Deviations Allowed)

def _make_client() -> Anthropic:
    """Create a fresh client per-call; reads ANTHROPIC_BASE_URL at call time for test isolation."""
    kwargs: dict = {"timeout": 60.0, "max_retries": 2}
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return Anthropic(**kwargs)


def create_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096) -> str:
    client = _make_client()          # was: module-level client
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except RateLimitError:
        raise ServiceError("AI service is busy. Please try again.", 503)
    except APIConnectionError:
        raise ServiceError("Cannot connect to AI service.", 502)
    except APIError as e:
        raise ServiceError(f"AI service error: {e.message}", 502)


def stream_message(system: str, prompt: str, *, model: str, max_tokens: int = 4096):
    client = _make_client()          # was: module-level client
    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                yield text
    except RateLimitError:
        yield "\n\n[Error: AI service is busy. Please try again.]"
    except APIConnectionError:
        yield "\n\n[Error: Cannot connect to AI service.]"
    except APIError as e:
        yield f"\n\n[Error: {e.message}]"
```

**Verify**: `cd server && pytest tests/test_chain_integration.py -q` — all pre-existing chain integration tests pass unchanged.

---

### Step 2: Add pytest-httpserver to dev requirements

**Action**: Open `server/requirements-dev.txt`. Check whether `jsonschema` and `pyyaml` are already listed (both are likely present as transitive deps; add them explicitly if absent). Append `pytest-httpserver>=1.1`.

**File**: `server/requirements-dev.txt` (existing — CODEBASE CONTEXT, Dependencies table)

**Pattern**:
```
# existing entries…
pytest-httpserver>=1.1
jsonschema>=4.0       # add only if not already present
pyyaml>=6.0           # add only if not already present
```

**Verify**: `pip install -r server/requirements-dev.txt && python -c "from pytest_httpserver import HTTPServer; print('ok')"` — prints `ok`, exits 0.

---

### Step 3: Register markers in pyproject.toml

**Action**: Add `integration` and `real_claude` to the `markers` list under `[tool.pytest.ini_options]`. If Task 1 already registered `unit`, `e2e`, `snapshot` — preserve them. If `pyproject.toml` has no `[tool.pytest.ini_options]` section, create one.

**File**: `pyproject.toml` (existing — workspace root or `server/`; check both with `ls pyproject.toml server/pyproject.toml`)

**Pattern**:
```toml
[tool.pytest.ini_options]
markers = [
    "unit: isolated unit tests with no I/O",
    "integration: cross-boundary tests (CORS, error-envelope, schema, SDK path)",
    "e2e: browser-driven end-to-end scenarios",
    "snapshot: golden-file assertion tests",
    "real_claude: calls the live Anthropic API — requires ANTHROPIC_API_KEY; excluded from CI default",
]
```

**Verify**: `cd server && pytest --markers 2>&1 | grep -E "integration|real_claude"` — both lines appear.

---

### Step 4: Add auth_headers fixture to conftest.py

**Action**: Add a function-scoped `auth_headers` fixture to `server/tests/conftest.py`. Use SQLAlchemy ORM model classes (no raw SQL — architecture rule). The fixture creates a test user and a non-expired magic-link token in the test SQLite DB, then yields the headers dict. Teardown is automatic via function scope.

**File**: `server/tests/conftest.py` (existing — established in Task 1)

**Pattern**:
```python
import uuid
from datetime import datetime, timedelta

@pytest.fixture
def auth_headers(db_session):
    """Insert a test user + non-expired magic-link token; return Authorization header dict.

    Import paths below are guesses — verify against the actual ORM models in
    server/modules/user/models.py and server/core/auth.py before running.
    """
    from server.modules.user.models import User          # verify import path
    from server.core.auth import MagicLinkToken          # verify import path

    user_id = str(uuid.uuid4())
    raw_token = str(uuid.uuid4())

    db_session.add(User(id=user_id, email="contract-test@example.com"))
    db_session.add(MagicLinkToken(
        token=raw_token,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    ))
    db_session.commit()
    return {"Authorization": f"Bearer {raw_token}"}
```

**Verify**: `cd server && pytest tests/ --collect-only -q 2>&1 | grep "auth_headers\|ERROR"` — no collection errors; existing test count unchanged.

---

### Step 5: Write test_contracts.py

**Action**: Create `server/tests/test_contracts.py` with the four contract test classes below. **Before writing the `_CASES` list and the OpenAPI test paths, confirm exact route URLs by reading `server/tests/test_text_routes.py` and `server/tests/test_waitlist_routes.py`**; replace the URL strings in the file if they differ from what is written here.

**File**: `server/tests/test_contracts.py` (new)

**Pattern**:
```python
"""Contract integration tests — four classes, four rules.

  TestCorsContract          every /api/ route returns Allow-Origin on OPTIONS + actual requests
  TestErrorEnvelopeContract every 4xx/5xx response is {"error": <str>} JSON
  TestOpenApiResponseShape  happy-path responses validate against server/openapi/*.yaml
  TestClaudeProviderPath    CHAIN_PROVIDER=claude propagates a stub response end-to-end
"""
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tests.fixtures.payloads import (
    make_rewrite_request,
    make_waitlist_request,
    make_tracking_request,
)

ALLOWED_ORIGIN = "http://localhost:4201"
OPENAPI_DIR = Path(__file__).parents[1] / "openapi"

# ── 1. CORS ───────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestCorsContract:
    """Every /api/ route returns Access-Control-Allow-Origin — preflight and actual request."""

    def _api_rules(self, app):
        return [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/")]

    def test_preflight_allApiRoutes_returnAllowOrigin(self, client, app):
        for rule in self._api_rules(app):
            resp = client.options(
                rule.rule,
                headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "POST"},
            )
            assert "Access-Control-Allow-Origin" in resp.headers, (
                f"CORS preflight missing on {rule.rule} — "
                "was this blueprint registered without the Flask-CORS decorator?"
            )

    def test_actualRequest_allApiRoutes_returnAllowOrigin(self, client, app):
        for rule in self._api_rules(app):
            method = next(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
            resp = getattr(client, method.lower())(
                rule.rule, json={}, headers={"Origin": ALLOWED_ORIGIN}
            )
            assert "Access-Control-Allow-Origin" in resp.headers, (
                f"CORS header absent on {method} {rule.rule}"
            )


# ── 2. Error Envelope ─────────────────────────────────────────────────────────

@pytest.mark.integration
class TestErrorEnvelopeContract:
    """Every 4xx/5xx response is application/json with an 'error' key."""

    # Verify these URLs against test_text_routes.py and test_waitlist_routes.py
    # before running; update if the actual prefixes differ.
    _CASES = [
        ("/api/text/rewrite", "post", {}),
        ("/api/text/generate", "post", {}),
        ("/api/waitlist/email", "post", {}),
        ("/api/nonexistent-contract-xyz", "get", None),
    ]

    @pytest.mark.parametrize("path,verb,body", _CASES)
    def test_errorStatus_returnsJsonErrorKey(self, client, path, verb, body):
        resp = getattr(client, verb)(path, json=body)
        assert resp.status_code >= 400, (
            f"{verb.upper()} {path}: expected 4xx/5xx, got {resp.status_code}"
        )
        data = resp.get_json()
        assert data is not None, (
            f"{verb.upper()} {path}: response body is not JSON"
        )
        assert "error" in data, (
            f"{verb.upper()} {path}: missing 'error' key; got {data!r}"
        )
        assert resp.content_type.startswith("application/json"), (
            f"{verb.upper()} {path}: Content-Type is {resp.content_type!r}"
        )


# ── 3. OpenAPI Response Shape ─────────────────────────────────────────────────

@pytest.mark.integration
class TestOpenApiResponseShape:
    """Happy-path responses validate against the schema in server/openapi/*.yaml."""

    @staticmethod
    def _response_schema(spec_file: str, path: str, method: str, status: str) -> dict:
        with (OPENAPI_DIR / spec_file).open() as f:
            spec = yaml.safe_load(f)
        return (
            spec["paths"][path][method]["responses"][status]
            ["content"]["application/json"]["schema"]
        )

    def test_waitlistSignup_matchesOpenApiSchema(self, client):
        schema = self._response_schema("waitlist.yaml", "/api/waitlist/email", "post", "201")
        resp = client.post("/api/waitlist/email", json=make_waitlist_request())
        assert resp.status_code == 201
        jsonschema.validate(resp.get_json(), schema)

    def test_trackingEvent_matchesOpenApiSchema(self, client):
        schema = self._response_schema("tracking.yaml", "/api/tracking/event", "post", "200")
        resp = client.post("/api/tracking/event", json=make_tracking_request())
        assert resp.status_code == 200
        jsonschema.validate(resp.get_json(), schema)


# ── 4. Claude SDK Provider Path ───────────────────────────────────────────────

_STUB_CLAUDE_RESPONSE = {
    "id": "msg_contract_test_01",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "contract-test-output"}],
    "model": "claude-opus-4-6-20250805",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


@pytest.mark.integration
class TestClaudeProviderPath:
    """CHAIN_PROVIDER=claude → SDK HTTP → pytest-httpserver stub → response reaches caller.

    This is the only test in the suite that sets CHAIN_PROVIDER=claude.
    All 250 pre-existing tests use CHAIN_PROVIDER=mock.
    """

    def test_claudeProvider_textRewrite_propagatesStubResponse(
        self, httpserver, monkeypatch, app, auth_headers
    ):
        httpserver.expect_request("/v1/messages", method="POST").respond_with_json(
            _STUB_CLAUDE_RESPONSE
        )
        monkeypatch.setenv("ANTHROPIC_BASE_URL", httpserver.url_for(""))
        monkeypatch.setenv("CHAIN_PROVIDER", "claude")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-contract-key")

        with app.test_client() as c:
            resp = c.post(
                "/api/text/rewrite",
                json=make_rewrite_request(),
                headers=auth_headers,
            )

        assert resp.status_code == 200, (
            f"expected 200, got {resp.status_code}; body: {resp.get_data(as_text=True)!r}"
        )
        body = resp.get_json() or {}
        assert "contract-test-output" in json.dumps(body), (
            f"stub response text not propagated through route; got: {body!r}"
        )
```

**Verify**: `cd server && pytest tests/test_contracts.py -m integration -v` — 9 tests collected (2 CORS + 4 error-envelope parametrized + 2 OpenAPI + 1 httpserver); all pass.

---

## 5. Tests

The test file in Step 5 **is** the test deliverable. All assertions are complete. No stubs. For reference, the nine assertion points are:

```python
# TestCorsContract (2 tests — loop over all /api/ routes)
assert "Access-Control-Allow-Origin" in resp.headers, "preflight missing Allow-Origin"
assert "Access-Control-Allow-Origin" in resp.headers, "actual request missing Allow-Origin"

# TestErrorEnvelopeContract (4 parametrized tests — one per _CASES entry)
assert resp.status_code >= 400
assert resp.get_json() is not None          # body is parseable JSON
assert "error" in resp.get_json()           # envelope key present
assert resp.content_type.startswith("application/json")

# TestOpenApiResponseShape (2 tests)
assert resp.status_code == 201              # waitlist signup success
jsonschema.validate(resp.get_json(), schema)  # response matches YAML schema
assert resp.status_code == 200              # tracking event success
jsonschema.validate(resp.get_json(), schema)

# TestClaudeProviderPath (1 test)
assert resp.status_code == 200
assert "contract-test-output" in json.dumps(resp.get_json())
```

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after completing each step — not once at the end. Each boundary below maps to a step above. Do not move to the next step until the verify command passes and the commit is made.

1. `refactor(chain): make claude provider client lazy for test-time ANTHROPIC_BASE_URL override` — after Step 1 — `server/modules/chain/providers/claude.py`: replaces module-level singleton with `_make_client()` factory
2. `chore(deps): add pytest-httpserver, jsonschema, pyyaml to dev requirements` — after Step 2 — `server/requirements-dev.txt`: adds three dev deps
3. `chore(test): register integration and real_claude pytest markers` — after Step 3 — `pyproject.toml`: two new marker declarations alongside Task 1 markers
4. `test(contracts): add auth_headers fixture for integration tests requiring auth` — after Step 4 — `server/tests/conftest.py`: function-scoped fixture, ORM-based insert
5. `test(contracts): add CORS, error-envelope, OpenAPI shape, and Claude SDK path contract tests` — after Step 5 — `server/tests/test_contracts.py`: four classes, 9 test functions

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd server
pytest tests/test_contracts.py -m integration -v --tb=short
```

**Expected delta**: baseline N → N+9 passing. Zero pre-existing tests broken.

To run only the httpserver stub class in isolation:

```bash
pytest tests/test_contracts.py::TestClaudeProviderPath -v --tb=short
```

To confirm the `real_claude` marker is registered but carries no tests:

```bash
pytest -m real_claude --collect-only -q   # expect: "no tests ran"
```

Full suite regression check:

```bash
pytest --tb=short -q 2>&1 | tail -5
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` without `--no-edit`.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>`. The pre-task SHA is the `HEAD` recorded during Pre-flight.

The laziness change to `claude.py` (Step 1) is the highest-risk modification — it changes how the Anthropic client is instantiated in every production AI call. If chain integration tests (`test_chain_integration.py`) regress after Step 1, revert that commit only and re-examine the `ServiceError` import path; the remaining steps have no dependency on each other.

---

## 9. Deviations Allowed

- **`ServiceError` import path unknown** → inspect `server/core/` and find the centralized exception class; if it does not exist yet and is defined inline in `claude.py`, leave the inline definition intact and import it from there.
- **`User` or `MagicLinkToken` model import paths differ from guide** → read `server/modules/user/models.py` and `server/core/auth.py`; use actual class names and column names; log the corrected imports as a deviation in the Step 4 commit.
- **`db_session` fixture not present in conftest.py from Task 1** → check existing test files for the session fixture name (may be `session`, `test_db`, or similar); use the correct name and log as a deviation.
- **Route URLs in `_CASES` and OpenAPI tests differ from actual routes** → read the existing test files (Step 5 pre-condition) and use confirmed URLs; log each substitution as a deviation in the Step 5 commit body.
- **`make_tracking_request` not in `tests/fixtures/payloads.py` from Task 1** → create a minimal inline factory `lambda: {"event": "page_view", "page": "/landing"}` inside the test class; log the deviation; flag to the Task 1 author that the factory is missing.
- **Text rewrite route uses streaming only (no JSON response body)** → switch the httpserver test to target `/api/text/generate` (open generation), which is more likely to use `chain.adapter.generate` (non-streaming); adjust `make_rewrite_request()` to `make_generate_request()` accordingly.
- **Side-effect required** (schema migration, push, publish) → STOP, mark [REQUIRES APPROVAL] and flag before proceeding.

---

## 10. Out of Scope

Task 4 delivers four integration test classes and the `real_claude` marker as registered infrastructure. It does not author any test body that carries the `real_claude` marker, does not set up CI pipeline changes to run integration tests separately from unit tests, and does not address the five E2E scenarios (Task 5) or snapshot golden files (Task 3). An eager executor may notice the `real_claude` marker is defined but unused and be tempted to write a smoke test using the live Anthropic API — this is explicitly deferred.

- **Test bodies carrying `real_claude`** — deferred; trigger is the first paying user justifying per-CI-run Anthropic API cost. The marker exists so local pre-deploy smoke tests can be tagged `pytest -m real_claude`.
- **CI matrix split** (integration tests in a separate workflow job from unit tests) — deferred; trigger is integration test suite growing past 30 seconds. Currently 9 tests plus the existing suite is one `pytest` invocation.
- **CORS `CORS_ORIGINS` env-var matrix** — the CORS contract tests confirm the header is present; they do not assert the exact origin value against the `CORS_ORIGINS` env var. Parametrizing over multiple origin values (allowed, blocked, wildcard) is deferred until a second CORS configuration exists or a CORS misconfiguration reaches production.
- **E2E `[data-test]` selector retrofit** — Task 5 scope; the contract tests here are pure backend and do not touch Angular templates.
- **OpenAPI coverage for auth-required routes** — the OpenAPI shape tests are scoped to unauthenticated routes (waitlist, tracking) to stay within the 80-line budget. Extending to photoshoot and text endpoints requires the `auth_headers` fixture (Step 4) and `make_photoshoot_request` / auth-aware happy-path payloads; deferred until Task 1's payload factory set is confirmed complete.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than absorbing scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, Parametrized Contract Matrix pattern, Provider Stub pattern
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Update status to ✅ Done after verification passes