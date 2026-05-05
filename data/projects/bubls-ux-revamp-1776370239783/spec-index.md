---
sidebar_position: 0
---

# 📋 Bubls UX/UI Revamp — Four Worlds

> Re-architect Bubls so each page is its own maxed-out app, with light as the default mode and dark as a first-class variant.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Bubls today ships a uniform dark theme applied flat across three unrelated AI features (Picks, Photoshoot, Text) and Onboarding. This capability re-architects the design system into four distinct visual worlds: **Picks as Sunday Magazine**, **Photoshoot as Polaroid Darkroom**, **Text as Writer's Desk**, and **Onboarding as Foyer**. The shell tab bar remains the portal — but each surface gets its own scoped visual identity inside.

Two load-bearing direction calls drive every decision: (1) light is the default mode with dark as a first-class variant, system-driven via `prefers-color-scheme` with no user toggle yet; (2) each route owns its visual world with scoped CSS overrides, not a shared design-system library. Mobbin research validates the pattern — Apple's apps share grammar, not appearance. Notes ≠ Photos ≠ Music.

This benefits anyone hitting Bubls for the first time (onboarding shifts from 5-field form to 3-screen 1Q-per-step) and existing users who currently see Picks, Photoshoot, and Text as variations of the same dark surface rather than distinct tools. Retention signal: unprompted return within 7 days across all four worlds.

## Related Documents

- [Analysis](./analysis.md)

