# 🎯 Epic: bubls3

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Event discovery in Zürich is fragmented across Eventbrite (400 results per query), Google (6 different sites), Instagram stories (24-hour TTL), and WhatsApp groups (unsearchable). The result: socially active people default to staying home or rotating through the same venues — not because nothing is happening, but because finding what's happening costs more effort than the event is worth. This is a city where 90% of potential users search for events once a week or less, confirming that the demand pattern is weekly, not continuous.

The competitive window is unusually open. Bending Spoons acquired Eventbrite for $500M (Dec 2025) with revenue declining 12% YoY, signaling platform neglect. IRL collapsed in fraud charges, damaging category trust. Google's "Ask Maps" (March 2026) threatens to own search-based discovery, but nobody owns push-based curation — the format that matches how people actually consume event recommendations. Meanwhile, the infrastructure layer is forming: MCP servers and structured APIs exist for Ticketmaster, Guidle, and others, but no consumer product has assembled them for the Swiss market.

Bubls targets socially active professionals, students, and expats in Zürich who go out 1–3 times per week. The initial product is free — validation before monetization. Revenue path: affiliate commission on ticket links (week 2+), then organizer self-serve listings after proving audience retention. Zürich's large international population and high density of events per capita make it an ideal single-city proving ground. If 200 subscribers retain after 4 weeks of Thursday picks, the model validates for expansion to Basel, Bern, and Geneva.

**Value Proposition**: Five AI-curated event picks delivered every Thursday at 6pm — no searching, no browsing, no decision fatigue.

---

## Scope

### What This Epic Covers

- **Weekly curation pipeline** — automated ingestion from Ticketmaster and Guidle APIs, vector embedding, and Claude-powered ranking into 5 picks per subscriber per week
- **Cross-platform client** — single Angular 19 + Ionic 8 + Capacitor 7 codebase serving iOS app (TestFlight), web app (bubls.ch), and weekly email
- **Interest-based onboarding** — lightweight signup (email + city + up to 3 interests) with magic link authentication, no accounts or passwords
- **Push + email delivery** — Thursday 6pm push notification (iOS) and Resend email with the same 5 picks, ensuring re-engagement regardless of notification opt-in
- **Vector storage from day one** — events stored with pgvector embeddings in Neon Postgres, accumulating data for future personalization without requiring it now

### What This Epic Does NOT Cover

- ❌ **User accounts or OAuth** — magic link tokens are sufficient for non-sensitive event recommendations
- ❌ **Search or browse UI** — the entire thesis is that curation replaces search; vector search powers the backend pipeline, not a user-facing feature
- ❌ **Monetization** — affiliate links are a week-2 addition; business model validation follows product validation
- ❌ **Android** — same Capacitor codebase enables Android later; iOS first to constrain scope
- ❌ **Multi-city** — Zürich only until retention is proven; geographic expansion is a scaling decision
- ❌ **Organizer portal or self-serve tools** — requires audience first (chicken-and-egg); post-validation feature
- ❌ **Unstructured sources (EventFrog, Facebook Events)** — APIs only for v1 to ensure reliability; LLM scraping deferred
- ❌ **Social features, map view, or calendar integration** — different product categories that dilute the core weekly-picks thesis

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Event ingestion and vector storage** | None | 2 | 3 days | High |
| 2 | **Cross-platform client (iOS + web)** | None | 1 | 4 days | High |
| 3 | **AI curation pipeline** | 1 | — | 2 days | High |
| 4 | **Push notification + email delivery** | 2, 3 | — | 2 days | High |
| 5 | **Onboarding and subscriber management** | 2 | — | 1 day | High |

### Task 1: Event ingestion and vector storage

Rewrite the proven Ticketmaster and Guidle integrations from the 2024 Java backend into a Python worker. Pull upcoming events for Zürich, generate embeddings via OpenAI (text-embedding-3-small, 1536 dimensions), and store in `bubls_events_raw` with pgvector on the existing Neon Postgres instance. This addresses the critical content treadmill issue — events expire in days, so automated weekly ingestion is non-negotiable. The two-pass approach (vector similarity pre-filter → Claude ranking) depends on embeddings being in place first. See [Solution Architecture](./architecture.md) for database schema and API integration design.

### Task 2: Cross-platform client (iOS + web)

Scaffold an Angular 19 + Ionic 8 + Capacitor 7 project reusing Constellation's proven patterns (capacitor.config.ts, ios/ directory, standalone components). Build one screen: the picks dashboard showing 5 event cards (German title preserved, English AI summary, date/time, venue, price, link to event page). Same codebase serves as PWA at bubls.ch and native iOS app via TestFlight. This directly addresses the analysis finding that event information is scattered across ephemeral platforms — Bubls provides one persistent surface. See [Solution Architecture](./architecture.md) for frontend architecture and Capacitor configuration.

### Task 3: AI curation pipeline

Build the Thursday curation workflow: for each subscriber, query `bubls_events_raw` by interest-keyword vector similarity to get ~15 candidates, then send those candidates to Claude (Haiku) with instructions to rank, filter, and summarize into 5 structured picks. Claude preserves German event titles and generates English summaries — directly addressing the language barrier issue for Zürich's international population. Output is structured JSON written to `bubls_picks`. This two-pass approach keeps per-subscriber cost to ~$0.02/week while producing curated, opinionated recommendations instead of undifferentiated listings. See [Solution Architecture](./architecture.md) for prompt design and vector query strategy.

### Task 4: Push notification + email delivery

Wire Thursday 6pm delivery across two channels: iOS push notifications via @capacitor/push-notifications and email via Resend API. Both channels carry the same 5 picks. Email serves as the fallback for declining push opt-in rates (identified as medium-priority risk in the analysis) and as the re-engagement mechanism for users who haven't opened the app. Email includes deep links to both the web dashboard and the native app. See [Solution Architecture](./architecture.md) for notification scheduling and email template design.

### Task 5: Onboarding and subscriber management

Build the signup flow: open app → pick city (Zürich only) → choose up to 3 interests from a fixed set (music, food, outdoors, art, nightlife, tech, sports, family) → enter email → see dashboard with countdown to first Thursday. No accounts, no passwords — email + UUID token is identity. Magic link tokens for web access. This addresses the social network dependency issue: new residents and expats get interest-based curation without needing local connections. Store subscriber data in `bubls_subscribers` with interests as a vector-queryable array. See [Solution Architecture](./architecture.md) for auth flow and data model.

---

## Success Criteria

This epic is complete when:

- ✅ 50 TestFlight users receive their first Thursday push notification with 5 curated Zürich event picks
- ✅ Weekly ingestion pipeline pulls events from both Ticketmaster and Guidle APIs and stores them with embeddings in Neon Postgres
- ✅ Web app at bubls.ch displays the same picks as the native iOS app from the same Angular codebase
- ✅ Email delivery achieves >40% open rate across the first 4 weekly sends
- ✅ Event click-through rate (CTR) from picks to event pages is measurable and >10%
- ✅ 4-week retention: >40% of initial subscribers open the app or email on the 4th Thursday

---

## Non-Goals

- ❌ **Behavior-based personalization** — interest keywords + vector similarity is the v1 algorithm; engagement-driven recommendations require interaction data that doesn't exist yet
- ❌ **Real-time event updates** — weekly batch cadence matches user behavior (90% search once/week or less); real-time adds complexity without matching demand
- ❌ **Competing on search** — Google's "Ask Maps" has insurmountable distribution for search-based discovery; Bubls competes on format (push-based curation), not on search
- ❌ **App Store launch** — TestFlight distribution to personal network first; App Store submission is a growth decision after validating retention
- ❌ **Scaling infrastructure** — Neon's shared instance handles the first 200 subscribers comfortably; infrastructure investment follows validation, not the other way around

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview