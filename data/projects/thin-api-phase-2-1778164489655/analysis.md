# 🔍 Thin API Phase 2 — Analysis

## The Problem
Python currently holds AI logic that belongs in the skill layer. v2 redraws the line: Python is infrastructure (routing, stdout parsing, job lifecycle); skills are product (prompt, output schema, execution model). The 95%/N=10 benchmark gates are the trust mechanism that makes old route retirement safe — without a defined evaluator, the gates are theatre.

## Hard Constraints
- "Zero AI strings in Python" — skills own all AI behavior; Python never touches prompt content
- `execution_model` declared in `skill.json` — frontend and routes derive behavior from the registry, no hardcoding
- stdout protocol is the skill↔Python contract — exit code + structured JSON only
- 95% pass, N=10 per track gates route retirement — no cutover without it
- No Redis, no external queue — in-process state + threading.Lock only

## Open Questions
- **Skill output schema ownership**: If `brainstorm` adds a top-level key, does Python validate before responding or does the frontend break silently? Options: Python validates against `output_schema` in `skill.json` / frontend owns schema / no enforcement — this is the one place "domain logic in the skill" creates tight coupling back to Python/frontend
- **"95% pass" evaluator for prose**: Rewrite and brainstorm output is text, not structure. Who judges pass/fail on N=10? Options: LLM-as-judge with explicit rubric / human review / structural heuristics only — needs a decision before Track A gates are meaningful
- **Sub-agent blast radius**: No recursion limit, timeout hierarchy, or cost ceiling specified. One brainstorm call can fan out unboundedly. Options: Claude CLI 3600s timeout as implicit ceiling / explicit depth limit in `skill.json` / Python enforces max concurrent sub-agents
- **Rollback surface**: If a skill passes its gate then degrades on real inputs, is the old Python route still live? Options: parallel routes with feature flag / hard cutover / shadow mode with fallback — no documented path backward exists
- **Prompt change review**: A SKILL.md edit is a product change disguised as a docs edit. Options: CI runs benchmark diff on SKILL.md changes / honor system / PR label triggers manual re-run

## Dependencies & Sequencing
- **Track B blocks on Track A**: Generic route, `skill.json` schema, and `execution_model` branching must be proven first — a flaw discovered in Track A requires Track B unwind; the parallel framing is misleading
- **Frontend integration blocks on `skill.json` schema finality**: Registry-driven frontend behavior means schema churn equals frontend churn
- **Benchmark runner blocks on job log format**: Consuming real `.jobs/<job_id>/run.log` corpus requires log schema to be stable before the runner is built to consume it
- **`brainstorm` → `spec-pipeline` handoff is undesigned**: Brainstorm explicitly produces a `rewritten_braindump` "ready to feed spec-pipeline" but no trigger exists — frontend assembles this ad hoc unless a `suggested_action` field is stubbed into the output schema now

## Explicitly Out of Scope
- **Skill inspector endpoint** (`GET /skills/{name}/inspect`) — valid DX tool; re-scope when authoring friction is actually measured
- **`execution_model` extensibility beyond sync/async** — handler registry for streaming/interactive modes is speculative abstraction; add when a third mode is concrete
- **Trace ID propagation through sub-agents** — Phase 3 observability; don't build the tracer before the multi-agent skills exist
- **`brainstorm` → `spec-pipeline` as a designed two-step UX flow** — stub `suggested_action` in output schema and defer; designing the guided flow now inflates Phase 2
- **Skill diff CI tool** — correct end state; build the benchmark runner first, wire to CI in a follow-on