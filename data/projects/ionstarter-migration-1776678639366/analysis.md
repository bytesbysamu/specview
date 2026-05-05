---
sidebar_position: 1
---

# 🔍 Bubls → Ionstarter Migration – Analysis

**Purpose**: Identify structural problems in the current Bubls codebase that drive the migration, and surface open questions that must be resolved before execution begins.

**Date**: 2026-04-20

---

## Summary

- **Total Issues**: 12
- **Critical**: 3
- **High**: 5
- **Medium**: 4

---

## Issue Breakdown

### Architectural Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Services live in flat directories with no domain boundaries — cross-feature coupling is implicit and untraceable | CRITICAL | Task 1, Task 3 |
| Pages own business logic directly — no service layering means logic can't be tested or reused without rendering a component | CRITICAL | Task 3, Task 4, Task 5 |
| No data-fetching abstraction — raw HTTP calls in components with no caching, deduplication, or loading-state management | CRITICAL | Task 2, Task 3 |
| Angular signals used ad-hoc with no consistent reactivity pattern — some state in services, some in components, some in both | HIGH | Task 2 |
| Capacitor plugin usage scattered across components instead of centralized behind platform-aware adapters | HIGH | Task 1 |

### Version Gap Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Capacitor 7 (ionstarter) vs Capacitor 8 (bubls) — plugin API differences in @capacitor-community/sqlite, Camera, Preferences | HIGH | Task 1 |
| Angular 19 (ionstarter) vs Angular 20 (bubls) — signal-based forms and resource API usage in bubls may need adaptation | HIGH | Task 1 |
| TanStack Query not present in bubls — all data fetching patterns must be learned and applied during migration | MEDIUM | Task 2 |

### Design System Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Dark mode implementation mismatch — ionstarter uses `ion-palette-dark` CSS class, bubls uses `[data-theme="dark"]` data attribute with per-world CSS overrides | HIGH | Task 1, Task 6 |
| Four Worlds per-route background overrides must survive migration without breaking the ionstarter theme system | MEDIUM | Task 6 |
| Feature registry (bubls dynamic tabs) vs hardcoded tab routes (ionstarter) — architectural mismatch in navigation | MEDIUM | Task 1 |

### Operational Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Two apps on TestFlight during migration creates user confusion and split analytics | MEDIUM | Task 7 |

---

## Open Questions (Must Resolve Pre-Flight)

1. **Cap 7 → Cap 8 delta**: Which specific plugin APIs changed between Capacitor 7 and 8? Does @capacitor-community/sqlite have breaking changes? Decision: audit plugin usage in bubls, check each against Cap 7 API surface.

2. **Ng 20 features in use**: Does bubls use `resource()`, signal-based forms, or other Ng 20-only APIs? Decision: grep for usage, document what needs downgrade or polyfill.

3. **Elf vs Signals boundary**: Adopt Elf for domain-level state (settings, user profile, feature flags) and keep Angular signals for component-local state. TanStack Query handles all server-state. This gives three clear tiers: component signals → Elf stores → TanStack queries.

4. **i18n strategy**: Keep Transloco wired with English-only keys from day one. The cost is negligible (string extraction is mechanical) and adding German later becomes trivial. Stripping it out and re-adding is more work.

5. **Bundle ID inheritance**: Ionstarter inherits bubls' bundle ID (`com.bubls.app`) from task 1. No dual-app period on TestFlight. The migration is invisible to end users.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
