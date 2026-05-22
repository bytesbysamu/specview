# Implementation Guide: ClawBoi v2 Phase 2 — Unfair Advantage Expansion

## Overview
This epic extends the Phase 1 diary-processing agent into a multi-domain life optimization system covering job intelligence, application automation, social graph management, and expense awareness. Task 1 lays the foundation by updating workspace configuration and defining the memory directory structure. Tasks 2, 4, and 5 can then proceed in parallel since they each build independent domain skills on top of that foundation. Task 3 depends on Task 2 because the application workflow consumes output from the job intelligence pipeline. All capabilities share two interaction patterns — passive extraction from diary entries and proactive nudging via heartbeat — plus a shared approval gate for any external side effects.

## Shared Pre-flight
- Confirm the VPS has Claude CLI operational and the existing Phase 1 skills (diary-process, pattern-detect, action-dispatch) are functioning correctly
- Verify himalaya is configured and can send email from the command line
- Verify Telegram bot integration is working for both inbound messages and outbound notifications
- Confirm the OpenClaw workspace root is accessible and contains the existing SOUL.md, AGENTS.md, USER.md, and IDENTITY.md files
- Ensure the heartbeat skill exists and runs on its configured interval
- Check that the base CV document exists or create a placeholder at memory/jobs/base-cv.md before starting Task 3
- Confirm RSS feed URLs are reachable from the VPS: test fetching SwissDevJobs and Indeed Switzerland RSS endpoints
- Review the existing diary-process skill to understand its current segment handling before extending it in Tasks 2, 4, and 5

---

## Task 1: Workspace & Memory Foundation  [Effort: 1 day]

### What
This task updates the core workspace configuration files to reflect the expanded agent role and creates the partitioned memory directory structure that all subsequent tasks depend on. Without this foundation, new skills cannot be discovered, routed, or persisted correctly.

### Files
- **Modify**: SOUL.md — expand the agent's role definition to include job intelligence, social graph management, and expense awareness alongside the existing diary-processing capabilities
- **Modify**: AGENTS.md — add skill routing entries for job-monitor, apply-workflow, contact-extract, expense-extract, and their associated heartbeat checks
- **Modify**: USER.md — update to reflect the full optimization picture including active job search posture, discretion constraints, and financial awareness goals
- **Modify**: IDENTITY.md — align identity description with the expanded multi-domain optimization role
- **Create**: memory/jobs/pipeline.md — empty pipeline tracker with section headers for applied, interview, and outcome stages
- **Create**: memory/jobs/seen.md — empty deduplication log for previously encountered job postings
- **Create**: memory/jobs/profile-match.md — reference file encoding Sam's job criteria: tech stack (Python, Flask, Angular, TypeScript), domain preference (finance), location (Zürich), and compensation floor (CHF 115k)
- **Create**: memory/contacts/contacts.md — empty contact store with section structure for name, context, date met, birthday, last contact date, and priority tier
- **Create**: memory/finance/categories.md — reference file defining expense categories: dining out, groceries, transport, subscriptions, entertainment, other

### Steps
1. Read the existing SOUL.md and append a new section describing the Phase 2 capabilities — job intelligence, social graph, and expense awareness — positioning them as extensions of the diary-driven insight loop rather than standalone features.
2. Open AGENTS.md and add routing entries for each new skill. Each entry should specify the skill name, the trigger conditions that cause the diary router to dispatch to it, and the memory partition it reads from and writes to.
3. Update USER.md to include Sam's job search context: currently employed, discretion required, target role parameters matching the profile-match reference file, and the goal of passive monitoring rather than active signaling.
4. Update IDENTITY.md to describe the agent as a life optimization system that acts on insights rather than merely surfacing them, while retaining the existing diary-processing identity.
5. Create the memory directory tree by establishing the three subdirectories: memory/jobs/, memory/contacts/, and memory/finance/.
6. Create the profile-match reference file at memory/jobs/profile-match.md with Sam's concrete criteria: primary tech stack, preferred domains, location constraint, and minimum compensation.
7. Create the pipeline tracker at memory/jobs/pipeline.md with empty sections for each stage and a convention for recording timestamps on state transitions.
8. Create the deduplication log at memory/jobs/seen.md with a header explaining its format: one line per posting with source, title, and date first seen.
9. Create the contact store at memory/contacts/contacts.md with the per-contact section structure and an empty top-20 priority section that Sam will manually curate.
10. Create the expense categories reference file at memory/finance/categories.md listing all six categories with brief descriptions of what each includes.

### Verify
- Confirm all four configuration files (SOUL.md, AGENTS.md, USER.md, IDENTITY.md) contain Phase 2 content and are parseable by Claude CLI
- Confirm the directory tree memory/jobs/, memory/contacts/, and memory/finance/ exists with all reference and tracker files in place
- Run the existing diary-process skill with a test entry to confirm Phase 1 functionality is not broken by the configuration changes
- Verify that AGENTS.md lists routing entries for all five new skills: job-monitor, apply-workflow, contact-extract, expense-extract, and the heartbeat extensions

---

## Task 2: Job Intelligence Pipeline  [Effort: 3 days]

### What
This task builds the passive job monitoring pipeline that ingests Swiss job postings from RSS feeds, scores them against Sam's profile, deduplicates against previously seen postings, and delivers a ranked top-5 weekly digest to Telegram. This is the data source that the entire application workflow in Task 3 depends on.

### Files
- **Create**: skills/job-monitor/SKILL.md — main job monitoring skill that orchestrates the ingest-score-digest pipeline
- **Create**: skills/job-monitor/ingest.md — RSS fetch and parse logic for SwissDevJobs and Indeed Switzerland feeds
- **Create**: skills/job-monitor/score.md — profile-match scoring skill that reads memory/jobs/profile-match.md and computes composite fit scores
- **Create**: skills/job-monitor/digest.md — weekly digest formatter that selects top-5 roles and composes a Telegram-friendly summary under 4096 characters
- **Modify**: memory/jobs/seen.md — will be written to by the deduplication step during each ingestion run
- **Create**: memory/jobs/raw/ — directory for dated raw ingestion result files
- **Modify**: AGENTS.md — add heartbeat check entry for new-job-match detection

### Steps
1. Build the ingest skill at skills/job-monitor/ingest.md. It should fetch RSS feeds from SwissDevJobs and Indeed Switzerland, parse each entry into a structured format (title, company, location, tech stack keywords, posting URL, date posted), and write the results to a dated file in memory/jobs/raw/.
2. Add deduplication logic to the ingest skill: before writing a new result, check the posting URL against memory/jobs/seen.md. If already present, skip it. If new, append it to seen.md and include it in the raw output file.
3. Implement graceful error handling in the ingest skill so that if one feed is unreachable or returns malformed data, the skill logs the error in the raw file and continues processing the other feed rather than failing entirely.
4. Build the scoring skill at skills/job-monitor/score.md. It should read the latest raw file from memory/jobs/raw/ and the profile-match reference from memory/jobs/profile-match.md, then compute a composite fit score for each posting based on tech stack overlap, domain relevance, location match, and compensation alignment where available.
5. Build the digest skill at skills/job-monitor/digest.md. It should take the scored results, select the top five by composite score, and format a compressed Telegram message: rank, job title, company, fit score, and a one-line rationale for each entry. Link to the full scored results file for detailed breakdowns.
6. Create the orchestrating SKILL.md at skills/job-monitor/SKILL.md that chains ingest, score, and digest in sequence and is designed to be triggered on a weekly schedule.
7. Add a heartbeat extension in AGENTS.md that checks whether scored results exist in memory/jobs/raw/ that have not yet been included in a digest delivery, so the heartbeat can flag undelivered matches between weekly runs.
8. Test the full pipeline end-to-end by triggering the job-monitor skill manually and confirming that a digest message arrives in Telegram with five ranked entries.

### Verify
- Trigger the job-monitor skill and confirm that memory/jobs/raw/ contains a dated file with parsed job postings from at least two sources
- Confirm that memory/jobs/seen.md has been updated with the URLs of the fetched postings
- Verify the Telegram digest message contains exactly five entries, each with a title, company, fit score, and rationale, and that the total message is under 4096 characters
- Run the ingest skill a second time and confirm that previously seen postings are not duplicated in the new raw file

---

## Task 3: Application Workflow  [Effort: 2 days]

### What
This task builds the sequential skill chain that takes a shortlisted role from the weekly digest through CV tailoring, cover letter drafting, approval gating, email dispatch via himalaya, and pipeline state tracking. Every external action requires explicit Telegram approval before execution.

### Files
- **Create**: skills/apply-workflow/SKILL.md — orchestrating skill that chains the full application sequence
- **Create**: skills/apply-workflow/tailor-cv.md — CV emphasis-tailoring skill that reads memory/jobs/base-cv.md and adjusts section ordering and keyword emphasis per role
- **Create**: skills/apply-workflow/draft-cover.md — cover letter drafting skill with tone matching based on company size and industry
- **Create**: skills/apply-workflow/send-application.md — approval gate and himalaya dispatch skill
- **Create**: skills/apply-workflow/tone-reference.md — reference file defining three tone templates: formal, balanced, and casual, with mapping rules from company attributes
- **Create**: memory/jobs/base-cv.md — Sam's base CV document that the tailoring skill works against
- **Modify**: memory/jobs/pipeline.md — updated by the send skill to record each state transition with timestamp

### Steps
1. Create the CV tailoring skill at skills/apply-workflow/tailor-cv.md. It should accept a role identifier from the digest, read the base CV from memory/jobs/base-cv.md, and produce a tailored version that reorders experience sections and promotes relevant bullet points based on the role's tech stack and domain. It must not fabricate experience or skills — only adjust emphasis and ordering.
2. Create the tone reference file at skills/apply-workflow/tone-reference.md defining three templates (formal for large financial institutions, balanced for mid-size companies, casual for startups) with concrete language guidelines for each.
3. Build the cover letter drafting skill at skills/apply-workflow/draft-cover.md. It should read the role description and company context from the scored results, classify the company into one of the three tone categories using the tone reference, and draft a cover letter that matches the appropriate register.
4. Build the approval gate and dispatch skill at skills/apply-workflow/send-application.md. It should present the complete application package in Telegram — tailored CV summary, full cover letter text, recipient email address, and subject line — then wait for Sam's explicit approval or rejection. Only on approval should it invoke himalaya to send the email.
5. Add pipeline state tracking to the dispatch skill: on successful send, append an entry to memory/jobs/pipeline.md with the role title, company, date applied, and current stage set to "applied." On rejection, record the role as "declined" with the reason.
6. Create the orchestrating SKILL.md at skills/apply-workflow/SKILL.md that chains the four steps in sequence: select role, tailor CV, draft cover letter, approve and send. Allow re-entry at any step so Sam can redraft a cover letter without re-tailoring the CV.
7. Connect the existing pattern-detect skill from Phase 1 to the pipeline data: add a pipeline-pattern check that flags ghosting (no response 14+ days after application) and suggests follow-up timing.
8. Populate memory/jobs/base-cv.md with Sam's current CV content, structured with clearly delimited sections that the tailoring skill can reorder.

### Verify
- Walk through the full chain with a test role: select from digest, generate tailored CV, draft cover letter, present for approval in Telegram, and confirm the approval prompt contains all required fields (CV summary, letter text, recipient, subject)
- Reject the test application and confirm that memory/jobs/pipeline.md records the role as "declined"
- Approve a test application and confirm that himalaya dispatches the email and memory/jobs/pipeline.md records the role as "applied" with a timestamp
- Verify that querying "what's my application status?" returns accurate pipeline data from memory/jobs/pipeline.md

---

## Task 4: Social Graph & Follow-ups  [Effort: 2 days]

### What
This task builds the contact extraction pipeline and relationship maintenance system. Diary entries mentioning people are automatically parsed into the contact store, and the heartbeat generates follow-up reminders, birthday alerts, and network warming nudges based on date thresholds.

### Files
- **Create**: skills/social-graph/SKILL.md — orchestrating skill for contact management queries and manual operations
- **Create**: skills/social-graph/contact-extract.md — diary-to-contact extraction skill that parses "met someone" segments into structured contact entries
- **Create**: skills/social-graph/reminders.md — heartbeat check skill that scans the contact store for overdue follow-ups, upcoming birthdays, and stale top-20 contacts
- **Modify**: memory/contacts/contacts.md — written to by the extraction skill and read by the reminders skill
- **Modify**: skills/diary-process/SKILL.md — extend the diary router to classify "met someone" segments and dispatch to contact-extract
- **Modify**: AGENTS.md — add heartbeat check entries for follow-up reminders, birthday alerts, and network warming nudges

### Steps
1. Extend the diary-process skill to recognize "met someone" segments in diary entries. Add classification logic that identifies mentions of new people, social interactions, or professional meetings and dispatches those segments to the contact-extract skill.
2. Build the contact-extract skill at skills/social-graph/contact-extract.md. It should parse dispatched segments to extract the person's name, the context of the meeting, and the date. It should then check memory/contacts/contacts.md for an existing entry — if found, update the last contact date; if new, append a new section with all available fields.
3. Define the contact section format in the extraction skill: name, context of meeting, date met, birthday (if mentioned, otherwise blank), last contact date, and priority tier (default to "standard" — Sam manually promotes to top-20).
4. Build the reminders skill at skills/social-graph/reminders.md with three check types. Follow-up reminders fire 3–5 days after the date met for any new contact. Birthday alerts fire the day before a known birthday. Network warming nudges fire when a top-20 contact's last contact date exceeds 30 days.
5. Each reminder check is a date comparison against today's date — no scheduling system, no persistent timers. The skill reads memory/contacts/contacts.md, iterates through entries, and collects all triggered reminders into a single Telegram notification.
6. Register the three reminder check types in AGENTS.md as heartbeat extensions so they run on every heartbeat sweep.
7. Create the orchestrating SKILL.md at skills/social-graph/SKILL.md to handle manual queries like "who should I follow up with?" or "show my contact list" by reading and summarizing the contact store.
8. Test the full flow: process a diary entry that mentions meeting someone new, confirm the contact appears in the store, then advance the system date context to 4 days later and confirm the follow-up reminder fires.

### Verify
- Submit a diary entry mentioning a new contact and confirm that memory/contacts/contacts.md contains a new entry with the correct name, context, and date
- Submit a second diary entry mentioning the same person and confirm the existing entry's last contact date is updated rather than a duplicate being created
- Verify that the heartbeat produces a follow-up reminder in Telegram for a contact whose date met is 3–5 days ago
- Manually add a birthday to a contact entry and confirm that a birthday alert fires in Telegram the day before

---

## Task 5: Expense Awareness  [Effort: 1 day]

### What
This task builds diary-based expense extraction and monthly trend analysis. Spending mentions in diary entries are parsed into monthly ledger files, and a summary skill computes category totals with month-over-month comparison, alerting via Telegram when any category exceeds the prior month by 20% or more.

### Files
- **Create**: skills/expense-tracker/SKILL.md — orchestrating skill for expense queries and monthly summary generation
- **Create**: skills/expense-tracker/expense-extract.md — diary-to-expense extraction skill that parses spending mentions into structured entries
- **Create**: skills/expense-tracker/monthly-summary.md — summary and trend analysis skill that computes category totals and compares against the prior month
- **Create**: memory/finance/2026-05.md — current month's expense ledger (and subsequent monthly files as they are created)
- **Modify**: skills/diary-process/SKILL.md — extend the diary router to classify expense segments and dispatch to expense-extract
- **Modify**: AGENTS.md — add heartbeat check entry for spending anomaly detection

### Steps
1. Extend the diary-process skill to recognize expense segments in diary entries. Add classification logic that identifies mentions of spending amounts with currency indicators (CHF, francs) and dispatches those segments to the expense-extract skill.
2. Build the expense-extract skill at skills/expense-tracker/expense-extract.md. It should parse each dispatched segment to extract the amount, category (matched against memory/finance/categories.md), and date. Append the structured entry to the appropriate monthly file at memory/finance/YYYY-MM.md.
3. Handle ambiguous categories in the extraction skill by defaulting to "other" and noting the original description so Sam can reclassify later if needed.
4. Build the monthly summary skill at skills/expense-tracker/monthly-summary.md. It should read the current month's ledger file, compute totals per category, then read the prior month's file and compute the percentage change per category. Format the summary for Telegram with category totals and month-over-month deltas.
5. Add a spending anomaly check to the summary skill: if any category exceeds the prior month's total by 20% or more, flag it prominently in the Telegram output with the exact percentage increase and both month's totals.
6. Register the spending anomaly check in AGENTS.md as a heartbeat extension that runs the monthly comparison on each sweep and alerts only when a threshold is crossed.
7. Create the orchestrating SKILL.md at skills/expense-tracker/SKILL.md to handle manual queries like "what did I spend this month?" or "show my dining out trend" by reading the relevant ledger files and computing on-demand summaries.

### Verify
- Submit a diary entry mentioning an expense (such as "lunch for CHF 22") and confirm that memory/finance/2026-05.md contains a new entry with the correct amount, category, and date
- Submit multiple expense entries across different categories and run the monthly summary skill to confirm category totals are accurate
- Create a prior month file with known values, add current month entries that exceed one category by more than 20%, and confirm the anomaly alert fires in Telegram with the correct percentage
- Run the expense-tracker skill with a query like "what did I spend this month?" and confirm it returns a readable category breakdown