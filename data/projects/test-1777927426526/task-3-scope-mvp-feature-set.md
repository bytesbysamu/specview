# Implementation Guide — Task 3: Scope MVP Feature Set

**Purpose**: Produce the MVP feature set document that replaces the placeholder scope table in `epic.md`, enumerating exactly 3–5 shippable features tied to confirmed success criteria and explicitly listing all deferred work.

**Effort**: 1 day

**Dependencies**: Task 1 (real problem statement in `analysis.md`) and Task 2 (success criteria written into `epic.md`) must be complete and merged before this task begins.

**Parallel With**: —

**Blocks**: Architecture Revision 1 (the architecture doc is explicitly gated on this task's output per the execution flow diagram in `architecture.md`)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 3 converts the problem statement and success criteria produced by Tasks 1–2 into the smallest possible list of shippable features — the MVP scope. Without this output, the architecture document cannot be revised from its current placeholder shell, and no engineering work can begin responsibly. The executor reads the existing source documents, extracts confirmed criteria, maps each candidate feature against those criteria, scores them, selects 3–5, and writes both a standalone `mvp-scope.md` and the replacement scope table in `epic.md`. Every feature in the MVP must be traceable to at least one success criterion; every feature that does not clear that bar is placed in the deferred list.

**Trade-offs considered** (≤3 bullets):
- **Produce scope as a separate `mvp-scope.md` file only** — rejected because `epic.md` contains a placeholder table that downstream readers (architecture, timeline) already reference; leaving the placeholder intact creates a stale cross-reference.
- **Inline all scope detail directly into `epic.md`** — rejected because the feature-by-criterion mapping matrix and deferral rationale would bloat `epic.md` beyond its role as a summary document.
- **Separate `mvp-scope.md` + minimal replacement table in `epic.md`** — preferred because detail lives in the dedicated file while cross-references in `epic.md`, `architecture.md`, and `timeline.md` remain valid and concise.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- docs/epic.md docs/analysis.md docs/architecture.md
# Confirm those three files are clean before editing

# Verify Task 1 output exists
grep -c "Problem Statement" docs/analysis.md   # Must return ≥ 1

# Verify Task 2 output exists
grep -c "Success Criteria" docs/epic.md        # Must return ≥ 1

# Baseline: count existing doc files
ls docs/*.md | wc -l                          # Record N; expect N+1 after Step 1
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**If `grep` checks return 0**: Task 1 or Task 2 is incomplete. STOP. Do not proceed — this task's inputs are missing. Flag the blocker.

**Baseline recorded**: `ls docs/*.md | wc -l` = **N** files.

---

## 3. Files

### To Create (new)
- `docs/mvp-scope.md` (new) — canonical MVP feature set document; contains the feature-by-criterion mapping matrix, feature descriptions, and the full deferral list. Depends on content read from `docs/analysis.md` and `docs/epic.md`.

### To Modify (cite CODEBASE CONTEXT)
- `docs/epic.md` — current state: contains a placeholder scope table with the comment "This task produces the replacement for the placeholder scope table above." Target state: placeholder table replaced with a concise 3–5 row feature summary table, each row linking to the relevant section in `docs/mvp-scope.md`.
- `docs/timeline.md` — current state: Task 3 row has status "pending" or equivalent. Target state: status updated to "complete" with today's date (2026-05-04).

### To Leave Alone
- `docs/analysis.md` — Task 1 output; read-only input to this task. Any edits belong to Task 1's scope.
- `docs/architecture.md` — currently a placeholder shell by design; it is gated on *this task's output*, not the reverse. Do not pre-fill it here.
- `docs/spec-index.md` — document registry; updated only when a net-new document is added to the repo (Step 6 handles the one addition this task makes).

---

## 4. Implementation Steps

---

### Step 1: Read and extract inputs

**Action**: Read `docs/analysis.md` in full and `docs/epic.md` in full. Extract: (a) the confirmed problem statement (one sentence), (b) every stated success criterion (verbatim, numbered list), and (c) any candidate features already mentioned. Write these extractions to a scratch block — you will reference them in every subsequent step. Do NOT edit any file in this step.

**File**: `docs/analysis.md`, `docs/epic.md` — read-only

**Pattern** (extraction schema you must populate before Step 2):
```
PROBLEM_STATEMENT: "<verbatim one-sentence statement from analysis.md>"

SUCCESS_CRITERIA:
  SC-1: "<verbatim criterion>"
  SC-2: "<verbatim criterion>"
  SC-N: "<verbatim criterion>"

CANDIDATE_FEATURES_MENTIONED (if any):
  - "<feature name if mentioned>" → mentioned in <file>:<section>
```

**Verify**:
```bash
grep -n "Success Criteria" docs/epic.md      # Line number of criteria section
grep -n "Problem Statement" docs/analysis.md # Line number of problem statement
```
Expect: both greps return ≥ 1 result. If either returns 0, STOP — prerequisite tasks are incomplete.

---

### Step 2: Generate and score candidate features

**Action**: Using the extracted success criteria as the scoring rubric, enumerate ALL candidate features that could plausibly address the problem. For each candidate, score it against each success criterion (Y / Partial / N). A feature qualifies for the MVP if it scores Y or Partial against at least one success criterion AND no other already-included feature fully covers that criterion. Features scoring N against all criteria are deferred.

**File**: scratch (no file edits yet)

**Pattern** (mapping matrix to complete before writing any file):
```
| Feature Candidate         | SC-1 | SC-2 | SC-N | MVP? | Rationale              |
|---------------------------|------|------|------|------|------------------------|
| <Feature A>               |  Y   |  N   |  Y   | YES  | Covers SC-1 and SC-N   |
| <Feature B>               |  N   |  Y   |  N   | YES  | Only path to SC-2      |
| <Feature C>               |  N   |  N   |  N   | NO   | Covers no criterion    |
| <Feature D>               |  Y   |  N   |  N   | NO   | SC-1 already covered   |
```

**Constraint**: Final MVP count must be ≥ 3 and ≤ 5. If your matrix produces fewer than 3 "YES" rows, revisit criterion coverage — you may have scored too conservatively. If it produces more than 5 "YES" rows, apply the tiebreaker: prefer the feature with the lowest estimated implementation effort that covers the most uncovered criteria.

**Verify**: Count "YES" rows in your matrix. Expect: 3 ≤ count ≤ 5. If outside range, re-score before proceeding.

---

### Step 3: Write `docs/mvp-scope.md`

**Action**: Create `docs/mvp-scope.md` (new file) using the completed matrix and extracted inputs from Steps 1–2. The file must contain every section shown in the pattern below — no stubs.

**File**: `docs/mvp-scope.md` (new)

**Pattern**:
```markdown
# MVP Feature Set

**Status**: Draft  
**Date**: 2026-05-04  
**Author**: Task 3 executor  
**References**: [Epic](./epic.md) · [Analysis](./analysis.md)

---

## Problem Statement

<one sentence verbatim from analysis.md>

---

## Success Criteria

| ID   | Criterion                        |
|------|----------------------------------|
| SC-1 | <verbatim from epic.md>          |
| SC-2 | <verbatim from epic.md>          |
| SC-N | <verbatim from epic.md>          |

---

## MVP Feature Set (v1)

| # | Feature            | Description (≤2 sentences)    | Covers  | Est. Effort |
|---|--------------------|-------------------------------|---------|-------------|
| 1 | <Feature Name>     | <description>                 | SC-1    | <S/M/L>     |
| 2 | <Feature Name>     | <description>                 | SC-2    | <S/M/L>     |
| … | …                  | …                             | …       | …           |

**Total features**: N (where 3 ≤ N ≤ 5)

### Feature Detail

#### F-1: <Feature Name>
**What it does**: <one paragraph>  
**Why MVP**: Maps to SC-<N> — without this feature, criterion SC-<N> cannot be satisfied.  
**Acceptance condition**: <one concrete, testable statement>  
**Deferred sub-features**: <list anything cut from this feature, or "none">

#### F-2: <Feature Name>
[same structure]

…

---

## Deferred Work

Features below were considered and explicitly excluded from MVP. They must not be absorbed into this scope.

| Feature          | Considered Because         | Deferred Because                        | Revisit When             |
|------------------|----------------------------|-----------------------------------------|--------------------------|
| <Feature C>      | <why it was considered>    | Covers no stated success criterion      | Success criteria expand  |
| <Feature D>      | <why it was considered>    | SC-1 already covered by F-1; redundant | Post-MVP iteration       |
| …                | …                          | …                                       | …                        |

---

## Scoping Constraints Applied

- Features were bounded to direct satisfaction of stated success criteria only.
- No feature was included on the basis of anticipated scope.
- Every deferred feature has an explicit reason and revisit trigger.

---

## Related Documents

- [Epic](./epic.md) – Scope summary
- [Analysis](./analysis.md) – Problem and success criteria source
- [Architecture](./architecture.md) – Will be revised once this document is finalized
- [Timeline](./timeline.md) – Status tracking
```

**Verify**:
```bash
ls docs/mvp-scope.md                          # File exists
grep -c "^#### F-" docs/mvp-scope.md          # Count feature detail sections; expect 3–5
grep -c "^| " docs/mvp-scope.md               # Count table rows; expect ≥ 10
wc -l docs/mvp-scope.md                       # Expect ≥ 60 lines (no stubs)
```

---

### Step 4: Replace the placeholder scope table in `epic.md`

**Action**: Locate the placeholder scope table in `docs/epic.md` (the one the task description calls out: "This task produces the replacement for the placeholder scope table above"). Replace it — and the surrounding placeholder commentary — with the compact replacement block shown in the pattern. Do NOT alter any other section of `epic.md`.

**File**: `docs/epic.md` — targeted replacement only

**Pattern** (replacement block):
```markdown
## MVP Scope

> Full feature detail, criterion mapping, and deferral rationale: **[mvp-scope.md](./mvp-scope.md)**

| # | Feature        | Covers  | Status   |
|---|----------------|---------|----------|
| 1 | <Feature Name> | SC-1    | Scoped   |
| 2 | <Feature Name> | SC-2    | Scoped   |
| … | …              | …       | Scoped   |

**Deferred features**: <count> — see [mvp-scope.md § Deferred Work](./mvp-scope.md#deferred-work)
```

**Verify**:
```bash
grep -n "placeholder" docs/epic.md            # Expect 0 results (placeholder removed)
grep -n "mvp-scope.md" docs/epic.md           # Expect ≥ 2 results (link present)
grep -c "^| " docs/epic.md                    # Expect table rows present
```

---

### Step 5: Update `timeline.md` task status

**Action**: In `docs/timeline.md`, find the row for Task 3. Update its status from whatever "pending/in-progress" value it currently holds to `Complete` and set the date column to `2026-05-04`. Change only that row.

**File**: `docs/timeline.md` — one row update

**Pattern**:
```markdown
| Task 3 | Scope MVP Feature Set | Complete | 2026-05-04 | — |
```
(Adapt column count/order to match the existing table structure in `timeline.md`.)

**Verify**:
```bash
grep "Task 3" docs/timeline.md                # Expect the row shows "Complete" and "2026-05-04"
grep -c "Complete" docs/timeline.md           # Expect count increased by 1 vs baseline
```

---

### Step 6: Register `mvp-scope.md` in `spec-index.md`

**Action**: Open `docs/spec-index.md`. Add one row for `mvp-scope.md` to the document registry table, following the existing format for other entries. Do NOT reorder or reformat existing rows.

**File**: `docs/spec-index.md` — append one row to existing table

**Pattern** (adapt column order to match existing rows):
```markdown
| [MVP Scope](./mvp-scope.md) | Canonical MVP feature set and deferral list | Task 3 | 2026-05-04 |
```

**Verify**:
```bash
grep "mvp-scope.md" docs/spec-index.md        # Expect exactly 1 result
```

---

## 5. Tests

These are shell-based structural assertions. Run all of them after Step 6 completes. Each must exit 0. No stubs — every check has a complete assertion body.

```bash
#!/usr/bin/env bash
# File: docs/tests/test_mvp_scope_structure.sh  (new — place alongside other doc tests if they exist, otherwise create)
set -euo pipefail
PASS=0; FAIL=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    echo "PASS: $label"
    PASS=$((PASS+1))
  else
    echo "FAIL: $label (expected $expected, got $actual)"
    FAIL=$((FAIL+1))
  fi
}

assert_gte() {
  local label="$1" min="$2" actual="$3"
  if [ "$actual" -ge "$min" ]; then
    echo "PASS: $label"
    PASS=$((PASS+1))
  else
    echo "FAIL: $label (expected >= $min, got $actual)"
    FAIL=$((FAIL+1))
  fi
}

# T1: mvp-scope.md exists
[ -f docs/mvp-scope.md ] && { echo "PASS: T1 mvp-scope.md exists"; PASS=$((PASS+1)); } \
  || { echo "FAIL: T1 mvp-scope.md missing"; FAIL=$((FAIL+1)); }

# T2: MVP feature count is 3–5
FEATURE_COUNT=$(grep -c "^#### F-" docs/mvp-scope.md)
assert_gte "T2a feature count >= 3" 3 "$FEATURE_COUNT"
[ "$FEATURE_COUNT" -le 5 ] && { echo "PASS: T2b feature count <= 5"; PASS=$((PASS+1)); } \
  || { echo "FAIL: T2b feature count > 5 ($FEATURE_COUNT)"; FAIL=$((FAIL+1)); }

# T3: every MVP feature has an acceptance condition
AC_COUNT=$(grep -c "^\*\*Acceptance condition\*\*" docs/mvp-scope.md)
assert_eq "T3 acceptance conditions match feature count" "$FEATURE_COUNT" "$AC_COUNT"

# T4: Deferred Work section is present and has at least 1 row
DEFERRED_ROWS=$(grep -A 50 "^## Deferred Work" docs/mvp-scope.md | grep -c "^| " || true)
assert_gte "T4 deferred table has >= 1 row" 1 "$DEFERRED_ROWS"

# T5: epic.md no longer contains the placeholder
PLACEHOLDER_HITS=$(grep -c "placeholder scope table" docs/epic.md || true)
assert_eq "T5 placeholder removed from epic.md" 0 "$PLACEHOLDER_HITS"

# T6: epic.md links to mvp-scope.md
LINK_HITS=$(grep -c "mvp-scope.md" docs/epic.md)
assert_gte "T6 epic.md links to mvp-scope.md" 1 "$LINK_HITS"

# T7: timeline.md shows Task 3 complete
TIMELINE_COMPLETE=$(grep "Task 3" docs/timeline.md | grep -c "Complete" || true)
assert_gte "T7 timeline Task 3 marked Complete" 1 "$TIMELINE_COMPLETE"

# T8: spec-index.md registers mvp-scope.md
INDEX_HITS=$(grep -c "mvp-scope.md" docs/spec-index.md)
assert_gte "T8 spec-index.md registers mvp-scope.md" 1 "$INDEX_HITS"

# T9: mvp-scope.md is non-trivial (no stubs — minimum 60 lines)
LINE_COUNT=$(wc -l < docs/mvp-scope.md)
assert_gte "T9 mvp-scope.md >= 60 lines" 60 "$LINE_COUNT"

# T10: every feature has "Why MVP" rationale present
WHY_COUNT=$(grep -c "^\*\*Why MVP\*\*" docs/mvp-scope.md)
assert_eq "T10 Why MVP rationale matches feature count" "$FEATURE_COUNT" "$WHY_COUNT"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task.

1. `docs(mvp-scope): create MVP feature set document` — after Step 3 — `docs/mvp-scope.md`: new file with full feature-by-criterion mapping, feature details, and deferred list
2. `docs(epic): replace placeholder scope table with MVP summary` — after Step 4 — `docs/epic.md`: placeholder removed, compact feature table added, link to `mvp-scope.md`
3. `docs(timeline): mark Task 3 complete` — after Step 5 — `docs/timeline.md`: Task 3 row status and date updated
4. `docs(spec-index): register mvp-scope.md` — after Step 6 — `docs/spec-index.md`: one row added
5. `test(mvp-scope): add structural assertion suite` — after tests pass — `docs/tests/test_mvp_scope_structure.sh`: 10 assertions covering presence, completeness, and cross-reference integrity

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation before the `Co-Authored-By` trailer.

---

## 7. Verification

```bash
bash docs/tests/test_mvp_scope_structure.sh
```

**Expected delta**: 0 → 10 passing (net-new test file; all 10 assertions green). Zero pre-existing tests broken. `ls docs/*.md | wc -l` increases by exactly 1 (from N to N+1).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>    # Reverts the named commit cleanly; no force required
  ```
- **Per-branch**: if verification fails catastrophically:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — discards all task commits on this branch
  ```
  Alternatively, if working on a feature branch, delete the branch:
  ```bash
  git branch -D <branch-name>       # [REQUIRES APPROVAL]
  ```

---

## 9. Deviations Allowed

- **`docs/timeline.md` has a different column schema** → adapt the replacement row to match the actual column order; note the deviation in the Step 5 commit body.
- **`docs/spec-index.md` does not exist** → verify with `ls docs/spec-index.md`; if missing, create it with a minimal two-row table (header + the new entry), note the deviation, and add `docs/spec-index.md` to the Step 6 commit.
- **Task 1 or Task 2 output is present but thin** (e.g., success criteria is a single vague criterion) → do not invent additional criteria; scope the MVP to what's stated, note the limitation in `mvp-scope.md` under a `## Scoping Notes` section, and flag it in the commit body.
- **Feature scoring produces < 3 YES rows** → STOP and flag as a blocker rather than inventing features; this means Task 2's success criteria are insufficient to drive scoping.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

This task ends at producing the feature list and updating the three cross-reference documents. It does not design, architect, or build anything. The following items were considered and explicitly excluded — an executor encountering any of them should stop and flag rather than absorbing the work.

- **Architecture Revision 1** — `architecture.md` is gated on this task completing; that revision is a separate task and requires the full constraint inventory from Task 4 as well. Touching `architecture.md` here is premature.
- **Feature decomposition into user stories or tickets** — story-mapping belongs in sprint planning, not in a scoping workshop. Acceptance conditions in `mvp-scope.md` are intentionally one sentence; expanding them into full stories is deferred to the team's sprint-zero process.
- **Effort estimation beyond S/M/L** — point estimates, hour estimates, and staffing plans require the architecture to be settled. The S/M/L column in `mvp-scope.md` is directional only.
- **Technology or stack selection** — no stack decision can be responsible before Task 4 (hard constraints) is complete. The architecture doc's open-questions list governs this explicitly.
- **Updating `analysis.md`** — that document is Task 1's output. If the scoping process reveals gaps in the problem statement, log them as a comment in the Step 3 commit body and flag them to the team; do not edit `analysis.md` here.
- **CI integration for the test script** — `test_mvp_scope_structure.sh` is a local verification aid. Wiring it into CI pipelines is deferred to whatever CI setup task owns the pipeline config.

**Rule for the executor**: if a change appears helpful but appears in this list, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale (placeholder; gated on this task)
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update in Step 5)