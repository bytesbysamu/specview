# 🏗️ Solution Architecture: Distribution Agent — The Missing Piece

## Architecture Overview

The Distribution Agent is an OpenClaw-native skill suite that transforms four idle SaaS products into four systematically distributed products. The core insight is that distribution at this stage is a monitoring and drafting problem, not a posting or automation problem. The agent watches two platforms — Reddit and Hacker News — scores conversations against product context files, drafts guardrail-compliant replies, and delivers a morning digest to Telegram for human approval. The entire system runs on the existing VPS within the existing OpenClaw workspace, using zero new infrastructure and zero paid APIs.

The architecture follows a file-driven composition model. Product context lives in markdown files. Brand guardrails live in a single shared file. Skills read these files at invocation time, meaning the monitoring surface changes the moment a file is added or removed — no skill edits, no redeployments, no code changes. This makes the agent product-agnostic by construction, not by abstraction.

The skill chain is linear and orchestrated, not event-driven. A single orchestrator skill — the distribution digest — calls the Reddit monitor, the HN monitor, and the reply drafter in sequence, then formats and delivers the result. There are no message queues, no inter-skill events, no coordination problems. One agent, five skills, one daily cron trigger, one Telegram message. The simplicity is the architecture.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | All external HTTP calls (Reddit `.json`, HN Algolia, Telegram) are isolated within the skill that owns them. No skill imports another skill's fetch logic. The Claude CLI backend is the only AI adapter, already wired through OpenClaw. |
| P4 — No Speculative Abstractions | One orchestrator skill calls three worker skills in sequence. No generic "platform monitor" base skill, no plugin registry, no abstract scoring interface. Reddit and HN have different APIs, different response shapes, and different scoring heuristics — they stay separate. |
| P6 — Skills First | Every capability is a `SKILL.md` file. No `openclaw.plugin.json` packaging, no build step. Skills iterate in minutes, not hours. Graduate to a full plugin only if skills hit real limits — and nothing in this scope pushes those limits. |
| P6 — References as Source of Truth | BRAND.md and product context files are the single source for voice, guardrails, keywords, and subreddit lists. Skills reference these files — they never inline the same rules. Changing a guardrail in BRAND.md changes every draft the reply drafter produces. |
| P6 — Channel-Aware Output | The distribution digest formats output for Telegram specifically: respects the 4096-character message limit, uses Telegram-compatible markdown, and splits across multiple messages when the opportunity set is large. |
| P7 — File Size & Structure | Each skill is a single `SKILL.md` under 200 lines. Each product context file is a single markdown document. BRAND.md is one file. No nesting, no inheritance, no shared templates. |

## Component Design

### Product Context Files

**Purpose:** Define what to monitor, where to monitor, and how to talk about each product. These files are the configuration layer that makes the agent product-agnostic.

Each product file lives at `workspace/products/<product-name>.md` and contains a fixed set of sections: one-liner, URL, ICP description, pain points, monitored keywords, target subreddits, HN-specific keywords, competitor names, reply tone guidance, and explicit anti-patterns. The schema is intentionally flat — no frontmatter, no YAML, no structured data format. Skills parse section headers to extract what they need. This keeps product files human-readable and human-editable, which matters because Sam is the author, the editor, and the sole consumer.

The directory itself is the registry. The Reddit monitor skill reads every `.md` file in the products directory and unions their subreddit lists. The HN monitor does the same for keyword lists. Adding a fifth product means creating one file. Removing Trendfy means deleting one file. The next cron run picks up the change automatically because skills enumerate the directory at invocation time, never at configuration time.

Four product files ship at launch: `specview.md`, `humanizme.md`, `speedback.md`, and `trendfy.md`. Trendfy's inclusion depends on the status resolution flagged in [Analysis](./analysis.md) — if archived, its file is simply not created.

### BRAND.md — Voice Guardrails

**Purpose:** Encode the reply rules that protect against ban-worthy behavior and ensure every draft sounds like a founder, not a marketer.

BRAND.md lives at `workspace/BRAND.md` and defines five concerns: the reply structure template (acknowledge → insight → mention with disclosure → no CTA), the hard prohibitions (no superlatives, no duplicate replies, no competitor bashing), the per-subreddit tone calibration guidance, the weekly reply cap (two threads per subreddit per week), and the disclosure phrasing variants ("I built X" / "Full disclosure, this is my tool").

The reply drafter skill loads BRAND.md on every invocation. Because it is a separate file from the product contexts, guardrails apply uniformly regardless of which product the draft is for. A guardrail change propagates to all products immediately — there is no per-product override mechanism, intentionally. Consistency of voice across the portfolio is a feature, not a limitation.

### Reddit Monitor Skill

**Purpose:** Scan target subreddits for posts where a product is genuinely relevant, score them, and return only high-signal opportunities.

The skill exploits Reddit's public `.json` endpoint — appending `.json` to any subreddit URL returns structured post data without authentication, without OAuth, and without API keys. This is the critical architectural enabler: zero-cost, zero-setup Reddit monitoring. The trade-off is that this endpoint provides only the current page of posts (roughly the top 25 in "new" or "hot" sorting), not historical search. This is acceptable because the agent runs daily — a 24-hour scan window aligned with the subreddit's natural post velocity means minimal missed posts for the target subreddits, which are medium-traffic communities, not front-page defaults.

The skill reads every product context file, extracts the union of target subreddits, and fetches each subreddit's `.json` endpoint. For each post, it evaluates relevance against the originating product's keywords, ICP description, and pain points, producing a score from 0 to 10. The scoring is performed by the Claude CLI backend — the skill describes the scoring criteria in its prompt, and the LLM evaluates semantic relevance rather than relying on keyword matching alone. This is important because valuable opportunities often use different vocabulary than the exact monitored keywords.

Posts scoring below 7 are discarded. Posts scoring 7 and above are passed to the reply drafter. The threshold of 7 is a starting heuristic — too low floods the digest with marginal matches, too high misses opportunities. The threshold lives in the skill file itself and can be tuned after the first week of operation based on digest quality.

