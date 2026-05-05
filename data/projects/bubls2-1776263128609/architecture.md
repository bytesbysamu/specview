# 🏗️ Solution Architecture: bubls2

**Purpose**: Long-lived system design document.

**References**: Addresses issues in [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The super app is an evolution, not a rewrite. The existing Bubls codebase — Angular 19, Ionic 8, Capacitor 8 — already proves the stack ships to TestFlight in a day. The architecture extends this shell into a multi-route host where each AI feature is a lazy-loaded route module with its own backend endpoint, while sharing auth, layout, navigation, and user state. The shell is the platform; features are tenants.

The backend follows the same consolidation principle. A single Flask API absorbs the Replicate inference logic from Trendfy and exposes feature-specific endpoints behind a common auth middleware. Neon Postgres serves as the single data store — user records, LoRA model mappings, generation history — accessible from both web and iOS clients through the same API surface. This mirrors the "one shell, many features" philosophy at the API layer.

The critical architectural insight is that the shell must be feature-agnostic. It knows how to authenticate a user, check their enabled features, render a tab bar, and route to a feature module. It does not know what /photoshoot does. This separation means Month 2 routes like /humanize and /headshot slot in without touching shell code — they register a route, declare a tab icon, and the shell handles the rest.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Evolve, don't rewrite | The Bubls codebase becomes the shell; no greenfield project, no migration risk |
| Features are routes | Each AI capability is a self-contained lazy-loaded route with its own service layer — the shell provides infrastructure, not behavior |
| One auth, one user, one database | Consolidate three incompatible auth approaches into a single user model on Neon Postgres, eliminating per-product account fragmentation |
| Deliberately unscalable first | Manual LoRA training, hand-picked testers, no self-serve — optimize for signal quality over infrastructure maturity |
| Platform parity from day one | Every feature must work on both web (Coolify) and iOS (TestFlight) from the same codebase — no web-only or native-only paths |

---

## System Boundaries

### What This System Includes

- Angular/Ionic/Capacitor shell with tab navigation, shared layout, and route registration
- Auth layer with user model, feature gating middleware, and session management
- /photoshoot route: camera capture, photo upload, Replicate LoRA inference, result gallery
- Flask API with auth middleware and /photoshoot inference endpoint
- Neon Postgres schema for users, LoRA model mappings, and generation history
- Dual deployment pipeline: Docker Compose to Coolify (web) and xcodebuild to TestFlight (iOS)

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Self-serve LoRA training | Manual training for 15 users is the validation mechanism; automation adds weeks of work before any signal exists |
| Stripe billing integration | First 15 testers are free; wiring payments before proving retention wastes effort on infrastructure that may never matter |
| Style picker or prompt customization | One default style isolates the variable being tested (personalized LoRA quality) from confounding UX complexity |
| Android build | Capacitor supports Android, but splitting QA across two platforms doubles testing burden for 15 users — iOS only until signal justifies it |
| Trendfy migration | The May 1 verdict determines what transfers; the shell accommodates either outcome but doesn't pre-commit to one |

---

## Component Design

### Shell Framework

**Purpose**: Provides the host environment that all feature routes inherit — navigation, layout, auth guards, and the user state that drives feature gating.

**Key Parts**:
- `AppComponent` — Root component with Ionic tab bar, dynamic route registration, and dark theme globals
- `AuthGuard` — Route-level guard that checks the user's `enabled_features` map before activating a feature route
- `UserStore` — Signal-based reactive store holding the current user object, including auth state, subscription tier, and enabled features
- `ShellLayoutComponent` — Shared header, navigation tabs, and content area that feature routes render into

**Patterns**: Each feature route is a standalone lazy-loaded module. The shell discovers available routes from a registry — a simple array of route configs declaring path, tab icon, label, and feature key. Adding a new feature means adding one entry to this registry and one lazy route module. The shell never imports feature-specific code directly.

### Auth + User Model

**Purpose**: Replaces three incompatible auth systems (Bubls magic links, Humanize-me Supabase, Trendfy email-only) with a single approach that supports both the super app's immediate needs and future payment integration.

**Key Parts**:
- `AuthService` — Handles signup, login, session persistence, and token refresh
- `UserModel` — Database record with id, email, auth metadata, `enabled_features` map, and optional Stripe customer reference
- `FeatureGateMiddleware` — Flask-side middleware that validates JWT and checks feature access before processing API requests

**Patterns**: The user model carries an `enabled_features` dictionary keyed by route name (e.g., `photoshoot: true`). For Month 1 this is manually set during tester onboarding. The same field becomes Stripe-driven in Month 2 — the middleware doesn't care who sets the flag, only that it's present. This decouples gating logic from billing logic.

**Auth Decision — Supabase vs Magic Links**: Supabase auth wins despite adding a dependency. The reasoning: Month 2 requires Stripe integration, which needs reliable session management, JWT validation, and password reset flows. Magic links work for throwaway signups but create friction when users need to manage a subscription. Supabase is already implemented in Humanize-me, so the integration cost is known. The trade-off is an external dependency for 15 users who don't strictly need it — but building magic links now and replacing them with Supabase in Month 2 is more expensive than starting with Supabase. If the May 1 Trendfy verdict brings its user base into the super app, Supabase also handles the migration path more cleanly than a custom magic link system.

### /photoshoot Feature

**Purpose**: The lead route that validates the super app concept — personalized LoRA inference behind a simple camera interface.

**Key Parts**:
- `PhotoshootPage` — Ionic page component with three entry points: camera capture, photo upload, and gallery view
- `CameraService` — Wraps Capacitor Camera plugin for native capture and falls back to file input on web
- `PhotoshootApiService` — Handles photo upload to Flask backend and polls/streams inference results
- `GalleryComponent` — Displays past generations with before/after comparison, reuses Trendfy's `GalleryCacheService` pattern for client-side caching

**Patterns**: The camera flow follows a capture → upload → wait → display pipeline. The Capacitor Camera plugin returns a base64 or file URI; the service normalizes this to a standard upload payload regardless of platform. The Flask endpoint receives the image, resolves the user's LoRA model ID from Neon, dispatches to Replicate, and returns the result URL. Result metadata (original URL, result URL, timestamp) persists to Neon for the gallery.

### Flask API

**Purpose**: Single backend serving all feature routes with shared auth middleware, replacing the per-product Flask instances (Trendfy on port 3003, Humanize-me on its own port).

**Key Parts**:
- `app.py` — Flask application with CORS, auth middleware, and feature-specific route blueprints
- `PhotoshootBlueprint` — Endpoint for photo upload + Replicate inference, absorbing Trendfy's existing inference logic
- `ReplicateService` — Wrapper around Replicate API for LoRA inference, adapted from Trendfy's generate module
- `UserRepository` — Neon Postgres queries for user lookup, LoRA model resolution, and generation history

**Patterns**: Each feature registers as a Flask Blueprint with its own routes. The auth middleware validates the JWT (issued by Supabase) and attaches the user object to the request context. Feature gating happens at the middleware level — if the user doesn't have the feature enabled, the request is rejected before reaching the Blueprint. This means feature Blueprints can assume an authenticated, authorized user.

### Data Layer

**Purpose**: Neon Postgres as the single source of truth for users, LoRA models, and generation history — consolidating the scattered data across Trendfy's tables and Humanize-me's Supabase instance.

**Key Parts**:
- `users` table — Core user record with Supabase auth ID, email, `enabled_features` JSONB column, and optional Stripe references
- `lora_models` table — Maps user IDs to Replicate model identifiers, training metadata, and default style parameters
- `generations` table — Records each inference run with user ID, original image reference, result image reference, model used, and timestamp
- Neon's connection pooler — Handles concurrent connections from both web and mobile clients through the existing pooler endpoint

**Patterns**: The `enabled_features` column is JSONB rather than a join table. For 15 users with 1-3 features each, a JSONB column is simpler to query, update, and reason about than a normalized many-to-many. If feature count grows beyond 10 or queries need to filter users by feature, a join table is the obvious next step — but that's a Month 3 concern at earliest.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | Angular 19 + Ionic 8 | Already proven in Bubls; Ionic provides native-feel components and Capacitor bridge without learning a new framework |
| Native bridge | Capacitor 8 | Same codebase deploys to web and iOS; Camera plugin provides native camera access; already configured in Bubls with working TestFlight pipeline |
| Backend | Flask (Python) | Trendfy's Replicate integration is already in Flask; rewriting in Express adds migration risk for no Month 1 benefit |
| Database | Neon Postgres (shared instance) | Already running, already paid for, already hosts Trendfy data; connection pooler handles concurrent mobile clients |
| Auth | Supabase Auth | JWT-based sessions, password reset, OAuth-ready; already implemented in Humanize-me; supports Month 2 Stripe integration |
| AI inference | Replicate (LoRA) | Trendfy's pipeline already trains and runs LoRA models on Replicate; per-inference pricing (~$0.01-0.05) is viable at 15-user scale |
| Web deployment | Docker Compose → Coolify | Humanize-me's pipeline works; no new infrastructure to provision |
| iOS deployment | xcodebuild → TestFlight | Bubls pipeline works; CLI-based archive and upload already automated |
| Image storage | Replicate output URLs + Neon metadata | Replicate hosts generated images temporarily; for Month 1, URLs in the database suffice without a dedicated storage layer |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Evolve Bubls codebase rather than start fresh | Bubls already has a working Capacitor 8 + Ionic 8 + Angular 19 shell with TestFlight pipeline; starting fresh means rebuilding all of this for zero benefit | Inherits any Bubls-specific assumptions (event card components, signal patterns) that may not fit the super app model — some cleanup needed |
| Supabase Auth over magic links | Magic links work for throwaway signups but don't support the subscription management, session persistence, and OAuth that Month 2 requires; Supabase is already proven in Humanize-me | Adds an external auth dependency for 15 users who could work with simpler auth; Supabase free tier limits (50K MAU) are irrelevant at this scale but become a cost factor at growth |
| Flask over Express for the unified backend | Trendfy's Replicate LoRA integration is in Python/Flask; the inference logic, model config, and image handling are already written and tested with real orders | JavaScript/TypeScript would unify the stack with Angular, but rewriting working Python inference code in JS adds a week of migration work and regression risk |
| JSONB `enabled_features` over normalized join table | 15 users, 1-3 features each — a JSONB column is a single read, a single update, and zero joins; the simplicity-to-scale ratio overwhelmingly favors JSONB at this size | Loses queryability ("find all users with /photoshoot enabled") — acceptable because Month 1 has 15 users queryable by eye |
| Repurpose `ch.bubls.app` bundle ID rather than register new | A new bundle ID means a new App Store Connect record, new provisioning profile, new TestFlight group; repurposing Bubls avoids all of this and existing TestFlight testers get the update automatically | Existing Bubls TestFlight users see a different app after update; acceptable because the current tester pool is just Sam and the Bubls concept is being absorbed into the super app |
| Replicate-hosted image URLs over dedicated object storage | Replicate returns publicly accessible URLs for generated images; storing these URLs in Neon is sufficient for 15 users generating a handful of images each | Replicate URLs may expire or become unavailable; at scale this needs S3/R2 mirroring, but for Month 1 the simplicity of not managing a storage layer outweighs the durability risk |
| Single default style over style picker | Isolates the variable being tested — does personalized LoRA inference create a "wow" reaction? Adding style choices confounds feedback ("was the result bad because of the model or the style?") | May bore testers faster; mitigated by the personal model itself being the novelty, not the style options |

---

## Patterns

### Feature-as-Route Registration

**When to use**: Every time a new AI capability is added to the super app.

**How it works**: A feature declares itself as a route config — path, tab label, icon, and feature key. The shell's router consumes this config to build navigation and route guards. The feature module is lazy-loaded, meaning the shell binary doesn't grow with each feature. The `AuthGuard` checks the user's `enabled_features` map against the route's feature key before activation.

**Example in this system**: /photoshoot registers with path `photoshoot`, icon `camera`, and feature key `photoshoot`. When Month 2 adds /humanize, it registers with path `humanize`, icon `text`, and feature key `humanize`. The shell code doesn't change — only the route registry gains an entry.

### Capture-Normalize-Infer Pipeline

**When to use**: Any feature that accepts user media input and returns AI-processed output.

**How it works**: The client captures input through a platform-appropriate mechanism (Capacitor Camera on iOS, file input on web), normalizes it to a standard payload format, sends it to the Flask API, and receives a result URL. The normalization step is critical — it means the API endpoint doesn't care whether the image came from a native camera, a photo library, or a drag-and-drop on web. The Flask endpoint's only job is: receive image → resolve user's model → call Replicate → return result.

**Example in this system**: `CameraService` returns either a base64 string (Capacitor) or a File object (web file input). Before upload, the service converts both to a multipart form payload. The Flask endpoint receives the same payload shape regardless of source, looks up the user's LoRA model ID in Neon, sends it to Replicate, and returns the generated image URL.

### Pre-seeded Personalization

**When to use**: When the "first run" experience must feel magical and waiting (for model training, data processing, etc.) would kill the effect.

**How it works**: Before any user signs up, their personalized asset (in this case, a trained LoRA model) is already created and mapped to their identity in the database. The moment they authenticate, the system resolves their model and they can use the feature immediately. This inverts the typical onboarding flow — instead of "sign up → upload data → wait → use," it's "receive invite → sign up → instant magic."

**Example in this system**: Sam collects selfies from 15 friends, trains a LoRA model for each on Replicate, and inserts a `lora_models` row mapping their email to their model ID. When a tester signs up with that email, the `/photoshoot` route resolves their model on first inference — no training step, no waiting screen, no "your model will be ready in 30 minutes."

---

## Execution Flow

```
[Phase 1: Foundation — Day 1]
  Shell scaffold + tab navigation
         │
[Phase 2: Core — Days 2-3, parallel]
  Auth + user model + gating ──┬── /photoshoot route + camera + inference
                               │
[Phase 3: Ship — Day 4-5]     ▼
  Deploy web (Coolify) + iOS (TestFlight) ──┬── Pre-train 15 LoRA models
                                            │
[Phase 4: Validate — Days 6-10]             ▼
  Invite testers → collect feedback → iterate
```

Phase 1 is the foundation — nothing else can start until the shell scaffold exists because both the auth system and /photoshoot need routing and layout to build against.

Phase 2 runs two workstreams in parallel. Auth and /photoshoot are independent at the code level: auth builds the user model and gating middleware, while /photoshoot builds the camera-to-inference pipeline. They converge only at integration — /photoshoot needs the user's LoRA model ID, which lives in the user model that auth creates. This means both can be built simultaneously by working against a shared schema contract for the user and LoRA model tables.

Phase 3 has a hard dependency on both Phase 2 workstreams completing — deployment requires a working auth flow and a functional /photoshoot route. However, LoRA model training can begin as soon as the Replicate inference endpoint is confirmed working (end of Phase 2), since training uses Replicate's API directly and doesn't require the deployed app.

Phase 4 is the validation event. The 15 testers receive TestFlight invites, their pre-trained models are already mapped, and they experience the instant-magic flow on first launch. This phase has no defined end — it runs until signal emerges or the Month 2 decision point arrives.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Capacitor Camera plugin fails in Ionic 8 shell | /photoshoot loses its primary input method on iOS | Fall back to photo library upload via file input — less magical but functionally equivalent; camera support becomes a fast-follow fix rather than a blocker |
| Replicate inference latency exceeds 60 seconds | Users perceive the app as broken; success criterion missed | Show a progress indicator with intermediate status from Replicate's prediction API; set user expectations with "generating your photo" messaging rather than a spinner |
| Supabase free tier introduces unexpected limits | Auth failures during tester onboarding | At 15 users this is extremely unlikely (free tier supports 50K MAU); if hit, magic link fallback is a one-day implementation since the user model is auth-provider-agnostic |
| Repurposing Bubls bundle ID confuses App Store review | TestFlight submission rejected for mismatched app description | Update App Store Connect metadata (name, description, screenshots) before submitting; the app category and purpose change is routine for TestFlight builds |
| Replicate image URLs expire | Gallery shows broken images after URL TTL | For Month 1, accept the risk — 15 users, short feedback window; if URLs expire within the testing period, add a post-inference step that copies the image to a persistent store |
| May 1 Trendfy verdict changes technical requirements | Architecture assumptions invalidated mid-build | The shell is feature-agnostic by design — it doesn't care whether /photoshoot uses Trendfy's models or new ones; the `lora_models` table maps users to model IDs regardless of where those models were trained |

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this design
- [Epic](./epic.md) – Scope, tasks, and success criteria
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview