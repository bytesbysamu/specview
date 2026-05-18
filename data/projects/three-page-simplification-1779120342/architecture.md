I have extensive codebase context from the prompt. Let me write the Solution Architecture document based on everything provided.

# 🏗️ Solution Architecture: Three-Page Simplification

## Architecture Overview

The Three-Page Simplification restructures specview's Angular frontend from a multi-route, sidebar-driven application into three distinct surfaces: a static landing page at `/`, a dual-mode app shell at `/app`, and an internal playground at `/playground`. The architectural keystone is a **data-source abstraction layer** — a single injectable service that sits between every component and the real `ProjectsService`, switching its backing implementation based on authentication state. Components never know whether they're rendering mock or live data.

This architecture exploits a structural advantage that already exists in the codebase: `playground-demo-data.ts` already contains hardcoded demo projects, and `auth.service.ts` already tracks authentication state via signals. The new design wires these two existing capabilities together through one new service — the `DemoAwareProjectsService` — rather than introducing conditional logic across every component. The result is that the entire demo-to-authenticated transition is a single signal flip at the service boundary, invisible to the template layer.

The navigation model collapses from sidebar-driven multi-level browsing to a flat top bar with two elements: logo and auth action. This isn't just a UI simplification — it's an architectural one. The sidebar currently owns route transitions, project selection state, and AI operation triggers. Removing it forces these responsibilities to migrate: route transitions move to the router, project selection moves into the app page component's local signal state, and AI operations stay bound to the reader panel where they're already triggered. No new orchestration layer is needed because the sidebar was aggregating responsibilities that already had natural homes.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | The `DemoAwareProjectsService` becomes the sole data adapter for the app page. Components import this wrapper, never `ProjectsService` directly. Auth state determines which backing source responds. |
| P2 — Thin HTTP Layer | No change to Flask routes or handlers. The backend remains untouched — this epic is purely frontend surface reduction. |
| P4 — No Speculative Abstractions | One wrapper service for one fork (mock vs. real). No generic "data source registry," no plugin architecture for future data modes. The fork is a single `computed()` signal check. |
| P7 — File Size & Structure | The 1,087-line `app-v2.component.ts` gets decomposed as part of this work. The app page, landing page, and top bar are each standalone components under 200 lines. |
| Signal-based state | Auth state, project selection, and demo/live mode all flow through Angular signals. No RxJS subject chains, no NgRx. Signal `computed()` handles derived state like "which data source am I using?" |

## Component Design

### Route Shell

**Purpose**: Replace the current monolithic root component with a minimal router outlet.

The existing `app-v2.component.ts` at 1,087 lines serves as both the root shell and the application view. This architecture splits those roles. The root component shrinks to a `<router-outlet>` wrapper — under 30 lines. All view logic moves into route-level components. The three routes are defined in `app.routes.ts`, replacing the current multi-route table that includes `/v1`, `/v2`, `/signup`, and other surfaces being eliminated. A wildcard redirect sends any undefined path to `/`.

The router uses lazy loading for the app page route (since it carries the heaviest component tree and the service dependency graph) while the landing page loads eagerly since it's the entry point and is trivially small. The playground loads lazily — it's rarely accessed and carries its own substantial component set (`pg-tokens`, `pg-borders`, `pg-animations`, `pg-state-matrix`, `pg-components-app`, `pg-components-ui`).

### Landing Page

**Purpose**: Zero-dependency entry point that routes users into the product.

A standalone component with no service injections. Static content: headline, subline, CTA button with `routerLink="/app"`. This component reuses the newspaper design system tokens from `styles.css` — `--ink`, `--serif`, `--sans`, `--body` — but owns no state and makes no HTTP calls. The existing `landing-pitch.component.ts` provides the starting shape, but the new landing strips it further: no features grid, no multi-section scroll, just the hero.

The design decision to make this completely static means it renders instantly regardless of API health, auth service initialization, or network conditions. First paint is pure HTML and CSS.

### Demo-Aware Data Layer

**Purpose**: Single service boundary that makes demo mode invisible to consuming components.

This is the architectural centerpiece. A new `DemoAwareProjectsService` wraps both `ProjectsService` (real API calls) and a static mock data module (evolved from `playground-demo-data.ts`). It injects `AuthService` and exposes the same method signatures as `ProjectsService` — `getProjects()`, `getProject(id)`, `getSpec(id, section)` — but routes calls based on auth state.

The switching mechanism is a `computed()` signal derived from `AuthService`'s authentication signal. When auth state changes (user logs in), the computed signal flips, and any component reading project data through this service reactively receives real API data on the next read. No imperative "switch mode" call, no event bus, no reload. Angular's signal reactivity handles the propagation.

Mock data fixtures live in a dedicated file (`demo-fixtures.ts`), separate from the playground's `playground-demo-data.ts`. The playground has its own demo data needs (component state matrices, edge cases, stress tests) that don't align with what a first-time visitor should see. Demo fixtures are curated for persuasion — two to three polished projects with realistic spec content that demonstrates the product's value. Playground fixtures are curated for coverage.

### App Page

**Purpose**: Unified workspace that renders identically in demo and authenticated modes.

The app page consumes `DemoAwareProjectsService` exclusively. It composes three existing sub-components: `project-grid.component` for project browsing, `reader-panel.component` for spec display, and `status-bar.component` for generation status. These components already exist and already consume data through service injection — the migration is changing which service they inject, not how they render.

Project browsing currently lives in `sidebar-v2.component`, which combines project listing, section navigation, and AI operation triggers. The app page absorbs the project listing responsibility directly (a signal holding the selected project ID, fed to the grid and reader). Section navigation stays in `section-nav.component`, which is already a standalone piece. AI operation triggers remain on the reader panel where the user's attention already is.

The app page also owns the auth-transition UX. When an unauthenticated user clicks "Sign in," the auth flow completes, `AuthService`'s signal updates, `DemoAwareProjectsService` reactively switches to real API calls, and the app page's project list re-resolves. If the authenticated user has no projects yet, the app page shows an empty-state creation prompt — but this is the *only* empty state in the entire app, and it only appears post-login for genuinely new users. Demo visitors never see it.

### Top Bar

**Purpose**: Minimal persistent chrome replacing the sidebar.

A standalone component rendered by the route shell (above the `<router-outlet>`), visible on all three pages. Contains two elements: the logo (linking to `/`) and a single auth action (login or logout, based on auth signal state). No navigation links — the landing CTA and router handle all navigation. The playground has no nav link by design; it's accessed by direct URL only.

The top bar stays under 50 lines. It injects `AuthService` for the auth action and uses `routerLink` for the logo. No project state, no AI state, no generation status — those are the app page's concerns.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Router | `@angular/router` via `provideRouter()` | Already available in `app.routes.ts`; the app already has routing configured. This epic reduces the route table, it doesn't introduce routing. |
| State | Angular signals (`signal`, `computed`, `effect`) | Already the state pattern across all V2 components. No new state library. |
| Mock data | Static TypeScript objects | Matches `playground-demo-data.ts` pattern. No mock server, no interceptors, no service worker. Static imports that tree-shake out if unused. |
| Styling | Global `styles.css` token system | All V2 components already use global newspaper tokens. No component-scoped CSS. No new design tokens needed. |
| Auth | Existing `AuthService` + `TokenLifecycleService` | JWT flow is untouched. The only new dependency is that `DemoAwareProjectsService` reads auth state — a one-line injection. |
| Backend | No changes | Flask API, chain adapter, background jobs — all unchanged. This epic is frontend-only. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Separate demo fixtures from playground fixtures | Demo data is curated for first impressions — polished, realistic, minimal. Playground data is curated for component coverage — edge cases, stress tests, empty states. Mixing them dilutes both purposes. | Two fixture files to maintain instead of one. Acceptable because they serve different audiences and evolve on different triggers. |
| Wrapper service over HTTP interceptor for mock data | An interceptor would catch all HTTP calls and return mocks based on URL pattern. A wrapper service is explicit — the fork point is visible in the dependency graph, not hidden in middleware. Interceptors also complicate debugging when you're unsure whether you're hitting mock or real endpoints. | Components must inject `DemoAwareProjectsService` instead of `ProjectsService`. This is a mechanical find-and-replace, not a design burden. |
| Eager landing, lazy app and playground | The landing page is the entry point for most visitors and is trivially small (static HTML). The app page carries the full service graph. Lazy loading it means unauthenticated visitors who never click the CTA pay zero cost for the app bundle. | Slight delay on first `/app` navigation. Negligible because Angular's lazy loading prefetch can be tuned, and the app bundle isn't large for a three-page site. |
| No sidebar — project browsing inline on app page | The sidebar served as a navigation hub for a multi-page app. With one app page, navigation is selection within the page. Inline project browsing (grid → click → reader) replaces sidebar's project list without an extra layout column. | Loses persistent project list visibility during spec reading. Acceptable because the grid-to-reader transition is a natural flow, and a "back to projects" action is trivial. |
| Wildcard redirect to `/` not `/app` | An unknown URL likely means a stale bookmark or a typo. Dropping to the landing page gives the user orientation. Dropping to the app page skips context — the user doesn't know what this product is yet. | Returning users who mistype a URL see the landing page instead of going straight to their workspace. Minor friction, easily corrected by the CTA. |
| Top bar on all pages including playground | Consistent chrome means the playground doesn't feel like a broken page if someone stumbles onto it. The top bar is two elements — logo and auth — so the visual cost is near zero. | Playground gets a sliver of non-playground UI. Acceptable because the top bar is purely navigational and doesn't interfere with design system exploration. |
| Auth transition without reload | Signals propagate auth state changes reactively. When `AuthService` flips from unauthenticated to authenticated, every `computed()` depending on it re-evaluates. The app page's data source switches, the top bar's action label switches, and no route change occurs. | If the real API returns an error on first authenticated fetch, the user sees a flash from mock to error state. Mitigated by a loading signal during the first real fetch after login. |
| No removal of backend endpoints | Flask routes for removed pages (signup, upgrade, etc.) stay intact. Cleaning them up is a separate hygiene task that carries zero user value and non-zero risk of breaking something downstream. | Dead endpoints accumulate. Low cost — they serve no traffic and introduce no maintenance burden until the next backend deploy. |

## Data Flow

The critical data path runs: **Landing CTA → Router → App Page → DemoAwareProjectsService → (mock fixtures | ProjectsService → Flask API)**. 

For unauthenticated users, the chain terminates at mock fixtures — no network call, no latency, no failure mode. The app renders instantly with curated content. For authenticated users, the chain continues through `ProjectsService` to the Flask API, with the same component tree rendering real data through the same template bindings.

Auth state change triggers a reactive cascade: `AuthService.isAuthenticated` (signal) → `DemoAwareProjectsService.dataSource` (computed) → component-level project/spec signals (computed) → template re-render. This cascade is synchronous for the signal flip and asynchronous only for the subsequent API fetch — meaning the UI updates its "loading" state instantly when auth changes, then resolves to real data when the API responds.

## Migration Path

The existing `app-v2.component.ts` at 1,087 lines is the primary decomposition target. Its current responsibilities split across the new components as follows: route shell logic → new root component, project grid orchestration → app page component, sidebar integration → removed, reader panel wiring → stays in reader panel, auth-aware rendering → moves to `DemoAwareProjectsService`.

The existing `app.routes.ts` already defines routes including `/v2`, `/playground`, `/signup`, and others. The migration replaces this route table entirely: three routes plus a wildcard. Components associated with removed routes (`components/login`, `components/upgrade`, `pages/signup`, `pages/public-spec`) are deleted. Their backend endpoints remain.

The existing `playground-demo-data.ts` informs but does not become the demo fixtures. Its data is shaped for playground component demos, not for product showcase. New demo fixtures are authored with realistic project names, plausible braindumps, and pre-generated spec content that reads as a genuine product demonstration.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| V2 component decomposition introduces regressions | Medium | High | Task 5 (strip dead pages) runs last, after app page is verified working. Build verification (`ng build --configuration production`) gates every task. |
| Mock data feels fake and undermines demo credibility | Medium | Medium | Curate fixtures from real spec-doc output. Use actual project names and realistic braindump content. Two to three projects, not ten. |
| Signal reactivity causes double-render on auth transition | Low | Low | The flash between mock → loading → real is one render cycle. A `loading` signal in `DemoAwareProjectsService` suppresses intermediate states. |
| Playground breaks after sidebar removal | Low | High | Playground components don't depend on sidebar. They're self-contained with their own demo data. Route-level isolation confirms this — playground already works at its own route. |

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking