# Task 1 — Confirm Module Inventory and Resolve Open Questions

## 1. Context

Before a single file moves in the modular restructure, three factual gaps must be closed: whether `implementation_guide/` exposes HTTP routes (requiring a Blueprint slot), whether `quality/` does the same, and which strategy the `packages_areInExpectedHierarchy` structural test (Task 5) should use to police the `saas_optional` allowlist. Getting these wrong would cause either silent Blueprint omissions in `create_app.py` or a structural test that is either too strict or too permissive on day one. This task runs only read commands, writes one output document, and commits it — the mapping document is the gate that Tasks 2 through 5 consume to avoid re-inspecting the filesystem mid-move.

**Trade-offs considered:**

- **Defer all three questions to Task 2** — rejected because the answers change Task 2's scaffold target list; starting Task 2 without them means re-work if the answers surprise.
- **Inline the answers in commit messages** — rejected because commit messages are not reliably discoverable; a named document in `api/docs/restructure/` is linkable and diffable across PRs.
- **Write findings to a Markdown doc committed with the task** — preferred; costs one small commit, gives Tasks 2–5 a stable reference point, and the `saas_optional` rationale is preserved alongside its architectural context.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# 1. Confirm clean working tree
git status

# 2. Confirm no in-flight changes on the target output path
git diff HEAD -- api/docs/restructure/

# 3. Record baseline test count — must match 624 before proceeding
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
```

**If working tree is dirty on any `api/` path**: stash or commit unrelated changes before starting.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)

- `api/docs/restructure/task-1-findings.md` — the output document; records confirmed inventory, answers to all three open questions, the complete source → target mapping, and the `saas_optional` decision with rationale. Consumed by Tasks 2–5.

### To Modify

*None.* This task writes only the new findings document.

### To Leave Alone

- `api/modules/` — every `.py` file; read-only inspection only
- `api/create_app.py` — read for Blueprint inventory; do not touch
- `api/tests/test_structural.py` — read to understand existing tests; Task 5 adds the new assertion
- `api/openapi.yaml` — independent of package layout; out of scope for all restructure tasks
- `api/dtos/models.py` — generated artifact; never hand-edited

---

## 4. Implementation Steps

### Step 1: Inventory `modules/implementation_guide/`

**Action**: List every file under `implementation_guide/` and confirm whether `routes.py` exists.

**File**: `{WORKSPACE}/api/modules/implementation_guide/` (existing)

**Pattern**:
```bash
find {WORKSPACE}/api/modules/implementation_guide -type f -name "*.py" | sort
```

**Expected output** — verify character-for-character; flag any addition or omission:
```
modules/implementation_guide/__init__.py
modules/implementation_guide/prompts.py
modules/implementation_guide/tests/__init__.py
modules/implementation_guide/tests/test_attribution.py
modules/implementation_guide/tests/test_impl_guide_prompts.py
modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py
```

**Answer to Open Question 1**: `routes.py` is **absent**. `implementation_guide` is a prompt-only module. No Blueprint entry is present in `ENABLED_MODULES` and none is needed post-restructure.

**Verify**: `ls {WORKSPACE}/api/modules/implementation_guide/routes.py` → `No such file or directory`

---

### Step 2: Inventory `modules/quality/`

**Action**: List every file under `quality/` and confirm whether `routes.py` exists.

**File**: `{WORKSPACE}/api/modules/quality/` (existing)

**Pattern**:
```bash
find {WORKSPACE}/api/modules/quality -type f -name "*.py" | sort
```

**Expected output**:
```
modules/quality/__init__.py
modules/quality/coherence.py
modules/quality/lint.py
modules/quality/tests/__init__.py
modules/quality/tests/test_coherence.py
modules/quality/tests/test_lint.py
```

**Answer to Open Question 2**: `routes.py` is **absent**. `quality` is a service-only module (`coherence.py`, `lint.py`). No Blueprint entry exists in `ENABLED_MODULES` and none is needed; its path does not change in the restructure.

**Verify**: `ls {WORKSPACE}/api/modules/quality/routes.py` → `No such file or directory`

---

### Step 3: Confirm `ENABLED_MODULES` in `create_app.py`

**Action**: Read `create_app.py` and record the exact `ENABLED_MODULES` list and how Blueprint registration works.

**File**: `{WORKSPACE}/api/create_app.py` (existing)

**Pattern**:
```bash
grep -n "ENABLED_MODULES\|register_blueprint\|import_module" \
  {WORKSPACE}/api/create_app.py
