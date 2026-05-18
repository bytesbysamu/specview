---
name: Bubls — no foreign URL links
description: In Bubls, event cards must not link out to external event URLs. There's an in-app details page that owns all event data.
type: feedback
originSessionId: 7cda5ddd-d774-4826-9d3f-7bfd1c5f774f
---
Event cards in Bubls must NOT link to external/foreign URLs (no `window.open`, no `Browser.open` to source sites). Bubls has its own in-app details page that displays the full event data.

**Why:** User explicitly rejected external linking. Bubls owns the full event data (title, summary, time, venue, price, image, description). Sending users off to Tagesanzeiger/Eventbrite/etc. breaks the curated experience, creates dead-link risk, and gives up engagement data.

**How to apply:** When wiring event card taps or detail flows, route to an internal page (e.g. `/pick/:id`) that renders Pick data from PicksService. The `Pick.url` field — if kept at all — is only for attribution display, not navigation. Don't install `@capacitor/browser` for this purpose.
