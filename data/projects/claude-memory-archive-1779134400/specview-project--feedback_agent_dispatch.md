---
name: Use specialist agent types for exec-guide dispatch
description: User prefers specialist subagent_type over general-purpose when executing impl guide tasks
type: feedback
---

When executing implementation guide tasks via exec-guide, dispatch using the specialist agent type (`spec-frontend`, `chain-developer`, `spec-backend`, `chain-agent`) — not `subagent_type: "general-purpose"`. The exec-guide skill says general-purpose but user rejects those dispatches.

**Why:** User wants clean agent execution using the actual specialists, not a general agent with a pasted preamble.

**How to apply:** Override the exec-guide skill's "use general-purpose" instruction — use the matching specialist subagent_type directly.
