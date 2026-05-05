# Implementation Guide: Task 4 — Identify Hard Constraints & Dependencies

---

## 1. Context

This task produces a canonical `constraints.md` document that enumerates every forcing function the team must design around: external deadlines, partner or vendor lock-in, compliance obligations, and internal sequencing blockers. Without this document, the architecture revision (the immediate downstream artifact) cannot make cost-of-reversal judgments — compliance and timeline constraints are among the most expensive to retrofit, yet are routinely discovered late. The constraints document is a direct input feed to `architecture.md` (Open Questions: "Are there compliance or data-residency constraints?") and to `timeline.md` (sequencing dependencies determine critical-path ordering). This task deliberately stops at cataloguing — mitigation and design responses belong to the architecture work that follows.

**Trade-offs considered** (≤3 bullets):
- **Embedding constraints inline in `architecture.md`** — rejected because architecture is a living design document; constraints are facts of the environment, not design choices, and mixing them couples two different change cadences.
- **Deferring constraint capture to architecture revision** — rejected because architecture decisions cannot be costed without knowing which constraints are non-negotiable; deferral produces the exact premature commitment the architecture principles prohibit.
- **Dedicated `constraints.md` fed by structured interview template** — preferred because it gives constraints a single authoritative location, supports independent versioning, and decouples discovery work from design work.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                        # Flag any unrelated M/?? entries
git diff HEAD -- constraints.md timeline.md architecture.md   # Confirm targets are clean
ls -1 *.md                                        # Confirm which spec files exist at workspace root
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: This task produces net-new documentation; no test suite applies. Record the current `git log --oneline -5` output as your pre-task reference SHA.

---

## 3. Files

### To Create (new)
- `constraints.md` (new) — Canonical catalog of hard constraints and dependency edges; primary output of this task. No code dependency; feeds `architecture.md` and `timeline.md`.

### To Modify (cite CODEBASE CONTEXT)
- `architecture.md` — Current state: Open Questions section lists "Are there compliance or data-residency constraints?" as unresolved. Target state: add a `## Constraints Reference` section pointing to `constraints.md` and marking that blocking question as "→ see constraints.md."
- `timeline.md` — Current state: status tracking document (referenced by architecture but not yet inspected). Target state: add a sequencing dependency block that maps constraint findings to unblocked downstream tasks.
- `spec-index.md` — Current state: document overview index (referenced by architecture). Target state: add `constraints.md` entry so it appears in the canonical document list.

### To Leave Alone
- `epic.md` — Source of truth for task definitions; this task does not change scope, only documents findings against it.
- `analysis.md` — Problem analysis upstream of architecture; constraints do not alter problem framing.

---

## 4. Implementation Steps

### Step 1: Scaffold `constraints.md` with structured sections

**Action**: Create `constraints.md` at workspace root with all required top-level sections, a document header, and inline fill-in prompts. The executor populates each section by interviewing stakeholders or reviewing available project materials; where information is not yet available, mark the cell `⚠️ UNKNOWN — owner: [name], due: [date]`.

**File**: `constraints.md` (new)

**Pattern**:
```markdown
# Hard Constraints & Dependencies

**Status**: Draft — populate before Architecture Revision 1  
**Owner**: [team lead name]  
**Last updated**: YYYY-MM-DD  
**Feeds**: [architecture.md](./architecture.md), [timeline.md](./timeline.md)

---

## 1. External Forcing Functions

### 1.1 Deadlines & Milestones
| Constraint | Hard/Soft | Date | Owner | Notes |
|------------|-----------|------|-------|-------|
| [e.g. partner integration demo] | Hard | YYYY-MM-DD | [name] | [context] |

### 1.2 Partner & Vendor Dependencies
| Dependency | Type | Availability | Blocking? | Mitigation |
|------------|------|--------------|-----------|------------|
| [e.g. third-party API key provisioning] | External | [date/status] | Yes/No | [action] |

### 1.3 Compliance & Regulatory Requirements
| Requirement | Applies? | Evidence | Retrofit Cost | Owner |
|-------------|----------|----------|---------------|-------|
| SOC 2 | ⚠️ UNKNOWN | | High | |
| GDPR | ⚠️ UNKNOWN | | High | |
| HIPAA | ⚠️ UNKNOWN | | Very High | |
| Data residency | ⚠️ UNKNOWN | | High | |
| None confirmed | — | — | — | |

---

## 2. Internal Sequencing Constraints

### 2.1 Dependency Graph
<!-- List each task-to-task edge that represents a hard block -->
| Upstream Task | Downstream Task | Type | Rationale |
|---------------|-----------------|------|-----------|
| Task 1 (Problem Statement) | Architecture Revision 1 | Hard block | Domain unknown without it |
| Task 2 (Success Criteria) | Architecture Revision 1 | Hard block | Scale/latency inputs required |
| Task 3 (MVP Scope) | Architecture Revision 1 | Hard block | Component count unknown |
| Task 4 (Constraints) | Architecture Revision 1 | Hard block | Compliance gates stack choice |

### 2.2 Parallel-Safe Tasks
| Task Pair | Safe to Parallelize? | Condition |
|-----------|----------------------|-----------|
| [Task A] + [Task B] | Yes/No | [condition if yes] |

---

## 3. Technology & Platform Constraints
| Constraint | Source | Non-negotiable? | Notes |
|------------|--------|-----------------|-------|
| [e.g. must deploy to existing AWS org] | [infra team] | Yes | |
| [e.g. language runtime version lock] | [build system] | TBD | |

---

## 4. Resource Constraints
| Resource | Available | Required | Gap | Owner |
|----------|-----------|----------|-----|-------|
| Engineering headcount | [N] FTE | [N] FTE | [delta] | |
| Budget | [amount] | [estimate] | [delta] | |

---

## 5. Open Constraint Items

Items that must be resolved before Architecture Revision 1 is signed off:

- [ ] Compliance scope confirmed by legal/security (SOC 2 / GDPR / HIPAA / none)
- [ ] Hard ship date confirmed by product
- [ ] All external partner API/service dependencies identified and provisioned or on track
- [ ] Deployment target confirmed (cloud provider, region, tenancy model)

---

## 6. Change Log
| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | [name] | Initial draft |
```

**Verify**:
```bash
grep -c "^##" constraints.md
```
Expect: `6` (six top-level sections present).

---

### Step 2: Populate constraint cells from available project materials

**Action**: For each table in `constraints.md`, fill in every row that can be resolved from currently available information (epic, architecture open questions, any existing project docs). Leave `⚠️ UNKNOWN` only where no evidence exists. Do not speculate — mark unknown cells with an owner and a resolution-due date. At minimum, populate Section 2.1 (Internal Sequencing Constraints) from the dependency chain already encoded in `architecture.md` Execution Flow.

**File**: `constraints.md` (created in Step 1)

**Pattern** (Section 2.1 minimum population from architecture.md Execution Flow):
```markdown
| Task 1 (Problem Statement) | Architecture Revision 1 | Hard block | Domain is an input to every component boundary decision |
| Task 2 (Success Criteria)  | Architecture Revision 1 | Hard block | Scale/latency requirements gate stack selection |
| Task 3 (MVP Scope)         | Architecture Revision 1 | Hard block | Component count and interface count are undefined without MVP scope |
| Task 4 (This task)         | Architecture Revision 1 | Hard block | Compliance constraints are most expensive to retrofit; must be known before stack is chosen |
| Tasks 1–4                  | Timeline Revision 1     | Hard block | Critical path cannot be drawn until all constraint edges are known |
```

**Verify**:
```bash
grep -c "⚠️ UNKNOWN" constraints.md
```
Record the count. Every `⚠️ UNKNOWN` is an open action item. The count should decrease in subsequent revisions as stakeholders are interviewed.

