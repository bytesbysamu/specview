---
sidebar_position: 1
---

# 🔍 Distribution Experiment — Analysis

**Purpose**: Filter scope and surface unsettled decisions before the epic inflates.

**Date**: 2026-04-17

---

## Problem

Bubls has zero stranger validation. The product works, the pipeline ships, but demand is untested. Every feature added without distribution data is a bet placed blind. The experiment must answer one question: do strangers return after first use? Not "do they sign up" — do they come back unprompted?

## Hard Constraints

- **One channel only.** Multi-channel confuses attribution and multiplies effort. Reddit r/SideProject is highest volume, lowest effort, allows TestFlight links.
- **One week.** Day 7 is the verdict. No "let's wait another week." The retention window is 7 days — matches the architecture principle that unprompted return within 7 days is the only signal.
- **Retention, not vanity.** Impressions and signups are reported but do not inform the verdict. Only day-7 return rate decides continue/kill/pivot.
- **Existing infra only.** Neon Postgres for tracking. Coolify for hosting. No new services, no analytics SaaS, no paid tools.
- **No app changes for distribution.** The app ships as-is. If strangers don't return, the problem is demand or positioning, not missing features.

## Open Questions

| Question | Options | Leaning |
|----------|---------|---------|
| Landing page or direct TestFlight link? | Landing page adds a funnel step but captures non-iOS visitors and tracks clicks. Direct link is simpler. | Landing page — need the tracking, and non-iOS visitors hitting a dead TestFlight link is a bad first impression. |
| Where to host the landing page? | New route in Bubls frontend, standalone static page on Coolify, or external (Carrd, etc.) | Standalone static page on Coolify — decoupled from app deploys, loads fast, no framework overhead for one page. |
| How to detect "return" without app analytics SDK? | Client-side event on app open → POST to Flask → Neon. Or Capacitor plugin for lifecycle events. | Capacitor `App.addListener('appStateChange')` → POST to tracking endpoint. Lightweight, no SDK. |

## Dependencies

- TestFlight link must be active and accepting new testers (currently: yes).
- Bubls app must have a tracking endpoint deployed before the post goes live — otherwise day-1 opens aren't captured.
- Reddit account must meet r/SideProject posting requirements (age, karma). Verify before writing the post.

## Explicitly Out of Scope

- Multi-channel distribution (Twitter, HN, Product Hunt) — save for later if Reddit shows signal.
- Paid acquisition or ads.
- App Store submission — this tests demand before committing to review.
- Onboarding flow changes — ship what exists, measure what exists.
- Referral mechanics, invite codes, or viral loops.
- A/B testing the post copy — one post, one shot.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

