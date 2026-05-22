# Life Discipline Agent — Track Everything, Stall on Nothing

## The pattern (from actual diary data)

March 3: "The plan now is officially promoted in April, in May find new jobs, at least 115,000, till then work on CV and skills, new job by August."
March 4: "Career prep commitment: 2 hours/day starting now."
March 11: "Career prep: 2h/day commitment unclear — no tracking since March 4."
May 22: Career prep absent entirely. May was supposed to be application month. Zero applications.

Same pattern everywhere:
- CHF 1k/month savings goal stated March 11. "No tracker running." Never mentioned again.
- MRI March 4. "Follow-up overdue." Disappeared from diary.
- "Keep writing diary — don't let another 8 days pass." Then 68 days of silence until May 22.
- Gym trial March 3 ("did not feel comfortable"). No gym mention since.

Meanwhile, shipped: BullshitBench 93.4%, 4 OpenClaw skills, VPS deployment, Bubls discovery system — all in days. The engineering dopamine loop works. The life discipline loop doesn't exist.

## What I need

The same CI/CD I have for code, applied to life. Not a planning tool — a tracking + nudging system that reads what I'm already writing in my diary and surfaces what I'm ignoring.

## Financial discipline

### Spending awareness (Phase 1 — immediate)
I already mention spending naturally: "had kebap for dinner" (March 3), "hosting wine & cheese" (March 10). The diary-process skill should extract CHF amounts with context. If I don't mention an amount, infer the category (eating out, groceries, transport).

Weekly Sunday digest:
- Total spent this week
- Top 3 spending categories
- vs last week (↑/↓)
- Savings projection: "at CHF X/month spending, you'll save CHF Y vs your 1k target"

Monthly 1st-of-month check:
- Did I hit CHF 1k savings?
- Self-reported or derived from spending mentions

### Swiss financial calendar (set-and-forget reminders)
These are hard deadlines I shouldn't miss:
- **November 30**: Krankenkasse switch deadline. Remind me 3 weeks before. Link comparis.ch.
- **December 31**: Pillar 3a max contribution. Remind me November 1. Current provider: [need to find out — VIAC? Frankly?]
- **March 31** (or canton deadline): Tax return. Remind me January 15 to start collecting.
- **Quellensteuer**: If I change jobs, I may switch from Quellensteuer to regular taxation. Flag this if job change is detected.

### Deal hunting (Phase 4 — nice to have)
- TooGoodToGo: I already wanted to automate this on March 3 ("maybe we can automate this too ;)"). Alert via Telegram for bags near Walchestrasse 25.
- SBB supersaver: Zurich-Bern, Zurich-Geneva routes.

## Career discipline

### The accountability gap
The diary proves the pattern: I set career goals with conviction, then they vanish within a week. The system needs to catch this automatically.

- If "career", "job", "application", "CV", "interview", "LeetCode" not mentioned in diary for 14 days → nudge: "Career prep has been silent for 2 weeks. Your May application deadline passed."
- If I mention a company or role → track as pipeline entry (applied/interviewing/rejected/ghosted)
- Monthly career momentum: how many career-related actions this month vs last month?

### Skill tracking
- AZ-900 was "in progress" March 3. Status? If not mentioned in 30 days, ask.
- LeetCode/coding practice: any mentions? Count per week.
- Conference/meetup: did I attend anything tech-related this month?

## Health discipline

### What the diary shows
March 3: Knee injury from dancing. MRI booked March 4. Trial gym same day ("did not like it"). Then: nothing. No gym, no MRI follow-up, no physio, no recovery update until May 22 where it's briefly "going well."

The system should track:
- Gym mentions: weekly count. If 0 for 2 consecutive weeks → nudge
- Knee/injury/physio/MRI: if mentioned and then disappears for 30 days → "what happened with your knee?"
- Sleep: if mentioned, track quality/quantity pattern
- Eating out vs cooking ratio: derived from spending data. March 3 I had kebap alone. Is that a pattern?

### Annual health reminders
- Doctor checkup: if "doctor" not mentioned in 12 months → remind
- Dentist: same
- Eye exam: same

## Social discipline

### What's working (don't break it)
March 3: "I felt like I never had a good social circle." March 11: "Social life is exploding. I'm orchestrating group dinners and building event infrastructure." That's a massive 8-day transformation. The system should protect this momentum.

### What to track
- When I mention meeting someone new ("met Alex at pub quiz"), create a follow-up reminder for 3-5 days
- Birthday mentions → store and remind day before
- Network warming: if I mention someone 3+ times across entries (Hannah, Adi, Isabelle, Krisi, Mariana, etc.), they're "inner circle." Flag if not mentioned in 30+ days.
- Event hosting cadence: March had wine night → Ethiopian dinner → pub quiz → BBQ plan. If I go 6 weeks without mentioning hosting, nudge.

### Social health score (weekly)
- How many people did I mention this week?
- How many different social contexts? (1-on-1, group dinner, work, random meetup)
- Am I seeing the same 3 people or expanding?

## Side project discipline

### Revenue reality check
- humaniz.me: live since May. Revenue? If CHF 0 for 3 months → flag: "ship marketing or kill it"
- Trendfy: May 1 kill date passed. What happened? If no diary mention → ask
- Pattern: "you've mentioned 4 projects this month but zero marketing activities"

### The builder-vs-seller gap
March 11: "Am I building or avoiding?" The reality-check already identified this. The discipline agent should track the ratio: hours mentioned building vs hours mentioned selling/marketing/reaching out. If the ratio is 10:0 for a month, that's a problem.

## How it all works

### Input: Diary entries (already happening)
I write naturally to ClawBoi via Telegram. The system extracts everything — spending, people, health, career, projects — from what I'm already saying.

### Output: Weekly discipline digest (Sunday)
One Telegram message:
- 💰 Spent: CHF X (↑12% vs last week). Top: eating out CHF Y.
- 💼 Career: 0 mentions this week. ⚠️ Silent for 14 days.
- 🏋️ Health: 0 gym mentions. Knee status unknown.
- 👥 Social: 4 people mentioned. Follow-up due: Alex (5 days ago).
- 🚀 Projects: 0 marketing activities. humaniz.me revenue: CHF 0.

### Output: Monthly accountability (1st of month)
Full report with trends. Did anything actually improve?

### Output: Proactive nudges (when triggered)
Not scheduled — fired when the pattern detector catches a gap:
- "Career prep absent 14 days."
- "Krankenkasse deadline in 3 weeks."
- "You haven't mentioned Hanna in 6 weeks."
- "Gym: 0 visits, 3rd consecutive week."

## Phases

### Phase 1: Financial awareness + Swiss calendar
- CHF extraction from diary
- Weekly spending digest
- Swiss deadline reminders (Krankenkasse, 3a, tax)
Immediate ROI. Saves real money.

### Phase 2: Career + health tracking
- Career mention tracking + gap detection
- Health/gym tracking
- Proactive nudges for silence gaps

### Phase 3: Social + project tracking
- People extraction + follow-up reminders
- Network warming
- Side project revenue/marketing tracking

### Phase 4: Deal hunting + advanced
- TooGoodToGo alerts
- SBB supersaver monitoring
- Monthly accountability report with trends

## Constraints

- Everything comes from diary entries — zero extra effort
- No bank APIs — spending is self-reported through natural diary writing
- No separate apps — everything in Telegram
- CHF default currency
- Sharp friend tone, not guilt machine
- Running on VPS (OpenClaw on bytesbysamu.cloud)
- Skills-first: SKILL.md files, no build step