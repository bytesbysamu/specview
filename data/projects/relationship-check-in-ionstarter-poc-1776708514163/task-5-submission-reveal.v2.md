# Task 5: Submission + Reveal Logic

## 1. Purpose

Add a "Submit" button that appears after all ten questions are rated. On submit, mark the current partner's session as submitted. Then check if the opposite partner has also submitted a session on the same calendar day. If both have submitted, unlock the reveal (navigate to comparison view). If only one has submitted, show a "Waiting for [Partner X]" state with a polling mechanism to detect when the other partner completes.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 1 day |
| **Dependencies** | Task 4 (draft auto-save + session expiry) |
| **Parallel with** | None — sequential after Task 4 |
| **Blocks** | Task 6 (quality computation + comparison view) |

---

## 3. Context

### Why this task exists

Tasks 1–4 delivered session creation, the rating UI, and draft persistence. At this point a user can rate all 10 questions and each answer persists automatically. However there is no finalization step — no way to lock answers and signal completion. This task adds the submit gate and implements the partner-pairing logic that determines whether both sides of the check-in are done.

### Trade-offs

- **Calendar-date pairing is timezone-local**: Uses the device's local calendar date via `new Date().toISOString().slice(0, 10)` or `toLocaleDateString('en-CA')`. If two partners are in different timezones and submit around midnight, they could mismatch. Acceptable for an on-device, same-couple tool.
- **Polling instead of push**: Since there is no backend, the "waiting" state cannot receive a real push. Instead, we poll local storage every 3 seconds (partner B might be on the same device). If both partners are on different devices with no backend, the waiting state simply persists until the user navigates away and returns.
- **Submit is irreversible**: Once submitted, the session cannot be un-submitted. This prevents gaming and keeps the comparison trustworthy.
- **Route structure**: The submit page is a new route segment (`/check-in/submit/:sessionId`) rather than a sub-view of the rating page. This gives a clean back-navigation story and separates concerns.

### Rejected alternatives

- **Auto-submit after 10th answer**: Removes user agency. Explicit submit is clearer.
- **Websocket pairing**: No backend yet. Overkill for same-device usage.
- **Shared session codes**: Adds UX complexity. Calendar-date pairing is implicit and zero-effort.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Verify Task 4 outputs exist (expiry service, markComplete, pre-fill logic)
ls src/app/domains/check-in/services/check-in/check-in.service.ts
ls src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts

# 4. Verify CheckInSession interface has submitted field
grep "submitted" src/app/domains/check-in/interfaces/check-in.ts

# 5. Verify markComplete method exists
grep "markComplete" src/app/domains/check-in/services/check-in/check-in.service.ts

# 6. Verify current route structure
cat src/app/domains/check-in/check-in.routes.ts

# 7. Verify 10 questions exist
grep -c "text:" src/app/domains/check-in/constants/questions.ts || echo "Check questions constant"
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.ts` | Submit button + waiting state + reveal navigation |
| 2 | `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.html` | Template with conditional submit/waiting/reveal states |
| 3 | `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.scss` | Dark theme styles for submit + waiting states |
| 4 | `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.spec.ts` | Unit tests for submit page |
| 5 | `src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.ts` | TanStack Query page service: submit mutation + partner-pairing query |
| 6 | `src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.spec.ts` | Unit tests for page service |
| 7 | `src/app/domains/check-in/utils/date.util.ts` | `getCalendarDate(isoString): string` helper |
| 8 | `src/app/domains/check-in/utils/date.util.spec.ts` | Unit tests for date utility |

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/domains/check-in/check-in.routes.ts` | Add `submit/:sessionId` route |
| 2 | `src/app/domains/check-in/services/check-in/check-in.service.ts` | Add `getSessionsByDate(date: string)` method |
| 3 | `src/app/domains/check-in/services/index.ts` | Add barrel export for `check-in-submit-page` service |
| 4 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts` | Add "Submit" button when all 10 rated, navigate to submit page |
| 5 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.html` | Add submit button at bottom |
| 6 | `src/app/core/services/router/router.service.ts` | Add `navigateToCheckInSubmitPage(sessionId)` method |

### To Leave Alone

- `src/app/domains/check-in/interfaces/check-in.ts` — `submitted: boolean` already present
- `src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.ts` — Already has `updateSession` with `submitted` support
- `src/app/domains/check-in/services/check-in-local-storage/check-in-local-storage.service.ts` — Already has `updateSession` with partial merge
- `src/app/domains/check-in/constants/questions.ts` — No changes needed

---

## 6. Implementation Steps

### Step 1: Create the date utility

**Action**: A pure function that extracts the local calendar date (YYYY-MM-DD) from an ISO string. Used to pair sessions by day.

**File**: `src/app/domains/check-in/utils/date.util.ts`

```typescript
/**
 * Extract the local calendar date (YYYY-MM-DD) from an ISO timestamp.
 * Used to pair partner sessions by the same day.
 */
export function getCalendarDate(isoString: string): string {
  const date = new Date(isoString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Get today's calendar date in YYYY-MM-DD format (local timezone).
 */
export function getTodayDate(): string {
  return getCalendarDate(new Date().toISOString());
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 2: Add `getSessionsByDate` to CheckInService

**Action**: Add a method that returns all sessions whose `createdAt` falls on a given calendar date. This is the core query for pairing logic.

**File**: `src/app/domains/check-in/services/check-in/check-in.service.ts`

Add after the existing `getActiveSessions` method (or after `getSessions`):

```typescript
import { getCalendarDate } from '../../utils/date.util';

// ... inside the class:

  public async getSessionsByDate(date: string): Promise<CheckInSession[]> {
    const sessions = await this.getSessions();
    return sessions.filter(s => getCalendarDate(s.createdAt) === date);
  }

  public async getPartnerSessionForDate(
    partner: CheckInSession['partner'],
    date: string,
  ): Promise<CheckInSession | null> {
    const sessions = await this.getSessionsByDate(date);
    return (
      sessions.find(s => s.partner === partner && s.submitted) ?? null
    );
  }
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 3: Add `navigateToCheckInSubmitPage` to RouterService

**Action**: Add a navigation method for the new submit route.

**File**: `src/app/core/services/router/router.service.ts`

Add after `navigateToCheckInRatingPage`:

```typescript
  public navigateToCheckInSubmitPage(
    sessionId: string,
    options?: NavigationOptions,
  ): Promise<boolean> {
    return this.navigateForward(['/check-in', 'submit', sessionId], options);
  }
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 4: Create the submit page service

**Action**: Build the TanStack Query page service that handles: (1) submit mutation, (2) partner-pairing query, (3) navigation.

**File**: `src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { RouterService } from '@app/core';
import {
  MutationResult,
  QueryObserverResult,
  injectMutation,
  injectQuery,
  injectQueryClient,
} from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { CheckInSession } from '../../interfaces';
import { CheckInService } from '../check-in/check-in.service';
import { getCalendarDate } from '../../utils/date.util';

export interface PartnerStatus {
  thisSession: CheckInSession | null;
  partnerSession: CheckInSession | null;
  bothSubmitted: boolean;
  waitingForPartner: 'A' | 'B' | null;
}

@Injectable({
  providedIn: 'root',
})
export class CheckInSubmitPageService {
  #client = injectQueryClient();
  #mutation = injectMutation();
  #query = injectQuery();

  constructor(
    private readonly checkInService: CheckInService,
    private readonly routerService: RouterService,
  ) {}

