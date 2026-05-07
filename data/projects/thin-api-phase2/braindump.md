The filesystem is locked down — I'll put everything directly here. This is long by design: every question gets full treatment.

---

# Thin API Phase 2 — Questions Answered + Brain Dump Rewrite

---

## PART 1: Open Questions — Answered

---

### From the Main Document

---

#### Q: How does the skill write files back to the project directory?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Agent writes directly to `SPEC_DOC_DIR` | Simplest. Partial files exist on crash. |
| B | Agent writes to a temp dir; Python does atomic move on clean exit | Safe. Requires Python to know the temp dir location. |
| C | Agent emits file content as base64 stdout lines; Python writes them | No filesystem coupling. Impractical for large files. |
| D | Agent writes to temp dir + emits manifest; Python promotes files only if manifest exists | Atomic + auditable. Clean partial-failure story. |

**Recommendation: Option D.**

The agent writes to `SPEC_DOC_DIR/.jobs/<job_id>/` during the run. Its last act before exit 0 is writing a `manifest.json` there listing every file it generated. Python's post-exit handler checks: manifest exists + exit 0 → copy files to `SPEC_DOC_DIR/`. Anything less → leave temp dir in place for debugging, mark job as failed. Direct writes to the live project dir are a trap — a crash at step 3 of 5 leaves the project half-written with no recovery path.

---

#### Q: How does the frontend know which files were generated?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Manifest stdout line: `output:analysis.md,epic.md` | Simple. String parsing. No metadata. |
| B | `skill.json` declares expected outputs; Python validates on exit | Static contract. Can't handle dynamic output (e.g. per-task files). |
| C | Python scans `SPEC_DOC_DIR` for files modified after job start | Works, but noisy in concurrent jobs. No source of truth. |
| D | Structured JSON event line: `{"type":"output","files":[{"name":"analysis.md","size":4200}]}` | Extensible. Parseable without regex. Carries metadata. |

**Recommendation: Option D.**

The manifest stdout line should be a JSON event, not a comma-delimited string. You'll want metadata (size, type, whether it's new vs. updated) before you think you will. Define this in `STDOUT_PROTOCOL.md` as the `output` event type. The Python post-exit handler parses this line and populates the job record's `outputs` field. The status endpoint returns it. The frontend renders it. No scanning, no static contracts.

---

#### Q: What replaces WorkflowExecution for per-step progress?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Plain text stdout lines: `step:analysis starting` | Human-readable. Hard to parse reliably. |
| B | Structured JSON event lines: `{"type":"step","name":"analysis","status":"done","elapsed_ms":4200}` | Machine-readable. Extensible. Debuggable. |
| C | A sidecar progress file written by the agent, polled by Python | Decoupled. Adds filesystem polling complexity. |
| D | No per-step tracking — just raw streaming output | Simplest. Frontend loses step-level UX. |

**Recommendation: Option B.**

Define a `step` event type in the stdout protocol. The Python status endpoint parses buffered stdout for `{"type":"step",...}` lines and returns an array of step states. The SSE stream forwards all lines raw. This means one source of truth (stdout) serves both the live stream consumer and the polling status consumer. No separate state machine. Elapsed time is free — the agent knows when each step started and ended.

---

#### Q: How does this work for per-task generation where state tracks multiple concurrent tasks?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Each task = its own `POST /api/run` | HTTP handles concurrency. Job IDs per task. Natural. |
| B | One job per project; agent manages internal parallelism | Concurrency inside the skill. Complex. Hard to cancel individual tasks. |
| C | A batch endpoint: `POST /api/run/batch [{skill, args}, ...]` | Convenient for the frontend. Hides per-task status. |

**Recommendation: Option A, with explicit frontend contract.**

The frontend calls `POST /api/run` once per task. It gets a job ID per task. It polls/streams each independently. Concurrency is at the HTTP layer. This isn't just simpler — it's the right model: tasks are independent units of work, failure of one shouldn't block others, and individual retry maps cleanly to "just call POST /run again for that task." Document this as an intentional design decision, not a limitation.

---

#### Q: What about the lint gate in task_gen?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Lint runs inside the skill; nonzero exit on failure | Agent owns the gate. One exit code for all failures. |
| B | Lint is a separate skill the task_gen skill calls (via stdout protocol) | Composable. Verbose. Requires skill composition story. |
| C | Python runs lint after subprocess exits | Python re-acquires domain knowledge. Regression. |
| D | Lint inside skill; distinct exit codes: 2=lint failure, 1=crash | Agent owns the gate + failure type is surfaced to Python. |

**Recommendation: Option D.**

The agent owns the lint gate — that's the whole point of Phase 2. But exit code is your only structured out-of-band channel from subprocess to Python. Use it. `exit 0` = success. `exit 2` = lint failure (user-actionable). `exit 1` = unexpected error (needs investigation). Python maps these to distinct job states and the frontend can show a different message for "your task failed lint" vs "something went wrong." Without this, every failure looks identical.

---

#### Q: Can the frontend trigger individual steps (analysis-only retry, epic-only retry)?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Separate skills per sub-step: `bootstrap-analysis-only` | Maximum granularity. Combinatorial explosion as steps grow. |
| B | One skill with a `steps` arg: `spec-pipeline --steps analysis` | Flexible. One skill file. Requires the agent to handle partial execution. |
| C | `steps` is a valid field in `skill.json`; the generic route passes it through | Same as B but the contract is formalized, not ad-hoc. |

**Recommendation: Option C.**

`skill.json` declares an optional `steps` field with valid step names. The frontend passes `{ skill: "spec-pipeline", args: { steps: ["analysis"] } }`. The agent runs only those steps. This prevents the "one skill file per retry surface" explosion while keeping the contract explicit and validatable before spawn. The skill.json becomes the canonical list of retry surfaces — which is the same as saying it's the canonical list of fault boundaries.

---

#### Q: How do we version skills in production?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Skills are files; deploy = git push; rollback = git revert | Simplest. No auditability of what version ran for a given job. |
| B | `skill.json` carries semver: `"version": "1.2.0"` | Auditable. Git is still the deployment mechanism. |
| C | Skills are git-tagged; frontend can request a specific version | Powerful. Overkill for current scale. |
| D | Skill versioning via feature flags | External dependency. Not worth it. |

**Recommendation: Option B.**

Skills are files — git is fine as the deployment mechanism. But `skill.json` should carry a `version` field, and the job record should store `skill_version` alongside `skill_name`. When a job fails in production, you know exactly what version of the skill ran. When you roll back a skill via git revert, the version field changes and the job history stays interpretable. This is one line in `skill.json` and one column in the jobs table. Do it now before you need to debug a regression without it.

---

### From the Previous Brainstorm

---

#### Q: Who owns partial failure?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Python confirms files exist after exit; accept partial state | Simple. Project can be in corrupt intermediate state. |
| B | Temp dir + atomic move on clean exit only | Safe. Requires consistent temp dir convention. |
| C | Agent writes completion manifest; Python only promotes files if manifest present | Cleanest contract. Partial files stay isolated in temp. |
| D | Agent is responsible for cleanup on failure — deletes own partial writes | Agent owns cleanup. Hard to debug what it wrote before failing. |

**Recommendation: Option C (same as the file-write answer — these are the same problem).**

Partial failure and the file-write model are one question, not two. If you implement the temp dir + manifest promotion pattern, partial failure is solved automatically: files never land in the live project dir unless the agent finished cleanly and declared completion. The temp dir at `.jobs/<job_id>/` is your forensic artifact. You can inspect it, replay it, or delete it. Option D (agent self-cleanup) sounds responsible but destroys the evidence you need to understand what went wrong.

---

#### Q: What's the security model for `skill`?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | `skill.json` lookup as gate — if the file doesn't exist, reject | Necessary but not sufficient. Doesn't prevent path traversal before lookup. |
| B | Regex sanitize before lookup: `skill` must match `^[a-z][a-z0-9-]{0,63}$` | Prevents path traversal. Simple. |
| C | Explicit allowlist in config: enumerate runnable skill names | Tight. Extra maintenance step when adding skills. |
| D | B + A combined: sanitize first, then existence-check `plugin/skills/<name>/skill.json` | Defense in depth. Neither step alone is sufficient. |

**Recommendation: Option D — mandatory, not optional.**

The generic route takes a user-supplied string and constructs a filesystem path from it. That's a path traversal vulnerability waiting to happen if you don't sanitize first. The correct sequence: (1) validate `skill` matches `^[a-z][a-z0-9-]{0,63}$` — reject immediately if not. (2) Check `plugin/skills/<name>/skill.json` exists — reject if not. (3) Never pass the skill name as a shell string — construct the subprocess args array in Python as a list, not a string. These three steps together make injection non-trivially hard. Document the threat model explicitly in the route code, not in a wiki.

---

#### Q: Does the agent actually self-orchestrate reliably at the workflow level?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Build Phase 2 and test in production | Fast. High risk if the claim is wrong. |
| B | Shadow mode: run both paths in parallel for two weeks | Validates with real traffic. Doubles infrastructure temporarily. |
| C | Benchmark: run spec-pipeline as single agent invocation against N known projects | Offline validation. Controlled. Comparable outputs. |
| D | Phased trust: start with single-step skills; layer in multi-step after validation | Incremental. Slower, but each step is validated before the next bet. |

**Recommendation: Option D, with Option C as the gate for each phase.**

Don't bet spec-pipeline (5 steps, state dependencies, lint gate) on the first deploy. The migration path:

1. **Phase 2a** — single-step skills only (`analysis-only`, `epic-only`). Each is one agent call, one file output. Run Option C benchmark against 10 known projects. Pass rate > 95%? Proceed.
2. **Phase 2b** — two-step skills with explicit state handoff. Benchmark again.
3. **Phase 2c** — full spec-pipeline with lint gate.

Each phase retires a piece of WorkflowExecution. You never delete the Python safety net before the agent has proven it can replace it at that specific level of complexity.

---

#### Q: How do you debug a production failure?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Trust the SSE stream — no persistence | Nothing to debug after the fact. |
| B | Pipe stdout to a flat file per `job_id`: `jobs/<job_id>.log` | Simple. Persistent. Grep-able. |
| C | Structured log middleware: captures exit code, duration, stdout tail, skill version | Queryable. Slightly more setup. |
| D | B + C: flat file log + structured job record | Full picture: raw log for context, structured record for queries. |

**Recommendation: Option D.**

Every subprocess stdout is tee'd to `jobs/<job_id>.log` (raw). The job record stores: `skill_name`, `skill_version`, `exit_code`, `started_at`, `ended_at`, `stdout_tail` (last 50 lines), `error_type` (none/lint-failure/crash). The status endpoint returns `stdout_tail` when the job is in error state. "What happened to job xyz" is answered by: (1) check job record for exit code and error type, (2) `cat jobs/xyz.log` for the full picture. Add job_id to the Docker log output so cross-referencing is instant. Without this, a silently hanging agent or a partial write is completely opaque.

---

#### Q: What's the skill composition story?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Composition is out of scope — skills stay atomic | Simple. Explicit constraint. Build it when needed. |
| B | Skills can call other skills via HTTP: `POST /api/run` from inside the agent | Reuses the existing job model. Each sub-skill is trackable. |
| C | Skills invoke sub-skills via a CLI helper: `run_skill("analysis", args)` | Tighter coupling. Bypasses the HTTP layer. Harder to track. |
| D | Skills declare dependencies in `skill.json`; Python pre-resolves and sequences | Python re-acquires orchestration knowledge. Regression. |

**Recommendation: Option A for Phase 2, Option B as the documented future path.**

Explicitly write "skill composition is out of scope for Phase 2" in the architecture doc. If a skill needs another skill's output, the current answer is: write a skill that does both things. If that becomes a real constraint (not a theoretical one), the right model is Option B — the agent calls `POST /api/run` as an HTTP tool call, gets a job ID, polls status, and continues. This reuses the same job/stream model and keeps each sub-skill independently observable. Don't build it speculatively.

---

#### Q: When does "one generic route" become the wrong abstraction?

**Options**

| | Model | Tradeoff |
|---|---|---|
| A | Define the scope in docs; handle exceptions as they arise | Pragmatic. Exceptions accumulate silently. |
| B | `execution_model` field in `skill.json`: `"subprocess"` \| `"sync"` \| `"webhook"` | Explicit. The route reads it and routes accordingly. |
| C | Force everything into subprocess model; accept no exceptions | Pure. Breaks for cheap synchronous calls. |
| D | Second generic route for sync: `POST /api/run/sync` | Explicit split. Two routes instead of one. |

**Recommendation: Option B.**

The generic route needs to know one thing about a skill: how to run it. `"execution_model": "subprocess"` = spawn process, return job_id, stream stdout. `"execution_model": "sync"` = run inline, return result in the response body, no job_id. This handles the cases that break the async model (cheap validation, health checks, file reads) without adding per-skill route logic. The scope boundary is now machine-readable, not a comment in the code. A webhook model can be added later if needed. Do this now — the first time someone asks "why do I need to poll for a result that takes 50ms?" you'll want the answer to be "add execution_model: sync to skill.json" not "we need to add a new route."

---

## PART 2: Brain Dump — Rewritten

The previous brainstorm was observation-mode: "here are connections, here are tensions." This rewrite is decision-mode: here's what you must decide, in what order, and what the options cost you.

---

# Thin API Phase 2 — Decision Map

## The Actual Claim Being Made

Phase 2 rests on one bet: **the agent's judgment is more reliable than the Python scaffolding built to constrain it.** Everything else — the generic route, the stdout protocol, the subprocess model — is infrastructure that makes that bet viable. If the bet is wrong, no amount of clean infrastructure saves you. If the bet is right, deleting the Python orchestration layer is inevitable. The question is how you validate the bet incrementally instead of all at once.

---

## The Five Decisions That Shape Everything Else

### 1. The File-Write Contract (Atomic vs. Direct)

**The stakes:** Agent writes directly to `SPEC_DOC_DIR` → crash at step 3 corrupts the project. Temp dir + manifest promotion → crash is isolated, forensic artifacts preserved, project is never half-written.

**Decision:** Agent writes to `.jobs/<job_id>/` during run. Final act before exit 0 is `manifest.json`. Python promotes on clean exit + manifest present. This is not optional infrastructure — it's the difference between a system that can fail safely and one that can't.

---

### 2. The Stdout Protocol (Convention vs. Spec)

**The stakes:** `step:analysis starting` is a string convention that will drift, be inconsistently formatted, and fail silently. A named JSON event schema is a contract that fails loudly and is machine-parseable from day one.

**Decision:** Write `STDOUT_PROTOCOL.md` before writing the first skill. Define three event types to start:

```json
{"type": "step",   "name": "analysis", "status": "started|done|failed", "elapsed_ms": 0}
{"type": "output", "files": [{"name": "analysis.md", "size": 4200}]}
{"type": "error",  "message": "...", "recoverable": false}
```

Write a Python validator (20 lines) that parses a job's stdout and checks protocol compliance. Run it in CI. Skills that don't comply fail at dev time. The stdout protocol IS the API contract between the agent and the Python host — treat it with the same rigor as an HTTP API.

---

### 3. The Security Gate (Sanitize Before You Trust)

**The stakes:** User-supplied skill name → filesystem path → subprocess. Without explicit sanitization, this is a path traversal vulnerability. The skill.json existence check is NOT sufficient on its own.

**Decision:** Two-step mandatory gate in the generic route:
1. Validate skill name against `^[a-z][a-z0-9-]{0,63}$` — reject immediately if not.
2. Check `plugin/skills/<name>/skill.json` exists — reject if not.
3. Build subprocess args as a Python list, never a shell string.

This is three lines of code and a documented threat model. Do it before the route goes to production.

---

### 4. The Migration Strategy (Phased Trust vs. Big Bang)

**The stakes:** "The agent orchestrates itself" is a claim, not a fact. Deleting WorkflowExecution before that claim is validated with real multi-step traffic is how you end up with no fallback when it fails.

**Decision:** Three-phase migration. Each phase requires a benchmark (run N known projects, measure pass rate) before proceeding:

- **Phase 2a:** Single-step skills only. One agent call, one file output. Retire the simplest services.
- **Phase 2b:** Two-step skills with state handoff. Validate sequencing works.
- **Phase 2c:** Full spec-pipeline with lint gate. Delete WorkflowExecution.

Each phase has a pass threshold and a rollback plan. WorkflowExecution stays in the codebase until Phase 2c passes. The branching point (`CHAIN_PROVIDER=cli` style) lets you run both paths.

---

### 5. The Observability Model (Log Everything That Moves)

**The stakes:** A silently failing agent or a partial write with no log is the worst failure mode — invisible, non-reproducible, non-debuggable. The subprocess model trades Python-level observability for simplicity, and you have to consciously replace what you lose.

**Decision:** Every job gets:
- `jobs/<job_id>.log` — raw stdout, tee'd from the subprocess pipe.
- Job record: `skill_name`, `skill_version`, `exit_code`, `started_at`, `ended_at`, `stdout_tail` (last 50 lines), `error_type`.
- `GET /api/health` returns pinned CLI version.
- Job ID in all Docker log lines.

"What happened to job xyz?" must always have an answer. This is the infrastructure that makes the subprocess model production-grade instead of a prototype.

---

## The Two Hidden Tensions Worth Naming

### Tension 1: Skill Granularity IS the Fault Tolerance Map

Every retry surface the frontend offers corresponds to a skill boundary. If you design skills for DX (one big spec-pipeline skill because it's clean) you silently eliminate retry granularity. If you design for fault tolerance (one skill per step) you create a combinatorial explosion of skill files.

**Resolution:** Use the `steps` arg pattern. One skill file. `skill.json` declares valid step names. Frontend passes `{ steps: ["analysis"] }` for a partial retry. The skill decomposition map and the fault tolerance map are unified in one `skill.json` — design them together once, don't retrofit later.

### Tension 2: "No Domain Knowledge" vs. Skill Evolution

The Python layer knowing nothing about skills is the goal. But as skills accumulate and contracts change, something has to own backward compatibility. Right now the answer is "git revert" — which only works if the frontend, skill contract, and stored job state are all versioned together. At small scale, this is fine. At 20 skills and 6 months of job history, it isn't.

**Resolution:** `skill.json` carries semver now, stored in job records. This costs nothing today and buys you auditability and breaking-change awareness when you need it. The Python layer still knows nothing about what skills *do* — it just records what version of a skill ran. That's not domain knowledge; it's an audit log.

---

## What the Skill Registry Unlocks

`GET /api/skills` — returns all available skills, their `skill.json` contracts, estimated durations, and current versions — is the canary test for whether the "no domain knowledge" abstraction is actually clean.

If the frontend can render a run form, display step progress, show expected outputs, and surface retry options **purely from skill metadata**, the abstraction is working. If the frontend needs any hardcoded knowledge of what `spec-pipeline` does to render correctly, the abstraction has a leak.

Build this endpoint early. It's a dozen lines of Python (read all `skill.json` files in `plugin/skills/`). It makes the architecture's central claim testable. And it pays forward into discoverability, deprecation warnings, and duration estimates — none of which require rebuilding the underlying model.

---

## Deployment Checklist Before Phase 2 Goes Live

These are the things that need to be true before WorkflowExecution can be deleted — not aspirations, actual gates:

- [ ] `STDOUT_PROTOCOL.md` written and CI validator passing
- [ ] Path traversal security gate implemented and tested
- [ ] Temp dir + manifest promotion implemented; partial failure tested explicitly
- [ ] Job log file written for every subprocess run
- [ ] CLI version pinned in Docker image and surfaced in `/api/health`
- [ ] Phase 2a benchmark passed (single-step skills, N known projects)
- [ ] `skill.json` version field populated for all skills
- [ ] `execution_model` field defined so sync vs. async is explicit
- [ ] "Who owns partial failure?" answered in the architecture doc, not just in code

---

## The One-Line Summary

Phase 2 isn't "remove Python from AI calls." It's "move the last remaining trust boundary from Python's WorkflowExecution to the agent's judgment" — and the job of the infrastructure is to make that trust verifiable, auditable, and recoverable when it's wrong.