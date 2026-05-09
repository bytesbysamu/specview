# 🔍 landing-polish-newspaper — Analysis

## The Problem
Brain dump references `ux-polish-newspaper-1778238000` and a "playground" as source material, but neither artifact is accessible from this workspace (`/app`). Without the UX files and current landing page markup, the polish target is undefined — there is nothing concrete to spec against.

## Hard Constraints
- Reference bundle `ux-polish-newspaper-1778238000` MUST exist and be readable before spec generation continues — it is the sole source of design intent.
- Landing page is part of `spec-doc` frontend (Angular :4201, standalone components, signals) — polish must respect that stack, no framework swap.
- "Newspaper" aesthetic implies editorial typography + dense grid — must remain responsive down to mobile (Telegram is primary mobile surface for the broader system, but landing is web-only).
- No new backend endpoints — landing is static-shaped; Flask :3101 stays untouched unless the brain dump explicitly says otherwise.

## Open Questions
- **Where is `ux-polish-newspaper-1778238000`?** — (a) external path the user will mount, (b) a `spec-doc` artifact stored in git_db, (c) a typo for an existing directory. Cannot proceed until resolved.
- **What is "the playground"?** — (a) `/playground` route in spec-doc frontend, (b) a separate prototype app, (c) a Storybook-style component sandbox. Determines whether polish patterns are extracted from playground → landing, or pushed landing → playground.
- **Which landing page?** — (a) spec-doc's own marketing/login surface, (b) humaniz.me, (c) trendfy.me, (d) Bubls. Brain dump says "the landing page" as if singular and obvious; it is not.
- **What is "newspaper" non-negotiable vs. directional?** — typography only, full editorial layout (columns/rules/drop caps), or just tonal cue? Scope swings 3× depending on answer.
- **Polish vs. redesign threshold** — keep current IA and restyle, or allowed to restructure sections?

## Dependencies & Sequencing
- Resolving the reference bundle location blocks everything — analysis, epic, architecture all derive from those files.
- Identifying the target landing page blocks "current state" capture (screenshots, component inventory).
- Newspaper design tokens (type scale, rules, grid) must be defined in architecture.md before any implementation guide can be written.
- Playground reconciliation (shared components vs. landing-only) decides whether this is one guide or two.

## Explicitly Out of Scope
- Backend/API changes — landing polish is presentational; trigger to re-scope only if UX files mandate new data.
- Mobile app surfaces (Bubls, Telegram) — different channel, different constraints.
- Auth/onboarding flow redesign — polish ≠ funnel rework; re-scope only if brain dump explicitly names signup.
- Cross-project rollout (humaniz.me, trendfy.me) — single landing page in scope; re-scope only if user confirms multi-site.
- Net-new sections (pricing, testimonials, blog) not present in current landing — polish operates on what exists.