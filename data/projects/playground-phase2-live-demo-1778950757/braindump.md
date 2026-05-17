# Playground Phase 2 — Live Demo, Landing Page & Goard-Inspired Product Docs

## Where we are

Phase 1 of Playground 2.0 just shipped (PR #70). The `/playground` route now loads `pg-case-study.component.ts` — a narrative shell with sticky nav, IntersectionObserver-based active section tracking, and seven sections: hero (tagline + stat strip + before/after), pipeline visualization (5-step click-to-reveal), four editorial narrative wrappers around the existing Phase 1/2 design system demos (tokens, borders, animations, state matrix, app components, UI components), and a journey map timeline. All existing anchor links and dark-mode behavior preserved. No live API calls — everything is hardcoded demo data and CSS animations.

The existing components live at `web-ng/src/app/pg-*.component.ts`. The shell is `pg-case-study.component.ts`. Demo data is in `playground-demo-data.ts` which exports `DEMO_PROJECTS` (8 projects across 4 lifecycle sections), `DEMO_NAV_SECTIONS`, and pipeline preview content constants.

## What Phase 2 needs to be

Phase 2 is about making the playground feel like you're actually using specview — not reading about it. Three pillars:

### Pillar 1: Live app demo

The actual specview app UI running inside the playground with demo data. Not a screenshot, not a mockup — the real components: project grid, section nav, sidebar, reader panel, status bar. Visitors can click projects, browse specs, read rendered markdown, toggle between files — the full experience minus the API calls.

The existing `LivePlaygroundComponent` already does most of this. It imports `SectionNavComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent` and wires them up with `DEMO_PROJECTS`. It has section filtering, project selection, file browsing, expandable panel with markdown rendering via `marked` + `DOMPurify`. It even has a dark-mode toggle and a "Load demo project" button.

The trick is: we already built this for Phase 1 of the playground and it works. We just need to bring it into the case study narrative. Wrap it with editorial context the way we did for tokens and borders — an overline, headline, deck explaining "this is the real app", then the live demo, then a pull quote about live components replacing screenshots.

The demo should feel like you're using the real product. Show the project grid in "all sections" view first, let visitors click into a project, see the sidebar with file list, read the rendered analysis.md or epic.md. The status bar should be in idle state (green) showing "system ready". Maybe one project has the status bar in "active" mode showing generation in progress with the shimmer animation.

The key insight from the existing `live-playground.component.html`: it renders ALL the app components — section nav (interactive), status bar (all 4 states), project grid (clickable cards), expanded panel (sidebar + reader). This is already a complete working demo. We just need to frame it narratively.

### Pillar 2: Landing page section

The landing page (`landing/index.html`) is a separate static site served by nginx. But its design patterns are the most polished expression of the newspaper aesthetic. Inside the playground, we should render a section that shows the landing page components — or at least the key landing page patterns — as part of the case study narrative.

What the landing page has that the playground doesn't show yet:
- **Masthead**: "Vol. II, No. 1" edition line, centered "Spec Doc" title (64px Playfair), "All the Specs Fit to Build" tagline — the newspaper header that sets the entire editorial tone
- **Output cards**: 4-column grid showing the 5 deliverables (Analysis, Epic, Architecture, Timeline, Implementation Guide) with icons, filenames, and descriptions. This is the clearest visual communication of "what ships"
- **How it works — 3-step process**: Step numbers at 96px Playfair Display, titles, body text, code examples showing braindump → generation chain → implementation guide
- **Comparison table**: Dimension-by-dimension comparison against Lovable/Bolt/Kiro — this positions specview as "specs not code"
- **Pricing section**: Free vs Pro tiers with feature lists — shows the business model
- **FAQ accordion**: Details/summary pattern with Playfair headings
- **Pull quotes**: The testimonial-style quotes ("I wrote 3 paragraphs... 47 seconds later I had an analysis, epic, architecture doc, and implementation guide")
- **Stat strip**: 44.5s / 5 files / 0 code / Free — already in the hero but originally from the landing

The landing page also has a "See it" demo section with a nested UI frame — this is basically a miniature version of the app demo (sidebar + reader). That pattern could be reused.

The question is whether to iframe the actual landing page or rebuild its sections as Angular components. I think rebuild — the landing is static HTML and we want the playground sections to be interactive Angular components that respond to dark mode and IntersectionObserver. We can lift the key sections (output cards, how it works, comparison, pricing) as standalone playground components.

### Pillar 3: Goard-inspired product documentation

The Groad case study (a Behance food delivery app case study) uses a universal narrative arc: problem → process → branding → journey → screens → patterns. Phase 1 already adapted this arc loosely. Phase 2 should go deeper.

What Groad does that we should steal more explicitly:
- **Problem statement section**: Not just "Write messy. Ship clean." but a real articulation of the problem specview solves. Why do braindumps get lost? Why do teams ship without specs? What happens when architecture decisions are made implicitly? This should be a proper editorial section with statistics and real-world pain points.
- **Process visualization**: Groad shows a 6-stage circular flow (Understand → Research → Sketch → Design → Implement → Evaluate). We have the 5-step pipeline but it's about the AI pipeline, not the user's process. We should show the user's journey through specview: Braindump → Generate → Review → Iterate → Ship. This is different from the AI pipeline — it's the human workflow.
- **User research / personas**: Groad has target personas with goals. We could show who uses specview — the solo founder, the tech lead, the PM who doesn't code. Not fake personas, but real user archetypes with real problems.
- **Journey map with pain points**: Groad's journey map shows pain points at each stage. We should show the specview user journey with honest annotations: "This is where you realize the braindump was too vague" or "This is where the architecture doc saves you from a bad database decision."
- **Screen annotations**: Groad annotates every screen with "This screen does X because Y." We already have live components — we should add editorial callouts explaining why each piece of the UI exists. The sidebar file list is not just a file list — it's ordered by workflow stage. The status bar is not just a status indicator — it's an editorial ticker.
- **Before/after transformation**: Groad shows raw ingredients → finished dish. We already have braindump → spec suite in the hero. But Phase 2 could go deeper: show the actual content transformation. A real messy braindump paragraph becoming a structured analysis finding. Side by side. Line by line.

What we should NOT do (learned from Phase 1 spec):
- No heritage section (ClawBoi origin story) — vanity content
- No cross-product demos — we only have one product
- No live API calls — canned demo data is fine
- No fake checkout or billing flow — misleading
- No rounded corners or shadows — newspaper aesthetic uses sharp corners and borders

## How it should compose

The `pg-case-study.component.ts` shell currently has 7 sections. Phase 2 would reorganize and expand:

1. **Hero** (existing — keep as is, maybe refine copy)
2. **Problem statement** (NEW — Goard-inspired, why specs matter)
3. **Pipeline** (existing — keep, maybe enhance with user workflow overlay)
4. **Live app demo** (NEW — the actual specview app with demo data, wrapped in narrative)
5. **Landing showcase** (NEW — key landing page sections as Angular components)
6. **Design Language** (existing narrative wrapper — keep)
7. **Screen Gallery** (existing narrative wrapper — keep)
8. **Patterns** (existing narrative wrapper — keep)
9. **Dark Mode** (existing narrative wrapper — keep)
10. **User journey** (ENHANCED — Goard-style journey map with pain points and annotations, replaces current simple timeline)
11. **CTA / closing** (maybe merge with journey or add separate)

The nav bar would need to accommodate more sections. Could group into acts: Act 1 (Hero + Problem + Pipeline), Act 2 (Live Demo + Landing), Act 3 (Design System sections), Act 4 (Journey + CTA).

## Design system context

All new components must use the existing design tokens:
- `--ink`, `--bg`, `--border`, `--red`, `--ink-muted`, `--accent`
- `--sans` (Source Sans 3), `--serif` (Playfair Display), `--body` (Source Serif 4)
- Overline: 9px uppercase sans, `var(--red)` color
- Headline: Playfair Display 44px
- Deck: Source Serif 4 18px, max-width 680px
- Pullquote row: two-column grid with 1px divider, italic serif 22px
- Section heading: Source Sans 3 28px, 700 weight, 1px bottom border
- CTA button: square (no border-radius), `var(--ink)` background, `var(--bg)` text

## Existing infrastructure to reuse

- `playground-demo-data.ts` — already has `DEMO_PROJECTS` with 8 projects, `DEMO_NAV_SECTIONS`, pipeline previews. Extend for new demo content.
- `LivePlaygroundComponent` — still in the codebase (not deleted in Phase 1). Its template and logic are the blueprint for the live app demo section.
- `landing/index.html` + `landing/style.css` — 308 lines of HTML, 1172 lines of CSS. The source material for the landing showcase section.
- `landing/specview-landing-wireframe.jsx` — React mockup with full content data arrays for output cards, steps, stats, FAQs. Can lift the data directly.
- Groad case study PDF at `docs/design-references/` — the narrative arc template.
- All existing `pg-*` components remain unchanged — new sections compose around them.

## Constraints

- Angular 17 standalone components, signals only, `@if` / `@for` control flow
- No live API calls in the playground — all demo data is static
- CSS custom properties for theming — no hardcoded colors
- ChangeDetectionStrategy.OnPush on all new components
- No new design tokens — use existing ones
- Preserve all existing anchor links from Phase 1
- The playground must build with `ng build --configuration production` zero errors
