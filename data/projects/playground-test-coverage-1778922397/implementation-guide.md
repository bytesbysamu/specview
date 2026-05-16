# Implementation Guide: Playground & V2 Test Coverage

## Overview
This epic delivers approximately 153 new automated tests across nine spec files, covering six playground components, two additional presentational components (pg-components-app and pg-components-ui), the css-read utility, and the 1,087-line app-v2 component — all before V3's AppStateService extraction branch forks. Tasks sequence in three independent tiers: Tier 1 (Task 1) builds utility and leaf specs as a tested foundation; Tier 2 (Task 2) adds composition specs for pg-state-matrix and live-playground that depend on leaf specs for failure attribution; Tier 3 (Tasks 3–4) builds the app-v2 regression suite structured so every assertion migrates from component-instance access to service-instance access via mechanical find-and-replace. Task 5 gates the epic with a CI verification pass confirming 410+ total tests pass alongside a clean production build. Tasks 1, 3, and 4 can run in parallel; Task 2 should follow Task 1; Task 5 runs last.

## Shared Pre-flight
- Run `ng test --watch=false` and confirm 257 existing tests pass — this is the regression baseline
- Run `ng build --configuration production` and confirm zero errors — this is the build baseline
- Verify no spec files already exist for any target component to avoid naming collisions: search for `pg-tokens.component.spec.ts`, `pg-animations.component.spec.ts`, `pg-borders.component.spec.ts`, `pg-state-matrix.component.spec.ts`, `live-playground.component.spec.ts`, `app-v2.component.spec.ts`, `css-read.util.spec.ts`, `pg-components-app.component.spec.ts`, and `pg-components-ui.component.spec.ts` in `web-ng/src/app/`
- Locate existing mock factories in the codebase for ProjectsService, AiService, AuthService, and SubscriptionService — these are reused without modification across all spec files
- Review `web-ng/src/app/playground-demo-data.ts` to understand the demo data shapes consumed by pg-state-matrix and live-playground
- Confirm the flat file convention: all new spec files are placed directly in `web-ng/src/app/`, not in subdirectories
- Adopt present-tense test names without "should" throughout: `it('creates ...')` not `it('should create ...')`
- Confirm DOMPurify is available as a project dependency for the state-matrix sanitization test

---

## Task 1: Utility & Leaf Specs  [Effort: 1.5 days]

### What
Create spec files for the css-read utility function, four leaf playground components (pg-borders, pg-tokens, pg-animations), and two presentational playground components (pg-components-app, pg-components-ui). These specs establish a tested foundation that Tier 2 composition specs depend on for failure attribution — when a live-playground test fails, leaf specs help isolate whether the bug is in the child or the parent.

### Files
- **Create**: `web-ng/src/app/css-read.util.spec.ts` — five assertions covering trimmed value return, empty-string fallback to the "not set" sentinel, whitespace-only handling, and real DOM element fixture
- **Create**: `web-ng/src/app/pg-borders.component.spec.ts` — five assertions confirming the seven border demos render with correct CSS classes and label text
- **Create**: `web-ng/src/app/pg-tokens.component.spec.ts` — fifteen assertions covering MutationObserver lifecycle (setup on init, callback trigger for dark-mode toggle, disconnect on destroy) and token value rendering via mocked getComputedStyle
- **Create**: `web-ng/src/app/pg-animations.component.spec.ts` — twelve assertions covering the replay reflow trick (classList remove, offsetWidth read, classList add sequence) and animation class toggling
- **Create**: `web-ng/src/app/pg-components-app.component.spec.ts` — eight assertions confirming masthead, modal, search bar, context cards, and update banner demos render expected markup
- **Create**: `web-ng/src/app/pg-components-ui.component.spec.ts` — ten assertions confirming op chip variants, button variants, and overline/badge elements render with correct classes and content

### Steps
1. Start with `web-ng/src/app/css-read.util.spec.ts` because pg-tokens depends on the utility's contract. Import the css-read function and spy on `window.getComputedStyle` to return controlled values. Write assertions confirming: a trimmed value is returned from getComputedStyle, an empty string returns the "not set" sentinel, whitespace-only input returns the "not set" sentinel, a missing property is handled gracefully, and the function works against a real DOM element fixture created via `document.createElement`.

2. Create `web-ng/src/app/pg-borders.component.spec.ts` with a minimal TestBed configuration — this component has no service dependencies. Instantiate the component via `TestBed.createComponent`, call `fixture.detectChanges`, and write five assertions querying the fixture's native element to confirm each border demo section renders with the expected CSS class and label text.

3. Create `web-ng/src/app/pg-tokens.component.spec.ts` with the most complex browser API mocking in this task. In `beforeEach`, assign a mock constructor to `window.MutationObserver` that captures the callback reference, and spy on `window.getComputedStyle` to return controlled token values. In `afterEach`, restore the original MutationObserver. Write assertions confirming the observer targets `document.documentElement` with attribute observation, token values render from mocked getComputedStyle responses, manually invoking the captured callback causes the component to re-read token values, and the observer's `disconnect` method is called when the component is destroyed via `fixture.destroy()`.

4. Create `web-ng/src/app/pg-animations.component.spec.ts`. After creating the component fixture, obtain a reference to the animation target element and spy on its `classList.remove`, `classList.add`, and the `offsetWidth` property getter. Trigger the replay action and write assertions confirming the sequence: `classList.remove` is called first, then `offsetWidth` is accessed (forcing reflow), then `classList.add` is called. Add assertions that the animation toggle signal changes state correctly and that the component renders the expected animation demo sections.

5. Create `web-ng/src/app/pg-components-app.component.spec.ts` with a minimal TestBed configuration (no service dependencies, standalone component import). Write eight assertions querying the rendered template to confirm each app-level demo section — masthead, modal dialog structure, search bar input, context card containers, and update banner — renders with its expected CSS classes and content structure.

6. Create `web-ng/src/app/pg-components-ui.component.spec.ts` with a minimal TestBed configuration. Write ten assertions confirming each UI demo renders correctly: op chip variants display the right labels and classes, all button variants (primary, secondary, icon) render with expected styling classes, and overline/badge elements contain the correct text and decorative classes.

7. After completing each spec file, run `ng test --watch=false` to confirm new tests pass without breaking existing tests. Fix any test isolation issues (leaked global state from MutationObserver or getComputedStyle mocks) before moving to the next file.

### Verify
- `ng test --watch=false` passes with all new leaf and utility tests green and the existing 257 tests unchanged
- Each of the six spec files exists directly in `web-ng/src/app/` (not in subdirectories) and contains at least five passing tests
- `pg-tokens.component.spec.ts` explicitly asserts MutationObserver setup on init and disconnect on destroy
- `pg-animations.component.spec.ts` explicitly asserts the classList mutation sequence: remove, offsetWidth read, add

---

## Task 2: State-Matrix & Live-Playground Specs  [Effort: 2 days]

### What
Create spec files for the two composition-level playground components. pg-state-matrix tests validate demo data rendering across every visual state and include the only security-relevant assertion in the epic (DOMPurify sanitization). live-playground tests validate signal computation, user interaction flows, and dark mode toggling. Both use shallow rendering via NO_ERRORS_SCHEMA to avoid importing full child component trees.

### Files
- **Create**: `web-ng/src/app/pg-state-matrix.component.spec.ts` — fifteen assertions covering demo data mapping to DOM across five project card variants, five file-dot states, three section-nav configurations, reader panel modes (including access-denied and AI-diff), and one DOMPurify sanitization test with a real XSS vector
- **Create**: `web-ng/src/app/live-playground.component.spec.ts` — twenty assertions covering signal computation (filtered projects, section counts, column calculation), user interaction flows (select project, select file, close panel), dark mode toggle via document.documentElement attribute, and shallow-rendered child component composition

### Steps
1. Create `web-ng/src/app/pg-state-matrix.component.spec.ts`. Configure TestBed with `NO_ERRORS_SCHEMA` and import the component as standalone. Import the demo data from `web-ng/src/app/playground-demo-data.ts` so tests use the same data source as the production component. Write assertions for each state category: five project card variants map to the expected DOM structure with correct CSS classes, five file-dot states apply the correct status classes, three section-nav configurations render the right number of navigation items, and reader panel modes (including access-denied and AI-diff) display their distinctive content markers.

2. Add the DOMPurify sanitization assertion within the same spec file. Construct a demo data entry containing a known XSS vector — a script tag or an event handler attribute in an HTML string field. Render the component with this data and query the output DOM to verify the malicious content has been stripped. Use real DOMPurify (not a mock) so the test proves actual XSS prevention.

3. Create `web-ng/src/app/live-playground.component.spec.ts`. Configure TestBed with `NO_ERRORS_SCHEMA` to suppress the six child component selectors (pg-tokens, pg-borders, pg-animations, pg-state-matrix, pg-components-app, pg-components-ui). Mock any injected services the component requires using existing mock factories or minimal jasmine spy objects.

4. Write signal computation assertions for live-playground: set the projects signal to a known dataset and verify `filteredProjects` returns the correct subset when a section filter is active, verify `sectionCounts` aggregates the correct count per section across all demo projects, verify the `columns` computed signal returns the right grid column count based on the number of projects, and verify the search filter narrows results correctly when a search term signal is set.

5. Write user interaction flow assertions for live-playground: call the `selectProject` method and verify the selected-project signal updates, call a file-selection method within the selected project and verify the active-file signal updates, call the close-panel method and verify selection signals reset to their defaults. Test dark mode toggling by calling the toggle method and asserting that `document.documentElement.getAttribute` returns the updated theme attribute value.

6. Run `ng test --watch=false` to confirm all composition tests pass alongside the leaf specs from Task 1 and the existing 257 tests.

### Verify
- `ng test --watch=false` passes with all Task 1 and Task 2 tests green and existing 257 tests unchanged
- `pg-state-matrix.component.spec.ts` contains at least 15 passing tests including one explicit DOMPurify sanitization assertion using a real XSS vector
- `live-playground.component.spec.ts` contains at least 20 passing tests covering signal computation and user interaction flows
- Both spec files use `NO_ERRORS_SCHEMA` in their TestBed configuration and do not import any child component modules

---

## Task 3: App-v2 Pre-V3 Regression Suite  [Effort: 2 days]

### What
Create 48 tests targeting the app-v2 component's state and behavior, organized into five groups mirroring the planned AppStateService interface: signal initialization, computed derivations, method behavior, polling lifecycle, and bootstrap pipeline. Every assertion accesses the component instance directly — never through template queries — so migration to AppStateService requires only a find-and-replace from `component.` to `service.`.

### Files
- **Create**: `web-ng/src/app/app-v2.component.spec.ts` — 48 tests across five describe groups: signal initialization (10 tests), computed derivations (10 tests), method behavior (15 tests), polling lifecycle (5 tests), bootstrap pipeline (8 tests)

### Steps
1. Configure the TestBed for app-v2 with an all-mocks service layer. Reuse existing mock factories for ProjectsService, AiService, AuthService, and SubscriptionService. Create minimal jasmine spy objects for any remaining service dependencies (Router, ActivatedRoute, and any app-specific services). Replace localStorage with a spy object that returns controlled values for the `isDark` key. Set `NO_ERRORS_SCHEMA` since these tests never interact with the template.

2. Write the signal initialization describe group containing 10 tests. For each signal the component declares, assert its default value immediately after component construction: selected project is null, search term is empty string, theme signal matches the mocked localStorage value, section filter holds its default, undo stack is an empty array, loading flags are false, polling state is idle, and any remaining signals hold their documented defaults. These catch constructor regressions during V3 extraction.

3. Write the computed derivations describe group containing 10 tests. For each computed signal, set the upstream input signals to known states before reading the computed output. Assert that `filteredProjects` correctly filters by the active section, `filteredProjects` correctly filters by search term, `filteredProjects` applies both filters simultaneously, `sectionCounts` produces the correct aggregation from the projects signal, `columns` computes the right value from the project count, and cover any additional computed signals. These are the highest-value assertions because computed signals depend on multiple upstream signals being wired correctly in the new host.

4. Write the method behavior describe group containing 15 tests. For each public method, call it directly on `component` and assert resulting signal state changes and spy invocations. Cover: `selectProject` setting the selected-project and related signals, `toggleTheme` updating both the localStorage spy and `document.documentElement`, `applyResult` pushing a new entry onto the undo stack, file save methods updating the correct project signals, navigation methods delegating to the Router spy, undo/redo methods manipulating the stack correctly, and search-clear resetting the search signal.

5. Write the polling lifecycle describe group containing 5 tests using `fakeAsync` and `tick`. Assert that starting the poll triggers the first service call, stopping the poll prevents further calls after tick advancement, the retry counter increments on each failed poll, polling resumes correctly after a pause-and-restart sequence, and the maximum retry limit stops polling and sets an error signal.

6. Write the bootstrap pipeline describe group containing 8 tests using `fakeAsync` and `tick`. Assert the initialization sequence: the auth check resolves first and triggers project loading, project load populates the projects signal with the mock response, theme is applied from the mocked localStorage value, polling starts automatically after bootstrap completes, a partial file save during a long bootstrap operation is handled without corrupting state, an auth failure during bootstrap sets the appropriate error signal, a project-load failure sets a distinct error signal, and the bootstrap-completed flag transitions to true only after all steps succeed.

7. Review every test in the file to confirm the direct-access pattern: all assertions read `component.signalName()` or call `component.methodName()` with no references to `fixture.debugElement`, `fixture.nativeElement`, or `By.css` queries.

### Verify
- `ng test --watch=false` passes with all 48 pre-extraction tests green alongside all prior tests
- `app-v2.component.spec.ts` contains exactly five describe groups: signal initialization, computed derivations, method behavior, polling lifecycle, and bootstrap pipeline
- No test in this file references `fixture.debugElement`, `fixture.nativeElement`, or any template query method
- Searching the spec file for `HttpClient`, direct `fetch` calls, or `window.localStorage` (outside of spy setup) finds zero matches — all external dependencies are mocked

---

## Task 4: App-v2 Basic Behavior Tests  [Effort: 0.5 days]

### What
Add 15 template-aware tests to the app-v2 spec file covering the component's role as a view controller: service injection verification, conditional template rendering, and navigation delegation. Unlike the pre-extraction tests in Task 3, these tests intentionally depend on the component's template and will remain in the component-level spec file after V3 extraction to verify that app-v2 correctly delegates to the extracted service.

### Files
- **Modify**: `web-ng/src/app/app-v2.component.spec.ts` — add a sixth describe group for basic behavior tests (service injection, conditional rendering, navigation delegation) alongside the five pre-extraction groups from Task 3

### Steps
1. Add a new describe group within `web-ng/src/app/app-v2.component.spec.ts` for basic behavior tests. This group uses the same TestBed configuration established in Task 3 but accesses the template via `fixture.debugElement` for rendering assertions.

2. Write approximately five service injection verification tests. For each critical service the component depends on (ProjectsService, AiService, AuthService, SubscriptionService, Router), inject the service from the TestBed and assert it is defined and matches the mock instance. These catch provider wiring regressions if V3 changes the module or component provider configuration.

3. Write approximately five conditional rendering tests. Set the component's signals to states that trigger different template branches, then call `fixture.detectChanges()` and query the DOM. Assert that the landing-pitch view renders when no project is selected and the user is on the home route, the workspace view renders when a project is active, a loading indicator appears when the loading signal is true, an error state renders the appropriate message when the error signal is set, and the transition between landing and workspace views is clean (no remnant elements from the previous view).

4. Write approximately five navigation delegation tests. Call the component's navigation-related methods and assert that the Router spy's `navigate` or `navigateByUrl` method received the expected arguments. Cover project-open navigation (method call produces the correct route), file-open navigation within an active project, section switching updating the route parameter, back-navigation behavior, and deep-link handling when the component initializes with route parameters already present.

5. Run the full test suite to verify the 15 new basic behavior tests coexist with the 48 pre-extraction tests without conflicts, and that the total app-v2 test count reaches 63.

### Verify
- `ng test --watch=false` passes with all 63 app-v2 tests green (48 pre-extraction + 15 basic behavior)
- The basic behavior describe group is a distinct section within `app-v2.component.spec.ts`, visually separated from the five pre-extraction groups
- At least one test in the conditional rendering group queries the rendered template via `fixture.debugElement` to confirm the landing-pitch view appears when expected
- Router spy assertions confirm `navigate` is called with the correct route for both project-open and file-open flows

---

## Task 5: CI Gate Verification & Coverage Audit  [Effort: 0.5 days]

### What
Run the complete test suite and production build as a final release gate, verify the total test count meets the 410+ target, confirm zero regressions in the original 257 tests, and audit every spec file against the epic's success criteria. This task produces no code — it is a verification-only pass that confirms the epic is complete.

### Files
- No files created or modified — this task is a verification-only pass across all spec files produced by Tasks 1 through 4

### Steps
1. Run `ng test --watch=false` and record the total test count from the Karma output summary. Verify the count is at least 410 (257 existing + approximately 153 new). If the count falls short, identify which spec file is under its target assertion count and trace back to the relevant task to add the missing tests.

2. Run `ng build --configuration production` and confirm it completes with zero errors. Spec files should not affect the production build, but this step catches any accidental import of test-only symbols into production code or any TypeScript compilation errors triggered by new files.

3. Audit each spec file against the success criteria from the epic: `web-ng/src/app/css-read.util.spec.ts` covers the graceful-empty-value path returning "not set"; `web-ng/src/app/pg-tokens.component.spec.ts` covers MutationObserver setup and teardown; `web-ng/src/app/pg-animations.component.spec.ts` covers the replay reflow trick via classList spy sequence; `web-ng/src/app/pg-state-matrix.component.spec.ts` includes at least one DOMPurify sanitization assertion; `web-ng/src/app/app-v2.component.spec.ts` contains at least 48 pre-extraction tests using direct component-instance access; `web-ng/src/app/pg-components-app.component.spec.ts` and `web-ng/src/app/pg-components-ui.component.spec.ts` each have at least five passing tests.

4. Verify zero modifications to existing spec files by diffing against the base branch. All changes from this epic should be new file additions only. Run a diff limited to spec files and confirm no existing spec file appears in the modified list.

5. Confirm all app-v2 pre-V3 tests use mock services exclusively by searching `web-ng/src/app/app-v2.component.spec.ts` for any direct references to HttpClient, real fetch calls, or direct localStorage access (outside of beforeEach spy setup). Zero matches confirms the isolation contract.

6. Run `ng test --watch=false` one final time to confirm the full suite is stable and deterministic — both runs should produce identical pass counts with zero flaky failures.

### Verify
- `ng test --watch=false` reports 410 or more total tests with zero failures across two consecutive runs
- `ng build --configuration production` completes with zero errors
- Diffing spec files against the base branch shows only new `.spec.ts` file additions in `web-ng/src/app/` and zero modifications to any pre-existing spec file
- Every component listed in the success criteria — pg-tokens, pg-animations, pg-borders, pg-state-matrix, live-playground, pg-components-app, pg-components-ui, css-read.util, and app-v2 — has a corresponding spec file with passing tests
---

## Implementation Notes

1. **Task 3 Step 6 naming:** "bootstrap pipeline" in this context means `_runBootstrap()` (spec generation polling), not app initialization. The "auth check resolves first" tests belong in a separate "initialization" sub-group within the describe block.
2. **Task 4 auth mock:** Conditional rendering tests need `auth.isLoggedIn` mock signal toggled explicitly — `isLoggedIn.set(true)` before `fixture.detectChanges()` to show workspace, `isLoggedIn.set(false)` for landing pitch.
3. **Test names: present tense, no "should".** `it('creates')` not `it('should create')`.
