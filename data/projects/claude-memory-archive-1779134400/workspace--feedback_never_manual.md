---
name: Never do anything manually
description: Always use spec-doc pipeline for spec docs, guides, and task execution — never hand-write these artifacts
type: feedback
originSessionId: e024faf7-9ea0-4c83-9555-b3f47825503d
---
Never manually write spec docs, implementation guides (.v2.md), or task execution prompts. Always use the spec-doc pipeline.

**Why:** User has corrected this multiple times. Hand-written artifacts drift from the pipeline's format and quality. The pipeline is the system of record.
**How to apply:** For ANY spec/guide/task-exec work: start spec-doc server → call the API → parse output → write files → push to sidebar. If something needs fixing in the output, fix the INPUT (braindump/epic) and re-run the pipeline. Never bypass it.
