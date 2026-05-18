---
name: Never push to master
description: Always create PRs, never push directly to master branch
type: feedback
---

Never push directly to master. Always create a feature branch and PR.

**Why:** User wants PR review workflow, not direct pushes. Direct pushes bypass CI checks and review.

**How to apply:** For every change, create `feature/<name>` or `fix/<name>` branch, commit there, push with `-u`, then `gh pr create`. Wait for user to merge.
