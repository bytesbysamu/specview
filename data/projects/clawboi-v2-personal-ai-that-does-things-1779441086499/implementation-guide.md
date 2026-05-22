# Implementation Guide: ClawBoi v2 — Personal AI That Does Things

## Overview
ClawBoi v2 delivers four new SKILL.md files and one workspace configuration update into the existing OpenClaw runtime, creating a diary-to-action pipeline: freeform Telegram input is processed into structured memory, analyzed for recurring patterns and rationalizations, and converted into dispatchable actions through existing skills like apple-reminders and himalaya. Tasks sequence linearly — diary processing is the foundation (Task 1), pattern detection builds on stored entries (Task 2), reality check layers scoring onto both (Task 3), action dispatch runs in parallel with Task 2 since it only needs diary output (Task 4), and cold-start bootstrap seeds the pattern baseline once detection is ready (Task 5). All work targets the local OpenClaw clone at `/Users/sam/Projects/openclaw/`.

## Shared Pre-flight
- Confirm the OpenClaw repo exists at `/Users/sam/Projects/openclaw/` and the `skills/` directory contains existing skills (e.g., `apple-reminders/SKILL.md`, `himalaya/SKILL.md`)
- Verify at least 15 existing memory entries exist under `/Users/sam/.openclaw/workspace/memory/` in the `2026-*.md` format
- Read `/Users/sam/.openclaw/workspace/SOUL.md` and `/Users/sam/.openclaw/workspace/USER.md` to understand current personality context
- Read 3-5 existing `/Users/sam/.openclaw/workspace/memory/2026-*.md` files to internalize the established memory entry format, field structure, and writing style
- Read 2-3 existing SKILL.md files in `/Users/sam/Projects/openclaw/skills/` (e.g., `apple-reminders/SKILL.md`, `himalaya/SKILL.md`) to internalize the SKILL.md frontmatter format, section structure, and conventions
- Establish a test diary entry text (freeform text with at least one `#win` and one `#struggle` tag) to use as a validation fixture across all tasks

---

## Task 1: Diary Processing Skill  [Effort: 2 days]

### What
Create the SKILL.md that accepts freeform Telegram text and extracts structured fields — mood, events, wins, struggles, and tomorrow's priority — into a memory entry written in the established `2026-*.md` format. This is the entry point for the entire pipeline; every downstream skill depends on diary entries existing in a consistent, parseable shape.

### Files
- **Create**: `/Users/sam/Projects/openclaw/skills/diary-process/SKILL.md` — skill definition declaring input acceptance, extraction fields, optional hashtag handling, and output format targeting the existing memory schema

### Steps
1. Read 2-3 existing SKILL.md files in `/Users/sam/Projects/openclaw/skills/` to understand the exact frontmatter format (`name`, `description`, `metadata.openclaw` with emoji, os, requires fields) and the section conventions (When to Use, When NOT to Use, commands/instructions).
2. Read 5 existing memory entries in `/Users/sam/.openclaw/workspace/memory/` to document the exact heading structure, field order, date-naming convention (`YYYY-MM-DD.md`), and the writing style used in entries.
3. Create `/Users/sam/Projects/openclaw/skills/diary-process/SKILL.md` with proper frontmatter (name: diary-process, emoji: notebook, os: darwin+linux, no binary requirements) and the following sections:
4. Write a "When to Use" section: diary-like/journal-like Telegram messages, personal reflections, day recaps, mood updates, explicit "diary"/"journal"/"log this" triggers.
5. Write a "When NOT to Use" section: commands starting with `/`, questions expecting answers, explicit action requests, technical/project discussions.
6. Write the extraction fields specification: mood (inferred or explicit 1-10), what happened (key events), wins (boosted by `#win` tags), struggles (boosted by `#struggle` tags), tomorrow's priority (if mentioned). Specify that `#win` and `#struggle` tags boost extraction confidence but are stripped from output, and extraction must work without tags.
7. Write the output format specification matching the existing memory entry format observed in step 2. Include the append-not-overwrite rule: if an entry for today exists, append a new timestamped section.
8. Add key constraints: output must be human-readable AND machine-parseable by downstream skills, Telegram confirmation response under 500 characters, filename format `YYYY-MM-DD.md`.

### Verify
- `/Users/sam/Projects/openclaw/skills/diary-process/SKILL.md` exists with valid frontmatter matching the OpenClaw skill format
- The SKILL.md references the memory path `/Users/sam/.openclaw/workspace/memory/`
- The output format section matches the heading structure observed in existing memory entries
- The skill handles both tagged (`#win`, `#struggle`) and untagged freeform input

---

## Task 2: Pattern Detection Skill  [Effort: 3 days]

### What
Create the SKILL.md that reads memory history and surfaces stalled goals, recurring statements, priority drift, and contradictions across entries. This is the longitudinal awareness layer that transforms isolated diary entries into detectable patterns over time, operating in both a fast inline mode and a thorough deep mode.

### Files
- **Create**: `/Users/sam/Projects/openclaw/skills/pattern-detect/SKILL.md` — skill definition declaring dual-mode operation (inline and deep), memory window strategy, stalled-goal detection thresholds, and output format for pattern reports

### Steps
1. Read the existing SKILL.md format conventions (already understood from Task 1 pre-flight).
2. Create `/Users/sam/Projects/openclaw/skills/pattern-detect/SKILL.md` with proper frontmatter (name: pattern-detect, emoji: magnifying glass, os: darwin+linux, no binary requirements).
3. Write the dual operating modes: inline mode scoped to the most recent 14-28 days of entries loaded verbatim, and deep mode that reads the full available memory history triggered by `/reflect`.
4. Write the memory window strategy: inline loads last 14-28 days verbatim; deep loads all but summarizes entries older than 30 days into compressed theme summaries preserving goal mentions, stated priorities, and action commitments while discarding narrative detail.
5. Write the stalled-goal detection heuristic: a goal is flagged when it appears in 3+ entries across 2+ weeks with no corresponding action taken or progress reported. Write the count threshold and time window as tunable parameters directly in the SKILL.md.
6. Write detection categories beyond stalled goals: recurring statements (same phrasing repeated), priority drift (priorities shifting without acknowledgment), and contradictions (current claims conflicting with prior entries). Include concrete examples for each.
7. Write the output format: ranked list of findings, each with category label, evidence trail (which entries by date), and one-line summary. Inline mode: top 2-3 findings under 1500 characters. Deep mode: all findings organized by category.
8. Add the token-budget bail-out heuristic for deep mode and the constraint that inline output must stay under 1500 characters.
9. Add a reference to the baseline file at `/Users/sam/.openclaw/workspace/reference/pattern-baseline.md` — when it exists, compare against it to avoid re-surfacing known patterns.

### Verify
- `/Users/sam/Projects/openclaw/skills/pattern-detect/SKILL.md` exists with valid frontmatter
- The SKILL.md declares both inline and deep modes with clear triggering conditions
- Stalled-goal thresholds are explicitly stated as tunable parameters (3 mentions, 14-day window)
- The memory path references `/Users/sam/.openclaw/workspace/memory/2026-*.md`
- Output format includes evidence trails with entry dates

---

## Task 3: Reality Check Skill  [Effort: 3 days]

### What
Create the SKILL.md that applies calibrated skepticism to the user's reasoning using the BullshitBench judge prompt pattern adapted for personal reflection. Instead of planted falsehoods, this skill anchors on memory-history deltas — contradictions, stalled goals, and rationalizations detected between current and prior entries — scoring each challenged assumption on a 0/1/2 rubric.

### Files
- **Create**: `/Users/sam/Projects/openclaw/skills/reality-check/SKILL.md` — skill definition declaring auto-light and full analysis modes, the five anchor types, scoring rubric, calibration guardrail, and output format
- **Modify**: `/Users/sam/.openclaw/workspace/SOUL.md` — add a "Reflection Voice" section defining the sharp-friend calibration: direct, challenging, but never dismissive of experiences or measurements

### Steps
1. Read `/Users/sam/.openclaw/workspace/SOUL.md` to understand the current personality definition before modifying it.
2. Read `/Users/sam/Projects/specview/api/evals/bullshit_bench/judge.py` lines 48-107 to understand the BullshitBench judge prompt pattern — specifically the scoring rubric, the anchoring on known nonsensical elements, and the calibration between challenging domain claims vs preserving user data.
3. Create `/Users/sam/Projects/openclaw/skills/reality-check/SKILL.md` with proper frontmatter (name: reality-check, emoji: target, os: darwin+linux, no binary requirements).
4. Write the dual operating modes: auto-light runs on every diary entry challenging at most 1-2 assumptions under 800 characters; full mode triggers on `/reflect` scoring all detected assumptions.
5. Write the five anchor types adapted from BullshitBench: wish-vs-plan (repeated without progress), avoidance (planning around bottleneck), contradiction (flip-flopping), feeling-as-fact (strategy on mood), sunk-cost (continuing due to investment not results). Include a detection heuristic for each.
6. Write the scoring rubric: 0 = no rationalization detected, grounded in experience/data; 1 = possible rationalization, worth examining; 2 = clear pattern with supporting evidence from prior entries.
7. Write the calibration guardrail as the most prominent section: experiences, measurements, and external facts are NEVER challengeable; rationalizations, plans, and causal claims are fair game. Provide explicit examples of each category.
8. Write the output format: each challenge includes the assumption text, score, anchor type, referenced prior entry date, and one-line rationale.
9. Add a directive to read `SOUL.md` before every run to maintain tone consistency.
10. Append a "Reflection Voice" section to `/Users/sam/.openclaw/workspace/SOUL.md` defining the sharp-friend persona: challenges reasoning directly, no hedging qualifiers, but respects lived experience and hard data as unchallengeable ground truth.

### Verify
- `/Users/sam/Projects/openclaw/skills/reality-check/SKILL.md` exists with valid frontmatter
- The SKILL.md contains all five anchor types with detection heuristics
- The calibration guardrail section clearly separates challengeable vs unchallengeable claims with examples
- The scoring rubric matches the 0/1/2 pattern from BullshitBench
- `/Users/sam/.openclaw/workspace/SOUL.md` contains a new "Reflection Voice" section
- The skill references SOUL.md for tone calibration

---

## Task 4: Action Dispatch Skill  [Effort: 2 days]

### What
Create the SKILL.md that converts diary reflection output into 1-3 concrete actions routable through existing OpenClaw skills, with mandatory user confirmation before execution. This closes the loop from reflection to action — the core value proposition of the system.

### Files
- **Create**: `/Users/sam/Projects/openclaw/skills/action-dispatch/SKILL.md` — skill definition declaring the action-type-to-skill routing map, proposal format, confirmation protocol, and output constraints

### Steps
1. Read `/Users/sam/Projects/openclaw/skills/apple-reminders/SKILL.md` and `/Users/sam/Projects/openclaw/skills/himalaya/SKILL.md` to understand the target skills' capabilities and invocation patterns.
2. Create `/Users/sam/Projects/openclaw/skills/action-dispatch/SKILL.md` with proper frontmatter (name: action-dispatch, emoji: rocket, os: darwin+linux, no binary requirements).
3. Write the routing map: follow-up reminders and deadlines route to `apple-reminders`; email drafts and sends route to `himalaya`. Note wacli is excluded pending verification, and document how to add it later by editing one line.
4. Write the proposal format: each action includes a natural-language description, target skill name, and key parameters. Maximum 3 proposals per invocation.
5. Write the confirm-before-execute protocol as a non-negotiable constraint: every action requires explicit user confirmation in Telegram before execution. Present as numbered list, user approves with numbers ("1, 2") or "skip".
6. Write the standalone invocation path: explicit action requests ("remind me to...", "draft an email to...") bypass the diary pipeline and route directly to the target skill after confirmation.
7. Add constraints: max 3 proposals, output under 800 characters in diary flow, never execute without confirmation, only route to verified-working skills.

### Verify
- `/Users/sam/Projects/openclaw/skills/action-dispatch/SKILL.md` exists with valid frontmatter
- The routing map lists `apple-reminders` and `himalaya` as targets with examples
- The confirm-before-execute protocol is documented as non-negotiable
- Standalone mode is described for direct action requests
- wacli is explicitly noted as excluded pending verification

---

## Task 5: Cold-Start Bootstrap  [Effort: 1 day]

### What
Create a reference directory and instructions for running a one-time deep-mode pass of the pattern detection skill against the full existing memory corpus to establish a baseline of recurring themes, stalled goals, and contradiction history.

### Files
- **Create**: `/Users/sam/.openclaw/workspace/reference/bootstrap-instructions.md` — instructions for running the one-time pattern detection bootstrap pass and storing the baseline report
- **Create**: `/Users/sam/.openclaw/workspace/reference/.gitkeep` — ensure the reference directory exists

### Steps
1. Create the `/Users/sam/.openclaw/workspace/reference/` directory.
2. List all existing memory entries in `/Users/sam/.openclaw/workspace/memory/` and count them to document the corpus size for the bootstrap.
3. Write `/Users/sam/.openclaw/workspace/reference/bootstrap-instructions.md` containing: (a) the purpose — one-time pass to seed pattern detection baseline, (b) instructions to invoke pattern-detect in deep mode against the full corpus, (c) instructions to save the output as `pattern-baseline.md` in the same reference directory, (d) a header template noting generation date and entry count, (e) a note that this is a one-time artifact that loses relevance as rolling detection accumulates history.
4. Add a note that the baseline file must live outside `memory/` to prevent pattern detection from reading its own output (feedback loop prevention).
5. Verify the reference directory exists and is separate from the memory directory.

### Verify
- `/Users/sam/.openclaw/workspace/reference/` directory exists
- `/Users/sam/.openclaw/workspace/reference/bootstrap-instructions.md` exists with clear step-by-step instructions
- The instructions specify storing output as `pattern-baseline.md` in the reference directory, NOT in memory
- The instructions reference the pattern-detect skill by name
