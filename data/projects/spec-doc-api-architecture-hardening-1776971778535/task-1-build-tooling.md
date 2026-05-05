# Task 1: Build Tooling — Executor Implementation Guide

**Task**: Add Makefile (6 targets), split requirements, add `pyproject.toml` with pytest config, declare `/api/ai/text/rewrite` in `openapi.yaml` so generated DTOs include `RewriteRequest` / `RewriteResponse` (consumed by Task 3).

---

## 1. Context

Task 1 formalizes the build surface for the Flask backend at `flask/`. Right now the only way to run tests is to know the exact `python -m pytest` invocation; the only way to regenerate DTOs is to recall a `datamodel-codegen` flag set that lives in no file; and `pytest` shares `requirements.txt` with production containers. This task makes all three discoverable, repeatable, and machine-checkable — without touching any route handler, exception class, or environment file.

**Trade-offs considered**:
- `Makefile` at `flask/` vs. project-root `Makefile` — `flask/` is correct; the project root already has `package.json` targets for the Angular + Express layer; a separate Makefile per subsystem avoids cross-contamination.
- `pyproject.toml` vs. `setup.cfg` for pytest config — `pyproject.toml` is the current standard; `setup.cfg` is legacy; both work, the former is chosen for longevity.
- `datamodel-code-generator` in `requirements-dev.txt` vs. a pinned version lock — unpinned `datamodel-code-generator` matches the pattern used by every other dep in this repo; pinning is a CI concern for a later task.

---

## 2. Pre-flight

Run these commands **from `flask/`** BEFORE editing any file:

```bash
cd {WORKSPACE}/spec-doc/flask

git status                                 # flag any unrelated M/?? entries
git diff HEAD -- requirements.txt          # confirm clean before split

# Record baseline test count — exact number required, not an estimate
python -m pytest --collect-only -q 2>&1 | tail -3
```

**If working tree is dirty on `requirements.txt`**: stash or commit unrelated changes before starting.

**Baseline recorded**: run the collect command above and write down N (e.g., "47 tests collected").

---

## 3. Files

### To Create (new)
- `flask/Makefile` — 6-target build facade; wraps dev server, pytest, flake8, datamodel-codegen
- `flask/pyproject.toml` — pytest config: testpaths, pythonpath, addopts, python_functions
- `flask/requirements-dev.txt` — dev-only deps; includes `-r requirements.txt`
- `flask/tests/test_tooling.py` — verifies the tooling artifacts are well-formed; first file using `condition_expectedOutcome` naming
- `flask/dtos/models.py` is regenerated (not created) — after openapi.yaml updates, running `make generate-dtos` produces `RewriteRequest` and `RewriteResponse` classes; the regenerated file is committed alongside openapi.yaml so `make check-dtos` exits 0

### To Modify
- `flask/requirements.txt` — remove `pytest>=8.0.0` and `openapi-spec-validator>=0.5`; keep prod-only deps
- `flask/openapi.yaml` — declare `RewriteRequest` + `RewriteResponse` schemas and the `POST /api/ai/text/rewrite` path so `make generate-dtos` emits the types route handlers will consume in Task 3

### To Leave Alone
- `flask/dtos/models.py` — stays committed; `check-dtos` guards against drift; gitignore deferral is explicitly out of scope for this task
- `flask/tests/conftest.py` — `sys.path.insert` becomes redundant after `pyproject.toml` adds `pythonpath = ["."]` but is harmless; removal is Task 4 (test cleanup)
- `flask/create_app.py` — no changes; CORS hardening is Task 2
- All existing test files — no renames; that's Task 4

---

## 4. Implementation Steps

### Step 1: Split requirements

**Action**: Move `pytest>=8.0.0` and `openapi-spec-validator>=0.5` from `requirements.txt` into a new `requirements-dev.txt`. Add `datamodel-code-generator` and `flake8` as new dev deps.

**File**: `flask/requirements.txt` (existing)

Replace with:
```
flask>=3.0.0
flask-cors>=4.0.0
anthropic
pydantic>=2.0.0
pyyaml
```

**File**: `flask/requirements-dev.txt` (new)

```
-r requirements.txt
pytest>=8.0.0
openapi-spec-validator>=0.5
datamodel-code-generator
flake8
```

**Verify**: `grep pytest flask/requirements.txt` — expect no output (pytest must NOT appear in prod file).

---

### Step 2: Add `pyproject.toml`

**Action**: Create `flask/pyproject.toml` with pytest configuration. The `python_functions` key is the critical setting — without it, any function named `condition_expectedOutcome` (no `test_` prefix) is silently skipped by pytest. `pythonpath = ["."]` makes `from modules.X import Y` work without `sys.path.insert` in every test file.

**File**: `flask/pyproject.toml` (new)

```toml
[tool.pytest.ini_options]
testpaths   = ["tests", "modules"]
pythonpath  = ["."]
addopts     = "-v"
python_functions = ["test_*", "*_*"]
```

**Verify**: `cd flask && python -m pytest --collect-only -q 2>&1 | grep "test session starts"` — expect pytest to start without "no configuration file found" warnings; collected count should match the baseline from Pre-flight.

---

### Step 3: Add Makefile

**Action**: Create `flask/Makefile` with six named targets. All targets assume `flask/` as the working directory (the Makefile's own directory). The `check-dtos` target is the CI-grade guard: it regenerates DTOs to a temp file, diffs against the committed `dtos/models.py`, exits non-zero on drift, and removes the temp file regardless of outcome.

**File**: `flask/Makefile` (new)

```makefile
.PHONY: dev test lint generate-dtos check-dtos install

PYTHON = python

## Install production and development dependencies
install:
	pip install -r requirements.txt -r requirements-dev.txt

## Run the Flask development server (port from PORT env var, default 3101)
dev:
	$(PYTHON) app.py

## Run the full test suite
test:
	$(PYTHON) -m pytest

## Lint with flake8 (generated dtos/models.py excluded)
lint:
	flake8 . --max-line-length=120 --exclude=__pycache__,dtos/models.py

## Regenerate dtos/models.py from openapi.yaml
generate-dtos:
	datamodel-codegen \
		--input openapi.yaml \
		--output dtos/models.py \
		--output-model-type pydantic_v2 \
		--input-file-type openapi

## Fail non-zero if committed dtos/models.py does not match what would be generated
check-dtos:
	@TMPFILE=$$(mktemp /tmp/models_check_XXXXXX.py); \
	datamodel-codegen \
		--input openapi.yaml \
		--output $$TMPFILE \
		--output-model-type pydantic_v2 \
		--input-file-type openapi 2>/dev/null; \
	diff dtos/models.py $$TMPFILE; \
	EXIT=$$?; \
	rm -f $$TMPFILE; \
	exit $$EXIT
```

**Verify**:
```bash
cd flask
make install          # should complete without error
make test             # should pass same count as baseline
make check-dtos       # should exit 0 (committed file matches generated)
```

---

### Step 4: Declare `/api/ai/text/rewrite` in `openapi.yaml` and regenerate DTOs

**Action**: Add the rewrite path + `RewriteRequest` + `RewriteResponse` component schemas to `flask/openapi.yaml` so generated DTOs include them. Without this, `dtos/models.py` has no `RewriteRequest` and Task 3 cannot wire DTO validation into `/rewrite`. Run `make generate-dtos` to refresh `dtos/models.py` after editing — commit the regenerated file alongside the openapi change.

**File**: `flask/openapi.yaml` (existing; 8 paths, no AI entries yet)

Append under `paths:`:

```yaml
  /api/ai/text/rewrite:
    post:
      summary: Rewrite text with optional instructions
      operationId: rewriteText
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RewriteRequest'
      responses:
        '200':
          description: Rewritten text
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RewriteResponse'
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '502':
          description: Upstream AI provider failure
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

Append under `components: schemas:`:

```yaml
    RewriteRequest:
      type: object
      required: [text]
      properties:
        text:
          type: string
          minLength: 1
          description: Text to rewrite. Whitespace-only values are rejected by the server.
        instructions:
          type: string
          default: ''
          description: Optional rewrite instruction. Empty string means clean rewrite.
    RewriteResponse:
      type: object
      required: [text, latencyMs]
      properties:
        text:
          type: string
        latencyMs:
          type: integer
          minimum: 0
```

**Verify**:
```bash
cd flask
make generate-dtos
grep -c "^class RewriteRequest\b" dtos/models.py     # expect 1
grep -c "^class RewriteResponse\b" dtos/models.py    # expect 1
make check-dtos                                       # expect exit 0 (committed == regenerated)
python -m pytest tests/test_openapi_spec.py -v       # openapi must remain schema-valid
```

---

### Step 5: Add tooling verification tests

**Action**: Create `flask/tests/test_tooling.py`. This file is the first to use `condition_expectedOutcome` naming — each function name has no `test_` prefix, relying on `python_functions = ["test_*", "*_*"]` in `pyproject.toml`. The tests assert the tooling artifacts are well-formed: no subprocess calls, pure file content assertions.

**File**: `flask/tests/test_tooling.py` (new)

```python
"""Tooling artifact verification — Task 1: Build tooling.

These tests use condition_expectedOutcome naming (no test_ prefix).
Discovery relies on python_functions = ["test_*", "*_*"] in pyproject.toml.
If pytest skips this file's functions, pyproject.toml is missing or misconfigured.
"""
from __future__ import annotations

from pathlib import Path

FLASK_ROOT = Path(__file__).resolve().parent.parent


def devDeps_notInProdRequirements():
    """pytest and openapi-spec-validator must not appear in requirements.txt."""
    prod = (FLASK_ROOT / "requirements.txt").read_text()
    assert "pytest" not in prod, (
        "pytest belongs in requirements-dev.txt, not requirements.txt"
    )
    assert "openapi-spec-validator" not in prod, (
        "openapi-spec-validator belongs in requirements-dev.txt"
    )


def devRequirements_includesProdRequirements():
    """-r requirements.txt must appear in requirements-dev.txt."""
    dev = (FLASK_ROOT / "requirements-dev.txt").read_text()
    assert "-r requirements.txt" in dev, (
        "requirements-dev.txt must include -r requirements.txt so make install covers both"
    )


def devRequirements_containsDatamodelCodegen():
    """datamodel-code-generator must be declared in requirements-dev.txt."""
    dev = (FLASK_ROOT / "requirements-dev.txt").read_text()
    assert "datamodel-code-generator" in dev, (
        "datamodel-code-generator must be in requirements-dev.txt for make generate-dtos to work"
    )


def pyproject_enablesConditionExpectedOutcomeNaming():
    """pyproject.toml must configure python_functions to include '*_*'."""
    config = (FLASK_ROOT / "pyproject.toml").read_text()
    assert "python_functions" in config, (
        "pyproject.toml must declare python_functions for condition_expectedOutcome discovery"
    )
    assert '"*_*"' in config or "'*_*'" in config, (
        "python_functions must include '*_*' to discover condition_expectedOutcome names"
    )


def pyproject_setsPythonpath():
    """pyproject.toml must add '.' to pythonpath so module imports work without sys.path hacks."""
    config = (FLASK_ROOT / "pyproject.toml").read_text()
    assert "pythonpath" in config, (
        "pyproject.toml must set pythonpath = ['.'] so 'from modules.X import Y' works in tests"
    )


def makefile_declaresRequiredTargets():
    """Makefile must declare all six required targets."""
    makefile = (FLASK_ROOT / "Makefile").read_text()
    required = ["dev", "test", "lint", "generate-dtos", "check-dtos", "install"]
    for target in required:
        assert f"{target}:" in makefile, (
            f"Makefile is missing target '{target}:'"
        )
```

**Verify**: `cd flask && python -m pytest tests/test_tooling.py -v` — expect 6 tests collected and passing. If any are **not collected**, `python_functions` in `pyproject.toml` is not being read — confirm `pyproject.toml` is in `flask/` (same directory as where you run pytest from).

---

## 5. Tests

Full test file is in Step 4 above. Assertions summary:

| Function | Assertion |
|----------|-----------|
| `devDeps_notInProdRequirements` | `"pytest" not in requirements.txt` AND `"openapi-spec-validator" not in requirements.txt` |
| `devRequirements_includesProdRequirements` | `"-r requirements.txt" in requirements-dev.txt` |
| `devRequirements_containsDatamodelCodegen` | `"datamodel-code-generator" in requirements-dev.txt` |
| `pyproject_enablesConditionExpectedOutcomeNaming` | `"python_functions" in pyproject.toml` AND `"*_*"` appears |
| `pyproject_setsPythonpath` | `"pythonpath" in pyproject.toml` |
| `makefile_declaresRequiredTargets` | Each of 6 target names followed by `:` appears in Makefile |

Framework: pytest (existing repo framework). No mocking, no fixtures — pure `Path.read_text()` assertions.

---

## 6. Commit Plan

One commit per logical unit. Run `make test` after each commit to confirm zero regressions.

1. `chore(flask): split requirements into prod and dev` — `flask/requirements.txt`, `flask/requirements-dev.txt`: remove pytest + openapi-spec-validator from prod; create dev file with `-r requirements.txt` + moved + new deps.

2. `chore(flask): add pyproject.toml with pytest configuration` — `flask/pyproject.toml`: testpaths, pythonpath, addopts, python_functions.

3. `chore(flask): add Makefile with dev, test, lint, generate-dtos, check-dtos, install` — `flask/Makefile`: six targets; `check-dtos` is the CI-grade drift guard.

4. `feat(openapi): declare rewrite path + RewriteRequest/Response schemas` — `flask/openapi.yaml` + regenerated `flask/dtos/models.py`. The two files land together so `make check-dtos` exits 0 on the commit.

5. `test(flask): add tooling verification tests in condition_expectedOutcome style` — `flask/tests/test_tooling.py`: 6 assertions; first file using new naming convention.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/flask

# Install newly split deps (including datamodel-code-generator)
make install

# Full suite — must pass everything, plus the 6 new tooling tests
make test

# Confirm no DTO drift (generated == committed)
make check-dtos

# Confirm lint passes (warnings are acceptable; errors are not)
make lint
```

**Expected delta**: baseline N → N+6 passing. Zero pre-existing tests broken. `make check-dtos` exits 0.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. No step has runtime dependencies on a prior step — all four commits are additive and orthogonal.
- **Per-branch**: if verification fails after all four commits, `git reset --hard <pre-task-sha>` returns to the state before Task 1 began. The only environment side-effect is `pip install`; re-running `pip install -r requirements.txt` (the old file) restores the original installed set.

---

## 9. Deviations Allowed

- **`datamodel-codegen` flags differ from what generated the current `dtos/models.py`** → run `datamodel-codegen --help` to inspect available flags; match the header comment in `flask/dtos/models.py` (line 1: `# generated by datamodel-codegen: filename: openapi.yaml`) for clues; adjust `generate-dtos` flags until `make check-dtos` exits 0 on the unmodified committed file, then proceed.
- **`flake8` not installed after `make install`** → if `openapi-spec-validator`'s transitive deps don't include `flake8`, it is already declared in `requirements-dev.txt` by this guide; verify `pip show flake8` after `make install` before blaming the guide.
- **`python_functions = ["test_*", "*_*"]` collects unexpected functions in test files** → acceptable trade-off per architecture doc; do not remove `"*_*"` unless a specific collision is observed; if a collision occurs, note it in the commit body as a deviation and flag for Task 4.
- **Side-effect required** (push, schema change, rm -rf anything outside `flask/`) → STOP, mark `[REQUIRES APPROVAL]`, and surface to the requester.
- **Step N simplifies Step N+1** → take it; log in commit body.

---

## 10. Out of Scope

This task creates the build surface only. It does not modify any route handler, exception class, environment file, or test assertion body. The following were considered and explicitly deferred:

- **Gitignoring `flask/dtos/models.py`** — deferred because `check-dtos` diffs against the committed file; gitignoring it requires a bootstrap step and belongs with the CI workflow task (when a workflow exists to run `generate-dtos` before `check-dtos`). Trigger: first CI workflow created for spec-doc-api.
- **`python-dotenv` and `CORS_ORIGINS` env var** — Task 2 (Config hardening); adding dotenv here would mix concerns into a single PR.
- **Test function renames to `condition_expectedOutcome`** — Task 4; pyproject.toml enables the convention, but applying it retroactively to existing files is a separate commit chain with zero logic changes and its own verification pass.
- **CI workflow (`.github/workflows/backend.yml`)** — no GitHub Actions workflow exists for spec-doc-api today; the Makefile's `check-dtos` and `test` targets are designed to compose into one when the workflow is created.
- **`make ci` meta-target** — deferred until a CI workflow consumer exists; one target per current need.
- **mypy / type checking target** — separate quality epic; not blocking Phase 2 work.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- `flask/architecture.md` — design rationale for all four hardening tasks
- `flask/epic.md` — task scope and success criteria
- `flask/specs/` — spec index