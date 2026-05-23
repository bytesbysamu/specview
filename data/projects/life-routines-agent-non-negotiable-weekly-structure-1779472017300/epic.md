# 🎯 Epic: Life Routines Agent — Non-Negotiable Weekly Structure

## Business Value

Sam's diary data across 80+ days reveals a clear pattern: high investment in exciting activities (product building, social events) paired with complete neglect of fundamentals (gym mentioned once then abandoned for 80 days, office attendance untracked, family visits unmonitored). This isn't a motivation problem — it's a visibility problem. Without a system that tracks weekly minimums and proactively nudges, routine commitments decay silently until the gap is too large to recover from gracefully.

The financial case is concrete. Current food spend trends toward ~CHF 400/week; a cooking-first approach with manual TGTG supplementation targets ~CHF 200/week — CHF 800/month in savings. Office attendance means free coffee and structured social lunches instead of CHF 15–25 daily food court spending. Friend meetups on the terrace cost CHF 0 versus CHF 55 at Kennedy's. Gym consistency prevents CHF 394 doctor visits. These aren't hypothetical — every number comes from Sam's own bank data and diary entries.

This agent is not a product for market — it is Sam's personal operating system layer, running inside the existing OpenClaw + Telegram pipeline. The consumer is one person, the ROI is measured in sustained habits and reduced financial bleed, and the entire system must work without adding a single new app or input surface beyond the diary entries Sam already writes.

## Scope

### What This Epic Covers

- **Diary-to-structure parsing** — Extract routine signals (office/WFH, exercise type, friend names, family mentions, meals cooked, eating-out spend, mood) from free-text diary entries, including ultra-short formats like "7/10, cooked, gym, saw Hannah"
- **Five core weekly metrics** — Track office attendance (goal: 2–3×), friend meetups excluding Lea (goal: 2×), gym/exercise (goal: 2×), family contact (goal: 1× per 2 weeks), and room cleanliness (Sunday + Wednesday prompts) against targets with week-over-week trend visibility
- **Four anchor-point messages** — Proactive Telegram nudges at Monday 7AM (weekly preview), Wednesday 8PM (mid-week check), Friday 6PM (weekend planning), and Sunday 9PM (weekly review + scorecard), all dispatched through ClawBoi via the OpenClaw heartbeat
- **Silence escalation ladder** — Graduated diary-gap response from grace period (day 1) through gentle ping (day 2), direct prompt (day 3), to blunt intervention (day 7), running on the existing 10-minute heartbeat
- **Cooking and meal tracking** — Daily 5PM meal prompt offering cook-or-TGTG options, cooking frequency tracking against 5×/week goal, manual TGTG reserve-and-remind flow (user says "reserved TGTG from X at 18:00", system sets pickup reminder)

### What This Epic Does NOT Cover

- ❌ **TGTG API integration** — Unofficial `tgtg-python` library breaks on auth changes; manual reserve-and-tell is sufficient for v1. Re-scope when manual flow is proven and bag frequency justifies automation
- ❌ **Calendar API integration** — No provider selected, adds an adapter boundary for uncertain value; v1 uses static weekly patterns and diary-derived context. Re-scope after 4 weeks of scorecard data reveals whether real-time calendar awareness changes behavior
- ❌ **SBB supersaver lookups** — Agent can suggest "check SBB" without querying price APIs; marginal value for significant integration work. Re-scope if family visit compliance stays low after 4 weeks
- ❌ **External event/activity suggestions** — Requires an event feed (Bubls API, scraping); agent can suggest activity *types* ("standup comedy Tuesday", "lake walk") without knowing tonight's listings. Re-scope when Bubls has a queryable API
- ❌ **Rigid day-by-day meal plans** — Over-prescriptive for someone who explicitly needs flexibility; track cooking frequency, don't dictate which days
- ❌ **Friend CRM features** — No TWINT reimbursement tracking, relationship warmth scoring, or contacts management; track diary mention frequency only. Re-scope when the core 5 metrics are stable
- ❌ **Financial agent integration** — Routines agent feeds data *to* the financial agent but does not own spend analysis or budget enforcement; that is a separate capability

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Diary Entry Parser for Routine Signals** — Parse free-text diary entries (including one-liners and emoji-only responses) into structured signals: office/WFH, exercise type + count, friend names matched against the known 14-person contact list, family/Yoseph mentions, meals cooked, eating-out amounts, and mood score. Must handle "7/10, cooked, gym, saw Hannah" as well as "shit day". Lea filtered from friend counts. | None | — | 3 days | High |
| 2 | **Weekly Metrics Engine & Scorecard** — Aggregate parsed diary signals into the 5 core metrics (office, friends, gym, family, room) plus cooking frequency and eating-out spend. Compare against weekly goals. Produce the gamified scorecard format for Sunday delivery. Track week-over-week trends to detect sustained failures (e.g., gym at zero for 3 consecutive weeks). | Task 1 | With Task 4 | 2 days | High |
| 3 | **Four Anchor-Point Message Dispatch** — Deliver proactive Telegram messages at Monday 7AM (weekly preview with metric goals and friend/family gaps), Wednesday 8PM (mid-week progress check + room tidy prompt), Friday 6PM (weekend planning: family visit?, meal prep?, social plans?), and Sunday 9PM (full scorecard + weekly review prompt). Time-window detection runs on the OpenClaw 10-minute heartbeat. Includes the daily 5PM meal planning prompt with cook-or-TGTG framing. | Task 2 | — | 3 days | High |
| 4 | **Silence Detection & Escalation Ladder** — Detect diary entry gaps via heartbeat and escalate through four tiers: day 1 grace, day 2 gentle 9PM ping, day 3 direct prompt naming the pattern, day 7 blunt intervention. Distinguish "no diary entry" from "diary entry with no data" (the latter keeps the streak alive). Track acknowledgment of anchor-point messages to detect full disengagement. | Task 1 | With Task 2 | 1 day | High |
| 5 | **Manual TGTG Reserve-and-Remind Flow** — Accept user input like "reserved TGTG from Mesob at 18:00" and set a pickup reminder 1 hour before the window. On planned TGTG days, send an 8AM morning prompt to reserve a bag before work. Track TGTG purchases with estimated retail value to calculate savings ("bag CHF 5.90 → retail ~CHF 18 → saved CHF 12.10"). No API integration — app checking is manual, reminders are automated. | Task 3 | — | 2 days | Low |

## Success Criteria

- ✅ Ultra-short diary entries ("7/10, cooked, gym, saw Hannah") are parsed into all relevant routine signals with ≥80% accuracy across a 2-week validation window
- ✅ All four anchor-point messages (Monday preview, Wednesday check, Friday planning, Sunday scorecard) are delivered within their scheduled time windows for 3 consecutive weeks
- ✅ Weekly scorecard accurately reflects the 5 core metrics with correct goal comparison (office 2–3×, friends 2×, gym 2×, family 1×/2wk, room prompted)
- ✅ Silence escalation triggers at the correct tier (day 2 gentle, day 3 direct, day 7 blunt) with zero false positives when diary entries exist
- ✅ Cooking frequency is trackable from diary data, and the week-over-week food category trend (cook vs. eat-out vs. TGTG) is visible in the Sunday scorecard
- ✅ Lea is never counted in friend metrics; known contact list of 14 names is matched against diary mentions without requiring exact-match formatting

## Related Documents

- [Analysis](./analysis.md) — Problems, contradictions, and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design for diary parsing, metrics engine, and heartbeat-driven dispatch
- [Timeline](./timeline.md) — Task status and delivery tracking