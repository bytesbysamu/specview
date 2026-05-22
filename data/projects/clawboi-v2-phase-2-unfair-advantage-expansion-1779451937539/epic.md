# 🎯 Epic: ClawBoi v2 Phase 2 — Unfair Advantage Expansion

## Business Value

Phase 1 proved that an AI agent can process unstructured diary entries into actionable insights — pattern detection, BS scoring, and action dispatch are running in production. But insight without action is journaling, not advantage. The Swiss tech job market is contracting, and manual applications are a losing strategy: slow, generic, and invisible against candidates using AI-assisted pipelines. An automated job intelligence system that passively monitors openings, filters to a curated shortlist, and drafts tailored applications gives a measurable edge — higher application quality at 10× the throughput, with zero public signal that a search is underway.

Beyond career, the same agent infrastructure can reduce daily friction in two high-value areas. Expense awareness turns scattered diary mentions into monthly spending intelligence — no bank API needed, just structured extraction from entries already being written. Social graph maintenance prevents the slow decay of professional relationships that costs opportunities: automated follow-up reminders and birthday tracking turn a 20-person network from "people I used to know" into active connections. Each of these capabilities compounds over time — the agent gets more context, the pattern detection gets sharper, the advantage grows.

The sole consumer is Sam. There is no market to sell to — the ROI is direct: better job offers, lower monthly spend, stronger professional network. The investment is skill files and Claude CLI compute on an existing VPS. The cost of *not* building this is continuing to manually scan job boards, forget follow-ups, and lose track of spending — problems that get worse under the stress of an active job search.

## Scope

### What This Epic Covers

- **Workspace & memory foundation** — updated SOUL.md, AGENTS.md, and a defined memory directory structure that supports persistent state for all new capabilities
- **Job intelligence pipeline** — passive monitoring of Swiss job boards via RSS feeds and aggregator APIs, smart filtering by profile fit, weekly top-5 digest delivered to Telegram
- **Application workflow** — CV emphasis tailoring per shortlisted role, cover letter drafting, confirm-before-send execution via himalaya, and pipeline tracking (applied → interview → outcome)
- **Social graph management** — contact store extracted from diary entries, follow-up reminders, birthday tracking, and 30-day network warming nudges
- **Expense awareness** — diary-based expense extraction, monthly category totals, and trend alerts when spending deviates from baseline

### What This Epic Does NOT Cover

- ❌ **LinkedIn scraping or public "open to work" signals** — violates ToS, actively blocked, and contradicts the discretion constraint
- ❌ **Real-time TooGoodToGo / SBB alerting** — Claude CLI + Telegram latency is too high for time-sensitive inventory (bags sell out in minutes); revisit only if a dedicated lightweight poller is built outside OpenClaw
- ❌ **Investment or portfolio advice** — explicitly excluded in brain dump; no net-worth tracking
- ❌ **Bank API or automated expense import** — Swiss banks have poor API support; manual diary logging only; revisit if `/expense` structured command proves too tedious after 30 days of use
- ❌ **Bubls integration** — social event discovery is handled by a separate app; no duplication inside OpenClaw
- ❌ **Automated sending without approval** — confirm-before-execute is a hard constraint, not a future relaxation target
- ❌ **LinkedIn profile optimization** — contradicts discretion constraint while employed

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Workspace & Memory Foundation** — update SOUL.md with expanded role, AGENTS.md with new skill routing, define memory directory structure (`memory/jobs/`, `memory/contacts/`, `memory/finance/`), update USER.md and IDENTITY.md to reflect full optimization picture | None | — | 1 day | High |
| 2 | **Job Intelligence Pipeline** — resolve data source (RSS feeds + aggregator API, not scraping), build job-monitor skill with profile-match scoring, deliver weekly top-5 digest to Telegram with fit rationale | Task 1 | With Task 4 | 3 days | High |
| 3 | **Application Workflow** — CV emphasis-tailoring skill using base CV, cover letter drafting matched to role tone, confirm-before-send via himalaya, pipeline state tracking in `memory/jobs/pipeline.md` with pattern detection on ghosting | Task 2 | With Task 4, 5 | 2 days | High |
| 4 | **Social Graph & Follow-ups** — contact store in `memory/contacts/`, diary-to-contact extraction, follow-up reminders (3-5 days after meeting), birthday tracking with day-before alerts, 30-day network warming for top 20 contacts | Task 1 | With Task 2 | 2 days | Low |
| 5 | **Expense Awareness** — diary-based expense extraction skill, monthly category totals in `memory/finance/`, trend detection with Telegram alerts when category spending exceeds prior month by 20%+ | Task 1 | With Task 2, 4 | 1 day | Low |

## Success Criteria

- ✅ Memory directory structure is defined and all new skills read/write to it consistently
- ✅ Job monitor returns a ranked top-5 weekly digest from at least two Swiss job data sources with profile-fit scores
- ✅ A shortlisted role can go from digest → tailored CV → drafted cover letter → approved send via himalaya in a single Telegram conversation
- ✅ Pipeline state persists across sessions — querying "what's my application status?" returns accurate, current data
- ✅ Diary entry mentioning a new contact triggers a follow-up reminder 3-5 days later without manual scheduling
- ✅ Monthly expense summary is generated from diary entries with category breakdown and month-over-month trend comparison
- ✅ All external actions (emails, applications, messages) require explicit Telegram approval before execution — zero unsanctioned sends
- ✅ Heartbeat performs at least one proactive check (new job matches or overdue follow-ups) per configured interval

## Related Documents

- [Analysis](./analysis.md) — Problems driving this epic
- [Solution Architecture](./architecture.md) — System design
- [Timeline](./timeline.md) — Status tracking