# spec-doc — SaaS Auth via Supabase Magic Link

> **Priority**: P1 — gates every authenticated route.
> **Effort**: ~1 day (User entity + JWKS validation + `@require_auth` + Angular interceptor).
> **Blocks**: billing (Stripe customer needs `User.id`), metering (UsageCounter needs `user_id`),
>             every per-tenant query in projects/, task_gen/, spec_gen/, ai/ routes.
> **Depends on**: data-layer (User entity sits in the SQL store).
> **Siblings**: `braindump-saas-data-layer.md` (User entity defined together),
>               `braindump-saas-stripe-billing.md` (denormalises to `User.plan`),
>               `braindump-saas-usage-metering.md` (reads `User.plan` for free/pro dispatch).
> **Port from**: bubls `auth` module. Near-verbatim — JWKS + JWT decode pattern is generic.

## What

Add user auth using Supabase's magic-link flow — same shape bubls ships in production. No passwords, no OAuth complexity, no PCI/SOC2 burden. The Angular client requests a magic link by email; Supabase emails the user; the user clicks; the SPA receives a JWT; every API request carries it as `Authorization: Bearer <token>`. Flask validates the JWT, extracts the Supabase user id, looks up (or creates) the matching `User` row, and injects it into the request context.

Spec-doc is currently a single-user dev tool. Auth is the gate for everything else SaaS — billing rows need a user_id, usage rows need a user_id, projects need an owner. **Without auth, the data-layer brain dump's `user_id` foreign keys are dangling.**

Port the shape verbatim from bubls's `auth` module. The Supabase JWKS validation pattern is copy-paste from `kw-auth`'s `BearerTokenAuthenticationFilter` (Spring Security analogue). The only spec-doc-specific bit is the `User` table.

### 1. New module — `api/modules/auth/`

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

### 2. User entity — `modules/auth/models.py`

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

`plan` is denormalised here so the auth layer can answer "is this user pro?" without joining `Subscription`. The Stripe brain dump syncs the field on webhook.

### 3. JWT validation — `modules/auth/service.py`

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

JWKS is fetched lazily and cached. Supabase rotates keys infrequently; the cache TTL is fine at default.

### 4. Per-request user injection — `modules/auth/middleware.py`

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

The decorator goes on every route in `projects/`, `task_gen/`, `spec_gen/`, `ai/`. The `/health` and `/api/auth/*` routes stay public.

`g.current_user` is the Flask-context analogue of bubls's Spring Security `Principal.user`. Routes read `g.current_user.id` to scope queries.

### 5. Routes that scope to user

```python
# modules/projects/routes.py
@projects_bp.get("/")
@require_auth
def list_projects():
    user_id = g.current_user.id
    return jsonify(current_app.project_repository.list_for_user(user_id))


@projects_bp.post("/")
@require_auth
def create_project():
    user_id = g.current_user.id
    req = CreateProjectRequest.model_validate(request.get_json())
    project = current_app.project_repository.create(user_id=user_id, name=req.name, files=req.files)
    return jsonify(project)
```

Every existing route gains `@require_auth` and replaces its global project lookup with a user-scoped one. The repository pattern from the data-layer brain dump means this is a one-line change per route.

### 6. Angular — Supabase JS client

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

  // HttpInterceptor pulls token from supabase.auth.getSession()
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

Magic-link click lands on `/auth/callback`; Supabase JS picks up the token from the URL fragment and stores the session in localStorage. Subsequent API calls inherit it via the interceptor.

### 7. New routes — `modules/auth/routes.py`

```python
@auth_bp.get("/me")
@require_auth
def me():
    return jsonify({
        "id": g.current_user.id,
        "email": g.current_user.email,
        "plan": g.current_user.plan,
    })
```

That's the only new server-side endpoint. Sign-in itself is client-side via Supabase JS.

### 8. .env additions

```
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_ANON_KEY=...                  # Angular env, not server
SUPABASE_SERVICE_ROLE_KEY=...          # server-only, used by webhooks (billing brain dump)
```

JWKS is public; no server-side key needed for JWT validation. The service role key is for the Stripe webhook brain dump's user-lookup-by-email flow.

## Why now

The data-layer brain dump's `user_id` foreign keys are useless without a user table. The user table is useless without a way to populate it. Magic-link auth is the cheapest path: zero password storage, zero OAuth client registration, Supabase free tier covers everything for the early SaaS phase, the Angular library is two imports.

The bubls codebase is the canonical port source — Supabase magic link is what they ship for the same single-developer-team-ships-SaaS shape. Trendfy added Apple Sign-In on top later for the iOS app store requirement; spec-doc is a web app and doesn't need that.

Auth must land before billing (Stripe customer needs a user row) and before metering (UsageCounter needs a user_id). The dependency chain is **data-layer → auth → billing → metering**.

## What's missing

One decision: **what happens to the existing single-user filesystem dev workflow?** Options:
- (a) Auth required everywhere; dev mode pre-seeds a single user (proposed) — `DEV_BYPASS_AUTH=true` env injects `g.current_user` as a fixed local user, no Supabase call. Production refuses to start with that flag set.
- (b) Routes split into authed (`/api/v2/*`) and unauthed (`/api/*`) — keeps the dev tool working alongside the SaaS surface. Doubles the maintenance.
- (c) Auth required everywhere from day one — clean break, but blocks dev iteration until Supabase is provisioned locally.

(a) is right. Dev iteration speed matters; the bypass is one env-flag check; production-mode refuses to honour it.

## Explicitly out of scope

- **Apple Sign-In, Google OAuth** — magic link covers the web SaaS use case; native auth providers land if/when an iOS app is built.
- **Two-factor / TOTP** — Supabase supports it; spec-doc enables it as a per-user setting only when a user requests it.
- **Custom email templates** — Supabase's default templates are fine for the early phase; brand them when the landing page brain dump lands.
- **Self-hosted Postgres for auth** — Supabase auth runs on Supabase's Postgres; spec-doc's app data runs on Neon (per the data-layer brain dump). Two databases, one for auth state, one for app state. Standard bubls split.
- **Replacing the dev `SPEC_DOC_DIR` flow** — kept until everyone on the team is comfortable with the SQL repository; flagged behind `PROJECT_REPOSITORY=fs|sql` per the data-layer brain dump.
- **Workspace / team / org primitives** — single user owns single set of projects. Multi-user workspaces wait for a paying team customer to ask.
