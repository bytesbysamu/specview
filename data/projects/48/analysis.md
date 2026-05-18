# 🔍 UX: App Grid Polish — Analysis

## The Problem
The project grid in `web-ng` has three compounding issues: Braindumps cards show an identical static string regardless of content, all sections are visually indistinguishable at a glance, and card padding at `12px 8px` makes content feel compressed. Two additional concerns — an icon library swap and a playground pattern backport — were appended to this brain dump and need scoping decisions before they can enter the epic.

## Hard Constraints
- No new npm packages requiring TS or component changes — icons must be asset/CSS/HTML only
- All color must use existing CSS variables — no new palette additions
- Dark mode must work without extra rules — `currentColor` or existing variables only
- Zero changes to layout structure, landing page, typography system, or existing components
- `[attr.data-section]` values in Angular must match CSS attribute selectors exactly — a mismatch silently breaks all color logic

## Open Questions
- **Icons: decided or deferred?** Brain dump says "evaluate Lucide first" — is this epic blocked on that evaluation? (a) Include Lucide sprite in this epic; (b) defer icons to their own epic; (c) Heroicons copy-paste now, revisit later
- **Section 5 scope gate:** Items 5a–5k are audit findings, not grid polish. Which ship here? (a) Only items already touching grid-affected files (5b, 5c, 5e); (b) all high-impact 5a–5e together; (c) none — separate epic
- **5d retry button:** "Confirm the retry button is actually rendered" is an investigation, not a fix. (a) Investigate + fix in this epic; (b) file as a separate bug; (c) skip until confirmed broken
- **Padding arithmetic between items 2 and 3:** Item 2 says reduce `padding-left` by 3px after adding the border; item 3 raises base padding to `16px 12px`. What is the final `padding-left` on a bordered card? This must be resolved before either item is implemented.

## Dependencies & Sequencing
- Item 3 (spacing) must be settled before item 2 (color borders) finalizes its `padding-left` value — both write to `.file-item`
- Item 4 (icons) and item 2 both modify `app.component.html` — coordinate or sequence to avoid merge conflict
- All section-5 `styles.css` changes (5a–5g) will conflict with items 2 and 3 if worked in parallel

## Explicitly Out of Scope
- **Items 5h and 5k** — explicitly marked future/low-priority in the brain dump itself; no delivery pressure exists
- **Items 5f, 5g, 5i, 5j** — medium/lower polish unrelated to the grid; re-scope if a dedicated playground-backport sprint is scheduled
- **Icon library evaluation** — "evaluate Lucide first" is research; the epic should receive a decision, not carry the evaluation
- **Retry button wiring (5d)** — unknown current state makes this a bug investigation, not a polish task; re-scope once confirmed broken