# Distribution Agent — The Missing Piece

## What this is

An OpenClaw-powered distribution agent that monitors Reddit, Hacker News, and the web for conversations where our products are relevant — then drafts replies, surfaces leads, and queues content for human approval via Telegram. Product-agnostic: works for any SaaS in the portfolio. Zero additional cost — runs on the existing VPS, uses existing Claude CLI backend, no paid APIs.

This is the thing that turns 4 deployed products into 4 revenue-generating products. Engineering is done. Distribution is the bottleneck. This agent IS the distribution.

## Why this matters now

The data is unambiguous:

- 68.9% of TrustMRR startups make $0-$1K/month. We're in that bucket.
- 78% of cases on TrustMRR show revenue outpaced follower growth. Audience is not the bottleneck — showing up in the right conversations is.
- $1M+ founders with <50 X followers (Tarkle, Doors Delivered, MyCater) all run one product at scale. They don't have audiences. They have SEO + presence in the right places.
- 47% of top-200 TrustMRR startups run zero ad pixels. They grow organically.
- The Unicorne weekly winners pattern: 7 of 14 grew via niche SEO + community embedding. TikTok and paid ads are nearly absent from breakout growth.

We have 4 products deployed, signups trickling in, and zero systematic distribution. Every day we don't show up in relevant Reddit threads, HN discussions, and search results is revenue left on the table.

## What exists already

OpenClaw is running on VPS (72.62.150.237) with:
- Telegram channel connected (bot token active, owner ID verified)
- Claude CLI backend (claude-sonnet-4-6 via claude-code, bypass permissions)
- Cron scheduling (already running routines-heartbeat-dispatcher every 30 min)
- 14 custom skills (diary, cooking, routines, spending extraction, etc.)
- Docker container with persistent state

What's missing: skills for Reddit monitoring, HN monitoring, reply drafting, and content queuing.

## The zero-cost stack

Every component is free or already paid for:

| Component | How | Cost |
|-----------|-----|------|
| Reddit monitoring | `reddit-openclaw` skill — appends `.json` to Reddit URLs, no API key, no OAuth | $0 |
| Hacker News monitoring | HN Algolia API — `hn.algolia.com/api/v1/search` — public, no key, no rate limit | $0 |
| Web monitoring | F5Bot — free alerts for keywords across Reddit + HN + Lobsters, email delivery | $0 |
| Reply drafting | Claude CLI (already running, already paying for) | $0 incremental |
| Content delivery | Telegram (already connected) | $0 |
| Cron scheduling | OpenClaw native cron (already running heartbeat) | $0 |
| Hosting | Existing VPS (already running 5 products + OpenClaw) | $0 incremental |

Total additional cost: **$0/month**

X/Twitter is excluded intentionally. The research shows X followers don't correlate with revenue. Reddit + HN + SEO is where the signal is. We add X later only if we need it.

## Architecture

One workspace, one agent, product context loaded from files.

```
openclaw/
├── workspace/
│   ├── IDENTITY.md          (already exists — Claw)
│   ├── BRAND.md             (NEW — voice, guardrails, anti-patterns)
│   └── products/
│       ├── specview.md       (positioning, ICP, keywords, subreddits)
│       ├── humanizme.md      (positioning, ICP, keywords, subreddits)
│       ├── speedback.md      (positioning, ICP, keywords, subreddits)
│       └── trendfy.md        (positioning, ICP, keywords, subreddits)
├── skills/
│   ├── reddit-monitor/       (NEW — scan subreddits, return relevant posts)
│   ├── hn-monitor/           (NEW — scan HN for keyword matches)
│   ├── reply-drafter/        (NEW — take post + product context → draft reply)
│   ├── distribution-digest/  (NEW — daily summary of opportunities via Telegram)
│   └── f5bot-processor/      (NEW — parse F5Bot email alerts into actionable items)
```

NOT sub-agents. One agent with multiple skills. Simpler, cheaper, easier to debug.

## Product context files

Each product file contains:

```markdown
# Product Name
## One-liner
## URL
## ICP (who buys this)
## Pain points (what they search for)
## Keywords to monitor
## Subreddits to watch
## HN keywords
## Competitor names to track
## Reply tone (how to talk about this product)
## What NOT to say
```

Product-agnostic: add a new .md file and the agent picks it up. Remove one and it stops monitoring. No code changes.

## Daily workflow

**Morning (07:30 Europe/Zurich) — already a cron slot:**
1. Reddit monitor scans all target subreddits (via .json endpoint)
2. HN monitor scans Algolia API for keyword matches
3. Agent reads each post, scores relevance (0-10) against product context files
4. Posts scoring 7+ get a drafted reply
5. Distribution digest sent to Telegram:
   - "3 Reddit opportunities found"
   - Each with: subreddit, title, score, draft reply, one-tap approve link
6. Sam approves or edits via Telegram, agent posts (or queues for manual posting)

**Continuous (via F5Bot):**
- F5Bot emails arrive for keyword matches
- f5bot-processor skill parses, deduplicates against morning scan
- High-signal matches get immediate Telegram notification

**Weekly (Sunday 21:00 — already a cron slot):**
- Distribution scorecard: how many opportunities found, how many replied to, any responses/leads generated
- Adjust keywords based on what's working

## Target subreddits and keywords

**specview.dev:**
- Subreddits: r/ClaudeAI, r/cursor, r/programming, r/ProductManagement, r/SaaS, r/cscareerquestions, r/LocalLLaMA
- Keywords: "PRD generator", "spec driven", "braindump to spec", "product requirements", "Claude Code planning", "AI spec", "vibe coding problems", "spec kit"
- Competitors: ChatPRD, Miro AI, ClickUp Brain, Linear AI

**humaniz.me:**
- Subreddits: r/ChatGPT, r/ArtificialIntelligence, r/college, r/GradSchool, r/EssayWriting, r/studytips
- Keywords: "AI detector", "Turnitin flagged", "GPTZero false positive", "humanize AI text", "AI writing detector", "essay flagged AI"
- Competitors: Undetectable AI, StealthWriter, HumanizerAI, Lunchbreak

**speedback.pro:**
- Subreddits: r/webdev, r/web_design, r/freelance, r/webdesign, r/Wordpress
- Keywords: "website feedback tool", "client feedback", "visual bug report", "website QA", "bug reporting widget"
- Competitors: BugHerd, Marker.io, Usersnap, SeggWat

**trendfy.me:**
- Subreddits: r/femalefashionadvice, r/malefashionadvice, r/streetwear, r/findfashion
- Keywords: "AI outfit", "virtual try on", "AI styling", "outfit generator", "fashion AI"
- Competitors: Provamoda, Fit It On, Outfii

**F5Bot keywords (200 keyword limit, free):**
humaniz.me, humanize AI, AI detector bypass, Turnitin AI, specview, PRD generator, spec driven development, braindump to spec, speedback, website feedback tool, visual bug report, trendfy, AI outfit, virtual try on, AI styling, Undetectable AI, StealthWriter, ChatPRD, BugHerd, Marker.io, Provamoda

## Reply guardrails (BRAND.md)

The research is clear on what works and what gets you banned:

**Do:**
- Be a human who built something, not a marketer
- Lead with value — answer the question first, mention tool second
- Disclose: "I built X" or "Full disclosure, this is my tool"
- Match the subreddit's tone (r/programming is technical, r/college is casual)
- Only reply when the product genuinely solves the person's stated problem

**Don't:**
- Never use superlatives ("best", "revolutionary", "game-changing")
- Never reply to more than 2 threads per subreddit per week (spam threshold)
- Never post the same reply twice
- Never reply without adding value beyond "try my tool"
- Never use AI-generated replies without editing (ironic for a humanizer product)
- Never engage in competitor bashing

**Reply template structure:**
1. Acknowledge the problem (1 sentence)
2. Share relevant experience or insight (1-2 sentences)
3. Mention the tool naturally, with disclosure (1 sentence)
4. No CTA, no link unless asked

## Show HN and content calendar

The distribution agent handles monitoring. Content creation is manual but agent-assisted:

**Monthly Show HN (specview only):**
- Agent drafts the post based on latest features
- Best slots: Friday 12-15 UTC or Sunday 16-19 UTC
- Talk like an engineer, link to GitHub, free try-it, no signup
- Reality check: median score is 2, 200 competing posts/day. Plan for failure, treat GitHub repo as the durable asset.

**Weekly content (agent-drafted, human-approved):**
- 1 Reddit value-post per product per week (rotate across subreddits)
- Agent drafts based on trending discussions found in morning scan

## SEO landing pages (manual, agent-informed)

The agent surfaces what people search for. We build pages targeting those exact queries:

Priority pages for specview.dev:
1. "PRD from braindump" — exact match for the core use case
2. "AI spec generator for Cursor / Claude Code" — ride the Spec Kit wave
3. "spec-driven development template" — category keyword

These are static pages, not agent-generated. The agent's job is to surface which keywords appear most in the threads it monitors, so we know what to build next.

## Success metrics

**Week 1:** Agent running, morning digest arriving in Telegram, at least 10 relevant posts surfaced per day across all products.

**Week 2:** First 5 reply drafts approved and posted. At least 1 reply gets >5 upvotes or a response.

**Month 1:** 20+ replies posted across Reddit/HN. At least 1 measurable click-through to a product. Keyword frequency data informing first SEO page.

**Month 3:** One product crosses $500 MRR. If none do, the distribution message is wrong — pivot positioning, not the agent.

## What this is NOT

- Not a bot that auto-posts. Every reply gets human approval via Telegram.
- Not a content farm. Quality over quantity — 2-3 genuine replies per week beats 20 spammy ones.
- Not a replacement for the product being good. If the product doesn't solve a real problem, no amount of distribution fixes that.
- Not an X/Twitter strategy. X comes later, only if Reddit/HN proves the message works.

## Implementation order

1. Write BRAND.md + 4 product context files (30 min)
2. Build reddit-monitor skill (2-3 hours — .json endpoint parsing + relevance scoring)
3. Build hn-monitor skill (1-2 hours — Algolia API is simpler)
4. Build reply-drafter skill (1-2 hours — prompt engineering against product context)
5. Build distribution-digest skill (1 hour — format results for Telegram)
6. Wire cron to 07:30 daily slot (30 min — extend existing heartbeat dispatcher)
7. Set up F5Bot keywords (15 min — web form)
8. Test for 3 days, tune relevance scoring
9. Start approving and posting replies

Total build time: ~1 day. This is not a month-long project. The skills are simple — the hard part was knowing what to build, and the research already answered that.