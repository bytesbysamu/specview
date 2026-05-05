# spec-doc — SaaS Billing via Stripe Checkout + Webhook

> **MERGED** into `braindump-saas-monetisation.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P2 — required for paid launch.
> **Effort**: ~1 day (3 routes + 6 webhook handlers + Subscription entity + Angular service).
> **Blocks**: usage metering (gates on `User.plan` denormalised here).
> **Depends on**: `braindump-saas-data-layer.md` (Subscription FK to user_id),
>                 `braindump-saas-auth-magic-link.md` (Stripe customer needs `User.id`).
> **Siblings**: `braindump-saas-usage-metering.md` (paired — together = SaaS economics).
> **Port from**: bubls `billing` module — near-verbatim, ~250 LOC. Stripe SDK calls + webhook
>                signature verification + lazy customer creation are all generic.

## What

Add Stripe-backed subscription billing — same shape bubls ships. Stripe Checkout handles card collection, SCA, and receipts (zero PCI scope on the spec-doc backend). Stripe webhooks are the **sole writer** of subscription state into the `Subscription` table. The Angular client never writes — it only reads `GET /api/billing/status` to render the paywall and the meter.

Spec-doc has zero monetisation today. To ship as SaaS, it needs a free→pro upgrade flow that takes payment without spec-doc touching card data or maintaining session state across billing changes. Stripe's hosted Checkout + webhook event model is the canonical answer; bubls already has it in production.

Port the `billing` module verbatim from bubls. The shape is well-trodden: three routes (create checkout session, webhook receiver, status read), one entity (`Subscription`), one Angular service (`SubscriptionService`).

### 1. New module — `api/modules/billing/`

```
modules/billing/
├── __init__.py
├── models.py           # Subscription SQLModel
├── service.py          # checkout session creation, webhook event mapping
├── routes.py           # POST /create-checkout-session, POST /webhook, GET /status
└── tests/
    └── test_webhook.py # all 6 Stripe event types we handle
```

### 2. Subscription entity — `modules/billing/models.py`

```python
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Subscription(SQLModel, table=True):
    __tablename__ = "spec_doc_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="spec_doc_users.id", unique=True, index=True)

    plan: str = Field(default="free")              # "free" | "pro"
    status: str = Field(default="active")          # "active" | "past_due" | "canceled" | "incomplete"

    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)

    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

Stripe customer is created **lazily on first checkout** (per bubls — avoids phantom customers for users who never pay). The `Subscription` row exists for every user from signup; `plan='free'` is the default state.

### 3. Routes — `modules/billing/routes.py`

```python
import stripe
from flask import Blueprint, current_app, g, jsonify, request
from modules.auth.middleware import require_auth
from .service import create_or_update_subscription_from_event, get_or_create_stripe_customer

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


@billing_bp.post("/create-checkout-session")
@require_auth
def create_checkout_session():
    user = g.current_user
    customer_id = get_or_create_stripe_customer(user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": os.environ["STRIPE_PRICE_ID_PRO_MONTHLY"], "quantity": 1}],
        success_url=f"{os.environ['APP_URL']}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{os.environ['APP_URL']}/upgrade",
        client_reference_id=str(user.id),
    )
    return jsonify({"checkout_url": session.url})


@billing_bp.post("/webhook")
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ["STRIPE_WEBHOOK_SECRET"]
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"error": "invalid signature"}), 400

    create_or_update_subscription_from_event(event)
    return jsonify({"received": True})


@billing_bp.get("/status")
@require_auth
def status():
    sub = current_app.subscription_repository.get_for_user(g.current_user.id)
    return jsonify({
        "plan":   sub.plan,
        "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "canceled_at":        sub.canceled_at.isoformat() if sub.canceled_at else None,
        "manage_url":         _customer_portal_url(sub.stripe_customer_id) if sub.stripe_customer_id else None,
    })
```

The webhook signature check is non-negotiable — Stripe explicitly rejects unsigned payloads as a security boundary.

`manage_url` returns a Stripe Customer Portal session — Stripe-hosted self-service for plan changes, cancellations, payment-method updates. Zero spec-doc surface for billing UI beyond the upgrade button.

### 4. Webhook event handlers — `modules/billing/service.py`

Six event types to handle (the bubls set):

| Event | Action |
|---|---|
| `checkout.session.completed` | Look up user by `client_reference_id`; set `plan='pro'`, status='active'; record subscription_id |
| `customer.subscription.updated` | Update `current_period_end`, `status`; if `cancel_at_period_end=True`, mark `canceled_at` |
| `customer.subscription.deleted` | Set `plan='free'`, `status='canceled'` |
| `invoice.payment_failed` | Set `status='past_due'`; downgrade after Stripe's grace period via `subscription.updated` |
| `invoice.paid` | Set `status='active'`; bump `current_period_end` from invoice |
| `customer.subscription.trial_will_end` | (optional) email user; not implemented for v1 |

```python
EVENT_HANDLERS = {
    "checkout.session.completed":         _handle_checkout_completed,
    "customer.subscription.updated":      _handle_subscription_updated,
    "customer.subscription.deleted":      _handle_subscription_deleted,
    "invoice.payment_failed":             _handle_invoice_failed,
    "invoice.paid":                       _handle_invoice_paid,
}


def create_or_update_subscription_from_event(event: dict) -> None:
    handler = EVENT_HANDLERS.get(event["type"])
    if handler is None:
        return  # event types we don't care about — safe to ignore
    handler(event["data"]["object"])
```

**The User.plan field is the canonical read source for "is this user pro right now?"** — it's denormalised from `Subscription` so the auth and metering layers don't need to join. The webhook handler updates both atomically.

### 5. Angular — `SubscriptionService`

```typescript
@Injectable({ providedIn: 'root' })
export class SubscriptionService {
  plan = signal<'free' | 'pro'>('free');
  isPro = computed(() => this.plan() === 'pro');

  async refresh() {
    const status = await firstValueFrom(this.http.get<BillingStatus>('/api/billing/status'));
    this.plan.set(status.plan);
  }

  async startCheckout() {
    const { checkout_url } = await firstValueFrom(
      this.http.post<{checkout_url: string}>('/api/billing/create-checkout-session', {})
    );
    window.location.href = checkout_url;  // Stripe redirect
  }
}
```

Called once at app boot via `APP_INITIALIZER`; refreshed after Stripe redirect-back.

### 6. Pricing decision: monthly only (v1)

One Stripe Price ID, one plan: `Pro Monthly` at `$X/mo`. No annual yet, no team plan, no usage-based pricing. Bubls launched with the same minimum.

Add the env var: `STRIPE_PRICE_ID_PRO_MONTHLY=price_...`. Stripe Dashboard creates the product + price; the env var pins which one this app sells.

### 7. .env additions

```
STRIPE_SECRET_KEY=sk_live_...                   # server-only
STRIPE_WEBHOOK_SECRET=whsec_...                 # webhook verification
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
APP_URL=https://spec-doc.yourdomain.com         # for Checkout success/cancel URLs
```

## Why now

The auth + data-layer brain dumps unblock multi-tenant primitives. Without billing, every user is forever on the free tier — there is no monetisation surface, and no enforceable distinction between casual and paying users for the metering brain dump to gate against. Billing is the load-bearing piece for shipping a SaaS that pays for its hosting + Anthropic API costs.

The bubls billing module is in production, tested against real Stripe webhooks. Porting it is a `cp -r` plus the table-name change (`superapp_subscriptions` → `spec_doc_subscriptions`). The shape — webhook is the sole writer, plan signal is denormalised, customer portal handles self-service — is the durable pattern; spec-doc inherits it.

This must land before metering. The metering brain dump's free-tier cap means nothing if there's no way for a user to upgrade out of it. Order: **data-layer → auth → billing → metering → landing page**.

## What's missing

One decision: **annual plans + team plans at launch?** Options:
- (a) Monthly only (proposed) — minimum surface, fastest to ship, matches bubls launch
- (b) Monthly + Annual — Annual is one extra Stripe Price ID + one toggle in the upgrade UI; ~half day
- (c) Monthly + Annual + Team — adds workspace/team plumbing (out of scope for the multi-tenant v1)

(a) is right. Annual is a one-PR addition once the monthly flow is proven. Team plans require workspace sharing primitives spec-doc doesn't have yet.

## Explicitly out of scope

- **PCI compliance** — Stripe Checkout means cards never touch spec-doc; PCI scope is zero.
- **Refund automation** — handled in Stripe Dashboard manually for v1. Automate when refund volume is a problem.
- **Annual / lifetime / team plans** — see What's Missing.
- **Coupon / discount codes** — Stripe Checkout supports them; the upgrade UI doesn't expose them yet.
- **Affiliate / referral system** — out of scope; revisit when launch reveals an organic referral pattern worth automating.
- **In-app purchase (iOS / Android)** — spec-doc is web-only; if/when an app ships, IAP joins the conversation (bubls's app-store-launch epic addresses this).
- **Tax handling** — Stripe Tax adds itself when enabled in Dashboard; no spec-doc code change.
- **Email receipts / invoices** — Stripe sends them automatically.
