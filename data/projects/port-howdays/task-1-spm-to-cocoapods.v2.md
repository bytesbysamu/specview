# Task 1: Migrate iOS from SPM to CocoaPods

## Goal

Replace the Swift Package Manager (`CapApp-SPM/Package.swift`) dependency system with a CocoaPods `Podfile`, matching howDays' proven setup. This unblocks all community Capacitor plugins that lack `Package.swift` files (speech-recognition, media, sqlite, revenuecat).

## Current State

- `ios/App/CapApp-SPM/Package.swift` lists 8 plugins: App, Camera, Haptics, Keyboard, Preferences, Share, SplashScreen, StatusBar.
- Three npm-installed community plugins (speech-recognition, media, sqlite) and RevenueCat are NOT wired into the native build — they return UNIMPLEMENTED on device.
- `@capawesome/capacitor-live-update` is not yet in `package.json`.

## Changes

1. **Create `ios/App/Podfile`** modeled on howDays reference (`/projects/howDays/angular-sqlite-starter/ios/App/Podfile`).
   - Platform: `ios, '14.0'` (matches howDays; current SPM targets 15 but 14 is fine for CocoaPods).
   - Include ALL plugins from `package.json` dependencies:
     - Core: `Capacitor`, `CapacitorCordova`
     - Official: `CapacitorApp`, `CapacitorCamera`, `CapacitorHaptics`, `CapacitorKeyboard`, `CapacitorPreferences`, `CapacitorShare`, `CapacitorSplashScreen`, `CapacitorStatusBar`
     - Community: `CapacitorCommunitySpeechRecognition`, `CapacitorCommunityMedia`, `CapacitorCommunitySqlite`
     - Third-party: `RevenuecatPurchasesCapacitor`
   - `post_install` hook calls `assertDeploymentTarget` (same as howDays).

2. **Rename `ios/App/CapApp-SPM/` to `ios/App/CapApp-SPM.backup/`** — preserves the old config as reference. Delete after pod install confirms everything works.

3. **Note**: `pod install` must run on Mac after pulling this commit. The `Pods/` directory and `App.xcworkspace` are gitignored.

## Verification

- `npx ng build --configuration=production` passes (Podfile is iOS-only, no effect on Angular build).
- After `pod install` on Mac: `ios/App/Pods/` directory appears, `App.xcworkspace` is generated.

## Commit

```
refactor(ios): migrate from SPM to CocoaPods for community plugin support

Podfile includes all 13 plugin pods matching package.json.
CapApp-SPM directory backed up to CapApp-SPM.backup.

NOTE: run `pod install` inside ios/App/ on Mac after pulling.
```
