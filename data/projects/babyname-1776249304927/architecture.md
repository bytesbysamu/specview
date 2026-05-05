# 🏗️ Solution Architecture: babyname

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The baby name app is a thin client that captures structured preferences, sends them to a backend proxy wrapping the Claude API, and renders the AI-generated results as name cards. The architectural insight is that the prompt *is* the product — the system has no database of names, no recommendation engine, no ML pipeline. Claude generates names, explanations, and cultural context on every request. Everything else is UI and payment plumbing.

The system follows a request-response model rather than a streaming or real-time architecture. A parent fills out preferences, taps generate, waits a few seconds, and gets a batch of name cards. This simplicity is deliberate — the interaction pattern doesn't benefit from streaming (parents want to see complete cards, not partial names), and it keeps the backend stateless. The only persistent state lives on the device (favorites) and in a lightweight server-side store (shared shortlists).

The backend exists for exactly three reasons: protect the Claude API key from extraction, enforce generation limits for the freemium paywall, and store shared shortlists. Everything else runs on-device. This keeps infrastructure cost near zero until validation signals arrive.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Claude IS the algorithm | No name database, no embeddings pipeline, no training data. Claude generates everything from preferences per request. The prompt engineering is the entire product differentiator. |
| Ship the car, not the engine | Reuse the existing Ionic + Capacitor boilerplate from the constellation repo. No custom build pipeline, no new CI/CD — same workflow as existing shipped products. |
| Local-first, server-lite | Favorites, preferences, and generation history stored on-device. The server only handles what the client physically cannot: API key custody, usage metering, and shareable link storage. |
| Validate before scaling | Direct Claude API calls through a single proxy endpoint. No caching layer, no queue, no CDN. These are scaling concerns that don't matter until 200 users confirm the product has legs. |

---

## System Boundaries

### What This System Includes

- Preference capture UI with structured input categories
- Backend proxy for Claude API requests with usage tracking
- Name card generation via prompt engineering
- On-device favorites persistence
- Server-side shared shortlist storage
- StoreKit 2 subscription paywall with server receipt validation

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Name database or static dataset | Claude generates names dynamically — a database adds maintenance cost without improving quality |
| User accounts or authentication | Magic links or anonymous device IDs are sufficient for MVP; auth adds friction to a validation-stage product |
| Real-time partner collaboration | Sharing a read-only link covers the core need identified in [Analysis](./analysis.md); collaborative editing is a post-PMF feature |
| Analytics pipeline | App Store Connect and basic server logs provide enough signal for 200-user validation |
| Embeddings or pgvector | No similarity search or recommendation engine needed when Claude handles personalization directly |

---

## Component Design

### Preference Capture

**Purpose**: Translate what parents care about into structured input that produces high-quality Claude generations.

**Key Parts**:
- `PreferencePage` — Multi-step input flow using Ionic slides. Each slide covers one preference dimension (style, origin, meaning, gender, constraints). Feels conversational because each step has a single focus rather than presenting a form wall.
- `PreferenceModel` — Typed data structure holding all input dimensions. Serialized to JSON for the API request and cached on-device for regeneration.

**Patterns**: Wizard pattern with skip-friendly steps. Only gender is required — everything else has sensible defaults or is optional. This keeps the under-60-second target from the [Epic](./epic.md) achievable while still capturing enough signal for quality output.

### Generation Engine

**Purpose**: Turn structured preferences into personalized name cards via Claude API.

**Key Parts**:
- `GenerationProxy` — Backend endpoint that receives preference JSON, constructs the Claude prompt, calls the API, and returns structured name card data. Stateless — no session affinity, no caching.
- `UsageMeter` — Tracks generation count per device ID. Stores counts in Neon Postgres alongside shared shortlists. This is the paywall enforcement point.
- `PromptTemplate` — The system prompt and structured output instructions for Claude. This is versioned and iterable — prompt quality directly determines product quality.

**Patterns**: The prompt instructs Claude to return a JSON array of name objects with specific fields (name, pronunciation, origin, meaning, popularity tier, rationale). Structured output avoids parsing fragility. The rationale field explicitly references the user's stated preferences — this is the differentiator that makes results feel personalized rather than random.

### Name Card Display

**Purpose**: Present generated names with enough context for parents to form an opinion without leaving the app.

**Key Parts**:
- `ResultsPage` — Scrollable card list rendered from the generation response. Each card is a self-contained unit showing all metadata.
- `NameCard` — Component displaying name, pronunciation, origin, meaning, popularity indicator, and the personalized rationale. The rationale gets visual prominence — it's the element that no competitor offers.
- `FavoritesService` — On-device persistence using Capacitor Preferences or Ionic Storage. Reads and writes a local JSON array of saved name objects.

**Patterns**: Cards are immutable once generated. Favoriting copies the full card data to local storage rather than storing a reference, because there's no server-side card persistence to reference against. This trades storage efficiency for simplicity and offline reliability.

### Favorites and Sharing

**Purpose**: Let parents curate a shortlist and share it with a partner without requiring app installation.

**Key Parts**:
- `FavoritesPage` — Displays saved name cards with remove and reorder actions. All data is local.
- `ShareService` — Posts the favorites list to a backend endpoint that stores it in Neon Postgres and returns a unique URL. The URL serves a simple read-only web page rendering the shortlist.
- `SharedListPage` — Server-rendered or static page at the shareable URL. No authentication, no app install required. The partner sees the list in a mobile browser.

**Patterns**: Shareable links are write-once. Updating the list generates a new link rather than mutating the old one. This avoids sync complexity and stale-link confusion — if a parent reshares, the partner always sees the latest version.

### Paywall

**Purpose**: Convert free users to subscribers after demonstrating value.

**Key Parts**:
- `PaywallGate` — Checks remaining free generations before each request. When the limit is reached, presents the subscription offer instead of generating.
- `StoreKitService` — Wraps Capacitor's StoreKit 2 plugin for subscription purchase, restore, and status checks.
- `ReceiptValidator` — Backend endpoint that validates Apple receipts to confirm active subscriptions. The backend checks receipts before allowing generation, preventing client-side bypass.

**Patterns**: The free tier limit is enforced server-side via `UsageMeter`, not client-side. Client-side enforcement alone is trivially bypassable (reinstall, clear data). Device fingerprinting via `identifierForVendor` ties usage to the device. This isn't bulletproof but is sufficient for MVP — determined abusers represent negligible cost at validation scale.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 19 + Ionic 8 + Capacitor 7 | Reuses the existing constellation boilerplate. Same build pipeline, same iOS deployment workflow via Fastlane. Zero ramp-up time. |
| Backend | Python (Flask) | Matches the existing product API pattern from Humanize-me. Minimal surface area — three endpoints (generate, share, validate receipt). Express would also work, but Flask is the established pattern for product APIs. |
| Database | Neon Postgres (shared instance) | Already provisioned with existing products. Stores only usage counts and shared shortlists — two tables. pgvector available if embedding-based features become relevant post-validation. |
| AI | Claude API (Anthropic) | Direct API calls via the backend proxy. No SDK wrapper needed — raw HTTP with structured JSON output. Claude's instruction-following quality is critical for rationale accuracy and cultural sensitivity. |
| Payments | StoreKit 2 via Capacitor plugin | Native iOS subscription handling. Apple Small Business Program keeps the cut at 15%. No Stripe needed — App Store is the only distribution channel for MVP. |
| Local Storage | Capacitor Preferences | Key-value storage for favorites and cached preferences. No SQLite overhead for what amounts to a single JSON blob per feature. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Backend proxy instead of direct Claude API calls from app | API keys in client binaries are extractable. A proxy also centralizes usage tracking and paywall enforcement. | Adds a server dependency and ~200ms latency per request. Acceptable because generation already takes 3-8 seconds. |
| Device ID for identity instead of user accounts | No friction to start using the app. Parents in the validation phase won't create accounts for a name generator. | Usage limits reset if the user reinstalls or switches devices. At 200-user validation scale, this is negligible revenue leakage. |
| On-device favorites instead of server-synced | Eliminates auth requirement and sync complexity. Favorites are personal and low-volume (tens of names, not thousands). | No cross-device sync. If a user switches phones, favorites are lost. Acceptable for MVP — account-based sync is a post-validation feature. |
| Batch response instead of streaming | Parents want to see complete name cards, not partial results. A card with half a rationale is worse than a loading spinner. | Perceived wait time is higher than streaming. Mitigated by a progress indicator and the fact that 5-10 cards in 3-8 seconds is fast enough. |
| Write-once shareable links instead of mutable shared lists | Avoids real-time sync, conflict resolution, and stale-state bugs. A new share action costs nothing. | Partners may see outdated lists if the parent updates favorites but forgets to reshare. Acceptable friction for MVP. |
| Flask over Express for backend | Flask is the established pattern for product APIs in the builder's stack. Consistency reduces context-switching cost across products. | Node.js would allow a single-language stack with the Angular frontend. The backend is small enough that language choice is irrelevant to maintenance cost. |
| No caching of generation results | Every generation is preference-dependent and effectively unique. Caching would require hashing preference combinations and rarely produce hits. | Slightly higher Claude API cost per user session. At validation scale, this is single-digit dollars per month. |

