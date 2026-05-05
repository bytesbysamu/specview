# 🛠️ Task 2: Extract Reusable Task Runner

**Purpose**: Eliminate the ~70 lines of duplicated generation logic in the single-task code path by making it call the already-extracted `generateOneTask()`, and add tests that pin the adapter boundary so future tasks can't re-introduce the duplication.

**Effort**: 0.5 day

**Dependencies**: None

**Parallel With**: Task 1 (Concurrency Ceiling Test), Task 3 (Wave Grouper)

**Blocks**: Task 4 (`--parallel N` Flag), Task 5 (`--all` Flag)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

`generateOneTask()` already exists at `scripts/regen-task.mjs:559-621` — it was introduced when parallel/all mode was added. However, the single-task legacy code path (lines 654–768) still performs its own inline prompt assembly, curl call, preamble strip, auto-review, and file write, duplicating everything `generateOneTask` already does. This means a bug fix to the generation logic must be applied in two places, and the two paths can silently diverge. This task replaces the inline logic with a call to `generateOneTask()`, keeping only the single-task-specific diagnostic output (input reporting, size comparison, first-30-lines preview) as wrapper code in `main()`. It also adds `taskName` to the return type (per architecture spec) and adds tests that pin the extraction.

**Trade-offs considered** (≤3 bullets):
- **Keep both paths and sync manually** — rejected because two independent implementations of the same logic is a maintenance liability; any fix to generation must be applied twice
- **Move all diagnostic output into `generateOneTask`** — rejected because size comparison, first-30-lines preview, and verbose input reporting are CLI concerns that don't belong in a reusable function called by the batch orchestrator
- **Refactor single-task path to call `generateOneTask`, keep presentation in `main()`** — preferred because it eliminates duplication while preserving the single-task UX; the function stays clean for batch consumers

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                             # Flag any unrelated M/?? entries
git diff HEAD -- scripts/regen-task.mjs                # Confirm target file is clean
git diff HEAD -- scripts/regen-task.test.mjs           # Confirm test file is clean
node --test scripts/regen-task.test.mjs 2>&1 | tail -5 # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: All tests in `scripts/regen-task.test.mjs` passing (currently 28 tests across 5 describe blocks).

---

## 3. Files

### To Create (new)
- None

### To Modify (cite CODEBASE CONTEXT)
- `scripts/regen-task.mjs` — single-task path (lines 654–768) replaced with `generateOneTask()` call + post-call presentation; `generateOneTask` return type gains `taskName` field
- `scripts/regen-task.test.mjs` — add `generateOneTask` describe block (export verification, return shape, structural adapter test)

### To Leave Alone
- `scripts/context-loader.mjs` — shared context block formatters; no changes needed
- `scripts/context-loader.test.mjs` — unrelated tests
- `scripts/deviation-report.mjs` — unrelated script
- `server.js` — no server changes for this task
- `package.json` — `test:regen-task` script already exists

---

## 4. Implementation Steps

### Step 1: Add `taskName` to `generateOneTask` return value

**Action**: In the success return statement of `generateOneTask`, add `taskName: task.name` to the returned object. This aligns the return type with the architecture spec (`{ success, taskNum, taskName, filePath, latencyMs, error }`).

**File**: `scripts/regen-task.mjs` (line 615)

**Pattern**:
```javascript
// Before (line 615):
return { success: true, taskNum: task.num, filePath: outPath, latencyMs: latencyMs ?? elapsed, error: null };

// After:
return { success: true, taskNum: task.num, taskName: task.name, filePath: outPath, latencyMs: latencyMs ?? elapsed, error: null };
```

Also update the failure return (line 619):
```javascript
// Before (line 619):
return { success: false, taskNum: task.num, filePath: null, latencyMs: elapsed, error: err.message };

// After:
return { success: false, taskNum: task.num, taskName: task.name, filePath: null, latencyMs: elapsed, error: err.message };
```

**Verify**: `grep -n 'taskName' scripts/regen-task.mjs` — expect two hits in `generateOneTask` return statements

### Step 2: Refactor single-task path to call `generateOneTask`

**Action**: Replace the inline generation logic in the single-task code path (lines 694–747) with a call to `generateOneTask()`. Keep all pre-call setup (rescan, input reporting) and post-call presentation (size comparison, first-30-lines, next-steps hint) in `main()`. The result object from `generateOneTask` provides `filePath` and `success` for the post-call code.

**File**: `scripts/regen-task.mjs` (lines 654–768, the `if (taskNum !== null)` block)

**Pattern** — the refactored single-task block becomes:
```javascript
// ─── SINGLE-TASK MODE (legacy — no --parallel, no --all, exactly 1 task) ───
if (taskNum !== null) {
    const task = allTasks.find((t) => t.num === taskNum);
    if (!task) {
      console.error(`✗ Task ${taskNum} not found in epic.md task table. Found tasks: ${allTasks.map((t) => t.num).join(', ')}`);
      process.exit(1);
    }

    // Rescan codebase if needed (unchanged)
    let codebase = initialCodebase;
    if (shouldRescan(taskNum, allTasks, forceRescan)) {
      const reason = forceRescan
        ? '--rescan flag'
        : `depends on foundation task(s): ${task.deps.filter(d => isFoundationTask(d, allTasks)).join(', ')}`;
      console.log(`── Rescan triggered (${reason}) ──`);
      const freshContent = await triggerRescan(REPO_ROOT);
      if (freshContent !== null) {
        codebase = freshContent;
      } else {
        console.log('  (falling back to existing codebase.md)');
      }
    }

    // Report inputs (unchanged)
    console.log('── Inputs ──');
    console.log(`  builder.md:    ${builder ? `${builder.length} chars` : '⚠️  MISSING'}`);
    console.log(`  principles.md: ${principles ? `${principles.length} chars` : '⚠️  MISSING'}`);
    console.log(`  codebase.md:   ${codebase ? `${codebase.length} chars` : '⚠️  MISSING (regeneration loses the main Prompt 10 benefit — see plan)'}${codebase !== initialCodebase ? ' (freshly rescanned)' : ''}`);
    console.log(`  references.md: ${references ? `${references.length} chars` : '(none — no cross-project code to port)'}`);
    const caveatsSource = await readOrEmpty(path.join(projectDir, 'caveats.md')) ? 'per-project' : (caveats ? 'global' : null);
    console.log(`  caveats.md:    ${caveats ? `${caveats.length} chars (${caveatsSource})` : '(none — no environment caveats)'}`);
    console.log(`  epic.md:       ${epicContent.length} chars`);
    console.log(`  architecture.md: ${archContent.length} chars`);

    const priorTasks = await loadPriorTasksSummary(projectDir, taskNum);
    console.log(`  prior tasks:   ${priorTasks ? `${priorTasks.length} chars` : '(none — this is the first task)'}`);

    console.log(`── Task ──`);
    console.log(`  ${task.num} — ${task.name} (${task.effort})`);
    console.log('');

    // ── Call generateOneTask (replaces inline generation) ──
    const sharedCtx = { epicContent, archContent, builder, principles, codebase, references, caveats, projectDir };
    console.log(`→ Generating task-${taskNum} (this may take 1–5 min)…`);
    const result = await generateOneTask(projectId, task, sharedCtx, { noReview });

    if (!result.success) {
      console.error(`✗ Generation failed: ${result.error}`);
      process.exit(1);
    }

    console.log(`✓ Wrote ${path.relative(REPO_ROOT, result.filePath)}`);

    // Size comparison with v1 (single-task UX only)
    const originalName = (await fs.readdir(projectDir)).find(
      (f) => f.match(new RegExp(`^task-${task.num}[-–].+\\.md$`)) && !f.endsWith('.v2.md'),
    );
    if (originalName) {
      const original = await fs.readFile(path.join(projectDir, originalName), 'utf8');
      const finalText = await fs.readFile(result.filePath, 'utf8');
      console.log(`── Size comparison ──`);
      console.log(`  v1 (${originalName}): ${original.length} chars, ${original.split('\n').length} lines`);
      console.log(`  v2: ${finalText.length} chars, ${finalText.split('\n').length} lines`);
      console.log(`  Δ:  ${finalText.length - original.length >= 0 ? '+' : ''}${finalText.length - original.length} chars`);
    }

    // Preview first 30 lines
    const finalText = await fs.readFile(result.filePath, 'utf8');
    console.log('');
    console.log('── First 30 lines of v2 ──');
    console.log(finalText.split('\n').slice(0, 30).join('\n'));
    console.log('');
    console.log(`── Next ──`);
    console.log(`  diff -u ${path.relative(REPO_ROOT, path.join(projectDir, originalName ?? '(original)'))} \\`);
    console.log(`          ${path.relative(REPO_ROOT, result.filePath)} | head -400`);
    return;
}
```

**Key deletions**: Remove the following inline blocks entirely (they are now handled by `generateOneTask`):
- Prompt assembly + logging (~lines 694-697)
- curl call + error handling (~lines 698-723)
- Preamble strip (~line 720-721)
- Auto-review block (~lines 727-739)
- `finalText` assembly + file write (~lines 741-747)

**Verify**: `node --test scripts/regen-task.test.mjs` — all existing tests pass. Then manually verify single-task invocation produces the same output file:
```bash
# Dry-run verification against a known project (compare file sizes/content)
node scripts/regen-task.mjs <existing-project-id> <task-num> --no-review
```

### Step 3: Add tests for `generateOneTask`

**Action**: Add a new `describe('generateOneTask')` block to the existing test file. Since `generateOneTask` calls `execSync(curl ...)`, unit tests focus on: export verification, structural adapter boundary enforcement (no other function in the module should call the generate endpoint), and the `taskName` field in the return type contract.

**File**: `scripts/regen-task.test.mjs`

**Pattern**: See Section 5 (Tests) below for complete test bodies.

**Verify**: `node --test scripts/regen-task.test.mjs` — expect 3 new tests passing in the `generateOneTask` block

### Step 4: Verify no stale references to removed code

**Action**: Search for any remaining inline curl-to-generate calls in the single-task path. After the refactoring, the only `curl.*api/ai/text/generate` calls should be inside `generateOneTask` and `reviewSpec`.

**File**: `scripts/regen-task.mjs`

**Verify**: `grep -n 'api/ai/text/generate' scripts/regen-task.mjs` — expect exactly 1 hit (inside `generateOneTask` at ~line 579). The `reviewSpec` function calls `/api/ai/text/review` (different endpoint), which is correct. No other function should call the generate endpoint.

---

## 5. Tests

Add to `scripts/regen-task.test.mjs`. Framework: `node:test` + `assert/strict` (matching existing convention). Test naming: `condition_expectedOutcome`.

```javascript
// =============================================================================
// generateOneTask
// =============================================================================

describe('generateOneTask', () => {
  it('exported_isFunctionWithExpectedArity', () => {
    assert.strictEqual(typeof generateOneTask, 'function');
    // (pidProjectId, task, ctx, opts) = 4 params
    assert.strictEqual(generateOneTask.length, 4);
  });

  it('noOtherFunction_callsGenerateEndpoint', () => {
    // Structural test: only generateOneTask should call the /api/ai/text/generate endpoint.
    // This pins the adapter boundary — orchestration code goes through generateOneTask,
    // never calls curl to the generate endpoint directly.
    const fs = await import('node:fs');
    const source = fs.readFileSync(new URL('./regen-task.mjs', import.meta.url), 'utf8');

    // Find all occurrences of the generate endpoint URL
    const generateEndpointPattern = /api\/ai\/text\/generate/g;
    const matches = [...source.matchAll(generateEndpointPattern)];

    // Should appear exactly once (inside generateOneTask's curl call)
    assert.strictEqual(matches.length, 1,
      `Expected exactly 1 reference to api/ai/text/generate (inside generateOneTask), found ${matches.length}. ` +
      'If the single-task path has its own curl call, the extraction is incomplete.'
    );
  });

  it('returnType_includesTaskName', () => {
    // Structural test: verify the return statements in generateOneTask include taskName.
    // This catches regressions where someone adds a return path without taskName.
    const fs = await import('node:fs');
    const source = fs.readFileSync(new URL('./regen-task.mjs', import.meta.url), 'utf8');

    // Extract the generateOneTask function body (from "async function generateOneTask" to its closing brace)
    const fnStart = source.indexOf('async function generateOneTask');
    assert.ok(fnStart >= 0, 'generateOneTask function not found in source');

    // Find the function body by counting braces
    let braceCount = 0;
    let fnEnd = -1;
    let started = false;
    for (let i = fnStart; i < source.length; i++) {
      if (source[i] === '{') { braceCount++; started = true; }
      if (source[i] === '}') { braceCount--; }
      if (started && braceCount === 0) { fnEnd = i + 1; break; }
    }
    assert.ok(fnEnd > fnStart, 'Could not find end of generateOneTask function');

    const fnBody = source.slice(fnStart, fnEnd);
    const returnStatements = fnBody.match(/return\s*\{[^}]+\}/g) || [];

    assert.ok(returnStatements.length >= 2,
      `Expected at least 2 return statements (success + failure), found ${returnStatements.length}`);

    for (const ret of returnStatements) {
      assert.ok(ret.includes('taskName'),
        `Return statement missing taskName: ${ret.slice(0, 80)}...`);
    }
  });
});
```

**Import update** — add `generateOneTask` to the import at the top of the test file:

```javascript
import {
  extractTasksFromEpic,
  groupTasksIntoWaves,
  runWithConcurrency,
  parseArgs,
  formatElapsed,
  generateOneTask,    // ← add this
} from './regen-task.mjs';
```

**Note**: The `noOtherFunction_callsGenerateEndpoint` and `returnType_includesTaskName` tests use `await import('node:fs')` because the `describe` callback in `node:test` supports async. If the test runner does not support top-level `await` in `it` blocks, change the two structural tests to use `fs.readFileSync` synchronously (imported at the top of the file).

---

## 6. Commit Plan

One commit per logical unit:

1. `refactor(regen-task): add taskName to generateOneTask return type` — `scripts/regen-task.mjs`: add `taskName: task.name` to both success and failure return statements (2-line change)
2. `refactor(regen-task): single-task path calls generateOneTask` — `scripts/regen-task.mjs`: replace inline generation logic (lines 694–747) with `generateOneTask()` call; keep rescan, input reporting, size comparison, and preview as wrapper code in `main()`
3. `test(regen-task): add generateOneTask export, adapter boundary, and return shape tests` — `scripts/regen-task.test.mjs`: three new tests in `generateOneTask` describe block

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/regen-task.test.mjs
```

**Expected delta**: 28 → 31 passing. Zero pre-existing tests broken.

Additionally, a manual smoke test (not automated):
```bash
# Requires running API server: npm run api (or AI_PROVIDER=mock npm run api)
node scripts/regen-task.mjs <existing-project-id> <task-num> --no-review
# Verify: file written, output includes "✓ Wrote", size comparison shown, first 30 lines shown
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
  - Commit 1 (taskName): safe to revert — no downstream dependency within this task
  - Commit 2 (refactor single-task path): reverting restores the inline duplication. All functionality preserved
  - Commit 3 (tests): safe to revert — no production code affected
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch

---

## 9. Deviations Allowed

- **Line numbers shifted** → the guide cites lines based on the current file snapshot. If prior commits shifted lines, match by content pattern (`const prompt = buildImplementationGuidePrompt`, `const payloadFile`, `text.indexOf('# ')`) rather than line number. Log line-number corrections in commit body.
- **`fs.readFileSync` vs `await import('node:fs')`** → if the test runner's `it()` callback doesn't support `await import()`, use `import fs from 'node:fs'` at the top of the test file. Note in commit body.
- **Single-task diagnostic output differs slightly** → `generateOneTask` logs `task-N generating... (prompt X chars)` and `task-N done (Xs, Y chars)`. The old single-task path logged `── Prompt assembled: X chars ──` and `← Done in Xs (server latency Xms)`. The new output is acceptable — the file content is identical. Note in commit body if anyone asks about the log format change.
- **`finalText` read-back for preview** → the refactored path reads the output file back from disk for the size comparison and preview. This is one extra `readFile` call. Acceptable cost for clean separation. If this feels wasteful, an alternative is to have `generateOneTask` return the text content in the result object — take that simplification if obvious, log deviation.

---

## 10. Out of Scope

This task completes the extraction of generation logic into `generateOneTask()`. It does NOT add concurrency, wave ordering, retry, or progress reporting — those are Tasks 3–7. The batch orchestrator in parallel/all mode already calls `generateOneTask` and is not modified here.

- **Concurrency support** — deferred to Task 4 (`--parallel N` flag); `generateOneTask` is already concurrency-safe (no shared mutable state)
- **Wave grouping** — deferred to Task 3; `groupTasksIntoWaves` already exists and is tested
- **Integration tests with `AI_PROVIDER=mock`** — deferred to Task 8; this task adds only structural/unit tests
- **Removing duplicate context-block helpers** — `getBuilderBlock`, `getPrinciplesBlock`, etc. are defined in both `regen-task.mjs` and `context-loader.mjs`. Consolidation is a separate cleanup task, not in scope here
- **Returning generated text in result object** — the architecture spec doesn't include `text` in the return type. If a future task needs the content without re-reading the file, add it then

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)