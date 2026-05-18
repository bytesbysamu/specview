# 🔍 Playground V3 — Analysis

## The Problem
The playground exists as two layers — a live component demo (Phase 1) and a case-study shell with 9+ sections (Phase 2). Both prove the system works but neither sells it. V3 consolidates into a single guided scroll (~5 sections) that exercises every design pattern through demonstration, not documentation — serving as the canonical reference for both the app and landing page.

## Hard Constraints
- Design system is locked (ref-design-system.md, all UX polish projects done)
- Angular standalone components, spec-doc stack (Flask :3101 + Angular :4201)
- Cream/ink/slate palette, Playfair + Source Serif + Source Sans type stack
- No shadows, no decorative chrome — newspaper layout rules apply
- Single consumer (Sam) — playground must be self-documenting without a walkthrough

## Open Questions
- **What does "gated" mean mechanically?** Scroll-triggered reveal (IntersectionObserver + CSS transitions), click-to-advance (stepper), or scroll-snapping? Each implies different complexity and mobile behavior
- **What are the ~5 sections?** Current Phase 2 has 9 (hero, pipeline, live demo, landing showcase, design language, screen gallery, patterns, dark mode, journey). What merges and what gets cut?
- **"Informs both app and landing page" — how?** Is the playground a standalone route that shares components into both? A living styleguide that the landing page pulls from? Or just a visual reference Sam eyeballs while building?
- **Annotations or no annotations?** Phase 2's Goard approach explicitly annotates screens ("why this exists"). V3 says "not documented, demonstrated." These contradict — pick one
- **Does the section nav survive?** Phase 1 shipped interactive tabs with counts and pulse animation. "No traditional navigation" kills that — is a scroll-position indicator replacing it, or is nav gone entirely?
- **Dark mode toggle fate?** Phase 1 featured it prominently. A minimal single-scroll may not have room for a toggle — is dark mode still in scope?

## Dependencies & Sequencing
- Section inventory must be decided before layout work — the scroll architecture depends on knowing the ~5 sections
- Gating mechanism choice affects every section's component structure (scroll-reveal needs wrapper directives; stepper needs state)
- If playground feeds components to the landing page, the component API boundaries must be defined before either is built
- App V3 state extraction (done) unblocks embedding the live app demo section

## Explicitly Out of Scope
- **New design system tokens** — system is locked; V3 composes, doesn't extend. Re-scope if a section genuinely can't be built with current tokens
- **Multi-page routing** — "one long scroll" is the constraint. Re-scope only if mobile performance proves a single scroll with all live components is too heavy
- **Content writing / copywriting** — "minimal text" means this is a layout/composition project, not a content project. Re-scope when the sections are locked and placeholder text needs replacing
- **Phase 1 live playground as separate route** — V3 appears to absorb it. If it doesn't, that's a routing decision for open questions