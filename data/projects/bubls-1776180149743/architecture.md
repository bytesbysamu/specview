---
sidebar_position: 3
---

# 🏗️ Bubls — Architecture

**Purpose**: Technical design for Bubls — weekly AI-curated event discovery.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Bubls is a three-layer system: a Next.js frontend (landing page + dashboard), a Supabase data layer (subscribers + picks), and a Python worker that runs once weekly to ingest events, curate via Claude, and trigger email delivery. The system is designed for batch processing, not real-time interaction. The only user-facing write operation is signup; everything else is a read. The weekly worker is the heart of the system — it pulls raw events from two APIs, sends them through Claude for per-subscriber curation, writes results to Supabase, and dispatches emails via Resend.

The architecture deliberately avoids: API routes beyond signup, server-side rendering, authentication systems, WebSocket connections, background job queues, and caching layers. The dashboard is a static read from Supabase using the subscriber's token. The worker runs as a scheduled script, not a persistent service.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | Two pages, two tables, one worker script. No infrastructure beyond what's needed for the first Thursday email. |
| Push over pull | Users receive picks via email. Dashboard exists for detail, not for browsing. No search, no filtering. |
| Claude IS the algorithm | No embeddings, no collaborative filtering, no behavior tracking. The prompt is the entire recommendation system. |
| APIs only, no scraping | Ticketmaster Discovery + Eventbrite APIs provide structured, reliable event data. No Playwright, no HTML parsing. |
| Magic links over auth | UUID tokens in URLs eliminate passwords, OAuth, session management. Acceptable security for non-sensitive content. |
| Batch over real-time | One weekly run. No streaming, no live updates, no polling. Events are curated Thursday, consumed Friday–Sunday. |

---

## Component Design

### Task 1: Supabase Schema + Project Setup

**Purpose**: Data foundation — two tables, RLS, and client initialization.

**Components**:
- `supabase/migrations/001_initial.sql` — Schema definition
- `lib/supabase.ts` — Supabase client (browser + server)
- `.env.local` — Supabase URL + anon key

**Schema**:

```sql
-- Subscribers: who gets picks
CREATE TABLE subscribers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  city TEXT NOT NULL DEFAULT 'zurich',
  interests TEXT[] NOT NULL CHECK (array_length(interests, 1) <= 3),
  token UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Picks: what they see each week
CREATE TABLE picks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscriber_id UUID NOT NULL REFERENCES subscribers(id),
  week_start DATE NOT NULL,
  events JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(subscriber_id, week_start)
);

-- Engagement events: what they do
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscriber_id UUID NOT NULL REFERENCES subscribers(id),
  event_type TEXT NOT NULL, -- 'email_open', 'dashboard_visit', 'link_click'
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No RLS needed — all reads go through Next.js server-side API routes
-- using the Supabase service role key. No client-side Supabase calls.
-- This avoids RLS complexity since there's no auth system.
```

**Patterns**: All Supabase reads happen server-side in Next.js route handlers or server components using the service role key. The dashboard page `/picks/[token]` is a server component that queries Supabase directly — no client-side SDK, no RLS policies, no auth headers. The token is validated server-side by querying `subscribers WHERE token = $1`. This is simpler and more secure than trying to pass tokens through RLS headers.

### Task 2: Landing Page + Signup Flow

**Purpose**: Convert visitors to subscribers in under 30 seconds.

**Components**:
- `app/page.tsx` — Landing page with signup form
- `app/actions/signup.ts` — Server action: validate, insert subscriber, redirect
- `components/interest-picker.tsx` — Multi-select for interests (max 3)
- `components/city-selector.tsx` — City dropdown (Zürich active, others "coming soon")

**Flow**:
```
User lands on bubls.ch
  → Sees hero: "5 picks. Every Thursday. Your city."
  → Selects city (Zürich)
  → Taps up to 3 interests (toggles)
  → Enters email
  → Submit → Server Action inserts subscriber → Redirect to /picks/[token]
```

**Patterns**: Next.js Server Actions for the write path. No client-side state management. Form validation with Zod. Interests stored as Postgres text array.

### Task 3: Dashboard Page

**Purpose**: Display the 5 curated picks for a subscriber's weekend.

**Components**:
- `app/picks/[token]/page.tsx` — Dashboard page (server component)
- `components/event-card.tsx` — Individual pick display
- `components/interest-editor.tsx` — Inline interest editing
- `components/countdown.tsx` — "Next refresh" indicator

**Data flow**:
```
/picks/[token]
  → Server component reads subscriber by token from Supabase
  → Fetches latest picks for subscriber_id
  → Renders 5 EventCard components
  → Shows interests + next refresh time
```

**Event card schema** (from picks.events JSONB):
```json
{
  "title": "Zürich Jazz Festival Opening Night",
  "summary": "Oscar Peterson tribute with the Zurich Jazz Orchestra — rare outdoor set on the lake stage, free entry before 8pm.",
  "datetime": "2026-04-17T19:00:00+02:00",
  "venue": "Zürichhorn",
  "price": "Free",
  "url": "https://ticketmaster.ch/event/...",
  "source": "ticketmaster"
}
```

**Patterns**: Server components for zero client JS on read path. Dynamic route with token param. Conditional rendering for empty state (new subscriber, no picks yet).

### Task 4: Event Ingestion Worker

**Purpose**: Pull raw events from Ticketmaster + Eventbrite for the upcoming weekend.

**Components**:
- `worker/ingest.py` — Main ingestion script
- `worker/sources/ticketmaster.py` — Ticketmaster Discovery API client
- `worker/sources/eventbrite.py` — Eventbrite API client
- `worker/models.py` — Normalized event dataclass
- `worker/requirements.txt` — Dependencies (httpx, supabase-py, anthropic)

**Ticketmaster query**:
```python
GET https://app.ticketmaster.com/discovery/v2/events.json
  ?apikey={key}
  &city=Zürich
  &countryCode=CH
  &startDateTime={friday_5pm_utc}
  &endDateTime={sunday_midnight_utc}
  &size=100
  &sort=date,asc
```

**Eventbrite query**:
```python
# NOTE: Eventbrite's /v3/events/search/ endpoint was deprecated in late 2024.
# Current alternative: /v3/destination/search/ or scrape public listings.
# Fallback plan: Replace Eventbrite with Guidle API (Swiss event portal,
# already integrated in 2024 Bubls backend — GuidleClient.java exists).
# Guidle endpoint: https://www.guidle.com/m_3GbJsF/guidle/Veranstaltungskalender
# This gives strong Swiss-specific coverage that Eventbrite lacked anyway.
GET https://www.eventbriteapi.com/v3/destination/search/
  ?place_id=ChIJGaK-SZFLqEcR... (Zürich Google Place ID)
  &dates=this_weekend
  &expand=venue
  &token={key}
```

**Normalization**: Both sources mapped to common `Event` dataclass. Deduplication by fuzzy title + venue + date matching (simple string similarity, no ML). Expected pool: 50–200 events per weekend for Zürich. If Eventbrite API proves unreliable, swap in Guidle as the second source — the mapper already existed in the 2024 codebase.

**Patterns**: httpx for async HTTP. Dataclasses for structured events. No ORM, no database for raw events — passed in-memory to curation step.

### Task 5: Claude Curation Pipeline

**Purpose**: Rank and summarize 5 best events per subscriber using Claude.

**Components**:
- `worker/curate.py` — Curation logic
- `worker/prompts.py` — System and user prompts

**Prompt structure**:
```
System: You are a local events curator for {city}. Your job is to pick the 
5 best events for someone based on their interests. Be specific about 
what makes each event worth attending. Never use generic marketing copy.

User: Here are {n} events this weekend in {city}:
{events_json}

This person likes: {interests}

Pick the 5 best. For each, return:
- title: event title
- summary: one specific sentence about why this is worth attending
- datetime: ISO 8601
- venue: venue name
- price: price or "Free"
- url: link to tickets/details
- source: ticketmaster or eventbrite

Return valid JSON array of 5 objects. Nothing else.
```

**Batching**: If subscriber count exceeds 50 with same city, batch by interest overlap to reduce API calls. For v1 with <200 subscribers in one city, the raw event pool is the same — only interests differ per call.

**Cost estimate**: ~4K input tokens (100 events) + ~500 output tokens per subscriber = ~$0.02/subscriber/week. At 200 subscribers: $4/week.

**Patterns**: Anthropic Python SDK. JSON mode for structured output. Retry with exponential backoff (3 attempts). Validation of response schema before writing to Supabase.

### Task 6: Email Delivery System

**Purpose**: Deliver Thursday 6pm email with 5 picks and dashboard link.

**Components**:
- `worker/email.py` — Email composition and sending
- `worker/templates/weekly.tsx` — React Email template (compiled to HTML)

**Email structure**:
```
Subject: Your 5 picks for this weekend 🎯
From: picks@bubls.ch
To: {subscriber_email}

[Bubls logo]

Here's your weekend, curated:

1. {title}
   {summary}
   📅 {date} · 📍 {venue} · {price}
   [View details →]

... (×5)

[See all picks on your dashboard →] (links to /picks/[token])

---
[Unsubscribe] (sets active=false)
```

**Patterns**: Resend SDK with React Email for templates. Batch sending with rate limiting (Resend free tier: 100 emails/day, $20/mo tier: 50K/month). Unsubscribe handled via one-click link that flips `active` flag.

### Task 7: Engagement Tracking

**Purpose**: Measure whether curation quality drives engagement.

**Components**:
- `app/api/click/[pickId]/route.ts` — Click redirect + logging
- `app/api/webhook/resend/route.ts` — Email open/delivery webhooks
- Middleware in `app/picks/[token]/page.tsx` — Dashboard visit logging

**Metrics**:
| Metric | Source | Target |
|--------|--------|--------|
| Email open rate | Resend webhook | >40% |
| Dashboard visit rate | Token page load | >30% |
| Link click-through | Click proxy redirect | >20% |
| 4-week retention | Subscriber still active | >60% |
| Weekly active | Opened email OR visited dashboard | >50% |

**Patterns**: Resend webhooks for email events. Server-side logging on page load for dashboard visits. Click proxy (`/api/click/[id]` → log → redirect to event URL) for outbound tracking.

### Task 8: Thursday Cron Scheduling

**Purpose**: Orchestrate the weekly worker run.

**Components**:
- `.github/workflows/weekly-picks.yml` — GitHub Actions cron
- `worker/main.py` — Orchestrator script

**Workflow**:
```yaml
name: Weekly Picks
on:
  schedule:
    - cron: '0 16 * * 4'  # 4pm UTC = 6pm CET
  workflow_dispatch: {}      # Manual trigger for testing

jobs:
  generate-picks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r worker/requirements.txt
      - run: python worker/main.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          TICKETMASTER_API_KEY: ${{ secrets.TICKETMASTER_API_KEY }}
          EVENTBRITE_TOKEN: ${{ secrets.EVENTBRITE_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
```

**Orchestrator flow**: Fetch active subscribers → Ingest events for Zürich → Curate per subscriber → Write picks → Send emails → Report success/failure count.

**Patterns**: GitHub Actions cron with `workflow_dispatch` for manual runs. Single sequential pipeline — no parallelism needed at <200 subscribers. Error notification via Resend email to admin address.

---

## Execution Flow

```
[Phase 1: Foundation]          (1.5 days)
   Task 1 (Schema) ──→ Task 2 (Landing)
                    ──→ Task 3 (Dashboard)

[Phase 2: Pipeline]            (2 days)
   Task 4 (Ingestion) ──→ Task 5 (Curation)

[Phase 3: Delivery]            (1.5 days)
   Task 5 + Task 3 ──→ Task 6 (Email)
   Task 2 + Task 3 + Task 6 ──→ Task 7 (Tracking)

[Phase 4: Operations]          (1 day)
   Task 5 + Task 6 ──→ Task 8 (Scheduling)
   All ──→ Task 9 (Deploy)
```

**Total estimated effort**: ~6 days (one person)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Next.js 15 on Vercel | Server components for zero-JS dashboard reads. Vercel deploys in seconds. Same stack as Humaniz.me — no learning curve. |
| Database | Supabase (Postgres) | Free tier covers <500 subscribers. Built-in RLS for token-based access. Client SDKs for both JS and Python. |
| Event APIs | Ticketmaster + Eventbrite | Both have Swiss coverage, free query tiers, structured JSON responses. No scraping needed. |
| AI curation | Claude API (Haiku for v1) | Fast, cheap ($0.02/subscriber/week), excellent at ranking + summarization. Upgrade to Sonnet if quality insufficient. |
| Email delivery | Resend | Developer-friendly, React Email support, webhook tracking, free tier of 100 emails/day covers initial launch. |
| Auth approach | Magic link UUID tokens | No passwords, no OAuth, no session management. URL-based access is sufficient for non-sensitive event recommendations. Token in URL is acceptable — no financial or personal data exposed. |
| Worker runtime | Python script on GitHub Actions cron | Python has the best Anthropic SDK. GitHub Actions is free for public repos. No infrastructure to manage. Runs once/week for <10 minutes. |
| Dashboard as server component | Next.js RSC, no client JS | Dashboard is a pure read. Server component fetches data and renders HTML. Zero JavaScript shipped to client for the main view. |
| No app | Web only | Users engage once per week. An app install is too much friction for weekly use. Email is the primary surface; web dashboard is secondary. |
| Single city launch | Zürich only | Depth over breadth. One city with good coverage beats 10 cities with gaps. Zürich has strong Ticketmaster/Eventbrite coverage for validation. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)