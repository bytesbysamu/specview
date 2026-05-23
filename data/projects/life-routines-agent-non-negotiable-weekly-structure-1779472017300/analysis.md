# 🔍 Life Routines Agent — Non-Negotiable Weekly Structure — Analysis

## The Problem
Sam has no weekly structure — exciting things get over-invested, routine things (gym, office, family) drift and die. The diary proves this pattern over 80+ days. He needs an agent that enforces minimum weekly commitments via proactive Telegram nudges, tracking everything through existing diary entries without adding new apps.

## Hard Constraints
- All tracking derived from diary text parsing — no new input apps
- Nudges delivered via Telegram through ClawBoi/OpenClaw pipeline
- Must run on the existing OpenClaw heartbeat (10-min interval)
- No calendar integration exists today — must be built or scoped out
- Lea excluded from friend tracking — hardcoded filter
- Knee injury active — exercise suggestions must be adaptive

## Open Questions
- **Where does this live?** New OpenClaw skill (SKILL.md) vs. extension of existing diary skill vs. new sam-plugin capability. Determines file boundaries and state management.
- **Calendar: which provider and how?** Google Calendar API, Apple Calendar, or just a static weekly template baked into the agent? API = real-time awareness but adds an adapter. Static = simpler but can't detect conflicts.
- **TGTG: API or manual?** `tgtg-python` exists but is unofficial and breaks frequently. Manual = user says "reserved TGTG", agent sets reminder. API = automated bag alerts. Pick one for v1.
- **Relationship to financial agent?** Brain dump says "not separate" but defines an independent scorecard. Is the routines agent a module *inside* the financial agent, or a peer that feeds it data?
- **Name extraction from diary — how?** "saw Hannah" is easy. "dinner at Mesob with the crew" is not. LLM parse on every entry, or keyword match against a known contacts list?

## Dependencies & Sequencing
- **Diary parsing reliability** blocks all tracking — if one-liner entries can't be parsed into structured routine data, nothing downstream works
- **Scheduled message dispatch** blocks the four anchor points (Mon/Wed/Fri/Sun) — OpenClaw heartbeat can check time windows, but who templates and sends the messages?
- **Contact list** (the 14 names in the brain dump) must be stored somewhere accessible to the agent before friend tracking works
- **TGTG decision** blocks the entire meal-planning subsystem — build the cooking/eating-out tracker first, add TGTG as a follow-on

## Explicitly Out of Scope
- **TGTG API integration** — unofficial library, breaks on auth changes, manual reserve-and-tell is sufficient for v1. Re-scope when manual flow is proven and bag frequency justifies automation.
- **SBB supersaver lookups** — requires scraping or API work for marginal value ("CHF 12 ticket" is a nice nudge but the agent can say "check SBB" without querying it). Re-scope if family visit compliance stays low after 4 weeks.
- **Event/activity suggestions from external sources** — "Kon-Tiki Comedy tonight" requires an event feed (Bubls? scraping?). Agent can suggest *types* of activities without knowing tonight's listings. Re-scope when Bubls has a queryable API.
- **Day-by-day meal plan templates** (Mon cook, Tue TGTG, Wed cook…) — this is over-prescriptive for someone who explicitly said "not rigid." Track cooking frequency, don't dictate which days. Re-scope if cooking count stays below 3/week for 3 weeks.
- **Friend CRM features** (TWINT reimbursement tracking, relationship warmth scoring) — track mention frequency, don't build a contacts manager. Re-scope when the core 5 metrics are stable.

## Contradictions to Resolve
- **"Zero extra apps" + "All tracking from diary"** vs. **TGTG API, calendar integration, SBB lookups** — the brain dump asks for proactive data the diary cannot provide. Decision: diary is the *input* layer; external APIs are *output/suggestion* layers added incrementally.
- **"Not rigid"** vs. **a fixed 7-day meal rotation** — pick one. Recommendation: track frequency goals, don't assign days.
- **"System comes to me"** vs. **"if I go silent, there's no diary data to track"** — the escalation ladder handles silence, but the scorecard becomes meaningless with no input. The agent must distinguish "no data" from "bad data."