# spec-doc — SaaS Monetisation (Stripe billing + free-tier metering)

> **Priority**: P2 — required for paid public launch.
> **Effort**: ~2 days (Stripe billing + usage metering combined).
> **Blocks**: nothing — public launch gate.
> **Depends on**: persistence (Subscription + UsageCounter need user_id FKs), auth (decorator reads `g.current_user`).
> **Siblings**: `braindump-saas-persistence.md` (DB layer ships sister tables), auth dump (User.plan denormalised here).
> **Consolidates**: former `braindump-saas-stripe-billing.md` + `braindump-saas-usage-metering.md`.
> **Port from**: bubls `billing` + `usage` modules — near-verbatim, ~430 LOC combined. Stripe Checkout + webhook + atomic-upsert metering are all generic patterns.

## What

Charge money + meter the free tier. Stripe Checkout handles cards (zero PCI scope). Stripe webhooks are the **sole writer** of subscription state. Free-tier users get N spec generations per day; (N+1)th request returns 429 → Angular routes to the upgrade page. Pro users uncapped. **`User.plan` is denormalised** from Subscription so every per-request gate is a single-field read, not a join.

The two halves ship together because they share the `User.plan` field and the upgrade flow: billing populates `plan='pro'`; metering reads `plan` to skip the cap check. Splitting them across two brain dumps obscures that one is the consumer of the other.

### 1. Subscription entity + 6 webhook handlers

```python
# modules/billing/models.py
class Subscription(SQLModel, table=True):
    __tablename__ = "spec_doc_subscriptions"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="spec_doc_users.id", unique=True, index=True)
    plan: str = Field(default="free")                        # "free" | "pro"
    status: str = Field(default="active")                    # "active" | "past_due" | "canceled" | "incomplete"
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    canceled_at: datetime | None = None
```

Webhook handlers (Stripe is the sole writer; signed payloads enforced):

| Event | Action |
|---|---|
| `checkout.session.completed` | Look up user by `client_reference_id`; set `plan='pro'`, status=active; record IDs; **also update `User.plan`** |
| `customer.subscription.updated` | Update `current_period_end`, `status`; mark `canceled_at` if `cancel_at_period_end=True` |
| `customer.subscription.deleted` | Set `plan='free'`, `status='canceled'`; **update `User.plan='free'`** |
| `invoice.payment_failed` | `status='past_due'` (downgrade follows via `subscription.updated` after grace) |
| `invoice.paid` | `status='active'`; bump `current_period_end` from invoice |

### 2. Three billing routes

```python
@billing_bp.post("/create-checkout-session")
@require_auth
def create_checkout_session():
    customer_id = get_or_create_stripe_customer(g.current_user)    # lazy — first checkout, not signup
    session = stripe.checkout.Session.create(
        customer=customer_id, mode="subscription",
        line_items=[{"price": os.environ["STRIPE_PRICE_ID_PRO_MONTHLY"], "quantity": 1}],
        success_url=f"{os.environ['APP_URL']}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{os.environ['APP_URL']}/upgrade",
        client_reference_id=str(g.current_user.id),
    )
    return jsonify({"checkout_url": session.url})

@billing_bp.post("/webhook")
def webhook():
    event = stripe.Webhook.construct_event(request.get_data(), request.headers["Stripe-Signature"],
                                            os.environ["STRIPE_WEBHOOK_SECRET"])
    handler = EVENT_HANDLERS.get(event["type"])
    if handler: handler(event["data"]["object"])
    return jsonify({"received": True})

@billing_bp.get("/status")
@require_auth
def status():
    sub = current_app.subscription_repository.get_for_user(g.current_user.id)
    return jsonify({
        "plan": sub.plan, "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "manage_url": _customer_portal_url(sub.stripe_customer_id) if sub.stripe_customer_id else None,
    })
```

`manage_url` returns a Stripe Customer Portal session — Stripe-hosted self-service for plan changes/cancellation/payment-method updates. **No spec-doc billing UI beyond the upgrade button.**

### 3. UsageCounter entity + decorator

```python
# modules/usage/models.py
class UsageCounter(SQLModel, table=True):
    __tablename__ = "spec_doc_usage_counters"
    __table_args__ = (UniqueConstraint("user_id", "feature", "date"),)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="spec_doc_users.id", index=True)
    feature: str = Field(index=True)              # "bootstrap" | "task_gen" | "spec_gen"
    date: date = Field(default_factory=date.today, index=True)
    count: int = Field(default=0)


# modules/usage/service.py
DAILY_FREE_TIER_LIMITS = {"bootstrap": 3, "task_gen": 20, "spec_gen": 10}


def increment(user_id, feature) -> int:
    """Atomic upsert via INSERT ... ON CONFLICT — works on Postgres + SQLite."""
    with get_session() as db:
        db.execute(text("""
            INSERT INTO spec_doc_usage_counters (user_id, feature, date, count)
            VALUES (:u, :f, :d, 1)
            ON CONFLICT (user_id, feature, date)
            DO UPDATE SET count = spec_doc_usage_counters.count + 1
        """), {"u": user_id, "f": feature, "d": date.today()})
        db.commit()
```

```python
# modules/usage/middleware.py
def check_usage_limit(feature: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = g.current_user
            if user.plan == "pro":
                return fn(*args, **kwargs)            # uncapped
            remaining = get_remaining(user.id, feature, user.plan)
            if remaining == 0:
                return jsonify({
                    "error": "free_tier_limit_reached",
                    "feature": feature, "limit": DAILY_FREE_TIER_LIMITS[feature],
                    "reset_at": reset_at_utc().isoformat(),
                    "upgrade_url": "/upgrade",
                }), 429
            response = fn(*args, **kwargs)
            if not isinstance(response, tuple) or response[1] < 400:
                increment(user.id, feature)            # only charge on < 400 responses
            return response
        return wrapper
    return deco
```

Decorator order on routes: `@require_auth → @check_usage_limit("feature") → handler`.

### 4. Angular surface

```typescript
// services/subscription.service.ts
export class SubscriptionService {
  plan = signal<'free'|'pro'>('free');
  isPro = computed(() => this.plan() === 'pro');
  async refresh() { this.plan.set((await firstValueFrom(this.http.get<BillingStatus>('/api/billing/status'))).plan); }
  async startCheckout() {
    const { checkout_url } = await firstValueFrom(this.http.post<{checkout_url:string}>('/api/billing/create-checkout-session', {}));
    window.location.href = checkout_url;
  }
}

// guards/pro.guard.ts — canActivate: subscription.isPro() ? true : router.parseUrl('/upgrade?returnUrl='+state.url)

// components/usage-meter.component.ts — "X/N remaining" pill, hidden for pro, red at ≤1

// interceptors/usage-limit.interceptor.ts — catch 429 → router.navigate(['/upgrade'])
// interceptors/auth.interceptor.ts — attach Bearer from supabase session

// pages/upgrade.page.ts — pricing copy + Pro CTA → subscription.startCheckout()
```

All five Angular pieces port near-verbatim from bubls.

### 5. .env additions

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
APP_URL=https://spec-doc.yourdomain.com
```

### 6. Single Stripe Price ID at launch

One product, one price: `Pro Monthly` at $X/mo. No annual, no team plan, no usage-based pricing. Bubls launched with the same minimum.

## Why now

Persistence brain dump is queued; once Subscription + UsageCounter tables exist there's no reason not to wire them. **The Anthropic SDK provider brain dump makes API spend a real cost** — without metering, a single freeloader drains the org's API budget on day one of public access.

The bubls billing + usage modules are in production. Porting is a `cp -r` plus the table-name change (`superapp_*` → `spec_doc_*`) — ~430 LOC near-verbatim. The shape (webhook is sole writer, `User.plan` denormalised, customer portal owns self-service) is the durable pattern; spec-doc inherits it.

## What's missing

Two decisions:

1. **Daily caps** — proposed `bootstrap=3, task_gen=20, spec_gen=10`. Tune by watching upgrade-conversion rate.
2. **Counter reset window** — daily UTC midnight (proposed) vs daily user-local vs rolling 24h. UTC midnight is right for v1; matches bubls.

## Explicitly out of scope

- **Annual / team / lifetime plans** — single Price ID for v1; annual is one extra Price ID later.
- **Coupon / discount codes** — Stripe supports them; UI defers.
- **Per-feature pricing** — one Pro plan, all features uncapped.
- **Token-based metering** — counting AI calls is the v1 currency; per-token is more granular but more confusing.
- **Per-org usage pools** — single user owns single counter; org-shared pools require workspaces (separate brain dump).
- **Per-minute rate limit** (abuse) — daily cap is the budget guard; per-IP throttle belongs in cloud LB / Cloudflare.
- **Refund automation** — Stripe Dashboard manually for v1.
- **In-app purchase / RevenueCat** — mobile-only.
- **PCI compliance** — Stripe Checkout means cards never touch spec-doc; PCI scope is zero.
- **Email receipts / invoices** — Stripe sends them automatically.
