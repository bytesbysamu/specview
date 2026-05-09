# 🎯 Epic: mom next weekend

## Business Value

This epic does not deliver business value in the product sense — it is a personal planning request, not a shippable capability. The "value" is a curated, low-friction Saturday/Sunday plan in Zürich (2026-05-16 / 2026-05-17) that respects mom's pacing, the weather, and a reasonable budget. The "customer" is the builder; the "payment" is the time invested upfront to avoid a fragmented weekend.

It is captured here only because the spec-doc pipeline was invoked. The analysis flagged that this request does not belong in the pipeline. This epic exists as a thin scaffold so the folder is internally consistent, but no implementation guides, architecture docs, or code should follow. If the request is later reframed as a product feature (Bubls event integration, a trip-planner tool), a new epic should be opened with proper scope.

The minimum useful output is a one-page itinerary with a weather-driven A/B path and one dinner reservation locked in.

## Scope

### What This Epic Covers
- A two-day Zürich itinerary draft (Sat + Sun) — anchored to mom's pacing and interests
- A weather-contingent A/B plan — outdoor primary (Uetliberg, lake cruise, Old Town walk) vs. indoor fallback (Kunsthaus, Landesmuseum, café crawl)
- One booked Saturday dinner reservation — traditional Swiss vs. lighter option, pending mom's preference
- A short list of optional add-ons — Lindt Home of Chocolate, Grossmünster tower, ZSG short lake loop

### What This Epic Does NOT Cover
- ❌ Building a Zürich activity recommender — out of scope; this is a one-off plan, not a product
- ❌ Bubls event data integration — out unless explicitly reframed as a Bubls feature
- ❌ Overnight side trips (Lucerne, Rigi, Rheinfall) — deferred unless mom wants a multi-day trip
- ❌ Implementation guides, architecture, or code artifacts — no software is being built
- ❌ Premium experiences (Dolder spa, helicopter, private guides) — out unless budget tier is confirmed

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Confirm mom's preferences** (mobility, indoor/outdoor, food, first-timer y/n, budget) | None | — | 0.25 day | High |
| 2 | **Check weather forecast** for Sat/Sun and lock outdoor-vs-indoor primary path | Task 1 | Yes (with 3) | 0.1 day | High |
| 3 | **Draft Sat + Sun itinerary** with A/B weather-contingent slots and travel times | Task 1 | Yes (with 2) | 0.5 day | High |
| 4 | **Book Saturday dinner reservation** (traditional Swiss or lighter option per Task 1) | Task 1 | — | 0.25 day | High |
| 5 | **Compile shortlist of optional add-ons** (chocolate museum, tower, lake loop) as buffer slots | Task 3 | — | 0.25 day | Low |

## Success Criteria

- ✅ Mom's pacing, dietary, and budget preferences captured in writing before planning starts
- ✅ A single-page itinerary exists for both Saturday and Sunday with concrete time blocks
- ✅ Both an outdoor-primary and indoor-fallback path are documented and switchable on Friday evening based on forecast
- ✅ Saturday dinner reservation is confirmed with a booking reference
- ✅ Total planned walking distance per day matches mom's stated mobility level
- ✅ At least two buffer activities are pre-identified in case a slot runs short or long

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking