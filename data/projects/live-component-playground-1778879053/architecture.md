Now I have enough context from the codebase to write a well-grounded architecture document. Let me produce it.

# 🏗️ Solution Architecture: Live Component Playground

## Architecture Overview

The live playground is a single routable Angular page that replaces a 2,304-line static HTML artifact with a composition of every V2 sub-component rendered with real Angular signals and hardcoded demo data. The mental model is a "component showroom" — one scrollable page organized into labeled sections, where each section instantiates a production sub-component with the same input bindings the real application uses, but fed by local signals instead of service calls. This means the playground is both a visual demo and an implicit integration test: if a sub-component's input contract changes, the playground breaks at compile time.

The key architectural insight is that this page must be completely self-contained. It makes zero HTTP calls, requires no authentication, and loads no data from the Flask API. Every signal, computed property, and event handler lives within the playground component and its dedicated demo data files. This isolation is what makes it safe to use as a public-facing demo and what differentiates it from the real application shell. The trade-off is obvious — the demo data will drift from reality over time — but the benefit is that the playground always works, for every visitor, regardless of backend state.

Component composition follows the existing Angular conventions: standalone components imported directly, signals for all state, computed properties for derivations, and `@if`/`@for` control flow in the template. The playground introduces one new capability the existing app lacks — a routable page — which requires adding Angular Router configuration. Since the current app uses signal-based navigation without a router, this is the first route definition in the project and establishes the pattern for future route additions.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | One playground component with one template. No generic "demo wrapper" or "section renderer" abstraction. Each section is a direct sub-component binding in the template. |
| P7 — File Size and Structure | The playground component file stays under 200 lines by extracting all demo data (projects, specs, section metadata) into dedicated constant files. The template file has no line limit but is organized with HTML comments marking each section boundary. |
| P1 — Adapter Boundary | The playground imports no services. It never touches `ProjectsService` or `HttpClient`. All data flows from imported constants through local signals — no adapter needed because there are no external calls. |
| P2 — Thin HTTP Layer | Not applicable. This is a pure frontend feature with zero backend involvement. No new API endpoints, no new routes in Flask, no changes to `openapi.yaml`. |
| Signal Reactivity Convention | All playground state expressed as `signal()` and `computed()` per Angular conventions. No `BehaviorSubject`, no `Observable` pipelines. Template reads signals as function calls. |

## Component Design

### LivePlaygroundComponent

**Purpose**: The single orchestrator that composes all V2 sub-components on one scrollable page. It owns demo signals, handles user interactions within the playground (tab clicks, file selection, dark mode toggle), and delegates rendering entirely to the existing sub-components.

**Structural approach**: The component class declares demo signals initialized from imported constants. Computed properties derive filtered views, section counts, and parsed markdown from those signals. Event handler methods respond to output events from sub-components by updating the appropriate signal. The class contains no business logic, no HTTP calls, and no lifecycle hooks beyond what Angular requires for signal initialization.

**Template organization**: The HTML template is divided into clearly labeled sections — Section Nav, Status Bar (all four states), Project Grid, Sidebar, Reader Panel, Landing Pitch, Create Modal trigger, and Dark Mode toggle. Each section has a visible heading so a visitor scrolling the page understands what they are looking at. The status bar section is unique in that it renders four instances of the same component with different mode inputs to showcase all visual states simultaneously.

### Demo Data Files

**Purpose**: Isolate hardcoded constants so the playground component stays under 200 lines and demo data is easy to update independently.

**Structure**: Two or three TypeScript files exporting named constants. One file for demo projects (eight projects distributed across all four sections with realistic names and dates). One file for demo specs keyed by filename (to support the sidebar-to-reader binding — clicking "architecture.md" in the sidebar loads the architecture demo spec content into the reader panel). One file for section metadata (section names, counts, pulse states). All constants conform to the existing `Project`, `Spec`, `SpecSummary`, and `SpecDetail` interfaces from the app's type definitions.

**Data realism**: Demo project names should suggest real software capabilities (not "Test Project 1"). Demo spec content should be valid markdown of sufficient length to demonstrate the newspaper layout in the reader panel — at least three headings, a table, and a bullet list. This matters because the playground is the product's demo reel for new users; lorem ipsum signals "prototype."

### Sidebar-to-Reader Binding

**Purpose**: Demonstrate that clicking a file in the sidebar updates the reader panel, proving the two components work together.

**Mechanism**: The playground holds a `demoActiveFile` signal. When `SidebarV2Component` emits a file-selected output event, the handler sets `demoActiveFile` to the new filename. A computed property looks up the corresponding demo spec from a keyed map and produces the parsed HTML via `marked` and `DOMPurify`. The `ReaderPanelComponent` receives this computed value as its parsed content input. This is the same data flow the real app uses, just with the service layer replaced by a static lookup.

### Dark Mode Toggle

**Purpose**: A single control at the top of the page that switches the `data-theme` attribute on the document root between `light` and `dark`, causing all sub-components to re-render in the alternate theme simultaneously.

**Mechanism**: A boolean signal (`isDarkMode`) drives the toggle state. An effect or click handler sets `document.documentElement.setAttribute('data-theme', ...)` based on the signal value. This is the same mechanism the app already uses for theming — CSS custom properties scoped to `[data-theme="dark"]` in component SCSS files handle the rest. No per-component theme prop is needed.

### Create Modal (Display-Only)

**Purpose**: Show the create-project modal as a live, interactive form without actually creating a project.

**Mechanism**: A trigger button in the playground opens the existing create-project modal component. The form fields (name, braindump) accept input and show validation states. The submit handler is a no-op — it logs to console or briefly shows a success toast, but makes no API call and creates no project. This demonstrates the modal's UX without side effects.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | Angular 17+ (standalone components, signals) | Existing project stack. The playground is a new component within `web-ng/src/app/`, not a separate application. |
| Routing | Angular Router (new addition) | The app currently uses signal-based navigation without a router. The playground requires a routable URL (`/playground`). This is the minimal addition — a route config file with two entries (live playground and static fallback). |
| Markdown rendering | `marked` + `DOMPurify` | Already project dependencies per Angular conventions. The reader panel demo content must go through the same render pipeline the real app uses. |
| State management | Angular signals + computed | Convention-mandated. No external state library. All playground state is local to the component. |
| Styling | Component SCSS + CSS custom properties | Existing pattern. Dark mode toggle works through `[data-theme]` attribute already supported by all component stylesheets. |
| Backend | None | The playground makes zero API calls. No Flask changes, no new endpoints, no `openapi.yaml` modifications. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Hardcoded demo data only — no real API calls, even when authenticated | The epic analysis identified a contradiction between "real data when logged in" and "no real API calls, works without auth." Hardcoded-only eliminates auth-gating complexity, prevents the playground from breaking when the backend is down, and ensures every visitor sees the same polished demo regardless of their account state. | Demo data drifts from reality over time. New sections or project shapes added to the real app may not appear in the playground until someone manually updates the constants. Acceptable for a solo project where the builder controls both. |
| Introduce Angular Router for this feature | The current app has no router — navigation is signal-based. The playground needs a URL (`/playground`) because it is a standalone page, not a view within the existing project shell. Adding the router now creates one route config file with two entries. | Adds a new dependency (Angular Router is bundled but not yet configured). Future features may need to reconcile the existing signal-based navigation with router-based navigation. However, the playground routes are leaf pages with no nesting, so they coexist cleanly with the signal-based main app. |
| Four simultaneous status bar instances instead of a cycling demo | Rendering all four states (idle, active, success, failure) at once lets a visitor compare them side-by-side without waiting for a timer or clicking through a carousel. It is visually denser but communicates more information in less time. | Uses more vertical space. A cycling demo would be more compact but hides three states at any given moment, defeating the purpose of a visual reference. |
| Old static playground preserved at `/playground-static` | The static HTML playground is a 2,304-line design artifact that documents CSS token application. It has historical value as a pixel reference even after the live playground replaces it for functional demonstration. | Two playground routes to maintain. Mitigation: the static playground requires zero maintenance — it is a frozen HTML file loaded via DOMParser and will continue working indefinitely. |
| UsageMeterComponent excluded | Referenced in the braindump's import list but has no defined section, no demo data strategy, and no success criteria in the epic. Including it would mean inventing a scope that was never specified. | If a usage meter demo is needed later, it can be added as a new section with its own demo data constants. The playground template's section-based organization makes this a localized addition. |
| Demo data in separate files, not inline | The 200-line file limit (P7) makes it impossible to define eight demo projects with full spec content inside the component class. Extracting to dedicated files also makes the demo data independently reviewable and updatable. | More files to maintain (two or three data files plus the component). Acceptable because each file has a single clear purpose and the total count stays small. |
| Create modal is display-only with no-op submit | Real project creation would pollute the user's project list and require authentication. Real Stripe flows are permanently out of scope for a demo page. A no-op submit demonstrates the modal UX without side effects. | The "Generate" button does not actually generate. A visitor might find this confusing. Mitigation: the button can show a brief "Demo mode — no project created" message on click. |

## Data Flow

The playground's data flow is intentionally one-directional and local. Demo constants are imported at module level and fed into signals at component initialization. User interactions (clicking a tab, selecting a file, toggling dark mode) update a signal, which triggers computed properties to re-derive downstream values, which Angular's change detection propagates to the sub-component inputs. No data leaves the component. No data enters from outside the component.

The sidebar-to-reader binding is the most interesting data flow: `SidebarV2Component` emits a filename string via its output event. The playground's handler sets the `demoActiveFile` signal to that filename. A computed property uses the filename as a key into a `Record<string, DemoSpec>` map imported from the demo data file, producing the matching spec. A second computed property pipes the spec's markdown content through `marked.parse()` and `DOMPurify.sanitize()` to produce safe HTML. The `ReaderPanelComponent` receives this HTML as its parsed content input. The entire chain — from click to rendered markdown — is reactive via signals with no imperative wiring.

## Routing Strategy

The route configuration introduces Angular Router with exactly two playground routes and preserves the existing signal-based navigation for the main application. The router is configured at the application level with these entries:

- `/playground` — resolves to the new `LivePlaygroundComponent`
- `/playground-static` — resolves to the existing `DesignPlaygroundComponent`
- Default/fallback — resolves to the existing `AppComponent` shell (the main application)

This approach means the main app continues to work exactly as it does today — the router simply wraps it as the default route. The playground pages are siblings, not children, of the main app. Navigation links in the landing page or main app that previously pointed to the static playground must be updated to point to `/playground`.

## File Organization

All new files live under `web-ng/src/app/` following the project's flat structure convention:

- **Playground component**: component class, HTML template, and SCSS file in a `live-playground/` directory
- **Demo data**: two to three TypeScript files in the same directory, each exporting named constants
- **Route config**: a new `app.routes.ts` file at the `app/` level defining the route table
- **No new services, no new modules, no new shared utilities**

The existing `DesignPlaygroundComponent` files remain in place but their route changes from `/playground` to `/playground-static`. No files are deleted.

## Dependency Verification

Before implementation begins, the following must be confirmed:

- All six sub-components (`SectionNavComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `LandingPitchComponent`) are standalone components with stable `@Input`/`@Output` contracts
- `marked` and `DOMPurify` are listed in `package.json` (the Angular conventions document confirms both are in use, but version compatibility should be verified)
- The `Project`, `Spec`, `SpecSummary`, and `SpecDetail` TypeScript interfaces are exported and importable from the types or models location
- The create-project modal component exists and is standalone-importable
- CSS custom properties for dark mode are already defined in component SCSS files scoped to `[data-theme="dark"]`

Any missing dependency discovered during Task 1 must be resolved before demo data authoring begins in Task 2.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sub-component input contract is unstable or undocumented | Medium | High — blocks playground composition | Task 1 explicitly verifies all contracts before proceeding. Any unstable component is flagged and either stabilized or excluded. |
| Adding Angular Router breaks existing signal-based navigation | Low | High — regression in the main app | The router wraps the existing app as the default route. Signal-based navigation inside `AppComponent` continues to work because signals operate independently of the router. Manual verification required. |
| Demo data files push total new-file count higher than expected | Low | Low — more files but each under 200 lines | Acceptable per P7. The alternative (inline data) violates the line limit. |
| `ng build --configuration production` fails with new imports | Low | Medium — blocks delivery | Build verification is a success criterion. Run `ng build` after every task, not just at the end. |

## Related Documents

- [Analysis](./analysis.md) — Problems and drift risks driving the replacement of the static playground
- [Epic](./epic.md) — Scope definition, task breakdown, and success criteria for the live playground
- [Timeline](./timeline.md) — Delivery milestones and task status tracking