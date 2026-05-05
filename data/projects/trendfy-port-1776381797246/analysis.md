---
sidebar_position: 1
---

# 🔍 Port Trendfy into Bubls Photoshoot — Analysis

**Purpose**: Surface constraints, dependencies, and open questions before scoping.

**Date**: 2026-04-16

---

## Problem

Trendfy has 7 users with trained LoRA models that work on Replicate today. Only Sam has a row in `superapp_lora_models`. The other 6 model-owning users have no Bubls account and no model mapping. Generated image URLs stored in Trendfy's database are Replicate CDN links — some have already expired. Without migration, Trendfy's tester base is wasted signal and their generated content is ephemeral.

## Hard Constraints

- Same Neon Postgres instance — Trendfy tables are readable from the Bubls backend (no cross-DB migration needed)
- No new Replicate training costs — reuse existing model IDs verbatim
- Always ORM — migration scripts use SQLAlchemy, not raw SQL
- Magic link auth — new Bubls users created via the existing auth flow, not by copying Trendfy passwords (Trendfy used email+password)
- Feature-gated — photoshoot already has its own feature flag; ported models follow the same gate

## Open Questions (resolved)

| Question | Resolution |
|---|---|
| How do Trendfy users become Bubls users? | One-time migration script creates Bubls user rows from Trendfy emails, sends magic-link invite. No password copy. |
| Which 7 models are real? | Sam v1, Sam v2, Sam v3a, Milky, Serina, Isabell, Lea — filter by `replicate_model_id IS NOT NULL` in Trendfy's `lora_models` table |
| How to handle expired Replicate URLs? | Download remaining valid URLs to local temp, save to device photo library on first Bubls launch. Expired = show placeholder in history. |
| Model picker UX? | Show model version label (e.g. "Sam v3a") in photoshoot page header. Single active model for v1 — no picker. If user has multiple models, use the most recent. |

## Dependencies

- Bubls photoshoot route (Epic 1) — ✅ shipped
- `superapp_lora_models` table (Epic 1) — ✅ shipped (Sam's row exists)
- `superapp_generations` table (Epic 2, Task 7) — ✅ shipped
- `@capacitor/filesystem` or `@capacitor-community/media` for photo library save — needs installation
- Trendfy DB tables readable from Bubls backend — ✅ same Neon instance

## Explicitly Out of Scope

- Self-serve LoRA training inside Bubls
- Multi-scenario generation (5 outfits per tap)
- Trendfy Stripe/payment migration
- Trendfy order management
- Model retraining or quality improvement
- Cloud image storage (S3/R2) — device-first for v1
