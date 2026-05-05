# Task 3: Create SQLite app_settings table

## Goal

Create an `app_settings` key-value table via the existing SQLite service layer, plus an `AppSettingsService` that wraps get/set operations. Validates the migration layer end-to-end with a real table.

## Current State

- `src/app/shared/sqlite/sqlite.service.ts` exists — dormant shell with `addUpgradeStatements`, `query`, `execute`, `close`.
- `src/app/shared/sqlite/sqlite.model.ts` defines `Migration`, `QueryOptions`, `QueryResult`, `RunOptions`.
- No tables, no migrations, no consumers.
- Theme preference currently lives in `localStorage` (`src/app/services/theme.service.ts`, key `bubls.theme`).
- Device token lives in `localStorage` (`src/app/services/auth-token.service.ts`, key `bubls.devToken`).

## Changes

1. **Create `src/app/shared/sqlite/app-settings.service.ts`**:
   - Injects `SqliteService`.
   - Database name: `bubls` (constant).
   - Migration version 1: `CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)`.
   - `init()` method: registers upgrade statements, opens the DB.
   - `get(key: string): Promise<string | null>` — SELECT value WHERE key = ?.
   - `set(key: string, value: string): Promise<void>` — INSERT OR REPLACE with ISO timestamp.
   - `remove(key: string): Promise<void>` — DELETE WHERE key = ?.
   - `getAll(): Promise<Record<string, string>>` — SELECT * for debug/dump.
   - On web: all operations are no-ops (SqliteService returns empty arrays, execute is no-op). The service stays functional but inert.

2. **Create `src/app/shared/sqlite/app-settings.service.spec.ts`**:
   - Unit test with mock SqliteService.
   - Tests: `get_existingKey_returnsValue`, `get_missingKey_returnsNull`, `set_insertsRow`, `remove_deletesRow`.

3. **Export from `src/app/shared/sqlite/index.ts`**.

4. **Do NOT wire into theme.service.ts or auth-token.service.ts yet** — that migration is a separate concern. AppSettingsService is ready for consumers but has zero active callers (same dormancy pattern as SqliteService before this task).

## Verification

- `npx ng build --configuration=production` passes.
- Unit tests pass.
- On device after pod install: `AppSettingsService.init()` creates the `app_settings` table.

## Commit

```
feat(sqlite): add app_settings table with key-value store
```
