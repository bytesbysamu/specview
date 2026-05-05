---
sidebar_position: 0
---

# 📋 Relationship Check-In

> Local-first partner check-in app — ten questions, four qualities, honest measurement after every meetup.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Relationship Check-In is a local-first app where two partners independently rate ten questions on a 1–10 scale after each meetup. Neither sees the other's answers until both have submitted. Scores are tracked over time and mapped to four underlying qualities: Communication Honesty, Mutual Respect, Prioritization, and Long-term Viability.

This is the POC for the bubls → ionstarter migration. Rather than porting the organic check-in code from bubls, it's built fresh on ionstarter to validate the domain-driven architecture. The check-in domain is ideal because it's self-contained (no Flask API, local storage only), exercises real persistence patterns (SQLite + localStorage dual-backend), and has enough complexity — 10 questions, 4 computed qualities, partner pairing, trend tracking, divergence detection — to stress-test the architecture recipe.

If this domain works cleanly reusing ionstarter's existing patterns, the recipe is proven for migrating picks, photoshoot, and text domains next.

## Related Documents

- [Analysis](./analysis.md)
