# Task 4: Submission Lock + Results Comparison View

**Purpose**: Enforce privacy until both partners submit, then reveal a side-by-side comparison of four quality scores. This task builds two components: a waiting screen that locks results until the session completes, and a results screen that displays quality cards color-coded by threshold with divergence highlighting. The waiting screen polls local SQLite for session completion and auto-navigates to results. The results screen is the payoff moment -- the first time either partner sees how their perception compares.

**Effort**: 1 day

**Dependencies**:
- Task 1 (SQLite schema + data service) -- `CheckinDataService` at `/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts` with `getSession()`, `getScoresForSession()`, `bothSubmitted()`.
- Task 2 (Partner selection + session creation) -- `CheckinPage` at `/projects/bubls/src/app/pages/checkin/checkin.page.ts` with session creation flow, route at `/checkin`.
- Task 3 (Question rating interface) -- `QuestionRatingComponent` at `/projects/bubls/src/app/features/checkin/components/question-rating.component.ts` with `submitted` output emitting `{ bothDone: boolean }`.

**Blocks**: Task 5 (Trend Lines + Divergence Alerts) -- the "View Trends" button in the results screen navigates to the trends route that Task 5 builds. Task 6 (Session Expiry) -- adds 48h auto-expiry to sessions stuck in the waiting state built here.

**Related**:
- [Solution Architecture -- Task 4 Component Design](./architecture.md)
- [Epic -- Task 4 Details](./epic.md)

---

## 1. Objective

Deliver two new components and the data/navigation glue that connects them to the existing check-in flow:

1. **`checkin-waiting.component.ts`** -- Shown after one partner submits. Displays a lock icon, "Waiting for [Partner Name]" message, and the session timestamp. No scores visible. Polls `CheckinDataService.getSession()` on interval. When `status === 'complete'`, auto-navigates to results.

2. **`checkin-results.component.ts`** -- Shown after both partners submit. Displays four quality cards vertically (Communication Honesty, Mutual Respect, Prioritization, Long-term Viability). Each card shows Partner A score (left), Partner B score (right), and a delta badge (center). Cards are color-coded: green (score >= 7), amber (5 <= score < 7), red (score < 5). Divergence (delta >= 3) gets a pulsing border. Footer has "View Trends" and "New Check-In" buttons.

3. **Privacy enforcement** -- `getSessionResults()` method added to `CheckinDataService` returns quality scores only when session `status === 'complete'`. All UI paths guard against showing scores for incomplete sessions.

4. **Navigation wiring** -- `CheckinPage` gains two new view states (`waiting` and `results`) and transitions between them based on session status. The `QuestionRatingComponent.submitted` output drives the transition from rating to waiting or results.

---

## 2. Inputs

Every file referenced below exists and is shipped from Tasks 1-3.

### Model (`/projects/bubls/src/app/features/checkin/checkin.model.ts`)

```typescript
export type Partner = 'A' | 'B';
export type SessionStatus = 'active' | 'complete' | 'expired';
export type QualityKey = 'communication' | 'respect' | 'prioritization' | 'viability';

export interface QualityDefinition {
  readonly key: QualityKey;
  readonly label: string;
  readonly questionIndices: readonly number[];
}

export const QUALITY_DEFINITIONS: readonly QualityDefinition[] = [
  { key: 'communication', label: 'Communication Honesty', questionIndices: [0, 6, 7] },
  { key: 'respect', label: 'Mutual Respect', questionIndices: [1, 2, 3] },
  { key: 'prioritization', label: 'Prioritization', questionIndices: [4, 5, 8] },
  { key: 'viability', label: 'Long-term Viability', questionIndices: [2, 7, 9] },
];

export const THRESHOLD_HEALTHY = 7;
export const THRESHOLD_CONCERNING = 5;
export const DIVERGENCE_DELTA = 3;

export interface CheckinSession {
  id: string;
  created_at: string;
  status: SessionStatus;
  partner_a_submitted: number; // 0 | 1
  partner_b_submitted: number; // 0 | 1
}

export interface CheckinQualityScore {
  id: string;
  session_id: string;
  partner: Partner;
  quality_key: QualityKey;
  score: number;
}
```

### Data Service (`/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts`)

Existing public API consumed by this task:

| Method | Signature | Returns |
|--------|-----------|---------|
| `init()` | `async init(): Promise<void>` | Registers migration, warms DB. Idempotent. |
| `getSession(id)` | `async getSession(id: string): Promise<CheckinSession \| null>` | Single session by ID, or null. |
| `getActiveSession()` | `async getActiveSession(): Promise<CheckinSession \| null>` | Most recent active session, or null. |
| `bothSubmitted(sessionId)` | `async bothSubmitted(sessionId: string): Promise<boolean>` | True when both partners submitted. |
| `getScoresForSession(sessionId)` | `async getScoresForSession(sessionId: string): Promise<CheckinQualityScore[]>` | All quality scores (both partners, all four qualities). |

New method to add:

| Method | Signature | Returns |
|--------|-----------|---------|
| `getSessionResults(sessionId)` | `async getSessionResults(sessionId: string): Promise<CheckinQualityScore[] \| null>` | Quality scores only if session `status === 'complete'`. Returns `null` otherwise. Privacy guard. |

### CheckinPage (`/projects/bubls/src/app/pages/checkin/checkin.page.ts`)

Current view states: `'loading' | 'start' | 'select-partner' | 'session-created' | 'waiting'`

Signals:
- `view: WritableSignal<PageView>` -- controls which screen is shown
- `selectedPartner: WritableSignal<Partner | null>` -- current partner identity
- `activeSession: WritableSignal<CheckinSession | null>` -- current session
- `error: WritableSignal<string | null>` -- error message display

The existing `'waiting'` view is a bare placeholder ("You've already submitted for this session. Waiting for your partner to finish."). This task replaces it with the full `CheckinWaitingComponent`.

