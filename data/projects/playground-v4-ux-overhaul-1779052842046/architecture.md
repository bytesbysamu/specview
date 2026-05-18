# 🏗️ Solution Architecture: Playground V4 — UX Overhaul

## Architecture Overview

Playground V4 restructures the existing scroll shell from a component showcase into a narrative conversion tool. The central architectural insight is that the playground's five-section structure is sound, but three of those sections currently render static demonstrations where they should render *transformations* — content visibly changing state in response to user interaction or scroll position. The architecture treats each section as a self-contained narrative beat with a single responsibility: make the visitor *feel* a specific moment in the braindump-to-spec journey.

The system remains entirely frontend. No new API endpoints, no new services, no HTTP calls in DEMO_MODE. All data already exists in `playground-demo-data.ts` — the architecture challenge is state orchestration between components that must share awareness of which project is selected, which pipeline stage is active, and whether the user is in grid or detail mode. Angular signals provide this coordination without introducing a state management library.

The key structural change is elevating the live app section from "embedded app preview" to "faithful product mirror." This means the playground's Main Course section must implement the same grid-OR-detail mutual exclusion that `app-v2.component.ts` uses in production. The section doesn't wrap the real app — it replicates the interaction model with demo data, ensuring the visitor's muscle memory transfers directly when they sign up.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | Each section is a standalone component with its own signal state. No shared "playground state service" — sections communicate only through the scroll shell's signal inputs where strictly necessary. |
| P7 — File Size & Structure | New components (before-after, pipeline progression) live as flat files in `src/app/`. Each stays under 200 lines by delegating content rendering to existing components like `reader-panel`. |
| Narrative-First UX | Every section answers one question for the visitor. Greeting: "What is this?" Kitchen: "How does it work?" Main Course: "Can I use it?" Presentation: "Is it well-made?" Send-Off: "What do I do next?" |
| Mirror Over Mock | The demo replicates real app interaction patterns exactly. If production uses mutual exclusion, the demo uses mutual exclusion. If production uses horizontal section nav, the demo uses horizontal section nav. |
| Passive Revelation | Content appears through CSS transitions triggered by scroll position. No JavaScript gating, no locked states, no blank sections. The narrative pull does the pacing work — animation just adds polish. |

## Component Design

### Grid-OR-Detail View Controller (Main Course Section)

**Purpose**: Replaces the current stacked layout where grid and detail panel render simultaneously. Implements the same mutually exclusive view states that `app-v2.component.ts` uses in production.

**Behavior model**: A single signal (`activeView: 'grid' | 'detail'`) determines which DOM subtree renders. When `activeView` is `'detail'`, the grid is removed from the DOM entirely (not hidden via CSS — removed, matching production). Clicking a project card transitions to detail. A close action transitions back to grid. Default state on section entry: detail view with Payment Gateway Redesign's analysis open, because this shows the richest content immediately and demonstrates the reader experience without requiring a click.

**Composition**: The detail state renders a horizontal section nav (tabs for braindump, analysis, epic, architecture) above the reader panel content area. This matches the production layout where section nav spans the full content width rather than sitting in a sidebar column.

**Mini-masthead**: A thin branded header ("Specview") sits above the grid/detail area, framing the embedded experience as the actual product rather than an anonymous component demo. This is a static element — purely presentational, no logic.

### Before/After Transformation Section

**Purpose**: Provides the emotional "aha" moment that Groad achieves with its problem→result pattern. Shows identical content in two visual states — raw braindump text and structured spec output — so the visitor sees the transformation without needing to interact.

**Placement**: Between the Greeting (hero) and Kitchen (pipeline). This is the "pain" beat — the visitor recognizes their own messy thinking in the braindump column, then sees what it becomes.

**Layout strategy**: Two-column side-by-side on desktop. Left column renders raw braindump text from Payment Gateway Redesign's `braindump` field in demo data. Right column renders the same project's `analysis` field with full spec formatting (headings, bullet structure, section breaks). Both columns use existing typography tokens — the contrast comes from content structure, not color or decoration.

**Scroll behavior**: Both columns are visible simultaneously with no interaction required. On scroll, a subtle fade-translate-up animation reveals the right column slightly after the left, creating a temporal "before then after" feel using pure CSS transitions.

### Interactive Pipeline Progression

**Purpose**: Transforms the static four-card pipeline description into an experiential journey where the visitor watches one project evolve through all four generation stages.

**Interaction model**: Four stage tabs (Braindump → Analysis → Epic → Architecture) displayed horizontally. Clicking a tab renders that stage's content for Payment Gateway Redesign in a reader area below. The content genuinely changes — this is not a description of what happens at each stage, but the actual output for that stage rendered with production formatting.

**Data source**: `playground-demo-data.ts` already contains full content for all four stages of Payment Gateway Redesign. No new demo data required.

**Dependency on Grid-OR-Detail**: The pipeline section provides a "See it live" affordance on the final stage (Architecture) that scrolls to the Main Course section and activates detail view with the architecture tab selected. This creates narrative continuity — the visitor follows one project from raw input through the pipeline and into the actual reading experience.

**Signal design**: A local `activeStage` signal (0–3) drives tab highlighting and content rendering. No external state dependency. The component reads from demo data directly.

### Scroll Reveal System (replacing IntersectionObserver gating)

**Purpose**: Removes the JavaScript-driven section locking that causes blank sections during fast scrolling. Replaces with CSS-only reveal animations that feel like content appearing naturally.

**Mechanism**: Each section wrapper gets a CSS class that applies `opacity: 0` and `transform: translateY(20px)` by default. A single IntersectionObserver (threshold 0.1, not 0.6) adds a `revealed` class when a section enters the viewport. The `revealed` class triggers a CSS transition to full opacity and zero translate. Once revealed, sections stay visible permanently — no re-hiding on scroll-up.

