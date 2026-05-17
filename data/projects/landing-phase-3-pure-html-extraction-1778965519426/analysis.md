# 🔍 Landing Phase 3 — Pure HTML Extraction — Analysis

## The Problem
`landing-v2.html` exists but violates the design system (border-radius, shadows, wrong fonts, inline styles). Rather than patch it, this rewrites from scratch using playground components as content source — extracting curated sections into clean, design-system-compliant static HTML.

## Hard Constraints
- Zero new CSS — only instantiate existing `style.css` classes
- No inline styles, no hardcoded colors, no border-radius, no box-shadow
- Three fonts only: Playfair Display, Source Serif 4, Source Sans 3
- Same deployment: `landing/` dir, nginx container, single HTML + CSS
- All content hardcoded — no JS data binding (dark mode toggle is the one JS exception)
- Colors exclusively via tokens: `--ink`, `--bg`, `--border`, `--red`, `--accent`

## Open Questions
- **Filename**: Brain dump says rewrite `landing-v2.html` but success criteria says "a single `index.html`" — which ships? Does nginx need a route change?
- **CTA target**: "Get Started" links where? The app (`/generate`)? A signup wall? Waitlist? This decides whether Pro pricing needs a payment link or just a "coming soon."
- **Hero "generating" state**: Showing one file marked as generating without animation — is this a static text label (`Generating...`), a progress bar at fixed width, or a highlighted row? Need to know what class from style.css handles this.
- **Code excerpts in How It Works**: Pull real snippets from `pg-landing-data.ts` verbatim, or editorially rewrite for brevity?

## Dependencies & Sequencing
- Must audit `style.css` for available classes BEFORE writing HTML — if a section needs a pattern that doesn't exist, the section gets cut
- `pg-landing-data.ts` content must be finalized before extraction (any late copy changes propagate manually)
- Comparison table copy (competitor characterizations) is a positioning decision, not an HTML decision — needs sign-off before markup

## Explicitly Out of Scope
- **New CSS classes or tokens** — if style.css can't express it, it dies (re-scope only if style.css gets a Phase 2.5 update)
- **JavaScript beyond dark mode toggle** — no scroll animations, no intersection observers, no dynamic anything
- **A/B testing or analytics instrumentation** — ship clean first, instrument later
- **Competitor research for comparison table** — use existing claims from playground data as-is; don't validate pricing or feature accuracy now