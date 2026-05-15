# 🎯 Epic: Unified Page

## Business Value

spec-doc currently splits its identity across three disconnected surfaces: a static marketing page at `/`, a static design playground with the finalized visual language, and the real Angular app behind `/app`. Every route boundary is a drop-off point. A visitor who likes the pitch must navigate to a different URL to use the product. A returning user who shares the root URL sends people to marketing copy, not the tool. The gap between "what the product looks like" (playground) and "what the product does" (app) exists only because they were built at different times — not because the separation serves anyone.

Collapsing all three into a single Angular template at `/` eliminates these handoff losses. Anonymous visitors see the landing pitch integrated directly above the real product interface. Authenticated users skip the pitch and land in their workspace immediately. The page adapts to auth state, not to route config. This is the difference between a product that *describes* itself and a product that *is* itself at every URL.

The leverage is high because the hard work is already done. The design playground's 2,304 lines of CSS, grid layouts, and newspaper-style design tokens represent every visual decision — finalized and tested. The Angular app has every signal, service, and API integration wired up. Neither needs to be rebuilt. The work is purely compositional: decompose the playground HTML into Angular components, compose them with the existing app logic, and conditionally render the landing pitch for anonymous visitors. This is a layout merge with outsized impact on perceived product quality and conversion simplicity.

## Scope

### What This Epic Covers

- **Playground HTML decomposition** — break the 2,304-line static design playground into importable Angular standalone components that preserve its CSS classes, grid layouts, and design tokens
- **Landing pitch extraction** — convert the static `landing/index.html` hero/pitch section into an Angular standalone component
- **Unified template composition (`app-v2`)** — a new Angular component at a staging route that arranges the landing pitch, playground-derived layout, and existing app signals/services into one page
- **Auth-conditional rendering** — anonymous visitors see the pitch section; authenticated users see it collapsed or hidden, with the workspace shown immediately
- **Route cutover** — promote `app-v2` to `/` once validated, redirect legacy `/app` to `/`

### What This Epic Does NOT Cover

- ❌ **Live anonymous demo / real-time generation for visitors** — the playground is a static design mockup, not a live feature; building a public demo is a separate epic with backend implications
- ❌ **Ghost projects / anonymous persistence** — requires new backend (session tokens, account merging); revisit only if a live demo feature is built
- ❌ **Spectator mode / public braindump feed** — new feature, new API, privacy implications; not a layout task
- ❌ **Braindump-as-seed onboarding flow** — product feature requiring login/signup flow redesign; not a template composition
- ❌ **Animated section transitions / morph effects** — the pitch section uses simple conditional rendering (`@if`), not collapse/expand animations; revisit as a polish pass after the merge ships
- ❌ **Server-side rendering or dynamic OG tags** — Angular app is client-rendered; landing SEO stays on the static nginx page until it is explicitly retired
- ❌ **A/B testing framework** — solo founder, one user flow; measure with analytics after shipping
- ❌ **Inline signup without navigation** — requires auth flow redesign; current redirect-based auth is preserved
- ❌ **New backend routes or API changes** — this is entirely a frontend layout merge

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Decompose playground HTML into Angular components** | None | — | 2 days | High |
| 2 | **Extract landing pitch into Angular component** | None | T1 | 1 day | High |
| 3 | **Compose unified template (`app-v2`)** | T1, T2 | — | 2 days | High |
| 4 | **Wire auth-conditional rendering** | T3 | — | 0.5 day | High |
| 5 | **Route cutover and legacy redirect** | T4 | — | 0.5 day | Low |

**Task 1** decomposes the static playground into standalone Angular components (project grid, reader panel, sidebar, status bar, section nav) each under 200 lines, preserving the playground's CSS classes and design tokens as the visual foundation.

**Task 2** extracts the hero/pitch content from the static landing page into a standalone Angular component, independent of Task 1 and runnable in parallel.

**Task 3** creates the `app-v2` component that imports the playground-derived layout components, the landing pitch component, and the existing app's signals and services — composing them into a single template on a staging route.

**Task 4** uses the existing auth service to conditionally render the pitch section for anonymous visitors and hide it for authenticated users, with no animation or transition logic.

**Task 5** promotes the staging route to `/` and adds a redirect from `/app` to `/`, retiring the old separate-route architecture. Kept at Low priority because it only fires once Tasks 1–4 are validated.

## Success Criteria

- ✅ A single route at `/` renders the landing pitch, playground-derived layout, and real app functionality in one Angular template
- ✅ Anonymous visitors see the pitch section; authenticated users see their workspace without the pitch
- ✅ All playground-derived components are standalone Angular components under 200 lines each
- ✅ No new backend routes or API changes introduced
- ✅ Existing app signals, services, and API integrations function identically in the unified template
- ✅ Legacy `/app` redirects to `/` with no broken navigation
- ✅ `ng build --configuration production` passes with zero errors

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — Component decomposition and composition design
- [Timeline](./timeline.md) — Status tracking and delivery milestones