# 🔍 Dev Experience — Analysis

## The Problem
spec-doc-api has no container, CI, or deployment config. The app runs on Flask dev server and deploys manually. Phase 2 (AI text endpoints) is imminent — adding DevOps scaffolding now avoids debugging a broken container once AI calls complicate the surface.

## Hard Constraints
- Gunicorn timeout ≥ 900s — AI calls run up to 15 min; 120s silently kills them
- Reference pattern is constellation-api (single service, Coolify webhook) — not wardrobai's nginx stack
- No nginx — Traefik via Coolify handles SSL and subdomain routing
- Separate Coolify webhooks for Angular and Flask — already decided
- Volume contract already decided: API-only named volume; Angular frontend writes through `PUT /api/projects/:id/files/:filename`
- No direct push to master (repo rule)

## Open Questions
- **Does `AI_PROVIDER=mock` exist?** CI docker-build overrides to avoid needing an API key at build time. If the mock isn't implemented, the job fails before any container work is validated. Answer: it exists already / it needs to be built first.
- **What are the Makefile targets?** The brain dump names `make docker-up` as a consumer but lists no actual target definitions. `docker-up`, `docker-down`, `docker-logs`? Decide before writing the Makefile section.
- **How is `spec-doc/` resolved locally?** docker-compose mounts the sibling repo as a volume. Absolute host paths break on other machines. Relative `..` path, or `SPEC_DOC_DIR` env var already in `.env`?

## Dependencies & Sequencing
- `/health` route must exist in `create_app.py` before the docker-build CI job is written — brain dump flags this, it's a hard blocker
- Mock AI provider must exist before CI docker-build can pass without secrets
- Coolify secrets (`COOLIFY_WEBHOOK`, `COOLIFY_TOKEN`) must be provisioned (human action) before the deploy job activates — not a code task but blocks pipeline end-to-end validation
- `/health`, Dockerfile, and docker-compose can be written in parallel; pipeline YAML depends on all three

## Explicitly Out of Scope
- **dorny/paths-filter** — brain dump explicitly defers; re-scope when a second distinct module triggers false CI runs
- **gevent worker class** — no concurrent AI use observed; re-scope when multi-user load is measured in production
- **spec-doc-live worktree removal** — cleanup consequence of this work, not a deliverable in this epic; re-scope as a standalone task after containers run stably in production for one week