# 🎯 Epic: Trendfy.me

**Purpose**: Capability-definition document for AI-powered virtual try-on MVP.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Virtual try-on solves a real friction point in online shopping: the uncertainty of how clothes will actually look on you. Returns cost retailers $816 billion annually, with "didn't fit/look right" as the top reason. Consumers want confidence before buying; Trendfy gives them a photorealistic preview in under 90 seconds.

The target market is online shoppers who hesitate to buy clothes they can't try on, fashion-curious users who want to experiment with styles outside their comfort zone, and content creators who need outfit visualization for planning. The monetization path is freemium with paid tiers: $5 one-time for early access, $10/month for unlimited try-ons, with future affiliate revenue from clothing brand links.

**Value Proposition**: See yourself in any outfit before you buy—upload a selfie, pick a garment, get a photorealistic try-on in 90 seconds.

**Origin**: The idea came from a co-founder who wanted to visualize outfits without trying them on. Combined with existing technical infrastructure (Spec Doc methodology, Claude Code, Replicate API experience), the product went from idea to live landing page in 4 days.

---

## Scope

### What This Epic Covers

- **Landing page** – Convert visitors, explain value prop, capture early interest (LIVE at trendfy.me)
- **Core try-on flow** – Selfie upload → garment selection → AI generation → result display
- **Catalog garments** – Pre-loaded clothing items for instant try-on (10 items curated)
- **Infrastructure** – Deployed system with CI/CD, SSL, and subdomain architecture
- **AI pipeline** – IDM-VTON production path with Remove.bg, Claude Vision, ESRGAN, CodeFormer

### What This Epic Does NOT Cover

- ❌ User accounts / auth — Validating product-market fit first
- ❌ Payment processing — Free tier only for MVP (Stripe integration is Phase 2)
- ❌ LoRA personalization — Future premium feature ($2/user to train personal model)
- ❌ Garment upload by users — Catalog-only for MVP simplicity

---

## Architecture

```
trendfy.me          → Landing page (static HTML, LIVE)
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

**Total: ~65 seconds for full pipeline.**

### Models Evaluated

| Model | Quality | Speed | Cost | Verdict |
|-------|---------|-------|------|---------|
| IDM-VTON | Best for try-on | 26s | $0.025 | **Production** (need license for commercial) |
| Flux 2 Pro | Good general | 15s | $0.05 | Good for text-to-outfit |
| Custom LoRA v3a | Best LoRA | 60s | $0.01 | Rank 16, trained all layers |

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Landing page** | None | 2 | 1 day | ✅ Done |
| 2 | **AI pipeline integration** | None | 1 | 2 days | ✅ Done |
| 3 | **Try-on UI flow** | 2 | — | 1 day | High |
| 4 | **Catalog garments** | 2, 3 | — | 0.5 days | ✅ Done |
| 5 | **Deploy & CI/CD** | 1, 3 | — | 0.5 days | ✅ Done |
| 6 | **DNS configuration** | 5 | — | 0.5 days | High |
| 7 | **API endpoint** | 2 | 6 | 0.5 days | High |
| 8 | **Payment integration** | 3, 7 | — | 1 day | Medium |

### Task 1: Landing Page ✅

Static HTML page at trendfy.me with editorial design, LoRA hero carousel, before/after try-on showcase, comparison table, and email capture. 1120 lines, 30KB, SSL via Let's Encrypt. Live and deployed.

### Task 2: AI Pipeline Integration ✅

Complete generation chain wired up in Jupyter notebooks: Remove.bg for garment extraction, Claude Vision for garment detection, IDM-VTON for try-on generation, ESRGAN for upscaling, and CodeFormer for face enhancement. 83 AI-generated images produced during development. 4 models tested (IDM-VTON, Flux 2 Pro, Flux VTON, custom LoRA).

### Task 3: Try-on UI Flow

Build the Angular frontend where users upload a selfie, select a garment from the catalog, see a loading state during generation (~65s), and view their result. 5 pages built with dark glassmorphism theme: Closet, Upload, Builder, Try-On, Outfits. For launch, only Upload + Try-On matter.

### Task 4: Catalog Garments ✅

10 garments curated across categories (tops, dresses, jackets). Pre-processed garment masks so try-on requests skip the extraction step.

### Task 5: Deploy & CI/CD ✅

Docker Compose deployment to Coolify with Traefik reverse proxy. GitHub Actions pipeline for automated deploys on push. SSL via Let's Encrypt. 41 git commits, 53,236 lines of code.

### Task 6: DNS Configuration

Set DNS records for app.trendfy.me, api.trendfy.me, and docs.trendfy.me subdomains to enable full application access.

### Task 7: API Endpoint

Build POST /api/tryon endpoint (single Flask route) that accepts selfie and garment selection, runs the AI pipeline, and returns the result image.

### Task 8: Payment Integration

Connect Stripe for $5 early access payments. Connect Supabase for email capture and persistence.

---

## Success Criteria

This epic is complete when:

- ✅ Landing page live at trendfy.me with clear value prop
- ✅ User can upload selfie and see try-on result in <90 seconds
- ✅ At least 10 catalog garments available
- ⬜ Full pipeline works end-to-end via web UI (upload → result display)
- ✅ CI/CD deploys working code on git push
- ⬜ First real users test the try-on flow

---

## Unit Economics

| Metric | Value |
|--------|-------|
| Cost per try-on | $0.025 (IDM-VTON on Replicate) |
| Cost per LoRA training | ~$2 (one-time per user) |
| Cost per user/month at 20 try-ons | $0.50 |
| Subscription price | $10/month |
| Gross margin | ~95% |
| Total spend to date | ~$26 (Replicate $10, Anthropic $10, domain ~$6) |

### Revenue Targets

- Week 2: First payment ($5)
- Week 4: 3+ paying users
- Month 2: $1K MRR
- Month 3: $5K MRR

---

## Non-Goals

- ❌ Perfect image quality — Good enough to validate; iterate based on feedback
- ❌ Mobile optimization — Desktop-first for MVP, mobile polish later
- ❌ Analytics/tracking — Ship first, measure second
- ❌ Multiple body types in catalog — Start with co-founder's photos as test subject
- ❌ Self-hosted GPU infrastructure — Pay per API call until $5K MRR

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Replicate over self-hosting | Pay per API call, no GPU infrastructure. Self-host only after $5K MRR. |
| IDM-VTON as production model | Best quality for virtual try-on at $0.025/run. |
| LoRA for personalization | $2 per user to train a personal model. Retention and quality moat. |
| Landing page before product | Validate demand before building features. |
| Co-founder on distribution | She sells, I build. Zero overlap. 50/50 split with 4-year vesting. |
| May 1 kill date | If nobody pays, pivot the tech to a different application. |

---

## Distribution

- **Website**: https://trendfy.me (LIVE)
- **Instagram**: @trendfy (active)
- **Twitter/X**: @trendfy (first tweet posted)
- **Strategy**: Co-founder handles all distribution and shares in fashion communities

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design and tech decisions
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview