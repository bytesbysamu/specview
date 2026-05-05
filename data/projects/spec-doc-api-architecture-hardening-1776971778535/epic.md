# spec-doc-api — Architecture Hardening

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Phase 2 (AI text module) adds approximately seven route handlers and twenty tests. Built on the current foundation, every new file inherits bare `except Exception` blocks, undocumented DTO generation, and inconsistent logging — defects that are cheap to fix once and expensive to fix after they multiply. Hardening now costs one focused epic with zero behavior change to the Angular frontend. Hardening after Phase 2 means touching every file twice.

The DTO problem is time-sensitive. Phase 2 will introduce new schemas for AI request and response shapes. Without an automated generation step, every schema addition is a manual Pydantic edit that may silently drift from `openapi.yaml`. The generator (`datamodel-codegen`) is already installed and proven — the current models were generated with it. It needs to be in the build, not in someone's shell history.

Developer confidence is the deliverable. When an executor agent or new contributor can run `make test`, `make check-dtos`, and `make lint` and trust the results, the onboarding cost of every future task drops to near zero. Constellation-java demonstrated this: once `@RestControllerAdvice` and `@Valid` were in place, every subsequent endpoint got centralized error handling for free. Bubls demonstrated it at the Flask level. spec-doc-api is a smaller codebase — the cost is lower and the return comes sooner.

**Value Proposition**: One hardening epic eliminates the hidden tax on every Phase 2 and Phase 3 task by making the foundation explicit, scriptable, and testable.

---

## Scope

### What This Epic Covers

- **Build tooling** — Makefile with standard targets, requirements split (prod/dev), pyproject.toml with pytest configuration, `/api/ai/text/rewrite` added to `openapi.yaml` so generated DTOs include `RewriteRequest` / `RewriteResponse`
- **Config hardening** — `python-dotenv` at startup, `CORS_ORIGINS` from env, documented `.env.example`
- **Error handling** — generated DTOs wired into every route handler (kills hand-rolled `data.get(...)` parsing and deletes `modules/context/dto.py` shim); domain exceptions per module; centralized `@app.errorhandler(ValidationError)` → 422 and `@app.errorhandler(Exception)` → 500 in `create_app.py`
- **Observability + test conventions** — structured logging in every module file, `conftest.py` factory fixtures, `condition_expectedOutcome` naming applied across existing tests

### What This Epic Does NOT Cover

- ❌ `SpecDocError` base class — no second consumer until Phase 3 has four or more modules; trigger: fourth module registered
- ❌ CI pipeline integration for `check-dtos` — no GitHub Actions workflow exists for spec-doc-api; trigger: first CI workflow created
- ❌ Per-module DTO generation — single `dtos/models.py` is sufficient at current schema size; trigger: schema exceeds thirty models
- ❌ mypy — separate quality epic; not blocking Phase 2
- ❌ `openapi.yaml` updates for `/api/ai/text/rewrite` — Phase 2 schema work, belongs in Phase 2 epic

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Build tooling** | None | 2, 3, 4 | 1 day | High |
| 2 | **Config hardening** | None | 1, 3, 4 | 0.5 days | High |
| 3 | **Error handling** | None | 1, 2, 4 | 1 day | High |
| 4 | **Observability + test conventions** | None | 1, 2, 3 | 1 day | High |

### Task 1: Build tooling

Adds a `Makefile` with six targets (`dev`, `test`, `lint`, `generate-dtos`, `check-dtos`, `install`), splits `requirements.txt` into prod-only and `requirements-dev.txt` for dev dependencies, and adds `pyproject.toml` with `testpaths` and `python_functions = ["test_*", "*_*"]` to unlock `condition_expectedOutcome` test naming. The `generate-dtos` target codifies the existing `datamodel-codegen` invocation against `openapi.yaml → dtos/models.py`; `check-dtos` regenerates to a temp file and diffs — non-zero diff fails the target.

**Port budget**: Makefile (~30 lines), pyproject.toml (~15 lines), requirements resplit (~10 lines total) — no route handlers, no exception classes, no environment files; `datamodel-codegen` moves from implicit to `requirements-dev.txt`, nothing else changes.

### Task 2: Config hardening

Adds `python-dotenv` to `requirements.txt` and calls `load_dotenv()` at startup in `create_app.py`. Replaces the hardcoded `['http://localhost:4201', 'http://localhost:4202']` CORS list with `CORS_ORIGINS` env var (comma-separated, with the existing two values as the default). Documents `AI_PROVIDER`, `PORT`, `SPEC_DOC_DIR`, and `CORS_ORIGINS` in `.env.example`. Pinned constants (model names, file paths) remain module-level capitals after the env block, following the Bubls `core/config.py` pattern.

**Port budget**: `create_app.py` changes (~20 lines), `.env.example` (~10 lines) — no new routes, no exception types, no test changes; this task deliberately does not introduce a `config.py` module (one caller, not worth the indirection).

### Task 3: Error handling

Adds domain exception classes to each module (`ProjectNotFoundError`, `ContextReadError`, `AIProviderError`) — one file per module, three to five lines each. Route handlers are rewritten to raise specific types from the service layer and catch them explicitly, mapping to HTTP status codes. A single `@app.errorhandler` registered in `create_app.py` catches anything that escapes a route and returns a consistent `{ "error": "...", "status": 500 }` JSON shape. No bare `except Exception` remains in any route.

**Port budget**: Three exception files (~15 lines each), `create_app.py` errorhandler additions (~15 lines), route handler modifications across `modules/projects/routes.py` and `modules/ai/routes.py` (~30 lines total) — no `SpecDocError` base class (flat per-module, one registration per type), no middleware, no new routes.

### Task 4: Observability + test conventions

Adds `logger = logging.getLogger(__name__)` to every module file that is missing it (projects routes, chain providers), a shared logging config in `create_app.py` (`INFO` on success, `ERROR` with `exc_info=True` on failure, elapsed time logged for chain provider calls). Adds `conftest.py` factory fixtures (`make_project_dir(tmp_path, name, files)`) to replace repeated ten-line setup blocks across test functions. Renames existing test functions to `condition_expectedOutcome` convention — behavior is unchanged, only function names change.

**Port budget**: Logger additions (~one line per file, ~ten files), logging config (~10 lines), `conftest.py` (~50 lines), test renames (no logic changes) — no new test cases, no new assertions, no new fixtures beyond `make_project_dir` and scope-annotated app/client fixtures.

---

## Success Criteria

This epic is complete when:

- ✅ `make test` runs and all existing tests pass (baseline: executor records at pre-flight; currently 172 — confirm with `python -m pytest --collect-only -q` before starting)
- ✅ `make check-dtos` exits 0 — committed `dtos/models.py` matches regenerated output
- ✅ `make lint` exits 0
- ✅ `CORS_ORIGINS` is configurable via environment variable without editing any source file
- ✅ Every module file (`routes.py`, `service.py`, provider files) has a module-level logger; INFO logged on success, ERROR with `exc_info=True` on failure
- ✅ No bare `except Exception` exists in any route handler
- ✅ All existing test functions follow `condition_expectedOutcome` naming
- ✅ `conftest.py` provides at least `make_project_dir` fixture used by three or more test functions

---

## Non-Goals

- ❌ `SpecDocError` base class — flat per-module exceptions are sufficient; add hierarchy when the fourth module registers, not before
- ❌ CI integration for `check-dtos` — no GitHub Actions pipeline exists for spec-doc-api; wiring this into CI is Phase 3 work triggered by the first workflow
- ❌ Per-module DTO files — single `dtos/models.py` matches current schema size; splitting is premature and adds Makefile complexity with no current benefit
- ❌ New test cases — test conventions apply to existing tests only; Phase 2 writes the new tests on the new foundation
- ❌ mypy — deferred; a separate quality epic when Phase 2 stabilizes type coverage

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview