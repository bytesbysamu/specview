---
sidebar_position: 3
---

# 🏗️ Bubls UX/UI Revamp — Solution Architecture

**Purpose**: Technical design for the four-worlds revamp.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

The revamp keeps the existing Angular 19 + Ionic 8 + Capacitor 7 shell and all four feature routes. Changes are concentrated in three layers:

1. **Token layer** (`src/theme/tokens.scss`): rewritten to light-default with `[data-theme="dark"]` override and per-world background slots.
2. **Shell layer** (`shell-layout.component.ts`, new `theme.service.ts`): adds the `immersive` signal consumed by feature pages and the theme service that watches `prefers-color-scheme`.
3. **Feature layer** (each of `picks/`, `photoshoot/`, `text/`, `onboarding/`): scoped `:host` overrides, no cross-feature imports, no new shared components except `onboarding-step.component.ts` within the onboarding feature.

No new AI providers. No new backend endpoints. No database migrations beyond removing dropped onboarding profile fields from the Neon schema (Alembic migration).

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = bounded context | Each of the four worlds owns its SCSS, logic, and visual identity. Shared code stays in `shared/` (token primitives, tab pill, reduced-motion mixins) |
| Signals, OnPush, standalone | `ThemeService` exposes a `mode: Signal<'light' \| 'dark'>`; shell exposes `immersive: Signal<boolean>`. All feature pages are `ChangeDetectionStrategy.OnPush` |
| Adapter (at infra boundary) | AI providers unchanged; this epic doesn't cross the adapter — but the `ThemeService` follows the same pattern: UI reads `mode()`, never `window.matchMedia` directly |
| data-test selectors only | Every new interactive element (onboarding step CTA, save pill, mode button, theme-reactive surface) gets a `data-test` attribute |
| Explicit over implicit | No global SCSS inheritance tricks. Each world imports `tokens.scss` and overrides via `:host`. No CSS-in-JS |
| Accessibility floor | WCAG-AA pair contrast enforced in `tokens.scss` comments and verified in Task 6 |
| Not-yet-built is the right state | No design-system library. No theme-switching animation framework. No color-extraction service abstracted before the single Picks use case proves it |

---

## Component Design

### Task 1: Dual-Mode Token Plumbing

**Purpose**: Introduce light as the default mode, dark as a first-class variant, and per-world background slots.

**Components**:
- `src/theme/tokens.scss` — rewritten: `:root` holds light defaults, `:root[data-theme="dark"]` overrides. Adds `--page-bg`, `--surface`, `--text-primary`, `--hairline`, `--accent-warm`, `--on-accent-warm`, `--shadow-soft`, `--accent-paper`, `--world-bg` (per-world slot)
- `src/app/services/theme.service.ts` (new) — signal-based service. On init, reads `window.matchMedia('(prefers-color-scheme: dark)')`, sets `data-theme` on `documentElement`, listens for changes
- `src/app/shell/shell-layout.component.ts` — adds `immersive = signal(false)`, exposes `setImmersive(value: boolean)`; template binds `[class.immersive]="immersive()"`
- `src/theme/reduced-motion.scss` — existing mixin reused

**Patterns**: CSS custom property cascade; Angular signals; explicit service injection via `inject()`

### Task 2: Onboarding Foyer Rebuild

**Purpose**: Replace 5-field form with 3-screen step machine.

**Components**:
- `src/app/features/onboarding/onboarding.page.ts` — rebuilt as step machine with `currentStep = signal<0 | 1 | 2>(0)`, `answers = signal<OnboardingAnswers>({ city: '', interests: [], email: '' })`
- `src/app/features/onboarding/components/onboarding-step.component.ts` (new) — standalone, accepts `question`, `inputMode`, emits `next`
- `src/app/features/onboarding/onboarding.page.scss` — dual radial gradient background, Cormorant question type scale
- `src/app/features/onboarding/onboarding.model.ts` — shrink `OnboardingAnswers` to `{ city, interests, email }`
- `server/modules/onboarding/` — Flask: remove `name`, `role`, `stack`, `style`, `goals` from the profile DTO
- `migrations/versions/XXXX_drop_onboarding_fields.py` (new) — Alembic migration dropping the columns

**Patterns**: Step machine via signals; system-native list for chips; Page Object test class using `data-test` selectors

### Task 3: Picks Sunday Magazine Pass

**Purpose**: Editorial magazine identity — masthead, alternating card rhythm, per-pick accent.

**Components**:
- `src/app/features/picks/components/mini-header.component.ts` — rebuilt as masthead: issue number, date, location in dark caps on cream (light) / off-white (dark) with hairline rule
- `src/app/features/picks/components/feed-card.component.ts` — alternation logic: `@Input() index: number`; indices 1,3,5 full-bleed, 2,4 pull-quote with serif blockquote
- `src/app/features/picks/services/accent-extractor.service.ts` (new, feature-scoped) — Canvas API reads dominant color from poster thumbnail; desaturates −15% in dark mode
- `src/app/features/picks/pick-detail.page.ts` — adds save pill (top-right, frosted, dual variant); italic Cormorant footer colophon
- `src/app/features/picks/picks.page.scss` — `:host { --world-bg: var(--page-bg-cream); }` (light) / overrides in dark

**Patterns**: Input-driven alternation over conditional templates; feature-scoped service (no `shared/`); scoped `:host` overrides

### Task 4: Photoshoot Darkroom Pass

**Purpose**: Ceremony — single glowing thing in a void, violet accent, immersive shell.

**Components**:
- `src/app/features/photoshoot/photoshoot.page.ts` — on generation start, calls `shellLayout.setImmersive(true)`; on finish/error, `setImmersive(false)`. Also calls `StatusBar.hide()` / `StatusBar.show()` via Capacitor
- `src/app/features/photoshoot/photoshoot.page.scss` — `:host { --accent-cool: #5B6CC0; --world-bg: #FAFAFA; }` light / `#818CF8` + `#000` dark; all copy `font-family: var(--font-cormorant); font-style: italic`
- `src/app/features/photoshoot/components/progress-portrait.component.ts` — dual stroke color via `--accent-cool`; single liquid silhouette centerpiece
- `src/app/features/photoshoot/components/contact-sheet.component.ts` (new) — numbered grayscale history tiles with hairline borders
- `src/app/features/photoshoot/photoshoot.page.html` — existing scanline + grain overlay; boosted intensity in dark via CSS opacity var

**Patterns**: Shell signal consumption; Capacitor plugin call isolated to the feature; feature-local presentational components

### Task 5: Text Writer's Desk Pass

**Purpose**: Manuscript aesthetics — vellum background, typewriter keys, Cormorant output, char-by-char reveal.

**Components**:
- `src/app/features/text/text.page.scss` — vellum background with SVG paper-grain noise overlay (data URI); typewriter key styling on `.mode-button`
- `src/app/features/text/text.page.ts` — adds `revealedText = signal('')`, `revealChar()` method running at 18ms/char via `setInterval`; clears on new generation; respects `prefers-reduced-motion` (full text immediately)
- `src/app/features/text/components/typewriter-keys.component.ts` (new) — row of mode buttons as keys in a "carriage"
- `src/theme/tokens.scss` — adds `--accent-paper: #5a7a6a` light / `#7a9a8a` dark

**Patterns**: Signal-driven character reveal; feature-scoped noise overlay (no shared asset); reduced-motion fallback

### Task 6: A11y + Screenshot QA

**Purpose**: Verify accessibility floor and capture retrospective evidence.

**Components**:
- `scripts/a11y-contrast-check.mjs` (new) — reads `tokens.scss`, computes WCAG contrast for every documented pair, fails on < 4.5:1 (body) or < 3:1 (large text)
- `e2e/screenshot-matrix.spec.ts` (new) — Playwright run on iPhone Mini + Pro Max viewports, light + dark, one screenshot per route
- `docs/retrospectives/2026-04-XX-revamp-contact-sheet.pdf` (new) — compiled contact sheet from screenshot matrix

**Patterns**: Structural test (contrast pairs enumerated in tokens comments); Playwright matrix runner

---

## Execution Flow

```
[Phase 1: Plumbing]
   Task 1 ──→ unlocks all downstream tasks

[Phase 2: Parallel World Builds]
   Task 2 (Onboarding)  ─┐
   Task 3 (Picks)        │
   Task 4 (Photoshoot)   │── all consume Task 1 tokens
   Task 5 (Text)         │
                          ▼
[Phase 3: QA]
   Task 6 ──→ ships
```

Task 2 can ship to production independently while Tasks 3, 4, 5 are still in flight — onboarding lives alongside existing dark surfaces without conflict because the token plumbing is already in place.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Theme mechanism | `data-theme` attribute + CSS custom properties | Standard cascade; no runtime style swap; single source of truth (`documentElement`) |
| Theme source | `prefers-color-scheme`, no user toggle | Keeps positioning simple; toggle can come later with zero re-architecture |
| Per-world identity | Scoped `:host` overrides | Avoids a design-system library before we've proven the pattern across four worlds |
| Color extraction (Picks) | Canvas API, feature-scoped service | Single consumer; no pre-emptive shared service until a second consumer appears |
| Immersive mode | Shell `Signal<boolean>`, feature calls `setImmersive()` | Observer pattern; shell listens, feature publishes; no cross-feature imports |
| Status bar control | Capacitor `StatusBar` plugin inside photoshoot feature | Only photoshoot needs it — isolating it per the "one concrete case" principle |
| Char-by-char reveal (Text) | Feature-local `setInterval` on a signal | No animation library; 18ms cadence is the only tuning knob |
| Dropped onboarding fields | Alembic migration drops columns | Not-yet-built is the right state — the fields had no downstream consumer |
| Dark-mode verification | Screenshot diff before/after Task 1 | Catches regression the token rewrite could introduce |
| Reduced-motion scope | Every reveal animation — step drift, scanline, char-stream | Accessibility floor, non-negotiable |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Per-pick accent extraction looks chaotic in the feed | Desaturate −15% in dark; cap saturation at 60% in both modes; fall back to default accent if extraction fails |
| `StatusBar.hide()` causes layout shift on generate | Wrap in `requestAnimationFrame`; test on iPhone Mini (smallest viewport) in Task 6 |
| Char-stream reveal tanks scroll performance | Render into a detached text node; only commit to DOM every N chars if profiling shows jank |
| Light mode fails WCAG-AA on amber accent | Deepen to `#C8761A` (per brain dump); Task 6 contrast script catches regressions |
| Onboarding migration drops fields users still reference elsewhere | Audit `profile` usage before migration; if any read site exists, fail the task and revisit scope |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

