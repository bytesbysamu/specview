# Implementation Guide: Unified Page V3

## Overview
Unified Page V3 reunifies spec-doc's visual identity by merging V1's proven newspaper rendering with V2's decomposed component architecture. The work sequences across five tasks: first, fix the upgrade-button logout bug that destroys user trust at the payment boundary; second, achieve pixel-parity by porting V1's HTML into V2's five sub-components and emptying their scoped CSS so the global design system governs all rendering; third, migrate the 155 Karma unit tests and E2E suite to target V2's DOM structure; fourth, swap V2 to the root route with V1 preserved at /v1 as a one-week escape hatch; fifth, remove V1 dead code after a clean soak period with zero rollbacks.

## Shared Pre-flight
- Confirm the Angular dev server starts cleanly with `ng serve` and the production build passes with `ng build --configuration production`
- Verify `web-ng/src/styles.css` contains the newspaper design tokens: `--ink`, `--bg`, `--serif`, `--sans`, `--border`
- Confirm V1 renders correctly at the current root route as the baseline for visual comparison
- Identify all five V2 sub-component directories under `web-ng/src/app/`: project-grid, reader-panel, sidebar-v2, status-bar, section-nav
- Verify the billing backend responds correctly: `POST /api/billing/create-checkout-session` returns a `{ url }` payload and `GET /api/billing/status` returns plan and status fields
- Screenshot V1's app workspace at desktop and tablet widths for use as the pixel-parity reference throughout Task 2
- Ensure the Karma test runner executes the existing 155 tests successfully against V1 before any changes
- Confirm `app.routes.ts` currently maps `/` to V1's `AppComponent`

---

## Task 1: Fix upgrade-button logout bug  [Effort: 0.5 days]

### What
The upgrade button in V2's app workspace calls the auth service's `logout()` method instead of initiating the Stripe Checkout flow. Users who click "upgrade" lose their session at the exact moment they signal purchase intent. This task rewires the click handler to call the billing service's checkout method and navigate to the returned Stripe URL. It must ship and soak independently before any visual refactoring touches the same component tree.

### Files
- **Modify**: `web-ng/src/app/app-v2.component.ts` — replace the `logout()` call in the upgrade button's click handler with a call to the billing service's `createCheckoutSession()` method, then navigate to the returned URL
- **Modify**: `web-ng/src/app/app-v2.component.html` — update the upgrade button's event binding if it currently points to a logout handler method

### Steps
1. Locate the upgrade button's click handler in `app-v2.component.ts`. It currently invokes the auth service's `logout()` method. Change it to call the billing service's `createCheckoutSession()` method instead.
2. In the same handler, after receiving the response from `createCheckoutSession()`, navigate the browser to the returned `url` property using `window.location.href` assignment. The backend already returns the correct Stripe Checkout URL with `success_url` pointing to `/upgrade?session_id={CHECKOUT_SESSION_ID}`.
3. Ensure the billing service is injected into `AppV2Component` if it is not already. The service should already exist in the codebase and expose the checkout session creation call to `POST /api/billing/create-checkout-session`.
4. Verify the template in `app-v2.component.html` binds the upgrade button's click event to the updated handler method. If the binding references a method named after logout, rename the binding to reflect its actual purpose.
5. Run the production build to confirm no compilation errors were introduced.

### Verify
- Click the upgrade button while authenticated and confirm the browser navigates to the Stripe Checkout page without losing the session
- After completing a test checkout on Stripe, confirm the browser redirects back to `/upgrade?session_id=...` with the user still authenticated
- Run `ng build --configuration production` and confirm it passes with zero errors
- Confirm that the existing Karma test suite still passes without modification

---

## Task 2: Achieve visual parity: V1 rendering in V2 components  [Effort: 1.5 days]

### What
V2's five sub-components reference undefined CSS variables and carry component-scoped styles extracted from the playground, producing a visual mismatch with V1's newspaper aesthetic. This task ports V1's HTML structure from `app.component.html` into V2's sub-component templates, empties all five component CSS files so the global `styles.css` cascade applies, slims down `app-v2.component.css` to remove duplicates, and adds the missing panel slide animation and usage meter. The result is pixel-identical rendering between V1 and V2.

### Files
- **Modify**: `web-ng/src/app/project-grid/project-grid.component.html` — replace V2 template content with the 4-column newspaper grid region from V1's `app.component.html`, preserving `.file-item` cards with correct padding, `282px` column width, section groups with separators, and the search bar with left-aligned project count
- **Modify**: `web-ng/src/app/project-grid/project-grid.component.css` — empty the file, leaving only a comment indicating styles are inherited from global `styles.css`
- **Modify**: `web-ng/src/app/reader-panel/reader-panel.component.html` — replace with V1's expanded file viewer region including `.expanded-main`, `.markdown-content`, `WordCountPipe` integration, and `DOMPurify` sanitization
- **Modify**: `web-ng/src/app/reader-panel/reader-panel.component.css` — empty the file
- **Modify**: `web-ng/src/app/reader-panel/reader-panel.component.ts` — register the `@panelEnter` slide animation ported from V1's `app.component.ts` using Angular's `@trigger` animation syntax
- **Modify**: `web-ng/src/app/sidebar-v2/sidebar-v2.component.html` — replace with V1's `.expanded-sidebar` region including `.sidebar-file` list and active-file highlighting
- **Modify**: `web-ng/src/app/sidebar-v2/sidebar-v2.component.css` — empty the file
- **Modify**: `web-ng/src/app/status-bar/status-bar.component.html` — replace with V1's generation status strip including dark olive background, white text, project name, current step, and elapsed timer
- **Modify**: `web-ng/src/app/status-bar/status-bar.component.css` — empty the file
- **Modify**: `web-ng/src/app/section-nav/section-nav.component.html` — replace with V1's section navigation region including pill buttons with count badges and active underline indicator
- **Modify**: `web-ng/src/app/section-nav/section-nav.component.css` — empty the file
- **Modify**: `web-ng/src/app/app-v2.component.css` — remove duplicate class definitions (`.thinking-dot`, `.text-ops-error`, `.overline`, `.btn-icon`) that already exist in `styles.css`; keep only the `.v2-shell` rule
- **Modify**: `web-ng/src/app/app-v2.component.html` — update auth-conditional `@if` blocks so the landing pitch and playground sections collapse for authenticated users while the app workspace fills the viewport
- **Read**: `web-ng/src/app/app.component.html` — source of V1's HTML structure to port into each sub-component
- **Read**: `web-ng/src/app/app.component.ts` — source of the `@panelEnter` animation definition to port into the reader panel component

### Steps
1. Diff V1's `app.component.html` against each V2 sub-component template to catalog every V2-only logic block (signal bindings, `@if` conditionals, `@for` loops) that must be preserved after porting. Document these blocks before overwriting any template.
2. Port the newspaper grid region from `app.component.html` into `project-grid.component.html`. The grid uses `.file-item` cards with `20px 24px` padding, `282px` column width, and section groups with separators. Re-add any V2-only signal bindings or control flow blocks identified in the diff.
3. Port the expanded file viewer region into `reader-panel.component.html`, including `.expanded-main`, `.markdown-content`, `WordCountPipe` usage, and the `DOMPurify` sanitization binding. Ensure all V2 input/output bindings are preserved.
4. Copy the `@panelEnter` animation definition from `app.component.ts` and register it in `reader-panel.component.ts` using the `animations` array in the component decorator.
5. Port the sidebar region into `sidebar-v2.component.html` with `.expanded-sidebar`, the `.sidebar-file` list, and active-file highlighting logic.
6. Port the generation status strip into `status-bar.component.html` with the dark olive background, white text, project name display, current step indicator, and elapsed timer.
7. Port the section navigation into `section-nav.component.html` with pill buttons, count badges, and the active underline indicator.
8. Empty all five sub-component CSS files so the global `styles.css` cascade applies to the ported class names without specificity conflicts.
9. Slim down `app-v2.component.css` by removing the duplicate class definitions for `.thinking-dot`, `.text-ops-error`, `.overline`, and `.btn-icon`. Retain only the `.v2-shell { min-height: 100dvh; }` rule.
10. Add the usage meter data binding to the masthead component, reading from the subscription signal that sources its data from `GET /api/billing/status`.
11. Update the auth-conditional `@if` blocks in `app-v2.component.html` so the landing pitch and playground sections are hidden for authenticated users and the app workspace fills the viewport. The masthead must persist across both states.
12. Run `ng build --configuration production` and fix any compilation errors from missing imports, unresolved signal references, or template syntax issues.
13. Take a screenshot of V2's app workspace and overlay it at 50% opacity on the V1 reference screenshot. Identify and fix any remaining pixel-level mismatches in grid alignment, card sizing, font rendering, or spacing.

### Verify
- V2's `.file-item` cards render with `20px 24px` padding and `282px` column width, matching V1 exactly
- The `@panelEnter` slide animation triggers when expanding a file in the reader panel
- The usage meter renders in the masthead with data from the billing status endpoint
- `ng build --configuration production` passes with zero errors and zero warnings related to the modified components

---

## Task 3: Migrate test suite to V2 DOM structure  [Effort: 1.5 days]

### What
The 155 existing Karma unit tests target V1's monolithic `AppComponent`. This task repoints them at V2's component tree, fixes selectors that break against the new DOM structure, and adds dedicated spec files for each of the five sub-components. The E2E suite is extended to run against both routes during the transition period so any V2-specific regressions are caught before route cutover.

### Files
- **Modify**: `web-ng/src/app/app.component.spec.ts` — update test bed imports to include V2's sub-components and point DOM queries at V2's component tree
- **Create**: `web-ng/src/app/project-grid/project-grid.component.spec.ts` — unit tests for ProjectGridComponent verifying card rendering, grid layout, search bar, and project count display
- **Create**: `web-ng/src/app/reader-panel/reader-panel.component.spec.ts` — unit tests for ReaderPanelComponent verifying panel expansion, markdown rendering, word count display, and DOMPurify sanitization
- **Create**: `web-ng/src/app/sidebar-v2/sidebar-v2.component.spec.ts` — unit tests for SidebarV2Component verifying file list rendering and active-file highlighting
- **Create**: `web-ng/src/app/status-bar/status-bar.component.spec.ts` — unit tests for StatusBarComponent verifying project name, step display, and elapsed timer
- **Create**: `web-ng/src/app/section-nav/section-nav.component.spec.ts` — unit tests for SectionNavComponent verifying pill buttons, count badges, and active indicator
- **Modify**: E2E spec files — add parallel test runs targeting both `/` (V2) and `/v1` (V1) so any asymmetric failures are detected

### Steps
1. Run the existing 155 Karma tests against V2's component tree by updating the test bed configuration in `app.component.spec.ts` to import `AppV2Component` and its sub-components instead of V1's `AppComponent`. Record which tests pass and which fail.
2. For each failing test, determine if the failure is a selector mismatch or a genuine behavioral difference. Tests that query the DOM by `[data-test]` attributes should pass without changes since both versions use the same attribute names. Tests that use component-internal structural selectors need their queries updated to match V2's sub-component boundaries.
3. Fix all selector-based failures by updating DOM queries to use `[data-test]` attributes wherever possible. Do not delete any previously passing test; only repoint selectors.
4. Create a spec file for `ProjectGridComponent` following the project's testing conventions: use `createMock` service factory files for dependency injection, `fakeAsync` for any polling or async operations, and `[data-test]` selectors for all DOM queries. Test card rendering, grid column count, search bar filtering, and project count display.
5. Create a spec file for `ReaderPanelComponent` testing panel expansion via the `@panelEnter` animation trigger, markdown content rendering, word count pipe output, and DOMPurify sanitization of untrusted content.
6. Create a spec file for `SidebarV2Component` testing file list rendering from input data, active-file highlighting when a file is selected, and click-to-select behavior.
7. Create a spec file for `StatusBarComponent` testing that project name, current generation step, and elapsed timer render from their input bindings.
8. Create a spec file for `SectionNavComponent` testing pill button rendering, count badge values, and the active underline indicator toggling on click.
9. Update the E2E spec configuration to run each E2E test against both `/` and `/v1`. Any test that passes on `/v1` but fails on `/` indicates a V2 component regression that must be fixed before route cutover.
10. Run the full Karma suite and E2E suite and confirm all tests pass on both routes.

### Verify
- All 155 original Karma tests pass when pointed at V2's component tree
- Each of the five new sub-component spec files passes independently with `ng test`
- The E2E suite passes against both `/` (V2) and `/v1` (V1) with no asymmetric failures
- `ng build --configuration production` continues to pass

---

## Task 4: Route cutover with /v1 escape hatch  [Effort: 0.5 days]

### What
This task swaps the root route to serve V2 and preserves V1 at `/v1` as a rollback path. The cutover is a routing change only — both component trees are fully independent with no shared mutable state. The `/v1` escape hatch has a defined lifetime of one week with zero rollbacks before dead code cleanup is triggered.

### Files
- **Modify**: `web-ng/src/app/app.routes.ts` — change the `/` route to load `AppV2Component` and add a new `/v1` route that loads V1's `AppComponent`
- **Modify**: `web-ng/src/app/app-v2.component.html` — ensure all internal navigation links reference `/` rather than any V2-specific path prefix

### Steps
1. Open `app.routes.ts` and change the route entry for `/` from `AppComponent` to `AppV2Component`. Add a new route entry mapping `/v1` to `AppComponent` so V1 remains accessible as a fallback.
2. Verify that both route entries use lazy loading or direct component references consistently with the existing routing pattern in the file. Both component trees must be fully independent with no shared mutable state between them.
3. Audit `app-v2.component.html` and all sub-component templates for any internal links or `routerLink` directives that reference V2-specific paths. Update them to use `/` since V2 is now the root.
4. Run `ng build --configuration production` to confirm the route configuration compiles without circular dependency or missing import errors.
5. Start the dev server and manually verify that `/` renders V2's unified newspaper layout and `/v1` renders V1's original layout. Test navigation between the two routes to confirm they are independent.
6. Run the full E2E suite against both `/` and `/v1` to confirm no regressions from the route swap.

### Verify
- Navigating to `/` renders V2's app workspace with the newspaper visual design
- Navigating to `/v1` renders V1's original layout identically to how it rendered before the cutover
- `ng build --configuration production` passes with the new route configuration
- The E2E suite passes on both routes with zero asymmetric failures

---

## Task 5: V1 dead code cleanup  [Effort: 0.5 days]

### What
After one week of the route cutover running with zero rollbacks, this task removes V1-only files, the `/v1` escape hatch route, duplicate CSS classes, and dead imports. This is the final step that fully retires V1. The global `styles.css` is never deleted — it is the design system. All shared services remain untouched since they serve V2 identically.

### Files
- **Delete**: `web-ng/src/app/app.component.html` — V1's 585-line monolithic template, no longer referenced
- **Delete**: `web-ng/src/app/app.component.ts` — V1's component class, no longer routed
- **Delete**: `web-ng/src/app/app.component.spec.ts` — V1's test file, superseded by V2 sub-component specs
- **Modify**: `web-ng/src/app/app.routes.ts` — remove the `/v1` route entry and the `AppComponent` import
- **Modify**: `web-ng/src/styles.css` — remove any CSS classes that were exclusively used by V1's template and have no references in V2's component templates
- **Modify**: Any module or barrel files that import or re-export `AppComponent` — remove the dead references

### Steps
1. Confirm the one-week soak period has elapsed with zero rollbacks to `/v1`. Do not proceed if any rollback occurred during the soak.
2. Search the entire `web-ng/src/app/` directory for any remaining imports or references to `AppComponent` (V1's class name). Catalog every file that references it.
3. Remove the `/v1` route entry from `app.routes.ts` and delete the `AppComponent` import statement from the same file.
4. Delete V1's component files: `app.component.html`, `app.component.ts`, `app.component.css` (if it exists as a separate file), and `app.component.spec.ts`.
5. Search `web-ng/src/styles.css` for class names that appear only in the deleted V1 template and nowhere in V2's sub-component templates. Remove those dead classes. Do not remove classes that are still referenced by V2 components, the landing page, or the playground.
6. Remove any dead imports or re-exports of `AppComponent` from module files, barrel index files, or test configuration files.
7. Run `ng build --configuration production` to confirm no compilation errors from dangling references to deleted files.
8. Run the full Karma test suite and E2E suite to confirm no regressions. All tests should pass against `/` (V2) only, since `/v1` no longer exists.

### Verify
- No file under `web-ng/src/app/` contains an import or reference to V1's `AppComponent`
- `ng build --configuration production` passes with zero errors
- The full Karma test suite and E2E suite pass against `/`
- Navigating to `/v1` returns a 404 or redirects to `/` rather than rendering a broken page


---

## Implementation Notes

1. **Task 1 already done.** Upgrade button fix shipped in previous exec-guide (PR #60). `navigateToUpgrade()` replaces `logout()`. Skip this task.
2. **Task 2 is a CSS-only fix, not an HTML port.** The V1 and V2 HTML is already identical (same class names, same structure — verified by Playwright DOM comparison). The visual mismatch is purely CSS specificity. Follow the 3-step plan from the architecture doc: (a) empty 5 component CSS files, (b) slim app-v2.component.css to `.v2-shell` only, (c) verify ViewEncapsulation. This is 30 minutes, not 1.5 days.
3. **Flat file paths.** The guide uses subdirectory paths (`project-grid/project-grid.component.html`). Actual files are at `web-ng/src/app/` flat level per CLAUDE.md.
4. **Task 3: new spec files go at flat level** — `project-grid.component.spec.ts`, not `project-grid/project-grid.component.spec.ts`.
5. **Task 4: `/v2` already exists.** The route swap is changing the default `/` to V2 and moving V1 to `/v1`, not adding `/v2`.
