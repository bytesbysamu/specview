# Task 1: Fix 60-line truncation — structured prior contracts

---

## 1. Context

`collect_prior_task_content()` in `modules/task_gen/service.py` (line 177) limits each prior task document to 60 lines before concatenating them into the prompt's `PRIOR TASKS` block. Because §3 (Files) is typically the third major section of a task guide and §5 (Tests) follows it, the 60-line ceiling routinely cuts off both — meaning downstream task generation never sees what files a prior task declared as `(new)` or `(modify)`. This is the structural root cause of cross-task path and field-name drift identified in the analysis. This task replaces the truncation with a structured contract parser (`_parse_task_contract`) that extracts `creates`, `modifies`, and `exports` from §3 and any explicit Exports block; a public aggregator (`collect_prior_task_contracts`) that builds a per-task-number dict from the project's spec list; a formatter (`_format_contracts`) that renders the dict as a compact, prompt-ready `PRIOR-TASK CONTRACTS` block; and the two-line wire-up in `run_generation` that replaces the old truncation call with the new mechanism.

**Trade-offs considered:**
- **Increase the 60-line limit (e.g., to 300)** — rejected because it is still an approximation; a sufficiently long context window masks the deeper problem and grows token cost without giving the model structured, machine-verifiable information about file surfaces.
- **Pass the full prior task text untruncated** — rejected because it injects implementation detail noise (step narratives, code snippets, rollback text) that the model does not need. The model needs the declared file surface, not the full guide. Structured extraction gives exactly that at a fraction of the token cost.
- **Regex + markdown section conventions** — preferred because the task guide section structure is stable (§3 is always `Files`, subsections always `To Create` / `To Modify`) and the existing `re` module is already in use in `service.py`; no new dependency is introduced and the parser is pure and easily testable.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From {WORKSPACE}/spec-doc/api
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- modules/task_gen/service.py modules/implementation_guide/prompts.py \
    modules/task_gen/tests/test_service_helpers.py \
    modules/implementation_guide/tests/test_impl_guide_prompts.py \
    modules/implementation_guide/tests/__snapshots__/test_impl_guide_prompts_snapshots.ambr
make test                                     # Record baseline passing count
```

**If working tree is dirty on any target file**: stash or commit unrelated changes before starting.

**Baseline recorded**: ___/192 passing (record the actual count; the CLAUDE.md figure of 192 is the last known state).

---

## 3. Files

### To Create (new)
- `modules/task_gen/tests/test_contract_parser.py` — 14 unit tests for `_parse_task_contract`, `collect_prior_task_contracts`, and `_format_contracts`; no I/O, no Flask

### To Modify (cite CODEBASE CONTEXT)
- `modules/task_gen/service.py` — add `_FILES_SECTION_RE`, `_looks_like_path`, `_parse_task_contract`, `collect_prior_task_contracts`, `_format_contracts` after line 174 (`_task_sort_key`); update module docstring line 8; replace Step 7 body at lines 309–310 in `run_generation`
- `modules/implementation_guide/prompts.py` — change `"PRIOR TASKS"` → `"PRIOR-TASK CONTRACTS"` at line 65
- `modules/implementation_guide/tests/test_impl_guide_prompts.py` — update two functions: `buildPrompt_embedsPriorTasksSection_whenProvided` (line 124) and `buildPrompt_omitsPriorTasksSection_whenEmpty` (line 134)
- `modules/implementation_guide/tests/__snapshots__/test_impl_guide_prompts_snapshots.ambr` — regenerate (contains `## PRIOR TASKS` at line 31 which becomes `## PRIOR-TASK CONTRACTS`)

### To Leave Alone
- `modules/task_gen/service.py:collect_prior_task_content` (lines 177–195) — keep the function and its 60-line default intact; it has three passing tests in `test_service_helpers.py` and may be called by tools outside this task's scope. Simply stop calling it from `run_generation`.
- `modules/task_gen/tests/test_service_helpers.py` — all existing `collectPrior_*` tests cover `collect_prior_task_content` which is unchanged; do not touch
- `modules/task_gen/tests/test_routes.py` — integration tests use `CHAIN_PROVIDER=mock`; the seeded project has no prior task files so `collect_prior_task_contracts` returns `{}` and `_format_contracts({})` returns `""` — the prior block is omitted, which is already the behaviour at that fixture boundary
- `openapi.yaml` — no API surface change
- `dtos/models.py` — no DTO change

---

## 4. Implementation Steps

### Step 1: Add parser helpers to `service.py`

**Action**: Add one module-level compiled regex, three private helpers, and one public helper immediately after `_task_sort_key` (line 174). Also add `collect_prior_task_contracts(...)` to the module docstring's Public surface list (line 8).

**File**: `modules/task_gen/service.py`

**Pattern** (insert after line 174, before line 177 `def collect_prior_task_content`):

```python
_FILES_SECTION_RE = re.compile(
    r"^#{1,3}\s+(?:\d+\.\s+)?Files\b",
    re.MULTILINE | re.IGNORECASE,
)


def _looks_like_path(s: str) -> bool:
    """True if a backtick-quoted value looks like a file path, not a placeholder."""
    return "{" not in s and ("/" in s or bool(re.match(r"[\w\-]+\.\w{1,5}$", s)))


def _parse_task_contract(text: str) -> dict:
    """Extract declared file surfaces from §3 (Files) of a task guide.

    Parses 'To Create (new)' and 'To Modify' subsections, plus any
    standalone 'Exports' block anywhere in the document.

    Returns:
        creates: list[str] — backtick paths under 'To Create (new)'
        modifies: list[str] — backtick paths under 'To Modify'
        exports: list[str] — backtick paths under a standalone 'Exports' block
    """
    creates: list[str] = []
    modifies: list[str] = []
    exports: list[str] = []

    sec_m = _FILES_SECTION_RE.search(text)
    if not sec_m:
        return {"creates": creates, "modifies": modifies, "exports": exports}

    # Bound to the next H2 heading; search the tail after the section heading
    bound_m = re.search(r"^##\s+", text[sec_m.end():], re.MULTILINE)
    sec_end = sec_m.end() + bound_m.start() if bound_m else len(text)
    sec_text = text[sec_m.start():sec_end]

    sub_re = re.compile(r"^#{2,4}\s+To\s+(Create|Modify)", re.MULTILINE | re.IGNORECASE)
    sub_ms = list(sub_re.finditer(sec_text))
    for i, sub_m in enumerate(sub_ms):
        sub_end = sub_ms[i + 1].start() if i + 1 < len(sub_ms) else len(sec_text)
        sub_text = sec_text[sub_m.start():sub_end]
        label = sub_m.group(1).lower()  # 'create' or 'modify'
        for line in sub_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            for pm in re.finditer(r"`([^`]+)`", stripped):
                path = pm.group(1)
                if _looks_like_path(path):
                    (creates if label == "create" else modifies).append(path)

    # Optional standalone Exports block (may appear anywhere in the document)
    exp_m = re.search(r"^#{2,4}\s+Exports?\b", text, re.MULTILINE | re.IGNORECASE)
    if exp_m:
        exp_bound = re.search(r"^#{2,4}\s+", text[exp_m.end():], re.MULTILINE)
        exp_end = exp_m.end() + exp_bound.start() if exp_bound else len(text)
        exp_text = text[exp_m.start():exp_end]
        for line in exp_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            for pm in re.finditer(r"`([^`]+)`", stripped):
                if _looks_like_path(pm.group(1)):
                    exports.append(pm.group(1))

    return {"creates": creates, "modifies": modifies, "exports": exports}


def collect_prior_task_contracts(specs: list[dict], current_task_num: str) -> dict:
    """Parse file-surface contracts from all prior task guides.

    Returns a dict keyed by task number string in sort order:
        {"1": {"creates": [...], "modifies": [...], "exports": [...]}, ...}

    Only task-N-*.md files whose N sorts before current_task_num are included.
    """
    cur_key = _task_sort_key(current_task_num)
    pairs: list[tuple[tuple, str, str]] = []
    for spec in specs:
        m = _TASK_FILE_RE.match(spec.get("filename", ""))
        if not m:
            continue
        num = m.group(1)
        key = _task_sort_key(num)
        if key >= cur_key:
            continue
        pairs.append((key, num, spec.get("content") or ""))
    pairs.sort(key=lambda p: p[0])
    return {num: _parse_task_contract(content) for _, num, content in pairs}


def _format_contracts(contracts: dict) -> str:
    """Render prior-task contracts as a prompt-injectable string.

    Returns "" when contracts is empty or every entry declares no paths —
    PromptBuilder.section() will then omit the block entirely.
    """
    if not contracts:
        return ""
    lines: list[str] = [
        "The following files are already declared by prior tasks.",
        "Do NOT re-declare (new) files listed under Creates.",
        "",
    ]
    any_entry = False
    for task_num in sorted(contracts, key=_task_sort_key):
        c = contracts[task_num]
        creates = c.get("creates") or []
        modifies = c.get("modifies") or []
        exports_ = c.get("exports") or []
        if not creates and not modifies and not exports_:
            continue
        any_entry = True
        lines.append(f"## task-{task_num}")
        if creates:
            lines.append("**Creates (new)**: " + ", ".join(f"`{p}`" for p in creates))
        if modifies:
            lines.append("**Modifies**: " + ", ".join(f"`{p}`" for p in modifies))
        if exports_:
            lines.append("**Exports**: " + ", ".join(f"`{p}`" for p in exports_))
        lines.append("")
    return "\n".join(lines).strip() if any_entry else ""
```

**Module docstring update** — at line 8, add after `extract_task_desc(...)  — pure helper, unit-testable`:
```python
    collect_prior_task_contracts(...) — pure helper, unit-testable
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api && python -c "
from modules.task_gen.service import (
    _parse_task_contract, collect_prior_task_contracts, _format_contracts
)
print(_parse_task_contract('## 3. Files\n### To Create (new)\n- \`a/b.py\` — new\n'))
"
# expect: {'creates': ['a/b.py'], 'modifies': [], 'exports': []}
```

---

### Step 2: Wire `run_generation` Step 7 to use contracts

**Action**: In `run_generation`, replace lines 309–310 with the two-line contracts call. Keep the variable name `prior` so the existing `build_implementation_guide_prompt` call at line 310 (now 312) is unchanged.

**File**: `modules/task_gen/service.py`

**Pattern** (replace existing Step 7 block):
```python
        # Step 7: collect prior task contracts (structured file declarations)
        contracts = collect_prior_task_contracts(specs, task["num"])
        prior = _format_contracts(contracts)
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api && python -c "
import json
from pathlib import Path
# Confirm run_generation imports still resolve — no circular dep
from modules.task_gen import service
print('run_generation OK')
"
```

---

### Step 3: Rename the prompt section label and update dependent tests + snapshot

**Action A**: In `prompts.py` line 65, change the section heading string from `"PRIOR TASKS"` to `"PRIOR-TASK CONTRACTS"`.

**File**: `modules/implementation_guide/prompts.py`

**Pattern**:
```python
        .section("PRIOR-TASK CONTRACTS", prior)
```

**Action B**: In `test_impl_guide_prompts.py`, update the two functions that assert the section heading (lines 124–131 and 134–140):

```python
def buildPrompt_embedsPriorTasksSection_whenProvided():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        prior="### task-1-unify.md\nPrior task content.",
    )
    assert "PRIOR-TASK CONTRACTS" in user   # was "PRIOR TASKS"
    assert "Prior task content." in user


def buildPrompt_omitsPriorTasksSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        prior="",
    )
    assert "PRIOR-TASK CONTRACTS" not in user   # was "PRIOR TASKS"
```

**Action C**: Regenerate the syrupy snapshot (it contains `## PRIOR TASKS` at line 31 of the `.ambr` file):

```bash
cd {WORKSPACE}/spec-doc/api && pytest -m snapshot --snapshot-update
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api && grep "PRIOR-TASK CONTRACTS" \
    modules/implementation_guide/tests/__snapshots__/test_impl_guide_prompts_snapshots.ambr
# expect: one match on the line that previously read "## PRIOR TASKS"

pytest modules/implementation_guide/tests/ -v
# expect: all tests pass (property tests + snapshot tests)
```

---

### Step 4: Create `test_contract_parser.py`

**Action**: Create the new test file. No existing file to read first — this is a new path.

**File**: `modules/task_gen/tests/test_contract_parser.py` (new)

**Pattern**: see §5 Tests below — paste the full body verbatim.

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api && pytest modules/task_gen/tests/test_contract_parser.py -v
# expect: 14 passed, 0 failed
```

---

## 5. Tests

Complete assertion bodies. Framework: pytest with `python_functions = ["test_*", "*_*"]` — camelCase underscore-separated function names are collected.

```python
# modules/task_gen/tests/test_contract_parser.py
"""Unit tests for the contract parser in modules.task_gen.service.

Covers _parse_task_contract(), collect_prior_task_contracts(), and
_format_contracts(). No threads, no Flask, no I/O.
"""
from modules.task_gen import service as _svc

parseContract = _svc._parse_task_contract
collectContracts = _svc.collect_prior_task_contracts
formatContracts = _svc._format_contracts

# ---------------------------------------------------------------------------
# Shared fixture text
# ---------------------------------------------------------------------------

_FULL_SECTION_THREE = """\
## 3. Files

### To Create (new)
- `modules/quality/lint.py` — pre-emit linter; no existing deps
- `modules/quality/__init__.py` — package init

### To Modify (cite CODEBASE CONTEXT)
- `modules/task_gen/service.py` — add contract parser calls

### To Leave Alone
- `modules/chain/adapter.py` — unchanged

## 4. Implementation Steps

Step content here.
"""

# ---------------------------------------------------------------------------
# _parse_task_contract
# ---------------------------------------------------------------------------

def parseContract_fullSectionThree_extractsCreatesAndModifies():
    result = parseContract(_FULL_SECTION_THREE)
    assert result["creates"] == [
        "modules/quality/lint.py",
        "modules/quality/__init__.py",
    ], "expected both (new) paths extracted in order"
    assert result["modifies"] == [
        "modules/task_gen/service.py",
    ], "expected single modify path extracted"
    assert result["exports"] == [], "no exports block present"


def parseContract_noFilesSectionInDoc_returnsEmptyLists():
    doc = (
        "# Task\n\n"
        "## 1. Context\n\nSome context.\n\n"
        "## 2. Pre-flight\n\nSome pre-flight.\n"
    )
    result = parseContract(doc)
    assert result == {"creates": [], "modifies": [], "exports": []}, (
        "document with no Files section must return all-empty lists"
    )


def parseContract_multiplePaths_inCreateSubsection_allExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Create (new)\n"
        "- `modules/quality/lint.py` — linter\n"
        "- `modules/quality/coherence.py` — coherence pass\n"
        "- `modules/quality/__init__.py` — package init\n"
    )
    result = parseContract(doc)
    assert result["creates"] == [
        "modules/quality/lint.py",
        "modules/quality/coherence.py",
        "modules/quality/__init__.py",
    ], "all three (new) paths must appear in order"


def parseContract_multiplePaths_inModifySubsection_allExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Modify (cite CODEBASE CONTEXT)\n"
        "- `modules/task_gen/service.py` — add contracts\n"
        "- `modules/implementation_guide/prompts.py` — rename section\n"
    )
    result = parseContract(doc)
    assert result["modifies"] == [
        "modules/task_gen/service.py",
        "modules/implementation_guide/prompts.py",
    ], "both modify paths must appear in order"


def parseContract_placeholderPaths_notExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Create (new)\n"
        "- `{workspace-relative-path}` — placeholder, not a real path\n"
    )
    result = parseContract(doc)
    assert result["creates"] == [], (
        "template placeholder containing '{' must be excluded from creates"
    )


def parseContract_exportsBlockPresent_exportsExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Create (new)\n"
        "- `modules/quality/lint.py` — linter\n\n"
        "## Exports\n\n"
        "- `modules/quality/lint.py` — lint_task_guide, Flag\n"
    )
    result = parseContract(doc)
    assert "modules/quality/lint.py" in result["exports"], (
        "path from Exports block must appear in exports list"
    )


def parseContract_onlyLeaveAloneSubsection_noCreatesOrModifies():
    doc = (
        "## 3. Files\n\n"
        "### To Leave Alone\n"
        "- `modules/chain/adapter.py` — no changes needed\n"
    )
    result = parseContract(doc)
    assert result["creates"] == [], "To Leave Alone must not populate creates"
    assert result["modifies"] == [], "To Leave Alone must not populate modifies"


# ---------------------------------------------------------------------------
# collect_prior_task_contracts
# ---------------------------------------------------------------------------

def collectContracts_multiplePriorTasks_dictKeyedByTaskNum():
    specs = [
        {"filename": "epic.md", "content": "ignore"},
        {"filename": "task-1-alpha.md", "content": _FULL_SECTION_THREE},
        {
            "filename": "task-2-beta.md",
            "content": (
                "## 3. Files\n\n"
                "### To Create (new)\n"
                "- `modules/new/thing.py` — new module\n"
            ),
        },
        {"filename": "task-3-gamma.md", "content": "not yet reached"},
    ]
    result = collectContracts(specs, current_task_num="3")
    assert set(result.keys()) == {"1", "2"}, (
        "only tasks 1 and 2 sort before current_task_num=3"
    )
    assert "modules/quality/lint.py" in result["1"]["creates"]
    assert "modules/new/thing.py" in result["2"]["creates"]


def collectContracts_noEarlierTasks_returnsEmptyDict():
    specs = [{"filename": "task-2-beta.md", "content": _FULL_SECTION_THREE}]
    result = collectContracts(specs, current_task_num="1")
    assert result == {}, "no task file sorts before task 1"


def collectContracts_currentTaskNotIncluded():
    specs = [
        {"filename": "task-1-alpha.md", "content": _FULL_SECTION_THREE},
        {
            "filename": "task-2-beta.md",
            "content": (
                "## 3. Files\n\n"
                "### To Create (new)\n"
                "- `x/y.py` — new\n"
            ),
        },
    ]
    result = collectContracts(specs, current_task_num="2")
    assert "2" not in result, "current task must be excluded even when its file is present"
    assert "1" in result, "prior task 1 must appear"


def collectContracts_priorTaskWithNoFileSection_emptyContractForThatTask():
    specs = [
        {"filename": "task-1-alpha.md", "content": "# Context only\nNo files section."}
    ]
    result = collectContracts(specs, current_task_num="2")
    assert result["1"] == {"creates": [], "modifies": [], "exports": []}, (
        "task with no §3 must produce an all-empty contract, not raise"
    )


# ---------------------------------------------------------------------------
# _format_contracts
# ---------------------------------------------------------------------------

def formatContracts_emptyDict_returnsEmptyString():
    assert formatContracts({}) == "", "empty dict must produce empty string"


def formatContracts_allEmptyContracts_returnsEmptyString():
    contracts = {"1": {"creates": [], "modifies": [], "exports": []}}
    assert formatContracts(contracts) == "", (
        "task with no declared paths must produce empty string "
        "so PromptBuilder.section() omits the block"
    )


def formatContracts_taskWithCreatesAndModifies_containsCorrectContent():
    contracts = {
        "1": {
            "creates": ["modules/quality/lint.py", "modules/quality/__init__.py"],
            "modifies": ["modules/task_gen/service.py"],
            "exports": [],
        }
    }
    out = formatContracts(contracts)
    assert "task-1" in out, "task header must appear"
    assert "modules/quality/lint.py" in out, "create path must appear"
    assert "modules/task_gen/service.py" in out, "modify path must appear"
    assert "Do NOT re-declare" in out, "instruction line must appear"
```

---

## 6. Commit Plan

**Executor instruction**: run each commit immediately after completing the corresponding step — do not batch at the end.

1. **`feat(task_gen): add _parse_task_contract, collect_prior_task_contracts, _format_contracts`** — after Step 1 — `modules/task_gen/service.py`: new helpers + module docstring update. No behaviour change yet.

2. **`feat(task_gen): wire run_generation step 7 to use contract parser`** — after Step 2 — `modules/task_gen/service.py`: step 7 body only (two lines). `collect_prior_task_content` remains in the file but is no longer called from `run_generation`.

3. **`feat(impl_guide): rename PRIOR TASKS section to PRIOR-TASK CONTRACTS`** — after Step 3 — `modules/implementation_guide/prompts.py` (one string change), `modules/implementation_guide/tests/test_impl_guide_prompts.py` (two assertion updates), `modules/implementation_guide/tests/__snapshots__/test_impl_guide_prompts_snapshots.ambr` (regenerated).

4. **`test(task_gen): add contract parser unit tests`** — after Step 4 + tests pass — `modules/task_gen/tests/test_contract_parser.py` (new, 14 tests).

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api && make test
```

**Expected delta**: N → N+14 passing (where N is the baseline recorded in pre-flight). Zero pre-existing tests broken. The two updated tests in `test_impl_guide_prompts.py` are not new tests — they are the same tests with corrected assertions, so they count toward the zero-broken requirement, not the +14 delta.

**Spot-check the section rename end-to-end**:
```bash
python -c "
from modules.implementation_guide.prompts import build_implementation_guide_prompt
_, user = build_implementation_guide_prompt(
    task_num='2', task_name='T', task_effort='1d', task_desc='desc', arch='arch',
    prior='## task-1\n**Creates (new)**: \`modules/quality/lint.py\`',
)
assert 'PRIOR-TASK CONTRACTS' in user
assert 'PRIOR TASKS' not in user
print('section rename verified')
"
```

**Spot-check the round-trip through run_generation** (uses mock provider, no real AI call):
```bash
pytest modules/task_gen/tests/test_routes.py -v
# All existing route tests must pass unchanged
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. Revert in reverse order if multiple steps have been applied (Step 4 → 3 → 2 → 1). The snapshot revert restores the `.ambr` file to its pre-task state.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch, or `git branch -D <branch>` if it has not been merged. The pre-task SHA is the HEAD recorded during pre-flight.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag in commit body and do not invent.
- **Test framework mismatch** → match the repo's convention (`python_functions = ["test_*", "*_*"]`, no class required for new file); translate silently and note in commit body.
- **`_FILES_SECTION_RE` fails to match a real task guide's section heading** → widen the heading regex (e.g., relax the number prefix from `\d+\.` to `\d[\d.]*\.`) and log the mismatch in the commit body. Do NOT change the section heading in the task guide template — the parser adapts to the document, not vice versa.
- **Snapshot regeneration produces unexpected diff beyond the `PRIOR TASKS` → `PRIOR-TASK CONTRACTS` change** → STOP, inspect the diff, and confirm no other prompt content changed. If something else changed, investigate the cause before committing the regenerated snapshot.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit body.

---

## 10. Out of Scope

This task is a one-bug fix with a tightly bounded scope: replace the 60-line truncation with a structured contract parser, wire it into `run_generation`, and rename the prompt section to match. The following work is explicitly deferred and must not be absorbed even if the implementation appears to invite it.

- **Lint rule #8 (section-count check in `modules/quality/lint.py`)** — the quality module does not yet exist; it is Task N in the epic. The contract parser's dependence on §3's position is a coordination requirement that Task N must document, but implementing the linter is out of scope here.
- **`collect_prior_task_content` removal** — the function has passing tests and may be referenced by exploratory tooling outside this repo. Deleting it is a separate clean-up task; the function being present but uncalled from `run_generation` is not a correctness defect.
- **Exports block in the impl-guide template** — the architecture mentions an optional Exports section; this task parses it if present but does not add it to the template. Adding it to the template is a prompt-template change deferred to a follow-up.
- **Attribution injector (`EXECUTOR_ATTRIBUTION`)** — described in the architecture as a companion change to this one but scoped to a separate task. Do not add it here.
- **Angular coherence badge or `POST /coherence` endpoint** — post-task, separate scope.
- **`post_generateTask_specifiesTaskNum_generatesCorrectTask`** — a route test for the explicit `task_num` code path is useful but not required by this task's contract; add it in a test-hardening follow-up if the route test coverage gap is flagged.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for structured extraction vs. raw truncation
- [Epic](./epic.md) – Task scope and sequencing
- [Timeline](./timeline.md) – Status tracking (mark Task 1 done after verification passes)