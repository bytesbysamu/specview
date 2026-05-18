---
name: Always run CI before pushing and merging
description: Must run full test suite (make test / python -m pytest) before merging or pushing to master in spec-doc
type: feedback
---

Always run the full test suite before merging a branch or pushing to master in the spec-doc project.

**Why:** The user explicitly asked for this after observing CI failures that made it to master.

**How to apply:** In spec-doc-live (`/Users/sam/Projects/2026/spec-doc-live/api`), run `python -m pytest --tb=short -q` and confirm all tests pass before doing `git push origin master` or merging branches.
