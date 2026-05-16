# Playground & V2 Test Coverage

## Why before V3

V3 extracts state from app-v2 into a service. If we don't have tests on the V2 sub-components and playground components BEFORE the extraction, we can't verify V3 didn't break anything. Tests written now become the regression safety net for the extraction.

## Current coverage (audited 2026-05-16)

257 tests across 14 spec files. Strong on services, weak on components.

### What HAS tests (14 files, 245 tests)

| File | Tests | What's tested |
|------|-------|---------------|
| projects.service | 20 | HTTP calls, sortSpecs |
| project-teaser | 41 | Text parsing, task counting, edge cases |
| reader-panel.component | 35 | Input/output binding |
| sidebar-v2.component | 35 | Input/output binding |
| ai.service | 22 | All 8 AI endpoints |
| token-lifecycle.service | 18 | JWT decode, refresh, expiry |
| project-grid.component | 11 | Input/output binding |
| section-nav.component | 11 | Input/output binding |
| auth.service | 11 | Login, register, signOut |
| word-count.pipe | 11 | Word counting edge cases |
| status-bar.component | 10 | Input/output binding |
| subscription.service | 9 | Plan refresh, checkout |
| section-taxonomy.service | 6 | Section classification |
| app.component | 5 | Polling lifecycle |

### What's MISSING tests (12 files, 0 tests)

| File | Lines | Priority | Why |
|------|-------|----------|-----|
| pg-tokens.component | 252 | HIGH | MutationObserver lifecycle, CSS var reading, dark mode reactivity |
| pg-animations.component | 293 | HIGH | Replay logic (reflow trick), animation class toggling |
| pg-state-matrix.component | 466 | HIGH | Component rendering in every state, data shape validation |
| live-playground.component | 569 | HIGH | Orchestration, demo signal wiring, project selection flow |
| pg-components-app.component | ? | MEDIUM | Masthead, modal, search bar, context cards rendering |
| pg-components-ui.component | ? | MEDIUM | Op chips, buttons, overline/badges rendering |
| pg-borders.component | 180 | MEDIUM | Border class application |
| app-v2.component | 1,087 | HIGH | Service injection, signal initialization, method delegation |
| landing-pitch.component | 481 | LOW | Pure presentational, no logic |
| css-read.util | 3 | LOW | Single function, trivial |
| playground-demo-data | 169 | LOW | Data shape only, no logic |

## Test design per component

### pg-tokens.component (target: ~15 tests)

```
describe('PgTokensComponent', () => {
  it('should create')
  it('should read color tokens from CSS on init')
  it('should display correct number of color swatches')
  it('should show token variable name and hex value')
  it('should read typography tokens on init')
  it('should display typography specimens')
  it('should show spacing scale boxes')
  it('should update all token values when dark mode toggles')
  it('should set up MutationObserver on document.documentElement')
  it('should clean up MutationObserver on destroy')
  it('should handle missing CSS variables gracefully (return "not set")')
  it('should display status color tokens separately from base colors')
})
```

Key testing challenge: MutationObserver needs to be mocked or triggered via DOM manipulation. Use `fakeAsync` + manual attribute change on documentElement.

### pg-animations.component (target: ~12 tests)

```
describe('PgAnimationsComponent', () => {
  it('should create')
  it('should render all 7 animation demo cards')
  it('should show "Always Running" label for infinite animations')
  it('should show "Replay" button for one-shot animations')
  it('should remove and re-add class on replay click')
  it('should force reflow between remove and re-add (offsetWidth read)')
  it('should display animation name and timing label')
  it('should distinguish between one-shot and infinite animations')
})
```

Key testing challenge: `replay()` method uses `void el.offsetWidth` for reflow. Spy on the class list changes, not the animation itself.

### pg-state-matrix.component (target: ~15 tests)

```
describe('PgStateMatrixComponent', () => {
  it('should create')
  it('should render 5 project card variants')
  it('should render featured card with .featured class')
  it('should render sidebar nav with 5 file states (idle, active, running, success, failure)')
  it('should render 3 section nav instances with different active states')
  it('should render reader panel with normal content')
  it('should render reader panel with access denied state')
  it('should render reader panel with AI diff view')
  it('should parse demo markdown via marked + DOMPurify')
  it('should sanitize HTML content (no XSS)')
  it('should apply correct CSS classes for file dot states')
})
```

### live-playground.component (target: ~20 tests)

```
describe('LivePlaygroundComponent', () => {
  it('should create')
  it('should initialize with 8 demo projects')
  it('should compute section counts from demo projects')
  it('should compute filtered projects based on active section')
  it('should select a project and set activeProject signal')
  it('should select a file and update activeFile signal')
  it('should compute parsed markdown content for selected spec')
  it('should close expanded panel and reset activeProject')
  it('should toggle dark mode on document element')
  it('should render section nav component')
  it('should render all 4 status bar states')
  it('should render project grid with demo data')
  it('should render expanded panel when project is selected')
  it('should render landing pitch component')
  it('should bind teaserFn and sectionFn to project grid')
  it('should compute columns based on filtered project count')
  it('should update demo section counts reactively')
  it('should handle empty filtered projects (show grid with no cards)')
})
```

Key testing challenge: This component composes 6+ sub-components. Use shallow rendering (schemas: [NO_ERRORS_SCHEMA]) for child components that aren't the test focus.

### app-v2.component (target: ~15 tests)

```
describe('AppV2Component', () => {
  it('should create')
  it('should inject AuthService')
  it('should inject ProjectsService')
  it('should inject AiService')
  it('should inject SubscriptionService')
  it('should show landing pitch when not logged in')
  it('should show workspace when logged in')
  it('should load projects on login')
  it('should navigate to /upgrade on upgrade button click')
  it('should call logout on sign out button click')
  it('should toggle dark mode')
  it('should open create modal')
  it('should close create modal')
  it('should start bootstrap on project creation')
  it('should handle polling lifecycle (start/stop on auth change)')
})
```

Key testing challenge: 1,087-line component with many dependencies. Use mock services extensively. Focus on the signal flow, not the internal method implementations (those will be tested on the state service after V3 extraction).

### css-read.util (target: ~5 tests)

```
describe('getCssVar', () => {
  it('should return computed value for existing CSS variable')
  it('should return "not set" for undefined CSS variable')
  it('should trim whitespace from returned values')
  it('should handle empty string values')
})
```

### pg-borders.component (target: ~5 tests)

```
describe('PgBordersComponent', () => {
  it('should create')
  it('should render all 7 border demos')
  it('should apply correct CSS class to each border demo')
  it('should display label and description for each border')
})
```

## Implementation approach

### File naming convention
- `pg-tokens.component.spec.ts` (flat, next to component)
- `pg-animations.component.spec.ts`
- etc.

### Mock strategy
- Sub-components in playground tests: use `NO_ERRORS_SCHEMA` for shallow rendering
- Services in app-v2 tests: use existing mock factories (`createMockProjectsService`, etc.)
- DOM/CSS: mock `getComputedStyle` for token tests
- MutationObserver: mock constructor, trigger callback manually

### Priorities (what to write first)

1. **live-playground.component.spec.ts** (~20 tests) — the orchestrator, highest value
2. **pg-tokens.component.spec.ts** (~15 tests) — has real logic (MutationObserver, CSS reads)
3. **pg-animations.component.spec.ts** (~12 tests) — has replay logic
4. **pg-state-matrix.component.spec.ts** (~15 tests) — validates demo data rendering
5. **app-v2.component.spec.ts** (~15 tests) — pre-V3 regression safety net
6. **pg-borders.component.spec.ts** (~5 tests) — simple rendering
7. **css-read.util.spec.ts** (~5 tests) — trivial but good practice

### Target: ~87 new tests → total ~344

## Success criteria
- Every playground component has a spec file with at least 5 tests
- Every spec file tests: creation, rendering, and at least one behavioral assertion
- MutationObserver lifecycle tested (setup + teardown)
- Replay animation logic tested
- Demo data shape validated (tests catch if playground-demo-data changes break rendering)
- `ng test` passes with 340+ tests
- `ng build` passes
- Zero regressions in existing 257 tests
