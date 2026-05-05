---
sidebar_position: 3
---

# 🏗️ Batch Task Generation – Solution Architecture

**Purpose**: Technical design for the cross-project batch orchestration layer.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

The batch orchestrator is a single Node.js script (`scripts/batch-regen.mjs`) that sits above the existing `regen-task.mjs` without modifying it. The architecture follows a strict delegation pattern: the orchestrator manages project sequencing, progress tracking, and failure recovery, while all prompt assembly, wave ordering, API calls, and spec writing remain inside `regen-task.mjs`. This means the batch layer has zero coupling to the generation prompt, the review endpoint, or the codebase scanning logic — it only depends on `regen-task.mjs`'s CLI interface and stdout conventions.

The data flow is:

```
batch-manifest.json → batch-regen.mjs → [for each project] → regen-task.mjs --all --parallel 2
                                                                      ↓
                                                              projects/{id}/task-*.v2.md
                                                                      ↓
                                                          logs/batch-{ts}/summary.md
```

The orchestrator spawns `regen-task.mjs` as a child process (not an import) so that each project run gets a clean Node.js process with independent memory. This avoids accumulating context files in memory across 10 projects and matches how an operator would run the commands manually.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Delegation over reimplementation | The orchestrator never touches prompt assembly, API calls, or spec writing — it spawns `regen-task.mjs` as a subprocess and parses its stdout |
| Sequential projects, parallel tasks | Projects run one at a time to keep logs readable; within each project, `--parallel 2` handles task-level concurrency via the existing wave grouper |
| Fail-forward | A project failure is captured and logged, not propagated — the batch continues to the next project. Retry is a separate pass |
| File-based state | Manifest, logs, retry manifest, and summary are all JSON/Markdown files. No database, no in-memory state surviving process boundaries |
| Operator control surface | The manifest is the single point of control — project order, per-project flags, skip toggles. The operator edits JSON, not code |

---

## Component Design

### Task 1: Project Inventory Scanner

**Purpose**: Discover which projects have epics without complete task spec coverage.

**Components**:
- `scripts/batch-regen.mjs` — `scanProjectInventory(projectsDir)` function (exported for reuse)
- Reads: `projects/*/epic.md`, `projects/*/task-*.md`, `projects/*/task-*.v2.md`

**Patterns**: Reuses `extractTasksFromEpic()` from `regen-task.mjs` (imported as ESM). Walks `projects/` with `fs.readdir`, filters for directories containing `epic.md`, and compares the task table count against existing task file count. Returns `Array<{ projectId, epicTaskCount, existingSpecCount, missingTaskNums, hasArchitecture }>`.

**Key decision**: Import `extractTasksFromEpic` rather than re-implementing the regex. This couples the scanner to regen-task.mjs's export, but the alternative (duplicating the parser) is worse — a task table format change would need two fixes.

### Task 2: Batch Manifest Schema and Seed Data

**Purpose**: Define the operator-controlled project list with per-project configuration.

**Components**:
- `scripts/batch-manifest.json` — the manifest file
- `scripts/batch-regen.mjs` — `loadManifest(path)` and `validateManifest(manifest)` functions

**Schema**:
```json
{
  "version": 1,
  "projects": [
    {
      "projectId": "chain-meta-display-...",
      "category": "ready",
      "priority": 1,
      "flags": { "parallel": 2, "rescan": false, "noReview": false },
      "skip": false
    }
  ]
}
```

**Validation rules**: `projectId` must match a directory in `projects/`; that directory must contain `epic.md` and `architecture.md`; `category` must be one of `retroactive | ready | backlog`; `priority` is a positive integer (lower = first); `flags.parallel` is clamped to 1–3.

### Task 3: Batch Orchestrator Script

**Purpose**: Sequential project iteration with child process delegation.

**Components**:
- `scripts/batch-regen.mjs` — `runBatch(manifest, options)` main loop
- Child process: `node scripts/regen-task.mjs {projectId} --all --parallel {N} [--rescan] [--no-review]`
- Output: `logs/batch-{timestamp}/{projectId}.log` per project

**Patterns**: Uses `child_process.spawn` (not `exec`) to stream stdout/stderr in real-time for progress parsing. Each project spawn inherits `SPEC_DOC_API` env var so the orchestrator respects the same API base URL. The `--dry-run` flag short-circuits before spawning any child processes — it runs the inventory scanner, cross-references the manifest, and prints a planned-work table.

**Process lifecycle per project**:
```
1. Print "[Project N/10] {projectId} ({category}) — {taskCount} tasks"
2. Spawn: node scripts/regen-task.mjs {projectId} --all --parallel {N}
3. Stream stdout → parse for progress lines (✓ Wrote, ✗ error, ── Task ──)
4. Stream stderr → capture for error log
5. On exit: record { projectId, exitCode, duration, tasksSucceeded, tasksFailed }
6. Write project log to logs/batch-{ts}/{projectId}.log
7. Update running totals
```

**Child process timeout**: 15 minutes per project (generous upper bound: 8 tasks × 2 minutes each at concurrency 2 ≈ 8 min, plus rescan overhead). Killed with SIGTERM on timeout, recorded as failure.

### Task 4: Progress Reporting

**Purpose**: Real-time cross-project progress visibility.

**Components**:
- `scripts/batch-regen.mjs` — `ProgressReporter` class
- Output: stderr (so stdout is clean for piping)

**Format** (table per user preference):
```
┌─────────────────────────────────┬──────────┬───────┬────────┬─────────┐
│ Project                         │ Category │ Tasks │ Status │ Time    │
├─────────────────────────────────┼──────────┼───────┼────────┼─────────┤
│ chain-meta-display-...          │ ready    │  5/5  │ ✓ done │ 4m12s   │
│ parallel-gen-1776452567763      │ ready    │  3/6  │ ▶ run  │ 2m30s   │
│ text-chains-1776379250140       │ retro    │  0/8  │ · wait │ —       │
│ ...                             │          │       │        │         │
├─────────────────────────────────┼──────────┼───────┼────────┼─────────┤
│ Total                           │          │ 8/63  │        │ 6m42s   │
└─────────────────────────────────┴──────────┴───────┴────────┴─────────┘
```

**stdout parsing**: The reporter watches child process stdout for these patterns from `regen-task.mjs`:
- `✓ Wrote projects/{id}/task-{n}-...` → increment task success counter
- `✗` prefix → increment task failure counter
- `── Task ──` → update "currently generating" display
- `← Done in` → capture per-task timing

### Task 5: Failure Recovery and Retry Manifest

**Purpose**: Graceful degradation and targeted retry of failed tasks.

**Components**:
- `scripts/batch-regen.mjs` — `writeRetryManifest(failures, outputPath)` function
- `logs/batch-{timestamp}/retry-manifest.json` — retry manifest file

**Retry manifest schema** (extends base manifest):
```json
{
  "version": 1,
  "retryOf": "logs/batch-2026-04-17T1430/",
  "projects": [
    {
      "projectId": "text-chains-1776379250140",
      "category": "retroactive",
      "priority": 1,
      "flags": { "parallel": 1, "rescan": true },
      "taskNums": [4, 6]
    }
  ]
}
```

**Key difference from base manifest**: the `taskNums` array. When present, the orchestrator passes individual task numbers to `regen-task.mjs` instead of `--all`. Retry runs also default to `parallel: 1` (conservative — the failure may have been concurrency-related) and `rescan: true` (the codebase may have changed since the original run).

**Failure detection**: Parse child process stdout for `✗` lines to identify per-task failures within a project. If the child process exits non-zero without any `✓ Wrote` lines, treat the entire project as failed. If some tasks succeeded and some failed, only the failed tasks go into the retry manifest.

### Task 6: Batch Summary Report

**Purpose**: Post-run quality signal and operational summary.

**Components**:
- `scripts/batch-regen.mjs` — `generateSummaryReport(results, outputPath)` function
- `logs/batch-{timestamp}/summary.md` — Markdown summary report

**Report sections**:
1. **Batch metadata**: timestamp, manifest path, total runtime, API base URL
2. **Per-project results table**: project, category, tasks attempted/succeeded/failed, runtime, avg review score
3. **Aggregate statistics**: total specs, total chars, mean/median review score
4. **Quality flags**: projects with mean score < 3.0, tasks with score 0, projects where >50% of tasks failed
5. **Next steps**: pointer to `deviation-report.mjs` for deeper analysis, pointer to retry manifest if failures occurred

**Review score extraction**: Parse the `##### Post-generation review (auto)` section appended to each generated `.v2.md` file — specifically the `**Overall**: X/5` line. This is post-hoc (reads the written files) rather than real-time (would require modifying regen-task.mjs to emit structured data).

---

## Execution Flow

```
[Phase 1 — Foundation]
   Task 1 (scanner) ──┐
   Task 2 (manifest) ─┤
                       │
[Phase 2 — Core]      ▼
   Task 3 (orchestrator)
          │
[Phase 3 — Polish]    ▼
   Task 4 (progress) ──┐
   Task 5 (retry)    ──┤
                        │
[Phase 4 — Reporting]  ▼
   Task 6 (summary)
```

**Critical path**: Tasks 1+2 → Task 3 → Tasks 4+5 → Task 6. Tasks 1 and 2 are independent and parallel. Tasks 4 and 5 are independent and parallel (both extend Task 3's main loop).

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Child process vs. import | `spawn` child process | Clean memory per project run; matches operator's mental model of running commands; avoids module-level side effects in regen-task.mjs's `main()` |
| Sequential projects | One project at a time | Keeps stdout/logs readable; avoids interleaving progress from different epics; regen-task.mjs's `--parallel` handles intra-project concurrency |
| Stdout parsing vs. structured IPC | Parse stdout patterns | Zero changes to regen-task.mjs required; the `✓ Wrote` and `✗` patterns are stable conventions; adding JSON IPC would require modifying the child script |
| Retry manifest schema | Extends base manifest with `taskNums` | Reuses validation and loading code; operator can edit retry manifest same as base manifest; `taskNums` is the only addition needed to scope retries |
| Log directory structure | `logs/batch-{ISO-timestamp}/` | Self-documenting; naturally sorted; one directory per batch run prevents overwriting; operator can `ls logs/` to see all runs |
| Review score extraction | Post-hoc file parsing | Avoids modifying regen-task.mjs; the `##### Post-generation review` section is already written to every `.v2.md` file; reading it after-the-fact is simpler than adding structured output |
| Progress to stderr | `process.stderr.write` | Keeps stdout clean for piping (e.g., `batch-regen.mjs | tee batch.log`); matches Unix convention for status output |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

