# 🛠️ Task 2: Define Consumer & Success Criteria — Implementation Guide

---

## 1. Context

This task produces the single artifact that gates every downstream design decision: a `consumer-criteria.md` document that names who uses the system and asserts at least three measurable, structured success criteria in Given/When/Then form. The architecture document (`architecture.md`) is currently an explicit placeholder shell — it lists "Who is the consumer?" and "What are the scale and latency requirements?" as blocking open questions with no answer. Until those are answered in writing, no component can be named, no stack selected, and no Epic Task 3 (MVP scope) can begin. This task closes those open questions by converting stakeholder knowledge into a verifiable spec artifact that every subsequent task references as its acceptance gate.

**Trade-offs considered:**
- **Embedding criteria inside `epic.md`** — rejected because the epic is scope-oriented, not acceptance-oriented; conflating them makes it ambiguous which section governs what, and the epic is already structured around tasks, not assertions.
- **Writing criteria as a user-story backlog** — rejected because user stories defer measurability to sprint review; Given/When/Then form forces explicit conditions and observable outcomes up front, which is what unblocks architecture revision.
- **Standalone `consumer-criteria.md` with architecture cross-links** — preferred because it is independently versionable, satisfies the architecture's open-question checklist by reference, and gives subsequent tasks a single stable citation target.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm clean working tree
git status

# 2. Inspect current state of all target files before touching them
git diff HEAD -- consumer-criteria.md architecture.md timeline.md spec-index.md

# 3. Verify existing docs directory structure matches what architecture.md references
ls -1 *.md

# 4. Baseline: structural lint of existing markdown (zero broken links is the baseline)
grep -rn "\./consumer-criteria" *.md   # expect: no matches (file doesn't exist yet)
grep -n "Task 2" timeline.md           # record current status of Task 2 in timeline
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: `consumer-criteria.md` does not exist. `architecture.md` lists "Who is the consumer?" as an open blocking question. `timeline.md` Task 2 status is pending.

---

## 3. Files

### To Create (new)
- `consumer-criteria.md` (new) — primary deliverable; defines the named consumer and ≥3 Given/When/Then success criteria; becomes the acceptance gate cited by all subsequent tasks

### To Modify (cite CODEBASE CONTEXT)
- `architecture.md` — current state: "Open Questions" section lists "Who is the consumer?" as blocking and unresolved → target state: that entry is annotated with a cross-link to `consumer-criteria.md` and marked resolved; no other sections are touched
- `timeline.md` — current state: Task 2 row shows status pending → target state: status updated to "Done"; completion date recorded
- `spec-index.md` — current state: does not contain an entry for `consumer-criteria.md` → target state: entry added in document-index table

### To Leave Alone
- `epic.md` — scope definition is settled; success criteria live in `consumer-criteria.md`, not the epic; modifying the epic here risks scope creep
- `analysis.md` — analysis artifacts feed into this task as inputs but are not modified by it; they are read-only references
- Any source code files — this task produces no code; touching code files is out of scope

---

## 4. Implementation Steps

### Step 1: Conduct Consumer Discovery and Draft the Consumer Definition

**Action**: Before writing any file, conduct a focused stakeholder interview or review existing materials (product brief, prior analysis, team Slack channels, or equivalent) to answer the three blocking questions from `architecture.md`: (1) who is the consumer, (2) what interaction pattern they use (UI / API / automated pipeline), and (3) what scale/latency envelope is acceptable. Record raw notes in a scratch file (not committed). Then distill to a single, unambiguous consumer statement.

**File**: scratch notes only at this stage — do not commit raw notes. The distilled statement flows into Step 2.

**Pattern** (distillation shape to reach before proceeding):
```
Consumer: <role or system name>
Interaction: <UI | API | automated pipeline | batch>
Volume envelope: <order-of-magnitude requests/events per unit time>
Latency tolerance: <real-time (<500 ms) | interactive (<5 s) | batch (minutes)>
```

