---
sidebar_position: 3
---

# Architecture -- Chain Meta Display

**Purpose**: Technical design for rendering chain sidecar metadata in collapsible Inspector panels.

**References**: See [Epic](./epic.md) for scope. See [Analysis](./analysis.md) for constraints and resolved decisions.

---

## Overview

Three file modifications and two new files. No backend changes, no new services, no new routes. The work adds a `meta` field to the frontend `ChainResponse` interface, parses meta JSON in the page component, and renders structured lint/score data in a new `ChainMetaPanelsComponent`.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = Bounded Context | `ChainMetaPanelsComponent` lives in `pages/text/components/`. Receives typed data via `@Input`. No service injection, no cross-feature imports. |
| Adapter (every feature service) | `TextApiService` remains the only backend boundary. The page component parses raw `meta` strings; the panel component never sees raw JSON. |
| Explicit Over Implicit | Collapsed-by-default via `expanded = signal(false)`. No auto-expand heuristics. User controls visibility. |
| Anti-Corruption Layer | Raw LLM JSON strings are parsed in `text.page.ts` (the adapter boundary for meta data). `ChainMetaPanelsComponent` receives `LintMeta | null` and `ScoreMeta | null` -- typed, validated, or null. |
| data-test Selectors Only | Every interactive element: `data-test="meta-toggle"`, `data-test="meta-inspector"`, `data-test="lint-issue"`, `data-test="score-row"`, `data-test="score-value"`, `data-test="lint-pass"`. |

---

## Data Flow

```
Backend API response
  └── { generationId, files, meta: { lint: "<json-string>", score: "<json-string>" } }
       │
       ▼
TextApiService.chainRun()           ← returns ChainResponse (now with optional meta)
       │
       ▼
TextPage.runChain()
  ├── chainFiles.set(res.files)     ← existing
  ├── chainLint.set(parseMeta(res.meta?.['lint']))    ← NEW
  └── chainScore.set(parseMeta(res.meta?.['score']))  ← NEW
       │
       ▼
Template: @if (chainLint() || chainScore())
  └── <app-chain-meta-panels [lint]="chainLint()" [score]="chainScore()">
       │
       ▼
ChainMetaPanelsComponent
  ├── expanded signal (false by default)
  ├── toggle button → expanded.set(!expanded())
  └── @if (expanded())
       ├── Lint section: issues[] → badge list or "All clear"
       └── Score section: scores{} → labeled bars with percentages
```

---

## Type Definitions

### Meta interfaces (defined in `text.page.ts`)

```typescript
interface LintMeta {
  issues: string[];
}

interface ScoreMeta {
  scores: Record<string, number>;
}
```

These are local to the page component. They are not exported or shared. If a second consumer appears, extract to a `text.model.ts` file per the feature-model convention.

### ChainResponse interface update

```typescript
// src/app/services/text-api.service.ts
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
  meta?: Record<string, string>;                      // NEW
}

// src/app/mocks/chain.mock.ts
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
  meta?: Record<string, string>;                      // NEW
}
```

---

## Component Design: `ChainMetaPanelsComponent`

### Inputs

| Input | Type | Required | Default |
|-------|------|----------|---------|
| `lint` | `LintMeta \| null` | No | `null` |
| `score` | `ScoreMeta \| null` | No | `null` |

### Internal State

| Signal | Type | Default | Purpose |
|--------|------|---------|---------|
| `expanded` | `boolean` | `false` | Toggle visibility of panel content |
| `scoreEntries` | `computed` | `[]` | Derived from `score.scores` as `{ key, value }[]` |

### Rendering Rules

1. **Both inputs null** -- render nothing (empty host element, no toggle button)
2. **At least one input non-null** -- render "Inspector" toggle button
3. **Collapsed** -- only toggle button visible; panel content hidden
4. **Expanded, lint present** -- render lint section with issues list or "All clear" badge
5. **Expanded, score present** -- render score section with dimension bars
6. **Expanded, both present** -- render both sections, lint first then score

### Template Structure

```html
@if (lint || score) {
  <div class="inspector" data-test="meta-inspector">
    <button
      type="button"
      class="inspector-toggle"
      data-test="meta-toggle"
      (click)="expanded.set(!expanded())"
    >
      Inspector {{ expanded() ? '(hide)' : '(show)' }}
    </button>

    @if (expanded()) {
      <div class="inspector-body">
        @if (lint) {
          <section class="panel" data-test="meta-lint">
            <h4 class="panel-title">Lint</h4>
            @if (lint.issues.length === 0) {
              <span class="badge badge--pass" data-test="lint-pass">All clear</span>
            } @else {
              <ul class="lint-list">
                @for (issue of lint.issues; track issue) {
                  <li class="lint-issue" data-test="lint-issue">
                    <span class="badge badge--warn">Warning</span>
                    <span class="lint-text">{{ issue }}</span>
                  </li>
                }
              </ul>
            }
          </section>
        }

        @if (score) {
          <section class="panel" data-test="meta-score">
            <h4 class="panel-title">Quality Scores</h4>
            @for (entry of scoreEntries(); track entry.key) {
              <div class="score-row" data-test="score-row">
                <span class="score-label">{{ entry.key }}</span>
                <div class="score-bar" role="meter" [attr.aria-valuenow]="entry.value" aria-valuemin="0" aria-valuemax="1">
                  <div class="score-fill" [style.width.%]="entry.value * 100"></div>
                </div>
                <span class="score-value" data-test="score-value">{{ (entry.value * 100).toFixed(0) }}%</span>
              </div>
            }
          </section>
        }
      </div>
    }
  </div>
}
```

---

## Styling

**New file**: `src/app/pages/text/components/chain-meta-panels.component.scss`

All values use existing CSS tokens from the Bubls design system. No new tokens introduced.

```scss
:host {
  display: block;
  margin-top: var(--sp-3, 12px);
}

.inspector-toggle {
  appearance: none;
  border: 1px solid var(--hairline);
  background: transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  padding: 6px 14px;
  border-radius: var(--r-pill, 999px);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.inspector-body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4, 16px);
  padding-top: var(--sp-3, 12px);
}

.panel-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 var(--sp-2, 8px) 0;
}

.badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: var(--r-sm, 8px);
}

.badge--pass {
  background: color-mix(in srgb, var(--accent-sage) 18%, transparent);
  color: var(--accent-sage);
}

.badge--warn {
  background: color-mix(in srgb, var(--accent-warm) 18%, transparent);
  color: var(--accent-warm);
}

.lint-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2, 8px);
}

.lint-issue {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2, 8px);
  font-size: 14px;
  color: var(--text-secondary);
}

.score-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2, 8px);
}

.score-label {
  flex: 0 0 120px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: capitalize;
}

.score-bar {
  flex: 1;
  height: 6px;
  background: var(--hairline);
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  background: var(--accent-sage);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.score-value {
  flex: 0 0 40px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: right;
}
```

---

## Page Integration

### Signal additions to `text.page.ts`

```typescript
// New signals
protected readonly chainLint = signal<LintMeta | null>(null);
protected readonly chainScore = signal<ScoreMeta | null>(null);

// Helper
private parseMeta<T>(raw: string | undefined): T | null {
  if (!raw) return null;
  try { return JSON.parse(raw) as T; }
  catch { return null; }
}
```

### `runChain()` changes

At the top of `runChain()`, reset meta signals:
```typescript
this.chainLint.set(null);
this.chainScore.set(null);
```

After receiving the chain response, parse meta:
```typescript
if (res.meta) {
  this.chainLint.set(this.parseMeta<LintMeta>(res.meta['lint']));
  this.chainScore.set(this.parseMeta<ScoreMeta>(res.meta['score']));
}
```

### Template addition

Inside the `@if (state() === 'result' && chainFiles(); as files)` block, after `<app-chain-output-tabs>`:

```html
@if (chainLint() || chainScore()) {
  <app-chain-meta-panels
    [lint]="chainLint()"
    [score]="chainScore()"
    data-test="chain-meta-panels"
  ></app-chain-meta-panels>
}
```

### `rewrite()` and `generate()` reset

Both methods should reset chain meta signals at the top (since they are not chain operations):
```typescript
this.chainLint.set(null);
this.chainScore.set(null);
this.chainFiles.set(null);
```

---

## Mock Data

```typescript
// src/app/mocks/chain.mock.ts
export const MOCK_CHAIN_MULTI: ChainResponse = {
  generationId: '00000000-0000-0000-0000-000000000011',
  files: [
    { name: 'analysis.md', content: '# Analysis\n\nProblem: the braindump needs structure.' },
    { name: 'epic.md', content: '# Epic\n\nScope: three tasks, two weeks.' },
    { name: 'architecture.md', content: '# Architecture\n\nFlask + Angular + Neon.' },
  ],
  meta: {
    lint: '{"issues": ["Missing \\"Why now\\" section", "What section under 50 words"]}',
    score: '{"scores": {"structure": 0.85, "clarity": 0.92, "completeness": 0.78, "actionability": 0.88}}',
  },
};
```

---

## Affected Files Summary

| File | Action | Change |
|------|--------|--------|
| `src/app/services/text-api.service.ts` | Modify | Add `meta?: Record<string, string>` to `ChainResponse` |
| `src/app/mocks/chain.mock.ts` | Modify | Add `meta` to interface + `MOCK_CHAIN_MULTI` |
| `src/app/pages/text/text.page.ts` | Modify | Add signals, parse meta, wire component, reset on rewrite/generate |
| `src/app/pages/text/components/chain-meta-panels.component.ts` | Create (new) | Standalone component with lint + score panels |
| `src/app/pages/text/components/chain-meta-panels.component.scss` | Create (new) | Styling for inspector, badges, score bars |
| `src/app/pages/text/components/chain-meta-panels.component.spec.ts` | Create (new) | TestBed tests |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Chain runner fix hasn't shipped yet (no real `meta` data) | Mock mode provides sample data for development + testing. Toggle via `environment.useMocks.textChains`. |
| LLM returns malformed JSON in `meta` values | `parseMeta()` catches `JSON.parse` failures and returns `null`. Component renders nothing for null inputs. |
| Score dimension names vary between chain runs | Component renders whatever keys exist in `scores{}`. No hardcoded dimension names. `text-transform: capitalize` handles display. |
| Performance with many lint issues | Lint issues are typically 0--5 items. No virtualization needed. If a future chain returns 50+ issues, truncate in the page before passing to the component. |

---

## Tech Stack (no changes)

```
Frontend: Angular 19 + Ionic 8 (existing)
New:      1 component + 1 SCSS file + interface update
Backend:  No changes (prerequisite: chain runner fix epic)
```

No new dependencies. No new services. No new routes.

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)
- [Chain Runner Fix architecture](../chain-runner-fix-1776426025036/architecture.md) -- prerequisite backend work

===END===
