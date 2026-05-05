# 🔍 Chain Primitive — Analysis

## The Problem
`adapter.py` and providers shipped; the runner that sequences them is missing. Bootstrap workflow lives as a 5-step JS loop in the browser — untestable server-side, requires the tab to stay open. The three items (runner, bootstrap port, OpenAPI contract) are sequentially dependent; shipping them separately risks a hardcoded `BootstrapService` that gets retro-ported the moment the runner exists.

## Hard Constraints
- Tasks 1–3 merged: context unified (`/api/context/{key}`), `PromptBuilder` shipped, template generators on `/api/templates/*`
- `adapter.py`, providers, `context.py`, `file_parser.py`, `errors.py` already exist — runner is the only new infrastructure
- `dtos/models.py` is generated; `make check-dtos` must pass in CI; never hand-edit
- No master push — always PR; structural tests must stay green between phases
- SSE deferred: v1 is synchronous JSON + polling pair only
- In-memory bootstrap status tracking is correct for single-user dev tool
- `POST /api/ai/text/generate-spec` keeps its URL and client-visible response shape — Phase B is an internal refactor
- Context loading is outside the runner; route reads context and passes a flat `inputs` dict

## Open Questions
- **`generate-spec` outbound shape after Phase B**: keep `===FILE:===` markers outbound for backward compat, or switch to structured `{spec_index, analysis, epic, architecture}`? Brain dump explicitly defers this to "the spec phase" — must decide before `routes.py` is touched
- **`BOOTSTRAP_CHAIN` composition**: flatten all nine steps in one `ChainDefinition`, or call `run_chain(SPEC_CHAIN, …)` from inside a bootstrap step? Brain dump recommends flatten; trade-off is real since `generate-spec` endpoint also drives `SPEC_CHAIN` independently
- **`GENERATE_TASK_CHAIN`**: brain dump mentions wrapping single-shot task-gen as a one-step chain to unlock future multi-step workflows, but the task breakdown omits it — in scope or not?
- **Chains module home**: `flask/modules/ai/chains.py` now, `flask/modules/chains/` at count ≥ 3; this epic declares 2–3 chains, so the threshold may trigger mid-epic — decide the boundary before Phase B

## Dependencies & Sequencing
- Runner (`ChainStep`, `ChainDefinition`, `run_chain`, structural test) blocks all chain declarations
- `SPEC_CHAIN` declaration blocks `generate-spec` route refactor and `BOOTSTRAP_CHAIN` declaration
- `BOOTSTRAP_CHAIN` + polling endpoints block Angular `BootstrapService`
- OpenAPI flattening blocks on both `generate-spec` refactor and polling-pair routes being stable

## Explicitly Out of Scope
- `GENERATE_TASK_CHAIN` declaration — one consumer; re-scope when a second task-gen step appears
- JSON chain definitions on disk — two Python chains need no loader; trigger: count ≥ 5 or user-editable chains
- `STEP_HANDLERS` dispatch — all current chains are single-op-type; trigger: two chains share atomic-op vocabulary
- Observer / `chainCompleted` events — stdout structlog sufficient; trigger: cost analytics or usage-limit enforcement
- Retry/backoff per step — no failure data; trigger: first production rate-limit incident
- Removal of per-step batch endpoints — separate PR after ≥ 1 week green dev traffic on the polling pair