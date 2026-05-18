---
name: trendfy-project-overview
description: Full project state for trendfy.me — AI fashion photoshoot product, stack, deployment, and current status as of 2026-04-08
type: project
---

## Product

**trendfy.me** — AI outfit photoshoot. User uploads 15-25 selfies → LoRA model trained on Replicate → 5 outfit scenarios generated (Office, Date Night, Summer, Weekend, Formal) → delivered in app.

**URLs:**
- Landing: https://trendfy.me
- App: https://app.trendfy.me
- API: https://api.trendfy.me (via app nginx proxy, also direct via Traefik)
- Docs: Docusaurus on sslip.io subdomain

## Stack

- **Frontend:** Angular 21, Tailwind 4, single-page home with models+results
- **Backend:** Flask, Gunicorn, Postgres (Neon), file-based order storage
- **AI:** Replicate (LoRA training + Flux inference), Claude Vision (profile extraction)
- **Auth:** JWT + refresh tokens, bcrypt passwords
- **Payments:** Stripe checkout (waitlist → early access flow)
- **Deploy:** Coolify on VPS (72.62.150.237), Docker Compose, Traefik

## Architecture (Coolify)

Each service gets its own Traefik subdomain. The app's nginx proxies `/api/` and `/static/` to the server container internally via Docker network.

Images stored on named Docker volume `order_data` mounted at `/home/appuser/app/data/orders/`.

## Key env vars needed on remote

- `DATABASE_URL` — Neon Postgres
- `REPLICATE_API_TOKEN` — training + generation
- `ANTHROPIC_API_KEY` — Claude Vision profile extraction
- `AUTH_JWT_SECRET` — must not be dev default
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PHOTOSHOOT`

## Current status (2026-04-08)

- Login/auth works on remote
- Image generation works (Replicate) + saves to volume + DB
- Image serving works through app nginx `/static/` proxy
- Landing page intermittently 504 on Coolify
- Model training upload flow needs testing on remote
- Refresh token crash fixed (PR #13)
- Images slow (served through Flask, no CDN) — Firebase Storage planned

## Repo: bytesbysamu/trendfy

**Why:** Context for future conversations about this project.
**How to apply:** Reference for stack decisions, deployment debugging, env var requirements.
