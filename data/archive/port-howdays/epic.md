---
sidebar_position: 2
---

# 🎯 howDays Patterns Port – Epic

**Purpose**: Define scope and tasks for porting proven howDays patterns into Bubls shared modules.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed and decisions made.

---

## Business Value

Bubls is entering distribution — the first time strangers will use the app. Three things break when strangers arrive that don't break with friends: payments need to actually work, errors need to produce messages humans can act on, and the app needs to degrade gracefully on bad connections.

howDays has solved all three on the identical stack. The RevenueCat integration handles Apple's receipt validation edge cases (family sharing, billing retry, grace periods) that take weeks to discover and debug from scratch. The ErrorParserService turns `HttpErrorResponse`, `TypeError`, `DOMException`, and unknown throws into consistent toast-ready messages — something Bubls currently does ad-hoc with different formats per feature. The Capacitor wrapper pattern prevents the class of bugs where a plugin initializes twice or crashes on web.

Porting these as shared modules means Bubls gets production-proven infrastructure without the discovery cost. Each module is self-contained — features opt in when they're ready, and nothing existing breaks during the port.

---

## Scope

### What This Epic Covers

- RevenueCat service with paywall modal, entitlement checking, and server sync
- ErrorParserService for normalizing unknown error types into user-facing messages
- SQLite service layer with version-based migration runner (no tables)
- Capacitor base service pattern for standardized plugin lifecycle
- Mock mode for every module (environment flag gated)
- Unit tests for each module matching Bubls test conventions

### What This Epic Does NOT Cover

- ❌ Wiring RevenueCat into existing features (separate task per feature)
- ❌ Replacing existing error handling call sites (separate migration task)
- ❌ Creating SQLite tables or migrations (deferred until consumer exists)
- ❌ Refactoring existing `PhotoLibraryService` or `VoiceInputService` to use the new base pattern
- ❌ RevenueCat webhook integration (server sync on app open is sufficient for v1)
- ❌ Android configuration (iOS-first, Android when validated)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Capacitor Base Service** | None | 2 | 0.5 day | High |
| 2 | **ErrorParserService** | None | 1 | 0.5 day | High |
| 3 | **RevenueCat Service + Paywall Modal** | 1 | — | 2 days | High |
| 4 | **Server Entitlements Sync Endpoint** | 3 | — | 0.5 day | High |
| 5 | **SQLite Service Layer** | 1 | — | 1 day | Medium |

### Task Details

#### Task 1: Capacitor Base Service

Extract the standardized Capacitor plugin wrapper pattern from howDays into `src/app/shared/capacitor/`. The base service handles: (a) one-time initialization with a guard against double-init, (b) platform detection that returns mock data on web instead of crashing, (c) typed API surface that wraps the raw Capacitor plugin. Port the pattern as an abstract base or a factory function — whichever howDays uses. Include a concrete example (e.g., `HapticsService`) to validate the pattern compiles and tests pass. All new Capacitor plugin integrations in Bubls will extend or use this pattern.

#### Task 2: ErrorParserService

Port `ErrorParserService` from howDays into `src/app/shared/error/`. The service accepts `unknown` and returns a `{ message: string; code?: string; retryable: boolean }` object. It handles: `HttpErrorResponse` (extract server message or fall back to status text), `TypeError` (network failures), `DOMException` (aborted requests), plain strings, and unknown objects. Include the toast integration helper that maps parsed errors to Ionic toast controller calls. Tests cover each error type with concrete assertions — no stubs.

#### Task 3: RevenueCat Service + Paywall Modal

Port the RevenueCat integration from howDays into `src/app/shared/payments/`. Three components: (a) `RevenueCatService` — initialize SDK, fetch offerings, check entitlements, purchase package, restore purchases. Adapter pattern with mock mode that returns configurable entitlements via environment flag. (b) `PaywallModalComponent` — standalone Ionic modal showing current offering, price, and purchase button. OnPush, signals, `data-test` selectors on all interactive elements. (c) `FeatureGateGuard` — route guard that checks entitlements and redirects to paywall modal when a Pro feature is accessed by a free user (null object pattern: paywall page, never 404). Configure for two tiers: Free (limited daily uses) and Pro ($4.99/mo, unlimited).

#### Task 4: Server Entitlements Sync Endpoint

Add `POST /api/entitlements/sync` to the Flask backend in `server/modules/entitlements/`. The endpoint receives the client's current RevenueCat entitlements on app open and upserts them into the user's row in Neon. Updates the `enabled_features` JSONB and adds a `last_entitlement_sync` timestamp. This is a write-only sync — the client does not read entitlements from the server. The server uses this data for analytics and server-side rate limit decisions. SQLAlchemy model, no raw SQL. Rate limited to 1 sync per user per 5 minutes.

#### Task 5: SQLite Service Layer

Port the SQLite service from howDays into `src/app/shared/sqlite/`. Two components: (a) `SqliteService` — wraps `@capacitor-community/sqlite`, handles database open/close lifecycle, provides typed query/execute methods. Uses the Capacitor base service pattern from Task 1. Mock mode returns empty results on web. (b) `MigrationRunner` — reads a version number from a `_migrations` table, applies numbered migration files in order, updates version. Port the runner logic but do not create any application tables or migrations. The trigger for creating tables: Neon p95 latency exceeds 2s on cellular for gallery reads post-distribution. Until then, the module is available but dormant.

---

## Success Criteria

- ✅ `RevenueCatService` initializes, fetches offerings, and completes a sandbox purchase on iOS simulator
- ✅ `PaywallModalComponent` renders with correct price and purchase button; `data-test` selectors on all interactive elements
- ✅ `FeatureGateGuard` redirects free users to paywall, passes Pro users through — verified with mock entitlements
- ✅ `ErrorParserService` produces consistent `{ message, code, retryable }` for all 5 error types (HttpErrorResponse, TypeError, DOMException, string, unknown)
- ✅ `SqliteService` opens a database and runs a no-op migration on iOS simulator; returns mock data on web
- ✅ All Capacitor services use the base pattern: single init, web guard, typed API
- ✅ Every module has mock mode gated by environment flag
- ✅ Zero changes to existing feature code — all modules land in `src/app/shared/` or `server/modules/`
- ✅ All tests pass with concrete assertions, no stubs, `data-test` selectors in component tests
- ✅ Unprompted return within 7 days by test users encountering the paywall (retention signal, not purchase conversion)

---

## Non-Goals

- ❌ RevenueCat Android configuration — iOS-first until validation
- ❌ Server-side receipt validation — RevenueCat handles this; server trusts client-synced entitlements for analytics
- ❌ Offline-first gallery caching — SQLite layer is ported but dormant until latency data justifies tables
- ❌ Migrating existing ad-hoc error handling — separate task after ErrorParserService lands
- ❌ RevenueCat webhooks — app-open sync is sufficient; webhooks add complexity without a current need

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

