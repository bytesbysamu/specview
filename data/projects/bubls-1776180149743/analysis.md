---
sidebar_position: 1
---

# 🔍 Bubls — Analysis

**Purpose**: Identify the problems driving Bubls and the constraints learned from the 2024 attempt.

**Date**: 2026-04-14

---

## Summary

- **Total Issues**: 16
- **Critical**: 3
- **High**: 7
- **Medium**: 6

---

## Issue Breakdown

### Event Discovery Market Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Users face 400+ undifferentiated results on Eventbrite/Google — decision paralysis kills conversion | CRITICAL | Task 5: Claude curation pipeline |
| 90% of people search for events once a week or less — insufficient cadence for habit-forming apps | HIGH | Core design: weekly push delivery (Thursday 6pm) |
| Events expire in days — content shelf life too short for browse-based discovery | HIGH | Task 5: Weekly batch processing, weekend-scoped picks |
| Geographic fragmentation makes scaling expensive — supply must be rebuilt city by city | MEDIUM | Scope: Zürich-only launch, single-city depth over multi-city breadth |
| Chicken-and-egg: organizers won't list without audience, audience won't come without events | HIGH | Task 4: API-sourced supply (Ticketmaster + Eventbrite) — no organizer dependency |

### Prior Attempt Issues (2024 Angular/Spring Boot Version)

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Scope creep into infrastructure killed velocity — vector embeddings, SSR, Docker, Stripe all built before a user saw an event | CRITICAL | Deliberate exclusions list; no monetization, no accounts, no advanced features in v1 |
| Frontend never shipped a real event UI — home page was a 3,247-line admin template | CRITICAL | Task 2: Single-page dashboard, no admin UI, no navigation |
| Over-engineered ingestion with MapStruct mappers, 30+ field entities, pgvector | HIGH | Task 4: Minimal event schema — title, summary, datetime, venue, price, link |
| Multiple scraper strategies (Playwright + Zod + OpenAI for EventFrog) added complexity without value | MEDIUM | Task 4: APIs only — Ticketmaster Discovery + Eventbrite, no scraping |
| Firebase auth added overhead for a product that doesn't need accounts | MEDIUM | Task 2: Magic link tokens, no auth system |

### Competitive Threats (April 2026)

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Google "Ask Maps" (March 2026) — Gemini-powered conversational event discovery baked into Google Maps, massive distribution | HIGH | Speed: ship before Google iterates. Differentiation: curated push (weekly email) vs. on-demand pull (Ask Maps requires user to open Maps and ask) |
| Bigfoot/Littlefoot (ex-Airbnb team) — AI chatbot for local discovery, 120K events across 160 cities | MEDIUM | Bigfoot is US-focused, no Swiss coverage yet. Bubls owns the Zürich niche first. |
| Apple Invites (Feb 2025) — social coordination, not discovery, but captures the "plan with friends" moment | LOW | Different problem. Apple Invites helps you invite people; Bubls tells you where to go. Complementary, not competitive. |
| Fever ($1.8B) — creates own events, acquired Dice | MEDIUM | Fever creates supply; Bubls aggregates it. Different model. Fever's Candlelight concerts would show up in Bubls picks via Ticketmaster. |

### Delivery and Engagement Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No engagement mechanism existed — users had no reason to return | HIGH | Task 6: Thursday email with 5 curated picks + dashboard link |
| No way to validate whether curation quality was good enough | MEDIUM | Task 7: Tracking — open rates, click-through, retention after 4 weeks |

---

## Key Insights

1. **The 2024 attempt failed from over-engineering, not from a bad idea.** The core insight — people want to be told what's good, not browse — remains valid. The fix is radical scope reduction.

2. **Weekly push cadence is a feature, not a bug.** Every prior attempt tried to make event discovery a daily habit. That fights user behavior. Thursday delivery for weekend events matches how people actually plan.

3. **API-sourced supply removes the chicken-and-egg problem.** Ticketmaster and Eventbrite already have Swiss coverage. No need to recruit organizers or scrape unstructured sites. This unlocks launch without supply-side cold start.

4. **Claude IS the recommendation algorithm.** No embeddings, no collaborative filtering, no behavior tracking needed. The prompt is the algorithm. This is the same Claude-as-infrastructure pattern proven with Humaniz.me.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)