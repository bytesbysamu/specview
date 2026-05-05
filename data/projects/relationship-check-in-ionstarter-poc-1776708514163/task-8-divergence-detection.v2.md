# Task 8: Divergence Detection + Alerts

## 1. Purpose

Detect sustained scoring gaps between partners by computing per-quality average divergence over a rolling window of the last 3 completed sessions. When |avgA - avgB| exceeds 2.0 points, surface a visual warning marker inline on the trends page -- a warning icon next to the quality name and explanatory text. These are not modal alerts or push notifications; they are passive visual indicators that appear within the existing trends view.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 0.5 day |
| **Dependencies** | Task 7 (trends + sparklines — provides the trends page and data loading) |
| **Parallel with** | None — terminal task |
| **Blocks** | Nothing |
| **Priority** | Low |

---

## 3. Context

### Why this task exists

Task 7's trends page already flags single-session divergence (delta >= 3 for the most recent session only) via `DivergenceAlertComponent`. However, a single bad session can be noise. This task adds **sustained divergence detection**: averaging over a configurable window (default 3 sessions) to surface only persistent gaps. This gives couples a meaningful signal that a quality dimension is chronically misaligned, not just a one-off.

### What already exists

- `CheckinTrendsComponent` loads quality scores for all sessions and already computes single-session divergence alerts (see `alerts` computed signal).
- `DivergenceAlertComponent` renders individual alert items (quality label, scores, delta, severity).
- `DIVERGENCE_DELTA = 3` is the existing single-session threshold (defined in `checkin.model.ts`).
- `CheckinDataService.getCompletedSessions(limit)` returns sessions oldest-first.
- `CheckinDataService.getScoresForSession(sessionId)` returns `CheckinQualityScore[]`.

### Key distinction from existing alerts

| Existing (Task 7) | New (Task 8) |
|---|---|
| Looks at the **most recent session only** | Averages over **last N sessions** (default 3) |
| Threshold: `DIVERGENCE_DELTA = 3` (absolute single-session gap) | Threshold: `2.0` (averaged gap over window) |
| Rendered in a separate "Divergence Alerts" section below charts | Rendered **inline next to the quality label** in each chart card |
| Uses `DivergenceAlertComponent` | Uses a new warning icon + inline text treatment |

### Trade-offs

- **Pure utility function, no service**: The detection logic is stateless and deterministic — a pure function is the right abstraction level.
- **Visual-only, no modals**: Per spec, divergence indicators are passive. Users notice them while reviewing trends; the app does not interrupt flow.
- **Threshold 2.0 (not 3)**: The sustained threshold is intentionally lower than the single-session threshold because averaging smooths spikes. A sustained 2.0+ gap over 3 sessions is as concerning as a single 3.0+ spike.
- **Window of 3 sessions (not configurable from UI)**: The window is a parameter in code but not user-configurable in V1. Hardcoded default is fine.

### Rejected alternatives

- **Replace the existing single-session alerts**: No. Both indicators serve different purposes. Single-session alerts catch acute spikes; sustained alerts catch chronic drift.
- **Implement as a service**: Overkill. The function takes data in, returns results — no state, no side effects, no DI needed.
- **Add to a global notification system**: Out of scope. Visual indicators on the trends page only.

---

## 4. Pre-flight

Run from the workspace root (`/workspace`):

```bash
# 1. Verify the project builds cleanly
npm run build

# 2. Verify tests pass
npx ng test --no-watch --browsers=ChromeHeadless

# 3. Verify trends page exists and renders
grep "checkin-trends" src/app/app.routes.ts

# 4. Verify CheckinTrendsComponent exists
ls src/app/features/checkin/components/checkin-trends.component.ts

# 5. Verify model types are available
grep "QualityKey" src/app/features/checkin/checkin.model.ts
grep "CheckinQualityScore" src/app/features/checkin/checkin.model.ts

# 6. Verify CheckinDataService has getCompletedSessions and getScoresForSession
grep "getCompletedSessions" src/app/features/checkin/services/checkin-data.service.ts
grep "getScoresForSession" src/app/features/checkin/services/checkin-data.service.ts

# 7. Verify QUALITY_DEFINITIONS are exported
grep "QUALITY_DEFINITIONS" src/app/features/checkin/checkin.model.ts
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/features/checkin/utils/divergence.util.ts` | Pure function: `detectDivergences()` |
| 2 | `src/app/features/checkin/utils/divergence.util.spec.ts` | Unit tests for detection logic |

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/features/checkin/components/checkin-trends.component.ts` | Import `detectDivergences`, compute sustained alerts, render warning icons inline |
| 2 | `src/app/features/checkin/components/checkin-trends.component.spec.ts` | Add tests for sustained divergence rendering |
| 3 | `src/app/features/checkin/index.ts` | Export `detectDivergences` and `DivergenceAlert` type |

### To Leave Alone

- `src/app/features/checkin/components/divergence-alert.component.ts` — Existing single-session alert (unmodified)
- `src/app/features/checkin/services/checkin-data.service.ts` — No new methods needed
- `src/app/features/checkin/checkin.model.ts` — No model changes needed
- `src/app/features/checkin/components/sparkline.component.ts` — Untouched

---

## 6. Implementation Steps

### Step 1: Create the divergence utility

**Action**: Create a pure function that detects sustained divergence across a window of sessions.

**File**: `src/app/features/checkin/utils/divergence.util.ts`

```typescript
import type { QualityKey, CheckinQualityScore } from '../checkin.model';
import { QUALITY_DEFINITIONS } from '../checkin.model';

