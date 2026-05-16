# Implementation Guide: V3 + Cleanup — State Extraction, Tests, Deletion

## Overview
This epic replaces two god components (V1 at 1,774 lines, V2 at 1,087 lines) with a single injectable AppStateService and a thin V3 shell component, then deletes the originals after a soak period. The four tasks are strictly sequential: extract state into a service and build the shell, prove test and visual parity, promote V3 to the default route with a one-week soak, then delete V1/V2 and consolidate CSS. The net result is a ~7,650-line reduction with zero behavior change.

## Shared Pre-flight
- Confirm `ng build --configuration production` passes on the current codebase before starting any task
- Run the full Karma suite and verify 441+ tests pass as the green baseline
- Run the Playwright E2E suite and verify 34+ scenarios pass (9 skipped mock-dependent tests are acceptable)
- Identify the three HTTP services AppStateService will depend on: ProjectsService, AiService, SubscriptionService
- Confirm Angular standalone component conventions are followed throughout (no NgModule coordination)
- Ensure Playwright is configured with a fixed viewport size for screenshot comparison consistency
- Verify that routes `/v1` and `/v2` currently resolve correctly so baseline URLs are known
- Take a reference screenshot of V2 at `/v2` to use as the pixel-parity baseline in Task 2

---

## Task 1: Extract AppStateService + V3 Shell  [Effort: 3 hrs]

### What
Move all state logic (~40 signals, ~15 computed properties, ~30 methods, and 3 effects) out of `app-v2.component.ts` into a standalone `AppStateService`, extract pure utility functions into dedicated files, and build a thin V3 shell component routed at `/v3`. This makes state independently injectable and testable without rendering a component tree.

### Files
- **Create**: `src/app/services/app-state.service.ts` — root-provided service holding all signals, computed properties, mutation methods, and effects extracted from V2
- **Create**: `src/app/utils/paragraph-diff.ts` — pure function that takes two strings and returns diff HTML
- **Create**: `src/app/utils/nav-sections.ts` — static constant exports for section definitions and context file mappings
- **Create**: `src/app/v3/app-v3.component.ts` — thin shell component under 30 lines injecting AppStateService
- **Create**: `src/app/v3/app-v3.component.html` — V2 template with bindings changed from direct signal access to `state.signalName()` prefix
- **Modify**: `src/app/app.routes.ts` — add `/v3` route pointing to AppV3Component

### Steps
1. Create `app-state.service.ts` as a root-provided injectable service. Move all 40 signals from V2's component class into the service constructor, preserving their initial values and types exactly as they exist in `app-v2.component.ts`.
2. Move all 15 computed properties into the service, keeping the same derivation logic and signal dependencies. Ensure each computed references signals on `this` rather than the old component instance.
3. Move all 30 methods into the service. Replace any direct component references (like `this.router`) with injected dependencies or callbacks that the shell will wire up. Expose a `navigateToUpgrade` callback property that the shell sets after injection.
4. Move the three effects (auth state watcher, elapsed timer for spec generation, section count pulse animation) into the service constructor using Angular's `effect()` API within injection context.
5. Extract the paragraph diff computation from the service into `paragraph-diff.ts` as a named export pure function. Import it back into the service where the original logic lived.
6. Extract the static NAV_SECTIONS constant and CONTEXT_FILES mapping into `nav-sections.ts` as named constant exports.
7. Create the V3 shell component as a standalone component. Its class body contains only `inject()` calls for AppStateService, AuthService, and SubscriptionService, plus static constant imports from `nav-sections.ts`.
8. Copy V2's template into `app-v3.component.html` and mechanically replace every direct signal/method reference with the `state.` prefix (e.g., `activeProject()` becomes `state.activeProject()`).
9. Register the `/v3` route in `app.routes.ts` pointing to AppV3Component with lazy loading.
10. Run `ng build --configuration production` and confirm zero errors.

