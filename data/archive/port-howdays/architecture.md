---
sidebar_position: 3
---

# 🏗️ howDays Patterns Port – Solution Architecture

**Purpose**: Technical design for porting howDays patterns into Bubls shared modules.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Four self-contained modules land in `src/app/shared/` (frontend) and `server/modules/` (backend). Each module follows the Adapter pattern: a public interface with mock mode gated by environment flag, so features can develop against mocks before the real integration is wired. The Capacitor base service establishes a lifecycle pattern that the RevenueCat and SQLite modules build on top of.

The dependency graph is shallow. The Capacitor base service is the only shared dependency — RevenueCat and SQLite both use it, but ErrorParserService is fully independent. This means Tasks 1 and 2 run in parallel, Task 3 depends on Task 1, and Task 5 depends on Task 1. Task 4 (server endpoint) depends on Task 3 only for the entitlements shape definition.

No existing Bubls code changes. Features opt into these modules in follow-up tasks by importing from `shared/` — the same bounded-context rule that governs feature code applies here.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Adapter pattern (every service) | Each module exposes a single adapter interface. Mock mode via `MOCK_PAYMENTS=true`, `MOCK_SQLITE=true` env flags. Features import the adapter, never the provider |
| Feature guard with null object | `FeatureGateGuard` shows paywall modal, never 404. Disabled payment → upgrade page with clear CTA |
| Not-yet-built is the right state | SQLite migration runner ported, zero tables created. Trigger: Neon p95 > 2s on cellular |
| No cross-feature imports | All modules in `shared/`. Features import from `shared/payments`, `shared/error`, `shared/sqlite`, `shared/capacitor` |
| Standalone components, OnPush, signals | PaywallModalComponent follows Angular 19 patterns. State via signals, no NgModules |
| `data-test` selectors only | Every interactive element in PaywallModalComponent gets a `data-test` attribute |
| Always ORM, never raw SQL | Server entitlements sync uses SQLAlchemy model for upsert |

---

## Component Design

### Task 1: Capacitor Base Service

**Purpose**: Standardize Capacitor plugin lifecycle — initialize once, guard against web, expose typed API.

**Components**:
- `src/app/shared/capacitor/capacitor-base.service.ts` — Abstract base or factory function. Handles: (a) `initialized` signal that guards against double-init, (b) `platform` check via `Capacitor.isNativePlatform()` returning mock data on web, (c) typed wrapper methods that subclasses or consumers override per plugin.
- `src/app/shared/capacitor/capacitor-base.service.spec.ts` — Tests: web platform returns mock, native platform initializes once, second init is no-op, typed methods delegate to plugin.
- `src/app/shared/capacitor/haptics.service.ts` — Concrete example validating the pattern. Wraps `@capacitor/haptics`. On web: no-op. On native: delegates to plugin.

**Patterns**: Template Method (base defines lifecycle, subclass defines plugin-specific behavior). Adapter (web vs. native).

**Key decision**: Abstract class vs. factory function. howDays uses abstract class with `protected abstract initializePlugin(): Promise<void>` and `protected abstract getWebFallback(): T`. Port as-is — the abstract class communicates the contract more clearly than a factory, and Angular's `inject()` works naturally with class-based services.

### Task 2: ErrorParserService

**Purpose**: Normalize unknown error types into consistent, toast-ready messages.

**Components**:
- `src/app/shared/error/error-parser.service.ts` — Stateless service. Single method: `parse(error: unknown): ParsedError`. Returns `{ message: string; code?: string; retryable: boolean }`. Type-narrowing chain: `HttpErrorResponse` → `TypeError` → `DOMException` → `string` → fallback.
- `src/app/shared/error/error-parser.model.ts` — `ParsedError` interface. `ErrorCode` string union for known codes (`NETWORK`, `TIMEOUT`, `ABORT`, `SERVER`, `UNKNOWN`).
- `src/app/shared/error/toast-error.helper.ts` — Function that takes a `ParsedError` and Ionic `ToastController`, shows a toast with appropriate color (danger for non-retryable, warning for retryable) and optional retry button.
- `src/app/shared/error/error-parser.service.spec.ts` — Tests for each error type: `HttpErrorResponse` with body message, `HttpErrorResponse` with status-only, `TypeError` (network), `DOMException` (abort), plain string, `null`, `undefined`, random object.

**Patterns**: Chain of Responsibility (type narrowing). Anti-Corruption Layer (isolates domain from raw error formats).

**Error type mapping**:

| Input Type | `message` | `code` | `retryable` |
|------------|-----------|--------|-------------|
| `HttpErrorResponse` with body `{ message }` | Body message | `SERVER` | `status >= 500` |
| `HttpErrorResponse` without body message | Status text | `SERVER` | `status >= 500` |
| `TypeError` | "Network error — check your connection" | `NETWORK` | `true` |
| `DOMException` (name=AbortError) | "Request was cancelled" | `ABORT` | `false` |
| `string` | The string itself | `UNKNOWN` | `false` |
| `null` / `undefined` / unknown | "Something went wrong" | `UNKNOWN` | `false` |

### Task 3: RevenueCat Service + Paywall Modal

**Purpose**: Payments, entitlement checking, and paywall UX — ported from howDays.

**Components**:
- `src/app/shared/payments/revenuecat.service.ts` — Adapter wrapping `@revenuecat/purchases-capacitor`. Methods: `initialize()`, `getOfferings(): Signal<Offerings | null>`, `checkEntitlement(id: string): Signal<boolean>`, `purchase(package: Package): Promise<PurchaseResult>`, `restorePurchases(): Promise<void>`. Mock mode (`MOCK_PAYMENTS=true`): returns configurable entitlements from `payments.mock.ts`, skips SDK init. Uses Capacitor base service pattern from Task 1 — extends the abstract base, implements `initializePlugin()` (configure SDK with API key) and `getWebFallback()` (return mock offerings).
- `src/app/shared/payments/paywall-modal.component.ts` — Standalone Ionic modal. Inputs: `offering` signal. Displays: product title, price, billing period, feature list. Buttons: Purchase (`data-test="paywall-purchase"`), Restore (`data-test="paywall-restore"`), Close (`data-test="paywall-close"`). OnPush change detection. Loading state via signal during purchase flow. Error handling via ErrorParserService (Task 2).
- `src/app/shared/payments/paywall-modal.component.spec.ts` — TestBed with mocked `RevenueCatService`. Page object with `data-test` selectors. Tests: renders price from offering, purchase button triggers service call, loading state shown during purchase, error shows toast, restore triggers restore flow.
- `src/app/shared/payments/feature-gate.guard.ts` — Functional route guard. Checks `RevenueCatService.checkEntitlement('pro')`. If entitled: pass through. If not: open paywall modal, return `false`. Null object pattern — never 404, always paywall.
- `src/app/shared/payments/payments.mock.ts` — Mock offerings and entitlements for development and tests.
- `src/app/shared/payments/payments.model.ts` — `PurchaseResult`, `PaywallConfig` types. Product tier definitions: Free (3 uses/day), Pro ($4.99/mo, unlimited).

**Patterns**: Adapter (RevenueCat SDK vs. mock), Strategy (payment provider swappable), Feature Guard with Null Object (paywall, never 404).

**RevenueCat configuration**:

| Product | ID | Price | Entitlement |
|---------|----|-------|-------------|
| Bubls Free | `bubls_free` | $0 | (none) |
| Bubls Pro Monthly | `bubls_pro_monthly` | $4.99/mo | `pro` |

**Entitlement flow**:
```
App Open
  → RevenueCatService.initialize()
  → Fetch customer info
  → Update entitlement signals
  → Sync to server (Task 4)

Feature Access
  → FeatureGateGuard checks entitlement signal
  → Entitled: route activates
  → Not entitled: paywall modal opens
     → Purchase success: signal updates, route activates
     → Purchase cancel: stays on current page
```

### Task 4: Server Entitlements Sync Endpoint

**Purpose**: Receive client-synced entitlements for analytics and server-side gating.

**Components**:
- `server/modules/entitlements/__init__.py` — Flask blueprint registration.
- `server/modules/entitlements/routes.py` — `POST /api/entitlements/sync`. Accepts `{ user_id: str, entitlements: string[], synced_at: str }`. Upserts `enabled_features` JSONB and `last_entitlement_sync` timestamp on user row. Rate limited: 1 per user per 5 minutes. Returns `204 No Content`.
- `server/modules/entitlements/model.py` — SQLAlchemy model updates. Adds `last_entitlement_sync: DateTime` column to existing user model (Alembic migration).
- `server/modules/entitlements/dto.py` — Generated from OpenAPI spec. `EntitlementsSyncRequest` Pydantic model.
- `server/openapi/entitlements.yaml` — OpenAPI spec for the sync endpoint.
- `server/modules/entitlements/test_routes.py` — Tests: valid sync updates user, rate limit rejects within 5 minutes, missing user returns 404, malformed payload returns 422.

**Patterns**: Anti-Corruption Layer (client entitlement format → server JSONB), Adapter (SQLAlchemy, not raw SQL).

**Schema change**:
```sql
-- Via Alembic migration, not raw SQL
ALTER TABLE users ADD COLUMN last_entitlement_sync TIMESTAMP;
-- enabled_features JSONB already exists
```

### Task 5: SQLite Service Layer

**Purpose**: Offline-first data capability — ported but dormant until needed.

**Components**:
- `src/app/shared/sqlite/sqlite.service.ts` — Extends Capacitor base service. Wraps `@capacitor-community/sqlite`. Methods: `openDatabase(name: string): Promise<void>`, `query<T>(sql: string, params?: any[]): Promise<T[]>`, `execute(sql: string, params?: any[]): Promise<void>`, `close(): Promise<void>`. Web fallback: returns empty arrays for queries, no-ops for execute. Initializes SQLite plugin once via base service pattern.
- `src/app/shared/sqlite/migration-runner.ts` — Reads `_migrations` table for current version. Accepts an array of `Migration` objects (`{ version: number, up: string }`). Applies migrations in order, updates version. Creates `_migrations` table on first run if it doesn't exist.
- `src/app/shared/sqlite/sqlite.model.ts` — `Migration` interface, `QueryResult` type.
- `src/app/shared/sqlite/sqlite.mock.ts` — In-memory store for tests. Tracks executed queries for assertions.
- `src/app/shared/sqlite/sqlite.service.spec.ts` — Tests: opens database on native, returns empty on web, migration runner applies in order, migration runner skips already-applied, migration runner creates tracking table.

**Patterns**: Adapter (native SQLite vs. web mock), Template Method (base service lifecycle).

**Dormancy contract**: No application migrations exist. No feature imports `SqliteService`. The module is available for import but has zero runtime cost until a feature creates migrations and opens a database. Trigger condition for activation: Neon p95 latency > 2s on cellular for gallery reads, measured post-distribution via existing API response time logging.

---

## Execution Flow

```
[Phase 1 — parallel]
   Task 1 (Capacitor Base)  ──┐
   Task 2 (ErrorParser)       │
                               │
[Phase 2]                      ▼
   Task 3 (RevenueCat + Paywall) ← uses Task 1 base + Task 2 error handling
                               │
[Phase 3 — parallel]           ▼
   Task 4 (Server Sync) ← uses entitlement shape from Task 3
   Task 5 (SQLite) ← uses Task 1 base
```

**Critical path**: Task 1 → Task 3 → Task 4 (payments end-to-end).
**Total elapsed**: ~3.5 days with parallelization.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RevenueCat as client-side entitlement source of truth | RevenueCat checks on device, sync to server for analytics | RevenueCat handles receipt validation, grace periods, billing retry — duplicating server-side is waste. Server needs entitlements for rate limits and analytics, not for gating |
| Abstract class for Capacitor base, not factory function | Abstract class with `initializePlugin()` and `getWebFallback()` | Communicates the contract more explicitly. Angular `inject()` works naturally with class hierarchy. Matches howDays implementation for lowest-friction port |
| SQLite layer ported but dormant | Port service + runner, zero tables | Per Engineering Discipline: infrastructure without a consumer is speculative debt. Trigger: Neon p95 > 2s cellular. Until then, the module costs nothing |
| `enabled_features` JSONB becomes a projection, not source | Server upserts from client sync, never authoritative | Avoids dual-source-of-truth bugs. RevenueCat is the authority. Server is a read cache for analytics/rate-limits |
| No RevenueCat webhooks | App-open sync only | Webhooks add server complexity (signature verification, retry handling, event ordering). App-open sync is eventually consistent within minutes — good enough for analytics. Add webhooks when server-side gating becomes latency-sensitive |
| iOS only, no Android config | Skip Android RevenueCat setup | Bubls is iOS-first. Android config is mechanical (add API key, configure billing) but requires testing infrastructure that doesn't exist yet. Port when Android validation starts |
| ErrorParserService is standalone, no base service dependency | Independent module in `shared/error/` | Error parsing has nothing to do with Capacitor plugins. Keeping it independent means it works in any Angular context, including server-rendered or test harnesses |
| Two tiers only: Free and Pro | No Starter, no Unlimited | Reduce decision friction for first-time users. One upgrade path. Revisit tiers after 100 paying users provide pricing signal |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

