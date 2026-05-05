# Task 4: GitHub Actions Pipeline — Implementation Guide

**Purpose**: Wire the existing quality gates (pytest, DTO-drift) and new Docker smoke test into a sequential CI/CD pipeline that fires on every push and PR, deploying to production via a Coolify webhook on `main` only.

**Effort**: 0.5 days

**Dependencies**: Tasks 1–3 complete — `/health` route exists in `create_app.py`; `docker-compose.yml` with read-only `../spec-doc` bind-mount exists; Makefile has `docker-build`, `docker-up`, `docker-down`, `docker-smoke` targets; `mock` AI provider registered in `modules/chain/adapter.py`.

**Parallel With**: —

**Blocks**: Automated production deploys; Dependabot PRs receiving CI validation.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task wires the three enforcement layers the architecture describes — the pytest suite, DTO-drift check, and Docker smoke test — into a `.github/workflows/deploy.yml` pipeline that runs on every push and PR. The pipeline is intentionally sequential: the smoke test does not run unless tests pass; the deploy webhook does not fire unless the smoke test passes. No partial-success path exists. A `dependabot.yml` is shipped at the same time to prevent the common gap where a CI pipeline ships without a dependency-update mechanism, leaving the newly enforced pipeline to silently bit-rot. The `mock` AI provider (a prerequisite this task verifies but does not create) allows the docker-build smoke job to start the container without a live API key, keeping CI costs and credential requirements zero for the smoke signal.

**Trade-offs considered:**

- **Parallelising test + docker-build** — rejected because a passing smoke test on a broken test suite is not a meaningful signal; sequential jobs make the dependency explicit and keep the failure surface narrow.
- **Storing image in GHCR and pulling in deploy** — rejected per architecture decision: Coolify builds from source on deploy; a registry adds push/pull steps and credentials with no named consumer at this stage.
- **Single workflow file vs. separate `ci.yml` + `deploy.yml`** — a single file with job-level `if:` guards is preferred; the pipeline is small enough that splitting adds indirection without benefit.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm clean working tree on target paths
git status
git diff HEAD -- .github/ Makefile requirements-dev.txt

# Verify prior-task deliverables are present
grep -n "^lint:" Makefile             # expect a line; if absent, Step 1 adds it
grep -n "^docker-build:" Makefile     # must exist from Task 3
grep -n "^docker-up:" Makefile        # must exist from Task 3
grep -n "^docker-down:" Makefile      # must exist from Task 3
grep -n "^docker-smoke:" Makefile     # must exist from Task 3
grep -n "/health" create_app.py       # must exist from Task 1
ls docker-compose.yml                 # must exist from Task 3

# Verify mock provider is registered
grep -n "mock" modules/chain/adapter.py   # must exist — prerequisite for this task

# Baseline test count (record the number)
make test 2>&1 | tail -5
```

**If working tree is dirty on target files**: stash or commit unrelated changes before proceeding.

**If `docker-build`, `docker-up`, `docker-down`, `docker-smoke` are missing from the Makefile**: STOP — Task 3 is incomplete. This task cannot proceed until those targets exist.

**If `mock` provider is absent from `modules/chain/adapter.py`**: STOP — the docker-build smoke job cannot run without it. Mark [REQUIRES APPROVAL] and raise with the team.

**Baseline recorded**: 192 / 192 passing (per CLAUDE.md).

---

## 3. Files

### To Create (new)

- `.github/workflows/deploy.yml` *(new)* — three-job sequential CI/CD pipeline; depends on `docker-compose.yml`, `Makefile`, and mock AI provider from prior tasks
- `.github/dependabot.yml` *(new)* — weekly pip dependency updates; no external dependencies
- `tests/test_pipeline.py` *(new)* — pytest structural tests for workflow YAML; depends on `pyyaml` in `requirements-dev.txt`

### To Modify (cite CODEBASE CONTEXT)

- `Makefile` — add `lint` target if absent (pre-flight grep will confirm); `docker-smoke` target should already be present from Task 3 but is verified here
- `requirements-dev.txt` — add `ruff` (linter) and `pyyaml` (for workflow structure tests) if not already present; the CLAUDE.md `requirements*.txt` glob confirms this file exists

### To Leave Alone

- `create_app.py` — health route added in Task 1; no changes needed
- `docker-compose.yml` — bind-mount contract established in Task 3; the CI workflow reads it as-is
- `modules/chain/adapter.py` — mock provider is a prerequisite; this task does not modify it
- `dtos/models.py` — never hand-edited per CLAUDE.md repo rule
- `openapi.yaml` — no changes; `make check-dtos` validates its sync state

---

## 4. Implementation Steps

### Step 1: Add `lint` Makefile target and linter dependency

**Action**: Check whether `make lint` exists (`grep -n "^lint:" Makefile`). If absent, add `ruff` to `requirements-dev.txt` and a `lint:` target to the Makefile. If it already exists, skip the edits but still verify it passes cleanly.

**File**: `Makefile` + `requirements-dev.txt` (both from prior tasks; paths relative to repo root)

**Pattern**:
```makefile
# In Makefile — add after existing targets
lint:
	ruff check .
```

```text
# In requirements-dev.txt — append if ruff is absent
ruff>=0.4.0
pyyaml>=6.0
```

**Verify**:
```bash
pip install -r requirements-dev.txt
make lint
# expect: exit 0, zero lint errors (or only pre-existing ones that cannot be fixed in this task)
```

> If `make lint` exists and calls a different linter (e.g., `flake8`), keep the existing target and log a deviation. Do not replace an existing linter with ruff.

---

### Step 2: Create `.github/dependabot.yml`

**Action**: Create the Dependabot configuration file scoped to pip with a weekly schedule.

**File**: `.github/dependabot.yml` *(new)*

**Pattern**:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

**Verify**:
```bash
python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"
# expect: no exception — valid YAML
```

**Commit after this step** (see Commit Plan item 2).

---

### Step 3: Create the `test` job in `.github/workflows/deploy.yml`

**Action**: Create the workflow file with triggers and the `test` job only. The `docker-build` and `deploy` jobs are added in Step 4 to keep each commit independently reviewable.

**File**: `.github/workflows/deploy.yml` *(new)*

**Pattern**:
```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: "requirements*.txt"

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
```

**Verify**:
```bash
python -c "
import yaml, sys
w = yaml.safe_load(open('.github/workflows/deploy.yml'))
assert 'test' in w['jobs'], 'test job missing'
assert 'push' in w['on'], 'push trigger missing'
assert 'pull_request' in w['on'], 'pull_request trigger missing'
print('workflow YAML valid')
"
```

**Commit after this step** (see Commit Plan item 3).

---

### Step 4: Add `docker-build` and `deploy` jobs to the workflow

**Action**: Append the `docker-build` and `deploy` jobs to `.github/workflows/deploy.yml`. The `docker-build` job creates the sibling `spec-doc` stub that the `docker-compose.yml` bind-mount requires, overrides `AI_PROVIDER=mock`, polls `/health`, hits `/api/projects`, then tears down unconditionally. The `deploy` job issues the Coolify webhook.

**File**: `.github/workflows/deploy.yml` (append to `jobs:` block)

**Pattern**:
```yaml
  docker-build:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Create sibling spec-doc stub
        run: mkdir -p ${{ github.workspace }}/../spec-doc

      - name: Build Docker image
        run: make docker-build

      - name: Start container
        run: make docker-up
        env:
          AI_PROVIDER: mock
          ANTHROPIC_API_KEY: ci-mock-key-not-used

      - name: Poll /health (60s timeout)
        run: |
          for i in $(seq 1 30); do
            if curl -sf http://localhost:3101/health > /dev/null; then
              echo "Health OK on attempt $i"
              exit 0
            fi
            echo "Attempt $i: not ready, sleeping 2s"
            sleep 2
          done
          echo "ERROR: /health did not respond within 60s"
          docker compose logs
          exit 1

      - name: Smoke test /api/projects
        run: |
          response=$(curl -sf http://localhost:3101/api/projects)
          echo "Response: $response"

      - name: Tear down
        if: always()
        run: make docker-down

  deploy:
    needs: docker-build
    if: github.ref == 'refs/heads/main'
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

**Verify**:
```bash
python -c "
import yaml
w = yaml.safe_load(open('.github/workflows/deploy.yml'))
jobs = w['jobs']
assert 'docker-build' in jobs and 'deploy' in jobs
db_needs = jobs['docker-build'].get('needs', [])
if isinstance(db_needs, str): db_needs = [db_needs]
assert 'test' in db_needs, 'docker-build must need test'
dep_needs = jobs['deploy'].get('needs', [])
if isinstance(dep_needs, str): dep_needs = [dep_needs]
assert 'docker-build' in dep_needs, 'deploy must need docker-build'
content = open('.github/workflows/deploy.yml').read()
assert 'COOLIFY_WEBHOOK' in content
assert 'COOLIFY_TOKEN' in content
print('all structural checks passed')
"
```

**Commit after this step** (see Commit Plan item 4).

---

### Step 5: Write workflow structure tests

**Action**: Create `tests/test_pipeline.py` with pytest assertions covering every structural property the architecture mandates.

**File**: `tests/test_pipeline.py` *(new)*

**Pattern** (see full bodies in §5 below):
```python
import yaml, pathlib, pytest

WORKFLOW = pathlib.Path(__file__).parent.parent / ".github" / "workflows" / "deploy.yml"
```

**Verify**:
```bash
make test 2>&1 | tail -10
# expect: 192 + 7 = 199 passing, 0 failed
```

**Commit after this step** (see Commit Plan item 5).

---

## 5. Tests

Framework: `pytest` (matches repo per CLAUDE.md). File: `tests/test_pipeline.py`.

```python
"""
Structural tests for .github/workflows/deploy.yml.
These fail fast if a future edit breaks the sequential-job dependency contract
or removes the Coolify secret references.
"""
import pathlib
import yaml
import pytest

WORKFLOW_PATH = pathlib.Path(__file__).parent.parent / ".github" / "workflows" / "deploy.yml"
DEPENDABOT_PATH = pathlib.Path(__file__).parent.parent / ".github" / "dependabot.yml"


@pytest.fixture(scope="module")
def workflow():
    assert WORKFLOW_PATH.exists(), f"Workflow file not found: {WORKFLOW_PATH}"
    with WORKFLOW_PATH.open() as f:
        return yaml.safe_load(f)


def test_workflow_file_is_valid_yaml(workflow):
    assert workflow is not None, "deploy.yml parsed to None — likely empty or invalid YAML"


def test_workflow_triggers_on_push_and_pull_request(workflow):
    triggers = workflow.get("on", {})
    assert "push" in triggers, "push trigger missing — PRs to main won't gate on this workflow"
    assert "pull_request" in triggers, "pull_request trigger missing — PRs skip all checks"


def test_required_jobs_present(workflow):
    jobs = workflow.get("jobs", {})
    for required in ("test", "docker-build", "deploy"):
        assert required in jobs, f"job '{required}' missing from deploy.yml"


def test_docker_build_depends_on_test(workflow):
    needs = workflow["jobs"]["docker-build"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "test" in needs, "docker-build must declare needs: test — smoke test can't run before tests pass"


def test_deploy_depends_on_docker_build(workflow):
    needs = workflow["jobs"]["deploy"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "docker-build" in needs, "deploy must declare needs: docker-build — deploy can't run before smoke passes"


def test_coolify_secrets_referenced_in_deploy_job(workflow):
    raw = WORKFLOW_PATH.read_text()
    assert "COOLIFY_WEBHOOK" in raw, "COOLIFY_WEBHOOK secret reference missing from workflow"
    assert "COOLIFY_TOKEN" in raw, "COOLIFY_TOKEN secret reference missing from workflow"


def test_dependabot_config_is_valid_yaml():
    assert DEPENDABOT_PATH.exists(), f"dependabot.yml not found: {DEPENDABOT_PATH}"
    with DEPENDABOT_PATH.open() as f:
        config = yaml.safe_load(f)
    assert config.get("version") == 2, "dependabot.yml must be version 2"
    updates = config.get("updates", [])
    assert len(updates) >= 1, "dependabot.yml must have at least one update entry"
    pip_entry = next((u for u in updates if u.get("package-ecosystem") == "pip"), None)
    assert pip_entry is not None, "pip ecosystem entry missing from dependabot.yml"
    assert pip_entry["schedule"]["interval"] == "weekly", "pip schedule must be weekly"
```

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after completing each numbered step — not at the end. Each boundary below names which step it follows.

1. `chore(makefile): add lint target and ruff dev dependency` — after Step 1 — files: `Makefile`, `requirements-dev.txt`
2. `ci(deps): add dependabot weekly pip updates` — after Step 2 — files: `.github/dependabot.yml`
3. `ci(pipeline): add test job to deploy workflow` — after Step 3 — files: `.github/workflows/deploy.yml`
4. `ci(pipeline): add docker-build smoke and deploy jobs` — after Step 4 — files: `.github/workflows/deploy.yml`
5. `test(pipeline): add workflow structure tests` — after Step 5 passes — files: `tests/test_pipeline.py`

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation. Example:

```
ci(pipeline): add test job to deploy workflow

Deviations:
- make lint already existed as flake8 target; ruff not added
```

---

## 7. Verification

```bash
make test
```

**Expected delta**: 192 → 199 passing (7 new tests in `tests/test_pipeline.py`). Zero pre-existing tests broken.

Secondary verification — confirm workflow YAML is syntactically accepted by GitHub's schema (optional, requires `actionlint` if installed):

```bash
# optional — only if actionlint is available
actionlint .github/workflows/deploy.yml
# expect: no errors
```

---

## 8. Rollback

- **Per-step**: each step has its own commit. Revert individually:
  ```bash
  git revert <sha>   # creates a new revert commit; does not rewrite history
  ```
- **Per-branch**: if verification fails catastrophically after all steps:
  ```bash
  git reset --hard <pre-task-sha>
  # or, on a feature branch:
  git checkout main && git branch -D feat/task4-pipeline
  ```
- **Dependabot-only rollback**: if `dependabot.yml` causes unwanted PR noise before the team is ready:
  ```bash
  git revert <dependabot-commit-sha>
  ```

---

## 9. Deviations Allowed

- **`make lint` already exists with a different linter** — keep the existing target; do not replace it. Log in the commit body. Skip the `ruff` addition to `requirements-dev.txt`.
- **`make docker-smoke` or other Makefile targets missing from Task 3** — STOP. This is a Task 3 incompletion. Do not add those targets here; raise with the team. The Commit Plan for this task does not include Makefile additions beyond `lint`.
- **`requirements-dev.txt` uses `pytest-cov` or another runner wrapper** — the `pyyaml` addition is still valid; append it. If `pyyaml` is already present (e.g., as a transitive dep in `requirements.txt`), skip adding it to `requirements-dev.txt` and log the deviation.
- **`/api/projects` returns a non-200 response against an empty stub dir** — if the endpoint requires at least one file to exist, create a minimal stub: `echo '{}' > ${{ github.workspace }}/../spec-doc/.spec-doc-project`. Log the deviation and the exact stub structure.
- **`COOLIFY_WEBHOOK` format is POST, not GET** — Coolify's webhook endpoint varies by version. If the team confirms it's a POST, change the `curl -X GET` to `curl -X POST`. Mark [REQUIRES APPROVAL] before changing secret format assumptions.
- **Side-effect required** (git push to remote, publishing secrets, triggering live deploy) — STOP, mark [REQUIRES APPROVAL], do not proceed.

---

## 10. Out of Scope

This task ships the pipeline skeleton and the Dependabot wiring. It does not address the operational readiness of production or the deployment target configuration. An eager executor might notice several adjacent improvements — all of them are explicitly deferred here to preserve blast radius.

- **Provisioning `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` secrets in GitHub** — the pipeline ships without them; the deploy job will fail until they are set. Provisioning is a manual operation in the GitHub repo settings UI that requires access to the Coolify instance. It is a post-ship step, not part of this pipeline task.
- **Staging / preview environments** — no second-environment trigger exists; production and local are the only targets per architecture. Do not add a `staging` job or branch rule.
- **Matrix builds across Python versions** — a single-user internal tool with a pinned `python:3.11-slim` base image has no consumer for multi-version CI. Deferred until a second Python version is actually needed.
- **Slack / email notifications on deploy failure** — no named consumer; deferred until the team asks for it.
- **`spec-doc-live` worktree cleanup** — side effect of containerization, not pipeline work. Deferred until the container is proven stable in production per architecture decision.
- **`actionlint` or workflow linting as a required step** — nice-to-have, but adds a non-standard tool dependency. Deferred; the `test_pipeline.py` structural tests provide equivalent coverage for the properties that matter.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale and component specs
- [Epic](./epic.md) – Full task scope and sequencing
- [Timeline](./timeline.md) – Status tracking (mark Task 4 complete after Step 5 commit)