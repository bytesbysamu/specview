# SaaS Phase 2b: Billing UI & Stripe Activation

> **Priority**: P2 — monetization gate. Users can register and see their own projects (after 2a) but can't pay.
> **Effort**: ~1.5 days.
> **Depends on**: Phase 1 (auth), Phase 2a (isolation — so billing status is per-user).

## The problem

The entire Stripe billing backend is built and waiting — checkout sessions, webhook handlers for 6 events, usage limits with daily caps, pro plan bypass. But it's dead code because: (1) no Stripe credentials are configured in the environment, and (2) there are zero Angular components to trigger checkout, show plan status, or handle the 429 "upgrade" flow. A user hits their free tier limit, gets a JSON error, and has no way to upgrade.

---

## Current state (fact-checked 2026-05-12)

**Backend (complete, just needs credentials):**
- `api/modules/billing/service.py` — Stripe adapter (ELA #1 pattern). `create_checkout_session(user)` returns a Stripe-hosted URL. `create_portal_session(stripe_customer_id)` returns a self-service portal URL. `handle_webhook(payload, sig_header)` routes 6 events with signature verification.
- Webhook handlers: `checkout.session.completed` → upsert Subscription + `User.plan='pro'`. `customer.subscription.updated` → period dates. `customer.subscription.deleted` → `User.plan='free'`. `invoice.payment_succeeded` → activate. `invoice.payment_failed` → `User.plan='free'` (0-day grace, locked decision). `invoice.upcoming` → log only.
- `User.plan` is written ONLY by webhook handlers — enforced by test boundary.
- `api/modules/billing/routes.py` — `POST /api/billing/create-checkout-session`, `POST /api/billing/webhook`, `GET /api/billing/status` (returns plan + status + period_end + manage_url).
- `api/modules/usage/` — `@check_usage_limit` decorator with atomic upsert. Daily caps: bootstrap=30, task_gen=100, spec_gen=50. Pro bypass. Returns 429 with `{error, feature, limit, reset_at, upgrade_url}`.

**Frontend (stubs only):**
- Auto-generated DTOs from openapi codegen: `BillingStatusResponse`, `CheckoutSessionResponse`.
- Auto-generated API functions: `getBillingStatus()`, `createCheckoutSession()`.
- No `SubscriptionService`, no upgrade page, no usage meter component, no 429 interceptor handling.

**Environment (missing):**
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `FRONTEND_URL` — not in `.env`, not in `docker-compose.yml`, not in Coolify config.

---

## Learnings from other projects

**Springular (most mature billing UI):**
Has a full subscription component with monthly/annual toggle, multi-tier pricing (Individual $2, Pro $4, Enterprise $10), and a "Manage subscription" button that opens the Stripe Customer Portal. The Customer Portal is key — it's Stripe-hosted, handles payment updates, cancellation, and invoice downloads with zero code on our side. Springular also has an invoice history page that queries Stripe directly for invoice PDFs. All pricing config is in `environment.ts` (publishable key + price IDs per tier), keeping secrets server-side.

The checkout flow: frontend sends `{priceId, returnUrl}` → backend creates Stripe session → returns `{url}` → frontend does `window.location.href = url` → Stripe handles everything → webhook fires on success. Simple and PCI-compliant.

**Bubls (signal-based subscription state):**
Uses `isPro = signal(true)` with `checkEntitlement(id)` for reactive plan state. Feature gate guard pattern: `CanActivateFn` checks entitlement, opens paywall modal if not entitled, waits for purchase, re-checks. The paywall modal takes a `PaywallConfig` with title + features list — reusable component. Mock mode via `environment.useMocks.payments` returns fixture data when Stripe isn't configured — great for local dev.

**Trendfy (Flask + Stripe, simpler model):**
Has a `GET /api/v1/stripe/config` endpoint that returns public Stripe info (publishable key, prices) so the frontend doesn't hardcode anything. Also supports public checkout (no auth required) — auto-creates user on webhook from Stripe customer email. Interesting for a future landing page "buy before signup" flow, but not needed for launch.

---

## Architecture direction

**Stripe activation is config, not code.** Create a Stripe account (or use test mode), create "Specview Pro" product at $29/mo, configure webhook endpoint to `https://specview.app/api/billing/webhook`, add env vars. Test locally with `stripe listen --forward-to localhost:8095/api/billing/webhook`.

**SubscriptionService with signals.** `plan = signal<'free'|'pro'>('free')`, `isPro = computed(() => this.plan() === 'pro')`. Calls `GET /api/billing/status` on init and after checkout redirect. Exposes `startCheckout()` that calls the backend and redirects to Stripe.

**Upgrade page.** Simple page: pricing copy, feature comparison (free vs pro), "Upgrade to Pro — $29/mo" button → `startCheckout()`. No custom payment form — Stripe Checkout handles cards. For existing subscribers: "Manage subscription" button → Stripe Customer Portal URL from `BillingStatusResponse.manage_url`.

**Usage meter.** Small pill in the status bar area showing "X/N remaining" for the current feature. Hidden for Pro users. Turns red at ≤1 remaining. Data comes from a new lightweight endpoint or is derived client-side from the 429 response body.

**429 interceptor.** HTTP interceptor catches 429 from `@check_usage_limit` → navigates to `/upgrade` with a message. The 429 body already contains `{error, feature, limit, reset_at, upgrade_url}` — the interceptor just needs to read it and route.

**Stripe Customer Portal** for self-service subscription management. The backend already generates portal session URLs in `GET /api/billing/status` → `manage_url`. Frontend just needs to open it.

---

## Testing baseline to maintain

Phase 3 established 146 tests across 9 spec files (39% statement coverage, 21% branch coverage). New frontend code must maintain or improve this:

- **SubscriptionService** needs a `.spec.ts` with tests for: initial state is 'free', `refresh()` updates plan signal from API response, `startCheckout()` calls backend and redirects, `isPro` computed reacts to plan changes. Follow the co-located mock convention — create `subscription.service.mock.ts` alongside it.
- **Upgrade component** needs basic component tests: renders pricing, CTA button triggers checkout, shows "Manage" button when already Pro.
- **429 interceptor logic** needs a test: verify that a 429 response triggers navigation to `/upgrade` with the right message.
- **Backend:** No new backend code, but verify existing billing tests still pass after credential configuration. Run `pytest api/modules/billing/` to confirm.
- **E2E:** The existing `billing-gate.feature` already tests free tier limit + pro bypass. After Stripe is activated, verify this scenario still works against the real billing routes (not just mocks).

---

## Files involved

- `.env` / `docker-compose.override.yml` — Stripe credentials
- `web-ng/src/app/services/subscription.service.ts` — new, signal-based plan state
- `web-ng/src/app/services/subscription.service.spec.ts` — new, tests
- `web-ng/src/app/services/subscription.service.mock.ts` — new, co-located mock
- `web-ng/src/app/components/upgrade/` — new, upgrade page + pricing
- `web-ng/src/app/app.component.html` — usage meter pill
- `web-ng/src/app/interceptors/auth.interceptor.ts` — extend with 429 handling

## Success criteria

- Stripe test mode checkout completes end-to-end ($29 charge appears in Stripe dashboard)
- Webhook flips `User.plan` from "free" to "pro" after checkout
- Angular `SubscriptionService.isPro()` reflects the plan change
- Upgrade page renders with pricing and CTA
- `@check_usage_limit` 429 response navigates to upgrade page with clear message
- "Manage subscription" button opens Stripe Customer Portal
- Usage meter shows remaining calls, hidden for Pro
- SubscriptionService has spec file with passing tests
- Existing 146 frontend tests still pass (no regression)
- Existing E2E billing-gate scenario still passes
