# 🛠️ Task 4: Photoshoot Darkroom Pass

**Purpose**: Reskin the photoshoot world as ceremony — a single glowing thing in a violet-accented void, with the shell going immersive (status bar hidden, tabs faded) for the duration of a generation.

**Effort**: 1 day

**Dependencies**: Task 1 (Dual-Mode Token Plumbing — provides `--accent-cool`, `--world-bg`, and the shell `immersive` signal/`setImmersive()` API)

**Parallel With**: Task 2 (Onboarding), Task 3 (Picks), Task 5 (Text) — all consume Task 1 tokens but touch different feature folders

**Blocks**: Task 6 (A11y + Screenshot QA — needs all four worlds shipped to capture the contact sheet)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The photoshoot tab today renders as a generic Ionic page with default accent and the standard tab shell visible throughout generation. This task gives it a distinct visual identity — violet `--accent-cool` (`#5B6CC0` light / `#818CF8` dark), a `#FAFAFA`/`#000` world background, italic Cormorant copy, and an immersive shell mode that hides the status bar and tabs while the LoRA inference runs. The "ceremony" reading comes from a single liquid silhouette centered in a void with dual-stroke progress, plus a numbered grayscale contact sheet of prior generations beneath it. All changes are scoped to `src/app/pages/photoshoot/` (and a `setImmersive` call into the shell signal added in Task 1) — no cross-feature imports, no new shared components, no AI/backend changes.

**Trade-offs considered**:
- **Animated theme transition library** — rejected because the only state change is `immersive: boolean`; CSS class toggle on the shell is enough, and a library would be infrastructure before second consumer
- **Shared `ImmersiveDirective` for any feature to use** — rejected because photoshoot is the only consumer right now; per "not-yet-built is the right state for infrastructure nobody's asked for", we keep the call site explicit
- **Calling `StatusBar.hide()` from the shell on any immersive route** — rejected because it couples the shell to a Capacitor plugin that only one feature needs; isolating the plugin call inside the photoshoot feature keeps the shell pure

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git log --oneline -10                                            # Confirm Task 1 (token plumbing) commits are present
ls src/app/pages/photoshoot/                                     # Inventory existing files
ls src/app/pages/photoshoot/components 2>/dev/null || echo "no components dir yet"
grep -n "immersive" src/app/shell/shell-layout.component.ts      # Confirm Task 1 added the signal
grep -n "accent-cool\|world-bg" src/theme/tokens.scss            # Confirm Task 1 added the tokens
git diff HEAD -- src/app/pages/photoshoot src/theme               # Confirm target tree is clean
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -20   # Record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**If `immersive` signal or `--accent-cool` token is missing**: STOP — Task 1 is not done. Do not invent the missing API; flag it and switch to Task 1.

**Baseline recorded**: write the test pass count here before starting (e.g., `42/42 passing`).

---

## 3. Files

### To Create (new)
- `src/app/pages/photoshoot/components/contact-sheet.component.ts` — standalone Angular 20 component; `@Input() generations: GenerationTile[]`; renders numbered grayscale tiles with hairline borders
- `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts` — TestBed spec with Page Object using `data-test` selectors
- `src/app/pages/photoshoot/photoshoot.types.ts` — local type `GenerationTile = { id: string; index: number; thumbUrl: string; createdAt: string }` (only if not already in an existing model file — check first)

### To Modify (cite CODEBASE CONTEXT)
- `src/app/pages/photoshoot/photoshoot.page.ts` (CODEBASE: `src/app/pages/photoshoot/`) — inject `ShellLayoutComponent` (or its `ImmersiveService` if Task 1 extracted one), call `setImmersive(true)` on generation start, `setImmersive(false)` on finish/error; wrap in `try/finally` so error paths still restore. Import `StatusBar` from `@capacitor/status-bar` (declared in codebase deps) and call `StatusBar.hide()`/`StatusBar.show()` alongside, guarded by `Capacitor.isNativePlatform()`
- `src/app/pages/photoshoot/photoshoot.page.scss` (CODEBASE: `src/app/pages/photoshoot/`) — add `:host` block setting `--accent-cool: #5B6CC0; --world-bg: #FAFAFA;` and a `:host-context([data-theme="dark"])` block setting `--accent-cool: #818CF8; --world-bg: #000;`; set body copy `font-family: var(--font-cormorant); font-style: italic;`; raise `--scanline-opacity` and `--grain-opacity` in dark
- `src/app/pages/photoshoot/photoshoot.page.html` (CODEBASE: `src/app/pages/photoshoot/`) — wrap existing content with `data-test="photoshoot-stage"`; add `<bubls-contact-sheet [generations]="recentGenerations()" data-test="contact-sheet">` below the centerpiece; ensure scanline + grain overlays read CSS vars (not hardcoded opacities)
- `src/app/pages/photoshoot/photoshoot.page.spec.ts` (CODEBASE: `src/app/pages/photoshoot/`) — add tests for immersive lifecycle and StatusBar calls (mock the Capacitor plugin)

### To Modify only if it already exists (verify in pre-flight)
- `src/app/pages/photoshoot/components/progress-portrait.component.ts` — replace any hardcoded stroke color with `var(--accent-cool)`; reduce silhouettes to a single centered liquid form. **If this file does not exist**, create it as a new minimal component (`<svg>` with one circular path, stroke from CSS var) and add a corresponding `.spec.ts`. Log either path as a deviation in the commit body
- `src/app/pages/photoshoot/photoshoot.page.scss` scanline/grain rules — only edit if scanline/grain overlay classes already exist; if not, defer the "boosted intensity in dark" sub-step and flag in commit body (Task 5 may introduce noise overlay primitives we can share)

### To Leave Alone
- `src/app/pages/home/`, `src/app/pages/dashboard/`, `src/app/pages/pick-detail/` — Task 3's territory
- `src/app/features/onboarding/` — Task 2's territory
- `src/theme/tokens.scss` — Task 1 owns the global token layer; this task only consumes via `:host`
- `src/app/shell/shell-layout.component.ts` — Task 1 owns the `immersive` signal; this task only calls `setImmersive()`
- `server/modules/photoshoot/` — no backend changes in this task
- `src/app/services/photoshoot-api.service.ts` — API surface unchanged
- `capacitor.config.ts` — `@capacitor/status-bar` is already in deps (codebase context)

---

## 4. Implementation Steps

### Step 1: Scope the violet accent and dark void via `:host`

**Action**: Open the photoshoot page SCSS and add a `:host` block that overrides the world tokens for this route only. Add a `:host-context([data-theme="dark"])` block for the dark variant. Set body copy to italic Cormorant.

**File**: `src/app/pages/photoshoot/photoshoot.page.scss`

**Pattern**:
```scss
:host {
  --accent-cool: #5B6CC0;
  --world-bg: #FAFAFA;
  --on-accent-cool: #FFFFFF;
  --scanline-opacity: 0.08;
  --grain-opacity: 0.06;

  display: block;
  background: var(--world-bg);
  color: var(--text-primary);
  font-family: var(--font-cormorant);
  font-style: italic;
}

:host-context([data-theme="dark"]) {
  --accent-cool: #818CF8;
  --world-bg: #000000;
  --scanline-opacity: 0.18;
  --grain-opacity: 0.12;
}
```

**Verify**:
```bash
grep -nE "accent-cool|world-bg|font-cormorant" src/app/pages/photoshoot/photoshoot.page.scss
npm run build 2>&1 | tail -5
```
Expect: both blocks present; `npm run build` exits 0.

### Step 2: Add the `immersive` lifecycle calls on generation start/end

**Action**: In `photoshoot.page.ts`, inject the shell (or the immersive service Task 1 exposes), and wrap the generation kickoff so that immersive mode is set true on start and false in `finally` (covering both success and error paths). Use signals consistently with the OnPush component.

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Pattern**:
```typescript
private shell = inject(ShellLayoutComponent);   // or: inject(ImmersiveService) — match Task 1's API
private photoshootApi = inject(PhotoshootApiService);

readonly recentGenerations = signal<GenerationTile[]>([]);

async generate(): Promise<void> {
  this.shell.setImmersive(true);
  try {
    const result = await this.photoshootApi.generate(this.prompt());
    this.recentGenerations.update(prev => [toTile(result), ...prev]);
  } finally {
    this.shell.setImmersive(false);
  }
}
```

**Verify**:
```bash
grep -n "setImmersive" src/app/pages/photoshoot/photoshoot.page.ts
npm run build 2>&1 | tail -5
```
Expect: two call sites (true on start, false in finally); build passes.

### Step 3: Hide the native status bar via Capacitor (guarded)

**Action**: Same file as Step 2. Import `StatusBar` from `@capacitor/status-bar` and `Capacitor` from `@capacitor/core`. Wrap the calls so they are no-ops in the browser (`Capacitor.isNativePlatform()` is false on web).

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Pattern**:
```typescript
import { StatusBar } from '@capacitor/status-bar';
import { Capacitor } from '@capacitor/core';

private async setImmersive(on: boolean): Promise<void> {
  this.shell.setImmersive(on);
  if (Capacitor.isNativePlatform()) {
    on ? await StatusBar.hide() : await StatusBar.show();
  }
}

async generate(): Promise<void> {
  await this.setImmersive(true);
  try { /* ...as Step 2... */ }
  finally { await this.setImmersive(false); }
}
```

**Verify**:
```bash
grep -n "@capacitor/status-bar\|isNativePlatform" src/app/pages/photoshoot/photoshoot.page.ts
npm run build 2>&1 | tail -5
```
Expect: import present; `isNativePlatform` guard present; build passes.

### Step 4: Tune progress portrait to violet dual stroke + single silhouette

**Action**: If `progress-portrait.component.ts` already exists in `src/app/pages/photoshoot/components/`, edit it: replace any hardcoded stroke color with `stroke: var(--accent-cool)`, and remove any extra portrait variants so only one centered silhouette remains. If it does not exist, create a minimal new component as described in Files §"To Modify only if it already exists".

**File**: `src/app/pages/photoshoot/components/progress-portrait.component.ts` (verify or create)

**Pattern**:
```typescript
@Component({
  selector: 'bubls-progress-portrait',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="0 0 200 200" data-test="progress-portrait">
      <circle cx="100" cy="100" r="80"
              fill="none"
              stroke="var(--accent-cool)"
              stroke-width="1.5"
              stroke-dasharray="4 4" />
      <path d="M100 60 ... Z"
            fill="var(--accent-cool)"
            opacity="0.65"
            data-test="silhouette" />
    </svg>
  `,
  styles: [`
    :host { display: block; width: 100%; max-width: 320px; margin: 0 auto; }
  `],
})
export class ProgressPortraitComponent {}
```

**Verify**:
```bash
grep -n "var(--accent-cool)" src/app/pages/photoshoot/components/progress-portrait.component.ts
grep -c "data-test=\"silhouette\"" src/app/pages/photoshoot/components/progress-portrait.component.ts
npm run build 2>&1 | tail -5
```
Expect: stroke uses CSS var; exactly one `silhouette` data-test (single centerpiece); build passes.

### Step 5: Build the contact-sheet component (new)

**Action**: Create a standalone Angular 20 component that takes a `generations` input and renders numbered grayscale tiles (latest first) with hairline borders. No shared library — feature-local.

**File**: `src/app/pages/photoshoot/components/contact-sheet.component.ts` (new)

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { NgFor } from '@angular/common';
import type { GenerationTile } from '../photoshoot.types';

@Component({
  selector: 'bubls-contact-sheet',
  standalone: true,
  imports: [NgFor],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ol class="sheet" data-test="contact-sheet-list">
      <li *ngFor="let g of generations; let i = index"
          class="tile"
          [attr.data-test]="'tile-' + i">
        <span class="num">{{ i + 1 | number:'2.0-0' }}</span>
        <img [src]="g.thumbUrl" [alt]="'Generation ' + (i + 1)" />
      </li>
    </ol>
  `,
  styles: [`
    :host { display: block; padding: 1rem 0; }
    .sheet { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
             gap: 0.5rem; list-style: none; margin: 0; padding: 0; }
    .tile { position: relative; aspect-ratio: 1; border: 1px solid var(--hairline);
            filter: grayscale(100%); }
    .tile img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .num { position: absolute; top: 4px; left: 4px;
           font-family: var(--font-cormorant); font-size: 0.75rem;
           color: var(--text-primary); background: var(--world-bg);
           padding: 0 4px; }
  `],
})
export class ContactSheetComponent {
  @Input({ required: true }) generations: GenerationTile[] = [];
}
```

**Verify**:
```bash
grep -n "data-test" src/app/pages/photoshoot/components/contact-sheet.component.ts
npm run build 2>&1 | tail -5
```
Expect: `data-test` selectors on list and tiles; build passes.

### Step 6: Wire the contact sheet and immersive class into the page template

**Action**: In `photoshoot.page.html`, add a `data-test="photoshoot-stage"` wrapper, render `<bubls-contact-sheet>` below the centerpiece, and ensure the scanline/grain overlay elements use the CSS vars set in Step 1 (so dark-mode boost takes effect).

**File**: `src/app/pages/photoshoot/photoshoot.page.html`

**Pattern**:
```html
<ion-content class="stage" data-test="photoshoot-stage">
  <div class="overlay scanline" [style.opacity]="'var(--scanline-opacity)'"></div>
  <div class="overlay grain"    [style.opacity]="'var(--grain-opacity)'"></div>

  <bubls-progress-portrait data-test="centerpiece" />

  <bubls-contact-sheet
    [generations]="recentGenerations()"
    data-test="contact-sheet" />
</ion-content>
```

Also import the new components in `photoshoot.page.ts`:
```typescript
imports: [/* existing */, ProgressPortraitComponent, ContactSheetComponent],
```

**Verify**:
```bash
grep -n "bubls-contact-sheet\|photoshoot-stage" src/app/pages/photoshoot/photoshoot.page.html
grep -n "ContactSheetComponent" src/app/pages/photoshoot/photoshoot.page.ts
npm run build 2>&1 | tail -5
```
Expect: tag rendered, data-test wrapper present, component imported, build passes.

### Step 7: Manual smoke (web only — native validation deferred to Task 6)

**Action**: Run the dev server, hit the photoshoot route in both light and dark, trigger a mock generation, watch for: (a) violet accent visible, (b) shell tabs fade out during generation, (c) status bar code path no-ops in browser without console error, (d) contact sheet appears after generation completes.

**File**: N/A (browser)

**Pattern**:
```bash
npm start
# open http://localhost:4201/#/photoshoot
# DevTools: emulate prefers-color-scheme dark; reload; trigger generate
```

**Verify**: Visual + console — no errors; immersive mode toggles. If shell `setImmersive` API differs from what Task 1 exposed, stop and reconcile (do not edit Task 1's surface).

---

## 5. Tests

Karma + Jasmine (per codebase context: "Testing: pytest (BE), Karma + Jasmine (FE)"). Use TestBed with real child components rendered, Page Object with `data-test` selectors. Test naming: `condition_expectedOutcome`, no "should".

### `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContactSheetComponent } from './contact-sheet.component';
import type { GenerationTile } from '../photoshoot.types';

class ContactSheetPageObject {
  constructor(private fixture: ComponentFixture<ContactSheetComponent>) {}
  get list() { return this.q("[data-test='contact-sheet-list']"); }
  tile(i: number) { return this.q(`[data-test='tile-${i}']`); }
  private q<T extends HTMLElement>(sel: string): T | null {
    return this.fixture.nativeElement.querySelector(sel);
  }
}

const tile = (i: number): GenerationTile => ({
  id: `g-${i}`, index: i, thumbUrl: `https://example.test/${i}.png`,
  createdAt: '2026-04-16T00:00:00Z',
});

describe('ContactSheetComponent', () => {
  let fixture: ComponentFixture<ContactSheetComponent>;
  let po: ContactSheetPageObject;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ContactSheetComponent] }).compileComponents();
    fixture = TestBed.createComponent(ContactSheetComponent);
    po = new ContactSheetPageObject(fixture);
  });

  it('emptyInput_rendersEmptyList', () => {
    fixture.componentRef.setInput('generations', []);
    fixture.detectChanges();
    expect(po.list).withContext('list element should still exist').not.toBeNull();
    expect(po.list!.children.length).toBe(0);
  });

  it('threeTiles_rendersThreeNumberedTiles', () => {
    fixture.componentRef.setInput('generations', [tile(0), tile(1), tile(2)]);
    fixture.detectChanges();
    expect(po.list!.children.length).toBe(3);
    expect(po.tile(0)).not.toBeNull();
    expect(po.tile(2)!.querySelector('.num')!.textContent!.trim()).toBe('03');
  });

  it('tile_hasGrayscaleFilter', () => {
    fixture.componentRef.setInput('generations', [tile(0)]);
    fixture.detectChanges();
    const styles = window.getComputedStyle(po.tile(0)!);
    expect(styles.filter).toContain('grayscale');
  });
});
```

### `src/app/pages/photoshoot/photoshoot.page.spec.ts` (modify — add cases)

```typescript
import { Capacitor } from '@capacitor/core';
import { StatusBar } from '@capacitor/status-bar';
import { ShellLayoutComponent } from '../../shell/shell-layout.component';
import { PhotoshootApiService } from '../../services/photoshoot-api.service';
import { PhotoshootPage } from './photoshoot.page';

describe('PhotoshootPage immersive lifecycle', () => {
  let setImmersive: jasmine.Spy;
  let apiSpy: jasmine.SpyObj<PhotoshootApiService>;
  let statusHide: jasmine.Spy;
  let statusShow: jasmine.Spy;

  beforeEach(async () => {
    setImmersive = jasmine.createSpy('setImmersive');
    apiSpy = jasmine.createSpyObj<PhotoshootApiService>('PhotoshootApiService', ['generate']);
    statusHide = spyOn(StatusBar, 'hide').and.resolveTo();
    statusShow = spyOn(StatusBar, 'show').and.resolveTo();
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);

    await TestBed.configureTestingModule({
      imports: [PhotoshootPage],
      providers: [
        { provide: ShellLayoutComponent, useValue: { setImmersive } },
        { provide: PhotoshootApiService, useValue: apiSpy },
      ],
    }).compileComponents();
  });

  it('generateSuccess_callsSetImmersiveTrueThenFalse', async () => {
    apiSpy.generate.and.resolveTo({ id: 'g-1', thumbUrl: 'x', createdAt: '2026-04-16T00:00:00Z' } as any);
    const fixture = TestBed.createComponent(PhotoshootPage);
    await fixture.componentInstance.generate();
    expect(setImmersive.calls.allArgs()).toEqual([[true], [false]]);
  });

  it('generateError_stillRestoresImmersiveFalse', async () => {
    apiSpy.generate.and.rejectWith(new Error('boom'));
    const fixture = TestBed.createComponent(PhotoshootPage);
    await expectAsync(fixture.componentInstance.generate()).toBeRejected();
    expect(setImmersive).toHaveBeenCalledWith(true);
    expect(setImmersive).toHaveBeenCalledWith(false);
  });

  it('nativePlatform_generate_hidesAndShowsStatusBar', async () => {
    apiSpy.generate.and.resolveTo({ id: 'g-1', thumbUrl: 'x', createdAt: '2026-04-16T00:00:00Z' } as any);
    const fixture = TestBed.createComponent(PhotoshootPage);
    await fixture.componentInstance.generate();
    expect(statusHide).toHaveBeenCalledTimes(1);
    expect(statusShow).toHaveBeenCalledTimes(1);
  });

  it('webPlatform_generate_doesNotCallStatusBar', async () => {
    (Capacitor.isNativePlatform as jasmine.Spy).and.returnValue(false);
    apiSpy.generate.and.resolveTo({ id: 'g-1', thumbUrl: 'x', createdAt: '2026-04-16T00:00:00Z' } as any);
    const fixture = TestBed.createComponent(PhotoshootPage);
    await fixture.componentInstance.generate();
    expect(statusHide).not.toHaveBeenCalled();
    expect(statusShow).not.toHaveBeenCalled();
  });
});
```

If `progress-portrait.component.ts` is created in Step 4, add a 1-test spec:

```typescript
describe('ProgressPortraitComponent', () => {
  it('renders_singleSilhouette', async () => {
    await TestBed.configureTestingModule({ imports: [ProgressPortraitComponent] }).compileComponents();
    const fixture = TestBed.createComponent(ProgressPortraitComponent);
    fixture.detectChanges();
    const silhouettes = fixture.nativeElement.querySelectorAll("[data-test='silhouette']");
    expect(silhouettes.length).toBe(1);
  });
});
```

---

## 6. Commit Plan

One commit per logical unit. If a step deviates from this guide (e.g., `progress-portrait.component.ts` had to be created instead of edited), prefix the commit body with `Deviations:` and one line per deviation. Target: ≤3 deviation lines per commit (per the judgment-calls-per-commit metric).

1. `feat(photoshoot): scope violet accent + dark void via :host` — `photoshoot.page.scss`: Steps 1
2. `feat(photoshoot): immersive shell + status bar lifecycle on generate` — `photoshoot.page.ts`: Steps 2 + 3
3. `feat(photoshoot): violet dual-stroke single-silhouette progress portrait` — `components/progress-portrait.component.ts` (+ spec): Step 4
4. `feat(photoshoot): contact sheet of recent generations` — `components/contact-sheet.component.ts` + `.spec.ts` + `photoshoot.types.ts`: Step 5
5. `feat(photoshoot): wire stage wrapper, contact sheet, dark grain boost into template` — `photoshoot.page.html` + `photoshoot.page.ts` imports: Step 6
6. `test(photoshoot): immersive lifecycle + native vs web status bar branches` — `photoshoot.page.spec.ts`: §5

---

## 7. Verification

```bash
npm run build                                                           # Production build, must succeed
npm test -- --watch=false --browsers=ChromeHeadless                     # Full FE suite
```

**Expected delta**: baseline `N` → `N + 7` passing (3 contact-sheet + 4 immersive lifecycle; +1 if progress-portrait spec was created → `N + 8`). Zero pre-existing tests broken.

Manual visual check (web only):
```bash
npm start                                                               # then open /#/photoshoot in light + dark
```

Expected: violet accent visible in both modes; tabs fade out during generation; contact sheet renders after generation.

Native verification (status bar) is **deferred to Task 6** — flagging is intentional, not a gap.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any one of the 6 commits.
- **Per-file emergency**: if Step 6 breaks the photoshoot route, `git checkout HEAD -- src/app/pages/photoshoot/photoshoot.page.html src/app/pages/photoshoot/photoshoot.page.ts` to restore the prior template/component while keeping the new feature components.
- **Per-branch**: if the full task verification fails catastrophically, `git reset --hard <pre-task-sha>` (capture this sha in pre-flight as `git rev-parse HEAD`) or delete the feature branch.

---

## 9. Deviations Allowed

- **Architecture says `src/app/features/photoshoot/`, codebase has `src/app/pages/photoshoot/`** → use the actual `pages/` path that exists today; do NOT rename folders as part of this task. Note in the first commit body.
- **Task 1 exposed `ImmersiveService` instead of injecting `ShellLayoutComponent`** → use whatever Task 1 actually shipped. Adjust the inject site in Step 2; the contract is `setImmersive(boolean)`. Log as a one-line deviation.
- **`progress-portrait.component.ts` does not exist yet** → create it as the minimal component shown in Step 4 (single silhouette, violet stroke, OnPush). Add the spec from §5. Log "created vs modified" in the Step 4 commit body.
- **Scanline/grain overlay classes do not exist in the current template** → defer the dark-mode opacity boost; remove the `--scanline-opacity` / `--grain-opacity` lines from Step 1 SCSS. Log the deferral.
- **Existing `photoshoot.page.spec.ts` does not exist** → create it with just the §5 immersive lifecycle suite.
- **Test framework mismatch** (e.g., repo uses Jest now) → match the repo's actual framework; translate the syntax silently and note in the test commit body.
- **`PhotoshootApiService.generate` signature differs from `(prompt) => Promise<Generation>`** → pass through whatever the actual signature requires; the only invariant the tests assert is that `setImmersive` is called true/false around it.
- **Side-effect commands required** (DB migration, push, publish) → STOP, mark `[REQUIRES APPROVAL]` and ask. None should be needed in this task.

---

## 10. Out of Scope

This task gives the photoshoot world its violet/void identity and immersive ceremony. It does NOT touch the AI provider, the Replicate adapter, the LoRA model schema, the photoshoot backend module, or any other feature folder. It does NOT introduce a shared `ImmersiveDirective` or animation library — those are infrastructure-before-second-consumer that we explicitly defer per the engineering discipline rules. Native iOS verification of `StatusBar.hide()` happens in Task 6's screenshot matrix, not here.

- **Generalized `ImmersiveDirective` or `ImmersiveService` for any feature** — deferred until a second feature (text? picks?) actually requests immersive mode. Two consumers calibrate the abstraction.
- **Theme transition animations** (fade between light/dark) — out of epic scope; `prefers-color-scheme` change happens instantly, by design
- **User-toggleable theme** — explicitly declined in architecture ("no user toggle; can come later with zero re-architecture")
- **Shared noise/grain SVG primitive** — Task 5 may also need a noise overlay; if so, the second-consumer trigger fires there and a `shared/` mixin gets extracted then, not now
- **Contact sheet click-to-restore behavior** — tiles render but are non-interactive in this task. Re-prompting from history is a separate epic.
- **Capacitor StatusBar style customization** (light vs dark icon set) — `hide()`/`show()` only; styling defaults are fine for v1
- **Cross-feature route-change `setImmersive(false)` cleanup** — current scope is "generate sets true, generate finally sets false". If the user navigates away mid-generation, the in-flight request resolves and the `finally` still fires. Anything more (route-leave guard) is YAGNI.
- **Performance profiling of the contact sheet at >50 tiles** — the feature is launching with a single recent-generations array; pagination/virtualization is not needed until a real user has >50 generations
- **Backend changes to return a `recentGenerations` list endpoint** — initial version reads from the in-memory `signal()` populated as the user generates in this session. Persistence across sessions is a separate task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale, decision table
- [Epic](./epic.md) — scope and business context
- [Timeline](./timeline.md) — status tracking (update Task 4 to ✅ after verification passes)