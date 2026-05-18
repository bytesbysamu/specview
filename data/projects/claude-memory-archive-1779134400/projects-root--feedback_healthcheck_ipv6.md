---
name: Docker healthchecks must use 127.0.0.1 not localhost
description: localhost resolves to IPv6 ::1 in containers but services bind IPv4 — always use 127.0.0.1 in healthcheck test URLs
type: feedback
---

Always use `127.0.0.1` (not `localhost`) in Docker `healthcheck.test` URLs.

**Why:** `localhost` in a Docker container resolves to `::1` (IPv6), but gunicorn and nginx bind to `0.0.0.0` (IPv4 only). Every healthcheck gets connection refused → container stays unhealthy → Coolify/Traefik deregisters the service → 404 in production. This caused the May 9 VPS outage.

**How to apply:** Any time a `docker-compose.yml` healthcheck is written or reviewed, ensure `test:` lines use `http://127.0.0.1:PORT/...` or `http://127.0.0.1/...`. The CI `compose-lint` job now enforces this automatically (fails if `localhost` appears in any `test:` line).
