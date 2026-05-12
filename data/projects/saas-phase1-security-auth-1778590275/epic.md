# 🎯 Epic: SaaS Phase 1 — Security + Auth Completion

## Business Value

spec-doc cannot accept paying users until signup exists and security holes are closed. The auth system is 70% built — bcrypt/HS256 login, JWT issuance, and a `@require_auth` decorator all work — but there is no registration endpoint, no way for the frontend to automatically attach tokens to requests, and production credentials are committed to git history in plaintext. Any external user who visits the app today hits a dead end: they can't create an account, and if they could, the system protecting their data has exploitable gaps.

This epic is the hard gate between "working demo" and "launchable product." Phase 2 (billing) requires user accounts to exist. Phase 4 (onboarding) requires auth pages to route through. Neither can begin until this phase ships. The 3-day budget reflects the reality that most of the infrastructure already exists — this is completion work, not construction.

The business case is binary: without this epic, spec-doc has zero addressable users. With it, the product can onboard its first cohort, validate pricing assumptions, and begin generating revenue. Every day this ships late is a day billing integration sits idle.

## Scope

### What This Epic Covers

- **User registration** — Backend endpoint and Angular signup page so new users can create accounts and receive a JWT without manual database insertion
- **Auth interceptor + token lifecycle** — Angular HTTP interceptor that auto-attaches Bearer tokens to API requests, proactively refreshes tokens nearing expiry, and handles 401 responses gracefully — built as a single unit to avoid refresh race conditions
- **Credential extraction** — Move `DATABASE_URL`, `JWT_SECRET`, and all secrets out of committed files into environment variables, rotate compromised credentials, and update deployment configuration
- **Transport security** — Lock CORS to production/dev origins, add standard security headers, and gate the `SKIP_AUTH` dev bypass behind `FLASK_ENV=development` so it cannot fire in production
- **Registration abuse mitigation** — Rate limiting on the signup endpoint and optionally Cloudflare Turnstile to compensate for the absence of email verification

### What This Epic Does NOT Cover

- ❌ **Email verification** — No email infrastructure exists; deferred to Phase 4 onboarding
- ❌ **Password reset** — Requires transactional email; deferred post-launch until lockout volume justifies the investment
- ❌ **Social login (Google/Apple)** — Unnecessary for web SaaS launch; revisit when signup friction data warrants it
- ❌ **Content-Security-Policy** — Requires careful SPA tuning for inline styles/scripts; Phase 4 scope
- ❌ **Git history scrubbing** — Credential rotation makes leaked values useless; scrubbing is fragile and breaks clones
- ❌ **Account lockout** — Dangerous without password reset (self-DoS risk); defer until reset flow exists
- ❌ **`auth_user_id` column cleanup** — Nullable vestige of the rejected Supabase plan; harmless, ignore until Phase 4

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Secrets Rotation & Env-Var Migration** — Extract `DATABASE_URL` and `JWT_SECRET` from `docker-compose.yml` into env vars, rotate the Neon database password, generate a new JWT secret, update `.env.example` with placeholders, and configure Coolify production env vars. Coordinate that secret rotation invalidates all existing sessions. | None | — | 0.5 days | High |
| 2 | **Signup Endpoint + Angular Registration Page** — Add `POST /api/auth/register` with input validation, duplicate-email detection, and rate limiting. Build the Angular signup form page and wire it to the auth service. Optionally integrate Cloudflare Turnstile for bot mitigation. | Task 1 | — | 1 day | High |
| 3 | **Token Lifecycle + Refresh** — Extend the existing Angular HTTP interceptor (which already attaches Bearer tokens and handles 401→signOut) with a token-lifecycle service that owns proactive expiry checking, refresh orchestration (mutex to prevent concurrent refreshes), and 401 fallback. Add `POST /api/auth/refresh` backend endpoint. Add `/register` to the interceptor's `PUBLIC_PATHS`. | Task 2 | — | 1 day | High |
| 4 | **CORS Lockdown, Security Headers & SKIP_AUTH Gating** — Restrict `CORS_ORIGINS` to `specview.app` in production and `localhost` in dev. Add `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security` headers via Flask `after_request`. Gate `SKIP_AUTH` behind `FLASK_ENV=development`. | Task 3 | — | 0.5 days | High |

## Success Criteria

- ✅ A new user can register with email and password via the Angular signup page and lands in an authenticated session
- ✅ The Angular HTTP interceptor attaches Bearer tokens to all `/api/` requests without manual header management in feature code
- ✅ Tokens refresh proactively before expiry; expired tokens trigger redirect to login — no user-visible errors during normal use
- ✅ `DATABASE_URL` and `JWT_SECRET` appear in zero committed files (verified by grepping the working tree)
- ✅ Neon database password and JWT signing secret are both rotated to values that have never been in git history
- ✅ CORS rejects requests from origins other than `specview.app` (production) or `localhost` (development)
- ✅ `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Strict-Transport-Security` headers present on all HTTP responses
- ✅ `SKIP_AUTH` bypass has no effect when `FLASK_ENV` is not `development`
- ✅ Registration endpoint rate-limited to prevent bulk fake-account creation

## Related Documents

- [Analysis](./analysis.md) — Problem identification and open questions driving this epic
- [Solution Architecture](./architecture.md) — Interceptor lifecycle design, secrets management pattern, and auth flow diagrams
- [Timeline](./timeline.md) — Execution status and schedule tracking