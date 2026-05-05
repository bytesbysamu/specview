---
sidebar_position: 2
---

# Pipeline V2 -- Epic

**Purpose**: Define scope and tasks for automating the five manual pipeline interventions that dropped deviation average from 6.0 to 2.0.

**Source Analysis**: See [Analysis](./analysis.md) for the problems each task addresses.

---

## Business Value

The spec-doc pipeline's value proposition is that specs are good enough for an AI executor to run end-to-end with minimal deviation. One session proved this works -- but only because the operator manually rescanned context, reviewed outputs, injected caveats, stripped preamble, and counted deviations. Those five interventions are the difference between a 6.0-deviation run (unusable without hand-holding) and a 2.0-deviation run (executor ships clean code).

Without codifying them, every new session starts from scratch. Worse, anyone who clones spec-doc and runs it on a different project gets the 6.0 experience, not the 2.0 experience. Pipeline V2 makes the pipeline self-correcting: context stays fresh, outputs get reviewed before execution, environment quirks are injected automatically, LLM formatting artifacts are stripped, and deviation counts are measured programmatically.

The compound effect matters most. Each intervention improves spec quality by a bounded amount individually, but together they close the gap between "operator-assisted pipeline" and "autonomous pipeline." This is the difference between "Sam's tool that Sam operates" and "a product someone else can run."

---

## Scope

### What This Epic Covers

- Auto-rescan of `codebase.md` after foundation tasks merge, triggered by dependency markers in the epic's task table
- Post-generation advisory review that appends findings to the spec without blocking executor launch
- Regex-based preamble stripping in `regen-task.mjs` to enforce the Executor Protocol's "first character is `#`" rule
- Per-project `caveats.md` loading with global fallback, injected as a context block in every task-generation prompt
- Deviation-count parser that reads commit bodies for `Deviation: <category> -- <description>` lines and outputs a categorized summary table

### What This Epic Does NOT Cover

- Blocking review gates -- advisory is sufficient per session evidence; blocking is a future gate earned by data showing advisory alone is insufficient
- Frontend UI for deviation reports -- the parser outputs to stdout and optionally to a file; a dashboard is a separate capability when there is a second consumer
- Changes to the AI provider layer (`cliProvider`, `remoteProvider`) -- Pipeline V2 changes prompt assembly and post-processing, not the model call
- Multi-project orchestration -- each project folder is self-contained; cross-project pipelines are a separate epic
- Implementation guide generation prompt changes beyond caveats injection -- the prompt template in `regen-task.mjs` is already mature; V2 adds a context block, not a rewrite

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Preamble Strip** | None | 2, 4 | 0.5 day | High |
| 2 | **Caveats Injection** | None | 1, 4 | 0.5 day | High |
| 3 | **Auto-Rescan** | None | 4 | 1 day | High |
| 4 | **Auto-Review** | None | 1, 2, 3 | 1 day | High |
| 5 | **Deviation-Count Parser** | None | -- | 1 day | Medium |

### Task Details

### Task 1: Preamble Strip

Add a single regex in `scripts/regen-task.mjs` that drops everything before the first `# ` heading in the LLM response. Pipeline output sometimes starts with "I now have enough context..." or similar reasoning preamble. The Executor Protocol (see `principles.md`, section "Executor Protocol") requires the first character of a generated guide to be `#`. This is a one-line fix with a test to confirm it strips known preamble patterns and passes through clean output unchanged.

**Files**: `scripts/regen-task.mjs` (modify), test file (new)

### Task 2: Caveats Injection

Load a `caveats.md` file as a new context block in every task-generation prompt. Resolution order: look for `caveats.md` in the project folder first (`projects/{projectId}/caveats.md`), fall back to a global `caveats.md` at the repo root. The block uses the existing `getCaveatsBlock()` helper already defined in `regen-task.mjs`. This task extends `server.js`'s `generate-spec` endpoint and `regen-task.mjs` to both load caveats with the per-project-then-global resolution. Per-project from day one prevents Bubls-specific quirks leaking into other projects.

**Files**: `server.js` (modify: add caveats loading to generate-spec), `scripts/regen-task.mjs` (modify: add per-project resolution), test file (new)

### Task 3: Auto-Rescan

After each foundation task merges, rescan the target repo's `codebase.md` before generating downstream task specs. In `regen-task.mjs`, add a `--rescan` flag that calls the `/api/ai/text/scan` endpoint on the workspace before building the prompt. The decision is to rescan after foundation tasks only (tasks with no dependencies that others depend on), not after every task. Session evidence: stale-path deviations came from tasks that depended on Task 1's output, not from parallel siblings. The script detects foundation tasks by parsing the epic's task table for tasks where other tasks list them as dependencies.

**Files**: `scripts/regen-task.mjs` (modify: add --rescan flag and foundation detection), test file (new)

### Task 4: Auto-Review

After `regen-task.mjs` generates a task spec via `/api/ai/text/generate`, pipe the output through `/api/ai/text/review` with the project's architecture and principles as rubric. Append the review findings as a `## Post-generation Review` section at the end of the generated spec. Advisory, not blocking -- the executor sees the review notes and adapts. Session evidence: advisory review alone dropped deviation average from 6.0 to 3.0. If deviations stay high despite advisory, that is the signal to add a blocking gate later.

**Files**: `scripts/regen-task.mjs` (modify: add post-generation review call and append logic), test file (new)

### Task 5: Deviation-Count Parser

Build a script that parses commit bodies for `Deviation: <category> -- <description>` lines, counts per task, and categorizes into five buckets: `stale-context`, `UX-silent`, `env-gap`, `commit-drift`, `positive-review-absorption`. Output a summary table to stdout and optionally to a file. This is the spec-quality signal -- without it, you cannot tell whether the pipeline is calibrated or drifting between runs.

**Format contract**: executors write `Deviation: <category> -- <description>` in commit bodies (one line per deviation). The parser uses this format to categorize automatically.

**Files**: `scripts/deviation-report.mjs` (new), test file (new)

---

## Success Criteria

- Preamble strip: generated specs never start with LLM reasoning preamble; first character is always `#`
- Caveats injection: `regen-task.mjs` and `server.js` both load per-project caveats with global fallback; caveats block appears in generated prompts when `caveats.md` exists
- Auto-rescan: running `regen-task.mjs --rescan` on a foundation task triggers a `/api/ai/text/scan` call before prompt assembly; downstream tasks receive fresh codebase context
- Auto-review: every generated spec includes a `## Post-generation Review` section with dimensional scores and findings; executors absorb review notes (deviation average stays at or below 3.0)
- Deviation parser: running `scripts/deviation-report.mjs <repo-path>` on a repo with executor commits produces a categorized deviation table matching the 5-bucket taxonomy
- Combined: a fresh clone of spec-doc, given a braindump and a target codebase, produces implementation guides with deviation average <= 3.0 without manual intervention

---

## Non-Goals

- Blocking review gate -- earned by data, not pre-built
- Frontend deviation dashboard -- stdout is the UI until a second consumer appears
- Prompt template rewrite -- the existing `buildImplementationGuidePrompt()` is mature; V2 adds context blocks, not restructuring
- CI/CD integration -- pipeline runs locally via CLI; CI integration is a separate capability
- Multi-model A/B testing -- one provider at a time; comparison testing is out of scope

---

## Related Documents

- [Analysis](./analysis.md) -- problems driving each task
- [Architecture](./architecture.md) -- technical design
- [Timeline](./timeline.md) -- status tracking (ONLY place for status)
