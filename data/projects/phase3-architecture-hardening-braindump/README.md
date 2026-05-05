# spec-doc-api — Architecture Hardening

## What

Bring spec-doc-api up to the standard set by Bubls and constellation-java across six dimensions: DTO generation pipeline, error handling, configuration, logging, testing conventions, and build scripts. None of this changes behavior the Angular frontend sees. All of it changes how confidently a new engineer (or executor agent) can work in the codebase.

### 1. Build-time DTO generation, not committed code

`dtos/models.py` is currently generated once and committed. The generation command is not in the repo. `datamodel-codegen` is not in `requirements.txt`. If `openapi.yaml` changes, there is no documented path to regenerate the models — a developer edits the YAML and either re-runs a command they have to discover, or edits the Pydantic classes by hand and drifts the spec.

Fix: `dtos/models.py` stays committed (acceptable for a deterministic generator), but the generation command becomes a first-class `make generate-dtos` target. `datamodel-codegen` moves to `requirements-dev.txt`. A CI check (`make check-dtos`) regenerates and diffs — if the committed file and the regenerated output diverge, the build fails. This is how constellation-java handles it with the Gradle OpenAPI generator plugin (line 156 of build.gradle).

Consumer: every developer, every CI run, every executor agent that modifies openapi.yaml.

### 2. Custom exceptions + centralized error handler

Every route handler in `modules/projects/routes.py` has a bare `except Exception: return jsonify({"error": "Failed to ..."}), 500`. There are no custom exception types. The service layer has no way to signal "project not found" vs "project malformed" vs "filesystem permission denied" — every failure looks the same to the caller.

Fix: Domain exceptions in each module (`ProjectNotFoundError`, `ContextReadError`, `AIProviderError`). The service raises; the route catches the specific type and maps to HTTP status. A Flask `@app.errorhandler` in `create_app.py` catches anything that reaches the app level and returns a consistent `{ error, status }` JSON shape. This is the pattern from Bubls (`modules/waitlist/service.py:22-27`) and constellation-java (`GlobalExceptionHandler.java:15-31`).

Consumer: all route handlers, all callers of service functions, future AI module routes.

### 3. Structured logging in all modules

`modules/context/routes.py` has `logger = logging.getLogger(__name__)` and uses it. `modules/projects/routes.py` has nothing. When a project fails to load in production, there is no trace. The chain module has no logging at the provider level — a slow or failing Claude CLI call is invisible.

Fix: `logger = logging.getLogger(__name__)` at the top of every module file. Log at INFO on success (project created, context written), ERROR on failure with `exc_info=True` for stack traces. Provider calls in the chain module log elapsed time and exit code. One logging config in `create_app.py` that applies to all modules.

Consumer: every service and route file, executor agent debugging provider failures.

### 4. Config via python-dotenv, CORS from env

CORS origins are hardcoded in `create_app.py` (`['http://localhost:4201', 'http://localhost:4202']`). When the Angular port changes (already changed once this session), config.py or create_app.py needs editing. `SPEC_DOC_DIR` is the only env override today.

Fix: `python-dotenv` reads `.env` at startup. `CORS_ORIGINS` env var (comma-separated) replaces the hardcoded list. `AI_PROVIDER`, `PORT`, `SPEC_DOC_DIR` all documented in `.env.example`. Bubls pattern (`core/config.py:1-30`): `load_dotenv()` at top, `os.environ.get("KEY", default)` for every config value, pinned constants (model names, file paths) as module-level capitals after the env block.

Consumer: local dev, executor container, any deployment that isn't localhost.

### 5. requirements split + pyproject.toml

`requirements.txt` has 8 lines mixing prod and dev deps (`pytest`, `openapi-spec-validator`). There is no pyproject.toml. pytest config is undocumented — no testpaths, no naming convention.

