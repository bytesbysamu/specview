The codebase isn't mounted in this environment, but I have extensive context from the provided documents. I'll write the architecture document grounded in the real paths and patterns described in the codebase context.

# 🏗️ Solution Architecture: Playground V3

## Architecture Overview

Playground V3 replaces two disconnected surfaces — the live component playground (`live-playground.component.ts` and its `pg-*` children) and the nine-section case study shell (`pg-case-study.component.ts`) — with a single guided scroll experience containing roughly five sections. The mental model is a restaurant walk-through: the visitor is greeted, seated, shown the menu, served, and sent off — each transition intentional, each section exercising the full design-system vocabulary without naming it. The scroll is the spec-doc product's front door, not a reference sheet.

The key architectural insight is that V3 is a **composition problem, not a component problem**. The building blocks already exist — `pg-tokens`, `pg-borders`, `pg-animations`, `pg-state-matrix`, `pg-components-app`, `pg-components-ui`, the live app shell from `app-v3-state-extraction`, and the design tokens in `styles.css`. What's missing is the orchestrating container that sequences these pieces into a narrative arc, gates progression so visitors engage each section before advancing, and exposes a clean extraction boundary for the landing page to consume individual sections as standalone components.

The scroll shell is a single Angular standalone component that owns the section inventory, the gating state machine, and the viewport intersection logic. Each section is itself a standalone component receiving demo data via input signals. No new services, no new routes beyond replacing `/playground` — the complexity lives entirely in the composition layer and the scroll-gating mechanism.

## Design Principles

| Principle | Application in V3 |
|-----------|-------------------|
| P4 — No Speculative Abstractions | Five concrete sections, not a generic "section renderer." Each section component is hand-composed for its narrative purpose. No dynamic section registry. |
| P7 — File Size & Structure | Scroll shell under 200 lines; each section component under 200 lines. One component per file. Named exports only. |
| P6 — Channel Awareness (adapted) | Desktop gets the full 12-col newspaper grid; mobile gets a simplified 4-col layout with the same section sequence but lighter gating animations to avoid jank. |
| Newspaper Design Philosophy | Typography does the heavy lifting. No decorative chrome. Borders and whitespace provide structure. Ink-on-cream palette throughout. Quiet interactions — hover states barely visible. |
| Demonstration Over Documentation | Every design pattern (type scale, grid, borders, color, interaction) is exercised through use in each section. No section exists to "show" the design system — every section "is" the design system working. |
| Single Source of Truth | V3 becomes the canonical expression of the design system. Both the app's UX consistency checks and the landing page's component library consume from this one scroll, not from three diverging surfaces. |

## Component Design

### Scroll Shell

**Purpose**: The top-level container that hosts all sections in a single continuous route, manages gating state, and handles viewport intersection detection.

The scroll shell replaces the current `/playground` route binding (currently pointing to `live-playground.component.ts`). It renders as a full-viewport container with vertical scroll, no horizontal overflow, and a `max-width: 1400px` centered content area matching the existing newspaper layout constraint from `styles.css`. The shell owns a signal-based state machine tracking which sections the visitor has "unlocked." Each section slot receives its lock/unlock state as an input signal.

Viewport intersection drives the gating logic — as a section scrolls into the viewport threshold (roughly 60% visible), the shell evaluates whether the visitor has met the engagement condition for the current section and, if so, unlocks the next. This keeps the mechanism scroll-native rather than requiring explicit button clicks or stepper navigation, which would break the "guided restaurant" feel.

The shell exposes no public API beyond its route binding. Internally it manages an ordered array of section states (`locked | revealing | unlocked`) and a single `IntersectionObserver` instance observing sentinel elements placed at each section boundary.

### Section 1 — The Greeting (Hero / First Impression)

**Purpose**: Orient the visitor. Establish the aesthetic. Set expectations for the scroll ahead.

This section ports the narrative opening from the Groad case-study pattern: a masthead-scale headline (56–64px Playfair 700), a single sentence of body text (15–17px Source Serif), and generous whitespace. It exercises the top of the type scale, the ink-on-cream palette, and the newspaper border vocabulary — a thin rule separating the greeting from what follows. No interactive components here; this is pure typography and layout demonstrating that the design system can carry a page with nothing but words and space.

The section also contains a subtle scroll-down affordance — not a bouncing arrow, but a gentle opacity shift on the bottom border that implies continuation. This is the maître d' saying "right this way."

### Section 2 — The Kitchen (Process / Pipeline)

**Purpose**: Show how spec-doc works — the transformation from messy braindump to structured spec — through a visual pipeline, not a text explanation.

This section exercises the mid-range type scale (section titles at 28–36px, card titles at 18–22px), the 12-col grid, and the label typography (11–12px Source Sans, uppercase, tracked). It presents the spec-doc pipeline as a horizontal sequence on desktop (4 stages across the grid) and a vertical sequence on mobile (stacked cards). Each stage shows a thumbnail representation of the document it produces — braindump, analysis, epic, architecture — using real rendered markdown from `playground-demo-data.ts`.

The gating condition: the visitor must scroll through the full pipeline visualization before Section 3 unlocks. The IntersectionObserver sentinel sits at the bottom of this section.

### Section 3 — The Main Course (Live App Demo)

**Purpose**: The actual specview app running with demo data inside the scroll — not screenshots, not mockups, the real thing.

This is the centerpiece section and the most architecturally significant. It embeds the V2 app components — `project-grid`, `sidebar-v2`, `reader-panel`, `section-nav`, `status-bar` — wired to demo data from `playground-demo-data.ts` rather than live API calls. The services layer is the key design challenge: the embedded app needs to render real component trees with realistic data without hitting the Flask API.

The approach is a **demo-mode signal** propagated through the component tree. The scroll shell sets a `demoMode` signal to `true`, and the existing services check this signal before making HTTP calls — when true, they return hardcoded responses from `playground-demo-data.ts` instead. This avoids forking the component tree or creating parallel "demo" versions of each component. The `projects.service.ts` already manages all project CRUD and polling; adding a demo-mode branch that returns fixture data is a localized change.

This section exercises every design pattern simultaneously — the full type scale from masthead to label, the grid in both its 12-col and nested configurations, newspaper borders between panels, the ink-on-cream palette, hover states on grid cards and section tabs, and the dark-mode toggle affecting all embedded components. It is the design system under real load.

### Section 4 — The Presentation (Design Language in Action)

**Purpose**: A curated gallery of the design system's pattern vocabulary, demonstrated through composed vignettes rather than isolated swatches.

This section absorbs the best of Phase 1's live playground — the token swatches from `pg-tokens`, the border catalog from `pg-borders`, the animation gallery from `pg-animations` — but recomposes them into editorial layouts rather than presenting them as a reference grid. Instead of "here are all the colors," the visitor sees a composed newspaper spread where the colors, typography, borders, and spacing work together in a realistic layout that happens to showcase every token.

The gating condition is time-based intersection: the visitor must spend at least three seconds with this section in the viewport before Section 5 unlocks. This prevents drive-by scrolling past the pattern demonstration.

### Section 5 — The Send-Off (Call to Action / Exit)

**Purpose**: Close the experience. Transition the visitor from "exploring" to "using."

The final section is deliberately minimal — a large headline, a single call-to-action, and a generous footer whitespace. It exercises the masthead type scale one more time and introduces the accent color (#567B95) for the first time in the scroll as the CTA element, making it feel earned rather than arbitrary. The red (#C41E3A) appears only if the visitor has not signed up — a quiet urgency signal, not an alarm.

This section also serves as the extraction boundary test: it is the first component designed to be consumable by the landing page as a standalone unit, proving the extraction pattern before it scales to other sections.

## Gating Mechanism

### Scroll-Reveal with Intersection Gating

The gating model uses native `IntersectionObserver` with sentinel elements rather than a discrete stepper or scroll-snap. This decision resolves the first open question from the [Analysis](./analysis.md) and warrants detailed rationale.

**How it works**: Each section boundary contains an invisible sentinel `<div>` observed by a single `IntersectionObserver` instance owned by the scroll shell. When a sentinel crosses the visibility threshold (0.6 on desktop, 0.4 on mobile to account for smaller viewports), the shell evaluates the gating condition for the current section. If met, the next section transitions from `locked` to `revealing` — a CSS transition that fades in content and shifts it upward by 24px over 400ms, using the existing quiet-interaction philosophy.

**Locked sections** render their container at full height with content at `opacity: 0` and `pointer-events: none`. This preserves scroll position and page height — the visitor can see there is more content but cannot interact with it. A faint newspaper rule marks the boundary, and a single-line teaser in label typography (11px Source Sans, uppercase) hints at what the section contains.

**Why not scroll-snap**: Scroll-snap forces discrete page boundaries that conflict with the "one continuous scroll" requirement. It also creates jarring experiences on trackpad devices where momentum scrolling fights the snap points. The restaurant metaphor is "guided," not "locked in a room."

**Why not a stepper**: A visible stepper (dots, progress bar, numbered steps) adds navigation chrome that contradicts the "no decorative UI" principle. The gating should feel implicit — the visitor doesn't realize they're being guided until they try to skip ahead and find the content hasn't appeared yet.

**Mobile adaptation**: On viewports below 768px, the intersection threshold drops to 0.4, the reveal animation simplifies to opacity-only (no transform, avoiding layout recalculation), and the time-based gate on Section 4 reduces from 3 seconds to 1.5 seconds to respect faster mobile browsing patterns.

## Section Inventory Resolution

The epic's nine Phase 2 sections consolidate into five through merging and cutting:

| V3 Section | Absorbs From Phase 2 | Cut From Phase 2 |
|------------|----------------------|-------------------|
| 1 — Greeting | Hero section | — |
| 2 — Kitchen | Pipeline section, User Journey | Before/after transformation (redundant with live demo) |
| 3 — Main Course | Live App Demo, Screen Gallery | Screen annotations (the live app IS the annotation) |
| 4 — Presentation | Design Language, Patterns, Dark Mode | Component-by-component catalog (replaced by composed vignettes) |
| 5 — Send-Off | (new) | Landing Showcase (deferred to landing page epic) |

**What was cut entirely**: The "Landing Showcase" section from Phase 2 is removed. Its purpose — showing landing page patterns as Angular components — is better served by the extraction boundary defined in Section 5. The playground demonstrates the design system; the landing page consumes it. Mixing the two in one scroll dilutes both messages.

**Dark mode toggle**: Absorbed into Section 3 (live app demo) as an interactive element within the embedded app, not a standalone section. The toggle affects all components within Section 3's boundary only — it does not propagate to the scroll shell or other sections, which remain in the canonical ink-on-cream light mode. This prevents the jarring full-page flash that a global toggle would cause mid-scroll.

**Section nav fate**: The section nav component (`section-nav.component.ts`) renders inside Section 3 as part of the embedded app demo. It does not appear as scroll-level navigation. The scroll has no visible nav — progression is the navigation.

## State Management

### Demo-Mode Signal Architecture

The scroll shell introduces a single `demoMode` signal at the component level, propagated via Angular's dependency injection (a simple `InjectionToken<Signal<boolean>>`). Components that currently call `projects.service.ts` check this token: when `true`, the service returns fixture data from `playground-demo-data.ts` without HTTP calls.

This is the minimal intervention that avoids forking components. The existing `playground-demo-data.ts` already contains hardcoded demo projects; the architecture extends its shape to cover the additional data paths the embedded app components need (section taxonomy for `section-nav`, generation status for `status-bar`, markdown content for `reader-panel`).

### Gating State Machine

The scroll shell manages gating state as a simple signal array: `Signal<SectionState[]>` where `SectionState` is `'locked' | 'revealing' | 'unlocked'`. Section 1 starts as `unlocked`; all others start as `locked`. Transitions are unidirectional (`locked → revealing → unlocked`). There is no "re-lock" — once a section is unlocked, it stays unlocked for the session.

No persistence across sessions. Refreshing the page resets to Section 1 unlocked. This is intentional — the playground is a short experience (under 3 minutes), and forced repetition costs nothing while ensuring every visitor gets the full narrative.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | Angular 17 (standalone components, signals) | Existing stack; all playground components already built in Angular. No framework migration. |
| State | Angular signals (`Signal`, `computed`, `effect`) | Already the state pattern across all V2 components. No NgRx, no RxJS subjects for this surface. |
| Scroll detection | Native `IntersectionObserver` | Zero-dependency, browser-native, performant. No scroll-position polling, no third-party scroll libraries. |
| Animation | CSS transitions only | `opacity` and `transform` transitions at 400ms. No JavaScript animation libraries. Matches the "quiet interaction" design principle. |
| Styling | Global `styles.css` tokens | All V2 components use global classes with no component-scoped CSS. V3 continues this pattern — new classes added to `styles.css`, not to component stylesheets. |
| Demo data | `playground-demo-data.ts` (extended) | Existing fixture file extended with additional shapes for section taxonomy, generation status, and markdown content. |
| Routing | Single route replacing `/playground` | `app.routes.ts` updated to point `/playground` at the new scroll shell component. Old `live-playground.component.ts` route removed. |

## Landing Page Extraction Boundary

### Component Export Strategy

V3 defines but does not implement the extraction boundary — the landing page rebuild is a separate epic. The boundary is defined here so that Section 5 (Send-Off) can be built as a proof-of-concept extractable component.

**Extraction pattern**: Each V3 section component accepts all data via input signals and has zero dependencies on the scroll shell's gating state. This means any section can be rendered standalone by providing its inputs directly. The landing page imports the component, provides its own data, and renders it outside the scroll context.

**What is extractable**: Sections 1 (Greeting), 4 (Presentation), and 5 (Send-Off) are designed as self-contained compositions with no inter-section dependencies. Section 3 (Live App Demo) requires the demo-mode injection token and the full `playground-demo-data.ts` fixture — it is extractable but heavyweight. Section 2 (Kitchen) depends on the pipeline visualization layout, which is tightly coupled to its scroll position within the narrative.

**Export surface**: Named exports from each section component file. No barrel file, no shared module. The landing page imports directly from the component path.

## File Inventory

| File | Purpose | Est. Lines |
|------|---------|------------|
| `pg-scroll-shell.component.ts` | Scroll container, gating state machine, IntersectionObserver setup | ~180 |
| `pg-scroll-shell.component.html` | Section slots with sentinel elements | ~60 |
| `pg-section-greeting.component.ts` | Section 1 — hero typography and scroll affordance | ~80 |
| `pg-section-kitchen.component.ts` | Section 2 — pipeline visualization | ~150 |
| `pg-section-live-app.component.ts` | Section 3 — embedded app demo with demo-mode wiring | ~180 |
| `pg-section-patterns.component.ts` | Section 4 — composed design-pattern vignettes | ~160 |
| `pg-section-sendoff.component.ts` | Section 5 — CTA and extraction boundary proof | ~60 |
| `playground-demo-data.ts` | Extended with section taxonomy, status, and markdown fixtures | ~200 (from current ~120) |
| `styles.css` | New utility classes for scroll-reveal transitions and section sentinels | +~40 lines |
| `app.routes.ts` | Route update: `/playground` → `pg-scroll-shell` | ~2 line change |

All files stay under the 200-line target. All components are standalone with named exports. All live in the flat `web-ng/src/app/` directory — no subdirectories created.

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| IntersectionObserver gating over scroll-snap | Preserves continuous scroll feel; no momentum-fighting on trackpads; works identically on mobile without polyfill | Gating is "soft" — a determined visitor can scroll past locked content boundaries, though content remains invisible and non-interactive |
| Demo-mode signal over forked components | One component tree serves both the real app and the playground; changes to V2 components automatically appear in the playground | Services gain a conditional branch; if demo-mode logic grows complex, it should be extracted to a `demo.service.ts` |
| Five sections over Phase 2's nine | Tighter narrative arc; each section has a clear purpose in the restaurant metaphor; shorter total scroll respects visitor attention | Some Phase 2 content is cut entirely (landing showcase, screen annotations); if needed later, they become standalone routes, not scroll additions |
| No visible navigation (no stepper, no dots) | Aligns with "no decorative chrome" principle; the scroll IS the navigation; gating provides implicit progression | Visitors cannot jump to a specific section; acceptable because the scroll is designed to be consumed sequentially in under 3 minutes |
| CSS transitions only (no JS animation library) | `opacity` and `transform` are GPU-composited; zero dependency overhead; matches "quiet interaction" philosophy | Complex choreography (staggered reveals, spring physics) is off the table; if a section needs richer animation, it must be achievable with CSS keyframes alone |
| Dark mode scoped to Section 3 only | Prevents jarring full-page flash mid-scroll; the toggle demonstrates the capability without disrupting the narrative flow | Visitors don't see dark mode applied to the design-pattern vignettes in Section 4; acceptable because Section 3 already proves the system works in both modes |
| Session-only gating (no persistence) | The playground is a 2-3 minute experience; re-experiencing it on refresh costs nothing and ensures narrative integrity | Returning visitors cannot skip to their favorite section; mitigated by the short total length |
| Extended `playground-demo-data.ts` over API mock | Keeps all fixture data in one file already purpose-built for the playground; no mock server, no interceptor setup | Demo data must be manually updated when component data shapes change; acceptable for a solo-maintained project |

## Performance Considerations

The single-scroll architecture renders all five sections in one page load. This is viable because:

- **Sections 1, 2, and 5** are pure typography and layout — near-zero rendering cost.
- **Section 3** (live app demo) is the heaviest, containing the full V2 component tree. It renders with demo data (no HTTP latency) and is gated behind Sections 1 and 2, giving the browser time to paint it off-screen before the visitor arrives.
- **Section 4** recomposes existing `pg-*` components that are already optimized for the current live playground.

If mobile performance degrades (measured by Lighthouse or observed jank), the first mitigation is lazy-rendering Section 3's component tree — keeping the container at full height but deferring component instantiation until the section transitions to `revealing`. This is a localized change to `pg-section-live-app.component.ts` and does not affect the scroll shell architecture.

## Migration Path

The transition from the current playground to V3 is a replacement, not a gradual migration:

1. **New components built alongside existing** — all `pg-section-*` and `pg-scroll-shell` components are new files. No existing component is modified during development.
2. **Route swap** — when V3 is ready, `app.routes.ts` changes `/playground` from `live-playground.component.ts` to `pg-scroll-shell.component.ts`. The old V1 playground route (`/playground/v1` if it exists) is removed.
3. **Old components retained temporarily** — `live-playground.component.ts` and `pg-case-study.component.ts` remain in the codebase but are unreachable by route. They are deleted in a cleanup pass after V3 is verified in production.
4. **Demo data extended in place** — `playground-demo-data.ts` gains new exports for the additional fixture shapes. Existing exports remain unchanged so any other consumer is unaffected.

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this architecture
- [Epic](./epic.md) — Scope, tasks, and success criteria for Playground V3
- [Timeline](./timeline.md) — Status tracking for each task