# Task 2: Create Frontend Container — Implementation Guide

## 1. Context

This task adds the two files that define the frontend container: `web/Dockerfile` and `web/nginx/nginx.conf`. Together they promote nginx to own everything the web tier needs — serving the Angular SPA, applying `Cache-Control: immutable` to hash-named bundles, proxying `/api/` to the Flask backend with `proxy_buffering off` for SSE safety, and deferring DNS resolution via the `set $backend` variable trick so the frontend container starts cleanly before the backend is healthy. Neither file touches existing Flask source or Angular source. Compose wiring, the `environment.ts` base-URL change, and `web_serve_bp` removal are all deferred to later tasks, so today's changes are completely isolated and independently buildable.

**Trade-offs considered:**
- **Nginx in the Flask image (current state)** — rejected because it couples the Python runtime and Node build stage, prevents independent scaling, and cannot set nginx directives like `proxy_buffering off` without an extra sidecar.
- **Separate nginx reverse-proxy tier (wardrobai pattern)** — rejected per ELA Pattern #5: spec-doc has exactly one SPA and one backend; a third container is a premature abstraction with no second consumer to justify it.
- **nginx:alpine final stage with node:20-alpine builder (chosen)** — matches the proven pattern already shipping in humanize-me and speedback; keeps the image minimal and produces a single EXPOSE 80 entry point that Coolify's Traefik can route to by domain.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From repo root — confirm clean working tree on target files
git status
git diff HEAD -- web/Dockerfile web/nginx/nginx.conf

# Confirm neither file exists yet
ls web/Dockerfile 2>/dev/null && echo "EXISTS — stop" || echo "absent — ok"
ls web/nginx/       2>/dev/null && echo "EXISTS — stop" || echo "absent — ok"

# Confirm the Angular dist output path (must match the Dockerfile COPY)
grep -E "outputPath|\"browser\"" web/angular.json

# Record baseline test count
cd api && python -m pytest --tb=no -q 2>&1 | tail -3
cd ..
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Angular dist path to confirm**: the existing `api/Dockerfile` (line 46) already proves the output is `dist/spec-doc/browser`. The grep above is a belt-and-suspenders check. If `angular.json` shows a different path, treat it as truth and update the Dockerfile COPY in Step 2 accordingly — log as a deviation.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)
- `web/Dockerfile` — two-stage build: `node:20-alpine` compiles the Angular app; `nginx:alpine` serves the dist and owns the nginx config
- `web/nginx/nginx.conf` — three location blocks: `/api/ ^~` proxy (SSE-safe, DNS-deferred), static asset cache headers, SPA try_files fallback
- `api/tests/test_web_container.py` — structural tests verifying the two new files encode all load-bearing constraints

### To Modify (cite CODEBASE CONTEXT)
_(none — this task creates only)_

### To Leave Alone
- `api/Dockerfile` — existing multi-stage Flask+Angular image; still used by the current `docker-compose.yml` and `deploy.yml`; Task 3 splits compose, Task 5 simplifies this file
- `api/create_app.py` — `web_serve_bp` is still registered (line 119); Task 5 removes it after the split is verified live
- `web/angular.json` — read for confirmation only; not modified
- `web/proxy.conf.json` — Angular dev-server proxy config; untouched; Task 5 aligns `environment.ts`
- `api/tests/test_docker.py` — existing structural tests for `api/Dockerfile` and `api/docker-compose.yml`; must stay green

---

## 4. Implementation Steps

### Step 1: Confirm Angular dist output path

**Action**: Read `web/angular.json` and record the confirmed dist path before writing any Dockerfile. The current `api/Dockerfile` declares `dist/spec-doc/browser` — verify `angular.json` agrees.

**File**: `web/angular.json` (existing — read only)

**Pattern**:
```bash
# Run from repo root
grep -A2 "outputPath" web/angular.json
# Expected output contains: "dist/spec-doc/browser"
# or: "browser": "dist/spec-doc/browser"
```

**Verify**: grep output contains `spec-doc` and `browser` on the same line or adjacent lines. If the path differs from `dist/spec-doc/browser`, record the real path, update the COPY directive in Step 2, and log as a deviation in the commit body.

> No commit for this step — it is an audit step with no file output.

---

### Step 2: Create `web/Dockerfile`

**Action**: Create the two-stage Dockerfile. Build context is `web/` (confirmed by the docker-compose `build: ./web` in Task 3), so all `COPY` paths are relative to `web/`.

**File**: `web/Dockerfile` (new)

**Pattern**:
```dockerfile
# ── Stage 1: Angular build ──────────────────────────────────────────────────
# node:20-alpine matches the version used in the existing api/Dockerfile
# (api/Dockerfile line 12) and the CI Python+Node setup.
FROM node:20-alpine AS frontend-builder
WORKDIR /workspace

# Copy lockfiles first — better layer-cache behaviour on dep-only changes.
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit --progress=false

# Copy Angular source and build the production bundle.
# Angular 17+ application builder outputs to dist/spec-doc/browser/.
# Confirmed from api/Dockerfile line 46 and web/angular.json outputPath.
COPY . .
RUN npx ng build --configuration production

# ── Stage 2: nginx serve ────────────────────────────────────────────────────
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Copy Angular bundle from the build stage.
COPY --from=frontend-builder /workspace/dist/spec-doc/browser ./

# nginx config owns: SPA fallback, /api/ proxy, static asset cache headers.
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

**Verify**:
```bash
# Structural check (no Docker build needed at this step)
grep -c "FROM" web/Dockerfile
# Expected: 2  (one builder stage, one final stage)

grep "dist/spec-doc/browser" web/Dockerfile
# Expected: one COPY --from=frontend-builder line
```

**Commit after this step** — see Commit Plan item 1.

---

### Step 3: Create `web/nginx/nginx.conf`

**Action**: Create the `web/nginx/` directory and write the config. Three location blocks in priority order: `^~` API proxy (wins over regex), regex static-asset cache, prefix SPA fallback. The `set $backend` variable + `resolver 127.0.0.11` pair is the load-bearing pattern for Docker DNS deferral — nginx will not fail to start if the backend container is not yet resolvable.

**File**: `web/nginx/nginx.conf` (new)

**Pattern** (port the shape from the architecture doc's Frontend Container section; no reference file is directly readable, but the constraints are fully specified):
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Docker embedded DNS — resolves "backend" service name.
    # valid=30s re-resolves after backend restarts; prevents stale IP cache.
    resolver 127.0.0.11 valid=30s;

    # ── /api/ proxy ──────────────────────────────────────────────────────────
    # ^~ prefix: takes priority over regex locations; /api/ requests never
    # fall through to the static-asset block even if they carry a file extension.
    # proxy_buffering off: required for SSE — nginx default buffering silently
    # breaks streaming responses (task-gen, bootstrap-project events).
    # proxy_read_timeout 900s: matches gunicorn --timeout 900; covers the 15-minute
    # AI provider ceiling documented in api/Dockerfile and references.md (Trendfy).
    location ^~ /api/ {
        set $backend http://backend:3101;
        proxy_pass $backend;

        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_buffering      off;
        proxy_read_timeout   900s;
        proxy_connect_timeout 10s;
        proxy_send_timeout   900s;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ── Static assets ─────────────────────────────────────────────────────────
    # Angular 17 production builder emits hash-named JS/CSS bundles; these are
    # safe to cache immutably because the hash changes with every build.
    location ~* \.(js|css|woff2?|ttf|eot|ico|svg|png|jpg|jpeg|gif|webp|map)$ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # ── SPA fallback ──────────────────────────────────────────────────────────
    # All unmatched paths return index.html so Angular's client-side router
    # handles deep-link URLs (e.g. /projects/my-project-123) without 404.
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Verify**:
```bash
grep "proxy_buffering" web/nginx/nginx.conf
# Expected: proxy_buffering      off;

grep "proxy_read_timeout" web/nginx/nginx.conf
# Expected: proxy_read_timeout   900s;

grep "try_files.*index.html" web/nginx/nginx.conf
# Expected: try_files $uri $uri/ /index.html;

grep "set \$backend" web/nginx/nginx.conf
# Expected: set $backend http://backend:3101;

grep "resolver" web/nginx/nginx.conf
# Expected: resolver 127.0.0.11 valid=30s;
```

**Commit after this step** — see Commit Plan item 2.

---

### Step 4: Add structural tests

**Action**: Create `api/tests/test_web_container.py`. Follow the naming convention in `api/tests/test_docker.py` — function names with underscores (collected by `python_functions = ["*_*"]` in `api/pyproject.toml` line 5). The path sentinel `_WEB` must resolve to `web/` relative to the repo root regardless of `cwd` — use `Path(__file__).parent.parent.parent / "web"`.

**File**: `api/tests/test_web_container.py` (new)

**Pattern**: see § 5 Tests below for complete bodies.

**Verify**:
```bash
cd api
python -m pytest tests/test_web_container.py -v --tb=short
# Expected: 11 passed, 0 failed
cd ..
```

**Commit after this step** — see Commit Plan item 3.

---

## 5. Tests

Complete assertion bodies. Framework: `pytest` with plain `assert`. Pattern mirrors `api/tests/test_docker.py`. Add to `api/tests/test_web_container.py`.

```python
"""Structural tests for the web/ frontend container files.

Verifies that web/Dockerfile and web/nginx/nginx.conf encode
all load-bearing constraints from the architecture:
  - Two-stage build: node:20-alpine builder, nginx:alpine final
  - Angular dist path: dist/spec-doc/browser (confirmed from web/angular.json)
  - proxy_buffering off  — SSE streams break silently when buffering is enabled
  - proxy_read_timeout 900s — matches gunicorn timeout; covers 15-minute AI ceiling
  - SPA try_files fallback  — client-side routing requires index.html for deep links
  - set $backend variable  — defers DNS so nginx starts before backend is healthy
"""
from pathlib import Path

_WEB = Path(__file__).parent.parent.parent / "web"


# ── web/Dockerfile ───────────────────────────────────────────────────────────

def web_dockerfile_exists():
    assert (_WEB / "Dockerfile").is_file(), \
        "web/Dockerfile not found — Task 2 must create it"


def web_dockerfile_builder_stage_uses_node20_alpine():
    text = (_WEB / "Dockerfile").read_text()
    assert "FROM node:20-alpine" in text, (
        "Builder stage must use node:20-alpine — "
        "matches the version in api/Dockerfile and existing CI config"
    )


def web_dockerfile_final_stage_uses_nginx_alpine():
    text = (_WEB / "Dockerfile").read_text()
    assert "FROM nginx:alpine" in text, (
        "Final stage must use nginx:alpine — "
        "lightweight; proven across humanize-me and speedback"
    )


def web_dockerfile_has_two_from_stages():
    text = (_WEB / "Dockerfile").read_text()
    from_count = sum(1 for line in text.splitlines() if line.strip().startswith("FROM"))
    assert from_count == 2, (
        f"web/Dockerfile must have exactly 2 FROM stages (builder + final); found {from_count}"
    )


def web_dockerfile_copies_angular_browser_dist():
    text = (_WEB / "Dockerfile").read_text()
    assert "dist/spec-doc/browser" in text, (
        "web/Dockerfile must COPY from dist/spec-doc/browser — "
        "Angular 17 application builder writes to that path (confirmed in api/Dockerfile line 46)"
    )


def web_dockerfile_exposes_port_80():
    text = (_WEB / "Dockerfile").read_text()
    assert "EXPOSE 80" in text, \
        "web/Dockerfile must EXPOSE 80 — nginx:alpine serves HTTP on port 80"


# ── web/nginx/nginx.conf ─────────────────────────────────────────────────────

def web_nginx_conf_exists():
    assert (_WEB / "nginx" / "nginx.conf").is_file(), \
        "web/nginx/nginx.conf not found — Task 2 must create it"


def web_nginx_conf_has_proxy_buffering_off():
    text = (_WEB / "nginx" / "nginx.conf").read_text()
    assert "proxy_buffering" in text and "off" in text, (
        "nginx.conf must set proxy_buffering off — "
        "SSE streams (task-gen, bootstrap) break silently when nginx buffers the response"
    )


def web_nginx_conf_has_proxy_read_timeout_900s():
    text = (_WEB / "nginx" / "nginx.conf").read_text()
    assert "proxy_read_timeout" in text and "900" in text, (
        "nginx.conf must set proxy_read_timeout 900s — "
        "matches gunicorn --timeout 900; AI provider calls can run up to 15 minutes"
    )


def web_nginx_conf_has_spa_try_files_fallback():
    text = (_WEB / "nginx" / "nginx.conf").read_text()
    assert "try_files" in text and "index.html" in text, (
        "nginx.conf must include a try_files ... /index.html fallback — "
        "Angular client-side routes (e.g. /projects/foo) return 404 without it"
    )


def web_nginx_conf_uses_set_backend_for_dns_deferral():
    text = (_WEB / "nginx" / "nginx.conf").read_text()
    assert "set $backend" in text, (
        "nginx.conf must use 'set $backend' variable for proxy_pass — "
        "variable-based proxy_pass defers DNS resolution so nginx starts cleanly "
        "before the backend container is resolvable (Docker Compose startup race)"
    )
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step that produces file output. Step 1 (audit) has no output — do not commit for it.

**1.** `feat(web): add web/Dockerfile (node:20-alpine builder → nginx:alpine)` — after Step 2 — files: `web/Dockerfile`

```
Adds the two-stage Dockerfile for the Angular frontend container.
Stage 1: node:20-alpine compiles the Angular production bundle (dist/spec-doc/browser).
Stage 2: nginx:alpine serves the bundle on port 80.
Build context is web/ — used by docker-compose.yml frontend service (Task 3).
No changes to existing api/Dockerfile or Angular source.
```

