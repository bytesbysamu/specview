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
