# exec-guide summary — SaaS Phase 2b: Billing UI & Stripe Activation

**Date:** 2026-05-13
**Tasks run:** 4 (Task 5 E2E verification is manual)
**Tasks passed:** 4 / 4
**Tests:** passed (backend: 819 passed, 0 failed; frontend: build clean, 155 tests pass)
**Review:** not run separately (review findings from 2a review applied)
**PR:** https://github.com/bytesbysamu/specview/pull/50 (merged)

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Stripe Activation & Lapsed State | ✓ complete | `billing/service.py`, `billing/routes.py`, `usage/decorators.py`, `openapi.yaml`, test files |
| Task 2: SubscriptionService + Tests | ✓ complete | `subscription.service.ts`, `.spec.ts`, `.mock.ts` (all new) |
| Task 3: Billing Interceptor + Upgrade Page | ✓ complete | `billing.interceptor.ts`, `usage.state.ts`, upgrade component (ts/html/scss), `app.config.ts`, `app.routes.ts` |
| Task 4: Usage Meter | ✓ complete | `usage-meter.component.ts/html/scss` (new), `app.component.html/ts` |
| Task 5: E2E Verification | ⏳ manual | Requires Stripe test-mode credentials in running environment |

## Test results

Backend: 819 passed, 0 failed
Frontend: `ng build --configuration production` succeeded, 155 Karma tests pass (154 existing + 1 new subscription spec — note: the subscription `startCheckout` test initially crashed CI with "full page reload" error)

## CI issues discovered & fixed

| Issue | Root cause | Fix |
|-------|-----------|-----|
| Backend lint: `F401` unused import | `verify_session as vs` imported but not used in `test_routes.py` | Removed unused import |
| Frontend: `Cannot redefine property: location` | `startCheckout` test tried to mock `window.location` via `Object.defineProperty` — Chrome Headless blocks this | Extracted `redirect()` as protected method on `SubscriptionService`, test spies on it instead |
| Frontend: `Some of your tests did a full page reload!` | Even with `.catch()`, `window.location.href = url` actually fires and reloads the browser, crashing Karma | Same fix as above — `redirect()` method is spied on, preventing actual navigation |

## Backend changes detail

### `invoice.payment_failed` → `plan='lapsed'`
The webhook handler now writes `plan='lapsed'` instead of `plan='free'`, distinguishing "never subscribed" from "payment failed". The `billing_status()` route maps `lapsed` → `free` for the OpenAPI Plan enum (which stays `[free, pro]`) while the internal DB carries the tri-state.

### `GET /api/billing/verify-session`
New endpoint with `@require_auth` + user_id ownership check. Retrieves the Stripe checkout session, validates `metadata.user_id` matches the authenticated user, returns the plan state. Closes the webhook-redirect race condition (user returns from Stripe before webhook fires).

### `X-Usage-Remaining` header
The `@check_usage_limit` decorator now emits `X-Usage-Remaining: {remaining}/{limit}` on every successful response from a usage-limited endpoint. The billing interceptor extracts this passively — zero additional HTTP requests.

## Frontend changes detail

### SubscriptionService
Signal-based: `plan = signal<Plan>('free')`, `isPro = computed(() => this.plan() === 'pro')`. Methods: `refresh()`, `startCheckout()`, `verifySession(sessionId)`. Constructor calls `refresh()` on injection. Co-located `.spec.ts` (6 tests) and `.mock.ts`.

### Billing Interceptor
Separate from auth interceptor (single-responsibility). Catches 429 → navigates to `/upgrade` with context (`?reason=limit_reached&feature=...` or `?reason=payment_lapsed`). Extracts `X-Usage-Remaining` header into `usageRemaining` signal. Registered after `authInterceptor` in `app.config.ts`.

### Upgrade Page
Standalone component at `/upgrade`. Conditional CTAs: free → checkout button, lapsed → Customer Portal, pro → manage subscription. Post-checkout: reads `session_id` query param, calls `verifySession()`, shows "Welcome to Pro" confirmation.

### Usage Meter
Pill component in masthead. Reads `usageRemaining` signal from billing interceptor. Shows `"N/M remaining"`. Hidden for Pro. Red warning at ≤1 remaining.

## Next steps

- Configure Stripe test-mode credentials in `.env` / Coolify:
  - `STRIPE_SECRET_KEY=sk_test_...`
  - `STRIPE_WEBHOOK_SECRET=whsec_...`
  - `STRIPE_PRO_PRICE_ID=price_...`
  - `FRONTEND_URL=https://specview.app`
- Test locally: `stripe listen --forward-to localhost:5001/api/billing/webhook`
- Complete manual E2E verification (Task 5): signup → generate → hit limit → upgrade → checkout → Pro
- Reconcile `success_url` in `service.py` to redirect to `/upgrade?session_id={CHECKOUT_SESSION_ID}`
