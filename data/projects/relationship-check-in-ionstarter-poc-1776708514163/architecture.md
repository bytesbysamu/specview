---
sidebar_position: 3
---

# 🏗️ Relationship Check-In – Solution Architecture

**Purpose**: Technical design for the relationship check-in capability on ionstarter.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

The check-in feature is a single lazy-loaded Angular route that follows ionstarter's domain-driven feature pattern exactly. It has its own models, services, and page components — no cross-feature imports. Persistence uses the dual-backend technique from the tasks domain: `CheckInSqliteService` for native (Capacitor SQLite) and `CheckInLocalStorageService` for web (Capacitor Preferences), with `CheckInService` routing between them based on platform detection.

Page-level state management uses TanStack Query (`@tanstack/angular-query-experimental`) — queries for reads, mutations for writes, `invalidateQueries` on mutation success. No Elf store. No global state. Signals for local component state only.

The UI is dark-only (per bubls design direction), renders custom tap circles for 1–10 input (no ion-range), and uses hand-built SVG sparklines for trend visualization (no Chart.js dependency).

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = Bounded Context | Check-in is one folder, one route, zero cross-feature imports |
| Mirror existing patterns | Every service mirrors tasks domain — same method signatures, same DI pattern |
| Local-first, no server | All data in SQLite (native) or Capacitor Preferences (web) |
| Adapter pattern via platform routing | `CheckInService` routes to SQLite or localStorage based on `Capacitor.getPlatform()` |
| TanStack Query for async state | Page services use `injectQuery` / `injectMutation`, no manual loading flags |
| No new abstractions | No adapter interfaces, no base classes, no generic persistence layer |
| Standalone components, OnPush, Signals | Every component standalone, OnPush CD, local state via signals |

---

## Component Design

### Task 1: Domain Models + Persistence Layer

**Purpose**: Define the data schema and implement the dual-backend persistence services.

**Models** (`check-in.model.ts`):

```typescript
interface CheckInSession {
  id: string;              // nanoid()
  createdAt: string;       // ISO timestamp
  partner: 'A' | 'B';
  submitted: boolean;
  expiredAt?: string;      // Set when 48h passes without submission
}

interface CheckInResponse {
  id: string;              // nanoid()
  sessionId: string;       // FK to CheckInSession
  questionIndex: number;   // 0-9
  score: number;           // 1-10
  answeredAt: string;      // ISO timestamp
}

interface QualityScore {
  communicationHonesty: number;  // avg(Q1, Q7, Q8)
  mutualRespect: number;         // avg(Q2, Q3, Q4)
  prioritization: number;        // avg(Q5, Q6, Q9)
  longTermViability: number;     // avg(Q3, Q8, Q10)
}

interface CompletedMeetup {
  id: string;
  date: string;
  partnerA: { responses: CheckInResponse[]; qualities: QualityScore };
  partnerB: { responses: CheckInResponse[]; qualities: QualityScore };
}
```

**SQLite Schema** (registered as upgrade statements):

```sql
CREATE TABLE IF NOT EXISTS check_in_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  partner TEXT NOT NULL CHECK(partner IN ('A', 'B')),
  submitted INTEGER NOT NULL DEFAULT 0,
  expired_at TEXT
);

CREATE TABLE IF NOT EXISTS check_in_responses (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  question_index INTEGER NOT NULL CHECK(question_index BETWEEN 0 AND 9),
  score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 10),
  answered_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES check_in_sessions(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_responses_session_question
  ON check_in_responses(session_id, question_index);
```

**Components**:
- `check-in.model.ts` — All interfaces above
- `check-in-sqlite.service.ts` — Mirrors `TasksSqliteService`, uses `SqliteService` from `@app/core`
- `check-in-local-storage.service.ts` — Mirrors `TasksLocalStorageService`, uses `CapacitorPreferencesService` from `@app/core`
- `check-in.service.ts` — Routes via `Capacitor.getPlatform() === 'web'`, generates IDs with `nanoid()`
- `check-in.mock.ts` — Mock data for development/testing

**Patterns**: Dual-backend routing (platform detection), upgrade statement registration (SQLite migrations)

### Task 2: Session Creation + Partner Selection

**Purpose**: Entry point — create or resume a check-in session for the selected partner.

**Components**:
- `check-in-start.component.ts` — Partner selection UI (two large tap targets: "I'm Partner A" / "I'm Partner B")
- `check-in-start-page.service.ts` — TanStack Query: queries active sessions, mutation for create session

**Logic**:
1. On partner select, query for active (non-expired, non-submitted) session for that partner
2. If exists → navigate to rating screen with that session
3. If not → create new session via mutation → navigate to rating screen
4. Expiry check: if `createdAt` + 48h < now, mark as expired before querying

**Patterns**: `injectQuery` for active session lookup, `injectMutation` for session creation, `invalidateQueries` on success

### Task 3: Rating UI with Tap Circles

**Purpose**: The core interaction — ten questions, each rated 1–10 via tap circles.

**Components**:
- `check-in-rating.component.ts` — Container: loops through questions, tracks progress
- `tap-circle-rating.component.ts` — Reusable: renders 10 circles, emits selected value
- `question-card.component.ts` — Displays question text + tap circle rating for one question

**UI Spec**:
- Dark background, white/accent text
- Each circle: 32px diameter, 8px gap, row of 10
- Unselected: border only (1px white/30% opacity)
- Selected: filled accent color, number visible
- Below circles: subtle "1" and "10" labels at edges
- Progress: "3 of 10" top-right, or progress dots

**Patterns**: Standalone components, OnPush, output signals for score changes, `data-test` on every circle

### Task 4: Draft Auto-Save + Session Expiry

**Purpose**: Persist each answer immediately, restore on reopen, expire stale sessions.

**Components**:
- Logic integrated into `check-in-rating.component.ts` and `check-in.service.ts`
- Expiry logic in `check-in.service.ts` — called on app init and before session queries

**Logic**:
- On tap circle selection → call `saveResponse(sessionId, questionIndex, score)` immediately
- `saveResponse` upserts (unique constraint on session_id + question_index handles idempotency)
- On rating screen init → load all responses for session → pre-fill circles
- On app launch → scan for sessions where `createdAt + 48h < now` and `submitted = false` → set `expired_at`

**Patterns**: Upsert via `INSERT OR REPLACE` (SQLite) or object merge (localStorage), TanStack mutation with `invalidateQueries`

### Task 5: Submission + Reveal Logic

**Purpose**: Lock answers on submit, pair sessions by date, unlock comparison when both submit.

**Components**:
- `check-in-submit.component.ts` — Submit button + waiting state
- `check-in-reveal.component.ts` — Comparison view router (decides: show waiting or show results)

**Pairing Logic**:
- Sessions are paired by calendar date (same day = same meetup)
- On submit: set `submitted = true` for this session
- Query: find session for opposite partner on same calendar date where `submitted = true`
- If found → both submitted → navigate to comparison view
- If not → show "Waiting for [Partner X] to complete their check-in"

**Patterns**: Query with date filter, optimistic UI via TanStack mutation, `invalidateQueries(['check-in-sessions'])`

### Task 6: Quality Computation + Comparison View

**Purpose**: Derive four quality scores and display side-by-side comparison.

**Components**:
- `quality.util.ts` — Pure function: `computeQualities(responses: CheckInResponse[]): QualityScore`
- `check-in-comparison.component.ts` — Side-by-side quality scores + per-question grid
- `quality-bar.component.ts` — Horizontal bar showing score 1–10 with accent fill

**Computation**:
```typescript
function computeQualities(responses: CheckInResponse[]): QualityScore {
  const score = (idx: number) => responses.find(r => r.questionIndex === idx)?.score ?? 0;
  return {
    communicationHonesty: (score(0) + score(6) + score(7)) / 3,
    mutualRespect: (score(1) + score(2) + score(3)) / 3,
    prioritization: (score(4) + score(5) + score(8)) / 3,
    longTermViability: (score(2) + score(7) + score(9)) / 3,
  };
}
```

**Patterns**: Pure utility function (no service needed), standalone presentation components, `data-test` on each quality row

### Task 7: Trend Tracking + SVG Sparklines

**Purpose**: Visualize quality scores over time with dual-line sparklines.

**Components**:
- `check-in-trends.component.ts` — Container: loads completed meetups, renders sparklines
- `check-in-trends-page.service.ts` — TanStack Query: fetches all completed meetups, slices to last 10
- `sparkline.component.ts` — Reusable SVG component: two polyline paths, viewBox-scaled
- `trend-toggle.component.ts` — "Last 10" / "Show all" toggle

**SVG Sparkline Spec**:
- ViewBox: `0 0 200 60` (200 wide, 60 tall)
- X axis: evenly spaced points (meetup index)
- Y axis: scaled 1–10 → 0–60 (inverted: 10 at top)
- Partner A line: accent color (e.g., cyan)
- Partner B line: secondary color (e.g., pink)
- Dots at each data point: 3px radius circles
- No axis labels, no grid — pure sparkline

**Patterns**: Standalone SVG component with `@Input()` signals for data, responsive via viewBox (no fixed pixel sizes)

### Task 8: Divergence Detection + Alerts

**Purpose**: Surface sustained scoring gaps between partners.

**Components**:
- `divergence.util.ts` — Pure function: `detectDivergences(meetups: CompletedMeetup[], window: number): DivergenceAlert[]`
- Visual treatment in `check-in-trends.component.ts` — warning icon + inline text next to divergent qualities

**Logic**:
- For each quality, compute average of Partner A scores and Partner B scores over last `window` sessions (default: 3)
- If `|avgA - avgB| > 2.0` → flag as divergent
- Return array of `{ quality: string, gap: number, higherPartner: 'A' | 'B' }`

**Patterns**: Pure utility, no service. Visual-only alerts (no modals, no push notifications).

---

## Execution Flow

```
[Phase 1 — Foundation]
   Task 1 (models + persistence)
        │
        ├──────────────────┐
        ▼                  ▼
[Phase 2 — Core UX]
   Task 2 (sessions)    Task 3 (rating UI)
        │                  │
        └────────┬─────────┘
                 ▼
   Task 4 (auto-save + expiry)
                 │
                 ▼
[Phase 3 — Completion]
   Task 5 (submit + reveal)
                 │
                 ▼
   Task 6 (qualities + comparison)
                 │
                 ▼
[Phase 4 — Trends]
   Task 7 (sparklines)
                 │
                 ▼
   Task 8 (divergence)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Persistence pattern | Mirror tasks domain exactly | POC validates ionstarter patterns — introducing new patterns defeats the purpose |
| State management | TanStack Query, no Elf for this domain | Elf is used for app-level settings only; feature domains use TanStack Query for async state |
| Session pairing | Calendar date matching | Simplest approach for same-device usage — no session codes or pairing tokens needed |
| Input method | Custom tap circles | ion-range is flaky on web/iOS; tap circles give precise integer control |
| Trend visualization | Hand-built SVG sparklines | No Chart.js dependency; SVG scales perfectly; simple polyline paths are < 50 lines |
| Session expiry | 48 hours from creation | Matches existing bubls behavior; prevents indefinite zombie sessions |
| Draft persistence | Upsert on each tap | Zero data loss risk; no explicit save button; restore is transparent |
| Divergence threshold | >2.0 averaged over 3 sessions | Single-session spikes are noise; sustained gap over 3+ meetups is signal |
| Dark only | No theme toggle | Per bubls design direction — each surface gets its own visual world |
| ID generation | `nanoid()` | Matches ionstarter's tasks domain pattern |

---

## File Structure

```
src/app/domains/check-in/
├── check-in.model.ts
├── check-in.mock.ts
├── check-in.service.ts
├── check-in-sqlite.service.ts
├── check-in-local-storage.service.ts
├── check-in.routes.ts
├── pages/
│   ├── check-in-start/
│   │   ├── check-in-start.component.ts
│   │   └── check-in-start-page.service.ts
│   ├── check-in-rating/
│   │   ├── check-in-rating.component.ts
│   │   └── check-in-rating-page.service.ts
│   ├── check-in-comparison/
│   │   ├── check-in-comparison.component.ts
│   │   └── check-in-comparison-page.service.ts
│   └── check-in-trends/
│       ├── check-in-trends.component.ts
│       └── check-in-trends-page.service.ts
├── components/
│   ├── tap-circle-rating.component.ts
│   ├── question-card.component.ts
│   ├── quality-bar.component.ts
│   ├── sparkline.component.ts
│   └── trend-toggle.component.ts
└── utils/
    ├── quality.util.ts
    └── divergence.util.ts
```

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
