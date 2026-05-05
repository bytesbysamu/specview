---
sidebar_position: 3
---

# 🏗️ Spec Route + Chain Primitive – Solution Architecture

**Purpose**: Technical design for the `/spec` feature module, the shared chain primitive that underlies it, the builder/principles user model, and the photoshoot retrofit.

**Epic Reference**: See [Epic](./epic.md) for scope, tasks, and success criteria.

---

## Architecture Overview

Three layers collaborate:

1. **User model** (`superapp_users.builder`, `superapp_users.principles`) — namespaced JSONB read by every feature that needs context about who the user is and what decisions they have accumulated.
2. **Chain primitive** (`server/agent_runtime/`) — a bounded orchestrator that takes a declarative chain definition, injects builder + principles, runs the steps sequentially, streams events, logs every model call, and exposes a signal-capture endpoint.
3. **Feature modules** (`server/modules/spec/`, `server/modules/photoshoot/`) — each owns a chain *definition* (data, not code), prompts, route handlers, OpenAPI YAML, and feature-gate entry. Routes never call Claude or Replicate directly; they construct inputs, call `run_chain`, and forward the stream.

Frontend mirrors the shape: `/spec` is a standalone Angular route with a `SpecService` adapter that consumes SSE events from `POST /api/spec/generate`, and `/onboarding` is a standalone route that writes to `PUT /api/user/builder`. Feature-registry entries gate both behind flags on the user object.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = bounded context | `server/modules/spec/` owns its chain config, prompts, OpenAPI, routes. No imports from `modules/photoshoot/`. |
| Adapter everywhere | `SpecService` adapts SSE stream into signals; chain primitive adapts provider responses into `ChainEvent`s. |
| Strategy for providers | Each `ChainStep` declares `provider: claude \| replicate \| openai`. Primitive dispatches. |
| Registry via routes | `/spec` and `/onboarding` added to `app.routes.ts`. Shell untouched. |
| Feature guard + null object | `/spec` disabled → paywall, never 404. Primitive provider down → mock mode returns fixture outputs. |
| Anti-corruption layer | Provider-specific response shapes mapped to `ChainStepResult` inside `agent_runtime/providers/`. |
| Always ORM | `ChainCall` and `ChainSignal` are SQLModel classes. User.builder/principles typed accessors. No raw SQL. |
| OpenAPI-first | `server/openapi/spec.yaml` and `server/openapi/user.yaml` are sources of truth. TS + Pydantic generated. |
| `data-test` selectors, TestBed, Page Objects | Every interactive element on `/spec` and `/onboarding` has `data-test`. Specs render real children. |

---

## Component Design

### Task 1: User model — builder + principles

**Purpose**: Persist the builder profile and accumulated principles per user, namespaced per feature.

**Components**:
- `server/migrations/versions/{rev}_add_builder_principles.py` — Alembic migration adding two JSONB columns.
- `server/modules/user/model.py` — `User` SQLModel gains `builder: Optional[BuilderProfile]` and `principles: Dict[str, Dict[str, Any]]`.
- `server/openapi/user.yaml` — updated response schemas, regenerated DTOs both sides.

**Patterns**: ORM, OpenAPI-first, namespaced JSONB to avoid future migrations.

### Task 2: Chain primitive (`agent_runtime`)

**Purpose**: One place where sequential AI chains execute. Every feature calls it; no feature re-implements orchestration.

**Components**:
- `server/agent_runtime/runner.py` — `run_chain(chain_def, user, input) -> AsyncIterator[ChainEvent]`.
- `server/agent_runtime/types.py` — `ChainDefinition`, `ChainStep`, `ChainEvent` (`step_start`, `step_complete`, `final_output`, `error`), `ChainStepResult`.
- `server/agent_runtime/context.py` — builds the per-step context: merges builder + principles (namespaced slice for the owning feature) + prior step outputs.
- `server/agent_runtime/providers/claude.py`, `providers/replicate.py`, `providers/mock.py` — strategy implementations behind a common `Provider` protocol.
- `server/agent_runtime/logging.py` — writes each call to `chain_call` (provider, model, tokens_in, tokens_out, latency_ms, cost_usd, generation_id).
- `server/agent_runtime/signals.py` — `capture_signal(generation_id, signal_type, payload)` writes to `chain_signal`. Aggregation deferred.
- `server/migrations/versions/{rev}_chain_tables.py` — Alembic migration for `chain_call` and `chain_signal`.
- `server/agent_runtime/tests/` — pytest suite using `providers/mock.py` fixtures.

**Patterns**: Strategy (providers), Observer (event stream), Anti-corruption layer (provider response mappers), Registry (provider lookup by name).

### Task 3: Spec module + chain definition

**Purpose**: Port Spec Doc's generation pipeline as a chain definition consumed by the primitive.

**Components**:
- `server/modules/spec/chain.py` — `SPEC_CHAIN: ChainDefinition` with steps `analysis`, `epic`, `architecture`, `tasks`. Each step references a prompt template and declares its input mapping from prior outputs.
- `server/modules/spec/prompts/` — one `.md` file per step, ported from Spec Doc's current prompts with minimal adaptation for the chain primitive's input shape.
- `server/modules/spec/routes.py` — Flask blueprint exposing `POST /api/spec/generate` (SSE) and `POST /api/spec/signal`. Each route ~30 lines; constructs input, calls `run_chain`, forwards events to the client.
- `server/openapi/spec.yaml` — endpoint definitions. DTOs generated both sides.
- `server/modules/spec/tests/` — route tests with primitive mocked; assertion targets event shape and feature-gate enforcement.

**Patterns**: Feature = bounded context, Adapter (route → primitive), OpenAPI-first.

### Task 4: Spec frontend route + SSE rendering

**Purpose**: Minimal UX — brain dump in, streamed spec files rendered progressively.

**Components**:
- `src/app/features/spec/spec.page.ts` — standalone, OnPush, signals for `input`, `files`, `status`.
- `src/app/features/spec/spec.page.spec.ts` — TestBed with Page Object, `data-test="spec-input"`, `data-test="spec-submit"`, `data-test="spec-file-{id}"`.
- `src/app/features/spec/spec.service.ts` — adapter; `generate(input: string): Observable<SpecEvent>` wrapping `EventSource`.
- `src/app/features/spec/spec.model.ts` — `SpecEvent`, `SpecFile` types generated from `server/openapi/spec.yaml`.
- `src/app/features/spec/spec.mock.ts` — fixture stream for mock mode.
- `src/app/app.routes.ts` — single-line entry: `{ path: 'spec', loadComponent: () => import(...) }`.
- Feature-registry entry guarded by `enabled_features.includes('spec')`.

**Patterns**: Standalone + OnPush + signals, Adapter, Feature guard with null object (paywall), `data-test` selectors.

### Task 5: Onboarding route + builder form

**Purpose**: Capture builder profile on first run, editable forever from settings.

**Components**:
- `src/app/features/onboarding/onboarding.page.ts` — standalone form, signals for field state.
- `src/app/features/onboarding/onboarding.page.spec.ts` — TestBed + Page Object, tests cover `validForm_submitsAndRedirects`, `skipButton_setsSkippedAtAndRedirects`, `existingBuilder_prefillsForm`.
- `src/app/features/onboarding/onboarding.service.ts` — `PUT /api/user/builder`.
- `src/app/app.routes.ts` — `/onboarding` lazy route.
- `src/app/shared/guards/onboarding.guard.ts` — redirects users with NULL builder and no `onboarding_skipped_at`.
- `server/modules/user/routes.py` — `PUT /api/user/builder` handler.

**Patterns**: Standalone + OnPush + signals, route guard, Adapter.

### Task 6: Photoshoot retrofit onto primitive

**Purpose**: Validate the primitive by making photoshoot consume it. Zero user-facing change.

**Components**:
- `server/modules/photoshoot/chain.py` — `PHOTOSHOOT_CHAIN: ChainDefinition` capturing the existing vision → prompt → inference pipeline as steps.
- `server/modules/photoshoot/service.py` — reduced to input construction + `run_chain` invocation + output mapping. Orchestration code deleted.
- `server/modules/photoshoot/tests/` — updated to mock the primitive instead of providers. End-to-end photoshoot test unchanged and passing.

**Patterns**: Feature = bounded context, Adapter, proof-by-duplication that the primitive is general.

---

## Execution Flow

```
[Phase 1: foundation]
   Task 1 (user model: builder + principles)
      │
      ▼
   Task 2 (chain primitive in agent_runtime)
      │
      ├───────────────┬───────────────┐
[Phase 2: parallel]   │               │
   Task 3 (spec)   Task 4 (spec UI) Task 5 (onboarding)
      │               │               │
      └───────────────┴───────────────┘
      │
[Phase 3: validation]
   Task 6 (photoshoot retrofit)
```

Request flow at runtime:

```
Client → POST /api/spec/generate (SSE)
       → Flask route (server/modules/spec/routes.py)
       → run_chain(SPEC_CHAIN, user, input)
           → context.build (merge user.builder + user.principles['spec'])
           → for step in chain:
               → provider.execute(prompt, context)
               → log to chain_call
               → yield ChainEvent(step_complete, output)
           → yield ChainEvent(final_output, files)
       ← SSE events → client renders progressively
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primitive location | `server/agent_runtime/` | Not a user-facing feature, has no route, genuinely cross-cutting. Signals future package extraction. |
| Streaming transport | SSE | One-way, stateless, matches Spec Doc today, nothing in Bubls needs bidirectional. |
| Chain definitions | Declarative data structures, not code | Adding a feature = define chain + prompts + UI. No new orchestration code. |
| Principles storage | Namespaced JSONB per feature | Costs nothing now, prevents a migration when feature three lands. |
| Onboarding UX | Dedicated `/onboarding` route with skip | Routable, returnable from settings, not dismissable by accident. |
| Photoshoot retrofit timing | Inside Epic 2 | Unvalidated abstraction until it runs two chains. Shipping one-chain primitive ships an abstraction of one. |
| Signal capture endpoint | Stub that persists; aggregation in Epic 3 | Schema in place, plumbing validated, aggregation when signal volume justifies it. |
| Provider interface | Strategy pattern behind `Provider` protocol | Swap Claude/Replicate/mock without touching chain logic. Mock mode is a first-class provider, not a test hack. |
| Per-call logging | `chain_call` table from day one | Cost tracking and debugging are load-bearing; retrofitting logging later is painful. |
| Spec UX | Textarea + submit + stream view, nothing more | No editor, no file tree — if `/spec` gets used, UX becomes a follow-up task with real signal. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
