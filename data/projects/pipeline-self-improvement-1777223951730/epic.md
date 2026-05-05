
# 🎯 Epic: Pipeline Self-Improvement

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Every recurring quality bug in the pipeline — leaked thinking lines, stale model attribution, path drift across sibling tasks, mismatched test counts — is currently caught by a human and fixed by hand. That fix never propagates back into the generation prompt. The next generation re-produces the same bug class. The hand-fix pass on the Workflows-as-a-Domain-Layer epic (commit `729e5c1`) is the highest-cost recent example: four sibling task docs disagreed on a file location and field names; a full session was spent reconciling what structured tooling would have caught at generation time. Each uncaught bug compounds — it reaches the executor's inbox, consumes review bandwidth, and in the worst case ships to disk as a misleading contract for a downstream task.

A pre-emit linter encodes each recurring bug class as a machine-checkable rule. Once encoded, the bug cannot ship — not because the model is instructed differently, but because the artefact is rejected before it is written. The coherence pass extends this from single-document rules to cross-document invariants: path uniqueness, timeline-to-epic alignment, component-to-task coverage. Together they shift quality assurance from a discipline (review everything, fix by hand) to a structural guarantee (artefacts that pass lint are coherent by construction). That shift has compounding value: every future capability added to the pipeline inherits the guarantee without additional review work.

The immediate addressable cost is developer time lost to regen-and-reconcile cycles on multi-task capabilities. The secondary value is confidence in generated specs as a product surface — a subscriber paying for generated spec docs expects consistency across the task docs they hand to an executor. A linter that blocks incoherent output is a feature, not infrastructure.

**Value Proposition**: The linter turns prompt rules into artefact contracts, making spec quality a structural guarantee rather than a review discipline.

---

## Scope

### What This Epic Covers

- **Pre-emit linter** — nine deterministic rules run before every file write; errors block generation (502); warnings write with a `warnings` field in the polling response.
- **Executor attribution injection** — a versioned `EXECUTOR_ATTRIBUTION` context block eliminates stale model co-author lines; lint rule #3 is the safety net.
- **Structured prior-task contracts** — replaces the 60-line truncation in `task_gen/service.py` with a contract parser that surfaces `(new)` file declarations to downstream task prompts; the root-cause fix for cross-task path drift.
- **Multi-doc coherence pass** — eight cross-document invariants run post-generation and are exposed via `POST /api/projects/<id>/coherence`; flags returned as `{flags, summary}`.
- **Project repair endpoint** — `POST /api/projects/<id>/repair` retroactively generates `spec-index.md`, `timeline.md`, and `README.md` for projects missing them.

### What This Epic Does NOT Cover

- ❌ **Auto-retry / self-healing loop** — deferred until linter error rate stabilises in production; re-scope when false-positive rate is measured.
- ❌ **Persistent flag history and analytics** — deferred until a second consumer of flag data exists; the linter's job is to gate, not to dashboard.
- ❌ **Warning-severity auto-fixers** — deferred until failure-rate distribution is known; humans decide what to do with warnings.
- ❌ **Angular coherence badge** — `POST /coherence` ships headless in this epic; the project-card badge surface is deferred to a UI-focused follow-up.
- ❌ **Impl-guide prompt template wholesale rewrite** — only the prior-contracts context block and the attribution hard rule change; any broader rewrite requires a separate brain dump.
- ❌ **Mid-generation coherence checking** — the coherence pass runs post-task only; in-flight partial-state checking is out of scope.

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel With | Effort | Priority |
|---|------|--------------|---------------|--------|----------|
| 1 | **Fix 60-line truncation — structured prior contracts** | None | Task 2, Task 5 | 2 days | High |
| 2 | **Executor attribution injection** | None | Task 1, Task 5 | 1 day | High |
| 3 | **Pre-emit linter** | Task 2 | — | 2 days | High |
| 4 | **Multi-doc coherence pass** | Task 1 | — | 3 days | High |
| 5 | **Project repair endpoint** | None | Tasks 1, 2, 3, 4 | 1 day | Low |

---

### Task 1: Fix 60-line truncation — structured prior contracts

The single-line truncation in `task_gen/service.py` at the `collect_prior_task_content` call cuts off §3 (Files) and §5 (Tests) of every prior task doc. Downstream tasks cannot see what prior tasks declared as `(new)` files, which is the structural cause of the cross-task path and field-name drift documented in the analysis. This task replaces the truncation with a contract parser that extracts `(new)` and `(modify)` file declarations plus any exports block, and injects the result as a `PRIOR-TASK CONTRACTS` block in the impl-guide prompt. This is a one-bug fix with compounding value — every multi-task generation from this point forward inherits correct contract visibility.

