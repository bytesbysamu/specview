# Task 1: Add `/health` Route and Audit Env Vars

## 1. Context

The Docker healthcheck in the split-compose (Task 3) targets `http://localhost:3101/health` on the backend container. This route already exists at `api/create_app.py` lines 90–92 and returns `{"status": "ok"}` with HTTP 200, matching the `HealthResponse` schema in `openapi.yaml`. The primary work of this task is therefore the env var audit: grepping each of the six questioned vars (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `NEON_AUTH_JWKS_URI`, `DATABASE_URL`, `SENTRY_DSN`) against `api/` Python source, then updating `api/.env.example` to document every var that is genuinely referenced. The audit also surfaces a gap in the opposite direction — `APP_ENV`, `SKIP_AUTH`, `APP_RELEASE`, and the billing vars are all wired into code but absent from `.env.example`. The deliverable is a `.env.example` that matches reality: nothing speculative, nothing silently missing.

**Trade-offs considered**:
- **Full healthcheck (chain ping + DB ping) vs minimal 200** — minimal wins; Docker healthcheck needs deterministic liveness, not business-logic availability. Coupling health to upstream services causes flapping during cold starts. The richer observability endpoint already exists at `health_bp` (`modules/observability/health.py`).
- **Create a dedicated health blueprint vs keep the route in `create_app.py`** — `create_app.py` wins; ELA Pattern #5 (Not-Yet-Built) forbids a new module for a three-line route with no business logic. `health_bp` at line 82 is the observability variant; the Docker route is distinct and minimal.
- **Add missing vars to `.env.example` vs create a separate `docker.env.example`** — single file wins; spec-doc is a single-developer tool, splitting env documentation across files adds maintenance surface with no benefit.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From the repo root (parent of api/)
git status                              # flag any unrelated M/?? entries
git diff HEAD -- api/create_app.py api/.env.example api/tests/test_health.py
cd api && python -m pytest tests/test_health.py -v 2>&1 | tail -20
cd api && python -m pytest --tb=no -q 2>&1 | tail -5  # record baseline pass count
```

**Additionally, read these files before touching anything:**

```bash
cat -n api/create_app.py | sed -n '88,95p'        # confirm /health route shape
cat -n api/tests/test_env_example.py               # read full file — structure matters for Step 4
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**Baseline recorded**: 624 / 624 passing (1 skipped — web-root check).

---

## 3. Files

### To Create (new)
_(none — all required files already exist)_

### To Modify (cite CODEBASE CONTEXT)
- `api/create_app.py` — **read only**; confirm lines 90–92 are correct. If the route is absent or returns non-JSON, apply the fix in Step 1. No other changes to this file.
- `api/.env.example` — add five new documentation sections: Auth bypass, Environment/Observability, Database, Billing. Currently 54 lines; adds ~35 lines of documented vars.
- `api/tests/test_env_example.py` — extend the expected-vars list to cover the newly-documented vars; confirm no existing assertion is broken.

### To Leave Alone
- `api/openapi.yaml` — `GET /health` path and `HealthResponse` schema are already declared; `make check-dtos` will fail if this file is edited without regenerating DTOs.
- `api/dtos/models.py` — generated file; never hand-edit. `HealthResponse` shape is `{ status: Status.ok }` which maps correctly to `{"status": "ok"}`.
- `api/tests/test_health.py` — 11 existing tests fully cover the Docker healthcheck scenario (200, JSON body, content-type, CORS). No additions required here.
- `api/modules/billing/service.py` — source of truth for which Stripe vars are read; do not touch.
- `api/modules/observability/sentry.py` — source of truth for which Sentry/APP vars are read; do not touch.
- `api/modules/auth/decorators.py` — source of truth for `SKIP_AUTH`; do not touch.
- `api/modules/data/db/engine.py` — source of truth for `DATABASE_URL`; do not touch.

---

## 4. Implementation Steps

### Step 1: Confirm the `/health` Route

**Action**: Read `api/create_app.py` lines 88–95. Confirm the route is present and returns `jsonify({'status': 'ok'})` with implicit HTTP 200. If and only if the route is missing or returns a non-JSON body, apply the fix below.

**File**: `api/create_app.py` (existing — CODEBASE CONTEXT: app factory, line 90)

**Pattern** (current correct state — match exactly; do NOT apply if already present):
```python
@app.get('/health')
def health():
    return jsonify({'status': 'ok'})
```

**Verify**:
```bash
cd api && python -m pytest tests/test_health.py -v
```
Expect: all 11 tests pass. If any fail, the route body is wrong — fix before proceeding.

> **Commit**: `chore(health): confirm /health route — no source change required`
> If the route was absent and you applied the fix, change the message to `feat(health): add /health route for Docker healthcheck`.

---

### Step 2: Run the Env Var Audit

**Action**: Execute the grep commands below and record each result in a local scratch note (or directly in the commit body as `Deviations:` entries if any result surprises you). Do not edit any files during this step.

**File**: audit only — no file changes yet

**Audit commands** (run each from `api/`):

```bash
# ── Questioned vars (humanize-me crossover risk) ──────────────────────────
grep -r "STRIPE_SECRET_KEY"      --include="*.py" modules/ create_app.py config.py
grep -r "STRIPE_WEBHOOK_SECRET"  --include="*.py" modules/ create_app.py config.py
grep -r "STRIPE_PRO_PRICE_ID"    --include="*.py" modules/ create_app.py config.py
grep -r "NEON_AUTH_JWKS_URI"     --include="*.py" modules/ create_app.py config.py
grep -r "DATABASE_URL"           --include="*.py" modules/ create_app.py config.py
grep -r "SENTRY_DSN"             --include="*.py" modules/ create_app.py config.py

# ── Vars used in code but absent from .env.example ───────────────────────
grep -r "APP_ENV"                --include="*.py" modules/ create_app.py
grep -r "APP_RELEASE"            --include="*.py" modules/ create_app.py
grep -r "SKIP_AUTH"              --include="*.py" modules/ create_app.py
```

**Expected findings** (verified against codebase before writing this guide):

| Var | Used in code | In `.env.example` | Action |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | ✅ `modules/billing/service.py:43` | ❌ | Add |
| `STRIPE_WEBHOOK_SECRET` | ✅ `modules/billing/service.py:47` | ❌ | Add |
| `STRIPE_PRO_PRICE_ID` | ✅ billing module | ❌ | Add |
| `NEON_AUTH_JWKS_URI` | ❌ not found | ❌ | Confirmed absent — no action |
| `DATABASE_URL` | ✅ `modules/data/db/engine.py:14` | ❌ | Add |
| `SENTRY_DSN` | ✅ `modules/observability/sentry.py:29` | ❌ | Add |
| `APP_ENV` | ✅ `create_app.py:43`, `sentry.py:39` | ❌ | Add |
| `APP_RELEASE` | ✅ `modules/observability/sentry.py` | ❌ | Add |
| `SKIP_AUTH` | ✅ `modules/auth/decorators.py:25` | ❌ | Add |

**If any expected finding differs** from the table above (e.g., `NEON_AUTH_JWKS_URI` appears), STOP and note it as a deviation in the next commit body. Proceed only after recording it.

**Verify**: `grep -c "" <result>` — confirm each grep either returns ≥1 matches (used) or 0 (absent). No file edits yet.

> **Commit**: No commit for this step — it's audit-only. Proceed to Step 3.

---

### Step 3: Update `.env.example` with Audit Findings

**Action**: Append five new sections to `api/.env.example` immediately after the existing `CONTEXT_PROVIDER` block (line 47) and before the `── Deployment secrets ──` comment block (lines 49–54). Move the deployment-secrets block to the very end.

**File**: `api/.env.example` (existing — CODEBASE CONTEXT: 54 lines; add ~38 lines)

**Pattern** (insert between line 47 and line 49):
```bash
# ── Auth ───────────────────────────────────────────────────────────────────
# Bypass JWT validation in local dev. Set to "1" or "true" to skip auth checks.
# NEVER set in production — the startup gate rejects APP_ENV=production with this set.
SKIP_AUTH=

# ── Environment ────────────────────────────────────────────────────────────
# Deployment environment tag. Defaults to "production" when unset.
# Set to "local" or "staging" for non-prod deployments.
APP_ENV=local

# ── Observability ──────────────────────────────────────────────────────────
# Sentry error-reporting DSN. Leave blank locally; the SDK silently no-ops when unset.
# Provision in GitHub → Settings → Secrets for production.
SENTRY_DSN=

# Sentry release tag for source-map attribution. Defaults to "dev" when unset.
# Set to the Git SHA in CI (APP_RELEASE=$(git rev-parse --short HEAD)).
APP_RELEASE=

# ── Database ───────────────────────────────────────────────────────────────
# Override the default SQLite path. When blank, uses {SPEC_DOC_DIR}/spec_doc.db.
# In the split-compose (Task 3), set this to sqlite:////data/spec-doc/spec_doc.db
# (four slashes: three for the absolute path prefix on Linux).
DATABASE_URL=

# ── Billing (Stripe) ───────────────────────────────────────────────────────
# Stripe secret key. Use sk_test_... locally; sk_live_... in production.
# Required only when the billing module routes are exercised.
STRIPE_SECRET_KEY=

# Stripe webhook signing secret (whsec_...).
# Required for /api/billing/webhook signature validation.
STRIPE_WEBHOOK_SECRET=

# Stripe Price ID for the Pro plan (price_...).
# Obtain from Stripe Dashboard → Products → Pro plan → Price ID.
STRIPE_PRO_PRICE_ID=
```

**Verify**:
```bash
grep -c "SKIP_AUTH\|SENTRY_DSN\|APP_ENV\|APP_RELEASE\|DATABASE_URL\|STRIPE_SECRET_KEY\|STRIPE_WEBHOOK_SECRET\|STRIPE_PRO_PRICE_ID" api/.env.example
```
Expect: `8` (one match per var name).

> **Commit here** (before Step 4):
> ```
> chore(env): document billing, observability, auth, and db vars in .env.example
>
> Env var audit findings:
> - STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRO_PRICE_ID: used in
>   modules/billing/service.py — legitimately wired, not speculative copy.
> - NEON_AUTH_JWKS_URI: not found anywhere in api/ Python source — confirmed absent.
> - DATABASE_URL: used in modules/data/db/engine.py — needed for compose data volume.
> - SENTRY_DSN, APP_ENV, APP_RELEASE: used in modules/observability/sentry.py.
> - SKIP_AUTH: used in modules/auth/decorators.py dev bypass.
> ```

---

### Step 4: Extend `test_env_example.py`

**Action**: Read the full `api/tests/test_env_example.py` file first (pre-flight already did this). Locate the list or parametrize block that enumerates expected var names. Add the eight new var names to that list. Do not change the test logic itself — only extend the data.

**File**: `api/tests/test_env_example.py` (existing — CODEBASE CONTEXT: `tests/` directory)

**Pattern** (extend the existing vars list — adapt to match the file's actual structure):
```python
# If the file uses a list literal, extend it:
EXPECTED_VARS = [
    # … existing vars …
    "SKIP_AUTH",
    "APP_ENV",
    "APP_RELEASE",
    "SENTRY_DSN",
    "DATABASE_URL",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRO_PRICE_ID",
]
```

**Verify**:
```bash
cd api && python -m pytest tests/test_env_example.py -v
```
All parametrized cases (or individual test methods) for the new vars must pass. If any fail, the var name in the list does not match what was inserted in `.env.example` — fix the spelling.

> **Commit here**:
> ```
> test(env): assert billing, observability, auth, and db vars in .env.example
> ```

---

## 5. Tests

Framework: pytest, bare functions with fixture injection (no class grouping in `test_health.py`; follows the same convention). New tests go in `api/tests/test_env_example.py`, appended to the existing expected-vars list. All test functions already exist in `test_health.py` — no new health tests needed.

The following assertions are for the `test_env_example.py` extension. Match whatever structure already exists in that file; translate if it uses `@pytest.mark.parametrize` or individual function names.

```python
# Add to the EXPECTED_VARS list (or equivalent parametrize values) in test_env_example.py.
# Each entry causes one test assertion of the form:
#   assert VAR_NAME in env_example_content, f"{VAR_NAME} is used in code but missing from .env.example"

"SKIP_AUTH",          # modules/auth/decorators.py:25
"APP_ENV",            # create_app.py:43, modules/observability/sentry.py:39
"APP_RELEASE",        # modules/observability/sentry.py (APP_RELEASE default)
"SENTRY_DSN",         # modules/observability/sentry.py:29
"DATABASE_URL",       # modules/data/db/engine.py:14
"STRIPE_SECRET_KEY",  # modules/billing/service.py:43
"STRIPE_WEBHOOK_SECRET",  # modules/billing/service.py:47
"STRIPE_PRO_PRICE_ID",    # modules/billing/service.py (price lookup)
```

If `test_env_example.py` reads the actual `.env.example` file and asserts the string appears, each entry above is sufficient. If the file has a different shape (assertion function, fixture-loaded file path), adapt without changing the assertion logic — only the data list grows.

---

## 6. Commit Plan

**Executor instruction**: commit after each completed step — not at the end. The plan below gives exact commit boundaries.

1. **`chore(health): confirm /health route — no source change required`** — after Step 1 — `api/create_app.py`: no diff expected; create an empty commit only if the route was already correct, OR use `feat(health): add /health route for Docker healthcheck` if you applied the fix.

2. **`chore(env): document billing, observability, auth, and db vars in .env.example`** — after Step 3 — `api/.env.example`: adds SKIP\_AUTH, APP\_ENV, APP\_RELEASE, SENTRY\_DSN, DATABASE\_URL, STRIPE\_SECRET\_KEY, STRIPE\_WEBHOOK\_SECRET, STRIPE\_PRO\_PRICE\_ID sections. Include the audit findings summary in the commit body as shown in Step 3.

3. **`test(env): assert billing, observability, auth, and db vars in .env.example`** — after Step 4 tests pass — `api/tests/test_env_example.py`: extends expected-vars list by 8 entries.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

> **Note on commit 1**: if `create_app.py` lines 90–92 are exactly as expected and no source change occurs, you may skip the empty commit and note "Step 1: no change" in commit 2's body instead. Do not accumulate both steps into a single commit if changes were made.

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → **632** passing (8 new parametrized/individual assertions in `test_env_example.py`, one per newly-documented var). Zero pre-existing tests broken. The 1 skipped test (web-root) remains skipped.

Spot-check the health route directly:
```bash
cd api && FLASK_APP=create_app CHAIN_PROVIDER=mock flask run --port 3101 &
sleep 2 && curl -s http://localhost:3101/health | python -m json.tool
# expect: { "status": "ok" }
kill %1
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # creates a new revert commit; safe on feature branch
  ```
- **Per-branch**: if verification fails catastrophically after all steps:
  ```bash
  git reset --hard <sha-before-task-start>   # [REQUIRES APPROVAL] destructive
  ```
  Or delete the feature branch and re-branch from master.
- **Health route rollback**: if commit 1 applied a fix and the fix breaks something, `git revert <sha>` restores the prior state. The `health_bp` observability endpoint at `/api/health` is unaffected — it is registered separately at `create_app.py` line 82.

---

## 9. Deviations Allowed

- **`test_env_example.py` uses a different structure** (e.g., `@pytest.mark.parametrize`, fixture-loaded file, per-function assertions) — adapt the data addition to match the actual structure. Translate silently but note in the Step 4 commit body: `Deviations: test_env_example.py uses [actual pattern]; extended accordingly`.
- **`STRIPE_PRO_PRICE_ID` name differs in source** (e.g., `STRIPE_PRO_PLAN_PRICE_ID` or `STRIPE_PRICE_ID_PRO`) — use the exact string from the grep output, not the name assumed in this guide. Update both `.env.example` and `test_env_example.py` to match.
- **`APP_RELEASE` not found in grep** — omit it from both `.env.example` and the test list; log as `Deviations: APP_RELEASE absent from sentry.py grep — omitted`.
- **`/health` route differs from lines 90–92** (e.g., it's inside `health_bp` and returns a different shape) — do not move or refactor it; only fix the response body if it does not return `{"status": "ok"}` with 200. Flag any structural difference as a deviation before touching it.
- **Step unlocks a simplification** — take it, log it in the commit body.
- **Side-effect required** (push, schema migration, DTO regeneration) — STOP, mark [REQUIRES APPROVAL].

---

## 10. Out of Scope

This task confirms the health route, audits env vars, and documents the findings in `.env.example`. It does not provision any infrastructure, change any runtime behavior, or touch the CI pipeline. An eager executor might be tempted to expand into adjacent work — all of the following are explicitly deferred:

- **Docker Compose authoring (`docker-compose.yml`)** — Task 3 consumes the `/health` route; it writes the healthcheck stanza. Do not write compose files here.
- **`api/Dockerfile` simplification** — Task 3 also simplifies the backend Dockerfile to a single `python:3.11-slim` stage. No Dockerfile changes belong in Task 1.
- **`web/Dockerfile` and `web/nginx/nginx.conf`** — Task 2; independently parallelisable with Task 1. No frontend container work here.
- **Deleting `web_serve_bp`** — Task 5; intentionally last. The blueprint stays registered for rollback safety.
- **Moving `/health` into `health_bp` or a new blueprint** — ELA Pattern #5 forbids a new module for one route. If a second consumer appears, revisit then.
- **Adding the Stripe/Sentry vars to GitHub Actions secrets** — operational work that follows deployment; not a code task.
- **Alembic migration for `DATABASE_URL`** — `modules/data/db/engine.py` handles the SQLite default; no migration is needed for local dev. Production database provisioning is a separate concern.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale; healthcheck and env var audit framing in "Component Design: Backend Container" and "Open Questions"
- [Epic](./epic.md) — Task scope and dependency graph
- [Timeline](./timeline.md) — Update task status to ✅ after verification passes