# Implementation Guide: Playground Phase 2 — Missing Sections

## Overview
This epic ports the 12 remaining component demos from the old static playground into the live Angular playground at `/playground`, then retires the static file so there is a single source of truth for the spec-doc design system. Work is organized into five tasks: two independent child components for app-level and landing-page demos (Tasks 1 and 2, parallelizable), an interaction-state demo component that depends on Task 1, a lightweight extension to the existing state matrix, and a final integration pass that wires everything together and deletes the old static playground. All new components are Angular 17 standalone components using the established child-component pattern from Phase 1.

## Shared Pre-flight
- Confirm `ng build --configuration production` passes on the current main branch before starting any work
- Verify the existing Phase 1 child components render correctly at `/playground` — pg-tokens, pg-borders, pg-animations, pg-state-matrix
- Review `web-ng/public/assets/playground.html` and identify all 12 demo sections to be ported: masthead, op chips, modal, update banner, context cards, search bar, overline/badges, buttons, pull quote, step section, interaction states table, and comparison tables
- Confirm `web-ng/src/styles.css` contains the CSS classes referenced by the eight app-level demos (masthead, op-chip, modal, update-banner, context-card, search-bar, overline, btn-primary/secondary)
- Confirm `landing/style.css` contains the pull quote and step section rules that will be extracted into pg-landing
- Ensure the live-playground parent component at `web-ng/src/app/live-playground/live-playground.component.ts` is ready to accept new child component imports
- Review the existing pg-state-matrix template at `web-ng/src/app/pg-state-matrix/pg-state-matrix.component.html` and count remaining line budget (must have room for approximately 45 additional lines)

---

## Task 1: App Component Demos  [Effort: 1.5 days]

### What
Build the `pg-components` standalone child component that renders static visual demos for all eight app-level elements — masthead, op chips, modal, update banner, context cards, search bar, overline/badges, and all button variants. These elements all rely on the global `styles.css` already loaded by Angular, so no CSS isolation is needed.

### Files
- **Create**: `web-ng/src/app/pg-components/pg-components.component.ts` — minimal standalone component class with no inputs, outputs, or injected services
- **Create**: `web-ng/src/app/pg-components/pg-components.component.html` — template containing eight demo sections with semantic HTML using existing CSS classes from the global stylesheet
- **Create**: `web-ng/src/app/pg-components/pg-components.component.scss` — demo-specific layout only (grid spacing between demo blocks, section header styling); actual component appearance comes from global styles

### Steps
1. Scaffold the component directory at `web-ng/src/app/pg-components/` and create the three files (ts, html, scss). The TypeScript file declares a standalone component with selector `app-pg-components`, templateUrl, and styleUrl — no other logic.
2. Build the masthead demo section in the template using the existing `.masthead`, `.edition-label`, `.masthead-date`, `.masthead-title`, and `.masthead-tagline` classes. Populate with representative static text (edition number, date, title, tagline) matching the old playground's content.
3. Build the op chips demo section rendering all eight chip variants. Use an `@for` loop over a typed array defined in the component class to avoid repeating chip markup eight times. Include both default and `.active` / accent state variants for each chip.
4. Build the modal demo section, rendering the modal markup inline with `position: static` override in the component SCSS so it appears in document flow rather than as an overlay. Include all form fields visible in the old static playground version.
5. Build the update banner demo section using the existing `.update-banner` class and representative content.
6. Build the context cards demo section rendering two or three cards using the `.context-card` class with sample content.
7. Build the search bar demo section using the existing `.search-bar` class and its child elements.
8. Build the overline and badges demo section using the existing `.overline` and badge-related classes.
9. Build the buttons demo section as a single row showing every variant — primary, secondary, new-project, logout, upgrade, and icon buttons — plus a disabled state for each. Use an `@for` loop if the variant list exceeds six items to stay within line budget.
10. Verify the template stays under 200 lines. If it exceeds the budget, convert any remaining hand-repeated markup into `@for` loops over typed arrays in the component class.

### Verify
- All eight demo sections (masthead, op chips, modal, update banner, context cards, search bar, overline/badges, buttons) render visually in the browser when the component is temporarily added to the playground
- The masthead shows full newspaper chrome: edition label, date, title, and tagline
- All eight op chip variants display with active and accent state variants visible
- Every file in `web-ng/src/app/pg-components/` is under 200 lines (check with `wc -l web-ng/src/app/pg-components/*`)

---

## Task 2: Landing Page Demos  [Effort: 0.5 days]

### What
Build the `pg-landing` standalone child component that renders pull quote and step section demos using CSS extracted from `landing/style.css`. Angular's emulated view encapsulation scopes these styles to prevent collision with identically-named app-level classes like `.btn-primary`.

### Files
- **Create**: `web-ng/src/app/pg-landing/pg-landing.component.ts` — minimal standalone component class, no inputs/outputs/services
- **Create**: `web-ng/src/app/pg-landing/pg-landing.component.html` — template containing pull quote demo (single and row variants) and step section demo
- **Create**: `web-ng/src/app/pg-landing/pg-landing.component.scss` — contains the relevant CSS rules extracted from `landing/style.css` as a one-time snapshot (approximately 70 lines covering `.pullquote-*`, `.steps`, `.step`, `.step-num`, `.step-title`, `.step-body`, `.step-code` classes)

### Steps
1. Scaffold the component directory at `web-ng/src/app/pg-landing/` and create the three files. The TypeScript file declares a standalone component with selector `app-pg-landing`.
2. Open `landing/style.css` and identify the CSS rules for pull quote elements (`.pullquote-*` classes) and step section elements (`.steps`, `.step`, `.step-num`, `.step-title`, `.step-body`, `.step-code`). Copy only these relevant rules — approximately 70 lines — into `pg-landing.component.scss`.
3. Build the pull quote demo in the template using the extracted pullquote classes. Render both a single pull quote (with the oversized quotation mark) and a row-layout variant side by side to show both presentation modes.
4. Build the step section demo in the template using the extracted step classes. Render two or three steps with representative content (step number, title, body text, optional code reference).
5. Verify that Angular's emulated encapsulation properly scopes the landing CSS by confirming no style bleed into other playground sections.

### Verify
- Pull quote renders with the oversized quotation mark in both single and row variants
- Step section renders with numbered steps, titles, and body text matching the old static playground
- `ng build --configuration production` passes with no CSS-related warnings or errors
- Confirm no style leakage by inspecting other playground sections (especially app-level buttons) — they must be unaffected by the landing `.btn-primary` rules in this component

---

## Task 3: Interaction State Demos  [Effort: 1 day]

### What
Build the `pg-interactions` standalone child component that shows default versus hover/active/focus states side-by-side for all interactive elements. Instead of inline styles, this uses forced-state CSS classes (e.g., `.force-hover`) that duplicate hover rules as regular class selectors, maintaining the project's no-inline-styles convention.

### Files
- **Create**: `web-ng/src/app/pg-interactions/pg-interactions.component.ts` — minimal standalone component class
- **Create**: `web-ng/src/app/pg-interactions/pg-interactions.component.html` — two-column comparison table layout with default state on the left and forced state on the right for each interactive element
- **Create**: `web-ng/src/app/pg-interactions/pg-interactions.component.scss` — forced-state class definitions (`.force-hover`, `.force-focus`, `.force-active`) that replicate pseudo-class rules from `web-ng/src/styles.css`, approximately 120–150 lines

### Steps
1. Scaffold the component directory at `web-ng/src/app/pg-interactions/` and create the three files. The TypeScript file declares a standalone component with selector `app-pg-interactions`.
2. Audit `web-ng/src/styles.css` for every `:hover`, `:focus`, and `:active` rule on interactive elements. Create a list of all elements that need forced-state classes — this should include op chips, buttons (all variants), context cards, search bar, navigation links, and any other interactive elements from the inventory.
3. In `pg-interactions.component.scss`, define companion classes for each interactive element's pseudo-states. For example, define `.op-chip.force-hover` containing the same declarations as `.op-chip:hover` from the global stylesheet. Repeat for `.force-focus` and `.force-active` where those states exist.
4. Build the template as a two-column comparison table. Each row contains a section header identifying the element, the element in its default state in the left column, and the identical element with the appropriate `.force-hover` (or `.force-focus` / `.force-active`) class applied in the right column.
5. Monitor the SCSS file line count as forced-state classes are added. If the file exceeds 180 lines, split the component into two sub-components along the natural domain boundary: `pg-interactions-nav` for navigation elements and `pg-interactions-actions` for action elements (buttons, chips, cards).
6. Verify the visual output matches what a user would see when actually hovering over each element in the real application.

### Verify
- Every interactive element from the inventory appears in the comparison table with both default and hover/active/focus states visible simultaneously
- Forced-state rendering visually matches the real hover appearance (compare by hovering the default-state column element and visually comparing to the forced-state column)
- All files in `web-ng/src/app/pg-interactions/` are under 200 lines (check with `wc -l web-ng/src/app/pg-interactions/*`)
- No forced-state classes leak outside the component boundary — verify other playground sections are unaffected

---

## Task 4: State Matrix Extension  [Effort: 0.5 days]

### What
Add two reference tables to the existing `pg-state-matrix` component: an App vs. Landing comparison table documenting layout pattern differences between the two CSS domains, and a ClawBoi vs. Specview heritage table documenting design lineage. These are documentation tables, not component demos, and belong alongside the existing state matrix content.

### Files
- **Modify**: `web-ng/src/app/pg-state-matrix/pg-state-matrix.component.html` — append approximately 45 lines of table markup for the two new comparison tables after the existing state matrix content

### Steps
1. Open `web-ng/src/app/pg-state-matrix/pg-state-matrix.component.html` and count the current line total to confirm headroom for approximately 45 additional lines within the 200-line budget.
2. Add the App vs. Landing comparison table after the existing state matrix table. This table should have columns for the property being compared (typography, button styling, layout model, color palette, spacing conventions) and the corresponding approach in each CSS domain.
3. Add the ClawBoi vs. Specview heritage table below the App vs. Landing table. This table documents which visual elements descend from the ClawBoi design system versus the Specview design system, with columns for element name, heritage source, and any relevant notes about adaptation.
4. Ensure both tables use the same markup patterns and CSS classes as the existing state matrix table for visual consistency.

### Verify
- Both new tables render in the state matrix section of the playground with correct column alignment and readable content
- The App vs. Landing table accurately reflects the differences documented in the architecture (separate CSS files, class name collisions, encapsulation strategy)
- `wc -l web-ng/src/app/pg-state-matrix/pg-state-matrix.component.html` confirms the file remains under 200 lines
- Existing state matrix content above the new tables is visually unchanged

---

## Task 5: Integration & Old Playground Retirement  [Effort: 0.5 days]

### What
Wire all three new child components into the live playground parent, verify that every section from the old static playground has a live equivalent with zero gaps, confirm the production build passes, and delete the old static playground file to make `/playground` the single source of truth.

### Files
- **Modify**: `web-ng/src/app/live-playground/live-playground.component.ts` — add imports for PgComponentsComponent, PgLandingComponent, and PgInteractionsComponent to the standalone component's imports array
- **Modify**: `web-ng/src/app/live-playground/live-playground.component.html` — add the three new component selectors (`app-pg-components`, `app-pg-landing`, `app-pg-interactions`) in the correct section order: app components first, landing second, interaction states third
- **Delete**: `web-ng/public/assets/playground.html` — the old 2,304-line static playground file, removed only after full verification
- **Delete**: `web-ng/src/app/design-playground/design-playground.component.ts` — the old static playground loader component

### Steps
1. Open `web-ng/src/app/live-playground/live-playground.component.ts` and add the three new components to the imports array: PgComponentsComponent, PgLandingComponent, and PgInteractionsComponent.
2. Open `web-ng/src/app/live-playground/live-playground.component.html` and add the component selectors in order. Place `app-pg-components` after the existing Phase 1 sections, followed by `app-pg-landing`, then `app-pg-interactions`. The state matrix extension from Task 4 is already in its existing position within `app-pg-state-matrix`.
3. Run `ng serve` and visually inspect every section of the playground in the browser. Walk through all 12 demo items from the verified inventory and confirm each one renders correctly: masthead with full newspaper chrome, all eight op chips with variants, inline modal with form fields, update banner, context cards, search bar, overline/badges, all button variants with disabled states, pull quote in both layouts, step section, interaction states table, and both comparison tables in the state matrix.
4. Cross-reference the old static playground at `web-ng/public/assets/playground.html` section by section against the live playground to confirm zero missing demos. Document any gaps and resolve them before proceeding.
5. Run `ng build --configuration production` and confirm zero errors and zero regressions in existing Phase 1 sections.
6. After all verification passes, delete `web-ng/public/assets/playground.html` and `web-ng/src/app/design-playground/design-playground.component.ts`. Remove any route definitions or references that pointed to the old static playground.
7. Run `ng build --configuration production` one final time to confirm the build still passes after deletion of the old files.

### Verify
- All 12 items from the verified inventory render correctly at `/playground` in a single scrollable page
- `ng build --configuration production` passes with zero errors after all changes including old file deletion
- The old static playground file `web-ng/public/assets/playground.html` no longer exists on disk
- No route or import in the codebase references `design-playground` or the old static playground path (verify with a project-wide search for "design-playground" and "playground.html")
---

## Implementation Notes

1. **Flat file paths.** All files at `web-ng/src/app/` level per CLAUDE.md. NOT in subdirectories. Files: `pg-components.component.ts`, `pg-landing.component.ts`, `pg-interactions.component.ts` — all flat.
2. **Static playground already deleted.** Phase 1 Task 4 already deleted `design-playground.component.ts`, `playground.html`, `landing-style.css`. Task 5 is verify-only, not delete.
3. **Source of 12 demos:** The old static playground HTML (`landing/playground.html`, 2,304 lines) still exists in the **landing container** and in git history. Use it as the visual reference for porting demos. The deleted files were copies in the web-ng build.
4. **pg-components will exceed 200 lines.** Split into `pg-components-app.component` (masthead, modal, search, banner, context cards) and `pg-components-ui.component` (op chips, buttons, overlines/badges).
5. **live-playground.component.ts is at** `web-ng/src/app/live-playground.component.ts` (flat), not in a subdirectory.
