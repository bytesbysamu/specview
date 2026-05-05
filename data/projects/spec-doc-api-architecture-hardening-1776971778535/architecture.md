# spec-doc-api — Architecture Hardening

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The Flask backend already has the right structural bones: bounded-context modules behind blueprints, a pure service layer, an ELA-compliant adapter boundary over AI providers, and an OpenAPI-first contract. What's missing is the connective tissue that makes those structures self-enforcing — build targets a new contributor can discover, environment config that doesn't require editing source, exception types the service layer can signal distinctly, and logging that makes failures visible after they happen.

This hardening is not an architectural pivot. It is the formalization of decisions already implied by the codebase: the YAML is the contract, so generation must be scriptable; the adapter boundary exists, so it must be testable; the modules are bounded contexts, so their exceptions must not leak each other's domain language. None of these changes are visible to the Angular frontend. All of them are visible to the next executor agent that opens the repo.

The organizing insight is that developer-facing tooling and runtime correctness are the same problem at different layers. A `Makefile` target that fails loudly on a DTO drift is the same guarantee as an `@app.errorhandler` that returns a consistent JSON envelope — both replace implicit, per-person knowledge with explicit, machine-checked rules. This epic adds both layers together because they reinforce each other: a contributor who can trust `make check-dtos` will also trust that a failed request returns a structured error they can handle.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Explicit over implicit | Config values, generation commands, and test conventions are documented and discoverable — not in someone's shell history |
| One consumer, concrete case | Flat per-module exceptions rather than a `SpecDocError` base class; the hierarchy earns its place when the fourth module registers |
| Scars, not theory | Structural tests added for the adapter boundary because that boundary was already violated once; no pre-emptive structural test library |
| No infrastructure before features | `CORS_ORIGINS` from env is one `os.environ.get` in `create_app.py`, not a separate config module — only one caller exists |
| Fail loudly at the boundary | The `@app.errorhandler` in `create_app.py` is the last line of defence; anything that reaches it logs `exc_info=True` so the stack trace is never silently swallowed |

---

## System Boundaries

### What This System Includes

- **Makefile** with six discoverable targets covering dev, test, lint, DTO generation, DTO drift check, and dependency install
- **Requirements split** into prod and dev so CI and production containers don't carry test tooling
- **pyproject.toml** that encodes pytest configuration, including the naming convention that unlocks `condition_expectedOutcome`
- **python-dotenv at startup** and `CORS_ORIGINS` as an environment variable replacing the hardcoded origin list in `create_app.py`
- **`.env.example`** as the single source of documentation for all environment variables the server reads
- **Per-module domain exceptions** (`ProjectNotFoundError`, `ContextReadError`, `AIProviderError`) that let the service layer signal intent rather than silence
- **Centralized `@app.errorhandler`** in `create_app.py` that maps uncaught exceptions to a consistent `{ error, status }` JSON shape
- **Module-level loggers** in every file that currently lacks one (`projects/routes.py`, chain provider files), with a shared logging config in `create_app.py`
- **`conftest.py` factory fixture** (`make_project_dir`) replacing inline ten-line setup blocks repeated across project tests
- **Test function renames** across all existing tests to `condition_expectedOutcome` convention

### What This System Does NOT Include

| Excluded | Reason | Trigger to re-scope |
|----------|--------|---------------------|
| `SpecDocError` base class | One concrete exception type per module is sufficient at current size; the hierarchy adds a registration abstraction with no second consumer | Fourth module registers its own exception type |
| CI pipeline integration for `check-dtos` | No GitHub Actions workflow exists for spec-doc-api today; wiring `check-dtos` into CI before a workflow exists is premature | First CI workflow created for spec-doc-api |
| Per-module DTO generation | Single `dtos/models.py` is appropriate at the current schema size (under 30 models); splitting requires multiple `make` targets and import reorganization | Schema exceeds 30 models or a module needs its own versioning cadence |
| mypy | A separate quality epic; not blocking Phase 2 AI module work | Phase 2 stabilizes type coverage |
| OpenAPI updates for `/api/ai/text/rewrite` | Phase 2 schema work; belongs in the Phase 2 epic to avoid mixed concerns in a single PR | Phase 2 epic begins |

