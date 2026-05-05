# 🎯 Epic: SaaS Monetisation

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

spec-doc has no revenue layer. The Anthropic SDK provider makes API spend a real operational cost; without metering, any public-access user makes unbounded calls against the org's API budget from day one. Stripe Checkout closes the payment gap with zero PCI scope — cards never reach spec-doc's servers. A daily call cap converts overages into an upgrade prompt rather than a runaway cost centre.

The bubls billing and usage modules are production-proven. Porting to spec-doc is a table-name substitution plus the OpenAPI contract additions — approximately 430 lines of near-verbatim code. The shape (webhook-only writer, `User.plan` denormalised, Customer Portal owns self-service) is a durable pattern that has already survived a production billing cycle in bubls.

This epic is the public-launch gate. spec-doc can be used privately without it, but cannot be opened to external users without both a payment path and a cost guard. Everything downstream — social proof, first paying customer, portfolio launches — waits on this shipping.

**Value Proposition**: Gate public access behind a metered free tier and a Stripe-billed Pro plan so API costs are covered before the first external user signs up.

---

## Scope

### What This Epic Covers

- **OpenAPI contract extension** — billing and usage routes entered into `openapi.yaml`; DTOs regenerated before any route code is written
- **Billing module** — Stripe Checkout session creation, signed webhook handlers (sole writer of subscription state), billing status route, Customer Portal redirect
- **Usage metering module** — per-user daily counters with atomic upsert, `check_usage_limit` decorator applied to gated routes, 429 response with upgrade URL
- **Angular billing surface** — upgrade page, `SubscriptionService` (signals-based), pro route guard, usage-meter pill, 429 interceptor routing to upgrade page

### Pre-conditions (must resolve before Task 1 begins)

Three decisions gate Task 1 because they define the 429 response shape and webhook handler count that enter `openapi.yaml`:

1. **Daily free-tier caps** — proposed `bootstrap=3 / task_gen=20 / spec_gen=10`; must be confirmed before the 429 error body is written into the contract.
2. **Past-due access rule** — (a) stay Pro until `subscription.deleted`, or (b) revert to free on first `invoice.payment_failed`; determines which webhook events write `User.plan`.
3. **Sixth webhook event** — the brain dump states 6 handlers but lists only 5 events; the missing event must be named before the handler table is final.

### What This Epic Does NOT Cover

- ❌ **Annual / team / lifetime plans** — single Price ID at launch; re-scope when a paying user requests a second tier
- ❌ **Coupon / discount codes** — Stripe Dashboard handles manually; no in-app trigger
- ❌ **Per-feature or token-based pricing** — daily call count is the v1 billing currency
- ❌ **Per-org usage pools** — single-user counters only; shared pools require a workspaces epic not yet requested
- ❌ **Billing UI beyond the upgrade page** — Customer Portal owns cancellation, plan changes, and payment-method updates
- ❌ **Usage status endpoint** — deferred for v1; Angular usage-meter reads from billing status response or is dropped if the response shape is insufficient
- ❌ **Per-minute rate limiting** — cloud load balancer or Cloudflare concern, not app-layer
- ❌ **Refund automation / email receipts** — Stripe handles both automatically

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **OpenAPI Contract Extension** | Persistence epic shipped; auth decorator live; 3 pre-conditions resolved | — | 0.5d | High |
| 2 | **Billing Module** | Task 1 | Task 3 | 1d | High |
| 3 | **Usage Metering Module** | Task 1 | Task 2 | 0.5d | High |
| 4 | **Angular Billing Surface** | Tasks 2 + 3 | — | 0.5d | High |

### Task 1: OpenAPI Contract Extension

Add billing routes (`POST /api/billing/create-checkout-session`, `POST /api/billing/webhook`, `GET /api/billing/status`) and the 429 usage-limit error response shape (including `error`, `feature`, `limit`, `reset_at`, and `upgrade_url` fields) to `openapi.yaml`, then run `make generate-dtos`. This is the contract gate; no implementation in Tasks 2 or 3 may begin before DTOs are regenerated and committed. The three pre-conditions above must be resolved before this task opens, because caps and webhook event count directly influence the contract.

**Port budget**: New YAML only — no bubls equivalent; approximately 50 lines. All implementation deferred to Tasks 2–3.

---

### Task 2: Billing Module

Create `modules/billing/` as a Flask Blueprint covering Checkout session creation, signed webhook receipt, and billing status. Webhook handlers are the sole writers of `Subscription.plan` and `User.plan`; every event identified in pre-condition 3 is handled. The Customer Portal redirect URL is generated on demand inside the status handler — no stored URL. Stripe credentials are read from environment variables; none appear in code or committed config.

**Port budget**: ~250 LOC from bubls `billing` module; primary change is table-name substitution (`superapp_*` → `spec_doc_*`).

---

### Task 3: Usage Metering Module

Create `modules/usage/` with an atomic-upsert counter service and a `check_usage_limit` decorator. Free-tier caps live in a single constant dict so they can be tuned without a deploy. Decorator order on all gated routes is `@require_auth → @check_usage_limit("feature") → handler`. Pro users bypass the counter via the denormalised `User.plan` field. Counters increment only on sub-400 responses so failed requests do not consume quota.

**Port budget**: ~180 LOC from bubls `usage` module; table-name and feature-key substitution only.

---

### Task 4: Angular Billing Surface

Wire five Angular pieces: `SubscriptionService` (signals-based plan state and checkout redirect), pro route guard, usage-meter pill (hidden for Pro, highlighted at ≤ 1 remaining), 429 interceptor (routes to `/upgrade`), and upgrade page (pricing copy plus Pro CTA). No billing management UI ships here — Customer Portal handles all self-service. Angular version and signal API compatibility with the bubls source must be verified before porting begins.

**Port budget**: ~5 files near-verbatim from bubls; compatibility check is the only non-trivial delta.

---

## Success Criteria

- ✅ A free user who exhausts their daily allowance for any gated feature receives a 429 with an `upgrade_url` and is routed to the upgrade page by the Angular interceptor
- ✅ Clicking "Upgrade to Pro" redirects the browser to a Stripe Checkout session loaded with the correct Price ID
- ✅ A completed Stripe Checkout sets `User.plan = 'pro'`; that user's next request bypasses the usage counter without a re-login
- ✅ All webhook events are handled; no internal code path may write `plan = 'pro'` except a webhook handler
- ✅ `make check-dtos` passes with all billing and usage routes present in `openapi.yaml` and matching generated DTOs
- ✅ `make test` passes with billing and usage modules covered

---

## Non-Goals

- ❌ **Annual or team plans** — one Price ID ships; a second can be added when a paying user requests it without touching any of this epic's code
- ❌ **Token or per-minute metering** — daily call count is sufficient for v1 cost control; re-scope if abuse patterns emerge post-launch
- ❌ **In-app billing management** — Stripe Customer Portal is the self-service surface; no spec-doc screens for cancellation or payment-method updates
- ❌ **Workspace-shared usage pools** — counters are per-user; pooling requires a workspaces epic that has not been requested

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview