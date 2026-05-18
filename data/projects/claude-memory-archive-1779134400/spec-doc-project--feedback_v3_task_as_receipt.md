---
name: V3 pipeline — task file is a receipt, not a plan
description: Executor agents write the task spec AFTER implementation (as documentation of what was done), not before. Same file format, same project folder, zero pre-generation tokens.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Pipeline V3 eliminates task spec generation as a pre-step. The executor:
1. Reads the epic task description + architecture
2. Scans codebase
3. Plans internally
4. Implements + commits
5. **Writes task-N.v2.md as a receipt** — documents what was built, files changed, trade-offs, deviations, tests, commits

The task file is the SAME format as before (10 sections) but filled from reality, not prediction. It lives in the same project folder so the sidebar shows the full set.

**Why:** Task spec generation burned 60K tokens per task, took 3-5 min, failed 50% of the time via CLI, and the executor re-discovered everything anyway. The receipt costs ~2K tokens (agent already has all the context from implementing) and is more accurate than the prediction.

**How to apply:**
- When spawning an executor: include in the prompt "After completing, write a task-N.v2.md file in the project folder documenting: Context, Files changed, Implementation steps taken, Tests added, Commit plan, Deviations"
- The receipt goes to the spec-doc project folder so it appears in the sidebar
- Same format = same reviewability, just filled post-hoc instead of pre-hoc
