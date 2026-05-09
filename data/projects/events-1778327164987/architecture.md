# 🏗️ Solution Architecture: events

## Architecture Overview

The events expansion is a **catalog widening** problem, not a platform problem. Bubls already has an events screen, an event-source boundary, and filter chips — concerts and theater slot into that existing shape rather than introducing new infrastructure. The mental model is: one new adapter behind the existing source boundary, two new flat tags on the existing filter UI, and one new daily refresh thread. Nothing else moves.

The key insight is that concerts and theater are not separate features — they are two new values of an existing `category` field. Treating them as a generic "more events" expansion (multi-source, hierarchical genre, ranking) would violate P4 by building abstractions for problems that don't exist yet. The MVP scope is intentionally narrow: prove the catalog renders well on iOS with one source and flat tags before any ranking, dedup, or affiliate work.

Component-wise, the system stays a thin Flask service fronting a Capacitor/Ionic Angular app. The new concert/theater adapter is the only AI/external boundary added; the rest of the stack — DTOs from `openapi.yaml`, route handler that validates and delegates, in-process daemon thread for the refresh job — reuses patterns already proven in spec-doc and humanize-me.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | One new adapter module behind the existing event-source interface. Routes and services never touch the source provider directly. |
| P2 — Thin HTTP Layer | The events route validates filter input, delegates to the events service, returns the DTO. No filtering, sorting, or source-specific shaping in the handler. |
| P3 — Async 202 + Polling | Daily batch refresh runs in a daemon thread on a timer; the user-facing GET stays synchronous (fast cache read). No held-open connections, no Redis. |
| P4 — No Speculative Abstractions | Flat tags only (no genre hierarchy). Single source (no aggregation framework). One city (no multi-region config). Three near-identical category branches beat a category registry. |
| P5 — OpenAPI-First | `openapi.yaml` gains `concert` and `theater` as `category` enum values before any code changes. DTOs regenerate. Routes implement the updated contract. |
| P7 — File Size & Structure | Adapter, service additions, and route changes each stay under 200 lines. The epic explicitly budgets <200 backend lines added. |

## Component Design

### Concert/Theater Source Adapter
**Purpose**: Single boundary to the chosen external listings source. Translates the source's native shape into Bubls' internal `Event` DTO with `category` set to `concert` or `theater`. Owns retries, timeouts, and parsing — every other module treats it as a black box returning a list of events.

**Why a separate adapter and not extending an existing one**: P1 demands one provider per adapter file. If a future source replaces this one, only this file changes. The existing event-source interface stays untouched.

### Events Service Extension
**Purpose**: The existing service that backs the events endpoint gains awareness of the new categories — meaning it accepts `concert` and `theater` in the filter input, queries the cache built by the refresh job, and returns merged results alongside existing categories.

**Why extend rather than fork**: Concert and theater are values of the same `category` field that already exists. Forking the endpoint would create two parallel code paths that filter chips would need to reconcile in the UI. One endpoint, more values, less surface area.

### Daily Refresh Daemon
**Purpose**: A `threading.Thread(daemon=True)` started at app boot that refreshes the cache from the source adapter on a daily cadence. Cache is module-level dict keyed by category. On failure, the daemon logs and retries on the next tick — stale data is preferred to no data.

**Why in-process and not a cron/queue**: Builder constraints disallow Redis and external queues. Single-worker gunicorn (per Trendfy reference) makes module-level state safe. Daily cadence means a missed tick is recovered within hours — no orchestration needed.

**Why daemon thread**: Code rule — never block server shutdown. Daemon threads die with the process; no graceful-shutdown coordination required.

### Filter Chips (Frontend)
**Purpose**: Two flat tags (`concert`, `theater`) added to the existing chip array on the events screen. Selection state already wired through the existing filter signal — new chips reuse the same mechanism.

**Why flat and not hierarchical**: P4 — there is no evidence that users want to filter by classical-vs-pop or opera-vs-spoken-theater. If usage data later shows the buckets feel too coarse, hierarchy is a follow-up trigger explicitly listed in the epic's "does not cover."

### Event Card + Detail Rendering
**Purpose**: List card and detail view render concert/theater entries with a category badge, title, venue, start time, and an external link. iOS-first — the production build (`ng build --configuration production`) is the merge gate.

**Why no in-app ticket flow**: Out of scope per epic. External link reuses existing link-out behavior. Affiliate work is gated on an explicit revenue decision.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Mobile shell | Ionic + Capacitor (iOS 16+) | Existing Bubls stack; no reason to deviate for a catalog change |
| Frontend framework | Angular standalone components, signals | Existing Bubls stack; filter chip state already on signals |
| Backend | Flask Blueprints, Python 3.11 | Existing Bubls API; thin layer pattern (humanize-me reference) |
| Contract | `openapi.yaml` + generated DTOs | P5 — contract-first; concert/theater added as enum values |
| External boundary | Single source adapter module | P1 — one provider per adapter; deferred decision: which source (Task 1) |
| Refresh scheduling | `threading.Thread(daemon=True)` with sleep loop | No Redis, no external queue; daily cadence tolerates in-process loss |
| Deploy | Existing Bubls Docker Compose / Coolify pipeline | No infra changes |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Single source for MVP | Catalog breadth matters more than perfect coverage; one source proves the rendering and filter contract end-to-end before investing in dedup logic | Catalog gaps are possible; explicit follow-up trigger if users complain about missing events |
| Flat tags (`concert`, `theater`) | Matches today's filter UI shape; avoids hierarchy decisions before any usage data exists (P4) | Cannot filter by genre or theater type; revisited if filter feels too coarse |
| Clubs/DJ sets folded into `concert`; opera/dance folded into `theater` | Two buckets keep the chip row scannable on a phone; the alternative is four chips for an unproven UI | Some users may expect a separate `clubs` chip — explicit MVP trade-off, observable via filter usage |
| Daily batch, not real-time | Concert and theater listings change on the order of days, not minutes; daily refresh matches the data's natural cadence and stays trivial to operate | Same-day additions appear up to 24h late; trigger for real-time is stale-listing complaints |
| In-process cache, no DB | Builder constraints: no Redis, no Postgres for this project. Module-level dict + single worker is the proven pattern (spec-doc reference) | Cache lost on restart — first request after deploy may be slow until daemon repopulates; acceptable for daily-batch data |
| Extend events endpoint, don't fork | Concert and theater are `category` values, not separate resources; one endpoint = one DTO shape = simpler frontend | Endpoint response grows by category enum surface; no functional cost |
| External link-out, no affiliate | Affiliate requires legal/commercial decisions out of scope for an MVP catalog expansion | No revenue capture this iteration; explicit trigger gates the next step |
| Frontend mock-first (Task 2 parallel with Task 3) | Builder preference: build UI against mock data, then make Flask match the contract | Brief duplication of shape between mock and real adapter — resolved when Task 4 wires the live endpoint |
| Source decision deferred to Task 1 | Source selection is a research call (coverage, terms, stability) that shouldn't block UI work; the adapter boundary makes the choice swappable | Task 1 is a hard blocker on Task 3; mitigated by Task 2 running in parallel |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking