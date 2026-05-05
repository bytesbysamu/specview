# 🎯 Epic: Aligning spec-doc Deployment

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Every other project on Coolify (humanize-me, speedback) runs the same two-container pattern: an nginx frontend container that owns the domain entry point, and an internal Flask container that processes API requests. spec-doc is the only outlier — it bakes Angular dist into the Flask image and serves everything from Python. That divergence means every CSS tweak triggers a full 4-minute rebuild, Coolify requires non-standard port mapping configuration, and the deployment runbook is project-specific knowledge rather than muscle memory.

Aligning spec-doc to the shared pattern eliminates the rebuild overhead and reduces the Coolify configuration surface to a single port-80 expose — the same setup already understood from two other live projects. nginx also brings SSE streaming safety (`proxy_buffering off`) and static asset caching as free wins, replacing bespoke Flask logic that only exists because Angular had nowhere else to live.

The business case is speed and confidence: solo deployments should be boring. A pattern you've already shipped twice is one you can fix at 11 PM without re-reading docs.

**Value Proposition**: Replace the monolithic Flask+Angular image with the battle-tested two-container pattern already running in production on humanize-me and speedback.

---

## Scope

### What This Epic Covers

- **`/health` Flask route** — resolves the open question in Analysis; prerequisite for Docker healthcheck on the backend container
- **Env var audit** — resolve whether Stripe/Neon/Sentry vars are live in spec-doc or copied from humanize-me; trim or document in `.env.example`
- **Frontend container** (`web/Dockerfile` + `web/nginx/nginx.conf`) — new files; nginx serves Angular SPA, proxies `/api/` to backend with SSE-safe headers
- **Compose split** — `docker-compose.yml` becomes two services (`frontend`, `backend`); `expose:` only, no `ports:`
- **Backend Dockerfile simplification** — remove the Angular build stage from `api/Dockerfile`; Flask-only image
- **Angular API base URL** — change `environment.ts` from `http://localhost:3101/api` to `/api` (relative, nginx-routed)
- **`web_serve_bp` removal** — delete the Flask blueprint that served Angular dist; nginx owns that responsibility after the split
- **CI pipeline alignment** — `deploy.yml` restructured to match humanize-me: parallel `frontend-ci` / `backend-ci` → `docker-integration` smoke test → `deploy` webhook

### What This Epic Does NOT Cover

- ❌ Wardrobai-style dedicated nginx reverse-proxy container — spec-doc has one SPA; the frontend container is the entry point; no second consumer exists to justify a separate proxy tier
- ❌ Separate `docker-compose.test.yml` — the main compose file is sufficient for smoke tests; a parallel test file adds maintenance surface with no benefit
- ❌ Docusaurus / docs container — spec-doc has no docs site
- ❌ CI artifact upload for the Angular build — the frontend image builds inside its own Docker stage; no downstream job consumes a standalone artifact

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Add `/health` Route and Audit Env Vars** | None | T2 | 0.5 days | High |
| 2 | **Create Frontend Container** | None | T1 | 0.5 days | High |
| 3 | **Split Compose and Simplify Backend Dockerfile** | T1, T2 | — | 0.5 days | High |
| 4 | **Align CI Pipeline** | T2 | T3 | 0.5 days | High |
| 5 | **Update Angular API URL and Remove `web_serve_bp`** | T3 verified in prod | — | 0.5 days | High |

---

### Task 1: Add `/health` Route and Audit Env Vars

The Docker healthcheck in the proposed compose targets `http://localhost:3101/health` — this route must exist in Flask before the split compose can start cleanly. The env var audit resolves the Analysis open question: determine which of the Stripe, Neon, and Sentry vars are actually wired into spec-doc's Flask code versus copied speculatively from humanize-me, and produce a trimmed `.env.example` that reflects reality.

**Scope**: New Flask route (minimal) + env var audit producing a trimmed `.env.example`. No new module needed; the route lives in an existing blueprint or `create_app.py`.

---

### Task 2: Create Frontend Container

Two new files — `web/Dockerfile` and `web/nginx/nginx.conf` — give the Angular app its own build and serve layer. The nginx config must handle three concerns: SPA `try_files` fallback for client-side routing, `/api/` proxy to `backend:3101` with `proxy_buffering off` and `proxy_read_timeout 900s` for SSE safety, and static asset cache headers for the Angular bundle. This task has no dependency on T1 and can be built and validated independently.

**Scope**: Two new files in `web/`. No changes to existing Flask or Angular source. Defers all compose wiring to T3.

---

### Task 3: Split Compose and Simplify Backend Dockerfile

`docker-compose.yml` becomes two services — `frontend` (builds from `web/`) and `backend` (builds from repo root, `api/Dockerfile`) — with `expose:` only and a shared bridge network. `api/Dockerfile` loses its Stage 1 Angular build and the `COPY --from=frontend-builder` line; it becomes a Flask-only image. This is the central structural change that all other tasks gate on or follow from.

**Scope**: `docker-compose.yml` rewrite, `api/Dockerfile` simplification. Depends on T1 (`/health` exists for backend healthcheck) and T2 (`web/Dockerfile` exists to reference in compose).

---

### Task 4: Align CI Pipeline

`deploy.yml` restructures to match humanize-me: `frontend-ci` (Angular build in `web/`) and `backend-ci` (lint, pytest, check-dtos in `api/`) run in parallel, then a `docker-integration` job runs `docker-compose up`, waits for `frontend:80`, hits `/` and `/api/health`, and tears down. The `deploy` job gates on all three and fires the Coolify webhook only on `master`. This replaces the current sequential `test → build-frontend → docker-build → deploy` chain.

**Scope**: `.github/workflows/deploy.yml` restructure. Can begin after T2 (frontend Dockerfile must exist for CI to reference). Runs in parallel with T3.

---

### Task 5: Update Angular API URL and Remove `web_serve_bp`

`environment.ts` changes the API base URL from the hardcoded `http://localhost:3101/api` to the relative `/api` — this is the only Angular source change required; nginx handles routing in both prod and local dev via `proxy.conf.json`. `web_serve_bp` is then deleted from Flask entirely. This task is intentionally last: the split compose must be deployed and verified in production before the Flask static-file fallback is removed, preserving rollback safety.

**Scope**: One-line `environment.ts` change + deletion of `web_serve_bp` blueprint. Gated on T3 being live and verified in Coolify.

---

## Success Criteria

- ✅ `docker-compose up` starts exactly two containers (`frontend`, `backend`) with no `ports:` mapping
- ✅ `GET /` returns the Angular application through nginx
- ✅ `GET /api/health` returns HTTP 200, proxied by nginx to Flask
- ✅ SSE streaming delivers tokens end-to-end without buffering on any `/api/` route
- ✅ CI `docker-integration` job passes smoke tests for `/` and `/api/health` on every push
- ✅ `api/Dockerfile` contains no Node.js build stage
- ✅ `web_serve_bp` blueprint is absent from the Flask codebase
- ✅ `.env.example` reflects only env vars that are referenced in spec-doc code

---

## Non-Goals

- ❌ Separate nginx reverse-proxy container (wardrobai pattern) — no second consumer of the backend exists; the frontend container is the sufficient entry point
- ❌ Separate `docker-compose.test.yml` — the main compose file handles smoke tests without a parallel test file
- ❌ Docusaurus or docs service — spec-doc has no documentation site to containerize
- ❌ CI artifact upload for the Angular build — the frontend Docker image is self-contained; no downstream artifact consumer exists

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview