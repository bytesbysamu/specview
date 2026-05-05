---
sidebar_position: 3
---

# 🏗️ Cold DM Outreach – Solution Architecture

**Purpose**: System design for the cold DM outreach campaign — targeting, messaging, tracking, and measurement.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a manual outreach system, not a software system. The "architecture" is the workflow design: how search queries feed into prospect qualification, how qualified prospects get assigned a message variant, how every touchpoint is logged, and how the tracking data produces a channel verdict. The system has three layers: **Discovery** (find prospects), **Delivery** (send messages), and **Measurement** (track outcomes). Each layer has explicit inputs, outputs, and quality gates.

The key design constraint is authenticity. Automated outreach tools (Phantombuster, Tweet Hunter DM features, etc.) are deliberately excluded — not because they don't work mechanically, but because they produce messages that feel templated. The entire value proposition of this campaign is that a real person saw a real tweet and sent a real message. The system is designed to make that manual process efficient and trackable without making it robotic.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Manual over automated | Every DM is sent by hand from a personal account — authenticity is the moat against spam filters and user skepticism |
| Track everything, analyze later | Log before sending, not after — the spreadsheet is pre-filled with the prospect before the DM goes out |
| One touch only | No follow-up DMs — if they don't reply, they're not interested. Respect beats persistence |
| Helpful, not salesy | The DM solves a problem they publicly expressed — it's not a pitch, it's a recommendation |
| Fail fast, fail cheap | 50 DMs is a small enough batch to learn from without over-investing. Channel verdict after Day 2, not Day 30 |

---

## Component Design

### Task 1: Search Query System

**Purpose**: Surface high-intent prospects from Twitter/X's public timeline using keyword searches that match AI writing frustration patterns.

**Components**:
- `queries.md` — Ranked list of 8–10 search queries with expected hit rate and prospect quality notes
- Twitter/X Advanced Search — Native search with operators (`"exact phrase"`, `-filter:retweets`, `lang:en`, `since:2026-04-11`)

**Query categories (three intent levels):**

| Intent Level | Signal | Example Queries |
|--------------|--------|-----------------|
| **Direct pain** | User explicitly frustrated with AI-sounding text | `"sounds like ChatGPT"`, `"AI detection" caught me` |
| **Active search** | User looking for a solution | `"humanize AI text"`, `"make AI writing sound natural"` |
| **Adjacent frustration** | User dealing with consequences of AI detection | `"GPTZero" unfair`, `"Turnitin" false positive`, `"flagged as AI"` |

**Qualification gate**: A prospect must pass ALL of these before being logged in the spreadsheet:
1. Tweeted within last 7 days
2. Bio exists and reads as a real person
3. 50+ followers (engaged enough to check DMs)
4. Tweet expresses personal experience, not commentary
5. DMs appear to be open (check profile)

**Patterns**: Filter-then-qualify — search broadly, qualify strictly. Better to send 40 highly qualified DMs than 50 loosely targeted ones.

### Task 2: Message Template System

**Purpose**: Three distinct DM variants that cover different emotional registers while maintaining consistent tone (helpful, brief, genuine).

**Components**:
- `templates.md` — Three variants with character counts, emotional framing notes, and personalization slots

**Template constraints:**
- Under 280 characters (including TestFlight link)
- Must include TestFlight link (the call to action)
- Must reference their specific pain (not generic "check out my app")
- Must NOT include: price, feature lists, company name, "we", marketing language ("revolutionary", "game-changing"), or exclamation marks in the opening line
- Must feel like it was written for them specifically

**Variant assignment**: Round-robin (A → B → C → A → ...) to ensure even distribution across the 50-DM batch. No cherry-picking variants based on prospect profile — the goal is directional signal on which framing works, not per-prospect optimization.

**Personalization protocol**: Each DM should swap in one detail from their tweet to prove it's not a template. Examples:
- "Saw your tweet about [specific thing they mentioned]"
- "Your point about [specific frustration] resonated"

This takes 10 seconds per DM and is the difference between "someone read my tweet" and "bot spam."

### Task 3: Tracking System

**Purpose**: Single source of truth for every prospect contacted, variant sent, and outcome observed.

**Components**:
- Google Sheet — One row per prospect, columns defined in Epic Task 3
- No software, no database, no API — a spreadsheet is the right tool for 50 rows

**Tracking protocol:**
1. Find prospect via search query
2. Qualify against criteria (Task 1)
3. Log prospect in spreadsheet BEFORE sending DM (row exists = DM will be sent)
4. Send DM
5. Mark "Sent" column
6. Check for replies at end of each batch + next morning

**Why log before sending**: If you log after, you'll forget entries when the flow gets fast. Pre-logging also forces you to slow down and confirm the prospect is qualified before committing a DM slot.

### Task 4: Delivery Protocol

**Purpose**: Pacing and execution rules to avoid platform restrictions and maximize reply rates.

**Components**:
- Personal Twitter/X account (not a brand account)
- Manual sending via Twitter/X web or mobile app

**Pacing rules:**
| Rule | Value | Rationale |
|------|-------|-----------|
| Max DMs per hour | 5 | Platform safety — new DM senders get flagged above this |
| Min gap between DMs | 2 minutes | Natural human pacing |
| Daily cap | 25 | Half the total batch — allows course correction on Day 2 |
| Time window | 9am–2pm ET | Peak engagement for US writers/students |
| Sending platform | Web (not mobile) | Easier to copy-paste from spreadsheet + personalize |

**Account hygiene**: Before starting, ensure the personal account has: a real profile photo, a bio, recent tweets (last 7 days), and at least 100 followers. Accounts that look dormant or bot-like get their DMs filtered. If the account doesn't meet these criteria, spend Day 0 tweeting 3–5 times about AI writing topics to establish presence.

### Task 5: Measurement System

**Purpose**: Convert raw tracking data into a channel verdict.

**Components**:
- Spreadsheet pivot/summary row at bottom
- 5-line retrospective (see Epic Task 5 template)

**Metrics and thresholds:**

| Metric | Formula | Green | Yellow | Red |
|--------|---------|-------|--------|-----|
| Response rate | Replies / DMs sent | >15% | 10–15% | <10% |
| Install rate | Installs / Replies | >50% | 30–50% | <30% |
| Variant winner | Highest response rate | Clear winner (>2x others) | Slight edge | All equal |
| Query winner | Most qualified prospects per search | >5 per query | 2–5 per query | <2 per query |
| Retention (D7) | Active at Day 7 / Installs | >40% | 20–40% | <20% |

**Channel verdict logic:**
- **Continue** (scale to 100/week): Response rate green AND install rate green or yellow
- **Iterate** (change messaging, try again): Response rate yellow, or install rate red with response green
- **Kill** (channel doesn't work): Response rate red, or zero installs after 50 DMs

---

## Execution Flow

```
[Day 0 — Prep]
   Task 1 (queries) ──→ Task 2 (templates)
                        Task 3 (spreadsheet)
                            │
[Day 1 — Execute]          ▼
   Task 4 (25 DMs, paced at 5/hour)
         │
[Day 2 — Execute + Measure]
         ▼
   Task 5 (check replies → 25 more DMs → retrospective)
```

**Total time investment**: ~8 hours across 3 days (2h prep, 3h sending, 1h reply handling, 2h measurement + retrospective).

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Personal account vs. product account | Personal | Brand accounts with no history get DMs filtered; personal account has built-in social proof and trust |
| Manual sending vs. automation tools | Manual | Authenticity is the differentiator — templated DMs from tools get ignored or reported. 50 DMs is small enough to do by hand |
| 280-char limit vs. longer messages | 280 chars | Short messages get read. Long DMs from strangers get skipped. Matches Twitter's native communication style |
| Round-robin variant assignment vs. targeted | Round-robin | Sample is too small (17 per variant) for targeted assignment to be meaningful. Even distribution gives cleaner signal |
| One touch vs. follow-up sequence | One touch | Follow-up DMs from strangers cross the line from helpful to pushy. If they're interested, they'll reply to the first message |
| Google Sheet vs. Notion/Airtable/custom tool | Google Sheet | Zero setup, shareable, formulas for summary metrics. 50 rows doesn't need a database |
| TestFlight link vs. web app link | TestFlight | Humaniz.me is live on web, but TestFlight creates exclusivity and commitment — someone who installs an app is more invested than someone who clicks a link |
| 50 DMs vs. 100+ | 50 | Minimum viable batch to get signal. If 50 DMs yield zero installs, 100 won't fix it — the problem is upstream (targeting or messaging) |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

