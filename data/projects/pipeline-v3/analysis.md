---
sidebar_position: 1
---

# Pipeline V3 — Analysis

**Purpose**: Identify the problems driving the merge of plan generation and execution.

**Date**: 2026-04-17

---

## Problem

The `regen-task.mjs` generation step burns 60K tokens per task, takes 3–5 minutes, and fails ~50% on first attempt via the CLI provider. A 20-task epic costs 1.2M tokens and 60–100 minutes just to produce plans — before a single line of code ships. The generated plans are consumed by an executor agent that must re-read the same codebase context, re-audit the same git state, and re-evaluate the same architecture trade-offs. The generation output is a lossy intermediary: it captures what the generator *thinks* the executor will need, not what the executor *actually* needs once it sees the workspace. Executors that skipped task specs entirely and worked from epics directly produced equally good code — the empirical signal that the separate generation step adds cost without proportional value.

---

## Hard Constraints

| Constraint | Source | Implication |
|-----------|--------|-------------|
| 10-section task format is the contract | Executor Protocol (principles.md) | V3 must produce the same format — written by the executor, not a separate generator |
| `deviation-report.mjs` parses commit bodies | Pipeline V2 | Commit body format (`Deviation: <category> -- <desc>`) must not change |
| Task files live in project folder, appear in sidebar | Spec Doc UX | Output path (`projects/{id}/task-N-{slug}.v2.md`) must not change |
| Context files are global | regen-task.mjs lines 627–688 | V3 must inject the same 5 context blocks (builder, principles, codebase, references, caveats); extract into shared module |
| CLI provider has ~50% first-attempt failure rate | Observed in 100-task generation session | V3 doesn't fix CLI reliability, but cuts LLM calls per task from 2+ (generate + execute) to 1 |

---

## Open Questions

| Question | Options | Recommendation |
|----------|---------|----------------|
| Should the plan step be interruptible? | Continuous (default) vs `--review-first` flag | Continuous by default. Interruptibility requires session state management; defer until someone asks |
| What happens to regen-task.mjs? | Delete, deprecate, or keep for V2 projects | Keep as-is for existing V2 projects. V3 bypasses it entirely. No migration needed |
| Should the executor's plan be auto-reviewed? | Post-plan review before execution vs skip | Skip. The executor reviews its own plan by executing it. Post-execution signal is the deviation report |
| Where does context loading live? | regen-task.mjs (current, inline), server.js, or shared module | Shared module (`scripts/context-loader.mjs`). Both regen-task.mjs and `/api/ai/implement` import from it |
| Does V3 need `--rescan`? | Inherit from regen-task.mjs or always rescan | Inherit. The executor's pre-flight phase audits codebase freshness — if stale, rescan before planning |

---

## Dependencies

| Dependency | Status | Impact |
|-----------|--------|--------|
| `/api/ai/implement` endpoint (server.js:1313) | Exists, bare-bones prompt | Must be upgraded with rich context injection and V3 prompt template |
| `regen-task.mjs` context loading (lines 627–688) | Exists, inline in script | Must be extracted into `scripts/context-loader.mjs` so server.js can reuse |
| `buildImplementationGuidePrompt()` (regen-task.mjs:350) | Exists, 195-line prompt | V3 prompt reuses the 10-section template but wraps it in plan→execute→update instructions |
| `deviation-report.mjs` | Exists, 207 lines | No changes — V3 commits use the same `Deviation:` line format in commit bodies |
| Claude CLI (`claude -p --output-format text`) | Available | V3 prompt is longer (plan-write + execute instructions), but total tokens per task drop from ~120K (generate + execute) to ~60K (one pass) |

---

## Explicitly Out of Scope

- **Container execution mode** — already wired in `/api/ai/implement`; V3 changes the prompt, not the execution substrate
- **Parallel task execution** — V2's `--all --parallel N` parallelized *generation*; parallel *execution* (multiple Claude CLI sessions against the same repo) is a concurrency/merge problem deferred to a future epic
- **Plan quality scoring** — V2 auto-reviewed generated plans via `/api/ai/text/review`; V3 measures quality post-execution via deviation counts
- **Frontend redesign** — sidebar already renders task files; the only UI change is triggering V3 execution instead of V2 generation + separate execution

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

