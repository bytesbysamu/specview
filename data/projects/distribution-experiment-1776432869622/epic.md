---
sidebar_position: 2
---

# 🎯 Distribution Experiment — Epic

**Purpose**: Define scope and tasks for the 100-strangers distribution test.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and open questions resolved.

---

## Business Value

Bubls has no demand signal from anyone outside the builder's network. The product is complete enough to test — 6 epics shipped, 3 AI features, TestFlight live — but "complete enough" is a builder judgment, not a market verdict. This experiment replaces opinion with data.

The cost is near-zero: one landing page, one tracking table, one Reddit post, one week of patience. The upside is binary clarity. If strangers return, the product has legs and every subsequent feature investment is justified. If they don't, the pivot happens before more months are sunk. Either outcome is valuable — ambiguity is the only waste.

This also establishes the distribution muscle. Even if Bubls succeeds, every future product in the portfolio (Cold Email Writer, LinkedIn Post Generator, etc.) needs the same strangers-first test. Running it once, measuring it properly, and documenting the playbook means the second run takes hours instead of days.

---

## Scope

### What This Epic Covers

- A standalone landing page that presents Bubls to strangers and funnels iOS users to TestFlight
- Event tracking infrastructure to measure each funnel stage (page view → TestFlight click → app open → day-7 return)
- A single Reddit post on r/SideProject with clear positioning
- A daily metrics query and a day-7 verdict framework
- A documented decision (continue / pivot / kill) based on the return rate

### What This Epic Does NOT Cover

- ❌ Multi-channel distribution (no Twitter, no HN, no Product Hunt in this experiment)
- ❌ App Store submission or review process
- ❌ Changes to the Bubls app itself (features, onboarding, UI)
- ❌ Paid ads or sponsored posts
- ❌ Referral or viral mechanics
- ❌ Automated analytics dashboards (a SQL query is sufficient)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Tracking endpoint + schema** | None | 2 | 3h | High |
| 2 | **Landing page** | None | 1 | 3h | High |
| 3 | **App-open event instrumentation** | 1 | — | 2h | High |
| 4 | **Reddit research + post draft** | None | 1, 2, 3 | 2h | High |
| 5 | **Publish post + wire landing page tracking** | 1, 2, 3 | — | 1h | High |
| 6 | **Day-7 verdict query + decision** | 5 | — | 1h | Medium |

### Task Details

#### Task 1: Tracking endpoint + schema

Create a `distribution_events` table in Neon Postgres to record funnel events. Columns: `id`, `session_id` (UUID, set via cookie on landing page), `event_type` (enum: `page_view`, `testflight_click`, `app_open`, `app_return`), `created_at`, `metadata` (JSONB for user-agent, referrer, etc.). Add a Flask endpoint `POST /api/track` that inserts events. No auth required — these are anonymous strangers. Rate-limit to 10 events/minute per IP to prevent abuse. Use SQLAlchemy model, Alembic migration.

#### Task 2: Landing page

Build a single-page static site: headline (what Bubls does in one sentence), one app screenshot or short GIF, TestFlight CTA button for iOS users, email capture for non-iOS visitors ("Get notified when we launch on Android/Web"). Host on Coolify as a standalone Docker container (nginx serving static HTML/CSS/JS). The page fires a `page_view` event on load and a `testflight_click` event on CTA tap — both via `POST /api/track`. No framework, no build step. Plain HTML + vanilla JS. Must load in under 1 second on 3G.

#### Task 3: App-open event instrumentation

In the Bubls Capacitor app, add a listener for `App.addListener('appStateChange')`. On each foreground event, POST to `/api/track` with event type `app_open`. Include a `device_id` (generated on first launch, stored in Capacitor Preferences) so returns can be distinguished from first opens. The `app_return` event is not sent from the client — it's derived server-side: any `app_open` event from a `device_id` that has a prior `app_open` more than 24 hours earlier counts as a return. This avoids client-side date logic and makes the definition authoritative on the server.

#### Task 4: Reddit research + post draft

Verify r/SideProject allows TestFlight links (check rules, search for precedent posts). Check account meets posting requirements (age, karma). Draft post: lead with the problem Bubls solves (not the tech), include one screenshot, link to landing page (not directly to TestFlight — need the tracking). Keep it under 200 words. No "I built this" energy — frame it as "this exists now, here's what it does, try it if you're curious." Write a backup post for r/artificial if r/SideProject rules block it.

#### Task 5: Publish post + wire landing page tracking

Publish the Reddit post. Verify the landing page is live, tracking endpoint returns 200, and a test `page_view` event lands in Neon. Do a full manual walkthrough: open Reddit post → click landing page link → verify `page_view` recorded → tap TestFlight CTA → verify `testflight_click` recorded → install from TestFlight → open app → verify `app_open` recorded. Fix any broken links or failed events before walking away. Record the post URL, exact publish time, and initial upvote count.

#### Task 6: Day-7 verdict query + decision

On day 7 (or the morning of day 8), run the verdict query against Neon. Compute the full funnel: `page_view` count → unique `testflight_click` count → unique `device_id` with `app_open` → unique `device_id` with `app_return` (open > 24h after first open). Calculate conversion rates between each stage. The verdict is binary: if `app_return / app_open >= 0.05` (5%), the experiment produced signal — plan the next distribution push. If return rate is 0%, document what was learned and decide kill vs. pivot. If between 0% and 5%, dig into qualitative signal (did anyone DM, comment, or engage?) before deciding. Write the verdict as a one-page markdown file committed to the repo.

---

## Success Criteria

- ✅ Landing page is live and loads in under 1s on 3G
- ✅ Full funnel tracked end-to-end: page_view → testflight_click → app_open → app_return
- ✅ Reddit post published and reaching strangers (≥500 impressions proxy via upvotes/comments)
- ✅ Day-7 verdict delivered with concrete numbers, not vibes
- ✅ Binary decision documented: continue with signal, or kill/pivot with data

---

## Non-Goals

- ❌ Building a growth engine — this is one experiment, not a system
- ❌ Optimizing conversion rates — measure first, optimize only if there's signal
- ❌ Reaching 100 TestFlight signups — 100 strangers means 100 people who see the post, not 100 installs
- ❌ Getting Reddit karma or building a social presence
- ❌ Polishing the app before the experiment — ship what exists

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

