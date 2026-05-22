# 🎯 Epic: ClawBoi v2 — Personal AI That Does Things

## Business Value

Five repos hold fragments of a personal assistant — OpenClaw runs the skills, ClawBoi stores memory, Bubls feeds social data, Specview proved the BS-detection prompt pattern — but nothing connects diary input to pattern detection to dispatched action. Memory accumulates without reflection. Plans repeat without challenge. The gap isn't infrastructure (OpenClaw already runs 50+ skills on Telegram); the gap is an intelligence layer that reads what was written, compares it to what was said before, and calls out the delta.

The value is cognitive leverage for a solo founder running multiple projects simultaneously. Every stalled plan that goes undetected costs weeks. Every recurring excuse that goes unchallenged becomes a habit. Every follow-up that doesn't get dispatched as a reminder or email is a missed connection. ClawBoi v2 closes the loop: diary in → reflection applied → action out. No new infrastructure, no new daemon — just skills and prompts on the runtime that already exists.

This is not a product for a market. It is a personal tool for one user whose bottleneck is distribution, not building. The ROI is measured in decisions improved and actions taken, not revenue. If the pattern works, the architecture (skills-first, single-consumer, Telegram I/O) is reusable across any OpenClaw workspace — but that is a future consideration, not a current goal.

## Scope

### What This Epic Covers

- **Diary processing skill** — Accept freeform Telegram input (with optional `#win`, `#struggle` tags), extract structured fields (mood, events, wins, struggles, priorities), persist as memory entry in the established `2026-*.md` format
- **Pattern detection skill** — Read memory history within the 3600s Claude CLI timeout, identify recurring themes, stalled goals (mentioned 3+ times with no progress), contradictions with past entries, and drift from stated priorities
- **Reality check skill** — Adapted from the BullshitBench judge prompt pattern: anchor on memory-history deltas (not planted nonsense), challenge domain claims (rationalizations) while preserving user data (experiences and measurements), output a calibrated BS score per challenged assumption
- **Action dispatch skill** — Convert diary insights into concrete actions routed through existing OpenClaw skills: apple-reminders for follow-ups, himalaya for email drafts, wacli for messages (contingent on verification)
- **Cold-start bootstrap** — One-time pattern detection pass against the existing 20+ memory entries to seed the reflection baseline

### What This Epic Does NOT Cover

- ❌ **Google Calendar integration** — Not an existing OpenClaw skill; re-scope when diary flow is stable
- ❌ **Gmail IMAP reading** — Different trust and filtering problem than sending; re-scope after send-path works via himalaya
- ❌ **Domain-specific tracking (gym, investments, spending)** — Each domain needs its own data source; add one at a time after the core diary→reflection→action loop works
- ❌ **ClawMemory dashboard changes** — Dashboard reads memory.json today; no UI work in this epic
- ❌ **Mood trending or emotional analysis** — This is a pattern-matcher, not a journal app
- ❌ **WhatsApp (wacli) message dispatch** — Brain dump contradicts itself ("priority #4" and "WhatsApp broken"); verify wacli works before scoping any WhatsApp action; if broken, cut entirely
- ❌ **Bubls skill integration** — Bubls has its own pipeline; integration is a read-only feed into the weekly digest context, not a new skill; defer until core loop is proven
- ❌ **Weekly digest aggregation** — Valuable but not MVP; depends on pattern detection running for multiple weeks to have meaningful data

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Diary Processing Skill** — SKILL.md that accepts freeform Telegram text, extracts structured fields (mood, events, wins, struggles, tomorrow's priority), supports optional `#tags`, writes to established memory format | None | — | 2 days | High |
| 2 | **Pattern Detection Skill** — SKILL.md that reads memory history (constrained to fit within 3600s timeout), identifies stalled goals (3+ mentions, no progress), recurring statements, priority drift, and contradictions across entries | Task 1 | — | 3 days | High |
| 3 | **Reality Check Skill** — SKILL.md adapting the BullshitBench judge pattern for personal reflection: anchors on memory-history deltas, scores challenged assumptions (0/1/2), distinguishes rationalizations from facts, runs auto-light on every diary entry and full analysis on `/reflect` command | Task 1, Task 2 | — | 3 days | High |
| 4 | **Action Dispatch Skill** — SKILL.md that takes processed diary output (validated wins, challenged assumptions, detected patterns) and proposes 1–3 concrete actions dispatchable through existing OpenClaw skills (apple-reminders, himalaya); confirms before executing | Task 1 | With Task 2 | 2 days | High |
| 5 | **Cold-Start Bootstrap** — One-time pass of pattern detection against existing 20+ memory entries to establish baseline for recurring themes, stalled goals, and contradiction history | Task 2 | — | 1 day | Low |

## Success Criteria

- ✅ A freeform Telegram message is processed into a structured memory entry and persisted in `~/.openclaw/workspace/memory/` within the established format
- ✅ Pattern detection identifies at least one stalled goal or recurring theme when run against 4+ weeks of memory entries, completing within the 3600s Claude CLI timeout
- ✅ Reality check produces a scored challenge (0/1/2) on at least one assumption per diary entry, without challenging stated experiences or measurements
- ✅ Action dispatch proposes a concrete next action routable to an existing OpenClaw skill (apple-reminders or himalaya) and executes on confirmation
- ✅ All output fits within Telegram's 4096-character response limit
- ✅ All new capabilities are delivered as SKILL.md files in the OpenClaw workspace — no new daemons, no new repos, no build step
- ✅ End-to-end flow (diary entry → structured storage → pattern check → reality check → proposed action) completes in a single Telegram interaction

## Related Documents

- [Analysis](./analysis.md) — Problems, constraints, and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design, skill structure, and prompt patterns
- [Timeline](./timeline.md) — Status tracking and delivery milestones