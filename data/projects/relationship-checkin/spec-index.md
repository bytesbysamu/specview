---
sidebar_position: 0
---

# 📋 Relationship Check-In

> Local-first partner score tracking — ten questions, four qualities, honest measurement stored on device.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Relationship Check-In is a new route (`/checkin`) inside the Bubls app that lets two partners independently rate ten predefined relationship questions on a 1–10 scale after each meetup. The ten questions map to four derived qualities — Communication Honesty, Mutual Respect, Prioritization, and Long-term Viability — each computed as the average of its constituent question scores. Neither partner sees the other's answers until both have submitted for that meetup session.

The interpretation framework is baked into the UI: scores above 7 surface as healthy, below 5 as concerning, diverging scores between partners flag misaligned experiences, and declining trends over time signal erosion. Trend lines render per-quality history across all completed sessions, giving both partners a shared factual record of how the relationship is tracking.

This is a zero-infrastructure feature. No server, no AI, no advice engine. All data lives in the device's SQLite database via the already-shipped Capacitor SQLite service. The Bubls dark theme, base service layer, and routing infrastructure are reused directly. The feature ships as a self-contained bounded context under `features/checkin/` with its own models, service, mock, and tests — no cross-feature imports.

## Related Documents

- [Analysis](./analysis.md)

