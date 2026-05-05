# Modular Restructure — Analysis

## The Problem
`api/modules/` has 10 flat packages where three (`spec_gen`, `task_gen`, `implementation_guide`) are conceptually one domain sharing the same chain adapter and workflow runtime. The flat shape was acceptable at 3 modules; at 10 it's navigation noise. Five incoming SaaS brain dumps and ~4 bucket-7 modules push the count to 17–20 without a restructure.

## Hard Constraints
- **Import paths only.** No logic changes, no Blueprint URL changes, no openapi.yaml changes, no test-assertion changes. Any diff touching a function body is out of scope.
- **Must land before bucket 7.** The restructure is the landing pad for SaaS modules; they cannot land first and then be shuffled retroactively.
- **No toolchain changes.** `make generate-dtos` and `make check-dtos` must pass unchanged — DTOs live at `api/dtos/` and don't import from `modules/`.

## Open Questions
- **Does `implementation_guide` have a routes file?** The file-by-file mapping shows only `prompts.py` moving; if `implementation_guide/routes.py` exists and registers a Blueprint, it's absent from the `create_app.py` before/after block and the mapping is incomplete. Answer: confirm with `ls modules/implementation_guide/` before writing the guide.
- **Does `quality/` register a Blueprint?** It's missing from both the before and after `ENABLED_MODULES` blocks. Either it has no HTTP routes, or it auto-registers, or it was accidentally omitted — the guide needs to be explicit. Answer: check `quality/routes.py` exists or doesn't.
- **Is `saas_optional` in the structural test exhaustive?** Hardcoding `{auth, billing, usage, observability}` means a fifth SaaS module (e.g. `notifications`) trips the test without a PR to update the allowlist. Decide: exhaustive allowlist (forces explicit PR) vs. a naming-convention check (e.g. any module with a `saas_` prefix is legal).

## Dependencies & Sequencing
- Structural test ships in the **same PR** as file moves; a separate PR creates a window where the old shape passes the new test.
- Any in-flight branch touching `modules/` must rebase after this lands — note in the PR description.
- `make test` is expected to fail between the openapi-edit step and the route-handler-add step (existing known gap from `everyOpenapiPath_hasRouteHandler`); this refactor doesn't change that, but the guide should say so explicitly to avoid confusion mid-execution.

## Explicitly Out of Scope
- **Renaming `quality/` to `pipeline/`** — separate concern, separate PR.
- **Splitting `chain/` into sub-packages** — already cohesive; no second consumer exists to justify it.
- **Moving `AICall` into `ai/workflows/steps/`** — it's generic runtime infrastructure; spec-gen-specific step kinds don't exist yet.
- **Per-package `CLAUDE.md` files** — single `api/CLAUDE.md` is the source of truth; per-package docs add maintenance burden with no payoff for a solo codebase.
- **Future SaaS modules (`auth`, `billing`, `usage`, `observability`)** — the restructure creates the slots; populating them is each SaaS epic's concern.