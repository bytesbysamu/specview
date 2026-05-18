# Playground V4 — UX Overhaul

## Context

The playground is Specview's primary conversion tool and portfolio piece. V3 introduced a 5-section scroll-gated shell (Greeting, Kitchen, Main Course, Presentation, Send-Off). It works, but doesn't match the original Groad case study vision or faithfully represent the real app.

This braindump captures everything learned from a deep UX audit cross-referencing the current implementation against the Groad food ordering case study, the architecture docs, and the design system.

---

## Core Problem: The Demo Doesn't Feel Like the Real App

The "Main Course" section (live embedded app) currently stacks the project grid AND detail panel vertically. But the real app uses them mutually exclusively — you see the grid OR the expanded panel, never both. Section nav is in a side column when it should be horizontal. The demo feels like a component reference, not a product you'd actually use.

The fix: mirror the real app's behavior exactly. Grid view shows project cards. Click one — grid disappears, expanded panel (sidebar + reader) takes its place. Close — back to grid. Two distinct "screens" the user flips between naturally.

---

## Missing Narrative Arc (Groad's Secret Sauce)

Groad's case study works because it follows a transformation arc:
1. Here's the pain (problem statement)
2. Here's the process (5 design stages)
3. Here's the result (screen gallery proving it works)
4. Here's the journey (user goes from confused to satisfied)

V3 jumps from "here's a pipeline" straight to "here's the app." No before state. No transformation moment. No "this was broken, now it's fixed" payoff.

What's needed: a Before/After section between hero and pipeline. Messy braindump text on the left, structured spec output on the right. Show the transformation visually — the same content, two states.

---

## Pipeline Section is Static, Not Experiential

The Kitchen currently shows 4 static cards with markdown snippets. It tells you what each stage does but doesn't show the transformation. The architecture docs envision showing the SAME project evolving through stages — braindump becomes analysis, analysis becomes epic, epic becomes architecture.

The demo data already supports this: Payment Gateway Redesign has full content for braindump + analysis + epic + architecture. The pipeline section should click/scroll through these as a single story transforming through four states.

---

## Journey Map is Entirely Missing

The architecture explicitly calls for a journey map: paste → watch → read → iterate → upgrade → share. Horizontal timeline showing user progression from anonymous visitor to power user, with conversion CTA at the end.

This is Groad's "trigger → browsing → ordering → waiting → delivery" equivalent. It contextualizes the product in a user's life, not just as features. Currently the Send-Off has a CTA but no journey visualization leading to it.

---

## Landing Showcase Section Missing

Architecture docs specify a landing page showcase between Live Demo and Design Language — showing the marketing face as a separate product surface. The equivalent in Groad is the "Branding" section showing the logo/colors/type applied to marketing materials. Currently missing entirely.

---

## Presentation Section Lacks Editorial Context

Design tokens, borders, and animations are shown as a raw component reference. No editorial wrapper explaining WHY newspaper aesthetic, WHY no shadows, WHY these three fonts. Groad's branding section tells a story — "we chose warm tones because food apps need approachability." Each decision has reasoning.

The architecture calls for "narrative wrappers" — thin editorial context around each demo. Not just token swatches, but the design philosophy story.

---

## Scroll Gating Adds Friction Without Narrative Value

The original vision says "single continuous scroll with fragment anchors, no lazy-loading." V3 added IntersectionObserver gating (0.6 threshold) that locks sections until previous ones are scrolled. A user who scrolls fast gets blank sections.

Groad uses a single continuous scroll where the narrative pull does the work of holding attention. The artificial gates contradict this. Consider replacing with smooth reveal-on-scroll animations (CSS only, no locked state) that feel like content appearing rather than doors opening.

---

## Dark Mode Hidden Behind Interaction

Groad shows light AND dark variants in the gallery — side by side or in sequence — so the viewer sees both without interacting. V3 hides dark mode behind a toggle button inside the Main Course section. The viewer has to actively click to discover it.

Consider showing light/dark as a split-screen comparison or as a dedicated "Dark Mode" section with token diff table (as the architecture suggests) rather than hiding it behind a button.

---

## Concrete Changes for V4

### P0 — Make the Demo Real
- Main Course: grid-OR-detail mutually exclusive (match real app behavior)
- Section nav: horizontal full-width (not side column)
- Default state: start with detail view pre-loaded (Payment Gateway analysis open) — shows richest content immediately, close reveals grid
- The embedded app should have a mini-masthead ("Specview" title) to frame it as the actual product

### P1 — Add Narrative Transformation
- Before/After section: braindump text → structured spec output, same content, side-by-side
- Pipeline: interactive progression showing ONE project transforming through 4 stages (click/tab through)
- Narrative wrappers on Presentation section: "The Newspaper Aesthetic" story framing the tokens

### P2 — Complete the Arc
- Journey map section: horizontal timeline (paste → watch → read → iterate → share)
- Landing showcase section: show the marketing page as a product artifact
- Dark mode comparison view: side-by-side light/dark, no interaction required

### P3 — Polish
- Remove scroll gating, replace with CSS reveal-on-scroll animations
- Add section progress indicator (sticky nav showing where you are in the narrative)
- Performance: ensure sub-2s load, all content is static (already true)

---

## What's Working (Keep These)

- Newspaper design system is consistent — tokens, borders, typography match design-system.md
- DEMO_MODE injection — clean separation, no HTTP calls
- Demo data quality — Payment Gateway Redesign is believable and complete
- Component extraction — sections are standalone, reusable on landing
- Status bar in "active" mode — shows real-time generation UX immediately
- Five-section narrative structure (Greeting, Kitchen, Main Course, Presentation, Send-Off) — the sections are right, their content needs work

---

## Reference Materials

- Groad case study PDF: docs/design-references/Groad - Food Ordering System - UI_UX Case Study __ Behance.pdf
- Design system: docs/design-system.md
- Architecture (V3): data/projects/playground-phase-2-live-demo-landing-goard-docs-1778950998224/architecture.md
- UX audit project: data/projects/ux-audit-design-refs-1778945980/
- Product behavior: product-behavior.md
- Current implementation: web-ng/src/app/pg-scroll-shell.component.ts, pg-section-live-app.component.ts
