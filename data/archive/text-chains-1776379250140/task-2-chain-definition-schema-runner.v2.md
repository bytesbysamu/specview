I now have all the context needed to generate the implementation guide. Let me produce it.

# Task 2: Chain Definition Schema + Runner

**Epic**: Text Chains — LoRA for Text
**Effort**: 1 day (~500 lines across 12 files)
**Dependencies**: None (parallel with Task 1; context loader calls use mock mode via conftest)
**Parallel With**: Task 1 (Context Block Loader)
**Blocks**: Task 3 (Deep Humanize), Task 4 (Braindump → Docs), Task 5 (Rewrite + Review), Task 6 (Chain Mode UI)

**Related**:
- [Architecture](./architecture.md) — Chain Definition schema, STEP_HANDLERS dispatch, Observer pattern, endpoint contract
- [Epic](./epic.md) — Task 2 detail, success criteria

---

## 1. Context

The existing `server/modules/chain/runner.py` (shipped in the prior Bubls epic) provides a minimal `sequential(steps, initial)` helper that takes a list of callables plus a thin `run_chain` wrapper. Text Chains needs a **data-driven** runner: load a JSON chain definition by ID, resolve each step's operation to a handler via a `STEP_HANDLERS` dispatch map, inject context blocks from the loader (Task 1), pass output between steps, parse multi-file markers on the final output, and emit a `chainCompleted` Observer signal. This task builds six deliverables: (1) the `ChainDefinition` / `ChainStep` data classes, (2) a `definition_runner.py` with handler dispatch and the run loop, (3) three chain definition JSON files, (4) the `POST /api/text/chain` endpoint with feature-gating, (5) an Alembic migration adding `chain_id` + `step_count` to `superapp_generations`, and (6) structural tests enforcing module boundaries.

The existing `runner.py` is preserved untouched. The new `definition_runner.py` calls `adapter.generate` (respecting the ELA Adapter boundary) and can internally use `sequential` from `runner.py` if needed — but the dispatch loop is its own concern.

### Trade-offs considered

- **New file `definition_runner.py` vs extending existing `runner.py`** — new file chosen to avoid modifying the `run_chain` contract that `modules/text/service.py` and photoshoot already consume. The original `runner.py` stays stable; the definition runner imports from it if needed but doesn't alter its surface. Rejected: extending `runner.py` (breaks existing callers' import expectations, mixes two abstraction levels in one module).
- **`STEP_HANDLERS` as module-level dict vs class registry with `register()` decorator** — module-level dict matches the codebase convention (cf. `prompts.MODES` dict in `modules/text/prompts.py`). Adding an operation = one function + one dict entry. No class hierarchy overhead for 3 operations. Rejected: class registry (overengineered; trigger: when step handlers need shared state or lifecycle hooks).
- **`blinker` signals vs custom Observer** — `blinker` is already a transitive Flask dependency. One `signal("chainCompleted")` matches the architecture's Observer pattern. Rejected: custom event bus (reinvents what blinker provides), direct function call from runner to analytics (couples the modules).

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/bubls/server
git status                                           # flag unrelated M/?? entries
git diff HEAD -- modules/chain/ modules/text/        # confirm target files are clean
python -m pytest --tb=short -q 2>&1 | tail -5        # record baseline test count
ls modules/chain/runner.py                           # confirm chain primitive exists
ls modules/chain/adapter.py                          # confirm adapter exists
python -c "from modules.chain import generate, ChainResult; print('chain adapter OK')"
ls modules/text/routes.py 2>/dev/null && echo "text module exists" || echo "text module missing"
ls migrations/versions/ | tail -3                    # note latest revision for down_revision
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**If `modules/chain/runner.py` does not exist**: STOP — the prior Bubls epic (chain primitive) has not been merged.

**If Task 1 (context loader) is not merged**: safe to proceed. The conftest fixture forces `CONTEXT_PROVIDER=mock`, so `load_blocks` returns fixture strings with no file I/O. The runner does not depend on real context files.

**Baseline recorded**: `[N]/[N] passing` — fill in from pytest output.

---

## 3. Files

### To Create

| File | Purpose |
|------|---------|
| `server/modules/chain/definition_runner.py` | Schema-driven runner: load definition JSON, dispatch via `STEP_HANDLERS`, parse multi-file output, emit `chainCompleted` signal |
| `server/modules/chain/signals.py` | `chainCompleted` blinker signal definition |
| `server/modules/chain/definitions/deep-humanize.json` | 3-step humanize chain (rewrite × 3) |
| `server/modules/chain/definitions/braindump-to-docs.json` | 3-step braindump chain (review + generate + review), multi-file output |
| `server/modules/chain/definitions/rewrite-review.json` | 3-step rewrite+review chain (rewrite + review + fix) |
| `server/modules/chain/tests/test_definition_runner.py` | Unit + structural tests for the definition runner |
| `server/modules/text/chain_routes.py` | `POST /api/text/chain` endpoint with feature gate |
| `server/modules/text/chain_service.py` | Orchestrates definition runner → repository persist → response |
| `server/modules/text/chain_dto.py` | Pydantic v2 DTOs for chain request/response |
| `server/migrations/versions/{rev}_add_chain_columns.py` | Alembic: add `chain_id` + `step_count` to `superapp_generations` |
| `server/tests/test_text_chain_routes.py` | Route-level integration tests for chain endpoint |

### To Modify

| File | Change |
|------|--------|
| `server/modules/chain/__init__.py` | Add re-exports: `run_definition`, `load_definition`, `ChainRunResult`, `parse_multi_file_output`, `chain_completed` |
| `server/modules/photoshoot/models.py` | Add `chain_id: Mapped[str \| None]` and `step_count: Mapped[int \| None]` columns to `Generation` model |
| `server/modules/text/repository.py` | Add `create_chain_generation()` accepting `chain_id` + `step_count` |
| `server/app.py` | Register `modules.text.chain_routes` in `ENABLED_MODULES` (or wire blueprint into existing text registration) |

### To Leave Alone

| File | Reason |
|------|--------|
| `server/modules/chain/runner.py` | Existing `sequential`/`run_chain` preserved for backward compat — definition runner is additive |
| `server/modules/chain/adapter.py` | Definition runner calls `adapter.generate()` — no adapter changes needed |
| `server/modules/chain/context.py` | Builder/principles injection at adapter boundary unchanged |
| `server/modules/chain/providers/` | Adapter boundary intact; runner never imports providers directly |
| `server/modules/text/service.py` | Single-shot text service unchanged |
| `server/modules/text/prompts.py` | Single-shot prompt modes unchanged |
| `server/modules/text/routes.py` | Existing `/api/text/rewrite` and `/api/text/generate` routes unchanged |
| `server/modules/context/` | Context loader unchanged; definition runner calls `load_blocks()` through its public API |
| `src/app/` | Zero frontend work in Task 2 |

---

## 4. Implementation Steps

### Step 1: Create chain definition JSON files

**Action**: Create `server/modules/chain/definitions/` directory and three chain definition JSON files. These are data files that the definition runner reads — no Python code.

**File**: `server/modules/chain/definitions/deep-humanize.json` (new)

```json
{
  "id": "deep-humanize",
  "name": "Deep Humanize",
  "steps": [
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-1"] },
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-2"] },
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-3"] }
  ],
  "outputMode": "single"
}
```

**File**: `server/modules/chain/definitions/braindump-to-docs.json` (new)

```json
{
  "id": "braindump-to-docs",
  "name": "Brain Dump → Docs",
  "steps": [
    { "op": "review", "context": ["braindump-lint"], "outputKey": "lint" },
    { "op": "generate", "context": ["builder", "principles", "references", "braindump-to-docs"] },
    { "op": "review", "context": ["quality-rubric"], "outputKey": "score" }
  ],
  "outputMode": "multi-file"
}
```

**File**: `server/modules/chain/definitions/rewrite-review.json` (new)

```json
{
  "id": "rewrite-review",
  "name": "Rewrite + Review",
  "steps": [
    { "op": "rewrite", "mode": "user-selected", "context": [] },
    { "op": "review", "context": ["quality-rubric"] },
    { "op": "rewrite", "mode": "fix", "context": [] }
  ],
  "outputMode": "single"
}
```

Schema fields: `id` (unique identifier, used as `chainId` in API), `name` (human-readable label for UI), `steps` (ordered array), `outputMode` (`"single"` or `"multi-file"`). Each step: `op` (must exist in `STEP_HANDLERS`), `mode` (optional, operation-specific), `context` (array of block names from manifest), `outputKey` (optional, names the output for downstream reference).

**Verify**:
```bash
python -c "
import json, pathlib
defs_dir = pathlib.Path('modules/chain/definitions')
for f in sorted(defs_dir.glob('*.json')):
    d = json.loads(f.read_text())
    assert 'id' in d and 'steps' in d and 'outputMode' in d, f'{f.name} missing required field'
    print(f'{d[\"id\"]}: {len(d[\"steps\"])} steps, {d[\"outputMode\"]}')
"
```

Expected: three lines — `braindump-to-docs: 3 steps, multi-file`, `deep-humanize: 3 steps, single`, `rewrite-review: 3 steps, single`.

---

### Step 2: Create the signals module

**Action**: Create `server/modules/chain/signals.py` with a blinker signal. `blinker` is a transitive Flask dependency — no new pip install.

**File**: `server/modules/chain/signals.py` (new)

```python
"""Observer signals for the chain module.

Uses blinker (Flask's built-in signal library). Subscribers connect without
importing the chain module — they import signals.py directly.

Pattern mirrors the ``outputCompleted`` signal from the UX revamp design.
"""
from __future__ import annotations

from blinker import Namespace

_ns = Namespace()

chain_completed = _ns.signal("chainCompleted")
"""Emitted after every chain run with payload:
    {
        "chainId": str,
        "stepCount": int,
        "inputLength": int,
        "outputLength": int,
        "totalTokens": int | None,
    }
"""
```

**Verify**:
```bash
python -c "from modules.chain.signals import chain_completed; print(f'Signal: {chain_completed.name}')"
```

Expected: `Signal: chainCompleted`

---

### Step 3: Create the definition runner

**Action**: Create `server/modules/chain/definition_runner.py` with `STEP_HANDLERS` dispatch map, definition loading/parsing, multi-file output parsing (anti-corruption layer), and the `run_definition()` main function. This is the core of the task.

The runner calls `adapter.generate()` per step — never imports from `providers.*` directly (ELA Adapter boundary). Context blocks are loaded via `modules.context.loader.load_blocks()`. The `===FILE: name===` marker parsing is ported from spec-doc's `generate-spec` endpoint shape (see REFERENCE CODE: `spec-doc/server.js` multi-file generation pattern).

**File**: `server/modules/chain/definition_runner.py` (new)

```python
"""Schema-driven chain runner with step-handler dispatch.

Loads a ``ChainDefinition`` from JSON, resolves each step's handler via
``STEP_HANDLERS``, injects context blocks via ``modules.context.loader``,
and passes output between steps sequentially.

Adding a new operation = one handler function + one ``STEP_HANDLERS`` entry.
No if/elif branches in the run loop.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from modules.chain import adapter
from modules.chain.signals import chain_completed
from modules.chain.types import ChainResult
from modules.context import loader as context_loader

_DEFINITIONS_DIR = Path(__file__).resolve().parent / "definitions"

_FILE_MARKER = re.compile(r"^===FILE:\s*(.+?)\s*===$", re.MULTILINE)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ChainStep:
    op: str
    context: list[str] = field(default_factory=list)
    mode: str | None = None
    output_key: str | None = None


@dataclass(frozen=True)
class ChainDefinition:
    id: str
    name: str
    steps: list[ChainStep]
    output_mode: str  # "single" or "multi-file"


# ── Definition loading ───────────────────────────────────────────────────────

def load_definition(chain_id: str) -> ChainDefinition:
    """Load a chain definition JSON by ID.

    Raises:
        FileNotFoundError: no definition file for the given chain_id.
        ValueError: definition file is invalid JSON or missing required fields.
    """
    path = _DEFINITIONS_DIR / f"{chain_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Chain definition not found: {chain_id}. Expected: {path}"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _parse_definition(raw)


def _parse_definition(raw: dict[str, Any]) -> ChainDefinition:
    for key in ("id", "name", "steps", "outputMode"):
        if key not in raw:
            raise ValueError(f"Chain definition missing required field: {key!r}")
    steps = []
    for i, s in enumerate(raw["steps"]):
        if "op" not in s:
            raise ValueError(f"Step {i} missing required field: 'op'")
        steps.append(ChainStep(
            op=s["op"],
            context=s.get("context", []),
            mode=s.get("mode"),
            output_key=s.get("outputKey"),
        ))
    return ChainDefinition(
        id=raw["id"],
        name=raw["name"],
        steps=steps,
        output_mode=raw["outputMode"],
    )


# ── Step handlers ────────────────────────────────────────────────────────────

def _handle_rewrite(
    text: str,
    step: ChainStep,
    context_blocks: dict[str, str],
    *,
    user: Any = None,
) -> ChainResult:
    system_parts = list(context_blocks.values())
    system = "\n\n".join(system_parts) if system_parts else "Rewrite the following text."
    return adapter.generate(system=system, prompt=text, user=user, feature="text")


def _handle_generate(
    text: str,
    step: ChainStep,
    context_blocks: dict[str, str],
    *,
    user: Any = None,
) -> ChainResult:
    system_parts = list(context_blocks.values())
    system = "\n\n".join(system_parts) if system_parts else "Generate content based on the input."
    return adapter.generate(system=system, prompt=text, user=user, feature="text")


def _handle_review(
    text: str,
    step: ChainStep,
    context_blocks: dict[str, str],
    *,
    user: Any = None,
) -> ChainResult:
    system_parts = list(context_blocks.values())
    system = "\n\n".join(system_parts) if system_parts else "Review the following text."
    review_prompt = f"Review this text and return structured feedback as JSON:\n\n{text}"
    return adapter.generate(system=system, prompt=review_prompt, user=user, feature="text")


STEP_HANDLERS: dict[str, Callable] = {
    "rewrite": _handle_rewrite,
    "generate": _handle_generate,
    "review": _handle_review,
}


# ── Multi-file output parsing ────────────────────────────────────────────────

def parse_multi_file_output(text: str) -> list[dict[str, str]]:
    """Parse ``===FILE: name===`` markers into ``[{name, content}]``.

    Anti-corruption layer: LLM marker-delimited output is parsed into
    structured objects before reaching the frontend. Ported from
    spec-doc's generate-spec multi-file output shape.
    """
    markers = list(_FILE_MARKER.finditer(text))
    if not markers:
        return [{"name": "output.md", "content": text.strip()}]

    files: list[dict[str, str]] = []
    for i, match in enumerate(markers):
        name = match.group(1)
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        files.append({"name": name, "content": content})
    return files


# ── Main runner ──────────────────────────────────────────────────────────────

@dataclass
class ChainRunResult:
    """Result of a full chain execution."""
    chain_id: str
    output_mode: str
    result: str | None = None
    files: list[dict[str, str]] | None = None
    step_count: int = 0
    total_tokens: int | None = None
    input_length: int = 0
    output_length: int = 0


def run_definition(
    chain_id: str,
    user_input: str,
    *,
    user: Any = None,
) -> ChainRunResult:
    """Execute a chain definition end-to-end.

    1. Load definition by chain_id
    2. For each step: resolve handler, load context blocks, execute, forward output
    3. Parse multi-file output if outputMode == "multi-file"
    4. Emit chainCompleted signal
    5. Return structured result

    Raises:
        FileNotFoundError: chain definition not found (→ 404)
        ValueError: invalid definition or unknown step op (→ 400)
        ProviderError: upstream AI provider failure (→ 500)
    """
    definition = load_definition(chain_id)
    current_text = user_input
    total_tokens: int = 0

    for i, step in enumerate(definition.steps):
        handler = STEP_HANDLERS.get(step.op)
        if handler is None:
            raise ValueError(
                f"Unknown step op {step.op!r} in chain {chain_id!r} step {i}. "
                f"Available: {sorted(STEP_HANDLERS.keys())}"
            )

        context_blocks = context_loader.load_blocks(step.context) if step.context else {}

        result: ChainResult = handler(current_text, step, context_blocks, user=user)
        current_text = result.text
        total_tokens += (result.tokens_in or 0) + (result.tokens_out or 0)

    final_output = current_text
    output_length = len(final_output)

    if definition.output_mode == "multi-file":
        files = parse_multi_file_output(final_output)
        run_result = ChainRunResult(
            chain_id=definition.id,
            output_mode=definition.output_mode,
            files=files,
            step_count=len(definition.steps),
            total_tokens=total_tokens or None,
            input_length=len(user_input),
            output_length=output_length,
        )
    else:
        run_result = ChainRunResult(
            chain_id=definition.id,
            output_mode=definition.output_mode,
            result=final_output,
            step_count=len(definition.steps),
            total_tokens=total_tokens or None,
            input_length=len(user_input),
            output_length=output_length,
        )

    chain_completed.send(
        None,
        chainId=definition.id,
        stepCount=len(definition.steps),
        inputLength=len(user_input),
        outputLength=output_length,
        totalTokens=total_tokens or None,
    )

    return run_result
```

**Verify**:
```bash
CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -c "
from modules.chain.definition_runner import run_definition
r = run_definition('deep-humanize', 'test input')
print(f'chain={r.chain_id}, steps={r.step_count}, mode={r.output_mode}')
print(f'result[:80]={r.result[:80]}')
"
```

Expected: chain=deep-humanize, steps=3, mode=single, result contains `MOCK[`.

---

### Step 4: Create Alembic migration for chain columns

**Action**: Add `chain_id` (String, nullable) and `step_count` (Integer, nullable) to `superapp_generations`. Both nullable — existing single-shot rows keep `NULL`. No backfill needed.

**File**: `server/migrations/versions/{rev}_add_chain_columns.py` (new)

The `down_revision` must match the latest migration file found in Pre-flight. The example below uses a placeholder; the executor MUST fill in the actual revision from `ls migrations/versions/ | tail -1`.

```python
"""add chain_id and step_count to superapp_generations

Text Chains epic: persist chain metadata alongside generation rows.
Both columns nullable — existing single-shot rows keep NULL.
No backfill needed.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# IMPORTANT: replace down_revision with the ACTUAL latest revision from pre-flight
revision = "20260421_add_chain_columns"
down_revision = None  # ← FILL IN from `ls migrations/versions/ | tail -1`
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "superapp_generations",
        sa.Column("chain_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "superapp_generations",
        sa.Column("step_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("superapp_generations", "step_count")
    op.drop_column("superapp_generations", "chain_id")
```

**Verify**:
```bash
python -c "
import importlib, sys
sys.path.insert(0, '.')
m = importlib.import_module('migrations.versions.20260421_add_chain_columns')
print(f'revision={m.revision}, down_revision={m.down_revision}')
assert m.down_revision is not None, 'STOP: down_revision not filled in'
"
```

---

### Step 5: Update Generation model with chain columns

**Action**: Add `chain_id` and `step_count` mapped columns to the `Generation` model in `server/modules/photoshoot/models.py`.

**File**: `server/modules/photoshoot/models.py` — add after the existing `result_text` (or last existing) column:

```python
    # Text Chains: chain metadata. Null for single-shot generations.
    chain_id: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    step_count: Mapped[int | None] = mapped_column(nullable=True)
```

**Verify**:
```bash
python -c "
from modules.photoshoot.models import Generation
cols = [c.name for c in Generation.__table__.columns]
assert 'chain_id' in cols, f'chain_id missing. Columns: {cols}'
assert 'step_count' in cols, f'step_count missing. Columns: {cols}'
print(f'OK: chain_id and step_count present in {len(cols)}-column table')
"
```

---

### Step 6: Add chain generation persistence

**Action**: Add `create_chain_generation()` to `server/modules/text/repository.py` after the existing `create_text_generation` function.

**File**: `server/modules/text/repository.py`

```python
def create_chain_generation(
    db: Session,
    *,
    user_id: uuid.UUID,
    chain_id: str,
    step_count: int,
    input_text: str,
    output: str,
) -> Generation:
    """Persist a chain-run row in the unified superapp_generations table.

    ``feature="text"`` + ``chain_id`` discriminate chain rows from single-shot.
    """
    gen = Generation(
        user_id=user_id,
        lora_model_id=None,
        feature="text",
        input_text=input_text,
        result_text=output,
        result_image_url=None,
        original_thumbnail=None,
        chain_id=chain_id,
        step_count=step_count,
    )
    db.add(gen)
    db.commit()
    db.refresh(gen)
    return gen
```

If the existing `create_text_generation` function uses different column names or the `Generation` constructor has a different signature, adapt accordingly and log as deviation. The executor should read the existing function first.

**Verify**:
```bash
python -c "from modules.text.repository import create_chain_generation; print('import OK')"
```

---

### Step 7: Create chain DTOs

**Action**: Create Pydantic v2 DTOs for the chain endpoint request/response. Matches the architecture doc's API contract: `{ chainId, input }` → `{ generationId, result? , files? }`.

**File**: `server/modules/text/chain_dto.py` (new)

```python
"""Pydantic DTOs for the chain endpoint.

Matches POST /api/text/chain contract from architecture.md:
  Request:  { chainId: string, input: string }
  Response: { generationId: string, result?: string, files?: [{name, content}] }
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChainRequest(BaseModel):
    chain_id: str = Field(..., alias="chainId", min_length=1, max_length=64)
    input: str = Field(..., min_length=1, max_length=20000)

    model_config = {"populate_by_name": True}


class ChainFileOutput(BaseModel):
    name: str
    content: str


class ChainResponse(BaseModel):
    generation_id: str = Field(..., alias="generationId")
    result: str | None = None
    files: list[ChainFileOutput] | None = None

    model_config = {"populate_by_name": True, "by_alias": True}


class ChainErrorResponse(BaseModel):
    error: str
    upgrade: bool | None = None
    partial_output: str | None = Field(None, alias="partialOutput")
    failed_step: int | None = Field(None, alias="failedStep")

    model_config = {"populate_by_name": True, "by_alias": True}
```

**Verify**:
```bash
python -c "
from modules.text.chain_dto import ChainRequest, ChainResponse
req = ChainRequest.model_validate({'chainId': 'deep-humanize', 'input': 'test'})
print(f'chain_id={req.chain_id}, input_len={len(req.input)}')
resp = ChainResponse(generation_id='abc-123', result='output')
print(resp.model_dump(by_alias=True))
"
```

Expected: `{'generationId': 'abc-123', 'result': 'output', 'files': None}`

---

### Step 8: Create chain service

**Action**: Create `server/modules/text/chain_service.py` — the orchestration layer between route and runner. Zero Flask imports, zero SQLAlchemy model imports — onion layering.

**File**: `server/modules/text/chain_service.py` (new)

```python
"""Service layer for chain operations.

Orchestrates: definition_runner → repository persist → response dict.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from modules.chain.definition_runner import run_definition, ChainRunResult

from . import repository


def execute_chain(
    db: Session,
    *,
    user,
    chain_id: str,
    input_text: str,
) -> dict:
    """Run a chain definition and persist the result.

    Returns a dict ready for jsonify:
      - Single-file: {"generationId": str, "result": str}
      - Multi-file:  {"generationId": str, "files": [{name, content}]}

    Raises:
        FileNotFoundError: chain definition not found (→ 404)
        ValueError: invalid chain definition (→ 400)
        ProviderError: upstream AI failure (→ 500)
    """
    run_result: ChainRunResult = run_definition(
        chain_id,
        input_text,
        user=user,
    )

    # Serialize for persistence (multi-file → marker-delimited string)
    output_text = run_result.result or ""
    if run_result.files:
        output_text = "\n\n".join(
            f"===FILE: {f['name']}===\n{f['content']}" for f in run_result.files
        )

    row = repository.create_chain_generation(
        db,
        user_id=user.id,
        chain_id=chain_id,
        step_count=run_result.step_count,
        input_text=input_text,
        output=output_text,
    )

    response: dict = {"generationId": str(row.id)}
    if run_result.files is not None:
        response["files"] = run_result.files
    else:
        response["result"] = run_result.result
    return response
```

**Verify**:
```bash
python -c "from modules.text.chain_service import execute_chain; print('import OK')"
```

---

### Step 9: Create chain routes

**Action**: Create `server/modules/text/chain_routes.py` with the `POST /api/text/chain` endpoint. Feature-gated via `require_feature("text_chains")` — returns 403 with upgrade hint when disabled. Error handling maps exceptions to the architecture's error response contract.

**File**: `server/modules/text/chain_routes.py` (new)

The executor must read `server/modules/text/routes.py` and `server/core/auth.py` (or equivalent) to confirm the auth decorator names (`require_auth`, `require_feature`). Adapt if the actual decorator names differ.

```python
"""HTTP surface for the chain endpoint.

Thin controller: parse JSON, validate, check feature gate, delegate to
chain_service, jsonify the result. Registered via ENABLED_MODULES or
nested blueprint.
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from core.auth import require_auth, require_feature
from modules.chain.errors import ProviderError

from . import chain_service
from .chain_dto import ChainErrorResponse, ChainRequest

bp = Blueprint("text_chain", __name__, url_prefix="/api/text")

FEATURE_FLAG = "text_chains"


def _error(message: str, status: int, **kwargs):
    payload = ChainErrorResponse(error=message, **kwargs).model_dump(
        by_alias=True, exclude_none=True
    )
    return jsonify(payload), status


@bp.post("/chain")
@require_auth
@require_feature(FEATURE_FLAG)
def run_chain():
    try:
        req = ChainRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _error(f"Invalid request: {exc.errors()}", 400)

    try:
        payload = chain_service.execute_chain(
            g.db,
            user=g.user,
            chain_id=req.chain_id,
            input_text=req.input,
        )
    except FileNotFoundError:
        return _error(f"Chain definition not found: {req.chain_id}", 404)
    except ValueError as exc:
        return _error(str(exc), 400)
    except ProviderError as exc:
        return _error(exc.message, exc.status_code)

    return jsonify(payload), 200
```

**Verify**: Deferred to Step 10 (blueprint registration check).

---

### Step 10: Register chain blueprint

**Action**: Register the chain routes blueprint. Read `server/app.py` to determine the exact registration pattern.

**File**: `server/app.py` — one of:

**Option A** (if `ENABLED_MODULES` supports submodule paths):
```python
ENABLED_MODULES: list[str] = [
    "modules.photoshoot",
    "modules.user",
    "modules.text",
    "modules.text.chain_routes",   # Text Chains: POST /api/text/chain
]
```

**Option B** (if blueprints are imported in the module's `routes.py`):
In `server/modules/text/routes.py`, add at the bottom:
```python
from .chain_routes import bp as chain_bp
```
And ensure the app factory registers both blueprints.

The executor must read `server/app.py` to determine which pattern applies and adapt. Log as deviation if the registration pattern differs from Option A.

**Verify**:
```bash
CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -c "
from app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
assert '/api/text/chain' in rules, f'/api/text/chain not registered. Routes: {[r for r in rules if \"text\" in r]}'
print('OK: /api/text/chain registered')
"
```

---

### Step 11: Update chain module `__init__.py`

**Action**: Add definition_runner exports to `server/modules/chain/__init__.py` so downstream modules can `from modules.chain import run_definition`.

**File**: `server/modules/chain/__init__.py` — add after existing imports:

```python
from .definition_runner import (
    load_definition,
    run_definition,
    ChainRunResult,
    parse_multi_file_output,
    STEP_HANDLERS,
)
from .signals import chain_completed
```

Update `__all__` to include:
```python
__all__ = [
    # existing exports
    "ChainResult",
    "ProviderError",
    "generate",
    "run_chain",
    "sequential",
    "stream",
    # new exports
    "ChainRunResult",
    "STEP_HANDLERS",
    "chain_completed",
    "load_definition",
    "parse_multi_file_output",
    "run_definition",
]
```

**Verify**:
```bash
CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -c "
from modules.chain import run_definition, chain_completed, STEP_HANDLERS
print(f'STEP_HANDLERS: {sorted(STEP_HANDLERS.keys())}')
print('OK')
"
```

Expected: `STEP_HANDLERS: ['generate', 'review', 'rewrite']`

---

## 5. Tests

### File: `server/modules/chain/tests/test_definition_runner.py`

```python
"""Tests for the schema-driven definition runner.

Mock provider (CHAIN_PROVIDER=mock) + mock context (CONTEXT_PROVIDER=mock)
forced by conftest fixtures.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from modules.chain import definition_runner as _dr
from modules.chain.definition_runner import (
    ChainRunResult,
    ChainStep,
    load_definition,
    parse_multi_file_output,
    run_definition,
    STEP_HANDLERS,
)
from modules.chain.signals import chain_completed


@pytest.fixture(autouse=True)
def _force_mock_context(monkeypatch):
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")


# ── Definition loading ───────────────────────────────────────────────────────

def test_loadDefinition_deepHumanize_parsesCorrectly():
    d = load_definition("deep-humanize")
    assert d.id == "deep-humanize"
    assert d.output_mode == "single"
    assert len(d.steps) == 3
    assert all(s.op == "rewrite" for s in d.steps)


def test_loadDefinition_braindumpToDocs_parsesMultiFile():
    d = load_definition("braindump-to-docs")
    assert d.output_mode == "multi-file"
    assert d.steps[0].op == "review"
    assert d.steps[1].op == "generate"
    assert len(d.steps[1].context) == 4


def test_loadDefinition_rewriteReview_parsesCorrectly():
    d = load_definition("rewrite-review")
    assert d.id == "rewrite-review"
    assert len(d.steps) == 3
    assert d.steps[1].op == "review"


def test_loadDefinition_unknownId_raisesFileNotFoundError():
    with pytest.raises(FileNotFoundError, match="nonexistent-chain"):
        load_definition("nonexistent-chain")


def test_loadDefinition_allDefinitions_haveValidStepOps():
    """Every step.op in every definition file must exist in STEP_HANDLERS."""
    defs_dir = pathlib.Path(_dr.__file__).parent / "definitions"
    for f in defs_dir.glob("*.json"):
        raw = json.loads(f.read_text())
        for i, step in enumerate(raw["steps"]):
            assert step["op"] in STEP_HANDLERS, (
                f"{f.name} step {i}: unknown op {step['op']!r}. "
                f"Available: {sorted(STEP_HANDLERS.keys())}"
            )


# ── STEP_HANDLERS ────────────────────────────────────────────────────────────

def test_stepHandlers_hasExactlyThreeOps():
    assert set(STEP_HANDLERS.keys()) == {"rewrite", "generate", "review"}


def test_stepHandlers_noIfElifInRunLoop():
    """The runner loop must use dict dispatch, not if/elif branches."""
    source = pathlib.Path(_dr.__file__).read_text()
    fn_start = source.index("def run_definition(")
    fn_body = source[fn_start:]
    assert "if step.op ==" not in fn_body, (
        "Runner loop must use STEP_HANDLERS dispatch, not if/elif"
    )
    assert "elif step.op" not in fn_body, (
        "Runner loop must use STEP_HANDLERS dispatch, not if/elif"
    )


# ── run_definition ───────────────────────────────────────────────────────────

def test_runDefinition_deepHumanize_returnsSingleResult():
    r = run_definition("deep-humanize", "AI-generated test text")
    assert isinstance(r, ChainRunResult)
    assert r.chain_id == "deep-humanize"
    assert r.output_mode == "single"
    assert r.result is not None
    assert r.files is None
    assert r.step_count == 3
    assert r.input_length == len("AI-generated test text")
    assert r.output_length > 0


def test_runDefinition_deepHumanize_outputContainsMockTrace():
    r = run_definition("deep-humanize", "test input")
    assert "MOCK[" in r.result


def test_runDefinition_rewriteReview_returnsSingleResult():
    r = run_definition("rewrite-review", "some text to review")
    assert r.output_mode == "single"
    assert r.result is not None
    assert r.step_count == 3


def test_runDefinition_emitsChainCompletedSignal():
    received = []

    def on_completed(sender, **kwargs):
        received.append(kwargs)

    chain_completed.connect(on_completed)
    try:
        run_definition("deep-humanize", "test")
    finally:
        chain_completed.disconnect(on_completed)

    assert len(received) == 1
    payload = received[0]
    assert payload["chainId"] == "deep-humanize"
    assert payload["stepCount"] == 3
    assert payload["inputLength"] == 4
    assert payload["outputLength"] > 0


def test_runDefinition_unknownChain_raisesFileNotFoundError():
    with pytest.raises(FileNotFoundError):
        run_definition("nonexistent", "text")


# ── parse_multi_file_output ──────────────────────────────────────────────────

def test_parseMultiFileOutput_withMarkers_splitsByFile():
    text = (
        "===FILE: analysis.md===\n# Analysis\nContent A\n\n"
        "===FILE: epic.md===\n# Epic\nContent B\n\n"
        "===FILE: architecture.md===\n# Arch\nContent C"
    )
    files = parse_multi_file_output(text)
    assert len(files) == 3
    assert files[0]["name"] == "analysis.md"
    assert files[0]["content"].startswith("# Analysis")
    assert files[1]["name"] == "epic.md"
    assert files[2]["name"] == "architecture.md"


def test_parseMultiFileOutput_noMarkers_returnsSingleFile():
    files = parse_multi_file_output("just plain text")
    assert len(files) == 1
    assert files[0]["name"] == "output.md"
    assert files[0]["content"] == "just plain text"


def test_parseMultiFileOutput_singleMarker_returnsOneFile():
    text = "===FILE: only.md===\nSingle file content"
    files = parse_multi_file_output(text)
    assert len(files) == 1
    assert files[0]["name"] == "only.md"


def test_parseMultiFileOutput_markerWithSpaces_trimmed():
    text = "===FILE:  spaced-name.md  ===\nContent"
    files = parse_multi_file_output(text)
    assert files[0]["name"] == "spaced-name.md"


# ── Structural tests ─────────────────────────────────────────────────────────

def test_chainDefinitions_onlyReadByDefinitionRunner():
    """Only definition_runner.py may read from chain/definitions/.

    Greps the chain module for references to the definitions directory
    outside definition_runner.py. Tests are exempt.
    """
    chain_dir = pathlib.Path(_dr.__file__).parent
    runner_path = chain_dir / "definition_runner.py"
    offenders: list[str] = []

    for py in chain_dir.rglob("*.py"):
        rel = py.relative_to(chain_dir)
        if py.resolve() == runner_path.resolve():
            continue
        if "tests" in rel.parts:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        for marker in ["definitions/", "definitions\\"]:
            if marker in text:
                lines = [
                    line.strip() for line in text.splitlines()
                    if marker in line
                    and not line.strip().startswith("#")
                    and "import" not in line.lower()
                ]
                if lines:
                    offenders.append(f"{rel}: {lines[0][:80]}")

    assert offenders == [], (
        "Only chain/definition_runner.py may read from chain/definitions/. "
        f"Use definition_runner.load_definition(chainId). Offenders: {offenders}"
    )


def test_chainDefinitions_contextBlocksExistInManifest():
    """Every context block referenced in a chain definition must exist in manifest.json."""
    defs_dir = pathlib.Path(_dr.__file__).parent / "definitions"
    manifest_path = pathlib.Path(_dr.__file__).parent.parent.parent / "context" / "manifest.json"

    if not manifest_path.exists():
        pytest.skip("manifest.json not yet created (Task 1)")

    manifest_keys = set(json.loads(manifest_path.read_text()).keys())
    missing: list[str] = []

    for f in defs_dir.glob("*.json"):
        raw = json.loads(f.read_text())
        for i, step in enumerate(raw.get("steps", [])):
            for block_name in step.get("context", []):
                if block_name not in manifest_keys:
                    missing.append(f"{f.name} step {i}: {block_name!r}")

    assert missing == [], (
        f"Chain definitions reference context blocks not in manifest.json: {missing}"
    )


def test_definitionRunner_mustNotImportProvidersDirectly():
    """Adapter boundary: definition_runner.py must call chain.adapter, not providers."""
    runner_text = pathlib.Path(_dr.__file__).read_text()
    assert "from .providers" not in runner_text, (
        "definition_runner.py must not import from providers directly. "
        "Call chain.adapter.generate() instead."
    )
    assert "from modules.chain.providers" not in runner_text, (
        "definition_runner.py must not import from providers directly."
    )
```

### File: `server/tests/test_text_chain_routes.py`

```python
"""Route tests for POST /api/text/chain.

Uses mock chain provider + mock context provider (forced via fixtures).
Tests require the Flask test client + db_session fixtures from the
existing conftest.py. Read server/tests/conftest.py or
server/modules/chain/tests/conftest.py to confirm fixture names.
"""
from __future__ import annotations

import uuid

import pytest

from modules.photoshoot.models import Generation, User


@pytest.fixture(autouse=True)
def _force_mocks(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")


class _H:
    """Test helpers — keep out of test names."""

    @staticmethod
    def make_user(db, *, chains_enabled: bool) -> User:
        features = {"text": True}
        if chains_enabled:
            features["text_chains"] = True
        u = User(
            email=f"chain-{uuid.uuid4().hex[:8]}@test.co",
            token=uuid.uuid4(),
            enabled_features=features,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    @staticmethod
    def bearer(u: User) -> dict:
        return {"Authorization": f"Bearer {u.token}"}


class TestChainEndpoint:
    def test_noBearer_returns401(self, client):
        r = client.post("/api/text/chain", json={"chainId": "deep-humanize", "input": "hi"})
        assert r.status_code == 401

    def test_featureDisabled_returns403(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=False)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": "some text"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 403
        body = r.get_json()
        assert "text_chains" in body.get("error", "") or "text_chains" in body.get("feature", "")

    def test_unknownChain_returns404(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "nonexistent-chain", "input": "text"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 404
        assert "not found" in r.get_json()["error"].lower()

    def test_missingInput_returns400(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 400

    def test_missingChainId_returns400(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"input": "some text"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 400

    def test_deepHumanize_returns200WithResult(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": "AI generated text to humanize"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert "generationId" in body
        assert uuid.UUID(body["generationId"])
        assert body["result"] is not None
        assert "MOCK[" in body["result"]
        assert body.get("files") is None

    def test_rewriteReview_returns200WithResult(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "rewrite-review", "input": "text with issues"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["result"] is not None
        assert body.get("files") is None

    def test_deepHumanize_persistsWithChainMetadata(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": "persist test"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200

        rows = db_session.query(Generation).filter(Generation.user_id == u.id).all()
        assert len(rows) == 1
        assert rows[0].feature == "text"
        assert rows[0].chain_id == "deep-humanize"
        assert rows[0].step_count == 3
        assert rows[0].input_text == "persist test"
        assert rows[0].result_text is not None

    def test_emptyInput_returns400(self, client, db_session):
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": ""},
            headers=_H.bearer(u),
        )
        assert r.status_code == 400

    def test_existingSingleShotRoutes_stillWork(self, client, db_session):
        """Regression: chain endpoint does not break existing /rewrite and /generate."""
        u = _H.make_user(db_session, chains_enabled=True)
        r = client.post(
            "/api/text/rewrite",
            json={"text": "hello world", "mode": "humanize"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200
```

---

## 6. Commit Plan

### Commit 1: `feat(chain): add chain definition JSON files`

**Scope**: `server/modules/chain/definitions/deep-humanize.json`, `braindump-to-docs.json`, `rewrite-review.json`.

**Boundary**: Data files only. No Python code.

### Commit 2: `feat(chain): add chainCompleted blinker signal`

**Scope**: `server/modules/chain/signals.py`.

**Boundary**: Signal definition only.

### Commit 3: `feat(chain): add schema-driven definition runner with STEP_HANDLERS dispatch`

**Scope**: `server/modules/chain/definition_runner.py`, updated `server/modules/chain/__init__.py`.

**Boundary**: Runner logic + module exports. No routes, no persistence, no migration.

### Commit 4: `feat(db): add chain_id + step_count columns to superapp_generations`

**Scope**: `server/migrations/versions/{rev}_add_chain_columns.py`, updated `server/modules/photoshoot/models.py`.

**Boundary**: Schema change only.

### Commit 5: `feat(text): add POST /api/text/chain endpoint with feature gate`

**Scope**: `server/modules/text/chain_dto.py`, `chain_service.py`, `chain_routes.py`, updated `server/modules/text/repository.py`, updated `server/app.py`.

**Boundary**: Full endpoint wiring.

### Commit 6: `test(chain): add definition runner + chain endpoint tests`

**Scope**: `server/modules/chain/tests/test_definition_runner.py`, `server/tests/test_text_chain_routes.py`.

**Boundary**: Tests only. Run full suite after this commit.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/bubls/server
python -m pytest --tb=short -v
```

**Expected delta**: baseline + 27 new tests passing.

Breakdown:
- `test_definition_runner.py`: 17 tests (4 loading + 2 STEP_HANDLERS + 5 run_definition + 4 parse_multi_file + 3 structural)
- `test_text_chain_routes.py`: 10 tests (1 auth + 1 feature gate + 1 not found + 2 validation + 2 happy path + 1 persistence + 1 empty input + 1 regression)

Zero pre-existing tests broken. Existing single-shot `/api/text/rewrite` and `/api/text/generate` must still pass.

---

## 8. Rollback

### Per-step rollback

| Step | Rollback |
|------|----------|
| Step 1 (definition JSONs) | `rm -rf server/modules/chain/definitions/` |
| Step 2 (signals) | `rm server/modules/chain/signals.py` |
| Step 3 (definition runner) | `rm server/modules/chain/definition_runner.py`; revert `__init__.py` |
| Step 4 (migration) | `rm server/migrations/versions/*_add_chain_columns.py`; if applied to DB: `alembic downgrade -1` [REQUIRES APPROVAL] |
| Step 5 (Generation model) | Revert `server/modules/photoshoot/models.py` (remove 2 lines) |
| Step 6 (repository) | Revert `server/modules/text/repository.py` (remove `create_chain_generation`) |
| Step 7 (DTOs) | `rm server/modules/text/chain_dto.py` |
| Step 8 (chain service) | `rm server/modules/text/chain_service.py` |
| Step 9 (chain routes) | `rm server/modules/text/chain_routes.py` |
| Step 10 (app.py) | Revert `server/app.py` (remove chain_routes from ENABLED_MODULES) |
| Step 11 (__init__.py) | Revert `server/modules/chain/__init__.py` |

### Per-branch rollback

```bash
git checkout main -- server/
git branch -D feat/chain-definition-runner
```

If the Alembic migration has been applied to a live database, run `alembic downgrade -1` before deleting the migration file. [REQUIRES APPROVAL]

---

## 9. Deviations Allowed

| Situation | Action |
|-----------|--------|
| `blinker` not installed / import fails | Install via `pip install blinker` (Flask depends on it). If truly absent, add to `requirements.txt`. Log in commit body. |
| Task 1 (context loader) not merged | Safe to proceed. conftest forces `CONTEXT_PROVIDER=mock`. `load_blocks` returns fixture strings. No file I/O. |
| `require_feature` decorator doesn't exist / has different name | Read `server/core/auth.py` (or `server/core/middleware.py`) for the actual feature-gate decorator. Adapt import. Log deviation. |
| `ENABLED_MODULES` registration doesn't support `modules.text.chain_routes` | Merge chain route into existing text blueprint by importing `chain_routes.bp` in `text/routes.py`. Log deviation. |
| `Generation` model column names differ from documented (`result_text`, `feature`, `input_text`) | Read `server/modules/photoshoot/models.py` and adapt column names. Log deviation. |
| `client` / `db_session` test fixtures have different names | Read `server/tests/conftest.py` for actual fixture names. Adapt tests. Log deviation. |
| Pydantic v1 in the environment (no `model_validate`) | Use `parse_obj` / `dict()` instead. The codebase should be on v2 (`model_validate`, `model_dump`). |
| Latest Alembic revision differs from example | FILL IN `down_revision` from pre-flight. Do not guess. |
| Existing test count differs from baseline by more than 2 | STOP. Investigate whether another branch was merged. Re-record baseline before continuing. |

---

## 10. Out of Scope

This task builds the runner, endpoint, and definitions — the execution backbone for Text Chains. It does **not** ship real prompt content, frontend UI, or advanced chain features. Executor must **STOP and flag** if implementation pulls toward any of these:

- **Real prompt content for humanize passes** — Task 3 ports PASS_1/PASS_2/PASS_3 from humanize-me into the placeholder context files. This task only creates the chain definition JSON that references those block names.
- **Braindump prompt content** — Task 4 ports spec-doc's generation template. This task only creates the definition JSON.
- **Review-step JSON parsing + fix-step issue injection** — Task 5 adds `_parse_review_json` and the injection logic into `_handle_review`. This task's `_handle_review` is a plain adapter call that returns the LLM's text output; it does not parse JSON or inject issues.
- **SSE/streaming per chain step** — deferred until chains exceed 30s with user-reported perceived hangs. Current implementation returns synchronous JSON response matching existing `/api/text/rewrite` pattern.
- **`RunnerAdapter` interface (abstract base)** — extract when a second execution strategy appears (parallel steps, streaming, retry). One concrete sequential runner is the only consumer.
- **Per-chain feature gating (`enabled_features.chain:deep-humanize`)** — single `text_chains` flag gates all chains for v1. Split when pricing tiers diverge per chain.
- **`chain_call` + `chain_signal` database tables** — extract when cost tracking becomes a reporting requirement, not just logging.
- **Retry/backoff machinery in the runner** — the Anthropic SDK handles retries internally (`timeout=60, max_retries=2`). No runner-level retry until a real failure teaches us a retry budget.
- **Chain Mode UI (buttons + tabbed output)** — Task 6 builds the frontend. Zero `src/app/` changes in this task.
- **Cost analytics subscriber for `chainCompleted`** — the signal is emitted; no subscriber wired yet. Build when cost dashboard is scoped.
- **OpenAPI spec for chain endpoint** — YAML file deferred; hand-authored DTOs match the existing `modules/text/dto.py` pattern for now.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) — Design rationale, system boundaries diagram, STEP_HANDLERS dispatch design
- [Epic](./epic.md) — Task scope, success criteria, dependencies
- [Timeline](./timeline.md) — Status tracking (update after done)