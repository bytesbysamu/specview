---
sidebar_position: 1
---

# 🔍 Cold DM Outreach – Analysis

**Purpose**: Identify problems and open questions before executing outreach.

**Date**: 2026-04-18

---

## Summary

- **Total Issues**: 5
- **Critical**: 1
- **High**: 2
- **Medium**: 2

---

## Problem

Cold outreach to Twitter/X users who are publicly complaining about AI-sounding text is the fastest path to real testers. But executing it without preparation leads to wasted DMs (wrong targets), shadowbans (wrong cadence), and zero signal (no tracking).

## Hard Constraints

- DMs must be under 280 characters (Twitter DM has no hard limit, but short messages get read; 280 keeps the discipline of a tweet-length pitch)
- Tone must be helpful, not salesy — these people are frustrated, not shopping
- Must use personal account (brand accounts with zero followers sending DMs get flagged instantly)
- TestFlight link must be included (the ask is "try this," not "check out our website")
- 50 DMs over 2 days — not 50 in one hour (platform rate limits, shadowban risk)

## Open Questions

| Question | Impact | Resolution |
|----------|--------|------------|
| Personal account or product account? | Determines trust level and shadowban risk | Personal — new accounts with no history get flagged; personal account has social proof |
| Which search queries surface the best prospects? | Determines conversion rate of the entire funnel | Task 1 — test queries, rank by prospect quality |
| Should DMs include the product name or just the link? | Framing affects whether it reads as spam | Test in variants — one with name, one without |
| What time of day to send? | Response rate varies by timezone/activity | Send during US business hours (9am–5pm ET) when AI/writing discourse peaks |
| How to handle replies? | Need a follow-up protocol | Task 4 covers reply handling |

## Dependencies

- TestFlight link must be active and working (verify before first DM)
- Personal Twitter/X account must have DM permissions enabled
- Account must not be in restricted state from prior activity

## Explicitly Out of Scope

- Automated DM sending tools (Phantombuster, etc.) — manual only for v1
- Twitter Ads or promoted content
- Outreach on platforms other than Twitter/X
- Building a CRM or outreach SaaS tool
- A/B testing infrastructure — variant tracking is a spreadsheet

---

## Issue Breakdown

### Targeting Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No defined search queries to find prospects — random searching wastes time and finds irrelevant accounts | CRITICAL | Task 1 |
| No criteria for qualifying a prospect (follower count, bio, recency of tweet) — risk of DMing bots or inactive accounts | HIGH | Task 1 |

### Messaging Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No message templates — improvising DMs leads to inconsistent tone and untraceable results | HIGH | Task 2 |
| No variant strategy — sending the same message to everyone means no signal on what framing works | MEDIUM | Task 2 |

### Tracking Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No system to track who was contacted, which variant was sent, and whether they replied — makes retrospective impossible | MEDIUM | Task 3 |

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

