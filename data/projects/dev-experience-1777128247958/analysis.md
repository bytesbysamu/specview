# 🔍 Dev Experience — Analysis

## The Problem

spec-doc-api has no containerization, no CI pipeline, and no deployment configuration. The backend runs only as a local Flask dev server, making it unreproducible across environments and undeployable without manual steps. This phase adds the scaffolding layer without touching application code.

## Hard Constraints

- Reference pattern is constellation-api (single Flask service + Coolify webhook), not wardrobai's multi-service nginx stack
- Gunicorn timeout must be ≥ 900s — Claude CLI calls run up to 15 minutes; 120s silently kills them
- Coolify manages SSL/DNS via Traefik; no nginx
- Separate Coolify webhooks for Angular and Flask — decided, not revisable here
- Data volume: API container owns the named volume; Angular writes files through `PUT /api/projects/:id/files/:filename`; no shared volume with Angular container
- `/health` route must be implemented before the CI docker-build job is written

## Open Questions

- **Makefile targets**: The brain dump names `make docker-up` as a consumer but the new target list is blank — which targets are being added? (`docker-up`, `docker-down`, `docker-logs`?)
- **`AI_PROVIDER=mock` in CI**: Is a mock provider already implemented, or does overriding this env var require application code changes before docker-build can pass?
- **`spec-doc-data` volume lifecycle in Coolify**: Does Coolify auto-create the named volume on first deploy, or does it require manual pre-creation in the Coolify UI?

## Dependencies & Sequencing

- `/health` route blocks the CI docker-build job — implement it first
- test → docker-build → deploy is structural and sequential; no parallelism available
- This phase should land before Phase 2 (AI text endpoints) — debugging a broken container is harder once AI calls are in the mix
- Worktree removal can only be verified after containers are confirmed live in production — it is a post-deploy cleanup step, not part of this phase

## Explicitly Out of Scope

- **Path filters (dorny/paths-filter)** — no independent modules yet; re-scope when ≥2 modules exist where a change in one should not trigger the other's CI
- **gevent worker class / task queue** — no concurrent multi-user load yet; re-scope when concurrent AI use from multiple users is observed in production
- **`spec-doc-live` worktree removal** — consequence of this phase, not part of it; re-scope as a cleanup ticket after containers are confirmed running in production