**Scope boundary**: Parser covers §3 file tables and export blocks only. No changes to the impl-guide prompt template beyond the new context block.

---

### Task 2: Executor attribution injection

Stale `Co-Authored-By: Claude Sonnet 4.6` lines appear in generated docs because no authoritative source of the current executor model version is injected into the prompt. This task adds an `EXECUTOR_ATTRIBUTION` environment-derived context block, injects it into the impl-guide prompt template, and adds a hard rule prohibiting invented model versions. Lint rule #3 (in Task 3) is the enforcement mechanism, so this task must land before Task 3 ships — otherwise valid docs fail the attribution check on the first linter run.

**Scope boundary**: Environment variable read at startup only. No new file written to disk unless `bootstrap_project` is confirmed to require one (open question from analysis).

---

### Task 3: Pre-emit linter

`modules/quality/lint.py` exposes a pure function that runs nine deterministic rules against any task guide text before `update_file()` writes it to disk. Error-severity flags return 502 from the polling endpoint with the flag list; warning-severity flags write the file and include a `warnings` field in the polling response. The nine rules cover: hash-first document structure, leaked thinking preambles, stale attribution (rule #3 depends on Task 2), absolute test counts, personal filesystem paths, placeholder values, empty test bodies, numbered-section count, and `+K` test-claim consistency. Wired into `task_gen/service.py:run_generation` immediately before the write call.

**Scope boundary**: Nine rules as specified; severity classification is not configurable. Lint rule #8 hardcodes 10 sections matching the current impl-guide template — any template section-count change must be coordinated with this rule (see open question in analysis).

---

### Task 4: Multi-doc coherence pass

`modules/quality/coherence.py` exposes a function that checks eight cross-document invariants against a project directory after task generation completes. Invariants cover: symbol uniqueness across file tables, cross-task import-path consistency, epic task-table-to-filename alignment, `spec-index.md` accuracy, `timeline.md`-to-epic backlog alignment, architecture-component-to-task coverage, pre-flight cross-task symbol dependency validity, and content-routing (status terms only in `timeline.md`). Exposed via `POST /api/projects/<id>/coherence` returning `{flags, summary}`. Invariants #1 and #7 will surface drift that Task 1's prior-contracts fix is still producing until Task 1 lands, so Task 1 is a sequencing prerequisite.

**Scope boundary**: Eight invariants as specified. Angular badge is deferred. The endpoint ships headless.

---

### Task 5: Project repair endpoint

`POST /api/projects/<id>/repair` re-runs the deterministic template generators for any project missing `spec-index.md`, `timeline.md`, or `README.md`. Returns `{repaired: [...]}` listing filenames written. Catches pre-linter projects from earlier capability generations. Fully independent — no ordering constraint relative to Tasks 1–4.

**Scope boundary**: Deterministic generators only (spec-index, timeline, README). No AI generation call. Auth requirements to be confirmed (see open question in analysis); idempotency is a requirement.

---

## Success Criteria

- ✅ A task guide containing a leaked thinking preamble is rejected at the polling endpoint with a 502 and a flag identifying the offending line.
- ✅ A task guide containing a stale `Co-Authored-By: Claude Sonnet 4.6` line produces a warning-severity flag, not a 502, and the file is written with `warnings` in the polling response.
- ✅ A two-task generation where task 2 references a file declared `(new)` in task 1 does not produce a coherence flag for symbol drift.
- ✅ `POST /coherence` on the Workflows-as-a-Domain-Layer project (the hand-fix reference case) returns zero flags after the repair endpoint has run.
- ✅ `POST /repair` on a project missing `timeline.md` writes a valid timeline and returns `{repaired: ["timeline.md"]}` without error.
- ✅ All nine lint rules have unit test coverage; rule coverage is verified by a test that enumerates rules by name.

---

## Non-Goals

- ❌ **Self-healing retry loop** — when the linter rejects, the user clicks Regenerate; no automated re-prompt until error rate data exists.
- ❌ **Flag persistence across sessions** — flags are ephemeral gate signals, not a stored quality history.
- ❌ **Configurable severity thresholds** — severity is per-rule and fixed until a real "ship the warning" exception case is confirmed.
- ❌ **Coherence pass during task generation** — post-task only; mid-generation partial-state checking is architecturally out of scope for this epic.
- ❌ **Angular UI changes for coherence flags** — the badge is deferred; headless endpoint only.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
