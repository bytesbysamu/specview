# Task 5: Trend Lines + Divergence Alerts

**Purpose**: Visualize relationship patterns over time. Four SVG sparkline charts (one per quality) overlay Partner A and Partner B scores across completed sessions. Below the charts, divergence alerts surface any quality where the most recent session's delta is 3 or greater, with plain-language descriptions. This is the insight layer -- turning accumulated check-in data into visible patterns that reward consistent use.

**Effort**: 1 day

**Dependencies**:
- Task 1 (SQLite schema + data service) -- `CheckinDataService` at `/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts` with `init()`, `getScoresForSession()`.
- Task 4 (Results comparison view) -- `CheckinResultsComponent` at `/projects/bubls/src/app/features/checkin/components/checkin-results.component.ts` with route at `/checkin/results/:sessionId`. The "View Trends" button will be added to this component as part of this task.
- Model -- `checkin.model.ts` with `QUALITY_DEFINITIONS`, `QualityKey`, `THRESHOLD_HEALTHY`, `THRESHOLD_CONCERNING`, `DIVERGENCE_DELTA`, `CheckinSession`, `CheckinQualityScore`.
- Routes -- `/checkin` parent route at `/projects/bubls/src/app/app.routes.ts` with existing children: `''` (page), `waiting/:sessionId`, `results/:sessionId`.

**Blocks**: Task 6 (Session Expiry + Edge Cases) -- trend charts only render complete sessions. Expired session handling is Task 6's concern.

**Related**:
- [Solution Architecture -- Task 5 Component Design](./architecture.md)
- [Epic -- Task 5 Details](./epic.md)

---

## 1. Objective

Deliver three new components, one new data service method, a new route, and modifications to existing components:

1. **`checkin-trends.component.ts`** -- Container view at `/checkin/trends`. Renders four sparkline charts (one per quality), each showing Partner A and Partner B score lines overlaid across the last 10 completed sessions. Below the charts, renders a divergence alert list for the most recent session. Header with back navigation to check-in home.

2. **`sparkline.component.ts`** -- Reusable SVG sparkline. Inputs: two data arrays (Partner A and Partner B scores), labels (session dates), threshold values. Renders two polylines with circle markers at each data point, dashed horizontal threshold lines at score 5 and score 7. `viewBox="0 0 300 100"`, responsive width. `data-test="sparkline-{qualityKey}"`.

3. **`divergence-alert.component.ts`** -- Reusable alert list item. Inputs: quality name, Partner A score, Partner B score, delta. Only rendered when delta >= 3. Plain-language description: "You scored Communication Honesty 8, partner scored 4". `data-test="divergence-alert-{qualityKey}"`.

4. **`getCompletedSessions(limit)` method** -- New method on `CheckinDataService` that fetches the last N completed sessions ordered by `created_at` descending, along with all quality scores for those sessions. This is the data source for trend rendering.

5. **Route addition** -- New child route `trends` under `/checkin` parent, lazy-loading `CheckinTrendsComponent`.

6. **"View Trends" button** -- Added to `CheckinResultsComponent` actions area, navigating to `/checkin/trends`.

---

## 2. Inputs

Every file referenced below exists and is shipped from Tasks 1-4.

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

export const THRESHOLD_HEALTHY = 7;    // score >= 7 is green
export const THRESHOLD_CONCERNING = 5; // score >= 5 is amber, below is red
export const DIVERGENCE_DELTA = 3;     // delta >= 3 triggers divergence alert

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
| `getScoresForSession(sessionId)` | `async getScoresForSession(sessionId: string): Promise<CheckinQualityScore[]>` | All quality scores (both partners, all four qualities) for one session. |

New method to add:

| Method | Signature | Returns |
|--------|-----------|---------|
| `getCompletedSessions(limit)` | `async getCompletedSessions(limit: number): Promise<CheckinSession[]>` | Last N completed sessions ordered by `created_at` ASC (oldest first, for left-to-right charting). |

The trends component will call `getCompletedSessions(10)` to get sessions, then `getScoresForSession()` for each session to collect quality scores. This avoids adding a complex join method to the service -- the iteration is simple and the data volume is small (10 sessions x 8 scores = 80 rows max).

### CheckinResultsComponent (`/projects/bubls/src/app/features/checkin/components/checkin-results.component.ts`)

Currently renders four quality cards with a "New Check-In" button in the actions footer. No "View Trends" button exists yet.

Relevant existing elements:
- `<div class="actions" data-test="results-actions">` -- action button container
- Uses `Router` (already injected) for navigation
- Route: `/checkin/results/:sessionId` (child route under `/checkin`)

### Routes (`/projects/bubls/src/app/app.routes.ts`)

Current `/checkin` route structure:
```typescript
{
  path: 'checkin',
  children: [
    { path: '', loadComponent: () => import('./pages/checkin/checkin.page').then(m => m.CheckinPage) },
    { path: 'waiting/:sessionId', loadComponent: () => import('./features/checkin/components/checkin-waiting.component').then(m => m.CheckinWaitingComponent) },
    { path: 'results/:sessionId', loadComponent: () => import('./features/checkin/components/checkin-results.component').then(m => m.CheckinResultsComponent) },
  ],
},
```

New child route to add: `trends`.

### Barrel Exports (`/projects/bubls/src/app/features/checkin/index.ts`)

Currently exports: `CheckinDataService`, `QuestionRatingComponent`, `CheckinResultsComponent`, `CheckinWaitingComponent`, all model types and constants.

### Design Tokens (`/projects/bubls/src/app/styles/tokens.scss`)

Relevant tokens for sparkline rendering:

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--accent-warm` | `#A6510A` | `#E8A85C` | Partner A line color |
| `--accent-cool` | `#5B6CC0` | `#818CF8` | Partner B line color |
| `--success` | `#146E37` | `#2DD36F` | Green score indicator |
| `--danger` | `#C93B3B` | `#EB445A` | Red score indicator, divergence alert accent |
| `--surface` | `#FFFFFF` | `#141414` | Chart card background |
| `--surface-elevated` | `#FFFFFF` | `#1C1C1E` | Elevated surface |
| `--hairline` | `rgba(26,26,26,0.12)` | `rgba(245,245,245,0.10)` | Threshold dashed lines, axis lines |
| `--text-primary` | `#1A1A1A` | `#F5F5F5` | Chart labels, alert text |
| `--text-secondary` | `rgba(26,26,26,0.62)` | `rgba(245,245,245,0.60)` | Axis labels, secondary text |
| `--text-muted` | `rgba(26,26,26,0.42)` | `rgba(245,245,245,0.40)` | Date labels, muted text |
| `--font-display` | Cormorant Garamond | -- | Quality labels, section headings |
| `--font-body` | Instrument Sans | -- | Scores, alert text |
| `--r-md` | `16px` | -- | Chart card border radius |
| `--shadow-soft` | subtle | darker | Chart card elevation |

---

## 3. Outputs

### Files to Create

| File | Purpose |
|------|---------|
| `src/app/features/checkin/components/checkin-trends.component.ts` | Container view. Fetches trend data, renders four sparkline charts and divergence alert list. Route target for `/checkin/trends`. |
| `src/app/features/checkin/components/checkin-trends.component.spec.ts` | Unit tests: data loading, chart rendering, divergence alerts, empty state, error handling, navigation. |
| `src/app/features/checkin/components/sparkline.component.ts` | Reusable SVG sparkline. Two polylines, circle markers, threshold dashed lines. Pure presentational component. |
| `src/app/features/checkin/components/sparkline.component.spec.ts` | Unit tests: SVG element rendering, polyline point calculations, threshold lines, empty data handling, accessibility. |
| `src/app/features/checkin/components/divergence-alert.component.ts` | Single divergence alert item. Quality name, both scores, delta, plain-language label. |
| `src/app/features/checkin/components/divergence-alert.component.spec.ts` | Unit tests: rendering, text content, delta display, conditional visibility. |

### Files to Modify

| File | Change |
|------|--------|
| `src/app/features/checkin/services/checkin-data.service.ts` | Add `getCompletedSessions(limit: number)` method. |
| `src/app/features/checkin/services/checkin-data.service.spec.ts` | Add tests for `getCompletedSessions()`. |
| `src/app/features/checkin/components/checkin-results.component.ts` | Add "View Trends" button to the actions area, navigating to `/checkin/trends`. |
| `src/app/features/checkin/components/checkin-results.component.spec.ts` | Add test for "View Trends" button rendering and navigation. |
| `src/app/app.routes.ts` | Add `trends` child route under `/checkin`. |
| `src/app/features/checkin/index.ts` | Add barrel exports for `CheckinTrendsComponent`, `SparklineComponent`, `DivergenceAlertComponent`. |

### Files to Leave Alone

| File | Reason |
|------|--------|
| `src/app/features/checkin/checkin.model.ts` | All types and constants needed already exist. `THRESHOLD_HEALTHY`, `THRESHOLD_CONCERNING`, `DIVERGENCE_DELTA`, `QUALITY_DEFINITIONS` are sufficient. No new interfaces required in the model file. |
| `src/app/features/checkin/components/checkin-waiting.component.ts` | Consumed as-is. No changes. |
| `src/app/features/checkin/components/question-rating.component.ts` | Consumed as-is. No changes. |
| `src/app/pages/checkin/checkin.page.ts` | No changes needed. Trends are accessed from the results view, not the home screen. |
| `src/app/styles/tokens.scss` | All colors used via existing tokens. No new global tokens. |
| `src/app/shared/sqlite/` | Consumed transitively through `CheckinDataService`. No changes. |

---

## 4. Component Design

### 4.1 CheckinTrendsComponent

**File**: `src/app/features/checkin/components/checkin-trends.component.ts`

**Selector**: `app-checkin-trends`

**Inputs**: None. This is a route-level component. It fetches its own data from `CheckinDataService`.

**Outputs**: None. Navigation happens via `Router`.

**Internal interfaces** (defined in the component file, not exported to the model):

```typescript
interface TrendData {
  quality: QualityDefinition;
  dataA: number[];       // Partner A scores per session, oldest-first
  dataB: number[];       // Partner B scores per session, oldest-first
  labels: string[];      // Short date labels per session (e.g., "Apr 12")
}

interface DivergenceAlertData {
  qualityKey: QualityKey;
  qualityLabel: string;
  scoreA: number;
  scoreB: number;
  delta: number;
}
```

**Signals**:
- `loading: WritableSignal<boolean>` -- true during initial data fetch.
- `error: WritableSignal<string | null>` -- set if data fetch fails or no completed sessions exist.
- `trends: WritableSignal<TrendData[]>` -- array of four trend datasets, one per quality.
- `alerts: Signal<DivergenceAlertData[]>` -- computed from `trends`. Filters the most recent session's data for qualities where `delta >= DIVERGENCE_DELTA`.
- `hasData: Signal<boolean>` -- computed, true when `trends().length > 0` and at least one quality has data points.

**Template Structure**:
```
<ion-content [fullscreen]="true" class="trends-content" data-test="checkin-trends-page">
  <header class="bar" data-test="trends-header">
    <button
      type="button"
      class="back-btn"
      data-test="trends-back-btn"
      (click)="onBack()"
      aria-label="Back to check-in"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <span class="eyebrow">Trends</span>
  </header>

  @if (loading()) {
    <section class="hero" data-test="trends-loading" aria-busy="true">
      <p class="sub">Loading trends...</p>
    </section>
  }

  @if (error(); as msg) {
    <section class="hero" data-test="trends-error-section">
      <p class="error" role="alert" data-test="trends-error">{{ msg }}</p>
      <button type="button" class="cta secondary" data-test="trends-back-to-checkin" (click)="onBack()">
        Back to Check-In
      </button>
    </section>
  }

  @if (!loading() && !error() && hasData()) {
    <section class="trends" data-test="trends-section">
      <h1 class="title" data-test="trends-title">Score Trends</h1>
      <p class="sub" data-test="trends-subtitle">
        How your scores have evolved across check-ins.
      </p>

      <div class="legend" data-test="trends-legend">
        <span class="legend__item legend__item--a" data-test="legend-partner-a">
          <span class="legend__swatch legend__swatch--a"></span> Partner A
        </span>
        <span class="legend__item legend__item--b" data-test="legend-partner-b">
          <span class="legend__swatch legend__swatch--b"></span> Partner B
        </span>
      </div>

      <div class="charts" data-test="trends-charts">
        @for (trend of trends(); track trend.quality.key) {
          <div class="chart-card" [attr.data-test]="'chart-card-' + trend.quality.key">
            <h2 class="chart-card__label" [attr.data-test]="'chart-label-' + trend.quality.key">
              {{ trend.quality.label }}
            </h2>
            <app-sparkline
              [dataA]="trend.dataA"
              [dataB]="trend.dataB"
              [labels]="trend.labels"
              [qualityKey]="trend.quality.key"
              [qualityLabel]="trend.quality.label"
              [thresholds]="thresholds"
            />
          </div>
        }
      </div>

      @if (alerts().length > 0) {
        <div class="alerts" data-test="trends-alerts">
          <h2 class="alerts__title" data-test="alerts-title">Divergence Alerts</h2>
          <p class="alerts__sub" data-test="alerts-subtitle">
            Qualities where your most recent scores differ by 3 or more.
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
        <button type="button" class="cta secondary" data-test="trends-new-checkin" (click)="onNewCheckin()">
          New Check-In
        </button>
      </div>
    </section>
  }

  @if (!loading() && !error() && !hasData()) {
    <section class="hero" data-test="trends-empty">
      <h1 class="title">No Trends Yet</h1>
      <p class="sub">Complete at least one check-in to see your trends.</p>
      <button type="button" class="cta primary" data-test="trends-start-checkin" (click)="onBack()">
        Start a Check-In
      </button>
    </section>
  }
</ion-content>
```

**Lifecycle**:
- `ngOnInit`: Set `loading(true)`. Call `checkinData.init()`. Call `checkinData.getCompletedSessions(10)`. If no sessions returned, set `loading(false)` and leave `trends` empty (triggers empty state). Otherwise, for each session call `checkinData.getScoresForSession(session.id)` to collect all quality scores. Shape the data into `TrendData[]` and `DivergenceAlertData[]`. Set `loading(false)`.

**Data shaping logic**:
```typescript
private async loadTrends(): Promise<void> {
  this.loading.set(true);
  this.error.set(null);

  try {
    await this.checkinData.init();
    const sessions = await this.checkinData.getCompletedSessions(10);

    if (sessions.length === 0) {
      this.loading.set(false);
      return;
    }

    // Collect all scores for all sessions
    const sessionScores: Map<string, CheckinQualityScore[]> = new Map();
    for (const session of sessions) {
      const scores = await this.checkinData.getScoresForSession(session.id);
      sessionScores.set(session.id, scores);
    }

    // Shape into TrendData per quality
    const trendData: TrendData[] = QUALITY_DEFINITIONS.map((quality) => {
      const dataA: number[] = [];
      const dataB: number[] = [];
      const labels: string[] = [];

      for (const session of sessions) {
        const scores = sessionScores.get(session.id) ?? [];
        const scoreA = scores.find(
          (s) => s.quality_key === quality.key && s.partner === 'A',
        )?.score ?? 0;
        const scoreB = scores.find(
          (s) => s.quality_key === quality.key && s.partner === 'B',
        )?.score ?? 0;

        dataA.push(scoreA);
        dataB.push(scoreB);
        labels.push(this.formatDateLabel(session.created_at));
      }

      return { quality, dataA, dataB, labels };
    });

    this.trends.set(trendData);
  } catch (e) {
    this.error.set(e instanceof Error ? e.message : 'Failed to load trends.');
  } finally {
    this.loading.set(false);
  }
}
```

**Computed alerts signal**:
```typescript
protected readonly alerts = computed<DivergenceAlertData[]>(() => {
  const trendData = this.trends();
  if (trendData.length === 0) return [];

  return trendData
    .filter((t) => t.dataA.length > 0)
    .map((t) => {
      const lastA = t.dataA[t.dataA.length - 1];
      const lastB = t.dataB[t.dataB.length - 1];
      const delta = Math.abs(lastA - lastB);
      return {
        qualityKey: t.quality.key,
        qualityLabel: t.quality.label,
        scoreA: lastA,
        scoreB: lastB,
        delta,
      };
    })
    .filter((a) => a.delta >= DIVERGENCE_DELTA);
});
```

**Date label formatting**:
```typescript
private formatDateLabel(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(date);
}
```

**Threshold constant**:
```typescript
protected readonly thresholds = [THRESHOLD_CONCERNING, THRESHOLD_HEALTHY]; // [5, 7]
```

**Methods**:
- `onBack(): void` -- navigates to `/checkin`.
- `onNewCheckin(): void` -- navigates to `/checkin`.

Both navigate to the check-in home. Distinguished only for semantic clarity in the template and for test targeting.

**Standalone, OnPush, signals.**

### 4.2 SparklineComponent

**File**: `src/app/features/checkin/components/sparkline.component.ts`

**Selector**: `app-sparkline`

**Inputs**:
- `dataA: InputSignal<number[]>` (required) -- Partner A scores array, oldest-first
- `dataB: InputSignal<number[]>` (required) -- Partner B scores array, oldest-first
- `labels: InputSignal<string[]>` (required) -- Date labels for the x-axis
- `qualityKey: InputSignal<QualityKey>` (required) -- Used for `data-test` attribute
- `qualityLabel: InputSignal<string>` (required) -- Used for `aria-label`
- `thresholds: InputSignal<number[]>` (required) -- Y-axis values to draw dashed lines at (e.g., `[5, 7]`)

**Outputs**: None. Pure presentational.

**SVG rendering strategy**:

The sparkline is a fixed-aspect-ratio SVG with `viewBox="0 0 300 100"`. The SVG element uses `width="100%"` and `preserveAspectRatio="xMidYMid meet"` for responsive scaling within its parent card.

**Coordinate system**:
- The usable plot area has padding: `left=30, right=10, top=10, bottom=20` to accommodate y-axis labels and x-axis date labels.
- Plot width: `300 - 30 - 10 = 260` (from x=30 to x=290)
- Plot height: `100 - 10 - 20 = 70` (from y=10 to y=80)
- Y-axis range maps score 1 to y=80 (bottom) and score 10 to y=10 (top)
- X-axis distributes data points evenly across the plot width

**Computed signals**:
```typescript
protected readonly pointsA = computed<string>(() => {
  return this.computePolylinePoints(this.dataA());
});

protected readonly pointsB = computed<string>(() => {
  return this.computePolylinePoints(this.dataB());
});

protected readonly circlesA = computed<{ cx: number; cy: number }[]>(() => {
  return this.computeCircles(this.dataA());
});

protected readonly circlesB = computed<{ cx: number; cy: number }[]>(() => {
  return this.computeCircles(this.dataB());
});

protected readonly thresholdLines = computed<{ y: number; label: string }[]>(() => {
  return this.thresholds().map((t) => ({
    y: this.scoreToY(t),
    label: t.toString(),
  }));
});

protected readonly ariaLabel = computed<string>(() => {
  const dataA = this.dataA();
  const dataB = this.dataB();
  const label = this.qualityLabel();
  if (dataA.length === 0) return `${label}: no data`;
  const lastA = dataA[dataA.length - 1];
  const lastB = dataB[dataB.length - 1];
  return `${label}: Partner A latest ${lastA.toFixed(1)}, Partner B latest ${lastB.toFixed(1)}, ${dataA.length} sessions`;
});
```

**Scale functions**:
```typescript
// Constants
private readonly PADDING = { left: 30, right: 10, top: 10, bottom: 20 };
private readonly VIEW_WIDTH = 300;
private readonly VIEW_HEIGHT = 100;
private readonly SCORE_MIN = 1;
private readonly SCORE_MAX = 10;

private get plotWidth(): number {
  return this.VIEW_WIDTH - this.PADDING.left - this.PADDING.right;
}

private get plotHeight(): number {
  return this.VIEW_HEIGHT - this.PADDING.top - this.PADDING.bottom;
}

/** Map a score (1-10) to a y coordinate (top = high score, bottom = low score). */
private scoreToY(score: number): number {
  const clamped = Math.max(this.SCORE_MIN, Math.min(this.SCORE_MAX, score));
  const ratio = (clamped - this.SCORE_MIN) / (this.SCORE_MAX - this.SCORE_MIN);
  return this.PADDING.top + this.plotHeight * (1 - ratio);
}

/** Map a data index to an x coordinate (evenly distributed). */
private indexToX(index: number, total: number): number {
  if (total <= 1) return this.PADDING.left + this.plotWidth / 2;
  return this.PADDING.left + (index / (total - 1)) * this.plotWidth;
}

/** Build a polyline points string from a data array. */
private computePolylinePoints(data: number[]): string {
  return data
    .map((score, i) => {
      const x = this.indexToX(i, data.length);
      const y = this.scoreToY(score);
      return `${x},${y}`;
    })
    .join(' ');
}

/** Build circle coordinate arrays from a data array. */
private computeCircles(data: number[]): { cx: number; cy: number }[] {
  return data.map((score, i) => ({
    cx: this.indexToX(i, data.length),
    cy: this.scoreToY(score),
  }));
}
```

**Template Structure**:
```
<svg
  [attr.viewBox]="'0 0 ' + VIEW_WIDTH + ' ' + VIEW_HEIGHT"
  width="100%"
  preserveAspectRatio="xMidYMid meet"
  [attr.aria-label]="ariaLabel()"
  role="img"
  [attr.data-test]="'sparkline-' + qualityKey()"
  class="sparkline"
>
  <!-- Y-axis labels -->
  <text x="2" [attr.y]="scoreToY(10)" class="axis-label" dominant-baseline="middle">10</text>
  <text x="2" [attr.y]="scoreToY(5)" class="axis-label" dominant-baseline="middle">5</text>
  <text x="2" [attr.y]="scoreToY(1)" class="axis-label" dominant-baseline="middle">1</text>

  <!-- Threshold dashed lines -->
  @for (line of thresholdLines(); track line.label) {
    <line
      [attr.x1]="PADDING.left"
      [attr.y1]="line.y"
      [attr.x2]="VIEW_WIDTH - PADDING.right"
      [attr.y2]="line.y"
      class="threshold-line"
      [attr.data-test]="'threshold-' + line.label"
    />
  }

  <!-- Partner A polyline -->
  @if (pointsA()) {
    <polyline
      [attr.points]="pointsA()"
      class="line line--a"
      data-test="line-partner-a"
      fill="none"
    />
  }

  <!-- Partner B polyline -->
  @if (pointsB()) {
    <polyline
      [attr.points]="pointsB()"
      class="line line--b"
      data-test="line-partner-b"
      fill="none"
    />
  }

  <!-- Partner A circle markers -->
  @for (circle of circlesA(); track $index) {
    <circle
      [attr.cx]="circle.cx"
      [attr.cy]="circle.cy"
      r="3"
      class="marker marker--a"
      [attr.data-test]="'marker-a-' + $index"
    />
  }

  <!-- Partner B circle markers -->
  @for (circle of circlesB(); track $index) {
    <circle
      [attr.cx]="circle.cx"
      [attr.cy]="circle.cy"
      r="3"
      class="marker marker--b"
      [attr.data-test]="'marker-b-' + $index"
    />
  }

  <!-- X-axis date labels (show first, middle, last to avoid crowding) -->
  @for (label of xAxisLabels(); track $index) {
    <text
      [attr.x]="label.x"
      [attr.y]="VIEW_HEIGHT - 4"
      class="axis-label axis-label--x"
      text-anchor="middle"
      [attr.data-test]="'x-label-' + $index"
    >
      {{ label.text }}
    </text>
  }
</svg>
```

**X-axis label strategy** (to avoid visual crowding):
```typescript
protected readonly xAxisLabels = computed<{ x: number; text: string }[]>(() => {
  const allLabels = this.labels();
  if (allLabels.length === 0) return [];
  if (allLabels.length <= 3) {
    // Show all labels
    return allLabels.map((text, i) => ({
      x: this.indexToX(i, allLabels.length),
      text,
    }));
  }
  // Show first, middle, last
  const first = 0;
  const mid = Math.floor(allLabels.length / 2);
  const last = allLabels.length - 1;
  return [
    { x: this.indexToX(first, allLabels.length), text: allLabels[first] },
    { x: this.indexToX(mid, allLabels.length), text: allLabels[mid] },
    { x: this.indexToX(last, allLabels.length), text: allLabels[last] },
  ];
});
```

**Single data point handling**: When there is only one session, the polyline degenerates to a single point. The circle marker still renders. The polyline `points` attribute will be a single `"x,y"` value which renders nothing visible -- the circle marker at that coordinate is the visual. This is acceptable.

**Standalone, OnPush, signals. No lifecycle hooks -- pure computed rendering.**

### 4.3 DivergenceAlertComponent

**File**: `src/app/features/checkin/components/divergence-alert.component.ts`

**Selector**: `app-divergence-alert`

**Inputs**:
- `qualityKey: InputSignal<QualityKey>` (required) -- for `data-test` attribute
- `qualityLabel: InputSignal<string>` (required) -- quality display name
- `scoreA: InputSignal<number>` (required) -- Partner A score
- `scoreB: InputSignal<number>` (required) -- Partner B score
- `delta: InputSignal<number>` (required) -- absolute difference

**Outputs**: None. Pure presentational.

**Computed signals**:
```typescript
protected readonly message = computed<string>(() => {
  const label = this.qualityLabel();
  const a = this.scoreA().toFixed(1);
  const b = this.scoreB().toFixed(1);
  return `You scored ${label} ${a}, partner scored ${b}`;
});
```

**Template Structure**:
```
<div
  class="alert"
  [attr.data-test]="'divergence-alert-' + qualityKey()"
  role="listitem"
>
  <div class="alert__icon" aria-hidden="true">
    <svg viewBox="0 0 24 24" class="alert__icon-svg">
      <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
        stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div class="alert__content">
    <span class="alert__quality" [attr.data-test]="'alert-quality-' + qualityKey()">
      {{ qualityLabel() }}
    </span>
    <span class="alert__message" [attr.data-test]="'alert-message-' + qualityKey()">
      {{ message() }}
    </span>
    <span class="alert__delta" [attr.data-test]="'alert-delta-' + qualityKey()">
      Gap: {{ delta().toFixed(1) }}
    </span>
  </div>
</div>
```

**Standalone, OnPush, signals. No lifecycle hooks -- pure presentational.**

### 4.4 CheckinResultsComponent Modifications

**File**: `src/app/features/checkin/components/checkin-results.component.ts`

Add a "View Trends" button to the existing actions area, placed before the "New Check-In" button:

```html
<div class="actions" data-test="results-actions">
  <button
    type="button"
    class="cta primary"
    data-test="view-trends-btn"
    (click)="onViewTrends()"
  >
    View Trends
  </button>
  <button
    type="button"
    class="cta secondary"
    data-test="new-checkin-btn"
    (click)="onNewCheckin()"
  >
    New Check-In
  </button>
</div>
```

The "View Trends" button uses the `primary` CTA style (accent-warm) since it's the higher-value action. "New Check-In" becomes `secondary`.

New method:
```typescript
/** Navigate to the trends view. */
async onViewTrends(): Promise<void> {
  await this.router.navigate(['/checkin/trends']);
}
```

The existing `Router` injection is already available in the component. No new imports needed.

---

## 5. Data Flow

```
                    CheckinTrendsComponent (container)
                              |
                    ngOnInit → loadTrends()
                              |
                    ┌─────────┴──────────────────────────┐
                    |                                      |
          CheckinDataService                    CheckinDataService
          .getCompletedSessions(10)             .getScoresForSession(id)
                    |                                x N sessions
                    v                                      |
                 SQLite                                    v
            checkin_session                            SQLite
          WHERE status='complete'                checkin_quality_score
          ORDER BY created_at ASC                WHERE session_id = ?
              LIMIT 10                                     |
                    |                                      |
                    └─────────┬────────────────────────────┘
                              |
                    shape into TrendData[] + DivergenceAlertData[]
                              |
                    ┌─────────┴─────────────┐
                    |                         |
            SparklineComponent       DivergenceAlertComponent
            (per quality x 4)         (per alert, 0-4)
                    |                         |
            SVG polylines +           Plain-language text +
            circle markers +          delta badge
            threshold lines
```

**Sequence -- happy path**:

1. User navigates to `/checkin/trends` (via "View Trends" button in results, or directly).
2. `CheckinTrendsComponent.ngOnInit()` calls `loadTrends()`.
3. `loadTrends()` calls `checkinData.getCompletedSessions(10)` -- returns up to 10 sessions, oldest-first.
4. For each session, calls `checkinData.getScoresForSession(session.id)` -- returns 8 quality scores (4 qualities x 2 partners).
5. Maps the collected data into `TrendData[]` (one per quality, each containing `dataA[]`, `dataB[]`, `labels[]`).
6. Sets `this.trends` signal, which triggers computed `alerts` signal.
7. Template renders four `<app-sparkline>` components and 0-4 `<app-divergence-alert>` components.

**Edge cases**:
- **Zero completed sessions**: `getCompletedSessions(10)` returns `[]`. The `hasData` computed signal is false. Template renders the empty state.
- **One completed session**: Single data point. Sparkline shows one marker per partner per quality. Polyline is invisible (single point). Divergence alerts still computed.
- **Missing partner data**: If a quality score is missing for a partner (should not happen with the current data service, but defensively), the score defaults to 0. This would show as a data point at the bottom of the chart.
- **Service failure**: Error signal catches the exception and displays error state with back button.

---

## 6. SVG Rendering

### ViewBox and Coordinate System

```
viewBox="0 0 300 100"

  0                                                     300
  ┌─────────────────────────────────────────────────────────┐
  │  y-labels  │              PLOT AREA                  │  │ 0
  │            │                                         │  │
  │   10 ──── │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │  │ 10 (top padding)
  │            │                                         │  │
  │            │  ●───────●                              │  │  (Partner A line)
  │            │       ●───────●                         │  │  (Partner B line)
  │            │                                         │  │
  │    7 ──── │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │  │  (threshold: healthy)
  │            │                                         │  │
  │    5 ──── │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │  │  (threshold: concerning)
  │            │                                         │  │
  │    1 ──── │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │  │ 80 (bottom of plot)
  │            │                                         │  │
  │            │  Apr 12        Apr 15        Apr 18     │  │ 96 (x-axis labels)
  └─────────────────────────────────────────────────────────┘ 100
  0           30                                       290
              │← ─ ─ ─ ─ ─  260px plot width ─ ─ ─ ─ →│
```

### Padding Constants

| Edge | Pixels | Purpose |
|------|--------|---------|
| Left | 30 | Y-axis score labels (10, 5, 1) |
| Right | 10 | Breathing room for rightmost marker |
| Top | 10 | Breathing room for score-10 marker |
| Bottom | 20 | X-axis date labels |

### Score-to-Y Mapping

Formula: `y = PADDING.top + plotHeight * (1 - (score - 1) / 9)`

| Score | Y coordinate |
|-------|-------------|
| 10 | 10.0 (top of plot) |
| 7 | 33.3 (healthy threshold line) |
| 5 | 48.9 (concerning threshold line) |
| 1 | 80.0 (bottom of plot) |

The range is `[1, 10]` (not `[0, 10]`) because scores are always 1-10 from the rating interface.

### Index-to-X Mapping

Formula: `x = PADDING.left + (index / (total - 1)) * plotWidth`

For 10 data points (indices 0-9):
| Index | X coordinate |
|-------|-------------|
| 0 | 30.0 (leftmost) |
| 1 | 58.9 |
| 4 | 145.6 (near center) |
| 9 | 290.0 (rightmost) |

For 1 data point: centered at `x = PADDING.left + plotWidth / 2 = 160`.

### Polyline Points String

For Partner A scores `[8, 7, 6, 8, 9]` across 5 sessions:

```
points="30,17.8  95,25.6  160,33.3  225,17.8  290,10"
```

Each pair is `x,y` separated by spaces. The `<polyline>` SVG element connects them with straight line segments.

### Circle Markers

Radius: 3px. Same coordinates as the polyline points. Filled with the partner's accent color. These serve as the primary data point indicators, especially for single-session data where the polyline is invisible.

### Threshold Lines

Dashed horizontal lines at scores 5 and 7:
```html
<line x1="30" y1="48.9" x2="290" y2="48.9" class="threshold-line" />
<line x1="30" y1="33.3" x2="290" y2="33.3" class="threshold-line" />
```

CSS: `stroke-dasharray: 4,4` for a subtle dashed pattern.

---

## 7. Styling

### CheckinTrendsComponent Styles

```css
:host {
  --world-bg: var(--page-bg);
  --line-a: var(--accent-warm);
  --line-b: var(--accent-cool);
  --threshold-line-color: var(--hairline);

  display: block;
  background: var(--world-bg);
  color: var(--text-primary);
  font-family: var(--font-body);
}

:host ::ng-deep ion-content.trends-content {
  --background: var(--world-bg);
  --padding-start: 0;
  --padding-end: 0;
  --padding-top: 0;
  --padding-bottom: 0;
}

.bar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--page-pad);
  padding-top: calc(var(--sp-4) + env(safe-area-inset-top));
}

.back-btn {
  background: none;
  border: none;
  padding: var(--sp-1);
  cursor: pointer;
  color: var(--text-primary);
  -webkit-tap-highlight-color: transparent;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  transition: background var(--t-press) var(--ease-out);
}

.back-btn:active {
  background: var(--accent-warm-tint);
}

.back-btn svg {
  width: 20px;
  height: 20px;
}

.eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--text-muted);
}

.hero {
  padding: var(--sp-6) var(--page-pad);
  min-height: 66vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--sp-4);
}

.trends {
  padding: var(--sp-6) var(--page-pad);
  padding-bottom: calc(var(--sp-12) + env(safe-area-inset-bottom));
  max-width: 480px;
  margin: 0 auto;
}

.title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 500;
  line-height: 1.08;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0 0 var(--sp-2);
  text-align: center;
}

.sub {
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0 0 var(--sp-6);
  text-align: center;
}
```

### Legend Styling

```css
.legend {
  display: flex;
  justify-content: center;
  gap: var(--sp-6);
  margin-bottom: var(--sp-6);
}

.legend__item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.legend__swatch {
  width: 16px;
  height: 3px;
  border-radius: 2px;
}

.legend__swatch--a {
  background: var(--line-a);
}

.legend__swatch--b {
  background: var(--line-b);
}
```

### Chart Card Styling

```css
.charts {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.chart-card {
  background: var(--surface);
  border-radius: var(--r-md);
  padding: var(--sp-4);
  box-shadow: var(--shadow-soft);
  border: 1px solid var(--hairline);
}

.chart-card__label {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 500;
  font-style: italic;
  color: var(--text-primary);
  margin: 0 0 var(--sp-3);
}
```

### SparklineComponent Styles

```css
:host {
  display: block;
}

.sparkline {
  width: 100%;
  height: auto;
}

.line--a {
  stroke: var(--line-a, var(--accent-warm));
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

.line--b {
  stroke: var(--line-b, var(--accent-cool));
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

.marker--a {
  fill: var(--line-a, var(--accent-warm));
}

.marker--b {
  fill: var(--line-b, var(--accent-cool));
}

.threshold-line {
  stroke: var(--threshold-line-color, var(--hairline));
  stroke-width: 1;
  stroke-dasharray: 4, 4;
}

.axis-label {
  font-family: var(--font-body, sans-serif);
  font-size: 8px;
  fill: var(--text-muted);
  user-select: none;
}

.axis-label--x {
  font-size: 7px;
}
```

### DivergenceAlertComponent Styles

```css
:host {
  display: block;
}

.alert {
  display: flex;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  background: color-mix(in srgb, var(--danger) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--danger) 25%, transparent);
  border-radius: var(--r-sm);
  margin-bottom: var(--sp-3);
}

.alert__icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  color: var(--danger);
  margin-top: 2px;
}

.alert__icon-svg {
  width: 100%;
  height: 100%;
}

.alert__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.alert__quality {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  font-style: italic;
  color: var(--text-primary);
}

.alert__message {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.alert__delta {
  font-size: 12px;
  font-weight: 700;
  color: var(--danger);
}
```

### Alerts Section Styling (in CheckinTrendsComponent)

```css
.alerts {
  margin-top: var(--sp-8);
}

.alerts__title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 var(--sp-2);
}

.alerts__sub {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 var(--sp-4);
}
```

### Action Buttons (in CheckinTrendsComponent)

Reuse the same CTA pattern from the results component:

```css
.actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-3);
  margin-top: var(--sp-8);
}

.cta {
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
}

.cta:active { transform: scale(0.97); }

.cta.primary {
  background: var(--accent-warm);
  color: var(--on-accent-warm);
  box-shadow: 0 8px 32px -8px color-mix(in srgb, var(--accent-warm) 55%, transparent);
}

.cta.secondary {
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--hairline);
  box-shadow: var(--shadow-soft);
}

.error {
  color: var(--danger);
  font-size: 14px;
  margin: 0;
}

@media (prefers-reduced-motion: reduce) {
  .cta { transition: none; }
}
```

### Color Summary

| Element | Token | Light | Dark |
|---------|-------|-------|------|
| Partner A line + markers | `--accent-warm` | `#A6510A` | `#E8A85C` |
| Partner B line + markers | `--accent-cool` | `#5B6CC0` | `#818CF8` |
| Threshold dashed lines | `--hairline` | `rgba(26,26,26,0.12)` | `rgba(245,245,245,0.10)` |
| Chart card background | `--surface` | `#FFFFFF` | `#141414` |
| Divergence alert bg | `--danger` at 8% mix | subtle red tint | subtle red tint |
| Divergence alert border | `--danger` at 25% mix | red border | red border |
| Delta text | `--danger` | `#C93B3B` | `#EB445A` |

---

## 8. Navigation

### Route Addition

Add a new child route under the existing `/checkin` parent in `app.routes.ts`:

```typescript
{
  path: 'checkin',
  children: [
    {
      path: '',
      loadComponent: () =>
        import('./pages/checkin/checkin.page').then(m => m.CheckinPage),
    },
    {
      path: 'waiting/:sessionId',
      loadComponent: () =>
        import('./features/checkin/components/checkin-waiting.component').then(m => m.CheckinWaitingComponent),
    },
    {
      path: 'results/:sessionId',
      loadComponent: () =>
        import('./features/checkin/components/checkin-results.component').then(m => m.CheckinResultsComponent),
    },
    {
      path: 'trends',                  // <-- NEW
      loadComponent: () =>
        import('./features/checkin/components/checkin-trends.component').then(m => m.CheckinTrendsComponent),
    },
  ],
},
```

The `trends` route has no params. Trend data spans all completed sessions -- it is not tied to a specific session ID.

### Navigation Paths

```
[Results view: /checkin/results/:sessionId]
    |
    ├── [View Trends button]  →  router.navigate(['/checkin/trends'])
    │                              → CheckinTrendsComponent
    │
    └── [New Check-In button] →  router.navigate(['/checkin'])
                                   → CheckinPage

[Trends view: /checkin/trends]
    |
    ├── [Back arrow button]   →  router.navigate(['/checkin'])
    │                              → CheckinPage
    │
    └── [New Check-In button] →  router.navigate(['/checkin'])
                                   → CheckinPage
```

### Entry Points to Trends

1. **Primary**: "View Trends" button in `CheckinResultsComponent` -- added by this task.
2. **Direct URL**: User navigates to `/checkin/trends` directly (e.g., browser history). The component self-loads data; no prior navigation context required.

### Why Not a Tab on the Check-In Home Screen

The epic mentions "accessible from the check-in home screen as a 'Trends' tab or toggle." The architecture routes trends through the results view instead. Rationale:

1. The check-in home (`CheckinPage`) manages session creation flow -- it should not be cluttered with trend navigation when the user's primary intent is starting or continuing a check-in.
2. Trends are a reward for completing a check-in. Placing the button in results creates a natural flow: complete check-in -> see results -> explore trends.
3. Direct URL access (`/checkin/trends`) still works for users who want to skip straight to trends.

If user testing shows people want trends from the home screen, a "View Past Trends" secondary button can be added to `CheckinPage` in Task 6 or a follow-up task. This is additive and does not block.

---

## 9. Tests

Framework: Jasmine + Karma. Component tests use `TestBed` with standalone component imports. Mock `CheckinDataService` with `jasmine.createSpyObj`. Use `query()` / `queryAll()` helper pattern established in existing tests.

### 9.1 `checkin-data.service.spec.ts` -- Additions (3 new tests)

Add to the existing spec file:

```typescript
// ── getCompletedSessions ────────────────────────────────────────

it('getCompletedSessions_returnsSessions_orderedOldestFirst', async () => {
  // Mock: two complete sessions
  sqliteSpy.query.and.resolveTo({
    values: [
      fakeSession({ id: 'sess-old', created_at: '2026-04-12T10:00:00.000Z', status: 'complete' }),
      fakeSession({ id: 'sess-new', created_at: '2026-04-18T10:00:00.000Z', status: 'complete' }),
    ],
  });

  const result = await service.getCompletedSessions(10);

  expect(result.length).toBe(2);
  expect(result[0].id).toBe('sess-old');
  expect(result[1].id).toBe('sess-new');
});

it('getCompletedSessions_respectsLimit', async () => {
  sqliteSpy.query.and.resolveTo({ values: [] });

  await service.getCompletedSessions(5);

  // Verify the SQL statement includes LIMIT 5
  const callArgs = sqliteSpy.query.calls.mostRecent().args[0];
  expect(callArgs.statement).toContain('LIMIT');
  expect(callArgs.values).toContain(5);
});

it('getCompletedSessions_noSessions_returnsEmptyArray', async () => {
  sqliteSpy.query.and.resolveTo({ values: [] });

  const result = await service.getCompletedSessions(10);

  expect(result).toEqual([]);
});
```

### 9.2 `sparkline.component.spec.ts` -- New file (10 tests)

```typescript
// Test setup uses a test host to supply required InputSignals
@Component({
  standalone: true,
  imports: [SparklineComponent],
  template: `
    <app-sparkline
      [dataA]="dataA()"
      [dataB]="dataB()"
      [labels]="labels()"
      [qualityKey]="qualityKey()"
      [qualityLabel]="qualityLabel()"
      [thresholds]="thresholds()"
    />
  `,
})
class TestHostComponent {
  readonly dataA = signal<number[]>([8, 7, 6, 8, 9]);
  readonly dataB = signal<number[]>([6, 5, 7, 6, 7]);
  readonly labels = signal<string[]>(['Apr 12', 'Apr 13', 'Apr 14', 'Apr 15', 'Apr 16']);
  readonly qualityKey = signal<QualityKey>('communication');
  readonly qualityLabel = signal('Communication Honesty');
  readonly thresholds = signal<number[]>([5, 7]);
}
```

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_svgElement` | `data-test="sparkline-communication"` SVG element present |
| 2 | `renders_partnerAPolyline` | `data-test="line-partner-a"` polyline element present with non-empty `points` attribute |
| 3 | `renders_partnerBPolyline` | `data-test="line-partner-b"` polyline element present with non-empty `points` attribute |
| 4 | `renders_circleMarkersForPartnerA` | 5 elements matching `[data-test^="marker-a-"]` |
| 5 | `renders_circleMarkersForPartnerB` | 5 elements matching `[data-test^="marker-b-"]` |
| 6 | `renders_twoThresholdLines` | 2 elements matching `.threshold-line` |
| 7 | `renders_yAxisLabels` | Text elements containing "10", "5", "1" |
| 8 | `renders_xAxisLabels` | At least 1 element matching `[data-test^="x-label-"]` |
| 9 | `ariaLabel_containsLatestScores` | SVG `aria-label` contains "Partner A latest 9.0" and "Partner B latest 7.0" |
| 10 | `emptyData_rendersNoPolylines` | When `dataA` and `dataB` are `[]`, no polyline elements rendered |

### 9.3 `divergence-alert.component.spec.ts` -- New file (5 tests)

```typescript
// Test host
@Component({
  standalone: true,
  imports: [DivergenceAlertComponent],
  template: `
    <app-divergence-alert
      [qualityKey]="qualityKey()"
      [qualityLabel]="qualityLabel()"
      [scoreA]="scoreA()"
      [scoreB]="scoreB()"
      [delta]="delta()"
    />
  `,
})
class TestHostComponent {
  readonly qualityKey = signal<QualityKey>('communication');
  readonly qualityLabel = signal('Communication Honesty');
  readonly scoreA = signal(8);
  readonly scoreB = signal(4);
  readonly delta = signal(4);
}
```

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_alertElement` | `data-test="divergence-alert-communication"` element present |
| 2 | `renders_qualityLabel` | `data-test="alert-quality-communication"` contains "Communication Honesty" |
| 3 | `renders_plainLanguageMessage` | `data-test="alert-message-communication"` contains "You scored Communication Honesty 8.0, partner scored 4.0" |
| 4 | `renders_deltaValue` | `data-test="alert-delta-communication"` contains "Gap: 4.0" |
| 5 | `renders_warningIcon` | `.alert__icon` element present with SVG child |

### 9.4 `checkin-trends.component.spec.ts` -- New file (14 tests)

```typescript
// Mock data factory
function fakeSessions(count: number): CheckinSession[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `sess-${i}`,
    created_at: `2026-04-${String(10 + i).padStart(2, '0')}T10:00:00.000Z`,
    status: 'complete' as const,
    partner_a_submitted: 1,
    partner_b_submitted: 1,
  }));
}

function fakeScoresForSession(sessionId: string): CheckinQualityScore[] {
  return [
    { id: `${sessionId}-1`, session_id: sessionId, partner: 'A', quality_key: 'communication', score: 8 },
    { id: `${sessionId}-2`, session_id: sessionId, partner: 'B', quality_key: 'communication', score: 5 },
    { id: `${sessionId}-3`, session_id: sessionId, partner: 'A', quality_key: 'respect', score: 7 },
    { id: `${sessionId}-4`, session_id: sessionId, partner: 'B', quality_key: 'respect', score: 7 },
    { id: `${sessionId}-5`, session_id: sessionId, partner: 'A', quality_key: 'prioritization', score: 6 },
    { id: `${sessionId}-6`, session_id: sessionId, partner: 'B', quality_key: 'prioritization', score: 5 },
    { id: `${sessionId}-7`, session_id: sessionId, partner: 'A', quality_key: 'viability', score: 9 },
    { id: `${sessionId}-8`, session_id: sessionId, partner: 'B', quality_key: 'viability', score: 4 },
  ];
}
// Communication: delta=3 (divergent), Respect: delta=0, Prioritization: delta=1, Viability: delta=5 (divergent)
```

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_trendsPage` | `data-test="checkin-trends-page"` present after data loads |
| 2 | `renders_fourChartCards` | 4 elements matching `[data-test^="chart-card-"]` |
| 3 | `renders_chartLabels` | `data-test="chart-label-communication"` contains "Communication Honesty", etc. for all 4 |
| 4 | `renders_sparklinePerQuality` | 4 elements matching `[data-test^="sparkline-"]` |
| 5 | `renders_legend` | `data-test="legend-partner-a"` and `data-test="legend-partner-b"` present |
| 6 | `renders_divergenceAlerts_whenDeltaGte3` | `data-test="divergence-alert-communication"` and `data-test="divergence-alert-viability"` present (delta >= 3) |
| 7 | `noDivergenceAlerts_whenDeltaLt3` | `data-test="divergence-alert-respect"` and `data-test="divergence-alert-prioritization"` absent (delta < 3) |
| 8 | `renders_alertsTitle_whenAlertsExist` | `data-test="alerts-title"` contains "Divergence Alerts" |
| 9 | `emptyState_whenNoSessions` | When `getCompletedSessions` returns `[]`, `data-test="trends-empty"` present |
| 10 | `errorState_whenServiceFails` | When `getCompletedSessions` rejects, `data-test="trends-error"` present |
| 11 | `loadingState_initially` | Before async completes, `data-test="trends-loading"` present |
| 12 | `backButton_navigatesToCheckin` | Click `data-test="trends-back-btn"` -> router navigated to `['/checkin']` |
| 13 | `title_isPresent` | `data-test="trends-title"` contains "Score Trends" |
| 14 | `alerts_usePlainLanguage` | `data-test="alert-message-communication"` contains "You scored Communication Honesty 8.0, partner scored 5.0" |

### 9.5 `checkin-results.component.spec.ts` -- Additions (2 new tests)

Add to the existing spec file:

| # | Test name | Assertion |
|---|-----------|-----------|
| 1 | `renders_viewTrendsButton` | `data-test="view-trends-btn"` element present with text "View Trends" |
| 2 | `viewTrendsButton_navigatesToTrends` | Click `data-test="view-trends-btn"` -> `routerSpy.navigate` called with `['/checkin/trends']` |

### Test Count Summary

| Spec file | Existing | New | Total |
|-----------|----------|-----|-------|
| `checkin-data.service.spec.ts` | ~17 | 3 | ~20 |
| `sparkline.component.spec.ts` | -- | 10 | 10 |
| `divergence-alert.component.spec.ts` | -- | 5 | 5 |
| `checkin-trends.component.spec.ts` | -- | 14 | 14 |
| `checkin-results.component.spec.ts` | ~18 | 2 | ~20 |
| **Total** | **~35** | **34** | **~69** |

---

## 10. Out of Scope

This section explicitly lists what Task 5 does NOT do. These are either handled by other tasks or deferred entirely.

| Item | Reason |
|------|--------|
| Session expiry (48h auto-close) | Task 6. Trends only render sessions with `status = 'complete'`. Expired sessions are excluded by the query. |
| Interactive chart features (zoom, pan, tap-to-highlight) | Not needed for v1. Four small sparklines are scannable at a glance. Interactivity adds complexity without clear value at this session count. |
| Animated chart drawing (line reveal, marker pop-in) | Optional polish. Could be added in Task 6 or a follow-up. For now, charts render statically on load. |
| Session history list / "View all sessions" | Not in scope. Trends show aggregated data. Individual session results are accessible via the results route. |
| Export or share trend data | Out of epic scope entirely. No print, screenshot, or share functionality. |
| Weighted or rolling-average trend lines | Simple point-to-point polylines. No smoothing, no moving averages. The raw data is the value. |
| Threshold annotations (text labels on the dashed lines) | The dashed lines at 5 and 7 are self-explanatory given the y-axis labels. Text annotations would crowd the 300x100 viewBox. |
| Trend summary / AI insights | Out of epic scope. No generated commentary. The charts and alerts speak for themselves. |
| Tab navigation on the check-in home screen | Trends are accessed from results. Adding a tab to the home screen is a UX decision that can be revisited after user feedback. |
| Cloud sync / multi-device trend aggregation | Out of epic scope. Single-device, local SQLite only. |
| Custom date range selection | Trends always show the last 10 sessions. No date picker or "show last N" control. |
| Responsive breakpoints for larger screens (iPad, desktop) | The `viewBox` SVG scales automatically. The `max-width: 480px` container keeps charts readable on larger screens. No tablet-specific layout. |
| Accessibility beyond ARIA labels | Each sparkline has an `aria-label` with the quality name and latest scores. VoiceOver announces chart content. Full data table alternative (for screen readers who need every data point) is deferred. |
| E2E / integration tests | Unit tests only. E2E belongs to a separate testing effort. |
