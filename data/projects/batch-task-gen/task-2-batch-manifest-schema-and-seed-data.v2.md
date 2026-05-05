# Task 2: Batch Manifest Schema and Seed Data

**Purpose**: Define the JSON manifest schema that serves as the operator's control surface for batch task generation, and seed it with the 10 target projects categorized by readiness.

**Effort**: 1h

**Dependencies**: None — the manifest is a static JSON file with loader/validator functions. Task 1 (scanner) is parallel and independent.

**Parallel With**: Task 1 (Project inventory scanner)

**Blocks**: Task 3 (Batch orchestrator script) — the orchestrator reads and validates this manifest before iterating projects.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task creates the manifest file (`scripts/batch-manifest.json`) that tells the batch orchestrator which projects to process, in what order, and with what per-project configuration. It also adds `loadManifest()` and `validateManifest()` functions to `scripts/batch-regen.mjs` — the orchestrator script that Task 3 will build on top of. The manifest is deliberately a flat JSON file (not a database, not generated code) because the operator needs to hand-edit it: reorder priorities, skip a project, override concurrency per-project. The seed data comes from the braindump's 10 target projects, with categories assigned based on current state: 2 ready (have epics + architecture, no task specs, no shipped code), 4 retroactive (code already shipped, specs needed for documentation), 4 backlog (future work, specs needed before agents can execute).

**Trade-offs considered**:
- **Auto-generate manifest from scanner output** — rejected because the scanner (Task 1) assigns categories heuristically, but the operator knows intent better (e.g., a project with existing `.v2.md` files might still need re-generation). A hand-seeded manifest with scanner as a _suggestion tool_ is more operator-friendly.
- **YAML instead of JSON** — rejected because every other config file in the pipeline is JSON, the schema is flat enough that JSON comments aren't needed, and `JSON.parse` is zero-dependency.
- **Manifest as a JS module** — rejected because the operator edits this file directly and shouldn't need to know JS syntax. JSON is universally readable.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- scripts/                     # Confirm scripts/ is clean
node --test scripts/regen-task.test.mjs       # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 35/35 passing (regen-task.test.mjs).

---

## 3. Files

### To Create (new)
- `scripts/batch-manifest.json` **(new)** — the 10-project seed manifest with schema version, categories, priorities, and per-project flags
- `scripts/batch-regen.mjs` **(new)** — `loadManifest()` and `validateManifest()` functions (Task 3 extends this file with the orchestrator loop)
- `scripts/batch-regen.test.mjs` **(new)** — tests for manifest loading, validation, and edge cases

### To Modify (cite CODEBASE CONTEXT)
- None

### To Leave Alone
- `scripts/regen-task.mjs` — the batch orchestrator treats this as a black box; no changes needed for manifest work
- `scripts/regen-task.test.mjs` — existing 35 tests; this task does not modify them
- `projects/*/epic.md` — read-only during validation; never written by manifest code

---

## 4. Implementation Steps

### Step 1: Create the manifest schema seed file

**Action**: Write `scripts/batch-manifest.json` with the 10 target projects, ordered by priority (ready first, retroactive second, backlog last). Each entry has `projectId`, `category`, `priority`, `flags`, and `skip`.

**File**: `scripts/batch-manifest.json` (new)

**Pattern**:
```json
{
  "version": 1,
  "projects": [
    {
      "projectId": "chain-meta-display",
      "category": "ready",
      "priority": 1,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "parallel-gen-1776452567763",
      "category": "ready",
      "priority": 2,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "text-chains-1776379250140",
      "category": "retroactive",
      "priority": 3,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "pipeline-v2-1776415926445",
      "category": "retroactive",
      "priority": 4,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "trendfy-port-1776381797246",
      "category": "retroactive",
      "priority": 5,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "waitlist-module-1776444761500",
      "category": "retroactive",
      "priority": 6,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "photoshoot-prompts-1776450888937",
      "category": "backlog",
      "priority": 7,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "spec-doc-self-spec-1776416446652",
      "category": "backlog",
      "priority": 8,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "distribution-experiment-1776433092383",
      "category": "backlog",
      "priority": 9,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    },
    {
      "projectId": "landing-page-1776432869599",
      "category": "backlog",
      "priority": 10,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    }
  ]
}
```

**Verify**: `node -e "const m = JSON.parse(require('fs').readFileSync('scripts/batch-manifest.json','utf8')); console.log(m.projects.length + ' projects, version ' + m.version)"` — expect `10 projects, version 1`

### Step 2: Create `batch-regen.mjs` with `loadManifest` and `validateManifest`

**Action**: Create the batch orchestrator file with two exported functions. `loadManifest(manifestPath)` reads and parses the JSON file, returning the parsed object. `validateManifest(manifest, projectsDir)` checks every entry against the schema rules from the architecture doc and verifies that each `projectId` has a matching directory with `epic.md` and `architecture.md`. Returns `{ valid: boolean, errors: string[] }`.

**File**: `scripts/batch-regen.mjs` (new)

**Pattern**:
```javascript
#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const DEFAULT_MANIFEST = path.join(__dirname, 'batch-manifest.json');
const PROJECTS_DIR = path.join(REPO_ROOT, 'projects');

const VALID_CATEGORIES = ['retroactive', 'ready', 'backlog'];

async function loadManifest(manifestPath = DEFAULT_MANIFEST) {
  const raw = await fs.readFile(manifestPath, 'utf8');
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Invalid JSON in manifest: ${e.message}`);
  }
  return parsed;
}

async function validateManifest(manifest, projectsDir = PROJECTS_DIR) {
  const errors = [];

  // Top-level schema
  if (manifest.version !== 1) {
    errors.push(`Unsupported manifest version: ${manifest.version} (expected 1)`);
  }
  if (!Array.isArray(manifest.projects)) {
    errors.push('manifest.projects must be an array');
    return { valid: false, errors };
  }

  const seenIds = new Set();
  const seenPriorities = new Set();

  for (let i = 0; i < manifest.projects.length; i++) {
    const p = manifest.projects[i];
    const prefix = `projects[${i}]`;

    // projectId
    if (typeof p.projectId !== 'string' || p.projectId.length === 0) {
      errors.push(`${prefix}.projectId must be a non-empty string`);
      continue;
    }
    if (seenIds.has(p.projectId)) {
      errors.push(`${prefix}.projectId "${p.projectId}" is duplicated`);
    }
    seenIds.add(p.projectId);

    // Directory existence + required files
    const projDir = path.join(projectsDir, p.projectId);
    try {
      await fs.access(projDir);
    } catch {
      errors.push(`${prefix}: directory not found: ${p.projectId}/`);
      continue;
    }
    for (const required of ['epic.md', 'architecture.md']) {
      try {
        await fs.access(path.join(projDir, required));
      } catch {
        errors.push(`${prefix}: missing ${required} in ${p.projectId}/`);
      }
    }

    // category
    if (!VALID_CATEGORIES.includes(p.category)) {
      errors.push(`${prefix}.category must be one of: ${VALID_CATEGORIES.join(', ')} (got "${p.category}")`);
    }

    // priority
    if (typeof p.priority !== 'number' || p.priority < 1 || !Number.isInteger(p.priority)) {
      errors.push(`${prefix}.priority must be a positive integer (got ${p.priority})`);
    } else {
      if (seenPriorities.has(p.priority)) {
        errors.push(`${prefix}.priority ${p.priority} is duplicated`);
      }
      seenPriorities.add(p.priority);
    }

    // flags
    if (typeof p.flags !== 'object' || p.flags === null) {
      errors.push(`${prefix}.flags must be an object`);
    } else {
      if (p.flags.parallel !== undefined) {
        if (typeof p.flags.parallel !== 'number' || p.flags.parallel < 1 || p.flags.parallel > 3) {
          errors.push(`${prefix}.flags.parallel must be 1–3 (got ${p.flags.parallel})`);
        }
      }
      if (p.flags.rescan !== undefined && typeof p.flags.rescan !== 'boolean') {
        errors.push(`${prefix}.flags.rescan must be boolean`);
      }
      if (p.flags.noReview !== undefined && typeof p.flags.noReview !== 'boolean') {
        errors.push(`${prefix}.flags.noReview must be boolean`);
      }
    }

    // skip
    if (typeof p.skip !== 'boolean') {
      errors.push(`${prefix}.skip must be boolean (got ${typeof p.skip})`);
    }
  }

  return { valid: errors.length === 0, errors };
}

export { loadManifest, validateManifest, VALID_CATEGORIES, DEFAULT_MANIFEST, PROJECTS_DIR };
```

**Verify**: `node -e "import('./scripts/batch-regen.mjs').then(m => console.log(Object.keys(m).sort().join(', ')))"` — expect `DEFAULT_MANIFEST, PROJECTS_DIR, VALID_CATEGORIES, loadManifest, validateManifest`

### Step 3: Write tests for manifest loading and validation

**Action**: Create `scripts/batch-regen.test.mjs` using `node:test` and `node:assert/strict` (matching the repo's existing test framework in `scripts/regen-task.test.mjs`). Cover: successful load, invalid JSON, schema violations (bad category, duplicate projectId, duplicate priority, missing required files, parallel out of range, non-integer priority, missing flags), and skip filtering.

**File**: `scripts/batch-regen.test.mjs` (new)

**Pattern**:
```javascript
import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { loadManifest, validateManifest, VALID_CATEGORIES } from './batch-regen.mjs';

// ── Helpers ─────────────────────────────────────────────────────────────────

async function withTempDir(fn) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'batch-test-'));
  try {
    return await fn(dir);
  } finally {
    await fs.rm(dir, { recursive: true, force: true });
  }
}

async function seedProject(projectsDir, id, files = ['epic.md', 'architecture.md']) {
  const projDir = path.join(projectsDir, id);
  await fs.mkdir(projDir, { recursive: true });
  for (const f of files) {
    await fs.writeFile(path.join(projDir, f), `# ${f}`);
  }
}

function validEntry(overrides = {}) {
  return {
    projectId: 'test-project',
    category: 'ready',
    priority: 1,
    flags: { parallel: 2, rescan: false, noReview: false },
    skip: false,
    ...overrides,
  };
}

// ── loadManifest ────────────────────────────────────────────────────────────

describe('loadManifest', () => {
  it('parses valid JSON manifest', async () => {
    await withTempDir(async (dir) => {
      const manifestPath = path.join(dir, 'manifest.json');
      const data = { version: 1, projects: [] };
      await fs.writeFile(manifestPath, JSON.stringify(data));
      const result = await loadManifest(manifestPath);
      assert.deepStrictEqual(result, data);
    });
  });

  it('throws on invalid JSON', async () => {
    await withTempDir(async (dir) => {
      const manifestPath = path.join(dir, 'bad.json');
      await fs.writeFile(manifestPath, '{ broken json }');
      await assert.rejects(() => loadManifest(manifestPath), /Invalid JSON/);
    });
  });

  it('throws on missing file', async () => {
    await assert.rejects(() => loadManifest('/nonexistent/manifest.json'));
  });
});

// ── validateManifest ────────────────────────────────────────────────────────

