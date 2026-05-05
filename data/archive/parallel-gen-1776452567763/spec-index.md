
```markdown
---
sidebar_position: 0
---

# 📋 Parallel Task Generation

> Unblock the pipeline bottleneck — generate implementation guides concurrently instead of one at a time.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Parallel Task Generation adds concurrency support to `scripts/regen-task.mjs`, the script that turns epic task rows into executor-ready implementation guides. Today each task generates serially — one `curl` call to the Express server, one `claude -p` spawn, one file written — before the next begins. For a 17-task epic, this takes ~50 minutes. The same work at concurrency 3 takes ~18 minutes.

The capability introduces two new CLI flags: `--parallel N` (run up to N tasks concurrently) and `--all` (generate every task in the epic in one command, batched by dependency order). Together they cut task-generation wall-clock by 60–70% without requiring server-side changes — the 600s `requestTimeout` and preamble-strip fixes already shipped in Pipeline v2 provide the necessary infrastructure.

The design respects task dependencies. Tasks with no unresolved dependencies are grouped into waves; within each wave, up to N tasks run concurrently. This preserves the prior-tasks context block that makes downstream guides aware of what earlier tasks produced, while still parallelizing within each dependency tier. A wave completes when all its tasks finish (or fail); then the next wave's prior-tasks context is rebuilt from the freshly-written files, and the next batch launches.

## Related Documents

- [Analysis](./analysis.md)
- [Braindump](../../braindump-parallel-task-gen.md) — original session notes
- [Pipeline v2 Feature Tests](../e2e-pipeline-v2.md) — existing pipeline test matrix
```

