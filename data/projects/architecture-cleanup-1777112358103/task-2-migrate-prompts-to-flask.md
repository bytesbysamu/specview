Now I have everything I need. Let me write the guide.

# Task 2: Migrate Prompts to Flask

## 1. Context

`_build_impl_prompt()` in `modules/projects/routes.py` (lines 114–155) is already a working Python port of the Angular `buildImplementationGuidePrompt()` — but it is an **inline private function** inside a route file, it reads context files itself, and it returns a raw string rather than `(system, user)`. Meanwhile `generate_spec_prompt()`, `review_prompt()`, and `lint_braindump_prompt()` in `modules/ai/prompts/__init__.py` each do their own ad-hoc string concatenation with no shared building primitive.

This task:
1. Creates `modules/ai/prompts/builder.py` — a `PromptBuilder` class (fluent, pure, no I/O).
2. Refactors `generate_spec_prompt`, `review_prompt`, and `lint_braindump_prompt` in `__init__.py` to use it.
3. Creates `modules/implementation_guide/` (new module) with `prompts.py` containing `build_implementation_guide_prompt()` returning `(system, user)`.
4. Refactors `_build_impl_prompt` in `modules/projects/routes.py` to delegate to the new function.
5. Adds snapshot tests for `build_implementation_guide_prompt` sections.
6. Adds a structural test: no prompt string literals (`"You are `) in route handler files.

**No Angular changes in this task.** The Angular `implementation-guide.service.ts` still calls `POST /api/projects/<id>/generate-task`. The Flask route's behaviour is identical post-refactor; only the internal plumbing changes.

**Snapshot impact:** `generate_spec_prompt`, `review_prompt`, `lint_braindump_prompt` snapshots must remain byte-identical after refactor. Run `pytest -m snapshot` before and after to confirm. If any golden breaks, the refactor changed output — fix the builder before proceeding.

---

## 2. Pre-flight

```bash
cd /workspace/api

# Suite must be green
make test
# Expected: all tests pass, 0 failures

# Pin current snapshot output so refactor can be validated against it
pytest -m snapshot -v
# Expected: 7 snapshot tests pass (TestRewritePromptSnapshot through TestScanPromptSnapshot)

# Confirm _build_impl_prompt lives in projects/routes.py
grep -n "_build_impl_prompt\|build_implementation_guide_prompt" modules/projects/routes.py
# Expected:
# 114:def _build_impl_prompt(task: dict, epic: str, arch: str, prior: str) -> str:
# 200:        prompt = _build_impl_prompt(next_task, epic, arch, prior)

# Confirm implementation_guide module does NOT exist yet
ls modules/ | grep implementation
# Expected: (no output)

# Confirm builder.py does NOT exist yet
ls modules/ai/prompts/
# Expected: __init__.py only (no builder.py)
```

---

## 3. Files

| Path | Status | Purpose |
|------|--------|---------|
| `modules/ai/prompts/builder.py` | **new** | `PromptBuilder` class — fluent section assembler |
| `modules/ai/prompts/__init__.py` | modify | Refactor `generate_spec_prompt`, `review_prompt`, `lint_braindump_prompt` to use `PromptBuilder` |
| `modules/implementation_guide/__init__.py` | **new** | Empty package marker |
| `modules/implementation_guide/prompts.py` | **new** | `build_implementation_guide_prompt()` returning `(system, user)` |
| `modules/implementation_guide/tests/__init__.py` | **new** | Empty test package marker |
| `modules/implementation_guide/tests/test_impl_guide_prompts.py` | **new** | Unit tests for `build_implementation_guide_prompt` |
| `modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py` | **new** | Syrupy snapshot tests — pin each context section |
| `modules/implementation_guide/tests/__snapshots__/` | **new** (auto-created) | Syrupy golden directory — created on first `--snapshot-update` |
| `modules/projects/routes.py` | modify | `_build_impl_prompt` delegates to `build_implementation_guide_prompt`; route call updated to unpack `(system, user)` |
| `tests/test_structural.py` | **new** | Structural test: no `"You are ` in route handler files |

---

## 4. Implementation Steps

### Step 1 — Create `modules/ai/prompts/builder.py`

Create the file. No existing file to modify:

