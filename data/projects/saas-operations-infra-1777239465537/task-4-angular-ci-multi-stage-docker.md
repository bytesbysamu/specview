# Task 4: Angular CI + Multi-stage Docker — Implementation Guide

## 1. Context

This task gates every deploy on a verified Angular build and a smoke-tested production image. Currently the pipeline proves the Flask backend works but ships the frontend unverified — a broken `ng build` silently produces a container with a missing SPA. Three changes close that gap: a `build-frontend` CI job that fails fast on an `ng build` error; a reworked `docker-build` CI job that assembles a multi-stage image from the pre-built Angular artifact and smoke-tests both the Flask API and the Angular root before the deploy job fires; and a Flask catch-all route in `create_app.py` that activates only when the `web/` directory is present, serving Angular's `index.html` for all non-API paths in the production container. Together these make the deployed artifact identical to what CI tested.

**Trade-offs considered:**
- **Flask-only image + Angular served by a separate nginx sidecar** — rejected: two containers to coordinate on a Coolify single-host deploy; Traefik already handles SSL and routing, making a second container pure overhead at this team size.
- **Multi-stage Dockerfile that always re-runs `ng build` inside Docker** — rejected: `ng build` would run twice in every CI pipeline (once in `build-frontend`, once inside `docker build`), wasting minutes and making the fail-fast gate redundant.
- **Multi-stage Dockerfile with CI artifact injection (chosen)** — `build-frontend` uploads the dist as a workflow artifact; `docker-build` downloads it into `web/dist/` before calling `docker build`; the Dockerfile build stage detects the pre-built dist and skips `ng build`. Local `docker build` (no pre-built dist) runs `ng build` in the build stage as usual.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# From {WORKSPACE}/spec-doc/
git status                                          # flag any unrelated M/?? entries
git diff HEAD -- .github/workflows/deploy.yml       # must be clean
git diff HEAD -- api/create_app.py                  # must be clean

# Verify angular.json output path — executor MUST do this before writing Dockerfile COPY paths
cat web/angular.json | grep -A3 '"outputPath"'
# Expected value: dist/spec-doc/browser  (or dist/spec-doc — record the exact value)

# Verify whether gunicorn is already in requirements
grep -i gunicorn api/requirements.txt || echo "MISSING — add it in Step 3"

# Verify package-lock.json exists (needed for npm ci in CI)
ls web/package-lock.json || echo "MISSING — adjust npm ci step in Step 5"

# Record baseline test count
cd api && make test 2>&1 | tail -5
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: 624/624 passing (1 skipped — web-root check).

---

## 3. Files

### To Create (new)
- `.dockerignore` — excludes `web/node_modules/`, `__pycache__`, `.git`; deliberately includes `web/dist/` so CI-downloaded artifact reaches the Docker build context
- `Dockerfile` — multi-stage: Node 20 Alpine build stage + Python 3.11-slim final stage; ported from `humanize-me` (references.md) + Trendfy gunicorn config
- `api/tests/test_catch_all.py` — pytest tests for the Angular SPA catch-all route in `create_app.py`

### To Modify (cite CODEBASE CONTEXT)
- `.github/workflows/deploy.yml` (root) — add `build-frontend` job (parallel with `test-backend`); update existing `docker-build` job to depend on both + download artifact + smoke-test multi-stage image
- `api/create_app.py` — add catch-all route at the end of `create_app()`, after all blueprints are registered; ported from `humanize-me` catch-all pattern (references.md); inactive in dev (no `web/` dir)
- `api/requirements.txt` — add `gunicorn` if absent (Step 3 pre-flight check)

### To Leave Alone
- `api/openapi.yaml` — no contract changes; catch-all is not an API endpoint
- `api/dtos/models.py` — generated; no new DTOs needed
- `api/modules/` — all feature modules unchanged
- `.github/workflows/deploy.yml` jobs `test-backend` and `deploy` — per epic constraint: "No changes to the existing test-backend or deploy jobs"

---

## 4. Implementation Steps

### Step 1: Create `.dockerignore`

**Action**: Create `.dockerignore` at the repo root. Exclude build artifacts and tooling that inflate the Docker build context. Do **not** exclude `web/dist/` — the CI artifact download populates this path and the Dockerfile build stage must see it.

**File**: `.dockerignore` (new, at `{WORKSPACE}/spec-doc/.dockerignore`)

**Pattern**:
```
# Python
**/__pycache__/
**/*.pyc
**/*.pyo
.pytest_cache/
.mypy_cache/
*.egg-info/

# Node — exclude heavy dep tree; keep dist/ (CI artifact injection)
web/node_modules/
web/.angular/cache/

# Git and CI
.git/
.gitignore
.github/

# Environment / secrets
.env
*.env

# Editor
.idea/
.vscode/
*.swp
*.swo

# Spec-doc runtime data (not needed in image)
projects/
```

**Verify**: `docker build --no-cache --dry-run . 2>&1 | grep "Sending build context"` — context size should be under 50 MB before any dist is present. (If `--dry-run` is unsupported on the local Docker version, run `docker build -t spec-doc:dryrun . 2>&1 | head -3` and confirm the first line reports a small context.)

---

### Step 2: Create multi-stage `Dockerfile`

**Action**: Create `Dockerfile` at the repo root. Ported from the humanize-me multi-stage pattern (references.md, "Multi-stage CI pipeline" section) and the Trendfy gunicorn config (references.md, "gunicorn config" section). The build stage checks for a pre-built dist before running `ng build` — this is the artifact-injection seam used by CI.

Before writing, verify the `ng build` output path from the pre-flight `cat web/angular.json` output. The architecture states `dist/spec-doc/browser` — if your `angular.json` differs, substitute throughout.

**File**: `Dockerfile` (new, at `{WORKSPACE}/spec-doc/Dockerfile`)

**Pattern**:
```dockerfile
# ── Stage 1: Angular build ──────────────────────────────────────────────────
# CI injects a pre-built dist into web/dist/ before docker build runs,
# so the RUN guard skips npm ci + ng build when the artifact is already present.
# Local `docker build` (no pre-built dist) always runs the full build here.
FROM node:20-alpine AS frontend-builder
WORKDIR /workspace

# Separate COPY for package files — preserves Docker layer cache when only
# source files change and package.json/lock are unchanged.
COPY web/package.json web/package-lock.json ./
COPY web/ ./

# Skip if dist was provided by the CI artifact; build otherwise.
RUN test -d dist/spec-doc/browser \
    || (npm ci --prefer-offline \
        && npx ng build --configuration production)

# ── Stage 2: Production image ────────────────────────────────────────────────
FROM python:3.11-slim AS final
WORKDIR /app

# Install Python dependencies before copying source for layer cache efficiency.
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask source.
COPY api/ ./

# Copy Angular dist alongside create_app.py — Flask catch-all serves from ./web.
COPY --from=frontend-builder /workspace/dist/spec-doc/browser ./web

EXPOSE 3101

# Trendfy gunicorn config (references.md): gthread worker allows daemon threads
# (task_gen, bootstrap) to coexist with gunicorn workers; timeout 3600 for AI calls.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:3101", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "3600", \
     "--worker-class", "gthread", \
     "create_app:create_app()"]
```

**Verify**: Local build succeeds (requires `web/node_modules/` to be installed or a pre-built dist):
```bash
# From {WORKSPACE}/spec-doc/
docker build -t spec-doc:local . 2>&1 | tail -10
# Expect: "Successfully built <sha>" — no error
```
If the local build lacks node_modules, pre-build first: `cd web && npm ci && cd ..` then re-run.

---

### Step 3: Add `gunicorn` to `api/requirements.txt`

**Action**: If the pre-flight grep confirmed gunicorn is absent, add it. If already present, skip this step and do not create a commit for it.

**File**: `api/requirements.txt` (existing)

**Pattern**:
```
# Add at the end of the file, after existing dependencies
gunicorn==21.2.0
```

Use `==21.2.0` (current stable). If a different version is already pinned elsewhere in the project, match that convention.

**Verify**:
```bash
grep gunicorn api/requirements.txt
# Expect: gunicorn==21.2.0  (or similar)
pip install -r api/requirements.txt --dry-run 2>&1 | grep gunicorn
# Expect: Requirement already satisfied or Would install gunicorn-...
```

---

### Step 4: Add Angular catch-all route to `api/create_app.py`

**Action**: Add the Flask catch-all route at the **end** of the `create_app()` function body, after all blueprint registrations. Ported verbatim from the humanize-me catch-all pattern (references.md, "Flask catch-all route for Angular SPA"). The route is conditionally registered only when `web/` exists — dev mode is unaffected. The `FLASK_WEB_DIR` override enables unit testing without touching the filesystem next to the source tree.

**File**: `api/create_app.py` (existing — read before editing)

```python
# Add these imports at the top of create_app.py if not already present:
import os
from flask import send_from_directory
```

```python
# At the END of create_app() — after all blueprint .register_blueprint() calls,
# before the `return app` line:

    # Angular SPA catch-all — inactive in dev (no web/ dir present).
    # FLASK_WEB_DIR overrides the default path for tests.
    # Ported from humanize-me catch-all pattern (references.md).
    _web_dir = os.environ.get(
        "FLASK_WEB_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"),
    )
    if os.path.isdir(_web_dir):

        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_angular(path):
            if path:
                target = os.path.join(_web_dir, path)
                if os.path.isfile(target):
                    return send_from_directory(_web_dir, path)
            return send_from_directory(_web_dir, "index.html")

    return app
```

**Verify**:
```bash
cd api
# Confirm catch-all is NOT active in dev (no web/ dir):
python -c "
from create_app import create_app
app = create_app()
rules = [str(r) for r in app.url_map.iter_rules()]
assert not any('serve_angular' in r for r in rules), 'catch-all must be absent without web/'
print('OK — catch-all absent in dev mode')
"

# Confirm catch-all IS active when web/ exists:
mkdir -p /tmp/spec-doc-web-stub
echo '<!DOCTYPE html><html><body>ok</body></html>' > /tmp/spec-doc-web-stub/index.html
FLASK_WEB_DIR=/tmp/spec-doc-web-stub python -c "
from create_app import create_app
app = create_app()
rules = [str(r) for r in app.url_map.iter_rules()]
assert any('serve_angular' in r for r in rules), 'catch-all must be present with web/'
print('OK — catch-all active with web/')
"
rm -rf /tmp/spec-doc-web-stub
```

---

### Step 5: Add `build-frontend` CI job to `.github/workflows/deploy.yml`

**Action**: Add a `build-frontend` job that runs in parallel with the existing `test-backend` job. It checks out the repo, builds the Angular app, and uploads the `dist/` directory as a workflow artifact that the `docker-build` job will consume. If `ng build` exits non-zero, the job fails and downstream jobs do not run.

**File**: `.github/workflows/deploy.yml` (existing — read the full file before editing)

Locate the `jobs:` key. Insert `build-frontend` as a sibling to `test-backend`:

```yaml
  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: web/package-lock.json

      - name: Install Angular dependencies
        run: npm ci
        working-directory: web

      - name: Build Angular (production)
        run: npx ng build --configuration production
        working-directory: web

      - name: Upload dist artifact
        uses: actions/upload-artifact@v4
        with:
          name: angular-dist
          # Adjust path if angular.json outputPath differs from dist/spec-doc/browser
          path: web/dist/spec-doc/browser
          retention-days: 1
```

**Verify**: Push to a branch and confirm in the GitHub Actions UI that `build-frontend` appears as a parallel sibling to `test-backend` and produces an artifact named `angular-dist`. *(Do not merge to master yet — deploy job is gated.)*

---

### Step 6: Update `docker-build` CI job in `.github/workflows/deploy.yml`

**Action**: Replace the body of the existing `docker-build` job. It now depends on both `test-backend` and `build-frontend`, downloads the Angular artifact into `web/dist/spec-doc/browser` (so the Dockerfile build stage skips `ng build`), builds the multi-stage image, starts a container, and asserts both surface areas respond before allowing the `deploy` job to proceed.

**File**: `.github/workflows/deploy.yml` (same file as Step 5 — edit in the same file read)

Replace the existing `docker-build` job definition with:

```yaml
  docker-build:
    needs: [test-backend, build-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download Angular dist artifact
        uses: actions/download-artifact@v4
        with:
          name: angular-dist
          # Must match the path the Dockerfile COPY --from=frontend-builder references
          path: web/dist/spec-doc/browser

      - name: Build multi-stage Docker image
        run: docker build -t spec-doc:ci .

      - name: Start container
        run: |
          docker run -d --name spec-doc-ci \
            -p 3101:3101 \
            -e SPEC_DOC_DIR=/tmp/projects \
            -e CHAIN_PROVIDER=anthropic_sdk \
            spec-doc:ci

      - name: Wait for gunicorn to accept connections
        run: |
          for i in {1..15}; do
            curl -s http://localhost:3101/api/health/neon && break
            echo "attempt $i — waiting..."; sleep 3
          done

      - name: Smoke-test health endpoint (accept ok or degraded — no API key in CI)
        run: |
          HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
                 http://localhost:3101/api/health/anthropic)
          [[ "$HTTP" =~ ^(200|503)$ ]] \
            || (echo "Unexpected HTTP $HTTP from /api/health/anthropic" && exit 1)
          echo "health/anthropic → $HTTP (pass)"

      - name: Smoke-test Angular root (must serve index.html)
        run: |
          BODY=$(curl -fs http://localhost:3101/)
          echo "$BODY" | grep -qi "<!DOCTYPE html>" \
            || (echo "Root did not serve Angular HTML" && exit 1)
          echo "/ → served Angular index.html (pass)"

      - name: Stop and remove container
        if: always()
        run: docker rm -f spec-doc-ci || true
```

**The `deploy` job's `needs: [docker-build]` line is unchanged** — it already gates on `docker-build`, which now gates on both `test-backend` and `build-frontend`. No edits to the `deploy` job.

**Verify**: Inspect the updated file:
```bash
grep -A3 "needs:" .github/workflows/deploy.yml
# Expect docker-build to show: needs: [test-backend, build-frontend]
# Expect deploy to show: needs: [docker-build]  (unchanged)
```

---

## 5. Tests

Framework: `pytest` (matches existing `api/tests/` suite). Run from `api/`.

**File**: `api/tests/test_catch_all.py` (new)

```python
"""
Tests for the Angular SPA catch-all route added to create_app.py.

The catch-all is conditional: it registers only when the web/ directory exists.
FLASK_WEB_DIR env var overrides the default path so tests can inject a stub
without touching the source tree.
"""
import os
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def web_root(tmp_path):
    """Minimal Angular dist stub: index.html + one static asset."""
    (tmp_path / "index.html").write_bytes(
        b"<!DOCTYPE html><html><body>spec-doc</body></html>"
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes
    return tmp_path


@pytest.fixture()
def client_with_web(web_root, monkeypatch):
    """Flask test client with FLASK_WEB_DIR pointing to the stub web root."""
    monkeypatch.setenv("FLASK_WEB_DIR", str(web_root))
    # Import after env var is set so create_app() reads the override
    from create_app import create_app as _make_app
    app = _make_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture()
def client_without_web(tmp_path, monkeypatch):
    """Flask test client with FLASK_WEB_DIR pointing to a non-existent directory."""
    monkeypatch.setenv("FLASK_WEB_DIR", str(tmp_path / "absent-dir"))
    from create_app import create_app as _make_app
    app = _make_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Tests: catch-all active (web/ present) ────────────────────────────────────

class TestCatchAllActive:
    def test_root_returns_index_html(self, client_with_web):
        resp = client_with_web.get("/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert b"<!DOCTYPE html>" in resp.data, "Root must serve Angular index.html"

    def test_unknown_angular_route_returns_index_html(self, client_with_web):
        resp = client_with_web.get("/projects/my-project/tasks/3")
        assert resp.status_code == 200, (
            f"Angular route /projects/... must fall back to index.html, got {resp.status_code}"
        )
        assert b"<!DOCTYPE html>" in resp.data

    def test_existing_static_asset_served_directly(self, client_with_web):
        resp = client_with_web.get("/assets/icon.png")
        assert resp.status_code == 200, f"Static asset must be served, got {resp.status_code}"
        # Verify PNG magic bytes — not the HTML index
        assert resp.data[:4] == b"\x89PNG", (
            "Static file must be served as-is, not replaced by index.html"
        )

    def test_api_routes_are_not_captured_by_catchall(self, client_with_web):
        # /api/health/neon returns {"status": "skipped"} with 200 (Task 3).
        # It must return JSON, not the Angular HTML.
        resp = client_with_web.get("/api/health/neon")
        assert resp.status_code == 200, (
            f"Health endpoint must respond 200, got {resp.status_code}"
        )
        assert resp.content_type.startswith("application/json"), (
            f"API routes must return JSON, not HTML. Got: {resp.content_type}"
        )
        data = resp.get_json()
        assert data is not None, "Response must be valid JSON"
        assert data.get("status") == "skipped", (
            f"Expected {{\"status\": \"skipped\"}}, got {data}"
        )

    def test_catch_all_registered_when_web_dir_present(self, web_root, monkeypatch):
        monkeypatch.setenv("FLASK_WEB_DIR", str(web_root))
        from create_app import create_app as _make_app
        app = _make_app()
        rule_names = [rule.endpoint for rule in app.url_map.iter_rules()]
        assert "serve_angular" in rule_names, (
            "serve_angular route must be registered when web/ directory exists"
        )


# ── Tests: catch-all inactive (web/ absent) ───────────────────────────────────

class TestCatchAllInactive:
    def test_catch_all_not_registered_without_web_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FLASK_WEB_DIR", str(tmp_path / "absent-dir"))
        from create_app import create_app as _make_app
        app = _make_app()
        rule_names = [rule.endpoint for rule in app.url_map.iter_rules()]
        assert "serve_angular" not in rule_names, (
            "serve_angular must NOT be registered when web/ directory is absent (dev mode)"
        )

    def test_non_api_path_returns_404_without_web_dir(self, client_without_web):
        resp = client_without_web.get("/some-angular-path")
        assert resp.status_code == 404, (
            f"Without web/, non-API paths must 404; got {resp.status_code}"
        )
```

Run tests:
```bash
cd api && python -m pytest tests/test_catch_all.py -v
# Expect: 7 passed
```

---

## 6. Commit Plan

**Executor instruction**: commit after **each** step completes — not at the end of the task. Run the commit command shown before moving to the next step.

```
1. chore(docker): add .dockerignore for multi-stage build context
   — after Step 1 — files: .dockerignore
   git add .dockerignore && git commit -m "chore(docker): add .dockerignore for multi-stage build context"

2. feat(docker): add multi-stage Dockerfile (Node build + Python final)
   — after Step 2 — files: Dockerfile
   git add Dockerfile && git commit -m "feat(docker): add multi-stage Dockerfile (Node build + Python final)"

3. chore(api): add gunicorn to requirements.txt
   — after Step 3, ONLY if gunicorn was missing — files: api/requirements.txt
   git add api/requirements.txt && git commit -m "chore(api): add gunicorn to requirements.txt"
   (Skip this commit entirely if gunicorn was already present.)

4. feat(app): add Angular SPA catch-all route to create_app
   — after Step 4 — files: api/create_app.py
   git add api/create_app.py && git commit -m "feat(app): add Angular SPA catch-all route to create_app"

5. ci(frontend): add build-frontend job to gate on ng build
   — after Step 5 — files: .github/workflows/deploy.yml
   git add .github/workflows/deploy.yml && git commit -m "ci(frontend): add build-frontend job to gate on ng build"

6. ci(docker): update docker-build job for multi-stage image and smoke test
   — after Step 6 — files: .github/workflows/deploy.yml
   git add .github/workflows/deploy.yml && git commit -m "ci(docker): update docker-build job for multi-stage image and smoke test"

7. test(catch-all): add pytest tests for Angular SPA catch-all route
   — after tests pass — files: api/tests/test_catch_all.py
   git add api/tests/test_catch_all.py && git commit -m "test(catch-all): add pytest tests for Angular SPA catch-all route"
```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Backend test suite
cd api && make test
# Expected: 624 → 631 passing (7 new catch-all tests), 1 skipped unchanged