---

## Component Design

### Build Facade

**Purpose**: Replace per-person tribal knowledge about how to run, test, and maintain the repo with six discoverable targets that any executor agent or contributor can run without reading the codebase.

**Key Parts**:
- `Makefile` — the single entry point. Each target is a named, documented shell command. `generate-dtos` encodes the `datamodel-codegen` invocation that currently lives only in shell history. `check-dtos` regenerates to a temp file, diffs against the committed output, and fails non-zero if they diverge — the same guarantee constellation-java provides through the Gradle OpenAPI generator plugin.
- `requirements.txt` (prod) / `requirements-dev.txt` (dev) — the split ensures that `datamodel-codegen`, `pytest`, `flake8`, and `openapi-spec-validator` are not installed in production containers. The dev file includes `-r requirements.txt` so a single `make install` covers both.
- `pyproject.toml` — pytest configuration with `testpaths`, `addopts`, and `python_functions = ["test_*", "*_*"]`. The last setting is the key change: without it, pytest only discovers `test_*` functions, which means `condition_expectedOutcome` names (e.g., `missingText_returns422`) are silently skipped. Encoding this in config rather than a README means the convention is enforced by the test runner, not convention.

**Consumers**: Task 1 (Build tooling), every future executor agent, CI pipeline when created.

**Patterns**: Build Facade — one command surface over multiple underlying tools.

---

### Config Layer

**Purpose**: Make every value the server reads from the environment visible, documented, and overridable without editing source files.

**Key Parts**:
- `create_app.py` startup block — `load_dotenv()` called before any `os.environ.get`. Order matters: the dotenv file sets defaults that env vars can override, which is the right precedence for a container deployment.
- `CORS_ORIGINS` env var — replaces the hardcoded list in `create_app.py`. The existing two values (`http://localhost:4201`, `http://localhost:4202`) become the default, so no `.env` file is required for local dev. Comma-separated parsing happens once, in `create_app.py`, where it is consumed.
- `.env.example` — documents `AI_PROVIDER`, `PORT`, `SPEC_DOC_DIR`, and `CORS_ORIGINS` with their defaults and valid values. This is the single place a new contributor looks to understand the server's configuration surface.

**Why no `config.py` module**: A dedicated config module is worth its indirection when multiple callers import from it. Currently `SPEC_DOC_DIR` has one caller (config.py already exists for filesystem paths); `CORS_ORIGINS` will have one caller (`create_app.py`). Adding a second config module for four env vars creates import indirection with no second consumer. The Bubls pattern (`core/config.py`) is the right shape when a product has cross-module shared config — spec-doc-api does not have that yet.

**Consumers**: Task 2 (Config hardening), any deployment environment that is not localhost.

**Patterns**: Fail-fast at startup (missing required env vars raise at `load_dotenv` time, not at first request).

---

### Error Handling

**Purpose**: Replace bare `except Exception` in five project route handlers with typed exceptions the service layer can signal distinctly, and a central handler that converts them to a consistent HTTP envelope.

**Key Parts**:
- `ProjectNotFoundError` in `modules/projects/` — raised by `service.py` when a project directory or `project.json` does not exist. The route maps this to HTTP 404. Currently, this case is indistinguishable from a filesystem permission error — both surface as `500: "Failed to get project"`.
- `ContextReadError` in `modules/context/` — raised when a context file cannot be read. The route maps this to HTTP 500 with a structured message rather than a bare exception log.
- `AIProviderError` in `modules/ai/` — raised when the chain adapter's underlying provider fails. The route maps this to HTTP 502 (bad gateway) because the failure is in a downstream dependency, not in the request itself. Distinct from `ProviderError` already in `modules/chain/errors.py` — the chain module's error is an infrastructure-layer signal; `AIProviderError` is the feature-layer signal that the AI route exposes to callers.
- `@app.errorhandler` in `create_app.py` — catches any exception that escapes a route handler. Returns `{ "error": str(e), "status": 500 }`. Logs `exc_info=True` so the full stack trace appears in server logs regardless of what the client sees. This is the constellation-java `GlobalExceptionHandler` pattern at Flask scale.

