# Thin API Phase 2 — Zero-Python AI Layer

## Where Phase 1 Left Us

Phase 1 removed prompt strings from Python services. The services still exist —
they still own the routing logic, the workflow steps, the multi-step chain sequencing,
the streaming pattern, the background thread lifecycle. Python got thinner but
it's still the orchestrator.

The fundamental structure is unchanged:
- One Python route per generation type (bootstrap, epic guide, task guide, rewrite, iterate…)
- One Python service per generation type
- One Python workflow per multi-step chain
- A WorkflowExecution state machine in Python
- A threading.Thread per job in Python

Every new generation type still requires: a new route, a new service, a new workflow,
a new background thread pattern, new tests. The plugin skills describe what to do —
but Python still decides when, in what order, with what state.

## The Extreme Version

What if the API had no domain knowledge at all?

One route: `POST /api/run { skill: "spec-pipeline", project_id: "...", args: {} }`
One response: `{ job_id: "..." }`
One polling route: `GET /api/run/status/<job_id>`

The Python layer does exactly three things:
1. Auth + rate limiting
2. Spawn a subprocess running `claude --skill <skill> <args>`
3. Stream stdout to the polling client

The plugin skill is the service. The agent is the workflow engine.
Adding a new generation type means writing a markdown file, not a Python file.

## What Goes Away

- `api/modules/ai/workflows/` — the entire workflow engine
- `api/modules/ai/services/` — all generation services
- `api/modules/ai/routes/` — all domain-specific routes (replaced by one generic route)
- `WorkflowExecution`, `AICall`, `Compute`, `Workflow.builder()` — the whole runtime layer
- Background thread boilerplate — subprocess stdout IS the stream
- Per-step polling complexity — one job, one stream, one done signal

## What Stays

- Auth (JWT + require_auth)
- Usage limiting (check_usage_limit)
- Project CRUD (create, read, list projects)
- File I/O service (read/write files in SPEC_DOC_DIR)
- The Angular frontend (unchanged — same HTTP contract)
- The Docker setup

## The New API Surface

```
POST /api/run
  { skill: "spec-pipeline", project_id: "abc", args: { ... } }
  → { job_id: "xyz" }

GET /api/run/status/<job_id>
  → { running, done, output?, error? }

GET /api/run/stream/<job_id>
  → SSE stream of stdout lines

POST /api/projects          (unchanged)
GET  /api/projects          (unchanged)
GET  /api/projects/<id>     (unchanged)
POST /api/auth/login        (unchanged)
```

Everything the frontend needs. Half the Python.

## The Skill Side

Each skill gets a machine-callable contract alongside its human-readable SKILL.md:

```
plugin/skills/spec-pipeline/
  SKILL.md          ← human procedure (already exists)
  skill.json        ← machine contract: inputs, outputs, estimated_duration
```

The generic run route reads `skill.json` to validate inputs before spawning.
No Python knowledge of what the skill does — just input validation and process spawn.

## The Streaming Model

Current: background thread → stdout captured → stored in execution state → client polls.

New: subprocess stdout is piped directly to SSE. The skill writes progress lines to stdout.
The run route streams them to the client. No intermediate state. No polling for partials.
Done when the process exits.

```
claude --skill spec-pipeline abc123
  → stdout: "step:analysis starting\n"
  → stdout: "step:analysis done\n"
  → stdout: "step:epic starting\n"
  ...
  → exit 0
```

## Open Questions

How does the skill write files back to the project directory?
  — Agent reads/writes SPEC_DOC_DIR directly. Python just confirms the files exist after exit.

How does the frontend know which files were generated?
  — Skill writes a manifest line to stdout: `output:analysis.md,epic.md`. Python parses on exit.

What replaces WorkflowExecution for per-step progress?
  — Structured stdout lines (`step:<name> <status>`). Python parses them for the status endpoint.

How does this work for per-task generation (task_gen) where state tracks multiple concurrent tasks?
  — Each task is its own `POST /api/run` call. Job IDs are per-task. Concurrency is at the HTTP level.

What about the lint gate in task_gen?
  — Lint runs inside the skill (agent calls lint tool). If it fails, skill exits nonzero. Python records error.

Can the frontend still trigger individual steps (analysis-only retry, epic-only retry)?
  — Yes: each retry is just `{ skill: "bootstrap-analysis-only", project_id: "..." }`. Skills can be granular.

How do we version skills in production?
  — Skills are files in the repo. Deploy = git push. Rollback = git revert. Same as today.

## Risk: The Claude CLI as a production dependency

Phase 1 already accepted this risk (`CHAIN_PROVIDER=cli`). Phase 2 deepens it.
Every AI call goes through the Claude CLI subprocess. If the CLI updates and breaks,
all AI generation stops. Mitigation: pin the Claude Code CLI version in the Docker image.

## Why Now

Phase 1 proved the pattern at the service level. The WorkflowExecution runtime is
now the last remaining layer of Python that exists purely to orchestrate AI calls.
The agent can orchestrate itself. The runtime was built before the plugin existed —
it was the only way to sequence multi-step chains. That reason is gone.