### Verify
- `ng build --configuration production` succeeds with no errors or warnings related to the new files
- Navigating to `/v3` in the dev server renders the application identically to `/v2` by visual inspection
- `app-v3.component.ts` is under 50 lines of TypeScript
- `app-state.service.ts` is approximately 400 lines and contains all signals, computed properties, methods, and effects

---

## Task 2: Migrate Tests & Prove Parity  [Effort: 2 hrs]

### What
Migrate the 48 pre-V3 regression tests from the component test file to a service-level spec, run the full Karma and E2E suites against V3, and perform pixel-identical screenshot comparison between V2 and V3 to prove zero visual regression.

### Files
- **Create**: `src/app/services/app-state.service.spec.ts` — unit tests for AppStateService migrated from V2 component tests
- **Modify**: `e2e/tests/app.spec.ts` — add V3 route variants or parameterize base URL to cover `/v3`
- **Create**: `e2e/tests/visual-parity.spec.ts` — Playwright test that screenshots V2 and V3 at identical viewports and compares them

### Steps
1. Create `app-state.service.spec.ts` using Angular's `TestBed` to provide AppStateService with mocked HTTP services (ProjectsService, AiService, SubscriptionService).
2. Mechanically copy each of the 48 pre-V3 regression test cases from the V2 component spec. Replace every `component.signalName()` reference with `service.signalName()` and every `component.methodName()` call with `service.methodName()`. Preserve assertion logic exactly.
3. Run the full Karma suite and confirm that all 441+ tests pass, including the 48 newly migrated service tests.
4. Configure the E2E suite to run its 34+ scenarios against `/v3` by parameterizing the base URL or duplicating the route in test configuration.
5. Run the Playwright E2E suite against `/v3` and confirm 34+ scenarios pass with the same 9 acceptable skips.
6. Create `visual-parity.spec.ts` that navigates to `/v2` and `/v3` in the same Playwright session with identical viewport dimensions, takes full-page screenshots of both, and performs a pixel comparison asserting less than 0.1% difference.
7. Run the visual parity test and confirm V3 renders pixel-identically to V2.
8. Run `ng build --configuration production` to confirm the test file additions introduced no build regressions.

### Verify
- `ng test --no-watch --browsers=ChromeHeadless` reports 441+ tests passing including the 48 migrated service tests
- `pytest e2e/` against `/v3` reports 34+ scenarios passing
- Visual parity screenshot test passes with less than 0.1% pixel difference
- `ng build --configuration production` succeeds

---

## Task 3: Route Cutover + 1-Week Soak  [Effort: 1 hr + 7-day wait]

### What
Promote V3 to the default route `/`, redirect `/v2` to `/`, and preserve `/v1` as a one-week escape hatch. Monitor for regressions over 7 calendar days before proceeding to deletion.

### Files
- **Modify**: `src/app/app.routes.ts` — change the default `/` route to load AppV3Component, add redirect from `/v2` to `/`, keep `/v1` pointing to AppComponent (V1)
- **Modify**: `e2e/tests/app.spec.ts` — update base URL assertions to expect V3 content at `/`

### Steps
1. In `app.routes.ts`, change the default path `''` route to load `AppV3Component` instead of `AppV2Component`.
2. Add a redirect route entry that sends `/v2` to `/` so any bookmarked V2 URLs continue working.
3. Confirm that `/v1` still routes to the original `AppComponent` as an escape hatch.
4. Remove the now-redundant `/v3` route since V3 is the default.
5. Update E2E tests to run against `/` and confirm 34+ scenarios still pass against the promoted V3.
6. Run `ng build --configuration production` and deploy.
7. Monitor application behavior over 7 calendar days. Check for console errors, visual regressions, or user-reported issues. The rollback path is re-pointing `/` back to AppV2Component in a single route change.

### Verify
- `ng build --configuration production` succeeds after route changes
- Navigating to `/` renders V3 and navigating to `/v1` renders V1
- Navigating to `/v2` redirects to `/`
- After 7 days of soak, no regressions have been observed or reported

---

## Task 4: Delete V1, V2, and Consolidate CSS  [Effort: 2 hrs]

### What
Remove all V1 and V2 component files, delete the duplicated scoped CSS from landing-pitch, audit and remove dead classes from the global stylesheet, and extract shared design tokens into a single canonical file. This achieves the ~7,650-line net reduction.

### Files
- **Delete**: `src/app/app.component.ts` — V1 component (1,774 lines)
- **Delete**: `src/app/app.component.html` — V1 template
- **Delete**: `src/app/app.component.css` — V1 styles
- **Delete**: `src/app/app-v2.component.ts` — V2 component shell (279 lines)
- **Delete**: `src/app/app-v2.component.html` — V2 template
- **Modify**: `src/app/app.routes.ts` — remove `/v1` route and all references to AppComponent and AppV2Component
- **Modify**: `src/app/landing-pitch/landing-pitch.component.ts` — change to `ViewEncapsulation.None`
- **Delete**: `src/app/landing-pitch/landing-pitch.component.css` — scoped CSS (401 lines) replaced by global classes
- **Create**: `src/shared/tokens.css` — canonical design token definitions (~50 lines) for colors, typography, and spacing
- **Modify**: `src/styles.css` — import `shared/tokens.css`, remove ~200 lines of dead classes confirmed unused by grep audit
- **Modify**: `src/app/landing-pitch/landing/style.css` — import `shared/tokens.css` instead of maintaining parallel `--lp-*` variable definitions

### Steps
1. Delete the V1 component files: `app.component.ts`, `app.component.html`, and `app.component.css`.
2. Delete the V2 component files: `app-v2.component.ts` and `app-v2.component.html`.
3. Remove the `/v1` route from `app.routes.ts` and remove all import statements referencing AppComponent or AppV2Component.
4. Grep every CSS class name in `styles.css` against all active component template files. Record every class with zero matches across templates.
5. Remove the approximately 200 dead class definitions identified by the grep audit from `styles.css`.
6. Create `src/shared/tokens.css` containing all design token custom properties (`--ink`, `--bg`, `--accent`, typography scales, spacing values) currently duplicated between `styles.css` and the landing-pitch scoped stylesheet.
7. Add an import of `shared/tokens.css` at the top of `styles.css` and remove the now-redundant token definitions from the file body.
8. Add an import of `shared/tokens.css` at the top of `landing/style.css` and remove the parallel `--lp-*` variable declarations.
9. In `landing-pitch.component.ts`, change the encapsulation property to `ViewEncapsulation.None` and remove the `styleUrls` reference to the scoped CSS file.
10. Delete `landing-pitch.component.css` entirely.
11. Run `ng build --configuration production` and confirm zero errors.
12. Run the full Karma suite and confirm 441+ tests pass.
13. Run the full E2E suite and confirm 34+ scenarios pass with no visual regressions.

### Verify
- `ng build --configuration production` succeeds with no errors
- Zero references to `AppComponent` or `AppV2Component` exist in the codebase (confirmed by grep)
- `src/shared/tokens.css` exists and is imported by both `src/styles.css` and `src/app/landing-pitch/landing/style.css`
- Full Karma suite (441+ tests) and E2E suite (34+ scenarios) pass green
---

## Implementation Notes

1. **Flat paths.** `app-v3.component.ts` at `web-ng/src/app/` level, NOT in `src/app/v3/` subdirectory.
2. **Utils location.** `paragraph-diff.ts` and `nav-sections.ts` — put at `web-ng/src/app/` level (flat) since `services/` is the only allowed subdirectory per CLAUDE.md.
3. **landing-pitch path.** It's `web-ng/src/app/landing-pitch.component.ts` (flat), not in a subdirectory.
4. **landing/style.css** is at project root `/Users/sam/Projects/specview/landing/style.css`, not inside the Angular app.
5. **E2E test paths.** E2E files are at `e2e/test_overview.py`, `e2e/test_core.py` etc. Not `e2e/tests/`.
6. **app.component.css doesn't exist.** V1 has no CSS file — skip that deletion step.
7. **Test names: present tense, no "should".**