**Why flat exceptions, not a hierarchy**: A `SpecDocError` base class enables a single `@app.errorhandler(SpecDocError)` registration and lets the central handler dispatch by subclass. At three modules, each with one exception type, this saves two `@app.errorhandler` registrations. The cost is an additional abstraction with a three-type-class library as its only consumer. The flat approach — one `errorhandler` per type, or a single catch-all `Exception` handler — is simpler and wrong in fewer ways. The hierarchy earns its place when the fourth module appears.

**Consumers**: Task 3 (Error handling), all five project route handlers, the AI rewrite route, future Phase 2 AI route handlers.

**Patterns**: Anti-Corruption Layer at the service boundary — service raises domain exceptions, route translates to HTTP status codes, the central handler catches everything that escapes.

---

### Observability and Test Conventions

**Purpose**: Make failures visible in logs and make the test suite self-consistent so a new contributor or executor agent can add tests without deciphering existing naming and fixture patterns.

**Key Parts**:
- Module-level logger in every file — `logger = logging.getLogger(__name__)` is a one-line addition to `modules/projects/routes.py` and the chain provider files that currently have none. The `__name__`-based logger name means log lines carry the module path, which makes filtering by module possible in production.
- Logging config in `create_app.py` — sets the root logger to `INFO`, ensures `ERROR` with `exc_info=True` is consistent, and adds elapsed-time logging for chain provider calls. Centralizing this means new modules inherit the config automatically.
- `conftest.py` factory fixture `make_project_dir(tmp_path, name, files)` — creates a populated project directory structure under pytest's `tmp_path`. Currently, the same ten-line setup block appears inline in multiple test functions; each repetition is a maintenance burden and a divergence risk when the project directory structure changes. The factory fixture ensures that structure is defined once.
- `condition_expectedOutcome` renames — existing test functions like `test_list_sorted_newest_first` become `newestFirst_sortsBeforeOlderProjects`. No logic changes, no new assertions — only function names, governed by `pyproject.toml` so the convention is machine-enforced.

**Why test renames matter**: The naming convention is not aesthetic. `condition_expectedOutcome` forces the test author to name the precondition and the assertion separately, which surfaces tests that have no clear condition (testing the happy path only) and tests that assert multiple outcomes (should be split). Renaming existing tests applies the discipline retroactively and establishes the baseline for Phase 2 tests.

**Consumers**: Task 4 (Observability + test conventions), every Phase 2 and Phase 3 test file that inherits from conftest.py, executor agents debugging provider failures.

**Patterns**: Fixture factory over inline setup. Named logging over print. Convention-in-config over convention-in-docs.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Build tooling | GNU Make | Already present on all developer machines; zero new tooling dependencies; targets are shell commands, which means they compose with CI exactly as they run locally |
| Config | python-dotenv | Single `load_dotenv()` call at startup; env var overrides still work; no custom parser required |
| DTO generation | datamodel-codegen | Already proven — it generated the current `dtos/models.py`; moving it to `requirements-dev.txt` and a Makefile target formalizes what is already true |
| Linting | flake8 | In requirements-dev.txt already as openapi-spec-validator's transitive dep; explicit declaration costs nothing |
| Exception types | Python built-in exceptions | No library required; `ProjectNotFoundError(Exception)` is three lines |
| Logging | Python stdlib logging | Already used in `context/service.py`; consistent with `logging.getLogger(__name__)` across all modules |
| Testing | pytest + pytest-flask | Already in use; pyproject.toml adds the naming configuration that was missing |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Flat per-module exceptions, no `SpecDocError` base | Three exception types, three consumers — the hierarchy would add indirection with no current return | When the fourth module registers, the base class is a one-line addition and its absence cost nothing until then |
| Single `dtos/models.py`, not per-module generated files | Schema has under 30 models; one generation target is simpler than one per module; the generated header already identifies provenance | When a module needs its own DTO versioning cadence, per-module generation is the right split |
| `CORS_ORIGINS` in `create_app.py`, not a new `config.py` | One caller; the existing `config.py` handles filesystem paths; a second config module adds import indirection with no current benefit | If three or more modules need cross-cutting config access, a shared `config.py` is the right extraction |
| `make check-dtos` diffs committed vs regenerated, not just runs generation | A generation target that always succeeds cannot catch drift; the diff step is what turns it into a CI-grade check | Requires the temp file pattern, which is slightly more complex than a simple `generate-dtos` invocation |
| `@app.errorhandler(Exception)` catch-all, not per-type registrations | Simpler until the hierarchy exists; any exception that the route handler didn't anticipate still gets a structured response | Over-broad — a programming error that raises `AttributeError` will return a 500 JSON response rather than a clear stack trace in development (mitigated by `exc_info=True` in the log) |
| `python_functions = ["test_*", "*_*"]` in pyproject.toml | Unlocks `condition_expectedOutcome` naming without requiring `Test` prefix or `test_` prefix on every function; signals intent rather than enforcing a prefix | Slightly broader discovery — any `*_*` function in a test file is collected; in practice this is contained to test files |

---

## Patterns

### Build Facade

**When to use**: When a developer-facing operation involves more than one command, or when the exact invocation is non-obvious and likely to diverge between contributors.

**How it works**: A named Makefile target wraps the full invocation, including flags and file paths that are easy to forget. The target is the documented entry point; the underlying command is an implementation detail.

**Example in this system**: `make check-dtos` wraps the `datamodel-codegen` invocation against `openapi.yaml`, pipes output to a temp file, diffs against `dtos/models.py`, and exits non-zero if they differ. Without the target, a contributor regenerating DTOs must discover the correct flags independently.

---

### Domain Exception → HTTP Status Mapping

**When to use**: Whenever a service function can fail in a way that has distinct HTTP semantics — not found (404), bad input (400), downstream failure (502), or unexpected internal error (500).

**How it works**: The service layer raises a typed exception. The route handler catches the specific type and maps it to an HTTP status. The central `@app.errorhandler` catches anything that escapes with a fallback 500. No route handler contains `except Exception` with a silent log.

**Example in this system**: `projects/service.py` raises `ProjectNotFoundError` when a project directory does not exist. The route catches it and returns 404. Before hardening, the same route catches all exceptions and returns 500 — the distinction between "not found" and "permission denied" is invisible to the caller.

---

### Convention in Config

**When to use**: When a code convention (naming, discovery, test isolation) needs to be enforced consistently across multiple contributors and executor agents, and the convention can be encoded in a config file rather than documented prose.

**How it works**: The tool reads its own config and applies the convention automatically. A new contributor who follows the tool's output naturally follows the convention without reading a style guide.

**Example in this system**: `python_functions = ["test_*", "*_*"]` in `pyproject.toml` means pytest discovers `condition_expectedOutcome`-named functions without any manual configuration. The convention is enforced by the test runner, not by code review.

---

## Execution Flow

```
[All four tasks are independent — no cross-task dependencies]

Task 1: Build Tooling    Task 2: Config Hardening
  Makefile                 python-dotenv at startup
  requirements split       CORS_ORIGINS from env
  pyproject.toml           .env.example

Task 3: Error Handling   Task 4: Observability + Test Conventions
  Per-module exceptions    Module-level loggers
  @app.errorhandler        Logging config in create_app.py
  Route handler rewrites   conftest.py factory fixtures
                           Test function renames
```

Tasks 1 through 4 have no runtime dependencies on each other. They share the same `create_app.py` file — Task 2 adds `load_dotenv()` and `CORS_ORIGINS` parsing, Task 3 adds `@app.errorhandler` registration, and Task 4 adds logging config — but these are additive changes that do not require sequencing. Any task can be committed independently and `make test` will pass after each commit.

The only practical ordering constraint is that `pyproject.toml` (Task 1) should land before test renames (Task 4), because the `python_functions` setting is what makes `condition_expectedOutcome` names discoverable. Renaming tests before that setting is in place would cause pytest to silently skip the renamed functions.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview