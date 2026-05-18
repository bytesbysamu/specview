---
name: Run epic gen and executor in parallel — check deviations after both land
description: Generate the epic and execute the task simultaneously. The epic is the documentation, the executor is the implementation. Compare after both complete and fix deviations. Cuts latency in half.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Sam's insight: running the spec-doc epic generation AND the executor agent simultaneously is the optimal pattern. Don't wait for the epic to finish before starting execution — they run in parallel and you reconcile after.

**The flow:**
1. Write braindump
2. Launch BOTH: `generate-spec` (epic gen) + executor agent (reads braindump + architecture directly)
3. Both complete ~same time
4. Compare epic vs implementation — fix deviations
5. Epic becomes documentation of what was built, corrected by reality

**Why this works:**
- The epic takes 3-5 min to generate. The executor takes 5-10 min to implement.
- Running them in sequence = 8-15 min. Running in parallel = 5-10 min (longest wins).
- The executor is smart enough to work from the braindump alone. The epic adds structure it doesn't strictly need.
- Deviations between epic and implementation are the INTERESTING signal — they reveal where the braindump was ambiguous.

**How to apply:**
- When user says "braindump this and execute": save braindump, launch generate-spec AND executor agent in the same message
- When both complete: compare epic task table vs actual commits, note deviations, fix gaps (like the iOS Info.plist permission that was in the epic but not in the executor's output)
- The epic in the sidebar is the documentation. The code in the worktree is the truth. They converge through deviation review.

**This does NOT violate "everything through spec-doc"** — the braindump still goes through generate-spec. The executor just doesn't wait for it.
