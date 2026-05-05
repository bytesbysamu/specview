# 🛠️ Task 1: Dual-Mode Token Plumbing

**Purpose**: Rewrite the theme token layer so light is the default, dark is a first-class `[data-theme="dark"]` override, and every world can inject its own background via a `--world-bg` slot. Wire a signals-based `ThemeService` that follows `prefers-color-scheme` and add an `immersive` signal to the shell for ceremonial feature pages.

**Effort**: 1 day

**Dependencies**: None

**Parallel With**: —

**Blocks**: Tasks 2 (Onboarding), 3 (Picks), 4 (Photoshoot), 5 (Text), 6 (A11y QA) — all consume the new tokens and the `immersive` signal.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The revamp needs a foundation that lets four feature worlds express distinct visual identities without forking the shell or duplicating SCSS. Today the theme file assumes dark as the universe and hardcodes surface colors; the four-worlds pass needs light-first tokens, a dark override via a single HTML attribute, and per-world background slots that features override in their own `:host`. We also need a ceremony knob: the photoshoot "darkroom" feature will hide tab chrome during a generation, and rather than coupling the photoshoot page to shell internals we expose a single `immersive` signal on the shell that any feature can toggle. Getting this right in one commit series unblocks all four parallel world builds.

**Trade-offs considered**:
- **CSS-in-JS / runtime style objects** — rejected; breaks the Ionic cascade, adds a runtime library, and every downstream task would have to learn a second styling dialect.
- **Class-based theme toggle (`.dark` on `<html>`)** — rejected; `data-theme` is the Ionic-idiomatic attribute, lets us extend to named worlds later (`data-theme="dark" data-world="picks"`) without a class-name explosion, and is easier to assert in tests.
- **`data-theme` + CSS custom properties + a signals `ThemeService`** — chosen; single source of truth on `documentElement`, no style swapping, features read `mode()` via signals and never touch `window.matchMedia` directly (adapter discipline at the UI boundary).

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git diff HEAD -- src/theme/tokens.scss src/app/shell/shell-layout.component.ts
npm test -- --watch=false --browsers=ChromeHeadless             # Baseline FE suite; record pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting. Target files (`src/theme/tokens.scss`, `src/app/shell/shell-layout.component.ts`) must be clean at HEAD.

**Baseline recorded**: write the pass count here after running (format: `N/N passing`). This is the `N` referenced in §7.

---

## 3. Files

### To Create (new)
- `src/app/services/theme.service.ts` — signals-based theme service; reads `prefers-color-scheme`, writes `data-theme` on `documentElement`, listens for OS-level changes.
- `src/app/services/theme.service.spec.ts` — unit tests for the service.
- `src/app/shell/shell-layout.component.spec.ts` — unit tests for the new `immersive` signal and `setImmersive()` method (create only if no spec file currently exists for the shell; otherwise extend the existing one — see Step 5).

### To Modify (cite CODEBASE CONTEXT)
- `src/theme/tokens.scss` — current dark-first token file → light defaults at `:root`, dark override at `:root[data-theme="dark"]`, new tokens added (`--page-bg`, `--surface`, `--text-primary`, `--hairline`, `--accent-warm`, `--on-accent-warm`, `--shadow-soft`, `--accent-paper`, `--world-bg`).
- `src/app/shell/shell-layout.component.ts` — add `immersive = signal(false)` + `setImmersive(value)`; template binds `[class.immersive]` on the root element; provide `ThemeService` via `inject()` so it boots at shell construction.
- `src/main.ts` — no change expected, but confirm the bootstrap path still constructs the shell (the `ThemeService` boots via shell injection, not `main.ts`).

### To Leave Alone
- `src/app/app.routes.ts` — routing is untouched in this task.
- `src/app/features/**` — feature-specific `:host` overrides land in their own tasks (2–5); do not pre-populate.
- `server/**` — no backend changes in this task; the onboarding column drop belongs to Task 2.
- `src/app/shell/feature-registry.ts` — feature registration is unrelated.
- `src/theme/reduced-motion.scss` — reused as-is (cited by architecture).

---

## 4. Implementation Steps

### Step 1: Read current token file and shell component

**Action**: Inspect the files you're about to replace, so the rewrite preserves any token name currently in use by feature SCSS. Grep the repo for every `var(--...)` reference and make sure the new token set is a strict superset of the names currently consumed.

**File**: `src/theme/tokens.scss` (existing), `src/app/shell/shell-layout.component.ts` (existing)

**Pattern**:
```bash
# List currently-consumed token names
grep -rhoE "var\(--[a-z0-9-]+\)" src/ | sort -u
```

**Verify**: the printed list must be a subset of the token names you'll define in Step 2 (enumerated in Architecture §Task 1 plus any the grep surfaces). If grep reveals a token name not in that list, add it to the new tokens.scss with a value that preserves current behavior — log as a deviation.

### Step 2: Rewrite `tokens.scss` — light default, dark override, per-world slot

**Action**: Replace the file with a two-section structure: `:root { ...light... }` and `:root[data-theme="dark"] { ...dark... }`. Every token listed in the epic must appear in both sections with WCAG-AA-compliant pairings. Add `--world-bg: var(--page-bg)` as the default so features can override via `:host { --world-bg: ... }`.

**File**: `src/theme/tokens.scss`

**Pattern**:
```scss
:root {
  /* Light defaults — WCAG-AA enforced against --text-primary */
  --page-bg: #FAF7F2;           /* cream */
  --surface: #FFFFFF;
  --text-primary: #1A1A1A;
  --hairline: rgba(26, 26, 26, 0.12);
  --accent-warm: #C8761A;       /* amber deepened per Architecture Risks */
  --on-accent-warm: #FFFFFF;
  --shadow-soft: 0 1px 2px rgba(26, 26, 26, 0.06), 0 4px 12px rgba(26, 26, 26, 0.04);
  --accent-paper: #5A7A6A;
  --world-bg: var(--page-bg);   /* feature :host may override */
}

:root[data-theme="dark"] {
  --page-bg: #0A0A0A;
  --surface: #141414;
  --text-primary: #F5F5F5;
  --hairline: rgba(245, 245, 245, 0.10);
  --accent-warm: #E8A85C;
  --on-accent-warm: #0A0A0A;
  --shadow-soft: 0 1px 2px rgba(0, 0, 0, 0.4), 0 4px 12px rgba(0, 0, 0, 0.3);
  --accent-paper: #7A9A8A;
  --world-bg: var(--page-bg);
}
```

**Verify**: `npm run build` succeeds; `grep -n "^:root" src/theme/tokens.scss` shows exactly two selectors.

### Step 3: Create `ThemeService` (port the Adapter discipline to the UI boundary)

**Action**: Create the file with a constructor that reads `matchMedia('(prefers-color-scheme: dark)')`, sets the initial `data-theme`, and subscribes to `change` events. Expose a `mode: Signal<'light' | 'dark'>` — features read `mode()`, never `window.matchMedia`.

**File**: `src/app/services/theme.service.ts` (new)

**Pattern**:
```typescript
import { Injectable, signal, Signal, DOCUMENT, inject, DestroyRef } from '@angular/core';

type Mode = 'light' | 'dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private doc = inject(DOCUMENT);
  private destroyRef = inject(DestroyRef);
  private _mode = signal<Mode>('light');
  readonly mode: Signal<Mode> = this._mode.asReadonly();

  constructor() {
    const mq = this.doc.defaultView?.matchMedia?.('(prefers-color-scheme: dark)');
    if (!mq) {
      this.apply('light');
      return;
    }
    this.apply(mq.matches ? 'dark' : 'light');
    const listener = (e: MediaQueryListEvent) => this.apply(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', listener);
    this.destroyRef.onDestroy(() => mq.removeEventListener('change', listener));
  }

  private apply(mode: Mode): void {
    this._mode.set(mode);
    const root = this.doc.documentElement;
    if (mode === 'dark') {
      root.setAttribute('data-theme', 'dark');
    } else {
      root.removeAttribute('data-theme');
    }
  }
}
```

**Verify**: `npx tsc --noEmit` clean; file size ≤ 40 lines.

### Step 4: Add `immersive` signal to the shell; inject `ThemeService`

**Action**: On `ShellLayoutComponent`, add a private `immersive = signal(false)` exposed via a readonly getter or direct signal, plus `setImmersive(value: boolean)`. Bind `[class.immersive]` on the root element in the template. Inject `ThemeService` so it boots when the shell instantiates.

**File**: `src/app/shell/shell-layout.component.ts` (cite CODEBASE CONTEXT: `src/app/shell/shell-layout.component.ts`)

**Pattern**:
```typescript
import { Component, ChangeDetectionStrategy, signal, inject } from '@angular/core';
import { ThemeService } from '../services/theme.service';

@Component({
  selector: 'app-shell-layout',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="shell-root" [class.immersive]="immersive()" data-test="shell-root">
      <!-- existing tab shell driven by FEATURE_ROUTES -->
      <ng-content />
    </div>
  `,
  /* ...existing imports / styleUrls preserved... */
})
export class ShellLayoutComponent {
  private theme = inject(ThemeService);       // boots theme watcher
  readonly immersive = signal(false);
  setImmersive(value: boolean): void {
    this.immersive.set(value);
  }
}
```

**Verify**: `npm run build`; `grep -n "setImmersive\|immersive" src/app/shell/shell-layout.component.ts` shows the new member + binding.

### Step 5: Write unit tests (see §5 for full bodies)

**Action**: Create the two spec files. Match the Karma + Jasmine convention already in the repo (inspect any existing `.spec.ts` to confirm imports/style before writing).

**File**: `src/app/services/theme.service.spec.ts` (new), `src/app/shell/shell-layout.component.spec.ts` (new or extended)

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless` — all new tests green, no pre-existing tests regressed.

### Step 6: Dark-mode screenshot diff (regression check)

**Action**: Before and after this task, capture a dark-mode screenshot of each route and diff them visually. The epic explicitly requires zero visual regression in dark post-plumbing. Use Playwright if configured, else a manual checklist — the executor should NOT install new tooling for this.

**File**: no file edit; capture artifacts under `docs/retrospectives/2026-04-16-task1-dark-diff/` as PNGs.

**Pattern**:
```bash
# If Playwright is already installed (check package.json):
npx playwright test --grep "dark baseline" || true   # skip silently if absent
# Else: manual — open each route in the browser with DevTools > Rendering >
# Emulate CSS media feature prefers-color-scheme = dark; compare by eye.
```

**Verify**: any diff beyond anti-aliasing is a blocker — STOP and flag as deviation per §9.

---

## 5. Tests

All assertions complete. Framework: Jasmine + Karma (the repo convention per CODEBASE CONTEXT > Dependencies > Testing). Before writing, open one existing `.spec.ts` in the repo to confirm the TestBed import surface.

### `src/app/services/theme.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { DOCUMENT } from '@angular/core';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  let mediaChangeListener: ((e: MediaQueryListEvent) => void) | null = null;
  let matches = false;

  const mockDoc = {
    documentElement: document.createElement('html'),
    defaultView: {
      matchMedia: (_q: string) => ({
        matches,
        addEventListener: (_evt: string, cb: (e: MediaQueryListEvent) => void) => {
          mediaChangeListener = cb;
        },
        removeEventListener: () => { mediaChangeListener = null; },
      }),
    },
  };

  beforeEach(() => {
    matches = false;
    mediaChangeListener = null;
    mockDoc.documentElement = document.createElement('html');
    TestBed.configureTestingModule({
      providers: [{ provide: DOCUMENT, useValue: mockDoc }],
    });
  });

  it('prefersLight_setsModeLightAndNoAttribute', () => {
    matches = false;
    const svc = TestBed.inject(ThemeService);
    expect(svc.mode()).toBe('light');
    expect(mockDoc.documentElement.hasAttribute('data-theme')).toBeFalse();
  });

  it('prefersDark_setsModeDarkAndDataThemeAttribute', () => {
    matches = true;
    const svc = TestBed.inject(ThemeService);
    expect(svc.mode()).toBe('dark');
    expect(mockDoc.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('osChangesToDark_updatesModeAndAttribute', () => {
    matches = false;
    const svc = TestBed.inject(ThemeService);
    expect(svc.mode()).toBe('light');
    mediaChangeListener!({ matches: true } as MediaQueryListEvent);
    expect(svc.mode()).toBe('dark');
    expect(mockDoc.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('osChangesToLight_removesDataThemeAttribute', () => {
    matches = true;
    const svc = TestBed.inject(ThemeService);
    expect(mockDoc.documentElement.getAttribute('data-theme')).toBe('dark');
    mediaChangeListener!({ matches: false } as MediaQueryListEvent);
    expect(svc.mode()).toBe('light');
    expect(mockDoc.documentElement.hasAttribute('data-theme')).toBeFalse();
  });
});
```

### `src/app/shell/shell-layout.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ShellLayoutComponent } from './shell-layout.component';

class ShellPageObject {
  constructor(private fixture: ComponentFixture<ShellLayoutComponent>) {}
  get root(): HTMLElement | null {
    return this.fixture.nativeElement.querySelector("[data-test='shell-root']");
  }
}

describe('ShellLayoutComponent', () => {
  let fixture: ComponentFixture<ShellLayoutComponent>;
  let po: ShellPageObject;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ShellLayoutComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(ShellLayoutComponent);
    po = new ShellPageObject(fixture);
    fixture.detectChanges();
  });

  it('initialState_immersiveIsFalse', () => {
    expect(fixture.componentInstance.immersive()).toBeFalse();
    expect(po.root?.classList.contains('immersive')).toBeFalse();
  });

  it('setImmersiveTrue_togglesImmersiveClass', () => {
    fixture.componentInstance.setImmersive(true);
    fixture.detectChanges();
    expect(fixture.componentInstance.immersive()).toBeTrue();
    expect(po.root?.classList.contains('immersive')).toBeTrue();
  });

  it('setImmersiveFalse_removesImmersiveClass', () => {
    fixture.componentInstance.setImmersive(true);
    fixture.detectChanges();
    fixture.componentInstance.setImmersive(false);
    fixture.detectChanges();
    expect(po.root?.classList.contains('immersive')).toBeFalse();
  });
});
```

### `src/theme/tokens.scss` — structural assertion (optional grep test)

If an existing structural test harness exists (check `src/**/*structural*`), add this; otherwise defer per "Structural tests — add as encountered, not before" in principles.

---

## 6. Commit Plan

One commit per logical unit:

1. `refactor(theme): light-first tokens with [data-theme="dark"] override` — `src/theme/tokens.scss`: rewrite tokens.scss per epic token list, add `--world-bg` slot.
2. `feat(shell): ThemeService follows prefers-color-scheme via signals` — `src/app/services/theme.service.ts`: new service, signals-based, writes `data-theme` on `documentElement`.
3. `feat(shell): immersive signal on shell for ceremonial feature pages` — `src/app/shell/shell-layout.component.ts`: add `immersive` signal + `setImmersive()`, inject `ThemeService` so it boots.
4. `test(shell): unit tests for ThemeService and immersive signal` — `theme.service.spec.ts`, `shell-layout.component.spec.ts`: assertions per §5.
5. `chore(theme): dark-mode screenshot diff baseline (no regression)` — capture artifacts if any, or empty commit with message body documenting the manual diff if no tooling present.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation. Keep the total to ≤3 per commit (principle: judgment-calls-per-commit is the spec-quality metric).

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build
```

**Expected delta**: `N` → `N + 7` passing (4 new `ThemeService` specs + 3 new shell specs). Zero pre-existing tests broken. `npm run build` clean with no new warnings.

Manual check: open the app in the browser, toggle DevTools → Rendering → `prefers-color-scheme`. The `<html>` element should gain/lose `data-theme="dark"` and the page should repaint without a flicker.

---

## 8. Rollback

- **Per-step**: each of the 5 commits is independently revertible. `git revert <sha>` on any single commit restores the prior state.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (record the SHA during §2 Pre-flight) or delete the feature branch.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT (e.g., confirm `src/app/shell/shell-layout.component.ts` exists); if genuinely missing, STOP and flag — do NOT invent a replacement file.
- **Test framework mismatch** → the repo says Karma + Jasmine; if inspection of existing specs reveals Vitest/Jest instead, translate assertions silently to match and log in the commit body.
- **Grep in Step 1 finds an unlisted token** (e.g., `--accent-cool` used by photoshoot) → add it to the new tokens.scss with a light + dark value derived from Architecture §Task 4; log as deviation.
- **Playwright not installed** → skip Step 6 screenshot tooling; perform the manual dark-mode eyeball diff and document in the commit body. Do NOT install Playwright in this task (that's Task 6's scope).
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]`, ask.
- **Existing `shell-layout.component.spec.ts` already exists** → extend it with the three new tests rather than creating a second file; log deviation.

---

## 10. Out of Scope

This task plumbs tokens, the theme service, and the immersive signal — nothing more. It does **not** restyle any feature page, build any new shared component, modify backend code, or introduce a user-facing theme toggle. Feature-scoped `:host { --world-bg: ... }` overrides belong to Tasks 2–5; an explicit light/dark toggle (if it ever ships) is a separate epic; onboarding field removal is Task 2. An eager executor will notice that Picks or Photoshoot pages currently look broken under light mode — that is expected and acceptable for this commit series, because Tasks 3 and 4 restyle them.

- **Per-world `:host` overrides** — deferred to Tasks 2–5; each world owns its own background slot in its own commit.
- **Explicit user theme toggle UI** — deferred indefinitely; the epic states no toggle for v1. Revisit when a user explicitly asks.
- **Named worlds on `data-theme`** (e.g., `data-theme="dark" data-world="picks"`) — speculative infrastructure; ship the concrete `[data-theme="dark"]` case first, extract later only if a second override axis appears.
- **Theme-switching animation** — no CSS transition on token swap in this task; sudden repaint is the acceptable MVP behavior.
- **Onboarding field schema drop** — Task 2 owns the Alembic migration; do not touch `server/` here.
- **Playwright screenshot matrix** — Task 6 owns the e2e screenshot harness; Step 6 in this guide is an eyeball check only.
- **Contrast-check script** — Task 6 owns `scripts/a11y-contrast-check.mjs`; do not build it here even though you're editing the pairs it will later enforce.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)