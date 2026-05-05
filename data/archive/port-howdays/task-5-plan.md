# Task 5: SQLite Service Layer (shell only) — Plan

## Goal

Port howDays' SQLite service pattern into `src/app/shared/sqlite/sqlite.service.ts`. Abstract service wrapping `@capacitor-community/sqlite`. Initialize connection, version-based upgrade statements, platform guard (web = no-op). No tables created.

## Design Decisions

- **Extends CapacitorBaseService** from Task 1 — consistent with architecture.md.
- **howDays pattern**: `SqliteService` wraps a `CapacitorSqliteService` which wraps `@capacitor-community/sqlite`. In Bubls, the base service already provides the native/web guard, so we simplify: `SqliteService` extends `CapacitorBaseService` directly and wraps `CapacitorSQLite` static calls internally.
- **Migration runner**: Accepts upgrade statement arrays, delegates to the plugin's `addUpgradeStatement`. No application tables.
- **Web no-op**: queries return empty arrays, executes are no-ops.
- **Mock mode**: Controlled by `environment.useMocks.sqlite` flag for tests.
- **Dormancy**: Module exists, no consumer imports it. Zero runtime cost.

## Files

| File | Action |
|------|--------|
| `src/app/shared/sqlite/sqlite.service.ts` | Service shell — extends CapacitorBaseService |
| `src/app/shared/sqlite/sqlite.model.ts` | `Migration`, `QueryResult`, `RunOptions`, `QueryOptions` interfaces |
| `src/app/shared/sqlite/sqlite.mock.ts` | In-memory mock for tests |
| `src/app/shared/sqlite/sqlite.service.spec.ts` | Tests: init, web no-op, query/execute delegation |
| `src/app/shared/sqlite/index.ts` | Barrel export |

## Test Plan

1. `webPlatform_query_returnsEmptyArray` — on web, query returns `{ values: [] }`
2. `webPlatform_execute_isNoop` — on web, execute resolves without error
3. `service_initialize_setsInitialized` — after init, `initialized()` is true
4. `addUpgradeStatement_delegatesToPlugin` — on native, delegates to CapacitorSQLite

## Actual Results

| Item | Result |
|------|--------|
| Commit | `5ad4aca` feat(sqlite): add SQLite service shell with web no-op |
| Tests | 7 spec cases (expanded: query, execute, close, initialize, addUpgradeStatements, initialized default, isNative) |
| Build | Production build passes cleanly |
| Package | Installed `@capacitor-community/sqlite` for types — dynamic imports keep it zero-cost at runtime on web |
| Files changed | 7 (service, model, mock, spec, index, package.json, package-lock.json) |
| Deviation from plan | Added `close()` method and extra test cases beyond the planned 4. No environment.useMocks.sqlite flag added (web no-op via CapacitorBaseService is sufficient). |
