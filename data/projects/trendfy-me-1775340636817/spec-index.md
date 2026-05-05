# Trendfy.me — Project Documentation

> AI-powered virtual try-on. Upload a selfie, try on any outfit.
> Live at https://trendfy.me
> Built in 4 days. April 1-4, 2026.

---

## What It Is

Trendfy is an AI wardrobe app where you upload a photo of yourself, pick any clothing item, and see yourself wearing it. The AI learns your body and generates photorealistic try-on images.

The product is for people who want to see how clothes look on them before buying, plan outfits without physically trying them on, or experiment with styles they'd never walk into a store for.

## Origin

The idea came from my co-founder/roommate. She wanted a way to visualize outfits without trying them on. I had the technical infrastructure (Spec Doc methodology, Claude Code in Docker containers, Replicate API experience) to build it fast.

From idea to live landing page: 4 days. From brainstorm to deployed product with CI/CD: 96 hours.

---

## Numbers (Day 4)

- 41 git commits
- 53,236 lines of code
- 83 AI-generated images
- 3 trained LoRA models
- 4 models tested (IDM-VTON, Flux 2 Pro, Flux VTON, custom LoRA)
- 39 training photos
- 10 catalog garments
- ~$26 total spend (Replicate $10, Anthropic $10, domain ~$6)
- 0 users (just launched)
- 0 revenue (by design — validating first)

---

## Architecture

```
trendfy.me          → Landing page (static HTML, live)
app.trendfy.me      → Angular 19 frontend (DNS pending)
api.trendfy.me      → Flask API (DNS pending)
docs.trendfy.me     → Docusaurus (DNS pending)
```

All services run in Docker containers on a single VPS, orchestrated by Coolify with Traefik reverse proxy and Let's Encrypt SSL.

## Tech Stack

- Frontend: Angular 19 + Tailwind CSS
- Backend: Flask + Gunicorn
- AI: Replicate API (IDM-VTON, LoRA training, ESRGAN, CodeFormer)
- Vision: Claude API (garment detection)
- Deployment: Docker Compose + Coolify + GitHub Actions CI/CD
- SSL: Let's Encrypt via Traefik

---

## AI Pipeline

The core product is a chain of API calls, not a single model.

### Production Pipeline (IDM-VTON path)
1. User uploads selfie (person photo)
2. User selects garment (from catalog or upload)
3. Remove.bg extracts clean garment (~6s)
4. Claude Vision detects garment type and description (~3.4s)
5. IDM-VTON generates try-on image (~26s)
6. ESRGAN upscales result (~16s)
7. CodeFormer enhances face (~14s)
8. Result displayed to user

Total: ~65 seconds for full pipeline.

### LoRA Pipeline (personalized model path)
1. User uploads 15-28 photos of themselves (one-time)
2. Flux LoRA trains on Replicate (~2 min, ~$2)
3. Future try-ons use text prompt with trigger word
4. No garment photo needed — describe any outfit
5. Model knows user's face and body permanently

### Models Tested

| Model | Quality | Speed | Cost | License | Verdict |
|-------|---------|-------|------|---------|---------|
| IDM-VTON | Best for try-on | 26s | $0.025 | CC BY-NC-SA | Production (need license for commercial) |
| Flux 2 Pro | Good general | 15s | $0.05 | Commercial ok | Good for text-to-outfit |
| Custom LoRA v1 | Decent | 60s | $0.01 | FLUX dev license | Face needs work |
| Custom LoRA v2 | Better | 60s | $0.01 | FLUX dev license | Improved with more training photos |
| Custom LoRA v3a | Best LoRA | 60s | $0.01 | FLUX dev license | Rank 16, all layers |

### Training History

| Model | Photos | Steps | Cost | Notes |
|-------|--------|-------|------|-------|
| v1 | 15 | 1500 | ~$2 | Base experiment |
| v2 | 28 | 2000 | ~$2 | More photos, better face |
| v3a | 28 | 2000 | ~$2 | Rank 16, trained all layers |

---

## Repository Structure

```
wardrobai/
├── ai-models/
│   ├── images/              # Training photos (39 total)
│   │   ├── lora/            # v1 training set
│   │   └── lora2/           # v2/v3 training set
│   ├── outputs/             # 83 generated images
│   │   ├── flux-2-pro/      # 8 outputs
│   │   ├── idm-vton/        # 5 outputs
│   │   ├── quality/         # Comparison and postprocessed
│   │   └── segmentation/    # Background removal results
│   ├── catalog/             # 10 garment images
│   ├── wardrobe-poc.ipynb   # Main pipeline (13 cells)
│   ├── lora-experiment.ipynb
│   ├── quality-experiments.ipynb
│   └── results-comparison.ipynb
├── app/                     # Angular 19 frontend
├── server/                  # Flask API
├── landing/                 # Static landing page (LIVE)
├── docs/                    # Docusaurus documentation
├── nginx/                   # Reverse proxy config
├── docker-compose.yml       # Local development
├── docker-compose.coolify.yml  # Production
└── .github/workflows/ci.yml    # CI/CD
```

---

## Frontend

5 pages built, dark glassmorphism theme:
- Closet — grid of saved garments
- Upload — photo upload with AI detection
- Builder — select items to create outfit
- Try-On — submit outfit for AI generation
- Outfits — saved try-on results

10 mock items pre-loaded for development.

For launch, only Upload + Try-On matter. The rest is iteration.

---

## Landing Page

Live at https://trendfy.me

- Editorial design with LoRA hero carousel
- Before/after try-on showcase
- Comparison table
- Email capture (pending backend)
- Thanks page included
- 1120 lines, 30KB, static HTML
- SSL via Let's Encrypt

---

## Distribution Channels

- Website: https://trendfy.me
- Instagram: @trendfy (active)
- Twitter/X: @trendfy (first tweet posted)
- Co-founder handles all distribution

---

## Business Model

### Pricing (planned)
- Early access: $5 one-time
- Subscription: $10/month for unlimited try-ons
- Future: affiliate revenue from clothing brand links

### Unit Economics
- Cost per try-on: $0.025 (IDM-VTON on Replicate)
- Cost per LoRA training: ~$2 (one-time per user)
- Cost per user/month at 20 try-ons: $0.50
- Subscription price: $10/month
- Gross margin: ~95%

### Revenue Targets
- Week 2: First payment ($5)
- Week 4: 3+ paying users
- Month 2: $1K MRR
- Month 3: $5K MRR

---

## Co-Founder Structure

- Technical co-founder (me): 50% — builds product
- Product co-founder (roommate): 50% — owns distribution, user research, content
- Vesting: 4-year with 1-year cliff
- Kill date: May 1, 2026 — reassess if zero paying users

---

## What's Next (Priority Order)

1. Set DNS records for app, api, docs subdomains
2. Build POST /api/tryon endpoint (one Flask route)
3. Wire frontend try-on page to API
4. Connect Stripe ($5 early access)
5. Connect Supabase (email capture + persistence)
6. Co-founder shares landing page in fashion communities
7. First real users test the try-on flow

---

## Key Decisions Made

- **Replicate over self-hosting** — pay per API call, no GPU infrastructure. Self-host only after $5K MRR.
- **IDM-VTON as production model** — best quality for virtual try-on at $0.025/run.
- **LoRA for personalization** — $2 per user to train a personal model. Retention and quality moat.
- **Landing page before product** — validate demand before building features.
- **Co-founder on distribution** — she sells, I build. Zero overlap.
- **May 1 kill date** — if nobody pays, pivot the tech to a different application.

---

## Built With

This project was built using the Spec Doc methodology — documentation-first development with Claude Code executing specs in sandboxed Docker containers. The entire AI pipeline, frontend, and deployment infrastructure was built by a single developer in 4 days using AI-assisted development.

Spec Doc: the competitive advantage nobody sees.# 📋 Spec Index: trendfy.me

> Single source of truth for this capability's specifications.
> Claude Code reads this to understand available context.

---

## Active Specs

| Document | Purpose | Location |
|----------|---------|----------|
| Analysis | Problems driving this capability | [analysis.md](./analysis.md) |
| Epic | Scope, tasks, success criteria | [epic.md](./epic.md) |
| Architecture | System design & decisions | [architecture.md](./architecture.md) |
| Timeline | Status tracking | [timeline.md](./timeline.md) |

---

## Document Flow

```
Analysis ──→ Epic ──→ Architecture ──→ Implementation
(Problems)   (Scope)   (Design)        (How-to)
```

---

## Quick Reference

| When you need... | Read this |
|------------------|-----------|
| Why we're building this | [Analysis](./analysis.md) |
| What we're building | [Epic](./epic.md) |
| How it's designed | [Architecture](./architecture.md) |
| Task status | [Timeline](./timeline.md) |

---

## For Claude Code

To work on this capability:

```
@trendfy.me/epic.md
@trendfy.me/architecture.md

Implement the next task from the backlog.
Follow patterns in architecture.md.
```

---

**Last Updated**: 2026-04-04