Fix:
- `requirements.txt` — prod only: flask, flask-cors, pydantic, anthropic, pyyaml, python-dotenv, gunicorn
- `requirements-dev.txt` — `-r requirements.txt` + pytest, pytest-flask, datamodel-codegen, openapi-spec-validator, flake8
- `pyproject.toml` for pytest: testpaths, `python_functions = ["test_*", "*_*"]` (enables `condition_expectedOutcome` naming from Bubls), addopts for verbosity

Consumer: CI, executor container pip install, any contributor.

### 6. Makefile with standard targets

No Makefile exists. To run tests you have to know `pytest`. To regenerate DTOs you have to remember the datamodel-codegen invocation. To start the dev server you have to know to run `python app.py`.

Fix: `Makefile` at repo root with:
- `make dev` — `python app.py`
- `make test` — `pytest -v`
- `make lint` — `flake8`
- `make generate-dtos` — datamodel-codegen invocation against openapi.yaml → dtos/models.py
- `make check-dtos` — regenerate to a temp file, diff against committed, fail if different
- `make install` — `pip install -r requirements-dev.txt`

Consumer: developer onboarding, CI pipeline, executor agent running tasks.

### 7. Test naming and fixture conventions

Tests in `test_project.py` use `test_list_sorted_newest_first` naming. Tests in chain module use generic names. No factory fixtures — test data is constructed inline per test. No shared test helpers for common assertions.

Fix: Adopt `condition_expectedOutcome` naming from Bubls (`pyproject.toml:8-9`). Add factory fixtures for common objects — `make_project_dir(tmp_path, name, files)` in `conftest.py` replaces 10-line setup blocks repeated across test functions. Separate conftest fixtures by scope: session-level app, function-level tmp_path, module-level seeded data.

Consumer: every test file, executor agent writing Phase 2 and 3 tests.

## Why now

Phase 1 and 2 are functional — 94 tests passing, Flask live on 3101. Phase 2 (AI text module) is about to be built. The AI module will add ~7 route handlers, ~7 prompt builder functions, and ~20 tests. If we build it on the current foundation, it inherits bare `except Exception`, undocumented generation steps, and inconsistent logging. Fixing the foundation now costs one epic with zero behavior change. Fixing it after Phase 2 means touching every file twice.

Constellation-java showed the value of this investment: the `@RestControllerAdvice` global handler and `@Valid` annotations absorbed every new endpoint without new error-handling code. Bubls showed it at the Flask level: every new module registered its custom exceptions and got centralized handling for free. spec-doc-api can have that too — and it is a smaller codebase, so the cost is lower.

The DTOs problem is urgent: Phase 2 will need new schemas (AI request/response shapes, lint advisory, review score). If generation is not automated, every schema addition is a manual Pydantic edit that may drift from the YAML. The generator is already installed and proven — it generated the current models. It just needs to be in the build.

## What's missing

Two decisions before writing the first file:

- **Exception hierarchy**: One base `SpecDocError` that all domain exceptions inherit from, or flat domain exceptions per module with no shared base? The shared-base approach lets the global handler catch everything with `@app.errorhandler(SpecDocError)` in one registration. The flat approach is simpler but requires one `errorhandler` registration per exception type. Bubls uses flat (per-module exceptions, per-route handling). Spring uses hierarchy (`RuntimeException` subtypes caught by `@RestControllerAdvice`). For spec-doc-api's current size, flat is fine — add base class when Phase 3 has 4+ modules.
- **DTO generation location**: Generate into `dtos/models.py` (current, all models in one file) or generate per-module into `modules/X/dto_generated.py` alongside handwritten `dto.py`? Per-module is cleaner but requires multiple generation commands. Single file is simpler and works until the schema has 30+ models.

## Explicitly out of scope

- Database, migrations, Alembic — spec-doc-api is filesystem only; no DB means no repository pattern beyond service functions
- Auth middleware — single-user local tool; no auth consumer exists
- Rate limiting — no current consumer
- OpenAPI serving (Swagger UI) — no named consumer until developer onboarding is an explicit need
- Type checking (mypy) — valuable but a separate quality epic; not blocking Phase 2
