# 🏗️ Solution Architecture: Life Routines Agent — Non-Negotiable Weekly Structure

## Architecture Overview

The Life Routines Agent is not a standalone application — it is a capability layer inside the existing OpenClaw workspace, triggered by two inputs that already exist: diary entries arriving via Telegram, and the 10-minute heartbeat that already runs. The core architectural insight is that every feature in this system reduces to one of two operations: **parse an inbound diary message into structured signals**, or **check the clock and accumulated state to decide whether an outbound message is due**. There is no request-response cycle, no HTTP API, no frontend. The entire system is event-driven by text input and time.

The design decomposes into five components arranged in a pipeline. The **Diary Parser** converts free-text into structured signal records. The **Signal Store** persists those records as flat JSON files keyed by date. The **Metrics Engine** aggregates signals across a rolling week window and compares against goal thresholds. The **Heartbeat Dispatcher** runs on each 10-minute tick, evaluating time-window rules to decide which messages — anchor-point nudges, silence escalations, or TGTG reminders — need to fire. The **Scorecard Renderer** formats metric snapshots into Telegram-safe output for the four anchor-point messages.

Every component is a separate skill file. No component knows how another component works internally — they communicate through the signal store files and the contact reference. This means any skill can be rewritten, replaced, or disabled without cascading changes, which matters for a system that will evolve as Sam's routines shift.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P1 — Adapter Boundary** | All Telegram message dispatch goes through OpenClaw's existing channel adapter. Skills never construct Telegram API calls directly — they produce a message payload and let the ClawBoi agent handle delivery. This also means the system works identically if a web UI channel is added later. |
| **P4 — No Speculative Abstractions** | There is exactly one consumer (Sam), one input channel (Telegram diary), and one output channel (Telegram nudges). No generic "routine framework" or pluggable metric registry. Five metrics are hardcoded as five fields. A sixth metric means adding a sixth field — not building a metric plugin system for five items. |
| **P6 — Skills First** | Every component starts as a SKILL.md file with no build step. The parser is a skill. The scorecard is a skill. The heartbeat dispatcher is a skill. If a skill hits real limits (needs persistent background state beyond files, needs to register its own cron), it graduates to a plugin component. Not before. |
| **P6 — References as Source of Truth** | The contact list (14 names, Lea exclusion flag, last-seen thresholds) lives in a single reference file. The parser skill reads it to match names. The metrics skill reads it to compute friend gaps. The scorecard skill reads it to render names. No skill duplicates the list. |
| **P6 — Channel-Aware Output** | Every outbound message must fit within Telegram's 4,096-character limit. The scorecard renderer enforces this as a hard constraint — if a weekly review exceeds the limit, it truncates detail sections rather than splitting into multiple messages, because multi-message delivery complicates acknowledgment tracking. |
| **P7 — File Size & Structure** | Each skill file stays under 200 lines. The parser skill does not also compute metrics. The dispatcher skill does not also render scorecards. One concern per file. |

## Component Design

### Diary Parser

**Purpose**: Convert free-text diary entries of any length — from "shit day" to a 500-word reflection — into a structured signal record with consistent fields.

The parser handles a spectrum of input formats. The minimal case is a mood-only entry ("7/10" or even "👍"), which produces a record with just a mood score and a flag that the streak is alive. The maximal case is a full narrative entry from which office/WFH status, exercise type and count, friend names, family mentions, meal data, spending amounts, and mood are all extracted. The parser must degrade gracefully: missing fields are null, never inferred. If Sam writes "good day" and mentions no friends, the friend field is an empty list — not a guess.

Name matching runs against the contact reference file, which contains the 14 known names with variant spellings (e.g., "Adi" and "Adrian" resolve to the same person). Lea is present in the reference but flagged as excluded from friend-metric counting. The parser emits her name in the raw signal if mentioned — the exclusion happens downstream in the metrics engine — because the parser's job is to extract what was said, not to interpret what it means for goals.

Exercise detection uses keyword matching with a category list: gym, workout, run, walk, swim, dance, padel, yoga, hike. Long walks count — the reference file defines the inclusion threshold (any walk mentioned intentionally counts; the system does not try to distinguish "walked to the store" from "went for a long walk along the lake"). This is a deliberate trade-off: false positives on exercise are less damaging than false negatives that discourage Sam from logging casual movement.

Mood extraction accepts numeric scores (7/10, 7, seven), emoji shorthand (👍 → 7, 😐 → 5, 💀 → 2), and descriptive words ("great" → 8, "shit" → 3). The mapping lives in the contact reference file alongside the name list — a single reference file for all parser configuration.

### Signal Store

**Purpose**: Persist parsed diary signals in a format that the metrics engine can aggregate without re-parsing.

Each day's signals are stored as a single JSON file named by ISO date (2026-05-22.json) inside the OpenClaw workspace data directory. One file per day, not one file per entry — if Sam sends multiple diary messages in a day, each parse appends to that day's signal file by merging fields. The merge rule is last-write-wins for scalar fields (mood, office status) and union for list fields (friends seen, exercises done). This means Sam can send "gym this morning" at noon and "saw Hannah tonight" at 10 PM and both signals land in the same day record.

The weekly view is computed by reading the seven files for Monday through Sunday of the target week. Missing files mean missing days — the metrics engine and silence detector both use file-existence as the primary diary-gap signal. This is simpler and more reliable than maintaining a separate "last entry" timestamp, because the file system is the single source of truth.

No database. No Redis. Flat JSON files in a known directory. This aligns with the OpenClaw workspace model where context files are the persistence layer, and with Sam's constraint against external infrastructure for single-consumer tools.

### Metrics Engine

**Purpose**: Aggregate a week's signal files into the five core metrics plus cooking frequency and eating-out spend, compare against goals, and detect multi-week trend failures.

The engine reads all signal files for the current ISO week and produces a metrics snapshot: office count (goal: 2–3), unique friends seen excluding Lea (goal: 2), exercise sessions (goal: 2), family contact flag (goal: 1 per rolling 14 days), room prompts acknowledged (binary: prompted or not), cooking count (goal: 5), and total eating-out spend (goal: under CHF 75). Each metric carries a status: met, at-risk (reachable but behind pace given remaining days), or missed.

The "at-risk" calculation is day-of-week-aware. If it is Wednesday and gym count is zero, the metric is at-risk because four days remain. If it is Saturday and gym count is zero, the metric is effectively missed. This distinction matters because the Wednesday anchor-point message uses at-risk status to nudge without alarm, while the Sunday scorecard uses final status for the gamified report.

Trend detection operates on a rolling 3-week window. If any metric is at zero for three consecutive weeks (the gym pattern from the diary data), the scorecard escalates its language from informational to confrontational. This is not configurable per-metric in v1 — three weeks at zero is the universal escalation threshold. Adding per-metric thresholds would be a speculative abstraction for a system that has not yet proven which thresholds matter.

Family contact uses a 14-day rolling window rather than a calendar week because the goal is biweekly. The engine tracks the last signal-file date containing a family or Yoseph mention and computes days-since. This crosses week boundaries intentionally.

### Heartbeat Dispatcher

**Purpose**: Run on each OpenClaw 10-minute heartbeat tick and decide whether any outbound message needs to fire, then delegate to the appropriate skill.

The dispatcher is the scheduling brain. It does not generate message content — it evaluates time-window rules and invokes the correct skill when a window matches. The four anchor-point windows are:

- **Monday 7:00–7:30 AM** → invoke weekly-preview skill
- **Wednesday 8:00–8:30 PM** → invoke midweek-check skill
- **Friday 6:00–6:30 PM** → invoke weekend-planning skill
- **Sunday 9:00–9:30 PM** → invoke weekly-review skill

Each window is 30 minutes wide (three heartbeat ticks) to absorb clock drift without double-firing. The dispatcher writes a "last-fired" timestamp per anchor point into a dispatcher state file after successful delivery. On each tick, it checks: is the current time inside the window AND is the last-fired timestamp outside the window? If both conditions hold, fire. This prevents duplicate messages if the heartbeat runs three times during the 30-minute window.

The daily 5 PM meal prompt uses the same mechanism — a 5:00–5:30 PM window, every day. The dispatcher checks whether a meal prompt was already sent today before firing.

Silence detection also runs on each tick but uses a different clock: it checks whether a signal file exists for yesterday (evaluated after 9 PM to avoid false positives during a normal day). The escalation tier is determined by counting consecutive days with no signal file, and the tier determines which silence-response skill to invoke. The grace period (day 1) means no skill is invoked — the dispatcher simply notes the gap and moves on.

The dispatcher maintains its own small state file (last-fired timestamps, current silence streak count) separate from the signal store. This file is the only mutable state the dispatcher owns.

### Scorecard Renderer

**Purpose**: Format a metrics snapshot into a Telegram-deliverable message with the gamified visual style Sam described.

The renderer takes a metrics snapshot from the engine and produces a UTF-8 string under 4,096 characters. The format uses emoji status indicators (✅ met, ⚠️ at-risk, ❌ missed), numeric progress (e.g., "2/3"), and — for the Sunday review — week-over-week trend arrows (↑ improved, → flat, ↓ declined).

Four message variants exist, one per anchor point. The Monday preview is forward-looking (goals for this week, gaps carried from last week, friend/family suggestions). The Wednesday check is progress-focused (current counts, room tidy prompt). The Friday message is planning-oriented (weekend activity suggestions, family visit prompt if gap exceeds 10 days). The Sunday scorecard is the full gamified report with all seven metrics, trend arrows, and a streak counter for consecutive weeks with all five core metrics met.

The renderer is the only component that knows about Telegram formatting constraints. All other components work with structured data. This separation means the renderer can be swapped for a different channel format (email digest, web dashboard) without touching the metrics engine or dispatcher.

### TGTG Reminder Flow

**Purpose**: Accept manual reservation announcements and set time-based pickup reminders, plus deliver the daily 8 AM reserve prompt on designated TGTG days.

This flow is intentionally manual for v1. Sam tells ClawBoi "reserved TGTG from Mesob at 18:00" and the system parses the place name and pickup time, then sets a reminder for one hour before the pickup window. The reminder fires via the heartbeat dispatcher — the TGTG skill writes a pending-reminder record (place, pickup time, reminder time) to the dispatcher state file, and the dispatcher checks for due reminders on each tick.

The 8 AM reserve prompt fires on days Sam has indicated as TGTG days in the weekly plan. In v1, this defaults to a static pattern (Tuesday and Thursday evenings) that Sam can override by telling ClawBoi to change TGTG days. The pattern lives in the contact reference file alongside the name list and parser config — one reference file for all configuration that might change.

Savings tracking is append-only. Each TGTG purchase logged by Sam includes the bag price; the system estimates retail value at 3× the bag price (industry standard ratio) and appends the savings entry to the current week's signal file. The Sunday scorecard includes cumulative monthly TGTG savings.

No TGTG API integration. The `tgtg-python` library requires authentication that breaks on app updates, and the failure mode (silent auth expiry, no bags shown) is worse than the manual flow (Sam checks the app, which takes 30 seconds). Re-scoping for API integration requires the manual flow to be proven over 4 weeks and the bag frequency to justify the maintenance burden.

## Data Architecture

### Signal File Schema

Each daily signal file contains the parsed output of all diary entries for that date. Fields are nullable — a minimal entry ("shit day") produces a record with only mood populated and a streak-alive flag set to true. The schema covers: mood score (1–10 integer), office status (office/wfh/null), exercise list (array of activity type strings), friends seen (array of matched contact names), family contact (boolean), meals cooked (integer count), eating-out spend (decimal CHF amount), tgtg purchases (array of price entries), and raw text (original diary input preserved for re-parsing if the parser improves).

### Contact Reference File

A single reference file in the OpenClaw workspace containing: the 14-person contact list with canonical names and known aliases, Lea's exclusion flag, the exercise keyword list with inclusion rules, the mood-word-to-score mapping, the TGTG day pattern, and the escalation tier thresholds (days 2/3/7). This file is the only place configuration lives. Skills read it; nothing else writes to it except Sam via direct edit.

### Dispatcher State File

A small file tracking: last-fired timestamp per anchor point (to prevent double-firing), current silence streak count (to determine escalation tier), and pending TGTG reminders (place, pickup time, reminder time). This file is read-write by the dispatcher only. It resets weekly for anchor-point timestamps and resets on any diary entry for the silence counter.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Runtime | OpenClaw workspace skills | Already running, already connected to Telegram via ClawBoi, already has the 10-minute heartbeat. Zero new infrastructure. |
| Persistence | Flat JSON files in workspace data directory | Single consumer, no concurrent writes, no query complexity. A directory listing is the "database query." Aligns with P4 — no database for one user writing one file per day. |
| AI layer | Claude CLI via OpenClaw's chain adapter | Diary parsing uses Claude to extract structured signals from free text. The prompt is deterministic (system prompt + diary text + contact reference → JSON). Routed through the existing adapter, never imported directly. |
| Scheduling | OpenClaw heartbeat (10-minute interval) | No cron, no external scheduler. The heartbeat is already running. Time-window matching on each tick replaces a dedicated scheduler with zero additional moving parts. |
| Delivery | Telegram via ClawBoi channel | Already the primary interface. No new app, no new notification channel. Messages must stay under 4,096 characters. |
| Configuration | Single reference file in workspace | One file holds all tunable values (contact list, exercise keywords, mood mappings, TGTG days, escalation thresholds). Skills read from this file. Editing configuration means editing one file. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **File-per-day signal storage instead of a database** | One user, one write per day, queries are always "give me this week" (7 file reads). SQLite adds a dependency and schema migration burden for a workload that is literally 7 file reads. | Cannot do ad-hoc queries like "show me all days I went to gym" without reading all files. Acceptable because the only query pattern is weekly aggregation. If month-over-month analysis becomes needed, a batch script can read 30 files in milliseconds. |
| **Parser uses Claude CLI for extraction instead of regex** | Diary entries are wildly variable — "saw Hannah and Adi at the lake, cooked pasta after" requires semantic understanding that regex cannot provide. The contact reference file gives the LLM a bounded name list to match against, making extraction reliable without building a custom NER pipeline. | Every diary entry costs one Claude CLI call (~2–5 seconds). Acceptable because diary entries arrive at most a few times per day, not at scale. The latency is invisible in a Telegram async flow. |
| **30-minute fire windows instead of exact-time cron** | The heartbeat runs every 10 minutes, not every minute. A 30-minute window guarantees at least three ticks fall inside it, absorbing timing jitter. Exact-time delivery would require a dedicated cron, adding infrastructure for marginal precision — Sam does not care if the Monday preview arrives at 7:00 or 7:20. | Messages may arrive up to 20 minutes after the nominal time. Acceptable for a nudge system where ±20 minutes has zero behavioral impact. |
| **Lea exclusion as a data flag, not parser logic** | The parser extracts all mentioned names including Lea. The metrics engine applies the exclusion. This keeps the parser generic (it finds names) and the business rule (Lea is excluded from friend counts) in one place: the contact reference file. | The signal file will contain Lea's name when mentioned, which could feel odd if Sam inspects raw data. Acceptable because Sam will interact through the scorecard, not raw JSON files. |
| **No TGTG API integration in v1** | The `tgtg-python` library uses unofficial API access that breaks on auth changes. The failure mode (silent breakage, no bags shown, Sam thinks no bags are available) is worse than the status quo (Sam checks the app manually in 30 seconds). Manual reserve-and-tell costs 10 seconds of input for reliable reminders. | Sam must open the TGTG app manually and announce reservations. If TGTG usage exceeds 8 bags/month and the manual flow becomes friction, API integration re-enters scope. The architecture supports it: a TGTG adapter skill could replace the manual-input skill without changing the reminder or tracking logic. |
| **Static TGTG day pattern instead of dynamic optimization** | v1 defaults to Tuesday/Thursday for TGTG. Sam can override by telling ClawBoi. Dynamic optimization ("TGTG on days you're not cooking") requires cooking-plan data that does not exist yet — Sam does not plan meals in advance, so there is no signal to optimize against. | Sub-optimal TGTG timing on weeks where Sam cooks on Tuesday anyway. Acceptable because the cost of a wasted prompt ("reserve TGTG tonight?" → "no, I'm cooking") is one ignored message, not a system failure. |
| **Silence streak resets on any entry, not on substantive entry** | Even "👍" resets the silence counter. The goal is diary habit maintenance, not data richness. A thumbs-up proves Sam is engaged; pushing for more content when engagement is fragile risks full disengagement. | Low-content entries produce sparse signal files, weakening weekly metrics accuracy. Acceptable because the alternative (silence counter keeps climbing despite engagement) would trigger escalation messages that feel punitive and erode trust in the system. |
| **Single reference file for all configuration** | Contacts, exercise keywords, mood mappings, TGTG days, and escalation thresholds live in one file. Multiple config files for a system with five metrics and 14 contacts is over-engineering. | The file will grow as configuration accumulates. At current scope (~50 lines of YAML-style config), this is years away from being a problem. Split when the file exceeds 200 lines, consistent with P7. |
| **Trend detection at fixed 3-week zero threshold** | A metric at zero for 3 consecutive weeks triggers escalated language. No per-metric customization. The gym-at-zero-for-80-days pattern from diary data shows that Sam's failure mode is consistent across categories: not gradual decline, but complete abandonment. | A metric at 1/2 for three weeks (consistent under-performance but not zero) does not trigger escalation. Acceptable for v1 because the immediate problem is zero-state collapse, not marginal underperformance. Add granular thresholds after 8 weeks of scorecard data reveals whether 1/2 trends precede 0/2 collapses. |

