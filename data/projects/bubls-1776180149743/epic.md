---
sidebar_position: 2
---

# 🎯 Bubls — Epic

**Purpose**: Define scope and tasks for Bubls MVP — weekly AI-curated event discovery for Zürich.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

Event discovery is a market where incumbents are consolidating (Bending Spoons acquired Eventbrite for $500M, revenue declining 12% YoY), the dominant social graph owner (Facebook/Meta) never prioritized it, and the clear winner (Fever at $1.8B) creates its own supply rather than aggregating. Every aggregation attempt has either narrowed to a niche (Luma → tech events), pivoted to social coordination (Partiful), or imploded (IRL — 95% bot users, founder charged with fraud). The whitespace is a consumer product that aggregates, curates with AI, and delivers without requiring the user to do anything.

Bubls captures this whitespace with the simplest possible product: 5 picks, pushed weekly. The economics are favorable — Claude API costs per subscriber per week are under $0.02, event APIs are free to query, and email delivery via Resend costs fractions of a cent. At scale, affiliate links on Ticketmaster and Eventbrite ticket URLs provide revenue without requiring organizer relationships. The path to revenue is: validate engagement → add affiliate links → expand cities → introduce organizer self-serve.

The validation target is clear: 200 subscribers in Zürich who open the Thursday email for 4 consecutive weeks. Open rate above 40% and any measurable click-through to event links signals product-market fit. This is testable within one month of launch with near-zero marginal cost.

---

## Scope

### What This Epic Covers

- Landing page with city + interest selection and email signup
- Personal dashboard showing 5 weekend picks (accessible via magic link token)
- Weekly Python worker that pulls events from Ticketmaster + Eventbrite APIs
- Claude API integration for ranking, filtering, and summarizing events
- Thursday 6pm email delivery with 5 picks and dashboard link
- Subscriber data model (email, city, interests, token)
- Picks data model (subscriber, week, curated events as JSON)
- Basic engagement tracking (email opens, dashboard visits, link clicks)

### What This Epic Does NOT Cover

- ❌ Native mobile app (weekly use doesn't justify an install)
- ❌ User accounts, passwords, or OAuth
- ❌ Search, browse, or filtering on the dashboard
- ❌ Map view or geolocation
- ❌ Calendar integration
- ❌ Social features or friend graph
- ❌ Organizer portal or self-serve listings
- ❌ Monetization (affiliate links, ads, premium tiers)
- ❌ Scraping unstructured event sources (EventFrog, Guidle)
- ❌ Multi-city support beyond Zürich
- ❌ Personalization based on click/engagement behavior
- ❌ WhatsApp or push notification delivery

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **Supabase schema + project setup** | None | 0.5 day | High |
| 2 | **Landing page + signup flow** | 1 | 1 day | High |
| 3 | **Dashboard page** | 1 | 1 day | High |
| 4 | **Event ingestion worker** | 1 | 1 day | High |
| 5 | **Claude curation pipeline** | 4 | 1 day | High |
| 10 | **Initial distribution** | 9 | ongoing | High |
| 6 | **Email delivery system** | 3, 5 | 1 day | High |
| 7 | **Engagement tracking** | 2, 3, 6 | 0.5 day | Medium |
| 8 | **Thursday cron scheduling** | 5, 6 | 0.5 day | Medium |
| 9 | **Production deployment** | All | 0.5 day | High |

### Task Details

#### Task 1: Supabase Schema + Project Setup
Initialize Supabase project with two tables: `subscribers` (id, email, city, interests[], token, created_at, active) and `picks` (id, subscriber_id, week_start, events jsonb, created_at). Set up Next.js project on Vercel with Supabase client. Generate magic link tokens as UUIDs on subscriber creation. Add RLS policies: subscribers can only read their own row via token, picks filtered by subscriber_id.

#### Task 2: Landing Page + Signup Flow
Single-page marketing site with value proposition ("5 picks. Every Thursday. Your city."), city selector (Zürich only, greyed-out options for Basel/Bern/Geneva with "coming soon"), interest picker (up to 3 from: music, food, outdoors, art, nightlife, tech, sports, family), and email input. On submit: insert subscriber row, generate token, redirect to dashboard at `/picks/[token]`. No confirmation email — immediate access. Responsive design, mobile-first.

#### Task 3: Dashboard Page
Single page at `/picks/[token]` that reads subscriber's latest picks from Supabase. Displays 5 event cards, each showing: title, AI-generated one-line summary, date + time, venue name, price (or "Free"), and outbound link to original event/tickets. Below picks: subscriber's interests (editable inline), city, and "Next refresh: Thursday 6pm" indicator. If no picks yet (new subscriber before first Thursday), show a welcome state with countdown to next delivery. No nav, no sidebar, no header beyond a small Bubls logo.

#### Task 4: Event Ingestion Worker
Python script that queries Ticketmaster Discovery API (`/discovery/v2/events.json` with `city=Zürich&startDateTime=...&endDateTime=...`) and Eventbrite API (`/v3/events/search?location.address=Zürich&start_date.range_start=...`) for the upcoming weekend (Friday 5pm through Sunday 11:59pm). Normalize results into a common schema: `{source, source_id, title, description, datetime, venue, price_min, price_max, currency, category, url, image_url}`. Deduplicate by title + venue + date similarity. Store raw event pool in a temporary structure for Claude processing.

#### Task 5: Claude Curation Pipeline
Takes the raw event pool from Task 4 and a subscriber's interests. Sends to Claude API with the prompt: "Here are events this weekend in {city}. This person likes {interests}. Pick the 5 best. For each, write a one-line summary that makes someone want to go. Be specific about what makes it worth attending, not generic marketing copy. Return JSON." Parse Claude's response, validate structure, write to picks table as JSONB. Run once per subscriber per week. Handle Claude API errors with retry logic (max 3 attempts, exponential backoff).

#### Task 6: Email Delivery System
Integrate Resend SDK. For each subscriber with fresh picks, compose and send an HTML email: subject line "Your 5 picks for this weekend 🎯", body with scannable event cards (title, summary, date, venue, price), and a CTA linking to `/picks/[token]`. Use Resend's React email templates for clean rendering across clients. Include unsubscribe link that sets subscriber.active = false. Send at 6pm CET every Thursday.

#### Task 7: Engagement Tracking
Track three metrics: (1) email opens via Resend webhook or tracking pixel, (2) dashboard visits by logging token access with timestamp, (3) outbound link clicks by proxying through a `/click/[pick_id]` redirect that logs and forwards. Store events in a simple `events` table (subscriber_id, event_type, metadata jsonb, created_at). No analytics dashboard for v1 — query Supabase directly.

#### Task 8: Thursday Cron Scheduling
Set up GitHub Actions workflow with `cron: '0 16 * * 4'` (4pm UTC = 6pm CET) that triggers the Python worker. Worker flow: pull all active subscribers → run ingestion for Zürich → run Claude curation per subscriber → write picks → trigger email sends. Add error alerting via simple webhook to personal Slack/email if any step fails. Consider Supabase Edge Function as alternative if GitHub Actions proves unreliable for scheduled work.

#### Task 9: Production Deployment
Deploy Next.js to Vercel (connected to GitHub repo, auto-deploy on push to main). Configure Supabase production project with proper RLS. Set environment variables: Supabase URL/key, Ticketmaster API key, Eventbrite API key, Claude API key, Resend API key. Configure custom domain. SSL via Vercel. Run end-to-end test: create test subscriber → trigger worker manually → verify picks appear on dashboard → verify email received.

#### Task 10: Initial Distribution
Manual hustle to reach 200 subscribers. Post in r/zurich, r/switzerland, local Facebook groups, Zürich expat WhatsApp groups, Luma/Meetup community channels. Share with personal network. This is not a feature — it's founder-led distribution that happens in parallel with week 1-2 of operation. Track which channels convert best for future scaling.

---

## Success Criteria

- ✅ A new user can sign up (city + interests + email) in under 30 seconds
- ✅ Dashboard shows 5 curated event picks with real events from Zürich
- ✅ Email arrives every Thursday at 6pm CET with scannable picks
- ✅ Each pick links to the original event page for tickets/details
- ✅ Magic link token provides access without login or password
- ✅ Email open rate tracked and exceeds 40% after first 4 weeks
- ✅ At least one outbound click per subscriber per week (20%+ CTR)
- ✅ 200 subscribers within first month of launch
- ✅ Subscriber retention: >60% still active after 4 Thursdays

---

## Non-Goals

- ❌ Building a recommendation engine or ML pipeline — Claude prompt is the algorithm
- ❌ Achieving comprehensive event coverage — 5 good picks beats 400 mediocre ones
- ❌ Full multilingual UI — interface is English, but Claude summaries preserve German event titles and write summaries in English (Zürich audience is bilingual)
- ❌ Real-time event updates — weekly batch is the design constraint
- ❌ Competing with Fever on supply — we aggregate, they create
- ❌ Building organizer tools before proving consumer demand

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)