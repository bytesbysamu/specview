# 🛠️ Task 4: Register in ENABLED_MODULES + smoke test

**Purpose**: Wire the waitlist module (built by Tasks 1–3) into the Flask application by adding it to `ENABLED_MODULES` in `server/app.py`, then verify end-to-end that the signup endpoint responds and the health check reports the module as loaded.

**Effort**: 15m

**Dependencies**: Task 1 (model + migration), Task 2 (OpenAPI + DTOs), Task 3 (routes + service + repository)

**Parallel With**: —

**Blocks**: Task 5 (port Trendfy subscribers — requires the table + endpoint to be wired), Task 6 (delete email-api/)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Tasks 1–3 built the waitlist module's internals — model, migration, OpenAPI spec, DTOs, routes, service, and repository — but none of them touched `server/app.py`. The module exists on disk but Flask doesn't know about it yet: no blueprint is registered, so `POST /api/waitlist/signup` returns 404. This task adds `"waitlist"` to the `ENABLED_MODULES` list in `server/app.py` so `create_app()` discovers and registers the waitlist blueprint alongside existing modules (e.g. `photoshoot`, `user`). A pytest smoke-test file then locks the wiring so future module-list edits don't silently drop waitlist. Manual curl against the running server confirms the full stack (Flask → service → repository → Neon) is connected.

**Trade-offs considered**:
- **Lazy import via `importlib` vs. explicit import in `create_app`** — the codebase already uses `ENABLED_MODULES` with dynamic iteration (`create_app()` iterates the list); follow the established pattern rather than adding a hard-coded import.
- **Smoke tests in a dedicated file vs. appending to an existing integration test file** — dedicated `test_waitlist_smoke.py` keeps the wiring assertions isolated from Task 3's endpoint-logic tests in `test_waitlist_routes.py`, making failures unambiguous.
- **Automated smoke only vs. automated + manual curl** — both: the pytest suite runs in CI, the curl command is a one-shot sanity check against a live database that catches config/migration issues the test DB can't.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}
git status                                              # Flag any unrelated M/?? entries
git log -1 --format='%H' > /tmp/pretask4-sha            # Rollback anchor
git diff HEAD -- server/app.py                          # Confirm target file is clean

# Verify Task 1–3 deliverables exist
ls server/modules/waitlist/__init__.py                  # Task 1
ls server/modules/waitlist/models.py                    # Task 1
ls server/modules/waitlist/dto.py                       # Task 2
ls server/openapi/waitlist.yaml                         # Task 2
ls server/modules/waitlist/routes.py                    # Task 3
ls server/modules/waitlist/service.py                   # Task 3
ls server/modules/waitlist/repository.py                # Task 3

# Confirm the blueprint object exists in routes.py
grep -n "^bp = Blueprint" server/modules/waitlist/routes.py

# Confirm current ENABLED_MODULES contents
grep -n "ENABLED_MODULES" server/app.py

