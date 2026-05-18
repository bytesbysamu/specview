# Implementation Guide: Three-Page Simplification

## Overview
This epic restructures Specview from a multi-route, sidebar-driven Angular application into exactly three pages: a static landing page at `/`, a dual-mode app shell at `/app`, and an internal playground at `/playground`. The work sequences as: bootstrap Angular Router first (Task 1), then build the landing page (Task 2) and mock data layer (Task 3) in parallel, converge on the unified app page with demo/auth modes (Task 4), and finally strip all dead pages and collapse navigation into a top bar (Task 5). The architectural centerpiece is a `DemoAwareProjectsService` that switches between mock fixtures and real API calls based on authentication state, making demo mode invisible to consuming components.

## Shared Pre-flight
- Confirm `@angular/router` is available in `package.json` dependencies — it is already present but unused in the route shell
- Verify the existing `app.routes.ts` file to understand the current route table being replaced
- Review `auth.service.ts` to confirm the authentication signal (`isAuthenticated`) is exposed and reactive
- Review `playground-demo-data.ts` for its data shape — it informs but does not become the demo fixtures
- Identify all components referenced by routes being deleted: `components/login`, `components/upgrade`, `pages/signup`, `pages/public-spec`
- Run `ng build --configuration production` to establish a green baseline before any changes
- Note the monolithic `app-v2.component.ts` (1,087 lines) — its decomposition spans Tasks 1 and 4
- Confirm `styles.css` global newspaper tokens (`--ink`, `--serif`, `--sans`, `--body`) are available for new components

---

## Task 1: Bootstrap Angular Router  [Effort: 1 day]

### What
Add route-based navigation to a currently routerless app. This replaces the signal-based view switching in the root component with a proper Angular Router setup, establishing the three-route foundation that every subsequent task depends on.

### Files
- **Modify**: `src/app/app.config.ts` — add `provideRouter()` with the route configuration to the application providers
- **Modify**: `src/app/app.routes.ts` — replace the existing multi-route table with three routes (`/`, `/app`, `/playground`) plus a wildcard redirect to `/`
- **Modify**: `src/app/app-v2.component.ts` — strip all view-switching logic from the root component and reduce it to a minimal `<router-outlet>` wrapper (target: under 30 lines)

### Steps
1. Open `src/app/app.config.ts` and register `provideRouter(routes)` in the providers array, importing the routes from `app.routes.ts`.
2. Rewrite `src/app/app.routes.ts` to define exactly three routes: `/` pointing to a placeholder landing component, `/app` pointing to a placeholder app component (lazy-loaded), and `/playground` pointing to the existing playground shell (lazy-loaded). Add a wildcard route that redirects any undefined path to `/`.
3. Refactor `src/app/app-v2.component.ts` by removing all signal-based view-switching logic, sidebar integration, and embedded view templates. Replace the template with a `<router-outlet>` element only. The resulting root component should be under 30 lines.
4. Create minimal placeholder standalone components for the landing and app routes so the router resolves without errors. These are scaffolds that Tasks 2 and 4 will replace with real implementations.
5. Verify that navigating between `/`, `/app`, and `/playground` renders the correct placeholder or existing component, and that any other path redirects to `/`.

### Verify
- `ng build --configuration production` completes with zero errors
- Navigating to `/` renders the placeholder landing component
- Navigating to `/app` renders the placeholder app component
- Navigating to `/playground` renders the existing playground shell without regression
- Navigating to any undefined path (e.g., `/signup`, `/v1`) redirects to `/`

---

## Task 2: Build Landing Page (Hero-Only)  [Effort: 1 day]

### What
Replace the placeholder landing component with a zero-dependency static page containing only a headline, subline, and a CTA button that routes to `/app`. This is the primary entry point for unauthenticated visitors and must render instantly with no service injections or API calls.

### Files
- **Create**: `src/app/pages/landing/landing.component.ts` — standalone component with static hero content and a `routerLink="/app"` CTA
- **Create**: `src/app/pages/landing/landing.component.css` — styles using global newspaper design tokens from `styles.css`
- **Modify**: `src/app/app.routes.ts` — update the `/` route to point to the new landing component (eagerly loaded)

### Steps
1. Create the `landing.component.ts` as a standalone Angular component. Import `RouterLink` in the component's imports array. The template contains one headline element, one subline paragraph, and one CTA button bound with `routerLink="/app"`.
2. Style the component using the global newspaper design system tokens (`--ink`, `--serif`, `--sans`, `--body`) from `styles.css`. Reference `landing-pitch.component.ts` for visual direction but strip it down to only the hero section — no features grid, no testimonials, no footer, no multi-section scroll.
3. Update `src/app/app.routes.ts` to point the `/` route at the new `LandingComponent`. Keep it eagerly loaded since it is the primary entry point and is trivially small.
4. Remove the placeholder landing component created in Task 1 if it was a separate file.

### Verify
- `ng build --configuration production` completes with zero errors
- Navigating to `/` renders the hero section with headline, subline, and CTA button
- Clicking the CTA navigates to `/app` without a page reload
- The landing component has zero service injections — confirm no constructor dependencies or `inject()` calls exist in the component

---

## Task 3: Create Mock Data Layer  [Effort: 2 days]

### What
Build the auth-aware data abstraction that makes demo mode invisible to consuming components. This creates curated demo fixtures and a `DemoAwareProjectsService` that returns mock data for unauthenticated users and delegates to the real `ProjectsService` for authenticated users.

### Files
- **Create**: `src/app/services/demo-fixtures.ts` — static TypeScript objects containing two to three polished mock projects with realistic spec content
- **Create**: `src/app/services/demo-aware-projects.service.ts` — wrapper service that injects `AuthService` and forks between `demo-fixtures.ts` and `ProjectsService` based on auth state
- **Modify**: `src/app/services/auth.service.ts` — confirm the `isAuthenticated` signal is publicly readable (no changes expected, but verify the contract)

### Steps
1. Create `src/app/services/demo-fixtures.ts` with two to three static project objects. Each project should have a realistic name, a plausible braindump, and pre-generated spec content that reads as a genuine product demonstration. Shape the data to match the interfaces that `ProjectsService` returns. Do not reuse `playground-demo-data.ts` — demo fixtures are curated for persuasion, playground fixtures are curated for coverage.
2. Create `src/app/services/demo-aware-projects.service.ts` as an injectable service. Inject `AuthService` and `ProjectsService`. Expose the same method signatures as `ProjectsService`: `getProjects()`, `getProject(id)`, and `getSpec(id, section)`.
3. Inside `DemoAwareProjectsService`, create a `computed()` signal derived from `AuthService.isAuthenticated`. When unauthenticated, methods return data from `demo-fixtures.ts`. When authenticated, methods delegate to `ProjectsService`.
4. Add a `loading` signal to `DemoAwareProjectsService` that activates during the first real API fetch after login. This suppresses the visual flash between mock data, loading state, and real data during auth transition.
5. Write the service so that when auth state flips from unauthenticated to authenticated, Angular's signal reactivity propagates the change — no imperative switch-mode call, no event bus, no reload required.

### Verify
- `ng build --configuration production` completes with zero errors
- `DemoAwareProjectsService` is injectable and exposes `getProjects()`, `getProject(id)`, and `getSpec(id, section)`
- When `AuthService.isAuthenticated` is false, calling service methods returns mock fixture data without any HTTP calls
- When `AuthService.isAuthenticated` is true, calling service methods delegates to `ProjectsService`

---

## Task 4: Build App Page with Demo/Auth Modes  [Effort: 2 days]

### What
Build the unified app shell at `/app` that consumes `DemoAwareProjectsService` exclusively. Unauthenticated users see mock projects and specs immediately (demo mode). On login, the service switches to real API calls with the same components rendering real data — no page reload, no redirect. This task also absorbs the project browsing responsibility from the sidebar into inline selection.

### Files
- **Create**: `src/app/pages/app-page/app-page.component.ts` — standalone component composing project grid, reader panel, and status bar with inline project browsing
- **Create**: `src/app/pages/app-page/app-page.component.css` — layout styles for the app page grid
- **Modify**: `src/app/app.routes.ts` — update the `/app` route to lazy-load the new `AppPageComponent`
- **Modify**: `src/app/components/project-grid.component.ts` — change injection from `ProjectsService` to `DemoAwareProjectsService`
- **Modify**: `src/app/components/reader-panel.component.ts` — change injection from `ProjectsService` to `DemoAwareProjectsService`
- **Modify**: `src/app/components/status-bar.component.ts` — change injection from `ProjectsService` to `DemoAwareProjectsService`

### Steps
1. Create `src/app/pages/app-page/app-page.component.ts` as a standalone component. Import and compose three existing sub-components: `project-grid.component`, `reader-panel.component`, and `status-bar.component`. Inject `DemoAwareProjectsService`.
2. Add a local signal to the app page component that holds the currently selected project ID. Wire this signal so that clicking a project in the grid updates it, and the reader panel displays the selected project's spec content. This replaces the project-selection responsibility that previously lived in `sidebar-v2.component`.
3. Update each sub-component (`project-grid.component.ts`, `reader-panel.component.ts`, `status-bar.component.ts`) to inject `DemoAwareProjectsService` instead of `ProjectsService` directly. This is a mechanical find-and-replace of the injection token.
4. Implement the auth-transition UX in the app page: when an unauthenticated user triggers sign-in, `AuthService`'s signal updates, `DemoAwareProjectsService` reactively switches to real API calls, and the project list re-resolves. If the authenticated user has no projects, show an empty-state creation prompt — this is the only empty state in the app and appears only post-login for genuinely new users.
5. Update `src/app/app.routes.ts` to point the `/app` route at `AppPageComponent` using lazy loading via `loadComponent`.
6. Remove the placeholder app component created in Task 1 if it was a separate file.

### Verify
- `ng build --configuration production` completes with zero errors
- Navigating to `/app` while unauthenticated shows mock projects and spec content with zero empty states and zero login prompts
- Clicking a project in the grid displays its spec content in the reader panel
- Logging in while on `/app` transitions from mock data to real API data without a page reload or route change
- An authenticated user with no projects sees the empty-state creation prompt

---

## Task 5: Strip Dead Pages and Collapse Navigation  [Effort: 1 day]

### What
Remove all components not serving the three surviving pages and replace the sidebar with a minimal top bar containing only the logo and an auth action. This is the cleanup pass that eliminates maintenance tax from dead code and completes the navigation collapse.

### Files
- **Create**: `src/app/components/top-bar/top-bar.component.ts` — standalone component with logo (linking to `/`) and login/logout action based on auth state, under 50 lines
- **Create**: `src/app/components/top-bar/top-bar.component.css` — minimal top bar styles
- **Modify**: `src/app/app-v2.component.ts` — add `TopBarComponent` above the `<router-outlet>` in the root shell template
- **Delete**: `src/app/components/sidebar-v2.component.ts` — sidebar replaced by top bar and inline project browsing
- **Delete**: `src/app/components/login/` — login page no longer routed
- **Delete**: `src/app/components/upgrade/` — upgrade page no longer routed
- **Delete**: `src/app/pages/signup/` — signup page no longer routed
- **Delete**: `src/app/pages/public-spec/` — public spec page no longer routed
- **Delete**: `src/app/components/landing-pitch.component.ts` — replaced by the new landing component
- **Modify**: `src/app/app.routes.ts` — confirm no routes reference deleted components; remove any stale imports

### Steps
1. Create `src/app/components/top-bar/top-bar.component.ts` as a standalone component. Inject `AuthService` for the auth action and use `routerLink` for the logo link to `/`. The template contains two elements: the logo and a conditional login/logout button driven by the `isAuthenticated` signal. No navigation links, no project state, no AI state.
2. Modify the root shell component (`app-v2.component.ts`) to import and render `TopBarComponent` above the `<router-outlet>`. The top bar appears on all three pages including the playground.
3. Delete `sidebar-v2.component.ts` and all its associated styles and tests. Remove all imports and references to the sidebar from other components.
4. Delete all components associated with removed routes: the login component directory, upgrade component directory, signup page directory, public-spec page directory, and the old `landing-pitch.component.ts`.
5. Audit `app.routes.ts` and the root module for any imports referencing deleted components. Remove stale imports, unused style references, and orphaned asset files.
6. Search the codebase for any remaining references to deleted components or the sidebar. Remove all dead imports and unused dependency injections.

### Verify
- `ng build --configuration production` completes with zero errors and no warnings about missing components
- The top bar renders on all three pages (`/`, `/app`, `/playground`) with logo and auth action
- No sidebar renders anywhere in the application
- `/playground` remains fully functional with no regression from current behavior
- Navigating to any previously valid route (e.g., `/signup`, `/v1`, `/v2`) redirects to `/`