# Implementation Guide: Playground — Design System Extension

## Overview
This epic merges the live component playground at `/playground` with the design system documentation that currently lives in a stale 2,304-line static HTML file. Four sequential tasks decompose the monolithic playground template into five child components — covering design tokens, borders, animations, a component state matrix, and an interactive expanded panel — then delete 3,562 lines of dead static assets. Tasks execute in order: Task 1 establishes the child component pattern and pure-CSS sections, Task 2 builds the integration-heavy state matrix, Task 3 wires the interactive expanded panel using the real component with demo data, and Task 4 deletes the old static files after visual review.

## Shared Pre-flight
- Confirm `ng build --configuration production` passes cleanly on the current codebase before starting
- Verify the dark-mode toggle in `LivePlaygroundComponent` applies a CSS class to `document.documentElement` and that `getComputedStyle(document.documentElement).getPropertyValue('--ink')` returns a valid value
- Inventory all CSS custom properties in `styles.css` (color tokens like `--ink`, `--paper`, status colors, typography stacks) to build the token list for Section A
- Inventory all `@keyframes` definitions in `styles.css` to build the animation list for Section C
- Inventory all border utility classes (`.divider`, `.divider.thick`, section-group separators, card separators, expanded-panel top borders, sidebar right borders, column rules) for Section B
- Confirm every V2 standalone component (`StatusBarComponent`, project card components, `SidebarNavComponent`, `SectionNavComponent`, `ReaderPanelComponent`, `ExpandedPanelComponent`) can be imported independently without requiring parent-injected services
- Ensure the workspace enforces the 200-line file rule — no new file may exceed 200 lines
- Review the existing `live-playground.component.html` template to identify which inline sections will be extracted into child components

---

## Task 1: Child Component Scaffold + Sections A–C  [Effort: 2 days]

### What
Decompose the monolithic `live-playground.component.html` into child components and build Sections A (design tokens), B (border rules), and C (animation gallery) as standalone Angular components. This establishes the parent-children pattern used by all subsequent tasks, and delivers three pure-CSS documentation sections that auto-update on dark-mode toggle.

### Files
- **Create**: `web-ng/src/app/playground/css-read.util.ts` — single helper function wrapping `getComputedStyle(document.documentElement).getPropertyValue(name)` with a fallback for undefined variables
- **Create**: `web-ng/src/app/playground/pg-tokens.component.ts` — standalone component rendering live color swatches, typography specimens, and spacing scale from CSS custom properties, with MutationObserver for dark-mode reactivity
- **Create**: `web-ng/src/app/playground/pg-borders.component.ts` — standalone component rendering every border style as a labeled demo box with the real CSS class applied
- **Create**: `web-ng/src/app/playground/pg-animations.component.ts` — standalone component rendering all keyframe animations with replay controls
- **Modify**: `web-ng/src/app/playground/live-playground.component.ts` — import the three new child components and add them to the standalone imports array
- **Modify**: `web-ng/src/app/playground/live-playground.component.html` — replace inline sections for tokens, borders, and animations with `<pg-tokens>`, `<pg-borders>`, and `<pg-animations>` tags while preserving section anchors and the `.pg-section` / `.pg-label` visual pattern

### Steps
1. Create `css-read.util.ts` with a single exported function that accepts a CSS custom property name string and returns its computed value from the document root, returning the string "not set" when the value is empty or undefined.
2. Create `PgTokensComponent` as an Angular standalone component. Define a local array of token definitions containing the variable name, display label, and category (color, status, typography). On initialization, read each token's computed value using the helper from `css-read.util.ts`. Set up a `MutationObserver` on `document.documentElement` watching the class attribute so that when dark mode toggles, all token values are re-read and the swatches update. Render color tokens as small boxes with their background color bound to the computed value, alongside the variable name and hex string. Render typography specimens as text samples with font-family bound to the computed font-stack value. Render the spacing scale as visual box diagrams at hardcoded measurements (8px through 48px) documenting current conventions.
3. Create `PgBordersComponent` as an Angular standalone component. Define a local array of border definitions with label, CSS class, and description. The template iterates over this array, rendering each entry as a demo container element with the real CSS class applied. This component is mostly template with minimal TypeScript.
4. Create `PgAnimationsComponent` as an Angular standalone component. Define a local array of animation definitions with name, CSS class, duration string, and a boolean for whether the animation is infinite. Infinite animations display continuously with an "Always Running" label. Finite animations include a Replay button. Implement a single replay method on the component that accepts an element reference and class name, removes the animation class, forces a reflow by reading `offsetWidth`, then re-adds the class.
5. Open `live-playground.component.ts` and add imports for `PgTokensComponent`, `PgBordersComponent`, and `PgAnimationsComponent` to the component's standalone imports array.
6. Edit `live-playground.component.html` to replace the inline markup for the tokens, borders, and animations sections with the corresponding `<pg-tokens>`, `<pg-borders>`, and `<pg-animations>` child component tags. Keep the section anchor IDs and `.pg-section` / `.pg-label` wrappers intact around each child tag.
7. Verify every new file stays under 200 lines. If `PgTokensComponent` approaches the limit, move the token definitions array into a co-located constant at the top of the file rather than extracting a separate data file.

### Verify
- Toggle dark mode on the playground page and confirm that every color swatch in Section A updates its displayed hex value and background color instantly
- Confirm Section C's Replay buttons restart finite animations and that infinite animations display with an "Always Running" label
- Confirm each of the three new component files and the modified parent template are all under 200 lines
- Run `ng build --configuration production` and confirm zero new warnings or errors

---

## Task 2: Component State Matrix (Section D)  [Effort: 2 days]

### What
Build the state matrix as a new child component that imports every V2 component and renders each in every meaningful state side by side. This validates that all V2 components are importable standalone and creates a living visual integration reference that updates automatically when component rendering changes.

### Files
- **Create**: `web-ng/src/app/playground/pg-state-matrix.component.ts` — standalone component importing all V2 components and rendering them in a grid with mock inputs for every documented state
- **Modify**: `web-ng/src/app/playground/live-playground.component.ts` — add `PgStateMatrixComponent` to the standalone imports array
- **Modify**: `web-ng/src/app/playground/live-playground.component.html` — add a `<pg-state-matrix>` tag in a new section anchor block after the animations section

### Steps
1. Create `PgStateMatrixComponent` as an Angular standalone component. Import `StatusBarComponent`, the project card components, `SidebarNavComponent`, `SectionNavComponent`, and `ReaderPanelComponent` into the component's standalone imports array.
2. Define inline mock data as simple object literals in the component class for each V2 component's states. For example, define multiple status bar configurations (connected, disconnected, syncing), multiple project card variants (with and without descriptions, different status indicators), sidebar nav states (collapsed, expanded, with active item), section nav states (different section counts, active selections), and reader panel states (markdown content, empty state, loading state).
3. Build the template as a grid layout where each row corresponds to a V2 component type and each column corresponds to a state. Each cell contains the real component tag with input bindings set to the appropriate mock data object. Add a label above each cell identifying the state name.
4. If the template approaches 200 lines, refactor the mock data into configuration arrays and use `@for` loops to iterate over component-state pairs rather than writing individual template blocks for each cell.
5. Add `PgStateMatrixComponent` to the imports array in `live-playground.component.ts`.
6. Add a new section block in `live-playground.component.html` with an anchor ID and `.pg-section` wrapper containing the `<pg-state-matrix>` tag.
7. Visually inspect the rendered matrix to confirm every V2 component appears in every documented state. If any component fails to render standalone due to a missing injected service, wrap that component instance in a minimal host element that provides the required injection context.

### Verify
- Confirm the state matrix grid renders every V2 component (status bar, project cards, sidebar nav, section nav, reader panel) in every documented state without console errors
- Confirm that toggling dark mode updates the appearance of all components in the matrix consistently
- Confirm `pg-state-matrix.component.ts` stays under 200 lines
- Run `ng build --configuration production` and confirm zero new warnings or errors

---

## Task 3: Interactive Expanded Panel (Section E)  [Effort: 2 days]

### What
Wire a fully interactive expanded panel demo that reuses the real `ExpandedPanelComponent` with injected demo data. Clicking files in the sidebar changes reader content, the panel slide animation fires on enter, and the AI toolbar renders in its floating position. This proves the expanded panel works end-to-end and prevents documentation drift by coupling directly to the real component's input contract.

### Files
- **Modify**: `web-ng/src/app/playground/live-playground.component.ts` — add the expanded panel section logic, demo data constant, and event handlers for file navigation directly in the parent component (or in a new child if the parent exceeds 200 lines)
- **Modify**: `web-ng/src/app/playground/live-playground.component.html` — add the expanded panel demo section with the real `ExpandedPanelComponent` tag and input/output bindings
- **Create** (if needed): `web-ng/src/app/playground/pg-expanded-demo.component.ts` — standalone wrapper component for the expanded panel demo, created only if adding the demo inline to the parent would push it over 200 lines

### Steps
1. Define a demo project data constant containing a mock project with multiple files spanning different types: at least one spec file, one braindump file, and one AI result file. Each file entry should include a title, file-type label, and markdown content body. Include enough variety to exercise the word count meta line, overline file-type labels, and AI result toolbar with Apply/Copy/Dismiss actions.
2. Add a local state property tracking the currently selected file in the sidebar. Initialize it to the first file in the demo project.
3. Bind the real `ExpandedPanelComponent` in the template with the demo project data as its input. Bind the file selection output event to update the local selected-file state, which in turn updates the reader panel content through the component's normal input bindings.
4. Ensure the panel slide animation fires when the section scrolls into view or when the component initializes. Confirm the AI result toolbar appears in its floating position for AI-result-type files.
5. If adding this section to `LivePlaygroundComponent` directly would push its template or TypeScript over 200 lines, extract the demo into a new `PgExpandedDemoComponent` standalone component and reference it via a `<pg-expanded-demo>` tag in the parent template instead.
6. Add the section to `live-playground.component.html` with an anchor ID, `.pg-section` wrapper, and `.pg-label` heading consistent with the other sections.
7. Test the interactive flow end-to-end: click each file in the sidebar navigation and confirm the reader panel content updates, the correct file-type overline label displays, and the AI toolbar appears only for AI result files.

### Verify
- Confirm clicking files in the sidebar navigation changes the reader panel content without page reload or console errors
- Confirm the panel slide animation plays on component initialization
- Confirm the AI result toolbar (Apply/Copy/Dismiss) renders in floating position for AI-result-type files and does not appear for other file types
- Run `ng build --configuration production` and confirm zero new warnings or errors

---

## Task 4: Static Asset Deletion & Cleanup  [Effort: 0.5 days]

### What
Delete the old static playground files — the frozen `DesignPlaygroundComponent`, its 2,304-line HTML, and the orphaned 1,224-line CSS — and remove all references from the app shell. This is gated on visual review of Tasks 1–3 confirming that the live playground fully replaces the static documentation. Removes 3,562 lines of dead code that inflates the build and confuses navigation.

### Files
- **Delete**: `web-ng/src/app/playground/design-playground.component.ts` — the 34-line component class for the old static playground
- **Delete**: `web-ng/public/assets/playground.html` — the 2,304-line static HTML documentation file
- **Delete**: `web-ng/public/assets/landing-style.css` — the 1,224-line orphaned stylesheet
- **Modify**: `web-ng/src/app/app-v2.component.ts` — remove the import and any routing or component reference to `DesignPlaygroundComponent`
- **Modify**: `web-ng/src/app/app-v2.component.html` — remove any navigation link or component tag referencing the old design playground

### Steps
1. Perform a final visual review of the live playground at `/playground`, walking through every section (tokens, borders, animations, state matrix, expanded panel) and confirming each renders correctly in both light and dark modes. Do not proceed with deletion until this review passes.
2. Search the entire codebase for references to `DesignPlaygroundComponent`, `design-playground`, `playground.html`, and `landing-style.css` to build a complete list of files that import or reference these assets.
3. Delete `web-ng/src/app/playground/design-playground.component.ts`.
4. Delete `web-ng/public/assets/playground.html`.
5. Delete `web-ng/public/assets/landing-style.css`.
6. Open each file identified in step 2 and remove the import statements, route definitions, component references, and navigation links that pointed to the deleted files. This includes at minimum `app-v2.component.ts` and `app-v2.component.html`.
7. Run the full build and test suite to confirm no dangling references remain.

### Verify
- Confirm `design-playground.component.ts`, `web-ng/public/assets/playground.html`, and `web-ng/public/assets/landing-style.css` no longer exist in the workspace
- Run a codebase-wide search for `DesignPlayground`, `playground.html`, and `landing-style.css` and confirm zero results
- Run `ng build --configuration production` and confirm zero warnings or errors
- Run the full test suite and confirm no test regressions
---

## Implementation Notes

1. **Flat file paths.** All new files at `web-ng/src/app/` level per CLAUDE.md. NOT in a `playground/` subdirectory. Files: `pg-tokens.component.ts`, `pg-borders.component.ts`, `pg-animations.component.ts`, `pg-state-matrix.component.ts`, `css-read.util.ts`.
2. **Correct component names.** No `ExpandedPanelComponent` or `SidebarNavComponent` — these don't exist. Use: `SidebarV2Component`, `ReaderPanelComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SectionNavComponent`. The expanded panel is `<app-sidebar-v2>` + `<app-reader-panel>` inside a `div.expanded-panel`, not a standalone component.
3. **design-playground.component.ts** is at `web-ng/src/app/design-playground.component.ts` (flat), not in a subdirectory.
4. **Task 3:** Compose the expanded panel from `<app-sidebar-v2>` + `<app-reader-panel>` directly, same pattern as `app-v2.component.html`. Not a wrapper component.
