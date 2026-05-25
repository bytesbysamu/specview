# OpenClaw Distribution Agent — Brain Dump

## What this is

Use OpenClaw as internal distribution automation for the 4 SaaS products first, then productize what works as a skill pack on Claw Mart / LarryBrain.

## Why OpenClaw, not manual

All the primitives exist in OpenClaw 2026.5.x — Reddit monitoring (free, no API key), X posting (OpenTweet $11.99/mo), Playwright browser automation, cron, Claude API. Nobody has bundled these into a turnkey "SaaS Distribution" workflow. The wrapper/hosting niche is saturated and dying (SimpleClaw wound down from $17k MRR to $0). The gap is productized outcomes, not deployment.

## The internal agent (week 1-2)

4 sub-agents, one per product. Shared BRAND.md (voice, talking points), per-product PRODUCT.md (positioning, pain points, links).

**Cron schedule:**
- 7:30 AM daily: Reddit digest across target subreddits → Telegram
- Hourly during US business hours: keyword scan → draft replies → Telegram for one-tap approval
- 2x daily: X competitor mentions → draft 2 threads + 5 tweets → queue in OpenTweet

**Skills needed:**
- `reddit-openclaw` (read-only, free, no API key)
- `opentweet-x-poster` ($11.99/mo)
- Custom `reply-drafter` skill

**Cost:** ~$50-100/month total (existing VPS + OpenTweet + Claude API with Sonnet 4.6 + prompt caching)

## Productize (weeks 3-6) — Skill Pack on Claw Mart

Bundle: reddit-digest, reddit-reply-drafter, x-mention-monitor, x-thread-drafter, competitor-pulse, launch-amplifier.

**Pricing:** $49 standard, $79 Claude-optimized variant (with cache-retention + 1M context recipes).

**Market proof:** Claw Mart top skill ($9) did 1,381 sales = $12K+. Top persona ($99) did 1,123 sales = $111K+. A "SaaS founder distribution" pack could target $1K-5K/mo within 6 months.

## Vertical agency (months 2-4, only if skill pack works)

"DistributionClaw for AI SaaS founders" — modeled after Roofclaw ($1.8M total).
- $500-800 one-time setup + $99-149/mo managed care
- Cap at 30 clients ($3K-4.5K MRR)
- Differentiation: BullshitBench #2, 4 production SaaS, real track record

## What NOT to build

- Another "one-click OpenClaw deploy" wrapper (SimpleClaw died, Quick Claw overpriced at 5.9x)
- Horizontal "marketing brain" (Claw4Growth already owns this)
- Custom managed hosting without security differentiator

## Kill thresholds

- Internal agent: if <3 qualified leads or <10K impressions in 14 days → fix workflow before productizing
- Skill pack: if <50 sales in 60 days → pivot positioning
- Managed care: if churn >5%/month → raise price, reduce scope

## LarryBrain acquisition (opportunistic only)

Currently $120K asking / $5.1K MRR (1.1x). Only if: skill pack >$1.5K MRR, asking drops <$60K, and clear marketplace thesis. Anything above 1x MRR is overpaying.