## Integration Points

### Inbound: Diary Entry Arrival

When Sam sends a Telegram message that ClawBoi identifies as a diary entry (existing classification logic), the diary parser skill is invoked. The parser reads the contact reference file, sends the entry text plus reference context to Claude CLI for structured extraction, and writes the resulting signal record to the day's JSON file. If a file already exists for today, fields are merged (last-write-wins for scalars, union for lists). ClawBoi acknowledges the entry with a brief confirmation that includes parsed highlights ("logged: office, gym, saw Hannah — streak day 12").

### Inbound: TGTG Reservation Announcement

When Sam sends a message matching the pattern "reserved TGTG from [place] at [time]", the TGTG skill parses the place and time, computes the reminder time (pickup minus 60 minutes), and writes a pending reminder to the dispatcher state file. A confirmation message is sent immediately ("TGTG from Mesob at 18:00 — reminder set for 17:00"). The purchase is also appended to today's signal file for savings tracking.

### Outbound: Heartbeat-Driven Messages

Every 10 minutes, the heartbeat invokes the dispatcher skill. The dispatcher reads its state file, checks the current time against all fire windows (four anchor points, daily meal prompt, pending TGTG reminders, silence check), and invokes the appropriate skill for each window that matches. Fired messages update the state file to prevent re-firing. All outbound messages route through ClawBoi's Telegram channel adapter — the dispatcher never touches the Telegram API directly.

### Outbound: To Financial Agent

The weekly scorecard includes eating-out spend and TGTG savings data that feeds the financial agent's view of food-category spending. This is a read-only relationship: the financial agent reads the same signal files to pull food spend data. No API, no message passing — shared file access in the same OpenClaw workspace. The routines agent owns the files; the financial agent reads them.

## Failure Modes and Mitigations

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Claude CLI call fails during diary parsing | Entry is received but not parsed — signals lost for that entry | Write raw text to signal file immediately with a "parse-pending" flag. Retry parsing on next heartbeat tick. Raw text is preserved so no data is lost. |
| Heartbeat stops running | No anchor-point messages, no silence detection, no reminders | Heartbeat health is an existing OpenClaw concern, not this system's responsibility. If heartbeat stops, all OpenClaw capabilities degrade equally. No special mitigation needed. |
| Signal file corrupted or deleted | Metrics for that day are lost; silence detector may false-positive | Signal files are append-only during the day and read-only after midnight. Corruption risk is minimal for a single-writer system. If a file is missing, the metrics engine treats it as a no-data day (same as a day Sam did not write a diary entry). |
| Sam changes routines (e.g., gym goal from 2 to 3) | Hardcoded goals produce wrong scorecard | Goals live in the contact reference file, not in skill logic. Sam edits one file to change a goal. The metrics engine reads goals from the file on each run. |
| Telegram message exceeds 4,096 characters | Message delivery fails silently | The scorecard renderer enforces the limit as a hard constraint. If content exceeds the limit, the renderer truncates the detail section (individual friend mentions, daily breakdowns) and appends "full details in Sunday review." Truncation is logged in the dispatcher state file for debugging. |

## Related Documents

- [Analysis](./analysis.md) — Problems, diary patterns, and open questions driving this design
- [Epic](./epic.md) — Scope, task breakdown, success criteria, and explicit exclusions
- [Timeline](./timeline.md) — Task status and delivery tracking