# 🎯 Epic: UX: Landing & Grid Polish

## Business Value

The landing page is the conversion surface for spec-doc — the first thing a visitor sees before deciding whether the tool is worth trying. The current page uses a flat `<ul>` where the validated mockup proved that an output-card grid, demo strip, and editorial step bodies communicate the product's value far more effectively. Every missing element is a missed opportunity to show, not tell, what the tool produces. Closing these gaps turns the landing page from a feature list into a working product demo.

Inside the app, small CSS divergences between the validated mockup and live styles erode the editorial authority the design system was built to project. Grey pill badges, muted overlines, and longer teaser windows are details individually trivial but collectively responsible for the difference between "polished tool" and "prototype." For a solo-founder product competing on craft, that gap is the product-market signal. Users of documentation tools judge the tool by its own documentation and presentation — inconsistency here is a direct credibility cost.

This epic is a single polish pass across two surfaces (app CSS, landing HTML) that closes the remaining mockup-to-production gaps without touching Angular templates or introducing new architectural patterns.

## Scope

### What This Epic Covers

- **App CSS alignment** – Pill badge styling for nav count badges, overline color verification in app context, and separator class name consistency (`styles.css` only, no template changes)
- **Teaser window expansion** – Increase `teaser_chars` from 300 to 500 in the API so braindump-heavy projects surface meaningful prose instead of fallback text
- **Landing output card grid** – Replace the flat `<ul>` in `.lede-aside` with 5 `.output-card` elements using existing CSS classes, and add `<p class="step-body">` editorial rhythm to the "How it works" section
- **Landing demo strip** – Wire the `.demo-strip` HTML section between "How it works" and "Pricing", add corresponding 4th section nav link
- **Masthead tagline font correction** – Single CSS rule change from `var(--sans)` to `var(--body)` for editorial deck styling

### What This Epic Does NOT Cover

- ❌ **Hero grid `2fr 1fr 1fr` Angular template change** — Deferred until single-section view work begins; requires Angular template surgery outside this CSS/HTML scope
- ❌ **Status bar relocation** — Moving `.gen-status-bar` from fixed-bottom to inline-flow requires Angular template changes (`app.component.html`) and always-render logic; different build surface than CSS edits; separate ticket
- ❌ **Newspaper column-first layout for small sections** — Four possible directions identified, none chosen; this is research, not a deliverable
- ❌ **Vertical rhythm / `border-bottom` restoration** — Not included in "What to build"; do not let it creep in
- ❌ **Playground or component-library changes** — Playground is a design reference, not a build target

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **App CSS Alignment** — Pill-style `.section-count`, verify `.overline` scoping in app context, normalize `.file-item-meta-sep` / `.sep` class name | None | — | 0.5 days | High |
| 2 | **Teaser Window Expansion** — Change `teaser_chars=300` → `500` in `service.py`; verify braindump-heavy projects surface prose | None | T1 | 0.5 days | High |
| 3 | **Landing: Output Card Grid & Step Bodies** — Replace `.lede-aside` `<ul>` with 5 `.output-card` elements; add `<p class="step-body">` above each `.step-code` in "How it works" | None | T1, T2 | 1 day | High |
| 4 | **Landing: Demo Strip & Section Nav** — Wire `.demo-strip` section HTML between "How it works" and "Pricing"; add 4th nav link ("Demo") pointing to the new section | T3 | — | 1 day | High |
| 5 | **Masthead Tagline Font** — Change `.masthead-tagline` `font-family` from `var(--sans)` to `var(--body)` in `landing/style.css` | None | T1–T4 | 0.5 days | Low |

## Success Criteria

- ✅ Nav count badges render as grey pill badges (`background: var(--border)`, `border-radius: 2px`) in the live app, matching the mockup
- ✅ App-context `.overline` elements render in `var(--ink-muted)` — not red — within section group headers
- ✅ Projects whose first prose sentence falls between chars 300–500 display a real teaser instead of fallback text
- ✅ Landing hero aside shows 5 output cards (Analysis, Epic, Architecture, Timeline, Implementation Guide) using `.output-card` grid, not a flat `<ul>`
- ✅ "How it works" steps each have a `<p class="step-body">` sentence creating editorial rhythm above the code mockup
- ✅ Demo strip section is visible between "How it works" and "Pricing" with section nav linking to it
- ✅ Masthead tagline renders in `Source Serif 4 italic 13px`, not `Source Sans 3`
- ✅ All locked design decisions (grid min-width, card padding, color philosophy, etc.) remain unchanged

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design and CSS/HTML change specifications
- [Timeline](./timeline.md) – Status tracking