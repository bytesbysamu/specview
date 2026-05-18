---
name: Always create PR after push + monitor CI
description: Every git push must be followed by a PR, CI monitoring, conflict resolution, and blocking issue check
type: feedback
---

After every `git push`, always:
1. Create a PR if one isn't already open — verify with `gh pr list` before reporting done
2. Resolve any merge conflicts on the branch before the PR is mergeable
3. Monitor CI with `gh pr checks --watch` until all checks pass or fail
4. Check for blocking issues on the PR (`gh pr view --json mergeable,mergeStateStatus`)

**Why:** "push means create PR" — pushing without a PR is an incomplete action. Conflicts and CI are part of the same workflow, not follow-up tasks.

**How to apply:** `git push` → `gh pr list` (confirm PR exists or create) → resolve conflicts if any → `gh pr checks --watch` → report final state (mergeable + CI status).
