---
name: Executor agents must use worktrees or verify build before committing
description: Executor agents writing to the live working directory break the dev server mid-flight. Use git worktrees for isolation, and always verify ng build passes before declaring done.
type: feedback
originSessionId: ddd9becd-d854-4163-892e-00f6ecd0b63d
---
Executor agents MUST NOT write directly to the user's live working directory.

**Why:** During the Relationship Check-In epic, the Task 6 executor modified `checkin-data.service.ts` and `checkin.page.ts` mid-flight, introducing compile errors (duplicate variable declaration, missing signal) that the user saw live in their dev server. The errors would have been caught at RECONCILE + INTEGRATE, but the user hit them first because the executor was writing to the same directory.

**How to apply:**
- Use `isolation: "worktree"` when spawning executor agents so they work on an isolated git copy
- If worktrees aren't available: executor agents MUST run `ng build --configuration=production` and verify zero errors BEFORE committing
- Compile errors in the live directory are a pipeline failure — they should NEVER reach the user
- The INTEGRATE step (ng build + tests) must run AFTER agent completion, not just as a final check
- Divergence checking should include a compile-error scan, not just spec-vs-implementation comparison