---

## Patterns

### Prompt-as-Product

**When to use**: Any feature where the quality of Claude's output directly determines the user experience.

**How it works**: The system prompt and user message template are treated as production artifacts — versioned, tested against the quality rubric in the [Epic](./epic.md) success criteria, and iterated based on output quality. The prompt instructs Claude to return a JSON array with a strict schema, references the user's specific preferences in each rationale, and includes guardrails for cultural sensitivity and pronunciation accuracy.

**Example**: The generation prompt includes the parent's stated style preference ("modern") and origin preference ("Scandinavian") in the instructions, then requires Claude to reference these in each name's rationale field. A name card for "Saga" would explain that it fits because it's a modern revival of a traditional Norse name — directly addressing both stated preferences.

### Server-Side Paywall Enforcement

**When to use**: Any freemium feature where client-side enforcement is trivially bypassable.

**How it works**: The backend tracks generation count per device ID. Each generation request checks the count against the free tier limit before calling Claude. If the limit is exceeded and no valid receipt is on file, the backend returns a paywall response instead of generating names. The client displays the subscription offer based on this response.

**Example**: A device has used 3 of 3 free generation rounds. The next generate request hits the backend, `UsageMeter` finds the limit reached, and the response includes a `paywall: true` flag instead of name cards. The client renders the StoreKit subscription sheet.

### Structured AI Output

**When to use**: Any Claude API call where the response needs to be parsed and rendered as UI components.

**How it works**: The prompt specifies the exact JSON schema expected in the response. The backend validates the response structure before forwarding to the client. Malformed responses trigger a retry with the same input — Claude's structured output reliability is high enough that retries are rare but necessary as a safety net.

**Example**: The generation prompt ends with explicit formatting instructions: return an array of objects, each with `name`, `pronunciation`, `origin`, `meaning`, `popularity` (enum: common, rising, rare), and `rationale` (string referencing user preferences). The backend validates these fields exist before returning the response.

---

## Execution Flow

```
[Phase 1: Foundation]
  Preference Input Flow ──→ AI Generation Engine
                                    │
[Phase 2: Experience]               ▼
  Name Card UI + Results ◄──► Favorites + Sharing
                                    │
[Phase 3: Monetization]             ▼
                              Paywall + Subscription
```

Phase 1 is strictly sequential — the generation engine needs structured preference input to function. Phase 2 tasks run in parallel: the results screen consumes generation output while favorites consumes the same name card data structure independently. Phase 3 depends on the results screen existing (the paywall gates access to generation, which surfaces through results), but can be developed in parallel if the paywall gate uses a feature flag or configuration toggle.

The critical path runs through preference input → generation engine → results screen → paywall. Favorites and sharing branch off the critical path and can absorb schedule variance without delaying launch.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview