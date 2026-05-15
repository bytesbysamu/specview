# Implementation Guide: Unified Page

## Overview
This epic collapses three disconnected surfaces — a static landing page, a 2,304-line static design playground, and the live Angular app — into a single Angular template rendered at `/`. Tasks 1 and 2 run in parallel: Task 1 decomposes the playground HTML into five standalone Angular components preserving its CSS grid and design tokens, while Task 2 extracts the landing pitch hero into its own component. Task 3 composes all of these into a new `app-v2` root component on a staging route. Task 4 wires auth-conditional rendering so anonymous visitors see the pitch and authenticated users land directly in their workspace. Task 5 promotes the staging component to the root bootstrap entry and redirects the legacy `/app` path.

## Shared Pre-flight
- Confirm the Angular workspace builds cleanly by running `ng build --configuration production` with zero errors before starting any task.
- Locate the static playground HTML file (likely `landing/playground.html`, approximately 2,304 lines) and the static landing page (`landing/index.html`) — these are the source artifacts for extraction.
- Identify the existing app entry point in `src/app/app.component.ts` and catalog every signal it owns: `projects`, `activeProject`, `activeSpec`, `loading`, `error`, `bootstrapProgress`, `currentStep`.
- Confirm `ProjectsService` exists in `src/app/services/` and exposes `listProjects()` and `bootstrap()` methods.
- Verify that `marked` and `dompurify` are already listed in `package.json` dependencies.
- Extract shared design tokens (CSS custom properties for typography scale, spacing rhythm, color palette, and dark-mode overrides) from the playground CSS and promote them into `src/styles.scss` as global variables — all five playground-derived components will reference these tokens.
- Ensure Angular 17+ control-flow syntax (`@if`, `@for`) is available in the workspace and that no legacy `*ngIf`/`*ngFor` directives will be used.
- Create the target directories: `src/app/components/project-grid/`, `src/app/components/reader-panel/`, `src/app/components/sidebar/`, `src/app/components/status-bar/`, `src/app/components/section-nav/`, and `src/app/components/landing-pitch/`.

---

## Task 1: Decompose Playground HTML into Angular Components  [Effort: 2 days]

### What
Break the 2,304-line static playground HTML into five standalone Angular components — ProjectGridComponent, ReaderPanelComponent, SidebarComponent, StatusBarComponent, and SectionNavComponent — each under 200 lines. These components preserve the playground's CSS classes, grid layouts, and newspaper-style design tokens as the visual foundation for the unified page.

### Files
- **Create**: `src/app/components/project-grid/project-grid.component.ts` — standalone component for the newspaper-style project card grid
- **Create**: `src/app/components/project-grid/project-grid.component.html` — template extracted from the playground's project grid section
- **Create**: `src/app/components/project-grid/project-grid.component.scss` — grid-specific styles extracted from the playground CSS
- **Create**: `src/app/components/reader-panel/reader-panel.component.ts` — standalone component for the expanded document reader
- **Create**: `src/app/components/reader-panel/reader-panel.component.html` — template extracted from the playground's reader section
- **Create**: `src/app/components/reader-panel/reader-panel.component.scss` — reader-specific styles from the playground CSS
- **Create**: `src/app/components/sidebar/sidebar.component.ts` — standalone component for the left-hand file tree navigation rail
- **Create**: `src/app/components/sidebar/sidebar.component.html` — template extracted from the playground's sidebar section
- **Create**: `src/app/components/sidebar/sidebar.component.scss` — sidebar-specific styles from the playground CSS
- **Create**: `src/app/components/status-bar/status-bar.component.ts` — standalone component for the bottom generation-status strip
- **Create**: `src/app/components/status-bar/status-bar.component.html` — template extracted from the playground's status bar section
- **Create**: `src/app/components/status-bar/status-bar.component.scss` — status bar styles from the playground CSS
- **Create**: `src/app/components/section-nav/section-nav.component.ts` — standalone component for the spec-type tabs or breadcrumb navigation
- **Create**: `src/app/components/section-nav/section-nav.component.html` — template extracted from the playground's section navigation
- **Create**: `src/app/components/section-nav/section-nav.component.scss` — section nav styles from the playground CSS
- **Modify**: `src/styles.scss` — add promoted CSS custom properties (typography scale, spacing rhythm, color palette, dark-mode overrides) extracted from the playground's shared design tokens

### Steps
1. Open the playground HTML file and identify the five distinct layout zones: the project card grid, the document reader panel, the left sidebar navigation rail, the bottom status bar strip, and the top section navigation tabs.
2. For each zone, identify its outermost container element and note the CSS classes, grid-area assignments, and any parent-child nesting relationships that affect styling.
3. Extract the project grid zone into `project-grid.component.html`, keeping all original CSS classes intact. In the component TypeScript file, declare a standalone component with `@Input()` signals for the `projects` list. Replace static mockup cards with an `@for` loop over the projects input, and include a hardcoded constant array of example `ProjectSummary` objects for anonymous-mode rendering.
4. Extract the reader panel zone into `reader-panel.component.html`. In the component TypeScript file, declare an `@Input()` for `activeSpec` and bind the template content area to render markdown through the existing `marked` plus `DOMPurify` pipeline. Replace the static lorem content with a signal binding that renders the real spec content.
5. Extract the sidebar zone into `sidebar.component.html`. In the component TypeScript file, declare `@Input()` signals for `activeProject` and `activeSpec`, and an `@Output()` event emitter for spec selection. Replace the static filename list with an `@for` loop over `activeProject.specs`.
6. Extract the status bar zone into `status-bar.component.html`. In the component TypeScript file, declare `@Input()` signals for `bootstrapProgress`, `currentStep`, and `loading`. Replace the static status text with signal bindings.
7. Extract the section nav zone into `section-nav.component.html`. In the component TypeScript file, declare an `@Input()` for the available specs of the active project and an `@Output()` for spec-type selection events. Replace static labels with an `@for` loop.
8. For each component, extract its corresponding CSS from the playground stylesheet into the component's `.scss` file. Keep only the rules that apply to elements within that component's template. Remove any shared design token declarations that were already promoted to `src/styles.scss`.
9. Visually verify each extracted component in isolation by temporarily rendering it in a test harness or the existing app shell, comparing it side-by-side with the original playground in the browser to catch CSS specificity breaks, grid-area misalignments, or responsive breakpoint regressions.

### Verify
- Each of the five component TypeScript files is under 200 lines, confirmed by running `wc -l src/app/components/*//*.component.ts`.
- `ng build --configuration production` completes with zero errors after all five components are created.
- Rendering each component in isolation visually matches the corresponding section of the original static playground — grid proportions, typography, spacing, and dark-mode colors are identical.
- The shared CSS custom properties in `src/styles.scss` are referenced by at least two of the five component `.scss` files, confirming token promotion worked.

---

## Task 2: Extract Landing Pitch into Angular Component  [Effort: 1 day]

### What
Convert the hero and pitch content from `landing/index.html` into a standalone Angular presentational component. This component has no signals, no service dependencies, and no interactivity beyond a "Get Started" link. It runs in parallel with Task 1.

### Files
- **Create**: `src/app/components/landing-pitch/landing-pitch.component.ts` — standalone presentational component for the hero headline, value proposition, and call-to-action
- **Create**: `src/app/components/landing-pitch/landing-pitch.component.html` — template extracted from the landing page's hero and pitch sections
- **Create**: `src/app/components/landing-pitch/landing-pitch.component.scss` — styles extracted from the landing page CSS, preserving fonts, spacing, background treatment, and responsive breakpoints

### Steps
1. Open `landing/index.html` and identify the hero section containing the product headline, value proposition copy, and the call-to-action button or link.
2. Extract the hero section HTML into `landing-pitch.component.html`, preserving all original CSS classes and structural markup. The "Get Started" call-to-action should remain as a standard anchor link pointing to the existing auth redirect URL.
3. In `landing-pitch.component.ts`, declare a standalone component with no inputs, no outputs, and no injected services. Set the component selector to `app-landing-pitch`, reference the external template and stylesheet, and set `changeDetection` to `OnPush`.
4. Extract the landing page's hero-specific CSS into `landing-pitch.component.scss`. This component does not use the playground's design tokens — it retains its own visual identity with its own font choices, spacing scale, and background treatment.
5. Visually verify the extracted component renders identically to the original landing page hero by temporarily mounting it in the app shell and comparing in the browser at desktop and mobile viewport widths.

### Verify
- `landing-pitch.component.ts` is under 200 lines, confirmed by `wc -l src/app/components/landing-pitch/landing-pitch.component.ts`.
- `ng build --configuration production` completes with zero errors.
- The rendered component visually matches the original `landing/index.html` hero section at both desktop and mobile breakpoints.
- The "Get Started" call-to-action link navigates to the existing auth redirect URL without errors.

---

## Task 3: Compose Unified Template (app-v2)  [Effort: 2 days]

### What
Create the `UnifiedPageComponent` (aliased as `app-v2`) that imports all playground-derived layout components, the landing pitch component, and the existing app signals and services into a single composition root on a staging route. This is the architectural centerpiece — it owns the signals that currently live in `app.component.ts` and arranges child components in a CSS grid shell.

### Files
- **Create**: `src/app/app-v2.component.ts` — composition root component that owns all signals (`projects`, `activeProject`, `activeSpec`, `loading`, `error`, `bootstrapProgress`, `currentStep`) and imports child components plus `AuthService` and `ProjectsService`
- **Create**: `src/app/app-v2.component.html` — unified template arranging LandingPitchComponent at the top, then a CSS grid shell containing SidebarComponent, SectionNavComponent, ProjectGridComponent or ReaderPanelComponent in the center, and StatusBarComponent at the bottom
- **Create**: `src/app/app-v2.component.scss` — grid shell layout styles defining the CSS grid areas, shared spacing, and responsive behavior derived from the playground's top-level grid
- **Create**: `src/app/services/auth.service.ts` — AuthService exposing `isAuthenticated`, `currentUser`, and `authLoading` signals; reads JWT from localStorage and validates via `GET /api/auth/me`
- **Create**: `src/app/services/auth.service.spec.ts` — unit tests for AuthService covering token-present, token-expired, token-missing, and network-error scenarios
- **Create**: `src/app/services/auth.service.mock.ts` — mock factory for AuthService returning controllable signals for use in child component tests
- **Modify**: `src/app/app.config.ts` — temporarily add `UnifiedPageComponent` as an available bootstrap component for staging validation (do not yet replace `AppComponent`)

### Steps
1. Create `AuthService` in `src/app/services/auth.service.ts`. Declare three signals: `isAuthenticated` (boolean), `currentUser` (the `/api/auth/me` response or null), and `authLoading` (boolean, initially true). In the constructor, check `localStorage` for a JWT token. If present, call `GET /api/auth/me` using `HttpClient` to validate it. On success, set `currentUser` and `isAuthenticated` to true. On failure or missing token, set `isAuthenticated` to false. In both cases, set `authLoading` to false when the check completes.
2. Write unit tests in `auth.service.spec.ts` covering four scenarios: valid token resolves `isAuthenticated` to true, expired token resolves to false, missing token resolves to false without making an HTTP call, and network error on `/api/auth/me` resolves to false gracefully. Create the mock factory in `auth.service.mock.ts` that returns an `AuthService`-shaped object with writable signals.
3. Create `UnifiedPageComponent` in `src/app/app-v2.component.ts`. Inject `AuthService` and `ProjectsService`. Declare the same signals currently owned by `app.component.ts`: `projects`, `activeProject`, `activeSpec`, `loading`, `error`, `bootstrapProgress`, `currentStep`. In `ngOnInit`, check `isAuthenticated()` — if true, call `ProjectsService.listProjects()` to populate the `projects` signal. If false, skip the API call.
4. Build the unified template in `app-v2.component.html`. Place `app-landing-pitch` at the top of the template. Below it, define a div with the playground's top-level CSS grid classes to serve as the layout shell. Inside the grid shell, place `app-sidebar` in the left rail area, `app-section-nav` in the top bar area, either `app-project-grid` or `app-reader-panel` in the center area (toggled by whether `activeProject` is set), and `app-status-bar` in the bottom strip area.
5. Wire the child component inputs in the template. Pass `projects` to ProjectGridComponent, `activeProject` and `activeSpec` to SidebarComponent, `activeSpec` to ReaderPanelComponent, available specs to SectionNavComponent, and `bootstrapProgress`, `currentStep`, and `loading` to StatusBarComponent. Bind output events from SidebarComponent and SectionNavComponent to update `activeSpec` and `activeProject` signals.
6. Define the grid shell styles in `app-v2.component.scss`. Extract the playground's top-level CSS grid declaration (grid-template-areas, grid-template-columns, grid-template-rows) and responsive breakpoint overrides. Apply shared spacing variables from `src/styles.scss`.
7. Migrate the `submitBraindump()` method and its polling logic from `app.component.ts` into `app-v2.component.ts`, ensuring it calls `ProjectsService.bootstrap()`, stores the `job_id`, polls `GET /status/{job_id}` via setInterval, and updates `bootstrapProgress` and `currentStep` signals until completion.
8. Temporarily update `src/app/app.config.ts` to bootstrap `UnifiedPageComponent` instead of `AppComponent` for local validation. Serve the app with `ng serve` and verify the full composition renders correctly in the browser.

### Verify
- `ng build --configuration production` completes with zero errors with `UnifiedPageComponent` as the bootstrap component.
- All `AuthService` unit tests pass when running `ng test --include=**/auth.service.spec.ts`.
- The unified page renders the playground-derived layout grid with correct proportions, matching the original playground visually.
- Authenticated users see their real project list populated from `ProjectsService.listProjects()`, and clicking a project card updates the reader panel with real spec content.

---

## Task 4: Wire Auth-Conditional Rendering  [Effort: 0.5 days]

### What
Use the `AuthService.isAuthenticated` and `AuthService.authLoading` signals to conditionally render sections of the unified template — anonymous visitors see the landing pitch with placeholder content, authenticated users see their workspace with live data, and a loading skeleton prevents auth-state flash during token validation.

### Files
- **Modify**: `src/app/app-v2.component.html` — wrap the landing pitch in an `@if (!authService.isAuthenticated())` block, wrap the workspace data bindings in an `@if (authService.isAuthenticated())` block, and add an `@if (authService.authLoading())` guard at the top that renders a loading skeleton while the initial auth check is in flight
- **Modify**: `src/app/components/project-grid/project-grid.component.ts` — add logic to display the hardcoded example `ProjectSummary` array when the projects input is empty or null (anonymous mode), and real project data when populated (authenticated mode)
- **Modify**: `src/app/components/reader-panel/reader-panel.component.ts` — add a fallback to render a sample spec document when `activeSpec` is null (anonymous mode)
- **Modify**: `src/app/components/sidebar/sidebar.component.ts` — add a fallback to display sample filenames when `activeProject` is null (anonymous mode)

### Steps
1. Open `src/app/app-v2.component.html` and wrap the outermost container in an `@if` guard on `authService.authLoading()`. When loading is true, render a minimal loading skeleton element in the top zone. When loading is false, render the full conditional content below.
2. Inside the loading-resolved block, wrap the `app-landing-pitch` element in `@if (!authService.isAuthenticated())` so it only renders for anonymous visitors.
3. In the workspace section of the template, add conditional logic so that when `isAuthenticated()` is true, child components receive real signal data, and when false, they receive null or empty inputs which trigger their built-in placeholder rendering.
4. In `project-grid.component.ts`, add a check at the top of the template rendering logic: if the `projects` input is empty or null, render the hardcoded example `ProjectSummary` constant array instead. Ensure the example data conforms to the same `ProjectSummary` interface used by real projects.
5. In `reader-panel.component.ts`, add a fallback: if `activeSpec` is null, render a static sample spec markdown string through the same `marked` plus `DOMPurify` pipeline.
6. In `sidebar.component.ts`, add a fallback: if `activeProject` is null, render a static list of sample filenames.
7. Test the anonymous experience by clearing the JWT from localStorage, reloading the page, and confirming the landing pitch appears at top with placeholder content in the grid, reader, and sidebar below.
8. Test the authenticated experience by logging in through the existing auth flow, returning to `/`, and confirming the landing pitch is hidden and real project data populates all components.

### Verify
- With no JWT in localStorage, the page renders the landing pitch at the top and placeholder content in the workspace grid, reader panel, and sidebar.
- With a valid JWT in localStorage, the page hides the landing pitch entirely and shows real project data in all workspace components.
- During the brief `authLoading` period (observable by throttling the network in browser devtools), neither the pitch nor the workspace flashes — only the loading skeleton is visible.
- `ng build --configuration production` completes with zero errors.

---

## Task 5: Route Cutover and Legacy Redirect  [Effort: 0.5 days]

### What
Promote `UnifiedPageComponent` as the permanent root bootstrap component, update the nginx configuration so `/` serves the Angular SPA, redirect `/app` to `/`, and migrate landing page SEO meta tags into the Angular app's `index.html`.

### Files
- **Modify**: `src/app/app.config.ts` — set `UnifiedPageComponent` as the sole bootstrap component, removing `AppComponent` from the bootstrap array
- **Modify**: `src/index.html` — add the landing page's SEO meta tags (title, description, Open Graph tags) so crawlers receive them from the Angular entry point
- **Modify**: `nginx.conf` (or equivalent server configuration file) — update the root location to serve the Angular build's `index.html` for all non-API paths, and add a redirect rule from `/app` to `/`
- **Modify**: `src/app/app-v2.component.ts` — rename the selector from `app-v2` to `app-root` (or update `src/index.html` to use the `app-v2` selector) so the Angular bootstrap finds the correct root element

### Steps
1. Open `src/app/app.config.ts` and change the bootstrap array to contain only `UnifiedPageComponent`. Remove `AppComponent` from the array entirely.
2. Update the root element selector in `src/index.html` to match `UnifiedPageComponent`'s selector. If the component uses `app-v2` as its selector, either change the selector in `app-v2.component.ts` to `app-root` or change the element tag in `index.html` to `app-v2`.
3. Copy the SEO meta tags from `landing/index.html` — including the page title, meta description, and any Open Graph tags — into the `<head>` section of `src/index.html`.
4. Open the nginx configuration file and update the root location block to serve `index.html` from the Angular build output directory for all paths that do not match `/api/`. Add a location block for `/app` that returns a 301 redirect to `/`.
5. Build the production bundle with `ng build --configuration production` and verify the output directory contains the updated `index.html` with SEO tags.
6. Start the application through the production-like nginx configuration and verify that navigating to `/` serves the Angular unified page, navigating to `/app` redirects to `/`, and API routes still proxy correctly to the Flask backend.
7. Confirm that the old `src/app/app.component.ts`, `src/app/app.component.html`, and `src/app/app.component.scss` files are no longer imported or referenced anywhere. Leave them in the repository as inert reference artifacts per the architecture decision — do not delete them in this task.

### Verify
- `ng build --configuration production` completes with zero errors using `UnifiedPageComponent` as the sole bootstrap component.
- Navigating to `/` in the browser serves the unified Angular page with the correct SEO meta tags visible in the page source.
- Navigating to `/app` returns a 301 redirect to `/`.
- The Flask API routes (such as `/api/auth/me` and `/api/projects`) continue to respond correctly through the nginx proxy.
---


---

## Implementation Notes

1. **Reuse existing AuthService.** `web-ng/src/app/services/auth.service.ts` already exists with `isLoggedIn` signal via `TokenLifecycleService`. Do not create a new one in Task 3 — inject the existing service.
2. **Flat Angular structure.** Per CLAUDE.md, new components go at `web-ng/src/app/` level, not under a new `components/` subdirectory.
3. **Gradual cutover.** Route `app-v2` at `/v2` first. Old app stays live at `/` until validated. Task 5 swaps them.
