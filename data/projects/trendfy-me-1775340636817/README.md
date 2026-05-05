# 📖 trendfy.me

> AI-powered virtual try-on. Upload a selfie, try on any outfit.
> Live at https://trendfy.me — Built in 4 days.

---

## What This Is

Trendfy is an AI wardrobe app where you upload a photo of yourself, pick any clothing item, and see yourself wearing it. The AI learns your body and generates photorealistic try-on images.

The product is for people who want to see how clothes look on them before buying, plan outfits without physically trying them on, or experiment with styles they'd never walk into a store for.

This capability is defined by the following documents:

| Document | Purpose |
|----------|---------|
| [Spec Index](./spec-index.md) | Entry point for Claude Code |
| [Analysis](./analysis.md) | Problems we're solving |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | System design |
| [Timeline](./timeline.md) | Status tracking |

---

## Origin

The idea came from my co-founder/roommate. She wanted a way to visualize outfits without trying them on. I had the technical infrastructure (Spec Doc methodology, Claude Code in Docker containers, Replicate API experience) to build it fast.

From idea to live landing page: 4 days. From brainstorm to deployed product with CI/CD: 96 hours.

---

## Numbers (Day 4)

| Metric | Value |
|--------|-------|
| Git commits | 41 |
| Lines of code | 53,236 |
| AI-generated images | 83 |
| Trained LoRA models | 3 |
| Models tested | 4 (IDM-VTON, Flux 2 Pro, Flux VTON, custom LoRA) |
| Training photos | 39 |
| Catalog garments | 10 |
| Total spend | ~$26 (Replicate $10, Anthropic $10, domain ~$6) |
| Users | 0 (just launched) |
| Revenue | $0 (validating first) |

---

## Architecture Overview

```
trendfy.me          → Landing page (static HTML, live)
app.trendfy.me      → Angular 19 frontend (DNS pending)
api.trendfy.me      → Flask API (DNS pending)
docs.trendfy.me     → Docusaurus (DNS pending)
```

All services run in Docker containers on a single VPS, orchestrated by Coolify with Traefik reverse proxy and Let's Encrypt SSL.

### Tech Stack

- **Frontend**: Angular 19 + Tailwind CSS
- **Backend**: Flask + Gunicorn
- **AI**: Replicate API (IDM-VTON, LoRA training, ESRGAN, CodeFormer)
- **Vision**: Claude API (garment detection)
- **Deployment**: Docker Compose + Coolify + GitHub Actions CI/CD
- **SSL**: Let's Encrypt via Traefik

See [Architecture](./architecture.md) for full system design.

---

## AI Pipeline

The core product is a chain of API calls, not a single model.

### Production Pipeline (IDM-VTON)

1. User uploads selfie (person photo)
2. User selects garment (from catalog or upload)
3. Remove.bg extracts clean garment (~6s)
4. Claude Vision detects garment type and description (~3.4s)
5. IDM-VTON generates try-on image (~26s)
6. ESRGAN upscales result (~16s)
7. CodeFormer enhances face (~14s)
8. Result displayed to user

**Total: ~65 seconds for full pipeline.**

### LoRA Pipeline (personalized model)

1. User uploads 15-28 photos of themselves (one-time)
2. Flux LoRA trains on Replicate (~2 min, ~$2)
3. Future try-ons use text prompt with trigger word
4. No garment photo needed — describe any outfit
5. Model knows user's face and body permanently

### Models Tested

| Model | Quality | Speed | Cost | Verdict |
|-------|---------|-------|------|---------|
| IDM-VTON | Best for try-on | 26s | $0.025 | Production |
| Flux 2 Pro | Good general | 15s | $0.05 | Text-to-outfit |
| Custom LoRA v3a | Best LoRA | 60s | $0.01 | Personalization |

---

## Business Model

### Pricing (planned)

- Early access: $5 one-time
- Subscription: $10/month for unlimited try-ons
- Future: affiliate revenue from clothing brand links

### Unit Economics

| Metric | Value |
|--------|-------|
| Cost per try-on | $0.025 |
| Cost per LoRA training | ~$2 (one-time per user) |
| Cost per user/month (20 try-ons) | $0.50 |
| Subscription price | $10/month |
| Gross margin | ~95% |

### Revenue Targets

- Week 2: First payment ($5)
- Week 4: 3+ paying users
- Month 2: $1K MRR
- Month 3: $5K MRR

---

## Co-Founder Structure

| Role | Ownership | Responsibility |
|------|-----------|----------------|
| Technical (me) | 50% | Builds product |
| Product (roommate) | 50% | Distribution, user research, content |

- **Vesting**: 4-year with 1-year cliff
- **Kill date**: May 1, 2026 — reassess if zero paying users

---

## Distribution Channels

- **Website**: https://trendfy.me
- **Instagram**: @trendfy (active)
- **Twitter/X**: @trendfy (first tweet posted)
- Co-founder handles all distribution

---

## Key Decisions

- **Replicate over self-hosting** — pay per API call, no GPU infrastructure. Self-host only after $5K MRR.
- **IDM-VTON as production model** — best quality for virtual try-on at $0.025/run.
- **LoRA for personalization** — $2 per user to train a personal model. Retention and quality moat.
- **Landing page before product** — validate demand before building features.
- **Co-founder on distribution** — she sells, I build. Zero overlap.
- **May 1 kill date** — if nobody pays, pivot the tech to a different application.

---

## Quick Start

1. Read [Analysis](./analysis.md) to understand the problems
2. Read [Epic](./epic.md) to understand scope and tasks
3. Read [Architecture](./architecture.md) before implementing
4. Track progress in [Timeline](./timeline.md)

---

## For Claude Code

```
Read this capability's docs and implement the next task:

@spec-index.md
@epic.md
@architecture.md

Implement Task 1 from the backlog. Follow architecture patterns.
```

---

## Document Guidelines

- **Status** belongs ONLY in [Timeline](./timeline.md)
- **Reference, don't duplicate** — link to other docs
- **Each doc has ONE job** — don't mix concerns

---

## Built With

This project was built using the Spec Doc methodology — documentation-first development with Claude Code executing specs in sandboxed Docker containers. The entire AI pipeline, frontend, and deployment infrastructure was built by a single developer in 4 days using AI-assisted development.

---

**Created**: 2026-04-04