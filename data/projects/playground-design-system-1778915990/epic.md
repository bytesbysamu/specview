# 🎯 Epic: Playground — Design System Extension

## Business Value

The live playground at `/playground` currently functions as a component demo reel — it shows working V2 components with mock data but offers zero guidance on *how* to build new ones. The design system documentation (tokens, borders, animations, state expectations) lived in a 2,304-line static HTML file that drifted from the codebase months ago. Every new component Sam builds requires reverse-engineering CSS custom properties from source instead of referencing a single live document. This costs 15–30 minutes per component session in context-switching alone.

Merging both halves into a single live playground eliminates documentation drift permanently. Design tokens render from `getComputedStyle`, animations replay from the actual `@keyframes` definitions, and the state matrix imports real components with real inputs. When a token changes, the playground reflects it immediately — no manual doc update, no stale screenshot. The payoff is compounding: every future component, every dark-mode tweak, every animation addition starts at `/playground` instead of grep.

The secondary payoff is codebase hygiene. Completing this epic deletes 3,562 lines of dead static assets — an entire frozen UI layer that currently confuses navigation and inflates the build.

## Scope

### What This Epic Covers

- **Design Token Display (Section A)** – Live color swatches, typography specimens, and spacing scale read from CSS custom properties; auto-updates on dark mode toggle
- **Border Rules Catalog (Section B)** – Every border style rendered with its actual CSS class, eliminating guesswork when styling new containers
- **Animation Gallery (Section C)** – All `@keyframes` from `styles.css` with live demos and replay controls
- **Component State Matrix (Section D)** – Every V2 component rendered in every meaningful state, side by side, as a visual integration reference
- **Interactive Expanded Panel (Section E)** – Full 2-column layout with working file navigation, reader panel, and AI toolbar — clickable, not static
- **Static File Deletion** – Remove `DesignPlaygroundComponent`, its 2,304-line HTML, and the orphaned 1,224-line CSS (3,562 lines total)

### What This Epic Does NOT Cover

- ❌ **Split-screen dark mode before/after** — Diffing UI feature, not documentation; existing toggle is sufficient
- ❌ **Spacing tokenization (`--space-*` variables)** — Prerequisite CSS refactor; document current hardcoded conventions only
- ❌ **Visual regression testing harness** — State matrix is for human eyes, not snapshot infrastructure
- ❌ **Responsive/mobile playground layout** — Playground is desktop dev tooling; Telegram is the mobile interface

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Child Component Scaffold + Sections A–C** | None | — | 2 days | High |
| 2 | **Component State Matrix (Section D)** | Task 1 | — | 2 days | High |
| 3 | **Interactive Expanded Panel (Section E)** | Task 2 | — | 2 days | High |
| 4 | **Static Asset Deletion & Cleanup** | Tasks 1–3 | — | 0.5 days | High |

**Task 1** — Decompose `live-playground.component.html` into child components (`pg-tokens`, `pg-borders`, `pg-animations`) to satisfy the 200-line file rule. Build Sections A–C inside these children. Pure CSS reads, no component dependencies.

**Task 2** — Build the state matrix as a new child component (`pg-state-matrix`). Requires all V2 components to be importable standalone with mock inputs. Covers status bar, project cards, sidebar nav, section nav, and reader panel states.

**Task 3** — Wire the full interactive expanded panel with sidebar navigation, reader content switching, and AI toolbar. Re-uses the real `ExpandedPanelComponent` with injected demo data (decision from architecture). Depends on Task 2 confirming all components render standalone.

**Task 4** — Delete `design-playground.component.ts`, `playground.html`, `landing-style.css`, and remove all imports/references from `app-v2`. Gated on visual review of Tasks 1–3.

## Success Criteria

- ✅ Color swatches display live computed values and update instantly on dark mode toggle
- ✅ Animation gallery renders all `@keyframes` with functional Replay buttons
- ✅ Component state matrix shows every V2 component in every documented state
- ✅ Expanded panel section is fully interactive — clicking files changes reader content
- ✅ All child component files remain under 200 lines
- ✅ Old static playground files deleted (3,562 lines removed)
- ✅ `ng build --configuration production` passes with zero new warnings
- ✅ No test regressions

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking