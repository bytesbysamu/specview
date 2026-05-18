---
name: Atomic task execution — always 2 agents per task, always produces code + doc
description: Every task execution spawns exactly 2 agents in parallel. Agent A writes the task-N.v2.md plan. Agent B implements code. Both mandatory, both in one function call, no exceptions.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Sam's rule: task execution is ONE atomic function that ALWAYS spawns TWO agents:

```
executeTask(epicPath, taskNum, workDir):
  Agent A (planner): reads epic → writes task-N.v2.md to project folder
  Agent B (executor): reads epic → implements → commits
  Both run in parallel
  Both MUST complete
  Reconcile deviations after both land
```

**What went wrong:** In the distribution sprint, executor 1 was told to write task plans. Executors 2 and 3 were not — different prompts, inconsistent output. 6 of 9 tasks shipped code without documentation.

**The fix:** Never write custom prompts per executor. Use ONE function that spawns the same 2-agent pair every time. The planner prompt is always the same (read epic task N, write 10-section plan). The executor prompt is always the same (read epic task N, implement, commit). The only variable is the epic path + task number + working directory.

**How to apply:**
- NEVER spawn a single executor agent for a task
- ALWAYS spawn exactly 2 in one message: planner + executor
- If only 1 agent is needed (trivial task), still spawn the planner — the doc is mandatory
- The function signature is: `executeTask(epicPath, taskNum, workDir)` — everything else is template
- After both land: compare, fix deviations, merge

This is the abstraction the user asked for: "one function that spawns two agents, one on task, one on doc."
