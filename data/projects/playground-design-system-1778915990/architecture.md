The project files aren't accessible in this environment, but I have comprehensive context from the epic, braindump, codebase context, and principles documents. That's sufficient to write the architecture — this is a pure frontend decomposition with no backend changes. Let me produce the document.

# 🏗️ Solution Architecture: Playground — Design System Extension

## Architecture Overview

The live playground at `/playground` today is a component demo reel — it renders V2 components with mock data but says nothing about the design system underneath them. The design system documentation exists only in a frozen 2,304-line static HTML file that drifts further from reality with every CSS change. This architecture merges both halves into a single live playground where tokens, borders, animations, and component states all render from the real codebase — never from hardcoded snapshots.

The key architectural insight is that Angular components can read their own styling environment at runtime. `getComputedStyle` against the document root returns the live value of any CSS custom property, and those values change instantly when the dark-mode class toggles. By building each playground section as a standalone child component that reads from the actual CSS and imports real V2 components, the documentation becomes self-maintaining. A token change in `styles.css` propagates to the playground without any manual update step.

The decomposition follows a simple parent-children pattern. The existing `LivePlaygroundComponent` becomes a thin shell — a scrollable page with section anchors — while five new child components each own one documentation domain. Every child stays under 200 lines because each has a narrow, well-bounded responsibility: read some CSS values, render some swatches or demos, done. No shared state service is needed; each child is self-contained with local reads from the DOM or direct imports of V2 components.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P4 — No Speculative Abstractions** | One CSS-read helper function, not a "design token service." Each child component imports the helper directly — no registry, no injection token, no observable stream of token changes. |
| **P7 — File Size & Structure** | The current monolithic playground template gets decomposed into five child components. Parent template drops to section anchors and `<pg-*>` tags. Each child stays under 200 lines by owning exactly one documentation domain. |
| **P7 — One Component Per File** | Each playground section is its own `.component.ts` file with an inline or co-located template. No barrel files, no shared module — standalone components imported directly. |
| **P6 — No Rules Duplicated Inline** | Design token variable names, animation keyframe names, and border class names are defined once in CSS. Playground children read from CSS at runtime rather than maintaining a parallel list of token names. Where a static list is unavoidable (e.g., the set of animations to demo), it lives in one place in the child component. |
| **Live-over-static** | Every value displayed in the playground is read from the running application — `getComputedStyle` for tokens, actual CSS classes for borders, real `@keyframes` for animations, real V2 component imports for the state matrix. Nothing is hardcoded that could drift. |

## Component Design

### Parent Shell — `LivePlaygroundComponent` (existing)

**Purpose**: Scrollable page layout with section anchors, dark-mode toggle, and child component slots.

The existing component already handles the page frame, the dark-mode toggle button, and several demo sections. The refactor strips inline section markup out of its template and replaces each block with a child component tag. The parent's only remaining responsibilities are the page-level dark-mode toggle (which applies a CSS class to the document root, triggering all children to re-read their values) and the section navigation anchors. This brings its template well under 200 lines while preserving the existing scroll structure and `.pg-section` / `.pg-label` visual pattern.

### Child: `PgTokensComponent` (new — Section A)

**Purpose**: Live color swatches, typography specimens, and spacing scale read from CSS custom properties.

This component maintains a local array of token definitions — variable name, display label, and category (color, status, typography). On initialization and on every dark-mode toggle, it calls `getComputedStyle(document.documentElement).getPropertyValue(name)` for each token and stores the computed value. The template renders color swatches as small boxes with `[style.backgroundColor]` bound to the computed value, plus the variable name and hex string beside each.

Typography specimens render actual text samples using `[style.fontFamily]` bound to the computed font-stack value, at the documented sizes. The spacing scale section displays visual box diagrams at common padding/margin values (8px through 48px) — these are hardcoded measurements documenting current conventions, not CSS custom properties, since spacing tokenization is out of scope per the epic.

Dark-mode reactivity works without any event bus: the parent toggles a class on `document.documentElement`, and this component re-reads all properties on a click handler passed down or by listening for the class change via a simple `MutationObserver` on the root element's class attribute.

### Child: `PgBordersComponent` (new — Section B)

**Purpose**: Catalog of every border style rendered with its actual CSS class applied.

Each border rule is rendered as a demo container with the real CSS class applied — `.divider`, `.divider.thick`, section-group separators, card separators, expanded-panel top borders, sidebar right borders, and column rules. The component template is a straightforward list of labeled demo boxes. Since these are pure CSS class applications with no logic, this component is mostly template with minimal TypeScript — just the component decorator and an array of border definitions for iteration.

### Child: `PgAnimationsComponent` (new — Section C)

**Purpose**: Gallery of all `@keyframes` animations with live demos and replay controls.

Each animation gets a card showing its name, timing specification, and a demo element with the animation class applied. Infinite animations display continuously with an "Always Running" label. Finite animations include a "Replay" button that triggers replay by removing the animation class, forcing a reflow (reading `offsetWidth`), and re-adding the class. This reflow-force pattern is the standard browser mechanism for restarting CSS animations without JavaScript animation APIs.

The component maintains a local array of animation definitions (name, CSS class, duration string, whether infinite). The replay method is a single component method that accepts an element reference and class name — no service extraction needed for one call site.

### Child: `PgStateMatrixComponent` (new — Section D)

**Purpose**: Every V2 component rendered in every meaningful state, side by side.

This is the most integration-heavy child. It imports the real V2 standalone components — `StatusBarComponent`, project card components, `SidebarNavComponent`, `SectionNavComponent`, and `ReaderPanelComponent` — and renders each with different input bindings to show every documented state. Each component-state combination gets a labeled cell in a grid layout.

The key architectural decision here is **real components with mock inputs, not screenshots or clones**. Each V2 component is imported directly and rendered with carefully chosen `@Input` values that trigger each visual state. This means if a component's state rendering changes, the matrix reflects it automatically. The trade-off is that this component has the most imports and the longest template — but since each grid cell is just a component tag with input bindings (no logic), the template stays descriptive rather than complex.

Mock data for each state is defined as simple object literals in the component class — not extracted to a service or JSON file, since this data has exactly one consumer (P4).

### Section E: Expanded Panel Demo (Task 3)

**Purpose**: Full interactive 2-column layout with working file navigation, reader panel, and AI toolbar.

This section reuses the real `ExpandedPanelComponent` rather than building a playground-specific replica. The playground passes a pre-built demo project data structure — a mock project with multiple files, markdown content, and simulated AI operation results — as inputs to the real component. Clicks on sidebar files change the reader content through the component's normal input/output bindings.

**Why reuse the real component instead of a demo clone**: A clone would drift from the real implementation — exactly the problem the old static playground had. By instantiating the real component with demo data, every visual change to the expanded panel (animations, layout, toolbar positioning) appears in the playground automatically. The trade-off is tighter coupling: if the real component's input contract changes, the playground demo breaks at compile time. This is a feature, not a bug — it forces the playground to stay current.

The demo data includes enough variety to exercise: panel slide animation on enter, word count in the meta line, overline file-type labels, AI result toolbar in floating position (Apply/Copy/Dismiss), and at least one file per type (spec, braindump, AI result). This data lives in a local constant within the component file.

### Dark-Mode Toggle (existing — enhanced)

The current dark-mode toggle in the parent shell already works. Per the epic scope, no split-screen before/after comparison is added — the existing toggle is sufficient for verifying dark-mode behavior across all sections. The live token table in `PgTokensComponent` provides the "before/after" visibility: toggle dark mode and watch every computed hex value update in real time.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Components | Angular standalone components (signals) | Matches existing V2 component architecture; no module declarations needed; each child is self-contained |
| CSS token reads | `getComputedStyle` on `document.documentElement` | Browser-native, zero dependencies, returns live values that respect dark-mode class |
| Dark-mode reactivity | `MutationObserver` on root element class | Decouples children from parent's toggle mechanism; no event bus or shared service needed |
| Animation replay | Class removal + `offsetWidth` reflow + class re-add | Standard browser pattern; no animation library dependency |
| State matrix data | Inline object literals per component | One consumer, no extraction warranted (P4); compile-time type safety via component input types |
| Backend | None | Entire epic is frontend-only; no API changes, no new endpoints |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Five child components, not six sections in one template** | The 200-line file rule (P7) makes a monolithic template unviable. Five children map cleanly to the five documentation domains (tokens, borders, animations, state matrix, interactive panel). Each has a single responsibility and no cross-child state. | More files in the components directory; marginally more import statements in the parent. Acceptable for a playground that is itself a development tool, not a user-facing feature. |
| **`getComputedStyle` reads, not a token map constant** | A hardcoded map of `{ name: '--ink', value: '#121212' }` drifts the moment someone changes a CSS variable. Reading live values means the playground is always correct. | Reads happen at component init and on dark-mode toggle — not on every change detection cycle. Negligible performance cost for a dev-only page. Requires a small list of variable names to iterate, which is the one static piece. |
| **Real `ExpandedPanelComponent` reuse, not a playground replica** | A demo clone of the expanded panel would reproduce the exact drift problem this epic solves. Using the real component with injected demo data guarantees visual fidelity. | The playground section depends on the real component's input contract. If inputs change, the playground breaks at compile time. This is intentional — it forces synchronization. |
| **Inline mock data, not a shared fixtures file** | Each child component defines its own demo data. The state matrix has one set of mock inputs; the expanded panel demo has another. No two children share data. Extracting to a shared file would create an abstraction with multiple unrelated consumers (violates P4). | If a component's input shape changes, mock data in two places (state matrix and expanded panel) might need updating. Acceptable — both are in playground children, and the compiler catches mismatches. |
| **Descope Section F split-screen dark mode** | The epic explicitly excludes this. The existing toggle plus the live token value display in Section A provides equivalent verification capability without the additional layout complexity. | No side-by-side comparison view. Developers toggle and observe, which is how dark-mode testing actually works in practice. |
| **MutationObserver for dark-mode reactivity, not an Angular service** | A shared `DarkModeService` with an observable would be a speculative abstraction (P4) — the only consumers are playground children, and they all need the same thing: "re-read CSS vars when the root class changes." A `MutationObserver` on `document.documentElement` does this with zero shared state. | Each child sets up its own observer (or the parent passes a signal down). Slightly more boilerplate than a service, but no shared mutable state and no lifecycle coordination issues. |
| **Sequential task execution, not parallel** | Tasks 1→2→3→4 are sequentially dependent. Task 2 (state matrix) needs Task 1's child component pattern established. Task 3 (interactive panel) needs Task 2 to confirm V2 components render standalone. Task 4 (deletion) is gated on visual review of all prior tasks. | No parallelism means ~6.5 days sequential. Acceptable for a solo developer where context-switching between parallel tasks has its own overhead. |
| **Deletion gated on visual review, not automated** | The old static files (3,562 lines) are only deleted after visual confirmation that all new sections render correctly. No automated equivalence check — the state matrix and token display are fundamentally different from the static HTML, so snapshot comparison would be meaningless. | Requires manual visual review before Task 4 can proceed. This is a feature: it ensures nothing is lost in translation from static to live. |

## File Impact

### New Files

| File | Purpose | Estimated Size |
|------|---------|---------------|
| `pg-tokens.component.ts` | Design token swatches, typography specimens, spacing scale | ~180 lines |
| `pg-borders.component.ts` | Border rules catalog with live CSS classes | ~80 lines |
| `pg-animations.component.ts` | Animation gallery with replay controls | ~150 lines |
| `pg-state-matrix.component.ts` | V2 component state grid with mock inputs | ~190 lines |
| `css-read.util.ts` | Single helper function for `getComputedStyle` reads | ~10 lines |

### Modified Files

| File | Change |
|------|--------|
| `live-playground.component.ts` | Import five new child components; replace inline sections with child tags |
| `live-playground.component.html` | Slim down to section anchors and `<pg-*>` child tags |

### Deleted Files (Task 4, after visual review)

| File | Lines Removed |
|------|--------------|
| `design-playground.component.ts` | 34 |
| `web-ng/public/assets/playground.html` | 2,304 |
| `web-ng/public/assets/landing-style.css` | 1,224 |
| References in `app-v2.component.html` and `app-v2.component.ts` | ~5 |

**Net line change**: ~610 lines added, ~3,562 lines deleted = **~2,952 lines net reduction**.

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| **V2 components not importable standalone** | Medium | Task 2 validates this early. If a component has hard dependencies on parent context (e.g., injected services), wrap it in a thin demo host that provides the required injection context. |
| **`getComputedStyle` returns empty string for undefined variables** | Low | The helper function returns a fallback string ("not set") for empty values. The token list in `PgTokensComponent` is curated to match actual CSS — any mismatch is immediately visible as a blank swatch. |
| **State matrix template exceeds 200 lines** | Medium | If the grid of all component states pushes past 200 lines, extract sub-grids per component type (status bar states, card states, nav states) as `@for` loops over configuration arrays rather than individual template blocks. |
| **Expanded panel demo data goes stale** | Low | Using the real component means the compiler catches input contract changes. Demo data is simple enough to update in minutes. The alternative (not demoing the panel) is worse than occasional maintenance. |

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking