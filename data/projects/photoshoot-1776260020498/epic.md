# 🎯 Epic: Photoshoot

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The /photoshoot feature is the super app's lead differentiator — a personal AI that makes your photos beautiful. Unlike generic filter apps, each user gets a LoRA model trained on their likeness, producing results that feel uncanny and personal. This "instant magic" drives word-of-mouth among the first 15 testers and validates whether personalized AI photo enhancement retains users before investing in scale.

The underlying business model reuses proven infrastructure from two shipped products: Trendfy's LoRA pipeline (training + inference) and Humanize-me's Stripe subscriptions (freemium tiers). Month 1 investment is minimal — ~$75-150 in model training, zero new infrastructure — while testing the highest-risk assumption: do users come back after the first wow moment? If 40%+ of the initial 15 return within 4 weeks, the feature earns its place as the super app's anchor and justifies building self-serve LoRA training in Month 2.

The super app shell itself is the multiplier. Every feature added after /photoshoot — /humanize, /headshot, future routes — inherits auth, payments, and distribution for near-zero marginal cost. Photoshoot pays the shell's setup cost; everything after rides free.

**Value Proposition**: Your personal AI model transforms every photo you take — no filters, no presets, just results that look like you at your best.

---

## Scope

### What This Epic Covers

- **Super app shell** – Tab-routed Ionic shell evolved from Bubls scaffold, with shared auth, feature gating, and /photoshoot as the first route
- **Auth + user-to-model mapping** – Resolve the auth approach and build the identity layer that maps each user to their pre-trained LoRA model
- **Photo capture and generation pipeline** – Camera/upload → Flask → Replicate LoRA inference → before/after result display, including loading UX and failure states
- **Manual LoRA pre-training for 15 testers** – Collect selfies, train models, seed database mappings, validate with real photos
- **Web + iOS deployment** – Ship to Coolify and TestFlight using existing pipelines

### What This Epic Does NOT Cover

- ❌ Self-serve LoRA training — Deferred to Month 2; Month 1 is manual pre-training for 15 users only
- ❌ Style picker or multiple output styles — One default style ships; variety comes after validation
- ❌ Android support — iOS-only via Capacitor for Month 1
- ❌ Onboarding wizard — Email signup and done; no multi-step flows
- ❌ Analytics dashboard — Query Neon directly for Month 1 metrics
- ❌ Settings page or social features — Stripped to essential flow only

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Super app shell + auth** | None | 2 | 2 days | High |
| 2 | **Pre-train 15 LoRA models** | None | 1 | 3 days | High |
| 3 | **Photo capture and generation pipeline** | 1 | — | 2 days | High |
| 4 | **Deploy and distribute** | 1, 2, 3 | — | 1 day | High |

### Task 1: Super app shell + auth

Evolve the Bubls scaffold into a tab-routed super app shell with /photoshoot as the first route. Resolve the auth decision (magic link vs. Supabase) and implement user identity with an `enabled_features` gating mechanism. Build the user-to-model mapping in Neon so each authenticated user resolves to their pre-trained LoRA model. This task unblocks everything downstream — without identity, there is no personalization. See [Solution Architecture](./architecture.md) for design decisions.

### Task 2: Pre-train 15 LoRA models

Collect 10-20 selfies from 15 friends/testers, train a LoRA model for each on Replicate, and seed the user-to-model mappings in Neon Postgres. Validate each model produces acceptable results before inviting users. This task runs in parallel with shell development and is the manual, deliberately unscalable approach that creates the "instant magic" first impression — when user #1 opens the app, their model is already waiting. Total cost: ~$75-150.

### Task 3: Photo capture and generation pipeline

Wire the end-to-end flow: Capacitor Camera plugin for live capture, file input for upload, Flask endpoint that receives an image and user_id, looks up the user's LoRA model, calls Replicate inference, and returns the result. Build the result screen with before/after comparison, and implement loading states that set honest latency expectations (addressing Replicate cold-start delays). Include failure handling so users see clear feedback when generation fails rather than entering a void. Gallery view displays past results. See [Solution Architecture](./architecture.md) for storage and latency decisions.

### Task 4: Deploy and distribute

Ship the web build to Coolify and the iOS build to TestFlight using existing pipelines from Bubls and Humanize-me. Invite the 15 pre-trained testers to TestFlight. Validate that camera permissions, LoRA inference, and auth all work on a real device. This is the "watch, collect feedback, fix critical bugs" gate before iterating.

---

## Success Criteria

This epic is complete when:

- ✅ A pre-trained user can open the app, take or upload a photo, and receive a LoRA-enhanced result
- ✅ 15 users have pre-trained models seeded in the database and can access /photoshoot via TestFlight
- ✅ Auth identifies each user and maps them to their personal LoRA model without manual intervention
- ✅ Users see clear loading indication during generation and actionable feedback on failure
- ✅ The app is live on both Coolify (web) and TestFlight (iOS) with the same codebase
- ✅ User #16 sees a clear boundary (waitlist, message) rather than a broken experience

---

## Non-Goals

- ❌ Scaling beyond 15 users — This epic validates the experience, not the infrastructure; self-serve training is a future epic
- ❌ Optimizing Replicate latency — Honest loading UX is the Month 1 answer; cold-start optimization is premature
- ❌ Multiple styles or user preferences — One default style ships; if retention is strong, style variety follows
- ❌ Cost optimization — At 15 users and ~$150 training cost, monitoring matters more than optimizing
- ❌ Trendfy integration decisions — The May 1 verdict determines what merges; this epic maintains isolation so either outcome works

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview