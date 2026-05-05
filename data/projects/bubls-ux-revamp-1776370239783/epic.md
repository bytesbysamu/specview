---
sidebar_position: 2
---

# 🎯 Bubls UX/UI Revamp — Epic

**Purpose**: Define scope and tasks for the four-worlds revamp.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

Bubls is three AI features under one roof. The current flat dark treatment forces them to look identical, which makes each feel less than it is — Picks reads like a dimmer version of Photoshoot, Photoshoot reads like a darker Text. Mobbin research across Claude, Lovi, Yazio, Sora, Apple Fitness, Tolan, Pinterest, Magnolia, and Houzz shows that multi-feature apps that earn retention share grammar (spacing, type, motion) but not appearance. Apple does this across Notes, Photos, and Music. This epic applies the same logic.

The second lever is light mode. A meaningful fraction of users default to light at the OS level and bounce when an app feels wrong for their environment. Shipping light as the default — designed natively, not converted from dark — opens the product to that audience without sacrificing the dark-mode identity users already know. System-driven (`prefers-color-scheme`) with no toggle keeps positioning simple.

**Value proposition**: Each world feels maxed-out for its core action. Picks reads like a Sunday magazine. Photoshoot feels like a darkroom ceremony. Text feels like a writer's desk. Onboarding feels like a welcoming foyer. Retention target: 40%+ four-week return, with signal measured per world.

---

## Scope

### What This Epic Covers

- Dual-mode token system (light default + dark variant) with per-world background slots
- System-driven theme via `prefers-color-scheme`, no user toggle
- Shell `immersive` signal for generation ceremonies
- Picks rebuild as "Sunday Magazine" — masthead, editorial card rhythm, per-pick accent extraction
- Photoshoot rebuild as "Polaroid Darkroom" — violet accent, immersive mode, contact-sheet history, italic copy
- Text rebuild as "Writer's Desk" — vellum background, typewriter key buttons, Cormorant output, char-by-char reveal
- Onboarding rebuild as "Foyer" — 3-screen step machine, 1 question per screen, gradient CTAs
- Accessibility floor: WCAG-AA contrast on every pair in both modes, `prefers-reduced-motion` honored

### What This Epic Does NOT Cover

- ❌ User-facing dark/light toggle (system-driven only until post-launch)
- ❌ New feature surfaces — no new routes, no new AI backends
- ❌ Design-system component library — tokens + scoped overrides only
- ❌ Light-mode derived from dark by lightness flip — each mode designed natively
- ❌ Changes to backend or AI providers
- ❌ Changes to existing user profile fields (dropped fields are deferred, not migrated)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Dual-Mode Token Plumbing** | None | — | 1 day | High |
| 2 | **Onboarding Foyer Rebuild** | 1 | 3, 4, 5 | 1.5 days | High |
| 3 | **Picks Sunday Magazine Pass** | 1 | 2, 4, 5 | 2 days | High |
| 4 | **Photoshoot Darkroom Pass** | 1 | 2, 3, 5 | 1 day | High |
| 5 | **Text Writer's Desk Pass** | 1 | 2, 3, 4 | 1 day | Medium |
| 6 | **A11y + Screenshot QA** | 2, 3, 4, 5 | — | 1 day | Medium |
| 7 | **Theme Toggle (System/Light/Dark)** | 1, 6 | — | 0.5 day | High |

### Task Details

#### Task 1: Dual-Mode Token Plumbing
Rewrite `tokens.scss` so light is the default (`:root`) and dark is a `[data-theme="dark"]` override. Add `--page-bg`, `--surface`, `--text-primary`, `--hairline`, `--accent-warm`, `--on-accent-warm`, `--shadow-soft` and their dark counterparts. Add a per-world background slot that each route's `:host` can override. Wire `prefers-color-scheme` via a `ThemeService` that sets `data-theme` on `document.documentElement` and listens for OS changes. Add the `immersive` signal to the shell so feature pages can hide chrome during ceremonies. Verify zero visual regression in dark by screenshot-diffing current dark against post-plumbing dark.

##### Learnings check-in
_To be filled during/after implementation._ Capture: did any existing component break when light was introduced? Which tokens needed a third value (e.g. mid-elevation surface)? What surprised you about the OS listener lifecycle?

