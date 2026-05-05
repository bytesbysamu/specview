# spec-doc-api — Sequential Chain Runner (port from Bubls)

> **OBSOLETE — superseded by the Workflows-as-a-Domain-Layer epic** (landed
> 2026-04-26, master at commit `6083160`).
>
> `WorkflowRuntime.run(execution, workflow)` is a strict superset of what
> this brain dump proposed: it provides the sequential step driver, plus
> a state machine, plus typed domain events, plus a repository for loading
> named workflows, plus per-feature ownership via Bounded Context.
>
> Do not generate a spec from this file. The capability is shipped.

---

## (Original brain dump below — do not act on)

## What

Port the `sequential(steps)` chain runner from Bubls into `modules/chain/runner.py`. Replace the manually unrolled `analysis → epic → architecture` calls in `_run_bootstrap` with a declarative step list. Same observable behavior, cleaner internals.

Bubls has a proven `ChainStep` / `sequential()` pattern: each step is a callable that receives the previous step's output and returns the next prompt + a way to extract the value. The bootstrap chain is exactly three steps in a fixed sequence — a perfect fit.

### 1. modules/chain/runner.py — new file

```python
"""Sequential chain runner — port of Bubls ChainRunner."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from modules.chain import adapter as chain_adapter


@dataclass
class ChainStep:
    name: str
    build_prompt: Callable[..., tuple[str, str]]   # (...) → (system, user)
    extract: Callable[[str], object] = field(default=lambda x: x)  # raw text by default
    max_tokens: int = 4096


@dataclass
class ChainResult:
    steps: dict[str, object]  # step_name → extracted value
    latency_ms: int


def sequential(steps: list[ChainStep], **kwargs) -> ChainResult:
    """Run steps in order, passing kwargs + prior results to each build_prompt."""
    t0 = time.monotonic()
    results: dict[str, object] = {}
    for step in steps:
        system, user = step.build_prompt(**kwargs, **results)
        raw = chain_adapter.generate(system, user, max_tokens=step.max_tokens).text
        results[step.name] = step.extract(raw)
    return ChainResult(steps=results, latency_ms=int((time.monotonic() - t0) * 1000))
```

### 2. modules/ai/routes.py — replace unrolled chain calls

Before (three explicit AI calls):
```python
sys1, u1 = bootstrap_analysis_prompt(braindump, project_name, builder)
analysis = chain_adapter.generate(sys1, u1).text

sys2, u2 = bootstrap_epic_prompt(braindump, project_name, analysis, builder, principles)
epic = chain_adapter.generate(sys2, u2).text

sys3, u3 = bootstrap_architecture_prompt(braindump, project_name, epic, builder, principles, codebase, references)
architecture = chain_adapter.generate(sys3, u3).text
```

After (declarative):
```python
from modules.chain.runner import ChainStep, sequential

BOOTSTRAP_STEPS = [
    ChainStep("analysis", bootstrap_analysis_prompt),
    ChainStep("epic",     bootstrap_epic_prompt),
    ChainStep("architecture", bootstrap_architecture_prompt, max_tokens=16384),
]

chain_result = sequential(
    BOOTSTRAP_STEPS,
    braindump=braindump,
    project_name=project_name,
    builder=builder,
    principles=principles,
    codebase=codebase,
    references=references,
)
analysis     = chain_result.steps["analysis"]
epic         = chain_result.steps["epic"]
architecture = chain_result.steps["architecture"]
```

Each `build_prompt` function already takes keyword arguments — no signature changes needed.

### 3. Prompt functions — accept **kwargs

Current `bootstrap_epic_prompt(braindump, project_name, analysis, builder, principles)` uses positional args. Add `**_` so the runner can pass the full accumulated dict without KeyError:

```python
def bootstrap_epic_prompt(braindump, project_name, analysis="", builder="", principles="", **_):
    ...
```

Same for `bootstrap_architecture_prompt`. `bootstrap_analysis_prompt` needs no change (first step, no prior results).

### 4. Unit tests — runner is pure

```python
# modules/chain/tests/test_runner.py
def test_sequential_passes_prior_results(monkeypatch):
    calls = []
    def fake_generate(system, user, *, max_tokens=4096):
        calls.append(user)
        return FakeResult(f"out{len(calls)}")
    monkeypatch.setattr(chain_adapter, "generate", fake_generate)

    steps = [
        ChainStep("first",  lambda **kw: ("sys", f"input={kw['x']}")),
        ChainStep("second", lambda **kw: ("sys", f"first={kw['first']}")),
    ]
    result = sequential(steps, x="hello")
    assert result.steps["first"] == "out1"
    assert "first=out1" in calls[1]
```

## Why now

The bootstrap route has 60+ lines of scaffolding around three AI calls. Adding a fourth step (e.g., a timeline scaffold, a spec-index) means copy-pasting the pattern again. The runner makes that a one-line addition to `BOOTSTRAP_STEPS`. The refactor also makes step-level error handling, logging, and latency tracking a single cross-cutting change rather than three repetitions.

The Bubls port costs ~40 lines. The cleanup saves more than that.

## What's missing

One decision: **step-level error isolation**. Should a failure in step 2 abort the chain (current behavior) or write partial results (steps 1 and 2 files) and report a partial error? Options:
- (a) Abort on first failure (proposed) — simplest, consistent with current behavior
- (b) Write partial results + mark chain as partially done — more complex, marginal UX gain

Option (a) for now. Option (b) could follow from the retry/recovery braindump.

## Explicitly out of scope

- Parallel step execution — bootstrap steps have data dependencies, must be sequential
- Step result caching — no repeated runs in the same session that would benefit
- Dynamic step list from config — BOOTSTRAP_STEPS is code, not data
- DAG / branching chains — not needed until a non-linear chain is required
