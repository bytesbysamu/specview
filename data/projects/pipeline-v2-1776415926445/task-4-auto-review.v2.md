Now I have everything I need. Let me produce the implementation guide.

# 🛠️ Task 4: Auto-Review

**Purpose**: Append an advisory quality review to every generated task spec before file write, using the existing `/api/ai/text/review` endpoint with the project's architecture and principles as rubric context. This closes the feedback loop between generation and quality without blocking the pipeline.

**Effort**: 1 day

**Dependencies**: None (parallel with Tasks 1–3; operates on the post-LLM text regardless of whether preamble strip has shipped)

**Parallel With**: Tasks 1, 2, 3, 5

**Blocks**: Task 5 (Deviation-Count Parser) benefits from review-absorption deviations; no hard block

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 4 adds a post-generation review stage to `scripts/regen-task.mjs`. After the LLM generates a task spec via `POST /api/ai/text/generate`, the script pipes the output through the existing `POST /api/ai/text/review` endpoint (`server.js:1013`), formats the JSON review response as a `## Post-generation Review` markdown section, and appends it to the spec text before writing the file. The review is advisory — low scores produce a visible section but never block the write. This directly targets the "judgment-calls-per-commit" metric: session data showed advisory review alone dropped deviations from 6.0 to 3.0 per task, because executors read the appended findings and self-correct.

**Trade-offs considered**:
- **Blocking gate (fail on low score)** — rejected because there is no empirical threshold yet. A blocking gate with an arbitrary cutoff would stall the pipeline for false positives. If advisory proves insufficient, Task 5's deviation parser will detect the quality regression, and a threshold can be calibrated from real data.
- **Separate review step as a standalone script** — rejected because it would require the operator to run two commands per generation. Inline review in `regen-task.mjs` is zero-friction and matches the architecture's flow: `[LLM] → [Strip] → [Review] → [Write]`.
- **Inline review in `regen-task.mjs` (chosen)** — preferred because it's automatic, advisory, and adds one HTTP call (~30s) to an already 1–5 min pipeline. The review endpoint already exists and returns structured JSON. Formatting is pure string manipulation, easily testable.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                          # Flag any unrelated M/?? entries
git diff HEAD -- scripts/regen-task.mjs             # Confirm target file is clean
node --test server.test.js                          # Record pass count (expect 88 passing)
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: 88/88 passing (`server.test.js`). No existing `scripts/regen-task.test.mjs`.

---

## 3. Files

### To Create (new)
- `scripts/regen-task.test.mjs` **(new)** — Unit tests for `formatReviewSection()` and `reviewSpec()` covering: well-formed review JSON, malformed/non-JSON review response, missing dimensions, review endpoint failure (HTTP error), and the `--no-review` skip flag. Uses `node:test` + `node:assert/strict` to match `server.test.js` conventions.

### To Modify (cite CODEBASE CONTEXT)
- `scripts/regen-task.mjs` — Current state: `main()` receives LLM text at line 392 and writes it at line 400 with no intermediate processing. Target state: add `reviewSpec()` function that calls `/api/ai/text/review` via `curl` (matching the existing pattern at line 379–386), add `formatReviewSection()` pure function that turns the review JSON into a markdown section, call both between line 395 and line 398, accept `--no-review` CLI flag to skip, export `formatReviewSection` for testing.

### To Leave Alone
- `server.js` — The `/api/ai/text/review` endpoint (line 1013–1105) already exists and works. This task is a consumer, not a modifier.
- `server.test.js` — Existing 88 tests unchanged. New tests go in `scripts/regen-task.test.mjs`.
- `server.integration.test.js` — Integration tests already cover the review endpoint (line 389–411). No changes needed.

---

## 4. Implementation Steps

### Step 1: Add `--no-review` flag parsing

**Action**: Modify the CLI argument parsing at the top of `main()` to detect `--no-review` anywhere in `process.argv`. This lets operators skip the review step when iterating quickly.

**File**: `scripts/regen-task.mjs` (line 15, existing)

**Pattern**:
```javascript
const noReview = process.argv.includes('--no-review');
// Place after line 15 (const [, , projectId, taskNumArg] = process.argv;)
```

**Verify**: `node scripts/regen-task.mjs --help` (visual — script exits with usage if missing positional args, confirms no parse crash from the new flag)

### Step 2: Add `formatReviewSection()` pure function

**Action**: Add an exported function that takes a parsed review object (the shape returned by `/api/ai/text/review` — see `server.js:1073–1084`) and returns the markdown section string. This is a pure function with no side effects, making it trivially testable.

**File**: `scripts/regen-task.mjs` (after `getPriorTasksBlock` at line 64, before `loadPriorTasksSummary`)

**Pattern**:
```javascript
/**
 * Format a review JSON response as a markdown section to append to generated specs.
 * @param {object} review - Parsed review JSON from /api/ai/text/review
 * @returns {string} Markdown section starting with horizontal rule + ## heading
 */
export function formatReviewSection(review) {
  // Handle non-object review (raw text fallback from server)
  if (!review || typeof review !== 'object' || !review.dimensions) {
    const raw = typeof review === 'string' ? review : JSON.stringify(review);
    return `\n\n---\n\n## Post-generation Review\n\n_Review returned non-structured output:_\n\n${raw}\n`;
  }

  const { dimensions, overall_score, level, top_3_fixes } = review;

  const dimensionNames = {
    structural_completeness: 'Structural completeness',
    content_routing: 'Content routing',
    pattern_application: 'Pattern application',
    rule_compliance: 'Rule compliance',
    content_quality: 'Content quality',
    usefulness: 'Usefulness',
  };

  const rows = Object.entries(dimensionNames).map(([key, label]) => {
    const dim = dimensions[key];
    if (!dim) return `| ${label} | —/5 | _not scored_ |`;
    const finding = dim.issues?.[0] || dim.violations?.[0] || dim.missing?.[0] || dim.feedback?.[0] || dim.gaps?.[0] || 'Pass';
    return `| ${label} | ${dim.score}/5 | ${finding} |`;
  });

  const fixesList = (top_3_fixes || []).map((f) => `- ${f}`).join('\n');

  return `\n\n---\n\n## Post-generation Review\n\n**Overall**: ${overall_score ?? '?'}/5 (${level ?? 'unknown'})\n\n| Dimension | Score | Key Finding |\n|-----------|-------|-------------|\n${rows.join('\n')}\n\n**Top fixes**:\n${fixesList || '- (none)'}\n`;
}
```

**Verify**: `node -e "import('./scripts/regen-task.mjs')"` — expect no syntax errors (ESM dynamic import smoke test)

### Step 3: Add `reviewSpec()` async function

**Action**: Add a function that calls the review endpoint via `curl` (same pattern as the generate call at line 379–386), parses the response, and returns the formatted markdown section. On failure (network error, non-200, parse error), it returns a fallback section noting the failure rather than crashing the pipeline.

**File**: `scripts/regen-task.mjs` (after `formatReviewSection`, before `loadPriorTasksSummary`)

**Pattern**:
```javascript
async function reviewSpec(specText, archContent, principles) {
  const reviewPayload = {
    documents: {
      'task-spec': specText,
    },
  };

  // Include architecture and principles as additional rubric context if available
  if (archContent) reviewPayload.documents['architecture'] = archContent;
  if (principles) reviewPayload.documents['principles'] = principles;

  const payloadFile = `/tmp/regen-review-${Date.now()}.json`;
  await fs.writeFile(payloadFile, JSON.stringify(reviewPayload));

  try {
    const raw = execSync(
      `curl -sS -X POST ${API_BASE}/api/ai/text/review -H 'Content-Type: application/json' --data-binary @${payloadFile} --max-time 300`,
      { maxBuffer: 10 * 1024 * 1024, timeout: 310_000 },
    ).toString();

    const parsed = JSON.parse(raw);
    if (parsed.error) {
      console.log(`  ⚠️  Review endpoint returned error: ${parsed.error}`);
      return formatReviewSection(`Error: ${parsed.error}`);
    }

    return { section: formatReviewSection(parsed.review), latencyMs: parsed.latencyMs };
  } catch (err) {
    console.log(`  ⚠️  Review call failed (non-blocking): ${err.message}`);
    return { section: formatReviewSection(`Review unavailable: ${err.message}`), latencyMs: 0 };
  } finally {
    // Clean up temp file
    fs.unlink(payloadFile).catch(() => {});
  }
}
```

**Verify**: Read the function — confirm it uses `curl` (matching line 379 pattern), catches errors (advisory, not blocking), cleans up temp file.

### Step 4: Wire review into `main()` between LLM response and file write

**Action**: In `main()`, between receiving the LLM text (line 392–395) and writing the file (line 398–401), add the review call. Pass `archContent` and `principles` from the already-loaded context variables. Respect the `--no-review` flag. Log timing.

**File**: `scripts/regen-task.mjs` (in `main()`, after line 395 `console.log` for output size, before line 398 slug computation)

**Pattern**:
```javascript
  // 6b. Auto-review (advisory)
  let reviewSection = '';
  if (noReview) {
    console.log('  ⏭️  Review skipped (--no-review)');
  } else {
    console.log(`→ POST ${API_BASE}/api/ai/text/review (advisory, ~30s)…`);
    const r0 = Date.now();
    const reviewResult = await reviewSpec(text, archContent, principles);
    reviewSection = reviewResult.section;
    const reviewElapsed = Date.now() - r0;
    console.log(`← Review done in ${(reviewElapsed / 1000).toFixed(1)}s (server latency ${reviewResult.latencyMs}ms)`);
  }

  const finalText = text + reviewSection;
```

Then change the file write on line 400 to use `finalText` instead of `text`:

```javascript
  await fs.writeFile(outPath, finalText, 'utf8');
```

And update the size comparison (line 411) to use `finalText.length` and `finalText.split('\n').length` and the "First 30 lines" preview to reference `finalText`.

**Verify**: `grep -n 'finalText' scripts/regen-task.mjs` — expect hits on the write line and size comparison lines.

### Step 5: Update inputs report

**Action**: Add a line to the inputs report (after line 360) showing review status.

**File**: `scripts/regen-task.mjs` (in `main()`, after priorTasks report line)

**Pattern**:
```javascript
  console.log(`  auto-review:   ${noReview ? 'disabled (--no-review)' : 'enabled'}`);
```

**Verify**: Visual — consistent with the existing report format at lines 349–360.

### Step 6: Write tests

**Action**: Create `scripts/regen-task.test.mjs` with unit tests for `formatReviewSection()`. Tests cover: well-formed review JSON, non-object fallback, missing dimensions, null/undefined review, empty top_3_fixes. Test framework: `node:test` + `node:assert/strict` (matches `server.test.js` convention).

**File**: `scripts/regen-task.test.mjs` **(new)**

**Pattern**: See Section 5 below for complete test bodies.

**Verify**: `node --test scripts/regen-task.test.mjs` — expect 6/6 passing.

---

## 5. Tests

```javascript
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { formatReviewSection } from './regen-task.mjs';

describe('formatReviewSection', () => {
  it('wellFormedReview_returnsMarkdownTableWithScores', () => {
    const review = {
      dimensions: {
        structural_completeness: { score: 4, issues: ['Missing out-of-scope section'] },
        content_routing: { score: 5, violations: [] },
        pattern_application: { score: 4, missing: ['Execution flow diagram'] },
        rule_compliance: { score: 5, violations: [] },
        content_quality: { score: 3, feedback: ['Business value is thin'] },
        usefulness: { score: 4, gaps: ['Implementation guides would help'] },
      },
      overall_score: 4,
      level: 'silver',
      top_3_fixes: ['Add out-of-scope', 'Expand business value', 'Add flow diagram'],
    };

    const result = formatReviewSection(review);

    assert.ok(result.includes('## Post-generation Review'), 'should contain review heading');
    assert.ok(result.includes('**Overall**: 4/5 (silver)'), 'should show overall score and level');
    assert.ok(result.includes('| Structural completeness | 4/5 | Missing out-of-scope section |'), 'should format dimension row with top issue');
    assert.ok(result.includes('| Content routing | 5/5 | Pass |'), 'should show Pass when violations array is empty');
    assert.ok(result.includes('- Add out-of-scope'), 'should list top fixes as bullets');
    assert.ok(result.startsWith('\n\n---\n\n'), 'should start with horizontal rule separator');
  });

  it('nonObjectReview_returnsFallbackWithRawText', () => {
    const result = formatReviewSection('The AI returned plain text instead of JSON');

    assert.ok(result.includes('## Post-generation Review'), 'should still have heading');
    assert.ok(result.includes('non-structured output'), 'should flag it as non-structured');
    assert.ok(result.includes('The AI returned plain text instead of JSON'), 'should include the raw text');
  });

  it('nullReview_returnsFallbackSection', () => {
    const result = formatReviewSection(null);

    assert.ok(result.includes('## Post-generation Review'), 'should still have heading');
    assert.ok(result.includes('non-structured output'), 'should flag null as non-structured');
  });

  it('missingDimension_showsDashAndNotScored', () => {
    const review = {
      dimensions: {
        structural_completeness: { score: 4, issues: [] },
        // content_routing intentionally missing
        pattern_application: { score: 3, missing: [] },
        rule_compliance: { score: 5, violations: [] },
        content_quality: { score: 4, feedback: [] },
        usefulness: { score: 4, gaps: [] },
      },
      overall_score: 4,
      level: 'silver',
      top_3_fixes: [],
    };

    const result = formatReviewSection(review);

    assert.ok(result.includes('| Content routing | —/5 | _not scored_ |'), 'missing dimension shows dash score');
  });

  it('emptyTopFixes_showsNonePlaceholder', () => {
    const review = {
      dimensions: {
        structural_completeness: { score: 5, issues: [] },
        content_routing: { score: 5, violations: [] },
        pattern_application: { score: 5, missing: [] },
        rule_compliance: { score: 5, violations: [] },
        content_quality: { score: 5, feedback: [] },
        usefulness: { score: 5, gaps: [] },
      },
      overall_score: 5,
      level: 'gold',
      top_3_fixes: [],
    };

    const result = formatReviewSection(review);

    assert.ok(result.includes('- (none)'), 'empty fixes array should show (none) placeholder');
  });

  it('reviewWithoutOverallScore_showsQuestionMark', () => {
    const review = {
      dimensions: {
        structural_completeness: { score: 3, issues: ['Sparse'] },
        content_routing: { score: 3, violations: [] },
        pattern_application: { score: 3, missing: [] },
        rule_compliance: { score: 3, violations: [] },
        content_quality: { score: 3, feedback: [] },
        usefulness: { score: 3, gaps: [] },
      },
      // overall_score and level intentionally missing
      top_3_fixes: ['Fix something'],
    };

    const result = formatReviewSection(review);

    assert.ok(result.includes('**Overall**: ?/5 (unknown)'), 'missing overall_score should show ?');
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(task-4): add auto-review stage to regen-task pipeline` — `scripts/regen-task.mjs`: add `formatReviewSection()`, `reviewSpec()`, `--no-review` flag, wire into `main()` between LLM response and file write
2. `test(task-4): unit tests for formatReviewSection` — `scripts/regen-task.test.mjs`: 6 test cases covering well-formed, fallback, null, missing dimensions, empty fixes, missing overall score

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
node --test scripts/regen-task.test.mjs
```

**Expected delta**: 0 → 6 passing in `scripts/regen-task.test.mjs`. Zero pre-existing tests broken in `server.test.js` (run `node --test server.test.js` to confirm — expect 88/88 passing).

**Integration smoke test** (requires running server with `AI_PROVIDER=mock node server.js`):

```bash
node scripts/regen-task.mjs <projectId> <taskNum>
# Expect: review call logged, "Post-generation Review" section visible in output file
# Expect: --no-review skips it

node scripts/regen-task.mjs --no-review <projectId> <taskNum>
# Expect: "Review skipped (--no-review)" in console, no review section in output
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.
- **Safe to revert**: the review stage is purely additive (appends text to the generated spec). Reverting removes the appended section and the review HTTP call. No schema changes, no persistent state, no external side effects.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it, do not invent.
- **Task 1 (preamble strip) already shipped** → the review runs on stripped text. No change needed — the flow is `[LLM] → [strip if present] → [review] → [write]`. If `stripPreamble` exists in `regen-task.mjs`, the review receives already-clean text. If it doesn't exist yet, the review receives raw text. Both are correct.
- **Test framework mismatch** → match the repo's convention (`node:test` + `node:assert/strict`); translate silently but note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **Review endpoint response shape differs from mock** → use the `formatReviewSection` fallback path (non-object review). The function handles both structured JSON and raw text. Log a deviation noting the actual shape observed.
- **`scripts/regen-task.test.mjs` already exists** (created by Task 1 or Task 3) → append the `formatReviewSection` describe block to the existing file rather than overwriting. Log deviation.

---

## 10. Out of Scope

This task adds advisory review output. It does not add blocking behavior, scoring thresholds, or UI display of review results. The review endpoint (`server.js:1013–1105`) is consumed as-is — no modifications to the endpoint's prompt, scoring model, or response format.

- **Blocking gate (fail pipeline on low score)** — deferred until Task 5's deviation parser provides empirical data on what threshold would be meaningful. Revisit after 10+ tasks have shipped with advisory review.
- **Review of individual sections** (reviewing architecture separately from the task spec) — deferred; the review endpoint accepts a `documents` object and reviews all of them together. Section-level review is a prompt change, not a pipeline change.
- **Caching review results** — deferred; no persistence layer exists for pipeline metadata. When a second consumer needs review history (e.g., a dashboard), add a `pipeline_runs` table. Not before.
- **Modifying `server.js` review endpoint** — the endpoint works. Any prompt tuning is a separate task.
- **Frontend display of review scores** — no Angular changes in this epic. The review section is readable in the markdown file; no UI needed yet.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale (Task 4 component design)
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)