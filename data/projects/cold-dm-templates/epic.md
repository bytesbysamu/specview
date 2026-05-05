---
sidebar_position: 2
---

# 🎯 Cold DM Outreach – Epic

**Purpose**: Define scope and tasks for the cold DM outreach campaign targeting Twitter/X users frustrated with AI-sounding text.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

Humaniz.me is live in production with validated pricing ($5–$25/mo tiers) but no organic acquisition channel yet. The gap between "product works" and "product has users" is distribution, not features. Cold DM outreach closes that gap with the highest-fidelity signal available: you find someone who publicly expressed the exact pain your product solves, you hand them the solution, and you watch what happens.

The math is simple. 50 DMs × 10% response rate = 5 conversations. 5 conversations × 60% install rate = 3 TestFlight installs. 3 installs × 40% retention = 1–2 retained users. That's 1–2 people who found the product through a direct recommendation, used it on their real work, and came back. Their feedback is worth more than any survey, and their word-of-mouth is the seed of organic growth.

If the channel works (>10% response rate, >5% install rate), it becomes a repeatable weekly ritual: 30 minutes of searching, 30 minutes of sending, done. If it doesn't work, the failure mode is diagnostic — you learn whether the problem is targeting (wrong people), messaging (wrong pitch), or product-market fit (right people, tried it, didn't stick). Either outcome is valuable. Doing nothing is the only waste.

---

## Scope

### What This Epic Covers

- Defining Twitter/X search queries that surface high-intent prospects
- Writing 3 DM message variants (under 280 chars, helpful tone, TestFlight link)
- Setting up a lightweight tracking spreadsheet
- Executing 50 DMs across 2 days (25/day)
- Measuring response rate, install rate, and qualitative feedback
- Defining a reply protocol for conversations that open

### What This Epic Does NOT Cover

- ❌ Automated DM tools or bots (manual only — authenticity matters)
- ❌ Outreach on LinkedIn, Reddit, Discord, or other platforms
- ❌ Twitter Ads or paid promotion
- ❌ Building software to support the outreach process
- ❌ Follow-up campaigns beyond initial reply handling
- ❌ Content marketing or tweet threads (separate capability)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Define search queries + prospect criteria** | None | — | 2 hours | High |
| 2 | **Write 3 DM template variants** | 1 | 3 | 2 hours | High |
| 3 | **Set up tracking spreadsheet** | None | 2 | 1 hour | High |
| 4 | **Execute Day 1 batch (25 DMs)** | 1, 2, 3 | — | 1 hour | High |
| 5 | **Execute Day 2 batch (25 DMs) + measure results** | 4 | — | 2 hours | High |

### Task Details

#### Task 1: Define search queries + prospect criteria

Identify 8–10 Twitter/X search queries that surface people actively frustrated with AI-generated text sounding robotic or being flagged by detection tools. Queries should target recency (last 7 days), English language, and exclude retweets. Define qualifying criteria: the prospect should have a real bio (not a bot), at least 50 followers (engaged enough to check DMs), and their tweet should express a personal pain point (not a news article share). Produce a ranked list of queries by expected prospect quality.

**Search queries to test:**
- `"ChatGPT sounds" robotic`
- `"AI detection" flagged OR caught`
- `"humanize AI" text OR writing`
- `"GPTZero" OR "Turnitin" false positive`
- `"sounds like AI" -filter:retweets`
- `"AI writing" sounds wrong OR weird OR off`
- `"rewrite" "sound human" OR "sound natural"`
- `"AI detector" unfair OR broken OR wrong`

**Qualifying criteria:**
- Tweeted within last 7 days
- Bio exists and is coherent (not a bot)
- 50+ followers
- Tweet expresses personal frustration (not commentary or news sharing)
- DMs are open (or they follow a large enough account that you can request)

#### Task 2: Write 3 DM template variants

Write three distinct DM message variants, each under 280 characters, each with a different framing angle. All must include the TestFlight link, use a helpful (not salesy) tone, and feel like a real person reaching out — not a template. Each variant targets a different emotional register: empathy ("I saw your frustration"), utility ("I built something that fixes this"), and social proof ("others with the same problem are using this").

**Variant A — Empathy lead:**
> Hey! Saw your tweet about AI text sounding robotic — I had the same problem. Built a tool that rewrites AI text to sound natural. Free to try if you want: [TestFlight link]

**Variant B — Utility lead:**
> Noticed you're dealing with AI detection issues. I made a free app that humanizes AI-written text — makes it sound like you actually wrote it. Here if you want to try: [TestFlight link]

**Variant C — Curiosity lead:**
> Your tweet about AI writing resonated. Been working on something that fixes exactly that — turns AI text into natural writing. Grabbing early feedback: [TestFlight link]

Each variant should be tested against ~17 prospects (50 / 3 ≈ 17 each) with even distribution.

#### Task 3: Set up tracking spreadsheet

Create a simple Google Sheet (or Notion table) with columns: Date, Username, Tweet URL, Search Query Used, Variant Sent (A/B/C), Reply Received (Y/N), Reply Sentiment (positive/neutral/negative), Installed (Y/N), Notes. Pre-populate with the search query list from Task 1. This is the single source of truth for the campaign — every DM sent gets logged before sending the next one.

**Columns:**
| Column | Type | Purpose |
|--------|------|---------|
| Date | Date | When DM was sent |
| Username | Text | Twitter handle |
| Tweet URL | URL | The tweet that qualified them |
| Query | Text | Which search query surfaced them |
| Variant | A/B/C | Which template was sent |
| Replied | Y/N | Did they respond |
| Sentiment | +/0/- | Tone of reply |
| Installed | Y/N | Did they install via TestFlight |
| Retained D7 | Y/N | Still active 7 days later |
| Notes | Text | Qualitative feedback, quotes |

#### Task 4: Execute Day 1 batch (25 DMs)

Run through search queries from Task 1, qualify prospects against criteria, log each one in the spreadsheet, send the appropriate variant, and move to the next. Pace: no more than 5 DMs per hour (platform safety). Alternate variants (A → B → C → A → ...) across prospects. Send from personal account. Time window: 9am–2pm ET (highest engagement window for US-based writers/students). After sending all 25, note any patterns: which queries produced the most prospects, which prospects had open DMs vs. locked, any immediate replies.

**Cadence protocol:**
- 5 DMs per hour maximum
- 2–3 minute gap between DMs
- If a DM fails to send (locked DMs), log it and move on — do not count toward the 25
- Stop immediately if you receive a rate limit warning or temporary restriction

#### Task 5: Execute Day 2 batch (25 DMs) + measure results

Check for Day 1 replies first — respond to anyone who engaged (reply protocol: answer their question honestly, don't push, offer to help). Then execute the remaining 25 DMs using the same process. At the end of Day 2, compile metrics from the spreadsheet: total sent, response rate per variant, install rate, qualitative themes in replies. Write a 5-line retrospective: what worked, what didn't, whether to continue the channel.

**Reply protocol:**
- Positive reply ("cool, I'll try it"): Say thanks, ask what they'll use it for (context for product feedback)
- Question reply ("what does it do?"): Answer in 1–2 sentences, link to TestFlight again
- Negative reply ("stop spamming"): Apologize briefly, do not reply again
- No reply after 48 hours: Do not follow up — one touch only

**Retrospective template:**
1. Response rate: X/50 (target: >10%)
2. Install rate: X/Y responders (target: >50% of responders)
3. Best-performing variant: A/B/C
4. Best-performing search query: [query]
5. Channel verdict: continue / pause / kill

---

## Success Criteria

- ✅ 50 DMs sent across 2 days (25/day, paced at ≤5/hour)
- ✅ ≥5 replies received (10% response rate)
- ✅ ≥3 TestFlight installs from DM-sourced users
- ✅ ≥1 retained user at Day 7 (unprompted return)
- ✅ Tracking spreadsheet complete with all 50 entries logged
- ✅ Retrospective written with channel verdict (continue/pause/kill)
- ✅ Best-performing variant and query identified for future batches

---

## Non-Goals

- ❌ Building a DM automation tool or outreach SaaS
- ❌ Achieving viral growth from this batch alone
- ❌ Converting DM recipients to paid users (free TestFlight only)
- ❌ A/B testing with statistical significance (sample too small — directional signal only)
- ❌ Multi-platform outreach (Twitter/X only for v1)
- ❌ Influencer partnerships or paid placements

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

