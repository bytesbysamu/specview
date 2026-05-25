# 🔍 OpenClaw Distribution Agent — Analysis

## The Problem
Sam runs 4 SaaS products with zero systematic distribution — posting is manual and inconsistent. OpenClaw already has the primitives (Reddit scraping, X via OpenTweet, Playwright, cron, Claude API) but nobody has wired them into a repeatable distribution workflow. The plan is dogfood first, then sell what works as a Claw Mart skill pack and optionally a managed vertical agency.

## Hard Constraints
- Solo founder — no support staff, no delegation for managed care clients
- Telegram 4096-char limit for all approval flows
- OpenClaw 2026.5.x skill system (SKILL.md first, plugin later)
- No Reddit API key — free scraping only (rate/reliability risk)
- OpenTweet at $11.99/mo is the only paid external dependency
- Claude Sonnet 4.6 + prompt caching for cost control (~$50-100/mo ceiling)

## Open Questions
- **Which 4 products?** Profile lists 5 (spec-doc, humanize-me, Bubls, Trendfy, sam-plugin). Trendfy has a passed kill date. Is it dead or zombie? Pick 4 now.
- **Shared BRAND.md across what?** A humanizer, an event app, a fashion tool, and a dev tool have no shared voice. Is BRAND.md Sam's personal voice, or per-product? If shared, it'll produce generic slop.
- **Telegram approval UX for batched content?** "2 threads + 5 tweets" won't fit in one 4096-char message. Approve individually (noisy) or batch with truncation (blind approval)?
- **Who services 30 managed-care clients?** $99-149/mo × 30 = real support load. Solo founder + 4 products + skill pack maintenance. Where does the time come from?
- **Do `reddit-openclaw` and `opentweet-x-poster` exist today?** If not, week 1-2 is building skills, not the agent.

## Dependencies & Sequencing
- `reddit-openclaw` and `opentweet-x-poster` skills must exist before the internal agent can run — verify or build first
- Internal agent must produce measurable results (14-day kill threshold) before skill pack work starts — but week 1-2 build + 14-day eval = 4 weeks minimum, not 2
- Skill pack pricing requires Claw Mart listing mechanics — submission process, review time, revenue split unknown
- Managed care (months 2-4) depends on skill pack traction ($1.5K MRR gate) — no parallel work justified

## Explicitly Out of Scope
- **LarryBrain acquisition** — opportunistic sidebar, not a workstream. Re-scope trigger: skill pack crosses $1.5K MRR AND asking drops below $60K
- **Vertical agency buildout** — months 2-4, gated behind skill pack sales. No design work until gate is met
- **`launch-amplifier` and `competitor-pulse` skills** — named in the pack but undefined. Spec them when skill pack work begins, not now
- **Playwright browser automation** — mentioned as an OpenClaw primitive but no workflow uses it. Don't build integrations for it yet