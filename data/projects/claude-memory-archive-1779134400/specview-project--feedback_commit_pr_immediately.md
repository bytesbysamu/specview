---
name: Commit often, create PR immediately
description: Always commit work frequently and create PR as soon as an epic/task is done — never leave work uncommitted or on a branch without a PR
type: feedback
---

Commit often. When done with an epic or task, create a PR immediately — before any other work starts.

**Why:** Work was lost when a squash-merged PR auto-deleted a branch that had subsequent commits (braindumps, CLAUDE.md updates, exec-guide-summary) that weren't included in the squash. The branch deletion wiped those commits.

**How to apply:**
- Commit after every meaningful change, not in batches
- Create PR immediately after completing an epic's implementation
- Never push docs/braindumps to a feature branch after its PR has been auto-merged
- If the PR is already merged and you have more commits, push directly to master or create a new branch+PR
