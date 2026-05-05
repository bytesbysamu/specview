# spec-doc-api — Codebase Cleanup Pass (open-ended audit + execute)

> **Priority**: P3 — quality + sets correct foundation before bucket-7 SaaS modules ship.
> **Effort**: ~1–2 days (depends on what's found).
> **Blocks**: nothing functionally; **prevents** silent migration debt and god-module drift
>             from compounding as new features land.
> **Depends on**: nothing — pure cleanup pass, no new capabilities; all tests must stay green.
> **Siblings**: `braindump-modular-restructure.md` (the bigger 11→4 package restructure;
>               this brain dump does the per-file cleanup that should land alongside or
>               just before).
> **Charter**: open-ended audit + execute, **measured by lines removed** and structural
>               debt closed. The seed findings below are starting points, not the full
>               worklist — the executor is expected to discover more during the walk.

## What

An open-ended cleanup pass. Walk the api/ codebase looking for **anything** that fits the categories below, fix what's safe, document what isn't. **Outcome is measured numerically**: net LOC removed, files deleted, god-functions decomposed, dead code purged. The seed findings are the audit's starting point — the executor should add to the list as the walk surfaces more.

The constraint is non-negotiable: **all 764 tests stay green at every step**. Anything that breaks a test is reverted; anything that requires changing test logic is out of scope.

### Categories to audit (the "go look" list)

| Category | Technique | What to remove |
|---|---|---|
| **Dead code** | Cross-file `grep` for function/class names; AST scan for unused imports; `pyflakes`; check Blueprint registrations + `@register_compute` lookups before flagging | Unused functions, unused imports, dead branches, dead classes |
| **Duplication / anti-DRY** | Side-by-side reads of similarly-named files (the 3 `templates/generators.py` functions; the 3 chain provider files; route handlers across `data/projects/`); fuzzy-grep for repeated code blocks (≥10 LOC repeated ≥3 places) | Duplicated logic → extract helper; duplicated boilerplate → decorator/factory |
| **God modules** | `wc -l` on every `*.py` in `modules/`; flag anything > 400 LOC | Split per-feature; `__init__.py` becomes re-export shim |
| **God functions** | AST scan: function bodies > 50 LOC | Decompose into named sub-functions |
| **Silent migration debt** | Cross-check: routes that *claim* to use WorkflowRuntime via `WorkflowExecution(workflow_ref=...)` strings vs routes that actually call `WorkflowRuntime().run()`; duplicated routes (old + new pointing at same domain) | Complete the migration OR delete the orphan |
| **SOLID-adjacent smells** | Look for: classes that mix routing + business logic + persistence; functions that take >5 positional args; conditional logic that's really polymorphism in disguise | Extract; rename to clarify; dispatch via Strategy where natural |
| **Magic numbers / unnamed thresholds** | `grep -nE '\b[0-9]{3,}\b'` outside test fixtures + obvious port/timeout values | Promote to named constant with comment |
| **Lint** | `make lint` (flake8) | Trivial — fix or `# noqa` with reason |

### How to measure

Before the cleanup PR, capture:
- Total LOC under `modules/` (excluding `__pycache__`, generated DTOs)
- Number of `*.py` files
- Largest file's LOC
- Largest function's LOC
- Test count + pass count
- Lint violation count

After:
- Same five metrics
- Net delta on each
- Specific items addressed (commit-by-commit)

A successful cleanup looks like: ≥500 LOC removed, no new files, ≥3 god-modules split, ≥3 god-functions decomposed, **same or higher** test count, zero new lint violations.

### Seed findings (audit starting points — not exhaustive)

These are the items the audit pass already surfaced. The executor should treat them as **the first six items on a longer list**, not as the entire job.

#### 1. Bootstrap is half-migrated (silent debt)

`modules/ai/routes/text.py:212-247` defines `bootstrap_project` as async (returns 202 + job_id) and creates `WorkflowExecution(workflow_ref="ai/bootstrap-project", ...)`. **But `_run_bootstrap_thread` never invokes the runtime** — it makes three inline `chain_adapter.generate()` calls. Meanwhile the workflow file at `modules/ai/workflows/spec_gen/bootstrap.py` is registered as `spec_gen/bootstrap-project` (the `workflow_ref` string is dangling — wrong namespace + nothing reads it).

Fix shape: replace the three inline calls with `runtime.run(repo.get("spec_gen/bootstrap-project"))`. Lines removed: ~30 inline + the now-unused `bootstrap_*_prompt` functions in `prompts/__init__.py` (44 + 105 + 138 = 287 LOC). Net **~310 LOC**.

#### 2. Duplicate route — old `/api/ai/text/generate-spec` survives next to new `/api/spec-gen/generate`

`text.py:156-211` is the old single-call inline implementation; `spec_gen.py:52` is the new WorkflowRuntime-backed one. Angular still calls the old one (`web/src/app/services/ai.service.ts:90`); the new one has zero consumers.

Fix shape: switch Angular URL → delete old handler → remove `generate_spec_prompt` from `prompts/__init__.py` → drop openapi path → `make generate-dtos`. Lines removed: ~60 backend + ~30 prompt + ~15 openapi + DTO regeneration delta. Net **~100 LOC**.

#### 3. God module: `modules/ai/prompts/__init__.py` (779 LOC)

Holds rewrite + iterate + generate + generate-spec + review + lint-braindump + scan + bootstrap-{analysis,epic,architecture}_prompt + content-routing constants + bootstrap template strings.

Fix shape: split per-feature into `prompts/text.py`, `prompts/review.py`, `prompts/bootstrap.py`; `__init__.py` shrinks to a re-export shim (~30 LOC). After §1 deletes the bootstrap_*_prompt functions, the file collapses further. Lines removed from one file: ~750 → 30; redistributed across ~5 new files of ~80 LOC each. Net file-count change: +4, LOC unchanged but distributed. **Measure: largest-file LOC drops from 779 to ~200.**

#### 4. God function: `task_gen/services/task_gen.py::run_generation` (139 LOC)

Decompose into named sub-functions: `_load_inputs`, `_select_task`, `_build_prompt`, `_invoke_chain`, `_persist_result`, `_record_completion`. Each ~20 LOC. Lines removed: net 0 (decomposition, not deletion); **measure: largest-function LOC drops from 139 to ~25**.

#### 5. DRY in `modules/data/templates/generators.py`

Three functions (`generate_spec_index` 58 LOC, `generate_timeline` 66, `generate_readme` 56) emit markdown sections with similar shape. Extract `_section(title, body) -> str` helper. Lines removed: ~60 across the file. **Measure: file shrinks from 216 to ~150 LOC.**

#### 6. Test coverage gaps

Two modules with zero service-level tests: `context/`, `projects/`. **This is the one item that ADDS lines** — ~10 tests per module, ~80 LOC added. Outcome metric: +20 tests; net LOC delta is positive but justified.

### Discovery prompts (run these and dump what you find)

```bash
# Files > 400 LOC
find modules -name '*.py' -not -path '*__pycache__*' -not -path '*tests*' \
  | xargs wc -l | awk '$1 > 400'

# Functions > 50 LOC
for f in $(find modules -name '*.py' -not -path '*__pycache__*' -not -path '*tests*'); do
  python3 -c "import ast; t=ast.parse(open('$f').read()); [print(f'{(n.end_lineno or n.lineno)-n.lineno:4d}  $f::{n.name}') for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and (n.end_lineno or n.lineno)-n.lineno > 50]"
done | sort -rn

# pyflakes for unused imports + variables
python -m pyflakes modules/

# Functions named the same across files (potential duplications)
grep -rEn '^def [a-z_]+' modules/ --include='*.py' | grep -v test_ | \
  awk -F: '{print $3}' | awk '{print $2}' | sed 's/(.*//' | sort | uniq -c | sort -rn | awk '$1 > 1'

# Routes vs openapi paths — drift
grep -rE "@.*_bp\.(get|post|put|delete)" modules/ --include='*.py' | grep -v test_
grep -E "^  /" openapi.yaml

# WorkflowRuntime users vs raw chain_adapter callers
grep -rn "WorkflowRuntime\|workflow_repository\.get\|WorkflowExecution(" modules/ --include='*.py' | grep -v test_
grep -rn "chain_adapter\.\(generate\|stream\|rewrite\)" modules/ --include='*.py' | grep -v test_
```

Dump the output as a `findings.md` artifact at the start of the cleanup PR. Then walk it.

### Guardrails

- **All tests must stay green at every commit.** If a refactor breaks a test, revert.
- **No logic changes.** Renames, decompositions, deletions of unused code only. If a behaviour change feels needed, that's a separate brain dump.
- **No openapi.yaml shape changes** beyond removing duplicated paths (§2). If a path moves, route URLs stay the same.
- **No Blueprint name changes.** Routes register the same way.
- **Generated DTOs are downstream of openapi.yaml.** Run `make generate-dtos` after any openapi edit; commit the regenerated `dtos/models.py`.
- **`featureModules_mustNotImportProvidersDirectly` and `packages_areInExpectedHierarchy` (if landed) stay green.**
- **Tests added for §6 must follow the existing pytest convention** (`condition_expectedOutcome` naming; helpers without `_` to dodge the `*_*` collection rule).

## Why now

The audit surfaced **silent migration debt** (bootstrap half-migrated, generate-spec duplicated) that didn't show up in the test suite — both old and new paths pass tests. Test green is necessary but insufficient: it doesn't catch "this code was supposed to be deleted but wasn't." The longer the duplicates live, the more code references the wrong endpoint, the harder the deletion becomes.

The Workflows-as-a-Domain-Layer epic was supposed to be the *one* substrate for AI orchestration. Today it's the substrate for `task_gen` and `spec_gen`; `bootstrap` simulates being on it (state machine wrapper) without actually using it. Every future feature that copies the half-migrated `_run_bootstrap_thread` pattern entrenches the half-migration. Closing this in one cleanup pass is much cheaper than adding "and untangle the bootstrap pattern" to every future brain dump.

Five bucket-7 SaaS brain dumps (github-integration, spec-sharing, landing-page, onboarding, settings-page) are queued. They will each add prompt functions to `prompts/__init__.py` if it stays at 779 LOC, route handlers to god `routes.py` files, etc. Cleaning before they land is cheaper than after.

## What's missing

One decision: **how aggressively to delete vs document?**

- (a) **Delete by default; document only what can't be deleted** (proposed) — every dead function gets removed; every duplication gets de-duped; only items with explicit consumer dependencies get a comment-and-defer.
- (b) **Document everything; delete only with sign-off** — safer; slower; the cleanup PR becomes a discussion thread, not a refactor.

(a) is right. Deletions show up in code review; reverts are cheap. Documenting-without-deleting accumulates more debt than it removes.

## Explicitly out of scope

- **Full SOLID compliance audit** — academic; this brain dump targets observed structural debt, not theoretical violations. Single-Responsibility checks would flag many `routes.py` files for "doing routing AND request validation AND response shaping" but that's the Flask convention; chasing it adds ceremony without payoff.
- **Frontend (Angular) audit** — separate concern; small surface (13 components + 7 services + ~6K LOC); revisit when frontend tech debt becomes a felt pain.
- **Replacing `chain_adapter` direct calls in single-step routes** (`rewrite`, `iterate`, `lint-braindump`, `review`, `generate`) — single AI calls don't benefit from a workflow wrapper; leaving them as-is is correct. Don't migrate for migration's sake.
- **Replacing the FS-based `ProjectRepository` with the SQL adapter** — that's the persistence brain dump's job, not this cleanup.
- **Renaming `quality/` to `pipeline/`** — naming refactor; defer with the modular-restructure brain dump.
- **Per-PR preview deploys / git mailmap consolidation** (4 contributor names for likely 1 person) — operational housekeeping, not code quality.
- **The 6 stale agent worktrees in `.claude/worktrees/`** — harness will reap; no action.
- **Adding type annotations / mypy CI** — type-discipline is a separate brain dump if/when desired.
- **Behaviour changes disguised as refactors** — if a function looks wrong AND broken, file it as a bug fix in a separate PR. This pass is structural cleanup only.

---

*Open-ended charter: walk, find, fix, measure. Seed findings above are the audit's starting points; the executor should add to the list as the walk surfaces more. Outcome: a single PR with a `findings.md` artifact + per-finding commits + a final report on net LOC removed.*
