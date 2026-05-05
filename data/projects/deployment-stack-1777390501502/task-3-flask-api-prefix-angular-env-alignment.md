Now I have all the context I need. Let me write the guide.

---

# Task 3: Flask `/api/` prefix + Angular env alignment

## 1. Context

Every Flask route that currently lacks an `/api/` prefix — namely the inline `GET /health` in `create_app.py` — gains that prefix so the full route map is partition-clean: anything under `/api/` is Flask; anything else is Angular static or nginx infrastructure. Simultaneously, Angular's `environment.ts` switches from the absolute `http://localhost:3101/api` dev origin to the relative `/api` so dev (via a new `proxy.conf.json` forwarding to Flask) and prod (via nginx) resolve identically, eliminating environment-specific branching in every service. `web_serve_bp` is evicted: once nginx owns static serving the Flask catch-all blueprint is dead weight that shadows `/<path:path>` and confuses future route-debugging. This task also updates the eight test files that currently hard-code the bare `/health` path or assert the absence of `proxy.conf.json`; both of those structural assertions invert in this task.

**Trade-offs considered:**
- **App-level `url_prefix` on Flask** — rejected; all feature blueprints already carry `/api/` in their individual `url_prefix`, so adding a second layer would double-prefix every route. The only uncovered routes are the two inline app-level ones (`/health`, `/specs/<filename>`); renaming the decorator is the minimal, targeted fix.
- **Keep `web_serve_bp`, add nginx in front** — rejected for this task; the blueprint continues to shadow `/<path:path>` even behind nginx and adds complexity for a future nginx task to unwind. The epic explicitly removes it here.
- **Chosen**: rename the one bare inline route (`/health` → `/api/health`), unregister `web_serve_bp`, update Angular env to relative `/api` with a dev-proxy — net change is a reduction in lines of code.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/api

git checkout -b task/3-api-prefix-angular-env

git status                              # confirm clean working tree on task files
git diff HEAD -- create_app.py openapi.yaml docker-compose.yml \
  modules/web_serve/routes.py \
  tests/test_health.py tests/test_config_envvar.py tests/test_contracts.py \
  tests/test_openapi_spec.py tests/test_ai_rewrite.py tests/test_deploy_config.py \
  tests/test_retire_express.py tests/test_structural.py

python -m pytest --tb=no -q           # record baseline; expect 624 passed, 1 skipped
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: 624 / 625 passing (1 skipped).

> **Gate — resolve before merging**: open the Coolify dashboard and any external uptime-monitor config to confirm whether the bare `/health` path is registered as a liveness probe target. If it is, you must update those external monitors as part of the deploy step (mark that action **[REQUIRES APPROVAL]** in the PR description). Coolify's in-container probe at `docker-compose.coolify.yml` is updated in Step 3 of this guide and is safe to change.

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/proxy.conf.json` — Angular ng-serve dev proxy; forwards `/api/*` to Flask `:3101` so `apiUrl: '/api'` resolves during local development

### To Modify
- `{WORKSPACE}/api/create_app.py` — remove `web_serve_bp` import + registration; rename inline route decorator from `/health` → `/api/health`
- `{WORKSPACE}/api/openapi.yaml` — rename path key `/health` → `/api/health` (contract stays aligned with Flask)
- `{WORKSPACE}/api/docker-compose.yml` — update healthcheck probe URL `/health` → `/api/health` (file deleted by Task 4; this edit keeps it consistent during the transition window)
- ~~`api/docker-compose.coolify.yml`~~ — **deleted by Task 1**; do not edit (Task 4 also assumes it's gone)
- `{WORKSPACE}/web/src/environments/environment.ts` — change `apiUrl` from absolute `http://localhost:3101/api` to relative `/api`
- `{WORKSPACE}/web/src/environments/environment.prod.ts` — verify/set `apiUrl: '/api'` (see Step 5)
- `{WORKSPACE}/web/angular.json` — add `"proxyConfig": "../proxy.conf.json"` to the `serve.options` stanza
- `{WORKSPACE}/api/tests/test_health.py` — update all 6 path literals `/health` → `/api/health`
- `{WORKSPACE}/api/tests/test_config_envvar.py` — update 4 `client.get("/health")` calls → `/api/health`
- `{WORKSPACE}/api/tests/test_contracts.py` — update `responseSchemaFor` path key and `mock_client.get` path from `/health` → `/api/health`
- `{WORKSPACE}/api/tests/test_openapi_spec.py` — update `REQUIRED_PATHS` list and parametrize tuple from `/health` → `/api/health`
- `{WORKSPACE}/api/tests/test_ai_rewrite.py` — remove the `and rule.rule != "/health"` special-case in `everyOpenapiPath_hasRouteHandler`
- `{WORKSPACE}/api/tests/test_deploy_config.py` — update healthcheck assertion from `"/health"` → `"/api/health"`
- `{WORKSPACE}/api/tests/test_retire_express.py` — invert two proxy structural tests: `proxyConfJson_doesNotExist` → `proxyConfJson_exists`; `angularJson_hasNoProxyConfigReference` → `angularJson_hasProxyConfigReference`
- `{WORKSPACE}/api/tests/test_structural.py` — remove `"web_serve"` entry from `SAAS_OPTIONAL`

### To Leave Alone
- `{WORKSPACE}/api/modules/observability/health.py` — already correct; routes are `/api/health/{anthropic,neon,stripe}` with `url_prefix="/api/health"`; no change needed
- `{WORKSPACE}/api/modules/*/routes.py` (all feature blueprints) — all already carry `/api/` in their individual `url_prefix`; this task does not change them
- `{WORKSPACE}/api/dtos/models.py` — generated; openapi.yaml path rename does not affect DTO schemas
- `{WORKSPACE}/api/tests/test_retire_express.py` route-reachability tests (lines 136-229) — those test feature routes under `/api/ai/text/*`; unaffected

---

## 4. Implementation Steps

### Step 1: Rename `/health` → `/api/health` and drop `web_serve_bp` in `create_app.py` + `openapi.yaml`

> **Note**: `everyOpenapiPath_hasRouteHandler` fails in the window between editing `openapi.yaml` and the matching Flask route change. Make both edits in this single step before committing or running `make test`.

**Action**: In `create_app.py`, (a) delete the `web_serve_bp` import, (b) rename the inline route decorator, (c) delete the `app.register_blueprint(web_serve_bp)` call and its comment. In `openapi.yaml`, rename the top-level path key.

**File**: `{WORKSPACE}/api/create_app.py`

**Pattern**:
```python
# REMOVE this import (line 13):
from modules.web_serve import web_serve_bp

# CHANGE route decorator (line 90):
@app.get('/health')          # before
@app.get('/api/health')      # after
def health():
    return jsonify({'status': 'ok'})

# REMOVE these two lines (lines 117-119):
# web_serve_bp registers the Angular catch-all `/<path:path>`. Must be LAST
# so it doesn't shadow `/api/*` or the routes above.
app.register_blueprint(web_serve_bp)
```

**File**: `{WORKSPACE}/api/openapi.yaml`

**Pattern**:
```yaml
paths:

  /api/health:          # was /health (line 20)
    get:
      summary: Health check
      operationId: getHealth
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from create_app import create_app; app = create_app({'TESTING': True}); rules = [r.rule for r in app.url_map.iter_rules()]; print('/api/health' in rules, '/health' not in rules)"
# expect: True True
grep -n "url_prefix" openapi.yaml || grep -n "^  /health:" openapi.yaml
# expect: no match (bare /health: gone)
grep -n "^  /api/health:" openapi.yaml
# expect: line 20 (or nearby)
```

---

### Step 2: Delete the `web_serve` module

**Action**: Remove the `modules/web_serve/` directory entirely. The blueprint is no longer imported; leaving dead code increases confusion in structural tests.

**File**: `{WORKSPACE}/api/modules/web_serve/` (delete)

**Pattern**:
```bash
rm -rf {WORKSPACE}/api/modules/web_serve/
```

**Verify**:
```bash
ls {WORKSPACE}/api/modules/web_serve/ 2>&1 | grep "No such file"
# expect: "No such file or directory"
python -c "import sys; sys.path.insert(0,'api'); from create_app import create_app; create_app({'TESTING':True})" 2>&1 | grep -i error
# expect: no output (app boots without web_serve_bp)
```

---

### Step 3: Update Docker healthcheck probe URL in `api/docker-compose.yml`

**Action**: Replace the bare `/health` URL with `/api/health` in `api/docker-compose.yml` only. (Task 1 deletes `api/docker-compose.coolify.yml`; the new root `docker-compose.yml` is created by Task 4 with `/api/health` already in place.)

**File**: `{WORKSPACE}/api/docker-compose.yml`

**Pattern**:
```yaml
healthcheck:
  test:
    - "CMD-SHELL"
    - >
      python -c "import urllib.request;
      urllib.request.urlopen('http://localhost:3101/api/health')"
      || exit 1
```

**Verify**:
```bash
grep -n "health" {WORKSPACE}/api/docker-compose.yml
# expect: shows /api/health; bare /health must not appear
```

**Note**: this edit keeps `api/docker-compose.yml` runnable in the window between Task 3 and Task 4. Task 4 deletes the file entirely.

---

### Step 4: Add `proxy.conf.json` at the workspace root

**Action**: Create the Angular dev-server proxy config so `apiUrl: '/api'` resolves to Flask `:3101` during `ng serve`. Place the file at the workspace root; `angular.json` will reference it with a relative path in Step 5.

**File**: `{WORKSPACE}/proxy.conf.json` (new)

**Pattern**:
```json
{
  "/api": {
    "target": "http://localhost:3101",
    "secure": false,
    "changeOrigin": false,
    "logLevel": "info"
  }
}
```

**Verify**:
```bash
python -c "import json; d = json.load(open('{WORKSPACE}/proxy.conf.json')); assert '/api' in d; assert d['/api']['target'] == 'http://localhost:3101'; print('ok')"
# expect: ok
```

---

### Step 5: Update Angular environment and register proxy in `angular.json`

**Action**: Set `apiUrl` to the relative string `'/api'` in both environment files. Then wire `proxy.conf.json` into the `serve` architect target in `angular.json`.

**File**: `{WORKSPACE}/web/src/environments/environment.ts`

**Pattern**:
```typescript
export const environment = {
  production: false,
  apiUrl: '/api',   // was 'http://localhost:3101/api'
  // ... other keys unchanged
};
```

**File**: `{WORKSPACE}/web/src/environments/environment.prod.ts` (if it exists)

**Pattern**:
```typescript
export const environment = {
  production: true,
  apiUrl: '/api',   // must match dev — nginx routes /api/* to Flask
  // ... other keys unchanged
};
```
If `environment.prod.ts` does not exist, `environment.ts` is used for all builds — no action required for that file.

**File**: `{WORKSPACE}/web/angular.json`

Locate the `projects.spec-doc.architect.serve.options` object (the path is `projects → spec-doc → architect → serve → options`) and add `proxyConfig`:

**Pattern**:
```json
"serve": {
  "builder": "@angular-devkit/build-angular:dev-server",
  "options": {
    "proxyConfig": "../proxy.conf.json"
  }
}
```
> `"../proxy.conf.json"` is relative from the `web/` directory to the workspace root where the file was created in Step 4.

**Verify**:
```bash
node -e "
const a = require('{WORKSPACE}/web/angular.json');
const opts = a.projects?.['spec-doc']?.architect?.serve?.options ?? {};
console.assert(opts.proxyConfig === '../proxy.conf.json', 'proxyConfig missing');
console.log('proxyConfig:', opts.proxyConfig);
"
# expect: proxyConfig: ../proxy.conf.json

grep 'apiUrl' {WORKSPACE}/web/src/environments/environment.ts
# expect: apiUrl: '/api'
```

---

### Step 6: Update `test_health.py` and `test_config_envvar.py`

**Action**: Replace every bare `/health` path literal with `/api/health`.

**File**: `{WORKSPACE}/api/tests/test_health.py`

All six occurrences of `client.get('/health')` become `client.get('/api/health')`. Full updated file:

```python
def healthEndpoint_returns200(client):
    response = client.get('/api/health')
    assert response.status_code == 200

def healthEndpoint_returnsStatusOk(client):
    response = client.get('/api/health')
    data = response.get_json()
    assert data == {'status': 'ok'}, f'expected {{"status": "ok"}}, got {data}'

def healthEndpoint_returnsJsonContentType(client):
    response = client.get('/api/health')
    assert 'application/json' in response.content_type

def angularOrigin_corsHeaderPresent(client):
    response = client.get('/api/health', headers={'Origin': 'http://localhost:4201'})
    assert 'Access-Control-Allow-Origin' in response.headers, \
        'CORS header missing — flask-cors may not be applied at factory level'

def angularOrigin_corsAllowsExactOrigin(client):
    response = client.get('/api/health', headers={'Origin': 'http://localhost:4201'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao == 'http://localhost:4201', \
        f'expected "http://localhost:4201", got "{acao}"'

def unknownOrigin_corsNotReflected(client):
    response = client.get('/api/health', headers={'Origin': 'http://evil.example.com'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao != 'http://evil.example.com', \
        'Flask must not reflect arbitrary origins'

def createApp_projectsBlueprintRegistered(app):
    assert 'projects' in app.blueprints, \
        'projects Blueprint not registered — check ENABLED_MODULES in create_app.py'

def createApp_contextBlueprintRegistered(app):
    assert 'context' in app.blueprints, \
        'context Blueprint not registered — check ENABLED_MODULES in create_app.py'

def createApp_aiBlueprintRegistered(app):
    assert 'ai' in app.blueprints, \
        'ai Blueprint not registered — check ENABLED_MODULES in create_app.py'

def createApp_allThreeBlueprintsRegistered(app):
    registered = set(app.blueprints.keys())
    assert {'projects', 'context', 'ai'}.issubset(registered), \
        f'expected projects + context + ai, got {registered}'
```

**File**: `{WORKSPACE}/api/tests/test_config_envvar.py`

Replace `"/health"` with `"/api/health"` at lines 16, 29, 42, and 43:

```python
resp = client.get("/api/health", headers={"Origin": "http://localhost:4201"})
# ...
resp = client.get("/api/health", headers={"Origin": "http://staging.example.com"})
# ...
resp1 = client.get("/api/health", headers={"Origin": "http://localhost:4201"})
resp2 = client.get("/api/health", headers={"Origin": "http://localhost:4202"})
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -m pytest tests/test_health.py tests/test_config_envvar.py -v --tb=short
# expect: all tests pass; zero failures
```

---

### Step 7: Update `test_contracts.py`, `test_openapi_spec.py`, `test_ai_rewrite.py`, and `test_deploy_config.py`

**Action**: Update every remaining `/health` string in test infrastructure to `/api/health`, and simplify the `everyOpenapiPath_hasRouteHandler` filter which had a special-case exemption for the now-gone bare `/health` route.

**File**: `{WORKSPACE}/api/tests/test_contracts.py` (lines 256–260)

```python
def test_health_matchesOpenApiSchema(self, mock_client, spec):
    schema = responseSchemaFor(spec, "/api/health", "get", "200")  # was /health
    resp = mock_client.get("/api/health")                           # was /health
    assert resp.status_code == 200
    jsonschema.validate(resp.get_json(), schema)
```

**File**: `{WORKSPACE}/api/tests/test_openapi_spec.py` (lines 61–80)

```python
REQUIRED_PATHS = [
    "/api/health",              # was /health
    "/api/projects",
    "/api/projects/{id}",
    "/api/projects/{id}/files/{filename}",
    "/api/context/{key}",
]

@pytest.mark.parametrize("path,method", [
    ("/api/health", "get"),     # was ("/health", "get")
    ("/api/projects", "get"),
    ("/api/projects", "post"),
    ("/api/projects/{id}", "get"),
    ("/api/projects/{id}", "delete"),
    ("/api/projects/{id}/files/{filename}", "put"),
    ("/api/context/{key}", "get"),
    ("/api/context/{key}", "put"),
])
```

**File**: `{WORKSPACE}/api/tests/test_ai_rewrite.py` (line 305)

Remove the bare-`/health` special case — every route tracked by this test now starts with `/api`:

```python
# BEFORE:
if not rule.rule.startswith("/api") and rule.rule != "/health":
    continue
# AFTER:
if not rule.rule.startswith("/api"):
    continue
```

**File**: `{WORKSPACE}/api/tests/test_deploy_config.py` (line 104)

```python
assert "/api/health" in test_cmd, (          # was "/health"
    f"healthcheck 'test' command must probe the /api/health endpoint; got: {test_cmd!r}"
)
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -m pytest tests/test_contracts.py tests/test_openapi_spec.py \
  tests/test_ai_rewrite.py tests/test_deploy_config.py -v --tb=short
# expect: all pass; zero failures
```

---

### Step 8: Invert proxy structural tests in `test_retire_express.py`

**Action**: The two tests that asserted `proxy.conf.json` and `proxyConfig` must be absent now assert the opposite — both must be present as part of the nginx-alignment architecture.

**File**: `{WORKSPACE}/api/tests/test_retire_express.py` (replace functions `proxyConfJson_doesNotExist` and `angularJson_hasNoProxyConfigReference`)

```python
def proxyConfJson_exists():
    """proxy.conf.json must exist at the workspace root.

    Task 3 (Flask /api/ prefix + Angular env alignment) re-introduces this file
    to forward /api/* from the Angular dev server (:4201) to Flask (:3101).
    Its absence indicates a regression; the file must be committed at the
    workspace root alongside angular.json.
    """
    proxy_path = REPO_ROOT / "proxy.conf.json"
    assert proxy_path.exists(), (
        f"proxy.conf.json must exist at {proxy_path}. "
        f"Task 3 creates it to proxy /api/* to Flask in dev. "
        f"Run: cp the proxy.conf.json created in Task 3 to the workspace root."
    )
    import json
    content = json.loads(proxy_path.read_text())
    assert "/api" in content, (
        f"proxy.conf.json must contain a '/api' key targeting Flask; got keys: {list(content)}"
    )
    assert content["/api"].get("target", "").startswith("http://localhost:"), (
        f"proxy /api target must be a localhost URL; got: {content['/api'].get('target')!r}"
    )


def angularJson_hasProxyConfigReference():
    """angular.json serve.options must reference proxy.conf.json after Task 3.

    Task 3 adds proxyConfig so ng serve forwards /api/* to Flask. Its absence
    means the Angular dev server won't proxy API calls and local development
    will hit CORS errors or 404s.
    """
    if not (WEB_ROOT / "angular.json").exists():
        pytest.skip(f"angular.json not found at {WEB_ROOT} (CI stub)")
    angular_json = json.loads((WEB_ROOT / "angular.json").read_text())
    serve_opts = (
        angular_json.get("projects", {})
        .get("spec-doc", {})
        .get("architect", {})
        .get("serve", {})
        .get("options", {})
    )
    assert "proxyConfig" in serve_opts, (
        f"angular.json serve.options must contain 'proxyConfig' pointing to proxy.conf.json. "
        f"Task 3 adds this key; its absence means ng serve won't proxy /api/* to Flask. "
        f"Got options: {serve_opts}"
    )
    assert "proxy.conf.json" in serve_opts["proxyConfig"], (
        f"proxyConfig must reference proxy.conf.json; got: {serve_opts['proxyConfig']!r}"
    )
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -m pytest tests/test_retire_express.py -v --tb=short
# expect: proxy structural tests pass (proxyConfJson_exists, angularJson_hasProxyConfigReference)
# route-reachability tests (iterate, lintBraindump, review, generateSpec) unchanged — still pass
```

---

### Step 9: Remove `web_serve` from `SAAS_OPTIONAL` in `test_structural.py`

**Action**: Now that `modules/web_serve/` has been deleted, remove its entry from the structural allowlist. Leaving a ghost entry is harmless to the test (it's an allowlist, not a checklist) but misleads future readers.

**File**: `{WORKSPACE}/api/tests/test_structural.py` (around line 197)

```python
SAAS_OPTIONAL = {
    "auth",           # planned: Neon auth wrapper
    "billing",        # planned: Stripe / RevenueCat adapter
    "usage",          # planned: per-user quota + rate-limit service
    "observability",  # planned: structured logging + health aggregation
    # "web_serve" removed — Task 3: module deleted; nginx now owns static serving
}
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -m pytest tests/test_structural.py -v --tb=short
# expect: all structural tests pass; packages_areInExpectedHierarchy passes (web_serve not in actual)
```

---

## 5. Tests

All tests are in pytest format matching the repo convention. Complete assertion bodies below; none are stubs.

```python
# tests/test_health.py — full replacement (Step 6)

def healthEndpoint_returns200(client):
    response = client.get('/api/health')
    assert response.status_code == 200

def healthEndpoint_returnsStatusOk(client):
    response = client.get('/api/health')
    data = response.get_json()
    assert data == {'status': 'ok'}, f'expected {{"status": "ok"}}, got {data}'

def healthEndpoint_returnsJsonContentType(client):
    response = client.get('/api/health')
    assert 'application/json' in response.content_type

def angularOrigin_corsHeaderPresent(client):
    response = client.get('/api/health', headers={'Origin': 'http://localhost:4201'})
    assert 'Access-Control-Allow-Origin' in response.headers, \
        'CORS header missing — flask-cors may not be applied at factory level'

def angularOrigin_corsAllowsExactOrigin(client):
    response = client.get('/api/health', headers={'Origin': 'http://localhost:4201'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao == 'http://localhost:4201', \
        f'expected "http://localhost:4201", got "{acao}"'

def unknownOrigin_corsNotReflected(client):
    response = client.get('/api/health', headers={'Origin': 'http://evil.example.com'})
    acao = response.headers.get('Access-Control-Allow-Origin', '')
    assert acao != 'http://evil.example.com', \
        'Flask must not reflect arbitrary origins'
```

```python
# tests/test_retire_express.py — replacement proxy structural functions (Step 8)

def proxyConfJson_exists():
    proxy_path = REPO_ROOT / "proxy.conf.json"
    assert proxy_path.exists(), (
        f"proxy.conf.json must exist at {proxy_path}. "
        f"Task 3 creates it to proxy /api/* to Flask in dev."
    )
    content = json.loads(proxy_path.read_text())
    assert "/api" in content, (
        f"proxy.conf.json must contain a '/api' key; got keys: {list(content)}"
    )
    assert content["/api"].get("target", "").startswith("http://localhost:"), (
        f"proxy /api target must be a localhost URL; got: {content['/api'].get('target')!r}"
    )


def angularJson_hasProxyConfigReference():
    if not (WEB_ROOT / "angular.json").exists():
        pytest.skip(f"angular.json not found at {WEB_ROOT} (CI stub)")
    angular_json = json.loads((WEB_ROOT / "angular.json").read_text())
    serve_opts = (
        angular_json.get("projects", {})
        .get("spec-doc", {})
        .get("architect", {})
        .get("serve", {})
        .get("options", {})
    )
    assert "proxyConfig" in serve_opts, (
        f"angular.json serve.options must contain 'proxyConfig'. Got options: {serve_opts}"
    )
    assert "proxy.conf.json" in serve_opts["proxyConfig"], (
        f"proxyConfig must reference proxy.conf.json; got: {serve_opts['proxyConfig']!r}"
    )
```

---

## 6. Commit Plan

**Executor instruction**: run each commit command immediately after completing the corresponding step — not at the end of the task.

1. `fix(api): rename /health to /api/health; drop web_serve_bp` — after Steps 1–2 — files: `api/create_app.py`, `api/openapi.yaml`, `api/modules/web_serve/` (deleted)

```bash
cd {WORKSPACE}
git add api/create_app.py api/openapi.yaml
git rm -r api/modules/web_serve/
git commit -m "$(cat <<'EOF'
fix(api): rename /health to /api/health; drop web_serve_bp

Every route now lives under /api/* — the bare /health special-case is gone.
web_serve_bp removed; nginx owns static serving from Task 4 onward.
Resolves everyOpenapiPath_hasRouteHandler drift between openapi.yaml and Flask map.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

2. `fix(docker): update healthcheck probe to /api/health` — after Step 3 — files: `api/docker-compose.yml`

```bash
git add api/docker-compose.yml
git commit -m "$(cat <<'EOF'
fix(docker): update healthcheck probe to /api/health

api/docker-compose.yml now probes /api/health to match the renamed Flask route.
Task 4 will replace this file with the root two-service compose.
Update Coolify dashboard external probe manually if configured.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

3. `feat(web): relative /api base URL + ng serve dev proxy` — after Steps 4–5 — files: `proxy.conf.json`, `web/src/environments/environment.ts`, `web/src/environments/environment.prod.ts` (if changed), `web/angular.json`

```bash
git add proxy.conf.json web/src/environments/environment.ts web/angular.json
# add environment.prod.ts if it was changed:
# git add web/src/environments/environment.prod.ts
git commit -m "$(cat <<'EOF'
feat(web): relative /api base URL + ng serve dev proxy

environment.ts: apiUrl 'http://localhost:3101/api' → '/api'
proxy.conf.json: forward /api/* to Flask :3101 in ng serve
angular.json: wire proxyConfig so ng serve picks up the proxy

Dev and prod now resolve the same relative /api paths; no env branching.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

4. `test: update /health→/api/health in all test fixtures` — after Steps 6–7 — files: `api/tests/test_health.py`, `api/tests/test_config_envvar.py`, `api/tests/test_contracts.py`, `api/tests/test_openapi_spec.py`, `api/tests/test_ai_rewrite.py`, `api/tests/test_deploy_config.py`

```bash
git add api/tests/test_health.py api/tests/test_config_envvar.py \
  api/tests/test_contracts.py api/tests/test_openapi_spec.py \
  api/tests/test_ai_rewrite.py api/tests/test_deploy_config.py
git commit -m "$(cat <<'EOF'
test: update /health→/api/health in test fixtures

All 6 test files that hard-coded the bare /health path now use /api/health.
everyOpenapiPath_hasRouteHandler filter simplified — no /health special-case needed.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

5. `test(retire): reflect proxy.conf.json presence post Task 3` — after Step 8 — files: `api/tests/test_retire_express.py`

```bash
git add api/tests/test_retire_express.py
git commit -m "$(cat <<'EOF'
test(retire): reflect proxy.conf.json presence post Task 3

proxyConfJson_doesNotExist → proxyConfJson_exists (asserts target + key)
angularJson_hasNoProxyConfigReference → angularJson_hasProxyConfigReference

These tests previously encoded the Express-retirement no-proxy state.
Task 3 re-introduces proxy.conf.json for the nginx-alignment architecture.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

6. `test(structural): remove web_serve from module allowlist` — after Step 9 — files: `api/tests/test_structural.py`

```bash
git add api/tests/test_structural.py
git commit -m "$(cat <<'EOF'
test(structural): remove web_serve from module allowlist

modules/web_serve/ deleted in this task; remove its entry from SAAS_OPTIONAL
so the allowlist reflects actual shipped modules.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Deviation logging**: if any step deviates from this guide, prefix that commit's body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api
python -m pytest --tb=short -q
```

**Expected delta**: 624 → 624 passing (net zero — tests updated in-place, no new tests added), 1 skipped (web-root CI check). Zero pre-existing tests broken.

**Spot-check the renamed route is live**:
```bash
cd {WORKSPACE}/api
python -c "
from create_app import create_app
app = create_app({'TESTING': True})
c = app.test_client()
r = c.get('/api/health')
assert r.status_code == 200 and r.get_json() == {'status': 'ok'}, r.data
r404 = c.get('/health')
assert r404.status_code == 404, f'bare /health must be 404, got {r404.status_code}'
print('ok')
"
# expect: ok
```

**Smoke-check Angular proxy is wired** (requires running processes):
```bash
# Terminal 1:
cd {WORKSPACE}/api && make dev          # Flask on :3101

# Terminal 2:
cd {WORKSPACE}/web && ng serve          # should pick up proxyConfig from angular.json

# Terminal 3:
curl -s http://localhost:4201/api/health | python -m json.tool
# expect: {"status": "ok"}
```

---

## 8. Rollback

- **Per-step**: every step above corresponds to exactly one commit. Any step can be independently reverted:
  ```bash
  git revert <sha>   # creates a new revert commit — safe on a branch
  ```
- **Per-branch**: if verification fails catastrophically and the branch is unusable:
  ```bash
  git reset --hard <pre-task-sha>   # wipes all commits on this branch since task start
  # or simply delete the branch:
  git checkout master && git branch -D task/3-api-prefix-angular-env
  ```
- **External state**: `proxy.conf.json` at the workspace root is created in Step 4. A rollback of that commit removes it. `angular.json`'s `proxyConfig` key is removed by reverting commit 3.

---

## 9. Deviations Allowed

- **`environment.ts` line differs from `apiUrl: 'http://localhost:3101/api'`** → read the actual value, make the minimal change to `apiUrl: '/api'`, note actual line in commit body.
- **`environment.prod.ts` not found** → skip that file; `environment.ts` covers all builds. Note absence in commit body for commit 3.
- **`angular.json` project key is not `spec-doc`** → locate the actual project key (`Object.keys(angular_json.projects)[0]`), use that key, log deviation.
- **`proxy.conf.json` already exists at workspace root with different content** → update the `/api` block to match Step 4's pattern; do not erase other keys. Log deviation.
- **`web_serve` absent from `modules/`** → Step 2 is a no-op; skip `git rm`, log deviation; still remove the import and registration lines from `create_app.py`.
- **Step N simplification unlocks Step N+1** → take it, log deviation in that commit body.
- **Side-effect required** (push, publish, Coolify config change) → STOP, mark `[REQUIRES APPROVAL]`, do not proceed until approved.

---

## 10. Out of Scope

This task covers only the route-prefix alignment, Angular env switch, proxy wiring, and the module deletion that makes nginx ownership coherent. It explicitly does not include the nginx configuration itself, the Dockerfile multi-stage restructure, or any CORS origin changes — those land in Task 4.

- **`/specs/<path:filename>` bare route in `create_app.py`** (line 104) — this file-serving route also lacks the `/api/` prefix. Renaming it was considered but deferred: it is a utility endpoint not declared in `openapi.yaml`, not consumed by Angular, and not covered by `everyOpenapiPath_hasRouteHandler`. It needs a separate decision on whether it should live under `/api/specs/` or be absorbed into a static-files layer in Task 4.
- **Nginx config (`nginx.conf`)** — Task 4 owns this. The proxy config created here (`proxy.conf.json`) is the dev-only forward; nginx is the prod-only layer.
- **Dockerfile multi-stage Angular build** — still builds the Angular dist into `api/web/`; the Dockerfile does not need to change now that `web_serve_bp` is gone since the `web/` directory copy can be cleaned up in Task 4 when nginx takes over.
- **CORS origin changes** — `CORS_ORIGINS` env var and allowed origins are unchanged. Task 4 may add the production domain.
- **Coolify external uptime-monitor reconfiguration** — flagged as a Gate above. This is a live-system change requiring dashboard access and must be handled as a deploy-day action by the operator, not as a code commit.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)