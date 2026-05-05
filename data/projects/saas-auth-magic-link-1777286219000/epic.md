# 🎯 Epic: SaaS Auth — Magic Link

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Auth is the gate for everything else SaaS. Without verified JWTs and a `g.current_user` injection point, billing webhooks have nothing to attach a Stripe customer to, the usage-metering decorator silently no-ops, and the per-tenant `auth_user_id` foreign keys in `User`, `Project`, and `UsageCounter` from saas-persistence are dangling. Magic-link via Neon Auth is the cheapest path: zero password storage, zero OAuth client registration, Neon Auth free tier covers everything for the early SaaS phase, the Angular SDK is two imports.

The capability is also a wiring task more than a build task. Neon Auth issues the JWT; spec-doc validates it via standard `PyJWKClient` (RS256, JWKS endpoint, claim `sub`). The `User` table, the `auth_user_id` column, and the repository methods that scope queries by `user_id` already exist. Once `@require_auth` lands and every existing AI/projects/context route gains the decorator, the multi-tenant promise of saas-persistence is finally enforced. Billing and usage-metering capabilities that were waiting for `g.current_user` can land immediately after.

The dependency chain is **persistence → auth → billing → metering**. This epic delivers the second link. It blocks two siblings, it consumes one, and it has zero new external services to integrate beyond Neon Auth — which is already the database tenancy provider for spec-doc, so the integration is one additional dashboard configuration, not a new vendor.

**Value Proposition**: Activate per-tenant scoping by validating Neon Auth JWTs at every existing route and exposing `g.current_user` to the decorators that billing and usage metering depend on.

---

## Scope

### What This Epic Covers

- **Backend `modules/auth/service.py`** — `verify_jwt(token)` returns claims; `get_or_create_user_from_claims(claims)` upserts a `User` row keyed by `auth_user_id`; `send_magic_link(email)` and `verify_magic_link(token)` proxy to Neon Auth's REST API
- **Backend `modules/auth/decorators.py`** — `@require_auth` reads `Authorization: Bearer`, calls `verify_jwt`, hydrates `g.current_user` via the user repository; returns 401 on missing/invalid token
- **Backend `modules/auth/routes.py`** — `auth_bp` with `POST /api/auth/login` (request magic link), `POST /api/auth/verify` (exchange one-time token for JWT + create `User` row), `POST /api/auth/logout` (client-side discard, 204), `GET /api/auth/me` (returns `g.current_user` as JSON)
- **Existing route protection** — every route in `modules/ai/`, `modules/data/projects/`, `modules/data/context/`, `modules/data/templates/` gains `@require_auth`; per-tenant queries replace global ones (`list_for_user(g.current_user.id)`)
- **Frontend `web/src/app/services/auth.service.ts`** — `requestMagicLink(email)`, `verifyToken(token)`, `signOut()`, `currentUser` signal; persists JWT to `localStorage` keyed by `spec_doc_jwt`
- **Frontend `web/src/app/interceptors/auth.interceptor.ts`** — adds `Authorization: Bearer` header to every `/api/*` request; on HTTP 401 clears stored JWT and redirects to `/login`
- **Frontend login flow** — `LoginComponent` (email input + request-link button), `AuthCallbackComponent` (extracts token from URL, calls `verifyToken`, redirects to `/projects`), router guards on every protected route

### What This Epic Does NOT Cover

- ❌ **OAuth providers (Google, Apple, GitHub)** — magic link is the only login surface for v1; native auth waits for an iOS app or paying customer SSO request
- ❌ **Two-factor / TOTP** — per-user setting added when first user requests it; not in default flow
- ❌ **Custom branded email templates** — Neon Auth defaults; brand when marketing-page capability lands
- ❌ **Multi-user workspaces / team primitives** — single user owns single set of projects; multi-tenant teams wait for a paying team customer
- ❌ **DEV_BYPASS_AUTH env flag** — production refuses to start without real Neon Auth env vars; dev uses real Neon Auth project; the bypass is one less code path to test
- ❌ **Server-side session table / refresh-token store** — Neon Auth owns session lifecycle; spec-doc holds no session state
- ❌ **Account-deletion / GDPR-erase flows** — re-scope when first user requests it; database has cascade-on-delete from saas-persistence

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Auth service + JWT verifier** | None | — | 0.5 days | High |
| 2 | **`@require_auth` decorator + `auth_bp` routes** | 1 | 3 | 0.5 days | High |
| 3 | **Protect existing routes with `@require_auth`** | 2 | — | 0.5 days | High |
| 4 | **Angular auth service + interceptor + login flow** | 2 | 3 | 0.5 days | High |

### Task 1: Auth service + JWT verifier

Build `modules/auth/service.py` with three pure functions: `verify_jwt(token)` (PyJWKClient + RS256 decode against `NEON_AUTH_JWKS_URL`), `get_or_create_user_from_claims(claims, repo)` (idempotent upsert keyed by `auth_user_id`), and `send_magic_link(email)` / `verify_magic_link(token)` (HTTP calls to Neon Auth REST API). Service is pure Python — no Flask imports, no `g` access. Blueprint and decorator that consume it land in Task 2.

**Port budget**: ~80 lines across one file + 8 unit tests; PyJWKClient is stdlib-grade once `pyjwt[crypto]` is in `requirements.txt`; HTTP calls use `requests` already pinned for the chain adapter.

### Task 2: `@require_auth` decorator + `auth_bp` routes

Build `modules/auth/decorators.py` with `@require_auth` (reads `Authorization` header, calls `verify_jwt`, sets `g.current_user`, returns 401 on failure) and `modules/auth/routes.py` with `auth_bp` exposing `POST /api/auth/login`, `POST /api/auth/verify`, `POST /api/auth/logout`, `GET /api/auth/me`. Register `auth_bp` in `create_app.py` `ENABLED_MODULES`. Add OpenAPI schema entries for the four routes; regenerate DTOs.

**Port budget**: ~120 lines across two files + 4 route handlers + DTO regen; openapi.yaml gets four new path entries; structural test `everyOpenapiPath_hasRouteHandler` must pass.

### Task 3: Protect existing routes with `@require_auth`

Add `@require_auth` to every route in `modules/ai/routes/`, `modules/data/projects/routes.py`, `modules/data/context/routes.py`, `modules/data/templates/routes.py`. Replace any global `list_projects()` / repository call with the user-scoped equivalent (`list_for_user(g.current_user.id)`). `/health` and `/api/auth/*` stay public. Update integration tests to pass a valid JWT fixture; tests for the `mock` provider mint a synthetic token with the test JWKS.

**Port budget**: ~30 lines of decorator additions + ~20 lines of repository call rewrites + 1 pytest fixture (`auth_headers`) consumed by every existing integration test.

### Task 4: Angular auth service + interceptor + login flow

Build `web/src/app/services/auth.service.ts` (signals + `localStorage`), `web/src/app/interceptors/auth.interceptor.ts` (Bearer injection + 401 redirect), `web/src/app/components/login/login.component.ts` (email + request button), `web/src/app/components/auth-callback/auth-callback.component.ts` (token exchange + redirect), and a `canActivate` guard on every protected route. Wire the interceptor in `app.config.ts`. Update `web/src/environments/environment.ts` with `neonAuthProjectId` and `neonAuthAppOrigin`.

**Port budget**: ~250 lines of TypeScript across 5 files + router updates + 12 component/service unit tests.

---

## Success Criteria

- ✅ `POST /api/auth/login` with valid email returns 202 and Neon Auth dispatches an email containing a one-time link
- ✅ `POST /api/auth/verify` with the link's token returns 200 with `{ jwt, user: { id, email, auth_user_id } }` and the `User` row exists in the SQL store
- ✅ Every existing protected route returns 401 without `Authorization: Bearer` and the documented success envelope with a valid JWT
- ✅ `g.current_user` is a hydrated `User` SQLModel instance inside every protected route handler (asserted via integration test)
- ✅ Angular interceptor adds `Authorization: Bearer <jwt>` to every `/api/*` request when a session exists; HTTP 401 clears the session and routes to `/login`
- ✅ Test count grows by at least 30 (8 service unit tests + 4 decorator tests + 6 route tests + 12 Angular tests)
- ✅ Structural test `everyOpenapiPath_hasRouteHandler` passes after auth routes are added

---

## Non-Goals

- ❌ **OAuth / SSO providers** — single magic-link surface ships v1
- ❌ **TOTP / 2FA** — opt-in feature added on first user request
- ❌ **Server-side session store** — Neon Auth owns session lifecycle
- ❌ **DEV_BYPASS_AUTH back-door** — single auth path, fewer test branches
- ❌ **Per-tenant data migration tooling** — single existing user; data ownership backfilled by the persistence migration's seed user

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
