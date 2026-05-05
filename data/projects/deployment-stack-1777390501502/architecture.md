# 🏗️ Solution Architecture: Deployment Stack

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

spec-doc currently ships as one container that bakes the Angular dist into the Flask image and serves static files via a Python catch-all blueprint. The end state is the same shape humanize-me and speedback already run in production: an `nginx:alpine` frontend container that owns the Coolify entry point and proxies `/api/*` to an internal Flask container, with both services living in one canonical `docker-compose.yml` at the repo root.

The central structural decision is that the repo is already split (`api/` + `web/`); only the runtime needs to follow. The Angular SPA gets its own multi-stage Dockerfile (`web/Dockerfile`: `node:20-alpine` builder → `nginx:alpine` runtime), and `api/Dockerfile` collapses to a single `python:3.11-slim` stage with no Node.js anywhere. Flask gains a single `/api/` prefix on the one route that lacks it (`/health`), so the entire backend route map partitions cleanly: anything under `/api/*` is Flask, anything else is nginx.

CI follows the same restructuring: parallel `frontend-ci` and `backend-ci` jobs replace the current sequential chain, and a `docker-integration` job brings up the full compose stack on master to prove the nginx→Flask path end-to-end before the Coolify webhook fires.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Port proven patterns | `web/Dockerfile` and the nginx config shape are ported directly from humanize-me; no novel abstractions |
| One canonical file per concern | One `docker-compose.yml` at repo root, one `.dockerignore` at repo root, one `.github/workflows/deploy.yml` |
| nginx owns HTTP concerns | SSE buffering, SPA routing, and asset cache headers live in `web/nginx/nginx.conf`; Flask is route handlers only |
| Single Coolify entry point | Coolify points at `web:80`; Traefik routes by domain; no `ports:` mapping anywhere |
| No premature abstractions | No reverse-proxy tier, no dev-only compose override, no shared base image — one consumer each |
| Rollback safety | Each task is one `git revert` away from the prior state; compose split lands before the Flask static-file fallback is removed |
| Hard-fail CI | No `continue-on-error: true`; the smoke test exits non-zero on any unexpected response |

---

## System Boundaries

### What This System Includes

- `web` container — `nginx:alpine` serving Angular dist, proxying `/api/*` to the backend with SSE-safe headers
- `api` container — single-stage `python:3.11-slim` running gunicorn `gthread`; no static file responsibility
- `web/Dockerfile` — multi-stage: node builder → nginx runtime (build context = repo root)
- `web/nginx/nginx.conf` — SPA fallback, `/api/` proxy with deferred DNS, static asset cache headers
- `api/Dockerfile` — Flask-only; no Node stage; no `web_serve_bp` COPY
- `docker-compose.yml` (root) — two services with `expose:` only, shared bridge network, named `spec-doc-data` volume
- `.dockerignore` (root) — excludes `web/node_modules`, `.git/`, test artifacts, secrets
- `/api/health` Flask route — replaces the bare `/health` route for the Docker healthcheck
- Trimmed `.env` plumbing in compose — Stripe / Auth / DB / Sentry vars all named `STRIPE_PRICE_ID_PRO` (canonical)
- Restructured `deploy.yml` — parallel `frontend-ci` / `backend-ci` → `docker-integration` (master only) → `deploy`
- Relative `/api` base URL in `web/src/environments/environment.ts`
- `proxy.conf.json` at repo root — forwards `/api/*` to Flask in `ng serve` so dev and prod resolve identically

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Separate nginx reverse-proxy tier (wardrobai pattern) | Only one SPA consumer exists; the frontend container is the entry point — a second proxy tier has no second consumer |
| `docker-compose.test.yml` | The main compose file handles smoke tests in `docker-integration`; a parallel test file doubles maintenance with no benefit |
| `docker-compose.override.yml` for local dev | `make dev-api` runs `python3 app.py` directly; compose for dev is over-engineering |
| CI artifact upload for the Angular dist | The frontend image builds inside its own Docker stage; no downstream job consumes a standalone artifact |
| TLS / HTTPS termination in nginx | Coolify/Traefik terminates TLS upstream; frontend container stays HTTP-only on port 80 |
| `environment.prod.ts` | Nothing currently varies between dev and prod that isn't a runtime env var |
| Redis, Postgres, message broker | spec-doc is in-process state with a SQLite backing store; no second service needed |

---

## Component Design

### Frontend Container (`web/`)

**Purpose**: Owns the HTTP entry point; serves the Angular SPA; proxies `/api/*` to Flask with SSE safety.

**Key Parts**:
- `web/Dockerfile` — two stages: `node:20-alpine` builds Angular (`npx ng build --configuration production` → `dist/spec-doc/browser`); `nginx:alpine` copies the dist and the nginx config. Build context = `web/` directory (not repo root) so `COPY package*.json` and `COPY .` work as written. Consumers: `docker-compose.yml` `web` service, `frontend-ci` CI job.
- `web/nginx/nginx.conf` — three location blocks:
  - `^~ /api/` proxy with `proxy_buffering off` and `proxy_read_timeout 900s` (SSE safety, matches gunicorn `--timeout 900`)
  - `~* \.(js|css|woff2|…)$` static asset cache with `Cache-Control: public, immutable`
  - `/` SPA fallback via `try_files $uri $uri/ /index.html`
- `set $upstream http://api:3101; proxy_pass $upstream;` + `resolver 127.0.0.11 valid=30s` — defers DNS so nginx starts cleanly before the `api` container is healthy.

**Patterns**: humanize-me Angular variant. The deferred-DNS pattern is the standard Docker-embedded-DNS technique.

---

### Backend Container (`api/`)

**Purpose**: Pure Flask API process; no static file serving; no Node.js build stage.

**Key Parts**:
- `api/Dockerfile` — single `FROM python:3.11-slim`. Non-root `appuser`; `pip install -r requirements.txt`; `COPY api/`; gunicorn CMD with `--worker-class gthread --workers 2 --threads 4 --timeout 900 --preload`. Consumer: `docker-compose.yml` `api` service.
- `/api/health` route — minimal Flask route returning `{"status": "ok"}` and HTTP 200. Lives inline in `create_app.py` at the same line that previously declared `/health` (the route is renamed, not moved). Consumers: `api` container healthcheck, `docker-integration` CI smoke test.

**Patterns**: gunicorn config (workers=2, threads=4, timeout=900) preserved from existing Dockerfile; daemon thread pattern unchanged for `task_gen` and `ai` async jobs.

---

### Compose Topology (`docker-compose.yml`)

**Purpose**: Defines the two-service runtime graph; eliminates `ports:` exposure so Coolify/Traefik is the only ingress.

**Key Parts**:
- `web` service — `build: { context: ., dockerfile: web/Dockerfile }`, `expose: ["80"]`, healthcheck `wget -qO- http://localhost/api/health`. Consumer: Coolify domain assignment.
- `api` service — `build: { context: ., dockerfile: api/Dockerfile }`, `expose: ["3101"]`, named volume `spec-doc-data:/data/spec-doc`, healthcheck `python -c "import urllib.request; urllib.request.urlopen('http://localhost:3101/api/health')"`. Consumer: `web` nginx upstream `api:3101`.
- Named volume `spec-doc-data` — mounted at `/data/spec-doc`; `SPEC_DOC_DIR` env var points here. Persists across image rebuilds.
- `web.depends_on.api.condition: service_healthy` — nginx starts only after Flask passes `/api/health`.

**Patterns**: `expose:` not `ports:` matches every sibling Coolify project; Coolify routes by domain to `web:80`.

**Healthcheck choice**: Flask container uses `python -c urllib.request` because `python:3.11-slim` does not ship `curl`. Frontend container uses `wget` because `nginx:alpine` includes BusyBox wget.

---

### CI Pipeline (`.github/workflows/deploy.yml`)

**Purpose**: Validates frontend and backend in parallel; proves the two containers communicate before any deploy fires.

**Key Parts**:
- `frontend-ci` — installs deps and runs `ng build --configuration production` in `web/`. No artifact upload — the frontend image rebuilds inside its own Docker stage in `docker-integration`. Runs on every push and PR.
- `backend-ci` — `make lint`, `make test`, `make check-dtos` in `api/`. Runs on every push and PR.
- `docker-integration` — `if: github.ref == 'refs/heads/master'`. Runs `docker compose up -d --build`, waits for the `web` container to be healthy, then runs `docker compose exec -T web wget -qO- http://localhost/api/health` to prove the full nginx→Flask path. Tears down on `always()`. Hard-fails on any non-200.
- `deploy` — `if: github.ref == 'refs/heads/master'`. Fires the Coolify webhook. Gates on `docker-integration`.

**Patterns**: humanize-me four-job structure. Parallel CI is a speed win because the frontend and backend test surfaces share no state.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend serve | nginx:alpine | Battle-tested across humanize-me and speedback; handles SSE buffering, SPA routing, and asset caching with config rather than code |
| Frontend build | node:20-alpine | Matches the version in CI and the existing `api/Dockerfile`; only a build stage, never a runtime dependency |
| Backend | python:3.11-slim + gunicorn gthread | Unchanged; `gthread` supports daemon thread async jobs; pinned by `dockerfile_baseImage_is_python311Slim` structural test |
| Container orchestration | Docker Compose v2, `expose:` only | Matches every sibling Coolify project; no host port binding; Traefik routes by domain |
| CI | GitHub Actions, single root `deploy.yml` | One workflow file at the only location GitHub reads; no `api/.github/` or `web/.github/` |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Frontend container is the Coolify entry point | One SPA, one backend; no second consumer justifies a third proxy container | If a second frontend ships, revisit whether a shared proxy tier is warranted |
| Rename Flask `/health` → `/api/health` | All Flask routes under `/api/*` partitions cleanly with nginx; no special-case routes | One bare-path route was a special case in CORS/test fixtures; sweep is mechanical but touches eight test files |
| `web_serve_bp` removed in the same task as the rename | nginx owns static serving once compose ships; the blueprint shadows `/<path:path>` and is dead weight | Leaves the blueprint live until Task 3 runs; acceptable because the catch-all is conditional on `web/` existing in the image (which is removed in Task 4) |
| `proxy_buffering off` in nginx | SSE streams break silently with buffering enabled; centralising this in nginx config keeps Flask handlers unaware | nginx config is slightly more complex; acceptable because it is explicit and version-controlled |
| Angular base URL becomes relative `/api` | Removes `localhost:3101` hardcoding; nginx routes `/api/` in prod, `proxy.conf.json` routes it in dev — same path in both | Any environment that bypasses nginx (direct Flask access on a host port) breaks API calls; that access pattern is intentionally removed |
| `python -c urllib.request` healthcheck | `python:3.11-slim` does not ship `curl`; installing curl adds image weight for a one-call use case | Slightly more verbose YAML than a one-liner curl |
| `STRIPE_PRICE_ID_PRO` is canonical | Already used in the billing module and all current compose files; do not invent a new name | None |
| Single root `.dockerignore` | Build context is repo root; Docker only honours the file at the build context root | None |
| `expose:` only, no `ports:` | Coolify/Traefik handles ingress; matches sibling projects | Local dev cannot `curl http://localhost:3101` directly — must use `docker compose exec` or run `make dev-api` outside compose. Acceptable: dev does not use compose |
| Architecture file ships before any task executes | Tasks reference this doc for design context; an empty file would force decisions to live inside task bodies and drift | None |

---

## Execution Flow

```
Task 1 (cleanup) ──────────────┐
                               │
Task 2 (web/Dockerfile+nginx) ─┤
                               ├─→ Task 4 (compose + api/Dockerfile simplify) ──→ done
Task 3 (Flask /api/ prefix) ───┘                                                      │
                                                                                      │
                              Task 5 (workflow rewrite) ─────────────────────────────┘
```

- Tasks 1, 2, 3 are independent and can run in parallel.
- Task 4 requires Task 2 (`web/Dockerfile` referenced in compose) and Task 3 (`/api/health` route exists; `web_serve_bp` removed).
- Task 5 requires Task 3 (smoke test hits `/api/health`) and Task 4 (smoke test exec's into the `web` service). Task 5 is the last to ship.

---

## Open Questions (resolved during execution)

- **Coolify's active `Compose Path` setting** — gates Task 4. If Coolify currently reads `api/docker-compose.coolify.yml`, that path must be updated in the Coolify dashboard to repo-root `docker-compose.yml` before Task 4 deletes the old file. Operator action, not code.
- **External consumers of bare `/health`** — gates Task 3. If any uptime monitor or Coolify probe hits `/health` directly (not via nginx), they must be updated to `/api/health` or the route must be aliased temporarily. Confirm before merging Task 3.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