### QuestionRatingComponent (`/projects/bubls/src/app/features/checkin/components/question-rating.component.ts`)

- Input: `sessionId: InputSignal<string>` (required)
- Input: `partner: InputSignal<Partner>` (required)
- Output: `submitted: OutputEmitterRef<{ bothDone: boolean }>`

After submission, emits `{ bothDone: true }` if both partners done (navigate to results) or `{ bothDone: false }` if only one partner done (navigate to waiting).

### Barrel Exports (`/projects/bubls/src/app/features/checkin/index.ts`)

Currently exports: `CheckinDataService`, `QuestionRatingComponent`, all model types and constants including `THRESHOLD_HEALTHY`, `THRESHOLD_CONCERNING`, `DIVERGENCE_DELTA`, `QUALITY_DEFINITIONS`.

### Design Tokens (`/projects/bubls/src/app/styles/tokens.scss`)

Relevant tokens for this task:

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--success` | `#146E37` | `#2DD36F` | Green threshold (score >= 7) |
| `--danger` | `#C93B3B` | `#EB445A` | Red threshold (score < 5) |
| `--accent-warm` | `#A6510A` | `#E8A85C` | CTA buttons, accents |
| `--accent-cool` | `#5B6CC0` | `#818CF8` | Waiting state accent |
| `--surface` | `#FFFFFF` | `#141414` | Card backgrounds |
| `--surface-elevated` | `#FFFFFF` | `#1C1C1E` | Elevated card surface |
| `--hairline` | `rgba(26,26,26,0.12)` | `rgba(245,245,245,0.10)` | Borders, dividers |
| `--text-primary` | `#1A1A1A` | `#F5F5F5` | Primary text |
| `--text-secondary` | `rgba(26,26,26,0.62)` | `rgba(245,245,245,0.60)` | Secondary labels |
| `--text-muted` | `rgba(26,26,26,0.42)` | `rgba(245,245,245,0.40)` | Eyebrow, muted text |
| `--font-display` | Cormorant Garamond | -- | Quality labels, headings |
| `--font-body` | Instrument Sans | -- | Scores, deltas, buttons |
| `--r-md` | `16px` | -- | Card border radius |
| `--r-pill` | `999px` | -- | Button border radius |
| `--shadow-soft` | subtle box-shadow | darker box-shadow | Card elevation |

No amber token exists in the design system. This task introduces `--threshold-amber` as a local CSS custom property scoped to the results component.

### Routes (`/projects/bubls/src/app/app.routes.ts`)

Current `/checkin` route:
```typescript
{
  path: 'checkin',
  loadComponent: () =>
    import('./pages/checkin/checkin.page').then(
      (m) => m.CheckinPage,
    ),
},
```

This is a flat route that loads `CheckinPage` directly. The page manages its own view states internally via signals rather than child routes. This task continues that pattern -- the waiting and results views are internal states of `CheckinPage`, not separate routes.

---

## 3. Outputs

### Files to Create

| File | Purpose |
|------|---------|
| `src/app/features/checkin/components/checkin-waiting.component.ts` | Lock screen shown while waiting for partner. Displays lock icon, partner name, session timestamp. Polls session status. Auto-navigates on completion. |
| `src/app/features/checkin/components/checkin-waiting.component.spec.ts` | Unit tests for waiting component: rendering, polling, auto-transition, cleanup. |
| `src/app/features/checkin/components/checkin-results.component.ts` | Results comparison view. Four quality cards with scores, deltas, color-coding, divergence highlighting. Footer with action buttons. |
| `src/app/features/checkin/components/checkin-results.component.spec.ts` | Unit tests for results component: card rendering, color classes, delta calculations, divergence treatment, button actions. |

### Files to Modify

| File | Change |
|------|--------|
| `src/app/features/checkin/services/checkin-data.service.ts` | Add `getSessionResults(sessionId)` privacy-guard method. |
| `src/app/features/checkin/services/checkin-data.service.spec.ts` | Add tests for `getSessionResults()`. |
| `src/app/pages/checkin/checkin.page.ts` | Add `'rating' \| 'results'` to `PageView` union. Import and render `CheckinWaitingComponent`, `CheckinResultsComponent`, `QuestionRatingComponent`. Wire `submitted` output to view transitions. |
| `src/app/pages/checkin/checkin.page.spec.ts` | Add tests for new view states, transitions, and component rendering. |
| `src/app/features/checkin/index.ts` | Add barrel exports for `CheckinWaitingComponent` and `CheckinResultsComponent`. |

### Files to Leave Alone

| File | Reason |
|------|--------|
| `src/app/features/checkin/checkin.model.ts` | All types and constants needed (`QUALITY_DEFINITIONS`, `THRESHOLD_HEALTHY`, etc.) already exist. No changes. |
| `src/app/features/checkin/components/question-rating.component.ts` | Consumed as-is. The `submitted` output provides the handoff signal. No changes. |
| `src/app/features/checkin/components/question-rating.component.spec.ts` | Task 3 tests. No changes. |
| `src/app/app.routes.ts` | Route stays as a flat `/checkin` -> `CheckinPage`. No child routes needed. |
| `src/app/shell/feature-registry.ts` | Already has the checkin tab entry. No changes. |
| `src/app/styles/tokens.scss` | Threshold colors use existing `--success` and `--danger` tokens plus a locally scoped amber variable. No global token changes. |
| `src/app/shared/sqlite/` | Consumed transitively through `CheckinDataService`. No changes. |

---

## 4. Component Design

### 4.1 CheckinWaitingComponent

**File**: `src/app/features/checkin/components/checkin-waiting.component.ts`

**Selector**: `app-checkin-waiting`

**Inputs**:
- `sessionId: InputSignal<string>` (required) -- the active session to poll
- `waitingForPartner: InputSignal<Partner>` (required) -- the partner who has NOT yet submitted (`'A'` or `'B'`). Used to display "Waiting for Partner A" or "Waiting for Partner B".
- `sessionCreatedAt: InputSignal<string>` (required) -- ISO timestamp for display

**Outputs**:
- `bothDone: OutputEmitterRef<void>` -- emitted when polling detects `status === 'complete'`. Parent navigates to results view.

**Template Structure**:
```
<section class="waiting" data-test="checkin-waiting-view">
  <div class="waiting__icon" data-test="waiting-lock-icon">
    [lock-closed SVG inline]
  </div>
  <h2 class="waiting__title" data-test="waiting-title">
    Waiting for Partner {{ waitingForPartner() }}
  </h2>
  <p class="waiting__sub" data-test="waiting-subtitle">
    Scores are locked until both partners submit.
  </p>
  <p class="waiting__timestamp" data-test="waiting-timestamp">
    Session started {{ formattedTime() }}
  </p>
  <div class="waiting__pulse" data-test="waiting-pulse" aria-hidden="true"></div>
</section>
```

**Signals**:
- `formattedTime: Signal<string>` -- computed from `sessionCreatedAt`, formatted as "Apr 19 at 3:42 PM" using `Intl.DateTimeFormat`.

**Lifecycle**:
- `ngOnInit`: Start a `setInterval` polling loop. Every 3 seconds, call `CheckinDataService.getSession(sessionId())`. If `session.status === 'complete'`, emit `bothDone` and clear the interval.
- `ngOnDestroy`: Clear the interval. Critical to prevent memory leaks and stale polling after navigation.

**Polling interval**: 3 seconds. Fast enough to feel responsive when the second partner submits on the same device. No network cost since all queries hit local SQLite.

**Accessibility**: `aria-live="polite"` on the title so screen readers announce changes. Lock icon is decorative (`aria-hidden="true"`).

**Styling (inline)**:
- `:host` sets `--world-bg: var(--page-bg)`, uses `--accent-cool` for the lock icon tint.
- `.waiting` is centered vertically (`min-height: 50vh`, flexbox column, `align-items: center`, `justify-content: center`).
- `.waiting__icon` renders a 64x64 lock icon using `--accent-cool` stroke color.
- `.waiting__title` uses `--font-display`, 28px, `--text-primary`.
- `.waiting__sub` uses `--font-body`, 16px, `--text-secondary`.
- `.waiting__pulse` is a decorative pulsing circle using `@keyframes` (opacity 0.2 -> 0.6 -> 0.2 on a 2s loop) in `--accent-cool`. Respects `prefers-reduced-motion: reduce` by stopping animation.

### 4.2 CheckinResultsComponent

**File**: `src/app/features/checkin/components/checkin-results.component.ts`

**Selector**: `app-checkin-results`

**Inputs**:
- `sessionId: InputSignal<string>` (required) -- the completed session to display

**Outputs**:
- `viewTrends: OutputEmitterRef<void>` -- emitted when "View Trends" tapped. Parent navigates (Task 5 will build the destination).
- `newCheckin: OutputEmitterRef<void>` -- emitted when "New Check-In" tapped. Parent resets to start state.

**Internal interface** (defined in component file, not exported):

```typescript
interface QualityCardData {
  key: QualityKey;
  label: string;
  scoreA: number;
  scoreB: number;
  delta: number;
  colorClass: 'green' | 'amber' | 'red';
  isDivergent: boolean;
}
```

**Signals**:
- `qualityCards: WritableSignal<QualityCardData[]>` -- populated in `ngOnInit` by fetching scores from `CheckinDataService.getSessionResults(sessionId())`. Mapped from raw `CheckinQualityScore[]` into `QualityCardData[]`.
- `loading: WritableSignal<boolean>` -- true during initial data fetch.
- `error: WritableSignal<string | null>` -- set if `getSessionResults()` returns null (privacy guard) or throws.

**Template Structure**:
```
<section class="results" data-test="checkin-results-view">
  <header class="results__header">
    <h2 class="results__title" data-test="results-title">Your Results</h2>
    <p class="results__sub" data-test="results-subtitle">
      How you each experienced this check-in.
    </p>
  </header>

  @if (loading()) {
    <div class="results__loading" data-test="results-loading" aria-busy="true">
      <p>Loading results...</p>
    </div>
  } @else if (error(); as msg) {
    <div class="results__error" data-test="results-error" role="alert">
      <p>{{ msg }}</p>
    </div>
  } @else {
    <div class="results__cards" data-test="results-cards">
      @for (card of qualityCards(); track card.key) {
        <div
          class="quality-card"
          [class.quality-card--green]="card.colorClass === 'green'"
          [class.quality-card--amber]="card.colorClass === 'amber'"
          [class.quality-card--red]="card.colorClass === 'red'"
          [class.quality-card--divergent]="card.isDivergent"
          [attr.data-test]="'quality-card-' + card.key"
        >
          <span class="quality-card__label" [attr.data-test]="'quality-label-' + card.key">
            {{ card.label }}
          </span>
          <div class="quality-card__scores">
            <div class="quality-card__partner" data-test="score-partner-a">
              <span class="quality-card__partner-label">A</span>
              <span class="quality-card__score">{{ card.scoreA | number:'1.1-1' }}</span>
            </div>
            <div
              class="quality-card__delta"
              [class.quality-card__delta--divergent]="card.isDivergent"
              [attr.data-test]="'delta-' + card.key"
            >
              <span class="quality-card__delta-value">{{ card.delta | number:'1.1-1' }}</span>
              <span class="quality-card__delta-label">delta</span>
            </div>
            <div class="quality-card__partner" data-test="score-partner-b">
              <span class="quality-card__partner-label">B</span>
              <span class="quality-card__score">{{ card.scoreB | number:'1.1-1' }}</span>
            </div>
          </div>
        </div>
      }
    </div>

    <footer class="results__footer" data-test="results-footer">
      <button
        type="button"
        class="results__cta results__cta--trends"
        data-test="view-trends-btn"
        (click)="onViewTrends()"
      >
        View Trends
      </button>
      <button
        type="button"
        class="results__cta results__cta--new"
        data-test="new-checkin-btn"
        (click)="onNewCheckin()"
      >
        New Check-In
      </button>
    </footer>
  }
</section>
```

**Lifecycle**:
- `ngOnInit`: Set `loading(true)`. Call `CheckinDataService.getSessionResults(sessionId())`. If null, set error "Results not available yet." If successful, map raw scores to `QualityCardData[]` using the mapping logic below. Set `loading(false)`.

**Score-to-card mapping logic**:
```typescript
private mapScoresToCards(scores: CheckinQualityScore[]): QualityCardData[] {
  return QUALITY_DEFINITIONS.map((def) => {
    const scoreA = scores.find(
      (s) => s.quality_key === def.key && s.partner === 'A',
    )?.score ?? 0;
    const scoreB = scores.find(
      (s) => s.quality_key === def.key && s.partner === 'B',
    )?.score ?? 0;
    const avg = (scoreA + scoreB) / 2;
    const delta = Math.abs(scoreA - scoreB);

    return {
      key: def.key,
      label: def.label,
      scoreA,
      scoreB,
      delta,
      colorClass: this.getColorClass(avg),
      isDivergent: delta >= DIVERGENCE_DELTA,
    };
  });
}

private getColorClass(avg: number): 'green' | 'amber' | 'red' {
  if (avg >= THRESHOLD_HEALTHY) return 'green';
  if (avg >= THRESHOLD_CONCERNING) return 'amber';
  return 'red';
}
```

The color class is determined by the **average** of both partners' scores for that quality. This is the combined health signal. Individual scores may differ, but the card color represents the relationship-level assessment.

**Methods**:
- `onViewTrends(): void` -- emits `viewTrends`. No navigation logic in this component; parent handles routing.
- `onNewCheckin(): void` -- emits `newCheckin`. Parent resets session state and returns to start view.

**Pipes**: Uses Angular's built-in `DecimalPipe` (`number:'1.1-1'`) for one-decimal formatting. Import `DecimalPipe` from `@angular/common`.

### 4.3 CheckinPage Modifications

**File**: `/projects/bubls/src/app/pages/checkin/checkin.page.ts`

**View state expansion**:

Current: `type PageView = 'loading' | 'start' | 'select-partner' | 'session-created' | 'waiting';`

New: `type PageView = 'loading' | 'start' | 'select-partner' | 'rating' | 'waiting' | 'results';`

- Remove `'session-created'` (replaced by `'rating'` which renders `QuestionRatingComponent`)
- Add `'rating'` (renders `QuestionRatingComponent` with session and partner inputs)
- Change `'waiting'` (currently a bare placeholder; now renders `CheckinWaitingComponent`)
- Add `'results'` (renders `CheckinResultsComponent`)

**New imports**:
```typescript
import { QuestionRatingComponent } from '../../features/checkin/components/question-rating.component';
import { CheckinWaitingComponent } from '../../features/checkin/components/checkin-waiting.component';
import { CheckinResultsComponent } from '../../features/checkin/components/checkin-results.component';
```

**New computed signals**:
```typescript
/** The partner who has NOT submitted -- displayed in the waiting component. */
protected readonly waitingForPartner = computed<Partner>(() => {
  const session = this.activeSession();
  if (!session) return 'B';
  if (session.partner_a_submitted === 1 && session.partner_b_submitted === 0) return 'B';
  if (session.partner_b_submitted === 1 && session.partner_a_submitted === 0) return 'A';
  return 'B'; // fallback
});
```

**Template additions** (inside the `@switch (view())` block):

```html
@case ('rating') {
  <app-question-rating
    [sessionId]="activeSession()!.id"
    [partner]="selectedPartner()!"
    (submitted)="onRatingSubmitted($event)"
    data-test="checkin-rating"
  />
}

@case ('waiting') {
  <app-checkin-waiting
    [sessionId]="activeSession()!.id"
    [waitingForPartner]="waitingForPartner()"
    [sessionCreatedAt]="activeSession()!.created_at"
    (bothDone)="onBothDone()"
    data-test="checkin-waiting-component"
  />
}

@case ('results') {
  <app-checkin-results
    [sessionId]="activeSession()!.id"
    (viewTrends)="onViewTrends()"
    (newCheckin)="onNewCheckin()"
    data-test="checkin-results-component"
  />
}
```

**New methods**:

```typescript
/** Called when QuestionRatingComponent emits `submitted`. */
onRatingSubmitted(event: { bothDone: boolean }): void {
  if (event.bothDone) {
    this.view.set('results');
  } else {
    this.view.set('waiting');
  }
}

/** Called when CheckinWaitingComponent detects both partners done. */
async onBothDone(): Promise<void> {
  // Refresh session data to get complete status
  const session = this.activeSession();
  if (session) {
    const refreshed = await this.checkinData.getSession(session.id);
    this.activeSession.set(refreshed);
  }
  this.view.set('results');
}

/** Navigate to trends (Task 5 placeholder). */
onViewTrends(): void {
  // Task 5 will implement trends. For now, no-op.
}

/** Reset to start a new check-in. */
onNewCheckin(): void {
  this.activeSession.set(null);
  this.selectedPartner.set(null);
  this.error.set(null);
  this.view.set('start');
}
```

**Modify `onSelectPartner`**: Change the current terminal state from `'session-created'` to `'rating'`:

Current:
```typescript
this.view.set('session-created');
```

New:
```typescript
this.view.set('rating');
```

**Modify `ngOnInit`**: When resuming an active session where both partners have submitted, go directly to results. When resuming with one submitted, detect which partner submitted and show waiting:

Current logic:
```typescript
if (session.partner_a_submitted === 1 || session.partner_b_submitted === 1) {
  this.view.set('waiting');
}
```

New logic:
```typescript
if (session.partner_a_submitted === 1 && session.partner_b_submitted === 1) {
  // Both done -- show results
  this.view.set('results');
} else if (session.partner_a_submitted === 1 || session.partner_b_submitted === 1) {
  // One done -- show waiting
  this.view.set('waiting');
}
```

Also handle complete session status on resume:
```typescript
if (session.status === 'complete') {
  this.activeSession.set(session);
  this.view.set('results');
  return;
}
```

---

## 5. Data Flow

```
                       CheckinPage (orchestrator)
                             |
          ┌──────────────────┼──────────────────────┐
          |                  |                       |
   QuestionRating     CheckinWaiting          CheckinResults
   [rating view]      [waiting view]          [results view]
          |                  |                       |
          | submitted({      | polls getSession()   | calls getSessionResults()
          |   bothDone       |    every 3s           |    on init
          | })               |                       |
          v                  v                       v
     CheckinDataService.submitScores()     CheckinDataService
     CheckinDataService.bothSubmitted()    .getSessionResults()
          |                  |                       |
          v                  v                       v
       SQLite             SQLite                  SQLite
    checkin_response   checkin_session        checkin_quality_score
    checkin_quality_score                     + checkin_session
    checkin_session                           (status check)
```

**Sequence -- happy path (both partners, same device)**:

1. Partner A selects identity -> `CheckinPage.onSelectPartner('A')` -> creates session -> `view.set('rating')`
2. Partner A rates 10 questions -> submits -> `QuestionRatingComponent.submitted.emit({ bothDone: false })`
3. `CheckinPage.onRatingSubmitted({ bothDone: false })` -> `view.set('waiting')`
4. `CheckinWaitingComponent` starts polling `getSession()` every 3s
5. Device is handed to Partner B -> Partner B taps "I'm Partner B" on a fresh page load or... (edge case: partner B would need to navigate back. See note below.)
6. **Alternative**: since this is a same-device flow, Partner B would restart the `/checkin` route. `ngOnInit` detects `partner_a_submitted === 1`, shows `'select-partner'` state so Partner B can identify themselves and enter rating.

Wait -- the current `ngOnInit` shows `'waiting'` when one partner has submitted. This needs refinement. When one partner has submitted and the OTHER partner arrives, they need to be able to select their identity and rate. The waiting view should only appear to the partner who already submitted.

**Revised `ngOnInit` logic**: The page cannot know which partner is currently using the device (partner identity is not persisted). So when resuming with one partner submitted:
- Show `'select-partner'` state (not `'waiting'`), letting the arriving partner identify themselves.
- If the arriving partner selects the one that already submitted, show them `'waiting'`.
- If the arriving partner selects the one that hasn't submitted, show them `'rating'`.

This changes the `onSelectPartner` method:

```typescript
async onSelectPartner(partner: Partner): Promise<void> {
  this.error.set(null);
  this.selectedPartner.set(partner);

  try {
    let session = this.activeSession();
    if (!session) {
      const sessionId = await this.checkinData.createSession();
      session = await this.checkinData.getSession(sessionId);
      this.activeSession.set(session);
    }

    if (!session) {
      this.error.set('Failed to create session.');
      this.view.set('select-partner');
      return;
    }

    // Check if this partner already submitted
    const alreadySubmitted =
      (partner === 'A' && session.partner_a_submitted === 1) ||
      (partner === 'B' && session.partner_b_submitted === 1);

    if (session.status === 'complete') {
      this.view.set('results');
    } else if (alreadySubmitted) {
      this.view.set('waiting');
    } else {
      this.view.set('rating');
    }
  } catch (e) {
    this.error.set(describeError(e));
    this.view.set('select-partner');
  }
}
```

And the `ngOnInit` resume logic:

```typescript
if (session.status === 'complete') {
  this.activeSession.set(session);
  this.view.set('results');
} else if (session.partner_a_submitted === 1 || session.partner_b_submitted === 1) {
  // One partner submitted -- let the other identify themselves
  this.activeSession.set(session);
  this.view.set('select-partner');
} else {
  // Active session, nobody submitted
  this.view.set('select-partner');
}
```

---

## 6. Privacy & Lock Logic

The submission lock state machine, as defined in the architecture:

```
Session status = 'active'
├── partner_a_submitted = 0, partner_b_submitted = 0
│   → Both can rate. Select partner → rating view.
│
├── partner_a_submitted = 1, partner_b_submitted = 0
│   → Partner A sees waiting. Partner B can rate.
│   → No scores visible to either partner.
│
├── partner_a_submitted = 0, partner_b_submitted = 1
│   → Partner B sees waiting. Partner A can rate.
│   → No scores visible to either partner.
│
└── partner_a_submitted = 1, partner_b_submitted = 1
    → submitScores() auto-transitions status → 'complete'
    → Results visible to both.

Session status = 'complete'
└── Both partners see results.
    → getSessionResults() returns quality scores.
    → No further submissions possible.
```

**Privacy guards**:

1. **Service level**: `getSessionResults()` checks session status before returning scores. Returns `null` for non-complete sessions.

2. **Component level**: `CheckinResultsComponent` only renders when view state is `'results'`, which is only set when `bothDone === true` or when `session.status === 'complete'`.

3. **Waiting component**: Shows no scores. Only shows lock icon, partner name, and timestamp.

4. **No score data in URL**: Scores are never passed as route params or query params. All data flows through the service from SQLite.

**`getSessionResults()` implementation**:

```typescript
/**
 * Privacy-guarded results fetch.
 * Returns quality scores only if the session is complete.
 * Returns null for active, expired, or non-existent sessions.
 */
async getSessionResults(
  sessionId: string,
): Promise<CheckinQualityScore[] | null> {
  const session = await this.getSession(sessionId);
  if (!session || session.status !== 'complete') {
    return null;
  }
  return this.getScoresForSession(sessionId);
}
```

---

## 7. Styling

### Color Tokens for Thresholds

The results component defines three local CSS custom properties for threshold card backgrounds:

