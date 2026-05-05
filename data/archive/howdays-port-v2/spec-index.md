---
sidebar_position: 0
---

# 📋 Port howDays Boilerplate

> Migrate Bubls from SPM to CocoaPods and port proven infrastructure — RevenueCat subscriptions, SQLite local storage, Capacitor plugin management, and live-update — as business-agnostic shared modules.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls currently uses Swift Package Manager (SPM) for iOS dependency management. Three community Capacitor plugins — speech-recognition, media, and revenuecat — are installed via npm but never wired into the native iOS build. They silently return `UNIMPLEMENTED` on device. The speech-recognition plugin doesn't even ship a `Package.swift` file, making SPM integration impossible without forking. Camera only works because someone manually added it to `Package.swift`. This blocks voice input, photo library save, and payments on real iPhones.

howDays uses CocoaPods and every plugin works out of the box. When you run `cap sync`, Capacitor auto-generates the Podfile with all installed plugins — no manual native wiring. One migration from SPM to CocoaPods unblocks every community plugin in a single move instead of fighting each one into SPM individually.

Beyond unblocking plugins, howDays has proven infrastructure worth porting: RevenueCat subscription management with a native paywall modal, a SQLite local storage layer with a forward migration system, and @capawesome/capacitor-live-update for OTA JavaScript deploys that skip App Store review. Each piece lands in Bubls as a shared module with zero business logic — reusable across any future Capacitor app in the portfolio.

## Related Documents

- [Analysis](./analysis.md)

