# 🛠️ Task 3: Picks Sunday Magazine Pass

**Purpose**: Turn the Picks surface into an editorial magazine — masthead, alternating card rhythm, per-pick accent from poster art, frosted save pill, italic colophon.

**Effort**: 2 days

**Dependencies**: Task 1 (Dual-Mode Token Plumbing — supplies `--page-bg-cream`, `--world-bg`, `--accent-warm`, `--hairline`, `ThemeService`, `prefers-color-scheme` wiring)

**Parallel With**: Task 4 (Photoshoot), Task 5 (Text), Task 2 (Onboarding) — all four worlds consume Task 1 tokens independently

**Blocks**: Task 6 (A11y + Screenshot QA)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The Picks feed currently renders as a generic card stack. Task 3 rebuilds it as a Sunday magazine: a masthead that anchors the issue in space and time, an alternating rhythm of full-bleed posters and serif pull-quotes, a per-pick accent colour extracted from the poster thumbnail, and an editorial detail page with a frosted save pill and italic colophon. All work is scoped to the picks feature — no shared components, no new backend endpoints, no dependency on any world beyond Task 1's tokens. Accent extraction is a feature-local Canvas service with a single consumer by design.

**Trade-offs considered**:
- **Shared color-extraction service in `src/app/shared/`** — rejected because Picks is the only consumer; pre-abstracting before a second caller exists locks in a shape with no calibration. If photoshoot later needs extraction it can import from the feature or the code can be lifted then.
- **Library-based palette extraction (Vibrant.js, node-vibrant)** — rejected because the Canvas API solves the single dominant-color need in ~40 lines, ships zero new dependency weight, and keeps bundle size flat.
- **Variant input on FeedCard (`variant: 'full-bleed' | 'pull-quote'`)** — rejected in favour of `index`-driven alternation because the magazine rhythm is positional ("every second card breathes"), and exposing index keeps the caller declarative. The component decides the shape from position, the caller doesn't choreograph.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                        # Flag any unrelated M/?? entries; confirm Task 1 commits are on branch
git diff HEAD -- src/app/                         # Target files clean
git log --oneline -20                             # Confirm Task 1 shipped (theme.service.ts, tokens.scss rewrite)
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -20   # Record baseline pass count
```

Locate the picks components — architecture names `src/app/features/picks/` but codebase.md documents `src/app/pages/home/` and `src/app/pages/pick-detail/`. Record the real paths:

```bash
find src/app -type f \( -name 'mini-header.component.ts' -o -name 'feed-card.component.ts' -o -name 'pick-detail.page.ts' \) 2>/dev/null
find src/app -type d \( -name 'picks' -o -name 'home' -o -name 'pick-detail' \) 2>/dev/null
```

**Use the real paths returned above as the authoritative base** for every step below; paths written as `src/app/features/picks/...` are the architecture-intended locations. If the real base is `src/app/pages/home/` with a sibling `pick-detail/`, rewrite all step paths accordingly and log a single `Deviations: paths under pages/ not features/picks/` line on the first commit.

**If `mini-header.component.ts` or `feed-card.component.ts` does not exist anywhere** under `src/app/`: STOP and flag. The architecture says "rebuilt" / alternation is applied to these — they must pre-exist. Do not scaffold them blind.

**Baseline recorded**: _____ / _____ passing.

---

## 3. Files

### To Create (new)
- `src/app/features/picks/services/accent-extractor.service.ts` — Canvas-API dominant-color extractor with HSL desaturation; mock toggle via environment flag for tests
- `src/app/features/picks/services/accent-extractor.service.spec.ts` — unit specs
- `src/app/features/picks/components/mini-header.component.spec.ts` — masthead render specs
- `src/app/features/picks/components/feed-card.component.spec.ts` — alternation specs
- `src/app/features/picks/pick-detail.page.spec.ts` — save pill + colophon specs (add only if missing; extend if present)

### To Modify
- `src/app/features/picks/components/mini-header.component.ts` — rebuild template and styles as masthead (issue number · date · location), hairline rule, dark-caps-on-cream / off-white-on-warm-black
- `src/app/features/picks/components/feed-card.component.ts` — add `index` signal input; template branches on `index % 2` (odd → full-bleed, even → pull-quote with `<blockquote>`); consume `--accent` custom property
- `src/app/features/picks/pick-detail.page.ts` — inject `AccentExtractorService`, apply extracted accent to `:host` as `--accent`, add save pill (top-right, frosted) and italic Cormorant footer colophon
- `src/app/features/picks/pick-detail.page.html` (or inline template) — add save pill and colophon markup with `data-test` attributes
- `src/app/features/picks/pick-detail.page.scss` — frosted-glass styling for pill (dual mode), colophon typography
- `src/app/features/picks/picks.page.scss` — set `:host { --world-bg: var(--page-bg-cream); }` so Picks wears its own cream paper, dark override inside `[data-theme="dark"] &`
- Parent feed page template (the one rendering the `*ngFor` over picks) — pass `[index]="i"` to `<feed-card>`; locate via pre-flight find

### To Leave Alone
- `src/theme/tokens.scss` — Task 1 owns this. Do not add tokens here; use scoped `:host` for per-feature slots.
- `src/app/services/theme.service.ts` — Task 1 owns theme detection; Picks consumes `themeService.mode()` read-only.
- `src/app/shell/shell-layout.component.ts` — Task 4 (photoshoot) owns the `immersive` signal; Picks does not toggle it.
- `src/app/services/picks.service.ts` — current mock store; not touched by this task (no data shape changes needed — `pick.posterUrl` already exists).
- Any file under `src/app/features/photoshoot/`, `features/text/`, `features/onboarding/` — no cross-feature edits.

---

## 4. Implementation Steps

### Step 1: Rebuild `mini-header` as masthead

**Action**: Replace template + styles. Expose `issueNumber`, `issueDate`, `location` as signal inputs; render in a single row with middle-dot separators; hairline rule underneath; Cormorant-serif caps; dark-on-cream in light, off-white on `--page-bg` in dark.

**File**: `src/app/features/picks/components/mini-header.component.ts`

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { DatePipe, UpperCasePipe } from '@angular/common';

@Component({
  selector: 'app-mini-header',
  standalone: true,
  imports: [DatePipe, UpperCasePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header data-test="masthead" class="masthead">
      <span class="brand">BUBLS</span>
      <span class="sep">·</span>
      <span data-test="masthead-issue">No. {{ issueNumber() }}</span>
      <span class="sep">·</span>
      <span data-test="masthead-date">{{ issueDate() | date: 'EEE MMM d' }}</span>
      <span class="sep">·</span>
      <span data-test="masthead-location">{{ location() | uppercase }}</span>
    </header>
    <hr data-test="masthead-rule" class="masthead-rule" />
  `,
  styles: [`
    :host { display: block; }
    .masthead {
      font-family: var(--font-cormorant, Georgia, serif);
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-primary);
      display: flex; gap: 0.6rem; align-items: baseline;
      padding: 1rem 1.25rem 0.35rem;
    }
    .sep { opacity: 0.55; }
    .masthead-rule {
      border: 0; height: 1px; background: var(--hairline);
      margin: 0 1.25rem 0.75rem;
    }
  `],
})
export class MiniHeaderComponent {
  issueNumber = input.required<number>();
  issueDate = input.required<Date | string>();
  location = input.required<string>();
}
```

**Verify**: `npx ng build --configuration=development` — compiles without TS errors. Visual check in browser: masthead shows `BUBLS · No. 17 · THU APR 16 · ZÜRICH` with a hairline below.

### Step 2: Alternate `feed-card` rhythm by index

**Action**: Add `index` signal input; branch the template on `index % 2 !== 0` (odd indices = full-bleed image, even = serif pull-quote blockquote). Expose `--accent` as a CSS custom property the parent can set on the host.

**File**: `src/app/features/picks/components/feed-card.component.ts`

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, input, computed } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import type { Pick } from '../picks.model';   // adapt to actual model path

@Component({
  selector: 'app-feed-card',
  standalone: true,
  imports: [NgOptimizedImage],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (isFullBleed()) {
      <article data-test="card-full-bleed" class="card card--bleed" [style.--accent]="pick().accent ?? null">
        <img [ngSrc]="pick().posterUrl" [width]="1200" [height]="1600" priority alt="" />
        <footer class="hint" data-test="card-hint">{{ pick().title }}</footer>
      </article>
    } @else {
      <article data-test="card-pull-quote" class="card card--quote" [style.--accent]="pick().accent ?? null">
        <blockquote data-test="card-quote" class="pull">
          "{{ pick().pullQuote || pick().title }}"
        </blockquote>
        <cite class="byline">— {{ pick().venue }}, {{ pick().city }}</cite>
      </article>
    }
  `,
  styles: [`
    :host { display: block; margin-bottom: 1.5rem; }
    .card { border-radius: 6px; overflow: hidden; }
    .card--bleed img { width: 100%; height: auto; display: block; }
    .card--bleed .hint {
      padding: 0.6rem 0.9rem;
      border-left: 3px solid var(--accent, var(--accent-warm));
      background: var(--surface);
      color: var(--text-primary);
    }
    .card--quote {
      padding: 2rem 1.25rem;
      background: var(--surface);
      border-top: 1px solid var(--hairline);
      border-bottom: 1px solid var(--hairline);
    }
    .pull {
      font-family: var(--font-cormorant, Georgia, serif);
      font-style: italic;
      font-size: 1.6rem; line-height: 1.35;
      color: var(--text-primary);
      border-left: 3px solid var(--accent, var(--accent-warm));
      padding-left: 1rem;
      margin: 0 0 0.75rem;
    }
    .byline { font-size: 0.85rem; opacity: 0.7; }
  `],
})
export class FeedCardComponent {
  pick = input.required<Pick>();
  index = input.required<number>();
  isFullBleed = computed(() => this.index() % 2 !== 0);
}
```

**Verify**: Open the feed route. Indices 1, 3, 5 render image-first; 2, 4 render blockquote. Scroll: rhythm alternates.

### Step 3: Parent feed template passes `index`

**Action**: Locate the template that iterates picks (likely `src/app/features/picks/picks.page.html` or inline in `picks.page.ts`). Change the `@for` / `*ngFor` to pass the loop index.

**File**: the picks feed page template (path from pre-flight find)

**Pattern**:
```html
@for (pick of picks(); track pick.id; let i = $index) {
  <app-feed-card [pick]="pick" [index]="i"></app-feed-card>
}
```
(or, if still using `*ngFor`: `*ngFor="let pick of picks(); let i = index"` with `[index]="i"`)

**Verify**: DevTools shows each `<app-feed-card>` instance has a distinct `index` input; first card (index 0) renders as full-bleed, next (index 1) as full-bleed, index 2 as pull-quote, per `index % 2 !== 0`. **Note**: the epic reads "indices 1, 3, 5 are full-bleed; 2, 4 are pull-quote" (1-indexed). If you prefer the 1-indexed phrasing, either pass `[index]="i + 1"` or invert the `computed` to `index() % 2 === 1`. Pick one, be consistent, and log the choice.

### Step 4: Create `AccentExtractorService`

**Action**: Canvas-API service that loads the poster image, samples pixels, returns the dominant hex. Exposes a `desaturate(hex, amount)` helper. In dark mode, applies `desaturate(..., 0.15)` automatically when called via `extractForMode`. Fails closed to `var(--accent-warm)` on CORS / load errors. **Port the shape from `humanize-me/backend/services/claude.py:11-15`'s provider-swap discipline** (dependency-injectable, test-swappable) — not the code itself; Canvas API is a different domain.

**File**: `src/app/features/picks/services/accent-extractor.service.ts` (new)

**Pattern**:
```typescript
import { Injectable, inject } from '@angular/core';
import { ThemeService } from '../../../services/theme.service';

