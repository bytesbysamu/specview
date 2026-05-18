# 🎯 Epic: events

## Business Value

Bubls' value to Zürich users hinges on catalog breadth — if a local opens the app on Friday night and the listing skips the sold-out concert at Hallenstadion or the premiere at Schauspielhaus, the app stops being the default "what's on tonight" surface. Concerts and theater are the two highest-intent event categories in Zürich nightlife and culture spend, and their absence is the most common reason an event-discovery app gets uninstalled in favor of venue-specific apps or Google.

Expanding the catalog to concerts and theater turns Bubls from a niche feed into a credible primary discovery surface for the city. The user paying with attention (and eventually with affiliate-driven ticket clicks) is the Zürich resident or visitor planning their week. Broader catalog directly increases sessions per user and creates the inventory needed for any future affiliate or featured-listing revenue.

This epic is intentionally MVP-scoped: prove the catalog expansion ships and renders well on iOS before investing in ticketing deals, ranking, or push.

## Scope

### What This Epic Covers
- **Concert listings** – live music events in Zürich (clubs/DJ sets included for MVP — single broad bucket)
- **Theater listings** – spoken theater, opera, and dance under one bucket for MVP
- **Category filter UI** – flat tags (`concert`, `theater`) added to existing filter chips on the events screen
- **Single-source adapter** – one new adapter module behind the existing event-source boundary, daily batch refresh
- **Link-out to ticketing** – existing external-link behavior; no deep-link or affiliate work
- **iOS-first rendering** – list and detail views render concert/theater entries with category badge

### What This Epic Does NOT Cover
- ❌ **Multi-source aggregation** — One source for MVP; multi-source merging/dedup is a follow-up if catalog gaps appear
- ❌ **Ticket purchase in-app or affiliate links** — Trigger: explicit revenue decision
- ❌ **Hierarchical categories (genre, theater type)** — Flat tags only; trigger: filter UI feels too coarse in usage
- ❌ **Real-time refresh** — Daily batch is sufficient; trigger: stale-listing complaints
- ❌ **Push notifications for new concerts** — Trigger: retention metric problem
- ❌ **Personalized recommendations / ML ranking** — Trigger: catalog size makes browsing unusable
- ❌ **Geographic expansion beyond Zürich** — Trigger: explicit user request for another city
- ❌ **User-submitted events** — Trigger: moderation requirement appears

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Decide source + category model** | None | — | 0.5 days | High |
| 2 | **Frontend mock screens for concert/theater** | 1 | Yes (with 3) | 1.5 days | High |
| 3 | **Concert/theater adapter + openapi contract** | 1 | Yes (with 2) | 2 days | High |
| 4 | **Wire frontend to live Flask endpoint** | 2, 3 | — | 1 day | High |
| 5 | **Daily batch refresh job** | 3 | — | 0.5 days | Low |

## Success Criteria

- ✅ Opening the events screen on iOS shows at least one concert and one theater entry from Zürich within the next 14 days
- ✅ Filter chips include `concert` and `theater`; selecting either narrows the list correctly
- ✅ Each concert/theater entry has title, venue, start time, and a working external link to the source/ticketing page
- ✅ Backend stays under 200 lines added; new source goes through a single adapter module (P1)
- ✅ `openapi.yaml` updated first; DTOs regenerated; routes implement the contract (P5)
- ✅ Daily refresh runs as a daemon thread without blocking server shutdown (P3, code rules)
- ✅ Production iOS build passes (`ng build --configuration production`) before merge to master

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking