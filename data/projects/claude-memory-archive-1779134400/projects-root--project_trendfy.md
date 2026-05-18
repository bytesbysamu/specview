---
name: trendfy project context
description: wardrobai/trendfy.me monorepo — AI fashion photoshoot service, dev environment in Docker executor container
type: project
---

trendfy.me (repo: wardrobai) is an AI fashion photoshoot product. Pay → upload selfies → LoRA training → 5 outfit images.

**Why:** Phase 1 MVP targeting German market. Pivoted from closet/try-on concept to fixed-scenario photoshoot.

**How to apply:** All dev happens inside `specdocv2-executor` Docker container. Dev servers must be running (Angular :4000, Landing :4001, Flask :3003, Jupyter :8888). When container restarts, `dev-start.sh` should auto-start them but may need manual restart.

Key decisions made 2026-04-06:
- Flask stays as backend (considered TS migration for Better Auth but deferred)
- Neon Postgres added for email signups, will expand to orders/auth
- Models endpoint reads from config.py (no Replicate API calls in dev)
- Gallery shows ALL generated images from all orders (81 total)
- Angular caches gallery + models data via GalleryCacheService (shareReplay)
