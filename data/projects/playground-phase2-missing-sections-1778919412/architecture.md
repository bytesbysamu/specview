Now I have enough context about the project conventions, structure, and constraints. Let me produce the Solution Architecture document.

# 🏗️ Solution Architecture: Playground Phase 2 — Missing Sections

## Architecture Overview

The playground is a development-only reference surface — a living catalog of every visual element in spec-doc. Phase 1 proved the child-component decomposition pattern works: each thematic section is an independent Angular component imported into the parent `live-playground` shell. Phase 2 extends this same pattern with three new child components (`pg-components`, `pg-landing`, `pg-interactions`) and one extension to the existing `pg-state-matrix`.

The central architectural challenge is not the component structure — that pattern is established — but **CSS isolation for cross-origin styles**. The app components live under the global `styles.css` loaded by Angular, but the landing-page components (pull quote, step section) are styled by a separate `landing/style.css` that exists outside the Angular build pipeline entirely. The playground must render both worlds accurately without either one polluting the other or the rest of the application.

The secondary challenge is the **200-line file budget**. Eight app-level demos in a single child component would blow past any reasonable template length. The architecture must split responsibility so that each `.html`, `.ts`, and `.scss` file remains independently readable at a glance — a constraint that forces grouping decisions early rather than at implementation time.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | Each child component renders static HTML demos directly. No shared "demo-card wrapper" component, no generic "component renderer" service. Three similar demo sections with similar markup is better than a premature abstraction that adds indirection for the one consumer (the playground itself). |
| P7 — File Size & Structure | Every new file targets under 200 lines. This is the forcing function for the three-component split rather than a monolithic "all remaining sections" component. The split is by CSS domain (app vs. landing vs. interaction states), not by arbitrary line count chunking. |
| Angular Conventions — No Inline Styles | Interaction state demos need to show hover/focus states statically. Rather than violating the "no inline styles" rule, the architecture uses class-forced state rendering — applying state classes directly in the template (`.op-chip.active`, `.context-card--hover-demo`) with companion CSS that mirrors the hover rule. This keeps the no-inline-styles contract intact while achieving the visual goal. |
| Angular Conventions — Component Encapsulation | Default `ViewEncapsulation.Emulated` for all three components. Landing CSS is brought into scope via the component's own SCSS file, not via global injection. The encapsulation boundary prevents landing styles from affecting anything outside `pg-landing`. |

## Component Design

### pg-components (App Component Demos)

**Purpose**: Renders all eight app-level visual elements that exist in `styles.css` but were absent from Phase 1's scope. These elements (masthead, op chips, modal, update banner, context cards, search bar, overline/badges, buttons) share a common trait: they rely exclusively on the global application stylesheet already loaded by Angular.

**Design rationale**: Grouping all eight here works because they share one CSS source and none require special isolation. The 200-line constraint is achievable because these are static HTML snapshots — no logic, no signals, no service calls. The TypeScript file is a minimal standalone component declaration. The template contains semantic sections with short repeated markup. The SCSS file holds only demo-specific layout (grid spacing between demo blocks, section headers) since the actual component styles come from the global sheet.

**Boundary**: This component has no inputs, no outputs, no injected services. It is a pure visual reference. It reads from global CSS by inheriting the application's stylesheet — no explicit imports needed.

### pg-landing (Landing Page Demos)

**Purpose**: Renders pull quote and step section demos using CSS that normally lives outside the Angular build pipeline in `landing/style.css`.

**Design rationale**: The landing page is a static nginx-served HTML file with its own stylesheet. The Angular app never loads `landing/style.css` — and it must not, because landing class names (`.btn-primary`, `.btn-secondary`) would collide with app-level classes that share the same names but different rules. Isolating landing demos into their own component with a dedicated SCSS file that contains only the relevant landing CSS rules (approximately 70 lines covering pull quotes and step sections) solves the collision problem through Angular's emulated encapsulation. The scoped attribute selectors Angular generates ensure these rules cannot leak.

**CSS sourcing strategy**: The relevant rules are extracted from `landing/style.css` into `pg-landing.component.scss` as a one-time snapshot. This is intentional duplication — the playground is a reference tool that documents what exists today, not a live binding that auto-updates. When the landing page CSS changes (rarely — it is a static marketing page), the playground demo is updated in the same PR. This is preferable to the alternatives: importing the full landing stylesheet globally (specificity nightmares) or using `ViewEncapsulation.None` (style leakage across the app).

**Boundary**: Same as pg-components — no inputs, no outputs, no services. Pure visual reference with self-contained CSS.

### pg-interactions (Interaction State Demos)

**Purpose**: Shows default versus hover/active/focus states side-by-side for all interactive elements, without requiring the user to physically hover over anything.

**Design rationale**: The fundamental challenge is rendering a "hover state" in a static document. The standard approach — inline `style` attributes — violates the project's template conventions. Instead, each interactive element is rendered twice: once in default state, once with a forced-state CSS class applied. The component's SCSS defines classes like `.force-hover` that duplicate the hover rule from `styles.css` but as a regular class selector. This means `op-chip.force-hover` contains the same declarations as `.op-chip:hover` — a conscious duplication that keeps templates clean and the visual output accurate.

**Layout model**: A two-column comparison table. Left column renders each element in default state. Right column renders the identical element with the forced-state class. Section headers identify the element being demonstrated. This is the simplest layout that communicates the information — no tabs, no toggles, no JavaScript interaction.

**Boundary**: No inputs/outputs. The SCSS file is the largest of the three components (~120–150 lines) because it must duplicate hover rules for ten interactive elements. This stays within budget but is the tightest constraint; if it drifts past 200 lines in implementation, the resolution is splitting into two sub-sections (navigation elements vs. action elements), not compressing the CSS.

### pg-state-matrix Extension (App vs. Landing Comparison)

**Purpose**: Adds two reference tables to the existing state matrix section — one comparing app layout patterns against landing layout patterns, and one documenting the ClawBoi-to-Specview design heritage.

**Design rationale**: These tables are documentation, not component demos. They belong in the state matrix section because they describe the system's design properties in tabular form — the same function as the existing state matrix (which shows component states). Adding them to pg-state-matrix rather than creating a new child component avoids introducing a fourth child for what amounts to two HTML tables. The existing pg-state-matrix template has room under its 200-line budget for approximately 40–50 lines of table markup.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Component framework | Angular 17 standalone components | Matches existing playground architecture; no NgModules, direct imports in the parent shell |
| Styling | Component-scoped SCSS + global styles.css inheritance | App demos inherit from global; landing demos self-contain their CSS; interaction demos define forced-state classes locally |
| State management | None (no signals needed) | These are static visual references — no user interaction, no async operations, no data fetching |
| Template syntax | `@if` / `@for` control flow | Angular 17+ convention per project rules; used minimally (e.g., `@for` to render op chip variants in a loop rather than duplicating markup eight times) |
| Encapsulation | ViewEncapsulation.Emulated (default) | Sufficient for CSS isolation between landing and app styles; ShadowDom unnecessary for this use case |
| Build verification | `ng build --configuration production` | Non-negotiable quality gate per P7 |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Three child components split by CSS domain, not by line count | The natural boundary is where the stylesheet source changes: app components (global CSS), landing components (isolated landing CSS), interaction states (duplicated hover rules). This produces meaningful cohesion within each component rather than arbitrary chunking. | If future phases add more landing elements, pg-landing grows; but currently two demos fit comfortably under budget. |
| Landing CSS extracted as a snapshot, not dynamically imported | The playground documents a point-in-time state of the design system. A snapshot in the component's SCSS is honest about what it is — a reference, not a live binding. Dynamic import would add complexity (build-time path resolution, potential caching issues) for zero practical benefit given the landing page's low change frequency. | Manual sync required when landing CSS changes. Mitigated by the fact that landing page changes are rare and always deliberate. |
| Forced-state classes instead of inline styles for hover demos | Maintains the project's no-inline-styles convention. Keeps templates declarative and readable. The forced-state classes are co-located in the component SCSS where they can be reviewed alongside the originals. | Duplicates hover rule declarations — each hover rule exists in both `styles.css` (as `:hover`) and `pg-interactions.component.scss` (as `.force-hover`). Approximately 40 lines of duplication. Acceptable because the playground is a consumer of the design system, not part of it. |
| Modal rendered inline (not as overlay) | The playground is a scrollable reference document. Rendering a modal as an overlay would obscure other content and require dismiss logic — defeating the purpose of a static visual catalog. Inline rendering with `position: static` override shows the modal's visual design without its behavioral complexity. | Does not demonstrate the backdrop dimming effect. Acceptable — the playground shows appearance, not interaction behavior (per epic scope). |
| No shared "demo section" wrapper component | Three components each rendering 2–8 demos could share a wrapper for consistent section headers, spacing, and borders. But this is the one-consumer case — only the playground uses these demos. A shared wrapper adds a file, an import, input bindings, and content projection for saving approximately 3–4 repeated lines of heading markup per section. Not worth the abstraction. | If Phase 3 adds more demo sections, this decision may be revisited. For now, P4 (no speculative abstractions) governs. |
| Extend pg-state-matrix rather than create pg-comparison | The comparison tables are tabular documentation about design properties — the same conceptual category as the existing state matrix content. A fourth child component for two HTML tables would over-fragment the playground's structure and add import/declaration overhead that exceeds the content itself. | pg-state-matrix's template grows by ~45 lines. Must be monitored against the 200-line ceiling but currently has headroom from Phase 1. |

## CSS Isolation Strategy

The playground renders elements from three distinct CSS domains in a single scrollable page. The isolation strategy prevents cross-contamination:

**Domain 1 — App components** (pg-components): No isolation needed. These elements are styled by `styles.css` which is globally available in the Angular app. The playground inherits all app styles naturally because it runs inside the app shell.

**Domain 2 — Landing components** (pg-landing): Full component-level isolation via Angular's emulated encapsulation. The relevant landing CSS rules (~70 lines covering `.pullquote-*`, `.steps`, `.step`, `.step-num`, `.step-title`, `.step-body`, `.step-code`) are extracted into `pg-landing.component.scss`. Angular's compiler adds scoping attributes that prevent these rules from affecting any element outside the pg-landing component boundary.

**Domain 3 — Forced interaction states** (pg-interactions): Companion classes (`.force-hover`, `.force-focus`, `.force-active`) defined in `pg-interactions.component.scss` that replicate the visual effect of pseudo-class states. These are scoped to the component and cannot conflict with real hover behavior elsewhere.

**Collision avoidance**: The key risk is `.btn-primary` and `.btn-secondary` which exist in both `styles.css` and `landing/style.css` with different rules. Because pg-landing's SCSS is encapsulated, its `.btn-primary` rules only apply within that component's template. The buttons demo in pg-components uses the global app `.btn-primary` naturally. No conflict occurs.

## Integration Approach

The parent `live-playground` component imports the three new standalone components and renders them as additional sections in its template. No routing changes — the playground remains a single scrollable page. Section ordering follows the old static playground's sequence for familiarity: app components first, landing components second, interaction states third, with the extended state matrix in its existing position.

The old static playground file is deleted only after all success criteria are verified via visual inspection and a passing production build. This is the final step of Task 5, not a concurrent activity.

## 200-Line Feasibility Assessment

| File | Estimated Lines | Risk |
|------|----------------|------|
| pg-components.component.ts | ~15 | None — minimal decorator + class |
| pg-components.component.html | ~160 | Moderate — eight demo sections with markup. Mitigated by using `@for` loops for repeated elements (op chips, buttons) rather than manual repetition |
| pg-components.component.scss | ~40 | None — only layout/spacing for demo sections; actual component CSS is global |
| pg-landing.component.ts | ~15 | None |
| pg-landing.component.html | ~60 | None — only two demos |
| pg-landing.component.scss | ~80 | None — extracted landing CSS for pull quotes + steps |
| pg-interactions.component.ts | ~15 | None |
| pg-interactions.component.html | ~130 | Moderate — ten elements × two states. Mitigated by consistent table row pattern |
| pg-interactions.component.scss | ~140 | Moderate — must duplicate ten hover rules. If exceeded, split into pg-interactions-nav and pg-interactions-actions |
| pg-state-matrix extension | ~45 added | Low — existing template has headroom |

The tightest files are `pg-components.component.html` and `pg-interactions.component.scss`. Both have escape valves defined in advance: for the template, convert repeated button/chip markup into `@for` loops over a typed array; for the SCSS, split into two interaction sub-components along a natural domain boundary (navigation elements vs. action elements).

## Related Documents

- [Analysis](./analysis.md) — Problems driving design; verified inventory source
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking and completion dates