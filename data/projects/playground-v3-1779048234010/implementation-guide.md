# Implementation Guide: Playground V3

## Overview
Playground V3 consolidates the Phase 1 live component demo and Phase 2 nine-section case study into a single guided scroll experience with five restaurant-themed sections — Greeting, Kitchen, Main Course, Presentation, and Send-Off. The work sequences linearly: Task 1 locks the section inventory and gating model decisions, Task 2 builds the scroll shell container with IntersectionObserver-based gating, Tasks 3 and 4 run in parallel to populate section content and embed the live app demo respectively, and Task 5 defines the extraction boundary so the landing page can consume playground components.

## Shared Pre-flight
- Confirm the design system is locked — no new tokens, palette changes, or type additions are in scope
- Verify all existing Phase 1 playground components are functional: `pg-tokens`, `pg-borders`, `pg-animations`, `pg-state-matrix`, `pg-components-app`, `pg-components-ui`
- Verify `playground-demo-data.ts` exists and contains the current hardcoded demo project fixtures
- Confirm app-v3-state-extraction work is complete and the V2 app components (`project-grid`, `sidebar-v2`, `reader-panel`, `section-nav`, `status-bar`) render correctly with service-provided data
- Confirm Angular 17 standalone component patterns and signal-based state are used consistently across the existing codebase
- Review `styles.css` for the existing global token classes (type scale, ink-on-cream palette, newspaper borders, grid utilities) that V3 sections will compose
- Review `app.routes.ts` to understand the current `/playground` route binding to `live-playground.component.ts`
- Verify the build succeeds with `ng build --configuration production` before starting any work

---

## Task 1: Section Inventory & Gating Model  [Effort: 1 day]

### What
Resolve all six open questions from the analysis: define the five sections (what merges and what is cut from Phase 2's nine), choose scroll-reveal with IntersectionObserver as the gating mechanism, decide that demonstration replaces annotation, confirm the section nav renders only inside the live app demo, and scope the dark-mode toggle to Section 3 only. This task produces no code but locks every design decision that Tasks 2–5 depend on.

### Files
- **Create**: `pg-scroll-shell.component.ts` — stub file containing the section inventory as a typed constant array (section names, gating conditions, ordering) and the `SectionState` type alias (`'locked' | 'revealing' | 'unlocked'`)
- **Modify**: `playground-demo-data.ts` — add TypeScript interfaces for the extended demo data shapes needed by each section (section taxonomy, generation status, markdown content)

### Steps
1. Document the five-section inventory by mapping each V3 section to its Phase 2 sources: Greeting absorbs the hero section, Kitchen absorbs pipeline and user journey, Main Course absorbs live app demo and screen gallery, Presentation absorbs design language, patterns, and dark mode, and Send-Off is new.
2. Record what is cut: the landing showcase section is deferred to the landing page epic, before/after transformation is redundant with the live demo, screen annotations are replaced by the live app itself, and the component-by-component catalog is replaced by composed vignettes.
3. Define the gating mechanism as IntersectionObserver-based scroll-reveal with sentinel divs at section boundaries — threshold 0.6 on desktop and 0.4 on viewports below 768px.
4. Specify locked section behavior: full-height container, content at opacity zero with pointer-events none, a faint newspaper rule at the boundary, and a single-line uppercase label teaser.
5. Specify reveal transition: CSS-only fade-in with a 24px upward shift over 400ms on desktop, opacity-only on mobile.
6. Confirm the dark-mode toggle is scoped to Section 3 and does not propagate to the scroll shell or other sections.
7. Confirm the section-nav component renders inside Section 3 as part of the embedded app demo, not as scroll-level navigation.
8. Create the stub `pg-scroll-shell.component.ts` with the section inventory constant and the `SectionState` type so downstream tasks can import them.
9. Add the extended demo data interfaces to `playground-demo-data.ts` covering section taxonomy entries, generation status shape, and markdown content fixtures.

### Verify
- The stub `pg-scroll-shell.component.ts` file exists and exports a typed section inventory array with exactly five entries and the `SectionState` type
- `playground-demo-data.ts` compiles with the new interfaces and no existing exports are broken
- `ng build --configuration production` succeeds with no errors

---

## Task 2: Scroll Shell with Gated Transitions  [Effort: 2 days]

### What
Build the single-scroll container component that hosts five section slots, manages the gating state machine via Angular signals, and drives section reveals through a single IntersectionObserver instance watching sentinel elements. This task delivers a working scroll shell that transitions empty placeholder sections through locked, revealing, and unlocked states on both desktop and mobile.

### Files
- **Create**: `pg-scroll-shell.component.html` — template with five section slots, sentinel divs at each boundary, and locked-state teaser lines
- **Modify**: `pg-scroll-shell.component.ts` — expand the stub from Task 1 into the full standalone component with the signal-based gating state machine, IntersectionObserver lifecycle, and mobile threshold adaptation
- **Modify**: `styles.css` — add utility classes for scroll-reveal transitions (opacity, transform), sentinel element positioning, locked-section styling, and section boundary newspaper rules
- **Modify**: `app.routes.ts` — change the `/playground` route to lazy-load `pg-scroll-shell.component.ts` instead of `live-playground.component.ts`

### Steps
1. Implement the gating state machine in `pg-scroll-shell.component.ts` as a `Signal<SectionState[]>` initialized with Section 1 unlocked and Sections 2–5 locked. Transitions are unidirectional: locked to revealing to unlocked. No persistence across sessions.
2. Set up a single `IntersectionObserver` in the component's `afterViewInit` lifecycle hook, observing sentinel elements placed at each section boundary in the template. Use a threshold of 0.6 on desktop and 0.4 on viewports below 768px, determined by a media query check at initialization.
3. Write the intersection callback logic: when a sentinel becomes visible and the current section's gating condition is met, transition the next section from locked to revealing. After the 400ms CSS transition completes, transition it to unlocked.
4. Build the template in `pg-scroll-shell.component.html` with a full-viewport container, max-width 1400px centered content area, five section slots rendered as host elements for the section components, and an invisible sentinel div between each pair of sections.
5. Add the locked-section presentation: each locked section renders at full height with content hidden via the reveal transition classes, a faint newspaper rule at the top boundary, and a single-line uppercase teaser label.
6. Add CSS classes to `styles.css` for the three states — locked (opacity zero, pointer-events none), revealing (opacity and transform transition over 400ms), and unlocked (opacity one, pointer-events auto) — plus a mobile variant that omits the transform to avoid layout recalculation.
7. Update `app.routes.ts` to point the `/playground` route at `PgScrollShellComponent` imported from `pg-scroll-shell.component.ts`.
8. Add the subtle scroll-down affordance at the bottom of the viewport — a gentle opacity shift on the bottom border — controlled by a CSS transition triggered when Section 1 is in view.
9. Clean up the IntersectionObserver in the component's `onDestroy` lifecycle hook by calling `disconnect()`.

### Verify
- Navigating to `/playground` renders the scroll shell with five visible section boundaries and teaser labels for Sections 2–5
- Scrolling down past Section 1's sentinel causes Section 2 to fade in with the reveal animation on desktop
- On a viewport below 768px (use browser dev tools), the reveal animation is opacity-only with no transform shift
- `ng build --configuration production` succeeds and the route loads the new scroll shell component

---

## Task 3: Section Content Composition  [Effort: 3 days]

### What
Populate each of the five sections with components that exercise the full design-pattern vocabulary — type scale, newspaper grid, ink-on-cream palette, borders, and quiet interactions. This task reuses Phase 1 live components and Phase 2 case-study pieces where they fit, recomposing them into the restaurant-metaphor narrative rather than presenting them as a reference catalog.

### Files
- **Create**: `pg-section-greeting.component.ts` — Section 1 standalone component with masthead headline, body text, and scroll-down affordance
- **Create**: `pg-section-kitchen.component.ts` — Section 2 standalone component with pipeline visualization showing the four spec-doc stages
- **Create**: `pg-section-patterns.component.ts` — Section 4 standalone component recomposing `pg-tokens`, `pg-borders`, and `pg-animations` into editorial vignettes
- **Create**: `pg-section-sendoff.component.ts` — Section 5 standalone component with CTA headline, accent color button, and extraction-boundary-ready input API
- **Modify**: `pg-scroll-shell.component.html` — replace placeholder section slots with the four new section components (Section 3 is handled in Task 4)
- **Modify**: `pg-scroll-shell.component.ts` — import the four section components and wire their input signals
- **Modify**: `playground-demo-data.ts` — add fixture data for the pipeline stage thumbnails and markdown content used by Section 2
- **Modify**: `styles.css` — add layout classes for the pipeline horizontal-to-vertical responsive grid and the editorial vignette compositions

### Steps
1. Build `pg-section-greeting.component.ts` as a standalone component rendering a masthead headline at 56–64px Playfair 700, a single sentence of body text at 15–17px Source Serif, generous whitespace, and a thin newspaper rule at the bottom. Add the scroll-down affordance as a subtle opacity shift on the bottom border.
2. Build `pg-section-kitchen.component.ts` as a standalone component presenting the spec-doc pipeline as four stages (braindump, analysis, epic, architecture) in a horizontal sequence on the 12-col grid for desktop and a vertical stacked layout on mobile. Use mid-range type scale for stage titles (28–36px) and label typography (11–12px Source Sans, uppercase, tracked) for stage labels. Render thumbnail representations using markdown fixture data from `playground-demo-data.ts`.
3. Add the pipeline fixture data to `playground-demo-data.ts` — four entries with stage names, short descriptions, and representative markdown snippets for each document type.
4. Build `pg-section-patterns.component.ts` as a standalone component that imports and recomposes `pg-tokens`, `pg-borders`, and `pg-animations` into editorial newspaper-spread layouts. Instead of a reference grid, arrange them as composed vignettes where colors, typography, borders, and spacing work together in realistic layouts. Set the time-based gating condition: the section's sentinel requires three seconds of intersection on desktop and 1.5 seconds on mobile.
5. Build `pg-section-sendoff.component.ts` as a standalone component with a large headline reusing the masthead type scale, a single call-to-action element using the accent color (#567B95), and generous footer whitespace. Design all data to flow through input signals with zero dependencies on the scroll shell's gating state, proving the extraction pattern.
6. Update `pg-scroll-shell.component.html` to render the four section components in their respective slots, passing demo data and any required input signals.
7. Import all four section components in `pg-scroll-shell.component.ts` and add them to the component's imports array.
8. Add responsive grid classes to `styles.css` for the pipeline layout (horizontal 4-across on desktop, vertical stack on mobile below 768px) and the editorial vignette compositions in Section 4.

### Verify
- All five section boundaries are visible in the scroll, with Sections 1, 2, 4, and 5 rendering their content (Section 3 remains a placeholder until Task 4)
- Section 1 displays the masthead headline in Playfair 700 and body text in Source Serif against the ink-on-cream palette
- Section 2's pipeline visualization switches from horizontal to vertical layout when the viewport is resized below 768px
- `ng build --configuration production` succeeds with all four new section components compiled

---

## Task 4: Live App Demo Integration  [Effort: 1 day]

### What
Embed the real specview app — `project-grid`, `sidebar-v2`, `reader-panel`, `section-nav`, and `status-bar` — as Section 3 of the scroll, wired to demo data instead of the Flask API. This replaces static screenshots with a functioning app instance that exercises every design pattern simultaneously under real component load.

### Files
- **Create**: `pg-section-live-app.component.ts` — Section 3 standalone component that hosts the V2 app component tree with demo-mode wiring and the scoped dark-mode toggle
- **Modify**: `playground-demo-data.ts` — extend with fixture data for the full app component tree: project list for `project-grid`, section taxonomy for `section-nav`, generation status for `status-bar`, and markdown content for `reader-panel`
- **Modify**: `projects.service.ts` — add a demo-mode branch that checks the `DEMO_MODE` injection token and returns fixture data from `playground-demo-data.ts` instead of making HTTP calls
- **Modify**: `pg-scroll-shell.component.ts` — provide the `DEMO_MODE` injection token set to true and import the Section 3 component
- **Modify**: `pg-scroll-shell.component.html` — render the Section 3 component in its slot between the Kitchen and Presentation sections

### Steps
1. Create a `DEMO_MODE` InjectionToken of type `Signal<boolean>` and export it from `pg-scroll-shell.component.ts`. The scroll shell provides this token with a value of `signal(true)` in its component providers array.
2. Extend `playground-demo-data.ts` with the additional fixture shapes: a project list array matching the shape `project-grid` expects, a section taxonomy array for `section-nav`, a generation status object for `status-bar`, and at least one markdown document string for `reader-panel`.
3. Add a demo-mode check to `projects.service.ts`: inject the `DEMO_MODE` token as optional, and when its value is true, return the fixture project list from `playground-demo-data.ts` instead of calling the HTTP endpoint. Apply the same pattern to any other service methods that the embedded components call during rendering.
4. Build `pg-section-live-app.component.ts` as a standalone component that renders the V2 app component tree — `project-grid`, `sidebar-v2`, `reader-panel`, `section-nav`, and `status-bar` — in a layout matching the real app's grid structure. Include the dark-mode toggle as an interactive element within this section only, toggling a CSS class on the section host element rather than propagating to the scroll shell.
5. Update `pg-scroll-shell.component.html` to render `pg-section-live-app` in the Section 3 slot, between the Kitchen sentinel and the Presentation sentinel.
6. Import `PgSectionLiveAppComponent` in `pg-scroll-shell.component.ts` and add it to the imports array.
7. Verify that the dark-mode toggle within Section 3 affects only the embedded app components and does not change the scroll shell or other sections.

### Verify
- Section 3 renders the full V2 app component tree with demo data visible in the project grid, reader panel, and status bar
- No HTTP calls are made to the Flask API when the playground loads — confirm in the browser network tab
- The dark-mode toggle in Section 3 switches the embedded app components between light and dark themes without affecting Sections 1, 2, 4, or 5
- `ng build --configuration production` succeeds with no warnings about missing providers or injection tokens

---

## Task 5: Landing Page Component Extraction  [Effort: 1 day]

### What
Define the API boundaries for components the landing page will consume from the playground, then extract and export Section 5 (Send-Off) as the proof-of-concept standalone component that can render outside the scroll context. This task does not build the landing page — it proves the extraction pattern works.

### Files
- **Modify**: `pg-section-sendoff.component.ts` — verify all data flows through input signals with zero scroll-shell dependencies, then add a named export and document the input contract
- **Modify**: `pg-section-greeting.component.ts` — verify input-signal-only data flow and add a named export for landing page consumption
- **Modify**: `pg-section-patterns.component.ts` — verify input-signal-only data flow and add a named export, noting that this component imports `pg-tokens`, `pg-borders`, and `pg-animations` as transitive dependencies
- **Modify**: `pg-scroll-shell.component.ts` — confirm that no section component references the gating state machine or the scroll shell's internal signals
- **Modify**: `pg-section-live-app.component.ts` — document that this component requires the `DEMO_MODE` injection token and the full `playground-demo-data.ts` fixture as extraction prerequisites

### Steps
1. Audit `pg-section-sendoff.component.ts` to confirm it accepts all data via input signals, has no constructor-injected dependencies on the scroll shell, and does not reference the gating state machine. If any scroll-shell coupling exists, refactor it out by moving data flow to inputs.
2. Audit `pg-section-greeting.component.ts` and `pg-section-patterns.component.ts` with the same criteria — all data via inputs, no gating dependencies. Document any transitive component dependencies (such as Section 4's use of `pg-tokens`, `pg-borders`, and `pg-animations`).
3. Document `pg-section-live-app.component.ts` as extractable but heavyweight — it requires the `DEMO_MODE` injection token to be provided by the consumer and the full fixture data from `playground-demo-data.ts`.
4. Mark `pg-section-kitchen.component.ts` as non-extractable due to its tight coupling to scroll position within the narrative layout.
5. Ensure each extractable section component uses a named export (not a default export) so the landing page can import directly from the component file path without a barrel file.
6. Create a minimal test harness — a temporary route or a test component — that renders `pg-section-sendoff` outside the scroll shell by providing its inputs directly. Confirm it renders correctly in isolation.
7. Remove the temporary test harness after verification. The extraction boundary is defined by the component's input API, not by a test route.
8. Remove the old Phase 1 playground route binding if one exists at `/playground/v1` in `app.routes.ts`, and confirm that `live-playground.component.ts` and `pg-case-study.component.ts` are no longer reachable by any route.

### Verify
- `pg-section-sendoff.component.ts` renders correctly when instantiated outside the scroll shell with inputs provided directly
- No import cycle exists between any section component and `pg-scroll-shell.component.ts` — verify with `ng build --configuration production` producing no circular dependency warnings
- The old `/playground/v1` route (if it existed) returns a 404 and `live-playground.component.ts` is not referenced in `app.routes.ts`
- `ng build --configuration production` succeeds with all section components exporting named symbols