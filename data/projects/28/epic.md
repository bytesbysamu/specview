# 🎯 Epic: SaaS Phase 2b — Billing UI & Stripe Activation

## Business Value

The entire Stripe billing backend — checkout sessions, webhook handlers for six events, usage limits with daily caps, pro plan bypass — is built, tested, and waiting. But it is dead code. No credentials are configured, and zero Angular components exist to trigger checkout, display plan status, or convert a 429 "you've hit your limit" into an upgrade action. Users hit their free-tier wall, receive a raw JSON error, and have no path to pay. Every day this stays unactivated is revenue left on the table with engineering cost already sunk.

Phase 2b is the monetization gate. It converts spec-doc from a free tool with arbitrary usage walls into a product with a $29/mo Pro tier and a clear upgrade funnel. The 429 → upgrade page transition is the single most important conversion moment in the product — a user who just hit a limit is maximally motivated to pay. Getting this moment right (clear messaging, zero-friction Stripe Checkout redirect, immediate plan activation) directly determines first-month revenue. Delaying it means users churn at the wall instead of converting.

The scope is deliberately narrow: configuration of existing infrastructure, a thin reactive service layer, one upgrade page, and one interceptor. No custom payment forms, no multi-tier pricing, no admin dashboards. Stripe Checkout and Customer Portal handle every PCI-scoped surface. This keeps the build under two days while unlocking the full billing pipeline that Phase 1 and 2a invested in.

## Scope

### What This Epic Covers

- **Stripe credential activation** — Configure test-mode keys, webhook secret, price ID, and frontend URL across all environments so existing backend billing code becomes operational
- **SubscriptionService (signal-based)** — Reactive Angular service exposing plan state (`free | pro | lapsed`) with computed convenience accessors, checkout initiation, and post-checkout session verification to close the webhook race condition
- **Billing interceptor** — Dedicated HTTP interceptor (separate from auth) that catches 429 responses from `@check_usage_limit` and routes users to the upgrade page with contextual messaging, distinguishing "never subscribed" from "payment lapsed"
- **Upgrade page** — Single-page component with pricing copy, free-vs-pro feature comparison, checkout CTA for non-subscribers, and "Manage subscription" button (opening Stripe Customer Portal) for existing subscribers
- **Usage meter** — Passive header-based usage display extracted from API response headers by the billing interceptor, showing remaining daily calls per feature, hidden for Pro users
- **`lapsed` plan state** — Backend webhook handler update so `invoice.payment_failed` writes `plan='lapsed'` instead of `plan='free'`, enabling the frontend to distinguish "upgrade" from "fix your payment method"

### What This Epic Does NOT Cover

- ❌ **Soft wall / 80% usage warning** — Better conversion UX but not launch-blocking; revisit after first week of conversion data
- ❌ **Inline upgrade modal** — Preserves user context better than full-page redirect but doubles the component surface area; scope to post-launch iteration
- ❌ **Revenue metrics endpoint** — Needed within the first week but is admin tooling, not user-facing billing; separate task
- ❌ **Checkout without auth (Trendfy pattern)** — "Buy before signup" flow is explicitly deferred; SubscriptionService design should not preclude it
- ❌ **Cancellation feedback** — Stripe portal configuration only, zero code, but not on the critical path to first revenue
- ❌ **`stripe listen` docker-compose sidecar** — Developer ergonomics improvement, not shipping software
- ❌ **Multi-tier pricing** — Single $29/mo Pro plan at launch; tiers add complexity with no data to justify them yet

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Stripe Activation & Lapsed State** | None | — | 0.25 days | High |
| 2 | **SubscriptionService + Tests** | Task 1 (env vars) | — | 0.5 days | High |
| 3 | **Billing Interceptor + Upgrade Page** | Task 2 (plan state) | Yes (with each other after Task 2) | 0.5 days | High |
| 4 | **Usage Meter (Header-Based)** | Task 3 (interceptor extracts headers) | — | 0.25 days | Low |
| 5 | **E2E Verification & Regression Suite** | Tasks 1–4 | — | 0.25 days | High |

**Task 1** — Create Stripe account (or activate test mode), create "Specview Pro" product at $29/mo, configure webhook endpoint, add all four env vars, verify webhook delivery with Stripe CLI. Add `lapsed` to the plan model: update `openapi.yaml` Plan enum to `[free, pro, lapsed]` first, regenerate Angular DTOs, then modify `invoice.payment_failed` webhook handler to write `plan='lapsed'` instead of `plan='free'`. Also add `X-Usage-Remaining` header emission to the `@check_usage_limit` decorator. Also add `GET /api/billing/verify-session` endpoint (with `@require_auth` + user_id verification) for post-checkout race condition mitigation.

**Task 2** — Build `SubscriptionService` with signal-based plan state (`free | pro | lapsed`), computed `isPro` accessor, `startCheckout()` method, `refresh()` from billing status endpoint, and post-checkout `session_id` verification to close the redirect-before-webhook race condition. Co-located `.spec.ts` and `.mock.ts` files per project convention.

**Task 3** — Two parallel deliverables gated on Task 2. Billing interceptor: dedicated `billing.interceptor.ts` catching 429 responses, extracting usage context from the response body, routing to `/upgrade` with appropriate messaging (distinguishing "upgrade" from "payment lapsed"). Must be registered in `app.config.ts` as `withInterceptors([authInterceptor, billingInterceptor])` — auth first, billing second. Upgrade page: pricing comparison, conditional CTA (checkout for non-subscribers, "Manage subscription" via Customer Portal for existing subscribers), and post-checkout success state. Both `/upgrade` and the post-checkout return route must be added to `app.routes.ts` (currently only `signup` + wildcard exist). Reconcile `success_url` in `service.py` (currently `/billing/success`) with the Angular route — either redirect to `/upgrade?session_id=...` or add a dedicated `/billing/success` route.

**Task 4** — Backend decorator adds `X-Usage-Remaining` response header piggy-backing on existing traffic. Billing interceptor extracts it into a signal. Usage meter pill component reads the signal, shows "X/N remaining," turns red at ≤1, hidden for Pro users.

**Task 5** — Full Stripe test-mode checkout end-to-end ($29 charge visible in dashboard). Webhook round-trip verification. Run existing 146 frontend tests to confirm zero regression. Run `billing-gate.feature` E2E scenario against real billing routes. Verify `lapsed` state produces correct upgrade page copy.

## Success Criteria

- ✅ Stripe test-mode checkout completes end-to-end — $29 charge appears in Stripe dashboard and webhook flips `User.plan` to `pro`
- ✅ Post-checkout redirect with `session_id` shows Pro status immediately (no stale "Free plan" flash)
- ✅ Angular `SubscriptionService.isPro()` reactively reflects plan changes across the app
- ✅ Upgrade page renders pricing comparison with correct CTA: "Upgrade" for free/lapsed users, "Manage subscription" for Pro users
- ✅ 429 response from `@check_usage_limit` navigates to `/upgrade` with contextual message (not a raw JSON error)
- ✅ Lapsed state (`invoice.payment_failed`) produces "Update your payment method" messaging, not "Upgrade to Pro"
- ✅ "Manage subscription" button opens Stripe Customer Portal successfully
- ✅ Usage meter displays remaining daily calls per feature, hidden for Pro users
- ✅ `SubscriptionService` has passing `.spec.ts` with co-located `.mock.ts`
- ✅ Existing 146 frontend tests pass with zero regressions
- ✅ Existing `billing-gate.feature` E2E scenario passes against activated billing routes

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — Signal-based state design, interceptor separation, session verification pattern
- [Timeline](./timeline.md) — Status tracking and delivery schedule