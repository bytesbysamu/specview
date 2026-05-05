# Task 6: Chain Mode UI

**Purpose**: Extend the /text page with a second row of chain-mode buttons (sage accent), loading state with step progress, tabbed output for multi-file chains, and a null-object feature guard for gated users.

**Effort**: 1 day

**Dependencies**: Task 3 (Deep Humanize), Task 4 (Braindump to Docs), Task 5 (Rewrite + Review) — all three chain definitions must be landed so the UI can call them. Task 2 (Chain Runner + Endpoint) provides `POST /api/text/chain`.

**Blocks**: Task 7 (Integration Test + QA)

**Related**:
- [Architecture](./architecture.md) — Frontend: Chain Mode UI section, feature guard null-object table
- [Epic](./epic.md) — Task 6 detail, `data-test` selector inventory

---

## 1. Context

The /text page currently has one row of typewriter keys for single-shot modes (humanize, expand, compress, clarify, formalize) plus a Generate button. This task adds a second row of chain-mode buttons below the existing keys, a step-progress loading indicator, and a tabbed output area for multi-file chain results (braindump-to-docs). The chain buttons use a sage accent color (distinct from the warm accent of single-shot keys) to visually signal "multi-step, takes longer."

The feature guard follows the null-object pattern already established in the codebase (architecture doc, `require_feature` in `server/core/auth.py`): when `text_chains` is not in the user's `enabled_features`, chain buttons render locked (`opacity: 0.5`) with a "Pro" badge overlay. Tapping a locked button shows an upgrade toast. The buttons are never hidden. The backend returns `403 { error: "text_chains not enabled", upgrade: true }` — the frontend handles this as a specific case of the existing error flow.

**Trade-offs considered**:
- **Shared `TypewriterKeysComponent` with different accent vs. new component** — chose reuse with an `accent` input. The typewriter-keys component is already generic over string-keyed modes. Adding an `[accent]` CSS class input avoids duplicating the carriage frame, key depression, and `data-test` generation logic. A new component would only diverge on color.
- **Tabbed output as a new standalone component vs. inline template** — chose new standalone `ChainOutputTabsComponent`. The tab state (active tab signal, per-tab copy) is self-contained and has its own `data-test` selectors. Inlining would bloat `text.page.ts` beyond the 80-line component target.
- **Step progress via polling vs. response metadata** — chose response metadata. The chain endpoint is synchronous (request-response, not SSE per architecture doc). The loading indicator shows a generic "Step X of Y..." derived from the chain definition's `steps.length` (known client-side from the button config), ticking through steps on a timer estimate. Exact per-step progress would require SSE, which is deferred.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status
git diff HEAD -- src/app/pages/text/ src/app/services/text-api.service.ts src/app/mocks/text.mock.ts
npm test -- --watch=false --browsers=ChromeHeadless   # Record FE baseline: [N passing]
cd server && pytest -q                                 # Record BE baseline (untouched by this task)
```

**Pre-conditions**:
- `ls server/modules/chain/definitions/` prints `deep-humanize.json`, `braindump-to-docs.json`, `rewrite-review.json`. If any are missing, STOP — prerequisite tasks not landed.
- The text page exists at `src/app/pages/text/text.page.ts` (confirmed from codebase scan).
- `grep -n 'TypewriterKeysComponent' src/app/pages/text/text.page.ts` returns a hit (the UX revamp shipped it).

**Baseline recorded**: fill in `[FE: N/N passing]` in commit bodies.

---

## 3. Files

### To Create (new)
- `src/app/pages/text/components/chain-output-tabs.component.ts` — standalone OnPush component: tabbed output for multi-file chain results. Inputs: `files: Array<{name: string; content: string}>`. Emits nothing (read-only display). Contains per-tab copy button and active-tab signal. `data-test` selectors on every interactive element.
- `src/app/pages/text/components/chain-output-tabs.component.scss` — tab bar styling, active-tab indicator, copy button, content area using Cormorant-italic `.manuscript` class.
- `src/app/pages/text/components/chain-output-tabs.component.spec.ts` — TestBed spec with Page Object and `data-test` selectors.
- `src/app/mocks/chain.mock.ts` — mock chain responses: `MOCK_CHAIN_SINGLE` (deep-humanize shape) and `MOCK_CHAIN_MULTI` (braindump-to-docs shape with 3 files).

### To Modify
- `src/app/services/text-api.service.ts` — add `ChainResponse` interface, `ChainRequest` type, `chainRun(chainId: string, input: string): Promise<ChainResponse>` method with mock toggle, 403 handling with upgrade hint detection.
- `src/app/services/text-api.service.spec.ts` — add tests for `chainRun`: happy path single-file, happy path multi-file, 403 feature-gated, mock mode.
- `src/app/pages/text/text.page.ts` — add second row of chain-mode keys (reusing `TypewriterKeysComponent` with `accent` class), chain execution method, step-progress state, conditional rendering of `ChainOutputTabsComponent` for multi-file results, feature guard null-object logic.
- `src/app/pages/text/text.page.scss` — add chain-row styling (sage accent tokens: `--accent-sage`, `--accent-sage-tint`), locked-button styling (`.key--locked` with `opacity: 0.5` and Pro badge overlay), step-progress indicator styling.
- `src/app/pages/text/text.page.spec.ts` — add tests for chain button rendering, locked state, chain execution flow, tab output rendering.
- `src/app/pages/text/components/typewriter-keys.component.ts` — add optional `accent` input (`'warm' | 'sage'`, default `'warm'`) that applies a CSS class to the carriage; add optional `locked` input (boolean, default `false`) that overlays a Pro badge and disables click.
- `src/app/pages/text/components/typewriter-keys.component.scss` — add `.carriage--sage` accent variant (sage green tint on selected key, sage border on selected), `.key--locked` styling with pseudo-element "Pro" badge.
- `src/app/pages/text/components/typewriter-keys.component.spec.ts` — add tests for sage accent class, locked state rendering.
- `src/app/mocks/text.mock.ts` — re-export chain mocks for the text page's mock toggle.
- `src/environments/environment.ts` — add `textChains: false` to `useMocks` (chains always hit real API in dev; mock only for tests).

### To Leave Alone
- `server/` — no backend changes in this task. The endpoint and chain definitions are already landed.
- `src/app/services/auth-token.service.ts` — bearer token plumbing is unchanged.
- `src/app/pages/photoshoot/` — different feature, different world.
- `src/app/pages/dashboard/` — unrelated.
- `src/app/components/` — no shared components modified.

---

## 4. Implementation Steps

### Step 1: Add chain mock data

**Action**: Create `src/app/mocks/chain.mock.ts` with two mock responses matching the `ChainResponse` shape. One single-file (deep-humanize), one multi-file (braindump-to-docs with 3 files).

**File**: `src/app/mocks/chain.mock.ts` (new)

**Pattern**:
```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
}

export const MOCK_CHAIN_SINGLE: ChainResponse = {
  generationId: '00000000-0000-0000-0000-000000000010',
  result: 'Honestly, the quick brown fox — well, it sort of jumps. Three passes later, even the dog notices.',
};

export const MOCK_CHAIN_MULTI: ChainResponse = {
  generationId: '00000000-0000-0000-0000-000000000011',
  files: [
    { name: 'analysis.md', content: '# Analysis\n\nProblem: the braindump needs structure.' },
    { name: 'epic.md', content: '# Epic\n\nScope: three tasks, two weeks.' },
    { name: 'architecture.md', content: '# Architecture\n\nFlask + Angular + Neon.' },
  ],
};
```

**Verify**:
```bash
npx tsc --noEmit src/app/mocks/chain.mock.ts 2>&1 | head -5
```

### Step 2: Add `ChainResponse` and `chainRun()` to `TextApiService`

**Action**: Define `ChainResponse` and `ChainRequest` types. Add `chainRun(chainId: string, input: string): Promise<ChainResponse>` method following the same pattern as `rewrite()` and `generate()` — bearer auth, mock toggle, error mapping. The 403 response from the backend includes `upgrade: true`; detect this and throw a typed error so the UI can show an upgrade toast.

**File**: `src/app/services/text-api.service.ts`

**Pattern**:
```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
}

export interface ChainRequest {
  chainId: string;
  input: string;
}

