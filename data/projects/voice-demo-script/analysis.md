---
sidebar_position: 1
---

# 🔍 Voice Demo Script – Analysis

**Purpose**: Identify problems driving this capability.

**Date**: 2026-04-18

---

## Summary

- **Total Issues**: 5
- **Critical**: 2
- **High**: 2
- **Medium**: 1

---

## Problem

Humaniz.me is live with validated pricing ($5–$25/mo against StealthGPT's $15/mo) but zero public-facing proof that it works. The Reddit launch post is the first distribution moment. Text-only posts on r/ChatGPT average 10x less engagement than video posts. Without a demo, the post competes on copywriting alone — a losing game against established tools with social proof. The demo must be short enough to autoplay in Reddit's feed (under 30 seconds), compelling enough to stop scrolling (visible before/after transformation), and honest enough to survive r/ChatGPT's cynical audience.

## Hard Constraints

- **30-second maximum**: Reddit autoplay videos loop at the end. Anything over 30 seconds loses viewers on the second loop. Under 25 seconds feels rushed; 27–30 is the sweet spot.
- **No editing cuts**: Jump cuts signal "fake." A single continuous screen recording is more credible. One take, one trim at head/tail.
- **Mobile screen recording**: The product is a web app. Recording on mobile (iOS screen recording) shows it works on the device people actually use Reddit on. Desktop recording feels like a dev demo, not a user demo.
- **Must show voice input**: The mic → transcription → humanize flow is the differentiator. Every competitor has paste-and-rewrite. Voice input is the hook that makes someone stop scrolling.
- **No audio narration**: Reddit videos autoplay muted. The demo must be self-explanatory with visuals alone. Captions optional but the flow must read without them.

## Open Questions

| Question | Options | Recommendation |
|----------|---------|----------------|
| Side-by-side vs sequential? | A) Split screen showing before/after simultaneously B) Sequential flow showing transformation in real-time | **Sequential**. Side-by-side requires post-production compositing, breaks the "one continuous take" constraint, and feels like an ad. Sequential is authentic — the viewer watches the transformation happen live. |
| Captions/text overlay? | A) Clean recording, no overlay B) Minimal captions labeling each step C) Full subtitle track | **Minimal captions** — three labels max ("Step 1: Paste AI text", "Step 2: Humanize", "Step 3: Voice → Humanize"). Added in post using iOS markup or a free tool like CapCut. No subtitle track — too much visual noise for 30 seconds. |
| Which subreddit first? | r/ChatGPT (1.2M+), r/ArtificialIntelligence, r/SideProject | **r/ChatGPT** — largest audience, highest density of people who paste ChatGPT output into emails/essays and worry about detection. Post title frames it as a solution to their problem, not self-promotion. |

## Dependencies

- Humaniz.me must be live and responsive (it is — production confirmed)
- Voice input feature must work in mobile Safari/Chrome (verify before recording)
- iOS screen recording must capture the mic interaction (test: does iOS screen recording pick up in-app mic usage or does it conflict?)

## Explicitly Out of Scope

- Producing multiple demo variants or A/B testing different scripts
- Building any new product features for the demo
- Paid promotion or ad spend
- Analytics or tracking on the Reddit post itself

---

## Issue Breakdown

### Content Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No sample "obviously AI" text selected — must be instantly recognizable as ChatGPT output without context | CRITICAL | Task 1 |
| No spoken sentence chosen — must be natural, short, and produce a transcription that visibly benefits from humanization | CRITICAL | Task 1 |
| Recording timing not validated — 4 beats in 30 seconds may require rehearsal to avoid dead air during API response | HIGH | Task 3 |

### Production Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| iOS screen recording + in-app mic conflict unknown — if the system mic is captured by screen recording, the voice input may not work simultaneously | HIGH | Task 2 |
| No caption/overlay workflow defined — even minimal labels need a tool and a process | MEDIUM | Task 4 |

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

