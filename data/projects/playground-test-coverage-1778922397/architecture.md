# 🏗️ Solution Architecture: Playground & V2 Test Coverage

## Architecture Overview

This test suite is not a coverage exercise — it is a **migration contract**. The 135 new assertions formalize the behavioral surface of two untested layers: the six playground components that compose the design-system showcase, and the 1,087-line `app-v2.component` that orchestrates the entire workspace. Every test is written against the current component shape but designed for a specific future: V3's extraction of state into `AppStateService`. The architectural decisions here optimize for that one-move migration, not for abstract test purity.

The suite divides into three tiers by coupling strategy. **Tier 1** (utility and leaf components) tests pure logic with no component dependencies — `css-read.util`, `pg-borders`, `pg-tokens`, `pg-animations`. **Tier 2** (composition components) tests orchestration through shallow rendering — `pg-state-matrix` and `live-playground` declare child selectors valid via schema suppression rather than importing full component trees. **Tier 3** (app-v2 pre-extraction) tests signal and computed behavior through an all-mocks service layer, structured so every assertion maps one-to-one onto the future `AppStateService` interface. The tiers are independent and can be developed in parallel, but Tier 2 benefits from Tier 1 existing for failure attribution — when a composition test fails, leaf specs help isolate whether the bug is in the child or the parent.

The unifying design constraint is **zero modifications to production code**. These tests assert current behavior as-is. Any test that would require a refactor to make a component testable is out of scope — that refactor belongs to V3. This means the architecture must solve testability entirely through mock strategy, TestBed configuration, and DOM simulation rather than dependency injection changes or component API modifications.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | Tests never call real services. Every service dependency is replaced with a mock factory that returns controlled signals and observables. The mock is the test's adapter boundary. |
| P4 — No Speculative Abstractions | No shared test utilities beyond what already exists. Each spec file is self-contained. A `createMockProjectsService` factory is reused only because it already ships in the codebase — no new shared test infrastructure is created for 135 tests. |
| P7 — File Size & Structure | Every spec file lives flat beside its component file. No `test/` subdirectories, no barrel exports, no shared fixture files. Each spec is independently runnable and independently readable. |
| Pre-extraction contract | App-v2 tests are written as `component.signalName()` and `component.methodName()` assertions — not template-query assertions. This structure means the V3 migration is a find-and-replace from `component.` to `service.`, not a rewrite. |
| Behavioral fidelity | Tests assert what the user sees and what the signals compute — not how the implementation achieves it. Spying on internal methods is avoided unless the method is the unit under test. This keeps tests valid across refactors. |

## Component Design

### Tier 1 — Utility and Leaf Specs

**Purpose**: Establish a tested foundation for the three building-block components and one utility function that the rest of the playground depends on.

`css-read.util` is a single function that wraps `getComputedStyle`. Its spec validates the graceful-empty-value contract: callers receive a trimmed string or a `"not set"` sentinel, never `undefined` or an empty string. This contract is consumed by `pg-tokens` and must hold before token tests can trust their data source.

`pg-tokens` carries the most complex browser API interaction in the playground: a `MutationObserver` watching `document.documentElement` for attribute changes (dark mode toggle). The spec mocks the `MutationObserver` constructor, captures the callback, and triggers it manually to verify token re-reads. Lifecycle coverage ensures the observer disconnects on component destroy — a real memory leak vector.

`pg-animations` tests the replay reflow trick where removing and re-adding a CSS class requires a forced layout between the two operations. The spec spies on `classList` mutations and verifies the sequence (remove → property read → add) without asserting on actual animation rendering, which is untestable in JSDOM.

`pg-borders` is the simplest leaf — pure template rendering with CSS class application. Five assertions confirm the seven border demos render with correct classes and labels.

### Tier 2 — Composition Specs

**Purpose**: Test orchestration logic in `pg-state-matrix` and `live-playground` without pulling in the full component dependency tree.

`pg-state-matrix` renders demo data across every visual state the design system supports — five project card variants, five file-dot states, three section-nav configurations, and reader panel modes including access-denied and AI-diff. The spec validates that the component correctly maps demo data shapes to DOM output and that HTML content passes through `DOMPurify` sanitization. The sanitization assertion is the only security-relevant test in this epic.

`live-playground` is the playground's orchestrator: it wires eight demo projects through signals, computes filtered views, manages project selection and file navigation, and composes six child components. The spec uses schema suppression to avoid importing child component modules — child behavior is already covered by Tier 1 specs. Tests focus on signal computation (filtered projects, section counts, column calculation) and user interaction flows (select project → select file → close panel). Dark mode toggling is tested by asserting the `document.documentElement` attribute change, not by verifying CSS variable propagation.

### Tier 3 — App-v2 Pre-Extraction Suite

**Purpose**: Build the regression safety net that makes V3's `AppStateService` extraction a verifiable operation instead of a trust exercise.

The 48 pre-extraction tests are organized into five groups that mirror the planned service's interface: signal initialization (10 tests), computed derivations (10 tests), method behavior (15 tests), polling lifecycle (5 tests), and bootstrap pipeline (8 tests). Each group targets a specific category of logic that will move from the component class to the service class.

Signal initialization tests confirm default values — these catch constructor regressions during extraction. Computed value tests confirm derivation logic — `filteredProjects` filtering by section and search, `sectionCounts` aggregating correctly, `columns` computing from project count. These are the highest-value assertions because computed signals are the most fragile during extraction (they depend on other signals being wired correctly in the new host).

Method behavior tests confirm side effects — `selectProject` setting the right signals, `toggleTheme` updating both `localStorage` and the DOM, `applyResult` pushing to the undo stack. Polling and bootstrap tests confirm async lifecycle — start/stop triggers, retry counting, partial file saves during long operations.

The additional 15 basic behavior tests cover service injection verification, conditional template rendering (landing pitch vs. workspace), and navigation delegation. These overlap slightly with pre-extraction tests but serve a different purpose: they validate the component's role as a view controller even after V3 extracts its state logic.

### Mock Strategy

**Purpose**: Define the single approach to dependency replacement that all 135 tests follow.

Every external service is replaced with a mock that exposes writable signals and jasmine spies. The project already ships mock factories for `ProjectsService`, `AiService`, `AuthService`, and `SubscriptionService` — these are reused without modification. No new shared mock infrastructure is created.

For browser APIs, the approach varies by API surface. `getComputedStyle` is replaced via `spyOn(window, 'getComputedStyle')` returning controlled values — this is the only viable approach since JSDOM does not compute real CSS. `MutationObserver` is replaced by assigning a mock constructor to `window.MutationObserver` in `beforeEach` and restoring in `afterEach`. `localStorage` is replaced with a spy object since the component reads `isDark` from storage on initialization.

Child components in composition tests are handled exclusively through `NO_ERRORS_SCHEMA` — Angular's mechanism for telling the compiler to ignore unknown element selectors. This is a deliberate trade-off: shallow rendering means composition tests cannot verify input/output bindings to children, but it eliminates transitive dependency chains that would make TestBed configuration brittle and slow. The binding contract is tested from the other direction — child component specs verify their own input/output behavior.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Test runner | Karma + Jasmine (existing) | Already configured in the project. Switching to Jest would require migration effort with zero value for this epic's goals. |
| Component testing | Angular TestBed | Required for signal-based components. `TestBed.createComponent` is the only way to instantiate components with dependency injection and change detection. |
| Shallow rendering | `NO_ERRORS_SCHEMA` | Avoids importing child component modules in composition tests. Keeps test setup fast and isolated. |
| Async testing | `fakeAsync` + `tick` | Polling lifecycle and bootstrap pipeline tests need controlled time advancement. `fakeAsync` zones are the Angular-standard approach. |
| DOM simulation | Jasmine spies on browser APIs | `getComputedStyle`, `MutationObserver`, and `localStorage` are mocked at the `window` level. No third-party DOM simulation library needed. |
| Sanitization testing | Real `DOMPurify` (no mock) | `pg-state-matrix` sanitization must be tested with the real library to verify XSS prevention. Mocking it would defeat the purpose of the assertion. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Write tests against current component shape, not against a future service interface | The service does not exist yet. Testing a hypothetical API risks asserting behavior that the extraction changes. Testing the real component guarantees the assertions match reality. | Tests require a mechanical find-and-replace during V3 migration — but that operation is trivial and verifiable. |
| Shallow rendering for all composition tests | `live-playground` composes six child components. Deep rendering would require importing and configuring every child's dependencies, creating a fragile 50-line TestBed setup that breaks whenever any child changes. | Cannot verify parent-to-child input bindings in composition tests. This gap is acceptable because child specs cover their own input contracts. |
| Mock all services in app-v2 tests — no real HTTP, no real localStorage | App-v2 tests target signal and computed logic, not integration behavior. Real services would introduce flakiness (network timing, storage state leakage between tests) without improving confidence in the extraction migration. | Cannot catch integration bugs between app-v2 and its services. This is acceptable — integration testing is explicitly out of scope for this epic. |
| Test MutationObserver via mock constructor, not via real DOM mutation | JSDOM (Karma's DOM) does not fire `MutationObserver` callbacks reliably on attribute changes. Mocking the constructor and capturing the callback gives deterministic control over when observation triggers. | Tests do not prove the observer works in a real browser. This is a unit-test limitation accepted across the Angular ecosystem. |
| Assert reflow trick via classList spy sequence, not via animation verification | CSS animations do not run in JSDOM. The reflow trick (`void el.offsetWidth` between class removal and re-addition) is a DOM-API-level concern, not a visual concern. Spying on the classList call sequence proves the trick executes. | Cannot verify the animation actually replays visually. Manual verification remains necessary for animation correctness. |
| Organize app-v2 tests by future service interface groups, not by template regions | Grouping by signal initialization, computed values, methods, polling, and bootstrap mirrors the planned `AppStateService` structure. This makes the V3 migration a file-copy operation rather than a test-reorganization. | Test file structure does not match the component's template structure, which may feel unintuitive to a reader unfamiliar with the V3 plan. The epic and timeline documents provide that context. |
| No shared test utility files beyond existing mock factories | 135 tests across 7 spec files do not justify a shared test harness. Each spec file stands alone. A shared utility would create coupling between specs that should be independent. | Minor duplication in TestBed configuration across spec files. Three similar `beforeEach` blocks are better than a premature `configureTestModule` helper (per P4). |
| Exclude `landing-pitch.component` from scope | 481 lines of pure presentational markup with zero logic branches, zero signals, and zero method calls. The cost-per-assertion is high and the regression risk during V3 extraction is zero — no state moves through this component. | If interactivity is added to landing-pitch in the future, it will need tests retroactively. Re-scope at that time. |
| Exclude `pg-components-app` and `pg-components-ui` from scope | Line counts are unknown and no test design exists. Including them would require an audit step that blocks the rest of the epic. Deferring to a follow-up keeps the critical path focused on the six components with known designs. | Two playground components remain untested after this epic. Follow-up audit will determine their complexity and priority. |
| Target 135 new tests bringing the total to approximately 392 | The combined count (87 playground + 48 pre-V3) provides meaningful coverage for the extraction migration. The 48 pre-V3 tests are the minimum set that covers every signal, computed value, and method that moves to `AppStateService`. | The total count is an approximation — individual specs may gain or lose one to two tests during implementation based on what the component's actual behavior reveals. |

## Migration Path — V3 Extraction Compatibility

The most consequential architectural choice in this suite is how app-v2 tests are structured for future portability. Every assertion in the pre-extraction suite follows the pattern of accessing a signal or calling a method directly on the component instance — never through template queries, never through DOM events, never through `fixture.debugElement`. This means the V3 migration touches exactly two lines per test file: the instantiation (component instance becomes service injection) and optionally the describe block name.

This pattern has one important constraint: **tests must not rely on Angular change detection to propagate signal values**. In a component, signals update synchronously when called. In a service, they will behave identically. But if a test triggers a signal update through a template interaction (button click → method call → signal update), it depends on the component's template existing — which will not be the case when the test migrates to a service. Every pre-extraction test calls the method directly, keeping the service migration path clean.

The 15 basic behavior tests (injection, rendering, navigation) are the exception — they do depend on the component's template and will remain in a component-level spec file after V3 extraction. These tests verify that app-v2 correctly delegates to the extracted service, which is a separate concern from the service's own logic.

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| MutationObserver mock does not match real browser behavior | Mock captures the exact callback signature the component registers. If the component changes its observer configuration, the mock will fail to trigger — surfacing the change. |
| Shallow rendering hides broken child bindings | Child components each have their own spec verifying input/output contracts. A broken binding surfaces in the child spec, not the parent composition spec. |
| `fakeAsync` zones mask real timing bugs in polling | Polling tests verify the state machine transitions (start → poll → retry → stop), not the timer intervals. Real interval values are irrelevant to the extraction migration. |
| Demo data changes break state-matrix tests | State-matrix tests import from the same `playground-demo-data` source the component uses. If the data shape changes, tests and component break simultaneously — the test surfaces the incompatibility. |
| Existing 257 tests regress during spec file additions | No existing spec file is modified. New spec files are additive. The CI gate verification task runs the full suite and confirms the existing count holds. |

## Related Documents

- [Analysis](./analysis.md) — Coverage audit and gap identification that drives the test targets in this architecture
- [Epic](./epic.md) — Scope boundaries, task breakdown, and success criteria this architecture fulfills
- [Timeline](./timeline.md) — Task sequencing, parallelism opportunities, and V3 branch-fork gate