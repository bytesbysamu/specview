---
sidebar_position: 2
---

# 🎯 Bubls → Ionstarter Migration – Epic

**Purpose**: Define scope and tasks for incrementally migrating all Bubls product features into the ionstarter domain-driven architecture.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

The current Bubls codebase shipped fast and validated the product — event picks, photoshoot, text generation, and check-in all work and users engage with them. But the architecture is now the bottleneck: adding features takes longer than it should because business logic lives in page components, services are flat and coupled, and there's no data-fetching abstraction to handle caching, loading states, or optimistic updates.

Ionstarter provides all of this out of the box: domain-driven feature isolation, TanStack Query for server-state, Elf for client-state, Transloco for i18n, RevenueCat for purchases, and OTA live updates. Rather than bolting these onto the existing codebase (high risk, weeks of refactoring with no user-visible improvement), we stand up the proven architecture and migrate features into it one at a time. Each domain works independently — we can ship partial migrations to TestFlight and validate before continuing.

The end result: same product, same features, same Flask backend — but a codebase that can sustain the next 6 months of feature development without accumulating more architectural debt. Future features (group check-in, event sharing, AI recommendations v2) slot cleanly into new domains without touching existing code.

---

## Scope

### What This Epic Covers

- Scaffolding ionstarter with bubls' bundle ID, app name, and iOS configuration
- Resolving Capacitor 7/8 and Angular 19/20 version gaps
- Establishing the reference migration pattern (picks domain as first domain)
- Migrating all 5 feature domains: picks, photoshoot, text-gen, check-in, onboarding
- Preserving the Four Worlds visual identity system in ionstarter's theme architecture
- Wiring the dynamic feature registry / tab system into ionstarter's routing
- Maintaining Flask backend compatibility throughout (zero backend changes)
- Setting up CI/CD to deploy ionstarter-bubls to TestFlight via existing pipeline

### What This Epic Does NOT Cover

- ❌ Backend migration or refactoring (Flask stays as-is)
- ❌ New feature development (no new capabilities during migration)
- ❌ Upgrading ionstarter to Angular 20 or Capacitor 8 (migrate into current ionstarter versions)
- ❌ RevenueCat integration (purchases come after migration is complete)
- ❌ German/multi-language i18n content (English-only keys, structure ready)
- ❌ OTA live update configuration (post-migration task)
- ❌ Analytics/tracking migration (tracking service is deferred)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Foundation: scaffold ionstarter with bubls identity + resolve version gaps** | None | — | 2 days | High |
| 2 | **Reference migration: picks domain with TanStack Query pattern** | 1 | — | 2 days | High |
| 3 | **Migrate photoshoot domain** | 2 | 4 | 2 days | High |
| 4 | **Migrate text-gen domain** | 2 | 3 | 1 day | High |
| 5 | **Migrate check-in domain** | 2 | 3, 4 | 1 day | Medium |
| 6 | **Migrate onboarding + Four Worlds theme system** | 1 | 2 | 2 days | High |
| 7 | **CI/CD: wire ionstarter-bubls to TestFlight pipeline** | 1 | 2, 6 | 1 day | Medium |

### Task Details

#### Task 1: Foundation — Scaffold ionstarter with bubls identity + resolve version gaps

Configure ionstarter with bubls' bundle ID (`com.bubls.app`), app display name, iOS entitlements, and splash/icon assets. Audit all Capacitor plugins used in bubls against Cap 7 APIs — document breaking changes and implement compatibility shims where needed. Grep bubls for Angular 20-only APIs (resource(), signal-based forms) and document what needs adaptation. Set up the domain directory structure with placeholder domains for all 5 features. Wire Transloco with English-only key files. Resolve the dark-mode implementation: adopt ionstarter's `ion-palette-dark` class as the base, extend with a `[data-world]` attribute for per-route Four Worlds overrides.

#### Task 2: Reference migration — Picks domain with TanStack Query pattern

Migrate the event picks feature as the canonical reference for all subsequent domain migrations. This establishes the pattern: `picks.page.ts` → `picks-page.service.ts` → `picks.service.ts` → `picks-backend.service.ts`. Wrap the existing Flask `/api/picks` calls in TanStack Query (`injectQuery` / `injectMutation`). Demonstrate loading states, error handling, cache invalidation, and optimistic updates. Component-local state stays as Angular signals. Domain-level state (selected city, filter preferences) goes into an Elf store. Write the page object tests proving the pattern works end-to-end against mocked backend responses. This task's output becomes the template README that tasks 3-5 follow.

#### Task 3: Migrate photoshoot domain

Reshape the photoshoot feature (LoRA model upload, photo generation, gallery) into `domains/photoshoot/`. The photoshoot has the most complex state: upload progress, generation queue, result polling. TanStack Query's `injectMutation` with `onMutate` optimistic updates handles the generation flow. Camera/file access goes through a platform adapter service (Capacitor Camera plugin on native, file input on web). Gallery images use TanStack Query's infinite scroll pattern with cursor-based pagination from the Flask API.

#### Task 4: Migrate text-gen domain

Reshape the text generation feature (prompt input, streaming response, history) into `domains/text-gen/`. Text generation uses SSE streaming from Flask — wrap in a custom TanStack Query that treats the stream as a mutation with progressive `onSuccess` updates. History is a standard paginated query. Prompt templates are component-local signal state. The domain service encapsulates the EventSource connection lifecycle.

#### Task 5: Migrate check-in domain

Reshape the check-in feature (venue search, check-in action, history feed) into `domains/check-in/`. Venue search uses TanStack Query with debounced input (300ms). Check-in action is a mutation that invalidates the history query on success. Location access goes through a platform adapter (Capacitor Geolocation on native, browser API on web). History feed is a standard paginated infinite query.

#### Task 6: Migrate onboarding + Four Worlds theme system

Reshape the onboarding flow (world selection, preference capture, initial picks generation) into `domains/onboarding/`. Critically, implement the Four Worlds CSS architecture: a `[data-world="neon"|"earth"|"minimal"|"cosmic"]` attribute on `ion-app` drives per-world CSS custom properties (backgrounds, gradients, accent colors, typography weights). Each route can declare its world via route data, and the shell applies it. This preserves bubls' distinctive per-page visual identity while working within ionstarter's Ionic theme system.

#### Task 7: CI/CD — Wire ionstarter-bubls to TestFlight pipeline

Adapt the existing GitHub Actions workflow (from constellation/springular patterns) to build ionstarter-bubls. Path-change detection via dorny/paths-filter. `test-frontend` job runs domain tests in parallel. `build-ios` job archives and uploads to TestFlight via Fastlane. Same signing certificates, same provisioning profile, same TestFlight track as current bubls — users see an update, not a new app.

---

## Success Criteria

- ✅ All 5 feature domains functional in ionstarter-bubls on TestFlight with zero Flask backend changes
- ✅ Each domain passes page-object tests with mocked backend (≥80% coverage on domain services)
- ✅ Four Worlds visual identity preserved — each route renders its world-specific theme correctly
- ✅ TanStack Query handles all server-state: loading indicators, error boundaries, cache invalidation all work
- ✅ Feature registry drives tab creation dynamically (same behavior as current bubls)
- ✅ CI/CD deploys to TestFlight on push to main with <10min pipeline time
- ✅ No user-visible regression: existing bubls users update seamlessly via same bundle ID
- ✅ Transloco keys in place for all user-facing strings (English-only, German-ready structure)

---

## Non-Goals

- ❌ Performance optimization (migration preserves current performance, optimization is a follow-up)
- ❌ New feature development during migration
- ❌ Backend API versioning or changes
- ❌ Migrating the tracking/analytics service (deferred until post-migration)
- ❌ RevenueCat / paywall integration (separate capability post-migration)
- ❌ Offline-first with SQLite sync (ionstarter has the abstraction, but bubls doesn't need it yet)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
