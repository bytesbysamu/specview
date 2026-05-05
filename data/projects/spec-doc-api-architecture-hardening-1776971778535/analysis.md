# spec-doc-api — Architecture Hardening — Analysis

## The Problem

spec-doc-api has bare `except Exception` in every route, no Makefile, hardcoded CORS origins, a DTO file with no documented regeneration path, and a per-module `modules/context/dto.py` shim that duplicates generated types. Phase 2 adds ~7 routes and ~20 tests — building on this foundation means every new file inherits every deficiency. Four hardening tasks, zero behavior change to the Angular frontend.

## Hard Constraints

- Zero behavior change to the Angular frontend — all six changes are internal
- Flask + filesystem only; no DB, no auth consumer exists, both stay out
- `datamodel-codegen` is already installed and proven; generation approach is settled
- 94 tests must stay green across the refactor

## Open Questions

- **Exception hierarchy**: flat per-module exceptions (one `errorhandler` registration per type) or shared `SpecDocError` base (one registration catches all)? Brain dump leans flat now, base class at Phase 3. Commit to flat so the epic doesn't hedge.
- **DTO generation location**: single `dtos/models.py` (current) or per-module `modules/X/dto_generated.py`? Brain dump leans single file. Decide before writing the Makefile target — it changes the `generate-dtos` command.
- **CI check-dtos scope**: `make check-dtos` as a CI step assumes a GitHub Actions pipeline for spec-doc-api exists. Does it? If not, the target is local-only for now and the CI wiring is Phase 3.

## Dependencies & Sequencing

- Exception hierarchy decision blocks: domain exception files, route handler rewrites, error handler in `create_app.py`
- DTO location decision blocks: `generate-dtos` and `check-dtos` Makefile targets
- Config/dotenv, requirements split, logging, test naming — all independent, parallelizable
- Makefile shell is unblocked; the two DTO and exception targets wait on the decisions above

## Explicitly Out of Scope

- `SpecDocError` base class — no second consumer until Phase 3 has 4+ modules; defer, trigger: fourth module registered
- CI pipeline integration for `check-dtos` — no GitHub Actions workflow exists for spec-doc-api; defer, trigger: first CI workflow created
- `openapi.yaml` update with `/api/ai/text/rewrite` — Phase 2 schema work, not hardening; belongs in Phase 2 epic
- `sys.path.insert` fix and test comment in `test_ai_rewrite.py` — cleanup, fold into Phase 2 test pass
- mypy — already deferred; separate quality epic