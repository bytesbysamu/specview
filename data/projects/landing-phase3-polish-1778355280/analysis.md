# 🔍 Landing & App Polish — Phase 3 — Analysis

## The Problem
`landing-v2.html` has five fully-defined CSS components that are never instantiated — the design system is ahead of the HTML and Phase 3 is mostly a promotion exercise. The app carries four unresolved criticals from Phase 2 — including an XSS bypass — that were marked complete in the epic but not in the code. A single epic is trying to fix correctness bugs and apply visual polish simultaneously, which obscures merge safety and makes rollback ambiguous.

## Hard Constraints
- All CSS changes go in `landing/style.css` — no `<style>` blocks in HTML, no inline styles for anything that repeats
- No shadows, no new font families, no JS beyond theme toggle
- `--status-running` is green (`#22A66A`) — never amber for a running state
- `.overline` class definition is frozen — only usage sites change
- `docker compose build landing && docker compose up -d landing` must pass before any PR

## Open Questions
- **XSS fix timing:** Standalone commit before Phase 3 opens (recommended), first-task gate inside Phase 3, or parallel to landing work? This decision determines whether app tasks can start at all.
- **Two-column pull quote:** Replace `.pullquote-single` with `.pullquote-row` (destructive), or add a second pull quote block (additive)? The brain dump says "OR" — pick one before the epic is written.
- **Pricing button hierarchy:** Free = `.btn-secondary`, Pro = `.btn-primary` (recommended), or both `.btn-primary`? Brain dump explicitly flags the design system as ambiguous here.
- **`wordCount` pipe:** Build a proper Angular pipe (recommended), approximate with `char / 5`, or drop word count and show only project name? Scope of `expanded-meta` task depends on this.
- **Op chip icons:** Unicode via `<span class="btn-icon">` (recommended, matches existing pattern) or inline SVG? Must be decided before implementation to prevent two approaches in one file.

## Dependencies & Sequencing
- XSS fix (`bypassSecurityTrustHtml` + DOMPurify) must commit before any app visual tasks — correctness gate, not a style task
- `wordCount` pipe must exist before `expanded-meta` line can ship
- `.section-page--compact` must land in `style.css` before inline overrides are removed from HTML
- Aside-list markup swap unblocks the dark mode audit — `color: var(--border)` text lives inside the same component

## Explicitly Out of Scope
- **Puppeteer visual regression baseline** — good idea; triggers infra work outside the current stack; separate spike
- **Design-system compliance script** — pre-commit tooling, not Phase 3 polish
- **`IntersectionObserver` for `rise` animation** — page-load stagger is sufficient and scoped; observer is speculative complexity; re-scope if scroll behavior becomes a complaint
- **Context cards in the app** — landing only; in-app equivalent is empty-state copy with a different voice, written separately
- **`thinking-pulse` animation** — color tokens already carry state semantics; second animation axis is noise, not signal
- **FAQ micro-CTAs** — converts support copy into a second sales page; re-scope if conversion data supports it