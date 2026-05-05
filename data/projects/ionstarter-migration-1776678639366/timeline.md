---
sidebar_position: 4
---

# 📅 Bubls → Ionstarter Migration – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Foundation: scaffold ionstarter with bubls identity + resolve version gaps | backlog | |
| 2 | Reference migration: picks domain with TanStack Query pattern | backlog | Blocked by Task 1 |
| 3 | Migrate photoshoot domain | backlog | Blocked by Task 2 |
| 4 | Migrate text-gen domain | backlog | Blocked by Task 2, parallel with 3 |
| 5 | Migrate check-in domain | backlog | Blocked by Task 2, parallel with 3, 4 |
| 6 | Migrate onboarding + Four Worlds theme system | backlog | Blocked by Task 1, parallel with 2 |
| 7 | CI/CD: wire ionstarter-bubls to TestFlight pipeline | backlog | Blocked by Task 1, parallel with 2, 6 |

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency

---

## Estimated Timeline

| Phase | Tasks | Duration | Target |
|-------|-------|----------|--------|
| Phase 1 — Foundation | Task 1 | 2 days | Week 1 |
| Phase 2 — Reference + Theme | Tasks 2, 6, 7 (parallel) | 2 days | Week 1 |
| Phase 3 — Feature Migration | Tasks 3, 4, 5 (parallel) | 2 days | Week 2 |
| Phase 4 — Validation | Integration testing | 1 day | Week 2 |

**Total estimated duration**: 7 working days (under 2-week max)

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-20 | All | Created | Initial planning complete |
