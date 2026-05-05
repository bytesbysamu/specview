
```markdown
---
sidebar_position: 2
---

# 🎯 Parallel Task Generation – Epic

**Purpose**: Define scope and tasks for adding concurrent task generation to the spec-doc pipeline.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and open decisions.

---

## Business Value

Task generation is the single biggest wall-clock bottleneck in the spec-doc pipeline. Every epic must pass through `regen-task.mjs` before executors can begin — and today that means serial generation: one task at a time, 2–4 minutes per task, no overlap. A 17-task epic blocks for ~50 minutes. A 7-task epic still blocks for 15–20 minutes. During this time, executor capacity sits idle.

Cutting generation time by 60–70% (concurrency 3 on a 17-task epic: ~18 minutes) directly unblocks executor throughput. More importantly, the `--all` flag eliminates the manual step of invoking `regen-task.mjs` once per task — the operator runs one command and walks away. This compounds: fewer manual steps means fewer forgotten tasks, fewer stale prior-tasks contexts, and fewer re-runs.

The investment is small — all changes are contained in `scripts/regen-task.mjs` and a new test file. No server changes, no new dependencies, no schema changes. The 600s timeout infrastructure already shipped in Pipeline v2. This is pure script-level orchestration.

---

## Scope

### What This Epic Covers

- `--parallel N` flag for concurrent task generation within a single epic
- `--all` flag to generate every task in the epic in one command
- Dependency-aware wave grouping (topological sort on task dependencies)
- Batched execution: up to N tasks per wave, waves run sequentially
- Progress reporting to stdout (which tasks are in-flight, completed, failed)
- End-of-run failure retry (one retry pass for tasks that timed out or errored)
- Concurrency ceiling discovery (empirical test at 3, 4, 5 concurrent calls)
- Unit tests for wave grouping, dependency resolution, and CLI argument parsing
- Integration test for parallel generation against the running Express server

### What This Epic Does NOT Cover

- ❌ Server-side changes (no Express worker pool, no queue, no rate limiting)
- ❌ Cross-epic parallelism (generating tasks from multiple epics simultaneously)
- ❌ Distributed generation (multiple machines)
- ❌ LLM response caching or deduplication
- ❌ UI/frontend changes (this is CLI-only)
- ❌ Changes to the prompt template or review pipeline

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Concurrency Ceiling Test** | None | — | 0.5 day | High |
| 2 | **Extract Reusable Task Runner** | None | 1 | 0.5 day | High |
| 3 | **Dependency-Aware Wave Grouper** | None | 1, 2 | 0.5 day | High |
| 4 | **`--parallel N` Flag Implementation** | 2, 3 | — | 1 day | High |
| 5 | **`--all` Flag with Batched Waves** | 3, 4 | — | 1 day | High |
| 6 | **Progress Reporter** | 4 | 5 | 0.5 day | Medium |
| 7 | **Retry Failed Tasks** | 5 | 6 | 0.5 day | Medium |
| 8 | **Integration Tests** | 5, 7 | — | 0.5 day | Medium |

### Task Details

#### Task 1: Concurrency Ceiling Test

Empirically determine the maximum safe number of concurrent `claude -p` calls against the Express server with the 600s timeout fix in place. Run 3, then 4, then 5 concurrent calls using the existing `regen-task.mjs` (invoked N times in parallel via shell). Record success/failure, latency, and error type for each concurrency level. Document the ceiling in a short report. This informs the default value for `--parallel N`.

#### Task 2: Extract Reusable Task Runner

Refactor the task-generation logic in `regen-task.mjs` (currently lines 430–580) into a standalone async function `generateOneTask(projectId, taskNum, options)` that returns `{ success, taskNum, filePath, latencyMs, error }`. Today the logic is inline in the script's main flow — extracting it enables calling it N times concurrently from a batch orchestrator. Preserve all existing behavior: context loading, optional rescan, prompt assembly, generation, preamble strip, auto-review, file write.

#### Task 3: Dependency-Aware Wave Grouper

Implement `groupTasksIntoWaves(tasks)` — a function that takes the parsed task array (from `extractTasksFromEpic()`) and returns an ordered array of waves, where each wave contains tasks whose dependencies are all satisfied by prior waves. This is a topological sort grouped by depth. Tasks with no dependencies land in wave 0. Tasks depending only on wave-0 tasks land in wave 1. And so on. Cycle detection throws an error with the cycle path.

#### Task 4: `--parallel N` Flag Implementation

Wire the `--parallel N` CLI argument into `regen-task.mjs`. When `--parallel N` is provided alongside a list of task numbers (e.g., `node scripts/regen-task.mjs projectId 1 2 3 4 --parallel 3`), run up to N tasks concurrently using `generateOneTask()`. Use a hand-rolled Promise pool: launch N, wait for one to settle, launch the next. Default N to 3 if `--parallel` is passed without a value. Ignore dependency ordering in this mode — the caller explicitly chose which tasks to run.

#### Task 5: `--all` Flag with Batched Waves

Wire the `--all` flag. When passed, parse the epic, extract all tasks, group into dependency-aware waves via `groupTasksIntoWaves()`, and generate each wave as a batch. Within each wave, respect `--parallel N` (default 3). Between waves, rebuild the prior-tasks context from the freshly-written files before launching the next wave. This is the "one command, walk away" mode. Log wave boundaries to stdout.

#### Task 6: Progress Reporter

Add a live progress table to stdout during parallel generation. Show each task's state: `pending`, `in-flight`, `done`, `failed`. Update in-place using ANSI cursor movement (`\x1b[{n}A` to move up, `\r` to overwrite). Include elapsed time per task and overall elapsed time. Degrade gracefully to simple line-by-line logging if stdout is not a TTY (e.g., piped to a file).

#### Task 7: Retry Failed Tasks

After all waves complete, collect any tasks with `success: false`. If there are failures and retries haven't been attempted, re-run the failed tasks as one final wave at `--parallel N` concurrency. Log clearly that this is a retry pass. If retries also fail, report the final failure list with error messages. Add `--no-retry` flag to skip this behavior.

#### Task 8: Integration Tests

Add `scripts/regen-task.test.mjs` with tests for: (a) `groupTasksIntoWaves` with linear, diamond, and independent dependency graphs; (b) `--parallel N` argument parsing; (c) `--all` argument parsing; (d) integration test that runs `--all --parallel 2` against a test project on the live Express server (requires `AI_PROVIDER=mock`) and verifies all task files are written. Use Node's built-in `node:test` runner to match existing test conventions (`deviation-report.test.mjs`).

---

## Success Criteria

- ✅ `--parallel 3` on a 7-task epic completes in <40% of serial time (measured wall-clock)
- ✅ `--all` generates every task in the epic without manual intervention
- ✅ Dependency ordering is respected: no task generates before its dependencies' files are written
- ✅ Prior-tasks context for wave N+1 includes output from wave N (verified by inspecting generated files)
- ✅ Failed tasks are retried once and failures are reported with actionable error messages
- ✅ Zero regressions: existing single-task `regen-task.mjs projectId 3` still works identically
- ✅ All new tests pass (`node --test scripts/regen-task.test.mjs`)
- ✅ Concurrency ceiling is documented with empirical data

---

## Non-Goals

- ❌ Optimizing LLM latency (that's Claude CLI / Anthropic API territory)
- ❌ Building a job queue or task scheduler (this is a script, not a service)
- ❌ Parallelizing the review step independently from generation (review runs inline per task)
- ❌ Supporting `--parallel` across different projects simultaneously
- ❌ Auto-detecting optimal concurrency (user sets it explicitly; default 3)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
```

