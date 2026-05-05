# Task 5: Wire live-update (Capawesome)

## Goal

Add the `@capawesome/capacitor-live-update` plugin and create a dormant `LiveUpdateService` shell — same pattern as the SQLite service (ready, no active use).

## Current State

- `@capawesome/capacitor-live-update` is NOT in `package.json`.
- No Podfile entry for it yet (Task 1's Podfile does not include it since the npm package isn't installed).
- howDays has it: `CapawesomeCapacitorLiveUpdate` pod pointing to `../../node_modules/@capawesome/capacitor-live-update`.

## Changes

1. **Note for Mac**: Run `npm install @capawesome/capacitor-live-update` before pod install.

2. **Add pod to `ios/App/Podfile`**: `CapawesomeCapacitorLiveUpdate` pointing to `../../node_modules/@capawesome/capacitor-live-update`.

3. **Create `src/app/shared/live-update/live-update.service.ts`**:
   - Extends `CapacitorBaseService<void>`.
   - Methods: `ready()` (checks if a bundle is available), `sync()` (downloads + applies latest bundle), `reload()` (reloads the webview with new bundle), `reset()` (reverts to built-in bundle).
   - All methods are no-ops on web (via `isNative()` guard from base class).
   - Dynamic import of `@capawesome/capacitor-live-update` to avoid bundling on web.

4. **Create `src/app/shared/live-update/live-update.service.spec.ts`**:
   - Basic test: `webPlatform_syncIsNoop`.

5. **Create `src/app/shared/live-update/index.ts`** — barrel export.

6. **Dormancy contract**: No consumer calls this service. Ready for when OTA JavaScript updates are configured post-launch.

## Verification

- `npx ng build --configuration=production` passes.
- Unit tests pass.

## Commit

```
feat(infra): add live-update service shell (Capawesome)
```
