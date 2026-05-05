# 🔍 Aligning spec-doc Deployment — Analysis

## The Problem
spec-doc runs a monolithic Flask container that bakes Angular dist into the image and serves it via `web_serve_bp`. Every other project on Coolify uses a split pattern: nginx frontend container + internal Flask container. The divergence complicates Coolify config and forces a full image rebuild on any frontend change.

## Hard Constraints
- Coolify exposes `frontend:80` and lets Traefik handle the domain — no `ports:` mapping anywhere
- SSE streaming is live; nginx **must** have `proxy_buffering off` and `proxy_read_timeout 900s` on `/api/`
- In-process state only — no Redis, no Postgres added as services
- `api/Dockerfile` context is repo root (Flask lives in `api/`); this must be preserved in the split compose

## Open Questions
- **Backend health endpoint**: proposed `healthcheck` hits `http://localhost:3101/health` — does this route exist, or does it need to be added? *(options: add `/health` route, use an existing route, skip Docker healthcheck)*
- **Env vars in compose**: brain dump lists Stripe, Neon, Sentry vars — are all of these live in the current spec-doc backend, or were they copied from humanize-me? *(options: audit and trim, keep all speculatively, move to `.env.example`)*
- **CI compose smoke test**: run against main `docker-compose.yml` or a separate `docker-compose.test.yml`? *(options: main file with overrides, separate test file like wardrobai, skip integration job)*

## Dependencies & Sequencing
- `web/Dockerfile` + `web/nginx/nginx.conf` must exist before `docker-compose.yml` is split — compose references them
- `environment.ts` API base URL must change to `/api` before the frontend container works — the old `http://localhost:3101/api` breaks when nginx is the proxy
- `web_serve_bp` can only be deleted after the split compose is deployed and verified — deleting it first breaks the monolithic image still running in production

## Explicitly Out of Scope
- Separate nginx reverse-proxy service (wardrobai pattern) — spec-doc has one SPA; frontend container IS the entry point; no second consumer justifies a dedicated proxy service
- `build-frontend` CI artifact upload — no downstream job consumes the artifact once Angular builds inside its own Docker image
- Docusaurus / docs service — spec-doc has no docs site; do not model after speedback's three-service compose