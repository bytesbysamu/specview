# Chain Adapter Conventions — spec-doc / specview

This reference describes the AI call adapter layer in `api/modules/runtime/chain/`.
All agents and skills that touch AI generation must read this file first.

## The Adapter Boundary

Feature modules import ONLY from `modules/runtime/chain/adapter.py`. Direct imports
from `providers.*` are forbidden and enforced by `test_structural.py`.

The four public functions:

- `generate(system, prompt, *, builder, principles, model, max_tokens) -> ChainResult`
- `rewrite(system, prompt, *, model, max_tokens) -> ChainResult`
- `stream(system, prompt, *, builder, principles, model, max_tokens) -> Iterator[str]`
- `stream_generate(system, prompt, *, model, max_tokens) -> Iterator[str]`

`generate` and `stream` inject `builder` and `principles` context via `with_context()`.
`rewrite` and `stream_generate` are caller-driven — no automatic context injection.

## Providers

Three providers exist under `api/modules/runtime/chain/providers/`:

- `cli.py` — subprocess call to the `claude` CLI. Used in Docker with mounted
  `~/.claude` credentials. No API key. Calls `claude -p --output-format text`.
  Optionally routes through `--agent chain-agent` when `CHAIN_AGENT` env var is set.
- `claude.py` — Anthropic SDK. Used when `ANTHROPIC_API_KEY` is present.
- `mock.py` — Deterministic fixture output. Tests only.

Provider selection via `CHAIN_PROVIDER` env var (explicit overrides auto-detection).
In production Docker: always set `CHAIN_PROVIDER=cli`.

## ChainResult

```python
@dataclass(frozen=True)
class ChainResult:
    text: str
    latency_ms: int
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
```

`tokens_in` and `tokens_out` are None for the CLI provider (subprocess gives no token counts).

## Context Injection

`with_context(system, *, builder, principles)` prepends builder-profile and principles
strings to the system prompt. Populated from `api/modules/data/context/` files.
Context injection happens inside `generate()` and `stream()` — callers pass raw
builder/principles strings, not pre-composed prompts.

## SQLModel Conventions

Models live in `api/modules/{module}/models.py`. Mandatory patterns:

- All models extend `SQLModel`. Table models set `table=True`.
- Primary keys are `str` (UUID) with `default_factory=lambda: str(uuid4())`.
- `created_at: datetime` with `default_factory=datetime.utcnow`.
- Never use raw SQL in route handlers — always call a service function.
- Session dependency via `get_session()` — never construct sessions manually.

## Alembic Conventions

Migrations live in `api/migrations/versions/`. Rules:

- Auto-generate with `alembic revision --autogenerate -m "<description>"`.
- Review generated migration before applying — never apply blindly.
- One concern per migration file — no combined schema + data migrations.
- Never drop a column in the same migration that removes application code using it.
- Downgrade functions must be implemented (not `pass`).

## Workflow Steps

Workflows under `api/modules/ai/workflows/` use `AICall` steps. Each step:

- Specifies a system prompt, a prompt template, and optionally `stream=True`.
- References `chain.generate()` or `chain.stream_generate()` indirectly via the step runner.
- Is not imported by feature modules — workflows import from `workflows.steps`.

## Error Handling

`ProviderError(message, http_status)` — raised by providers on subprocess failure,
timeout (3600s), or missing CLI binary. Feature code catches `ProviderError` only.
Never catch base `Exception` in chain code.

## Adding a New Provider

1. Create `api/modules/runtime/chain/providers/{name}.py`.
2. Implement `create_message(system, prompt, *, model, max_tokens) -> tuple[str, None, None]`.
3. Optionally implement `stream_message(system, prompt, *, model, max_tokens) -> Iterator[str]`.
4. Register in `adapter._select_provider()` mapping dict.
5. Add a test in `providers/tests/`.

## Quality Rules (non-negotiable)

- Never import `providers.*` from a feature module.
- Never construct a `ChainResult` outside of `adapter.py` (except in tests).
- Never pass a composed system+prompt string — keep them separate.
- Never set `max_tokens` above 8192 without an explicit reason in the PR.
- Always use `CHAIN_PROVIDER=cli` in Docker; never hardcode a provider name.