Deduplication is handled by a file-based seen-posts store. After each run, the skill appends scored post IDs (Reddit's `t3_` prefixed identifiers) to a JSON file at `workspace/state/seen-reddit.json`. Before scoring, the skill checks incoming posts against this file and skips any already seen. The file is pruned of entries older than 30 days on each run to prevent unbounded growth. JSON-file-based state is appropriate here because there is exactly one consumer (the daily cron), no concurrent writes, and the dataset is small (hundreds of entries, not thousands).

### HN Monitor Skill

**Purpose:** Scan Hacker News for keyword and competitor mentions relevant to the product portfolio.

The skill uses the HN Algolia API at `hn.algolia.com/api/v1/search`, which is public, requires no API key, and has no documented rate limit for reasonable usage. Unlike Reddit's page-limited endpoint, the Algolia API supports full-text search with time-range filtering, making it inherently better suited to a daily scan pattern. The skill queries for each product's keywords and competitor names, filtered to the last 24 hours.

HN's structure differs from Reddit in a way that affects scoring. Reddit posts have a subreddit context that signals intent (someone posting in r/webdev about "feedback tools" is likely a practitioner). HN posts lack this contextual signal — a mention of "AI detector" could be a technical discussion, a product launch, a policy debate, or a tangential comment. The HN monitor compensates by weighting story type (Show HN and Ask HN posts score higher for product relevance than general submissions) and comment depth (top-level comments expressing a need score higher than deep-thread tangents).

Deduplication follows the same pattern as the Reddit monitor: a file-based store at `workspace/state/seen-hn.json` keyed by HN story ID. The two state files are deliberately separate rather than unified because the platforms have different ID schemes, different pruning needs, and independent failure modes. Merging them would create coupling for zero benefit.

The Reddit and HN monitors are designed to run sequentially within the orchestrator skill's single Claude CLI invocation, not in parallel. OpenClaw skills execute within a single Claude CLI session, which means parallelism would require multiple subprocess invocations — adding complexity for a marginal time saving. Sequential execution is simpler and still fits comfortably within the 3600-second timeout budget.

### Reply Drafter Skill

**Purpose:** Transform a scored post and its matched product context into a reply draft that follows BRAND.md guardrails.

The reply drafter takes three inputs: the post content (title, body, top comments for context), the matched product's context file, and BRAND.md. It produces a structured output block containing the draft reply text, the disclosure phrasing used, and a confidence note explaining why this product is relevant to this specific post.

The drafting prompt enforces the four-part reply structure defined in BRAND.md: acknowledge the problem, share a relevant insight or experience, mention the tool with founder disclosure, and close without a call to action. The prompt also receives the subreddit or HN context so it can calibrate tone — technical and specific for r/programming, conversational for r/college, Show-HN-native for Hacker News.

A critical design choice: the drafter produces one reply per post, matched to the single most relevant product. Even if a post matches keywords for multiple products, the drafter picks the strongest match and drafts for that product only. Multi-product replies would violate the "be a human, not a marketer" guardrail — no real founder promotes four products in one comment. The scoring step in the monitor skills already associates each post with its highest-scoring product, so this is resolved before the drafter is invoked.

The drafter does not attempt to evaluate whether a reply would be well-received. That judgment stays with Sam during Telegram review. The drafter's job is to produce a guardrail-compliant starting point that is faster to approve or edit than to write from scratch.

### Distribution Digest Skill — The Orchestrator

**Purpose:** Wire the full pipeline together, format results for Telegram, and deliver the morning digest.

The distribution digest is the only skill that the cron system invokes directly. It is the orchestrator: it calls the Reddit monitor, then the HN monitor, then the reply drafter for each qualifying post, then formats everything into a Telegram-deliverable digest. This single-entry-point design means the cron configuration is trivial — one skill name in one cron slot — and the execution order is explicit in one place.

Telegram's 4096-character message limit is a hard constraint that shapes the digest format. The skill uses a message-splitting strategy: it builds the digest content, measures length, and splits at opportunity boundaries (never mid-post) when the content exceeds the limit. Each message is a self-contained batch of opportunities. The first message includes a summary header ("12 opportunities across 4 products, 8 with draft replies"). Subsequent messages are continuation batches.

Each opportunity in the digest contains: platform badge (Reddit or HN), subreddit or HN context, post title as a link, relevance score, matched product name, and the draft reply text. The format uses Telegram-compatible markdown — bold for headers, inline code for scores, plain links rather than embedded markdown links (which Telegram renders inconsistently).

The skill delivers via the existing Telegram bot connection in OpenClaw. The delivery mechanism is already proven across 14 existing skills — this is not new infrastructure. The digest skill's only Telegram-specific concern is the message splitting logic described above.

### Cron Wiring

**Purpose:** Trigger the daily digest at 07:30 Europe/Zurich using the existing OpenClaw cron infrastructure.

The OpenClaw workspace already runs a `routines-heartbeat-dispatcher` every 30 minutes. The distribution digest wires into this existing scheduler, not alongside it. The heartbeat dispatcher already handles time-of-day routing — it checks the current time and dispatches the appropriate routine. Adding the distribution digest means adding one entry to the dispatcher's schedule: trigger `distribution-digest` at the 07:30 slot.

The 07:30 slot is chosen so the digest arrives before Sam's morning review window. The full pipeline — four products across two platforms, plus reply drafting — must complete within the Claude CLI's 3600-second timeout. The timeout budget breaks down approximately as follows: Reddit monitoring across roughly 15 unique subreddits (fetching `.json` endpoints is fast — network time dominates, estimated under 120 seconds total), HN monitoring across keyword sets (Algolia queries are sub-second, estimated under 60 seconds total), and reply drafting for qualifying posts (the most expensive step, as each draft requires an LLM generation pass — estimated 30–60 seconds per draft, budget for up to 15 drafts at 900 seconds). Total estimated pipeline time: under 1200 seconds, leaving substantial headroom within the 3600-second limit.

If the pipeline exceeds the timeout on a given day — perhaps due to an unusually high volume of qualifying posts — the digest delivers whatever was completed before the cutoff. Partial delivery is better than no delivery. The deduplication store still records all posts that were fetched and scored, so the next day's run does not re-surface them.

### Deduplication State Layer

**Purpose:** Prevent the same post from appearing in consecutive digests.

The deduplication layer is the simplest component and the most important for daily usability. Without it, the digest would resurface the same high-scoring posts every morning until they fall off the subreddit's front page or the Algolia time window.

Two JSON files in `workspace/state/` — one for Reddit, one for HN — store post identifiers with timestamps. The write pattern is append-on-score: every post that the monitor fetches and scores (regardless of whether it meets the threshold) is recorded. This means even a post that scores 4 today won't be re-evaluated tomorrow, which is correct because relevance doesn't change — the post's content is static.

The pruning strategy is date-based: entries older than 30 days are removed at the start of each run. Thirty days is generous — Reddit posts older than a week are rarely worth replying to, and HN threads go cold within 48 hours. The 30-day window exists to handle edge cases where a post resurfaces (crosspost, meta-discussion) rather than to support late replies.

The state files are not backed up. If they are lost, the only consequence is one digest with duplicate entries — an annoyance, not a failure. This is an intentional trade-off: the state is cheap to regenerate (one day of duplicates) and not worth the complexity of a backup mechanism.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Agent Runtime | OpenClaw workspace (existing) | Already running on VPS with Telegram, cron, and Claude CLI wired. Zero new infrastructure. |
| Skill Format | SKILL.md files | P6 compliance — skills first, no build step, iterate in minutes. Graduate to plugin packaging only if skills hit real limits. |
| AI Backend | Claude CLI via OpenClaw (`claude-sonnet-4-6`) | Already running, already paid for. Handles relevance scoring and reply drafting. No separate Anthropic SDK call needed. |
| Reddit Data | Public `.json` endpoint | Zero-cost, zero-auth. Trade-off: page-limited (top ~25 posts), no historical search. Acceptable for daily cadence on medium-traffic subreddits. |
| HN Data | HN Algolia API (`hn.algolia.com/api/v1/search`) | Zero-cost, zero-auth, supports time-range filtering. Better search capability than Reddit's endpoint. |
| Delivery | Telegram via existing bot connection | Already connected, already proven across 14 skills. 4096-char limit handled by message splitting. |
| Scheduling | OpenClaw cron via `routines-heartbeat-dispatcher` | Already running every 30 minutes. Distribution digest adds one time-slot entry. |
| State | File-based JSON (`workspace/state/`) | Two files for deduplication. No Redis, no database. Appropriate for single-consumer, single-writer, small-dataset state. |
| Configuration | Markdown files (`workspace/products/*.md`, `workspace/BRAND.md`) | Human-readable, human-editable. Directory enumeration is the registry. Add a file to add a product. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Single agent with skills, not sub-agents | One Claude CLI session per run. No inter-agent coordination, no message passing, no routing logic. Debugging is reading one session log, not correlating across multiple agent invocations. | Cannot parallelize Reddit and HN monitoring within a single run. Sequential execution adds time but stays well within the 3600s budget. |
| Reddit `.json` endpoint, not Reddit API with OAuth | Zero setup, zero cost, zero API key management. The endpoint returns the same data as the API for the "current posts" use case. | Limited to ~25 posts per subreddit per fetch. No search, no historical access, no comment-level scanning. Acceptable because daily cadence on medium-traffic subreddits means few posts are missed. |
| LLM-based relevance scoring, not keyword matching | Semantic relevance catches opportunities that use different vocabulary than monitored keywords. "My professor flagged my essay" is relevant to humaniz.me even though none of those words are in the keyword list. | Scoring consumes Claude CLI time per post. Budget allows for it within the timeout, but a spike in subreddit activity could push scoring time up. Mitigated by the threshold — only posts above 7 proceed to drafting. |
| Score threshold of 7 (out of 10) | Balances signal density against opportunity coverage. Below 7 floods the digest with marginal matches. Above 7 misses edge cases. | Starting heuristic — may need tuning. Too high means missed opportunities in the first week. Too low means Sam ignores the digest because of noise. Tunable in the skill file without architectural changes. |
| One reply per post, strongest product match only | Authenticity guardrail — no real founder promotes four products in one comment. Single-product replies are indistinguishable from genuine community participation. | Misses the rare post where two products are equally relevant. Acceptable loss — Sam can manually draft a second reply for the other product if the opportunity is obvious. |
| File-based deduplication, not in-memory state | Persists across cron runs without a database. Survives container restarts. Simple enough to inspect manually (it is a JSON file). | File I/O on every run, but the dataset is small (hundreds of entries) and the I/O is negligible compared to network and LLM time. No concurrent-write protection needed because only one cron run executes at a time. |
| Telegram message splitting at opportunity boundaries | Never splits mid-opportunity. Each message is independently readable. The first message contains the summary header so Sam knows the total scope even before scrolling. | Long digests (many qualifying posts) produce multiple Telegram messages, which may push earlier messages out of view. Mitigated by the summary header in the first message and by the score threshold keeping the total opportunity count manageable. |
| Sequential skill execution within orchestrator | Explicit execution order in one place. No coordination primitives, no race conditions, no partial-failure recovery logic. The orchestrator is a linear script: fetch → score → draft → format → deliver. | Cannot exploit parallelism between Reddit and HN fetching. Total pipeline time is the sum, not the max. Stays within budget and avoids the complexity of managing multiple concurrent Claude CLI sessions. |
| Separate dedup files per platform | Reddit and HN have different ID schemes (`t3_` prefixed vs numeric), different lifecycle characteristics (Reddit posts stay relevant longer than HN threads), and independent failure modes. Merging them adds coupling for zero benefit. | Two files to manage instead of one. The management overhead is negligible — both follow the same prune-on-read pattern. |
| Two-per-subreddit-per-week reply cap in BRAND.md | Research-backed spam threshold. Reddit communities and moderators notice patterns. Two replies per week per subreddit is sustainable indefinitely without triggering scrutiny. | Caps the distribution volume. With ~15 target subreddits across four products, the cap allows roughly 30 replies per week total — sufficient for the "2–3 genuine replies per week" target in the [Epic](./epic.md). |
| No auto-posting, Telegram review only | Reddit requires OAuth for programmatic posting. HN has no write API. Beyond the technical constraint, human review is a feature — it prevents brand-damaging replies and maintains the authentic voice that makes founder replies effective. | Manual copy-paste from Telegram to platform. Slower than auto-posting, but the volume (2–3 per week per product) makes this a minutes-per-day task, not a bottleneck. |
| Daily cron at 07:30, not continuous monitoring | Aligns with existing cron infrastructure. Morning delivery fits Sam's review cadence. Batch processing is simpler than event-driven monitoring and stays within the Claude CLI timeout model. | Misses posts that spike and die within hours (e.g., a viral HN thread that's cold by next morning). Acceptable trade-off — the target subreddits are not high-velocity enough for this to be a significant loss. |

## Failure Modes and Mitigations

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Reddit `.json` endpoint returns 429 or changes format | Reddit monitor produces no results for that run | Skill detects non-200 response and reports "Reddit unavailable" in the digest rather than failing silently. Sam sees the gap and can check manually. No retry logic — next day's run tries again. |
| HN Algolia API unavailable | HN monitor produces no results | Same pattern — report in digest, no retry, next day's run recovers. |
| Claude CLI timeout reached mid-pipeline | Partial digest — some posts scored, some drafts generated, some not | Orchestrator delivers whatever completed. Dedup store still records fetched posts. Next day does not re-process them. Partial delivery is better than no delivery. |
| Dedup state file corrupted or deleted | One day of duplicate entries in the digest | Files are regenerated on next run. No backup needed — the cost of one duplicate digest is trivial. |
| Product context file has malformed sections | Skill reads wrong keywords or subreddits | Skills parse section headers — a missing or renamed header means that section is skipped, not that the skill crashes. The digest would show fewer results for that product, which is a visible signal that something is misconfigured. |
| Telegram bot connection drops | Digest generated but not delivered | OpenClaw's existing Telegram error handling applies. The digest content is logged in the Claude CLI session, so Sam can retrieve it manually if Telegram delivery fails. |

## Scaling Path

The architecture is designed for the current concrete case: four products, two platforms, one daily run, one consumer. If the distribution thesis proves out and the scope expands, the natural scaling points are:

**More products** — Add a `.md` file. No architectural change. The timeout budget is the practical ceiling: each additional product adds subreddits and keywords, increasing fetch and scoring time. Roughly eight to ten products fit within the 3600-second budget before optimization is needed.

**More platforms** — Each new platform (Lobsters, IndieHackers, Product Hunt) is a new monitor skill following the same pattern. The orchestrator adds one more skill call. No architectural change, just a new skill file and a new dedup state file.

**Higher frequency** — Moving from daily to twice-daily means adding a second cron slot. The dedup layer already handles this correctly — posts seen in the morning run won't resurface in the evening run. No architectural change.

**Auto-posting** — If Reddit OAuth is ever set up, the reply drafter's output is already structured for programmatic submission. The architectural change is a new "reply-poster" skill that the orchestrator calls after Telegram approval, not a redesign of the pipeline. This is explicitly out of scope per the [Epic](./epic.md) but the architecture does not foreclose it.

## Related Documents

- [Analysis](./analysis.md) — Open questions on Trendfy status, Reddit `.json` endpoint reliability, and write-API constraints that shaped scope decisions
- [Epic](./epic.md) — Scope definition, task breakdown, and success criteria this architecture is designed to fulfill
- [Timeline](./timeline.md) — Task sequencing and delivery tracking