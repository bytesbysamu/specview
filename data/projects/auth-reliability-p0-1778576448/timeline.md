# 📅 Timeline: Auth Reliability & Credential Persistence

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
| 1 | CLI Error Signal Recovery — stdout in errors, 401 detection | — | 0.5 days | Parallel with #2 |
| 2 | Credential Volume & Entrypoint Guard — named volume, seed-only-once | — | 0.5 days | Parallel with #1 |
| 3 | Environment Cleanup & Container Auth Session — remove env vars, `claude login`, validate restart + teardown | — | 1 day | Depends on #1, #2 |
| 4 | Docker Healthcheck & Deploy Docs — fix `/api/health/anthropic` for CLI provider, wire healthcheck, update DEPLOY.md | — | 0.5 days | Depends on #3 |

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
