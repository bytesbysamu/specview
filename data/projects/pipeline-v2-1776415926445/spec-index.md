---
sidebar_position: 0
---

# Pipeline V2 -- Codify the Session

> Automate the five manual interventions that dropped deviation average from 6.0 to 2.0, so the next session starts at 2.0 instead of relearning.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Problems driving this capability |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design |
| [Timeline](./timeline.md) | Status tracking |

## Overview

One session produced 3 epics, 21 tasks, 90 commits, 8,592 lines, 240 tests, and zero regressions. Deviation average dropped from 6.0 to 2.0 across three epics (UX Revamp, Text Chains, Trendfy) as the pipeline learned. But that learning was manual -- rescans, reviews, caveats injection, deviation counting -- all performed by the operator. Without codifying those interventions, the next session starts at 6.0 again.

Pipeline V2 turns five manual steps into automated pipeline stages inside spec-doc itself. The target codebase is spec-doc: `server.js` (Express API on port 3100), `scripts/regen-task.mjs` (task generation script), and the Angular frontend. When complete, a fresh clone of spec-doc produces 2.0-deviation specs on its first run, not its third.

## Document Flow

```
Analysis  -->  Epic  -->  Architecture  -->  Implementation Guides
(problems)    (scope)     (design)          (per-task contracts)
```

## Quick Reference

| When you need... | Read... |
|-------------------|---------|
| Why these 5 changes matter | [Analysis](./analysis.md) |
| What tasks ship, in what order | [Epic](./epic.md) |
| How the pipeline stages connect | [Architecture](./architecture.md) |
| Current status of each task | [Timeline](./timeline.md) |

## For Claude Code

```
@analysis.md @epic.md @architecture.md @timeline.md
```

Reference all four when generating implementation guides for this capability.

**Last Updated**: 2026-04-16
