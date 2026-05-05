# Task 4 — Wire Per-Step Model Routing into AI Workflows

**Effort**: 0.2 days

## 1. Context

Task 3 made cost observable; this task makes it lower. The `AICall` step kind already accepts a `model=` argument (shipped in the workflows epic). What's missing is its application: today the bootstrap-project chain runs every step against `DEFAULT_MODEL` (Sonnet 4.5). The brain dump's per-step routing convention says analysis steps should use Haiku 4.5 (~5x cheaper input) and the architecture step should use Opus 4.7 (quality matters most for system design); the epic step keeps Sonnet as a sensible default.

This is a tiny edit in scope (2-3 lines per workflow file) but it depends on Task 3 because the only credible verification that the routing is correct is `/api/ai/stats` showing per-model line items. A unit test on the workflow definitions confirms each `AICall` requests the intended model id without invoking the network.

---

## 2. Pre-flight

```bash
git status -- api/modules/ai/workflows/
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
ls {WORKSPACE}/api/modules/ai/workflows/
```

Confirm Task 3 has merged. The recorded test count is `Q`. Inventory the workflow files so the edits below target the right paths — `bootstrap.py`, `generate_spec.py`, or both depending on the post-restructure layout.

---

## 3. Files

### To Modify

- `{WORKSPACE}/api/modules/ai/workflows/bootstrap.py` — three `AICall` steps (analysis, epic, architecture) — set `model=` on each
- `{WORKSPACE}/api/modules/ai/workflows/generate_spec.py` — same three steps if present in this file (the spec-gen workflow predates bootstrap-project; both define analogous AICall sequences)
- `{WORKSPACE}/api/modules/ai/workflows/tests/test_bootstrap_models.py` (new) — assert each step requests its intended model

### To Create (new)

- `{WORKSPACE}/api/modules/ai/workflows/tests/__init__.py` (new) — empty package marker if not already present

### To Leave Alone

- `{WORKSPACE}/api/modules/runtime/workflows/steps/ai_call.py` — `AICall` already accepts `model=`; no change needed
- `{WORKSPACE}/api/modules/runtime/chain/adapter.py` — Task 3 shipped per-model accounting; routing change requires no adapter edit
- `{WORKSPACE}/api/openapi.yaml` — no contract change

---

## 4. Implementation Steps

### Step 1: Identify the AICall steps that need a model override

**Action**: Open the workflow definition file(s) under `modules/ai/workflows/` and locate the chain. The pattern is `.step(AICall(name="...", system=..., prompt_template=..., input_keys=(...), max_tokens=...))`. The brain dump's mapping:

- `name="analysis"` → `model="claude-haiku-4-5"`
- `name="epic"` → `model="claude-sonnet-4-5"` (explicit Sonnet, not relying on default)
- `name="architecture"` → `model="claude-opus-4-7"`
- everything else → leave the default

Setting `epic` explicitly is intentional — it removes ambiguity in the workflow file and makes the per-step pricing trivially auditable.

---

### Step 2: Apply the model override to bootstrap.py

**File**: `{WORKSPACE}/api/modules/ai/workflows/bootstrap.py`

**Pattern** (representative; preserve the existing prompt template and input_keys arguments verbatim):

```python
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.workflow import Workflow
from modules.ai.prompts import (
    BOOTSTRAP_ANALYSIS_SYSTEM, BOOTSTRAP_ANALYSIS_USER,
    BOOTSTRAP_EPIC_SYSTEM, BOOTSTRAP_EPIC_USER,
    BOOTSTRAP_ARCHITECTURE_SYSTEM, BOOTSTRAP_ARCHITECTURE_USER,
)

bootstrap_workflow = (
    Workflow.builder("bootstrap-project")
    .step(AICall(
        name="analysis",
        system=BOOTSTRAP_ANALYSIS_SYSTEM,
        prompt_template=BOOTSTRAP_ANALYSIS_USER,
        input_keys=("braindump", "project_name", "builder"),
        model="claude-haiku-4-5",  # cheap, short prompt
        max_tokens=4096,
    ))
    .step(AICall(
        name="epic",
        system=BOOTSTRAP_EPIC_SYSTEM,
        prompt_template=BOOTSTRAP_EPIC_USER,
        input_keys=("braindump", "project_name", "analysis", "builder", "principles"),
        model="claude-sonnet-4-5",  # default; explicit for auditability
        max_tokens=4096,
    ))
    .step(AICall(
        name="architecture",
        system=BOOTSTRAP_ARCHITECTURE_SYSTEM,
        prompt_template=BOOTSTRAP_ARCHITECTURE_USER,
        input_keys=("braindump", "project_name", "epic", "builder", "principles", "codebase", "references"),
        model="claude-opus-4-7",  # quality matters most here
        max_tokens=16384,
    ))
    .build()
)
```

If the actual file uses a different builder syntax, only the `model=...` and `max_tokens=...` lines need to change — preserve everything else.

---

### Step 3: Apply the same routing to generate_spec.py if it has analogous steps

**File**: `{WORKSPACE}/api/modules/ai/workflows/generate_spec.py`

**Pattern**: locate any AICall step whose `name` matches `analysis`/`epic`/`architecture` and set `model=` to the same values as Step 2.

If `generate_spec.py` does NOT define an `architecture` step (some versions stop at the spec triple), only override the `analysis` step there. Do not invent steps that do not exist.

---

### Step 4: Test the routing without invoking the network

**File**: `{WORKSPACE}/api/modules/ai/workflows/tests/test_bootstrap_models.py` **(new)**

```python
"""Verify per-step model routing on the bootstrap-project workflow.

Network is never touched — the assertions read AICall step attributes
directly. Cost reduction itself is verified manually via /api/ai/stats.
"""
from __future__ import annotations

from modules.ai.workflows.bootstrap import bootstrap_workflow


def _step(name: str):
    for s in bootstrap_workflow.steps:
        if s.name == name:
            return s
    raise AssertionError(f"step {name!r} missing from bootstrap_workflow")


def test_analysis_step_uses_haiku_for_cost():
    assert _step("analysis").model == "claude-haiku-4-5"


def test_epic_step_uses_sonnet_explicitly():
    assert _step("epic").model == "claude-sonnet-4-5"


def test_architecture_step_uses_opus_for_quality():
    assert _step("architecture").model == "claude-opus-4-7"


def test_all_workflow_models_are_priced_in_adapter():
    """Catches drift: every model used by the workflow must have a price entry."""
    from modules.runtime.chain.adapter import _PRICING
    used_models = {s.model for s in bootstrap_workflow.steps if hasattr(s, "model")}
    missing = used_models - set(_PRICING)
    assert missing == set(), (
        f"Workflow uses models with no _PRICING entry: {missing}. "
        f"Add them to modules/runtime/chain/adapter.py:_PRICING."
    )
```

If `Workflow.steps` is private (`._steps`), use the private name; the brain dump and architecture treat workflows as data so step iteration must be possible. If neither attribute exposes the steps, add a public `steps` property to `Workflow` in this task — it is a one-line `@property` and is needed by the test.

---

## 5. Tests

```bash
cd {WORKSPACE}/api && python -m pytest modules/ai/workflows/ -q
cd {WORKSPACE}/api && python -m pytest -q
```

**Expected delta**: `Q → Q+4 passing` (4 new model-routing tests). No existing tests break — the workflow definitions are still valid; only the `model=` attribute changes.

---

## 6. Commit Plan

```bash
cd {WORKSPACE}
git add api/modules/ai/workflows/bootstrap.py \
        api/modules/ai/workflows/generate_spec.py \
        api/modules/ai/workflows/tests/__init__.py \
        api/modules/ai/workflows/tests/test_bootstrap_models.py

git commit -m "$(cat <<'EOF'
feat(workflows): per-step model routing for bootstrap chain

analysis -> claude-haiku-4-5 (cheap, short prompt)
epic     -> claude-sonnet-4-5 (explicit default for auditability)
architecture -> claude-opus-4-7 (quality matters most here)

Estimated 60-80% cost reduction on bootstrap vs all-Sonnet baseline,
verifiable via /api/ai/stats. Drift test pins every workflow model to a
_PRICING entry so unpriced models cannot ship silently.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: `Q → Q+4 passing`.

End-to-end smoke (only with a real `ANTHROPIC_API_KEY` and network access; skip in CI):

```bash
cd {WORKSPACE}/api && CHAIN_PROVIDER=claude python -c "
from create_app import create_app
app = create_app({'TESTING': True})
with app.test_client() as c:
    r = c.post('/api/ai/text/bootstrap-project', json={
        'project_name': 'smoke-test',
        'braindump': 'A tiny braindump used only to exercise the chain.'
    })
    print(r.status_code, r.get_json())
    print(c.get('/api/ai/stats').get_json())
"
```

Expected: the stats response includes non-zero token counts under both `claude-haiku-4-5` and `claude-opus-4-7`. (To inspect per-model breakdown, also call `adapter._USAGE['by_model']` in a REPL.)

---

## 8. Rollback

```bash
git revert <sha-of-this-task>
```

Revert restores the all-Sonnet behaviour. Cost rises but functionality is identical. Tasks 1, 2, 3, and 5 are independent of this routing.

---

## 9. Deviations Allowed

- **Workflow file uses a different builder syntax** (e.g., `WorkflowBuilder().add_step(...)` instead of `.step(...)`): preserve the syntax; only edit the `model=` argument values.
- **`Workflow.steps` accessor does not exist**: add a `@property` returning the internal step list. One-line addition; do not refactor the broader workflow API in this task.
- **`generate_spec.py` predates Task 4 and uses a different model id constant**: prefer the explicit string literal in this task so the routing is searchable; refactor to a shared constant in a follow-on commit.
- **`Workflow.builder("bootstrap-project")` is named differently** (e.g., `Workflow.named(...)`): preserve the existing constructor; only the `.step(AICall(..., model=...))` lines change.

---

## 10. Out of Scope

- Production startup gate in `create_app.py` — Task 5
- Adding model overrides for the task-gen workflow or implementation-guide chain — separate cost-tuning capability if/when those step costs become observable problems
- Per-tenant model overrides ("free tier uses Haiku, paid tier uses Sonnet") — usage-metering capability
- Adding new model ids to `_PRICING` beyond Sonnet 4.5, Haiku 4.5, Opus 4.7 — only when a workflow actually requests them

---

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
