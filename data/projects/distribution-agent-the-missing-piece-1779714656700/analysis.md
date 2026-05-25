# 🔍 Distribution Agent — The Missing Piece — Analysis

## The Problem
Four SaaS products are deployed but generate near-zero revenue because there is no systematic distribution. OpenClaw already runs on VPS with Telegram, Claude CLI, and cron — but has no skills for monitoring platforms or drafting replies. The gap is not engineering capacity but showing up where buyers are already talking.

## Hard Constraints
- OpenClaw skill system (SKILL.md files, not sub-agents)
- No Redis/Postgres — dedup state must be file-based or in-process dict + Lock
- Telegram message limit: 4096 chars (digest formatting must respect this)
- Claude CLI subprocess timeout: 3600s (morning scan across 4 products × 2 platforms must fit)
- Reddit `.json` endpoint is **read-only** — no write capability without OAuth
- F5Bot delivers via email — OpenClaw has no email ingestion path today

## Open Questions
- **How does the agent post replies to Reddit?** `.json` scraping is read-only. Posting requires OAuth + registered app. "Zero API" only covers monitoring, not action. Options: (a) agent drafts, Sam posts manually, (b) add Reddit OAuth (breaks the "no API key" claim), (c) Telegram message includes a deep link to the thread and Sam copy-pastes.
- **How does the agent post to HN?** HN has no public write API. Same three options apply.
- **How does F5Bot email reach OpenClaw?** No email reader exists in the stack. Options: (a) forward to a webhook via email-to-HTTP service, (b) IMAP polling skill, (c) drop F5Bot and rely solely on the morning scan.
- **Trendfy is alive or dead?** Builder profile says "kill date passed, status TBD" but the brain dump monitors it as one of four active products. Decide before writing product context files.
- **What are specview and speedback?** Neither appears in the builder profile's active projects. Are these new launches, renamed projects, or aspirational? Their deployment status determines whether monitoring them is premature.
- **"One-tap approve" mechanism?** Telegram inline keyboard buttons → callback to OpenClaw → OpenClaw posts? This is a non-trivial interaction loop that isn't scoped in any skill.

## Dependencies & Sequencing
- Product context files block every skill (they define what to monitor and how to reply)
- Reddit/HN posting decision blocks reply-drafter scope (draft-only vs. draft-and-post are different skills)
- F5Bot email ingestion blocks f5bot-processor (or cut it entirely)
- Deduplication requires persistent state — file-based store must be designed before both monitors ship
- Telegram approval flow (inline keyboards + callbacks) blocks the "one-tap approve" UX — this may be the hardest piece

## Explicitly Out of Scope
- **SEO landing pages** — manual content work, not agent behavior. Revisit when keyword frequency data exists (Month 1+).
- **Show HN / content calendar** — content creation strategy, not monitoring. Separate spec if needed after agent proves distribution thesis.
- **X/Twitter** — intentionally excluded per brain dump. Trigger: Reddit/HN replies generate measurable traffic but plateau.
- **Auto-posting** — brain dump explicitly rejects it, but the workflow implies it. Resolve in open questions above; keep human-in-the-loop as the default.
- **Bubls** — not listed as a monitored product; don't let it creep in. Trigger: Bubls launches publicly.