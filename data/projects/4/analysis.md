# 🔍 Auth Reliability & Credential Persistence — Analysis

## The Problem
The spec-doc API authenticates to Claude CLI via an OAuth access token (~1hr TTL) baked into a Docker env var. Every container restart replays the stale token. The CLI's `--bare` flag bypasses its own refresh mechanism, so tokens rot silently. This causes daily 502 outages requiring manual keychain extraction — the #1 reliability blocker for production use.

## Hard Constraints
- Claude Max flat rate is the only viable cost path — API key billing (Option A) is rejected on cost grounds
- `--bare` mode (triggered by `ANTHROPIC_CLI_KEY` env var) bypasses `.credentials.json` entirely — the persistent volume only works if this env var is removed
- All changes validated locally via `docker compose` before touching VPS
- Solo operator — recovery procedures must be executable without tribal knowledge

## Open Questions
- **Does `claude login` work headless inside a Docker container?** The decision assumes it does, but the analysis flags this as unvalidated. If it requires a browser redirect with no `--no-browser` fallback, Option B is dead on arrival. Test locally before planning anything else.
- **What is the actual refresh token TTL?** The doc says "weeks to months" but never cites a source. If it's days, Option B buys almost nothing over the current manual cycle. This determines whether the fix is durable or just a longer fuse.
- **Is `--agent chain-agent` load-bearing?** Listed as a pro of Option B over Option A, but never validated. If it's unused, the only remaining argument for Option B over a future Option A is cost — and cost calculus changes at SaaS launch.
- **What triggers a refresh token rotation?** If `docker compose down` causes the CLI to miss a rotation window, the "survives full teardown" assumption in Phase 5 may be wrong.

## Dependencies & Sequencing
- Removing `ANTHROPIC_CLI_KEY` is a **hard prerequisite** — without it, the volume mount is pointless because `--bare` still bypasses the credentials file
- `entrypoint.sh` seed-only-once logic must land **before** the first `claude login`, or the next restart overwrites the session
- `cli.py` stdout-in-errors fix (Quick Win #1) should land **before** testing Option B — otherwise auth failures during testing will produce the same empty-stderr confusion
- VPS login can only happen **after** merge + deploy — it's a post-deploy manual step, not a code change

## Explicitly Out of Scope
- **Frontend error differentiation** — real problem, separate concern, separate PR. Re-scope when auth is stable and the next UX pass begins.
- **Alerting/monitoring stack** — no existing alerting infrastructure to extend. Coolify healthcheck wiring (switching to `/api/health/anthropic`) is in scope; anything beyond that is a new initiative.
- **API key migration (Option A)** — explicitly deferred to SaaS launch. Re-scope trigger: first paying customer, or refresh token proves unreliable.
- **Credential proxy sidecar** — over-engineered for solo operation. Re-scope if a second service needs Claude auth.
- **Status dashboard page** — nice idea, not this epic. The healthcheck endpoint already exists; wiring it to Docker is sufficient for now.
- **Structured logging overhaul** — the stdout-in-errors fix is in scope; broader logging instrumentation is not.