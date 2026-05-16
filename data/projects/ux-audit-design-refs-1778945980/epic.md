# 🎯 Epic: Playground 2.0 — Specview Case Study + UX Audit

## Business Value

The current `/playground` is a component reference — useful for development, invisible to prospects. A narrative case study transforms this page into Specview's primary conversion tool: an anonymous visitor scrolls top-to-bottom, understands what the product does, sees it working live, and hits "Try it free" with full context. Every SaaS competitor uses static screenshots; Specview's case study runs real Angular components — the product sells itself by being itself.

Secondary value: the page doubles as a portfolio piece (Behance/Dribbble-grade case study structure) demonstrating both product thinking and design system execution. For a solo founder, the playground IS the pitch deck — it replaces slide decks, demo videos, and explainer pages with a single scrollable artifact.

The audience is a prospect evaluating whether Specview solves their "think before code" problem. Portfolio viewers (hiring managers, collaborators) are a secondary audience served by the same narrative without any content fork.

## Scope

### What This Epic Covers

- **Narrative shell** – Scrollable page architecture that hosts both the case study narrative and existing Phase 1/2 component demos without breaking current anchor links
- **Hero + Problem section** – Above-the-fold hook: tagline, stat strip, and before/after transformation (messy braindump → structured docs)
- **Pipeline visualization** – Horizontal 5-step flow (braindump → analysis → epic → architecture → impl guide) with click-to-reveal document previews
- **Narrative wrappers** – Editorial context (overlines, pull quotes, annotations) around existing Phase 1/2 sections (Design Language, Screen Gallery, Design Patterns, Dark Mode)
- **Journey map** – User flow from anonymous visitor to power user, visualized as a horizontal newspaper-style timeline

### What This Epic Does NOT Cover

- ❌ **Heritage section (ClawBoi origin story)** — Vanity content with no conversion payoff; revisit only if shipping a public design system docs site
- ❌ **Cross-product demos (Ionic theming, Groad food patterns)** — No second product ships on this design system yet; zero current use case
- ❌ **Live API calls in hero background** — A canned CSS animation of the status bar achieves the same visual impact at 1% of the build cost; real API calls add auth complexity and failure modes
- ❌ **Billing/Stripe flow as live component** — Fake checkout in a case study is misleading; a static annotated screenshot suffices if needed at all
- ❌ **Forced 1:1 Groad section mapping** — Steal the 3-act arc (hook → method → product), not the 14-row table; "driver interface → dark mode" is a stretch

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Narrative shell + route architecture** | None | — | 1 day | High |
| 2 | **Hero + Problem section (above the fold)** | Task 1 | — | 2 days | High |
| 3 | **Pipeline visualization (5-step flow)** | Task 1 | ∥ Task 2 | 2 days | High |
| 4 | **Narrative wrappers for Phase 1/2 sections** | Task 1 | ∥ Tasks 2–3 | 1.5 days | High |
| 5 | **Journey map (user flow timeline)** | Tasks 2–3 | — | 1.5 days | Low |

## Success Criteria

- ✅ A visitor scrolling `/playground` top-to-bottom can explain what Specview does, how it works, and why it looks the way it does — without clicking anything
- ✅ All existing Phase 1/2 anchor links (`#tokens`, `#borders`, `#animations`, etc.) remain functional and unchanged
- ✅ Every section uses live Angular components rendered with design system tokens — zero screenshots
- ✅ Dark mode toggle flips the entire narrative page including new sections
- ✅ Page loads under 2s on desktop (no heavy assets, no API calls on load)
- ✅ The 3-act narrative arc (hook → method → product) is legible in the scroll structure without requiring interaction

## Related Documents

- [Analysis](./analysis.md) – Open questions, dependency mapping, and scope exclusion rationale
- [Solution Architecture](./architecture.md) – Component tree, route strategy, and scroll architecture
- [Timeline](./timeline.md) – Status tracking and delivery sequence