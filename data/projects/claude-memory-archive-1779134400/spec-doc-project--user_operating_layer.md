---
name: User operates as architect, not pair-programmer
description: Sam wants to manage executor capacity across parallel workstreams; do not pull him back down into per-line code review
type: user
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Sam is consciously shifting his role from "writing code" to "managing executor capacity." He framed it explicitly: "you're the architect reviewing diffs, not the developer writing code... become a better founder, not a better engineer."

**How to apply:**
- When a task can be parallelized across worktrees, default to that shape — don't ask him to micromanage sequencing.
- Surface decisions at the strategy layer: "merge order," "spec-quality verdict," "next product to ship," "branching policy."
- Don't surface line-level diffs unless they reveal a strategic signal (deviation count, principle violation, scope creep). The diffs themselves go to him as `git log` / `git diff` artifacts, not in-conversation prose.
- When he reviews work, frame the report as a manager would receive it from a team lead: who shipped, what landed, where the friction was, what the next decision is.
- Resist the urge to pull him into the implementation when an executor agent can run the spec end-to-end.
