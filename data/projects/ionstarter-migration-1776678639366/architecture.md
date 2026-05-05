---
sidebar_position: 3
---

# 🏗️ Bubls → Ionstarter Migration – Solution Architecture

**Purpose**: Technical design for reshaping Bubls features into ionstarter's domain-driven architecture while preserving the Flask backend contract.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

The migration introduces a three-tier service layering within each feature domain, replacing bubls' current flat service-in-component pattern. The Flask backend remains unchanged — it continues to serve the same REST endpoints. The frontend architecture shifts from "pages that fetch data" to "domains that manage state, consumed by pages that render it."

Each domain is a self-contained lazy-loaded route module with its own service stack, state management, and tests. Domains communicate only through the shell (route navigation) or through a shared event bus (Angular signals at the shell level). No domain imports from another domain. Shared utilities (HTTP interceptors, auth token management, platform adapters) live in `src/app/shared/`.

TanStack Query owns all server-state (data fetched from Flask). Elf stores own client-state that persists across navigation (selected world, user preferences, feature flags). Angular signals own component-local ephemeral state (form values, UI toggles, animation state).

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = Bounded Context | Each bubls feature becomes one ionstarter domain with zero cross-domain imports |
| Adapter pattern | Every domain service adapts between UI needs and Flask API shape. Mock mode via `MOCK=true` env flag |
| Three-tier service layering | Page Service (UI orchestration) → Domain Service (business logic) → Backend Service (HTTP/TanStack Query) |
| Server-state vs client-state separation | TanStack Query for anything from Flask, Elf for persisted client preferences, signals for ephemeral UI state |
| Anti-corruption layer | Flask API response shapes are mapped to domain models at the backend-service boundary. Domain code never sees raw API DTOs |
| Platform adapter | Capacitor plugins wrapped in adapter services with web fallbacks. Domain code calls the adapter, never the plugin directly |
| CSS custom properties for theming | Four Worlds identity via `[data-world]` attribute driving CSS variables. No JavaScript theme switching in components |

---

## Component Design

### Task 1: Foundation — Identity + Version Resolution

**Purpose**: Make ionstarter build and run as "Bubls" with correct bundle ID, resolve all version incompatibilities before feature migration begins.

**Components**:
- `capacitor.config.ts` — Set `appId: 'com.bubls.app'`, `appName: 'Bubls'`, configure server settings
- `ios/App/App/Info.plist` — Bundle display name, version, required device capabilities
- `src/environments/environment.ts` — Flask API base URL, feature flags, mock mode toggle
- `src/app/shared/adapters/` — Platform adapter interfaces for Camera, Geolocation, Preferences, Filesystem
- `src/app/shared/adapters/capacitor/` — Cap 7 implementations of each adapter
- `src/app/shared/adapters/web/` — Browser-native fallbacks for PWA/dev mode
- `docs/VERSION-GAPS.md` — Audit of Cap 7 vs Cap 8 plugin differences, Ng 19 vs Ng 20 API usage

**Patterns**: Adapter (platform services), Strategy (environment-based provider selection)

### Task 2: Reference Migration — Picks Domain

**Purpose**: Establish the canonical migration pattern that all subsequent domains follow.

**Components**:
- `src/app/domains/picks/picks.routes.ts` — Lazy-loaded route definition
- `src/app/domains/picks/pages/picks.page.ts` — Standalone component, OnPush, injects page service
- `src/app/domains/picks/services/picks-page.service.ts` — UI orchestration (loading states, error handling, pagination triggers)
- `src/app/domains/picks/services/picks.service.ts` — Domain logic (filtering, sorting, business rules)
- `src/app/domains/picks/services/picks-backend.service.ts` — TanStack Query wrappers around Flask `/api/picks` endpoints
- `src/app/domains/picks/models/picks.model.ts` — Domain types (Pick, PickCategory, PickFilter)
- `src/app/domains/picks/models/picks.api.ts` — API response DTOs (mapped to domain models in backend service)
- `src/app/domains/picks/state/picks.store.ts` — Elf store for persisted client state (selected city, active filters)
- `src/app/domains/picks/picks.mock.ts` — Mock data for development and testing
- `src/app/domains/picks/picks.page.spec.ts` — Page object tests
- `src/app/domains/picks/services/picks.service.spec.ts` — Domain service unit tests

**Patterns**: Adapter (backend service), Anti-Corruption Layer (API DTO → domain model mapping), Registry (feature flag check in route guard)

### Task 3: Photoshoot Domain

**Purpose**: Migrate the most state-complex feature — LoRA upload, generation queue, gallery.

**Components**:
- `src/app/domains/photoshoot/pages/photoshoot.page.ts` — Main photoshoot page
- `src/app/domains/photoshoot/pages/gallery.page.ts` — Generated image gallery with infinite scroll
- `src/app/domains/photoshoot/services/photoshoot-backend.service.ts` — TanStack mutations for upload + generation, queries for gallery
- `src/app/domains/photoshoot/services/photoshoot.service.ts` — Generation queue management, progress tracking
- `src/app/domains/photoshoot/components/upload-zone.component.ts` — File/camera capture via platform adapter
- `src/app/domains/photoshoot/components/generation-card.component.ts` — Single generation with progress indicator
- `src/app/domains/photoshoot/models/photoshoot.model.ts` — Generation, LoraModel, GalleryImage types

**Patterns**: Adapter (Camera platform adapter), Observer (generation progress events), Strategy (upload strategy: chunked for large files, direct for small)

### Task 4: Text-Gen Domain

**Purpose**: Migrate streaming text generation with SSE consumption.

**Components**:
- `src/app/domains/text-gen/pages/text-gen.page.ts` — Prompt input + streaming output display
- `src/app/domains/text-gen/services/text-gen-backend.service.ts` — EventSource wrapper as TanStack mutation
- `src/app/domains/text-gen/services/text-gen.service.ts` — Stream lifecycle, token accumulation, history management
- `src/app/domains/text-gen/components/stream-output.component.ts` — Progressive text rendering
- `src/app/domains/text-gen/models/text-gen.model.ts` — Prompt, Generation, StreamChunk types

**Patterns**: Observer (stream chunk events), Adapter (EventSource abstraction for testability)

### Task 5: Check-In Domain

**Purpose**: Migrate venue search + check-in action + history feed.

**Components**:
- `src/app/domains/check-in/pages/check-in.page.ts` — Venue search + check-in CTA
- `src/app/domains/check-in/pages/check-in-history.page.ts` — Paginated history feed
- `src/app/domains/check-in/services/check-in-backend.service.ts` — TanStack queries for venue search (debounced), mutations for check-in
- `src/app/domains/check-in/services/check-in.service.ts` — Geolocation orchestration, venue ranking logic
- `src/app/domains/check-in/models/check-in.model.ts` — Venue, CheckIn, Location types

**Patterns**: Adapter (Geolocation platform adapter), Anti-Corruption Layer (venue API response normalization)

### Task 6: Onboarding + Four Worlds Theme

**Purpose**: Migrate onboarding flow and establish the CSS architecture for per-world visual identity.

**Components**:
- `src/app/domains/onboarding/pages/world-select.page.ts` — World selection carousel
- `src/app/domains/onboarding/pages/preferences.page.ts` — Initial preference capture
- `src/app/domains/onboarding/services/onboarding.service.ts` — Flow orchestration, completion tracking
- `src/theme/worlds/` — Per-world CSS custom property definitions
- `src/theme/worlds/neon.css` — Neon world: electric gradients, high-contrast accents
- `src/theme/worlds/earth.css` — Earth world: warm tones, organic shapes
- `src/theme/worlds/minimal.css` — Minimal world: monochrome, sharp geometry
- `src/theme/worlds/cosmic.css` — Cosmic world: deep space, aurora gradients
- `src/app/shared/services/theme.service.ts` — Applies `[data-world]` attribute based on route data or user preference
- `src/app/shared/guards/world.guard.ts` — Route guard that sets world context from route data

**Patterns**: Strategy (world-specific CSS loaded per route), Observer (theme changes propagated via service signal)

### Task 7: CI/CD Pipeline

**Purpose**: Automate test + build + deploy to TestFlight.

**Components**:
- `.github/workflows/ci.yml` — Path-filtered test + build workflow
- `.github/workflows/deploy-ios.yml` — Fastlane archive + TestFlight upload
- `fastlane/Fastfile` — Lane definitions for build, sign, upload
- `fastlane/Matchfile` — Code signing via match (same certs as current bubls)

**Patterns**: Registry (path-filter decides which jobs run based on changed files)

---

## Execution Flow

```
[Phase 1 — Foundation]
   Task 1 (scaffold + version gaps)
              │
              ├──────────────────────┐
              ▼                      ▼
[Phase 2 — Reference + Theme]
   Task 2 (picks reference)    Task 6 (onboarding + worlds)
   Task 7 (CI/CD)                   │
              │                      │
              ▼                      ▼
[Phase 3 — Feature Migration]
   Task 3 (photoshoot) ─┐
   Task 4 (text-gen) ───┼── parallel
   Task 5 (check-in) ───┘
              │
              ▼
[Phase 4 — Validation]
   Full integration test on TestFlight
   Retire old bubls codebase
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State management split | TanStack Query (server) + Elf (client) + Signals (component) | Three clear tiers prevent confusion about where state lives. TanStack handles caching/refetching automatically. Elf persists preferences. Signals are ephemeral |
| Capacitor version | Stay on Cap 7 (ionstarter's version) | Upgrading to Cap 8 mid-migration adds risk. Migrate first, upgrade Cap separately after |
| Angular version | Stay on Ng 19 (ionstarter's version) | Any Ng 20 features used in bubls get adapted. Upgrade Ng separately post-migration |
| Bundle ID | Inherit bubls' `com.bubls.app` from day one | No dual-app period. Users see a seamless update. No TestFlight confusion |
| Dark mode implementation | `ion-palette-dark` (ionstarter) + `[data-world]` attribute extension | Ionstarter's dark mode is Ionic-native. Four Worlds layer on top via additional CSS custom properties scoped to the data attribute |
| Feature registry | Keep bubls' dynamic tab system, adapt to ionstarter routing | Dynamic tabs proven in production, hardcoded routes are inflexible. Registry pattern aligns with architecture principles |
| i18n | Keep Transloco, English-only keys | Near-zero cost now, large cost to add later. German expansion becomes a translation file, not a code change |
| Tracking service | Defer to post-migration | Not a user-facing feature. Adding it mid-migration adds scope without validating anything |
| SSE streaming (text-gen) | Custom TanStack mutation wrapper around EventSource | TanStack doesn't natively support streaming, but wrapping EventSource in a mutation gives us the same lifecycle hooks (onMutate, onError, onSettled) |
| Mock mode | Environment flag `MOCK=true` replaces backend services with mock implementations | Enables offline development, fast tests, and demo mode without Flask running |

---

## Service Layering (Reference Pattern)

```
┌─────────────────────────────────────────┐
│              picks.page.ts              │  ← Renders UI, injects page service
├─────────────────────────────────────────┤
│         picks-page.service.ts           │  ← UI orchestration: loading, errors, pagination
├─────────────────────────────────────────┤
│           picks.service.ts              │  ← Business logic: filtering, sorting, validation
├─────────────────────────────────────────┤
│       picks-backend.service.ts          │  ← TanStack Query: injectQuery, injectMutation
├─────────────────────────────────────────┤
│           Flask API (/api/picks)         │  ← Unchanged
└─────────────────────────────────────────┘
```

Each layer has one job. Page services never call HTTP. Backend services never contain business logic. Domain services never know about loading indicators.

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
