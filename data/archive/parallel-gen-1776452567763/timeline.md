
```markdown
---
sidebar_position: 4
---

# 📅 Parallel Task Generation – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Concurrency Ceiling Test | backlog | Run before other tasks to determine safe default |
| 2 | Extract Reusable Task Runner | backlog | Refactor existing inline logic into `generateOneTask()` |
| 3 | Dependency-Aware Wave Grouper | backlog | Pure function, can develop in parallel with Task 2 |
| 4 | `--parallel N` Flag Implementation | backlog | Blocked on Task 2 + 3 |
| 5 | `--all` Flag with Batched Waves | backlog | Blocked on Task 3 + 4 |
| 6 | Progress Reporter | backlog | Can develop in parallel with Task 5 |
| 7 | Retry Failed Tasks | backlog | Can develop in parallel with Task 6 |
| 8 | Integration Tests | backlog | Blocked on Task 5 + 7 |

---

## Estimated Timeline

```
Day 1 (morning):  Task 1 — Concurrency ceiling test
Day 1 (afternoon): Task 2 + Task 3 — Extract runner + wave grouper (parallel)
Day 2 (morning):  Task 4 — --parallel N flag
Day 2 (afternoon): Task 5 — --all flag with batched waves
Day 3 (morning):  Task 6 + Task 7 — Progress reporter + retry (parallel)
Day 3 (afternoon): Task 8 — Integration tests
```

**Total estimated effort**: 4.5 days (3 calendar days with parallelism)

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
| 2026-04-17 | All | Created | Initial spec generation from braindump |
```

===END===

---

All 5 files generated. Here's the summary:

| File | Key Content |
|------|-------------|
| **spec-index.md** | Overview, quick links, related docs |
| **analysis.md** | 5 hard constraints, 4 open questions with recommendations, dependency map, explicit scope exclusions |
| **epic.md** | 8 tasks with dependency graph, detailed task descriptions, success criteria |
| **architecture.md** | Component designs for all 8 tasks, hand-rolled Promise pool pattern, Kahn's algorithm for wave grouping, ANSI progress reporter, design decision rationale |
| **timeline.md** | Status tracking, 3-day estimated timeline with parallelism |

Key design decisions baked into the specs:
- **Dependency-aware waves** over blast-all (quality > speed)
- **Hand-rolled Promise pool** over `p-limit` (20 lines, no new dep)
- **Default concurrency 3** (proven safe, override with `--parallel N`)
- **Single retry pass at end** (no backoff, keeps it simple)
- **All changes in `regen-task.mjs`** (one consumer, no premature extraction)

Want me to write these to a specific directory once you grant write permissions?