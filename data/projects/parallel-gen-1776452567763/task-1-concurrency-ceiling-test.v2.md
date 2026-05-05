# Task 1: Concurrency Ceiling Test

**Purpose**: Empirically determine the maximum safe number of concurrent `claude -p` calls against the Express server with the 600s timeout fix, informing the default `--parallel N` value for subsequent tasks.

**Effort**: 0.5 day

**Dependencies**: None

**Parallel With**: Task 2 (Extract Reusable Task Runner), Task 3 (Dependency-Aware Wave Grouper)

**Blocks**: Task 4 (`--parallel N` default value decision)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task creates a shell script that launches N instances of `regen-task.mjs` in parallel (using `&` + `wait`) at concurrency levels 3, 4, and 5, recording success/failure, wall-clock latency, and error type for each run. Each concurrency level is tested 3 times to account for variance. The script targets a real project with existing epic/architecture files and uses `--no-review` to isolate generation latency from review latency. Results are captured in a markdown report at `docs/concurrency-ceiling.md` with a structured table. This is a one-time empirical test — the script is a throwaway diagnostic, not a recurring gate. The report is the deliverable: it tells subsequent tasks what default to set for `--parallel N`.

**Trade-offs considered**:
- **Automated test harness with assertions** — rejected because the signal is empirical (latency distribution, error frequency under real API load), not binary pass/fail. Assertions would be arbitrary thresholds that don't teach us anything the raw numbers don't.
- **Testing against `AI_PROVIDER=mock`** — rejected because mock responses return instantly; the bottleneck being measured is real `claude -p` process spawning, Express request handling under concurrent load, and Anthropic API rate limits. Mock would measure nothing useful.
- **Chosen approach: shell script + manual invocation against a running server with real `claude -p`** — preferred because it directly measures the actual constraint (Claude CLI concurrency) with minimal tooling, and the markdown report is the permanent artifact.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- scripts/ docs/               # Confirm target directories are clean
node --test scripts/regen-task.test.mjs       # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: Record current passing test count from `scripts/regen-task.test.mjs`.

**Server prerequisite**: The Express server must be running with the real CLI provider (NOT mock):
```bash
npm run api                                   # Starts server.js on port 3100
```

**Project prerequisite**: Identify a project with a multi-task epic (at least 5 tasks). The `parallel-gen-1776452567763` project has the epic for this feature but may be too meta. Any project with `epic.md` + `architecture.md` + 5+ tasks works. The executor should pick one and record the project ID in the report.

---

## 3. Files

### To Create (new)
- `scripts/concurrency-ceiling-test.sh` (new) — Shell script that launches N parallel `regen-task.mjs` invocations and captures timing/status
- `docs/concurrency-ceiling.md` (new) — Markdown report documenting results; the permanent deliverable of this task

### To Modify (cite CODEBASE CONTEXT)
- None — this task creates new files only

### To Leave Alone
- `scripts/regen-task.mjs` — The script being tested; do not modify it during this task
- `server.js` — The Express server being tested; timeout config at lines 1615–1618 is the fix being validated
- `package.json` — No new npm scripts needed for a one-time diagnostic

---

## 4. Implementation Steps

### Step 1: Create the concurrency test script

**Action**: Write a bash script that accepts a project ID and concurrency level, launches N parallel `regen-task.mjs` processes targeting distinct tasks, waits for all to complete, and captures per-process exit code + wall-clock time.

**File**: `scripts/concurrency-ceiling-test.sh` (new)

**Pattern**:
```bash
#!/usr/bin/env bash
# Concurrency ceiling test for regen-task.mjs
# Usage: ./scripts/concurrency-ceiling-test.sh <projectId> <concurrency> <taskNums...>
#
# Example: ./scripts/concurrency-ceiling-test.sh parallel-gen-1776452567763 3 1 2 3
#
# Launches <concurrency> instances of regen-task.mjs in parallel,
# each targeting a different task number. Records wall-clock time,
# exit code, and any error output per process.

set -euo pipefail

PROJECT_ID="${1:?Usage: $0 <projectId> <concurrency> <taskNums...>}"
CONCURRENCY="${2:?Usage: $0 <projectId> <concurrency> <taskNums...>}"
shift 2
TASK_NUMS=("$@")

if [ "${#TASK_NUMS[@]}" -lt "$CONCURRENCY" ]; then
  echo "ERROR: Need at least $CONCURRENCY task numbers, got ${#TASK_NUMS[@]}"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="/tmp/concurrency-ceiling-$$"
mkdir -p "$RESULTS_DIR"

echo "=== Concurrency Ceiling Test ==="
echo "Project:     $PROJECT_ID"
echo "Concurrency: $CONCURRENCY"
echo "Tasks:       ${TASK_NUMS[*]:0:$CONCURRENCY}"
echo "Results dir: $RESULTS_DIR"
echo ""

PIDS=()
START_GLOBAL=$(date +%s)

for i in $(seq 0 $((CONCURRENCY - 1))); do
  TASK="${TASK_NUMS[$i]}"
  RESULT_FILE="$RESULTS_DIR/task-${TASK}.result"
  (
    START=$(date +%s%N)
    set +e
    OUTPUT=$(node "$SCRIPT_DIR/regen-task.mjs" "$PROJECT_ID" "$TASK" --no-review 2>&1)
    EXIT_CODE=$?
    set -e
    END=$(date +%s%N)
    ELAPSED_MS=$(( (END - START) / 1000000 ))

    # Extract error if failed
    ERROR_MSG=""
    if [ "$EXIT_CODE" -ne 0 ]; then
      ERROR_MSG=$(echo "$OUTPUT" | grep -i -m1 'error\|fail\|timeout' || echo "unknown error")
    fi

    echo "task=$TASK exit=$EXIT_CODE elapsed_ms=$ELAPSED_MS error=$ERROR_MSG" > "$RESULT_FILE"
    echo "  Task $TASK finished: exit=$EXIT_CODE elapsed=${ELAPSED_MS}ms"
  ) &
  PIDS+=($!)
done

echo "Waiting for $CONCURRENCY processes..."
echo ""

FAILURES=0
for pid in "${PIDS[@]}"; do
  wait "$pid" || ((FAILURES++))
done

END_GLOBAL=$(date +%s)
WALL_CLOCK=$((END_GLOBAL - START_GLOBAL))

echo ""
echo "=== Results (concurrency=$CONCURRENCY) ==="
echo "Wall clock: ${WALL_CLOCK}s"
echo "Failures:   $FAILURES / $CONCURRENCY"
echo ""

# Print per-task results
echo "| Task | Exit Code | Elapsed (s) | Error |"
echo "|------|-----------|-------------|-------|"
for i in $(seq 0 $((CONCURRENCY - 1))); do
  TASK="${TASK_NUMS[$i]}"
  RESULT_FILE="$RESULTS_DIR/task-${TASK}.result"
  if [ -f "$RESULT_FILE" ]; then
    source "$RESULT_FILE" 2>/dev/null || true
    # Re-parse from file content
    LINE=$(cat "$RESULT_FILE")
    T_EXIT=$(echo "$LINE" | sed 's/.*exit=\([0-9]*\).*/\1/')
    T_MS=$(echo "$LINE" | sed 's/.*elapsed_ms=\([0-9]*\).*/\1/')
    T_ERR=$(echo "$LINE" | sed 's/.*error=\(.*\)/\1/')
    T_SEC=$(echo "scale=1; $T_MS / 1000" | bc 2>/dev/null || echo "$((T_MS / 1000))")
    echo "| $TASK | $T_EXIT | ${T_SEC} | ${T_ERR:--} |"
  else
    echo "| $TASK | ? | ? | result file missing |"
  fi
done

echo ""
echo "Raw results: $RESULTS_DIR"
```

**Verify**: `chmod +x scripts/concurrency-ceiling-test.sh && bash -n scripts/concurrency-ceiling-test.sh` — expect no syntax errors.

### Step 2: Run the test at concurrency=3 (3 trials)

**Action**: With the Express server running (`npm run api`), execute the test script 3 times at concurrency 3. Choose a project with at least 5 tasks. Capture the table output from each run.

**File**: No file change — this is a manual execution step.

**Command** (repeat 3 times):
```bash
./scripts/concurrency-ceiling-test.sh <projectId> 3 <task1> <task2> <task3>
```

Record for each trial:
- Number of successes vs failures
- Per-task wall-clock time
- Any error messages (timeout, rate limit, connection refused)
- Total wall-clock time

**Verify**: At least 2 of 3 trials should have 3/3 successes (concurrency 3 is expected to be safe per architecture doc).

### Step 3: Run the test at concurrency=4 (3 trials)

**Action**: Same as Step 2 but with concurrency 4 and 4 distinct task numbers.

**Command** (repeat 3 times):
```bash
./scripts/concurrency-ceiling-test.sh <projectId> 4 <task1> <task2> <task3> <task4>
```

**Verify**: Record success rate. Note any degradation vs concurrency=3.

### Step 4: Run the test at concurrency=5 (3 trials)

**Action**: Same as Step 2 but with concurrency 5 and 5 distinct task numbers.

**Command** (repeat 3 times):
```bash
./scripts/concurrency-ceiling-test.sh <projectId> 5 <task1> <task2> <task3> <task4> <task5>
```

**Verify**: Record success rate. Note whether any failures are rate-limit errors (429/503 from Anthropic API) vs timeouts vs Express errors.

### Step 5: Write the concurrency ceiling report

**Action**: Create the markdown report documenting all 9 test runs (3 concurrency levels × 3 trials each). Include a summary table, per-trial detail tables, analysis of failure modes, and a recommendation for the default `--parallel N` value.

**File**: `docs/concurrency-ceiling.md` (new)

**Pattern**:
```markdown
# Concurrency Ceiling Test Report

**Date**: YYYY-MM-DD
**Server**: Express on port 3100, `server.requestTimeout = 600_000`
**AI Provider**: CLI (`claude -p`)
**Project used**: <projectId> (<N> tasks in epic)
**Flags**: `--no-review` (isolate generation latency)

---

## Summary

| Concurrency | Trial 1 | Trial 2 | Trial 3 | Success Rate | Avg Wall Clock |
|-------------|---------|---------|---------|--------------|----------------|
| 3           | N/N ✓   | N/N ✓   | N/N ✓   | X%           | Xs             |
| 4           | N/N ✓   | N/N ?   | N/N ?   | X%           | Xs             |
| 5           | N/N ?   | N/N ?   | N/N ?   | X%           | Xs             |

## Recommendation

Based on the results, the recommended default for `--parallel N` is **[3|4|5]**.

[1-2 sentences explaining why — e.g., "Concurrency 3 showed 100% success
across all trials with no rate limiting. Concurrency 4 showed intermittent
timeout failures in trial 2. Concurrency 5 showed consistent rate-limit
errors from the Anthropic API."]

---

## Detailed Results

### Concurrency = 3

#### Trial 1
| Task | Exit Code | Elapsed (s) | Error |
|------|-----------|-------------|-------|
| ...  | ...       | ...         | ...   |

Wall clock: Xs

#### Trial 2
[same table format]

#### Trial 3
[same table format]

### Concurrency = 4
[same structure]

### Concurrency = 5
[same structure]

---

## Failure Analysis

| Error Type | Occurrences | Concurrency Level | Notes |
|------------|-------------|-------------------|-------|
| Rate limit (429/503) | N | 4, 5 | Anthropic API throttling |
| Timeout (600s) | N | 5 | curl --max-time exceeded |
| Connection refused | N | — | Server overloaded |

---

## Environment

- Node.js: [version]
- Express timeout: 600s (request, headers, keepAlive)
- curl timeout: 600s (--max-time)
- Node child_process timeout: 620s
- Claude CLI version: [version]
```

**Verify**: The report must contain all 9 trial result tables and a concrete numeric recommendation for the default `--parallel N` value.

---

## 5. Tests

No automated tests for this task. The deliverable is an empirical report, not production code. The test script (`concurrency-ceiling-test.sh`) is a diagnostic tool, not a CI gate — it requires a running server with real `claude -p` calls and takes 15–30 minutes per full run. It would be actively harmful to add this to `test:all`.

The report itself is the test artifact. Verification is: does the report exist, does it contain data for all 9 trials, and does it state a recommendation.

```bash
# Verify report completeness (run after Step 5)
test -f docs/concurrency-ceiling.md && \
  grep -c "^| .* |" docs/concurrency-ceiling.md | \
  xargs -I{} test {} -ge 12 && \
  grep -q "Recommendation" docs/concurrency-ceiling.md && \
  echo "Report complete" || echo "Report incomplete"
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(scripts): add concurrency ceiling test script` — `scripts/concurrency-ceiling-test.sh`: shell script that launches N parallel regen-task.mjs invocations and captures timing/status per process
2. `docs: add concurrency ceiling test report` — `docs/concurrency-ceiling.md`: results from 9 test runs (3 concurrency levels × 3 trials), failure analysis, and recommended default for `--parallel N`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Script is syntactically valid
bash -n scripts/concurrency-ceiling-test.sh

# Report exists and has required sections
grep -q "## Summary" docs/concurrency-ceiling.md
grep -q "## Recommendation" docs/concurrency-ceiling.md
grep -q "## Detailed Results" docs/concurrency-ceiling.md
grep -q "## Failure Analysis" docs/concurrency-ceiling.md
```

**Expected delta**: 0 new automated tests (this is an empirical measurement task, not a code change). Zero pre-existing tests broken — nothing was modified.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`. Both commits add new files only — reverting deletes them cleanly.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch. No existing files were modified, so there's no risk of data loss beyond the new files.

---

## 9. Deviations Allowed

- **Fewer than 5 tasks in the chosen project** → pick a different project, or generate placeholder tasks first. Document which project was used in the report header.
- **Rate limiting kicks in at concurrency=3** → record the result honestly; the recommendation becomes "2 or serial." Do not hide failures to force a higher number.
- **`date +%s%N` not available on macOS** → use `gdate` (from `coreutils`) or fall back to `date +%s` with second-level precision. Note the precision change in the report.
- **Server crashes under load** → this IS the finding. Document the crash, its error output, and the concurrency level. The recommendation is one level below the crash threshold.
- **A task generates successfully but the output is garbage** → count as success for concurrency testing purposes (the test measures transport reliability, not output quality). Note if output quality degrades at higher concurrency.
- **Trial variance is extreme** (e.g., trial 1 passes, trial 2 all fail at same concurrency) → run 2 additional trials at that concurrency level to get more signal. Note the extra trials in the report.

---

## 10. Out of Scope

This task produces a diagnostic script and a report. It does not modify any production code, add any automated tests to CI, or change any default values in `regen-task.mjs`. The report's recommendation is consumed by Task 4 (`--parallel N` flag implementation) when setting the default value — that's where the recommendation turns into code.

- **Modifying `regen-task.mjs`'s `--parallel` default** — deferred to Task 4; this task only informs the decision
- **Server-side rate limiting or concurrency controls** — explicitly out of scope per epic ("No server-side changes")
- **Testing against `AI_PROVIDER=mock`** — useless for measuring real concurrency constraints; mock returns instantly
- **Automated CI gate for concurrency** — the ceiling is environment-dependent (Anthropic API tier, machine resources); a hard-coded CI assertion would be fragile and misleading
- **Testing concurrency > 5** — architecture doc caps investigation at 5; if 5 is safe, 5 is the ceiling for this epic. Further testing is a separate decision after shipping `--parallel`

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, Task 1 component design
- [Epic](./epic.md) – Task scope and dependency graph
- [Timeline](./timeline.md) – Status tracking (update after done)