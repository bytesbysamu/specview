# 🎯 Epic: Thin API Phase 2

## Business Value

Every AI capability in spec-doc today requires a Python route that knows what it's doing — a prompt string lives somewhere in Python, a branching condition gates async vs sync, a shape assumption about the output is buried in a handler. That coupling means adding or changing any AI feature is a Python deploy, not a skill edit. For a solo founder iterating on product behavior daily, that tax compounds: the architecture is rate-limiting the product. Phase 2 redraws the line permanently — Python becomes dumb infrastructure that reads a registry and executes a protocol; skills become the entire product layer, owned and iterated in isolation.

The benchmark gate mechanism (95% pass, N=10 per track) is the business-critical piece that makes this migration safe enough to ship. Without a defined evaluator and a reproducible runner, "the skill works" is a gut call. With it, route retirement becomes a governed decision — old infrastructure is only removed when the new layer has earned the trust. That confidence machine is what allows a solo developer to migrate production AI behavior without a QA team or a rollback army.

The brainstorm skill's output schema — `questions`, `recommendations`, `rewritten_braindump` — is the first instance of spec-doc acting as an active collaborator rather than a passive validator. The `suggested_action` field stubs the natural funnel into `spec-pipeline`, positioning the product toward guided AI-assisted project creation. That interaction model is the product differentiator: not an API that answers questions, but a tool that thinks alongside the user and proposes the next step.

## Scope

### What This Epic Covers

- **Skill registry contract** — `skill.json` schema extended with `execution_model` and `output_schema` fields; the generic route reads both and derives all branching behavior from the registry, eliminating per-skill conditionals in Python
- **Output schema enforcement** — Python validates agent stdout against the declared `output_schema` before writing any response; schema violations surface as skill errors, not silent frontend breakage
- **Benchmark runner** — consumes real `.jobs/<job_id>/run.log` corpus; evaluates structural skills on file shape and sync/prose skills via LLM-as-judge with an explicit rubric; produces a reproducible pass/fail result per track
- **Track A sync migration** — rewrite and review skills migrated through the generic route; old Python routes retired only after 95%/N=10 benchmark gate is cleared
- **Track B async migration** — brainstorm and spec-pipeline skills migrated through the generic route; brainstorm output schema includes a stubbed `suggested_action` field as the handoff hook to spec-pipeline; same 95%/N=10 gate applies before retirement

### What This Epic Does NOT Cover

- ❌ **Skill inspector endpoint** (`GET /skills/{name}/inspect`) — valid developer experience tool; re-scope when authoring friction is actually measured
- ❌ **`execution_model` extensibility beyond sync/async** — handler registry for streaming or interactive modes is a speculative abstraction; add when a third concrete mode exists
- ❌ **Trace ID propagation through sub-agents** — Phase 3 observability; the multi-agent skills must exist before the tracer is built
- ❌ **Brainstorm → spec-pipeline as a designed two-step UX flow** — `suggested_action` is stubbed in the output schema this phase; the guided frontend flow is a follow-on
- ❌ **Skill diff CI tool** — correct end state; build the benchmark runner first, wire benchmark diffs to CI in a follow-on

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Skill Registry Contract** — extend `skill.json` with `execution_model` and `output_schema`; generic route reads both; Python validates stdout against declared schema before responding; zero AI strings in Python enforced as the acceptance bar | None | — | 2 days | High |
| 2 | **Benchmark Runner** — runner consumes `.jobs/<job_id>/run.log` corpus; structural evaluator for file-shape skills; LLM-as-judge evaluator (with explicit rubric, not assumption) for prose/sync skills; produces per-track pass rate against N=10 | Task 1 | Yes (with 3) | 2 days | High |
| 3 | **Track A Sync Migration** — rewrite and review skills migrated through generic route; run against benchmark runner; old Python routes retired only after 95% gate is cleared | Task 1 | Yes (with 2) | 2 days | High |
| 4 | **Track B Async Migration** — brainstorm and spec-pipeline migrated through generic route; brainstorm `output_schema` includes `suggested_action` stub; 95%/N=10 gate required; old routes retired after gate clears | Tasks 2, 3 | — | 3 days | High |

## Success Criteria

- ✅ Zero natural-language instruction strings exist in any Python file under `api/modules/ai/` — verifiable by grep
- ✅ Generic route handles all four skills (rewrite, review, brainstorm, spec-pipeline) with no per-skill conditional logic in Python
- ✅ `skill.json` `output_schema` field is declared for all four skills and Python rejects malformed stdout before any response is written
- ✅ Benchmark runner produces a reproducible pass/fail result for a given skill version against the `.jobs` corpus — same input, same verdict on re-run
- ✅ Track A skills (rewrite, review) clear 95%/N=10 benchmark gate before old routes are retired
- ✅ Track B skills (brainstorm, spec-pipeline) clear 95%/N=10 benchmark gate before old routes are retired
- ✅ Brainstorm output schema includes `suggested_action` field (may be `null`; frontend contract is declared, not assembled ad hoc)
- ✅ LLM-as-judge evaluator rubric is a documented artifact, not an implicit assumption embedded in runner code

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking