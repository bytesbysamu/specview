# 🔍 Deployment Stack — Analysis

## The Problem
Three compose files with conflicting env coverage and ingress strategies make every deploy a coin-flip about which file Coolify reads. The `curl` healthcheck never passes in `python:3.11-slim`; the `.dockerignore` doesn't apply to the build context; three workflow files are tracked but never execute. None fail loudly — they fail by being silently wrong.

## Hard Constraints
- Coolify stays; no migration.
- humanize-me two-container pattern (nginx + Flask) is the target shape — already proven in production.
- `STRIPE_PRICE_ID_PRO` is the canonical billing var name; it's live in the billing module. Do not rename.
- No Redis, no Postgres, no external queue — named volume and in-process state only.
- `make dev-api` runs `python3 app.py` directly; `api/docker-compose.yml` is unused in any dev workflow. Deleting it contradicts nothing in builder context.
- Flask route prefix change must land before the compose swap — nginx `/api/` proxy won't resolve otherwise.

## Open Questions
- **Coolify's active `Compose Path`**: root `docker-compose.yml`, `api/docker-compose.coolify.yml`, or something else? Determines whether we need a transition window (briefly two valid files) or can hard-swap. Confirm in Coolify dashboard before touching compose.
- **External consumers of `/health`**: Does Coolify's healthcheck UI, an uptime monitor, or anything outside the codebase hit the bare path? Options: (a) add `/api/health` alias, deprecate `/health` later; (b) confirm no external consumer and delete directly; (c) keep both routes permanently.
- **`environment.prod.ts`**: Add a second Angular environment file or stay single-file? Brain dump leans single-file; nothing currently varies at build time. Decision affects whether `--configuration production` does anything useful.

## Dependencies & Sequencing
- Coolify `Compose Path` confirmation blocks the compose file swap — wrong active file during transition breaks production.
- Flask route prefix change blocks compose + nginx wiring — nginx upstream is broken until Flask routes move.
- `web_serve_bp` deletion is gated on nginx taking over static serving; can't delete until compose swap ships.
- Cleanup (dead workflows, `.dockerignore`), `web/Dockerfile` addition, and workflow rewrite are independent and can land in any order.

## Explicitly Out of Scope
- All Dockerfile, nginx.conf, compose YAML, and workflow YAML in the brain dump → implementation guides only per content routing rules; no code blocks here.
- `aligning-spec-doc-deployment` epic: superseded; do not port or reference.
- Separate nginx reverse-proxy tier: no second SPA consumer exists. Re-scope when a second product shares this host.
- `docker-compose.test.yml`: integration job in the main workflow handles smoke testing; parallel test compose doubles maintenance with no payoff. Re-scope if test isolation becomes a real need.
- CLAUDE.md and deploy runbook updates: track separately after code ships.