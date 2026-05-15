# 🎯 Epic: Live Component Playground

## Business Value

The current design playground is a 2,304-line static HTML snapshot — a screenshot frozen in time. It proves that CSS tokens were applied once but says nothing about whether components actually work today. Every time a sub-component changes, the static HTML silently drifts out of sync, and the "reference" becomes a lie. Replacing it with live, rendered sub-components turns the playground from a maintenance liability into a self-verifying integration surface: if the playground renders, the components work.

For new users evaluating spec-doc, the playground is the first proof-of-life. A static page with lorem ipsum and fake project names signals "prototype." A live page where tabs click, status bars animate, markdown renders in a newspaper layout, and dark mode toggles across every section signals "production tool." This is the difference between a bounce and a signup. The playground is the product's demo reel — it must be live.

From an engineering perspective, a live playground that composes every V2 sub-component on one page is also the cheapest smoke test available. If any component's `@Input` contract breaks, the playground breaks visibly. This catches integration regressions without writing dedicated integration tests, saving ongoing maintenance effort for a solo developer shipping across multiple projects.

## Scope

### What This Epic Covers
- **Live sub-component composition** — Replace the static HTML playground with a single routable page that renders `SectionNavComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, and `LandingPitchComponent` using hardcoded demo data
- **Full status bar showcase** — Display all four status bar states (idle, active, success, failure) simultaneously so every visual state is provable at a glance
- **Interactive sidebar → reader binding** — Clicking files in the sidebar demo updates the reader panel content, requiring multiple demo spec entries keyed by filename
- **Dark mode toggle** — A single page-level toggle that switches all rendered sub-components between light and dark themes simultaneously
- **Create modal (display-only)** — A trigger button that opens the create-project modal with a functional form, but submit is a no-op handler (no project is created, no API is called)
- **Old playground preservation** — The static `DesignPlaygroundComponent` moves to `/playground-static` as a historical reference; the `/playground` route points to the new live page
- **Demo data extraction** — Hardcoded projects, specs, and section metadata isolated into dedicated data files to keep the component file under 200 lines

### What This Epic Does NOT Cover
- ❌ **Auth-gated real project loading** — The analysis identified a contradiction between "real data when logged in" and "no real API calls, works without auth"; this epic chooses hardcoded-only to eliminate auth-gating complexity from a demo page
- ❌ **Real AI operations** — Cost and side-effect risk make this permanently out of scope for a playground; a separate sandbox would be needed
- ❌ **Real project creation or Stripe flows** — Would pollute the user's project list and introduce transactional side effects on a demo page
- ❌ **Editable spec content** — The reader panel is read-only display; editing turns a demo into a mini-IDE
- ❌ **Animated section transitions** — Not in the brief, not in the success criteria; re-scope only if user testing reveals navigation confusion
- ❌ **UsageMeterComponent** — Referenced in the architecture sketch but has no defined playground section or demo data strategy; dropped until a clear use case emerges

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Verify sub-component input contracts** | None | — | 0.5 days | High |
| 2 | **Build demo data constants** | Task 1 | — | 1 day | High |
| 3 | **Create live playground component and template** | Task 2 | — | 1.5 days | High |
| 4 | **Wire route and retire static playground** | Task 3 | — | 0.5 days | High |
| 5 | **Add dark mode toggle and create modal trigger** | Task 3 | Yes (with Task 4) | 1 day | Low |

**Task 1 — Verify sub-component input contracts:** Confirm that all six sub-components (`SectionNavComponent`, `StatusBarComponent`, `ProjectGridComponent`, `SidebarV2Component`, `ReaderPanelComponent`, `LandingPitchComponent`) are stable standalone components with documented `@Input`/`@Output` signatures. Confirm `marked` and `DOMPurify` are project dependencies. Flag any missing or unstable contracts before proceeding.

**Task 2 — Build demo data constants:** Create hardcoded demo projects (8 projects across all 4 sections), multiple demo specs keyed by filename (to support sidebar → reader binding), and section metadata. Isolate into dedicated files to respect the 200-line file limit. This is the foundation every playground section consumes.

**Task 3 — Create live playground component and template:** Build the main component that composes all sub-components with demo signals and computed properties. Template organized in labeled sections. Sidebar file clicks update the reader panel content. Status bar renders all four states. Project grid renders demo projects. Verify `ng build` passes.

**Task 4 — Wire route and retire static playground:** Point `/playground` to the new live component. Move the old `DesignPlaygroundComponent` to `/playground-static`. Verify no navigation links elsewhere in the app or landing page break from the route change.

**Task 5 — Add dark mode toggle and create modal trigger:** Add a page-level dark mode toggle that affects all sections simultaneously. Add a button that opens the create-project modal in display-only mode (functional form, no-op submit). This is lower priority because the core demo value is delivered by Tasks 1–4.

## Success Criteria

- ✅ All six V2 sub-components render and are interactive on a single scrollable page at `/playground`
- ✅ Status bar displays all four states (idle, active, success, failure) simultaneously with working animation on the active state
- ✅ Project grid renders eight demo projects distributed across all four sections
- ✅ Clicking a file in the sidebar updates the reader panel with the corresponding demo spec content
- ✅ Dark mode toggle switches all rendered sections between light and dark themes
- ✅ Page loads and functions fully without authentication and without any backend API calls
- ✅ `ng build --configuration production` passes with zero new errors or test failures
- ✅ No component file exceeds 200 lines; demo data lives in separate files
- ✅ Old static playground remains accessible at `/playground-static`

## Related Documents

- [Analysis](./analysis.md) – Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) – System design, component composition, and demo data strategy
- [Timeline](./timeline.md) – Status tracking and delivery milestones