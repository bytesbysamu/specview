# Implementation Guide: Playground V4 — UX Overhaul

## Overview
This epic transforms the playground from a static component showcase into a narrative conversion tool by fixing four problems: the grid and detail views stack instead of being mutually exclusive, there is no visual before/after transformation moment, the pipeline section is static rather than interactive, and IntersectionObserver gating causes blank sections during fast scrolling. Tasks 1 and 2 can run in parallel. Task 3 depends on Task 1 (pipeline clicks into the detail view). Task 4 runs last after all interactive sections are stable.

## Shared Pre-flight
- Confirm the project builds cleanly by running `ng build --configuration production` from `web-ng/`
- Review the demo data file at `web-ng/src/app/playground-demo-data.ts` and confirm that Payment Gateway Redesign has content for all four stages: braindump, analysis, epic, and architecture
- Read the production view-switching logic in `web-ng/src/app/app-v2.component.ts` to understand the mutual-exclusion pattern (grid vs. detail) that the playground must mirror
- Read `web-ng/src/app/pg-scroll-shell.component.ts` and its HTML template to understand the current five-section orchestration and IntersectionObserver setup
- Read `web-ng/src/app/section-nav.component.ts` to understand the horizontal tab pattern used in production
- Read `web-ng/src/app/reader-panel.component.ts` to understand the content rendering approach that pipeline and detail views will reuse
- Confirm no existing tests are broken by running `ng test --watch=false` from `web-ng/`
- Review `web-ng/src/styles.css` for available newspaper design system tokens — no new tokens should be introduced

---

## Task 1: Grid-OR-Detail View Fix  [Effort: 2 days]

### What
The current Main Course section renders the project grid and detail panel simultaneously in a stacked layout. This task replaces that stacking with mutually exclusive view states — grid or detail, never both — mirroring the production behavior in `web-ng/src/app/app-v2.component.ts`. The detail view defaults to showing Payment Gateway Redesign's analysis on section entry so visitors see the richest content immediately.

### Files
- **Modify**: `web-ng/src/app/pg-section-live-app.component.ts` — Add an `activeView` signal with two states (`grid` and `detail`), wire project card clicks to switch to detail, add a close action to switch back to grid, and set the default to `detail` with Payment Gateway Redesign's analysis selected
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.ts` — Add an input signal on the Main Course section to accept external view/tab activation requests (needed later by Task 3's "See it live" handoff), and pass demo data to the refactored live-app section
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.html` — Update the Main Course section slot to pass the new input signal and demo data bindings to `pg-section-live-app`

### Steps
1. Open `web-ng/src/app/pg-section-live-app.component.ts` and define an Angular signal named `activeView` with a type union of `grid` and `detail`, defaulting to `detail`.
2. Define a second signal named `activeTab` to track which section tab is selected in detail view (braindump, analysis, epic, or architecture), defaulting to `analysis`.
3. Refactor the component template so that when `activeView` is `grid`, only the project grid markup renders using an `@if` block — remove it from the DOM entirely rather than hiding with CSS, matching production behavior.
4. When `activeView` is `detail`, render a mini-masthead element with the text "Specview" above the content area, followed by a horizontal section nav using the same tab pattern as `web-ng/src/app/section-nav.component.ts`, followed by the reader panel content area showing the selected stage's content from demo data.
5. Wire each project card in the grid to call a method that sets `activeView` to `detail` and sets `activeTab` to `analysis` for the clicked project.
6. Add a close button or back affordance in the detail view header that sets `activeView` back to `grid`.
7. In `web-ng/src/app/pg-scroll-shell.component.ts`, add an input signal on the live-app section child that accepts an object with a target view and tab selection, so Task 3 can programmatically activate detail view with a specific tab.
8. Update the scroll shell template to pass demo project data and the new activation signal to the live-app section component.

### Verify
- Open the playground route in a browser and confirm the Main Course section defaults to detail view showing Payment Gateway Redesign's analysis content with horizontal section tabs
- Click the close/back affordance and confirm the grid renders and the detail panel is fully removed from the DOM (inspect elements to verify, not just visual)
- Click a project card in the grid and confirm detail view appears with that project's analysis tab selected
- Run `ng build --configuration production` and confirm zero errors

---

## Task 2: Before/After Transformation Section  [Effort: 2 days]

### What
This task adds a new section between Greeting and Kitchen that shows the emotional "aha" moment: the same Payment Gateway Redesign content rendered first as a raw braindump and then as a structured spec analysis. The visitor sees the transformation without any interaction — both columns are visible simultaneously on scroll, with the right column revealing slightly after the left via a CSS transition.

### Files
- **Create**: `web-ng/src/app/pg-section-before-after.component.ts` — Standalone Angular component that renders a two-column layout sourcing braindump and analysis content from demo data
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.ts` — Import and register the new before-after section, insert it between the greeting and kitchen section slots
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.html` — Add the before-after section element between the greeting and kitchen sections
- **Modify**: `web-ng/src/styles.css` — Add the fade-translate-up animation class for the delayed right-column reveal (using only existing token values for spacing and typography)

### Steps
1. Create `web-ng/src/app/pg-section-before-after.component.ts` as a standalone Angular component with no dependencies on external services.
2. In the component, import the Payment Gateway Redesign project from `playground-demo-data.ts` and read its `braindump` field for the left column and its `analysis` field for the right column.
3. Build the template as a two-column CSS grid using the existing 12-column grid tokens from `web-ng/src/styles.css` — left column spans 5 columns, right column spans 7 columns, with a gap using the existing spacing scale.
4. Render the left column with the raw braindump text using a monospace or plain-text presentation style, applying existing typography tokens to convey "unprocessed input."
5. Render the right column with the structured analysis content using the same formatted rendering approach as the reader panel — headings, bullet structure, and section breaks using existing newspaper typography classes.
6. Add a CSS class to the right column that starts with `opacity: 0` and `transform: translateY(20px)`, transitioning to full opacity and zero translate when a `revealed` class is applied.
7. In the component class, use a single IntersectionObserver with a low threshold (0.1) on the section wrapper to add the `revealed` class when the section scrolls into view, triggering the right column's delayed appearance.
8. In `web-ng/src/app/pg-scroll-shell.component.ts`, import the new component and add it to the imports array.
9. Update `web-ng/src/app/pg-scroll-shell.component.html` to place the before-after section element between the greeting section and the kitchen section.

### Verify
- Open the playground route and scroll past the greeting section — confirm the before-after section appears with raw braindump text on the left and formatted analysis on the right
- Confirm the right column animates in with a subtle fade-translate-up after the left column is visible
- Confirm no new CSS custom properties or tokens were defined — only existing values from `web-ng/src/styles.css` are used
- Run `ng build --configuration production` and confirm zero errors and no increase in bundle size beyond the new component's template text

---

## Task 3: Interactive Pipeline Progression  [Effort: 3 days]

### What
This task transforms the static pipeline section from a description of stages into an interactive experience where the visitor clicks through four tabs (Braindump, Analysis, Epic, Architecture) and watches Payment Gateway Redesign's actual content change at each stage. On the final stage, a "See it live" affordance scrolls to the Main Course section and opens detail view with the architecture tab selected, creating narrative continuity.

### Files
- **Modify**: `web-ng/src/app/pg-pipeline.component.ts` — Replace the current static 5-step visualization with a 4-stage tabbed interface driven by an `activeStage` signal, rendering real demo data content for each stage
- **Modify**: `web-ng/src/app/pg-pipeline.component.html` — Restructure the template to show four horizontal stage tabs and a content reader area below
- **Modify**: `web-ng/src/app/pg-section-kitchen.component.ts` — Wire the pipeline component's "See it live" output event upward to the scroll shell
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.ts` — Handle the "See it live" event from the kitchen section by scrolling to the Main Course section and activating detail view with the architecture tab via the input signal added in Task 1

### Steps
1. Open `web-ng/src/app/pg-pipeline.component.ts` and define a local Angular signal named `activeStage` with a numeric type (0 through 3), defaulting to 0 (Braindump).
2. Import the Payment Gateway Redesign project from `playground-demo-data.ts` and map stages 0–3 to the project's braindump, analysis, epic, and architecture content fields respectively.
3. Refactor the template in `web-ng/src/app/pg-pipeline.component.html` to render four horizontal tabs labeled Braindump, Analysis, Epic, and Architecture, with the active tab visually distinguished using existing newspaper design system classes.
4. Below the tabs, render a content area that displays the demo content for the currently active stage, using the same formatted rendering approach as the reader panel for structured content and plain-text rendering for the braindump stage.
5. Wire each tab click to update the `activeStage` signal to the corresponding index.
6. On the Architecture tab (stage 3), add a "See it live" button or link affordance that emits an output event from the pipeline component.
7. In `web-ng/src/app/pg-section-kitchen.component.ts`, receive the pipeline component's output event and re-emit it as the kitchen section's own output event to the scroll shell.
8. In `web-ng/src/app/pg-scroll-shell.component.ts`, handle the kitchen section's "See it live" output event by scrolling the viewport to the Main Course section and setting the live-app section's activation input to detail view with the architecture tab selected.
9. Ensure the scroll-to-section behavior uses `scrollIntoView` with smooth behavior and positions the Main Course section at the top of the viewport.

### Verify
- Open the playground route and scroll to the pipeline section — confirm four stage tabs render horizontally with Braindump active by default
- Click each tab in sequence and confirm the content area updates with real Payment Gateway Redesign content for that stage — braindump shows raw text, analysis/epic/architecture show structured formatted content
- On the Architecture tab, click "See it live" and confirm the page scrolls smoothly to the Main Course section which switches to detail view with the architecture tab selected
- Run `ng build --configuration production` and confirm zero errors

---

## Task 4: Scroll Gating Removal & CSS Reveals  [Effort: 1 day]

### What
This task removes the JavaScript-driven IntersectionObserver section locking from V3 that causes blank sections during fast scrolling and replaces it with a lightweight CSS-only reveal animation. A single observer at a low threshold adds a `revealed` class to each section as its edge enters the viewport, triggering a CSS transition. Once revealed, sections stay visible permanently.

### Files
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.ts` — Replace the current high-threshold (0.6) IntersectionObserver with content-locking logic with a single low-threshold (0.1) observer that only adds a CSS class, remove all JavaScript content gating logic
- **Modify**: `web-ng/src/app/pg-scroll-shell.component.html` — Remove any conditional rendering directives tied to section visibility state, ensure all section elements are always present in the DOM with the initial hidden-state CSS class applied
- **Modify**: `web-ng/src/styles.css` — Add the section reveal animation classes: a default state with `opacity: 0` and `transform: translateY(20px)`, and a `.revealed` state that transitions to full opacity and zero translate using GPU-composited properties only

### Steps
1. Open `web-ng/src/app/pg-scroll-shell.component.ts` and locate the existing IntersectionObserver setup — identify the threshold value (currently 0.6), the callback logic that gates content rendering, and any signals or flags that control whether a section's content is shown.
2. Remove all JavaScript logic that conditionally hides or shows section content based on intersection state — this includes any signals, boolean flags, or template bindings that prevent a section from rendering its children.
3. Replace the observer with a single IntersectionObserver instance using a threshold of 0.1, observing all section wrapper elements.
4. In the observer callback, when a section entry's `isIntersecting` is true, add the CSS class `revealed` to that section's element and stop observing it (since sections stay revealed permanently).
5. Update `web-ng/src/app/pg-scroll-shell.component.html` to remove any `@if` blocks, `ngIf` directives, or conditional rendering tied to section visibility — all sections should always render their children in the DOM.
6. Add a default CSS class to each section wrapper (applied in the template) that sets `opacity: 0` and `transform: translateY(20px)`.
7. In `web-ng/src/styles.css`, define the `.revealed` class with a CSS transition that animates `opacity` to 1 and `transform` to `translateY(0)` over a duration that feels natural (approximately 0.6 seconds with an ease-out curve).
8. Ensure only compositor-friendly properties are animated — no `height`, `width`, `margin`, `padding`, or other layout-triggering properties in the transition.
9. Verify that the before-after section's own reveal animation from Task 2 integrates cleanly with this system — it should use the same `.revealed` class trigger rather than its own separate observer.
10. Remove the before-after section's standalone IntersectionObserver added in Task 2 and let the scroll shell's unified observer handle its reveal, ensuring the delayed right-column animation still fires as a child transition within the revealed section.

### Verify
- Open the playground route and scroll quickly from top to bottom — confirm no sections appear blank or locked at any scroll speed
- Scroll slowly and confirm each section fades in with the translate-up animation as its top edge enters the viewport
- Scroll back up and confirm all previously revealed sections remain fully visible (no re-hiding)
- Run `ng build --configuration production` and confirm zero errors and that only one IntersectionObserver instance is created (verify by searching the compiled output or adding a temporary log)