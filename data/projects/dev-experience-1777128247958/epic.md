# 🎯 Epic: Dev Experience

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The spec-doc-api backend currently runs only as a local Flask dev server. There is no way to deploy it reproducibly, no CI gate that catches a broken build before merge, and no documented environment contract for a new machine or a production host. Every developer and every deployment environment absorbs that cost silently, in ad-hoc setup time and in the risk of a breaking change reaching production undetected.

Containerizing before Phase 2 AI endpoints are added keeps the feedback loop short. A single Flask service with no database and no auth is the simplest possible containerization surface in the portfolio. Doing this work after AI calls are in the mix means diagnosing a failing container against live Claude API calls — slower feedback, harder to isolate. The two-hour reference case (constellation-api) confirms the surface is small enough to close in a single session.

The `spec-doc-data` volume contract also needs to be settled at the infrastructure layer before production traffic arrives. The Angular frontend writes project files through the API; defining that boundary now in `docker-compose.coolify.yml` prevents ad-hoc bind-mount decisions made under deployment pressure.

**Value Proposition**: A reproducible, CI-verified, single-push-deployable Flask backend that eliminates the manual deployment gap and unblocks Phase 2 AI endpoint work before production users arrive.

---

## Scope

### What This Epic Covers

- **`/health` route** — prerequisite for the CI smoke check; implemented in `create_app.py` before any pipeline is wired
- **Dockerfile + Gunicorn** — non-root, slim base, 900 s timeout to accommodate long-running Claude CLI calls
- **docker-compose (local + Coolify)** — local dev/CI mounts `spec-doc/` read-only; Coolify compose carries Traefik labels and the `spec-doc-data` named volume; Makefile docker targets for developer use
- **GitHub Actions pipeline** — three sequential jobs (test → docker-build → deploy); pip cache; Coolify webhook on main push
- **Dependabot + `.env.example`** — automated pip updates added with the pipeline; environment contract documented for every new developer and for Coolify's environment UI

### What This Epic Does NOT Cover

- ❌ **nginx reverse proxy** — Coolify's Traefik handles SSL and routing; a separate proxy layer adds complexity with no benefit for a single-service backend
- ❌ **gevent worker class / task queue** — single-user load does not require concurrent AI call handling; re-scope when multi-user concurrency is observed in production
- ❌ **`spec-doc-live` worktree removal** — consequence of this phase, not part of it; scope as a cleanup ticket after containers are confirmed running in production
- ❌ **Path filters (dorny/paths-filter)** — no independent modules yet; add when ≥ 2 modules exist where a change in one should not trigger the other's CI

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **`/health` Route** | None | 2 | 0.5 days | High |
| 2 | **Dockerfile + Gunicorn** | None | 1 | 0.5 days | High |
| 3 | **docker-compose Files + Makefile Docker Targets** | 2 | — | 0.5 days | High |
| 4 | **GitHub Actions Pipeline + Dependabot + `.env.example`** | 1, 2, 3 | — | 1 day | High |

---

### Task 1: `/health` Route

Adds a single unauthenticated route to `create_app.py` that returns `{"status": "ok"}`. This route is the only prerequisite that gates the CI docker-build smoke check — the pipeline cannot verify the container starts correctly without it. Tasks 1 and 2 have no dependency on each other and can proceed in parallel.

**Port budget**: ~5 lines in `create_app.py`; deliberately excludes readiness-vs-liveness distinction, metrics exposure, and auth middleware — one deployment target and one developer makes that distinction premature.

---

### Task 2: Dockerfile + Gunicorn

Produces a production-ready `Dockerfile` using a non-root user, a slim Python base, and Gunicorn as the WSGI server. The 900 s worker timeout is a hard requirement, not a tuning parameter — Claude CLI calls run up to 15 minutes and a 120 s default will silently kill them. `--preload` loads the app once before workers fork, avoiding duplicate AI provider initialization.

**Port budget**: ~30 lines in one `Dockerfile`; deliberately excludes multi-stage build, gevent worker class, and worker count tuning — single-user workload does not justify the added surface today.

---

### Task 3: docker-compose Files + Makefile Docker Targets

Produces `docker-compose.yml` for local dev and CI (mounts `spec-doc/` read-only, matching the current bind-mount pattern) and `docker-compose.coolify.yml` for production (Traefik labels for subdomain routing, `spec-doc-data` named volume owned by the API container). Adds `docker-up`, `docker-down`, and `docker-logs` targets to the existing Makefile.

**Port budget**: ~40 lines across two compose files plus three Makefile targets; deliberately excludes a multi-env profile setup and health check overrides in compose — Coolify's Traefik makes a local reverse proxy redundant, and the single environment makes profiles unnecessary.

---

### Task 4: GitHub Actions Pipeline + Dependabot + `.env.example`

Wires three sequential jobs — **test** (lint, pytest, DTO drift check, pip cache), **docker-build** (container smoke with `AI_PROVIDER=mock`), and **deploy** (Coolify webhook) — triggered on every push and PR against `main`. Adds `.github/dependabot.yml` for weekly pip updates alongside the pipeline rather than as a later afterthought. Adds `.env.example` documenting every env var the app reads.

**Port budget**: ~80 lines in `deploy.yml`, ~15 lines in `dependabot.yml`, ~15 lines in `.env.example`; deliberately excludes path filters, matrix builds, and Slack/email notifications — no independent modules to filter yet, a single deployment target makes matrix unnecessary, and notification infrastructure is overhead before the first production user.

---

## Success Criteria

This epic is complete when:

- ✅ `docker compose up` starts the API on port 3101 with no manual steps beyond copying `.env` from `.env.example`
- ✅ `curl http://localhost:3101/health` returns `{"status": "ok"}` against the running container
- ✅ Every push to `main` executes the full test → docker-build → deploy pipeline without manual intervention
- ✅ A PR against `main` runs the test job and blocks merge if lint, tests, or DTO drift check fails
- ✅ Production deployment is triggered by a push to `main` with no SSH access or manual Coolify UI steps required

---

## Non-Goals

- ❌ **nginx reverse proxy** — Coolify's Traefik handles SSL and subdomain routing; adding nginx introduces a layer with no functional benefit for a single-service backend
- ❌ **gevent / task queue** — two Gunicorn workers with gthread is correct for a single-user tool; re-scope when concurrent AI use from multiple users is observed
- ❌ **Worktree removal** — `spec-doc-live` removal is a post-deploy cleanup step, not part of standing up the container; scope separately after production containers are confirmed running
- ❌ **Path filters** — dorny/paths-filter adds value only when ≥ 2 independent modules exist; adding it now optimises a pipeline that has nothing to filter

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview