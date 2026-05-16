# 🔍 Playground Phase 2 — Missing Sections — Analysis

## The Problem
Phase 1 added design tokens, borders, animations, and a state matrix to `/playground`. The old static playground still has 12 component demos that aren't in the live version. Phase 2 ports those remaining demos into 3 new child components + 1 extension so the static playground can be retired.

## Hard Constraints
- All files under 200 lines each (ts, html, css separately)
- Angular standalone components, one per file
- No new dependencies — render using existing CSS classes from `styles.css` and `landing/style.css`
- `ng build` must pass, zero regressions in existing 10 sections

## Open Questions
- **Count mismatch**: Intro says "10 remaining sections," inventory lists 12 items, implementation produces 3 sections + 1 extension. Which number is the source of truth? (a) 10 was approximate and 12 is correct, (b) some items were meant to be grouped and the section count is 10, (c) typo
- **Landing CSS isolation**: `pg-landing` renders markup expecting `landing/style.css` classes. How do those styles reach the playground? (a) Component-scoped `styleUrls` pointing to landing CSS, (b) duplicate the relevant rules into `pg-landing.component.css`, (c) global import — risky bleed
- **200-line feasibility for pg-components**: 8 separate demos in one component — the HTML alone will push past 200 lines. Split into two components now, or accept the overage?
- **Old static playground deletion**: Success criteria says "fully replaced — zero missing sections." Is deleting the old file in scope for Phase 2, or is that a separate cleanup task?
- **Heritage table relevance**: "ClawBoi vs Specview heritage" is project history, not a UI component demo. Does it belong in a design-system playground, or should it live in docs?

## Dependencies & Sequencing
- `pg-components` and `pg-landing` are independent — can be built in parallel
- `pg-interactions` depends on `pg-components` existing (it renders hover states for elements defined there)
- State matrix extension (App vs Landing table) depends on nothing — independent
- Landing CSS question **blocks** `pg-landing` — wrong answer means rework

## Explicitly Out of Scope
- **Refactoring existing Phase 1 sections** — separate PR if needed; trigger: bugs found during Phase 2 integration
- **Making demos interactive** (click handlers, live state toggling) — these are static visual demos; trigger: user-testing feedback requests interactivity
- **Responsive/mobile layout for playground itself** — playground is a dev tool, not production UI; trigger: if playground is ever exposed to non-dev users
- **New component creation** (components not in the verified inventory) — no speculative additions; trigger: discovery of missed components during implementation