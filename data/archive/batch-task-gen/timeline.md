---
sidebar_position: 4
---

# 📅 Batch Task Generation – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Project inventory scanner | deferred | Core value covered by shell loop + existing --all flag |
| 2 | Batch manifest schema and seed data | deferred | Core value covered by shell loop + existing --all flag |
| 3 | Batch orchestrator script | deferred | Core value covered by shell loop + existing --all flag |
| 4 | Progress reporting | deferred | Core value covered by shell loop + existing --all flag |
| 5 | Failure recovery and retry manifest | deferred | Core value covered by shell loop + existing --all flag |
| 6 | Batch summary report | deferred | Core value covered by shell loop + existing --all flag |

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency
- `deferred` - Covered by existing tooling or deprioritized

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-17 | All | Created | Initial spec generation from braindump |
| 2026-04-17 | All | backlog -> deferred | Core value already covered by existing regen-task.mjs --all --parallel N + shell loop. See assessment below. |

---

## Assessment: Existing Coverage (2026-04-17)

The core value proposition of this epic -- "generate task specs for multiple projects in a single command" -- is already achievable with existing tooling:

```bash
for dir in projects/*/; do
  id=$(basename "$dir")
  [ -f "$dir/epic.md" ] && [ -f "$dir/architecture.md" ] && \
    node scripts/regen-task.mjs "$id" --all --parallel 2
done
```

`regen-task.mjs` already provides: `--all` (full-epic generation), `--parallel N` (concurrent tasks within a project), wave-ordered dependency resolution, auto-rescan, auto-review, retry pass, and summary table output.

What this epic would add on top: JSON manifest for project ordering, cross-project progress tables, retry manifests for failed projects, and batch summary reports. These are operational conveniences, not capability gaps. The effort (13+ hours across 6 tasks) is disproportionate to the incremental value over the shell loop.

**Recommendation**: Defer until the shell loop proves insufficient. If 10+ project runs expose a pattern of failures needing retry manifests or quality analysis needing cross-project summary reports, revisit.

---

## Related Documents

- [Epic](./epic.md) -- Task definitions and scope
- [Spec Index](./spec-index.md) -- Entry point