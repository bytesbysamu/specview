---
sidebar_position: 2
---

# 🎯 Spec Route + Chain Primitive – Epic

**Purpose**: Port Spec Doc's brain-dump-to-spec pipeline into Bubls as `/spec`, extract a shared chain primitive that photoshoot and spec both consume, and add the builder/principles user model that every future AI feature reads from.

**Source Analysis**: See [Analysis](./analysis.md) for problem framing, constraints, and unresolved questions.

---

## Business Value

Epic 1 proved Bubls can host one AI feature. Epic 2 proves it can host many without duplicating orchestration. That transition — from "app with a feature" to "runtime for features" — is the architectural inflection that determines whether adding feature five costs a week or costs three days.

Spec is the right second capability because its chain is structurally different from photoshoot's (long-form streaming text vs. single-shot image generation), so porting it surfaces whatever the primitive actually needs rather than the subset photoshoot would have revealed alone. It is also the ultimate dogfood moment: Bubls now contains Spec Doc, which means future Bubls features get spec'd from inside Bubls.

The value proposition: ship a second AI feature *and* the infrastructure so feature three is chain-definition + prompts + minimal UI, nothing more. That plus the onboarding form — visible, user-facing — keeps the epic from being invisible infrastructure work.

---

## Scope

### What This Epic Covers

- Alembic migration adding `builder` and `principles` JSONB columns to `superapp_users`, plus SQLModel updates.
- Chain primitive in `server/agent_runtime/` exposing `run_chain(chain_def, user, input)` streaming events and `capture_signal(generation_id, signal_type, payload)`.
- Unit tests for the primitive using a mock AI provider (no real API calls in CI).
- Per-call logging to a `chain_call` table for cost tracking and debugging.
- `server/modules/spec/` — chain definition (analysis → epic → architecture → tasks), prompts, OpenAPI YAML, Flask routes, feature-gate middleware.
- Angular `/spec` route — standalone component, textarea, submit button, SSE rendering of streamed files. Feature-registry entry, tab icon.
- Angular `/onboarding` route — builder form, `PUT /api/user/builder`, "skip for now" escape hatch. Return accessible from settings.
- Photoshoot retrofit — refactored to call `run_chain` internally with the same prompts, same inputs, same outputs. Zero user-facing change.

### What This Epic Does NOT Cover

- ❌ Signal aggregation into principles updates (Epic 3 — correction loop).
- ❌ `/spec` UX beyond textarea + submit + stream view (no markdown editor, no file tree, no multi-panel layout).
- ❌ Migrating existing Spec Doc projects into Bubls.
- ❌ Bringing the Plate editor or principles editor inside Bubls.
- ❌ Publishing the chain primitive as an external package.
- ❌ Any user-visible change to photoshoot.
- ❌ Real-time collaborative editing, multi-user spec sessions, public sharing.

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **User model: builder + principles** | None | — | 1 day | High |
| 2 | **Chain primitive (`agent_runtime`)** | 1 | — | 3 days | High |
| 3 | **Spec module + chain definition** | 2 | 4, 5 | 2 days | High |
| 4 | **Spec frontend route + SSE rendering** | 2 | 3, 5 | 2 days | High |
| 5 | **Onboarding route + builder form** | 1 | 3, 4 | 1 day | Medium |
| 6 | **Photoshoot retrofit onto primitive** | 2 | — | 1 day | Medium |
| 7 | **/text route + text operations UI** | 2 | 6 | 1 day | High |

### Task Details

#### Task 1: User model — builder + principles
Alembic migration adding `builder JSONB NULL` and `principles JSONB NOT NULL DEFAULT '{}'::jsonb` to `superapp_users`. Update `User` SQLModel with typed accessors. Namespaced principles shape: `{photoshoot: {...}, spec: {...}}`. No data backfill — existing users get NULL builder, empty principles. OpenAPI schema updated for `GET /api/user/me` to include both fields.

#### Task 2: Chain primitive
Build `server/agent_runtime/` with `run_chain(chain_def, user, input) -> AsyncIterator[ChainEvent]` and `capture_signal(generation_id, signal_type, payload)`. Chain definitions are declarative: list of `ChainStep(id, provider, prompt_template, input_map, output_schema)`. Primitive handles builder/principles injection into every step's context, sequential execution with forward output mapping, retry with exponential backoff, per-call logging to `chain_call` table, SSE-compatible event streaming. Mock provider for tests. `capture_signal` writes to `chain_signal` table; aggregation deferred to Epic 3.

#### Task 3: Spec module + chain definition
`server/modules/spec/` — chain config wiring analysis → epic → architecture → tasks with prompts ported from Spec Doc, OpenAPI YAML (`POST /api/spec/generate` SSE, `POST /api/spec/signal`), Flask route that calls `run_chain`, feature-gate middleware entry. Prompts copied from `specs/` and `src/app/services/ai.service.ts` with adaptation for the chain primitive's input shape.

#### Task 4: Spec frontend route
Angular standalone `/spec` component — textarea for brain dump, submit button, progressive render of streamed files as SSE events arrive. `SpecService` adapter calling `POST /api/spec/generate`. Feature-registry entry, tab icon, route lazy-loaded. TestBed spec with Page Object, `data-test` selectors, mock streaming service.

#### Task 5: Onboarding route + builder form
Angular `/onboarding` route with builder form (name, stack preferences, style, goals, working-style context). `PUT /api/user/builder` persists. Route guard redirects first-run users with NULL builder. "Skip for now" escape hatch sets a `onboarding_skipped_at` timestamp so nagging can resume later. Return path from settings page.

#### Task 6: Photoshoot retrofit
Refactor `server/modules/photoshoot/service.py` to define its chain as a `ChainDefinition` and execute via `run_chain`. Prompts and outputs unchanged. Tests updated to mock the primitive instead of the underlying providers. Commit message: `refactor(photoshoot): run via chain primitive`. Zero user-facing change verified by existing end-to-end photoshoot test.

**Port budget**: ~100 LOC of changes; no new modules; no new tables; zero user-facing change.

#### Task 7: /text route + text operations UI
Ship a user-facing `/text` tab in Bubls with textarea + 5 rewrite mode buttons (Humanize, Expand, Compress, Clarify, Formalize) + Generate. Two endpoints: `POST /api/text/rewrite {text, mode}` and `POST /api/text/generate {prompt}`. Both flow through `chain.adapter.generate(...)` — the text module never imports from `chain.providers.*` directly; enforced by a structural test mirroring Task 2's. Prompt sources: port `humanize-me/backend/app.py:65` (REWRITE_PROMPT, single-pass) for the `humanize` mode; write the other four modes fresh as one-liners in `server/modules/text/prompts.py`. Persistence: extend `superapp_generations` with a nullable `feature` column ("photoshoot" | "text") and nullable `input_text`; make `result_image_url` nullable. One unified generations table, not two. Feature-gate is opt-in — no mass migration of `enabled_features` defaults. Frontend: standalone OnPush Angular page at `src/app/pages/text/` with `data-test` selectors, `TextApiService` passing the bearer token, TestBed spec covering happy paths + error toast + empty-textarea disabled state. Reference shape for Task 6's retrofit — if `/text`'s module and the retrofit converge differently, one is wrong.

**Port budget**: ~250 LOC backend (module + migration + 1 Alembic + 2 endpoints + 5 prompts) + ~200 LOC frontend (page + service + spec); 0 new tables (extension migration only); 1 structural test; 5 new feature-level tests minimum.

---

## Success Criteria

- ✅ New user signs in → lands on `/onboarding` → fills builder form → lands on home. Form is returnable from settings.
- ✅ User taps Spec tab, pastes brain dump, watches analysis → epic → architecture → tasks stream progressively. Output quality matches Spec Doc on a held-out brain dump (no regression on rubric scoring).
- ✅ Photoshoot still works end-to-end, now running through the chain primitive. Existing photoshoot tests pass unchanged.
- ✅ A hypothetical third AI feature requires only: chain definition, prompts, minimal UI. Reviewed by reading `server/modules/spec/` and `server/modules/photoshoot/` side-by-side — no orchestration code in either.
- ✅ TestFlight build ships with `/spec` route and `/onboarding` form gated by feature-registry.
- ✅ `chain_call` table logs every model call with tokens-in, tokens-out, latency, cost estimate.
- ✅ Retention signal: ≥1 unprompted return to `/spec` within 7 days of first use among internal testers.

---

## Non-Goals

- ❌ Correction loop that updates principles from captured signals (Epic 3).
- ❌ Markdown editor, file tree, or multi-panel layout on `/spec`.
- ❌ Importing existing Spec Doc projects.
- ❌ Extracting the chain primitive to a separate package.
- ❌ Any change to photoshoot's UX or output.

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
