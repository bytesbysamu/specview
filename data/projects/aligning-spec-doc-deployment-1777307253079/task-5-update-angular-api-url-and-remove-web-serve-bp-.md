Now I have everything I need to write the guide precisely.

# Task 5: Update Angular API URL and Remove `web_serve_bp`

## 1. Context

This task closes the gap left open by the compose split: Angular still hardcodes `http://localhost:3101/api` as its API base URL, and Flask still ships a `web_serve_bp` SPA catch-all that is now dead code once nginx owns the frontend container. After Task 3 deployed a verified two-container compose to Coolify, the Flask static-file fallback is safe to remove. The single Angular source change — `environment.apiUrl: '/api'` — makes the same relative path work in both environments: `proxy.conf.json` routes `/api` traffic to Flask on the Angular dev server; nginx does the same in every deployed environment. Removing `web_serve_bp` and its module directory cleans the Flask image of responsibilities that nginx now owns permanently.

**Trade-offs considered:**
- **Keep `web_serve_bp` as a no-op guard** — rejected because the directory being present causes `packages_areInExpectedHierarchy` to track it forever, invites accidental re-activation, and keeps dead code with no consumer.
- **Change `apiUrl` per-environment (`/api` in prod, absolute in dev)** — rejected because the relative path works identically in dev (via `proxy.conf.json`) and eliminates environment-specific branching that has to be maintained.
- **One-line `environment.ts` change + full module delete** — preferred because the split is already live and verified; there is no rollback scenario that requires the Flask fallback to reactivate.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Verify working tree is clean on the target files
git status
git diff HEAD -- \
  web/src/environments/environment.ts \
  api/create_app.py \
  api/tests/test_structural.py \
  api/tests/test_retire_express.py

# Confirm compose split is live (prerequisite gate for this task)
curl -sf https://<your-coolify-domain>/api/health | grep -q '"ok"' && echo "T3 live ✓" || echo "T3 NOT live — do not proceed"

# Record test baseline (run from api/)
cd api && make test 2>&1 | tail -3
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Gate check**: If the Coolify `/api/health` curl fails, **stop**. This task is explicitly gated on Task 3 being live and verified.

**Baseline recorded**: record the `N passed, M skipped` count from `make test` before touching anything.

---

## 3. Files

### To Create (new)
_(none)_

### To Modify (cite CODEBASE CONTEXT)
- `web/src/environments/environment.ts` — change `apiUrl` value from `'http://localhost:3101/api'` to `'/api'`
- `web/src/environments/environment.prod.ts` — same one-line change (if the file exists; verify with `ls web/src/environments/`)
- `api/create_app.py` — remove line 13 (`from modules.web_serve import web_serve_bp`) and lines 117–119 (comment + `app.register_blueprint(web_serve_bp)`)
- `api/tests/test_structural.py` — remove line 197 (`"web_serve"` entry from `SAAS_OPTIONAL`)
- `api/tests/test_retire_express.py` — **conditional**: remove `proxyConfJson_doesNotExist()` and `angularJson_hasNoProxyConfigReference()` only if they are currently failing (see Step 4 below)

### To Delete
- `api/modules/web_serve/__init__.py` — exported `web_serve_bp`; no consumer after removal from `create_app.py`
- `api/modules/web_serve/routes.py` — SPA catch-all route definitions
- `api/modules/web_serve/` — directory itself

### To Leave Alone
- `api/modules/web_serve/` tests — there are none; no test directory to clean up
- `api/Dockerfile` — already simplified by Task 3; the multi-stage Angular build stage is gone; do not re-edit
- `api/tests/test_docker.py` — docker tests are unchanged by this task
- `web/proxy.conf.json` — dev-server proxy config set up by Task 1/3; Task 5 does not touch it
- `web/angular.json` — already updated by the compose split tasks; do not touch
- All `api/modules/*` not listed above — no cross-module changes required

---

## 4. Implementation Steps

### Step 1: Update `environment.ts` API Base URL

**Action**: Open `web/src/environments/environment.ts`. Change the `apiUrl` property value from `'http://localhost:3101/api'` to `'/api'`. No other property changes.

**File**: `web/src/environments/environment.ts` (CODEBASE CONTEXT — `web/` Angular SPA)

**Pattern**:
```typescript
// Before
export const environment = {
  production: false,
  apiUrl: 'http://localhost:3101/api'   // ← old absolute dev URL
};

// After
export const environment = {
  production: false,
  apiUrl: '/api'                        // ← relative; proxy.conf.json routes in dev, nginx in prod
};
```

**Verify**:
```bash
grep "apiUrl" web/src/environments/environment.ts
# Expect: apiUrl: '/api'
# Expect: no 'localhost' substring
```

---

### Step 2: Update `environment.prod.ts` if it exists

**Action**: Check whether `web/src/environments/environment.prod.ts` exists. If it does, apply the identical one-line change: `apiUrl: '/api'`. If the file does not exist, skip this step (no action required).

**File**: `web/src/environments/environment.prod.ts` — (CODEBASE CONTEXT — `web/`)

**Pattern**:
```typescript
// After (if file exists)
export const environment = {
  production: true,
  apiUrl: '/api'   // nginx routes /api/ in every deployed environment
};
```

**Verify**:
```bash
ls web/src/environments/
# If environment.prod.ts is present:
grep "apiUrl" web/src/environments/environment.prod.ts
# Expect: apiUrl: '/api'
```

---

### Step 3: Remove `web_serve_bp` Import and Registration from `create_app.py`

**Action**: Edit `api/create_app.py`. Remove the top-level import on line 13 and the registration block on lines 117–119 (the comment and the `app.register_blueprint(web_serve_bp)` call). Leave all other imports and registrations intact.

**File**: `api/create_app.py` (CODEBASE CONTEXT — `api/`)

**Pattern** — before → after diff:
```python
# REMOVE line 13 entirely:
from modules.web_serve import web_serve_bp

# REMOVE lines 117-119 entirely:
    # web_serve_bp registers the Angular catch-all `/<path:path>`. Must be LAST
    # so it doesn't shadow `/api/*` or the routes above.
    app.register_blueprint(web_serve_bp)

# The function must still end with:
    return app
```

**Verify**:
```bash
grep "web_serve" api/create_app.py
# Expect: (no output)
```

---

### Step 4: Delete the `modules/web_serve/` Module Directory

**Action**: Remove the two files and their directory. Confirm the directory is gone.

**File**: `api/modules/web_serve/` (CODEBASE CONTEXT — `api/modules/`)

```bash
rm api/modules/web_serve/__init__.py
rm api/modules/web_serve/routes.py
rmdir api/modules/web_serve/
```

**Verify**:
```bash
ls api/modules/web_serve/ 2>&1
# Expect: "No such file or directory"
```

---

### Step 5: Remove `web_serve` from `SAAS_OPTIONAL` in `test_structural.py`

**Action**: In `api/tests/test_structural.py`, locate the `packages_areInExpectedHierarchy` function. Remove the `"web_serve"` line from the `SAAS_OPTIONAL` set (currently line 197). The set should retain `"auth"`, `"billing"`, `"usage"`, and `"observability"`.

**File**: `api/tests/test_structural.py` (CODEBASE CONTEXT — `api/tests/`)

**Pattern** — before → after:
```python
# Before
SAAS_OPTIONAL = {
    "auth",           # planned: Neon auth wrapper
    "billing",        # planned: Stripe / RevenueCat adapter
    "usage",          # planned: per-user quota + rate-limit service
    "observability",  # planned: structured logging + health aggregation
    "web_serve",      # SaaS Operations & Infra Task 4: Angular SPA catch-all blueprint
}

# After
SAAS_OPTIONAL = {
    "auth",           # planned: Neon auth wrapper
    "billing",        # planned: Stripe / RevenueCat adapter
    "usage",          # planned: per-user quota + rate-limit service
    "observability",  # planned: structured logging + health aggregation
}
```

**Verify**:
```bash
grep "web_serve" api/tests/test_structural.py
# Expect: (no output)
```

---

### Step 6: Conditional — Clean Up Stale `test_retire_express.py` Assertions

**Action**: First, check whether these two functions are failing:

```bash
cd api && python -m pytest tests/test_retire_express.py::proxyConfJson_doesNotExist \
  tests/test_retire_express.py::angularJson_hasNoProxyConfigReference -v 2>&1 | grep -E "PASSED|FAILED|ERROR"
```

- **If both PASS**: skip this step entirely; nothing to do.
- **If either FAILS**: the compose split (Tasks 1–3) introduced `proxy.conf.json` and/or updated `angular.json`'s `proxyConfig`, making these assertions from the Express-retirement era incorrect. Delete both functions from `api/tests/test_retire_express.py`.

**File**: `api/tests/test_retire_express.py` (CODEBASE CONTEXT — `api/tests/`) — **conditional edit only**

**Pattern** — delete both functions when failing:
```python
# DELETE this entire function (lines ~50-58):
def proxyConfJson_doesNotExist():
    """..."""
    proxy_path = REPO_ROOT / "proxy.conf.json"
    assert not proxy_path.exists(), (...)

# DELETE this entire function (lines ~62-79):
def angularJson_hasNoProxyConfigReference():
    """..."""
    if not (WEB_ROOT / "angular.json").exists():
        pytest.skip(...)
    ...
    assert "proxyConfig" not in serve_opts, (...)
```

**Verify**:
```bash
cd api && python -m pytest tests/test_retire_express.py -v 2>&1 | grep -E "FAILED|ERROR"
# Expect: (no output — all remaining tests pass)
```

---

## 5. Tests

Add both functions to `api/tests/test_structural.py`, after the existing `packages_areInExpectedHierarchy` function. Follow the repo's `camelCase_underscore` naming pattern (collected by `python_functions = ["*_*"]`).

```python
def webServeModule_isDeleted():
    """modules/web_serve/ must not exist after nginx owns static serving.

    The directory being present would cause packages_areInExpectedHierarchy
    to reject the module (it was removed from SAAS_OPTIONAL in the same commit)
    and would leave dead code in the Flask image with no runtime consumer.
    """
    web_serve_dir = _REPO_ROOT / "modules" / "web_serve"
    assert not web_serve_dir.exists(), (
        "modules/web_serve/ still exists. "
        "Delete the directory: rm -rf api/modules/web_serve/. "
        "nginx owns static serving; this blueprint has no consumer."
    )


def createApp_doesNotReferenceWebServeBp():
    """create_app.py must not import or register web_serve_bp after module removal.

    Any lingering reference means Flask will ImportError on startup because
    the source files no longer exist.
    """
    create_app_text = (_REPO_ROOT / "create_app.py").read_text()
    assert "web_serve" not in create_app_text, (
        "create_app.py still references web_serve. "
        "Remove the import (line ~13) and the register_blueprint call (lines ~117-119). "
        "The module directory has been deleted; any reference will crash Flask startup."
    )
```

> `_REPO_ROOT` is already defined at the top of `test_structural.py`; no new imports needed.

**Run the new tests in isolation before committing:**
```bash
cd api && python -m pytest tests/test_structural.py::webServeModule_isDeleted \
  tests/test_structural.py::createApp_doesNotReferenceWebServeBp -v
# Expect: 2 passed
```

---

## 6. Commit Plan

**Executor instruction**: commit after **each** step completes — not at the end. Batch commits are a failure.

1. **`feat(web): use relative /api base URL in environment.ts`** — after Steps 1–2 — files: `web/src/environments/environment.ts`, (optionally) `web/src/environments/environment.prod.ts` — removes hardcoded localhost:3101; relative path works in dev (proxy.conf.json) and prod (nginx)

2. **`refactor(api): remove web_serve_bp import and registration`** — after Step 3 — files: `api/create_app.py` — deletes import and register_blueprint call; Flask no longer serves Angular SPA

3. **`chore(api): delete modules/web_serve/ directory`** — after Step 4 — files: `api/modules/web_serve/__init__.py`, `api/modules/web_serve/routes.py` — nginx is the sole static-file owner; module has no runtime consumer

4. **`test(api): remove web_serve from SAAS_OPTIONAL; add deletion invariants`** — after Steps 5–6 and after new tests pass — files: `api/tests/test_structural.py`, (conditionally) `api/tests/test_retire_express.py` — structural guard prevents re-adding the module without an explicit PR edit

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd api && make test
```

**Expected delta**: baseline_N → baseline_N + 2 passing (the two new structural tests), zero pre-existing tests broken.

If Step 6 deleted `proxyConfJson_doesNotExist` and `angularJson_hasNoProxyConfigReference` from `test_retire_express.py`, the net delta is `baseline_N + 2 - 2 = baseline_N` (same count, different composition).

Also verify the Flask app starts cleanly with no import errors:
```bash
cd api && CHAIN_PROVIDER=mock python -c "from create_app import create_app; app = create_app(); print('Flask startup OK')"
# Expect: Flask startup OK
```

And verify the Angular dev server correctly routes through `proxy.conf.json`:
```bash
# With both servers running (make dev in api/, ng serve in web/):
curl -s http://localhost:4201/api/health | grep -q '"ok"' && echo "Dev proxy OK"
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` undoes exactly one logical change without touching adjacent commits.
- **`environment.ts` rollback** (commit 1): `git revert <sha>` restores `http://localhost:3101/api`; dev mode immediately works again with direct Flask access.
- **`web_serve_bp` deletion rollback** (commits 2–4): `git revert <sha>` on commit 4 (structural test) first, then commit 3 (directory), then commit 2 (create_app); or `git revert <sha-2>..<sha-4>` to revert the range. Flask resumes serving the SPA catch-all once `create_app.py` imports and registers the restored module.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-5-sha>` [REQUIRES APPROVAL] or delete the feature branch. The split compose remains deployed and functional; only the cleanup is rolled back.

---

## 9. Deviations Allowed

- **`environment.prod.ts` does not exist** → skip Step 2 entirely; log in commit 1 body: `Deviations: environment.prod.ts not present — skipped`.
- **`proxyConfJson_doesNotExist` / `angularJson_hasNoProxyConfigReference` currently PASS at pre-flight** → skip Step 6 entirely; these tests were cleaned up in a prior task. Do not remove them proactively.
- **`environment.ts` has a different property name than `apiUrl`** → adapt the value change to match the actual property; log in commit 1 body.
- **Test framework mismatch** → match the repo's `python_functions = ["*_*"]` naming convention; translate silently but note in the commit body.
- **Step 4 unlocks an obvious dead import** (e.g., `send_from_directory` in `create_app.py` is now unused) → check if removing it causes a lint failure; if so, remove it and note in commit 3 body. Do not remove it speculatively if it's still referenced by `serve_spec`.
- **Side-effect required** (git push, image publish) → STOP, mark [REQUIRES APPROVAL].

---

## 10. Out of Scope

This task is deliberately scoped to the one-line Angular URL change and the Flask module deletion. It does not address any structural improvements that would be tempting but belong in separate decisions.

- **Updating `test_retire_express.py` route-reachability tests** (`iterate_validRequest_flaskHandlesIt`, etc.) — these route tests are independent of the static-serving removal; they are not broken by this task and must not be touched here.
- **Trimming `api/Dockerfile` comments** that reference `web_serve_bp` — the Dockerfile was simplified in Task 3; any lingering comment references there are cosmetic and out of scope for Task 5.
- **Removing CORS origins from `create_app.py`** — CORS is still needed for the Angular dev server at `:4201` and `:4202`; this is not affected by the nginx split.
- **Updating `api/.env.example`** — covered by Task 1's env var audit; Task 5 does not add or remove env vars.
- **Angular unit test updates** — any `spec.ts` files that reference `environment.apiUrl` with the old value are out of scope; Angular tests are in the Angular test runner, not `make test`, and are not part of the CI gate for this task.
- **Removing `web/nginx/nginx.conf` SSE headers** or any other nginx config changes — nginx config is Task 2's output; Task 5 has no nginx concerns.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale; see "Rollback safety" decision and "Angular base URL becomes relative `/api`" decision
- [Epic](./epic.md) – Full task scope and dependency graph
- [Timeline](./timeline.md) – Update task 5 status to `done` after verification passes