**Key difference from V3**: V3's observer at 0.6 threshold with content-locking JavaScript meant sections appeared empty until substantially in view. V4's observer at 0.1 threshold with CSS-only transitions means content starts appearing the moment a section's edge enters the viewport. The observer serves only as an animation trigger, never as a content gate.

**Performance**: A single observer instance monitors all section boundaries. No per-element observers. No scroll event listeners. CSS transitions are GPU-composited (opacity + transform only).

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| State coordination | Angular signals (local per-component) | Each section manages its own state. No shared service needed because sections don't depend on each other's state — only the pipeline→detail handoff requires cross-section awareness, handled via a simple callback passed through the shell. |
| Animation | CSS transitions + single IntersectionObserver | GPU-composited, no JavaScript animation frames, no layout thrashing. Observer is the lightest possible bridge between scroll position and CSS class application. |
| Layout | Existing CSS grid tokens from `styles.css` | The newspaper design system already defines the 12-column grid, spacing scale, and typography hierarchy. No new tokens needed — the before/after section is just a two-column grid, the pipeline is tabs + content area. |
| Content rendering | Existing `reader-panel` patterns | The reader panel already handles markdown-to-formatted-HTML rendering with the newspaper aesthetic. Pipeline and detail view reuse this rendering approach rather than inventing a new content display. |
| Demo data | `playground-demo-data.ts` (existing) | All four stages of Payment Gateway Redesign are already present. The before/after section sources from the same data. Zero new content authoring required. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Default to detail view (not grid) on section entry | The detail view shows the richest content — formatted spec with section nav. Starting on grid requires a click before the visitor sees value. Groad's case study leads with the most impressive artifact, not the navigation shell. | Visitors don't immediately see that multiple projects exist. Mitigated by ensuring the "close" affordance is obvious and the grid is the first thing seen on close. |
| Single project for pipeline progression (Payment Gateway Redesign) | Following one project through four transformations creates narrative continuity. Showing four different projects at four stages breaks the "transformation" feeling — it becomes a feature list again. | Less demo data variety visible. Acceptable because the goal is demonstrating process, not breadth. |
| CSS reveal instead of JavaScript gating | Eliminates blank-section problem entirely. Fast scrollers see all content. Narrative pull does the pacing work without artificial friction. Matches Groad's continuous scroll philosophy. | Visitors could theoretically skip sections by scrolling fast. Acceptable — if someone scrolls past content, gate logic wouldn't have converted them anyway. |
| Separate Before/After section rather than integrating into pipeline | The emotional beat (seeing the transformation) is different from the educational beat (understanding the stages). Combining them dilutes both. Groad separates "here's the result" from "here's the process." | Adds one more section to the scroll. Kept short (viewport-height max) to avoid bloat. |
| Remove grid+detail stacking in favor of mutual exclusion | Direct mirror of production behavior. Stacking creates a layout that exists nowhere in the real app, which undermines the implicit promise that "what you see here is what you get." | The demo shows less on screen at once. This is actually a benefit — it respects the hierarchy of attention that the real app enforces. |
| No journey map or landing showcase in V4 scope | Journey map requires a defined conversion funnel and pricing page that don't exist yet. Landing showcase requires a standalone landing page to show. Both are dependencies that would block shipping. | The narrative arc is incomplete — "iterate → upgrade → share" goes untold. Acceptable for V4; the Send-Off CTA still provides conversion affordance. |
| Horizontal section nav (not sidebar) in detail view | Production uses horizontal tabs for section navigation. The playground previously placed this in a side column, creating a layout the user would never encounter in the real app. Consistency builds trust. | Less vertical space for content. Mitigated by the nav being a single-line tab bar with minimal height. |

## Data Flow

The playground operates entirely on static demo data with no API interaction. Data flows in one direction: `playground-demo-data.ts` → section components → rendered DOM.

The scroll shell component acts as the orchestration boundary. It instantiates each section as a child component and passes demo data as signal inputs. Sections never fetch their own data and never reach into sibling component state.

The one cross-section interaction (pipeline "See it live" → Main Course detail view) flows upward through an output event to the shell, which then sets an input signal on the Main Course section. This preserves unidirectional data flow — no child-to-child communication, no shared mutable state.

## Performance Constraints

The sub-2s page load requirement is maintained by design: all content is statically compiled into the bundle, no HTTP calls fire in DEMO_MODE, and the IntersectionObserver does no work until scroll begins. The total demo data for Payment Gateway Redesign (all four stages) is approximately 8KB of text — negligible impact on bundle size.

CSS transitions use only compositor-friendly properties (opacity, transform). No layout-triggering properties animate. No JavaScript animation loops run. The single IntersectionObserver instance has O(n) cost where n = number of sections (5–6), which is constant and trivial.

## Boundaries and Constraints

**What this architecture does NOT introduce**: No new Angular services. No new CSS tokens. No new route definitions. No state management library. No component-scoped stylesheets (all styling uses global newspaper classes). No new demo projects. No API endpoints.

**What this architecture reuses**: The scroll shell container, the reader panel rendering approach, the section nav tab pattern, the project grid card layout, the existing demo data structure, and the full newspaper design system token set.

**File budget**: Four new component files (before-after section, pipeline progression section, refactored live-app section, updated scroll shell). Each under 200 lines. The scroll shell refactor may require splitting the current `pg-scroll-shell.component.ts` if it exceeds 200 lines after changes — in that case, section orchestration extracts into a lightweight coordinator.

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking