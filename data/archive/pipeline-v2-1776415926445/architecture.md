---
sidebar_position: 3
---

# Pipeline V2 -- Solution Architecture

**Purpose**: Technical design for the five automated pipeline stages that replace manual operator interventions.

**Epic Reference**: See [Epic](./epic.md) for scope, task breakdown, and success criteria.

---

## Architecture Overview

Pipeline V2 inserts four new stages into the existing task-generation flow and adds one standalone observability script. The current flow is:

```
[Load context] --> [Build prompt] --> [Call LLM] --> [Write file]
```

The V2 flow becomes:

```
[Load context + caveats] --> [Rescan if foundation] --> [Build prompt] --> [Call LLM] --> [Strip preamble] --> [Review (advisory)] --> [Write file]
```

The deviation parser operates independently, reading git history after executor runs to produce a quality signal.

All changes live in two files (`server.js`, `scripts/regen-task.mjs`) plus one new script (`scripts/deviation-report.mjs`). No new dependencies. No new endpoints. The pipeline's shape stays the same -- prompt in, spec out -- with better context going in and cleaner output coming out.

---

## Design Principles

| Principle | Application in Pipeline V2 |
|-----------|---------------------------|
| Adapter (every service) | Caveats loading uses the same `readOrEmpty()` + block-builder pattern as builder/principles/codebase/references. No new abstraction -- same interface, new content. |
| Not-yet-built is right for infrastructure nobody asked for | Advisory review, not blocking gate. Stdout parser, not dashboard. Each can be promoted when a second consumer appears. |
| Judgment-calls-per-commit is the spec-quality metric | The deviation parser directly measures this metric. The auto-review reduces it proactively. |
| Structural tests -- add as encountered | Each task adds tests for the specific behavior it introduces: preamble regex, caveats resolution order, rescan trigger logic, review append format, deviation parsing. |

---

## System Boundaries

### What Pipeline V2 Touches

- `scripts/regen-task.mjs` -- preamble strip, caveats resolution, rescan flag, review append (Tasks 1-4)
- `server.js` -- caveats loading in `generate-spec` endpoint (Task 2)
- `scripts/deviation-report.mjs` -- new standalone script (Task 5)
- Test files for each task

### What Pipeline V2 Does NOT Touch

- `server.js` AI provider layer (`cliProvider`, `remoteProvider`, `aiAdapter`) -- unchanged
- `server.js` endpoints other than `generate-spec` -- `review`, `lint-braindump`, `scan` are consumers, not modified
- Angular frontend components -- no UI changes in this epic
- `principles.md`, `builder.md` -- read-only context files, not modified
- The `buildImplementationGuidePrompt()` function's template structure -- only the context blocks it receives change

---

## Component Design

### Task 1: Preamble Strip

**Purpose**: Enforce Executor Protocol rule that generated specs start with `#`.

**Location**: `scripts/regen-task.mjs`, after LLM response is received, before file write.

**Pattern**: Single regex applied to the raw LLM output text. Drop everything before the first line that starts with `# ` (heading level 1 with space). If the output already starts with `#`, the regex is a no-op.

```
Input:  "I now have enough context...\n\n# Task 3: Foo\n..."
Output: "# Task 3: Foo\n..."
```

**Edge cases**: Output with no `# ` heading at all (malformed LLM response) -- log a warning, write the raw output anyway, let the review stage flag it.

### Task 2: Caveats Injection

**Purpose**: Inject environment-specific quirks into every task-generation prompt.

**Resolution order**:
1. `projects/{projectId}/caveats.md` (per-project)
2. `caveats.md` at repo root (global fallback)
3. Empty string (no caveats -- block omitted from prompt)

**In `regen-task.mjs`**: The `getCaveatsBlock()` helper already exists. Change `main()` to try project-level first, then fall back to repo root. Currently it only reads from repo root.

**In `server.js`**: The `generate-spec` endpoint does not load caveats at all. Add a `getCaveats(projectId)` helper that follows the same resolution order and inject the block into the generate-spec prompt alongside builder and principles.

**Context block format** (matches existing convention):
```
## KNOWN ENVIRONMENT CAVEATS (hard-won from prior executor runs -- apply these)
{content of caveats.md}
```

### Task 3: Auto-Rescan

**Purpose**: Keep `codebase.md` fresh by rescanning after foundation tasks ship.

**Trigger**: `--rescan` CLI flag on `regen-task.mjs`. The script can also auto-detect foundation tasks: parse the epic's task table, identify tasks where the current task's dependencies include a task that other tasks also depend on (i.e., a task that is a dependency of multiple downstream tasks).

**Mechanism**: HTTP POST to `${API_BASE}/api/ai/text/scan` with `{ workspacePath }`. The scan endpoint already exists and writes `codebase.md`. After the scan completes, the script proceeds to load the freshly written `codebase.md` for prompt assembly.

**Decision**: Rescan after foundation tasks only, not after every task. Session evidence: 18 stale-path deviations came from tasks depending on Task 1's token output changes; parallel siblings that did not depend on each other had no stale-context deviations.

**Implementation flow**:
```
regen-task.mjs --rescan <projectId> <taskNum>
  |
  +--> Parse epic task table
  +--> If --rescan flag OR task depends on a foundation task:
  |      POST /api/ai/text/scan { workspacePath }
  |      Wait for completion
  |      Log: "Rescanned codebase.md (N chars)"
  |
  +--> Load codebase.md (now fresh)
  +--> Continue with prompt assembly
```

### Task 4: Auto-Review

**Purpose**: Append advisory quality review to every generated spec before file write.

**Mechanism**: After the LLM generates a task spec, pipe the output through the existing `/api/ai/text/review` endpoint. The review endpoint already exists and returns dimensional scores. Append the review output as a `## Post-generation Review` section at the end of the generated spec.

**Input to review**: The generated spec text plus the project's architecture and principles as rubric context.

**Output format appended to spec**:
```markdown
---

## Post-generation Review

**Overall**: {score}/5 ({level})

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | {n}/5 | {top issue or "Pass"} |
| Content routing | {n}/5 | {top issue or "Pass"} |
| Pattern application | {n}/5 | {top issue or "Pass"} |
| Rule compliance | {n}/5 | {top issue or "Pass"} |
| Content quality | {n}/5 | {top issue or "Pass"} |
| Usefulness | {n}/5 | {top issue or "Pass"} |

**Top fixes**: {top_3_fixes as bullet list}
```

**Advisory, not blocking**: The executor sees the review section and adapts. The script does not fail on low scores. If future data shows advisory is insufficient, a blocking gate can be added by checking `overall_score` against a threshold before writing.

**Implementation flow**:
```
[LLM generates spec text]
  |
  +--> POST /api/ai/text/review { documents: { "task-spec": specText } }
  +--> Parse review JSON response
  +--> Format as markdown section
  +--> Append to spec text
  +--> Write combined output to file
```

### Task 5: Deviation-Count Parser

**Purpose**: Measure spec quality by parsing executor commit bodies for deviation lines.

**Location**: `scripts/deviation-report.mjs` (new standalone script).

**Format contract**: Executors write one line per deviation in commit bodies:
```
Deviation: <category> -- <description>
```

**Categories** (5 buckets):
- `stale-context` -- spec cited a path/module that no longer exists or has changed
- `UX-silent` -- spec omitted a UX detail the executor had to decide
- `env-gap` -- environment-specific issue the spec did not anticipate
- `commit-drift` -- executor changed commit boundaries vs. the commit plan
- `positive-review-absorption` -- executor incorporated a review finding that improved the output

**Input**: Git repository path + optional branch/range filter.

**Output**: Summary table to stdout:

```
Deviation Report: {epic-name}
Tasks: {N}  Commits: {N}  Total deviations: {N}

| Category               | Count | % of Total |
|------------------------|-------|------------|
| stale-context          |     3 |        25% |
| UX-silent              |     2 |        17% |
| env-gap                |     4 |        33% |
| commit-drift           |     1 |         8% |
| positive-review-absorb |     2 |        17% |

Per-task breakdown:
| Task | Deviations | Avg/Commit | Categories |
|------|------------|------------|------------|
| 1    |          4 |        1.3 | stale-context(2), env-gap(2) |
| 2    |          3 |        0.6 | UX-silent(2), commit-drift(1) |
...
```

**Optional file output**: `--out <path>` flag writes the same table to a markdown file.

**Parsing logic**: `git log --format=%B` piped through a regex: `/^Deviation:\s*(\S+)\s*(?:--|—)\s*(.+)$/gm`. Group 1 is category, group 2 is description. Task number inferred from commit message scope (e.g., `feat(task-3): ...` extracts task 3) or from branch name.

---

## Execution Flow

```
[Phase 1 — Independent, parallel]
   Task 1 (Preamble Strip)
   Task 2 (Caveats Injection)
   Task 3 (Auto-Rescan)
   Task 4 (Auto-Review)

[Phase 2 — Independent]
   Task 5 (Deviation-Count Parser)
```

All five tasks are independent -- no task blocks another. Tasks 1-4 all modify `regen-task.mjs` but touch different functions/stages: Task 1 is post-LLM, Task 2 is pre-prompt context loading, Task 3 is pre-prompt rescan, Task 4 is post-LLM + post-strip. Merge order does not matter as long as each task's changes are in distinct code sections.

Task 5 is a standalone script with no dependency on Tasks 1-4. It can be built at any time.

---

## Design Decisions

| Decision | Choice | Rationale | Trade-offs |
|----------|--------|-----------|------------|
| Advisory vs. blocking review | Advisory (append to spec) | Session data: advisory alone dropped deviations 6.0 -> 3.0. Blocking gate adds latency and requires a threshold that has no empirical basis yet. | Risk: executors might ignore review notes. Mitigation: deviation parser will detect if quality degrades. |
| Per-project caveats from day one | `projects/{id}/caveats.md` -> `caveats.md` fallback | Prevents Bubls-specific quirks leaking into other projects. One extra `readOrEmpty()` call per generation. | Risk: two files to maintain per project. Mitigation: most projects use global only; per-project is opt-in. |
| Rescan after foundation tasks only | Foundation = tasks depended on by multiple downstream tasks | 18 stale-path deviations in UX Revamp came from foundation-dependent tasks, not parallel siblings. Rescanning every task doubles API calls with no observed benefit. | Risk: non-foundation tasks that restructure files could still cause staleness. Mitigation: `--rescan` flag allows manual override. |
| Deviation format: `Deviation: <category> -- <description>` | Structured single-line format | Parseable by regex, human-readable in `git log`, categorizable without NLP. The session used freeform "Deviations:" lines -- standardizing enables automation. | Risk: executors must adopt the new format. Mitigation: the format is specified in the Executor Protocol and in every generated spec's "Deviations Allowed" section. |
| Deviation parser as standalone script | `scripts/deviation-report.mjs` | Follows "not-yet-built" principle -- no dashboard, no DB, no API endpoint until a second consumer appears. Stdout is the UI. | Risk: output format is not machine-readable for future consumers. Mitigation: adding `--json` flag later is trivial. |

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Task generation script | Node.js ESM (`scripts/regen-task.mjs`) | Already exists; all modifications extend it |
| API server | Express (`server.js`) | Already exists; caveats loading added alongside existing context loaders |
| Deviation parser | Node.js ESM (`scripts/deviation-report.mjs`) | Same runtime as regen-task; uses `child_process.execSync` for `git log` |
| Tests | Node.js built-in `node:test` + `assert` | Matches existing test framework in `server.integration.test.js` |
| HTTP client in scripts | `curl` via `execSync` | Already used in `regen-task.mjs` to avoid Node's undici timeout limits |

---

## Related Documents

- [Epic](./epic.md) -- task scope and success criteria
- [Analysis](./analysis.md) -- problems driving each design decision
- [Timeline](./timeline.md) -- status tracking
