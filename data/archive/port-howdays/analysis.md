---
sidebar_position: 1
---

# 🔍 howDays Patterns Port – Analysis

**Purpose**: Surface the gaps in Bubls that howDays patterns close, and the decisions that need resolving before porting.

**Date**: 2026-04-18

---

## Summary

- **Problem**: Bubls is hitting distribution without payments, consistent errors, or a standardized Capacitor plugin pattern
- **Hard Constraints**: Same stack as howDays (Angular 19 + Ionic 8 + Capacitor 7), modules must land in `shared/` with zero feature-code changes
- **Open Questions**: 3 decisions to resolve before or during implementation
- **Dependencies**: RevenueCat account + product configuration, existing `enabled_features` JSONB on user model
- **Explicitly Out of Scope**: Rewriting existing feature services, creating SQLite tables without a consumer, migrating existing error handling call sites

---

## Hard Constraints Check

| Constraint | Status | Notes |
|------------|--------|-------|
| Neon Postgres only — no Supabase, no Firebase | ✅ Clear | RevenueCat is client-side entitlements, not auth. Server sync writes to Neon |
| Feature = bounded context, no cross-feature imports | ✅ Clear | Each port is a `shared/` module. Features import from shared, never from each other |
| Adapter pattern for all services | ✅ Clear | Each module exposes an adapter interface with mock mode via environment flag |
| No infrastructure before consumers exist | ⚠️ Tension | SQLite service layer has no current consumer. Resolution: port the service, defer table creation |
| Standalone components, OnPush, signals | ✅ Clear | Paywall modal follows this pattern |

---

## Open Questions

### 1. RevenueCat as entitlements source of truth vs. `enabled_features` JSONB

Two options on the table:

- **Option A**: RevenueCat is source of truth client-side. On app open, sync entitlements to server for analytics and server-side gating. The `enabled_features` JSONB becomes a read cache, not the authority.
- **Option B**: Server's `enabled_features` JSONB remains authoritative. RevenueCat purchase events update it via webhook. Client reads from server.

**Recommendation**: Option A. RevenueCat already handles receipt validation, grace periods, billing retry, and family sharing. Duplicating that logic server-side is pure waste. Client checks RevenueCat directly for gate decisions. Server receives a sync payload on app open for analytics and for any server-side enforcement (rate limits, API access). The `enabled_features` JSONB stays but becomes a projection of RevenueCat state, not the source.

### 2. SQLite port timing

The SQLite service layer has no current consumer in Bubls. Per Engineering Discipline ("not-yet-built is the right state for infrastructure nobody's asked for"), porting the full migration system now is speculative.

**Recommendation**: Port the `SqliteService` wrapper and migration runner as a shared module. Do not create any tables or migrations. The trigger condition for creating tables: Neon latency on cellular exceeds 2s p95 for gallery reads, measured after distribution launch. Until then, the module exists but does nothing.

### 3. Which Capacitor services to retroactively standardize

Bubls already has `PhotoLibraryService` and `VoiceInputService` that partially follow the wrapper pattern. Retroactively refactoring them to use the standardized base would improve consistency but touches existing feature code.

**Recommendation**: Do not refactor existing services in this epic. Port the standardized pattern into `shared/`. New Capacitor plugins use the standard pattern. Existing services get refactored in a separate task if/when they need changes for other reasons.

---

## Dependencies

| Dependency | Blocks | Status |
|------------|--------|--------|
| RevenueCat account created | Task 1 (RevenueCat module) | Needs Apple Developer + RevenueCat dashboard setup |
| RevenueCat products configured (Free + Pro $4.99/mo) | Task 1 | Needs product IDs from dashboard |
| Existing `enabled_features` JSONB on user model | Task 1 (server sync) | Already exists in Neon |
| howDays source code access | All tasks | Available in local repo |

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

