# 🔍 events — Analysis

## The Problem
Bubls currently surfaces a narrow slice of Zürich events. The brain dump asks to broaden the catalog to include **concerts and theater** alongside whatever is already indexed. Captured while driving — input is terse and underspecified.

## Hard Constraints
- Mobile-first surface: Ionic + Capacitor, iOS 16+, Angular signals
- Backend stays thin Flask (~150 lines, Blueprint, openapi.yaml-first)
- No Redis, no Postgres, no external queue — adapter pattern for any new source
- Geography stays Zürich (no signal to expand)

## Open Questions
- **Source of truth for concerts/theater** — (a) scrape venue sites, (b) licensed feed (Ticketmaster/Eventim API), (c) manual curation. Each has different cost/legal/freshness tradeoffs.
- **Category model** — (a) flat tags `concert`, `theater`, (b) hierarchy `music > concert > genre`, `performance > theater > type`. Affects filter UI and DB shape.
- **Ticketing integration** — link out only, or deep-link/affiliate? Brain dump is silent.
- **Scope of "concerts"** — clubs/DJ sets included, or strictly live music? "Theater" — opera and dance too, or spoken theater only?
- **Refresh cadence** — real-time, daily batch, or on-demand? Drives adapter design.

## Dependencies & Sequencing
- Category model decision blocks DB schema and filter UI
- Source decision blocks adapter contract and openapi.yaml
- Frontend mock-data screens for the new categories come first (per build-order pref), then Flask matches

## Explicitly Out of Scope
- Expanding beyond Zürich — not mentioned; trigger: explicit user request for another city
- User-submitted events / UGC — not mentioned; trigger: moderation requirement appears
- Ticket purchase inside the app — not mentioned; trigger: affiliate revenue decision
- Push notifications for new concerts — not mentioned; trigger: retention metric problem
- Personalized recommendations / ML ranking — speculative; trigger: catalog size makes browsing unusable