# Task 1: Module Scaffold + Prompt Functions

## 1. Context

Task 1 creates the `modules/ai/` Flask blueprint and the `prompts/` submodule housing all seven pure prompt-construction functions. No route handlers are wired — the module exists only to register the blueprint in `ENABLED_MODULES` and give tasks 2–4 a stable import surface (`from modules.ai.prompts import rewrite_prompt`, etc.) and a unit-testable prompt layer that never requires an HTTP fixture. The chain adapter, providers, and context loader are already implemented from Phase 1 and are not touched here.

**Trade-offs considered:**
- **One file per prompt function** (e.g., `prompts/rewrite.py`) — rejected; 7 files for 7 single-function modules is overhead with no deduplication benefit; promote to per-file layout when a prompt function grows past ~20 lines.
- **Inline prompts in future route handlers** — rejected; the Node.js `server.js` used this pattern and its prompts became untestable without spinning up HTTP; pure functions allow direct assertion.
- **Single `prompts/__init__.py` with all 7 functions** — chosen; fits within the ~60-line port budget, keeps the import path flat (`from modules.ai.prompts import generate_spec_prompt`), and matches the "one module per feature" shape of `modules/context/` and `modules/projects/`.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
git status
git diff HEAD -- flask/create_app.py flask/tests/test_health.py
cd flask && python -m pytest --tb=short -q 2>&1 | tail -3
```

Record the passing test count from the last command as **N**.

**If `flask/create_app.py` or `flask/tests/test_health.py` are dirty**: stash or commit unrelated changes before starting.

---

## 3. Files

### To Create (new)
- `flask/modules/ai/__init__.py` — empty package marker; makes `modules.ai` importable
- `flask/modules/ai/routes.py` — Flask Blueprint declaration only; no route handlers (tasks 2–4 add them)
- `flask/modules/ai/prompts/__init__.py` — 7 pure prompt-construction functions; no I/O, no imports from `modules.context` or `modules.chain`
- `flask/modules/ai/tests/__init__.py` — empty package marker
- `flask/modules/ai/tests/test_prompts.py` — 16 unit tests asserting prompt shape and invariants

### To Modify (cite CODEBASE CONTEXT)
- `flask/create_app.py` (line 7–10: `ENABLED_MODULES`) — add `('modules.ai.routes', 'ai_bp')` as third entry
- `flask/tests/test_health.py` (lines 31–42) — add `test_ai_blueprint_registered` + update `test_both_blueprints_registered` to include `'ai'`

### To Leave Alone
- `flask/modules/chain/` — Phase 1 adapter; tasks 2–4 import from it; do not modify
- `flask/modules/context/service.py` — `read_context()` will be called by route handlers in tasks 2–4, not here
- `flask/dtos/models.py` — generated from `flask/openapi.yaml`; do not hand-edit
- `flask/openapi.yaml` — AI route schemas are Phase 2 concerns; out of scope here

---

## 4. Implementation Steps

### Step 1: Create package marker files

**Action**: Create two empty `__init__.py` files to make `modules.ai` and `modules.ai.tests` importable.

**File**: `flask/modules/ai/__init__.py` (new)
```python
```
*(empty — zero bytes)*

**File**: `flask/modules/ai/tests/__init__.py` (new)
```python
```
*(empty — zero bytes)*

**Verify**: `python -c "import sys; sys.path.insert(0,'flask'); import modules.ai"` — expect no error.

---

### Step 2: Declare the Flask blueprint

**Action**: Create `routes.py` with only the Blueprint object. Route handlers are wired in tasks 2–4 — do not add any here.

**File**: `flask/modules/ai/routes.py` (new)

```python
from flask import Blueprint

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai/text")

