# Implementation Guide: Life Routines Agent — Non-Negotiable Weekly Structure

## Overview
This epic delivers a personal operating-system layer that enforces five weekly routine commitments (office attendance, friend meetups, gym, family contact, room tidiness) plus cooking/meal tracking and TGTG savings — all derived from free-text Telegram diary entries Sam already writes, nudged by four proactive anchor-point messages, and escalated when diary silence sets in. The work sequences as a pipeline: Task 1 builds the diary parser that every downstream component depends on; Tasks 2 and 4 run in parallel to create the metrics engine and silence detector respectively; Task 3 wires up the heartbeat dispatcher and scorecard renderer that deliver the four anchor-point messages; and Task 5 layers on the manual TGTG reserve-and-remind flow last.

## Shared Pre-flight
- Confirm the OpenClaw workspace is running and the 10-minute heartbeat is active by checking heartbeat logs for recent ticks.
- Verify ClawBoi's Telegram channel adapter can send outbound messages — send a test nudge and confirm delivery.
- Confirm the existing diary-entry classification logic in ClawBoi correctly tags inbound Telegram messages as diary entries.
- Create the data directory for routine signal files at workspace/data/routines/signals/ and verify write permissions.
- Create the contact reference file at workspace/reference/routines-config.md containing the 14-person contact list with canonical names, known aliases, Lea's exclusion flag, exercise keyword list, mood-word-to-score mapping, TGTG day pattern (default Tuesday/Thursday), weekly goal thresholds, and escalation tier day counts (2/3/7).
- Verify Claude CLI is accessible through OpenClaw's chain adapter by sending a test structured-extraction prompt and confirming JSON output.
- Establish the convention that each skill is a standalone SKILL.md file under the skills/ directory, staying under 200 lines, with no skill importing or duplicating logic from another.

---

## Task 1: Diary Entry Parser for Routine Signals  [Effort: 3 days]

### What
Build the skill that converts free-text diary entries of any length — from a single emoji to a 500-word reflection — into a structured JSON signal record. This is the foundational component: every metric, scorecard, and escalation downstream depends on reliable signal extraction from natural language.

### Files
- **Create**: skills/routines-diary-parser/SKILL.md — skill definition that receives raw diary text, reads the contact reference file, invokes Claude CLI for structured extraction, and writes the resulting signal record to the daily JSON file.
- **Create**: workspace/data/routines/signals/.gitkeep — placeholder to establish the signal storage directory.
- **Modify**: workspace/reference/routines-config.md — populate with the 14-person contact list (canonical names, aliases like "Adi"/"Adrian"), exercise keywords (gym, workout, run, walk, swim, dance, padel, yoga, hike), mood mappings (numeric, emoji, descriptive words), and Lea's exclusion flag.

### Steps
1. Define the signal file JSON schema with nullable fields: mood (1-10 integer), office status (office/wfh/null), exercise list (array of activity-type strings), friends seen (array of matched contact names), family contact (boolean), meals cooked (integer), eating-out spend (decimal CHF), tgtg purchases (array of price entries), streak-alive flag (boolean), and raw text (original diary input preserved for re-parsing).

2. Write the Claude CLI system prompt inside the skill that instructs the model to extract structured signals from diary text. The prompt must include the full contact reference data (names, aliases, exercise keywords, mood mappings) as grounding context so the model matches against known names rather than hallucinating.

3. Implement the parsing flow in the skill: receive the diary message text, read workspace/reference/routines-config.md for the contact list and keyword configuration, send the text plus reference context to Claude CLI via OpenClaw's chain adapter, and validate the returned JSON against the signal schema.

4. Implement the daily file merge logic. If workspace/data/routines/signals/{ISO-date}.json already exists, merge the new parse result using last-write-wins for scalar fields (mood, office status) and union for list fields (friends, exercises). If no file exists, create a new one.

5. Handle the minimal-input case: an entry like "7/10" or a thumbs-up emoji must produce a valid signal record with mood populated and streak-alive set to true, with all other fields null. Ensure the parser never infers missing fields — a missing friend mention means an empty list, not a guess.

6. Implement name matching against the contact reference, resolving aliases to canonical names. Lea must appear in the emitted signal when mentioned (the exclusion happens downstream in the metrics engine, not here).

7. Add the parse-pending fallback: if the Claude CLI call fails, write the raw diary text to the signal file with a parse-pending flag set to true, so data is never lost and the next heartbeat tick can retry.

8. Wire the skill into ClawBoi's diary-entry classification hook so that when an inbound Telegram message is tagged as a diary entry, this skill is invoked automatically. Have ClawBoi return a brief confirmation including parsed highlights (e.g., "logged: office, gym, saw Hannah — streak day 12").

### Verify
- Send five test diary entries spanning the input spectrum: a full narrative, a one-liner ("7/10, cooked, gym, saw Hannah"), an emoji-only ("thumbs-up"), a mood-only ("shit day"), and a multi-friend mention ("dinner with Adi and Fabienne") — confirm each produces a valid signal file in workspace/data/routines/signals/ with correct field extraction.
- Confirm that sending two diary messages on the same day merges correctly: scalar fields reflect the latest value, list fields contain the union of both entries.
- Verify that a mention of Lea appears in the signal file's friends-seen list (exclusion is not the parser's job).
- Simulate a Claude CLI failure and confirm the raw text is written to the signal file with parse-pending set to true.

---

## Task 2: Weekly Metrics Engine & Scorecard  [Effort: 2 days]

### What
Aggregate parsed diary signals into the five core weekly metrics plus cooking frequency and eating-out spend, compare each against its goal threshold, compute at-risk/met/missed status based on the day of the week, and detect multi-week trend failures. This engine produces the metrics snapshot that the scorecard renderer and anchor-point messages consume.

### Files
- **Create**: skills/routines-metrics-engine/SKILL.md — skill that reads a week's worth of signal files, applies goal comparisons from the reference file, computes metric statuses, and outputs a structured metrics snapshot.
- **Create**: skills/routines-scorecard-renderer/SKILL.md — skill that takes a metrics snapshot and formats it into a Telegram-safe UTF-8 string under 4,096 characters, with four message variants (Monday preview, Wednesday check, Friday planning, Sunday full scorecard).

### Steps
1. Implement the weekly aggregation function in the metrics engine skill. It reads all signal files for the current ISO week (Monday through Sunday) from workspace/data/routines/signals/, counts office days, unique friends seen (excluding Lea by checking her exclusion flag in workspace/reference/routines-config.md), exercise sessions, family contact occurrences, cooking count, and sums eating-out spend.

2. Implement the goal comparison logic. Read weekly goal thresholds from workspace/reference/routines-config.md (office 2-3, friends 2, gym 2, cooking 5, eating-out under CHF 75). For each metric, compute a status: met (goal reached), at-risk (goal reachable given remaining days in the week), or missed (goal unreachable given remaining days). The at-risk calculation must be day-of-week-aware — gym at zero on Wednesday is at-risk, gym at zero on Saturday is missed.

3. Implement the family contact rolling-window check. Family contact uses a 14-day rolling window, not a calendar week. The engine scans signal files across the last 14 days for any family or Yoseph mention and reports days-since-last-contact.

4. Implement trend detection over a rolling 3-week window. If any metric is at zero for three consecutive weeks, flag it for escalated language in the scorecard. Read the prior two weeks' signal files to compute this.

5. Data flow between engine and renderer: the metrics engine writes its snapshot to `workspace/data/routines/current-metrics.json`. The scorecard renderer reads this file. No skill-to-skill imports — they communicate through the filesystem. The dispatcher invokes the engine first, then the renderer.

6. Build the scorecard renderer skill with four message variants. The Monday preview is forward-looking (goals for this week, gaps carried from last week, friend and family suggestions). The Wednesday check shows current progress counts plus a room-tidy prompt. The Friday message is planning-oriented (weekend suggestions, family visit prompt if the gap exceeds 10 days). The Sunday scorecard is the full gamified report with all seven metrics, emoji status indicators, week-over-week trend arrows, and a streak counter for consecutive weeks with all five core metrics met.

6. Enforce the Telegram 4,096-character limit as a hard constraint in the renderer. If content exceeds the limit, truncate the detail section (individual friend mentions, daily breakdowns) and append a note that full details are in the Sunday review. Log truncation events for debugging.

### Verify
- Populate workspace/data/routines/signals/ with seven synthetic signal files representing a full week with known values, then invoke the metrics engine and confirm the snapshot matches expected counts, statuses, and goal comparisons.
- Test the at-risk calculation by running the engine on a Wednesday with gym at zero — confirm status is at-risk — then on a Saturday with gym at zero — confirm status is missed.
- Generate a Sunday scorecard from the synthetic data and confirm the output is valid UTF-8 under 4,096 characters, contains emoji status indicators, and shows trend arrows.
- Confirm Lea is excluded from the friend count in the metrics snapshot even though she appears in signal files.

---

## Task 3: Four Anchor-Point Message Dispatch  [Effort: 3 days]

### What
Deliver proactive Telegram messages at the four weekly anchor points (Monday 7 AM, Wednesday 8 PM, Friday 6 PM, Sunday 9 PM) plus a daily 5 PM meal-planning prompt, all triggered by the existing 10-minute heartbeat. The dispatcher is the scheduling brain that evaluates time windows and invokes the correct skills without generating message content itself.

### Files
- **Create**: skills/routines-heartbeat-dispatcher/SKILL.md — skill invoked on each heartbeat tick that evaluates time-window rules, checks last-fired timestamps, and delegates to the appropriate skill when a window matches.
- **Create**: workspace/data/routines/dispatcher-state.json — state file tracking last-fired timestamp per anchor point, current silence streak count, and pending TGTG reminders.

### Steps
1. Define the five fire windows in the dispatcher skill: Monday 7:00-7:30 AM (weekly preview), Wednesday 8:00-8:30 PM (midweek check), Friday 6:00-6:30 PM (weekend planning), Sunday 9:00-9:30 PM (weekly review), and daily 5:00-5:30 PM (meal prompt). Each 30-minute window accommodates three heartbeat ticks to absorb clock drift.

2. Implement the double-fire prevention logic. On each heartbeat tick, the dispatcher reads workspace/data/routines/dispatcher-state.json and checks two conditions for each window: is the current time inside the window, AND is the last-fired timestamp for that anchor point outside the window? Only fire if both conditions hold. After successful delivery, write the current timestamp to the state file.

3. Wire each anchor-point window to its corresponding skill invocation. Monday invokes the scorecard renderer's preview variant, Wednesday invokes the check variant plus a room-tidy prompt, Friday invokes the planning variant, and Sunday invokes the full scorecard variant. The daily 5 PM window invokes a meal prompt that offers cook-or-TGTG framing.

4. Implement the meal prompt logic for the daily 5 PM window. The prompt asks Sam whether tonight is a cook night or a TGTG night, using a lightweight framing that tracks cooking frequency against the 5x/week goal. Check whether a meal prompt was already sent today before firing. If Sam replies "cook", invoke the existing `cooking-quick-reference` skill to suggest a meal from the 10-meal rotation.

5. Register the dispatcher skill with the OpenClaw heartbeat so it is invoked automatically on every 10-minute tick. Ensure the dispatcher reads the current time in the correct timezone (Europe/Zurich) for all window comparisons.

6. Route all outbound messages through ClawBoi's Telegram channel adapter. The dispatcher never constructs Telegram API calls directly — it produces a message payload and delegates delivery.

### Verify
- Set the system clock (or mock the time check) to fall within the Monday 7:00-7:30 AM window and trigger a heartbeat tick — confirm the weekly preview message is delivered via Telegram.
- Trigger three consecutive heartbeat ticks within the same 30-minute window and confirm that only one message is sent (double-fire prevention works).
- Confirm workspace/data/routines/dispatcher-state.json is updated with the correct last-fired timestamp after each delivery.
- Trigger the daily 5 PM meal prompt and confirm it arrives with cook-or-TGTG framing.

---

## Task 4: Silence Detection & Escalation Ladder  [Effort: 1 day]

### What
Detect diary entry gaps by checking for missing daily signal files and escalate through four graduated tiers — grace (day 1), gentle ping (day 2), direct prompt (day 3), blunt intervention (day 7) — to maintain the diary habit without being punitive. This runs on the same heartbeat as the anchor-point dispatcher.

### Files
- **Modify**: skills/routines-heartbeat-dispatcher/SKILL.md — add silence-detection logic that runs on each tick after 9 PM, checking for missing signal files and determining the current escalation tier.
- **Create**: skills/routines-silence-escalation/SKILL.md — skill containing the four escalation message templates, invoked by the dispatcher with the current tier as input.

### Steps
1. Add silence-check logic to the heartbeat dispatcher. After 9 PM on each tick, check whether a signal file exists for yesterday in workspace/data/routines/signals/. Use file existence as the diary-gap signal — no separate "last entry" timestamp needed.

2. Implement the streak counter in the dispatcher. When yesterday's file is missing, increment the silence streak count in workspace/data/routines/dispatcher-state.json. When any signal file is written (even a minimal "thumbs-up" entry), reset the streak to zero. The streak-alive flag in the signal file is the trigger — any entry, no matter how sparse, resets the counter.

3. Map streak count to escalation tier: day 1 is grace (no message sent), day 2 fires the gentle 9 PM ping, day 3 fires the direct prompt that names the pattern ("no diary in 3 days — what's happening?"), and day 7 fires the blunt intervention. Read tier thresholds from workspace/reference/routines-config.md so they are configurable.

4. Build the four escalation message templates in the silence-escalation skill. The gentle ping is warm and brief. The direct prompt references the specific gap duration. The blunt intervention is confrontational and references the historical pattern of abandonment. The grace tier produces no output.

5. Add acknowledgment tracking: if Sam responds to an anchor-point message, note the response in the dispatcher state. If anchor-point messages go unacknowledged for two consecutive cycles while diary entries also stop, the system treats this as full disengagement and escalates one tier faster.

### Verify
- Remove yesterday's signal file and trigger a heartbeat tick after 9 PM — confirm no message is sent (day 1 grace).
- Remove signal files for the last two days and trigger a tick — confirm the gentle ping is delivered.
- Remove signal files for the last three days and trigger a tick — confirm the direct prompt is delivered and references the 3-day gap.
- Write a minimal signal file ("thumbs-up" entry) and confirm the silence streak resets to zero in workspace/data/routines/dispatcher-state.json.

---

## Task 5: Manual TGTG Reserve-and-Remind Flow  [Effort: 2 days]

### What
Accept manual TGTG reservation announcements from Sam (e.g., "reserved TGTG from Mesob at 18:00"), set a pickup reminder one hour before the window, deliver morning reserve prompts on designated TGTG days, and track purchase savings for the Sunday scorecard. No API integration — app checking is manual, reminders are automated.

### Files
- **Create**: skills/routines-tgtg-reminder/SKILL.md — skill that parses reservation messages, writes pending reminders to the dispatcher state file, handles savings tracking, and generates the 8 AM reserve prompt on TGTG days.
- **Modify**: skills/routines-heartbeat-dispatcher/SKILL.md — add a check for pending TGTG reminders on each tick and fire them when the reminder time is reached. Add an 8:00-8:30 AM window on configured TGTG days for the morning reserve prompt.
- **Modify**: workspace/reference/routines-config.md — add the TGTG day pattern (default: Tuesday and Thursday) as a configurable field.

### Steps
1. Build the reservation parser in the TGTG skill. When Sam sends a message matching the pattern "reserved TGTG from {place} at {time}", extract the place name and pickup time, compute the reminder time as pickup minus 60 minutes, and write a pending-reminder record (place, pickup time, reminder time) to workspace/data/routines/dispatcher-state.json. Send an immediate confirmation via ClawBoi ("TGTG from Mesob at 18:00 — reminder set for 17:00").

2. Wire the pending-reminder check into the heartbeat dispatcher. On each tick, the dispatcher reads pending reminders from the state file, fires any reminder whose reminder time has passed, and removes it from the pending list. The reminder message includes the place name and pickup time.

3. Add the 8 AM morning reserve prompt. Read the TGTG day pattern from workspace/reference/routines-config.md (default Tuesday and Thursday). On those days, fire a message during the 8:00-8:30 AM window prompting Sam to check the TGTG app and reserve a bag before work.

4. Implement savings tracking. When a reservation is logged, append the bag price to today's signal file in the tgtg-purchases array. Estimate retail value at 3x the bag price and compute savings per purchase. The metrics engine already reads signal files, so the Sunday scorecard will pick up cumulative monthly TGTG savings automatically.

5. Allow Sam to override the TGTG day pattern by telling ClawBoi to change TGTG days. The skill updates workspace/reference/routines-config.md with the new pattern, and the dispatcher uses the updated schedule on the next tick.

### Verify
- Send "reserved TGTG from Mesob at 18:00" and confirm a pending reminder appears in workspace/data/routines/dispatcher-state.json with the correct reminder time of 17:00, and that an immediate confirmation message is sent.
- Trigger a heartbeat tick at 17:05 and confirm the reminder fires with the place name and pickup time, then confirm the reminder is removed from the state file.
- Trigger a heartbeat tick on a configured TGTG day during the 8:00-8:30 AM window and confirm the morning reserve prompt is delivered.
- Log a TGTG purchase at CHF 5.90 and confirm the signal file contains the entry with estimated retail value of CHF 17.70 and savings of CHF 11.80.