```css
:host {
  --threshold-green-bg: color-mix(in srgb, var(--success) 12%, transparent);
  --threshold-green-border: color-mix(in srgb, var(--success) 30%, transparent);
  --threshold-amber: #D4A017;
  --threshold-amber-bg: color-mix(in srgb, var(--threshold-amber) 12%, transparent);
  --threshold-amber-border: color-mix(in srgb, var(--threshold-amber) 30%, transparent);
  --threshold-red-bg: color-mix(in srgb, var(--danger) 12%, transparent);
  --threshold-red-border: color-mix(in srgb, var(--danger) 30%, transparent);
}

:host-context([data-theme="dark"]) {
  --threshold-amber: #F5C842;
}
```

Amber is not a global design token. Defining it locally scoped to the results component avoids polluting the global token namespace with a feature-specific color.

### Quality Card Styling

```css
.quality-card {
  padding: var(--sp-4);
  border-radius: var(--r-md);
  background: var(--surface);
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-soft);
  transition: border-color var(--t-in) var(--ease-out);
}

.quality-card--green {
  background: var(--threshold-green-bg);
  border-color: var(--threshold-green-border);
}

.quality-card--amber {
  background: var(--threshold-amber-bg);
  border-color: var(--threshold-amber-border);
}

.quality-card--red {
  background: var(--threshold-red-bg);
  border-color: var(--threshold-red-border);
}
```

### Divergence Treatment

Cards with `delta >= 3` receive a pulsing border animation:

```css
.quality-card--divergent {
  border-width: 2px;
  animation: divergence-pulse 2s ease-in-out infinite;
}

@keyframes divergence-pulse {
  0%, 100% { border-color: var(--danger); }
  50% { border-color: color-mix(in srgb, var(--danger) 40%, transparent); }
}

@media (prefers-reduced-motion: reduce) {
  .quality-card--divergent {
    animation: none;
    border-color: var(--danger);
    border-width: 2px;
  }
}
```

### Score Layout Within Each Card

```css
.quality-card__scores {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--sp-3);
}

.quality-card__partner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-1);
  min-width: 64px;
}

.quality-card__partner-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.quality-card__score {
  font-family: var(--font-body);
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.quality-card__delta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--sp-2) var(--sp-3);
  border-radius: var(--r-sm);
  background: var(--surface-elevated);
}

.quality-card__delta--divergent {
  background: color-mix(in srgb, var(--danger) 15%, transparent);
}

.quality-card__delta-value {
  font-family: var(--font-body);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.quality-card__delta-label {
  font-family: var(--font-body);
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.quality-card__label {
  font-family: var(--font-display);
  font-size: 18px;
  font-style: italic;
  color: var(--text-primary);
}
```

### Results Footer Buttons

```css
.results__footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-3);
  margin-top: var(--sp-8);
  padding-bottom: calc(var(--sp-12) + env(safe-area-inset-bottom));
}

.results__cta {
  border: 0;
  padding: 16px 24px;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.2px;
  border-radius: var(--r-pill);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: transform var(--t-press) var(--ease-out);
  min-width: 220px;
  text-align: center;
}

.results__cta:active { transform: scale(0.97); }

.results__cta--trends {
  background: var(--accent-warm);
  color: var(--on-accent-warm);
  box-shadow: 0 8px 32px -8px color-mix(in srgb, var(--accent-warm) 55%, transparent);
}

.results__cta--new {
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-soft);
}
```

### Waiting Component Styling

```css
:host {
  --world-bg: var(--page-bg);
  display: block;
}

.waiting {
  min-height: 50vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-4);
  padding: var(--sp-6) var(--page-pad);
  text-align: center;
}

.waiting__icon {
  width: 64px;
  height: 64px;
  color: var(--accent-cool);
}

.waiting__icon svg {
  width: 100%;
  height: 100%;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.5;
}

.waiting__title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  margin: 0;
}

.waiting__sub {
  font-family: var(--font-body);
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
}

.waiting__timestamp {
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.waiting__pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent-cool);
  animation: pulse-dot 2s ease-in-out infinite;
  margin-top: var(--sp-4);
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.2; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.3); }
}

@media (prefers-reduced-motion: reduce) {
  .waiting__pulse {
    animation: none;
    opacity: 0.4;
  }

  .quality-card--divergent {
    animation: none;
  }
}
```

---

## 8. Navigation

### View Transitions in CheckinPage

```
[App launch / tab tap]
        |
        v
    ngOnInit()
        |
        ├── No session found → view: 'start'
        │       |
        │       v
        │   [Start Check-In button]
        │       |
        │       v
        │   view: 'select-partner'
        │
        ├── Active session, nobody submitted → view: 'select-partner'
        │
        ├── Active session, one submitted → view: 'select-partner'
        │   (let arriving partner identify themselves)
        │       |
        │       v
        │   onSelectPartner(partner)
        │       |
        │       ├── This partner already submitted → view: 'waiting'
        │       └── This partner not yet submitted → view: 'rating'
        │
        └── Complete session → view: 'results'

[rating view]
    |
    v
QuestionRatingComponent.submitted
    |
    ├── { bothDone: true }  → view: 'results'
    └── { bothDone: false } → view: 'waiting'

[waiting view]
    |
    v
CheckinWaitingComponent.bothDone
    |
    v
view: 'results'

[results view]
    |
    ├── [View Trends]  → onViewTrends() (Task 5 placeholder, no-op)
    └── [New Check-In] → onNewCheckin() → view: 'start'
```

### Route Configuration

No route changes. The `/checkin` route stays as a single flat route loading `CheckinPage`. All transitions happen via the `view` signal, not via URL changes. This is the established pattern in the existing `CheckinPage`.

Benefits:
- No URL state leakage (session IDs never in the address bar)
- No guard complexity
- Single component manages the entire flow
- Back button on the browser/device doesn't break mid-flow

### onNewCheckin Reset

