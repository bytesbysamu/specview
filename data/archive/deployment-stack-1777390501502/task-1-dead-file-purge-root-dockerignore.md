# Task 1: Dead-file Purge + Root `.dockerignore`

## 1. Context

Three files tracked under `api/.github/` (`workflows/deploy.yml`, `dependabot.yml`) and one file under `web/.github/` exist only as dead artifacts: GitHub Actions reads `.github/` exclusively at the repository root, so any `.github/` nested under a subdirectory is silently ignored. Likewise, `api/.dockerignore` has no effect because `api/Dockerfile` explicitly sets its build context to the repo root (confirmed by its opening comment and by `docker build -f api/Dockerfile … .`), so Docker reads only `<repo-root>/.dockerignore`. Removing all five dead files eliminates the confusion they cause, and adding a single root-level `.dockerignore` protects the build from pulling in `web/node_modules/`, `.git/`, and test artifacts — the primary sources of build-context bloat. `api/docker-compose.coolify.yml` is also purged; it was superseded by the root-level `docker-compose.yml` added in commit `416e317`.

**Trade-offs considered:**
- **Leaving dead files in place and documenting them** — rejected because silent confusion compounds over time; a future executor will re-discover the wrong trigger branch (`main` vs `master`) and wonder whether the file is authoritative.
- **Moving `api/.github/` contents to root `.github/`** — rejected; the root `.github/workflows/deploy.yml` already exists with the correct pipeline. There is nothing to rescue — only dead content to remove.
- **Chosen: delete dead files, create one root `.dockerignore`** — fewest moving parts, zero functional change, unambiguous audit trail via `git rm`.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm working tree is clean on every target
git -C {WORKSPACE} status

# 2. Verify the four api/ targets exist (each should print its path)
ls {WORKSPACE}/api/.github/workflows/deploy.yml
ls {WORKSPACE}/api/.github/dependabot.yml
ls {WORKSPACE}/api/.dockerignore
ls {WORKSPACE}/api/docker-compose.coolify.yml

# 3. Verify web/.github/ exists (conditional — see Step 2)
ls {WORKSPACE}/web/.github/ 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"

# 4. Confirm no root .dockerignore yet
ls {WORKSPACE}/.dockerignore 2>/dev/null && echo "ALREADY EXISTS — review before overwriting" || echo "absent — safe to create"

# 5. Record baseline test count
cd {WORKSPACE}/api && make test 2>&1 | tail -5
```

**`{WORKSPACE}`** = `/Users/sam/Projects/2026/spec-doc` (never hard-code in edits).

**If working tree is dirty on any target file**: stash or commit unrelated changes before starting.

**Baseline recorded**: 624 / 624 passing (1 skipped — web-root check).

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/.dockerignore` — root-level Docker ignore file; covers both `api/` and `web/` source trees; read by Docker when build context is repo root

### To Modify
- `{WORKSPACE}/api/tests/test_cleanup.py` — **(new)** structural assertions that the four dead files are absent and the root `.dockerignore` is present and correct

### To Delete (via `git rm`)
- `{WORKSPACE}/api/.github/workflows/deploy.yml` — dead CI config; GH Actions ignores any `.github/` below repo root; also targets wrong branch (`main` vs project's `master`)
- `{WORKSPACE}/api/.github/dependabot.yml` — dead Dependabot config; same reason
- `{WORKSPACE}/api/.dockerignore` — has no effect; Docker reads root `.dockerignore` when context = repo root
- `{WORKSPACE}/api/docker-compose.coolify.yml` — superseded by root `docker-compose.yml` (commit `416e317`)
- `{WORKSPACE}/web/.github/**` — **(conditional)** check existence in pre-flight; if found, `git rm -r` the whole directory

### To Leave Alone
- `{WORKSPACE}/api/.github/` — the *directory* itself disappears automatically when both tracked files are removed via `git rm`; do not `rm -rf` manually
- `{WORKSPACE}/api/docker-compose.yml` — local-dev compose file; referenced by `test_docker.py` structural invariant (`_ROOT / "docker-compose.yml"`); do not touch
- `{WORKSPACE}/.github/workflows/deploy.yml` — the **live** root-level CI pipeline; do not touch
- `{WORKSPACE}/api/Dockerfile` — correct, used by CI and `test_docker.py`; do not touch
- `{WORKSPACE}/api/tests/test_docker.py` — passing structural tests; do not touch

---

## 4. Implementation Steps

### Step 1: Delete dead `api/.github/` files, `api/.dockerignore`, and `api/docker-compose.coolify.yml`

**Action**: Use `git rm` so the deletions are staged and the directory is removed atomically when the last tracked file under it is gone. Verify each removal.

**File**: `{WORKSPACE}/api/.github/workflows/deploy.yml`, `{WORKSPACE}/api/.github/dependabot.yml`, `{WORKSPACE}/api/.dockerignore`, `{WORKSPACE}/api/docker-compose.coolify.yml`

**Pattern**:
```bash
git -C {WORKSPACE} rm api/.github/workflows/deploy.yml \
                      api/.github/dependabot.yml \
                      api/.dockerignore \
                      api/docker-compose.coolify.yml
```

**Verify**:
```bash
# All four paths must be absent
ls {WORKSPACE}/api/.github/ 2>/dev/null && echo "FAIL — directory still exists" || echo "OK"
ls {WORKSPACE}/api/.dockerignore 2>/dev/null && echo "FAIL" || echo "OK"
ls {WORKSPACE}/api/docker-compose.coolify.yml 2>/dev/null && echo "FAIL" || echo "OK"
git -C {WORKSPACE} status   # expect four 'D' (deleted) entries, nothing else
```

---

### Step 2: Delete `web/.github/` if it exists (conditional)

**Action**: Check whether `web/.github/` is tracked. If yes, `git rm -r` the entire directory. If no, skip this step and note in the commit body.

**File**: `{WORKSPACE}/web/.github/` (conditional — may not exist)

**Pattern**:
```bash
# Check
git -C {WORKSPACE} ls-files web/.github/

# If output is non-empty, remove:
git -C {WORKSPACE} rm -r web/.github/

# If output is empty, skip — no action needed.
```

**Verify**:
```bash
# Either the directory is gone, or it was never there
ls {WORKSPACE}/web/.github/ 2>/dev/null && echo "FAIL — still present" || echo "OK"
```

---

### Step 3: Create root `.dockerignore`

**Action**: Create `{WORKSPACE}/.dockerignore`. The content below is derived directly from `api/.dockerignore` (which captured the correct exclude rules for the Python side) expanded to also cover the `web/` source tree (Node, Angular) and repo-level metadata. Patterns are anchored to the build context root (repo root) as Docker requires.

**File**: `{WORKSPACE}/.dockerignore` (new)

**Pattern**:
```
# ─── Secrets ────────────────────────────────────────────────────────────────
.env
api/.env

# ─── Git / IDE / Claude Code ─────────────────────────────────────────────────
.git/
.gitignore
.idea/
.vscode/
.claude/

# ─── CI and GitHub metadata ──────────────────────────────────────────────────
.github/
api/.github/

# ─── Documentation & project context (not needed at runtime) ─────────────────
CLAUDE.md
api/CLAUDE.md
api/docs/
projects/
builder.md
principles.md
codebase.md
references.md

# ─── Python build artifacts ──────────────────────────────────────────────────
**/__pycache__/
**/*.py[cod]
**/*.pyo
api/.venv/
api/venv/

# ─── Test & coverage artifacts ───────────────────────────────────────────────
api/tests/
api/.pytest_cache/
api/.coverage
api/htmlcov/

# ─── Node / Angular ──────────────────────────────────────────────────────────
web/node_modules/
web/.angular/
web/dist/

# ─── Docker host-side files ───────────────────────────────────────────────────
docker-compose*.yml
api/docker-compose*.yml
api/.dockerignore
```

**Verify**:
```bash
ls -la {WORKSPACE}/.dockerignore          # file must exist
wc -l {WORKSPACE}/.dockerignore           # expect ~32 lines
grep "web/node_modules" {WORKSPACE}/.dockerignore   # must print the line
grep "\.git/" {WORKSPACE}/.dockerignore             # must print the line
```

---

### Step 4: Add structural tests

**Action**: Create `{WORKSPACE}/api/tests/test_cleanup.py` with six pytest assertions verifying the purge is permanent and the root `.dockerignore` is correct. Follows the same `Path(__file__).parent.parent` convention used in `api/tests/test_docker.py`.

**File**: `{WORKSPACE}/api/tests/test_cleanup.py` (new)

**Pattern** — see Tests section below.

**Verify**:
```bash
cd {WORKSPACE}/api && python -m pytest tests/test_cleanup.py -v
# Expect: 6 passed
```

---

## 5. Tests

Complete assertion bodies. Framework: pytest, matching `api/tests/test_docker.py` conventions exactly.

```python
# api/tests/test_cleanup.py
"""Structural tests — Task 1: dead-file purge + root .dockerignore.

Keeps the repository honest: if a future commit accidentally re-adds a dead
file, these tests fail in CI before the confusion spreads.
"""
from pathlib import Path

_API_ROOT = Path(__file__).parent.parent   # api/
_REPO_ROOT = _API_ROOT.parent              # spec-doc/ (repo root)


# ── Dead-file absence ────────────────────────────────────────────────────────

def test_api_github_directory_absent():
    """api/.github/ must not exist — GH Actions ignores .github/ below repo root."""
    path = _API_ROOT / ".github"
    assert not path.exists(), (
        f"{path} still exists — GitHub Actions only reads <repo-root>/.github/; "
        "api/.github/ is silently ignored and should be removed to avoid confusion"
    )


def test_api_dockerignore_absent():
    """api/.dockerignore must not exist — has no effect when build context is repo root."""
    path = _API_ROOT / ".dockerignore"
    assert not path.exists(), (
        f"{path} still exists — Docker build context is repo root; "
        "only <repo-root>/.dockerignore is honoured; api/.dockerignore is dead"
    )


def test_api_docker_compose_coolify_absent():
    """api/docker-compose.coolify.yml must not exist — superseded by root docker-compose.yml."""
    path = _API_ROOT / "docker-compose.coolify.yml"
    assert not path.exists(), (
        f"{path} still exists — superseded by root docker-compose.yml (commit 416e317); "
        "remove it to avoid ambiguity about which compose file Coolify uses"
    )


# ── Root .dockerignore presence and content ──────────────────────────────────

def test_root_dockerignore_exists():
    """Root .dockerignore must exist when Docker build context is repo root."""
    path = _REPO_ROOT / ".dockerignore"
    assert path.is_file(), (
        f"{path} not found — Docker build context is repo root (api/Dockerfile line 1); "
        "without a root .dockerignore the full build context includes node_modules, .git, etc."
    )


def test_root_dockerignore_excludes_node_modules():
    """Root .dockerignore must exclude web/node_modules/ (largest build-context bloat)."""
    text = (_REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "web/node_modules" in text, (
        "web/node_modules/ must appear in root .dockerignore — "
        "it can be several hundred MB and must never enter the Docker build context"
    )


def test_root_dockerignore_excludes_git():
    """Root .dockerignore must exclude .git/ to prevent repo history from entering context."""
    text = (_REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".git/" in text, (
        ".git/ must appear in root .dockerignore — "
        "git history can be large and contains no runtime-relevant content"
    )
```

---

## 6. Commit Plan

**Executor instruction**: run each `git commit` immediately after the corresponding step completes — not at the end of the task.

**Commit 1** — after Steps 1 and 2 — `chore(purge): remove dead api/.github, api/.dockerignore, api/docker-compose.coolify.yml`

Files staged: `api/.github/workflows/deploy.yml` (D), `api/.github/dependabot.yml` (D), `api/.dockerignore` (D), `api/docker-compose.coolify.yml` (D), and `web/.github/**` (D) if found.

Message body:
```
api/.github/ is never read by GitHub Actions (root .github/ is the only
location Actions scans). The embedded workflow also targeted 'main' while
the repo's default branch is 'master' — confirming it was never active.

api/.dockerignore has no effect because api/Dockerfile declares build
context = repo root; Docker reads only <repo-root>/.dockerignore.

api/docker-compose.coolify.yml is superseded by the root
docker-compose.yml added in 416e317.
```

**Commit 2** — after Step 3 — `chore(docker): add root .dockerignore for repo-root build context`

Files staged: `.dockerignore` (A).

Message body:
```
api/Dockerfile uses repo root as build context. Without a root
.dockerignore, Docker sends web/node_modules/, .git/, api/tests/, and
other non-runtime paths to the daemon on every build.

Excludes: secrets, .git/, IDE config, ci/, docs, Python artifacts,
test/coverage dirs, web/node_modules/, web/.angular/, web/dist/,
and host-side docker-compose files.
```

**Commit 3** — after Step 4, tests pass — `test(cleanup): structural assertions for Task 1 dead-file purge`

Files staged: `api/tests/test_cleanup.py` (A).

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api && make test
```

**Expected delta**: 624 → 630 passing (6 new tests in `test_cleanup.py`). Zero pre-existing tests broken.

Spot-check that the three most sensitive existing tests still pass:

```bash
cd {WORKSPACE}/api && python -m pytest tests/test_docker.py -v
# Expect: all 13 test_docker.py tests pass (api/docker-compose.yml and api/Dockerfile untouched)
```

---

## 8. Rollback

- **Per-step (preferred)**: each commit is independently revertible with `git revert <sha>`. Order: revert commit 3, then 2, then 1.
- **Per-branch (catastrophic)**: if the branch is in a broken state and revert is impractical:
  ```bash
  git reset --hard <pre-task-sha>    # [REQUIRES APPROVAL] — discards all uncommitted changes
  ```
  Retrieve `<pre-task-sha>` from pre-flight `git status` / `git log` output.
- **Restoring a deleted file**: `git checkout <pre-task-sha> -- api/.dockerignore` (or whichever file). Do this before committing if a step is wrong.

---

## 9. Deviations Allowed

- **`web/.github/` does not exist** → skip Step 2; note `web/.github/ not found — skipped` in commit 1 body under `Deviations:`.
- **`web/.github/` has files not mentioned in the epic** → delete them anyway with `git rm -r web/.github/`; include file list in commit body.
- **Root `.dockerignore` already exists** (pre-flight warning fires) → read its contents first; if it already covers the key patterns (`web/node_modules`, `.git/`), verify it matches the intent here, then skip Step 3 or merge the two files; log as a deviation.
- **Test framework mismatch** → match whatever `api/tests/test_docker.py` uses (currently bare pytest functions, no class wrapper). Translate `test_cleanup.py` to match; note in commit 3 body.
- **Step N simplification is obvious** → take it; log one line in commit body under `Deviations:`.
- **Any side effect required** (push, schema change) → STOP, mark `[REQUIRES APPROVAL]`, do not proceed.

---

## 10. Out of Scope

This task is narrowly scoped to file deletion and one new `.dockerignore`. It deliberately does not touch any Python module, route, test fixture, or CI pipeline logic. The following items are explicitly deferred and must not be absorbed here:

- **Fixing the root `.github/workflows/deploy.yml`** — the root pipeline exists and runs; any improvements (matrix tests, caching, branch protection rules) are separate operational concerns.
- **Adding a root-level `dependabot.yml`** — the deleted `api/dependabot.yml` tracked `pip` dependencies; a correct root-level version would need to also cover `web/` npm dependencies. That is a deliberate configuration decision, not a purge task.
- **`api/docker-compose.yml` review** — that file is kept intentionally (it serves local dev and anchors `test_docker.py` structural invariants). Any updates to its port mapping, volume paths, or health-check belong to an operational task.
- **`web/node_modules/` cleanup on disk** — `.dockerignore` prevents it from entering build context; `git` already ignores it via `web/node_modules/` in root `.gitignore`. Pruning it from disk is a developer machine concern, not a task action.
- **Multi-stage Dockerfile optimisation** — the Dockerfile is correct as-is; layer cache analysis and build-time benchmarking are separate from this purge.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)