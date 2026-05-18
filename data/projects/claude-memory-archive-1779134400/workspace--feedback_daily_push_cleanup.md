---
name: Daily push and worktree cleanup
description: Push to remote and clean up stale git worktrees at least once per day
type: feedback
originSessionId: 80e80787-3bf9-450c-a496-b83c508e6270
---
Push all commits to remote and clean up stale git worktrees at least once per day.

**Why:** Work gets stranded locally — 15+ worktree branches were never pushed, and stale worktrees accumulate in /tmp/wt/. Daily hygiene prevents drift between local and remote.

**How to apply:** At the end of a session or when wrapping up work, check for unpushed commits (`git log origin/branch..HEAD`) and stale worktrees (`git worktree list`). Push what's ready, prune merged worktrees.
