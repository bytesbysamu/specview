---
sidebar_position: 2
---

# 🎯 Relationship Check-In – Epic

**Purpose**: Define scope and tasks for the Relationship Check-In capability inside Bubls.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed and open questions resolved.

---

## Business Value

Relationships fail silently. By the time one partner voices a concern, the pattern is months old and the evidence is anecdotal. A structured check-in after each meetup converts subjective feelings into trackable data — not to replace conversation, but to make it honest. When both partners independently rate the same ten questions, divergence becomes visible immediately: one partner scored Communication Honesty at 9, the other at 4. That gap is the conversation starter no amount of "how was your day" will produce.

The scoring model already exists and has been validated manually. The interpretation thresholds are calibrated: above 7 is real, below 5 is broken, diverging means different experiences, declining means erosion. What's missing is the container — a UI that removes friction from rating, enforces privacy until both submit, and renders trends over time. This is a tool for two specific people first. If it works for them, the model generalizes to any partnership that values measurement over assumption.

Building inside Bubls rather than as a standalone app eliminates all infrastructure work. The SQLite service, Capacitor base, dark theming, and routing are already shipped. The entire capability is a new lazy-loaded route and a new set of SQLite tables. Estimated total effort: 5 days.

---

## Scope

### What This Epic Covers

- SQLite schema for sessions, responses, and quality scores
- Partner selection screen (Partner A / Partner B)
- Ten-question rating interface (swipeable cards, 1–10 scale)
- Submission lock (neither sees results until both submit)
- Results comparison view (side-by-side scores per quality)
- Trend lines (per-quality score history across sessions)
- Divergence alerts (flag when partner scores differ by ≥3 on a quality)
- Session expiry (auto-close after 48h if only one partner submitted)
- Mock mode for development and testing

### What This Epic Does NOT Cover

- ❌ Cloud sync or multi-device pairing
- ❌ AI-generated advice or coaching
- ❌ Custom question editing
- ❌ Export, share, or print
- ❌ Push notifications or reminders
- ❌ QR code or Bluetooth partner pairing
- ❌ Onboarding tutorial or walkthrough

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **SQLite schema + migration + data service** | None | — | 1 day | High |
| 2 | **Partner selection + session creation screen** | 1 | 3 | 1 day | High |
| 3 | **Question rating interface** | 1 | 2 | 1.5 days | High |
| 4 | **Submission lock + results comparison view** | 2, 3 | — | 1 day | High |
| 5 | **Trend lines + divergence alerts** | 4 | — | 1 day | Medium |
| 6 | **Session expiry + edge cases + polish** | 5 | — | 0.5 days | Medium |

### Task Details

#### Task 1: SQLite schema + migration + data service

Create the SQLite tables: `checkin_session` (id, created_at, expired_at, status), `checkin_response` (id, session_id, partner, question_index, score), and `checkin_quality_score` (id, session_id, partner, quality_key, score). Build `checkin.service.ts` as the adapter between UI and SQLite — all reads and writes go through this service. Include mock mode gated by environment flag. Define the ten questions and four quality mappings in `checkin.model.ts` as static readonly arrays. Write the Alembic-style migration as a versioned SQL string executed on first access.

#### Task 2: Partner selection + session creation screen

Build `checkin.page.ts` as the entry point at `/checkin`. On load, show active session status or a "Start Check-In" button. When starting, display Partner A / Partner B selection. Tapping a partner name creates a new session (if none active) and navigates to the rating interface. If a session is already active and the current partner hasn't submitted, resume. If the current partner already submitted, show "Waiting for partner" state. Standalone component, OnPush, signals for session state.

#### Task 3: Question rating interface

Build `checkin-rate.component.ts` — a swipeable card stack showing one question at a time with a 1–10 slider or tap-to-select row. Track answers in a local signal array. Show progress indicator (e.g., "4 / 10"). Back button returns to previous question without losing state. Final card shows summary of all ten answers with a "Submit" button. On submit, write all ten responses to SQLite via the service, compute quality averages, write quality scores, and mark this partner's submission as complete.

#### Task 4: Submission lock + results comparison view

After both partners submit for a session, transition the session status to `complete`. Build `checkin-results.component.ts` showing side-by-side comparison: four quality cards, each displaying Partner A score, Partner B score, and the delta. Color-code by threshold: green (≥7), amber (5–6.9), red (<5). Highlight divergence (delta ≥3) with a distinct visual treatment. If only one partner has submitted, show a locked state with "Waiting for [Partner Name]" — no scores visible.

#### Task 5: Trend lines + divergence alerts

Build `checkin-trends.component.ts` showing four SVG sparkline charts (one per quality) with Partner A and Partner B lines overlaid. X-axis is session date, Y-axis is 1–10. Render at least the last 10 sessions. Below the charts, show a divergence alert list: any quality where the most recent session delta ≥3, with the specific scores and a plain-language label ("You scored Communication Honesty 8, partner scored 4"). Accessible from the check-in home screen as a "Trends" tab or toggle.

#### Task 6: Session expiry + edge cases + polish

Implement 48-hour auto-expiry for sessions where only one partner submitted. On app open, check for expired sessions and mark them `expired` in SQLite. Handle edge cases: app killed mid-rating (persist partial state), rapid double-tap on submit (debounce), empty session list (first-use empty state). Polish transitions between partner selection → rating → waiting → results. Ensure all interactive elements have `data-test` attributes.

---

## Success Criteria

- ✅ Two partners can independently rate ten questions on the same device without seeing each other's scores until both submit
- ✅ Four quality scores (Communication Honesty, Mutual Respect, Prioritization, Long-term Viability) compute correctly as averages of their constituent questions
- ✅ Results comparison view shows side-by-side scores with threshold color-coding and divergence highlighting
- ✅ Trend lines render per-quality history across at least 10 sessions with both partners' lines overlaid
- ✅ Divergence alerts fire when any quality delta ≥3 between partners
- ✅ Sessions auto-expire after 48 hours if only one partner submitted
- ✅ All data persists in local SQLite — no network calls, no server dependency
- ✅ Feature loads as a lazy route at `/checkin` with zero impact on other Bubls features
- ✅ Retention signal: both partners complete check-ins for 4 consecutive meetups within the first 3 weeks (unprompted return)

---

## Non-Goals

- ❌ Replacing conversation — this measures, it doesn't advise
- ❌ Clinical or therapeutic validity — the scoring model is personal, not peer-reviewed
- ❌ Multi-device sync — v1 is deliberately single-device to avoid infrastructure
- ❌ Gamification — no streaks, no badges, no rewards
- ❌ Social features — no sharing, no leaderboards, no community

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

