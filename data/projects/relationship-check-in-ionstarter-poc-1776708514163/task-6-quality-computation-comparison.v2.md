# Task 6: Quality Computation + Comparison View

## 1. Purpose

Compute four quality scores from the ten check-in responses and display a side-by-side comparison page after both partners have submitted. The four qualities are: Communication Honesty (avg Q1, Q7, Q8), Mutual Respect (avg Q2, Q3, Q4), Prioritization (avg Q5, Q6, Q9), and Long-term Viability (avg Q3, Q8, Q10). The comparison page shows each partner's quality scores with horizontal bar visualization, a per-question score grid, divergence highlighting (color-coded by gap magnitude), and a static interpretation guide with thresholds.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 1 day |
| **Dependencies** | Task 5 (submission + reveal logic) |
| **Parallel with** | None — sequential after Task 5 |
| **Blocks** | Task 7 (trend tracking + SVG sparklines) |

---

## 3. Context

### Why this task exists

Tasks 1-5 delivered the full session lifecycle: creation, rating, auto-save, submission, and partner pairing. At this point both partners can independently submit their ten ratings. However, the raw scores are not yet transformed into meaningful quality dimensions, and there is no view that shows both partners' results side by side. This task adds the quality computation (a pure utility function) and the comparison page that surfaces divergences between partners.

### Trade-offs

- **Pure utility function for computation**: `computeQualities` is a plain function, not a service. It takes a `CheckInResponse[]` and returns a `QualityScore`. This keeps it trivially testable and avoids DI overhead for what is essentially arithmetic.
- **Q3 and Q8 appear in multiple qualities**: By design, some questions contribute to more than one quality dimension. This is intentional — the architecture doc specifies the exact index mapping.
- **Divergence thresholds are hardcoded**: Green (gap <= 2), yellow (gap 2-3 exclusive), red (gap >= 4). These match the architecture spec. No user-configurable thresholds.
- **Static interpretation guide**: A simple in-page section showing what score ranges mean (1-3 low, 4-6 moderate, 7-10 strong). No AI-generated narrative.
- **Page service fetches both partners' data**: The comparison page service queries responses for both the current session and the paired partner session from the same calendar day. It computes qualities client-side.

### Rejected alternatives

- **Server-side quality computation**: No backend yet. All computation happens in the utility function.
- **Chart.js or D3 for visualization**: Overkill for simple horizontal bars. CSS width percentage is sufficient.
- **Modal popup for divergences**: Inline coloring is less intrusive and keeps context visible.
- **Separate page per quality dimension**: Over-engineering. A single scrollable page with all four qualities + question grid is sufficient.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Verify Task 5 outputs exist (submit page, partner pairing)
ls src/app/domains/check-in/pages/check-in-submit/check-in-submit.page.ts
ls src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.ts

# 4. Verify CheckInResponse and QualityScore interfaces exist
grep "QualityScore" src/app/domains/check-in/interfaces/check-in.ts
grep "CheckInResponse" src/app/domains/check-in/interfaces/check-in.ts

# 5. Verify getResponses method exists in check-in service
grep "getResponses" src/app/domains/check-in/services/check-in/check-in.service.ts

# 6. Verify getSessionsByDate method exists (added in Task 5)
grep "getSessionsByDate" src/app/domains/check-in/services/check-in/check-in.service.ts

# 7. Verify current route structure includes submit route
grep "submit" src/app/domains/check-in/check-in.routes.ts

# 8. Verify navigateToComparison placeholder exists (Task 5 created it)
grep "navigateToComparison" src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.ts
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/utils/quality.util.ts` | Pure function: `computeQualities(responses: CheckInResponse[]): QualityScore` |
| 2 | `src/app/domains/check-in/utils/quality.util.spec.ts` | Unit tests for quality computation |
| 3 | `src/app/domains/check-in/components/quality-bar/quality-bar.component.ts` | Horizontal bar component showing a score 1-10 with accent fill |
| 4 | `src/app/domains/check-in/components/quality-bar/quality-bar.component.html` | Template for quality bar |
| 5 | `src/app/domains/check-in/components/quality-bar/quality-bar.component.scss` | Styles for quality bar with divergence coloring |
| 6 | `src/app/domains/check-in/components/quality-bar/quality-bar.component.spec.ts` | Unit tests for quality bar |
| 7 | `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.ts` | Side-by-side comparison page component |
| 8 | `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.html` | Template: quality bars + question grid + interpretation guide |
| 9 | `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.scss` | Dark theme styles for comparison layout |
| 10 | `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.spec.ts` | Unit tests for comparison page |
| 11 | `src/app/domains/check-in/services/check-in-comparison-page/check-in-comparison-page.service.ts` | TanStack Query page service: loads both partners' responses + computes qualities |
| 12 | `src/app/domains/check-in/services/check-in-comparison-page/check-in-comparison-page.service.spec.ts` | Unit tests for comparison page service |

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/domains/check-in/check-in.routes.ts` | Add `comparison/:sessionId` route |
| 2 | `src/app/domains/check-in/services/index.ts` | Add barrel export for `check-in-comparison-page` service |
| 3 | `src/app/core/services/router/router.service.ts` | Add `navigateToCheckInComparisonPage(sessionId)` method |

### To Leave Alone

- `src/app/domains/check-in/interfaces/check-in.ts` — `QualityScore` interface already defined (Task 1)
- `src/app/domains/check-in/services/check-in/check-in.service.ts` — Consumed, not modified
- `src/app/domains/check-in/services/check-in-submit-page/check-in-submit-page.service.ts` — `navigateToComparison` already routes to `/check-in/comparison/:sessionId`
- `src/app/domains/check-in/pages/check-in-submit/` — Task 5's concern, already navigates to comparison

---

## 6. Implementation Steps

### Step 1: Create the quality computation utility

**Action**: A pure function that takes an array of `CheckInResponse` objects and returns a `QualityScore`. The function uses 0-indexed question references matching the architecture spec.

**File**: `src/app/domains/check-in/utils/quality.util.ts`

```typescript
import { CheckInResponse, QualityScore } from '../interfaces/check-in';

/**
 * Compute four quality scores from the ten check-in responses.
 *
 * Quality dimensions (0-indexed questions):
 *   Communication Honesty: avg(Q0, Q6, Q7)
 *   Mutual Respect: avg(Q1, Q2, Q3)
 *   Prioritization: avg(Q4, Q5, Q8)
 *   Long-term Viability: avg(Q2, Q7, Q9)
 *
 * Returns 0 for any quality where constituent questions have no score.
 */
export function computeQualities(responses: CheckInResponse[]): QualityScore {
  const score = (idx: number): number =>
    responses.find(r => r.questionIndex === idx)?.score ?? 0;

  return {
    communicationHonesty: (score(0) + score(6) + score(7)) / 3,
    mutualRespect: (score(1) + score(2) + score(3)) / 3,
    prioritization: (score(4) + score(5) + score(8)) / 3,
    longTermViability: (score(2) + score(7) + score(9)) / 3,
  };
}

/**
 * Determine divergence severity between two scores.
 * Returns a color token based on the absolute gap.
 */
export type DivergenceLevel = 'green' | 'yellow' | 'red';

export function getDivergenceLevel(
  scoreA: number,
  scoreB: number,
): DivergenceLevel {
  const gap = Math.abs(scoreA - scoreB);
  if (gap >= 4) return 'red';
  if (gap > 2) return 'yellow';
  return 'green';
}

/**
 * Quality dimension labels for display.
 */
export const QUALITY_LABELS: Record<keyof QualityScore, string> = {
  communicationHonesty: 'Communication & Honesty',
  mutualRespect: 'Mutual Respect',
  prioritization: 'Prioritization',
  longTermViability: 'Long-term Viability',
};

/**
 * Static interpretation thresholds.
 */
export interface InterpretationBand {
  min: number;
  max: number;
  label: string;
  description: string;
}

export const INTERPRETATION_BANDS: InterpretationBand[] = [
  {
    min: 1,
    max: 3,
    label: 'Low',
    description: 'Significant attention needed. Consider discussing openly.',
  },
  {
    min: 4,
    max: 6,
    label: 'Moderate',
    description: 'Room for growth. Awareness is the first step.',
  },
  {
    min: 7,
    max: 10,
    label: 'Strong',
    description: 'Healthy range. Keep nurturing what works.',
  },
];
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 2: Create the quality-bar component

**Action**: Build a reusable horizontal bar that visualizes a single quality score (1-10 scale). It accepts a score, optional label, and optional divergence level for coloring.

**File**: `src/app/domains/check-in/components/quality-bar/quality-bar.component.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  Input,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DivergenceLevel } from '../../utils/quality.util';

@Component({
  selector: 'app-quality-bar',
  templateUrl: './quality-bar.component.html',
  styleUrls: ['./quality-bar.component.scss'],
  imports: [CommonModule],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QualityBarComponent {
  @Input({ required: true }) score = 0;
  @Input() maxScore = 10;
  @Input() label = '';
  @Input() divergenceLevel: DivergenceLevel = 'green';

  public get fillPercent(): number {
    if (this.maxScore <= 0) return 0;
    return Math.min(100, Math.max(0, (this.score / this.maxScore) * 100));
  }

  public get formattedScore(): string {
    return this.score.toFixed(1);
  }
}
```

**File**: `src/app/domains/check-in/components/quality-bar/quality-bar.component.html`

```html
<div
  class="quality-bar"
  [class.quality-bar--green]="divergenceLevel === 'green'"
  [class.quality-bar--yellow]="divergenceLevel === 'yellow'"
  [class.quality-bar--red]="divergenceLevel === 'red'"
  [attr.data-test]="'quality-bar-' + label"
>
  <div class="quality-bar__track">
    <div
      class="quality-bar__fill"
      [style.width.%]="fillPercent"
    ></div>
  </div>
  <span class="quality-bar__score" data-test="quality-bar-score">
    {{ formattedScore }}
  </span>
</div>
```

**File**: `src/app/domains/check-in/components/quality-bar/quality-bar.component.scss`

```scss
:host {
  display: block;
}

.quality-bar {
  display: flex;
  align-items: center;
  gap: 12px;

  &__track {
    flex: 1;
    height: 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
    overflow: hidden;
  }

  &__fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
    background: var(--ion-color-primary);
  }

  &__score {
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
    min-width: 32px;
    text-align: right;
  }

  // Divergence coloring
  &--green .quality-bar__fill {
    background: #4caf50;
  }

  &--yellow .quality-bar__fill {
    background: #ffc107;
  }

  &--red .quality-bar__fill {
    background: #f44336;
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 3: Create the comparison page service

**Action**: Build the TanStack Query page service that loads both partners' responses for a paired session, computes quality scores for each, and exposes the comparison data.

**File**: `src/app/domains/check-in/services/check-in-comparison-page/check-in-comparison-page.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { RouterService } from '@app/core';
import {
  QueryObserverResult,
  injectQuery,
  injectQueryClient,
} from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { CheckInResponse, CheckInSession, QualityScore } from '../../interfaces';
import { CheckInService } from '../check-in/check-in.service';
import { computeQualities, getDivergenceLevel, DivergenceLevel } from '../../utils/quality.util';
import { getCalendarDate } from '../../utils/date.util';

export interface QualityComparison {
  key: keyof QualityScore;
  label: string;
  scoreA: number;
  scoreB: number;
  divergenceLevel: DivergenceLevel;
}

export interface QuestionComparison {
  questionIndex: number;
  scoreA: number;
  scoreB: number;
  divergenceLevel: DivergenceLevel;
}

export interface ComparisonData {
  sessionA: CheckInSession | null;
  sessionB: CheckInSession | null;
  qualitiesA: QualityScore;
  qualitiesB: QualityScore;
  qualityComparisons: QualityComparison[];
  questionComparisons: QuestionComparison[];
  hasDivergences: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class CheckInComparisonPageService {
  #client = injectQueryClient();
  #query = injectQuery();

  constructor(
    private readonly checkInService: CheckInService,
    private readonly routerService: RouterService,
  ) {}

  /**
   * Load comparison data for the given session.
   * Finds the paired partner session from the same calendar day,
   * loads both sets of responses, and computes quality scores.
   */
  public getComparisonData(
    sessionId: string,
  ): Result<QueryObserverResult<ComparisonData, Error>> {
    return this.#query({
      queryKey: ['check-in-comparison', sessionId],
      queryFn: async (): Promise<ComparisonData> => {
        // 1. Load the session to determine partner and date
        const session = await this.checkInService.getSession(sessionId);
        if (!session) {
          return this.emptyComparison();
        }

        const sessionDate = getCalendarDate(session.createdAt);
        const oppositePartner: 'A' | 'B' =
          session.partner === 'A' ? 'B' : 'A';

        // 2. Find the paired partner's session for the same day
        const partnerSession =
          await this.checkInService.getPartnerSessionForDate(
            oppositePartner,
            sessionDate,
          );

        if (!partnerSession) {
          return this.emptyComparison();
        }

        // 3. Load responses for both sessions
        const [responsesA, responsesB] = await Promise.all([
          this.checkInService.getResponses(
            session.partner === 'A' ? session.id : partnerSession.id,
          ),
          this.checkInService.getResponses(
            session.partner === 'B' ? session.id : partnerSession.id,
          ),
        ]);

        // 4. Compute qualities
        const qualitiesA = computeQualities(responsesA);
        const qualitiesB = computeQualities(responsesB);

        // 5. Build quality comparisons
        const qualityKeys: (keyof QualityScore)[] = [
          'communicationHonesty',
          'mutualRespect',
          'prioritization',
          'longTermViability',
        ];

        const qualityLabels: Record<keyof QualityScore, string> = {
          communicationHonesty: 'Communication & Honesty',
          mutualRespect: 'Mutual Respect',
          prioritization: 'Prioritization',
          longTermViability: 'Long-term Viability',
        };

        const qualityComparisons: QualityComparison[] = qualityKeys.map(
          key => ({
            key,
            label: qualityLabels[key],
            scoreA: qualitiesA[key],
            scoreB: qualitiesB[key],
            divergenceLevel: getDivergenceLevel(qualitiesA[key], qualitiesB[key]),
          }),
        );

        // 6. Build per-question comparisons
        const questionComparisons: QuestionComparison[] = Array.from(
          { length: 10 },
          (_, i) => {
            const scoreA =
              responsesA.find(r => r.questionIndex === i)?.score ?? 0;
            const scoreB =
              responsesB.find(r => r.questionIndex === i)?.score ?? 0;
            return {
              questionIndex: i,
              scoreA,
              scoreB,
              divergenceLevel: getDivergenceLevel(scoreA, scoreB),
            };
          },
        );

        // 7. Determine if any divergences exist
        const hasDivergences = qualityComparisons.some(
          q => q.divergenceLevel !== 'green',
        );

        return {
          sessionA: session.partner === 'A' ? session : partnerSession,
          sessionB: session.partner === 'B' ? session : partnerSession,
          qualitiesA,
          qualitiesB,
          qualityComparisons,
          questionComparisons,
          hasDivergences,
        };
      },
    });
  }

  public async navigateToStart(): Promise<void> {
    await this.routerService.navigateToCheckInStartPage({
      animationDirection: 'back',
    });
  }

  public async navigateToTrends(): Promise<void> {
    await this.routerService.navigateForward(['/check-in', 'trends'], {});
  }

  private emptyComparison(): ComparisonData {
    const emptyQualities: QualityScore = {
      communicationHonesty: 0,
      mutualRespect: 0,
      prioritization: 0,
      longTermViability: 0,
    };
    return {
      sessionA: null,
      sessionB: null,
      qualitiesA: emptyQualities,
      qualitiesB: emptyQualities,
      qualityComparisons: [],
      questionComparisons: [],
      hasDivergences: false,
    };
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 4: Create the comparison page component

**Action**: Build the comparison page that displays quality scores side by side with horizontal bars, a per-question grid, divergence highlighting, and a static interpretation guide.

**File**: `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  computed,
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
import { warningOutline, arrowForward } from 'ionicons/icons';
import {
  CheckInComparisonPageService,
  ComparisonData,
} from '../../services/check-in-comparison-page/check-in-comparison-page.service';
import { QualityBarComponent } from '../../components/quality-bar/quality-bar.component';
import {
  INTERPRETATION_BANDS,
  InterpretationBand,
} from '../../utils/quality.util';
import { CHECK_IN_QUESTIONS } from '../../constants/questions';

@Component({
  selector: 'app-check-in-comparison',
  templateUrl: './check-in-comparison.page.html',
  styleUrls: ['./check-in-comparison.page.scss'],
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
    QualityBarComponent,
  ],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInComparisonPage {
  public readonly sessionId: string;
  public readonly interpretationBands: InterpretationBand[] =
    INTERPRETATION_BANDS;
  public readonly questions = CHECK_IN_QUESTIONS;

  // TanStack Query
  private readonly comparisonResult;

  public readonly comparisonData = computed<ComparisonData | null>(() => {
    const result = this.comparisonResult();
    return result?.data ?? null;
  });

  public readonly isLoading = computed(() => {
    const result = this.comparisonResult();
    return result?.isLoading ?? true;
  });

  public readonly hasData = computed(() => {
    const data = this.comparisonData();
    return data !== null && data.qualityComparisons.length > 0;
  });

  constructor(
    private readonly activatedRoute: ActivatedRoute,
    private readonly comparisonPageService: CheckInComparisonPageService,
  ) {
    addIcons({ warningOutline, arrowForward });
    this.sessionId = this.activatedRoute.snapshot.params['sessionId'];
    this.comparisonResult =
      this.comparisonPageService.getComparisonData(this.sessionId).result;
  }

  public getQuestionText(questionIndex: number): string {
    return this.questions[questionIndex]?.text ?? '';
  }

  public onNavigateToStart(): void {
    void this.comparisonPageService.navigateToStart();
  }

  public onNavigateToTrends(): void {
    void this.comparisonPageService.navigateToTrends();
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 5: Create the comparison page template

**Action**: Three sections: (1) quality scores side by side with bars, (2) per-question grid, (3) interpretation guide.

**File**: `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.html`

```html
<ion-header [translucent]="true">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-back-button
        defaultHref="/check-in"
        data-test="back-button"
      ></ion-back-button>
    </ion-buttons>
    <ion-title>Comparison</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <!-- Loading state -->
  @if (isLoading()) {
    <div class="loading-state" data-test="loading-state">
      <ion-spinner name="crescent"></ion-spinner>
      <p>Loading results...</p>
    </div>
  }

  <!-- No data state -->
  @if (!isLoading() && !hasData()) {
    <div class="empty-state" data-test="empty-state">
      <p>No comparison data available yet.</p>
      <ion-button fill="outline" (click)="onNavigateToStart()">
        Back to Check-In
      </ion-button>
    </div>
  }

  <!-- Comparison content -->
  @if (hasData()) {
    <div class="comparison-content" data-test="comparison-content">

      <!-- Section 1: Quality Scores -->
      <section class="quality-section" data-test="quality-section">
        <h2 class="section-title">Quality Scores</h2>
        <div class="partner-legend">
          <span class="legend-item legend-item--a">Partner A</span>
          <span class="legend-item legend-item--b">Partner B</span>
        </div>

        @for (quality of comparisonData()!.qualityComparisons; track quality.key) {
          <div
            class="quality-row"
            [class.quality-row--divergent]="quality.divergenceLevel !== 'green'"
            [attr.data-test]="'quality-row-' + quality.key"
          >
            <div class="quality-row__header">
              <span class="quality-row__label">{{ quality.label }}</span>
              @if (quality.divergenceLevel !== 'green') {
                <ion-icon
                  name="warning-outline"
                  class="quality-row__warning"
                  [class.quality-row__warning--yellow]="quality.divergenceLevel === 'yellow'"
                  [class.quality-row__warning--red]="quality.divergenceLevel === 'red'"
                  data-test="divergence-warning"
                ></ion-icon>
              }
            </div>
            <div class="quality-row__bars">
              <div class="quality-row__bar-group">
                <span class="quality-row__partner-label">A</span>
                <app-quality-bar
                  [score]="quality.scoreA"
                  [label]="quality.key + '-a'"
                  [divergenceLevel]="quality.divergenceLevel"
                ></app-quality-bar>
              </div>
              <div class="quality-row__bar-group">
                <span class="quality-row__partner-label">B</span>
                <app-quality-bar
                  [score]="quality.scoreB"
                  [label]="quality.key + '-b'"
                  [divergenceLevel]="quality.divergenceLevel"
                ></app-quality-bar>
              </div>
            </div>
          </div>
        }
      </section>

      <!-- Section 2: Per-Question Grid -->
      <section class="question-section" data-test="question-section">
        <h2 class="section-title">Per-Question Breakdown</h2>
        <div class="question-grid">
          <div class="question-grid__header">
            <span class="question-grid__col question-grid__col--q">#</span>
            <span class="question-grid__col question-grid__col--text">Question</span>
            <span class="question-grid__col question-grid__col--score">A</span>
            <span class="question-grid__col question-grid__col--score">B</span>
          </div>
          @for (q of comparisonData()!.questionComparisons; track q.questionIndex) {
            <div
              class="question-grid__row"
              [class.question-grid__row--yellow]="q.divergenceLevel === 'yellow'"
              [class.question-grid__row--red]="q.divergenceLevel === 'red'"
              [attr.data-test]="'question-row-' + q.questionIndex"
            >
              <span class="question-grid__col question-grid__col--q">
                {{ q.questionIndex + 1 }}
              </span>
              <span class="question-grid__col question-grid__col--text">
                {{ getQuestionText(q.questionIndex) }}
              </span>
              <span
                class="question-grid__col question-grid__col--score"
                data-test="score-a"
              >
                {{ q.scoreA }}
              </span>
              <span
                class="question-grid__col question-grid__col--score"
                data-test="score-b"
              >
                {{ q.scoreB }}
              </span>
            </div>
          }
        </div>
      </section>

      <!-- Section 3: Interpretation Guide -->
      <section class="interpretation-section" data-test="interpretation-section">
        <h2 class="section-title">Interpretation Guide</h2>
        @for (band of interpretationBands; track band.label) {
          <div
            class="interpretation-band"
            [attr.data-test]="'band-' + band.label"
          >
            <span class="interpretation-band__range">
              {{ band.min }}–{{ band.max }}
            </span>
            <div class="interpretation-band__content">
              <strong class="interpretation-band__label">{{ band.label }}</strong>
              <p class="interpretation-band__desc">{{ band.description }}</p>
            </div>
          </div>
        }
      </section>

      <!-- Actions -->
      <div class="comparison-actions" data-test="comparison-actions">
        <ion-button expand="block" (click)="onNavigateToStart()">
          Done
        </ion-button>
      </div>

    </div>
  }
</ion-content>
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 6: Create the comparison page styles

**Action**: Dark-themed styles consistent with the rest of the check-in flow. Includes divergence coloring for grid rows and quality sections.

**File**: `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.scss`

```scss
:host {
  --ion-background-color: #0d0d0d;
  --ion-toolbar-background: #0d0d0d;
  --ion-toolbar-color: #ffffff;
}

ion-toolbar {
  --border-color: rgba(255, 255, 255, 0.08);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  padding: 32px 24px;
  text-align: center;

  ion-spinner {
    --color: var(--ion-color-primary);
    width: 32px;
    height: 32px;
    margin-bottom: 12px;
  }

  p {
    font-size: 15px;
    color: rgba(255, 255, 255, 0.6);
  }
}

.comparison-content {
  padding: 16px;
  padding-bottom: calc(env(safe-area-inset-bottom, 16px) + 24px);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 24px 0 16px;

  &:first-child {
    margin-top: 8px;
  }
}

// Partner legend
.partner-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.legend-item {
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 12px;

  &--a {
    color: var(--ion-color-primary);
    background: rgba(var(--ion-color-primary-rgb), 0.15);
  }

  &--b {
    color: #e040fb;
    background: rgba(224, 64, 251, 0.15);
  }
}

// Quality rows
.quality-row {
  margin-bottom: 20px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);

  &--divergent {
    border-left: 3px solid #ffc107;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  &__label {
    font-size: 14px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.85);
  }

  &__warning {
    font-size: 18px;

    &--yellow {
      color: #ffc107;
    }

    &--red {
      color: #f44336;
    }
  }

  &__bars {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__bar-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__partner-label {
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    min-width: 16px;
  }
}

// Question grid
.question-section {
  margin-top: 32px;
}

.question-grid {
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.03);

  &__header {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    background: rgba(255, 255, 255, 0.06);
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  &__row {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    &:last-child {
      border-bottom: none;
    }

    &--yellow {
      background: rgba(255, 193, 7, 0.08);
    }

    &--red {
      background: rgba(244, 67, 54, 0.08);
    }
  }

  &__col {
    &--q {
      width: 28px;
      flex-shrink: 0;
      font-size: 12px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.4);
    }

    &--text {
      flex: 1;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.8);
      line-height: 1.3;
      padding-right: 8px;
    }

    &--score {
      width: 32px;
      flex-shrink: 0;
      text-align: center;
      font-size: 14px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

// Interpretation guide
.interpretation-section {
  margin-top: 32px;
}

.interpretation-band {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  &:last-child {
    border-bottom: none;
  }

  &__range {
    font-size: 14px;
    font-weight: 700;
    color: var(--ion-color-primary);
    min-width: 40px;
  }

  &__content {
    flex: 1;
  }

  &__label {
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }

  &__desc {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.55);
    margin: 4px 0 0;
    line-height: 1.4;
  }
}

// Actions
.comparison-actions {
  margin-top: 32px;

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

### Step 7: Add the comparison route

**Action**: Register the new `comparison/:sessionId` route in the check-in routes config.

**File**: `src/app/domains/check-in/check-in.routes.ts`

Add after the `submit/:sessionId` route:

```typescript
  {
    path: 'comparison/:sessionId',
    loadComponent: () =>
      import(
        './pages/check-in-comparison/check-in-comparison.page'
      ).then(m => m.CheckInComparisonPage),
  },
```

Full file should be:

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
  {
    path: 'comparison/:sessionId',
    loadComponent: () =>
      import(
        './pages/check-in-comparison/check-in-comparison.page'
      ).then(m => m.CheckInComparisonPage),
  },
];
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 8: Add `navigateToCheckInComparisonPage` to RouterService

**Action**: Add a navigation method for the new comparison route.

**File**: `src/app/core/services/router/router.service.ts`

Add after `navigateToCheckInSubmitPage`:

```typescript
  public navigateToCheckInComparisonPage(
    sessionId: string,
    options?: NavigationOptions,
  ): Promise<boolean> {
    return this.navigateForward(
      ['/check-in', 'comparison', sessionId],
      options,
    );
  }
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 9: Update the services barrel export

**Action**: Add the new comparison page service to the barrel.

**File**: `src/app/domains/check-in/services/index.ts`

Append:

```typescript
export * from './check-in-comparison-page/check-in-comparison-page.service';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

## 7. Tests

### Test 1: `quality.util.spec.ts`

**File**: `src/app/domains/check-in/utils/quality.util.spec.ts`

```typescript
import { CheckInResponse } from '../interfaces/check-in';
import {
  computeQualities,
  getDivergenceLevel,
  INTERPRETATION_BANDS,
  QUALITY_LABELS,
} from './quality.util';

function makeResponse(
  questionIndex: number,
  score: number,
): CheckInResponse {
  return {
    id: `resp-${questionIndex}`,
    sessionId: 'sess-1',
    questionIndex,
    score,
    answeredAt: new Date().toISOString(),
  };
}

function makeFullResponses(scores: number[]): CheckInResponse[] {
  return scores.map((score, index) => makeResponse(index, score));
}

describe('quality.util', () => {
  describe('computeQualities', () => {
    it('should compute correct communicationHonesty from Q0, Q6, Q7', () => {
      const responses = makeFullResponses([9, 5, 5, 5, 5, 5, 6, 3, 5, 5]);
      const result = computeQualities(responses);
      // (9 + 6 + 3) / 3 = 6
      expect(result.communicationHonesty).toBe(6);
    });

    it('should compute correct mutualRespect from Q1, Q2, Q3', () => {
      const responses = makeFullResponses([5, 8, 7, 9, 5, 5, 5, 5, 5, 5]);
      const result = computeQualities(responses);
      // (8 + 7 + 9) / 3 = 8
      expect(result.mutualRespect).toBe(8);
    });

    it('should compute correct prioritization from Q4, Q5, Q8', () => {
      const responses = makeFullResponses([5, 5, 5, 5, 10, 4, 5, 5, 7, 5]);
      const result = computeQualities(responses);
      // (10 + 4 + 7) / 3 = 7
      expect(result.prioritization).toBe(7);
    });

    it('should compute correct longTermViability from Q2, Q7, Q9', () => {
      const responses = makeFullResponses([5, 5, 6, 5, 5, 5, 5, 9, 5, 3]);
      const result = computeQualities(responses);
      // (6 + 9 + 3) / 3 = 6
      expect(result.longTermViability).toBe(6);
    });

    it('should handle all-same scores', () => {
      const responses = makeFullResponses([7, 7, 7, 7, 7, 7, 7, 7, 7, 7]);
      const result = computeQualities(responses);
      expect(result.communicationHonesty).toBe(7);
      expect(result.mutualRespect).toBe(7);
      expect(result.prioritization).toBe(7);
      expect(result.longTermViability).toBe(7);
    });

    it('should return 0 for missing responses', () => {
      const responses: CheckInResponse[] = [];
      const result = computeQualities(responses);
      expect(result.communicationHonesty).toBe(0);
      expect(result.mutualRespect).toBe(0);
      expect(result.prioritization).toBe(0);
      expect(result.longTermViability).toBe(0);
    });

    it('should handle partial responses gracefully', () => {
      // Only Q0 and Q6 answered (2 of 3 for communicationHonesty)
      const responses = [makeResponse(0, 9), makeResponse(6, 6)];
      const result = computeQualities(responses);
      // (9 + 6 + 0) / 3 = 5
      expect(result.communicationHonesty).toBe(5);
    });

    it('should produce fractional results', () => {
      const responses = makeFullResponses([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
      const result = computeQualities(responses);
      // communicationHonesty: (1 + 7 + 8) / 3 = 16/3 ≈ 5.333
      expect(result.communicationHonesty).toBeCloseTo(5.333, 2);
      // mutualRespect: (2 + 3 + 4) / 3 = 3
      expect(result.mutualRespect).toBe(3);
      // prioritization: (5 + 6 + 9) / 3 = 20/3 ≈ 6.667
      expect(result.prioritization).toBeCloseTo(6.667, 2);
      // longTermViability: (3 + 8 + 10) / 3 = 7
      expect(result.longTermViability).toBe(7);
    });

    it('should handle duplicate question indices (takes first found)', () => {
      const responses = [
        makeResponse(0, 10),
        makeResponse(0, 1), // duplicate — first one wins via .find()
        makeResponse(6, 5),
        makeResponse(7, 5),
      ];
      const result = computeQualities(responses);
      // communicationHonesty: (10 + 5 + 5) / 3 = 6.667
      expect(result.communicationHonesty).toBeCloseTo(6.667, 2);
    });
  });

  describe('getDivergenceLevel', () => {
    it('should return green for gap <= 2', () => {
      expect(getDivergenceLevel(5, 5)).toBe('green');
      expect(getDivergenceLevel(7, 5)).toBe('green');
      expect(getDivergenceLevel(3, 5)).toBe('green');
    });

    it('should return yellow for gap > 2 and < 4', () => {
      expect(getDivergenceLevel(8, 5)).toBe('yellow');
      expect(getDivergenceLevel(2, 5)).toBe('yellow');
      expect(getDivergenceLevel(7, 4)).toBe('yellow');
    });

    it('should return red for gap >= 4', () => {
      expect(getDivergenceLevel(9, 5)).toBe('red');
      expect(getDivergenceLevel(1, 5)).toBe('red');
      expect(getDivergenceLevel(10, 2)).toBe('red');
    });

    it('should handle fractional scores', () => {
      expect(getDivergenceLevel(5.5, 3.4)).toBe('green'); // gap 2.1 → yellow
      expect(getDivergenceLevel(5.5, 3.4)).toBe('yellow'); // corrected: gap > 2
    });

    it('should treat exact boundary of 2 as green', () => {
      expect(getDivergenceLevel(7, 5)).toBe('green'); // gap = 2 exactly
    });

    it('should treat gap of exactly 4 as red', () => {
      expect(getDivergenceLevel(9, 5)).toBe('red'); // gap = 4 exactly
    });
  });

  describe('QUALITY_LABELS', () => {
    it('should have labels for all four qualities', () => {
      expect(QUALITY_LABELS.communicationHonesty).toBe(
        'Communication & Honesty',
      );
      expect(QUALITY_LABELS.mutualRespect).toBe('Mutual Respect');
      expect(QUALITY_LABELS.prioritization).toBe('Prioritization');
      expect(QUALITY_LABELS.longTermViability).toBe('Long-term Viability');
    });
  });

  describe('INTERPRETATION_BANDS', () => {
    it('should have three bands covering 1-10', () => {
      expect(INTERPRETATION_BANDS.length).toBe(3);
      expect(INTERPRETATION_BANDS[0].min).toBe(1);
      expect(INTERPRETATION_BANDS[2].max).toBe(10);
    });

    it('should have non-overlapping ranges', () => {
      for (let i = 0; i < INTERPRETATION_BANDS.length - 1; i++) {
        expect(INTERPRETATION_BANDS[i].max).toBeLessThan(
          INTERPRETATION_BANDS[i + 1].min,
        );
      }
    });
  });
});
```

---

### Test 2: `quality-bar.component.spec.ts`

**File**: `src/app/domains/check-in/components/quality-bar/quality-bar.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { QualityBarComponent } from './quality-bar.component';

describe('QualityBarComponent', () => {
  let component: QualityBarComponent;
  let fixture: ComponentFixture<QualityBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QualityBarComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(QualityBarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should compute fillPercent correctly', () => {
    component.score = 7;
    component.maxScore = 10;
    expect(component.fillPercent).toBe(70);
  });

  it('should clamp fillPercent at 100', () => {
    component.score = 12;
    component.maxScore = 10;
    expect(component.fillPercent).toBe(100);
  });

  it('should clamp fillPercent at 0 for negative scores', () => {
    component.score = -1;
    component.maxScore = 10;
    expect(component.fillPercent).toBe(0);
  });

  it('should handle maxScore of 0 gracefully', () => {
    component.score = 5;
    component.maxScore = 0;
    expect(component.fillPercent).toBe(0);
  });

  it('should format score to one decimal place', () => {
    component.score = 7.333;
    expect(component.formattedScore).toBe('7.3');
  });

  it('should format whole number scores with .0', () => {
    component.score = 8;
    expect(component.formattedScore).toBe('8.0');
  });

  it('should apply green class by default', () => {
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const bar = el.querySelector('.quality-bar');
    expect(bar?.classList.contains('quality-bar--green')).toBe(true);
  });

  it('should apply yellow class when divergenceLevel is yellow', () => {
    component.divergenceLevel = 'yellow';
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const bar = el.querySelector('.quality-bar');
    expect(bar?.classList.contains('quality-bar--yellow')).toBe(true);
  });

  it('should apply red class when divergenceLevel is red', () => {
    component.divergenceLevel = 'red';
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const bar = el.querySelector('.quality-bar');
    expect(bar?.classList.contains('quality-bar--red')).toBe(true);
  });

  it('should render the score value', () => {
    component.score = 6.5;
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const scoreEl = el.querySelector('[data-test="quality-bar-score"]');
    expect(scoreEl?.textContent?.trim()).toBe('6.5');
  });

  it('should set fill width based on score', () => {
    component.score = 5;
    component.maxScore = 10;
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const fill = el.querySelector('.quality-bar__fill') as HTMLElement;
    expect(fill.style.width).toBe('50%');
  });
});
```

---

### Test 3: `check-in-comparison-page.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-comparison-page/check-in-comparison-page.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { CheckInComparisonPageService } from './check-in-comparison-page.service';
import { CheckInService } from '../check-in/check-in.service';
import { RouterService } from '@app/core';
import { CheckInSession, CheckInResponse } from '../../interfaces';
import { provideQueryClient, QueryClient } from '@ngneat/query';

describe('CheckInComparisonPageService', () => {
  let service: CheckInComparisonPageService;
  let checkInSpy: jasmine.SpyObj<CheckInService>;
  let routerSpy: jasmine.SpyObj<RouterService>;

  const today = new Date();
  const todayIso = today.toISOString();

  function makeSession(overrides: Partial<CheckInSession> = {}): CheckInSession {
    return {
      id: 'sess-a',
      createdAt: todayIso,
      partner: 'A',
      submitted: true,
      ...overrides,
    };
  }

  function makeResponses(
    sessionId: string,
    scores: number[],
  ): CheckInResponse[] {
    return scores.map((score, index) => ({
      id: `resp-${sessionId}-${index}`,
      sessionId,
      questionIndex: index,
      score,
      answeredAt: todayIso,
    }));
  }

  beforeEach(() => {
    checkInSpy = jasmine.createSpyObj('CheckInService', [
      'getSession',
      'getSessions',
      'getResponses',
      'getSessionsByDate',
      'getPartnerSessionForDate',
    ]);
    routerSpy = jasmine.createSpyObj('RouterService', [
      'navigateToCheckInStartPage',
      'navigateForward',
    ]);

    checkInSpy.getSession.and.resolveTo(makeSession());
    checkInSpy.getPartnerSessionForDate.and.resolveTo(
      makeSession({ id: 'sess-b', partner: 'B' }),
    );
    checkInSpy.getResponses.and.callFake((sessionId: string) => {
      if (sessionId === 'sess-a') {
        return Promise.resolve(
          makeResponses('sess-a', [7, 8, 9, 7, 6, 8, 7, 8, 7, 9]),
        );
      }
      return Promise.resolve(
        makeResponses('sess-b', [5, 6, 5, 4, 8, 7, 5, 4, 6, 7]),
      );
    });

    routerSpy.navigateToCheckInStartPage.and.resolveTo(true);
    routerSpy.navigateForward.and.resolveTo(true);

    TestBed.configureTestingModule({
      providers: [
        CheckInComparisonPageService,
        { provide: CheckInService, useValue: checkInSpy },
        { provide: RouterService, useValue: routerSpy },
        provideQueryClient(new QueryClient()),
      ],
    });

    service = TestBed.inject(CheckInComparisonPageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('navigateToStart', () => {
    it('should navigate back to check-in start page', async () => {
      await service.navigateToStart();
      expect(routerSpy.navigateToCheckInStartPage).toHaveBeenCalledWith({
        animationDirection: 'back',
      });
    });
  });

  describe('navigateToTrends', () => {
    it('should navigate forward to trends route', async () => {
      await service.navigateToTrends();
      expect(routerSpy.navigateForward).toHaveBeenCalledWith(
        ['/check-in', 'trends'],
        {},
      );
    });
  });
});
```

---

### Test 4: `check-in-comparison.page.spec.ts`

**File**: `src/app/domains/check-in/pages/check-in-comparison/check-in-comparison.page.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { signal } from '@angular/core';
import { CheckInComparisonPage } from './check-in-comparison.page';
import {
  CheckInComparisonPageService,
  ComparisonData,
} from '../../services/check-in-comparison-page/check-in-comparison-page.service';
import { QualityScore } from '../../interfaces';

describe('CheckInComparisonPage', () => {
  let component: CheckInComparisonPage;
  let fixture: ComponentFixture<CheckInComparisonPage>;
  let comparisonServiceSpy: jasmine.SpyObj<CheckInComparisonPageService>;

  const mockComparisonData: ComparisonData = {
    sessionA: {
      id: 'sess-a',
      createdAt: new Date().toISOString(),
      partner: 'A',
      submitted: true,
    },
    sessionB: {
      id: 'sess-b',
      createdAt: new Date().toISOString(),
      partner: 'B',
      submitted: true,
    },
    qualitiesA: {
      communicationHonesty: 7.3,
      mutualRespect: 8.0,
      prioritization: 7.0,
      longTermViability: 8.7,
    },
    qualitiesB: {
      communicationHonesty: 4.7,
      mutualRespect: 5.0,
      prioritization: 7.0,
      longTermViability: 5.3,
    },
    qualityComparisons: [
      {
        key: 'communicationHonesty',
        label: 'Communication & Honesty',
        scoreA: 7.3,
        scoreB: 4.7,
        divergenceLevel: 'yellow',
      },
      {
        key: 'mutualRespect',
        label: 'Mutual Respect',
        scoreA: 8.0,
        scoreB: 5.0,
        divergenceLevel: 'yellow',
      },
      {
        key: 'prioritization',
        label: 'Prioritization',
        scoreA: 7.0,
        scoreB: 7.0,
        divergenceLevel: 'green',
      },
      {
        key: 'longTermViability',
        label: 'Long-term Viability',
        scoreA: 8.7,
        scoreB: 5.3,
        divergenceLevel: 'yellow',
      },
    ],
    questionComparisons: Array.from({ length: 10 }, (_, i) => ({
      questionIndex: i,
      scoreA: 7,
      scoreB: 5,
      divergenceLevel: 'green' as const,
    })),
    hasDivergences: true,
  };

  beforeEach(async () => {
    comparisonServiceSpy = jasmine.createSpyObj(
      'CheckInComparisonPageService',
      ['getComparisonData', 'navigateToStart', 'navigateToTrends'],
    );

    const mockQueryResult = {
      result: signal({
        data: mockComparisonData,
        isLoading: false,
        error: null,
      }),
    };
    comparisonServiceSpy.getComparisonData.and.returnValue(
      mockQueryResult as any,
    );
    comparisonServiceSpy.navigateToStart.and.resolveTo();
    comparisonServiceSpy.navigateToTrends.and.resolveTo();

    await TestBed.configureTestingModule({
      imports: [CheckInComparisonPage],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { params: { sessionId: 'sess-a' } } },
        },
        {
          provide: CheckInComparisonPageService,
          useValue: comparisonServiceSpy,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CheckInComparisonPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should read sessionId from route params', () => {
    expect(component.sessionId).toBe('sess-a');
  });

  it('should show comparison content when data is loaded', () => {
    const el = fixture.nativeElement as HTMLElement;
    const content = el.querySelector('[data-test="comparison-content"]');
    expect(content).toBeTruthy();
  });

  it('should render quality section with 4 quality rows', () => {
    const el = fixture.nativeElement as HTMLElement;
    const rows = el.querySelectorAll('[data-test^="quality-row-"]');
    expect(rows.length).toBe(4);
  });

  it('should render per-question grid with 10 rows', () => {
    const el = fixture.nativeElement as HTMLElement;
    const rows = el.querySelectorAll('[data-test^="question-row-"]');
    expect(rows.length).toBe(10);
  });

  it('should render interpretation section with 3 bands', () => {
    const el = fixture.nativeElement as HTMLElement;
    const bands = el.querySelectorAll('[data-test^="band-"]');
    expect(bands.length).toBe(3);
  });

  it('should show divergence warnings for non-green qualities', () => {
    const el = fixture.nativeElement as HTMLElement;
    const warnings = el.querySelectorAll('[data-test="divergence-warning"]');
    // 3 qualities have yellow divergence in mock data
    expect(warnings.length).toBe(3);
  });

  it('should navigate to start on Done click', () => {
    component.onNavigateToStart();
    expect(comparisonServiceSpy.navigateToStart).toHaveBeenCalled();
  });

  it('should return question text for valid index', () => {
    const text = component.getQuestionText(0);
    expect(text).toBeTruthy();
    expect(text.length).toBeGreaterThan(0);
  });

  it('should return empty string for invalid question index', () => {
    const text = component.getQuestionText(99);
    expect(text).toBe('');
  });
});
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add quality computation utility with divergence detection` | `utils/quality.util.ts`, `utils/quality.util.spec.ts` |
| 2 | `feat(check-in): add quality-bar component` | `components/quality-bar/quality-bar.component.ts`, `.html`, `.scss`, `.spec.ts` |
| 3 | `feat(check-in): add comparison page service with partner pairing + quality computation` | `services/check-in-comparison-page/check-in-comparison-page.service.ts`, `.spec.ts`, `services/index.ts` |
| 4 | `feat(check-in): add comparison page with side-by-side view + interpretation guide` | `pages/check-in-comparison/check-in-comparison.page.ts`, `.html`, `.scss`, `.spec.ts` |
| 5 | `feat(check-in): add comparison route + router navigation method` | `check-in.routes.ts`, `core/services/router/router.service.ts` |

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
#   - quality.util: 12+ specs
#   - QualityBarComponent: 11+ specs
#   - CheckInComparisonPageService: 3+ specs
#   - CheckInComparisonPage: 9+ specs

# 5. Manual smoke test
ionic serve &
# Test 1: Complete check-in as Partner A (all 10 rated, submit)
# Test 2: Complete check-in as Partner B (all 10 rated, submit)
# Test 3: Verify comparison page shows both partners' quality bars
# Test 4: Verify divergence warnings appear for qualities with >2 gap
# Test 5: Verify per-question grid highlights rows with large gaps (yellow/red bg)
# Test 6: Verify interpretation guide shows 3 bands (Low, Moderate, Strong)
# Test 7: Verify "Done" button navigates back to start

# 6. Verify file structure
ls src/app/domains/check-in/utils/quality.util.ts
ls src/app/domains/check-in/utils/quality.util.spec.ts
ls src/app/domains/check-in/components/quality-bar/
ls src/app/domains/check-in/pages/check-in-comparison/
ls src/app/domains/check-in/services/check-in-comparison-page/

# 7. Verify route registration
grep "comparison" src/app/domains/check-in/check-in.routes.ts

# 8. Verify quality computation is correct
# Run just the quality util tests
npx jest --testPathPattern="quality.util.spec" --verbose
```

---

## 10. Rollback

Changes add new files plus modifications to 3 existing files. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -5  # find the 5 commit SHAs
git revert <sha5> <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~5

# Option 3: Manual cleanup
rm -f src/app/domains/check-in/utils/quality.util.ts
rm -f src/app/domains/check-in/utils/quality.util.spec.ts
rm -rf src/app/domains/check-in/components/quality-bar/
rm -rf src/app/domains/check-in/pages/check-in-comparison/
rm -rf src/app/domains/check-in/services/check-in-comparison-page/
# Revert modifications:
git checkout -- src/app/domains/check-in/check-in.routes.ts
git checkout -- src/app/domains/check-in/services/index.ts
git checkout -- src/app/core/services/router/router.service.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Divergence threshold boundaries** | Executor may use `gap > 2` (exclusive) instead of `gap >= 2` for yellow, or `gap >= 3` instead of `gap > 2`. The key is three tiers: low/medium/high gap. |
| **Divergence coloring** | Executor may use orange instead of yellow, or any warm color for the medium tier. The key is three visually distinct severity levels. |
| **Score formatting** | Executor may show 2 decimal places instead of 1, or show integers when the value is whole. |
| **Interpretation guide placement** | Executor may place the interpretation guide in a collapsible section, a modal, or at the top of the page. Inline at the bottom is preferred but not required. |
| **Quality bar implementation** | Executor may use CSS gradients, SVG bars, or `ion-progress-bar` instead of custom div-based bars. The key requirement is a visual representation of 0-10 scale. |
| **Page service vs inline computation** | Executor may compute qualities directly in the page component instead of in the page service. The pure utility function must still exist separately. |
| **Navigation method** | Executor may reuse Task 5's `navigateToComparison` method directly instead of adding a new `navigateToCheckInComparisonPage` to RouterService. Both are valid. |
| **Template syntax** | Executor may use `@if` / `@for` (Angular 17+ control flow) or `*ngIf` / `*ngFor`. Both valid since project uses Angular 19+. |
| **Question grid layout** | Executor may use a table element, CSS grid, or flex layout for the per-question comparison. The key is showing question number, text, and both scores. |
| **Signal inputs vs @Input** | Executor may use `input()` / `input.required()` signal-based inputs instead of `@Input()` decorators. Both valid for Angular 17+. |
| **Test count** | Executor may write fewer tests if key paths (quality computation correctness, divergence detection, component renders with data, empty state) are covered. |

---

## 12. Out of Scope

- **Trend tracking / sparklines** -- Task 7
- **Divergence detection over time (multi-session)** -- Task 8
- **Animated transitions or page enter animations** -- Nice-to-have, not required
- **PDF/image export of comparison results** -- Not planned
- **Sharing comparison with partner** -- No backend; single-device usage
- **Custom quality formulas or configurable weights** -- Hardcoded per spec
- **AI-generated narrative or advice** -- Explicitly excluded from product scope
- **Editable quality names or labels** -- Fixed labels per architecture
- **Server-side computation** -- No backend yet; all client-side
- **Dark/light theme toggle** -- Dark only per spec
- **Accessibility beyond basic data-test attributes** -- V1 limitation; post-POC
- **E2E tests** -- Unit tests only for this task
- **Haptic feedback** -- Nice-to-have; may be added but not required
- **Offline handling** -- Data is already local; no network dependency
