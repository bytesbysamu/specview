# 🏗️ Solution Architecture: Two Separate Levers

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The system has two independent failure modes that happen to share a root. The CLI subprocess timeout is a global ceiling that applies to every generation call regardless of call site — bootstrap, direct API call, or background thread. Raising that ceiling is not a feature; it is removing a constraint that would otherwise defeat every other improvement in this epic. The generate-task endpoint is a separate concern: it provides a targeted, visible recovery path for missing guides that the current system entirely lacks. Treating them as one lever would misrepresent the problem and produce a muddier design.

The endpoint design follows the shape of infrastructure already present. `implementation_guide/prompts.py` already builds prompts. `modules/chain/adapter.py` already owns the sole boundary between application logic and the AI provider. The Angular sidebar already has a polling client wired to a status shape. The architectural work is to connect these existing pieces with the minimum new surface: one route that spawns a thread, one route that reads the thread's in-process state, and one timeout parameter that stops the thread from inheriting the old ceiling.

The deliberate constraint is that no new shared infrastructure is introduced. Thread state stays in-process; there is no queue, no database write, and no new service layer. This is appropriate because the endpoint has exactly one consumer — the Chain Primitive sidebar — and in-process state is sufficient for that polling contract. Introducing a persistent store would add failure modes without adding capability for this consumer.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Remove constraints before adding features | The timeout raise is treated as a prerequisite, not bundled with the endpoint, because the endpoint inherits the subprocess ceiling and would silently reproduce the original failure without it |
| One adapter boundary for AI calls | All generation passes through `modules/chain/adapter.py`; the background thread calls the adapter, not the CLI directly, so the provider is interchangeable |
| In-process state is sufficient for one consumer | The Angular polling client needs a state signal, not an audit log; thread state held in memory satisfies that contract without a persistence layer |
| Reuse over duplication | The prompt builder in `implementation_guide/prompts.py` and the chain adapter are reused without modification; the new route is a thin orchestrator, not a second implementation of generation logic |
| Hardcode the concrete case | The endpoint has one consumer. Abstractions for batch generation or multi-consumer dispatch are deferred until a second consumer exists |

---

## System Boundaries

### What This System Includes

- The timeout parameter in `modules/chain/providers/cli.py` that sets the subprocess ceiling for all generation calls
- The POST route that receives a regeneration request, spawns a background thread, and returns immediately
- The background thread that locates the next missing guide, invokes the prompt builder, and calls the chain adapter
- The GET status route that reads in-process thread state and returns it in the shape the Angular polling client expects
- The binding in the Chain Primitive sidebar that points the existing polling client at the new endpoint URLs

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Configurable or per-task timeout | No variance data across task types exists yet; hardcoding 1 200 s is sufficient and avoids premature parameterisation |
| Persistent thread state (database, queue) | The single consumer is a polling client; in-process state satisfies the contract without the failure modes of an external store |
| Bootstrap migration to the generate-task endpoint | Deferred until the endpoint has demonstrated reliability and a second consumer warrants the shared path |
| Streaming progress events over SSE or WebSocket | Adds protocol complexity the sidebar polling client does not require; polling is sufficient for this UX |
| Batch or multi-task generation in a single request | No product requirement exists; speculative design would impose interface constraints with no current payoff |

---

## Component Design

### CLI Subprocess Timeout

**Purpose**: Removes the 600-second ceiling that caused the guide generation failure documented in [Analysis](./analysis.md). All generation call sites — bootstrap, direct adapter calls, and the new background thread — invoke `subprocess.run` through `cli.py`. Without this change, every downstream improvement inherits the original failure mode.

**Key Parts**:
- `modules/chain/providers/cli.py` — holds the single `timeout` parameter that governs every subprocess call the CLI provider makes

**Patterns**: Configuration constant — no abstraction warranted for a single numeric parameter with one change site.

**Why 1 200 s**: Observed peak generation time (460 s, Dev Experience project) sets the lower bound. Doubling provides headroom for variance without speculative over-engineering. This is not a permanent ceiling; it is a value grounded in observed data.

---

### POST Generate-Task Route

**Purpose**: Provides the Chain Primitive sidebar with an endpoint it can invoke to trigger targeted regeneration of a missing implementation guide. The route itself does no generation work; it delegates immediately to a background thread and returns an accepted response so the HTTP connection is not held open.

**Key Parts**:
- Route handler under `/api/projects/{id}/generate-task` — validates the project, checks that no thread is already running for this project, spawns the thread, and returns HTTP 202
- Background thread — the sole owner of the generation sequence:
  1. `get_project(projects_dir, project_id)` → fetch all file contents
  2. `bootstrap_extract_tasks(epic_content)` (`modules/ai/prompts/__init__.py`) → parse task list
  3. First task num with no matching `task-{num}-*.md` in the project dir → next missing task; if none → set `allDone=True`
  4. `re.search(rf"### Task {num}:[^#]*", epic_content, re.DOTALL)` → extract `task_desc`
  5. `read_context("builder")`, `read_context("principles")`, `read_context("codebase")`, `read_context("references")` → load context strings
  6. Read existing `task-N-*.md` files (num < current) from project dir, concatenate (~60 lines each) → `prior` parameter
  7. `build_implementation_guide_prompt(task_num, task_name, task_effort, task_desc, arch, builder, principles, codebase, references, prior)` → system + user prompt
  8. `chain_adapter.generate(system, user)` → sole AI call
  9. `update_file(projects_dir, project_id, filename, content)` → persist result
- `implementation_guide/prompts.py` — called by the thread; not modified
- `modules/chain/adapter.py` — called by the thread as the sole AI boundary; not modified
- In-process state: module-level `dict[str, dict]` keyed by `project_id`; fields: `{running, done, allDone, filename, taskNum, taskName, error}`

**Patterns**: Fire-and-forget thread dispatch. The route is an orchestrator with no generation logic of its own. The adapter boundary (ELA Pattern #1) ensures the thread is not coupled to the CLI provider directly — a different provider can be substituted without touching the thread.

**Why a thread and not a task queue**: The endpoint has one consumer and one concurrent generation per project is the expected case. A queue introduces a broker dependency and failure modes (broker unavailability, message loss) that in-process threads avoid. If a second consumer or concurrent multi-project generation emerges, the thread model is a well-understood migration target for a queue.

---

### GET Generate-Task Status Route

**Purpose**: Exposes the in-process state of the background thread to the Angular polling client. The client already exists and already expects a state signal; this route provides the real signal in place of the stub the client currently polls against.

**Key Parts**:
- Route handler under `/api/projects/{id}/generate-task/status` — reads shared in-process state and returns it in the polling contract shape
- In-process state store — a minimal structure (per-project) holding whether a thread is running, idle, or faulted, and optionally the name of the task currently being generated

**Patterns**: Read-only projection of in-process state. The route is intentionally thin — it reads, shapes, and returns. No writes, no side effects.

**Why no database**: The polling client needs a current-state signal, not history. In-process state is reset on process restart, which is acceptable because an in-flight generation that survives a process restart is an edge case outside this epic's scope. Adding a database for this case would trade simplicity for correctness in a scenario with no current consumer requirement.

---


## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend routes | Flask | Existing framework; no new dependency introduced |
| Background execution | Python threading | Sufficient for one-per-project concurrency; no broker dependency |
| In-process state | Module-level dict keyed by project ID | Simplest structure that satisfies one polling consumer; no persistence overhead |
| AI boundary | `modules/chain/adapter.py` (existing) | ELA Pattern #1 already in place; thread calls adapter, not provider directly |
| Frontend | Angular (existing service + component) | No new framework; binding only |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Raise timeout to 1 200 s (hardcoded) | Grounded in observed peak (460 s); provides headroom without abstraction | Does not adapt to future task types with different distributions; revisit when variance data exists |
| Background thread over task queue | One consumer, one-at-a-time per project; avoids broker dependency and associated failure modes | Cannot survive process restart mid-generation; not suitable if concurrent multi-project generation becomes a requirement |
| In-process state over persistent store | Polling contract requires current state only, not history; simplest correct solution for one consumer | State lost on process restart; acceptable given no consumer requirement for restart-resilient progress |
| Reuse prompt builder and adapter without modification | Avoids duplicating generation logic; keeps the adapter as the sole AI boundary | Thread is a new call site for existing functions; any signature change to those functions becomes a breaking change for the thread as well |
| No bootstrap migration in this epic | Bootstrap is a separate call site; migrating it before the endpoint has demonstrated reliability would couple two concerns | Bootstrap and endpoint remain independent call sites until the endpoint has a reliability baseline |

---

## Execution Flow

The sequence below describes the two levers and how they interact at runtime. It is not a step-by-step implementation guide.

```
Prerequisite
  cli.py timeout raised to 1 200 s
    └─ all downstream call sites inherit the new ceiling

Regeneration flow (sidebar trigger)
  Sidebar button pressed
    └─ POST /api/projects/{id}/generate-task
         └─ thread spawned, HTTP 202 returned immediately
              └─ thread: locate next missing guide
                   └─ thread: build prompt (implementation_guide/prompts.py)
                        └─ thread: chain_adapter.generate()
                             └─ adapter: cli.py subprocess (now with 1 200 s ceiling)
                                  └─ thread: write output file

Polling flow (sidebar indicator)
  Polling client ticks
    └─ GET /api/projects/{id}/generate-task/status
         └─ in-process state read
              └─ response: running | idle | faulted (+ optional task name)
```

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview