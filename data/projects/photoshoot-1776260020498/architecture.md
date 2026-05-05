# 🏗️ Solution Architecture: Photoshoot

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The photoshoot system is a thin orchestration layer connecting three proven pieces: an Ionic shell for capture, a Flask API for routing, and Replicate's hosted inference for LoRA generation. The key architectural insight is that personalization lives entirely in the database — a single foreign key mapping each user to their pre-trained model — not in application logic. The app treats every user identically; the model lookup is what makes each result personal.

The super app shell is the load-bearing decision. Rather than building a standalone photoshoot app, the system invests its complexity budget in a tab-routed shell that /photoshoot inhabits as the first tenant. This means auth, payments, and navigation are shared concerns that future routes (/humanize, /headshot) inherit for free. The shell's marginal cost is ~2 days upfront; the payoff is near-zero cost for every subsequent feature.

The entire backend is stateless by design. Flask receives an image and a user ID, resolves the model, calls Replicate, and returns a URL. No queues, no workers, no persistent connections. At 15 users generating a handful of images per day, this simplicity is the architecture — complexity would be premature and would slow the only thing that matters: getting real photos in front of real people to test retention.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Reuse over build | Every major component — shell (Bubls), LoRA pipeline (Trendfy), payments (Humanize-me) — is extracted from a shipped product, not built from scratch |
| Personalization via data, not code | The user-to-model mapping in Neon is the only thing that differentiates one user's experience from another; application code is identical for all users |
| Honest UX over optimized infra | Replicate cold-starts cause 10-30s latency; the architecture addresses this with loading states and expectation-setting, not caching or warm pools |
| Shell-first investment | Shared concerns (auth, nav, gating) are solved once in the shell; features are routes that inherit everything |
| Manual before automated | 15 hand-trained models before building self-serve training; validates the experience without the pipeline |

---

## System Boundaries

### What This System Includes

- Tab-routed Ionic shell with feature gating and shared auth
- User identity layer with user-to-LoRA-model mapping in Neon Postgres
- Photo capture via Capacitor Camera plugin and file upload
- Flask orchestration endpoint: image in, Replicate inference, result URL out
- Before/after result display with gallery of past generations
- Web deployment (Coolify) and iOS deployment (TestFlight) from a single codebase

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Self-serve LoRA training | Month 2 scope; manual training validates the experience without pipeline complexity |
| Style selection or generation parameters | One default style reduces decision fatigue and ships faster; style variety follows retention signal |
| Image storage service | Replicate returns hosted URLs; building custom storage at 15 users adds cost without value |
| Android build | Capacitor supports it, but iOS-only for Month 1 limits QA surface to one platform |
| Real-time generation optimization | At 15 users, cold-start latency is a UX problem solved with honest loading states, not an infra problem solved with warm pools |
| Analytics pipeline | Direct Neon queries answer every Month 1 question; a dashboard is premature |

---

## Component Design

### Super App Shell

**Purpose**: Provides the shared substrate — navigation, auth, feature gating — so that each AI feature is just a route with a tab.

**Key Parts**:
- `AppComponent` — Root layout with Ionic tab bar; each tab maps to a lazy-loaded feature route
- `AuthService` — Handles authentication flow, session persistence, and exposes the current user as a signal
- `FeatureGateGuard` — Route guard that checks `enabled_features` on the user object before activating a route; unauthorized users see a waitlist or upgrade prompt
- `UserModel` — Typed representation of the user record including `enabled_features` dict and `lora_model_id` foreign key

**Patterns**: Signal-based state (Angular 19 signals, not RxJS subjects), standalone components with OnPush change detection, lazy-loaded routes per feature. The shell is intentionally thin — under 10 files — so that feature routes own their own complexity.

### Auth + Identity Layer

**Purpose**: Maps a human (email) to a user record to a LoRA model, forming the personalization chain.

**Key Parts**:
- `AuthService` — Wraps the chosen auth provider, exposes login/logout/session signals
- `users` table in Neon — Stores user identity, `enabled_features`, and `lora_model_id`
- `lora_models` table in Neon — Stores Replicate model identifiers, training metadata, and the user foreign key

**Patterns**: The auth decision (Supabase vs. magic link) is the highest-impact design choice in this layer. See Design Decisions below for the trade-off analysis. Regardless of choice, the contract is the same: after authentication, the app holds a user ID that resolves to a LoRA model via a single database lookup.

### Photo Capture + Upload

**Purpose**: Gets an image from the user's device to the backend, handling both native camera and file picker paths.

**Key Parts**:
- `PhotoCaptureComponent` — Presents camera and upload options; uses Capacitor Camera plugin for native capture, standard file input for gallery selection
- `PhotoService` — Handles image encoding, compression (if needed), and upload to the Flask endpoint

**Patterns**: Capacitor's Camera plugin abstracts iOS-specific permissions and camera access behind a single API call. The component doesn't know or care whether it's running in a browser or on a native device — Capacitor handles the bridge. Images are sent as multipart form data to keep the Flask endpoint simple.

### Generation Pipeline (Backend)

**Purpose**: Receives an image and user ID, resolves the LoRA model, calls Replicate inference, and returns the result.

**Key Parts**:
- `generate` endpoint in Flask — The single orchestration endpoint; stateless, no queue, no async workers
- `ModelResolver` — Queries Neon for the user's `lora_model_id` and returns the Replicate model identifier
- `ReplicateClient` — Wraps the Replicate prediction API; sends the input image and model ID, polls for completion, returns the output URL
- `generations` table in Neon — Records each generation (user ID, original URL, result URL, timestamp) for gallery display and usage tracking

**Patterns**: Synchronous request-response. The Flask endpoint blocks while Replicate processes (10-30s typical, up to 60s on cold start). At 15 concurrent users this is fine — Python's threading handles the overlap. The frontend shows a loading state with honest latency expectations. If Replicate fails, the endpoint returns a structured error that the frontend translates into actionable user feedback.

### Result Display + Gallery

**Purpose**: Shows the user their enhanced photo and maintains a history of past generations.

**Key Parts**:
- `ResultComponent` — Before/after comparison view with swipe or slider interaction
- `GalleryComponent` — Grid of past generations pulled from Neon via a list endpoint
- `GalleryCacheService` — Adapted from Trendfy's existing implementation; uses `shareReplay` to avoid redundant API calls when switching between tabs

**Patterns**: The gallery is read-heavy and write-rare (a user generates maybe 3-5 images per session). Caching at the service layer with cache invalidation on new generation is sufficient. No pagination needed at 15 users.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | Angular 19 + Ionic 8 | Proven in Bubls (shipped to TestFlight in one day); tab routing and native UI components come free |
| Native bridge | Capacitor 8 | Single codebase → web + iOS; Camera plugin handles permissions and capture; already working in Bubls |
| Backend | Flask (Python) | Trendfy's existing Replicate integration is Flask; rewriting in another framework adds risk for zero user-facing value |
| Database | Neon Postgres (shared instance) | Already running, already has auth tables from other products; adding two tables costs nothing |
| AI inference | Replicate (hosted LoRA) | Trendfy's LoRA training and inference pipeline is battle-tested; no reason to self-host at 15 users |
| Auth | Supabase Auth (recommended) | See Design Decisions; session management, JWT, and OAuth are table stakes for a payment-enabled app |
| Payments | Stripe | Already integrated in Humanize-me; webhook handler and subscription tiers transfer directly |
| Web hosting | Coolify | Running, proven, zero-config deploys via Docker Compose |
| iOS distribution | TestFlight | Pipeline working from Bubls; App Store Connect account active |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Supabase Auth over magic links** | The super app will have Stripe payments, which require persistent sessions, token refresh, and account recovery. Magic links work for low-stakes apps (Bubls), but payment-enabled apps need proper session management. Supabase is already implemented in Humanize-me, so the integration cost is known. | Adds a Supabase dependency and slightly more complex auth flow vs. a simple UUID token. If the super app never adds payments, this is over-engineered — but the epic explicitly scopes payments. |
| **Shared Neon instance over dedicated database** | Three products already use this Neon instance. Adding two tables (users, generations) to an existing database avoids provisioning, connection string management, and cost. Schema isolation via naming conventions is sufficient at this scale. | Risk of noisy-neighbor if another product hammers the DB, but at 15 users the load is negligible. Migration to a dedicated instance is trivial if needed. |
| **Synchronous Replicate calls over async queue** | At 15 users, the maximum concurrent generation requests is realistically 2-3. A synchronous Flask endpoint that blocks during Replicate inference is simpler than adding Redis, Celery, or polling. The frontend handles the wait with loading UX. | If the user closes the app mid-generation, the result is lost (no background job to complete it). Acceptable at 15 users; a queue becomes necessary at scale. |
| **Replicate-hosted URLs over custom image storage** | Replicate returns hosted URLs for generated images. Storing these URLs in Neon rather than downloading and re-hosting avoids S3/R2 setup, egress costs, and upload logic. | Replicate may expire URLs or change hosting policies. Mitigation: the URL expiry is documented and long enough for Month 1. If URLs expire, a migration to download-and-store is straightforward. |
| **One default style over style picker** | Reduces the generation pipeline to a single path: image in, styled image out. No UI for style selection, no backend logic for style routing. Ships faster and forces the team to pick the best single style rather than offering mediocre variety. | Users who dislike the default style have no recourse. Acceptable risk: if the core experience works, adding styles is a UI change, not an architecture change. |
| **Manual LoRA pre-training over self-serve** | Self-serve training requires an upload flow, training status tracking, webhook handling, and error recovery — easily a week of work. Manual training for 15 users takes 3 days and creates the "instant magic" first impression where the model is already waiting when the user opens the app. | Does not scale beyond 15 users. Explicitly acceptable per the [Epic](./epic.md) — this epic validates the experience, not the pipeline. |
| **Feature gating via user object over middleware** | The `enabled_features` dict on the user record is checked by a route guard on the frontend and a decorator on the backend. This is simpler than a feature flag service and sufficient for gating routes by subscription tier. | No audit trail, no gradual rollout, no A/B testing. These are Month 2+ concerns if retention validates the product. |

---

## Patterns

### User-to-Model Resolution

**When to use**: Every generation request — the system must resolve which LoRA model belongs to the requesting user.

**How it works**: The authenticated user's ID is sent with every generation request. The Flask endpoint queries the `lora_models` table for the model associated with that user ID. If no model exists (user #16 who wasn't pre-trained), the endpoint returns a clear "no model available" response that the frontend renders as a waitlist prompt. The lookup is a single indexed query with sub-millisecond latency.

**Example in this system**: User opens /photoshoot, takes a photo. The `PhotoService` sends the image and user ID to Flask. Flask calls `ModelResolver`, which returns the Replicate model identifier. If the user has no model, the response tells the frontend to show a waitlist message instead of a generation result.

### Honest Loading UX

**When to use**: During any Replicate inference call, which takes 10-30 seconds (up to 60 seconds on cold start).

**How it works**: The frontend enters a loading state immediately on submission and displays progress information that sets realistic expectations — not a spinner with no context, but a message acknowledging the generation takes time. The backend streams progress if available, or the frontend uses a timed sequence of messages. On failure, the backend returns a structured error (model unavailable, Replicate timeout, rate limit) that the frontend maps to a human-readable message with a retry option.

**Example in this system**: User submits a photo. The UI shows "Your AI model is creating your photo — this usually takes 15-30 seconds." If Replicate cold-starts, the wait extends but the user isn't staring at an unexplained void. On failure: "Generation didn't complete — tap to try again" with the specific error logged for debugging.

### Shell-as-Platform

**When to use**: When adding any new AI feature to the super app.

**How it works**: Each feature is a lazy-loaded Angular route with its own module boundary. The shell provides auth (user identity), navigation (tab bar entry), and gating (subscription check). A new feature adds a route config entry, a tab icon, and its own component tree. It does not touch auth, payments, or navigation code. The `enabled_features` dict on the user object controls which tabs are visible and which routes are accessible.

**Example in this system**: /photoshoot is the first route. When /humanize is added in Month 2, it gets a new tab entry, a new lazy-loaded route, and its own components. It inherits the authenticated user object (including subscription tier) without any integration work. The shell's tab bar automatically shows or hides the tab based on the user's `enabled_features`.

---

## Execution Flow

```
[Phase 1 — Foundation]        [Phase 1 — Parallel]
  Shell + Auth + Gating    ║    Pre-train 15 LoRA models
  (Task 1: 2 days)         ║    (Task 2: 3 days)
         │                  ║           │
         ▼                  ║           │
[Phase 2 — Integration]     ║           │
  Photo Capture + Pipeline  ║           │
  (Task 3: 2 days)          ║           │
         │                              │
         ▼                              ▼
[Phase 3 — Ship]
  Deploy Web + iOS, Invite 15 Testers
  (Task 4: 1 day)
```

Task 1 (shell + auth) and Task 2 (pre-train models) run in parallel because they have no dependencies on each other. The shell needs a working auth system and user-to-model mapping schema; the models need trained weights and database entries. Neither blocks the other.

Task 3 (generation pipeline) depends on Task 1 because it needs authenticated user identity to resolve LoRA models. It does not strictly depend on Task 2 — the pipeline can be built and tested with a single developer's model before all 15 are ready.

Task 4 (deploy + distribute) gates on all three prior tasks. The app must have auth, trained models, and a working pipeline before inviting testers. This is a single-day task because both deployment pipelines (Coolify for web, TestFlight for iOS) are already proven.

The critical path runs through Task 1 → Task 3 → Task 4 (5 days). Task 2 floats alongside with 1 day of slack, assuming it starts on Day 1.

---

## Data Model

The system adds two tables to the shared Neon Postgres instance alongside existing tables from other products.

**`users`** — Core identity record. Stores email, auth provider ID (Supabase), `enabled_features` as a JSONB dict, subscription tier, and timestamps. The `enabled_features` field is the gating mechanism: `{"photoshoot": true, "humanize": false}` determines which routes the user can access.

**`lora_models`** — Maps a user to their Replicate LoRA model. Stores user ID (foreign key), Replicate model identifier, training metadata (number of training images, training date), and a status flag. For Month 1, all 15 rows are manually inserted. The status flag exists so the system can distinguish "model exists and is ready" from "model is training" when self-serve is added later.

**`generations`** — Records each generation event. Stores user ID, original image URL, result image URL, model ID used, generation duration, and timestamp. Serves the gallery view and provides the raw data for retention analysis (query: how many unique users generated images in the last 7 days?).

Schema isolation is by naming convention, not by Postgres schema. All tables share the `public` schema alongside tables from Trendfy and other products. At this scale, this is simpler than managing multiple schemas or connections.

---

## Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Replicate cold starts cause 60s+ waits | Users abandon the app thinking it's broken | Honest loading UX with time estimates; pre-warm models by running a dummy inference before inviting testers |
| Supabase auth integration takes longer than expected | Blocks all downstream tasks | Fallback: ship with magic link auth (2-hour implementation) and migrate to Supabase before adding payments |
| LoRA model quality varies across the 15 testers | Some users get poor results, poisoning first impressions | Validate every model with 3-5 test generations before inviting that user; reject and retrain if quality is below threshold |
| Replicate URL expiration | Gallery images break after expiry period | Monitor expiry policy; if URLs expire within Month 1, add a background job to download and store images |
| User #16 finds the app organically | Broken experience with no model and no explanation | Feature gate: users without a `lora_model_id` see a waitlist prompt, not an error |

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview