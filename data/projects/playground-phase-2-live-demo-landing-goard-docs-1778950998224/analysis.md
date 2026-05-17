# 🔍 Playground Phase 2 — Live Demo, Landing & Goard Docs — Analysis

## The Problem
The playground proves specview's design system exists but doesn't prove the product works. Visitors see components in isolation, never the assembled app experience. Phase 2 closes that gap — but the brain dump conflates "wrap existing LivePlaygroundComponent" with "rebuild half the landing page as Angular components and add Goard-style editorial depth," which is three different-sized efforts wearing one trenchcoat.

## Hard Constraints
- Angular 17 standalone, signals, OnPush, `@if`/`@for` — no exceptions
- Zero live API calls — all data from `playground-demo-data.ts`
- Existing anchor links and dark-mode behavior preserved
- No new design tokens; no border-radius; no shadows
- Must pass `ng build --configuration production` clean

## Open Questions
- **Which landing sections actually earn their space?** Output cards and 3-step process demonstrate the product. Pricing, FAQ, and comparison table are marketing — do they belong in a case study narrative, or does including them turn the playground into a second landing page?
- **What's the CTA?** The brain dump mentions "CTA / closing" but never says what visitors should *do*. Waitlist signup? GitHub link? "Try it" with no backend?
- **Personas — real or aspirational?** "Not fake personas, but real user archetypes" requires real user data. Solo project with no public users yet. Build these from Sam's own pain points only, or skip entirely?
- **Acts grouping in nav — ship or defer?** 11 sections need hierarchy, but the grouped-nav interaction pattern doesn't exist yet and is a component unto itself.

## Dependencies & Sequencing
- Live demo section is zero-effort *only if* `LivePlaygroundComponent` still compiles unchanged — verify before planning around it
- Landing showcase components depend on deciding which sections survive the cut (previous question)
- Problem statement and journey map are pure content — no code dependency — but block narrative coherence of the whole page
- Nav refactor (acts) blocks nothing but must land before or with the new sections, not after

## Explicitly Out of Scope
- **Pricing section** — marketing conversion content, not product demonstration; re-scope when checkout flow exists
- **Comparison table** — competitive positioning belongs on landing page; duplicating it dilutes both
- **FAQ accordion** — informational, not demonstrative; adds lines without advancing the narrative
- **Real user research / interviews** — no user base yet; re-scope post-launch when real feedback exists
- **Before/after line-by-line diff view** — high-effort custom component for one section; revisit as a standalone feature