# Specview SaaS Launch Readiness

## What this is

Everything needed to go from "self-hosted tool for Sam" to "SaaS product that other people can sign up for and pay to use." The app works end-to-end for a single user — the gap is multi-tenancy, persistence, billing enforcement, security hardening, reliability, and onboarding flow.

This braindump consolidates the legacy SaaS braindump collection from `~/Projects/2026/spec-doc/projects/` into the current Specview project structure. Six legacy braindumps are merged here:

| Legacy braindump | Mapped to | Status |
|------------------|-----------|--------|
| `braindump-saas-auth-magic-link.md` | Task 1 — Auth | Verbatim port, updated for current codebase |
| `braindump-saas-persistence.md` | Task 2 — Persistence | Verbatim port (consolidates data-layer + git-storage) |
| `braindump-saas-monetisation.md` | Task 3 — Monetisation | Verbatim port (consolidates stripe-billing + usage-metering) |
| `braindump-saas-reliability.md` | Task 4 — Reliability | Verbatim port (consolidates async + streaming + retry + cancel) |
| `braindump-saas-operations.md` | Task 6 — Operations | Verbatim port (consolidates observability + CI + deploy) |
| `braindump-saas-anthropic-sdk-provider.md` | Task 7 — SDK Provider | Verbatim port; P0 auth decision defers this to SaaS launch |

Four additional legacy braindumps were already merged into the above before this consolidation:
- `braindump-saas-data-layer.md` → merged into `saas-persistence.md`
- `braindump-saas-git-storage-layer.md` → merged into `saas-persistence.md`
- `braindump-saas-stripe-billing.md` → merged into `saas-monetisation.md`
- `braindump-saas-usage-metering.md` → merged into `saas-monetisation.md`
- `braindump-saas-observability.md` → merged into `saas-operations.md`

**Cross-reference:** The GTM project (`specview-saas-gtm-1778233000`) owns Stripe wiring, Show HN launch, analytics, and email capture. This project owns the infrastructure those depend on.

---

## Current State

What exists today:
- **Auth**: JWT auth with bcrypt passwords, single-user (`sam@specview.app / salt`). No signup, no password reset, no email verification. The `@require_auth` decorator and `User` model already exist in `api/modules/auth/`.
- **Billing**: Stripe integration module exists (`api/modules/billing/`), but it's not gating actual usage. `Subscription` model exists in `billing/models.py`.
- **Usage tracking**: Usage module exists (`api/modules/usage/`), rate limiting decorators exist (`@check_usage_limit`), daily caps defined (`bootstrap=30, task_gen=100, spec_gen=50`). Not tied to billing tiers.
- **Projects**: Filesystem-based storage at `data/projects/<id>/`. All projects globally visible — no per-user isolation. No version history.
- **Database**: PostgreSQL on Neon, Alembic migrations in place. SQLModel models for `User` and `Usage` exist.
- **Chain provider**: CLI provider with Claude Max OAuth (see P0 project). SDK provider (`providers/claude.py`) exists but is not the production default.
- **CORS**: Set to `"*"` — wide open.
- **Secrets**: `DATABASE_URL` and `JWT_SECRET` hardcoded in `docker-compose.yml`.
- **Landing page**: Marketing page exists but CTA doesn't connect to a real signup flow.

---

## Dependency Chain

```
Task 2 (Persistence) ← foundational, all FKs depend on it
    ↓
Task 1 (Auth) ← gates every authenticated route
    ↓
Task 3 (Monetisation) ← depends on User.id + Subscription table
    ↓
Task 4 (Reliability) ← depends on WorkflowRuntime + SDK provider
    ↓
Task 5 (Security) ← hardens everything above
Task 6 (Operations) ← enables debugging everything above
Task 7 (SDK Provider) ← production AI provider (deferred from P0)
    ↓
Task 8 (Onboarding) ← last; needs everything working
```

---

## Task 1 — Multi-Tenant Auth via Supabase Magic Link

> **Priority**: P1 — gates every authenticated route.
> **Effort**: ~1 day (User entity + JWKS validation + `@require_auth` + Angular interceptor).
> **Blocks**: billing (Stripe customer needs `User.id`), metering (UsageCounter needs `user_id`),
>             every per-tenant query in projects/, ai/ routes.
> **Depends on**: persistence (User entity sits in the SQL store).
> **Port from**: bubls `auth` module. Near-verbatim — JWKS + JWT decode pattern is generic.

Add user auth using Supabase's magic-link flow — same shape bubls ships in production. No passwords, no OAuth complexity, no PCI/SOC2 burden. The Angular client requests a magic link by email; Supabase emails the user; the user clicks; the SPA receives a JWT; every API request carries it as `Authorization: Bearer <token>`. Flask validates the JWT, extracts the Supabase user id, looks up (or creates) the matching `User` row, and injects it into the request context.

**Decision: magic-link over email/password.** The current codebase has bcrypt JWT auth, but for SaaS launch magic-link is simpler: zero password storage, zero password reset flow, zero email verification flow. Supabase free tier covers everything for the early phase.

### New module — `api/modules/auth/`

```
modules/auth/
├── __init__.py
├── models.py           # User SQLModel
├── service.py          # validate_jwt, get_or_create_user, get_current_user
├── middleware.py       # @require_auth decorator + before_request hook
├── routes.py           # GET /api/me — returns current user
└── tests/
    └── test_service.py
```

### User entity — `modules/auth/models.py`

```python
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "spec_doc_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    supabase_id: str = Field(unique=True, index=True)   # Supabase auth.users.id (uuid)
    email: str = Field(unique=True, index=True)
    plan: str = Field(default="free")                    # "free" | "pro"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
```

`plan` is denormalised here so the auth layer can answer "is this user pro?" without joining `Subscription`. The Stripe webhook syncs the field.

### JWT validation — `modules/auth/service.py`

```python
import os
import jwt
from jwt import PyJWKClient

_SUPABASE_URL = os.environ.get("SUPABASE_URL")  # e.g. https://abcd.supabase.co
_JWKS = PyJWKClient(f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json")


def validate_jwt(token: str) -> dict:
    """Validate a Supabase JWT; return the claims dict."""
    signing_key = _JWKS.get_signing_key_from_jwt(token).key
    return jwt.decode(token, signing_key, algorithms=["RS256"], audience="authenticated")
```

### Per-request user injection — `modules/auth/middleware.py`

```python
from functools import wraps
from flask import request, g, jsonify
from modules.db.engine import get_session
from .models import User
from .service import validate_jwt

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401
        try:
            claims = validate_jwt(auth[7:])
        except Exception as exc:
            return jsonify({"error": f"invalid token: {exc}"}), 401

        with get_session() as db:
            user = db.exec(
                select(User).where(User.supabase_id == claims["sub"])
            ).first()
            if user is None:
                user = User(supabase_id=claims["sub"], email=claims.get("email", ""))
                db.add(user); db.commit(); db.refresh(user)
            g.current_user = user
        return fn(*args, **kwargs)
    return wrapper
```

The decorator goes on every route in `projects/`, `ai/`. The `/health` and `/api/auth/*` routes stay public.

### Angular — Supabase JS client

```typescript
// services/auth.service.ts
import { createClient, Session, User } from '@supabase/supabase-js';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private supabase = createClient(
    environment.supabaseUrl,
    environment.supabaseAnonKey,
  );
  user: WritableSignal<User | null> = signal(null);

  async signInWithEmail(email: string) {
    return this.supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
  }

  async signOut() { await this.supabase.auth.signOut(); }
}
```

```typescript
// auth.interceptor.ts — attaches Bearer to every /api/* request
intercept(req, next) {
  return from(this.supabase.auth.getSession()).pipe(
    switchMap(({ data: { session } }) => {
      if (session) {
        req = req.clone({
          setHeaders: { Authorization: `Bearer ${session.access_token}` },
        });
      }
      return next.handle(req);
    })
  );
}
```

Magic-link click lands on `/auth/callback`; Supabase JS picks up the token from the URL fragment and stores the session in localStorage.

### Dev bypass

What happens to the existing single-user filesystem dev workflow? Decision:
- (a) **Auth required everywhere; dev mode pre-seeds a single user (proposed)** — `DEV_BYPASS_AUTH=true` env injects `g.current_user` as a fixed local user, no Supabase call. Production refuses to start with that flag set.
- (b) Routes split into authed (`/api/v2/*`) and unauthed (`/api/*`) — doubles maintenance.
- (c) Auth required everywhere from day one — blocks dev iteration until Supabase provisioned locally.

**(a) is right.** Dev iteration speed matters; the bypass is one env-flag check; production-mode refuses to honour it.

### .env additions

```
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_ANON_KEY=...                  # Angular env, not server
SUPABASE_SERVICE_ROLE_KEY=...          # server-only, used by webhooks
```

### Explicitly out of scope

- Apple Sign-In, Google OAuth — magic link covers the web SaaS use case; native auth providers land if/when an iOS app is built.
- Two-factor / TOTP — Supabase supports it; enable per-user when requested.
- Custom email templates — Supabase defaults are fine for early phase.
- Workspace / team / org primitives — single user owns single set of projects. Multi-user workspaces wait for a paying team customer.

---

## Task 2 — SaaS Persistence (DB metadata + git for markdown)

> **Priority**: P1 — foundational. Every other SaaS task needs `user_id` foreign keys.
> **Effort**: ~2 days (DB layer + git layer + migration script + tests).
> **Blocks**: auth (User entity sits in DB), monetisation (Subscription/UsageCounter need user_id), reliability (executions reference projects), every per-tenant query.
> **Depends on**: nothing — paired internally; ships as one Phase 1 unit.
> **Consolidates**: former `braindump-saas-data-layer.md` + `braindump-saas-git-storage-layer.md`.
> **Port from**: bubls `kw-data` SQLModel + Alembic shape (near-verbatim, ~1 day). Git-store is net-new.

Two-tier storage. **SQL for metadata** (User, Project, Subscription, UsageCounter — anything that changes by row). **Git for markdown content** (one repo per project — anything that changes by line). Each handles what it's best at; combining them is what avoids inventing a worse SQL-blob versioning system or a clumsy git-as-database hack.

The `Project` table holds a pointer (`git_repo_path` + `latest_commit_sha`) to its git repo. Every `update_file()` becomes a `git commit` via `pygit2`. History (`git log`), diff (`git diff`), revert (`git checkout`) come free as three new endpoints. The future "Connect GitHub" upsell becomes a `git push` to the user's repo.

### DB layer — `modules/db/`

```python
# modules/db/engine.py
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./spec_doc.db")
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True,
                      connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

def get_session() -> Session: return Session(ENGINE)
```

Production: Postgres on Neon. Dev: SQLite. Same DDL — avoid Postgres-specific types.

### Entities (metadata only)

```python
# modules/projects/models.py
class Project(SQLModel, table=True):
    __tablename__ = "spec_doc_projects"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="spec_doc_users.id", index=True)
    name: str
    slug: str = Field(unique=True, index=True)
    git_repo_path: str                                    # /data/projects/<id>/.git
    latest_commit_sha: str | None = None                 # advances on every update_file
    file_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**No `ProjectFile` table.** Markdown lives in git. Subscription + UsageCounter ship in the monetisation task (paired tables, same migration).

### Repository pattern (metadata-only)

```python
class ProjectRepository(Protocol):
    def create(self, user_id: int, name: str) -> Project: ...
    def get_by_slug(self, user_id: int, slug: str) -> Project | None: ...
    def list_for_user(self, user_id: int) -> list[Project]: ...
    def touch(self, project_id: int, new_commit_sha: str) -> None: ...
    def delete(self, project_id: int) -> None: ...
```

`create()` is atomic: insert row → call `git_store.init_repo(project_id)` → if git fails, rollback. `touch()` is called by the git layer after every successful commit, advancing `latest_commit_sha`.

### Git layer — `modules/git_store/` (six public ops via `pygit2`)

```python
def init_repo(project_id) -> Path                       # bare or working repo + initial commit
def write_file(project_id, filename, content, msg=None) -> str    # returns new SHA
def read_file(project_id, filename, ref="HEAD") -> str
def list_files(project_id, ref="HEAD") -> list[str]
def get_history(project_id, filename=None, limit=50) -> list[dict]
def get_diff(project_id, filename, from_sha, to_sha="HEAD") -> str
def revert_file(project_id, filename, to_sha) -> str
def delete_file(project_id, filename, msg=None) -> str
```

Per-project repo at `/data/projects/<id>/.git/`. Auto-commit author = `spec-doc <system@spec-doc.app>`. Commit messages by call site: `feat(<filename>): generated by bootstrap`, `edit(<filename>): user edit`, `revert(<filename>): to <short-sha>`.

### Three new endpoints (free with the git layer)

- `GET /api/projects/<slug>/files/<filename>/history` → list of commits touching this file
- `GET /api/projects/<slug>/files/<filename>/diff?from=<sha>&to=<sha>` → unified diff
- `POST /api/projects/<slug>/files/<filename>/revert` `{sha: ...}` → restore to old version

### Wiring into existing routes

```python
@projects_bp.put("/<slug>/files/<filename>")
@require_auth
def update_file(slug, filename):
    project = current_app.project_repository.get_by_slug(g.current_user.id, slug)
    body = request.get_json()
    new_sha = git_store.write_file(project.id, filename, body["content"])
    current_app.project_repository.touch(project.id, new_sha)
    return jsonify({"sha": new_sha})
```

### Migration — one-shot script

```python
# scripts/migrate_filesystem_to_git_db.py
"""For each /data/projects/<slug>/ on disk:
    1. Insert Project row (owner = configured admin).
    2. git_store.init_repo(project_id).
    3. Copy markdown files → working tree → commit "chore: import from filesystem".
    4. project_repository.touch(project_id, sha).
"""
```

Idempotent (skip-if-slug-exists). Run once, verify, switch `PROJECT_REPOSITORY=sql` in `.env`. Production refuses `PROJECT_REPOSITORY=fs`.

### Decision: per-project repo vs shared monorepo

- (a) **Per-project repo** at `/data/projects/<id>/.git/` (chosen) — clean isolation; trivial export-to-user-GitHub; easy garbage-collect on delete
- (b) Shared monorepo with `project/<id>` branch per project — fewer inodes; harder to export individually; one corrupt repo affects everyone

**(a) is right.** Storage is cheap; isolation matters more than dedup; the GitHub-mirror story is the killer-app argument.

### Explicitly out of scope

- Markdown content in DB — git owns it entirely.
- Multi-region replication / read replicas — single Postgres for v1.
- Per-project access sharing (collaborator model) — single owner; `ProjectShare` is a future feature.
- GitHub OAuth + push — separate Phase 4 feature; depends on this layer existing.

---

## Task 3 — Monetisation (Stripe billing + free-tier metering)

> **Priority**: P2 — required for paid public launch.
> **Effort**: ~2 days (Stripe billing + usage metering combined).
> **Blocks**: nothing — public launch gate.
> **Depends on**: persistence (Subscription + UsageCounter need user_id FKs), auth (decorator reads `g.current_user`).
> **Consolidates**: former `braindump-saas-stripe-billing.md` + `braindump-saas-usage-metering.md`.
> **Port from**: bubls `billing` + `usage` modules — near-verbatim, ~430 LOC combined.
> **Cross-reference**: GTM project (`specview-saas-gtm-1778233000`) has a fully specced epic + impl-guide for Stripe wiring. This task and the GTM Task 1 are the same work — execute from whichever spec is more current at implementation time.

Charge money + meter the free tier. Stripe Checkout handles cards (zero PCI scope). Stripe webhooks are the **sole writer** of subscription state. Free-tier users get N spec generations per day; (N+1)th request returns 429 → Angular routes to the upgrade page. Pro users uncapped. **`User.plan` is denormalised** from Subscription so every per-request gate is a single-field read, not a join.

The two halves ship together because they share the `User.plan` field and the upgrade flow: billing populates `plan='pro'`; metering reads `plan` to skip the cap check.

### Subscription entity + 5 webhook handlers

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

### Three billing routes

```python
@billing_bp.post("/create-checkout-session")
@require_auth
def create_checkout_session():
    customer_id = get_or_create_stripe_customer(g.current_user)
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

### UsageCounter entity + decorator

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

### Angular surface

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
```

All Angular pieces port near-verbatim from bubls.

### Pricing (single Price ID at launch)

One product, one price: `Pro Monthly` at $29/mo. No annual, no team plan, no usage-based pricing. Bubls launched with the same minimum.

| Tier | Price | Specs/day | Text ops/day | Models |
|------|-------|-----------|--------------|--------|
| Free | $0 | 3 | 20 | Haiku only |
| Pro | $29/mo | Uncapped | Uncapped | Opus + Sonnet + Haiku |

### .env additions

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
APP_URL=https://app.specview.io
```

### Explicitly out of scope

- Annual / team / lifetime plans — single Price ID for v1.
- Coupon / discount codes — Stripe supports them; UI defers.
- Per-token metering — counting AI calls is the v1 currency.
- Per-org usage pools — single user owns single counter.
- Refund automation — Stripe Dashboard manually for v1.
- PCI compliance — Stripe Checkout means cards never touch spec-doc; PCI scope is zero.

---

## Task 4 — Reliability (async lifecycle, streaming, retry, cancellation)

> **Priority**: P3 — quality + UX. Real users will hit every one of these.
> **Effort**: ~2 days (4 features sharing the polling/runtime substrate).
> **Blocks**: nothing — all additive over the existing WorkflowRuntime.
> **Depends on**: WorkflowRuntime + WorkflowExecution (already exist); Anthropic SDK provider for streaming.
> **Consolidates**: former `braindump-bootstrap-async.md` + `braindump-streaming-task-gen.md` + `braindump-retry-recovery.md` + `braindump-runtime-cancellation.md`.

Four operational capabilities for long-running AI generations, all sharing the same `WorkflowRuntime` + `WorkflowExecution` + polling substrate. Each is small individually; bundling them prevents inventing parallel state machines per feature.

1. **Async via WorkflowRuntime** — bootstrap migrates from inline 25-min HTTP call to 202 + polling, reusing the proven pattern.
2. **Streaming partial buffer** — runtime accumulates streamed chunks; polling endpoint surfaces them; user sees a live console instead of a spinner.
3. **Retry / regenerate** — failed or truncated tasks get a one-click rerun; bootstrap retries individual failed steps (~33% cost vs full chain).
4. **Cooperative cancellation** — `WorkflowExecution.request_cancel()` shipped but unread; this wires it into the runtime loop.

### Bootstrap async (kills the timeout class)

```python
# modules/ai/routes.py
_BOOTSTRAP_JOBS: dict[str, WorkflowExecution] = {}    # in-process; purge on first done-read

@ai_bp.post("/bootstrap-project")
@require_auth
@check_usage_limit("bootstrap")
def bootstrap_project():
    inputs = {**request.get_json(force=True), "builder": ...read_context...}
    workflow = current_app.workflow_repository.get("spec_gen/bootstrap-project")
    job_id = str(uuid.uuid4())
    execution = WorkflowExecution(workflow_ref="spec_gen/bootstrap-project", inputs=inputs)
    _BOOTSTRAP_JOBS[job_id] = execution
    threading.Thread(target=_run, args=(job_id, execution, workflow), daemon=True).start()
    return jsonify({"job_id": job_id}), 202

@ai_bp.get("/bootstrap-project/status/<job_id>")
def bootstrap_status(job_id):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if not execution: return jsonify({"error": "not found"}), 404
    response = {
        "running": execution.status == ExecutionStatus.IN_PROGRESS,
        "done":    execution.status in (ExecutionStatus.COMPLETED, ExecutionStatus.ERROR),
        "current_step": execution.current_step_name,
        "partial":      execution.outputs.get("_partials", {}).get(execution.current_step_name, ""),
        "warnings":     execution.warnings,
        "error":        execution.error,
    }
    if response["done"]:
        if execution.status == ExecutionStatus.COMPLETED:
            response["files"] = execution.outputs.get("files", [])
        _BOOTSTRAP_JOBS.pop(job_id, None)        # purge on first done-read
    return jsonify(response)
```

### Streaming partial buffer

```python
# modules/workflows/steps/ai_call.py — opt-in streaming flag
class AICall(AbstractStep):
    ...
    stream: bool = False

    def _invoke(self, context):
        merged = {**context.outputs, **context.inputs}
        prompt = self.prompt_template.format_map(merged)
        if not self.stream:
            return chain_adapter.generate(self.system, prompt, model=self.model, max_tokens=self.max_tokens)
        chunks = []
        for delta in chain_adapter.stream_generate(self.system, prompt, model=self.model, max_tokens=self.max_tokens):
            chunks.append(delta)
            if cb := context.inputs.get("_partial_callback"):
                cb(self.name, "".join(chunks)[-500:])    # rolling tail
        return ChainResult(text="".join(chunks), latency_ms=0)
```

Long-form steps (architecture, impl-guide) opt in via `AICall(..., stream=True)`. Rolling 500-char tail surfaced as `partial` in the polling response. Angular renders it in `<pre>`. **No SSE client needed** — the existing 3-second polling loop sees the live preview.

### Retry + recovery

Bootstrap retry uses **per-step sub-workflows** so the user pays for one call, not three, on architecture-only retries:

```python
@ai_bp.post("/bootstrap-project/<job_id>/retry")
@require_auth
@check_usage_limit("bootstrap")
def retry_bootstrap(job_id):
    step = request.get_json()["step"]                # "analysis" | "epic" | "architecture"
    prior = _BOOTSTRAP_JOBS.get(job_id)
    workflow = current_app.workflow_repository.get(f"spec_gen/bootstrap-{step}-only")
    new_inputs = {**prior.inputs,
                  "analysis": prior.outputs.get("analysis", ChainResult(text="")).text,
                  "epic":     prior.outputs.get("epic",     ChainResult(text="")).text}
    new_id = str(uuid.uuid4())
    new_exec = WorkflowExecution(workflow_ref=f"spec_gen/bootstrap-{step}-only", inputs=new_inputs)
    _BOOTSTRAP_JOBS[new_id] = new_exec
    threading.Thread(target=_run, args=(new_id, new_exec, workflow), daemon=True).start()
    return jsonify({"job_id": new_id}), 202
```

Angular surfaces a "Regenerate" button on any spec file with `size === 0`, `warnings.length > 0`, or `error != null`.

### Cooperative cancellation

```python
# modules/workflows/runtime.py
def run(self, execution, workflow):
    execution.start()
    context = StepContext(run_id=execution.execution_id, inputs={**execution.inputs, "_partial_callback": ...})
    try:
        for step in workflow.steps:
            if execution.status == ExecutionStatus.CANCELLING:
                execution.cancel()                   # CANCELLING → CANCELLED
                return
            yield from step.execute(context)
        execution.complete()
    except Exception as exc:
        execution.fail(str(exc))
        raise
```

One `if` per step. Cooperative (between-steps), not preemptive. Cancellation latency = at most one full step.

### Explicitly out of scope

- Persistent job storage (DB-backed executions) — in-process is sufficient for v1.
- Mid-step cancellation (interrupting in-flight `generate()`) — requires subprocess kill; race-y; defer.
- WebSocket transport — SSE is one-way push, sufficient.
- Auto-retry on transient failures — explicit user click only.

---

## Task 5 — Security Hardening

> **Priority**: P2 — launch gate.
> **Effort**: ~1 day.
> **Depends on**: auth (security headers apply to authed responses).

### CORS lockdown
- Replace `CORS_ORIGINS: "*"` with explicit origin list
- Production: `https://specview.app, https://www.specview.app`
- Local dev: `http://localhost:8095`

### Secrets management
- Remove hardcoded `DATABASE_URL` from `docker-compose.yml`
- Remove hardcoded `JWT_SECRET` from `docker-compose.yml`
- Use `.env` file (gitignored) or Coolify env vars
- Generate a proper random JWT_SECRET

### Input validation
- Validate project names (no path traversal in filesystem storage)
- Validate file content size limits
- Rate limit all API endpoints (not just AI ones)

### Security headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Content-Security-Policy for the SPA

---

## Task 6 — Operations & Infra (observability + CI)

> **Priority**: mixed — observability is P3 (ship around Phase 1 so everything else is debuggable);
>                       Angular CI is P4.
> **Effort**: ~1.5 days observability; ~1 day Angular CI.
> **Blocks**: nothing structurally; observability **enables** debugging every other task.
> **Consolidates**: former `braindump-saas-observability.md` + `braindump-frontend-backend-cicd.md` + `braindump-monorepo-refactor.md`.
> **Port from**: bubls (Sentry + structlog + health checks — all near-verbatim).

### Observability — `modules/observability/`

Four small things that share a debug-context model:

```
modules/observability/
├── sentry.py        # init_sentry(app) — Flask integration, per-user scoping after auth
├── logging.py       # init_logging() — structlog with JSON output + request_id propagation
├── health.py        # health_bp blueprint — /api/health/{anthropic,neon,stripe}
└── errors.py        # register_error_handlers(app) — JSON responses for every exception
```

```python
# modules/observability/sentry.py
def init_sentry(app):
    if dsn := os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=dsn, integrations=[FlaskIntegration()],
                        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                        environment=os.environ.get("APP_ENV", "production"),
                        release=os.environ.get("APP_RELEASE", "dev"))
```

```python
# modules/observability/logging.py
def init_logging():
    structlog.configure(processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level, structlog.stdlib.add_logger_name,
        _add_request_context,                    # injects request_id, user_id
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ], wrapper_class=structlog.stdlib.BoundLogger, cache_logger_on_first_use=True)
```

```python
# modules/observability/errors.py
def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def _http(exc): return jsonify({"error": exc.description, "code": exc.code}), exc.code

    @app.errorhandler(ValidationError)
    def _validation(exc): return jsonify({"error": "validation_failed", "details": exc.errors()}), 422

    @app.errorhandler(Exception)
    def _unexpected(exc):
        logger.exception("unhandled_exception", path=request.path)
        return jsonify({"error": "internal_server_error", "code": 500}), 500
```

All four wired in `create_app()` in order: structlog → sentry → error handlers → health blueprint. **Order matters** (structlog first so subsequent inits log structured).

### Angular CI

Current CI: backend only. Bad `ng build` ships silently. Fix: add frontend build job.

```yaml
# .github/workflows/deploy.yml
jobs:
  test-backend:    # existing — pytest
  build-frontend:  # NEW — ng build, upload dist as artifact
  docker-build:    # NEW — multi-stage Dockerfile; smoke test /api + /
  deploy:          # existing Coolify webhook — main branch only
```

### .env additions

```
SENTRY_DSN=https://...@sentry.io/...
APP_ENV=production
LOG_LEVEL=INFO
```

### Decisions

1. **Where do JSON logs go in production?** Coolify captures stdout (proposed; zero infra). Upgrade to BetterStack/Logtail when volume justifies.
2. **Sentry traces sample rate** — 0.1 (10%) proposed; matches bubls launch.

### Explicitly out of scope

- APM (Datadog, New Relic) — Sentry covers errors + basic perf.
- OpenTelemetry tracing — overkill for single-service backend.
- Frontend session replay (Sentry Replay) — enable when first hard-to-repro user bug appears.
- Per-PR preview deploys — not needed at current team size.

---

## Task 7 — Anthropic SDK Provider as Production Default

> **Priority**: P0 for SaaS (deferred from current P0 auth project due to cost constraint).
> **Effort**: ~1 day (SDK provider + cost accumulator + `/api/stats` + startup gate).
> **Blocks**: any cloud-deploy AI call under API key billing; SaaS launch in general.
> **Depends on**: nothing (independent of the auth/persistence track).
> **Port from**: humanize-me + bubls SDK shape.

**Context from P0 decision:** The P0 auth reliability project chose Option B (container login + persistent volume with Claude Max flat-rate) over Option A (API key) because per-token billing is not affordable pre-revenue. This task is the migration to API key billing that happens at SaaS launch when per-user cost tracking justifies per-token pricing.

Make the Anthropic SDK provider the default for any deployment that isn't a developer's laptop. The CLI provider is the dev-only legacy path.

### SDK provider — `api/modules/chain/providers/anthropic_sdk.py`

```python
"""Anthropic SDK provider — production default.

The CLI provider is dev-only. Production must use this provider because
CLI OAuth tokens require manual refresh and per-token cost tracking is impossible.
"""
import os
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from ..errors import ProviderError
from ..types import ChainResult


def create_message(
    system: str,
    prompt: str,
    *,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 4096,
) -> ChainResult:
    """One-shot Anthropic SDK call. Returns ChainResult with text + token usage."""
    client = Anthropic(timeout=900.0, max_retries=2)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except RateLimitError:
        raise ProviderError("AI provider rate-limited. Try again in a moment.", 429)
    except APIConnectionError:
        raise ProviderError("Cannot reach AI provider. Try again.", 502)
    except APIError as exc:
        raise ProviderError(f"AI provider error: {exc.message}", 502)

    return ChainResult(
        text=msg.content[0].text,
        latency_ms=0,
        tokens_in=msg.usage.input_tokens,
        tokens_out=msg.usage.output_tokens,
    )
```

### Adapter — flip the default

Auto-detect: if `ANTHROPIC_API_KEY` is set, use SDK. Otherwise CLI. Production deployments set the key; dev machines may set neither (then they get CLI with their Claude Max subscription). `CHAIN_PROVIDER=mock` for tests. **Backward-compatible**: every existing dev environment without `ANTHROPIC_API_KEY` keeps using CLI.

### Per-step model routing

```python
.step(AICall(name="analysis",     model="claude-haiku-4-5",   max_tokens=4096))   # cheap
.step(AICall(name="architecture", model="claude-opus-4-7",    max_tokens=16384))  # quality matters
```

Saves ~3x on cost for analysis step (Haiku is ~5x cheaper than Sonnet for input tokens).

### Cost accounting

Module-level usage accumulator + `/api/stats` endpoint. Per-user cost attribution joins on top via the usage metering task.

### Deployment gate

```python
# create_app.py
if os.environ.get("APP_ENV") == "production" and not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError("Production mode requires ANTHROPIC_API_KEY.")
```

Hard fail loud. Better to crash on startup than discover at first AI call.

### Explicitly out of scope

- OpenAI / Gemini providers — out of scope until pricing pressure justifies.
- Per-user / per-tenant API keys — single org-wide key for v1.
- Replacing the CLI provider — kept indefinitely as dev convenience.

---

## Task 8 — Onboarding Flow

> **Priority**: P3 — last; needs everything working.
> **Effort**: ~1 day.
> **Depends on**: auth + billing + landing page.

### Landing → App connection
- Landing page "Get Started" CTA → `/signup` route (Supabase magic-link)
- After magic-link click → redirect to app with first-run experience
- Free tier starts immediately (no credit card required)

### First-run experience
- Create a sample project automatically ("My First Spec")
- Show tooltip/walkthrough: paste braindump → click generate → see specs

### Email infrastructure
- Supabase handles transactional email for magic-link and verification
- Additional templates (usage warning, welcome) via Resend or Postmark if needed

---

## Launch Checklist

- [ ] Persistence: Project + User tables, git-backed markdown, migration script
- [ ] Auth: Supabase magic-link, `@require_auth` on all routes, dev bypass
- [ ] Billing: Stripe Checkout, webhook handlers, `@check_usage_limit` gating
- [ ] Usage: Daily free-tier caps, 429 → upgrade flow
- [ ] Security: CORS locked, secrets out of compose, security headers
- [ ] Observability: Sentry, structlog, JSON error handler, health checks
- [ ] CI: Angular build in pipeline, smoke test
- [ ] Reliability: Async bootstrap, streaming partials, retry, cancel
- [ ] SDK provider: `ANTHROPIC_API_KEY` as production default, per-step model routing
- [ ] Onboarding: Landing CTA → magic-link → first-run experience
- [ ] Auth reliability: P0 project complete (credential persistence)
- [ ] Frontend tests: P2 project complete (basic test coverage)
- [ ] Load test with 10 concurrent users
- [ ] Terms of service + privacy policy pages
- [ ] Custom domain + SSL verified
