# Spec Doc Self-Spec -- Solution Architecture

**Purpose**: Technical design for Spec Doc as it actually exists today -- the Express + Angular + Claude CLI system with 9 system prompts, 4 context blocks, and a 6-stage pipeline.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Spec Doc is a two-process system: an Express server (`server.js`, port 3100) and an Angular 19 SPA (port 4201). The server has two jobs -- persisting project folders as flat markdown files and routing AI requests through system prompts to Claude CLI. The frontend has two jobs -- providing a Monaco editor for markdown editing and rendering previews via marked.js. The product's intellectual property is not in the server framework or the frontend components; it is in the 9 system prompts that encode the constellation methodology. Everything else is plumbing.

```
Angular 19 SPA (port 4201)
  +-- Monaco Editor (markdown editing)
  +-- marked.js Preview (instant render)
  +-- Operation Bar (AI text ops)
  +-- Sidebar (project tree)
  +-- New Project Modal (bootstrap flow)
      |
      | HTTP REST
      v
Express Server (port 3100)
  +-- Project CRUD (/api/projects/*)
  +-- Context Blocks (/api/builder, /api/principles, /api/codebase, /api/references)
  +-- AI Text Ops (/api/ai/text/rewrite, /generate, /iterate)
  +-- Spec Pipeline (/api/ai/text/generate-spec, /review, /lint-braindump, /scan)
  +-- Task Pipeline (/api/ai/implement -- SSE streaming)
  +-- Container Mgmt (/api/container/* -- optional, off by default)
      |
      | stdin/stdout via child_process.spawn
      v
Claude CLI (`claude -p --output-format text`)
```

---

## Design Principles

| Principle | Application in Spec Doc |
|-----------|------------------------|
| **Prompts are code** | The 9 system prompts in `server.js` are the product's core logic. They are iterated, tested, and versioned like algorithms. |
| **Methodology scales, tools don't** | The value is in the document hierarchy (Analysis -> Epic -> Architecture -> Implementation), not in the Express server or Angular app. |
| **Context completeness** | Every generative prompt receives all available context blocks. Missing context produces speculative output; complete context produces port-first output. |
| **Port before invent** | When reference code exists, the pipeline produces guides that port it. Without references, models invent type systems and DB tables the task doesn't need. |
| **Each doc has ONE job** | Status only in Timeline. Design only in Architecture. Scope only in Epic. Content routing violations are scored as defects by the Review prompt. |
| **Adapter pattern for AI** | Three providers (cli, remote, mock) behind one interface. Tests use mock. Dev uses cli. Future prod uses remote. |

---

## System Boundaries

### Included

- Express server: project CRUD, context block persistence, AI routing, prompt assembly
- Angular frontend: Monaco editor, preview, operation bar, project sidebar, bootstrap modal
- Claude CLI: AI execution via `claude -p --output-format text` (spawned per request)
- 9 system prompts: the product logic
- 4 context blocks: builder.md, principles.md, codebase.md, references.md
- Project persistence: flat folder of markdown files under `projects/`

### Excluded

- Authentication / authorization (single-operator tool)
- Database (all state is flat files)
- Deployment infrastructure (runs locally)
- Container execution (endpoints exist, off by default, no integration tests)

---

## The 9 System Prompts (Product Core)

These prompts ARE the product. They encode the constellation methodology, quality rubrics, and context-block injection patterns.

### Prompt 1: Rewrite

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/rewrite` |
| **Location** | `server.js` L617, delegated to `aiAdapter.rewrite()` |
| **Purpose** | Atomic text transformation: given text + instruction, return rewritten text |
| **Inputs** | `text` (string), `instructions` (string) |
| **Context blocks** | None -- operates on raw text |
| **Output** | `{ text, latencyMs }` |
| **Prompt complexity** | Low -- the instruction IS the prompt |

### Prompt 2: Generate

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/generate` |
| **Location** | `server.js` L635, delegated to `aiAdapter.generate()` |
| **Purpose** | Freeform text generation from a prompt |
| **Inputs** | `prompt` (string), `tone` (optional string) |
| **Context blocks** | None -- caller assembles full prompt |
| **Output** | `{ text, latencyMs }` |
| **Prompt complexity** | Low -- passthrough |

### Prompt 3: Iterate

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/iterate` |
| **Location** | `server.js` L656 |
| **Purpose** | Rewrite a spec by merging base structure with user's current version |
| **Inputs** | `baseSpec` (string), `currentContent` (string) |
| **Context blocks** | Builder profile injected if available |
| **Output** | `{ text, latencyMs }` |
| **Key instructions** | "COMPLETE NEW version", "similar in LENGTH to base spec", "Do not summarize" |
| **Known gap** | No quality gate -- output returned raw (see [Analysis](./analysis.md)) |

### Prompt 4: Generate-Spec (The Bootstrap Prompt)

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/generate-spec` |
| **Location** | `server.js` L706-L998 |
| **Purpose** | Transform a braindump into a complete 5-file capability folder |
| **Inputs** | `input` (braindump string) |
| **Context blocks** | Builder profile, Architecture principles |
| **Output** | `{ text, latencyMs }` -- raw text with `===FILE: name.md===` markers |
| **Files generated** | `spec-index.md`, `analysis.md`, `epic.md`, `architecture.md`, `timeline.md` |
| **Key instructions** | Templates for each file embedded in prompt. Each file 300+ words. Tasks specific and actionable. |
| **Prompt size** | ~290 lines -- the largest single prompt |
| **Evolution** | Started as the only generative prompt. Builder/principles injection added later. File markers (`===FILE:===`) chosen over JSON for reliability. |

### Prompt 5: Review (Quality Gate)

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/review` |
| **Location** | `server.js` L1013-L1084 |
| **Purpose** | Score generated documents against 6 quality dimensions |
| **Inputs** | `documents` (object: `{ analysis, epic, architecture }`) |
| **Context blocks** | None -- documents ARE the input |
| **Output** | JSON: `{ dimensions: { structural_completeness, content_routing, pattern_application, rule_compliance, content_quality, usefulness }, overall_score, level, top_3_fixes }` |
| **Scoring** | 1-5 per dimension. Levels: gold / silver / bronze / needs_work |
| **Relationship to rubric** | The 6 dimensions overlap with but do not exactly match `specs/quality-rubric.md`. The rubric scores per-document (Analysis 14pts, Epic 22pts, etc.); the review prompt scores per-dimension across all documents. |

### Prompt 6: Lint-Braindump (Pre-flight)

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/lint-braindump` |
| **Location** | `server.js` L1111-L1188 (function `buildBraindumpLintPrompt`) |
| **Purpose** | Structural pre-flight on braindump before bootstrap. Flags gaps that will produce bad specs. |
| **Inputs** | `braindump` (string) |
| **Context blocks** | Architecture principles, References (truncated to 3000 chars) |
| **Output** | JSON: `{ readiness, length, flags[5], top_3_fixes }` |
| **5 lint dimensions** | `port_sources`, `out_of_scope_explicit`, `invents_vs_cites`, `consumers_named`, `principles_contradicted` |
| **Readiness thresholds** | ready (5/5 pass), ready_with_caveats (3-4 pass), needs_rewrite (2+ fail) |
| **Origin** | Born from reflection `2026-04-16-references-port-discipline-epic2.md` -- the braindump lint was proposed as improvement target #6 and shipped same day. |

### Prompt 7: Scan (Codebase Context)

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/text/scan` |
| **Location** | `server.js` L1195-L1304 (function `buildScanPrompt`) |
| **Purpose** | Walk a filesystem, send tree + file heads to LLM, get back a structured `codebase.md` |
| **Inputs** | `workspacePath` (filesystem path) |
| **Context blocks** | None -- this prompt CREATES a context block |
| **Output** | Raw markdown persisted to `codebase.md` |
| **Key instructions** | "respond with markdown text only -- no tool calls, no approval prompts" (learned: CLI intercepts write-intent prompts) |
| **Hardening** | `looksLikeCliRefusal()` detects tool-permission interceptions and returns 502 instead of persisting garbage |

### Prompt 8: Implement (Task Execution)

| Attribute | Value |
|-----------|-------|
| **Endpoint** | `POST /api/ai/implement` |
| **Location** | `server.js` L1311-L1516 |
| **Purpose** | Execute a task from a capability spec via Claude CLI with SSE streaming |
| **Inputs** | `taskNum`, `taskName`, `projectContext` (specIndex, epic, architecture) |
| **Context blocks** | Builder profile, project's spec-index + epic + architecture |
| **Output** | SSE stream: `status`, `output` (chunks), `error`, `done` events |
| **Execution modes** | Container (sandboxed Docker), Local (direct CLI spawn), Mock (instant test response) |
| **Key instructions** | "Read the architecture for design patterns", "Follow coding standards", "Report files created/modified" |

### Prompt 9: Implementation Guide (Task-Spec Generator)

| Attribute | Value |
|-----------|-------|
| **Location** | `src/app/services/implementation-guide.service.ts` (canonical), `scripts/regen-task.mjs` (drifted copy) |
| **Purpose** | Generate an executor-ready implementation guide for a single task |
| **Inputs** | Task metadata (num, name, effort), epic content, architecture content, prior tasks summary |
| **Context blocks** | All 6: Builder, Principles, Codebase, References, Prior Tasks, Epic+Architecture |
| **Output** | 10-section markdown guide |
| **10 sections** | Context, Pre-flight, Files, Implementation Steps, Tests, Commit Plan, Verification, Rollback, Deviations Allowed, Out of Scope |
| **Hard rules** | No personal paths, no test stubs, no "etc.", no side-effects without approval markers, PORT before invent, adapter boundary for shared infra |
| **Output format rule** | "First character of your answer is `#`" -- kills CLI preamble leak |
| **Template drift** | `regen-task.mjs` has a copy that drifts. Missing: trade-offs sub-list, out-of-scope section, first-char-# rule, PORT-before-invent rule. See [Analysis](./analysis.md) Task 8. |
| **Evolution** | Most iterated prompt. Grew from 5 sections to 10 across executor-meta and references-port-discipline reflections. |

---

## The 4 Context Blocks

Context blocks are persisted flat files that are injected into prompts to provide project-specific knowledge. Each follows the same pattern: GET/PUT REST endpoint, flat `.md` file on disk, service class on the frontend, conditional injection into prompt assembly.

| Block | File | Endpoint | Injected Into | Purpose |
|-------|------|----------|---------------|---------|
| **Builder** | `builder.md` | `GET/PUT /api/builder` | generate-spec, iterate, implement, impl-guide | Who you are: tech stack preferences, experience level, constraints |
| **Principles** | `principles.md` | `GET/PUT /api/principles` | generate-spec, lint-braindump, impl-guide | How you build: non-negotiable architectural patterns (ELA patterns, adapter rule, etc.) |
| **Codebase** | `codebase.md` | `GET/PUT /api/codebase` | impl-guide | What the target repo looks like: feature modules, shared services, patterns in use |
| **References** | `references.md` | `GET/PUT /api/references` | lint-braindump, impl-guide | Cross-project code to port from: the source material that triggers port-first behavior |

**Pattern**: If a 5th context dimension emerges (API contracts, regulatory requirements, etc.), the plumbing template is proven: new block = ~150 lines of parallel code (endpoint + service + prompt injection + tests).

**Key insight from reflections**: Context completeness is a design dimension. When the LLM can see the port sources, it ports (-47% guide size, -86% speculative types). When it cannot, it invents. Every missing context block produces speculative output.

---

## The Pipeline (End-to-End Flow)

```
Braindump (user text input)
    |
    v
[1] LINT (/api/ai/text/lint-braindump)
    |  Inputs: braindump + principles + references
    |  Output: { readiness, flags[5], top_3_fixes }
    |  Gate: "ready" or "ready_with_caveats" to proceed
    |
    v
[2] GENERATE (/api/ai/text/generate-spec)
    |  Inputs: braindump + builder + principles
    |  Output: 5 files (spec-index, analysis, epic, architecture, timeline)
    |  Parsing: ===FILE: name.md=== markers split into separate files
    |
    v
[3] REVIEW (/api/ai/text/review)
    |  Inputs: generated documents (analysis, epic, architecture)
    |  Output: 6-dimension scores + top_3_fixes
    |  Gate: "gold" or "silver" level to proceed
    |
    v
[4] REGEN-TASK (ImplementationGuideService or regen-task.mjs)
    |  Inputs: task metadata + epic + architecture + all 6 context blocks
    |  Output: 10-section executor-ready implementation guide per task
    |  Loop: one guide per epic task, sequential (next = first without existing guide)
    |
    v
[5] IMPLEMENT (/api/ai/implement)
    |  Inputs: task context (spec-index, epic, architecture) + builder
    |  Output: SSE stream of Claude CLI executing the task
    |  Modes: container / local / mock
    |
    v
[6] DEVIATION ANALYSIS (manual, post-execution)
       Inputs: commit history, implementation guide, diff
       Output: deviation log in commit bodies (prefix: "Deviations:")
       Status: not automated -- executor logs deviations per commit
```

**Key property**: Each stage's output is the next stage's input. Context accumulates: the braindump produces the spec, the spec feeds the task guide, the task guide feeds the executor. Losing context at any stage degrades downstream quality.

---

## Component Design

### Capability 1: Project Management

**Purpose**: CRUD for project folders, flat-file persistence, metadata

**Components**:
- `server.js` L469-L612 -- REST endpoints: list, get, create, update file, delete
- `projects/` directory -- one subfolder per project, each containing markdown files + `project.json`
- `src/app/services/projects.service.ts` -- Angular service wrapping HTTP calls

**Pattern**: No database. Projects are folders. Files are markdown. Metadata is `project.json`. This is deliberately simple -- the product's complexity is in the prompts, not in the persistence layer.

### Capability 2: AI Text Operations

**Purpose**: Atomic text transforms -- rewrite, expand, compress, clarify, generate

**Components**:
- `server.js` L617-L633 -- rewrite endpoint (text + instructions -> transformed text)
- `server.js` L635-L653 -- generate endpoint (prompt -> text)
- `src/app/services/ai.service.ts` -- Angular service with methods for each operation
- `src/app/components/operation-bar/operation-bar.component.ts` -- UI buttons for each operation

**Pattern**: Adapter pattern. Three AI providers: `cliProvider` (Claude CLI via spawn), `remoteProvider` (HTTP to external API), `mockProvider` (instant test responses). Selection via `AI_PROVIDER` env var. The rewrite prompt is the simplest -- the user's instruction IS the prompt. The generate prompt is a passthrough -- the caller assembles the full prompt.

### Capability 3: Spec Bootstrapping

**Purpose**: Braindump to 5-file capability folder

**Components**:
- `server.js` L706-L1006 -- generate-spec endpoint with the 290-line bootstrap prompt
- `server.js` L1013-L1105 -- review endpoint for quality gating
- `server.js` L1111-L1189 -- lint-braindump endpoint for pre-flight
- `src/app/components/new-project/new-project.component.ts` -- modal that orchestrates: braindump input -> lint -> generate -> parse files -> review -> persist

**Pattern**: The generate-spec prompt embeds templates for all 5 files with `===FILE: name.md===` markers. The frontend splits the output on these markers and persists each file separately. The review prompt scores the output against 6 dimensions. The lint prompt checks the braindump for structural completeness before generation begins.

### Capability 4: Task-Spec Generation