/**
 * A sustained divergence alert for a single quality dimension.
 */
export interface DivergenceAlert {
  /** Quality key (e.g. 'communication') */
  quality: QualityKey;
  /** Human-readable label */
  qualityLabel: string;
  /** Average gap magnitude (always positive) */
  gap: number;
  /** Which partner scored higher on average */
  higherPartner: 'A' | 'B';
  /** Partner A's average score over the window */
  avgA: number;
  /** Partner B's average score over the window */
  avgB: number;
}

/**
 * Detect sustained divergence between partners over a rolling window.
 *
 * For each quality dimension, computes the average score of Partner A
 * and Partner B over the last `window` sessions. If the absolute
 * difference exceeds `threshold`, the quality is flagged.
 *
 * @param scores      All quality scores across sessions (both partners, all qualities).
 *                    Expects scores from sessions ordered oldest-first.
 * @param sessionIds  Ordered session IDs (oldest-first) matching the scores.
 * @param window      Number of most-recent sessions to average over (default 3).
 * @param threshold   Minimum average gap to trigger an alert (default 2.0).
 * @returns           Array of DivergenceAlert for qualities that exceed the threshold.
 */
export function detectDivergences(
  scores: CheckinQualityScore[],
  sessionIds: string[],
  window = 3,
  threshold = 2.0,
): DivergenceAlert[] {
  if (sessionIds.length === 0) return [];

  // Take the last `window` sessions
  const windowSessionIds = sessionIds.slice(-window);

  if (windowSessionIds.length === 0) return [];

  const alerts: DivergenceAlert[] = [];

  for (const quality of QUALITY_DEFINITIONS) {
    const scoresA: number[] = [];
    const scoresB: number[] = [];

    for (const sessionId of windowSessionIds) {
      const aScore = scores.find(
        (s) =>
          s.session_id === sessionId &&
          s.partner === 'A' &&
          s.quality_key === quality.key,
      );
      const bScore = scores.find(
        (s) =>
          s.session_id === sessionId &&
          s.partner === 'B' &&
          s.quality_key === quality.key,
      );
      if (aScore) scoresA.push(aScore.score);
      if (bScore) scoresB.push(bScore.score);
    }

    // Need at least 1 score from each partner to compute
    if (scoresA.length === 0 || scoresB.length === 0) continue;

    const avgA = scoresA.reduce((sum, s) => sum + s, 0) / scoresA.length;
    const avgB = scoresB.reduce((sum, s) => sum + s, 0) / scoresB.length;
    const gap = Math.abs(avgA - avgB);

    if (gap > threshold) {
      alerts.push({
        quality: quality.key,
        qualityLabel: quality.label,
        gap,
        higherPartner: avgA > avgB ? 'A' : 'B',
        avgA,
        avgB,
      });
    }
  }

  return alerts;
}
```

**Verify**:

```bash
npx tsc --noEmit
```

---

### Step 2: Update CheckinTrendsComponent to compute and display sustained divergence

**Action**: Import `detectDivergences`, compute sustained alerts from loaded scores, and render warning icons inline next to quality labels in chart cards.

**File**: `src/app/features/checkin/components/checkin-trends.component.ts`

Add to the imports at the top of the file:

```typescript
import { detectDivergences, DivergenceAlert } from '../utils/divergence.util';
```

Add a new signal to the component class (after the existing `sessionCount` signal):

```typescript
  /** Sustained divergence alerts (averaged over last 3 sessions, threshold > 2.0) */
  private readonly sustainedDivergenceData = signal<DivergenceAlert[]>([]);
  protected readonly sustainedAlerts = computed(() => this.sustainedDivergenceData());
```

Add a helper method to the component class to check if a quality has a sustained alert:

```typescript
  /**
   * Returns the sustained divergence alert for a given quality, or null.
   * Used in the template to conditionally render warning indicators.
   */
  getSustainedAlert(qualityKey: QualityKey): DivergenceAlert | null {
    return this.sustainedAlerts().find((a) => a.quality === qualityKey) ?? null;
  }
```

In the `ngOnInit()` method (or `loadTrends()` if Task 7 has refactored to that), after the line that sets `this.trendData.set(trends)`, add:

```typescript
      // Compute sustained divergence alerts (window=3, threshold=2.0)
      const sessionIdList = sessions.map((s) => s.id);
      const sustained = detectDivergences(allScores, sessionIdList, 3, 2.0);
      this.sustainedDivergenceData.set(sustained);
```

Update the template's chart card section. Replace the existing chart card label `<h2>` with a version that includes a warning icon when sustained divergence is detected:

Replace:
```html
                <h2 class="chart-card__label" [attr.data-test]="'chart-label-' + trend.key">
                  {{ trend.label }}
                </h2>
```

With:
```html
                <h2 class="chart-card__label" [attr.data-test]="'chart-label-' + trend.key">
                  @if (getSustainedAlert(trend.key); as alert) {
                    <span
                      class="chart-card__warning"
                      [attr.data-test]="'sustained-warning-' + trend.key"
                      role="img"
                      aria-label="Sustained divergence detected"
                    >&#9888;</span>
                  }
                  {{ trend.label }}
                </h2>
                @if (getSustainedAlert(trend.key); as alert) {
                  <p
                    class="chart-card__divergence-text"
                    [attr.data-test]="'sustained-text-' + trend.key"
                  >
                    Partner {{ alert.higherPartner }} scored {{ alert.gap.toFixed(1) }} points higher on average over the last 3 sessions.
                  </p>
                }
```

Add styles for the warning icon and divergence text (append to the existing `styles` section):

```css
    .chart-card__warning {
      display: inline-block;
      font-size: 18px;
      margin-right: 6px;
      color: var(--score-amber, #FFC409);
      vertical-align: middle;
      line-height: 1;
    }

    .chart-card__divergence-text {
      font-size: 13px;
      color: var(--score-amber, #FFC409);
      margin: var(--sp-1, 4px) 0 var(--sp-2, 8px);
      padding-left: 24px;
      line-height: 1.4;
      font-style: italic;
    }
```

**Verify**:

```bash
npx tsc --noEmit
```

---

### Step 3: Export the utility from the feature barrel

**Action**: Export the new utility function and type from `index.ts`.

**File**: `src/app/features/checkin/index.ts`

Add these exports:

```typescript
export { detectDivergences } from './utils/divergence.util';
export type { DivergenceAlert } from './utils/divergence.util';
```

**Verify**:

```bash
npx tsc --noEmit
```

---

## 7. Tests

### Test 1: `divergence.util.spec.ts`

**File**: `src/app/features/checkin/utils/divergence.util.spec.ts`

```typescript
import { detectDivergences, DivergenceAlert } from './divergence.util';
import type { CheckinQualityScore } from '../checkin.model';

function fakeScore(
  sessionId: string,
  partner: 'A' | 'B',
  qualityKey: string,
  score: number,
): CheckinQualityScore {
  return {
    id: `qs-${sessionId}-${partner}-${qualityKey}`,
    session_id: sessionId,
    partner,
    quality_key: qualityKey as CheckinQualityScore['quality_key'],
    score,
  };
}

describe('detectDivergences', () => {
  const sessionIds = ['s1', 's2', 's3'];

  // ── Basic detection ─────────────────────────────────────────────────

  it('returns empty array when no sessions provided', () => {
    const result = detectDivergences([], [], 3, 2.0);
    expect(result).toEqual([]);
  });

  it('returns empty array when scores have no gap exceeding threshold', () => {
    const scores: CheckinQualityScore[] = [
      // Communication: A=7, B=6 (gap=1 per session)
      fakeScore('s1', 'A', 'communication', 7),
      fakeScore('s1', 'B', 'communication', 6),
      fakeScore('s2', 'A', 'communication', 7),
      fakeScore('s2', 'B', 'communication', 6),
      fakeScore('s3', 'A', 'communication', 7),
      fakeScore('s3', 'B', 'communication', 6),
      // Respect: A=8, B=8 (gap=0)
      fakeScore('s1', 'A', 'respect', 8),
      fakeScore('s1', 'B', 'respect', 8),
      fakeScore('s2', 'A', 'respect', 8),
      fakeScore('s2', 'B', 'respect', 8),
      fakeScore('s3', 'A', 'respect', 8),
      fakeScore('s3', 'B', 'respect', 8),
      // Prioritization: A=5, B=5 (gap=0)
      fakeScore('s1', 'A', 'prioritization', 5),
      fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5),
      fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5),
      fakeScore('s3', 'B', 'prioritization', 5),
      // Viability: A=6, B=7 (gap=1)
      fakeScore('s1', 'A', 'viability', 6),
      fakeScore('s1', 'B', 'viability', 7),
      fakeScore('s2', 'A', 'viability', 6),
      fakeScore('s2', 'B', 'viability', 7),
      fakeScore('s3', 'A', 'viability', 6),
      fakeScore('s3', 'B', 'viability', 7),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    expect(result.length).toBe(0);
  });

  it('detects divergence when average gap exceeds threshold', () => {
    const scores: CheckinQualityScore[] = [
      // Communication: A avg = 8, B avg = 5 → gap = 3.0
      fakeScore('s1', 'A', 'communication', 8),
      fakeScore('s1', 'B', 'communication', 5),
      fakeScore('s2', 'A', 'communication', 8),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'A', 'communication', 8),
      fakeScore('s3', 'B', 'communication', 5),
      // Respect: A=7, B=7 (gap=0)
      fakeScore('s1', 'A', 'respect', 7),
      fakeScore('s1', 'B', 'respect', 7),
      fakeScore('s2', 'A', 'respect', 7),
      fakeScore('s2', 'B', 'respect', 7),
      fakeScore('s3', 'A', 'respect', 7),
      fakeScore('s3', 'B', 'respect', 7),
      // Prioritization: A=5, B=5 (gap=0)
      fakeScore('s1', 'A', 'prioritization', 5),
      fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5),
      fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5),
      fakeScore('s3', 'B', 'prioritization', 5),
      // Viability: A=6, B=6 (gap=0)
      fakeScore('s1', 'A', 'viability', 6),
      fakeScore('s1', 'B', 'viability', 6),
      fakeScore('s2', 'A', 'viability', 6),
      fakeScore('s2', 'B', 'viability', 6),
      fakeScore('s3', 'A', 'viability', 6),
      fakeScore('s3', 'B', 'viability', 6),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    expect(result.length).toBe(1);
    expect(result[0].quality).toBe('communication');
    expect(result[0].gap).toBeCloseTo(3.0, 1);
    expect(result[0].higherPartner).toBe('A');
  });

  it('correctly identifies Partner B as higher when B scores more', () => {
    const scores: CheckinQualityScore[] = [
      // Respect: A avg = 4, B avg = 7 → gap = 3, B higher
      fakeScore('s1', 'A', 'respect', 4),
      fakeScore('s1', 'B', 'respect', 7),
      fakeScore('s2', 'A', 'respect', 4),
      fakeScore('s2', 'B', 'respect', 7),
      fakeScore('s3', 'A', 'respect', 4),
      fakeScore('s3', 'B', 'respect', 7),
      // Fill other qualities with equal scores
      fakeScore('s1', 'A', 'communication', 5),
      fakeScore('s1', 'B', 'communication', 5),
      fakeScore('s2', 'A', 'communication', 5),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'A', 'communication', 5),
      fakeScore('s3', 'B', 'communication', 5),
      fakeScore('s1', 'A', 'prioritization', 5),
      fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5),
      fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5),
      fakeScore('s3', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5),
      fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5),
      fakeScore('s2', 'B', 'viability', 5),
      fakeScore('s3', 'A', 'viability', 5),
      fakeScore('s3', 'B', 'viability', 5),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    const respectAlert = result.find((a) => a.quality === 'respect');
    expect(respectAlert).toBeDefined();
    expect(respectAlert!.higherPartner).toBe('B');
  });

  it('does not flag gap of exactly 2.0 (threshold is strict >)', () => {
    const scores: CheckinQualityScore[] = [
      // Communication: A avg = 7, B avg = 5 → gap = 2.0 exactly
      fakeScore('s1', 'A', 'communication', 7),
      fakeScore('s1', 'B', 'communication', 5),
      fakeScore('s2', 'A', 'communication', 7),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'A', 'communication', 7),
      fakeScore('s3', 'B', 'communication', 5),
      // Others equal
      fakeScore('s1', 'A', 'respect', 5), fakeScore('s1', 'B', 'respect', 5),
      fakeScore('s2', 'A', 'respect', 5), fakeScore('s2', 'B', 'respect', 5),
      fakeScore('s3', 'A', 'respect', 5), fakeScore('s3', 'B', 'respect', 5),
      fakeScore('s1', 'A', 'prioritization', 5), fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5), fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5), fakeScore('s3', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5), fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5), fakeScore('s2', 'B', 'viability', 5),
      fakeScore('s3', 'A', 'viability', 5), fakeScore('s3', 'B', 'viability', 5),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    expect(result.length).toBe(0);
  });

  // ── Window behavior ─────────────────────────────────────────────────

  it('uses only the last N sessions from the window parameter', () => {
    const allSessionIds = ['s1', 's2', 's3', 's4', 's5'];
    const scores: CheckinQualityScore[] = [
      // s1-s3: communication gap is 4 (would trigger)
      fakeScore('s1', 'A', 'communication', 9),
      fakeScore('s1', 'B', 'communication', 5),
      fakeScore('s2', 'A', 'communication', 9),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'A', 'communication', 9),
      fakeScore('s3', 'B', 'communication', 5),
      // s4-s5: communication gap is 0 (no divergence in window=2)
      fakeScore('s4', 'A', 'communication', 7),
      fakeScore('s4', 'B', 'communication', 7),
      fakeScore('s5', 'A', 'communication', 7),
      fakeScore('s5', 'B', 'communication', 7),
      // Others equal across all sessions
      ...allSessionIds.flatMap((sid) => [
        fakeScore(sid, 'A', 'respect', 5), fakeScore(sid, 'B', 'respect', 5),
        fakeScore(sid, 'A', 'prioritization', 5), fakeScore(sid, 'B', 'prioritization', 5),
        fakeScore(sid, 'A', 'viability', 5), fakeScore(sid, 'B', 'viability', 5),
      ]),
    ];

    // Window=2 → only s4, s5 → no divergence
    const result2 = detectDivergences(scores, allSessionIds, 2, 2.0);
    expect(result2.length).toBe(0);

    // Window=5 → s1-s5 averaged → A avg = (9+9+9+7+7)/5=8.2, B avg = (5+5+5+7+7)/5=5.8 → gap=2.4
    const result5 = detectDivergences(scores, allSessionIds, 5, 2.0);
    expect(result5.find((a) => a.quality === 'communication')).toBeDefined();
  });

  it('handles fewer sessions than the window gracefully', () => {
    // Only 2 sessions, window=3 → should use available 2
    const scores: CheckinQualityScore[] = [
      fakeScore('s1', 'A', 'communication', 9),
      fakeScore('s1', 'B', 'communication', 4),
      fakeScore('s2', 'A', 'communication', 9),
      fakeScore('s2', 'B', 'communication', 4),
      fakeScore('s1', 'A', 'respect', 5), fakeScore('s1', 'B', 'respect', 5),
      fakeScore('s2', 'A', 'respect', 5), fakeScore('s2', 'B', 'respect', 5),
      fakeScore('s1', 'A', 'prioritization', 5), fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5), fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5), fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5), fakeScore('s2', 'B', 'viability', 5),
    ];

    const result = detectDivergences(scores, ['s1', 's2'], 3, 2.0);
    // gap = 5.0 for communication → should still flag
    expect(result.find((a) => a.quality === 'communication')).toBeDefined();
    expect(result.find((a) => a.quality === 'communication')!.gap).toBeCloseTo(5.0, 1);
  });

  // ── Multiple qualities ──────────────────────────────────────────────

  it('can flag multiple qualities simultaneously', () => {
    const scores: CheckinQualityScore[] = [
      // Communication: gap = 3
      fakeScore('s1', 'A', 'communication', 9),
      fakeScore('s1', 'B', 'communication', 6),
      fakeScore('s2', 'A', 'communication', 9),
      fakeScore('s2', 'B', 'communication', 6),
      fakeScore('s3', 'A', 'communication', 9),
      fakeScore('s3', 'B', 'communication', 6),
      // Respect: gap = 0
      fakeScore('s1', 'A', 'respect', 7),
      fakeScore('s1', 'B', 'respect', 7),
      fakeScore('s2', 'A', 'respect', 7),
      fakeScore('s2', 'B', 'respect', 7),
      fakeScore('s3', 'A', 'respect', 7),
      fakeScore('s3', 'B', 'respect', 7),
      // Prioritization: gap = 2.33
      fakeScore('s1', 'A', 'prioritization', 3),
      fakeScore('s1', 'B', 'prioritization', 6),
      fakeScore('s2', 'A', 'prioritization', 4),
      fakeScore('s2', 'B', 'prioritization', 6),
      fakeScore('s3', 'A', 'prioritization', 3),
      fakeScore('s3', 'B', 'prioritization', 6),
      // Viability: gap = 0
      fakeScore('s1', 'A', 'viability', 6),
      fakeScore('s1', 'B', 'viability', 6),
      fakeScore('s2', 'A', 'viability', 6),
      fakeScore('s2', 'B', 'viability', 6),
      fakeScore('s3', 'A', 'viability', 6),
      fakeScore('s3', 'B', 'viability', 6),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    expect(result.length).toBe(2);
    expect(result.find((a) => a.quality === 'communication')).toBeDefined();
    expect(result.find((a) => a.quality === 'prioritization')).toBeDefined();
  });

  // ── avgA and avgB values ────────────────────────────────────────────

  it('returns correct avgA and avgB in alert', () => {
    const scores: CheckinQualityScore[] = [
      fakeScore('s1', 'A', 'communication', 8),
      fakeScore('s1', 'B', 'communication', 4),
      fakeScore('s2', 'A', 'communication', 9),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'A', 'communication', 7),
      fakeScore('s3', 'B', 'communication', 3),
      // Others equal
      fakeScore('s1', 'A', 'respect', 5), fakeScore('s1', 'B', 'respect', 5),
      fakeScore('s2', 'A', 'respect', 5), fakeScore('s2', 'B', 'respect', 5),
      fakeScore('s3', 'A', 'respect', 5), fakeScore('s3', 'B', 'respect', 5),
      fakeScore('s1', 'A', 'prioritization', 5), fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5), fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5), fakeScore('s3', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5), fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5), fakeScore('s2', 'B', 'viability', 5),
      fakeScore('s3', 'A', 'viability', 5), fakeScore('s3', 'B', 'viability', 5),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    const alert = result.find((a) => a.quality === 'communication')!;
    expect(alert.avgA).toBeCloseTo(8.0, 1);   // (8+9+7)/3 = 8
    expect(alert.avgB).toBeCloseTo(4.0, 1);   // (4+5+3)/3 = 4
    expect(alert.gap).toBeCloseTo(4.0, 1);
  });

  // ── Custom threshold ────────────────────────────────────────────────

  it('respects custom threshold parameter', () => {
    const scores: CheckinQualityScore[] = [
      // Communication: gap = 2.33 (above 2.0, below 3.0)
      fakeScore('s1', 'A', 'communication', 7),
      fakeScore('s1', 'B', 'communication', 5),
      fakeScore('s2', 'A', 'communication', 8),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'A', 'communication', 7),
      fakeScore('s3', 'B', 'communication', 5),
      // Others equal
      fakeScore('s1', 'A', 'respect', 5), fakeScore('s1', 'B', 'respect', 5),
      fakeScore('s2', 'A', 'respect', 5), fakeScore('s2', 'B', 'respect', 5),
      fakeScore('s3', 'A', 'respect', 5), fakeScore('s3', 'B', 'respect', 5),
      fakeScore('s1', 'A', 'prioritization', 5), fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5), fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5), fakeScore('s3', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5), fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5), fakeScore('s2', 'B', 'viability', 5),
      fakeScore('s3', 'A', 'viability', 5), fakeScore('s3', 'B', 'viability', 5),
    ];

    // Threshold 2.0 → triggers (gap ~2.33)
    const resultLow = detectDivergences(scores, sessionIds, 3, 2.0);
    expect(resultLow.length).toBe(1);

    // Threshold 3.0 → does not trigger
    const resultHigh = detectDivergences(scores, sessionIds, 3, 3.0);
    expect(resultHigh.length).toBe(0);
  });

  // ── Missing data ────────────────────────────────────────────────────

  it('skips quality when no Partner A scores exist for the window', () => {
    const scores: CheckinQualityScore[] = [
      // Only B scores for communication
      fakeScore('s1', 'B', 'communication', 5),
      fakeScore('s2', 'B', 'communication', 5),
      fakeScore('s3', 'B', 'communication', 5),
      // Others have both
      fakeScore('s1', 'A', 'respect', 5), fakeScore('s1', 'B', 'respect', 5),
      fakeScore('s2', 'A', 'respect', 5), fakeScore('s2', 'B', 'respect', 5),
      fakeScore('s3', 'A', 'respect', 5), fakeScore('s3', 'B', 'respect', 5),
      fakeScore('s1', 'A', 'prioritization', 5), fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5), fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5), fakeScore('s3', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5), fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5), fakeScore('s2', 'B', 'viability', 5),
      fakeScore('s3', 'A', 'viability', 5), fakeScore('s3', 'B', 'viability', 5),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    // Communication should not appear (can't compute without A data)
    expect(result.find((a) => a.quality === 'communication')).toBeUndefined();
  });

  it('includes qualityLabel in alert output', () => {
    const scores: CheckinQualityScore[] = [
      fakeScore('s1', 'A', 'communication', 9),
      fakeScore('s1', 'B', 'communication', 4),
      fakeScore('s2', 'A', 'communication', 9),
      fakeScore('s2', 'B', 'communication', 4),
      fakeScore('s3', 'A', 'communication', 9),
      fakeScore('s3', 'B', 'communication', 4),
      fakeScore('s1', 'A', 'respect', 5), fakeScore('s1', 'B', 'respect', 5),
      fakeScore('s2', 'A', 'respect', 5), fakeScore('s2', 'B', 'respect', 5),
      fakeScore('s3', 'A', 'respect', 5), fakeScore('s3', 'B', 'respect', 5),
      fakeScore('s1', 'A', 'prioritization', 5), fakeScore('s1', 'B', 'prioritization', 5),
      fakeScore('s2', 'A', 'prioritization', 5), fakeScore('s2', 'B', 'prioritization', 5),
      fakeScore('s3', 'A', 'prioritization', 5), fakeScore('s3', 'B', 'prioritization', 5),
      fakeScore('s1', 'A', 'viability', 5), fakeScore('s1', 'B', 'viability', 5),
      fakeScore('s2', 'A', 'viability', 5), fakeScore('s2', 'B', 'viability', 5),
      fakeScore('s3', 'A', 'viability', 5), fakeScore('s3', 'B', 'viability', 5),
    ];

    const result = detectDivergences(scores, sessionIds, 3, 2.0);
    expect(result[0].qualityLabel).toBe('Communication Honesty');
  });
});
```

---

### Test 2: Additional tests for `checkin-trends.component.spec.ts`

**File**: `src/app/features/checkin/components/checkin-trends.component.spec.ts`

Add these tests to the existing describe block. Uses the existing mock data setup (`SESSIONS`, `ALL_SCORES`).

```typescript
  // ── Sustained divergence indicators ─────────────────────────────────

  it('renders sustained warning icon for communication (avg gap > 2.0 over 3 sessions)', async () => {
    // ALL_SCORES has communication: A=[6,7,9] B=[5,6,5]
    // avgA = (6+7+9)/3 = 7.33, avgB = (5+6+5)/3 = 5.33, gap = 2.0 → exactly 2.0, NOT > 2.0
    // Need to set up data with gap > 2.0 to test the indicator renders
    const divergentScores = [
      ...fakeScoresForSession(
        's1',
        { communication: 9, respect: 7, prioritization: 5, viability: 6 },
        { communication: 4, respect: 7, prioritization: 5, viability: 6 },
      ),
      ...fakeScoresForSession(
        's2',
        { communication: 9, respect: 7, prioritization: 5, viability: 6 },
        { communication: 4, respect: 7, prioritization: 5, viability: 6 },
      ),
      ...fakeScoresForSession(
        's3',
        { communication: 9, respect: 7, prioritization: 5, viability: 6 },
        { communication: 4, respect: 7, prioritization: 5, viability: 6 },
      ),
    ];

    setup(SESSIONS, divergentScores);
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    expect(query('sustained-warning-communication')).not.toBeNull();
  });

  it('renders sustained divergence explanatory text', async () => {
    const divergentScores = [
      ...fakeScoresForSession(
        's1',
        { communication: 9, respect: 7, prioritization: 5, viability: 6 },
        { communication: 4, respect: 7, prioritization: 5, viability: 6 },
      ),
      ...fakeScoresForSession(
        's2',
        { communication: 9, respect: 7, prioritization: 5, viability: 6 },
        { communication: 4, respect: 7, prioritization: 5, viability: 6 },
      ),
      ...fakeScoresForSession(
        's3',
        { communication: 9, respect: 7, prioritization: 5, viability: 6 },
        { communication: 4, respect: 7, prioritization: 5, viability: 6 },
      ),
    ];

    setup(SESSIONS, divergentScores);
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    const text = query('sustained-text-communication');
    expect(text).not.toBeNull();
    expect(text?.textContent).toContain('Partner A');
    expect(text?.textContent).toContain('higher on average');
  });

  it('does not render sustained warning when gap <= 2.0', async () => {
    // Default ALL_SCORES: respect has gap=1 in last session → no sustained alert
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    expect(query('sustained-warning-respect')).toBeNull();
  });

  it('does not render sustained text for non-divergent qualities', async () => {
    setup();
    fixture.detectChanges();
    await component.ngOnInit();
    fixture.detectChanges();

    expect(query('sustained-text-respect')).toBeNull();
  });
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(checkin): add sustained divergence detection utility` | `utils/divergence.util.ts`, `utils/divergence.util.spec.ts` |
| 2 | `feat(checkin): add sustained divergence indicators to trends page` | `components/checkin-trends.component.ts`, `components/checkin-trends.component.spec.ts` |
| 3 | `feat(checkin): export divergence utility from feature barrel` | `index.ts` |

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
#   - detectDivergences: 11 specs
#   - CheckinTrendsComponent: existing 16 specs + 4 new specs

# 4. Verify file structure
ls src/app/features/checkin/utils/divergence.util.ts
ls src/app/features/checkin/utils/divergence.util.spec.ts

# 5. Verify barrel export
grep "detectDivergences" src/app/features/checkin/index.ts
grep "DivergenceAlert" src/app/features/checkin/index.ts

# 6. Verify import in trends component
grep "detectDivergences" src/app/features/checkin/components/checkin-trends.component.ts

# 7. Verify visual markers exist in template
grep "sustained-warning" src/app/features/checkin/components/checkin-trends.component.ts
grep "sustained-text" src/app/features/checkin/components/checkin-trends.component.ts

# 8. Manual smoke test
ionic serve &
# Test 1: Navigate to /checkin/trends with 3+ completed sessions where one quality has sustained gap > 2.0
# Test 2: Verify warning icon (⚠) appears next to the divergent quality label
# Test 3: Verify explanatory text appears below the label ("Partner X scored Y.Z points higher...")
# Test 4: Verify non-divergent qualities show NO warning icon or text
# Test 5: Verify the existing single-session divergence alerts section still renders below charts
# Test 6: Verify both indicators can coexist (sustained inline + single-session section)
```

---

## 10. Rollback

Changes add 2 new files and modify 3 existing files. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -3  # find the 3 commit SHAs
git revert <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~3

# Option 3: Manual cleanup
rm -f src/app/features/checkin/utils/divergence.util.ts
rm -f src/app/features/checkin/utils/divergence.util.spec.ts
# Revert modifications:
git checkout -- src/app/features/checkin/components/checkin-trends.component.ts
git checkout -- src/app/features/checkin/components/checkin-trends.component.spec.ts
git checkout -- src/app/features/checkin/index.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Warning icon** | Executor may use an Ionicons `warning-outline` icon via `<ion-icon>` instead of the Unicode `&#9888;` character. Both are valid. |
| **Inline text wording** | Executor may adjust the explanatory text phrasing (e.g. "averaged X.Y points higher" vs "scored X.Y points higher on average"). Key: the partner, gap value, and "last 3 sessions" context must be present. |
| **Threshold value** | Executor may use `>= 2.0` (inclusive) instead of `> 2.0` (exclusive). Either interpretation is acceptable for V1. |
| **CSS placement** | Executor may position the warning icon after the label text instead of before it. Key: it's visually adjacent to the quality name. |
| **Utility file location** | Executor may place `divergence.util.ts` directly in `components/` or at the feature root instead of creating a `utils/` directory. |
| **Signal vs method** | Executor may use a `computed()` signal that returns a `Map<QualityKey, DivergenceAlert>` instead of a `getSustainedAlert(key)` method. Both approaches work. |
| **Window parameter** | Executor may hardcode `3` instead of making it a parameter. The architecture says "default 3" so either approach is valid. |
| **Alert interface naming** | Executor may name the type `SustainedDivergenceAlert` or `WindowedDivergenceAlert` instead of `DivergenceAlert`. Key: it must not collide with the existing `DivergenceAlertData` interface. |
| **Integration approach** | Executor may compute sustained alerts inside the existing `alerts` computed signal (unified) or keep them separate. Separate signals are preferred for clarity but not required. |
| **Test count** | Executor may write fewer utility tests if the core paths (empty input, below threshold, above threshold, window slicing, partner direction) are covered. Minimum: 8 utility tests + 2 component integration tests. |

---

## 12. Out of Scope

- **Replacing the existing single-session divergence alerts** -- The existing `DivergenceAlertComponent` section remains untouched. Both indicators coexist.
- **Modal/toast/push alerts** -- Visual indicators only. No interruption of user flow.
- **User-configurable threshold or window** -- Hardcoded in V1. Settings UI is a future task.
- **Trend direction** -- This task detects magnitude of gap, not whether the gap is growing or shrinking over time.
- **Per-question divergence** -- Only quality-level (aggregated) divergence. Per-question drill-down is Task 7's concern.
- **Historical alert log** -- No persistence of when alerts were triggered. Computed fresh on each page load.
- **Notification badge on tab bar** -- Out of scope. Indicators live only on the trends page itself.
- **Accessibility announcements (live region)** -- The warning icon has `role="img"` and `aria-label`, but no `aria-live` region. V1 limitation.
- **Animation/transition on warning appearance** -- Static render. No fade-in or pulse animation.
- **E2E / Playwright tests** -- Unit tests only.
- **Dark/light theme** -- Dark only per spec.
