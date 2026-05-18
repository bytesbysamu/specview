---
name: exec-guide always creates summary file
description: After exec-guide finishes all tasks, always write an execution-report.md to the project dir summarising what was done
type: feedback
---

After running exec-guide (or any implementation pipeline), always write an `execution-report.md` to the project directory as the final step. Do not wait to be asked.

**Why:** Sam expects a summary file to be created as part of the pipeline — it's the paper trail for what was executed, what passed, and what was skipped. Without it the project dir has no record of the run.

**How to apply:** After the final task completes and /dev-test passes, write `data/projects/<project_id>/execution-report.md` with:
- Date and method (exec-guide)
- Tasks run and their status
- Files created/modified/deleted
- Test results summary
- Any pre-existing failures noted separately
