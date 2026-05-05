---
sidebar_position: 0
---

# 📋 Bubls → Ionstarter Migration

> Incrementally migrate Bubls product features into the ionstarter domain-driven architecture, one feature domain at a time, sharing the same Flask backend throughout.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

The Bubls → Ionstarter migration replaces the organically-grown Bubls Angular app with a properly architected domain-driven codebase built on the ionstarter boilerplate. Rather than a risky big-bang rewrite, the migration proceeds one feature domain at a time — event picks, photoshoot, text generation, check-in, onboarding — each reshaped into a self-contained ionstarter domain with proper service layering (page service → domain service → backend service).

The Flask backend remains untouched throughout the migration. Both the old Bubls app and the new ionstarter-based app hit the same API endpoints simultaneously. This eliminates backend migration risk entirely and allows feature-by-feature validation — each domain can be tested independently in ionstarter before the corresponding Bubls code is retired.

The end state is a single canonical mobile codebase with: TanStack Query for data fetching, domain-driven feature isolation, Transloco i18n readiness, RevenueCat purchases, OTA live updates, and the Four Worlds visual identity system preserved via CSS custom properties. Once feature-complete, the ionstarter repo replaces the Bubls repo entirely — same bundle ID, same TestFlight track, same users.

## Related Documents

- [Analysis](./analysis.md)
