# 🔍 Playground V4 — UX Overhaul — Analysis

## The Problem
V3's playground shows components stacked vertically instead of mirroring the real app's mutually-exclusive grid/detail pattern. The narrative arc from the Groad case study (pain → process → result → journey) is missing — the demo jumps from pipeline description to live app with no transformation moment. Result: it reads as a component reference, not a product story.

## Hard Constraints
- Solo dev — no parallel workstreams; changes ship sequentially
- Angular standalone components + existing design system tokens (newspaper aesthetic)
- DEMO_MODE injection pattern stays — no HTTP calls in playground
- Sub-2s load, all static content (already true, must remain true)
- Five-section shell structure is kept (content changes, not container)

## Open Questions
- **Before/After placement** — new section between Greeting and Kitchen, or replace Greeting's current content? Adding sections increases scroll length, which contradicts the "narrative pull does the work" principle.
- **Pipeline interactivity model** — tabs (user-driven) or auto-advancing scroll-linked animation (passive)? Tabs are simpler to build; scroll-linked is more Groad-like but harder to get right.
- **"Landing Showcase" content** — does a marketing landing page exist yet to screenshot/embed, or does this section require building a landing page first? If the latter, this is a hidden dependency that doubles scope.
- **Dark mode comparison** — side-by-side (needs 2x render width) or sequential (before/after scroll)? Side-by-side breaks on mobile.

## Dependencies & Sequencing
- Grid-OR-detail fix (P0) must land before Pipeline interactivity (P1) — pipeline clicks into detail view
- Before/After section needs finalized demo data for the "messy braindump" side — is raw text available or must it be written?
- Journey map depends on knowing the actual conversion flow — does "upgrade" mean a pricing page exists?
- Removing scroll gating (P3) should happen LAST — current gating masks any loading jank from new interactive sections

## Explicitly Out of Scope
- **Building an actual landing page** — showcase section should use a static screenshot/mockup, not require a new page. Re-scope when landing page ships independently.
- **New demo projects** — Payment Gateway Redesign already covers all 4 stages. No new content authoring.
- **User accounts / upgrade flow** — journey map visualizes the path but doesn't build the destination. Re-scope post-launch.
- **Mobile-specific layout** — playground is a desktop conversion tool and portfolio piece. Responsive nice-to-have only. Re-scope if analytics show >20% mobile traffic.