# 🛠️ Task 7: Theme Toggle (System / Light / Dark)

**Purpose**: Add a three-state theme toggle (`system` → `light` → `dark` → `system`) to the shell masthead, extending Task 1's `ThemeService` with a persisted explicit override while keeping OS-follow behavior in `system` mode.

**Effort**: 0.5 day

**Dependencies**: Task 1 (Dual-Mode Token Plumbing — `ThemeService` + `data-theme` attribute must exist)

**Parallel With**: Tasks 3, 4, 5 (feature world builds — no shared files)

**Blocks**: — (QA sweep in Task 6 should include the toggle once shipped)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 1 shipped a `ThemeService` that reads `prefers-color-scheme` and writes `data-theme="dark"` on `documentElement`. The epic's original non-goal ("no toggle until post-launch") is reversed here: users want agency over theme, and the plumbing already exists to make this cheap. The change is additive — a new `preference = signal<'system'|'light'|'dark'>('system')` persisted to `localStorage.bubls.theme`, a `cycle()` method that advances it, and a single toggle button in the shell masthead (visible on every route, outside any feature `:host`). When preference is `system`, the existing `MediaQueryList` observer continues driving `data-theme`; when it's `light` or `dark`, the observer is effectively ignored and the attribute is written explicitly. No new tokens, no new backgrounds, no cross-feature edits.

**Trade-offs considered**:
- **Three buttons (radio group) in settings page** — rejected because there is no settings page yet and a per-route button defeats the "masthead, always visible" requirement in the epic.
- **Two-state toggle (light ↔ dark only, no system)** — rejected because users on auto-switching OS setups lose the auto-follow benefit Task 1 just shipped; the epic explicitly requires `system` as a first-class state.
- **Chosen: single cycling button with three glyphs** — preferred because it collapses the full state space into one tappable element, fits the masthead footprint, and the glyph itself reveals current state (system-chip / sun / moon).

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status
git diff HEAD -- src/app/services/theme.service.ts src/app/services/theme.service.spec.ts src/app/shell/shell-layout.component.ts src/app/shell/shell-layout.component.spec.ts src/app/shell/shell-layout.component.scss src/app/shell/shell-layout.component.html
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -40
```

Also confirm Task 1 has landed:

```bash
grep -n "data-theme" src/app/services/theme.service.ts
grep -n "immersive" src/app/shell/shell-layout.component.ts
grep -n "@capacitor/haptics" package.json
```

**Expected**: `theme.service.ts` already sets `data-theme` on `documentElement`; shell has the `immersive` signal from Task 1; `@capacitor/haptics` is listed in codebase deps (see CODEBASE CONTEXT — Native).

**If working tree is dirty on any target file**: stash or commit unrelated changes BEFORE starting. Do not mix Task 7 edits with in-flight Task 3/4/5 work on feature pages (no overlap expected — flag if seen).

**Baseline recorded**: record the number of passing specs from `npm test` output (e.g., `N`/`N` passing). You will reference this number in Verification (Section 7).

---

## 3. Files

### To Create (new)
- `src/app/shell/components/theme-toggle.component.ts` (new) — standalone presentational button; injects `ThemeService`; renders one of three Ionicons based on `themeService.preference()`; calls `themeService.cycle()` + `Haptics.impact({ style: ImpactStyle.Light })` on tap.
- `src/app/shell/components/theme-toggle.component.spec.ts` (new) — TestBed spec + Page Object over `data-test="theme-toggle"`; covers glyph swap, aria-label rotation, haptic invocation (mocked).

### To Modify (cite CODEBASE CONTEXT)
- `src/app/services/theme.service.ts` (cited in PRIOR TASKS — Task 1 "To Create" list) — add `preference = signal<'system'|'light'|'dark'>(...)` initialized from `localStorage.bubls.theme`, `cycle()` method, effect that writes `data-theme` based on `preference()` + OS state. Keep the existing `MediaQueryList` listener; when `preference() === 'system'`, it drives the attribute, otherwise it is bypassed.
- `src/app/services/theme.service.spec.ts` (cited in PRIOR TASKS — Task 1) — extend with cycle / localStorage round-trip / OS-change-in-system / OS-change-in-override / aria-label-label suite (the last via the toggle component spec, but the service-side label source tested here).
- `src/app/shell/shell-layout.component.ts` (cited in PRIOR TASKS — Task 1 "To Modify") — import `ThemeToggleComponent`; add to the `imports` array of the standalone component.
- `src/app/shell/shell-layout.component.html` (or inline template on the `.ts` — check first and edit whichever exists) — render `<app-theme-toggle data-test="theme-toggle" />` in the top-right of the masthead, outside any `<ion-router-outlet>` and outside any feature `:host`.
- `src/app/shell/shell-layout.component.scss` (sibling of the `.ts` — check existence; if inline styles are used on the component, edit those) — one-rule positioning for the toggle (top-right corner of masthead, e.g., `position: absolute; top: var(--space-2); right: var(--space-2); z-index: 10;`). Use existing Task 1 spacing tokens only — do not introduce new tokens.

### To Leave Alone
- `src/theme/tokens.scss` — Task 1 owns the token layer; the toggle consumes existing tokens (no new ones, per the epic directive "No new tokens, no new backgrounds").
- `src/app/features/**` — feature pages are bounded contexts; the toggle lives in the shell and MUST NOT be placed inside any feature `:host` override. Do not edit any file under `features/`.
- `src/app/shell/feature-registry.ts` — feature registration is unrelated.
- `server/**` — FE-only task; zero backend, zero migrations, zero DTO changes.
- `src/app/services/auth-token.service.ts` — localStorage access for the theme preference is deliberately inline (one key, one read, one write); do not shoehorn it through `AuthTokenService`.
- `capacitor.config.ts` — `@capacitor/haptics` is already a declared dep (CODEBASE CONTEXT — Native); no plugin installation step.

---

## 4. Implementation Steps

### Step 1: Extend `ThemeService` with `preference` + `cycle()` + persistence

**Action**: Add a three-state `preference` signal, initialize it from `localStorage.bubls.theme` (with fall-through to `'system'`), add `cycle()` that rotates `system → light → dark → system`, and make the effective `data-theme` write derive from both `preference()` and the existing OS `MediaQueryList`. Keep the OS listener; it only drives `data-theme` when `preference() === 'system'`.

**File**: `src/app/services/theme.service.ts` (cited in PRIOR TASKS — Task 1)

**Pattern**:
```typescript
// additions only — existing init + MediaQueryList listener stay
import { Injectable, signal, computed, effect, inject } from '@angular/core';

type ThemePreference = 'system' | 'light' | 'dark';
type ThemeMode = 'light' | 'dark';
const STORAGE_KEY = 'bubls.theme';
const CYCLE_NEXT: Record<ThemePreference, ThemePreference> = {
  system: 'light',
  light: 'dark',
  dark: 'system',
};

@Injectable({ providedIn: 'root' })
export class ThemeService {
  // existing osMode = signal<ThemeMode>(...)  ← already set by the MediaQueryList listener from Task 1
  readonly preference = signal<ThemePreference>(this.readStoredPreference());
  readonly mode = computed<ThemeMode>(() =>
    this.preference() === 'system' ? this.osMode() : (this.preference() as ThemeMode),
  );

  constructor() {
    // replace (or add alongside) Task 1's existing effect that wrote data-theme from osMode
    effect(() => {
      const m = this.mode();
      document.documentElement.setAttribute('data-theme', m);
    });
  }

  cycle(): void {
    const next = CYCLE_NEXT[this.preference()];
    this.preference.set(next);
    if (next === 'system') {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, next);
    }
  }

  private readStoredPreference(): ThemePreference {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw === 'light' || raw === 'dark' ? raw : 'system';
  }
}
```

**Note on Task 1 compatibility**: Task 1's `data-theme`-writing effect (if it wrote from `osMode` directly) must be **replaced** by the `mode()`-driven effect above — otherwise two effects will race to set the attribute. Confirm via pre-flight grep that only one `setAttribute('data-theme', ...)` call remains in the service after editing.

**Verify**:
```bash
grep -n "setAttribute('data-theme'" src/app/services/theme.service.ts
# expect exactly one line
grep -n "preference" src/app/services/theme.service.ts
# expect preference signal declaration + cycle references
```

### Step 2: Build the `ThemeToggleComponent`

**Action**: Create a standalone, `OnPush` component with one `ion-button`. Template reads `themeService.preference()` to pick the icon (Ionicons `contrast-outline` for `system`, `sunny-outline` for `light`, `moon-outline` for `dark`) and the `aria-label` (`"Theme: system"`, `"Theme: light"`, `"Theme: dark"`). Click handler calls `themeService.cycle()` then `Haptics.impact({ style: ImpactStyle.Light })`, guarded by `Capacitor.isNativePlatform()`.

**File**: `src/app/shell/components/theme-toggle.component.ts` (new)

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { IonButton, IonIcon } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { contrastOutline, moonOutline, sunnyOutline } from 'ionicons/icons';
import { Capacitor } from '@capacitor/core';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { ThemeService } from '../../services/theme.service';

const ICON_BY_PREF = { system: 'contrast-outline', light: 'sunny-outline', dark: 'moon-outline' } as const;
const LABEL_BY_PREF = { system: 'Theme: system', light: 'Theme: light', dark: 'Theme: dark' } as const;

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IonButton, IonIcon],
  template: `
    <ion-button
      fill="clear"
      size="small"
      (click)="onTap()"
      [attr.aria-label]="label()"
      data-test="theme-toggle"
    >
      <ion-icon slot="icon-only" [name]="icon()"></ion-icon>
    </ion-button>
  `,
})
export class ThemeToggleComponent {
  private readonly themeService = inject(ThemeService);
  readonly icon = computed(() => ICON_BY_PREF[this.themeService.preference()]);
  readonly label = computed(() => LABEL_BY_PREF[this.themeService.preference()]);

  constructor() {
    addIcons({ contrastOutline, sunnyOutline, moonOutline });
  }

  async onTap(): Promise<void> {
    this.themeService.cycle();
    if (Capacitor.isNativePlatform()) {
      await Haptics.impact({ style: ImpactStyle.Light });
    }
  }
}
```

**Verify**:
```bash
ls src/app/shell/components/theme-toggle.component.ts
npx ng build --configuration=development 2>&1 | tail -30
# expect: zero TS errors; the component compiles standalone
```

### Step 3: Mount the toggle in the shell masthead

**Action**: Import `ThemeToggleComponent` into the shell and render it in the top-right of the masthead, outside the `<ion-router-outlet>` and outside any feature content. Use existing tokens for spacing (`--space-2`, `--space-3` — whichever Task 1 shipped; check `tokens.scss`).

**File**: `src/app/shell/shell-layout.component.ts` + its template (inline or `.html` sibling — pre-flight `grep -n "templateUrl\|template:" src/app/shell/shell-layout.component.ts` to determine which)

**Pattern**:
```typescript
// shell-layout.component.ts — additions
import { ThemeToggleComponent } from './components/theme-toggle.component';

@Component({
  // ...
  imports: [/* existing */, ThemeToggleComponent],
  // ...
})
```

Template (inline or `.html`) — add the toggle as a sibling of the outlet, not a child of any feature wrapper:
```html
<ion-header>
  <app-theme-toggle class="masthead-toggle" />
  <!-- existing masthead content -->
</ion-header>
<!-- existing <ion-content> / <ion-router-outlet> untouched -->
```

SCSS (in `shell-layout.component.scss` if it exists, else in the inline `styles` array):
```scss
.masthead-toggle {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  z-index: 10;
}
```

**Verify**:
```bash
grep -n "app-theme-toggle" src/app/shell/shell-layout.component.ts src/app/shell/shell-layout.component.html 2>/dev/null
# expect at least one hit — the template placement
grep -n "ThemeToggleComponent" src/app/shell/shell-layout.component.ts
# expect the import + imports-array entry
```

### Step 4: Service tests — cycle, persistence, OS-change behavior

**Action**: Extend `src/app/services/theme.service.spec.ts` with a suite covering the five tests listed in the epic: (a) cycle transitions, (b) `localStorage.bubls.theme` round-trip, (c) OS change while in `system` mode flips, (d) OS change while in `light`/`dark` override is ignored, (e) preference value is the source of the aria-label (the rendering of the label is tested in the component spec, Step 5).

**File**: `src/app/services/theme.service.spec.ts` (cited in PRIOR TASKS — Task 1)

**Pattern**: mock `window.matchMedia` to return a controllable `MediaQueryList` stub whose `matches` flag and `change` listener you can drive synchronously. Clear `localStorage` in `beforeEach`.

**Verify**: `npm test -- --watch=false --include=src/app/services/theme.service.spec.ts 2>&1 | tail -20` — all five new specs pass.

### Step 5: Component tests — glyph swap, aria-label, haptic invocation

**Action**: Create `theme-toggle.component.spec.ts` with a Page Object over `data-test="theme-toggle"` that asserts: glyph name matches preference state (all three), `aria-label` rotates correctly, tap calls `themeService.cycle()`, and `Haptics.impact` is invoked only when `Capacitor.isNativePlatform()` returns `true` (mock both).

**File**: `src/app/shell/components/theme-toggle.component.spec.ts` (new)

**Pattern**: provide a stub `ThemeService` with a writable `preference` signal; mock `@capacitor/core` and `@capacitor/haptics` via `jasmine.createSpyObj` or a manual stub object in `TestBed.overrideProvider` / `providers` array.

**Verify**: `npm test -- --watch=false --include=src/app/shell/components/theme-toggle.component.spec.ts 2>&1 | tail -20` — specs pass.

### Step 6: Full suite + manual smoke

**Action**: Run full suite, then load the app in the browser dev server and confirm (a) the toggle is visible in the top-right on every route, (b) three taps return to the starting glyph, (c) reload persists `light` and `dark` but not `system`, (d) on a device with OS auto-dark, flipping the OS setting flips the app only while the toggle shows `contrast-outline`.

**File**: — (no file edits; smoke only)

**Verify**:
```bash
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -30
# all tests pass; new count = baseline + new specs
npm start
# visit http://localhost:4200 (or the Ionic serve port), verify toggle on /photoshoot, /home, /picks, /text
```

---

## 5. Tests

Complete assertion bodies. Matches the repo's Karma + Jasmine setup (CODEBASE CONTEXT — Testing).

### `theme.service.spec.ts` additions

```typescript
import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService — preference, cycle, persistence', () => {
  let mql: { matches: boolean; addEventListener: jasmine.Spy; removeEventListener: jasmine.Spy; dispatchChange: (matches: boolean) => void };
  let service: ThemeService;

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');

    const listeners: Array<(e: { matches: boolean }) => void> = [];
    mql = {
      matches: false,
      addEventListener: jasmine.createSpy('add').and.callFake((_: string, fn: (e: { matches: boolean }) => void) => listeners.push(fn)),
      removeEventListener: jasmine.createSpy('remove'),
      dispatchChange: (matches: boolean) => {
        mql.matches = matches;
        listeners.forEach(fn => fn({ matches }));
      },
    };
    spyOn(window, 'matchMedia').and.returnValue(mql as unknown as MediaQueryList);

    TestBed.configureTestingModule({ providers: [ThemeService] });
    service = TestBed.inject(ThemeService);
    TestBed.flushEffects();
  });

  it('defaultsToSystem_whenLocalStorageEmpty', () => {
    expect(service.preference()).toBe('system');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('cycle_transitions_systemLightDarkSystem', () => {
    expect(service.preference()).toBe('system');
    service.cycle(); expect(service.preference()).toBe('light');
    service.cycle(); expect(service.preference()).toBe('dark');
    service.cycle(); expect(service.preference()).toBe('system');
  });

  it('cycle_toLight_persistsToLocalStorage', () => {
    service.cycle();
    expect(localStorage.getItem('bubls.theme')).toBe('light');
  });

  it('cycle_toDark_persistsToLocalStorage', () => {
    service.cycle();
    service.cycle();
    expect(localStorage.getItem('bubls.theme')).toBe('dark');
  });

  it('cycle_backToSystem_removesLocalStorageEntry', () => {
    service.cycle(); service.cycle(); service.cycle();
    expect(localStorage.getItem('bubls.theme')).toBeNull();
  });

  it('reload_withStoredDark_initializesToDark', () => {
    localStorage.setItem('bubls.theme', 'dark');
    const fresh = TestBed.runInInjectionContext(() => new ThemeService());
    TestBed.flushEffects();
    expect(fresh.preference()).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('osChange_whileInSystem_flipsDataTheme', () => {
    expect(service.preference()).toBe('system');
    mql.dispatchChange(true);
    TestBed.flushEffects();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    mql.dispatchChange(false);
    TestBed.flushEffects();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('osChange_whileInLightOverride_isIgnored', () => {
    service.cycle();
    TestBed.flushEffects();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    mql.dispatchChange(true);
    TestBed.flushEffects();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('osChange_whileInDarkOverride_isIgnored', () => {
    service.cycle(); service.cycle();
    TestBed.flushEffects();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    mql.dispatchChange(false);
    TestBed.flushEffects();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });
});
```

### `theme-toggle.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ThemeToggleComponent } from './theme-toggle.component';
import { ThemeService } from '../../services/theme.service';
import { Capacitor } from '@capacitor/core';
import { Haptics } from '@capacitor/haptics';

class ThemeTogglePageObject {
  constructor(private fixture: ComponentFixture<ThemeToggleComponent>) {}
  get root(): HTMLElement { return this.fixture.nativeElement.querySelector('[data-test="theme-toggle"]'); }
  get icon(): HTMLElement { return this.fixture.nativeElement.querySelector('ion-icon'); }
  get ariaLabel(): string | null { return this.root.getAttribute('aria-label'); }
  get iconName(): string | null { return this.icon.getAttribute('name'); }
  tap(): void { this.root.click(); }
}

describe('ThemeToggleComponent', () => {
  let fixture: ComponentFixture<ThemeToggleComponent>;
  let page: ThemeTogglePageObject;
  let themeStub: { preference: ReturnType<typeof signal<'system' | 'light' | 'dark'>>; cycle: jasmine.Spy };

  beforeEach(async () => {
    themeStub = { preference: signal<'system' | 'light' | 'dark'>('system'), cycle: jasmine.createSpy('cycle') };
    themeStub.cycle.and.callFake(() => {
      const next = { system: 'light', light: 'dark', dark: 'system' } as const;
      themeStub.preference.set(next[themeStub.preference()]);
    });

    await TestBed.configureTestingModule({
      imports: [ThemeToggleComponent],
      providers: [{ provide: ThemeService, useValue: themeStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(ThemeToggleComponent);
    page = new ThemeTogglePageObject(fixture);
    fixture.detectChanges();
  });

  it('systemPreference_showsContrastIconAndSystemLabel', () => {
    expect(page.iconName).toBe('contrast-outline');
    expect(page.ariaLabel).toBe('Theme: system');
  });

  it('lightPreference_showsSunIconAndLightLabel', () => {
    themeStub.preference.set('light');
    fixture.detectChanges();
    expect(page.iconName).toBe('sunny-outline');
    expect(page.ariaLabel).toBe('Theme: light');
  });

  it('darkPreference_showsMoonIconAndDarkLabel', () => {
    themeStub.preference.set('dark');
    fixture.detectChanges();
    expect(page.iconName).toBe('moon-outline');
    expect(page.ariaLabel).toBe('Theme: dark');
  });

  it('tap_callsThemeServiceCycle', () => {
    page.tap();
    expect(themeStub.cycle).toHaveBeenCalledTimes(1);
  });

  it('tap_threeTimes_returnsToSystemGlyph', () => {
    page.tap(); fixture.detectChanges();
    page.tap(); fixture.detectChanges();
    page.tap(); fixture.detectChanges();
    expect(page.iconName).toBe('contrast-outline');
  });

  it('tap_onNativePlatform_invokesHaptics', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
    const impact = spyOn(Haptics, 'impact').and.resolveTo();
    page.tap();
    await fixture.whenStable();
    expect(impact).toHaveBeenCalledTimes(1);
  });

  it('tap_onWebPlatform_skipsHaptics', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(false);
    const impact = spyOn(Haptics, 'impact').and.resolveTo();
    page.tap();
    await fixture.whenStable();
    expect(impact).not.toHaveBeenCalled();
  });
});
```

---

## 6. Commit Plan

One commit per logical unit. Each commit is independently revertible.

1. `feat(theme): add preference signal + cycle() + localStorage persistence to ThemeService` — `src/app/services/theme.service.ts`: adds `preference`, `cycle()`, derived `mode` computed, single consolidated `data-theme` effect.
2. `test(theme): cover cycle transitions, persistence, and OS-change gating` — `src/app/services/theme.service.spec.ts`: nine new specs.
3. `feat(shell): add ThemeToggleComponent and mount in masthead` — `src/app/shell/components/theme-toggle.component.ts` (new) + `src/app/shell/shell-layout.component.{ts,html,scss}` edits.
4. `test(shell): cover theme-toggle glyph swap, aria-label, haptic gating` — `src/app/shell/components/theme-toggle.component.spec.ts` (new).

**Deviation logging**: if any step deviates from this guide (e.g., Task 1's existing `data-theme` effect needs to be kept alongside the new one because it reads a different signal, or the shell uses inline styles so the SCSS edit moves into the `.ts`), prefix the commit body with `Deviations:` and one bullet per deviation. Target: 0–3 deviations across the four commits.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -40
npx ng build --configuration=development 2>&1 | tail -20
```

**Expected delta**: baseline `N` → `N + 16` passing (9 new service specs + 7 new component specs). Zero pre-existing tests broken. Production-mode build is NOT required for this task (no router/deploy changes); dev build suffices to catch TS/template errors.

**Manual smoke** (not automated in this task — Task 6 owns screenshot matrix):
- Toggle visible top-right on `/photoshoot`, `/home`, `/picks`, `/text`.
- Three taps return to the starting glyph.
- Hard reload after choosing `light` → still `light`. After cycling back to `system` → reload leaves `localStorage.bubls.theme` unset and OS drives the theme.

---

## 8. Rollback

- **Per-step**: each of the four commits is independently revertible via `git revert <sha>`. Reverting commit 3 leaves the service with the new preference API but no UI — safe transitional state.
- **Per-branch**: `git reset --hard <pre-task-7-sha>` or delete the feature branch. No DB changes to unwind, no deployed endpoints to roll back, no migrations.
- **localStorage residue on user devices**: reverting this task leaves stray `bubls.theme` entries in browsers that already ran it. The unchanged (Task 1) `ThemeService` ignores unknown localStorage keys, so the residue is inert. No cleanup required.

---

## 9. Deviations Allowed

- **Task 1's `data-theme` effect writes from `osMode` directly** → consolidate into the new `mode()`-driven effect in Step 1; do not ship two racing effects. Log as a deviation.
- **Shell uses inline template/styles rather than separate `.html`/`.scss` files** → edit the inline versions; the mounting + positioning still happen, the file count just changes. Log.
- **`ion-button` / `ion-icon` standalone imports surface differently in this codebase's Ionic version** → match the pattern used by existing standalone components (cited via CODEBASE CONTEXT — Patterns in Use: "Standalone components"). Do not introduce a new import style.
- **`@capacitor/haptics` is not yet in `package.json`** → STOP. CODEBASE CONTEXT lists it as a dep; if it's absent, the context has drifted. Flag before installing — do not `npm install` without approval.
- **Task 1 exported `osMode` under a different name** (`systemMode`, `prefers`) → reuse whichever name exists; do not rename Task 1's public API as a side-effect. Log.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit body, keep the scope otherwise identical.

---

## 10. Out of Scope

This task ships the three-state toggle, persistence, and masthead mounting. It does not ship any UX elaboration beyond the single cycling button, any backend persistence of the preference, any per-world override of the preference, any animation of the glyph swap, or any A11y instrumentation beyond `aria-label` + `data-test`. Keep the blast radius to the four files in Section 3 "To Modify" + two new files in Section 3 "To Create".

- **Server-side persistence of theme preference** (per-user on `superapp_users`) — deferred; localStorage is fine for a single-device prototype. Revisit when users install on multiple devices and complain.
- **Animated transition between themes** (fade/crossfade on `data-theme` swap) — deferred; Task 6 may introduce a reduced-motion-aware helper, and this can piggyback later.
- **Per-world theme override** (e.g., Picks always cream, Photoshoot always dark) — deferred and likely wrong; the epic's direction is that each world expresses identity through `--world-bg`, not by forcing a global theme.
- **Keyboard shortcut for theme cycle** — deferred; no keyboard story exists anywhere else in the app.
- **Settings page exposing the three states as a radio group** — deferred; no settings page exists, and creating one is a separate epic.
- **Syncing the toggle state to iOS `UITraitCollection`** (Capacitor native appearance) — deferred; only relevant if we ever ship native UI outside the WebView.
- **Analytics event on toggle tap** — deferred; Observer-pattern event bus doesn't exist yet (CODEBASE CONTEXT lists no analytics sink). Revisit when the first analytics consumer lands.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale (theme mechanism, signals, adapter boundary)
- [Epic](./epic.md) — Task scope and user-visible requirements
- [Timeline](./timeline.md) — Status tracking (update after done)