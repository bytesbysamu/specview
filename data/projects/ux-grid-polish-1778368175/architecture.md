# 🏗️ Solution Architecture: UX: App Grid Polish

## Architecture Overview

This epic is a pure frontend concern: three independent improvements to the project grid that share no runtime dependencies, no service changes, and no new components. The changes live across three files — `project-teaser.ts`, `app.component.html`, and `styles.css` — and each task can be read, reviewed, and merged in isolation. The only sequencing constraint is that the breathing-room padding values must be settled before the semantic border offset can be computed, since `padding-left` must shrink by exactly the border width to keep content visually aligned.

The central architectural insight is that semantic color belongs to the CSS layer, not the component layer. Rather than threading color tokens through Angular component inputs or computing class strings in TypeScript, the design plants a single `data-section` attribute on the nearest ancestor container and lets CSS attribute selectors do the rest. This keeps all color logic in one place, makes the rules trivially auditable, and ensures that any future section type gets color behavior simply by adding a rule — no component changes required.

The teaser fix follows the same philosophy of minimal surface: the logic already exists (`firstNonHeadingSentence`), the data is already fetched (`leadFileContent`), and the invocation is already wired for two of the three sections. The Braindumps branch simply has not been connected to the same path. Closing that gap requires touching one function in one file and nothing else.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | No new CSS custom property system, no new component inputs, no new Angular services. Each fix is the minimum change to close the gap. |
| P7 — File Size & Structure | All CSS changes go into the existing `styles.css`. No new stylesheet. No scoped component styles for cross-cutting concerns. |
| Semantic over decorative | Color assignments are grounded in project state (running, ready, idle) — not aesthetic preference. New palette values are not introduced; existing CSS variables carry the full semantic load. |
| Attribute selectors as data contracts | `data-section` acts as a typed enum on the DOM. CSS consumes it. TypeScript only writes it. The two layers are decoupled — neither needs to know the other's implementation. |
| Cascade containment | Grid card and column card diverge in their padding model. The cascade resolves this through selector specificity: base rules on `.file-item`, overrides scoped to `.section-group-cards .file-item`. No `!important`. |

---

## Component Design

### Teaser Logic (`project-teaser.ts`)

**Purpose**: Eliminates identical card text across all Braindumps cards and surfaces the actual intent of each project.

The function `projectTeaser()` already accepts `leadFileContent` as a parameter and already uses `firstNonHeadingSentence()` for the Specced and Ready-to-build branches. The Braindumps branch diverges only by ignoring `leadFileContent` entirely and returning a hardcoded string. The fix adds a conditional guard that mirrors what the other branches already do: try the content first, fall back to the static string only when the content is empty or yields no prose sentence.

The fallback string `"Braindump — ready to generate"` is preserved as the zero-content state. Cards with an empty or heading-only `braindump.md` will still display it. The change is additive, not substitutive.

No template changes are required because `teaserFor()` in `app.component.ts` already passes `leadFileContent` for the Braindumps case. The parameter is being discarded downstream; making use of it is purely an internal fix.

### Semantic Color System (`app.component.html` + `styles.css`)

**Purpose**: Adds a single visual axis — section state — to the grid without introducing new data, new components, or new color tokens.

The strategy uses a `data-section` HTML attribute as the bridge between Angular's data model and CSS's visual rules. The attribute is written once per group in the template; CSS reads it via attribute selectors to set a `--section-accent` custom property at the container level. Child `.file-item` elements inherit this property and apply it as a left border.

Two DOM contexts must be handled independently:

**Grouped (all-sections) view**: The `data-section` attribute lives on `.section-group`. Cards inside `.section-group-cards` use a 2D CSS grid — no negative-margin hover bleed is needed or desirable. The card override is `margin: 0; padding: 16px`, and the border is applied without a compensating bleed. Exact selectors:
```css
[data-section="Active"]     { --section-accent: var(--status-running); }
[data-section="Specced"]    { --section-accent: var(--accent); }
[data-section="Braindumps"] { --section-accent: var(--ink-muted); }

.section-group-cards .file-item {
  border-left: 3px solid var(--section-accent, transparent);
  padding-left: 13px; /* 16px grid base − 3px border */
}
```

**Single-section column view**: The `data-section` attribute lives on `.file-column`. Cards use negative-margin hover bleed (`margin: 0 -12px; padding: 16px 12px`). The border-left reduces `padding-left` by 3px to keep content aligned with the column edge. Exact selector:
```css
[data-section].file-column .file-item {
  border-left: 3px solid var(--section-accent, transparent);
  padding-left: 9px; /* 12px column base − 3px border */
}
```

`padding-left` correction is the one place where the border and padding changes are coupled. This is why T1 (breathing room) must be settled before T3 (semantic color) — the exact corrected value depends on the chosen base padding.

The `data-section` values are the string literals of the `Section` type from `section-taxonomy.service.ts`: `"Active"`, `"Specced"`, `"Braindumps"`, `"Ready to build"`, `"Archive"`. The binding in the template is `[attr.data-section]="group.section"` (grouped view) and `[attr.data-section]="activeSection()"` (column view). `Archive` receives no `--section-accent` declaration and falls back to `transparent`.

Section title tinting (Active = green, Specced = blue) is scoped to `.section-group-title` within the same attribute selector block. Braindumps, Ready to build, and Archive titles remain unstyled. This restraint follows the ClawBoi principle: color marks urgency, not identity.

The four section values — `Active`, `Specced`, `Braindumps`, `Ready to build` — are treated as a closed enum. `Archive` receives no border (transparent default). Adding a new section type in the future requires one CSS block, no TypeScript.

### Card Breathing Room (`styles.css`)

**Purpose**: Aligns visual density with the ClawBoi reference — content-forward, not data-dense.

The dimension changes are purely additive: padding increases, grid min-width increases, section group spacing increases. No layout algorithm changes. The key structural decision is that grid cards and column cards share a base rule but diverge in their override:

- **Base** (column layout): `padding: 16px 12px` with `margin: 0 -12px` hover bleed — matches ClawBoi's column-provides-horizontal-padding model.
- **Override** (grid layout): `margin: 0; padding: 16px` flat — 2D grids do not benefit from bleed, and bleed in a multi-column grid creates misaligned hit areas.

The `minmax(260px, 1fr)` increase on the grid template is the only change to layout geometry. It pushes the breakpoint at which the grid collapses from three columns to two slightly wider — consistent with the intent to give cards more visual room at narrower viewports.

### CSS Animation Backport (`styles.css`)

**Purpose**: Closes the gap between visual patterns defined in `playground.html` and the live app, for three animation concerns already scoped to this epic.

**Gen-status shimmer (5b)**: The static `.gen-status-bar--active` track is replaced with a keyframe-driven gradient sweep. The animation communicates "work in progress" without requiring any polling state to be exposed to the template. The CSS targets the element's active state class directly.

**Diff block highlights (5c)**: `.diff-block-remove` and `.diff-block-add` CSS rules render the semantic content already produced by `diffHtmlUnified`. The diff HTML is already generated in `app.component.ts`; the rules simply make it visible. No TypeScript changes are needed.

**Count-pulse verification (5e)**: The template already references `section-count-pulse`. The task is to verify that the `@keyframes count-pulse` definition exists in `styles.css` and matches what the template applies. If the keyframe is absent or misnamed, it is added. This is a correctness fix, not a new feature.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 17 (existing) | All changes are template bindings and CSS — no framework boundary is crossed |
| Styling | CSS custom properties + attribute selectors | Keeps color logic in CSS, out of TypeScript; survives dark mode automatically via existing variable definitions |
| State bridge | HTML `data-section` attribute | Typed string from Angular template; consumed by CSS only; zero coupling between layers |
| Icon library | Deferred — not in this epic | Evaluated in a standalone epic once a library decision is confirmed |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Attribute selectors over Angular class bindings for section color | CSS owns visual state; TypeScript owns data state. Mixing them by computing class names in TS would scatter color logic across files. | Slightly less discoverable for developers unfamiliar with attribute selectors; mitigated by a clear comment block in `styles.css`. |
| `--section-accent` CSS custom property on the container, not the card | A single property declaration at the group level cascades to all child cards automatically. Adding a card to a group requires no additional color wiring. | Custom properties cascade through the shadow-less DOM unconditionally — no risk here, but would require care if shadow DOM were ever introduced. |
| No `padding-left` correction class — use direct value reduction | The 3px correction is a fixed offset from the border width, not a state-dependent value. A class would imply multiple states that don't exist. | If the border width ever changes, the padding correction must be updated in sync. Documented in the CSS comment. |
| Grid card and column card padding as base + override, not two independent rules | Avoids duplication of the full padding declaration; makes the relationship between the two contexts explicit. | Requires understanding of cascade specificity to modify either rule correctly — acceptable given the one-file constraint. |
| Braindumps fallback string preserved | Zero-content cards must still communicate something. Removing the fallback entirely would leave cards blank, which is worse than the current state. | Fallback is indistinguishable from a project that has `braindump.md` content of only headings. Acceptable edge case. |
| CSS-only scope for animation backport (5b, 5c, 5e) | All three animations are driven by existing template state and existing HTML structure. No new TS bindings are required, which keeps the backport risk-free and reviewable as a single-file diff. | If the active-state class names in the template ever change, the CSS rules silently stop working — no compile-time check. |
| Icon library evaluation excluded from this epic | The evaluation itself is research, not delivery. Shipping an unconsidered icon library dependency into a production Angular build carries higher risk than the visual benefit of this sprint warrants. | Op chip glyphs remain Unicode for this sprint. |

---

## Related Documents

- [Analysis](./analysis.md) — Problems driving design
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Delivery status and task progress tracking