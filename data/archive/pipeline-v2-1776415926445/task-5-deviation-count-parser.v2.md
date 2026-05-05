Now I have everything I need. Let me generate the implementation guide.

# 🛠️ Task 5: Deviation-Count Parser

**Purpose**: Build a standalone script that parses executor commit bodies for `Deviation: <category> -- <description>` lines, counts them per task, categorizes into five buckets, and outputs a summary table to stdout — the spec-quality signal that reveals whether the pipeline is calibrated or drifting.

**Effort**: 1 day

**Dependencies**: None — standalone script, no dependency on Tasks 1–4

**Parallel With**: Tasks 1, 2, 3, 4 (all independent)

**Blocks**: Pipeline calibration feedback loop — without this, deviation trends are invisible between executor runs

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task creates `scripts/deviation-report.mjs`, a standalone Node.js ESM script that reads git history from a repository, extracts `Deviation: <category> -- <description>` lines from commit bodies, categorizes them into five predefined buckets (`stale-context`, `UX-silent`, `env-gap`, `commit-drift`, `positive-review-absorption`), infers which task each commit belongs to, and prints a summary table to stdout. The architecture doc specifies this as the observability layer — it runs after executor runs and produces the single sharpest signal for spec quality: judgment-calls-per-commit trending upward means the prompts need work. An optional `--out <path>` flag writes the same table to a markdown file. The script uses `child_process.execSync` for `git log` (matching the existing `regen-task.mjs` pattern at line 379) and has zero external dependencies.

**Trade-offs considered**:
- **Database-backed deviation store** — rejected because the architecture's "not-yet-built" principle says no DB tables until a second consumer appears. Stdout is the UI until a dashboard exists.
- **NLP-based category inference from freeform text** — rejected because the format contract (`Deviation: <category> -- <description>`) makes regex parsing deterministic. NLP adds a dependency and non-determinism for no gain.
- **Standalone script with regex parsing** — preferred because it matches the architecture decision (stdout, no API, no DB), is testable as pure functions, and ships in a day.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- scripts/                     # Confirm scripts/ is clean
npm run test:server                           # Record: 88 passing (server.test.js)
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 88/88 passing (`server.test.js`). The new script gets its own test file — baseline for it is 0.

---

## 3. Files

### To Create (new)
- `scripts/deviation-report.mjs` **(new)** — Standalone CLI: parses git log, extracts deviation lines, categorizes, prints summary table. Uses `child_process.execSync` for git access. Exports `parseDeviations`, `categorize`, `inferTaskNum`, `formatTable` for testing.
- `scripts/deviation-report.test.mjs` **(new)** — Unit tests using `node:test` + `node:assert/strict` (matches `server.test.js` conventions). Tests pure functions only — no git repo fixture needed.

### To Modify (cite CODEBASE CONTEXT)
- `package.json` — Add `"test:deviations": "node --test scripts/deviation-report.test.mjs"` to scripts and update `"test:all"` to include it.

### To Leave Alone
- `scripts/regen-task.mjs` — This is the pipeline script modified by Tasks 1–4. Task 5 is a standalone consumer of git history, not a modifier of the pipeline.
- `server.js` — No server changes. The deviation parser reads git log, not API endpoints.
- `server.test.js` — Existing 88 tests unchanged. New tests go in `scripts/deviation-report.test.mjs`.
- `server.integration.test.js` — Integration tests are for the running API. Deviation parsing is script-side, git-side.

---

## 4. Implementation Steps

### Step 1: Create the deviation parser module with exported pure functions

**Action**: Create `scripts/deviation-report.mjs` with the core parsing logic as exported functions, plus a CLI entry point gated behind `import.meta.url` check. Port the `execSync` + git-log pattern from `scripts/regen-task.mjs:379–386`.

**File**: `scripts/deviation-report.mjs` **(new)**

**Pattern**:
```javascript
#!/usr/bin/env node
// Deviation-count parser — spec quality signal.
// Usage: node scripts/deviation-report.mjs [--out <path>] [--branch <ref>] [<repo-path>]
//
// Parses commit bodies for: Deviation: <category> -- <description>
// Outputs categorized summary table to stdout.

import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

// ── Constants ──

const CATEGORIES = [
  'stale-context',
  'UX-silent',
  'env-gap',
  'commit-drift',
  'positive-review-absorption',
];

const DEVIATION_RE = /^Deviation:\s*(\S+)\s*(?:--|—)\s*(.+)$/;
const TASK_SCOPE_RE = /^(?:feat|fix|chore|test|docs)\(task-(\d+)\)/;
const TASK_BRANCH_RE = /task-(\d+)/;

// ── Pure functions (exported for testing) ──

export function parseDeviationLine(line) {
  const m = line.trim().match(DEVIATION_RE);
  if (!m) return null;
  return { category: m[1], description: m[2].trim() };
}

export function inferTaskNum(subject, branch) {
  const scopeMatch = subject.match(TASK_SCOPE_RE);
  if (scopeMatch) return scopeMatch[1];
  const branchMatch = (branch || '').match(TASK_BRANCH_RE);
  if (branchMatch) return branchMatch[1];
  return 'unknown';
}

export function parseCommits(gitLogOutput, branch) {
  // gitLogOutput: commits separated by ---COMMIT_SEP---
  // Each commit block: first line is subject, rest is body
  const commits = gitLogOutput
    .split('---COMMIT_SEP---')
    .map(c => c.trim())
    .filter(Boolean);

  const results = [];
  for (const block of commits) {
    const lines = block.split('\n');
    const subject = lines[0] || '';
    const bodyLines = lines.slice(1);
    const taskNum = inferTaskNum(subject, branch);
    const deviations = [];
    for (const line of bodyLines) {
      const parsed = parseDeviationLine(line);
      if (parsed) deviations.push(parsed);
    }
    results.push({ subject, taskNum, deviations });
  }
  return results;
}

export function categorize(commits) {
  const counts = Object.fromEntries(CATEGORIES.map(c => [c, 0]));
  let uncategorized = 0;
  const allDeviations = [];
  const perTask = {};

  for (const commit of commits) {
    for (const d of commit.deviations) {
      if (CATEGORIES.includes(d.category)) {
        counts[d.category]++;
      } else {
        uncategorized++;
      }
      allDeviations.push({ ...d, taskNum: commit.taskNum });

      if (!perTask[commit.taskNum]) {
        perTask[commit.taskNum] = { deviations: 0, commits: 0, categories: {} };
      }
      perTask[commit.taskNum].deviations++;
      perTask[commit.taskNum].categories[d.category] =
        (perTask[commit.taskNum].categories[d.category] || 0) + 1;
    }
    // Count commits per task (even those with zero deviations)
    if (!perTask[commit.taskNum]) {
      perTask[commit.taskNum] = { deviations: 0, commits: 0, categories: {} };
    }
    perTask[commit.taskNum].commits++;
  }

  return { counts, uncategorized, allDeviations, perTask, totalCommits: commits.length };
}

export function formatTable(categorized, epicName) {
  const { counts, uncategorized, perTask, totalCommits } = categorized;
  const totalDeviations = Object.values(counts).reduce((a, b) => a + b, 0) + uncategorized;
  const taskCount = Object.keys(perTask).length;

  const lines = [];
  lines.push(`Deviation Report: ${epicName || '(unnamed)'}`);
  lines.push(`Tasks: ${taskCount}  Commits: ${totalCommits}  Total deviations: ${totalDeviations}`);
  lines.push('');

  // Category table
  lines.push('| Category               | Count | % of Total |');
  lines.push('|------------------------|-------|------------|');
  for (const cat of CATEGORIES) {
    const count = counts[cat];
    const pct = totalDeviations > 0 ? Math.round((count / totalDeviations) * 100) : 0;
    lines.push(`| ${cat.padEnd(22)} | ${String(count).padStart(5)} | ${String(pct + '%').padStart(10)} |`);
  }
  if (uncategorized > 0) {
    const pct = Math.round((uncategorized / totalDeviations) * 100);
    lines.push(`| ${'(uncategorized)'.padEnd(22)} | ${String(uncategorized).padStart(5)} | ${String(pct + '%').padStart(10)} |`);
  }
  lines.push('');

  // Per-task table
  lines.push('Per-task breakdown:');
  lines.push('| Task | Deviations | Avg/Commit | Categories |');
  lines.push('|------|------------|------------|------------|');
  const sortedTasks = Object.keys(perTask).sort((a, b) => {
    const na = parseInt(a, 10);
    const nb = parseInt(b, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  for (const taskNum of sortedTasks) {
    const t = perTask[taskNum];
    const avg = t.commits > 0 ? (t.deviations / t.commits).toFixed(1) : '0.0';
    const cats = Object.entries(t.categories)
      .map(([c, n]) => `${c}(${n})`)
      .join(', ');
    lines.push(`| ${String(taskNum).padEnd(4)} | ${String(t.deviations).padStart(10)} | ${String(avg).padStart(10)} | ${cats} |`);
  }

  return lines.join('\n');
}

// ── CLI ──

function getGitLog(repoPath, branch) {
  const branchArg = branch ? `${branch}` : 'HEAD';
  const cmd = `git -C "${repoPath}" log --format="%s%n%b---COMMIT_SEP---" ${branchArg}`;
  return execSync(cmd, { maxBuffer: 10 * 1024 * 1024, encoding: 'utf8' });
}

function parseArgs(argv) {
  const args = argv.slice(2);
  let outPath = null;
  let branch = null;
  let repoPath = '.';
  let epicName = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out' && args[i + 1]) {
      outPath = args[++i];
    } else if (args[i] === '--branch' && args[i + 1]) {
      branch = args[++i];
    } else if (args[i] === '--epic' && args[i + 1]) {
      epicName = args[++i];
    } else if (!args[i].startsWith('--')) {
      repoPath = args[i];
    }
  }
  return { outPath, branch, repoPath, epicName };
}

function main() {
  const { outPath, branch, repoPath, epicName } = parseArgs(process.argv);
  const resolvedRepo = path.resolve(repoPath);

  const raw = getGitLog(resolvedRepo, branch);
  const commits = parseCommits(raw, branch);
  const categorized = categorize(commits);
  const table = formatTable(categorized, epicName);

  console.log(table);

  if (outPath) {
    fs.writeFileSync(outPath, table + '\n', 'utf8');
    console.log(`\nWritten to ${outPath}`);
  }
}

// Run CLI only when invoked directly
const isMainModule = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/'));
if (isMainModule) {
  main();
}
```

**Verify**: `node -e "import('./scripts/deviation-report.mjs').then(m => console.log(typeof m.parseDeviationLine))"` — expect `function`

### Step 2: Create comprehensive unit tests

**Action**: Create `scripts/deviation-report.test.mjs` with tests for all exported pure functions. Uses `node:test` + `node:assert/strict` matching `server.test.js` conventions.

**File**: `scripts/deviation-report.test.mjs` **(new)**

**Pattern**: See Section 5 (Tests) below for complete assertion bodies.

**Verify**: `node --test scripts/deviation-report.test.mjs` — expect all tests passing

### Step 3: Register test script in package.json

**Action**: Add `test:deviations` script and update `test:all` to include it.

**File**: `package.json` (cite CODEBASE CONTEXT — line 12–16)

**Pattern**:
```json
"test:server": "node --test server.test.js",
"test:deviations": "node --test scripts/deviation-report.test.mjs",
...
"test:all": "node --test server.test.js && node --test scripts/deviation-report.test.mjs && node --test server.integration.test.js"
```

**Verify**: `npm run test:deviations` — expect all tests passing

---

## 5. Tests

Complete assertion bodies. Framework: `node:test` + `node:assert/strict` (matches `server.test.js`).

```javascript
// scripts/deviation-report.test.mjs
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseDeviationLine,
  inferTaskNum,
  parseCommits,
  categorize,
  formatTable,
} from './deviation-report.mjs';

// =============================================================================
// parseDeviationLine
// =============================================================================

describe('parseDeviationLine', () => {
  it('parses valid deviation with double-dash separator', () => {
    const result = parseDeviationLine('Deviation: stale-context -- codebase.md cited old path');
    assert.deepStrictEqual(result, {
      category: 'stale-context',
      description: 'codebase.md cited old path',
    });
  });

  it('parses valid deviation with em-dash separator', () => {
    const result = parseDeviationLine('Deviation: UX-silent — button label not specified');
    assert.deepStrictEqual(result, {
      category: 'UX-silent',
      description: 'button label not specified',
    });
  });

  it('returns null for non-deviation line', () => {
    assert.strictEqual(parseDeviationLine('feat(task-1): add preamble strip'), null);
  });

  it('returns null for empty string', () => {
    assert.strictEqual(parseDeviationLine(''), null);
  });

  it('handles leading whitespace', () => {
    const result = parseDeviationLine('  Deviation: env-gap -- node 22 required but 20 installed');
    assert.deepStrictEqual(result, {
      category: 'env-gap',
      description: 'node 22 required but 20 installed',
    });
  });

  it('preserves category verbatim even if unknown', () => {
    const result = parseDeviationLine('Deviation: new-category -- some description');
    assert.deepStrictEqual(result, {
      category: 'new-category',
      description: 'some description',
    });
  });
});

// =============================================================================
// inferTaskNum
// =============================================================================

describe('inferTaskNum', () => {
  it('extracts task number from feat(task-N) scope', () => {
    assert.strictEqual(inferTaskNum('feat(task-3): add rescan', ''), '3');
  });

  it('extracts task number from fix(task-12) scope', () => {
    assert.strictEqual(inferTaskNum('fix(task-12): edge case', ''), '12');
  });

  it('falls back to branch name when subject has no task scope', () => {
    assert.strictEqual(inferTaskNum('chore: update deps', 'feat/task-5-deviation'), '5');
  });

  it('returns unknown when neither subject nor branch has task number', () => {
    assert.strictEqual(inferTaskNum('chore: update deps', 'main'), 'unknown');
  });

  it('prefers subject scope over branch name', () => {
    assert.strictEqual(inferTaskNum('feat(task-2): thing', 'feat/task-7-other'), '2');
  });

  it('handles null branch', () => {
    assert.strictEqual(inferTaskNum('chore: something', null), 'unknown');
  });
});

// =============================================================================
// parseCommits
// =============================================================================

describe('parseCommits', () => {
  it('parses single commit with one deviation', () => {
    const log = 'feat(task-1): add feature\nDeviation: stale-context -- old path\n---COMMIT_SEP---';
    const commits = parseCommits(log, null);
    assert.strictEqual(commits.length, 1);
    assert.strictEqual(commits[0].subject, 'feat(task-1): add feature');
    assert.strictEqual(commits[0].taskNum, '1');
    assert.strictEqual(commits[0].deviations.length, 1);
    assert.strictEqual(commits[0].deviations[0].category, 'stale-context');
  });

  it('parses multiple commits', () => {
    const log = [
      'feat(task-1): first\nDeviation: env-gap -- missing dep\n---COMMIT_SEP---',
      'feat(task-2): second\n---COMMIT_SEP---',
    ].join('\n');
    const commits = parseCommits(log, null);
    assert.strictEqual(commits.length, 2);
    assert.strictEqual(commits[0].deviations.length, 1);
    assert.strictEqual(commits[1].deviations.length, 0);
  });

  it('handles commit with multiple deviations', () => {
    const log = [
      'feat(task-3): big commit',
      'Deviation: stale-context -- path changed',
      'Deviation: UX-silent -- color not specified',
      'Deviation: commit-drift -- merged two steps',
      '---COMMIT_SEP---',
    ].join('\n');
    const commits = parseCommits(log, null);
    assert.strictEqual(commits[0].deviations.length, 3);
  });

  it('ignores empty blocks from trailing separator', () => {
    const log = 'feat(task-1): only\n---COMMIT_SEP---\n';
    const commits = parseCommits(log, null);
    assert.strictEqual(commits.length, 1);
  });

  it('uses branch for task inference when subject lacks scope', () => {
    const log = 'chore: no scope\nDeviation: env-gap -- thing\n---COMMIT_SEP---';
    const commits = parseCommits(log, 'feat/task-4-review');
    assert.strictEqual(commits[0].taskNum, '4');
  });
});

// =============================================================================
// categorize
// =============================================================================

describe('categorize', () => {
  it('counts deviations by category', () => {
    const commits = [
      { subject: 'a', taskNum: '1', deviations: [
        { category: 'stale-context', description: 'x' },
        { category: 'stale-context', description: 'y' },
      ]},
      { subject: 'b', taskNum: '1', deviations: [
        { category: 'env-gap', description: 'z' },
      ]},
    ];
    const result = categorize(commits);
    assert.strictEqual(result.counts['stale-context'], 2);
    assert.strictEqual(result.counts['env-gap'], 1);
    assert.strictEqual(result.counts['UX-silent'], 0);
    assert.strictEqual(result.totalCommits, 2);
  });

  it('tracks uncategorized deviations', () => {
    const commits = [
      { subject: 'a', taskNum: '1', deviations: [
        { category: 'made-up-category', description: 'x' },
      ]},
    ];
    const result = categorize(commits);
    assert.strictEqual(result.uncategorized, 1);
    assert.strictEqual(result.counts['stale-context'], 0);
  });

  it('builds per-task breakdown', () => {
    const commits = [
      { subject: 'a', taskNum: '1', deviations: [
        { category: 'stale-context', description: 'x' },
      ]},
      { subject: 'b', taskNum: '2', deviations: [
        { category: 'UX-silent', description: 'y' },
        { category: 'UX-silent', description: 'z' },
      ]},
      { subject: 'c', taskNum: '2', deviations: [] },
    ];
    const result = categorize(commits);
    assert.strictEqual(result.perTask['1'].deviations, 1);
    assert.strictEqual(result.perTask['1'].commits, 1);
    assert.strictEqual(result.perTask['2'].deviations, 2);
    assert.strictEqual(result.perTask['2'].commits, 2);
  });

  it('handles zero deviations gracefully', () => {
    const commits = [
      { subject: 'a', taskNum: '1', deviations: [] },
    ];
    const result = categorize(commits);
    assert.strictEqual(result.perTask['1'].deviations, 0);
    assert.strictEqual(result.perTask['1'].commits, 1);
    assert.strictEqual(result.totalCommits, 1);
  });
});

// =============================================================================
// formatTable
// =============================================================================

describe('formatTable', () => {
  it('includes epic name in header', () => {
    const categorized = {
      counts: { 'stale-context': 0, 'UX-silent': 0, 'env-gap': 0, 'commit-drift': 0, 'positive-review-absorption': 0 },
      uncategorized: 0,
      perTask: {},
      totalCommits: 0,
      allDeviations: [],
    };
    const table = formatTable(categorized, 'Pipeline V2');
    assert.ok(table.includes('Deviation Report: Pipeline V2'), 'header should contain epic name');
  });

  it('shows (unnamed) when no epic name provided', () => {
    const categorized = {
      counts: { 'stale-context': 0, 'UX-silent': 0, 'env-gap': 0, 'commit-drift': 0, 'positive-review-absorption': 0 },
      uncategorized: 0,
      perTask: {},
      totalCommits: 0,
      allDeviations: [],
    };
    const table = formatTable(categorized, null);
    assert.ok(table.includes('(unnamed)'), 'should show (unnamed) placeholder');
  });

  it('renders category rows with correct counts', () => {
    const categorized = {
      counts: { 'stale-context': 3, 'UX-silent': 0, 'env-gap': 1, 'commit-drift': 0, 'positive-review-absorption': 0 },
      uncategorized: 0,
      perTask: { '1': { deviations: 4, commits: 3, categories: { 'stale-context': 3, 'env-gap': 1 } } },
      totalCommits: 3,
      allDeviations: [],
    };
    const table = formatTable(categorized, 'Test');
    assert.ok(table.includes('stale-context'), 'should list stale-context');
    assert.ok(table.includes('3'), 'should show count 3');
    assert.ok(table.includes('75%'), 'stale-context should be 75% of 4 total');
  });

  it('renders per-task breakdown rows', () => {
    const categorized = {
      counts: { 'stale-context': 1, 'UX-silent': 2, 'env-gap': 0, 'commit-drift': 0, 'positive-review-absorption': 0 },
      uncategorized: 0,
      perTask: {
        '1': { deviations: 1, commits: 2, categories: { 'stale-context': 1 } },
        '2': { deviations: 2, commits: 3, categories: { 'UX-silent': 2 } },
      },
      totalCommits: 5,
      allDeviations: [],
    };
    const table = formatTable(categorized, 'Test');
    assert.ok(table.includes('Per-task breakdown:'), 'should have per-task section');
    assert.ok(table.includes('stale-context(1)'), 'should show categories for task 1');
    assert.ok(table.includes('UX-silent(2)'), 'should show categories for task 2');
  });

  it('includes uncategorized row when present', () => {
    const categorized = {
      counts: { 'stale-context': 1, 'UX-silent': 0, 'env-gap': 0, 'commit-drift': 0, 'positive-review-absorption': 0 },
      uncategorized: 2,
      perTask: { '1': { deviations: 3, commits: 1, categories: { 'stale-context': 1, 'other': 2 } } },
      totalCommits: 1,
      allDeviations: [],
    };
    const table = formatTable(categorized, 'Test');
    assert.ok(table.includes('(uncategorized)'), 'should show uncategorized row');
  });

  it('sorts tasks numerically', () => {
    const categorized = {
      counts: { 'stale-context': 2, 'UX-silent': 0, 'env-gap': 0, 'commit-drift': 0, 'positive-review-absorption': 0 },
      uncategorized: 0,
      perTask: {
        '10': { deviations: 1, commits: 1, categories: { 'stale-context': 1 } },
        '2': { deviations: 1, commits: 1, categories: { 'stale-context': 1 } },
      },
      totalCommits: 2,
      allDeviations: [],
    };
    const table = formatTable(categorized, 'Test');
    const task2Idx = table.indexOf('| 2   ');
    const task10Idx = table.indexOf('| 10  ');
    assert.ok(task2Idx < task10Idx, 'task 2 should appear before task 10 (numeric sort)');
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(pipeline): deviation-count parser — scripts/deviation-report.mjs` — `scripts/deviation-report.mjs`: standalone CLI that parses git commit bodies for `Deviation: <category> -- <description>` lines, categorizes into 5 buckets, outputs summary table to stdout. Exports pure functions for testing.

2. `test(pipeline): deviation-report unit tests + package.json registration` — `scripts/deviation-report.test.mjs`, `package.json`: 24 tests covering `parseDeviationLine`, `inferTaskNum`, `parseCommits`, `categorize`, `formatTable`. Adds `test:deviations` script and updates `test:all`.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation using the format `Deviation: <category> -- <description>`.

---

## 7. Verification

```bash
node --test scripts/deviation-report.test.mjs
npm run test:server
```

**Expected delta**: `server.test.js` stays at 88 passing (zero regressions). `deviation-report.test.mjs` adds 24 new passing tests. Total across both: 88 → 112 passing.

**Smoke test** (manual):
```bash
node scripts/deviation-report.mjs --epic "Pipeline V2" .
```
Expected: prints a deviation table reading from the current repo's git log. Commits without `Deviation:` lines produce zero deviations — the table still renders with zeros.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch. The new script has no dependents — deleting it breaks nothing.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it, do not invent.
- **Test framework mismatch** → match the repo's convention (`node:test` + `node:assert/strict`); translate silently but note in commit body.
- **`git log --format` flag differences across git versions** → adjust the format string to match the installed git version; log deviation.
- **`import.meta.url` main-module detection doesn't work in the test runner** → gate CLI execution behind a separate `if` condition (e.g., check `process.argv[1]` directly); log deviation.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task builds the parser and its tests — nothing more. It does not modify the executor's commit workflow, does not build a dashboard, does not persist results to a database, and does not integrate with CI. Each of those is a separate consumer that would promote this stdout tool when the pull exists.

- **`--json` output flag** — deferred until a machine consumer (dashboard, CI check) appears. The architecture doc names this as a trivial addition when needed.
- **CI integration** (run deviation report on every PR) — deferred until the pipeline has shipped at least 3 executor runs and the report format is stable.
- **Database persistence of deviation history** — deferred per architecture "not-yet-built" principle. No second consumer exists.
- **Modifying executor protocol to enforce `Deviation:` format** — the format contract is already documented in the epic and architecture. Enforcement is a separate task.
- **Trend analysis across multiple runs** — requires stored history (blocked by DB deferral). When the DB consumer appears, this becomes the natural next feature.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, Task 5 component design
- [Epic](./epic.md) – Task scope, success criteria
- [Timeline](./timeline.md) – Status tracking (update after done)