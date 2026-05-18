---
name: exec-guide must run full procedure including post-implementation steps
description: When dispatching exec-guide via background agent, include ALL steps (dev-test, dev-review, commit, PR, CI, merge, summary) — not just the implementation tasks
type: feedback
---

The exec-guide skill has mandatory post-implementation steps (5-12): dev-test, dev-review, fix findings, commit, PR, CI monitoring, merge, summary file. When dispatching via a background agent with a custom prompt, these steps were skipped because the prompt only said "execute all 5 tasks."

**Why:** The skill file explicitly warns "All steps of the Procedure are mandatory. Do not report 'done' until the PR is merged." Skipping steps defeats the quality pipeline.

**How to apply:** ALWAYS use the `/exec-guide` skill directly. NEVER dispatch exec-guide via a manual prompt to a background agent. The skill loads the full procedure automatically. A custom prompt will always miss steps — there is no valid shortcut.