---

### Step 3: Add `## Constraints Reference` section to `architecture.md`

**Action**: Open `architecture.md`. Locate the `## Open Questions` section. Insert a new `## Constraints Reference` section immediately above `## Open Questions`. In `## Open Questions`, replace the compliance bullet's body text with a forward-reference to `constraints.md`. Do not alter any other section.

**File**: `architecture.md` (cite CODEBASE CONTEXT — architecture.md, Open Questions section)

**Pattern**:
```markdown
## Constraints Reference

Hard constraints and external forcing functions are catalogued in [constraints.md](./constraints.md).  
That document is the authoritative source; this architecture references it but does not duplicate it.

**Status of constraint inputs** (as of Architecture Revision 0):
- Compliance scope: ⚠️ see constraints.md §1.3
- Hard deadlines: ⚠️ see constraints.md §1.1
- Partner dependencies: ⚠️ see constraints.md §1.2
- Internal sequencing: documented in constraints.md §2.1

Architecture Revision 1 will not begin until all `⚠️ UNKNOWN` cells in constraints.md §5 (Open Items) are resolved.

---
```

Then update the compliance open question bullet from:
```markdown
- **Are there compliance or data-residency constraints?** — Options: none / SOC 2 / GDPR / HIPAA / other. Re-decision trigger: Epic Task 4 (hard constraints) complete. *Compliance constraints are the most expensive to retrofit.*
```
to:
```markdown
- **Are there compliance or data-residency constraints?** — → see [constraints.md §1.3](./constraints.md). Re-decision trigger: constraints.md §5 checklist complete. *Compliance constraints are the most expensive to retrofit.*
```

**Verify**:
```bash
grep -n "Constraints Reference" architecture.md
grep -n "constraints.md" architecture.md | wc -l
```
Expect: first command returns one line; second returns `≥ 4` references.

---

### Step 4: Add dependency block to `timeline.md`

**Action**: Open `timeline.md`. Append (or insert into) a `## Dependency Map` section that encodes the hard-block edges from `constraints.md §2.1`. If `timeline.md` already has a section with a semantically equivalent name, extend it rather than duplicating.

**File**: `timeline.md` (cite CODEBASE CONTEXT — timeline.md, status tracking document)

**Pattern**:
```markdown
## Dependency Map

Sourced from [constraints.md §2](./constraints.md). Update constraints.md first; this section mirrors it.

```
Task 1 (Problem Statement)
Task 2 (Success Criteria)   ──→ Architecture Revision 1 ──→ All engineering tasks
Task 3 (MVP Scope)
Task 4 (Constraints) ──────┘
```

**Critical path**: Tasks 1–4 are the critical path gate. No engineering task begins until Architecture Revision 1 is signed off.

**Earliest Architecture Revision 1 start**: when constraints.md §5 open items are all resolved.
```

**Verify**:
```bash
grep -n "Dependency Map" timeline.md
grep -n "constraints.md" timeline.md
```
Expect: both return at least one matching line.

---

### Step 5: Register `constraints.md` in `spec-index.md`

**Action**: Open `spec-index.md`. Add an entry for `constraints.md` in whatever list or table format `spec-index.md` uses. Place it after the entry for `analysis.md` and before `architecture.md` to reflect the flow: Analysis → Constraints → Architecture.

**File**: `spec-index.md` (cite CODEBASE CONTEXT — spec-index.md, document overview index)

**Pattern** (adapt to existing table/list format found in spec-index.md):
```markdown
| [constraints.md](./constraints.md) | Hard constraints & dependency edges | Task 4 | Feeds architecture.md, timeline.md |
```

**Verify**:
```bash
grep "constraints.md" spec-index.md
```
Expect: at least one line returned.

---

## 5. Tests

This task produces documentation. Structural verification replaces unit tests. The following shell assertions constitute the test suite; all must pass before marking the task complete.