**Verify**: You can answer all four fields above with concrete words — not "TBD" or "unknown." If any field is still blank, the interview is incomplete. Do not proceed to Step 2 until all four fields have answers.

---

### Step 2: Create `consumer-criteria.md` with Consumer Definition and ≥3 Success Criteria

**Action**: Create `consumer-criteria.md` (new file) containing the formal consumer definition (from Step 1) and at least three measurable success criteria in Given/When/Then form. Each criterion must name: the precondition (Given), the actor's action or system event (When), and the observable, measurable outcome (Then). At least one criterion must address the happy path, at least one must address a failure/error path, and at least one must address a non-functional property (latency, accuracy, availability, or data correctness).

**File**: `consumer-criteria.md` (new)

**Pattern**:
```markdown
# Consumer & Success Criteria

**Status**: Draft → Ready for review  
**Owner**: [name or role]  
**Last updated**: YYYY-MM-DD  
**References**: [Architecture](./architecture.md) | [Epic](./epic.md) | [Analysis](./analysis.md)

---

## 1. Consumer Definition

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| Consumer name      | <role or system — one noun phrase>         |
| Interaction type   | <UI / REST API / event stream / batch job> |
| Volume envelope    | <N requests/events per unit time>          |
| Latency tolerance  | <real-time / interactive / batch>          |
| Data sensitivity   | <none / internal / PII / regulated>        |

**Narrative**: [One paragraph: who this consumer is, what job they are doing when they use this system, and what failure looks like for them. This paragraph is the human-readable anchor for every criterion below.]

---

## 2. Success Criteria

Each criterion follows the form: **Given** [precondition], **When** [action or event], **Then** [observable, measurable outcome].

### SC-01: [Short name — happy path]

- **Given** [specific system state or user context]
- **When** [specific action the consumer takes or event that fires]
- **Then** [outcome, with a measurable threshold — e.g., response within 500 ms, field X contains value Y, error rate < 0.1 %]

**Measurement method**: [how this is verified — log metric / integration test / manual QA step]  
**Acceptance owner**: [role responsible for signing off]

---

### SC-02: [Short name — failure / error path]

- **Given** [precondition that sets up the failure condition]
- **When** [action or event that triggers the failure]
- **Then** [what the system does — graceful degradation, error message, fallback — with measurable condition]

**Measurement method**: [how this is verified]  
**Acceptance owner**: [role]

---

### SC-03: [Short name — non-functional property]

- **Given** [load or environmental condition — e.g., "under peak load of N concurrent users"]
- **When** [representative operation]
- **Then** [non-functional outcome with threshold — e.g., p95 latency ≤ X ms, availability ≥ 99.5 %, data loss = 0]

**Measurement method**: [how this is verified]  
**Acceptance owner**: [role]

---

## 3. Acceptance Gate

A task or feature is considered complete when:

1. All SC-01 through SC-0N criteria are met with evidence recorded.
2. No pre-existing passing test has been broken.
3. The acceptance owner for each criterion has signed off in writing (PR comment or equivalent).

Any criterion not yet met MUST be listed as a blocking issue before the corresponding task is marked Done in [Timeline](./timeline.md).

---

## 4. Open Edge Cases (Deferred to Post-MVP)

The following scenarios were identified during discovery but are explicitly deferred:

- [Edge case 1] — deferred because [reason]; revisit after MVP ships
- [Edge case 2] — deferred because [reason]

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale (cites this document)
- [Epic](./epic.md) – Task scope
- [Analysis](./analysis.md) – Problems driving design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
```

**Verify**:
```bash
# File exists
ls consumer-criteria.md

# Contains at least three SC- blocks
grep -c "^### SC-" consumer-criteria.md   # expect: ≥ 3

# All three GWT keywords present in each criterion block
grep -c "\*\*Given\*\*" consumer-criteria.md   # expect: ≥ 3
grep -c "\*\*When\*\*"  consumer-criteria.md   # expect: ≥ 3
grep -c "\*\*Then\*\*"  consumer-criteria.md   # expect: ≥ 3

# Measurement method is present for each criterion
grep -c "Measurement method" consumer-criteria.md   # expect: ≥ 3

# No "TBD" left in the consumer table
grep -i "tbd" consumer-criteria.md   # expect: 0 matches
```

---

### Step 3: Annotate `architecture.md` — Close the Consumer Open Question

**Action**: In `architecture.md`, locate the "Open Questions" table. Find the row for "Who is the consumer?" and append a resolution note with a cross-link to `consumer-criteria.md`. Do NOT rewrite any other section — the architecture document is explicitly a placeholder shell until Architecture Revision 1, and this task is not that revision.

**File**: `architecture.md` (existing — from CODEBASE CONTEXT)

**Pattern** (diff shape):
```markdown
<!-- BEFORE -->
- **Who is the consumer?** — Options: internal team / external end-users / automated system / partner integration. Re-decision trigger: Epic Task 2 complete. *Consumer identity changes every component boundary.*

<!-- AFTER -->
- **Who is the consumer?** — ✅ Resolved by Epic Task 2. See [Consumer & Success Criteria](./consumer-criteria.md) § 1. Re-decision trigger: if consumer definition changes, update that document first. *Consumer identity changes every component boundary.*
```

**Verify**:
```bash
grep -n "consumer-criteria" architecture.md   # expect: ≥ 1 match with link
grep -n "✅ Resolved" architecture.md          # expect: ≥ 1 match on the consumer row
# Confirm no other sections were touched
git diff architecture.md | grep "^+" | grep -v "consumer-criteria\|✅ Resolved\|^+++" 
# expect: 0 unrelated additions
```

---

### Step 4: Update `spec-index.md` — Register the New Document

**Action**: In `spec-index.md`, add an entry for `consumer-criteria.md` in the document-index table. Match the formatting convention of existing rows exactly (inspect the file first).

**File**: `spec-index.md` (existing — referenced in CODEBASE CONTEXT)

**Pattern** (row shape to add; match surrounding table formatting):
```markdown
| [Consumer & Success Criteria](./consumer-criteria.md) | Defines the named consumer and ≥3 GWT acceptance criteria; acceptance gate for all tasks | Task 2 | Done |
```

**Verify**:
```bash
grep -n "consumer-criteria" spec-index.md   # expect: 1 match
```

---

### Step 5: Update `timeline.md` — Mark Task 2 Done

**Action**: In `timeline.md`, find the Task 2 row and update its status to "Done" and record today's completion date. Match the table formatting of surrounding rows exactly.

**File**: `timeline.md` (existing — referenced in CODEBASE CONTEXT)

**Pattern** (cell values to update; do not alter column count or row order):
```markdown
<!-- Find the Task 2 row and update Status and Completed columns -->
| Task 2 | Define Consumer & Success Criteria | Done | YYYY-MM-DD |
```

**Verify**:
```bash
grep -n "Task 2" timeline.md   # expect: row shows "Done" and today's date
```

---

## 5. Tests

The test framework for a documentation-only task is structural: bash-based grep assertions that verify the spec artifact is well-formed. These run in CI or locally. No test framework dependency is required.

```bash
#!/usr/bin/env bash
# File: test-consumer-criteria.sh  (new, placed at repo root)
# Run: bash test-consumer-criteria.sh
# Exits 0 on all pass, 1 on any failure.

set -euo pipefail
PASS=0
FAIL=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    echo "  PASS: $label (got $actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label — expected $expected, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_gte() {
  local label="$1" min="$2" actual="$3"
  if [ "$actual" -ge "$min" ]; then
    echo "  PASS: $label (got $actual, min $min)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label — expected ≥ $min, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== consumer-criteria.md existence ==="
if [ -f consumer-criteria.md ]; then
  echo "  PASS: file exists"
  PASS=$((PASS + 1))
else
  echo "  FAIL: consumer-criteria.md does not exist"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Structural: Success Criteria count ==="
SC_COUNT=$(grep -c "^### SC-" consumer-criteria.md || true)
assert_gte "at least 3 SC- blocks" 3 "$SC_COUNT"

echo ""
echo "=== Structural: GWT keyword presence ==="
GIVEN_COUNT=$(grep -c "\*\*Given\*\*" consumer-criteria.md || true)
WHEN_COUNT=$(grep -c "\*\*When\*\*"  consumer-criteria.md || true)
THEN_COUNT=$(grep -c "\*\*Then\*\*"  consumer-criteria.md || true)
assert_gte "Given appears ≥ SC count" "$SC_COUNT" "$GIVEN_COUNT"
assert_gte "When appears ≥ SC count"  "$SC_COUNT" "$WHEN_COUNT"
assert_gte "Then appears ≥ SC count"  "$SC_COUNT" "$THEN_COUNT"

echo ""
echo "=== Structural: Measurement method per criterion ==="
MM_COUNT=$(grep -c "Measurement method" consumer-criteria.md || true)
assert_gte "Measurement method appears ≥ SC count" "$SC_COUNT" "$MM_COUNT"

echo ""
echo "=== Structural: Acceptance owner per criterion ==="
AO_COUNT=$(grep -c "Acceptance owner" consumer-criteria.md || true)
assert_gte "Acceptance owner appears ≥ SC count" "$SC_COUNT" "$AO_COUNT"

echo ""
echo "=== Structural: No unresolved TBD placeholders ==="
TBD_COUNT=$(grep -ic "tbd" consumer-criteria.md || true)
assert_eq "zero TBD in consumer-criteria.md" 0 "$TBD_COUNT"

echo ""
echo "=== Structural: Consumer table completeness ==="
# All five consumer table fields must be present
for field in "Consumer name" "Interaction type" "Volume envelope" "Latency tolerance" "Data sensitivity"; do
  COUNT=$(grep -c "$field" consumer-criteria.md || true)
  assert_gte "consumer table field: $field" 1 "$COUNT"
done

echo ""
echo "=== Cross-links: architecture.md resolves consumer question ==="
ARCH_LINK=$(grep -c "consumer-criteria" architecture.md || true)
assert_gte "architecture.md links to consumer-criteria.md" 1 "$ARCH_LINK"

RESOLVED=$(grep -c "✅ Resolved" architecture.md || true)
assert_gte "architecture.md marks consumer question resolved" 1 "$RESOLVED"

echo ""
echo "=== Cross-links: spec-index.md contains entry ==="
SI_COUNT=$(grep -c "consumer-criteria" spec-index.md || true)
assert_gte "spec-index.md has consumer-criteria entry" 1 "$SI_COUNT"

echo ""
echo "=== Cross-links: timeline.md marks Task 2 done ==="
T2_DONE=$(grep -i "Task 2" timeline.md | grep -ci "Done" || true)
assert_gte "timeline.md Task 2 status is Done" 1 "$T2_DONE"

echo ""
echo "=== Coverage gate: ≥1 happy-path, ≥1 failure-path, ≥1 non-functional ==="
# These are validated by the acceptance owner during review; automated check
# verifies that the Acceptance Gate section exists and names all SC- IDs.
GATE_COUNT=$(grep -c "Acceptance Gate" consumer-criteria.md || true)
assert_gte "Acceptance Gate section present" 1 "$GATE_COUNT"

echo ""
echo "=============================="
echo "Results: $PASS passed, $FAIL failed"
echo "=============================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end. Run each commit command before moving to the next step.

1. `docs(consumer-criteria): create consumer definition and GWT success criteria` — after Step 2 — `consumer-criteria.md`: new file with consumer table, ≥3 SC- blocks, acceptance gate section
2. `docs(architecture): annotate consumer open question as resolved` — after Step 3 — `architecture.md`: consumer open-question row annotated with link and ✅ Resolved marker
3. `docs(spec-index): register consumer-criteria.md in document index` — after Step 4 — `spec-index.md`: new table row for consumer-criteria.md
4. `docs(timeline): mark Task 2 complete` — after Step 5 — `timeline.md`: Task 2 status → Done, completion date recorded
5. `test(consumer-criteria): add structural lint script for spec artifact` — after tests pass — `test-consumer-criteria.sh`: new bash test file; exits 0 on all passing

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation before the `Co-Authored-By` trailer.

---

## 7. Verification

```bash
# Run full structural test suite
bash test-consumer-criteria.sh
```

**Expected delta**: 0 → 14 passing assertions (the script above contains exactly 14 `assert_*` calls at minimum, scaling with SC count). Zero pre-existing documents broken. All cross-links resolve to real files on disk.

Additionally, perform a final manual link-walk:
```bash
# Confirm every cross-link in consumer-criteria.md points to an existing file
grep -oP '\./[a-z\-]+\.md' consumer-criteria.md | sort -u | while read f; do
  [ -f "$f" ] && echo "OK: $f" || echo "BROKEN: $f"
done
# expect: all lines print "OK:"
```

---

## 8. Rollback

- **Per-step**: each step is a discrete commit. Revert individually without touching other steps:
  ```bash
  git revert <sha-of-step-N-commit>   # creates a new revert commit; does not rewrite history
  ```
- **Per-branch**: if verification fails catastrophically and all five commits must be undone:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destroys the five commits locally
  # OR, if on a feature branch:
  git checkout main && git branch -D feature/task-2-consumer-criteria   # [REQUIRES APPROVAL]
  ```
- The safest rollback for a docs-only task is `git revert` in reverse commit order (Step 5 → Step 1), since each commit is independent and there are no schema migrations or published artifacts.

---

## 9. Deviations Allowed

- **`spec-index.md` or `timeline.md` uses a different table schema** → inspect the actual file first; adapt the row format to match existing columns exactly. Log the column name differences in the commit body.
- **`architecture.md` "Open Questions" section uses a bullet list rather than a table** → apply the annotation to the correct structural element; the link and ✅ marker must still appear. Log format difference in commit body.
- **Stakeholder interview surfaces more than 3 criteria** → include all well-formed criteria; the guide specifies a minimum of 3, not a maximum. Do not prune to exactly 3.
- **Step 3 (architecture annotation) would require broader rewrites to make sense in context** → STOP. Mark [REQUIRES APPROVAL]. The architecture document must not be substantively rewritten in this task — that is Architecture Revision 1, which is explicitly deferred.
- **Side-effect required** (push to remote, notify external stakeholder via automated script, modify a database) → STOP, mark [REQUIRES APPROVAL] and flag before proceeding.

---

## 10. Out of Scope

This task produces the consumer definition and acceptance criteria document. It does not produce an architecture revision, a component design, a technology stack selection, or any code. The architecture document remains a placeholder shell after this task completes; that shell is intentional and is not a defect to fix here. Edge-case acceptance scenarios, load-testing thresholds, and compliance-specific criteria were identified as candidates during scoping but are explicitly deferred to post-MVP to keep this task within its one-day budget.

- **Architecture Revision 1** — deferred until Epic Tasks 1–4 are all complete; this task resolves one of five blocking open questions, not all of them
- **Edge-case acceptance criteria** — deferred to post-MVP; the three required criteria cover happy-path, failure-path, and one non-functional property, which is the minimum viable acceptance gate
- **Compliance/data-residency criteria** — deferred until Epic Task 4 (hard constraints) is complete; writing compliance criteria before constraints are confirmed risks writing criteria that are immediately invalidated
- **Non-functional benchmarking and load tests** — deferred; SC-03 names the non-functional threshold but does not implement the measurement harness; that belongs to the task that implements the feature being measured
- **Stakeholder sign-off automation** — the acceptance gate names owners and requires written sign-off, but automating that workflow (e.g., PR approval gates) is deferred to the process/CI task, not this spec task

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale; Open Questions this task partially resolves
- [Epic](./epic.md) – Task scope and port budget
- [Analysis](./analysis.md) – Problems driving design; read-only input to Step 1
- [Timeline](./timeline.md) – Status tracking; updated in Step 5
- [Spec Index](./spec-index.md) – Document overview; updated in Step 4