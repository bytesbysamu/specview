# ClawBoi v2 Phase 2 — Unfair Advantage Expansion

## Where we are

Phase 1 is deployed: diary-process, pattern-detect, reality-check, action-dispatch skills running on OpenClaw with Claude CLI (Sonnet 4.6) via Telegram. The diary pipeline works — it extracts structured entries, detects stalled goals across 68 days of gaps, and calls out wish-vs-plan patterns with a 0/1/2 BS score. Action dispatch routes to apple-reminders and himalaya for email.

The foundation is solid. Now I need it to actually do things that create measurable advantage.

## Job search automation

The job market is bad right now. Manual applying is a losing strategy — too slow, too generic. I need:

- Job scraping: monitor LinkedIn, SwissDevJobs, Indeed Switzerland for roles matching my profile (full-stack, Python/Flask, Angular/TypeScript, finance domain, Zurich, CHF 115k+ target)
- Smart filtering: rank matches by fit (tech stack overlap, domain relevance, company size, salary range). Don't show me everything — show me the top 5 per week
- CV tailoring: for each shortlisted role, generate a tailored version of my CV emphasizing the relevant experience. I have a base CV — the AI adjusts emphasis, not content
- Application drafting: draft cover letter / application message per role. Match the company's tone and the role's requirements
- Send after approval: confirm-before-execute like action-dispatch. Show me the draft, I approve, it sends via himalaya or the platform's apply mechanism
- Track pipeline: which roles I applied to, when, status (applied/interview/rejected/ghosted). Pattern detection can flag "you've been ghosted by 5 companies this month — follow up"

Key constraint: I'm employed. This needs to be discreet — no public LinkedIn "open to work" signals. The scraping should be passive.

## Financial monitoring

Practical money saving, not investment advice:

- TooGoodToGo: monitor for good deals near me in Zurich. Alert via Telegram when a bag from a good restaurant becomes available. This is time-sensitive — bags sell out in minutes
- Spending awareness: I should log expenses in the diary and the system should track monthly totals, flag trends ("you've spent CHF 400 on eating out this month, up 30% from last month")
- Swiss-specific: monitor SBB supersaver tickets for routes I travel often. Alert when cheap tickets drop

## Social outreach

Bubls handles event discovery. But I also need:

- Follow-up reminders: when I meet someone interesting, log it in the diary, and the system should remind me to follow up in 3-5 days
- Birthday tracking: store birthdays from conversations, send a reminder the day before
- Network warming: for my top 20 contacts, remind me to reach out if I haven't contacted them in 30+ days

## OpenClaw configuration improvements

The current setup works but could be better:

- SOUL.md needs updating with the expanded role (not just diary, but career/finance/social assistant)
- AGENTS.md needs orchestration for the new skills
- The heartbeat should do useful proactive checks: new job postings matching my profile, TooGoodToGo availability, overdue follow-ups
- Memory structure: should diary entries, job search logs, and expense logs be in the same memory/ dir or separate?
- Workspace files (USER.md, IDENTITY.md) should reflect the full picture of who I am and what I'm optimizing for

## Constraints

- Single user, Telegram I/O, Claude CLI provider
- Confirm-before-execute on ALL external actions (emails, applications, messages)
- No public signals about job searching
- Budget-conscious: this runs on a VPS, not a data center. Keep it lightweight
- Skills-first: SKILL.md files, no build step, iterate by editing markdown