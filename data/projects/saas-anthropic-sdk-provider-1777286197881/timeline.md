# 📅 Timeline: SaaS Anthropic SDK Provider

**Last Updated**: 2026-04-26

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
| 1 | **Surface SDK token usage on ChainResult** | TBD | 0.3 days | — |
| 2 | **Auto-detect SDK provider in adapter** | TBD | 0.2 days | — |
| 3 | **Add cost accumulator and `/api/ai/stats` endpoint** | TBD | 0.3 days | — |
| 4 | **Wire per-step model routing into AI workflows** | TBD | 0.2 days | — |
| 5 | **Add production startup gate to create_app** | TBD | 0.1 days | — |

---

## Epic Progress

| Metric | Count |
|--------|-------|
| Done | 0 |
| In Progress | 0 |
| Backlog | 5 |
| **Total** | **5** |

---

## Upstream Dependencies (Done — referenced, not redone)

| Capability | Status | Why it matters |
|------------|--------|----------------|
| modular-restructure | Done | This capability lands inside `modules/{ai,runtime,data,quality}` |
| persistence | Done | Independent; no shared schema |
| monetisation | Done | Will consume `/api/ai/stats` later for per-tenant attribution |
| operations-infra | Done | Coolify deploy job sets `ANTHROPIC_API_KEY`; startup gate enforces it |

---

## Related Documents

- [Epic](./epic.md) – Task definitions and scope
- [Solution Architecture](./architecture.md) – Design decisions
- [Spec Index](./spec-index.md) – Document overview
