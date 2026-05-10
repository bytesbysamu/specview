# Implementation Guide: UX: App Grid Polish

## Overview

This epic delivers four targeted improvements to the project grid in `web-ng`: real prose teasers for Braindumps cards, semantic left-border color keyed by section state, increased card breathing room, and a CSS animation backport for generation shimmer, diff highlights, and count-pulse verification. Tasks 1 and 2 are fully independent and can be worked in parallel; Task 3 depends on Task 1 settling the base padding values before the border offset can be computed; Task 4 is independent of all others but should land after the `styles.css` changes from Tasks 1 and 3 are merged to avoid conflicts.

## Shared Pre-flight

- Confirm `web-ng/src/styles.css` exists and locate the `.file-item`, `.section-group-cards`, and `.file-column` rule blocks before editing.
- Confirm `web-ng/src/app/project-teaser.ts` exists and locate the `projectTeaser()` function and `firstNonHeadingSentence()` helper.
- Confirm `web-ng/src/app/app.component.html` exists and locate the grouped (all-sections) and single-section column view template blocks.
- Verify that the `Section` type string literals in `web-ng/src/app/section-taxonomy.service.ts` are `"Active"`, `"Specced"`, `"Braindumps"`, `"Ready to build"`, and `"Archive"` — these must match `data-section` attribute values exactly.
- Run `ng build --configuration production` from `web-ng/` and confirm it passes with zero errors before making any changes.
- Start the dev server (`ng serve`) and open the project grid in both light and dark mode to capture the baseline visual state.
- Confirm that CSS variables `--status-running`, `--accent`, and `--ink-muted` are defined in `styles.css` or an imported token file — do not introduce new palette values.
- Confirm that `.gen-status-track`, `.gen-status-bar--active`, `.section-count-pulse`, and `@keyframes count-pulse` exist (or are absent) in `web-ng/src/styles.css` before beginning Task 4.

---

## Task 1: Card Breathing Room  [Effort: 0.5 days]

### What

Increase card padding, grid minimum column width, and section group spacing so the project grid matches the ClawBoi reference density rather than feeling like a compressed file manager. This task establishes the base padding values that Task 3 depends on.

### Files

- **Modify**: `web-ng/src/styles.css` — raise `.file-item` base padding to `16px 12px`, update hover bleed to `0 -12px`, set grid card override to `margin: 0; padding: 16px`, widen `minmax` to `260px`, and increase section group gap to `32px`.

### Steps

1. Locate the `.file-item` base rule in `web-ng/src/styles.css` and change the `padding` value from its current setting to `16px 12px`.
2. Locate the hover bleed rule for `.file-item` (the negative-margin rule applied on hover in column view) and update it to `margin: 0 -12px` so it mirrors the new horizontal base padding.
3. Locate the grid card override block scoped to `.section-group-cards .file-item` and set it to `margin: 0; padding: 16px` flat, removing any inherited bleed values.
4. Locate the CSS grid `grid-template-columns` declaration for the section cards grid and change the `minmax` first argument from its current value to `260px`.
5. Locate the `gap` or `row-gap` property on `.section-group` (or the equivalent section group container) and increase it to `32px`.

### Verify

- Inspect a Braindumps card in column view: computed `padding` in DevTools reads `16px 12px` and the hover state shows a `0 -12px` margin bleed.
- Inspect a card in the grouped (all-sections) grid view: computed `padding` reads `16px` on all sides and `margin` is `0`.
- The grid does not collapse from three columns to two columns at the same viewport width as before — the wider `minmax` is observable by resizing the browser.
- `ng build --configuration production` passes with zero errors after the change.

---

## Task 2: Real Braindump Teasers  [Effort: 0.5 days]

### What

Wire `leadFileContent` through the Braindumps branch of `projectTeaser()` so Braindumps cards display the first real prose sentence from `braindump.md` instead of the same static string on every card. Cards whose `braindump.md` is empty or heading-only retain the fallback string `"Braindump — ready to generate"`.

### Files

- **Modify**: `web-ng/src/app/project-teaser.ts` — add a conditional guard in the Braindumps branch of `projectTeaser()` that calls `firstNonHeadingSentence(leadFileContent)` before returning the fallback string.

### Steps

1. Open `web-ng/src/app/project-teaser.ts` and read the `projectTeaser()` function to understand how the Specced and Ready-to-build branches already call `firstNonHeadingSentence(leadFileContent)`.
2. Locate the Braindumps branch inside `projectTeaser()` — it currently ignores `leadFileContent` and returns the hardcoded fallback string unconditionally.
3. Add a guard before the fallback return: call `firstNonHeadingSentence(leadFileContent)`, assign the result to a local variable, and return it only when it is a non-empty string.
4. Leave the fallback string `"Braindump — ready to generate"` in place as the else path so zero-content cards still display something meaningful.
5. Do not touch `app.component.ts` or the template — `teaserFor()` already passes `leadFileContent` for the Braindumps case; the fix is entirely internal to `projectTeaser()`.

### Verify

- Open two Braindumps projects whose `braindump.md` files contain distinct prose: their cards display different teaser text.
- Open a Braindumps project whose `braindump.md` is empty or contains only headings: its card displays `"Braindump — ready to generate"`.
- No other section's cards (Active, Specced, Ready-to-build) display changed teaser text.
- `ng build --configuration production` passes with zero errors after the change.

---

## Task 3: Semantic Section Color  [Effort: 1 day]

### What

Add a 3px left-border accent to every `.file-item` keyed by the section it belongs to — green for Active, blue for Specced, muted for Braindumps, transparent for Ready-to-build and Archive — and tint the section title for Active and Specced only. This task depends on Task 1 because the border introduces a `padding-left` correction whose exact value is derived from the settled base padding.

### Files

- **Modify**: `web-ng/src/app/app.component.html` — add `[attr.data-section]="group.section"` to the grouped view section container and `[attr.data-section]="activeSection()"` to the single-section column container.
- **Modify**: `web-ng/src/styles.css` — add `--section-accent` CSS custom property declarations keyed by `[data-section]` attribute selectors, apply `border-left: 3px solid var(--section-accent, transparent)` with corrected `padding-left` values on `.file-item` in both grid and column contexts, and tint `.section-group-title` for Active and Specced.

### Steps

1. Open `web-ng/src/app/app.component.html` and locate the element that wraps each section group in the grouped (all-sections) view — likely a div with class `.section-group` or similar — and add the Angular binding `[attr.data-section]="group.section"` to it.
2. Locate the element that wraps the card list in the single-section column view and add `[attr.data-section]="activeSection()"` to it, using whatever method or signal exposes the current section name.
3. Open `web-ng/src/styles.css` and add a block of attribute selector rules that set `--section-accent` on containers whose `data-section` matches `"Active"` (using `--status-running`), `"Specced"` (using `--accent`), and `"Braindumps"` (using `--ink-muted`); leave `"Ready to build"` and `"Archive"` with no declaration so they fall back to `transparent`.
4. Inside the `.section-group-cards .file-item` override block (the grid context established in Task 1), add `border-left: 3px solid var(--section-accent, transparent)` and set `padding-left: 13px` (16px grid base minus 3px border) so content does not shift.
5. Add a parallel rule for the column view context — scoped to `[data-section].file-column .file-item` — with the same `border-left` declaration and `padding-left: 9px` (12px column base minus 3px border).
6. Within the `[data-section="Active"]` and `[data-section="Specced"]` blocks, add a rule targeting `.section-group-title` that sets its `color` to `var(--section-accent)` so only those two titles receive a tint; do not add color rules for other section titles.
7. Open the app in the browser in both light and dark mode and confirm that color tokens resolve correctly via existing CSS variable definitions.

### Verify

- Active section cards show a green left border; Specced cards show a blue left border; Braindumps cards show a muted left border; Ready-to-build and Archive cards show no border — confirmed in both grouped and single-section views.
- Section title tint (green for Active, blue for Specced) appears only on those two sections; other titles are unstyled.
- Card content (text, icons) is horizontally aligned with the same column edge as before — no visible shift caused by border introduction — confirmed by comparing DevTools computed `padding-left` values against the expected `13px` (grid) and `9px` (column).
- Dark mode renders all borders and title tints without introducing any new palette values.
- `ng build --configuration production` passes with zero errors after the change.

---

## Task 4: CSS Animation Backport  [Effort: 0.5 days]

### What

Backport three animation patterns from the playground prototype into `styles.css`: a shimmer keyframe on `.gen-status-track` during active generation, highlight rules for `.diff-block-remove` and `.diff-block-add` in unified diff output, and verification or addition of the `@keyframes count-pulse` definition that the template already references via `section-count-pulse`. All changes are CSS-only.

### Files

- **Modify**: `web-ng/src/styles.css` — add `@keyframes gen-shimmer` and animate `.gen-status-track` when `.gen-status-bar--active` is present; add `.diff-block-remove` and `.diff-block-add` highlight rules; verify and if absent add `@keyframes count-pulse` tied to `.section-count-pulse`.

### Steps

1. Open `web-ng/src/styles.css` and search for the `.gen-status-track` rule; confirm it exists and note the current static background or color value applied when `.gen-status-bar--active` is on the element.
2. Add a `@keyframes gen-shimmer` definition in `styles.css` that animates a gradient sweep (using a background-position or background-size shift) to communicate "work in progress" visually; then replace or supplement the static `.gen-status-bar--active` track rule with an `animation` property referencing `gen-shimmer` at an appropriate duration and repeat.
3. Search `styles.css` for `.diff-block-remove` and `.diff-block-add` — if they are absent, add rule blocks for each: `.diff-block-remove` should apply a red-tinted background and a strikethrough text decoration; `.diff-block-add` should apply a green-tinted background; use existing color variables or `rgba` from existing tokens rather than new hex values.
4. Search `styles.css` for `@keyframes count-pulse` — if it is present, confirm that the keyframe name matches what the template class `section-count-pulse` triggers via an `animation-name` property in the `.section-count-pulse` rule; if it is absent, add a `@keyframes count-pulse` definition that scales or briefly highlights the element and wire it to `.section-count-pulse` via `animation`.
5. Verify in the browser that triggering active generation shows the shimmer animation on the status track, that a diff view renders removed lines with a red tint and added lines with a green tint, and that a section badge count change triggers the pulse.

### Verify

- The `.gen-status-track` element visually animates (gradient sweep or equivalent shimmer) when the generation active state class is present; it does not animate when idle.
- Diff output rendered by `diffHtmlUnified` shows `.diff-block-remove` lines with red-tinted strikethrough and `.diff-block-add` lines with green-tinted background in the browser.
- The `@keyframes count-pulse` definition exists in `styles.css` and its name matches the `animation-name` referenced by the `.section-count-pulse` rule — confirmed by searching the file.
- `ng build --configuration production` passes with zero errors after the change.