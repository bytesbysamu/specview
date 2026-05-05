Now I have all the context. Here's the implementation guide:

# 🛠️ Task 1: Preamble Strip

**Purpose**: Enforce the Executor Protocol rule that generated specs start with `#` by stripping LLM reasoning preamble from `regen-task.mjs` output before file write.

**Effort**: 0.5 day

**Dependencies**: None

**Parallel With**: Task 2 (Caveats Injection), Task 4 (Auto-Review)

**Blocks**: Task 4 reads from the stripped text, so the strip function should be a named export for Task 4 to call after its own append step if needed.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The LLM sometimes prefixes generated implementation guides with reasoning text like "I now have enough context..." or "Based on the analysis..." before the actual spec heading. The Executor Protocol (principles.md, section "Executor Protocol") requires the first character of the output to be `#`. Today, `regen-task.mjs` writes raw LLM output directly to disk (line 400), so preamble leaks into the file and the executor must manually strip it. This task adds a `stripPreamble()` function that drops everything before the first `# ` (H1 with space) line, applied between receiving the LLM response (line 392) and writing the file (line 400). When the output already starts with `#`, the function is a no-op. When the output has no `# ` heading at all (malformed), it logs a warning and returns the raw text unchanged.

**Trade-offs considered** (≤3 bullets):
- **Strip all content before any heading level (`##`, `###`)** — rejected because the Executor Protocol specifically mandates `#` (H1) as the first character; stripping to `##` would mask a deeper LLM formatting bug
- **Reject (fail with error) when no `#` heading found** — rejected because the architecture specifies "log a warning, write the raw output anyway, let the review stage flag it" — hard failure blocks the pipeline for a formatting quirk
- **Single regex on the full string, applied post-receive/pre-write** — preferred because it's a one-liner, zero dependencies, testable in isolation, and matches the architecture's "single regex" specification

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- scripts/regen-task.mjs       # Confirm target file is clean
node --test server.test.js                    # Record pass count — expect 88/88
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 88/88 passing (server.test.js).

---

## 3. Files

### To Create (new)
- `scripts/regen-task.test.mjs` — Unit tests for `stripPreamble()` covering: clean input (no-op), preamble before H1, multi-line preamble, no heading (warning path), heading without space (`#Title` — not stripped, only `# Title` counts)

### To Modify (cite CODEBASE CONTEXT)
- `scripts/regen-task.mjs` — Add `stripPreamble()` function (exported); call it on `text` between line 392 (receive) and line 400 (write); log character delta and warning if no heading found

### To Leave Alone
- `server.js` — No changes; preamble strip is script-side, not server-side
- `server.test.js` — Existing tests unchanged; new tests go in a separate file
- `server.integration.test.js` — Integration tests unchanged
- `src/app/services/implementation-guide.service.ts` — Angular frontend is not modified; this task is pipeline-only

---

## 4. Implementation Steps

### Step 1: Add `stripPreamble()` function to `regen-task.mjs`

**Action**: Add a named, exported function `stripPreamble(text)` after the existing helper functions (after `getPriorTasksBlock` at line 68) and before `loadPriorTasksSummary` (line 70).

**File**: `scripts/regen-task.mjs`

**Pattern**:
```javascript
/**
 * Strip LLM preamble: drop everything before the first line starting with "# ".
 * If no H1 heading found, log a warning and return the raw text unchanged.
 */
export function stripPreamble(text) {
  const match = text.match(/^# /m);
  if (!match) {
    console.warn('⚠️  No "# " heading found in LLM output — writing raw text (preamble strip skipped)');
    return text;
  }
  return text.slice(match.index);
}
```

The regex `^# /m` matches the first line that starts with `# ` (H1 with trailing space). `match.index` gives the character offset; `.slice()` drops everything before it. If the output already starts with `# `, `match.index` is 0 and the slice is a no-op.

**Verify**: `node -e "import('./scripts/regen-task.mjs')"` — expect no crash (module parses cleanly)

### Step 2: Wire `stripPreamble()` into the pipeline

**Action**: In `main()`, between the line that destructures `{ text, latencyMs }` (line 392) and the line that computes `slug` (line 398), apply `stripPreamble()` and log the delta.

**File**: `scripts/regen-task.mjs`

**Pattern**:
```javascript
  const { text: rawText, latencyMs } = parsed;
  const elapsed = Date.now() - t0;
  console.log(`← Done in ${(elapsed / 1000).toFixed(1)}s (server latency ${latencyMs}ms)`);
  console.log(`  Output: ${rawText.length} chars`);

  // 6b. Strip LLM preamble (Executor Protocol: first char must be #)
  const text = stripPreamble(rawText);
  if (text.length < rawText.length) {
    console.log(`  Preamble stripped: ${rawText.length - text.length} chars removed`);
  }
```

Note: the existing `const { text, latencyMs }` on line 392 becomes `const { text: rawText, latencyMs }` so that `text` can be reassigned to the stripped version. All downstream references to `text` (lines 395, 400, 410-411, 417) continue to work because `text` is now the stripped version.

**Verify**: Read the file and confirm `stripPreamble(rawText)` appears between the JSON parse and the file write.

### Step 3: Write unit tests

**Action**: Create `scripts/regen-task.test.mjs` with tests for `stripPreamble()`.

**File**: `scripts/regen-task.test.mjs` (new)

**Pattern**: See Section 5 (Tests) below for complete test bodies.

**Verify**: `node --test scripts/regen-task.test.mjs` — expect 6/6 passing

---

## 5. Tests

Test framework: `node:test` + `node:assert/strict` (matches `server.test.js` and `server.integration.test.js`).

```javascript
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { stripPreamble } from './regen-task.mjs';

describe('stripPreamble', () => {
  it('noOp_whenOutputAlreadyStartsWithH1', () => {
    const input = '# Task 3: Foo\n\nSome content here.';
    const result = stripPreamble(input);
    assert.equal(result, input, 'clean output should pass through unchanged');
  });

  it('stripsSingleLinePreamble', () => {
    const input = 'I now have enough context.\n\n# Task 3: Foo\n\nContent.';
    const result = stripPreamble(input);
    assert.equal(result, '# Task 3: Foo\n\nContent.',
      'should drop everything before first "# " line');
  });

  it('stripsMultiLinePreamble', () => {
    const input = 'Let me think about this.\nBased on the analysis...\nHere is my response:\n\n# 🛠️ Task 1: Setup\n\n## 1. Context\nDone.';
    const result = stripPreamble(input);
    assert.equal(result, '# 🛠️ Task 1: Setup\n\n## 1. Context\nDone.',
      'should handle multi-line preamble with emoji in heading');
  });

  it('returnsRawText_whenNoH1HeadingFound', () => {
    const input = 'This output has no heading at all.\nJust plain text.';
    const result = stripPreamble(input);
    assert.equal(result, input,
      'malformed output (no # heading) should be returned unchanged');
  });

  it('doesNotStripOnHashWithoutSpace', () => {
    const input = 'Preamble text.\n#NoSpace\n\n# Real Heading\nContent.';
    const result = stripPreamble(input);
    assert.equal(result, '# Real Heading\nContent.',
      'should only match "# " (with space), not "#" without space');
  });

  it('stripsToFirstH1_notH2OrH3', () => {
    const input = 'Preamble.\n\n## Section Two\n\n# Actual Title\nContent.';
    const result = stripPreamble(input);
    assert.equal(result, '# Actual Title\nContent.',
      'should strip to first H1, ignoring earlier H2/H3 lines');
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(pipeline): add preamble strip to regen-task.mjs` — `scripts/regen-task.mjs`: add `stripPreamble()` function and wire into `main()` between LLM response receive and file write
2. `test(pipeline): preamble strip unit tests` — `scripts/regen-task.test.mjs`: 6 test cases covering no-op, single-line, multi-line, no-heading, hash-without-space, H1-vs-H2

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/regen-task.test.mjs
node --test server.test.js
```

**Expected delta**: `scripts/regen-task.test.mjs` — 0 → 6 passing. `server.test.js` — 88 → 88 passing (no regressions). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in codebase; if still missing, flag it, do not invent.
- **`export` syntax causes runtime issue** → `regen-task.mjs` currently has no exports. If adding `export` to `stripPreamble` causes the script's `main()` to break when run directly, wrap the export in a named-export-only pattern or move `stripPreamble` to a separate `scripts/lib/strip-preamble.mjs` module. Log deviation in commit body.
- **Line numbers shifted** → the guide cites line 392, 398, 400 from the current file. If prior uncommitted changes shifted these, find the equivalent lines by searching for `const { text, latencyMs } = parsed;` and `await fs.writeFile(outPath, text`. Adapt silently but note in commit body.
- **Test framework mismatch** → match the repo's convention (`node:test` + `node:assert/strict`); translate silently but note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task adds a one-function preamble strip to the script-side pipeline only. It does not touch the server-side `generate-spec` endpoint, does not modify the LLM prompt to prevent preamble generation, does not add preamble stripping to the Angular frontend's bootstrap flow, and does not integrate with the review stage (Task 4).

- **Server-side preamble strip in `server.js`** — deferred; the architecture scopes preamble strip to `regen-task.mjs` only. If the generate-spec endpoint also needs it, that's a follow-up after Task 4 ships.
- **Prompt-level fix to prevent preamble** — deferred; the current prompt already says "first character is `#`" but LLMs sometimes ignore it. The regex is the belt-and-suspenders fix. Prompt iteration is a separate concern.
- **Integration with Task 4 (Auto-Review)** — Task 4 will call `stripPreamble` on its own output if needed. The export exists for that purpose but wiring is Task 4's responsibility.
- **Frontend preamble strip** — the Angular bootstrap flow (`new-project.component.ts`) is a separate code path; if it has the same problem, that's a separate task.
- **Caveats injection into `regen-task.mjs`** — that is Task 2; do not absorb it.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)