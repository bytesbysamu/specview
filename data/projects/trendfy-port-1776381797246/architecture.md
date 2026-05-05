---
sidebar_position: 3
---

# 🏗️ Port Trendfy into Bubls Photoshoot — Architecture

**Purpose**: Technical design for the Trendfy data migration and photo-library integration.

**References**: See [Epic](./epic.md) for scope. See [Analysis](./analysis.md) for constraints.

---

## Overview

This epic is a data migration + one Capacitor plugin, not a feature build. Trendfy's tables sit on the same Neon Postgres instance Bubls reads from. Three Alembic scripts map users → `superapp_users`, models → `superapp_lora_models`, results → `superapp_generations`. One new adapter service wraps `@capacitor-community/media` for photo-library save. The photoshoot UI extends to show migrated history + model label.

---

## System Boundaries

```
┌─────────────────────────────────────────────┐
│  Neon Postgres (shared instance)            │
│  ┌───────────────┐  ┌───────────────────┐   │
│  │ Trendfy tables │  │ Bubls tables      │   │
│  │ users          │  │ superapp_users    │   │
│  │ lora_models    │  │ superapp_lora_    │   │
│  │ generated_     │  │   models          │   │
│  │   images       │  │ superapp_         │   │
│  │ orders         │  │   generations     │   │
│  └───────┬───────┘  └───────┬───────────┘   │
│          │ READ              │ WRITE         │
│          └──────┬────────────┘               │
│                 │                            │
│          Alembic migrations (Tasks 1-3)      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Bubls iOS app                               │
│  ┌──────────────────┐                        │
│  │ Photoshoot page   │                        │
│  │  ├── generate     │──→ Replicate API       │
│  │  ├── save to lib  │──→ PhotoLibraryService │
│  │  ├── history      │    (ACL adapter)       │
│  │  └── model label  │         │              │
│  └──────────────────┘          ▼              │
│                        @capacitor-community/  │
│                        media                  │
└─────────────────────────────────────────────┘
```

---

## Component Design

### Migration Scripts (Alembic, Tasks 1-3)

Three idempotent migrations, each with up + down:

1. **User migration** — reads Trendfy `users`, creates `superapp_users` for new emails, queues magic-link invites. Idempotent: skip existing emails.
2. **Model migration** — reads Trendfy `lora_models` where `replicate_model_id IS NOT NULL`, creates `superapp_lora_models` rows. Sets `is_active = true` on most recent per user.
3. **Result migration** — reads Trendfy `generated_images`, HEAD-checks each URL for expiry, creates `superapp_generations` rows with `feature = 'photoshoot'` + `expired` flag.

All three use SQLAlchemy models — no raw SQL.

### PhotoLibraryService (`src/app/services/photo-library.service.ts`)

Adapter wrapping `@capacitor-community/media`:
- `saveImage(url: string): Promise<void>` — download URL to temp, save to photo library
- On web: no-op (photo library API doesn't exist)
- On iOS: request Photos permission, save, emit `imageSaved` event (Observer)
- **ACL invariant**: only `PhotoLibraryService` imports `@capacitor-community/media`. Pin with structural test (extend existing `architecture-acl-check.mjs`).

### History Extension

Extend the photoshoot contact-sheet component (from UX revamp Task 4) to render unified history:
- Query `superapp_generations WHERE feature = 'photoshoot'` — returns both Trendfy migrations and new Bubls generations
- Sort by `created_at DESC`
- Expired results: show placeholder thumbnail with "Image expired" overlay
- Trendfy results are indistinguishable from Bubls results in the UI — same card shape, same tap behavior

### Model Label

Read `superapp_lora_models WHERE user_id = current AND is_active = true`. Display model name in photoshoot page header: "Model: Sam v3a". If no model: "No model" (no CTA for v1 — deferred to self-serve training epic).

---

## Design Decisions

| Decision | Choice | Why | Rejected |
|---|---|---|---|
| User creation method | Magic-link invite, not password copy | Bubls is magic-link-only (principle). Trendfy passwords are bcrypt — different auth model entirely. | Copy passwords (violates auth principle), auto-login tokens (security risk) |
| Expired URL handling | HEAD-check at migration time + `expired` boolean column | One-time cost at migration, not per-render. Placeholder in UI is cheap. | Re-download all to S3 (scope creep, infra cost), hide expired (loses history signal) |
| Photo save target | Device photo library via Capacitor | No S3/R2 to provision. Phone IS the storage layer. User owns the file. | S3 bucket (infra overhead for v1), app-internal Filesystem (not discoverable by user) |
| Model selection | Auto-select most recent, no picker | 5 of 7 users have exactly 1 model. The 2 with multiple (Sam) can use the most recent. Picker is premature. | Model picker dropdown (UI complexity for 2 users) |

---

## Tech Stack

```
Migrations: Alembic + SQLAlchemy (existing patterns)
Photo save: @capacitor-community/media (new dep)
Frontend:   Extend existing photoshoot components (contact-sheet, page header)
Backend:    No new endpoints — migrations are one-time scripts
```

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)
