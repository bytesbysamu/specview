I now have all the concrete details needed. Writing the guide:

---

# Task 3: Split Compose and Simplify Backend Dockerfile

## 1. Context

`api/docker-compose.yml` currently runs a single `api` service whose `build: .` context points at `api/Dockerfile` — a two-stage file that first compiles the Angular SPA inside a `node:20-alpine` build stage before creating the Flask runtime image. That coupling means every Flask-only change forces a full Angular rebuild, and the production container carries the Angular dist as static files served by a Python catch-all route. Task 3 severs that coupling: the `api/Dockerfile` becomes a single-stage Flask-only image, and `api/docker-compose.yml` grows a second `frontend` service whose build context is `../web` (pointing at the `web/Dockerfile` delivered by Task 2). The backend service drops its `ports:` mapping in favour of `expose:` — Coolify/Traefik becomes the only external ingress, consistent with every sibling project. The split is the prerequisite unlock for Task 4 (parallel CI jobs that build each service independently) and Task 5 (removing the Flask static-serve blueprint once nginx owns that responsibility).

**Trade-offs considered:**
- **Keeping a single multi-stage Dockerfile** — rejected; ties every backend build to the Node.js toolchain and prevents independent image caching per service in CI.
- **Moving `docker-compose.yml` to the repo root** — rejected for this task; the existing `api/docker-compose.yml` location is encoded in `api/tests/test_docker.py` (`_ROOT = Path(__file__).parent.parent = api/`), and relocating the file would require cascading test and Makefile changes that belong to Task 4's CI restructure.
- **Keeping compose at `api/docker-compose.yml` with `build: ../web` for the frontend** — preferred; zero friction with the existing test-path contract, Docker Compose resolves `../web` relative to the compose-file directory, and the `api/Dockerfile` becomes a clean single-stage file whose build context is unambiguously `api/`.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From {WORKSPACE}/api/
git status
git diff HEAD -- Dockerfile docker-compose.yml tests/test_docker.py
make test
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**Verify Task 1 prerequisite** (`/health` exists):
```bash
grep -n "def health" create_app.py          # expect: @app.get('/health') handler
grep -n "^  /health:" openapi.yaml           # expect: /health GET defined
```

**Verify Task 2 prerequisite** (`web/Dockerfile` exists):
```bash
ls ../web/Dockerfile                          # must exist — Task 3 requires it
```

If `../web/Dockerfile` is missing, **stop and complete Task 2 first**.

**Baseline recorded**: 624 / 624 passing.

---

## 3. Files

### To Create (new)
*(none — all changes are modifications)*

### To Modify (cite CODEBASE CONTEXT)
- `api/Dockerfile` — currently two-stage (node:20-alpine + python:3.11-slim); remove Stage 1 entirely; update `COPY` paths from repo-root context to `api/` context
- `api/docker-compose.yml` — currently single `api` service with `ports: 3101:3101`; rewrite to two services (`backend`, `frontend`) with `expose:` only and a shared bridge network
- `api/tests/test_docker.py` — two assertions will fail against the rewritten compose (`dockerCompose_defines_api_service`, `dockerCompose_maps_port_3101`); update both in-place; add five new assertions

### To Leave Alone
- `api/docker-compose.coolify.yml` — tested by `api/tests/test_deploy_config.py`; not in Task 3 scope; updating it for Coolify production traffic belongs to Task 5
- `api/tests/test_deploy_config.py` — tests `docker-compose.coolify.yml`; no changes required here
- `api/create_app.py` — `web_serve_bp` stays registered until Task 5 explicitly removes it; the simplified Dockerfile no longer copies `web/` dist, so Flask's catch-all 404s on direct access, which is intentional (nginx is the entry point in Docker mode)
- `api/Makefile` — docker-* targets are tested by `test_deploy_config.py`; Makefile changes belong to Task 4
- `web/nginx/nginx.conf` — nginx upstream (`backend:3101`) is Task 2's deliverable; do not edit
- `api/dtos/models.py` — no API contract changes in this task

---

## 4. Implementation Steps

### Step 1: Simplify `api/Dockerfile` to Flask-only

**Action**: Delete Stage 1 (`FROM node:20-alpine AS frontend-builder` through `RUN npx ng build …`). Delete the `COPY --from=frontend-builder` line. Replace `COPY api/requirements.txt ./` with `COPY requirements.txt ./` and `COPY api/ ./` with `COPY . .`. Update the build-context comment. Stage 2 (`AS final`) becomes the sole stage — all gunicorn flags, non-root user, and `EXPOSE 3101` are preserved verbatim.

**File**: `api/Dockerfile`

**Pattern**:
```dockerfile
# Flask-only image — Angular is served by the frontend container (nginx).
# Build context: api/ directory.
#
# CI:    docker build -t spec-doc-backend:ci api/
# Local: docker compose -f api/docker-compose.yml build backend

FROM python:3.11-slim AS final

# Non-root user — defense against container escape.
RUN addgroup --system appgroup \
 && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install Python dependencies before copying source — better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask source (build context is api/).
COPY . .

# Drop to non-root before the process starts.
USER appuser

EXPOSE 3101

# 2 workers × 4 gthread threads.
# --timeout 900: AI provider calls run up to 15 minutes; gunicorn's default 120
#   silently kills them with no error visible to the caller.
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
grep -c "FROM node:" Dockerfile                      # expect: 0
grep -c "frontend-builder" Dockerfile                # expect: 0
grep "FROM python:3.11-slim" Dockerfile              # expect: one match
grep "COPY requirements.txt" Dockerfile              # expect: COPY requirements.txt ./ (no api/ prefix)
grep "COPY \. \." Dockerfile                         # expect: COPY . .
grep "\-\-timeout" Dockerfile                        # expect: --timeout 900
grep "EXPOSE 3101" Dockerfile                        # expect: EXPOSE 3101
```

---

### Step 2: Rewrite `api/docker-compose.yml` to two services

**Action**: Replace the entire file. The `backend` service keeps `build: .` (context = `api/`), `expose: ["3101"]`, the `../spec-doc:/data/spec-doc:ro` bind-mount, and the existing healthcheck. Add the `frontend` service with `build: ../web`, `expose: ["80"]`, a `depends_on: backend: condition: service_healthy` guard, and a healthcheck that probes `/api/health` through nginx (proving the proxy path). Add a top-level `networks:` block declaring the `spec-doc-net` bridge. Both services join `spec-doc-net`.

**File**: `api/docker-compose.yml`

**Pattern** (complete replacement):
```yaml
# Two-service split (Task 3).
# nginx (frontend:80) is the Coolify entry point; proxies /api/ to backend:3101.
#
# Run from api/:       docker compose up --build
# Run from repo root:  docker compose -f api/docker-compose.yml up --build
#
# Production: Coolify is pointed at frontend:80. nginx proxies /api/ to backend:3101.
# Data: spec-doc workspace bind-mounted read-only at /data/spec-doc.

services:
  backend:
    build: .
    expose:
      - "3101"
    volumes:
      - ../spec-doc:/data/spec-doc:ro
    environment:
      SPEC_DOC_DIR: /data/spec-doc
      CHAIN_PROVIDER: ${CHAIN_PROVIDER:-claude}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:4201,http://localhost:4202}
      APP_ENV: ${APP_ENV:-production}
    healthcheck:
      test:
        - "CMD-SHELL"
        - >
          python -c "import urllib.request;
          urllib.request.urlopen('http://localhost:3101/health')"
          || exit 1
      interval: 10s
      timeout: 5s
      start_period: 30s
      retries: 5
    networks:
      - spec-doc-net

  frontend:
    build: ../web
    expose:
      - "80"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost/api/health || exit 1"]
      interval: 15s
      timeout: 5s
      start_period: 45s
      retries: 5
    networks:
      - spec-doc-net

networks:
  spec-doc-net:
    driver: bridge
```

**Notes on changes from old compose**:
- `api` service → renamed `backend`; `ports: 3101:3101` → `expose: ["3101"]`
- `PORT: "3101"` env var dropped — gunicorn hardcodes `--bind 0.0.0.0:3101`; `config.py` never reads `PORT`
- `APP_ENV` added — `create_app.py` enforces `APP_ENV=production` requires a real `CHAIN_PROVIDER`
- `start_period` on backend bumped from 15s → 30s — single-stage image starts faster but `--preload` initializes the AI adapter before forking, adding a few seconds
- `start_period` on frontend is 45s — frontend waits for backend to be healthy first (`service_healthy`), so nginx is already proxying before its own healthcheck fires