# Route handlers are registered in tasks 2–4.
```

**Verify**: `python -c "import sys; sys.path.insert(0,'flask'); from modules.ai.routes import ai_bp; print(ai_bp.url_prefix)"` — expect `/api/ai/text`.

---

### Step 3: Register `ai_bp` in `ENABLED_MODULES`

**Action**: Add the AI module entry to `create_app.py`. The comment on line 6 of the existing file already documents that tasks 2 and 3 will NOT edit this file — task 1 is the only time it changes.

**File**: `flask/create_app.py` (modify line 7–10)

Current:
```python
ENABLED_MODULES = [
    ('modules.projects.routes', 'projects_bp'),
    ('modules.context.routes',  'context_bp'),
]
```

Replace with:
```python
ENABLED_MODULES = [
    ('modules.projects.routes', 'projects_bp'),
    ('modules.context.routes',  'context_bp'),
    ('modules.ai.routes',       'ai_bp'),
]
```

**Verify**: `cd flask && python -c "from create_app import create_app; app = create_app(); print(list(app.blueprints))"` — expect `['projects', 'context', 'ai']` (order may vary).

---

### Step 4: Create all seven prompt functions

**Action**: Write `flask/modules/ai/prompts/__init__.py` with the full content below. No I/O, no imports from `modules.context` or `modules.chain`. Every function returns `tuple[str, str]` — `(system_prompt, user_prompt)`. Context parameters (`builder`, `principles`) are plain strings already loaded by the route layer (tasks 2–4).

**File**: `flask/modules/ai/prompts/__init__.py` (new)

```python
"""Pure prompt-construction functions for the AI text module.

Each function returns (system_prompt, user_prompt). No I/O, no imports from
modules.context, no adapter calls. Unit tests call these directly.
"""
from __future__ import annotations

# ── rewrite ──────────────────────────────────────────────────────────────────

_REWRITE_SYSTEM = (
    "You are a precise text editor. Apply the given instruction to rewrite "
    "the provided text. Return only the rewritten text — no preamble, no commentary."
)


def rewrite_prompt(text: str, instructions: str) -> tuple[str, str]:
    return _REWRITE_SYSTEM, f"Instruction: {instructions}\n\nText:\n{text}"


# ── generate ─────────────────────────────────────────────────────────────────

_GENERATE_BASE = "You are a markdown spec writer producing documentation."


def generate_prompt(prompt_text: str, builder: str, principles: str, tone: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    ctx += (f"\n\nUse a {tone} tone." if tone else "")
    return _GENERATE_BASE + ctx, prompt_text


# ── iterate ───────────────────────────────────────────────────────────────────

_ITERATE_BASE = (
    "You are a spec editor. Update the current document to reflect the intended "
    "changes while preserving canonical structure and section headings."
)


def iterate_prompt(base_spec: str, current_content: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    prompt = f"## Base specification\n{base_spec}\n\n## Current document\n{current_content}"
    return _ITERATE_BASE + ctx, prompt


# ── generate-spec ─────────────────────────────────────────────────────────────

_GENERATE_SPEC_BASE = """\
You are a specification document generator. Given a product brain dump, \
produce four specification files.

Output EXACTLY in this format — no text before the first marker, no text after the last:

===FILE: analysis.md===
[analysis content]

===FILE: epic.md===
[epic content]

===FILE: architecture.md===
[architecture content]

===FILE: spec-doc-spec.md===
[spec-doc-spec content]\
"""


def generate_spec_prompt(input_text: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    return _GENERATE_SPEC_BASE + ctx, input_text


# ── review ────────────────────────────────────────────────────────────────────

_REVIEW_SYSTEM = (
    "You are a spec reviewer. Score documents on six dimensions: "
    "clarity, completeness, actionability, consistency, specificity, feasibility. "
    'Return ONLY valid JSON — no commentary, no markdown fences: '
    '{"scores":{"clarity":<1-5>,"completeness":<1-5>,"actionability":<1-5>,'
    '"consistency":<1-5>,"specificity":<1-5>,"feasibility":<1-5>},"issues":["..."]}'
)


def review_prompt(documents: dict) -> tuple[str, str]:
    body = "\n\n".join(f"## {k}\n{v}" for k, v in documents.items())
    return _REVIEW_SYSTEM, body


# ── lint-braindump ────────────────────────────────────────────────────────────

_LINT_SYSTEM = (
    "You are a spec readiness checker. Analyse the brain dump for gaps and contradictions. "
    'Return ONLY valid JSON — no commentary, no markdown fences: '
    '{"ready":<true|false>,"flags":[{"severity":"error"|"warning"|"info","message":"..."}]}'
)


def lint_braindump_prompt(braindump: str) -> tuple[str, str]:
    return _LINT_SYSTEM, braindump


# ── scan ──────────────────────────────────────────────────────────────────────

_SCAN_SYSTEM = (
    "You are a codebase analyst. Summarise the provided filesystem tree as structured "
    "markdown: directory layout, key files, entry points, module boundaries. "
    "Do NOT include write instructions, code modifications, or tool invocations."
)


def scan_prompt(tree_text: str) -> tuple[str, str]:
    return _SCAN_SYSTEM, f"## Filesystem tree\n\n{tree_text}"
```

**Verify**: `python -c "import sys; sys.path.insert(0,'flask'); from modules.ai.prompts import generate_spec_prompt; s,_ = generate_spec_prompt('test','',''); print('===FILE:' in s)"` — expect `True`.

---

### Step 5: Update `test_health.py` blueprint assertions

**Action**: Add `test_ai_blueprint_registered` after line 37. Update `test_both_blueprints_registered` (line 39–42) to include `'ai'` in the expected set.

**File**: `flask/tests/test_health.py` (modify)

Add after line 37 (`assert 'context' in app.blueprints...`):
```python
def test_ai_blueprint_registered(app):
    assert 'ai' in app.blueprints, \
        'ai Blueprint not registered — check ENABLED_MODULES in create_app.py'
```

Replace `test_both_blueprints_registered` (lines 39–42):
```python
def test_both_blueprints_registered(app):
    registered = set(app.blueprints.keys())
    assert {'projects', 'context', 'ai'}.issubset(registered), \
        f'expected projects + context + ai, got {registered}'
```

**Verify**: `cd flask && python -m pytest tests/test_health.py -v` — all health tests pass; `test_ai_blueprint_registered` and `test_both_blueprints_registered` both show `PASSED`.

---

### Step 6: Create the prompt unit tests

**Action**: Write `flask/modules/ai/tests/test_prompts.py` with the full content from Section 5 below.

**File**: `flask/modules/ai/tests/test_prompts.py` (new)

**Verify**: `cd flask && python -m pytest modules/ai/tests/test_prompts.py -v` — 16 tests, all `PASSED`.

---

## 5. Tests

```python
# flask/modules/ai/tests/test_prompts.py
from modules.ai.prompts import (
    generate_prompt,
    generate_spec_prompt,
    iterate_prompt,
    lint_braindump_prompt,
    review_prompt,
    rewrite_prompt,
    scan_prompt,
)


def test_rewrite_prompt_embedsTextAndInstructions():
    _, prompt = rewrite_prompt("Hello world", "Make it formal")
    assert "Hello world" in prompt
    assert "Make it formal" in prompt


def test_rewrite_prompt_systemHasNoBuilderContext():
    system, _ = rewrite_prompt("x", "y")
    assert "Builder" not in system
    assert "Principles" not in system


def test_generate_prompt_embedsBuilderInSystem():
    system, _ = generate_prompt("write a spec", "I am a solo founder", "", "")
    assert "I am a solo founder" in system


def test_generate_prompt_omitsBuilderSectionWhenEmpty():
    system, _ = generate_prompt("write a spec", "", "", "")
    assert "Builder Profile" not in system


def test_generate_prompt_embedsToneInSystem():
    system, _ = generate_prompt("write a spec", "", "", "concise")
    assert "concise" in system


def test_iterate_prompt_embedsBaseSpec():
    _, prompt = iterate_prompt("base spec content", "current doc", "", "")
    assert "base spec content" in prompt


def test_iterate_prompt_embedsCurrentContent():
    _, prompt = iterate_prompt("base", "current doc content", "", "")
    assert "current doc content" in prompt


def test_iterate_prompt_embedsPrinciplesInSystem():
    system, _ = iterate_prompt("base", "current", "", "ship fast, validate first")
    assert "ship fast, validate first" in system


def test_generate_spec_prompt_containsFileMarkerInstruction():
    system, _ = generate_spec_prompt("my product idea", "", "")
    assert "===FILE:" in system


def test_generate_spec_prompt_embedsPrinciples():
    system, _ = generate_spec_prompt("my product idea", "", "minimal, ship fast")
    assert "minimal, ship fast" in system


def test_review_prompt_systemContainsAllSixDimensions():
    system, _ = review_prompt({"spec.md": "content"})
    for dimension in ("clarity", "completeness", "actionability", "consistency",
                      "specificity", "feasibility"):
        assert dimension in system, f"review_prompt system missing dimension: {dimension}"


def test_review_prompt_requestsJsonOutput():
    system, _ = review_prompt({})
    assert "JSON" in system


def test_lint_braindump_prompt_embedsBraindump():
    _, prompt = lint_braindump_prompt("my product idea text")
    assert "my product idea text" in prompt


def test_lint_braindump_prompt_requestsJsonOutput():
    system, _ = lint_braindump_prompt("")
    assert "JSON" in system


def test_scan_prompt_embedsTreeText():
    _, prompt = scan_prompt("src/\n  main.py")
    assert "src/" in prompt
    assert "main.py" in prompt


def test_scan_prompt_systemProhibitsWriteOperations():
    system, _ = scan_prompt("")
    # Claude CLI converts write intent into a tool-use permission stub;
    # the scan system prompt must explicitly forbid it.
    assert "Do NOT" in system, (
        "scan_prompt system must explicitly prohibit write operations — "
        "Claude CLI converts write intent into a permission stub (see architecture.md)"
    )
```

---

## 6. Commit Plan

**Commit 1** — `feat(ai): scaffold modules/ai blueprint and register in ENABLED_MODULES`
- Files: `flask/modules/ai/__init__.py`, `flask/modules/ai/routes.py`, `flask/create_app.py`
- What: empty package, blueprint declaration, ENABLED_MODULES entry

**Commit 2** — `feat(ai/prompts): add pure prompt-construction functions for all 7 endpoints`
- Files: `flask/modules/ai/prompts/__init__.py`
- What: 7 prompt functions; no I/O, no adapter imports

**Commit 3** — `test(ai): add prompt unit tests and blueprint registration assertion`
- Files: `flask/modules/ai/tests/__init__.py`, `flask/modules/ai/tests/test_prompts.py`, `flask/tests/test_health.py`
- What: 16 prompt tests, 1 new health test, updated `test_both_blueprints_registered`

**Deviation logging**: if any step deviates, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd flask && python -m pytest --tb=short -q
```

**Expected delta**: N → N+17 passing (16 new prompt tests + 1 new health blueprint test; `test_both_blueprints_registered` is a modification, not a new test). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` in reverse order (commit 3 → 2 → 1).
- **Per-branch**: if verification fails entirely, `git reset --hard <pre-task-sha>` and delete the working branch. The only files modified in the existing tree are `flask/create_app.py` and `flask/tests/test_health.py` — both are small and the diffs are surgical.

---

## 9. Deviations Allowed

- **`flask/modules/ai/` directory already exists** → verify contents match; if `routes.py` or `prompts/__init__.py` exist from a prior abandoned attempt, read them before overwriting and log the deviation.
- **Review dimensions don't match `specs/quality-rubric.md`** → read `specs/quality-rubric.md` and update `_REVIEW_SYSTEM` in `prompts/__init__.py` to use the exact rubric dimensions; log in commit 2 body.
- **`test_both_blueprints_registered` uses a different assertion pattern** than described above → translate silently to match the existing file's shape; note in commit 3 body.
- **Side-effect required** (git push, schema change) → STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.

---

## 10. Out of Scope

Task 1 installs the import surface and ensures the blueprint is registered — nothing more. Route handlers, request parsing, response serialization, context loading, and JSON extraction are all wired in tasks 2–4. Do not absorb them here.

- **Route handlers** (`GET /rewrite`, `POST /generate`, etc.) — belong in tasks 2–4; adding them here would skip smoke-test validation ordering
- **`extract_json()` utility** — belongs in task 3 where review and lint-braindump routes are wired; two consumers don't exist yet
- **`looks_like_cli_refusal()` guard** — belongs in task 4 (scan endpoint); no scan route exists yet
- **OpenAPI YAML updates for AI routes** — belongs in a separate schema task after all 7 routes are confirmed working; adding them before routes exist generates unverifiable spec drift
- **Context loading in prompt functions** — prompt functions are deliberately pure; `read_context()` calls belong in route handlers (tasks 2–4), not here; the architecture's rationale is testability without filesystem state

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for this module
- [Epic](./epic.md) — Task scope and ordering
- [Timeline](./timeline.md) — Update status to `done` after verification passes