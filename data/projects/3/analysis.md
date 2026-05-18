# 🔍 App UI Mockups — Analysis

## The Problem
Specview's Angular app requires a dev server for every visual change, slowing design iteration. A static HTML mockup layer (`landing/app-overview.html`) was built to validate design decisions using the existing `style.css` design system. The mockup is done — it now needs to transfer decisions to the Angular app without dragging in unresolved contradictions.

## Hard Constraints
- Mockup is pure HTML/CSS — no JS interactions beyond theme toggle
- All design tokens must live in or be promoted to `landing/style.css`
- Angular implementation goes through the spec pipeline, not direct edits
- Solo dev — no parallel design + implementation tracks

## Open Questions
- **Nav icons**: text-only (A) vs inline SVG (B) were both mocked but never picked — which ships?
- **Status strip vs status bar**: ✅ RESOLVED — unified as `.gen-status-bar` with playground 5.7 colors (idle/active/success/failure). One element, one class prefix.
- **Progress bar inside cards**: ✅ RESOLVED — global status bar only, not in-card. Single-threaded chain adapter means one generation at a time.
- **Badge data source**: ✅ RESOLVED — client-side derived from existing data. State-colored (red=NEW, green=COMPLETE, blue=READY), neutral grey for counts.
- **Port**: ✅ RESOLVED — 8097 for local dev (`python3 -m http.server 8097` in `landing/`). 8096 is the Docker landing container which requires a rebuild.

## Dependencies & Sequencing
- Inline `<style>` rules must be promoted to `style.css` BEFORE Angular work begins — Angular imports `style.css`, not the mockup
- Hero grid (`2fr 1fr 1fr`) needs a CSS fallback for 0–1 Active projects — template logic depends on this being designed first
- `Source Serif 4` must be added to `web-ng/index.html` Google Fonts import before teaser font change works
- Badge system requires either a backend status field or purely client-side derivation logic — decide before Task 5

## Explicitly Out of Scope
- **Page 2 (app-reader.html)** — not started, separate epic when overview ships — re-scope when overview design is in Angular
- **The 8-task Angular implementation plan** — this is an implementation guide, not a mockup concern. Eject it into its own braindump and run through the spec pipeline as stated in the doc's own conclusion
- **Masonry layout (Direction 5)** — browser support insufficient, explicitly rejected
- **Single unified grid (Direction 4)** — loses newspaper aesthetic, explicitly rejected
- **ClawBoi mood color scale** — mentioned as adaptable for "project health" but no concrete use case exists. Don't port speculatively — re-scope if a health metric materializes