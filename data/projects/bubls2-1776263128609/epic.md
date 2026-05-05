# 🎯 Epic: bubls2

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Three shipped products (Bubls, Trendfy, Humanize-me) share overlapping infrastructure — auth, payments, deployment, UI patterns — but live in separate codebases. Every new feature idea means re-wiring the same plumbing from scratch. A super app shell that hosts AI features as routes eliminates this duplication: one auth system, one payment integration, one deployment pipeline, N features. The marginal cost of adding the next feature drops from "a week of boilerplate" to "a route and an API endpoint."

The lead feature, /photoshoot, sits at the intersection of two validated signals. Trendfy proved demand for AI-generated styled photos (81 real orders, a working LoRA pipeline). Bubls proved the Angular + Ionic + Capacitor stack ships to TestFlight in a day. Combining these into a single app with pre-trained personal LoRA models creates an instant-magic experience: open the app, take a photo, get a styled result from your own model. No other consumer app offers personalized LoRA inference behind a simple camera button.

Month 1 targets 15 hand-picked testers with pre-trained models. This is deliberately unscalable — the goal is wow-factor and direct feedback, not growth. At ~$75-150 in Replicate training costs and zero new infrastructure spend (Neon, Coolify, Apple Developer all provisioned), the validation cost is trivial. If 15 users show retention signal, Month 2 adds /humanize and /headshot routes into the same shell, compounding the value of every prior investment.

**Value Proposition**: One app, many AI features — each new route inherits auth, payments, and deployment for free.

---

## Scope

### What This Epic Covers

- **Super app shell** – Evolve the Bubls codebase into a multi-route shell with shared navigation, layout, and user model
- **/photoshoot route** – Camera capture and upload flow connected to per-user LoRA inference, with gallery of past results
- **Auth consolidation** – Single auth system across the super app replacing three incompatible approaches
- **Per-user feature gating** – User model with `enabled_features` and route-level middleware to enforce access
- **LoRA model pre-training** – 15 personal models trained and mapped to user accounts before launch
- **Dual deployment** – Web via Coolify and iOS via TestFlight from the same codebase

### What This Epic Does NOT Cover

- ❌ Self-serve LoRA training pipeline — Deliberately unscalable for Month 1; only needed after 15-user validation
- ❌ Style picker for /photoshoot — Ship one default style; user feedback determines if variety matters
- ❌ Android build — iOS-first; Capacitor enables Android later but not a Month 1 priority
- ❌ Analytics dashboard — Query Neon directly for Month 1; build tooling only after signal
- ❌ Additional routes (/humanize, /headshot) — Month 2 scope, dependent on Month 1 feedback
- ❌ Stripe multi-feature billing — First 15 testers get free access; payments wired in Month 2 after validating retention

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Shell scaffold + navigation** | None | — | 1 day | High |
| 2 | **Auth + user model + feature gating** | 1 | 3 | 2 days | High |
| 3 | **/photoshoot route + camera + inference** | 1 | 2 | 2 days | High |
| 4 | **Deploy web + iOS** | 2, 3 | 5 | 1 day | High |
| 5 | **Pre-train 15 LoRA models + invite testers** | 3 | 4 | 3 days | High |

### Task 1: Shell scaffold + navigation

Evolve the existing Bubls codebase into a multi-route shell with tab navigation. Each feature becomes a route; the shell provides shared layout (dark theme, header, nav) and the structural foundation that all subsequent tasks build on. This directly addresses the codebase fragmentation issue identified in the Analysis — one shell replaces three separate apps.

### Task 2: Auth + user model + feature gating

Consolidate authentication into a single system and define the user model with an `enabled_features` structure. Route-level middleware checks feature access before rendering. This resolves the three incompatible auth approaches (magic links, Supabase, email-only) and creates the per-user gating that the payments system will later plug into. The auth decision (magic links vs Supabase) must account for the May 1 Trendfy verdict — see [Solution Architecture](./architecture.md) for design rationale.

### Task 3: /photoshoot route + camera + inference

Build the lead feature: camera capture (native via Capacitor Camera plugin), photo upload, Replicate LoRA inference with the user's personal model, and a before/after result screen with gallery. This is the core value proposition for first testers. Depends on the shell scaffold for routing and consumes the user model for LoRA model lookup. The Capacitor Camera integration is unproven in this shell — see [Solution Architecture](./architecture.md) for risk mitigation.

### Task 4: Deploy web + iOS

Ship the super app to both platforms: web via Docker Compose to Coolify (reusing Humanize-me's pipeline) and iOS via the Bubls TestFlight pipeline. Both pipelines exist but need configuration for the new app identity — the bundle ID decision (repurpose ch.bubls.app vs new ID) affects existing TestFlight users.

### Task 5: Pre-train 15 LoRA models + invite testers

Manually collect 10-20 selfies from 15 friends/testers, train a personal LoRA model for each on Replicate, and map each model to the user's account in the database. When testers open the app for the first time, their personalized model is already ready — instant magic, no waiting. This is the validation event: 15 real users with real photos generating real results.

---

## Success Criteria

This epic is complete when:

- ✅ Super app shell serves at least two routes (home + /photoshoot) on both web and iOS from one codebase
- ✅ A user can sign up once and access all enabled features without separate credentials
- ✅ /photoshoot captures or accepts a photo and returns a LoRA-styled result within 60 seconds
- ✅ 15 testers have pre-trained personal LoRA models mapped to their accounts
- ✅ 15 testers are invited to TestFlight and can use /photoshoot with their own model
- ✅ App is simultaneously accessible via Coolify (web) and TestFlight (iOS)

---

## Non-Goals

- ❌ Scalable onboarding — Manual LoRA training for 15 users is the point; self-serve comes after validation
- ❌ Feature completeness — One route, one style, one flow; breadth comes in Month 2
- ❌ Revenue — First 15 testers are free; Stripe integration deferred until retention signal exists
- ❌ Trendfy migration — The May 1 verdict determines what transfers; the shell must support either outcome but doesn't depend on it
- ❌ Co-founder IP resolution — Legal separation of Trendfy assets from solo super app is a business task, not a technical one

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview