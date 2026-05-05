# Task 2: web/Dockerfile + nginx config — Implementation Guide

## 1. Context

This task produces the two infrastructure files that turn the Angular SPA into a shippable container image: a two-stage `web/Dockerfile` (Node build → nginx:alpine runtime) and a `web/nginx/nginx.conf` that handles SPA fallback, `/api/` reverse-proxy to Flask, static-asset caching, and deferred backend DNS so the frontend container can start independently of the API container. Neither file is referenced by the compose file yet — Task 4 wires the `web` service to `build: ./web`. The purpose here is to get the image buildable and the nginx config syntactically verified in isolation, so Task 4 can wire them up without revisiting this work.

**Trade-offs considered:**
- **Single-stage Dockerfile (node:alpine, serve the dist with `npx serve`)** — rejected because it bundles Node in the production image; nginx:alpine is ~8 MB vs ~180 MB and is purpose-built for static serving.
- **Baking the nginx config into the `api/` Flask server via a catch-all route** — already exists for single-container dev (ported from humanize-me reference); rejected here because the compose deployment needs a distinct frontend service that can be scaled, updated, and cache-headered independently.
- **Two-stage Dockerfile + nginx:alpine with deferred DNS** — preferred because it matches the Trendfy/humanize-me reference patterns, keeps the production image minimal, and the `resolver 127.0.0.11 + set $upstream` pattern is the standard Docker-embedded-DNS technique for container-startup independence.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# From {WORKSPACE} = spec-doc/ root
git status                                          # Flag any unrelated M/?? entries
git diff HEAD -- web/Dockerfile web/nginx/nginx.conf web/.dockerignore
# Both commands should produce no output — files do not exist yet

# Confirm Angular project name and output path (drives COPY --from path in Dockerfile)
grep -E '"outputPath"|"projects"' web/angular.json
# Expected: "outputPath": "dist/spec-doc"  and project key "spec-doc"
# Angular 17+ application builder appends /browser, so the dist path is dist/spec-doc/browser
# If outputPath differs, use whatever angular.json declares — adjust the COPY line in Step 2

# Baseline test count
cd api && python -m pytest --tb=no -q 2>&1 | tail -3
# Record: e.g. "624 passed, 1 skipped"
cd ..
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: 624 passed, 1 skipped (per CODEBASE CONTEXT).

---

## 3. Files

### To Create (new)

- `web/.dockerignore` — excludes `node_modules`, `.git`, and Angular cache from the Docker build context; prevents local installs from shadowing `npm ci` and keeps the build layer deterministic
- `web/Dockerfile` — two-stage build: Stage 1 (`builder`) installs deps + runs `npm run build`; Stage 2 (`runtime`) is `nginx:alpine` serving the compiled dist
- `web/nginx/nginx.conf` — nginx server block: static-asset cache, `/api/` proxy with deferred DNS and streaming support, SPA `try_files` fallback
- `api/tests/test_web_infra.py` — structural pytest tests verifying the three files above exist and contain the required directives

### To Modify (cite CODEBASE CONTEXT)

_(none — this task is a pure addition)_

### To Leave Alone

- `web/angular.json` — read for the `outputPath` value but never edited; changing it would break the Angular CLI dev server
- `web/src/` — Angular source; no changes
- `api/` — Flask backend; not affected by frontend containerisation
- root `docker-compose.yml` — Task 3 will add the `web` service; do not touch it here

---

## 4. Implementation Steps

### Step 1: Add web/.dockerignore

**Action**: Create `.dockerignore` in `web/` so that `node_modules`, Angular cache, and git metadata are excluded from the Docker build context sent to the daemon. Without this, a local `node_modules/` would be copied into the builder stage before `npm ci` runs, potentially shadowing platform-incompatible binaries or bloating the layer.

**File**: `web/.dockerignore` (new)

**Pattern**:
```
node_modules
.angular
dist
.git
*.md
.env*
coverage
```

**Verify**: `wc -l web/.dockerignore` — expect ≥ 7 lines; `cat web/.dockerignore` — confirm `node_modules` and `.angular` are listed.

---

### Step 2: Add web/Dockerfile

