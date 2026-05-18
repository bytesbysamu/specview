# 🎯 Epic: Playground V4 — UX Overhaul

## Business Value

The playground is spec-doc's primary conversion surface — the single page that transforms a curious visitor into a paying user. V3 proved the five-section narrative structure works mechanically, but a UX audit against the original Groad case study reveals a critical gap: the demo reads as a component reference rather than a product experience. Visitors see features listed but never feel the transformation that justifies paying for the tool. The Groad pattern (pain → process → result → journey) converts because it makes the viewer *feel* the before/after shift — V3 skips that emotional beat entirely.

Closing this gap is a revenue prerequisite. A portfolio visitor who sees a static pipeline description bounces; one who watches their own messy braindump become a structured spec in four clicks understands the value instantly. Every week without the narrative arc is a week where the playground functions as a tech demo instead of a sales tool. The competitive moat for spec-doc isn't features — it's the "aha" moment speed, and V4 exists to compress that moment from minutes of reading to seconds of scrolling.

The secondary payoff is portfolio credibility. As a solo founder selling a documentation-first methodology, the playground IS the case study. If it doesn't mirror real app behavior faithfully, the implicit promise ("this tool produces professional output") rings hollow at the exact moment a prospect is evaluating trust.

## Scope

### What This Epic Covers

- **Grid-OR-Detail view parity** – Make the embedded demo behave identically to the production app (mutually exclusive states, not stacked components)
- **Before/After transformation section** – Visual proof of braindump-to-spec conversion using existing demo data
- **Interactive pipeline progression** – Single project (Payment Gateway Redesign) shown transforming through all four stages via user-driven interaction
- **Scroll gating removal** – Replace IntersectionObserver locks with passive CSS reveal animations that preserve narrative pull without adding friction

### What This Epic Does NOT Cover

- ❌ **Building an actual landing/marketing page** — Showcase section deferred until a standalone landing page ships; adding it here doubles scope with a hidden dependency
- ❌ **Journey map + upgrade flow visualization** — Requires a defined conversion funnel and pricing page that don't exist yet; revisit post-launch
- ❌ **New demo project content** — Payment Gateway Redesign already covers all 4 stages; no content authoring needed
- ❌ **Mobile-specific layout** — Playground targets desktop conversion; responsive polish scoped separately if analytics justify it
- ❌ **Dark mode comparison view** — Side-by-side breaks on narrow viewports; sequential approach needs design exploration outside this epic

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Grid-OR-Detail View Fix** | None | — | 2 days | High |
| 2 | **Before/After Transformation Section** | None | ∥ with #1 | 2 days | High |
| 3 | **Interactive Pipeline Progression** | #1 (clicks into detail view) | — | 3 days | High |
| 4 | **Scroll Gating Removal & CSS Reveals** | #1, #2, #3 | — | 1 day | Low |

## Success Criteria

- ✅ Clicking a project card in the demo hides the grid and shows the detail panel; closing detail restores the grid (zero stacked-component states)
- ✅ Before/After section renders the same content in two visual states (raw braindump → structured spec) without any user interaction required
- ✅ Pipeline section advances Payment Gateway Redesign through all 4 stages (braindump → analysis → epic → architecture) via tab/click interaction
- ✅ No section is blank or locked during normal scroll speed — all content reveals passively via CSS animation
- ✅ Page load remains sub-2s with zero HTTP calls in DEMO_MODE
- ✅ All changes use existing design system tokens (newspaper aesthetic) with no new token definitions

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking