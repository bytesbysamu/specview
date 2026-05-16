# Implementation Guide: Live Component Playground

## Overview
This epic replaces a 2,304-line static HTML design playground with a live, interactive page that composes all six V2 sub-components using hardcoded demo data and Angular signals. Tasks sequence linearly: first verify that all sub-components have stable input/output contracts (Task 1), then author the demo data constants those components consume (Task 2), then build the orchestrating playground component and template (Task 3), then wire the Angular Router and retire the old static playground to a new route (Task 4), and finally layer on the dark mode toggle and display-only create modal (Task 5). Tasks 4 and 5 can run in parallel once Task 3 is complete.

## Shared Pre-flight
- Confirm Angular 17+ standalone component conventions are followed throughout the project — signals, computed properties, and `@if`/`@for` control flow in templates
- Verify `marked` and `DOMPurify` are listed in `web-ng/package.json` and importable; run `npm ls marked dompurify` to confirm versions
- Confirm that `Project`, `Spec`, `SpecSummary`, and `SpecDetail` TypeScript interfaces are exported from the existing types or models directory under `web-ng/src/app/`
- Verify that no Angular Router configuration exists yet — the app uses signal-based navigation, and this epic introduces routing for the first time
- Ensure all six sub-components are standalone (no `NgModule` wrappers) by checking each component's `@Component` decorator for the `standalone: true` flag
- Confirm that component SCSS files already define CSS custom properties scoped to `[data-theme="dark"]` for dark mode support
- Ensure the existing `DesignPlaygroundComponent` is importable and its current route or navigation entry is identified so it can be redirected
- Run `ng build --configuration production` to establish a clean baseline before any changes

---

## Task 1: Verify Sub-Component Input Contracts  [Effort: 0.5 days]

### What
Audit all six sub-components that the live playground will compose — `SectionNavComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, and `LandingPitchComponent` — to confirm each has stable, documented `@Input` and `@Output` signatures. This prevents Task 2 from authoring demo data against contracts that are missing, incomplete, or about to change.

### Files
- **Modify**: `web-ng/src/app/section-nav/section-nav.component.ts` — only if inputs or outputs are missing or undocumented; add missing type annotations
- **Modify**: `web-ng/src/app/status-bar/status-bar.component.ts` — confirm `mode` input accepts at least idle, active, success, and failure values
- **Modify**: `web-ng/src/app/project-grid/project-grid.component.ts` — confirm projects input type aligns with the `Project` interface
- **Modify**: `web-ng/src/app/sidebar-v2/sidebar-v2.component.ts` — confirm file-selected output event emits a filename string
- **Modify**: `web-ng/src/app/reader-panel/reader-panel.component.ts` — confirm parsed HTML content input and verify it uses `marked` and `DOMPurify` internally or accepts pre-parsed HTML
- **Modify**: `web-ng/src/app/landing-pitch/landing-pitch.component.ts` — confirm standalone and document any required inputs
- **Modify**: `web-ng/src/app/create-project-modal/create-project-modal.component.ts` — confirm the modal is standalone-importable and identify the submit output event that will become a no-op in the playground

### Steps
1. Open each of the six sub-component TypeScript files and catalog every `@Input()` and `@Output()` declaration, noting the type, whether it is required or optional, and any default values.
2. Cross-reference each input type against the exported TypeScript interfaces in the project's types or models directory to confirm the demo data can satisfy every required input without introducing new types.
3. Inspect `StatusBarComponent` specifically to verify it accepts a mode input that supports at least four distinct string literal values — idle, active, success, and failure — since the playground will render four simultaneous instances.
4. Inspect `SidebarV2Component` to confirm it emits a file-selection output event carrying a filename string, which the playground will use to drive the reader panel binding.
5. Inspect `ReaderPanelComponent` to determine whether it expects raw markdown or pre-parsed sanitized HTML, so Task 2 knows whether demo spec content should be stored as markdown strings or pre-rendered HTML.
6. Confirm the create-project modal component exists, is standalone, and has an identifiable submit callback or output event that can be intercepted with a no-op handler.
7. If any component is missing required inputs, has untyped signatures, or is not standalone, fix or flag it now before proceeding to Task 2.

### Verify
- A written list of every `@Input` and `@Output` for all six sub-components plus the create modal exists, with types confirmed against project interfaces
- `ng build --configuration production` still passes after any stabilization edits
- No sub-component requires a service injection or HTTP call to render — all accept data purely through inputs

---

## Task 2: Build Demo Data Constants  [Effort: 1 day]

### What
Author hardcoded demo data files that supply realistic projects, specs, and section metadata to the playground component. Isolating this data into dedicated files keeps the playground component under 200 lines and makes the demo content independently editable. The data shapes must exactly match the `@Input` contracts verified in Task 1.

### Files
- **Create**: `web-ng/src/app/live-playground/demo-projects.ts` — exports a `DEMO_PROJECTS` constant containing eight `Project` objects distributed across all four sections with realistic names and dates
- **Create**: `web-ng/src/app/live-playground/demo-specs.ts` — exports a `DEMO_SPECS` constant as a `Record<string, DemoSpec>` map keyed by filename, each containing markdown content with at least three headings, a table, and a bullet list to exercise the reader panel's newspaper layout
- **Create**: `web-ng/src/app/live-playground/demo-sections.ts` — exports a `DEMO_SECTIONS` constant containing section metadata including section names, project counts, and pulse states for the section nav and status bar components

### Steps
1. Create the `web-ng/src/app/live-playground/` directory to house all playground-related files.
2. In `demo-projects.ts`, define eight project objects that conform to the `Project` interface, distributing two projects into each of the four sections. Use realistic software project names that suggest real capabilities rather than generic test names.
3. In `demo-specs.ts`, define at least three spec entries keyed by filename strings such as `architecture.md`, `requirements.md`, and `api-reference.md`. Each spec's markdown content must be long enough to demonstrate the newspaper column layout — include multiple headings, a markdown table, and bullet lists.
4. In `demo-sections.ts`, define section metadata entries that match the section nav component's expected input shape, including human-readable section names and project counts derived from the eight demo projects.
5. Ensure every exported constant uses the project's existing TypeScript interfaces for type safety — import `Project`, `Spec`, `SpecSummary`, and `SpecDetail` from the types directory rather than defining ad hoc shapes.
6. Confirm that no demo data file exceeds 200 lines; if the spec markdown content pushes a file over the limit, split into an additional file.

### Verify
- Each demo data file exports typed constants that satisfy the `@Input` contracts documented in Task 1
- TypeScript compilation passes with no type errors when importing the constants — run `npx tsc --noEmit`
- No individual file exceeds 200 lines as measured by `wc -l web-ng/src/app/live-playground/demo-*.ts`
- The `DEMO_SPECS` map contains at least three entries keyed by distinct filenames

---

## Task 3: Create Live Playground Component and Template  [Effort: 1.5 days]

### What
Build the `LivePlaygroundComponent` that composes all six V2 sub-components on a single scrollable page, wired with Angular signals and computed properties fed by the demo data from Task 2. This is the core deliverable — the page that replaces the static playground with a live, interactive component showroom.

### Files
- **Create**: `web-ng/src/app/live-playground/live-playground.component.ts` — the component class declaring demo signals, computed properties for derived state, and event handler methods for sidebar-to-reader binding
- **Create**: `web-ng/src/app/live-playground/live-playground.component.html` — the template organizing sub-components into labeled sections: Section Nav, Status Bar (four instances), Project Grid, Sidebar, Reader Panel, and Landing Pitch
- **Create**: `web-ng/src/app/live-playground/live-playground.component.scss` — minimal layout styles for section spacing and page-level structure; sub-component styles remain in their own files

### Steps
1. In the component class, import all six sub-components as standalone imports in the `@Component` decorator's `imports` array, along with the demo data constants from the files created in Task 2.
2. Declare a `demoProjects` signal initialized from `DEMO_PROJECTS`, a `demoSections` signal from `DEMO_SECTIONS`, and a `demoActiveFile` signal initialized to the first filename key in the `DEMO_SPECS` map.
3. Create a computed property that looks up the current `demoActiveFile` value in the `DEMO_SPECS` map, pipes the markdown content through `marked.parse()` and `DOMPurify.sanitize()`, and returns the safe HTML string for the reader panel.
4. Write an `onFileSelected` method that receives a filename string from the sidebar's output event and sets the `demoActiveFile` signal to the new value.
5. In the template, create a section for the status bar that renders four `StatusBarComponent` instances side by side, each bound to a different mode value — idle, active, success, and failure.
6. In the template, bind `SidebarV2Component`'s file-selected output to the `onFileSelected` handler, and bind `ReaderPanelComponent`'s content input to the computed parsed-HTML property.
7. In the template, bind `ProjectGridComponent` to the `demoProjects` signal and `SectionNavComponent` to the `demoSections` signal.
8. Add `LandingPitchComponent` as its own labeled section at the bottom of the page.
9. Verify the component class stays under 200 lines; if it approaches the limit, check that no demo data leaked into the class and extract any remaining inline data to the demo data files.

### Verify
- `ng build --configuration production` passes with zero errors
- The component file `live-playground.component.ts` is under 200 lines as measured by `wc -l`
- All six sub-components appear in the template with bindings to demo data signals or computed properties
- The sidebar-to-reader binding is wired through signals — no imperative DOM manipulation or service injection

---

## Task 4: Wire Route and Retire Static Playground  [Effort: 0.5 days]

### What
Introduce Angular Router configuration for the first time in the project, point `/playground` to the new `LivePlaygroundComponent`, and move the old `DesignPlaygroundComponent` to `/playground-static` so it remains accessible as a historical reference.

### Files
- **Create**: `web-ng/src/app/app.routes.ts` — the route configuration file defining three entries: `/playground` for the live component, `/playground-static` for the old component, and a default fallback to `AppComponent`
- **Modify**: `web-ng/src/app/app.component.ts` — add `RouterOutlet` to the component's imports and include the `router-outlet` element in its template if not already present
- **Modify**: `web-ng/src/app/app.config.ts` or the bootstrap file — register the router with `provideRouter` using the route definitions from `app.routes.ts`
- **Modify**: any landing page or navigation component that links to the old playground — update href or routerLink values from the old playground reference to `/playground`

### Steps
1. Create `app.routes.ts` with a `Routes` array containing three entries: a path for `playground` lazy-loading or directly referencing `LivePlaygroundComponent`, a path for `playground-static` referencing `DesignPlaygroundComponent`, and a wildcard or empty-path default that renders the existing `AppComponent` shell.
2. In the application bootstrap configuration, add `provideRouter(routes)` to the providers array so the Angular Router is active at application startup.
3. Add `RouterOutlet` to the `AppComponent` imports and place a `router-outlet` element in the app component template so routed components can render.
4. Search the entire `web-ng/src/app/` directory for any references to the old playground route or component selector, including the landing page component, and update them to point to `/playground`.
5. Manually verify in a dev server that navigating to `/playground` renders the live playground, navigating to `/playground-static` renders the old static playground, and navigating to the root renders the main application shell unchanged.
6. Confirm that the existing signal-based navigation within the main app still functions correctly — the router wraps the app as the default route but must not interfere with internal signal-driven view switching.

### Verify
- `ng build --configuration production` passes with zero errors
- Navigating to `/playground` in the browser renders the live playground with all six sub-components visible
- Navigating to `/playground-static` renders the old 2,304-line static playground
- No existing navigation links in the app or landing page are broken — search for dead references with `grep -r "playground" web-ng/src/app/`

---

## Task 5: Add Dark Mode Toggle and Create Modal Trigger  [Effort: 1 day]

### What
Layer two interactive features onto the live playground: a page-level dark mode toggle that switches all sub-components between light and dark themes simultaneously, and a trigger button that opens the create-project modal in display-only mode with a no-op submit handler. These are lower priority because the core demo value is delivered by Tasks 1 through 4.

### Files
- **Modify**: `web-ng/src/app/live-playground/live-playground.component.ts` — add an `isDarkMode` boolean signal, a toggle method that sets the `data-theme` attribute on `document.documentElement`, a `showCreateModal` boolean signal, and a no-op submit handler for the modal
- **Modify**: `web-ng/src/app/live-playground/live-playground.component.html` — add a dark mode toggle control at the top of the page and a create-project button that opens the modal; add the create-project modal component with its submit output bound to the no-op handler
- **Modify**: `web-ng/src/app/live-playground/live-playground.component.scss` — add styles for the toggle control and the modal trigger button, keeping them consistent with the existing design token system

### Steps
1. In the component class, declare an `isDarkMode` signal initialized to `false` and a `toggleDarkMode` method that flips the signal and sets `document.documentElement.setAttribute('data-theme', ...)` to either `light` or `dark` based on the new value.
2. In the template, add a toggle control near the top of the page — before all component sections — bound to the `isDarkMode` signal and the `toggleDarkMode` click handler. Label it clearly so visitors understand it affects the entire page.
3. Verify that toggling dark mode causes all six sub-components to re-render with dark theme styles by confirming their SCSS files reference `[data-theme="dark"]` CSS custom properties.
4. Add the create-project modal component to the component's standalone imports array.
5. Declare a `showCreateModal` boolean signal and a method to set it to `true` when the trigger button is clicked.
6. In the template, add a button labeled to indicate project creation that sets `showCreateModal` to `true`, and conditionally render the create-project modal component when the signal is truthy.
7. Bind the modal's submit output to a no-op handler that logs to the console and optionally sets `showCreateModal` back to `false`, displaying a brief message indicating demo mode rather than creating a real project.
8. Confirm the component class still stays under 200 lines after these additions.

### Verify
- Clicking the dark mode toggle switches all visible sub-components between light and dark themes in a single action — visually confirm in the browser
- Clicking the create-project button opens the modal with a functional form that accepts input in all fields
- Submitting the modal form does not make any HTTP calls — confirm by watching the browser network tab during submit
- `ng build --configuration production` passes with zero errors and the component file remains under 200 lines