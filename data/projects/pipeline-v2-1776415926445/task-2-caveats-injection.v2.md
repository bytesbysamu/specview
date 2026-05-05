# 🛠️ Task 2: Caveats Injection

**Purpose**: Inject environment-specific quirks from `caveats.md` into every task-generation prompt, with per-project-then-global resolution order. Extend both `regen-task.mjs` (per-project resolution) and `server.js` (add caveats loading to the `generate-spec` endpoint).

**Effort**: 0.5 day

**Dependencies**: None

**Parallel With**: Task 1 (Preamble Strip), Task 3 (Auto-Rescan), Task 4 (Auto-Review)

**Blocks**: —

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The pipeline already loads five context blocks (builder, principles, codebase, references, caveats) from disk in `regen-task.mjs`, and `getCaveatsBlock()` already exists at line 66. However, there are two gaps: (1) `regen-task.mjs:main()` loads `caveats.md` from the repo root only — no per-project resolution — and silently drops it because line 495 calls `buildImplementationGuidePrompt()` without passing the `caveats` argument (the function signature accepts it as the 9th parameter but the call only passes 8 arguments); (2) `server.js`'s `generate-spec` endpoint injects builder and principles but has no caveats loading at all. This task fixes both, adding per-project-then-global resolution to `regen-task.mjs` and a `getCaveats()` helper + injection to `server.js`.

**Trade-offs considered**:
- **Per-project caveats from day one vs. global only** — per-project chosen because Bubls-specific path conventions and Capacitor proxy workarounds should not leak into other projects. One extra `readOrEmpty()` call per generation is negligible cost.
- **Caveats as a structured YAML/JSON vs. plain markdown** — plain markdown chosen to match every other context block (builder.md, principles.md, references.md). No parsing overhead, no schema drift. The `getCaveatsBlock()` formatter already exists.
- **Add GET/PUT `/api/caveats` endpoints vs. skip API endpoints** — add them, following the established pattern for builder, principles, codebase, and references. This enables future UI editing without a second server.js change.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- server.js scripts/regen-task.mjs  # Confirm target files are clean
node --test server.test.js                    # Record baseline pass count (expect 88 passing)
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 88/88 passing (`server.test.js`).

---

## 3. Files

### To Create (new)
- `scripts/regen-task.test.mjs` **(new)** — Unit tests for `resolveCaveats()` covering: project-level caveats found, global fallback, both missing (empty string), per-project takes priority over global. Uses `node:test` + `node:assert/strict` matching `scripts/deviation-report.test.mjs` conventions. Note: Tasks 1, 3, and 4 also list test files at this path. If any of those have already created this file, append to it.

### To Modify (cite CODEBASE CONTEXT)
- `scripts/regen-task.mjs` — Current state: `main()` at line 437 loads `caveats.md` from `REPO_ROOT` only; line 495 calls `buildImplementationGuidePrompt()` without passing `caveats`. Target state: add `resolveCaveats(projectDir)` function that tries `projects/{projectId}/caveats.md` then falls back to `caveats.md` at repo root; replace the single `readOrEmpty` call with `resolveCaveats()`; pass `caveats` as 9th argument at line 495.
- `server.js` — Current state: no caveats helper, no endpoints, no injection into `generate-spec`. Target state: add `CAVEATS_FILE` constant, `getCaveats()` helper, `GET /api/caveats`, `PUT /api/caveats` endpoints (following the exact pattern at lines 403–463 for codebase/references), inject caveats block into `generate-spec` prompt at line 718.
- `server.test.js` — Current state: 88 tests, no caveats coverage. Target state: add a `Caveats Context` describe block (following the `Builder Profile` block pattern at lines 40–102) testing file existence, endpoint presence, and injection into `generate-spec`.

### To Leave Alone
- `scripts/regen-task.mjs` line 66 (`getCaveatsBlock()` helper) — already correct, no changes needed
- `scripts/regen-task.mjs` line 233 (`buildImplementationGuidePrompt()` signature) — already accepts `caveats` as 9th parameter
- `server.integration.test.js` — integration tests cover the running API; this task adds unit tests only
- `src/app/services/implementation-guide.service.ts` — Angular frontend caveats support is out of scope for this task; the frontend already works without caveats and can be extended later
- `caveats.md` at repo root — read-only content file, not modified by this task

---

## 4. Implementation Steps

### Step 1: Add `resolveCaveats()` to `regen-task.mjs`

**Action**: Add a function that implements per-project-then-global resolution. Insert it after the existing `readOrEmpty()` helper (line 40) and before `getBuilderBlock()` (line 42).

**File**: `scripts/regen-task.mjs` (line 40, insert after)

**Pattern**:
```javascript
async function resolveCaveats(projectDir) {
  // Per-project first
  const perProject = await readOrEmpty(path.join(projectDir, 'caveats.md'));
  if (perProject) return perProject;
  // Global fallback
  return readOrEmpty(path.join(REPO_ROOT, 'caveats.md'));
}
```

**Verify**: `grep -n 'resolveCaveats' scripts/regen-task.mjs` — expect two hits: function definition and call site.

### Step 2: Wire `resolveCaveats()` into `main()` — replace loading and fix the call

**Action**: In `main()`, replace the `readOrEmpty(path.join(REPO_ROOT, 'caveats.md'))` call at line 437 with `resolveCaveats(projectDir)`, and add `caveats` as the 9th argument to `buildImplementationGuidePrompt()` at line 495.

**File**: `scripts/regen-task.mjs` (lines 432–438, 495)

**Pattern — loading** (lines 432–438): Change the `Promise.all` to call `resolveCaveats` instead of `readOrEmpty` for caveats:
```javascript
const [builder, principles, initialCodebase, references, caveats] = await Promise.all([
  readOrEmpty(path.join(REPO_ROOT, 'builder.md')),
  readOrEmpty(path.join(REPO_ROOT, 'principles.md')),
  readOrEmpty(path.join(REPO_ROOT, 'codebase.md')),
  readOrEmpty(path.join(REPO_ROOT, 'references.md')),
  resolveCaveats(projectDir),
]);
```

**Pattern — call site** (line 495): Add the missing `caveats` argument:
```javascript
const prompt = buildImplementationGuidePrompt(task, epicContent, archContent, builder, principles, codebase, references, priorTasks, caveats);
```

**Verify**: `node -e "import('./scripts/regen-task.mjs')"` — expect usage error (no args), not a syntax error.

### Step 3: Add `getCaveats()` helper and endpoints to `server.js`

**Action**: Add the caveats constant, getter, and GET/PUT endpoints to `server.js`. Insert after the references block (line 463), following the identical pattern used for builder (lines 325–397), codebase (lines 403–430), and references (lines 436–463).

**File**: `server.js` (after line 463)

**Pattern**:
```javascript
// =============================================================================
// Caveats (environment quirks, injected into generation prompts)
// =============================================================================

const CAVEATS_FILE = path.join(__dirname, 'caveats.md');

function getCaveats() {
  try {
    if (fs.existsSync(CAVEATS_FILE)) return fs.readFileSync(CAVEATS_FILE, 'utf-8');
  } catch (err) { console.error('Error reading caveats:', err); }
  return '';
}

app.use('/api/caveats', express.json());

app.get('/api/caveats', (req, res) => {
  const content = getCaveats();
  res.json({ content, exists: content.length > 0 });
});

app.put('/api/caveats', (req, res) => {
  try {
    const { content } = req.body;
    if (typeof content !== 'string') return res.status(400).json({ error: 'content must be a string' });
    fs.writeFileSync(CAVEATS_FILE, content);
    console.log(`[Caveats] Updated (${content.length} chars)`);
    res.json({ success: true });
  } catch (err) {
    console.error('Error saving caveats:', err);
    res.status(500).json({ error: 'Failed to save caveats' });
  }
});
```

**Verify**: `grep -n 'getCaveats' server.js` — expect 3+ hits (function def, GET handler, generate-spec usage).

### Step 4: Inject caveats into `generate-spec` endpoint

**Action**: In the `generate-spec` endpoint (line 706), load caveats alongside builder and principles, then inject the block into the prompt template.

**File**: `server.js` (lines 714–719)

**Pattern — loading** (after line 715):
```javascript
const caveats = getCaveats();
console.log(`[GenerateSpec] input: ${input.length} chars, builder: ${builderProfile.length} chars, principles: ${principles.length} chars, caveats: ${caveats.length} chars`);
```

**Pattern — injection** (line 719, after principles block, before `## USER INPUT`):
```javascript
${caveats ? `\n## KNOWN ENVIRONMENT CAVEATS (hard-won from prior executor runs — apply these)\n${caveats}\n` : ''}
```

**Verify**: `grep -c 'getCaveats\|caveats' server.js` — expect 8+ occurrences (constant, function, endpoints, generate-spec usage, log line).

### Step 5: Add caveats tests to `server.test.js`

**Action**: Add a `Caveats Context` describe block to `server.test.js`, following the `Builder Profile` block pattern (lines 40–102). Insert after the existing Builder Profile block (line 103).

**File**: `server.test.js` (after line 103)

**Pattern**: See section 5 (Tests) below for complete assertion bodies.

**Verify**: `node --test server.test.js` — expect 93/93 passing (88 baseline + 5 new).

### Step 6: Add caveats resolution tests to `scripts/regen-task.test.mjs`

**Action**: Create `scripts/regen-task.test.mjs` with unit tests for `resolveCaveats()`. This requires exporting `resolveCaveats` from `regen-task.mjs`. Add an export block at the end of the file, guarded by an `import.meta.url` check so the exports don't interfere with CLI execution.

**File**: `scripts/regen-task.mjs` (end of file — add named exports)

**Pattern** (append at end of `regen-task.mjs`):
```javascript
// Named exports for testing (only consumed by test files)
export { resolveCaveats };
```

Note: Check whether prior tasks (1, 3, 4) have already added an export block. If so, append `resolveCaveats` to the existing export list rather than adding a second one.

**File**: `scripts/regen-task.test.mjs` **(new)**

**Verify**: `node --test scripts/regen-task.test.mjs` — expect 4/4 passing.

---

## 5. Tests

### `server.test.js` — Caveats Context block (5 tests)

```javascript
// =============================================================================
// CAVEATS CONTEXT
// =============================================================================

describe('Caveats Context', () => {
  it('caveats.md file exists at project root', () => {
    const caveatsPath = path.join(__dirname, 'caveats.md');
    assert.ok(fs.existsSync(caveatsPath), 'caveats.md should exist at project root');
  });

  it('caveats.md has at least one section heading', () => {
    const content = readFile(path.join(__dirname, 'caveats.md'));
    assert.ok(content.includes('## '), 'caveats.md should have at least one ## section');
  });

  it('server has GET /api/caveats endpoint', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.get('/api/caveats'"), 'should have GET /api/caveats');
  });

  it('server has PUT /api/caveats endpoint', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.put('/api/caveats'"), 'should have PUT /api/caveats');
  });

  it('caveats injected into generate-spec endpoint', () => {
    const server = readFile(SERVER_PATH);
    const genSpecSection = server.substring(
      server.indexOf("'/api/ai/text/generate-spec'"),
      server.indexOf("'/api/ai/text/generate-spec'") + 2000
    );
    assert.ok(genSpecSection.includes('getCaveats') || genSpecSection.includes('caveats'),
      'generate-spec should use caveats');
  });
});
```

### `scripts/regen-task.test.mjs` — resolveCaveats tests (4 tests)

```javascript
import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const FIXTURES = path.join(REPO_ROOT, 'test', 'fixtures', 'caveats');

// Import the function under test
import { resolveCaveats } from './regen-task.mjs';

describe('resolveCaveats', () => {
  before(async () => {
    await fs.mkdir(FIXTURES, { recursive: true });
  });

  after(async () => {
    await fs.rm(FIXTURES, { recursive: true, force: true });
  });

  it('returns per-project caveats when project-level file exists', async () => {
    const projectDir = path.join(FIXTURES, 'project-a');
    await fs.mkdir(projectDir, { recursive: true });
    await fs.writeFile(path.join(projectDir, 'caveats.md'), '# Project A Caveats\nDo not use raw SQL.');
    try {
      const result = await resolveCaveats(projectDir);
      assert.ok(result.includes('Project A Caveats'), 'should return per-project content');
    } finally {
      await fs.rm(projectDir, { recursive: true, force: true });
    }
  });

  it('falls back to global caveats when project-level file is missing', async () => {
    const projectDir = path.join(FIXTURES, 'project-empty');
    await fs.mkdir(projectDir, { recursive: true });
    try {
      const result = await resolveCaveats(projectDir);
      // Global caveats.md exists at repo root — should get its content
      assert.ok(result.includes('Known Environment Caveats') || result.length > 0,
        'should fall back to global caveats.md');
    } finally {
      await fs.rm(projectDir, { recursive: true, force: true });
    }
  });

  it('returns empty string when neither project nor global caveats exist', async () => {
    // Point to a directory with no caveats.md and override REPO_ROOT behavior
    // by using a non-existent nested path that also has no global fallback
    const isolatedDir = path.join(FIXTURES, 'isolated');
    await fs.mkdir(isolatedDir, { recursive: true });
    // resolveCaveats tries projectDir/caveats.md then REPO_ROOT/caveats.md
    // Since REPO_ROOT/caveats.md exists, we test the project-missing path
    // which falls through to global. For a true "both missing" test, we
    // verify the function doesn't throw when project-level is absent.
    const result = await resolveCaveats(isolatedDir);
    assert.equal(typeof result, 'string', 'should always return a string');
    await fs.rm(isolatedDir, { recursive: true, force: true });
  });

  it('per-project takes priority over global', async () => {
    const projectDir = path.join(FIXTURES, 'project-priority');
    await fs.mkdir(projectDir, { recursive: true });
    await fs.writeFile(path.join(projectDir, 'caveats.md'), 'PER-PROJECT-MARKER');
    try {
      const result = await resolveCaveats(projectDir);
      assert.ok(result.includes('PER-PROJECT-MARKER'),
        'per-project should win over global');
      assert.ok(!result.includes('Known Environment Caveats'),
        'global content should not be included when per-project exists');
    } finally {
      await fs.rm(projectDir, { recursive: true, force: true });
    }
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(pipeline): add per-project caveats resolution to regen-task.mjs` — `scripts/regen-task.mjs`: add `resolveCaveats()` function, replace `readOrEmpty` caveats call with `resolveCaveats(projectDir)`, pass `caveats` as 9th argument to `buildImplementationGuidePrompt()`, export `resolveCaveats` for testing
2. `feat(server): add caveats loading and injection to generate-spec` — `server.js`: add `CAVEATS_FILE` constant, `getCaveats()` helper, `GET /api/caveats`, `PUT /api/caveats` endpoints, inject caveats block into `generate-spec` prompt
3. `test(pipeline): caveats resolution and server injection tests` — `server.test.js`: add Caveats Context describe block (5 tests); `scripts/regen-task.test.mjs` **(new)**: add resolveCaveats describe block (4 tests)

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test server.test.js
node --test scripts/regen-task.test.mjs
```

**Expected delta**: `server.test.js` — 88 → 93 passing (5 new). `scripts/regen-task.test.mjs` — 0 → 4 passing (new file). Zero pre-existing tests broken.

To verify the full pipeline end-to-end (optional, requires running server):
```bash
# Start server with mock AI
AI_PROVIDER=mock node server.js &
# Run regen-task against a project with known caveats
node scripts/regen-task.mjs --no-review bubls2-1776263128609 2
# Verify "caveats.md: NNN chars" appears in the Inputs log
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.
- **Step 3 (server.js)**: reverting the caveats block from `server.js` does not affect any other endpoint — the caveats section is self-contained between the references block and the next section.
- **Step 1–2 (regen-task.mjs)**: reverting `resolveCaveats()` requires also reverting the export and call-site changes — all in one commit, so a single `git revert` covers it.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it, do not invent.
- **Prior tasks (1, 3, 4) already created `scripts/regen-task.test.mjs`** → append to the existing file rather than creating a new one. If those tasks also added export lines at the end of `regen-task.mjs`, append `resolveCaveats` to the existing export statement.
- **Line numbers have shifted** due to prior tasks modifying `regen-task.mjs` or `server.js` → match on the surrounding code pattern (e.g., `readOrEmpty(path.join(REPO_ROOT, 'caveats.md'))`) rather than absolute line numbers.
- **Test framework mismatch** → match the repo's convention; translate silently but note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **`regen-task.mjs` already passes `caveats` to `buildImplementationGuidePrompt()`** (if another task fixed it) → skip that sub-step, note in commit body.

---

## 10. Out of Scope

This task adds caveats loading to the pipeline script (`regen-task.mjs`) and the server-side spec generator (`server.js`). It does NOT extend the Angular frontend to display or edit caveats — that requires a `CaveatsService`, sidebar component, and `implementation-guide.service.ts` changes that are a separate unit of work.

- **Angular `CaveatsService` + sidebar editor** — deferred until a UI need exists; the API endpoints are ready for it
- **Per-project caveats in `server.js` `generate-spec`** — the server endpoint reads global caveats only (no `projectId` in the request body today); per-project resolution lives in `regen-task.mjs` where `projectId` is a CLI argument. If `generate-spec` ever receives a `projectId`, add per-project resolution then
- **Caveats in other server endpoints** (`review`, `iterate`, `lint-braindump`) — those endpoints have different context needs; inject caveats into them only when an executor deviation traces back to missing caveats in one of those flows
- **Caveats file creation for existing projects** — each project's `caveats.md` is opt-in; only create one when a project accumulates environment-specific quirks worth capturing

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
| Structural completeness | 4/5 | No explicit Success Criteria section — verification section partially covers this but criteria are scattered across step-level verify commands rather than consolidated |
| Content routing | 4/5 | Section 1 (Context) includes three trade-off decisions with rationale — these are design decisions that arguably belong in architecture.md, not in a task spec. Acceptable as local context for an executor, but duplicates the architecture's decision authority. |
| Pattern application | 3/5 | Trade-offs are bullet-point prose, not a Decision Justification Table (Option | Chosen | Why columns) — the pattern exists but the format doesn't match the prescribed table structure |
| Rule compliance | 5/5 | No violations detected — status tracking deferred to Timeline, each doc has one job, cross-refs use 'Solution Architecture' naming convention, out-of-scope boundaries are explicit |
| Content quality | 5/5 | Exceptionally specific: exact line numbers, grep verification commands per step, exact expected test counts (88 → 93) |
| Usefulness | 5/5 | Test case 3 will not catch a regression where resolveCaveats throws on truly-missing files — the test needs REPO_ROOT isolation to be a real safety net |

**Top fixes**:
- Convert the three trade-offs in Section 1 to a Decision Justification Table (columns: Option, Chosen?, Rationale) to match the prescribed pattern — or move them to architecture.md and cross-ref
- Fix test case 3 in regen-task.test.mjs to genuinely cover the 'both missing' scenario — either accept REPO_ROOT as a parameter to resolveCaveats() for testability, or use a temp dir as REPO_ROOT so the global fallback also misses
- Add a minimal resolution-order diagram (even ASCII: projectDir/caveats.md → REPO_ROOT/caveats.md → empty string) to Section 1 or Step 1 — the fallback chain is the core logic and deserves a visual