**Purpose**: Per-task implementation guides with 6 context blocks

**Components**:
- `src/app/services/implementation-guide.service.ts` -- canonical prompt template (10-section guide)
- `scripts/regen-task.mjs` -- CLI script with drifted copy of same prompt
- Frontend: "Generate Next Task" button in sidebar triggers `generateNextTask()`

**Pattern**: The prompt injects up to 6 context blocks (builder, principles, codebase, references, prior tasks, epic+architecture). Each block is conditional -- if the context is empty, the block is omitted. The output is a 10-section executor-ready guide with hard rules (no personal paths, no test stubs, PORT before invent).

### Capability 5: Quality Gating

**Purpose**: Lint (pre-flight) + Review (post-generation) + Deviation logging (post-execution)

**Components**:
- `server.js` L1111-L1189 -- lint-braindump (5-dimension structural check)
- `server.js` L1013-L1105 -- review (6-dimension quality scoring)
- Manual: deviation logging in commit bodies (not automated)

**Pattern**: Lint is a gate before generation. Review is a gate after generation. Deviation logging is a convention (not enforced by code): executors prefix commit bodies with `Deviations:` when they deviate from the implementation guide. The review prompt's 6 dimensions (structural completeness, content routing, pattern application, rule compliance, content quality, usefulness) are hardcoded and do not exactly match the quality rubric in `specs/quality-rubric.md`.

### Capability 6: Codebase Scanning

**Purpose**: Walk a filesystem, summarize it via LLM, produce `codebase.md`

**Components**:
- `server/walker.js` -- filesystem walker (tree + file heads + entry points)
- `server.js` L1195-L1305 -- scan endpoint with `buildScanPrompt()`
- `looksLikeCliRefusal()` -- guard against CLI tool-permission interceptions

**Pattern**: The walker collects raw data (file tree, first 10 lines of each source file, entry point contents). The prompt asks the LLM to summarize into a structured markdown template (Feature Modules, Shared Services, Entry Points, Dependencies, Patterns in Use). The output is persisted to `codebase.md` and injected into the implementation-guide prompt as the CODEBASE CONTEXT block.

---

## Design Decisions

| Decision | Choice | Rationale | Trade-off |
|----------|--------|-----------|-----------|
| Express over Spring Boot | Express | The original architecture (Spring Boot + GitHub + Docusaurus) was over-engineered. Express + flat files ships in days, not months. Claude CLI is the AI backend -- no Java SDK needed. | No database, no migrations, no ORM. Limits future multi-user scenarios. |
| Claude CLI over direct API | `claude -p` via spawn | Zero API key management. Uses the operator's existing Claude subscription. Streaming via stdout. | Depends on CLI being installed and configured. No programmatic rate limiting. |
| Flat files over database | `projects/` folder | Zero infrastructure. `ls` lists projects. `cat` reads specs. Git tracks history. | No querying, no relationships, no transactions. Fine for single-operator. |
| Inline prompts over external files | Prompts in `server.js` | Prompts and routing logic are tightly coupled. One file to read, one file to deploy. | Template drift when prompts are duplicated (regen-task.mjs). Extraction proposed -- see [Analysis](./analysis.md). |
| marked.js over Docusaurus | Client-side rendering | Instant feedback (<1ms vs 60s rebuild). 50KB library. Works offline. | No SSR, no SEO. Acceptable for a local-first tool. |
| Monaco over plain textarea | Monaco Editor | Syntax highlighting, multiple cursors, find/replace, bracket matching. Standard for code/markdown editing. | 2MB bundle. Acceptable for a desktop-class web app. |
| `===FILE:===` markers over JSON | Text markers in generate-spec output | More reliable than asking the LLM to produce valid JSON with markdown content embedded as string values. Easier to parse. | Custom parsing logic in frontend. |
| 4 context blocks (not 3, not 5) | builder + principles + codebase + references | Each block serves a distinct purpose. Builder = who. Principles = how. Codebase = what exists. References = what to port. Adding a 5th when needed follows the same ~150-line pattern. | More blocks = longer prompts = higher cost. Conditional injection mitigates: empty blocks are omitted. |
| 10-section implementation guide | Grew from 5 to 10 sections | Each section addresses a failure mode observed in execution: missing pre-flight, missing commit plan, missing rollback, missing out-of-scope boundary, missing deviation rules. | Longer guides = more prompt tokens = higher cost. But shorter guides produce executors that design instead of transcribe. |

---

## Key Learnings from Reflections

These architectural decisions were extracted from the 13 reflections in `specs/reflections/`. Each is a permanent principle, not a session artifact.

| Learning | Source Reflection | Architectural Consequence |
|----------|-------------------|--------------------------|
| Port-first beats invent-first | `2026-04-16-references-port-discipline-epic2.md` | References context block + "PORT before invent" hard rule in impl-guide prompt |
| Structural tests pin architecture | `2026-04-16-task-2-executor-as-typist.md` | Adapter boundary rule in impl-guide prompt + grep-based structural test pattern |
| Context-completeness is a design dimension | `2026-04-16-references-port-discipline-epic2.md` | Every generative prompt receives all available context blocks |
| The braindump is a first-class input | `2026-04-16-references-port-discipline-epic2.md` | Lint-braindump endpoint: structural pre-flight before bootstrap |
| Template drift is a recurring problem | `2026-04-16-references-port-discipline-epic2.md` | Extraction of `ImplementationGuideService` as single source of truth (script still drifted) |
| "Executor as typist" is the quality signal | `2026-04-16-task-2-executor-as-typist.md` | If the executor designs, the spec was underspecified. If the executor transcribes, the spec was correct. |
| CLI refusal detection | `2026-04-16-references-port-discipline-epic2.md` | `looksLikeCliRefusal()` guard on scan endpoint |
| System prompts are code | `2026-03-31-the-meta-vision.md` | Prompts need versioning, testing, iteration -- same discipline as algorithms |

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Angular 19, TypeScript, standalone components, OnPush | Consistent with constellation. Standalone components, no NgModules. |
| **Editor** | Monaco Editor | Industry-standard markdown/code editor. Syntax highlighting, multi-cursor. |
| **Preview** | marked.js | Client-side markdown rendering. <1ms vs 60s for SSG rebuild. |
| **Backend** | Express.js (Node.js), port 3100 | Minimal server. Routes + prompt assembly + file persistence. |
| **AI** | Claude CLI (`claude -p --output-format text`) | Zero API key management. Uses operator's Claude subscription. |
| **Persistence** | Flat markdown files in `projects/` | Zero infrastructure. Git-trackable. `ls` lists projects. |
| **Context blocks** | `builder.md`, `principles.md`, `codebase.md`, `references.md` | Persisted flat files, injected into prompts at assembly time. |
| **Testing** | `node:test` + `assert` (server), Jasmine (Angular) | Server tests: 72 passing. Protocol assertions for every pipeline feature. |
| **Container** | Docker (optional, `CONTAINER_MODE=true`) | Sandboxed execution. Off by default. Endpoints exist but untested. |

---

## Execution Flow

```
[Phase 1: Context Setup]
   builder.md ──┐
   principles.md ─┤── Persisted flat files, loaded at startup
   codebase.md ──┤     or refreshed via PUT endpoints
   references.md ─┘

[Phase 2: Braindump -> Spec]
   User input ──→ Lint ──→ Generate-Spec ──→ Review
                   │              │               │
                   │              │               v
                   │              │         Score + fixes
                   │              v
                   │        5 files parsed
                   v            from markers
              Readiness gate

[Phase 3: Task Guides]
   Epic tasks ──→ Implementation Guide Service
                   │
                   │ Injects 6 context blocks
                   v
              10-section guide per task

[Phase 4: Execution]
   Task guide ──→ Implement (SSE)
                   │
                   │ Claude CLI spawned
                   v
              Streaming output + done event
```

---

## Known Gaps

### Builder/Principles Onboarding Gap

**Problem**: `builder.md` and `principles.md` are flat files loaded at server startup and injected into every generative prompt. They are the single largest factor in output quality -- without builder context, the LLM guesses the operator's stack preferences; without principles, it invents patterns instead of following established ones. But a new operator cloning the repo finds no `builder.md` (gitignored, personal), an example file (`builder.example.md`) with no instructions on how to populate it, and a `principles.md` that contains Sam's ELA-derived patterns which may not apply to their codebase.

**Current state**: The operator must know to:
1. Copy `builder.example.md` to `builder.md` and customize it
2. Review `principles.md` and adapt it to their own architectural patterns
3. Optionally populate `codebase.md` by running a scan against their workspace
4. Optionally populate `references.md` with cross-project code to port from

There is no first-run check, no setup wizard, and no error message when these files are missing. The pipeline silently produces lower-quality output.

**Impact**: First-run output quality is degraded. The operator does not know output is degraded because there is no baseline comparison. They may conclude the tool does not work well, when in fact the tool was never configured.

**Proposed solutions** (in order of effort):

1. **Startup warning** (minimal, ~10 lines): On server boot, check if `builder.md` exists. If not, log a prominent warning: `[SETUP] No builder.md found. Copy builder.example.md to builder.md and customize. See CLAUDE.md for details. Output quality will be degraded without it.` Same check for `principles.md`. This is the minimum viable fix -- it surfaces the gap without adding UI or CLI complexity.

2. **CLI setup command** (moderate, ~50 lines): `npm run setup` that interactively prompts for stack, role, and preferences, then writes `builder.md`. Could also prompt for workspace path and run the initial codebase scan. Follows the pattern of `npm init`.

3. **First-run modal** (more effort, ~150 lines): When the Angular app loads and detects empty builder/principles via GET endpoints, show a setup modal before allowing spec generation. Mirrors the existing builder-profile editor modal but triggers automatically on first visit.

**Recommendation**: Start with option 1 (startup warning). It is zero-UI, zero-dependency, and immediately surfaces the gap. Upgrade to option 2 when a second operator actually clones the repo.

### Iterate-without-Review Gap

The `/api/ai/text/iterate` endpoint returns raw LLM output with no quality gate. All other generative endpoints in the pipeline have review steps: `generate-spec` is followed by the review prompt (6-dimension scoring), `regen-task.mjs` auto-reviews each generated spec. But `iterate` -- which rewrites a spec by merging base structure with user's current version -- returns the output directly. This means an operator can iterate a spec into a degraded state without any signal.

**Current mitigation**: None. The operator must manually review iterated output.

**Proposed fix**: Optionally pipe iterate output through the review prompt before returning. Add a `review: boolean` flag to the iterate request body (default `false` for backward compatibility, `true` when called from the pipeline).

### Container Integration Gap

Container execution endpoints exist (`/api/container/*`) but have no integration tests and `CONTAINER_MODE` is off by default. The endpoints were added as scaffolding for sandboxed task execution but have not been validated end-to-end. What would need to be true for container mode to be production-ready:

1. Integration tests covering container lifecycle (create, exec, destroy)
2. Volume mount validation (workspace and projects directories accessible)
3. Claude CLI available inside the container
4. Timeout and resource limit enforcement
5. Error propagation from container to SSE stream

This is documented-as-is, not a blocker for current operation.

---

## Related Documents

- [Epic](./epic.md) -- Task scope and success criteria
- [Analysis](./analysis.md) -- Problems driving this work
- [Timeline](./timeline.md) -- Status tracking (ONLY place for status)
- [Spec Index](./spec-index.md) -- Entry point
- [Quality Rubric](../../specs/quality-rubric.md) -- Scoring criteria for generated documents
- [Product Thesis](../../specs/spec-doc-spec.md) -- Why Spec Doc exists
