# 🎯 Epic: landing-v2-playground

## Business Value

Spec Doc's current landing page reads like a museum tour of its own design system — every section announces itself ("here is the masthead," "here is the step grid") instead of just *being* the page. Visitors learn how the components are constructed but not what the product does. For a documentation-first methodology tool, this is fatal: the landing page should *demonstrate the methodology by being well-designed*, not narrate the design.

The playground (`landing/playground.html`) already proves the design system works — every token, pattern, and interaction state is dialed in. What's missing is the shipped application of it. A from-scratch `landing-v2.html` collapses this gap: it consumes the playground as a Figma file and produces a real newspaper landing page where the masthead is a masthead, the lede is a lede, and the steps are steps. No labels, no scaffolding, no meta.

The payer is Sam — solo founder optimizing for a credible front door before sharing Spec Doc with collaborators or potential users. A landing that visibly embodies its own typography and editorial discipline is the cheapest possible proof that the methodology produces shippable artifacts.

## Scope

### What This Epic Covers
- **New file `landing/landing-v2.html`** – built from zero, parallel to existing `index.html`
- **Playground pattern inventory** – confirm every class hook used is present in `style.css`
- **Structural sections** – masthead, lede with output-grid, overline section sequence (what / how / see / start), three-step grid, demo strip, pull quote, pricing, footer
- **Inline SVG icons + theme toggle JS port** – sun/moon glyphs and the date label script copied verbatim from current landing
- **Placeholder editorial copy** – lorem-style filler that respects line lengths and paragraph counts so structure is judgable

### What This Epic Does NOT Cover
- ❌ **Real product copy** — content pass is a separate epic; this epic ships with placeholder editorial filler
- ❌ **Modifying `landing/style.css`** — if a pattern is missing, the section is dropped, not added to CSS
- ❌ **Replacing `index.html`** — swap (`index.html` → `index-old.html`, `landing-v2.html` → `index.html`) is a separate decision
- ❌ **New JavaScript** — only the existing theme toggle and date label are ported; nothing else
- ❌ **CDN icon libraries** — no `data-lucide`, no external icon fonts; inline SVG or emoji only
- ❌ **Code mockup chrome** — no `.step-code` blocks anywhere in the landing
- ❌ **Analytics, forms, backend wiring** — pure static HTML
- ❌ **Mobile-specific tweaks** — rely entirely on `style.css` responsive behavior
- ❌ **Reusable templates or partials** — single HTML file, not a system

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Playground Pattern Inventory** | None | — | 0.25 days | High |
| 2 | **Masthead + Lede Structure** | 1 | — | 0.5 days | High |
| 3 | **Overline Section Sequence (How / See / Start)** | 2 | — | 0.75 days | High |
| 4 | **Demo Strip + Pull Quote + Pricing + Footer** | 2 | with 3 | 0.5 days | High |
| 5 | **Theme Toggle + Date Label Port** | 2 | with 3, 4 | 0.25 days | Low |

## Success Criteria

- ✅ `landing/landing-v2.html` exists and renders at `http://localhost:8096/landing-v2.html` without console errors
- ✅ Zero new CSS classes introduced — every `class="..."` value already appears in `landing/style.css`
- ✅ Zero `style="..."` inline attributes anywhere in the file
- ✅ Zero `<i data-lucide>` references and zero CDN script/style tags beyond what current `index.html` already loads
- ✅ Zero `.step-code` blocks and zero code-mockup chrome in the rendered page
- ✅ All four overline sections present with `.overline` + `.section-heading` pairing
- ✅ Lede uses `.lede` / `.lede-main` / `.lede-aside` / `.lede-divider` and contains an `.output-grid` of 5 `.output-card` elements
- ✅ Steps section is a three-column `.steps` grid with `.step-num` / `.step-title` / `.step-body` only — no code blocks
- ✅ Demo strip uses `.demo-strip` / `.demo-masthead` / `.demo-sidebar` / `.demo-content` as a live page section, not a labeled demo
- ✅ Theme toggle switches light/dark; date label populates on load
- ✅ Existing `landing/index.html` is unchanged after this epic ships

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking