---
name: PR target is master
description: PRs in spec-doc merge feature branches into master; live is the deploy branch (master → live is a separate step, not a PR)
type: feedback
---

PRs target `master`, not `live`. When the user says "create a PR", create feature-branch → master.

**Why:** `live` is the production deploy branch. Merging master → live is a separate deploy action, not a development PR.

**How to apply:** Always open PRs with `--base master`. Never open master → live PRs unless explicitly asked to deploy.
