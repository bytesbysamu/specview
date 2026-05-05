# 🏗️ Solution Architecture: Aligning spec-doc Deployment

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

spec-doc currently diverges from every other project in the Coolify portfolio by baking the Angular build into the Flask image and serving static files from Python. The split pattern — an nginx frontend container owning port 80, a Flask backend container on an internal port — is already proven across humanize-me and speedback. The architecture here reuses that proven shape rather than inventing a project-specific one.

The central insight is that the repo is already structurally split (`web/` + `api/`); the runtime was just never aligned to match. Adding `web/Dockerfile` and `web/nginx/nginx.conf` makes the build boundary explicit and gives nginx responsibility for the three things it does better than Flask: SPA client-side routing fallback, SSE-safe API proxying with `proxy_buffering off`, and static asset cache headers. Flask is then free to be a pure API process.

The CI pipeline follows the same restructuring logic: the existing `build-frontend` job becomes the `frontend-ci` job running inside `web/`; it already existed in isolation, so parallel execution with `backend-ci` is a natural promotion rather than a redesign. A new `docker-integration` job provides end-to-end smoke confidence before any deploy webhook fires.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Port proven patterns, don't invent | `web/Dockerfile` shape is ported directly from humanize-me/speedback; no novel abstractions |
| Single entry point | `frontend:80` is the Coolify domain target; Traefik sees one service, one port — same as every sibling project |
| nginx owns HTTP concerns | SSE safety, SPA routing, and asset caching live in `web/nginx/nginx.conf`; Flask has no HTTP middleware responsibility after the split |
| ELA Pattern #4 (Async 202) | Unchanged — long AI operations already return 202; the split does not affect backend job patterns |
| ELA Pattern #5 (Not-Yet-Built) | No separate nginx reverse-proxy tier; spec-doc has one SPA and one backend — the frontend container is the sufficient entry point |
| Rollback safety | `web_serve_bp` is removed only after the split compose is verified live in Coolify (Task 5 is intentionally last) |

---

## System Boundaries

### What This System Includes

- `frontend` container — nginx serving Angular dist, proxying `/api/` to the backend service
- `backend` container — Flask-only image, no Node.js stage, no static file responsibility
- `web/Dockerfile` — multi-stage: node builder → nginx:alpine (ported from humanize-me)
- `web/nginx/nginx.conf` — SPA fallback + `/api/` proxy block with SSE headers (ported from speedback)
- `docker-compose.yml` — two services with `expose:` only, shared bridge network, named data volume
- `/health` Flask route — prerequisite for backend Docker healthcheck
- Trimmed `.env.example` — reflects only env vars referenced in spec-doc code
- Restructured `deploy.yml` — parallel `frontend-ci` / `backend-ci` → `docker-integration` → `deploy`
- Relative `/api` base URL in `environment.ts` — the single Angular source change enabling nginx routing
- Deletion of `web_serve_bp` — Flask blueprint removed once nginx owns static serving

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Separate nginx reverse-proxy container (wardrobai pattern) | Only one SPA consumer exists; the frontend container is already the entry point — a second proxy tier has no second consumer to justify it (ELA Pattern #5) |
| `docker-compose.test.yml` | The main compose file handles smoke tests in `docker-integration`; a parallel test file doubles maintenance surface with no benefit |
| CI artifact upload for Angular build | The frontend image builds inside its own Docker stage; no downstream job consumes a standalone Angular artifact |
| Docusaurus / docs service | spec-doc has no documentation site |

---

## Component Design

### Frontend Container (`web/`)
**Purpose**: Owns the HTTP entry point; serves the Angular SPA; proxies all `/api/` traffic to the backend with SSE safety.

**Key Parts**:
- `web/Dockerfile` — two stages: node builder compiles Angular; nginx:alpine copies dist and nginx config. Consumers: `docker-compose.yml` `frontend` service, `frontend-ci` CI job.
- `web/nginx/nginx.conf` — three location blocks: SPA `try_files` fallback (client-side routing), `/api/` proxy with `proxy_buffering off` and 900s timeouts (SSE and long AI calls), static asset `Cache-Control: immutable` (Angular hash-named bundles). Consumer: `web/Dockerfile` COPY.

**Patterns**: Ported from humanize-me (Next.js variant) and speedback (Angular variant). `set $backend` variable trick defers DNS resolution so nginx starts cleanly before the backend container is healthy.

---

### Backend Container (`api/`)
**Purpose**: Pure Flask API process; no static file serving; no Node.js build stage.

**Key Parts**:
- `api/Dockerfile` — simplified to a single `python:3.11-slim` stage; gunicorn `gthread` worker class preserves daemon thread coexistence for `generate-task` and `bootstrap` async jobs. Consumer: `docker-compose.yml` `backend` service.
- `/health` route — minimal Flask route returning 200; no business logic; can live in `create_app.py` or an existing utility blueprint. Consumers: `docker-compose.yml` backend healthcheck, `docker-integration` CI smoke test.

**Patterns**: gunicorn config (workers=2, threads=4, timeout=900) ported from Trendfy reference; daemon thread pattern unchanged from existing `task_gen` and `ai` modules.

---

### Compose Topology (`docker-compose.yml`)
**Purpose**: Defines the two-service runtime graph; eliminates `ports:` exposure so Coolify/Traefik is the only ingress.

**Key Parts**:
- `frontend` service — builds from `./web`, exposes 80, healthcheck hits `/api/health` through nginx. Consumer: Coolify domain assignment.
- `backend` service — builds from repo root with `api/Dockerfile`, exposes 3101 on bridge network only, mounts `spec-doc-data` named volume. Consumer: `frontend` nginx upstream `backend:3101`.
- Named volume `spec-doc-data` — mounted at `/data/spec-doc`; `SPEC_DOC_DIR` env var points here. Consumer: Flask `config.py` `SPEC_DOC_DIR`.

**Patterns**: `expose:` not `ports:` is the pattern across humanize-me and speedback; Coolify routes by domain to whichever service it's pointed at — always `frontend:80` after this change.

---

### CI Pipeline (`.github/workflows/deploy.yml`)
**Purpose**: Validates frontend and backend independently in parallel; proves the two containers start and communicate before any deploy fires.

**Key Parts**:
- `frontend-ci` — installs deps and runs `ng build --configuration production` in `web/`; catches Angular compile errors without waiting for backend tests. Consumer: `docker-integration` (gates on this).
- `backend-ci` — runs `make lint`, `make test`, `make check-dtos` in `api/`; unchanged scope from the current `test` job. Consumer: `docker-integration` (gates on this).
- `docker-integration` — runs `docker compose up -d`, waits for `frontend:80`, GETs `/` and `/api/health`, tears down. Proves the full request path: Coolify → nginx → Flask. Consumer: `deploy` job.
- `deploy` — fires Coolify webhook; gates on all three preceding jobs; master-only. Consumer: Coolify.

**Patterns**: Directly ports the humanize-me four-job structure; parallel CI is a speed win with no added risk because frontend and backend test suites share no state.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend serve | nginx:alpine | Battle-tested across humanize-me and speedback; handles SSE buffering, SPA routing, and asset caching with config rather than code |
| Frontend build | node:20-alpine | Matches the node version used in existing CI; alpine keeps the image small; only a build stage, not a runtime dependency |
| Backend | python:3.11-slim + gunicorn gthread | Unchanged — gthread is required for daemon thread coexistence with async job patterns |
| Container orchestration | Docker Compose v2, `expose:` only | Matches every sibling Coolify project; no ports exposed to host, Traefik routes by domain |
| CI | GitHub Actions, single `deploy.yml` | Matches humanize-me structure; no separate workflow files needed at spec-doc's scale |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Frontend container is the Coolify entry point, not a separate nginx proxy tier | spec-doc has exactly one SPA and one backend — no second consumer justifies a dedicated proxy container (wardrobai has landing, app, docs, and ai-models; spec-doc has none of those) | If a second frontend is ever added, the topology must revisit whether a shared proxy tier is warranted |
| `web_serve_bp` removed only after split is live (Task 5 last) | Preserves rollback safety: if the compose split fails in Coolify, Flask can still serve the Angular dist through the old route while the issue is diagnosed | Leaves dead code in Flask for the duration of Tasks 3–4; acceptable because the code is small and does not interfere |
| `proxy_buffering off` in nginx (not a Flask concern) | SSE streams break silently with nginx buffering enabled; centralizing this in nginx config means Flask route handlers need no special SSE headers or response shaping | nginx config is slightly more complex; acceptable because config is explicit and version-controlled |
| Angular base URL becomes relative `/api` | Removes the hardcoded `localhost:3101` that only worked in dev; nginx routes `/api/` in prod, `proxy.conf.json` routes it in Angular dev server — same relative path works in both environments | Any environment that bypasses nginx entirely (direct Flask access) would break API calls; that access pattern is intentionally removed by the split |
| `/health` route added to Flask, not inferred from an existing route | A dedicated route is explicit, stable, and has no side effects; using an existing route (e.g. `GET /api/context`) as a healthcheck would couple health status to business logic availability | One extra route in Flask; negligible cost |
| Healthcheck on `frontend` container hits `/api/health` through nginx | Proves the proxy path is live, not just that nginx started; catches misconfigured upstream blocks | If the backend is slow to start, the frontend healthcheck fails until both are ready — `depends_on` + `start_period` mitigates this |

---

## Execution Flow

```
Task 1 (health route + env audit) ──┐
                                    ├──→ Task 3 (compose split + api/Dockerfile simplify) ──→ Task 5 (env.ts + delete web_serve_bp)
Task 2 (web/Dockerfile + nginx) ────┘
                                    │
                                    └──→ Task 4 (CI restructure, parallel with T3)
```

Tasks 1 and 2 are independently parallelisable. Task 3 requires both. Task 4 requires Task 2 (frontend Dockerfile must exist for CI to reference). Task 5 gates on Task 3 being verified live.

---

## Open Questions

- **Env var audit scope** — which of `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`, `NEON_AUTH_JWKS_URI`, `DATABASE_URL`, `SENTRY_DSN` are actually imported in `api/` code vs copied speculatively from humanize-me? Implementation guide for Task 1 must grep each var against the Flask codebase and remove unused ones from `.env.example`. Re-decision trigger: if any var is wired at a later date, it is added back to `.env.example` then.

- **Angular dist output path** — `web/Dockerfile` must COPY from the exact `ng build` output directory. Angular 17 outputs to `dist/<project-name>/browser` by default, but the actual project name in `angular.json` must be confirmed before the Dockerfile is written. Implementation guide for Task 2 must read `web/angular.json` and state the confirmed path.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview