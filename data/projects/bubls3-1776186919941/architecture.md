# 🏗️ Solution Architecture: bubls3

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Bubls is a weekly event curation system built around a single insight: people don't want to search for events, they want someone to tell them what's good. The architecture reflects this by splitting the system into two independent halves — an ingestion-and-curation pipeline that runs once per week, and a multi-surface delivery layer that presents the same 5 picks across iOS, web, and email. These halves share nothing except a Postgres database, which means either can be rebuilt or replaced without affecting the other.

The pipeline half is a Python worker that pulls events from two structured APIs (Ticketmaster and Guidle), generates vector embeddings, and uses a two-pass ranking strategy: pgvector similarity narrows ~200 raw events to ~15 candidates per subscriber, then Claude Haiku selects and summarizes the final 5. This architecture keeps per-subscriber AI cost at ~$0.02/week while producing opinionated, curated output rather than ranked search results. The vector store exists from day one not because personalization requires it now, but because retrofitting embeddings onto historical data is expensive and lossy — accumulating them cheaply while the subscriber base is small means the data is ready when behavior-based ranking becomes viable.

The delivery half is a single Angular 19 + Ionic 8 + Capacitor 7 codebase that serves both the iOS app (via TestFlight) and the web app at bubls.ch. One screen, one data model, one build pipeline. Email is a parallel delivery channel driven by Resend, not a separate product surface. The entire system runs on a shared Neon Postgres instance that already hosts tables for three other products — no new infrastructure provisioning required.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Batch over real-time | Weekly curation matches the 90%-search-once-a-week demand pattern. Real-time ingestion would add operational complexity without matching how users actually consume event recommendations. The Thursday 6pm cadence is a product decision, not a technical limitation. |
| Claude IS the algorithm | No custom ML models, no recommendation engine, no collaborative filtering. Claude Haiku ranks and summarizes events based on a prompt. The prompt is the algorithm — iterable in minutes, not weeks. Vector similarity handles pre-filtering to keep costs bounded, but the taste-making happens in the LLM call. |
| Accumulate data before you need it | pgvector embeddings and the `bubls_engagement` table exist from day one. They serve no user-facing purpose in v1. But switching from keyword-based to behavior-based personalization later requires historical embeddings and interaction data — and generating those retroactively is either impossible (interactions) or expensive (re-embedding expired events). The cost of storing them now is negligible at small scale. |
| Same codebase, multiple surfaces | Angular + Ionic + Capacitor produces a native iOS app and a web PWA from one build. This isn't about saving development time on v1 — it's about ensuring the web and native experiences can never diverge, which matters when email deep links need to work regardless of whether the recipient has the app installed. |
| Shared infrastructure, isolated data | Bubls tables live on the same Neon Postgres instance as Springular, Trendfy, and Humanize-me. Table prefixing (`bubls_`) provides namespace isolation without provisioning costs. At the current scale (< 200 subscribers), a shared instance is the correct call — dedicated infrastructure is a scaling decision that should follow validation, not precede it. |

---

## System Boundaries

### What This System Includes

- Weekly Python worker for event ingestion, embedding generation, and AI curation
- Cross-platform Angular + Ionic + Capacitor client (iOS native + web PWA)
- Subscriber management with magic link authentication
- Push notification delivery (iOS) and email delivery (Resend)
- Vector storage layer for events with pgvector on Neon Postgres
- Engagement tracking schema (writes only — no read-side analytics in v1)

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| User accounts or OAuth | Event recommendations are non-sensitive data. Magic link tokens (email + UUID) provide sufficient identity without the friction of account creation. Auth complexity is a retention killer for a product whose value proposition is "no effort required." |
| Search or browse UI | The entire thesis is that curation replaces search. Exposing vector search to users would reposition Bubls as a discovery tool competing with Google's "Ask Maps" — a fight it cannot win on distribution. The vectors power the pipeline, not a user-facing feature. |
| Organizer portal | Classic chicken-and-egg. Organizer tools require an audience to attract organizers. Building the portal before proving subscriber retention invests in the wrong side of the marketplace first. |
| Unstructured source scraping | Ticketmaster and Guidle provide structured APIs with reliable field mapping. Scraping EventFrog or Facebook Events introduces fragility (DOM changes, rate limits, legal ambiguity) that is not justified until the structured sources prove insufficient for curation quality. |
| Android build | The Capacitor codebase supports Android with minimal additional work, but constraining to iOS-only for v1 reduces the QA surface to one platform. Android is a distribution decision, not an architecture decision — the same `ng build → cap copy` pipeline applies. |
| Real-time event updates | Events change infrequently within the Thursday-to-Sunday consumption window. Real-time sync would require webhook infrastructure or polling, adding operational burden for a scenario (event cancellation between Thursday and Sunday) that affects a small fraction of picks. |

---

## Component Design

### Event Ingestion Worker

**Purpose**: Solve the content treadmill problem — events expire in days, so the supply of raw events must be replenished automatically every week.

**Key Parts**:
- `TicketmasterClient` — Queries the Discovery API v2 for upcoming Zürich events, maps response fields to the internal event schema. Rewritten from the proven 2024 Java implementation (`TicketmasterClient.java`) into Python, dropping MapStruct mappers in favor of simple dataclass construction with only the 10 fields that matter for curation.
- `GuidleClient` — Queries the Guidle Veranstaltungskalender endpoint, navigates the groupSet → offers → events hierarchy, and extracts event metadata including Swiss-specific venue and address formatting.
- `EmbeddingService` — Generates 1536-dimensional vectors for each event description via OpenAI's text-embedding-3-small model. OpenAI over Ollama because hosted inference eliminates GPU provisioning, and at the expected volume (< 500 events/week) the API cost is negligible compared to self-hosted infrastructure.
- `EventStore` — Handles upsert logic into `bubls_events_raw` with deduplication on source + source_id composite key. Expired events are soft-deleted (retained for embedding history) rather than hard-deleted.

**Patterns**: The worker is a single-run script triggered by a cron schedule (GitHub Actions or system cron), not a long-running service. This matches the weekly cadence and avoids the operational overhead of keeping a worker process alive between runs. If the script fails, it can be re-run idempotently because upserts on source_id prevent duplicate events.

### AI Curation Pipeline

**Purpose**: Transform ~200 undifferentiated event listings into 5 opinionated, subscriber-relevant picks — the core value proposition.

**Key Parts**:
- `CurationService` — Orchestrates the two-pass ranking strategy. First pass: pgvector cosine similarity query using subscriber interest keywords as the query vector, returning ~15 candidate events. Second pass: Claude Haiku prompt that receives the 15 candidates and returns 5 ranked picks with English summaries and preserved German titles.
- `PicksWriter` — Writes the structured 5-pick output to `bubls_picks` as a JSONB column, keyed by subscriber_id and week_start. This denormalized structure optimizes for the read pattern (fetch this week's picks for one subscriber) at the cost of storage efficiency that doesn't matter at this scale.

**Patterns**: The two-pass approach is an explicit cost-quality trade-off. Sending all 200 events to Claude would cost ~$0.20/subscriber/week and produce better results. Sending 15 pre-filtered events costs ~$0.02/subscriber/week and produces results that are good enough — the vector similarity pass eliminates obviously irrelevant events (a techno club night for someone interested in outdoor hiking), and Claude's ranking handles the subjective taste-making within the relevant set. At 200 subscribers, the difference is $40/week vs. $4/week. The cheaper option is correct until curation quality data proves otherwise.

### Cross-Platform Client

**Purpose**: Provide a single persistent surface for event picks that works on iOS and web, replacing the fragmented discovery experience across ephemeral platforms.

**Key Parts**:
- `PicksDashboardPage` — The one screen. Displays 5 event cards with title, AI summary, date/time, venue, price, and a link to the event source page. Countdown timer to next Thursday when no picks are available. This is a standalone Angular component with no routing complexity — the entire app is one page.
- `PicksService` — Fetches the current week's picks from the API. Thin HTTP wrapper with no caching beyond Angular's default — picks change once per week, so cache invalidation is a non-problem.
- `InterestPickerComponent` — Onboarding and preference editing. Renders the fixed interest set (music, food, outdoors, art, nightlife, tech, sports, family) as toggleable chips. Maximum 3 selections. This constraint is intentional — more interests means broader, less opinionated recommendations, which defeats the curation thesis.
- `EventCardComponent` — Presentational component for a single pick. German title preserved from source, English summary from Claude, external link to event page. No internal event detail view — Bubls is a referral surface, not a destination.

**Patterns**: The Ionic + Capacitor layer handles platform differentiation (push notifications on iOS, standard web APIs on browser) through Capacitor's plugin abstraction. The Angular code never checks which platform it's running on — Capacitor plugins degrade gracefully on web, and the `@capacitor/push-notifications` plugin is simply a no-op in the browser context. This means the web build requires zero conditional logic.

### Subscriber Management

**Purpose**: Enable interest-based curation without imposing authentication friction on a product that handles no sensitive data.

**Key Parts**:
- `SubscriberService` — Handles signup (email + city + interests → UUID token), magic link generation for web access, and interest updates. No password hashing, no session management, no OAuth flows. The token is the identity.
- `bubls_subscribers` table — Stores email, city, interests as a text array, UUID token, and active flag. Interests are stored as plain text rather than foreign keys to a categories table because the interest set is fixed and small — normalization would add joins without adding value.

**Patterns**: Magic link authentication is a deliberate trade-off: it's less secure than OAuth (token in URL, no expiration rotation in v1) but dramatically simpler for a product where the worst-case breach is someone seeing another person's event recommendations. If Bubls ever handles payments or personal data beyond email, this decision must be revisited. For now, the reduced signup friction directly serves the 50-user TestFlight validation goal.

### Notification and Email Delivery

**Purpose**: Ensure subscribers see their picks regardless of app open behavior or push notification opt-in status.

**Key Parts**:
- `NotificationScheduler` — Triggers at 6pm CET every Thursday after the curation pipeline completes. Sends iOS push notifications via APNs (through Capacitor's push plugin server-side counterpart) and emails via Resend API in parallel. Both channels carry the same 5 picks — email is not a degraded experience.
- `EmailTemplateService` — Renders picks into a scannable email format via Resend's template system. Includes deep links to both the web dashboard (with magic link token) and the iOS app (via universal links). The email is the re-engagement mechanism for subscribers who disable push notifications or stop opening the app.

**Patterns**: Dual-channel delivery (push + email) addresses the medium-priority risk identified in the [Analysis](./analysis.md): declining push notification opt-in rates across iOS. Email provides a fallback that doesn't depend on Apple's permission system. The 6pm Thursday timing is fixed, not subscriber-configurable — consistency builds habit, and a configurable schedule adds complexity without evidence that it improves retention.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 19 + Ionic 8 + Capacitor 7 | Proven in Constellation (189 commits). Single codebase produces iOS native app and web PWA. Standalone components, no NgModules — minimal boilerplate for a one-screen app. Ionic provides mobile-native UI patterns (cards, chips, haptics) without custom CSS. |
| Backend / Worker | Python (scripts, not a framework) | The backend is a weekly cron job, not a web server. Python is the natural choice for a script that calls APIs, generates embeddings, and writes to Postgres. No Flask, no FastAPI — just a script with `psycopg2`, `requests`, and `anthropic`. The simplicity is intentional: there is no API to serve because the client reads directly from the database via a thin Express proxy or Neon's HTTP API. |
| Database | Neon Postgres with pgvector | Shared instance already provisioned in EU Central 1. pgvector is natively supported — no extension installation required. Postgres handles both relational data (subscribers, picks) and vector data (event embeddings) in one system, avoiding the operational overhead of a separate vector database like Pinecone or Weaviate. At < 500 events and < 200 subscribers, Neon's free/starter tier is sufficient. |
| AI — Curation | Claude Haiku (Anthropic API) | Cheapest Claude model at ~$0.25/M input tokens. Sufficient for ranking 15 events and generating 5 one-line summaries. The prompt is the algorithm — Haiku's instruction-following is strong enough for structured JSON output with bilingual handling (German titles, English summaries). Upgrading to Sonnet is a one-line change if curation quality needs improvement. |
| AI — Embeddings | OpenAI text-embedding-3-small | 1536-dimensional embeddings at $0.02/M tokens. Industry-standard model with strong multilingual support (critical for German-language event descriptions). OpenAI over Ollama because hosted inference eliminates GPU provisioning — and at < 500 events/week, the total embedding cost is under $0.01/week. |
| Email | Resend API | Already used in Humanize-me. Simple REST API, generous free tier (100 emails/day), built-in analytics (open rate, click rate). No need for SendGrid's complexity or Mailchimp's template builder — Bubls sends one email template once per week. |
| Push Notifications | APNs via @capacitor/push-notifications | Capacitor's push plugin handles device token registration on the client side. Server-side push delivery uses APNs directly (via a Python APNs library) rather than a push notification service like OneSignal — at < 200 subscribers, the abstraction layer adds dependency without reducing complexity. |
| CI/CD | GitHub Actions | Proven patterns from Springular (path-change detection via dorny/paths-filter) and Constellation (iOS archive → TestFlight via Fastlane). Thursday cron trigger for the Python worker. All secrets (Neon connection string, API keys, Apple signing certificates) managed in GitHub Actions secrets. |
| Hosting — Web | Coolify (or Vercel) | Angular SSG build deployed via webhook on push to main. Static hosting is sufficient — the web app is a read-only dashboard with one API call on load. Coolify is already provisioned for Humanize-me; Vercel is the fallback if Coolify's Angular support proves problematic. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Two-pass curation (vector → Claude) instead of Claude-only | Sending 200 events to Claude would cost 10x more per subscriber and hit context window limits. Vector similarity pre-filtering reduces the candidate set to ~15 relevant events, keeping Claude focused on subjective ranking rather than bulk filtering. | Vector similarity may exclude events that Claude would have found interesting but that don't match interest keywords literally. Mitigation: interest keywords are embedded as vectors too, so semantic similarity (not keyword matching) handles edge cases like "live jazz" matching "music" interests. |
| OpenAI embeddings instead of Ollama | Ollama requires a GPU-equipped server running continuously. OpenAI's API costs < $0.01/week at Bubls' volume and eliminates infrastructure provisioning. The 2024 backend used Ollama because it existed alongside a self-hosted Spring Boot server; the new architecture has no always-on server. | Vendor dependency on OpenAI for a core pipeline component. Mitigation: the embedding model is a single function call — swapping to Voyage AI, Cohere, or a future Anthropic embedding model requires changing one API call, not re-architecting. Existing embeddings would need regeneration, but at < 500 events/week the migration cost is trivial. |
| Magic link tokens instead of OAuth/Supabase Auth | Bubls handles no sensitive data — the worst case of a compromised token is someone seeing another user's 5 event picks. OAuth adds signup friction (password creation, email verification flow, forgot-password handling) that directly conflicts with the goal of converting 50 TestFlight users from install to onboarding in under 30 seconds. | No session management, no token rotation, no multi-device sync. A user's token is a permanent bearer credential embedded in URLs. Acceptable for v1 where the threat model is "event recommendations are not secrets." Must be revisited if Bubls ever handles payments or personal data. |
| Fixed interest set (8 categories) instead of free-text | Free-text interests require NLP to normalize ("techno" vs "electronic music" vs "EDM") and create a sparse vector space that degrades similarity search quality. A fixed set of 8 categories ensures consistent vector queries and simplifies the onboarding UI to one tap per interest. | Subscribers whose interests don't fit the 8 categories (e.g., "theater," "comedy," "networking") get less relevant picks. Mitigation: the categories are broad enough to cover ~90% of Zürich events, and the Claude ranking pass can surface interesting outliers even within a broad category match. The category set can be expanded based on subscriber feedback without schema changes. |
| JSONB picks column instead of normalized event-pick junction table | Picks are read as a unit (all 5 together, once per week) and never queried individually. A junction table would add 5 JOINs per dashboard load for no query flexibility benefit. JSONB stores the denormalized pick data (title, summary, venue, link) directly, optimizing for the single read pattern. | Harder to run aggregate queries across picks (e.g., "which events were picked most frequently"). Mitigation: `bubls_engagement` captures click-through events separately, and aggregate analysis is a post-validation concern that can use JSONB operators or a data warehouse export. |
| Thursday 6pm fixed schedule instead of configurable | Consistent timing builds habit. A configurable schedule requires timezone handling, preference UI, per-subscriber cron scheduling, and testing across time zones — all for a feature that no competitor has validated as valuable. The fixed schedule also simplifies the pipeline: one curation run per week, not a rolling window. | Subscribers in different time zones receive picks at suboptimal local times. Mitigation: Zürich-only scope means all subscribers are in CET/CEST. Multi-city expansion will require timezone-aware scheduling, but that's a scaling decision. |
| Neon shared instance instead of dedicated database | Bubls adds 4 tables to an instance that already hosts 3 other products. At < 200 subscribers and < 500 events, the total data volume is under 100MB including embeddings. A dedicated instance would cost $19+/month for isolation that provides no performance benefit at this scale. | Noisy neighbor risk — a runaway query in another product's tables could affect Bubls performance. Mitigation: Neon's connection pooling and query timeout defaults limit blast radius. If Bubls reaches 1K+ subscribers, migrating to a dedicated instance is a connection string change, not an architecture change. |
| No API server (Express proxy or Neon HTTP) instead of Flask/FastAPI | The client needs one read endpoint (get this week's picks for subscriber token) and one write endpoint (create subscriber). A full web framework is overhead for two routes. Either a minimal Express proxy (already familiar from Spec Doc) or Neon's built-in HTTP API can serve these. | Limited extensibility if the API surface grows. Mitigation: the two-endpoint contract is unlikely to expand significantly — Bubls is not a CRUD app. If organizer tools or additional surfaces require more endpoints, Flask can be introduced at that point without affecting the existing routes. |

---

## Patterns

### Weekly Batch Pipeline

**When to use**: Any operation where the consumption cadence is weekly and real-time freshness provides no user value.

**How it works**: A single Python script runs as a cron-triggered GitHub Actions job every Thursday. It executes the full pipeline sequentially: ingest events → generate embeddings → store in Postgres → run curation per subscriber → write picks → send notifications and emails. Each step is idempotent — re-running the script for the same week overwrites picks rather than duplicating them. Failures at any step are logged and can be manually restarted without side effects.

**Example in this system**: The Thursday curation pipeline runs once, processes all subscribers in a loop, and completes in minutes. There is no queue, no worker pool, no retry infrastructure. At 200 subscribers with ~15 candidates each, the total Claude API calls complete in under 5 minutes sequentially. Parallelization is a premature optimization at this scale.

### Two-Pass Ranking (Vector Filter → LLM Judge)

**When to use**: When the candidate set is too large or too expensive to send entirely to an LLM, but the final ranking requires subjective judgment that vector similarity alone cannot provide.

**How it works**: First pass uses pgvector cosine similarity to reduce the candidate set from ~200 events to ~15 per subscriber, based on semantic similarity between subscriber interest embeddings and event description embeddings. Second pass sends the 15 candidates to Claude Haiku with instructions to rank by relevance, variety, and quality, then select 5 and generate summaries. The vector pass handles "is this event remotely relevant?" while the LLM pass handles "is this event worth recommending?"

**Example in this system**: A subscriber interested in "music" and "food" gets ~15 candidates that include concerts, food festivals, and restaurant openings. Claude then applies editorial judgment — dropping a generic cover band night in favor of a unique pop-up dinner, even though the cover band had higher vector similarity to "music." This subjective ranking is what separates curation from search.

### Progressive Platform Enhancement

**When to use**: When a single codebase must serve both native mobile and web, with platform-specific features (push notifications, haptics) available only on native.

**How it works**: Capacitor plugins provide a unified API that resolves to native implementations on iOS and graceful no-ops on web. The Angular application code calls the same plugin API regardless of platform. No `if (platform === 'ios')` conditionals — the Capacitor bridge handles platform detection internally. Features that have no web equivalent (push notifications) simply don't execute on web, and the email channel serves as the delivery fallback.

**Example in this system**: `@capacitor/push-notifications` registers for push tokens on iOS and does nothing on web. The same `PicksDashboardPage` component renders identically on both platforms. The email with deep links serves as the web user's equivalent of a push notification — same content, different delivery mechanism, no code branching.

### Namespace Isolation on Shared Infrastructure

**When to use**: When multiple products share a database instance or cloud account, and full isolation (separate instances) is not justified by scale or security requirements.

**How it works**: All Bubls tables use the `bubls_` prefix. No foreign keys cross product boundaries. Each product's tables are self-contained — if Bubls needs to be migrated to a dedicated instance, the migration is a `pg_dump` of prefixed tables and a connection string change. No shared sequences, no shared enums, no cross-product joins.

**Example in this system**: `bubls_subscribers`, `bubls_events_raw`, `bubls_picks`, and `bubls_engagement` coexist alongside Springular's auth tables, Trendfy's signup tables, and Humanize-me's usage tables on the same Neon instance. The `bubls_` prefix is a convention, not enforced by Postgres schemas — simplicity over rigor at this scale.

---

## Data Model

### Core Tables

**`bubls_events_raw`** — The event content lake. Every event from every source lands here with its vector embedding. Deduplication key is `source` + `source_id`. The `embedding vector(1536)` column enables pgvector similarity queries. Events are never hard-deleted — expired events retain their embeddings for historical analysis. This table is write-heavy (weekly batch upsert) and read-heavy during curation (vector similarity queries per subscriber).

**`bubls_subscribers`** — Subscriber identity and preferences. Email is the unique identifier, UUID token is the authentication credential, interests are stored as a text array. The interests array is intentionally not normalized into a junction table — with a fixed set of 8 categories, the array is simpler to query and update. City is stored for future multi-city expansion but is always "zurich" in v1.

**`bubls_picks`** — Denormalized weekly picks per subscriber. JSONB column contains the 5 event objects (title, summary, venue, datetime, price, url) as returned by the Claude curation step. Keyed by subscriber_id + week_start. One row per subscriber per week. This is the primary read table for the client — one query returns everything needed to render the dashboard.

**`bubls_engagement`** — Event-sourced interaction log. Records clicks, opens, shares, and other subscriber actions as individual rows with event_type and metadata JSONB. Not used for any v1 feature — exists purely to accumulate behavioral data for future personalization. Write-only in v1, no read queries, no indexes beyond the primary key.

### Data Flow

Events flow in one direction: external APIs → `bubls_events_raw` → (vector query + Claude) → `bubls_picks` → client and email. Subscriber data flows in the opposite direction: client → `bubls_subscribers` → curation pipeline (reads interests for vector query). Engagement data flows from client → `bubls_engagement` and is not read by any v1 component. This unidirectional flow means there are no circular dependencies between tables and no complex transaction requirements.

---

## Execution Flow

```
[Phase 1 — Parallel]
  Task 1: Event Ingestion ──────────┐
  Task 2: Cross-Platform Client ────┤
                                    │
[Phase 2 — Sequential]             │
  Task 3: AI Curation Pipeline ◄────┘ (depends on Task 1)
  Task 5: Onboarding ◄──────────────── (depends on Task 2)

[Phase 3 — Sequential]
  Task 4: Push + Email Delivery ◄────── (depends on Tasks 2, 3)
```

Tasks 1 and 2 have no dependencies and should be built in parallel. Task 1 (ingestion + vector storage) takes 3 days and produces the `bubls_events_raw` table that Task 3 depends on. Task 2 (cross-platform client) takes 4 days and produces the app shell that Tasks 4 and 5 depend on. Task 3 (curation pipeline, 2 days) cannot start until Task 1 delivers stored events with embeddings. Task 5 (onboarding, 1 day) can start as soon as the client shell from Task 2 exists. Task 4 (delivery, 2 days) is the integration point — it requires both the client (for push registration) and the curation pipeline (for picks to deliver).

The critical path runs through Tasks 1 → 3 → 4 (7 days). Task 2 runs in parallel with Task 1 and must complete before Task 4, but at 4 days it finishes before Task 3 completes, so it does not extend the critical path. Total estimated timeline: 7–8 days with parallel execution of Tasks 1 and 2.

---

## Risk Mitigation

| Risk | Mitigation Built Into Architecture |
|------|------------------------------------|
| API rate limits or downtime (Ticketmaster, Guidle) | Weekly batch means one API call window per week. If either source fails, the pipeline continues with the other — 5 picks from one source is better than 0 picks from two. No real-time dependency on external APIs. |
| Push notification opt-in decline | Email delivery runs in parallel, not as a fallback. Every subscriber gets email regardless of push opt-in status. The architecture treats push as a bonus channel, not the primary one. |
| Vector similarity returns poor candidates | Claude's second-pass ranking can surface quality even from a mediocre candidate set. The 15-candidate window is wide enough to include edge cases. If quality is consistently poor, the fix is prompt tuning (minutes) not re-architecture. |
| Neon shared instance performance | Bubls' total data volume (< 100MB including embeddings) and query pattern (one batch write/week, low-frequency reads) make it one of the lightest tenants. Vector similarity queries on < 500 rows complete in milliseconds. Connection pooling prevents runaway connections. |
| Magic link token compromise | Threat model explicitly scoped: event recommendations are not sensitive data. If the product evolves to handle payments or personal data, auth must be upgraded — this is a documented architectural debt, not an oversight. |

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview