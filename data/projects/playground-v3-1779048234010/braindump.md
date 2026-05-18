# Playground V3

Next iteration of the playground — informs both the app and landing page.

## Shape

One long scroll. No traditional navigation. About 5 pages/sections within the scroll.

## UX model

Guard / restaurant UX — guided progression. Onboarding-style. The user is walked through sections like a restaurant experience (greet → seat → menu → order → serve). Each transition is intentional and gated.

## Design patterns

Every design pattern is exercised across each page — not documented explicitly, but demonstrated in use. The playground IS the patterns working together.

## Tone

Clean. Minimal text per page. Let the design breathe.

---

## Context: Design System (from ref-design-system.md)

**Philosophy:** Dieter Rams minimalism + editorial newspaper layout.
- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace as structure, not decoration
- Ink on paper: cream background, near-black ink, no shadows
- Interaction is quiet — hover states are barely-there

**Colors:** warm off-white (#FFFEF9), near-black ink (#121212), muted slate blue accent (#567B95), red (#C41E3A).

**Typography:** Playfair Display (headlines), Source Serif 4 (body), Source Sans 3 (labels/UI).

**Type Scale:**
- Masthead: 56–64px Playfair 700
- Hero headline: 44px Playfair 700
- Section title: 28–36px Playfair 700
- Card title: 18–22px Playfair 700
- Body: 15–17px Source Serif, line-height 1.65–1.75
- Label: 11–12px Source Sans 600, uppercase, tracking 0.08–0.12em

**Layout:** max-width 1400px, 12-col grid, newspaper borders, no shadows, square elements.

---

## Context: Live Component Playground (from live-component-playground braindump)

What shipped: a live interactive playground where every V2 sub-component renders with real services and real data. Sections include:
- Section nav (interactive tabs, counts, pulse animation)
- Status bar (all 4 states: idle, active, success, failure)
- Project grid (clickable cards with real project data)
- Expanded panel (sidebar + reader with rendered markdown)
- Dark mode toggle affecting all components simultaneously

Key insight: the live playground proves components work — it's the best demo for new users because they see every feature in action.

---

## Context: Playground Phase 2 (from phase 2 braindump)

Phase 2 added three pillars to the case study shell:
1. **Live app demo** — the actual specview app UI with demo data (not screenshots)
2. **Landing showcase** — key landing page patterns as Angular components
3. **Goard-inspired product docs** — narrative arc: problem → process → journey → screens → patterns

What Goard (food delivery case study) does well:
- Problem statement with real pain articulation
- Process visualization (user journey, not just AI pipeline)
- Screen annotations explaining why each piece exists
- Before/after transformation (messy braindump → structured spec)
- Journey map with honest pain points at each stage

Current structure (pg-case-study.component.ts): hero, pipeline, live app demo, landing showcase, design language, screen gallery, patterns, dark mode, user journey.

---

## Context: UX Audit — Executed Projects

| Project | Focus | Status |
|---------|-------|--------|
| ux-grid-polish | App grid layout & spacing | done |
| ux-landing-grid-polish | Landing grid alignment | done |
| ux-polish-newspaper | Newspaper design pass | done |
| ux-reader-textops | Reader panel + text ops | done |
| landing-phase3-polish | Landing page phase 3 | done |
| playground-design-system | Design system in playground | done |
| playground-phase2-missing-sections | 12 remaining demos | done |
| live-component-playground | Live interactive playground | done |
| app-v3-state-extraction | V3 state extraction + shell | done |

---

## Context: Groad Reference (food ordering UX case study)

PDF at `docs/design-references/Groad - Food Ordering System - UI_UX Case Study.pdf`

Key patterns to port:
- Universal narrative arc (problem → process → branding → journey → screens → patterns)
- Restaurant/guard UX: guided progression through ordering flow
- Clean pages with minimal text, large visuals
- Each screen demonstrates the design system in action
- Section transitions are intentional, not just scrolling
