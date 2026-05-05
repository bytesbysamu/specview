The implementation guide is ready. Here's what it covers across 12 steps:

**Steps 1-3**: Project scaffold (Ionic + Angular + Capacitor), data model (`Pick`/`WeeklyPicks` interfaces matching the `bubls_picks` JSONB contract), and environment config pointing at the Express proxy.

**Steps 4-6**: The three core pieces — `PicksService` (thin HTTP wrapper, token-based identity), `EventCardComponent` (Ionic cards/chips, German titles, signal-based inputs), and `PicksDashboardPage` (the one screen with 5 cards or a Thursday countdown timer).

**Steps 7-8**: App bootstrap (one route, `mode: 'ios'` everywhere) and mock data with 5 realistic Zürich events so you can style the dashboard before Task 3 delivers real curation.

**Steps 9-10**: Express proxy endpoint (one SQL query, graceful empty response) and PWA manifest with service worker.

**Steps 11-12**: Capacitor iOS build pipeline (`ng build → cap copy → cap sync → Xcode`) and the dev workflow for both web (`ionic serve`) and iOS live reload.

The guide also includes verification checklists (web, iOS, PWA, cross-platform parity), edge case handling, and clear boundaries with the other tasks (onboarding is Task 5, push is Task 4, curation is Task 3).

Shall I save the file?