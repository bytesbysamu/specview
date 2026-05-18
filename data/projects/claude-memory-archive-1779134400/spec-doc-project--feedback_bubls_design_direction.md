---
name: Bubls — light-default, dark variant; each page is its own maxed-out app
description: Bubls design philosophy: LIGHT is the default mode (dark variant available); treat each route (Picks/Photoshoot/Text/Onboarding) as a distinct visual world maxed out for that feature, not a uniform design-system app.
type: feedback
originSessionId: be5272c1-b80e-4ac3-9f7a-c85bfa4dc48b
---
For Bubls (`/projects/bubls/`), two load-bearing direction calls:

**1. Light is the default mode. Dark mode also exists as a variant.**
The current `src/app/styles/tokens.scss` ships dark-only (`color-scheme: dark`, `--page-bg: #080808`) — that is incorrect/stale. Bubls ships **light-default**, with a dark variant. Both modes need first-class design treatment for every surface — light mode is not an afterthought.

Why: User explicitly corrected an earlier "always dark" framing on 2026-04-16. Closest spiritual reference for Bubls' light identity = Claude mobile (cream background + serif headline + dark CTAs). Closest dark reference = Sora (deep black, restrained type).

**2. Each page = its own app, maxed out for its feature.**
The user does NOT want one consistent design system flattened across all surfaces. They want each route (Picks / Photoshoot / Text / Onboarding) to be a distinct visual world, handcrafted for its single core action. The shell tab bar is a portal between worlds, not chrome that homogenises them.

How to apply:
- Every visual decision must be designed for BOTH light and dark — not just dark with `prefers-color-scheme` flips.
- Per-surface tokens override defaults inside that route's `:host`. Each surface picks its own backgrounds, accent emphasis, type scale, motion, header treatment.
- Only token primitives (radius, spacing, motion easing, font families) + tab-pill grammar are shared across surfaces.
- Reject suggestions to demote/hide a feature for "consistency" — each is a first-class world.
- Don't introduce a user-facing dark/light toggle yet (system-driven only); revisit after launch.
