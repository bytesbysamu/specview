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

## Manual test guide — Phase 2b: Billing UI

### Prerequisites
1. Local stack running: `docker compose up -d`
2. Stripe CLI installed: `brew install stripe/stripe-cli/stripe`
3. Stripe test-mode credentials in `api/.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRO_PRICE_ID=price_...
   FRONTEND_URL=http://localhost:8095
   ```
4. Webhook forwarding: `stripe listen --forward-to localhost:5001/api/billing/webhook`

### Test 1: Free tier usage limit → upgrade prompt
1. Log in at `http://localhost:8095`
2. Create a project and paste a braindump
3. Click "Generate specs" repeatedly until the daily limit is hit (bootstrap=30 for free tier — or temporarily lower the limit in `api/modules/usage/service.py` LIMITS dict to 1 for testing)
4. **Expected:** 429 response → billing interceptor catches it → navigates to `/upgrade` with "You've used all N daily generations" message
5. **Verify:** usage meter pill in masthead shows "0/N remaining" with red warning styling

### Test 2: Stripe checkout flow
1. On the `/upgrade` page, verify you see the pricing comparison (Free vs Pro)
2. Click "Upgrade to Pro — $29/mo"
3. **Expected:** redirect to Stripe Checkout (test mode)
4. Use test card `4242 4242 4242 4242`, any future expiry, any CVC
5. Complete payment
6. **Expected:** redirect back to app, brief "Verifying..." state, then "Welcome to Pro"
7. **Verify:** `stripe listen` terminal shows `checkout.session.completed` webhook delivered
8. **Verify:** `GET /api/billing/status` returns `{"plan": "pro", "status": "active", ...}`

### Test 3: Pro user bypasses limits
1. After upgrading, generate specs again
2. **Expected:** no 429, no usage meter (hidden for Pro), unlimited generations
3. **Verify:** `X-Usage-Remaining` header is NOT present in responses (Pro users skip the decorator)

### Test 4: Lapsed state (payment failure)
1. In a separate terminal: `stripe trigger invoice.payment_failed`
2. **Expected:** webhook fires, user's plan flips to `lapsed` in DB
3. Navigate to `/upgrade`
4. **Expected:** message says "Update your payment method to restore Pro access" (not "Upgrade to Pro")
5. **Expected:** CTA button opens Stripe Customer Portal (not checkout)

### Test 5: Manage subscription (Customer Portal)
1. As a Pro user, navigate to `/upgrade`
2. **Expected:** shows "You're on Pro" with "Manage subscription" button
3. Click "Manage subscription"
4. **Expected:** opens Stripe Customer Portal in new tab where you can cancel, update payment, download invoices