```python
# modules/ai/prompts/builder.py
"""Fluent prompt assembler.

PromptBuilder accumulates named sections and joins them in declaration order.
No I/O. No side effects. Call build() to get the final string.

Usage:
    system = (
        PromptBuilder("You are a spec writer.")
        .section("Builder Profile", builder_ctx)
        .section("Principles", principles_ctx)
        .build()
    )
"""
from __future__ import annotations


class PromptBuilder:
    """Accumulate prompt sections and produce a plain string via build()."""

    def __init__(self, base: str = "") -> None:
        self._parts: list[str] = [base] if base else []

    def section(self, heading: str, content: str) -> "PromptBuilder":
        """Append ``## heading\\ncontent`` block. No-op when content is blank."""
        if content and content.strip():
            self._parts.append(f"\n\n## {heading}\n{content}")
        return self

    def raw(self, text: str) -> "PromptBuilder":
        """Append raw text without a heading wrapper. No-op when text is empty."""
        if text:
            self._parts.append(text)
        return self

    def build(self) -> str:
        """Return the assembled string."""
        return "".join(self._parts)
```

### Step 2 — Refactor `modules/ai/prompts/__init__.py`

Add the import at the top of the file (after the docstring, before the `# ── rewrite` comment):

```python
from modules.ai.prompts.builder import PromptBuilder
```

Replace `generate_spec_prompt` (lines 69–72 of the current file):

**Before:**
```python
def generate_spec_prompt(input_text: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    return _GENERATE_SPEC_BASE + ctx, input_text
```

**After:**
```python
def generate_spec_prompt(input_text: str, builder: str, principles: str) -> tuple[str, str]:
    system = (
        PromptBuilder(_GENERATE_SPEC_BASE)
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .build()
    )
    return system, input_text
```

Replace `review_prompt` (lines 86–88):

**Before:**
```python
def review_prompt(documents: dict) -> tuple[str, str]:
    body = "\n\n".join(f"## {k}\n{v}" for k, v in documents.items())
    return _REVIEW_SYSTEM, body
```

**After:**
```python
def review_prompt(documents: dict) -> tuple[str, str]:
    user = PromptBuilder().raw(
        "\n\n".join(f"## {k}\n{v}" for k, v in documents.items())
    ).build()
    return _REVIEW_SYSTEM, user
```

Replace `lint_braindump_prompt` (lines 100–101):

**Before:**
```python
def lint_braindump_prompt(braindump: str) -> tuple[str, str]:
    return _LINT_SYSTEM, braindump
```

**After:**
```python
def lint_braindump_prompt(braindump: str) -> tuple[str, str]:
    return _LINT_SYSTEM, PromptBuilder().raw(braindump).build()
```

> **Snapshot check** — run immediately after this step before touching anything else:
> ```bash
> pytest -m snapshot -v
> # All 7 must still pass. If any fail, the builder changed output — fix before continuing.
> ```

### Step 3 — Create `modules/implementation_guide/` package

```bash
mkdir -p /workspace/api/modules/implementation_guide/tests/__snapshots__
touch /workspace/api/modules/implementation_guide/__init__.py
touch /workspace/api/modules/implementation_guide/tests/__init__.py
```

### Step 4 — Create `modules/implementation_guide/prompts.py`

```python
# modules/implementation_guide/prompts.py
"""Prompt constructor for implementation guide generation.

build_implementation_guide_prompt() is the sole public export.
No I/O. No imports from modules.context — callers supply pre-loaded strings.
"""
from __future__ import annotations

from modules.ai.prompts.builder import PromptBuilder

_SYSTEM = "You are a senior engineer writing executor-ready implementation guides."

_USER_HEADER = """\
## Your ONE Job
Produce an executor-ready implementation guide. Every path must be real or \
marked "(new)". Every test must have a complete assertion body. Every step \
must be verifiable.

## Required Sections (in order)
1. Context  2. Pre-flight  3. Files  4. Implementation Steps  5. Tests
6. Commit Plan  7. Verification  8. Rollback  9. Deviations Allowed  10. Out of Scope

## Hard Rules
- NO absolute personal paths. Use {WORKSPACE} or workspace-relative paths.
- NO test stubs. Match the repo's test framework.
- Your entire response MUST begin with `#`. No preamble.\
"""


def build_implementation_guide_prompt(
    *,
    task_num: str,
    task_name: str,
    task_effort: str,
    task_desc: str,
    arch: str,
    builder: str = "",
    principles: str = "",
    codebase: str = "",
    references: str = "",
    prior: str = "",
) -> tuple[str, str]:
    """Return (system, user) for implementation guide generation.

    All context strings are caller-supplied; this function performs no I/O.

    Args:
        task_num:     Task number string, e.g. "2".
        task_name:    Task name from the epic table, e.g. "Migrate Prompts to Flask".
        task_effort:  Effort string from the epic table, e.g. "1.5 days".
        task_desc:    ### Task N: ... block extracted from epic.md.
        arch:         Full architecture.md content.
        builder:      Builder profile context (optional).
        principles:   Architecture principles context (optional).
        codebase:     Codebase context (optional).
        references:   Reference code context (optional).
        prior:        Concatenated prior task guide content (optional).
    """
    user = (
        PromptBuilder(_USER_HEADER)
        .section("BUILDER CONTEXT", builder)
        .section("ARCHITECTURE PRINCIPLES", principles)
        .section("CODEBASE CONTEXT", codebase)
        .section("REFERENCE CODE", references)
        .section("PRIOR TASKS", prior)
        .raw(f"\n\n---\n\n# Task {task_num}: {task_name}\n\n**Effort**: {task_effort}\n\n")
        .raw(f"CONTEXT FROM EPIC:\n{task_desc}\n\n")
        .raw(f"CONTEXT FROM ARCHITECTURE:\n{arch}\n\n")
        .raw("Generate a concrete, executor-ready implementation guide for this task.")
        .build()
    )
    return _SYSTEM, user
```

### Step 5 — Refactor `_build_impl_prompt` in `modules/projects/routes.py`

The existing `_build_impl_prompt` function (lines 114–155) reads context internally and returns a raw string. After refactoring it will read context, call `build_implementation_guide_prompt`, and return `(system, user)`.

**Add import** at the top of `modules/projects/routes.py` alongside the existing imports:

```python
from modules.implementation_guide.prompts import build_implementation_guide_prompt
```

**Replace `_build_impl_prompt`** (lines 114–155):

**Before:**
```python
def _build_impl_prompt(task: dict, epic: str, arch: str, prior: str) -> str:
    """Port of ImplementationGuideService.buildImplementationGuidePrompt()."""
    builder    = read_context("builder")
    principles = read_context("principles")
    codebase   = read_context("codebase")
    references = read_context("references")
    task_desc  = _extract_task_desc(epic, task["num"])

    blocks = ""
    if builder:    blocks += f"\n## BUILDER CONTEXT\n{builder}\n"
    if principles: blocks += f"\n## ARCHITECTURE PRINCIPLES\n{principles}\n"
    if codebase:   blocks += f"\n## CODEBASE CONTEXT\n{codebase}\n"
    if references: blocks += f"\n## REFERENCE CODE\n{references}\n"
    if prior:      blocks += f"\n## PRIOR TASKS\n{prior}\n"

    return f"""You are generating an **Implementation** guide for a task.
{blocks}
## Your ONE Job
Produce an executor-ready implementation guide. Every path must be real or marked "(new)". Every test must have a complete assertion body. Every step must be verifiable.

## Required Sections (in order)
1. Context  2. Pre-flight  3. Files  4. Implementation Steps  5. Tests
6. Commit Plan  7. Verification  8. Rollback  9. Deviations Allowed  10. Out of Scope

## Hard Rules
- NO absolute personal paths. Use {{WORKSPACE}} or workspace-relative paths.
- NO test stubs. Match the repo's test framework.
- Your entire response MUST begin with `#`. No preamble.

---

# Task {task["num"]}: {task["name"]}

**Effort**: {task["effort"]}

CONTEXT FROM EPIC:
{task_desc}

CONTEXT FROM ARCHITECTURE:
{arch}

Generate a concrete, executor-ready implementation guide for this task."""
```

**After:**
```python
def _build_impl_prompt(task: dict, epic: str, arch: str, prior: str) -> tuple[str, str]:
    """Assemble implementation guide prompt via build_implementation_guide_prompt()."""
    return build_implementation_guide_prompt(
        task_num=task["num"],
        task_name=task["name"],
        task_effort=task["effort"],
        task_desc=_extract_task_desc(epic, task["num"]),
        arch=arch,
        builder=read_context("builder"),
        principles=read_context("principles"),
        codebase=read_context("codebase"),
        references=read_context("references"),
        prior=prior,
    )
```

**Update the call site** in `_run_generate_task` (line 200–206):

**Before:**
```python
        prompt = _build_impl_prompt(next_task, epic, arch, prior)

        result = chain_adapter.generate(
            "You are a senior engineer writing executor-ready implementation guides.",
            prompt,
            max_tokens=8192,
        )
```

**After:**
```python
        system, prompt = _build_impl_prompt(next_task, epic, arch, prior)

        result = chain_adapter.generate(
            system,
            prompt,
            max_tokens=8192,
        )
```

### Step 6 — Add structural test `tests/test_structural.py`

```python
# tests/test_structural.py
"""Structural invariants as tests.

These tests encode architecture rules that are easy to violate silently.
Each is one grep + one assertion + one failure message naming the rule and fix.
"""
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


def _route_files() -> list[Path]:
    """All route handler files in modules/."""
    return list((_REPO_ROOT / "modules").rglob("routes.py"))


def noPromptStrings_inRouteHandlers():
    """Route handler files must not contain inline prompt string literals.

    Rule: prompt construction belongs in modules/*/prompts.py, not in routes.py.
    Fix:  Move the prompt string into the appropriate prompts module and import
          the function into the route file.
    """
    violations = []
    for path in _route_files():
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if '"You are ' in line or "'You are " in line:
                violations.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: {line.strip()}")

    assert not violations, (
        "Route files must not contain inline prompt strings ('You are ...').\n"
        "Move prompt construction to the module's prompts.py:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
```

---

## 5. Tests

All tests live inside the module they test — `modules/implementation_guide/tests/`. Use the same no-underscore alias pattern as `test_prompts.py` to avoid double-collection under `python_functions = ["test_*", "*_*"]`.

### `modules/implementation_guide/tests/test_impl_guide_prompts.py`

```python
# modules/implementation_guide/tests/test_impl_guide_prompts.py
"""Unit tests for build_implementation_guide_prompt().

No I/O. No snapshots. Fast property assertions only.
"""
from modules.implementation_guide.prompts import build_implementation_guide_prompt

buildPrompt = build_implementation_guide_prompt


def buildPrompt_returnsSystemUserTuple():
    result = buildPrompt(
        task_num="1", task_name="Unify Context Services",
        task_effort="1 day", task_desc="### Task 1: details",
        arch="# Architecture", builder="", principles="", codebase="", references="", prior="",
    )
    assert isinstance(result, tuple)
    assert len(result) == 2


def buildPrompt_systemIsSeniorEngineerRole():
    system, _ = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
    )
    assert "senior engineer" in system
    assert "You are" in system


def buildPrompt_userContainsTaskNumAndName():
    _, user = buildPrompt(
        task_num="3", task_name="Extract Template Generators",
        task_effort="0.5 days", task_desc="desc", arch="arch",
    )
    assert "Task 3:" in user
    assert "Extract Template Generators" in user


def buildPrompt_userContainsEffort():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1.5 days",
        task_desc="desc", arch="arch",
    )
    assert "1.5 days" in user


def buildPrompt_userContainsRequiredSectionsHeader():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
    )
    assert "Required Sections" in user
    assert "Implementation Steps" in user


def buildPrompt_userContainsHardRules():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
    )
    assert "{WORKSPACE}" in user
    assert "NO test stubs" in user


def buildPrompt_embedsBuilderSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="I ship fast.",
    )
    assert "BUILDER CONTEXT" in user
    assert "I ship fast." in user


def buildPrompt_omitsBuilderSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="",
    )
    assert "BUILDER CONTEXT" not in user


def buildPrompt_embedsPrinciplesSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        principles="Ship fast, validate first.",
    )
    assert "ARCHITECTURE PRINCIPLES" in user
    assert "Ship fast, validate first." in user


def buildPrompt_omitsPrinciplesSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        principles="",
    )
    assert "ARCHITECTURE PRINCIPLES" not in user


def buildPrompt_embedsCodebaseSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        codebase="src/main.py",
    )
    assert "CODEBASE CONTEXT" in user
    assert "src/main.py" in user


def buildPrompt_embedsReferencesSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        references="# Reference\nExample code.",
    )
    assert "REFERENCE CODE" in user
    assert "Example code." in user


def buildPrompt_embedsPriorTasksSection_whenProvided():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        prior="### task-1-unify.md\nPrior task content.",
    )
    assert "PRIOR TASKS" in user
    assert "Prior task content." in user


def buildPrompt_omitsPriorTasksSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        prior="",
    )
    assert "PRIOR TASKS" not in user


def buildPrompt_embedsArchInUser():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc",
        arch="## Architecture Overview\nFluent builder pattern.",
    )
    assert "CONTEXT FROM ARCHITECTURE" in user
    assert "Fluent builder pattern." in user


def buildPrompt_embedsTaskDescInUser():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1d",
        task_desc="### Task 2: Migrate Prompts\nCreate PromptBuilder.",
        arch="arch",
    )
    assert "CONTEXT FROM EPIC" in user
    assert "Create PromptBuilder." in user


def buildPrompt_allContextPresent_sectionsInCorrectOrder():
    """Context sections appear before the task header."""
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="builder text",
        prior="prior text",
    )
    builder_pos = user.index("builder text")
    prior_pos   = user.index("prior text")
    task_pos    = user.index("# Task 1:")
    assert builder_pos < task_pos, "BUILDER CONTEXT must appear before task header"
    assert prior_pos   < task_pos, "PRIOR TASKS must appear before task header"
```

### `modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py`

```python
# modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py
"""Snapshot tests for build_implementation_guide_prompt().

Run:    pytest -m snapshot
Update: pytest -m snapshot --snapshot-update

Pin the full (system, user) tuple for a representative call. Any future change
to the prompt wording produces a visible, attributable diff against the golden.
"""
import pytest

from modules.implementation_guide.prompts import build_implementation_guide_prompt

# Stable minimal inputs — deliberately small; only enough to exercise all sections.
_TASK_NUM    = "2"
_TASK_NAME   = "Migrate Prompts to Flask"
_TASK_EFFORT = "1.5 days"
_TASK_DESC   = "### Task 2: Migrate Prompts to Flask\nCreate PromptBuilder class."
_ARCH        = "## Architecture Overview\nBuilder pattern for prompts."
_BUILDER     = "I am a solo founder shipping fast."
_PRINCIPLES  = "Ship fast, validate first."
_CODEBASE    = "modules/ai/prompts/__init__.py"
_REFERENCES  = "# Reference\nExisting prompt functions."
_PRIOR       = "### task-1-unify-context-services.md\nContext unified."


class TestBuildImplementationGuidePromptSnapshot:
    @pytest.mark.snapshot
    def test_allSections_returnsStablePrompt(self, snapshot):
        assert build_implementation_guide_prompt(
            task_num=_TASK_NUM,
            task_name=_TASK_NAME,
            task_effort=_TASK_EFFORT,
            task_desc=_TASK_DESC,
            arch=_ARCH,
            builder=_BUILDER,
            principles=_PRINCIPLES,
            codebase=_CODEBASE,
            references=_REFERENCES,
            prior=_PRIOR,
        ) == snapshot

    @pytest.mark.snapshot
    def test_noOptionalContext_returnsStablePrompt(self, snapshot):
        assert build_implementation_guide_prompt(
            task_num=_TASK_NUM,
            task_name=_TASK_NAME,
            task_effort=_TASK_EFFORT,
            task_desc=_TASK_DESC,
            arch=_ARCH,
        ) == snapshot
```

> **Generate golden files** after writing all tests:
> ```bash
> pytest -m snapshot --snapshot-update \
>   modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py -v
> # Creates: modules/implementation_guide/tests/__snapshots__/test_impl_guide_prompts_snapshots.ambr
> ```

---

## 6. Commit Plan

Two commits. Keep the builder extraction and the route refactor separate so bisect is useful. **No `git push`, no `gh pr create`** — the container has no `ssh` and no `gh`. Commit on a feature branch off `master`; the user pushes and opens the PR separately.

**Commit 1 — `PromptBuilder` class + `__init__.py` refactor + existing snapshot confirmation**

Staged files:
```
modules/ai/prompts/builder.py                          (new)
modules/ai/prompts/__init__.py                         (modified)
```

Verify snapshots are still green before staging:
```bash
pytest -m snapshot -v    # must pass without --snapshot-update
```

Message:
```
refactor(prompts): introduce PromptBuilder; refactor generate_spec/review/lint_braindump
```

**Commit 2 — `implementation_guide` module + route refactor + new tests + structural test**

Staged files:
```
modules/implementation_guide/__init__.py                                    (new)
modules/implementation_guide/prompts.py                                     (new)
modules/implementation_guide/tests/__init__.py                              (new)
modules/implementation_guide/tests/test_impl_guide_prompts.py               (new)
modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py     (new)
modules/implementation_guide/tests/__snapshots__/test_impl_guide_prompts_snapshots.ambr  (new)
modules/projects/routes.py                                                  (modified)
tests/test_structural.py                                                    (new)
```

Message:
```
feat(implementation-guide): extract build_implementation_guide_prompt; add structural test
```

---

## 7. Verification

```bash
cd /workspace/api

# 1. Full suite green
make test
# Expected: all tests pass, 0 failures

# 2. Existing snapshots unchanged (no golden drift from __init__.py refactor)
pytest -m snapshot -v
# Expected: all 9 snapshot tests pass
#   (7 existing + 2 new implementation_guide snapshots)

# 3. Unit tests for new module
pytest modules/implementation_guide/tests/test_impl_guide_prompts.py -v
# Expected: 17 tests pass

# 4. Structural test passes
pytest tests/test_structural.py -v
# Expected: noPromptStrings_inRouteHandlers PASSED

# 5. Builder imported correctly from prompts package
python -c "
from modules.ai.prompts.builder import PromptBuilder
result = PromptBuilder('base').section('X', 'content').section('Y', '').build()
assert result == 'base\n\n## X\ncontent', repr(result)
print('PromptBuilder: OK')
"

# 6. build_implementation_guide_prompt returns correct tuple shape
python -c "
from modules.implementation_guide.prompts import build_implementation_guide_prompt
system, user = build_implementation_guide_prompt(
    task_num='1', task_name='Test', task_effort='1d',
    task_desc='desc', arch='arch', builder='B',
)
assert 'senior engineer' in system
assert 'BUILDER CONTEXT' in user
assert '# Task 1: Test' in user
print('build_implementation_guide_prompt: OK')
"

# 7. projects route still loads cleanly
python -c "
from create_app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
assert any('generate-task' in r for r in rules), 'generate-task route missing'
print('projects route: OK')
"

# 8. Lint
make lint
# Expected: 0 errors
```

---

## 8. Rollback

No schema changes. No new routes registered. No database migrations. Rollback is a single revert:

```bash
# Revert everything to pre-task state
git revert HEAD~1 HEAD   # reverts both commits in reverse order

# Or, if not yet committed:
git checkout -- modules/ai/prompts/__init__.py
git checkout -- modules/projects/routes.py
rm -rf modules/ai/prompts/builder.py
rm -rf modules/implementation_guide/
rm -f tests/test_structural.py
```

The Flask application remains fully functional before and after — `_run_generate_task` behaviour is identical; only internal plumbing changes.

---

## 9. Deviations Allowed

| Deviation | Condition |
|-----------|-----------|
| Add a `pair(system_base, user_base)` factory on `PromptBuilder` that returns two builders | Only if a third prompt function needs simultaneous system+user construction. Do not add it speculatively. |
| Move `_SYSTEM` constant from `implementation_guide/prompts.py` to `ai/prompts/__init__.py` | Only if a second caller needs the same system string. The string is intentionally co-located with the function that uses it. |
| Additional snapshot cases for edge inputs (empty arch, all-blank context) | Permitted. Keep inputs minimal and deterministic. |
| Rename `_USER_HEADER` to `_GUIDE_HEADER` | Permitted — cosmetic, no functional effect. |

---

## 10. Out of Scope

| Item | Why |
|------|-----|
| Modifying Angular `implementation-guide.service.ts` | No Flask endpoint changes; Angular still calls `POST /api/projects/<id>/generate-task`. Angular cleanup is deferred to when the Bootstrap Facade (Task 4) replaces the generate-task endpoint entirely. |
| Adding a `PromptBuilder` versioning parameter | One prompt format. Add versioning when a second named format has a user (per architecture doc). |
| Moving `rewrite_prompt` or `iterate_prompt` to use `PromptBuilder` | Neither has conditional context sections — the builder adds noise without clarity benefit. Refactor them only if a third context parameter is added. |
| `scan_prompt` refactor | Static system, single-section user. No benefit from builder at this size. |
| `generate_prompt` refactor | Already has its own inline context logic (builder + principles + tone as three separate conditions). The builder would produce identical output — defer until a fourth context type appears. |
| Updating `openapi.yaml` or regenerating DTOs | No route surface changes in this task. |
| Database, in-memory job status changes | Not touched. `_jobs` dict in `projects/routes.py` is unchanged. |
| Provider routing, prompt caching, versioning parameter | Explicitly deferred in architecture doc until a second format consumer exists. |