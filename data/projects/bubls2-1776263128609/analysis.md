# 🔍 Analysis: bubls2

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-04-15

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 5 |
| MEDIUM | 5 |

---

## The Core Problem

Three shipped products (Bubls, Trendfy, Humanize-me) share overlapping infrastructure — auth, payments, deployment, even UI patterns — yet live in separate codebases with incompatible implementations. Every new product idea means re-wiring the same plumbing from scratch: Stripe webhooks, user sessions, rate limiting, CI/CD. The result is duplicated effort, divergent user models, and a growing maintenance surface that scales linearly with each new feature instead of amortizing across them.

The super app thesis — one shell, many routes — is the right structural answer, but the consolidation itself is the hard problem. The existing assets were built for their own contexts. Trendfy's Flask backend assumes its own auth tables. Humanize-me's Stripe integration assumes its own tier model. Bubls has no backend at all. Merging these into a coherent shell with shared auth, shared payments, and per-user feature gating requires reconciling three different data models, two different auth strategies, and an undefined billing architecture — all while shipping a new feature (/photoshoot) that depends on unproven native camera integration.

Consider: This is like merging three restaurants into a food hall. The kitchens (backends) were designed for their own menus. The POS systems (auth/payments) don't talk to each other. And the first thing you need to serve is a dish (photoshoot) that requires equipment (Capacitor Camera) nobody has tested in the new building yet.

---

## Symptoms

Users experience:

- No single app to access multiple AI features from one account
- Separate signups and credentials for each product (Bubls, Humanize-me, Trendfy)
- No way to discover new features within an existing product
- LoRA-powered photoshoot requires manual coordination (WhatsApp selfies, wait for training) before first use
- No unified payment tier that bundles multiple features
- iOS-only native experience limits reach to a single platform
- No feedback mechanism to report issues or request features
- Cold start — new features require full onboarding rather than appearing in an existing shell

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No unified auth system across products | Bubls uses magic links, Humanize-me uses Supabase, Trendfy uses email-only signup — three incompatible approaches, decision explicitly marked TBD in brain dump | Task: Auth consolidation |
| Codebase fragmentation prevents feature sharing | Three repos (Bubls, Trendfy, Humanize-me) with overlapping but incompatible code; no shared shell exists | Task: Shell scaffold from Bubls |
| LoRA onboarding is entirely manual and unscalable | Pre-training requires personally collecting 10-20 selfies per user, uploading to Replicate, manually mapping model_id to user — caps at exactly 15 users | Task: Pre-train 15 LoRA models |
| Trendfy verdict (May 1) creates architectural uncertainty | Feature roadmap, co-founder IP boundaries, and LoRA infrastructure ownership all depend on an external decision that hasn't been made; super app must be designed to absorb or discard Trendfy code | Task: Architecture must account for both outcomes |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Per-user feature gating doesn't exist | `enabled_features` dict described conceptually but not implemented in any current codebase; route middleware for checking features is net-new code | Task: User model + feature gating |
| Cross-product data model mismatch | Trendfy uses Neon Postgres auth tables, Humanize-me uses Supabase tables, Bubls has no persistence layer — no unified user record exists | Task: Database schema consolidation |
| Payments architecture undefined for multi-feature model | Humanize-me's Stripe integration handles 4 tiers for one product; super app needs per-feature gating across N features with different usage limits — fundamentally different billing model | Task: Stripe integration redesign |
| Capacitor Camera integration is unproven | Native iOS camera access via @capacitor/camera has not been tested in the Bubls shell; /photoshoot's core flow depends on it working | Task: Camera plugin integration |
| iOS app identity conflict with Bubls | App Store Connect record exists as ch.bubls.app; super app needs its own bundle ID, name, and store listing — or Bubls must be repurposed, which affects existing TestFlight users | Task: App identity decision |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No error handling for Replicate inference failures | LoRA inference can timeout, fail, or produce low-quality results; no fallback or retry described; user sees nothing if Replicate is down | Task: Backend error handling |
| Container port contention across projects | specdocv2-executor maps ports 8100/4000/4001/3003/8888 for different projects; super app consolidation may create conflicts during local development | Task: Docker Compose consolidation |
| No feedback collection mechanism | Week 2 plan says "watch, collect feedback" but no tooling, form, or channel exists for structured user feedback from the first 15 testers | Task: Feedback loop for testers |
| Co-founder IP boundaries on shared infrastructure | Trendfy is 50/50 with co-founder (4-year vest, 1-year cliff); super app is solo; LoRA pipeline and user model data transfer from Trendfy needs clarity on ownership | Task: Legal/business separation |
| Single default style limits photoshoot differentiation | v1 ships with one style and no picker; early users may find the output monotonous, reducing wow-factor and shareability | Task: Out of scope for Month 1 (noted for Month 2) |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Self-serve LoRA training pipeline | Deliberately unscalable for Month 1; only needed after 15-user validation |
| Android support | iOS-first strategy; Capacitor enables Android later but not a Month 1 priority |
| Analytics dashboard | Check Neon directly for Month 1; build tooling only after signal from first 15 |
| Style picker for /photoshoot | Month 2 feature; need user feedback on single-style experience first |
| Social features (sharing, following) | Post-validation; no evidence of demand yet |
| Web-only features | Everything must work on both web and iOS; no platform-specific features in Month 1 |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview