# 🎯 Epic: UX Polish — Newspaper Feel, Phase 2

## Business Value

Specview's value proposition is "documentation-first thinking" — a tool where ideas come forward and the interface recedes. The newspaper aesthetic established by ClawBoi and the Specview landing page is the visual proof of that proposition: editorial typography, semantic color, borders over shadows. The app currently breaks that promise. A user moves from the landing page (which sells the vision) into the app (which feels like a different product) and the cognitive dissonance erodes trust in the product's design conviction.

This epic is brand cohesion work with direct conversion impact. The landing-to-app transition is where prospective users decide whether the tool delivers on what it advertised. Closing the typographic, structural, and semantic gaps means the app ships the same editorial authority the marketing surface promises — masthead at 64px Playfair, the nameplate rule under the masthead, red overlines above section flags, semantic-only color for state. For a solo-founder tool sold on aesthetic and methodology, design coherence is the product.

The buyer is the methodology-conscious solo developer or small team who already values "ideas over chrome." They are paying for taste as much as functionality. Every drift between landing and app is a refund risk.

## Scope

### What This Epic Covers
- **Masthead alignment** — title to 64px, tagline to Source Serif italic, `align-items: flex-end`
- **Nameplate rule** — 3px `--ink` `border-top` on the section nav, matching the landing
- **Overline pattern adoption** — red overline class applied to section group headers, reader file-type label, and error states
- **Icon system standardization** — 13px / stroke 1.75, semantic color by context, op chip icon mapping (expand/compress/clarify/simplify/tldr/bullets/brainstorm/style/undo/redo)
- **Dark-mode contrast fixes** — modal elevation, sticky toolbar border, section nav separation, icon contrast floor at `--ink-light`
- **Spec file sidebar ordering** — canonical sequence (braindump → analysis → epic → architecture → timeline → implementation-guide)

### What This Epic Does NOT Cover
- ❌ `--status-attention` token / stale-spec detection — token may be reserved, feature is not in this epic
- ❌ Landing page or ClawBoi changes — app-only (`web-ng/`)
- ❌ New components beyond what the playground already shows — alignment, not invention
- ❌ Markdown rendering engine changes — 2-column flow stays CSS-only (`column-count: 2`)
- ❌ Full WCAG accessibility audit — only the stated 3:1 icon floor is in scope
- ❌ Animation system overhaul — existing pulsing dot is sufficient
- ❌ Settings page or any new app surface
- ❌ Reverting `--status-running` to amber — explicitly forbidden

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Token & Overline Foundation** | None | — | 0.5 days | High |
| 2 | **Masthead & Nameplate Typography** | 1 | 3, 4, 5 | 1 day | High |
| 3 | **Overline Adoption Across App** | 1 | 2, 4, 5 | 1 day | High |
| 4 | **Icon System Standardization & Op Chip Mapping** | 1 | 2, 3, 5 | 1 day | High |
| 5 | **Dark-Mode Contrast Fixes** | 1 | 2, 3, 4 | 1 day | High |
| 6 | **Spec File Sidebar Ordering** | None | 2, 3, 4, 5 | 0.5 days | Low |

## Success Criteria

- ✅ Masthead matches landing: title 64px Playfair, tagline Source Serif italic 13px, `align-items: flex-end`
- ✅ Section nav has 3px `--ink` `border-top` (nameplate rule) in both light and dark modes
- ✅ Red overline class exists once and is consumed by section group headers, reader file-type label, and error states — no duplicated overline styling
- ✅ All content icons render at 13px with stroke-width 1.75; no `1em` inheritance remains in icon usage
- ✅ Op chips display the mapped Lucide icon (compress → minimize-2, clarify → help-circle, etc.) for every operation in the chain
- ✅ All meaningful UI icons in dark mode clear 3:1 contrast (floor: `--ink-light` `#A0A0A0`); navigational-only icons may stay at `--ink-muted`
- ✅ Modal in dark mode visually separates from the dimmed backdrop (chosen elevation treatment applied consistently)
- ✅ Sticky section nav and editor toolbar have a clearly visible structural edge in dark mode
- ✅ `--status-running` remains `#22A66A` green; no amber appears for any state in the app
- ✅ Gray (`--ink-muted`) is not used for any state-bearing element; idle = gray (no state) is the only allowed gray usage
- ✅ Spec file sidebar renders in canonical order (braindump → analysis → epic → architecture → timeline → implementation-guide) regardless of filesystem order
- ✅ Side-by-side screenshot of landing masthead and app masthead is visually indistinguishable (modulo content)
- ✅ Angular production build passes (`ng build --configuration production`); all touched files remain under 200 lines

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking