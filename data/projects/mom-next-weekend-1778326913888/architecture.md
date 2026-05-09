# 🏗️ Solution Architecture: mom next weekend

## Architecture Overview

This is not a software architecture. The Epic explicitly flags that no implementation guides, code, or system components should follow from this folder. The "system" here is a **planning artefact** — a one-page weekend itinerary for Zürich (2026-05-16 / 2026-05-17) with a weather-contingent A/B path and one locked dinner reservation.

The mental model is a **decision tree, not a service graph**. The single high-leverage decision (outdoor vs. indoor) is deferred until Friday evening when the forecast is reliable. Everything else — dinner, pacing, walking distance, dietary fit — is locked early because those constraints don't change with weather. The "components" below are itinerary modules, not software modules, and they are described only so the folder is internally consistent with the spec-doc pipeline that produced it.

If this is later reframed as a Bubls feature or a trip-planner tool, this document should be discarded and a fresh architecture written against a real product epic.

## Design Principles

| Principle | Application |
|-----------|-------------|
| Defer the reversible decision | Outdoor-vs-indoor path is a Friday-evening switch, not a Monday commitment — forecasts past 5 days are noise |
| Lock the irreversible early | Saturday dinner reservation is the only hard booking; everything else stays flexible |
| Pace to the weakest constraint | Mom's mobility level caps total walking distance per day; activities are sized to fit, not the other way round |
| One page, two columns | Itinerary fits on a single sheet (Sat / Sun) so it is glanceable on a phone, no app required |
| Buffers over density | At least two optional add-ons held in reserve so a slot running short doesn't become dead time |
| No new tooling | This is a one-off plan; no recommender, no event API, no Bubls integration — out of scope per Epic |

## Component Design

### Preference Capture
**Purpose**: Resolve the five unknowns that drive every other decision — mobility, indoor/outdoor lean, food preferences, first-time-in-Zürich status, and budget tier. Until these are written down, every downstream choice is a guess. Captured as a short note in the folder, not a form or a database.

### Weather Gate
**Purpose**: A single Friday-evening decision point that flips the itinerary between the outdoor primary (Uetliberg ridge walk, ZSG lake cruise, Old Town stroll) and the indoor fallback (Kunsthaus, Landesmuseum, café crawl, Lindt Home of Chocolate). Both paths must be fully drafted upfront; the gate only selects, it does not plan.

### Itinerary Sheet
**Purpose**: The deliverable. Two columns (Sat / Sun), concrete time blocks, travel times between stops, walking distance per day footnoted. Same structure on both A and B paths so the switch is visually obvious. Lives as a markdown note — printed if mom prefers paper.

### Dinner Anchor
**Purpose**: The only fixed booking. Locked early because Saturday-night reservations in central Zürich tighten through the week. Choice between traditional Swiss (Zeughauskeller, Kronenhalle-tier) and a lighter option is driven by Preference Capture, not weather. Confirmation reference is recorded on the itinerary sheet.

### Buffer Pool
**Purpose**: A short, ranked list of optional add-ons (Grossmünster tower, Lindt Home of Chocolate, ZSG short lake loop) that can fill a slot running short or replace one running long. Not scheduled — held in reserve.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Itinerary format | Single markdown page | Glanceable on phone, no app install, easy to share with mom |
| Weather source | MeteoSwiss / SRF Meteo, checked Friday evening | Local model, more reliable for Alpine micro-climate than global APIs |
| Reservation channel | Restaurant website or phone | One booking — automation is overkill |
| Distribution | Shared note or printout | Mom-friendly; no login, no app |
| Backup channel | Telegram message to self | Fits Sam's existing OpenClaw mobile flow if the printout is forgotten |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Treat this as a planning note, not a product | Epic explicitly scopes out software; building a recommender for one weekend violates P4 (no speculative abstractions) | No reusable artefact; if this recurs, the work repeats |
| Two fully-drafted paths instead of one adaptive plan | Weather call is binary and late-binding; trying to build one plan that "flexes" would cost more thinking and hide the decision | Roughly 1.5× the upfront drafting effort |
| Lock dinner, leave everything else open | Reservations are the only inventory-constrained item; museums and lake cruises have walk-up capacity at this time of year | Mild risk if a specific museum is sold out — mitigated by the Buffer Pool |
| No Bubls integration | Bubls is a product; this is a personal request. Mixing them pollutes the product backlog and the personal plan | Loses any leverage Bubls' event data might have given — accepted, since the Old Town and lake content is well-known to the planner |
| Defer overnight side trips (Lucerne, Rigi, Rheinfall) | Multi-day scope wasn't confirmed and adds travel-day overhead that breaks pacing | If mom would have loved a Rigi sunrise, we miss it — re-openable as a follow-up if she stays longer |
| Pace to mobility, not to ambition | A weekend with mom optimises for shared time, not landmarks visited | Fewer "sights" on the list — by design |
| No architecture for code that will not be written | Per the Epic, no implementation should follow; producing a software design here would be ceremony, not value | This document is intentionally thin — it exists for folder consistency, not engineering input |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking