---
sidebar_position: 2
---

# 🎯 Relationship Check-In – Epic

**Purpose**: Define scope and tasks for the relationship check-in capability on ionstarter.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and open questions resolved.

---

## Business Value

This is the validation POC for the bubls → ionstarter migration. The bubls check-in domain grew organically without architecture; rebuilding it on ionstarter proves (or disproves) that ionstarter's domain-driven patterns — SQLite dual-backend, TanStack Query page services, lazy-loaded feature routes — can absorb real product complexity without new abstractions.

If the check-in domain works cleanly, the migration recipe is proven: each bubls domain (picks, photoshoot, text) gets the same treatment. If it doesn't work cleanly, we learn what ionstarter is missing before committing to a full migration.

The app itself provides honest relationship measurement — ten questions rated 1–10 after each meetup, scores hidden until both partners submit, four computed qualities tracked over time. No advice, no AI, no suggestions. Just structured reflection that accumulates signal.

---

## Scope

### What This Epic Covers

- Check-in session creation and lifecycle (create → rate → submit → reveal)
- Ten-question rating UI with tap circles (1–10)
- Partner selection (A or B) before each rating
- Draft auto-save and restore on reopen
- 48-hour session expiry for incomplete sessions
- Quality computation (four qualities from ten questions)
- Side-by-side comparison view after both partners submit
- Trend tracking across sessions (last 10 default, show-all toggle)
- Per-quality and per-question trend sparklines (custom SVG)
- Divergence detection (flagging when partners score a quality >2 apart)
- SQLite persistence (native) and localStorage persistence (web)
- Full dual-backend implementation mirroring ionstarter's tasks domain

### What This Epic Does NOT Cover

- ❌ Multi-device sync or networking
- ❌ User accounts or authentication
- ❌ Push notifications or reminders
- ❌ AI-generated insights or advice
- ❌ Custom or editable questions
- ❌ More than two partners
- ❌ Data export/import/backup
- ❌ Onboarding flow or tutorial
- ❌ Dark/light theme toggle (dark only per bubls direction)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Domain models + persistence layer** | None | — | 1 day | High |
| 2 | **Session creation + partner selection** | 1 | 3 | 1 day | High |
| 3 | **Rating UI with tap circles** | 1 | 2 | 1 day | High |
| 4 | **Draft auto-save + session expiry** | 2, 3 | — | 0.5 day | High |
| 5 | **Submission + reveal logic** | 4 | — | 1 day | High |
| 6 | **Quality computation + comparison view** | 5 | — | 1 day | Medium |
| 7 | **Trend tracking + SVG sparklines** | 6 | — | 1.5 days | Medium |
| 8 | **Divergence detection + alerts** | 7 | — | 0.5 day | Low |

### Task Details

#### Task 1: Domain models + persistence layer
Define the SQLite schema (sessions table, responses table) and implement `CheckInSqliteService` mirroring `TasksSqliteService`. Implement `CheckInLocalStorageService` mirroring `TasksLocalStorageService`. Implement `CheckInService` with platform routing via `Capacitor.getPlatform() === 'web'`. Register upgrade statements for the SQLite tables. All CRUD operations: create session, save response, get session by ID, list completed sessions, delete session.

#### Task 2: Session creation + partner selection
Build the session start flow: user taps "New Check-In", selects Partner A or Partner B, a new session record is created with the current timestamp and selected partner. Route to the rating screen. If an active (non-expired, non-submitted) session exists for this partner, resume it instead of creating a new one.

#### Task 3: Rating UI with tap circles
Build the ten-question rating screen. Each question displayed one at a time (or scrollable list — match bubls UX). For each question, render ten tap circles numbered 1–10. Tapping a circle selects it (filled state). Allow changing selection before submission. Show progress indicator (e.g., "3 of 10 rated"). Style: dark background, minimal chrome, circles as the primary interaction.

#### Task 4: Draft auto-save + session expiry
On each tap circle selection, immediately persist the response to storage (no explicit save button needed). On app reopen, check for active sessions for this partner — if found and not expired (< 48h since creation), restore the draft with all previously tapped answers pre-filled. If expired, mark session as expired and do not include in trends. Clean up expired sessions on app launch.

#### Task 5: Submission + reveal logic
Add a "Submit" action after all ten questions are rated. On submit, mark this partner's session as submitted. Check if the other partner has also submitted for this session pair (same session date, both partners submitted). If yes, unlock the reveal — both partners' scores become visible. If no, show "Waiting for partner" state. The session pair is matched by creation date (same calendar day = same meetup).

#### Task 6: Quality computation + comparison view
Compute the four quality scores from the ten question responses: Communication Honesty (avg Q1, Q7, Q8), Mutual Respect (avg Q2, Q3, Q4), Prioritization (avg Q5, Q6, Q9), Long-term Viability (avg Q3, Q8, Q10). Display side-by-side: Partner A's qualities vs Partner B's qualities. Show per-question scores in a grid. Highlight divergences (>2 point gap) with visual treatment.

#### Task 7: Trend tracking + SVG sparklines
Aggregate completed sessions (both partners submitted) into a trend dataset. For each quality, plot dual-line SVG sparklines (Partner A line + Partner B line) across sessions. Default: last 10 sessions. "Show all" toggle expands to full history. Per-question trends available on drill-down. SVG is hand-built (no Chart.js) — simple polyline paths with viewBox scaling.

#### Task 8: Divergence detection + alerts
When computing trends, flag any quality where the absolute difference between Partner A and Partner B exceeds 2.0 points averaged over the last 3 sessions. Surface these as divergence indicators on the trends view — not modal alerts, just visual markers (e.g., warning icon next to the quality name, tooltip or inline text explaining the divergence).

---

## Success Criteria

- ✅ Both partners can independently rate all ten questions without seeing each other's scores
- ✅ Scores are revealed only after both partners submit
- ✅ Four quality scores are correctly computed and displayed
- ✅ Draft auto-saves on each tap and restores on reopen
- ✅ Sessions expire after 48 hours if incomplete
- ✅ Trend sparklines render correctly for 2+ completed sessions
- ✅ Divergence detection flags qualities with >2 point sustained gap
- ✅ App works on both web (localStorage) and native (SQLite) with identical behavior
- ✅ All persistence code mirrors ionstarter's tasks domain patterns exactly — no new abstractions
- ✅ Feature is a single lazy-loaded route in app.routes.ts, removable by deleting the folder + one line

---

## Non-Goals

- ❌ Replacing couples therapy or professional relationship guidance
- ❌ Building a social platform or sharing mechanism
- ❌ Gamification (streaks, badges, achievements)
- ❌ Historical data migration from bubls
- ❌ Accessibility beyond basic tap targets (v1 limitation, address post-POC)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
