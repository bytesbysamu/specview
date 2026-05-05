# Task 7: Trend Tracking + SVG Sparklines

## 1. Purpose

Aggregate all completed check-in sessions into a time-series trend dataset and render four SVG sparkline charts (one per quality dimension). Each sparkline draws two polyline paths (Partner A + Partner B) over session indices. The page defaults to the last 10 sessions and includes a "Show all" toggle to expand to full history. Tapping a quality card navigates to a per-question drill-down. SVG is hand-built (viewBox-scaled polylines + circles), no Chart.js or third-party charting library.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 1.5 days |
| **Dependencies** | Task 6 (quality computation + comparison view) |
| **Parallel with** | None — sequential after Task 6 |
| **Blocks** | Task 8 (divergence detection + alerts) |

---

## 3. Context

### Why this task exists

Tasks 1-6 delivered the full session lifecycle through quality computation and single-session comparison. However, scores from individual sessions in isolation reveal nothing about trajectory. Users need to see how their relationship qualities evolve over time. This task adds the trend visualization layer: aggregating completed sessions into ordered time-series data and rendering it with custom SVG sparklines.

### Trade-offs

- **Hand-built SVG over Chart.js**: The architecture spec mandates no chart library. SVG polylines with viewBox scaling are < 100 lines of code, scale to any container width, and have zero bundle impact.
- **Signal-based state over TanStack Query page service**: The existing implementation (from prior tasks) uses direct `CheckinDataService` calls in `ngOnInit` with signals. We follow the same pattern for consistency.
- **ViewBox `0 0 300 100` instead of `0 0 200 60`**: The existing sparkline component already uses `300x100` with 20px padding. We follow the established implementation rather than the original spec dimensions.
- **Divergence alerts co-located with trends**: The trends page already computes and displays divergence alerts inline (delta >= 3 for the most recent session). This is preparatory work for Task 8's sustained-divergence detection.
- **`getCompletedSessions(limit)` over `getSessionHistory()`**: The data service already has a `getCompletedSessions(limit)` method that returns oldest-first ordering (suitable for left-to-right chart rendering).

### What already exists

The executor should be aware that `SparklineComponent` and `CheckinTrendsComponent` already exist in `/workspace/src/app/features/checkin/components/`. The route `checkin/trends` is already registered in `app.routes.ts`. The `DivergenceAlertComponent` is also already implemented. The task is to verify these implementations match spec, add the "show all" toggle, and add per-question drill-down on tap.

### Rejected alternatives

- **Separate trends page service**: Not needed. The trends component calls `CheckinDataService` directly. Adding a TanStack Query wrapper would be over-engineering for a read-only page with no mutations.
- **Canvas rendering**: SVG is simpler, accessible (aria-label), and scales without pixelation.
- **Separate route for drill-down**: Per-question drill-down is implemented as inline expansion within the same page (tap card to expand), not as a separate route.

---

## 4. Pre-flight

Run from the workspace root (`/workspace`):

```bash
# 1. Verify the project builds cleanly
npm run build

# 2. Verify tests pass
npx ng test --no-watch --browsers=ChromeHeadless

# 3. Verify Task 6 outputs exist (sparkline + trends components)
ls src/app/features/checkin/components/sparkline.component.ts
ls src/app/features/checkin/components/checkin-trends.component.ts
ls src/app/features/checkin/components/divergence-alert.component.ts

# 4. Verify CheckinDataService has getCompletedSessions and getScoresForSession
grep "getCompletedSessions" src/app/features/checkin/services/checkin-data.service.ts
grep "getScoresForSession" src/app/features/checkin/services/checkin-data.service.ts

# 5. Verify existing route registration
grep "trends" src/app/app.routes.ts

# 6. Verify checkin.model exports quality definitions
grep "QUALITY_DEFINITIONS" src/app/features/checkin/checkin.model.ts

# 7. Verify SparklineComponent has buildPoints exported
grep "export function buildPoints" src/app/features/checkin/components/sparkline.component.ts
```

---

## 5. Files

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/features/checkin/components/checkin-trends.component.ts` | Add "show all" toggle signal + per-question drill-down + toggle logic |
| 2 | `src/app/features/checkin/components/checkin-trends.component.spec.ts` | Add tests for show-all toggle and per-question drill-down |
| 3 | `src/app/features/checkin/services/checkin-data.service.ts` | Add `getResponsesForSession(sessionId)` method to fetch raw responses |

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/features/checkin/components/trend-toggle.component.ts` | "Last 10" / "Show all" toggle button component |
| 2 | `src/app/features/checkin/components/trend-toggle.component.spec.ts` | Unit tests for toggle component |
| 3 | `src/app/features/checkin/components/question-drilldown.component.ts` | Per-question sparkline drill-down (shown on quality card tap) |
| 4 | `src/app/features/checkin/components/question-drilldown.component.spec.ts` | Unit tests for question drilldown |

### To Leave Alone

- `src/app/features/checkin/components/sparkline.component.ts` — Already fully implemented and tested
- `src/app/features/checkin/components/divergence-alert.component.ts` — Already implemented
- `src/app/features/checkin/checkin.model.ts` — No changes needed
- `src/app/app.routes.ts` — Route already registered

---

## 6. Implementation Steps

### Step 1: Add `getResponsesForSession` to CheckinDataService

**Action**: Add a method to retrieve raw per-question responses for a session (needed for per-question drill-down).

**File**: `src/app/features/checkin/services/checkin-data.service.ts`

Add after the `getScoresForSession` method:

```typescript
  /**
   * All individual responses for a session (both partners, all 10 questions).
   * Used for per-question trend drill-down.
   */
  async getResponsesForSession(
    sessionId: string,
  ): Promise<CheckinResponse[]> {
    const result = await this.sqlite.query<CheckinResponse>({
      database: DB_NAME,
      statement:
        'SELECT * FROM checkin_response WHERE session_id = ?;',
      values: [sessionId],
    });
    return result.values;
  }
```

Also add `CheckinResponse` to the import if not already present:

```typescript
import {
  type Partner,
  type QualityKey,
  type CheckinSession,
  type CheckinResponse,
  type CheckinQualityScore,
  QUALITY_DEFINITIONS,
} from '../checkin.model';
```

**Verify**:

```bash
npx tsc --noEmit
```

---

### Step 2: Create the TrendToggle component

**Action**: Build a simple toggle button that switches between "Last 10" and "Show all" views. Emits the selected mode.

**File**: `src/app/features/checkin/components/trend-toggle.component.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

/**
 * Toggle between "Last 10" and "Show All" trend views.
 *
 * Inputs:
 *   showAll – current toggle state
 *
 * Outputs:
 *   toggled – emits when user taps the toggle
 */
@Component({
  selector: 'app-trend-toggle',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="toggle-group" data-test="trend-toggle">
      <button
        type="button"
        class="toggle-btn"
        [class.toggle-btn--active]="!showAll()"
        (click)="onToggle(false)"
        data-test="toggle-last-10"
      >
        Last 10
      </button>
      <button
        type="button"
        class="toggle-btn"
        [class.toggle-btn--active]="showAll()"
        (click)="onToggle(true)"
        data-test="toggle-show-all"
      >
        Show All
      </button>
    </div>
  `,
  styles: `
    :host {
      display: block;
    }

    .toggle-group {
      display: flex;
      background: var(--surface-elevated, rgba(255, 255, 255, 0.06));
      border-radius: var(--r-pill, 20px);
      padding: 3px;
      gap: 2px;
    }

    .toggle-btn {
      flex: 1;
      border: 0;
      background: transparent;
      color: var(--text-muted, #999);
      font-family: var(--font-body, sans-serif);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.2px;
      padding: 8px 16px;
      border-radius: var(--r-pill, 18px);
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      transition: background 0.2s ease, color 0.2s ease;
    }

    .toggle-btn--active {
      background: var(--surface, #1a1a1a);
      color: var(--text-primary, #fff);
      box-shadow: var(--shadow-soft, 0 2px 8px rgba(0,0,0,0.2));
    }

    .toggle-btn:active {
      transform: scale(0.97);
    }

    @media (prefers-reduced-motion: reduce) {
      .toggle-btn {
        transition: none;
      }
    }
  `,
})
export class TrendToggleComponent {
  readonly showAll = input<boolean>(false);
  readonly toggled = output<boolean>();

  protected onToggle(value: boolean): void {
    this.toggled.emit(value);
  }
}
```

**Verify**:

```bash
npx tsc --noEmit
```

---

### Step 3: Create the QuestionDrilldown component

**Action**: Build a component that displays per-question sparklines for a given quality. Receives question indices, question labels, and per-question score arrays for both partners.

**File**: `src/app/features/checkin/components/question-drilldown.component.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { SparklineComponent } from './sparkline.component';

/**
 * Per-question drill-down: shows a mini sparkline for each question
 * that contributes to a quality dimension.
 *
 * Inputs:
 *   questions – array of { index, text, scoresA, scoresB }
 *   qualityKey – parent quality key for data-test attributes
 */

export interface QuestionTrendItem {
  index: number;
  text: string;
  scoresA: number[];
  scoresB: number[];
}

@Component({
  selector: 'app-question-drilldown',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SparklineComponent],
  template: `
    <div class="drilldown" [attr.data-test]="'drilldown-' + qualityKey()">
      @for (q of questions(); track q.index) {
        <div class="drilldown__item" [attr.data-test]="'drilldown-q-' + q.index">
          <p class="drilldown__label">
            Q{{ q.index + 1 }}: {{ q.text }}
          </p>
          <app-sparkline
            [dataA]="q.scoresA"
            [dataB]="q.scoresB"
            [thresholds]="[5, 7]"
            [qualityKey]="'q' + q.index"
            [title]="'Question ' + (q.index + 1)"
          />
        </div>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }

    .drilldown {
      display: flex;
      flex-direction: column;
      gap: var(--sp-3, 12px);
      padding: var(--sp-3, 12px) 0;
      border-top: 1px solid var(--hairline, rgba(255,255,255,0.08));
      margin-top: var(--sp-3, 12px);
    }

    .drilldown__item {
      display: flex;
      flex-direction: column;
      gap: var(--sp-1, 4px);
    }

    .drilldown__label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted, #999);
      margin: 0;
      line-height: 1.3;
    }
  `,
})
export class QuestionDrilldownComponent {
  readonly questions = input<QuestionTrendItem[]>([]);
  readonly qualityKey = input<string>('');
}
```

**Verify**:

```bash
npx tsc --noEmit
```

---

### Step 4: Enhance CheckinTrendsComponent with show-all toggle and drill-down

**Action**: Modify the existing trends component to add the toggle, per-question drill-down on card tap, and dynamic session limit.

**File**: `src/app/features/checkin/components/checkin-trends.component.ts`

Replace the imports section:

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
  computed,
} from '@angular/core';
import { Router } from '@angular/router';
import { IonContent } from '@ionic/angular/standalone';

import { CheckinDataService } from '../services/checkin-data.service';
import { SparklineComponent } from './sparkline.component';
import { DivergenceAlertComponent } from './divergence-alert.component';
import { TrendToggleComponent } from './trend-toggle.component';
import { QuestionDrilldownComponent, QuestionTrendItem } from './question-drilldown.component';
import type { DivergenceAlertData } from './divergence-alert.component';
import {
  QUALITY_DEFINITIONS,
  CHECKIN_QUESTIONS,
  DIVERGENCE_DELTA,
  THRESHOLD_HEALTHY,
  THRESHOLD_CONCERNING,
  type QualityKey,
  type CheckinSession,
  type CheckinQualityScore,
  type CheckinResponse,
} from '../checkin.model';
```

Replace the `QualityTrendData` interface to include question-level data:

```typescript
/**
 * Trend data for a single quality across multiple sessions.
 */
export interface QualityTrendData {
  key: QualityKey;
  label: string;
  scoresA: number[];
  scoresB: number[];
  dates: string[];
  questionIndices: readonly number[];
}
```

Replace the `@Component` decorator metadata (imports array):

```typescript
  imports: [IonContent, SparklineComponent, DivergenceAlertComponent, TrendToggleComponent, QuestionDrilldownComponent],
```

Replace the template with the enhanced version:

```typescript
  template: `
    <ion-content [fullscreen]="true" class="trends-content" data-test="checkin-trends-page">
      <header class="bar" data-test="trends-header">
        <span class="eyebrow">Trend Analysis</span>
      </header>

      @if (loading()) {
        <section class="hero" data-test="trends-loading">
          <p class="sub">Loading trends...</p>
        </section>
      }

      @if (error(); as msg) {
        <section class="hero" data-test="trends-error-section">
          <p class="error" role="alert" data-test="trends-error">{{ msg }}</p>
          <button
            type="button"
            class="cta secondary"
            data-test="trends-back-btn"
            (click)="onBack()"
          >
            Back to Check-In
          </button>
        </section>
      }

      @if (!loading() && !error() && trends().length > 0) {
        <section class="trends" data-test="trends-section">
          <h1 class="title" data-test="trends-title">Relationship Trends</h1>
          <p class="sub" data-test="trends-subtitle">
            Score history across your last {{ sessionCount() }} sessions.
          </p>

          <app-trend-toggle
            [showAll]="showAll()"
            (toggled)="onToggleShowAll($event)"
          />

          <div class="legend" data-test="trends-legend">
            <span class="legend__item legend__item--a">Partner A</span>
            <span class="legend__item legend__item--b">Partner B</span>
          </div>

          <div class="charts" data-test="trends-charts">
            @for (trend of trends(); track trend.key) {
              <div
                class="chart-card"
                [class.chart-card--expanded]="expandedQuality() === trend.key"
                [attr.data-test]="'chart-card-' + trend.key"
                (click)="onToggleDrilldown(trend.key)"
              >
                <h2 class="chart-card__label" [attr.data-test]="'chart-label-' + trend.key">
                  {{ trend.label }}
                </h2>
                <app-sparkline
                  [dataA]="trend.scoresA"
                  [dataB]="trend.scoresB"
                  [labels]="trend.dates"
                  [thresholds]="[thresholdConcerning, thresholdHealthy]"
                  [qualityKey]="trend.key"
                  [title]="trend.label"
                />
                @if (expandedQuality() === trend.key) {
                  <app-question-drilldown
                    [questions]="questionTrends(trend.key)"
                    [qualityKey]="trend.key"
                  />
                }
              </div>
            }
          </div>

          @if (alerts().length > 0) {
            <div class="alerts" data-test="divergence-alerts">
              <h2 class="alerts__title" data-test="alerts-title">Divergence Alerts</h2>
              <p class="alerts__sub" data-test="alerts-subtitle">
                Qualities where partner scores differ by {{ divergenceThreshold }}+ points.
              </p>
              @for (alert of alerts(); track alert.qualityKey) {
                <app-divergence-alert
                  [qualityKey]="alert.qualityKey"
                  [qualityLabel]="alert.qualityLabel"
                  [scoreA]="alert.scoreA"
                  [scoreB]="alert.scoreB"
                  [delta]="alert.delta"
                />
              }
            </div>
          }

          <div class="actions" data-test="trends-actions">
            <button
              type="button"
              class="cta secondary"
              data-test="trends-back-home-btn"
              (click)="onBack()"
            >
              Back to Check-In
            </button>
          </div>
        </section>
      }

      @if (!loading() && !error() && trends().length === 0) {
        <section class="hero" data-test="trends-empty">
          <h1 class="title">No Trends Yet</h1>
          <p class="sub">Complete at least one check-in session to see trends.</p>
          <button
            type="button"
            class="cta primary"
            data-test="trends-start-btn"
            (click)="onBack()"
          >
            Start a Check-In
          </button>
        </section>
      }
    </ion-content>
  `,
```

Add these styles to the existing styles section (append before the closing backtick):

```css
    .chart-card {
      background: var(--surface);
      border-radius: var(--r-md);
      padding: var(--sp-4);
      box-shadow: var(--shadow-soft);
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      transition: border-color 0.2s ease;
      border: 2px solid transparent;
    }

    .chart-card--expanded {
      border-color: var(--accent-warm, #FF6B6B);
    }
```

Replace the component class:

```typescript
export class CheckinTrendsComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly checkinData = inject(CheckinDataService);

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  private readonly trendData = signal<QualityTrendData[]>([]);
  protected readonly sessionCount = signal(0);
  protected readonly showAll = signal(false);
  protected readonly expandedQuality = signal<QualityKey | null>(null);

  // Per-question response data for drill-down
  private readonly questionResponseData = signal<
    Map<string, { scoresA: Map<number, number[]>; scoresB: Map<number, number[]> }>
  >(new Map());

  protected readonly thresholdHealthy = THRESHOLD_HEALTHY;
  protected readonly thresholdConcerning = THRESHOLD_CONCERNING;
  protected readonly divergenceThreshold = DIVERGENCE_DELTA;

  protected readonly trends = computed(() => this.trendData());

  protected readonly alerts = computed<DivergenceAlertData[]>(() => {
    const data = this.trendData();
    if (data.length === 0) return [];

    const result: DivergenceAlertData[] = [];
    for (const trend of data) {
      if (trend.scoresA.length === 0 || trend.scoresB.length === 0) continue;
      const lastA = trend.scoresA[trend.scoresA.length - 1];
      const lastB = trend.scoresB[trend.scoresB.length - 1];
      const delta = Math.abs(lastA - lastB);
      if (delta >= DIVERGENCE_DELTA) {
        result.push({
          qualityKey: trend.key,
          qualityLabel: trend.label,
          scoreA: lastA,
          scoreB: lastB,
          delta,
        });
      }
    }
    return result;
  });

  async ngOnInit(): Promise<void> {
    await this.loadTrends();
  }

  async onToggleShowAll(showAll: boolean): Promise<void> {
    this.showAll.set(showAll);
    this.expandedQuality.set(null);
    await this.loadTrends();
  }

  onToggleDrilldown(qualityKey: QualityKey): void {
    if (this.expandedQuality() === qualityKey) {
      this.expandedQuality.set(null);
    } else {
      this.expandedQuality.set(qualityKey);
    }
  }

  /**
   * Build per-question trend items for the given quality key.
   * Called from the template when a chart card is expanded.
   */
  questionTrends(qualityKey: QualityKey): QuestionTrendItem[] {
    const quality = QUALITY_DEFINITIONS.find((q) => q.key === qualityKey);
    if (!quality) return [];

    const responseData = this.questionResponseData();
    const qualityData = responseData.get(qualityKey);
    if (!qualityData) return [];

    return quality.questionIndices.map((qIdx) => ({
      index: qIdx,
      text: CHECKIN_QUESTIONS[qIdx]?.text ?? `Question ${qIdx + 1}`,
      scoresA: qualityData.scoresA.get(qIdx) ?? [],
      scoresB: qualityData.scoresB.get(qIdx) ?? [],
    }));
  }

  async onBack(): Promise<void> {
    await this.router.navigate(['/checkin']);
  }

  private async loadTrends(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);

    try {
      await this.checkinData.init();
      const limit = this.showAll() ? 9999 : 10;
      const sessions = await this.checkinData.getCompletedSessions(limit);

      if (sessions.length === 0) {
        this.trendData.set([]);
        this.loading.set(false);
        return;
      }

      this.sessionCount.set(sessions.length);

      // Load quality scores for all sessions
      const allScores: CheckinQualityScore[] = [];
      for (const session of sessions) {
        const scores = await this.checkinData.getScoresForSession(session.id);
        allScores.push(...scores);
      }

      // Load per-question responses for drill-down
      const allResponses: CheckinResponse[] = [];
      for (const session of sessions) {
        const responses = await this.checkinData.getResponsesForSession(session.id);
        allResponses.push(...responses);
      }

      // Build quality-level trend data
      const trends: QualityTrendData[] = QUALITY_DEFINITIONS.map((quality) => {
        const scoresA: number[] = [];
        const scoresB: number[] = [];
        const dates: string[] = [];

        for (const session of sessions) {
          const aScore = allScores.find(
            (s) =>
              s.session_id === session.id &&
              s.partner === 'A' &&
              s.quality_key === quality.key,
          );
          const bScore = allScores.find(
            (s) =>
              s.session_id === session.id &&
              s.partner === 'B' &&
              s.quality_key === quality.key,
          );
          if (aScore && bScore) {
            scoresA.push(aScore.score);
            scoresB.push(bScore.score);
            dates.push(formatDate(session.created_at));
          }
        }

        return {
          key: quality.key,
          label: quality.label,
          scoresA,
          scoresB,
          dates,
          questionIndices: quality.questionIndices,
        };
      });

      this.trendData.set(trends);

      // Build per-question response data keyed by quality
      const questionData = new Map<
        string,
        { scoresA: Map<number, number[]>; scoresB: Map<number, number[]> }
      >();

      for (const quality of QUALITY_DEFINITIONS) {
        const scoresA = new Map<number, number[]>();
        const scoresB = new Map<number, number[]>();

        for (const qIdx of quality.questionIndices) {
          const qScoresA: number[] = [];
          const qScoresB: number[] = [];

          for (const session of sessions) {
            const respA = allResponses.find(
              (r) =>
                r.session_id === session.id &&
                r.partner === 'A' &&
                r.question_index === qIdx,
            );
            const respB = allResponses.find(
              (r) =>
                r.session_id === session.id &&
                r.partner === 'B' &&
                r.question_index === qIdx,
            );
            if (respA && respB) {
              qScoresA.push(respA.score);
              qScoresB.push(respB.score);
            }
          }

          scoresA.set(qIdx, qScoresA);
          scoresB.set(qIdx, qScoresB);
        }

        questionData.set(quality.key, { scoresA, scoresB });
      }

      this.questionResponseData.set(questionData);
    } catch (e) {
      this.error.set(
        e instanceof Error ? e.message : 'Failed to load trends.',
      );
    } finally {
      this.loading.set(false);
    }
  }
}

/** Format ISO date to short display string (e.g. "Apr 17"). */
function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return iso.slice(0, 10);
  }
}
```

**Verify**:

```bash
npx tsc --noEmit
```

---

### Step 5: Update the barrel export in index.ts

**Action**: Export the new components from the feature barrel.

**File**: `src/app/features/checkin/index.ts`

Add these exports:

```typescript
export { TrendToggleComponent } from './components/trend-toggle.component';
export { QuestionDrilldownComponent } from './components/question-drilldown.component';
export type { QuestionTrendItem } from './components/question-drilldown.component';
```

**Verify**:

```bash
npx tsc --noEmit
```

---

## 7. Tests

### Test 1: `trend-toggle.component.spec.ts`

**File**: `src/app/features/checkin/components/trend-toggle.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TrendToggleComponent } from './trend-toggle.component';

describe('TrendToggleComponent', () => {
  let fixture: ComponentFixture<TrendToggleComponent>;
  let component: TrendToggleComponent;

  function setup(showAll = false) {
    TestBed.configureTestingModule({
      imports: [TrendToggleComponent],
    });
    fixture = TestBed.createComponent(TrendToggleComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('showAll', showAll);
    fixture.detectChanges();
  }

  function query(testId: string): HTMLElement | null {
    return fixture.nativeElement.querySelector(`[data-test="${testId}"]`);
  }

  it('renders the toggle group', () => {
    setup();
    expect(query('trend-toggle')).not.toBeNull();
  });

  it('renders Last 10 button', () => {
    setup();
    expect(query('toggle-last-10')).not.toBeNull();
    expect(query('toggle-last-10')?.textContent?.trim()).toBe('Last 10');
  });

  it('renders Show All button', () => {
    setup();
    expect(query('toggle-show-all')).not.toBeNull();
    expect(query('toggle-show-all')?.textContent?.trim()).toBe('Show All');
  });

  it('Last 10 is active by default', () => {
    setup(false);
    expect(query('toggle-last-10')?.classList.contains('toggle-btn--active')).toBe(true);
    expect(query('toggle-show-all')?.classList.contains('toggle-btn--active')).toBe(false);
  });

  it('Show All is active when showAll input is true', () => {
    setup(true);
    expect(query('toggle-last-10')?.classList.contains('toggle-btn--active')).toBe(false);
    expect(query('toggle-show-all')?.classList.contains('toggle-btn--active')).toBe(true);
  });

  it('emits toggled(true) when Show All is clicked', () => {
    setup(false);
    spyOn(component.toggled, 'emit');
    query('toggle-show-all')?.click();
    expect(component.toggled.emit).toHaveBeenCalledWith(true);
  });

  it('emits toggled(false) when Last 10 is clicked', () => {
    setup(true);
    spyOn(component.toggled, 'emit');
    query('toggle-last-10')?.click();
    expect(component.toggled.emit).toHaveBeenCalledWith(false);
  });
});
```

---

### Test 2: `question-drilldown.component.spec.ts`

**File**: `src/app/features/checkin/components/question-drilldown.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { QuestionDrilldownComponent, QuestionTrendItem } from './question-drilldown.component';

describe('QuestionDrilldownComponent', () => {
  let fixture: ComponentFixture<QuestionDrilldownComponent>;
  let component: QuestionDrilldownComponent;

  const mockQuestions: QuestionTrendItem[] = [
    { index: 0, text: 'How honest was our communication today?', scoresA: [7, 8, 9], scoresB: [6, 7, 7] },
    { index: 6, text: 'How open was I about what I actually felt?', scoresA: [5, 6, 8], scoresB: [4, 5, 6] },
    { index: 7, text: 'Did we address what needed to be said?', scoresA: [6, 7, 7], scoresB: [5, 6, 8] },
  ];

  function setup(questions: QuestionTrendItem[] = mockQuestions) {
    TestBed.configureTestingModule({
      imports: [QuestionDrilldownComponent],
    });
    fixture = TestBed.createComponent(QuestionDrilldownComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('questions', questions);
    fixture.componentRef.setInput('qualityKey', 'communication');
    fixture.detectChanges();
  }

  function query(testId: string): HTMLElement | null {
    return fixture.nativeElement.querySelector(`[data-test="${testId}"]`);
  }

  function queryAll(testId: string): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll(`[data-test="${testId}"]`));
  }

  it('renders the drilldown container', () => {
    setup();
    expect(query('drilldown-communication')).not.toBeNull();
  });

  it('renders one item per question', () => {
    setup();
    expect(query('drilldown-q-0')).not.toBeNull();
    expect(query('drilldown-q-6')).not.toBeNull();
    expect(query('drilldown-q-7')).not.toBeNull();
  });

  it('renders question text with index prefix', () => {
    setup();
    const item = query('drilldown-q-0');
    expect(item?.textContent).toContain('Q1');
    expect(item?.textContent).toContain('How honest was our communication today?');
  });

  it('renders sparkline SVG for each question', () => {
    setup();
    const sparklines = fixture.nativeElement.querySelectorAll('app-sparkline');
    expect(sparklines.length).toBe(3);
  });

  it('handles empty questions array gracefully', () => {
    setup([]);
    const container = query('drilldown-communication');
    expect(container).not.toBeNull();
    const items = fixture.nativeElement.querySelectorAll('[data-test^="drilldown-q-"]');
    expect(items.length).toBe(0);
  });

  it('renders correct sparkline quality keys', () => {
    setup();
    expect(fixture.nativeElement.querySelector('[data-test="sparkline-q0"]')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('[data-test="sparkline-q6"]')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('[data-test="sparkline-q7"]')).not.toBeNull();
  });
});
```

---

### Test 3: Enhanced `checkin-trends.component.spec.ts`

**File**: `src/app/features/checkin/components/checkin-trends.component.spec.ts`

Add these additional tests to the existing spec file:

```typescript
  // ── Show All toggle ──────────────────────────────────────────────

  it('renders the trend toggle', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    expect(query('trend-toggle')).not.toBeNull();
  });

  it('defaults to showAll = false (Last 10 active)', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    const last10 = query('toggle-last-10');
    expect(last10?.classList.contains('toggle-btn--active')).toBe(true);
  });

  it('re-fetches data with high limit when toggled to show all', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    dataSpy.getCompletedSessions.calls.reset();
    await component.onToggleShowAll(true);
    fixture.detectChanges();

    expect(dataSpy.getCompletedSessions).toHaveBeenCalledWith(9999);
  });

  it('re-fetches data with limit 10 when toggled back to Last 10', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    await component.onToggleShowAll(true);
    dataSpy.getCompletedSessions.calls.reset();
    await component.onToggleShowAll(false);
    fixture.detectChanges();

    expect(dataSpy.getCompletedSessions).toHaveBeenCalledWith(10);
  });

  // ── Drill-down ───────────────────────────────────────────────────

  it('no quality expanded by default', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    const drilldowns = fixture.nativeElement.querySelectorAll('[data-test^="drilldown-"]');
    expect(drilldowns.length).toBe(0);
  });

  it('expands drilldown on quality card tap', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    component.onToggleDrilldown('communication');
    fixture.detectChanges();

    expect(query('drilldown-communication')).not.toBeNull();
  });

  it('collapses drilldown on second tap of same quality', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    component.onToggleDrilldown('communication');
    fixture.detectChanges();
    expect(query('drilldown-communication')).not.toBeNull();

    component.onToggleDrilldown('communication');
    fixture.detectChanges();
    expect(query('drilldown-communication')).toBeNull();
  });

  it('switches drilldown when different quality tapped', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    component.onToggleDrilldown('communication');
    fixture.detectChanges();
    expect(query('drilldown-communication')).not.toBeNull();

    component.onToggleDrilldown('respect');
    fixture.detectChanges();
    expect(query('drilldown-communication')).toBeNull();
    expect(query('drilldown-respect')).not.toBeNull();
  });

  it('applies expanded class to tapped chart card', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    component.onToggleDrilldown('communication');
    fixture.detectChanges();

    const card = query('chart-card-communication');
    expect(card?.classList.contains('chart-card--expanded')).toBe(true);
  });
```

Also add to the mock setup: mock `getResponsesForSession` to return per-question data:

```typescript
  function setup(sessions = SESSIONS, scores = ALL_SCORES) {
    dataSpy = jasmine.createSpyObj('CheckinDataService', [
      'init',
      'getCompletedSessions',
      'getScoresForSession',
      'getResponsesForSession',
    ]);
    dataSpy.init.and.resolveTo();
    dataSpy.getCompletedSessions.and.resolveTo(sessions);
    dataSpy.getScoresForSession.and.callFake(async (sessionId: string) =>
      scores.filter((s) => s.session_id === sessionId),
    );
    dataSpy.getResponsesForSession.and.callFake(async (sessionId: string) =>
      fakeResponsesForSession(sessionId),
    );

    // ... rest of setup
  }
```

Add the `fakeResponsesForSession` helper:

```typescript
function fakeResponsesForSession(sessionId: string): CheckinResponse[] {
  const responses: CheckinResponse[] = [];
  for (let i = 0; i < 10; i++) {
    responses.push({
      id: `resp-${sessionId}-a-${i}`,
      session_id: sessionId,
      partner: 'A',
      question_index: i,
      score: 5 + (i % 4),
      submitted_at: '2026-04-10T10:00:00.000Z',
    });
    responses.push({
      id: `resp-${sessionId}-b-${i}`,
      session_id: sessionId,
      partner: 'B',
      question_index: i,
      score: 4 + (i % 3),
      submitted_at: '2026-04-10T10:00:00.000Z',
    });
  }
  return responses;
}
```

---

### Test 4: `checkin-data.service.spec.ts` addition

Add to the existing `checkin-data.service.spec.ts`:

```typescript
  describe('getResponsesForSession', () => {
    it('returns all responses for a given session', async () => {
      // Assuming session s1 has responses from submitScores
      const responses = await service.getResponsesForSession('s1');
      // Returns CheckinResponse[] — may be empty on web (no-op SQLite)
      expect(Array.isArray(responses)).toBe(true);
    });
  });
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(checkin): add getResponsesForSession to data service for drill-down` | `services/checkin-data.service.ts` |
| 2 | `feat(checkin): add trend-toggle component (Last 10 / Show All)` | `components/trend-toggle.component.ts`, `components/trend-toggle.component.spec.ts` |
| 3 | `feat(checkin): add question-drilldown component for per-question sparklines` | `components/question-drilldown.component.ts`, `components/question-drilldown.component.spec.ts` |
| 4 | `feat(checkin): enhance trends page with show-all toggle + per-question drill-down` | `components/checkin-trends.component.ts`, `components/checkin-trends.component.spec.ts` |
| 5 | `feat(checkin): export new trend components from feature barrel` | `index.ts` |

---

## 9. Verification

After all steps are complete, run from `/workspace`:

```bash
# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. Full build
npm run build
# Expected: Build succeeds

# 3. Unit tests
npx ng test --no-watch --browsers=ChromeHeadless
# Expected: All tests pass, including:
#   - TrendToggleComponent: 7 specs
#   - QuestionDrilldownComponent: 6 specs
#   - CheckinTrendsComponent: existing + 9 new specs
#   - SparklineComponent: existing 13 specs (untouched)

# 4. Verify file structure
ls src/app/features/checkin/components/trend-toggle.component.ts
ls src/app/features/checkin/components/trend-toggle.component.spec.ts
ls src/app/features/checkin/components/question-drilldown.component.ts
ls src/app/features/checkin/components/question-drilldown.component.spec.ts

# 5. Verify new method exists
grep "getResponsesForSession" src/app/features/checkin/services/checkin-data.service.ts

# 6. Verify barrel exports
grep "TrendToggleComponent" src/app/features/checkin/index.ts
grep "QuestionDrilldownComponent" src/app/features/checkin/index.ts

# 7. Manual smoke test
ionic serve &
# Test 1: Navigate to /checkin/trends with 2+ completed sessions
# Test 2: Verify four sparkline charts render with dual lines (A + B)
# Test 3: Verify "Last 10" / "Show All" toggle switches data range
# Test 4: Tap a quality card — verify per-question sparklines expand below
# Test 5: Tap same card again — verify it collapses
# Test 6: Verify divergence alerts appear below charts when applicable
# Test 7: Verify empty state shows when no completed sessions exist
# Test 8: Verify dots render at each data point on sparklines
```

---

## 10. Rollback

Changes add 4 new files and modify 3 existing files. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -5  # find the 5 commit SHAs
git revert <sha5> <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~5

# Option 3: Manual cleanup
rm -f src/app/features/checkin/components/trend-toggle.component.ts
rm -f src/app/features/checkin/components/trend-toggle.component.spec.ts
rm -f src/app/features/checkin/components/question-drilldown.component.ts
rm -f src/app/features/checkin/components/question-drilldown.component.spec.ts
# Revert modifications:
git checkout -- src/app/features/checkin/components/checkin-trends.component.ts
git checkout -- src/app/features/checkin/components/checkin-trends.component.spec.ts
git checkout -- src/app/features/checkin/services/checkin-data.service.ts
git checkout -- src/app/features/checkin/index.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **ViewBox dimensions** | Executor may use `0 0 200 60` (original spec) instead of the existing `0 0 300 100`. The key is consistent viewBox-scaled rendering. |
| **Toggle implementation** | Executor may use `ion-segment` / `ion-segment-button` instead of custom toggle buttons. Key: two states (Last 10 / Show All) are switchable. |
| **Drill-down trigger** | Executor may use a separate "expand" icon/button instead of making the entire card tappable. Key: per-question sparklines are accessible. |
| **Drill-down presentation** | Executor may use a modal/bottom-sheet instead of inline expansion. Inline is preferred but not required. |
| **Session limit for "Show All"** | Executor may use `Infinity`, `0` (meaning unlimited), or any large number instead of `9999`. Key: all completed sessions are loaded. |
| **Question response loading** | Executor may lazy-load question responses only when drill-down is tapped (instead of eagerly loading all on page init). Both approaches are valid. |
| **Signal inputs vs @Input** | Executor may use `@Input()` decorators instead of `input()` signal functions. Both valid for Angular 19+. |
| **Template syntax** | Executor may use `*ngIf`/`*ngFor` instead of `@if`/`@for`. Both valid. |
| **Color tokens** | Executor may use different color values for Partner A/B lines (cyan/pink per original spec vs warm/cool per existing implementation). Key: two visually distinct line colors. |
| **Test count** | Executor may write fewer tests if key paths (toggle state change, drill-down expand/collapse, data loading with limit, empty state) are covered. Minimum: 15 total new test cases. |
| **Sparkline component modification** | Executor may add minor enhancements to SparklineComponent (e.g., labels input rendering) without breaking existing tests. Must not remove existing functionality. |
| **TanStack Query page service** | Executor may introduce a `CheckinTrendsPageService` wrapping the data calls with `injectQuery`. This is valid but not required — direct service calls with signals are sufficient. |

---

## 12. Out of Scope

- **Divergence detection over multiple sessions (sustained gap)** -- Task 8's concern
- **Animated line drawing / chart transitions** -- Nice-to-have, not required
- **Date axis labels on sparklines** -- Pure sparkline per spec (no axis labels, no grid)
- **Pinch-to-zoom on sparklines** -- Not planned
- **Export/share trend images** -- Not planned
- **Server-side trend aggregation** -- No backend; all client-side
- **Dark/light theme toggle** -- Dark only per spec
- **Custom date range picker** -- Only "Last 10" vs "Show All"
- **Third-party charting library (Chart.js, D3, etc.)** -- Explicitly excluded by architecture spec
- **Offline sync / multi-device trends** -- Single device, local data only
- **Haptic feedback on card tap** -- Nice-to-have; not required for this task
- **E2E / Playwright tests** -- Unit tests only
- **Performance optimization for 100+ sessions** -- Not a concern at current scale; revisit post-POC
- **Accessibility beyond data-test + aria-label** -- V1 limitation
