# 🏗️ Solution Architecture: ClawBoi v2 Phase 2 — Unfair Advantage Expansion

## Architecture Overview

Phase 2 extends a working diary-processing agent into a multi-domain life optimization system. The core architectural insight is that **the diary remains the universal input**. Rather than building separate intake mechanisms for jobs, contacts, and expenses, every new capability extracts structured data from the same unstructured diary entries that Phase 1 already processes. This means the diary-process skill becomes a router — it classifies entry segments and dispatches them to domain-specific extraction skills that persist structured state into a partitioned memory layer.

The second key insight is that **all five capabilities share exactly two interaction patterns**: passive extraction (diary entry → structured data → memory file) and proactive nudging (heartbeat scan → condition met → Telegram alert). No capability requires a novel interaction model. Job monitoring adds a third pattern — external data ingestion via RSS — but the downstream flow (filter → rank → notify) is identical to the nudge pattern. By recognizing these shared shapes, the architecture avoids five bespoke subsystems and instead builds three reusable patterns that all skills compose.

The system remains a single-user OpenClaw workspace running Claude CLI on a VPS. There is no database, no queue, no API server. Persistent state lives in partitioned markdown files under a `memory/` directory tree. External actions (emails, applications, messages) pass through a shared approval gate that blocks execution until explicit Telegram confirmation is received. The entire system is editable with a text editor and deployable by updating skill files — no build step, no compilation, no container rebuild.

## Design Principles

| Principle | Application in Phase 2 |
|-----------|----------------------|
| P1 — Adapter Boundary | himalaya is the sole email adapter. Job data sources are accessed through a single fetch-and-parse skill, never called directly from pipeline logic. If a source changes format or goes offline, only one skill file changes |
| P2 — Thin HTTP Layer | Not applicable — no HTTP server. The Telegram channel is the equivalent thin layer: it receives input, routes to skills, returns output. Skills contain no channel-formatting logic; output formatting is handled at the delivery boundary |
| P4 — No Speculative Abstractions | Each domain (jobs, contacts, finance) gets its own skill files and memory partition. No generic "entity extraction framework" — three concrete extractors that happen to follow the same shape |
| P6 — Skills First | Every capability ships as SKILL.md files. No plugin packaging, no build step. Iterate by editing markdown. Graduate to plugin only if a skill hits a real limitation (none anticipated for Phase 2) |
| P6 — References as Source of Truth | Profile-match criteria, contact priority rules, and expense categories live in reference files. Skills read them at invocation time — never duplicated inline |
| P6 — Channel-Aware Output | All Telegram responses stay under 4096 characters. Weekly digests use compressed formatting (rank + title + fit score + one-line rationale). Detailed breakdowns are written to memory files and linked, not inlined |
| P6 — Context Files Stay Current | SOUL.md, USER.md, IDENTITY.md, and AGENTS.md are updated as a prerequisite task, not an afterthought. Every new skill assumes these files reflect the full optimization picture |

## Component Design

### Memory Layer

**Purpose**: Provide partitioned, file-based persistent state for all domain skills without introducing a database.

The memory directory tree is the backbone of Phase 2. Each domain owns a subdirectory under `memory/` with a predictable file structure. Job intelligence writes to `memory/jobs/`, social graph to `memory/contacts/`, and expense tracking to `memory/finance/`. Within each partition, files follow a consistent convention: one index file for queryable state (the pipeline, the contact list, the monthly ledger) and dated log files for append-only history.

This partitioning matters for three reasons. First, it prevents a single monolithic memory file from growing past the point where Claude CLI can process it within context limits. Second, it allows skills to read only their domain's state without loading unrelated context. Third, it makes manual inspection trivial — Sam can open `memory/jobs/pipeline.md` in any editor to see application status without invoking the agent.

The trade-off is that cross-domain queries (such as "how much did I spend on job-search-related meals this month?") require reading from multiple partitions. This is acceptable for a single-user system where such queries are rare and can be handled by a dedicated skill that reads across partitions on demand.

### Diary Router (Extended diary-process)

**Purpose**: Classify diary entry segments and dispatch to domain-specific extraction skills.

The existing diary-process skill handles mood, goals, and action items. Phase 2 extends it with segment classification: when an entry mentions a person met, an expense incurred, or a job-related observation, the router dispatches those segments to the appropriate extraction skill after completing standard diary processing.

The router does not extract structured data itself. It identifies segments and passes them downstream. This keeps diary-process under the 200-line target and ensures each extraction skill owns its own parsing logic and validation rules. The router's only new responsibility is classification — a lightweight addition to an already-working skill.

### Job Intelligence Pipeline

**Purpose**: Passively monitor Swiss job markets, filter to high-fit roles, and deliver a curated weekly digest.

The pipeline has three stages: ingest, score, and digest. Ingestion pulls from RSS feeds (SwissDevJobs has a public feed) and aggregator APIs that provide structured job data without scraping. Each fetch writes raw results to `memory/jobs/raw/` as dated files. The scoring stage reads raw results against a profile-match reference file that encodes Sam's criteria: tech stack overlap (Python, Flask, Angular, TypeScript), domain relevance (finance preferred), location (Zürich), and compensation floor (CHF 115k). Each role gets a composite fit score. The digest stage selects the top five, formats a compressed summary with fit rationale, and delivers via Telegram.

The pipeline runs on the heartbeat schedule — not as a real-time monitor. Job postings are not time-sensitive in the way that inventory deals are; a weekly cadence is sufficient and keeps VPS compute low. Raw results accumulate between digests, and the scoring stage deduplicates against previously seen postings stored in `memory/jobs/seen.md`.

The critical constraint is discretion. No LinkedIn API calls, no authenticated scraping, no "open to work" signals. The data sources must be publicly accessible RSS feeds and APIs that do not require login or leave a traceable access pattern tied to Sam's identity.

### Application Workflow

**Purpose**: Take a shortlisted role from digest to sent application in a single Telegram conversation, with full approval gating.

This is a sequential skill chain, not a single monolithic skill. The chain is: select role from digest → generate tailored CV emphasis → draft cover letter → present complete application for approval → send via himalaya → update pipeline state. Each step is a separate skill invocation to keep individual skills small and independently testable.

CV tailoring works against a base CV stored in `memory/jobs/base-cv.md`. The skill adjusts emphasis and ordering of experience sections — it does not fabricate experience or skills. The reference file for tailoring rules defines which sections can be reordered, which bullet points can be promoted, and which keywords should be surfaced for given tech stacks.

Cover letter drafting reads the role description and company context to match tone. A formal Swiss financial institution gets different language than a startup. The tone-matching heuristic is simple: company size and industry from the job posting, mapped to three templates (formal, balanced, casual) defined in a reference file.

The approval gate is the hard constraint. The complete application (tailored CV summary, cover letter text, recipient, subject line) is presented in Telegram. Sam replies with explicit approval or rejection. Only after approval does himalaya dispatch the email. The pipeline tracker in `memory/jobs/pipeline.md` records each state transition with a timestamp.

Pattern detection on pipeline state (ghosting alerts, follow-up timing) reuses the existing pattern-detect skill from Phase 1 — pointed at pipeline data instead of diary entries.

### Social Graph Engine

**Purpose**: Extract contacts from diary entries, maintain a relationship store, and generate timely follow-up nudges.

The contact store in `memory/contacts/` holds one section per contact: name, context of meeting, date met, birthday (if known), last contact date, and priority tier. The diary router identifies "met someone" segments and passes them to the contact-extraction skill, which appends or updates the store.

Three reminder types fire on the heartbeat: follow-up reminders (3–5 days after meeting a new contact), birthday alerts (day-before notification), and network warming nudges (30+ days since last contact with a top-20 priority contact). Each reminder type is a simple date-comparison check against the contact store — no scheduling system, no cron, no persistent timers. The heartbeat reads the file, compares dates, and fires alerts for any contacts that cross a threshold.

The top-20 priority tier is manually curated by Sam in the contact store, not algorithmically determined. Automated priority ranking would require interaction frequency data that the system does not reliably have. Manual curation is more accurate and trivial to maintain for 20 entries.

### Expense Tracker

**Purpose**: Extract spending data from diary entries, maintain monthly category totals, and alert on trend deviations.

Expense extraction follows the same diary-router pattern: diary mentions of spending ("grabbed lunch for CHF 18," "SBB ticket CHF 45") are identified and dispatched to the expense-extraction skill. The skill parses amount, category, and date, then appends to `memory/finance/YYYY-MM.md` — one file per month.

Categories are defined in a reference file, not hardcoded in the skill. Initial categories: dining out, groceries, transport, subscriptions, entertainment, other. The monthly summary skill reads the current month's file, computes category totals, and compares against the prior month. A Telegram alert fires when any category exceeds the prior month by 20% or more.

The deliberate limitation is that this is diary-dependent. If Sam forgets to log an expense, it is invisible to the system. No bank API integration is planned — Swiss bank API support is poor, and the privacy trade-off is not worth it for a single-user awareness tool. If diary logging proves too tedious after 30 days, a structured `/expense` command can be added as a faster input path without changing the storage or analysis layer.

### Approval Gate (Shared Pattern)

**Purpose**: Ensure zero unsanctioned external actions across all capabilities.

Every skill that triggers an external side effect (sending email, submitting application) must pass through the approval gate. The gate is not a separate service — it is a behavioral contract enforced in each skill's SKILL.md: present the complete action to the user in Telegram, wait for explicit confirmation, execute only on approval.

The gate operates at the skill level, not at the adapter level. This is intentional — the approval context (what is being sent, to whom, why) is skill-specific and must be presented with enough detail for an informed decision. A generic adapter-level gate would strip that context.

### Heartbeat Extensions

**Purpose**: Make the existing heartbeat proactively useful by adding Phase 2 checks.

The heartbeat already runs on a configured interval. Phase 2 adds three check types to its sweep: new job matches since last digest, overdue follow-ups from the contact store, and overdue network warming nudges. Each check is a read-only scan of the relevant memory partition — no external calls, no heavy computation.

The heartbeat does not run job ingestion. Ingestion is a separate skill triggered on its own schedule (weekly). The heartbeat only checks whether new scored results exist that have not been delivered, and whether any contact date thresholds have been crossed. This keeps heartbeat execution fast and predictable.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent Runtime | OpenClaw with Claude CLI (Sonnet) | Already deployed from Phase 1. Claude CLI subprocess with 3600s timeout is sufficient for all Phase 2 operations. No reason to migrate to Anthropic SDK — single user, no concurrency pressure |
| Primary Interface | Telegram | Existing channel from Phase 1. Under-4096-char constraint forces concise output, which is a feature not a bug. No web UI needed for a single consumer |
| Email Dispatch | himalaya CLI | Already integrated via action-dispatch in Phase 1. Lightweight, scriptable, no SMTP configuration beyond what exists |
| Job Data Sources | RSS feeds + public aggregator APIs | SwissDevJobs RSS, Indeed RSS (Switzerland filter). No authenticated scraping, no LinkedIn API. Discretion constraint eliminates any source requiring login |
| Persistent State | Flat markdown files in `memory/` | No database warranted for single-user, low-write-frequency state. Markdown is human-readable, git-trackable, and directly consumable by Claude CLI as context |
| Compute | Existing VPS | No additional infrastructure. Skills are markdown files; compute cost is Claude CLI invocations. Budget constraint satisfied by weekly (not real-time) job monitoring cadence |

## Data Flow

The system has two primary data flows that account for all Phase 2 operations.

**Inbound (diary-driven)**: Telegram message → diary-process skill → segment classification → domain extraction skills (contact, expense, or job observation) → structured writes to `memory/` partitions. This flow is synchronous within a single Claude CLI invocation and completes within the diary-process response.

**Outbound (heartbeat-driven)**: Heartbeat fires → reads memory partitions → checks thresholds (new job matches, overdue follow-ups, spending anomalies) → composes alerts → delivers via Telegram. This flow is read-heavy and produces notifications, not state changes.

A third flow exists for the application workflow: user selects from digest → sequential skill chain → approval gate → himalaya send → pipeline state update. This is user-initiated and interactive, not automated.

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Diary as universal input | Avoids building separate intake UIs or commands for each domain. Sam already writes diary entries daily — extraction piggybacks on existing behavior | Expense and contact logging depend on diary discipline. If entries are sparse, extraction is sparse. Mitigated by adding `/expense` command later if needed |
| Weekly job digest, not real-time alerts | Job postings are not perishable inventory. Weekly cadence keeps VPS compute low and avoids alert fatigue. Five curated roles per week is more actionable than fifty raw postings | May miss a fast-filling role posted and closed within a week. Acceptable risk — most Swiss roles stay open 2–4 weeks |
| Flat markdown over SQLite | Single user, low write frequency, and Claude CLI can read markdown directly as context. No ORM, no schema migrations, no query language to maintain | Cross-domain queries are expensive (read multiple files, parse manually). Acceptable because cross-domain queries are rare and low-priority |
| RSS feeds over web scraping | Discretion constraint eliminates authenticated scraping. RSS is public, stateless, and leaves no traceable access pattern. Aggregator APIs with public endpoints supplement coverage | Fewer sources than scraping would provide. SwissDevJobs + Indeed cover the Swiss market adequately for a curated top-5 approach. LinkedIn is the gap — accepted and unfillable under constraints |
| Manual contact priority over algorithmic ranking | Algorithmic ranking requires interaction frequency data the system does not have (Telegram message counts, email frequency). Manual curation of 20 contacts is trivial and more accurate | Requires Sam to periodically review and update the priority list. Acceptable maintenance cost for a 20-item list |
| Skill chain over monolithic application skill | The apply workflow (select → tailor CV → draft letter → approve → send → track) is five distinct operations. Separate skills keep each under 200 lines and allow partial re-execution (redraft letter without re-tailoring CV) | More skill files to maintain. Each skill is small and focused, so the total complexity is lower than a single 500-line skill |
| Approval gate at skill level, not adapter level | Skill-level gating preserves action context (what is being sent, the full draft, the recipient). Adapter-level gating would be generic and lose this context | Every outbound skill must independently implement the gate pattern. Duplication is minimal (a few lines of confirmation prompting) and the safety guarantee is worth it |
| Exclude TooGoodToGo and SBB monitoring | Claude CLI + Telegram latency is measured in seconds to minutes. TooGoodToGo bags sell out in under two minutes. SBB supersaver tickets are similarly time-sensitive. The system cannot compete with dedicated real-time pollers | Loses two requested capabilities. Revisit only if a lightweight, non-OpenClaw poller is built separately (a simple cron + curl script pushing to Telegram, outside this architecture) |
| No investment or portfolio tracking | Explicitly excluded in scope. The system handles expense awareness (what you spend) not wealth management (what you have). Mixing the two creates scope creep and liability | Expense tracking without income/savings context gives an incomplete financial picture. Acceptable — the goal is spending awareness, not financial planning |

## Risk Considerations

**Job data source reliability**: RSS feeds can change format or go offline without notice. The ingestion skill should handle parse failures gracefully — write an error to the raw log and continue rather than failing the entire digest. If both primary sources degrade, the weekly digest simply reports fewer results rather than erroring.

**Memory file growth**: Monthly expense files and the contact store are bounded by human input rate and will not grow unmanageably. The job pipeline file could accumulate entries over months. A periodic archival pattern (move entries older than 90 days to `memory/jobs/archive/`) prevents the active pipeline file from exceeding context limits.

**Diary logging discipline**: The entire inbound flow depends on Sam writing diary entries that mention expenses, contacts, and job observations. If diary entries become sparse during a stressful job search period, extraction quality degrades. The `/expense` escape hatch and potential `/contact` command mitigate this for the two most structured domains.

**Claude CLI token costs**: Each heartbeat invocation and each diary processing run consumes Claude CLI tokens. Phase 2 roughly doubles the context read per invocation (more memory files loaded). Monitor monthly token spend after launch and adjust heartbeat frequency if costs exceed budget.

## Related Documents

- [Analysis](./analysis.md) — Problems driving this architecture
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Delivery status tracking