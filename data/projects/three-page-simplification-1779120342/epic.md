Now I have enough context from the analysis, builder profile, and codebase structure. Let me write the epic document.

# 🎯 Epic: Three-Page Simplification

## Business Value

Specview's current surface area works against its own adoption. An unauthenticated visitor lands on a multi-section landing page, hits a login wall, and sees an empty state — three friction points before encountering any value. Meanwhile, the sidebar-driven app exposes context editors, billing gates, and navigation depth that a solo-product tool doesn't need yet. Every unnecessary page is a maintenance tax on a solo developer and a cognitive tax on a first-time visitor. Stripping to three pages (landing, app, playground) eliminates both costs simultaneously.

Demo-by-default is the core business lever. When the CTA drops an unauthenticated user into a working app with mock data — real projects, real specs, real UI interactions — the product sells itself before any signup form appears. This is the same pattern that made tools like Linear and Figma convert at high rates: show the working product, not a marketing page about the product. For spec-doc, where the value proposition is "see your documentation generated," showing generated documentation is strictly better than describing it.

The playground survives as an internal design workbench, not a user-facing page. It's where new sections get prototyped and validated before graduating into landing or app. This keeps the creative iteration loop fast without adding public surface area. Three pages is not a limitation — it's a forcing function that keeps the product focused on the one thing it does: generate and display specs.

## Scope

### What This Epic Covers
- **Angular Router bootstrap** — Add `@angular/router` to a currently routerless app, establishing `/`, `/app`, and `/playground` as the only three routes
- **Landing page (hero-only)** — Single-section static page: headline, subline, CTA button routing to `/app`
- **Mock data layer** — Auth-aware service fork that returns static project/spec data for unauthenticated users, enabling demo mode without backend calls
- **App page with demo-by-default** — Unified app shell that renders mock data for anonymous users and real API data for authenticated users, with seamless transition on login
- **Navigation collapse** — Replace sidebar-driven navigation with minimal top bar (logo + auth action); sidebar removed from shell, project browsing handled inline

### What This Epic Does NOT Cover
- ❌ **Billing/pricing pages** — No monetization timeline; premature to build gates for revenue that doesn't exist
- ❌ **Context editors as standalone views** — Revisit once the app page layout stabilizes; currently too much surface for too little usage
- ❌ **Backend route removal** — Endpoints stay intact; only frontend surfaces are cut. Dead endpoint cleanup is a separate hygiene pass
- ❌ **Playground redesign or documentation** — Kept as-is for internal use; no onboarding, no nav link, no public discovery
- ❌ **OAuth or new auth providers** — Existing JWT flow is sufficient; new providers are a separate capability
- ❌ **Feature pages, about pages, footer navigation** — Explicitly killed; no planned trigger for return

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Bootstrap Angular Router** | None | — | 1 day | High |
| 2 | **Build landing page (hero-only)** | Task 1 | Yes (with 3) | 1 day | High |
| 3 | **Create mock data layer** | Task 1 | Yes (with 2) | 2 days | High |
| 4 | **Build app page with demo/auth modes** | Tasks 2, 3 | — | 2 days | High |
| 5 | **Strip dead pages and collapse navigation** | Task 4 | — | 1 day | High |

**Task 1 — Bootstrap Angular Router:** Add `provideRouter()` to `app.config.ts`, define three routes (`/` → landing, `/app` → app, `/playground` → existing shell), refactor root component to use `<router-outlet>`. Replace signal-based view switching with route-based navigation.

**Task 2 — Build landing page (hero-only):** Standalone component at `/`. One headline, one subline, one CTA button. CTA uses `routerLink="/app"`. No features grid, no pricing, no testimonials, no footer. Pure static — no service dependencies.

**Task 3 — Create mock data layer:** Define static JSON fixtures (2–3 mock projects with pre-generated spec content). Create an auth-aware service wrapper: when unauthenticated, methods return mock data; when authenticated, methods delegate to the real `ProjectsService`. Components consume the wrapper, never the concrete service directly.

**Task 4 — Build app page with demo/auth modes:** Unified app shell at `/app` consuming the mock-aware service. Unauthenticated users see mock projects and specs immediately (demo mode). On login, the service switches to real API calls — same components, same template, different data source. No page reload, no redirect. Includes inline project browsing (replacing sidebar's role).

**Task 5 — Strip dead pages and collapse navigation:** Remove all components not serving landing, app, or playground. Replace the sidebar with a minimal top bar (logo + login/logout). Ensure `/playground` is routable but has no nav link. Clean up unused imports, styles, and assets.

## Success Criteria

- ✅ Unauthenticated user clicking the landing CTA sees a populated app with mock projects and specs — zero empty states, zero login prompts
- ✅ Authenticated user sees real API data in the same app shell with no visible transition seam (no reload, no redirect)
- ✅ Only three routes exist: `/`, `/app`, `/playground` — any other path redirects to `/`
- ✅ No sidebar renders anywhere in the app; top bar is the only persistent chrome
- ✅ `ng build --configuration production` passes with zero errors after all tasks complete
- ✅ Playground remains fully functional at `/playground` with no regression from current behavior

## Related Documents

- [Analysis](./analysis.md) — Problems driving this epic
- [Solution Architecture](./architecture.md) — System design
- [Timeline](./timeline.md) — Status tracking