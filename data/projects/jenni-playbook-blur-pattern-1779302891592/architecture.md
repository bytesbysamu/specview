# 🏗️ Solution Architecture: Jenni Playbook Blur Pattern

## Architecture Overview

The blur pattern is a conversion funnel expressed as system architecture. A visitor arrives, pastes a brain dump, and receives a fully rendered analysis document with no authentication barrier. That analysis is the hook — it proves the pipeline works in under sixty seconds. Below the analysis, four additional documents — epic, solution architecture, timeline, and implementation guide — render with visible titles and section headers but blurred body content. The visitor sees that interconnected value exists, sees cross-references between documents pointing to content they cannot read, and feels the psychological tension that converts. The system must make the free tier feel generous and the blur wall feel inevitable.

The architectural challenge is that this funnel touches every layer of the existing system. Anonymous users need a session identity without authentication. The generation pipeline currently assumes an authenticated user with a project. The Angular frontend currently renders all spec content identically — there is no concept of a locked document. Stripe must gate access without introducing a heavyweight auth-before-value flow. Each of these concerns must be addressed without violating the thin-layer, adapter-boundary, and no-speculative-abstraction principles that keep the codebase navigable for a solo developer.

The core insight is that the blur wall is not a visual effect bolted onto the frontend — it is a data-layer concern. The API must return different payloads for free-tier and pro-tier requests against the same project. Free-tier responses include full content for the analysis document and metadata-only responses (titles, section headers, word counts) for the remaining four documents. The frontend never receives blurred content and un-blurs it — it receives structured preview metadata and renders the blur presentation locally. This prevents any client-side bypass of the paywall.

## Design Principles

| Principle | Application in This Epic |
|-----------|--------------------------|
| P1 — Adapter Boundary | Stripe calls go through a single `payments/adapter.py` module. No route or service file imports Stripe SDK directly. Swap to LemonSqueezy or Paddle later without touching business logic. |
| P2 — Thin HTTP Layer | New routes for anonymous analysis, blur-wall preview, and payment webhooks validate input, call service functions, and return responses. No conversion logic, no Stripe session creation inside route handlers. |
| P3 — Async 202 + Polling | Anonymous analysis generation reuses the existing background-thread pattern from `spec_gen` bootstrap. POST returns 202 with a job ID; the frontend polls until the analysis is ready. Same pattern, new entry point. |
| P4 — No Speculative Abstractions | One payment provider (Stripe). One free tier, one pro tier. No plan registry, no feature-flag framework, no A/B test infrastructure. Measure conversion with event counts and a single funnel query. |
| P5 — OpenAPI-First | New anonymous and payment endpoints are defined in `openapi.yaml` before any route is written. The blur-wall preview response schema is a contract — frontend and backend agree on structure before either builds. |
| P7 — File Size & Structure | Each new concern (anonymous session, blur preview, payment adapter, analytics events) gets its own module. No file exceeds 200 lines. |

## Component Design

### Anonymous Session Identity

**Purpose**: Track a visitor from first pageview through analysis generation, blur-wall interaction, and eventual signup — without requiring authentication at any step before payment.

The system generates a session ID client-side on first visit and persists it in `localStorage`. This ID accompanies every API request as a header. The backend treats it as an opaque correlation key for analytics events. When the visitor eventually signs up, the signup flow sends the anonymous session ID alongside the new account credentials, allowing the analytics pipeline to stitch the pre-auth and post-auth funnels into one journey.

The anonymous session is not an account. It has no server-side record beyond analytics events. The analysis document generated for an anonymous visitor is stored on the server keyed by a project ID (same as today), but the project is marked as `anonymous: true` with the session ID attached. On signup, anonymous projects are claimed by associating the session ID's projects with the new user account.

### Anonymous Analysis Generation

**Purpose**: Let an unauthenticated visitor submit a brain dump and receive a fully rendered analysis document — the free-tier hook that proves time-to-value.

This component reuses the existing `spec_gen` bootstrap workflow but strips the authentication requirement. A new route accepts a brain dump payload plus the anonymous session ID, creates a project record marked anonymous, and kicks off only the analysis step of the generation pipeline. The existing `adapter.py` handles the AI call. The existing background-thread-and-polling pattern handles the async lifecycle.

The critical constraint is cost. Every anonymous analysis burns tokens with no guarantee of conversion. The architecture caps anonymous generation to the analysis document only — no epic, no architecture, no timeline, no implementation guide. The analysis prompt is tuned to produce a complete, valuable document in a single chain call (no multi-step correction loop for free-tier). Token cost per free analysis must be measured and monitored. If cost per analysis exceeds the threshold that makes 100+ free runs per day unsustainable, the analysis prompt is shortened — the funnel is not removed.

### Blur-Wall Preview Renderer

**Purpose**: Show the structure and interconnectedness of the four locked documents without revealing content, creating the psychological suspension that drives conversion.

The API exposes a preview endpoint that returns metadata for each locked document type: document title, section headers (H2 and H3), approximate word count per section, and cross-reference mentions to other documents. This is enough for the frontend to render a document skeleton that looks real and rich without containing readable content.

The frontend renders these skeletons using the existing newspaper design system — same typography, same layout, same section-header styling — but applies a CSS blur filter to placeholder paragraph blocks and overlays an upgrade CTA per document. The placeholders are not the real content blurred; they are generated text blocks sized to match the reported word counts. This is a deliberate choice: even if a visitor disables CSS blur, they see meaningless placeholder text, not the actual spec content.

Cross-reference rendering is the conversion multiplier. When the analysis document mentions "see the [Epic](./epic.md) for task breakdown" and the epic preview shows a section header called "Tasks" with five visible sub-headers but blurred descriptions, the visitor sees the pipeline's interconnection without being able to use it. That visible-but-unreachable cross-reference is the Jenni citation pattern adapted for multi-document specs.

### Conversion Analytics Pipeline

**Purpose**: Measure the anonymous-analyze → signup funnel with enough granularity to diagnose where visitors drop off, so conversion can be improved before Show HN.

The analytics pipeline is a lightweight event-logging system, not a third-party analytics integration. Each funnel step emits a named event with the anonymous session ID and a timestamp: `page_land`, `braindump_paste`, `analysis_start`, `analysis_view`, `blur_scroll` (visitor scrolled into the blur wall), `blur_cta_click` (visitor clicked an upgrade button), `signup_start`, `signup_complete`, `payment_start`, `payment_complete`. Events are POST-ed to a thin Flask endpoint and stored as append-only JSON lines in a flat file per day.

A stats endpoint aggregates these events into a funnel view: counts per step, drop-off rates between steps, and a conversion rate from `analysis_view` to `signup_complete`. This is the dashboard that answers the 3% gate question. No Postgres, no Redis, no third-party analytics — just structured event files and a Python aggregation function.

The reason for building this in-house rather than using Mixpanel or PostHog is principle P4: the system needs one funnel with seven steps. A third-party analytics tool introduces a dependency, a data-export concern, and a configuration surface that is not justified by the complexity of the question being asked. If the funnel grows past ten events or needs cohort analysis, revisit — but not before.

### Auth and Payment Gate

**Purpose**: Convert blur-wall interest into paid access with the minimum friction path between "I want this" and "I have this."

The authentication layer uses the existing `modules/auth` JWT system. Signup is a new page that accepts email and password, creates an account, and issues a JWT. The signup page receives the anonymous session ID from `localStorage` and sends it to the backend so anonymous projects and analytics events are stitched to the new account.

Stripe Checkout handles payment. The payment flow is: visitor clicks upgrade CTA → signup (if not already authenticated) → Stripe Checkout session → redirect back with success/cancel. The Stripe integration lives behind `modules/payments/adapter.py`, which exposes two functions: create a checkout session and verify a webhook event. No other module imports Stripe. The webhook handler updates the user record to `tier: pro` and triggers generation of the remaining four documents for any anonymous projects associated with that user.

The architectural decision is whether to require signup before showing the blur wall or after the visitor clicks upgrade. The answer is after — the blur wall must be visible to fully anonymous visitors. Requiring signup before seeing the blur wall adds friction before the psychological trigger fires. The visitor must feel the itch before being asked to act on it. Signup happens only when they click the CTA, which means they have already decided to convert.

### Pro Tier Unlock and Full Suite Delivery

**Purpose**: Deliver the remaining four documents after payment completes, turning the blur-wall promise into the full spec suite.

On payment confirmation (via Stripe webhook), the backend triggers the full generation pipeline for the four remaining documents: epic, solution architecture, timeline, and implementation guide. These are generated fresh using the analysis document as input context — the same pipeline that exists today, minus the analysis step which already ran during the free tier.

