# 🏗️ Solution Architecture: App UI Mockups

## Architecture Overview

This epic's architectural challenge is not about building software — it is about designing a **CSS promotion pipeline** that moves validated visual decisions from a rapid-iteration scratchpad into a shared design system consumed by both static mockups and the Angular application. The core insight is that `landing/style.css` serves as the single source of truth for all visual tokens, and the mockup's inline `<style>` block is a staging area, not a permanent home.

The system has three layers: the **design token layer** (CSS custom properties already in `style.css`), the **component layer** (class-based rules for reusable elements), and the **page composition layer** (how components combine into layouts). Tasks 1 and 2 resolve naming and semantic conflicts at the component layer. Task 3 performs the actual promotion — moving approximately 30 validated rules from the staging area into the shared system. Tasks 4 and 5 extend the system with new capabilities (grid fallback logic, font dependency) that the Angular implementation epic will consume.

The architectural constraint that shapes every decision: `landing/style.css` is imported by both `app-overview.html` (static mockup served by nginx) and `web-ng/src/styles.css` (Angular app). Any rule promoted to `style.css` must work in both contexts without modification. This means no Angular-specific selectors, no framework assumptions, and no JavaScript-dependent states in the promoted CSS.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | `style.css` is the adapter between design decisions and consumers. Neither the mockup nor Angular imports tokens directly — both go through this single file. |
| P4 — No Speculative Abstractions | Promote only rules validated through three mockup variants plus two audits. No generic grid system for hypothetical future pages. |
| P5 — OpenAPI-First (contract-first) | `style.css` is the contract. The mockup proves a rule works; promotion makes it official. Angular implements against the contract. |
| P7 — File Size & Structure | After promotion, zero app-specific rules remain inline in `app-overview.html`. One file owns each concern. |
| State not Category | Color communicates current operational state (running, success, failure, idle) — never section taxonomy. Category is communicated by position and grouping. |
| Earned Color | Neutral by default. Color appears only when something demands attention — a badge uses red only for "NEW", green only for "COMPLETE". Count badges stay grey. |

## Component Design

### CSS Promotion Pipeline

**Purpose**: Eliminate the inline `<style>` block in `app-overview.html` by moving every validated rule into `style.css`, ensuring visual regression-free transfer.

The promotion follows a dependency order: naming decisions (Task 2) must land before class names are finalized, design question resolutions (Task 1) must land before ambiguous rules can be promoted. The pipeline is: resolve ambiguity → name elements → promote rules → verify visual parity.

Rules group into six promotion batches, each independently testable by browser refresh: header family, status element, section group family, data-section attribute selectors with custom property, hero grid family, and animation keyframes. Promoting in batches allows visual regression checks at each step rather than one large all-or-nothing transfer.

### Unified Status Element

**Purpose**: Collapse "action status strip" and "status bar" into one named element with one CSS class prefix and one DOM placement.

The brain dump introduces two overlapping concepts: an "action status strip" (below nav, showing generation step + project name) and a "status bar" (playground 5.7 colors with idle/active/success/failure states). The mockup already unifies these visually — it is one element below the nav with playground 5.7 color semantics. The architecture decision is to canonicalize on a single name and class prefix that both the mockup and Angular app use identically.

The chosen name is **generation status bar** with class prefix `.gen-status-bar`. Rationale: "generation" scopes it to its actual purpose (showing spec generation state), "status bar" matches the playground's existing class naming (section 5.7), and the prefix `.gen-status-bar` already exists in `style.css` with `--active` and `--idle` modifiers. The "action status strip" name and `.action-status-strip` class are retired — all references in the promoted CSS use `.gen-status-bar` exclusively.

Placement is fixed: below the nav bar, above the search bar, full viewport width. Height is content-driven with a 32px minimum when visible. When idle, the element uses the dark green idle background — it does not hide or collapse, maintaining layout stability.

### Hero Grid with Fallback

**Purpose**: Design CSS-level degradation for the `2fr 1fr 1fr` hero layout when Active section has fewer than two items.

The hero grid works well with 2–3 items but requires explicit fallback behavior for edge cases. This is a CSS-only decision — the Angular template will apply conditional classes, but the visual behavior must be defined at the stylesheet level.

Three-item case: standard `2fr 1fr 1fr` with 24px gap. Two-item case: same grid, third column simply empty (no grey fill since background is transparent). One-item case: single item spans full width using `grid-column: 1 / -1` — the hero card fills the entire hero region at its natural height. Zero-item case: the hero section hides entirely via a utility class that Angular applies conditionally.

The fallback does not require media queries or container queries — it is purely item-count driven. The CSS defines the grid and the span rule; the template logic decides which class to apply based on item count.

### Section Group System

**Purpose**: Provide consistent taxonomy grouping with semantic color reserved for headers only.

Each section (Active, Specced, Braindumps, Ready to Build, Archive) renders as a `.section-group` containing a header and a cards container. The header carries the section's semantic color on its title text and a 2px ink underline spanning only the title width (inline-block trick from ClawBoi). Cards within the group carry no category color — their left borders are removed per the "state not category" color philosophy.

The `[data-section]` attribute selector pattern sets a `--section-accent` custom property per section, consumed only by the section header title color. Cards read state from a separate `[data-state]` attribute if they have active generation or completion status.

### Font Dependency Chain

**Purpose**: Ensure Source Serif 4 loads in both mockup and Angular app contexts.

The mockup already loads Source Serif 4 via its own Google Fonts link tag. The Angular app (`web-ng/index.html`) loads Playfair Display and Source Sans 3 but not Source Serif 4. The fix is additive: append `Source+Serif+4:ital,wght@0,400;0,600;1,400` to the existing Google Fonts URL in `web-ng/index.html`. Both files end up loading the same three-font family set, ensuring the promoted `.file-item-teaser` rule renders identically in both contexts.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Design system | Pure CSS custom properties + class-based components | No preprocessor needed — tokens in `:root`, components as classes, dark mode via `[data-theme]` attribute. Consumed identically by static HTML and Angular. |
| Mockup serving | `python3 -m http.server 8097` on host (dev), nginx:alpine on port 8096 (Docker) | Host server for instant iteration; Docker container for deployment verification. |
| Font hosting | Google Fonts CDN | Already in use for Playfair Display and Source Sans 3. Adding Source Serif 4 to the same import chain — no new dependency. |
| Grid layout | CSS Grid with `auto-fill` + explicit `2fr 1fr 1fr` hero | Native browser support, no polyfill. Hero grid for Active section only; standard auto-fill for all others. |
| Visual regression | Manual browser refresh comparison | Appropriate for solo developer with one viewport target (1400px). No automated visual testing overhead for a design scratchpad. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Nav icons: text-only** | At 12px, inline SVGs add visual noise without improving scan speed. The text labels are already short and distinctive. Mockup Variant A reads cleaner than Variant B at normal viewing distance. | Lose quick recognition for users who scan by icon shape. Acceptable because tab count is small (6 items) and labels are single words. |
| **Status bar idle: visible with dark green background** | Hiding the element on idle causes layout shift when generation starts. Showing "connected" in muted ink adds a lie (the bar does not actually indicate connection state). The playground's section 5.7 uses a persistent dark green idle state — follow the established pattern. | Costs 32px of vertical space permanently. Acceptable because it communicates system readiness and prevents jank. |
| **Hero card progress: global status bar only, not in-card** | Putting a progress indicator inside the Active hero card creates a redundant signal — the global status bar already shows generation state with the project name. In-card progress also breaks the clean card layout and requires per-card polling logic. | Lose at-a-glance progress when multiple projects generate simultaneously. Acceptable because the current system generates one project at a time (single-threaded chain adapter). |
| **Badges: state-colored, not category-colored** | The playground color audit proved that the established design system uses color for state (running/done/error) and neutral grey for informational counts. Category-colored badges (green for Active, blue for Specced) would contradict this philosophy and create visual clutter. | Lose instant category identification at the card level. Acceptable because section grouping already communicates category — the badge adds new information (state), not redundant information (category). |
| **Dev port: 8097 (host), 8096 (Docker)** | Local dev uses `python3 -m http.server 8097` in `landing/` for instant iteration without Docker rebuild. Docker landing container serves on 8096 but requires a rebuild to pick up changes. Both are valid — 8097 is the fast iteration path. | Two ports to remember. Acceptable because Docker is for deployment verification, not design iteration. |
| **Class prefix: `.gen-status-bar`** | Unifies "action status strip" and "status bar" under one name matching the existing playground class. Avoids a breaking rename since `.gen-status-bar` already exists in `style.css`. | "Generation" in the name limits future reuse for non-generation status. Acceptable per P4 — build for the one concrete case that exists now. |
| **Hero fallback: span full width at 1 item, hide at 0** | Single item stretched across `2fr 1fr 1fr` looks orphaned in column one. Full-width span gives it hero prominence appropriate to being the only active project. Zero items hiding the section entirely prevents an empty hero region with no content. | Lose the three-column visual rhythm with a single item. Acceptable because a single active project deserves maximum visual weight, not a cramped quarter of the viewport. |
| **Promotion target: `landing/style.css` not `web-ng/src/styles.css`** | The landing stylesheet is the shared contract. Angular imports from it (or can import from it). Promoting to the Angular-specific stylesheet would strand the mockup with inline rules forever. One source of truth, two consumers. | Angular-specific overrides still live in `web-ng/src/styles.css`. Acceptable because overrides are rare — the design system should serve both contexts without modification. |

## Integration Points

The outputs of this epic feed directly into the Angular implementation epic (separate braindump, separate spec pipeline run). The contract between this epic and that one consists of three artifacts:

**First**: `landing/style.css` with all promoted rules — the Angular app imports these classes and they work without modification. Class names, custom property names, and selector patterns are the API surface.

**Second**: the five resolved design questions documented in this architecture — the Angular implementation consumes these decisions without re-litigating them.

**Third**: the hero grid fallback CSS — the Angular template applies conditional classes (`.hero-grid--single`, `.hero-grid--empty`) that activate the fallback layouts defined purely in CSS.

## Risk Mitigation

The primary risk is visual regression during CSS promotion — moving 30 rules from inline to external stylesheet could subtly change specificity or cascade order. Mitigation: promote in six independent batches, verify each batch with a browser refresh at 1400px viewport before proceeding to the next. If any batch breaks, it can be reverted independently.

The secondary risk is naming collision — `.section-group` and `.gen-status-bar` classes already exist in `style.css` with slightly different definitions than the mockup's inline versions. Mitigation: Task 2's naming reconciliation explicitly identifies every collision and defines the canonical definition before Task 3 begins promotion.

## Related Documents

- [Analysis](./analysis.md) — Open questions and dependency sequencing driving this epic
- [Epic](./epic.md) — Scope, tasks, and success criteria for the mockup layer
- [Timeline](./timeline.md) — Task status and sequencing