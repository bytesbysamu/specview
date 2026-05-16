# 🏗️ Solution Architecture: Playground 2.0 — Specview Case Study + UX Audit

## Architecture Overview

The current `/playground` is a flat component reference — a vertically stacked list of design system demos (tokens, borders, animations, state matrix, component catalogs) rendered by `live-playground.component.ts` and its `pg-*` sub-components. It serves development needs but tells no story. A prospect lands on the page, sees swatches and border catalogs, and leaves without understanding what Specview does or why it looks the way it does.

Playground 2.0 wraps this reference in a narrative shell: a scrollable case study that follows a 3-act arc (hook → method → product). The shell is a new top-level component that **composes** the existing playground components rather than replacing them. New narrative sections (hero, problem statement, pipeline visualization, journey map) sit between and around the existing Phase 1/2 demos. The key architectural insight is that the existing `pg-*` components become acts in a story — they stay unchanged, but gain editorial context (overlines, pull quotes, annotations) that explain *why* each design decision exists.

No backend work is required. The entire scope is frontend Angular: new components for new sections, a wrapper shell for scroll orchestration, and narrative chrome around existing demos. The newspaper design system already has every CSS class needed for editorial layout — overlines, headlines, pull quotes, section headings, the lede grid. This architecture adds no new design tokens and introduces no new layout primitives. It uses what exists.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | No generic "section renderer" or "narrative block" base class. Each narrative section is its own component with its own template. Five components, not one abstraction. |
| P7 — File Size & Structure | Every new component stays under 200 lines. The narrative shell orchestrates via template composition, not logic. One component per file, flat in `src/app/`. |
| Newspaper Design System | All new sections use existing global CSS classes from `styles.css` — `.overline`, `.headline`, `.deck`, `.pullquote-row`, `.section-heading`, `.lede`. Zero component-scoped CSS. |
| P2 — Thin Layer (applied to components) | Narrative wrapper components contain editorial markup and compose existing `pg-*` components via their selectors. No business logic, no services, no HTTP calls. |
| Anchor Preservation | Every existing Phase 1/2 anchor (`#tokens`, `#borders`, `#animations`, `#state-matrix`, `#components-app`, `#components-ui`) keeps its `id` attribute on the same DOM element. The narrative shell adds sections *around* them, never replaces the anchored elements. |

## Component Design

### Narrative Shell (`pg-case-study.component.ts`)

**Purpose**: Replaces `live-playground.component.ts` as the top-level component rendered at `/playground`. Provides the scroll container, section ordering, and anchor navigation for the full case study experience.

The shell is a template-only orchestrator — it contains no logic beyond a dark-mode signal binding that already exists in the app. Its template sequences the narrative sections top-to-bottom, interspersed with existing `pg-*` component selectors. The section nav bar (already present in `live-playground`) moves here with updated labels that reflect the narrative arc instead of raw component category names.

The route table (`app.routes.ts`) updates the `/playground` path to load `pg-case-study` instead of `live-playground`. The old component remains in the codebase — it is not deleted — so any internal links or dev bookmarks pointing to the component directly still resolve. If a rollback is needed, the route change is a one-line revert.

**Section ordering within the shell template:**

1. Hero + stat strip (new component)
2. Problem statement / before-after (new component)
3. Pipeline visualization (new component)
4. Design Language — narrative wrapper around existing `pg-tokens` and `pg-borders`
5. Screen Gallery — narrative wrapper around existing `pg-components-app` and `pg-components-ui`
6. Design Patterns — narrative wrapper around existing `pg-animations` and `pg-state-matrix`
7. Dark Mode — narrative wrapper around existing dark-mode demo, plus token diff table
8. Journey Map (new component, positioned last as a conversion-oriented coda)

### Hero + Problem Section (`pg-hero.component.ts`)

**Purpose**: Above-the-fold hook. Delivers the "Write messy. Ship clean." tagline, stat strip (44.5s / 5 files / 0 code / Free), and a before/after transformation layout showing a messy braindump on the left and five structured document previews on the right.

This section uses the existing `.lede` two-column grid from `styles.css` — the braindump sits in `.lede-main`, a `1px` column rule divider, and the structured output in the lede aside. The stat strip reuses the same pattern already built in `landing-v2.html` (four inline-block stat items with Playfair Display numbers and Source Sans labels).

The "live generation demo" described in the braindump is implemented as a **canned CSS animation** — the status bar component (`status-bar.component`) rendered in a looping demonstration state, showing file names appearing one by one via CSS keyframes. No API calls, no auth complexity, no failure modes. The epic explicitly excludes live API calls in the hero background, and a CSS animation achieves the same visual impact at a fraction of the build cost.

**Trade-off**: A canned animation cannot show real document content generating. It sacrifices authenticity for reliability. A visitor who has used the product may notice the demo is scripted. This is acceptable because the hero's job is to communicate *what happens* (braindump in → docs out), not to prove it works — the pipeline section below handles proof.

### Pipeline Visualization (`pg-pipeline.component.ts`)

**Purpose**: Visualizes the 5-step spec generation flow (braindump → analysis → epic → architecture → implementation guide) as a horizontal newspaper-style progression. Each step is a clickable station that reveals a document preview panel below.

The horizontal layout uses a CSS grid with five equal columns, separated by `1px solid var(--border)` column rules — the same pattern as the landing page's output cards grid. Each step column contains: a decorative Playfair Display step number (64px, `var(--border)` color — the faint decorative pattern from the landing), a Source Sans uppercase label, and a one-line description in Source Serif.

Clicking a step expands an inline preview panel below the flow bar. This panel uses the **expanded panel pattern** from the ClawBoi design system: `border-top: 3px solid var(--ink)`, `border-bottom: 1px solid var(--border)`, two-column body text with `column-rule`. The preview shows hardcoded representative content for each document type — not live API output, not pulled from a real project. The data lives in `playground-demo-data.ts`, extending the existing demo data pattern.

**Trade-off**: Hardcoded previews mean the pipeline section does not prove the AI works — it shows what the AI produces. This is the right trade-off for a case study page: the narrative explains the pipeline, and a visitor who wants proof can sign up and run a real generation. Pulling live data would require auth, API calls on page load, error handling for empty states, and a loading skeleton — all for a page whose job is to *explain*, not to *demonstrate*.

**Parallel with Task 2**: This component has no dependency on the hero section. It depends only on the narrative shell (Task 1) being in place. Tasks 2 and 3 can be built simultaneously.

### Narrative Wrappers (`pg-narrative-design.component.ts`, `pg-narrative-screens.component.ts`, `pg-narrative-patterns.component.ts`, `pg-narrative-dark.component.ts`)

**Purpose**: Four thin wrapper components that add editorial context around the existing Phase 1/2 playground sections without modifying those sections.

Each wrapper follows the same structural pattern:

- A `.section-heading` full-width label strip (the structural divider, not the overline)
- Inside the section: a `.overline` in `var(--red)` (the editorial opener), a `.headline` in Playfair Display, a `.deck` paragraph in Source Serif explaining *why* this design decision exists
- The existing `pg-*` component rendered via its selector, unchanged
- A closing `.pullquote-row` with an editorial pull quote that ties the section back to the product narrative

The wrappers add approximately 30–50 lines of template markup each. They import zero services and contain zero logic — they are pure editorial chrome. This is the lightest possible integration: the existing `pg-*` components do not know they are wrapped, their inputs do not change, and their anchor `id` attributes remain on the original elements.

**Why four separate wrapper components instead of one generic wrapper with content projection**: P4 — no speculative abstractions. Each section has different editorial content, different pull quotes, different headline text. A generic wrapper would need `ng-content` slots, configuration inputs, and conditional rendering — more machinery than four simple templates. The four components share no logic because there is no logic to share.

