---
sidebar_position: 3
---

# 🏗️ Bubls App Store Launch – Solution Architecture

**Purpose**: Technical design for monetization, voice input, sharing, and App Store submission.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This epic adds three new server-side modules (`billing`, `usage`, `share-tracking`), two new Capacitor plugin integrations (`@capacitor-community/speech-recognition`, `@capacitor/share`), and one new Angular feature page (`upgrade`). The existing Text, Photoshoot, and Picks pages gain new UI elements (mic button, share buttons, usage meter) but no structural changes.

The payment flow is deliberately external: Stripe Checkout handles card collection, SCA, and receipt emails. The backend stores subscription state, not payment details. This avoids PCI scope entirely. The webhook is the source of truth — the client never writes subscription state; it only reads it via `GET /api/billing/status`.

Usage metering is server-authoritative. The client shows a counter for UX ("7/10 remaining") but the server enforces at the endpoint level. Free-tier requests that exceed the daily cap receive a 429 with a structured error body. The client interprets the 429 and routes to the paywall. This matches the architecture principle: "Client checks for UX, server enforces."

Voice input uses on-device speech recognition via the Capacitor community plugin. No audio leaves the device. No API cost. No latency. The transcription result fills the textarea; the user then triggers any rewrite mode. The mic is a new input modality, not a new AI operation — the backend doesn't know or care whether the textarea was typed or spoken.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = bounded context | `billing/` owns subscription state. `usage/` owns metering. Text page owns the mic button. No cross-feature imports |
| Adapter at every boundary | `SubscriptionService` adapts Stripe state → `plan` signal. `VoiceInputService` adapts Capacitor plugin → transcription. `ShareService` adapts `@capacitor/share` → share intent. Mock mode via env flag for all three |
| Server enforces, client hints | Usage limit enforced at `POST /api/text/rewrite` with 429. Client shows counter and paywall as UX layer |
| Feature guard → paywall, never 404 | `proGuard` navigates to `/upgrade` with return URL. Upgrade page shows pricing + CTA. Never a blank screen or error |
| ORM always | `Subscription`, `UsageCounter` as SQLModel entities. Alembic migrations. No raw SQL |
| Magic link auth | Stripe customer linked via email from magic-link user. No sessions, no OAuth |
| Not-yet-built is the right state | No billing portal UI (link to Stripe portal). No refund automation. No analytics dashboard. No IAP (Stripe web checkout first) |

---

## Component Design

### Task 1: Stripe Subscription Backend

**Purpose**: Payment infrastructure — Stripe Checkout sessions, webhook processing, subscription state in Neon.

**Components**:
- `server/modules/billing/__init__.py` — Flask blueprint registration
- `server/modules/billing/routes.py` — three endpoints: `create-checkout-session`, `webhook`, `status`
- `server/modules/billing/service.py` — business logic: create Stripe customer, map webhook events to subscription state transitions
- `server/modules/billing/models.py` — SQLModel `Subscription` entity with `plan` enum, `status` enum, Stripe IDs, period timestamps
- `server/modules/billing/dto.py` — generated from OpenAPI: `CheckoutSessionRequest`, `CheckoutSessionResponse`, `BillingStatusResponse`, `WebhookEvent`
- `server/openapi/billing.yaml` — OpenAPI spec for the three endpoints
- `migrations/versions/XXXX_add_subscriptions_table.py` — Alembic migration

**Patterns**: Adapter (Stripe SDK → subscription state). Anti-Corruption Layer (webhook event shapes mapped to domain model, Stripe response format never leaks into billing service).

**Key decisions**:
- Stripe customer created lazily on first checkout, not on user registration — avoids phantom customers for users who never pay
- Webhook is the sole writer of subscription state — client reads but never writes
- `stripe.Webhook.construct_event` verifies every webhook payload — unsigned payloads rejected with 400

### Task 2: Paywall UI + Feature Guard

**Purpose**: Gate Pro features behind a purchase flow that feels like an upgrade, not a wall.

**Components**:
- `src/app/services/subscription.service.ts` — Adapter: `GET /api/billing/status` → `plan: Signal<'free' | 'pro'>`, `isPro: Signal<boolean>`, `refresh()` method
- `src/app/pages/upgrade/upgrade.page.ts` — standalone OnPush component: pricing table, feature comparison, CTA opens Checkout URL
- `src/app/pages/upgrade/upgrade.page.scss` — warm gradient background (matches onboarding foyer), Cormorant headings
- `src/app/guards/pro.guard.ts` — `canActivate` checks `isPro()`, navigates to `/upgrade?returnUrl=` if false
- `src/app/features/text/text.page.ts` — chain mode buttons wrapped with pro guard check, show lock icon + "Pro" badge if free

**Patterns**: Adapter (`SubscriptionService`). Registry (feature guard keyed on plan). Feature guard with null object (paywall page, never 404).

### Task 3: Usage Metering Enforcement

**Purpose**: Server-side daily limits for free-tier users. Pro users uncapped.

**Components**:
- `server/modules/usage/__init__.py` — Flask blueprint
- `server/modules/usage/middleware.py` — `check_usage_limit` decorator: reads plan from subscription, reads today's count, returns 429 if free + count ≥ 10
- `server/modules/usage/models.py` — SQLModel `UsageCounter` entity: `user_id`, `feature`, `date`, `count`, unique constraint
- `server/modules/usage/service.py` — `increment(user_id, feature)` with `INSERT ... ON CONFLICT DO UPDATE`, `get_remaining(user_id, feature)` for client hint
- `migrations/versions/XXXX_add_usage_counters_table.py` — Alembic migration
- `src/app/features/text/components/usage-meter.component.ts` — "7/10 remaining" pill, hidden for Pro, red at ≤2 remaining

**Patterns**: Middleware decorator on existing text endpoints. Atomic upsert for counter increment. Feature-scoped UI component.

### Task 4: Voice Input on Text Page

**Purpose**: New input modality — speech-to-textarea, no backend changes.

**Components**:
- `src/app/services/voice-input.service.ts` — Adapter wrapping `@capacitor-community/speech-recognition`: `startListening()`, `stopListening()`, `isListening: Signal<boolean>`, `transcript: Signal<string>`, `hasPermission: Signal<boolean>`. Mock mode returns fixture text
- `src/app/features/text/components/mic-button.component.ts` — standalone OnPush: microphone icon, pulse animation while listening, waveform amplitude indicator, Pro badge if free user, tooltip if permission denied
- `src/app/features/text/components/mic-button.component.scss` — ring pulse keyframe (honors `prefers-reduced-motion`), frosted glass circle
- `src/app/features/text/text.page.ts` — mic button integrated next to textarea. On transcript, fills textarea (append or replace based on toggle). Haptic on start/stop via `@capacitor/haptics`
- `capacitor.config.ts` — add `@capacitor-community/speech-recognition` plugin config, iOS permission descriptions

**Patterns**: Adapter (`VoiceInputService`). Strategy-ready (swap to Whisper API later without touching UI). Feature-gated via subscription service (not route guard — mic is on the Text page, gated at the component level).

### Task 5: Share Sheet Integration

**Purpose**: Native sharing from all three output surfaces.

**Components**:
- `src/app/services/share.service.ts` — Adapter wrapping `@capacitor/share`: `shareText(text, subject)`, `shareImage(filePath, subject)`, `shareUrl(url, title)`. Mock mode logs intent
- `src/app/features/text/components/share-button.component.ts` — appears after output, shares text
- `src/app/features/photoshoot/components/share-button.component.ts` — shares image file from result
- `src/app/features/picks/pick-detail.page.ts` — share pill added next to save pill, shares URL + title
- `migrations/versions/XXXX_add_shared_at_to_generations.py` — Alembic: nullable `shared_at` timestamp on `superapp_generations`
- `server/modules/text/routes.py` — `POST /api/text/share-event` logs share for tracking

**Patterns**: Adapter (`ShareService`). Observer (share event published for analytics). Feature-scoped components (no shared `ShareButton` — each feature owns its share UI because the payload shape differs).

### Task 6: App Store Submission

**Purpose**: Package and submit to App Store Connect.

**Components**:
- `fastlane/Snapfile` — screenshot capture config for 6.7", 6.1", 5.5" devices
- `fastlane/metadata/en-US/description.txt` — App Store description
- `fastlane/metadata/en-US/keywords.txt` — search keywords (100 char limit)
- `fastlane/metadata/en-US/privacy_url.txt` — privacy policy URL
- `fastlane/screenshots/` — light + dark screenshots for each feature
- `landing/privacy.html` (new) — privacy policy page
- `.github/workflows/release.yml` — archive + upload to App Store Connect via Fastlane

**Patterns**: Fastlane for screenshot automation and metadata management. CI/CD for archive + upload.

---

## Execution Flow

```
[Phase 1 — independent]
   Task 1 (Stripe backend) ──→ Task 2 (Paywall UI)
                              → Task 3 (Usage metering)
   Task 4 (Voice input)
   Task 5 (Share sheet)

[Phase 2 — convergence]
   Tasks 2, 3, 4, 5 complete
              │
              ▼
   Task 6 (App Store submission)
```

Phase 1 runs three independent work streams: payments (Task 1 → 2, 3), voice (Task 4), and sharing (Task 5). Phase 2 is the integration point where all features must be stable before packaging for App Store review.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Stripe Checkout vs. StoreKit 2 | Stripe Checkout (web-hosted) | Avoids Apple's 30% cut. StealthGPT, ChatGPT, and other AI apps use web billing. If Apple rejects, add IAP as fallback — but test the web path first. Stripe key already provisioned |
| On-device speech vs. Whisper API | `@capacitor-community/speech-recognition` (on-device) | Zero API cost, zero latency, works offline, supports 60+ languages. Whisper is better quality but adds $0.006/min cost and requires network. On-device is good enough for "speak a paragraph" use case |
| Single `usage_counters` table vs. per-feature tables | Single table with `feature` column | One table, one query pattern, one migration. Feature column allows per-feature limits later (e.g., 5 photoshoots/day) without schema changes |
| Share button per feature vs. shared component | Per-feature components | Each feature shares different content types (text, image, URL). A shared component would need a union type and conditional rendering — more complex than three 20-line components |
| Subscription state in Neon vs. check Stripe on every request | State in Neon, synced via webhook | Checking Stripe on every request adds 200ms+ latency and couples availability to Stripe's uptime. Webhook sync is eventually consistent (seconds) but fast and resilient |
| Lazy Stripe customer creation vs. on registration | Lazy (first checkout) | Prevents phantom customers. Most free users never upgrade; creating a Stripe customer for each wastes API calls and pollutes the Stripe dashboard |

---

## Data Model

```
subscriptions
├── id (UUID, PK)
├── user_id (FK → superapp_users.id)
├── stripe_customer_id (varchar, unique)
├── stripe_subscription_id (varchar, unique, nullable)
├── plan (enum: free, pro)
├── status (enum: active, cancelled, past_due, trialing)
├── current_period_end (timestamp, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)

usage_counters
├── id (UUID, PK)
├── user_id (FK → superapp_users.id)
├── feature (varchar: "text_rewrite", "text_generate", "photoshoot")
├── date (date)
├── count (int, default 0)
└── UNIQUE(user_id, feature, date)

superapp_generations (modified)
└── shared_at (timestamp, nullable) — added column
```

---

## Security Considerations

| Surface | Threat | Mitigation |
|---------|--------|------------|
| Webhook endpoint | Spoofed Stripe events | `stripe.Webhook.construct_event` with `STRIPE_WEBHOOK_SECRET` — unsigned payloads rejected |
| Billing status | Privilege escalation (forge pro status client-side) | Server enforces plan check on every text endpoint; client signal is UX only |
| Microphone | Recording without consent | iOS permission dialog on first use; rationale string explains purpose; permission state tracked in service |
| Usage counter | Race condition (parallel requests bypass limit) | `INSERT ... ON CONFLICT DO UPDATE SET count = count + 1` is atomic in Postgres |
| Share tracking | Replay attacks on share event endpoint | Idempotent write (upsert on generation_id); no business logic depends on share count |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