The alternative — pre-generating all five documents during the free tier and simply revealing them on payment — is rejected for two reasons. First, it quintuples the token cost for every visitor who never converts, and at a projected 97% non-conversion rate, that is catastrophic to unit economics. Second, it means the blur-wall preview must contain real section headers from real generated content, which requires running the full pipeline before the visitor has signaled any intent to pay. Generating only the analysis for free and generating the rest on payment aligns cost with conversion probability.

The trade-off is that the blur-wall preview shows synthetic section headers rather than headers from actual generated content. The section headers displayed in the blur wall are canonical — they come from the prompt templates that define each document type's structure. Since the generation pipeline uses structured prompts that produce predictable section headers, the preview headers closely match what the final documents will contain. If a visitor upgrades and sees section headers that differ slightly from the preview, that is acceptable — the value was never in the exact headers but in the content beneath them.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 17 (existing `web-ng`) | The blur-wall components, anonymous flow, and CTA overlays are new standalone components added to the existing flat structure. No framework change. |
| Frontend blur rendering | CSS `filter: blur()` on placeholder blocks | Native CSS, no library. Placeholder text blocks sized by word-count metadata. Degradation: if blur is stripped, placeholder text is meaningless — security does not depend on CSS. |
| Backend | Flask (existing `api/`) | New routes in `modules/anon/` for anonymous analysis, `modules/payments/` for Stripe adapter. Reuses `modules/runtime/chain/` for AI calls. |
| Payment | Stripe Checkout (server-side session creation) | No embedded payment form — redirect to Stripe-hosted checkout. Minimizes PCI scope. Webhook for fulfillment. |
| Payment adapter | `modules/payments/adapter.py` | Single boundary module. Only file that imports `stripe`. Swap provider by replacing this file. |
| Analytics storage | Flat JSON-lines files in `data/analytics/` | One file per day. No database dependency. Aggregation reads files and computes funnel counts in Python. Sufficient for the volume (hundreds of events/day, not millions). |
| Auth | Existing `modules/auth` JWT | Extended with anonymous-session-to-user stitching on signup. No new auth framework. |
| Background generation | Existing `threading.Thread` + in-process state dict | Same pattern as current `spec_gen` bootstrap. No new job infrastructure. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| API returns preview metadata, not blurred content | Prevents client-side paywall bypass entirely. A visitor who inspects network requests sees section headers and word counts — never actual document text. | Frontend must build a convincing blur-wall presentation from metadata alone. Requires thoughtful placeholder generation to look realistic. |
| Generate analysis only for free tier; generate remaining four on payment | Token cost scales with conversion, not traffic. At 3% conversion and 100 free analyses/day, only 3 visitors/day trigger the expensive four-document pipeline. | Post-payment generation adds 60–120 seconds of wait time after payment. Mitigated by showing a progress screen with the 202-polling pattern — the visitor already experienced this pattern during analysis generation. |
| Canonical section headers in blur preview instead of pre-generated real headers | Avoids running the full pipeline for non-paying visitors. Keeps free-tier cost to one AI call per visitor. | Slight mismatch possible between preview headers and final generated headers. Acceptable because the conversion trigger is the visible structure and cross-references, not exact header text. |
| In-house analytics over third-party (Mixpanel, PostHog) | One funnel, seven events, one question (is it above 3%?). Third-party tool adds dependency, data residency concern, and configuration overhead not justified by the problem's simplicity. | No cohort analysis, no retention curves, no automatic dashboards. If the funnel question evolves past simple step-counting, migrate to PostHog. |
| Signup required only after CTA click, not before blur wall | The blur wall is the psychological trigger. Showing it to fully anonymous visitors maximizes the number of people who experience the itch. Gating it behind signup means fewer people feel the trigger. | Anonymous project management is more complex — must handle project claiming on signup. Worth it for higher top-of-funnel exposure to the conversion mechanic. |
| Stripe Checkout (redirect) over embedded Stripe Elements | Zero PCI surface. No card form on Specview's domain. Stripe handles the entire payment UI. Faster to implement for a solo developer. | Less control over checkout UX. Visitor leaves the Specview domain momentarily. Acceptable for V1 — Jenni used the same approach at early scale. |
| One free analysis per anonymous session, not unlimited | Prevents token-cost abuse from visitors who generate dozens of analyses without converting. Session ID in `localStorage` is the soft gate; not tamper-proof but sufficient for honest visitors. | Determined users can clear storage and regenerate. That is acceptable — they are engaging deeply with the product, which is itself a positive signal. Hard rate-limiting by IP comes later only if abuse is measured. |
| Flat-file analytics over SQLite | Append-only JSON lines require no schema, no migrations, no connection management. A Python function reads and aggregates on demand. The data volume (hundreds of events/day) makes database overhead pointless. | No indexing, no ad-hoc queries. Funnel aggregation is the only query. If query patterns diversify, migrate to SQLite — a one-file change in the aggregation module. |

## Data Flow

### Free Tier Journey

Visitor lands → anonymous session ID generated client-side → brain dump pasted → POST to anonymous analysis endpoint (no auth) → 202 returned with job ID → background thread generates analysis via chain adapter → frontend polls until done → analysis rendered in full → four blur-wall previews rendered below with metadata from canonical templates → analytics events emitted at each step.

### Conversion Journey

Visitor clicks upgrade CTA on any blurred document → routed to signup page (session ID preserved) → account created, anonymous projects claimed → Stripe Checkout session created via payments adapter → visitor completes payment on Stripe → webhook fires → user record updated to `tier: pro` → four-document generation triggered as background job → frontend polls until suite is complete → full spec suite rendered, blur wall removed.

## Module Boundaries

| Module | Responsibility | Depends On |
|--------|---------------|------------|
| `modules/anon/routes.py` | Anonymous analysis submission endpoint, anonymous session validation | `modules/anon/service.py` |
| `modules/anon/service.py` | Anonymous project creation, session-to-user claiming on signup | `modules/data/`, `modules/ai/workflows/spec_gen/` |
| `modules/payments/adapter.py` | Stripe checkout session creation, webhook signature verification | Stripe SDK (sole import point) |
| `modules/payments/routes.py` | Checkout initiation endpoint, webhook receiver | `modules/payments/service.py` |
| `modules/payments/service.py` | Post-payment user upgrade, generation trigger for remaining docs | `modules/payments/adapter.py`, `modules/auth/`, `modules/ai/workflows/spec_gen/` |
| `modules/analytics/routes.py` | Event ingestion endpoint, funnel stats endpoint | `modules/analytics/service.py` |
| `modules/analytics/service.py` | Event storage (append to JSON lines), funnel aggregation | File system (`data/analytics/`) |
| `web-ng` — `blur-preview.component.ts` | Renders metadata-only document skeleton with blur overlay and CTA | `services/projects.service.ts` |
| `web-ng` — `anon-analyze.component.ts` | Anonymous brain-dump submission and analysis polling | `services/ai.service.ts` |
| `web-ng` — `conversion.service.ts` | Emits funnel analytics events, manages anonymous session ID | `services/auth.service.ts` |

## Security Considerations

The blur wall is a server-side access control, not a client-side visual trick. The API never returns document content for locked documents to unauthenticated or free-tier users. The preview endpoint returns only titles, section headers, and word counts. Even if a visitor reverse-engineers the API, there is no endpoint that serves locked content without a valid pro-tier JWT.

Stripe webhook verification uses the signing secret to ensure fulfillment events originate from Stripe. The payments adapter validates the signature before any state change.

Anonymous session IDs are client-generated UUIDs with no server-side session store. They are correlation keys, not authentication tokens. A visitor who fabricates a session ID gains nothing — they can generate one free analysis per session, same as any visitor.

## Capacity and Cost Model

The critical economic constraint is token cost per free-tier analysis. Each anonymous analysis is one AI call through the chain adapter. The prompt must be tuned so that the analysis document is valuable enough to convert but cheap enough to sustain at scale. The target is 100+ free analyses per day at a token cost that stays below the revenue from the 3% who convert.

Generation of the four pro-tier documents reuses the existing multi-step pipeline, which involves four sequential AI calls (one per document type, each building on the previous). This cost is borne only by paying users and is therefore self-funding.

The analytics pipeline stores approximately one kilobyte per visitor session (seven events at ~150 bytes each). At 1,000 visitors per day, that is one megabyte per day — negligible. Aggregation reads the current day's file plus historical files for trend comparison.

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this architecture
- [Epic](./epic.md) — Scope, tasks, and success criteria for the blur pattern
- [Timeline](./timeline.md) — Delivery sequence and status tracking