The document is ready. Here's the complete **Solution Architecture: Unified Page** document:

---

# 🏗️ Solution Architecture: Unified Page

## Architecture Overview

The unified page is a compositional merge of three existing surfaces — the static landing pitch, the static design playground, and the live Angular app — into a single Angular template rendered at `/`. No new features are introduced. No new backend routes are created. The work is entirely structural: decompose static HTML into Angular standalone components, compose them with the existing signal-driven app shell, and use auth state to conditionally render the landing pitch for anonymous visitors.

The key architectural insight is that the design playground's 2,304 lines of static HTML already contain every visual decision — grid layouts, section proportions, newspaper-style typography tokens, dark-mode variables, responsive breakpoints. The Angular app already contains every behavioral decision — project signals, polling service, markdown rendering, API integration. Neither needs to be rebuilt. The architecture's job is to define the seam where visual structure meets live data: playground HTML becomes the layout skeleton, Angular signals fill it with real content.

The current Angular app has no router — it is a single-view shell where `app.component.ts` holds all state as signals and navigation is driven by setting `activeProject` and `activeSpec`. This architecture preserves that pattern. The unified page does not introduce Angular Router. Instead, it introduces a top-level view-state signal that distinguishes between `landing` (anonymous) and `workspace` (authenticated) modes. The page does not route between views — it reveals or hides sections based on auth state. This matches the braindump's core philosophy: auth state is a UI variable, not a routing decision.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | Auth state flows through a single `AuthService` that wraps JWT token management. No component reads `localStorage` directly for auth. |
| P4 — No Speculative Abstractions | Each playground section becomes exactly one Angular component. No generic "section renderer" or "layout engine." Five concrete components for five concrete sections. |
| P7 — File Size and Structure | The 2,304-line playground is decomposed into standalone components each under 200 lines. One component per file. Named exports only. |
| P2 — Thin HTTP Layer | No new backend routes. The frontend consumes existing `/api/auth/me` and `/api/projects` endpoints. Auth-conditional rendering is purely a frontend concern. |
| Signal-First State | View state (`landing` vs `workspace`), project list, active spec — all signals. No new observables. `computed()` derives visibility flags from auth state. |
| Composition Over Rewrite | The unified template imports existing components and playground-derived components. `app.component` is not rewritten — `app-v2` composes alongside it, then replaces it. |

## Component Design

### AuthService

**Purpose**: Single source of truth for authentication state on the frontend.

This is the only new service introduced. It owns the JWT token lifecycle — reading from `localStorage`, validating expiry, exposing an `isAuthenticated` signal, and providing the current user's identity. Every auth-dependent rendering decision in the unified template reads from this service's signals, never from raw storage.

The service exposes three signals: `isAuthenticated` (boolean, derived from token presence and expiry), `currentUser` (the `/api/auth/me` response or `null`), and `authLoading` (true while the initial token validation request is in flight). On app bootstrap, the service checks for a stored token, hits `/api/auth/me` to validate it, and resolves `isAuthenticated`. If the token is missing or expired, the signal resolves to `false` with no error — the page simply renders in anonymous mode.

This service does not handle login or registration flows. Those remain redirect-based as they are today. The service's only job is to answer: "right now, is the visitor authenticated, and if so, who are they?"

### Playground Layout Components (Task 1)

**Purpose**: Decompose the monolithic playground HTML into importable Angular standalone components that preserve the playground's visual design as the layout foundation for the real app.

The playground HTML contains five distinct layout zones. Each becomes a standalone Angular component:

**ProjectGridComponent** — The newspaper-style project card grid. In the playground this is static mockup cards. In the unified page, this component receives the real `projects` signal and renders actual project summaries using the playground's grid CSS classes. It is the primary content area for authenticated users and the visual centerpiece for anonymous visitors (showing example/placeholder cards).

**ReaderPanelComponent** — The expanded document reader that displays rendered markdown when a project spec is selected. In the playground this shows static lorem content. In the unified page, it binds to `activeSpec` and renders real markdown through the existing `marked` + `DOMPurify` pipeline. The panel uses the playground's proportional layout (width ratios, padding, typography) as-is.

**SidebarComponent** — The left-hand navigation rail showing the project file tree and section links. In the playground this is a static list of filenames. In the unified page, it binds to `activeProject.specs` and renders the real file list. Selection events update `activeSpec` through the existing signal flow.

**StatusBarComponent** — The bottom status strip showing generation progress, job state, and system status. In the playground this displays static status text. In the unified page, it binds to the polling signals (`bootstrapProgress`, `currentStep`) and shows real-time generation feedback.

**SectionNavComponent** — The top navigation tabs or breadcrumb-style section indicators (analysis, epic, architecture, timeline). In the playground these are static labels. In the unified page, they bind to the active project's available specs and allow switching between spec documents.

Each component's template is a direct extraction from the playground HTML — same CSS classes, same grid areas, same design tokens. The only change is replacing static content with signal bindings (`{{ signal() }}`) and static lists with `@for` loops. The playground's SCSS is split per-component into each component's `.scss` file, with shared design tokens (CSS custom properties for typography scale, spacing rhythm, color palette, dark-mode overrides) promoted to `styles.scss` as global variables.

### LandingPitchComponent (Task 2)

**Purpose**: Extract the hero and pitch content from the static landing page into a standalone Angular component that can be conditionally rendered in the unified template.

This component contains the product headline, value proposition copy, and call-to-action that currently live in `landing/index.html`. It is a presentational component with no signals, no service dependencies, and no interactivity beyond a "Get Started" link that scrolls to the workspace section of the unified page (or triggers the auth redirect for signup).

The component preserves the landing page's existing CSS — fonts, spacing, background treatment, responsive breakpoints. It does not import or depend on the playground's design tokens; the landing pitch has its own visual identity that sits above the product interface.

This component is extracted independently of the playground decomposition (Task 1) and can be built in parallel. Its only integration point is the unified template, where it occupies the top section of the page for anonymous visitors.

### UnifiedPageComponent — `app-v2` (Task 3)

**Purpose**: The composition root that arranges all components — landing pitch, playground-derived layout, and existing app signals — into a single template on a staging route.

This is the architectural centerpiece. It does not contain business logic. It imports `AuthService` for the `isAuthenticated` signal, imports `ProjectsService` for data operations, and arranges child components in a template.

The top zone renders `LandingPitchComponent` when `isAuthenticated()` is `false`. Below it (or replacing it for authenticated users), the main workspace zone renders the playground-derived layout: `SidebarComponent` on the left, `ProjectGridComponent` or `ReaderPanelComponent` in the center (depending on whether a project is selected), `SectionNavComponent` above the reader, and `StatusBarComponent` at the bottom.

The critical composition decision is where state lives. Today, `app.component.ts` holds all signals. In the unified architecture, those signals migrate to `app-v2.component.ts` — not to a shared service, not to a state store. The unified component is the new root, and it owns the same signals that `app.component.ts` currently owns: `projects`, `activeProject`, `activeSpec`, `loading`, `error`, `bootstrapProgress`, `currentStep`. Child components receive these as inputs or read them from injected services.

The staging strategy is: `app-v2` initially coexists alongside the current `app.component` as an alternative entry point. The Angular bootstrap configuration in `app.config.ts` is updated to render `app-v2` instead of `app.component`. This is a single-line change — swap the bootstrap component. The old `app.component` files remain in the codebase until the cutover is validated, then are deleted in a cleanup pass.

### Auth-Conditional Rendering (Task 4)

**Purpose**: Use the `AuthService.isAuthenticated` signal to control which sections are visible to anonymous vs authenticated visitors.

The rendering logic is minimal. The unified template uses `@if (authService.isAuthenticated())` to gate sections:

Anonymous visitors see: `LandingPitchComponent` at the top, followed by the full playground-derived layout populated with placeholder/example content. The project grid shows example cards (hardcoded in the component, not fetched from the API). The reader panel shows a sample spec document. The sidebar shows sample file names. This gives visitors a taste of the product's visual design without requiring backend calls or live data.

Authenticated users see: No landing pitch (the `@if` block excludes it). The playground-derived layout populated with real data from `ProjectsService`. The project grid shows their actual projects. The reader panel shows real spec content. The sidebar shows real file lists.

The transition between these states is not animated (per epic scope). If the user authenticates via the existing redirect flow and returns to `/`, the page simply renders in authenticated mode. There is no morph, collapse, or slide transition — that is explicitly deferred to a future polish pass.

One subtlety: while `authLoading` is `true` (the initial `/api/auth/me` call is in flight), the page should render neither the anonymous nor the authenticated view. A brief loading skeleton or spinner in the top zone prevents a flash of landing-pitch content for returning users whose token is valid but not yet verified. This is a single `@if (authService.authLoading())` guard wrapping the conditional block.

### Route Cutover (Task 5)

**Purpose**: Promote `app-v2` to the root entry point and retire the old separate-route architecture.

Since the Angular app currently has no router, "route cutover" means: change the bootstrap component in `app.config.ts` from `AppComponent` to `UnifiedPageComponent`. The static landing page served by nginx at `/` is retired — nginx now proxies `/` to the Angular dev server (or serves the Angular build artifacts in production). The `/app` path, if it existed as a separate nginx location, redirects to `/`.

This is the lowest-risk step because it is purely a configuration change. If the unified page has a critical bug post-cutover, reverting is a single-line change back to `AppComponent` in the bootstrap config.

The static `landing/index.html` and `landing/playground.html` files are not deleted. They remain as reference artifacts. The nginx configuration is updated to serve the Angular SPA for all paths, with API routes proxied to Flask as before. The landing page's SEO meta tags (title, description, OG tags) move into `index.html` of the Angular app — the Angular build's `index.html` becomes the single entry point for crawlers and users alike.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Component Framework | Angular 17+ standalone components | Matches existing app. Standalone components require no NgModule declarations — each playground section is self-contained. |
| State Management | Angular signals (`signal`, `computed`, `effect`) | Already the pattern in `app.component.ts`. No new state library. No observables for component state. |
| Auth State | New `AuthService` with signal-based `isAuthenticated` | Wraps existing JWT + `/api/auth/me` endpoint. Single source of truth for conditional rendering. |
| HTTP | Existing `ProjectsService` | No new service for data. Auth check uses `HttpClient` via `AuthService` only. |
| Styling | Playground CSS classes + CSS custom properties | Playground's 2,304 lines of CSS are the design system. Tokens extracted to `styles.scss` globals; component styles stay in `.component.scss` files. |
| Markdown | Existing `marked` + `DOMPurify` | Already in `package.json`. Reader panel reuses the same rendering pipeline. |
| Template Syntax | `@if` / `@for` (Angular 17+ control flow) | Required by conventions. No `*ngIf` / `*ngFor`. |
| Testing | Jasmine + Karma (unit), pytest-bdd + Playwright (E2E) | Existing test infrastructure. Each new component and service gets a `.spec.ts` and `.mock.ts`. |
| Backend | No changes | Zero new routes, zero new services. This epic is frontend-only. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| No Angular Router introduced | The current app is routerless — navigation is signal-driven. Adding a router for one conditional section (landing pitch) would introduce routing infrastructure for a problem solved by a single `@if` block. Router adds bundle size, route guards complexity, and a navigation model that contradicts the "one page" philosophy. | Deep-linking to `/#projects` or `/#playground` is not possible without a router or manual `location.hash` handling. Deferred — hash-based scrolling can be added later without a full router. |
| Auth state as a signal, not a route guard | Route guards require Angular Router. Since we have no router, auth-conditional rendering is a template concern: `@if (isAuthenticated())`. This keeps auth simple — a boolean signal, not a navigation interceptor. | If the app later grows to need protected routes (settings page, admin panel), a router with guards would need to be introduced at that point. For now, one page means one guard is overkill. |
| Signals stay in the unified component, not a shared store | Moving signals to an injectable state service (or NgRx) would be premature abstraction for a single-consumer app. The unified component owns its signals just as `app.component.ts` does today. Child components receive data via `@Input()` signals or read from `ProjectsService`. | If a second top-level view is ever added, signal ownership would need to be lifted into a service. P4 says: build for the one concrete case that exists now. |
| Playground CSS split per-component, tokens promoted globally | Each component owns the subset of playground CSS that styles its section. Shared values (typography scale, color palette, spacing rhythm, dark-mode custom properties) become CSS custom properties in `styles.scss`. This avoids a single monolithic stylesheet while keeping the design system coherent. | Some duplication of grid-area declarations may occur at component boundaries. Acceptable — three similar lines of CSS is better than a premature layout abstraction (P4). |
| Placeholder content for anonymous visitors, not live data | Anonymous visitors see hardcoded example project cards and sample spec content — not real API data. This avoids unauthenticated API calls, avoids exposing other users' data, and avoids the complexity of a public demo feature (explicitly out of scope). | The anonymous experience is static, not interactive. Visitors see what the product looks like, not what it does with their data. A live anonymous demo is a separate epic with backend implications. |
| `app-v2` as staging component, then bootstrap swap | Creating a new component rather than modifying `app.component` in place allows side-by-side comparison during development. The cutover is a single-line bootstrap config change, and rollback is equally trivial. | Two near-identical component trees exist briefly during validation. The old `app.component` files must be cleaned up after cutover to avoid confusion. |
| No animation on auth-state transition | The epic explicitly excludes animated section transitions. The pitch section appears or disappears via `@if` with no collapse, fade, or morph. This keeps the implementation focused on correctness. | The transition from anonymous to authenticated (after redirect return) may feel abrupt. Acceptable for initial ship — animation is a polish concern, not an architecture concern. |
| Static landing page files retained as reference | `landing/index.html` and `landing/playground.html` are not deleted post-cutover. They serve as the canonical reference for what the components were extracted from, useful for debugging visual regressions. | Stale reference files can drift from the live components over time. Mitigated by the fact that these files are never served after cutover — they are inert artifacts. |
| `AuthService` is the only new service | All other data operations use the existing `ProjectsService`. Introducing `AuthService` is justified because auth state is a cross-cutting concern that the unified template's conditional rendering depends on, and no existing service exposes an `isAuthenticated` signal. | One more file in `services/`. Acceptable — it serves a concrete, non-duplicated purpose. |

## Data Flow

The unified page's data flow is straightforward because no new backend integration is introduced.

**Bootstrap sequence**: Angular app loads. `AuthService` checks `localStorage` for a JWT token. If present, it calls `GET /api/auth/me` to validate the token and populate `currentUser`. The `isAuthenticated` signal resolves to `true` or `false`. The unified template renders accordingly.

**Authenticated flow**: `UnifiedPageComponent.ngOnInit()` calls `ProjectsService.listProjects()`. The `projects` signal populates. `ProjectGridComponent` renders the list. User clicks a project card, `activeProject` signal updates, `SidebarComponent` renders the file list, user clicks a spec file, `activeSpec` signal updates, `ReaderPanelComponent` renders the markdown. This is identical to the current `app.component` flow — the signals and service calls are the same, only the template layout changes.

**Anonymous flow**: `UnifiedPageComponent.ngOnInit()` skips the `listProjects()` call (guarded by `isAuthenticated()`). `LandingPitchComponent` renders at the top. The playground-derived layout renders below with hardcoded placeholder content. No API calls are made. The "Get Started" CTA links to the existing auth redirect.

**Braindump submission**: Unchanged. The `submitBraindump()` method calls `ProjectsService.bootstrap()`, receives a `job_id`, and polls `GET /status/{job_id}` via `setInterval` until `done: true`. The `StatusBarComponent` reads `bootstrapProgress` and `currentStep` signals to show real-time feedback. On completion, the new project appears in the `projects` signal and the grid updates. This flow only activates for authenticated users.

## Component Hierarchy

The composition tree for the unified page:

`UnifiedPageComponent` (root) — owns all signals, orchestrates child components
-- `LandingPitchComponent` (conditional: anonymous only) — presentational, no signals
-- Layout Shell (playground-derived CSS grid, defined in UnifiedPageComponent template)
---- `SidebarComponent` (left rail) — inputs: `activeProject`, `activeSpec`; outputs: spec selection events
---- `SectionNavComponent` (top bar) — inputs: available specs for active project; outputs: spec type selection
---- `ProjectGridComponent` or `ReaderPanelComponent` (center) — toggled by `activeProject` signal presence
---- `StatusBarComponent` (bottom strip) — inputs: `bootstrapProgress`, `currentStep`, `loading`

The Layout Shell is not a separate component — it is a `<div>` with the playground's CSS grid classes directly in the `UnifiedPageComponent` template. Wrapping a grid container in its own component would add a layer of indirection with no behavioral benefit. The grid is the template; the sections within it are the components.

## File Structure (Target State)

After all five tasks are complete, the Angular app directory adds these files:

`services/auth.service.ts` — AuthService (signal-based auth state)
`services/auth.service.spec.ts` — AuthService unit tests
`services/auth.service.mock.ts` — Mock factory for AuthService

`components/landing-pitch/landing-pitch.component.ts` — Hero and pitch extraction
`components/landing-pitch/landing-pitch.component.html` — Pitch template
`components/landing-pitch/landing-pitch.component.scss` — Pitch styles

`components/project-grid/project-grid.component.ts` — Project card grid
`components/project-grid/project-grid.component.html` — Grid template
`components/project-grid/project-grid.component.scss` — Grid styles

`components/reader-panel/reader-panel.component.ts` — Document reader
`components/reader-panel/reader-panel.component.html` — Reader template
`components/reader-panel/reader-panel.component.scss` — Reader styles

`components/sidebar/sidebar.component.ts` — File tree navigation
`components/sidebar/sidebar.component.html` — Sidebar template
`components/sidebar/sidebar.component.scss` — Sidebar styles

`components/status-bar/status-bar.component.ts` — Generation status
`components/status-bar/status-bar.component.html` — Status template
`components/status-bar/status-bar.component.scss` — Status styles

`components/section-nav/section-nav.component.ts` — Spec type tabs
`components/section-nav/section-nav.component.html` — Nav template
`components/section-nav/section-nav.component.scss` — Nav styles

`app-v2.component.ts` — Unified page (composition root)
`app-v2.component.html` — Unified template
`app-v2.component.scss` — Unified layout styles (grid shell and shared spacing)

Each component file stays under 200 lines. The template files are the densest — extracted playground HTML with signal bindings — but the extraction boundaries are chosen specifically to keep each under the limit.

## Risk Mitigation

**Visual regression during extraction**: The playground HTML is a tested, coherent design. Decomposing it into components risks breaking CSS specificity chains, grid-area relationships, or responsive breakpoints that depend on parent-child nesting. Mitigation: extract one section at a time, visually verify each extraction against the original playground in the browser before moving to the next. The static playground file remains as the visual reference throughout.

**Signal ownership confusion**: Moving signals from `app.component.ts` to `app-v2.component.ts` creates a period where both components exist with overlapping state. Mitigation: `app-v2` is developed as a complete replacement, not a partial overlay. During development, only one component is bootstrapped at a time — toggled via the `app.config.ts` bootstrap array. There is no period where both are live simultaneously.

**Auth flash on page load**: If the `AuthService` token validation takes perceptible time, authenticated users may briefly see the anonymous landing pitch before it disappears. Mitigation: the `authLoading` signal gates the entire conditional block. While loading is `true`, neither the pitch nor the workspace renders — a minimal loading skeleton displays instead.

**Placeholder content staleness**: Hardcoded example cards for anonymous visitors may drift from the real product's data shape over time. Mitigation: example data is defined as a constant array in `ProjectGridComponent`, using the same `ProjectSummary` interface as real data. Type checking ensures the examples stay structurally valid even as the interface evolves.

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking and delivery milestones