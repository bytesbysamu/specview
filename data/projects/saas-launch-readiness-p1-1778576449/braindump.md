# Specview SaaS Launch Readiness

> **Priority**: P1 — the checklist that ties all phases together.
> **Effort**: ~1 day (verification + gap-filling, not greenfield).
> **Depends on**: Phase 1 (auth), Phase 2a (isolation), Phase 2b (billing UI). Phase 3 (reliability) and Phase 5 (git storage) are nice-to-have but not blocking.

## The problem

Specview has been built phase by phase — auth, project isolation, billing, observability, git storage — each as a separate spec and branch. But nobody has verified the full end-to-end flow from "stranger lands on specview.app" to "paying Pro user generating specs." There are likely integration gaps between phases, missing environment config, untested edge cases in the flow transitions, and operational basics (domain, SSL, ToS, error pages) that don't belong in any specific phase.

This braindump is the launch verification layer — it catches everything that falls between the cracks.

---

## Current state (fact-checked 2026-05-13)

**Phase status:**
- Phase 1 (auth): Specced + impl guide + in progress on `feat/saas-phase1-security-auth`. JWT auth (bcrypt, HS256, 72h), login/register/refresh/me endpoints, `@require_auth` decorator, Angular auth interceptor, token lifecycle service with proactive refresh.
- Phase 2a (isolation): Braindump written, pending spec pipeline. ProjectRepository protocol exists, SQL implementation not wired.
- Phase 2b (billing UI): Braindump written, pending spec pipeline. Backend billing module complete, no frontend components.
- Phase 3 (reliability): Braindump written, pending spec pipeline. Observability infrastructure built but not activated.
- Phase 5 (git storage): Braindump written, pending spec pipeline. git_store module exists, not wired into routes.

**What's NOT covered by any phase:**
- Full end-to-end smoke test: signup → create project → paste braindump → generate specs → hit free limit → upgrade → generate as Pro
- Environment parity: local dev vs Coolify production — env vars, volumes, networking
- Domain + SSL: specview.app DNS, certificate, Traefik routing
- Legal: Terms of service, privacy policy (required for Stripe)
- Error pages: 404, 500, maintenance mode — currently shows raw JSON or Angular default
- Analytics: basic product analytics (who signed up, who generated, who paid) — currently zero visibility
- Email: transactional emails (welcome, payment confirmation, payment failed) — currently none
- Rate limiting: IP-based rate limiting on public endpoints (login, register) to prevent brute force. The auth routes have `@ip_rate_limit` but need to verify it's properly configured.
- CORS: Phase 1 should lock this down, but need to verify the production origin list is correct after deployment.
- Mobile responsiveness: the newspaper grid was designed desktop-first. How does it look on mobile? Is it usable?

---

## Learnings from other projects

**Springular (shipped SaaS):**
Has a documented launch checklist in its README. Key items specview is missing: email notification templates (checkout success, payment failed with portal retry link, subscription canceled), Swagger/OpenAPI docs exposed for API consumers, and a `/health` composite endpoint that aggregates all dependency probes into a single status. Also has environment-specific config files (`application-dev.yml`, `application-prod.yml`) which prevents env var drift between local and production.

**Trendfy (shipped in 4 days):**
Lean launch: domain on Coolify, Stripe in test mode for first 48 hours, switched to live after manual verification. No analytics at launch — added PostHog after first 10 users. No email beyond Stripe's built-in receipts. Lesson: don't block launch on analytics or email — those can be added in week 1. Do block on: auth works, payments work, user data is isolated.

**Bubls:**
Had a painful launch where the RevenueCat entitlement sync had a race condition that wasn't caught in testing. The fix was simple but the debugging took hours because there was no structured logging of the sync flow. Lesson: make sure the critical paths (auth → billing → access control) have structured log events at each transition, so when something breaks you can trace the full flow in logs.

---

## Architecture direction

**End-to-end verification script or manual checklist.** Not automated E2E tests (those are in Test Phase 2), but a manual launch-day checklist: sign up as a new user, verify email appears in DB, create project, paste braindump, trigger generation, verify it completes, verify usage counter increments, trigger enough generations to hit free limit, verify 429 and upgrade page, complete Stripe checkout, verify webhook flips plan to Pro, verify usage limit is bypassed.

**Environment config audit.** Document every env var required for production, verify each is set in Coolify, verify no secrets are in docker-compose.yml or committed to git. Create a `.env.example` with all required vars and descriptions.

**Legal minimum.** Terms of service and privacy policy pages — can be simple markdown rendered by the landing page. Required by Stripe for live mode. Link from the footer of both landing page and app.

**Error pages.** Custom 404 and 500 pages in the Angular app. The Flask API already has JSON error handlers, but the SPA needs to catch and display them gracefully.

**Post-launch monitoring.** Sentry for errors (Phase 3), structlog for request tracing (already wired), Stripe dashboard for revenue. Analytics (PostHog or similar) is week-1, not launch-day.

---

## Testing baseline to maintain

This project is primarily verification, not new code. But any gap-filling code (error pages, rate limit config, CORS lockdown) must maintain the existing testing baseline:

- 146 frontend tests across 9 spec files — run `ng test --watch=false` before and after any changes
- Backend pytest suite — run `pytest api/` to verify nothing broke
- E2E scenarios in `e2e/features/` — run against docker compose with `CHAIN_PROVIDER=mock`
- Any new Angular components (error pages) need basic component tests
- The end-to-end verification checklist itself becomes a reference document for future deployments

---

## Launch checklist (verification, not implementation)

These are the items to verify on launch day, not items to build (building happens in the phase projects):

- Auth flow: register → login → token refresh → logout works end-to-end
- Project isolation: new user sees only their own projects, cannot access others by ID
- Billing: free tier → hit limit → 429 → upgrade → Stripe checkout → webhook → Pro access
- Usage metering: counter increments on generation, resets at midnight UTC, Pro bypasses
- Health probes: `/api/health/anthropic`, `/api/health/neon`, `/api/health/stripe` all return ok
- Sentry: trigger an error, verify it appears in Sentry dashboard with user context
- Domain: specview.app resolves, SSL valid, Traefik routes correctly to web/api/landing
- Legal: ToS and privacy policy pages accessible from footer
- Stripe: live mode keys configured, webhook endpoint verified, test purchase completes
- Secrets: no hardcoded secrets in docker-compose or committed code
- CORS: only production origins allowed
- Mobile: app is usable on mobile viewport (may be degraded, not broken)
