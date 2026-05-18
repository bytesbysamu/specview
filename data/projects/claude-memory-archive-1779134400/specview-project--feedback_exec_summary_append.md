---
name: Exec summaries — always append, never replace
description: When updating exec-guide-summary.md files, always append new sections — never overwrite the file
type: feedback
---

Always append to exec-guide-summary.md files. Never use Write to overwrite them with new content. Each update (CI fixes, root cause explanations, test guides, post-merge notes) should be a new section appended to the bottom.

**Why:** The summary is a cumulative log of what happened during execution. Replacing it loses the history of earlier iterations, CI fix cycles, and review findings.

**How to apply:** Use Edit to add new sections at the end of the file. Only use Write for the initial creation when the file doesn't exist yet.
