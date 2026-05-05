# 🏗️ Solution Architecture: SaaS Auth — Magic Link

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The auth capability sits between Neon Auth (the identity provider that issues JWTs) and the existing SQL user table from saas-persistence. Spec-doc never stores passwords, never issues tokens, never holds session state — it validates, hydrates, and scopes. Every existing route gains one decorator; every existing repository method gains a `user_id` filter that was already supported but never enforced.

The mental model: Neon Auth is the bouncer at the door, `@require_auth` is the wristband check at every room, `g.current_user` is the wristband. Two siblings (billing webhook handler, usage-metering decorator) are downstream consumers of the same wristband and become functional the moment this capability ships. The whole flow is a copy of the bubls auth shape — the JWKS validation pattern is generic, the `User` row already exists, the only spec-doc-specific bit is which routes get the decorator.

The Angular side is symmetric: the auth interceptor attaches the wristband to every outgoing request, the auth service holds it in `localStorage`, and a 401 response signals the wristband is invalid and triggers a redirect to the magic-link request page.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Adapter Boundary (ELA #1) | All Neon Auth HTTP calls live in `service.py`. Routes never call Neon Auth directly. |
| Blueprint Module Structure (ELA #2) | `modules/auth/` owns `service.py` (pure logic), `decorators.py` (Flask glue), `routes.py` (HTTP only), `models.py` (existing). |
| OpenAPI-First (ELA #3) | The four `/api/auth/*` routes ship with openapi.yaml entries; DTOs regenerated; structural test enforces. |
| Not-Yet-Built (ELA #5) | Single auth flow ships. No OAuth, no 2FA, no team primitives. Each is reopened only when a named consumer asks. |
| Pure functions where possible | `verify_jwt`, `get_or_create_user_from_claims` take inputs and return outputs; no `g`, no global state. The decorator is the only Flask-aware seam. |

---

## System Boundaries

### What This System Includes

- `modules/auth/service.py` — JWT verification (RS256 + JWKS), Neon Auth REST proxies (`send_magic_link`, `verify_magic_link`), user-row upsert helper. Consumed by `decorators.py` and `routes.py`.
- `modules/auth/decorators.py` — `@require_auth` Flask decorator. Consumed by every protected route in `modules/ai/`, `modules/data/projects/`, `modules/data/context/`, `modules/data/templates/`, plus by the future Mon-T2/T3 usage decorator and the billing webhook handler.
- `modules/auth/routes.py` — `auth_bp` blueprint with `POST /api/auth/login`, `POST /api/auth/verify`, `POST /api/auth/logout`, `GET /api/auth/me`. Consumed by the Angular auth service.
- `modules/auth/models.py` — already exists from saas-persistence. `User` SQLModel with `auth_user_id`, `email`, `id`. Consumed by the user repository and by every route reading `g.current_user`.
- `web/src/app/services/auth.service.ts` — magic-link request, token exchange, sign-out, `currentUser` signal. Consumed by `LoginComponent`, `AuthCallbackComponent`, and any component reading the current user.
- `web/src/app/interceptors/auth.interceptor.ts` — Bearer header injection + 401 redirect. Consumed implicitly by every Angular HTTP call to `/api/*`.
- `web/src/app/components/login/`, `web/src/app/components/auth-callback/` — the two new pages on the protected route.
- `auth_headers` pytest fixture — mints a synthetic test JWT signed with a test JWKS. Consumed by every integration test that hits a protected route.

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| OAuth / SSO providers | Single magic-link surface ships v1; native auth waits for an iOS app or paying-customer SSO request. |
| TOTP / 2FA | Per-user setting added on first user request; not in default flow. |
| Server-side session store | Neon Auth owns session lifecycle; spec-doc holds no session state. |
| DEV_BYPASS_AUTH env-flag | Production refuses to start without real Neon Auth env vars; dev uses real Neon Auth project. One less code path to test. |
| Custom branded email templates | Neon Auth defaults; brand when marketing-page capability lands. |
| Account deletion / GDPR-erase flows | Re-scope when first user requests it; cascade-delete already configured by saas-persistence migration. |
| Multi-user workspaces / team primitives | Single user owns single set of projects; teams wait for a paying team customer. |

---

## Component Design

### `modules/auth/service.py`

**Purpose**: Pure-Python core. Verifies Neon Auth JWTs, talks to Neon Auth's REST API for magic-link send/verify, and exposes an idempotent user-row upsert.

**Key Parts**:
- `verify_jwt(token)` — uses `PyJWKClient(NEON_AUTH_JWKS_URL).get_signing_key_from_jwt(token).key` and `jwt.decode(token, key, algorithms=["RS256"], audience=NEON_AUTH_AUDIENCE)`. Returns the claims dict. Consumed by the `@require_auth` decorator.
- `send_magic_link(email)` — POSTs to Neon Auth's email-OTP endpoint with the project ID and the redirect URL `/auth/callback`. Returns `{ "request_id": ... }`. Consumed by the `/api/auth/login` route.
- `verify_magic_link(token)` — POSTs to Neon Auth's verify endpoint, returns the issued JWT and the claims. Consumed by the `/api/auth/verify` route.
- `get_or_create_user_from_claims(claims, user_repo)` — idempotent upsert keyed by `claims["sub"]` → `User.auth_user_id`. Sets `email` from `claims["email"]`. Consumed by the decorator and the verify route.

**Patterns**: Adapter Boundary — Neon Auth HTTP is concentrated in this file, not scattered across routes.

### `modules/auth/decorators.py`

**Purpose**: The single Flask-aware seam in the auth module. Every protected route mounts this decorator; the rest of `modules/auth/` is pure Python.

**Key Parts**:
- `@require_auth` — reads `Authorization` header, returns 401 if missing or non-`Bearer`, calls `service.verify_jwt`, returns 401 with structured error body on `jwt.PyJWTError` subclasses, otherwise calls `get_or_create_user_from_claims`, sets `g.current_user`, and dispatches to the wrapped handler.

**Patterns**: Decorator pattern. Single point of `g.current_user` injection so downstream code (Mon-T2/T3 usage decorator, billing webhook handler) has a stable contract.

### `modules/auth/routes.py`

**Purpose**: Four HTTP endpoints that bridge the Angular auth service to Neon Auth. Routes are thin: parse, call service, serialize.

**Key Parts**:
- `POST /api/auth/login` — body `{ email }`; calls `service.send_magic_link`; returns 202 with `{ request_id }`.
- `POST /api/auth/verify` — body `{ token }`; calls `service.verify_magic_link`, then `get_or_create_user_from_claims`; returns 200 with `{ jwt, user: { id, email, auth_user_id } }`.
- `POST /api/auth/logout` — returns 204; client-side `localStorage` discard. Server-side no-op because Neon Auth owns session lifecycle.
- `GET /api/auth/me` — `@require_auth`; returns the `g.current_user` row as JSON.

**Patterns**: OpenAPI-First. All four routes are declared in `openapi.yaml` before the handlers exist; DTOs regenerate; structural test enforces the contract.

### Existing Route Protection

**Purpose**: Make the per-tenant promise of saas-persistence enforceable. Without this, any unauthenticated client can read every project. With this, every existing protected handler gains one decorator and one repository-call rewrite.

**Key Parts**:
- Decorator placement on every route in `modules/ai/routes/*.py`, `modules/data/projects/routes.py`, `modules/data/context/routes.py`, `modules/data/templates/routes.py`. The `/health` route and `/api/auth/*` routes stay public.
- Repository call rewrites: `ProjectRepository.list()` → `ProjectRepository.list_for_user(g.current_user.id)`. The user-scoped variants already exist from saas-persistence; they were never wired.
- `auth_headers` pytest fixture (mints a test JWT signed with a test JWKS keypair owned by the test fixture) consumed by every integration test that hits a protected route.

**Patterns**: Cross-cutting concern via decorator. Every route's behaviour change is one line; tests change once via the fixture.

### `web/src/app/services/auth.service.ts`

**Purpose**: Single source of truth for the current user on the Angular side. Holds the JWT, exposes a `currentUser` signal, and handles login/verify/logout.

**Key Parts**:
- `currentUser: WritableSignal<User | null>` — reactive surface for components.
- `requestMagicLink(email)` — POST `/api/auth/login`.
- `verifyToken(token)` — POST `/api/auth/verify`, persists JWT to `localStorage` keyed by `spec_doc_jwt`, populates `currentUser`.
- `signOut()` — clears `localStorage`, clears `currentUser`, navigates to `/login`.
- `getStoredJwt()` — read-only accessor consumed by the interceptor.

### `web/src/app/interceptors/auth.interceptor.ts`

**Purpose**: Single point of header injection. Every `/api/*` request gets `Authorization: Bearer <jwt>` if a session exists. Every 401 from a protected route triggers a forced sign-out and redirect to `/login`.

**Key Parts**:
- `intercept(req, next)` — clones the request with the `Authorization` header when `auth.getStoredJwt()` is non-null.
- 401 handler — `catchError` branch that calls `auth.signOut()` and redirects.

**Patterns**: HTTP interceptor (Angular built-in). Removes per-component header logic.

### Login + Auth-Callback Components

**Purpose**: Two pages: `LoginComponent` accepts an email and triggers `requestMagicLink`; `AuthCallbackComponent` extracts the one-time token from the URL fragment, calls `verifyToken`, and redirects to `/projects` on success.

**Key Parts**:
- `LoginComponent` (`/login`) — email input, request button, success and error states.
- `AuthCallbackComponent` (`/auth/callback`) — runs `verifyToken` on `ngOnInit`, shows loading and error states.
- `canActivate` guard on every protected route — checks `auth.currentUser()` is non-null; redirects to `/login` otherwise.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Identity provider | Neon Auth | Database tenancy is already on Neon; one less vendor; magic-link flow available; no PCI/SOC2 burden. |
| JWT format | RS256 + JWKS | Standard; PyJWKClient handles cache + refresh; `sub` claim → `User.auth_user_id`. |
| Backend | Flask blueprint | Matches every other module in `api/`. |
| Backend deps | `pyjwt[crypto]`, `requests` | `requests` already pinned for the chain adapter; pyjwt[crypto] adds RS256 support. |
| Frontend | Angular standalone + signals | Matches existing app shape. |
| Frontend deps | None new | Hosted Neon Auth pages do the heavy lifting; spec-doc only POSTs to its own backend. |
| Session storage | `localStorage` (`spec_doc_jwt`) | Matches Neon Auth SDK convention; interceptor stateless; survives reloads. |
| Test JWT | Local RSA keypair fixture | `tests/conftest.py` mints a keypair, signs synthetic tokens, monkeypatches `NEON_AUTH_JWKS_URL` to a fake JWKS endpoint. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Neon Auth, not Supabase | Database is already on Neon; one vendor instead of two; identity + tenancy in one console. | Requires the Neon Auth feature flag to be on the project; Supabase Auth has more public docs for magic-link UX. |
| `@require_auth` sets `g.current_user` (not `g.user_id`) | Downstream consumers (Mon-T2/T3, billing) need `email` and `plan` fields; passing the row avoids re-fetching. | Slightly heavier per-request object; one extra DB query on first verify per user; offset by repository-level cache later if needed. |
| Eager `User` row creation in `/api/auth/verify` | `g.current_user` is always hydrated downstream; no fallback path needed. | Verify endpoint does a write; acceptable because the call is idempotent and infrequent. |
| `localStorage` for JWT, not HTTP-only cookie | Matches Neon Auth SDK convention; interceptor stateless; survives reloads; works across `:3101` API and `:4201` SPA in dev without cookie-domain headaches. | Vulnerable to XSS if the SPA ever loads untrusted content; mitigated by Angular's strict template binding. Re-decision when CSP is hardened. |
| No DEV_BYPASS_AUTH env flag | Single auth path, fewer test branches; production refuses to start without real env vars. | Dev requires a real Neon Auth project; offset by the project being free. |
| RS256 + JWKS, not HS256 + shared secret | Neon Auth issues; spec-doc validates with public keys; no shared secret to leak; key rotation is automatic via JWKS cache. | One extra dependency (`pyjwt[crypto]`); negligible. |
| Decorator on every existing route, not before-request hook | Per-route opt-in is explicit; `/health` and `/api/auth/*` stay public without conditionals. | More decorators in the source; offset by clarity — every protected route shows its protection in its signature. |

---

## Execution Flow

```
Phase 1: Backend foundation
  Task 1 (auth service + JWT verifier)
         │
         ▼
  Task 2 (@require_auth + auth_bp routes + openapi)
         │
         ├──────────────────────────────┐
         ▼                              ▼
Phase 2: Backend wiring + frontend (parallel)
  Task 3 (protect existing routes)   Task 4 (Angular auth + login)
```

Task 1 has no dependencies. Task 2 depends on Task 1's `verify_jwt` and `get_or_create_user_from_claims`. Tasks 3 and 4 are fully parallel once Task 2 is done — Task 3 is server-only decorator additions; Task 4 is client-only Angular work that only needs the route contracts that Task 2 published in `openapi.yaml`.

---

## Open Questions

- **JWT storage on the Angular side** — `localStorage` (default), HTTP-only cookie, in-memory signal. Default to `localStorage`; re-decide when CSP is hardened or an XSS audit flags it.
- **Magic-link redirect target** — `/projects` index (default) vs deep-link to last opened project (UX polish). Default to `/projects`; re-decide when first paying user asks.
- **First-login row creation timing** — eager (in `/api/auth/verify`, default) vs lazy (in the decorator on first authenticated request). Default eager; re-decide if verify-time write latency becomes user-visible.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview

---

**Length budget**: target ≤ 250 lines including all tables. If you need more, the
architecture is doing too much — split into a follow-on capability.
