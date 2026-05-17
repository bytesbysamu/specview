# 🔍 SaaS Phase 3: Reliability + Observability — Analysis

## The Problem
Specview's 10-25 minute AI pipeline has no recovery path — a failure at minute 20 costs the user everything. Observability infrastructure exists but is half-wired: backend Sentry captures errors without user context, frontend Sentry isn't initialized, and health probes return hardcoded "skipped". There's no cancel, no retry, and no progress visibility.

## Hard Constraints
- Solo dev, ~2 days budget — scope must be ruthlessly held
- Phase 1 auth interceptor must be landed (Sentry user scoping depends on `g.current_user`)
- Phase 2a project isolation must be landed (per-user job scoping for retry/cancel)
- Sentry free tier: 5K errors/month — no room for noisy or duplicate reports
- No Redis, no SSE — progress feedback must work over existing 3s polling
- Claude Max quota is real cost — retry must replay *one* step, not three

## Open Questions
- **`WorkflowExecution.request_cancel()` — does it exist or not?** Brain dump says "may exist." If it doesn't, cancel is a build, not a wiring task. Verify before estimating → changes the 2-day budget
- **Docker healthcheck hitting `/api/health/anthropic` every 60s** — that's a real `count_tokens` API call. Does Claude Max count health checks against quota? If yes, use `/api/health` for liveness + a separate readiness probe. If no, proceed as described
- **How is `APP_RELEASE` set?** Docker build arg? Git SHA baked at image build? Runtime `git rev-parse`? Needs a one-line decision before implementation
- **Streaming partials — in or out?** Detailed design exists but it's tagged "stretch." Either cut it cleanly or commit it. Leaving it ambiguous guarantees it inflates day 2
- **Frontend Sentry is described as missing but no web-ng files are in the files-involved list.** Is Angular SDK integration in this phase or deferred?

## Dependencies & Sequencing
- Sentry user scoping is blocked by Phase 1 `@require_auth` decorator being landed
- Retry/cancel endpoints are blocked by Phase 2a job isolation (otherwise one user could cancel another's job)
- Health probes (Neon, Stripe) are independent — can ship first, unblock Docker healthcheck fix
- Cancel depends on confirming `request_cancel()` exists in the runtime
- Retry depends on understanding the exact step outputs that feed into subsequent steps (data shape)

## Explicitly Out of Scope
- **Streaming partials** — tagged stretch, has no success criterion, and the polling UX already exists. Trigger to re-scope: if user complaints about "blind waiting" appear post-launch
- **E2E retry scenario** — hedged language ("consider adding"), mock provider may not support it. Unit + integration coverage is sufficient for a P2
- **Alerting rules / PagerDuty** — zero users doesn't justify alert routing. Re-scope when paying users exist
- **Testing section claims "Phase 3 established 146 tests"** — this *is* Phase 3. That baseline belongs to Phase 2; fix the reference, don't re-derive coverage targets here

---
> **Cross-references:** [Epic](epic.md) · [Solution Architecture](architecture.md) · [Implementation Guide](guides/phase-3-reliability.md) · [Timeline](timeline.md)