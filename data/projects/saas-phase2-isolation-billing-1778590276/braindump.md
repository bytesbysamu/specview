# SaaS Phase 2: Project Isolation + Billing Wiring

> **Priority**: P1 — second launch gate. Users can register (Phase 1) but see each other's projects and can't pay.
> **Effort**: ~3 days.
> **Blocks**: Phase 4 (onboarding needs per-user project creation).
> **Depends on**: Phase 1 (signup must exist; `@require_auth` + interceptor must be wired).

## What this is

Wire the per-user project filtering that the database models already support but routes ignore, and set up the Stripe credentials so the existing billing code actually charges money.

---

## Current State (fact-checked 2026-05-12)

**What exists and works:**
- `api/modules/billing/routes.py` — 3 Stripe routes: `POST /api/billing/create-checkout-session`, `POST /api/billing/webhook`, `GET /api/billing/status`
- `api/modules/billing/service.py` — complete Stripe adapter (ELA #1 pattern), 6 webhook handlers, sole writer of `User.plan`, lazy Stripe customer creation
- `api/modules/billing/models.py` — `Subscription` model with `user_id`, `plan`, `status`, `stripe_customer_id`, `stripe_subscription_id`, `current_period_start/end`, `canceled_at`
- `api/modules/usage/` — complete: `UsageCounter` model, `@check_usage_limit` decorator, daily caps (bootstrap=30, task_gen=100, spec_gen=50), atomic upsert, pro bypass
- `api/modules/data/projects/models.py` — `Project` model exists in DB migration with `user_id` FK
- Database: `user`, `subscription`, `usage_counter` tables all created in `0001_initial_schema.py`

**What's broken or missing:**
- **Project routes don't filter by user_id.** `api/modules/data/projects/routes.py` uses `@require_auth` but every route calls `service.py` functions that read from the filesystem globally. The `user_id` FK on the Project model is never checked. All 41 projects are visible to all authenticated users.
- **Project routes use filesystem service, not ProjectRepository.** Routes call `service.list_projects(projects_dir)` which reads `project.json` files from disk. The SQLModel `Project` + `ProjectRepository` pattern exists in the models but is not wired into routes.
- **Stripe env vars not set.** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `FRONTEND_URL` are not in docker-compose.yml or .env. The billing service reads them at call time (`_stripe_secret_key()` returns empty string), so Stripe calls will fail silently.
- **No Angular SubscriptionService.** The generated DTO `BillingStatusResponse` exists from openapi codegen, but there's no Angular service to call `/api/billing/status` or trigger checkout. No upgrade page, no usage meter component.

---

## Task 1 — Per-User Project Isolation

> **Effort**: 1 day
> **This is the multi-tenancy gate.** Without it, User A sees User B's projects.

### Current route → service flow (broken)

```
GET /api/projects → @require_auth → service.list_projects(PROJECTS_DIR)
                    g.current_user exists but is NEVER used for filtering
```

### What needs to change

**Option A — Wire ProjectRepository into routes (clean, more work):**
Replace filesystem `service.py` calls with `ProjectRepository` calls that filter by `g.current_user.id`. This means the SQLModel `Project` table becomes the source of truth for project metadata, and the filesystem stores the markdown files.

**Option B — Add user_id filter to filesystem service (quick, less clean):**
Add `user_id` parameter to `service.list_projects()`, store `user_id` in `project.json`, filter at read time.

**Recommended: Option A.** The ProjectRepository and Project model already exist. This is the intended architecture. Option B would be a temporary hack that delays the inevitable migration.

### Changes for Option A

1. Wire `ProjectRepository` as the project listing source:
```python
# routes.py
@projects_bp.get("/")
@require_auth
def list_all():
    user_id = g.current_user.id
    projects = project_repository.list_for_user(user_id)
    return jsonify([p.dict() for p in projects])
```

2. Every route that accesses a project must verify ownership:
```python
@projects_bp.get("/<project_id>")
@require_auth
def get_project_route(project_id):
    project = project_repository.get_by_slug(g.current_user.id, project_id)
    if not project:
        return jsonify({"error": "not found"}), 404
    # ... read files from filesystem using project.id
```

3. Filesystem remains the file content store: `data/projects/<slug>/braindump.md` etc. The DB stores metadata + ownership.

### Migration of existing projects

All 41 existing projects need rows in the `project` table assigned to Sam's user:

```python
# scripts/migrate_filesystem_to_db.py
"""For each data/projects/<slug>/ on disk:
    1. Read project.json for name, createdAt
    2. Insert Project row: user_id=1 (Sam), slug=<dir-name>, name=<from json>
    3. Count .md files → file_count
"""
```

Idempotent (skip if slug exists). Run once after deploy.

---

## Task 2 — Stripe Credentials + Activation

> **Effort**: 0.5 days
> **No code changes needed.** The billing module is complete — it just needs credentials.

### Steps

1. Create a Stripe account (or use existing test mode)
2. Create a Product "Specview Pro" with a Price of $29/mo
3. Set up webhook endpoint in Stripe Dashboard pointing to `https://specview.app/api/billing/webhook`
4. Subscribe to events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`, `invoice.upcoming`
5. Add to `.env` and Coolify:

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
FRONTEND_URL=https://specview.app
```

6. Test locally with Stripe CLI:
```bash
stripe listen --forward-to localhost:8095/api/billing/webhook
stripe trigger checkout.session.completed
```

7. Verify `GET /api/billing/status` returns `{"plan": "pro", "status": "active", ...}` after a successful checkout.

---

## Task 3 — Angular Subscription UI

> **Effort**: 1 day
> **Port from**: bubls Angular billing components (near-verbatim).

### SubscriptionService

```typescript
@Injectable({ providedIn: 'root' })
export class SubscriptionService {
  plan = signal<'free' | 'pro'>('free');
  isPro = computed(() => this.plan() === 'pro');

  constructor(private http: HttpClient) {}

  async refresh(): Promise<void> {
    const res = await firstValueFrom(
      this.http.get<BillingStatusResponse>('/api/billing/status')
    );
    this.plan.set(res.plan);
  }

  async startCheckout(): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<{ url: string }>('/api/billing/create-checkout-session', {})
    );
    window.location.href = res.url;
  }
}
```

### Upgrade page

Simple page with pricing copy + "Upgrade to Pro" button that calls `subscriptionService.startCheckout()`. No custom payment form — Stripe Checkout handles everything.

### Usage meter

"X/N remaining" pill in the status bar area. Hidden for Pro users. Red when at ≤1 remaining.

### 429 interceptor

Catch 429 responses from `@check_usage_limit` → navigate to `/upgrade` with a message.

---

## Task 4 — Existing Projects Migration Script

> **Effort**: 0.5 days

```python
# scripts/migrate_filesystem_to_db.py
"""One-shot migration: filesystem projects → DB metadata rows.

For each data/projects/<slug>/ on disk:
    1. Read project.json for name, createdAt, priority
    2. Count .md files
    3. INSERT into project table: user_id=1, slug=<dir-name>, name=<from json>
    4. Skip if slug already exists (idempotent)

After running:
    - All 41 projects belong to user_id=1 (Sam)
    - Routes can now filter by user_id
    - Filesystem still stores the actual markdown content
"""
```

Run before deploy. Verify with `SELECT count(*) FROM project` = 41.

---

## Files to Change

| File | Change |
|------|--------|
| `api/modules/data/projects/routes.py` | Wire ProjectRepository, add user_id filtering to every route |
| `api/modules/data/projects/repository.py` | Implement ProjectRepository Protocol (if not already) |
| `.env` | Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `FRONTEND_URL` |
| `docker-compose.override.yml` | Add Stripe env var references |
| `web-ng/src/app/services/subscription.service.ts` | New — plan signal, checkout, refresh |
| `web-ng/src/app/components/upgrade/` | New — upgrade page with pricing |
| `web-ng/src/app/app.component.html` | Add usage meter pill |
| `scripts/migrate_filesystem_to_db.py` | New — one-shot filesystem → DB migration |

## Success Criteria

- [ ] User A cannot see User B's projects
- [ ] All 41 existing projects assigned to Sam's user_id in DB
- [ ] `GET /api/projects` returns only projects owned by the authenticated user
- [ ] Stripe test mode checkout completes end-to-end ($29 charge)
- [ ] Webhook flips `User.plan` from "free" to "pro" after checkout
- [ ] `@check_usage_limit` blocks 4th bootstrap for free-tier user with clear upgrade prompt
- [ ] Angular shows plan status, usage meter, and upgrade button
- [ ] 429 response navigates to upgrade page
