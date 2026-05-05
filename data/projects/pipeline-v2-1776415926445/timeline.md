---
sidebar_position: 4
---

# Pipeline V2 -- Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Preamble Strip | backlog | Single regex in regen-task.mjs; parallel with 2, 3, 4 |
| 2 | Caveats Injection | backlog | Per-project + global fallback; parallel with 1, 3, 4 |
| 3 | Auto-Rescan | backlog | Foundation tasks only; parallel with 1, 2, 4 |
| 4 | Auto-Review | backlog | Advisory append to spec; parallel with 1, 2, 3 |
| 5 | Deviation-Count Parser | backlog | Standalone script; no dependencies |

---

## Epic Progress

| Category | Count |
|----------|-------|
| Done | 0 |
| In Progress | 0 |
| Backlog | 5 |
| **Total** | **5** |

---

## Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| Preamble strip + caveats injection shipped (quick wins) | Day 1 | backlog |
| Auto-rescan + auto-review shipped (pipeline core) | Day 2.5 | backlog |
| Deviation parser shipped, first report generated | Day 3.5 | backlog |
| Full pipeline run on a fresh braindump with deviation avg <= 3.0 | Day 4 | backlog |

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
| 2026-04-16 | -- | Epic created from braindump | 5 tasks, all independent, targeting deviation avg <= 3.0 |

---

## Related Documents

- [Epic](./epic.md) -- task definitions and success criteria
- [Architecture](./architecture.md) -- technical design