# Baseline test count
cd server && python -m pytest -q 2>&1 | tail -3        # Record [N] passed
```

**If working tree is dirty on `server/app.py`**: stash or commit unrelated changes separately BEFORE starting.

**If any Task 1–3 deliverable is missing**: STOP — this task cannot proceed. Flag which file is absent and which prior task owns it.

**Baseline recorded**: capture `[N]` passed from pytest output — goes into the commit body.

---

## 3. Files

### To Create (new)
- `server/tests/test_waitlist_smoke.py` (new) — 4 pytest cases verifying module registration, route visibility, signup happy path, and health-endpoint inclusion.

### To Modify
- `server/app.py` — append `"waitlist"` to the `ENABLED_MODULES` list. One line change.

### To Leave Alone
- `server/modules/waitlist/__init__.py` — Task 1 deliverable. Already exists as a package marker.
- `server/modules/waitlist/models.py` — Task 1 deliverable. Do not modify.
- `server/modules/waitlist/routes.py` — Task 3 deliverable. Contains `bp = Blueprint("waitlist", ...)`. Do not modify.
- `server/modules/waitlist/service.py` — Task 3 deliverable. Do not modify.
- `server/modules/waitlist/repository.py` — Task 3 deliverable. Do not modify.
- `server/modules/waitlist/dto.py` — Task 2 deliverable. Do not modify.
- `server/openapi/waitlist.yaml` — Task 2 deliverable. Do not modify.
- `server/migrations/versions/20260417_create_waitlist_signups.py` — Task 1 migration. Never edit past migrations.
- `server/modules/photoshoot/**` — unrelated feature module.
- `server/modules/user/**` — unrelated feature module.
- `server/modules/chain/**` — unrelated infrastructure module.
- `server/tests/test_waitlist_model.py` — Task 1 test. Do not modify.
- `server/tests/test_waitlist_dto.py` — Task 2 test. Do not modify.
- All frontend files (`src/app/**`) — no frontend changes in this task.

---

## 4. Implementation Steps

### Step 1: Add `"waitlist"` to `ENABLED_MODULES`

**Action**: Open `server/app.py` and append `"waitlist"` to the `ENABLED_MODULES` list. Follow the existing list style (one entry per line if multi-line, or inline if single-line — match what's there).

**File**: `server/app.py` (modify)

**Pattern**:
```python
# Before (example — match the actual list format found in Pre-flight)
ENABLED_MODULES = [
    "photoshoot",
    "user",
]

# After
ENABLED_MODULES = [
    "photoshoot",
    "user",
    "waitlist",
]
```

If the list uses a different format (e.g., `ENABLED_MODULES = ["photoshoot", "user"]` on one line), follow that style. The key invariant: `"waitlist"` appears exactly once in the list.

**Verify**: `grep '"waitlist"' server/app.py` — expect one match inside `ENABLED_MODULES`.

### Step 2: Verify blueprint registration

**Action**: Run a Python one-liner to confirm `create_app()` registers the waitlist routes.

**File**: read-only verification.

**Pattern**:
```bash
cd server && python -c "
from app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules() if 'waitlist' in r.rule]
print(rules)
assert '/api/waitlist/signup' in rules, f'Missing signup route. Found: {rules}'
print('OK: waitlist routes registered')
"
```

**Verify**: Output includes `'/api/waitlist/signup'` and prints `OK: waitlist routes registered`. If `create_app` fails to import or the route is missing, STOP — check that Task 3's `routes.py` defines `bp = Blueprint("waitlist", __name__, url_prefix="/api/waitlist")` and that `server/app.py`'s module iteration logic uses the same pattern as existing modules.

### Step 3: Write smoke tests

**Action**: Create `server/tests/test_waitlist_smoke.py` with 4 test cases covering wiring correctness. Uses the existing `conftest.py` Flask test `client` and `db_session` fixtures.

**File**: `server/tests/test_waitlist_smoke.py` (new)

See **Section 5** for complete test bodies.

**Verify**: `cd server && python -m pytest tests/test_waitlist_smoke.py -q` — expect 4 passed.

### Step 4: Manual smoke test against running server [REQUIRES APPROVAL]

**Action**: Start the Flask dev server, run curl against the live endpoint, then verify the health check. This confirms end-to-end wiring including the real Neon database.

**File**: none (manual verification).

**Pattern**:
```bash
# Terminal 1: start the server (port discovered from server/app.py or run config)
cd server && python app.py

# Terminal 2: smoke-test the signup endpoint
curl -s -w "\nHTTP %{http_code}\n" \
  -X POST http://localhost:5001/api/waitlist/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke-test-task4@example.com"}'
# Expect: HTTP 201, JSON body with id, email, source, created_at

# Verify health endpoint includes waitlist
curl -s http://localhost:5001/api/health | python -m json.tool
# Expect: "modules" list includes "waitlist"

# Cleanup: delete the smoke-test row (optional — idempotent signup handles it)
```

**Verify**: `HTTP 201` response with a JSON body containing `"email": "smoke-test-task4@example.com"` and `"source": "landing_page"`. Health endpoint JSON includes `"waitlist"` in its modules list. If the health endpoint does not exist or does not include a modules list, log as a deviation — the wiring is still correct if Step 2 passed.

---

## 5. Tests

All tests use the existing pytest `conftest.py` fixtures (`client`, `db_session`). Match the repo's naming convention: `condition_expectedOutcome`.

```python
# server/tests/test_waitlist_smoke.py
"""Smoke tests for waitlist module wiring.

Verifies that server/app.py registers the waitlist blueprint and the
signup endpoint is reachable end-to-end through the Flask test client.
"""


class TestWaitlistModuleRegistration:
    """Wiring checks — module in ENABLED_MODULES, routes visible."""

    def test_waitlistRoutes_registeredInApp(self, client):
        """The /api/waitlist/signup route is present in the URL map."""
        rules = [
            rule.rule
            for rule in client.application.url_map.iter_rules()
            if "waitlist" in rule.rule
        ]
        assert "/api/waitlist/signup" in rules, (
            f"Waitlist signup route not registered. Found rules: {rules}. "
            "Check that 'waitlist' is in ENABLED_MODULES in server/app.py "
            "and that server/modules/waitlist/routes.py defines bp."
        )

    def test_healthEndpoint_includesWaitlist(self, client):
        """GET /api/health reports waitlist as a loaded module."""
        resp = client.get("/api/health")
        assert resp.status_code == 200, f"Health endpoint returned {resp.status_code}"
        body = resp.get_json()
        modules = body.get("modules", [])
        assert "waitlist" in modules, (
            f"'waitlist' not in health modules list: {modules}. "
            "Check ENABLED_MODULES in server/app.py."
        )


class TestWaitlistSignupSmoke:
    """End-to-end smoke through Flask test client + test DB."""

    def test_validEmail_returns201WithSignupBody(self, client, db_session):
        resp = client.post(
            "/api/waitlist/signup",
            json={"email": "smoke@example.com"},
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.get_json()}"
        )
        body = resp.get_json()
        assert body["email"] == "smoke@example.com"
        assert body["source"] == "landing_page"
        assert "id" in body
        assert "created_at" in body

    def test_duplicateEmail_returns409(self, client, db_session):
        # First signup succeeds
        resp1 = client.post(
            "/api/waitlist/signup",
            json={"email": "dupe@example.com"},
        )
        assert resp1.status_code == 201

        # Second signup with same email returns conflict
        resp2 = client.post(
            "/api/waitlist/signup",
            json={"email": "dupe@example.com"},
        )
        assert resp2.status_code == 409, (
            f"Expected 409 for duplicate, got {resp2.status_code}: {resp2.get_json()}"
        )
        body = resp2.get_json()
        assert "error" in body
```

**Note on fixtures**: If `client` and `db_session` fixtures do not exist in `server/tests/conftest.py`, inspect what Task 3's `test_waitlist_routes.py` uses — it must have established a test-client fixture since it tested the same endpoint. Reuse that fixture. If no shared conftest exists, create a minimal one inline at the top of this file (SQLite in-memory engine + `create_app()` test config) and log the deviation.

---

## 6. Commit Plan

One commit (this is a 15-minute wiring task — one logical unit):

1. `feat(waitlist): register module in ENABLED_MODULES + smoke tests` — `server/app.py`, `server/tests/test_waitlist_smoke.py`: add `"waitlist"` to module list, 4 smoke tests verifying route registration, health inclusion, and end-to-end signup.

**Commit body template**:
```
Baseline: [N] pytest passing (pre-task4)
Delta: +4 (smoke tests)
Manual curl: 201 confirmed against localhost:5001

Deviations: [none, or list each]
```

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd server && python -m pytest -q
```

**Expected delta**: `[N]` → `[N+4]` passing. Zero pre-existing tests broken.

Additionally, after the automated suite passes:

```bash
# Confirm the one-liner still works
cd server && python -c "
from app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules() if 'waitlist' in r.rule]
assert '/api/waitlist/signup' in rules
print('PASS: waitlist registered')
"
```

---

## 8. Rollback

- **Per-step**: single commit is independently revertible. `git revert <sha>`.
- **Per-branch**: if verification fails catastrophically, `git reset --hard $(cat /tmp/pretask4-sha)` to return to the pre-task state.
- **Partial rollback**: if only the `server/app.py` change needs reverting (e.g., it breaks another module), remove `"waitlist"` from `ENABLED_MODULES` — the module files from Tasks 1–3 remain intact and can be re-wired later.

---

## 9. Deviations Allowed

- **`ENABLED_MODULES` format differs from the example** (e.g., uses dotted paths like `"modules.waitlist"` instead of `"waitlist"`) → match the format of existing entries; log the deviation.
- **`create_app()` function signature or import path differs** → adapt the verify one-liner to match; log in commit body.
- **Health endpoint does not exist or does not report modules** → skip the health-related test (`test_healthEndpoint_includesWaitlist`) by marking it `pytest.mark.skip(reason="no /api/health endpoint found")` and log the deviation. The wiring is still valid if Step 2's route check passes.
- **Test fixtures (`client`, `db_session`) are not available in conftest** → inspect Task 3's test file for the fixture pattern; create a minimal conftest or inline fixture. Log the deviation.
- **Port is not 5001** → use whatever port `server/app.py` configures. Log the actual port in the commit body.
- **`bp` variable in `routes.py` has a different name** (e.g., `waitlist_bp`) → check what `create_app()` expects and whether it imports by convention (`bp`) or by explicit name. Adapt accordingly; log deviation.

---

## 10. Out of Scope

This task wires an existing module and smoke-tests it. It does not build, extend, or modify any module internals. The following are explicitly deferred:

- **Frontend waitlist form** — no Angular components, services, or routes are created. Frontend integration is a separate task after the backend is fully wired and validated.
- **Email confirmation / welcome email** — the architecture explicitly defers email sending ("No auth, no admin surface, no email sending"). Not part of this task.
- **Admin surface for viewing signups** — deferred per architecture; revisit after first 100 signups demonstrate signal.
- **Rate limiting on the signup endpoint** — architecture specifies in-memory per-IP rate limiting, but implementation belongs in Task 3's routes.py. If Task 3 deferred it, it stays deferred here.
- **CI/CD pipeline changes** — no GitHub Actions workflow modifications. The existing `pytest` step in CI will automatically pick up the new smoke tests.
- **Delete `email-api/`** — Task 6 handles cleanup of the legacy email service. Do not touch it here.
- **Trendfy subscriber port** — Task 5 handles the data migration. Do not run it as part of this task's verification.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale and module layout
- [Epic](./epic.md) – Task scope and execution phases
- [Timeline](./timeline.md) – Status tracking (update after done)