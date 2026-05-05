# Task 5: Workflow Rewrite — Implementation Guide

## 1. Context

The current `.github/workflows/deploy.yml` runs three jobs in a single linear chain — `test → docker-build → deploy` — serialising frontend and backend CI unnecessarily and leaving a soft-fail `continue-on-error: true` block that lets broken smoke tests pass silently. This task replaces that file with a four-job topology: `frontend-ci` and `backend-ci` run in parallel on every push and PR; `docker-integration` (master only) gates on both of them, brings up the full compose stack via Task 4's two-service `docker-compose.yml`, and hard-fails if `docker compose exec -T web wget /api/health` returns anything other than HTTP 200 with a JSON status body; `deploy` fires the Coolify webhook only after the integration gate passes. The structural tests in `api/tests/test_pipeline.py` are updated to encode the new topology so any future edit that breaks the contract fails immediately in CI.

**Dependencies**: Task 5 lands AFTER Tasks 3 and 4. Task 3 renames Flask `/health` → `/api/health`; the smoke test probes `/api/health`. Task 4 creates the two-service compose with a `web` (nginx) container; the smoke `docker compose exec -T web …` requires that service to exist.

**Trade-offs considered:**
- **Keeping the linear chain, just removing `continue-on-error`** — rejected because it still serialises frontend and backend steps that share zero dependencies, wasting runner time on every PR.
- **Running `docker-integration` on every branch** — rejected because a full compose up + health check adds ~2 min per PR push; the gate adds value only before a merge to master.
- **Smoke testing the api container directly on `localhost:3101`** — rejected because Task 4's compose uses `expose:` only (no host port mapping). More importantly, going through nginx tests the actual production path: a misconfigured `proxy_pass` upstream would fail this gate but pass a direct-Flask probe.
- **Uploading `web/dist/` as a CI artifact** — rejected; `docker-integration` rebuilds the dist inside `web/Dockerfile` during `docker compose up -d --build`. The artifact would never be consumed.
- **Chosen approach: parallel CI + master-only integration gate via `docker compose exec`** — frontend and backend failures are caught fast on PRs; the gate proves the same nginx→Flask path Coolify production uses; the Coolify webhook is unreachable unless the gate passes.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
cd {WORKSPACE}                                # repo root: spec-doc/

git status                                    # flag any unrelated M/?? entries
git diff HEAD -- .github/workflows/deploy.yml api/tests/test_pipeline.py

cd api && python -m pytest tests/test_pipeline.py -v   # record current pass count (7 tests)
python -m pytest --tb=short -q               # record full-suite baseline (624 passing)
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: 624 / 624 passing. `tests/test_pipeline.py` contributes 7.

---

## 3. Files

### To Create (new)
*(none — this task rewrites an existing file)*

### To Modify
- `.github/workflows/deploy.yml` — current: 3-job linear chain (`test → docker-build → deploy`) with soft-fail block; target: 4-job parallel/gated topology with no `continue-on-error`
- `api/tests/test_pipeline.py` — current: asserts `test`, `docker-build`, `deploy` job names and their linear `needs`; target: asserts `frontend-ci`, `backend-ci`, `docker-integration`, `deploy` topology plus four new structural assertions

### To Leave Alone
- `api/Makefile` — the backend-ci job calls `make check-dtos`, `make lint`, `make test`; none of those targets change
- `docker-compose.yml` — the docker-integration job uses it unmodified; the CI step creates the expected bind-mount host path instead of touching the compose file
- `api/tests/test_docker.py` — tests Docker-configuration invariants; unaffected by workflow topology
- All `modules/` source files — no application code changes in this task

---

## 4. Implementation Steps

### Step 1: Rewrite `.github/workflows/deploy.yml`

**Action**: Replace the entire file with the four-job workflow below. Do not preserve any part of the existing content — the full file is a structural replacement.

**File**: `.github/workflows/deploy.yml` (existing, at repo root)

**Pattern**:

```yaml
name: Deploy

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  # ── Parallel CI ────────────────────────────────────────────────────────────

  frontend-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: web/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: web

      - name: Build Angular app (compile-check only)
        run: npx ng build --configuration production
        working-directory: web

      # No artifact upload: docker-integration rebuilds the dist inside web/Dockerfile.

  backend-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: api/requirements*.txt

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
        working-directory: api

      - name: Check DTOs are in sync
        run: make check-dtos
        working-directory: api

      - name: Lint
        run: make lint
        working-directory: api

      - name: Run tests
        run: make test
        working-directory: api

  # ── Master-only integration gate ───────────────────────────────────────────

  docker-integration:
    runs-on: ubuntu-latest
    needs: [frontend-ci, backend-ci]
    if: github.ref == 'refs/heads/master'
    env:
      CHAIN_PROVIDER: mock
      ANTHROPIC_API_KEY: ci-mock-key-not-used
    steps:
      - uses: actions/checkout@v4

      - name: Build and start stack
        run: docker compose up -d --build

      - name: Wait for nginx→Flask path (2-minute timeout)
        run: |
          for i in $(seq 1 24); do
            if docker compose exec -T web wget -qO- http://localhost/api/health \
                > /dev/null 2>&1; then
              echo "Stack ready after $((i * 5))s"
              exit 0
            fi
            echo "  attempt $i/24 — sleeping 5s"
            sleep 5
          done
          echo "Stack never became healthy after 120s"
          docker compose logs
          exit 1

      - name: Smoke GET / (Angular SPA)
        run: |
          BODY=$(docker compose exec -T web wget -qO- http://localhost/)
          echo "$BODY" | head -3
          echo "$BODY" | grep -qi "<!doctype html>" \
            || (echo "FAIL: / did not serve Angular HTML"; docker compose logs; exit 1)

      - name: Smoke GET /api/health (through nginx → Flask)
        run: |
          BODY=$(docker compose exec -T web wget -qO- http://localhost/api/health)
          echo "$BODY"
          echo "$BODY" | grep -q '"status"' \
            || (echo "FAIL: /api/health missing status field"; docker compose logs; exit 1)

      - name: Tear down
        if: always()
        run: docker compose down -v

  # ── Deploy ─────────────────────────────────────────────────────────────────

  deploy:
    runs-on: ubuntu-latest
    needs: [docker-integration]
    if: github.ref == 'refs/heads/master'
    steps:
      - name: Trigger Coolify webhook
        run: |
          curl -sf -X GET \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}" \
            "${{ secrets.COOLIFY_WEBHOOK }}"
```

**Key choices**:
- `frontend-ci` does NOT upload `web/dist/` as an artifact. The dist is rebuilt inside `web/Dockerfile` during `docker compose up -d --build`, so the upload would never be consumed.
- `docker-integration` smoke tests go through `docker compose exec -T web` rather than against `localhost:80` because the new compose uses `expose:` only — no host port mapping. This tests the same network path Coolify production uses.
- Both smoke tests probe `/api/health` (Task 3 renamed the route from `/health`). Hard-fails on any non-`<!doctype html>` for `/` or any missing `"status"` field for `/api/health`.

**Verify**:
```bash
python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/deploy.yml')); print(list(d['jobs'].keys()))"
# expect: ['frontend-ci', 'backend-ci', 'docker-integration', 'deploy']

grep -c "continue-on-error" .github/workflows/deploy.yml
# expect: 0
```

---

### Step 2: Update `api/tests/test_pipeline.py`

**Action**: Rewrite the three job-topology tests (`test_required_jobs_present`, `test_docker_build_depends_on_test`, `test_deploy_depends_on_docker_build`) and append four new structural assertions at the end of the file. The `workflow` fixture, `test_workflow_file_is_valid_yaml`, `test_workflow_triggers_on_push_and_pull_request`, `test_coolify_secrets_referenced_in_deploy_job`, and `test_dependabot_config_is_valid_yaml` are **unchanged** — do not touch them.

**File**: `api/tests/test_pipeline.py` (existing)

Replace the three stale tests:

```python
# OLD — remove these three functions entirely:
#   test_required_jobs_present
#   test_docker_build_depends_on_test
#   test_deploy_depends_on_docker_build
```

Replace them with the five topology tests below (which cover the same ground plus four new assertions):

