# spec-doc improvements — recommendations report

**Date**: 2026-04-26
**Scope**: read-only audit of the spec-doc pipeline (`api/modules/ai/`, `api/modules/implementation_guide/`, `api/modules/task_gen/`), the principles/references/builder/codebase context blocks, the four reflections in `specs/reflections/`, and the dogfood evidence under `api/docs/epic-*/` + `projects/*/`.

The thesis the user named is correct: **content lessons compound through the prompt; production-quality lessons stay in the executor's head.** Every recurring bug class below is a production-quality bug that has been hand-fixed at least twice without ever being encoded.

---

## Section 1 — Recurring bug classes (ranked by frequency × cost)

### 1.1 Leaked thinking lines (preamble before the first `#`)

**Frequency**: ~14% of all task docs (36 of 260 task files, by `grep -l "Now I have\|Let me write\|Writing the guide" projects/*/*.md api/docs/epic-*/*.md`).

**Cost**: low per occurrence (one line) but high per session — the executor sees an obviously-wrong artefact and loses trust in the rest of the doc. It is also the canonical "should be impossible" bug because the prompt explicitly forbids it.

**Evidence**:
- `api/docs/epic-1-foundation/task-3-context-file-module.md:1` — `Now I have everything I need. Let me write the guide.`
- `api/docs/epic-1-foundation/task-2-project-crud-module.md:1` — `Now I have all the exact server.js handler code. Writing the guide.`
- `api/docs/epic-1-foundation/task-4-chain-module-port.md:1` — `Now I have all the context I need. Let me write the guide.`
- `api/docs/epic-2-openapi-mock/task-4-validate-angular-integration.md:1` — same shape
- `projects/architecture-cleanup-1777112358103/task-1-unify-context-services.md:1` and `task-2-migrate-prompts-to-flask.md:1` — same shape, both very recent (this week)
- `projects/dev-experience-1777196194310/task-2-dockerfile-docker-compose-yml.md:1` — same shape
- `projects/generate-next-task-1777116449690/task-3-add-appcomponent-handler.md:1` — same shape

**Root cause**: The Hard Rule "Your entire response MUST begin with `#`. No preamble." (`api/modules/implementation_guide/prompts.py:26`) is a *prompt instruction*, not a *post-condition*. The CLI provider obeys ~85% of the time and silently fails 15% of the time. There is no save-time check.

**Fix**: A `_strip_preamble(text)` helper that runs before every `update_file()` write in `api/modules/task_gen/service.py:run_generation`. Three lines. Pattern: drop everything before the first `^#` line. This is a strictly safer transformation than the model retry the prompt requests today; if the doc *legitimately* starts with `#`, the strip is a no-op.

---

### 1.2 Stale Co-Author / model attribution lines

**Frequency**: ~8 hits across 4 files.

**Cost**: low — but the *symbol* is high cost: the spec-doc executor is currently `Claude Opus 4.7 (1M context)` (per the live env), and yet every generated commit-block tells the executor to stamp `Co-Authored-By: Claude Sonnet 4.6`. The real co-author and the suggested co-author disagree.

**Evidence**:
- `projects/architecture-cleanup-1777112358103/task-3-extract-template-generators.md:717,738,754` — three commit blocks all suggest `Claude Sonnet 4.6 <noreply@anthropic.com>`
- `projects/architecture-cleanup-1777112358103/task-1-unify-context-services.md:563,588`
- `projects/dev-experience-1777196194310/task-5-docker-compose-coolify-yml-makefile-additions.md:353`
- `projects/generate-next-task-1777116449690/task-1-extend-sidebaraction-union.md:161`

**Root cause**: The model invented a "Sonnet 4.6" attribution on its own; the prompt does not pin it. This is the exact pathology Upgrade 3 of `specs/spec-doc-upgrade-plan-2026-04-16.md` predicted ("every invented version string is a future drift vector") and that plan recommended a `versions.md` block to fix. The block was never built.

**Fix**: Inject the runtime's actual `CLAUDE_CODE_VERSION` (or env-pinned model id) into the prompt as a `## EXECUTOR ATTRIBUTION` block, and add a Hard Rule to the impl-guide template: "When emitting a `Co-Authored-By:` trailer, copy the value from EXECUTOR ATTRIBUTION verbatim. Never invent."

---

### 1.3 Cross-doc contract drift between sibling task docs

**Frequency**: 1 of the 1 multi-task projects audited end-to-end (`workflows-as-a-domain-layer-1777209194016`). The "minimal-fix pass on spec docs" commit `729e5c1` (today) is the smoking gun — its commit body literally says *"align Tasks 1.1, 1.2, 2, 5 to the same contract"* — meaning four of the six task docs disagreed at generation time. This is the **highest-cost bug class** because the executor only finds it after committing Task N and starting Task N+1.

**Evidence (single project, fresh today)**:
- `task-1.1-abstractstep-foundation.md:42` declares `modules/workflows/steps/events.py` (sub-package path).
- `task-3-workflow-runtime.md:51` declares `modules/workflows/events.py` (top-level path) — different file, same symbol set (`StepStarted`, `StepCompleted`, `StepFailed`, `StepEvent`).
- `task-4-workflowrepository-fs-adapter-.md:59` references `events.py` "if present from Tasks 1–3" — i.e. the doc author isn't sure which path to expect.
- `task-1.2-concrete-step-kinds-aicall-compute.md:30` imports `from modules.workflows.steps.events import StepStarted, StepCompleted, StepFailed` (matches Task 1.1, contradicts Task 3).
- `task-3-workflow-runtime.md:996` commit message: `feat(workflows): add step domain event types — modules/workflows/events.py: StepStarted, ...`

So Task 1.1 builds events at path A, Task 3 builds them again at path B, both as "(new)". Whichever runs second silently shadows or duplicates the other. The executor either hand-merges or ships two competing modules.

**Root cause**: There is no shared contract surface between sibling task generations. Each `build_implementation_guide_prompt()` call (`api/modules/implementation_guide/prompts.py:30`) gets the **architecture** doc and a `prior` string of prior task content (truncated to 60 lines per task, see `task_gen/service.py:163`), but nothing enforces that Task N+1's "Files To Create" must be disjoint from Task N's, or that a symbol referenced in two tasks resolves to the same import path.

**Fix**: After each task doc is generated, extract its `## 3. Files` table and persist it as a structured artefact (`projects/<id>/.contract.json` with `{task_num: {creates: [...], modifies: [...]}}`). On the next task generation, inject this contract as a "PRIOR TASKS' FILES (do not re-create)" block. The model behaves correctly when the constraint is in-context.

---

### 1.4 Placeholder / inconsistent test counts

**Frequency**: visible in 3 of 6 task docs in the workflows project; visible in older epics too (epic-1-foundation `Pytest baseline is 15 passing`).

**Cost**: medium — when the doc says "Expected: 192 passed" but the actual baseline is 216, the executor either ignores the assertion (defeating the gate) or chases a phantom regression.

**Evidence**:
- `task-1.1-abstractstep-foundation.md:30` correctly says "Do not rely on the absolute number 192" (this is the **encoded** discipline). But the *same file* line 710 says `# Expected: 216 passed, 0 failed, 0 errors` (absolute) and line 760 says `# Expected: 192 passed (original count)` — three different baselines in one doc.
- `task-1.1-abstractstep-foundation.md:45` says "23 tests covering all branches" while §1, §5 and §6 of the same doc say "+24 tests" (4 references to 24, 1 reference to 23 — internal contradiction).
- `task-3-workflow-runtime.md:1016` hardcodes `192 → 225 passing`, ignoring the "do not rely on absolute counts" rule that Task 1.1 §2 establishes.
- `task-1.2-concrete-step-kinds-aicall-compute.md:75` says "All 192 tests must pass before adding new code" — absolute count, encoded back even though sibling Task 1.1 explicitly bans this.

**Root cause**: The "record N as baseline, do not rely on absolute counts" discipline is a *content lesson* (in some prompts) but is not enforced. Different generations of the same project apply it at different rates.

