# 🏗️ Solution Architecture: OpenClaw Distribution Agent

## Architecture Overview

The Distribution Agent is an OpenClaw workspace plugin that wires three foundation skills — Reddit monitoring, X posting, and contextual reply drafting — into a cron-driven workflow across Sam's four active products. The central insight is that distribution for a solo founder is not an automation problem but an **approval-flow problem**: the agent must surface the right content at the right time through Telegram, and the founder must be able to approve or kill each piece in under 10 seconds. Every design decision flows from this constraint.

The system is structured as a single OpenClaw plugin containing three skill files, four product sub-agents (one per product), and a shared context layer. Sub-agents are declarative — they describe what to monitor and how to respond, not how to execute. Execution is delegated entirely to the foundation skills. Cron entries trigger the sub-agents on schedule; each sub-agent assembles context from its PRODUCT.md, calls the relevant skill, and routes output to Telegram for approval. There is no central orchestrator, no job queue, and no persistent state beyond what OpenClaw's workspace already provides.

This architecture deliberately avoids building infrastructure. OpenClaw already ships cron scheduling, Claude API access with prompt caching, and Telegram channel delivery. The plugin's job is to provide the **domain knowledge** (product positioning, subreddit targets, competitor handles) and the **workflow shape** (what triggers what, what needs approval, what posts automatically). Anything that looks like plumbing belongs in OpenClaw core, not in this plugin.

## Design Principles

| Principle | Application in This System |
|-----------|---------------------------|
| **P6 — Skills First** | All three capabilities ship as `SKILL.md` files. No `openclaw.plugin.json` package until a concrete limitation forces graduation. Fast iteration matters more than packaging during the 14-day validation window. |
| **P4 — No Speculative Abstractions** | Four product sub-agents, not a generic "product agent factory." Each sub-agent is a flat markdown file with hardcoded subreddit lists, competitor handles, and posting cadence. Three similar agent files are better than a premature template system. |
| **P6 — References as Source of Truth** | BRAND.md and PRODUCT.md files are the single source of voice, positioning, and targeting. Sub-agents and skills reference these files — they never inline the same talking point twice. Updating a product's positioning means editing one file, not hunting through agent definitions. |
| **P1 — Adapter Boundary** | The `opentweet-x-poster` skill is the only component that knows how OpenTweet's API works. The `reddit-openclaw` skill is the only component that knows how Reddit scraping works. Sub-agents call skills by name; they never touch external services directly. |
| **P6 — Channel-Aware Output** | Every skill and sub-agent formats output for Telegram's 4096-character limit. This is not a nice-to-have — it is a structural constraint that shapes message design, approval UX, and content batching decisions. |
| **P2 — Thin Orchestration** | Cron entries call sub-agents. Sub-agents call skills. Skills call external services. No layer contains logic that belongs in another layer. The cron schedule is configuration, not code. |

## Component Design

### Context Layer — BRAND.md and PRODUCT.md

**Purpose**: Provide the agent with Sam's founder voice and per-product domain knowledge without duplicating content across sub-agents or skills.

BRAND.md is a single shared file capturing Sam's personal founder voice — communication style, credibility markers (BullshitBench #2, 4 production SaaS products), and tone guardrails. This file is product-agnostic. It answers: "How does Sam talk?"

Each active product gets its own PRODUCT.md containing: one-line positioning, target audience pain points, three to five target subreddits, competitor handles for X monitoring, key differentiators, and links. These files answer: "What does this product do and who cares?"

The epic flagged an open decision on which four products to include. Trendfy's kill date has passed — its status is TBD. The architecture accommodates this by treating product inclusion as a **context file decision, not a structural one**. Adding or removing a product means creating or deleting a PRODUCT.md and its corresponding sub-agent file. No shared infrastructure changes. The recommendation is to start with the four active products from the builder profile — spec-doc, humanize-me, Bubls, and sam-plugin — and re-evaluate Trendfy only if it is actively revived before the validation run begins.

### Foundation Skills — Three SKILL.md Files

**Purpose**: Encapsulate the three atomic capabilities that every distribution workflow depends on.

**`reddit-openclaw`** — Reads target subreddits using OpenClaw's free scraping primitive (no Reddit API key). Accepts a list of subreddits and keyword filters. Returns structured post summaries: title, subreddit, score, comment count, URL, and a relevance tag. This skill is read-only and stateless. It runs on every cron trigger and produces a fresh snapshot.

**`opentweet-x-poster`** — Wraps the OpenTweet service ($11.99/month) for posting threads and individual tweets to X. Accepts draft content and a scheduling timestamp. Returns confirmation or error. This is the only component in the system that holds an OpenTweet credential. All X-related output flows through this single skill — sub-agents never interact with OpenTweet directly.

**`reply-drafter`** — Takes a Reddit post or X mention plus the relevant PRODUCT.md context and produces a contextual reply draft. Uses Claude API (Sonnet 4.6) with prompt caching to keep per-invocation cost low. The skill's core job is **tone calibration**: replies must read as a founder sharing experience, not a bot pushing links. BRAND.md supplies the voice; PRODUCT.md supplies the substance; the skill blends them into a reply that passes the "would a human write this?" test.

All three skills follow the SKILL.md pattern from the financing-plugin reference: trigger conditions, steps, available tools, and examples. They reference BRAND.md and PRODUCT.md by path rather than inlining content.

### Product Sub-Agents — One Per Product

**Purpose**: Encode per-product distribution strategy as a declarative agent definition.

Each sub-agent is a flat markdown file that declares: which subreddits to monitor, which competitor handles to track on X, what posting cadence to follow, and which skills to invoke for each workflow. Sub-agents are not orchestrators — they are **configuration expressed as agent instructions**. When a cron entry fires, OpenClaw loads the sub-agent, which references its PRODUCT.md for context and calls the appropriate foundation skill.

Four sub-agents run independently. They share no state and have no awareness of each other. This is intentional: a failure in the humanize-me sub-agent (bad subreddit list, irrelevant drafts) does not cascade to Bubls or spec-doc. Each product's distribution quality is isolated and independently tunable.

The trade-off is repetition. Four sub-agent files will contain structurally similar instructions. Per P4, this is acceptable — a shared template would save perhaps 30 lines of markdown while introducing indirection that makes per-product tuning harder. When a fifth product is added, copy-and-modify remains cheaper than maintaining a template system.

### Cron Schedule Design

**Purpose**: Trigger the right workflows at the right times without overwhelming the approval channel.

Three cron patterns, chosen to match the natural rhythm of Reddit and X activity during US business hours (the primary audience timezone for all four products):

**Morning digest (7:30 AM ET, daily)** — Each sub-agent's Reddit monitoring fires once. The `reddit-openclaw` skill scrapes target subreddits, filters by keywords, and produces a digest. The digest routes to Telegram as a single summary message per product. This is informational — no approval needed. Sam reads the digest over coffee and decides which threads warrant a reply.

**Keyword scan and reply drafting (hourly, 9 AM–6 PM ET)** — Each sub-agent scans for new posts matching high-intent keywords. When matches are found, the `reply-drafter` skill produces draft replies. Each draft routes to Telegram for individual approval. Hourly cadence balances freshness (Reddit threads age fast) against notification fatigue (9 approval windows per day, not 24).

**X content drafting (twice daily, 10 AM and 3 PM ET)** — Each sub-agent triggers competitor mention analysis and produces draft threads and tweets. Drafts route to Telegram for approval. Approved content queues in OpenTweet for optimal posting times. Twice-daily cadence matches X's engagement patterns without requiring constant attention.

The total daily Telegram message volume across all four products: 4 morning digests + up to 36 reply approval requests (4 products × 9 hourly windows, though most windows will produce zero matches) + 8 X content batches (4 products × 2 daily). In practice, expect 10–15 messages per day during the validation period. If volume exceeds 25 messages per day, reduce the keyword scan to every 2 hours.

### Telegram Approval Flow

**Purpose**: Give Sam informed, fast approval of agent-drafted content without exceeding Telegram's 4096-character message limit.

The epic flagged this as an open decision: individual approvals versus batched approvals. The architecture chooses **individual approvals for replies, summary-first for X content batches**.

**Reddit reply approvals** arrive as individual messages. Each message contains: the original post title and subreddit, a 2-sentence summary of the post, the draft reply, and two action buttons (Approve / Skip). A single reply draft plus context fits comfortably within 4096 characters. Individual messages let Sam evaluate each reply on its own merits — blind batch approval of contextual replies risks posting tone-deaf responses.

**X content batches** arrive as a summary message followed by expandable detail. The summary message contains: product name, number of threads and tweets drafted, the hook line of each thread, and an Approve All / Review Individual / Skip All action set. If Sam taps Review Individual, each draft arrives as a separate follow-up message. This handles the "2 threads + 5 tweets won't fit in one message" constraint by splitting summary from detail rather than cramming everything into one message.

The trade-off: individual reply approvals are noisier than a batch. But distribution replies are the highest-risk output — a bad reply damages brand credibility in a public forum. The 10-second approval cost per reply is justified by the downside risk of blind approval. X content, by contrast, posts from Sam's own account where tone mismatches are less damaging and batch review is acceptable.

### Instrumentation Layer

**Purpose**: Capture the metrics needed to evaluate kill thresholds after the 14-day validation run.

Two metrics matter per the epic's success criteria: qualified leads (≥3 in 14 days) and impressions (≥10K in 14 days). The instrumentation approach is lightweight and manual-augmented:

**Impressions** are tracked automatically. The `reddit-openclaw` skill logs post view counts at scrape time. The `opentweet-x-poster` skill logs impression counts from OpenTweet's analytics API when posting. A daily rollup writes cumulative counts to a simple METRICS.md file in the plugin workspace — no database, no dashboard, just a running tally that Sam reviews alongside the morning digest.

**Qualified leads** require human judgment. A "qualified lead" for spec-doc is different from a qualified lead for Bubls. When Sam approves a reply and it generates a response (tracked via Reddit notification or X reply), Sam tags it as qualified or not in Telegram. The sub-agent appends the tag to METRICS.md. This is intentionally manual — automating lead qualification before understanding what "qualified" means for each product would produce vanity metrics.

The 14-day validation report is a skill invocation, not a dashboard. At the end of the run, a `validation-report` skill reads all four METRICS.md files and produces a summary against the kill thresholds. This skill is not built until day 12 — building reporting infrastructure before there is data to report violates P4.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent Runtime | OpenClaw 2026.5.x | All required primitives already exist — cron, Telegram, Claude API, scraping. Building on OpenClaw means zero new infrastructure. |
| AI Model | Claude Sonnet 4.6 with prompt caching | Reply drafting and content generation are the primary cost drivers. Sonnet 4.6 balances quality and cost. Prompt caching amortizes the BRAND.md and PRODUCT.md context across hourly invocations — estimated 60-70% cache hit rate on repeated context. |
| Reddit Monitoring | OpenClaw free scraping | No Reddit API key required. Free tier scraping is sufficient for monitoring 15-20 subreddits across four products. Rate limiting is OpenClaw's responsibility, not the plugin's. |
| X Posting | OpenTweet ($11.99/month) | Already operational. Handles scheduling, analytics, and rate limiting. The alternative — direct X API access — costs $100/month for Basic tier and requires maintaining OAuth token refresh logic. |
| Approval Channel | Telegram (existing OpenClaw channel) | Already wired into OpenClaw. 4096-character limit is a real constraint but manageable with the summary-first pattern described above. The alternative — a custom web approval UI — would cost 3-5 days of build time for marginal UX improvement over Telegram's inline buttons. |
| Metrics Storage | Flat markdown files (METRICS.md per product) | No database needed for a 14-day validation run tracking two metrics. Flat files are readable, diffable, and require zero infrastructure. If the system graduates to production beyond validation, metrics move to a structured store — but not before. |
| Plugin Format | SKILL.md files (no plugin.json package) | Per P6, skills first. The plugin does not need a build step, a manifest, or versioning during the validation phase. Graduate to full plugin packaging only when submitting to Claw Mart in Task 5. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Four independent sub-agents, not one parameterized agent** | Each product has different subreddits, competitors, and posting cadence. A parameterized agent would need conditional logic for every product-specific behavior. Four flat files are easier to tune independently and impossible to break across products. | Structural repetition across agent files (~30 lines duplicated). Acceptable per P4 — premature abstraction is a bigger risk than 120 lines of similar markdown. |
| **Individual Telegram approvals for Reddit replies, batched summaries for X content** | Reddit replies are high-risk (public, contextual, brand-damaging if wrong). X content is lower-risk (own account, editable). Individual approval ensures no blind posting of contextual replies. Batch summaries keep X content volume manageable. | More Telegram messages per day for Reddit replies (~10-15 vs. ~4 if fully batched). Justified by the asymmetric risk — one bad Reddit reply costs more credibility than 10 extra Telegram notifications cost attention. |
| **BRAND.md shared across products, PRODUCT.md per-product** | Sam's founder voice is consistent across products. Product positioning, pain points, and target audiences are completely different. Splitting voice from product knowledge lets the reply-drafter compose both without duplication. | Sam must maintain 5 context files (1 BRAND.md + 4 PRODUCT.md) and keep them current. Stale context produces stale drafts. Mitigation: the morning digest skill flags when PRODUCT.md has not been updated in 7+ days. |
| **Hourly keyword scan during business hours only (9 AM–6 PM ET)** | Reddit post engagement peaks during US business hours. Scanning overnight produces drafts for threads that have already cooled. Sam is not available for Telegram approvals overnight — drafts would queue and become stale. | Misses overnight posts from non-US timezones. Acceptable for the initial validation run — the 14-day metrics will show whether off-hours coverage matters. Adjustable by editing the cron schedule, not the architecture. |
| **No persistent database — flat file metrics only** | The validation run is 14 days tracking 2 metrics across 4 products. A database adds deployment complexity (Supabase setup, connection management, migration) for ~112 data points. Flat files are readable, diffable, and disposable. | No querying, no aggregation, no dashboards. The validation-report skill must parse markdown files. If the system graduates past validation, metrics storage is the first component to upgrade — but the decision to upgrade is gated behind the kill threshold, not anticipated before it. |
| **Prompt caching on BRAND.md + PRODUCT.md context** | The reply-drafter skill is invoked hourly across 4 products. BRAND.md (~500 tokens) and each PRODUCT.md (~300 tokens) are stable between invocations. Caching this context reduces per-invocation cost by an estimated 60-70% and keeps total Claude API spend within the $50-100/month ceiling. | Cached context that becomes stale (outdated positioning, changed pain points) will produce subtly wrong drafts until the cache expires or the file is updated. Mitigation: PRODUCT.md edits bust the cache automatically since the content hash changes. |
| **Exclude Trendfy, include sam-plugin as the fourth product** | Trendfy's kill date has passed and its status is TBD per the builder profile. Running a distribution agent for a product that may not exist wastes validation slots. sam-plugin is actively maintained and has a clear audience (OpenClaw users). | If Trendfy is revived during the 14-day run, adding it requires creating one PRODUCT.md and one sub-agent file — a 30-minute task, not an architectural change. |
| **Validation-report skill built on day 12, not day 1** | No data exists before the run starts. Building reporting infrastructure speculatively violates P4 and consumes a day of the 4-day foundation build window. By day 12, the data shape is known and the report can be built to match reality, not assumptions. | No mid-run dashboarding. Sam monitors metrics by reading METRICS.md files directly for the first 11 days. Acceptable for a solo founder who is also the only stakeholder. |
| **Skills graduate to plugin.json package only at Task 5 (Claw Mart submission)** | During the validation run, skills change frequently — new keywords, adjusted prompts, tuned output formats. SKILL.md files have zero build step and zero packaging overhead. The plugin.json package format adds versioning, manifest maintenance, and a publish workflow that has no value until the skills are proven and stable. | No version tracking during validation. If a skill change breaks the workflow, rollback is manual (git revert). Acceptable risk for a 14-day experimental run. |

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| **Reddit scraping blocked or rate-limited** | Medium — free scraping depends on OpenClaw's implementation remaining functional | The `reddit-openclaw` skill is the only component that touches Reddit. If scraping breaks, swap to Reddit RSS feeds (public, no auth) inside the skill without changing any sub-agent. The adapter boundary (P1) makes this a one-file change. |
| **Claude API costs exceed $100/month ceiling** | Low — prompt caching and Sonnet 4.6 pricing keep per-call costs around $0.01-0.03 | Monitor cumulative API spend in METRICS.md. If day-7 projection exceeds $100/month, reduce keyword scan frequency from hourly to every 2 hours. The cron schedule is configuration, not architecture. |
| **Telegram approval fatigue — Sam stops reviewing** | Medium — 10-15 messages/day is manageable but could grow with noisy keywords | Keyword tuning in the first 3 days of validation is critical. Start with narrow, high-intent keywords and broaden only if volume is too low. The sub-agent files contain keyword lists directly — tuning is a one-line edit per product. |
| **Reply quality too low for public posting** | Medium — contextual replies are hard to get right without fine-tuning | The reply-drafter skill includes BRAND.md voice constraints and PRODUCT.md domain knowledge. The individual approval flow ensures no reply posts without human review. Quality improves over the 14-day run as Sam rejects bad drafts and the patterns in rejected drafts inform prompt adjustments. |
| **OpenTweet service disruption** | Low — $11.99/month SaaS with established uptime | The `opentweet-x-poster` skill handles errors gracefully and routes failures back to Telegram as "posting failed — retry or skip" messages. No silent failures. |

## Capacity and Cost Model

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| Existing VPS | $0 incremental | Already running OpenClaw |
| OpenTweet | $11.99 | Already subscribed |
| Claude API (Sonnet 4.6) | $30–60 estimated | ~200 reply drafts + ~120 X content drafts per month at $0.01–0.03 per cached invocation |
| **Total** | **$42–72/month** | Well within the $50–100/month ceiling |

Prompt caching is the key cost lever. BRAND.md and the active PRODUCT.md are prepended to every reply-drafter and X content invocation. With a 5-minute cache TTL and hourly invocations, each product's context is cached once per hour and reused for all keyword matches within that hour. Without caching, the estimated cost doubles to $80–140/month.

## Related Documents

- [Analysis](./analysis.md) — Problems, constraints, and open questions driving this architecture
- [Epic](./epic.md) — Scope, task breakdown, success criteria, and kill thresholds
- [Timeline](./timeline.md) — Execution schedule and progress tracking