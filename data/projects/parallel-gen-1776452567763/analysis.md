
```markdown
---
sidebar_position: 1
---

# 🔍 Parallel Task Generation – Analysis

**Purpose**: Surface the constraints and open decisions that shape the parallel task generation design.

**Date**: 2026-04-17

---

## Problem

Task generation is the pipeline's throughput bottleneck. Every implementation guide requires a full `claude -p` round-trip through the Express server — prompt assembly, CLI spawn, LLM generation, preamble strip, auto-review, file write. Each call takes 2–4 minutes depending on task complexity. For a 17-task epic (e.g., the distribution capability), serial generation takes ~50 minutes. Every downstream executor is blocked until this step completes.

The infrastructure to support concurrency already exists: `server.js` sets `requestTimeout`, `headersTimeout`, and `keepAliveTimeout` to 600s (shipped in Pipeline v2). The preamble-strip fix prevents partial-output corruption. The missing piece is script-level orchestration inside `regen-task.mjs`.

---

## Hard Constraints

| Constraint | Source | Impact |
|-----------|--------|--------|
| Claude CLI is single-threaded per spawn | Claude CLI architecture | Each concurrent task needs its own `claude -p` process; the Express server spawns one per request |
| `UND_ERR_HEADERS_TIMEOUT` at high concurrency | Observed in session (5+ concurrent calls, pre-fix) | Must find the post-fix ceiling empirically; cannot assume unlimited concurrency |
| Prior-tasks context depends on earlier task output | `loadPriorTasksSummary()` in regen-task.mjs (lines 144–178) | Tasks with dependencies need their predecessors' files written before generation starts |
| `curl --max-time 600` hard ceiling | regen-task.mjs (line 512) | Individual task generation cannot exceed 10 minutes regardless of concurrency |
| Auto-rescan triggers on foundation tasks | `shouldRescan()` / `isFoundationTask()` in regen-task.mjs (lines 196–207) | Foundation tasks (no deps, 2+ dependents) trigger a codebase rescan — this must complete before dependent tasks begin |

---

## Open Questions

| Question | Options | Recommendation |
|----------|---------|---------------|
| What is the safe concurrency ceiling post-600s fix? | Test at 3, 4, 5 concurrent calls and measure failure rate | Default to 3 (proven), allow override via `--parallel N`, document the tested ceiling |
| Should `--all` respect task dependencies? | (A) Dependency-aware waves: slower but prior-tasks context is fresh. (B) Blast all: faster but prior-tasks block is stale for later tasks | Dependency-aware waves. The prior-tasks context block is what makes guides executor-ready — stale context defeats the purpose of generation quality |
| Where does the concurrency limiter live? | (A) Hand-rolled Promise pool in regen-task.mjs. (B) Import `p-limit` from npm | Hand-rolled. The logic is ~20 lines, avoids a new dependency, and the batched-wave model (run N, wait, next wave) is simpler than a continuous pool |
| Should failed tasks retry automatically? | (A) No retry, report failure, continue next wave. (B) Retry once with backoff. (C) Retry at end as a cleanup pass | Option C — collect failures, retry once at the end as a final wave. Avoids blocking the happy path but gives transient errors a second chance |

---

## Dependencies

| Dependency | Status | Blocks |
|-----------|--------|--------|
| 600s server timeout | Shipped (Pipeline v2) | Concurrency ceiling test |
| Preamble strip | Shipped (Pipeline v2) | Safe concurrent writes (no corruption) |
| Auto-review endpoint | Shipped (Pipeline v2) | Concurrent reviews (each task reviews independently) |
| `extractTasksFromEpic()` parser | Exists (regen-task.mjs lines 181–193) | Wave grouping needs the parsed dependency graph |
| `loadPriorTasksSummary()` | Exists (regen-task.mjs lines 144–178) | Must be called per-wave, not once up front |

---

## Explicitly Out of Scope

- Server-side concurrency changes (no Express worker pool, no queue system)
- Distributed generation across multiple machines
- Caching or memoizing LLM responses between runs
- Changing the Claude CLI invocation pattern (`-p` flag, `--output-format text`)
- Parallelizing across epics (this capability is within a single epic)

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
```

