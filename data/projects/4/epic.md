# 🎯 Epic: Auth Reliability & Credential Persistence

## Business Value

The spec-doc API is unusable as a production tool. Every ~26 hours the Claude CLI OAuth token expires, every AI feature returns a generic 502, and the only recovery path is a manual keychain extraction plus container restart. This is not a background annoyance — it is a hard blocker for daily use and an absolute blocker for any future paying customer. A SaaS product that silently breaks overnight and requires SSH access to fix is not a product.

Fixing auth reliability converts spec-doc from a tool that works when attended into one that runs unattended for weeks. This is the minimum bar for production — not a feature, but a prerequisite. Every hour of AI downtime is an hour where the entire product value proposition (AI-powered spec generation) is zero. For a solo founder, that's also an hour of context-switching from building features to fighting infrastructure.

The chosen approach (persistent CLI session via Docker volume) preserves the Claude Max flat-rate cost model, which is the only financially viable path pre-revenue. API key billing is deferred to SaaS launch when per-user cost tracking justifies per-token pricing. Solving this now means auth stops being a daily tax on development velocity and becomes a problem revisited quarterly at most.

## Scope

### What This Epic Covers

- **CLI error signal recovery** — Surface the actual auth error message (currently swallowed because CLI writes to stdout, not stderr) so future failures are diagnosable in seconds, not hours
- **Persistent credential volume** — Named Docker volume for `~/.claude/` so CLI-managed tokens survive container restarts and full teardowns
- **Seed-only-once entrypoint guard** — Prevent `entrypoint.sh` from overwriting CLI-refreshed credentials on every boot
- **Environment variable cleanup & container login** — Remove `ANTHROPIC_CLI_KEY` (which forces `--bare` mode and bypasses the credential file entirely), establish a persistent CLI session via interactive login
- **Docker healthcheck wiring** — Switch from process-level healthcheck to `/api/health/anthropic` so auth failures surface in `docker ps` and Coolify's health dashboard

### What This Epic Does NOT Cover

- ❌ **Frontend error differentiation** — The frontend shows a generic "Could not reach AI" for all failure types. Real problem, but a separate UX concern for a separate PR. Re-scope when auth is stable.
- ❌ **API key migration (Option A)** — Per-token billing is not viable pre-revenue. Re-scope trigger: first paying customer or proven refresh-token unreliability.
- ❌ **Alerting & monitoring stack** — No existing alerting infrastructure to extend. Healthcheck visibility in Docker/Coolify is sufficient for a solo operator. Re-scope when there's a second team member or an uptime SLA.
- ❌ **Credential proxy sidecar** — Over-engineered for a single service operated by one person.
- ❌ **Status dashboard page** — The healthcheck endpoint provides the signal; a dedicated UI is a nice-to-have, not a reliability fix.
- ❌ **Structured logging overhaul** — The stdout-in-errors fix is in scope; broader logging instrumentation is a separate initiative.

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **CLI Error Signal Recovery** — Include stdout in error messages on non-zero exit; detect 401/auth keywords and raise with correct status code | None | Yes (with #2) | 0.5 days | High |
| 2 | **Credential Volume & Entrypoint Guard** — Add named volume for `~/.claude/` in both compose files; update `entrypoint.sh` to skip credential write when file already exists | None | Yes (with #1) | 0.5 days | High |
| 3 | **Environment Cleanup & Container Auth Session** — Remove `ANTHROPIC_CLI_KEY` and `CLAUDE_CREDENTIALS_JSON` from env config; run `claude login` inside container; validate generation survives restart and full teardown | #1, #2 | No | 1 day | High |
| 4 | **Docker Healthcheck & Deploy Docs** — Update `/api/health/anthropic` to validate via CLI when `CHAIN_PROVIDER=cli` and no API key is set (currently returns `"skipped"`); wire as Docker healthcheck target; document VPS login procedure and force-re-seed escape hatch in `DEPLOY.md` | #3 | No | 0.5 days | High |

## Success Criteria

- ✅ `docker compose restart api` preserves credentials — generation works without re-login
- ✅ `docker compose down && docker compose up -d` preserves credentials — named volume survives full teardown
- ✅ CLI auth failure surfaces the actual error message (e.g., `401 Invalid authentication credentials`), not empty stderr
- ✅ `docker ps` shows unhealthy status within 120 seconds when auth credentials are invalid
- ✅ No manual credential refresh required for at least 14 consecutive days
- ✅ All changes validated locally via `docker compose` before merge to master
- ✅ Force re-seed escape hatch documented and tested (volume deletion → entrypoint re-seeds → re-login)

## Related Documents

- [Analysis](./analysis.md) — Root cause investigation, incident log, and corrected mental model of the auth flow
- [Solution Architecture](./architecture.md) — Volume mount design, entrypoint logic, and environment variable changes
- [Timeline](./timeline.md) — Task status and completion tracking