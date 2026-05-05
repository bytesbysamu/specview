# 🔍 Dev Experience, CI/CD, and Deployment — Analysis

## The Problem
spec-doc-api runs only via Flask dev server with no containerization, no CI pipeline, and no defined deployment path. The backend is not reproducible outside the original dev machine and has no automated test gate before production. This phase adds Dockerfile, Compose files, GitHub Actions pipeline, Dependabot, and `.env.example` without touching Flask application code.

## Hard Constraints
- Gunicorn timeout must be ≥ 900s — AI provider calls run up to 15 minutes; 120s silently kills them
- `dtos/models.py` is committed; `make check-dtos` is a required CI gate per existing repo rules
- No direct push to `master` — pipeline gates must apply to PRs, not just main pushes
- `FLASK_ENV` is deprecated since Flask 2.3; `FLASK_DEBUG` only
- `gunicorn` moves to `requirements.txt` (not dev deps) — the Dockerfile depends on it at build time
- Coolify builds from source; no Docker registry or pre-built image push

## Open Questions
- **Production domain**: `yourdomain.com` is a placeholder throughout — must be resolved before `docker-compose.coolify.yml` is committed. Options: lock at Coolify config time and never commit | commit with a placeholder and substitute via env | commit the real subdomain now
- **Mock AI provider**: CI overrides `AI_PROVIDER=mock` for the docker-build smoke job — does a mock provider exist? Options: already implemented | needs a stub added before CI is written | use `AI_PROVIDER=cli` with a fixture response instead
- **`requirements-dev.txt` split**: CI installs `requirements-dev.txt` separately — does this file exist? Options: split already in place | needs to be created as part of this phase | single requirements file, adjust CI `pip install` accordingly

## Dependencies & Sequencing
- `/health` route must exist in `create_app.py` before the docker-build CI job is written — the smoke step fails without it
- `gunicorn` must be in `requirements.txt` before the Dockerfile is built
- Dockerfile must pass a local `docker compose build` before the pipeline references it
- `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` must be provisioned as GitHub Secrets before the deploy job runs — pipeline ships without them but deploy job will fail

## Explicitly Out of Scope
- `spec-doc-live` worktree removal — side effect of containerization, not DevOps scaffolding; defer until container is proven stable in production
- Path filters (dorny/paths-filter) — deferred in brain dump until repo grows more modules; no second consumer exists yet
- Gevent worker class — no concurrent AI use demonstrated; ship gthread
- Staging environment — brain dump explicitly excludes it; no second-environment trigger exists