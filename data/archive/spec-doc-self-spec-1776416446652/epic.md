# Spec Doc Self-Spec -- Epic

**Purpose**: Define scope and tasks for documenting Spec Doc in its own format.

**Source Analysis**: See [Analysis](./analysis.md) for the 12 issues driving this work.

---

## Business Value

Spec Doc's value proposition is that specifications are the source of truth and the methodology scales. But the product itself violates both claims: its core logic (9 system prompts in `server.js`) is undocumented, its pipeline chain exists only in conversation history, and its architecture doc describes a superseded Spring Boot stack. The product that generates capability folders does not have a capability folder for itself.

Self-speccing delivers three concrete outcomes. First, **onboarding**: a new operator can open `spec-index.md` and understand what the product does, how it works, and where to find each piece, without reading all 1,600 lines of `server.js`. Second, **prompt iteration discipline**: documenting the 9 prompts as an architectural inventory makes each prompt's purpose, inputs, outputs, and evolution history visible -- which is a prerequisite for the prompt extraction that eliminates template drift between `ImplementationGuideService` and `regen-task.mjs`. Third, **methodology credibility**: if Spec Doc cannot spec itself, the methodology it encodes for others is incomplete. Eating the dog food proves the food is edible.

The scope is documentation and lightweight refactoring. No new user-facing features. No new endpoints. The deliverable is this 5-file capability folder plus the prompt inventory and pipeline flow documentation embedded in the architecture doc.

---

## Scope

### What This Epic Covers

- Creating the 5-file self-spec capability folder (spec-index, analysis, epic, architecture, timeline)
- Documenting all 9 system prompts: purpose, inputs, outputs, context-block injection points
- Documenting the pipeline chain: braindump -> lint -> generate-spec -> review -> regen-task -> implement -> deviation
- Documenting the 4 context blocks (builder, principles, codebase, references) as an architectural pattern
- Documenting design decisions: why Express over Spring Boot, why Claude CLI over direct API, why inline prompts (today) vs extracted prompts (proposed)
- Capturing key learnings from the 13 reflections as architectural decisions
- Resolving the open question on prompt extraction (recommendation + migration path)

### What This Epic Does NOT Cover

- Building new features or endpoints -- this is documentation, not development
- Rewriting the existing `specs/` philosophy documents -- they remain as historical artifacts
- Implementing prompt extraction -- Task 9 recommends it; the actual extraction is a follow-up epic
- Multi-capability folder support (the hierarchy-definition.md vision) -- future product work
- Container orchestration redesign -- documented as-is, not redesigned
- Quality rubric automation (scoring in CI) -- documented as a gap, not built

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Write spec-index.md** | None | 2 | 1 hour | High |
| 2 | **Write analysis.md** | None | 1 | 2 hours | High |
| 3 | **Document prompt inventory** | None | 1, 2 | 3 hours | High |
| 4 | **Document pipeline flow** | 3 | -- | 2 hours | High |
| 5 | **Write architecture.md** | 3, 4 | -- | 4 hours | High |
| 6 | **Distill reflections into architecture decisions** | 5 | 7 | 2 hours | High |
| 7 | **Wire quality rubric references into architecture** | 5 | 6 | 1 hour | Medium |
| 8 | **Document template drift problem and extraction plan** | 3 | -- | 1 hour | Medium |
| 9 | **Write prompt extraction migration path** | 5, 8 | -- | 2 hours | Medium |
| 10 | **Document builder/principles onboarding gap** | 5 | 11 | 1 hour | Low |
| 11 | **Document iterate-without-review gap** | 5 | 10 | 1 hour | Low |
| 12 | **Document container integration gap** | 5 | -- | 1 hour | Low |
| 13 | **Write timeline.md** | 1-12 | -- | 30 min | High |
| 14 | **Self-review: score this spec set against quality rubric** | 13 | -- | 1 hour | Medium |

### Task Details

#### Task 1: Write spec-index.md
The entry point document for the self-spec. Lists all 6 capabilities, links to each doc, provides the "For Claude Code" prompt template, and cross-references the existing `specs/` documents as historical context.

#### Task 2: Write analysis.md
Document the 12 issues driving this work, grouped by Structural / Knowledge Capture / Operational. Each issue maps to a task. Includes the open question on prompt extraction with arguments for and against.

#### Task 3: Document prompt inventory
Create a comprehensive inventory of all 9 system prompts in `server.js` plus the 1 prompt template in `ImplementationGuideService`. For each: name, endpoint, purpose, inputs (what data it receives), outputs (what it returns), context blocks injected, key instructions/rules embedded, and known evolution history from the reflections.

The 9+1 prompts:
1. **Rewrite** (`/api/ai/text/rewrite`, server.js L617) -- atomic text transform
2. **Generate** (`/api/ai/text/generate`, server.js L635) -- freeform text generation
3. **Iterate** (`/api/ai/text/iterate`, server.js L656) -- rewrite spec using base + current
4. **Generate-Spec** (`/api/ai/text/generate-spec`, server.js L706) -- braindump to 5-file capability folder
5. **Review** (`/api/ai/text/review`, server.js L1013) -- 6-dimension quality scoring
6. **Lint-Braindump** (`/api/ai/text/lint-braindump`, server.js L1111) -- structural pre-flight
7. **Scan** (`/api/ai/text/scan`, server.js L1195) -- filesystem walk to codebase.md
8. **Implement** (`/api/ai/implement`, server.js L1311) -- SSE-streamed task execution via Claude CLI
9. **Implementation Guide** (`ImplementationGuideService`, impl-guide.service.ts) -- 10-section executor-ready guide with 6 context blocks
10. **(Script duplicate)** `regen-task.mjs` -- copy of #9, source of template drift

#### Task 4: Document pipeline flow
Map the end-to-end pipeline: braindump -> lint-braindump -> generate-spec -> review -> (optional: regen-task per task) -> implement -> deviation analysis. Show data flow, where context blocks enter, which prompt fires at each stage, and what artifacts each stage produces.

#### Task 5: Write architecture.md
The core architecture document for Spec Doc as it actually exists today. Covers: Express server on port 3100, Angular 19 frontend on port 4201, Claude CLI as AI backend, adapter pattern for AI providers (cli/remote/mock), 4 persisted context blocks, Monaco editor + marked.js preview, project folder persistence. Includes design decisions with trade-offs.

#### Task 6: Distill reflections into architecture decisions
Read all 13 reflections in `specs/reflections/` and extract architectural decisions that should be permanent. Key ones already identified: port-first beats invent-first, structural tests pin architecture, context-completeness is a design dimension, the braindump is a first-class input, template drift is a recurring problem.

#### Task 7: Wire quality rubric references into architecture
The quality rubric (`specs/quality-rubric.md`) defines scoring criteria for generated documents. The architecture should reference it as the standard the review prompt scores against, and note the gap: the review prompt uses a hardcoded 6-dimension model that overlaps with but does not exactly match the rubric.

#### Task 8: Document template drift problem and extraction plan
The `buildImplementationGuidePrompt` function exists in two places: `ImplementationGuideService` (canonical) and `regen-task.mjs` (drifted copy). Document the drift, its consequences (missed rules in script-generated guides), and the two options: shared `.md` template file or server endpoint.

#### Task 9: Write prompt extraction migration path
Based on the analysis open question and the architecture decisions, propose a concrete migration from inline prompts to `prompts/*.md` files with `{{placeholder}}` interpolation. Define the folder structure, the interpolation mechanism, and the migration steps. This is a recommendation document, not an implementation guide -- the actual extraction is a follow-up epic.

#### Task 10: Document builder/principles onboarding gap
`builder.md` and `principles.md` are flat files read at server startup. A new operator must know to populate them before the pipeline produces good output. Document this as a known gap with a proposed solution (first-run wizard or CLI setup script).

#### Task 11: Document iterate-without-review gap
The `/api/ai/text/iterate` endpoint returns raw output with no quality gate. Document this as a gap: all other generative endpoints (generate-spec, regen-task) have review steps, but iterate does not.

#### Task 12: Document container integration gap
Container execution endpoints exist (`/api/container/*`) but have no integration tests and `CONTAINER_MODE` is off by default. Document the current state and what would need to be true for container mode to be production-ready.

#### Task 13: Write timeline.md
Create the timeline document with all 14 tasks in their initial status. This is the ONLY place for status tracking.

#### Task 14: Self-review: score against quality rubric
Run the completed 5-file spec set through the quality rubric scoring. Each document scored against its rubric section. Target: 90%+ (gold standard). Document the scores and any gaps.

---

## Success Criteria

- A new operator can open `spec-index.md` and navigate to any capability within 30 seconds
- All 9+1 system prompts are documented with purpose, inputs, outputs, and context-block injection points
- The pipeline chain is documented as a single flow diagram with data inputs and artifact outputs at each stage
- The architecture doc describes the actual current stack (Express + Angular + Claude CLI), not the superseded Spring Boot stack
- The self-spec scores 90%+ against the quality rubric (gold standard)
- Cross-references between all 5 documents are bidirectional and valid

---

## Non-Goals

- Building new features, endpoints, or UI -- this is pure documentation
- Implementing prompt extraction -- this epic recommends it; a follow-up epic implements it
- Replacing the existing `specs/` folder -- the self-spec lives in `projects/spec-doc-self-spec-*/` alongside bootstrapped projects
- Scoring other products' specs -- this is about Spec Doc speccing itself
- Achieving 100% coverage of every design decision ever made -- capture the ones that matter for the next operator

---

## Related Documents

- [Analysis](./analysis.md) -- Problems driving this work
- [Architecture](./architecture.md) -- Technical design
- [Timeline](./timeline.md) -- Status tracking (ONLY place for status)
- [Spec Index](./spec-index.md) -- Entry point
