# Braindump: spec-doc-legacy

## What it is

The original spec-doc: a document-first AI editor and spec generation pipeline. Users paste a braindump; an AI chain generates analysis, epic, architecture, timeline, and implementation guides. Also includes a task-spec generator (`regen-task.mjs`) that assembles a ~60–70K char prompt from 7 context blocks and produces a 10-section executor-ready implementation guide. The tool is designed to eat its own dog food — spec-doc specifies itself.

Stack: Angular 19 + Monaco Editor (browser UI) + Express API (port 3100, now being retired in favor of Flask at 3101) + Claude CLI for AI. No database; projects are folders of markdown files on disk.

## The problem it solves

AI code generation without structured specs produces inconsistent output and executor confusion. Spec-doc makes the spec the source of truth — braindump in, structured spec set out, executor guides generated from the spec, deviations logged in commit bodies. The 10-section Executor Protocol (Context, Pre-flight, Files, Steps, Tests, Commit Plan, Verification, Rollback, Deviations Allowed, Out of Scope) is the contract between the generator and any AI executor. The flywheel: braindump → specs → code → product → feedback → update specs.

## Current state

Feature-complete for the core pipeline (bootstrap, task-spec gen, quality gate, lint-braindump, codebase scan). Flask port of the Express API is complete and hardened. 270+ backend tests. Part A of the codebase context injection task shipped (Scan endpoint, codebase.md injection into prompts, codebase editor modal). Parts B (Refine) and C (integration) not yet started. Express is being retired; Flask at port 3101 is the new backend. CLAUDE.md Quick Start still references `:3100` — stale, needs updating before any external user touches the repo.

## Key decisions made

- **Prompts are code** — system prompts are versioned, tested against quality rubrics, iterated from executor deviation logs. The 10-section template is embedded in `ImplementationGuideService` and is the quality gate.
- **File-driven persistence** — projects are folders of markdown. No database, no ORM, no migrations. Git-friendly, grep-friendly.
- **Five context blocks** — builder, principles, codebase, references, prior-tasks. Each injected as a labeled markdown section so the LLM attributes constraints. Codebase.md capped at 250 lines by scanner.
- **Structural tests over behavioral** — source-contract tests grep actual source files for architectural invariants ("prompt template contains all 10 section headers", "adapter boundary not violated"). One grep + one assertion + one failure message per test.
- **Adapter pattern for AI providers** — CLI, remote, mock — same prompt logic, swappable execution. Tests run with mock provider.
- **Judgment-calls-per-commit is the spec quality metric** — target 0–3 per commit. Count `Deviations:` lines in commit bodies to measure spec calibration.
- **Not-yet-built is the right state** — infrastructure without a current consumer is speculative debt. Task 2 deferred ChainDefinition types, retry machinery, SSE event unions — none missed.
- **Pipeline V3 direction** — executor writes the task spec as Step 0, then executes it. No separate `regen-task.mjs` call. One agent, one pass: plan → execute → document. Still in braindump phase.
- **Flask hardening completed** — DTOs generated (not committed), Pydantic at route boundary, ServiceError + errorhandler, structural tests expanded, Makefile + CI workflow, config validated at startup.
- **SDK over CLI in prod** — `CHAIN_PROVIDER=claude` (SDK) is the production default; CLI is the no-API-key fallback.

## Open questions

- **Launch interpretation** — SaaS (auth + trial + billing) vs. self-hosted dev tool vs. open-source library. The next-iteration braindump assumes SaaS (freemium) but needs a one-sentence call from the user before it becomes an epic.
- **Monetization model** — freemium (5 projects free, $5/month unlimited) vs. pay-per-spec vs. team plan. Decision gates the trial length, success metrics, and monetization context editor fields.
- **Self-spec retrofit** — spec-doc's own docs don't follow the hierarchy it enforces on others. 35+ scattered markdown files with no entry point. Open question: which capabilities to carve (project management, AI text ops, spec bootstrapping, task-spec gen, quality gating, codebase scanning)?
- **Pipeline V3** — executor plans then executes in one pass. Needs the new executor prompt template written; decision on whether the plan step should be interruptible.

## Next steps

- Decide launch interpretation (SaaS / self-hosted / open-source) before the next-iteration braindump becomes an epic.
- Pick monetization model (freemium assumed).
- Ship Parts B (Refine endpoint: generic guide → executor-ready TASK.md with real paths) and C (integration, system-prompts.md update, principles.md pipeline section) of the codebase context injection task.
- Update CLAUDE.md Quick Start from `:3100` to `:3101` before any external user opens the repo.
- Port self-spec: retrofit spec-doc's own docs into the capability folder hierarchy it generates for others (Analysis, Epic, Architecture, Timeline, Implementation Guides).
- Run the launch POC epic: backend auth (magic-link, users table in Neon), frontend auth UI, monetization context editor, billing events + trial logic, project export endpoint, landing page + tracking.
