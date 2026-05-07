No file system access needed — all context is provided inline. Generating the document now.

---

# 🏗️ Solution Architecture: Thin API Phase 2

## Architecture Overview

The central claim of Phase 2 is a boundary redefinition: Python is infrastructure, not product. Today, every AI capability requires a Python route that knows what it does — a prompt string lives somewhere in Python, a sync/async branch is hardcoded in the handler, an output shape is an implicit assumption shared across the route, the frontend, and the skill. That coupling means any product change is a Python deploy. Phase 2 redraws this line permanently: the generic route reads a registry and executes a protocol; the skill registry carries all behavioral intelligence; Python never changes when product behavior changes.

Three structural components realize this. The **skill registry contract** (`skill.json` extended with `execution_model` and `output_schema`) is the single source of truth for all execution behavior — no per-skill conditionals exist anywhere in Python. The **generic route** is a single Flask handler that resolves a skill from the registry, derives branching from the registry fields, validates agent stdout against the declared schema, and returns a response — it never inspects the skill name to determine behavior. The **benchmark runner** is the trust mechanism that makes route retirement a governed decision rather than a gut call: it consumes real job logs, applies evaluators appropriate to each skill type, and produces a reproducible pass/fail verdict per track. The registry is the contract. The generic route is the executor. The benchmark runner is the confidence machine.

The migration is sequenced by architectural dependency, not by schedule preference. Track A (sync: rewrite, review) runs first and proves the generic route, the `skill.json` schema, and the output validator under real conditions before Track B (async: brainstorm, spec-pipeline) is introduced. This is not a conservative choice — it is the correct one. Track A and Track B share the route layer, the validator, and the schema contract. A flaw discovered in Track A's generic route execution model would require unwinding Track B work. The apparent parallelism in the task list is a scheduling target; the architectural sequencing is a dependency graph. The 95%/N=10 benchmark gate per track is what makes old route retirement safe: routes are not removed until the replacement has earned the trust, and that trust is demonstrated by a repeatable machine, not a one-time review.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | All AI calls remain in `modules/runtime/chain/adapter.py`; the generic route calls the adapter, never a provider directly; benchmark runner's LLM-as-judge evaluator also routes through the adapter |
| P2 — Thin HTTP Layer | The generic route validates input, reads the registry, delegates to a service module, and returns the response — no business logic inline; the output validator and job log writer are separate modules |
| P3 — Async 202 + Polling | `execution_model: async` skills return 202 immediately with job_id; sync skills return 200 with an `X-Job-Id` header — every invocation produces a corpus entry regardless of execution model |
| P4 — No Speculative Abstractions | `execution_model` supports sync and async only this phase; a handler registry pattern accommodates a future third mode additively without branching changes, but no third mode is designed speculatively |
| P5 — OpenAPI-First | The generic skill endpoint is declared in `openapi.yaml` before implementation; `output_schema` in `skill.json` is the skill-level contract and is not duplicated in the Python DTO layer |
| P6 — Skills First | Product intelligence lives exclusively in SKILL.md and skill.json; Python is the dumb executor; the max-plugin-use test (if swapping a skill for a plain prompt produces worse output, the skill is earning its complexity) is a policy, not a heuristic — it belongs in the skill review checklist and PR template |
| P7 — File Size & Structure | Generic route and service layer split at the 200-line boundary; output validator is a separate module; benchmark runner splits evaluator types into distinct modules |

## Component Design

### Skill Registry Contract

**Purpose**: Make `skill.json` the single source of truth for all execution behavior, eliminating per-skill conditionals from Python permanently and declaring the output contract that Python, the frontend, and the benchmark runner all depend on.

The registry contract extends `skill.json` with two fields. `execution_model` declares whether the skill runs synchronously (result returned in the response body) or asynchronously (202 + job_id, polled to completion). The generic route reads this field and branches accordingly — the word "brainstorm" or "rewrite" never appears in the route's conditional logic. `output_schema` declares the JSON Schema for the agent's stdout. This field is as load-bearing as `execution_model`: without it, the brainstorm skill's `questions`, `recommendations`, `rewritten_braindump`, and `suggested_action` structure is an implicit contract shared across the skill, Python, and Angular — a silent agreement that breaks silently when any party evolves. Declaring the schema in `skill.json` and enforcing it in Python closes this loop before it opens.

The `suggested_action` field in the brainstorm output schema is stubbed this phase. Its value may be null. Its presence in the declared schema is the architectural commitment: the frontend contract is declared now, not assembled ad hoc when the brainstorm → spec-pipeline flow is designed. This prevents the natural funnel between two skills from becoming a frontend hack — the slot exists in the contract, and the designed two-step flow fills it in a follow-on.

The max-plugin-use test applies at the skill.json level as well as the SKILL.md level: if a skill's `execution_model` and `output_schema` can be satisfied by a plain prompt with no sub-agent invocations, the skill is not earning its registered complexity. This test is a review artifact — it should appear on every skill PR, enforced by the PR template rather than by convention.

### Generic Route

**Purpose**: Replace four per-skill Python routes with a single handler that reads the registry and executes the protocol — zero per-skill conditional logic, zero natural-language strings in Python.

The generic route is the architectural keystone of Phase 2. It receives a skill name in the request, resolves the corresponding `skill.json` from the registry, and branches on `execution_model`. For sync skills, it calls the adapter and awaits the response synchronously. For async skills, it spawns a daemon thread, writes the initial job record to the in-process state dict, and returns 202 with the job_id immediately. In both cases, the route is skill-agnostic — it executes a protocol, not a named operation.

Between the adapter response and the HTTP response sits the output validator. It validates the agent's stdout against the skill's declared `output_schema` before any response is written. If validation fails, the route returns a structured skill error — the error surfaces at the skill boundary, not as corrupted data in the frontend. This is not defensive programming; it is the enforcement mechanism for the output contract. The validator is a separate module to maintain the 200-line boundary on the route and to make it independently testable.

The route also writes a run log entry for every invocation — sync and async alike — keyed by a generated job_id. Sync responses carry this job_id in an `X-Job-Id` response header. This is the observability primitive that doubles as the benchmark corpus seed: every real user invocation extends the test surface automatically, with no separate instrumentation required.

The "zero AI strings in Python" invariant is enforced mechanically, not by convention. A grep-based linter runs as a CI step against all Python files under `api/modules/ai/`. It fails the build if any file contains natural-language instruction strings above a calibrated character threshold. Convention drift is architecturally impossible if the build breaks on violation.

### Benchmark Runner

**Purpose**: Produce a reproducible, per-track pass/fail verdict that makes old route retirement a governed decision rather than a gut call — the confidence machine that makes the migration safe.

The runner consumes the `.jobs/<job_id>/run.log` corpus. This is the architectural payoff of writing `X-Job-Id` on sync responses: the corpus grows organically as the product is used, and benchmark quality improves without manual curation. A curated N=10 seed set initializes each track at migration time; real job logs extend it thereafter. The same input replayed against a new skill version produces a comparable verdict — corpus stability is what makes the benchmark reproducible.

Two evaluator types serve different skill profiles. The **structural evaluator** applies to async pipeline skills (brainstorm, spec-pipeline): it verifies that the output JSON contains the declared `output_schema` keys with the correct types — a deterministic, mechanical check that produces the same verdict on every run. The **LLM-as-judge evaluator** applies to sync prose skills (rewrite, review): it submits the agent's output alongside a reference output and an explicit rubric to the chain adapter, and interprets the judge's verdict. The rubric is a documented artifact — a versioned file checked into the repository — not an assumption embedded in runner code. A rubric change invalidates historical comparisons and must be treated as a benchmark reset, not a runner implementation detail.

Both evaluators produce a per-job pass/fail. The aggregate across the N=10 corpus is the track's pass rate. A track clears the 95% gate when the runner produces that verdict on a reproducible run — same corpus, same rubric, same result. This is the retirement trigger for the old route. The runner is also the primary tool for skill PR review: a SKILL.md change triggers a benchmark run against both the old and new skill version, and the diff is posted to the PR. Prompt changes are as reviewable as code changes.

### Migration Tracks

**Purpose**: Sequence the route retirement safely, prove the generic route before async complexity is introduced, and maintain a rollback surface throughout the transition.

Track A (sync: rewrite, review) runs in parallel with benchmark runner development. Its role is twofold: migrate two skills through the generic route, and validate that the generic route, `skill.json` schema, and output validator are correct under real conditions. Track A is the proof of concept for the architecture. Its benchmark gate is also the proof of concept for the runner.

Track B (async: brainstorm, spec-pipeline) begins only after Track A clears its 95%/N=10 gate. The sequencing is not conservative preference — it is a structural requirement. Track B shares the generic route, the output validator, and the `skill.json` schema with Track A. If Track A's execution_model branching logic contains a flaw, Track B inherits it. Deferring Track B until Track A is proven eliminates the rework risk.

Old routes remain alive and parallel to the generic route throughout the migration. This provides a concrete rollback surface: if a skill passes its benchmark, ships, and degrades on out-of-distribution real inputs, traffic can revert to the old route while the skill is corrected. The old routes are retired only after the gate is cleared and a production soak confirms the skill is stable under real usage. The duration of the soak is a deployment decision. The decision to retire is announced in the run log, not in a commit message.

Sub-agent invocations within skills (chain-agent, spec-backend, spec-frontend) carry an inherited blast radius risk: a single brainstorm invocation can fan out into multiple agent calls with no current bound on depth, compute time, or concurrent spawns. The architectural response this phase is the existing Claude CLI subprocess timeout (3600s) as the outer ceiling, and the 202 + polling pattern as the user-facing containment. A circuit breaker or cost ceiling is a Phase 3 concern — the multi-agent skills must exist in production before their failure modes are characterized well enough to bound.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Skill Registry | `skill.json` per skill directory | Co-located with the skill it describes; no separate registry service for a single consumer; schema is the contract, not a database row |
| Generic Route | Flask Blueprint, split route + service | Extends the existing thin HTTP layer pattern; Blueprint keeps the route file under 200 lines with the service split; no new framework surface |
| Output Validator | Python `jsonschema` library | Standard JSON Schema validation; synchronous, in-process; no external service; validates before any response write |
| Benchmark Runner | Standalone Python script consuming `.jobs/` | No new infrastructure; reuses existing job log format; structural and LLM-as-judge evaluators in one runner with two pluggable evaluator modules |
| LLM-as-judge Evaluator | Chain adapter (`modules/runtime/chain/adapter.py`) | Consistent with the P1 adapter boundary; rubric is a versioned file passed as context; no direct provider import in the runner |
| CI Grep Linter | Shell/Python script in CI pipeline | Zero dependencies; runs in any CI environment; calibrated threshold avoids false positives on short utility strings |
| Job Log Corpus | Existing `.jobs/<job_id>/run.log` format | No new storage format; sync jobs gain `X-Job-Id` header to extend corpus coverage; corpus grows organically with usage |
| Background Thread | `threading.Thread(daemon=True)` (existing pattern) | No Redis; no external queue; daemon flag ensures threads don't block server shutdown; matches the single-consumer deployment model |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| `execution_model` in `skill.json`, not Python | Eliminates per-skill conditionals from the route permanently; adding a new skill requires no Python change; the route is skill-agnostic by construction | Skill authors must understand the schema; a misconfigured `execution_model` produces wrong runtime behavior with no compile-time check — the output validator catches shape errors but not execution model misclassification |
| `output_schema` declared in `skill.json`, validated in Python before response write | Closes the silent contract-break loop; schema violations surface as skill errors at the boundary, not corrupted state in the frontend; makes the brainstorm output contract explicit and enforceable | Schema evolution requires coordinated updates to `skill.json`, the skill, and any frontend code that parses the output; schema changes must be treated as breaking changes and versioned accordingly |
| Benchmark runner consumes real job logs rather than synthetic inputs | Tests real user inputs; corpus grows organically with no curation overhead; replay against a new skill version produces a directly comparable verdict | Corpus quality depends on usage patterns; early benchmarks run on a thin corpus; a production soak of sufficient duration is required before the corpus is representative of the real input distribution |
| LLM-as-judge with an explicit, versioned rubric for prose skills | The only repeatable evaluator for prose output; rubric is a reviewable artifact, not an assumption embedded in runner code; makes "95% pass" mean the same thing on every run | The judge itself has variance — the same input can receive different verdicts across runs; the rubric must remain stable across benchmark runs; a rubric change constitutes a benchmark reset and invalidates historical pass rates |
| Track A (sync) proves generic route before Track B (async) begins | Validates the shared infrastructure before async complexity is introduced; a flaw in the execution_model branching or output validator is caught before Track B work is invested | Delays Track B start; the epic's parallel task framing is aspirational — architectural dependency constrains actual parallelism; Track B contributors must wait on Track A's gate |
| Old routes kept alive through benchmark gate and production soak | Provides a concrete rollback surface if a skill degrades on out-of-distribution inputs after passing the gate; retirement is a governed, reversible decision | Temporary code duplication; old routes must be kept passing tests and linting until retirement; the dual-route surface temporarily widens the codebase footprint |
| `suggested_action` stub in brainstorm output schema | Declares the frontend contract for the brainstorm → spec-pipeline handoff now; prevents ad hoc assembly of the two-step flow later; the field exists in the contract whether or not the skill populates it | Frontend must handle null gracefully; commits to a field name before the designed flow exists; a structural change to the field in a follow-on phase is a breaking schema change |
| Execution_model branching via handler registry, not if/else | A new execution model adds a handler entry, not a conditional branch; the route remains skill-agnostic even as execution models evolve | Minor indirection overhead; must be documented so skill authors understand the extension point; if a third mode never materializes, the registry is mildly over-designed relative to P4 |
| Max-plugin-use test codified as a PR policy, not a heuristic | Makes the skill complexity invariant mechanical; a skill that doesn't earn its sub-agent invocations is caught at review, not in production; mirrors the "zero AI strings in Python" invariant at the plugin layer | Requires calibration — what counts as "worse output" must be defined in the PR template, not left to reviewer judgment; adds review overhead to every skill change |
| `X-Job-Id` header on sync responses | Every sync invocation joins the benchmark corpus automatically; no separate instrumentation; corpus coverage extends to all skill types, not just async jobs | Clients must handle the header; adds a minor header to all sync responses regardless of whether the client uses it; the header exposes an internal job identifier on public responses |
| Skill SKILL.md change triggers benchmark re-run in CI | Prompt changes are as reviewable as code changes; the benchmark diff is posted to the PR; the architectural cleanliness of the skill layer is enforced by CI, not by discipline | CI benchmark runs add latency to skill PRs; the LLM-as-judge evaluator introduces non-determinism into the CI gate — a flaky judge verdict can block a valid skill change; flakiness threshold must be defined |

## Related Documents

- [Analysis](./analysis.md) – Problems driving this design
- [Epic](./epic.md) – Scope, tasks, and success criteria
- [Timeline](./timeline.md) – Status tracking