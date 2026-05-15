# Implementation Guide: Unified Page

## Overview
This epic unifies three disjointed experiences — landing pitch, design playground, and app workspace — into a single visually coherent page served at the root route. Work begins with an urgent trust-destroying bug where the upgrade button logs users out, then proceeds to replace all V2 CSS tokens with the newspaper design system, restore the full newspaper chrome into V2 component boundaries, wire up auth-aware page transitions without reload, and finally convert anonymous playground braindumps into persisted projects on signup. Tasks 1 and 2 are strictly sequential; Tasks 3 and 4 run in parallel after Task 2; Task 5 depends on both 3 and 4.

## Shared Pre-flight
- Ensure Node and Angular CLI are installed and `ng serve --port 4201` starts cleanly from the `web-ng/` directory.
- Run `ng build --configuration production` to confirm the build passes before making any changes.
- Familiarize yourself with the newspaper design tokens defined in `web-ng/src/styles.css`: `--ink`, `--bg` (`#FFFEF9`), `--border`, `--serif` (Playfair Display), `--sans` (Inter), `--body` (Source Serif 4).
- Confirm the V1 reference components and their HTML/SCSS are accessible for porting during Tasks 3 and 5.
- Verify that `web-ng/src/app/services/auth.service.ts` exposes the `isLoggedIn` signal from `TokenLifecycleService` and that `signOut()` clears tokens correctly.
- Confirm `web-ng/src/app/services/projects.service.ts` supports `createProject(name, braindump)` via `POST /api/projects`.
- Confirm `web-ng/src/app/services/subscription.service.ts` exposes the `plan` signal and `isPro` computed value.
- Review `web-ng/src/app/app.routes.ts` to understand the current route table: `/`, `/login`, `/signup`, `/upgrade`, and the wildcard fallback.

---

## Task 1: Upgrade Button Bug Fix  [Effort: 0.5 days]

### What
The upgrade button in the masthead currently calls `logout()` instead of `navigateToUpgrade()`, logging users out when they try to upgrade. This is a trust-destroying defect that must ship before any visual work because no amount of design polish recovers a user who clicked "upgrade" and lost their session.

### Files
- **Modify**: `web-ng/src/app/app.component.html` — change the upgrade button's click handler from `logout()` to `navigateToUpgrade()` in the `.masthead-actions` section.
- **Modify**: `web-ng/src/app/app.component.ts` — audit all action-to-handler mappings to confirm no other button is similarly misrouted; verify `navigateToUpgrade()` calls `this.router.navigate(['/upgrade'])`.

### Steps
1. Open `web-ng/src/app/app.component.html` and locate the upgrade button inside the `.masthead-actions` region. It is conditionally rendered when `!subscription.isPro()` is true. Change its click binding from `logout()` to `navigateToUpgrade()`.
2. Open `web-ng/src/app/app.component.ts` and confirm the `navigateToUpgrade()` method exists and navigates to `/upgrade` via the Angular router. If the method does not exist, add it with a single `this.router.navigate(['/upgrade'])` call.
3. While in `app.component.ts`, audit every other click handler referenced in the template to ensure no other action is bound to the wrong method. Pay special attention to the sign-out button, theme toggle, and new-project button — each must invoke its own dedicated handler.
4. Open the app in a browser, log in as a free-tier user, and click the upgrade button. Confirm it navigates to the `/upgrade` route and the user remains authenticated.
5. Repeat the test as a lapsed-plan user if possible, confirming the same navigation behavior.

### Verify
- Clicking the upgrade button while logged in navigates the browser to `/upgrade` without any logout side effect.
- The `isLoggedIn` signal remains `true` after clicking upgrade, confirmed by the masthead still rendering the authenticated layout.
- `ng build --configuration production` passes with no errors.

---

## Task 2: Design Token Unification  [Effort: 2 days]

### What
V2 components reference CSS variables (`--bg-primary`, `--text-primary`, `--border-default`, `--font-base`) that do not exist in the project stylesheet. This causes every V2 component to fall back to browser defaults — white backgrounds, system fonts, transparent borders — creating a visible quality cliff between the landing section and the app workspace. This task replaces every V2 token reference with the corresponding newspaper design system token so all components share one visual vocabulary.

### Files
- **Modify**: `web-ng/src/styles.css` — remove any lingering V2 token declarations if present; confirm the newspaper tokens (`--ink`, `--bg`, `--border`, `--serif`, `--sans`, `--body`, `--ink-light`, `--ink-muted`, `--red`, `--accent`, `--status-running`) are all defined in the `:root` block and the `[data-theme="dark"]` block.
- **Modify**: `web-ng/src/app/app.component.html` — update any inline style references that use V2 token names to use newspaper tokens.
- **Modify**: `web-ng/src/app/app.component.ts` — update any programmatic style assignments that reference V2 token names.
- **Modify**: `web-ng/src/app/components/upgrade/upgrade.component.ts` — replace V2 token references in the component's styles with newspaper tokens.
- **Modify**: `web-ng/src/app/components/usage-meter/usage-meter.component.ts` — replace V2 token references in component styles.
- **Modify**: `web-ng/src/app/components/login/login.component.ts` — replace V2 token references in component styles.
- **Modify**: `web-ng/src/app/pages/signup/signup.component.ts` — replace V2 token references in component styles.

### Steps
1. Search the entire `web-ng/src/` directory for every occurrence of `--bg-primary`, `--text-primary`, `--border-default`, and `--font-base`. Record every file and line where these tokens appear.
2. Perform the following mechanical replacements across all files found in step 1: `--bg-primary` becomes `--bg`, `--text-primary` becomes `--ink`, `--border-default` becomes `--border`, and `--font-base` becomes `--serif` for headings or `--body` for paragraph text (choose based on the element's semantic role).
3. Open `web-ng/src/styles.css` and confirm that no V2 token names remain as custom property declarations. Every token in the `:root` and `[data-theme="dark"]` selectors must belong to the newspaper design system.
4. Search for any remaining `font-family` declarations across all component files that reference system fonts or generic stacks directly instead of using `var(--serif)`, `var(--sans)`, or `var(--body)`. Replace them with the appropriate newspaper token.
5. Run `ng build --configuration production` to catch any undefined SCSS variable errors at compile time.
6. Launch the dev server and scroll through the full page — landing section, playground section, and app workspace. Confirm the background is a consistent warm cream (`#FFFEF9`) with no white gaps between sections. Confirm all text renders in the newspaper type stack: Playfair Display for display headings, Source Serif 4 for body text, and Inter/Source Sans 3 for UI chrome.
7. Toggle dark mode using the theme button and confirm all sections respond to the `[data-theme="dark"]` selector without any tokens falling through to undefined values.

### Verify
- A global search for `--bg-primary`, `--text-primary`, `--border-default`, and `--font-base` across `web-ng/src/` returns zero results.
- The background color is `#FFFEF9` across the full page scroll with no white gaps between sections.
- All visible text renders in the newspaper type stack — no system font fallbacks appear in the browser's computed styles for the app workspace section.
- `ng build --configuration production` passes with no errors.

---

## Task 3: Newspaper Chrome Restoration  [Effort: 2.5 days]

### What
The V1 newspaper chrome — masthead with edition/date/title/tagline, four-column project grid, status bar, section nav, and usage meter — must be restored to full visual fidelity within V2's decomposed component boundaries. This task ports V1's HTML structure into the existing V2 sub-components rather than re-skinning V2's generic markup, because V1's DOM was authored for the newspaper design tokens and forcing V1's visual language onto V2's DOM creates a permanent impedance mismatch.

### Files
- **Modify**: `web-ng/src/app/app.component.html` — replace the masthead markup in the `.masthead` region with V1's HTML structure: edition line (overline), date, title in Playfair Display at 64px, italic tagline in Source Serif 4, and the masthead action buttons.
- **Modify**: `web-ng/src/styles.css` — add or update styles for `.masthead`, `.masthead-edition`, `.masthead-date`, `.masthead-title`, `.masthead-tagline`, `.section-nav`, `.gen-status-bar`, `.file-grid`, `.section-group`, `.section-group-header`, `.file-item`, `.featured`, `.hero-grid`, `.hero-main`, `.hero-secondary`, and `.file-column` to match V1's newspaper layout.
- **Modify**: `web-ng/src/app/components/usage-meter/usage-meter.component.ts` — port V1's usage meter HTML into this standalone component, displaying remaining/limit counts with newspaper styling and the warning state when remaining is 1 or fewer.
- **Modify**: `web-ng/src/app/app.component.ts` — add or update the `columns()` computed signal for the three-column single-section masonry layout and ensure the `projectsBySection()` computed groups projects correctly for the multi-column grid.
- **Create**: `web-ng/src/app/components/masthead/masthead.component.ts` — extract the masthead into its own standalone component if the shell exceeds the 200-line limit, accepting subscription state and user info as input signals.

### Steps
1. Open V1's original template and identify the exact HTML structure for the masthead: the edition overline, formatted date, Playfair Display title, italic Source Serif tagline, and the row of action buttons (new project, theme toggle, upgrade, sign out).
2. Replace the current `.masthead` markup in `web-ng/src/app/app.component.html` with V1's HTML structure, using Angular 17 `@if` control flow for conditional elements (upgrade button hidden for Pro users, usage meter visible only for free-tier users).
3. Port V1's section nav HTML into the `.section-nav` region of the template. Each nav button should display its section name and a count badge using the `sectionCounts()` computed signal. Apply the 3px `--ink` border-top and the `.section-count-pulse` animation class for count changes.
4. Port V1's project grid HTML into the `.file-grid` region. Implement the section grouping with `.section-group` wrappers, each containing a `.section-group-header` and a card grid. The first card in each section receives the `.featured` class. The "Active" section uses the `.hero-grid` layout with a lead story at `2fr` and two secondaries at `1fr` each.
5. Port V1's status bar HTML into the `.gen-status-bar` region. Implement the four visual states (idle, active with animated dots, success flash, failure) driven by the `statusMode()` signal.
6. Open `web-ng/src/app/components/usage-meter/usage-meter.component.ts` and port V1's usage meter template into the component. It should display "N/M remaining" text, apply the `isWarning()` computed for low-usage styling, and remain hidden for Pro users via the `isVisible()` computed.
7. Update `web-ng/src/styles.css` with the newspaper layout styles: the four-column grid using `auto-fill minmax(280px, 1fr)` with 1px gap for hairline separators, the `.featured` card enhancement (17px title, 3-line clamp), the `.hero-grid` layout, and the `.file-column` border-right dividers for single-section three-column views.
8. Measure the line count of `web-ng/src/app/app.component.ts`. If it exceeds 200 lines, extract the masthead into a new `web-ng/src/app/components/masthead/masthead.component.ts` standalone component, passing subscription state, user info, and action callbacks as input signals and output events.
9. Run the dev server and visually compare the masthead, section nav, project grid, status bar, and usage meter against V1's appearance. Confirm Playfair Display renders at 64px for the title, section headers use the correct newspaper typography, and the grid renders in multi-column layout with featured cards and section grouping.

### Verify
- The masthead displays edition, date, title in Playfair Display, and italic tagline — all using newspaper design tokens.
- The project grid renders in multi-column newspaper layout with featured cards, section grouping, and hairline separators — not a compressed single-column list.
- The status bar correctly cycles through its four visual states (idle, active, success, failure) during a spec generation operation.
- `ng build --configuration production` passes with no errors.

---

## Task 4: Auth-Aware Page Transition  [Effort: 2 days]

### What
When a visitor logs in or a user logs out, the page must transition between anonymous and authenticated states without a full page reload or visual jarring. The landing pitch collapses, the playground crossfades into "create new project," and the workspace fades in — all driven by CSS transitions triggered by a signal state change in the shell component. This task also introduces the three-zone layout structure (landing pitch zone, playground/create zone, workspace zone) that the shell component composites via `@if` blocks bound to auth state.

### Files
- **Modify**: `web-ng/src/app/app.component.html` — restructure the template into three vertical zones: landing pitch zone (visible to anonymous visitors), playground/create zone (playground for anonymous, "new project" for authenticated), and workspace zone (project grid for authenticated). Add CSS transition classes for the auth state change animations.
- **Modify**: `web-ng/src/app/app.component.ts` — add signals for transition state management: a `transitionPhase` signal to track animation progress, an `effect()` that responds to auth state changes by applying transition classes, and a `transitionend` listener that updates the secondary signal to remove collapsed DOM after animation completes.
- **Modify**: `web-ng/src/styles.css` — add CSS transition declarations for the landing pitch collapse (`max-height`, `opacity`), the playground/create crossfade (`opacity`, `transform`), and the workspace fade-in (`opacity`). Define the `.zone-landing`, `.zone-playground`, `.zone-workspace` layout classes and their transition-state variants.

### Steps
1. In `web-ng/src/app/app.component.html`, wrap the existing landing pitch content in a `.zone-landing` container. This zone is visible to anonymous visitors and receives a `.zone-collapsing` class during the login transition.
2. Add a `.zone-playground` container below the landing zone. For anonymous visitors, this renders the playground input area. For authenticated users, it renders a "create new project" entry point that reuses the same input area but saves directly to a project instead of localStorage.
3. Add a `.zone-workspace` container that wraps the existing project grid, section nav, and expanded panel. This zone is hidden for anonymous visitors and fades in during the login transition.
4. In `web-ng/src/app/app.component.ts`, create a `transitionPhase` signal with values like `idle`, `collapsing`, and `complete`. Add an `effect()` that watches the `isLoggedIn` signal from `AuthService`. When auth state changes from false to true, set `transitionPhase` to `collapsing`, which triggers CSS classes on the zones. When auth state changes from true to false, play the reverse animation.
5. Add a `transitionend` event listener on the `.zone-landing` element. When the collapse animation finishes, update a secondary signal (such as `landingVisible`) to false, allowing Angular's `@if` to remove the landing DOM. This prevents the flash of missing content that would occur if the DOM were removed at the start of the state change.
6. In `web-ng/src/styles.css`, define transitions on `.zone-landing` for `max-height` and `opacity` with appropriate durations (around 400ms). Use `overflow: hidden` during the collapse to prevent content reflow. Define a fade-in transition on `.zone-workspace` using `opacity` and a slight upward `transform` translation. Define a crossfade on `.zone-playground` using `opacity`.
7. Ensure all three zones share one continuous scroll context with no iframes, no lazy-loaded route children, and no shadow DOM boundaries that would fragment the CSS cascade.
8. Test the login transition: as an anonymous visitor, observe the landing pitch, then log in and confirm the landing pitch slides up and collapses, the playground crossfades into the "create new project" variant, and the workspace fades in below — all without a page reload.
9. Test the logout transition: while authenticated, click sign out and confirm the workspace fades out, the landing pitch expands back in, and the playground reverts to its anonymous variant.

### Verify
- Logging in transitions the page from anonymous to authenticated state without a full page reload — the URL remains `/`.
- The landing pitch collapses with a smooth animation rather than an instant disappearance, and the workspace zone fades in without layout shift.
- Logging out plays the reverse transition: workspace fades out, landing pitch expands back in.
- `ng build --configuration production` passes with no errors.

---

## Task 5: Playground-to-Project Conversion  [Effort: 1.5 days]

### What
An anonymous visitor's braindump entered in the playground must survive signup and become their first project. This is the architectural expression of the "demo IS the product" philosophy — the visitor's work is never disposable. The persistence strategy uses localStorage as a bridge between anonymous and authenticated states, and the shell component orchestrates the conversion on auth state change.

### Files
- **Modify**: `web-ng/src/app/app.component.html` — wire the playground textarea's input event to a debounced save function that persists content to localStorage under a well-known key. Update the "create new project" zone variant for authenticated users to pre-populate from localStorage if content exists.
- **Modify**: `web-ng/src/app/app.component.ts` — add a `saveBraindumpToLocalStorage()` method that debounces writes to a localStorage key (such as `specview_playground_braindump`). Add logic to the auth state change `effect()` that checks for the localStorage key on login, calls `createProject()` on `ProjectsService` with the stored content, then clears the key. Add a `pendingBraindump` signal to track the conversion flow.
- **Modify**: `web-ng/src/app/services/projects.service.ts` — confirm that `createProject(name, braindump)` accepts a braindump string and passes it through to `POST /api/projects`. If the method only accepts a name, extend it to also accept an optional braindump parameter.
- **Modify**: `web-ng/src/styles.css` — add styles for the playground textarea zone in both anonymous and authenticated variants, using newspaper design tokens for consistent visual treatment.

### Steps
1. Define a constant for the localStorage key, such as `specview_playground_braindump`, in `web-ng/src/app/app.component.ts`.
2. Add a `saveBraindumpToLocalStorage()` method that writes the playground textarea's current value to localStorage. Debounce this method so it fires at most once every 500 milliseconds to avoid excessive writes on every keystroke.
3. In `web-ng/src/app/app.component.html`, bind the playground textarea's input event to the debounced save method. This ensures every anonymous visitor's braindump is auto-persisted as they type.
4. Extend the auth state change `effect()` in `web-ng/src/app/app.component.ts` to check for the localStorage key when `isLoggedIn` transitions from false to true. If content is found, call `ProjectsService.createProject()` with a default project name (such as "My First Project") and the stored braindump content.
5. After the project creation call succeeds, call the braindump bootstrap endpoint via `ProjectsService.startBootstrap()` if the content warrants generation, then clear the localStorage key to prevent duplicate conversion on subsequent logins.
6. Add a `pendingBraindump` signal that is set to true during the conversion process and false once complete. Use this signal to display a brief loading indicator in the workspace zone while the project is being created.
7. Confirm that `ProjectsService.createProject()` in `web-ng/src/app/services/projects.service.ts` passes the braindump content through to the `POST /api/projects` endpoint. If the current implementation only sends the project name, add the braindump field to the request body.
8. Handle the edge case where the localStorage content is empty or only whitespace — skip the conversion and clear the key silently.
9. Test the full flow: open the app as an anonymous visitor, type a braindump into the playground, then sign up via the `/signup` page. After signup completes and the page transitions to the authenticated state, confirm the braindump appears as the user's first project in the workspace grid.
10. Test that a returning authenticated user who had no anonymous braindump sees the normal "create new project" entry point with no leftover localStorage artifacts.

### Verify
- A braindump entered anonymously in the playground survives signup and appears as the user's first project in the authenticated workspace.
- The localStorage key is cleared after successful project creation, so refreshing the page does not trigger a duplicate conversion.
- An authenticated user with no pending braindump sees the standard "create new project" entry point with no errors in the browser console.
- `ng build --configuration production` passes with no errors.


---

## Implementation Notes

1. **Task 1 targets the wrong file.** The logout bug is in `app-v2.component.html` line 50, not `app.component.html`. The V1 app already has the correct handler.
2. **Task 2 targets the wrong files.** The V2 CSS token problem is in the V2 components: `app-v2.component.css`, `section-nav.component.css`, `status-bar.component.css`, `project-grid.component.css`, `sidebar-v2.component.css`, `reader-panel.component.css`. The V1 components (upgrade, usage-meter, login, signup) already use newspaper tokens.
3. **Task 3: flat structure.** Do not create `components/masthead/`. New components go at `web-ng/src/app/` level per CLAUDE.md.
4. **Task 3 targets the wrong template.** Port V1 HTML into the V2 sub-components, not into `app.component.html`. The V1 app stays untouched.
5. **Task 4 is over-engineered.** Use a simple `@if (auth.isLoggedIn())` toggle, same as V1. No `transitionPhase` signal, no `transitionend` listeners, no three-zone state machine. CSS transitions on opacity/max-height are fine as polish later, not MVP.
