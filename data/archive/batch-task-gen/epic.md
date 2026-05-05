---
sidebar_position: 2
---

# 🎯 Batch Task Generation – Epic

**Purpose**: Define scope and tasks for generating ~63 missing implementation guides across 10 projects in a single automated batch run.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

The spec-doc pipeline's value proposition is that implementation guides are the institutional memory of every shipped feature. When an agent executes a task, the guide records what was built, why decisions were made, and what was explicitly deferred. Without guides, the next session starts from zero — re-reading code, re-inferring intent, re-discovering constraints that were already solved.

Right now, 10 projects have epics but no task specs. Four of those projects already shipped code (retroactive documentation gap). Two are ready to execute but blocked on missing specs (chain-meta-display, parallel-gen). Four are backlog items that will need specs before any agent can touch them. Generating ~63 task specs manually — running `regen-task.mjs` per-project, monitoring each run, handling failures — is a 3–5 hour operator-attended job. The batch orchestrator turns that into a single command with unattended execution, progress tracking, and automatic retry.

The secondary value is calibration signal. Running 63 specs through the pipeline in one batch produces the largest quality sample yet — review scores and deviation counts across projects will reveal whether the generation prompts are calibrated or need work. The batch summary report surfaces this signal without requiring the operator to grep through 63 individual files.

---

## Scope

### What This Epic Covers

- Scanning `projects/` to discover which projects need task specs generated
- A JSON manifest defining the 10 target projects with category tags and priority ordering
- A batch orchestrator script (`scripts/batch-regen.mjs`) that iterates projects and delegates to `regen-task.mjs --all --parallel 2`
- Real-time progress reporting across all projects (table format, updated per-task completion)
- Failure handling: continue on task/project failure, capture errors, output retry manifest
- Post-batch summary report: specs generated, sizes, review scores, timing, quality distribution

### What This Epic Does NOT Cover

- ❌ Changes to `regen-task.mjs` itself — the batch orchestrator calls it as-is
- ❌ A `--retroactive` flag that injects git diffs as generation context
- ❌ Quality improvements to the generation prompt template (`buildImplementationGuidePrompt`)
- ❌ Automatic agent execution after spec generation
- ❌ UI integration — this is a CLI-only capability
- ❌ Cross-project task interleaving (tasks from different projects running simultaneously)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Project inventory scanner** | None | 2 | 2h | High |
| 2 | **Batch manifest schema and seed data** | None | 1 | 1h | High |
| 3 | **Batch orchestrator script** | 1, 2 | — | 4h | High |
| 4 | **Progress reporting** | 3 | 5 | 2h | High |
| 5 | **Failure recovery and retry manifest** | 3 | 4 | 2h | High |
| 6 | **Batch summary report** | 4, 5 | — | 2h | Medium |

### Task Details

#### Task 1: Project Inventory Scanner

Build a function `scanProjectInventory(projectsDir)` that walks `projects/`, reads each `epic.md`, extracts the task table via `extractTasksFromEpic()`, checks which `task-*.md` or `task-*.v2.md` files exist, and returns a structured inventory: `{ projectId, epicTaskCount, existingSpecCount, missingTaskNums[], category }`. Category is inferred: if any task spec files exist with `.v2.md` suffix, it's likely already been through the pipeline; if no task files exist at all, it's either retroactive (has code commits) or backlog. Output as both a JSON array and a human-readable table to stdout. This function is reusable — the batch orchestrator and the manifest seeder both call it.

#### Task 2: Batch Manifest Schema and Seed Data

Define the manifest schema as a JSON file (`scripts/batch-manifest.json`) with fields: `projectId` (string), `category` (enum: `retroactive | ready | backlog`), `priority` (number, lower = first), `flags` (object: `{ rescan?: boolean, noReview?: boolean, parallel?: number }`), `skip` (boolean, for excluding projects without removing them from manifest). Seed the manifest with the 10 target projects from the braindump, ordered: ready-to-execute first (chain-meta-display, parallel-gen), retroactive second (4 projects), backlog last (4 projects). The manifest is the operator's control surface — they edit it to reorder, skip, or override per-project flags.

#### Task 3: Batch Orchestrator Script

Create `scripts/batch-regen.mjs` that reads the manifest, filters out `skip: true` entries, sorts by `priority`, and iterates projects sequentially. For each project: validate `epic.md` and `architecture.md` exist, spawn `regen-task.mjs --all --parallel {N}` as a child process (default N=2, overridable per-project in manifest), capture stdout/stderr to a per-project log file (`logs/batch-{timestamp}/{projectId}.log`), track exit code and timing. The orchestrator does NOT re-implement wave ordering or prompt assembly — it delegates entirely to `regen-task.mjs`. CLI interface: `node scripts/batch-regen.mjs [--manifest path] [--dry-run]`. The `--dry-run` flag validates the manifest, checks all epics exist, reports planned work (project count, total tasks, estimated time), and exits without calling the API.

#### Task 4: Progress Reporting

Add real-time progress output to the batch orchestrator. Before starting: print the manifest summary table (project, category, task count, flags). During execution: for each project, print a header line when starting, pipe task-level progress from regen-task.mjs stdout (lines matching `✓ Wrote` or `✗` patterns), and print a completion line with timing and task count. After each project: print a running totals line (`[4/10 projects, 28/63 tasks, 2 failed, 47m elapsed]`). Format as a table (per the user's feedback preference). The progress output goes to stderr so stdout remains clean for piping.

#### Task 5: Failure Recovery and Retry Manifest

When a project's `regen-task.mjs` exits non-zero or when individual tasks fail within a project (detected by parsing stdout for `✗` lines), the orchestrator captures the failure, logs it, and continues to the next project. After the batch completes, if any failures occurred, write a retry manifest (`logs/batch-{timestamp}/retry-manifest.json`) containing only the failed projects with their failed task numbers. Support `--retry <path>` flag on `batch-regen.mjs` that reads a retry manifest instead of the default manifest, running only the failed tasks. The retry manifest uses the same schema as the main manifest but adds a `taskNums` array field to scope generation to specific tasks rather than `--all`.

#### Task 6: Batch Summary Report

After all projects complete (or fail), generate a summary report written to `logs/batch-{timestamp}/summary.md`. Contents: batch metadata (timestamp, manifest path, total runtime), per-project results table (project, category, tasks attempted, tasks succeeded, tasks failed, total time, avg review score), aggregate statistics (total specs generated, total chars written, mean/median review score, score distribution histogram as ASCII), and a quality signal section that flags projects with mean review score below 3.0 or any task with 0 review score as needing prompt attention. If `deviation-report.mjs` is available, include a note pointing the operator to run it against the generated specs for deeper quality analysis.

---

## Success Criteria

- ✅ `node scripts/batch-regen.mjs --dry-run` validates all 10 projects and reports planned work without calling the API
- ✅ `node scripts/batch-regen.mjs` generates task specs for all 10 projects end-to-end with a single command
- ✅ Progress table updates in real-time showing per-project and cross-project status
- ✅ A single project failure does not abort the batch — remaining projects continue
- ✅ Retry manifest is written on failure and `--retry` flag successfully re-runs only failed tasks
- ✅ Summary report includes per-project results, aggregate quality statistics, and flags low-scoring projects
- ✅ Total generated spec count matches expected ~63 (minus any legitimate skips)

---

## Non-Goals

- ❌ Modifying `regen-task.mjs` internals — the orchestrator treats it as a black box
- ❌ Cross-project task interleaving — projects run sequentially to keep logs readable
- ❌ Automatic quality remediation — the summary flags problems, the operator decides what to do
- ❌ Git-diff-aware retroactive generation — deferred until a `--retroactive` flag is justified
- ❌ Persisting batch results to a database — file-based logs are sufficient at this scale

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

