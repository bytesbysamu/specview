# WardrobAI / trendfy.me — Braindump

## What it is

trendfy.me is an AI fashion photoshoot service. Users pay $5, upload 15–25 selfies, a LoRA model trains on them, and they receive 5 outfit images (Office, Date Night, Summer, Weekend, Formal) by email in ~20 minutes. Category peer: Aragon, HeadshotPro, Secta — not closet apps or try-on tools. The repo folder is `wardrobai`; the customer-facing brand is trendfy.me.

Separately, the same repo contains **Bubls** — an event discovery app for Zürich delivering 5 AI-curated picks weekly via iOS app, web, and email. Both projects live in `/Users/sam/Projects/2026/wardrobai/`.

## Problem it solves

trendfy.me: People want to see what they look like in outfits before buying or for social media, but real photoshoots cost $200+. DIY AI tools don't put you in the images. trendfy.me does a $5 AI photoshoot.

Bubls: Event discovery is broken. Eventbrite shows 400 results, Google bounces you across 6 sites. Socially active Zürich residents (especially expats without local networks) default to inaction or repeat the same 3 venues. Nobody has solved push-based, curated, weekly discovery for Switzerland.

## Stack

**trendfy.me:** Angular 21 (`app/`), Flask/Gunicorn (`server/`), Replicate for LoRA training + inference, static landing (`landing/`), Docusaurus docs, nginx reverse proxy, Docker Compose. API contract in `api/openapi.yaml` → auto-generates TypeScript + Python types. Phase 1 routes: `upload/:orderId`, `status`, `results` only.

**Bubls:** Angular 19 + Ionic 8 + Capacitor 7 (reusing Constellation frontend scaffold). Python worker runs every Thursday: Ticketmaster + Guidle APIs → OpenAI embeddings → Neon Postgres with pgvector → Claude Haiku curates 5 picks per subscriber → push notifications + Resend email. Same Neon instance as Springular/humanize-me (tables prefixed `bubls_`).

## Current state

trendfy.me: Live pipeline exists (real LoRA training via Replicate). App redesign planned: 3-page user-scoped structure (Home/orders list, Upload, Order detail with processing→results transform). Current app shows global data without user scoping — broken UX. Landing page v3 plan written (honest copy that matches the actual product — remove "one click" claims). Backend pipeline exists but Phase A landing copy can't go live until `app.trendfy.me` subdomain, post-payment email with upload link, and end-to-end pipeline <25min are all confirmed.

Bubls: Frontend scaffold with mock data running. No backend yet. Spec docs written (analysis, epic, architecture, timeline in `bubls/` spec folder). Next step: get iOS TestFlight build, then wire Flask + Neon backend.

## Key decisions made

- **trendfy.me Phase 1 is a service, not an app**: payment → upload → generate → email. No closet, no real-time try-on, no outfit builder.
- **$5 USD single price** across all locales. Stripe Payment Link, no dual-currency complexity.
- **Timing claim is load-bearing**: "Ready in ~20 min" cannot go live until confirmed with end-to-end tests. Delay Phase A if needed.
- **Competitors in comparison table**: AI photoshoots (Aragon, HeadshotPro), not closet apps.
- **Bubls: Zürich only** until retention proven. iOS first. Email + token = identity (no accounts).
- **Bubls: Two-pass curation**: vector similarity pre-filters to top candidates, Claude ranks final 5. Cheaper than sending all events to Claude.
- **Repo structure** (MIGRATION_PLAN_V3/V4): Springular-pattern monorepo with `app/`, `server/`, `landing/`, `notebooks/`, `docs/`, `nginx/`, Docker Compose with healthchecks, non-root containers, resource limits, dorny/paths-filter CI.
- **Archive strategy**: Old code in `archive/` (gitignored locally, not pushed).

## Open questions

- Is the trendfy.me pipeline consistently hitting <25 min? (prerequisite to flip Phase A copy live)
- Is `app.trendfy.me` subdomain and TLS live?
- Does the `GET /api/v1/orders` (user-scoped list) endpoint exist yet? (needed for app redesign Home page)
- Bubls: Which distribution channels actually convert? (r/zurich vs. expat Facebook groups vs. personal network TestFlight)
- Bubls: Push notification opt-in rate — fallback to email-only cadence if low?
- Bubls backend: Build order — Flask API first or Python worker first?

## Next steps

**trendfy.me:**
1. Confirm pipeline <25 min end-to-end (5 cold-start tests)
2. Build `GET /api/v1/orders` (user-scoped list)
3. App redesign: HomeComponent (orders list), fix UploadComponent redirect, OrderComponent (processing→results state machine)
4. Once backend confirmed, flip Phase A landing copy

**Bubls:**
1. Style the dashboard component, wire up interest picker
2. Get TestFlight build via `ng build → cap copy ios → Xcode archive`
3. Set up Neon tables (`bubls_subscribers`, `bubls_picks`, `bubls_events_raw`, `bubls_engagement`)
4. Python worker: Thursday ingestion → embed → curate → email/push
5. Manual distribution: personal network TestFlight first, then Reddit/expat channels