**Verify**:
```bash
python -c "
import yaml
with open('docker-compose.yml') as f:
    d = yaml.safe_load(f)
assert 'backend' in d['services'], 'backend service missing'
assert 'frontend' in d['services'], 'frontend service missing'
assert 'ports' not in d['services']['backend'], 'backend must not expose ports to host'
assert 'ports' not in d['services']['frontend'], 'frontend must not expose ports to host'
assert any(str(p) == '3101' for p in d['services']['backend'].get('expose', [])), 'backend expose 3101'
assert any(str(p) == '80' for p in d['services']['frontend'].get('expose', [])), 'frontend expose 80'
assert 'spec-doc-net' in d.get('networks', {}), 'bridge network missing'
print('compose OK')
"
```

---

### Step 3: Update `api/tests/test_docker.py`

**Action**: In-place rename and rewrite two functions that now fail against the new compose structure (`dockerCompose_defines_api_service` → `dockerCompose_defines_backend_service`; `dockerCompose_maps_port_3101` → `dockerCompose_backend_exposes_port_3101`). Add five new functions after the existing compose block. Preserve all fourteen Dockerfile-only functions unchanged.

**File**: `api/tests/test_docker.py`

**Replace** `dockerCompose_defines_api_service`:
```python
def dockerCompose_defines_backend_service():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    assert "backend" in data.get("services", {}), \
        "docker-compose.yml must define a 'backend' service (renamed from 'api' in Task 3 two-service split)"
```

**Replace** `dockerCompose_maps_port_3101`:
```python
def dockerCompose_backend_exposes_port_3101():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    expose = data["services"]["backend"].get("expose", [])
    assert any(str(p) == "3101" for p in expose), \
        ("backend service must expose port 3101 via 'expose:' (not 'ports:') — "
         "Coolify/Traefik handles external routing; host-level port binding is removed in Task 3")
```

**Append** after the last existing compose function:
```python
def dockerCompose_defines_frontend_service():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    assert "frontend" in data.get("services", {}), \
        "docker-compose.yml must define a 'frontend' service (nginx, added in Task 3 two-service split)"


def dockerCompose_frontend_exposes_port_80():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    expose = data["services"]["frontend"].get("expose", [])
    assert any(str(p) == "80" for p in expose), \
        "frontend service must expose port 80 via 'expose:' (Coolify domain target)"


def dockerCompose_frontend_depends_on_healthy_backend():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    deps = data["services"]["frontend"].get("depends_on", {})
    # depends_on may be a list (short form) or a dict (long form with condition).
    if isinstance(deps, list):
        assert "backend" in deps, \
            "frontend must declare depends_on: backend"
    else:
        assert "backend" in deps, \
            "frontend must declare depends_on: backend"
        condition = deps["backend"].get("condition", "")
        assert condition == "service_healthy", \
            ("frontend depends_on backend must use condition: service_healthy — "
             "nginx starts only after Flask passes its /health check")


def dockerCompose_services_share_bridge_network():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    top_networks = data.get("networks", {})
    assert top_networks, \
        "docker-compose.yml must declare at least one top-level network"

    def _nets(svc_name):
        raw = data["services"][svc_name].get("networks")
        if raw is None:
            return set()
        return set(raw) if isinstance(raw, list) else set(raw.keys())

    shared = _nets("backend") & _nets("frontend")
    assert shared, \
        ("backend and frontend services must share at least one network "
         "so nginx can resolve 'backend:3101' as the upstream host")


def dockerfile_has_no_angular_build_stage():
    text = (_ROOT / "Dockerfile").read_text()
    assert "frontend-builder" not in text, \
        ("api/Dockerfile must not contain a 'frontend-builder' multi-stage alias — "
         "Angular is now built inside the frontend container (Task 3 split)")
    assert "FROM node:" not in text, \
        ("api/Dockerfile must not contain a Node.js base image — "
         "Flask-only after the two-service split (Task 3)")
```

**Verify** (static check — no pytest run needed mid-step):
```bash
grep -c "def dockerCompose_defines_api_service" tests/test_docker.py     # expect: 0
grep -c "def dockerCompose_defines_backend_service" tests/test_docker.py  # expect: 1
grep -c "def dockerCompose_maps_port_3101" tests/test_docker.py           # expect: 0
grep -c "def dockerCompose_backend_exposes_port_3101" tests/test_docker.py # expect: 1
grep -c "def dockerCompose_defines_frontend_service" tests/test_docker.py  # expect: 1
grep -c "def dockerfile_has_no_angular_build_stage" tests/test_docker.py   # expect: 1
```

---

## 5. Tests

All tests live in `api/tests/test_docker.py`. The repo uses `pyproject.toml` with `python_functions = ["test_*", "*_*"]` — any function with an underscore in its name is collected by pytest; no `test_` prefix required.

The eight existing Dockerfile-scoped functions (`dockerfile_exists`, `dockerfile_baseImage_is_python311Slim`, etc.) remain unchanged and continue to pass — the simplified Dockerfile preserves all the invariants they check.

The two updated compose functions and five new compose functions (all shown above in Step 3) provide complete assertion bodies with no stubs. Reproduced here for explicitness:

```python
# --- Updated ---

def dockerCompose_defines_backend_service():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    assert "backend" in data.get("services", {}), \
        "docker-compose.yml must define a 'backend' service (renamed from 'api' in Task 3 two-service split)"


def dockerCompose_backend_exposes_port_3101():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    expose = data["services"]["backend"].get("expose", [])
    assert any(str(p) == "3101" for p in expose), \
        ("backend service must expose port 3101 via 'expose:' (not 'ports:') — "
         "Coolify/Traefik handles external routing; host-level port binding is removed in Task 3")


# --- New ---

def dockerCompose_defines_frontend_service():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    assert "frontend" in data.get("services", {}), \
        "docker-compose.yml must define a 'frontend' service (nginx, added in Task 3 two-service split)"


def dockerCompose_frontend_exposes_port_80():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    expose = data["services"]["frontend"].get("expose", [])
    assert any(str(p) == "80" for p in expose), \
        "frontend service must expose port 80 via 'expose:' (Coolify domain target)"


def dockerCompose_frontend_depends_on_healthy_backend():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    deps = data["services"]["frontend"].get("depends_on", {})
    if isinstance(deps, list):
        assert "backend" in deps, \
            "frontend must declare depends_on: backend"
    else:
        assert "backend" in deps, \
            "frontend must declare depends_on: backend"
        condition = deps["backend"].get("condition", "")
        assert condition == "service_healthy", \
            ("frontend depends_on backend must use condition: service_healthy — "
             "nginx starts only after Flask passes its /health check")


def dockerCompose_services_share_bridge_network():
    data = yaml.safe_load((_ROOT / "docker-compose.yml").read_text())
    top_networks = data.get("networks", {})
    assert top_networks, \
        "docker-compose.yml must declare at least one top-level network"

    def _nets(svc_name):
        raw = data["services"][svc_name].get("networks")
        if raw is None:
            return set()
        return set(raw) if isinstance(raw, list) else set(raw.keys())

    shared = _nets("backend") & _nets("frontend")
    assert shared, \
        ("backend and frontend services must share at least one network "
         "so nginx can resolve 'backend:3101' as the upstream host")


def dockerfile_has_no_angular_build_stage():
    text = (_ROOT / "Dockerfile").read_text()
    assert "frontend-builder" not in text, \
        ("api/Dockerfile must not contain a 'frontend-builder' multi-stage alias — "
         "Angular is now built inside the frontend container (Task 3 split)")
    assert "FROM node:" not in text, \
        ("api/Dockerfile must not contain a Node.js base image — "
         "Flask-only after the two-service split (Task 3)")
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end. Each boundary below maps to a numbered step above.

1. `build(dockerfile): strip Angular build stage from api/Dockerfile` — **after Step 1** — file: `api/Dockerfile`
   - Removes Stage 1 (`FROM node:20-alpine AS frontend-builder` block + `COPY --from=frontend-builder` line)
   - Updates `COPY` paths from repo-root context to `api/` context

2. `build(compose): split api/docker-compose.yml into backend + frontend services` — **after Step 2** — file: `api/docker-compose.yml`
   - Replaces single `api` service with `backend` + `frontend` services
   - Adds `spec-doc-net` bridge network; changes `ports:` to `expose:`

3. `test(docker): update assertions for two-service compose split` — **after Step 3 + tests pass** — file: `api/tests/test_docker.py`
   - Renames `dockerCompose_defines_api_service` → `dockerCompose_defines_backend_service`
   - Renames `dockerCompose_maps_port_3101` → `dockerCompose_backend_exposes_port_3101`
   - Adds five new assertion functions

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# From {WORKSPACE}/api/
make test
```

**Expected delta**: 624 → 629 passing. Zero pre-existing tests broken.

Breakdown: `api/tests/test_docker.py` grows from 14 to 19 collected functions (+5 net: 2 renamed in-place, 5 added). All other 610 tests are unaffected.

**Sanity-check the Dockerfile build independently** (optional, no Docker daemon required — just verifies the file is syntactically valid and has the right shape):
```bash
grep -E "^FROM " Dockerfile             # expect: exactly one line — FROM python:3.11-slim AS final
grep "COPY web\|from=frontend" Dockerfile   # expect: no output (Angular stage is gone)
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Step 1: `git revert <sha-of-commit-1>` — restores the two-stage Dockerfile
  - Step 2: `git revert <sha-of-commit-2>` — restores the single-service compose
  - Step 3: `git revert <sha-of-commit-3>` — restores the old test assertions

- **Per-branch**: if verification fails catastrophically after all three commits:
  ```bash
  git reset --hard <pre-task-sha>   # sha recorded during pre-flight git status
  ```
  or, if on a feature branch:
  ```bash
  git checkout master
  git branch -D <feature-branch>
  ```

- **Safety note**: `docker-compose.coolify.yml` was not touched; Coolify production continues to deploy from that file unaffected while this branch is under review.

---

## 9. Deviations Allowed

- **`web/Dockerfile` absent** → Task 2 is not complete. Do not invent a placeholder. Stop, mark `[REQUIRES APPROVAL]`, and ask before proceeding.
- **`../spec-doc` bind-mount resolves incorrectly** → if the spec-doc data directory sits at a different relative path on the deployment host, update the volume source in `docker-compose.yml` and note in the commit body. The container-side path (`/data/spec-doc`) and the `SPEC_DOC_DIR` value must remain unchanged.
- **`make test` baseline is not 624** → record the actual count before editing. Use that count as the baseline for delta calculation at Step 7. Do not assume 624.
- **Named-volume preference for Coolify** → the architecture doc describes `spec-doc-data` as a named volume for Coolify production. If the executor prefers to use a named volume in `docker-compose.yml` instead of a bind mount, that is allowed — but update the `dockerCompose_mounts_specDoc_readonly` assertion accordingly (remove the `:ro` check; add a named-volume check). Log the deviation in commit 2's body.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **Side-effect required** (push, schema change, `rm -rf`) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

Task 3 delivers the structural split — the compose file and the backend Dockerfile. It does not wire up Coolify, update the production compose, or change the Angular environment config. Those changes are intentionally deferred to keep each task verifiable before the next one builds on it.

- **`api/docker-compose.coolify.yml` update** — this file still uses a single `api` service pointing directly at port 3101 with Traefik labels; updating it to use the two-service topology (frontend:80 as Traefik target) is deferred to Task 5, after the split is verified live
- **`web/environment.ts` base URL change** — Angular currently calls `http://localhost:3101` directly; switching to the relative `/api` path (so nginx routes it in production) is Task 5's explicit scope
- **Removal of `web_serve_bp`** — the Flask catch-all blueprint stays registered until Task 5 removes it; leaving it in place preserves rollback safety while the compose split is being verified
- **`api/Makefile` docker-* targets** — `test_deploy_config.py` already tests these targets; updates to Makefile commands (e.g., adding `--build` flags, scoping to `backend` service only) belong to Task 4's CI restructure
- **`.dockerignore` for `api/`** — since the build context changes from repo-root to `api/`, a `api/.dockerignore` excluding `tests/`, `__pycache__/`, `.env`, and `docker-compose*.yml` would reduce image layer size; it has no correctness impact and is a low-priority follow-on

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale; Component Design → Backend Container and Compose Topology sections
- [Epic](./epic.md) — Task scope and dependency graph
- [Timeline](./timeline.md) — Update status to ✅ after Step 7 verification passes