# 🏗️ Solution Architecture: SaaS Phase 1 — Security + Auth Completion

## Architecture Overview

This phase completes an auth system that is seventy percent built, not constructing a new one. The existing stack — bcrypt password hashing, HS256 JWT issuance, a `@require_auth` decorator, and an Angular auth service with localStorage token storage — forms a functional but disconnected set of parts. The architecture challenge is wiring them into a closed loop where a user can go from stranger to authenticated session holder without manual database inserts, without leaking credentials, and without the frontend silently dropping auth headers.

The key architectural insight is that the token lifecycle is a single concern that must not be split across components. The braindump correctly identified that building the HTTP interceptor separately from the refresh logic invites race conditions: a 401 triggers a retry, the retry triggers another refresh, and concurrent requests stampede into the refresh endpoint. The solution is a token-lifecycle service on the Angular side that owns storage, expiry detection, refresh orchestration, and failure-mode routing. The interceptor itself is a thin wrapper that delegates every decision to this service. On the backend, the work is straightforward CRUD behind the existing thin-HTTP-layer pattern.

The second organizing principle is that secrets management and transport security are not afterthoughts bolted on at the end — they are the first task executed because every subsequent task depends on a clean environment. Rotating the JWT secret invalidates every existing session. That must happen before new users can register, not after.

## Design Principles

| Principle | Application in This Phase |
|-----------|---------------------------|
| P1 — Adapter Boundary | Auth service functions (hashing, token creation, verification) remain the sole boundary for cryptographic operations. No route handler calls bcrypt or jwt directly. |
| P2 — Thin HTTP Layer | `/register` and `/refresh` route handlers validate input and delegate to `service.py`. No business logic in `routes.py` — duplicate-email detection, password policy enforcement, and token generation all live in the service layer. |
| P4 — No Speculative Abstractions | No generic "auth provider" abstraction. bcrypt/HS256 is the only provider. No base class, no registry, no strategy pattern. If a second auth method arrives later, refactor then. |
| P5 — Contract-First | The `/register` and `/refresh` endpoints mirror the existing `/login` response shape (`{token, email}`) so the Angular app can reuse the same post-auth flow. |
| P7 — File Size & Structure | The interceptor, token-lifecycle service, and signup page each get their own file. No auth god-file. `routes.py` stays under 200 lines by keeping validation logic in the service layer. |

## Component Design

### Secrets Management Layer

**Purpose**: Eliminate hardcoded credentials from version-controlled files and ensure rotated values have never existed in git history.

The current `docker-compose.yml` contains both `DATABASE_URL` and `JWT_SECRET` as plaintext string values. These are not merely "best practice" violations — the Neon database password and the JWT signing key are actively compromised. Anyone with read access to the git repository can authenticate as any user and connect directly to the production database.

The architectural pattern is environment-variable injection with three tiers: `.env` for local development (already gitignored), `docker-compose.yml` using variable substitution syntax for container orchestration, and Coolify's environment variable panel for production. The `.env.example` file provides placeholder values that make the local setup self-documenting without exposing real credentials.

Rotation order matters. The JWT secret must rotate first because it invalidates all active sessions. The Neon password rotates second because it requires coordination with the Neon console. Both rotations happen before any new endpoints are deployed, ensuring that the registration endpoint never issues tokens signed with a compromised secret.

A pre-commit grep guard should be added to `.pre-commit-config.yaml` to prevent future credential leaks. This is not defense-in-depth theater — it is a concrete prevention mechanism for a mistake that has already occurred once.

### Registration Service

**Purpose**: Allow new users to create accounts and receive a JWT without manual database insertion.

The registration flow follows the same thin-HTTP-layer pattern as the existing login endpoint: the route handler in `api/modules/auth/routes.py` accepts email and password, delegates to service functions in `api/modules/auth/service.py` for validation and persistence, and returns a token on success. The service layer handles email normalization (lowercase, trim), password policy enforcement (minimum eight characters), and duplicate detection via a database query before insert.

The response shape mirrors the login endpoint — a JSON object containing `token` and `email` — so the Angular app can use the same post-authentication flow for both login and registration. This is a deliberate design choice: the frontend auth service stores the token and updates its `isLoggedIn` signal identically regardless of whether the session originated from login or signup.

The Angular signup page lives as a standalone component with its own route. It shares no template with the login page because the UX copy, validation messaging, and error states are different enough that a shared component would require more conditional logic than two simple forms.

### Abuse Mitigation Strategy

**Purpose**: Compensate for the absence of email verification by making bulk fake-account creation expensive.

Without email verification, the registration endpoint accepts any syntactically valid email string with no proof of ownership. This is an acceptable trade-off for launch — email infrastructure is Phase 4 scope — but it creates a spam vector that must be narrowed.

The mitigation is two layers. The first layer is IP-based rate limiting on the `/register` endpoint only, scoped to five requests per IP per hour. This is implemented as a decorator using an in-process dictionary with timestamp-based sliding windows, consistent with the P4 principle of no external dependencies (no Redis, no rate-limiting service). The single-worker gunicorn configuration means in-process state is reliable.

The second layer is Cloudflare Turnstile, a free, privacy-respecting challenge mechanism. Turnstile is preferred over reCAPTCHA because it does not require user interaction in most cases (invisible challenge) and aligns with the existing Cloudflare infrastructure that fronts `specview.app`. The Turnstile token is validated server-side before the registration logic executes, making it a pre-auth gate rather than a post-auth check. If Turnstile integration proves complex within the time budget, IP rate limiting alone ships first and Turnstile follows as a fast-follow.

### Token Lifecycle Service

**Purpose**: Own the entire JWT lifecycle on the Angular side — storage, attachment, expiry detection, refresh orchestration, and failure routing — as a single cohesive unit.

The existing interceptor (`web-ng/src/app/interceptors/auth.interceptor.ts`) already handles two of the four responsibilities: it attaches Bearer tokens to `/api/` requests and catches 401 responses by calling `auth.signOut()`. It also maintains a `PUBLIC_PATHS` allowlist (currently just `/api/auth/login`) to avoid signing out on expected 401s. This is a solid foundation — the remaining work is adding refresh orchestration and proactive expiry checking.

The design introduces a dedicated Angular service (`token-lifecycle.service.ts`) that takes over token storage and adds two new responsibilities. First, expiry awareness: decoding the JWT payload client-side to extract the `exp` claim, then comparing against the local clock. Second, refresh orchestration: when the token is within one hour of expiry, the service proactively calls `POST /api/auth/refresh` and swaps the stored token. A mutex flag ensures only one refresh is in-flight at a time — subsequent callers await the same refresh promise rather than issuing parallel requests.

The existing interceptor is then refactored to delegate to this service: it asks for the current valid token (which may trigger a proactive refresh), attaches it, and on 401 passes disposition to the service rather than calling `signOut()` directly. The `PUBLIC_PATHS` list gains `/api/auth/register` and `/api/auth/refresh`.

On the backend, `POST /api/auth/refresh` is a protected endpoint (requires a valid, non-expired token via `@require_auth`) that issues a fresh token with a new 72-hour expiry window. This is a sliding-window session model: as long as the user is active at least once every 72 hours, they stay authenticated. The trade-off is that a stolen token remains valid for up to 72 hours with no server-side revocation mechanism. Token revocation (via a database blacklist or Redis set) is deferred — the complexity is disproportionate to the threat model at current scale.

The `/api/auth/me` response should include `token_expires_at` as an ISO timestamp alongside the existing user fields. This gives the frontend a decode-free way to seed its expiry-awareness on app initialization without importing a JWT parsing library.

### Transport Security Layer

**Purpose**: Restrict which origins can make cross-origin requests and add standard security headers to all responses.

CORS configuration moves from the current wildcard (`"*"`) to an environment-driven allowlist. In production, only `https://specview.app` and `https://www.specview.app` are permitted. In local development, `http://localhost:4200` (Angular dev server) and `http://localhost:8095` (Docker web proxy) are permitted via `docker-compose.override.yml`. The CORS origins are read from the `CORS_ORIGINS` environment variable as a comma-separated string, parsed at app startup, and passed to the Flask-CORS extension. No fallback to wildcard — if the variable is missing, CORS rejects all cross-origin requests. Failing closed is the correct default.

Security headers are applied via a Flask `after_request` handler in `api/app.py` (or `create_app.py` if the factory pattern is in use). Three headers ship in this phase: `X-Content-Type-Options: nosniff` prevents MIME-type sniffing attacks, `X-Frame-Options: DENY` prevents clickjacking via iframe embedding, and `Strict-Transport-Security` with a one-year max-age enforces HTTPS on subsequent visits. `Content-Security-Policy` is explicitly deferred to Phase 4 because Angular SPAs generate inline styles and scripts that require careful CSP tuning — shipping a broken CSP is worse than shipping no CSP.

An `X-Request-ID` header should be added in the same `after_request` handler. The cost is negligible (one UUID generation per request) and the debugging value is significant: when onboarding real users, correlating a frontend error report to a backend log entry requires a shared identifier.

### SKIP_AUTH Environment Gate

**Purpose**: Ensure the development auth bypass cannot activate in production.

The existing `@require_auth` decorator checks for a `SKIP_AUTH` environment variable and bypasses authentication entirely when it is set. This is a valid development convenience — running the full auth flow on every local request slows iteration — but it is a critical vulnerability if the variable leaks into a production environment.

The fix is an environment gate: `SKIP_AUTH` is only honored when `FLASK_ENV` equals `development`. In any other environment (production, staging, or unset), the bypass is dead code regardless of whether `SKIP_AUTH` is present. This is preferred over removing the bypass entirely because it preserves developer velocity without creating production risk. The gate check happens inside the decorator itself, not in configuration, so there is exactly one place in the codebase where the decision is made.

A complementary measure is a `/api/health/security` canary endpoint that returns a 503 status if any dev-bypass flag is active. Wiring this into the Coolify deployment pipeline ensures that a misconfigured production environment fails fast at deploy time rather than silently serving unauthenticated requests.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Password hashing | bcrypt (existing) | Already implemented and deployed in `service.py`. Switching to Argon2 or scrypt offers marginal security improvement at the cost of ripping out working code. |
| Token format | HS256 JWT, 72-hour expiry | Already implemented. Symmetric signing is appropriate for a single-service architecture where the issuer and verifier are the same process. RS256 adds key-management complexity with no benefit until a second service needs to verify tokens. |
| Token storage (client) | localStorage | Already implemented. httpOnly cookies would eliminate XSS-based token theft but require CSRF protection middleware, adding scope to a 3-day sprint. CSP in Phase 4 is the planned XSS mitigation. |
| Rate limiting | In-process dictionary with sliding window | Consistent with the no-Redis constraint. Single gunicorn worker means no cross-process state issue. Sufficient for launch-scale traffic. |
| Bot mitigation | Cloudflare Turnstile (optional) | Free, invisible, privacy-respecting. Complements IP rate limiting without requiring email infrastructure. Degrades gracefully — if Turnstile is unreachable, IP limiting still applies. |
| CORS | Flask-CORS with env-driven allowlist | Already a dependency. Moving from wildcard to explicit origins is a configuration change, not a code change. |
| Security headers | Flask `after_request` handler | No additional dependency. Three headers, one handler, applied globally. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Complete bcrypt/HS256 instead of migrating to Supabase magic-link | 70% of the auth system already works. Supabase would require ripping out `service.py`, `routes.py`, and `auth.service.ts` — three working modules — and adding a new external dependency with its own failure modes. | No passwordless login. No delegated auth infrastructure. Password reset requires building email sending from scratch. |
| Rotate secrets rather than scrub git history | BFG Repo-Cleaner and `git filter-branch` break existing clones, invalidate CI caches, and require force-pushing to every remote. Rotation makes the leaked values useless regardless of whether they remain in history. | The old credentials remain visible in git log. Anyone who cloned the repo before rotation has the old values. Acceptable because the old values will be inert. |
| Proactive token refresh with 401 fallback | Proactive refresh (check expiry before each request, refresh if within one hour) avoids user-visible auth failures during normal use. The 401 fallback handles edge cases: clock skew, server-side secret rotation, or manual token deletion. | Client must decode the JWT to read `exp`, adding a soft dependency on JWT structure. Mitigated by also exposing `token_expires_at` in the `/me` response. |
| Single token-lifecycle service rather than distributed auth logic | Concentrating storage, refresh, and failure handling in one service eliminates race conditions and makes auth behavior testable in isolation. The interceptor becomes a stateless delegate. | All auth logic is coupled to one service. If the service has a bug, all authenticated requests fail. Acceptable because auth is inherently a single concern. |
| IP-based rate limiting in-process rather than via middleware or external service | No Redis, no external dependencies, single gunicorn worker. A module-level dictionary with timestamps is the simplest correct implementation. | Rate limits reset on server restart. Not shared across workers if scaling beyond one worker. Both are acceptable at launch scale. |
| Defer Content-Security-Policy to Phase 4 | Angular generates inline styles and uses dynamic script evaluation in development mode. A restrictive CSP would break the SPA without careful `nonce` or `hash` configuration. Shipping a permissive CSP (with `unsafe-inline`) provides false confidence. | No CSP protection against XSS until Phase 4. Mitigated by `X-Content-Type-Options: nosniff` and the plan to add CSP with proper Angular tuning. |
| Defer email verification to Phase 4 | No email infrastructure exists. Building transactional email (Resend, Postmark, or SES), verification token generation, and a confirmation flow is a multi-day effort that exceeds the 3-day budget. | Accounts can be created with unverifiable email addresses. Typo'd emails result in unrecoverable accounts. Turnstile and rate limiting reduce abuse but do not prevent it. |
| Defer account lockout until password reset exists | Lockout without reset is a self-denial-of-service. A locked-out user with no reset mechanism must contact the developer directly. | Brute-force login attempts are not throttled beyond whatever Cloudflare provides at the edge. Acceptable because the bcrypt cost factor makes brute-force computationally expensive regardless. |
| Keep `auth_user_id` nullable column | Dropping it requires a migration that adds risk for zero functional benefit. The column is a vestige of the abandoned Supabase plan and is not referenced by any active code. | Schema carries dead weight. Clean up in Phase 4 when other migrations are already planned. |
| Gate `SKIP_AUTH` behind `FLASK_ENV=development` rather than removing it | Removing the bypass adds auth friction to every local development session. Gating it is a one-line conditional that preserves developer velocity while eliminating production risk. | If `FLASK_ENV` is accidentally set to `development` in production, the bypass activates. Mitigated by the `/api/health/security` canary that fails the deploy check. |

## Auth Flow Topology

The authentication flow forms a closed loop across four components: the Angular SPA, the token-lifecycle service, the Flask auth module, and the Neon database.

**Registration flow**: The user submits email and password from the signup page. The Angular auth service sends the credentials to `POST /api/auth/register`. The Flask route handler delegates to the auth service layer, which normalizes the email, validates the password policy, checks for duplicate accounts against the database, hashes the password with bcrypt, inserts the user row, and generates a JWT. The token returns to the Angular app, where the token-lifecycle service stores it and updates the `isLoggedIn` signal. From this point, the user is in the same authenticated state as if they had logged in.

**Authenticated request flow**: On every HTTP request to an `/api/` path, the Angular HTTP interceptor asks the token-lifecycle service for the current token. The service checks expiry: if the token is valid and more than one hour from expiry, it returns the token immediately. If the token is within the refresh window, the service calls `POST /api/auth/refresh` (using the still-valid current token), stores the fresh token, and returns it. The interceptor attaches the token as a Bearer header. On the backend, `@require_auth` decodes and validates the token on every protected route.

**Failure flow**: If the token is expired and refresh fails, or if any request returns a 401 that the service cannot recover from, the token-lifecycle service clears localStorage, resets the `isLoggedIn` signal to false, and navigates to the login page. No error is shown to the user beyond the redirect — the login page itself communicates the required action.

## Deployment Considerations

Secrets are injected at three levels. Locally, `.env` contains development credentials (a local SQLite fallback for the database URL and a throwaway JWT secret). In Docker Compose, variable substitution references these values without hardcoding them. In Coolify production, environment variables are set through the dashboard and never touch a file that could be committed.

The single-worker gunicorn configuration (`--workers 1 --threads 4 --worker-class gthread`) is preserved. In-process rate-limiting state and background-job state both depend on a single process. If the application scales beyond one worker, rate limiting must move to an external store. This is an explicit, accepted constraint — not an oversight.

The `after_request` security headers handler must be registered in the app factory before the CORS middleware to ensure headers are present on CORS preflight responses. Order of middleware registration is the most common source of "headers missing on OPTIONS" bugs.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JWT secret rotation logs out all active test users mid-sprint | High | Low | Coordinate rotation as the first task. No real users exist yet — only developer test accounts that can re-authenticate immediately. |
| Angular interceptor registration order causes headers to be applied inconsistently | Medium | Medium | The interceptor must be the first in the `withInterceptors` array. Any logging or error-handling interceptors register after it. |
| Turnstile integration exceeds time budget | Medium | Low | Turnstile is scoped as optional. IP rate limiting ships regardless. Turnstile can follow as a same-week patch. |
| Clock skew between client and server causes premature or missed refresh | Low | Medium | The proactive refresh window (one hour) is deliberately wide. Even significant clock drift (minutes) falls well within the window. The 401 fallback catches any case the proactive check misses. |
| Password-less email typo creates unrecoverable accounts | High | Low at launch scale | Acceptable for soft launch with a small initial cohort. Email verification in Phase 4 resolves this permanently. A manual database fix is viable for the handful of cases expected before Phase 4. |

## Related Documents

- [Analysis](./analysis.md) — Problem identification, current-state audit, and open questions driving this architecture
- [Epic](./epic.md) — Scope boundaries, task breakdown, and success criteria
- [Timeline](./timeline.md) — Execution schedule and delivery tracking