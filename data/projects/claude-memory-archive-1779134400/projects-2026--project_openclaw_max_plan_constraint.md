---
name: Claude Code Max plan has overage disabled — hard constraint for agent wrappers
description: Sam's Claude Code Max subscription has `overageDisabledReason: "org_level_disabled_until"`. Any tool that wraps Claude Code with large system prompts will exhaust the 5-hour bucket and hit an unrecoverable "out of extra usage" wall because overage cannot absorb the overflow.
type: project
---

Sam's Claude Code Max plan has **overage billing disabled at the org level**. Confirmed directly by the `rate_limit_event.rate_limit_info` payload in a `claude -p --output-format stream-json` response on 2026-04-11:

```
"rateLimitType": "five_hour",
"overageStatus": "rejected",
"overageDisabledReason": "org_level_disabled_until",
"isUsingOverage": false
```

Consequence: the moment a request would spill past Sam's 5-hour rolling bucket, Anthropic rejects it immediately with `"You're out of extra usage. Add more at claude.ai/settings/usage and keep going."` — there is no overage safety net.

**Why it matters for agent wrappers:** Tools that embed Claude Code as a subprocess (OpenClaw, similar) typically inject a large `--append-system-prompt` (30k+ tokens) plus enable MCP tool bundling. Even a trivial `claude -p "hello"` with default args costs ~16k cached tokens just from Claude Code's own baseline. Stack those together and each turn is 45–60k input tokens. On a Max plan the 5-hour bucket survives only 1–3 such turns.

**How to apply:**
- When setting up any tool that wraps Claude Code, default to aggressive prompt minimization: `systemPromptOverride` to a tiny string, `--tools ""`, `--disable-slash-commands`, `--exclude-dynamic-system-prompt-sections`. See `~/Projects/openclaw/SETUP-NOTES.md` for the concrete OpenClaw knobs.
- If a tool can't be tuned below ~10–15k tokens/turn, warn Sam upfront that it will burn the 5-hour bucket and have no fallback.
- Do NOT recommend "just wait for the bucket to reset" as a solution — overage being disabled means there's no graceful degradation.
- If Sam ever decides to enable overage, this constraint no longer applies and agent wrappers become trivially usable. He has not done this as of 2026-04-11.
- Relevant codepath in OpenClaw: `src/agents/cli-runner/execute.ts` spawns `claude` via a process supervisor with the args defined in `extensions/anthropic/cli-backend.ts`. `--tools ""` and `--exclude-dynamic-system-prompt-sections` measured a 65% drop in cached tokens (16,237 → 5,650) per trivial turn.
