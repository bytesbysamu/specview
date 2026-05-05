---
sidebar_position: 0
---

# 📋 howDays Patterns Port

> Surgical extraction of proven Capacitor patterns from howDays into Bubls shared modules — payments, error handling, SQLite, and plugin lifecycle.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls is about to hit strangers for the first time. The distribution sprint means real users on cellular connections, real payment flows, and real error states that need consistent handling. howDays has already solved these problems on the exact same stack — Angular 19 + Ionic 8 + Capacitor 7 — and the solutions are battle-tested.

This capability ports four proven patterns from howDays into Bubls as self-contained shared modules. RevenueCat handles payments with a paywall modal and entitlements-based feature gating. ErrorParserService normalizes unknown error types into consistent user-facing messages. The SQLite service layer provides version-based migrations for offline-first data when needed. The Capacitor service wrapper standardizes plugin lifecycle management — initialize once, guard against web, expose a typed API.

Each port lands as a module in `src/app/shared/` with zero changes to existing feature code. Features wire into these modules in separate follow-up tasks. This keeps the blast radius small: if RevenueCat's paywall modal has a bug, no existing Bubls feature is affected until it's explicitly opted in.

## Related Documents

- [Analysis](./analysis.md)

