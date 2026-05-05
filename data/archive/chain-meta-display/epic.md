---
sidebar_position: 2
---

# Epic -- Chain Meta Display

**Purpose**: Define scope and tasks for rendering chain sidecar metadata in the /text page UI.

**Source Analysis**: See [Analysis](./analysis.md) for problem statement and resolved questions.

---

## Business Value

The braindump-to-docs pipeline is the differentiator -- multi-file spec generation from a single brain dump. But right now the user submits a braindump, waits through 3 chain steps, gets their spec files, and has zero visibility into what the lint caught or how the output scored. The feedback loop is broken. Displaying lint warnings teaches users to write better braindumps. Displaying quality scores builds trust in the pipeline ("your specs scored 0.92 on structure"). Both turn an opaque AI call into a transparent quality process.

Secondary value: the Inspector panels establish the pattern for surfacing any future sidecar metadata (token costs, latency breakdowns, prompt versions) without cluttering the primary output.

---

## Scope

### What This Epic Covers

- **Interface + mock update**: Add `meta?: Record<string, string>` to the frontend `ChainResponse` interface and populate `MOCK_CHAIN_MULTI` with sample lint/score JSON
- **Page-level meta signal**: Store parsed `meta` data in `text.page.ts` after a chain run; parse JSON strings into typed objects
- **`ChainMetaPanelsComponent`**: New standalone component that renders lint warnings and quality scores in collapsible panels
- **Lint section**: Parse `meta.lint` JSON; render issues as a list with pass/fail badge per item; show "All clear" when no issues
- **Score section**: Parse `meta.score` JSON; render each dimension as a labeled bar (0.0--1.0) with numeric value
- **Collapsed by default**: "Inspector" toggle header; expanded state persisted in a signal (not localStorage -- session-only)
- **Raw JSON fallback**: If JSON parsing fails for a meta value, render the raw string in a `<pre>` block
- **Tests**: TestBed tests for the new component; page-level tests for meta signal wiring

### What This Epic Does NOT Cover

- Backend changes (chain runner fix, DTO plumbing, service layer) -- prerequisite epic
- Persisting meta data to the database
- Analytics events for Inspector panel interactions
- Re-running chains based on lint feedback
- Score trend tracking across runs
- Animations or transitions on panel expand/collapse (ship static toggle first)

---

## Tasks

**Note**: Task status tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **Update `ChainResponse` interface + mock** | None | 0.25 day | High |
| 2 | **Add meta signal to `text.page.ts`** | 1 | 0.25 day | High |
| 3 | **Create `ChainMetaPanelsComponent`** | None | 0.5 day | High |
| 4 | **Wire component into text page template** | 2, 3 | 0.25 day | High |
| 5 | **TestBed tests** | 3, 4 | 0.5 day | High |

### Task Details

#### Task 1: Update `ChainResponse` interface + mock

**Files to modify**:
- `src/app/services/text-api.service.ts` -- add `meta?: Record<string, string>` to `ChainResponse` interface
- `src/app/mocks/chain.mock.ts` -- add `meta?: Record<string, string>` to `ChainResponse` interface; add `meta` to `MOCK_CHAIN_MULTI`

**Mock data shape**:
```typescript
meta: {
  lint: '{"issues": ["Missing \\"Why now\\" section", "What section under 50 words"]}',
  score: '{"scores": {"structure": 0.85, "clarity": 0.92, "completeness": 0.78, "actionability": 0.88}}'
}
```

The mock enables development and testing before the backend ships.

#### Task 2: Add meta signal to `text.page.ts`

**File**: `src/app/pages/text/text.page.ts`

Add two typed interfaces and two signals:

```typescript
interface LintMeta {
  issues: string[];
}

interface ScoreMeta {
  scores: Record<string, number>;
}
```

```typescript
protected readonly chainLint = signal<LintMeta | null>(null);
protected readonly chainScore = signal<ScoreMeta | null>(null);
```

In `runChain()`, after receiving the response, parse `meta`:

```typescript
// After setting chainFiles / output:
this.chainLint.set(this.parseMeta<LintMeta>(res.meta?.['lint']));
this.chainScore.set(this.parseMeta<ScoreMeta>(res.meta?.['score']));
```

Helper method:
```typescript
private parseMeta<T>(raw: string | undefined): T | null {
  if (!raw) return null;
  try { return JSON.parse(raw) as T; }
  catch { return null; }
}
```

Reset both signals at the top of `runChain()` and in `rewrite()` / `generate()`.

