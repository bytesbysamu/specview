# 🛠️ Task 6: Photoshoot retrofit onto primitive

**Purpose**: Prove the chain primitive generalises by running `photoshoot`'s existing generation pipeline through `chain.run_chain` / `chain.adapter`. Zero user-facing change. Tests stop mocking Claude/Replicate clients and start mocking the primitive boundary instead.

**Effort**: 1 day

**Dependencies**: Task 1 (`superapp_users.builder` / `superapp_users.principles` columns), Task 2 (`server/modules/chain/{adapter,runner,types,errors}.py`). Both shipped.

**Parallel With**: —

**Blocks**: Epic 3 signal/aggregation work — without a second chain consumer the primitive's cost/shape calibration remains a one-instance abstraction.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The chain primitive landed in Task 2 as `sequential(steps, initial)` + `adapter.generate/stream` + `ChainResult` — intentionally **without** the declarative `ChainDefinition` / `ChainStep` / `ChainEvent` types the architecture doc proposed, because photoshoot hadn't yet pulled on the shape. This task is the second consumer. It calibrates the primitive by wrapping photoshoot's existing pipeline in a `pipeline.py` module of step callables that `service.py` hands to `run_chain`. Any Claude call currently made by photoshoot (prompt synthesis, caption analysis, safety check — whatever `service.py` actually does) gets routed through `chain.adapter.generate` rather than an inlined Anthropic client, which closes the adapter-boundary invariant for the second feature. Replicate LoRA inference stays as a plain callable inside `photoshoot` — it's still a single consumer and dragging it into `chain.providers` would re-open the speculative-infrastructure trap Task 2 just closed.

**Trade-offs considered**:
- **Introduce `ChainDefinition` declarative types now** — rejected because Task 2 deferred these with an explicit trigger ("second non-photoshoot consumer"). Photoshoot is still the second-ever chain user; calibrating declarative types off two consumers where one is the template is premature.
- **Move Replicate into `chain/providers/replicate.py`** — rejected because no second Replicate consumer exists. `chain.adapter` today is Claude-shaped (`system`, `prompt`, `model`, `max_tokens`); shoehorning an image-inference SDK into it would bend the adapter to fit one caller.
- **List-of-callables via `run_chain` (chosen)** — preferred because it matches the exact shape Task 2 shipped, validates the primitive with a structurally different pipeline (mixes Claude + Replicate + DB writes), and leaves `ChainDefinition` to calibrate off a third consumer that exercises branching or retry needs.

---

## 2. Pre-flight

Run BEFORE editing any file. The refactor must not start until the executor has read the current `service.py` — its exact step count, provider mix, and test harness dictate every subsequent decision.

```bash
git status                                                                    # Flag any unrelated M/?? entries
git diff HEAD -- server/modules/photoshoot server/modules/chain server/tests  # Confirm target trees are clean
cd server && pytest -q modules/photoshoot modules/chain tests                 # Baseline; record the pass count
cd server && pytest -q modules/chain/tests/test_adapter.py::test_featureModules_mustNotImportProvidersDirectly  # Must pass before we start
grep -rn "anthropic\|replicate\|claude" server/modules/photoshoot --include="*.py"  # Enumerate every provider touchpoint
grep -rn "from server.modules.chain" server/modules/photoshoot --include="*.py"     # Current chain usage (expected: none)
wc -l server/modules/photoshoot/service.py                                    # Size of the refactor target
```

Then **read in full** before designing the pipeline split:
- `server/modules/photoshoot/service.py` — the pipeline body
- `server/modules/photoshoot/routes.py` — what `service.generate_*` is called with and what it returns
- `server/modules/photoshoot/repository.py` — where persistence happens (must stay in the repo, not a chain step)
- `server/tests/test_service.py` — current mock shape (likely monkeypatches an Anthropic / Replicate client)
- `server/tests/test_routes.py` — feature-level end-to-end; the one that must pass unchanged
- `server/modules/chain/__init__.py` + `server/modules/chain/adapter.py` + `server/modules/chain/runner.py` — the import surface you will use

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**Baseline recorded**: write `<N passing, 0 failing>` in the first commit body.