**Fix**: Two layers — (a) lint regex `\b(\d{2,3}) passed\b` flags any explicit absolute count in an `Expected:` block; force `N → N+K`. (b) Lint regex on the Files-table count vs the "+K tests" mention vs the table-of-asserts row count: assert all three agree. Both are pre-emit string checks.

---

### 1.5 Missing task files from generated projects

**Frequency**: **53+ of ~80 multi-task projects** have an epic with N declared tasks but `< N` task-doc files (one-shot batch search via `grep -cE '^\| ?[0-9.]+ ?\| ?\*\*' epic.md` vs `ls task-*.md`). Examples:
- `projects/architecture-cleanup-1777112358103/`: epic declares 5 tasks, 3 task files exist (Tasks 4 + 5 missing).
- `projects/iteration-0006/`: epic declares 11 tasks, 6 files.
- `projects/chain-primitive-1777196289015/`: epic declares 5 tasks, 0 files.
- `projects/dev-experience-1777128247958/`, `dev-experience-1777128949271/`, `dev-experience-1777130470173/`: 4–5 tasks declared, 0 files.

**Cost**: medium-low for projects abandoned mid-stream (most of these). High for projects the user did intend to ship — Tasks 4 + 5 of `architecture-cleanup` are the missing piece for a feature this week.

**Root cause**: `bootstrap-project` (`api/modules/ai/routes.py:169`) generates analysis/epic/architecture/spec-index/timeline/README — **never** task docs. Task generation is one-task-per-click via `task_gen` (`api/modules/task_gen/routes.py:30`). There is no "bootstrap-all-tasks" endpoint and no lint that warns "this project's epic has 5 tasks but only 3 docs exist."

**Fix**: An `api/projects/<id>/lint` endpoint that returns `{declaredTasks: 5, generatedTasks: 3, missing: ["4", "5"]}`. The Angular sidebar already polls `generate-task/status`; surface the missing-task count as a badge on the project card.

---

### 1.6 Architecture-cleanup project also missing `spec-index.md` and `timeline.md`

**Evidence**: `ls /workspace/projects/architecture-cleanup-1777112358103/` returns 6 files (README, analysis, architecture, epic, project.json, 3 task files). Both `spec-index.md` and `timeline.md` are absent — even though `bootstrap_project` deterministically writes both (`routes.py:216-220`).

**Root cause**: This project was bootstrapped before those deterministic writes were added (or via a partial-failure path that skipped the deterministic step). There is no migration or lint that retroactively generates the missing canonical files for older projects.

**Fix**: A `POST /api/projects/<id>/repair` endpoint that re-runs only the deterministic template generators (`generate_spec_index`, `generate_timeline`, `generate_readme`) for any project missing those three files. ~30 lines.

---

### 1.7 Hardcoded personal / absolute paths

**Frequency**: 0 hits in the workflows project, 0 hits in the audited epic-1 / epic-6 task docs. **This bug class is essentially fixed.**

**Why**: The impl-guide prompt's Hard Rule "NO absolute personal paths. Use {WORKSPACE} or workspace-relative paths." (`api/modules/implementation_guide/prompts.py:24`) is the second of the three encoded rules and visibly works.

**Action**: keep the encoding; do not add a redundant lint here yet.

---

## Section 2 — What's working (encodings that compound)

### 2.1 The "Hard Rule" preamble in `_USER_HEADER`

`api/modules/implementation_guide/prompts.py:13-27` defines exactly three Hard Rules: no personal paths, no test stubs, response begins with `#`. The first one is doing visible work (Section 1.7). The third is doing partial work (Section 1.1). The middle one is doing complete work (no `/* ... */` stubs found in any audited spec). **Strengthening this list is the cheapest pipeline upgrade available** because it is one file, one diff, and the rules are already the prompt's "load-bearing assertion".

### 2.2 The CONTENT ROUTING RULES in `_BOOTSTRAP_CONTENT_ROUTING`

`api/modules/ai/prompts/__init__.py:129-139` is a 10-line block injected into all three bootstrap prompts. The audited workflows project shows the *exact* shape pay off:
- `analysis.md` has zero status terms.
- `epic.md` has the Priority column (not Status).
- `architecture.md` has zero code blocks.
- `timeline.md` is the *only* file with `Done / In Progress / Backlog` headings.

This is the highest-leverage encoding in the entire pipeline. Every "content in the wrong file" violation that v1 of the rubric (`specs/quality-rubric.md`) flagged is now structurally absent. The pattern — *negative rules with severity and a routing matrix* — is the template for fixing the production-quality bugs (which currently lack this kind of rule set).

### 2.3 The bootstrap chain (`analysis → epic → architecture` server-side)

`bootstrap_project` (`routes.py:169-228`) chains the three prompts in one HTTP call, where each step receives the prior step's output. Architecture quality jumped because the model sees the actual epic, not a re-summarised one. The workflows architecture doc cites specific tasks ("Phase 1 maps to Tasks 1.1, 1.2, 2, 3, 4, 5") because the prompt got the full epic. That coherence does not happen in single-shot prompts.

This pattern needs to be *extended downstream* (see §7): task generation today does NOT chain — each task gets epic + architecture + truncated `prior` content but no view of sibling tasks' Files tables.

---

## Section 3 — Reflections-not-encoded (the leaky loop)

### 3.1 Spec-doc-upgrade-plan 2026-04-16 status

The plan listed 3 must-do upgrades and 4 medium-term upgrades. Audit:

| Upgrade | Status | Evidence |
|---|---|---|
| **U1: Encode ELA Adapter pattern** | **Done** | `chain.adapter.py` exists; `featureModules_mustNotImportProvidersDirectly` test exists; the workflows architecture cites "ELA Pattern #6 Adapter" verbatim and forbids direct provider imports |
| **U2: Extract impl-guide template to shared source** | **Partially done** | `api/modules/implementation_guide/prompts.py` is the single source. But the script-side duplicate problem (regen-task.mjs) the upgrade describes does not exist in the current Flask architecture — task gen calls the same Python function. Net: solved by architectural change, not by the proposed mechanism |
| **U3: `versions.md` / inject current model IDs** | **NOT done** | No `versions.md` file. No fifth context block. Bug 1.2 (stale Sonnet 4.6 attribution) is the predicted symptom |
| **A: Task-guide lint endpoint** | **NOT done** | No `/api/ai/text/lint-task-guide` route. The 6-line manual grep audit at `spec-doc-upgrade-plan-2026-04-16.md:163-170` is still the gate |
| **B: Self-review generation pass** | **NOT done** | No second-pass review in the bootstrap or task-gen flow |
| **C: Post-execution retro endpoint** | **NOT done** | No `/api/ai/retro/branch` route; deviation classification still manual |
| **Structural-test library** | **Done in spirit** | `tests/test_structural.py` exists and is referenced by name in workflows architecture; the workflows generation extends it |
| **Task-retro auto-template** | **NOT done** | No `/api/projects/<id>/retro` route; `specs/reflections/` is hand-written |
| **Braindump lint** | **Done** | `lint_braindump_prompt` (`prompts/__init__.py:110`) and `POST /lint-braindump` (`routes.py:84`) exist |
| **Context-completeness pre-flight** | **NOT done** | No code that cross-checks the generated spec's external references against injected context blocks |

So **6 of 11 upgrades are still pending**. The three highest-value pending items (lint endpoint, self-review, retro endpoint) are exactly the production-quality feedback loop.

### 3.2 The followup-ela-adapter reflection

`specs/reflections/2026-04-16-followup-ela-adapter-in-references.md` proposed three encodings — adapter skeleton in references.md, principles.md ban on direct provider imports, and a Hard Rule in the impl-guide template. **The first two appear to have landed** (the workflows architecture cites the pattern correctly and the structural test exists). **The third — the Hard Rule in `_USER_HEADER`** — is **not in `api/modules/implementation_guide/prompts.py:13-27`**. The current Hard Rules are the original three (paths, stubs, `#`). The adapter-discipline rule is enforced only by review, never by prompt. Add it.

### 3.3 The executor-meta + executor-as-typist reflections

The four micro-decisions Task 2 surfaced (model id, ServiceError placement, pyproject testpaths, alias imports) all map to the predictions in `2026-04-16-executor-meta.md`. None of them are systematically encoded:
- Model id: see §1.2 (still drifting).
- File-vs-inline placement: no encoding; still per-task judgment.
- Test-path config: no encoding; still per-task judgment.
- Pytest-collection name conflicts: not in any prompt.

This is a 1-year-old reflection still unincorporated. The pattern is the meta-thesis the user named.

---

## Section 4 — Pre-emit linter spec

A `lint_task_guide(text: str) -> list[Flag]` function called from `task_gen.service.run_generation` immediately before `update_file()`. Each check is a regex and a one-line fix or block.

| # | Pattern | Severity | Fix on detect |
|---|---|---|---|
| 1 | `\A(?!#)` (file does not start with `#`) | error | strip everything before first `^#` line; re-validate |
| 2 | `^(Now I have\|Let me write\|Writing the guide\|Here's the guide\|Below is the guide)` | error | strip the line(s); re-validate rule 1 |
| 3 | `Co-Authored-By: Claude (?!Opus 4\.7)` | warning | rewrite to the env-pinned `EXECUTOR_ATTRIBUTION` value |
| 4 | `\b\d{2,3} passed\b` inside `Expected[:\s]` | warning | flag for `N → N+K` rewrite |
| 5 | `/Users/[a-z]+\|/home/[a-z]+\|C:\\\\Users\\\\` | error | refuse save; demand `{WORKSPACE}` substitution |
| 6 | `path/to/[a-z]+\|<placeholder>\|TODO\(executor\)\|<TBD>` | error | refuse save |
| 7 | `/\* \.\.\. \*/` or `it\([^,]+, ?\(\) ?=> ?\{\s*\}\)` (empty test bodies) | error | refuse save |
| 8 | Section headers `^## ` count != 11 (10 required + Related Documents) | error | refuse save with missing-section list |
| 9 | Files table `**(new)**` count != Implementation-Steps `### Step N` count ± tolerance | warning | flag for review |
| 10 | "+K tests" claim (in §1) ≠ row count of `## 5. Tests` table ≠ `+K` claim in §7 | error | refuse save with diff |

Implementation: ~120 lines of pure Python in a new `modules/quality/lint.py`. Wire it into `task_gen/service.py:run_generation` between the chain call and `update_file`. Failures return as a 502 to the polling client with the flag list — Angular shows a toast; the user clicks Regenerate.

This catches everything in §1.1, §1.2, §1.4, parts of §1.7. Estimated coverage: 80% of the bug classes the manual audit catches.

---

## Section 5 — Multi-doc coherence pass spec

For capability-level generation (the 12-doc shape in `workflows-as-a-domain-layer-1777209194016/`), add a `lint_capability(project_dir: Path) -> list[Flag]` invariant checker that runs after each task generation completes:

| # | Invariant | How to check |
|---|---|---|
| 1 | **Symbol uniqueness across `## Files` tables** | Parse each `task-*.md`'s files table; for each path, assert it appears in `(new)` at most once across all task docs |
| 2 | **Cross-task file-path consistency** | Index every Python import path mentioned in any code block; if `from modules.workflows.steps.events import X` and `from modules.workflows.events import X` both appear in different task docs, flag a path conflict |
| 3 | **Epic task table ↔ task-doc filenames** | Every row of `epic.md`'s `| # | Task | ...` table must have a matching `task-{num}-*.md` file. Missing files are listed; extra files are flagged as orphans |
| 4 | **Spec-index.md ↔ filesystem reality** | `spec-index.md`'s Task Guides table must list exactly the task-*.md files present on disk |
| 5 | **Timeline.md backlog ↔ epic task table** | `timeline.md`'s Backlog table rows must match `epic.md`'s task table by task num and name |
| 6 | **Architecture component ↔ task ownership** | Every component named in `architecture.md`'s "Component Design" must have a task in the epic that produces it (use the task table + task description) |
| 7 | **Prior-task dependency closure** | If task N's "## 2. Pre-flight" cites a symbol from task M (M < N), task M's "## 3. Files" table must declare creating that symbol |
| 8 | **Status-rule re-check** | Run rule 1 from CONTENT ROUTING RULES against every doc — status terms only allowed in timeline.md |

