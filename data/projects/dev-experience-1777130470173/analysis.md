# 🔍 Dev Experience — Analysis

## The Problem
spec-doc-api has no container, no CI pipeline, and no deployment configuration. Each developer configures the environment manually, pushes to main with no automated gate, and deployment is ad hoc. The backend is the simplest possible containerization surface — single Flask service, no database, no auth — but the scaffolding has never been added.

## Hard Constraints
- Gunicorn timeout must be ≥ 900s; Claude CLI calls run up to 15 minutes and 120s silently drops requests mid-generation
- Non-root user in the image — portfolio baseline, non-negotiable
- No nginx; Coolify's Traefik handles SSL and routing (constellation-api pattern)
- Separate Coolify webhooks for spec-doc and spec-doc-api — decided, closed
- gthread workers now; gevent deferred until concurrent AI load is observed
- **Contradiction:** brain dump states "none of this changes Flask application code" then requires `/health` added to `create_app.py` — that is an app change. The scope statement is wrong.

## Open Questions
- `AI_PROVIDER=mock` — does a mock provider exist today, or does it need to be built? The docker-build CI job cannot pass without it. Which path?
- Makefile additions are listed without specifying the actual targets. Which targets — `docker-up`, `docker-down`, others? Implementation guide can't be written until enumerated.
- Worktree removal — named as a consequence of containerization, not assigned as a task. Is it in scope for this epic, or a follow-on cleanup? Which path?

## Dependencies & Sequencing
- `/health` route must exist before the docker-build CI job is written — brain dump flags this; it must be sequenced first
- `AI_PROVIDER=mock` must be confirmed working before the docker-build job step can be written
- test → docker-build → deploy are strictly sequential; no parallelism in the pipeline
- Dependabot, `.env.example`, and Makefile additions have no blocking dependencies — can proceed in parallel with Dockerfile work

## Explicitly Out of Scope
- Path filters (dorny/paths-filter) — no current multi-module need; re-scope when repo reaches ≥ 3 independent modules
- gevent / task queue — no named concurrent-user load exists; re-scope when multi-user production traffic is observed
- wardrobai-style multi-service nginx compose — rejected, no consumer; re-scope never (Traefik handles this)
- Worktree removal — consequence of this phase, not a deliverable; defer to a standalone cleanup task after containers are proven stable in production