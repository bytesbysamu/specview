---
sidebar_position: 3
---

# 🏗️ Relationship Check-In – Solution Architecture

**Purpose**: Technical design for the Relationship Check-In capability inside Bubls.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Relationship Check-In is a self-contained bounded context added to the Bubls app as a lazy-loaded route at `/checkin`. It follows the standard Bubls feature structure: own page, service, model, mock, and child components. All state lives in local SQLite via the existing `SqliteService` — no new infrastructure, no server calls, no new dependencies.

The data flow is linear: partner selects identity → rates ten questions → responses persist to SQLite → quality scores compute and persist → when both partners complete, results unlock. Trend data is a read-only projection over historical quality scores. The entire feature operates offline-first by default because there is no online component.

The UI is three screens connected by router navigation within the `/checkin` route: (1) home/session management, (2) question rating, (3) results + trends. State flows through Angular signals scoped to the feature service — no global state, no cross-feature dependencies.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = Bounded Context | `/checkin` route is fully self-contained under `features/checkin/`. No imports from other features. Shared utilities (SQLite service, base service) accessed from `shared/`. |
| Adapter Pattern | `checkin.service.ts` adapts between UI signals and SQLite queries. Mock mode via `MOCK_CHECKIN` environment flag returns static data. Same interface regardless of source. |
| Local-First, No Server | All data in SQLite tables. No HTTP calls. No sync. The feature works identically in airplane mode. |
| Standalone + OnPush + Signals | Every component is standalone with OnPush change detection. Session state, rating progress, and computed qualities are Angular signals. |
| Dark-Only | Inherits Bubls dark theme via CSS custom properties. No theme toggle. Color-coding (green/amber/red) chosen for dark-background contrast. |
| Immutable Submissions | Once a partner submits, their responses are locked. No edits. This preserves honesty and simplifies the state machine. |

---

## Component Design

### Task 1: SQLite Schema + Data Service

**Purpose**: Define the persistence layer and provide an adapter for all check-in data operations.

**Components**:
- `checkin.model.ts` — Questions array (10 items, each with text and quality mapping), quality definitions (4 keys with display names and constituent question indices), score thresholds (healthy ≥7, concerning <5, divergence delta ≥3), `CheckinSession`, `CheckinResponse`, `CheckinQualityScore` interfaces
- `checkin.service.ts` — Adapter exposing: `createSession()`, `submitResponses(partner, scores[])`, `getActiveSession()`, `getSessionResults(sessionId)`, `getQualityTrends(limit)`, `expireStale()`. Internally calls `SqliteService` for all persistence. Mock mode returns static fixture data.
- `checkin.mock.ts` — Three complete mock sessions with divergent scores for development and testing

**SQLite Tables**:

```sql
CREATE TABLE checkin_session (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  -- status: 'active' | 'complete' | 'expired'
  partner_a_submitted INTEGER NOT NULL DEFAULT 0,
  partner_b_submitted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE checkin_response (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  partner TEXT NOT NULL,
  -- partner: 'A' | 'B'
  question_index INTEGER NOT NULL,
  score INTEGER NOT NULL,
  submitted_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES checkin_session(id)
);

CREATE TABLE checkin_quality_score (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  partner TEXT NOT NULL,
  quality_key TEXT NOT NULL,
  -- quality_key: 'communication' | 'respect' | 'prioritization' | 'viability'
  score REAL NOT NULL,
  FOREIGN KEY (session_id) REFERENCES checkin_session(id)
);
```

**Patterns**: Adapter (service wraps SQLite), Strategy (mock vs. real via env flag)

### Task 2: Partner Selection + Session Screen

**Purpose**: Entry point for the check-in flow — manage sessions and partner identity.

**Components**:
- `checkin.page.ts` — Route component at `/checkin`. Displays three states based on signals: (1) no active session → "Start Check-In" button, (2) active session, current partner not yet submitted → navigate to rating, (3) active session, current partner submitted → "Waiting for partner" with locked indicator. Session list below shows completed sessions as tappable cards linking to results.
- `partner-select.component.ts` — Modal or inline selector showing two large tap targets: "Partner A" and "Partner B". Selected partner stored in session signal (not persisted — each rating flow starts with selection). On select, creates session via service if none active, then navigates to rating.

**Patterns**: Feature Guard with Null Object (no sessions → empty state with CTA, never blank screen)

### Task 3: Question Rating Interface

**Purpose**: The core interaction — rate ten questions with minimal friction.

**Components**:
- `checkin-rate.component.ts` — Full-screen rating flow. Receives partner identity and session ID as route params. Renders one question at a time with transition animation between cards. Displays question text, a 1–10 horizontal scale (tap to select, active state highlighted), and navigation (back arrow, progress dots). Local signal array holds all ten scores. "Back" preserves state. Final screen summarizes all ten answers in a compact list with a "Submit" confirmation button.
- `score-selector.component.ts` — Reusable 1–10 horizontal picker. Ten circular tap targets in a row. Selected value highlighted with accent color. Emits `scoreChange` output signal. `data-test="score-{n}"` on each target.
- `question-card.component.ts` — Displays question text with index ("3 of 10"), handles swipe/tap navigation. `data-test="question-card"`.

**State Flow**:
```
partner signal ──→ rate component ──→ local scores[] signal
                                          │
                                    [Submit tap]
                                          │
                                          ▼
                                  service.submitResponses()
                                          │
                                          ▼
                              SQLite write + quality compute
                                          │
                                          ▼
                              navigate → results (if both done)
                                      → waiting (if partner pending)
```

**Patterns**: Standalone components, OnPush, Signals. No form module — raw signal bindings.

### Task 4: Submission Lock + Results View

**Purpose**: Enforce privacy until both submit, then display comparison.

**Components**:
- `checkin-waiting.component.ts` — Shown when current partner has submitted but the other hasn't. Displays a lock icon, "Waiting for [Partner Name]", and the session timestamp. No scores visible. Polls session status on interval (local SQLite query via service, not network). When both submitted, auto-navigates to results.
- `checkin-results.component.ts` — Four quality cards arranged vertically. Each card shows: quality name, Partner A score (left), Partner B score (right), delta badge between them. Color-coding: green background tint for ≥7, amber for 5–6.9, red for <5. Divergence (delta ≥3) gets a pulsing border or distinct icon. Below the four cards, a "View Trends" button navigates to the trends view. A "New Check-In" button returns to the home screen.

**Privacy Model**:
```
Session status = 'active'
├── partner_a_submitted = 0, partner_b_submitted = 0 → both can rate
├── partner_a_submitted = 1, partner_b_submitted = 0 → A sees waiting, B can rate
├── partner_a_submitted = 0, partner_b_submitted = 1 → B sees waiting, A can rate
└── partner_a_submitted = 1, partner_b_submitted = 1 → status → 'complete', results visible
```

No intermediate state leaks scores. The service method `getSessionResults()` returns `null` unless `status === 'complete'`.

**Patterns**: Feature Guard (incomplete session → waiting screen, never raw data), Observer (session status signal drives view transitions)

### Task 5: Trend Lines + Divergence Alerts

**Purpose**: Visualize relationship patterns over time.

**Components**:
- `checkin-trends.component.ts` — Four SVG sparkline charts, one per quality. Each chart plots Partner A (accent color 1) and Partner B (accent color 2) scores across the last N completed sessions. X-axis: session dates (short format). Y-axis: 1–10 scale with threshold lines at 5 and 7 drawn as dashed horizontals. Chart is an inline SVG — no charting library dependency.
- `sparkline.component.ts` — Reusable SVG sparkline. Inputs: `dataA: number[]`, `dataB: number[]`, `labels: string[]`, `thresholds: number[]`. Renders two polylines with circle markers at each data point. Responsive width via viewBox. `data-test="sparkline-{qualityKey}"`.
- `divergence-alert.component.ts` — List of alerts for the most recent session. Each alert: quality name, Partner A score, Partner B score, delta value. Only shown when delta ≥3. Plain language: "Communication Honesty: you scored 8, partner scored 4 (gap: 4)". `data-test="divergence-alert-{qualityKey}"`.

**SVG Rendering Strategy**:
```
viewBox="0 0 300 100"
│
├── dashed line at y=30 (maps to score 7)
├── dashed line at y=50 (maps to score 5)
├── polyline: Partner A scores (stroke: var(--accent-1))
├── polyline: Partner B scores (stroke: var(--accent-2))
└── circle markers at each data point
```

No external dependencies. Full dark-theme control via CSS custom properties. Accessible: each chart has an `aria-label` with the quality name and latest scores.

**Patterns**: Standalone, OnPush, Signals. Pure SVG rendering — no Canvas, no D3, no chart.js.

### Task 6: Session Expiry + Edge Cases

**Purpose**: Handle real-world usage patterns that break the happy path.

**Components**:
- Expiry logic in `checkin.service.ts`: on `getActiveSession()`, check if `created_at` is >48h ago and only one partner submitted. If so, set status to `expired`. Expired sessions appear in history with a "Partner didn't respond" label.
- Partial state recovery: `checkin-rate.component.ts` persists in-progress scores to a `checkin_draft` SQLite table on each question answer. On resume (app killed mid-rating), reload draft and continue from last answered question.
- Submit debounce: submit button disables immediately on tap via signal. Service method is idempotent — duplicate calls for same session+partner are no-ops.
- Empty state: first-ever visit to `/checkin` shows an illustration-free onboarding card: "Start your first check-in" with a single CTA button. `data-test="empty-state-cta"`.

---

## Execution Flow

```
[Phase 1 — Foundation]
   Task 1: Schema + Service
        │
        ├──────────────────┐
        ▼                  ▼
[Phase 2 — Core UI]
   Task 2: Selection    Task 3: Rating
        │                  │
        └────────┬─────────┘
                 ▼
[Phase 3 — Reveal]
   Task 4: Lock + Results
                 │
                 ▼
[Phase 4 — Insight]
   Task 5: Trends + Alerts
                 │
                 ▼
[Phase 5 — Hardening]
   Task 6: Expiry + Edge Cases
```

Tasks 2 and 3 are parallel — both depend only on Task 1's service and schema. Task 4 requires both because results need session creation (Task 2) and submitted responses (Task 3). Tasks 5 and 6 are sequential because trends need the full pipeline working end-to-end.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Bubls module vs. standalone app | Bubls module at `/checkin` | SQLite service, Capacitor base, dark theme, routing all shipped. Standalone would duplicate infrastructure for zero benefit. |
| Partner pairing model | Selection screen (Partner A / Partner B) | Simplest possible v1. No networking, no QR, no Bluetooth. Two people, one device, tap your name. Proper multi-device pairing is a separate epic when single-device proves the model. |
| Chart rendering | Inline SVG, no library | Four sparklines with two lines each is trivial SVG. A charting library adds bundle size, fights the dark theme, and constrains the visual design. Hand-rolled SVG is <100 lines per chart. |
| Score persistence | SQLite via existing service | Already shipped, already works on iOS and web. No new dependencies. LocalStorage would lose data on app reinstall. |
| Quality computation | Average of constituent questions, computed on submit | Simple, deterministic, no weighted scoring complexity. Stored as a materialized value in `checkin_quality_score` so trend queries are a single SELECT, not a join + aggregate. |
| Submission immutability | No edits after submit | Prevents second-guessing and score manipulation. The value of the tool is honesty; editability undermines it. If a partner made a mistake, they learn to be more careful next time — that's a feature. |
| Session expiry | 48h auto-expire | Prevents infinite "waiting for partner" states. Long enough for the other partner to pick up the device within a day. Short enough that stale sessions don't accumulate. |
| State management | Angular signals, feature-scoped | No global store. Session state, rating progress, and computed results are signals in `checkin.service.ts`. Components subscribe via the service. Explicit data flow, no magic. |
| Draft persistence | SQLite `checkin_draft` table | App kill during rating must not lose progress. Persisting each answer to a draft table means the worst case is re-answering the current question, not all ten. Draft deleted on successful submit. |
| Color palette for thresholds | Green ≥7, amber 5–6.9, red <5 | Matches the interpretation framework from the braindump. Universal traffic-light metaphor. Colors chosen for dark-background contrast accessibility. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

