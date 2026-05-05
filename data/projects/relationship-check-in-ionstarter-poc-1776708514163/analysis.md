---
sidebar_position: 1
---

# 🔍 Relationship Check-In – Analysis

**Purpose**: Identify problems and constraints driving the check-in capability, surface decisions not yet made, and kill scope before the epic inflates it.

**Date**: 2026-04-20

---

## Problem

Two partners need an honest, private way to measure relationship quality after meetups. Existing approaches (journaling, talking about it, ignoring it) lack structure, objectivity, and longitudinal tracking. The app provides structured measurement without advice, AI, or judgment — just numbers over time.

## Hard Constraints

| Constraint | Source | Implication |
|------------|--------|-------------|
| Reuse ionstarter SQLite dual-backend exactly | Builder principle: mirror what exists | No new abstractions, no adapter interfaces, no Elf store |
| Local-first, no server | Privacy requirement | All data in SQLite/localStorage, no networking |
| Same device for both partners | V1 simplification | Partner selection before rating, not device pairing |
| No ion-range | Flaky on web/iOS | Custom tap circles for 1–10 input |
| 48-hour session expiry | Matches existing bubls behavior | Incomplete sessions auto-expire |
| TanStack Query for page state | Ionstarter pattern | `injectQuery`, `injectMutation`, `invalidateQueries` |

## Open Questions

| Question | Decision | Rationale |
|----------|----------|-----------|
| How to prevent Partner B from seeing Partner A's scores before submitting? | Session state flag: `partner_a_submitted`, `partner_b_submitted`. Scores hidden in UI until both flags true. | Simplest enforcement — no crypto, no separate storage partitions |
| What happens if only one partner submits within 48h? | Session expires incomplete. Partial data preserved but not included in trends. | Avoids zombie sessions; partner can see their own draft but no comparison |
| How to handle question overlap in qualities (Q3 appears in both Mutual Respect and Long-term Viability)? | Same score contributes to multiple quality averages. No weighting. | Matches the braindump definition exactly — qualities aren't orthogonal by design |
| Draft persistence granularity? | Per-question auto-save on each tap. Full restore on reopen. | Prevents data loss if app backgrounded mid-rating |

## Dependencies

- Ionstarter boilerplate must be stable at `/projects/ionstarter/`
- `SqliteService` from `@app/core` must support the upgrade-statement registration pattern
- `CapacitorPreferencesService` from `@app/core` must be available for web fallback
- TanStack Query (`@tanstack/angular-query-experimental`) already installed

## Explicitly Out of Scope

- ❌ Networking or multi-device sync — same device only in v1
- ❌ AI analysis or advice — just measurement
- ❌ More than two partners — binary A/B only
- ❌ Custom questions — the ten questions are fixed
- ❌ Export/import data — no backup mechanism in v1
- ❌ Notifications or reminders — manual only
- ❌ Chart.js or any charting library — custom SVG sparklines only

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
