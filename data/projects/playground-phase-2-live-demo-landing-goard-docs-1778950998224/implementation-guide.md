# Implementation Guide: Playground Phase 2 — Live Demo, Landing & Goard Docs

## Overview
**The playground is the superset.** It contains everything — the design system, the live app demo, and every landing page pattern. The landing page is a downstream artifact: a curated extract of playground sections into pure HTML. This means we build ALL patterns in the playground first (Angular, interactive, dark-mode aware), then pick and choose what goes on the landing page and export it.

This epic adds the live app demo, a Goard-inspired problem statement, the complete set of landing page patterns as Angular components, navigation acts, and a journey map. Tasks 1, 2, and 3 can proceed in parallel; Task 4 (nav acts) depends on all three; Task 5 (journey map) depends on Task 2. Landing page extraction into pure HTML is Phase 3.

## Shared Pre-flight
- Confirm Angular 17 standalone component conventions are followed: signals, OnPush change detection, `@if`/`@for` control flow — no `*ngIf`/`*ngFor`
- Verify `LivePlaygroundComponent` still compiles and renders with demo data before building around it
- Confirm production components (`ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `SectionNavComponent`, `StatusBarComponent`) are importable without triggering HTTP side effects
- Ensure all styling uses existing global CSS classes and design tokens from `styles.css` — zero new custom properties, no border-radius, no shadows
- Validate that `playground-demo-data.ts` exports `DEMO_PROJECTS` and `DEMO_NAV_SECTIONS` as expected
- All new components use `ChangeDetectionStrategy.OnPush` and are declared as standalone
- All new sections must receive unique `id` attributes so the existing IntersectionObserver picks them up automatically
- Run `ng build --configuration production` with zero errors and zero warnings as the gating check after each task

---

## Task 1: Live App Demo Section  [Effort: 2 days]

### What
Embed the actual specview app experience inside the case study narrative by composing production components (`ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `SectionNavComponent`, `StatusBarComponent`) with demo data, wrapped in editorial framing (overline, headline, deck, pullquote). Visitors can click through project grids, browse specs, and read rendered markdown without any API calls.

### Files
- **Create**: `web-ng/src/app/pg-live-demo.component.ts` — standalone component that imports production app components, manages local selection state via signals, and renders the editorial wrapper plus live demo frame
- **Modify**: `web-ng/src/app/playground-demo-data.ts` — add a ninth demo project pre-configured with `statusState: 'active'` and partially-generated files to showcase generation-in-progress state
- **Modify**: `web-ng/src/app/pg-case-study.component.ts` — import `PgLiveDemoComponent`, add its template tag in the scroll container after the pipeline section, add `live-demo` to the section ID array, remove `LivePlaygroundComponent` from the rendered template

### Steps
1. Open `playground-demo-data.ts` and add a new project object to the `DEMO_PROJECTS` array with `statusState: 'active'`, a project name like "API Platform Spec," and three partially-generated files with markdown content to demonstrate the shimmer animation and in-progress status bar.
2. Create `pg-live-demo.component.ts` as a standalone component with OnPush change detection. Define local signals for `selectedProject`, `selectedFile`, and `activeSections`, initializing `selectedProject` to the first demo project.
3. Add a `computed()` signal that derives the file list from the currently selected project, mirroring the production app's derivation pattern.
4. Build the component template with three zones: an editorial header (overline reading "The Product," headline, and a one-sentence deck explaining this is the real app with demo data), the demo frame containing the five production components arranged in the same layout as `app-v2.component.ts`, and a closing pullquote reflecting on the live-component-over-screenshot philosophy.
5. Wire each production component via input bindings — pass `DEMO_PROJECTS` to `ProjectGridComponent`, the derived file list to `SidebarV2Component`, the selected file content to `ReaderPanelComponent`, section filters to `SectionNavComponent`, and the status state signal to `StatusBarComponent`.
6. Audit each production component's constructor and `ngOnInit` for service injections that trigger HTTP calls. If any exist, provide a no-op implementation in the component's `providers` array.
7. Apply the demo frame styling using a subtle 1px border with existing `--border` token and near-full-width layout. Add a small annotation below the status bar reading "Demo — generation simulation" for the active-state project.
8. Open `pg-case-study.component.ts`, add the import for `PgLiveDemoComponent`, insert its template tag with `id="live-demo"` after the pipeline section, and remove the old `LivePlaygroundComponent` reference from the template.

### Verify
- The live demo renders at `/playground` showing the project grid, sidebar, reader panel, section nav, and status bar populated with demo data
- Clicking a project in the grid updates the sidebar file list and reader panel content without any network requests (confirm via browser DevTools Network tab)
- The ninth "active" project displays the shimmer animation on the status bar
- `ng build --configuration production` passes with zero errors and zero warnings

---

## Task 2: Problem Statement Section  [Effort: 1 day]

### What
Create a Goard-inspired editorial section that articulates why specs matter, what happens without them, and what pain specview eliminates. This establishes narrative context that the live demo and journey map build upon. Pure content — no data binding, no interactivity.

### Files
- **Create**: `web-ng/src/app/pg-problem.component.ts` — standalone component containing three pain-point editorial blocks with pullquote callouts, using inline template content
- **Modify**: `web-ng/src/app/pg-case-study.component.ts` — import `PgProblemComponent`, insert its template tag after the hero section, add `problem` to the section ID array

### Steps
1. Create `pg-problem.component.ts` as a standalone component with OnPush change detection and an inline template.
2. Structure the template with the overline/headline/deck pattern: overline reading "The Problem," a headline articulating the core tension (specs are critical but nobody writes them), and a deck sentence expanding on the cost of skipping specs.
3. Add three pain-point blocks, each containing a section heading (using `.section-heading` class) and a body paragraph (using `.body-text` class). The three pain points should address: ambiguous requirements causing rework, architecture decisions made without documentation causing drift, and handoff friction between planning and implementation.
4. Insert a two-column pullquote row between the second and third pain points using the existing pullquote styling pattern from Phase 1 sections.
5. Add a closing argument paragraph after the third pain point that transitions toward the solution (specview's generation approach).
6. Open `pg-case-study.component.ts`, import `PgProblemComponent`, and insert its template tag with `id="problem"` between the hero section and the pipeline section.

### Verify
- The problem statement section renders between the hero and pipeline sections at `/playground`
- All three pain points are visible with correct typography (section headings in the established style, body text legible)
- Dark mode toggle applies correctly — text, backgrounds, and pullquote styling all respond to theme change
- `ng build --configuration production` passes with zero errors and zero warnings

---

## Task 3: Complete Landing Page Patterns as Angular Components  [Effort: 4 days]

### What
The playground is the superset — it must contain every landing page pattern as an interactive Angular component. This includes the masthead, output cards, how-it-works steps, comparison table, pricing tiers, FAQ accordion, stat strip, and pull quotes. All patterns are built here first; the static landing page will be extracted from these components in Phase 3.

### Files
- **Create**: `web-ng/src/app/pg-landing-showcase.component.ts` — standalone component containing ALL landing page patterns: masthead, output cards, how-it-works steps, comparison table, pricing tiers, FAQ accordion, and pull quotes
- **Create**: `web-ng/src/app/pg-landing-data.ts` — const data arrays for all landing content (output cards, steps, comparison rows, pricing tiers, FAQ items, pull quotes)
- **Modify**: `web-ng/src/app/pg-case-study.component.ts` — import `PgLandingShowcaseComponent`, insert its template tag after the live demo section, add `landing-showcase` to the section ID array

### Steps
1. Create `pg-landing-data.ts` with exported const arrays for all landing content:
   - `OUTPUT_CARDS`: five deliverables (Analysis, Epic, Architecture, Timeline, Implementation Guide) with icon (Unicode glyph), filename, and description
   - `HOW_IT_WORKS_STEPS`: three steps (Braindump, Generate, Implement) with title, body, and representative content excerpt
   - `COMPARISON_ROWS`: dimension-by-dimension comparison (Input, Output, Architecture, Docs, Quality, Pricing) with competitor column (Lovable/Bolt/Kiro) and Specview column
   - `PRICING_TIERS`: Free and Pro tiers with price, description, and feature lists
   - `FAQ_ITEMS`: 5-7 questions and answers covering common product questions
   - `PULL_QUOTES`: testimonial-style quotes about using Specview
2. Create `pg-landing-showcase.component.ts` as a standalone component with OnPush change detection. Import all data from `pg-landing-data.ts`.
3. Build the **masthead section**: "Vol. II" edition line, "Specview" title in 64px Playfair Display, "All the Specs Fit to Build" tagline — the newspaper header that sets the editorial tone. Include dark-mode toggle.
4. Build the **output cards section**: four-column grid (collapsing to two below 768px) showing the five deliverables with icon, filename in monospace, and description.
5. Build the **how-it-works section**: three numbered steps at 96px Playfair Display step numbers, with title, body text, and representative content excerpt styled with a left border accent.
6. Build the **comparison table**: full-width table with serif headers, sans-serif cells. Three columns: Dimension, Competitors, Specview. Competitor column gets muted styling.
7. Build the **pricing section**: two-tier grid (Free | Pro) separated by 1px divider. Each tier: Playfair Display name, price, description, feature list with dash bullets, CTA button.
8. Build the **FAQ accordion**: `<details>/<summary>` HTML elements with Playfair Display 18px headings, Source Serif 4 answer text. No visible markers (hide webkit default).
9. Build the **pull quote section**: two-column pullquote row using the established pattern from Phase 1.
10. Wrap all sections with editorial framing: overline "THE LANDING PAGE", headline "Every pattern, in one place", deck explaining the playground-as-superset philosophy.
11. Open `pg-case-study.component.ts`, import `PgLandingShowcaseComponent`, and insert its template tag with `id="landing-showcase"` after the live demo section.

### Verify
- All seven landing patterns render correctly: masthead, output cards, steps, comparison, pricing, FAQ, pull quotes
- The card grid collapses from four columns to two columns below 768px
- FAQ accordion opens/closes correctly
- Comparison table and pricing section respond to dark mode
- `ng build --configuration production` passes with zero errors and zero warnings

---

## Task 4: Navigation Acts Grouping  [Effort: 1 day]

### What
Restructure the sticky nav from a flat list of 11 items into four narrative acts (The Problem, The Product, The Craft, The Journey), preventing horizontal overflow at 1024px viewport width and providing a story-arc reading roadmap. This is a template-level change to the case study shell, not a new routing mechanism.

### Files
- **Modify**: `web-ng/src/app/pg-case-study.component.ts` — restructure the nav template from a flat section list into grouped acts with act labels and nested section items; update the section ID array to reflect the full 11-section ordering
- **Modify**: `web-ng/src/app/playground-demo-data.ts` — update `DEMO_NAV_SECTIONS` to include the four new section IDs (`problem`, `live-demo`, `landing-showcase`, `journey`) and add an acts grouping structure

### Steps
1. Open `playground-demo-data.ts` and update `DEMO_NAV_SECTIONS` to contain all 11 section IDs in narrative order: hero, problem, pipeline, live-demo, landing-showcase, design-language, screen-gallery, patterns, dark-mode, journey, cta. Add a new const defining the four acts with their labels and member section IDs.
2. In `pg-case-study.component.ts`, replace the flat nav list template with a grouped structure. Each act renders an act label (styled with `--sans` font, 9px uppercase, `--ink-muted` color) followed by its member section items as nested navigation links.
3. Ensure the act labels are rendered at reduced visual weight so they organize without competing with the section links they contain.
4. For viewports below 1024px, implement a collapse behavior where individual section items within each act become horizontally scrollable or collapse, while act labels remain visible as anchor points. Use existing CSS tokens and media queries — no JavaScript-driven responsive logic.
5. Verify all seven existing section IDs remain unchanged and the four new IDs are correctly wired. Confirm the old `#journey-map` ID is retained as an alias that scrolls to the new `#journey` section.
6. Test that the IntersectionObserver still correctly highlights the active section in the nav as the user scrolls — the observer logic should require no changes since it already watches all elements with `[id]` attributes.

### Verify
- The sticky nav displays four act groups with clear visual hierarchy — act labels above their member sections
- At 1024px viewport width, no horizontal overflow or truncation occurs in the nav
- All existing anchor links (`#hero`, `#pipeline`, `#design-language`, `#screen-gallery`, `#patterns`, `#dark-mode`, `#journey-map`) still scroll to correct targets
- `ng build --configuration production` passes with zero errors and zero warnings

---

## Task 5: Enhanced User Journey Map  [Effort: 2 days]

### What
Replace the existing simple timeline with a Goard-style journey map showing five workflow stages (Braindump, Generate, Review, Iterate, Ship) with pain-point annotations and editorial callouts at each stage. This complements the pipeline visualization (which shows the AI's process) by showing the human's experience with honest friction points.

### Files
- **Create**: `web-ng/src/app/pg-journey-v2.component.ts` — standalone component with a vertical stage-based layout, inline const arrays for stage definitions and pain-point annotations
- **Modify**: `web-ng/src/app/pg-case-study.component.ts` — import `PgJourneyV2Component`, replace the old journey/timeline section template reference with the new component, assign `id="journey"` and retain `id="journey-map"` as a scroll alias

### Steps
1. Create `pg-journey-v2.component.ts` as a standalone component with OnPush change detection.
2. Define an inline const array of five stage objects, each containing: stage number, stage name (Braindump, Generate, Review, Iterate, Ship), a one-paragraph description of what the user does at that stage, and a pain-point annotation string that honestly describes friction (e.g., "This is where you realize the braindump was too vague" or "This is where the architecture doc saves you from a bad database decision").
3. Build the template with a vertical stage-based layout. Each stage renders as a card with the stage number, stage name as a heading, the description paragraph, and the pain-point annotation in a distinct visual treatment.
4. Style pain-point annotations with a red overline using the existing `--red` token and italic text using the `--serif` token. This creates visual distinction from the neutral stage descriptions.
5. Add editorial framing: an overline reading "The Journey," a headline about the user's experience through specview, and a brief deck sentence contextualizing the stages.
6. Open `pg-case-study.component.ts`, import `PgJourneyV2Component`, and replace the existing simple timeline template reference with the new component's tag. Assign `id="journey"` to the new section. Add a hidden anchor element with `id="journey-map"` immediately before it so existing links to `#journey-map` still scroll to the correct location.

### Verify
- The journey map renders five vertical stages with visible pain-point annotations in red/italic styling distinct from the stage descriptions
- The section appears in the correct narrative position (Act 4, after dark mode and before CTA)
- Navigating to `#journey-map` scrolls to the same location as `#journey`
- `ng build --configuration production` passes with zero errors and zero warnings
