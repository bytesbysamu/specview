# 🎯 Epic: landing-polish-newspaper

## Business Value

The Specview landing page is the first contact surface for prospective users — it has to prove the product, not just describe it. Today the landing establishes the newspaper aesthetic at the masthead level but fails to demonstrate it through the page: the tagline uses the wrong font family, the hero aside is a flat bullet list instead of the output-card grid the CSS already supports, and a fully-styled demo strip exists in stylesheet form but was never rendered. Visitors leave without seeing what the product produces.

Closing these gaps converts the landing from a brochure into a demonstration. The output-card grid gives editorial weight to each generated artifact (Analysis, Epic, Architecture, Timeline, Implementation Guide) — visitors see the deliverables before signing up. The demo strip places a miniature of the app's UI inside the marketing page, proving the newspaper aesthetic is a product reality, not a marketing affectation. Editorial step bodies and a tagline typography fix close the credibility loop.

The buyer is the solo developer or small team evaluating spec-doc against ad-hoc prompting workflows. They pay $29/mo (Pro tier) once convinced the output is editorially serious. Polish on the landing directly raises the conversion rate on the existing pricing surface — no new product work required.

## Scope

### What This Epic Covers
- **Tagline typography fix** – swap `.masthead-tagline` from `var(--sans)` to `var(--body)` italic to match design-system intent
- **Hero output-card grid** – replace flat `.lede-aside` `<ul>` with the existing `.output-grid` / `.output-card` system rendering 5 generated-document cards
- **Demo strip section** – wire HTML for the existing `.demo-strip` CSS into a new section between "How it works" and "Pricing"
- **Step editorial bodies** – add one-sentence `<p class="step-body">` above each `.step-code` block in the 3 step columns
- **Section nav + metrics + dark-mode audit** – add "Demo" nav link, refresh metrics counts, verify dark-mode parity for new/changed components

### What This Epic Does NOT Cover
- ❌ App (`web-ng/`) polish — owned by `ux-polish-newspaper-1778238000`
- ❌ New design tokens — existing set is complete
- ❌ Playground HTML edits — read-only contract
- ❌ Responsive breakpoint rework — existing breakpoints hold
- ❌ JS behavior beyond existing theme toggle — no new interactivity
- ❌ Pricing tier or copy changes — visual polish only
- ❌ New font families — Playfair Display / Source Serif 4 / Source Sans 3 are the complete set

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Tagline + Step Bodies** | None | yes (with #2) | 0.5 days | High |
| 2 | **Hero Output-Card Grid** | None | yes (with #1) | 1 day | High |
| 3 | **Demo Strip Section** | #2 | — | 1.5 days | High |
| 4 | **Section Nav + Metrics Refresh** | #3 | — | 0.5 days | Low |
| 5 | **Dark-Mode Parity Audit** | #1, #2, #3, #4 | — | 0.5 days | High |

## Success Criteria

- ✅ `.masthead-tagline` renders in Source Serif 4 italic at 13px in both themes
- ✅ Hero aside displays 5 `.output-card` elements in a 2-column grid, each with icon + Playfair title + monospace filename + body
- ✅ A `.demo-strip` section is rendered between "How it works" and "Pricing", visible in light and dark modes
- ✅ Each of the 3 "How it works" steps has a `<p class="step-body">` editorial sentence above its `.step-code` block
- ✅ Section nav contains 4 links (What / How it works / Demo / Pricing) and remains visually balanced
- ✅ Metrics bar reflects current tests / commits / projects counts
- ✅ `docker compose build landing && docker compose up -d landing` succeeds with no console errors
- ✅ No inline styles introduced; all CSS lives in `landing/style.css`
- ✅ No shadows added anywhere; no new font families introduced
- ✅ Dark-mode hover states for `.output-card` and `.demo-strip` are visually consistent with light mode

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking