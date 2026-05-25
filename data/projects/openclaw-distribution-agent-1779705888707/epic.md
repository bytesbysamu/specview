# 🎯 Epic: OpenClaw Distribution Agent

## Business Value

Sam runs 4 active SaaS products with zero systematic distribution — posting is manual, inconsistent, and competes with build time. Every hour spent on manual Reddit replies or drafting X threads is an hour not shipping features. OpenClaw already has the primitives (Reddit scraping, X posting via OpenTweet, cron scheduling, Claude API) but nobody has wired them into a repeatable distribution workflow. An internal agent that handles daily Reddit digests, keyword-triggered reply drafting, and X content queuing would reclaim 5-10 hours per week at a running cost of ~$50-100/month.

The wrapper/hosting niche for AI agent platforms is saturated and dying — SimpleClaw wound down from $17K MRR to zero. The gap is **productized outcomes**, not deployment. Claw Mart's top skill ($9) moved 1,381 units ($12K+); its top persona ($99) moved 1,123 units ($111K+). A "SaaS founder distribution" skill pack priced at $49-79 targets a proven buyer persona with no direct competitor in the marketplace. The path is dogfood first — validate the workflow on Sam's own products — then package what works as a Claw Mart listing. Only after the skill pack demonstrates traction ($1.5K MRR gate) does a managed vertical agency become worth designing.

The internal agent is the forcing function: it either produces measurable distribution results within 14 days or it exposes workflow problems that must be fixed before any productization makes sense. There is no scenario where skipping internal validation and jumping to a skill pack listing ends well.

## Scope

### What This Epic Covers

- **Foundation skill development** — Build or verify the three core skills (`reddit-openclaw`, `opentweet-x-poster`, `reply-drafter`) that every downstream workflow depends on
- **Product positioning context** — Author the BRAND.md and per-product PRODUCT.md files that give the agent voice, talking points, and targeting information
- **Internal distribution agent** — Wire sub-agents, cron triggers, and Telegram approval flows into a running system across 4 active products
- **Validated distribution workflow** — A 14-day instrumented run that proves (or disproves) the agent produces qualified leads and impressions before any productization begins
- **Skill pack packaging** — Bundle proven skills for Claw Mart listing, gated behind internal validation passing kill thresholds

### What This Epic Does NOT Cover

- ❌ **LarryBrain acquisition** — Opportunistic sidebar, not a workstream; re-evaluate only if skill pack crosses $1.5K MRR AND asking drops below $60K
- ❌ **Vertical agency / managed care** — Months 2-4 at earliest, gated behind skill pack traction; no design work until gate is met
- ❌ **`launch-amplifier` and `competitor-pulse` skills** — Named in the skill pack vision but undefined; spec them when skill pack work begins
- ❌ **Playwright browser automation integration** — Listed as an OpenClaw primitive but no current workflow requires it
- ❌ **Horizontal "marketing brain" positioning** — Claw4Growth already owns this space; this agent targets the narrow SaaS-founder distribution niche

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Foundation Skills Build** — Verify existence or build `reddit-openclaw` (free scraping, no API key), `opentweet-x-poster` (OpenTweet integration), and `reply-drafter` (Claude-powered contextual replies) | None | Tasks 1 & 2 run in parallel | 4 days | High |
| 2 | **Product Context Authoring** — Create shared BRAND.md (Sam's personal founder voice) + individual PRODUCT.md for each of the 4 active products (positioning, pain points, target subreddits, competitor handles) | None | Tasks 1 & 2 run in parallel | 2 days | High |
| 3 | **Distribution Agent Assembly** — Wire 4 product sub-agents with cron schedules (Reddit digest, keyword scan, X content drafting) and Telegram approval flow respecting 4096-char limits | Tasks 1, 2 | — | 3 days | High |
| 4 | **14-Day Validation Run** — Operate the agent across all 4 products; instrument lead tracking and impression counts; evaluate against kill thresholds (≥3 qualified leads, ≥10K impressions) | Task 3 | — | 14 days | High |
| 5 | **Skill Pack Productization** — Bundle the 4 proven skills, write Claw Mart listing copy, set pricing tiers ($49 standard / $79 Claude-optimized), and submit for marketplace listing | Task 4 (must pass kill thresholds) | — | 3 days | Low |

## Success Criteria

- ✅ All three foundation skills (`reddit-openclaw`, `opentweet-x-poster`, `reply-drafter`) operational and tested against live targets
- ✅ Internal agent runs unattended on cron for 14 consecutive days across all 4 products
- ✅ Telegram approval flow delivers actionable content within the 4096-char limit — no blind approvals, no message truncation that hides context
- ✅ 14-day validation produces ≥3 qualified leads AND ≥10K impressions (kill threshold from brain dump)
- ✅ Total running cost stays within ~$50-100/month ceiling (existing VPS + OpenTweet $11.99 + Claude API with prompt caching)
- ✅ Skill pack listed on Claw Mart with both pricing tiers (only if Task 4 passes thresholds)

## Open Decisions

These were flagged in analysis and must be resolved before or during Task 2:

- **Which 4 products?** Profile lists 5 projects. Trendfy has a passed kill date — confirm whether it's included or replaced by sam-plugin
- **BRAND.md: shared or per-product?** A humanizer, an event app, a fashion tool, and a dev tool have no shared voice. Recommendation: BRAND.md captures Sam's founder voice; per-product PRODUCT.md captures product-specific tone
- **Telegram batch approval UX** — "2 threads + 5 tweets" won't fit in one 4096-char message. Choose: individual approvals (noisy but informed) vs. batched with summary (faster but blind). Must be decided in architecture

## Related Documents

- [Analysis](./analysis.md) — Problems, constraints, and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design, skill structure, cron schedules, and Telegram UX decisions
- [Timeline](./timeline.md) — Execution status and progress tracking