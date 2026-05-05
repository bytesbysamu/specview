# Task 6: Session Expiry + Edge Cases + Polish

**Purpose**: Harden the Relationship Check-In for real-world usage. Sessions that sit forever in "waiting for partner" get auto-expired after 48 hours. In-progress ratings survive an app kill via draft persistence. Double-tap on submit is debounced at the signal level. First-time users see an empty state CTA instead of a blank screen. Transitions between views are polished. Every interactive element gets a `data-test` attribute. This is the final task -- after this, the feature ships.

**Effort**: 0.5 days

**Dependencies**:
- Task 1 (SQLite schema + data service) -- `CheckinDataService` at `/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts` with `init()`, `createSession()`, `submitScores()`, `getSession()`, `getActiveSession()`, `bothSubmitted()`, `getCompletedSessions()`, `getScoresForSession()`.
- Task 2 (Partner selection + session creation) -- `CheckinPage` at `/projects/bubls/src/app/pages/checkin/checkin.page.ts` with `PageView` type and session management.
- Task 3 (Question rating interface) -- `QuestionRatingComponent` at `/projects/bubls/src/app/features/checkin/components/question-rating.component.ts` with slider inputs, `scores` signal, `onSubmit()`, `onSliderChange()`.
- Task 4 (Results + waiting) -- `CheckinResultsComponent` and `CheckinWaitingComponent`.
- Task 5 (Trends) -- `CheckinTrendsComponent`.
- Model -- `checkin.model.ts` with `SessionStatus` (already includes `'expired'`), `CheckinSession`, `QUESTION_COUNT`.
- SQLite -- `SqliteService` at `/projects/bubls/src/app/shared/sqlite/sqlite.service.ts` with `addUpgradeStatements()`, `query()`, `execute()`.

**Blocks**: Nothing. This is the final task in the epic.

**Related**:
- [Solution Architecture -- Task 6 Edge Cases](./architecture.md)
- [Epic -- Task 6 Details](./epic.md)

---

## 1. Objective

Deliver four hardening features and one polish pass:

1. **48-hour session expiry** -- On every call to `getActiveSession()`, check whether the session's `created_at` is more than 48 hours old AND only one partner has submitted. If so, mark it `expired` in SQLite before returning `null`. Expired sessions appear in the completed sessions history with a "Partner didn't respond" label.

2. **Draft persistence** -- A new `checkin_draft` SQLite table stores in-progress scores as each question is answered. If the app is killed mid-rating and the user returns, the draft is reloaded so they can continue from where they left off instead of re-answering all ten questions. The draft is deleted on successful submit.

3. **Submit debounce** -- The submit button in `QuestionRatingComponent` already disables via the `submitting` signal. Add idempotency to the service: if `submitScores()` is called for a session+partner combination that already has rows in `checkin_response`, it is a no-op. This prevents duplicate writes from rapid taps that bypass the UI guard.

4. **Empty state** -- When the user visits `/checkin` for the very first time (zero sessions of any status), show a first-use onboarding card with "Start your first check-in" and a single CTA button. Distinct from the current "start" view which says "Start Check-In" -- the empty state is warmer, acknowledges this is their first time, and has `data-test="empty-state-cta"`.

5. **Polish pass** -- Audit all components for missing `data-test` attributes. Add CSS transitions for view switching in `CheckinPage`. Ensure `prefers-reduced-motion` is respected. Verify all interactive elements are keyboard-accessible.

---

## 2. Inputs

Every file referenced below exists and is shipped from Tasks 1-5.

### Model (`/projects/bubls/src/app/features/checkin/checkin.model.ts`)

```typescript
export type Partner = 'A' | 'B';
export type SessionStatus = 'active' | 'complete' | 'expired';
export type QualityKey = 'communication' | 'respect' | 'prioritization' | 'viability';

export const QUESTION_COUNT = 10;

export interface CheckinSession {
  id: string;
  created_at: string;
  status: SessionStatus;
  partner_a_submitted: number; // 0 | 1
  partner_b_submitted: number; // 0 | 1
}

export interface CheckinResponse {
  id: string;
  session_id: string;
  partner: Partner;
  question_index: number;
  score: number;
  submitted_at: string;
}
```

New interface to add:

```typescript
export interface CheckinDraft {
  session_id: string;
  partner: Partner;
  question_index: number;
  score: number;
}
```

### Data Service (`/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts`)

Existing public API:

| Method | Signature | Returns |
|--------|-----------|---------|
| `init()` | `async init(): Promise<void>` | Registers migration, warms DB. Idempotent. |
| `createSession()` | `async createSession(): Promise<string>` | New session id. |
| `submitScores(sessionId, partner, scores)` | `async submitScores(sessionId: string, partner: Partner, scores: number[]): Promise<void>` | Writes responses + quality scores, flips submitted flag. |
| `getSession(id)` | `async getSession(id: string): Promise<CheckinSession \| null>` | Single session by ID. |
| `getActiveSession()` | `async getActiveSession(): Promise<CheckinSession \| null>` | Most recent active session. |
| `bothSubmitted(sessionId)` | `async bothSubmitted(sessionId: string): Promise<boolean>` | True if both partners submitted. |
| `getCompletedSessions(limit)` | `async getCompletedSessions(limit: number): Promise<CheckinSession[]>` | Last N completed sessions, oldest-first. |
| `getScoresForSession(sessionId)` | `async getScoresForSession(sessionId: string): Promise<CheckinQualityScore[]>` | All quality scores for one session. |

New methods to add:

| Method | Signature | Returns |
|--------|-----------|---------|
| `saveDraft(sessionId, partner, questionIndex, score)` | `async saveDraft(sessionId: string, partner: Partner, questionIndex: number, score: number): Promise<void>` | Upsert one draft answer. |
| `loadDraft(sessionId, partner)` | `async loadDraft(sessionId: string, partner: Partner): Promise<CheckinDraft[]>` | All draft answers for a session+partner. |
| `deleteDraft(sessionId, partner)` | `async deleteDraft(sessionId: string, partner: Partner): Promise<void>` | Remove all draft rows for a session+partner. |
| `hasSubmitted(sessionId, partner)` | `async hasSubmitted(sessionId: string, partner: Partner): Promise<boolean>` | True if `checkin_response` rows exist for this session+partner. |
| `getSessionCount()` | `async getSessionCount(): Promise<number>` | Total sessions of any status. Used for empty state detection. |
| `getExpiredSessions(limit)` | `async getExpiredSessions(limit: number): Promise<CheckinSession[]>` | Last N expired sessions, newest-first. For history display. |

Modified method:

| Method | Change |
|--------|--------|
| `getActiveSession()` | Before returning an active session, check if `created_at` is >48h ago and only one partner submitted. If so, execute `UPDATE ... SET status = 'expired'` and return `null`. |

### QuestionRatingComponent (`/projects/bubls/src/app/features/checkin/components/question-rating.component.ts`)

Key existing behavior:
- `scores` signal: `signal<number[]>(Array.from({ length: 10 }, () => 0))` -- local array, index = question, value = 0 (unset) or 1-10.
- `onSliderChange(questionIndex, event)` -- updates the `scores` signal, fires haptic.
- `onSubmit()` -- calls `dataService.submitScores()`, checks `bothSubmitted()`, emits `submitted`.
- `submitting` signal already guards double submit at the UI level.
- Inputs: `sessionId` (required), `partner` (required).

### CheckinPage (`/projects/bubls/src/app/pages/checkin/checkin.page.ts`)

Key existing behavior:
- `PageView` type: `'loading' | 'start' | 'select-partner' | 'rating' | 'waiting'`
- `ngOnInit()` checks for active session, routes to appropriate view.
- Currently no empty state distinction -- "start" view handles both first-time and returning users.

### SQLite Migration Pattern

Existing migration is version 2 (creates `checkin_session`, `checkin_response`, `checkin_quality_score`). The new `checkin_draft` table requires a version 3 migration.

```typescript
const MIGRATIONS: Migration[] = [
  {
    version: 2,
    statements: [/* existing tables */],
  },
  {
    version: 3,
    statements: [/* checkin_draft table */],
  },
];
```

### Routes (`/projects/bubls/src/app/app.routes.ts`)

Current structure -- no route changes needed for Task 6:

```typescript
{
  path: 'checkin',
  children: [
    { path: '', loadComponent: () => import('./pages/checkin/checkin.page').then(m => m.CheckinPage) },
    { path: 'waiting/:sessionId', loadComponent: () => import('./features/checkin/components/checkin-waiting.component').then(m => m.CheckinWaitingComponent) },
    { path: 'results/:sessionId', loadComponent: () => import('./features/checkin/components/checkin-results.component').then(m => m.CheckinResultsComponent) },
    { path: 'trends', loadComponent: () => import('./features/checkin/components/checkin-trends.component').then(m => m.CheckinTrendsComponent) },
  ],
},
```

### Design Tokens (existing, no changes)

| Token | Usage |
|-------|-------|
| `--accent-warm` | Primary CTA background, empty state CTA |
| `--on-accent-warm` | CTA text color |
| `--accent-warm-tint` | Active press feedback |
| `--surface` | Card backgrounds |
| `--hairline` | Borders |
| `--text-primary` | Headings |
| `--text-secondary` | Body text |
| `--text-muted` | Captions, expired labels |
| `--danger` | Error text |
| `--font-display` | Cormorant Garamond for headings |
| `--font-body` | Instrument Sans for body |
| `--r-pill` | Rounded button border-radius |
| `--r-md` | Card border-radius |
| `--shadow-soft` | Card elevation |
| `--t-press` | Press transition timing |
| `--ease-out` | Transition easing |
| `--t-in` | Enter transition timing |

---

## 3. Outputs

### Files to Modify

| File | Change |
|------|--------|
| `src/app/features/checkin/checkin.model.ts` | Add `CheckinDraft` interface. Add `SESSION_EXPIRY_MS` constant (48 * 60 * 60 * 1000). |
| `src/app/features/checkin/services/checkin-data.service.ts` | Add migration v3 (`checkin_draft` table). Add `saveDraft()`, `loadDraft()`, `deleteDraft()`, `hasSubmitted()`, `getSessionCount()`, `getExpiredSessions()`. Modify `getActiveSession()` to auto-expire stale sessions. Make `submitScores()` idempotent. |
| `src/app/features/checkin/services/checkin-data.service.spec.ts` | Add tests for all new and modified methods. |
| `src/app/features/checkin/components/question-rating.component.ts` | Add draft persistence: call `saveDraft()` on each slider change, call `loadDraft()` on init to restore partial state, call `deleteDraft()` after successful submit. Add idempotency guard in `onSubmit()`. |
| `src/app/features/checkin/components/question-rating.component.spec.ts` | Add tests for draft persistence and idempotency. (**New file** -- no spec exists yet for this component.) |
| `src/app/pages/checkin/checkin.page.ts` | Add `'empty'` to `PageView` union. Add empty state detection via `getSessionCount()`. Add `getExpiredSessions()` call for history display. Add CSS transitions for view switching. |
| `src/app/pages/checkin/checkin.page.spec.ts` | Add tests for empty state, expired session display, and view transitions. |
| `src/app/features/checkin/components/checkin-waiting.component.ts` | Show expiry timestamp ("Expires in X hours") computed from session `created_at` + 48h. |
| `src/app/features/checkin/components/checkin-waiting.component.spec.ts` | Add test for expiry countdown display. |
| `src/app/features/checkin/index.ts` | Add `CheckinDraft` type export. Add `SESSION_EXPIRY_MS` constant export. |

### Files to Leave Alone

| File | Reason |
|------|--------|
| `src/app/features/checkin/components/checkin-results.component.ts` | No changes. Expired sessions are not shown in results. Results already handles complete sessions correctly. |
| `src/app/features/checkin/components/checkin-results.component.spec.ts` | No changes needed. |
| `src/app/features/checkin/components/checkin-trends.component.ts` | No changes. Trends query `status = 'complete'` -- expired sessions are excluded by the existing query. |
| `src/app/features/checkin/components/sparkline.component.ts` | Pure presentational, no changes. |
| `src/app/features/checkin/components/divergence-alert.component.ts` | Pure presentational, no changes. |
| `src/app/app.routes.ts` | No new routes. All changes are within existing components. |
| `src/app/shared/sqlite/sqlite.service.ts` | Consumed transitively. No changes. |
| `src/app/styles/tokens.scss` | All colors via existing tokens. No new globals. |

---

## 4. Expiry Logic

### 48-Hour Auto-Expiry

**Where it runs**: Inside `CheckinDataService.getActiveSession()`. This is the single entry point that determines whether a session is still actionable. It is called by `CheckinPage.ngOnInit()` on every visit to `/checkin`, which covers app open, tab switch, and navigation back from other views.

**Expiry constant** (added to `checkin.model.ts`):

```typescript
/** 48 hours in milliseconds. Sessions exceeding this age with only one partner submitted are expired. */
export const SESSION_EXPIRY_MS = 48 * 60 * 60 * 1000;
```

**Modified `getActiveSession()` logic**:

```typescript
async getActiveSession(): Promise<CheckinSession | null> {
  const result = await this.sqlite.query<CheckinSession>({
    database: DB_NAME,
    statement:
      `SELECT * FROM checkin_session WHERE status = 'active'
       ORDER BY created_at DESC LIMIT 1;`,
  });

  if (result.values.length === 0) {
    return null;
  }

  const session = result.values[0];

  // Auto-expire: >48h old AND only one partner submitted
  const age = Date.now() - new Date(session.created_at).getTime();
  const onePartnerOnly =
    (session.partner_a_submitted === 1 && session.partner_b_submitted === 0) ||
    (session.partner_a_submitted === 0 && session.partner_b_submitted === 1);

  if (age > SESSION_EXPIRY_MS && onePartnerOnly) {
    await this.sqlite.execute({
      database: DB_NAME,
      statement: `UPDATE checkin_session SET status = 'expired' WHERE id = ?;`,
      values: [session.id],
    });
    return null;
  }

  // Also expire sessions where NEITHER partner submitted and >48h old
  // (abandoned sessions)
  if (age > SESSION_EXPIRY_MS && session.partner_a_submitted === 0 && session.partner_b_submitted === 0) {
    await this.sqlite.execute({
      database: DB_NAME,
      statement: `UPDATE checkin_session SET status = 'expired' WHERE id = ?;`,
      values: [session.id],
    });
    return null;
  }

  return session;
}
```

**Rationale for checking both one-submitted and zero-submitted**: The architecture specifies "only one partner submitted" as the trigger, but a session where neither partner submitted after 48h is equally stale. Both get expired.

**What does NOT trigger expiry**: A session where both partners submitted is already `complete` (status changed by `submitScores()`), so it never appears in the `WHERE status = 'active'` query.

### Expired Sessions in History

**New method `getExpiredSessions(limit)`**:

```typescript
async getExpiredSessions(limit = 10): Promise<CheckinSession[]> {
  const result = await this.sqlite.query<CheckinSession>({
    database: DB_NAME,
    statement:
      `SELECT * FROM checkin_session WHERE status = 'expired'
       ORDER BY created_at DESC LIMIT ?;`,
    values: [limit],
  });
  return result.values;
}
```

**Display in CheckinPage**: Expired sessions are shown below the main CTA in the `start` view (not the `empty` view -- empty means zero sessions). Each expired session card shows:
- Date of the session
- "Partner didn't respond" label in muted text
- `data-test="expired-session-{id}"`

This is a read-only list. No action buttons on expired session cards. The purpose is informational -- the user sees that the session timed out, not that it vanished.

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Session is exactly 48h old | NOT expired. The check is `>`, not `>=`. Grace period matters. |
| Session is 48h01m old, one submitted | Expired on next `getActiveSession()` call. |
| Both partners submitted within 48h | Session is `complete`, never reaches expiry check. |
| Neither partner submitted after 48h | Expired (abandoned session cleanup). |
| Device clock is wrong (ahead by days) | Session may expire prematurely. Acceptable risk -- clock manipulation is an edge case within an edge case. |
| Multiple active sessions (should not happen) | `getActiveSession()` returns the most recent one. Older active sessions will be expired on subsequent calls if they hit the 48h threshold. |
| App is offline for >48h | On next open, `getActiveSession()` fires, detects staleness, expires the session. No network call needed. |

---

## 5. Draft Persistence

### Schema

**Migration v3** (added to the `MIGRATIONS` array in `checkin-data.service.ts`):

```typescript
{
  version: 3,
  statements: [
    `CREATE TABLE IF NOT EXISTS checkin_draft (
      session_id TEXT NOT NULL,
      partner TEXT NOT NULL,
      question_index INTEGER NOT NULL,
      score INTEGER NOT NULL,
      PRIMARY KEY (session_id, partner, question_index)
    );`,
  ],
}
```

The composite primary key `(session_id, partner, question_index)` means `INSERT OR REPLACE` gives us upsert behavior. No separate `id` column -- the triple uniquely identifies a draft answer.

### Model Interface

Added to `checkin.model.ts`:

```typescript
export interface CheckinDraft {
  session_id: string;
  partner: Partner;
  question_index: number;
  score: number;
}
```

### Data Service Methods

**`saveDraft()`** -- Called on every slider change. Upserts a single draft row.

```typescript
async saveDraft(
  sessionId: string,
  partner: Partner,
  questionIndex: number,
  score: number,
): Promise<void> {
  await this.sqlite.execute({
    database: DB_NAME,
    statement:
      `INSERT OR REPLACE INTO checkin_draft (session_id, partner, question_index, score)
       VALUES (?, ?, ?, ?);`,
    values: [sessionId, partner, questionIndex, score],
  });
}
```

**`loadDraft()`** -- Called when `QuestionRatingComponent` initializes. Returns all draft answers for a session+partner pair.

```typescript
async loadDraft(
  sessionId: string,
  partner: Partner,
): Promise<CheckinDraft[]> {
  const result = await this.sqlite.query<CheckinDraft>({
    database: DB_NAME,
    statement:
      `SELECT * FROM checkin_draft WHERE session_id = ? AND partner = ?;`,
    values: [sessionId, partner],
  });
  return result.values;
}
```

**`deleteDraft()`** -- Called after successful `submitScores()`. Removes all draft rows for a session+partner.

```typescript
async deleteDraft(
  sessionId: string,
  partner: Partner,
): Promise<void> {
  await this.sqlite.execute({
    database: DB_NAME,
    statement:
      `DELETE FROM checkin_draft WHERE session_id = ? AND partner = ?;`,
    values: [sessionId, partner],
  });
}
```

### QuestionRatingComponent Changes

**OnInit lifecycle** -- Load draft on component initialization:

```typescript
async ngOnInit(): Promise<void> {
  const drafts = await this.dataService.loadDraft(
    this.sessionId(),
    this.partner(),
  );
  if (drafts.length > 0) {
    this.scores.update((prev) => {
      const next = [...prev];
      for (const draft of drafts) {
        next[draft.question_index] = draft.score;
      }
      return next;
    });
  }
}
```

Note: `QuestionRatingComponent` currently does not implement `OnInit`. Add it.

**onSliderChange() modification** -- Persist draft after updating the signal:

```typescript
onSliderChange(questionIndex: number, event: CustomEvent): void {
  const value = event.detail.value as number;
  if (typeof value !== 'number' || value < 1 || value > 10) return;

  this.scores.update((prev) => {
    const next = [...prev];
    next[questionIndex] = value;
    return next;
  });

  // Persist draft (fire-and-forget)
  this.dataService.saveDraft(
    this.sessionId(),
    this.partner(),
    questionIndex,
    value,
  ).catch(() => { /* best effort */ });

  this.hapticLight();
}
```

The `saveDraft()` call is fire-and-forget. It should not block the slider interaction or cause errors to surface. If the write fails, the user can still submit -- they just lose the partial state recovery for that question.

**onSubmit() modification** -- Delete draft after successful submit:

```typescript
async onSubmit(): Promise<void> {
  if (!this.allAnswered() || this.submitting()) return;

  this.submitting.set(true);
  try {
    await this.dataService.submitScores(
      this.sessionId(),
      this.partner(),
      this.scores(),
    );

    // Clean up draft
    await this.dataService.deleteDraft(
      this.sessionId(),
      this.partner(),
    ).catch(() => { /* best effort */ });

    const bothDone = await this.dataService.bothSubmitted(this.sessionId());

    if (!bothDone) {
      this.waiting.set(true);
    }

    this.hapticSuccess();
    this.submitted.emit({ bothDone });
  } catch {
    this.submitting.set(false);
  }
}
```

### Draft Lifecycle

```
User taps slider for Q3
  → scores signal updates (Q3 = 7)
  → saveDraft(sessionId, 'A', 3, 7) fires (async, no await)
  → hapticLight()

User taps slider for Q7
  → scores signal updates (Q7 = 5)
  → saveDraft(sessionId, 'A', 7, 5) fires
  → hapticLight()

APP KILLED

User reopens app, navigates to /checkin
  → getActiveSession() returns active session
  → user selects Partner A
  → QuestionRatingComponent.ngOnInit()
  → loadDraft(sessionId, 'A') returns [{q:3, s:7}, {q:7, s:5}]
  → scores signal pre-filled: [0,0,0,7,0,0,0,5,0,0]
  → UI shows 2/10 answered, Q3 and Q7 sliders at saved positions

User completes remaining 8 questions and submits
  → submitScores() writes all 10 responses
  → deleteDraft(sessionId, 'A') cleans up
```

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| No draft exists (fresh start) | `loadDraft()` returns `[]`. Scores array stays all zeros. Normal flow. |
| Draft exists for a different partner | `loadDraft()` filters by partner. Each partner's draft is independent. |
| Draft exists but session has been expired | User navigates to `/checkin`, `getActiveSession()` expires the session and returns `null`. User sees start/empty view. The orphaned draft rows persist in SQLite but are harmless -- they will never be loaded because the session is no longer active. Could add cleanup in expiry logic, but not necessary for v1. |
| Draft has all 10 answers | User is shown 10/10 answered and can submit immediately. |
| `saveDraft()` fails (SQLite error) | Caught silently. User can still submit normally -- they just lose crash recovery for that question. |
| Rapid slider changes (same question) | `INSERT OR REPLACE` handles the upsert. Each save overwrites the previous value for that question index. No duplicate rows. |

---

## 6. Submit Debounce

### UI-Level Guard (Already Exists)

The `submitting` signal in `QuestionRatingComponent` already prevents double submission at the UI level:

```typescript
protected readonly submitting = signal(false);

// In template:
[disabled]="!allAnswered() || submitting() || waiting()"

// In onSubmit():
if (!this.allAnswered() || this.submitting()) return;
this.submitting.set(true);
```

This is sufficient for normal use. The signal is set to `true` synchronously before any async work begins, so a second tap within the same event loop finds `submitting() === true` and returns early.

### Service-Level Idempotency (New)

For defense-in-depth (e.g., programmatic calls, test scenarios, or signal timing edge cases), make `submitScores()` idempotent:

**New method `hasSubmitted()`**:

```typescript
async hasSubmitted(
  sessionId: string,
  partner: Partner,
): Promise<boolean> {
  const result = await this.sqlite.query<{ cnt: number }>({
    database: DB_NAME,
    statement:
      `SELECT COUNT(*) as cnt FROM checkin_response
       WHERE session_id = ? AND partner = ?;`,
    values: [sessionId, partner],
  });
  return result.values.length > 0 && result.values[0].cnt > 0;
}
```

**Modified `submitScores()`** -- Add idempotency check at the top:

```typescript
async submitScores(
  sessionId: string,
  partner: Partner,
  scores: number[],
): Promise<void> {
  // Idempotency guard: if this partner already submitted, no-op
  const alreadySubmitted = await this.hasSubmitted(sessionId, partner);
  if (alreadySubmitted) {
    return;
  }

  // ... existing write logic unchanged ...
}
```

This makes the method safe to call multiple times with the same arguments. The first call writes. Subsequent calls detect existing rows and return immediately. No duplicate `checkin_response` or `checkin_quality_score` rows.

### Why Not a Database Constraint?

A `UNIQUE(session_id, partner, question_index)` constraint on `checkin_response` would also prevent duplicates, but it would throw an error on duplicate insert instead of silently succeeding. The idempotency guard is friendlier -- callers do not need to catch constraint violation errors.

---

## 7. Empty State

### Detection Logic

**New method `getSessionCount()`** in `CheckinDataService`:

```typescript
async getSessionCount(): Promise<number> {
  const result = await this.sqlite.query<{ cnt: number }>({
    database: DB_NAME,
    statement: `SELECT COUNT(*) as cnt FROM checkin_session;`,
  });
  return result.values.length > 0 ? result.values[0].cnt : 0;
}
```

### CheckinPage Changes

**Extended `PageView` type**:

```typescript
type PageView = 'loading' | 'empty' | 'start' | 'select-partner' | 'rating' | 'waiting';
```

**Modified `ngOnInit()`**:

```typescript
async ngOnInit(): Promise<void> {
  try {
    await this.checkinData.init();
    const session = await this.checkinData.getActiveSession();

    if (session) {
      this.activeSession.set(session);
      if (session.partner_a_submitted === 1 || session.partner_b_submitted === 1) {
        this.view.set('waiting');
      } else {
        this.view.set('select-partner');
      }
    } else {
      // Check if this is the user's very first visit
      const count = await this.checkinData.getSessionCount();
      if (count === 0) {
        this.view.set('empty');
      } else {
        this.view.set('start');
      }
    }
  } catch (e) {
    this.error.set(describeError(e));
    this.view.set('start');
  }
}
```

### Empty State Template

Added to the `@switch (view())` block in `CheckinPage`:

```html
@case ('empty') {
  <div class="pitch empty-state" data-test="checkin-empty-state">
    <h1 class="display title">Your first check-in</h1>
    <p class="sub">
      Ten honest questions. Two perspectives.
      See where you align and where you might not.
    </p>
    <button
      type="button"
      class="cta primary"
      (click)="onStartCheckin()"
      data-test="empty-state-cta"
    >
      Start your first check-in
    </button>
  </div>
}
```

**Design notes**:
- No illustration (per architecture: "illustration-free onboarding card").
- Distinct copy from the returning-user "start" view. "Your first check-in" is warmer than "Relationship Check-In".
- Same CTA behavior -- `onStartCheckin()` transitions to partner selection.
- `data-test="empty-state-cta"` as specified in the architecture.

### Empty State Styling

The `.pitch` class already handles centering and spacing. The `.empty-state` class adds no extra styles in v1 -- the existing layout works. If visual distinction is desired later, the class is a hook.

---

## 8. Polish

### View Transitions in CheckinPage

Add a CSS transition wrapper so view changes feel smooth instead of snapping:

```css
.hero {
  /* Existing styles... */
  animation: fade-up var(--t-in, 200ms) var(--ease-out) both;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero {
    animation: none;
  }
}
```

This applies to every view state in the `@switch` block because they are all inside the `.hero` section. When the view changes, Angular destroys the old DOM and creates new DOM, triggering the animation on the new element.

### data-test Attribute Audit

All interactive elements already have `data-test` attributes from Tasks 1-5. The audit confirms coverage and adds any missing ones:

**CheckinPage** (existing -- verified complete):
- `data-test="checkin-page"` -- page root
- `data-test="checkin-header"` -- header bar
- `data-test="checkin-hero"` -- content area
- `data-test="checkin-loading"` -- loading state
- `data-test="checkin-start"` -- start view
- `data-test="checkin-start-btn"` -- start CTA
- `data-test="checkin-select-partner"` -- partner select view
- `data-test="checkin-partner-buttons"` -- button container
- `data-test="checkin-partner-a"` -- Partner A button
- `data-test="checkin-partner-b"` -- Partner B button
- `data-test="checkin-rating"` -- rating component host
- `data-test="checkin-waiting"` -- inline waiting state
- `data-test="checkin-error"` -- error message

**New data-test attributes for Task 6**:
- `data-test="checkin-empty-state"` -- empty state container
- `data-test="empty-state-cta"` -- first-use CTA button
- `data-test="expired-session-{id}"` -- expired session cards in history
- `data-test="expired-label"` -- "Partner didn't respond" text
- `data-test="waiting-expiry-countdown"` -- countdown timer on waiting screen

**QuestionRatingComponent** (existing -- verified complete):
- `data-test="question-rating"` -- section root
- `data-test="rating-progress"` -- "X / 10 answered"
- `data-test="question-{index}"` -- each question card (0-9)
- `data-test="slider-{index}"` -- each ion-range slider (0-9)
- `data-test="value-{index}"` -- score display per question (0-9)
- `data-test="submitting-status"` -- submitting text
- `data-test="waiting-status"` -- waiting text
- `data-test="submit-scores"` -- submit button

**New data-test attributes for draft persistence**:
- `data-test="draft-restored"` -- visible only when drafts were loaded, shows "Restored X answers" label

**CheckinWaitingComponent** (existing -- verified complete):
- `data-test="checkin-waiting-page"` -- page root
- `data-test="waiting-header"` -- header bar
- `data-test="waiting-hero"` -- content area
- `data-test="waiting-lock-icon"` -- lock SVG
- `data-test="waiting-title"` -- title
- `data-test="waiting-message"` -- privacy message
- `data-test="waiting-timestamp"` -- session start time
- `data-test="waiting-error"` -- error message
- `data-test="waiting-back-btn"` -- back button

**New data-test attribute**:
- `data-test="waiting-expiry-countdown"` -- "Expires in X hours" label

### Waiting Screen Expiry Countdown

Add a computed signal to `CheckinWaitingComponent` that shows time remaining:

```typescript
protected readonly expiryLabel = computed<string | null>(() => {
  const ts = this.sessionCreatedAt();
  if (!ts) return null;
  const expiresAt = new Date(ts).getTime() + SESSION_EXPIRY_MS;
  const remaining = expiresAt - Date.now();
  if (remaining <= 0) return 'Session expired';
  const hours = Math.floor(remaining / (60 * 60 * 1000));
  const minutes = Math.floor((remaining % (60 * 60 * 1000)) / (60 * 1000));
  if (hours > 0) return `Expires in ${hours}h ${minutes}m`;
  return `Expires in ${minutes}m`;
});
```

This is a static computation -- it does not live-update. It shows the approximate time remaining when the page loads. The polling loop already checks `bothSubmitted()` every 3 seconds. If the session expires while on this screen, `getActiveSession()` on the next `/checkin` visit will detect it.

Template addition (after the timestamp):

```html
@if (expiryLabel(); as label) {
  <p class="expiry-countdown" data-test="waiting-expiry-countdown">
    {{ label }}
  </p>
}
```

Styled with `--text-muted`, `font-size: 13px`, matching the timestamp style.

### Keyboard Accessibility

All buttons already use `<button type="button">` which is keyboard-focusable by default. The `ion-range` sliders are natively keyboard-accessible via Ionic. No additional `tabindex` or `role` attributes are needed.

The `@switch` block in `CheckinPage` uses `aria-busy="true"` on the loading state. Add `role="status"` to the waiting and error elements for screen reader announcements.

### Reduced Motion

All existing components already have `@media (prefers-reduced-motion: reduce)` blocks that disable transitions and animations. The new fade-up animation in CheckinPage also respects this. Verify that the `QuestionRatingComponent` already has this (it does -- line 239-244 in the existing code).

---

## 9. Tests

Framework: Jasmine + Karma. Component tests use `TestBed` with standalone imports. Mock `CheckinDataService` with `jasmine.createSpyObj`. Same patterns as existing specs.

### 9.1 `checkin-data.service.spec.ts` -- Additions (14 new tests)

**Expiry tests**:

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `getActiveSession_staleOneSubmitted_expiresAndReturnsNull` | Session created >48h ago with `partner_a_submitted=1`, `partner_b_submitted=0`. Returns `null`. Execute called with `status = 'expired'`. |
| 2 | `getActiveSession_staleNeitherSubmitted_expiresAndReturnsNull` | Session created >48h ago with both flags 0. Returns `null`. Execute called with `status = 'expired'`. |
| 3 | `getActiveSession_freshOneSubmitted_returnsSession` | Session created 1h ago with one partner submitted. Returns the session. No expiry update. |
| 4 | `getActiveSession_staleBothSubmitted_neverReached` | Both-submitted sessions are `complete`, not `active`. This scenario should not occur. If it did (data corruption), the session would still be returned since both submitted means it is not stale in the single-partner sense. Test that the session is returned as-is. |
| 5 | `getActiveSession_exactly48h_doesNotExpire` | Session created exactly 48h ago. `>` not `>=`. Returns session. |

**Draft tests**:

| # | Test name | Assertion |
|---|-----------|-----------|
| 6 | `saveDraft_insertsOrReplacesRow` | Execute called with `INSERT OR REPLACE INTO checkin_draft` and correct values. |
| 7 | `loadDraft_returnsDraftRows` | Query returns draft rows. Method returns them. |
| 8 | `loadDraft_noDrafts_returnsEmptyArray` | Query returns `[]`. Method returns `[]`. |
| 9 | `deleteDraft_deletesRowsForSessionAndPartner` | Execute called with `DELETE FROM checkin_draft WHERE session_id = ? AND partner = ?`. |

**Idempotency tests**:

| # | Test name | Assertion |
|---|-----------|-----------|
| 10 | `hasSubmitted_rowsExist_returnsTrue` | Query returns `{ cnt: 5 }`. Method returns `true`. |
| 11 | `hasSubmitted_noRows_returnsFalse` | Query returns `{ cnt: 0 }`. Method returns `false`. |
| 12 | `submitScores_alreadySubmitted_isNoop` | `hasSubmitted` returns `true`. No INSERT calls to `checkin_response` or `checkin_quality_score`. |

**Count + expired session tests**:

| # | Test name | Assertion |
|---|-----------|-----------|
| 13 | `getSessionCount_returnsCount` | Query returns `{ cnt: 3 }`. Method returns `3`. |
| 14 | `getExpiredSessions_returnsExpiredRows` | Query returns expired sessions. Method returns them in order. |

### 9.2 `question-rating.component.spec.ts` -- New file (10 tests)

```typescript
// Test host to supply required inputs
@Component({
  standalone: true,
  imports: [QuestionRatingComponent],
  template: `
    <app-question-rating
      [sessionId]="sessionId()"
      [partner]="partner()"
      (submitted)="onSubmitted($event)"
    />
  `,
})
class TestHostComponent {
  readonly sessionId = signal('sess-1');
  readonly partner = signal<Partner>('A');
  submittedEvent: { bothDone: boolean } | null = null;
  onSubmitted(event: { bothDone: boolean }) {
    this.submittedEvent = event;
  }
}
```

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_questionRatingSection` | `data-test="question-rating"` present. |
| 2 | `renders_allTenQuestions` | 10 elements matching `[data-test^="question-"]`. |
| 3 | `renders_submitButton_disabledByDefault` | `data-test="submit-scores"` has `disabled` attribute. |
| 4 | `renders_progressCounter` | `data-test="rating-progress"` contains "0 / 10 answered". |
| 5 | `loadsDraft_onInit_restoresScores` | `loadDraft` returns 3 drafts. After init, `data-test="rating-progress"` shows "3 / 10 answered". |
| 6 | `loadsDraft_showsRestoredLabel` | When drafts loaded, `data-test="draft-restored"` visible with "Restored 3 answers". |
| 7 | `onSliderChange_callsSaveDraft` | Trigger slider change event on Q5. `saveDraft` spy called with `('sess-1', 'A', 5, value)`. |
| 8 | `onSubmit_callsDeleteDraft` | After submit, `deleteDraft` spy called with `('sess-1', 'A')`. |
| 9 | `onSubmit_alreadySubmitting_isNoop` | Set `submitting` to `true`. Call `onSubmit()`. `submitScores` not called. |
| 10 | `onSubmit_bothDone_emitsSubmittedEvent` | `bothSubmitted` returns `true`. Host receives `{ bothDone: true }`. |

### 9.3 `checkin.page.spec.ts` -- Additions (8 new tests)

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `emptyState_zeroSessions_showsEmptyView` | `getSessionCount` returns 0. `data-test="checkin-empty-state"` present. |
| 2 | `emptyState_showsFirstUseCTA` | `data-test="empty-state-cta"` contains "Start your first check-in". |
| 3 | `emptyState_ctaClick_showsPartnerSelection` | Click `data-test="empty-state-cta"`. Partner select view appears. |
| 4 | `startState_sessionsExist_showsStartView` | `getSessionCount` returns 3. `data-test="checkin-start"` present (not empty state). |
| 5 | `expiredSession_detected_showsStartView` | `getActiveSession` returns `null` (it expired internally). `getSessionCount` returns 1. Start view shown. |
| 6 | `expiredSessions_displayedInHistory` | `getExpiredSessions` returns 2 expired sessions. Both `data-test="expired-session-{id}"` elements present. |
| 7 | `expiredSession_showsPartnerDidntRespondLabel` | `data-test="expired-label"` contains "Partner didn't respond". |
| 8 | `viewTransition_heroHasFadeAnimation` | `.hero` element has CSS animation applied (or verify the class exists). |

### 9.4 `checkin-waiting.component.spec.ts` -- Additions (2 new tests)

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `showsExpiryCountdown` | Session created 24h ago. `data-test="waiting-expiry-countdown"` contains "Expires in 24h". |
| 2 | `expiryCountdown_notShown_whenNoSession` | No session loaded. `data-test="waiting-expiry-countdown"` absent. |

### Test Count Summary

| Spec file | Existing | New | Total |
|-----------|----------|-----|-------|
| `checkin-data.service.spec.ts` | 20 | 14 | 34 |
| `question-rating.component.spec.ts` | 0 | 10 | 10 |
| `checkin.page.spec.ts` | 12 | 8 | 20 |
| `checkin-waiting.component.spec.ts` | 14 | 2 | 16 |
| **Total** | **46** | **34** | **80** |

---

## 10. Out of Scope

This section explicitly lists what Task 6 does NOT do.

| Item | Reason |
|------|--------|
| Multi-device sync / push notifications for partner | Epic scope is single-device, local SQLite only. Push to notify the other partner is a separate epic. |
| Configurable expiry duration | Hardcoded at 48h. No settings UI. If 48h proves wrong, change the constant. |
| Expired session data cleanup (DELETE rows) | Expired sessions keep their response data in SQLite. Deletion would save disk space but loses forensic value. The data volume is tiny (10 rows per submission). |
| Orphaned draft cleanup for expired sessions | Draft rows for expired sessions persist harmlessly. They are never loaded (the session is no longer active). A `DELETE FROM checkin_draft WHERE session_id IN (SELECT id FROM checkin_session WHERE status = 'expired')` could run periodically but is not needed for v1. |
| Session history list / "View all past sessions" | The epic does not include a full session browser. Expired sessions are shown as a small informational list on the start view. Completed sessions are accessible via trends. |
| Undo / re-rate after submit | Architecture decision: submissions are immutable. No edit capability. |
| Offline queue / conflict resolution | All data is local SQLite. There is no remote server to conflict with. |
| Animated view transitions (shared element, slide) | The fade-up animation is sufficient polish. Shared-element transitions between partner-select and rating would be nice but are out of scope for 0.5 days. |
| Onboarding illustration / animation | Empty state is text-only per the architecture spec. |
| E2E / integration tests | Unit tests only. E2E belongs to a separate testing effort. |
| Performance optimization of draft writes | `saveDraft()` is fire-and-forget on each slider change. For 10 questions, this is 10 writes max. No batching or throttling needed. |
| Draft expiry (auto-delete old drafts) | Drafts are orphaned when sessions expire. Harmless. Not worth the complexity of a cleanup job. |
| History pagination | Expired sessions list shows up to 10 most recent. No infinite scroll or "Load more". |
| Accessibility: full data table alternative for sparklines | Deferred from Task 5. Still deferred. VoiceOver `aria-label` is the accessibility story for v1. |
