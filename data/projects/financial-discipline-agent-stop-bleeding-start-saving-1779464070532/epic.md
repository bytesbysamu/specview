# 🎯 Epic: Financial Discipline Agent — Stop Bleeding Start Saving

## Business Value

Four months of Migros Bank statements reveal a CHF 4'772 gap between reality and target: Sam lost CHF 772 (Jan–Apr 2026) instead of saving the intended CHF 4'000. The single largest controllable leak is restaurant spending — averaging CHF 980/month, consuming 40% of the CHF 2'442 discretionary budget left after CHF 4'049 in fixed obligations (two rents, two insurance premiums, phone). Cooking five days per week instead of eating out daily recovers an estimated CHF 530/month, covering more than half the CHF 1'000 monthly savings target with one behavioral shift.

Willpower alone has not produced this shift. Four months of data prove the pattern is structural, not occasional — five Kennedy's visits, five Mama Shelter visits in a single month, daily Parsaco and kiosk purchases. The intervention must be system-enforced: extract spending from diary entries Sam already writes, surface the numbers daily before they compound, and gamify the cooking habit so the feedback loop is immediate rather than monthly-bank-statement delayed. The agent is the accountability partner Sam does not currently have.

The financial co-pilot costs nothing incremental to operate — it runs as OpenClaw skills on the existing bytesbysamu.cloud VPS, reads from Telegram diary entries Sam already writes, and responds within Telegram where Sam already lives. There is no new app to open, no manual logging step, no subscription. The only investment is build time, and the payback period is under two months: CHF 530/month recovered against roughly ten days of development effort.

## Scope

### What This Epic Covers

- **Diary spending extraction** — parse unstructured Telegram diary entries for CHF amounts, meal type (cooked vs. ate out), and spending category; this is the load-bearing foundation for every downstream feature
- **Persistent spending ledger** — store daily entries, running totals, streaks, and points across sessions; enable aggregation for daily, weekly, and monthly reporting
- **Daily morning budget nudge** — proactive Telegram message showing cooking streak, eating-out budget remaining for the week (CHF 75 cap), and savings pace for the month
- **Weekly Sunday scorecard** — gamified Telegram report covering cooking ratio, spending vs. budget, savings trajectory, points earned, and current level
- **Cooking quick-reference** — static list of 10 cheap rotation meals and a reactive skill that suggests one when asked "what should I cook"; no live grocery prices

### What This Epic Does NOT Cover

- ❌ **TooGoodToGo real-time alerts** — no public API exists; scraper maintenance is a second project. Diary mentions of TGTG purchases will be passively extracted by the spending skill, but proactive bag-availability alerts are out of scope
- ❌ **Live grocery price suggestions** — Migros/Coop have no public pricing API; the cooking reference uses a static curated list, not dynamic pricing
- ❌ **Bank API or CSV import** — all spending is self-reported through diary entries; no Plaid, no statement parsing
- ❌ **Bubls integration** — Bubls has no running backend; coupling to it guarantees neither project ships. Re-scope when Bubls is deployed
- ❌ **Social follow-ups and network warming** — Phase 3 concern; this epic focuses exclusively on the food spending leak
- ❌ **Career tracking and salary negotiation** — different data source, different cadence; not part of the food-spending fix
- ❌ **Health and gym tracking** — one gym mention in four months of diary data; insufficient signal to build features around
- ❌ **Investing advice** — premature until three consecutive months hit the CHF 1'000 savings target
- ❌ **Monthly accountability report** — Phase 2 deliverable; weekly scorecard provides sufficient feedback cadence for MVP
- ❌ **Swiss financial calendar reminders** — useful but not part of the daily food-spending feedback loop; Phase 2

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Diary Spending Extraction Skill** — parse diary entries for CHF amounts, meal type (cooked / ate out / TGTG), and spending category; handle absent-amount days as CHF 0 spent; validate against 4 months of known bank data | None | — | 3 days | High |
| 2 | **Spending Ledger & Persistence** — storage layer (JSON file or SQLite) for daily entries, weekly/monthly aggregates, cooking streaks, and gamification points; thread-safe reads/writes | Task 1 | — | 2 days | High |
| 3 | **Daily Morning Budget Nudge** — cron-triggered Telegram skill delivering cooking streak length, weekly eating-out spend vs. CHF 75 budget, and monthly savings pace | Tasks 1, 2 | Parallel with Task 4 | 2 days | High |
| 4 | **Weekly Sunday Scorecard** — cron-triggered Telegram skill with cooking ratio, spending breakdown, points earned, level name, and savings projection vs. CHF 1'000 target | Tasks 1, 2 | Parallel with Task 3 | 2 days | High |
| 5 | **Cooking Quick-Reference Skill** — curated list of 10 cheap meals (≤ CHF 8/serving); reactive skill responds to "what should I cook" with a suggestion and estimated cost | None | Parallel with Tasks 1–4 | 1 day | Low |

## Success Criteria

- ✅ Diary entries containing CHF amounts are extracted with ≥ 90% accuracy when validated against known bank-statement transactions from Jan–Apr 2026
- ✅ Meal type classification (cooked / ate out / TGTG) produces correct labels for diary entries containing explicit meal references
- ✅ Daily nudge message arrives via Telegram every morning and stays under 4'096 characters
- ✅ Weekly scorecard delivers every Sunday with accurate spend-vs-budget, cooking ratio, and savings projection
- ✅ Restaurant spending drops below CHF 500/month within 60 days of deployment (down from CHF 980 baseline)
- ✅ Monthly savings rate reaches ≥ CHF 500 within 60 days (halfway to CHF 1'000 target, proving the behavioral loop works before Phase 2 investment)
- ✅ All skills run as SKILL.md files on OpenClaw — no build step, no external dependencies beyond Telegram

## Related Documents

- [Analysis](./analysis.md) — Bank data breakdown and problem identification driving this epic
- [Solution Architecture](./architecture.md) — Skill design, state persistence, cron triggers, and Telegram message formatting
- [Timeline](./timeline.md) — Task status and delivery tracking