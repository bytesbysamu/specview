Now I have everything I need. Writing the guide.

---

# Task 4: Two-service compose + api/Dockerfile simplification

## 1. Context

The project currently scatters Docker configuration across three files all living under `api/`: a local-dev compose, a Coolify production compose, and a multi-stage Dockerfile that bundles an Angular build into the Flask image. This task collapses everything: one canonical `docker-compose.yml` at the repo root with two services (`api` for Flask, `web` for nginx-served Angular), the two `api/`-level compose files are deleted, and `api/Dockerfile` drops its Node.js build stage to become a single-stage Flask image. The `web` service consumes the `web/Dockerfile` and `web/nginx/nginx.conf` produced by Task 2 — the frontend container is `nginx:alpine` serving the pre-built Angular dist and proxying `/api/*` to the `api` container. This is the humanize-me / speedback shape. Both services use `expose:` only; Coolify/Traefik handles ingress.

**Trade-offs considered:**
- **Keep multi-stage Dockerfile, just move compose to root** — rejected; the multi-stage build couples every Flask-only CI rebuild to a full npm install + ng build (~2–3 min penalty with no Python changes).
- **Keep three separate compose files (local, Coolify, CI)** — rejected; for a single-consumer tool with no staging environment, three sources of truth generate drift with zero benefit.
- **`web` service runs `ng serve` instead of nginx** — rejected; Angular's dev server is unsuitable for production. Task 2 already built the nginx-based `web/Dockerfile`; this task wires it in. Local integration testing works equally well against nginx because the `web` healthcheck proves the nginx→Flask path is live.
- **Single-stage Flask Dockerfile + two-service compose with nginx web** — preferred; Dockerfile shrinks by ~12 lines, the `web` service is production-grade from day one, and the Coolify compose path changes from `api/docker-compose.coolify.yml` to the repo-root `docker-compose.yml` (one-time Coolify setting update, gated below).

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From {WORKSPACE}/api/
git status
git diff HEAD -- Dockerfile docker-compose.yml docker-compose.coolify.yml tests/test_docker.py

# Confirm current compose files are where expected
ls api/docker-compose.yml api/docker-compose.coolify.yml api/Dockerfile

# Baseline test suite
cd api && python -m pytest --tb=short -q
# Record the passing count — expected: 624 passed, 1 skipped
```

**Coolify gate** (MUST check before Step 1 — replacing root compose):

1. Open Coolify → your spec-doc service → Settings → "Docker Compose Location".
2. If it shows `api/docker-compose.coolify.yml`: that file was already deleted by Task 1. Coolify's next deploy is already broken — update the path to `docker-compose.yml` (the repo-root file) before this task finishes, or block Task 1 from shipping until Coolify is reconfigured.
3. If it already shows `docker-compose.yml` or is blank (uses repo root): proceed immediately.

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: 624 / 625 passing (1 skipped).

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/docker-compose.yml` — **replaces** the existing root `docker-compose.yml`; two services (`api`, `web`) covering all production env vars

### To Modify (cite CODEBASE CONTEXT)
- `{WORKSPACE}/api/Dockerfile` — drop Stage 1 (`FROM node:20-alpine AS frontend-builder` block, ~12 lines) and the `COPY --from=frontend-builder` line in Stage 2; update file-header comment
- `{WORKSPACE}/api/tests/test_docker.py` — split `_ROOT` into `_API_ROOT` (points to `api/`) and `_REPO_ROOT` (points to repo root); update compose-test functions to use `_REPO_ROOT`; update `dockerCompose_mounts_specDoc_readonly` for named-volume shape; add `dockerCompose_defines_web_service` and Dockerfile regression guards

### To Leave Alone
- `{WORKSPACE}/.dockerignore` — created by Task 1; do not recreate or modify
- `{WORKSPACE}/web/Dockerfile` and `{WORKSPACE}/web/nginx/nginx.conf` — created by Task 2; the new compose references them as the `web` service build context
- `{WORKSPACE}/api/create_app.py` — `web_serve_bp` was already removed in Task 3; this task does not touch Flask source
- `{WORKSPACE}/api/requirements.txt` — no changes; gunicorn + flask dependencies are unaffected
- All `{WORKSPACE}/api/modules/` — no Docker concern; not touched
- `{WORKSPACE}/api/.github/`, `{WORKSPACE}/web/.github/`, `{WORKSPACE}/api/.dockerignore`, `{WORKSPACE}/api/docker-compose.coolify.yml` — all already deleted by Task 1; pre-flight will confirm

---

## 4. Implementation Steps

### Step 1: Replace root `docker-compose.yml` with the two-service nginx shape

**Action**: Replace the existing `{WORKSPACE}/docker-compose.yml` with a two-service definition: `api` (Flask, single-stage image, `python -c urllib.request` healthcheck on `/api/health`) and `web` (the nginx container built by `web/Dockerfile` from Task 2). Both services use `expose:` only — Coolify/Traefik is the only ingress. The `api` service supersedes both `api/docker-compose.yml` and `api/docker-compose.coolify.yml`. Persistent state lives in the named volume `spec-doc-data`, matching the existing root compose's volume name.

**File**: `{WORKSPACE}/docker-compose.yml` (replace)

**Pattern**:
```yaml
# Two-service deployment — humanize-me shape ported to spec-doc.
# Coolify points at the web service (port 80); web nginx proxies /api/* to api:3101.
#
# Local: docker compose up --build
# CI:    docker compose up -d --build  (see .github/workflows/deploy.yml docker-integration job)

services:

  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    expose:
      - "3101"
    volumes:
      - spec-doc-data:/data/spec-doc
    environment:
      SPEC_DOC_DIR: /data/spec-doc
      CHAIN_PROVIDER: ${CHAIN_PROVIDER:-claude}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:4201}
      APP_ENV: ${APP_ENV:-production}
      AUTH_SECRET: ${AUTH_SECRET:-}
      NEON_AUTH_JWKS_URI: ${NEON_AUTH_JWKS_URI:-}
      DATABASE_URL: ${DATABASE_URL:-}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY:-}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET:-}
      STRIPE_PRICE_ID_PRO: ${STRIPE_PRICE_ID_PRO:-}
      SENTRY_DSN: ${SENTRY_DSN:-}
    restart: unless-stopped
    healthcheck:
      test:
        - "CMD-SHELL"
        - >
          python -c "import urllib.request;
          urllib.request.urlopen('http://localhost:3101/api/health')"
          || exit 1
      interval: 10s
      timeout: 5s
      start_period: 30s
      retries: 5
    networks:
      - spec-doc-net

  web:
    build: ./web
    expose:
      - "80"
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost/api/health || exit 1"]
      interval: 15s
      timeout: 5s
      start_period: 45s
      retries: 5
    networks:
      - spec-doc-net

volumes:
  spec-doc-data:

networks:
  spec-doc-net:
    driver: bridge
```

**Notes on changes from the existing root compose**:
- `ports: "3101:3101"` → `expose: ["3101"]` (Traefik handles ingress; nothing should reach the host directly)
- Healthcheck switches from `curl` to `python -c urllib.request` (`python:3.11-slim` does not ship curl; brain dump #2)
- Healthcheck path `/health` → `/api/health` (matches Flask rename in Task 3)
- New `web` service builds from `./web` using the Dockerfile + nginx config Task 2 produced
- New `web.depends_on.api.condition: service_healthy` ensures nginx never proxies to a not-ready Flask
- `web` healthcheck `wget -qO- http://localhost/api/health` proves the full nginx→Flask path is live in-container
- Named volume `spec-doc-data` retained from the existing root compose; the broken `:.:/data/spec-doc:ro` shape that mounted the entire repo is replaced
- Both services join `spec-doc-net` so nginx can resolve `api:3101`

**Verify**:
```bash
cd {WORKSPACE}
docker compose config --quiet                       # parses YAML; exits 0 if valid
docker compose config | grep -E "^  (api|web):"     # must show both service headers
docker compose config | grep -c "ports:"            # expect: 0 (no host port mapping)
docker compose config | grep "/api/health"          # expect: appears in both healthchecks
```

---

### Step 2: Simplify `api/Dockerfile` to single-stage Flask

**Action**: Remove the entire `Stage 1: Angular build` block (lines 12–23 in the current file: `FROM node:20-alpine AS frontend-builder` through `RUN npx ng build`) and the `COPY --from=frontend-builder` line in Stage 2. Update the file-header comment to reflect the new single-stage reality. The `AS final` label on Stage 2 is no longer meaningful; drop it. All gunicorn flags, non-root user, EXPOSE, and COPY paths are unchanged.

**File**: `{WORKSPACE}/api/Dockerfile` (existing — modify)

**Pattern** (complete replacement):
```dockerfile
# Single-stage Flask image.
# Build context: REPO ROOT (so COPY api/... resolves correctly).
#   Local: docker compose up --build       (uses root docker-compose.yml)
#   CI:    docker compose up -d --build    (see .github/workflows/deploy.yml)
#
# Angular SPA is served by the web service (nginx:alpine, see web/Dockerfile and
# web/nginx/nginx.conf). nginx proxies /api/* to this container; no static
# files live in the Flask image after Task 3.

FROM python:3.11-slim

# Non-root user — defense against container escape.
RUN addgroup --system appgroup \
 && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install Python dependencies before copying source — better layer caching.
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask source.
COPY api/ ./

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
cd {WORKSPACE}
grep -c "FROM" api/Dockerfile   # must print 1 (single stage)
grep "frontend-builder" api/Dockerfile && echo FAIL || echo OK   # must print OK
docker build -f api/Dockerfile -t spec-doc:smoke-test . --quiet  # exits 0
```

---

### Step 3: Update `api/tests/test_docker.py`

**Action**: Split `_ROOT` into `_API_ROOT` (keeps its current value — `api/` — for Dockerfile assertions) and `_REPO_ROOT` (one level higher — the actual repo root — for compose assertions). Update all six compose-test functions to reference `_REPO_ROOT`. Add `dockerCompose_defines_web_service` test. The pytest config `python_functions = ["test_*", "*_*"]` (confirmed in `pyproject.toml`) will collect the new function automatically.

**File**: `{WORKSPACE}/api/tests/test_docker.py` (existing — modify)

Replace the `_ROOT` definition and all compose function references:

```python
# ── Path roots ──────────────────────────────────────────────────────────────
# _API_ROOT: api/ directory — Dockerfile lives here.
# _REPO_ROOT: repo root    — docker-compose.yml lives here.
# The comment "{WORKSPACE} root" on the old _ROOT was aspirational; the actual
# value was api/. This split makes both levels explicit.
_API_ROOT  = Path(__file__).parent.parent           # api/
_REPO_ROOT = Path(__file__).parent.parent.parent    # {WORKSPACE}/
```

Then update every `_ROOT` reference in the compose functions:

```python
def dockerCompose_exists():
    assert (_REPO_ROOT / "docker-compose.yml").is_file(), \
        "docker-compose.yml not found at workspace root"


def dockerCompose_is_valid_yaml():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    assert isinstance(data, dict), \
        "docker-compose.yml must parse as a YAML mapping"


def dockerCompose_defines_api_service():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    assert "api" in data.get("services", {}), \
        "docker-compose.yml must define an 'api' service"


def dockerCompose_defines_web_service():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    assert "web" in data.get("services", {}), \
        "docker-compose.yml must define a 'web' service for the Angular dev server"


def dockerCompose_mounts_specDocData_named_volume():
    """spec-doc-data named volume must be mounted at /data/spec-doc.

    Renamed from dockerCompose_mounts_specDoc_readonly: the named-volume shape
    is writable (Flask writes spec-doc projects), so :ro is removed. The named
    volume persists across image rebuilds — the previous bind mount required
    a sibling directory on the host that doesn't reliably exist.
    """
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    api_volumes = data["services"]["api"].get("volumes", [])
    assert any("spec-doc-data:/data/spec-doc" in str(v) for v in api_volumes), (
        "api service must mount the spec-doc-data named volume at /data/spec-doc"
    )
    top_volumes = data.get("volumes", {})
    assert "spec-doc-data" in top_volumes, (
        "top-level 'volumes:' must declare spec-doc-data so it persists across rebuilds"
    )


def dockerCompose_sets_specDocDir_to_containerPath():
    text = (_REPO_ROOT / "docker-compose.yml").read_text()
    assert "SPEC_DOC_DIR" in text and "/data/spec-doc" in text, \
        "SPEC_DOC_DIR must be set to /data/spec-doc so config.py resolves to the mounted volume"


def dockerCompose_api_exposes_port_3101():
    """Renamed from dockerCompose_maps_port_3101: services use expose:, not ports:.

    Coolify/Traefik handles host ingress; nothing should bind to the host directly.
    """
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    api = data["services"]["api"]
    assert "ports" not in api, \
        "api service must not declare 'ports:' — Coolify/Traefik handles ingress"
    expose = api.get("expose", [])
    assert any(str(p) == "3101" for p in expose), \
        "api service must expose port 3101 via expose: (not ports:)"


def dockerCompose_web_exposes_port_80():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    web = data["services"]["web"]
    assert "ports" not in web, \
        "web service must not declare 'ports:' — Coolify/Traefik handles ingress"
    expose = web.get("expose", [])
    assert any(str(p) == "80" for p in expose), \
        "web service must expose port 80 (Coolify domain target)"


def dockerCompose_web_depends_on_healthy_api():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    deps = data["services"]["web"].get("depends_on", {})
    assert isinstance(deps, dict) and "api" in deps, \
        "web must declare depends_on.api with a condition"
    assert deps["api"].get("condition") == "service_healthy", \
        "web must wait for api to be service_healthy — nginx must not proxy to a not-ready Flask"


def dockerCompose_services_share_bridge_network():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    assert data.get("networks"), "top-level 'networks:' must declare at least one network"

    def _nets(svc):
        raw = data["services"][svc].get("networks")
        if raw is None:
            return set()
        return set(raw) if isinstance(raw, list) else set(raw.keys())

    shared = _nets("api") & _nets("web")
    assert shared, (
        "api and web must share at least one network so nginx can resolve api:3101 as the upstream"
    )
```

All eight Dockerfile functions (`dockerfile_exists`, `dockerfile_baseImage_is_python311Slim`, etc.) change `_ROOT` → `_API_ROOT` in their bodies. The Dockerfile is still at `api/Dockerfile`, so `_API_ROOT / "Dockerfile"` resolves correctly.

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest tests/test_docker.py -v
```
Expected: all `test_docker.py` functions pass. New compose-shape assertions: `dockerCompose_defines_web_service`, `dockerCompose_mounts_specDocData_named_volume` (replaces the `:ro` assertion), `dockerCompose_api_exposes_port_3101` (replaces the ports-mapping assertion), `dockerCompose_web_exposes_port_80`, `dockerCompose_web_depends_on_healthy_api`, `dockerCompose_services_share_bridge_network`. Plus Dockerfile regression guards: `dockerfile_has_no_frontend_builder_stage`, `dockerfile_has_no_node_base_image`, `dockerCompose_api_healthcheck_uses_python_not_curl`.

---

### Step 4: Delete `api/docker-compose.yml`

**Action**: Remove the file. The root `docker-compose.yml` supersedes it. (`api/docker-compose.coolify.yml` was already removed by Task 1.)

**File**: `{WORKSPACE}/api/docker-compose.yml` (delete)

```bash
git rm api/docker-compose.yml
```

**Verify**:
```bash
ls api/docker-compose*.yml 2>&1   # must print "No such file or directory"
cd {WORKSPACE}/api && python -m pytest tests/test_docker.py -v   # must still pass
```

---

## 5. Tests

All assertions below belong in `{WORKSPACE}/api/tests/test_docker.py`. The repo uses `python_functions = ["test_*", "*_*"]` in `pyproject.toml`; functions with underscores are collected automatically — no `test_` prefix required, consistent with the file's existing style.

```python
# ── New function (add after dockerCompose_defines_api_service) ──────────────

def dockerCompose_defines_web_service():
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    assert "web" in data.get("services", {}), \
        "docker-compose.yml must define a 'web' service for the Angular dev server"


# ── Regression guards for simplification (add after dockerfile_exposes_port_3101) ──

def dockerfile_has_no_frontend_builder_stage():
    text = (_API_ROOT / "Dockerfile").read_text()
    assert "frontend-builder" not in text, (
        "api/Dockerfile must not contain a Node.js build stage — "
        "Angular is served by the web service; bundling in Dockerfile couples "
        "Flask rebuilds to npm install + ng build (~3 min penalty for Python-only changes)"
    )


def dockerfile_has_no_node_base_image():
    text = (_API_ROOT / "Dockerfile").read_text()
    assert "FROM node:" not in text, \
        "api/Dockerfile must be a single-stage Python image — no Node.js base image"


def dockerCompose_api_healthcheck_uses_python_not_curl():
    """api healthcheck must use python -c urllib.request — python:3.11-slim has no curl."""
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    api_hc = data["services"]["api"].get("healthcheck", {})
    test_cmd = " ".join(str(x) for x in api_hc.get("test", []))
    assert "curl" not in test_cmd, (
        "api healthcheck must not use curl — python:3.11-slim does not include it"
    )
    assert "urllib.request" in test_cmd, \
        "api healthcheck must probe via python -c urllib.request"
    assert "/api/health" in test_cmd, \
        "api healthcheck must probe /api/health (Task 3 renamed the route)"


def dockerCompose_web_healthcheck_probes_via_nginx():
    """web healthcheck must hit /api/health on localhost — proves the nginx→Flask path."""
    data = yaml.safe_load((_REPO_ROOT / "docker-compose.yml").read_text())
    web_hc = data["services"]["web"].get("healthcheck", {})
    test_cmd = " ".join(str(x) for x in web_hc.get("test", []))
    assert "/api/health" in test_cmd, (
        "web healthcheck must probe /api/health through nginx — "
        "this validates the upstream proxy is live, not just that nginx started"
    )
```

**Full test run targeting the docker module only**:

```bash
cd {WORKSPACE}/api
python -m pytest tests/test_docker.py -v
# Expected: 18 passed (14 original + 4 new), 0 failed
```

> Note: the four new functions bring the per-file count to 18. Three of those four (`dockerfile_has_no_frontend_builder_stage`, `dockerfile_has_no_node_base_image`, `dockerCompose_api_healthcheck_uses_python_not_curl`) are regression guards that lock in the simplification. They will fail if anyone re-introduces a multi-stage build or curl healthcheck.

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task. Each boundary below corresponds to exactly one step above.

1. `feat(docker): two-service compose — api (Flask) + web (nginx)` — after **Step 1** — `docker-compose.yml`: replace existing root compose; expose: only; api healthcheck on /api/health via urllib; web healthcheck via nginx; named volume + bridge network
2. `refactor(docker): simplify api/Dockerfile to single-stage Flask` — after **Step 2** — `api/Dockerfile`: drop node:20-alpine build stage and COPY --from=frontend-builder; -12 lines
3. `test(docker): split _ROOT; assert two-service compose shape and Dockerfile regressions` — after **Step 3** — `api/tests/test_docker.py`: split path roots; add web service / expose / named-volume / depends_on / shared-network / healthcheck assertions; rename `:ro` and `ports:` tests to match new shape
4. `chore(docker): delete api/docker-compose.yml superseded by root compose` — after **Step 4** — `git rm api/docker-compose.yml`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api
python -m pytest --tb=short -q
```

**Expected delta**: 624 → ~632 passing — net positive after renames and additions. Zero pre-existing tests broken outside the deliberate renames in `test_docker.py` (`dockerCompose_mounts_specDoc_readonly` → `dockerCompose_mounts_specDocData_named_volume`; `dockerCompose_maps_port_3101` → `dockerCompose_api_exposes_port_3101`).

Secondary smoke check (requires Docker daemon):
```bash
cd {WORKSPACE}
docker compose config --quiet          # YAML valid
docker build -f api/Dockerfile -t spec-doc:smoke . --quiet
docker run --rm spec-doc:smoke python -c "import flask, gunicorn; print('OK')"
# Expected output: OK
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # creates a new revert commit; does not rewrite history
  ```
- **Coolify rollback specifically**: if Coolify still reads `api/docker-compose.coolify.yml`, both Task 1 (which deleted that file) and this task need to be reverted, or the Coolify Compose Path needs to be updated to a still-existing file. The cleanest fix is to update Coolify's Compose Path forward to `docker-compose.yml` rather than reverting code.
- **Per-branch (catastrophic)**: if verification fails completely:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — discards all task commits
  ```
  Confirm the pre-task SHA with `git log --oneline -10` before running.

---

## 9. Deviations Allowed

- **Coolify Compose Path is already `docker-compose.yml`** → skip the gate-check update; proceed directly to Step 4.
- **`web/Dockerfile` or `web/nginx/nginx.conf` absent** → Task 2 has not landed. STOP — the `web` service `build: ./web` will fail. Land Task 2 first.
- **`/api/health` route returns 404 in the api container** → Task 3 has not landed. STOP — both healthchecks will fail forever. Land Task 3 first.
- **Angular dist path differs** → already verified by Task 2; if `web/Dockerfile` builds successfully then this task does not need to know the path.
- **`docker build` smoke test fails with "no space left on device"** → infrastructure issue; not a code defect. Clear Docker cache (`docker system prune`) and re-run.
- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it, do not invent.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **Side-effect required** (push, Coolify API call, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

This task is a structural cleanup: move compose to root, drop the Node.js Dockerfile stage, align tests. It does not address how the Angular SPA reaches end-users in production, nor does it touch CI/CD pipelines. An executor should resist all of the following until they are scheduled as their own tasks.

- **CI/CD restructure** — Task 5 owns the workflow rewrite. The new compose makes `docker compose up -d --build` the right CI invocation; Task 5 wires it in.
- **Root `.dockerignore` content audit** — Task 1 created the file. If the build-context size is still bloated after this task ships (verify with `docker build --progress=plain`), audit and trim is a follow-up.
- **Local dev compose for `make dev`** — `make dev-api` runs `python3 app.py` directly without compose. Adding a dev-only override (`docker-compose.override.yml`) is over-engineering for a single-developer tool.
- **TLS / HTTPS termination in nginx** — Coolify/Traefik handles TLS at the edge; the `web` container stays HTTP-only on port 80.
- **`proxy.conf.json` updates** — Task 3 created and wired up `proxy.conf.json`; this task does not touch it.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)