##### Post-generation review (added 2026-04-16)
- **Patterns gap**: `ThemeService` is implicitly an Adapter (OS → UI) **+ Observer** (subscribes to `MediaQueryList.change`). Spell that out — name the Adapter contract and the Observer subscription, both with a teardown path.
- **Patterns gap**: `immersive` is a Registry-style flag (any feature can opt in, shell honors it). Frame it that way: define the contract once in the shell, document who is allowed to set it, so Task 4 doesn't write it inline.
- **Reference (port-source)**: `/projects/howDays/angular-sqlite-starter` — its `SqliteService` is the canonical adapter shape in this stack (Angular 19 + Capacitor 7 + signals). Mirror its constructor-injection style and the `isInitialized` signal pattern for `ThemeService`.

#### Task 2: Onboarding Foyer Rebuild
Rebuild `onboarding.page.ts` as a 3-step machine: city → interests (≤3 chips) → email. Drop the existing 5-field form entirely. Each step is a new `onboarding-step.component.ts` with a big Cormorant question on top, a single answer surface centered, and a gradient pill CTA at the bottom. Background is a warm radial gradient in light (cream → soft amber) and a deep navy → warm-black radial in dark. Step transitions are a 1200ms upward drift + crossfade. System-native list look for interests chips (Apple Fitness pattern). Delete the dropped fields from the profile model.

##### Learnings check-in
_To be filled during/after implementation._ Capture: did Lovi's inline loader pattern actually apply, or did it feel wrong for a city selector? Did the 3-step flow feel too short? What fields did you miss most?

##### Post-generation review (added 2026-04-16)
- **Patterns gap (Adapter)**: as written, the step machine writes directly to "the profile model" — no service boundary. Add an `OnboardingService` adapter so step UI never imports the profile schema. One reason: when interests/email move to backend persistence later, only the adapter changes.
- **Patterns gap (ACL)**: the city → interests → email payload needs a DTO mapper between step state (UI shape) and profile DTO (storage shape). Without it, renaming a profile field will ripple into the step components.
- **Patterns gap (Registry)**: "Delete the dropped fields from the profile model" is a global-schema mutation driven by a single feature's needs. Either keep the fields and ignore them, or document the deletion as a profile-registry migration owned outside this task.
- **Reference (port-source)**: howDays uses `@ngneat/query` to expose `data().isLoading / .data` directly to templates — port the same shape for the email-submit step so the spinner is signal-driven, not Observable plumbing.

#### Task 3: Picks Sunday Magazine Pass
Rebuild `mini-header.component.ts` as a masthead: "BUBLS · No. 17 · Thu Apr 16 · ZÜRICH" in dark caps on cream (light) or off-white on warm black (dark), with a hairline rule below. Update `feed-card.component.ts` to alternate card rhythm — indices 1, 3, 5 are full-bleed image; indices 2, 4 are text-led pull-quotes with serif blockquote. Extract per-pick `--accent` from the poster's dominant color (Canvas API on thumbnail) and apply as hint-tint; desaturate −15% in dark. Add save/heart pill to `pick-detail.page.ts` hero — top-right, frosted, black-on-white in light, white-on-black in dark. Add italic Cormorant footer colophon.

##### Learnings check-in
_To be filled during/after implementation._ Capture: did per-pick accent extraction read as tasteful or chaotic? Which Magnolia/Pinterest pattern actually applied on iPhone Mini? What did the masthead replace that users missed?

##### Post-generation review (added 2026-04-16)
- **Patterns gap (Adapter + Strategy)**: per-pick accent extraction (Canvas API on thumbnail) is browser-coupled inline in the card component. Extract a `ColorExtractionService` adapter so the strategy can vary — Canvas now, server-precomputed later, library swap (vibrant.js / median-cut) without touching the card.
- **Patterns gap (Observer)**: principles say "Features publish signals/events. Shell listens for analytics." The save/heart pill currently has no event. Add a `pickSaved` signal published by the feature; the shell observes for analytics + future cross-feature reactions (Text could draft about a saved pick).
- **Reference (port-source)**: howDays uses `ion-item-sliding` for swipe-to-delete with multi-action options (Edit/Share/Delete). Port that exact pattern for the save/heart + share + dismiss actions on `pick-detail`. It already handles long-press affordance and ships with Ionic 8.
- **Reference (port-source)**: howDays uses `@ngneat/query` cache invalidation on mutation — `['picks']` query key, save toggles update the cached entry, no refetch round-trip. Port verbatim for the heart-pill optimistic UI.

#### Task 4: Photoshoot Darkroom Pass
Scope `--accent` to cool violet (`#5B6CC0` light / `#818CF8` dark) inside `photoshoot.page.scss`. Swap body copy to Cormorant italic. On generation start, set shell `immersive` signal to true — shell hides tab bar and calls `StatusBar.hide()`. Background becomes gallery white `#FAFAFA` (light) or OLED true black `#000` (dark). Single liquid silhouette centerpiece via `progress-portrait.component.ts` with dual stroke color. On reveal, play scanline + grain overlay (existing), boosted intensity in dark. History strip becomes numbered grayscale "contact sheet" prints in hairline-bordered tiles. Heavy haptic on shutter, soft on reveal.

##### Learnings check-in
_To be filled during/after implementation._ Capture: did the Tolan-style centrepiece work on low-end devices? Did `StatusBar.hide()` cause layout shift? How did violet feel against the cream background in light mode — was `#5B6CC0` deep enough?

##### Post-generation review (added 2026-04-16)
- **Patterns gap (Anti-Corruption Layer)**: `StatusBar.hide()` is a Capacitor native call invoked directly from a feature page — exactly what ACL exists to prevent. Wrap it in a `ShellChromeService` (or a shell command on the immersive signal) so the Capacitor API can change without rippling into Photoshoot. **This is the clearest principle violation in the whole spec.**
- **Patterns gap (Registry)**: feature page sets `immersive` inline; if Text or Picks ever needs immersive, the contract is undefined. Define it in Task 1 as a registered shell capability — Photoshoot here just consumes it.
- **Patterns clean (Observer)**: shell observing the `immersive` signal is correct-by-accident. Name it explicitly so future readers don't break the pattern.
- **Reference (port-source)**: howDays exposes loading state as a signal (`tasks().isLoading`) directly to templates. Port the same shape for `immersive` so the shell template binds without an Observable subscription.

#### Task 5: Text Writer's Desk Pass
Update `text.page.scss` with vellum background (`#F4F0E8` light / `#1a1714` dark) plus faint SVG paper-grain noise overlay. Style mode buttons as typewriter keys — soft drop-shadow, slight depth, slot into a "carriage" row; matte-dark keys with raised highlight in dark. Input stays Instrument Sans with autoGrow. Output renders in Cormorant serif (the "AI writes prettier than you" moment). Output reveals character-by-character at ~18ms/char via a char-stream renderer in `text.page.ts`. Add `--accent-paper` token (sage `#5a7a6a` light / `#7a9a8a` dark).

##### Learnings check-in
_To be filled during/after implementation._ Capture: did Cormorant output actually feel like a writing upgrade, or just different? Was 18ms/char the right cadence? Did the noise overlay affect scroll performance?

##### Post-generation review (added 2026-04-16)
- **Patterns deferred correctly (Adapter)**: char-stream renderer lives in `text.page.ts` with no abstraction. Per *Engineering Discipline § Not-yet-built is the right state* — one consumer, ship the concrete case. Trigger to extract: Photoshoot or another world wants the same reveal cadence.
- **Patterns gap (Observer)**: the epic's success criterion includes per-world retention measurement, but Text emits no `outputCompleted` event. Without it, retention has nothing to subscribe to. Add the event in this task even though the analytics consumer ships later — cheap to add now, expensive to retrofit.
- **Reference (port-source)**: howDays' signal-driven state pattern (`data().isLoading / .data` in template) suits the char-stream output naturally — a `streaming` signal flips during reveal, template binds without RxJS.

#### Task 6: A11y + Screenshot QA
Run WCAG-AA contrast check on every text/bg pair across all four worlds × both modes. Capture screenshots on iPhone Mini and iPhone Pro Max for every route in both modes. Verify `prefers-reduced-motion` disables: onboarding step drift, photoshoot scanline, text char-stream reveal. Fix any contrast failures by adjusting tokens, not by regressing design. Produce a contact-sheet PDF of all captures for the retrospective.

##### Learnings check-in
_To be filled during/after implementation._ Capture: which pair failed WCAG-AA first? Did reduced-motion fallbacks feel acceptable or degraded? What did iPhone Mini expose that Pro Max hid?

##### Post-generation review (added 2026-04-16)
- **Patterns N/A**: verification task, no new code surfaces.
- **Add to scope**: structural test that asserts no feature page imports `@capacitor/status-bar` or `@capacitor/haptics` directly (must go through `ShellChromeService` per Task 4 review). One grep + one assertion + one failure message — per *Engineering Discipline § Structural tests*.

#### Task 7: Theme Toggle (System / Light / Dark)
Add a user-facing theme toggle that reverses the epic's original "no toggle until post-launch" non-goal. Extend Task 1's `ThemeService` with a `cycle()` method that rotates through three states — `system` → `light` → `dark` → `system` — persisting the explicit override in `localStorage.bubls.theme`. When state is `system`, keep following `prefers-color-scheme` via the existing `MediaQueryList` observer. When state is `light` or `dark`, ignore the OS and write the corresponding `data-theme` attribute on `document.documentElement`. Ship a single toggle UI element in the top-right of the shell masthead (visible on every route, not inside any world's `:host` override). Icons: a small system-chip (auto), sun, moon. Tap cycles. Haptic on tap (light impact). `data-test="theme-toggle"`. Tests: (a) cycle transitions, (b) `localStorage.bubls.theme` round-trip, (c) OS change while in `system` mode still flips, (d) OS change while in `light`/`dark` override is ignored, (e) a11y label `aria-label` rotates with state. No new tokens, no new backgrounds — reuse everything Task 1 shipped.

##### Learnings check-in
_To be filled during/after implementation._ Capture: did users discover the toggle without prompting? Did the 3-state cycle feel clear, or should it be a 2-state switch? How did it interact with the `immersive` signal on Photoshoot — was the toggle hidden during generation ceremonies?

##### Post-generation review (added 2026-04-16)
- **Patterns (Adapter + Observer)**: the existing `ThemeService` is already Adapter + Observer. This task only extends it — no new service. Name the extension explicitly: `cycle()` mutates the Adapter's source-of-truth; the existing `mode()` signal is still the sole Observer surface templates bind to.
- **Patterns (Registry)**: shell-chrome surface area (the masthead corner) is a registry-style contract — declare it once in the shell, Task 7 consumes one slot. Do not let feature pages inject their own chrome.
- **Scope guard**: the toggle MUST NOT touch the `immersive` signal contract from Task 4. When immersive is true, the toggle should auto-hide (shell-level rule), not vanish mid-animation.

---

## Success Criteria

- ✅ Light is the default mode; dark activates via `prefers-color-scheme: dark`
- ✅ No user-facing theme toggle exists
- ✅ Each of the four worlds has scoped `:host` overrides; no shared feature-level design system
- ✅ Onboarding completes in 3 screens (city → interests → email)
- ✅ Photoshoot generation triggers `immersive` signal; tab bar and status bar hide during generate
- ✅ Picks masthead replaces the "bubls." chrome on the picks route
- ✅ Text output renders in Cormorant with char-by-char reveal
- ✅ All text/bg pairs pass WCAG-AA in both modes
- ✅ `prefers-reduced-motion` disables every reveal animation
- ✅ Zero visual regression in existing dark mode post-plumbing (Task 1)
- ✅ Retention signal: 40%+ four-week unprompted return measured per world post-launch

---

## Non-Goals

- ❌ ~~User-facing dark/light toggle~~ (reversed post-launch — added as Task 7)
- ❌ New feature surfaces or routes
- ❌ Design-system component library
- ❌ Light mode auto-derived from dark values
- ❌ Changes to AI providers or backend endpoints
- ❌ Profile model migrations beyond removing dropped onboarding fields

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

