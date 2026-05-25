# 🎯 Epic: Distribution Agent — The Missing Piece

## Business Value

Four SaaS products are deployed, collecting signups, and generating near-zero revenue. The engineering is done — the bottleneck is distribution. TrustMRR data confirms this pattern: 68.9% of tracked startups sit at $0–$1K/month, yet the ones breaking out don't have large audiences or ad budgets. They have systematic presence in the communities where buyers already talk. Every day without that presence is compounding missed revenue across four products simultaneously.

An OpenClaw-native distribution agent closes this gap at zero incremental cost. Reddit monitoring via public `.json` endpoints, Hacker News monitoring via the free Algolia API, reply drafting via the already-running Claude CLI backend, and delivery via the already-connected Telegram channel — all on the existing VPS. The agent is product-agnostic: a markdown file per product defines what to monitor, which subreddits to watch, and how to talk about it. Add a file, gain coverage. Remove a file, stop monitoring. No code changes, no new infrastructure, no paid APIs.

The business case is simple arithmetic. One product crossing $500 MRR within three months validates the entire distribution thesis. If four products × daily monitoring × 2–3 genuine replies per week can't produce a single measurable conversion, the problem is positioning — and the agent's keyword frequency data tells us exactly how to pivot. Either way, the agent generates the signal needed to make the next decision.

## Scope

### What This Epic Covers

- **Product context files and brand voice** — Markdown-based product definitions (ICP, keywords, subreddits, tone) and a shared BRAND.md that encodes reply guardrails, making the agent product-agnostic and safe by default
- **Reddit monitoring skill** — Subreddit scanning via public `.json` endpoints, relevance scoring against product context, and deduplication to avoid resurfacing stale threads
- **HN monitoring skill** — Keyword and competitor scanning via the HN Algolia API, scored and deduplicated alongside Reddit results
- **Reply drafting skill** — Context-aware draft generation that matches subreddit tone, leads with value, includes founder disclosure, and respects the guardrails defined in BRAND.md
- **Distribution digest and cron wiring** — A daily Telegram-delivered summary of scored opportunities with draft replies, wired to the existing 07:30 cron slot, formatted within the 4096-char Telegram limit

### What This Epic Does NOT Cover

- ❌ **Auto-posting to Reddit or HN** — Both platforms require OAuth (Reddit) or have no write API (HN); all replies are human-approved and manually posted. See [Analysis](./analysis.md) for the posting constraint breakdown
- ❌ **F5Bot email ingestion** — No email reader exists in the OpenClaw stack; adding IMAP polling or an email-to-webhook bridge is a separate capability. The morning scan covers the same platforms F5Bot monitors
- ❌ **X/Twitter monitoring or posting** — Intentionally excluded; research shows X followers don't correlate with revenue at this stage. Trigger: Reddit/HN replies generate measurable traffic but plateau
- ❌ **SEO landing pages** — Manual content work informed by agent keyword data, not agent behavior. Revisit after Month 1 when keyword frequency data exists
- ❌ **Show HN posts and content calendar** — Content creation strategy, not monitoring. Separate spec if distribution thesis proves out
- ❌ **Telegram inline-keyboard approval flow** — "One-tap approve → agent posts" requires a non-trivial callback loop and write-API access that doesn't exist. MVP approval is: read draft in Telegram, copy-paste to platform
- ❌ **Bubls** — Not a monitored product; not publicly launched. Trigger: public launch

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Product Context Files + BRAND.md** | None | — | 0.5 days | High |
| 2 | **Reddit Monitor Skill** | Task 1 | Can be built in any order with Task 3 | 1 day | High |
| 3 | **HN Monitor Skill** | Task 1 | Can be built in any order with Task 2 | 0.5 days | High |
| 4 | **Reply Drafter Skill** | Tasks 2, 3 | — | 0.5 days | High |
| 5 | **Distribution Digest + Cron Wiring** | Task 4 | — | 0.5 days | High |

**Task 1 — Product Context Files + BRAND.md:** Define the four product markdown files (specview, humaniz.me, speedback, trendfy) containing ICP, keywords, subreddits, competitors, and reply tone. Define BRAND.md with voice guardrails, anti-patterns, and the reply template structure. These files are the single source of truth that every downstream skill consumes. Resolve Trendfy's status (alive or archived) before writing its context file — see [Analysis](./analysis.md) open questions.

**Task 2 — Reddit Monitor Skill:** An OpenClaw SKILL.md that scans target subreddits from product context files, scores posts for relevance (0–10), deduplicates against a file-based seen-posts store, and returns posts scoring above threshold. Must complete within the Claude CLI 3600s timeout across all products and subreddits combined.

**Task 3 — HN Monitor Skill:** An OpenClaw SKILL.md that queries the HN Algolia API for keyword and competitor matches from product context files, scores relevance, and deduplicates. Runs in parallel with Task 2 during the morning cron window.

**Task 4 — Reply Drafter Skill:** An OpenClaw SKILL.md that takes a scored post plus the relevant product context file and BRAND.md, then generates a reply draft following the guardrail rules: acknowledge problem → share insight → mention tool with disclosure → no CTA. Output is a structured block ready for the digest.

**Task 5 — Distribution Digest + Cron Wiring:** An OpenClaw SKILL.md that formats all scored opportunities and draft replies into a Telegram-friendly digest (respecting 4096-char limit, splitting across messages if needed), and wiring the full pipeline to the 07:30 Europe/Zurich daily cron slot via the existing heartbeat dispatcher.

## Success Criteria

- ✅ Morning digest arrives in Telegram by 08:00 Europe/Zurich every day without manual intervention
- ✅ At least 10 relevant posts (score ≥ 7) surfaced per day across all four products and both platforms combined
- ✅ Each surfaced post includes a draft reply that follows BRAND.md guardrails (value-first, founder disclosure, no superlatives)
- ✅ Adding a new product requires only creating a new `.md` file in the products directory — no skill or code changes
- ✅ Removing a product `.md` file stops all monitoring for that product in the next cron run
- ✅ Deduplication prevents the same post from appearing in consecutive digests
- ✅ Full morning scan (4 products × 2 platforms) completes within the 3600s Claude CLI timeout
- ✅ At least 1 measurable click-through to a product page within 30 days of first reply posted (Month 1 gate)
- ✅ If no product crosses $500 MRR by Month 3, keyword frequency data from the agent is sufficient to inform a positioning pivot

## Related Documents

- [Analysis](./analysis.md) — Open questions on write-API access, F5Bot ingestion, and product status driving scope decisions
- [Solution Architecture](./architecture.md) — Skill design, deduplication strategy, cron wiring, and Telegram formatting
- [Timeline](./timeline.md) — Task status and delivery tracking