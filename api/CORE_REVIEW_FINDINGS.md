# oll.am Core — Comprehensive Review Findings
**Date:** 2026-06-25 | **Audited by:** 5-agent parallel workflow

---

## What Was Built This Session

oll.am Core (specview Flask API) extended with:
- `POST /api/email/send` — 6 email templates via Resend
- `POST /api/billing/portal` — Stripe customer portal
- Product/plan price routing: `STRIPE_PRICE_{PRODUCT}_{PLAN}` env convention
- Billing auth_user_id bug fixed — routes now use `g.current_user` directly
- Email wired into billing webhooks (activation + cancellation)
- 5/6 integration tests passing against live Neon + Stripe test APIs

---

## Audit Findings Summary (5 dimensions)

### SECURITY — Critical
1. `STRIPE_WEBHOOK_SECRET` unset in `.env` → webhook accepts unauthenticated payloads in prod
2. Hardcoded fallback JWT secret `dev-secret-change-in-prod` in auth/service.py
3. `SKIP_AUTH` bypass soft-gated on `FLASK_ENV=development` only (easy to misconfigure)

### SECURITY — High
- No rate limiting on `/api/auth/login` or `/api/auth/register` (credential stuffing)
- 72-hour access tokens with no real refresh (re-issues same lifetime token)
- Integer user ID in JWT `sub` (enumerable)
- `/api/context/<key>` GET/PUT have no `@require_auth`
- Any authenticated user can send email to any address via `/api/email/send`

---

### TESTS — Critical
1. **FAILING:** `test_status_for_free_user_returns_free_plan_and_null_manage_url` — conftest `_fake_load_user` returns `plan="pro"`, new billing routes use `g.current_user` directly → returns `"pro"` not `"free"`
2. **Zero tests** for `modules/email/` (routes + service)
3. **Zero tests** for `POST /api/billing/portal`
4. **No `test_login.py`** — `/api/auth/login` entirely untested

---

### API CONTRACT — Critical
1. `openapi.yaml` `/auth/me` schema is wrong — spec says `{id, email, auth_user_id}`, route returns `{id, email, plan, token_expires_at}`
2. Error shapes not unified — auth/billing: `{"error": "string"}`, email: `{"code": "...", "message": "..."}`

### API CONTRACT — High
- `/api/billing/portal` not in openapi.yaml
- `/api/email/send` not in openapi.yaml
- `/api/billing/create-checkout-session` `requestBody` missing `product`/`plan` params
- 401 errors not machine-distinguishable (TOKEN_EXPIRED vs UNAUTHORIZED vs USER_NOT_FOUND)

---

### DATABASE — Critical
1. No refresh token table — `refresh_token_for_user()` just re-issues a new AT, no revocation possible
2. SQLite FK constraints never enforced in tests (`PRAGMA foreign_keys = ON` missing)

### DATABASE — High
- Integer PK on User (enumerable via JWT)
- `DateTime` columns not timezone-aware
- Alembic not auto-run on deploy (no `alembic upgrade head` in `entrypoint.sh`)
- Table named `user` is a SQL reserved word

---

### EDGE CASES — Critical
1. Empty `STRIPE_SECRET_KEY` crashes checkout silently (no guard before Stripe SDK call)
2. Malformed webhook JSON crashes with unhandled exception when `STRIPE_WEBHOOK_SECRET` is unset

### EDGE CASES — High
- No error handling when Stripe API is down during checkout
- DB connection failure leaks exception type details to client
- `/billing/portal` has no try/except around `create_portal_session()`
- No email format validation on `/email/send` `to` field

---

## Immediate Next Steps (ordered)

1. **Rotate live Stripe key** — `sk_live_...` was exposed in session (SECURITY BLOCKER)
2. Fix billing test (monkeypatch `_load_user` to return `plan="free"` user)
3. Add `tests/` for email module and billing portal
4. Fix `openapi.yaml` — update `/auth/me` schema, add `/email/send` + `/billing/portal`
5. Add `alembic upgrade head` to `entrypoint.sh`
6. Guard `STRIPE_SECRET_KEY` empty before Stripe SDK calls
7. Set `STRIPE_WEBHOOK_SECRET` via `stripe listen --forward-to localhost:3101/api/billing/webhook`
8. Deploy to `core.api.oll.am`
