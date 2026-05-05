
```markdown
---
sidebar_position: 3
---

# 🏗️ Parallel Task Generation – Solution Architecture

**Purpose**: Technical design for adding concurrent task generation to `scripts/regen-task.mjs`.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

All changes are contained within `scripts/regen-task.mjs` and a new test file `scripts/regen-task.test.mjs`. No server changes. No new npm dependencies. The Express server already handles concurrent requests (each spawns its own `claude -p` process), and the 600s timeout fix provides sufficient headroom.

The design introduces three new modules inside `regen-task.mjs`:

1. **Task Runner** — extracted from the existing inline generation logic. One async function: `generateOneTask(projectId, taskNum, options) → Result`.
2. **Wave Grouper** — topological sort on the epic's dependency graph, producing ordered batches. One pure function: `groupTasksIntoWaves(tasks) → Wave[]`.
3. **Batch Orchestrator** — runs waves sequentially, tasks within each wave concurrently up to `--parallel N`. Handles progress reporting, failure collection, and retry.

The existing single-task path (`regen-task.mjs projectId 3`) remains unchanged — it calls `generateOneTask()` directly, skipping the orchestrator entirely.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| No infrastructure before features | No job queue, no worker pool, no external concurrency library. Hand-rolled Promise batching in ~20 lines |
| Adapter boundary | `generateOneTask()` is the boundary — orchestration code never touches curl, file I/O, or prompt assembly directly |
| Explicit over implicit | Concurrency limit is always explicit (`--parallel N`, default 3). No auto-detection, no dynamic scaling |
| Mock mode first | Integration tests use `AI_PROVIDER=mock` — no real LLM calls in CI |
| Structural tests as encountered | Add a structural test that `generateOneTask` is the only export calling the generation endpoint — pins the adapter boundary |

---

## Component Design

### Task 1: Concurrency Ceiling Test

**Purpose**: Empirically find the max safe concurrent `claude -p` calls post-600s-fix.

**Method**: Shell script that launches N instances of `regen-task.mjs` in parallel using `&` and `wait`. Test at N=3, 4, 5 against a real project. Record: success/failure, wall-clock per task, error type if failed. Run each level 3 times to account for variance.

**Output**: Markdown table in `docs/concurrency-ceiling.md` documenting results. This is a one-time test, not an automated gate.

### Task 2: Extract Reusable Task Runner

**Purpose**: Isolate the generation logic into a callable async function.

**Components**:
- `generateOneTask(projectId, taskNum, options)` — extracted from lines 430–580 of current `regen-task.mjs`
- Returns `{ success: boolean, taskNum: number, taskName: string, filePath: string, latencyMs: number, error?: string }`
- `options`: `{ rescan: boolean, noReview: boolean, apiBase: string }`

**Extraction boundary**: Everything from "load context files" through "write output file" becomes the function body. The current main flow becomes: parse args → call `generateOneTask()` → print result. No behavior change for single-task invocation.

**Pattern**: Adapter. The orchestrator calls `generateOneTask()` without knowing about curl, file paths, or prompt templates.

### Task 3: Dependency-Aware Wave Grouper

**Purpose**: Group epic tasks into ordered waves by dependency depth.

**Components**:
- `groupTasksIntoWaves(tasks)` — pure function, no I/O
- Input: `Array<{ num: number, name: string, deps: number[] }>` (output of existing `extractTasksFromEpic()`)
- Output: `Array<Array<{ num, name, deps }>>` — each inner array is one wave

**Algorithm**:
```
1. Build adjacency: task → [dependents]
2. Compute in-degree for each task
3. Wave 0 = all tasks with in-degree 0
4. For each wave:
   a. Collect all tasks with in-degree 0
   b. Remove them from the graph (decrement dependents' in-degree)
   c. Next wave = new in-degree-0 tasks
5. If tasks remain after all waves → cycle detected → throw with cycle path
```

This is Kahn's algorithm applied to the dependency DAG. Time complexity O(V+E) where V=tasks, E=dependency edges. For a 20-task epic, this is trivial.

**Edge cases**:
- Tasks with no dependencies and no dependents (isolated) → wave 0
- All tasks independent → single wave containing everything
- Linear chain (1→2→3→4) → one task per wave
- Diamond (1→2, 1→3, 2→4, 3→4) → wave 0: [1], wave 1: [2,3], wave 2: [4]

### Task 4: `--parallel N` Flag Implementation

**Purpose**: Enable concurrent generation for explicitly-listed tasks.

**Components**:
- CLI parsing update in argument handler (lines 15–28)
- `runBatch(tasks, concurrency, generateFn)` — launches up to N concurrent promises, returns results array

**`runBatch` implementation** (~20 lines):
```javascript
async function runBatch(taskNums, concurrency, generateFn) {
  const results = [];
  const executing = new Set();
  for (const num of taskNums) {
    const p = generateFn(num).then(r => { executing.delete(p); return r; });
    executing.add(p);
    results.push(p);
    if (executing.size >= concurrency) {
      await Promise.race(executing);
    }
  }
  return Promise.all(results);
}
```

No external dependency. `Promise.race` drains the pool naturally. When one finishes, the next launches.

**CLI syntax**: `node scripts/regen-task.mjs [--parallel N] [--rescan] [--no-review] <projectId> <taskNums...>`

When `--parallel` is present and multiple task numbers are given, use `runBatch()`. When only one task number is given, ignore `--parallel` and run directly (backward compatible).

### Task 5: `--all` Flag with Batched Waves

**Purpose**: One-command generation of an entire epic.

**Components**:
- CLI parsing for `--all` flag
- Wave orchestration loop in main flow

**Flow**:
```
1. Parse epic → extractTasksFromEpic()
2. Group → groupTasksIntoWaves(tasks)
3. For each wave:
   a. Log: "Wave {i}/{total}: generating tasks {nums}"
   b. If wave > 0: rebuild prior-tasks context (call loadPriorTasksSummary())
   c. If any task in wave is foundation AND has dependents: trigger rescan
   d. runBatch(wave.tasks, concurrency, generateOneTask)
   e. Collect results
4. Report summary
```

**Prior-tasks rebuild**: Between waves, `loadPriorTasksSummary()` is called fresh so that wave N+1 tasks see wave N outputs in their prior-tasks context block. This is the key quality guarantee — without it, later tasks would reference stale or missing prior-task summaries.

**Rescan trigger**: If a wave contains a foundation task (detected by existing `isFoundationTask()`), trigger one rescan before the wave. Only one rescan per wave, even if multiple foundation tasks exist.

### Task 6: Progress Reporter

**Purpose**: Live feedback during parallel generation.

**Components**:
- `ProgressReporter` class with `start()`, `update(taskNum, state)`, `finish()` methods
- States: `pending` (default), `in-flight`, `done`, `failed`

**TTY mode** (interactive terminal):
```
Wave 2/4 [00:03:42 elapsed]
  Task 3: pick-sunday-magazine  ✓ done     (2m 14s)
  Task 4: photoshoot-darkroom   ◉ in-flight (1m 30s...)
  Task 5: text-writers-desk     ◉ in-flight (0m 45s...)
  Task 6: a11y-screenshot-qa    ○ pending
```

Rendered via ANSI escape codes: `\x1b[{n}A` to move cursor up, `\r` to overwrite lines. Uses `process.stdout.isTTY` to detect.

**Non-TTY mode** (piped output):
```
[03:42] Task 3 done (2m 14s) → task-3-pick-sunday-magazine.v2.md
[03:42] Task 4 started
```

Simple line-by-line append. No cursor manipulation.

### Task 7: Retry Failed Tasks

**Purpose**: Give transient failures a second chance without blocking the happy path.

**Components**:
- Failure collector in batch orchestrator
- Retry wave at end of run

**Logic**:
```
1. After all waves complete, collect tasks where success === false
2. If failures.length > 0 AND --no-retry not set:
   a. Log: "Retrying {n} failed tasks..."
   b. runBatch(failures, concurrency, generateOneTask)
   c. Merge retry results into main results
3. Report final status: {passed}/{total} succeeded, {failed} failed
4. If any still failed: log task numbers + error messages, exit code 1
```

**No exponential backoff** — the retry is a single pass. If a task fails twice, the issue is likely not transient (prompt too large, API error, malformed epic row). The operator should investigate.

### Task 8: Integration Tests

**Purpose**: Automated verification of wave grouping, CLI parsing, and end-to-end parallel generation.

**Components**:
- `scripts/regen-task.test.mjs` — using `node:test` runner (matches existing `deviation-report.test.mjs`)

**Test cases**:

```javascript
// Wave grouping
test('linearDeps_producesOneTaskPerWave', () => { ... });
test('independentTasks_allInWaveZero', () => { ... });
test('diamondDeps_threeWaves', () => { ... });
test('cyclicDeps_throwsWithCyclePath', () => { ... });
test('isolatedTask_landsInWaveZero', () => { ... });

// CLI parsing
test('parallelFlag_parsesNumericValue', () => { ... });
test('parallelFlagNoValue_defaultsTo3', () => { ... });
test('allFlag_setsGenerateAll', () => { ... });
test('noRetryFlag_disablesRetry', () => { ... });

// Integration (requires running server with AI_PROVIDER=mock)
test('allParallel2_generatesAllTaskFiles', async () => { ... });
test('singleTask_backwardCompatible', async () => { ... });
```

**npm script**: `"test:regen": "node --test scripts/regen-task.test.mjs"` added to `package.json`.

---

## Execution Flow

```
[Wave 0]  No-dependency tasks
   Task 1 ──┐
   Task 2 ──┤  (parallel, up to N)
   Task 3 ──┘
      │
      ▼  rebuild prior-tasks context
[Wave 1]  Depends on wave-0 tasks
   Task 4 ──┐
   Task 5 ──┘  (parallel, up to N)
      │
      ▼  rebuild prior-tasks context
[Wave 2]  Depends on wave-1 tasks
   Task 6 ──→ Task 7
      │
      ▼
[Retry]   Failed tasks from any wave
   Task X ──┐
   Task Y ──┘  (one retry pass)
      │
      ▼
[Report]  Summary table + exit code
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Concurrency limiter | Hand-rolled Promise pool | ~20 lines, no new dependency, batched-wave model is simpler than a continuous pool. `p-limit` adds a dependency for functionality we can write in a `for` loop |
| Dependency handling for `--all` | Dependency-aware waves | Prior-tasks context is what makes guides executor-ready. Stale context = lower quality guides = more executor deviations. The ~30% speed cost vs. blast-all is worth the quality guarantee |
| Default concurrency | 3 | Proven safe in session testing (pre-600s fix). Conservative default; operator can override with `--parallel 5` after running the ceiling test |
| Retry strategy | Single retry pass at end | No backoff, no per-wave retry. Transient failures (timeout, network blip) get one more chance. Persistent failures surface immediately. Keeps logic simple |
| Progress reporting | ANSI in-place updates (TTY) / line append (non-TTY) | Matches common CLI tool UX (docker pull, npm install). Degrades gracefully when piped |
| No server changes | Script-only orchestration | Express already handles concurrent requests. Adding server-side queuing would be infrastructure-before-features. The bottleneck is script-level serial execution, not server capacity |
| Test runner | `node:test` (built-in) | Matches existing `deviation-report.test.mjs` and `server.test.js` conventions. No test framework dependency |
| Where to put new code | All in `regen-task.mjs` | Single file, ~100 lines of new code. Extracting to separate modules would be premature — there's exactly one consumer. If a second script needs wave grouping, extract then |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
```

