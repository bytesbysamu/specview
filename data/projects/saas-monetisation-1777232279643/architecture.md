# 🏗️ Solution Architecture: SaaS Monetisation

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The system divides into two halves that are coupled at exactly one seam: `User.plan`. The billing module writes it via Stripe webhooks; the usage metering module reads it on every gated request. This coupling is intentional — it is what allows the metering decorator to remain a single field read with no join. Splitting the two into independent capabilities would obscure that billing is the producer and metering is the consumer.

The key architectural constraint is that Stripe webhooks are the **sole writer** of subscription state. No in-app code path may set `plan = 'pro'`. This is not a purity rule but a correctness requirement: Stripe's event stream is the authoritative record of payment. Any in-app write creates a race condition between the checkout response and the asynchronous webhook. The webhook-only pattern was validated in bubls production and is ported directly — the only delta is table-name substitution.

The Angular surface is deliberately thin. Five pieces wire the signal → guard → interceptor chain. Stripe Customer Portal handles all billing management. This means no cancellation screen, no payment-method editor, and no plan-change UI ships here — those are Stripe-hosted and carry zero spec-doc maintenance burden.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #1 — Adapter Boundary | All Stripe SDK calls are isolated to `modules/billing/service.py`; no route handler or usage module imports Stripe directly |
| ELA #2 — Blueprint Module Structure | `modules/billing/` and `modules/usage/` each own routes, service, and tests; cross-module coupling is limited to `g.current_user` (auth boundary) and `User.plan` (denormalised field read) |
| ELA #3 — OpenAPI-First | All billing and usage routes plus the 429 error body enter `openapi.yaml` and DTOs are regenerated before any implementation begins |
| ELA #5 — Not-Yet-Built | Single Price ID at launch; no annual/team abstraction; no coupon engine; the one concrete Pro plan is described, not a generalised pricing engine |
| ELA #7 — In-Process State | `check_usage_limit` is stateless at the Python layer; counter state lives entirely in the DB via atomic upsert — no in-process counter dict is needed |

---

## System Boundaries

### What This System Includes

- `modules/billing/` Blueprint — Checkout session creation, signed webhook dispatch, billing status with Customer Portal URL
- `modules/usage/` Blueprint — atomic daily counter service, `check_usage_limit` decorator, free-tier cap constants
- `Subscription` SQLModel entity — one row per user; holds all Stripe IDs and the denormalised `plan` / `status` fields
- `UsageCounter` SQLModel entity — one row per `(user_id, feature, date)`; unique constraint enforces atomic-upsert safety
- `User.plan` denormalisation — written by billing webhook handlers; read by metering decorator; eliminates a join on every gated AI call
- Angular `SubscriptionService` — signals-based plan state and Stripe Checkout redirect
- Angular pro route guard, usage-meter pill, 429 interceptor, upgrade page

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Annual / team / lifetime plans | One Price ID is sufficient for v1; adding a second Price ID later does not require touching this architecture |
| Coupon / discount codes | Stripe Dashboard applies manually; no in-app trigger surface required at this scale |
| Token-based or per-minute metering | Daily call count is the cost-control unit; per-token granularity adds UI complexity without changing the billing decision at v1 scale |
| In-app billing management UI | Stripe Customer Portal owns cancellation, payment-method updates, and plan changes at zero maintenance cost |
| Usage status API endpoint | Angular reads plan and period from the billing status response; standalone call counts are not exposed in v1 |
| Per-org usage pools | Single-user counters only; shared pools require a workspaces epic not yet requested |

---

## Component Design

### Billing Module (`modules/billing/`)

**Purpose**: Makes Stripe the authoritative source of subscription state while keeping all card data off spec-doc servers.

**Key Parts**:
- `routes.py` — three handlers: checkout session creator (auth-gated), webhook receiver (signature-verified, no auth required), billing status (auth-gated, returns Customer Portal URL)
- `service.py` — sole Stripe SDK import point; `get_or_create_stripe_customer` (lazy — called only on first checkout, not on signup); webhook event dispatch to named handler functions; `_customer_portal_url` generates a live session on demand, never stored
- `repository.py` — `SubscriptionRepository.get_for_user` and `upsert_from_event`; single consumer is `routes.py`
- `models.py` — `Subscription` SQLModel; `plan` and `status` fields plus all Stripe ID columns

**Consumer**: `modules/billing/routes.py` is the sole consumer of `service.py`. Angular `SubscriptionService` is the sole HTTP consumer of all three routes.

**Patterns**: Webhook-only writer for plan state. Stripe signature verification at the route boundary — unsigned payloads are rejected before any handler runs. Customer Portal session generated per-request because Stripe session tokens expire; storing a URL would produce stale-token errors.

---

### Billing Webhook Handlers

**Purpose**: Translate Stripe event types into `Subscription` and `User.plan` mutations; five events are confirmed and a sixth is an open question.

| Event | Subscription Write | `User.plan` Write |
|---|---|---|
| `checkout.session.completed` | Insert/upsert: plan=pro, status=active, record all Stripe IDs | Yes → pro |
| `customer.subscription.updated` | Update period dates and status; set `canceled_at` if `cancel_at_period_end` | No |
| `customer.subscription.deleted` | plan=free, status=canceled | Yes → free |
| `invoice.payment_failed` | status=past_due | Conditional — see Open Questions |
| `invoice.paid` | status=active, bump `current_period_end` | No |

**Patterns**: Dispatch by event type via a constant dict keyed to handler functions. Each handler is a pure function receiving only the Stripe data object. No handler imports from any module other than `SubscriptionRepository` and the `User` update path. Port from bubls `billing` module — table-name substitution (`superapp_*` → `spec_doc_*`) is the primary delta.

---

### Usage Metering Module (`modules/usage/`)

**Purpose**: Enforces the free-tier daily cap per feature so API spend scales with paid users only.

**Key Parts**:
- `service.py` — `DAILY_FREE_TIER_LIMITS` constant dict (the single tuneable for cap values); `increment(user_id, feature)` atomic upsert; `get_remaining(user_id, feature)` for pre-check
- `middleware.py` — `check_usage_limit(feature)` decorator; reads `g.current_user.plan`; returns 429 with structured body (error, feature, limit, reset_at, upgrade_url) if limit reached; increments counter only on sub-400 responses
- `models.py` — `UsageCounter` SQLModel with unique constraint on `(user_id, feature, date)`

**Consumers**: `modules/ai/routes.py` bootstrap, task_gen, and spec_gen handlers each gain `@check_usage_limit`.

**Patterns**: Decorator stacking order is fixed — `@require_auth` outer, `@check_usage_limit` inner. Pro users short-circuit at the `plan == 'pro'` field read before any DB access. Counter increment is post-response to avoid charging failed requests. Atomic upsert prevents double-counting under concurrent requests from the same user session.

---

### Angular Billing Surface

**Purpose**: Surfaces plan state to the user and routes them to Stripe or the upgrade page; no billing logic executes in the browser.

**Key Parts**:
- `SubscriptionService` — `plan` signal and `isPro` computed; `refresh()` hydrates from `/api/billing/status`; `startCheckout()` posts to `/api/billing/create-checkout-session` then performs a full browser redirect to the Stripe-hosted page
- `pro.guard.ts` — `canActivate` reads `isPro()`; redirects to `/upgrade?returnUrl=` if false; consumer is any route declared pro-only
- `usage-meter.component.ts` — remaining-count pill in the app shell; hidden for pro users; highlighted red at ≤ 1 remaining
- `usage-limit.interceptor.ts` — catches 429 responses globally and navigates to `/upgrade`; consumer is the Angular HTTP client pipeline
- `upgrade.page.ts` — pricing copy and Pro CTA that calls `startCheckout()`; no in-page payment form; reachable from 429 interceptor and direct navigation

**Patterns**: All five pieces port near-verbatim from bubls. Angular version and signal API compatibility must be verified against the bubls source before porting begins — this is the only non-trivial pre-port step.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Payment processor | Stripe Checkout (hosted) | Zero PCI scope — cards never reach spec-doc servers; webhook payloads are signed |
| Subscription state | `spec_doc_subscriptions` via SQLModel | Single-row-per-user; `plan` denormalised for O(1) per-request reads without a join |
| Usage counters | `spec_doc_usage_counters` atomic upsert | Concurrent-safe on both SQLite (dev) and Postgres (prod) without application-level locking |
| Billing self-service | Stripe Customer Portal | Cancellation and payment-method management hosted by Stripe; zero spec-doc UI to maintain |
| Angular plan state | Signals + computed | Reactive without RxJS Subject boilerplate; consistent with bubls port source |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Webhook as sole plan writer | Prevents race conditions between checkout response and async webhook; Stripe event stream is the payment record of truth | Plan promotion is delayed by seconds after checkout; mitigated by success-page reload that re-fetches billing status |
| `User.plan` denormalised from `Subscription` | Per-request gate is a field read — critical for latency on every gated AI call | Field can drift if a webhook is missed; mitigated by idempotent upsert handlers and Stripe's built-in retry policy |
| Counter increment post-response | Failed requests do not consume free-tier quota | Decorator must inspect the response object; adds wrapping complexity but is correct for user trust |
| Daily UTC midnight reset | Simple, consistent, matches bubls production | Users near midnight may feel penalised; rolling 24h is fairer but adds per-feature `created_at` tracking complexity |
| Lazy Stripe customer creation | Customer ID only needed on first checkout; avoids a Stripe API call on every user signup | `manage_url` in the status response is null until first checkout; acceptable for a pre-checkout free user |
| Customer Portal URL generated on-demand | Stripe session tokens expire; generating per-request avoids stale-token errors | One extra Stripe API call per status request when a customer ID exists; negligible at this scale |

---

## Execution Flow

```
Pre-conditions resolved (caps, past-due rule, 6th event)
  └── Task 1: openapi.yaml extended → make generate-dtos committed
        ├── Task 2: modules/billing/ implemented
        └── Task 3: modules/usage/ implemented + @check_usage_limit applied to ai/routes.py
              └── Task 4: Angular billing surface wired
```

Tasks 2 and 3 are parallel; Task 4 waits on both.

---

## Open Questions

Three pre-conditions from the Epic must be resolved before Task 1 (OpenAPI contract) opens, because they directly determine route shapes and the handler table.

- **Past-due access rule** — Option A: user retains Pro until `subscription.deleted` (grace period); Option B: revert to free on first `invoice.payment_failed`. Choice determines whether `invoice.payment_failed` writes `User.plan`. Option A is more user-friendly; Option B reduces API cost exposure during unpaid grace periods. Re-decision trigger: first user complaint about unexpected service interruption (favour A) or first evidence of past-due users consuming material API budget (favour B).

- **Sixth webhook event** — The brain dump states six handlers but the event table lists five. The missing event must be named before the webhook handler constant is written into `openapi.yaml`. Candidate: `checkout.session.expired` (cleanup of incomplete checkout state) or `customer.subscription.trial_will_end` (if a trial tier is introduced later). Must be confirmed as an explicit pre-condition before Task 1 closes.

- **Daily free-tier cap values** — Proposed `bootstrap=3 / task_gen=20 / spec_gen=10`. Values live in `DAILY_FREE_TIER_LIMITS` in `modules/usage/service.py`. Whether to hard-code or read from env variables is a minor decision; env-configuration is preferred if values are expected to change during early access without a redeploy. Re-decision trigger: upgrade conversion rate data after the first 50 free users.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview