---
sidebar_position: 0
---

# SaaS Auth — Magic Link

> Validate Neon Auth JWTs at every existing route and inject `g.current_user` so billing, usage metering, and per-tenant queries become enforceable.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Problems driving this capability |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design |
| [Timeline](./timeline.md) | Status tracking |
| [Task 1](./task-1-auth-service-jwt-verifier.md) | Auth service + JWT verifier |
| [Task 2](./task-2-require-auth-decorator-routes.md) | `@require_auth` decorator + `auth_bp` routes |
| [Task 3](./task-3-protect-existing-routes.md) | Protect existing routes with `@require_auth` |
| [Task 4](./task-4-angular-auth-service-interceptor.md) | Angular auth service + interceptor + login flow |

## Overview

Spec-doc has the `User` table and `auth_user_id` foreign-key column from saas-persistence, but no code path populates them. Every existing handler in `modules/ai/`, `modules/data/projects/`, `modules/data/context/`, `modules/data/templates/` operates as if the tool is single-tenant. Without verified JWTs and a `g.current_user` injection point, the billing webhook handler (Mon-T2/T3) has no row to attach Stripe customer IDs to, the `@meter_usage` decorator silently no-ops, and the per-tenant scoping the persistence migration set up is unenforced.

This capability ships the second link in the **persistence → auth → billing → metering** chain. Neon Auth issues the JWT (RS256, JWKS endpoint, `sub` claim → `User.auth_user_id`); spec-doc validates it via standard `PyJWKClient`; `@require_auth` hydrates `g.current_user`; every existing route gains the decorator; every existing repository call switches to its already-existing `_for_user` variant. The Angular side adds a magic-link login page, an auth callback that exchanges the one-time token for a JWT, an HTTP interceptor that attaches the `Authorization: Bearer` header to every `/api/*` request, and a router guard on every protected route.

The whole capability is four tasks — one pure-Python service, one decorator + four-route blueprint, one decorator-sprinkle pass over the existing routes, and one Angular surface. No new infrastructure beyond Neon Auth (already the database tenancy provider). No password storage, no OAuth complexity, no PCI/SOC2 burden.

## Related Documents

- [Analysis](./analysis.md)
- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