describe('validateManifest', () => {
  it('validates a correct manifest', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a' })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, true, `Unexpected errors: ${errors.join('; ')}`);
      assert.strictEqual(errors.length, 0);
    });
  });

  it('rejects unsupported version', async () => {
    await withTempDir(async (dir) => {
      const manifest = { version: 2, projects: [] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('version')));
    });
  });

  it('rejects non-array projects', async () => {
    await withTempDir(async (dir) => {
      const manifest = { version: 1, projects: 'not-array' };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('must be an array')));
    });
  });

  it('rejects invalid category', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', category: 'invalid' })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('category')));
    });
  });

  it('rejects duplicate projectId', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = {
        version: 1,
        projects: [
          validEntry({ projectId: 'proj-a', priority: 1 }),
          validEntry({ projectId: 'proj-a', priority: 2 }),
        ],
      };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('duplicated')));
    });
  });

  it('rejects duplicate priority', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      await seedProject(dir, 'proj-b');
      const manifest = {
        version: 1,
        projects: [
          validEntry({ projectId: 'proj-a', priority: 1 }),
          validEntry({ projectId: 'proj-b', priority: 1 }),
        ],
      };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('priority') && e.includes('duplicated')));
    });
  });

  it('rejects non-integer priority', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', priority: 1.5 })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('priority') && e.includes('positive integer')));
    });
  });

  it('rejects zero priority', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', priority: 0 })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('priority')));
    });
  });

  it('rejects missing project directory', async () => {
    await withTempDir(async (dir) => {
      const manifest = { version: 1, projects: [validEntry({ projectId: 'nonexistent' })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('directory not found')));
    });
  });

  it('rejects missing epic.md', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a', ['architecture.md']);
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a' })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('missing epic.md')));
    });
  });

  it('rejects missing architecture.md', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a', ['epic.md']);
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a' })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('missing architecture.md')));
    });
  });

  it('rejects parallel out of range (too high)', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', flags: { parallel: 5 } })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('flags.parallel') && e.includes('1–3')));
    });
  });

  it('rejects parallel out of range (zero)', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', flags: { parallel: 0 } })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('flags.parallel')));
    });
  });

  it('rejects non-boolean skip', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', skip: 'yes' })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('skip') && e.includes('boolean')));
    });
  });

  it('rejects null flags', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', flags: null })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('flags must be an object')));
    });
  });

  it('accepts optional flags fields (parallel, rescan, noReview can be omitted)', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', flags: {} })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, true, `Unexpected errors: ${errors.join('; ')}`);
    });
  });

  it('rejects non-boolean rescan flag', async () => {
    await withTempDir(async (dir) => {
      await seedProject(dir, 'proj-a');
      const manifest = { version: 1, projects: [validEntry({ projectId: 'proj-a', flags: { rescan: 'yes' } })] };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.some(e => e.includes('flags.rescan') && e.includes('boolean')));
    });
  });

  it('collects multiple errors in a single pass', async () => {
    await withTempDir(async (dir) => {
      const manifest = {
        version: 99,
        projects: [
          { projectId: '', category: 'wrong', priority: -1, flags: null, skip: 'nope' },
        ],
      };
      const { valid, errors } = await validateManifest(manifest, dir);
      assert.strictEqual(valid, false);
      assert.ok(errors.length >= 2, `Expected multiple errors, got ${errors.length}`);
    });
  });
});

// ── VALID_CATEGORIES export ─────────────────────────────────────────────────

describe('VALID_CATEGORIES', () => {
  it('contains exactly three categories', () => {
    assert.strictEqual(VALID_CATEGORIES.length, 3);
    assert.ok(VALID_CATEGORIES.includes('retroactive'));
    assert.ok(VALID_CATEGORIES.includes('ready'));
    assert.ok(VALID_CATEGORIES.includes('backlog'));
  });
});

// ── Seed manifest validation against real projects ──────────────────────────

describe('seed manifest (integration)', () => {
  let manifest;

  before(async () => {
    manifest = await loadManifest();
  });

  it('loads the seed manifest without parse errors', () => {
    assert.strictEqual(manifest.version, 1);
    assert.ok(Array.isArray(manifest.projects));
  });

  it('contains exactly 10 projects', () => {
    assert.strictEqual(manifest.projects.length, 10);
  });

  it('has unique projectIds', () => {
    const ids = manifest.projects.map(p => p.projectId);
    assert.strictEqual(new Set(ids).size, ids.length, `Duplicate IDs: ${ids}`);
  });

  it('has unique priorities', () => {
    const pris = manifest.projects.map(p => p.priority);
    assert.strictEqual(new Set(pris).size, pris.length, `Duplicate priorities: ${pris}`);
  });

  it('orders ready projects before retroactive before backlog', () => {
    const categories = manifest.projects
      .sort((a, b) => a.priority - b.priority)
      .map(p => p.category);
    const firstRetro = categories.indexOf('retroactive');
    const firstBacklog = categories.indexOf('backlog');
    const lastReady = categories.lastIndexOf('ready');
    const lastRetro = categories.lastIndexOf('retroactive');
    assert.ok(lastReady < firstRetro || firstRetro === -1, 'All ready must come before retroactive');
    assert.ok(lastRetro < firstBacklog || firstBacklog === -1, 'All retroactive must come before backlog');
  });

  it('validates against real projects/ directory', async () => {
    const { valid, errors } = await validateManifest(manifest);
    assert.strictEqual(valid, true, `Manifest validation failed:\n${errors.join('\n')}`);
  });
});
```

**Verify**: `node --test scripts/batch-regen.test.mjs` — expect all tests passing (0 failures)

---

## 5. Tests

See Step 3 above for complete test bodies. The test file contains 21 tests across 4 describe blocks:

| Block | Tests | What it covers |
|-------|-------|----------------|
| `loadManifest` | 3 | Valid parse, invalid JSON, missing file |
| `validateManifest` | 16 | Every schema rule: version, array check, category enum, duplicate ID, duplicate priority, non-integer priority, zero priority, missing directory, missing epic, missing architecture, parallel range (high/low), non-boolean skip, null flags, optional flag fields, non-boolean rescan, multi-error accumulation |
| `VALID_CATEGORIES` | 1 | Export correctness |
| `seed manifest (integration)` | 5 | Real manifest loads, 10 projects, unique IDs, unique priorities, category ordering, validates against `projects/` directory |

No test stubs. Every test has a complete assertion body using `node:assert/strict`.

---

## 6. Commit Plan

1. **`feat(batch): add manifest schema and seed 10 target projects`** — `scripts/batch-manifest.json`, `scripts/batch-regen.mjs`: manifest file with 10 projects (2 ready, 4 retroactive, 4 backlog) and loadManifest/validateManifest functions
2. **`test(batch): add 21 tests for manifest loading and validation`** — `scripts/batch-regen.test.mjs`: unit tests for schema validation rules plus integration test against real projects directory

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/batch-regen.test.mjs
node --test scripts/regen-task.test.mjs
```

**Expected delta**: 35 → 35 passing (regen-task unchanged) + 21 new passing (batch-regen). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **Prescribed project ID doesn't match an actual directory** → verify in `projects/`, use the actual directory name. The 10 IDs in this guide were confirmed against the real filesystem at generation time, but directory names may have changed since.
- **A project is missing `architecture.md`** → keep it in the manifest but add `"skip": true` and note the reason in a comment-adjacent field or in the commit body. Do not remove it — the operator may generate the architecture later.
- **Test framework mismatch** → match `scripts/regen-task.test.mjs` conventions (`node:test`, `node:assert/strict`). If the repo has migrated to a different framework, translate silently but note in commit body.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task creates the static manifest and its loader/validator. It does NOT build the orchestrator loop, progress reporting, failure recovery, or summary generation — those are Tasks 3–6 respectively. The manifest schema here is the _base_ schema; the retry manifest extension (adding `taskNums` field) belongs to Task 5.

- **`scanProjectInventory()` function** — Task 1 scope. The manifest is hand-seeded, not auto-generated from scanning.
- **`runBatch()` orchestrator loop** — Task 3 scope. This task only creates the file that Task 3 will extend with the main loop.
- **CLI argument parsing for `batch-regen.mjs`** — Task 3 scope (`--manifest`, `--dry-run`, `--retry` flags).
- **Retry manifest schema extension** — Task 5 scope. The `taskNums` array field is not part of the base schema.
- **Category auto-detection** — deferred. The braindump categories are manually assigned based on operator knowledge; auto-detection from git history or file presence is a future enhancement if the manifest grows beyond 10 projects.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)

---

##### Post-generation review (auto)

**Overall**: 5/5 (gold)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 5/5 | All required task-spec sections present: Purpose, Dependencies, Pre-flight, Files, Implementation Steps, Tests, Commit Plan, Verification, Rollback, Deviations Allowed, Out of Scope, Related Documents |
| Content routing | 4/5 | Trade-offs in Section 1 (auto-generate vs hand-seed, YAML vs JSON, JS module vs JSON) are task-level rationale — appropriate here — but should be cross-referenced to the architecture decision log if one exists, to avoid drift between the two |
| Pattern application | 4/5 | No execution flow diagram for the validate → load → check-files pipeline; a simple sequential diagram would help an executor visualize the validation order before reading code |
| Rule compliance | 5/5 | No status words in the spec body — status tracking correctly deferred to timeline.md |
| Content quality | 5/5 | Extremely opinionated: specific project IDs verified against real filesystem, exact category assignments with rationale, concrete flag ranges (parallel 1–3) |
| Usefulness | 5/5 | An executor agent could implement this verbatim with zero ambiguity — complete code patterns, verify commands, and expected outputs |

**Top fixes**:
- Convert the three trade-offs in Section 1 to a structured Decision Justification Table (Option | Rejected Because | Chosen Alternative) and cross-reference the architecture decision log
- Add a simple sequential flow diagram for validateManifest: parse JSON → check version → iterate entries → check directory → check required files → check schema fields → accumulate errors
- Convert Out of Scope bullets to a ✅/❌ boundary table with a 'Belongs To' column (e.g., '❌ scanProjectInventory() — Task 1') for faster scanning