# Lint
cd api && make lint
# Expect: 0 flake8 violations

# DTO drift check
cd api && make check-dtos
# Expect: no diff (no openapi.yaml changes)

# Local Docker build (requires web/node_modules or pre-built dist)
cd {WORKSPACE}/spec-doc
docker build -t spec-doc:verify .
docker run --rm -e SPEC_DOC_DIR=/tmp/p -e CHAIN_PROVIDER=anthropic_sdk \
  -p 3101:3101 spec-doc:verify &
sleep 8
curl -s http://localhost:3101/ | grep -qi "<!DOCTYPE html>" && echo "ROOT PASS"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3101/api/health/neon
# Expect: 200
docker stop $(docker ps -q --filter ancestor=spec-doc:verify)
```

**Expected delta**: 624 → 631 passing. Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: every commit is independently revertible.
  ```bash
  git revert <sha>   # creates a revert commit — safe on master
  ```

- **Per-branch**: if verification fails catastrophically after multiple steps, reset to the pre-task SHA:
  ```bash
  # Record the SHA before starting (from pre-flight git log):
  git reset --hard <pre-task-sha>    # [REQUIRES APPROVAL] — destroys uncommitted work
  # OR if on a feature branch:
  git checkout master && git branch -D feature/task-4-ci-docker
  ```

- **CI-only rollback**: if the pipeline breaks but local tests pass, revert only the workflow file:
  ```bash
  git revert <ci-step-sha>   # reverts the deploy.yml change
  ```

---

## 9. Deviations Allowed

- **`angular.json` outputPath differs from `dist/spec-doc/browser`** → use the actual path from the pre-flight check throughout the Dockerfile and CI artifact path. Update both `upload-artifact path:` and `download-artifact path:` to match. Log the actual path in the commit body.
- **`package-lock.json` absent in `web/`** → change `npm ci` to `npm install` in both the CI job and the Dockerfile build stage. Log in commit body.
- **`gunicorn` already in `requirements.txt`** → skip Step 3 entirely; no commit for it.
- **`/api/health/neon` not yet implemented (Task 3 not done)** → replace the `test_api_routes_are_not_captured_by_catchall` assertion with any stable existing route (e.g., `GET /api/templates`). Adjust the status/content-type assertions to match. Log deviation.
- **Step 5 or 6 requires editing the same deploy.yml in one session** → read the file once before Step 5, apply both changes in one combined edit, then commit Step 5 and Step 6 separately using `git add -p` to stage hunks individually.
- **Side-effect required** (e.g., push to remote, publish image) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task wires the build gate and production container shape. It does not address any runtime operational concerns, alternative deploy topologies, or image distribution. The scope boundary is: CI blocks on a broken build, the image is smoke-tested, and Flask serves the Angular SPA in the production container.

- **Container registry push (GHCR / Docker Hub)** — Coolify builds from source on the deploy host; no push step is required or designed. Revisit only if the deploy target changes to a pull-based runtime (e.g., Kubernetes).
- **nginx sidecar inside the container** — Coolify Traefik handles SSL termination and routing; a sidecar adds operational overhead for zero benefit at this deploy topology. Defer until the first performance requirement that gunicorn cannot satisfy.
- **Angular unit tests (`ng test`) in CI** — `ng build` catches type errors, missing imports, and broken templates. Karma/Jest CI is a separate concern; add it as a follow-up task when test coverage justifies the CI minutes.
- **Docker layer caching via `--cache-from`** — the `test -d dist/...` guard already avoids re-running `ng build` in CI; full layer caching requires a registry. Defer until the registry is set up.
- **`SPEC_DOC_DIR` as a named Docker volume in `docker-compose.yml`** — the production volume mount is addressed in the Docker Compose production task (see architecture braindump). This task only ensures the env var is passed in the CI smoke test.
- **Per-PR preview deploys** — not needed at team size of one; revisit at team growth.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for multi-stage Dockerfile and CI extension
- [Epic](./epic.md) – Task scope and port budget
- [Timeline](./timeline.md) – Update status to ✅ after verification passes