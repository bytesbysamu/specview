# Implementation Guide: Task 1 — Provide Real Problem Statement

**Purpose**: Replace the placeholder "test" input with a real, decision-ready problem statement so every downstream task (architecture, timeline, implementation) can unblock.

**Effort**: 0.5 days

**Dependencies**: None — this is the root task.

**Parallel With**: —

**Blocks**: Architecture Revision 1, Epic Tasks 2–4 (success criteria, MVP scope, constraints), all implementation tasks.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task exists because the entire specification tree was initialized with the single word "test" as its problem statement. Every document downstream — the architecture, the epic, the timeline — is a well-structured shell with no domain, no consumer, and no constraint. That combination makes it impossible to make any design decision that would survive contact with reality: component boundaries require at least two concrete consumers to justify, stack choices require non-functional requirements to drive them, and AI infrastructure decisions (ELA Adapter Pattern) cannot be triggered without knowing whether AI is in scope at all. The single deliverable of this task is a written problem statement that answers five blocking questions identified in `architecture.md` (domain, consumer, AI involvement, scale/latency, compliance), so that Architecture Revision 1 can be written from scratch on top of real inputs rather than a void.

**Trade-offs considered** (≤3 bullets):
- **Conduct discovery interviews first, then write** — rejected because the executor is an AI agent; scheduling stakeholder interviews is outside the execution boundary and would stall the branch indefinitely.
- **Write a speculative problem statement and mark it as a draft** — rejected because a speculative statement creates false confidence, which the architecture explicitly warns against; downstream documents may be built on it before the speculation is corrected.
- **Elicit the problem statement from the user in-session, then commit the result** — preferred because it is immediate, requires no external coordination, produces a real artifact the executor can verify and commit, and is the only option consistent with a 0.5-day effort budget.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                               # Flag any unrelated M/?? entries
git diff HEAD -- epic.md architecture.md analysis.md  # Confirm target files are clean
# No automated test suite applies to a pure documentation task.
# Record word count of epic.md as baseline instead:
wc -w epic.md
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: Word count of `epic.md` at HEAD (executor records this value before Step 1).

---

## 3. Files

### To Create (new)
- `problem-statement.md` (new) — Canonical, standalone problem statement document; other docs reference this rather than embedding the narrative inline.

### To Modify (cite CODEBASE CONTEXT)
- `epic.md` — Current state: Task 1 row contains placeholder text ("test" / discovery prompt). Target state: Task 1 row links to `problem-statement.md` and is marked **Done**.
- `analysis.md` — Current state: analysis is driven by "test" placeholder. Target state: top section updated to reference the real domain, consumer, and constraints surfaced in `problem-statement.md`.
- `architecture.md` — Current state: shell document with five open blocking questions. Target state: Open Questions section updated to mark each question **Answered** or **Partially answered** with a pointer to `problem-statement.md`. (Full architecture rewrite is deferred — see §10.)

### To Leave Alone
- `timeline.md` — Do not edit; the timeline update is a separate step that depends on the architecture revision, which is downstream of this task.
- `spec-index.md` — Do not edit; index regeneration is out of scope for this task (see §10).

---

## 4. Implementation Steps

### Step 1: Elicit the Real Problem Statement

**Action**: Ask the user the five blocking questions from `architecture.md` § Open Questions in a single structured prompt. Record their answers verbatim. Do not paraphrase or interpret at this stage.

**File**: (no file edit yet — this is an in-session elicitation step)

**Pattern** — questions to present to the user, in this exact order:

```
1. What domain does this system operate in?
   (e.g., internal tooling / consumer product / data pipeline / other — describe in your own words)

2. Who is the primary consumer?
   (e.g., internal team / external end-users / automated system / partner integration)

3. Is AI or ML involved in any feature of the MVP?
   (yes / no / unsure — if yes, briefly describe the AI role)

4. What are the rough scale and latency expectations?
   (e.g., low-traffic internal tool / high-throughput external / real-time / batch)

5. Are there compliance or data-residency constraints?
   (e.g., none / SOC 2 / GDPR / HIPAA / other)

Additionally: describe the current broken or missing behavior in 2–5 sentences, name who is affected, and state at least one decision that has already been made.
```

**Verify**: All six items (five questions + broken-behavior narrative) have non-empty answers before proceeding to Step 2. If any answer is "unsure" or blank, ask a single follow-up to narrow it before continuing. Do not proceed with a blank field.

---

### Step 2: Write `problem-statement.md`

**Action**: Using the elicited answers from Step 1, author `problem-statement.md` (new) with the structure below. Port the user's words faithfully; add transitions for readability but do not introduce scope or constraints not stated by the user.

**File**: `problem-statement.md` (new)

**Pattern**:

```markdown
# Problem Statement

**Status**: Confirmed — [date]
**Author**: [user name or role, as provided]
**Reviewers**: (to be named after architecture revision)

---

## Current Broken or Missing Behavior

[2–5 sentences verbatim/lightly edited from user answer.
 Must name the symptom, not a proposed solution.]

## Who Is Affected

[Named consumer group(s) from Step 1, Q2.
 At least one sentence on impact severity.]

## Domain

[Answer to Q1. One sentence.]

## Consumer

[Answer to Q2. One sentence.]

## AI / ML Involvement

[Answer to Q3. One sentence. If yes, one additional sentence on the AI role.]

## Scale and Latency Expectations

[Answer to Q4. One sentence.]

## Compliance and Data-Residency Constraints

[Answer to Q5. One sentence.]

## Decisions Already Made

- [At least one decision stated by the user, verbatim or lightly edited.]

## Decisions Explicitly Not Made Here

- Technology stack — deferred to Architecture Revision 1.
- Component design — deferred to Architecture Revision 1.
- MVP feature list — deferred to Epic Task 3.
```

**Verify**:

```bash
# File must exist and be non-empty
test -s problem-statement.md && echo "OK: file exists and is non-empty"

# All required section headers must be present
for section in "Current Broken" "Who Is Affected" "Domain" "Consumer" \
               "AI / ML" "Scale and Latency" "Compliance" \
               "Decisions Already Made" "Decisions Explicitly Not Made"; do
  grep -q "$section" problem-statement.md \
    && echo "OK: $section" \
    || echo "MISSING: $section"
done
```

Expected output: nine `OK:` lines, zero `MISSING:` lines.

---

### Step 3: Update `epic.md` — Mark Task 1 Done

**Action**: In `epic.md`, locate the Task 1 row (currently containing the placeholder discovery prompt). Replace the task description cell with a link to `problem-statement.md` and update the status column to **Done**.

**File**: `epic.md` (cited in CODEBASE CONTEXT)

**Pattern** — replace the placeholder row:

```markdown
<!-- BEFORE -->
| Task 1 | Provide Real Problem Statement | ... | ⬜ Not started |

<!-- AFTER -->
| Task 1 | [Provide Real Problem Statement](./problem-statement.md) | ... | ✅ Done |
```

The executor must match whatever table format already exists in `epic.md` (column order, separator style). Do not reformat unrelated rows.

**Verify**:

```bash
grep -n "problem-statement.md" epic.md   # Must return ≥1 match
grep -n "Done\|✅" epic.md              # Must include the Task 1 row
```

---

### Step 4: Update `analysis.md` — Reference Real Domain and Consumer

**Action**: In `analysis.md`, locate the opening section (currently keyed to "test" placeholder). Prepend a two-sentence summary that names the real domain and consumer from `problem-statement.md`, and add a link: `See [Problem Statement](./problem-statement.md) for full detail.` Do not rewrite the entire analysis document — only the top section.

**File**: `analysis.md` (cited in CODEBASE CONTEXT)

**Pattern**:

```markdown
<!-- Insert at top of analysis.md, before existing content -->
> **Updated [date]**: This analysis has been anchored to the confirmed problem
> statement. Domain: [domain from Step 1 Q1]. Primary consumer: [consumer from
> Step 1 Q2]. See [Problem Statement](./problem-statement.md) for full detail.

---
[existing analysis content continues unchanged below]
```

**Verify**:

```bash
head -5 analysis.md | grep -q "problem-statement.md" \
  && echo "OK: reference present in top 5 lines" \
  || echo "FAIL: reference missing from top of file"
```

---

### Step 5: Update `architecture.md` — Mark Blocking Questions Answered

**Action**: In `architecture.md` § Open Questions, for each of the five blocking questions, append an **Answer** line drawn from `problem-statement.md`. Do not rewrite any other section of the document. The full architecture rewrite is deferred (see §10).

**File**: `architecture.md` (cited in CODEBASE CONTEXT)

**Pattern** — for each open question block:

```markdown
- **What domain does this system operate in?** — ...existing text...
  > **Answer (Task 1)**: [domain]. See [Problem Statement](./problem-statement.md).

- **Who is the consumer?** — ...existing text...
  > **Answer (Task 1)**: [consumer]. See [Problem Statement](./problem-statement.md).

- **Is AI/ML involved?** — ...existing text...
  > **Answer (Task 1)**: [yes/no + role, or no]. See [Problem Statement](./problem-statement.md).

- **What are the scale and latency requirements?** — ...existing text...
  > **Answer (Task 1)**: [scale/latency]. See [Problem Statement](./problem-statement.md).

- **Are there compliance or data-residency constraints?** — ...existing text...
  > **Answer (Task 1)**: [constraints]. See [Problem Statement](./problem-statement.md).
```

**Verify**:

```bash
grep -c "Answer (Task 1)" architecture.md   # Must return exactly 5
```

---

## 5. Tests

This task produces documentation artifacts, not executable code. The "tests" are structural grep assertions run against the committed files. These replace unit tests and are the executor's verification gate before the final commit.

```bash
#!/usr/bin/env bash
# Save as: validate-problem-statement.sh (new, in {WORKSPACE} root)
# Run: bash validate-problem-statement.sh
# Exit 0 = all pass. Exit 1 = at least one failure.

PASS=0
FAIL=0

assert_grep() {
  local label="$1" pattern="$2" file="$3"
  if grep -q "$pattern" "$file" 2>/dev/null; then
    echo "PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $label — pattern '$pattern' not found in $file"
    FAIL=$((FAIL + 1))
  fi
}

assert_file_nonempty() {
  local label="$1" file="$2"
  if [ -s "$file" ]; then
    echo "PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $label — $file is missing or empty"
    FAIL=$((FAIL + 1))
  fi
}

# --- problem-statement.md assertions ---
assert_file_nonempty "problem-statement.md exists and is non-empty" "problem-statement.md"
assert_grep "has 'Current Broken or Missing Behavior' section" \
  "Current Broken or Missing Behavior" "problem-statement.md"
assert_grep "has 'Who Is Affected' section" \
  "Who Is Affected" "problem-statement.md"
assert_grep "has 'Domain' section" \
  "^## Domain" "problem-statement.md"
assert_grep "has 'Consumer' section" \
  "^## Consumer" "problem-statement.md"
assert_grep "has 'AI / ML Involvement' section" \
  "AI / ML Involvement" "problem-statement.md"
assert_grep "has 'Scale and Latency' section" \
  "Scale and Latency" "problem-statement.md"
assert_grep "has 'Compliance' section" \
  "Compliance" "problem-statement.md"
assert_grep "has at least one 'Decisions Already Made' entry" \
  "Decisions Already Made" "problem-statement.md"
assert_grep "has status line" \
  "^\\*\\*Status\\*\\*:" "problem-statement.md"

# --- epic.md assertions ---
assert_grep "epic.md links to problem-statement.md" \
  "problem-statement.md" "epic.md"
assert_grep "epic.md marks Task 1 done" \
  "Done\|✅" "epic.md"

# --- analysis.md assertions ---
assert_grep "analysis.md references problem-statement.md in top 10 lines (use grep -m1)" \
  "problem-statement.md" "analysis.md"

# --- architecture.md assertions ---
ANSWER_COUNT=$(grep -c "Answer (Task 1)" architecture.md 2>/dev/null || echo 0)
if [ "$ANSWER_COUNT" -eq 5 ]; then
  echo "PASS: architecture.md has exactly 5 'Answer (Task 1)' entries"
  PASS=$((PASS + 1))
else
  echo "FAIL: architecture.md has $ANSWER_COUNT 'Answer (Task 1)' entries — expected 5"
  FAIL=$((FAIL + 1))
fi

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task.

1. `docs(problem-statement): create initial problem statement from elicited input` — after Step 2 — files: `problem-statement.md` — captures domain, consumer, AI involvement, scale, compliance, and broken-behavior narrative.

2. `docs(epic): mark Task 1 done and link problem statement` — after Step 3 — files: `epic.md` — updates status and adds cross-reference.

3. `docs(analysis): anchor analysis to confirmed domain and consumer` — after Step 4 — files: `analysis.md` — prepends domain/consumer summary and link.

4. `docs(architecture): answer five blocking open questions from problem statement` — after Step 5 — files: `architecture.md` — inserts Answer annotations under each open question; does NOT rewrite architecture sections.

5. `test(docs): add structural validation script for problem statement artifacts` — after tests pass — files: `validate-problem-statement.sh` — all 14 assertions green.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
bash validate-problem-statement.sh
```

**Expected delta**: 0 → 14 passing assertions. Zero pre-existing artifacts altered beyond the scoped edits. `timeline.md` and `spec-index.md` must show no diff (`git diff HEAD -- timeline.md spec-index.md` returns empty).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # reverts a single step's commit non-destructively
  ```
- **Per-branch**: if verification fails catastrophically and the branch must be abandoned:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destructive
  # or
  git checkout main && git branch -D <feature-branch>   # [REQUIRES APPROVAL]
  ```
  Record `<pre-task-sha>` from the Pre-flight `git status` output before any edits.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** (e.g., `analysis.md` is missing) → verify with `git ls-files`; if the file is genuinely absent, create a minimal stub at that path, note the deviation in the commit body, and continue.
- **`epic.md` uses a different table format** → match the existing table format exactly; do not convert to a different Markdown table style; note any structural adaptation in the commit body.
- **User provides partial answers in Step 1** → do not fabricate missing answers; mark the unanswered field as `[Pending — see open question in architecture.md]` and document which fields remain open in the commit body.
- **`analysis.md` already has a meaningful non-placeholder opening** → insert the update block after the existing opening paragraph rather than prepending it, so the existing content is not displaced.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in that step's commit.

---

## 10. Out of Scope

This task ends when a real problem statement is committed and the five blocking open questions in `architecture.md` are annotated with answers. It does not extend to using those answers to redesign any part of the system. Architecture Revision 1 — the full top-to-bottom rewrite of `architecture.md` — is deliberately deferred because it requires Epic Tasks 2–4 (success criteria, MVP scope, hard constraints) to be complete before the architectural decisions it encodes will be stable.

- **Architecture Revision 1 (full rewrite of `architecture.md`)** — deferred until Epic Tasks 2–4 are complete; the Open Questions annotations added in Step 5 are a bridge, not a substitute.
- **`spec-index.md` regeneration** — deferred; index accuracy depends on all documents in the spec tree being stable, which they are not until the architecture revision is done.
- **`timeline.md` update** — deferred; the timeline reflects delivery of the architecture and implementation, not just the problem statement; updating it now would create a false sense of progress.
- **Epic Tasks 2–4 (success criteria, MVP scope, constraints)** — each is a separate task with its own guide; do not draft them as a side-effect of this task even if the user's Step 1 answers suggest obvious candidates.
- **Technology stack selection** — not in scope; no non-functional requirements are confirmed until Epic Task 4 (constraints) is complete.
- **ELA Adapter pattern / AI infrastructure design** — triggered only after AI involvement is confirmed and MVP scope is set; even if Step 1 confirms AI is in scope, the adapter design does not begin here.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale; Open Questions section is the primary target of Step 5
- [Epic](./epic.md) — Task scope and status tracking; Task 1 row is the primary target of Step 3
- [Timeline](./timeline.md) — Status tracking; to be updated after Architecture Revision 1, not here
- [Analysis](./analysis.md) — Problem analysis; top section is the primary target of Step 4
- [Spec Index](./spec-index.md) — Document overview; left alone per §3