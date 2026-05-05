# 🛠️ Task 5: Text Writer's Desk Pass

**Purpose**: Give the Text feature a manuscript identity — vellum page, typewriter-key mode buttons, Cormorant-italic output with a reduced-motion-aware char-by-char reveal.

**Effort**: 1 day

**Dependencies**: Task 1 (Dual-Mode Token Plumbing) — `:root[data-theme="dark"]`, `--page-bg`, `--surface`, `--text-primary`, `--hairline`, `--world-bg` must already exist in `src/theme/tokens.scss`.

**Parallel With**: Task 2 (Onboarding), Task 3 (Picks), Task 4 (Photoshoot)

**Blocks**: Task 6 (A11y + Screenshot QA) — contrast script reads the new `--accent-paper` pair.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The Text feature today shares the generic dark surface with every other tab. The revamp gives each world its own aesthetic; "writer's desk" is the text world — vellum paper, inked accents, a typewriter sitting under the mode buttons, and output that reveals character-by-character so the user feels composition rather than API response. All changes stay inside `src/app/features/text/` plus one token addition (`--accent-paper`). No new providers, no new endpoints, no cross-feature imports.

**Trade-offs considered**:
- **Canvas-based ink animation** — rejected because a single `setInterval` on a signal proves the char-reveal concept with ~15 lines; a canvas engine would be infrastructure for one consumer.
- **Shared noise-overlay asset in `src/theme/`** — rejected because only Text uses vellum-grain; per the "not-yet-built is the right state" rule, a second consumer can extract it when it arrives.
- **Signal-driven `setInterval` char reveal at 18ms/char with `prefers-reduced-motion` fallback** — preferred: smallest possible surface, zero deps, framework-native reactivity, a11y floor preserved.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- src/app/features/text/ src/theme/tokens.scss
npm test -- --watch=false --browsers=ChromeHeadless   # Record FE baseline pass count
cd server && pytest -q                        # Record BE baseline (should be untouched by this task)
```

**If working tree is dirty on `src/app/features/text/` or `src/theme/tokens.scss`**: stash or commit unrelated changes separately before starting.

**Task-1 sanity check**: `grep -n 'data-theme="dark"' src/theme/tokens.scss` must return a hit. If empty, STOP — Task 1 is not yet landed and this task cannot proceed.

**Baseline recorded**: fill in `[FE: N/N passing]` and `[BE: M/M passing]` in the commit body of the final commit.

---

## 3. Files

### To Create (new)
- `src/app/features/text/components/typewriter-keys.component.ts` — standalone presentational component: row of mode buttons styled as typewriter keys in a carriage. Depends on Ionic + `data-test` convention (see `pages/photoshoot/` for standalone component shape).
- `src/app/features/text/components/typewriter-keys.component.spec.ts` — TestBed spec with Page Object and `data-test` selectors.

### To Modify
- `src/app/features/text/text.page.scss` — current state: generic dark surface → target state: vellum background with inlined SVG paper-grain data URI, typewriter-key styling hook on `.mode-button`, Cormorant-italic output text.
- `src/app/features/text/text.page.ts` — add `revealedText = signal('')`, `revealChar()` stepper on 18ms interval, `prefers-reduced-motion` short-circuit, cleanup on destroy / new generation.
- `src/app/features/text/text.page.spec.ts` — extend existing spec with reveal-behavior tests (reduced-motion fallback, interval tick, cleanup).
- `src/app/features/text/text.page.html` — render `<app-typewriter-keys>` where `.mode-button` row used to sit; bind output to `revealedText()` instead of the raw model.
- `src/theme/tokens.scss` — add `--accent-paper` in both `:root` and `:root[data-theme="dark"]` blocks; add a comment line enumerating the contrast pair for Task 6's contrast script.

### To Leave Alone
- `src/app/features/photoshoot/**` — Task 4 owns its own `:host` overrides; do not touch.
- `src/app/features/picks/**` — Task 3 owns Picks.
- `src/app/features/onboarding/**` — Task 2 owns Onboarding.
- `server/**` — this task is FE-only; no migrations, no DTOs, no routes.
- `src/app/services/theme.service.ts` — Task 1 owns the theme service; consume it, do not modify it.

---

## 4. Implementation Steps

### Step 1: Confirm the Text feature paths exist

**Action**: verify the feature directory and entry files exist before editing. The codebase context lists `pages/photoshoot/` and `features/onboarding/` explicitly but does not enumerate `features/text/`. If the feature lives under `pages/text/` instead, update every `src/app/features/text/` path below to `src/app/pages/text/` (log as a deviation).

**File**: N/A (audit only)

**Pattern**:
```bash
ls src/app/features/text/ 2>/dev/null || ls src/app/pages/text/
```

**Verify**: one of the two listings prints `text.page.ts`, `text.page.html`, `text.page.scss`. If neither does, STOP — flag as an architecture-doc/codebase mismatch and wait for guidance.

### Step 2: Add `--accent-paper` to the token file

**Action**: append a new custom property in both the light (`:root`) and dark (`:root[data-theme="dark"]`) blocks; add a comment enumerating the contrast pair so Task 6's `a11y-contrast-check.mjs` picks it up.

**File**: `src/theme/tokens.scss` (modify, from CODEBASE CONTEXT)

**Pattern**:
```scss
:root {
  /* ...existing light tokens... */
  --accent-paper: #5a7a6a;   /* contrast-pair: --accent-paper on --page-bg (body text) */
}

:root[data-theme="dark"] {
  /* ...existing dark tokens... */
  --accent-paper: #7a9a8a;   /* contrast-pair: --accent-paper on --page-bg (body text) */
}
```

**Verify**: `grep -n 'accent-paper' src/theme/tokens.scss` returns exactly two hits (one per block).

### Step 3: Add the char-reveal signal + interval logic to `text.page.ts`

**Action**: introduce `revealedText = signal('')`, a private `revealTimer: ReturnType<typeof setInterval> | null`, and a `startReveal(fullText: string)` method. Short-circuit to full-text-immediately when `window.matchMedia('(prefers-reduced-motion: reduce)').matches`. Wire the method to the existing generation completion handler. Ensure `ngOnDestroy` clears the timer.

**File**: `src/app/features/text/text.page.ts` (modify)

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, OnDestroy, signal } from '@angular/core';

// inside the class
revealedText = signal('');
private revealTimer: ReturnType<typeof setInterval> | null = null;

private startReveal(fullText: string): void {
  this.clearReveal();
  this.revealedText.set('');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) {
    this.revealedText.set(fullText);
    return;
  }
  let i = 0;
  this.revealTimer = setInterval(() => {
    if (i >= fullText.length) {
      this.clearReveal();
      return;
    }
    this.revealedText.update(prev => prev + fullText.charAt(i));
    i += 1;
  }, 18);
}

private clearReveal(): void {
  if (this.revealTimer !== null) {
    clearInterval(this.revealTimer);
    this.revealTimer = null;
  }
}

ngOnDestroy(): void {
  this.clearReveal();
}
```

Call `this.startReveal(fullTextFromResponse)` at the point the existing code sets the final model text, and call `this.clearReveal()` at the start of a new generation.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless --include='**/text.page.spec.ts'` — the pre-existing text page tests must still pass before new tests land.

### Step 4: Replace the output binding in `text.page.html`

**Action**: change the output region to bind `revealedText()` instead of the raw model field. Preserve every existing `data-test` attribute. Wrap output in a `<article class="manuscript">` to scope Cormorant-italic styling without bleeding into controls.

**File**: `src/app/features/text/text.page.html` (modify)

**Pattern**:
```html
<article class="manuscript" data-test="text-output">
  {{ revealedText() }}
</article>
```

**Verify**: `grep -n 'revealedText' src/app/features/text/text.page.html` returns at least one hit. The page still compiles: `npm run build -- --configuration=development` exits 0.

### Step 5: Create the `typewriter-keys` component

**Action**: standalone component that renders the mode buttons as typewriter keys inside a carriage frame. Takes `modes: Mode[]` and `selected: Mode` as inputs, emits `modeChange`. Uses `data-test` selectors for each key and the carriage.

**File**: `src/app/features/text/components/typewriter-keys.component.ts` (new)

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

export type TextMode = 'draft' | 'polish' | 'expand';

@Component({
  selector: 'app-typewriter-keys',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="carriage" data-test="typewriter-carriage">
      <button
        *ngFor="let m of modes"
        type="button"
        class="key"
        [class.key--selected]="m === selected"
        [attr.data-test]="'typewriter-key-' + m"
        (click)="modeChange.emit(m)"
      >{{ m }}</button>
    </div>
  `,
  styleUrl: './typewriter-keys.component.scss',
})
export class TypewriterKeysComponent {
  @Input({ required: true }) modes: TextMode[] = [];
  @Input({ required: true }) selected!: TextMode;
  @Output() modeChange = new EventEmitter<TextMode>();
}
```

And a minimal `typewriter-keys.component.scss` next to it (same directory) holding the carriage frame + key depression styles, all referencing tokens (`var(--surface)`, `var(--hairline)`, `var(--accent-paper)`).

**Verify**: `npm run build -- --configuration=development` exits 0.

### Step 6: Swap the mode-button row for the new component

**Action**: in `text.page.html`, replace the existing mode-button row with `<app-typewriter-keys [modes]="modes" [selected]="selectedMode" (modeChange)="onModeChange($event)"></app-typewriter-keys>`. Add `TypewriterKeysComponent` to `imports` in `text.page.ts`.

**File**: `src/app/features/text/text.page.html` + `src/app/features/text/text.page.ts`

**Pattern**:
```typescript
// text.page.ts
import { TypewriterKeysComponent } from './components/typewriter-keys.component';
// ...in @Component metadata:
imports: [/* existing */, TypewriterKeysComponent],
```

**Verify**: `grep -n 'app-typewriter-keys' src/app/features/text/text.page.html` returns a hit. `npm run build -- --configuration=development` exits 0.

### Step 7: Rewrite `text.page.scss` for the writer's desk aesthetic

**Action**: replace the current surface styling with vellum page background, inlined SVG paper-grain noise overlay, Cormorant-italic `.manuscript` output, and `:host` world-bg override. All colors via tokens only — no hex literals.

**File**: `src/app/features/text/text.page.scss` (modify)

**Pattern**:
```scss
:host {
  --world-bg: var(--page-bg);
  display: block;
  min-height: 100%;
  background:
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.35  0 0 0 0 0.30  0 0 0 0 0.22  0 0 0 0.08 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"),
    var(--world-bg);
  background-repeat: repeat;
  color: var(--text-primary);
}

.manuscript {
  font-family: var(--font-cormorant, 'Cormorant Garamond', serif);
  font-style: italic;
  font-size: 1.15rem;
  line-height: 1.65;
  white-space: pre-wrap;
  padding: 1.5rem 1.25rem;
  border-top: 1px solid var(--hairline);
}

@media (prefers-reduced-motion: reduce) {
  :host { background-image: none; }   /* drop grain for motion-sensitive users */
}
```

**Verify**: `npm run build -- --configuration=development` exits 0. Manually open the route at `/text` and confirm vellum texture renders in both light and dark (toggle OS scheme).

### Step 8: Update `text.page.spec.ts` for reveal behavior

**Action**: add three focused specs: (a) reduced-motion sets full text immediately; (b) non-reduced-motion reveals incrementally on timer tick; (c) destroy clears the timer. Use Jasmine's `jasmine.clock()` for interval control. Match the repo's Jasmine+Karma framework.

**File**: `src/app/features/text/text.page.spec.ts` (modify)

**Pattern**: see Section 5.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless --include='**/text.page.spec.ts'` — new specs pass, pre-existing specs still pass.

### Step 9: Create `typewriter-keys.component.spec.ts`

**Action**: TestBed spec with a small Page Object. Three tests: renders one key per mode; selected key gets `key--selected` class; clicking a key emits `modeChange`.

**File**: `src/app/features/text/components/typewriter-keys.component.spec.ts` (new)

**Pattern**: see Section 5.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless --include='**/typewriter-keys.component.spec.ts'` — three new specs pass.

---

## 5. Tests

Framework: Jasmine + Karma + Angular TestBed (matching existing specs in `src/app/pages/photoshoot/` and `src/app/features/onboarding/`). Naming: `condition_expectedOutcome`.

### `text.page.spec.ts` additions

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TextPage } from './text.page';

class TextPageObject {
  constructor(private fixture: ComponentFixture<TextPage>) {}
  get outputText(): string {
    const el = this.fixture.nativeElement.querySelector('[data-test="text-output"]');
    return el ? (el.textContent ?? '').trim() : '';
  }
}

describe('TextPage reveal behavior', () => {
  let fixture: ComponentFixture<TextPage>;
  let page: TextPage;
  let po: TextPageObject;
  let matchMediaSpy: jasmine.Spy;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [TextPage] }).compileComponents();
    fixture = TestBed.createComponent(TextPage);
    page = fixture.componentInstance;
    po = new TextPageObject(fixture);
  });

  afterEach(() => {
    jasmine.clock().uninstall();
  });

  it('reducedMotionPreferred_setsFullTextImmediately', () => {
    matchMediaSpy = spyOn(window, 'matchMedia').and.returnValue({ matches: true } as MediaQueryList);
    (page as any).startReveal('hello');
    fixture.detectChanges();
    expect(page.revealedText()).toBe('hello');
  });

  it('reducedMotionNotPreferred_revealsCharByCharOnTick', () => {
    spyOn(window, 'matchMedia').and.returnValue({ matches: false } as MediaQueryList);
    jasmine.clock().install();
    (page as any).startReveal('abc');
    expect(page.revealedText()).toBe('');
    jasmine.clock().tick(18);
    expect(page.revealedText()).toBe('a');
    jasmine.clock().tick(18);
    expect(page.revealedText()).toBe('ab');
    jasmine.clock().tick(18);
    expect(page.revealedText()).toBe('abc');
  });

  it('destroy_clearsIntervalAndStopsReveal', () => {
    spyOn(window, 'matchMedia').and.returnValue({ matches: false } as MediaQueryList);
    jasmine.clock().install();
    (page as any).startReveal('abc');
    jasmine.clock().tick(18);
    expect(page.revealedText()).toBe('a');
    page.ngOnDestroy();
    jasmine.clock().tick(18 * 10);
    expect(page.revealedText()).toBe('a');
  });
});
```

### `typewriter-keys.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TypewriterKeysComponent, TextMode } from './typewriter-keys.component';

class KeysPageObject {
  constructor(private fixture: ComponentFixture<TypewriterKeysComponent>) {}
  get keys(): HTMLElement[] {
    return Array.from(this.fixture.nativeElement.querySelectorAll('[data-test^="typewriter-key-"]'));
  }
  keyFor(mode: TextMode): HTMLElement | null {
    return this.fixture.nativeElement.querySelector(`[data-test="typewriter-key-${mode}"]`);
  }
}

