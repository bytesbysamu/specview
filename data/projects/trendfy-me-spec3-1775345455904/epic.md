# 🎯 Epic: Trendfy.me MVP

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Trendfy.me addresses the gap between fashion inspiration and actionable outfit decisions. Users scroll through endless content on Pinterest, Instagram, and TikTok but struggle to translate trends into wearable outfits with clothes they already own or can actually purchase. This disconnect creates friction that fashion-forward consumers would pay to eliminate.

The market opportunity sits at the intersection of AI image understanding and fashion e-commerce—a space where existing solutions either require manual wardrobe cataloging (tedious) or push affiliate products without context (annoying). Trendfy.me captures trending styles automatically and matches them to user wardrobes or shoppable items, creating value for both consumers seeking outfit guidance and brands seeking targeted placement.

Monetization follows the proven freemium model: free trend browsing with limited saves, paid tiers for wardrobe integration and unlimited outfit generation, plus affiliate revenue from "shop this look" features.

**Value Proposition**: Turn any trending outfit into a wearable look using your wardrobe or shoppable alternatives.

---

## Scope

### What This Epic Covers

- **Trend ingestion pipeline** – Automated collection of trending fashion content from social platforms
- **Outfit analysis engine** – AI-powered breakdown of outfits into components (tops, bottoms, accessories, colors, styles)
- **Basic wardrobe matching** – Simple photo upload to match trend pieces with owned items
- **Landing page with waitlist** – Capture early interest and validate demand

### What This Epic Does NOT Cover

- ❌ Full wardrobe management system — Future capability, requires significant UX investment
- ❌ E-commerce integrations — Phase 2 after validating core matching value
- ❌ Social features (sharing, following) — Post-MVP community features
- ❌ Mobile apps — Web-first for faster iteration

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Trend scraping infrastructure** | None | — | 2 days | High |
| 2 | **Outfit component analysis** | 1 | 3 | 2 days | High |
| 3 | **Landing page + waitlist** | None | 2 | 1 day | High |
| 4 | **Wardrobe photo matching** | 2 | — | 2 days | High |
| 5 | **MVP integration + polish** | 1,2,3,4 | — | 1 day | High |

### Task 1: Trend Scraping Infrastructure

Build automated pipeline to collect trending fashion content from target platforms (Pinterest, Instagram public feeds). Store images with metadata (source, engagement metrics, timestamps) in a format ready for analysis. Focus on reliability over volume—better to have 50 quality trend images daily than 500 noisy ones.

### Task 2: Outfit Component Analysis

Implement AI-powered analysis that breaks down outfit images into structured components: garment types, colors, patterns, styles, and occasions. Output should be searchable metadata that enables matching. Leverage Claude's vision capabilities for accurate categorization without training custom models.

### Task 3: Landing Page + Waitlist

Ship a simple landing page that communicates the value proposition and captures email signups. Include 3-5 example trend-to-outfit transformations to demonstrate the concept. This validates demand while other tasks complete.

### Task 4: Wardrobe Photo Matching

Allow users to upload photos of their clothing items and receive matches against trending outfits. Start with single-item matching ("this blazer works with these 5 trending looks") before expanding to full outfit assembly. Prioritize speed and relevance over comprehensiveness.

### Task 5: MVP Integration + Polish

Connect all components into a cohesive user flow: browse trends → see outfit breakdowns → upload your pieces → get matches. Handle edge cases, add loading states, and ensure the experience feels complete rather than prototype-y.

---

## Success Criteria

This epic is complete when:

- ✅ Pipeline ingests 50+ trending outfits daily without manual intervention
- ✅ Outfit analysis correctly identifies 80%+ of visible garment components
- ✅ Waitlist captures 100+ signups (validates demand)
- ✅ Users can upload a clothing photo and receive relevant trend matches in <10 seconds
- ✅ End-to-end flow tested with 5 external users who find matches useful

---

## Non-Goals

- ❌ Perfect categorization accuracy — Good enough beats perfect; iterate post-launch
- ❌ Comprehensive platform coverage — Start with 1-2 sources, expand based on quality
- ❌ User accounts for MVP — Waitlist emails suffice; auth comes when persistence matters
- ❌ Revenue features — Validate matching value before adding monetization complexity

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview