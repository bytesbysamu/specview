---
name: Chain epic generation with task generation — always, automatically
description: After generate-spec produces an epic, immediately run regen-task --all --parallel 3 on it. Never leave an epic in sidebar without task specs.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Sam's rule: epic generation and task generation are ONE step, not two. When a braindump goes through `generate-spec`, the pipeline MUST chain directly into `regen-task --all --parallel 3` without waiting for a human command.

The sequence is atomic:
1. Braindump → `generate-spec` → persist epic (5 files)
2. **Immediately** → `regen-task --all --parallel 3` on the new project
3. Task specs land → THEN report "ready to execute"

Never say "epic in sidebar, task specs not generated." That state should not exist. If it does, the pipeline broke.

**Why:** This session created 19 braindumps. Half the epics sat in the sidebar with zero task specs because epic gen and task gen were treated as separate manual steps. The user had to repeatedly say "generate tasks" after each epic landed. Chaining them eliminates that friction.

**How to apply:**
- After ANY `generate-spec` call that produces files: parse the project ID, immediately run `node scripts/regen-task.mjs {projectId} --all --parallel 3`
- After ANY agent writes an epic: same — chain task gen
- The "generate-spec + regen-task" pair is the atomic unit, not "generate-spec" alone
- Log both steps as one operation: "braindump → epic (5 files) → task specs (N tasks)"
