---
sidebar_position: 1
---

# 🔍 Port howDays Boilerplate – Analysis

**Purpose**: Identify problems driving this capability.

**Date**: 2026-04-18

---

## Summary

- **Total Issues**: 7
- **Critical**: 3
- **High**: 2
- **Medium**: 2

---

## Issue Breakdown

### Native Plugin Resolution Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| speech-recognition plugin has no Package.swift — cannot be wired into SPM at all, voice input completely blocked on iOS | CRITICAL | Task 1 |
| media plugin installed via npm but not in Package.swift — photo library save silently fails on device | CRITICAL | Task 1, Task 2 |
| revenuecat plugin installed via npm but not in Package.swift — payments impossible on device | CRITICAL | Task 1, Task 4 |
| Each new community plugin requires manual SPM wiring (find repo, add to Package.swift, resolve version conflicts) — CocoaPods gets this for free via `cap sync` | HIGH | Task 1 |
| Maintaining two dependency systems (SPM + CocoaPods) adds build complexity and CI fragility — recommend full SPM removal | MEDIUM | Task 1 |

### Missing Infrastructure Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No local storage layer — app cannot persist preferences, onboarding state, or offline data without a network round-trip to Neon | HIGH | Task 3 |
| No OTA update path — every JavaScript fix requires a full App Store review cycle (1–3 days minimum) | MEDIUM | Task 5 |

---

## Hard Constraints

- Bubls is Angular 19 + Ionic 8 + Capacitor 7 — same stack as howDays, so the port is a copy-adapt, not a rewrite.
- howDays is the reference implementation. Every ported module must match howDays' working patterns, not invent new ones.
- CocoaPods is the only viable path for community Capacitor plugins. SPM support is optional and inconsistent across the plugin ecosystem.

## Open Questions

- **Xcode workspace vs project**: After CocoaPods install, Xcode uses `.xcworkspace` instead of `.xcodeproj`. CI workflows (xcodebuild commands, Fastlane lanes) must switch to the workspace. Verify howDays CI config for the exact flags.
- **Minimum iOS version alignment**: howDays targets iOS 16.0. Confirm Bubls matches, or reconcile before migrating.
- **RevenueCat app ID**: Bubls needs its own RevenueCat project and API keys. These must be provisioned in the RevenueCat dashboard before task 4.

## Dependencies

- Task 1 (CocoaPods migration) unblocks everything else — no other task can proceed until `pod install` succeeds and the app builds.
- Task 4 (RevenueCat) requires a RevenueCat project with at least one entitlement and one offering configured in their dashboard.

## Explicitly Out of Scope

- Business logic for Bubls-specific features (subscription tiers, pricing, content).
- Neon Postgres schema changes — this capability is purely client-side infrastructure.
- Android — Bubls is iOS-first; Android uses Gradle and doesn't have the SPM problem.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

