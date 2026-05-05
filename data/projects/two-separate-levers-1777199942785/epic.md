# 🎯 Epic: Two Separate Levers — CLI Timeout Fix & Generate-Task Endpoint

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Implementation guides are the primary deliverable Chain Primitive produces for each project. When a guide silently fails to generate — because the CLI subprocess exceeds its 600-second ceiling — the developer has no recovery path short of re-running a full bootstrap. That full re-run is expensive, non-targeted, and risks overwriting guides that already exist. The gap between "guide generation started" and "guide is missing with no error" is invisible in the current system, meaning developers may not notice the failure until they need the guide downstream.

The generate-task endpoint converts a silent, unrecoverable failure mode into a visible, actionable one. Once the timeout floor is raised and the endpoint exists, a developer who sees a missing guide can trigger targeted regeneration from the sidebar in seconds rather than re-bootstrapping the entire project. The Angular polling client and the prompt builder already exist; the missing piece is the backend surface that connects them.

The compound effect is reliability: guides complete on the first attempt (timeout fix), and the rare case that still fails has a cheap, precise recovery (the endpoint). Both improvements accrue to every future project bootstrapped on the platform.

**Value Proposition**: Replace silent, unrecoverable guide generation failures with a timeout that covers observed variance and a targeted regeneration endpoint developers can invoke without re-running bootstrap.

---

## Scope

### What This Epic Covers

- **CLI timeout raise** — increase the subprocess ceiling from 600 s to 1 200 s so generation tasks that fall within observed variance complete without silent failure
- **POST /api/projects/{id}/generate-task** — a Flask route that spawns a background thread to find the next missing guide, build its prompt, and write the output file
- **GET /api/projects/{id}/generate-task/status** — a route that exposes the background thread's current state to the existing Angular polling client

### What This Epic Does NOT Cover

- ❌ **Bootstrap migration to the generate-task endpoint (Step 4)** — no second consumer of the endpoint exists yet; defer until the endpoint has proven reliability in production
- ❌ **Configurable timeout via env-var or per-task heuristic** — hardcoding 1 200 s is sufficient until task variance data justifies the abstraction
- ❌ **Bulk or batch generation** — speculative; no current consumer implies it

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Raise CLI subprocess timeout** | None | — | 0.5 days | High |
| 2 | **Implement generate-task routes + background thread** | Task 1 | — | 2 days | High |

---

### Task 1: Raise CLI Subprocess Timeout

The single-line change in `api/modules/chain/providers/cli.py` that raises `timeout=600` to `timeout=1200`. This is a prerequisite for Task 2 because the background thread calls the same subprocess path; without this change the endpoint inherits the identical failure mode it is meant to fix. Observed peak generation time (Dev Experience, 460 s) sets the lower bound; 1 200 s provides headroom without speculative over-engineering.

**Port budget**: 1 line changed in `modules/chain/providers/cli.py`; no new abstractions, no new tests.

---

### Task 2: Implement generate-task routes + background thread

Two Flask routes and a background thread registered under `modules/projects/routes.py` (or a new `modules/task_gen/routes.py` registered in `create_app.py`):

**POST `/api/projects/<project_id>/generate-task`** — validates the project exists, rejects if a thread is already running for that project, spawns a background thread, returns `{"started": true}` immediately (HTTP 202).

**GET `/api/projects/<project_id>/generate-task/status`** — reads in-process per-project state dict, returns the shape the Angular polling client already expects:
```json
{"running": bool, "done": bool, "allDone"?: bool, "filename"?: str, "taskNum"?: str, "taskName"?: str, "error"?: str}
```

**Background thread sequence** (all data sourced without new infrastructure):
1. Load project via `get_project(projects_dir, project_id)` → get all file contents
2. Find `epic.md` content from the specs list
3. Parse tasks via `bootstrap_extract_tasks(epic_content)` — already in `modules/ai/prompts/__init__.py`
4. Determine next missing task: find first task number with no matching `task-{num}-*.md` file in the project directory. If all present → set `allDone=True`, exit.
5. Extract task description block: `re.search(rf"### Task {num}:[^#]*", epic_content, re.DOTALL)`
6. Load context: `read_context("builder")`, `read_context("principles")`, `read_context("codebase")`, `read_context("references")` from `modules/context/service`
7. Collect prior task content: read all `task-N-*.md` files with num < current task num, concatenate (truncated to ~60 lines each)
8. Call `build_implementation_guide_prompt(...)` from `modules/implementation_guide/prompts` with all assembled data
9. Call `chain_adapter.generate(system, user)` — this is the only AI call; all other steps are I/O
10. Write output file via `update_file(projects_dir, project_id, filename, content)`
11. Update in-process state to `done=True` with filename/taskNum/taskName

**In-process state**: a module-level `dict[str, dict]` keyed by `project_id`. Each entry holds `running`, `done`, `error`, `filename`, `taskNum`, `taskName`, `allDone`. Reset on new POST.

**Angular contract already satisfied**: `ImplementationGuideService.generateNextTask()` already calls these exact URLs and already polls the status shape above. No Angular changes needed — the button works the moment this endpoint exists.

**Port budget**: ~100 lines in one new file; reuses `bootstrap_extract_tasks`, `build_implementation_guide_prompt`, `chain_adapter`, `get_project`, `update_file`, `read_context` without modification.

---

## Success Criteria

- ✅ A generation task that previously exceeded 600 s completes without error
- ✅ POST `/api/projects/{id}/generate-task` accepts a request and spawns a background thread without blocking the HTTP response
- ✅ GET `/api/projects/{id}/generate-task/status` returns a state the Angular polling client can act on
- ✅ The Chain Primitive "Generate Next Task" sidebar button produces a new `task-N-*.md` file without triggering a full bootstrap (Angular wiring already in place — no code change required)

---

## Non-Goals

- ❌ **Bootstrap migration** — Step 4 of the input recommendation; deferred until the endpoint has demonstrated production reliability and a second consumer warrants the abstraction
- ❌ **Configurable or per-task timeout** — no variance data yet; revisit when multiple task types have observed timing distributions
- ❌ **Streaming progress events** — adds protocol complexity with no current consumer; polling is sufficient for the sidebar UX
- ❌ **Batch / multi-task generation in a single request** — speculative; no product requirement exists

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview