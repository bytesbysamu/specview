# Task 1: Health Route + Gunicorn Prerequisite

**Purpose**: Confirm the `/health` liveness route is wired in the Flask app factory, and add `gunicorn` to `requirements.txt` so the Dockerfile can install it at build time. Both are prerequisites for Task 2 (Dockerfile).

**Effort**: 0.25 days

**Dependencies**: None

**Parallel With**: —

**Blocks**: Task 2 (Dockerfile), Task 3 (docker-compose files), Task 5 (CI smoke job)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 2's Dockerfile runs `pip install -r requirements.txt` and then starts the process with `gunicorn`. If `gunicorn` is absent from `requirements.txt` at build time, the image build fails at the `CMD` layer with a `ModuleNotFoundError` before any container test can run. Separately, the CI smoke job and Docker healthcheck both poll `GET /health` — without that route, the smoke test loop times out and the entire pipeline stalls. A pre-flight read of `create_app.py` shows `GET /health` returning `{"status": "ok"}` is already registered (lines 45–47) and is covered by ten tests in `tests/test_health.py`. The only missing piece is `gunicorn` in `requirements.txt`. This task does that one-line addition and adds a structural test so the gap can never silently reappear.

**Trade-offs considered:**
- **Add gunicorn to `requirements-dev.txt` only** — rejected because the Dockerfile installs only `requirements.txt`; putting it in dev deps produces a working local environment but a broken production image.
- **Pin `gunicorn` to an exact version** — rejected; the project pins floors (`>=`) for framework deps and leaves utility packages unpinned; gunicorn follows the same pattern here.
- **Add gunicorn to `requirements.txt`, enforce presence with a structural test** — preferred; the structural test catches any future accidental deletion before CI builds an image.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From the api directory
cd {WORKSPACE}/spec-doc/api

git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- requirements.txt create_app.py tests/test_structural.py

make test                                     # Record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Expected pre-flight outcome**: `requirements.txt` does not contain `gunicorn`. `create_app.py` lines 45–47 already contain the `GET /health` handler. `tests/test_health.py` contains 10 passing tests. Record the total passing count from `make test` — call it **N**.

**Confirm health route is already present** (do not modify if this passes):

```bash
grep -n "health" {WORKSPACE}/spec-doc/api/create_app.py
# Expected output: line 45  @app.get('/health')
#                  line 46  def health():
#                  line 47      return jsonify({'status': 'ok'})
```

**Confirm gunicorn is absent** (this is the gap to fix):

```bash
grep "gunicorn" {WORKSPACE}/spec-doc/api/requirements.txt
# Expected: no output (exit code 1)
```

---

## 3. Files

### To Create (new)
_None._

### To Modify (cite CODEBASE CONTEXT)
- `spec-doc/api/requirements.txt` — current state: 6 prod deps, no `gunicorn` → target state: 7 prod deps, `gunicorn` added on its own line
- `spec-doc/api/tests/test_structural.py` — current state: one structural test (`noPromptStrings_inRouteHandlers`) → target state: two structural tests, second one asserting `gunicorn` is in `requirements.txt`

### To Leave Alone
- `spec-doc/api/create_app.py` — `GET /health` is already registered at lines 45–47; do not modify
- `spec-doc/api/tests/test_health.py` — all 10 health tests already pass; do not modify
- `spec-doc/api/requirements-dev.txt` — dev deps are not consumed by the Dockerfile; no change needed
- `spec-doc/api/dtos/models.py` — auto-generated; never hand-edit

---

## 4. Implementation Steps

### Step 1: Verify the `/health` route (read-only confirmation)

**Action**: Read `create_app.py` lines 44–48 and confirm the route is present. If the route is missing (reality diverged from this guide), add it as shown in the Pattern block. If it is already present, do nothing and proceed to Step 2.

**File**: `spec-doc/api/create_app.py` — existing file, lines 45–47

**Pattern (expected existing state — only add this if lines 45–47 are absent)**:
```python
@app.get('/health')
def health():
    return jsonify({'status': 'ok'})
```

The handler must sit inside `create_app()`, after `CORS(app, ...)` is applied and before the error handlers, so CORS headers are present on `/health` responses. The existing position (after blueprint registration, before `serve_spec`) is correct.

**Verify**:
```bash
python -c "
from create_app import create_app
app = create_app()
client = app.test_client()
r = client.get('/health')
assert r.status_code == 200 and r.get_json() == {'status': 'ok'}, r.get_json()
print('OK: /health returns 200 + {status: ok}')
"
```
Expected: `OK: /health returns 200 + {status: ok}`

---

### Step 2: Add `gunicorn` to `requirements.txt`

**Action**: Append `gunicorn` on a new line at the end of `requirements.txt`. No version floor is added (consistent with `anthropic` and `pyyaml` which are also unpinned in this file).

**File**: `spec-doc/api/requirements.txt`

**Pattern (target state of the full file)**:
```text
flask>=3.0.0
flask-cors>=4.0.0
anthropic
pydantic>=2.0.0
pyyaml
python-dotenv>=1.0.0
gunicorn
```

**Verify**:
```bash
grep "gunicorn" {WORKSPACE}/spec-doc/api/requirements.txt
# Expected: gunicorn

pip install -r {WORKSPACE}/spec-doc/api/requirements.txt --dry-run 2>&1 | grep gunicorn
# Expected: a line containing "gunicorn" (would install or already satisfied)
```

> **Commit here** — see Commit Plan item 1 before continuing.

---

### Step 3: Add structural test asserting `gunicorn` is in `requirements.txt`

**Action**: Append a new test function to `tests/test_structural.py`, following the exact style of the existing `noPromptStrings_inRouteHandlers` function — `Path`-based, one assertion, one failure message naming the rule and fix.

**File**: `spec-doc/api/tests/test_structural.py` — append after line 31 (end of existing function)

**Pattern**:
```python
def gunicorn_inProdRequirements():
    """requirements.txt must list gunicorn so the Dockerfile installs it.

    Rule: the Dockerfile runs `pip install -r requirements.txt`; gunicorn must
          be a prod dependency, not a dev-only one.
    Fix:  Add 'gunicorn' to requirements.txt.
    """
    req = (_REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "gunicorn" in req, (
        "gunicorn not found in requirements.txt.\n"
        "The Dockerfile installs only requirements.txt; gunicorn must be a prod dep.\n"
        "Fix: add 'gunicorn' to requirements.txt."
    )
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api && python -m pytest tests/test_structural.py -v
# Expected: 2 passed (noPromptStrings_inRouteHandlers + gunicorn_inProdRequirements)
```

> **Commit here** — see Commit Plan item 2 before continuing.

---

## 5. Tests

Framework: pytest 8.x, plain `assert` statements, function-based naming `<subject>_<condition>` (collected via `python_functions = ["*_*"]` in `pyproject.toml`). No class wrappers required for structural tests.

The test below is the complete body to append to `spec-doc/api/tests/test_structural.py`. It uses `_REPO_ROOT` already defined at the top of that file (line 9: `_REPO_ROOT = Path(__file__).parent.parent`).

```python
def gunicorn_inProdRequirements():
    """requirements.txt must list gunicorn so the Dockerfile installs it.

    Rule: the Dockerfile runs `pip install -r requirements.txt`; gunicorn must
          be a prod dependency, not a dev-only one.
    Fix:  Add 'gunicorn' to requirements.txt.
    """
    req = (_REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "gunicorn" in req, (
        "gunicorn not found in requirements.txt.\n"
        "The Dockerfile installs only requirements.txt; gunicorn must be a prod dep.\n"
        "Fix: add 'gunicorn' to requirements.txt."
    )
```

**Health route tests**: `tests/test_health.py` already contains the full assertion suite (10 tests: 200 status, JSON body equality, content-type, CORS allow for known origin, CORS block for unknown origin, blueprint registration checks). No additions required.

**Negative test** (executor may choose to run this as a sanity check but does not need to commit it):
```bash
# Temporarily remove gunicorn from requirements.txt, run the structural test, confirm failure
cd {WORKSPACE}/spec-doc/api
python -m pytest tests/test_structural.py::gunicorn_inProdRequirements -v
# Then restore requirements.txt before committing
```

---

## 6. Commit Plan

**Executor instruction**: run each `git commit` immediately after completing the corresponding step. Do not batch commits at the end.

1. `chore(deps): add gunicorn to requirements.txt` — after Step 2 — files: `requirements.txt`
   - Body: `Gunicorn is a prod dependency; the Dockerfile installs requirements.txt at build time.`

2. `test(structural): assert gunicorn present in requirements.txt` — after Step 3 — files: `tests/test_structural.py`
   - Body: `Structural test catches any accidental removal of gunicorn from prod deps before a broken image is built.`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

**Commit commands**:
```bash
# After Step 2
cd {WORKSPACE}/spec-doc/api
git add requirements.txt
git commit -m "$(cat <<'EOF'
chore(deps): add gunicorn to requirements.txt

Gunicorn is a prod dependency; the Dockerfile installs requirements.txt at build time.
EOF
)"

# After Step 3
git add tests/test_structural.py
git commit -m "$(cat <<'EOF'
test(structural): assert gunicorn present in requirements.txt

Structural test catches any accidental removal of gunicorn from prod deps before a broken image is built.
EOF
)"
```

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api && make test
```

**Expected delta**: **N → N+1** passing. The one new test is `gunicorn_inProdRequirements` in `tests/test_structural.py`. Zero pre-existing tests broken. `tests/test_health.py` (10 tests) must still pass unchanged.

**Spot-check the two changed files**:
```bash
grep "gunicorn" {WORKSPACE}/spec-doc/api/requirements.txt          # → gunicorn
python -m pytest tests/test_structural.py -v                        # → 2 passed
python -m pytest tests/test_health.py -v                            # → 10 passed
```

---

## 8. Rollback

**Per-step**: each commit is independently revertible.
```bash
git revert <sha>   # reverts only the named commit; no other files touched
```

**Per-branch**: if verification fails catastrophically:
```bash
git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — discards both commits
```

Identify `<pre-task-sha>` from `git log --oneline` before starting Step 2.

**No schema migrations, no published artifacts, no pushed branches** are part of this task. All rollback is local.

---

## 9. Deviations Allowed

- **`/health` route is missing from `create_app.py`** → add the three-line handler exactly as shown in Step 1's Pattern block; add the file to the Step 2 commit; note the deviation in the commit body.
- **`gunicorn` is already present in `requirements.txt`** → skip Step 2 entirely; proceed to Step 3; note it in the Step 3 commit body.
- **`_REPO_ROOT` is not defined at the top of `test_structural.py`** → verify by reading the file before editing; if missing, add `_REPO_ROOT = Path(__file__).parent.parent` after the existing imports.
- **Test framework mismatch** (e.g., function naming convention differs) → match the repo's convention as observed; translate the test name; note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask before proceeding.

---

## 10. Out of Scope

This task establishes the two prerequisites that unblock Task 2. It intentionally stops there. The Gunicorn configuration (worker class, thread count, 900-second timeout, `--preload` flag) is an image-level concern expressed in the Dockerfile CMD — not a `requirements.txt` concern. Writing that CMD line is Task 2's job, not this one.

- **Dockerfile** — depends on `gunicorn` being installable; authored in Task 2
- **`docker-compose.yml` and `docker-compose.coolify.yml`** — depend on the Dockerfile existing; authored in Task 3
- **Gunicorn worker/timeout configuration** — expressed in Dockerfile CMD; belongs in Task 2 so the full configuration context (worker class, thread count, timeout, preload) is co-located in one file
- **`make docker-*` Makefile targets** — wrap compose commands; belong in Task 3 alongside the compose files they invoke
- **`.env.example` additions** — no new env vars are introduced in this task; `.env.example` authoring belongs in the task that introduces variables requiring documentation
- **`spec-doc-live` worktree removal** — deferred explicitly by architecture; not a prerequisite for containerization

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, especially health route and gunicorn timeout sections
- [Epic](./epic.md) – Full task scope
- [Timeline](./timeline.md) – Update status to ✅ after verification passes