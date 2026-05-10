# 🎯 Epic: App UI Mockups

## Business Value

Specview's overview page was designed through rapid HTML mockup iteration (`landing/app-overview.html`), validating design decisions across three variants, a ClawBoi gap analysis, a playground color audit, and multiple refinement passes. The mockup is locked — the remaining work is applying these validated decisions to the live Angular app (`web-ng/`).

The app currently uses the Phase 2 grid (240px min, grey background fill, horizontal card borders, no section color, no badges). The mock introduces: 280px cards with vertical-only rules, serif teasers, colored section headers with ink underline, state-based badges, playground 5.7 status bar colors, and featured first-card sizing.

## Scope

### What This Epic Covers

- **Grid + card styling** — wider cards (280px), vertical-only separators, generous padding (20px 24px), no grey fill on empty columns
- **Section headers + dividers** — colored overline titles, 2px ink underline spanning title text only, pill badge counts, inter-section dividers
- **Typography** — Source Serif 4 on teasers at 14px, featured first-card (17px title, 3-line clamp)
- **Status bar colors** — playground 5.7 state colors (idle/active/success/failure) with shimmer track
- **Badge system** — grey count pills, state-colored status badges (NEW=red, COMPLETE=green, READY=accent)
- **Section color tokens** — `[data-section]` attribute selectors setting `--section-color` for header titles

### What This Epic Does NOT Cover

- ❌ **Hero grid (2fr 1fr 1fr)** — requires Angular template logic changes beyond CSS; separate epic
- ❌ **Page 2: app-reader.html** — not started; separate epic
- ❌ **Masonry layout** — explicitly rejected (browser support)
- ❌ **ClawBoi mood color scale** — no concrete use case
- ❌ **CSS promotion to landing/style.css** — Angular does not import landing CSS; changes go directly to `web-ng/src/styles.css`

## Tasks

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **Grid system + card styling** | None | 0.5 days | High |
| 2 | **Section headers + dividers** | None | 0.5 days | High |
| 3 | **Typography — serif teasers** | None | 0.5 days | High |
| 4 | **Status bar colors** | None | 0.5 days | Medium |
| 5 | **Badge system** | None | 0.5 days | Medium |

All tasks are independent and target `web-ng/src/styles.css`. Tasks 1-3 have the most visual impact.

## Success Criteria

- ✅ Cards use 280px min-width, 20px 24px padding, vertical-only separators, no grey fill
- ✅ Section headers show colored title with 2px ink underline spanning title text only
- ✅ Teaser text renders in Source Serif 4 at 14px
- ✅ First card in each section has 17px title and 3-line teaser clamp
- ✅ Status bar uses playground 5.7 colors (amber active, green idle/success, red failure)
- ✅ Badge classes available: `.badge` (grey), `.badge--new` (red), `.badge--complete` (green), `.badge--ready` (blue)
- ✅ Section color tokens defined for Active, Specced, Ready to build, Braindumps
- ✅ Docker rebuild shows all changes in live app

## Related Documents

- [Analysis](./analysis.md) — Open questions (all resolved)
- [Solution Architecture](./architecture.md) — Design principles and decisions
- [Implementation Guide](./implementation-guide.md) — Step-by-step execution plan
- [Timeline](./timeline.md) — Status tracking
