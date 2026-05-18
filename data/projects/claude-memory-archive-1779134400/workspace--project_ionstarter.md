---
name: Ionstarter — new mobile app base
description: ionstarter boilerplate repo at /projects/ionstarter/ will become the main bubls mobile codebase via incremental feature migration
type: project
originSessionId: e024faf7-9ea0-4c83-9555-b3f47825503d
---
**Repo:** `/projects/ionstarter/` (mounted from `~/Projects/ionstarter/` on host)
**Origin:** https://github.com/ionstarter/angular-sqlite-starter.git
**Stack:** Angular 19 + Ionic 8 + Capacitor 7 + Elf state + TanStack Query + Transloco i18n + RevenueCat + @capacitor-community/sqlite

**Architecture:** Domain-driven — `src/app/domains/{home,tasks,settings,tabs}` each self-contained with routes/pages/services. Abstract service layer routes SQLite (native) vs LocalStorage (web). Core services wrap all Capacitor plugins.

**Plan:** Separate repo for now. Migrate bubls features one at a time into `src/app/domains/`. Same Flask backend serves both. Once feature-complete, lift-and-replace the current bubls repo.

**Migration mapping:**
- Dashboard/picks → `domains/picks/`
- Pick detail → `domains/picks/pages/pick-detail/`
- Photoshoot → `domains/photoshoot/`
- Text generation → `domains/text/`
- Check-in → `domains/checkin/`
- Onboarding foyer → `domains/onboarding/`
- Settings/theme → already exists in `domains/settings/`

**Why:** Current bubls codebase grew organically. ionstarter provides cleaner architecture (domain-driven, proper SQLite abstraction, i18n, edge-to-edge, live update OTA) as a foundation.
**How to apply:** When working on bubls mobile features, consider how they'll map to the ionstarter domain structure. Keep the Flask backend compatible with both codebases during transition.
