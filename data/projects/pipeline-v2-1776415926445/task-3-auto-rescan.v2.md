The file write was denied. Here's the complete implementation guide — I'll present it directly:

---

# 🛠️ Task 3: Auto-Rescan

**Purpose**: Keep `codebase.md` fresh by adding a `--rescan` flag to `regen-task.mjs` that calls the `/api/ai/text/scan` endpoint before prompt assembly, and by auto-detecting foundation tasks from the epic's task table so downstream specs receive up-to-date codebase context.

**Effort**: 1 day

**Dependencies**: None

**Parallel With**: Tasks 1, 2, 4

**Blocks**: —

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Pipeline V2's session data showed 18 stale-path deviations when generating specs for tasks that depended on a foundation task's structural changes — the executor cited paths from a stale `codebase.md` that no longer existed after Task 1 shipped. The fix is to rescan the target repo before building the prompt whenever the current task depends on a foundation task (a task that multiple downstream tasks list as a dependency). The `/api/ai/text/scan` endpoint already exists in `server.js:1195` and writes `codebase.md`; this task wires it into the `regen-task.mjs` CLI. A `--rescan` flag provides explicit override for any task, and auto-detection handles the common case without operator memory.

**Trade-offs considered** (≤3 bullets):
- **Rescan every task** — rejected because it doubles API calls (each scan takes 30-60s via Claude CLI) with no observed benefit for parallel/sibling tasks
- **Rescan manually via `curl` before running `regen-task.mjs`** — rejected because it relies on operator memory, which is exactly what Pipeline V2 eliminates
- **Rescan after foundation tasks only + explicit `--rescan` flag** — preferred because session evidence shows only foundation-dependent tasks had stale-context deviations, and the flag covers edge cases

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- scripts/regen-task.mjs       # Confirm target file is clean
node --test server.test.js                    # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 88/88 passing (server.test.js has 88 `it()` blocks).

---

## 3. Files

### To Create (new)
- `scripts/regen-task.test.mjs` — Unit tests for `extractTasksFromEpic()`, `isFoundationTask()`, `shouldRescan()` covering: epic table parsing, foundation detection logic, rescan trigger conditions, `--rescan` flag override. **(new)** — Note: Task 1 in the epic also lists a test file at this same path. If Task 1 has already created this file, append to it. If not, create it.

### To Modify (cite CODEBASE CONTEXT)
- `scripts/regen-task.mjs` — Current state: CLI takes `<projectId> <taskNum>` positional args, `extractTasksFromEpic()` parses num/name/effort but ignores Dependencies column, `main()` loads `codebase.md` from disk at line 322 with no rescan. Target state: accept `--rescan` flag, parse Dependencies column, detect foundation tasks, call `/api/ai/text/scan` before loading `codebase.md` when triggered.

### To Leave Alone
- `server.js` — The `/api/ai/text/scan` endpoint (line 1195) already exists and works; this task is a consumer, not a modifier
- `server.test.js` — Existing 88 tests unchanged; new tests go in `scripts/regen-task.test.mjs`
- `server.integration.test.js` — Integration tests are for the running API; rescan logic is script-side

---

## 4. Implementation Steps

### Step 1: Extend `extractTasksFromEpic()` to capture the Dependencies column

**Action**: Modify the regex in `extractTasksFromEpic()` to capture the Dependencies column (column 3 in the epic's task table). Return a `deps` array on each task object. `"None"` maps to `[]`.

**File**: `scripts/regen-task.mjs` (line 107-118)

**Pattern**:
```javascript
function extractTasksFromEpic(epicContent) {
  const tasks = [];
  for (const line of epicContent.split('\n')) {
    const match = line.match(
      /^\|\s*(\d+)\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*(?:High|Medium|Low|Critical)\s*\|/,
    );
    if (match) {
      const depsRaw = match[3].trim();
      const deps = depsRaw === 'None' ? [] : depsRaw.split(',').map(d => d.trim()).filter(Boolean);
      tasks.push({ num: match[1], name: match[2].trim(), deps, effort: match[5].trim() });
    }
  }
  return tasks;
}
```

**Verify**: `node -e "import('./scripts/regen-task.mjs')"` — no syntax errors.

### Step 2: Add `isFoundationTask()` and `shouldRescan()` helpers

**Action**: Add two pure functions after `extractTasksFromEpic`, before `buildImplementationGuidePrompt`.

**File**: `scripts/regen-task.mjs`

**Pattern**:
```javascript
function isFoundationTask(taskNum, allTasks) {
  const self = allTasks.find(t => t.num === taskNum);
  if (!self || self.deps.length > 0) return false;
  const dependents = allTasks.filter(t => t.deps.includes(taskNum));
  return dependents.length >= 2;
}

function shouldRescan(taskNum, allTasks, forceRescan) {
  if (forceRescan) return true;
  const self = allTasks.find(t => t.num === taskNum);
  if (!self) return false;
  return self.deps.some(depNum => isFoundationTask(depNum, allTasks));
}
```

**Verify**: Pure functions, no side effects. Tested in Step 7.

### Step 3: Add `triggerRescan()` function

**Action**: Add an async function that POSTs to the scan endpoint using the same `execSync`+`curl` pattern from `main()` line 379-386. Non-fatal on failure — returns `null` and logs a warning.

**File**: `scripts/regen-task.mjs` (after helpers, before `main()`)

**Pattern**:
```javascript
async function triggerRescan(workspacePath) {
  console.log(`⟳ Rescanning codebase at ${workspacePath}…`);
  const payloadFile = `/tmp/regen-task-rescan.json`;
  await fs.writeFile(payloadFile, JSON.stringify({ workspacePath }));
  let rawResponse;
  try {
    rawResponse = execSync(
      `curl -sS -X POST ${API_BASE}/api/ai/text/scan -H 'Content-Type: application/json' --data-binary @${payloadFile} --max-time 300`,
      { maxBuffer: 50 * 1024 * 1024, timeout: 310_000 },
    ).toString();
  } catch (err) {
    console.error(`⚠ Rescan failed (non-fatal): ${err.message}`);
    return null;
  }
  const parsed = JSON.parse(rawResponse);
  if (parsed.error) {
    console.error(`⚠ Rescan API error (non-fatal): ${parsed.error}`);
    return null;
  }
  console.log(`✓ Rescanned codebase.md (${parsed.content.length} chars)`);
  return parsed.content;
}
```

**Verify**: Syntactically valid. Integration test requires running server (manual).

### Step 4: Parse `--rescan` flag from CLI arguments

**Action**: Replace lines 15-21 to filter `--rescan` from args before extracting positional params.

**File**: `scripts/regen-task.mjs` (lines 15-21)

**Pattern**:
```javascript
const args = process.argv.slice(2);
const forceRescan = args.includes('--rescan');
const positional = args.filter(a => !a.startsWith('--'));
const [projectId, taskNumArg] = positional;

if (!projectId || !taskNumArg) {
  console.error('Usage: node scripts/regen-task.mjs [--rescan] <projectId> <taskNum>');
  console.error('  --rescan   Force codebase rescan before prompt assembly');
  console.error('Example: node scripts/regen-task.mjs bubls2-1776263128609 3');
  console.error('Example: node scripts/regen-task.mjs --rescan bubls2-1776263128609 3');
  process.exit(1);
}
const taskNum = String(taskNumArg);
```

**Verify**: `node scripts/regen-task.mjs` with no args — prints usage with `--rescan`, exits 1.

### Step 5: Wire rescan into `main()`

**Action**: Three changes in `main()`:

1. Rename destructured `codebase` to `initialCodebase` at line 322
2. After task lookup (line 346), insert rescan trigger block
3. Update codebase report line (line 352) to annotate rescans

**File**: `scripts/regen-task.mjs` (inside `main()`)

**Change 1** — line 319:
```javascript
  const [builder, principles, initialCodebase, references, caveats] = await Promise.all([
```

**Change 2** — after task lookup, before "4. Report inputs":
```javascript
  // 3b. Rescan codebase if --rescan flag or task depends on a foundation task
  let codebase = initialCodebase;
  if (shouldRescan(taskNum, tasks, forceRescan)) {
    const reason = forceRescan
      ? '--rescan flag'
      : `depends on foundation task(s): ${task.deps.filter(d => isFoundationTask(d, tasks)).join(', ')}`;
    console.log(`── Rescan triggered (${reason}) ──`);
    const freshContent = await triggerRescan(REPO_ROOT);
    if (freshContent !== null) {
      codebase = freshContent;
    } else {
      console.log('  (falling back to existing codebase.md)');
    }
  }
```

**Change 3** — replace codebase report line:
```javascript
  console.log(`  codebase.md:   ${codebase ? `${codebase.length} chars` : '⚠️  MISSING'}${codebase !== initialCodebase ? ' (freshly rescanned)' : ''}`);
```

**Verify**: `node scripts/regen-task.mjs pipeline-v2-1776415926445 3` — no rescan (Task 3 has `None` deps). `node scripts/regen-task.mjs --rescan pipeline-v2-1776415926445 3` — prints "Rescan triggered (--rescan flag)".

### Step 6: Export helpers for testing

**Action**: Add named exports before `main().catch(...)`.

**File**: `scripts/regen-task.mjs`

**Pattern**:
```javascript
export { extractTasksFromEpic, isFoundationTask, shouldRescan };
```

**Verify**: ESM file — `export` is valid alongside existing `import` statements at lines 6-9.

---

## 5. Tests

File: `scripts/regen-task.test.mjs` **(new)**

Tests use `node:test` + `node:assert/strict` matching `server.test.js` line 17.

```javascript
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

const originalArgv = process.argv;
process.argv = ['node', 'regen-task.mjs', 'fake-project', '1'];
const { extractTasksFromEpic, isFoundationTask, shouldRescan } = await import('./regen-task.mjs');
process.argv = originalArgv;

describe('extractTasksFromEpic', () => {
  const EPIC_TABLE = `
| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Preamble Strip** | None | 2, 4 | 0.5 day | High |
| 2 | **Caveats Injection** | None | 1, 4 | 0.5 day | High |
| 3 | **Auto-Rescan** | 1 | 4 | 1 day | High |
| 4 | **Auto-Review** | 1, 2 | 3 | 1 day | High |
| 5 | **Deviation-Count Parser** | None | -- | 1 day | Medium |
`;

  it('parses all five tasks', () => {
    const tasks = extractTasksFromEpic(EPIC_TABLE);
    assert.equal(tasks.length, 5, 'should find 5 tasks');
  });

  it('parses "None" dependencies as empty array', () => {
    const tasks = extractTasksFromEpic(EPIC_TABLE);
    const task1 = tasks.find(t => t.num === '1');
    assert.deepStrictEqual(task1.deps, []);
  });

  it('parses single dependency', () => {
    const tasks = extractTasksFromEpic(EPIC_TABLE);
    const task3 = tasks.find(t => t.num === '3');
    assert.deepStrictEqual(task3.deps, ['1']);
  });

  it('parses comma-separated dependencies', () => {
    const tasks = extractTasksFromEpic(EPIC_TABLE);
    const task4 = tasks.find(t => t.num === '4');
    assert.deepStrictEqual(task4.deps, ['1', '2']);
  });

  it('preserves name and effort fields', () => {
    const tasks = extractTasksFromEpic(EPIC_TABLE);
    const task1 = tasks.find(t => t.num === '1');
    assert.equal(task1.name, 'Preamble Strip');
    assert.equal(task1.effort, '0.5 day');
  });

  it('returns empty array for non-table content', () => {
    const tasks = extractTasksFromEpic('# Just a heading\n\nSome text.');
    assert.deepStrictEqual(tasks, []);
  });
});

describe('isFoundationTask', () => {
  const TASKS = [
    { num: '1', name: 'A', deps: [], effort: '1 day' },
    { num: '2', name: 'B', deps: [], effort: '1 day' },
    { num: '3', name: 'C', deps: ['1'], effort: '1 day' },
    { num: '4', name: 'D', deps: ['1', '2'], effort: '1 day' },
    { num: '5', name: 'E', deps: [], effort: '1 day' },
  ];

  it('returns true for task with no deps and ≥2 dependents', () => {
    assert.equal(isFoundationTask('1', TASKS), true);
  });

  it('returns false for task with only one dependent', () => {
    assert.equal(isFoundationTask('2', TASKS), false);
  });

  it('returns false for task that has its own dependencies', () => {
    assert.equal(isFoundationTask('3', TASKS), false);
  });

  it('returns false for task with no dependents at all', () => {
    assert.equal(isFoundationTask('5', TASKS), false);
  });

  it('returns false for unknown task number', () => {
    assert.equal(isFoundationTask('99', TASKS), false);
  });
});

describe('shouldRescan', () => {
  const TASKS = [
    { num: '1', name: 'A', deps: [], effort: '1 day' },
    { num: '2', name: 'B', deps: [], effort: '1 day' },
    { num: '3', name: 'C', deps: ['1'], effort: '1 day' },
    { num: '4', name: 'D', deps: ['1', '2'], effort: '1 day' },
    { num: '5', name: 'E', deps: [], effort: '1 day' },
  ];

  it('returns true when forceRescan is true regardless of deps', () => {
    assert.equal(shouldRescan('5', TASKS, true), true);
  });

  it('returns true when task depends on a foundation task', () => {
    assert.equal(shouldRescan('3', TASKS, false), true);
  });

  it('returns true when task depends on multiple tasks including a foundation', () => {
    assert.equal(shouldRescan('4', TASKS, false), true);
  });

  it('returns false when task has no deps', () => {
    assert.equal(shouldRescan('1', TASKS, false), false);
  });

  it('returns false when task deps are not foundation tasks', () => {
    const tasks = [
      { num: '1', name: 'A', deps: [], effort: '1 day' },
      { num: '2', name: 'B', deps: ['1'], effort: '1 day' },
    ];
    assert.equal(shouldRescan('2', tasks, false), false);
  });

  it('returns false for unknown task number without force', () => {
    assert.equal(shouldRescan('99', TASKS, false), false);
  });
});
```

**Test count**: 6 + 5 + 6 = **17 new tests**.

---

## 6. Commit Plan

1. `feat(regen-task): parse dependency column from epic task table` — `scripts/regen-task.mjs`: extend `extractTasksFromEpic()` regex to capture Dependencies column, return `deps` array
2. `feat(regen-task): add --rescan flag and foundation task detection` — `scripts/regen-task.mjs`: add `isFoundationTask()`, `shouldRescan()`, `triggerRescan()`, CLI flag parsing, rescan wiring in `main()`, exports
3. `test(regen-task): auto-rescan unit tests` — `scripts/regen-task.test.mjs`: 17 tests covering epic parsing, foundation detection, and rescan trigger conditions

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/regen-task.test.mjs
node --test server.test.js
```

**Expected delta**: 17 new tests passing in `scripts/regen-task.test.mjs`. 88 pre-existing tests in `server.test.js` unchanged.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.
- **Rescan is non-destructive**: overwrites `codebase.md` with a fresh scan; old content recoverable by re-running scan.

---

## 9. Deviations Allowed

- **`main()` runs on import**: If `process.argv` manipulation doesn't prevent `main()` from crashing during test import, the executor may wrap `main()` in an `if (import.meta.url === ...)` guard or extract helpers to a separate module. Log: `commit-drift -- added import guard`.
- **Epic table format varies**: If the regex doesn't match a different project's table layout, match what's actually in `projects/pipeline-v2-1776415926445/epic.md`. Log: `env-gap -- epic table format differs`.
- **Task 1 already created `scripts/regen-task.test.mjs`**: Append new `describe` blocks rather than creating fresh. Not a deviation.
- **Prescribed path doesn't exist** → flag it, do not invent.
- **Side-effect required** → STOP, mark [REQUIRES APPROVAL].
- **Step N unlocks obvious simplification for Step N+1** → take it, log deviation.

---

## 10. Out of Scope

This task adds rescan triggering to `regen-task.mjs` only. It does not modify the scan endpoint, does not add rescan to server-side `generate-spec`, and does not build workspace path configuration.

- **Server-side rescan in `generate-spec`** — deferred; epic scopes rescan to the CLI script only
- **Configurable workspace path per project** — deferred; `REPO_ROOT` is the only workspace until multi-workspace is needed
- **Rescan result caching / staleness TTL** — deferred; not needed at current scale
- **Changes to `buildScanPrompt()` or scan output format** — out of scope; scan endpoint is a consumer, not modified
- **Blocking on scan failure** — architecture specifies non-fatal fallback; do not add abort-on-failure

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)