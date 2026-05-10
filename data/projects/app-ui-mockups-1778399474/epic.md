# 🎯 Epic: App UI Mockups

## Business Value

Specview's Angular app requires a dev server running for every visual change, creating a friction-heavy design loop that slows iteration on a solo project. A static HTML mockup layer (`landing/app-overview.html`) eliminates that overhead entirely — edit HTML, refresh browser, see results. For a single developer shipping across multiple projects, shaving minutes off each design cycle compounds into hours saved per feature.

The mockup has already proven its value: a full overview page design was iterated through three variants, a ClawBoi gap analysis, a playground color audit, and a grey-fill grid fix — all in a single session. The design decisions captured in the mockup (hero grid, state-based color philosophy, serif teasers, generation status bar) are now locked and ready to transfer. Without this work, the Angular app would still be stuck on the Phase 2 grid with grey-fill bugs and no visual hierarchy.

The remaining work is surgical: resolve the five open design questions surfaced during iteration, promote validated CSS from the mockup's inline `<style>` block into the shared `style.css` design system, and prepare the font dependency — all prerequisites that must land before any Angular implementation can begin. This epic draws a hard line at the mockup boundary; the 8-task Angular implementation plan is a separate effort that consumes this epic's outputs.

## Scope

### What This Epic Covers

- **Open design question resolution** — pick winners for nav icons (text-only vs inline SVG), status strip idle state (hidden vs faint "connected"), hero card progress bar (in-card vs global-only), badge data source (decorative vs API-backed), and canonical port (8096 vs 8097)
- **CSS promotion to `style.css`** — move validated app-specific rules (`.app-header`, `.action-status-strip`, `.section-group`, `[data-section]` selectors, hero grid, hover bleed, badge system) from the mockup's inline `<style>` block into `landing/style.css` so Angular can import them
- **Font dependency** — add `Source Serif 4` to the Google Fonts import chain so the serif teaser decision is available to both mockup and Angular app
- **Hero grid CSS fallback** — design the `2fr 1fr 1fr` grid degradation for 0–1 Active projects (template logic depends on this being solved at the CSS level first)
- **Status strip/bar terminology alignment** — the brain dump uses "status strip" and "status bar" with overlapping placement; reconcile into one named element with one placement

### What This Epic Does NOT Cover

- ❌ **Angular implementation (Tasks 1–8)** — this is a separate epic; eject into its own braindump and run through the spec pipeline as the brain dump's own conclusion states
- ❌ **Page 2: app-reader.html** — not started; separate epic scoped after overview design ships in Angular
- ❌ **Masonry layout** — browser support insufficient for `grid-template-rows: masonry`; explicitly rejected during research
- ❌ **Single unified grid** — loses newspaper column aesthetic in single-section view; explicitly rejected
- ❌ **ClawBoi mood color scale** — no concrete project-health metric exists; do not port speculatively
- ❌ **JavaScript interactions beyond theme toggle** — mockup is pure HTML/CSS; interactivity belongs in the Angular app

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Resolve open design questions** | None | — | 0.5 days | High |
| 2 | **Reconcile status strip/bar naming** | None | With T1 | 0.5 days | High |
| 3 | **Promote validated CSS to `style.css`** | T1, T2 | — | 1 day | High |
| 4 | **Design hero grid fallback for 0–1 items** | T3 | — | 0.5 days | High |
| 5 | **Add Source Serif 4 font dependency** | None | With T1, T2 | 0.5 days | Low |

### Task Notes

**Task 1** — Five decisions need a winner before CSS can be promoted. Nav icons: the mockup shows both text-only (Variant A) and inline SVG (Variant B) but never picks one. Status strip idle: hidden strip or faint "● connected"? Hero card progress bar: inside the Active card or global-only? Badge data source: if badges are real (NEW/COMPLETE/READY), identify which backend field produces these statuses or decide they are client-side derived from existing data. Port: brain dump says 8096, build log says 8097 — one must be canonical.

**Task 2** — The brain dump introduces "action status strip" (below nav, idle/active/success/failure states) and references "status bar" (playground 5.7 colors). The final mock summary lists both a "Status bar" row and uses "status strip" CSS classes. Collapse into one element name, one CSS class prefix, one placement. This unblocks Task 3's class naming.

**Task 3** — The mockup's inline `<style>` block contains ~30 app-specific rules validated through three variants plus audits. These must move into `landing/style.css` before Angular work begins, since Angular imports `style.css`, not the mockup. Includes: `.app-header` family, `.action-status-strip` (or whatever T2 names it), `.section-group` family, `[data-section]` attribute selectors, `.hero-grid` / `.hero-main` / `.hero-secondary`, badge classes, hover bleed rules, and the 7 `@keyframes` animations.

**Task 4** — The `2fr 1fr 1fr` hero grid works well with 2–3 Active projects but looks orphaned with 0 or 1. Design the CSS fallback: single item should either fill full width or fall back to standard grid. Zero items should hide the hero section entirely. This is a CSS-level decision that the Angular template's conditional class logic will consume.

**Task 5** — `Source Serif 4` is referenced in the locked teaser font decision but must be added to `web-ng/index.html`'s Google Fonts `<link>` tag. The mockup already loads it, but the Angular app does not. Can be done independently of all other tasks.

## Success Criteria

- ✅ All five open design questions have documented decisions (nav icons, idle state, progress bar, badges, port)
- ✅ "Status strip" and "status bar" collapsed into one named element with one CSS class prefix
- ✅ Zero app-specific CSS rules remain in `app-overview.html`'s inline `<style>` block — all promoted to `style.css`
- ✅ Hero grid degrades gracefully when Active section has 0 or 1 project (verified in mockup at 1400px viewport)
- ✅ `Source Serif 4` loads in both `landing/app-overview.html` and `web-ng/index.html`
- ✅ `app-overview.html` renders identically before and after CSS promotion (visual regression check via browser refresh)
- ✅ Angular implementation braindump is ejected as a separate document referencing this epic's outputs

## Related Documents

- [Analysis](./analysis.md) — Open questions and dependency sequencing driving this epic
- [Solution Architecture](./architecture.md) — CSS promotion strategy and design system structure
- [Timeline](./timeline.md) — Status tracking for each task