# Task 1.2 — Concrete Step Kinds: AICall + Compute

---

## 1. Context

Task 1.2 delivers two concrete `AbstractStep` subclasses (`AICall`, `Compute`) and the `CallableRegistry` they share. `AICall` replaces the chain-primitive epic's planned `ChainStep`; it wraps a single `chain_adapter.generate()` call with prompt-template interpolation. `Compute` dispatches to a named, pre-registered Python callable — the escape hatch for non-AI steps without permitting `eval` or anonymous callables at dispatch time.

**Dependency**: Task 1.1 must supply `AbstractStep` (frozen Pydantic v2 `BaseModel` + ABC with sealed `execute(self, context: StepContext)` generator Template Method), `StepContext`, and `StepStarted` / `StepCompleted` / `StepFailed` Pydantic frozen domain events, all rooted at `modules/workflows/steps/base.py` and `modules/workflows/steps/events.py`. The exact expected contract is enumerated in §2 Pre-flight.

**Scope for this task only**:
- `modules/workflows/steps/registry.py` — `CallableRegistry` (register / get / clear / register_compute decorator)
- `modules/workflows/steps/ai_call.py` — `AICall` frozen value object + `_invoke`
- `modules/workflows/steps/compute.py` — `Compute` frozen value object + `_invoke`
- `modules/workflows/tests/conftest.py`, `test_registry.py`, `test_ai_call.py`, `test_compute.py` — 28 unit tests

**Explicitly excluded from this task**: `RetryStep`, `LoggedStep`, `CostTrackedStep`, `RateLimitedStep`, `WorkflowRuntime`, `WorkflowRepository`, any adapter widening (`invoke()`), and the `Workflow` aggregate (Task 2). Tasks 3, 4, 5 cover runtime, repository, and migration respectively.

---

## 2. Pre-flight

### 2a. Task 1.1 contract check

Run each assertion manually before writing any code:

```bash
cd {WORKSPACE}/spec-doc/api
python - <<'EOF'
from modules.workflows.steps.base import AbstractStep, StepContext
from modules.workflows.steps.events import StepStarted, StepCompleted, StepFailed
import inspect

# AbstractStep must be abstract (cannot be instantiated directly).
assert inspect.isabstract(AbstractStep), "AbstractStep must have @abstractmethod _invoke"
assert '_invoke' in AbstractStep.__abstractmethods__, "_invoke must be abstract"

# execute() must be present and concrete (the Template Method).
assert hasattr(AbstractStep, 'execute'), "execute() missing"
assert 'execute' not in AbstractStep.__abstractmethods__, "execute() must be concrete (Template Method)"

# Frozen Pydantic — concrete subclass instances are immutable, name passed as kwarg.
class DummyStep(AbstractStep):
    def _invoke(self, context): return "ok"

s = DummyStep(name="probe")
try:
    s.name = "x"
    raise AssertionError("AbstractStep subclass should be immutable (frozen Pydantic model)")
except Exception as e:
    assert "frozen" in str(e).lower() or type(e).__name__ in ("ValidationError", "TypeError"), \
        f"Expected immutability error, got: {e}"

# execute() is a generator yielding events; output is written to context.outputs[name].
ctx = StepContext(run_id="r", inputs={})
events = list(s.execute(ctx))
assert len(events) == 2, f"execute() must yield exactly StepStarted + StepCompleted: {events}"
assert isinstance(events[0], StepStarted), f"first event should be StepStarted, got {type(events[0])}"
assert isinstance(events[1], StepCompleted), f"second event should be StepCompleted, got {type(events[1])}"
assert ctx.outputs.get("probe") == "ok", f"context.outputs['probe'] should be 'ok', got {ctx.outputs}"

print("Task 1.1 contract: OK")
EOF
```

If this script exits non-zero, **stop**. Resolve Task 1.1 first.

### 2b. Existing test suite green

```bash
cd {WORKSPACE}/spec-doc/api
make test
```

All 192 tests must pass before adding new code.

### 2c. `modules/workflows/` package exists

```bash
python -c "import modules.workflows; print('package present')"
```

If this fails with `ModuleNotFoundError`, Task 1.1 has not created the package. Verify Task 1.1 created `modules/workflows/__init__.py`.

### 2d. Mock provider works

```bash
CHAIN_PROVIDER=mock python -c "
from modules.chain.adapter import generate
r = generate('sys', 'hello')
assert r.text.startswith('MOCK['), f'unexpected: {r.text}'
print('mock provider: OK')
"
```

---

## 3. Files

All paths are relative to `{WORKSPACE}/spec-doc/api`.

| File | Status |
|------|--------|
| `modules/workflows/steps/base.py` | **EXISTS** — Task 1.1 output. Do not edit. |
| `modules/workflows/steps/events.py` | **EXISTS** — Task 1.1 output. Do not edit. |
| `modules/workflows/steps/__init__.py` | **EXISTS** — Task 1.1 output. Append two exports in Step 5. |
| `modules/workflows/tests/__init__.py` | **EXISTS** — Task 1.1 output. Do not re-create. |
| `modules/workflows/steps/registry.py` | **(new)** |
| `modules/workflows/steps/ai_call.py` | **(new)** |
| `modules/workflows/steps/compute.py` | **(new)** |
| `modules/workflows/tests/conftest.py` | **(new)** |
| `modules/workflows/tests/test_registry.py` | **(new)** |
| `modules/workflows/tests/test_ai_call.py` | **(new)** |
| `modules/workflows/tests/test_compute.py` | **(new)** |

---

## 4. Implementation Steps

### Step 1 — Create `modules/workflows/steps/registry.py`

```python
"""Callable registry for Compute steps — ELA Pattern #27 (Registry).

Only named, pre-registered callables are legal. No eval, no anonymous dispatch.
Registered callables must have the signature: fn(context: StepContext) -> Any.
The callable reads ``context.inputs`` and ``context.outputs`` and returns any
JSON-serialisable value.

This module exposes both standalone functions and a ``CallableRegistry`` namespace
class (useful for dependency-injection in tests without re-importing each function).
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_registry: dict[str, Callable[..., Any]] = {}


# ---------------------------------------------------------------------------
# Module-level API
# ---------------------------------------------------------------------------


def register(name: str, fn: Callable[..., Any]) -> None:
    """Register *fn* under *name*.

    Raises
    ------
    TypeError   if *fn* is not callable.
    ValueError  if *name* is already registered (prevents silent overwrites).
    """
    if not callable(fn):
        raise TypeError(
            f"Expected a callable for {name!r}, got {type(fn).__name__}"
        )
    if name in _registry:
        raise ValueError(
            f"Callable {name!r} is already registered. "
            "Choose a unique name or call clear() between registrations (tests only)."
        )
    _registry[name] = fn
    logger.debug("registered compute callable %r", name)


def get(name: str) -> Callable[..., Any]:
    """Return the callable registered under *name*.

    Raises
    ------
    KeyError  if *name* has no registration.
    """
    if name not in _registry:
        raise KeyError(
            f"No callable registered under {name!r}. "
            f"Registered names: {sorted(_registry)}"
        )
    return _registry[name]


def registered_names() -> list[str]:
    """Return a sorted list of all registered callable names."""
    return sorted(_registry.keys())


def clear() -> None:
    """Remove all registrations.

    Call only from test teardown (autouse fixture in conftest.py).
    Never call in production code — there is no undo.
    """
    _registry.clear()


def register_compute(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: register a function as a named Compute step callable.

    Usage::

        @register_compute("format-output")
        def format_output(context: StepContext) -> str:
            return context.inputs["text"].strip()

    The decorated function is returned unchanged so it remains importable and
    directly callable in Python workflows.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        register(name, fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Namespace class — thin wrapper for dependency-injection scenarios
# ---------------------------------------------------------------------------


class CallableRegistry:
    """Class-level namespace mirroring the module-level functions.

    Prefer the module-level functions in production code.  This class exists
    so tests can inject the registry as a single object without importing each
    function separately.
    """

    register = staticmethod(register)
    get = staticmethod(get)
    registered_names = staticmethod(registered_names)
    clear = staticmethod(clear)
    register_compute = staticmethod(register_compute)
```

---

### Step 2 — Create `modules/workflows/steps/ai_call.py`

```python
"""AICall — concrete Step that wraps a single chain_adapter.generate() call.

AICall absorbs the chain-primitive epic: ChainStep becomes AICall here.
``ChainStep`` must not be introduced as a separate artefact.

Prompt construction
-------------------
``prompt_template`` is a str.format_map template.  At _invoke time the merged
dict ``{**context.outputs, **context.inputs}`` is substituted — inputs win on
key collision so workflow callers can override prior step outputs explicitly
when needed. Only ``context.inputs`` and ``context.outputs`` keys are in
scope; no arithmetic, no eval.

Value-object semantics
----------------------
AICall is a frozen Pydantic model.  Two AICall instances with the same field
values compare equal and hash equal (suitable for use as dict keys / set members).
"""
from __future__ import annotations

from typing import Any

from modules.chain import adapter as chain_adapter
from modules.chain.types import ChainResult

from .base import AbstractStep, StepContext


class AICall(AbstractStep):
    """Frozen value object: one ``chain_adapter.generate()`` invocation.

    Fields
    ------
    name              Step identity string; must be unique within a Workflow.
                      Inherited from AbstractStep (Pydantic field, kwarg-only).
    system            Static system prompt — no template substitution applied.
    prompt_template   User prompt template; ``{key}`` placeholders are resolved
                      from the merged inputs+outputs dict at execution time.
    input_keys        Keys that must exist in ``context.inputs`` before the
                      step runs. Backs ``required_inputs`` for validation.
                      Defaults to empty (no validation).
    model             Provider model identifier.  Defaults to the adapter's
                      ``DEFAULT_MODEL`` constant so callers need not hard-code it.
    max_tokens        Provider token ceiling.
    """

    system: str
    prompt_template: str
    input_keys: tuple[str, ...] = ()
    model: str = chain_adapter.DEFAULT_MODEL
    max_tokens: int = 4096

    @property
    def required_inputs(self) -> frozenset[str]:
        return frozenset(self.input_keys)

    def _invoke(self, context: StepContext) -> ChainResult:
        merged = {**context.outputs, **context.inputs}  # inputs win on collision
        prompt = self.prompt_template.format_map(merged)
        return chain_adapter.generate(
            self.system,
            prompt,
            model=self.model,
            max_tokens=self.max_tokens,
        )
```

**Implementation notes**:
- `format_map` (not `format(**merged)`) is used so subclasses can supply a custom mapping without changing this method.
- The `system` field is passed verbatim to `chain_adapter.generate()`. `with_context()` inside the adapter handles any `builder`/`principles` injection — `AICall` does not duplicate that concern. `builder` and `principles` are intentionally NOT fields on `AICall`; they are ambient context injected at the adapter boundary per its existing design.
- `DEFAULT_MODEL` is read from the adapter at class-definition time. If the adapter constant changes, existing `AICall` instances constructed with the default automatically reflect it on next construction.
- Step output is the returned `ChainResult` value; `AbstractStep.execute()` writes it to `context.outputs[self.name]` after `_invoke` returns.

---

### Step 3 — Create `modules/workflows/steps/compute.py`

```python
"""Compute — concrete Step that dispatches to a registered pure-Python callable.

Design constraints (hard lines from architecture)
-------------------------------------------------
- No eval.  No exec.  No anonymous functions at dispatch time.
- ``fn_name`` is resolved from the CallableRegistry at _invoke time, not at
  Compute construction time.  This allows Workflows to be defined before their
  callables are registered (e.g. at module import vs. app startup order).
- The callable's return value is returned directly from _invoke; no wrapping.

Callable contract
-----------------
    fn(context: StepContext) -> Any

The same StepContext that AbstractStep.execute() received is forwarded
unchanged. Callables read ``context.inputs`` and ``context.outputs`` and
return any JSON-serialisable value.
"""
from __future__ import annotations

from typing import Any

from .base import AbstractStep, StepContext
from .registry import get as _registry_get


class Compute(AbstractStep):
    """Frozen value object: one registered callable invocation.

    Fields
    ------
    name      Step identity string; must be unique within a Workflow.
              Inherited from AbstractStep.
    fn_name   Name the callable was registered under in the CallableRegistry.
              Resolved at _invoke time — not validated at construction time.
    """

    fn_name: str

    def _invoke(self, context: StepContext) -> Any:
        fn = _registry_get(self.fn_name)  # raises KeyError if not registered
        return fn(context)
```

---

### Step 4 — Create `modules/workflows/tests/__init__.py`

Empty file — required for pytest collection and `python -m pytest modules/workflows/tests/` invocation.

```python
```

---

### Step 5 — Create `modules/workflows/tests/conftest.py`

```python
"""Test fixtures scoped to modules/workflows/tests/.

autouse clear_callable_registry ensures every test starts with an empty
registry and leaves none of its registrations behind, regardless of whether
the test passes or raises.  This is the correct isolation mechanism for
module-level global state.
"""
from __future__ import annotations

import pytest

from modules.workflows.steps import registry


@pytest.fixture(autouse=True)
def clear_callable_registry():
    """Reset the CallableRegistry before and after every test in this directory."""
    registry.clear()
    yield
    registry.clear()
```

---

### Step 6 — Create `modules/workflows/tests/test_registry.py`

```python
"""Unit tests for the CallableRegistry."""
from __future__ import annotations

import pytest

from modules.workflows.steps.registry import (
    CallableRegistry,
    clear,
    get,
    register,
    register_compute,
    registered_names,
)

# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


def register_addsCallableByName():
    def fn(context):
        return "result"

    register("my-fn", fn)
    assert get("my-fn") is fn, "get() must return the exact object that was registered"


def register_duplicateName_raisesValueError():
    def fn(context):
        return "a"

    register("dup", fn)
    with pytest.raises(ValueError, match="dup"):
        register("dup", fn)


def register_nonCallable_raisesTypeError():
    with pytest.raises(TypeError, match="callable"):
        register("bad", "not-a-function")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


def get_unknownName_raisesKeyError():
    with pytest.raises(KeyError, match="unknown-fn"):
        get("unknown-fn")


def get_afterClear_raisesKeyError():
    register("temp", lambda c: None)
    clear()
    with pytest.raises(KeyError):
        get("temp")


# ---------------------------------------------------------------------------
# registered_names()
# ---------------------------------------------------------------------------


def registeredNames_returnsAlphabeticallySortedNames():
    register("zebra", lambda c: None)
    register("alpha", lambda c: None)
    names = registered_names()
    assert names == ["alpha", "zebra"], f"expected alphabetical order, got {names}"


def registeredNames_emptyRegistry_returnsEmptyList():
    assert registered_names() == [], "fresh registry must be empty"


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def clear_removesAllEntries():
    register("temp", lambda c: None)
    clear()
    assert registered_names() == [], "clear() must empty the registry"


# ---------------------------------------------------------------------------
# register_compute() decorator
# ---------------------------------------------------------------------------


def registerCompute_decoratorRegistersFunction():
    @register_compute("decorated-fn")
    def my_fn(context):
        return context.inputs.get("x", 0) * 2

    assert get("decorated-fn") is my_fn, "decorator must register the function by name"


def registerCompute_decoratorPreservesCallableIdentity():
    from modules.workflows.steps.base import StepContext

    @register_compute("passthrough")
    def passthrough(context):
        return context.inputs

    # The decorated function must still be directly callable
    result = passthrough(StepContext(run_id="r", inputs={"k": "v"}))
    assert result == {"k": "v"}, "decorator must return the original function unchanged"


# ---------------------------------------------------------------------------
# CallableRegistry class namespace
# ---------------------------------------------------------------------------


def callableRegistry_classMethods_delegateToModuleFunctions():
    """CallableRegistry class-level API must be a transparent wrapper."""

    def fn(c):
        return "ok"

    CallableRegistry.register("cls-test", fn)
    assert CallableRegistry.get("cls-test") is fn, "CallableRegistry.get() must find what CallableRegistry.register() stored"
    assert "cls-test" in CallableRegistry.registered_names(), "cls-test must appear in registered_names()"
```

---

### Step 7 — Create `modules/workflows/tests/test_ai_call.py`

```python
"""Unit tests for AICall — value-object semantics and _invoke behaviour.

Tests prefixed '# Requires Task 1.1' call execute() and depend on
AbstractStep.execute() being complete.  They are skipped automatically
when the integration contract is not yet satisfied.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.chain import adapter as chainAdapter
from modules.chain.types import ChainResult
from modules.workflows.steps.ai_call import AICall
from modules.workflows.steps.base import StepContext

# ---------------------------------------------------------------------------
# Helpers — camelCase names to avoid *_* pytest collection
# ---------------------------------------------------------------------------

# fakeGenerate captures the arguments forwarded to chain_adapter.generate()
# and returns a minimal ChainResult so tests stay offline.
def fakeGenerate(captured: list):
    def inner(system, prompt, *, model, max_tokens, **_):
        captured.append(
            {"system": system, "prompt": prompt, "model": model, "max_tokens": max_tokens}
        )
        return ChainResult(text=f"FAKE[{prompt[:30]}]", latency_ms=1)

    return inner


def stepCtx(inputs=None, outputs=None) -> StepContext:
    """Build a minimal StepContext for _invoke() and execute() tests."""
    return StepContext(run_id="run-001", inputs=inputs or {}, outputs=outputs or {})


# ---------------------------------------------------------------------------
# Value-object immutability
# ---------------------------------------------------------------------------


def aiCall_isImmutable():
    step = AICall(name="s", system="sys", prompt_template="hello")
    with pytest.raises((ValidationError, TypeError)):
        step.name = "mutated"  # type: ignore[misc]


def aiCall_equalByValue():
    a = AICall(name="s", system="sys", prompt_template="hello")
    b = AICall(name="s", system="sys", prompt_template="hello")
    assert a == b, "Two AICall instances with identical fields must compare equal"


def aiCall_differentName_notEqual():
    a = AICall(name="step-a", system="sys", prompt_template="hello")
    b = AICall(name="step-b", system="sys", prompt_template="hello")
    assert a != b


# ---------------------------------------------------------------------------
# Prompt template interpolation
# ---------------------------------------------------------------------------


def aiCall_invoke_interpolatesInputsIntoPrompt(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="hello {name}")
    step._invoke(stepCtx(inputs={"name": "Alice"}))

    assert len(captured) == 1, "generate() must be called exactly once"
    assert captured[0]["prompt"] == "hello Alice", (
        f"prompt interpolation failed; got: {captured[0]['prompt']!r}"
    )


def aiCall_invoke_interpolatesPriorOutputsIntoPrompt(monkeypatch):
    """Prior step outputs (context.outputs) are usable as template variables."""
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="exec={execution_id}")
    step._invoke(stepCtx(outputs={"execution_id": "abc-123"}))

    assert captured[0]["prompt"] == "exec=abc-123", (
        f"prior-output interpolation failed; got: {captured[0]['prompt']!r}"
    )


def aiCall_invoke_inputsTakePriorityOverPriorOutputsOnKeyCollision(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="val={x}")
    step._invoke(stepCtx(inputs={"x": "input-wins"}, outputs={"x": "output-loses"}))

    assert captured[0]["prompt"] == "val=input-wins", (
        "inputs must override prior outputs when the same key appears in both"
    )


def aiCall_invoke_missingTemplateKey_raisesKeyError(monkeypatch):
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate([]))

    step = AICall(name="s", system="sys", prompt_template="hello {missing_key}")
    with pytest.raises(KeyError):
        step._invoke(stepCtx())


# ---------------------------------------------------------------------------
# Model and max_tokens forwarding
# ---------------------------------------------------------------------------


def aiCall_invoke_forwardsModelToGenerate(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="p", model="claude-opus-42")
    step._invoke(stepCtx())

    assert captured[0]["model"] == "claude-opus-42", (
        f"model not forwarded correctly; got: {captured[0]['model']!r}"
    )


def aiCall_invoke_forwardsMaxTokensToGenerate(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="p", max_tokens=512)
    step._invoke(stepCtx())

    assert captured[0]["max_tokens"] == 512, (
        f"max_tokens not forwarded; got: {captured[0]['max_tokens']}"
    )


def aiCall_invoke_defaultModelMatchesAdapterConstant(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="sys", prompt_template="p")  # no explicit model
    step._invoke(stepCtx())

    assert captured[0]["model"] == chainAdapter.DEFAULT_MODEL, (
        f"default model mismatch; adapter has {chainAdapter.DEFAULT_MODEL!r}, "
        f"AICall forwarded {captured[0]['model']!r}"
    )


def aiCall_invoke_passesSystemUnmodifiedToGenerate(monkeypatch):
    captured: list = []
    monkeypatch.setattr(chainAdapter, "generate", fakeGenerate(captured))

    step = AICall(name="s", system="EXACT_SYSTEM_PROMPT", prompt_template="p")
    step._invoke(stepCtx())

    assert captured[0]["system"] == "EXACT_SYSTEM_PROMPT", (
        "system prompt must be forwarded verbatim; with_context injection is the adapter's responsibility"
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def aiCall_invoke_returnsChainResult(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    step = AICall(name="s", system="sys", prompt_template="hello")
    result = step._invoke(stepCtx())
    assert isinstance(result, ChainResult), f"_invoke must return ChainResult, got {type(result)}"
    assert isinstance(result.text, str), "ChainResult.text must be str"
    assert result.latency_ms >= 0, "ChainResult.latency_ms must be non-negative"


# ---------------------------------------------------------------------------
# Integration through execute() — Requires Task 1.1
# ---------------------------------------------------------------------------


def aiCall_execute_emitsStepStartedAndStepCompleted(monkeypatch):  # Requires Task 1.1
    from modules.workflows.steps.events import StepCompleted, StepStarted

    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    step = AICall(name="my-step", system="sys", prompt_template="hello")
    ctx = stepCtx()
    events = list(step.execute(ctx))

    kinds = [type(e).__name__ for e in events]
    assert "StepStarted" in kinds, f"StepStarted missing from events: {kinds}"
    assert "StepCompleted" in kinds, f"StepCompleted missing from events: {kinds}"
    assert isinstance(ctx.outputs["my-step"], ChainResult), (
        f"execute() must store ChainResult in context.outputs[name], got {type(ctx.outputs.get('my-step'))}"
    )


def aiCall_execute_emitsStepFailed_whenGenerateRaises(monkeypatch):  # Requires Task 1.1
    from modules.chain.errors import ProviderError
    from modules.workflows.steps.events import StepFailed

    def explode(system, prompt, **kwargs):
        raise ProviderError("provider down", status_code=502)

    monkeypatch.setattr(chainAdapter, "generate", explode)
    step = AICall(name="my-step", system="sys", prompt_template="p")

    with pytest.raises(ProviderError):
        list(step.execute(stepCtx()))
    # AbstractStep.execute() emits StepFailed then re-raises ProviderError.
    # The StepFailed type assertion lives in Task 1.1's AbstractStep tests;
    # this test confirms ProviderError propagates through the Template Method.
```

---

### Step 8 — Create `modules/workflows/tests/test_compute.py`

```python
"""Unit tests for Compute step — value-object semantics and _invoke behaviour."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.workflows.steps.compute import Compute
from modules.workflows.steps.registry import register

# ---------------------------------------------------------------------------
# Value-object immutability
# ---------------------------------------------------------------------------


def compute_isImmutable():
    step = Compute(name="s", fn_name="my-fn")
    with pytest.raises((ValidationError, TypeError)):
        step.fn_name = "mutated"  # type: ignore[misc]


def compute_equalByValue():
    a = Compute(name="s", fn_name="my-fn")
    b = Compute(name="s", fn_name="my-fn")
    assert a == b, "Two Compute instances with identical fields must compare equal"


def compute_differentFnName_notEqual():
    a = Compute(name="s", fn_name="fn-a")
    b = Compute(name="s", fn_name="fn-b")
    assert a != b


# ---------------------------------------------------------------------------
# Registry dispatch
# ---------------------------------------------------------------------------


def compute_invoke_dispatchesToRegisteredCallable():
    def double(context):
        return context.inputs["x"] * 2

    register("double", double)
    step = Compute(name="s", fn_name="double")
    result = step._invoke(stepCtx(inputs={"x": 5}))
    assert result == 10, f"expected 10 from double(5), got {result}"


def compute_invoke_passesContextToCallable():
    received: dict = {}

    def capture(context):
        received["inputs"] = context.inputs
        received["outputs"] = context.outputs
        received["run_id"] = context.run_id
        return "done"

    register("capture", capture)
    step = Compute(name="s", fn_name="capture")
    step._invoke(stepCtx(inputs={"key": "val"}, outputs={"prior": "x"}))

    assert received["inputs"] == {"key": "val"}, (
        f"context.inputs not passed correctly; got: {received.get('inputs')}"
    )
    assert received["outputs"] == {"prior": "x"}, (
        f"context.outputs not passed correctly; got: {received.get('outputs')}"
    )
    assert received["run_id"] == "run-001"


def compute_invoke_returnsCallableReturnValue():
    register("identity", lambda c: c.inputs)
    step = Compute(name="s", fn_name="identity")
    result = step._invoke(stepCtx(inputs={"a": 1}))
    assert result == {"a": 1}, f"_invoke must return the callable's return value; got {result}"


def compute_invoke_unregisteredFnName_raisesKeyError():
    step = Compute(name="s", fn_name="not-registered")
    with pytest.raises(KeyError, match="not-registered"):
        step._invoke(stepCtx())


def compute_invoke_callableException_propagatesUnwrapped():
    def explode(context):
        raise RuntimeError("boom")

    register("exploder", explode)
    step = Compute(name="s", fn_name="exploder")
    with pytest.raises(RuntimeError, match="boom"):
        step._invoke(stepCtx())


def compute_construction_doesNotValidateFnName():
    """Compute must NOT validate fn_name against the registry at construction time.

    Reason: workflows may be defined before their callables are registered
    (e.g. workflow Python file imported before the feature module's startup
    registers its callables).  Resolution is deferred to _invoke time.
    """
    # Should not raise even though "deferred-fn" is not registered yet
    step = Compute(name="s", fn_name="deferred-fn")
    assert step.fn_name == "deferred-fn"

    # Registering after construction must make _invoke succeed
    register("deferred-fn", lambda c: "ok")
    result = step._invoke(stepCtx())
    assert result == "ok"


# ---------------------------------------------------------------------------
# Integration through execute() — Requires Task 1.1
# ---------------------------------------------------------------------------


def compute_execute_emitsStepStartedAndStepCompleted():  # Requires Task 1.1
    from modules.workflows.steps.base import StepContext
    from modules.workflows.steps.events import StepCompleted, StepStarted

    register("noop", lambda c: {"processed": True})
    step = Compute(name="my-compute", fn_name="noop")
    ctx = StepContext(run_id="r", inputs={})
    events = list(step.execute(ctx))

    kinds = [type(e).__name__ for e in events]
    assert "StepStarted" in kinds, f"StepStarted missing from events: {kinds}"
    assert "StepCompleted" in kinds, f"StepCompleted missing from events: {kinds}"
    assert ctx.outputs["my-compute"] == {"processed": True}, (
        f"execute() must store callable result in context.outputs[name]; got {ctx.outputs}"
    )
```

---

### Step 9 — Append to `modules/workflows/steps/__init__.py`

Read the existing file first, then add the two new exports. The existing file will have whatever Task 1.1 exported. Add these lines:

```python
from .ai_call import AICall
from .compute import Compute
from .registry import CallableRegistry, register_compute
```

Ensure `__all__` (if present) includes `"AICall"`, `"Compute"`, `"CallableRegistry"`, `"register_compute"`.

---

### Step 10 — Verify structural test still passes

`modules/chain/tests/test_structural.py` enforces `featureModules_mustNotImportProvidersDirectly`. `AICall` imports `modules.chain.adapter` (the only legal path) — this must not trigger the structural guard.

```bash
cd {WORKSPACE}/spec-doc/api
python -m pytest modules/chain/tests/test_structural.py -v
```

Expected: all structural tests green.

---

## 5. Tests

**Framework**: pytest with `python_functions = ["test_*", "*_*"]`. No `test_` prefix needed on functions — any name matching `*_*` is collected. Module-level non-test names must NOT contain underscores (use camelCase for helpers: `fakeGenerate`, not `fake_generate`).

**Run new tests only**:
```bash
cd {WORKSPACE}/spec-doc/api
CHAIN_PROVIDER=mock python -m pytest modules/workflows/tests/ -v
```

**Expected output** (28 tests):

```
modules/workflows/tests/test_registry.py::register_addsCallableByName PASSED
modules/workflows/tests/test_registry.py::register_duplicateName_raisesValueError PASSED
modules/workflows/tests/test_registry.py::register_nonCallable_raisesTypeError PASSED
modules/workflows/tests/test_registry.py::get_unknownName_raisesKeyError PASSED
modules/workflows/tests/test_registry.py::get_afterClear_raisesKeyError PASSED
modules/workflows/tests/test_registry.py::registeredNames_returnsAlphabeticallySortedNames PASSED
modules/workflows/tests/test_registry.py::registeredNames_emptyRegistry_returnsEmptyList PASSED
modules/workflows/tests/test_registry.py::clear_removesAllEntries PASSED
modules/workflows/tests/test_registry.py::registerCompute_decoratorRegistersFunction PASSED
modules/workflows/tests/test_registry.py::registerCompute_decoratorPreservesCallableIdentity PASSED
modules/workflows/tests/test_registry.py::callableRegistry_classMethods_delegateToModuleFunctions PASSED

modules/workflows/tests/test_ai_call.py::aiCall_isImmutable PASSED
modules/workflows/tests/test_ai_call.py::aiCall_equalByValue PASSED
modules/workflows/tests/test_ai_call.py::aiCall_differentName_notEqual PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_interpolatesInputsIntoPrompt PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_interpolatesContextIntoPrompt PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_inputsTakePriorityOverContextOnKeyCollision PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_missingTemplateKey_raisesKeyError PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_forwardsModelToGenerate PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_forwardsMaxTokensToGenerate PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_defaultModelMatchesAdapterConstant PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_passesSystemUnmodifiedToGenerate PASSED
modules/workflows/tests/test_ai_call.py::aiCall_invoke_returnsChainResult PASSED
modules/workflows/tests/test_ai_call.py::aiCall_execute_emitsStepStartedAndStepCompleted PASSED
modules/workflows/tests/test_ai_call.py::aiCall_execute_emitsStepFailed_whenGenerateRaises PASSED

modules/workflows/tests/test_compute.py::compute_isImmutable PASSED
modules/workflows/tests/test_compute.py::compute_equalByValue PASSED
modules/workflows/tests/test_compute.py::compute_differentFnName_notEqual PASSED
modules/workflows/tests/test_compute.py::compute_invoke_dispatchesToRegisteredCallable PASSED
modules/workflows/tests/test_compute.py::compute_invoke_passesInputsAndContextToCallable PASSED
modules/workflows/tests/test_compute.py::compute_invoke_returnsCallableReturnValue PASSED
modules/workflows/tests/test_compute.py::compute_invoke_unregisteredFnName_raisesKeyError PASSED
modules/workflows/tests/test_compute.py::compute_invoke_callableException_propagatesUnwrapped PASSED
modules/workflows/tests/test_compute.py::compute_construction_doesNotValidateFnName PASSED
modules/workflows/tests/test_compute.py::compute_execute_emitsStepStartedAndStepCompleted PASSED

================================ 35 passed in X.XXs ================================
```

*(Count is 35 — 11 registry + 14 ai_call + 10 compute. If Task 1.1's `execute()` is not yet merged, the two `execute`-suffixed integration tests will fail with `AttributeError`. All other 33 tests must pass regardless.)*

---

## 6. Commit Plan

Single commit on a feature branch; no direct push to `master` (see repo rules).

```bash
cd {WORKSPACE}/spec-doc/api
git checkout -b task-1.2-concrete-steps

git add \
  modules/workflows/steps/registry.py \
  modules/workflows/steps/ai_call.py \
  modules/workflows/steps/compute.py \
  modules/workflows/steps/__init__.py \
  modules/workflows/tests/__init__.py \
  modules/workflows/tests/conftest.py \
  modules/workflows/tests/test_registry.py \
  modules/workflows/tests/test_ai_call.py \
  modules/workflows/tests/test_compute.py

git commit -m "$(cat <<'EOF'
feat(workflows): Task 1.2 — AICall, Compute step kinds, CallableRegistry

- steps/ai_call.py: AICall frozen Pydantic value object wrapping
  chain_adapter.generate(); absorbs chain-primitive epic (ChainStep → AICall)
- steps/compute.py: Compute frozen Pydantic value object; dispatches to
  named callable registered in CallableRegistry; fn_name resolved at
  _invoke time (not construction time) to decouple definition from startup order
- steps/registry.py: module-level CallableRegistry with register/get/clear/
  register_compute decorator + CallableRegistry namespace class for DI
- tests/: 35 unit tests (11 registry, 14 AICall, 10 Compute); autouse
  clear_callable_registry fixture in local conftest.py ensures registry isolation

Decorator suite (Retry, Log, Cost) is Phase 2 and not included here.
EOF
)"
```

Open a PR targeting `master`:
```bash
gh pr create --title "Task 1.2: AICall + Compute step kinds + CallableRegistry" \
  --body "Implements concrete step kinds on top of AbstractStep (Task 1.1). See task guide for full test plan."
```

---

## 7. Verification

### Full suite — must stay at 192 + 35 = 227 (or existing count + 35):
```bash
cd {WORKSPACE}/spec-doc/api
make test
```

### Registry isolation — confirm no cross-test bleed:
```bash
CHAIN_PROVIDER=mock python -m pytest modules/workflows/tests/test_registry.py \
  -v --tb=short -p no:randomly
```
Run twice (first normal order, second with `--randomly-seed=12345` if pytest-randomly is installed). Both runs must produce identical pass counts.

### Structural invariant — AICall must not violate the provider boundary:
```bash
python -m pytest modules/chain/tests/test_structural.py -v
```

### Import smoke test:
```bash
python - <<'EOF'
from modules.workflows.steps import AICall, Compute, CallableRegistry, register_compute
from modules.workflows.steps.registry import register, get, clear

# Registry round-trip
register("smoke-fn", lambda i, c: "ok")
assert get("smoke-fn")({"a": 1}, {}) == "ok"
clear()

# AICall construction
step = AICall(name="s", system="You are helpful.", prompt_template="Hello {name}")
assert step.model == "claude-sonnet-4-5"
assert step.max_tokens == 4096

# Compute construction (fn_name not yet registered — must not raise)
cstep = Compute(name="c", fn_name="not-yet-registered")
assert cstep.fn_name == "not-yet-registered"

# Compute deferred resolution
from modules.workflows.steps.base import StepContext
register("not-yet-registered", lambda c: 42)
assert cstep._invoke(StepContext(run_id="r", inputs={})) == 42
clear()

print("Import smoke: OK")
EOF
```

---

## 8. Rollback

If any verification step fails after merge:

```bash
# On the feature branch — revert and force PR update
git revert HEAD --no-edit
git push

# If merged to master and cannot wait for PR:
# Delete the three new source files and the tests directory,
# then revert the __init__.py edit.
git rm modules/workflows/steps/registry.py \
       modules/workflows/steps/ai_call.py \
       modules/workflows/steps/compute.py
git rm -r modules/workflows/tests/
# Revert __init__.py to Task 1.1 state
git checkout HEAD~1 -- modules/workflows/steps/__init__.py
git commit -m "revert: remove Task 1.2 artefacts pending fix"
```

The `clear()` function in `registry.py` ensures no production state is left behind — the registry is only populated at startup by feature-module registration calls, none of which exist yet.

---

## 9. Deviations Allowed

| Deviation | Condition |
|-----------|-----------|
| Use frozen `@dataclass` instead of Pydantic `BaseModel` for `AICall`/`Compute` | Permitted only if Task 1.1's `AbstractStep` also uses a frozen dataclass. The two must be consistent. If switching, update the `isImmutable` tests to expect `FrozenInstanceError` (from `dataclasses`) rather than `ValidationError`. |
| Rename `prompt_template` → `user_prompt` on `AICall` | Permitted if the workflow builder (Task 2) adopts a different field name convention, but requires updating all tests in §5 that reference `prompt_template`. |
| `_registry` keyed on `(module, name)` tuples instead of bare strings | Permitted if a naming collision across feature modules materialises in Phase 1. Update `register_compute` signature and all registry tests. |

---

## 10. Out of Scope

The following must not appear in this task's diff, even as stubs:

- `RetryStep`, `LoggedStep`, `CostTrackedStep`, `RateLimitedStep` — Phase 2 Decorator wrappers
- `Composite` step kind (Workflow as a Step) — Phase 2
- `Parallel` step kind — Phase 2 alongside async execution
- `invoke(invocation)` signature on `chain_adapter` — separate adapter-widening epic
- `WorkflowRuntime`, `WorkflowExecution` — Task 3
- `WorkflowRepository`, `WorkflowRepositoryFs` — Task 4
- `Workflow` aggregate and `WorkflowBuilder` — Task 2
- Any JSON schema or JSON workflow loader — Phase 3
- Any route handler changes or blueprint registrations in `create_app.py`
- `@validate_inputs` or input-schema declarations on `AbstractStep` — not specified for Phase 1 steps
- `CHAIN_PROVIDER` environment variable changes or new provider implementations