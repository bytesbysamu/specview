# Financial Discipline Agent — Stop Bleeding, Start Saving

## The situation

CHF 95k salary in Zurich. Zero side-project revenue. Savings goal of CHF 1k/month — untouched since March. No expense tracking. No spending awareness. New apartment (200m2 + terrace WG) means rent is probably not cheap. Hosting dinners, going out, building social life — all good for wellbeing, all costs money.

I don't even know where my money goes. That's the first problem. Can't fix what you don't measure.

## What I need

A lightweight financial awareness system running on OpenClaw that makes the invisible visible. Not a budgeting app — I won't use it. A passive monitoring + weekly nudge system.

### Daily: Expense logging via diary

When I write my daily diary entry, mention spending naturally: "had dinner at Mesob, CHF 45" or "bought new running shoes CHF 150". The diary-process skill already extracts structured data. Add a spending dimension: extract any amounts mentioned with context.

### Weekly: Spending digest

Every Sunday, the agent summarizes the week:
- Total spent (from diary mentions)
- Breakdown by category (eating out, groceries, transport, shopping, subscriptions)
- Comparison to last week and monthly average
- Savings projection: "At this rate, you'll save CHF X this month vs your CHF 1k target"
- One-line nudge if off track

### Monthly: Net position check

On the 1st, a simple check-in:
- Did I save CHF 1k+ last month? (self-reported via diary or bank statement mention)
- Side project revenue update (CHF 0 until something changes)
- Salary vs expenses trend

### Deal alerts

TooGoodToGo-style monitoring for Zurich:
- Alert via Telegram when good restaurant bags become available near me
- Time-sensitive (bags sell out in minutes)
- SBB supersaver tickets for routes I travel often (Zurich-Bern, Zurich-Geneva)

## What this is NOT

- Not a budgeting app with categories and envelopes — I won't maintain it
- Not connected to my bank — too much friction, too many security concerns
- Not a guilt machine — the tone should be informative, not judgmental
- Not complex — if it takes more than mentioning amounts in my diary, I won't do it

## How it works with existing infrastructure

- diary-process skill already runs daily — extend it to extract CHF amounts with context
- pattern-detect already identifies recurring themes — extend to spending patterns
- action-dispatch already routes to apple-reminders — use for savings transfer reminders
- himalaya already handles email — could forward bank notification summaries if configured

## The simple version

Phase 1 is just: extract spending from diary entries + weekly Telegram digest. That's it. If I use it for a month, expand. If I don't, it was too complex.

## Constraints

- Must be zero-friction — I mention amounts in my diary, the system does the rest
- No bank API integrations — too complex, too risky, not needed for awareness
- Swiss Francs (CHF) as default currency
- Weekly digest via Telegram, not email
- Running on the VPS (OpenClaw on bytesbysamu.cloud)

## Social outreach (from Phase 2)

Bubls handles event discovery. But I also need relationship maintenance integrated into the same system:

- Follow-up reminders: when I meet someone interesting, log it in the diary ("met Alex at the pub quiz, works in fintech"), and the system should remind me to follow up in 3-5 days
- Birthday tracking: store birthdays mentioned in conversations, send a reminder the day before via Telegram
- Network warming: for my top 20 contacts, remind me to reach out if I haven't mentioned them in 30+ days. The diary already captures social interactions — pattern-detect can flag "you haven't mentioned Hanna in 6 weeks"
- This is passive — it reads the diary entries I'm already writing and nudges me. No separate contact management app.