# 🔍 landing-polish-newspaper — Analysis

## The Problem
The Specview landing page established the newspaper aesthetic but doesn't fully embody it: tagline uses the wrong font family, hero aside is a flat `<ul>` instead of the output-card grid the CSS already defines, and a complete `.demo-strip` component exists in CSS but was never wired into HTML. Polish closes those gaps so the landing demonstrates the product, not just describes it.

## Hard Constraints
- All CSS changes in `landing/style.css` — no inline styles, no new files
- No shadows; no new font families beyond Playfair Display / Source Serif 4 / Source Sans 3
- Token values copied verbatim from playground (`http://localhost:8096/playground.html`)
- `.overline` class definition stays as-is
- `docker compose build landing && docker compose up -d landing` must pass before push
- Playground HTML is read-only reference — never edited

## Open Questions
- **Demo strip content** — does it render a static mock of a real generated spec, a generic "lorem-ipsum-newspaper" mock, or a screenshot-style fixed image? (CSS exists; HTML payload undecided.)
- **Output card filenames** — `analysis.md` / `epic.md` / `architecture.md` / `timeline.md` / `implementation/*.md`, or shorter labels? Brain dump says "monospace filename" but doesn't fix the strings.
- **Metrics source** — manually edited numbers, or pulled from a script/file? Brain dump says "update" without specifying cadence.
- **Section nav** — adding "Demo" link: does it scroll-anchor to `#demo` and does the existing centered 3-item layout hold at 4?
- **Dark mode parity** — is "audit" a visual review only, or does it require new dark-mode rules for `.output-card` / `.demo-strip` hover states?

## Dependencies & Sequencing
- Output card grid swap depends on finalizing the 5 card payloads (icon SVG, filename string, body copy)
- Demo strip HTML depends on resolving the content question above
- Section nav addition depends on demo strip landing first (anchor target must exist)
- Dark mode audit runs last — after all new HTML is in place
- Step body copy is independent and can ship first as a warm-up

## Explicitly Out of Scope
- App (`web-ng/`) polish — owned by `ux-polish-newspaper-1778238000`; trigger to re-scope: only if landing exposes a token gap that forces an app change
- New design tokens — existing set is complete; trigger: a required state has no semantic color
- Playground edits — read-only contract
- Responsive breakpoints — existing layout is fine; trigger: demo strip breaks below 768px
- JS behavior beyond existing theme toggle — no interactivity additions
- Pricing copy / tier changes — visual polish only