# 🔍 Analysis: bubls3

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-04-14

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 6 |
| MEDIUM | 5 |

---

## The Core Problem

Event discovery has been broken for over a decade, and nobody has fixed it — they've only sidestepped it. Eventbrite shows 400 results. Google sends you to 6 different sites. Instagram stories vanish in 24 hours. The outcome: socially active people in Zürich default to staying home or rotating through the same 3 places, not because nothing is happening, but because finding what's happening requires more effort than the event is worth.

Every successful player in the space confirms the problem is unsolvable through aggregation alone. Fever ($1.8B valuation) gave up on discovery and creates its own events. Luma narrowed to professional events. Partiful reframed the problem as coordination, not discovery. IRL faked its way to 95% bot users and collapsed in fraud charges. The graveyard of event apps that tried to "just aggregate better" is enormous.

Consider: event discovery today is like searching for restaurants before Yelp — technically possible, but so painful that most people just eat at the same place. The difference is that events expire in days, not years, making the content treadmill exponentially harder than restaurant listings.

---

## Symptoms

Users experience:

- **Decision paralysis** from hundreds of undifferentiated event listings across multiple platforms
- **Platform hopping** between Eventbrite, Google, Instagram, Facebook Events, and WhatsApp groups to piece together weekend options
- **Defaulting to inaction** — staying home or repeating the same venues despite wanting novelty
- **Language friction** — events listed in German with no English context for Zürich's large international/expat population
- **Ephemeral information** — event recommendations in Instagram stories and WhatsApp groups disappear before the weekend arrives
- **Social network dependency** — new residents and expats lack the local connections that surface word-of-mouth recommendations
- **Trust erosion** — after IRL's fraud and Eventbrite's declining quality under Bending Spoons, users distrust event platforms generally
- **Zero personalization** — existing platforms show the same results regardless of individual taste, making browsing feel like wasted effort

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Event discovery requires unacceptable user effort | 90% of people search for events once a week or less (Hugh Malkin 2015, still true 2026); Eventbrite shows 400 results per query | Task: curated weekly picks (remove search entirely) |
| Content treadmill — events expire in days | Unlike restaurants or hotels, event supply must be completely rebuilt every week; no long-tail value from past listings | Task: automated weekly ingestion pipeline |
| Geographic cold start — supply must be built city by city | Every event app faces chicken-and-egg: no audience without events, no organizer investment without audience; IRL's collapse proves faking scale doesn't work | Task: single-city focus (Zürich) with structured API sources |
| Google "Ask Maps" threatens to own the category | Gemini-powered conversational event discovery launched March 2026 with Google's distribution advantage; no indie app can compete on search | Task: push-based weekly cadence (compete on format, not search) |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Swiss event market is fragmented across sources | Ticketmaster covers international acts, Guidle covers local Swiss events, Facebook/Instagram/WhatsApp cover grassroots — no single aggregator exists for Switzerland | Task: multi-source ingestion (Ticketmaster + Guidle APIs) |
| Incumbent platforms are deteriorating | Bending Spoons acquired Eventbrite (Dec 2025, $500M) and Meetup; revenue declining 12% YoY; staff cuts signal reduced investment in product quality | Task: launch while incumbents are weakest |
| New residents and expats lack discovery networks | Zürich has a large international population without the local friend groups that surface word-of-mouth recommendations | Task: interest-based curation that doesn't require social graph |
| Language barrier for international users in Zürich | Events listed in German on local platforms; no platform provides bilingual context (German titles with English descriptions) | Task: AI-generated English summaries preserving German event titles |
| Information is ephemeral and unstructured | Best event recommendations live in Instagram stories (24h TTL) and WhatsApp groups (unsearchable, buried in chat) | Task: persistent weekly picks accessible via app, web, and email |
| No competitor has assembled available MCP/API infrastructure into a consumer product | MCP servers exist for Ticketmaster, Eventbrite, Luma, Meetup — the infrastructure layer is forming but nobody has built the consumer layer on top | Task: first-mover on structured API aggregation for Swiss market |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Push notification opt-in rates are declining industry-wide | iOS permission prompts create friction; users increasingly deny notifications; weekly cadence means each missed notification = missed week | Task: email as parallel delivery channel (not dependent on push opt-in) |
| Cold start — no social proof for first users | First 50 TestFlight users see an app with no reviews, no brand, no track record in a category where trust is damaged | Task: founder-led manual distribution to personal network first |
| API dependency on third-party event sources | Ticketmaster and Guidle could change terms, rate limits, or pricing; no contractual guarantee of continued access | Task: abstracted ingestion layer; multiple sources reduce single-point-of-failure risk |
| Single-city launch limits growth velocity and investor narrative | Zürich metro area (~1.5M) caps addressable market; competitor Bigfoot/Littlefoot already covers 160 cities | Task: validate retention before expanding; city expansion is a growth decision, not a product decision |
| Weekly cadence creates low engagement frequency | Only one meaningful touchpoint per week; apps with daily utility retain better; risk of users forgetting the app exists between Thursdays | Task: Thursday push + email as re-engagement pair; measure 4-week retention as PMF signal |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Organizer-side listing and self-serve tools | Post-validation feature; requires audience first (chicken-and-egg) |
| Behavior-based personalization from engagement data | Deferred until sufficient interaction data accumulates; vector infrastructure stores data from day one for later use |
| Android platform support | iOS first; same Capacitor codebase enables Android later with minimal additional effort |
| Unstructured event sources (EventFrog, Facebook Events) | Requires LLM scraping; APIs-only for v1 to ensure reliability |
| Monetization (affiliate links, organizer fees) | Earliest at week 2 (affiliate links); business model validation follows product validation |
| Social features and friend graph | Different product category (coordination vs. discovery); Partiful already owns this |
| Map view and calendar integration | Feature additions for post-validation; v1 validates whether curated picks are wanted at all |
| Multi-city coverage | Only after Zürich retention is proven; geographic expansion is a scaling problem, not a validation problem |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview