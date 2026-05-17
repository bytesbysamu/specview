Now I have sufficient context. Let me write the architecture document.

# 🏗️ Solution Architecture: Playground Phase 2 — Live Demo, Landing & Goard Docs

## Architecture Overview

Phase 2 transforms the playground from a component museum into a product narrative. The core architectural insight is that the specview app components already exist and already work with demo data — the architecture problem is not "how to build a demo" but "how to compose existing production components into an editorial narrative shell without duplicating logic or creating a parallel component tree."

The solution extends `pg-case-study.component.ts` with four new section components (`pg-problem`, `pg-live-demo`, `pg-landing-showcase`, `pg-journey-v2`) and one structural upgrade to the sticky nav (acts grouping). Each new section follows the identical wrapper pattern established in Phase 1: overline → headline → deck → content slot → pullquote. The live demo section does not rebuild the app — it imports the same `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `SectionNavComponent`, and `StatusBarComponent` that the production app uses, wired to `DEMO_PROJECTS` from `playground-demo-data.ts`. The landing showcase does not iframe the static landing page — it lifts content data (output card definitions, step descriptions, stat figures) into a new `pg-landing-showcase.component.ts` that renders them as Angular components with full dark-mode and IntersectionObserver support.

The navigation challenge — scaling from 7 sections to 11 without horizontal overflow — is solved by grouping sections into four narrative acts. The nav renders act labels as top-level items with section sub-items, collapsing the horizontal footprint while adding narrative structure. This is a template-level change to `pg-case-study.component.ts`, not a new routing mechanism.

## Design Principles

| Principle | Application in Phase 2 |
|-----------|----------------------|
| P4 — No Speculative Abstractions | Each new section is a standalone component. No shared "editorial section base class" — the overline/headline/deck pattern is repeated via CSS classes, not component inheritance. Three similar templates are cheaper than a premature abstraction that constrains future sections. |
| P7 — File Size & Structure | Each new section is its own `pg-*.component.ts` file, keeping files well under 200 lines. The case study shell (`pg-case-study.component.ts`) grows only by adding imports and template references, not by absorbing section logic. |
| P1 — Adapter Boundary | No new adapters needed — Phase 2 makes zero API calls. All data flows from `playground-demo-data.ts`, which is the "adapter" for the demo context: a single module that owns all static fixture data. |
| Existing Token System | Zero new CSS custom properties. Every typographic, color, and spacing decision uses the established newspaper design system tokens from `styles.css`. New components apply existing classes — they do not define component-scoped styles. |
| Composition over Wrapping | The live demo section imports production app components directly. It does not wrap them in playground-specific shells or create "demo mode" variants. The components already accept data via inputs — the demo section simply provides demo data instead of API-fetched data. |

## Component Design

### pg-problem.component.ts — Problem Statement Section

**Purpose**: Articulate why specs matter through a Goard-inspired editorial section. This is pure content — no interactive elements, no data binding beyond static text. Three concrete pain points rendered as a numbered editorial column with pull-quote callouts between them.

**Shape**: Standalone component, `OnPush` change detection. Template uses the overline/headline/deck pattern, followed by a three-block editorial layout. Each pain-point block is a section heading + body paragraph using existing `.section-heading` and `.body-text` classes. A two-column pullquote row separates the pain points from a closing argument paragraph.

**Data**: All content is inline in the template. No external data file — this is editorial copy, not structured data. Keeping it in the template makes the content immediately readable and editable without indirection.

**Why a separate component**: The problem statement is ~80 lines of template. Inlining it into the case study shell would push that file further past the 200-line target. As a standalone component, it can be iterated independently and tested in isolation.

### pg-live-demo.component.ts — Live App Demo Section

**Purpose**: Embed the real specview app experience inside the narrative, letting visitors click through projects, browse specs, and read rendered markdown — all with demo data and zero API calls.

**Shape**: Standalone component wrapping the existing production components. Imports `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `SectionNavComponent`, and `StatusBarComponent` directly — the same components the production `app-v2.component.ts` uses. This is the critical architectural choice: reuse production components, do not rebuild them.

**State management**: Local signals mirror the production app's state shape — `selectedProject`, `selectedFile`, `activeSections`, `statusState` — but initialized from `DEMO_PROJECTS` instead of API responses. A `computed()` derives the file list from the selected project. The section nav filters projects exactly as it does in production. One project is pre-configured with `statusState: 'active'` to showcase the shimmer animation and generation-in-progress status bar state.

**Editorial wrapper**: The component's template has three zones: (1) an overline/headline/deck above the demo explaining "this is the real app running with demo data," (2) the live demo frame rendered at near-full-width with a subtle 1px border, and (3) a pullquote below reflecting on the live-component-over-screenshot philosophy.

**What it does NOT do**: It does not fork or modify the production components. It does not add "demo mode" flags to existing components. It does not create a `DemoProjectsService` — it passes data directly via inputs and signal bindings. If a production component requires a service injection that would trigger real API calls, the demo section provides the data through input bindings that bypass the service layer entirely.

**Relationship to existing LivePlaygroundComponent**: The existing `live-playground.component.ts` already proves this composition pattern works. `pg-live-demo` replaces it as the canonical live demo within the case study narrative. `LivePlaygroundComponent` can be retained but is no longer rendered in the case study shell — `pg-live-demo` subsumes its role with the added editorial framing.

### pg-landing-showcase.component.ts — Landing Page Sections as Angular Components

**Purpose**: Render the two most product-demonstrative sections from the static landing page — output deliverable cards and the 3-step "how it works" process — as interactive Angular components inside the playground narrative.

**Shape**: Single standalone component with two visual sections, each preceded by its own section heading. The component template contains both the output cards grid and the process steps layout, separated by a thin 1px border divider.

**Output cards**: A four-column grid (collapsing to two columns below 768px) showing the five spec deliverables: Analysis, Epic, Architecture, Timeline, Implementation Guide. Each card has an icon (Unicode glyph — no icon library dependency), filename, and one-sentence description. Data lives in a const array within the component file — five items do not warrant a separate data file.

**How-it-works steps**: Three numbered steps rendered at large scale (step number in 96px Playfair Display, matching the landing page's established pattern). Each step has a title, body text, and a representative content snippet (not a code block — a styled text excerpt showing braindump input, generation output, or guide structure). The step numbers use the existing `--serif` token at computed size.

**What is excluded from the landing showcase**: The comparison table, pricing section, FAQ accordion, and masthead are deliberately omitted. The epic's scope excludes pricing (no checkout flow to back it up) and comparison (belongs on the landing page, not the playground). The FAQ adds informational weight without advancing the narrative. The masthead is a branding element that would feel redundant inside a playground that already has its own hero. These exclusions keep the showcase focused on the two patterns that directly demonstrate what specview produces.

**Why rebuild instead of iframe**: The static landing page is vanilla HTML/CSS served by nginx. Iframing it inside an Angular component creates four problems: (1) the iframe cannot inherit the playground's dark-mode `data-theme` attribute, requiring postMessage coordination; (2) IntersectionObserver cannot observe elements inside a cross-origin iframe for scroll-based nav highlighting; (3) the iframe height must be manually synchronized as viewport changes; (4) the iframe loads its own CSS, doubling style weight. Rebuilding as Angular components eliminates all four problems and keeps the sections as first-class participants in the case study's scroll narrative.

### pg-journey-v2.component.ts — Enhanced Journey Map

**Purpose**: Replace the existing simple timeline with a Goard-style journey map that shows the user's workflow stages with pain-point annotations and editorial callouts at each stage.

**Shape**: Standalone component with a vertical stage-based layout. Five stages (Braindump → Generate → Review → Iterate → Ship), each rendered as a stage card with: stage number, stage name, one-paragraph description, and a pain-point annotation in a distinct visual treatment (red overline, italic text — using existing `--red` and `--serif` tokens). The annotations are honest about friction: "This is where you realize the braindump was too vague" or "This is where the architecture doc saves you from a bad database decision."

**Distinction from the pipeline visualization**: The existing pipeline section shows the AI's internal steps (the five-step generation chain). The journey map shows the human's workflow through specview. These are complementary views — one is the machine's process, the other is the user's experience. Both stay in the narrative.

**Data**: Stage definitions and pain-point annotations are inline const arrays in the component file. Five stages with five annotations — roughly 30 lines of data. No external file needed.

### pg-case-study.component.ts — Shell Modifications

**Purpose**: Extend the existing narrative shell to accommodate the four new sections and the acts-based navigation grouping.

**Changes**: The shell gains four new component imports and four new template sections slotted into the scroll container. The section ID array expands from 7 to 11 entries. The IntersectionObserver callback remains unchanged — it already observes all elements with `[id]` attributes inside the scroll container.

**Navigation acts**: The sticky nav restructures from a flat list of 11 items into four grouped acts:

- **Act 1 — The Problem** (Hero, Problem Statement, Pipeline)
- **Act 2 — The Product** (Live App Demo, Landing Showcase)
- **Act 3 — The Craft** (Design Language, Screen Gallery, Patterns, Dark Mode)
- **Act 4 — The Journey** (User Journey, CTA)

Each act is a nav group with an act label rendered at reduced size (`--sans`, 9px uppercase, `--ink-muted`) and section items nested beneath it. At viewport widths below 1024px, act labels remain visible while individual section items collapse into a dropdown or horizontal scroll within the act group — preventing the overflow the epic's success criteria require.

**Anchor link preservation**: All seven existing section IDs remain unchanged. The four new sections receive new IDs. No existing anchor link breaks.

### playground-demo-data.ts — Data Extensions

**Purpose**: Extend the existing demo data module with content needed by the new sections.

**New exports**: The file gains one new export — a demo project pre-configured with `statusState: 'active'` and partially-generated files to showcase the generation-in-progress status bar state in the live demo. The existing `DEMO_PROJECTS` array gains this ninth project. The nav sections array (`DEMO_NAV_SECTIONS`) is updated to include the four new section IDs.

**What does NOT go here**: Output card definitions, step descriptions, journey stages, and problem statement content. These are editorial content tightly coupled to their rendering components. Centralizing editorial copy in a data file creates an abstraction layer that helps nobody — the copy is only consumed by one component, and editing it requires understanding that component's template anyway. Each section component owns its own content.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Component framework | Angular 17, standalone components, signals | Matches existing playground and production app. No new framework dependencies. |
| Change detection | `ChangeDetectionStrategy.OnPush` on all new components | Playground is static content — OnPush prevents unnecessary change detection cycles and matches the pattern established by Phase 1 components. |
| Control flow | `@if` / `@for` template syntax | Angular 17 convention per project quality rules. No `*ngIf` / `*ngFor`. |
| Markdown rendering | `marked` + `DOMPurify` (existing dependencies) | The live demo's reader panel renders spec markdown. Both libraries are already in `package.json`. |
| Styling | Global CSS classes from `styles.css` using design tokens | No component-scoped CSS. All new components use the newspaper design system's existing classes. This ensures dark mode toggle applies uniformly without per-component overrides. |
| Scroll tracking | `IntersectionObserver` (existing in shell) | The case study shell already tracks active section via IntersectionObserver. New sections participate automatically by having `[id]` attributes. |
| Build verification | `ng build --configuration production` | Zero errors, zero warnings — the gating criterion from the epic. |

## Data Flow

### Demo Data Pipeline

All data in Phase 2 flows in one direction: static constants → component signals → template rendering. There is no HTTP layer, no service injection for data, and no async operations.

```
playground-demo-data.ts (DEMO_PROJECTS, DEMO_NAV_SECTIONS)
       │
       ▼
pg-case-study.component.ts (shell — passes data to children via inputs)
       │
       ├──► pg-live-demo.component.ts (receives DEMO_PROJECTS, manages local selection state)
       │        ├──► ProjectGridComponent (input: projects)
       │        ├──► SidebarV2Component (input: selected project's files)
       │        ├──► ReaderPanelComponent (input: selected file content)
       │        ├──► SectionNavComponent (input: section filters)
       │        └──► StatusBarComponent (input: status state)
       │
       ├──► pg-problem.component.ts (no external data — inline editorial content)
       ├──► pg-landing-showcase.component.ts (no external data — inline content arrays)
       └──► pg-journey-v2.component.ts (no external data — inline stage definitions)
```

### Scroll-Based Navigation Flow

The existing IntersectionObserver in the case study shell fires callbacks as sections enter and exit the viewport. The active section ID updates a signal, which the nav component reads to highlight the current act and section. New sections participate in this flow by having unique `id` attributes — no registration step required.

### Dark Mode Flow

The global `[data-theme="dark"]` attribute on `<html>` triggers CSS custom property overrides defined in `styles.css`. Because all new components use global classes and tokens (not component-scoped styles), dark mode applies automatically. The live demo section inherits dark mode through the same mechanism — the production components it imports already respond to the theme attribute.

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Import production components directly into live demo, not fork them** | Eliminates maintenance of parallel "demo" versions. When production components improve, the demo improves automatically. Avoids the "stale demo" problem where the showcase diverges from the actual product. | If a production component has a hard dependency on a service that triggers API calls (e.g., service constructor with an initial fetch), the demo section must ensure that service is either not injected or injected with a no-op provider. This coupling is the price of reuse — but it is cheaper than maintaining forks. |
| **Rebuild landing sections as Angular components, not iframe** | Dark mode compatibility, IntersectionObserver participation, single style system, no cross-frame communication overhead. The rebuild is a one-time cost; the iframe would be ongoing friction. | The landing page and playground showcase can drift apart. Content updates to `landing/index.html` do not automatically propagate to `pg-landing-showcase.component.ts`. Mitigation: the landing showcase only renders two sections (output cards and steps), limiting the drift surface. |
| **Group nav into acts instead of truncating or scrolling** | Acts provide narrative structure that a flat nav list cannot. Grouping reduces the visible item count at any viewport width. Acts also create a reading roadmap — visitors understand the story arc before scrolling. | Act labels consume vertical or horizontal space that section labels previously owned. The nav becomes two-level instead of one-level, adding visual complexity. Mitigation: act labels are visually minimal (9px uppercase, muted color) — they organize without competing. |
| **Inline editorial content in component templates, not in a shared data file** | Each editorial section's content is consumed by exactly one component. Extracting it to a shared file adds indirection without reuse — violates P4 (no speculative abstractions). The component template IS the content's natural home. | If a future feature needs to reference editorial content programmatically (e.g., search across sections), it would need to parse templates. This is unlikely for a playground — and if it happens, extraction is a simple refactor. |
| **Retain the existing pipeline section alongside the new journey map** | The pipeline shows the AI's process; the journey shows the human's experience. These are complementary perspectives, not redundant ones. Removing the pipeline would lose the technical credibility the playground currently establishes. | Two "process" sections risks narrative repetition. Mitigation: placing them in different acts (pipeline in Act 1, journey in Act 4) creates distance. The pipeline is about the machine; the journey is about the user. The editorial framing makes the distinction clear. |
| **One demo project pre-set to "active" generation state** | The status bar's shimmer animation and generation-in-progress state are key product differentiators. Showing them requires a project in active state. A pre-configured project avoids building a fake generation timer. | The "active" project's status never resolves — it is permanently generating. This is honest (the playground has no backend to complete the generation) but could confuse visitors who expect it to finish. Mitigation: a subtle annotation below the status bar: "Demo — generation simulation." |
| **No new CSS custom properties** | The existing token system covers all typographic, color, and spacing needs. Adding tokens for Phase 2 would imply the design system is incomplete — it is not. New components should prove the system's expressiveness by composing existing tokens. | Some visual treatments (e.g., pain-point annotation styling) require combining multiple tokens in specific ways. Without a dedicated token, the combination must be repeated in each place it appears. At Phase 2's scale (one journey map component), repetition is cheaper than a new token. |
| **pg-live-demo replaces LivePlaygroundComponent's role in the shell** | The existing `LivePlaygroundComponent` was a Phase 1 proof-of-concept. `pg-live-demo` subsumes it with editorial framing. Keeping both in the shell would show the same demo twice. | `LivePlaygroundComponent` is still importable and useful for standalone testing or if the `/playground` route ever needs a stripped-down demo mode. Retaining the file costs nothing; it is simply no longer rendered in the case study shell. |

## Section Ordering Rationale

The 11-section sequence follows a deliberate narrative arc borrowed from the Goard case study pattern:

1. **Hero** — Hook. Establish what specview is in five seconds.
2. **Problem Statement** — Context. Why does this product need to exist?
3. **Pipeline** — Mechanism. How does the AI actually work?
4. **Live App Demo** — Proof. Experience it yourself, right now.
5. **Landing Showcase** — Promise. What exactly do you get?
6. **Design Language** — Craft. The visual system behind the product.
7. **Screen Gallery** — Detail. Every component up close.
8. **Patterns** — System. How pieces compose into wholes.
9. **Dark Mode** — Polish. A detail that signals engineering quality.
10. **User Journey** — Empathy. Your experience, stage by stage, with honest friction points.
11. **CTA / Closing** — Action. What to do next.

The sequence moves from "what is it?" → "why does it exist?" → "how does it work?" → "try it" → "what ships" → "how it's built" → "your experience" → "go." This is a sales narrative disguised as a case study, which is exactly what a solo-founder product with no marketing budget needs.

## Integration Points

### Production Component Compatibility

The five production components (`ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `SectionNavComponent`, `StatusBarComponent`) must be importable into `pg-live-demo` without triggering side effects. If any component's constructor or `ngOnInit` calls a service that makes HTTP requests, the demo section must provide that service with a no-op implementation via the component's providers array. This is the only point where Phase 2 might require a change to how production components are structured — and even then, only if a component violates the principle of inputs-over-injection for its data.

### Build Pipeline

Phase 2 adds four new `.component.ts` files to the flat `web-ng/src/app/` directory and extends one existing file (`playground-demo-data.ts`). The `pg-case-study.component.ts` shell adds imports for the four new components. No changes to `app.routes.ts` — the `/playground` route already renders the case study shell. No changes to `app.config.ts`. The build pipeline (`ng build --configuration production`) requires no configuration changes.

### Anchor Link Contract

Phase 1 established seven anchor IDs that may be linked externally. Phase 2 preserves all seven and adds four new ones. The mapping:

| Existing (preserved) | New (added) |
|----------------------|-------------|
| `#hero` | `#problem` |
| `#pipeline` | `#live-demo` |
| `#design-language` | `#landing-showcase` |
| `#screen-gallery` | `#journey` (replaces `#journey-map` ID on the old simple timeline) |
| `#patterns` | |
| `#dark-mode` | |
| `#journey-map` (kept as alias, scroll target moves to `#journey`) | |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Production component has hard service dependency that triggers API call in demo context | Medium | High — playground makes network requests, breaking the zero-API-calls constraint | Audit each production component's constructor and `ngOnInit` before integration. Provide no-op service instances via component-level `providers` if needed. |
| Case study shell file exceeds 200 lines after adding 4 new section templates | High | Low — violates P7 but shell is inherently a composition file | Accept that the shell is the one file allowed to exceed the target. Its role is purely compositional — imports and template slots. No logic lives here. |
| Nav acts grouping causes layout regression at narrow viewports | Medium | Medium — nav overflow is an explicit success criterion | Test at 1024px viewport width as the gating breakpoint. Acts collapse section labels at narrow widths — act labels alone fit within horizontal constraints. |
| Editorial content in landing showcase diverges from actual landing page | Low | Low — the showcase is a narrative element, not a mirror | Review landing showcase content when `landing/index.html` receives updates. The limited surface (two sections) makes drift manageable. |

## Related Documents

- [Analysis](./analysis.md) — Problems, open questions, and design-reference findings driving this architecture
- [Epic](./epic.md) — Business value, scope boundaries, task breakdown, and success criteria
- [Timeline](./timeline.md) — Execution status and delivery tracking