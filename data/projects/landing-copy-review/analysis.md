---
sidebar_position: 1
---

# 🔍 Landing Page Copy Review – Analysis

**Purpose**: Surface the specific problems in landing/index.html that leak conversions, and kill scope before the epic inflates.

**Date**: 2026-04-18

---

## Problem

The landing page is the only conversion surface for every distribution experiment. Weak copy, missing meta tags, or a broken email form means lost signups regardless of traffic quality. No systematic audit has been done — the page was shipped to unblock distribution, not to optimize conversion.

## Hard Constraints

- No real users yet — traditional social proof is unavailable and faking it violates trust
- The page is static HTML (landing/index.html), not an Angular route — changes are plain HTML/CSS/JS edits
- Email form must POST to the correct backend endpoint (Express on port 3100 or production equivalent)
- OG meta tags must work for Twitter Cards and LinkedIn previews — these are the primary share surfaces
- Mobile-first — most Reddit/Twitter traffic arrives on phones
- No frameworks, no build step for the landing page — keep it a single HTML file with inline or linked CSS

## Open Questions

| Question | Options | Recommendation |
|----------|---------|----------------|
| Social proof strategy with zero users | A) Skip entirely B) Show builder output metrics C) Show methodology credibility | **B** — "18 epics shipped in 42 hours" is concrete, verifiable, and speaks to the early-adopter audience. Avoids the "trusted by 0 companies" problem |
| TestFlight link handling | A) Hide until ready B) Show with "coming soon" badge C) Waitlist form instead | **C** — Waitlist captures intent and gives a distribution list for launch day. "Coming soon" is a dead end |
| Email form error states | A) Inline validation only B) Server-side with user feedback C) Both | **C** — Inline catches typos before submit, server-side prevents bad data. Both are cheap to implement |

## Dependencies

- Express server (server.js) must have the email signup endpoint active and tested
- OG image asset must exist at a stable URL (not localhost)
- No dependency on Angular build — landing page is standalone

## Explicitly Out of Scope

- A/B testing infrastructure — premature without traffic volume
- Analytics integration (Plausible, PostHog) — separate capability
- Blog or content pages — this is index.html only
- Pricing page — separate surface, separate capability
- Custom domain setup or DNS changes

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

