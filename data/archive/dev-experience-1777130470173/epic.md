# 🎯 Epic: Dev Experience — CI/CD and Containerization

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

spec-doc-api is a single Flask service with no database and no auth — the lowest-complexity containerization surface in the portfolio. Yet every developer who clones it today faces manual environment configuration, no automated test gate, and no reproducible deployment path. Phase 2 (AI text endpoints) is the inflection point: once streaming Claude calls land, a failing deployment becomes significantly harder to isolate from application bugs. Adding the scaffolding before Phase 2 ships means CI and the container are proven on a simple, stable codebase.

The cost of the gap compounds forward. Without a CI gate, DTO drift and lint regressions enter main silently. Without a container, the `spec-doc-live` worktree exists as a permanent maintenance surface — a structural workaround for a solved problem. Defining the `spec-doc-data` volume contract now prevents ad-hoc bind-mount decisions at production launch, when the pressure to "just make it work" is highest.

The reference case is constellation-api: identical service profile, two hours of scaffolding, the most painless deployment in the portfolio since. The effort ceiling is known and the patterns are proven.

**Value Proposition**: A locked-down CI pipeline and reproducible container, in place before Phase 2 AI endpoints land, keeps the deployment surface simple when debugging matters most.

---

## Scope

### What This Epic Covers

- **`/health` route** — single Flask app change; prerequisite for the CI docker-build smoke check
- **Dockerfile and local docker-compose** — reproducible dev environment; Gunicorn with 900s timeout for long-running AI calls; non-root user
- **`docker-compose.coolify.yml`** — production compose with Traefik labels; `spec-doc-data` named volume contract locked in
- **GitHub Actions pipeline** — three sequential jobs: test, docker-build (with smoke check), deploy via Coolify webhook
- **`.env.example` and Makefile additions** — environment documentation and developer-facing container targets
- **Dependabot** — automated pip dependency updates; added alongside CI, not after

### What This Epic Does NOT Cover

- ❌ **Path filters (dorny/paths-filter)** — no multi-module need exists; re-scope when the repo reaches ≥ 3 independent modules
- ❌ **gevent worker class** — no concurrent multi-user load is observed; re-scope when production traffic data exists
- ❌ **`spec-doc-live` worktree removal** — consequence of this phase, not a deliverable; defer to a standalone cleanup task after the container is proven stable in production
- ❌ **nginx sidecar** — Coolify's Traefik handles SSL and routing; a sidecar adds complexity with no benefit

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Health Route** | None | — | 0.5 days | High |
| 2 | **Container Scaffolding** | 1 | 5 | 1 day | High |
| 3 | **Production Compose** | 2 | — | 0.5 days | High |
| 4 | **CI/CD Pipeline** | 1, 2, 3 | 5 | 1 day | High |
| 5 | **Dependabot** | None | 2, 4 | 0.5 days | Low |

---

### Task 1: Health Route

Add a `/health` endpoint to `create_app.py` returning `{"status": "ok"}`. This is the only Flask application change in this epic; the analysis flags it as an explicit contradiction in the original scope statement ("none of this changes Flask application code"), and it must ship before any CI docker-build job is written. No authentication, no downstream dependency checks.

**Port budget**: ~5 lines in `create_app.py`; deliberately excludes downstream health checks (database, external services) because neither exists at this scale — adding them now builds infrastructure for problems the service doesn't have.

---

### Task 2: Container Scaffolding

Deliver the Dockerfile, `docker-compose.yml` for local development, `.env.example`, and Makefile additions that give every developer a reproducible run environment. The Gunicorn timeout must be set to 900 seconds to accommodate Claude CLI calls that run up to 15 minutes — see [Solution Architecture](./architecture.md) for the worker model rationale. This task must also confirm whether `AI_PROVIDER=mock` resolves without an API key today; if a mock provider does not exist, its minimum viable form is in scope here, since the CI docker-build job cannot pass without it.

**Port budget**: ~60 lines across Dockerfile, `docker-compose.yml`, and `.env.example`, plus Makefile targets (exact targets defined in [Solution Architecture](./architecture.md)); excludes multi-stage builds (no compiled artifacts), bind-mount strategies (volume contract decided in Task 3), and gevent configuration (no concurrent-load case today).

---

### Task 3: Production Compose

Deliver `docker-compose.coolify.yml` with Traefik routing labels and the `spec-doc-data` named volume definition. This file locks in the volume contract: the API container owns the single named volume; the Angular frontend writes project files through the API, not through a shared filesystem mount. Defining this now prevents bind-mount improvisation at production launch.

**Port budget**: ~25 lines; excludes nginx sidecar (Traefik handles SSL and subdomain routing per the constellation-api pattern), multi-service orchestration (single Flask service), and replica or scaling configuration (single-user tool today).

---

### Task 4: CI/CD Pipeline

Deliver the GitHub Actions workflow with three sequential jobs — test, docker-build, deploy — structured after the constellation-api `deploy.yml`. The test job runs on every push and PR; docker-build and deploy run on main pushes only. The docker-build job depends on `AI_PROVIDER=mock` being functional (resolved in Task 2) and `/health` being implemented (Task 1); the smoke check curls both `/health` and `/api/projects`. Deploy triggers the Coolify webhook via repository secrets.

**Port budget**: ~90 lines of YAML; excludes path filters (single module), matrix Python versions (pinned to 3.11), and parallel job execution (test → build → deploy ordering is a correctness requirement, not a performance choice).

---

### Task 5: Dependabot

Add `.github/dependabot.yml` configured for weekly pip updates. This has no blocking dependencies and can proceed in parallel with Tasks 2 through 4; it is sequenced last only to avoid merge conflicts while the Actions workflow file is being written.

**Port budget**: ~12 lines; excludes npm and Docker Hub digest update ecosystems — Python is the only active dependency surface in this repo today.

---

## Success Criteria

This epic is complete when:

- ✅ `docker compose up` starts the API locally without manual environment configuration beyond copying `.env.example`
- ✅ Every push to main triggers the three-job pipeline and a failing test or lint error blocks the deploy job
- ✅ A push to main with all checks passing results in a live deployment on the Coolify-managed subdomain without manual intervention
- ✅ `GET /health` returns `{"status": "ok"}` in both the local container and the production deployment
- ✅ The CI docker-build job completes without an API key present in the environment

---

## Non-Goals

- ❌ **`spec-doc-live` worktree removal** — this is a downstream consequence of the container being stable in production; it is not a deliverable of this epic and must not block merge
- ❌ **gevent or task queue** — no concurrent-user load case exists; building for it now is infrastructure nobody has asked for
- ❌ **Path filters** — premature optimization for a single-module repo; the decision criteria (≥ 3 independent modules) is explicit
- ❌ **wardrobai-style multi-service nginx compose** — Traefik handles routing; a second networking layer adds complexity with no benefit for a single-service backend

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – Worker model, volume strategy, and Makefile target definitions
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview