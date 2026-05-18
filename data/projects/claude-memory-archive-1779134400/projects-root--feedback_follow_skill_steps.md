---
name: Follow all skill steps — no skipping
description: When a skill is loaded and its procedure is shown, execute every step including post-execution steps like dev-test, dev-review, and summary file
type: feedback
---

When a skill's full procedure is loaded and visible in the conversation, execute **every step** — including post-implementation steps like dev-test, dev-review, and writing a summary file. Do not treat later steps as optional or skip them because the main work is done.

**Why:** exec-guide already had steps 5 (dev-test), 6 (dev-review), 7 (write summary), 8 (report to user) written in the skill. They were skipped anyway. Sam had to call it out manually. This should never happen.

**How to apply:** Before closing out any skill invocation, re-read the skill's Procedure section and confirm every numbered step has been executed. If a step was skipped, execute it before reporting done.
