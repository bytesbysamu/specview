# 🔍 Playground — Design System Extension — Analysis

## The Problem
The live playground at `/playground` demos working components but lacks the design-system documentation (tokens, borders, animations, state matrices) that lived in a now-stale 2,304-line static HTML file. The goal is to merge both halves into one live source of truth, then delete 3,562 lines of dead static assets.

## Hard Constraints
- Files under 200 lines — the brain dump routes all six sections into `live-playground.component.html`, which will blow past this immediately
- No speculative abstractions — each section must earn its place with a concrete current use
- Build order: frontend with mock data first → Flask built to match
- `ng build` must pass; no test regressions
- Single consumer (Sam) — no team onboarding concern

## Open Questions
- **File decomposition**: Six new sections in one HTML file violates the 200-line rule. Split into six child components (e.g., `pg-tokens.component.ts`, `pg-animations.component.ts`)? Or keep one file and treat playground as an explicit exception?
- **Section D data source**: The state matrix needs every V2 component in every state. Are these standalone imports with hardcoded props, or do they pull from the existing mock-data service the playground already uses?
- **Section E boundary**: The "fully interactive expanded panel" is a second running instance of the app's core read flow. Is this re-using the real `ExpandedPanelComponent` with injected demo data, or a simplified replica? Real component = tight coupling to services; replica = drift risk (the exact problem being solved).
- **Spacing scale tokens**: Colors and fonts read from CSS custom properties. Spacing values (8px, 12px, etc.) are hardcoded in component CSS, not tokenized as `--space-*` vars. Document hardcoded conventions as-is, or tokenize spacing first?
- **Existing section overlap**: Sections D, E, and F already partially exist in the current playground. Enhance in place, or tear out and rebuild as new child components?

## Dependencies & Sequencing
- Sections A–C (tokens, borders, animations) are pure CSS reads — no component dependencies, can ship first
- Section D (state matrix) requires every V2 component to be importable standalone with mock inputs — verify this is true before scoping
- Section E (interactive panel) depends on Section D being done (it's the most complex component in the matrix)
- Deletion of old static files is gated on all sections passing visual review — last step, not parallel

## Explicitly Out of Scope
- **Split-screen dark mode before/after** (Section F enhancement) — this is a diffing UI feature, not documentation; re-scope if token debugging becomes a real pain point
- **Spacing tokenization** (`--space-*` CSS custom properties) — prerequisite refactor that doesn't belong in a playground epic; document current hardcoded values only
- **Visual regression testing harness** — the state matrix looks like one, but building snapshot infra is a separate concern; the matrix is for human eyes only
- **Responsive/mobile playground layout** — Telegram is the mobile interface; playground is desktop dev tooling only

---

*Cross-references: [Solution Architecture](./architecture.md) · [Epic](./epic.md) · [Timeline](./timeline.md)*