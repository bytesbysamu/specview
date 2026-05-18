---
name: Two agents per task — planner and executor run in parallel
description: For each task, spawn Agent A (writes impl guide from epic) and Agent B (implements from epic) simultaneously. Compare outputs after both land. Deviations between guide and code are the quality signal.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
For every task execution, spawn TWO agents in parallel:

**Agent A (planner):** Reads epic task description + architecture → writes `task-N.v2.md` (10-section impl guide) to the project folder.

**Agent B (executor):** Reads epic task description + architecture → scans codebase → implements → commits.

Both run simultaneously. Neither waits for the other.

When both complete:
- Compare Agent A's plan vs Agent B's commits
- Deviations = where the plan and reality diverged
- Fix gaps (e.g., Agent B missed an iOS permission that Agent A's plan included)
- Agent A's guide becomes the documentation, corrected by Agent B's reality

**Why:** Step 0 (plan) inside the executor was sequential — 30-60s writing a plan before coding. Moving it to a parallel agent eliminates that latency. The planner and executor both read the same epic but approach it differently (one thinks about structure, one thinks about code). The diff between them is more valuable than either alone.

**How to apply:**
- For each task: spawn 2 agents in one message (both `run_in_background: true`)
- Agent A prompt: "Write task-N.v2.md with 10-section plan from the epic"
- Agent B prompt: "Read epic, implement, commit. No plan step — go straight to code."
- When both land: diff, fix, commit final state