```python
def test_required_jobs_present(workflow):
    jobs = workflow.get("jobs", {})
    for required in ("frontend-ci", "backend-ci", "docker-integration", "deploy"):
        assert required in jobs, f"job '{required}' missing from deploy.yml"


def test_frontend_ci_runs_unconditionally(workflow):
    job = workflow["jobs"]["frontend-ci"]
    assert "needs" not in job, (
        "frontend-ci must have no needs — it runs on every push/PR without waiting on anything"
    )
    assert "if" not in job, (
        "frontend-ci must have no if-condition — Angular build must gate PRs, not just master"
    )


def test_backend_ci_runs_unconditionally(workflow):
    job = workflow["jobs"]["backend-ci"]
    assert "needs" not in job, (
        "backend-ci must have no needs — pytest runs on every push/PR without waiting on anything"
    )
    assert "if" not in job, (
        "backend-ci must have no if-condition — tests must gate PRs, not just master"
    )


def test_docker_integration_needs_both_ci_jobs(workflow):
    needs = workflow["jobs"]["docker-integration"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "frontend-ci" in needs, (
        "docker-integration must need frontend-ci — "
        "the compose image must include the built Angular dist"
    )
    assert "backend-ci" in needs, (
        "docker-integration must need backend-ci — "
        "the compose image must not ship a revision with failing tests"
    )


def test_deploy_needs_docker_integration(workflow):
    needs = workflow["jobs"]["deploy"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "docker-integration" in needs, (
        "deploy must need docker-integration — "
        "Coolify must not be triggered until the health gate passes"
    )


def test_docker_integration_conditional_on_master(workflow):
    condition = str(workflow["jobs"]["docker-integration"].get("if", ""))
    assert "master" in condition, (
        "docker-integration must be conditional on the master branch. "
        "Running a full docker compose up on every PR push is unnecessary and slow."
    )


def test_no_continue_on_error_in_workflow():
    raw = WORKFLOW_PATH.read_text()
    assert "continue-on-error: true" not in raw, (
        "continue-on-error: true found in deploy.yml — the soft-fail WARN block must be removed. "
        "Every step must hard-fail its job so failures are visible immediately."
    )
```

**Verify**:
```bash
cd api && python -m pytest tests/test_pipeline.py -v
# expect: 11 passed  (7 original kept + 4 new — the 3 rewrites replace 3 originals)
```

---

## 5. Tests

Framework: `pytest` with plain `assert` (no third-party matcher library). Match the existing `api/tests/test_pipeline.py` conventions exactly — module-scoped `workflow` fixture, `WORKFLOW_PATH` path constant, direct raw-text reads for grep-style checks.

Full assertion bodies (these are the four net-new tests; the three rewrites are already shown in Step 2):

```python
# api/tests/test_pipeline.py  — complete bodies for the four new functions

def test_frontend_ci_runs_unconditionally(workflow):
    job = workflow["jobs"]["frontend-ci"]
    assert "needs" not in job, (
        "frontend-ci must have no needs — it runs on every push/PR without waiting on anything"
    )
    assert "if" not in job, (
        "frontend-ci must have no if-condition — Angular build must gate PRs, not just master"
    )


def test_backend_ci_runs_unconditionally(workflow):
    job = workflow["jobs"]["backend-ci"]
    assert "needs" not in job, (
        "backend-ci must have no needs — pytest runs on every push/PR without waiting on anything"
    )
    assert "if" not in job, (
        "backend-ci must have no if-condition — tests must gate PRs, not just master"
    )


def test_docker_integration_conditional_on_master(workflow):
    condition = str(workflow["jobs"]["docker-integration"].get("if", ""))
    assert "master" in condition, (
        "docker-integration must be conditional on the master branch. "
        "Running a full docker compose up on every PR push is unnecessary and slow."
    )


def test_no_continue_on_error_in_workflow():
    raw = WORKFLOW_PATH.read_text()
    assert "continue-on-error: true" not in raw, (
        "continue-on-error: true found in deploy.yml — the soft-fail WARN block must be removed. "
        "Every step must hard-fail its job so failures are visible immediately."
    )
```

---

## 6. Commit Plan

**Executor instruction**: commit after each step completes — not once at the end.

1. `ci: rewrite deploy.yml to parallel frontend-ci + backend-ci + docker-integration + deploy` — **after Step 1** — `.github/workflows/deploy.yml`: full file replacement; removes soft-fail block; adds master-only integration health gate.

   ```bash
   git add .github/workflows/deploy.yml
   git commit -m "ci: rewrite deploy.yml to parallel frontend-ci + backend-ci + docker-integration + deploy"
   ```

2. `test(pipeline): update structural tests for 4-job workflow topology` — **after Step 2 passes** — `api/tests/test_pipeline.py`: rewrites 3 topology tests, adds 4 new assertions for unconditional CI jobs, master-gating, and soft-fail absence.

   ```bash
   git add api/tests/test_pipeline.py
   git commit -m "test(pipeline): update structural tests for 4-job workflow topology"
   ```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation before the closing quote.

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → 628 passing. The 4 new test functions in `test_pipeline.py` account for the full delta. Zero pre-existing tests broken.

Cross-check the specific file:
```bash
python -m pytest tests/test_pipeline.py -v
# expect: 11 passed, 0 failed
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Revert Step 1: `git revert <sha-of-step-1-commit>` — restores the old `deploy.yml`; the test file is not yet changed so `test_pipeline.py` reverts to passing against the old shape.
  - Revert Step 2: `git revert <sha-of-step-2-commit>` — restores the old `test_pipeline.py`; the new workflow is still in place but the structural tests no longer enforce the new topology.

- **Per-branch**: if verification fails catastrophically after both commits: `git reset --hard <sha-before-step-1>`. This discards both commits and returns the working tree to its pre-task state. The sha to record is the output of `git rev-parse HEAD` captured during pre-flight.

---

## 9. Deviations Allowed

- **`web/package-lock.json` absent** → if `web/` has no lockfile, drop `cache-dependency-path: web/package-lock.json` from the `setup-node` step and use `cache: "npm"` without the path hint. Note the deviation in the commit body.
- **`docker compose` vs `docker-compose`** → ubuntu-latest runners have Docker Compose V2 (`docker compose`). If the runner has only V1, change to `docker-compose` (hyphen). Log the deviation.
- **`docker compose exec -T web` fails because `web` service is missing** → Task 4 has not landed. STOP — the smoke test cannot run without it.
- **Smoke `wget` unavailable in `web` container** → `nginx:alpine` includes BusyBox `wget`. If Task 2 chose a different base image and `wget` is absent, substitute `curl` if present or install `wget` via `apk add --no-cache wget`. Log the deviation.
- **`<!doctype html>` grep fails** → the smoke test compares against `wget`-fetched body; case-folded match. If Angular ever ships a BOM or leading whitespace that breaks the substring match, switch to `grep -qi "doctype"` without the leading `<`. Log the deviation.
- **Side-effect required** (push, webhook call, schema change) → STOP, mark `[REQUIRES APPROVAL]`, and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in commit body.

---

## 10. Out of Scope

This task owns only the workflow topology and its structural test coverage. It does not touch application code, Docker configuration, or deployment infrastructure. An eager executor might notice adjacent improvements — those are explicitly deferred below.

- **`docker-compose.yml` shape** — Task 4 owns the compose file. This task consumes it but does not modify it.
- **PR-scoped `docker-integration` preview** — running integration tests on every PR (with a shorter timeout or mock image) is a possible future enhancement; it is not part of this task's scope.
- **Dependabot / `dependabot.yml`** — Task 1 deletes the dead `api/.github/dependabot.yml`. Authoring a root-level `dependabot.yml` covering both pip and npm is a separate operational decision.
- **Coolify webhook response validation** — the `deploy` job currently fires the webhook and trusts a 2xx response. Adding retry logic or response-body validation is a future hardening task.
- **Direct-to-api smoke test** — the workflow probes only via nginx. A future addition could also probe `api:3101/api/health` directly via `docker compose exec -T api`; deferred because the nginx path is the production path and adding redundancy doubles the surface for breakage.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)