**Action**: Create a two-stage Dockerfile. Stage 1 (`builder`) uses `node:20-alpine`, installs dependencies with `npm ci`, and runs the production Angular build. Stage 2 (`runtime`) uses `nginx:alpine`, copies in the compiled dist and the nginx config, and exposes port 80.

Before writing the `COPY --from` line, confirm the Angular output path from pre-flight (`grep outputPath web/angular.json`). Angular 17's application builder appends `/browser` to `outputPath`. spec-doc declares `"outputPath": "dist/spec-doc"` so the dist path is `dist/spec-doc/browser` — confirmed by `api/Dockerfile:46`. Adjust if `angular.json` ever changes.

**File**: `web/Dockerfile` (new)

**Pattern** (port structure from humanize-me multi-stage reference, adapted for Angular):
```dockerfile
# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies first (layer-cached when only source changes)
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM nginx:alpine AS runtime

# nginx config (must match path in nginx.conf root directive)
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Angular dist — confirmed path from web/angular.json (outputPath: dist/spec-doc).
# Angular 17 application builder appends /browser. Matches existing api/Dockerfile:46.
COPY --from=builder /app/dist/spec-doc/browser /usr/share/nginx/html

EXPOSE 80
```

**Verify**:
```bash
# Syntax check only — does not run the container
docker build --target builder --no-cache -t spec-doc-web-builder-test web/
# Expect: "Successfully built ..." with npm ci + ng build output
# If outputPath is wrong, ng build will fail with "Output path does not exist"
```

---

### Step 3: Add web/nginx/nginx.conf

**Action**: Create `web/nginx/nginx.conf` with three `location` blocks: (1) static-asset cache for hashed Angular assets, (2) `/api/` proxy to the Flask container with deferred DNS resolution and streaming support, (3) SPA fallback for all other paths. The deferred-DNS pattern (`resolver 127.0.0.11 + set $upstream`) ensures nginx does not crash on startup if the `api` container isn't yet healthy — port pattern from Trendfy `nginx/nginx.conf` (`proxy_read_timeout 3600s`, adapted to 1800s to match the Angular HTTP timeout in the builder profile).

**File**: `web/nginx/nginx.conf` (new)

**Pattern**:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # ── Static assets (Angular outputs content-hashed filenames) ────────────
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # ── API proxy ─────────────────────────────────────────────────────────────
    # resolver 127.0.0.11 = Docker embedded DNS; valid=30s re-resolves on churn
    # set $upstream defers DNS lookup to request time — frontend starts without api
    location /api/ {
        resolver 127.0.0.11 valid=30s ipv6=off;
        set $upstream http://api:3101;
        proxy_pass $upstream;

        proxy_http_version 1.1;
        proxy_set_header Host               $host;
        proxy_set_header X-Real-IP          $remote_addr;
        proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
        proxy_set_header Connection         "";

        proxy_buffering    off;          # required for SSE streaming
        proxy_read_timeout 1800s;        # matches Angular HTTP timeout (30 min)
        proxy_connect_timeout 10s;
    }

    # ── SPA fallback ──────────────────────────────────────────────────────────
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Verify**:
```bash
# Mount the config into nginx:alpine and run a syntax check
docker run --rm \
  -v "$(pwd)/web/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine nginx -t
# Expect: "nginx: configuration file /etc/nginx/nginx.conf test is successful"
```

---

### Step 4: Full image build smoke-test

**Action**: Build the complete two-stage image (both stages) to confirm the Dockerfile and nginx.conf wire together without error. This catches any `outputPath` mismatch before Task 3 wires the compose file.

**File**: `web/Dockerfile` (already created in Step 2)

**Pattern**:
```bash
docker build -t spec-doc-web:local web/
```

**Verify**:
```bash
docker build -t spec-doc-web:local web/
# Expect: final line "Successfully tagged spec-doc-web:local" (or equivalent Buildkit output)

# Optional: confirm /usr/share/nginx/html is populated
docker run --rm spec-doc-web:local ls /usr/share/nginx/html
# Expect: index.html and hashed JS/CSS bundles
```

---

## 5. Tests

Tests live in `api/tests/test_web_infra.py` and follow the structural test pattern already used in the repo (Python `pathlib` + `pytest` assertions, no mocking). The tests verify that each file exists and contains the specific directives that downstream tasks and the CI pipeline depend on. These tests run in the existing `make test` suite.

```python
# api/tests/test_web_infra.py
"""Structural tests — verify web/Dockerfile and web/nginx/nginx.conf exist
and contain the directives required by the compose deployment (Task 3)."""

from pathlib import Path

# spec-doc root: api/tests/ → api/ → spec-doc/
WORKSPACE = Path(__file__).resolve().parents[2]
WEB = WORKSPACE / "web"


class TestDockerignore:
    def test_dockerignore_exists(self):
        assert (WEB / ".dockerignore").exists(), \
            "web/.dockerignore must exist to prevent node_modules from entering build context"

    def test_dockerignore_excludes_node_modules(self):
        content = (WEB / ".dockerignore").read_text()
        assert "node_modules" in content, \
            "web/.dockerignore must exclude node_modules"

    def test_dockerignore_excludes_angular_cache(self):
        content = (WEB / ".dockerignore").read_text()
        assert ".angular" in content, \
            "web/.dockerignore must exclude .angular cache dir"


class TestDockerfile:
    def test_dockerfile_exists(self):
        assert (WEB / "Dockerfile").exists(), \
            "web/Dockerfile must exist for the frontend container build"

    def test_dockerfile_has_builder_stage(self):
        content = (WEB / "Dockerfile").read_text()
        assert "AS builder" in content, \
            "Dockerfile must declare a named 'builder' stage for multi-stage COPY"

    def test_dockerfile_runtime_is_nginx_alpine(self):
        content = (WEB / "Dockerfile").read_text()
        assert "FROM nginx:alpine" in content, \
            "Dockerfile runtime stage must use nginx:alpine"

    def test_dockerfile_copies_nginx_conf(self):
        content = (WEB / "Dockerfile").read_text()
        assert "nginx/nginx.conf" in content, \
            "Dockerfile must COPY nginx/nginx.conf into the runtime stage"

    def test_dockerfile_exposes_port_80(self):
        content = (WEB / "Dockerfile").read_text()
        assert "EXPOSE 80" in content, \
            "Dockerfile must expose port 80 for the compose service mapping"

    def test_dockerfile_copies_from_builder(self):
        content = (WEB / "Dockerfile").read_text()
        assert "COPY --from=builder" in content, \
            "Dockerfile must copy the dist artefact from the builder stage"


class TestNginxConf:
    def test_nginx_conf_exists(self):
        assert (WEB / "nginx" / "nginx.conf").exists(), \
            "web/nginx/nginx.conf must exist"

    def test_nginx_conf_spa_fallback(self):
        content = (WEB / "nginx" / "nginx.conf").read_text()
        assert "try_files" in content, \
            "nginx.conf must include try_files for SPA client-side routing"
        assert "index.html" in content, \
            "nginx.conf try_files must fall back to index.html"

    def test_nginx_conf_api_proxy(self):
        content = (WEB / "nginx" / "nginx.conf").read_text()
        assert "/api/" in content, \
            "nginx.conf must proxy /api/ to the Flask backend"
        assert "proxy_pass" in content, \
            "nginx.conf must contain a proxy_pass directive"

    def test_nginx_conf_deferred_dns(self):
        content = (WEB / "nginx" / "nginx.conf").read_text()
        assert "resolver" in content, \
            "nginx.conf must declare a resolver for deferred DNS lookup"
        assert "set $" in content, \
            "nginx.conf must use a variable-based proxy_pass to defer DNS resolution"

    def test_nginx_conf_proxy_buffering_off(self):
        content = (WEB / "nginx" / "nginx.conf").read_text()
        assert "proxy_buffering" in content and "off" in content, \
            "nginx.conf must disable proxy_buffering for SSE streaming support"

    def test_nginx_conf_static_cache_headers(self):
        content = (WEB / "nginx" / "nginx.conf").read_text()
        assert "Cache-Control" in content, \
            "nginx.conf must set Cache-Control headers on static assets"
        assert "immutable" in content, \
            "nginx.conf Cache-Control must include immutable for content-hashed assets"
```

---

## 6. Commit Plan

**Executor instruction**: commit after **each** step completes — not at the end. Run the commit command before moving to the next step.

1. `chore(web): add .dockerignore for angular build context` — after Step 1 — files: `web/.dockerignore`
   ```bash
   git add web/.dockerignore
   git commit -m "chore(web): add .dockerignore for angular build context"
   ```

2. `feat(web): add two-stage dockerfile — node build + nginx runtime` — after Step 2 — files: `web/Dockerfile`
   ```bash
   git add web/Dockerfile
   git commit -m "feat(web): add two-stage dockerfile — node build + nginx runtime"
   ```

3. `feat(web): add nginx.conf with spa fallback, api proxy, and deferred dns` — after Step 3 — files: `web/nginx/nginx.conf`
   ```bash
   git add web/nginx/nginx.conf
   git commit -m "feat(web): add nginx.conf with spa fallback, api proxy, and deferred dns"
   ```

4. `test(web): add structural tests for frontend container files` — after tests pass — files: `api/tests/test_web_infra.py`
   ```bash
   git add api/tests/test_web_infra.py
   git commit -m "test(web): add structural tests for frontend container files"
   ```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation (e.g., `Deviations: dist/spec-doc/browser used instead of dist/web/browser — confirmed from angular.json`).

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → 636 passing (12 new structural assertions across 4 test classes), 1 skipped unchanged. Zero pre-existing tests broken.

Additionally, for the full image build:

```bash
# Syntax check
docker run --rm \
  -v "$(pwd)/web/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine nginx -t

# Full image build
docker build -t spec-doc-web:local web/
```

Both commands must exit 0 before this task is considered complete.

---

## 8. Rollback

- **Per-step**: each step has its own commit. Revert individually with:
  ```bash
  git revert <sha> --no-edit
  ```
  Steps are independent — reverting Step 3 (nginx.conf) does not require reverting Step 2 (Dockerfile).

- **Per-branch**: if all four commits need to be unwound, record the SHA before starting (`git rev-parse HEAD`) and reset:
  ```bash
  git reset --hard <pre-task-sha>
  ```
  This is safe because no existing files are modified — only new files are added.

---

## 9. Deviations Allowed

- **`outputPath` in `angular.json` is not `dist/spec-doc`** → update the `COPY --from=builder` line in the Dockerfile to match (remember to append `/browser`); log the actual path in the commit body. Do not invent the path — read it from `angular.json` first.
- **`npm run build` is not a defined script in `web/package.json`** → substitute `npx ng build --configuration production`; log as deviation.
- **`resolver 127.0.0.11` rejected by `nginx -t`** (not inside a Docker network) → this is expected when testing outside Docker; skip the resolver line in local testing only, restore it before committing.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log in commit body.
- **Side-effect required** (push, publish, remote deploy) → STOP, mark [REQUIRES APPROVAL].

---

## 10. Out of Scope

This task produces the frontend container image and nginx configuration as a standalone, buildable unit. It does not wire the image into any running system — that is deliberately deferred to Task 3 (docker-compose.yml) and the CI/CD pipeline task. An eager executor might be tempted to extend this task, but everything below is explicitly out of scope here:

- **Root `docker-compose.yml` edits** — Task 3 adds the `web` service; touching compose here creates a merge conflict with an incomplete API service definition.
- **CI/CD pipeline integration** — the `deploy.yml` workflow will reference `spec-doc-web:local` only after compose is wired; adding it here is premature.
- **TLS / HTTPS termination** — Coolify handles TLS at the edge; nginx listens on port 80 only. TLS config belongs in the Coolify project settings, not this file.
- **Environment-specific nginx.conf variants** — one config covers both staging and production; environment differences (if any) are handled via Coolify environment variables, not multiple config files.
- **Angular build optimisation flags** (`--source-map=false`, `--named-chunks`, etc.) — defaults are acceptable; premature until a specific production performance issue is identified.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for the two-container compose layout
- [Epic](./epic.md) – Task scope and ordering
- [Timeline](./timeline.md) – Update status to ✅ after verification passes