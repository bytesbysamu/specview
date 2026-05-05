---
sidebar_position: 4
---

# SaaS Auth — Magic Link — Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Auth service + JWT verifier | backlog | |
| 2 | `@require_auth` decorator + `auth_bp` routes | backlog | Depends on 1 |
| 3 | Protect existing routes with `@require_auth` | backlog | Depends on 2 |
| 4 | Angular auth service + interceptor + login flow | backlog | Depends on 2; parallel with 3 |

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-26 | — | Capability bootstrapped from braindump-saas-auth-magic-link.md | Locked to Neon Auth (not Supabase); reuses User.auth_user_id from saas-persistence |

===END===