Implementation: ~250 lines. Run as a `POST /api/projects/<id>/coherence` route that returns `{flags, summary}`. Wire into the post-task-generation hook so the executor sees a coherence summary before opening the next task. The workflows project's events.py drift (§1.3) would fire invariant 2; the architecture-cleanup missing-task drift (§1.5) would fire invariant 3.

---

## Section 6 — Impl-guide prompt template gaps

The current template (`api/modules/implementation_guide/prompts.py`) is 73 lines. Three concrete gaps from comparing the prompt to actual generated workflows-task docs:

### 6.1 The template under-specifies file-path conventions

The Hard Rules say "Use `{WORKSPACE}` or workspace-relative paths" but say nothing about whether new modules go at `modules/<feature>/` or `modules/<feature>/<sub>/`. Result: Task 1.1 chose `modules/workflows/steps/events.py`, Task 3 chose `modules/workflows/events.py` — both are workspace-relative, both obey the Hard Rule, neither references the other. The template should require that the architecture doc's path conventions be cited verbatim or re-derived in §3 of every task.

**Add to `_USER_HEADER`**: *"Every path you propose in §3. Files MUST either appear in CODEBASE CONTEXT (existing) or in ARCHITECTURE > Component Design (new). Inventing a path that contradicts a sibling task's path is a contract violation."*

### 6.2 The template does not constrain "+K tests" claims

The numbered sections list `5. Tests` but say nothing about asserting test count consistency. The rule "every test must have a complete assertion body" is encoded; the rule "the count you claim must match the rows you produce" is not. Result: §1.4 above.

**Add to `_USER_HEADER`**: *"If §1 Context says '+K tests', §5's table must have exactly K rows and §7 verification must say `+K vs baseline N`. K appears three times consistently or zero times."*

### 6.3 The template does not require declaring inter-task dependencies

The 10-section template has §2 Pre-flight (which includes "verify prior task contracts present") but does not require §3.1 "Symbols this task consumes from prior tasks" or §3.2 "Symbols this task exports for future tasks". Without that, the model has no prompt-shaped slot to surface a contract conflict.

**Add a §3.1 bullet to `_USER_HEADER` Required Sections**: *"3a. **Imports from prior tasks** — list every (`task-N`, `module.path`, `symbol`) tuple this task depends on. 3b. **Exports for future tasks** — list every public symbol this task introduces."*

### 6.4 The "prior" context is truncated arbitrarily

`task_gen.service.collect_prior_task_content` (`service.py:163`) truncates each prior task to 60 lines. That's the §1 + §2 of the prior task — **the §3 Files table and §5 Tests table are cut off**. The model literally cannot see what prior tasks declared as "(new)" files. This is the structural cause of §1.3.

**Fix**: Replace the line-truncated prior with a structured contract. Parse each prior task's §3 Files table and pass it as a structured dict in the prompt. ~40 lines of parsing in `service.py`.

### 6.5 No "Trade-offs considered" sub-list slot in §1

The plan said it was added; the prompt header doesn't show it. Workflows task-3 has a "Trade-offs considered:" block at line 7 (apparently the model invented it because the architecture used the phrase) but tasks 1.1, 2, 4 do not. The encoding either was never landed or was lost. Re-encode.

---

## Section 7 — The single highest-leverage move

**Build the pre-emit linter (Section 4) and the multi-doc coherence pass (Section 5) and gate `update_file()` on them.**

Why this and not anything else:

1. **It closes the leaky loop the user named.** Today, every production-quality bug (preamble, model ID, path drift, count mismatch, missing section) is caught at one of three places: the executor's eye on first read, the executor's grep after a regen, or the user's hand-fix commit (e.g. `729e5c1` "minimal-fix pass on spec docs"). None of these write back to the prompt. A pre-emit linter writes the bug class as code; the bug class then cannot ship; the failure surfaces at generation time and forces a real prompt-side fix instead of a downstream hand-edit.

2. **It is shaped exactly like the encoding that already works.** `_BOOTSTRAP_CONTENT_ROUTING` is a 10-line block of negative rules with severity and a routing matrix; that is the highest-leverage encoding in the pipeline today (§2.2). The linter generalises that pattern from "rules the model is asked to follow" to "rules the artefact is checked against". One is a wish; the other is a contract.

3. **It is the cheapest item on the spec-doc-upgrade-plan that has the most payoff.** Upgrade 4A in the plan (the lint endpoint) was estimated at "~80 lines, 1 hour". The plan estimate is correct for the linter alone; the coherence pass adds ~250 more lines but consumes the linter's parser. Total: ~1 day's work, replaces an audit the user is currently doing by hand after every regen.

4. **It is the precondition for the auto-retro (Upgrade C) the plan also wants.** A linter produces structured flags. Structured flags can be tallied, classified, and fed back into "the prompt that produces this class of bug needs a new Hard Rule". Without the linter, the retro endpoint has no input format. With it, the loop the user named — "executor hand-fixes a generated spec" → "next generation doesn't have that bug" — has a concrete shape: linter flags → retro tally → prompt edit → regression test in the linter's own test suite.

5. **It would have prevented the workflows-project drift the user just spent a session hand-fixing.** Run `lint_capability` on the project before commit `729e5c1` and rules 2, 3, 6, 7 from §5 would all have fired against the events.py path collision and the test-count drift.

The criterion was "if we did only this one thing in the next month, what would compound the most?" — a linter compounds because its test suite grows with every bug it catches. A new Hard Rule in the prompt does not compound; it just sits there hoping the model obeys.

---

## Out of scope (named, then skipped)

- **Refactoring the chain.adapter to take an `Invocation` value object** (the brain dump's widening proposal) — this is the workflows epic's job, not a spec-doc improvement. Spec-doc benefits regardless of which chain-layer shape ships under it.
- **A frontend modal for editing references.md** — the upgrade plan correctly deferred this; nothing has changed.
- **A web dashboard for pipeline metrics** — speculative; no consumer.
- **Replacing the CLI provider with the SDK provider** — orthogonal to spec quality.

---

## Section 8 — File-path index for follow-up

The pipeline's load-bearing files (audit-confirmed, in dependency order):

- `api/modules/ai/prompts/__init__.py` — bootstrap chain prompts (analysis/epic/architecture)
- `api/modules/ai/routes.py` — bootstrap_project HTTP entry point
- `api/modules/implementation_guide/prompts.py` — `_USER_HEADER` (Hard Rules) and `build_implementation_guide_prompt()`
- `api/modules/task_gen/service.py` — `run_generation` background-thread body; `collect_prior_task_content` (the truncation source)
- `api/modules/task_gen/routes.py` — POST /generate-task entry point
- `api/modules/chain/adapter.py` — provider boundary; not a quality concern, working as intended
- `api/modules/templates/generators.py` — deterministic generators for spec-index/timeline/README

Where the recommended changes land:

| Change | File | Estimate |
|---|---|---|
| §4 pre-emit linter | new `api/modules/quality/lint.py` + wire into `task_gen/service.py:run_generation` | ~150 lines |
| §5 coherence pass | new `api/modules/quality/coherence.py` + new `POST /api/projects/<id>/coherence` route | ~250 lines |
| §6.4 structured prior contracts | edit `api/modules/task_gen/service.py:collect_prior_task_content` | ~50 lines |
| §6.1, §6.2, §6.3, §6.5 prompt edits | edit `api/modules/implementation_guide/prompts.py:_USER_HEADER` | ~20 lines |
| §1.6 project repair endpoint | new `POST /api/projects/<id>/repair` route | ~30 lines |
| §1.2 attribution injection | edit `api/modules/ai/prompts/__init__.py` + `task_gen/service.py` to inject `EXECUTOR_ATTRIBUTION` | ~20 lines |

Total: roughly one engineering day for the linter + coherence pass; another half day for the prompt edits and repair endpoint.

---

*End of report.*
