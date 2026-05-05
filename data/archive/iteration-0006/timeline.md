# 📅 Timeline: Spec Doc

**Last Updated**: 2026-03-30

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

| # | Task | Effort | Priority | Parallel | Notes |
|---|------|--------|----------|----------|-------|
| 1 | **Document-First Editor** | 2 days | High | — | Foundation (lite) |
| 4 | **Agent Integration** | 2 days | High | — | Specs → Claude Code |
| 2 | **AI Text Operations** | 2 days | Medium | 5 | Core primitives |
| 3 | **Spec Bootstrap** | 2 days | Medium | — | Brain dump → specs |
| 5 | **Git Integration** | 1 day | Low | 2 | Export & versioning |

---

## Epic Progress

| Metric | Count |
|--------|-------|
| Done | 0 |
| In Progress | 0 |
| Backlog (MVP) | 5 |
| Backlog (Post-MVP) | 5 |
| **Total** | **10** |

---

## Future Backlog (Post-MVP)

> These tasks begin after MVP tasks 1-5 are complete. See [Epic](./epic.md) for details.

| # | Task | Effort | Priority | Dependencies | Notes |
|---|------|--------|----------|--------------|-------|
| 6 | **Validation Command** | 1 day | Medium | 3 | Quality checks |
| 7 | **Doc Update Suggestions** | 2 days | Medium | 4 | Post-implementation |
| 8 | **Claude Rules Generator** | 1 day | Low | 3 | .claude/rules/ |
| 9 | **Doc Drift Detection** | 2 days | Low | 4, 7 | Spec vs code sync |
| 10 | **Spec Search** | 1 day | Low | 3 | Natural language search |

---

## Execution Order

> **Reprioritized**: Agent Integration moved up to enable Spec Doc → Claude Code workflow faster.

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN TRACK                │  PARALLEL TRACK               │
├────────────────────────────┼────────────────────────────────┤
│                            │                                │
│  Task 1 (Editor lite)      │                                │
│       │                    │                                │
│       ▼                    │                                │
│  Task 4 (Agent)            │  ← Exit terminal, use Spec Doc │
│       │                    │                                │
│       ├────────────────────┼────────────┐                   │
│       │                    │            │                   │
│       ▼                    │            ▼                   │
│  Task 2 (AI Ops)           │       Task 5 (Git)             │
│       │                    │                                │
│       ▼                    │                                │
│  Task 3 (Bootstrap)        │                                │
│                            │                                │
└────────────────────────────┴────────────────────────────────┘
```

**Execution Notes**:
- Task 1 is foundation (lite version: editor + preview only)
- Task 4 moved up: enables specs → Claude Code without terminal
- Tasks 2 and 5 can run in parallel after Task 4
- Task 3 depends on Task 2 (AI operations required for bootstrap)

---

## Related Documents

- [🎯 Epic](./epic.md) – Task definitions and scope
- [🏗️ Architecture](./architecture.md) – Design decisions
- [📋 Spec Index](./spec-index.md) – Document overview
