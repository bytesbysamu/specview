# 🏗️ Solution Architecture: V3 + Cleanup — State Extraction, Tests, Deletion

## Architecture Overview

This refactor replaces two near-identical god components (V1 at 1,189 lines, V2 at 1,087 lines) with a single injectable state service and a thin rendering shell. The key architectural insight is that both V1 and V2 are the same application — identical signals, identical methods, identical computed properties — wrapped in slightly different template structures. The "component" isn't really a component at all; it's an application state machine that happens to live inside an Angular class decorator. Extracting it into a service makes that truth explicit.

The resulting architecture has three layers. At the bottom, `AppStateService` owns every signal, computed property, method, and effect that V2 currently holds — roughly 40 signals, 15 computed properties, 30 methods, and 3 effects totaling approximately 400 lines. In the middle, a V3 shell component (under 30 lines of TypeScript) injects the service and binds its template to `state.x()` calls. At the top, the existing five sub-components (project-grid, reader-panel, sidebar-v2, status-bar, section-nav) continue to receive data via inputs and emit events — completely unaware of the refactor above them.

The CSS consolidation follows the same philosophy: scoped styles in `landing-pitch` duplicate global tokens under `--lp-*` prefixes, creating a maintenance fork. Extracting shared design tokens into one canonical file and switching to unscoped encapsulation collapses that fork. The result is a single source of truth for every visual primitive — color, typography, spacing — imported by both the application stylesheet and the landing page stylesheet.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | AppStateService becomes the adapter between raw HTTP services (projects, ai, subscription) and the UI. No component ever calls ProjectsService directly for state-mutating operations — it flows through AppStateService methods that coordinate signals. |
| P2 — Thin HTTP Layer | V3 shell is the UI equivalent of a thin route handler: inject service, bind template, return pixels. Zero business logic in the component class. |
| P4 — No Speculative Abstractions | AppStateService ships as one ~400-line file. No premature split into "ProjectStateService" + "AIStateService" + "UIStateService." Split only when testing or reasoning pain emerges — not before. |
| P7 — File Size & Structure | The 400-line service is the largest file in the app and intentionally at the boundary. V3 shell stays under 50 lines. Utility extractions (paragraph-diff, nav-sections) keep helper logic in dedicated files under 50 lines each. |
| P7 — Build Verification | `ng build --configuration production` must pass at every phase boundary: after service extraction, after test migration, after route cutover, and after deletion. |

## Component Design

### AppStateService

**Purpose**: Single injectable that owns all application state, derived state, mutation methods, and side effects. Eliminates the impossibility of testing state logic without rendering a full component tree.

AppStateService is a root-provided Angular service using signals (not observables, not NgRx). It injects three HTTP services — ProjectsService, AiService, and SubscriptionService — and exposes reactive state to any consumer. The service manages the full lifecycle: loading projects, selecting files, running AI operations, handling polling for long-running spec generation, managing undo/redo stacks, and coordinating the generate-from-braindump workflow.

The three effects (auth state watcher, elapsed timer for spec generation, section count pulse animation) move into the service constructor using Angular's `effect()` API. They run in injection context, which means they activate when the service is first injected and clean up when the injector is destroyed — identical lifecycle to their current behavior inside the V2 component.

The service does not manage routing or navigation — those remain in the shell component because they depend on Angular Router injection at the component level. The service exposes a `navigateToUpgrade` callback that the shell wires to the router.

### V3 Shell Component

**Purpose**: Pure rendering adapter — translates service signals into template bindings with zero orchestration logic.

The shell injects AppStateService, AuthService, and SubscriptionService. Its TypeScript body contains only inject calls and static constant references (NAV_SECTIONS, CONTEXT_FILES, STYLE_PRESETS). Every template expression reads from `state.someSignal()` or calls `state.someMethod()`. The template itself is V2's existing template with the binding prefix changed from direct signal access to service-prefixed access.

The shell reuses V2's five sub-components without modification. Those sub-components receive data through inputs and emit events through outputs — they never knew they were talking to a god component, and they won't know they're now talking to a thin shell backed by a service.

### Utility Extractions

**Purpose**: Remove pure functions and static data from the service to keep it focused on state coordination.

`paragraph-diff.ts` extracts the diff computation — a pure function that takes two strings and returns HTML. It has no dependency on signals or services and is independently testable with string-in-string-out assertions.

`nav-sections.ts` extracts the static section definitions and context file mappings — configuration data that never changes at runtime. Keeping these as named constant exports means they're importable by both the service and the shell without circular dependency concerns.

### CSS Token Layer

**Purpose**: Eliminate the forked token system where `landing-pitch` maintains parallel `--lp-*` variables that shadow global `--ink`, `--bg`, etc.

A new `shared/tokens.css` file (~50 lines) becomes the single canonical definition for all design tokens. Both `styles.css` and `landing/style.css` import it. The `landing-pitch` component switches to `ViewEncapsulation.None` and consumes global classes directly, allowing its 401-line scoped stylesheet to be deleted entirely.

