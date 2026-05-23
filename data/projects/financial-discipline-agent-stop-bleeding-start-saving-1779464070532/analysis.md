# 🔍 Financial Discipline Agent — Stop Bleeding Start Saving — Analysis

## The Problem
Sam nets CHF 2'442/month after fixed costs but burns ~CHF 980 on restaurants — 40% of discretionary income — leaving nothing for the CHF 1'000/month savings target. Four months of bank data confirm a CHF 772 net loss instead of a CHF 4'000 gain. The core fix is behavioral (cook more, eat out less), but willpower alone hasn't worked, so the system needs to provide daily accountability via Telegram diary extraction.

## Hard Constraints
- All input comes from unstructured Telegram diary entries — zero extra apps, zero manual logging
- All output via Telegram (< 4'096 chars per message)
- Self-reported spending only — no bank API, no Plaid, no CSV import
- OpenClaw skill system (SKILL.md files, no build step, runs on bytesbysamu.cloud)
- CHF is the only currency tracked

## Open Questions
- **Diary extraction reliability** — "had dinner at Parsaco CHF 25" is parseable, but what about days with no CHF mention? Does no mention = CHF 0 spent, or = missing data? These produce opposite behaviors.
- **TooGoodToGo alerts** — brain dump says "alert me when bags are available." TGTG has no public API; this requires reverse-engineering or a scraper. Is this a real requirement or a nice-to-have that blocks Phase 1?
- **Scheduled messages vs reactive skills** — morning nudges and Sunday scorecards need cron triggers, not diary-reactive skills. Does OpenClaw support cron-triggered skills today, or is that new infra?
- **Social spending: budget or track-only?** — brain dump sets a CHF 50/week social budget AND a CHF 75/week eating-out budget. Are these separate pools, or does a CHF 55 Kennedy's visit hit both?
- **"Worth it" judgment** — the CHF 280 Mesob dinner is called a good investment. Who decides what's worth it — the user tags it, or the agent guesses? Guessing wrong erodes trust fast.

## Dependencies & Sequencing
- Diary NLP extraction is load-bearing — every feature (spending, cooking, social, health) depends on it working reliably. Build and validate this alone before anything else.
- Gamification (points, levels, streaks) requires persistent state — needs a storage decision (JSON file? SQLite?) before implementation.
- Weekly/monthly reports require cron — confirm OpenClaw supports this before promising scheduled nudges.
- Cooking suggestions with real grocery prices require an external data source that doesn't exist in the current stack.

## Explicitly Out of Scope
- **Bubls integration** — Bubls was never deployed. Coupling a new system to a dead project guarantees neither ships. Re-scope when Bubls has a running backend.
- **Recipe suggestions with live grocery prices** — needs Migros/Coop price data (no public API). A static list of 10 cheap meals is fine; dynamic pricing is a separate project.
- **Career tracking and salary negotiation** — different problem, different data source, different cadence. Track it in diary analysis if trivial, but don't design features around it.
- **Investing advice (Phase 4)** — premature by definition. The system hasn't proven it can help save CHF 1 yet. Re-scope after 3 consecutive months hitting CHF 1'000 savings.
- **TooGoodToGo real-time alerts** — no public API; scraper maintenance is a second job. Track TGTG purchases from diary mentions instead. Re-scope if an official API launches.
- **Health/gym tracking** — one mention in 4 months of diary data. Not enough signal to build features around. Let diary extraction passively capture it; don't build UI or nudges.