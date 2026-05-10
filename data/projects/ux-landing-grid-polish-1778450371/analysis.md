# 🔍 UX: Landing & Grid Polish — Analysis

## The Problem
A static HTML mockup (`app-overview.html`) validated design decisions for the app overview. Most have shipped to `web-ng/src/styles.css`, but ~4 CSS inconsistencies remain and the landing page hasn't adopted the output-card grid, demo strip, or step-body editorial rhythm yet. Two surfaces, one polish pass.

## Hard Constraints
- All values in the "Design decisions already locked" table are non-negotiable (grid min-width, card padding, color philosophy, etc.)
- Solo dev — no parallel workstreams; landing HTML and app CSS changes serialize through one person
- No Angular template changes in this epic (hero `2fr 1fr 1fr` grid is explicitly deferred)
- Files under 200 lines; one CSS rule change = one concern

## Open Questions
- **Status bar relocation: in scope or not?** The brain dump makes a firm "match the mock" decision and describes concrete changes (`position: relative`, move element in `app.component.html`, always-render). But the "What to build" section omits it entirely. This is an Angular template change, which contradicts the "App CSS fixes" framing. → Include and rename the section, or defer to a separate ticket?
- **Demo strip content: what populates it?** CSS classes exist but the brain dump never defines what text/markup goes inside `.demo-masthead`, `.demo-sidebar`, `.demo-content`. → Needs a content brief before implementation, or use lorem/placeholder?
- **Overline fix: is there actual bleed-through?** Item 2 says "verify this works — if `.overline` color bleeds through, scope it." This is an investigation disguised as a task. → Verify first, then either delete the task or write the fix?
- **Grid layout for small sections (1-2 cards):** Four "possible directions" listed, none chosen. → Is this in scope at all, or is it future research? If in scope, which direction?

## Dependencies & Sequencing
- Demo strip HTML (item 5) must land before section nav "Demo" link (item 8) — correctly noted in brain dump
- Teaser chars API change (item 3) is backend (`service.py`), not CSS — deploy order matters if frontend expects longer teasers before API ships
- Output card grid (item 4) depends on knowing the 5 card labels/descriptions — content must exist before HTML can be written
- Status bar relocation (if in scope) blocks on Angular template change, which is a different build surface than CSS edits

## Explicitly Out of Scope
- **Hero grid `2fr 1fr 1fr` Angular template change** — brain dump says "deferred." Re-scope when single-section view work begins
- **Newspaper column-first layout redesign** — the 4 "possible directions" are research, not deliverables. Re-scope if card grid still feels wrong after this pass ships
- **Vertical rhythm / `border-bottom` restoration** — marked ❌ in the vision comparison but not in "What to build." Don't let it creep in
- **Any Playground or component-library work** — Playground is a reference, not a build target here