# superapp-vision — Braindump

## What it is

Sam's overarching product strategy: a single Angular + Ionic + Capacitor shell app that hosts multiple AI-powered features as lazy-loaded routes. Features come and go; the shell (auth, payments, user gating) stays. The vision is a product factory — one monorepo, one deployment pipeline, one user base — that lets new features ship in days by reusing 70%+ of existing infrastructure. This is not a single product; it's a platform for rapid AI app iteration aimed at the App Store.

## Problem it solves

Building each AI micro-app from scratch wastes time on auth, payments, iOS pipelines, and deployment plumbing. The super app shells all of that so new features are purely product work. Simultaneously, each feature is a bounded context — no cross-feature coupling — so failures are isolated and features can be killed without touching the shell.

## Current state (as of May 2026)

- Architecture is fully specced (braindump-superapp-architecture.md): monorepo structure, feature-as-route pattern, Flask backend, Neon Postgres, magic link auth, Stripe subscriptions, per-user feature gating via enabled_features array, Angular signals for state.
- Month 1 plan exists (braindump-superapp-month1.md): shell + /photoshoot as the lead feature. Reuses Bubls iOS pipeline (already on TestFlight), Trendfy's LoRA/Replicate pipeline, Humanize-me's Stripe integration, Constellation's CI/CD patterns. Pre-train 15 LoRA models manually for first testers.
- Infrastructure already running: specdocv2-executor container, Neon Postgres (EU Central 1), Apple Developer account + TestFlight, Coolify for web, all API keys provisioned (Anthropic, Replicate, Stripe, Resend).
- babynamesai.md documents a parallel App Store play: iOS app for AI-generated baby names using Claude, targeting the evergreen "baby names" App Store search with no AI competition. Stack reuses the same Bubls/ionstarter template.
- Event discovery product (separate early-stage): a basic frontend + backend for surfacing events, pre-PMF. Core problems identified: rendering bugs, no strong filters, no data breadth. Path forward is event API aggregation (Ticketmaster, Eventbrite, Meetup), curated content, niche focus, affiliate monetization first. AI personalization is a future layer once data exists.
- Constellation context (claude-code-context-update.md, Jan 2026): earlier phase of the same strategy under a different name — "product factory" with a Flask + Angular ("Flangular") stack. Speedback Pro (AI feedback collection) shipped. ProposalPilot (Upwork automation) was next. This is the direct precursor to the super app vision.

## Key decisions already made

- Angular + Ionic + Capacitor: non-negotiable. Proven stack across Bubls, Trendfy, howDays, ionstarter. iOS-first but web works too.
- Flask backend: Python AI ecosystem is the best fit for Anthropic/Replicate SDKs. ~30 lines per endpoint.
- Neon Postgres: single database for everything. Already provisioned. pgvector-ready for future AI features.
- Magic link auth (not Supabase): zero friction, no passwords. Token in URL → Capacitor Preferences.
- Feature = bounded context: no cross-feature imports. Each feature has its own models, service, mock, tests.
- Angular signals, not NgRx: one screen per feature, no complex state flows needed.
- Coolify for web deployment, xcodebuild for iOS TestFlight: both pipelines already working.
- TestBed (not shallow-render): component tests use real child components to catch integration bugs.
- data-test selectors only: tests survive redesigns.
- Per-user feature gating via enabled_features array in Neon: Stripe webhook updates user record.
- Pre-train LoRA models manually for first 15 users: deliberately unscalable, optimizes for wow-factor.

## Open questions

- Trendfy verdict (May 1 kill date mentioned): does /try-on live on as a super app route or does only the LoRA pipeline survive?
- Auth decision: magic link (simple) vs Supabase (sessions, JWT, OAuth) — tension documented but unresolved.
- Baby names AI: standalone App Store app or a route in the super app?
- Event discovery: is this a super app route or a separate product? It has a different architecture (no LoRA, no Replicate) and different user intent (social planning vs personal AI tools).
- Pricing model: free tier limits and paid tier pricing are TBD across all features.
- Self-serve LoRA training: the manual-for-15 approach doesn't scale. When and how does this become self-serve?
- Android: currently excluded. When, if ever?

## Next steps

1. Execute Month 1 timeline: Bubls shell clone → /photoshoot route → Flask + Replicate inference endpoint → Capacitor Camera → deploy web + iOS.
2. Resolve Trendfy verdict: absorb surviving pieces into super app.
3. Ship Baby Names AI as a fast App Store experiment using ionstarter template + Claude API.
4. Fix event discovery front-end reliability; integrate one external event API (Ticketmaster or Eventbrite).
5. As features prove value, add Stripe subscriptions and per-feature paywalls.
6. Build toward the product factory pattern: each new feature takes less time because the shell, auth, payments, and CI/CD are already proven.