---

## 3. Files

### To Create (new)

- `server/modules/photoshoot/pipeline.py` (new) — pure functions, one per current pipeline stage. Each takes prior output, returns next. Signature mirrors `runner.sequential`'s contract: `step(prev) -> next`. Claude-bound stages delegate to `chain.adapter.generate(...)`; Replicate-bound stages call `replicate.run(...)` directly. No persistence, no Flask context — these are unit-testable callables.
- `server/tests/test_photoshoot_pipeline.py` (new) — unit tests for each step in isolation, with `chain.adapter.generate` and `replicate.run` monkeypatched to deterministic fakes. Asserts step-composition invariants (output of step N is accepted as input of step N+1).
- `server/tests/test_photoshoot_chain_retrofit.py` (new) — feature-level test that monkeypatches `server.modules.photoshoot.service.run_chain` to a fake and asserts `service.generate_*` still produces the same `Generation` row shape. This is the test that proves "tests updated to mock the primitive instead of the underlying providers" from the epic.

### To Modify (cite CODEBASE CONTEXT)

- `server/modules/photoshoot/service.py` (cited in codebase.md as `modules/photoshoot/service.*`) — replace inline provider calls with `from server.modules.chain import run_chain` + `from .pipeline import STEPS` (or per-call-site equivalent). Orchestration body shrinks to: build input → `run_chain(STEPS, user=user, initial=initial_input)` → persist result via `repository.*` → return DTO. Prompts unchanged. Return shape unchanged.
- `server/tests/test_service.py` (cited in codebase.md) — replace provider-client monkeypatches with runner-boundary monkeypatches. Any test that previously stubbed an anthropic / replicate client must now stub `run_chain` or `chain.adapter.generate`. Assertion targets (output shape, DB writes, error mapping) unchanged.

### To Leave Alone

- `server/modules/chain/**` — Task 2 is frozen; no new providers, no new types, no new runner signatures. If the retrofit would require a signature change, STOP and flag per Deviations.
- `server/modules/photoshoot/models.py`, `repository.py`, `dto.py`, `routes.py` — persistence, HTTP shape, and SQLAlchemy models are orthogonal to the retrofit. Routes call `service.*` which now runs the chain internally; the route signature does not change.
- `server/modules/photoshoot/*.yaml` under `server/openapi/` — contract unchanged, no regeneration needed.
- `server/tests/test_repository.py`, `server/tests/test_routes.py` — these must pass **unchanged**. They are the end-to-end guarantee that user-facing behaviour is identical.
- `server/migrations/**` — no schema change. `chain_call` / `chain_signal` tables are still deferred.
- Any `src/app/**` frontend file — zero client-side change.

---

## 4. Implementation Steps

### Step 1: Inventory the current pipeline

**Action**: From the files opened in Pre-flight, produce a numbered list of pipeline stages in `service.py`. For each stage record: (a) inputs, (b) provider (Claude / Replicate / pure-Python), (c) output type, (d) whether it writes to the DB. Stages that touch the DB are NOT chain steps — they remain in `service.py` around the `run_chain` call.

**File**: (inspection only — no edits yet)

**Pattern**: write the inventory as a plain comment block at the top of the eventual `pipeline.py`. Example shape:

```
# Inventory (from service.py @ <sha-of-baseline>):
# 1. build_prompt(req)           → pure: composes Replicate prompt string
# 2. call_replicate(prompt)      → Replicate: returns image URL
# 3. (persistence)               → repository.save_generation  ← stays in service.py
```

**Verify**: the inventory enumerates every `anthropic.*` / `replicate.*` / `client.messages.create` call that `grep` surfaced in Pre-flight. If the grep found 4 calls and the inventory lists 3, something was missed — re-read.

### Step 2: Create `pipeline.py` with step callables

**Action**: Create `server/modules/photoshoot/pipeline.py`. Export one callable per non-persistence stage. Each accepts the prior stage's output (or `initial` for stage 0) and returns the next stage's input. Claude stages call `chain.adapter.generate(...)`; Replicate stages call the Replicate SDK directly. No globals, no I/O besides the provider call, no exception swallowing — let `chain.errors.ProviderError` propagate.

**File**: `server/modules/photoshoot/pipeline.py` (new)

**Pattern**:

```python
"""Photoshoot pipeline steps — consumed by service.py via chain.run_chain.

Each step is a callable: (prev_output) -> next_input. Composition happens in
service.py; this module stays side-effect-free aside from the provider call it
owns. Claude stages go through chain.adapter; Replicate stages stay local
(single consumer — no premature move to chain.providers)."""

from dataclasses import dataclass
from typing import Any

import replicate  # existing dep used by service.py today

from server.modules.chain import adapter
from server.modules.chain.types import ChainResult


@dataclass(frozen=True)
class PhotoshootInput:
    user_prompt: str
    lora_model_id: str
    # add exactly the fields service.py currently passes; no extras


# --- step 1: prompt synthesis (IF service.py currently calls Claude here) ---
def synthesize_prompt(prev: PhotoshootInput) -> str:
    """Expand the user's raw prompt into a LoRA-ready prompt via Claude.
    Pulls builder + principles context via the adapter boundary (feature='photoshoot')."""
    result: ChainResult = adapter.generate(
        system=SYNTHESIS_SYSTEM_PROMPT,   # ← port verbatim from service.py
        prompt=prev.user_prompt,
        feature="photoshoot",
    )
    return result.text


# --- step 2: Replicate inference ---
def run_inference(prompt: str) -> str:
    """Run Replicate LoRA; return the image URL."""
    output = replicate.run(REPLICATE_MODEL_REF, input={"prompt": prompt, ...})
    return output[0] if isinstance(output, list) else output


STEPS = [synthesize_prompt, run_inference]  # order matches service.py today

# Port SYNTHESIS_SYSTEM_PROMPT + REPLICATE_MODEL_REF *verbatim* from service.py.
# Prompts are unchanged per the epic — do not reword.
```

Adapt the inventory: **the executor fills in `STEPS` with exactly the stages found in Step 1**. If there is only one Claude stage and no Replicate, `STEPS` has one entry. If the current `service.py` has no Claude call at all, STEPS is `[run_inference]` and the `adapter.generate` import moves to a future task — see Deviations.

**Verify**: `cd server && python -c "from server.modules.photoshoot.pipeline import STEPS; print(len(STEPS))"` — should print the inventory count from Step 1.

### Step 3: Rewrite `service.py` to run via `run_chain`

**Action**: Replace the inline orchestration in `service.py` with a call to `run_chain`. Persistence stays in `service.py` — the repository call wraps `run_chain`, not the other way around.

**File**: `server/modules/photoshoot/service.py` (cited in codebase.md)

**Pattern**:

```python
from server.modules.chain import run_chain
from .pipeline import STEPS, PhotoshootInput
from .repository import save_generation


def generate_image(user, req):
    """Orchestrate the photoshoot pipeline. Prompts and outputs unchanged."""
    initial = PhotoshootInput(
        user_prompt=req.prompt,
        lora_model_id=req.lora_model_id,
    )
    image_url = run_chain(STEPS, user=user, initial=initial)
    return save_generation(user=user, prompt=req.prompt, image_url=image_url)
```

Match the actual `generate_image` signature and `Generation` return shape discovered in Pre-flight. Do not change what the route receives.

**Verify**:
- `cd server && grep -n "anthropic\|replicate" server/modules/photoshoot/service.py` — expect **zero** matches (all provider work migrated to `pipeline.py`).
- `cd server && grep -n "from server.modules.chain import" server/modules/photoshoot/service.py` — expect exactly one import line pulling `run_chain`.

### Step 4: Update `test_service.py` to mock the primitive

**Action**: For every existing test in `server/tests/test_service.py` that previously monkeypatched an Anthropic or Replicate client, replace the patch target with `server.modules.photoshoot.service.run_chain`. Return the deterministic value the real chain would have produced. Assertion bodies stay the same — they test service-level behaviour.

**File**: `server/tests/test_service.py` (cited in codebase.md)

**Pattern**:

```python
import server.modules.photoshoot.service as svc


def test_generateImage_persistsGenerationWithImageUrlFromChain(monkeypatch, db_session, test_user):
    """service.generate_image must persist a Generation row whose image_url
    equals what run_chain returned. Mocking run_chain suppresses all real
    provider work — no anthropic, no replicate clients reached in this test."""
    monkeypatch.setattr(svc, "run_chain", lambda steps, *, user, initial: "https://cdn.fake/out.png")

    req = svc.PhotoshootRequest(prompt="a cat on a boat", lora_model_id="lora-1")
    generation = svc.generate_image(test_user, req)

    assert generation.image_url == "https://cdn.fake/out.png"
    assert generation.prompt == "a cat on a boat"
    assert generation.user_id == test_user.id
    # row persisted
    assert db_session.query(svc.Generation).filter_by(id=generation.id).count() == 1


def test_generateImage_propagatesProviderError(monkeypatch, test_user):
    """A ProviderError raised inside run_chain must bubble out of service.generate_image
    unchanged — service layer does not swallow primitive errors."""
    from server.modules.chain.errors import ProviderError

    def boom(steps, *, user, initial):
        raise ProviderError("claude down", status_code=502)

    monkeypatch.setattr(svc, "run_chain", boom)

    req = svc.PhotoshootRequest(prompt="x", lora_model_id="lora-1")
    with pytest.raises(ProviderError) as exc:
        svc.generate_image(test_user, req)
    assert exc.value.status_code == 502
```

Any test whose assertion was about the provider SDK itself (e.g., "anthropic.messages.create was called with max_tokens=4096") must be **deleted** — it tested infrastructure that now belongs to Task 2's `test_adapter.py`. Log each deletion in the commit body as a deviation with the deleted test name.

**Verify**: `cd server && pytest -q tests/test_service.py` — all retained tests pass; no test imports `anthropic` or `replicate` directly.

### Step 5: Add the pipeline unit tests

**Action**: Create `server/tests/test_photoshoot_pipeline.py`. Test each step in isolation with the provider it actually uses mocked.

**File**: `server/tests/test_photoshoot_pipeline.py` (new)

**Pattern**:

```python
import pytest

from server.modules.chain.types import ChainResult
from server.modules.photoshoot import pipeline as pl


def test_synthesizePrompt_callsAdapterWithFeatureTag(monkeypatch):
    """Step must go through chain.adapter.generate and pass feature='photoshoot'
    so the adapter injects photoshoot-namespaced principles."""
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return ChainResult(text="expanded prompt", latency_ms=42)

    monkeypatch.setattr(pl.adapter, "generate", fake_generate)

    out = pl.synthesize_prompt(pl.PhotoshootInput(user_prompt="cat", lora_model_id="lora-1"))

    assert out == "expanded prompt"
    assert captured["feature"] == "photoshoot"
    assert captured["prompt"] == "cat"
    assert "system" in captured  # the stage's system prompt was passed


def test_runInference_callsReplicateAndReturnsUrl(monkeypatch):
    """Step must invoke replicate.run and return the resulting URL."""
    monkeypatch.setattr(pl.replicate, "run", lambda *a, **kw: ["https://cdn.fake/x.png"])

    url = pl.run_inference("expanded prompt")

    assert url == "https://cdn.fake/x.png"


def test_STEPS_composableChain(monkeypatch):
    """Output of each step must be an acceptable input to the next."""
    monkeypatch.setattr(pl.adapter, "generate", lambda **kw: ChainResult(text="p", latency_ms=1))
    monkeypatch.setattr(pl.replicate, "run", lambda *a, **kw: ["https://cdn.fake/x.png"])

    prev = pl.PhotoshootInput(user_prompt="cat", lora_model_id="lora-1")
    for step in pl.STEPS:
        prev = step(prev)

    assert prev == "https://cdn.fake/x.png"
```

Adjust the step list + assertions to match what Step 1's inventory actually produced. If `STEPS` contains only `run_inference`, delete `test_synthesizePrompt_*` and keep the Replicate + composition tests.

**Verify**: `cd server && pytest -q tests/test_photoshoot_pipeline.py` — all tests pass.

### Step 6: Add the retrofit-level test that closes the primitive-mock contract

**Action**: Create `server/tests/test_photoshoot_chain_retrofit.py`. This is the test the epic calls for: photoshoot's tests now mock the primitive, not the underlying providers.

**File**: `server/tests/test_photoshoot_chain_retrofit.py` (new)

**Pattern**:

```python
import pathlib

import pytest

import server.modules.photoshoot.service as svc


def test_generateImage_zeroProviderSDKReached(monkeypatch, db_session, test_user):
    """End-to-end guarantee: service.generate_image must not touch anthropic or
    replicate modules when run_chain is mocked. Proves the primitive is the
    single seam feature tests rely on."""
    anthropic_hits = []
    replicate_hits = []

    import anthropic as _a
    import replicate as _r
    monkeypatch.setattr(_a, "Anthropic", lambda *a, **kw: anthropic_hits.append(kw) or (_ for _ in ()).throw(RuntimeError("anthropic reached")))
    monkeypatch.setattr(_r, "run", lambda *a, **kw: replicate_hits.append(kw) or (_ for _ in ()).throw(RuntimeError("replicate reached")))
    monkeypatch.setattr(svc, "run_chain", lambda steps, *, user, initial: "https://cdn.fake/ok.png")

    req = svc.PhotoshootRequest(prompt="cat", lora_model_id="lora-1")
    gen = svc.generate_image(test_user, req)

    assert gen.image_url == "https://cdn.fake/ok.png"
    assert anthropic_hits == []
    assert replicate_hits == []


def test_photoshoot_mustNotImportChainProvidersDirectly():
    """Structural test — mirrors chain/tests/test_adapter.py's rule at the
    feature level. Any file under server/modules/photoshoot importing from
    chain.providers.* is an adapter-boundary violation."""
    import server.modules.photoshoot as ps_pkg

    ps_dir = pathlib.Path(ps_pkg.__file__).parent
    forbidden_needles = (
        "from server.modules.chain.providers",
        "from ..chain.providers",
        "import server.modules.chain.providers",
    )
    offenders = []
    for py in ps_dir.rglob("*.py"):
        text = py.read_text()
        if any(needle in text for needle in forbidden_needles):
            offenders.append(str(py.relative_to(ps_dir)))
    assert offenders == [], (
        f"photoshoot must go through chain.adapter — offenders: {offenders}. "
        f"Fix: replace the direct providers.* import with `from server.modules.chain import adapter`."
    )
```

**Verify**: `cd server && pytest -q tests/test_photoshoot_chain_retrofit.py -v` — both tests pass.

### Step 7: Confirm the end-to-end route test still passes unchanged

**Action**: Do **not** edit `server/tests/test_routes.py`. Run it. The epic's acceptance signal is "zero user-facing change verified by existing end-to-end photoshoot test."

**File**: (no edit)

**Verify**: `cd server && pytest -q tests/test_routes.py` — same test count and same pass count as Pre-flight baseline. If any `test_routes.py` test fails, the refactor leaked a user-facing change — roll back to Step 3 and inspect.

---

## 5. Tests

All test code above is final. Summary of new assertion bodies:

- `test_photoshoot_pipeline.py::test_synthesizePrompt_callsAdapterWithFeatureTag` — asserts `feature="photoshoot"` reaches the adapter so principles namespace resolves correctly.
- `test_photoshoot_pipeline.py::test_runInference_callsReplicateAndReturnsUrl` — asserts Replicate output is returned as URL string.
- `test_photoshoot_pipeline.py::test_STEPS_composableChain` — asserts each step's output is a valid input for the next.
- `test_photoshoot_chain_retrofit.py::test_generateImage_zeroProviderSDKReached` — asserts the primitive is the only seam: with `run_chain` mocked, zero SDK imports are reached.
- `test_photoshoot_chain_retrofit.py::test_photoshoot_mustNotImportChainProvidersDirectly` — structural test; greps `server/modules/photoshoot/` for forbidden direct-provider imports.
- `test_service.py::test_generateImage_persistsGenerationWithImageUrlFromChain` — asserts persistence uses what `run_chain` returned.
- `test_service.py::test_generateImage_propagatesProviderError` — asserts `ProviderError` bubbles up unchanged.

Framework: pytest (matches `server/modules/chain/tests/` convention per Task 2). No Jasmine / no `describe` blocks — that's frontend only and this task is backend-only.

---

## 6. Commit Plan

One commit per logical unit. Every commit body includes `Baseline:` (pass count from Pre-flight) in the first commit and `Deviations:` if the executor diverged from the guide.

1. `refactor(photoshoot): extract pipeline steps into pipeline.py` — adds `server/modules/photoshoot/pipeline.py`; no behaviour change; `service.py` untouched; tests untouched. Verify: `pytest -q modules/photoshoot tests` passes at the same count as Pre-flight.
2. `refactor(photoshoot): run via chain primitive` — rewrites `service.py` to call `run_chain(STEPS, user, initial)`; prompts and DTOs unchanged. This is the epic's commit message, verbatim.
3. `test(photoshoot): mock chain primitive instead of provider SDKs` — updates `test_service.py` + adds `test_photoshoot_pipeline.py` + adds `test_photoshoot_chain_retrofit.py`. Commit body lists every deleted SDK-level test by name.

**Deviation logging**: if a step deviates, prefix the commit body with `Deviations:` and one line per deviation. Example: `Deviations: service.py had no Claude stage today; STEPS is [run_inference] only. test_synthesizePrompt_* deleted.`

---

## 7. Verification

```bash
cd server && pytest -q modules/photoshoot modules/chain tests
```

**Expected delta**: baseline `N` → `N + 5 to N + 7` passing (3 pipeline tests + 2 retrofit tests + 2 service tests if the current service had a Claude stage; 5 total if Claude-less). **Zero pre-existing tests broken.** Zero new failures.

Additional sanity checks:

```bash
cd server && pytest -q modules/chain/tests/test_adapter.py::test_featureModules_mustNotImportProvidersDirectly       # Task 2's invariant still holds
cd server && pytest -q tests/test_photoshoot_chain_retrofit.py::test_photoshoot_mustNotImportChainProvidersDirectly  # New feature-level invariant
cd server && grep -rn "anthropic\|replicate" server/modules/photoshoot --include="*.py"                              # Provider usage isolated to pipeline.py only
```

---

## 8. Rollback

- **Per-step**: each of the three commits is independently revertible. `git revert <sha>` in reverse order restores prior state. Commit 1 (`pipeline.py`) is purely additive — reverting it alone leaves the codebase working.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (captured during Pre-flight via `git rev-parse HEAD`). `pipeline.py` being new means deletion is clean. Do not force-push.

---

## 9. Deviations Allowed

- **Current `service.py` has no Claude stage** → `STEPS = [run_inference]` only. Delete `test_synthesizePrompt_*`. Note the deviation in commit 2's body. The retrofit still validates the primitive — a one-step chain is a legitimate calibration.
- **Current `service.py` has more than two stages** (e.g., vision analysis → prompt synthesis → inference) → add one callable per stage to `STEPS`, preserving order. Add one pipeline test per stage following the template in Step 5.
- **Persistence is interleaved between pipeline stages** (e.g., a `WIP_Generation` row gets created after prompt synthesis) → DO NOT move the DB call into a step. Split the `run_chain` call into two (`run_chain(STEPS_PRE_PERSIST, ...)` → repo write → `run_chain(STEPS_POST_PERSIST, ...)`). Log as a deviation.
- **`pipeline.py` import of `replicate` breaks mypy / pytest collection** → check `server/requirements.txt` for the `replicate` package; if missing, the current `service.py` must be using a different image provider — use that provider's module instead, keep the shape identical.
- **A pre-existing `test_service.py` test asserts on a provider SDK call directly** (e.g., `mock_anthropic.messages.create.assert_called_once_with(...)`) → delete it. Those assertions now belong to `chain/tests/test_adapter.py`. List each deletion by name in commit 3's body.
- **Signature mismatch between the guide's pseudo-types and reality** (e.g., `service.generate_image` takes different parameters) → adapt the call site to reality; do not invent wrapper functions to match the guide. The guide's `PhotoshootInput` dataclass is a suggestion; a tuple or existing DTO works identically.
- **`run_chain` signature doesn't accept `user=`/`initial=` kwargs** → verify against Task 2's shipped `server/modules/chain/runner.py`. If the shipped signature is `run_chain(steps, user, initial)` positional, adjust the call accordingly. If a required kwarg is missing entirely from Task 2, STOP — do not add it to Task 2's code, which is frozen.
- **Step N unlocks an obvious simplification in Step N+1** → take it; log in the commit body.
- **Side-effects** (push, publish, schema change, dependency install beyond what `server/requirements.txt` already pins) → `[REQUIRES APPROVAL]`, stop, ask.

---

## 10. Out of Scope

This task refactors photoshoot to consume the chain primitive as it shipped in Task 2 — nothing more. The architecture doc proposes several elaborations (declarative `ChainDefinition` types, `chain_call` / `chain_signal` tables, SSE event streaming, cost tracking, retry budgets, a Replicate provider inside the chain module) that an eager executor will feel drawn toward because "now there are two consumers, clearly the abstraction is ready." It isn't. Task 2's deferrals were calibrated against the rule *"infrastructure with one consumer = speculative debt."* Two consumers is still insufficient for any of the items below — each needs either a specific pain signal or a third consumer before it ships.

- **`ChainDefinition` / `ChainStep` / `ChainEvent` declarative types** — deferred in Task 2. Trigger: third consumer that needs branching or conditional step skips, OR explicit pain debugging the current list-of-callables shape. Neither exists after this task.
- **`chain_call` / `chain_signal` tables + Alembic migration** — deferred. Trigger: real cost-tracking or debugging need with a user complaining about spend visibility. No such signal today.
- **`server/modules/chain/providers/replicate.py`** — deferred. Trigger: a second Replicate consumer. Photoshoot is the only one; moving Replicate into the chain module now would shape `chain.adapter` around one caller and force a re-shape when a second caller with different needs appears.
- **SSE event streaming from `run_chain`** — deferred. Trigger: a feature whose UX needs progressive disclosure. Photoshoot's current UX is synchronous-response — no SSE demand. The `adapter.stream` helper already exists for the Claude-streaming case if photoshoot ever needs it; no runner-level event unions yet.
- **Retry / backoff machinery inside the chain runner** — deferred. Trigger: a real failure mode that the Anthropic SDK's built-in `max_retries=2` doesn't absorb. Discover the failure first, then add the mechanism calibrated to it.
- **Per-feature cost tracking dashboards** — deferred with the `chain_call` table it requires.
- **Photoshoot UI changes** — zero. The route contract is unchanged; the client sees identical JSON.
- **OpenAPI regeneration (`npm run gen:all`)** — not needed. No schema field changed.
- **Moving photoshoot tests into `server/modules/photoshoot/tests/`** — tempting because Task 2 used that layout. Photoshoot's tests live at `server/tests/` per codebase.md; moving them is a separate refactor unrelated to this task's primitive-consumption goal.

**Rule for the executor**: if any of the above starts to look necessary mid-refactor, STOP. Flag it as a deviation in the commit body and proceed with the minimum list-of-callables retrofit. The whole point of this task is to prove the primitive's shipped shape holds for a second consumer. Growing the primitive to meet the second consumer defeats the calibration.

---

## Related Documents

- [Solution Architecture](./architecture.md) — full design rationale for the primitive + feature split
- [Epic](./epic.md) — task scope and success criteria ("zero user-facing change verified by existing end-to-end photoshoot test")
- [Timeline](./timeline.md) — update to `done` after Verification passes