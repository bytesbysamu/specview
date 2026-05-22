# 🔍 ClawBoi v2 Phase 2 — Unfair Advantage Expansion — Analysis

## The Problem
Phase 1 delivers self-awareness (diary, patterns, BS detection). Phase 2 asks it to act on the world — scrape job boards, monitor deals, manage relationships. The gap between "parse my diary" and "apply to jobs on my behalf" is enormous: it requires persistent polling, anti-scraping evasion, multi-platform auth, and real-time alerting — all within a markdown-skills + Claude CLI + Telegram stack designed for async text processing.

## Hard Constraints
- Single-user, Telegram I/O, Claude CLI provider (3600s timeout)
- Confirm-before-execute on ALL external actions
- No public job-search signals — currently employed
- Skills-first architecture — SKILL.md files, no build step
- VPS-budget compute — no always-on polling daemons
- Himalaya for email; apple-reminders for tasks (existing integrations)

## Open Questions
- **Job board data access** — LinkedIn scraping violates ToS and is actively blocked. SwissDevJobs may have RSS. Indeed has no public API. Options: (a) RSS/feeds only, (b) browser automation via Playwright, (c) paid aggregator API (Adzuna, Arbeitnow). This decides what "scraping" actually means.
- **TooGoodToGo + SBB alerting latency** — bags sell out in minutes, but Claude CLI + Telegram has multi-second latency and heartbeat is periodic. Options: (a) dedicated lightweight polling script outside OpenClaw that pushes to Telegram directly, (b) accept you'll miss most bags and treat it as best-effort, (c) cut this feature.
- **Heartbeat frequency vs. cost** — proactive checks (jobs, TGTG, overdue follow-ups) burn Claude CLI invocations. How often? Every 15 min? Hourly? Daily? This is a budget question disguised as a config question.
- **Expense tracking input method** — "log expenses in the diary" implies manual entry. No bank API, no receipt scanning mentioned. Is manual-only acceptable, or does this need structured input (e.g., `/expense 45 restaurant`)?
- **Memory directory structure** — explicitly asked, unanswered. Options: (a) single `memory/` with prefixed files, (b) `memory/diary/`, `memory/jobs/`, `memory/finance/`, `memory/contacts/` subdirs, (c) hybrid — diary stays flat, structured data gets subdirs.
- **"Platform apply mechanism"** — what does this mean concretely? Most job platforms require authenticated browser sessions. Realistic option is email-only applications via himalaya. Does that limit the funnel unacceptably?

## Dependencies & Sequencing
- **Job scraping blocks everything downstream** — filtering, CV tailoring, application drafting, and pipeline tracking are all useless without a working data source. Resolve the data access question first.
- **Memory structure blocks all new skills** — every new skill (jobs, expenses, contacts) needs to read/write persistent state. Decide the directory convention before building any of them.
- **SOUL.md / AGENTS.md update blocks orchestration** — new skills won't be discovered or routed correctly without updated workspace config. This is the actual first task.
- **Social outreach depends on a contact store that doesn't exist yet** — "top 20 contacts" and birthday tracking need a structured data file and a convention for diary-to-contact extraction.

## Explicitly Out of Scope
- **Investment / portfolio advice** — brain dump explicitly excluded it, keep it excluded. Re-scope if net worth tracking is ever needed.
- **Automated sending without approval** — confirm-before-execute is a hard constraint, not a Phase 3 graduation target.
- **Bubls integration** — social events already handled by a separate app. Don't duplicate event discovery inside OpenClaw. Re-scope only if Bubls is sunset.
- **Bank API / automated expense import** — no mention of bank integration, and Swiss banks have poor API support. Manual diary logging only for now. Re-scope if a `/expense` structured command proves too tedious after 30 days.
- **LinkedIn profile optimization / public presence** — contradicts the discretion constraint. Not in scope until employment status changes.
- **Real-time TGTG/SBB monitoring** — unless the latency question resolves with a dedicated polling script, treat these as best-effort daily-digest features, not real-time alerting. Re-scope if a lightweight cron-based poller is built outside OpenClaw.