describe('TypewriterKeysComponent', () => {
  let fixture: ComponentFixture<TypewriterKeysComponent>;
  let component: TypewriterKeysComponent;
  let po: KeysPageObject;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [TypewriterKeysComponent] }).compileComponents();
    fixture = TestBed.createComponent(TypewriterKeysComponent);
    component = fixture.componentInstance;
    component.modes = ['draft', 'polish', 'expand'];
    component.selected = 'draft';
    po = new KeysPageObject(fixture);
    fixture.detectChanges();
  });

  it('threeModes_rendersThreeKeys', () => {
    expect(po.keys.length).toBe(3);
  });

  it('selectedMode_getsSelectedClass', () => {
    const draftKey = po.keyFor('draft')!;
    const polishKey = po.keyFor('polish')!;
    expect(draftKey.classList.contains('key--selected')).toBeTrue();
    expect(polishKey.classList.contains('key--selected')).toBeFalse();
  });

  it('clickKey_emitsModeChangeWithKeyMode', () => {
    let emitted: TextMode | null = null;
    component.modeChange.subscribe((m: TextMode) => (emitted = m));
    po.keyFor('polish')!.click();
    expect(emitted).toBe('polish');
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(tokens): add --accent-paper pair (light/dark)` — `src/theme/tokens.scss`: new custom property in both theme blocks with contrast-pair comments for Task 6.
2. `feat(text): char-by-char reveal signal with reduced-motion fallback` — `text.page.ts`, `text.page.html`: `revealedText` signal, 18ms interval, `prefers-reduced-motion` short-circuit, `ngOnDestroy` cleanup, output binding swap.
3. `feat(text): typewriter-keys component` — `components/typewriter-keys.component.ts` + `.scss`: standalone OnPush component with `data-test` selectors.
4. `feat(text): wire typewriter keys into page` — `text.page.ts`, `text.page.html`: import + render the new component in place of the mode-button row.
5. `feat(text): writer's-desk scss — vellum ground, manuscript italic` — `text.page.scss`: SVG paper-grain data URI, `:host { --world-bg }`, Cormorant-italic `.manuscript`, reduced-motion grain drop.
6. `test(text): cover reveal timing, reduced-motion, destroy cleanup` — `text.page.spec.ts`, `typewriter-keys.component.spec.ts`.

**Deviation logging**: if a step deviates (e.g., feature lives under `src/app/pages/text/` not `src/app/features/text/`), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build -- --configuration=development
```

**Expected delta**: FE `[N]` → `[N+6]` passing (3 new reveal specs + 3 new typewriter-keys specs). Zero pre-existing tests broken. Backend untouched — `cd server && pytest -q` must still report the baseline pass count.

Manual smoke, both themes:
1. `npm start`; open `/text` with `prefers-color-scheme: light` — vellum grain visible, mode row looks like keys.
2. Toggle OS to dark — paper darkens to `--page-bg` dark slot, keys retain carriage frame.
3. Trigger a generation — output reveals char-by-char; refresh with reduced-motion enabled in OS settings — output appears instantly.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any one unit.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch; the branch can be deleted safely because no migrations or shared-module changes landed (token addition is additive and unused by other features).
- **Token-only rollback**: if Task 6's contrast script later flags `--accent-paper`, revert commit 1 alone — the rest of the task only reads the variable, so falling back to a default inherited color is graceful.

---

## 9. Deviations Allowed

- **Feature directory under `pages/text/` instead of `features/text/`** → use whichever path exists; update all paths in this guide consistently; log in commit 1 body.
- **Existing `text.page.ts` uses a service-owned text stream (not a single final string)** → call `startReveal()` on the stream's `complete` or collapse to the accumulated full text; log the shape chosen in the commit body.
- **Existing mode set differs from `['draft','polish','expand']`** → pass the real mode list through `@Input()`; keep the component generic over `string`-keyed modes; update the spec's `modes` input to match.
- **Cormorant font token named differently** → grep `src/theme/` for the serif font variable; use whichever token Task 1 landed; log in commit body.
- **Jasmine `jasmine.clock()` not usable because tests already run with fakeAsync** → translate to `fakeAsync`/`tick(18)`; same assertion bodies; log in commit 6 body.
- **Side-effect required** (push, publish, schema change) → STOP and mark `[REQUIRES APPROVAL]`; this task should not need any.

---

## 10. Out of Scope

This task covers only the Text world's visual + output-reveal pass. It does not touch the AI provider, the text generation endpoint, the mode semantics, the shell's `immersive` signal (Photoshoot owns that), or any shared design-system component. An executor that sees an opportunity to "also" polish neighboring surfaces or factor out shared noise/texture utilities should STOP and flag it.

- **Shared noise-overlay utility in `src/theme/`** — deferred until a second feature needs a grain texture. Per "not-yet-built is the right state."
- **Animation library / engine** — deferred; one `setInterval` is sufficient for one consumer.
- **Immersive shell during reveal** — Photoshoot owns `shellLayout.setImmersive`; Text stays inside the normal shell.
- **New Text API endpoints or DTOs** — purely a FE pass.
- **User-facing theme toggle** — Task 1 already decided: `prefers-color-scheme` only, no toggle.
- **Cursor-blink / caret animation at reveal tail** — nice-to-have; can land as a follow-up after retention signal.
- **Replacing `setInterval` with `requestAnimationFrame`** — profile first; only switch if Task 6 screenshots reveal jank.
- **Migrating the Text feature directory between `pages/` and `features/`** — out of scope even if it turns out to be inconsistent with neighbors; log as a finding, do not refactor here.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)