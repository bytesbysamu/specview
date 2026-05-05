# 🔍 SaaS Auth — Magic Link — Analysis

## The Problem

Spec-doc has a `User` row in the SQL store from saas-persistence with an `auth_user_id` JWT-subject column, but no code path populates it. Every route handler in `modules/ai/`, `modules/data/projects/`, `modules/data/context/`, and `modules/data/templates/` operates as if the tool is single-tenant. Without a verified JWT and a `g.current_user` injection point, billing webhooks (Mon-T2/T3) and usage metering decorators have nothing to scope to and silently no-op, and the per-tenant queries the persistence migration set up are unenforced.

## Hard Constraints

Decisions already made. Deadlines. Budget limits. Tech that MUST be used or avoided. Cross-check against the builder context — if the brain dump contradicts a principle, flag it here.

- **Auth provider is Neon Auth, not Supabase** — the brain dump says Supabase; the locked decision overrides it. Magic-link via Neon Auth's email-OTP / hosted magic-link flow.
- **JWT validation = RS256 with JWKS**, claim `sub` maps to existing `User.auth_user_id` column from `0001_initial_schema.py`. Do not redefine the column or invent a `supabase_id` field.
- **Module shape is fixed**: `modules/auth/decorators.py` (decorator), `modules/auth/service.py` (verify + magic-link send/verify), `modules/auth/routes.py` (login/verify/logout), `modules/auth/models.py` (already exists — do not rewrite).
- **Decorator contract is fixed**: `@require_auth` sets `g.current_user`; downstream code (Mon-T2/T3 usage decorator, billing webhook user lookup) reads from `g.current_user` and assumes it is a `User` SQLModel instance with `id` and `auth_user_id` populated.
- **Frontend = Angular standalone + signals + auth interceptor**, not React. Single-page app at `:4201`. HTTP 401 from any `/api/*` route → interceptor redirects to `/login`.
- **Path convention `api/X`** (never `flask/X`) per CLAUDE.md migration note. Generated guides must use the new prefix.
- **No DEV_BYPASS_AUTH back-door** — the brain dump option (a) suggested an env-flag bypass; the locked-decisions context omits it. Production refuses to start without `NEON_AUTH_*` env vars; dev uses a real Neon Auth project.

## Open Questions

- **Where does the Angular client store the JWT?** Options: (1) `localStorage` keyed by Neon Auth SDK convention, (2) HTTP-only cookie set by the Neon Auth hosted page, (3) in-memory signal (lost on reload). Default to (1) — it matches Neon Auth SDK behaviour and keeps the interceptor stateless.
- **Magic-link redirect target after `/auth/verify` succeeds**: deep-link to last opened project, or land on `/projects` index? Default to `/projects` for the first SaaS release; deep-link is a UX polish that waits for paying users to ask.
- **First-login `User` row creation**: does verification create the row eagerly, or does first authenticated request lazily insert? Eager creation in `/auth/verify` keeps the contract that `g.current_user` is always a hydrated row, no fallback path needed downstream.

## Dependencies & Sequencing

What blocks what. Not a task list — structural dependencies.

- **saas-persistence DONE** — `User` table, `auth_user_id` column, repositories all exist. This capability consumes them; do not modify the migration.
- **modular-restructure DONE** — `modules/auth/` is a top-level SAAS_OPTIONAL package per the 4-package shape; data backends nest under `modules/data/`.
- **Blocks billing webhook handler (Mon-T2/T3)** — webhook needs `User.auth_user_id` lookup to attach a Stripe customer to a row.
- **Blocks usage-metering decorator** — `@meter_usage` reads `g.current_user.id` to increment counters; no-ops without it.
- **Blocks per-tenant query enforcement** — `ProjectRepository.list_for_user(user_id)` already exists; routes need `@require_auth` on top of every existing AI/projects/context route.

## Explicitly Out of Scope

Things the brain dump mentioned or implied that should NOT be in the epic. Apply the Not-yet-built principle: speculative infrastructure deferred until a second consumer exists.

- **OAuth providers (Google, Apple, GitHub)** — magic link is the single login surface for the web SaaS; native auth waits for an iOS app or a paying customer requesting SSO.
- **Two-factor / TOTP** — Neon Auth supports it; spec-doc enables it as a per-user setting only when a user requests it.
- **Custom branded email templates** — Neon Auth defaults are fine for early phase; brand them when the marketing-page capability lands.
- **Multi-user workspaces / team primitives** — single user owns single set of projects; multi-tenant teams wait for a paying team customer.
- **DEV_BYPASS_AUTH env-flag back-door** — production refuses to start without real auth; dev uses a real Neon Auth project; the bypass is one less code path to test.
- **Self-hosted JWKS or custom JWT issuer** — Neon Auth issues; spec-doc validates. No key rotation logic; PyJWKClient handles cache + refresh.
- **Session-persistence schema (refresh tokens, server-side session table)** — Neon Auth owns session lifecycle; spec-doc holds no session state.