#### Task 3: Create `ChainMetaPanelsComponent`

**New file**: `src/app/pages/text/components/chain-meta-panels.component.ts`
**New file**: `src/app/pages/text/components/chain-meta-panels.component.scss`

Standalone component with OnPush change detection. Inputs:

```typescript
@Input() lint: LintMeta | null = null;
@Input() score: ScoreMeta | null = null;
```

Internal state:
```typescript
readonly expanded = signal(false);
```

Template structure:
```
<div class="inspector" data-test="meta-inspector">
  <button (click)="expanded.set(!expanded())" data-test="meta-toggle">
    Inspector {{ expanded() ? '(hide)' : '(show)' }}
  </button>

  @if (expanded()) {
    @if (lint) {
      <section data-test="meta-lint">
        <h4>Lint</h4>
        @if (lint.issues.length === 0) {
          <span class="badge badge--pass" data-test="lint-pass">All clear</span>
        } @else {
          <ul>
            @for (issue of lint.issues; track issue) {
              <li class="lint-issue" data-test="lint-issue">
                <span class="badge badge--warn">Warning</span>
                {{ issue }}
              </li>
            }
          </ul>
        }
      </section>
    }

    @if (score) {
      <section data-test="meta-score">
        <h4>Quality Scores</h4>
        @for (entry of scoreEntries(); track entry.key) {
          <div class="score-row" data-test="score-row">
            <span class="score-label">{{ entry.key }}</span>
            <div class="score-bar">
              <div class="score-fill" [style.width.%]="entry.value * 100"></div>
            </div>
            <span class="score-value" data-test="score-value">{{ (entry.value * 100).toFixed(0) }}%</span>
          </div>
        }
      </section>
    }
  }
</div>
```

Computed for score entries:
```typescript
readonly scoreEntries = computed(() => {
  if (!this.score) return [];
  return Object.entries(this.score.scores).map(([key, value]) => ({ key, value }));
});
```

The component renders nothing (empty `<div>`) when both `lint` and `score` are `null`.

#### Task 4: Wire component into text page template

**File**: `src/app/pages/text/text.page.ts`

Add `ChainMetaPanelsComponent` to imports array. In the template, below `<app-chain-output-tabs>`:

```html
@if (chainLint() || chainScore()) {
  <app-chain-meta-panels
    [lint]="chainLint()"
    [score]="chainScore()"
    data-test="chain-meta-panels"
  ></app-chain-meta-panels>
}
```

This goes inside the existing `@if (state() === 'result' && chainFiles(); as files)` block, after the `<app-chain-output-tabs>` element.

#### Task 5: TestBed tests

**New file**: `src/app/pages/text/components/chain-meta-panels.component.spec.ts`

| Test | Assertion |
|------|-----------|
| `noMeta_rendersEmptyInspector` | When both `lint` and `score` are `null`, no toggle button renders |
| `toggleClick_expandsPanels` | Clicking `[data-test="meta-toggle"]` sets `expanded()` to `true` and renders panel content |
| `lintWithIssues_rendersWarningBadges` | When `lint.issues` has 2 items, 2 `[data-test="lint-issue"]` elements render with "Warning" badge |
| `lintNoIssues_rendersAllClear` | When `lint.issues` is empty, `[data-test="lint-pass"]` renders with "All clear" text |
| `scoreValues_renderBarsWithPercentage` | When `score.scores` has 3 entries, 3 `[data-test="score-row"]` render with correct percentage text |
| `scoreBarWidth_matchesValue` | A score of `0.85` renders a `.score-fill` element with `width: 85%` |
| `collapsedByDefault_noPanelContent` | On init, no `[data-test="meta-lint"]` or `[data-test="meta-score"]` elements exist |

---

## Success Criteria

- `braindump-to-docs` chain result shows an "Inspector" toggle below the file tabs
- Clicking "Inspector" reveals lint warnings with pass/fail badges and quality score bars
- Panels are collapsed by default -- primary output is not cluttered
- When `meta` is absent (e.g., `deep-humanize` chain), no Inspector toggle renders
- When `meta` JSON is malformed, panels degrade gracefully (no render, no error)
- Mock mode (`environment.useMocks.textChains`) renders the Inspector with sample data
- All existing text page tests pass without modification

---

## Non-Goals

- Backend changes (separate epic)
- Persisting meta or tracking trends
- Re-running chains from lint feedback
- Animations on expand/collapse
- Mobile-specific layout adjustments (panels inherit page's responsive `max-width: 640px`)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

===END===
