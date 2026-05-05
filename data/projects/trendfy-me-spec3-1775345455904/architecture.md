# 🏗️ Architecture: Trendfy.me

**Purpose**: Long-lived system design document for AI-powered fashion trend discovery platform.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Trendfy.me is a trend discovery platform that aggregates fashion content from multiple social platforms, extracts trend signals using AI, and presents actionable insights to users. The system follows a pipeline architecture: ingest → process → analyze → present.

The key architectural insight is treating trends as **emergent patterns** rather than explicit labels. Instead of relying on hashtags or platform-defined categories, the system analyzes visual and textual content to identify what's actually gaining momentum. This requires a multi-stage AI pipeline where each stage adds context and confidence.

The frontend is intentionally minimal—a consumption-first experience optimized for quick scanning. Heavy lifting happens server-side, with pre-computed trend scores refreshed on a schedule rather than computed on-demand.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Pre-compute over real-time | Trend analysis runs on schedule; users see cached results |
| Degrade gracefully | If one platform's API fails, others continue working |
| AI as filter, human as curator | AI surfaces candidates; editorial layer refines |
| Mobile-first consumption | Design for quick scrolling, not deep editing |

---

## System Boundaries

### What This System Includes

- Multi-platform content ingestion (TikTok, Instagram, Pinterest)
- AI-powered trend extraction and scoring
- User-facing trend feed with filtering
- Basic user accounts for saved trends

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| E-commerce integration | MVP focuses on discovery, not purchase |
| User-generated content upload | Consumption-first; creator tools are phase 2 |
| Real-time notifications | Trends move slowly enough that daily updates suffice |
| Brand dashboards | B2B features require different UX; separate product later |

---

## Component Design

### Content Ingestion Pipeline

**Purpose**: Reliably fetch and normalize content from heterogeneous platform APIs.

**Key Parts**:
- `PlatformAdapter` — Abstract interface each platform implements
- `ContentNormalizer` — Transforms platform-specific formats to unified schema
- `RateLimitManager` — Respects API quotas per platform
- `IngestionScheduler` — Coordinates fetch timing across sources

**Patterns**: Adapter pattern for platform differences; circuit breaker for API failures.

### Trend Analysis Engine

**Purpose**: Transform raw content into scored, categorized trends.

**Key Parts**:
- `VisualAnalyzer` — Extracts fashion elements from images via vision AI
- `TextExtractor` — Parses captions, hashtags, comments for context
- `TrendScorer` — Computes velocity, volume, and confidence metrics
- `TrendClusterer` — Groups similar items into coherent trends

**Patterns**: Pipeline pattern with independent stages; batch processing with checkpoints.

### Presentation Layer

**Purpose**: Deliver trends to users with minimal friction.

**Key Parts**:
- `TrendFeed` — Paginated, filterable trend stream
- `TrendCard` — Visual summary with key metrics
- `CategoryRouter` — Handles navigation between trend types

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Next.js 15 | SSR for SEO; React ecosystem; fast iteration |
| Backend | Node.js + Express | JavaScript throughout; simple deployment |
| Data | PostgreSQL + Redis | Relational for trends; Redis for caching hot data |
| AI | Claude API (vision + text) | Strong multimodal capabilities; consistent with existing stack |
| Queue | BullMQ | Handles ingestion jobs; Redis-backed; simple |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Batch processing over streaming | Trends don't need sub-minute freshness; simpler ops | Slight delay in trend detection |
| Single AI provider (Claude) | Reduces integration complexity; proven quality | Vendor dependency; fallback needed |
| Server-side trend scoring | Keeps scoring logic private; easier to update | Can't personalize without user data |
| Unified content schema | One format regardless of source; simpler downstream | Lossy transformation from platform-specific data |

---

## Patterns

### Platform Adapter Pattern

**When to use**: Adding a new social platform as content source.

**How it works**: Each platform implements `PlatformAdapter` interface with `fetch()`, `normalize()`, and `getRateLimits()` methods. The ingestion scheduler treats all adapters uniformly.

**Example**: TikTokAdapter handles TikTok's API auth and response format, outputting standard `ContentItem` objects.

### Trend Lifecycle Pattern

**When to use**: Managing trend state as it evolves.

**How it works**: Trends move through states: emerging → trending → peaked → declining. Each state change triggers different UI treatments and notification eligibility.

**Example**: A trend crosses the "emerging" threshold when velocity exceeds baseline for 48 hours with growing volume.

---

## Execution Flow

```
[Ingestion Phase]
  TikTok Fetch ──┐
  Instagram Fetch─┼──→ Normalize ──→ Store Raw
  Pinterest Fetch─┘

[Analysis Phase]
  Load Batch ──→ Vision AI ──→ Text Extract ──→ Score ──→ Cluster

[Presentation Phase]
  Cache Update ──→ CDN Invalidate ──→ User Request ──→ Serve
```

Ingestion runs every 4 hours per platform, staggered to spread load. Analysis runs after each ingestion completes. Presentation layer reads from cache, with 15-minute TTL.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview