# spec-doc — Unified Frontend + Backend CI/CD Pipeline

> **MERGED** into `braindump-saas-operations.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P4 — Angular build is currently untested in CI; bad `ng build` ships silently.
> **Effort**: ~1 day (Angular build job + multi-stage Dockerfile + Flask catch-all route).
> **Blocks**: nothing — Epic 6's backend pipeline keeps working without this.
> **Depends on**: Epic 6 (already shipped — backend `deploy.yml` is the foundation).
> **Siblings**: `braindump-docker-compose-production.md` (also covers Dockerfile + nginx, lower priority).
> **Port from**: bubls / Trendfy CI shape — proven multi-stage build pattern.

## What

Replace the current backend-only CI pipeline with a full-stack pipeline that tests Flask, builds Angular, validates the combined Docker image, and deploys. All jobs share a single `deploy.yml` workflow at the repo root.

The current CI runs `pytest` and a Docker smoke test but never validates Angular — a broken `ng build` can ship to production undetected. The Angular build is the most common failure surface: missing environment files, wrong base-href, broken imports.

### 1. Pipeline shape (four jobs)

```yaml
jobs:
  test-backend:       # pytest + check-dtos + flake8
  build-frontend:     # ng build --configuration production
  docker-build:       # multi-stage image: ng output + Flask; smoke test
  deploy:             # SSH rsync + docker compose up -d (on master only)
```

`docker-build` depends on both `test-backend` and `build-frontend`. `deploy` depends on `docker-build`.

### 2. test-backend (unchanged shape, moved to root)

```yaml
test-backend:
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: api
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.11" }
    - run: pip install -r requirements.txt -r requirements-dev.txt
    - run: make check-dtos
    - run: make lint
    - run: make test
```

### 3. build-frontend (new)

```yaml
build-frontend:
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: web
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: "20", cache: "npm", cache-dependency-path: "web/package-lock.json" }
    - run: npm ci
    - run: npx ng build --configuration production --base-href /
    - uses: actions/upload-artifact@v4
      with:
        name: angular-dist
        path: web/dist/spec-doc/browser/
        retention-days: 1
```

The artifact is consumed by `docker-build` to embed the static files.

### 4. docker-build — multi-stage, downloads artifact

```yaml
docker-build:
  needs: [test-backend, build-frontend]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/download-artifact@v4
      with: { name: angular-dist, path: web/dist/spec-doc/browser/ }
    - run: docker build -t spec-doc:ci .
    - name: Smoke test
      run: |
        docker run -d --name smoke \
          -e SPEC_DOC_DIR=/tmp/projects \
          -p 3101:3101 spec-doc:ci
        for i in $(seq 1 20); do
          curl -sf http://localhost:3101/health && break || sleep 3
        done
        curl -sf http://localhost:3101/api/projects
        curl -sf http://localhost:3101/  # Angular index.html served by Flask
        docker rm -f smoke
```

The final `curl` on `/` verifies Angular is embedded in the image — catches missing `COPY` in Dockerfile.

### 5. Dockerfile — multi-stage (new)

```dockerfile
# Stage 1: Angular (already built, just copy artifact)
FROM python:3.11-slim AS final
WORKDIR /app

# Flask API
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ .

# Angular static files — served by Flask send_from_directory
COPY web/dist/spec-doc/browser/ ./web/

EXPOSE 3101
CMD ["gunicorn", "--bind", "0.0.0.0:3101", "--timeout", "3600", "create_app:create_app()"]
```

Flask's catch-all route serves `web/index.html` for non-API paths. Angular router handles client-side navigation.

### 6. Flask catch-all route for Angular (new)

```python
# create_app.py — after blueprint registration
import os
from flask import send_from_directory

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_angular(path):
    if path and os.path.exists(os.path.join(WEB_DIR, path)):
        return send_from_directory(WEB_DIR, path)
    return send_from_directory(WEB_DIR, "index.html")
```

Only active when `web/` exists — dev mode (no `web/` dir) falls through to Angular dev server on :4201.

### 7. deploy job (SSH + rsync, unchanged mechanism)

```yaml
deploy:
  needs: docker-build
  if: github.ref == 'refs/heads/master'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/download-artifact@v4
      with: { name: angular-dist, path: web/dist/spec-doc/browser/ }
    - run: rsync -az --delete . ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }}:/srv/spec-doc/
    - run: ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} "cd /srv/spec-doc && docker compose up -d --build"
```

## Why now

The Angular build is untested in CI. A bad import or missing env file breaks production silently. The `ng build` step catches this in ~2 minutes instead of at deploy time. The multi-stage Docker image also eliminates the "works on my machine" gap between local dev and the container.

The pipeline shape is already proven in Springular and Trendfy — this is a port.

## What's missing

Two decisions:

1. **Where does Angular get its environment config?** `environment.prod.ts` has the API URL hardcoded to `localhost:3101` in dev. In the single-container model, Angular is served from the same origin as Flask — the base URL becomes `/api`. Options:
   - (a) Build with `--replace` to inject the right base URL at CI time (brittle)
   - (b) Angular detects same-origin and sets base to `/api` (runtime logic)
   - (c) Environment file baked at build time via secret (requires secret in CI)

2. **Health endpoint**: Flask doesn't have `/health` yet. Add a trivial `@app.get("/health")` returning `{"ok": true}` before the smoke test step can run.

## Explicitly out of scope

- Separate Angular container (nginx) — single-container Flask+static is simpler for this scale
- Kubernetes / Helm — Docker Compose on a single VPS is the deployment target
- Preview deploys per PR — not needed at current team size
- Angular unit tests in CI — zero Angular tests exist; add them when they exist
