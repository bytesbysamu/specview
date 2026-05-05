---
sidebar_position: 2
---

# 🎯 Port Trendfy into Bubls Photoshoot — Epic

**Purpose**: Migrate Trendfy's users, models, and results into Bubls photoshoot.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and resolved questions.

---

## Business Value

Trendfy has 32 users who already proved willingness to upload selfies and wait for AI-generated photos. 7 of them have trained LoRA models with real Replicate model IDs. 76 generated results sit in the database. Converting these to Bubls testers is a data migration, not a feature build — every one of them could open Bubls on TestFlight and immediately generate from their personal model.

This is the fastest path to multi-user TestFlight signal. No new AI, no new training, no new infrastructure — just mapping existing data into existing tables and adding one Capacitor plugin for photo-library save so images survive URL expiry.

---

## Scope

### What This Epic Covers

- User migration: Trendfy users → Bubls users via magic-link invite
- Model migration: 7 trained LoRA models → `superapp_lora_models` rows with real Replicate model IDs
- Result migration: 76 historical generated images → `superapp_generations` rows visible in photoshoot history
- Photo-library save: generated images persist to device photo library via Capacitor plugin
- Model label: active model version displayed in photoshoot page header
- Expired-URL handling: placeholder image for results whose Replicate URL has expired
- One-time migration script (Alembic + SQLAlchemy, not raw SQL)

### What This Epic Does NOT Cover

- ❌ Self-serve LoRA training
- ❌ Multi-scenario generation
- ❌ Trendfy payment/order migration
- ❌ Model retraining or quality improvement
- ❌ Cloud image storage (S3/R2)
- ❌ Model picker (multi-model selection UX) — most-recent model auto-selected for v1

---

## Tasks

**Note**: Task status tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **User Migration Script** | None | 2 | 0.5 day | High |
| 2 | **Model Migration Script** | None | 1 | 0.5 day | High |
| 3 | **Result Migration + Expired-URL Handling** | 1, 2 | — | 1 day | High |
| 4 | **Photo Library Save (Capacitor)** | None | 1, 2, 3 | 0.5 day | High |
| 5 | **History UI — Migrated Results + Model Label** | 3, 4 | — | 0.5 day | Medium |
| 6 | **Integration Test + TestFlight QA** | 5 | — | 0.5 day | Medium |

### Task Details

#### Task 1: User Migration Script
Alembic migration that reads Trendfy's `users` table (same Neon instance), creates Bubls `superapp_users` rows for each email that doesn't already exist. Set `builder = NULL`, `onboarding_skipped_at = NULL` so the onboarding guard triggers on first Bubls launch. Generate a magic-link token per user and queue invite emails via the existing email service. Do NOT copy Trendfy passwords — Bubls uses magic-link auth only. Log: N users created, N already existed, N emails queued.

#### Task 2: Model Migration Script
Alembic migration that reads Trendfy's `lora_models` table filtered by `replicate_model_id IS NOT NULL` (7 models). For each, create a `superapp_lora_models` row mapping to the Bubls user (from Task 1). Copy `replicate_model_id`, `model_name`, `trigger_word`, `created_at`. If user has multiple models, mark the most recent as `is_active = true`. Log: N models migrated, N users with models.

#### Task 3: Result Migration + Expired-URL Handling
Alembic migration that reads Trendfy's `generated_images` table (76 rows). For each, create a `superapp_generations` row with `feature = 'photoshoot'`, `result_image_url = trendfy.image_url`, `created_at` preserved. Before inserting, HEAD-check each URL to detect expiry. Mark expired URLs with a `expired = true` flag (new nullable boolean column on `superapp_generations`). Log: N results migrated, N expired. The UI (Task 5) renders expired results with a placeholder.

#### Task 4: Photo Library Save (Capacitor)
Install `@capacitor-community/media` (or `@capacitor/filesystem` + Photos framework). After a successful photoshoot generation, download the Replicate result URL to a temp file, then save to the device photo library. Wrap in an adapter service (`PhotoLibraryService`) so the Capacitor call doesn't leak into the photoshoot page directly (ACL pattern — per Task 4 UX-revamp precedent). On web: skip silently (no photo library API). On iOS: request permission, save, show toast "Saved to Photos". Add `data-test="save-to-photos"` on any visible save trigger.

#### Task 5: History UI — Migrated Results + Model Label
Extend the photoshoot history (contact-sheet component from UX revamp Task 4) to render migrated Trendfy results alongside new Bubls generations — unified by `feature = 'photoshoot'` in `superapp_generations`. Expired results show a placeholder thumbnail with "Image expired" overlay. Add active model label to the photoshoot page header: "Model: Sam v3a" (read from `superapp_lora_models` where `is_active = true`). If no model: show "No model" with a setup CTA (deferred — just the label for v1).

#### Task 6: Integration Test + TestFlight QA
End-to-end test: run migration scripts against a test DB seeded with Trendfy fixture data → verify user count, model count, result count, expired-URL detection. Verify photo-library save on a real iOS device via TestFlight. Verify history shows both old Trendfy results and new Bubls generations sorted by date. Verify expired-result placeholder renders. Zero regression on existing photoshoot flow (immersive mode, contact sheet, progress portrait from UX revamp).

---

## Success Criteria

- ✅ All 7 Trendfy users with trained models can generate a photo in Bubls on TestFlight
- ✅ Generated image appears in the iOS photo library after generation
- ✅ Trendfy's 76 historical results are browsable in Bubls photoshoot history
- ✅ No new Replicate training costs — purely reusing existing models
- ✅ Expired Replicate URLs show placeholder, not broken images
- ✅ Active model version label visible on photoshoot page
- ✅ Photo-library save wrapped in adapter service (ACL — no direct Capacitor call in page)
- ✅ Zero regression on existing photoshoot flow

---

## Non-Goals

- ❌ Self-serve LoRA training
- ❌ Multi-scenario generation
- ❌ Payment migration
- ❌ Model picker (auto-select most recent)
- ❌ Cloud storage

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
