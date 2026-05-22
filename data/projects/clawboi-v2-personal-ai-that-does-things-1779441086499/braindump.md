# ClawBoi v2 — Personal AI That Actually Does Things

I have all the pieces for a personal AI assistant scattered across 5 repos and none of them talk to each other. Time to unify.

## What I have already

OpenClaw is running on my VPS — it's a Claude agent runtime with Telegram input and 50+ skills (himalaya for email, apple-reminders, wacli for WhatsApp, spotify-player, things-mac, obsidian, notion, 1password, slack, discord, and more). It already maintains daily memory entries at ~/.openclaw/workspace/memory/2026-*.md — there are 20+ entries. It has MEMORY.md, USER.md, SOUL.md, HEARTBEAT.md (proactive checks), DREAMS.md. The Telegram channel works.

ClawBoi repo has the ClawMemory dashboard (newspaper-style HTML/JS that reads memory.json) and the memoryos-brainstorm.md architecture doc. The architecture-rethink docs established: ClawBoi = automation layer, Products = simple frontends.

Bubls is my event discovery + social matching app for Zurich — scrapes Meetup.com, computes match scores against my taste profile, generates weekly digests. Already has its own spec pipeline.

Specview has the analysis pipeline that just scored 93.4% on BullshitBench v2 (rank #2 of 158 models). The calibrated skepticism prompt distinguishes user data from domain claims and flags unverified assumptions. The judge prompt pattern at api/evals/bullshit_bench/judge.py scores responses 0/1/2 on whether they caught nonsense.

Claude memory files across 7 project directories document who I am: full-stack engineer in Zurich finance, side-income goal (not venture-scale), DACH language fluency (DE+FR), 1486 FINMA-licensed firms as addressable market, bottleneck is distribution not building.

## What I want

A unified personal assistant that runs on the existing OpenClaw runtime, takes daily diary input via Telegram, applies a personal bullshit detector to my own thoughts and plans, detects patterns across my memory history, and produces concrete actionable output — not advice, but actual actions dispatched through existing OpenClaw skills.

The daily diary flow: I send a text entry via Telegram (mood, what happened, wins, struggles, what's on my mind, tomorrow's priority). ClawBoi processes it through three lenses: (1) structured memory storage (already does this), (2) personal bullshit detection — adapted from the BullshitBench judge that catches self-deception, sunk-cost fallacies, avoidance patterns, recurring excuses, plans that haven't moved in weeks, and contradictions with past entries, (3) pattern detection against MEMORY.md looking for recurring themes, stalled goals, and drift from stated priorities.

The output should be: validated wins (reinforcement), challenged assumptions (with a BS score), detected patterns ("you said this same thing 3 weeks ago"), and 1-3 concrete next actions. Actions can be dispatched: "shall I set a reminder?" → apple-reminders, "shall I draft that email?" → himalaya, "shall I message X?" → wacli for WhatsApp.

Beyond daily diary, I want it to help with all aspects: career (job search prep, side project prioritization, networking follow-ups), health (MRI follow-up reminders, gym tracking), finances (spending awareness, investment research), social life (Bubls integration for event recommendations, dinner planning, friend outreach). Not as separate apps — as one coherent assistant that knows my full context.

## The bullshit detector for personal thoughts

The BullshitBench judge prompt works by anchoring on a specific known nonsensical element and evaluating whether the pipeline challenged it. The personal version should anchor on specific patterns from my memory history:

- Is this plan real or a wish? (Has it been mentioned 3+ times with no progress?)
- Am I avoiding the hard thing? (Am I planning around the bottleneck instead of through it?)
- Does this contradict what I said last week? (Am I flip-flopping?)
- Am I treating a feeling as a fact? (Am I building strategy on a mood?)
- Is this a sunk cost? (Am I continuing something because I've invested time, not because it's working?)

It should be calibrated like the BullshitBench prompt: challenge domain claims (my rationalizations) but don't challenge user data (my actual experiences and measurements). The guardrail is important — this should feel like a sharp friend, not a therapist or a critic.

## Integration priorities

1. Telegram — already working, primary input/output channel
2. Email (himalaya) — draft and send follow-ups, networking outreach, cold emails
3. Apple Reminders — action items from diary processing
4. WhatsApp (wacli) — if it works, message friends about plans
5. Google Calendar — event blocking for priorities identified in diary
6. Bubls — weekly social event digest fed into the assistant context

Gmail integration would be useful for reading incoming mail and surfacing things that need attention, not just sending. The himalaya skill might already handle IMAP.

## What this is NOT

Not a new codebase — it's skills + prompts + workspace files for the existing OpenClaw runtime. Not a SaaS product — it's my personal tool for one user. Not a therapy bot — it's a structured system with no emotional labor. Not overengineered — following the principle of skills first, SKILL.md files, no build step, iterate fast. Not a replacement for thinking — it catches patterns I miss because I'm inside my own head.

## Open questions

- Does wacli actually work for WhatsApp or is it broken? The memoryos brainstorm noted "WhatsApp broken"
- Should the diary be structured (form-like with mood/wins/struggles fields) or freeform (just talk and let the AI parse)?
- How much of the BS detector should run automatically on every entry vs triggered manually?
- Where does Bubls social data feed in — as a Claw skill, or piped into the weekly digest?
- What's the right home for this — new skills in the existing openclaw workspace, the clawboi repo, or a unified repo?
- How do I handle the cold start — do I seed the pattern detector with my existing 20+ memory entries?