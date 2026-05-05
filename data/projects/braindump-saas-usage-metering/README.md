# spec-doc — SaaS Usage Metering + Free-Tier Paywall

> **MERGED** into `braindump-saas-monetisation.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P2 — required for paid launch (free-tier cap means nothing without billing).
> **Effort**: ~1 day (UsageCounter + decorator + 429 paywall + Angular meter + interceptor).
> **Blocks**: nothing.
> **Depends on**: `braindump-saas-data-layer.md` (UsageCounter FK to user_id),
>                 `braindump-saas-auth-magic-link.md` (decorator reads `g.current_user`),
>                 `braindump-saas-stripe-billing.md` (`User.plan` populated by Stripe webhook).
> **Siblings**: `braindump-saas-stripe-billing.md` (paired — same SaaS-economics bucket).
> **Port from**: bubls `usage` module — near-verbatim, ~180 LOC. Atomic upsert via
>                `INSERT ... ON CONFLICT` is portable across Postgres + SQLite.

## What

Add server-side usage metering: free-tier users get N spec generations per day; the (N+1)th request returns 429 with a structured paywall payload; pro users are uncapped. The Angular client renders a "X/N remaining" meter (UX hint) and a paywall route when the 429 lands (server enforcement). Server is authoritative — client visibility is a hint, not a gate.

Spec-doc currently has zero usage caps. Every authenticated user can call bootstrap and task generation as often as they want, with each call costing real Anthropic API spend (the `braindump-saas-anthropic-sdk-provider.md` flips spec-doc onto the SDK provider, which means the cost is now real). Without metering, a single freeloader can drain the API budget.

Port the `usage` module verbatim from bubls. Bubls's pattern (`UsageCounter` entity + `check_usage_limit` decorator + `incrementer` service) is the durable shape; spec-doc inherits it.

### 1. New module — `api/modules/usage/`

```
modules/usage/
├── __init__.py
├── models.py           # UsageCounter SQLModel
├── service.py          # increment(), get_remaining(), reset_at()
├── middleware.py       # @check_usage_limit decorator
└── tests/
    └── test_middleware.py
```

### 2. UsageCounter entity — `modules/usage/models.py`

```python
from datetime import date
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class UsageCounter(SQLModel, table=True):
    __tablename__ = "spec_doc_usage_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "feature", "date", name="uq_user_feature_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="spec_doc_users.id", index=True)
    feature: str = Field(index=True)              # "bootstrap" | "task_gen" | "spec_gen"
    date: date = Field(default_factory=date.today, index=True)
    count: int = Field(default=0)
```

`(user_id, feature, date)` is the unique key. `count` is bumped via atomic upsert on every charged AI call. Rows accumulate forever (one per user-feature-day); cleanup of old rows is a future maintenance task.

### 3. Service — `modules/usage/service.py`

```python
from datetime import date, datetime, timedelta
from sqlmodel import select, func
from modules.db.engine import get_session
from .models import UsageCounter

DAILY_FREE_TIER_LIMITS = {
    "bootstrap": 3,        # 3 new projects/day for free
    "task_gen":  20,       # 20 task regenerations/day
    "spec_gen":  10,       # 10 generate-spec calls/day
}


def increment(user_id: int, feature: str) -> int:
    """Atomic upsert: bump count for (user, feature, today). Returns the new count."""
    today = date.today()
    with get_session() as db:
        # Upsert via raw SQL — Postgres + SQLite both support ON CONFLICT
        db.execute(text("""
            INSERT INTO spec_doc_usage_counters (user_id, feature, date, count)
            VALUES (:user_id, :feature, :date, 1)
            ON CONFLICT (user_id, feature, date)
            DO UPDATE SET count = spec_doc_usage_counters.count + 1
            RETURNING count
        """), {"user_id": user_id, "feature": feature, "date": today})
        db.commit()
        row = db.execute(text("""
            SELECT count FROM spec_doc_usage_counters
            WHERE user_id=:u AND feature=:f AND date=:d
        """), {"u": user_id, "f": feature, "d": today}).first()
        return row[0]


def get_remaining(user_id: int, feature: str, plan: str) -> int:
    """How many calls this user has left today. Pro = effectively unlimited (-1)."""
    if plan == "pro":
        return -1
    limit = DAILY_FREE_TIER_LIMITS.get(feature, 0)
    today = date.today()
    with get_session() as db:
        row = db.exec(
            select(UsageCounter)
            .where(UsageCounter.user_id == user_id)
            .where(UsageCounter.feature == feature)
            .where(UsageCounter.date == today)
        ).first()
        used = row.count if row else 0
        return max(0, limit - used)


def reset_at_utc() -> datetime:
    """When does the daily counter reset? Tomorrow 00:00 UTC."""
    tomorrow = date.today() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time())
```

### 4. Middleware decorator — `modules/usage/middleware.py`

```python
from functools import wraps
from flask import g, jsonify
from .service import DAILY_FREE_TIER_LIMITS, get_remaining, increment, reset_at_utc


