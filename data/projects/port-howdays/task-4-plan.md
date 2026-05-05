# Task 4: Server Entitlements Sync Endpoint — Plan

## Goal

Add `POST /api/user/entitlements` to existing `server/modules/user/routes.py`. Accepts `{ entitlements: string[] }` from the app on launch, updates the user's `enabled_features` JSONB to reflect RevenueCat entitlements. Write-only sync for analytics + backend feature gating.

## Design Decisions

- **Add to existing `user` module** (task description says `server/modules/user/routes.py`) rather than creating a new `entitlements` module. The epic's architecture.md suggests a separate module, but the task instruction is explicit: add to user routes.
- **In-memory rate limiter** — 1 sync per user per 5 minutes. Same pattern as `tracking/service.py`'s `_rate_buckets`.
- **Entitlement mapping**: if `"pro"` in entitlements list, set Pro features true in `enabled_features`. Otherwise set to free tier defaults.
- **SQLAlchemy model update**: Add `last_entitlement_sync: DateTime` column to `User` model + Alembic migration.
- **No OpenAPI spec** — task doesn't mention it. Keep lightweight.

## Files

| File | Action |
|------|--------|
| `server/modules/user/routes.py` | Add `POST /api/user/entitlements` endpoint |
| `server/modules/user/dto.py` | Add `EntitlementsSyncRequest` Pydantic model |
| `server/modules/user/service.py` | Add `sync_entitlements()` with rate limit logic |
| `server/modules/user/repository.py` | Add `upsert_entitlements()` |
| `server/modules/photoshoot/models.py` | Add `last_entitlement_sync` column to `User` |
| `server/migrations/versions/20260422_add_last_entitlement_sync.py` | Alembic migration |
| `server/openapi/user.yaml` | Add entitlements sync endpoint |
| `server/tests/test_entitlements.py` | 4 pytest cases |

## Test Plan

1. `validSync_updatesEnabledFeatures` — POST with `["pro"]` sets Pro features true
2. `rateLimitWithin5Min_returns429` — second call within 5 minutes returns 429
3. `emptyEntitlements_setsFreeDefaults` — POST with `[]` resets to free tier
4. `malformedPayload_returns422` — missing `entitlements` key returns 422

## Actual Results

| Item | Result |
|------|--------|
| Commit | `6e60058` feat(user): add POST /api/user/entitlements for RevenueCat sync |
| Tests | 4/4 passed |
| Files changed | 8 (routes, dto, service, repository, models, migration, openapi, tests) |
| Deviation from plan | Added OpenAPI spec (was listed in plan files table but initially noted as skipped) |
