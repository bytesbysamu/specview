# 📅 Timeline: SaaS Phase 1: Security + Auth Completion

**Last Updated**: 2026-05-12

> Status tracking for this capability. This is the ONLY place for status.
> Epic and Architecture docs contain Priority, not Status.

---

## Done

| # | Task | Completed | Effort | Notes |
|---|------|-----------|--------|-------|
| — | — | — | — | — |

---

## In Progress

| # | Task | Started | Effort | Notes |
|---|------|---------|--------|-------|
| — | — | — | — | — |

---

## Backlog

| # | Task | Due | Effort | Notes |
|---|------|-----|--------|-------|
| 1 | Secrets Rotation & Env-Var Migration | — | 0.5 days | Rotate JWT secret + Neon password, move to env vars, update .env.example |
| 2 | Signup Endpoint + Angular Registration Page | — | 1 day | POST /api/auth/register, rate limiting, Angular signup form |
| 3 | Token Lifecycle + Refresh | — | 1 day | Token-lifecycle service, POST /api/auth/refresh, extend existing interceptor |
| 4 | CORS Lockdown, Security Headers & SKIP_AUTH Gating | — | 0.5 days | Lock CORS origins, add security headers, gate SKIP_AUTH behind FLASK_ENV |

---

## Epic Progress

| Metric | Count |
|--------|-------|
| Done | 0 |
| In Progress | 0 |
| Backlog | 4 |
| **Total** | **4** |

---

## Related Documents

- [Epic](./epic.md) – Task definitions and scope
- [Solution Architecture](./architecture.md) – Design decisions
- [Spec Index](./spec-index.md) – Document overview
