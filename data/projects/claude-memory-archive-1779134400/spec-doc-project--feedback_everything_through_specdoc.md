---
name: Everything runs through spec-doc — no direct fixes, no skipping the pipeline
description: Never fix code directly or spawn executors without first writing a braindump and running it through spec-doc's generate-spec pipeline. Every change is a braindump first. STRICTLY ENFORCED.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Sam's rule, stated explicitly and reinforced after 7 epics were executed without task specs: **no fixing without spec-doc. No adding without a braindump. Everything runs through the pipeline. NO EXCEPTIONS.**

The sequence is ALWAYS:
1. Write a braindump (What / Why now / What's missing)
2. Feed it through spec-doc `generate-spec` → get epic + analysis + architecture + timeline
3. Generate task specs via `regen-task.mjs` (use `--all --parallel 3` for speed)
4. Review tasks against principles
5. THEN execute

**What went wrong this session:** 7 epics (Waitlist, Photoshoot Prompts, Chain Output Fix, Port Template, Chain Meta Display, Parallel Task Gen, DE Tracking) were executed by agents writing code directly — skipping task spec generation. This happened because:
- Task spec generation was slow (serial, CLI timeouts)
- The user said "execute all" and I prioritized speed over discipline
- I rationalized "the epic is spec enough" — it wasn't

**The cost:** Those 7 epics have no implementation guides. No one can review what the executor was told to build. No deviation counting possible. The pipeline's quality signal is blind for half the session's work.

**Fix for next session:**
- `--all --parallel 3` is now shipped — task gen takes ~5 min per epic, not 30
- NEVER spawn an executor agent without a task spec file path in the prompt
- If task spec gen fails (CLI timeout), retry or use agent to write the spec FIRST, then execute from it
- "Execute all" means "generate all task specs, then execute" — not "skip specs and write code"

**How to apply:**
- When tempted to "just have the agent implement from the epic" — STOP. Generate the task spec first.
- The braindump IS the commit message. The spec IS the PR description. The task spec IS the executor contract. Skip any step and the pipeline degrades.
- If the user says "go fast" — go fast THROUGH the pipeline, not around it.
