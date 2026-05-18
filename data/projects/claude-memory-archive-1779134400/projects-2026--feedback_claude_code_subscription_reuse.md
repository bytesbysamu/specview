---
name: Reuse Claude Code Max subscription, avoid new API costs
description: Sam strongly prefers reusing his Claude Code Max plan via `claude -p` as an ad-hoc "API" instead of paying for separate Anthropic/OpenAI keys. Applies to every AI tooling recommendation.
type: feedback
---

Sam pays for Claude Code Max and wants to reuse that subscription wherever possible for AI-powered tools and frameworks — spec-doc does this by exec'ing `claude -p "prompt"` as a subprocess. When evaluating or setting up any AI dev tool, default to the "use local `claude` CLI via subprocess" pattern instead of proposing Anthropic/OpenAI/OpenRouter API keys. Only suggest a paid API key path if Sam explicitly asks or if the `claude -p` path is demonstrably unworkable for the use case.

**Why:** Explicit instruction given during OpenClaw setup (2026-04-11): "i aleady pay for claude code max, i want to reuse that for claw, no other api cost". He confirmed the `spec-doc` project already does this via `execClaude(prompt)` → `claude -p`, and `spec-doc/docker/Dockerfile.executor` installs `@anthropic-ai/claude-code` globally + sets `CLAUDE_CODE_SKIP_PERMISSIONS=1` to make the pattern work headlessly.

**How to apply:**
- When recommending any AI framework/agent runner/CLI tool: lead with the Claude Code subscription reuse option (mount `~/.claude`, install `@anthropic-ai/claude-code`, point the tool at `claude -p`) and only mention API keys as a fallback.
- Hard constraint — see `project_openclaw_max_plan_constraint.md`: Sam's Max plan has overage disabled at the org level, so any tool that wraps Claude Code must keep per-turn token cost small or it will hit the 5-hour bucket wall. Check that constraint before claiming a tool "just works" with Max subscription.
- In new project planning, spec-doc's `execClaude` subprocess pattern is the reference implementation of this approach.