**`pg-narrative-dark`** adds one new element the others do not: a **token diff table** showing the light-to-dark value mapping for each CSS custom property (`--ink: #121212 → #E8E6E0`, etc.). This is a static HTML table using the existing newspaper table styling. It makes the dark mode toggle educational — the visitor sees not just the visual flip but the exact values changing.

### Journey Map (`pg-journey.component.ts`)

**Purpose**: Visualizes the user flow from anonymous visitor to power user as a horizontal newspaper-style timeline. This is the conversion-oriented closing section — it ends with the path to signup.

The timeline follows the Groad journey map pattern adapted to newspaper aesthetics: a horizontal sequence of stations, each with a Source Sans uppercase label, a Playfair Display station name, and a Source Serif description. Stations are separated by `1px solid var(--border)` vertical rules — the same column-divider pattern used throughout the design system. The horizontal scroll (if needed on narrow viewports) uses native CSS `overflow-x: auto` with no custom scrollbar styling.

Stations: Land on page → See the pitch → Explore playground → Sign up → Create project → Generate specs → Read in newspaper layout → Iterate with AI ops → Upgrade to Pro → Share specs publicly.

The final station ("Share specs publicly") includes an inline call-to-action styled as the existing CTA pattern from `landing-v2.html` — a square button (no border-radius) with `var(--ink)` background and `var(--bg)` text.

**Placement decision**: The journey map sits last in the scroll order, not after the hero. The epic marks this as low priority, and narratively it works better as a denouement — after the visitor has seen what the product does (hero), how it works (pipeline), and how it looks (design language + screens + patterns + dark mode), the journey map shows them where they fit in the story. It is the "what now" section, and ending with a CTA is the natural conversion point.

**Trade-off**: Horizontal timelines can be awkward on mobile viewports. The newspaper design system is desktop-first, and the epic's success criteria specify "desktop" for the 2s load time target. On viewports under 768px, the timeline degrades to a vertical stack — each station becomes a full-width row. This is a CSS-only responsive behavior, not a separate mobile component.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | Angular 17 (standalone components, signals) | Existing stack. All playground components are already Angular standalone components. No framework decision to make. |
| Styling | Global CSS classes from `styles.css` | The newspaper design system is built as global utility classes. Component-scoped CSS would duplicate tokens and drift from the system. Every new section uses `.overline`, `.headline`, `.deck`, `.lede`, `.pullquote-row`, `.section-heading` — all already defined. |
| State management | None (signals for dark-mode toggle only) | The case study is a static scroll page. No HTTP calls, no async state, no loading states. The dark-mode signal already exists and propagates through CSS custom properties. |
| Demo data | `playground-demo-data.ts` | Existing file for hardcoded playground fixtures. Pipeline document previews extend this same file rather than creating a new data source. |
| Backend | No changes | Zero API surface touched. The case study is entirely client-rendered static content with live Angular components. |
| Routing | `app.routes.ts` single-path update | `/playground` → `pg-case-study.component`. No lazy-loaded child routes — the case study is one scrollable page, not a multi-route experience. |

## Scroll Architecture

The page is a single continuous scroll — no route transitions, no virtual scrolling, no intersection-observer-driven lazy loading. The entire component tree renders on initial load. This is a deliberate choice:

**Why not lazy-load sections as they scroll into view**: The existing `pg-*` components are lightweight Angular templates rendering CSS demos. They contain no images, no API calls, and no heavy computation. The total DOM footprint of the full page — including all narrative wrappers and new sections — is smaller than a typical Angular material table. Intersection-observer lazy loading would add complexity (loading skeletons, height placeholders, flash-of-unloaded-content) for a problem that does not exist. The epic's 2s load time target is achievable without lazy loading because there are no heavy assets.

**Why not sub-routes**: A case study is a scroll experience. Breaking it into `/playground/hero`, `/playground/pipeline`, `/playground/design` would destroy the narrative flow. The Groad PDF is one continuous scroll — so is this. Fragment anchors (`#hero`, `#pipeline`, `#design-language`, etc.) provide deep-linking without route transitions.

**Section nav behavior**: The section nav bar at the top of the shell uses fragment anchors with `scrollIntoView` behavior. Active section highlighting uses a single `IntersectionObserver` on section heading elements — when a section heading crosses the viewport top, its nav item gets the active class. This is the same pattern used by the existing landing page's sticky header.

## Route Strategy

The `/playground` route currently loads `LivePlaygroundComponent`. The architecture changes this to load `PgCaseStudyComponent`:

- `app.routes.ts`: `/playground` path → `PgCaseStudyComponent` (the new narrative shell)
- `LivePlaygroundComponent` is **not deleted** — it remains in the codebase as a reference and fallback
- No new child routes. No lazy-loaded sub-modules. The case study is a single component tree
- All existing anchor fragments (`#tokens`, `#borders`, `#animations`, `#state-matrix`, `#components-app`, `#components-ui`) remain functional because the `pg-*` components that own those `id` attributes are still rendered — just composed inside narrative wrappers instead of directly inside the old shell

**Why not keep both routes** (`/playground` for case study, `/playground/raw` for component reference): P4 — no speculative abstractions. There is no current user for a raw component reference at a separate URL. The narrative shell includes every Phase 1/2 component with editorial context. If a developer needs the raw reference, `LivePlaygroundComponent` exists in the source — they can render it locally by temporarily reverting the route. A dead route that nobody visits is worse than no route.

## Dark Mode Strategy

Dark mode already works across all existing `pg-*` components because they use global CSS custom properties from `styles.css`. The narrative shell and all new components inherit this behavior automatically by using the same global classes (`.overline`, `.headline`, `.deck`, `.pullquote-row`). No additional dark-mode work is required for new sections.

The one addition is the **token diff table** in the dark-mode narrative wrapper. This is a static `<table>` showing each custom property's light and dark values. The table itself flips with the theme toggle — so in light mode, the "Light" column values match the current page appearance, and in dark mode, the "Dark" column values match. This creates a self-referential educational moment: the visitor toggles dark mode, sees the page change, and sees the exact values that changed listed in the table they are reading.

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| New shell component rather than extending `live-playground` | The existing component is a flat list of `pg-*` selectors. Adding narrative sections, scroll orchestration, and a restructured nav would push it past 300 lines and mix two concerns (reference vs. narrative). A new shell keeps both components focused. | Two components that render similar children. Mitigated by the old component remaining untouched — zero risk of regression. |
| Canned CSS animation in hero, not live API calls | The epic explicitly excludes live API calls. A CSS keyframe animation of the status bar achieves the visual goal (show files appearing) without auth, error handling, or network dependency. | The demo is obviously scripted to a returning user. Acceptable — the hero communicates the concept, not the proof. |
| Hardcoded pipeline previews, not live project data | The pipeline section explains the 5-step flow. Pulling real data requires auth context, a real project, and error handling for anonymous visitors who have no projects. | Content may drift from actual output as the product evolves. Mitigated by storing previews in `playground-demo-data.ts` alongside existing demo data — one file to update. |
| Four separate narrative wrappers, not one generic wrapper | Each section has unique editorial content. A generic wrapper with content projection slots adds indirection without reducing total code. Four 40-line components are simpler than one 80-line generic component plus four 20-line configuration objects. | Mild repetition in template structure (overline + headline + deck + component + pull quote). Acceptable — the pattern is visible, and extracting it would be premature until a sixth or seventh section appears. |
| Journey map last, not second | The journey map is the conversion coda — it answers "what do I do now?" after the visitor understands the product. Placing it after the hero (as Groad does) would interrupt the technical narrative with a flow diagram before the visitor has seen what the product looks like. | A visitor who bounces before reaching the bottom never sees the journey map or its CTA. Mitigated by the hero section containing its own CTA (the "Try it free" button from the landing pitch pattern). |
| Heritage section excluded | The epic explicitly scopes this out: "Vanity content with no conversion payoff." The braindump includes it, but the epic's scope exclusion takes precedence. The ClawBoi origin story adds color but not conversion — a prospect does not care where the font choice came from. | Loses the design system lineage narrative, which portfolio viewers (secondary audience) might value. Can be added as a standalone follow-up if portfolio use case materializes. |
| Single scroll page, no sub-routes | A case study is read top-to-bottom. Route transitions break narrative flow, add loading states, and fragment the reading experience. The Groad reference is a continuous scroll. | Deep-linking to mid-page sections depends on fragment anchors, which do not trigger Angular route guards or analytics page-view events. Mitigated by the `IntersectionObserver`-based active section tracking, which can emit analytics events if needed later. |
| No new CSS classes in `styles.css` | Every visual pattern needed — overlines, headlines, decks, pull quotes, section headings, lede grids, column dividers — already exists in the 1,769-line global stylesheet. Adding narrative-specific classes would fragment the design system. | New sections are constrained to existing layout patterns. If a future section needs a layout not covered by the current system (e.g., a full-bleed image strip), a new class would be warranted — but no such section exists in this scope. |

## Component Tree

```
pg-case-study (shell — route target)
├── section-nav (updated labels, fragment anchors)
├── pg-hero (hero + stat strip + before/after + canned status bar animation)
├── pg-pipeline (5-step horizontal flow + click-to-reveal document preview)
├── pg-narrative-design (editorial wrapper)
│   ├── pg-tokens (existing, unchanged)
│   └── pg-borders (existing, unchanged)
├── pg-narrative-screens (editorial wrapper)
│   ├── pg-components-app (existing, unchanged)
│   └── pg-components-ui (existing, unchanged)
├── pg-narrative-patterns (editorial wrapper)
│   ├── pg-animations (existing, unchanged)
│   └── pg-state-matrix (existing, unchanged)
├── pg-narrative-dark (editorial wrapper + token diff table)
│   └── existing dark-mode demo section
└── pg-journey (horizontal timeline + CTA)
```

**New files**: 7 components (shell + hero + pipeline + 4 narrative wrappers + journey). At the target of under 200 lines each, this adds approximately 700–1,000 lines of Angular template and TypeScript across 7 files in the flat `src/app/` directory. All files follow the existing `pg-` prefix naming convention.

**Modified files**: `app.routes.ts` (one route path change), `playground-demo-data.ts` (pipeline preview content added).

**Deleted files**: None. `live-playground.component.ts` remains in the codebase.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing anchor links break | Low | High — the epic's success criteria explicitly require all Phase 1/2 anchors to remain functional | Narrative wrappers compose existing `pg-*` components without touching their templates. Anchor `id` attributes stay on the same DOM elements. Verified by manual scroll-to-anchor test on each existing link. |
| Page load exceeds 2s target | Low | Medium | No new assets, no API calls, no images. The additional DOM is lightweight editorial markup. The only risk is if `playground-demo-data.ts` grows excessively with pipeline preview content — keep previews to 3–4 paragraphs per document type. |
| Dark mode breaks on new sections | Low | Medium | All new sections use global CSS custom property classes. As long as no component-scoped styles use hardcoded color values, dark mode propagates automatically. Build verification (`ng build --configuration production`) catches missing variable references. |
| Narrative feels disconnected from live components | Medium | Medium — undermines the "product sells itself by being itself" value proposition | Each narrative wrapper's pull quote and deck text reference the specific component rendered below it. The editorial content is written *about* the live demo, not as a standalone essay. |
| Scope creep into heritage section | Medium | Low — adds build time without conversion value | The epic's explicit exclusion is the guardrail. If heritage content surfaces during implementation, it gets flagged and deferred to a separate ticket. |

## Related Documents

- [Analysis](./analysis.md) — Open questions, dependency mapping, and scope exclusion rationale
- [Epic](./epic.md) — Scope, tasks, success criteria, and the Groad-to-Specview mapping that drives section structure
- [Timeline](./timeline.md) — Status tracking and delivery sequence