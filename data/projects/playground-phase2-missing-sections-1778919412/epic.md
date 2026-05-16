# 🎯 Epic: Playground Phase 2 — Missing Sections

## Business Value

The spec-doc playground is the living reference for every visual element in the product. Phase 1 proved the concept — design tokens, borders, animations, and the state matrix gave the playground real utility as a development tool. But 12 verified components still live only in the old static playground file, which means there are two sources of truth for the design system. Developers (in this case, Sam) must cross-reference a dead file to see how mastheads, modals, op chips, and landing elements actually render. That friction slows every UI task and creates drift between what the playground documents and what the product ships.

Completing Phase 2 eliminates the old static playground entirely, making `/playground` the single canonical reference for all spec-doc components. Every future UI change — whether it's a new button variant, a landing page tweak, or a modal redesign — gets validated against one living document instead of two stale ones. For a solo founder shipping across multiple projects, removing that cognitive overhead compounds: less context-switching per task, fewer "wait, which file has the real version?" moments, and a trustworthy visual regression surface when CSS changes land.

The immediate payoff is velocity on spec-doc itself, but the pattern transfers. A proven playground methodology can be replicated in Bubls or humanize-me when those projects reach the point of needing a component reference. Ship a complete playground once, reuse the approach everywhere.

## Scope

### What This Epic Covers

- **App component demos** — Masthead, op chips, modal, update banner, context cards, search bar, overline/badges, and all button variants rendered as static visual demos in a new child component
- **Landing page demos** — Pull quote and step section rendered using landing-specific markup and styles in a dedicated child component
- **Interaction state demos** — Side-by-side default vs. hover/active/focus rendering for all interactive elements, using inline style overrides to show states without requiring user interaction
- **State matrix extension** — App vs. Landing comparison table and ClawBoi vs. Specview heritage table added to the existing state matrix section
- **Old playground retirement** — Verification that every section from the static playground has a live equivalent, enabling deletion of the old file

### What This Epic Does NOT Cover

- ❌ **Refactoring Phase 1 sections** — Existing sections work; changes only if bugs surface during integration (see [Analysis](./analysis.md))
- ❌ **Interactive demos** (click handlers, live state toggling) — These are static visual references, not functional prototypes
- ❌ **Responsive/mobile layout for the playground** — Dev-only tool; not user-facing
- ❌ **New components not in the verified inventory** — Only the 12 items confirmed against source code on 2026-05-16; no speculative additions
- ❌ **Landing CSS architecture changes** — CSS loading strategy is a design decision scoped to [Solution Architecture](./architecture.md), not a feature deliverable

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **App Component Demos** — Build `pg-components` child component rendering all 8 app-level demos (masthead, op chips, modal, update banner, context cards, search bar, overline/badges, buttons) | None | Yes (with Task 2) | 1.5 days | High |
| 2 | **Landing Page Demos** — Build `pg-landing` child component rendering pull quote and step section demos with correct landing CSS isolation | None | Yes (with Task 1) | 0.5 days | High |
| 3 | **Interaction State Demos** — Build `pg-interactions` child component with default-vs-hover side-by-side table for all interactive elements | Task 1 | — | 1 day | High |
| 4 | **State Matrix Extension** — Add App vs. Landing comparison table and heritage table to existing `pg-state-matrix` component | None | Yes (with Tasks 1–2) | 0.5 days | Low |
| 5 | **Integration & Old Playground Retirement** — Wire all new child components into live playground, verify zero missing sections, confirm `ng build` passes, remove old static playground file | Tasks 1–4 | — | 0.5 days | High |

## Success Criteria

- ✅ All 12 items from the verified inventory render correctly in `/playground`
- ✅ Masthead renders with full newspaper chrome (edition label, date, title, tagline)
- ✅ All 8 op chips displayed with active and accent state variants
- ✅ Modal rendered inline (not overlay) with all form fields visible
- ✅ Every button variant (primary, secondary, new-project, logout, upgrade, icon) shown in a single row including disabled state
- ✅ Pull quote renders with oversized quotation mark in both single and row variants
- ✅ Interaction states table shows default vs. hover/active/focus side-by-side for all interactive elements
- ✅ App vs. Landing comparison table present in state matrix section
- ✅ `ng build --configuration production` passes with zero errors and no regressions in existing sections
- ✅ Old static playground file deleted — `/playground` is the single source of truth
- ✅ Every new file stays under 200 lines (`.ts`, `.html`, `.css` counted separately)

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — CSS isolation strategy, component structure, 200-line feasibility decisions
- [Timeline](./timeline.md) — Status tracking and completion dates