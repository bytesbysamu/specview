# 🏗️ Solution Architecture: Pipeline Self-Improvement

**Purpose**: Long-lived system design document.

**References**: Addresses issues in [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The pipeline today conflates two concerns that should be separate: the model's instruction space (what the prompt asks for) and the artefact's execution space (what the written file actually contains). Prompt rules are aspirational — they guide generation but cannot enforce outcomes. This system introduces a second enforcement layer that operates on the output text rather than the input instruction. The core shift is from discipline to contract: an artefact that passes the linter is correct by construction, not by review.

The system organises around a single new module, `modules/quality/`, housing two pure computation functions — the pre-emit linter and the multi-doc coherence pass — with no AI calls and no persistence. Purity is the architectural choice that makes the quality layer fast, independently testable, and safe to wire into the hot path of generation. Supporting the quality layer are two upstream changes: a contract parser in `task_gen/service.py` that gives the model accurate context about prior tasks, and an attribution injector in `implementation_guide/prompts.py` that eliminates the stale model-version leak. Together these four components close the loop identified in the analysis: the linter catches what slips through the prompt, the coherence pass catches what slips between documents, and the contract parser removes the structural cause of the cross-document drift.

A fifth component, the repair endpoint, is architecturally independent — it exists to apply the deterministic file generators retroactively to projects created before the linter and coherence pass existed. It shares no state with the quality module and requires no sequencing constraint.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Pure computation at the gate | `lint_task_guide` and `lint_capability` are stateless functions over text and paths. No DB reads, no AI calls, no side effects. This keeps them fast enough to block the write path and reliable enough to trust as gate signals. |
| Encode the bug class, not the instruction | Each lint rule targets a specific, historically-observed failure mode from the analysis. A rule is not "write good docs" — it is "text matching this regex at this position is a defect class that appeared in commit `729e5c1`." |
| Severity is structural, not configurable | Error versus warning is determined per-rule by whether the defect can corrupt downstream execution (error) or is a quality signal the author should resolve but can still ship around (warning). Making severity configurable would allow the gate to be bypassed, which defeats its purpose. |
| Contracts over context windows | Replacing 60-line truncation with structured contract extraction is a deliberate downscoping of the context problem. The model does not need the full prior task — it needs the declared file surface. Structured extraction gives the model exactly that, at a fraction of the token cost and with explicit semantics. |
| Environment-derived attribution | The executor model version is a fact about the runtime environment, not about the document being generated. Reading it from the environment at startup and injecting it as a named block prevents the model from hallucinating a version and makes the attribution auditable from outside the prompt. |

---

## System Boundaries

### What This System Includes

- `modules/quality/lint.py` — pre-emit linter, nine deterministic rules, consumed by `task_gen/service.py`
- `modules/quality/coherence.py` — multi-doc coherence pass, eight cross-document invariants, consumed by `POST /api/projects/<id>/coherence`
- Contract parser in `task_gen/service.py` — replaces the 60-line truncation; consumed by the impl-guide prompt builder
- Attribution injector in `implementation_guide/prompts.py` — `EXECUTOR_ATTRIBUTION` context block, consumed by `run_generation`
- `POST /api/projects/<id>/repair` — deterministic file repair for pre-linter projects

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Auto-retry / self-healing loop | Requires error-rate data to calibrate; a self-healing loop on an uncalibrated linter would regenerate valid documents. Deferred until false-positive rate is measured in production. |
| Persistent flag history and analytics | The linter's contract is to gate, not to dashboard. A persistent flag store requires a consumer that reads it; no such consumer exists in this epic. |
| Warning-severity auto-fixers | Auto-fix for trivial warnings (preamble strip, attribution rewrite) is attractive but requires knowing the failure-rate distribution before deciding which cases are safe to fix automatically. |
| Angular coherence badge | `POST /coherence` ships headless. The badge is a UI surface that belongs in a UI-focused follow-up once the endpoint has proven its flag quality. |
| Mid-generation coherence checking | The coherence pass requires a complete project directory to compare across documents. Partial state mid-generation does not satisfy that precondition. |
| Impl-guide prompt template wholesale rewrite | Only the attribution block and the prior-contracts block are added to the template. Any broader rewrite is a separate scope with separate risk. |

---

## Component Design

### Pre-emit Linter — `modules/quality/lint.py`

**Purpose**: Prevents defect classes from reaching disk by rejecting or flagging task guide text before `update_file()` writes it. Converts recurring hand-fix patterns into machine-checkable rules.

**Key Parts**:
- `Flag` — frozen dataclass carrying `rule`, `severity` (`"error"` or `"warning"`), `message`, and optional `line`. The immutable contract between the linter and its consumers.
- `lint_task_guide(text: str) -> list[Flag]` — the single entry point. Pure function; all nine rules run unconditionally and accumulate into the returned list. The caller decides what to do with the flags; the linter does not write, throw, or branch on severity.
- Nine rule implementations, each targeting one historically-observed defect class: hash-first structure, leaked thinking preambles, stale attribution, absolute test counts, personal filesystem paths, placeholder values, empty test bodies, section count, and `+K` test-claim consistency.

**Consumers**: `task_gen/service.py:run_generation` — wired immediately before the `update_file()` call. Any error-severity flag in the returned list causes the service to return a 502 with the flag list instead of writing. Warning-severity flags cause the file to be written with a `warnings` field added to the polling response.

**Patterns**: Gate pattern — the function runs to completion and returns a result; the caller enforces the policy. This separation means the linter can be tested exhaustively without simulating the write path.

---

### Multi-doc Coherence Pass — `modules/quality/coherence.py`

**Purpose**: Detects cross-document invariant violations that the per-document linter cannot see — path drift between sibling tasks, epic-to-file misalignment, architecture components with no producing task.

**Key Parts**:
- `lint_capability(project_dir: Path) -> list[Flag]` — reads all relevant markdown files in the project directory, runs eight invariants, returns a flat `list[Flag]` using the same `Flag` type as the pre-emit linter. The shared type is intentional: both functions are quality gates over text, and sharing the flag shape keeps the endpoint layer uniform.
- Eight invariants covering: symbol uniqueness across file tables (no path is `(new)` in two tasks), cross-task import-path consistency, epic task-table-to-filename alignment, `spec-index.md` accuracy, `timeline.md`-to-epic backlog alignment, architecture-component-to-task coverage, pre-flight cross-task symbol dependency validity, and content-routing (status terms only in `timeline.md`).

**Consumers**: `POST /api/projects/<id>/coherence` — returns `{flags, summary}`. Angular will surface unresolved flags as a project-card badge in a follow-up epic; in this epic the endpoint ships headless.

**Patterns**: Post-pass pattern — runs against a completed project directory, not against in-flight generation state. This avoids the partial-state problem that makes mid-generation coherence impractical. Invariants #1 and #7 will surface residual drift until the contract parser (Task 1) lands; that is expected and does not indicate a design flaw.

---

### Prior-Task Contract Parser — `task_gen/service.py`

**Purpose**: Replaces the 60-line truncation that prevents downstream tasks from seeing what prior tasks declared as new files. The truncation is the structural cause of the cross-task path drift documented in the analysis.

**Key Parts**:
- `collect_prior_task_contracts(project_dir: Path, current_task_num: str) -> dict` — iterates prior task docs in order, parses each for declared file surfaces, and returns a structured dict keyed by task number.
- `_parse_task_contract(text: str) -> dict` — extracts `creates`, `modifies`, and `exports` from §3 (Files) and any exports block. Operates on the document structure, not on raw line counts.
- Injected into the impl-guide prompt as a `PRIOR-TASK CONTRACTS` block — a named section the model can reference when declaring its own file surfaces. The block explicitly labels prior-task files as not to be re-created, giving the model the invariant as a positive instruction rather than a negative constraint.

**Consumers**: `task_gen/service.py:run_generation` — the contract dict is assembled before the prompt is built and passed into the prompt builder alongside the task spec.

**Patterns**: Structured extraction over raw truncation. The 60-line limit was an approximation of "give the model some context"; the contract parser gives the model exactly the context it needs — the file surface — without the noise of implementation detail or the risk of cutting off at an arbitrary boundary.

---

### Executor Attribution Injector — `implementation_guide/prompts.py`

**Purpose**: Eliminates the stale `Co-Authored-By: Claude Sonnet 4.6` leak by making the current executor model version an environment-derived fact injected into every impl-guide prompt, rather than something the model invents.

**Key Parts**:
- `EXECUTOR_ATTRIBUTION` dict — read from the environment at module import time (`CLAUDE_CODE_MODEL` env var, defaulting to the current production model). Contains the full co-author trailer line as a verbatim string.
- Hard rule added to `_USER_HEADER` — instructs the model to copy the attribution value verbatim from the `EXECUTOR ATTRIBUTION` block and never to invent a model version. This is the instructional layer; lint rule #3 is the enforcement layer.

**Consumers**: `run_generation` in `task_gen/service.py` — the attribution block is injected into the prompt template before the AI call. Lint rule #3 in `modules/quality/lint.py` acts as the post-generation safety net, flagging any co-author line that does not match the injected value.

**Patterns**: Environment injection at module load, not per-request. The version is a deployment-time fact; reading it once at startup is both correct (it cannot change mid-run) and efficient (no per-request env lookup).

---

### Project Repair Endpoint — `POST /api/projects/<id>/repair`

**Purpose**: Retroactively applies deterministic file generators to projects created before the linter and coherence pass existed and therefore missing `spec-index.md`, `timeline.md`, or `README.md`.

**Key Parts**:
- Route handler in the projects blueprint — checks project existence, iterates the three target filenames, writes any that are absent using the existing deterministic generators (`generate_spec_index`, `generate_timeline`, `generate_readme`), returns `{repaired: [...]}`.
- Idempotency by file-existence check — running repair twice on the same project produces the same result; files present on the first run are not overwritten on the second.

**Consumers**: Direct HTTP call from the Angular project view (or from a developer's curl) for any project displaying coherence flags that stem from missing structural files.

**Patterns**: Deterministic-only repair — no AI generation call. The generators are already used by `bootstrap_project`; this endpoint exposes them as an idempotent retroactive operation. Auth requirements are an open question carried from the analysis; the implementation guide must confirm whether project ownership check is required.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Quality module | Pure Python, stdlib only | The linter and coherence pass are regex and file-path logic. No external dependencies means no version drift, no test setup overhead, and no risk of the quality gate itself introducing failures. |
| Flag type | Frozen dataclass | Immutable, hashable, printable without custom logic. Both the linter and the coherence pass return the same type, keeping the endpoint layer uniform. |
| Contract parser | Python `re` + markdown structural conventions | The task doc format is stable (§3 is always Files, §5 is always Tests). Structural parsing by section heading is more robust than line-count truncation and more maintainable than a full markdown AST parser. |
| Repair generators | Existing `generate_spec_index`, `generate_timeline`, `generate_readme` | Already used by `bootstrap_project`. Reuse avoids duplication and ensures the repair output matches what a freshly bootstrapped project would produce. |
| AI calls | Existing `modules/chain/adapter.py` | All AI calls in this epic go through the existing adapter boundary. The quality module introduces no new AI surface. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Linter is a pure function, not a service class | Stateless functions are easier to test, easier to reason about, and cannot accumulate surprising state between calls. The linter has no reason to be stateful. | Cannot cache compiled regexes across calls as instance variables — mitigated by module-level regex compilation, which achieves the same result. |
| Error severity blocks the write; warning severity does not | The error/warning split lets the system distinguish defects that corrupt downstream execution (personal paths in a spec shipped to an executor, empty test bodies, leaked thinking preambles) from quality signals that inform but do not invalidate (stale attribution, absolute test counts). A binary block-or-pass design would either block too much or not enough. | The severity classification is per-rule and fixed, which means changing a rule's severity requires a code change and a review. This is a feature: severity changes need deliberate justification, not a configuration toggle. |
| Coherence pass runs post-task, not mid-generation | The coherence invariants require comparing across the full set of task documents. Mid-generation, prior tasks are complete but the current task is not; the comparison would produce false positives on invariants that depend on the current task's file declarations. Post-task is the earliest point where the full document set is coherent. | Errors caught post-task require a regeneration of the task that produced the drift, rather than blocking before it is written. The pre-emit linter handles per-document defects; the coherence pass handles cross-document drift. They are complementary, not redundant. |
| Structured contract extraction replaces raw truncation | The 60-line limit was a proxy for "enough context." The contract parser gives the model exactly the context that prevents drift — declared file surfaces — without the noise of the full task body. A smaller, more structured context block is more reliable than a larger, less structured one. | The parser depends on the task doc's section structure being stable. A section-numbering change in the impl-guide template would break the parser. This dependency is explicit and documented as a coordination requirement. |
| Attribution is environment-derived, not prompt-instructed | A prompt instruction ("use Opus 4.7") is a request the model may or may not follow. An environment-derived block with a hard rule is a fact the model copies verbatim. The lint rule is the enforcement backstop. The three-layer design (env → prompt → lint) means the attribution leak requires a failure at all three layers simultaneously. | Adds a startup-time environment dependency. If `CLAUDE_CODE_MODEL` is not set, the system defaults to the current production model name. The default must be kept current with deployments — documented as an operational requirement. |
| Repair endpoint uses deterministic generators only | The repair endpoint exists to produce structural files that should have been created at project bootstrap. Those files have deterministic content given the project metadata. Using AI generation would introduce variability and latency for a task that does not require creativity. | Deterministic generators produce files that may not reflect the actual project's current state as well as an AI-generated equivalent would. Acceptable trade-off: the goal is structural completeness for the coherence pass, not prose quality. |

---

## Execution Flow

```
[Task Generation Path]
  run_generation called
    → collect_prior_task_contracts (contract parser)
    → build impl-guide prompt with PRIOR-TASK CONTRACTS + EXECUTOR ATTRIBUTION blocks
    → AI call via chain/adapter.py
    → lint_task_guide(generated_text)
         → error flags present? → return 502 with flag list (no write)
         → warning flags only?  → update_file() + include warnings in polling response
         → no flags?            → update_file()

[Coherence Check Path]
  POST /api/projects/<id>/coherence
    → resolve project_dir
    → lint_capability(project_dir)
    → return {flags, summary}

[Repair Path]
  POST /api/projects/<id>/repair
    → for each of [spec-index.md, timeline.md, README.md]
         → if absent: generate deterministically and write
    → return {repaired: [...]}
```

---

## Module Topology

`modules/quality/` is a new module with no inbound imports from other modules — it is a terminal leaf in the dependency graph. `task_gen/service.py` imports `lint_task_guide` from it; the coherence route imports `lint_capability` from it. Neither the AI adapter nor the context loader imports from it. This topology ensures that adding or modifying lint rules cannot introduce circular dependencies and that the quality module can be tested without any application infrastructure.

The `Flag` dataclass is defined in `modules/quality/lint.py` and imported by `modules/quality/coherence.py`. Both modules return the same type to their callers. This is a deliberate shared contract: the endpoint layer can treat both flag sources uniformly without type-switching.

---

## Open Questions

These are unresolved decisions that implementation guides must address before coding begins:

1. **Repair endpoint auth** — the analysis notes that auth requirements are unconfirmed. The endpoint modifies project files; it should require at minimum the same project-ownership check as `POST /coherence`. The implementation guide must confirm this before the route is wired.

2. **Lint rule #8 section-count coordination** — the rule hardcodes 10 numbered sections matching the current impl-guide template. Any future change to the template's section count must be coordinated with this rule. The implementation guide should document this as an explicit coupling and propose a mechanism (a named constant shared between the prompt template and the lint rule) to make the coupling visible at the call site.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview