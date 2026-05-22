# Job Search Autopilot — From CHF 95k to 115k+

## The problem

It's May 22. The plan was: March-April prep, May applications. Zero applications sent. Zero. The career prep that was supposed to be 2 hours daily before work didn't survive past March 15. The promotion gave CHF 600 — insulting. The AZ-900 cert, the LeetCode practice, the CV updates, the company research — all planned, none sustained.

I'm not lazy. I shipped BullshitBench (93.4%, rank #2/158), deployed ClawBoi on a VPS, built 4 new skills — all in two days. The problem is that job searching is a sustained grind with no dopamine hits, and I keep choosing the interesting engineering work over the boring career work.

## What I need

An autonomous job search agent running on OpenClaw that does the sustained work I won't do manually. It should:

- Scrape Swiss job boards daily for roles matching my profile: full-stack (Python/Flask, Angular/TypeScript), finance domain preferred, Zurich, CHF 115k+ (or roles where that's negotiable)
- Sources: LinkedIn Jobs (passive scraping — no "open to work" signal), SwissDevJobs.ch, jobs.ch, Indeed Switzerland, Glassdoor Switzerland
- Smart ranking: score each role by tech stack overlap, domain relevance (finance = +50%), company size, estimated salary range, commute
- Weekly digest via Telegram: top 5-7 roles, each with a 2-line summary, why it matches, and estimated salary
- For each role I approve: generate a tailored CV variant (I have a base CV) emphasizing relevant experience, draft a cover letter matching the company's tone
- Application tracking: which roles I've applied to, when, status (applied/interview/rejected/ghosted), follow-up reminders
- Pattern detection: "you've approved 0 roles this week" or "3 applications pending your review for 5 days"

## What I have

- OpenClaw with himalaya (email), apple-reminders, Telegram, Claude CLI
- My base CV (somewhere in my files — need to locate or write)
- 2+ years finance domain experience in Zurich
- Full-stack skills: Python, Flask, Angular, TypeScript, Docker, CI/CD
- German + French fluency (can target DACH roles others can't)
- Azure cert in progress (AZ-900)

## What I explicitly don't want

- LinkedIn "open to work" badge — I'm employed and it needs to stay discreet
- Mass applying to everything — quality over quantity, 5-7 targeted applications per week max
- Another planning doc — I need the agent to DO the work, not plan it
- Manual daily effort from me — the agent scrapes, filters, ranks. I review and approve. That's it.

## The accountability mechanism

The diary-process + reality-check skills already catch stalled goals. The job search agent should feed into them: "job search: 0 applications this week, 0 roles reviewed" shows up in the pattern detector. The system I built should hold me accountable to using it.

## Constraints

- Must run on the VPS (OpenClaw on bytesbysamu.cloud) so it works even when my Mac is off
- Claude CLI as the AI provider (already configured)
- All external actions (sending applications, emails) require my confirmation via Telegram
- No paid APIs unless absolutely necessary — prefer scraping public listings
- The base CV needs to exist before any of this works — generating it is step 0