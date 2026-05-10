# Implementation Guide: App UI Mockups

## Overview
This epic delivers a complete CSS promotion pipeline that transfers validated design decisions from the static HTML mockup (`landing/app-overview.html`) into the shared design system (`landing/style.css`), resolving naming conflicts, open design questions, and font dependencies so the Angular implementation epic can consume stable, conflict-free class names and layout rules. Tasks sequence as: resolve ambiguity and naming (Tasks 1, 2, 5 in parallel), promote validated CSS (Task 3), then design the hero grid fallback (Task 4).

## Shared Pre-flight
- Confirm `landing/app-overview.html` renders correctly at 1400px viewport in a browser before any changes begin — this is the visual baseline for regression checks
- Confirm `landing/style.css` exists and is linked from both `landing/app-overview.html` and referenced by `web-ng/src/styles.css`
- Confirm the landing container nginx serves on port 8096 via Docker Compose
- Open `landing/app-overview.html` inline `<style>` block and inventory all app-specific rules (expect approximately 30 rules across six groups)
- Verify `web-ng/index.html` currently loads Playfair Display and Source Sans 3 from Google Fonts but not Source Serif 4
- Confirm `.gen-status-bar` class with `--active` and `--idle` modifiers already exists in `landing/style.css`
- Keep a second browser tab open on the mockup for side-by-side regression comparison after each promotion batch

---

## Task 1: Resolve Open Design Questions  [Effort: 0.5 days]

### What
Document binding decisions for the five unresolved design questions (nav icons, status bar idle state, hero card progress placement, badge data source, canonical port) so that downstream CSS promotion has unambiguous rules to work with.

### Files
- **Modify**: `landing/app-overview.html` — remove the unused Variant B inline SVG nav markup, leaving only text-only nav labels; update any port references to 8096
- **Create**: `docs/design-decisions.md` — record each of the five decisions with rationale in a single reference document for the Angular implementation epic

### Steps
1. ✅ ALREADY DONE — Nav is text-only (no Variant B SVG ever shipped in current mock). Verify no inline SVG elements exist in the nav section.
2. ✅ ALREADY DONE — Status bar uses playground 5.7 colors with 4 states (idle/active/success/failure). Verify idle state shows dark green background, not hidden.
3. ✅ ALREADY DONE — No in-card progress bar. Verify hero card markup has no progress element.
4. ✅ ALREADY DONE — Badges use state colors: `.badge--new` (red), `.badge--complete` (green), `.badge--ready` (accent blue), neutral grey for counts. Verify in markup.
5. Verify port references: 8097 is local dev server, 8096 is Docker landing container. Both are valid for their contexts.
6. Design decisions are documented in `architecture.md` Design Decisions table and `braindump.md` Final Mock Summary. No separate file needed.

### Verify
- Nav section contains text-only labels, no inline SVGs
- Status bar visible in idle state with dark green background
- No progress bar inside hero cards
- Badge colors match state philosophy (red/green/blue/grey)

---

## Task 2: Reconcile Status Strip/Bar Naming  [Effort: 0.5 days]

### What
Collapse the overlapping "action status strip" and "status bar" terminology into a single canonical element named "generation status bar" with class prefix `.gen-status-bar`, eliminating naming ambiguity before CSS promotion begins.

### Files
- **Modify**: `landing/app-overview.html` — rename all `.action-status-strip` class references to `.gen-status-bar` in both markup and inline styles
- **Modify**: `landing/style.css` — verify `.gen-status-bar` base rule exists with `--active` and `--idle` modifiers; remove any orphaned `.action-status-strip` rules if present

### Steps
1. Search `landing/app-overview.html` for every occurrence of `action-status-strip` in class attributes and replace with `gen-status-bar`.
2. Search the inline `<style>` block of `landing/app-overview.html` for any rule targeting `.action-status-strip` and rename the selector to `.gen-status-bar`.
3. Open `landing/style.css` and confirm the `.gen-status-bar` rule already exists with modifiers for `--active` and `--idle` states. If an `.action-status-strip` rule also exists in this file, merge any unique properties into the `.gen-status-bar` rule and delete the old selector.
4. Verify the element placement in the mockup markup: it must appear below the nav bar, above the search bar, with full viewport width and a 32px minimum height.
5. Refresh the mockup in browser and confirm the status bar renders identically after the rename — dark green idle state, same vertical position, no layout shift.

### Verify
- Zero occurrences of the string `action-status-strip` remain in `landing/app-overview.html`
- Zero occurrences of the string `action-status-strip` remain in `landing/style.css`
- The `.gen-status-bar` element renders below the nav and above the search bar at 32px minimum height
- Browser refresh shows no visual difference from baseline

---

## Task 3: Promote Validated CSS to style.css  [Effort: 1 day]

### What
Move all approximately 30 app-specific CSS rules from the inline `<style>` block in `landing/app-overview.html` into `landing/style.css`, promoted in six independent batches with visual regression verification between each batch.

### Files
- **Modify**: `landing/style.css` — append promoted rules organized into six clearly commented sections (header family, status bar, section group, data-section selectors, hero grid, animations)
- **Modify**: `landing/app-overview.html` — remove each batch of rules from the inline `<style>` block as they are promoted; the inline block should be empty or removed entirely when complete

### Steps
1. Promote Batch 1 — Header Family: cut the `.app-header`, `.app-header__title`, `.app-header__nav`, and any `.app-header__nav-item` rules from the inline block and append them to `landing/style.css`. Refresh browser and confirm header renders identically.
2. Promote Batch 2 — Status Bar: cut the `.gen-status-bar` rules (base, `--active`, `--idle`, `--success`, `--failure` modifiers) from the inline block into `landing/style.css`. If the external file already has a `.gen-status-bar` base rule, merge properties rather than duplicating selectors. Refresh and verify.
3. Promote Batch 3 — Section Group Family: cut `.section-group`, `.section-group__header`, `.section-group__title`, `.section-group__cards` rules from inline into `landing/style.css`. Refresh and verify.
4. Promote Batch 4 — Data-Section Attribute Selectors: cut all `[data-section="active"]`, `[data-section="specced"]`, `[data-section="braindumps"]`, `[data-section="ready"]`, `[data-section="archive"]` rules that set `--section-accent` custom properties. Append to `landing/style.css`. Refresh and verify section header colors remain correct.
5. Promote Batch 5 — Hero Grid Family: cut `.hero-grid`, `.hero-main`, `.hero-secondary`, `.hero-grid--single`, `.hero-grid--empty` rules into `landing/style.css`. Refresh and verify the hero layout at 1400px.
6. Promote Batch 6 — Animations and Utilities: cut all `@keyframes` declarations (expect approximately 7) and any hover bleed or badge utility classes from inline into `landing/style.css`. Refresh and verify hover effects and badge colors.
7. Confirm the inline `<style>` block in `landing/app-overview.html` is now empty. Remove the empty `<style></style>` tags entirely from the markup.

### Verify
- `landing/app-overview.html` contains no `<style>` block or contains only an empty one that has been removed
- `landing/style.css` contains rules for all six promotion batches (header, status bar, section group, data-section, hero grid, animations)
- The mockup at 1400px viewport renders identically to the pre-promotion baseline
- No CSS specificity conflicts visible (check that section accent colors, hover states, and badge colors all display correctly)

---

## Task 4: Design Hero Grid Fallback for 0–1 Items  [Effort: 0.5 days]

### What
Define CSS-level fallback behavior for the `2fr 1fr 1fr` hero grid when the Active section contains fewer than two projects, providing the layout rules that the Angular template's conditional class logic will consume.

### Files
- **Modify**: `landing/style.css` — add `.hero-grid--single` rule with `grid-column: 1 / -1` span and `.hero-grid--empty` rule with `display: none`
- **Modify**: `landing/app-overview.html` — add a test section or duplicate the hero grid markup to demonstrate both fallback states (single item and zero items) for visual verification

### Steps
1. Open `landing/style.css` and locate the `.hero-grid` rule promoted in Task 3. Below it, add a `.hero-grid--single` modifier rule that causes a single child element to span the full grid width using `grid-column: 1 / -1`.
2. Add a `.hero-grid--empty` modifier rule that hides the entire hero section via `display: none` when no items are present.
3. In `landing/app-overview.html`, temporarily modify the hero grid section to contain only one card item and apply the `.hero-grid--single` class to the grid container. Verify in browser that the single card fills the full hero width at 1400px viewport.
4. Temporarily remove all cards from the hero grid and apply `.hero-grid--empty` to the container. Verify the hero section disappears entirely with no empty space or visual artifact.
5. Restore the hero grid to its original 2–3 item state for the final mockup, removing temporary test modifications. The fallback classes remain in `landing/style.css` ready for Angular consumption.

### Verify
- `landing/style.css` contains both `.hero-grid--single` and `.hero-grid--empty` rules
- A single hero card with `.hero-grid--single` applied spans the full grid width at 1400px (test by temporarily modifying markup)
- The `.hero-grid--empty` rule completely hides the hero section with no residual whitespace
- The default hero grid with 2–3 items still renders as `2fr 1fr 1fr` with 24px gap

---

## Task 5: Add Source Serif 4 Font Dependency  [Effort: 0.5 days]

### What
Add Source Serif 4 to the Angular app's Google Fonts import so the serif teaser typography decision validated in the mockup renders identically when consumed by the Angular application.

### Files
- **Modify**: `web-ng/index.html` — append `Source+Serif+4:ital,wght@0,400;0,600;1,400` to the existing Google Fonts link tag URL
- **Modify**: `landing/app-overview.html` — verify the mockup's Google Fonts link already includes Source Serif 4 with the same weight and style variants

### Steps
1. Open `web-ng/index.html` and locate the Google Fonts `<link>` tag that currently loads Playfair Display and Source Sans 3.
2. Append `Source+Serif+4:ital,wght@0,400;0,600;1,400` to the existing font family list in the URL, using the pipe or ampersand separator matching the existing URL format.
3. Open `landing/app-overview.html` and verify its Google Fonts link includes Source Serif 4 with at minimum the same three variants (regular 400, semibold 600, italic 400). If variants differ, align the mockup to match the Angular app's import.
4. Open the Angular app in a browser (or inspect the network tab) and confirm Source Serif 4 loads successfully from Google Fonts CDN without 404 errors.
5. Verify that any `.file-item-teaser` or serif-styled elements in the mockup use `font-family: 'Source Serif 4', serif` and that this declaration exists in `landing/style.css` (promoted during Task 3) rather than inline.

### Verify
- `web-ng/index.html` Google Fonts link includes `Source+Serif+4` with weights 400, 600, and italic 400
- `landing/app-overview.html` Google Fonts link includes the same Source Serif 4 variants
- Network tab shows successful font load with HTTP 200 for Source Serif 4 files
- Teaser text in the mockup renders in Source Serif 4 (visually distinct from Source Sans 3)