// Inside TextApiService class:
async chainRun(chainId: string, input: string): Promise<ChainResponse> {
  if (environment.useMocks.textChains) {
    await delay(MOCK_DELAY_MS * 3); // chains take longer
    return chainId === 'braindump-to-docs'
      ? { ...MOCK_CHAIN_MULTI }
      : { ...MOCK_CHAIN_SINGLE };
  }

  const res = await fetch(`${this.baseUrl}/chain`, {
    method: 'POST',
    headers: this.jsonHeaders(),
    body: JSON.stringify({ chainId, input } satisfies ChainRequest),
  });
  if (!res.ok) throw await toError(res);
  return (await res.json()) as ChainResponse;
}
```

Update the `TextApi` interface:
```typescript
export interface TextApi {
  rewrite(text: string, mode: RewriteMode): Promise<RewriteResponse>;
  generate(prompt: string): Promise<GenerateResponse>;
  chainRun(chainId: string, input: string): Promise<ChainResponse>;
}
```

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 3: Add `chainRun` tests to `text-api.service.spec.ts`

**Action**: Four new tests: happy path single-file, happy path multi-file, 403 feature-gated rejection, mock mode returns fixture.

**File**: `src/app/services/text-api.service.spec.ts`

**Pattern**: see Section 5.

**Verify**:
```bash
npm test -- --watch=false --browsers=ChromeHeadless --include='**/text-api.service.spec.ts'
```

### Step 4: Extend `TypewriterKeysComponent` with `accent` and `locked` inputs

**Action**: Add `@Input() accent: 'warm' | 'sage' = 'warm'` and `@Input() locked = false`. When `accent === 'sage'`, apply `carriage--sage` class to the carriage div. When `locked === true`, each key gets `key--locked` class (visual: `opacity: 0.5`, Pro badge pseudo-element), clicks are suppressed (emit nothing), and the component emits a new `@Output() lockedTap = new EventEmitter<void>()` instead.

**File**: `src/app/pages/text/components/typewriter-keys.component.ts`

**Pattern**:
```typescript
@Input() accent: 'warm' | 'sage' = 'warm';
@Input() locked = false;
@Output() lockedTap = new EventEmitter<void>();

// In template:
// <div class="carriage" [class.carriage--sage]="accent === 'sage'" ...>
//   <button ... [class.key--locked]="locked" [disabled]="disabled || locked"
//     (click)="locked ? lockedTap.emit() : modeChange.emit(k.mode)">
//     <span class="key__face">{{ k.label }}</span>
//     @if (locked) { <span class="pro-badge" data-test="pro-badge">Pro</span> }
//   </button>
```

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 5: Add sage accent and locked-key styles

**Action**: Add `.carriage--sage` variant with sage green tint for selected keys. Add `.key--locked` styling: `opacity: 0.5`, `cursor: not-allowed`, `.pro-badge` positioned as an overlay (top-right, small pill with `--accent-sage` background). Add `--accent-sage` and `--accent-sage-tint` custom properties to `text.page.scss` (scoped to `:host`, not global tokens — only the text page uses sage).

**File**: `src/app/pages/text/components/typewriter-keys.component.scss` and `src/app/pages/text/text.page.scss`

**Pattern** (typewriter-keys.component.scss additions):
```scss
.carriage--sage .key--selected {
  color: var(--accent-sage);
  border-color: color-mix(in srgb, var(--accent-sage) 50%, var(--hairline));
}

.carriage--sage .key:active:not(:disabled):not(.key--locked),
.carriage--sage .key--selected {
  background: var(--accent-sage-tint, var(--surface));
}

.key--locked {
  opacity: 0.5;
  cursor: not-allowed;
  position: relative;
}

.pro-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: var(--accent-sage);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 2px 5px;
  border-radius: var(--r-pill, 999px);
  line-height: 1;
  pointer-events: none;
}
```

**Pattern** (text.page.scss additions):
```scss
:host {
  --accent-sage: #5a7a6a;
  --accent-sage-tint: color-mix(in srgb, var(--accent-sage) 12%, var(--surface));
}
```

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 6: Create `ChainOutputTabsComponent`

**Action**: Standalone OnPush component. Input: `files: Array<{name: string; content: string}>`. Internal signal: `activeTab = signal(0)`. Each tab has `data-test="chain-tab-{filename}"`. Active tab content renders in `.manuscript` class (Cormorant-italic, matching single-file output). Per-tab copy button with `data-test="chain-copy-tab"`.

**File**: `src/app/pages/text/components/chain-output-tabs.component.ts` (new)

**Pattern**:
```typescript
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ChainFile {
  name: string;
  content: string;
}

@Component({
  selector: 'app-chain-output-tabs',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="tabs" role="tablist" data-test="chain-tabs">
      <button
        *ngFor="let f of files; let i = index"
        type="button"
        role="tab"
        class="tab"
        [class.tab--active]="activeTab() === i"
        [attr.data-test]="'chain-tab-' + f.name"
        [attr.aria-selected]="activeTab() === i"
        (click)="activeTab.set(i)"
      >{{ f.name }}</button>
    </div>
    @if (files[activeTab()]; as activeFile) {
      <section class="tab-content" role="tabpanel">
        <header class="tab-head">
          <span class="tab-label">{{ activeFile.name }}</span>
          <button
            type="button"
            class="copy-btn"
            data-test="chain-copy-tab"
            (click)="copyTab(activeFile.content)"
          >{{ justCopied() ? 'Copied' : 'Copy' }}</button>
        </header>
        <article class="manuscript" data-test="chain-tab-content">{{ activeFile.content }}</article>
      </section>
    }
  `,
  styleUrls: ['./chain-output-tabs.component.scss'],
})
export class ChainOutputTabsComponent {
  @Input({ required: true }) files: ChainFile[] = [];
  readonly activeTab = signal(0);
  readonly justCopied = signal(false);

  async copyTab(content: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(content);
      this.justCopied.set(true);
      setTimeout(() => this.justCopied.set(false), 1500);
    } catch {
      // Clipboard can fail on non-https / older WebViews; swallow.
    }
  }
}
```

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 7: Create `chain-output-tabs.component.scss`

**Action**: Tab bar, active indicator, content area. All colors via tokens.

**File**: `src/app/pages/text/components/chain-output-tabs.component.scss` (new)

**Pattern**:
```scss
:host {
  display: block;
}

.tabs {
  display: flex;
  gap: var(--sp-1, 4px);
  padding: var(--sp-2, 8px) 0;
  border-bottom: 1px solid var(--hairline);
  overflow-x: auto;
}

.tab {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--r-sm, 8px);
  cursor: pointer;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
}

.tab--active {
  background: var(--accent-sage-tint, var(--surface-elevated));
  color: var(--accent-sage, var(--text-primary));
}

.tab-content {
  padding: var(--sp-3, 12px) 0;
}

.tab-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-2, 8px);
}

.tab-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
}

.copy-btn {
  appearance: none;
  border: 1px solid var(--hairline);
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: var(--r-pill, 999px);
  cursor: pointer;
}

.manuscript {
  font-family: var(--font-display, 'Cormorant Garamond', Georgia, serif);
  font-style: italic;
  font-size: 1.15rem;
  line-height: 1.65;
  white-space: pre-wrap;
  color: var(--text-primary);
}
```

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 8: Create `chain-output-tabs.component.spec.ts`

**Action**: TestBed spec with Page Object. Tests: renders N tabs for N files, clicking tab switches content, copy button calls clipboard API.

**File**: `src/app/pages/text/components/chain-output-tabs.component.spec.ts` (new)

**Pattern**: see Section 5.

**Verify**:
```bash
npm test -- --watch=false --browsers=ChromeHeadless --include='**/chain-output-tabs.component.spec.ts'
```

### Step 9: Wire chain buttons and chain execution into `text.page.ts`

**Action**: Add a second `<app-typewriter-keys>` row below the existing one with chain modes, `accent="sage"`, `[locked]` bound to a `textChainsEnabled` signal. Add chain execution: `runChain(chainId: string)` method that calls `api.chainRun()`, handles the response (single-file -> existing output area with reveal, multi-file -> `ChainOutputTabsComponent`). Add step-progress state: `chainStep = signal<{current: number; total: number} | null>(null)` with a timer that ticks through steps during execution. Add feature guard: when locked, tapping a chain key shows a toast via the existing Ionic toast controller pattern.

**File**: `src/app/pages/text/text.page.ts`

**Pattern**:
```typescript
import { ChainOutputTabsComponent } from './components/chain-output-tabs.component';
import { type ChainResponse } from '../../services/text-api.service';

// Chain mode definitions (inside the class or above it)
const CHAIN_MODES: { mode: string; label: string }[] = [
  { mode: 'deep-humanize', label: 'Deep Humanize' },
  { mode: 'braindump-to-docs', label: 'Brain Dump' },
  { mode: 'rewrite-review', label: 'Rewrite+Review' },
];

// Step counts per chain (derived from chain definitions, hardcoded client-side)
const CHAIN_STEP_COUNTS: Record<string, number> = {
  'deep-humanize': 3,
  'braindump-to-docs': 3,
  'rewrite-review': 3,
};

// Inside the class:
protected readonly chainModes = CHAIN_MODES;
protected readonly textChainsEnabled = signal(true); // TODO: wire to user.enabled_features
protected readonly chainFiles = signal<Array<{name: string; content: string}> | null>(null);
protected readonly chainStep = signal<{current: number; total: number} | null>(null);
private chainStepTimer: ReturnType<typeof setInterval> | null = null;

protected onChainKeyPress(chainId: string): void {
  if (!this.textChainsEnabled()) {
    // Show upgrade toast
    return;
  }
  void this.runChain(chainId);
}

protected async runChain(chainId: string): Promise<void> {
  if (!this.canSubmit()) return;
  this.clearReveal();
  this.chainFiles.set(null);
  this.state.set('running');
  this.actingMode.set(null);
  this.errorMsg.set(null);
  this.startChainProgress(chainId);
  try {
    const res: ChainResponse = await this.api.chainRun(chainId, this.input());
    this.stopChainProgress();
    if (res.files && res.files.length > 0) {
      this.chainFiles.set(res.files);
      this.output.set(null);
      this.state.set('result');
    } else if (res.result) {
      this.chainFiles.set(null);
      this.output.set(res.result);
      this.state.set('result');
      this.startReveal(res.result);
    }
  } catch (e) {
    this.stopChainProgress();
    this.errorMsg.set(e instanceof Error ? e.message : 'Chain failed');
    this.state.set('error');
  }
}

private startChainProgress(chainId: string): void {
  const total = CHAIN_STEP_COUNTS[chainId] ?? 3;
  this.chainStep.set({ current: 1, total });
  this.chainStepTimer = setInterval(() => {
    const step = this.chainStep();
    if (step && step.current < step.total) {
      this.chainStep.set({ current: step.current + 1, total: step.total });
    }
  }, 4000); // Estimate ~4s per step
}

private stopChainProgress(): void {
  if (this.chainStepTimer !== null) {
    clearInterval(this.chainStepTimer);
    this.chainStepTimer = null;
  }
  this.chainStep.set(null);
}
```

Template additions (within the `<div class="wrap">`, after the existing `<app-typewriter-keys>`):
```html
<app-typewriter-keys
  [keys]="chainModes"
  [selected]="null"
  [disabled]="!canSubmit() || state() === 'running'"
  [accent]="'sage'"
  [locked]="!textChainsEnabled()"
  (modeChange)="onChainKeyPress($event)"
  (lockedTap)="showUpgradeToast()"
  data-test="chain-keys"
></app-typewriter-keys>

@if (state() === 'running' && chainStep(); as step) {
  <p class="status chain-progress" data-test="chain-step-progress">
    Step {{ step.current }} of {{ step.total }}...
  </p>
}

@if (state() === 'result' && chainFiles(); as files) {
  <section class="result" data-test="text-result">
    <header class="result-head">
      <span class="eyebrow">Chain Result</span>
    </header>
    <app-chain-output-tabs [files]="files"></app-chain-output-tabs>
  </section>
}
```

Add `ChainOutputTabsComponent` to the component's `imports` array.

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 10: Add chain-specific styles to `text.page.scss`

**Action**: Add step-progress styling, sage accent custom properties (if not already added in Step 5), and chain result area spacing.

**File**: `src/app/pages/text/text.page.scss`

**Pattern**:
```scss
.chain-progress {
  font-size: 14px;
  font-style: italic;
  color: var(--accent-sage, var(--text-secondary));
  margin: 0;
}
```

**Verify**:
```bash
npm run build -- --configuration=development 2>&1 | tail -3
```

### Step 11: Add `text.page.spec.ts` chain-mode tests

**Action**: Extend the existing spec with chain-specific tests: chain buttons render, locked buttons show Pro badge, chain execution calls `api.chainRun`, multi-file result renders tabs, step progress shows during execution.

**File**: `src/app/pages/text/text.page.spec.ts`

**Pattern**: see Section 5.

**Verify**:
```bash
npm test -- --watch=false --browsers=ChromeHeadless --include='**/text.page.spec.ts'
```

### Step 12: Add typewriter-keys locked/accent tests

**Action**: Extend the existing spec with two tests: sage accent applies `carriage--sage` class, locked mode renders Pro badge and suppresses click.

**File**: `src/app/pages/text/components/typewriter-keys.component.spec.ts`

**Pattern**: see Section 5.

**Verify**:
```bash
npm test -- --watch=false --browsers=ChromeHeadless --include='**/typewriter-keys.component.spec.ts'
```

---

## 5. Tests

Framework: Jasmine + Karma + Angular TestBed. Naming: `condition_expectedOutcome`. All queries via `data-test` selectors.

### `src/app/services/text-api.service.spec.ts` additions

```typescript
import { MOCK_CHAIN_SINGLE, MOCK_CHAIN_MULTI } from '../mocks/chain.mock';

// Inside the 'real mode' describe block:

it('chainRun_postsToChainEndpointWithBearer', async () => {
  const body = { generationId: 'g-10', result: 'chain output' };
  window.fetch = jasmine.createSpy('fetch').and.resolveTo(fakeJsonResponse(body));

  const result = await service.chainRun('deep-humanize', 'some input');

  expect(result).toEqual(body);
  const [url, init] = (window.fetch as jasmine.Spy).calls.mostRecent().args;
  expect(url).toContain('/text/chain');
  expect(init.method).toBe('POST');
  expect(init.headers.Authorization).toBe(`Bearer ${TOKEN}`);
  expect(JSON.parse(init.body)).toEqual({ chainId: 'deep-humanize', input: 'some input' });
});

it('chainRun_multiFileResponse_returnFilesArray', async () => {
  const body = {
    generationId: 'g-11',
    files: [{ name: 'a.md', content: '# A' }, { name: 'b.md', content: '# B' }],
  };
  window.fetch = jasmine.createSpy('fetch').and.resolveTo(fakeJsonResponse(body));

  const result = await service.chainRun('braindump-to-docs', 'brain dump');

  expect(result.files?.length).toBe(2);
  expect(result.files?.[0].name).toBe('a.md');
});

it('chainRun_403_rejectsWithFeatureError', async () => {
  window.fetch = jasmine
    .createSpy('fetch')
    .and.resolveTo(
      fakeJsonResponse({ error: 'text_chains not enabled', upgrade: true }, 403),
    );

  await expectAsync(service.chainRun('deep-humanize', 'x')).toBeRejectedWithError(
    /text_chains not enabled/,
  );
});

// Inside the 'mock mode' describe block:

it('chainRun_mockMode_returnsSingleFixture', async () => {
  environment.useMocks = { picks: true, photoshoot: false, text: true, textChains: true };
  const promise = service.chainRun('deep-humanize', 'test');
  jasmine.clock().tick(5000);
  const result = await promise;
  expect(result.generationId).toBeTruthy();
  expect(result.result).toBeTruthy();
});
```

### `src/app/pages/text/components/chain-output-tabs.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChainOutputTabsComponent, type ChainFile } from './chain-output-tabs.component';

class TabsPO {
  constructor(private readonly f: ComponentFixture<ChainOutputTabsComponent>) {}

  get tabs(): HTMLElement[] {
    return Array.from(this.f.nativeElement.querySelectorAll('[data-test^="chain-tab-"]'));
  }

  tabFor(name: string): HTMLButtonElement | null {
    return this.f.nativeElement.querySelector(`[data-test="chain-tab-${name}"]`);
  }

  get content(): HTMLElement | null {
    return this.f.nativeElement.querySelector('[data-test="chain-tab-content"]');
  }

  get copyBtn(): HTMLButtonElement | null {
    return this.f.nativeElement.querySelector('[data-test="chain-copy-tab"]');
  }
}

describe('ChainOutputTabsComponent', () => {
  let fixture: ComponentFixture<ChainOutputTabsComponent>;
  let component: ChainOutputTabsComponent;
  let po: TabsPO;

  const FILES: ChainFile[] = [
    { name: 'analysis.md', content: '# Analysis\nContent A' },
    { name: 'epic.md', content: '# Epic\nContent B' },
    { name: 'architecture.md', content: '# Architecture\nContent C' },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChainOutputTabsComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(ChainOutputTabsComponent);
    component = fixture.componentInstance;
    component.files = FILES;
    fixture.detectChanges();
    po = new TabsPO(fixture);
  });

  it('threeFiles_rendersThreeTabs', () => {
    expect(po.tabs.length).toBe(3);
  });

  it('firstTabActiveByDefault_showsFirstFileContent', () => {
    expect(po.content?.textContent).toContain('Content A');
    expect(po.tabFor('analysis.md')?.getAttribute('aria-selected')).toBe('true');
  });

  it('clickSecondTab_switchesToSecondFileContent', () => {
    po.tabFor('epic.md')!.click();
    fixture.detectChanges();
    expect(po.content?.textContent).toContain('Content B');
    expect(po.tabFor('epic.md')?.classList.contains('tab--active')).toBeTrue();
  });

  it('copyButton_callsClipboardWriteText', async () => {
    spyOn(navigator.clipboard, 'writeText').and.resolveTo();
    po.copyBtn!.click();
    await fixture.whenStable();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('# Analysis\nContent A');
  });
});
```

### `src/app/pages/text/text.page.spec.ts` additions

```typescript
// Add to the existing TextPO class:
// get chainKeys(): HTMLElement | null {
//   return this.f.nativeElement.querySelector("[data-test='chain-keys']");
// }
// chainBtn(chainId: string): HTMLButtonElement | null {
//   return this.f.nativeElement.querySelector(`[data-test='typewriter-key-${chainId}']`);
// }
// get stepProgress(): HTMLElement | null {
//   return this.f.nativeElement.querySelector("[data-test='chain-step-progress']");
// }
// get chainTabs(): HTMLElement | null {
//   return this.f.nativeElement.querySelector("[data-test='chain-tabs']");
// }

describe('TextPage chain mode', () => {
  let fixture: ComponentFixture<TextPage>;
  let api: jasmine.SpyObj<TextApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('TextApiService', ['rewrite', 'generate', 'chainRun']);
    spyOn(window, 'matchMedia').and.returnValue({ matches: true } as MediaQueryList);
    await TestBed.configureTestingModule({
      imports: [TextPage],
      providers: [{ provide: TextApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(TextPage);
  });

  it('chainButtons_renderedWithSageAccent', () => {
    fixture.detectChanges();
    const chainKeys = fixture.nativeElement.querySelector("[data-test='chain-keys']");
    expect(chainKeys).not.toBeNull();
    const deepHumanize = fixture.nativeElement.querySelector(
      "[data-test='typewriter-key-deep-humanize']",
    );
    expect(deepHumanize).not.toBeNull();
  });

  it('chainRun_singleFile_showsResultInOutputArea', async () => {
    api.chainRun.and.resolveTo({ generationId: 'g1', result: 'chain output text' });
    fixture.detectChanges();
    const comp = fixture.componentInstance as any;
    comp.input.set('some input text');
    fixture.detectChanges();

    await comp.runChain('deep-humanize');
    fixture.detectChanges();

    const output = fixture.nativeElement.querySelector("[data-test='text-output']");
    expect(output?.textContent).toContain('chain output text');
  });

  it('chainRun_multiFile_showsTabsComponent', async () => {
    api.chainRun.and.resolveTo({
      generationId: 'g2',
      files: [
        { name: 'a.md', content: '# A' },
        { name: 'b.md', content: '# B' },
      ],
    });
    fixture.detectChanges();
    const comp = fixture.componentInstance as any;
    comp.input.set('brain dump text');
    fixture.detectChanges();

    await comp.runChain('braindump-to-docs');
    fixture.detectChanges();

    const tabs = fixture.nativeElement.querySelector("[data-test='chain-tabs']");
    expect(tabs).not.toBeNull();
    const tabA = fixture.nativeElement.querySelector("[data-test='chain-tab-a.md']");
    expect(tabA).not.toBeNull();
  });

  it('chainRunError_showsErrorMessage', async () => {
    api.chainRun.and.rejectWith(new Error('text_chains not enabled'));
    fixture.detectChanges();
    const comp = fixture.componentInstance as any;
    comp.input.set('some input');
    fixture.detectChanges();

    await comp.runChain('deep-humanize');
    fixture.detectChanges();

    const errorEl = fixture.nativeElement.querySelector("[data-test='text-error']");
    expect(errorEl?.textContent).toContain('text_chains not enabled');
  });
});
```

### `src/app/pages/text/components/typewriter-keys.component.spec.ts` additions

```typescript
it('sageAccent_appliesCarriageSageClass', () => {
  component.accent = 'sage';
  fixture.detectChanges();
  const carriage = fixture.nativeElement.querySelector("[data-test='typewriter-carriage']");
  expect(carriage.classList.contains('carriage--sage')).toBeTrue();
});

it('lockedMode_rendersProBadgeAndSuppressesClick', () => {
  component.locked = true;
  fixture.detectChanges();
  const badge = fixture.nativeElement.querySelector("[data-test='pro-badge']");
  expect(badge).not.toBeNull();
  expect(badge?.textContent?.trim()).toBe('Pro');

  let emitted = false;
  component.modeChange.subscribe(() => (emitted = true));
  const firstKey = fixture.nativeElement.querySelector("[data-test^='typewriter-key-']");
  firstKey?.click();
  expect(emitted).toBeFalse();
});
```

---

## 6. Commit Plan

1. `feat(text): chain mock data` — `src/app/mocks/chain.mock.ts`: `MOCK_CHAIN_SINGLE` and `MOCK_CHAIN_MULTI` fixtures.

2. `feat(text): TextApiService.chainRun + ChainResponse type` — `src/app/services/text-api.service.ts`: new method, types, mock toggle. `src/app/services/text-api.service.spec.ts`: 4 new tests.

3. `feat(text): typewriter-keys accent + locked inputs` — `src/app/pages/text/components/typewriter-keys.component.ts`: `accent`, `locked`, `lockedTap` inputs/outputs. `typewriter-keys.component.scss`: `.carriage--sage`, `.key--locked`, `.pro-badge`. `typewriter-keys.component.spec.ts`: 2 new tests.

4. `feat(text): ChainOutputTabsComponent` — `src/app/pages/text/components/chain-output-tabs.component.ts` + `.scss` + `.spec.ts`: standalone tabbed output, 4 new tests.

5. `feat(text): chain mode UI — buttons, progress, tabs wired` — `src/app/pages/text/text.page.ts`: second key row, `runChain()`, step progress, feature guard, `ChainOutputTabsComponent` import. `text.page.scss`: sage accent properties, chain-progress styling. `text.page.spec.ts`: 4 new tests.

6. `feat(text): add textChains mock toggle to environment` — `src/environments/environment.ts`: `textChains: false` in `useMocks`.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build -- --configuration=development
```

**Expected delta**: FE `[N]` -> `[N+14]` passing (4 service tests + 4 tabs tests + 2 typewriter-keys tests + 4 text page chain tests). Zero pre-existing tests broken. Backend untouched — `cd server && pytest -q` must still report the baseline pass count.

**Manual smoke** (both light and dark themes):
1. Open `/text` — second row of sage-accent keys visible below existing typewriter keys.
2. Type text, tap "Deep Humanize" — step progress shows "Step 1 of 3...", result appears in existing output area with char-reveal.
3. Type braindump, tap "Brain Dump" — step progress shows, result appears as tabbed output; clicking tabs switches content; copy-per-tab works.
4. Set `textChainsEnabled` to `false` (in dev tools or mock) — chain keys show locked with Pro badge, tapping shows upgrade toast, existing single-shot keys still work.

**`data-test` selector audit**:
```bash
grep -rn 'data-test=' src/app/pages/text/ --include="*.ts" | grep -oP "data-test=['\"]([^'\"]+)" | sort -u
```
Must include: `chain-keys`, `chain-deep-humanize` (via `typewriter-key-deep-humanize`), `chain-braindump` (via `typewriter-key-braindump-to-docs`), `chain-rewrite-review` (via `typewriter-key-rewrite-review`), `chain-tabs`, `chain-tab-{filename}`, `chain-copy-tab`, `chain-step-progress`, `pro-badge`.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any one unit.
  - Commit 1 (mocks): removes mock data; no consumers at this point.
  - Commit 2 (service): reverts `chainRun` method; chain buttons become dead code (acceptable if Task 6 is fully rolled back).
  - Commit 3 (typewriter-keys): reverts accent/locked inputs; chain row falls back to warm accent, no Pro badge. Existing single-shot keys unaffected.
  - Commit 4 (tabs component): reverts the standalone component; multi-file chains have no UI but single-file chains still work.
  - Commit 5 (page wiring): reverts the chain key row and execution logic; page returns to single-shot-only state.
  - Commit 6 (environment): reverts mock toggle; no production impact.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch. No migrations in this task. No backend changes. No shared-module changes beyond the text page boundary.

---

## 9. Deviations Allowed

- **`TypewriterKeysComponent` uses signals instead of `@Input()` decorators** — if the UX revamp migrated to signal-based inputs, add `accent` and `locked` as signal inputs instead; update the template binding syntax; log in commit body.
- **Page template is inline (not separate `.html` file)** — confirmed from codebase: the template is inline in `text.page.ts`. All template edits go in the `template` string; log if the guide's step references a `.html` file that does not exist.
- **`environment.useMocks` does not have a `textChains` key** — add it as part of Step 12 / Commit 6; if the type is strict, extend the interface; log in commit body.
- **Ionic toast not yet available** — if the app does not have a toast utility, use `window.alert('Upgrade to Pro')` as a placeholder; log in commit body; this is the null-object guard and must show some feedback.
- **Chain step count differs from 3** — if a chain definition has a different step count, update `CHAIN_STEP_COUNTS` to match; log in commit body.
- **`ChainResponse` type already defined elsewhere** — if Task 2 or the OpenAPI codegen already generated this type, import from the existing location instead of re-declaring; log in commit body.
- **Side-effect required** (push, publish, migration) — STOP and mark `[REQUIRES APPROVAL]`. This task should not need any.

---

## 10. Out of Scope

The executor must STOP and flag (not absorb) any of the following:

- **SSE/streaming per chain step** — v1 is request-response. Step progress is estimated client-side. Streaming deferred per architecture doc; trigger: chains exceeding 30s with user-reported perceived hangs.
- **Real `text_chains` feature flag resolution from user object** — the `textChainsEnabled` signal is hardcoded to `true` for v1. Wiring it to `user.enabled_features.text_chains` is a follow-up once the user service exposes feature flags to the frontend.
- **Upgrade flow / payment integration** — the upgrade toast is a dead-end placeholder. Stripe integration is a separate epic.
- **Custom chain composition UI** — users cannot create or edit chains. Fixed chain definitions only.
- **Backend changes** — this task is frontend-only. If a backend bug is discovered during development, flag it for the relevant task owner.
- **Modifying existing single-shot modes** — additive only. The existing typewriter keys, generate button, and output area must not change behavior.
- **Cost tracking UI / analytics dashboard** — the `chainCompleted` event is backend-only; no frontend analytics in this task.
- **Extracting shared tab component to `src/app/components/`** — `ChainOutputTabsComponent` stays inside the text page boundary until a second consumer appears.
- **Dark-mode sage color tuning** — ship the initial values; tune after Task 7's WCAG check provides contrast data.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) -- Frontend: Chain Mode UI section, feature guard null-object table
- [Epic](./epic.md) -- Task 6 detail, data-test selector inventory
- [Timeline](./timeline.md) -- Status tracking (update after done)
