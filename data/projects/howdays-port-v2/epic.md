---
sidebar_position: 2
---

# 🎯 Port howDays Boilerplate – Epic

**Purpose**: Define scope and tasks for migrating Bubls to CocoaPods and porting howDays' proven infrastructure modules.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

Three community Capacitor plugins are installed in Bubls but silently broken on iOS. Voice input, photo library save, and in-app payments all return `UNIMPLEMENTED` on device because SPM doesn't resolve them. This isn't a feature gap — it's a platform gap. Users on real iPhones hit dead functionality. Migrating to CocoaPods fixes all three in one move and prevents the same class of problem for every future plugin.

Beyond unblocking plugins, howDays has battle-tested infrastructure that took weeks to build and debug: RevenueCat paywall flow (configure offerings in dashboard, present modal, unlock entitlement, persist state), SQLite with forward migrations (create tables, alter schema, run on app launch), and live-update (push JS bundles OTA, skip App Store review for non-native changes). Porting this infrastructure now means Bubls ships with payments, local storage, and rapid iteration capability from day one — instead of rebuilding each from scratch when the feature that needs it is already overdue.

The value proposition: one migration (SPM → CocoaPods) unblocks the entire community plugin ecosystem, and porting four infrastructure modules gives Bubls the same operational maturity as howDays without repeating the engineering cost.

---

## Scope

### What This Epic Covers

- Full migration from SPM to CocoaPods for iOS dependency management
- Removal of all SPM configuration files and references
- Verification that all installed Capacitor plugins resolve and function on device
- SQLite local storage module with migration layer and initial `app_settings` table
- RevenueCat subscription module with paywall modal (business-agnostic, configurable)
- Live-update module using @capawesome/capacitor-live-update
- CI/CD updates (xcodebuild workspace flag, Fastlane Podfile step)

### What This Epic Does NOT Cover

- ❌ Bubls-specific subscription tiers, pricing, or entitlement names — those are product decisions, not infrastructure
- ❌ Bubls-specific SQLite tables beyond `app_settings` — schema is a feature concern
- ❌ Android build changes — Gradle already resolves Capacitor plugins correctly
- ❌ Backend changes — this is purely client-side infrastructure
- ❌ Live-update server/CDN setup — only the client-side capability is ported; bundle hosting is configured post-launch
- ❌ Migration of existing user data — there is no existing local data to migrate

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **SPM → CocoaPods migration** | None | — | 1 day | Critical |
| 2 | **Capacitor plugin verification** | 1 | — | 0.5 day | Critical |
| 3 | **SQLite local storage module** | 1 | 4, 5 | 1 day | High |
| 4 | **RevenueCat subscription module** | 1 | 3, 5 | 1.5 days | High |
| 5 | **Live-update module** | 1 | 3, 4 | 0.5 day | Medium |
| 6 | **CI/CD pipeline update** | 1 | — | 0.5 day | High |

### Task Details

#### Task 1: SPM → CocoaPods migration

Remove Swift Package Manager from the Bubls iOS project and replace it with CocoaPods. Delete `Package.swift`, `Package.resolved`, and any SPM-related entries in `project.pbxproj`. Install CocoaPods if not present (`gem install cocoapods` or `brew install cocoapods`). Run `cap sync` to generate the Podfile with all installed Capacitor plugins. Run `pod install` to resolve dependencies. Open the `.xcworkspace` (not `.xcodeproj`) and verify the project builds. Update `.gitignore` to include `Pods/` directory (CocoaPods convention: commit Podfile and Podfile.lock, ignore Pods/). Verify the app launches on a simulator.

#### Task 2: Capacitor plugin verification

After CocoaPods migration, verify every installed Capacitor plugin actually resolves and functions on a real iOS device. Test speech-recognition (record and transcribe a phrase), media (save an image to photo library), camera (capture a photo), and revenuecat (SDK initializes without crash). For each plugin, write a minimal smoke-test page or use the existing Bubls UI. Document any plugin that still fails — the migration should have fixed all of them, but verify. This task is the acceptance gate for task 1.

#### Task 3: SQLite local storage module

Port howDays' SQLite module as a shared service in `shared/sqlite/`. This includes: the Capacitor SQLite plugin configuration, a migration runner that executes numbered SQL migration files on app launch, and the initial migration (`001_app_settings.sql`) that creates an `app_settings` table (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT). The service exposes `get(key)`, `set(key, value)`, `delete(key)`, and `runMigrations()`. Wrap the Capacitor SQLite plugin behind an adapter so tests can swap in an in-memory mock. Validate by storing and retrieving a theme preference.

#### Task 4: RevenueCat subscription module

Port howDays' RevenueCat integration as a shared service in `shared/subscriptions/`. This includes: RevenueCat SDK initialization with a configurable API key, a `SubscriptionService` that exposes `getOfferings()`, `purchase(package)`, `restorePurchases()`, and `getActiveEntitlements()`, and a paywall modal component that displays offerings and handles purchase flow. The paywall modal is business-agnostic — it reads offerings from RevenueCat's dashboard configuration, not from hardcoded product IDs. The service persists entitlement state locally (via the SQLite module from task 3) so the app can check subscription status without a network call on every launch. Wrap behind an adapter with mock mode for development/testing.

#### Task 5: Live-update module

Port howDays' live-update configuration using @capawesome/capacitor-live-update. Install the plugin (`npm install @capawesome/capacitor-live-update`), verify it resolves via CocoaPods after `cap sync`. Create a shared service in `shared/live-update/` that wraps the plugin with `checkForUpdate()`, `downloadUpdate()`, and `applyUpdate()` methods. Configure the plugin in `capacitor.config.ts` with placeholder values (bundle URL, app ID) that will be set per-product. The service should check for updates on app launch and apply them silently on next restart. No UI for this task — updates happen transparently.

#### Task 6: CI/CD pipeline update

Update GitHub Actions workflows and Fastlane configuration to use CocoaPods instead of SPM. Change `xcodebuild` commands to use `-workspace App.xcworkspace` instead of `-project App.xcodeproj`. Add a `pod install` step before build in CI. Update Fastlane `Gymfile` or `Fastfile` to reference the workspace. Verify the full CI pipeline (test → build → archive) passes with the new configuration. Update any path-filter rules if iOS-specific files changed location.

---

## Success Criteria

- ✅ `cap sync && cd ios/App && pod install` succeeds with zero errors
- ✅ Speech-recognition plugin transcribes audio on a real iPhone
- ✅ Media plugin saves an image to photo library on a real iPhone
- ✅ RevenueCat SDK initializes and fetches offerings on a real iPhone
- ✅ SQLite migration runner creates `app_settings` table and `get`/`set` round-trips a value
- ✅ Live-update plugin initializes without crash (full OTA flow tested post-launch)
- ✅ CI pipeline builds the iOS app using CocoaPods workspace without manual intervention
- ✅ No SPM artifacts remain in the repository (no `Package.swift`, no `Package.resolved`, no SPM references in `project.pbxproj`)
- ✅ All ported modules live in `shared/` with adapter pattern and mock mode

---

## Non-Goals

- ❌ Designing Bubls subscription tiers or pricing — that's a product decision made after infrastructure lands
- ❌ Building a settings UI — task 3 creates the storage layer, not the settings screen
- ❌ Configuring a live-update CDN or bundle server — client capability only
- ❌ Writing Bubls-specific business logic in any ported module
- ❌ Supporting Android in this epic — Android plugin resolution already works

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