```

**Expected output** (exact entries; record actual line numbers):
```python
ENABLED_MODULES = [
    ('modules.projects.routes',  'projects_bp'),
    ('modules.context.routes',   'context_bp'),
    ('modules.ai.routes',        'ai_bp'),
    ('modules.templates.routes', 'templates_bp'),
    ('modules.task_gen.routes',  'task_gen_bp'),
    ('modules.spec_gen.routes',  'spec_gen_bp'),
]
```

Confirm `implementation_guide` is **absent** from this list and `quality` is **absent** from this list — consistent with Steps 1 and 2.

**Verify**: `grep -c "implementation_guide\|quality" {WORKSPACE}/api/create_app.py` → `0`

---

### Step 4: Enumerate all top-level `modules/` directories

**Action**: List every immediate subdirectory of `modules/` (one level deep).

**File**: `{WORKSPACE}/api/modules/` (existing)

**Pattern**:
```bash
ls -1 {WORKSPACE}/api/modules/ | sort
```

**Expected output** (10 entries):
```
__init__.py
ai
chain
context
implementation_guide
projects
quality
spec_gen
task_gen
templates
workflows
```

**Note for findings document**: `__pycache__` may also appear; exclude it from the canonical list.

**Verify**: count non-dunder directories: `ls -1d {WORKSPACE}/api/modules/*/` | wc -l` → `10`

---

### Step 5: Complete cross-module file inventory

**Action**: For each of the six modules that are moving (`chain`, `workflows`, `spec_gen`, `task_gen`, `projects`, `context`, `templates`), list every `.py` source file (excluding `__pycache__`). Record the results verbatim in the findings document.

**File**: `{WORKSPACE}/api/modules/` (existing)

**Pattern**:
```bash
for mod in chain workflows spec_gen task_gen projects context templates ai; do
  echo "=== $mod ===";
  find {WORKSPACE}/api/modules/$mod -type f -name "*.py" \
    | grep -v __pycache__ | sort | sed "s|{WORKSPACE}/api/||";
done
```

**Expected output per module** — verify these exactly; note any addition or omission as a codebase-context discrepancy and record it in the findings document:

```
=== chain ===
modules/chain/__init__.py
modules/chain/adapter.py
modules/chain/context.py
modules/chain/context_loader.py
modules/chain/errors.py
modules/chain/file_parser.py
modules/chain/types.py
modules/chain/providers/__init__.py
modules/chain/providers/claude.py          ← codebase.md shows "anthropic_sdk.py"; actual name is claude.py
modules/chain/providers/cli.py
modules/chain/providers/mock.py
modules/chain/tests/__init__.py
modules/chain/tests/...                    (4 test files — list verbatim)

=== workflows ===
modules/workflows/__init__.py
modules/workflows/execution.py             ← not listed in codebase.md map; record as undocumented file
modules/workflows/runtime.py
modules/workflows/workflow.py
modules/workflows/repository/__init__.py
modules/workflows/repository/fs_adapter.py
modules/workflows/steps/__init__.py
modules/workflows/steps/ai_call.py
modules/workflows/steps/base.py
modules/workflows/steps/compute.py
modules/workflows/steps/events.py
modules/workflows/steps/registry.py
modules/workflows/tests/...                (9 test files — list verbatim)

=== spec_gen ===
modules/spec_gen/__init__.py
modules/spec_gen/prompts.py
modules/spec_gen/routes.py
modules/spec_gen/tests/__init__.py
modules/spec_gen/tests/test_bootstrap_workflow.py
modules/spec_gen/tests/test_routes.py
modules/spec_gen/workflows/__init__.py
modules/spec_gen/workflows/bootstrap.py
modules/spec_gen/workflows/generate_spec.py

=== task_gen ===
modules/task_gen/__init__.py
modules/task_gen/routes.py
modules/task_gen/service.py
modules/task_gen/tests/...                 (list verbatim)

=== projects ===
modules/projects/__init__.py
modules/projects/errors.py
modules/projects/routes.py
modules/projects/service.py

=== context ===
modules/context/__init__.py
modules/context/routes.py
modules/context/service.py
modules/context/tests/...                  (list verbatim if present)

=== templates ===
modules/templates/__init__.py
modules/templates/generators.py
modules/templates/routes.py
modules/templates/tests/__init__.py
modules/templates/tests/test_generators.py
modules/templates/tests/test_generators_snapshots.py
modules/templates/tests/__snapshots__/test_generators_snapshots.ambr

=== ai ===
modules/ai/__init__.py
modules/ai/errors.py
modules/ai/routes.py
modules/ai/prompts/__init__.py
modules/ai/prompts/builder.py
modules/ai/tests/__init__.py
modules/ai/tests/...                       (list verbatim)
```

**Verify**: each `find` command exits 0 and the file counts match the expected lists. Flag any file not listed above as a finding.

---

### Step 6: Record the `saas_optional` decision

**Action**: Based on the confirmed inventory and the architecture's description of SaaS capabilities, record the allowlist decision.

**Decision: exhaustive allowlist** — `{"auth", "billing", "usage", "observability"}`

**Rationale** (record verbatim in the findings document):

> The architecture names exactly four SaaS modules with no open-ended qualifier. Each SaaS capability is its own future epic; the PR that adds it must also extend this allowlist — making the addition visible in the diff. A naming-convention check (`startswith("saas_")`) is open-ended: it allows any string matching the prefix past CI without explicit acknowledgment, which re-creates the silent sprawl this structural test is designed to prevent. Four known names, exhaustive list, annotated comment explaining why.

**Verify**: cross-check that none of `auth`, `billing`, `usage`, `observability` appears as an existing directory under `modules/`:
```bash
ls {WORKSPACE}/api/modules/ | grep -E "^(auth|billing|usage|observability)$"
```
Expected: no output (no pre-existing SaaS modules). Record result.

---

### Step 7: Write `task-1-findings.md`

**Action**: Create the output document. The executor fills in the exact file listings discovered in Steps 1–6. Do not paraphrase; paste actual command output.

**File**: `{WORKSPACE}/api/docs/restructure/task-1-findings.md` **(new)**

**Pattern**:
```bash
mkdir -p {WORKSPACE}/api/docs/restructure
```

Then write the document with this exact structure (fill `[…]` from Steps above):

```markdown
# Task 1 Findings — Module Inventory and Open Question Resolutions

Generated: 2026-04-26  
Baseline test count: 624 passing / 1 skipped

---

## Open Question Resolutions

### Q1: Does `implementation_guide/routes.py` exist?
**Answer: NO.**  
Files present: `__init__.py`, `prompts.py`, `tests/` (3 files).  
Blueprint action required in post-restructure `create_app.py`: **none**.  
Target location: `modules/ai/prompts/impl_guide.py`

### Q2: Does `quality/` register a Blueprint?
**Answer: NO.**  
Files present: `__init__.py`, `coherence.py`, `lint.py`, `tests/` (2 files).  
Blueprint action required in post-restructure `create_app.py`: **none**.  
Location change: `quality/` stays at `modules/quality/` — unchanged.

### Q3: `saas_optional` — exhaustive allowlist or naming-convention check?
**Decision: EXHAUSTIVE ALLOWLIST**  
Value: `{"auth", "billing", "usage", "observability"}`  
Rationale: Architecture names exactly 4 SaaS modules with no open-ended qualifier.
Each new SaaS module must extend this set via an explicit PR diff — that edit is
the acknowledgment gate. A prefix convention is open-ended and re-creates silent
sprawl. Confirmed no pre-existing SaaS directories exist under `modules/`.

---

## Codebase Context Discrepancies

The following files exist on disk but are not listed in `codebase.md`:

| Actual path | codebase.md note |
|---|---|
| `modules/chain/providers/claude.py` | Listed as `anthropic_sdk.py (planned)` |
| `modules/chain/context.py` | Not listed |
| `modules/chain/context_loader.py` | Not listed |
| `modules/chain/file_parser.py` | Not listed |
| `modules/chain/types.py` | Not listed |
| `modules/chain/providers/mock.py` | Not listed |
| `modules/workflows/execution.py` | Not listed |

Tasks 2–5 must use the **actual** paths above, not the codebase.md approximation.

---

## Module Inventory (source of truth for Task 3 moves)

### modules/implementation_guide/ (PROMPT-ONLY — no Blueprint)
[paste Step 1 output verbatim]

### modules/quality/ (SERVICE-ONLY — no Blueprint, no move)
[paste Step 2 output verbatim]

### modules/chain/ (→ runtime/chain/)
[paste Step 5 chain output verbatim]

### modules/workflows/ (→ runtime/workflows/)
[paste Step 5 workflows output verbatim]

### modules/spec_gen/ (→ ai/)
[paste Step 5 spec_gen output verbatim]

### modules/task_gen/ (→ ai/)
[paste Step 5 task_gen output verbatim]

### modules/ai/ (restructured in-place)
[paste Step 5 ai output verbatim]

### modules/projects/ (→ data/projects/)
[paste Step 5 projects output verbatim]

### modules/context/ (→ data/context/)
[paste Step 5 context output verbatim]

### modules/templates/ (→ data/templates/)
[paste Step 5 templates output verbatim]

---

## Source → Target Mapping (Task 3 reference)

Architecture estimated 16 source files; actual count: [fill in from Steps above].
All __init__.py stubs are created by Task 2 (scaffold), not listed here.

### → modules/ai/ (consolidation of ai/, spec_gen/, task_gen/, implementation_guide/)

| Source | Target | Blueprint? |
|---|---|---|
| `modules/ai/routes.py` | `modules/ai/routes/text.py` | yes — `ai_bp` |
| `modules/ai/errors.py` | `modules/ai/errors.py` | no |
| `modules/ai/prompts/__init__.py` | `modules/ai/prompts/__init__.py` | no |
| `modules/ai/prompts/builder.py` | `modules/ai/prompts/builder.py` | no |
| `modules/spec_gen/routes.py` | `modules/ai/routes/spec_gen.py` | yes — `spec_gen_bp` |
| `modules/spec_gen/prompts.py` | `modules/ai/prompts/spec_gen.py` | no |
| `modules/spec_gen/workflows/__init__.py` | `modules/ai/workflows/__init__.py` | no |
| `modules/spec_gen/workflows/bootstrap.py` | `modules/ai/workflows/bootstrap.py` | no |
| `modules/spec_gen/workflows/generate_spec.py` | `modules/ai/workflows/generate_spec.py` | no |
| `modules/task_gen/routes.py` | `modules/ai/routes/task_gen.py` | yes — `task_gen_bp` |
| `modules/task_gen/service.py` | `modules/ai/services/task_gen.py` | no |
| `modules/implementation_guide/prompts.py` | `modules/ai/prompts/impl_guide.py` | no |

### → modules/runtime/ (chain/ + workflows/)

| Source | Target | Blueprint? |
|---|---|---|
| `modules/chain/adapter.py` | `modules/runtime/chain/adapter.py` | no |
| `modules/chain/context.py` | `modules/runtime/chain/context.py` | no |
| `modules/chain/context_loader.py` | `modules/runtime/chain/context_loader.py` | no |
| `modules/chain/errors.py` | `modules/runtime/chain/errors.py` | no |
| `modules/chain/file_parser.py` | `modules/runtime/chain/file_parser.py` | no |
| `modules/chain/types.py` | `modules/runtime/chain/types.py` | no |
| `modules/chain/providers/__init__.py` | `modules/runtime/chain/providers/__init__.py` | no |
| `modules/chain/providers/claude.py` | `modules/runtime/chain/providers/claude.py` | no |
| `modules/chain/providers/cli.py` | `modules/runtime/chain/providers/cli.py` | no |
| `modules/chain/providers/mock.py` | `modules/runtime/chain/providers/mock.py` | no |
| `modules/workflows/execution.py` | `modules/runtime/workflows/execution.py` | no |
| `modules/workflows/runtime.py` | `modules/runtime/workflows/runtime.py` | no |
| `modules/workflows/workflow.py` | `modules/runtime/workflows/workflow.py` | no |
| `modules/workflows/repository/__init__.py` | `modules/runtime/workflows/repository/__init__.py` | no |
| `modules/workflows/repository/fs_adapter.py` | `modules/runtime/workflows/repository/fs_adapter.py` | no |
| `modules/workflows/steps/__init__.py` | `modules/runtime/workflows/steps/__init__.py` | no |
| `modules/workflows/steps/ai_call.py` | `modules/runtime/workflows/steps/ai_call.py` | no |
| `modules/workflows/steps/base.py` | `modules/runtime/workflows/steps/base.py` | no |
| `modules/workflows/steps/compute.py` | `modules/runtime/workflows/steps/compute.py` | no |
| `modules/workflows/steps/events.py` | `modules/runtime/workflows/steps/events.py` | no |
| `modules/workflows/steps/registry.py` | `modules/runtime/workflows/steps/registry.py` | no |

### → modules/data/ (projects/ + context/ + templates/)

| Source | Target | Blueprint? |
|---|---|---|
| `modules/projects/errors.py` | `modules/data/projects/errors.py` | no |
| `modules/projects/routes.py` | `modules/data/projects/routes.py` | yes — `projects_bp` |
| `modules/projects/service.py` | `modules/data/projects/service.py` | no |
| `modules/context/routes.py` | `modules/data/context/routes.py` | yes — `context_bp` |
| `modules/context/service.py` | `modules/data/context/service.py` | no |
| `modules/templates/generators.py` | `modules/data/templates/generators.py` | no |
| `modules/templates/routes.py` | `modules/data/templates/routes.py` | yes — `templates_bp` |

### → modules/quality/ (UNCHANGED)

All files stay in place. No mapping entry needed.

---

## Post-Restructure ENABLED_MODULES (Task 4 reference)

| Current import path | Post-restructure import path | Blueprint name |
|---|---|---|
| `modules.projects.routes` | `modules.data.projects.routes` | `projects_bp` |
| `modules.context.routes` | `modules.data.context.routes` | `context_bp` |
| `modules.ai.routes` | `modules.ai.routes.text` | `ai_bp` |
| `modules.templates.routes` | `modules.data.templates.routes` | `templates_bp` |
| `modules.task_gen.routes` | `modules.ai.routes.task_gen` | `task_gen_bp` |
| `modules.spec_gen.routes` | `modules.ai.routes.spec_gen` | `spec_gen_bp` |
```

**Verify**: `test -f {WORKSPACE}/api/docs/restructure/task-1-findings.md && echo "OK"` → `OK`

---

## 5. Tests

This task produces only a documentation artifact; no `.py` source file is created or modified. No new pytest tests are introduced.

**Verification obligation** (not a new test — a baseline check run twice):

```bash
# Before Step 7:
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
# Expected: 624 passed, 1 skipped

# After committing task-1-findings.md:
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
# Expected: identical output — the docs file is not collected by pytest
```

**Shell sanity check** (run after Step 7 before committing):

```bash
# Confirm the three mandatory sections are present in the findings doc
for section in "Q1:" "Q2:" "Q3:" "Source → Target" "ENABLED_MODULES"; do
  grep -q "$section" {WORKSPACE}/api/docs/restructure/task-1-findings.md \
    && echo "FOUND: $section" \
    || echo "MISSING: $section — do not commit until resolved"
done
```

All five lines must print `FOUND:` before the commit in Step 6 of the Commit Plan.

---

## 6. Commit Plan

**Executor instruction**: this task has exactly one commit. Run it after the shell sanity check passes.

```
1. docs(restructure): add task-1-findings — confirmed inventory and resolved open questions
```

**After Step 7** — file: `api/docs/restructure/task-1-findings.md`

Contents of commit:
- Confirmed file-by-file inventory for all 10 modules
- Q1 answer: `implementation_guide` is prompt-only, no Blueprint needed
- Q2 answer: `quality` is service-only, no Blueprint needed
- Q3 decision: exhaustive `saas_optional` allowlist `{"auth", "billing", "usage", "observability"}`
- Complete source → target mapping for Tasks 2–5
- Codebase-context discrepancies documented (chain provider name, undocumented files)

```bash
cd {WORKSPACE}
git add api/docs/restructure/task-1-findings.md
git commit -m "$(cat <<'EOF'
docs(restructure): add task-1-findings — confirmed inventory and resolved open questions

Inspected all 10 modules/. Key findings:
- implementation_guide has no routes.py — prompt-only, no Blueprint slot needed
- quality has no routes.py — service-only, no Blueprint slot needed
- saas_optional decision: exhaustive allowlist {"auth","billing","usage","observability"}
- chain/providers/claude.py is the actual provider filename (codebase.md shows anthropic_sdk.py)
- chain/ has 4 undocumented files: context.py, context_loader.py, file_parser.py, types.py
- workflows/ has undocumented execution.py
- Actual file-move count: [fill in] source files (architecture estimated 16)

EOF
)"
```

**Deviation logging**: if any finding differs from the expected output in Steps 1–6, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → 624 passing (0 new tests). Zero pre-existing tests broken. The new `docs/restructure/` directory is not on any pytest collection path.

---

## 8. Rollback

- **Per-step**: the single commit is independently revertible:
  ```bash
  git revert <sha>   # removes task-1-findings.md; no source files were touched
  ```
- **Per-branch**: if the branch is abandoned, `git branch -D <branch>` or `git reset --hard <pre-task-sha>`. Because no source file was modified, rollback carries zero risk of broken imports.

---

## 9. Deviations Allowed

- **A module contains a `routes.py` not expected** (e.g., `quality/routes.py` found): do not silently skip it — record it in the findings doc under a "Surprises" section, flag it as a deviation in the commit body, and note that `ENABLED_MODULES` in Task 4 must include the new entry.
- **Actual file count differs from architecture's "16 source files" estimate**: this is expected; record the actual count. The architecture note was written before full inspection. Do not attempt to reconcile — just record reality.
- **A provider file named `anthropic_sdk.py` coexists with `claude.py`**: record both; map both to `modules/runtime/chain/providers/`; do not delete either during this task.
- **`api/docs/restructure/` already exists** with other files: add `task-1-findings.md` to the existing directory; do not touch the other files.
- **Side-effect required** (push, schema change): STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.

---

## 10. Out of Scope

This task is read-only plus one documentation commit. The executor should resist the temptation to tidy, rename, or pre-move any module while the filesystem is open for inspection — the blast radius of a mid-task edit would make the findings document describe a state that no longer exists.

- **Directory scaffold (`__init__.py` stubs)** — Task 2; cannot begin until this document is committed and the mapping is confirmed
- **File moves** — Task 3; sequenced after Task 2 scaffolding passes `make test`
- **Import-path rewrites** — Task 4; touches ~50 `from modules.X` references across routes, services, and tests
- **`packages_areInExpectedHierarchy` assertion** — Task 5; encodes the `saas_optional` decision from this document inline as a comment
- **Updating `codebase.md`** to reflect the undocumented `chain/` and `workflows/` files — reasonable cleanup, but it modifies a file that the restructure tasks will also touch; defer to the post-Task-5 cleanup PR to avoid conflicting edits
- **Renaming `quality/` to `pipeline/`** — called out in architecture as a separate concern; not part of this epic

**Rule for the executor**: if a change appears helpful but is listed here, STOP, flag it as a deviation, and do not expand this task's scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale and open questions this task closes
- [Epic](./epic.md) – Full task scope; the "16 source files" estimate is refined by this task's findings
- [Timeline](./timeline.md) – Mark Task 1 complete after the findings commit merges