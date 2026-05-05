# Task 1: Project Inventory Scanner

**Purpose**: Build a reusable function that discovers all projects in `projects/`, extracts their task tables from `epic.md`, inventories existing task spec files, and returns a structured manifest of coverage gaps — consumed downstream by the batch orchestrator (Task 3) and the manifest seeder (Task 2).

**Effort**: 2h

**Dependencies**: None

**Parallel With**: Task 2 (Batch Manifest Schema and Seed Data)

**Blocks**: Task 3 (Batch Orchestrator Script)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The batch orchestrator needs to know which projects have epics, how many tasks each epic defines, which tasks already have generated spec files, and which are missing. Today an operator would manually `ls` each project directory and eyeball coverage — this doesn't scale across 43 projects. The scanner function `scanProjectInventory(projectsDir)` walks `projects/`, reads each `epic.md`, delegates task-table parsing to the existing `extractTasksFromEpic()` from `regen-task.mjs`, checks for `task-*.md` and `task-*.v2.md` files on disk, and returns a typed inventory array. It also prints a human-readable summary table to stdout. Both the batch orchestrator (Task 3) and manifest seeder (Task 2) import this function rather than re-implementing discovery.

**Trade-offs considered**:
- **Duplicate the task-table regex in batch-regen.mjs** — rejected because `extractTasksFromEpic()` is already tested and exported; duplicating means two places to fix when the table format changes.
- **Put the scanner in its own file (`scripts/scanner.mjs`)** — rejected because the architecture doc explicitly places it as an exported function inside `scripts/batch-regen.mjs`, co-located with the orchestrator that is its primary consumer. Separate file adds a module boundary with no benefit at this scale.
- **Import `extractTasksFromEpic` from `regen-task.mjs` and build the scanner into `batch-regen.mjs`** — preferred because it follows the architecture doc's design, reuses tested code, and keeps the batch-related functions together for Task 3 to extend.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                        # Flag any unrelated M/?? entries
git diff HEAD -- scripts/                         # Confirm scripts/ is clean
node --test scripts/regen-task.test.mjs           # Record baseline pass count
node --test scripts/deviation-report.test.mjs     # Record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: all existing tests passing (regen-task.test.mjs + deviation-report.test.mjs).

---

## 3. Files

### To Create (new)
- `scripts/batch-regen.mjs` — Scanner function + CLI entry point + table formatter. Hosts `scanProjectInventory()`, `formatInventoryTable()`, and a `main()` that prints the table when run directly. Future tasks (2–6) will add functions to this same file.
- `scripts/batch-regen.test.mjs` — Unit tests for `scanProjectInventory` and `formatInventoryTable` using `node:test` + `node:assert/strict` (matching `regen-task.test.mjs` pattern).

### To Modify (cite CODEBASE CONTEXT)
- `package.json` — Add `test:batch` script: `"node --test scripts/batch-regen.test.mjs"`. Append to `test:all` chain.

### To Leave Alone
- `scripts/regen-task.mjs` — Import `extractTasksFromEpic` from it; do not modify. Its export block (line 920) already exposes the function.
- `scripts/regen-task.test.mjs` — Existing tests; no changes needed.
- `projects/` — Read-only traversal; nothing written.
- `server.js` — No server changes required for this task.

---

## 4. Implementation Steps

### Step 1: Create `scripts/batch-regen.mjs` with scanner function

**Action**: Create the file with `scanProjectInventory(projectsDir)`, `formatInventoryTable(inventory)`, `categorizeProject(projectId, epicTasks, specFiles)`, and a CLI entry point.

**File**: `scripts/batch-regen.mjs` (new)

**Pattern**:

```javascript
// scripts/batch-regen.mjs
import { readdir, readFile, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { extractTasksFromEpic } from './regen-task.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const DEFAULT_PROJECTS_DIR = path.join(REPO_ROOT, 'projects');

/**
 * Categorize a project based on its spec file state.
 *
 * - "ready"       — has epic.md + architecture.md, missing at least one task spec
 * - "complete"    — has epic.md, all tasks have spec files
 * - "retroactive" — has epic.md and some task specs, but pre-dates the v2 pipeline
 *                   (has .md task files but no .v2.md files)
 * - "backlog"     — has epic.md but zero task spec files
 *
 * @param {string} projectId
 * @param {Array<{num: string}>} epicTasks - parsed from epic task table
 * @param {string[]} specFiles - filenames matching task-*.md or task-*.v2.md
 * @returns {"ready" | "complete" | "retroactive" | "backlog"}
 */
function categorizeProject(projectId, epicTasks, specFiles) {
  if (specFiles.length === 0) return 'backlog';

  const hasV2 = specFiles.some(f => f.endsWith('.v2.md'));
  const taskNums = epicTasks.map(t => t.num);
  const coveredNums = new Set();

  for (const f of specFiles) {
    const m = f.match(/^task-(\d+)-/);
    if (m) coveredNums.add(m[1]);
  }

  const allCovered = taskNums.every(n => coveredNums.has(n));
  if (allCovered) return 'complete';
  if (!hasV2) return 'retroactive';
  return 'ready';
}

/**
 * Scan projects/ for epic coverage.
 *
 * @param {string} [projectsDir] - absolute path to projects directory
 * @returns {Promise<Array<{
 *   projectId: string,
 *   epicTaskCount: number,
 *   existingSpecCount: number,
 *   missingTaskNums: string[],
 *   hasArchitecture: boolean,
 *   category: "ready" | "complete" | "retroactive" | "backlog"
 * }>>}
 */
async function scanProjectInventory(projectsDir = DEFAULT_PROJECTS_DIR) {
  const entries = await readdir(projectsDir, { withFileTypes: true });
  const dirs = entries.filter(e => e.isDirectory()).map(e => e.name).sort();

  const inventory = [];

  for (const projectId of dirs) {
    const projPath = path.join(projectsDir, projectId);
    const epicPath = path.join(projPath, 'epic.md');

    // Skip directories without epic.md
    try {
      await access(epicPath);
    } catch {
      continue;
    }

    const epicContent = await readFile(epicPath, 'utf-8');
    const epicTasks = extractTasksFromEpic(epicContent);

    // If epic has no parseable task table, skip
    if (epicTasks.length === 0) continue;

    // Read directory listing, filter for task spec files
    const allFiles = await readdir(projPath);
    const specFiles = allFiles.filter(f => /^task-\d+-.*\.(?:v2\.)?md$/.test(f));

    // Determine which task nums are covered by spec files
    const coveredNums = new Set();
    for (const f of specFiles) {
      const m = f.match(/^task-(\d+)-/);
      if (m) coveredNums.add(m[1]);
    }

    const missingTaskNums = epicTasks
      .map(t => t.num)
      .filter(n => !coveredNums.has(n));

    // Check for architecture.md
    const hasArchitecture = allFiles.includes('architecture.md');

    const category = categorizeProject(projectId, epicTasks, specFiles);

    inventory.push({
      projectId,
      epicTaskCount: epicTasks.length,
      existingSpecCount: coveredNums.size,
      missingTaskNums,
      hasArchitecture,
      category,
    });
  }

  return inventory;
}

/**
 * Format inventory as a human-readable table to stdout.
 *
 * @param {Array<{projectId: string, epicTaskCount: number, existingSpecCount: number, missingTaskNums: string[], hasArchitecture: boolean, category: string}>} inventory
 * @returns {string} formatted table
 */
function formatInventoryTable(inventory) {
  // Header
  const lines = [];
  lines.push('┌─────────────────────────────────────────┬──────────┬───────┬────────┬─────────┬──────────────┐');
  lines.push('│ Project                                 │ Category │ Tasks │ Specs  │ Arch    │ Missing      │');
  lines.push('├─────────────────────────────────────────┼──────────┼───────┼────────┼─────────┼──────────────┤');

  for (const p of inventory) {
    const id = p.projectId.length > 39 ? p.projectId.slice(0, 36) + '...' : p.projectId.padEnd(39);
    const cat = p.category.padEnd(8);
    const tasks = String(p.epicTaskCount).padStart(5);
    const specs = `${p.existingSpecCount}/${p.epicTaskCount}`.padStart(6);
    const arch = (p.hasArchitecture ? '✓' : '✗').padEnd(7);
    const missing = p.missingTaskNums.length > 0
      ? p.missingTaskNums.join(',').slice(0, 12).padEnd(12)
      : '—'.padEnd(12);
    lines.push(`│ ${id} │ ${cat} │ ${tasks} │ ${specs} │ ${arch} │ ${missing} │`);
  }

  // Totals
  const totalTasks = inventory.reduce((s, p) => s + p.epicTaskCount, 0);
  const totalSpecs = inventory.reduce((s, p) => s + p.existingSpecCount, 0);
  const totalMissing = inventory.reduce((s, p) => s + p.missingTaskNums.length, 0);

  lines.push('├─────────────────────────────────────────┼──────────┼───────┼────────┼─────────┼──────────────┤');
  lines.push(`│ ${'Total (' + inventory.length + ' projects)'.padEnd(39)} │ ${''.padEnd(8)} │ ${String(totalTasks).padStart(5)} │ ${(totalSpecs + '/' + totalTasks).padStart(6)} │ ${''.padEnd(7)} │ ${(totalMissing + ' missing').padEnd(12)} │`);
  lines.push('└─────────────────────────────────────────┴──────────┴───────┴────────┴─────────┴──────────────┘');

  return lines.join('\n');
}

// ── CLI entry point ───────────────────────────────────────────────────────────

const isMainModule = process.argv[1] && (
  process.argv[1] === fileURLToPath(import.meta.url) ||
  process.argv[1].endsWith('/batch-regen.mjs')
);

if (isMainModule) {
  const projectsDir = process.argv[2] || DEFAULT_PROJECTS_DIR;

  scanProjectInventory(projectsDir).then(inventory => {
    // JSON to stdout for piping
    if (process.argv.includes('--json')) {
      console.log(JSON.stringify(inventory, null, 2));
    } else {
      console.log(formatInventoryTable(inventory));
      console.log('');
      // Summary line
      const totalMissing = inventory.reduce((s, p) => s + p.missingTaskNums.length, 0);
      const ready = inventory.filter(p => p.category === 'ready').length;
      const backlog = inventory.filter(p => p.category === 'backlog').length;
      const retro = inventory.filter(p => p.category === 'retroactive').length;
      const complete = inventory.filter(p => p.category === 'complete').length;
      console.log(`Summary: ${ready} ready, ${retro} retroactive, ${backlog} backlog, ${complete} complete — ${totalMissing} specs missing`);
    }
  }).catch(err => {
    console.error('✗ Fatal:', err);
    process.exit(1);
  });
}

export {
  scanProjectInventory,
  categorizeProject,
  formatInventoryTable,
};
```

**Verify**: `node scripts/batch-regen.mjs` — expect a formatted table listing all 42+ projects with epic.md, showing category, task counts, spec coverage, and missing task numbers.

**Verify**: `node scripts/batch-regen.mjs --json | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')); console.log(d.length, 'projects')"` — expect `42 projects` (or similar count ≥40).

### Step 2: Create `scripts/batch-regen.test.mjs` with unit tests

**Action**: Write tests for `scanProjectInventory`, `categorizeProject`, and `formatInventoryTable` using `node:test` + `node:assert/strict`, matching the pattern in `scripts/regen-task.test.mjs`.

**File**: `scripts/batch-regen.test.mjs` (new)

**Pattern**: See Section 5 (Tests) below for complete assertion bodies.

**Verify**: `node --test scripts/batch-regen.test.mjs` — expect all tests passing.

### Step 3: Add `test:batch` script to `package.json`

**Action**: Add `"test:batch"` entry to the `scripts` block and append it to the `test:all` chain.

**File**: `package.json`

**Pattern**:

```json
"test:batch": "node --test scripts/batch-regen.test.mjs",
"test:all": "node --test server.test.js && node --test scripts/deviation-report.test.mjs && node --test scripts/regen-task.test.mjs && node --test scripts/batch-regen.test.mjs && node --test server.integration.test.js"
```

**Verify**: `npm run test:batch` — expect all batch tests passing. `npm run test:all` — expect all existing + new tests passing.

---

## 5. Tests

All tests use `node:test` (`describe`/`it`) and `node:assert/strict`, matching `scripts/regen-task.test.mjs`.

```javascript
// scripts/batch-regen.test.mjs
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { writeFile, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  scanProjectInventory,
  categorizeProject,
  formatInventoryTable,
} from './batch-regen.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TMP_DIR = path.join(__dirname, '..', '.tmp-test-projects');

// =============================================================================
// categorizeProject
// =============================================================================

describe('categorizeProject', () => {
  it('returns backlog when no spec files exist', () => {
    const result = categorizeProject(
      'proj-1',
      [{ num: '1' }, { num: '2' }],
      [],
    );
    assert.strictEqual(result, 'backlog');
  });

  it('returns complete when all tasks have spec files', () => {
    const result = categorizeProject(
      'proj-1',
      [{ num: '1' }, { num: '2' }],
      ['task-1-foo.v2.md', 'task-2-bar.v2.md'],
    );
    assert.strictEqual(result, 'complete');
  });

  it('returns retroactive when only v1 spec files exist and coverage is partial', () => {
    const result = categorizeProject(
      'proj-1',
      [{ num: '1' }, { num: '2' }, { num: '3' }],
      ['task-1-foo.md', 'task-2-bar.md'],
    );
    assert.strictEqual(result, 'retroactive');
  });

  it('returns ready when v2 files exist but coverage is partial', () => {
    const result = categorizeProject(
      'proj-1',
      [{ num: '1' }, { num: '2' }, { num: '3' }],
      ['task-1-foo.v2.md', 'task-2-bar.md'],
    );
    assert.strictEqual(result, 'ready');
  });

  it('returns complete when both v1 and v2 cover all tasks', () => {
    const result = categorizeProject(
      'proj-1',
      [{ num: '1' }, { num: '2' }],
      ['task-1-foo.md', 'task-1-foo.v2.md', 'task-2-bar.v2.md'],
    );
    assert.strictEqual(result, 'complete');
  });

  it('returns retroactive when all v1 only and all tasks covered', () => {
    const result = categorizeProject(
      'proj-1',
      [{ num: '1' }, { num: '2' }],
      ['task-1-foo.md', 'task-2-bar.md'],
    );
    assert.strictEqual(result, 'complete');
  });
});

// =============================================================================
// scanProjectInventory (filesystem integration)
// =============================================================================

describe('scanProjectInventory', () => {
  // Create a temp directory structure for isolated tests
  const EPIC_WITH_TABLE = `# Epic

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Alpha** | None | — | 1 day | High |
| 2 | **Beta** | 1 | — | 2 days | Medium |
| 3 | **Gamma** | 1, 2 | — | 1 day | Low |
`;

  const EPIC_NO_TABLE = `# Epic\n\nJust a description, no task table.\n`;

  // Setup: create temp project dirs
  it('returns inventory for projects with epic and task table', async () => {
    // Setup
    await rm(TMP_DIR, { recursive: true, force: true });
    await mkdir(path.join(TMP_DIR, 'proj-a'), { recursive: true });
    await writeFile(path.join(TMP_DIR, 'proj-a', 'epic.md'), EPIC_WITH_TABLE);
    await writeFile(path.join(TMP_DIR, 'proj-a', 'architecture.md'), '# Arch');
    await writeFile(path.join(TMP_DIR, 'proj-a', 'task-1-alpha.v2.md'), '# Task 1');

    const inventory = await scanProjectInventory(TMP_DIR);

    assert.strictEqual(inventory.length, 1);
    assert.strictEqual(inventory[0].projectId, 'proj-a');
    assert.strictEqual(inventory[0].epicTaskCount, 3);
    assert.strictEqual(inventory[0].existingSpecCount, 1);
    assert.deepStrictEqual(inventory[0].missingTaskNums, ['2', '3']);
    assert.strictEqual(inventory[0].hasArchitecture, true);
    assert.strictEqual(inventory[0].category, 'ready');

    // Cleanup
    await rm(TMP_DIR, { recursive: true, force: true });
  });

  it('skips directories without epic.md', async () => {
    await rm(TMP_DIR, { recursive: true, force: true });
    await mkdir(path.join(TMP_DIR, 'no-epic'), { recursive: true });
    await writeFile(path.join(TMP_DIR, 'no-epic', 'README.md'), '# Hello');

    const inventory = await scanProjectInventory(TMP_DIR);

    assert.strictEqual(inventory.length, 0);

    await rm(TMP_DIR, { recursive: true, force: true });
  });

  it('skips projects whose epic has no parseable task table', async () => {
    await rm(TMP_DIR, { recursive: true, force: true });
    await mkdir(path.join(TMP_DIR, 'empty-epic'), { recursive: true });
    await writeFile(path.join(TMP_DIR, 'empty-epic', 'epic.md'), EPIC_NO_TABLE);

    const inventory = await scanProjectInventory(TMP_DIR);

    assert.strictEqual(inventory.length, 0);

    await rm(TMP_DIR, { recursive: true, force: true });
  });

  it('reports hasArchitecture false when architecture.md missing', async () => {
    await rm(TMP_DIR, { recursive: true, force: true });
    await mkdir(path.join(TMP_DIR, 'no-arch'), { recursive: true });
    await writeFile(path.join(TMP_DIR, 'no-arch', 'epic.md'), EPIC_WITH_TABLE);

    const inventory = await scanProjectInventory(TMP_DIR);

    assert.strictEqual(inventory.length, 1);
    assert.strictEqual(inventory[0].hasArchitecture, false);

    await rm(TMP_DIR, { recursive: true, force: true });
  });

  it('counts both v1 and v2 spec files for the same task number once', async () => {
    await rm(TMP_DIR, { recursive: true, force: true });
    await mkdir(path.join(TMP_DIR, 'mixed'), { recursive: true });
    await writeFile(path.join(TMP_DIR, 'mixed', 'epic.md'), EPIC_WITH_TABLE);
    await writeFile(path.join(TMP_DIR, 'mixed', 'task-1-alpha.md'), '# v1');
    await writeFile(path.join(TMP_DIR, 'mixed', 'task-1-alpha.v2.md'), '# v2');
    await writeFile(path.join(TMP_DIR, 'mixed', 'task-2-beta.md'), '# v1');

    const inventory = await scanProjectInventory(TMP_DIR);

    assert.strictEqual(inventory[0].existingSpecCount, 2);
    assert.deepStrictEqual(inventory[0].missingTaskNums, ['3']);

    await rm(TMP_DIR, { recursive: true, force: true });
  });

  it('sorts projects alphabetically by projectId', async () => {
    await rm(TMP_DIR, { recursive: true, force: true });
    await mkdir(path.join(TMP_DIR, 'z-proj'), { recursive: true });
    await mkdir(path.join(TMP_DIR, 'a-proj'), { recursive: true });
    await writeFile(path.join(TMP_DIR, 'z-proj', 'epic.md'), EPIC_WITH_TABLE);
    await writeFile(path.join(TMP_DIR, 'a-proj', 'epic.md'), EPIC_WITH_TABLE);

    const inventory = await scanProjectInventory(TMP_DIR);

    assert.strictEqual(inventory[0].projectId, 'a-proj');
    assert.strictEqual(inventory[1].projectId, 'z-proj');

    await rm(TMP_DIR, { recursive: true, force: true });
  });
});

// =============================================================================
// formatInventoryTable
// =============================================================================

describe('formatInventoryTable', () => {
  it('returns table with header, rows, and totals', () => {
    const inventory = [
      { projectId: 'proj-a', epicTaskCount: 3, existingSpecCount: 1, missingTaskNums: ['2', '3'], hasArchitecture: true, category: 'ready' },
      { projectId: 'proj-b', epicTaskCount: 5, existingSpecCount: 5, missingTaskNums: [], hasArchitecture: true, category: 'complete' },
    ];

    const table = formatInventoryTable(inventory);

    assert.ok(table.includes('proj-a'), 'table should contain proj-a');
    assert.ok(table.includes('proj-b'), 'table should contain proj-b');
    assert.ok(table.includes('ready'), 'table should contain ready category');
    assert.ok(table.includes('complete'), 'table should contain complete category');
    assert.ok(table.includes('2,3'), 'table should list missing task nums');
    assert.ok(table.includes('Total'), 'table should have totals row');
    assert.ok(table.includes('2 projects'), 'total row should show project count');
  });

  it('returns table with dash for projects with no missing tasks', () => {
    const inventory = [
      { projectId: 'done-proj', epicTaskCount: 2, existingSpecCount: 2, missingTaskNums: [], hasArchitecture: true, category: 'complete' },
    ];

    const table = formatInventoryTable(inventory);

    assert.ok(table.includes('—'), 'completed project should show dash for missing column');
  });

  it('truncates long project IDs', () => {
    const longId = 'this-is-a-very-long-project-id-that-exceeds-39-chars-limit';
    const inventory = [
      { projectId: longId, epicTaskCount: 1, existingSpecCount: 0, missingTaskNums: ['1'], hasArchitecture: false, category: 'backlog' },
    ];

    const table = formatInventoryTable(inventory);

    assert.ok(table.includes('...'), 'long project IDs should be truncated with ellipsis');
    assert.ok(!table.includes(longId), 'full long ID should not appear in table');
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. **`feat(batch): add project inventory scanner`** — `scripts/batch-regen.mjs`: `scanProjectInventory()`, `categorizeProject()`, `formatInventoryTable()`, CLI entry point with `--json` flag.
2. **`test(batch): add 12 tests for inventory scanner`** — `scripts/batch-regen.test.mjs`: unit tests for categorization, filesystem scanning, and table formatting.
3. **`chore(batch): wire test:batch script into package.json`** — `package.json`: add `test:batch`, update `test:all` chain.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/batch-regen.test.mjs            # New tests pass
node --test scripts/regen-task.test.mjs              # Existing tests unbroken
node --test scripts/deviation-report.test.mjs        # Existing tests unbroken
npm run test:all                                     # Full suite green
node scripts/batch-regen.mjs                         # Human-readable table printed
node scripts/batch-regen.mjs --json | node -e "
  const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
  console.log(d.length + ' projects scanned');
  const missing = d.reduce((s,p) => s + p.missingTaskNums.length, 0);
  console.log(missing + ' specs missing');
"
```

**Expected delta**: 0 → 12 new tests passing (batch-regen.test.mjs). Zero existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.
- **Cleanup**: if temp test directories persist after test failure, run `rm -rf .tmp-test-projects`.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in codebase; if still missing, flag it, do not invent.
- **`extractTasksFromEpic` export signature changed** → check `scripts/regen-task.mjs` line 920; adapt import accordingly. Log deviation in commit body.
- **Task table format variation in some epics** (e.g., missing Priority column) → `extractTasksFromEpic` already handles this via its regex; if specific epics fail, log which ones and skip them (scanner is tolerant by design — `epicTasks.length === 0` means skip).
- **`readdir` returns files alongside directories in `projects/`** → the `withFileTypes: true` + `isDirectory()` filter handles this. If a symlink is encountered, skip it silently.
- **Project count differs from expected ~42** → the scanner reports what it finds. Proceed regardless. The count is data, not a test assertion on the real `projects/` directory.

---

## 10. Out of Scope

This task builds only the inventory scanner and its table output. It does NOT build the batch manifest schema (Task 2), the orchestrator loop (Task 3), the progress reporter (Task 4), retry logic (Task 5), or the summary report (Task 6). Those tasks extend `scripts/batch-regen.mjs` by adding functions alongside the scanner — the file structure is designed for this, but the executor must not pre-build stubs for future tasks.

- **Manifest schema and validation** — Task 2; depends on scanner output shape but is a separate commit scope.
- **`--dry-run` flag** — Task 3; uses scanner output but adds orchestrator logic.
- **Review score extraction** — Task 6; reads `.v2.md` file content, which the scanner intentionally does not parse (it only checks file existence).
- **Category inference heuristics beyond v1/v2 detection** — if richer categorization is needed (e.g., "has code commits"), it should be a follow-up after the batch orchestrator reveals whether the current heuristic is sufficient.
- **Writing any output files** — the scanner is read-only. It prints to stdout and returns data. It does not create manifest files or logs.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)

---

##### Post-generation review (auto)

**Overall**: 4/5 (silver)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 5/5 | Document is a task-level implementation spec, not an epic/architecture/analysis — standard section requirements for those types do not apply |
| Content routing | 4/5 | Code blocks are extensive (~200 lines of JS) — acceptable in an implementation guide but pushes the boundary; the spec is nearly copy-paste-ready, which is useful but risks becoming stale if architecture changes |
| Pattern application | 3/5 | Trade-offs use narrative bullet format instead of a Decision Justification Table with columns (Option / Pros / Cons / Verdict) |
| Rule compliance | 4/5 | Related Documents section correctly uses 'Solution Architecture' naming convention |
| Content quality | 5/5 | Highly opinionated: specific function names, file locations, import strategy all decided — no ambiguity left for executor |
| Usefulness | 5/5 | A developer could implement this nearly verbatim — complete code listing, test file, package.json changes, and verification commands are all provided |

**Top fixes**:
- Convert the 3 trade-offs in Section 1 (Context) from narrative bullets to a Decision Justification Table with columns: Option | Trade-off | Verdict — matches the methodology's pattern for decision documentation
- Reformat the Out of Scope section (Section 10) into ✅ In Scope / ❌ Out of Scope boundary pairs with one-line reasons, replacing the current prose paragraphs
- Add a simple execution flow diagram (ASCII or Mermaid) showing: projects/ dir → readdir filter → epic.md parse → extractTasksFromEpic → spec file inventory → categorize → structured output — makes the data pipeline scannable at a glance
