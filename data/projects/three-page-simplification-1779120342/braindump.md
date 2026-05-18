# Simplify to Three Pages

The current Specview has too many pages, too much navigation, and too much surface area. Strip it down to three pages: landing, app, playground.

## Landing page
Single-page, single-section: just the hero. No features grid, no pricing, no testimonials, no footer nav forest. One compelling headline, one subline, one "Try it" CTA button. That's it. The CTA routes the user straight into the app.

## App — demo mode by default
When an unauthenticated user arrives at the app (from the landing CTA or directly), they land in demo mode. Demo mode uses mock data — the same kind of content the playground shows today — so the user immediately sees a working product without signing up. They can browse projects, view generated specs, explore the UI. All interactions work against mock data. No sign-up wall, no empty states, no "please log in" friction.

## App — authenticated mode
When a user logs in, the app seamlessly switches from mock data to real data. Same components, same routes, same UI — just a different data source. Services check auth state: if authenticated, wire to the real API; if not, return mock responses. The transition should be invisible — no page reload, no jarring redirect.

## Navigation
With only three destinations, navigation becomes trivial. Landing has the CTA. App has minimal chrome — maybe just a top bar with logo, login/logout, and that's it. No sidebar sprawl, no multi-level menus. The playground remains accessible but hidden from normal nav — it's our internal design workbench, not user-facing.

## Playground stays
Keep the playground exactly as-is for our own design iteration. We use it to prototype sections, test components, refine the design system. When we like something, we extract it to the landing hero or the app. The playground is the superset; landing and app are curated subsets.

## What gets removed
Everything that isn't hero, app, or playground. Extra landing sections, feature pages, pricing pages, about pages, complex footer navigation — all of it goes. If it's not one of the three pages, it doesn't exist.

---

## Correction: actually TWO pages, not three

The landing page IS the app. There is no separate marketing hero page. When you visit specview.dev you see the real app running with mock data. That's the pitch — the product sells itself by being visible immediately.

- `/` = the app. Not logged in? Mock data. Logged in? Real data. Same component, same UI.
- `/playground` = internal dev tool, stays as-is.
- No `/app` route. No separate landing hero. No CTA to "open the app" — you're already in it.
- Login button in the top bar. That's how you authenticate.
- The old monolithic app.component.ts shell is dead. Everything goes through the new simplified AppPageComponent at root.

---

## Audit findings and fixes (2026-05-18)

Deep cleanup audit after simplification landed. Key findings:

### Dead code removed
- 17 orphaned files deleted: app-v2/v3 shells, app-page component, live-playground, landing-pitch, unused top-bar
- All were unreferenced by any route or import

### Route references fixed
- `/login` and `/signup` routes restored — these pages stay as-is
- Login/signup components restored from pre-simplification
- Playground CTA buttons correctly point to `/signup`
- Token lifecycle auth failure correctly navigates to `/login`
- Billing interceptor 429 handling fixed (no redirect to deleted `/upgrade`)

### Masthead cleanup
- Upgrade button, usage meter, and "New" button hidden for anonymous users — only visible when logged in
- Sign-in link in masthead goes to `/login` page (not inline form)
- Sign-out button visible only when authenticated

### Final route table
- `/` — the real app with demo data (anon) or real data (auth)
- `/login` — login page (full-page, no app shell)
- `/signup` — signup page (full-page, no app shell)
- `/playground` — internal dev workbench
- Everything else → redirects to `/`
