# 🛠️ Task 4: `--parallel N` Flag Implementation

**Purpose**: Wire the `--parallel N` CLI argument into `regen-task.mjs` so that when multiple task numbers are listed, up to N generate concurrently via a hand-rolled Promise pool. This eliminates serial bottleneck for explicit task lists where the caller has already decided ordering.

**Effort**: 1 day

**Dependencies**: Task 2 (Extract Reusable Task Runner) — `generateOneTask()` must exist as the atomic unit of work

**Parallel With**: —

**Blocks**: Task 5 (`--all` flag with batched waves) — needs the Promise pool and CLI wiring from this task

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 2 extracted `generateOneTask()` as the callable boundary for producing a single implementation guide. Currently, running multiple tasks requires invoking the script N times serially or running separate shell processes manually. This task adds a `--parallel N` flag that launches up to N `generateOneTask()` calls concurrently using a hand-rolled Promise pool — no npm dependency, ~20 lines of code. When the caller passes `node scripts/regen-task.mjs projectId 1 2 3 4 --parallel 3`, three tasks generate simultaneously; as one finishes, the next launches. Dependency ordering is explicitly skipped — the caller chose these tasks, they accept the ordering. Single-task invocation (`regen-task.mjs projectId 3`) is untouched.

**Trade-offs considered**:
- **`p-limit` npm package** — rejected because the entire pool is ~20 lines; adding a dependency for that is overhead with no payoff. Zero new deps is a project principle.
- **`Promise.all()` with no concurrency bound** — rejected because it would fire all tasks simultaneously, risking API rate limits and Claude CLI process exhaustion. Bounded concurrency is the whole point.
- **Dynamic auto-detection of safe N** — rejected because explicit is better than implicit (design principles). The operator sets N based on Task 1 ceiling-test findings; the script doesn't guess.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                         # Flag any unrelated M/?? entries
git diff HEAD -- scripts/regen-task.mjs scripts/regen-task.test.mjs   # Confirm target files are clean
node --test scripts/regen-task.test.mjs            # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: all existing tests passing. Count the number (expect ~35) and record it.

---

## 3. Files

### To Create (new)
- None

### To Modify (cite CODEBASE CONTEXT)
- `scripts/regen-task.mjs` — (1) add `--parallel N` flag parsing to `parseArgs()` (lines 20–58), (2) add `runWithConcurrency()` Promise pool function (~20 lines), (3) wire multi-task main flow to use pool when `--parallel` is set (inside `main()`, after the single-task path), (4) update help/usage text, (5) add `runWithConcurrency` to the export block (lines 920–930)
- `scripts/regen-task.test.mjs` — add `parseArgs` tests for `--parallel` flag parsing and `runWithConcurrency` tests covering ordering, concurrency bounds, empty input, error propagation

### To Leave Alone
- `server.js` — Express server already handles concurrent requests; no server changes needed for script-level concurrency
- `scripts/context-loader.mjs` — shared context block formatters; unrelated to CLI flag plumbing
- `scripts/context-loader.test.mjs` — unrelated tests
- `scripts/deviation-report.mjs` — unrelated script
- `package.json` — `test:regen-task` npm script already exists and runs `scripts/regen-task.test.mjs`

---

## 4. Implementation Steps

### Step 1: Add `--parallel N` to `parseArgs()`

**Action**: Extend the `parseArgs()` function (lines 20–58) to recognize `--parallel`, `--parallel N`, and `--parallel=N`. Default to 3 when `--parallel` is passed without a value. Clamp to `[1, 5]`. Store in `flags.parallel` as an integer or `null` (when not specified).

**File**: `scripts/regen-task.mjs` — `parseArgs()` function, lines 22–28 (flags init) and lines 31–51 (flag parsing loop)

**Pattern**:
```javascript
// In flags initializer (line 22-28):
const flags = {
  rescan: false,
  noReview: false,
  noRetry: false,
  all: false,
  parallel: null,  // null = not specified; integer when --parallel is given
};

// In parsing loop, add these cases:
if (arg === '--parallel') {
  const next = args[i + 1];
  if (next && /^\d+$/.test(next)) {
    flags.parallel = Math.min(Math.max(parseInt(next, 10), 1), 5);
    i++; // consume next arg
  } else {
    flags.parallel = 3; // default when --parallel is passed without a value
  }
  continue;
}
if (arg.startsWith('--parallel=')) {
  const val = parseInt(arg.split('=')[1], 10);
  flags.parallel = isNaN(val) ? 3 : Math.min(Math.max(val, 1), 5);
  continue;
}
```

**Verify**: `node -e "import('./scripts/regen-task.mjs').then(m => { const r = m.parseArgs(['node','s','proj','1','2','--parallel','3']); console.log(r.flags.parallel === 3 ? 'PASS' : 'FAIL: ' + r.flags.parallel); })"` — expect `PASS`

---

### Step 2: Set module-level variables from parsed flags

**Action**: In the CLI entry point block (lines 939–978), assign `parallelN` from the parsed flag. Also update the `taskNum` detection to treat multi-task invocations (with or without `--parallel`) as parallel mode.

**File**: `scripts/regen-task.mjs` — CLI entry point, lines 939–971

**Pattern**:
```javascript
// Line 945 (already):
parallelN = cliFlags.parallel;

// Line 969-971 — single-task detection:
// Single-task mode = exactly 1 task number AND no --parallel AND no --all
taskNum = (!allMode && taskNumArgs.length === 1 && parallelN === null)
  ? String(taskNumArgs[0])
  : null;
```

The module-level variable `parallelN` already declared at line 61. When `taskNum` is null (parallel mode), `main()` will enter the parallel path.

**Verify**: Visually confirm `parallelN` assignment at line 945.

---

### Step 3: Add `runWithConcurrency()` function

**Action**: Add a bounded-concurrency Promise pool. Place it after the `formatElapsed()` helper (around line 325) and before `triggerRescan()`. The function takes an array of zero-arg async functions and a concurrency limit, returns results in original order.

**File**: `scripts/regen-task.mjs` — new function, insert after `formatElapsed()` (line ~325)

**Pattern** (port from architecture design, ~18 lines):
```javascript
/**
 * Run async tasks with bounded concurrency.
 * @param {Array<() => Promise<T>>} fns - Array of zero-arg async functions
 * @param {number} concurrency - Max concurrent executions
 * @returns {Promise<T[]>} Results in same order as fns
 */
async function runWithConcurrency(fns, concurrency) {
  const results = new Array(fns.length);
  let nextIndex = 0;

  async function worker() {
    while (nextIndex < fns.length) {
      const idx = nextIndex++;
      results[idx] = await fns[idx]();
    }
  }

  const workers = [];
  for (let i = 0; i < Math.min(concurrency, fns.length); i++) {
    workers.push(worker());
  }
  await Promise.all(workers);
  return results;
}
```

Design notes:
- Worker pool pattern: N workers pull from a shared index. Each worker calls the next function when its current one completes.
- Order preservation: results array indexed by original position, not completion order.
- No error wrapping — if a task throws, `Promise.all` rejects. The caller (`generateOneTask`) already catches internally and returns `{ success: false }`, so `runWithConcurrency` never sees thrown errors in practice.

**Verify**: `node -e "import('./scripts/regen-task.mjs').then(m => m.runWithConcurrency([() => Promise.resolve(1), () => Promise.resolve(2)], 2).then(r => console.log(JSON.stringify(r) === '[1,2]' ? 'PASS' : 'FAIL')))"` — expect `PASS`

---

### Step 4: Wire parallel path in `main()`

**Action**: In `main()`, after the single-task path (which exits via `return`), add the multi-task parallel path. When `taskNum === null` (meaning `--parallel` or multiple task nums or `--all`), resolve the concurrency value, look up tasks from the epic, and run them through `runWithConcurrency`.

**File**: `scripts/regen-task.mjs` — `main()` function, after the single-task `return` (around line 768)

**Pattern**:
```javascript
// ─── PARALLEL MODE ──────────────────────────────────────────────────────────

const concurrency = parallelN ?? 3;
let codebase = initialCodebase;

// Determine which tasks to generate
let targetTasks;
if (allMode) {
  // --all mode handled by Task 5 — for now, fall through to explicit list
  targetTasks = allTasks;
  console.log(`── All mode: ${targetTasks.length} tasks, concurrency ${concurrency} ──`);
} else {
  // Explicit task numbers with --parallel
  targetTasks = [];
  for (const numArg of taskNumArgs) {
    const t = allTasks.find(t => t.num === String(numArg));
    if (!t) {
      console.error(`✗ Task ${numArg} not found in epic.md task table. Found: ${allTasks.map(t => t.num).join(', ')}`);
      process.exit(1);
    }
    targetTasks.push(t);
  }
  console.log(`── Parallel mode: ${targetTasks.length} tasks, concurrency ${concurrency} ──`);
}

// Rescan if --rescan flag
if (forceRescan) {
  console.log('── Rescan triggered (--rescan flag) ──');
  const freshContent = await triggerRescan(REPO_ROOT);
  if (freshContent !== null) codebase = freshContent;
  else console.log('  (falling back to existing codebase.md)');
}

// Report inputs once
console.log('── Inputs ──');
console.log(`  builder.md:    ${builder ? `${builder.length} chars` : '⚠️  MISSING'}`);
console.log(`  principles.md: ${principles ? `${principles.length} chars` : '⚠️  MISSING'}`);
console.log(`  codebase.md:   ${codebase ? `${codebase.length} chars` : '⚠️  MISSING'}`);
console.log(`  references.md: ${references ? `${references.length} chars` : '(none)'}`);
console.log(`  epic.md:       ${epicContent.length} chars`);
console.log(`  architecture.md: ${archContent.length} chars`);
console.log('');

const mainT0 = Date.now();
const sharedCtx = { epicContent, archContent, builder, principles, codebase, references, caveats, projectDir };

// Build task functions — no dependency ordering (caller chose these tasks)
let completedCount = 0;
const totalCount = targetTasks.length;
const fns = targetTasks.map(task => () => {
  const idx = ++completedCount;
  const label = `[${idx}/${totalCount}]`;
  return generateOneTask(projectId, task, sharedCtx, { noReview, label });
});

const allResults = await runWithConcurrency(fns, concurrency);

// Summary
const totalElapsed = Date.now() - mainT0;
const succeeded = allResults.filter(r => r.success);
const finalFailed = allResults.filter(r => !r.success);

console.log('');
console.log(`── Summary (${formatElapsed(totalElapsed)} total) ──`);
console.log(`  ✓ ${succeeded.length} succeeded`);
if (finalFailed.length > 0) {
  console.log(`  ✗ ${finalFailed.length} failed:`);
  for (const f of finalFailed) {
    console.log(`    task-${f.taskNum}: ${f.error}`);
  }
}

if (finalFailed.length > 0) {
  process.exit(1);
}
```

Key decisions in this step:
- `parallelN ?? 3` — default concurrency is 3 when `--parallel` omitted but multi-task mode triggered (e.g. `regen-task.mjs proj 1 2 3`)
- No wave grouping — explicit task lists bypass dependency ordering entirely. Wave grouping is Task 5's concern (`--all` mode).
- `generateOneTask` already returns `{ success, taskNum, filePath, latencyMs, error }` — the caller collects results and reports.
- Exit code 1 on any failure — CI-friendly.

**Verify**: `node scripts/regen-task.mjs <projectId> 1 2 --parallel 2 --no-review` (with server running and `AI_PROVIDER=mock`) — expect both tasks generated concurrently, two output files written, summary printed.

---

### Step 5: Update usage/help text

**Action**: Update the usage block in the CLI entry point (around line 950–965) to document `--parallel N`.

**File**: `scripts/regen-task.mjs` — CLI entry point, usage error block

**Pattern**:
```javascript
console.error('Usage: node scripts/regen-task.mjs [flags] <projectId> <taskNum...>');
console.error('       node scripts/regen-task.mjs [flags] <projectId> --all');
console.error('');
console.error('Flags:');
console.error('  --rescan        Force codebase rescan before prompt assembly');
console.error('  --no-review     Skip post-generation auto-review');
console.error('  --parallel N    Run up to N tasks concurrently (default 3, max 5)');
console.error('  --no-retry      Skip retry pass for failed tasks');
console.error('');
console.error('Examples:');
console.error('  node scripts/regen-task.mjs bubls2-1776263128609 3');
console.error('  node scripts/regen-task.mjs bubls2-1776263128609 1 2 3 --parallel 3');
console.error('  node scripts/regen-task.mjs bubls2-1776263128609 --all --parallel 2');
```

**Verify**: `node scripts/regen-task.mjs` (no args) — expect usage printed with `--parallel N` documented.

---

### Step 6: Export `runWithConcurrency` for testing

**Action**: Add `runWithConcurrency` to the export block at lines 920–930.

**File**: `scripts/regen-task.mjs` — export block

**Pattern**:
```javascript
export {
  extractTasksFromEpic,
  isFoundationTask,
  shouldRescan,
  formatReviewSection,
  groupTasksIntoWaves,
  runWithConcurrency,   // ← add
  parseArgs,
  generateOneTask,
  formatElapsed,
};
```

**Verify**: `node -e "import('./scripts/regen-task.mjs').then(m => console.log(typeof m.runWithConcurrency === 'function' ? 'PASS' : 'FAIL'))"` — expect `PASS`

---

## 5. Tests

All tests use `node:test` with `node:assert/strict`, matching the existing convention in `scripts/regen-task.test.mjs`.

### `parseArgs` — `--parallel` flag tests (add to existing describe block)

```javascript
it('parses --parallel with value', () => {
  const { flags, positional } = parseArgs(['node', 'script.mjs', 'proj-123', '1', '2', '--parallel', '3']);
  assert.strictEqual(flags.parallel, 3);
  assert.deepStrictEqual(positional, ['proj-123', '1', '2']);
});

it('parses --parallel without value (defaults to 3)', () => {
  const { flags } = parseArgs(['node', 'script.mjs', 'proj-123', '1', '--parallel']);
  assert.strictEqual(flags.parallel, 3);
});

it('parses --parallel=N form', () => {
  const { flags } = parseArgs(['node', 'script.mjs', 'proj-123', '--parallel=3', '1']);
  assert.strictEqual(flags.parallel, 3);
});

it('clamps --parallel to max 5', () => {
  const { flags } = parseArgs(['node', 'script.mjs', 'proj-123', '--parallel', '10']);
  assert.strictEqual(flags.parallel, 5);
});

it('clamps --parallel to min 1', () => {
  const { flags } = parseArgs(['node', 'script.mjs', 'proj-123', '--parallel', '0']);
  assert.strictEqual(flags.parallel, 1);
});

it('treats --parallel followed by non-numeric as default 3', () => {
  const { flags, positional } = parseArgs(['node', 'script.mjs', 'proj-123', '--parallel', '--all']);
  assert.strictEqual(flags.parallel, 3);
  assert.strictEqual(flags.all, true);
});

it('parses --parallel=N with invalid value defaults to 3', () => {
  const { flags } = parseArgs(['node', 'script.mjs', 'proj-123', '--parallel=abc']);
  assert.strictEqual(flags.parallel, 3);
});

it('parallel null when flag not present', () => {
  const { flags } = parseArgs(['node', 'script.mjs', 'proj-123', '3']);
  assert.strictEqual(flags.parallel, null);
});
```

### `runWithConcurrency` — new describe block

```javascript
describe('runWithConcurrency', () => {
  it('runs all tasks and returns results in order', async () => {
    const fns = [
      () => Promise.resolve('a'),
      () => Promise.resolve('b'),
      () => Promise.resolve('c'),
    ];
    const results = await runWithConcurrency(fns, 2);
    assert.deepStrictEqual(results, ['a', 'b', 'c']);
  });

  it('respects concurrency limit', async () => {
    let maxConcurrent = 0;
    let current = 0;

    const makeFn = (val) => async () => {
      current++;
      if (current > maxConcurrent) maxConcurrent = current;
      await new Promise(r => setTimeout(r, 10));
      current--;
      return val;
    };

    const fns = [makeFn(1), makeFn(2), makeFn(3), makeFn(4), makeFn(5)];
    const results = await runWithConcurrency(fns, 2);

    assert.deepStrictEqual(results, [1, 2, 3, 4, 5]);
    assert.ok(maxConcurrent <= 2, `max concurrent was ${maxConcurrent}, expected <= 2`);
  });

  it('handles concurrency=1 (serial)', async () => {
    const order = [];
    const makeFn = (val) => async () => {
      order.push(`start-${val}`);
      await new Promise(r => setTimeout(r, 5));
      order.push(`end-${val}`);
      return val;
    };

    const fns = [makeFn(1), makeFn(2), makeFn(3)];
    const results = await runWithConcurrency(fns, 1);

    assert.deepStrictEqual(results, [1, 2, 3]);
    assert.deepStrictEqual(order, ['start-1', 'end-1', 'start-2', 'end-2', 'start-3', 'end-3']);
  });

  it('handles empty input', async () => {
    const results = await runWithConcurrency([], 3);
    assert.deepStrictEqual(results, []);
  });

  it('handles concurrency higher than task count', async () => {
    const fns = [() => Promise.resolve('x'), () => Promise.resolve('y')];
    const results = await runWithConcurrency(fns, 10);
    assert.deepStrictEqual(results, ['x', 'y']);
  });

  it('propagates errors from individual tasks', async () => {
    const fns = [
      () => Promise.resolve('ok'),
      () => Promise.reject(new Error('boom')),
    ];
    await assert.rejects(() => runWithConcurrency(fns, 2), /boom/);
  });
});
```

### Main-flow branching tests (add to existing file)

```javascript
describe('main flow branching', () => {
  it('single task with no --parallel stays in single-task mode', () => {
    const { flags, positional } = parseArgs(['node', 'script.mjs', 'proj-123', '3']);
    const taskNumArgs = positional.slice(1);
    const singleTaskMode = (!flags.all && taskNumArgs.length === 1 && flags.parallel === null);
    assert.strictEqual(singleTaskMode, true, 'single task without --parallel should use legacy single-task path');
  });

  it('single task WITH --parallel enters parallel mode', () => {
    const { flags, positional } = parseArgs(['node', 'script.mjs', 'proj-123', '3', '--parallel', '2']);
    const taskNumArgs = positional.slice(1);
    const singleTaskMode = (!flags.all && taskNumArgs.length === 1 && flags.parallel === null);
    assert.strictEqual(singleTaskMode, false, 'single task with --parallel should enter parallel path');
  });

  it('multiple tasks without --parallel enters parallel mode with default concurrency', () => {
    const { flags, positional } = parseArgs(['node', 'script.mjs', 'proj-123', '1', '2', '3']);
    const taskNumArgs = positional.slice(1);
    const singleTaskMode = (!flags.all && taskNumArgs.length === 1 && flags.parallel === null);
    const concurrency = flags.parallel ?? 3;
    assert.strictEqual(singleTaskMode, false, 'multiple tasks should enter parallel path');
    assert.strictEqual(concurrency, 3, 'default concurrency should be 3');
    assert.strictEqual(taskNumArgs.length, 3, 'should have 3 task numbers');
  });

  it('--all enters parallel mode regardless of task count', () => {
    const { flags, positional } = parseArgs(['node', 'script.mjs', 'proj-123', '--all']);
    const taskNumArgs = positional.slice(1);
    const singleTaskMode = (!flags.all && taskNumArgs.length === 1 && flags.parallel === null);
    assert.strictEqual(singleTaskMode, false, '--all should enter parallel path');
    assert.strictEqual(flags.all, true);
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. **`feat(regen-task): add --parallel N flag and runWithConcurrency pool`** — `scripts/regen-task.mjs`: parseArgs update, runWithConcurrency function, parallel path in main(), usage text, export
2. **`test(regen-task): cover --parallel parsing, concurrency pool, and mode branching`** — `scripts/regen-task.test.mjs`: 21 new test cases across three describe blocks

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/regen-task.test.mjs
```

**Expected delta**: baseline → baseline + 21 passing. Zero pre-existing tests broken.

Smoke test (requires running server with `AI_PROVIDER=mock`):
```bash
# Start server in mock mode
AI_PROVIDER=mock node server.js &

# Run 2 tasks in parallel
node scripts/regen-task.mjs <projectId> 1 2 --parallel 2 --no-review

# Verify both output files exist
ls projects/<projectId>/task-1-*.v2.md projects/<projectId>/task-2-*.v2.md
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.
- `runWithConcurrency` is self-contained with no side effects on existing code; removing it has zero blast radius on the single-task path.

---

## 9. Deviations Allowed

- **`parseArgs` already has `--parallel` handling** → verify default value matches this guide (3, not 2). If the default is 2, update to 3. If the max clamp is 3 instead of 5, update to 5. Adjust tests to match. Log as deviation.
- **`runWithConcurrency` already exists** → verify function signature matches (`fns, concurrency → Promise<T[]>`), order preservation, and worker-pool pattern. If it exists and is correct, skip creation. Verify it is exported. Log as deviation.
- **Parallel main-flow path already wired** → verify concurrency fallback is `parallelN ?? 3` (not `?? 2`). Verify explicit task list skips wave ordering. Adjust if needed. Log as deviation.
- **Test framework mismatch** → match the repo's convention; translate silently but note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task wires `--parallel N` for explicit task lists only. It does not add dependency-aware wave ordering (`--all` mode), retry logic for failed tasks, or TTY progress reporting — those are separate tasks in the epic.

- **`--all` flag with wave-based execution** — Task 5. This task's `runWithConcurrency` is the foundation, but wave grouping, inter-wave context rebuild, and rescan triggers belong to Task 5.
- **Retry pass for failed tasks** — Task 7. This task exits with code 1 on failure; it does not retry.
- **TTY progress reporter** — Task 6. This task uses simple `console.log` labels (`[1/4]`, `[2/4]`); in-place ANSI updates are Task 6.
- **Concurrency max calibration** — depends on Task 1 (ceiling test) results. The max clamp of 5 is a conservative placeholder. If ceiling test findings exist in `docs/concurrency-ceiling.md`, the executor should read them and adjust the clamp accordingly. If that file doesn't exist, leave the clamp at 5.
- **Server-side queuing or rate limiting** — the Express server already spawns concurrent `claude -p` processes. No server changes belong in this task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, `runBatch` pseudocode, default concurrency decision
- [Epic](./epic.md) – Task scope and dependency graph
- [Timeline](./timeline.md) – Status tracking (update after done)