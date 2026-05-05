# spec-doc-api — Chain Primitive, Bootstrap, OpenAPI: Finish the Foundation

## What

Three architecturally-linked items collapsed into one epic:

1. **Finish the chain primitive port from Bubls** — we shipped the adapter; the runner is missing.
2. **Replace the 5-call frontend bootstrap loop with a server-side chain** — was architecture-cleanup Task 4; now becomes "declare `BOOTSTRAP_CHAIN`".
3. **Flatten the OpenAPI surface to its final post-cleanup shape** — was architecture-cleanup Task 5; needs Task 4's final routes.

These were three separate task specs. They're one architectural move: build the primitive, declare two existing pipelines as chains, update the contract. Doing them together avoids shipping a hardcoded `BootstrapService` that throws away the moment the runner exists.

## Why combined

The chain-primitive-port spec, the architecture-cleanup Task 4 (Bootstrap Facade), and architecture-cleanup Task 5 (Flatten OpenAPI) were three views of the same change:

- **Chain-primitive-port** says: port `run_chain()`, declare `SPEC_CHAIN`. That makes the runner real.
- **Bootstrap Facade** says: move the 5-step JS loop server-side as a `BootstrapService`. That's an `Application Service` with a hardcoded sequence — exactly what `run_chain` exists to *replace*.
- **Flatten OpenAPI** says: update `openapi.yaml` to reflect the final route surface. Task 4's outcome dictates the shape: a polling pair (`POST /api/capability/bootstrap` + `GET /api/capability/bootstrap/{id}/status`) is the v1 contract whether or not the implementation uses `run_chain`. The chain primitive shrinks the handler from ~80 lines (a bespoke service) to ~30 lines (a `run_chain` call).

Doing Bootstrap Facade as a hardcoded service first means writing a service that gets retro-ported to chain-runner-style later. Doing the chain primitive first means Task 4 is `BOOTSTRAP_CHAIN = ChainDefinition(...)` plus a route — ~30 lines instead of ~80.

**Streaming (SSE) is explicitly deferred.** v1 ships synchronous request-response for short calls and a polling pair for long-running bootstrap. Adds zero new transport machinery; matches the existing `/api/ai/text/*` endpoint shape. SSE is a follow-up upgrade triggered by user-reported wait-time complaints, not a v1 requirement.

## What got ported (already in `flask/modules/chain/`)

- `adapter.py` — single-shot AI call boundary; provider selection via `CHAIN_PROVIDER`.
- `providers/{claude,cli,mock}.py` — three provider implementations.
- `context.py` — `with_context()` prepends builder/principles to system prompt.
- `context_loader.py` — sole reader of the four workspace context files.
- `types.py` — `ChainResult`, `ReviewResult` frozen dataclasses.
- `file_parser.py` — `===FILE:===`/`===LINT===`/`===SCORE===` marker parser.
- `errors.py` — `ProviderError(message, status_code)`.

What's missing: the runner, `ChainStep`, `ChainDefinition`, `ChainEvent`, chain instances, the polling-pair endpoints for long-running bootstrap, structural test that prevents chain-by-copy-paste.

## What got cleaned up (already on unmerged branches)

- `task/1-unify-context-services` — 4 context services collapsed into one parametric `ContextService`; 8 routes → 2; 6 component consumers updated.
- `task/2-migrate-prompts-to-flask` — `PromptBuilder` fluent assembler; `build_implementation_guide_prompt` extracted into a new `implementation_guide` module; structural test forbids prompt strings in route handlers.
- `task/3-extract-template-generators` — `generate_spec_index`/`generate_timeline`/`generate_readme` ported to `flask/modules/templates/generators.py` with snapshot tests; Angular bootstrap loop now calls `/api/templates/...` for those three files.

After these merge, the bootstrap loop in `new-project.component.ts` is *almost* a chain — five sequential AI/HTTP calls in JS, each consuming the previous's output. This epic finishes the move.

## How Bubls used it (the source pattern, briefly)

In Bubls' `agent_runtime/runner.py`, chain primitive backed `/text` page's multi-pass operations. Three concrete chains: deep-humanize (3 sequential rewrite passes), brain-dump-to-docs (lint → multi-file-generate → score), rewrite-review (rewrite → review-with-rubric → rewrite-with-issues). Each chain a JSON file in `chain/definitions/`. Three glue primitives: `STEP_HANDLERS: dict[str, Callable]` dispatch, manifest-resolved context blocks, `chainCompleted` Observer event.

Spec-doc doesn't need most of that for v1. We need: the runner, two chain instances declared as Python values, and a polling-pair endpoint for the long-running bootstrap workflow. JSON definitions, `STEP_HANDLERS` dispatch, Observer events, and SSE all defer to follow-up triggers.

## How spec-doc uses it (target state)

Every implicit chain becomes a `ChainDefinition`:

| Chain | Steps | Today | After |
|---|---|---|---|
| `SPEC_CHAIN` | analysis → epic → architecture → spec-doc-spec | one Claude call with `===FILE:===` markers, ~30s blank loading | 4-step `run_chain`, per-step testable, same JSON response shape |
| `BOOTSTRAP_CHAIN` | lint → spec → timeline → readme → save | 5 sequential JS calls in `new-project.component.ts`, browser must stay open | Single server-side `run_chain`; one POST + 1–2s polling on `/status/{id}` |

After the runner ships, the Bootstrap Facade collapses from "build a `BootstrapService` Application Service" to "declare `BOOTSTRAP_CHAIN` plus a 30-line route handler that calls `run_chain`". The Application Service vanishes; the chain *is* the orchestrator.

`GENERATE_TASK_CHAIN` (single-shot today) doesn't strictly need a chain wrapper, but declaring it as a one-step chain unlocks the next multi-step task-gen workflow (e.g. lint-then-generate, or per-task review pass) without re-architecting.

## What this epic covers

### Phase A — Runner

- `flask/modules/chain/runner.py` with:
  - `ChainStep` (frozen dataclass: name, prompt_fn, input_keys)
  - `ChainDefinition` (name, steps)
  - `ChainEvent` (Pydantic BaseModel: type, step?, data) — used internally for logging and tests; not serialized over HTTP in v1
  - `_resolve_inputs(inputs, outputs)` for `$`-prefixed references
  - `run_chain(definition, inputs) -> Iterator[ChainEvent]` — sequential generator, halts on error, never silent truncation
- Unit tests against `CHAIN_PROVIDER=mock`: full event sequence, two-step chain, step-failure halt, missing-ref error, JSON roundtrip of `ChainEvent`.
- Structural test `pipelinedFeatures_useRunChain` — AST-greps `modules/*/routes.py` for handlers calling `chain_adapter.generate`/`stream` more than once. Ships alongside the primitive because this is when the violation class first becomes possible.

### Phase B — `SPEC_CHAIN` (refactor `generate-spec` internally)

- Split `generate_spec_prompt` into 4 step prompt functions (`spec_analysis_prompt`, `spec_epic_prompt`, `spec_architecture_prompt`, `spec_doc_spec_prompt`). Each uses `PromptBuilder` (already shipped on `task/2-migrate-prompts-to-flask`). Drop `===FILE:===` framing — the runner owns output composition; each step produces one document.
- Declare `SPEC_CHAIN` in `flask/modules/ai/chains.py` wiring the four step functions with explicit `$`-ref input resolution.
- The existing `POST /api/ai/text/generate-spec` keeps its current request/response shape; the route handler is rewritten to call `run_chain(SPEC_CHAIN, inputs)`, drain events into a final `{files: [...]}` envelope (still using the `===FILE:===` markers OUTBOUND for backward compatibility, OR returning a structured `{spec_index, analysis, epic, architecture}` object — pick one in the spec phase). No new endpoint, no SSE.
- `ChainEvent`s are produced internally — used for logging (`logger.info` per step) and tests, not serialized over HTTP.

### Phase C — `BOOTSTRAP_CHAIN` (replace the JS loop)

- Declare `BOOTSTRAP_CHAIN` with the five orchestration steps that replace the current JS loop: `lint` → `spec` → `timeline` → `readme` → `save_to_disk`.
  - **Open question:** does the `spec` step call `run_chain(SPEC_CHAIN, ...)` from inside it (chain-of-chains), or does `BOOTSTRAP_CHAIN` flatten the four spec sub-steps inline (9 top-level steps)? Recommend **flatten** for v1: nine top-level steps, one generator. Less abstraction, no nested generators to debug. Trade: less reuse if `SPEC_CHAIN` ever needs to be invoked outside bootstrap (it does — `generate-spec` endpoint also uses it). Mitigation: both chains share step prompt *functions*, just not a shared `run_chain` call.
- Two endpoints (polling pair, no SSE):
  - `POST /api/capability/bootstrap` — accepts `{name, braindump}`. Spawns the chain in a background thread, returns `{project_id}` immediately. In-memory dict tracks `{step, done, error}` keyed by project_id.
  - `GET /api/capability/bootstrap/{id}/status` — returns the current step name, done flag, error message, and (when done) the final `{files: [...]}` payload. Frontend polls every 1–2s until `done: true`.
- Frontend `BootstrapService` (Angular) replaces the JS loop with one POST + a polling loop. Component reads `current_step` from the status response for progress UI ("Step 4/9: generating timeline..."); `done: true` triggers project navigation. The `CONCURRENCY = 2` cap and the per-step orchestration disappear.
- In-memory tracking means job state is lost on server restart. Acceptable for a sub-2-minute workflow on a dev tool. Database-backed tracking is the upgrade trigger when auth + multi-user state lands.
- Remove `loadProjectContext`'s lint/spec/timeline/readme calls from `new-project.component.ts`. The bootstrap path becomes one POST + a polling loop, not five sequential AI calls.

### Phase D — OpenAPI flattening (was Task 5)

- `openapi.yaml` final shape after all branches merge.
  - Drop: 4 individual context paths (already done in Task 1), 4 bootstrap-step paths (`/lint-braindump`, `/generate-spec`'s siblings consumed by the JS loop). Keep batch endpoints during soak; remove only after Phase C ships and the frontend stops calling them.
  - Add: `/api/capability/bootstrap` (POST), `/api/capability/bootstrap/{id}/status` (GET).
  - Keep: per-template paths from Task 3 (`/api/templates/spec-index`, `/api/templates/timeline`, `/api/templates/readme`); context route from Task 1 (`/api/context/{key}`); the four AI text endpoints that have non-bootstrap consumers (`/rewrite`, `/iterate`, `/review`, `/generate`, `/generate-spec`).
- `make generate-dtos` regenerates `flask/dtos/models.py`; CI drift check (`make check-dtos`) passes clean.
- Structural test `everyOpenapiPath_hasRouteHandler` stays green throughout.

## What this epic does NOT cover

- ❌ **JSON chain definitions / loadable from disk.** Python values in `flask/modules/ai/chains.py` are sufficient. Trigger to switch: chain count ≥ 5 OR user-editable chains becomes a real ask.
- ❌ **`STEP_HANDLERS` dispatch over op names.** Bubls had it because `/text` mixed `rewrite`/`generate`/`review` ops. Spec-doc's chains today are all "generate" — composing different op types isn't a real use case yet. Defer until two chains share atomic-op vocabulary.
- ❌ **Multi-file output parsing inside `run_chain`.** `file_parser.py` already exists. Wire it in only when a chain explicitly needs structured multi-file output. SPEC_CHAIN doesn't (each step produces one document); BOOTSTRAP_CHAIN doesn't.
- ❌ **Observer / `chainCompleted` event for analytics.** Defer until cost analytics or usage-limit enforcement is a real ask. Stdout structlog is enough.
- ❌ **DB-backed chain runs / `chain_call` table.** Stdout JSON is sufficient for a single-user dev tool.
- ❌ **Retry/backoff per step.** No failure data; trigger: first production rate-limit incident.
- ❌ **Provider routing per step** (e.g. Haiku for analysis, Sonnet for architecture). No cost signal yet.
- ❌ **SSE / `text/event-stream` endpoints.** v1 ships synchronous JSON for short operations and a polling pair for bootstrap. SSE adds new transport machinery (Flask generator response handling, frontend `EventSource`) for a UX gap polling already covers. Upgrade trigger: a user-reported wait-time complaint that polling-granularity (1–2s) cannot address.
- ❌ **Per-token streaming inside a step.** The default `CHAIN_PROVIDER=cli` doesn't stream — `subprocess.run` blocks until the process exits. Token streaming requires either switching to the SDK provider or upgrading the CLI provider to use `subprocess.Popen` + `--output-format stream-json`. Both are deferred until the SSE upgrade triggers.
- ❌ **Database-backed bootstrap status tracking.** In-memory dict is correct for a single-user dev tool. Upgrade trigger: auth + multi-user state.
- ❌ **Frontend `EventSource` consumer.** Polling pair is the v1 transport. Angular `BootstrapService` does `setInterval` polling, not SSE subscription.
- ❌ **Bubls-specific chains** (deep-humanize, braindump-to-docs, rewrite-review). Cite the patterns; don't import the chains.
- ❌ **User-editable chain definitions.** Needs auth, versioning, prompt-injection review. Trigger: confirmed user ask.
- ❌ **Chain composition / chain-of-chains** as a runtime concept. `BOOTSTRAP_CHAIN` flattens its `spec` substeps inline rather than calling `run_chain(SPEC_CHAIN, ...)` recursively. Trigger: a third pipeline shares ≥2 steps with both `SPEC_CHAIN` and `BOOTSTRAP_CHAIN`.
- ❌ **Per-step events exposed over HTTP** for any endpoint. `ChainEvent`s stay server-side (logging + tests). Bootstrap progress is polled via `/status/{id}`; `generate-spec` stays synchronous request-response.
- ❌ **Removal of batch endpoints** (`generate-spec`, etc.) — separate PR after ≥1 week green dev traffic on streaming. Soak first, delete later.

## Why now

Three forcing functions:

1. **Architecture-cleanup Tasks 1–3 just landed.** Context unified, prompts migrated, templates extracted. The bootstrap loop is now *just* lint+spec+timeline+readme+save calls — exactly the shape `run_chain` exists to consume.
2. **PromptBuilder shipped (Task 2).** Step prompts use it. The chain primitive consumes step prompts. Sequencing them back-to-back is cheap.
3. **Avoid the throw-away.** If we ship Task 4 as a hardcoded `BootstrapService`, we'll retro-port it once the runner exists. One PR now beats two PRs later.

## Open questions

- **Chain-of-chains or flatten?** `BOOTSTRAP_CHAIN.steps[1]` (the spec step) — does it call `run_chain(SPEC_CHAIN, ...)` inline, or does it inline the four spec sub-steps directly? Recommend flatten for v1: nine top-level steps in `BOOTSTRAP_CHAIN`, one generator. Trade: less reuse if `SPEC_CHAIN` is ever invoked outside bootstrap. Mitigation: it can be — generate-spec/stream still exists as its own endpoint with its own chain instance. The two chains share step prompt functions, just not a shared `run_chain` call.
- **Polling interval for bootstrap status?** 1–2s. Frontend updates "Step N of 9" label; user sees discrete progress. Same UX as the current per-step JS loop, just controlled server-side.
- **Where do chains live?** `flask/modules/ai/chains.py` for now (single home, alongside prompts). Move to `flask/modules/chains/` when the count hits 3+ or non-AI chains appear.
- **Soak window length before deleting per-step endpoints?** ≥1 week of green dev traffic on the polling pair. Separate PR. Structural test flags any new code that bypasses `run_chain` mid-soak.
- **Context loading inside or outside the runner?** Outside. Route reads context, runner receives a flat `inputs` dict. Keeps the runner pure and testable with a plain dict.

## Suggested task breakdown

When this brain dump bootstraps, the epic generator should produce roughly:

| # | Task | Dependencies |
|---|---|---|
| 1 | Port chain runner (`run_chain`, `ChainStep`, `ChainDefinition`, `ChainEvent`, structural test) | None |
| 2 | Split `generate_spec_prompt` into 4 step functions; declare `SPEC_CHAIN` | 1 |
| 3 | Refactor `POST /api/ai/text/generate-spec` to call `run_chain(SPEC_CHAIN, ...)` internally; same response shape | 1, 2 |
| 4 | Declare `BOOTSTRAP_CHAIN` (flat 9-step); in-memory status tracker module | 1, 2 |
| 5 | `POST /api/capability/bootstrap` + `GET /api/capability/bootstrap/{id}/status` polling pair | 4 |
| 6 | Angular `BootstrapService` (1–2s polling); replace `new-project.component.ts` JS loop | 5 |
| 7 | Final `openapi.yaml` flattening + DTO drift check | 3, 5 |

Tasks 1, 2, 3 are the chain-primitive-port content. Tasks 4, 5, 6 are the Bootstrap Facade refit. Task 7 is OpenAPI cleanup. The original Task 4 (Bootstrap Facade as a service) and Task 5 (Flatten OpenAPI) of architecture-cleanup are **superseded** by this epic.

## Decision

Replace the standalone Task 4 + Task 5 specs in architecture-cleanup with this combined epic. The phase5 chain-primitive brain dump (the previous version of this file) is also superseded. Architecture-cleanup ends at Task 3 (already done); the epic that follows is "phase 5: chain primitive + bootstrap + openapi consolidation".

Then chains are a thing. Then bootstrap is a chain. Then every workflow is a chain. Then every new workflow is a Python value or a JSON file, not a new module.