**2.** `feat(web): add web/nginx/nginx.conf (SPA fallback, api proxy, cache headers)` — after Step 3 — files: `web/nginx/nginx.conf`

```
Three location blocks:
  ^~ /api/   proxy to backend:3101; proxy_buffering off; proxy_read_timeout 900s.
  ~* assets  Cache-Control: immutable on Angular hash-named bundles.
  /          try_files SPA fallback for client-side routing.
set $backend + resolver 127.0.0.11 defer DNS so nginx starts before backend.
```

**3.** `test(web): structural tests for web container files (11 tests)` — after Step 4 passes — files: `api/tests/test_web_container.py`

```
Asserts: web/Dockerfile exists, node:20-alpine builder, nginx:alpine final, 2 FROM stages,
dist/spec-doc/browser COPY, EXPOSE 80, nginx.conf proxy_buffering off,
proxy_read_timeout 900s, SPA try_files, set $backend DNS deferral.
```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd api
python -m pytest --tb=short -q
```

**Expected delta**: 624 → 635 passing (11 new structural tests in `test_web_container.py`). Zero pre-existing tests broken. 1 skipped count unchanged.

Optional Docker build smoke (requires Docker):
```bash
# From repo root — build context is web/
docker build --no-cache -t spec-doc-web:smoke ./web
docker run --rm -d --name spec-doc-web-smoke -p 8099:80 spec-doc-web:smoke
sleep 2
curl -sf http://localhost:8099/ | grep -i "<!doctype html" && echo "SPA ok"
docker stop spec-doc-web-smoke
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Revert Dockerfile: `git revert <sha-of-commit-1>`
  - Revert nginx.conf: `git revert <sha-of-commit-2>`
  - Revert tests: `git revert <sha-of-commit-3>`
- **Per-branch**: if verification fails and multiple commits are entangled, `git reset --hard <pre-task-sha>` on the feature branch, or `git branch -D <branch>` and start again. No deployed state has changed (Task 3 has not run); rollback is safe.

---

## 9. Deviations Allowed

- **Angular dist path differs from `dist/spec-doc/browser`** → read the confirmed path from `web/angular.json` in Step 1, update the `COPY --from=frontend-builder` line in Step 2, and log the real path in the commit body. Do not guess.
- **`web/nginx/` directory already exists** → inspect its contents before overwriting; if an `nginx.conf` already exists and differs, diff it against this guide and flag the discrepancy in the commit body rather than silently overwriting.
- **Docker not available during verification** → skip the optional Docker smoke and rely on the structural grep checks; note in Step 4 commit body.
- **Test framework mismatch** → `pyproject.toml` line 5 (`python_functions = ["test_*", "*_*"]`) already collects underscore-named functions; if the repo's pyproject.toml has changed, adapt function names to match — translate silently and note in commit body.
- **Step 2 unlocks an obvious hardening for Step 3** (e.g. a `gzip on;` block) → take it if it is a single-line addition, log as a deviation. Do not add new location blocks or restructure the proxy logic without flagging.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]`, and surface to the user.

---

## 10. Out of Scope

This task creates the two container definition files only. It does not wire them into the running system — the frontend container cannot be used end-to-end until Task 3 updates `docker-compose.yml` and Task 5 removes `web_serve_bp`. An eager executor might notice several adjacent changes and be tempted to absorb them; all of the following are explicitly deferred.

- **`docker-compose.yml` compose split** — Task 3; requires both Task 1 (`/health` route) and Task 2 to be complete first.
- **`api/Dockerfile` simplification** (remove Node stage, drop `web_serve_bp` COPY) — Task 3 as part of the compose split; leaving dead Node build stage in Flask image is acceptable for the duration of Tasks 2–4.
- **`web/angular.json` or `environment.ts` base URL change** — Task 5; the `apiUrl` pointing to `localhost:3101` must not be changed until nginx is live in Coolify and the split is verified.
- **`web_serve_bp` deletion from `create_app.py`** — Task 5; premature removal breaks the current single-container deploy path that is still live.
- **CI pipeline restructure** (parallel `frontend-ci` / `backend-ci` jobs) — Task 4; `web/Dockerfile` must exist before CI can reference it, which is exactly what this task delivers as a prerequisite.
- **`gzip` compression or Brotli encoding** — not required for correctness; can be added as a follow-up if payload size becomes a concern.
- **TLS / HTTPS termination in nginx** — Coolify/Traefik owns TLS; the frontend container must remain HTTP-only on port 80.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Frontend Container component design (§ Component Design)
- [Epic](./epic.md) — Task 2 scope definition
- [Timeline](./timeline.md) — Update status to `done` after Verification passes