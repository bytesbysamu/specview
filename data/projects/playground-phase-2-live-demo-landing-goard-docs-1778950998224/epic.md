# 🎯 Epic: Playground Phase 2 — Live Demo, Landing & Goard Docs

## Business Value

The playground currently proves specview's design system exists in isolation — tokens, borders, animations, state matrices — but never shows the assembled product experience. A visitor who lands on `/playground` today sees a component museum, not a product. Phase 2 closes that gap by embedding the actual working app (with demo data) inside an editorial narrative, transforming the playground from "look what we built" into "experience what you'd use." This is the difference between a portfolio piece and a conversion tool.

For a solo-founder product with no marketing budget, the playground *is* the sales funnel. Every section must answer one question: "What would using this feel like?" The live demo answers it directly. The landing showcase answers "What do I get?" The problem statement and journey map answer "Why do I need this?" Together they form a self-contained product story that replaces a demo call, a sales deck, and a docs site — all without a single live API call or fake checkout flow.

The target visitor is a technical founder or tech lead evaluating spec-generation tools. They won't read marketing copy, but they will click through a working demo. Showing real components rendering real (demo) data — project grids, sidebars, rendered markdown, status bars — creates the kind of "aha" moment that static screenshots and feature lists cannot. This is the playground earning its hosting cost.

## Scope

### What This Epic Covers

- **Live App Demo Section** – Wrap the existing `LivePlaygroundComponent` in editorial narrative context (overline, headline, deck, pull quote) and integrate it into the case study shell as a clickable, browsable product experience
- **Problem Statement Section** – Goard-inspired editorial section articulating why specs matter, what happens without them, and what pain specview eliminates; pure content with existing design tokens
- **Landing Showcase Section** – Output cards (5 deliverables) and 3-step "how it works" process rebuilt as interactive Angular components inside the playground narrative; the two landing patterns that directly demonstrate the product
- **Enhanced User Journey** – Upgrade the existing simple timeline into a Goard-style journey map with pain-point annotations and stage-by-stage editorial callouts
- **Navigation Acts Grouping** – Reorganize the sticky nav to accommodate 11 sections via grouped acts (Act 1–4), preventing nav overflow and providing narrative structure

### What This Epic Does NOT Cover

- ❌ **Pricing section** — Marketing conversion content; no checkout flow exists to back it up
- ❌ **Comparison table** — Competitive positioning belongs on the landing page; duplicating dilutes both
- ❌ **FAQ accordion** — Informational, not demonstrative; adds weight without advancing narrative
- ❌ **Before/after line-by-line diff view** — High-effort custom component for one section; revisit as standalone feature
- ❌ **Real user personas from research** — No user base yet; build from Sam's own pain points only within the problem statement
- ❌ **Iframe embedding of landing page** — Rebuild as Angular components instead for dark-mode and IntersectionObserver compatibility
- ❌ **Heritage/origin story content** — Vanity content identified in Phase 1 retrospective

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Live App Demo Section** | None | — | 2 days | High |
| 2 | **Problem Statement Section** | None | With #1 | 1 day | High |
| 3 | **Landing Showcase Components** | None | With #1, #2 | 3 days | High |
| 4 | **Navigation Acts Grouping** | #1, #2, #3 | — | 1 day | High |
| 5 | **Enhanced User Journey Map** | #2 (narrative context) | With #3 | 2 days | Low |

## Success Criteria

- ✅ Visitor can click through the full app experience (project grid → sidebar → reader panel) using demo data without any API calls
- ✅ All 5 output deliverables (Analysis, Epic, Architecture, Timeline, Implementation Guide) are visually communicated with descriptions in the landing showcase
- ✅ The 3-step process section clearly communicates braindump → generation → implementation guide
- ✅ Problem statement section articulates at least 3 concrete pain points specview solves
- ✅ Navigation accommodates all sections without horizontal overflow or truncation at 1024px viewport
- ✅ All existing Phase 1 anchor links remain functional
- ✅ Dark mode toggle applies correctly to all new sections
- ✅ `ng build --configuration production` completes with zero errors and zero warnings

## Related Documents

- [Analysis](./analysis.md) – Problems, open questions, and out-of-scope decisions driving this epic
- [Solution Architecture](./architecture.md) – Component structure, data flow, and integration patterns
- [Timeline](./timeline.md) – Execution status and delivery tracking