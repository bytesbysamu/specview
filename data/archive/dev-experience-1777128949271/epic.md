# 🎯 Epic: Dev Experience

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

spec-doc-api runs on the Flask development server and deploys manually. This is acceptable in early development, but Phase 2 (AI text generation endpoints) changes the risk profile: Claude calls run up to 15 minutes, and the dev server's default timeout silently kills long-running requests. A broken AI endpoint discovered in production — after AI complexity has been added to the call surface — is substantially harder to diagnose than a failing CI job caught before that work begins. Containerizing now locks in a validated deployment surface while the backend is still simple.

The pattern is already proven. constellation-api added identical scaffolding in two hours and has been the least-friction deployment in the portfolio. spec-doc-api is a single Flask service with no database and no auth, making it the easiest possible containerization target. WardrobAI's nginx-and-six-service approach is the cautionary counterexample: a full day of effort, most of it on complexity that a single-service backend doesn't need. This epic deliberately does not go there.

The production volume contract also warrants definition now, not later. The Angular frontend writes project files to the backend through `PUT /api/projects/:id/files/:filename`. Defining that as an API-only named volume in the Coolify compose file — and documenting all required environment variables in `.env.example` — prevents ad-hoc bind-mount workarounds when production deployment starts. Every new developer and every CI executor needs a single, authoritative record of what the app requires to run.

**Value Proposition**: Reproducible local development, CI-validated container builds, and a worker configuration that won't silently kill 15-minute AI calls.

---

## Scope

### What This Epic Covers

- **`/health` route** — the prerequisite route that unblocks CI smoke testing; does not exist yet
- **Container files** — Dockerfile, local/CI docker-compose, Coolify production compose, and `.env.example`
- **GitHub Actions pipeline + Dependabot** — test, docker-build, and deploy jobs; dependency update automation added at the same time
- **Makefile docker targets** — `docker-up`, `docker-down`, `docker-logs` appended to the existing Makefile

### What This Epic Does NOT Cover

- ❌ **gevent worker class** — no concurrent AI use has been measured; re-scope when multi-user load is observed in production
- ❌ **dorny/paths-filter** — module count doesn't justify path filtering yet; re-scope when a second distinct module triggers false CI runs
- ❌ **spec-doc-live worktree removal** — a cleanup consequence of this work, not a deliverable; re-scope as a standalone task after containers run stably in production for one week
- ❌ **nginx** — Traefik via Coolify handles SSL and subdomain routing; an nginx layer adds complexity with no benefit for a single-service backend

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **`/health` route** | None | 2 | 0.5 days | High |
| 2 | **Container files** | None | 1 | 1 day | High |
| 3 | **GitHub Actions pipeline + Dependabot** | 1, 2 | 4 | 1 day | High |
| 4 | **Makefile docker targets** | 2 | 3 | 0.5 days | High |

### Task 1: `/health` Route

A single route in `create_app.py` that returns a JSON status response. This is a hard prerequisite for the CI docker-build job's smoke curl — without it, the pipeline has no way to confirm the container started successfully. The route requires no auth and no downstream dependencies.

**Port budget**: One route, one response — deliberately excludes deep-health checks (database connectivity, provider reachability, queue depth) because none of those components exist in this service, and adding them now would test infrastructure that isn't there.

### Task 2: Container Files

Four files that define how the backend runs in containers: a production Dockerfile with a worker timeout sized for AI calls lasting up to 15 minutes (see [Solution Architecture](./architecture.md) for timeout rationale), a docker-compose for local development and CI that mounts the sibling `spec-doc/` repo as a read-only volume, a docker-compose for Coolify with Traefik labels and an API-only named volume for project files, and `.env.example` documenting every environment variable the app reads.

**Port budget**: Four files, approximately 60–90 total lines — deliberately excludes a multi-stage build (no asset compilation step exists), health check tuning beyond minimum viable, and per-developer volume path overrides (the existing `SPEC_DOC_DIR` env var already handles that).

### Task 3: GitHub Actions Pipeline + Dependabot

Three sequential jobs: test (lint, pytest, DTO drift check on every push and PR), docker-build (build, start, smoke curl against `/health` and `/api/projects`, teardown — main-branch pushes only, with `AI_PROVIDER=mock` overriding so no API key is required), and deploy (Coolify webhook trigger — main-branch pushes only, requires `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` secrets provisioned by a human). Dependabot weekly pip update config is added in the same change so dependency coverage is in place from day one.

**Port budget**: One workflow YAML plus one Dependabot YAML, approximately 80 lines combined — deliberately excludes path filters, matrix Python versions, and release tagging; none of those add value at the current repo scale.

### Task 4: Makefile Docker Targets

Three targets — `docker-up`, `docker-down`, `docker-logs` — appended to the existing Makefile so developers and CI scripts share a consistent interface for running the containerized backend locally. These targets wrap the docker-compose commands defined in Task 2.

**Port budget**: Three targets, approximately 15 lines — deliberately excludes a standalone `docker-build` target (docker compose build is sufficient) and production-facing targets (Coolify owns that surface).

---

## Success Criteria

This epic is complete when:

- ✅ `GET /health` returns `{"status": "ok"}` from a running container
- ✅ The CI pipeline completes end-to-end on a push to main — all three jobs green
- ✅ `make docker-up` starts the backend locally and the projects endpoint returns a valid JSON array
- ✅ `.env.example` accounts for every variable the app reads; no secrets appear in any committed file
- ✅ A developer with no prior context can clone the repo, copy `.env.example` to `.env`, run `make docker-up`, and reach the API without additional setup instructions

---

## Non-Goals

- ❌ **nginx reverse proxy** — Coolify's Traefik handles SSL and routing; adding nginx would replicate wardrobai's complexity for a single-service backend that doesn't need it
- ❌ **gevent async workers** — a single-user tool; synchronous gthread workers are correct until concurrent AI load is measured in production
- ❌ **spec-doc-live worktree cleanup** — depends on containers running stably; tracked separately and not a deliverable here
- ❌ **Frontend co-deployment** — the Angular app deploys via its own separate Coolify webhook; this epic is scoped to the Flask service only

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview