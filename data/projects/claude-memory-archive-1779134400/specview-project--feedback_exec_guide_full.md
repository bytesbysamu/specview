---
name: exec-guide must complete all steps
description: When /exec-guide is invoked, execute ALL steps including dev-test, dev-review, commit, PR, CI, merge, and summary — never skip post-implementation steps
type: feedback
---

When the user invokes /exec-guide explicitly, every step in the Procedure is mandatory. Steps 5-12 (dev-test, dev-review, fix findings, re-test, commit, PR, CI monitoring, merge, summary) must all execute — even if the implementation tasks went smoothly. Do not report "done" until the PR is merged and the exec-guide-summary.md is written.

**Why:** The user explicitly invoked the skill and expects the full pipeline. Skipping post-implementation steps defeats the purpose of the structured skill and leaves the work in an incomplete state (no tests verified, no review, no summary).

**How to apply:** After all tasks complete, always run dev-test → dev-review → fix criticals → commit → PR → CI → merge → write summary. No shortcuts.
