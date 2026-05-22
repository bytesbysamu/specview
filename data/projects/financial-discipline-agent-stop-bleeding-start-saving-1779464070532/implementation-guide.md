# Implementation Guide: Financial Discipline Agent — Stop Bleeding Start Saving

## Overview
This epic delivers a closed-loop spending feedback system built as five OpenClaw skills that extract spending data from Sam's existing Telegram diary entries, persist it in a lightweight JSON ledger, and push daily and weekly nudges back through Telegram. Tasks sequence linearly at the foundation — diary extraction (Task 1) must ship before the ledger (Task 2), and both must exist before the nudge and scorecard (Tasks 3 and 4, which parallelize). The cooking quick-reference (Task 5) has no dependencies and can be built at any time.

## Shared Pre-flight
- Confirm SSH access to bytesbysamu.cloud VPS and verify OpenClaw is running and Telegram-connected
- Confirm the OpenClaw workspace directory structure and locate where SKILL.md files are deployed
- Verify the OpenClaw CLI can be invoked from cron by running a test skill manually via the CLI
- Confirm cron is available on the VPS and test a one-shot cron entry that invokes an OpenClaw skill
- Collect Sam's Telegram diary entries from January through April 2026 for extraction validation
- Gather the Migros Bank statement summaries for January through April 2026 to use as ground-truth during accuracy testing
- Decide the fixed filesystem path for the spending ledger JSON file within the OpenClaw workspace
- Identify the target Telegram channel or chat ID that OpenClaw will deliver messages to

---

## Task 1: Diary Spending Extraction Skill  [Effort: 3 days]

### What
Build the foundational skill that parses unstructured Telegram diary entries into structured spending records containing CHF amounts, spending categories, and meal-type classifications. This is the load-bearing component — every downstream feature depends on its output. The skill must handle multilingual text (English and German mixed), varied amount formats ("CHF 25", "25.-", "twenty-five francs"), and distinguish between cooked meals (CHF 0 spend with a meal event), ate-out meals, and TooGoodToGo purchases.

### Files
- **Create**: `skills/diary-spending-extraction/SKILL.md` — the SKILL.md file containing extraction instructions, example diary patterns, the six-category taxonomy, and output format specification
- **Create**: `references/budget-constants.md` — reference file holding CHF 75/week eating-out cap, CHF 1,000/month savings target, CHF 2,442 discretionary budget, and other shared constants
- **Create**: `references/bank-validation-data.md` — reference file containing January through April 2026 bank statement summaries used to validate extraction accuracy during development
- **Create**: `data/spending-ledger.jsonl` — empty initial ledger file with the expected top-level structure (an object keyed by ISO date strings)

### Steps
1. Create the budget constants reference file with all shared financial values: the CHF 75 weekly eating-out budget, CHF 1,000 monthly savings target, CHF 2,442 monthly discretionary budget, and CHF 4,049 monthly fixed obligations. These values will be read by multiple skills downstream.
2. Create the bank validation reference file by transcribing the known monthly spending totals and restaurant transaction counts from the January through April 2026 bank statements. Structure the data by month with category-level totals.
3. Design the extraction skill's prompt section to instruct Claude (via the cli provider) on what to extract from diary text: CHF amounts in any format, the six spending categories (food-out, food-grocery, food-tgtg, transport, social, tech, other), and meal-type classification (cooked, ate-out, tgtg). Include five to eight example diary snippets drawn from Sam's actual writing patterns showing varied formats.
4. Define the output schema within the skill: each extraction produces a daily record containing the ISO date, a list of transactions (each with amount, category, and source text), a list of meal events (each with type and optional description), and a daily total. Specify that a diary entry mentioning cooking with no amount produces a cooked-meal event at CHF 0, and a diary entry with no spending mention at all produces a CHF 0 day with no meal events.
5. Implement the append logic: each extraction appends a new line to the JSONL file. No need to read or parse existing content — just append. Multiple entries per day are handled at read time by grouping lines with the same date.
6. Initialize the empty ledger JSONL file at the chosen filesystem path. Each diary extraction appends one JSON object per line (date, transactions, mealEvents) — no merging, no parsing existing content. Aggregation skills read all lines and group by date at read time.
7. Run the extraction skill against a few recent diary entries and compare category assignments to the bank validation reference file. The bank data is for validating that categories are correctly assigned (food-out vs food-grocery, etc.), not for coverage — the extraction only captures what Sam writes in diary entries going forward.
8. Test edge cases: a diary entry with no CHF amounts, a diary entry mentioning only cooking, a diary entry mixing German and English, and a diary entry with multiple transactions in a single sentence.

### Verify
- Run the extraction skill against at least 20 historical diary entries and confirm the output JSON matches the defined schema (date, transactions with amount/category/source, meal events with type)
- Compare extracted category assignments against bank validation data for a sample of transactions and confirm categories are correct
- Confirm that a diary entry mentioning only cooking produces a meal event of type "cooked" with CHF 0 amount and no phantom transactions
- Confirm that processing two diary entries for the same date appends transactions to the existing daily record rather than overwriting it

---

## Task 2: Spending Ledger & Persistence  [Effort: 2 days]

### What
Formalize the spending ledger as the single-file persistent state layer that all downstream skills read from. Define the canonical JSON structure, implement read and write conventions that the extraction skill and reporting skills will follow, and build the derivation functions for weekly totals, monthly totals, cooking streaks, and gamification points. All aggregates are computed at read time from daily records — nothing is cached.

### Files
- **Modify**: `data/spending-ledger.jsonl` — formalize the schema with a documented structure that the extraction skill writes and the reporting skills read
- **Create**: `references/gamification.md` — reference file defining point values per meal type (cooked meal, TooGoodToGo purchase, ate-out penalty), level thresholds and level names, and streak rules
- **Modify**: `skills/diary-spending-extraction/SKILL.md` — update the write section to conform to the finalized ledger schema and reference the gamification constants where relevant

### Steps
1. Document the canonical ledger schema: a JSONL file where each line is a JSON object containing an ISO date string, a transactions array, and a mealEvents array. Multiple lines may share the same date (from multiple diary entries in one day) — aggregation groups by date at read time. Each transaction has amount (number), category (string from the six-value taxonomy), and sourceText (string). Each meal event has type (cooked, ate-out, or tgtg) and an optional description string.
2. Create the gamification reference file with point values for each meal type: positive points for cooked meals and TooGoodToGo purchases, a penalty for ate-out meals exceeding a CHF threshold (defined in the reference). Define four to six level names mapped to weekly point ranges, and document the streak rule — consecutive days with at least one cooked-meal event, resetting to zero on any day without one.
3. Define the derivation logic that the nudge and scorecard skills will follow when reading the ledger: how to compute a weekly total (sum transactions from Monday through Sunday for a given week), a monthly total (sum all transactions in a calendar month), a cooking streak (scan backward from a given date counting consecutive days with at least one cooked meal event), and weekly points (apply the gamification reference values to the current week's meal events).
4. Update the extraction skill to ensure its output conforms exactly to the finalized schema, including field names, types, and the append-on-same-date behavior.
5. Populate the ledger with at least two weeks of historical data by running the extraction skill against diary entries from a recent period. Manually verify three to five daily records against the diary source text to confirm schema conformance.
6. Write a validation check that reads the ledger, computes a weekly total for a known week, and compares it to the bank data to confirm the derivation logic produces correct results.

### Verify
- Open the ledger JSON file and confirm every daily record contains transactions and mealEvents arrays with the correct field names and types
- Manually compute a weekly eating-out total for one known week from the ledger and confirm it matches the expected value from bank data
- Confirm the gamification reference file contains point values, level thresholds with names, and streak rules with no placeholder values
- Run the extraction skill on a new diary entry and confirm the resulting ledger record matches the finalized schema exactly

---

## Task 3: Daily Morning Budget Nudge  [Effort: 2 days]

### What
Build the cron-triggered skill that delivers a proactive Telegram message every morning showing three metrics: cooking streak length, weekly eating-out spend versus the CHF 75 budget, and monthly savings pace. This is the daily accountability signal that makes invisible spending visible before the day's decisions, not after.

### Files
- **Create**: `skills/daily-morning-nudge/SKILL.md` — the SKILL.md file that reads the ledger, computes the three metrics, and formats the Telegram message
- **Modify**: `references/budget-constants.md` — add the morning nudge delivery time constant if not already present
- **Create**: crontab entry on the VPS — a single cron line invoking the OpenClaw CLI with the nudge skill name and target Telegram channel

### Steps
1. Design the nudge skill to read the ledger file and the budget constants reference at invocation time. The skill must not hardcode any financial values — all caps and targets come from the reference file.
2. Implement the cooking streak computation within the skill instructions: scan the ledger backward from yesterday's date, counting consecutive days that contain at least one meal event of type "cooked." Stop counting at the first day with no cooked-meal event or no record at all. A streak of zero is reported honestly.
3. Implement the weekly eating-out budget computation: sum all transactions with category "food-out" from Monday of the current week through yesterday. Subtract from the CHF 75 weekly cap to produce the "remaining this week" figure. If the sum exceeds CHF 75, report the overage amount instead.
4. Implement the monthly savings pace computation: sum all transactions from the first of the current month through yesterday, divide by the number of days elapsed, multiply by the total days in the month to produce a projected monthly spend. Subtract the projected spend from the CHF 2,442 discretionary budget to produce projected savings, and compare against the CHF 1,000 target.
5. Format the message using emoji as section anchors — fire emoji for streak, fork-and-knife emoji for weekly budget, chart emoji for savings pace — with one line per metric. Keep the total message under 500 characters. Use a sharp-friend tone: factual, direct, no guilt. A streak reset gets "streak reset to 0 — cook tonight and start a new one."
6. Test the skill manually by invoking it through the OpenClaw CLI and confirming the Telegram message arrives with correct data.
7. Create the cron entry on the VPS that invokes the OpenClaw CLI with the nudge skill at the configured morning time. Set the cron schedule to run daily, Monday through Sunday.
8. Verify the cron-triggered invocation produces the same output as the manual invocation by letting it fire once and checking the Telegram message.

### Verify
- Invoke the nudge skill manually via the OpenClaw CLI and confirm a Telegram message arrives with all three metrics (streak, weekly budget remaining, savings pace)
- Confirm the message is under 4,096 characters and uses emoji section anchors with no markdown tables
- Verify the cron entry exists on the VPS and is scheduled for the correct morning time daily
- Let the cron fire at least once and confirm the Telegram message matches the manual invocation output

---

## Task 4: Weekly Sunday Scorecard  [Effort: 2 days]

### What
Build the cron-triggered skill that delivers a gamified weekly summary every Sunday morning covering cooking ratio, spending breakdown, points earned, level name, and savings projection. This is the "did I win this week" moment that transforms raw spending data into a progress narrative.

### Files
- **Create**: `skills/weekly-scorecard/SKILL.md` — the SKILL.md file that reads the ledger and gamification reference, computes five sections, and formats the Telegram message
- **Modify**: `references/gamification.md` — confirm level names and point thresholds are finalized and the scorecard skill can reference them
- **Create**: crontab entry on the VPS — a single cron line invoking the OpenClaw CLI with the scorecard skill on Sunday mornings

### Steps
1. Design the scorecard skill to read the full ledger and the gamification reference file. The skill computes metrics for the just-completed Monday-through-Sunday window ending yesterday (Saturday).
2. Implement the cooking ratio section: count the number of days in the week with at least one cooked-meal event versus the number of days with at least one ate-out meal event. Report the ratio and compare it to the previous week's ratio to show directional momentum.
3. Implement the spending breakdown section: compute total food spend for the week split between groceries (food-grocery category), eating out (food-out category), and TooGoodToGo (food-tgtg category). Compare the eating-out subtotal to the CHF 75 weekly cap — weeks under budget get a celebration emoji, weeks over budget get the overage amount stated plainly.
4. Implement the points and level section: apply the point values from the gamification reference to the current week's meal events. Sum the points and map the total to a level name using the thresholds in the reference file. Display the level name and point total.
5. Implement the savings projection section: compute total spending for the month so far, extrapolate to month-end using actual days in the current month, and compare projected savings against the CHF 1,000 target. If projected savings fall below CHF 500, flag as off-pace and state the specific CHF amount to recover in remaining weeks.
6. Format the message with five sections, each getting an emoji header and one data line, plus a one-line summary at top and bottom. Keep total length under 800 characters. Tone matches the daily nudge — factual, celebratory for wins, plainly stated for misses.
7. Test the skill manually by invoking through the OpenClaw CLI with at least one full week of ledger data present. Confirm all five sections render correctly in Telegram.
8. Create the cron entry on the VPS scheduled for Sunday morning, after the typical Saturday diary entry would have been processed. Verify the cron fires and delivers the scorecard to Telegram.

### Verify
- Invoke the scorecard skill manually with at least one full week of data in the ledger and confirm all five sections appear in the Telegram message (cooking ratio, spending breakdown, points/level, savings projection, summary)
- Confirm the scorecard message is under 4,096 characters and contains no markdown tables
- Verify the cron entry is scheduled for Sunday morning on the VPS
- Manually compute the weekly eating-out total and points for a known week and confirm they match the scorecard output

---

## Task 5: Cooking Quick-Reference Skill  [Effort: 1 day]

### What
Build the reactive skill that responds when Sam asks "what should I cook" or "dinner ideas" in Telegram, presenting a single meal suggestion with estimated cost and time from a curated list of ten cheap meals. This removes the "what do I even cook" friction that defaults to eating out.

### Files
- **Create**: `references/meal-rotation.md` — reference file containing ten curated meals, each with name, estimated cost per serving (at or below CHF 8), approximate active cooking time (at or below 20 minutes), a one-line description, and whether it produces leftovers suitable for next-day lunch
- **Create**: `skills/cooking-quick-reference/SKILL.md` — the SKILL.md file that reads the meal rotation reference, checks recent cooking history in the ledger, and suggests a meal

### Steps
1. Curate the meal rotation list of ten meals optimized for Sam's constraints: each meal must cost CHF 8 or less per serving, require no more than 20 minutes of active cooking, use ingredients available at Migros or Coop, and ideally produce leftovers. Include a mix of cuisines and protein sources for variety. Write each entry with the meal name, cost estimate, time estimate, one-line description, and a leftover suitability flag.
2. Create the meal rotation reference file with all ten meals in a structured format that the skill can parse — use a consistent heading-per-meal layout with the fields on labeled lines beneath each heading.
3. Design the cooking quick-reference skill to activate on natural-language cooking questions ("what should I cook," "dinner ideas," "meal suggestion," "was soll ich kochen"). The skill reads the meal rotation reference and the spending ledger.
4. Implement the selection logic in the skill instructions: read the ledger for the last three days and check if any meal event descriptions match meals in the rotation list. Exclude matched meals from the suggestion pool to avoid repetition. If no recent cooking data exists or no descriptions match, select at random from the full list.
5. Format the response as a single meal suggestion: the meal name, estimated cost, estimated time, the one-line description, and whether it makes good leftovers. Keep the message under 300 characters. No list of alternatives — one suggestion reduces decision fatigue.
6. Test the skill by invoking it through the OpenClaw CLI with various trigger phrases and confirming a meal suggestion arrives in Telegram with all fields present.

### Verify
- Invoke the skill with "what should I cook" via the OpenClaw CLI and confirm a single meal suggestion appears in Telegram with name, cost, time, and description
- Confirm the meal rotation reference file contains exactly ten meals, each at or below CHF 8 per serving
- Invoke the skill three times in sequence and confirm it does not suggest the same meal consecutively when recent cooking history contains meal descriptions
- Confirm the skill responds to both English ("what should I cook") and German ("was soll ich kochen") trigger phrases