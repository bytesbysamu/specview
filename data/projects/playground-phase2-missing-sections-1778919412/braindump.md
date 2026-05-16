# Playground Phase 2 — Missing Sections

## What this is

Phase 1 added design tokens, borders, animations, and a component state matrix to /playground. Phase 2 adds the 10 remaining sections from the old static playground that are verified to exist in the codebase but aren't yet in the live playground.

## Fact-checked inventory (all verified against source code 2026-05-16)

### App components (in app-v2.component.html + sub-components)

1. **Masthead** — inline in app-v2.component.html lines 8-33. Classes: `.masthead`, `.masthead-top`, `.masthead-center`, `.masthead-date`, `.masthead-title`, `.masthead-tagline`, `.edition`. CSS in styles.css lines 78-130.

2. **Editor Toolbar + Op Chips** — in sidebar-v2.component.html (op chips lines 114-144) and reader-panel.component.html (floating toolbar lines 16-28). Classes: `.op-chip`, `.op-chip--accent`, `.op-chip.active`, `.style-chip`, `.editor-toolbar`, `.editor-toolbar--floating`. CSS in styles.css lines 569-1295.

3. **Modal** — inline in app-v2.component.html lines 186-240. Classes: `.modal-backdrop`, `.modal`, `.modal-header`, `.modal-title`, `.modal-body`, `.modal-input`, `.modal-textarea`, `.modal-footer`, `.modal-cancel`, `.modal-generate`. CSS in styles.css lines 1485-1540.

4. **Update Banner** — inline in app-v2.component.html lines 57-61. Class: `.update-banner`. CSS in styles.css lines 831-851.

5. **Context Cards** — in project-grid.component.html lines 1-11. Classes: `.context-grid`, `.context-card`, `.context-card__label`, `.context-card__desc`. CSS in styles.css lines 854-895.

6. **Search Bar** — inline in app-v2.component.html lines 70-88. Classes: `.search-bar`, `.search-count`. CSS in styles.css lines 188-216.

7. **Overline + Badges** — `.overline` in styles.css line 1626, used in reader-panel and status bar. `.badge` in styles.css line 811, used in project-grid. `.section-count` in styles.css line 710.

8. **Buttons** — all variants: `.btn-primary` (landing/style.css line 246), `.btn-secondary` (landing/style.css line 262), `.new-project-btn` (styles.css line 1461), `.logout-btn` (styles.css line 1446), `.upgrade-btn` (styles.css line 1757), `.btn-icon` (styles.css line 1477).

### Landing-page-only components

9. **Pull Quote** — in landing-v2.html lines 273-280. Classes: `.pullquote-mark`, `.pullquote-single`, `.pullquote-row`. CSS in landing/style.css.

10. **Step Section** — in landing-v2.html lines 185-221. Classes: `.steps`, `.step`, `.step-num`, `.step-title`, `.step-body`, `.step-code`. CSS in landing/style.css lines 391-456.

### Documentation-only

11. **Interaction States** — 39 hover rules in styles.css. Key elements: `.file-item:hover`, `.sidebar-file:hover`, `.context-card:hover`, `.op-chip:hover`, `.style-chip:hover`, `.logout-btn:hover`, `.new-project-btn:hover`, `.search-bar input:focus`.

12. **App vs Landing comparison** — was a static table in the old playground. Two comparison tables: App vs Landing (layout differences) and ClawBoi Origin vs Specview (heritage).

## Implementation plan

### Child component: pg-components.component.ts
Renders all the app components that aren't in the state matrix:

**Masthead demo:**
- Render a live `<header class="masthead">` with the full V1/V2 structure
- Edition label, date, title "Specview", tagline
- Show both app and landing masthead variants (align-items: center vs flex-end)

**Op Chips demo:**
- Render all 8 op chips: Brainstorm, Expand, Compress, Clarify, Simplify, TL;DR, Bullets, Style
- Show active state, accent variant
- Style preset pills below when Style is active

**Modal demo:**
- Render the create project modal inline (not as an overlay — static in the page)
- Show form fields, generate button, cancel button

**Update Banner demo:**
- Render the notification strip with dismiss button

**Context Cards demo:**
- Render the 6 context cards in a grid
- Show hover state on one card

**Search Bar demo:**
- Render the search input with count label
- Show "36 projects" and "3 matches" states

**Overline + Badges demo:**
- Render overline text in all sizes
- Show badge variants: count badge, section badge, status badge

**Buttons demo:**
- All button variants in a row: primary, secondary, new project, logout, upgrade, theme toggle
- Show disabled state for generate button

### Child component: pg-landing.component.ts
Landing-page-only components:

**Pull Quote demo:**
- Render the pull quote with oversized quotation mark
- Show both single and row variants

**Step Section demo:**
- Render the 3-step braindump → generate → read flow
- Use the actual landing page markup

### Child component: pg-interactions.component.ts
Hover/active/focus states:

**Interaction state table:**
- Two-column layout: Default | Hover/Active/Focus
- For each interactive element, render both states side by side
- Use forced inline styles to show hover state without requiring actual hover
- Cover: .file-item, .section-bar a, .btn-primary, .btn-secondary, .op-chip, .modal-input, .context-card, .sidebar-file, .new-project-btn, .logout-btn

### Documentation section in pg-state-matrix (extend)
**App vs Landing comparison:**
- Render as a styled table (not a component — just HTML)
- Two tables: App vs Landing differences, ClawBoi vs Specview heritage

## File count
- `pg-components.component.ts` + `.html` + `.css` (under 200 lines each)
- `pg-landing.component.ts` + `.html` + `.css` (under 200 lines each)
- `pg-interactions.component.ts` + `.html` + `.css` (under 200 lines each)
- Extend `pg-state-matrix.component.html` with App vs Landing table

## What changes in live-playground
- Import 3 new child components
- Add 3 new sections + extend state matrix section
- Total sections after Phase 2: ~14 (6 original + 4 Phase 1 + 3 Phase 2 + 1 extended)

## Success criteria
- Every component from the old static playground has a live equivalent in /playground
- Masthead renders with full newspaper chrome
- All 8 op chips shown with active/accent states
- Modal rendered inline with form fields
- All button variants in one row
- Pull quote with quotation mark
- Interaction states table with default vs hover side by side
- App vs Landing comparison table
- `ng build` passes, no regressions
- Old static playground is fully replaced — zero missing sections
