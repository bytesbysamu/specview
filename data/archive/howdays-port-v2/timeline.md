---
sidebar_position: 4
---

# 📅 Port howDays Boilerplate – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | SPM → CocoaPods migration | backlog | Foundation — blocks all other tasks |
| 2 | Capacitor plugin verification | backlog | Acceptance gate for task 1; requires real iPhone |
| 3 | SQLite local storage module | backlog | Can start after task 1; parallel with 4, 5 |
| 4 | RevenueCat subscription module | backlog | Needs RevenueCat project + API key provisioned; soft dependency on task 3 for entitlement cache |
| 5 | Live-update module | backlog | Can start after task 1; parallel with 3, 4 |
| 6 | CI/CD pipeline update | backlog | Can start after task 1; parallel with task 2 |

---

## Estimated Timeline

| Phase | Tasks | Duration | Notes |
|-------|-------|----------|-------|
| Phase 1 | 1, 2, 6 | 1.5 days | Serial: migrate → verify → update CI |
| Phase 2 | 3, 4, 5 | 1.5 days | Parallel: all three modules simultaneously |
| **Total** | | **3 days** | Conservative; howDays reference code reduces unknowns |

---

## Prerequisites

| Prerequisite | Status | Needed By |
|-------------|--------|-----------|
| CocoaPods installed on dev machine | backlog | Task 1 |
| RevenueCat project created for Bubls | backlog | Task 4 |
| RevenueCat API key provisioned | backlog | Task 4 |
| At least one RevenueCat offering configured | backlog | Task 4 |
| Physical iPhone available for testing | backlog | Task 2 |

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
| 2026-04-18 | All | Created | Initial epic breakdown from braindump |

===END===