def check_usage_limit(feature: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = g.current_user
            if user.plan == "pro":
                return fn(*args, **kwargs)   # uncapped

            remaining = get_remaining(user.id, feature, user.plan)
            if remaining == 0:
                return jsonify({
                    "error": "free_tier_limit_reached",
                    "feature": feature,
                    "limit": DAILY_FREE_TIER_LIMITS[feature],
                    "reset_at": reset_at_utc().isoformat(),
                    "upgrade_url": "/upgrade",
                }), 429

            response = fn(*args, **kwargs)
            # Only charge on success — error responses don't decrement the counter
            if not isinstance(response, tuple) or response[1] < 400:
                increment(user.id, feature)
            return response
        return wrapper
    return deco
```

`@check_usage_limit("bootstrap")` decorates the AI routes:

```python
# modules/ai/routes.py
@ai_bp.post("/bootstrap-project")
@require_auth
@check_usage_limit("bootstrap")
def bootstrap_project():
    ...
```

The decorator order is `require_auth` → `check_usage_limit` → handler. Auth populates `g.current_user`; metering reads `user.plan` and `user.id`; the handler only runs if usage is under the cap.

### 5. Angular — usage meter component

```typescript
// components/usage-meter.component.ts
@Component({ standalone: true, /* ... */ })
export class UsageMeterComponent {
  feature = input.required<string>();
  remaining = signal<number>(-1);

  constructor(private http: HttpClient, private subscription: SubscriptionService) {
    effect(() => {
      if (this.subscription.isPro()) return;   // hide for pro users
      this.refresh();
    });
  }

  refresh() {
    this.http.get<{remaining: number}>(
      `/api/usage/${this.feature()}/remaining`
    ).subscribe(r => this.remaining.set(r.remaining));
  }
}
```

Template renders "3/3 remaining" pill in the project sidebar. Pulses red at ≤1.

### 6. Status route — `GET /api/usage/<feature>/remaining`

```python
@usage_bp.get("/<feature>/remaining")
@require_auth
def remaining(feature: str):
    if feature not in DAILY_FREE_TIER_LIMITS:
        return jsonify({"error": "unknown feature"}), 400
    return jsonify({
        "feature":   feature,
        "remaining": get_remaining(g.current_user.id, feature, g.current_user.plan),
        "limit":     DAILY_FREE_TIER_LIMITS[feature],
        "reset_at":  reset_at_utc().isoformat(),
    })
```

### 7. Angular — interceptor catches 429

```typescript
// usage-limit.interceptor.ts
intercept(req, next) {
  return next.handle(req).pipe(catchError(err => {
    if (err.status === 429 && err.error?.error === 'free_tier_limit_reached') {
      this.router.navigate(['/upgrade'], {
        queryParams: { feature: err.error.feature, returnUrl: this.router.url },
      });
      return EMPTY;
    }
    return throwError(() => err);
  }));
}
```

The 429 response is the route signal; the interceptor pushes the user into the upgrade flow without the calling component needing to handle it.

## Why now

The Anthropic SDK provider (separate brain dump) is what makes API spend a real cost. Until the SDK ships in production, every spec-doc call uses the developer's local Claude Code subscription — no marginal cost to the deployed service. The moment the SDK lands as the production default, every call hits the org's Anthropic API budget. Without metering, a single user can run ten bootstraps an hour and consume real money on the org's card.

The bubls usage module is in production. Porting is an entity copy + a decorator + ~80 lines of Angular meter + interceptor. The shape — atomic upsert via `INSERT ... ON CONFLICT`, denormalised `User.plan` for fast dispatch, route guard wrapping AI endpoints — is the durable pattern.

Order: **data-layer → auth → billing → metering**. Metering is last because it depends on `user.plan` being populated by the billing webhook and `user.id` being populated by auth.

## What's missing

Two decisions:

1. **What are the daily caps?** The proposed defaults are `bootstrap=3, task_gen=20, spec_gen=10`. Three bootstraps/day is enough for serious evaluation but caps power users. Tune by watching the upgrade-conversion rate: if free-tier users never hit the cap, the limit is too high; if they hit it on day one without upgrading, the limit is too low.

2. **Counter reset window: daily UTC, daily local-tz, or rolling 24h?** Options:
   - (a) Daily UTC midnight (proposed) — simplest, matches bubls
   - (b) Daily user-local midnight — requires storing tz on user
   - (c) Rolling 24-hour window — fairer but more complex DB query
   
   (a) is right for v1. The "reset at midnight UTC" is shown to the user in the paywall payload so they know when they're back in business.

## Explicitly out of scope

- **Per-feature pricing** — one Pro plan, all features uncapped. Tiered pricing (e.g., "AI Pro" vs "Workspace Pro") waits for a real consumer signal.
- **Token-based metering** — counting AI calls is the v1 currency; counting tokens-consumed is more granular but more confusing for the user. Revisit if Anthropic costs per project vary wildly.
- **Per-org usage pools** — single user owns single counter. Org-shared pools require workspaces (out of scope per the auth brain dump).
- **Hard rate limits per minute** — daily cap is the budget guard; per-minute throttle is for abuse protection (separate brain dump if needed).
- **Free-tier downgrade message at limit** — the 429 response carries the upgrade CTA; that's the entire downgrade UX. No email "you've hit your limit" notifications for v1.
- **Counter persistence beyond N days** — old rows stay forever; a cleanup job belongs with a maintenance brain dump if storage becomes a concern.
- **Refunds for failed AI calls** — if `bootstrap_project` succeeds at the route level but the AI call fails inside, the counter is still incremented. The decorator only charges on `< 400` responses, so 5xx returns from the route are not charged. This is the bubls pattern; tune if needed.
