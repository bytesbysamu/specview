# 🔍 Three-Page Simplification — Analysis

## The Problem
Specview is currently a single-page Angular app with signal-based navigation, a sidebar, and no router — but it exposes too many surfaces: context editors, billing gates, skill runners, action forms, and template pages all live in one shell. The brain dump wants exactly three destinations (landing, app, playground) with demo-by-default for unauthenticated users. This requires adding a router to an app that has none, adding a mock data layer that doesn't exist, and killing pages that are wired to live backend routes.

## Hard Constraints
- Angular standalone components + signals — no migration off this
- Flask backend stays; API contract changes must be additive (public share route already exists)
- Solo dev — the cut must be one pass, not a phased deprecation
- No Redis/Postgres — mock data lives client-side or as static JSON, not in a demo database

## Open Questions
- **What is "the playground"?** The brain dump says "keep exactly as-is" but no playground page exists in the current codebase. Is this the root app shell today rebranded? A hidden `/playground` route? A Storybook-like harness? → *Must define before the epic can reference it*
- **Does the sidebar survive?** Current app is sidebar-driven. "No sidebar sprawl" could mean slim it down or kill it. The app page still needs project browsing — what replaces the sidebar? → *Top bar with project switcher / sidebar stays but collapses / flat list in main area*
- **Where do context editors go?** Builder profile, principles, codebase, references are currently first-class views. Are they in-app settings? Moved to playground? Cut entirely? → *In-app settings panel / playground-only / removed*
- **Mock data scope:** Demo mode shows "a working product." Does that mean one fake project with pre-generated specs, or multiple projects with full browse/generate flows? Generate actions can't be mocked trivially. → *Static snapshot / interactive with canned responses*
- **Auth provider:** "When a user logs in" — the backend has JWT auth. Does the landing→app flow use the existing `/api/auth/login`, or is this a future OAuth flow? → *Existing JWT / add Google OAuth / defer auth entirely*

## Dependencies & Sequencing
- **Router before pages.** Angular Router must be added first — landing, app, and playground can't exist as separate pages without it. This is a structural change to `app.config.ts` and the root component.
- **Mock data layer before demo mode.** Services need an auth-aware fork (`isAuthenticated ? realApi : mockData`). Mock data must exist before the app page can render for unauthenticated users.
- **Landing page is blocked by nothing** — pure static component, can ship first.
- **Playground definition blocks playground work.** Can't "keep as-is" something that isn't defined yet.

## Explicitly Out of Scope
- **Billing/pricing pages** — cut now; re-scope if monetization timeline moves up
- **Context editors as standalone views** — too much surface; revisit when the app page settles
- **Feature pages, about pages, footer nav** — brain dump explicitly kills these; no trigger for return
- **Backend route removal** — endpoints stay; only frontend surfaces are cut. Dead endpoints get cleaned in a separate pass
- **Playground as user-facing** — brain dump says internal only; no onboarding, no docs, no nav link