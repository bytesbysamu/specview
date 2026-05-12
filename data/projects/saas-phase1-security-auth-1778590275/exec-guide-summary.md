# exec-guide summary — SaaS Phase 1: Security + Auth Completion

**Date:** 2026-05-12
**Tasks run:** 4
**Tasks passed:** 4 / 4
**Tests:** passed (backend: modules/auth — 5 passed)
**Review:** 4 critical, 7 warnings

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Secrets Rotation & Env-Var Migration | ✓ complete | docker-compose.yml, .env, .env.example, .pre-commit-config.yaml |
| Task 2: Signup Endpoint + Angular Registration Page | ✓ complete | routes.py, service.py, rate_limit.py, auth.interceptor.ts, auth.service.ts, app.component.ts/html, app.config.ts, app.routes.ts, signup component |
| Task 3: Token Lifecycle + Refresh | ✓ complete | routes.py, service.py, token-lifecycle.service.ts, auth.interceptor.ts, auth.service.ts |
| Task 4: CORS Lockdown, Security Headers & SKIP_AUTH Gating | ✓ complete | create_app.py, decorators.py, docker-compose.yml, docker-compose.override.yml, .env.example |

## Test results

Backend: modules/auth — 5 passed, 0 failed

## Review findings

### Critical (must fix before merge)

1. **routes.py:72-73** — `session.commit()` in route handler. Extract to service function.
2. **routes.py:77** — Logging plaintext email (PII). Hash or redact.
3. **Missing tests** — No tests for /register, /refresh, rate_limit.py, token-lifecycle.service.ts, signup.component.ts.
4. **login() lacks rate limiting** — /register has @ip_rate_limit but /login does not. Login is the primary brute-force target.

### Warnings

5. **auth.interceptor.ts:28** — `handleAuthFailure()` async call not awaited in catchError.
6. **auth.service.ts:30** — `signOut()` is sync but calls async `handleAuthFailure()`.
7. **create_app.py:34** — CORS fails closed when CORS_ORIGINS unset. Verify Coolify has it configured.
8. **rate_limit.py** — In-memory dict grows unbounded for unique IPs, no periodic cleanup.
9. **app.routes.ts:7** — Wildcard `**` catches all unknown paths silently (no 404 for unauth users).
10. **create_app.py:83** — X-Request-ID overwrites any upstream proxy header. Should preserve if present.
11. **create_app.py:82** — HSTS set unconditionally including localhost dev.

## Manual follow-ups (Task 1)

- Rotate Neon database password via console, update .env and Coolify
- Set DATABASE_URL, JWT_SECRET, CORS_ORIGINS in Coolify production env vars

## Next steps

- Fix 4 critical review findings
- Run `/commit` to commit all changes