```bash
# T1 — constraints.md exists and has all 6 required sections
test $(grep -c "^## " constraints.md) -ge 6 \
  && echo "PASS T1: constraints.md has required sections" \
  || echo "FAIL T1: constraints.md missing sections"

# T2 — all five internal sequencing edges are present
for phrase in \
  "Problem Statement" \
  "Success Criteria" \
  "MVP Scope" \
  "Architecture Revision 1" \
  "Hard block"; do
  grep -q "$phrase" constraints.md \
    && echo "PASS T2: '$phrase' present" \
    || echo "FAIL T2: '$phrase' missing from constraints.md"
done

# T3 — architecture.md references constraints.md at least 4 times
count=$(grep -c "constraints.md" architecture.md)
test "$count" -ge 4 \
  && echo "PASS T3: architecture.md has $count references to constraints.md" \
  || echo "FAIL T3: architecture.md has only $count references (expected ≥4)"

# T4 — timeline.md contains Dependency Map section
grep -q "Dependency Map" timeline.md \
  && echo "PASS T4: timeline.md has Dependency Map" \
  || echo "FAIL T4: timeline.md missing Dependency Map"

# T5 — spec-index.md lists constraints.md
grep -q "constraints.md" spec-index.md \
  && echo "PASS T5: spec-index.md lists constraints.md" \
  || echo "FAIL T5: spec-index.md does not list constraints.md"

# T6 — no section in constraints.md is completely empty (each has body text)
python3 - <<'EOF'
import re, sys
with open("constraints.md") as f:
    content = f.read()
sections = re.split(r'\n## ', content)
empty = [s.split('\n')[0] for s in sections[1:] if len(s.strip().splitlines()) < 3]
if empty:
    print(f"FAIL T6: sections with no body content: {empty}")
    sys.exit(1)
print("PASS T6: all sections have body content")
EOF

# T7 — Open Items checklist exists and has at least 4 items
count=$(grep -c "^\- \[" constraints.md)
test "$count" -ge 4 \
  && echo "PASS T7: Open Items checklist has $count items" \
  || echo "FAIL T7: Open Items checklist has only $count items (expected ≥4)"
```

---

## 6. Commit Plan

**Executor instruction**: run each `git commit` command immediately after completing the corresponding step — not at the end of the task.

1. `docs(constraints): scaffold constraints.md with all required sections` — after Step 1 — files: `constraints.md`: empty scaffold with all six section headers and table templates in place.

2. `docs(constraints): populate known dependency edges and mark unknowns` — after Step 2 — files: `constraints.md`: Section 2.1 filled from architecture.md execution flow; all unknown cells marked with `⚠️ UNKNOWN` and owner fields.

3. `docs(architecture): add Constraints Reference section and forward-references` — after Step 3 — files: `architecture.md`: new `## Constraints Reference` section inserted; compliance open question updated to point to `constraints.md`.

4. `docs(timeline): add Dependency Map sourced from constraints.md` — after Step 4 — files: `timeline.md`: `## Dependency Map` section added with critical-path encoding.

5. `docs(spec-index): register constraints.md in document index` — after Step 5 — files: `spec-index.md`: constraints.md entry added between analysis.md and architecture.md.

6. `test(constraints): add structural verification suite` — after all tests pass — files: any test runner file or inline in CI; records T1–T7 assertions passing.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation (e.g., `Deviations: timeline.md had no existing sections; created file from scratch`).

---

## 7. Verification

```bash
# Run full structural test suite
bash -e <<'SUITE'
test $(grep -c "^## " constraints.md) -ge 6 || { echo "FAIL T1"; exit 1; }
for phrase in "Problem Statement" "Success Criteria" "MVP Scope" "Architecture Revision 1" "Hard block"; do
  grep -q "$phrase" constraints.md || { echo "FAIL T2: $phrase missing"; exit 1; }
done
test $(grep -c "constraints.md" architecture.md) -ge 4 || { echo "FAIL T3"; exit 1; }
grep -q "Dependency Map" timeline.md || { echo "FAIL T4"; exit 1; }
grep -q "constraints.md" spec-index.md || { echo "FAIL T5"; exit 1; }
grep -q "constraints.md" spec-index.md || { echo "FAIL T5"; exit 1; }
test $(grep -c "^\- \[" constraints.md) -ge 4 || { echo "FAIL T7"; exit 1; }
echo "ALL STRUCTURAL TESTS PASS"
SUITE
```

**Expected delta**: 0 tests existed before this task; 7 structural assertions now pass (T1–T7). Zero pre-existing document references broken (verify with `grep -rn "constraints.md" . | wc -l` — expect the count grows, never shrinks after each step).

---

## 8. Rollback

- **Per-step**: each commit above is independently revertible without affecting prior steps.
  ```bash
  git revert <sha>    # Reverts exactly one step's changes; safe to run on any individual commit
  ```
- **Per-branch**: if verification fails catastrophically and multiple commits are corrupted:
  ```bash
  git reset --hard <pre-task-sha>    # [REQUIRES APPROVAL] — destructive; confirm SHA from pre-flight log
  ```
  Alternatively, if working on a feature branch: `git checkout main` and delete the branch.
- **Partial rollback order**: if only some steps need reverting, reverse-order revert: Step 6 → Step 5 → Step 4 → Step 3 → Step 2 → Step 1. Reverting Step 3 before Step 2 leaves `architecture.md` referencing a `constraints.md` that has been emptied.

---

## 9. Deviations Allowed

- **`timeline.md` or `spec-index.md` does not exist** → verify with `ls -1 *.md`; if missing, create the file from scratch with only the content this task adds, log as deviation in commit body.
- **`spec-index.md` uses a list format instead of a table** → match the existing format; translate the table entry to a list item silently, note in commit body.
- **`architecture.md` Open Questions section has changed structure** → locate the compliance question by content (grep for "compliance or data-residency"), update in place, log deviation.
- **Stakeholder interview reveals a hard constraint not anticipated by this template** → add it to the appropriate section table without adding new top-level sections; if a genuinely new category is required, add a Section 7 and log as deviation.
- **Side-effect required** (e.g., constraint document must be pushed to a shared wiki or Confluence) → STOP, mark `[REQUIRES APPROVAL]` and ask before proceeding.

---

## 10. Out of Scope

This task ends at cataloguing constraints — it does not evaluate them, propose mitigations, or make architectural decisions based on them. The 0.5-day budget covers discovery and documentation only. Mitigation planning, risk scoring, stack selection, and compliance program design are downstream work that belongs in Architecture Revision 1 and beyond. An eager executor will be tempted to propose design responses to the constraints found; that work is explicitly deferred.

- **Compliance program design** (SOC 2 readiness, GDPR controls, HIPAA BAA) — deferred to a dedicated compliance track; inputs from constraints.md feed that track, but the track itself is not scoped here.
- **Risk scoring or priority-ordering of constraints** — deferred to architecture work; the architecture team applies weighting once the full constraint set is visible.
- **Mitigation plans for external dependencies** — deferred; this task names the dependencies, Architecture Revision 1 decides how to design around them.
- **Stakeholder interview scheduling or facilitation** — this guide assumes interviews are conducted by the task owner; the guide does not script or schedule them.
- **Constraint tracking in a project management tool** (Jira, Linear, Notion) — deferred; `constraints.md` is the source of truth for now; a sync to a PM tool is a separate operational decision.
- **Architecture Revision 1 itself** — explicitly not started here; this task only resolves the last blocking input that Revision 1 requires.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale; updated by Step 3 of this guide
- [Epic](./epic.md) — Task scope; do not modify
- [Timeline](./timeline.md) — Status tracking; updated by Step 4 of this guide
- [Spec Index](./spec-index.md) — Document overview; updated by Step 5 of this guide