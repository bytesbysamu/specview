---
sidebar_position: 0
---

# 📋 Port Trendfy into Bubls Photoshoot

> Migrate 7 trained LoRA models, 32 users, and 76 generated results from Trendfy into Bubls so every Trendfy tester gets instant photoshoot on TestFlight day one.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Trendfy and Bubls share a Neon Postgres instance. Trendfy has 32 users, 17 trained LoRA models (7 with real Replicate model IDs), 8 completed orders, and 76 generated results — all in different tables on the same database. This epic maps Trendfy users to Bubls users, maps trained models to `superapp_lora_models`, migrates historical results into the photoshoot history, and adds device-photo-library save so images survive Replicate URL expiry.

No new model training. No new AI calls. Pure data migration + one Capacitor plugin integration.

## Related Documents

- [Analysis](./analysis.md)
- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
