# 🔍 ClawBoi v2 — Personal AI That Does Things — Analysis

## The Problem
OpenClaw runs 50+ skills and stores daily memory, but nothing connects the dots between entries or challenges what goes in. The ClawBoi dashboard reads memory but doesn't write back. Five repos hold fragments of a personal assistant with no unifying intelligence layer — memory exists, reflection doesn't.

## Hard Constraints
- Runtime is OpenClaw on VPS — no new daemon, no new infra, skills-first (SKILL.md files)
- Telegram is the only I/O channel — responses under 4096 chars
- Single user, single consumer — no auth, no multi-tenancy
- Memory format already established: `~/.openclaw/workspace/memory/2026-*.md`
- Claude CLI subprocess timeout: 3600s — diary processing + BS detection + pattern scan must fit
- No Redis, no Postgres, no external queue

## Open Questions
- **Repo home**: New skills in openclaw workspace, clawboi repo, or unified? → Decides file layout for everything else. Recommendation: openclaw workspace (skills-first principle), clawboi repo stays dashboard-only.
- **Structured vs freeform diary**: Form fields constrain input but simplify parsing; freeform is natural but requires reliable extraction. → Freeform with optional tags (e.g. `#win`, `#struggle`) is the middle path.
- **BS detector trigger**: Auto on every entry adds latency and cost; manual means you'll forget. → Auto-light on every entry (contradiction + stall detection), full analysis on `/reflect` command.
- **BS detector ground truth**: BullshitBench works because the judge knows the planted nonsense. Personal BS has no planted element — what's the anchor? → Anchor on **delta against memory history** (stalled plans, contradictions, repeated statements). This is pattern detection, not bullshit detection. Name it honestly.
- **WhatsApp (wacli)**: Brain dump says priority #4 AND "WhatsApp broken." → Verify before scoping. If broken, cut it.
- **Cold start**: 20+ memory entries exist. Seed or start fresh? → Run pattern detection against existing entries once to bootstrap; no special architecture needed.

## Dependencies & Sequencing
- Diary processing skill → before BS/pattern detection (they consume its structured output)
- Memory history retrieval → before pattern detection (needs to read + compare past entries within 3600s timeout)
- Verify wacli → before any WhatsApp action dispatch
- Bubls already has its own pipeline → integration is a read-only feed into weekly digest, not a new skill

## Explicitly Out of Scope
- **Google Calendar integration** — not an existing OpenClaw skill; build only if a SKILL.md proves trivial. Re-scope when diary flow is stable.
- **Gmail IMAP reading** — himalaya may support it, but reading inbound mail is a different trust/filtering problem than sending. Re-scope after send-path works.
- **"All aspects" parity (gym tracking, investment research, spending awareness)** — these are 6 separate domains each needing their own data source. V2 is diary + reflection + action dispatch. Add domains one at a time when the core loop works.
- **ClawMemory dashboard rewrite** — dashboard reads memory.json; leave it. No UI work in this epic.
- **Therapy-adjacent features** — mood trending, emotional analysis, wellness scoring. This is a pattern-matcher, not a journal app. Re-scope never.