Now I have everything I need. Let me write the guide.

# Task 4: Align CI Pipeline

## 1. Context

The current `deploy.yml` runs four jobs sequentially — `test`, `build-frontend`, `docker-build`, `deploy` — with `test` and `build-frontend` already parallelised, then `docker-build` gating on both before `deploy`. Task 4 promotes this latent parallelism to explicit named jobs (`frontend-ci`, `backend-ci`), replaces the single-container `docker build`/`docker run` smoke test with a two-service `docker compose` integration pass that exercises the actual nginx→Flask request path, and removes the `angular-dist` artifact upload that is no longer needed once each container owns its own build stage. One secondary fix is corrected alongside: `api/tests/test_pipeline.py` currently resolves the workflow path two levels up (`api/.github/workflows/deploy.yml`, untracked) instead of three (`{WORKSPACE}/.github/workflows/deploy.yml`, git-tracked); that path bug is fixed in the same task so CI assertions run against the canonical file.

**Trade-offs considered:**
- **Run `docker-integration` on every PR** — rejected; `docker compose --build` adds ~5 minutes to every PR feedback cycle; for a personal tool the fail-fast value of `frontend-ci` + `backend-ci` on PRs is sufficient, and the full stack proof belongs on `master` before the webhook fires.
- **Keep artifact upload (`angular-dist`) as a build-cache optimisation** — rejected; once `web/Dockerfile` has its own `node:20-alpine` build stage the dist artifact is redundant and doubles the artifact management surface with no correctness benefit.
- **`docker compose exec -T frontend wget` for smoke tests, not host-port mapping** — preferred; the root `docker-compose.yml` after Task 3 uses `expose:` (no `ports:`), so direct `localhost:80` access from the runner is unavailable; exec'ing into the nginx container exercises the identical nginx→`backend:3101` proxy path that production uses, with no special CI override needed.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm git root — must be {WORKSPACE}, not api/
git rev-parse --show-toplevel

# Confirm the canonical workflow file exists and is tracked
git ls-files .github/workflows/deploy.yml   # must print the path, not blank

# Show the current job names (executor records these as the baseline)
grep "^  [a-z].*:" .github/workflows/deploy.yml | head -10

# Confirm the untracked local copy that tests currently point to
ls api/.github/workflows/deploy.yml          # exists but untracked — do NOT edit this

# Baseline test count
cd api && make test 2>&1 | tail -3           # record N passed / M skipped
cd ..

# Confirm Task 2 pre-requisite: web/Dockerfile must exist
ls web/Dockerfile                            # STOP if missing — Task 2 is not merged

# Confirm Task 3 pre-requisite: root docker-compose.yml defines a 'frontend' service
grep "frontend:" docker-compose.yml          # STOP if missing — Task 3 is not merged
```

**If working tree is dirty on target files**: `git stash` unrelated changes before starting.

**If `web/Dockerfile` is absent**: do not attempt `docker-integration` changes — the job will reference a build context that does not exist. Complete Task 2 first, then return.

**If `docker-compose.yml` has no `frontend` service**: the `docker compose exec -T frontend` smoke commands will fail. Complete Task 3 first, or note the expected failure in the `docker-integration` job comment and accept the job will fail until Task 3 merges.

**Baseline recorded**: run `cd api && make test` and record the count.

---

## 3. Files

### To Create (new)
*(none — both targets already exist)*

### To Modify
- `{WORKSPACE}/.github/workflows/deploy.yml` — current state: four sequential jobs `test`, `build-frontend`, `docker-build`, `deploy`; target: rename to `frontend-ci`/`backend-ci` (parallel, all branches), `docker-integration` (master-only, compose-based smoke), `deploy` (master-only, unchanged)
- `{WORKSPACE}/api/tests/test_pipeline.py` — current state: path uses `parent.parent` pointing at untracked `api/.github/`; job assertions check `test`, `docker-build`, `deploy`; target: path corrected to `parent.parent.parent` (git root), job assertions updated to new names, two assertions added for the parallel-gate contract

### To Leave Alone
- `{WORKSPACE}/api/.github/workflows/deploy.yml` — untracked local copy; the canonical file is at the git root; do not edit or commit this file; it is safe to leave as-is (git ignores it)
- `{WORKSPACE}/api/docker-compose.yml` — local dev compose; Task 3 owns the root compose restructure; this task does not touch it
- `{WORKSPACE}/docker-compose.yml` — Task 3 owns the two-service split; this task reads it but does not edit it
- `{WORKSPACE}/api/Makefile` — the `make lint`, `make test`, `make check-dtos` targets are used verbatim; no changes needed
- `{WORKSPACE}/api/Dockerfile` — Task 1 scope; untouched here
- `{WORKSPACE}/web/Dockerfile` — Task 2 scope; untouched here

---

## 4. Implementation Steps

### Step 1: Rewrite `.github/workflows/deploy.yml`

**Action**: Replace the full file content with the four-job parallel structure. Preserve `COOLIFY_TOKEN` and `COOLIFY_WEBHOOK` secrets verbatim. Set `docker-integration` and `deploy` to `if: github.ref == 'refs/heads/master'` only.

**File**: `{WORKSPACE}/.github/workflows/deploy.yml`

**Pattern**:
```yaml
name: CI/CD

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:

  # ── 1. Frontend compile check ────────────────────────────────────────────────
  # Fail-fast gate on Angular compile errors. The dist is NOT uploaded as an
  # artifact; web/Dockerfile stage 1 builds Angular independently so the
  # production image is always self-contained.
  frontend-ci:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: web/package-lock.json

      - name: Install Angular dependencies
        run: npm ci --prefer-offline --no-audit --progress=false

      - name: Build Angular (production)
        run: npx ng build --configuration production

  # ── 2. Backend lint / test / check-dtos ─────────────────────────────────────
  backend-ci:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: api
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: "api/requirements*.txt"

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Create spec-doc stub
        run: mkdir -p /tmp/spec-doc-stub

      - name: Lint
        run: make lint

      - name: Test
        run: make test
        env:
          SPEC_DOC_DIR: /tmp/spec-doc-stub

      - name: Check DTOs
        run: make check-dtos

  # ── 3. Two-service integration smoke ────────────────────────────────────────
  # Builds frontend (nginx) and backend (Flask) containers from source,
  # then probes the nginx→Flask path end-to-end before the deploy fires.
  # Requires: Task 2 (web/Dockerfile) and Task 3 (two-service docker-compose.yml).
  docker-integration:
    needs: [frontend-ci, backend-ci]
    if: github.ref == 'refs/heads/master'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and start services
        run: docker compose up -d --build
        env:
          CHAIN_PROVIDER: mock
          ANTHROPIC_API_KEY: ci-mock-key-not-used

      - name: Wait for nginx→Flask path (2-minute timeout)
        run: |
          for i in $(seq 1 24); do
            if docker compose exec -T frontend wget -qO- http://localhost/api/health \
                > /dev/null 2>&1; then
              echo "Services ready after $((i * 5))s"
              exit 0
            fi
            echo "  attempt $i/24 — sleeping 5s"
            sleep 5
          done
          echo "Services never became healthy after 120s"
          docker compose logs
          exit 1

      - name: Smoke test GET / (Angular SPA root)
        run: |
          BODY=$(docker compose exec -T frontend wget -qO- http://localhost/)
          echo "$BODY" | head -3
          echo "$BODY" | grep -qi "<!doctype html>" \
            || (echo "FAIL: / did not serve Angular HTML" && exit 1)

      - name: Smoke test GET /api/health
        run: |
          BODY=$(docker compose exec -T frontend wget -qO- http://localhost/api/health)
          echo "$BODY"
          echo "$BODY" | grep -q '"status"' \
            || (echo "FAIL: /api/health missing status field" && exit 1)

      - name: Tear down
        if: always()
        run: docker compose down -v

  # ── 4. Deploy (master only) ──────────────────────────────────────────────────
  deploy:
    needs: [docker-integration]
    if: github.ref == 'refs/heads/master'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via Coolify webhook
        run: |
          curl -X GET \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}" \
            --fail \
            --silent \
            --show-error \
            "${{ secrets.COOLIFY_WEBHOOK }}"
```

**Verify**: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` — no output means valid YAML. Then: `grep "frontend-ci\|backend-ci\|docker-integration\|deploy" .github/workflows/deploy.yml | head -10` — all four job names appear.

---

### Step 2: Update `api/tests/test_pipeline.py`

**Action**: Fix the WORKFLOW_PATH and DEPENDABOT_PATH to resolve via `parent.parent.parent` (three levels: `tests/` → `api/` → `{WORKSPACE}/`). Replace the three job-structure tests with assertions matching the new four-job topology.

**File**: `{WORKSPACE}/api/tests/test_pipeline.py`

**Pattern**:
```python
"""
Structural tests for .github/workflows/deploy.yml.
These fail fast if a future edit breaks the job dependency contract
or removes the Coolify secret references.
"""
import pathlib
import yaml
import pytest

# The canonical workflow file lives at the monorepo root, not inside api/.
# parent.parent.parent navigates: tests/ → api/ → repo-root/
WORKFLOW_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / ".github" / "workflows" / "deploy.yml"
)
DEPENDABOT_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / ".github" / "dependabot.yml"
)


@pytest.fixture(scope="module")
def workflow():
    assert WORKFLOW_PATH.exists(), f"Workflow file not found: {WORKFLOW_PATH}"
    with WORKFLOW_PATH.open() as f:
        return yaml.safe_load(f)


def test_workflow_file_is_valid_yaml(workflow):
    assert workflow is not None, \
        "deploy.yml parsed to None — likely empty or invalid YAML"


def test_workflow_triggers_on_push_and_pull_request(workflow):
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert "push" in triggers, \
        "push trigger missing — pushes to master won't gate on this workflow"
    assert "pull_request" in triggers, \
        "pull_request trigger missing — PRs skip all checks"


def test_required_jobs_present(workflow):
    jobs = workflow.get("jobs", {})
    for required in ("frontend-ci", "backend-ci", "docker-integration", "deploy"):
        assert required in jobs, f"job '{required}' missing from deploy.yml"


def test_frontend_ci_and_backend_ci_run_in_parallel(workflow):
    jobs = workflow.get("jobs", {})
    assert "needs" not in jobs["frontend-ci"], (
        "frontend-ci must run in parallel (no needs:) — "
        "adding needs: serialises the pipeline and negates the speed win"
    )
    assert "needs" not in jobs["backend-ci"], (
        "backend-ci must run in parallel (no needs:) — "
        "adding needs: serialises the pipeline and negates the speed win"
    )


def test_docker_integration_needs_both_ci_jobs(workflow):
    needs = workflow["jobs"]["docker-integration"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "frontend-ci" in needs, (
        "docker-integration must declare needs: frontend-ci — "
        "a broken Angular build must block the integration smoke test"
    )
    assert "backend-ci" in needs, (
        "docker-integration must declare needs: backend-ci — "
        "a failing test suite must block the integration smoke test"
    )


def test_deploy_depends_on_docker_integration(workflow):
    needs = workflow["jobs"]["deploy"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "docker-integration" in needs, (
        "deploy must declare needs: docker-integration — "
        "the Coolify webhook must not fire if the smoke test has not passed"
    )


def test_coolify_secrets_referenced_in_deploy_job(workflow):
    raw = WORKFLOW_PATH.read_text()
    assert "COOLIFY_WEBHOOK" in raw, \
        "COOLIFY_WEBHOOK secret reference missing from workflow"
    assert "COOLIFY_TOKEN" in raw, \
        "COOLIFY_TOKEN secret reference missing from workflow"


def test_dependabot_config_is_valid_yaml():
    if not DEPENDABOT_PATH.exists():
        pytest.skip(
            f"dependabot.yml not present at {DEPENDABOT_PATH} — owned by Task 3"
        )
    with DEPENDABOT_PATH.open() as f:
        config = yaml.safe_load(f)
    assert config.get("version") == 2, "dependabot.yml must be version 2"
    updates = config.get("updates", [])
    assert len(updates) >= 1, \
        "dependabot.yml must have at least one update entry"
    pip_entry = next(
        (u for u in updates if u.get("package-ecosystem") == "pip"), None
    )
    assert pip_entry is not None, \
        "pip ecosystem entry missing from dependabot.yml"
    assert pip_entry["schedule"]["interval"] == "weekly", \
        "pip schedule must be weekly"
```

**Verify**: `cd api && python -m pytest tests/test_pipeline.py -v` — expect 8 tests, all passing. Confirm path printed in any failure message begins with `{WORKSPACE}/` not `{WORKSPACE}/api/`.

---

## 5. Tests

Complete bodies only. These ARE the tests — no external test file added; `test_pipeline.py` is updated in place (Step 2 above). The assertions below are the exact bodies; the full file is shown in Step 2.

```python
# FRAMEWORK: pytest (same as all api/tests/ — no extra imports needed)

def test_required_jobs_present(workflow):
    jobs = workflow.get("jobs", {})
    for required in ("frontend-ci", "backend-ci", "docker-integration", "deploy"):
        assert required in jobs, f"job '{required}' missing from deploy.yml"
    # Confirms old job names are gone by implication: if 'test' or 'docker-build'
    # were still the only jobs, the above assertions would pass only if the four
    # new names were also added — a reviewer should also run:
    assert "test" not in jobs, \
        "'test' job must be renamed 'backend-ci' — old name still present"
    assert "docker-build" not in jobs, \
        "'docker-build' job must be renamed 'docker-integration' — old name still present"
    assert "build-frontend" not in jobs, \
        "'build-frontend' job must be renamed 'frontend-ci' — old name still present"


def test_frontend_ci_and_backend_ci_run_in_parallel(workflow):
    jobs = workflow.get("jobs", {})
    assert "needs" not in jobs["frontend-ci"], (
        "frontend-ci must run in parallel (no needs:) — "
        "adding needs: serialises the pipeline and negates the speed win"
    )
    assert "needs" not in jobs["backend-ci"], (
        "backend-ci must run in parallel (no needs:) — "
        "adding needs: serialises the pipeline and negates the speed win"
    )


def test_docker_integration_needs_both_ci_jobs(workflow):
    needs = workflow["jobs"]["docker-integration"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "frontend-ci" in needs, (
        "docker-integration must declare needs: frontend-ci"
    )
    assert "backend-ci" in needs, (
        "docker-integration must declare needs: backend-ci"
    )


def test_deploy_depends_on_docker_integration(workflow):
    needs = workflow["jobs"]["deploy"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "docker-integration" in needs, (
        "deploy must declare needs: docker-integration"
    )
```

> **Note on `test_required_jobs_present`**: the three extra `assert "test" not in jobs` lines are additive guards against a partial edit that renames some jobs but not all. They are included in the final file in Step 2.

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step — not at the end. Each boundary below maps to one step above.

1. `ci(pipeline): restructure to parallel frontend-ci + backend-ci jobs` — **after Step 1** — `.github/workflows/deploy.yml`: rename test→backend-ci, build-frontend→frontend-ci (drop artifact upload), replace docker-build with docker-integration (compose-based smoke), update deploy needs.

2. `test(pipeline): fix workflow path + update job graph assertions` — **after Step 2** — `api/tests/test_pipeline.py`: path parent.parent → parent.parent.parent; replace docker-build assertions with parallel-gate and docker-integration assertions; add stale-name guards.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd api && make test
```

**Expected delta**: N → N+1 passing (one net test added: `test_frontend_ci_and_backend_ci_run_in_parallel` and `test_docker_integration_needs_both_ci_jobs` added; `test_docker_build_depends_on_test` removed). Zero pre-existing tests broken.

**Additional structural check** (run after both commits):
```bash
# Confirm path resolution is now correct
python3 -c "
import pathlib
p = pathlib.Path('api/tests/test_pipeline.py').resolve()
wp = p.parent.parent.parent / '.github' / 'workflows' / 'deploy.yml'
print('Resolves to:', wp)
print('Exists:', wp.exists())
print('Git-tracked:', __import__('subprocess').run(
    ['git', 'ls-files', str(wp.relative_to(pathlib.Path.cwd()))],
    capture_output=True, text=True
).stdout.strip())
"
# Expected output:
#   Resolves to: {WORKSPACE}/.github/workflows/deploy.yml
#   Exists: True
#   Git-tracked: .github/workflows/deploy.yml

# YAML validity
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"
# no output = valid

# Confirm job names present in the canonical file
grep "^  [a-z].*:$" .github/workflows/deploy.yml
# Expected: frontend-ci:, backend-ci:, docker-integration:, deploy:
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. The two commits are independent; reverting commit 2 (tests) while keeping commit 1 (YAML) leaves the new YAML in place with the old (now-misaligned) test assertions — acceptable short-term.
- **Per-branch**: if both commits must be undone, `git reset --hard <pre-task-sha>` on the feature branch, or delete and re-create the branch from `master`.
- **Smoke test failure on `master`**: if `docker-integration` fails post-merge because Task 3's `docker-compose.yml` is not yet in the right shape, the deploy job will be blocked (correct behaviour). Fix: merge Task 3 before or alongside Task 4, not after.

---

## 9. Deviations Allowed

- **`docker compose exec -T frontend` fails** — likely means the `docker-compose.yml` at root still defines only an `api` service (Task 3 not yet merged). If so: replace the `docker compose exec -T frontend wget` lines with direct curl against the port-mapped `api` service (`curl -sf http://localhost:3101/health`) as a temporary bridge, log the deviation in the commit body, and open a follow-up to re-enable the frontend exec once Task 3 merges.
- **`web/Dockerfile` absent** — the `frontend-ci` `working-directory: web` step will fail on `npm ci`. Verify Task 2 is merged; if it is not, add an explicit comment to `frontend-ci` that it is stubbed and mark the step with `continue-on-error: true` temporarily. Log the deviation.
- **`wget` unavailable in frontend container** — nginx:alpine includes BusyBox wget; if the Task 2 image is based on a different base (e.g., `nginx:debian`), `wget` may not be available. Substitute `curl` if present, or install `wget` in a multi-stage layer. Log the change.
- **Branch name is `main` not `master`** — the untracked `api/.github/workflows/deploy.yml` uses `main`; the git-tracked root file uses `master`. Trust the git-tracked file; keep `master`. If the remote default branch is actually `main`, update the `on:` trigger to `[main]` and the `if:` conditions to `refs/heads/main`. Log the change.
- **Prescribed path doesn't exist** — run `git rev-parse --show-toplevel` to confirm `{WORKSPACE}`; if the result differs from what the guide assumes, adjust all `parent.parent.parent` chains and YAML working-directory references accordingly. Do not invent a path.
- **Side-effect required** (push, schema change) — STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task rewrites exactly one YAML file and fixes one test file's path resolution. The CI topology change is complete when the four named jobs are in place, the dependency graph is correct, and the structural tests reflect the new structure. It does not own any application code change, any container configuration change, or any secret provisioning.

- **`COOLIFY_TOKEN` / `COOLIFY_WEBHOOK` secret provisioning** — these secrets already exist in the repository (confirmed by passing `test_coolify_secrets_referenced_in_deploy_job`). No new secrets are introduced. If they were removed, that is a separate ops action.
- **`api/.github/workflows/deploy.yml` cleanup** — this untracked local copy exists and currently has divergent content (`main` branch, 3 jobs). Deleting it is safe but is an ops housekeeping action, not a code change; it is deferred to avoid scope creep.
- **`docker-integration` on PRs** — the current design gates `docker-integration` on `master` only. A future decision to run the compose smoke test on all PRs (for earlier feedback) is explicitly deferred; it requires either an environment variable strategy for `CHAIN_PROVIDER` on PR branches or a cost/speed analysis. It belongs in a separate task.
- **`api/.github/dependabot.yml` content** — the `test_dependabot_config_is_valid_yaml` test already has a `pytest.skip` if the root-level `dependabot.yml` is absent; if it is present, the test validates it. Authoring or updating the dependabot config is a separate maintenance action.
- **`SPEC_DOC_DIR` in CI env** — the root `docker-compose.yml` hardcodes `SPEC_DOC_DIR=/data/spec-doc` and mounts the named volume; no CI-level override is needed for the smoke test. If the compose file changes to require an explicit env var injection, that is a Task 3 concern, not Task 4's.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, system boundaries
- [Epic](./epic.md) — Full task scope and dependency ordering
- [Timeline](./timeline.md) — Update status to ✅ after verification passes