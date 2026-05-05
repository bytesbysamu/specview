Now I have everything I need. Writing the guide.

# Task 2: Dockerfile + docker-compose.yml — Implementation Guide

## 1. Context

This task creates the containerization layer for `spec-doc-api`: a `Dockerfile` that produces the single reproducible build artifact and a `docker-compose.yml` that defines the local development and CI execution environment. Neither file existed before this task. Together they turn an undocumented filesystem assumption — that the API reads from a sibling directory — into an explicit, versioned volume contract, and they make the 900-second Gunicorn timeout a first-class, visible decision rather than an accidental default. The `/health` route is already registered in `create_app.py` and needs no changes; this task wires the surrounding infrastructure around it.

**Trade-offs considered:**
- **Dockerfile HEALTHCHECK vs compose healthcheck** — a HEALTHCHECK baked into the image applies to all environments uniformly, but compose-level healthchecks are easier to tune per target without rebuilding the image. Compose-level wins here; the Dockerfile stays environment-agnostic.
- **`gevent` worker class vs `gthread`** — gevent removes the GIL constraint for concurrent AI calls but adds monkey-patching risk and a heavier dependency. Concurrent AI use is not a demonstrated problem at current single-user scale; `gthread` ships now and gevent is added when the problem is real.
- **Single `Dockerfile` with compose-file targets** — one image, two compose files (local/CI now; production in a later task) over per-environment Dockerfiles or a single compose file with profile overrides. This makes the production config separately auditable and prevents accidental production-settings leakage into local runs.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# Confirm you are on, or create, the feature branch (no direct push to master)
git status
git checkout -b feat/task-2-docker

# Confirm the target files don't already exist
git diff HEAD -- Dockerfile docker-compose.yml .dockerignore requirements.txt Makefile

# Verify Python version in use (Dockerfile will use python:3.11-slim per architecture;
# record local version in case a deviation note is needed)
python --version

# Record baseline test count — substitute the actual number below
python -m pytest --co -q 2>/dev/null | tail -1
# → record as N tests collected
python -m pytest -q 2>/dev/null | tail -3
# → record pass/fail counts as the baseline
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: _N_ / _N_ passing (executor fills in actual count; CLAUDE.md cites 192 as of last documentation).

**Note on env var naming**: The architecture document references `AI_PROVIDER`; the codebase uses `CHAIN_PROVIDER` (see `modules/chain/adapter.py` and `.env.example`). This guide uses `CHAIN_PROVIDER` throughout, which is correct. This is a documentation inconsistency in the architecture doc, not a codebase change.

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/requirements.txt` — add `gunicorn` line; all other content unchanged
- `{WORKSPACE}/Dockerfile` — non-root, python:3.11-slim, Gunicorn/gthread/900s
- `{WORKSPACE}/.dockerignore` — excludes `.env`, caches, tests, docs from build context
- `{WORKSPACE}/docker-compose.yml` — single `api` service; `../spec-doc` mounted read-only at `/data/spec-doc`
- `{WORKSPACE}/tests/test_docker.py` — structural assertions for Dockerfile and compose constraints

### To Modify (cite CODEBASE CONTEXT)
- `{WORKSPACE}/requirements.txt` — current state: 6 production deps, no WSGI server → target: add `gunicorn>=21.0.0`
- `{WORKSPACE}/Makefile` — current state: `.PHONY` lists 5 targets, no Docker targets → target: update `.PHONY` + append 5 `docker-*` targets

### To Leave Alone
- `{WORKSPACE}/create_app.py` — `GET /health` already registered (line `@app.get('/health')` returning `jsonify({'status': 'ok'})`); no change needed
- `{WORKSPACE}/.env.example` — already documents `CHAIN_PROVIDER`, `PORT`, `SPEC_DOC_DIR`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY` with correct local defaults
- `{WORKSPACE}/modules/` — all application code; untouched by this task
- `{WORKSPACE}/dtos/models.py` — generated artifact force-committed via `git add -f`; Docker build context includes it via `COPY . .`; `.dockerignore` must not exclude it
- `{WORKSPACE}/openapi.yaml` — referenced at build time by `make check-dtos`; needed in context but not at container runtime (it's a CI/tooling artifact)

---

## 4. Implementation Steps

### Step 1: Add `gunicorn` to `requirements.txt`

**Action**: Append one line to `requirements.txt`. Gunicorn must be a production dependency so `pip install -r requirements.txt` inside the Dockerfile installs it.

**File**: `{WORKSPACE}/requirements.txt` (modify existing)

**Pattern**:
```text
flask>=3.0.0
flask-cors>=4.0.0
anthropic
pydantic>=2.0.0
pyyaml
python-dotenv>=1.0.0
gunicorn>=21.0.0
```

**Verify**:
```bash
grep gunicorn requirements.txt
# → gunicorn>=21.0.0
pip install -r requirements.txt --dry-run 2>&1 | grep gunicorn
# → Would install gunicorn-<version> (or "already satisfied")
```

---

### Step 2: Create `.dockerignore`

**Action**: Create `.dockerignore` at the workspace root. This prevents secrets, caches, test infrastructure, and documentation from entering the build context. The `dtos/` directory must **not** be excluded — `dtos/models.py` is force-committed and required at runtime.

**File**: `{WORKSPACE}/.dockerignore` (new)

**Pattern**:
```
# Secrets — must never enter the image
.env

# Python artifacts
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/

# Test infrastructure — not needed at runtime
tests/
.pytest_cache/
.coverage
htmlcov/

# Documentation and project management
docs/
CLAUDE.md
*.md

# IDE and Claude Code local config
.idea/
.vscode/
.claude/

# Git metadata
.git/
.gitignore

# Docker files — compose config is host-side only
.dockerignore
docker-compose*.yml
```

**Verify**:
```bash
# Confirm .env is excluded and dtos/ is NOT excluded
docker build --no-cache --dry-run . 2>&1 || true
# If --dry-run is not available on your Docker version, verify via:
cat .dockerignore | grep -E "^\.env$"
# → .env
cat .dockerignore | grep dtos
# → (empty — dtos must not be excluded)
```

---

### Step 3: Create `Dockerfile`

**Action**: Create the Dockerfile. The load-bearing constraints are: (1) `--timeout 900` so AI provider calls running up to 15 minutes are not silently killed; (2) `USER appuser` before `CMD` for non-root security posture; (3) `--preload` so the AI provider adapter initializes once before workers fork. These three lines are the ones the structural tests assert on.

**File**: `{WORKSPACE}/Dockerfile` (new)

**Pattern**:
```dockerfile
FROM python:3.11-slim

# Non-root user — defense against container escape
RUN addgroup --system appgroup \
 && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install dependencies before copying source — better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (respects .dockerignore)
COPY . .

# Drop to non-root before the process starts
USER appuser

EXPOSE 3101

# 2 workers × 4 gthread threads.
# --timeout 900: AI provider calls run up to 15 minutes;
#   Gunicorn's default 120 silently kills them with no error visible to the caller.
# --preload: AI provider adapter initializes once before workers fork.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--worker-class", "gthread", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "900", \
     "--preload", \
     "create_app:create_app()"]
```

**Verify**:
```bash
docker build -t spec-doc-api:smoke .
# → Successfully built <sha>
docker run --rm spec-doc-api:smoke gunicorn --version
# → gunicorn (version <21.x>)
docker image inspect spec-doc-api:smoke --format '{{.Config.User}}'
# → appuser
```

---

### Step 4: Create `docker-compose.yml`

**Action**: Create `docker-compose.yml` targeting local development and CI. The critical contract: `../spec-doc` (the sibling repo, parent of the `api/` directory) is mounted read-only at `/data/spec-doc`, and `SPEC_DOC_DIR=/data/spec-doc` is set so `config.py`'s `BASE_DIR` resolves to that mount. `CHAIN_PROVIDER` defaults to `claude` for local dev; CI overrides it to `mock` via the shell environment before running compose.

**File**: `{WORKSPACE}/docker-compose.yml` (new)

**Pattern**:
```yaml
services:
  api:
    build: .
    ports:
      - "3101:3101"
    volumes:
      - ../spec-doc:/data/spec-doc:ro
    environment:
      SPEC_DOC_DIR: /data/spec-doc
      CHAIN_PROVIDER: ${CHAIN_PROVIDER:-claude}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:4201}
      PORT: "3101"
    healthcheck:
      test:
        - "CMD-SHELL"
        - >
          python -c "import urllib.request;
          urllib.request.urlopen('http://localhost:3101/health')"
          || exit 1
      interval: 10s
      timeout: 5s
      start_period: 15s
      retries: 5
```

**Verify**:
```bash
# Validate YAML structure
python -c "import yaml; d=yaml.safe_load(open('docker-compose.yml')); print(list(d['services'].keys()))"
# → ['api']

# Confirm read-only mount string appears verbatim
grep ':ro' docker-compose.yml
# → - ../spec-doc:/data/spec-doc:ro

# Start the container with CHAIN_PROVIDER=mock (no API key needed)
CHAIN_PROVIDER=mock docker compose up -d
# Wait for health
sleep 5
curl -sf http://localhost:3101/health
# → {"status":"ok"}
docker compose down
```

---

### Step 5: Update `Makefile` with Docker targets

**Action**: Add 5 `docker-*` targets to the existing Makefile. Update the `.PHONY` line to include all 5 new targets. The existing targets and spacing must not change.

**File**: `{WORKSPACE}/Makefile` (modify existing)

Update the `.PHONY` line (current):
```makefile
.PHONY: dev test lint generate-dtos check-dtos install
```

Updated `.PHONY` line:
```makefile
.PHONY: dev test lint generate-dtos check-dtos install docker-build docker-up docker-down docker-logs docker-smoke
```

Append after the last existing target block:
```makefile
## Build the Docker image
docker-build:
	docker compose build

## Start the containerized API (detached; use docker-logs to follow output)
docker-up:
	docker compose up -d

## Stop and remove the containerized API
docker-down:
	docker compose down

## Tail API container logs (Ctrl-C to stop)
docker-logs:
	docker compose logs -f api

## Smoke test the running container — mirrors the CI docker-build job
## Requires: container started with make docker-up and CHAIN_PROVIDER=mock
docker-smoke:
	@curl -sf http://localhost:3101/health | grep -q 'ok' && echo "✓ /health OK"
	@curl -sf http://localhost:3101/api/projects > /dev/null && echo "✓ /api/projects OK"
```

**Verify**:
```bash
make --dry-run docker-build
# → docker compose build
make --dry-run docker-up
# → docker compose up -d
make --dry-run docker-smoke
# → curl -sf http://localhost:3101/health ...

# End-to-end smoke via make targets
CHAIN_PROVIDER=mock make docker-up
sleep 8
make docker-smoke
# → ✓ /health OK
# → ✓ /api/projects OK
make docker-down
```

---

### Step 6: Add `tests/test_docker.py`

**Action**: Create structural tests that fail loudly if the load-bearing constraints are removed from the Docker config files. Test naming follows the repo convention (`prefix_behaviorDescription`, collected by `python_functions = ["test_*", "*_*"]` in `pyproject.toml`). No fixtures needed — these are pure file-inspection tests.

**File**: `{WORKSPACE}/tests/test_docker.py` (new)

**Pattern**: See full test body in §5 below.

**Verify**:
```bash
python -m pytest tests/test_docker.py -v
# → 14 passed
```

---

## 5. Tests

```python
"""Structural tests for Docker configuration.

These tests verify that the Dockerfile and docker-compose.yml encode
the load-bearing constraints documented in the architecture:
  - 900-second Gunicorn timeout (AI provider calls run up to 15 minutes;
    the Gunicorn default of 120 silently kills them with no visible error)
  - Non-root container user (security posture)
  - Read-only spec-doc bind-mount (data contract — local/CI must not mutate source)
"""
from pathlib import Path

import yaml

_ROOT = Path(__file__).parent.parent  # {WORKSPACE} root


# ── Dockerfile ───────────────────────────────────────────────────────────────

def dockerfile_exists():
    assert (_ROOT / "Dockerfile").is_file(), \
        "Dockerfile not found at workspace root"


def dockerfile_baseImage_is_python311Slim():
    text = (_ROOT / "Dockerfile").read_text()
    assert "FROM python:3.11-slim" in text, \
        "Base image must be python:3.11-slim (matches local dev; slim avoids build toolchain)"


def dockerfile_creates_nonRootUser():
    text = (_ROOT / "Dockerfile").read_text()
    assert "adduser" in text, \
        "Dockerfile must create a non-root user (defense against container escape)"


def dockerfile_switches_to_appuser():
    text = (_ROOT / "Dockerfile").read_text()
    assert "USER appuser" in text, \
        "Dockerfile must switch to appuser before CMD"


def dockerfile_gunicorn_timeout_is_900():
    text = (_ROOT / "Dockerfile").read_text()
    lines_with_timeout = [line.strip() for line in text.splitlines() if "--timeout" in line]
    assert lines_with_timeout, \
        "Gunicorn --timeout flag must be present in Dockerfile CMD"
    assert any("900" in line for line in lines_with_timeout), (
        "Gunicorn timeout must be 900 — AI provider calls run up to 15 minutes; "
        "the default 120 silently kills them without surfacing an error to the caller"
    )


def dockerfile_uses_gthread_workerClass():
    text = (_ROOT / "Dockerfile").read_text()
    assert "gthread" in text, \
        "Gunicorn must use gthread worker class (handles I/O-bound AI calls without gevent)"


def dockerfile_has_preload_flag():
    text = (_ROOT / "Dockerfile").read_text()
    assert "--preload" in text, \
        "Gunicorn --preload missing — AI provider adapter must initialize once before workers fork"


def dockerfile_exposes_port_3101():
    text = (_ROOT / "Dockerfile").read_text()
    assert "EXPOSE 3101" in text, \
        "Dockerfile must EXPOSE 3101 to document the service port"


# ── docker-compose.yml ────────────────────────────────────────────────────────

def dockerCompose_exists():
    assert (_ROOT / "docker-compose.yml").is_file(), \
        "docker-compose.yml not found at workspace root"


def dockerCompose_is_valid_yaml():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    assert isinstance(data, dict), \
        "docker-compose.yml must parse as a YAML mapping"


def dockerCompose_defines_api_service():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    assert "api" in data.get("services", {}), \
        "docker-compose.yml must define an 'api' service"


def dockerCompose_mounts_specDoc_readonly():
    text = (_ROOT / "docker-compose.yml").read_text()
    assert "/data/spec-doc:ro" in text, (
        "spec-doc must be mounted read-only (:ro) at /data/spec-doc — "
        "local and CI environments must not mutate the source data"
    )


def dockerCompose_sets_specDocDir_to_containerPath():
    text = (_ROOT / "docker-compose.yml").read_text()
    assert "SPEC_DOC_DIR" in text and "/data/spec-doc" in text, \
        "SPEC_DOC_DIR must be set to /data/spec-doc so config.py resolves to the mounted volume"


def dockerCompose_maps_port_3101():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    ports = data["services"]["api"].get("ports", [])
    assert any("3101" in str(p) for p in ports), \
        "Port 3101 must be mapped in docker-compose.yml services.api.ports"
```

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after completing each step — not once at the end. Each commit message below corresponds exactly to one step above.

1. `chore(api): add gunicorn to requirements` — **after Step 1** — `requirements.txt`: adds `gunicorn>=21.0.0` as a production dependency so the Dockerfile's `pip install -r requirements.txt` installs the WSGI server.

2. `build(api): add Dockerfile and .dockerignore` — **after Step 3** (commit Steps 2+3 together; `.dockerignore` is only meaningful alongside the `Dockerfile`) — `Dockerfile`, `.dockerignore`: non-root `python:3.11-slim` image; 900-second Gunicorn timeout; gthread + preload.

3. `build(api): add docker-compose.yml with read-only spec-doc mount` — **after Step 4** — `docker-compose.yml`: local dev + CI target; `../spec-doc:/data/spec-doc:ro` volume contract; `CHAIN_PROVIDER` parameterized for CI mock override.

4. `chore(api): add docker make targets` — **after Step 5** — `Makefile`: `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-smoke` targets wrap compose commands behind the existing make interface.

5. `test(api): add structural tests for Dockerfile and docker-compose` — **after tests pass in Step 6** — `tests/test_docker.py`: 14 structural assertions for timeout, non-root user, read-only mount, and port mapping.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
python -m pytest -q
```

**Expected delta**: _N_ → _N+14_ passing. Zero pre-existing tests broken.

Full smoke verification (container + pytest together):
```bash
# 1. Run the test suite against the host (no container needed)
python -m pytest -q
# → N+14 passed

# 2. Build and smoke the container
CHAIN_PROVIDER=mock make docker-up
sleep 10
make docker-smoke
# → ✓ /health OK
# → ✓ /api/projects OK
make docker-down
```

---

## 8. Rollback

- **Per-step**: every commit is independently revertible.
  ```bash
  git revert <sha>   # creates a revert commit; safe on a feature branch
  ```
- **Per-branch**: if verification fails and the feature branch is not yet merged:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — discards all 5 commits
  # or simply delete the branch:
  git checkout master && git branch -D feat/task-2-docker
  ```
- **Image cleanup** (local Docker state only, no repository impact):
  ```bash
  docker rmi spec-doc-api:smoke
  docker compose down --rmi local
  ```

---

## 9. Deviations Allowed

- **Local Python version is 3.12, not 3.11** → use `python:3.11-slim` in the Dockerfile as specified in the architecture. If 3.11 introduces a runtime incompatibility with an installed package, note it in the commit body and escalate — do not silently change to 3.12 without flagging it.
- **`../spec-doc` doesn't exist as a directory at compose-up time** → `docker compose up` will fail with a bind-mount error. This is expected if the sibling `spec-doc/` repo is not checked out. Document it in the commit body as an environment setup requirement; do not change the volume path.
- **`docker compose` vs `docker-compose`** (v1 vs v2 CLI) → the Makefile targets use `docker compose` (v2 plugin syntax, no hyphen). If the executor's Docker installation only has v1, translate the Makefile targets to `docker-compose` and log as a deviation.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task delivers the Dockerfile and local/CI compose file only. It does not extend to the production deployment target, the CI/CD pipeline, or any surrounding infrastructure scaffolding. An eager executor may notice that Coolify deployment, GitHub Actions jobs, and `.env.example` updates for production secrets are adjacent work — none of that belongs here.

- **`docker-compose.coolify.yml`** — production Traefik labels and named volume; separate task; requires Coolify service to be configured first so label values are known.
- **`.github/workflows/deploy.yml`** — the three-job sequential pipeline (test → docker-build smoke → Coolify webhook deploy); separate task; depends on the `docker-compose.coolify.yml` existing and Coolify webhook secrets being provisioned in GitHub.
- **`.env.example` additions for production secrets** (`COOLIFY_WEBHOOK`, `COOLIFY_TOKEN`) — deferred to the pipeline task, where they belong as context for CI secrets setup.
- **Dependabot configuration** — `.github/dependabot.yml` for weekly pip updates; deferred to the pipeline task per the architecture's "ship together" intent.
- **`spec-doc-live` worktree removal** — the architecture notes this as a side effect of containerization, explicitly deferred until the container is proven stable in production.
- **Gevent worker class migration** — deferred until concurrent AI use is a demonstrated problem; the architecture is explicit on this point.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for all decisions reflected here
- [Epic](./epic.md) — Full task scope and sequencing
- [Timeline](./timeline.md) — Update status to ✅ after Step 6 commit passes