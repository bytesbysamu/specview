# Implementation Guide: Playground 2.0 — Specview Case Study + UX Audit

## Overview
This epic transforms the existing `/playground` component reference into a narrative case study that follows a 3-act arc (hook, method, product). Task 1 establishes the narrative shell and route wiring; Tasks 2 and 3 build the hero and pipeline sections in parallel on top of that shell; Task 4 wraps existing Phase 1/2 demo sections with editorial context (also parallel with 2–3); Task 5 closes the page with a journey map after the hero and pipeline land. All existing anchor links and Phase 1/2 components remain untouched — new components compose around them.

## Shared Pre-flight
- Confirm Angular 17 standalone component builds cleanly: run `ng build --configuration production` with zero errors before starting
- Verify all existing anchor fragments work (`#tokens`, `#borders`, `#animations`, `#state-matrix`, `#components-app`, `#components-ui`) by scrolling to each on the current `/playground`
- Confirm dark-mode toggle flips all existing `pg-*` components via CSS custom properties — no component-scoped color overrides present
- Audit `src/app/styles.css` for the global classes that new sections will use: `.overline`, `.headline`, `.deck`, `.pullquote-row`, `.section-heading`, `.lede`
- Locate `src/app/playground-demo-data.ts` and confirm it already exports demo fixtures
- Locate `src/app/live-playground.component.ts` and note the section nav pattern and the list of composed `pg-*` selectors
- Confirm the `pg-` prefix naming convention in `src/app/` for all playground component files
- Verify `app.routes.ts` currently maps `/playground` to `LivePlaygroundComponent`

---

## Task 1: Narrative Shell + Route Architecture  [Effort: 1 day]

### What
Create the top-level case study shell component that replaces `LivePlaygroundComponent` as the route target for `/playground`. This shell sequences all narrative and existing demo sections in the correct scroll order, provides fragment-anchor deep linking, and uses an IntersectionObserver to highlight the active section in the nav bar.

### Files
- **Create**: `src/app/pg-case-study.component.ts` — standalone component serving as the narrative shell; template-only orchestrator composing all sections top-to-bottom
- **Modify**: `src/app/app.routes.ts` — change the `/playground` path to load `PgCaseStudyComponent` instead of `LivePlaygroundComponent`

### Steps
1. Create `pg-case-study.component.ts` as a standalone Angular component with no services or HTTP dependencies. Its template lists placeholder selectors for each section in order: hero, pipeline, four narrative wrappers (design, screens, patterns, dark), and journey map — using HTML comment placeholders for components that do not yet exist.
2. Move the section nav bar markup from `live-playground.component.ts` into the new shell's template. Update nav item labels to reflect the narrative arc (e.g., "The Pitch" instead of "Tokens") and point each link to a fragment anchor.
3. Wire up a single IntersectionObserver in the component class that watches each section heading element. When a heading crosses the viewport top threshold, set the active nav item accordingly using a signal.
4. Bind the existing app-level dark-mode signal so that the shell's host element reflects the current theme class, ensuring all child components inherit it through CSS custom properties.
5. Update `app.routes.ts` to import `PgCaseStudyComponent` and assign it to the `/playground` path. Leave `LivePlaygroundComponent` in the codebase untouched.
6. Within the shell template, render existing `pg-*` selectors (pg-tokens, pg-borders, pg-animations, pg-state-matrix, pg-components-app, pg-components-ui) in their correct positions so that all Phase 1/2 anchors remain functional immediately.

### Verify
- `ng build --configuration production` succeeds with zero errors
- Navigating to `/playground` renders the new shell with existing Phase 1/2 component demos visible
- All six existing anchor fragments (`#tokens`, `#borders`, `#animations`, `#state-matrix`, `#components-app`, `#components-ui`) scroll to the correct position
- Dark-mode toggle flips the entire page including the nav bar

---

## Task 2: Hero + Problem Section (Above the Fold)  [Effort: 2 days]

### What
Build the above-the-fold hero component that hooks the visitor with the "Write messy. Ship clean." tagline, a stat strip, and a before/after layout showing a messy braindump transforming into structured documents. A canned CSS animation of the status bar component demonstrates file generation without live API calls.

### Files
- **Create**: `src/app/pg-hero.component.ts` — standalone component containing the hero section with tagline, stat strip, before/after layout, and CSS-animated status bar demo
- **Modify**: `src/app/pg-case-study.component.ts` — import and render `pg-hero` selector at position 1 in the template, replacing the placeholder

### Steps
1. Create `pg-hero.component.ts` as a standalone component. Structure the template into three vertical zones: tagline block, stat strip, and before/after lede grid.
2. Implement the tagline block using the `.headline` class with Playfair Display for the main line ("Write messy. Ship clean.") and a `.deck` paragraph in Source Serif explaining the one-sentence value proposition.
3. Build the stat strip as four inline items (44.5s average generation time, 5 files per run, 0 code required, Free tier available) using the same pattern found in the landing page — Playfair Display numbers with Source Sans labels.
4. Lay out the before/after section using the existing `.lede` two-column grid from `styles.css`. Place a styled braindump text block (representing messy input) in `.lede-main` and a set of five document title cards (representing structured output) in the lede aside, separated by the column rule.
5. Render the existing `status-bar.component` inside the hero in a demonstration loop state. Add a CSS keyframe animation that cycles through five file names appearing sequentially, simulating generation progress. Keep the animation purely in CSS with no TypeScript logic.
6. Add a "Try it free" call-to-action button at the bottom of the hero section using the existing CTA pattern: square button, `var(--ink)` background, `var(--bg)` text, no border-radius.
7. Update the shell template to import and render `pg-hero` at position 1.

### Verify
- The hero section appears above the fold when loading `/playground` at 1440px viewport width
- Stat strip renders four items horizontally with correct typography (Playfair numbers, Source Sans labels)
- The status bar CSS animation loops continuously without JavaScript errors in the console
- Dark-mode toggle correctly flips all hero elements (backgrounds, text colors, borders) via CSS custom properties

---

## Task 3: Pipeline Visualization (5-Step Flow)  [Effort: 2 days]

### What
Build a horizontal 5-step pipeline component showing the spec generation flow (braindump, analysis, epic, architecture, implementation guide). Each step is clickable and reveals a hardcoded document preview panel below using the expanded panel pattern.

### Files
- **Create**: `src/app/pg-pipeline.component.ts` — standalone component with horizontal 5-column grid and click-to-reveal preview panel
- **Modify**: `src/app/playground-demo-data.ts` — add pipeline preview content (3–4 paragraphs per document type) as exported constants
- **Modify**: `src/app/pg-case-study.component.ts` — import and render `pg-pipeline` selector at position 2 in the template

### Steps
1. Add five pipeline preview content blocks to `playground-demo-data.ts`. Each block is a short representative excerpt for one document type (analysis findings, epic scope, architecture decisions, implementation steps, braindump source). Keep each under four paragraphs to avoid bloating page weight.
2. Create `pg-pipeline.component.ts` as a standalone component. Define a signal tracking which step (0–4) is currently selected, defaulting to none.
3. Build the template's top section as a CSS grid with five equal columns separated by `1px solid var(--border)` column rules. Each column contains a decorative Playfair Display step number (styled at 64px in `var(--border)` color), a Source Sans uppercase label, and a one-line Source Serif description.
4. Attach a click handler to each step column that sets the selected-step signal to that column's index.
5. Below the grid, conditionally render the preview panel when a step is selected. Style the panel with `border-top: 3px solid var(--ink)` and `border-bottom: 1px solid var(--border)`, using two-column body text with `column-rule` — the expanded panel pattern from the design system.
6. Populate the preview panel content by reading from the imported demo data constants based on the selected step index.
7. Update the shell template to import and render `pg-pipeline` at position 2, directly after the hero.

### Verify
- All five pipeline steps render horizontally with correct column-rule separators at desktop viewport
- Clicking any step reveals the preview panel with content matching that document type
- Clicking a different step swaps the preview content without page scroll jumping
- Dark-mode toggle flips pipeline colors (border, ink, background) correctly

---

## Task 4: Narrative Wrappers for Phase 1/2 Sections  [Effort: 1.5 days]

### What
Create four thin editorial wrapper components that add overlines, headlines, deck text, and pull quotes around existing Phase 1/2 demo sections. These wrappers provide the "why" context without modifying the existing `pg-*` components, preserving all anchor links and dark-mode behavior.

### Files
- **Create**: `src/app/pg-narrative-design.component.ts` — wraps `pg-tokens` and `pg-borders` with Design Language editorial context
- **Create**: `src/app/pg-narrative-screens.component.ts` — wraps `pg-components-app` and `pg-components-ui` with Screen Gallery editorial context
- **Create**: `src/app/pg-narrative-patterns.component.ts` — wraps `pg-animations` and `pg-state-matrix` with Design Patterns editorial context
- **Create**: `src/app/pg-narrative-dark.component.ts` — wraps the dark-mode demo with editorial context plus a static token diff table
- **Modify**: `src/app/pg-case-study.component.ts` — replace direct `pg-*` component selectors with the four narrative wrapper selectors at positions 3–6

### Steps
1. Create `pg-narrative-design.component.ts`. Its template begins with a `.section-heading` strip, followed by a `.overline` in `var(--red)`, a `.headline` in Playfair Display explaining the Design Language philosophy, and a `.deck` paragraph in Source Serif. Below the deck, render `pg-tokens` and `pg-borders` via their selectors. Close with a `.pullquote-row` tying the design language back to the product narrative.
2. Create `pg-narrative-screens.component.ts` following the same structural pattern. The editorial content explains why the screen gallery demonstrates real application states. Render `pg-components-app` and `pg-components-ui` inside. Close with a pull quote about live components replacing static screenshots.
3. Create `pg-narrative-patterns.component.ts` following the same pattern. The editorial content explains why animation and state management patterns matter for perceived quality. Render `pg-animations` and `pg-state-matrix` inside. Close with a pull quote.
4. Create `pg-narrative-dark.component.ts` following the same pattern but adding one extra element: a static HTML table below the existing dark-mode demo showing the light-to-dark CSS custom property mappings (e.g., --ink, --bg, --border, --red values in both themes). Style the table using existing newspaper table classes.
5. In each wrapper, ensure the existing `pg-*` components keep their original anchor `id` attributes by not wrapping them in elements that would steal or shadow those IDs.
6. Update the shell template to remove the direct `pg-*` selectors for tokens, borders, animations, state-matrix, components-app, and components-ui. Replace them with the four narrative wrapper selectors at the correct positions in the scroll order.

### Verify
- All six original anchor fragments (`#tokens`, `#borders`, `#animations`, `#state-matrix`, `#components-app`, `#components-ui`) still scroll to the correct element
- Each narrative wrapper displays an overline, headline, deck, the live component demos, and a closing pull quote
- The token diff table in `pg-narrative-dark` renders with correct light and dark values and flips appropriately with the dark-mode toggle
- `ng build --configuration production` succeeds with no template compilation errors

---

## Task 5: Journey Map (User Flow Timeline)  [Effort: 1.5 days]

### What
Build a horizontal newspaper-style timeline component showing the user journey from anonymous visitor to power user. This is the conversion-oriented closing section, ending with a call-to-action. On viewports under 768px, the timeline degrades to a vertical stack via CSS only.

### Files
- **Create**: `src/app/pg-journey.component.ts` — standalone component with horizontal timeline of ten stations and a closing CTA
- **Modify**: `src/app/pg-case-study.component.ts` — import and render `pg-journey` selector at the final position in the template

### Steps
1. Create `pg-journey.component.ts` as a standalone component with no services or logic. Define the ten journey stations as a static array in the component class: Land on page, See the pitch, Explore playground, Sign up, Create project, Generate specs, Read in newspaper layout, Iterate with AI ops, Upgrade to Pro, Share specs publicly.
2. Build the template as a horizontal flex or grid container with `overflow-x: auto` for narrow viewports. Each station renders a Source Sans uppercase label, a Playfair Display station name, and a Source Serif one-line description. Separate stations with `1px solid var(--border)` vertical rules.
3. Style the final station ("Share specs publicly") to include an inline CTA button matching the existing pattern: square button with `var(--ink)` background, `var(--bg)` text, no border-radius.
4. Add a CSS media query for viewports under 768px that switches the container to a vertical stack layout, converting each station to a full-width row separated by horizontal rules instead of vertical ones.
5. Update the shell template to import and render `pg-journey` as the last section in the scroll order, after `pg-narrative-dark`.
6. Ensure the journey map section has a fragment anchor (e.g., `id="journey"`) and that the section nav bar in the shell includes a corresponding nav item.

### Verify
- The journey map renders ten stations horizontally at 1440px viewport width with visible column-rule separators
- At 375px viewport width, the timeline stacks vertically with horizontal separators and no horizontal overflow
- The final station's CTA button displays with correct square styling and ink/bg color contrast
- Dark-mode toggle flips all journey map elements correctly without any hardcoded color values showing through
---

## Implementation Notes

1. **LivePlaygroundComponent cleanup.** Task 1 leaves it in the codebase — add deletion to a follow-up cleanup task after the case study is validated.
2. **Journey stations.** 10 stations is a lot for a horizontal timeline. Consider trimming to 6-7 during implementation (combine "Land + See pitch" and "Iterate + Upgrade" into single stations).
3. **Hero stat strip.** Should reference shared constants (same values as landing page) rather than hardcoding. Extract to `playground-demo-data.ts` or a shared constants file.