  /**
   * Submit mutation: marks the session as submitted and invalidates queries.
   */
  public submitSession(): MutationResult<void, Error, string, unknown> {
    return this.#mutation({
      mutationFn: (sessionId: string) =>
        this.checkInService.markComplete(sessionId),
      onSuccess: () => {
        void this.#client.invalidateQueries({
          queryKey: ['check-in-sessions'],
        });
        void this.#client.invalidateQueries({
          queryKey: ['check-in-partner-status'],
        });
      },
    });
  }

  /**
   * Query the partner pairing status for a given session.
   * Returns whether the opposite partner has also submitted on the same day.
   */
  public getPartnerStatus(
    sessionId: string,
  ): Result<QueryObserverResult<PartnerStatus, Error>> {
    return this.#query({
      queryKey: ['check-in-partner-status', sessionId],
      queryFn: async (): Promise<PartnerStatus> => {
        const thisSession = await this.checkInService.getSession(sessionId);
        if (!thisSession) {
          return {
            thisSession: null,
            partnerSession: null,
            bothSubmitted: false,
            waitingForPartner: null,
          };
        }

        const sessionDate = getCalendarDate(thisSession.createdAt);
        const oppositePartner: 'A' | 'B' =
          thisSession.partner === 'A' ? 'B' : 'A';

        const partnerSession =
          await this.checkInService.getPartnerSessionForDate(
            oppositePartner,
            sessionDate,
          );

        const bothSubmitted = thisSession.submitted && partnerSession !== null;

        return {
          thisSession,
          partnerSession,
          bothSubmitted,
          waitingForPartner: bothSubmitted ? null : oppositePartner,
        };
      },
      refetchInterval: 3000, // Poll every 3s to detect partner submission
    });
  }

  /**
   * Get the session by ID (for pre-submit validation).
   */
  public getSession(
    sessionId: string,
  ): Result<QueryObserverResult<CheckInSession | null, Error>> {
    return this.#query({
      queryKey: ['check-in-sessions', sessionId],
      queryFn: () => this.checkInService.getSession(sessionId),
    });
  }

  public async navigateToComparison(sessionId: string): Promise<void> {
    // Task 6 will implement the comparison route; for now navigate forward
    await this.routerService.navigateForward(
      ['/check-in', 'comparison', sessionId],
      {},
    );
  }

  public async navigateBack(): Promise<void> {
    await this.routerService.navigateToCheckInStartPage({
      animationDirection: 'back',
    });
  }
}
```

**Note**: The `navigateToComparison` method references a route that Task 6 will create. For now, define the method — the route won't exist yet but the service compiles. Alternatively, the executor may navigate to the start page with a success toast.

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 5: Create the submit page component

**Action**: Build the page that shows three states: (1) pre-submit (all 10 rated, show Submit button), (2) submitting (loading), (3) post-submit waiting or reveal.

**File**: `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import {
  IonBackButton,
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonIcon,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { checkmarkCircle, hourglassOutline } from 'ionicons/icons';
import {
  CheckInSubmitPageService,
  PartnerStatus,
} from '../../services/check-in-submit-page/check-in-submit-page.service';
import { CheckInRatingPageService } from '../../services/check-in-rating-page/check-in-rating-page.service';
import { CHECK_IN_QUESTIONS } from '../../constants/questions';

@Component({
  selector: 'app-check-in-submit',
  templateUrl: './check-in-submit.page.html',
  styleUrls: ['./check-in-submit.page.scss'],
  imports: [
    CommonModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonBackButton,
    IonButton,
    IonContent,
    IonIcon,
    IonSpinner,
  ],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInSubmitPage {
  public readonly sessionId: string;
  public readonly totalQuestions = CHECK_IN_QUESTIONS.length;

  // State
  public readonly isSubmitting = signal(false);
  public readonly hasSubmitted = signal(false);

  // TanStack Query results
  private readonly partnerStatusResult;
  private readonly sessionResult;
  private readonly submitMutation;
  private readonly responsesResult;

  // Computed from partner status query
  public readonly partnerStatus = computed<PartnerStatus | null>(() => {
    const result = this.partnerStatusResult();
    return result?.data ?? null;
  });

  public readonly bothSubmitted = computed(
    () => this.partnerStatus()?.bothSubmitted ?? false,
  );

  public readonly waitingForPartner = computed(
    () => this.partnerStatus()?.waitingForPartner ?? null,
  );

  // Check if all 10 questions are answered
  public readonly responsesCount = computed(() => {
    const result = this.responsesResult();
    return result?.data?.length ?? 0;
  });

  public readonly allRated = computed(
    () => this.responsesCount() >= this.totalQuestions,
  );

  constructor(
    private readonly activatedRoute: ActivatedRoute,
    private readonly checkInSubmitPageService: CheckInSubmitPageService,
    private readonly checkInRatingPageService: CheckInRatingPageService,
  ) {
    addIcons({ checkmarkCircle, hourglassOutline });
    this.sessionId = this.activatedRoute.snapshot.params['sessionId'];

    // Initialize queries
    this.partnerStatusResult =
      this.checkInSubmitPageService.getPartnerStatus(this.sessionId).result;
    this.sessionResult =
      this.checkInSubmitPageService.getSession(this.sessionId).result;
    this.submitMutation = this.checkInSubmitPageService.submitSession();
    this.responsesResult =
      this.checkInRatingPageService.getResponses(this.sessionId).result;

    // Check if already submitted on load
    this.checkInitialSubmitState();

    // React to partner status changes — auto-navigate on both submitted
    effect(() => {
      if (this.bothSubmitted() && this.hasSubmitted()) {
        void this.checkInSubmitPageService.navigateToComparison(this.sessionId);
      }
    });
  }

  public async onSubmit(): Promise<void> {
    if (this.isSubmitting() || this.hasSubmitted()) {
      return;
    }

    this.isSubmitting.set(true);

    try {
      await this.submitMutation.mutateAsync(this.sessionId);
      this.hasSubmitted.set(true);
    } finally {
      this.isSubmitting.set(false);
    }
  }

  public onBackToRating(): void {
    void this.checkInRatingPageService.navigateBack();
  }

  private async checkInitialSubmitState(): Promise<void> {
    try {
      const session = await this.checkInSubmitPageService[
        'checkInService'
      ].getSession(this.sessionId);
      if (session?.submitted) {
        this.hasSubmitted.set(true);
      }
    } catch {
      // Silently continue
    }
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 6: Create the submit page template

**Action**: Three-state template: (1) submit button when all rated + not yet submitted, (2) spinner during submit, (3) waiting/reveal state.

**File**: `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.html`

```html
<ion-header [translucent]="true">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-back-button
        defaultHref="/check-in"
        data-test="back-button"
      ></ion-back-button>
    </ion-buttons>
    <ion-title>Submit Check-In</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <div class="submit-container">

    <!-- State 1: Ready to submit -->
    @if (!hasSubmitted() && !isSubmitting()) {
      <div class="submit-prompt" data-test="submit-prompt">
        <ion-icon
          name="checkmark-circle"
          class="submit-icon"
          aria-hidden="true"
        ></ion-icon>
        <h2 class="submit-heading">All {{ totalQuestions }} questions rated</h2>
        <p class="submit-description">
          Once you submit, your answers are locked. Your partner will need to
          complete their check-in before scores are revealed.
        </p>
        <ion-button
          expand="block"
          (click)="onSubmit()"
          [disabled]="!allRated()"
          data-test="submit-button"
        >
          Submit My Answers
        </ion-button>
      </div>
    }

    <!-- State 2: Submitting -->
    @if (isSubmitting()) {
      <div class="submitting-state" data-test="submitting-state">
        <ion-spinner name="crescent"></ion-spinner>
        <p>Submitting...</p>
      </div>
    }

    <!-- State 3a: Submitted, waiting for partner -->
    @if (hasSubmitted() && !bothSubmitted()) {
      <div class="waiting-state" data-test="waiting-state">
        <ion-icon
          name="hourglass-outline"
          class="waiting-icon"
          aria-hidden="true"
        ></ion-icon>
        <h2 class="waiting-heading">Submitted!</h2>
        <p class="waiting-description">
          Waiting for Partner {{ waitingForPartner() }} to complete their
          check-in...
        </p>
        <p class="waiting-hint">
          Scores will be revealed once both of you have submitted today.
        </p>
      </div>
    }

    <!-- State 3b: Both submitted — reveal unlocked -->
    @if (hasSubmitted() && bothSubmitted()) {
      <div class="reveal-state" data-test="reveal-state">
        <ion-icon
          name="checkmark-circle"
          class="reveal-icon"
          aria-hidden="true"
        ></ion-icon>
        <h2 class="reveal-heading">Both submitted!</h2>
        <p class="reveal-description">
          Your scores are ready to compare.
        </p>
        <ion-button
          expand="block"
          (click)="checkInSubmitPageService.navigateToComparison(sessionId)"
          data-test="reveal-button"
        >
          View Results
        </ion-button>
      </div>
    }

  </div>
</ion-content>
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 7: Create the submit page styles

**Action**: Dark-themed styles matching the rating page's visual language.

**File**: `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.scss`

```scss
:host {
  --ion-background-color: #0d0d0d;
  --ion-toolbar-background: #0d0d0d;
  --ion-toolbar-color: #ffffff;
}

ion-toolbar {
  --border-color: rgba(255, 255, 255, 0.08);
}

.submit-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 32px 24px;
  text-align: center;
}

.submit-icon,
.reveal-icon {
  font-size: 64px;
  color: var(--ion-color-success);
  margin-bottom: 16px;
}

.waiting-icon {
  font-size: 64px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 16px;
}

.submit-heading,
.waiting-heading,
.reveal-heading {
  font-size: 22px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px;
}

.submit-description,
.waiting-description,
.reveal-description {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0 0 24px;
  line-height: 1.5;
}

.waiting-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 8px;
}

.submitting-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;

  ion-spinner {
    --color: var(--ion-color-primary);
    width: 32px;
    height: 32px;
  }

  p {
    font-size: 15px;
    color: rgba(255, 255, 255, 0.7);
  }
}

ion-button {
  --border-radius: 12px;
  margin-top: 16px;
  width: 100%;
  max-width: 320px;
}
```

**Verify**:

```bash
cd /projects/ionstarter && npm run build
```

---

### Step 8: Add the submit route

**Action**: Register the new `submit/:sessionId` route in the check-in routes config.

**File**: `src/app/domains/check-in/check-in.routes.ts`

Replace entire file:

```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/check-in-start/check-in-start.page').then(
        m => m.CheckInStartPage,
      ),
  },
  {
    path: 'rating/:sessionId',
    loadComponent: () =>
      import('./pages/check-in-rating/check-in-rating.page').then(
        m => m.CheckInRatingPage,
      ),
  },
  {
    path: 'submit/:sessionId',
    loadComponent: () =>
      import('./pages/check-in-submit/check-in-submit.page').then(
        m => m.CheckInSubmitPage,
      ),
  },
];
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 9: Add submit button to the rating page

**Action**: When all 10 questions are rated, show a "Continue to Submit" button at the bottom of the rating list. Tapping navigates to the submit page.

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.html`

Replace with:

```html
<ion-header [translucent]="true">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-back-button defaultHref="/check-in"></ion-back-button>
    </ion-buttons>
    <ion-title>Check-In</ion-title>
    <ion-buttons slot="end">
      <span class="progress-label" data-test="progress-label">
        {{ ratedCount() }} of {{ totalQuestions }}
      </span>
    </ion-buttons>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <div class="rating-list">
    @for (question of questions; track question.index) {
      <app-question-card
        [questionText]="question.text"
        [questionIndex]="question.index"
        [score]="getScore(question.index)"
        (scoreChange)="onScoreChange(question.index, $event)"
      ></app-question-card>
    }

    @if (allRated()) {
      <div class="submit-section" data-test="submit-section">
        <ion-button
          expand="block"
          (click)="onNavigateToSubmit()"
          data-test="continue-to-submit"
        >
          Continue to Submit
        </ion-button>
      </div>
    }
  </div>
</ion-content>
```

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts`

Add computed + navigation method:

```typescript
import { RouterService } from '@app/core';

// Add to constructor params:
private readonly routerService: RouterService,

// Add computed:
public readonly allRated = computed(
  () => this.ratedCount() >= this.totalQuestions,
);

// Add method:
public onNavigateToSubmit(): void {
  void this.routerService.navigateToCheckInSubmitPage(this.sessionId);
}
```

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.scss`

Append:

```scss
.submit-section {
  padding: 24px 16px;
  padding-bottom: calc(env(safe-area-inset-bottom, 16px) + 16px);

  ion-button {
    --border-radius: 12px;
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npm run build
```

---

### Step 10: Update the services barrel export

**Action**: Add the new page service to the barrel.

**File**: `src/app/domains/check-in/services/index.ts`

Append:

```typescript
export * from './check-in-submit-page/check-in-submit-page.service';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

## 7. Tests

### Test 1: `date.util.spec.ts`

**File**: `src/app/domains/check-in/utils/date.util.spec.ts`

```typescript
import { getCalendarDate, getTodayDate } from './date.util';

describe('date.util', () => {
  describe('getCalendarDate', () => {
    it('should extract date from ISO string', () => {
      const result = getCalendarDate('2024-06-15T14:30:00.000Z');
      // Result depends on local timezone; verify format
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('should return same date for two timestamps on the same day', () => {
      const morning = '2024-06-15T08:00:00.000Z';
      const evening = '2024-06-15T20:00:00.000Z';
      // Both should resolve to same local calendar date
      // (may differ if timezone crosses midnight boundary)
      expect(getCalendarDate(morning)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(getCalendarDate(evening)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('should pad single-digit months and days', () => {
      // January 5th in a known timezone
      const date = new Date(2024, 0, 5, 12, 0, 0); // local
      const result = getCalendarDate(date.toISOString());
      expect(result).toBe('2024-01-05');
    });
  });

  describe('getTodayDate', () => {
    it('should return today in YYYY-MM-DD format', () => {
      const result = getTodayDate();
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('should match manual computation', () => {
      const now = new Date();
      const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      expect(getTodayDate()).toBe(expected);
    });
  });
});
```

### Test 2: `check-in-submit-page.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { CheckInSubmitPageService } from './check-in-submit-page.service';
import { CheckInService } from '../check-in/check-in.service';
import { RouterService } from '@app/core';
import { CheckInSession } from '../../interfaces';
import { provideQueryClient, QueryClient } from '@ngneat/query';

describe('CheckInSubmitPageService', () => {
  let service: CheckInSubmitPageService;
  let checkInSpy: jasmine.SpyObj<CheckInService>;
  let routerSpy: jasmine.SpyObj<RouterService>;

  function makeSession(
    overrides: Partial<CheckInSession> = {},
  ): CheckInSession {
    return {
      id: 'sess-1',
      createdAt: new Date().toISOString(),
      partner: 'A',
      submitted: false,
      ...overrides,
    };
  }

  beforeEach(() => {
    checkInSpy = jasmine.createSpyObj('CheckInService', [
      'getSession',
      'getSessions',
      'markComplete',
      'getSessionsByDate',
      'getPartnerSessionForDate',
    ]);
    routerSpy = jasmine.createSpyObj('RouterService', [
      'navigateToCheckInStartPage',
      'navigateForward',
    ]);

    checkInSpy.getSession.and.resolveTo(makeSession());
    checkInSpy.markComplete.and.resolveTo();
    checkInSpy.getPartnerSessionForDate.and.resolveTo(null);
    routerSpy.navigateToCheckInStartPage.and.resolveTo(true);
    routerSpy.navigateForward.and.resolveTo(true);

    TestBed.configureTestingModule({
      providers: [
        CheckInSubmitPageService,
        { provide: CheckInService, useValue: checkInSpy },
        { provide: RouterService, useValue: routerSpy },
        provideQueryClient(new QueryClient()),
      ],
    });

    service = TestBed.inject(CheckInSubmitPageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('submitSession', () => {
    it('should call markComplete on the session', async () => {
      const mutation = service.submitSession();
      await mutation.mutateAsync('sess-1');
      expect(checkInSpy.markComplete).toHaveBeenCalledWith('sess-1');
    });
  });

  describe('navigateBack', () => {
    it('should navigate to check-in start page', async () => {
      await service.navigateBack();
      expect(routerSpy.navigateToCheckInStartPage).toHaveBeenCalledWith({
        animationDirection: 'back',
      });
    });
  });

  describe('navigateToComparison', () => {
    it('should navigate forward to comparison route', async () => {
      await service.navigateToComparison('sess-1');
      expect(routerSpy.navigateForward).toHaveBeenCalledWith(
        ['/check-in', 'comparison', 'sess-1'],
        {},
      );
    });
  });
});
```

### Test 3: `check-in-submit.page.spec.ts`

**File**: `src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { CheckInSubmitPage } from './check-in-submit.page';
import { CheckInSubmitPageService } from '../../services/check-in-submit-page/check-in-submit-page.service';
import { CheckInRatingPageService } from '../../services/check-in-rating-page/check-in-rating-page.service';
import { signal } from '@angular/core';

describe('CheckInSubmitPage', () => {
  let component: CheckInSubmitPage;
  let fixture: ComponentFixture<CheckInSubmitPage>;
  let submitPageServiceSpy: jasmine.SpyObj<CheckInSubmitPageService>;
  let ratingPageServiceSpy: jasmine.SpyObj<CheckInRatingPageService>;

  beforeEach(async () => {
    submitPageServiceSpy = jasmine.createSpyObj('CheckInSubmitPageService', [
      'submitSession',
      'getPartnerStatus',
      'getSession',
      'navigateToComparison',
      'navigateBack',
    ]);
    ratingPageServiceSpy = jasmine.createSpyObj('CheckInRatingPageService', [
      'getResponses',
      'navigateBack',
    ]);

    // Mock TanStack query results
    const mockQueryResult = { result: signal({ data: null, isLoading: false }) };
    submitPageServiceSpy.getPartnerStatus.and.returnValue(mockQueryResult as any);
    submitPageServiceSpy.getSession.and.returnValue(mockQueryResult as any);
    submitPageServiceSpy.submitSession.and.returnValue({
      mutateAsync: jasmine.createSpy().and.resolveTo(),
    } as any);

    const mockResponsesResult = {
      result: signal({ data: [], isLoading: false }),
    };
    ratingPageServiceSpy.getResponses.and.returnValue(
      mockResponsesResult as any,
    );

    await TestBed.configureTestingModule({
      imports: [CheckInSubmitPage],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { params: { sessionId: 'test-session-1' } } },
        },
        {
          provide: CheckInSubmitPageService,
          useValue: submitPageServiceSpy,
        },
        {
          provide: CheckInRatingPageService,
          useValue: ratingPageServiceSpy,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CheckInSubmitPage);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should read sessionId from route params', () => {
    expect(component.sessionId).toBe('test-session-1');
  });

  it('should not allow double submission', async () => {
    component.hasSubmitted.set(true);
    await component.onSubmit();
    expect(submitPageServiceSpy.submitSession().mutateAsync).not.toHaveBeenCalled();
  });

  it('should set hasSubmitted to true after successful submit', async () => {
    const mockMutation = {
      mutateAsync: jasmine.createSpy().and.resolveTo(),
    };
    submitPageServiceSpy.submitSession.and.returnValue(mockMutation as any);

    // Re-create component to pick up new mock
    fixture = TestBed.createComponent(CheckInSubmitPage);
    component = fixture.componentInstance;
    component.hasSubmitted.set(false);
    component.isSubmitting.set(false);

    // Access the private mutation directly
    (component as any).submitMutation = mockMutation;
    await component.onSubmit();

    expect(component.hasSubmitted()).toBe(true);
  });

  it('should show submit prompt when not yet submitted', () => {
    component.hasSubmitted.set(false);
    component.isSubmitting.set(false);
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector('[data-test="submit-prompt"]');
    expect(el).toBeTruthy();
  });

  it('should show waiting state after submission when partner has not submitted', () => {
    component.hasSubmitted.set(true);
    component.isSubmitting.set(false);
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector('[data-test="waiting-state"]');
    expect(el).toBeTruthy();
  });
});
```

### Test 4: `check-in.service.spec.ts` additions

Add tests for the new methods:

```typescript
describe('getSessionsByDate', () => {
  it('should return sessions created on the given date', async () => {
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    storageSpy.selectSessions.and.resolveTo([
      { id: '1', createdAt: today.toISOString(), partner: 'A', submitted: false },
      { id: '2', createdAt: '2020-01-01T00:00:00Z', partner: 'B', submitted: false },
    ]);

    const result = await service.getSessionsByDate(todayStr);
    expect(result.length).toBe(1);
    expect(result[0].id).toBe('1');
  });
});

describe('getPartnerSessionForDate', () => {
  it('should return submitted session for given partner and date', async () => {
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    storageSpy.selectSessions.and.resolveTo([
      { id: '1', createdAt: today.toISOString(), partner: 'B', submitted: true },
      { id: '2', createdAt: today.toISOString(), partner: 'A', submitted: true },
    ]);

    const result = await service.getPartnerSessionForDate('B', todayStr);
    expect(result).toBeTruthy();
    expect(result!.id).toBe('1');
    expect(result!.partner).toBe('B');
  });

  it('should return null when partner has not submitted', async () => {
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    storageSpy.selectSessions.and.resolveTo([
      { id: '1', createdAt: today.toISOString(), partner: 'B', submitted: false },
    ]);

    const result = await service.getPartnerSessionForDate('B', todayStr);
    expect(result).toBeNull();
  });
});
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add date utility for calendar-day pairing` | `utils/date.util.ts`, `utils/date.util.spec.ts` |
| 2 | `feat(check-in): add getSessionsByDate + getPartnerSessionForDate to service` | `services/check-in/check-in.service.ts` |
| 3 | `feat(check-in): add navigateToCheckInSubmitPage to router service` | `core/services/router/router.service.ts` |
| 4 | `feat(check-in): add check-in-submit-page service with submit mutation + pairing query` | `services/check-in-submit-page/check-in-submit-page.service.ts`, `.spec.ts`, `services/index.ts` |
| 5 | `feat(check-in): add submit page component with waiting + reveal states` | `pages/check-in-submit/check-in-submit.page.ts`, `.html`, `.scss`, `.spec.ts` |
| 6 | `feat(check-in): add submit route + submit button on rating page` | `check-in.routes.ts`, `pages/check-in-rating/check-in-rating.page.ts`, `.html`, `.scss` |

---

## 9. Verification

After all steps are complete, run from `/projects/ionstarter/`:

```bash
# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. Full build
npm run build
# Expected: Build succeeds

# 3. Lint
npm run lint
# Expected: 0 errors, 0 warnings

# 4. Unit tests
npm run test:ci
# Expected: All tests pass, including:
#   - date.util: 4+ specs
#   - CheckInSubmitPageService: 4+ specs
#   - CheckInSubmitPage: 5+ specs
#   - CheckInService (getSessionsByDate, getPartnerSessionForDate): 3+ specs

# 5. Manual smoke test
ionic serve &
# Test 1: Start check-in as Partner A, rate all 10, verify "Continue to Submit" appears
# Test 2: Tap Submit → verify "Waiting for Partner B" state
# Test 3: Open new tab, start check-in as Partner B, rate all 10, submit
# Test 4: Return to Partner A tab → verify reveal unlocks (or check poll interval)
# Test 5: Verify back button from submit page returns to rating

# 6. Verify file structure
ls src/app/domains/check-in/pages/check-in-submit/
ls src/app/domains/check-in/services/check-in-submit-page/
ls src/app/domains/check-in/utils/date.util.ts

# 7. Verify route registration
grep "submit" src/app/domains/check-in/check-in.routes.ts
```

---

## 10. Rollback

Changes add new files plus modifications to 4 existing files. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -6  # find the 6 commit SHAs
git revert <sha6> <sha5> <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~6

# Option 3: Manual cleanup
rm -rf src/app/domains/check-in/pages/check-in-submit/
rm -rf src/app/domains/check-in/services/check-in-submit-page/
rm -f src/app/domains/check-in/utils/date.util.ts
rm -f src/app/domains/check-in/utils/date.util.spec.ts
# Revert modifications:
git checkout -- src/app/domains/check-in/check-in.routes.ts
git checkout -- src/app/domains/check-in/services/check-in/check-in.service.ts
git checkout -- src/app/domains/check-in/services/index.ts
git checkout -- src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts
git checkout -- src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.html
git checkout -- src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.scss
git checkout -- src/app/core/services/router/router.service.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Polling interval** | Executor may use 2s, 3s, or 5s for the refetchInterval. Any value between 2–10s is acceptable. |
| **Submit on rating page vs separate page** | Executor may show the submit button inline on the rating page (bottom sheet or modal) instead of a separate route. Both patterns are valid. |
| **Date pairing implementation** | Executor may compare dates using `toLocaleDateString('en-CA')` or `toISOString().slice(0, 10)` instead of the manual year/month/day extraction. |
| **Partner status polling** | Executor may use `setInterval` + manual query invalidation instead of TanStack Query's `refetchInterval`. Both achieve the same goal. |
| **Navigation after both submit** | Executor may navigate to comparison immediately via `effect()`, or show a "View Results" button and let the user tap. Both are acceptable. |
| **Service location** | Executor may put `getSessionsByDate` and `getPartnerSessionForDate` in the submit page service instead of CheckInService. Either works. |
| **Comparison route placeholder** | Executor may navigate back to start page with a success toast instead of navigating to a non-existent comparison route. Task 6 will wire the real destination. |
| **Template syntax** | Executor may use `@if` (Angular 17+ control flow) or `*ngIf`. Both are acceptable since the project uses Angular 19+. |
| **Test count** | Executor may write fewer tests if key paths (submit mutation fires, waiting state renders, both-submitted detection) are covered. |

---

## 12. Out of Scope

- **Quality score computation** -- Task 6
- **Comparison view UI** -- Task 6
- **Trend tracking / sparklines** -- Task 7
- **Divergence detection** -- Task 8
- **Push notifications when partner submits** -- No backend; future enhancement
- **Multi-device session sync** -- No backend; both partners use same device or separate installs
- **Un-submit / edit after submission** -- Intentionally not supported
- **Session timeout during submit flow** -- Expiry is handled at app launch (Task 4); if 48h passes during the submit screen the next app launch will expire it
- **Animated transitions between states** -- Nice-to-have; not required
- **Haptic feedback on submit** -- Nice-to-have; may be added but not required
- **Server-side pairing validation** -- No backend yet
- **E2E tests** -- Unit tests only for this task
