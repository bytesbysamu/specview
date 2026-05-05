# 🎯 Epic: Deployment Stack

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

spec-doc's deployment surface has grown by accretion: three compose files, three disconnected workflow directories, a healthcheck command that silently fails in the runtime image, and a build context that ships hundreds of megabytes of frontend cache on every push. None of these fail loudly. They fail by being irrelevant or broken in ways that only surface under pressure — a botched rollback, an env var gap that disables billing in production, a CI job that looks green because it warns instead of fails. Every future infrastructure change is a guess about which file actually matters.

Resolving this is not a feature — it is the precondition for trusting the deploy surface. humanize-me already runs the target shape (nginx frontend + internal Flask backend, single compose file, parallel CI) in production. Porting that proven pattern to spec-doc eliminates a class of operational uncertainty before it becomes a production incident. It also unblocks any future SaaS feature — Stripe webhooks, Sentry error tracking, Neon auth — that depends on consistent env var plumbing, since the current coolify compose silently omits all of those keys.

The total effort is approximately one day. The cost of not doing it compounds with every deploy and every CI change made against a misunderstood baseline.

**Value Proposition**: Replace a three-compose, monolithic-image deploy surface with the single-compose two-container shape already proven in production on humanize-me, eliminating silent failures and establishing a trustworthy baseline for all future infrastructure changes.

---

## Scope

### What This Epic Covers

- **Dead-file removal** — three tracked-but-never-executing workflow files, the misplaced `.dockerignore`, and the Coolify-specific compose are deleted; a root `.dockerignore` is added in the correct build-context location
- **Frontend container** — a dedicated `web/Dockerfile` and nginx configuration are added so the Angular SPA runs in its own nginx:alpine container separate from Flask. **The `web` service in Task 4's compose builds from these files** — Task 2 produces the artefacts; Task 4 wires them in.
- **Flask route prefix alignment** — all Flask routes, including `/health`, move under `/api/`; Angular's environment and dev proxy config align to the same relative path; `web_serve_bp` is removed
- **Single canonical compose file** — the root `docker-compose.yml` is replaced with a two-service definition (`api` + `web`) covering all production env vars; `api/docker-compose.yml` is deleted by Task 4 and `api/docker-compose.coolify.yml` is deleted by Task 1
- **Workflow rewrite** — `.github/workflows/deploy.yml` is rewritten to a four-job structure (`frontend-ci` ∥ `backend-ci` → `docker-integration` → `deploy`) with a hard-failing smoke test that exec's into the nginx container to prove the proxy→Flask path

### What This Epic Does NOT Cover

- ❌ **Coolify migration** — Coolify stays; no evaluation of Kamal, Dokku, or other platforms
- ❌ **TLS in nginx config** — Coolify/Traefik terminates TLS upstream; nginx stays HTTP on port 80
- ❌ **Separate nginx reverse-proxy tier** — one SPA, one backend; frontend container is the entry point; no second consumer justifies a third container
- ❌ **`docker-compose.test.yml`** — the `docker-integration` job in the main workflow handles smoke testing; a parallel test-only compose doubles maintenance with no benefit
- ❌ **Redis, Postgres, or external queue as compose services** — in-process state and named volume only, per architecture constraints
- ❌ **Build artifact upload for Angular dist** — each service builds inside its own Docker stage; no downstream artifact consumer
- ❌ **CLAUDE.md or deploy runbook updates** — tracked separately after code ships

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Dead-file purge + root .dockerignore** | None | Yes (w/ 2, 3) | 0.25 days | High |
| 2 | **web/Dockerfile + nginx config** | None | Yes (w/ 1, 3) | 0.25 days | High |
| 3 | **Flask /api/ prefix + Angular env alignment** | None (Coolify `/health` external-probe check is a deploy-day gate, not a code dep) | Yes (w/ 1, 2) | 0.5 days | High |
| 4 | **Two-service compose + api/Dockerfile simplification** | Tasks 2 + 3 (uses web/Dockerfile; healthcheck on /api/health) | — | 0.25 days | High |
| 5 | **Workflow rewrite** | Tasks 3 + 4 (smoke test hits /api/health via `web` service) | — | 0.25 days | High |

### Task 1: Dead-file purge + root .dockerignore

Three workflow files tracked under `api/.github/` and `web/.github/` are never executed by GitHub Actions, which only reads `.github/workflows/` at the repo root. Similarly, `api/.dockerignore` has no effect because the Docker build context is the repo root. This task removes all four files, removes `api/docker-compose.coolify.yml`, and adds a single `.dockerignore` at the repo root so subsequent builds exclude node_modules, caches, and non-essential paths from the build context.

**Port budget**: Deletions only plus one new file (~30 lines). No module changes, no route changes, no env changes.

---

### Task 2: web/Dockerfile + nginx config

This task introduces the frontend container as a pure addition — nothing references these files yet. A two-stage `web/Dockerfile` builds the Angular app and copies the dist into nginx:alpine. A `web/nginx/nginx.conf` wires the SPA fallback, the `/api/` proxy upstream, and static-asset cache headers. The nginx config defers backend DNS resolution so the frontend container can start before the backend is healthy.

**Port budget**: Two new files (~50 lines combined). No changes to existing files. Depends on Task 3 being merged before the compose file references them in production.

---

### Task 3: Flask /api/ prefix + Angular env alignment

Every Flask route, including `/health`, gains the `/api/` prefix by registering a `url_prefix` on the app. Angular's `environment.ts` changes its `apiUrl` to the relative path `/api` so dev (via `proxy.conf.json`) and prod (via nginx) resolve the same paths without environment-specific branching. `web_serve_bp` is removed since nginx now owns static serving. This task carries the largest diff but is mostly mechanical; it must land before Task 4 so the nginx upstream resolves correctly. **Gate**: Confirm whether any external consumer (Coolify healthcheck UI, uptime monitor) depends on the bare `/health` path before merging — see [Analysis](./analysis.md).

**Port budget**: Route prefix registration (~5 lines in `create_app.py`), `environment.ts` update (1 line), `proxy.conf.json` update (1 line), `web_serve_bp` deletion (~30 lines removed). Net change is a reduction.

---

### Task 4: Two-service compose + api/Dockerfile simplification

The root `docker-compose.yml` is replaced with a two-service definition: `api` (Flask) and `web` (the nginx container built by Task 2's `web/Dockerfile`). `api/docker-compose.yml` is deleted (`api/docker-compose.coolify.yml` was deleted by Task 1). `api/Dockerfile` drops its Node.js first stage and becomes a single-stage Flask-only image. Both services use `expose:` only — Coolify/Traefik handles ingress. The `api` healthcheck uses `python -c urllib.request` against `/api/health` (no curl in the slim image; Task 3 renamed the route). The `web` healthcheck `wget -qO- http://localhost/api/health` proves the full nginx→Flask path is live. **Gate**: Confirm Coolify's active `Compose Path` setting before touching compose files — see [Analysis](./analysis.md) — to determine whether a transition window is needed.

**Port budget**: Replacement of `docker-compose.yml` (~50 lines), deletion of `api/docker-compose.yml`, reduction of `api/Dockerfile` by ~12 lines. No new abstractions.

---

### Task 5: Workflow rewrite

`.github/workflows/deploy.yml` is rewritten to four jobs: `frontend-ci` and `backend-ci` run in parallel, then `docker-integration` (conditional on `master`) runs `docker compose up -d --build` and probes `/api/health` via `docker compose exec -T web wget` — testing the actual nginx→Flask path Coolify production uses. The `deploy` job fires the Coolify webhook only after `docker-integration` passes. The soft-fail `WARN` block identified in [Analysis](./analysis.md) is removed. **Gates on Tasks 3 and 4**: the smoke probe path requires Task 3 (Flask `/api/health`) and the `web` service requires Task 4 (two-service compose).

**Port budget**: Full replacement of the existing workflow file (~80 lines). Structural change; no new secrets or env vars required beyond what is already set.

---

## Success Criteria

- ✅ `docker compose up --build` from repo root starts exactly two services (`api`, `web`); both reach `healthy` status; healthchecks use `python -c urllib.request` (api) and `wget` (web), not curl
- ✅ `docker compose exec -T web wget -qO- http://localhost/api/health` returns HTTP 200 with `{"status": "ok"}` — proves the nginx→Flask path
- ✅ Neither service declares `ports:`; both use `expose:` only (Coolify/Traefik handles ingress)
- ✅ `docker build` does not send `web/node_modules/` or `web/.angular/` to the daemon (verified by build context size; root `.dockerignore` from Task 1)
- ✅ GitHub Actions shows exactly one workflow directory (`.github/workflows/`) at repo root; zero dead entries under `api/.github/` or `web/.github/`
- ✅ The `docker-integration` smoke test hard-fails (non-zero exit) on any non-200 response — no `continue-on-error: true` anywhere
- ✅ `api/docker-compose.coolify.yml`, `api/docker-compose.yml`, `api/.dockerignore`, `api/.github/`, and `web/.github/` are absent from the repo tree
- ✅ All existing `make test` and `make check-dtos` targets continue to pass; new structural tests in `test_docker.py`, `test_pipeline.py`, `test_cleanup.py`, `test_web_infra.py` lock in the new shape

---

## Non-Goals

- ❌ **Migrating off Coolify** — operational continuity takes priority; re-evaluate only if Coolify becomes a blocker
- ❌ **`environment.prod.ts`** — nothing currently varies between dev and prod that is not already a runtime env var; a second environment file adds build complexity with no payoff
- ❌ **Keeping `api/docker-compose.yml` as a dev convenience** — `make dev-api` runs `python3 app.py` directly; compose for local dev is over-engineering for a single-consumer tool
- ❌ **Abstracting a shared base image or shared build logic** — backend and frontend Dockerfiles are independent; a shared base has exactly one concrete case and no second consumer
- ❌ **CLAUDE.md, status.md, or deploy runbook updates** — documentation reflects reality after code ships; not part of this changeset

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview