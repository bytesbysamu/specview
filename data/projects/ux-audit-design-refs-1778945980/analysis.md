# 🔍 Playground 2.0 — Specview Case Study + UX Audit — Analysis

## The Problem
`/playground` currently serves as a component reference (Phase 1/2: tokens, borders, animations, state matrix, 12 demos). The proposal redefines it as a narrative case study modeled on Groad's Behance structure — but the braindump never resolves whether these two purposes coexist on the same page or one replaces the other.

## Hard Constraints
- Angular standalone components, newspaper design system tokens (no drift)
- Desktop-first, no shadows, no border-radius, 3-font stack
- Solo dev — "4 new sections + 5 narrative wrappers" must ship as one coherent pass
- Dark mode must work across the entire page (already solved in Phase 1/2)

## Open Questions
- **Single page or two routes?** Does the component reference survive at `/playground` alongside the case study, get relocated to `/playground/components`, or get subsumed? (Affects nav, scroll depth, and whether Phase 1/2 sections need backward-compat anchors.)
- **Who is the audience?** A Behance case study targets hiring managers / portfolio viewers. A product demo targets prospects. The braindump serves both — pick one primary or the narrative voice will split.
- **"Live generation demo running in background" (Section 1 Hero)** — is this a real API call, a canned animation, or a pre-recorded replay? Each has wildly different build cost.
- **Journey map interactivity depth** — "each station is a mini-demo" could mean a tooltip, a scroll-linked animation, or 8 embedded functional components. What's the ceiling?

## Dependencies & Sequencing
- Narrative wrappers (Sections 4, 6, 7, 8) depend on deciding whether Phase 1/2 component sections keep their current IDs/anchors
- Section 3 (Pipeline) requires deciding on click-to-reveal behavior — inline expand (ClawBoi pattern) or scroll-to-section
- Section 9 (Heritage) requires ClawBoi content to exist somewhere accessible — currently only in a design-system doc, not as a component

## Explicitly Out of Scope
- **Cross-product demos (Ionic theming, Groad food patterns)** — mentioned under "Future" in the braindump; zero current use case; re-scope if a second product ships on the same design system
- **Heritage section (Section 9)** — vanity content with no audience payoff; a visitor converting to signup doesn't care about ClawBoi lineage; re-scope only if building a public design system docs site
- **14-row Groad mapping table** — forcing every Groad section to have a Specview equivalent inflates scope; steal the 3-act arc (hook → method → product), drop the forced 1:1 mapping (driver interface → dark mode is a stretch)
- **Billing/Stripe flow as a live component** — showing a fake checkout in a case study is misleading and requires mock state management for zero narrative value