When "New Check-In" is tapped from results:
1. `activeSession.set(null)` -- clears the current session reference
2. `selectedPartner.set(null)` -- clears partner identity
3. `error.set(null)` -- clears any error state
4. `view.set('start')` -- returns to the initial CTA screen

The old completed session stays in SQLite for trends (Task 5). A new `createSession()` call will happen when the user taps "Start Check-In" and selects a partner.

---

## 9. Tests

Framework: Jasmine + Karma. Component tests use `TestBed` with standalone component imports. Mock `CheckinDataService` with `jasmine.createSpyObj`. Test hosts for components with required inputs.

### 9.1 `checkin-data.service.spec.ts` -- Additions (2 new tests)

Add to the existing spec file:

```typescript
// ── getSessionResults ────────────────────────────────────────────

it('getSessionResults_completeSession_returnsScores', async () => {
  const scores: CheckinQualityScore[] = [
    { id: 'qs-1', session_id: 'sess-1', partner: 'A', quality_key: 'communication', score: 8 },
    { id: 'qs-2', session_id: 'sess-1', partner: 'B', quality_key: 'communication', score: 6 },
  ];
  // First call: getSession returns complete session
  // Second call: getScoresForSession returns scores
  sqliteSpy.query.and.callFake((opts: any) => {
    if (opts.statement.includes('checkin_session')) {
      return Promise.resolve({
        values: [fakeSession({ id: 'sess-1', status: 'complete', partner_a_submitted: 1, partner_b_submitted: 1 })],
      });
    }
    if (opts.statement.includes('checkin_quality_score')) {
      return Promise.resolve({ values: scores });
    }
    return Promise.resolve({ values: [] });
  });

  const result = await service.getSessionResults('sess-1');

  expect(result).toEqual(scores);
});

it('getSessionResults_activeSession_returnsNull', async () => {
  sqliteSpy.query.and.resolveTo({
    values: [fakeSession({ id: 'sess-1', status: 'active' })],
  });

  const result = await service.getSessionResults('sess-1');

  expect(result).toBeNull();
});
```

### 9.2 `checkin-waiting.component.spec.ts` -- New file (8 tests)

```typescript
// Test host to supply required inputs
@Component({
  standalone: true,
  imports: [CheckinWaitingComponent],
  template: `
    <app-checkin-waiting
      [sessionId]="sessionId()"
      [waitingForPartner]="waitingFor()"
      [sessionCreatedAt]="createdAt()"
      (bothDone)="onBothDone()"
    />
  `,
})
class TestHostComponent {
  readonly sessionId = signal('test-session-1');
  readonly waitingFor = signal<'A' | 'B'>('B');
  readonly createdAt = signal('2026-04-19T15:42:00.000Z');
  bothDoneFired = false;
  onBothDone(): void { this.bothDoneFired = true; }
}
```

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_lockIcon` | `data-test="waiting-lock-icon"` element present |
| 2 | `renders_waitingTitle_withPartnerName` | Title text contains "Waiting for Partner B" |
| 3 | `renders_lockedMessage` | Subtitle contains "Scores are locked" |
| 4 | `renders_sessionTimestamp` | Timestamp element displays formatted date |
| 5 | `renders_pulseIndicator` | `data-test="waiting-pulse"` element present |
| 6 | `polls_sessionStatus_onInterval` | After advancing fake timers, `getSession` called multiple times |
| 7 | `emits_bothDone_when_sessionComplete` | Spy on `getSession` returning `status: 'complete'` triggers `bothDone` emission |
| 8 | `clears_interval_onDestroy` | After `fixture.destroy()`, no more `getSession` calls |

**Polling test strategy**: Use `jasmine.clock().install()` to control `setInterval` timing. Advance by 3000ms to trigger polls. Verify service call count. Mock service to return `status: 'complete'` on the second poll and assert `bothDone` was emitted.

### 9.3 `checkin-results.component.spec.ts` -- New file (16 tests)

```typescript
// Test host to supply required inputs
@Component({
  standalone: true,
  imports: [CheckinResultsComponent],
  template: `
    <app-checkin-results
      [sessionId]="sessionId()"
      (viewTrends)="onViewTrends()"
      (newCheckin)="onNewCheckin()"
    />
  `,
})
class TestHostComponent {
  readonly sessionId = signal('test-session-1');
  viewTrendsFired = false;
  newCheckinFired = false;
  onViewTrends(): void { this.viewTrendsFired = true; }
  onNewCheckin(): void { this.newCheckinFired = true; }
}
```

Mock `CheckinDataService.getSessionResults()` to return a full set of 8 quality scores (4 qualities x 2 partners).

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_fourQualityCards` | 4 elements matching `[data-test^="quality-card-"]` |
| 2 | `renders_correctQualityLabels` | Each card contains its label text (Communication Honesty, Mutual Respect, Prioritization, Long-term Viability) |
| 3 | `renders_partnerAScore` | `data-test="score-partner-a"` shows Partner A score for each card |
| 4 | `renders_partnerBScore` | `data-test="score-partner-b"` shows Partner B score for each card |
| 5 | `renders_deltaBadge` | `data-test="delta-communication"` etc. shows correct delta value |
| 6 | `greenClass_appliedWhenAvgGte7` | Card with avg score >= 7 has `quality-card--green` class |
| 7 | `amberClass_appliedWhenAvg5to7` | Card with avg score 5-6.9 has `quality-card--amber` class |
| 8 | `redClass_appliedWhenAvgLt5` | Card with avg score < 5 has `quality-card--red` class |
| 9 | `divergentClass_appliedWhenDeltaGte3` | Card with delta >= 3 has `quality-card--divergent` class |
| 10 | `noDivergentClass_whenDeltaLt3` | Card with delta < 3 does NOT have `quality-card--divergent` class |
| 11 | `viewTrendsBtn_emitsOutput` | Click `data-test="view-trends-btn"` -> host `viewTrendsFired === true` |
| 12 | `newCheckinBtn_emitsOutput` | Click `data-test="new-checkin-btn"` -> host `newCheckinFired === true` |
| 13 | `showsLoading_whileFetching` | Before service resolves, `data-test="results-loading"` present |
| 14 | `showsError_whenServiceReturnsNull` | Service returns null -> `data-test="results-error"` present |
| 15 | `title_isPresent` | `data-test="results-title"` contains "Your Results" |
| 16 | `deltaCalculation_isAbsoluteValue` | When A=3, B=8, delta shows 5.0 (not -5) |

**Mock scores for default test fixture**:

```typescript
const mockScores: CheckinQualityScore[] = [
  // Communication: A=8, B=6 → avg=7, delta=2, green, not divergent
  { id: '1', session_id: 'test-session-1', partner: 'A', quality_key: 'communication', score: 8 },
  { id: '2', session_id: 'test-session-1', partner: 'B', quality_key: 'communication', score: 6 },
  // Respect: A=5, B=6 → avg=5.5, delta=1, amber, not divergent
  { id: '3', session_id: 'test-session-1', partner: 'A', quality_key: 'respect', score: 5 },
  { id: '4', session_id: 'test-session-1', partner: 'B', quality_key: 'respect', score: 6 },
  // Prioritization: A=3, B=4 → avg=3.5, delta=1, red, not divergent
  { id: '5', session_id: 'test-session-1', partner: 'A', quality_key: 'prioritization', score: 3 },
  { id: '6', session_id: 'test-session-1', partner: 'B', quality_key: 'prioritization', score: 4 },
  // Viability: A=9, B=4 → avg=6.5, delta=5, amber, DIVERGENT
  { id: '7', session_id: 'test-session-1', partner: 'A', quality_key: 'viability', score: 9 },
  { id: '8', session_id: 'test-session-1', partner: 'B', quality_key: 'viability', score: 4 },
];
```

This fixture covers all three color classes and both divergent/non-divergent states.

### 9.4 `checkin.page.spec.ts` -- Additions (10 new tests)

Add to the existing spec file. Extend the `CheckinPO` page object:

```typescript
// Add to CheckinPO class:
get ratingView(): HTMLElement | null {
  return this.f.nativeElement.querySelector("[data-test='checkin-rating']");
}

get waitingComponent(): HTMLElement | null {
  return this.f.nativeElement.querySelector("[data-test='checkin-waiting-component']");
}

get resultsComponent(): HTMLElement | null {
  return this.f.nativeElement.querySelector("[data-test='checkin-results-component']");
}
```

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `selectPartner_noSubmissions_showsRating` | After `onSelectPartner('A')` on fresh session, `ratingView` is present |
| 2 | `selectPartner_alreadySubmitted_showsWaiting` | Session has `partner_a_submitted: 1`, select A -> `waitingComponent` present |
| 3 | `selectPartner_otherNotSubmitted_showsRating` | Session has `partner_a_submitted: 1`, select B -> `ratingView` present |
| 4 | `ratingSubmitted_bothDone_showsResults` | Call `onRatingSubmitted({ bothDone: true })` -> `resultsComponent` present |
| 5 | `ratingSubmitted_notBothDone_showsWaiting` | Call `onRatingSubmitted({ bothDone: false })` -> `waitingComponent` present |
| 6 | `bothDone_fromWaiting_showsResults` | Call `onBothDone()` -> `resultsComponent` present |
| 7 | `newCheckin_resetsToStart` | Call `onNewCheckin()` -> `startView` present, `activeSession` is null |
| 8 | `completeSession_resume_showsResults` | `getActiveSession` returns `status: 'complete'` session -> `resultsComponent` present |
| 9 | `activeSession_oneSubmitted_showsPartnerSelect` | `getActiveSession` returns session with one partner submitted -> `selectPartnerView` present (not waiting, so other partner can identify) |
| 10 | `viewTrends_isNoOp` | Call `onViewTrends()` -> no error, no navigation (placeholder for Task 5) |

### Test Count Summary

| Spec file | Existing | New | Total |
|-----------|----------|-----|-------|
| `checkin-data.service.spec.ts` | 17 | 2 | 19 |
| `checkin-waiting.component.spec.ts` | -- | 8 | 8 |
| `checkin-results.component.spec.ts` | -- | 16 | 16 |
| `checkin.page.spec.ts` | 11 | 10 | 21 |
| **Total** | **28** | **36** | **64** |

---

## 10. Out of Scope

This section explicitly lists what Task 4 does NOT do. These are either handled by other tasks or deferred entirely.

| Item | Reason |
|------|--------|
| Trend lines / sparkline charts | Task 5. The "View Trends" button is wired but navigates nowhere until Task 5 ships. |
| Session expiry (48h auto-close) | Task 6. Waiting screen does not check for stale sessions. |
| Draft persistence (crash recovery mid-rating) | Task 6. If the app is killed during rating, scores are lost. |
| Push notifications for partner submission | Out of epic scope entirely. Polling local SQLite is the mechanism. |
| Cloud sync / multi-device pairing | Out of epic scope. Single-device flow only. |
| Custom question editing | Out of epic scope. The ten questions are static. |
| Score editing after submission | Architecture decision: submissions are immutable. |
| Animated transitions between view states | Optional polish. CSS class transitions on the `@switch` blocks could be added in Task 6. For now, view changes are instantaneous. |
| Session history list | Task 2 originally specified completed session cards. If not yet implemented, this task does not add it. Results are accessible only through the flow (rating -> waiting -> results) or by resuming a complete session on init. |
| AI-generated advice or insights | Out of epic scope. Results show raw numbers only. |
| Accessibility audit beyond basic ARIA | Task 6 may add VoiceOver testing. This task adds `aria-live`, `role="alert"`, `aria-hidden` on decorative elements, and `data-test` on all interactive elements. |
| E2E / integration tests | Unit tests only in this task. E2E belongs to a separate testing epic if created. |
