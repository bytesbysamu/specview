---
sidebar_position: 1
---

# 🔍 Bubls UX/UI Revamp — Analysis

**Purpose**: Identify problems driving this capability.

**Date**: 2026-04-16

---

## Summary

- **Total Issues**: 7
- **Critical**: 2
- **High**: 3
- **Medium**: 2

---

## Issue Breakdown

### Identity & Positioning Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Three unrelated AI features share one flat dark theme — no visual differentiation between Picks, Photoshoot, Text | CRITICAL | Tasks 3, 4, 5 |
| Dark-only stance cuts out users who default to light system preference and never discover the product matches their environment | CRITICAL | Task 1 |
| Shared chrome ("bubls." brand pill, uniform accent) dilutes each feature's core action — no surface feels maxed-out for its job | HIGH | Tasks 3, 4, 5 |

### Onboarding Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| 5-field form (Name, Role, Stack, Style, Goals) front-loads friction before first value — Lovi/Apple Fitness pattern is 1 question per screen | HIGH | Task 2 |
| Onboarding shares the same flat dark surface as the rest of the app — no "welcome" ceremony | MEDIUM | Task 2 |

### Plumbing Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| `tokens.scss` is dark-only; no mechanism to swap mode, no per-world background slot | HIGH | Task 1 |
| Generation ceremony (photoshoot) doesn't hide shell chrome — immersive moments compete with tab bar and status bar | MEDIUM | Task 4 |

---

## Hard Constraints Check

- ✅ Neon Postgres only (no user profile changes in this epic)
- ✅ Angular 19 + Ionic 8 + Capacitor 7 stack preserved
- ✅ Signals for state, OnPush change detection, standalone components
- ✅ `data-test` selectors on every interactive element
- ✅ WCAG-AA contrast in both modes
- ✅ `prefers-reduced-motion` honored by every reveal animation

## Open Questions Resolved in Brain Dump

- **Light vs dark default** → Light default, dark first-class variant, system-driven, no toggle
- **Scoped overrides vs design-system library** → Scoped per-route `:host`, no library
- **Onboarding form** → Drop to 3 screens (city → interests → email), defer other fields to in-context AI prompts
- **Shell changes** → Tab bar pill grammar stays shared; `immersive` signal added for photoshoot generation

## Explicitly Out of Scope

- ❌ New feature surfaces (this is a visual + IA pass only)
- ❌ User-facing dark/light toggle
- ❌ Design-system component library
- ❌ Light-mode photocopy of dark values — each mode is designed natively

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

