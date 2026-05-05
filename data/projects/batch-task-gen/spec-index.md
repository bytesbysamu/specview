---
sidebar_position: 0
---

# 📋 Batch Task Generation

> Cross-project orchestration layer that generates missing implementation guides for epics at scale, running `regen-task.mjs` across multiple projects with dependency-aware scheduling and failure recovery.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🔍 Analysis](./analysis.md) | Problems driving this capability |
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

The spec-doc pipeline generates implementation guides one task at a time via `scripts/regen-task.mjs`. The `--all --parallel N` flags handle wave-ordered generation within a single project. But when 10 projects each need 4–12 task specs generated, the operator currently runs the command 10 times manually, monitors each run, restarts on failure, and pieces together results across terminal sessions. That's ~63 task specs across 10 projects — a 3–5 hour batch job with no cross-project progress visibility and no recovery path when a generation call times out mid-run.

Batch Task Generation adds a thin orchestration layer above `regen-task.mjs` that accepts a project manifest, iterates projects in priority order, delegates per-project generation to the existing `--all --parallel 2` machinery, and produces a unified progress stream and summary report. The operator starts one command, walks away, and comes back to a results table showing which specs shipped, which failed, and what to retry.

The four project categories have different motivations. **Retroactive** projects (code already shipped) need specs for institutional memory — without them, the next session re-discovers decisions this session already made. **Ready-to-execute** projects (`chain-meta-display`, `parallel-gen`) are blocked: their agents can't run until task specs exist. **Backlog** projects get specs now so they're execution-ready when prioritized. The batch treats all categories identically at generation time — the distinction matters for manifest ordering and summary grouping, not for the generation logic itself.

## Related Documents

- [Analysis](./analysis.md) — Problems and gaps driving this capability
- [Pipeline V2 braindump](../../braindump-pipeline-v2.md) — Parent context for pipeline improvements
- [Parallel Gen braindump](../../braindump-parallel-task-gen.md) — Prior work adding `--parallel` and `--all` to regen-task.mjs

