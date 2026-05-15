# 🔍 Unified Page — Analysis

## The Problem
Three templates exist independently: a static landing page, a 2,304-line static design playground with all visual/layout decisions, and the real Angular app. Users hit different routes for marketing vs. product. The goal is one Angular template at `/` that uses the playground's CSS/layout as the visual foundation, wires it to the app's real signals and services, and prepends the landing pitch for anonymous visitors.

## Hard Constraints
- Compose, don't rewrite — landing hero, playground layout, and app logic already exist
- Must be a new template (`app-v2`) so current routes stay live during development
- Angular standalone component architecture (signals, no NgModules)
- No new backend routes — this is a frontend layout merge
- Files under 200 lines — the unified template will need to be split into sub-components

## Open Questions

- **Section 5 contradicts Sections 1–4.** The brain dump pivots from "playground = live anonymous demo with real-time generation" to "playground = static HTML design mockup." Every idea premised on a live demo (ghost projects, braindump-as-seed, signup-at-peak-value, spectator mode) is **designing a feature that doesn't exist**. Which is it?
  - A: The unified page is purely a layout merge (Section 5) — fast, shippable now
  - B: The unified page is a layout merge AND you build a new anonymous live-demo feature — large scope addition
  - **This must be answered before anything else moves forward.**

- **Auth-gated sections: conditional render vs. transform animation?** Brain dump says "sticky sections that transform" (Option B) but also says "compose existing components." Morphing animations are custom engineering on top of a layout merge.
  - A: Simple `@if (isAuthenticated)` — pitch section hidden, app section shown. Ship fast.
  - B: Animated collapse/expand transitions. Looks great, costs 2–3× the effort.

- **What replaces the current `/app` route?** If `/` becomes the unified page, does `/app` redirect to `/`? Or do both coexist permanently?

## Dependencies & Sequencing
- Playground HTML (2,304 lines) must be decomposed into importable Angular components **before** the unified template can compose them
- Landing pitch section must be extracted from static HTML into an Angular component
- The existing `app.component` signals/services are the data layer — unified page depends on them, not the other way around
- Auth state conditional rendering depends on existing auth service — no new backend work

## Explicitly Out of Scope

- **Ghost projects / anonymous persistence** — requires new backend (session tokens, account merging). Revisit only if you build a real live demo feature.
- **Spectator mode / public braindump feed** — new feature, new API, privacy implications. Not a layout task.
- **A/B testing framework** — solo founder, one user flow. Measure with analytics after shipping, not before.
- **Server-side rendering for SEO** — Angular app is client-rendered. Landing SEO lives on the static nginx page until you kill it. Don't solve SSR for a layout merge.
- **Dynamic OG tags / social previews** — same reason. Out until the static landing page is actually retired.
- **Braindump-as-seed onboarding flow** — this is a product feature, not a template composition. Revisit when login/signup flow is being redesigned.