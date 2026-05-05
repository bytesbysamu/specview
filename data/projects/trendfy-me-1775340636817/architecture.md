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

Spec Doc: the competitive advantage nobody sees.
# 🏗️ Architecture: trendfy.me

**Purpose**: Long-lived system design document for AI-powered virtual try-on platform.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Trendfy is a pipeline orchestrator, not an AI company. The core insight is that virtual try-on quality comes from chaining specialized models—not from building one monolithic model. Each step (background removal, garment detection, try-on generation, upscaling, face enhancement) uses best-in-class external APIs rather than self-hosted inference.

This architecture optimizes for iteration speed and cost predictability over latency. A 65-second pipeline sounds slow, but it's acceptable for the use case (planning outfits, not real-time shopping). The trade-off buys us the ability to swap any model in the chain without touching the rest of the system.

The subdomain structure (trendfy.me, app., api., docs.) reflects a multi-product mindset from day one. The landing page is decoupled from the app, allowing independent A/B testing, messaging pivots, and even complete product rewrites without touching marketing infrastructure.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Orchestration over ownership | Use external APIs (Replicate, Claude, Remove.bg) rather than self-hosting models |
| Pipeline modularity | Each AI step is independently replaceable—swap ESRGAN for Real-ESRGAN without touching try-on logic |
| Fail-fast validation | Landing page shipped before app completion to test messaging and capture emails |
| Cost ceiling awareness | All API costs are per-request with known pricing—no surprise GPU bills |

---

## System Boundaries

### What This System Includes

- Image upload and storage workflow
- Garment catalog management
- AI pipeline orchestration (background removal → detection → try-on → upscaling → face enhancement)
- Result delivery and gallery display
- LoRA training workflow for personalized models

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| E-commerce / checkout | Validating try-on value before adding purchase flow |
| Affiliate link integration | Requires retailer partnerships—premature for MVP |
| Real-time try-on | 65s latency is acceptable for outfit planning; real-time requires different architecture |
| Self-hosted model inference | GPU infrastructure complexity not justified at current scale |
| Social features (sharing, followers) | Feature creep—validate core utility first |

---

## Component Design

### Landing Page (trendfy.me)

**Purpose**: Capture interest and validate messaging before users hit the app.

**Key Parts**:
- Static HTML with Tailwind — No framework overhead, instant load
- Email capture form — Validates demand before investing in app polish
- Hero demo images — Shows capability without requiring signup

**Patterns**: Static-first deployment. No JavaScript required for core landing experience.

### Frontend App (app.trendfy.me)

**Purpose**: Upload flow, garment selection, result gallery.

**Key Parts**:
- `UploadComponent` — Handles selfie and garment image uploads with preview
- `CatalogComponent` — Displays pre-loaded garments for quick try-on
- `ResultGalleryComponent` — Shows generated images with before/after comparison
- `PipelineStatusComponent` — Real-time progress indicator for 65s pipeline

**Patterns**: Reactive state management for pipeline status. Optimistic UI updates where safe (upload confirmation), pessimistic for AI results (wait for actual completion).

### Backend API (api.trendfy.me)

**Purpose**: Orchestrate the AI pipeline and manage state.

**Key Parts**:
- `PipelineOrchestrator` — Coordinates multi-step AI workflow with retry logic
- `ReplicateClient` — Wrapper for all Replicate API calls (IDM-VTON, ESRGAN, CodeFormer, LoRA training)
- `ClaudeClient` — Garment detection and type classification
- `ImageStorage` — Manages uploads and generated results

**Patterns**: Chain of Responsibility for pipeline steps. Each step can fail independently and report status without breaking the chain.

### LoRA Training Workflow

**Purpose**: Create personalized models from user photo sets.

**Key Parts**:
- `TrainingJobManager` — Tracks long-running Replicate training jobs
- `PhotoValidator` — Ensures uploaded photos meet quality requirements (15-28 photos, face visibility, variety)

**Patterns**: Async job tracking with webhook callbacks. Training takes 15-30 minutes—users are notified on completion rather than waiting.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular 19 + Tailwind | Familiar from Spec Doc, strong typing, good for complex state (pipeline progress) |
| Backend | Flask + Gunicorn | Minimal overhead for API orchestration, async-friendly for external calls |
| AI - Try-on | IDM-VTON via Replicate | Best quality/cost ratio after testing 4 models |
| AI - Detection | Claude API | Superior garment classification vs. open-source alternatives |
| AI - Enhancement | ESRGAN + CodeFormer | Composable—upscale and face enhancement as separate concerns |
| Background Removal | Remove.bg | Faster and cleaner than self-hosted alternatives for garments |
| Deployment | Docker Compose + Coolify | Single-VPS simplicity, easy CI/CD, no Kubernetes overhead |
| SSL/Routing | Traefik + Let's Encrypt | Auto-cert renewal, subdomain routing from config |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| External APIs over self-hosted models | Zero GPU management, predictable per-request costs, instant access to SOTA models | 65s latency, vendor dependency, margin compression at scale |
| Subdomain architecture from day one | Clean separation for independent scaling and potential product pivots | DNS propagation delays during setup, slight config overhead |
| IDM-VTON as primary try-on model | Best realism after testing Flux variants and custom LoRA | Slower than alternatives, limited pose flexibility |
| Two pipeline paths (IDM-VTON vs LoRA) | IDM-VTON for instant gratification, LoRA for power users wanting personalized results | User confusion about which to use, maintenance of two paths |
| Landing page before app completion | Validate messaging and capture demand before polishing product | Risk of disappointing early visitors if app isn't ready |
| Single VPS over distributed infrastructure | Simplicity for MVP, all services co-located | Single point of failure, manual scaling required |

---

## Patterns

### Pipeline Orchestration

**When to use**: Any multi-step AI workflow where each step depends on the previous.

**How it works**: Each pipeline step is a function that takes input, calls an external API, and returns output. The orchestrator chains steps, handles retries, and reports progress. Steps are stateless—state lives in the orchestrator.

**Example**: Try-on pipeline chains Remove.bg → Claude Vision → IDM-VTON → ESRGAN → CodeFormer. If ESRGAN fails, retry that step without re-running try-on generation.

### Webhook-Driven Long Jobs

**When to use**: Operations taking >30 seconds (LoRA training, bulk processing).

**How it works**: Submit job, store job ID, return immediately. External service calls webhook on completion. Webhook updates job status and triggers notification.

**Example**: LoRA training takes 15-30 minutes. User submits photos, receives "training started" confirmation, gets email/notification when model is ready.

### Optimistic Upload, Pessimistic Results

**When to use**: Distinguishing between user actions (uploads) and AI outputs (generations).

**How it works**: Show upload success immediately after file transfer completes—don't wait for processing. Show AI results only after pipeline completes—don't show placeholders or previews.

**Example**: User sees "Photo uploaded" instantly, then sees pipeline progress, then sees final result. No "generating preview..." states that might show bad intermediate outputs.

---

## Execution Flow

```
[User Upload Phase]
  Selfie upload ──→ Garment selection
                         │
[Preprocessing Phase]    ▼
  Remove.bg (garment) ──→ Claude Vision (detection)
                              │
[Generation Phase]            ▼
  IDM-VTON (try-on) ─────────→
                              │
[Enhancement Phase]           ▼
  ESRGAN (upscale) ──→ CodeFormer (face)
                              │
[Delivery Phase]              ▼
  Result storage ──→ Gallery display
```

**Parallelization opportunity**: Remove.bg and Claude Vision could run in parallel—both only need the garment image. Current implementation is sequential for simplicity.

**Critical path**: IDM-VTON at ~26s dominates total latency. Enhancement steps (ESRGAN + CodeFormer) add ~30s but significantly improve quality. Trade-off is intentional.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview