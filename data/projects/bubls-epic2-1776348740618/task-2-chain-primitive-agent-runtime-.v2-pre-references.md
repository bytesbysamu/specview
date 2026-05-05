# 🛠️ Task 2: Chain primitive (`agent_runtime`)

**Purpose**: Build the shared orchestrator that takes a declarative `ChainDefinition`, injects builder + principles, runs steps sequentially with retry, logs every provider call, streams SSE-compatible events, and exposes `capture_signal`. Every feature chain (spec, photoshoot) consumes this — no feature re-implements orchestration.

**Effort**: 3 days

**Dependencies**: Task 1 (user model: `superapp_users.builder`, `superapp_users.principles` columns must exist so `context.py` can read them).

**Parallel With**: —

**Blocks**: Task 3 (Spec module chain), Task 4 (Spec UI), Task 6 (photoshoot retrofit).

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task builds `server/agent_runtime/` — a bounded, feature-agnostic orchestrator for declarative AI chains. Every feature module (spec, photoshoot, future modules) defines a `ChainDefinition` (data), hands it to `run_chain`, and receives a stream of `ChainEvent`s. The primitive owns four cross-cutting concerns: per-step context assembly (user.builder + namespaced user.principles + prior step outputs), provider dispatch (Strategy pattern over Claude/Replicate/mock), per-call logging to `chain_call`, and retry-with-backoff on transient failures. It also exposes `capture_signal(generation_id, signal_type, payload)` — writing to `chain_signal`; aggregation is Epic 3. It fits the epic as Phase 1 foundation: Task 3 (spec chain) and Task 6 (photoshoot retrofit) both depend on this shipping first.

**Trade-offs considered**:
- *Async iterator vs. callback-based event emitter* → async iterator. SSE forwarding in Flask routes maps cleanly onto `async for event in run_chain(...)`; callbacks would require a queue adapter.
- *SQLModel vs. plain SQLAlchemy Core* → SQLAlchemy declarative (matches existing `server/modules/photoshoot/models.py` — no mixed ORM styles in the repo).
- *Per-call retry in `runner.py` vs. per-provider retry* → runner. Uniform policy (3 attempts, exp backoff 1s/2s/4s) applied once; providers stay dumb.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}
git status                                    # Flag any unrelated M/?? entries in server/
git diff HEAD -- server/                      # Confirm server/ tree clean (agent_runtime/ should not exist)
ls server/agent_runtime 2>&1                  # Expect: No such file or directory
pytest server/tests -q                        # Record baseline pass count
alembic -c server/alembic.ini current         # Record current migration head
```

**If working tree is dirty in `server/`**: stash or commit unrelated changes separately BEFORE starting. Task 1's migration (`{rev}_add_builder_principles.py`) MUST be the current Alembic head — if not, halt and flag.

**Baseline recorded**: `pytest server/tests -q` → [N]/[N] passing (executor fills in).

---

## 3. Files

### To Create (new)
- `server/agent_runtime/__init__.py` — package marker, re-exports `run_chain`, `capture_signal`, core types
- `server/agent_runtime/types.py` — `ChainDefinition`, `ChainStep`, `ChainStepResult`, `ChainEvent` union (`StepStartEvent`, `StepCompleteEvent`, `FinalOutputEvent`, `ErrorEvent`)
- `server/agent_runtime/context.py` — `build_context(chain_def, user, input_payload, prior_outputs) -> dict`; merges `user.builder`, `user.principles.get(chain_def.feature, {})`, and forward-mapped prior outputs
- `server/agent_runtime/runner.py` — async `run_chain(chain_def, user, input_payload) -> AsyncIterator[ChainEvent]` with retry/backoff + per-step logging
- `server/agent_runtime/logging.py` — `log_call(session, chain_def, step, result, status, error) -> ChainCall` (pure DB write, no side effects elsewhere)
- `server/agent_runtime/signals.py` — `capture_signal(session, generation_id, signal_type, payload) -> ChainSignal`
- `server/agent_runtime/models.py` — SQLAlchemy models `ChainCall`, `ChainSignal` (tables `chain_call`, `chain_signal`)
- `server/agent_runtime/providers/__init__.py` — package marker, exports `get_provider(name) -> Provider`
- `server/agent_runtime/providers/base.py` — `Provider` Protocol with `async execute(step, rendered_prompt, context) -> ChainStepResult`
- `server/agent_runtime/providers/mock.py` — deterministic fixture provider keyed by `step.id`; default for tests
- `server/agent_runtime/providers/claude.py` — Anthropic client wrapper; maps response → `ChainStepResult` (anti-corruption layer)
- `server/agent_runtime/providers/replicate.py` — Replicate client wrapper; SAME shape (skeleton OK — photoshoot retrofit in Task 6 exercises it)
- `server/migrations/versions/20260417_chain_tables.py` — Alembic migration creating `chain_call`, `chain_signal`
- `server/tests/test_agent_runtime_types.py` — type construction + event discrimination
- `server/tests/test_agent_runtime_context.py` — builder/principles merge + prior-output forwarding
- `server/tests/test_agent_runtime_runner.py` — happy path, retry-then-succeed, retry-exhausted, input_map forwarding, event ordering
- `server/tests/test_agent_runtime_logging.py` — `chain_call` row written with correct status/error
- `server/tests/test_agent_runtime_signals.py` — `capture_signal` persists row
- `server/tests/fixtures/mock_chain.py` — reusable `MOCK_CHAIN: ChainDefinition` for tests

### To Modify (cite CODEBASE CONTEXT)
- `server/core/database.py` — none required IF it already exports `Base`; if not, import from wherever photoshoot imports it. The executor verifies via: `grep -n "class Base" server/core/`. No additions here other than ensuring `agent_runtime.models` is importable when Alembic autoloads metadata.
- `server/migrations/env.py` — add `from server.agent_runtime import models as _agent_runtime_models  # noqa: F401` so Alembic sees the new tables in `target_metadata` (mirror the existing photoshoot import pattern).

### To Leave Alone
- `server/modules/photoshoot/**` — retrofit is Task 6; do NOT touch any photoshoot code in this task
- `server/modules/user/**` — builder/principles columns are Task 1; consume them read-only
- `server/app.py` — no new routes in this task (primitive has no HTTP surface; `capture_signal` exposure is Task 3's `/api/spec/signal` route)
- `src/app/**` — frontend untouched in this task

---

## 4. Implementation Steps

### Step 1: Define types

**Action**: Create the type surface the rest of the module (and future features) will import.

**File**: `server/agent_runtime/types.py` (new)

**Pattern**:
```python
from dataclasses import dataclass, field
from typing import Any, Literal, Union
from uuid import UUID

@dataclass(frozen=True)
class ChainStep:
    id: str
    provider: str                     # 'claude' | 'replicate' | 'mock'
    model: str                        # e.g. 'claude-opus-4-6'
    prompt_template: str              # Jinja2-style {{var}} placeholders
    input_map: dict[str, str] = field(default_factory=dict)  # local_key -> 'input.x' | '<prior_step_id>.field'
    output_schema: dict[str, Any] | None = None
    max_retries: int = 3

@dataclass(frozen=True)
class ChainDefinition:
    id: str
    feature: str                      # key into user.principles namespace
    steps: tuple[ChainStep, ...]

@dataclass
class ChainStepResult:
    step_id: str
    output: Any
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float
    raw_response: dict[str, Any]

@dataclass
class StepStartEvent:   type: Literal['step_start']    = 'step_start'; step_id: str = ''
@dataclass
class StepCompleteEvent: type: Literal['step_complete'] = 'step_complete'; step_id: str = ''; output: Any = None
@dataclass
class FinalOutputEvent:  type: Literal['final_output']  = 'final_output'; output: dict[str, Any] = field(default_factory=dict)
@dataclass
class ErrorEvent:        type: Literal['error']         = 'error'; step_id: str = ''; message: str = ''

ChainEvent = Union[StepStartEvent, StepCompleteEvent, FinalOutputEvent, ErrorEvent]
```

**Verify**: `python -c "from server.agent_runtime.types import ChainDefinition, ChainStep, ChainEvent; print('ok')"` — expect `ok`.

---

### Step 2: SQLAlchemy models for `chain_call` + `chain_signal`

**Action**: Declare ORM models using the same `Base` and column idioms as `server/modules/photoshoot/models.py`.

**File**: `server/agent_runtime/models.py` (new)

**Pattern**:
```python
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Text, DateTime, Numeric, JSON, Uuid
from server.core.database import Base  # same import path photoshoot uses

class ChainCall(Base):
    __tablename__ = 'chain_call'
    id             = Column(Uuid, primary_key=True, default=uuid4)
    generation_id  = Column(Uuid, nullable=True, index=True)
    user_id        = Column(Uuid, nullable=True, index=True)
    chain_id       = Column(String(128), nullable=False, index=True)
    step_id        = Column(String(128), nullable=False)
    provider       = Column(String(64),  nullable=False)
    model          = Column(String(128), nullable=False)
    tokens_in      = Column(Integer,     nullable=False, default=0)
    tokens_out     = Column(Integer,     nullable=False, default=0)
    latency_ms     = Column(Integer,     nullable=False, default=0)
    cost_usd       = Column(Numeric(10, 6), nullable=False, default=Decimal('0'))
    status         = Column(String(16),  nullable=False)       # 'ok' | 'error'
    error          = Column(Text,        nullable=True)
    created_at     = Column(DateTime,    nullable=False, default=datetime.utcnow, index=True)

class ChainSignal(Base):
    __tablename__ = 'chain_signal'
    id             = Column(Uuid, primary_key=True, default=uuid4)
    generation_id  = Column(Uuid, nullable=False, index=True)
    signal_type    = Column(String(64), nullable=False, index=True)
    payload        = Column(JSON,       nullable=False, default=dict)
    created_at     = Column(DateTime,   nullable=False, default=datetime.utcnow, index=True)
```

**Verify**: `python -c "from server.agent_runtime.models import ChainCall, ChainSignal; print(ChainCall.__tablename__, ChainSignal.__tablename__)"` — expect `chain_call chain_signal`.

---

### Step 3: Alembic migration

**Action**: Hand-author migration mirroring the style of `20260416_add_original_image_url.py` (no autogenerate — no live DB, per codebase conventions).

**File**: `server/migrations/versions/20260417_chain_tables.py` (new)

**Pattern**:
```python
"""chain_call and chain_signal tables

Revision ID: 20260417_chain_tables
Revises: <task_1_revision>         # Task 1 builder/principles migration
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '20260417_chain_tables'
down_revision = '<fill with `alembic heads` output after Task 1>'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'chain_call',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('generation_id', sa.Uuid(), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('chain_id', sa.String(128), nullable=False),
        sa.Column('step_id', sa.String(128), nullable=False),
        sa.Column('provider', sa.String(64), nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_chain_call_generation_id', 'chain_call', ['generation_id'])
    op.create_index('ix_chain_call_user_id',       'chain_call', ['user_id'])
    op.create_index('ix_chain_call_chain_id',      'chain_call', ['chain_id'])
    op.create_index('ix_chain_call_created_at',    'chain_call', ['created_at'])

    op.create_table(
        'chain_signal',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('generation_id', sa.Uuid(), nullable=False),
        sa.Column('signal_type', sa.String(64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_chain_signal_generation_id', 'chain_signal', ['generation_id'])
    op.create_index('ix_chain_signal_type',          'chain_signal', ['signal_type'])
    op.create_index('ix_chain_signal_created_at',    'chain_signal', ['created_at'])

def downgrade() -> None:
    op.drop_index('ix_chain_signal_created_at',    table_name='chain_signal')
    op.drop_index('ix_chain_signal_type',          table_name='chain_signal')
    op.drop_index('ix_chain_signal_generation_id', table_name='chain_signal')
    op.drop_table('chain_signal')
    op.drop_index('ix_chain_call_created_at',    table_name='chain_call')
    op.drop_index('ix_chain_call_chain_id',      table_name='chain_call')
    op.drop_index('ix_chain_call_user_id',       table_name='chain_call')
    op.drop_index('ix_chain_call_generation_id', table_name='chain_call')
    op.drop_table('chain_call')
```

Also append to `server/migrations/env.py` (near the other module imports):
```python
from server.agent_runtime import models as _agent_runtime_models  # noqa: F401
```

**Verify**:
```bash
alembic -c server/alembic.ini upgrade head      # Apply against SQLite dev DB or check-sql
alembic -c server/alembic.ini downgrade -1      # Confirm reversibility
alembic -c server/alembic.ini upgrade head
```
Expect no errors on up → down → up cycle. If no dev DB is configured, fall back to `alembic -c server/alembic.ini upgrade head --sql` (SQL-only dry run) and inspect that `CREATE TABLE chain_call` and `CREATE TABLE chain_signal` appear.

---

### Step 4: Provider Protocol + mock implementation

**Action**: Define `Provider` Protocol and ship the deterministic mock provider. Real Claude/Replicate providers are skeletons gated behind env so tests never hit the network.

**File**: `server/agent_runtime/providers/base.py` (new)

**Pattern**:
```python
from typing import Protocol, Any
from server.agent_runtime.types import ChainStep, ChainStepResult

class Provider(Protocol):
    name: str
    async def execute(
        self,
        step: ChainStep,
        rendered_prompt: str,
        context: dict[str, Any],
    ) -> ChainStepResult: ...
```

**File**: `server/agent_runtime/providers/mock.py` (new)

**Pattern**:
```python
import time
from typing import Any
from server.agent_runtime.types import ChainStep, ChainStepResult

class MockProvider:
    name = 'mock'

    def __init__(self, fixtures: dict[str, Any] | None = None, fail_times: dict[str, int] | None = None):
        # fixtures: step_id -> output to return
        # fail_times: step_id -> remaining failures before success
        self.fixtures = fixtures or {}
        self.fail_times = fail_times or {}
        self.calls: list[tuple[str, str]] = []   # (step_id, prompt) history for assertions

    async def execute(self, step: ChainStep, rendered_prompt: str, context: dict[str, Any]) -> ChainStepResult:
        self.calls.append((step.id, rendered_prompt))
        if self.fail_times.get(step.id, 0) > 0:
            self.fail_times[step.id] -= 1
            raise RuntimeError(f'mock transient failure for step {step.id}')
        started = time.perf_counter()
        output = self.fixtures.get(step.id, {'step_id': step.id, 'prompt': rendered_prompt})
        return ChainStepResult(
            step_id=step.id,
            output=output,
            tokens_in=len(rendered_prompt) // 4,
            tokens_out=len(str(output)) // 4,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd=0.0,
            raw_response={'mock': True, 'output': output},
        )
```

**File**: `server/agent_runtime/providers/__init__.py` (new)

**Pattern**:
```python
from server.agent_runtime.providers.base import Provider
from server.agent_runtime.providers.mock import MockProvider

_REGISTRY: dict[str, Provider] = {'mock': MockProvider()}

def register_provider(name: str, provider: Provider) -> None:
    _REGISTRY[name] = provider

def get_provider(name: str) -> Provider:
    if name not in _REGISTRY:
        raise KeyError(f'unknown provider: {name!r}. registered: {sorted(_REGISTRY)}')
    return _REGISTRY[name]
```

**File**: `server/agent_runtime/providers/claude.py` (new, skeleton — real wiring exercised in Task 3)

**Pattern**:
```python
import os, time
from anthropic import Anthropic
from server.agent_runtime.types import ChainStep, ChainStepResult

class ClaudeProvider:
    name = 'claude'
    def __init__(self, client: Anthropic | None = None):
        self._client = client or Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    async def execute(self, step: ChainStep, rendered_prompt: str, context) -> ChainStepResult:
        started = time.perf_counter()
        resp = self._client.messages.create(
            model=step.model,
            max_tokens=4096,
            messages=[{'role': 'user', 'content': rendered_prompt}],
        )
        text = ''.join(b.text for b in resp.content if b.type == 'text')
        return ChainStepResult(
            step_id=step.id,
            output=text,
            tokens_in=resp.usage.input_tokens,
            tokens_out=resp.usage.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd=0.0,  # cost calc deferred; log tokens and compute upstream
            raw_response=resp.model_dump(),
        )
```

**File**: `server/agent_runtime/providers/replicate.py` (new, skeleton)

**Pattern**:
```python
import os, time
import replicate
from server.agent_runtime.types import ChainStep, ChainStepResult

class ReplicateProvider:
    name = 'replicate'
    def __init__(self, client=None):
        self._client = client or replicate.Client(api_token=os.environ['REPLICATE_API_TOKEN'])

    async def execute(self, step: ChainStep, rendered_prompt: str, context) -> ChainStepResult:
        started = time.perf_counter()
        output = self._client.run(step.model, input={'prompt': rendered_prompt, **context.get('inference_inputs', {})})
        return ChainStepResult(
            step_id=step.id, output=output,
            tokens_in=0, tokens_out=0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd=0.0,
            raw_response={'output': list(output) if hasattr(output, '__iter__') else output},
        )
```

**Verify**: `python -c "from server.agent_runtime.providers import get_provider; p = get_provider('mock'); print(p.name)"` — expect `mock`.

---

### Step 5: Context assembly

**Action**: Merge `user.builder`, the namespaced `user.principles[chain_def.feature]`, the raw input payload, and prior outputs resolved via `step.input_map`. Renders the prompt template (simple `{{var}}` substitution — no full Jinja dep).

**File**: `server/agent_runtime/context.py` (new)

**Pattern**:
```python
import re
from typing import Any

_PLACEHOLDER = re.compile(r'\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}')

def build_context(chain_def, user, input_payload: dict[str, Any], prior_outputs: dict[str, Any]) -> dict[str, Any]:
    builder = getattr(user, 'builder', None) or {}
    all_principles = getattr(user, 'principles', None) or {}
    principles = all_principles.get(chain_def.feature, {}) if isinstance(all_principles, dict) else {}
    return {
        'builder': builder,
        'principles': principles,
        'input': input_payload,
        'steps': dict(prior_outputs),
    }

def resolve_input_map(step, context: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for local_key, path in step.input_map.items():
        resolved[local_key] = _lookup(context, path)
    return resolved

def _lookup(ctx: dict[str, Any], path: str) -> Any:
    cur: Any = ctx
    for part in path.split('.'):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur

def render_prompt(template: str, context: dict[str, Any], resolved_inputs: dict[str, Any]) -> str:
    merged = {**context, **resolved_inputs}
    def _sub(m: re.Match[str]) -> str:
        value = _lookup(merged, m.group(1))
        return '' if value is None else str(value)
    return _PLACEHOLDER.sub(_sub, template)
```

**Verify**: Covered in Step 9's `test_agent_runtime_context.py` — no separate CLI check.

---

### Step 6: Runner with retry + event stream

**Action**: Implement `run_chain`. Sequential step loop, `max_retries` attempts with exponential backoff (1s, 2s, 4s ...), emit `step_start` before each attempt, `step_complete` on success, `error` + stop on exhausted retries, `final_output` after last step.

**File**: `server/agent_runtime/runner.py` (new)

**Pattern**:
```python
import asyncio
from typing import AsyncIterator, Any
from server.agent_runtime.types import (
    ChainDefinition, ChainEvent,
    StepStartEvent, StepCompleteEvent, FinalOutputEvent, ErrorEvent,
)
from server.agent_runtime.context import build_context, resolve_input_map, render_prompt
from server.agent_runtime.providers import get_provider
from server.agent_runtime.logging import log_call

async def run_chain(
    chain_def: ChainDefinition,
    user,
    input_payload: dict[str, Any],
    *,
    db_session,
    generation_id=None,
    backoff_base: float = 1.0,  # test override
) -> AsyncIterator[ChainEvent]:
    outputs: dict[str, Any] = {}
    for step in chain_def.steps:
        yield StepStartEvent(step_id=step.id)
        context = build_context(chain_def, user, input_payload, outputs)
        resolved = resolve_input_map(step, context)
        prompt = render_prompt(step.prompt_template, context, resolved)
        provider = get_provider(step.provider)

        last_exc: Exception | None = None
        for attempt in range(step.max_retries):
            try:
                result = await provider.execute(step, prompt, context)
                log_call(db_session, chain_def, step, result, status='ok',
                         user_id=getattr(user, 'id', None), generation_id=generation_id)
                outputs[step.id] = result.output
                yield StepCompleteEvent(step_id=step.id, output=result.output)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt == step.max_retries - 1:
                    break
                await asyncio.sleep(backoff_base * (2 ** attempt))

        if last_exc is not None:
            log_call(db_session, chain_def, step, result=None, status='error',
                     error=str(last_exc),
                     user_id=getattr(user, 'id', None), generation_id=generation_id)
            yield ErrorEvent(step_id=step.id, message=str(last_exc))
            return

    yield FinalOutputEvent(output=outputs)
```

**Verify**: Covered in Step 9's `test_agent_runtime_runner.py`.

---

### Step 7: Logging helper

**Action**: Pure DB write — no exception handling beyond what SQLAlchemy raises. Caller owns the session lifecycle.

**File**: `server/agent_runtime/logging.py` (new)

**Pattern**:
```python
from decimal import Decimal
from server.agent_runtime.models import ChainCall

def log_call(session, chain_def, step, result, *, status: str, error: str | None = None,
             user_id=None, generation_id=None) -> ChainCall:
    row = ChainCall(
        generation_id=generation_id,
        user_id=user_id,
        chain_id=chain_def.id,
        step_id=step.id,
        provider=step.provider,
        model=step.model,
        tokens_in=result.tokens_in if result else 0,
        tokens_out=result.tokens_out if result else 0,
        latency_ms=result.latency_ms if result else 0,
        cost_usd=Decimal(str(result.cost_usd)) if result else Decimal('0'),
        status=status,
        error=error,
    )
    session.add(row)
    session.flush()
    return row
```

**Verify**: Covered in Step 9's `test_agent_runtime_logging.py`.

---

### Step 8: Signal capture

**Action**: Simple persistence. Aggregation is Epic 3 — DO NOT add rollups here.

**File**: `server/agent_runtime/signals.py` (new)

**Pattern**:
```python
from server.agent_runtime.models import ChainSignal

def capture_signal(session, generation_id, signal_type: str, payload: dict) -> ChainSignal:
    row = ChainSignal(generation_id=generation_id, signal_type=signal_type, payload=payload or {})
    session.add(row)
    session.flush()
    return row
```

Also populate `server/agent_runtime/__init__.py`:
```python
from server.agent_runtime.runner import run_chain
from server.agent_runtime.signals import capture_signal
from server.agent_runtime.types import (
    ChainDefinition, ChainStep, ChainStepResult, ChainEvent,
    StepStartEvent, StepCompleteEvent, FinalOutputEvent, ErrorEvent,
)
__all__ = [
    'run_chain', 'capture_signal',
    'ChainDefinition', 'ChainStep', 'ChainStepResult', 'ChainEvent',
    'StepStartEvent', 'StepCompleteEvent', 'FinalOutputEvent', 'ErrorEvent',
]
```

**Verify**: `python -c "from server.agent_runtime import run_chain, capture_signal, ChainDefinition, ChainStep; print('ok')"` — expect `ok`.

---

### Step 9: Tests (see §5 for bodies)

**Action**: Write the six test files listed under §3 and a shared `server/tests/fixtures/mock_chain.py`. Use the repo's existing `conftest.py` SQLite-in-memory session fixture (the photoshoot tests do — same pattern). Tests MUST import the session fixture by the same name the existing `server/tests/test_repository.py` uses (executor: grep `@pytest.fixture` in `server/tests/conftest.py` first to confirm fixture name; adapt if it differs from `db_session`).

**Verify**: `pytest server/tests/test_agent_runtime_*.py -v` — expect all new tests green.

---

## 5. Tests

File: `server/tests/fixtures/mock_chain.py`

```python
from server.agent_runtime.types import ChainDefinition, ChainStep

MOCK_CHAIN = ChainDefinition(
    id='mock.two_step',
    feature='spec',
    steps=(
        ChainStep(
            id='step_a', provider='mock', model='mock-v1',
            prompt_template='hello {{input.name}} from {{builder.role}}',
            input_map={'name': 'input.name'},
            max_retries=3,
        ),
        ChainStep(
            id='step_b', provider='mock', model='mock-v1',
            prompt_template='prior: {{prior}}',
            input_map={'prior': 'steps.step_a.echo'},
            max_retries=3,
        ),
    ),
)
```

File: `server/tests/test_agent_runtime_types.py`

```python
from server.agent_runtime.types import (
    ChainStep, ChainDefinition,
    StepStartEvent, StepCompleteEvent, FinalOutputEvent, ErrorEvent,
)

def test_chain_step_is_frozen():
    step = ChainStep(id='a', provider='mock', model='m', prompt_template='x')
    try:
        step.id = 'b'  # type: ignore[misc]
    except Exception as exc:
        assert 'frozen' in str(exc).lower() or isinstance(exc, AttributeError)
    else:
        raise AssertionError('ChainStep must be frozen')

def test_chain_definition_holds_tuple_of_steps():
    cd = ChainDefinition(id='c', feature='spec', steps=(ChainStep(id='a', provider='mock', model='m', prompt_template=''),))
    assert isinstance(cd.steps, tuple)
    assert cd.steps[0].id == 'a'
    assert cd.feature == 'spec'

def test_event_types_are_distinguishable_by_type_field():
    events = [StepStartEvent(step_id='a'), StepCompleteEvent(step_id='a', output={'k': 1}),
              FinalOutputEvent(output={'a': {'k': 1}}), ErrorEvent(step_id='a', message='boom')]
    assert [e.type for e in events] == ['step_start', 'step_complete', 'final_output', 'error']
```

File: `server/tests/test_agent_runtime_context.py`

```python
from types import SimpleNamespace
from server.agent_runtime.context import build_context, resolve_input_map, render_prompt
from server.tests.fixtures.mock_chain import MOCK_CHAIN

def _user(builder=None, principles=None):
    return SimpleNamespace(id=None, builder=builder, principles=principles)

def test_build_context_merges_builder_and_namespaced_principles():
    user = _user(
        builder={'role': 'solo-founder'},
        principles={'spec': {'tone': 'terse'}, 'photoshoot': {'style': 'editorial'}},
    )
    ctx = build_context(MOCK_CHAIN, user, {'name': 'world'}, prior_outputs={})
    assert ctx['builder'] == {'role': 'solo-founder'}
    assert ctx['principles'] == {'tone': 'terse'}, 'must slice to feature namespace only'
    assert ctx['input'] == {'name': 'world'}
    assert ctx['steps'] == {}

def test_build_context_handles_missing_builder_and_principles():
    user = _user(builder=None, principles=None)
    ctx = build_context(MOCK_CHAIN, user, {}, {})
    assert ctx['builder'] == {}
    assert ctx['principles'] == {}

def test_resolve_input_map_follows_dotted_paths_into_prior_outputs():
    user = _user(builder={'role': 'r'}, principles={'spec': {}})
    ctx = build_context(MOCK_CHAIN, user, {'name': 'world'}, prior_outputs={'step_a': {'echo': 'hi'}})
    resolved = resolve_input_map(MOCK_CHAIN.steps[1], ctx)
    assert resolved == {'prior': 'hi'}

def test_render_prompt_substitutes_placeholders_from_merged_scope():
    ctx = {'builder': {'role': 'r'}, 'input': {'name': 'world'}}
    rendered = render_prompt('hello {{input.name}} from {{builder.role}}', ctx, resolved_inputs={})
    assert rendered == 'hello world from r'

def test_render_prompt_treats_missing_values_as_empty_string():
    rendered = render_prompt('x={{nope.here}}', {'builder': {}, 'input': {}}, {})
    assert rendered == 'x='
```

File: `server/tests/test_agent_runtime_runner.py`

```python
import pytest
from types import SimpleNamespace
from uuid import uuid4
from server.agent_runtime.runner import run_chain
from server.agent_runtime.providers import register_provider
from server.agent_runtime.providers.mock import MockProvider
from server.agent_runtime.models import ChainCall
from server.tests.fixtures.mock_chain import MOCK_CHAIN

def _user():
    return SimpleNamespace(id=uuid4(), builder={'role': 'solo-founder'}, principles={'spec': {}})

async def _collect(aiter):
    return [ev async for ev in aiter]

@pytest.mark.asyncio
async def test_happy_path_emits_events_in_order_and_forwards_outputs(db_session):
    provider = MockProvider(fixtures={'step_a': {'echo': 'hi'}, 'step_b': {'final': 'done'}})
    register_provider('mock', provider)
    events = await _collect(run_chain(MOCK_CHAIN, _user(), {'name': 'world'},
                                      db_session=db_session, backoff_base=0))
    assert [e.type for e in events] == ['step_start', 'step_complete', 'step_start', 'step_complete', 'final_output']
    assert events[1].output == {'echo': 'hi'}
    assert events[3].output == {'final': 'done'}
    assert events[4].output == {'step_a': {'echo': 'hi'}, 'step_b': {'final': 'done'}}
    # prior-output forwarding: step_b saw 'prior: hi'
    step_b_prompt = provider.calls[1][1]
    assert step_b_prompt == 'prior: hi'

@pytest.mark.asyncio
async def test_retry_then_success_still_emits_step_complete(db_session):
    provider = MockProvider(fixtures={'step_a': {'echo': 'hi'}, 'step_b': {'ok': True}},
                            fail_times={'step_a': 2})  # fails twice, third attempt succeeds
    register_provider('mock', provider)
    events = await _collect(run_chain(MOCK_CHAIN, _user(), {'name': 'x'},
                                      db_session=db_session, backoff_base=0))
    types = [e.type for e in events]
    assert types == ['step_start', 'step_complete', 'step_start', 'step_complete', 'final_output']
    assert len([c for c in provider.calls if c[0] == 'step_a']) == 3, 'should retry twice then succeed'

@pytest.mark.asyncio
async def test_retry_exhausted_emits_error_and_halts_chain(db_session):
    provider = MockProvider(fixtures={}, fail_times={'step_a': 99})
    register_provider('mock', provider)
    events = await _collect(run_chain(MOCK_CHAIN, _user(), {'name': 'x'},
                                      db_session=db_session, backoff_base=0))
    types = [e.type for e in events]
    assert types == ['step_start', 'error'], f'expected early halt, got {types}'
    assert 'mock transient failure' in events[1].message
    assert not any(c[0] == 'step_b' for c in provider.calls), 'step_b must not run after step_a fails'

@pytest.mark.asyncio
async def test_runner_writes_chain_call_rows_with_status(db_session):
    provider = MockProvider(fixtures={'step_a': {'echo': 'hi'}, 'step_b': {'ok': 1}})
    register_provider('mock', provider)
    await _collect(run_chain(MOCK_CHAIN, _user(), {'name': 'x'}, db_session=db_session, backoff_base=0))
    rows = db_session.query(ChainCall).order_by(ChainCall.created_at.asc()).all()
    assert [r.step_id for r in rows] == ['step_a', 'step_b']
    assert all(r.status == 'ok' for r in rows)
    assert all(r.chain_id == MOCK_CHAIN.id for r in rows)
    assert all(r.provider == 'mock' for r in rows)

@pytest.mark.asyncio
async def test_runner_logs_error_row_when_retries_exhausted(db_session):
    provider = MockProvider(fixtures={}, fail_times={'step_a': 99})
    register_provider('mock', provider)
    await _collect(run_chain(MOCK_CHAIN, _user(), {'name': 'x'}, db_session=db_session, backoff_base=0))
    rows = db_session.query(ChainCall).all()
    assert len(rows) == 1
    assert rows[0].status == 'error'
    assert rows[0].error is not None and 'mock transient failure' in rows[0].error

@pytest.mark.asyncio
async def test_runner_rejects_unknown_provider(db_session):
    from server.agent_runtime.types import ChainDefinition, ChainStep
    bad = ChainDefinition(id='bad', feature='spec',
                          steps=(ChainStep(id='a', provider='nope_xyz', model='m', prompt_template=''),))
    with pytest.raises(KeyError, match='unknown provider'):
        async for _ in run_chain(bad, _user(), {}, db_session=db_session, backoff_base=0):
            pass
```

File: `server/tests/test_agent_runtime_logging.py`

```python
from decimal import Decimal
from uuid import uuid4
from server.agent_runtime.logging import log_call
from server.agent_runtime.models import ChainCall
from server.agent_runtime.types import ChainStepResult
from server.tests.fixtures.mock_chain import MOCK_CHAIN

def test_log_call_persists_success_row(db_session):
    result = ChainStepResult(step_id='step_a', output={'x': 1},
                             tokens_in=10, tokens_out=20, latency_ms=123,
                             cost_usd=0.0042, raw_response={})
    row = log_call(db_session, MOCK_CHAIN, MOCK_CHAIN.steps[0], result,
                   status='ok', user_id=uuid4(), generation_id=uuid4())
    db_session.commit()
    fetched = db_session.query(ChainCall).filter_by(id=row.id).one()
    assert fetched.status == 'ok'
    assert fetched.tokens_in == 10 and fetched.tokens_out == 20
    assert fetched.latency_ms == 123
    assert fetched.cost_usd == Decimal('0.004200')
    assert fetched.error is None
    assert fetched.chain_id == MOCK_CHAIN.id
    assert fetched.step_id == 'step_a'

def test_log_call_persists_error_row_with_null_metrics(db_session):
    row = log_call(db_session, MOCK_CHAIN, MOCK_CHAIN.steps[0], result=None,
                   status='error', error='provider timeout')
    db_session.commit()
    fetched = db_session.query(ChainCall).filter_by(id=row.id).one()
    assert fetched.status == 'error'
    assert fetched.error == 'provider timeout'
    assert fetched.tokens_in == 0 and fetched.tokens_out == 0 and fetched.latency_ms == 0
```

File: `server/tests/test_agent_runtime_signals.py`

```python
from uuid import uuid4
from server.agent_runtime.signals import capture_signal
from server.agent_runtime.models import ChainSignal

def test_capture_signal_persists_row_with_payload(db_session):
    gen = uuid4()
    row = capture_signal(db_session, gen, 'thumbs_up', {'reason': 'clear'})
    db_session.commit()
    fetched = db_session.query(ChainSignal).filter_by(id=row.id).one()
    assert fetched.generation_id == gen
    assert fetched.signal_type == 'thumbs_up'
    assert fetched.payload == {'reason': 'clear'}

def test_capture_signal_defaults_payload_to_empty_dict(db_session):
    row = capture_signal(db_session, uuid4(), 'view', None)  # type: ignore[arg-type]
    db_session.commit()
    fetched = db_session.query(ChainSignal).filter_by(id=row.id).one()
    assert fetched.payload == {}
```

**Framework notes**: `pytest.mark.asyncio` requires `pytest-asyncio` — if not already listed in `server/requirements-dev.txt` / `pyproject.toml`, add it (this IS a deviation — log it in the commit body per §9). If the existing `db_session` fixture auto-creates tables from `Base.metadata`, the `ChainCall` + `ChainSignal` models will be picked up automatically once `server/agent_runtime/models` is imported by a test module.

---

## 6. Commit Plan

One logical unit per commit:

1. `feat(agent_runtime): types, providers, context primitives` — `server/agent_runtime/__init__.py`, `types.py`, `context.py`, `providers/{base,mock,claude,replicate,__init__}.py`: the pure, DB-free surface.
2. `feat(agent_runtime): ChainCall + ChainSignal models and migration` — `server/agent_runtime/models.py`, `server/migrations/versions/20260417_chain_tables.py`, `server/migrations/env.py`: persistence layer.
3. `feat(agent_runtime): run_chain + log_call + capture_signal` — `server/agent_runtime/{runner,logging,signals}.py`: orchestrator and DB writers wired to models.
4. `test(agent_runtime): types, context, runner, logging, signals` — `server/tests/test_agent_runtime_*.py`, `server/tests/fixtures/mock_chain.py`: complete assertion bodies covering happy path, retry, retry-exhausted, logging, signal capture.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation (e.g. `Deviations: added pytest-asyncio to server/requirements-dev.txt — not previously present.`).

---

## 7. Verification

```bash
cd {WORKSPACE}
pytest server/tests -q
alembic -c server/alembic.ini upgrade head
alembic -c server/alembic.ini downgrade -1
alembic -c server/alembic.ini upgrade head
python -c "from server.agent_runtime import run_chain, capture_signal; print('imports ok')"
```

**Expected delta**: [N] → [N + 17] passing (2 types + 5 context + 6 runner + 2 logging + 2 signals = 17 new tests). Zero pre-existing tests broken. Alembic up/down/up cycle clean.

---

## 8. Rollback

- **Per-step / per-commit**: each of the 4 commits is independently revertible. `git revert <sha>`. Revert order (newest first): tests → runner → models+migration → types+providers. Revert of the migration commit also requires `alembic -c server/alembic.ini downgrade -1` against any environment that already ran `upgrade head`.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch, then `alembic -c server/alembic.ini downgrade -1` on any DB that saw the migration. Do NOT force-push shared branches [REQUIRES APPROVAL].

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** (e.g., `server/core/database.py` doesn't expose `Base` at the cited location) → grep for `class Base` under `server/` and import from the actual location; do NOT invent a new `Base`.
- **Test fixture name differs** (`db_session` vs. `session` vs. `db`) → inspect `server/tests/conftest.py`, match the existing name, note the mismatch in the test commit body.
- **`pytest-asyncio` not installed** → add to `server/requirements-dev.txt` (or `pyproject.toml` `[tool.poetry.group.dev]` — whichever the repo uses). Log as a deviation in commit 4.
- **`anthropic` / `replicate` Python SDKs missing** → the Claude/Replicate provider modules can still be authored (they're not exercised until Task 3/6), but their `import` at module top forces a dependency. Move imports inside `__init__` to keep module import cheap and tests hermetic. Log the change.
- **Alembic `down_revision`** → must equal `alembic heads` output after Task 1 is applied. If Task 1 hasn't landed on the branch, STOP and flag — this task depends on it.
- **Side effects required** (schema change to shared Neon, `npm publish`, destructive DB op) → STOP and mark [REQUIRES APPROVAL]. Local SQLite test DB upgrades are fine; Neon schema push is not part of this task.
- **Step N unlocks an obvious simplification for Step N+1** (e.g., consolidating `logging.py` into `runner.py` if the helper is trivially short) → take it, log the deviation.

---

## 10. Out of Scope

The executor must STOP and flag rather than absorb any of the following:

- **Cost-in-USD calculation** per provider/model — logged as `0.0` for now; Epic 3 computes from a pricing table.
- **Signal aggregation / rollups** — `capture_signal` only persists rows; no queries, no dashboards.
- **Route exposure of `capture_signal`** — the HTTP endpoint (`POST /api/spec/signal`) belongs to Task 3.
- **Spec-chain definition / spec prompts** — Task 3.
- **Photoshoot retrofit** — Task 6. Do NOT touch `server/modules/photoshoot/` in this task.
- **Frontend / SSE wiring** — Task 4. Runner emits dataclass events; translating to SSE lines is a route-handler concern.
- **Real Claude / Replicate API exercise** — skeletons only; no live-network tests in CI.
- **`user.builder` / `user.principles` column creation** — Task 1.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)