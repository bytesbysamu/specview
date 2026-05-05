---
sidebar_position: 4
---

# 📅 Distribution Experiment — Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Tracking endpoint + schema | backlog | Flask endpoint + Neon migration |
| 2 | Landing page | backlog | Static HTML, Coolify deploy |
| 3 | App-open event instrumentation | backlog | Capacitor lifecycle → tracking service |
| 4 | Reddit research + post draft | backlog | r/SideProject rules, post copy |
| 5 | Publish post + verify funnel | backlog | End-to-end walkthrough before go-live |
| 6 | Day-7 verdict query + decision | backlog | Run after 7 days, commit verdict doc |

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency

---

## Milestones

| Milestone | Target | Depends On |
|-----------|--------|------------|
| Funnel instrumented | Day 1 | Tasks 1, 2, 3 |
| Post live | Day 1-2 | Tasks 4, 5 |
| Verdict delivered | Day 8-9 | Task 6 |

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-17 | All | Created | Spec generated from braindump |

===END===

All 5 files already exist at `projects/distribution-experiment-1776432869622/` and are committed. The spec is tight to the braindump — 6 tasks, 3 phases of code (build parallel → prepare → launch), then a 7-day wait and a binary verdict. Every design decision traces back to the architecture principles (Neon only, Flask minimal, ship the car not the engine, adapter pattern with mock mode).