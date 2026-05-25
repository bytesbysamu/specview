# Implementation Guide: Distribution Agent — The Missing Piece

## Overview
This epic delivers a five-skill OpenClaw agent that monitors Reddit and Hacker News for conversations relevant to four SaaS products (SpecView, Humaniz.me, Speedback, Trendfy), drafts guardrail-compliant replies, and delivers a scored morning digest to Telegram. Tasks sequence linearly: Task 1 creates the product context files and brand guardrails that every downstream skill consumes; Tasks 2 and 3 build the Reddit and HN monitor skills in parallel, both reading from the product files; Task 4 adds the reply drafter that takes scored posts plus context and produces draft replies; Task 5 wires the orchestrator digest skill into the existing 07:30 cron slot and handles Telegram formatting. The entire system runs on the existing VPS with zero new infrastructure and zero paid APIs.

## Shared Pre-flight
- Confirm the OpenClaw workspace root directory and verify that the existing cron dispatcher at the 07:30 slot is accessible and accepting new routine entries
- Verify the Telegram bot connection is active by checking one of the 14 existing skills that use it
- Confirm Claude CLI is operational and responding within the workspace (model: claude-sonnet-4-6)
- Trendfy status: app.trendfy.me returns 504 (backend down). Include its context file for monitoring (costs nothing) but mark reply drafting as disabled until the app is fixed — no point driving traffic to a broken product
- SpecView is live at specview.dev and app.specview.dev. Speedback is live at speedback.pro. Both confirmed accessible.
- Create the directory workspace/state/ if it does not already exist, for deduplication JSON files
- Create the directory workspace/products/ if it does not already exist, for product context markdown files
- Verify that Reddit public .json endpoints are accessible from the VPS by fetching any subreddit URL with .json appended and confirming a 200 response

---

## Task 1: Product Context Files + BRAND.md  [Effort: 0.5 days]

### What
Define the four product markdown files and a shared BRAND.md that together serve as the single source of truth for what to monitor, where to monitor, and how to draft replies. Every downstream skill reads these files at invocation time, making the agent product-agnostic by construction — adding or removing a product requires only adding or removing a file.

### Files
- **Create**: workspace/products/specview.md — product context defining ICP, pain points, keywords, target subreddits, HN keywords, competitors, reply tone, and anti-patterns for SpecView
- **Create**: workspace/products/humanizme.md — product context for Humaniz.me following the same section structure
- **Create**: workspace/products/speedback.md — product context for Speedback following the same section structure
- **Create**: workspace/products/trendfy.md — product context for Trendfy following the same section structure (skip if Trendfy is archived)
- **Create**: workspace/BRAND.md — shared voice guardrails defining the four-part reply structure, hard prohibitions, per-subreddit tone calibration, the two-per-subreddit-per-week reply cap, and disclosure phrasing variants

### Steps
1. Create the workspace/products/ directory and establish the fixed section schema for product context files: one-liner, URL, ICP description, pain points, monitored keywords, target subreddits, HN-specific keywords, competitor names, reply tone guidance, and explicit anti-patterns. Use flat markdown headers for each section — no frontmatter, no YAML.
2. Write workspace/products/specview.md with all sections populated using real product details. Include three to five target subreddits where SpecView's ICP is active, five to ten monitored keywords, and at least two named competitors.
3. Write workspace/products/humanizme.md following the same structure. Target subreddits should include communities where AI detection and academic writing are discussed. Include keywords relevant to AI humanization and detector bypass concerns.
4. Write workspace/products/speedback.md following the same structure. Target subreddits should focus on developer tooling, code review, and feedback communities.
5. Write workspace/products/trendfy.md following the same structure, targeting trend analysis and market research communities. If the pre-flight status check determined Trendfy is archived, skip this file entirely.
6. Write workspace/BRAND.md defining five sections: the reply structure template (acknowledge problem, share insight, mention tool with founder disclosure, no CTA), the hard prohibitions (no superlatives, no duplicate replies, no competitor bashing), per-subreddit tone calibration guidance, the weekly reply cap of two threads per subreddit per week, and three to four disclosure phrasing variants such as "I built X" and "Full disclosure, this is my tool."

### Verify
- Confirm that each product file in workspace/products/ contains all required section headers and that no section is empty
- Confirm that workspace/BRAND.md contains the four-part reply structure, the hard prohibitions list, and the two-per-subreddit-per-week cap
- Confirm that removing one product file from workspace/products/ reduces the file count and that no other file references it by hardcoded name
- Manually verify that the union of all target subreddits across product files yields approximately 15 unique subreddits

---

## Task 2: Reddit Monitor Skill  [Effort: 1 day]

### What
Build an OpenClaw SKILL.md that scans target subreddits via public .json endpoints, scores each post for relevance against the matched product context using the Claude CLI backend, deduplicates against a file-based seen-posts store, and returns only posts scoring 7 or above. This skill runs within the orchestrator's Claude CLI session and must complete its portion well within the 3600-second timeout.

### Files
- **Create**: workspace/skills/reddit-monitor/SKILL.md — the Reddit monitoring skill definition containing the scanning logic, scoring criteria prompt, threshold configuration, and deduplication instructions
- **Create**: workspace/state/seen-reddit.json — initialized as an empty JSON object, populated at runtime with Reddit post IDs (t3_-prefixed) and timestamps

### Steps
1. Create the workspace/skills/reddit-monitor/ directory and write SKILL.md with a clear skill description, input expectations, and output format.
2. Define the scanning logic section of the skill: read every .md file in workspace/products/, extract the target subreddits from each file, compute the union of all subreddits, and fetch each subreddit's public .json endpoint by appending .json to the subreddit URL with "new" sorting.
3. Define the deduplication section: before scoring, load workspace/state/seen-reddit.json, prune entries older than 30 days based on their stored timestamp, and skip any post whose t3_-prefixed ID already appears in the file.
4. Define the pre-filter step: before invoking Claude for scoring, check each un-seen post's title and body against the originating product's monitored keywords using case-insensitive substring matching. Discard posts that contain zero keyword matches — these are not worth spending Claude tokens on. This pre-filter typically eliminates 80% of fetched posts and keeps the daily scan well within token budget.
5. Define the scoring section: for each pre-filtered post, instruct the Claude CLI to evaluate semantic relevance against the originating product's keywords, ICP description, and pain points, producing a score from 0 to 10. Describe the scoring criteria clearly in the skill prompt so the LLM evaluates semantic relevance rather than performing simple keyword matching.
6. Define the threshold and output section: discard posts scoring below 7, and for each post scoring 7 or above, output a structured block containing the post ID, subreddit, title, URL, body excerpt, relevance score, and matched product name.
7. Define the state persistence section: after scoring, append all fetched post IDs (regardless of score) to workspace/state/seen-reddit.json with the current timestamp.
8. Initialize workspace/state/seen-reddit.json as an empty JSON object.

### Verify
- Confirm that workspace/skills/reddit-monitor/SKILL.md exists, is under 200 lines, and references workspace/products/ for subreddit extraction
- Confirm that the skill references workspace/state/seen-reddit.json for deduplication and specifies the 30-day pruning rule
- Confirm the scoring threshold of 7 is explicitly stated in the skill file
- Run the skill manually within the OpenClaw workspace and verify that it fetches at least one subreddit's .json endpoint and returns structured output without errors

---

## Task 3: HN Monitor Skill  [Effort: 0.5 days]

### What
Build an OpenClaw SKILL.md that queries the Hacker News Algolia API for keyword and competitor mentions from product context files, scores relevance with weighting for story type and comment depth, and deduplicates against a separate file-based store. This skill runs sequentially after the Reddit monitor within the orchestrator.

### Files
- **Create**: workspace/skills/hn-monitor/SKILL.md — the HN monitoring skill definition containing query construction, scoring criteria with HN-specific weighting, and deduplication instructions
- **Create**: workspace/state/seen-hn.json — initialized as an empty JSON object, populated at runtime with HN story IDs and timestamps

### Steps
1. Create the workspace/skills/hn-monitor/ directory and write SKILL.md with a clear skill description, input expectations, and output format matching the Reddit monitor's output structure for consistency.
2. Define the query construction section: read every .md file in workspace/products/, extract the HN-specific keywords and competitor names from each file, and build Algolia API queries to hn.algolia.com/api/v1/search filtered to the last 24 hours.
3. Define the deduplication section: load workspace/state/seen-hn.json, prune entries older than 30 days, and skip any story whose numeric HN ID already appears in the file.
4. Define the scoring section: instruct the Claude CLI to score each post 0 to 10, weighting Show HN and Ask HN posts higher for product relevance than general submissions, and weighting top-level comments expressing a need higher than deep-thread tangents. Apply the same threshold of 7 as the Reddit monitor.
5. Define the state persistence section: append all fetched story IDs to workspace/state/seen-hn.json with timestamps after scoring.
6. Initialize workspace/state/seen-hn.json as an empty JSON object.

### Verify
- Confirm that workspace/skills/hn-monitor/SKILL.md exists, is under 200 lines, and references workspace/products/ for keyword extraction
- Confirm that the skill queries hn.algolia.com/api/v1/search with a 24-hour time-range filter
- Confirm that workspace/state/seen-hn.json is separate from seen-reddit.json and uses numeric HN story IDs as keys
- Run the skill manually and verify it returns structured output for at least one HN query without errors

---

## Task 4: Reply Drafter Skill  [Effort: 0.5 days]

### What
Build an OpenClaw SKILL.md that takes a scored post, its matched product context file, and BRAND.md, then generates a single guardrail-compliant reply draft following the four-part structure: acknowledge problem, share insight, mention tool with founder disclosure, no CTA. The drafter produces one reply per post matched to the single strongest product, ensuring authenticity.

### Files
- **Create**: workspace/skills/reply-drafter/SKILL.md — the reply drafting skill definition containing the drafting prompt, BRAND.md integration, tone calibration logic, and output format

### Steps
1. Create the workspace/skills/reply-drafter/ directory and write SKILL.md with a clear skill description specifying that it receives a scored post object and produces a draft reply block.
2. Define the input section: the skill receives the post content (title, body, top comments for context), the platform and subreddit or HN context, the relevance score, and the matched product name.
3. Define the context loading section: the skill reads the matched product's context file from workspace/products/ and loads workspace/BRAND.md for guardrails. Both files are loaded on every invocation to ensure changes propagate immediately.
4. Define the drafting prompt section: instruct the Claude CLI to follow the four-part reply structure from BRAND.md — acknowledge the problem, share a relevant insight or experience, mention the tool with founder disclosure, and close without a call to action. Include the subreddit or HN context so the LLM calibrates tone appropriately.
5. Define the single-product constraint: even if multiple products match, the drafter uses only the highest-scoring product. This constraint is already resolved upstream by the monitor skills, but the drafter should not attempt multi-product replies.
6. Define the output format: each draft block contains the reply text, the disclosure phrasing used, and a confidence note explaining why this product is relevant to this specific post.

### Verify
- Confirm that workspace/skills/reply-drafter/SKILL.md exists, is under 200 lines, and references both workspace/products/ and workspace/BRAND.md
- Confirm the skill enforces the four-part reply structure (acknowledge, insight, mention with disclosure, no CTA) in its drafting prompt
- Confirm the output format includes the reply text, disclosure phrasing, and confidence note
- Run the skill manually with a sample post and verify the generated draft does not contain superlatives, CTAs, or competitor bashing

---

## Task 5: Distribution Digest + Cron Wiring  [Effort: 0.5 days]

### What
Build the orchestrator SKILL.md that calls the Reddit monitor, HN monitor, and reply drafter in sequence, formats all scored opportunities and drafts into a Telegram-friendly digest respecting the 4096-character limit, delivers via the existing Telegram bot connection, and wires the full pipeline into the 08:00 Europe/Zurich cron slot through the existing heartbeat dispatcher.

### Files
- **Create**: workspace/skills/distribution-digest/SKILL.md — the orchestrator skill that sequences the three worker skills, formats the digest, handles message splitting, and delivers to Telegram
- **Create**: workspace/state/reply-counts.json — initialized as an empty JSON object, tracks replies posted per subreddit per week to enforce the two-per-subreddit-per-week cap from BRAND.md
- **Modify**: the existing routines-heartbeat-dispatcher configuration — add one entry to trigger distribution-digest at the 08:00 Europe/Zurich slot

### Steps
1. Create the workspace/skills/distribution-digest/ directory and write SKILL.md as the single orchestrator entry point that the cron system invokes.
2. Define the orchestration sequence: first invoke the Reddit monitor skill and collect its scored post output, then invoke the HN monitor skill and collect its output. Before invoking the reply drafter, load workspace/state/reply-counts.json and check each qualifying post's subreddit against the weekly cap (2 replies per subreddit per week per BRAND.md). Skip drafting for subreddits that have hit the cap. Then invoke the reply drafter skill once per qualifying post passing each post with its matched product context. After drafting, do NOT auto-increment reply-counts — Sam increments manually when he actually posts a reply (by editing the JSON or via a future approval flow).
3. Define the digest formatting section: build the digest content with a summary header line stating the total opportunity count, product breakdown, and draft count. For each opportunity, include a platform badge (Reddit or HN), the subreddit or HN context, the post title as a clickable link, the relevance score, the matched product name, and the draft reply text.
4. Define the message splitting strategy: measure the formatted digest length and split at opportunity boundaries — never mid-post — when content exceeds 4096 characters. The first message always contains the summary header. Subsequent messages are self-contained continuation batches. Use Telegram-compatible markdown: bold for headers, inline code for scores, plain links.
5. Define the delivery section: send each message through the existing OpenClaw Telegram bot connection. If the Telegram connection fails, log the digest content to the Claude CLI session output so it can be retrieved manually.
6. Define the error reporting section: if the Reddit monitor reports unavailability (non-200 response), include a "Reddit unavailable" line in the digest rather than failing silently. Apply the same pattern for HN monitor failures. If the pipeline hits the Claude CLI timeout, deliver whatever was completed.
7. Locate the existing routines-heartbeat-dispatcher schedule configuration and add one entry that triggers the distribution-digest skill at the 07:30 Europe/Zurich time slot.

### Verify
- Confirm that workspace/skills/distribution-digest/SKILL.md exists and references all three worker skills by their correct skill directory paths
- Confirm the heartbeat dispatcher configuration now includes an 08:00 entry pointing to the distribution-digest skill
- Run the full pipeline manually and verify that a Telegram message arrives containing the summary header and at least one formatted opportunity
- Verify that a digest exceeding 4096 characters splits into multiple Telegram messages at opportunity boundaries, with the summary header in the first message