@Injectable({ providedIn: 'root' })
export class AccentExtractorService {
  private theme = inject(ThemeService);

  async extractForMode(imageUrl: string): Promise<string> {
    const base = await this.extractDominant(imageUrl);
    if (base === this.fallback) return base;
    return this.theme.mode() === 'dark' ? this.desaturate(base, 0.15) : base;
  }

  async extractDominant(imageUrl: string): Promise<string> {
    try {
      const img = await this.loadImage(imageUrl);
      const canvas = document.createElement('canvas');
      const size = 32;                                     // downsample — perf > precision
      canvas.width = size; canvas.height = size;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) return this.fallback;
      ctx.drawImage(img, 0, 0, size, size);
      const { data } = ctx.getImageData(0, 0, size, size);
      return this.pickDominant(data);
    } catch {
      return this.fallback;                                // CORS, 404, decode error
    }
  }

  desaturate(hex: string, amount: number): string {
    const { h, s, l } = hexToHsl(hex);
    const s2 = Math.max(0, s - amount);
    return hslToHex(h, s2, l);
  }

  private fallback = 'var(--accent-warm)';

  private loadImage(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('image load failed'));
      img.src = url;
    });
  }

  private pickDominant(data: Uint8ClampedArray): string {
    const buckets = new Map<string, { r: number; g: number; b: number; n: number }>();
    for (let i = 0; i < data.length; i += 4) {
      const a = data[i + 3];
      if (a < 200) continue;                               // skip transparent
      const r = data[i] & 0xF0, g = data[i + 1] & 0xF0, b = data[i + 2] & 0xF0;
      const key = `${r},${g},${b}`;
      const prev = buckets.get(key) ?? { r: 0, g: 0, b: 0, n: 0 };
      prev.r += data[i]; prev.g += data[i + 1]; prev.b += data[i + 2]; prev.n++;
      buckets.set(key, prev);
    }
    let best: { r: number; g: number; b: number; n: number } | null = null;
    for (const v of buckets.values()) if (!best || v.n > best.n) best = v;
    if (!best) return this.fallback;
    const r = Math.round(best.r / best.n), g = Math.round(best.g / best.n), b = Math.round(best.b / best.n);
    return `#${[r, g, b].map(n => n.toString(16).padStart(2, '0')).join('')}`;
  }
}

function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return { h: 0, s: 0, l: 0.5 };
  const r = parseInt(m[1], 16) / 255, g = parseInt(m[2], 16) / 255, b = parseInt(m[3], 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l };
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0));
  else if (max === g) h = ((b - r) / d + 2);
  else h = ((r - g) / d + 4);
  return { h: h * 60, s, l };
}

function hslToHex(h: number, s: number, l: number): string {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const hp = h / 60, x = c * (1 - Math.abs((hp % 2) - 1));
  let r1 = 0, g1 = 0, b1 = 0;
  if (hp < 1) [r1, g1, b1] = [c, x, 0];
  else if (hp < 2) [r1, g1, b1] = [x, c, 0];
  else if (hp < 3) [r1, g1, b1] = [0, c, x];
  else if (hp < 4) [r1, g1, b1] = [0, x, c];
  else if (hp < 5) [r1, g1, b1] = [x, 0, c];
  else [r1, g1, b1] = [c, 0, x];
  const m = l - c / 2;
  const to = (v: number) => Math.round((v + m) * 255).toString(16).padStart(2, '0');
  return `#${to(r1)}${to(g1)}${to(b1)}`;
}
```

**Verify**: `npx ng build` compiles. Log output from a live call against an actual poster URL in the browser console returns a plausible hex (e.g., `#c88a4a` for a warm poster).

### Step 5: Consume accent in the feed

**Action**: In the feed page component, after picks load, call `accentExtractor.extractForMode(pick.posterUrl)` per pick and store the result on the pick (or a sibling map). Pass into `feed-card` via the `pick()` input if the model already has an `accent?: string` field, or wrap the pick with an `accent` property in the component.

**File**: picks feed page `.ts` (path from pre-flight find)

**Pattern**:
```typescript
private accentExtractor = inject(AccentExtractorService);

async ngOnInit() {
  const raw = await this.picksService.load();
  const withAccent = await Promise.all(
    raw.map(async p => ({ ...p, accent: await this.accentExtractor.extractForMode(p.posterUrl) }))
  );
  this.picks.set(withAccent);
}
```

If `Pick` doesn't have `accent?: string` on the model, add it to `picks.model.ts` (optional field — no API contract change since it's client-computed).

**Verify**: DevTools inspector on a feed card shows `style="--accent: #rrggbb;"` resolved from the poster.

### Step 6: Save pill on `pick-detail.page`

**Action**: Add a top-right frosted save pill (heart icon + "Save"). Light mode: black icon/text on white-glass. Dark mode: white on black-glass. Pill is a button with `data-test="save-pill"`. Local signal `saved = signal(false)`; click toggles. No backend — pure UI for now (persistence is out of scope).

**File**: `src/app/features/picks/pick-detail.page.ts` and its template/SCSS

**Pattern** (template fragment to place inside the hero container):
```html
<button
  type="button"
  data-test="save-pill"
  class="save-pill"
  [class.saved]="saved()"
  (click)="saved.set(!saved())"
  [attr.aria-pressed]="saved()"
  aria-label="Save pick">
  <ion-icon [name]="saved() ? 'heart' : 'heart-outline'"></ion-icon>
  <span>{{ saved() ? 'Saved' : 'Save' }}</span>
</button>
```

Component:
```typescript
saved = signal(false);
```

SCSS (scoped to `pick-detail.page.scss`):
```scss
.save-pill {
  position: absolute; top: 1rem; right: 1rem;
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 0.9rem; border-radius: 999px;
  border: 1px solid var(--hairline);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #000;
  font: 600 0.85rem/1 var(--font-sans, system-ui);
}
:host-context([data-theme="dark"]) .save-pill {
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}
.save-pill.saved { outline: 2px solid var(--accent, var(--accent-warm)); }
```

**Verify**: Open a pick-detail page. Pill appears top-right. Click toggles icon and label. Dark mode swaps colors. Screenshot on iPhone Mini viewport to check frosted effect renders.

### Step 7: Italic Cormorant colophon

**Action**: Add a footer block below the pick body with italic Cormorant. Content: small credit line — "Curated for issue №{{issue}} · Bubls {{ year }}".

**File**: `src/app/features/picks/pick-detail.page.ts` template + SCSS

**Pattern**:
```html
<footer data-test="pick-colophon" class="colophon">
  <em>Curated for issue №{{ issueNumber() }} · Bubls {{ currentYear }}</em>
</footer>
```
```scss
.colophon {
  padding: 2.5rem 1.25rem 3rem;
  text-align: center;
  font-family: var(--font-cormorant, Georgia, serif);
  font-style: italic;
  font-size: 0.95rem;
  color: var(--text-primary);
  opacity: 0.7;
  border-top: 1px solid var(--hairline);
  margin-top: 2rem;
}
```

**Verify**: Scroll to the end of a pick detail: italic serif colophon with a hairline separator sits above the page bottom.

### Step 8: Extract dominant accent for the detail hero

**Action**: In `pick-detail.page.ts`, on load, call `extractForMode` on the pick's poster and set `--accent` on `:host`. Uses the same service — proves the single-consumer assumption is now dual-use within the feature.

**File**: `src/app/features/picks/pick-detail.page.ts`

**Pattern**:
```typescript
private host = inject(ElementRef<HTMLElement>);
private accent = inject(AccentExtractorService);

async ngOnInit() {
  const pick = await this.loadPick();                 // existing load method
  this.pick.set(pick);
  const hex = await this.accent.extractForMode(pick.posterUrl);
  this.host.nativeElement.style.setProperty('--accent', hex);
}
```

**Verify**: DevTools shows the pick-detail host element has an inline `--accent: #rrggbb` style computed from the poster.

### Step 9: Set Picks world background

**Action**: Scope `:host` in the feed page's SCSS to set `--world-bg`. Light → `var(--page-bg-cream)`; dark override via `[data-theme="dark"] &`.

**File**: `src/app/features/picks/picks.page.scss`

**Pattern**:
```scss
:host {
  --world-bg: var(--page-bg-cream);
  display: block;
  min-height: 100%;
  background: var(--world-bg);
  color: var(--text-primary);
}
:host-context([data-theme="dark"]) {
  --world-bg: var(--page-bg);
}
```

**Verify**: Toggle system theme. Feed background shifts cream ↔ warm-black; masthead text colour follows via `--text-primary`.

---

## 5. Tests

Match existing frontend framework: **Karma + Jasmine + TestBed** (per codebase.md). `data-test` selectors only. Standalone components — provide dependencies directly.

### `mini-header.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MiniHeaderComponent } from './mini-header.component';

describe('MiniHeaderComponent', () => {
  let fixture: ComponentFixture<MiniHeaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [MiniHeaderComponent] }).compileComponents();
    fixture = TestBed.createComponent(MiniHeaderComponent);
    fixture.componentRef.setInput('issueNumber', 17);
    fixture.componentRef.setInput('issueDate', new Date('2026-04-16T00:00:00Z'));
    fixture.componentRef.setInput('location', 'Zürich');
    fixture.detectChanges();
  });

  it('rendersMastheadWithIssueNumber', () => {
    const issue = fixture.nativeElement.querySelector('[data-test="masthead-issue"]');
    expect(issue).withContext('masthead issue element missing').not.toBeNull();
    expect(issue.textContent.trim()).toBe('No. 17');
  });

  it('rendersLocationInCaps', () => {
    const loc = fixture.nativeElement.querySelector('[data-test="masthead-location"]');
    expect(loc.textContent.trim()).toBe('ZÜRICH');
  });

  it('rendersHairlineRule', () => {
    const rule = fixture.nativeElement.querySelector('[data-test="masthead-rule"]');
    expect(rule).withContext('hairline rule missing').not.toBeNull();
  });

  it('rendersBrandLiteral', () => {
    const masthead = fixture.nativeElement.querySelector('[data-test="masthead"]');
    expect(masthead.textContent).toContain('BUBLS');
  });
});
```

### `feed-card.component.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { FeedCardComponent } from './feed-card.component';

const mockPick = {
  id: 'p1',
  title: 'Herzog & de Meuron Retrospective',
  posterUrl: 'https://example.com/poster.jpg',
  pullQuote: 'An architecture of remembered light.',
  venue: 'Kunsthaus',
  city: 'Zürich',
  accent: '#c88a4a',
} as const;

describe('FeedCardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [FeedCardComponent] }).compileComponents();
  });

  [1, 3, 5].forEach(index => {
    it(`index${index}_rendersFullBleedLayout`, () => {
      const fixture = TestBed.createComponent(FeedCardComponent);
      fixture.componentRef.setInput('pick', mockPick);
      fixture.componentRef.setInput('index', index);
      fixture.detectChanges();
      const bleed = fixture.nativeElement.querySelector('[data-test="card-full-bleed"]');
      const quote = fixture.nativeElement.querySelector('[data-test="card-pull-quote"]');
      expect(bleed).withContext(`index ${index} should render full-bleed`).not.toBeNull();
      expect(quote).withContext(`index ${index} should NOT render pull-quote`).toBeNull();
    });
  });

  [2, 4].forEach(index => {
    it(`index${index}_rendersPullQuoteBlockquote`, () => {
      const fixture = TestBed.createComponent(FeedCardComponent);
      fixture.componentRef.setInput('pick', mockPick);
      fixture.componentRef.setInput('index', index);
      fixture.detectChanges();
      const quoteEl = fixture.nativeElement.querySelector('[data-test="card-quote"]');
      expect(quoteEl).withContext(`index ${index} should render pull-quote`).not.toBeNull();
      expect(quoteEl.tagName.toLowerCase()).toBe('blockquote');
      expect(quoteEl.textContent).toContain('remembered light');
    });
  });

  it('appliesPickAccentAsCustomProperty', () => {
    const fixture = TestBed.createComponent(FeedCardComponent);
    fixture.componentRef.setInput('pick', mockPick);
    fixture.componentRef.setInput('index', 1);
    fixture.detectChanges();
    const card = fixture.nativeElement.querySelector('[data-test="card-full-bleed"]');
    expect(card.style.getPropertyValue('--accent').trim()).toBe('#c88a4a');
  });
});
```

### `accent-extractor.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { AccentExtractorService } from './accent-extractor.service';
import { ThemeService } from '../../../services/theme.service';

describe('AccentExtractorService', () => {
  let themeMode: ReturnType<typeof signal<'light' | 'dark'>>;
  let service: AccentExtractorService;

  beforeEach(() => {
    themeMode = signal<'light' | 'dark'>('light');
    TestBed.configureTestingModule({
      providers: [{ provide: ThemeService, useValue: { mode: themeMode } }],
    });
    service = TestBed.inject(AccentExtractorService);
  });

  it('invalidUrl_returnsFallbackToken', async () => {
    const result = await service.extractDominant('not-a-real://protocol/nope.jpg');
    expect(result).toBe('var(--accent-warm)');
  });

  it('desaturate_reducesSaturationByAmount', () => {
    const out = service.desaturate('#ff0000', 0.5);
    expect(out).not.toBe('#ff0000');
    const r = parseInt(out.slice(1, 3), 16);
    const g = parseInt(out.slice(3, 5), 16);
    expect(g).withContext('green channel should rise as red desaturates').toBeGreaterThan(0);
    expect(r).withContext('red channel should drop as red desaturates').toBeLessThan(255);
  });

  it('desaturate_zeroAmount_returnsEquivalentColor', () => {
    const out = service.desaturate('#abcdef', 0);
    const r = parseInt(out.slice(1, 3), 16);
    const g = parseInt(out.slice(3, 5), 16);
    const b = parseInt(out.slice(5, 7), 16);
    expect(Math.abs(r - 0xab)).toBeLessThanOrEqual(1);
    expect(Math.abs(g - 0xcd)).toBeLessThanOrEqual(1);
    expect(Math.abs(b - 0xef)).toBeLessThanOrEqual(1);
  });

  it('darkMode_extractForMode_desaturatesResult', async () => {
    spyOn(service, 'extractDominant').and.resolveTo('#ff3366');
    themeMode.set('dark');
    const hex = await service.extractForMode('any.jpg');
    expect(hex).not.toBe('#ff3366');
    expect(hex.startsWith('#')).toBeTrue();
  });

  it('lightMode_extractForMode_returnsRawDominant', async () => {
    spyOn(service, 'extractDominant').and.resolveTo('#ff3366');
    themeMode.set('light');
    const hex = await service.extractForMode('any.jpg');
    expect(hex).toBe('#ff3366');
  });

  it('fallback_extractForMode_returnsFallbackUnchanged', async () => {
    spyOn(service, 'extractDominant').and.resolveTo('var(--accent-warm)');
    themeMode.set('dark');
    const hex = await service.extractForMode('any.jpg');
    expect(hex).toBe('var(--accent-warm)');
  });
});
```

### `pick-detail.page.spec.ts` (extend if existing; create if not)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PickDetailPage } from './pick-detail.page';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { AccentExtractorService } from './services/accent-extractor.service';

class PickDetailPageObject {
  constructor(private fixture: ComponentFixture<PickDetailPage>) {}
  get savePill() { return this.q('[data-test="save-pill"]') as HTMLButtonElement | null; }
  get colophon() { return this.q('[data-test="pick-colophon"]'); }
  private q(sel: string) { return this.fixture.nativeElement.querySelector(sel); }
}

describe('PickDetailPage', () => {
  let fixture: ComponentFixture<PickDetailPage>;
  let page: PickDetailPageObject;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PickDetailPage],
      providers: [
        { provide: ActivatedRoute, useValue: { paramMap: of(new Map([['id', 'p1']])) } },
        { provide: AccentExtractorService, useValue: { extractForMode: async () => '#c88a4a' } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(PickDetailPage);
    page = new PickDetailPageObject(fixture);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('rendersSavePill', () => {
    expect(page.savePill).withContext('save pill missing').not.toBeNull();
    expect(page.savePill!.getAttribute('aria-pressed')).toBe('false');
  });

  it('savePillClick_togglesSavedState', () => {
    page.savePill!.click();
    fixture.detectChanges();
    expect(page.savePill!.getAttribute('aria-pressed')).toBe('true');
    expect(page.savePill!.textContent).toContain('Saved');
  });

  it('rendersColophonInItalic', () => {
    const col = page.colophon;
    expect(col).withContext('colophon missing').not.toBeNull();
    const em = col.querySelector('em');
    expect(em).withContext('colophon should be italic').not.toBeNull();
    expect(em!.textContent).toContain('Bubls');
  });
});
```

If `PickDetailPage` loads data via a mechanism different from the mocked `ActivatedRoute` above, adapt injection to match the existing spec's pattern — see any sibling `*.page.spec.ts` in the same folder.

---

## 6. Commit Plan

One commit per logical unit. Subject line ≤ 72 chars. Deviations recorded in body with `Deviations:` prefix.

1. `feat(picks): rebuild mini-header as masthead` — `mini-header.component.ts`: issue/date/location signal inputs, Cormorant caps, hairline rule; dual-mode via tokens
2. `feat(picks): alternate feed-card rhythm by index` — `feed-card.component.ts` + feed page template: `index` input, full-bleed vs serif pull-quote branch, `--accent` custom property consumption
3. `feat(picks): accent extractor with dark-mode desaturation` — `accent-extractor.service.ts`, feed page wires `--accent` per pick
4. `feat(picks): save pill + italic colophon on detail` — `pick-detail.page.{ts,html,scss}`: frosted save pill, colophon, detail-hero accent application
5. `feat(picks): set cream world background` — `picks.page.scss`: `--world-bg` scoped to feed; dark override
6. `test(picks): masthead, alternation, accent, detail specs` — four spec files

Commits 1–5 are shippable independently. Commit 6 adds specs. Order matters only in that 2 depends on 1's shape, and 4 depends on 3's service — otherwise independent.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -30
npx ng build --configuration=development
```

**Expected delta**: baseline passing count + (4 masthead + 5 alternation + 6 accent + 3 detail) = **baseline + 18** passing. Zero pre-existing tests broken.

Manual smoke:
1. `npm start`, open `http://localhost:4201/home` (or the feed route from pre-flight).
2. Masthead displays `BUBLS · No. {{n}} · THU APR 16 · ZÜRICH` with hairline.
3. Scroll: cards alternate full-bleed → pull-quote.
4. Each card has a distinct `--accent` inline CSS var (inspect).
5. Toggle OS to dark mode: background → warm black, accents desaturate (visually less vivid).
6. Open a pick: save pill top-right, frosted; click toggles. Italic colophon at bottom.

---

## 8. Rollback

- **Per-commit**: each commit is independently revertible. `git revert <sha>`.
- **Per-step subset**: commits 4 (save pill) and 5 (world-bg) can be reverted without touching 1–3.
- **Per-branch**: `git reset --hard <pre-task-sha>` or `git branch -D <feature-branch>` after switching back to the base branch. [REQUIRES APPROVAL if branch is pushed]
- **Emergency kill**: comment out `[index]="i"` on `<app-feed-card>` in the parent template — restores every card to rendering as full-bleed (index defaults to `required`, so you'd need `[index]="1"` constant). Keeps the masthead + accent + detail pill live while isolating the alternation.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist under `src/app/features/picks/`** → use the path returned by the pre-flight `find`, typically under `src/app/pages/home/` or `src/app/pages/pick-detail/`. Log on the first commit: `Deviations: picks files under pages/ not features/picks/`.
- **Existing `MiniHeaderComponent` has inputs with different names** → keep the old input names, adapt the masthead template around them. Log the names retained. Do not rename inputs unless the rename is trivial and localized.
- **Existing `Pick` model lacks `accent` / `pullQuote` / `venue` / `city`** → add the missing fields to the model as optional (`?`). They are client-side enrichments, not API contract changes.
- **Test framework mismatch** (Karma/Jasmine missing; project uses Vitest or Jest) → translate specs silently to match the real runner; note framework used in the commit body.
- **`--font-cormorant` token missing** → Task 1 was supposed to add it. If absent, fallback to `Georgia, serif` inline (as the patterns show) and flag for Task 1 follow-up rather than adding the token here.
- **`backdrop-filter` unsupported** on target Safari/iOS version → leave the rule; browsers without it fall back to the semi-transparent `background`, which is acceptable.
- **`Step N unlocks obvious simplification for Step N+1`** → take it, log one line in the commit body.
- **Side-effect required** (push, deploy, native rebuild) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Picks data fetching is `Observable` not `Promise`** → use `firstValueFrom` or subscribe in Step 5/8 — do not rewrite the data layer. Log the shape used.

---

## 10. Out of Scope

This task rebuilds the Picks visual identity. It does **not** persist saves, add palette caching, build a saved-picks list, touch any world other than Picks, change picks data contracts, or introduce shared palette infrastructure. Dark-mode screenshot regression and contrast verification are Task 6's domain. Onboarding, Photoshoot, Text, and Shell layers are off-limits here.

- **Save persistence (localStorage / backend)** — deferred; the pill toggles ephemeral UI state. Revisit when a "Saved" tab enters the epic. Adding a `/api/picks/saves` endpoint now would pre-commit a shape with no consumer.
- **Accent palette caching** — deferred. Extraction runs on every feed render. If profiling in Task 6 shows jank, add a per-session `Map<posterUrl, hex>` inside `AccentExtractorService`. Do not pre-optimize.
- **Extracting multiple palette colors (primary + secondary + muted)** — out; one accent is the only current consumer. When a second slot appears in the design, extend.
- **Cross-feature use of `AccentExtractorService`** — deferred. Keep it feature-local. Moving to `src/app/shared/` happens when photoshoot or another world needs it — at that moment, lift, don't pre-lift.
- **Saved-picks route / tab** — out.
- **Replicating the magazine rhythm on `dashboard.page.ts`** — out; dashboard keeps its current form for now.
- **Contrast verification & screenshot matrix** — Task 6.
- **Adding fonts to `index.html` or Capacitor assets** — Task 1's job. If `Cormorant` is not loading, flag, do not add links here.
- **Onboarding migration, photoshoot immersive signal, text char-reveal** — their respective tasks.
- **Moving picks files from `pages/` to `features/`** — out. Structural reorganization is a separate task. Work in place.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale, token contract
- [Epic](./epic.md) — scope and success criteria
- [Timeline](./timeline.md) — status tracking (update to "In Progress" at Step 1, "Done" after Verification passes)