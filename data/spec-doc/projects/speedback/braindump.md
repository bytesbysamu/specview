# Speedback – Braindump

## What It Is

Speedback is an AI-assisted feedback writing tool targeting the DACH HR market. It takes the Speedback format (a structured peer-feedback template common in German-speaking companies) and wraps it in a component-based UI where each bullet point is independently generated from user-typed keywords. Tagline: "It's a match!" — riffing on speed dating.

## Problem It Solves

Writing one Speedback manually takes 30+ minutes. The format is rigid (Stärken → Entwicklung, each bullet follows Verhalten → Wirkung → Empfehlung/Wunsch), but most people struggle to articulate their thoughts within it. The tool reduces completion time to ~90 seconds: user enters keywords per bullet, hits Generate, reviews/edits, exports as clean plain text with no AI fingerprints.

## Core Design Insight

The template IS the interface. Bullets are generated one at a time (not the full document), which means users stay in control, can mix human and AI content, and the output feels like their own words. Each bullet has four states: Empty → Generating → Generated → Editing.

## Current State (as of 2026-01-20)

Phase 1 MVP is 90% complete. Frontend is fully functional: bullet component, form (header, Stärken/Entwicklung sections, Bemerkungen), export (clipboard + Markdown download), landing page with animated demo, confetti on completion, localStorage draft recovery. Backend is ready — using the existing Springular/Spring Boot server with Groq (llama-3.3-70b-versatile) via public endpoints (no auth required for MVP). Only remaining step: production deploy to speedback.ch.

## Key Decisions

- **No auth for MVP** — lower friction, faster launch, deferred to Phase 2
- **Unlimited bullets** — no free-tier limits until product-market fit is validated
- **Groq over Ollama** — free tier, dev/prod parity, fast
- **Client-side state only** — no database schema complexity; localStorage for draft recovery
- **German-first** — DACH target market; English later
- **Keep Angular** — reuse existing Springular codebase rather than rewrite in Next.js
- **API**: `POST /api/v1/speedback/bullet` (generate), `POST /api/v1/speedback/export` (MD/PDF)

## Tech Stack

Angular frontend (Speedback module added to existing app) + Spring Boot backend (`SpeedbackController` → `TextIntelligenceService` → Groq). Config-driven prompt selection via `application.yml`. Data model: `Speedback` with `Bullet[]` per section, stored client-side only in Phase 1.

## Business Model

Freemium. Phase 2: Pro at CHF 9/month (unlimited bullets, PDF export, email send, 30-day history). Phase 3: Team at CHF 29/month (5 seats, shared templates, dashboard). Month 1 targets: 100 completed speedbacks, 10 paying users, CHF 90 MRR.

## Open Questions

- Domain: speedback.ch vs speedback.app (availability unconfirmed)
- Whether to add rate limiting after launch if abuse occurs (currently deferred)
- Whether usage limits are even needed — MVP runs unlimited to test without friction
- AI-powered "magic" autocomplete (real-time keyword suggestions as user types) was planned but scope/status unclear

## Next Steps

1. Configure production environment + connect domain
2. Deploy and smoke test
3. Use for a real Speedback session (personal validation)
4. Share with first users, collect feedback
5. Phase 2: auth + Stripe + PDF export if validated