The dead-class audit of `styles.css` removes approximately 200 lines of classes that V1 referenced but no surviving component uses. The audit methodology is mechanical: grep each class name against every active template file; zero matches means deletion.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| State management | Angular signals (no library) | Already in use across V2. Signals provide fine-grained reactivity without the ceremony of NgRx or the subscription management of RxJS subjects. A service holding signals is the simplest reactive pattern Angular 17 offers. |
| Component architecture | Standalone components | Already the project standard. V3 shell is standalone, injectable, tree-shakeable. No NgModule coordination required. |
| Test framework | Karma + Jasmine (unit), Playwright via pytest (E2E) | Existing infrastructure with 441 unit tests and 43 E2E scenarios. No framework migration — reuse what works. |
| Visual regression | Playwright screenshots | Lightweight pixel comparison without introducing a dedicated visual testing tool. Overlay at 50% opacity catches layout shifts, color changes, and spacing regressions. |
| CSS architecture | Global utility classes + shared token import | V2 already uses global classes exclusively. This refactor makes that explicit by removing the last holdout (landing-pitch scoped styles) and centralizing token definitions. |
| Build verification | `ng build --configuration production` | Tree-shaking and AOT compilation catch dead imports, circular dependencies, and template binding errors that unit tests miss. Required at every phase gate. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| One monolithic AppStateService (~400 lines) rather than multiple focused services | P4 — no speculative abstractions. There is exactly one consumer (V3 shell) and one behavior surface. Splitting prematurely creates coordination overhead, import tangles, and injection ceremony without reducing cognitive load for a solo developer. | The 400-line file is the largest in the app. If future features (playground real-data mode, additional AI operations) push it past 500 lines, a split becomes justified — but not before. |
| V3 shell reuses V2's template verbatim rather than redesigning | Zero-behavior-change constraint. Any template modification risks visual regression. The template is a known-good artifact; changing it conflates refactoring with redesign. | V3 inherits V2's template structure even if some patterns are suboptimal. Template improvements are future work after the soak period. |
| Route V3 at `/v3` first, then promote to `/` after test parity | De-risks the cutover. If V3 has a subtle rendering bug, users at `/` (V2) are unaffected. Promotion only happens after 441 unit tests + 34 E2E tests + screenshot parity confirm equivalence. | Adds a routing step and a 1-week soak period. Slower to reach full deletion, but eliminates the possibility of a broken production deploy requiring emergency rollback. |
| Keep `/v1` as escape hatch for 1 week after V3 promotion | Provides a zero-cost safety net. If a user reports a regression that V3's test suite missed, routing back to V1 is a one-line change. | Delays final deletion by 7 calendar days. The cost is carrying 1,774 lines of dead code for one additional week — acceptable for a solo developer who may not notice subtle regressions immediately. |
| Delete scoped CSS and switch to ViewEncapsulation.None rather than migrating tokens | The scoped CSS exists only because `landing-pitch` was initially built as an isolated component. Now that it lives inside the same SPA with the same global stylesheet, encapsulation creates duplication without providing isolation benefit. | Components using `ViewEncapsulation.None` can accidentally leak styles. Mitigated by the project convention that all V2+ components already use global classes — there's nothing to leak. |
| Extract tokens.css rather than inlining tokens in both stylesheets | Single source of truth. When a token value changes (e.g., `--ink` shifts from pure black to off-black), one edit propagates everywhere. Without extraction, the same token lives in `styles.css` and `landing/style.css` with no guarantee of synchronization. | Adds a build-time import dependency between `landing/style.css` and the app's `shared/tokens.css`. Since both are served from the same Nginx container, this is a file-path reference, not a network dependency. |
| Screenshot comparison rather than snapshot testing for visual parity | Screenshots catch what snapshot tests cannot: computed styles, layout shifts from removed CSS classes, z-index changes, and animation state. A pixel overlay is the most honest assertion that "V3 looks exactly like V2." | Screenshots are environment-sensitive (font rendering, viewport size). Mitigated by running both captures in the same Playwright session with identical viewport configuration. |
| Test migration is a mechanical find-replace, not a rewrite | The 48 pre-V3 tests already assert against signal reads and method calls (`component.activeProject()`, `component.loadProjects()`). Changing `component` to `service` preserves the assertion logic verbatim. Rewriting tests during a refactor is how regressions sneak in. | Tests inherit any structural weaknesses of the original test suite. Acceptable — improving test quality is orthogonal to this refactor. |

## Dependency Flow

AppStateService depends downward on three HTTP services (ProjectsService, AiService, SubscriptionService) and has zero upward dependencies. The V3 shell depends on AppStateService plus AuthService and SubscriptionService for template bindings that are authentication-aware or billing-aware. Sub-components depend only on their input/output contracts — they never import AppStateService directly.

This means future consumers (e.g., playground real-data mode) can inject AppStateService independently without pulling in the V3 shell or any rendering concern. The service is the stable center; components are disposable shells around it.

## Risk Mitigations

The primary risk is a subtle behavioral divergence between V2 (methods and signals living in the component) and V3 (methods and signals living in an injected service). Angular's dependency injection creates the service as a singleton at the root injector level, meaning signal initialization timing differs slightly from component-level construction. The mitigation is the three-gate verification: unit tests prove signal behavior, E2E tests prove user flows, and screenshots prove visual output. All three must pass before promotion.

The secondary risk is CSS deletion removing a class that a template references via dynamic class binding (e.g., `[class]="someExpression"`). Static grep catches literal class names but misses computed strings. The mitigation is running the full E2E suite after CSS deletion — any missing class manifests as a visual regression caught by screenshot comparison or a broken interaction caught by E2E assertions.

## Future Extension Points

After deletion completes, AppStateService becomes the foundation for two planned capabilities. First, the playground's "real data mode" can inject AppStateService alongside its existing demo data, toggling between `playground-demo-data.ts` fixtures and live service signals with a single boolean. Second, new AI operations (additional spec types, quality scoring, revision suggestions) wire into AppStateService as new methods without touching any component file — the shell's template adds a button, the service adds a method, and the existing AI adapter pattern handles the backend call.

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design: god components, untestable trapped state, 4,211 lines of duplication
- [Epic](./epic.md) — Scope, task breakdown, success criteria, and exclusions
- [Timeline](./timeline.md) — Phase sequencing and soak period tracking