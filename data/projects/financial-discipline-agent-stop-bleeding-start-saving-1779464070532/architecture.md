# 🏗️ Solution Architecture: Financial Discipline Agent — Stop Bleeding Start Saving

## Architecture Overview

The Financial Discipline Agent is a set of OpenClaw skills that turn Sam's existing Telegram diary habit into a closed-loop spending feedback system. The core insight is that the data already exists — Sam writes daily diary entries mentioning meals, restaurants, and amounts — but the feedback arrives too late, as a monthly bank statement after the money is already gone. This architecture moves the feedback loop from monthly to daily by extracting spending signals from diary text, persisting them in a lightweight ledger, and pushing computed nudges back through Telegram on a daily and weekly cadence.

The system has three layers: an extraction layer that converts unstructured diary text into structured spending records, a persistence layer that stores daily entries and enables aggregation across arbitrary time windows, and a delivery layer that computes stats from the ledger and formats them for Telegram. Each layer maps to one or two OpenClaw skills. There is no HTTP API, no database server, and no new app — the entire system runs as SKILL.md files on the existing bytesbysamu.cloud VPS, communicating through Telegram via OpenClaw's channel integration.

The deliberate constraint is that all spending data is self-reported through diary entries. This means the system's accuracy ceiling is bounded by what Sam writes, not by what the bank records. The architecture treats this as a feature rather than a limitation: zero-friction input (Sam already writes the diary) beats high-accuracy input that requires a manual logging step Sam will abandon within two weeks.

## Design Principles

| Principle | Application in This System |
|-----------|---------------------------|
| P1 — Adapter Boundary | All AI extraction calls route through OpenClaw's claude-cli provider. Skills never call the Anthropic SDK directly. The extraction skill describes what to extract; the provider handles how. |
| P4 — No Speculative Abstractions | One ledger format, one extraction skill, one nudge skill. No generic "tracker framework" that could handle food, social, health, and career. Phase 2 concerns get their own skills when Phase 2 starts. |
| P6 — Skills First | Every component ships as a SKILL.md file with no build step. References hold the static data (meal list, budget constants, level definitions). Skills read from references, never duplicate constants inline. |
| P6 — Channel-Aware | Every outbound message is designed for Telegram's 4,096-character limit. Emoji serve as visual section separators. No HTML tables, no markdown tables — Telegram renders them poorly. |
| P6 — References as Source of Truth | Budget caps (CHF 75/week eating out, CHF 1,000/month savings target), level thresholds, point values, and the meal rotation list all live in reference files. Skills read these values at invocation time, so changing a budget cap is a one-line edit in one file. |
| P7 — File Size & Structure | Each skill is a single focused SKILL.md. The ledger is one JSON file. The meal reference is one markdown file. No file exceeds 200 lines. |

## Component Design

### Diary Spending Extraction Skill

**Purpose**: Transform unstructured diary text into structured spending records — the load-bearing foundation for every downstream component.

This skill activates when OpenClaw receives a Telegram message that the agent recognizes as a diary entry. Recognition is based on content signals: CHF amounts, restaurant names, meal references ("cooked," "ate out," "grabbed lunch"), or TooGoodToGo mentions. The skill uses Claude's language understanding through the cli provider to parse the entry rather than regex, because diary text is unpredictable — "had a CHF 25 thing at Parsaco" and "Parsaco Food Court, twenty-five francs" and "grabbed lunch (25.-)" must all resolve to the same structured record.

Each extraction produces a daily spending record containing: the date, a list of individual transactions (amount, category, and source text), a meal classification for each food transaction (cooked, ate-out, or tgtg), and the day's total spend. When a diary entry mentions cooking but no amount, the skill records a cooked-meal event with CHF 0 spend — this is essential for streak tracking. When no spending is mentioned at all, the day records as CHF 0 with no meal events, which is distinct from "cooked and spent nothing" and matters for streak accuracy.

The skill writes its output to the spending ledger file. If an entry for the same date already exists, the skill appends transactions rather than overwriting — Sam may write multiple diary entries in one day.

**Validation approach**: The epic requires 90% extraction accuracy against known bank data from January through April 2026. The architecture supports this by keeping the four months of bank statement summaries as a validation reference file. During development, the extraction skill can be run against historical diary entries and its output compared to bank data to measure precision before going live.

### Spending Ledger

**Purpose**: Single-file persistent state that enables aggregation across days, weeks, and months without an external database.

The ledger is a JSON file stored on the VPS filesystem at a fixed path within the OpenClaw workspace. It contains a flat collection of daily records keyed by ISO date. Each daily record holds the raw transaction list, meal events, and daily total. The ledger does not store computed aggregates — weekly totals, monthly totals, streak lengths, and point balances are all derived at read time by the nudge and scorecard skills.

**Why derive instead of store**: With a maximum dataset size of roughly 365 records per year, computing a weekly sum or scanning for consecutive cooking days is trivial. Stored aggregates create a consistency problem — if a diary entry is processed late or corrected, every stored aggregate that spans that date must be recomputed. Deriving from daily records means the latest read is always correct, with no stale cache to invalidate.

**Why a single JSON file instead of SQLite**: OpenClaw skills operate through Bash, Read, and Write tools. Reading and writing a JSON file is a native operation. SQLite would require the agent to shell out to the sqlite3 CLI, construct SQL strings, and parse tabular output — all feasible but unnecessarily complex for a dataset that will contain fewer than 400 records in its first year. If the ledger grows beyond a year or query patterns become complex enough to justify SQL, migration to SQLite is straightforward because the data model is already structured. This is a Phase 2 concern at earliest.

**Thread safety**: OpenClaw processes one message at a time per channel. There is no concurrent-write scenario — the extraction skill and the cron-triggered skills never run simultaneously on the same ledger. A write-then-read race is not possible in the single-consumer OpenClaw model, so no locking mechanism is needed.

**Backup**: The ledger file is small enough to include in the VPS's existing backup rotation. A corrupted or lost ledger is recoverable by re-extracting from diary history, though this is a manual process — acceptable for MVP.

### Daily Morning Budget Nudge

**Purpose**: Proactive Telegram message every morning that makes the invisible visible — spending pace and cooking momentum surfaced before the day's decisions, not after.

This skill is triggered by a system cron job on the VPS that invokes the OpenClaw skill at a fixed time each morning. The cron entry calls OpenClaw's CLI interface with the skill name; OpenClaw routes the output to Sam's Telegram channel. The skill reads the ledger, computes three metrics, and formats a single Telegram message.

**Metrics delivered**:

The cooking streak — consecutive days with at least one cooked-meal event, counting backward from yesterday. This is the behavioral reinforcement signal. A streak of zero is fine to report honestly; the gamification works through loss aversion (not wanting to break a streak) more than through accumulation.

The weekly eating-out spend versus the CHF 75 budget — summing all ate-out transactions from Monday through the current day of the week. The remaining budget for the week makes the cost of the next restaurant meal concrete: "CHF 22 left this week" reframes a CHF 25 lunch as a budget-breaker rather than a casual expense.

The monthly savings pace — total spending this month projected against the CHF 1,000 savings target. This connects daily food decisions to the monthly goal. The projection uses a simple linear extrapolation: (spending so far / days elapsed) × days in month, compared against the CHF 2,442 discretionary budget minus CHF 1,000.

**Message format**: The message uses emoji as section anchors (fire for streak, fork-and-knife for budget, chart for pace) with one line per metric. No paragraphs, no explanations — Sam knows the context. Total message length stays well under 1,000 characters, far below the 4,096 Telegram limit. The tone is sharp-friend: factual, direct, zero guilt-tripping. A bad day gets "streak reset to 0 — cook tonight and start a new one" not "you failed."

### Weekly Sunday Scorecard

**Purpose**: Gamified weekly summary that transforms spending data into a progress narrative — the "did I win this week" moment.

Triggered by a separate cron entry on Sunday morning. The skill reads the full ledger, computes weekly aggregates for the just-completed Monday-through-Sunday window, and delivers a single Telegram message with five sections.

**Cooking ratio**: Home-cooked meals versus ate-out meals for the week. The target from the epic is five cooked days per week. This section reports the ratio and compares it to the previous week — directional momentum matters more than absolute numbers in the early weeks.

**Spending breakdown**: Total food spend for the week, split between groceries (cooked-meal days), eating out, and TooGoodToGo. The eating-out subtotal is compared against the CHF 75 weekly cap. Weeks that come in under budget get a visual celebration; weeks over budget get the overage amount stated plainly.

**Points and level**: Points are computed from the week's meal events using the values defined in the gamification reference file (points per cooked meal, per TooGoodToGo purchase, penalty per expensive restaurant meal). The weekly point total determines the level label. Levels are cosmetic — they exist to make the scorecard feel like a game rather than an audit. The level thresholds and names live in a reference file so they can be tuned without editing the skill.

**Savings projection**: Monthly spending extrapolated from the weeks completed so far, compared against the CHF 1,000 target. This is the "are we going to make it" signal. If the projection shows savings below CHF 500, the scorecard flags it as off-pace with a specific CHF amount to recover in the remaining weeks.

**Message length budget**: The scorecard is the densest message in the system. Each of the five sections gets a two-line allocation (emoji header + one data line), plus a one-line summary at the top and bottom. This keeps the total under 800 characters. If future phases add sections (social spend, career momentum), the message can grow to roughly 1,500 characters before needing structural changes — well within Telegram's limit.

### Cooking Quick-Reference Skill

**Purpose**: Remove the "what do I even cook" friction that makes eating out the default decision.

This is the only reactive skill in the system — it activates when Sam asks a question like "what should I cook" or "dinner ideas" in Telegram. The skill reads a static reference file containing ten curated meals, each with an estimated cost per serving (all at or below CHF 8), a rough time estimate, and a one-line description. The skill selects one meal and presents it with the cost and time.

**Selection logic**: The simplest approach that avoids repetition is to read the ledger for the last three days' cooking entries (which may include meal names if Sam mentions what he cooked) and exclude those from the suggestion pool. If no recent cooking data exists, the skill picks at random. No preference learning, no ingredient tracking, no recipe database — P4 prohibits building a recommendation engine for a ten-item list.

**The reference file, not the skill, is the product**: The meal list is the value. The skill is just the delivery mechanism. The list should be curated for Sam's actual constraints: meals that require no more than 20 minutes of active cooking, use ingredients available at Migros or Coop within walking distance of Walchestrasse, and produce leftovers suitable for next-day lunch. The reference file is editable independently of the skill — Sam can add or swap meals without touching the skill definition.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Runtime | OpenClaw on bytesbysamu.cloud VPS | Already deployed, already Telegram-connected, zero incremental infrastructure cost |
| AI Provider | claude-cli via OpenClaw provider | Diary extraction requires NLU, not regex. Claude handles unstructured multilingual text (Sam mixes English and German). No API key management — OpenClaw handles provider routing |
| Persistence | Single JSON file on VPS filesystem | No external database needed for fewer than 400 records per year. Read/Write tool-native. Migrateable to SQLite if aggregation complexity grows |
| Scheduling | System cron on VPS | OpenClaw does not have built-in scheduling. A cron entry per skill (morning nudge, Sunday scorecard) calling the OpenClaw CLI is the simplest trigger mechanism with no custom scheduler to maintain |
| Delivery Channel | Telegram via OpenClaw | Sam's primary mobile interface. All messages designed for 4,096-character limit. No web UI, no second app |
| Skill Format | SKILL.md files | Per P6, skills first — no build step, iterate fast, graduate to plugin package only if skills hit real limits |

## Data Model

The ledger's conceptual structure centers on the daily record as the atomic unit. Each day contains zero or more transactions and zero or more meal events. A transaction has an amount in CHF, a category label (food-out, food-grocery, food-tgtg, transport, social, tech, other), and the source text from the diary that generated it. A meal event has a type (cooked, ate-out, tgtg) and an optional description.

All higher-order concepts — weekly totals, monthly totals, streaks, points, levels, budget remaining — are computed from daily records at read time. Nothing is cached. This makes the ledger append-mostly: the extraction skill writes daily records, and the nudge and scorecard skills only read.

Week boundaries follow ISO convention: Monday through Sunday. This aligns with Swiss cultural norms and ensures the CHF 75 weekly eating-out budget resets on Monday morning, giving the daily nudge a clean "budget remaining" number at the start of each work week.

Month boundaries are calendar months. The savings projection in the scorecard uses the actual number of days in the current month for extrapolation accuracy, not a fixed 30-day assumption.

## Cron Trigger Design

The VPS runs two cron entries:

The morning nudge fires at a fixed time early enough to precede Sam's first meal decision of the day. The exact time is a reference-file constant, not hardcoded in the cron entry — but changing it requires editing the crontab, which is acceptable for a value that changes at most once.

The Sunday scorecard fires on Sunday morning, after the Saturday spending has been processed. Since diary extraction happens when Sam writes (typically evening), the Sunday morning trigger ensures Saturday's data is already in the ledger.

Both cron entries invoke OpenClaw's CLI with the skill name and target Telegram channel. OpenClaw handles message delivery. If the VPS is unreachable or OpenClaw is down, the cron job fails silently — no retry queue, no alerting. A missed nudge is a minor degradation, not a system failure. Sam will notice the absence and can manually trigger the skill.

## Extraction Design

The extraction skill is the highest-risk component because it depends on Claude's ability to parse unstructured, inconsistent, multilingual diary text. The architecture mitigates this risk through three decisions.

**Prompt-driven extraction over code-driven parsing**: The skill provides Claude with explicit instructions on what to extract (CHF amounts, meal types, categories) and a small set of examples drawn from Sam's actual diary patterns. This leverages Claude's existing strength at information extraction from messy text. Regex would require enumerating every format Sam might use for amounts ("CHF 25", "25.-", "twenty-five francs", "25 Stutz") and every restaurant name — a brittle approach that degrades as Sam's language evolves.

**Category taxonomy kept small**: The extraction uses six categories (food-out, food-grocery, food-tgtg, transport, social, tech, other). More granular categories (distinguishing "pub" from "restaurant" from "takeout") add classification complexity without changing any downstream decision. The nudge and scorecard only care about the food-out total and the overall total. Additional categories can be introduced in Phase 2 without restructuring the ledger — they are just new label values on the same transaction schema.

**Validation against bank data as a development gate, not a runtime check**: The 90% accuracy target is verified during development by running the extraction skill against historical diary entries and comparing outputs to the bank statement summaries stored in a validation reference file. Once the extraction prompt achieves 90% on the historical data, it ships. There is no runtime accuracy monitoring — if extraction quality degrades, Sam will notice when the daily nudge numbers diverge from his mental model of what he spent, and he can flag it. Building automated accuracy monitoring for a single-user system violates P4.

## Gamification Design

Points, levels, and streaks exist to make the daily nudge and weekly scorecard feel like a game rather than a budget spreadsheet. The design is intentionally shallow — deep gamification (achievements, leaderboards, unlockable features) is speculative for a single-user system.

**Points are computed, not accumulated**: The scorecard computes points for the current week from that week's meal events. There is no lifetime point total in the MVP. This avoids the problem of early-week points making late-week overspending feel "covered" — each week starts fresh. If Sam wants lifetime tracking, it is a Phase 2 addition that reads all historical weeks from the ledger.

**Levels map to weekly point ranges**: The level label in the scorecard reflects the current week's performance, not a persistent progression. "Kitchen Boss" earned last week does not carry over if this week's cooking ratio drops. This keeps the level label honest and avoids the demotivation of losing a hard-earned persistent level.

**Streaks are the primary motivator**: Behavioral research consistently shows streaks drive habit formation more effectively than points. The cooking streak (consecutive days with at least one home-cooked meal) is the headline metric in the daily nudge. Streaks reset to zero on a missed day — no grace periods, no "freeze" tokens. The sharp reset is the point: it creates loss aversion that makes cooking the path of least resistance.

**Point values and level thresholds live in a reference file**: The extraction skill and delivery skills never hardcode these numbers. Tuning the gamification (making TooGoodToGo purchases worth more, adjusting the restaurant penalty threshold from CHF 30 to CHF 25) is a reference-file edit with no skill changes required.

## Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| JSON file over SQLite | Skills use Read/Write natively. No CLI SQL parsing needed. Dataset size is trivially small (under 400 records per year). | Aggregation queries are less expressive — weekly sums require reading and iterating all records. Acceptable at this scale; revisit if dataset grows past two years. |
| Derive aggregates instead of storing them | Eliminates stale-cache bugs. Late or corrected diary entries are automatically reflected in the next read. | Every nudge and scorecard read scans the full ledger. At under 400 records, this takes milliseconds. |
| AI extraction over regex | Diary text is unstructured, inconsistent, and mixes English and German. Claude handles this natively. Regex would require maintaining a fragile pattern library. | Each diary entry costs one Claude CLI invocation (~3-5 seconds). Acceptable for a once-daily operation. |
| System cron over custom scheduler | Zero lines of code to maintain. Cron is battle-tested on Linux. OpenClaw CLI is the invocation target. | Changing schedule requires SSH access to edit crontab. Acceptable for values that change at most quarterly. |
| No TooGoodToGo alerts | No public API exists. Building a scraper is a second project with ongoing maintenance cost that distracts from the core food-spending feedback loop. | Sam misses potential savings from TGTG bags he does not manually check. Passive tracking of TGTG purchases mentioned in diary entries still works. |
| Weekly point reset over lifetime accumulation | Prevents "banked points" masking current-week regression. Each week is an independent game. | No long-term progression feeling. Mitigated by streaks, which do carry across weeks and provide the persistent momentum signal. |
| Six spending categories, not fifteen | Fewer categories mean higher classification accuracy and simpler downstream logic. The nudge only needs food-out and total. | Less granular monthly analysis if Phase 2 wants detailed category breakdowns. Fixable by splitting categories later — new labels on existing transactions. |
| Monday-Sunday week boundaries | Aligns with Swiss convention and Sam's work-week rhythm. The CHF 75 budget resets when the work week starts, framing weekday lunches as budget decisions. | Weekend spending on Friday/Saturday counts against the current week, not the next. This is intentional — the weekly scorecard on Sunday reflects the full week just lived. |

## Risk Mitigation

**Diary entry quality degrades**: If Sam stops mentioning amounts or meal types, extraction accuracy drops and the nudge becomes useless. Mitigation: the daily nudge itself is the feedback loop — seeing "CHF 0 spent, 0 meals logged" when Sam knows he ate out will prompt better diary entries. The system is self-correcting through visibility.

**Sam stops writing diary entries**: The system produces no data and no nudges. This is an acceptable degradation — the agent cannot force behavior it can only reward. The streak reset to zero after missed days creates gentle pressure to resume. If diary writing stops for more than a week, the Sunday scorecard will show "no data" which is itself a signal.

**Ledger file corruption or loss**: The file is small and backed up with the VPS. Worst case, re-extract from Telegram diary history. This is manual but feasible — the diary messages are persistent in Telegram.

**Claude CLI extraction hallucinations**: The model might invent amounts not present in the diary text. Mitigation: the extraction prompt explicitly instructs Claude to extract only what is stated, never infer. The validation step during development tests for false positives (hallucinated amounts) as well as false negatives (missed amounts).

## Related Documents

- [Analysis](./analysis.md) — Bank data breakdown and problem identification driving this architecture
- [Epic](./epic.md) — Scope boundaries, task definitions, and success criteria this architecture fulfills
- [Timeline](./timeline.md) — Delivery sequencing and task status tracking