# 🎯 Epic: Playground V3

## Business Value

The spec-doc playground currently exists as two disconnected layers — a live component demo (Phase 1) that proves things work, and a nine-section case study shell (Phase 2) that documents why they exist. Neither sells the product. A prospective user lands on the playground and faces a tab bar with counts and pulse animations, then a wall of sections that read like internal documentation. The playground should be the product's best pitch: a single guided experience where every design pattern is demonstrated in context, not catalogued in a reference sheet.

V3 consolidates both layers into a restaurant-style guided scroll — roughly five sections that walk the visitor through spec-doc's design system the way a maître d' walks a guest through a meal. Each section exercises the full pattern vocabulary (typography scale, newspaper grid, ink-on-cream palette, quiet interactions) without calling attention to it. The result is a canonical reference that informs two downstream surfaces: the app's own UX consistency and the landing page's component library. Instead of maintaining three diverging expressions of the same design system, V3 becomes the single source of truth that both consume.

For a solo founder, this consolidation eliminates the maintenance drag of keeping Phase 1's live playground, Phase 2's case study, and the landing page visually aligned. One scroll, one component set, one place to verify the design system works end-to-end. The playground stops being a demo and starts being the product's front door.

## Scope

### What This Epic Covers

- **Section inventory definition** — resolve the ~5 sections by merging and cutting from Phase 2's nine, with clear rationale for each decision
- **Gating model selection** — choose the guided-progression mechanism (scroll-reveal, stepper, or scroll-snap) and define its behavior on both desktop and mobile
- **Single-scroll shell** — the container architecture that hosts ~5 gated sections in one continuous route
- **Section composition** — each section populated with components that exercise every design pattern (type scale, grid, borders, color, interaction) through demonstration
- **Live app embed** — the actual specview app running with demo data inside one section of the scroll, replacing screenshots
- **Component extraction boundaries** — define which playground components the landing page can consume and the API surface for sharing them

### What This Epic Does NOT Cover

- ❌ **New design tokens or palette changes** — design system is locked; V3 composes existing tokens only
- ❌ **Multi-page routing** — single scroll is the constraint; re-scope only if mobile performance forces it
- ❌ **Copywriting or content creation** — "minimal text" means this is a layout/composition project; placeholder text is acceptable at MVP
- ❌ **Landing page rebuild** — extraction boundaries are defined here, but the landing page consuming those components is a separate epic
- ❌ **Phase 1 playground as a separate route** — V3 absorbs it; the standalone live playground route is retired

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Section inventory & gating model** — Resolve all six open questions from analysis: define the ~5 sections (what merges, what's cut from Phase 2's nine), choose the gating mechanism, decide annotation vs. demonstration, settle section-nav and dark-mode-toggle fate | None | — | 1 day | High |
| 2 | **Scroll shell with gated transitions** — Build the single-scroll container with section slots and the chosen gating mechanism; transitions work on empty sections, desktop and mobile | 1 | — | 2 days | High |
| 3 | **Section content composition** — Populate each of the ~5 sections with components exercising the full design-pattern vocabulary; reuse Phase 1 live components and Phase 2 case-study pieces where they fit | 1, 2 | Per-section | 3 days | High |
| 4 | **Live app demo integration** — Embed the specview app (from app-v3-state-extraction) as one scroll section with demo data, replacing static screenshots | 2 | Yes (with 3) | 1 day | High |
| 5 | **Landing page component extraction** — Define the API boundaries for components the landing page will consume from the playground; extract and export them without breaking the scroll | 3, 4 | — | 1 day | Low |

## Success Criteria

- ✅ Playground renders as a single continuous scroll with ~5 distinct sections — no route changes, no tab navigation
- ✅ Progression through sections is gated (visitor cannot skip ahead without engaging each section)
- ✅ Every design-system pattern (type scale, grid, newspaper borders, ink-on-cream palette, quiet hover states) is exercised at least once across the scroll
- ✅ The live specview app runs inside one section with real services and demo data — not screenshots
- ✅ Phase 1 live playground and Phase 2 case study are fully absorbed — no orphaned routes remain
- ✅ Scroll performs acceptably on mobile (no layout-breaking jank from rendering all sections in one page)
- ✅ At least one playground component is consumable by the landing page through a defined export boundary

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design, gating mechanism, and section layout decisions
- [Timeline](./timeline.md) — Status tracking for each task