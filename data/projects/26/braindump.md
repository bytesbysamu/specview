# SaaS Phase 1: Security + Auth Completion

> **Priority**: P1 — hard launch gate. Can't accept real users with hardcoded secrets and no signup.
> **Effort**: ~3 days.
> **Blocks**: Phase 2 (billing needs user signup), Phase 4 (onboarding needs auth pages).
> **Depends on**: P0 auth reliability (credential persistence) — must be stable before adding users.

## What this is

Complete the auth system that already exists and close the security holes that would be showstoppers for any external user. This is not a new auth system — it's finishing the one that's 70% built.

---

## Current State (fact-checked 2026-05-12)

**What exists and works:**
- `api/modules/auth/models.py` — `User` model with `id`, `auth_user_id` (nullable), `email`, `password_hash`, `plan`, `created_at`
- `api/modules/auth/service.py` — bcrypt hashing (`hash_password`, `verify_password`), HS256 JWT (`create_token`, `verify_token`), 72-hour expiry
- `api/modules/auth/routes.py` — `POST /api/auth/login` (email + password → JWT), `GET /api/auth/me` (returns user)
- `api/modules/auth/decorators.py` — `@require_auth` decorator with `SKIP_AUTH` bypass for dev
- `web-ng/src/app/services/auth.service.ts` — `login(email, password)`, stores JWT in localStorage as `specview_jwt`, `isLoggedIn` signal
- Database: `user` table exists in Neon Postgres via Alembic migration `0001_initial_schema.py`

**What's missing:**
- No `POST /api/auth/register` endpoint — can't create new users
- No password reset flow — locked out users stay locked out
- No Angular auth interceptor — Bearer token stored but not auto-attached to API requests
- `DATABASE_URL` hardcoded in `docker-compose.yml` line 28: `postgresql://neondb_owner:npg_7koHUOnPFp3E@...`
- `JWT_SECRET` hardcoded in `docker-compose.yml` line 29: `ef65adfbc50572d85b346a0cb5791ccc577fd4ec6a91a018a5b994a92ff40405`
- `CORS_ORIGINS` set to `"*"` in docker-compose.yml
- No security headers (X-Content-Type-Options, X-Frame-Options, HSTS)

**Decision: stay with bcrypt/HS256.** The legacy braindumps proposed Supabase magic-link auth. That's wrong for the current codebase — bcrypt/HS256 is already built, tested, and deployed. Adding Supabase means ripping out working code and adding a new external dependency. Complete what's here.

---

## Task 1 — Signup Endpoint

> **Effort**: 0.5 days

Add `POST /api/auth/register` to `api/modules/auth/routes.py`.

```python
@auth_bp.post("/register")
def register():
    """POST /api/auth/register — {email, password} → {token, email}."""
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    with Session(get_engine()) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            return jsonify({"error": "email already registered"}), 409

        user = User(email=email, password_hash=hash_password(password))
        session.add(user)
        session.commit()
        session.refresh(user)

    token = create_token(user.id, user.email)
    return jsonify({"token": token, "email": user.email}), 201
```

Angular: add signup form page, call `POST /api/auth/register`, store returned JWT same as login.

Rate limit: add basic rate limiting on register endpoint (e.g. 5 attempts per IP per hour) to prevent abuse.

### Out of scope
- Email verification — defer to Phase 4 onboarding. Signup works immediately for launch.
- Social login (Google, Apple) — not needed for web SaaS launch.

---

## Task 2 — JWT Expiry + Refresh

> **Effort**: 0.5 days

**Already done:** `service.py` already has `_JWT_EXPIRY_SECONDS = 72 * 3600` (72 hours) and includes `exp` in the payload. `verify_token` decodes with expiry validation by default.

**Remaining:**
- Add `POST /api/auth/refresh` endpoint that accepts a valid (not-yet-expired) JWT and returns a fresh one:

```python
@auth_bp.post("/refresh")
@require_auth
def refresh():
    user = g.current_user
    token = create_token(user.id, user.email)
    return jsonify({"token": token}), 200
```

- Angular: auto-refresh the token when it's within 1 hour of expiry (check on each API response).

---

## Task 3 — Angular Auth Interceptor

> **Effort**: 0.5 days

The `auth.service.ts` stores the JWT but no interceptor attaches it. Every API call that hits `@require_auth` will fail with 401 unless the caller manually adds the header.

```typescript
// auth.interceptor.ts
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getStoredJwt();
  if (token && req.url.startsWith('/api/')) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }
  return next(req);
};
```

Register in `app.config.ts`:
```typescript
provideHttpClient(withInterceptors([authInterceptor]))
```

Also handle 401 responses globally — clear token and redirect to login.

---

## Task 4 — Secrets Out of docker-compose.yml

> **Effort**: 0.5 days

**Current state (security risk):**
```yaml
# docker-compose.yml line 28-29 — COMMITTED TO GIT
DATABASE_URL: "postgresql://neondb_owner:npg_7koHUOnPFp3E@ep-lively-feather-agg1dzjp-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"
JWT_SECRET: "ef65adfbc50572d85b346a0cb5791ccc577fd4ec6a91a018a5b994a92ff40405"
```

**Fix:**
1. Replace hardcoded values with env substitution:
```yaml
DATABASE_URL: ${DATABASE_URL}
JWT_SECRET: ${JWT_SECRET}
```

2. Move real values to `.env` (already gitignored) and Coolify env vars for production.

3. Update `.env.example` with placeholder values:
```
DATABASE_URL=sqlite:///./spec_doc.db
JWT_SECRET=dev-secret-change-in-prod
```

4. Generate a new random JWT_SECRET for production (the current one may be compromised since it's in git history):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

5. Rotate the Neon database password since it's been committed.

---

## Task 5 — CORS Lockdown + Security Headers

> **Effort**: 0.5 days

**CORS:**
```yaml
# docker-compose.yml
CORS_ORIGINS: "https://specview.app,https://www.specview.app"

# docker-compose.override.yml (local dev)
CORS_ORIGINS: "http://localhost:8095,http://localhost:4200"
```

**Security headers** — add to Flask via `after_request`:
```python
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

Content-Security-Policy for the SPA: defer to Phase 4 (needs careful tuning for inline styles/scripts).

---

## Task 6 — Password Reset (Optional for Launch)

> **Effort**: 1 day
> **Verdict**: defer to post-launch unless signup volume is high enough that lockouts become a support burden.

If implemented:
- `POST /api/auth/forgot-password` — sends reset email with time-limited token
- `POST /api/auth/reset-password` — validates token, updates password_hash
- Requires email infrastructure (Resend, Postmark, or SES)
- Angular: forgot password page, reset password page

---

## Files to Change

| File | Change |
|------|--------|
| `api/modules/auth/routes.py` | Add `/register` and `/refresh` endpoints |
| `api/modules/auth/service.py` | No change needed — already complete |
| `web-ng/src/app/services/auth.service.ts` | Add `register()` method |
| `web-ng/src/app/auth.interceptor.ts` | New — attach Bearer token to all /api/ requests |
| `web-ng/src/app/app.config.ts` | Register interceptor |
| `docker-compose.yml` | Replace hardcoded secrets with `${VAR}`, add security headers |
| `docker-compose.override.yml` | CORS origins for local dev |
| `.env` | Move secrets here |
| `.env.example` | Placeholder values for dev |
| `api/create_app.py` | Add security headers via after_request |

## Success Criteria

- [ ] New user can register via `POST /api/auth/register` and receive a JWT
- [ ] Angular auth interceptor attaches Bearer token to all API requests
- [ ] JWT has 72-hour expiry, refresh endpoint extends the session
- [ ] `DATABASE_URL` and `JWT_SECRET` not in any committed file
- [ ] CORS rejects requests from origins other than specview.app (production) or localhost (dev)
- [ ] Security headers present on all responses
- [ ] Neon database password rotated

---

## Braindump

### 1. Key Themes

"Finish, don't reinvent" is the entire philosophy. The most important decision in this doc is the one that's almost buried: rejecting Supabase magic-link auth in favor of completing bcrypt/HS256. This is a maturity signal. The temptation to rip-and-replace working infrastructure with a shinier dependency is the single most common way early SaaS projects stall. The 70%-done framing is doing real work here — it reframes the remaining effort as completion, not construction.

Security debt is being treated as a launch gate, not a backlog item. Hardcoded secrets in git history, wildcard CORS, missing security headers — these are typically the things teams say "we'll fix later" and never do. Elevating them to P1 blocking status is the right call, but it also means the team has to actually follow through on credential rotation, not just env-var substitution.

The Angular frontend is the silent bottleneck. Three of six tasks require Angular changes (signup form, interceptor, token refresh logic). The backend work is straightforward CRUD. The real integration risk is in the frontend: interceptor registration, 401 handling, auth state management across the app, and making sure the signup UX doesn't feel like an afterthought.

Email infrastructure is being deferred, and that's a ticking clock. Password reset is "optional for launch," but so is email verification. That means the system will accept any string that looks like an email with zero validation that the human controls it. This is fine for a soft launch but becomes a real problem the moment someone typos their email and can't recover their account.

The 3-day estimate is aggressive but achievable — if there are no surprises in the Angular build pipeline. The backend tasks are well-scoped. The risk is entirely in frontend integration and environment configuration across dev/staging/production.

### 2. Hidden Connections

Credential rotation and the JWT secret are the same problem. Rotating the Neon password and generating a new JWT secret are listed as separate line items, but they share a deeper issue: every JWT ever issued with the old secret is still valid until expiry. Rotating the secret effectively logs out every existing user. If there are any active sessions (even test accounts), this needs to be coordinated — not just run as a one-liner.

The auth interceptor and the refresh logic are tightly coupled but specified separately. The interceptor attaches tokens; the refresh logic checks expiry on responses. These need to be built as a single unit. If the interceptor fires, gets a 401, and the refresh handler also fires, you get a race condition. The interceptor should own the entire lifecycle: attach → detect expiry → refresh → retry → or redirect to login.

Rate limiting on /register and the absence of email verification create a spam vector. Without email verification, an attacker can register thousands of accounts with fake emails. Rate limiting by IP helps, but any attacker behind a VPN rotation or botnet bypasses it trivially. The real mitigation is either email verification (deferred) or a CAPTCHA (not mentioned at all).

CORS lockdown and the auth interceptor solve different halves of the same trust problem. CORS prevents unauthorized origins from making requests; the interceptor ensures authorized origins send credentials. But if CORS is locked to specview.app and the interceptor only fires for /api/ paths, what happens with any non-/api/ endpoints? Is there anything served outside that prefix that needs protection?

The SKIP_AUTH bypass in the decorator is a security hole hiding in plain sight. It's mentioned as existing functionality but not listed as something to remove or gate behind NODE_ENV. If SKIP_AUTH is an environment variable and it leaks into production, the entire auth system is worthless.

### 3. Open Questions

**What happens to the git history containing the hardcoded secrets?**
- Option A: Accept that the secrets are in history, rotate all credentials, and move on. The old values become useless.
- Option B: Use git filter-branch or BFG Repo-Cleaner to scrub history, then force-push.
- Option C: Rotate credentials AND scrub history for defense-in-depth.
- Recommended: Option A. History scrubbing is fragile, breaks clones, and the credentials are about to be rotated anyway. Rotation is the real fix; scrubbing is theater.

**Should the SKIP_AUTH dev bypass be removed or environment-gated before launch?**
- Option A: Remove it entirely — devs use real auth locally.
- Option B: Gate it behind FLASK_ENV=development so it can never fire in production.
- Option C: Leave it as-is and rely on deployment config to not set the flag.
- Recommended: Option B. Removing it entirely adds friction to local dev that slows everyone down. Gating it behind FLASK_ENV is a one-line change that eliminates the production risk.

**How should the Angular app handle the "logged in but token expired" state during the refresh window?**
- Option A: Optimistic — queue failed requests, refresh token, replay them automatically.
- Option B: Simple — on any 401, clear token, redirect to login, user re-authenticates.
- Option C: Proactive — check token expiry before each request, refresh preemptively if within 1 hour.
- Recommended: Option C with Option B as fallback. Proactive refresh avoids user-visible failures. But if the proactive check misses (clock skew, server-side revocation), the 401 handler cleans up gracefully.

**Is localStorage the right storage mechanism for the JWT, given XSS risk?**
- Option A: Keep localStorage — simple, already implemented, and XSS is mitigated by CSP (coming in Phase 4).
- Option B: Switch to httpOnly cookies — immune to XSS but requires backend changes for CSRF protection.
- Option C: Use sessionStorage — same XSS risk as localStorage but tokens don't persist across tabs.
- Recommended: Option A for now. Switching to httpOnly cookies mid-stream adds CSRF complexity that bloats a 3-day sprint. CSP in Phase 4 is the real XSS mitigation. Revisit cookie-based auth if the threat model changes.

**What's the plan for the auth_user_id nullable field on the User model?**
- Option A: It's a vestige of the Supabase plan — drop it in a migration.
- Option B: Keep it for future external auth provider integration (Google SSO, etc.).
- Option C: Ignore it — nullable fields don't hurt anything.
- Recommended: Option C for this phase, Option A in Phase 4 cleanup. Don't spend migration effort now, but don't build anything new on top of a field that has no purpose.

### 4. Ideas to Explore

- **Add a "canary" health check that fails if SKIP_AUTH is enabled.** Create a /api/health/security endpoint that returns 503 if any dev-bypass flags are active. Wire it into your deployment pipeline so production deploys fail-fast if someone misconfigures the environment.

- **Implement account lockout after N failed login attempts before you implement password reset.** Without password reset, lockout is a denial-of-service against your own users. But without lockout, brute-force is trivial. The pragmatic middle: lock for 15 minutes after 10 failures, log the event, and unlock automatically. No email needed.

- **Build the interceptor as a token-lifecycle service, not just a header-attacher.** Have it own: token storage, expiry checking, refresh orchestration, 401 handling, and logout. The interceptor function itself becomes a thin wrapper around this service. This makes it testable and prevents the auth logic from scattering across components.

- **Add a one-time "rotate secrets" migration script** that coordinates JWT secret rotation with user session invalidation. Don't just swap the secret and hope — build a script that: generates a new secret, updates the env var, and logs a warning that all active sessions will be invalidated. If you ever need to rotate again (breach response), you want this to be a single command, not a wiki page.

- **Ship a minimal CAPTCHA on the register endpoint instead of relying solely on IP rate limiting.** Turnstile (Cloudflare) is free, privacy-respecting, and takes ~30 minutes to integrate. It's a better spam defense than IP-based rate limiting and buys time before email verification is built.

- **Add an X-Request-ID header in the security headers middleware.** You're already touching after_request — adding a UUID request ID costs nothing and makes debugging auth failures across frontend/backend dramatically easier. Especially valuable when you're about to onboard real users who will file bug reports like "it doesn't work."

- **Write a pre-commit hook that greps for known secret patterns** (Neon connection strings, hex tokens > 32 chars) and blocks the commit. The horse is already out of the barn for the current secrets, but this prevents the next developer from making the same mistake. Tools like detect-secrets or gitleaks do this out of the box.

- **Consider adding a /api/auth/me response that includes token_expires_at as an ISO timestamp.** The Angular app currently has to decode the JWT client-side to check expiry. Returning the expiry in the /me response (which is likely called on app init) gives the frontend a clean, decode-free way to schedule refresh.
