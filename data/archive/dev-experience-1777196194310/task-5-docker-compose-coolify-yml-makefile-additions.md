# Task 5: docker-compose.coolify.yml + Makefile Additions

**Purpose**: Ship the production Coolify compose file and five `make docker-*` targets that complete the container workflow, closing the gap between "the image builds" and "Coolify can deploy it."

**Effort**: 0.25 days

**Dependencies**: Dockerfile exists and builds successfully; `/health` route registered in `create_app.py`; `docker-compose.yml` (local/CI target) already committed; existing Makefile has `dev`, `test`, `generate-dtos`, `check-dtos` targets.

**Parallel With**: GitHub Actions pipeline authoring (no file overlap)

**Blocks**: Coolify service configuration; production deploy via webhook

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task produces the two files that complete the developer container interface: `docker-compose.coolify.yml`, which Coolify reads verbatim on every deploy, and five Makefile targets that wrap `docker compose` commands behind the `make` interface developers already use. The compose file encodes the Traefik routing labels for `api.spec-doc.${DOMAIN}`, the Let's Encrypt certresolver, the hardcoded `FLASK_DEBUG=0` production guard, and the `spec-doc-data` named volume — the explicit data contract between the API and its project files in production. Without these two files, Coolify has no routing configuration to read and the container workflow has no `make` surface, forcing developers to remember raw compose syntax and leaving the production data relationship as an undocumented filesystem assumption.

**Trade-offs considered:**
- **Single `docker-compose.yml` with Compose profiles** — rejected because profile-based overrides make the production configuration non-auditable; a side-by-side diff of `docker-compose.yml` vs `docker-compose.coolify.yml` is the safest production change review surface and matches the architecture's "explicit over implicit" principle.
- **Hardcoded domain in the compose file** — rejected because it couples the file to a specific deployment and prevents it from being committed before the domain is finalized; a hardcoded value must be edited before every environment change.
- **`${DOMAIN}` env substitution in the Traefik `Host()` rule** — preferred because Coolify injects environment variables at deploy time, the file is committable before the domain is confirmed, and the substitution point is visible in the file rather than implicit in a Coolify UI field.

> **[REQUIRES APPROVAL — domain strategy]**: This guide uses `${DOMAIN}` substitution so the Traefik label reads `Host(\`api.spec-doc.${DOMAIN}\`)`. If the team has chosen a hardcoded domain or a different substitution strategy, resolve that decision before Step 1. Do not proceed past pre-flight until this is confirmed.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm working tree state
git status

# Confirm target files are clean (neither should exist yet)
git diff HEAD -- docker-compose.coolify.yml Makefile

# Confirm the Dockerfile and docker-compose.yml exist (prerequisites)
ls docker-compose.yml Dockerfile

# Confirm the /health route is registered
grep -n "health" create_app.py

# Record baseline test count
make test 2>&1 | tail -5
```

**If working tree is dirty on `Makefile`**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: 192 / 192 passing.

---

## 3. Files

### To Create (new)
- `docker-compose.coolify.yml` — production Coolify compose file; Traefik labels, named volume, hardcoded `FLASK_DEBUG=0`; depends on `Dockerfile` in the same directory
- `tests/test_deploy_config.py` — structural tests for compose file contents and Makefile target presence; uses the repo's `pytest` framework

### To Modify (cite CODEBASE CONTEXT)
- `Makefile` — current state: `dev`, `test`, `generate-dtos`, `check-dtos` targets (per `spec-doc/api/CLAUDE.md`); target state: five additional `docker-*` targets appended after existing targets

### To Leave Alone
- `docker-compose.yml` — local/CI target; no changes; the coolify file is a separate artifact, not an extension
- `Dockerfile` — prerequisite artifact; this task adds no image changes
- `create_app.py` — `/health` route already registered; this task has no route work
- `dtos/models.py` — generated file; never hand-edit (per `spec-doc/api/CLAUDE.md`)
- `openapi.yaml` — no new endpoints in this task

---

## 4. Implementation Steps

### Step 1: Create docker-compose.coolify.yml

**Action**: Create the production Coolify compose file. Hardcode `FLASK_DEBUG=0`. Use `${DOMAIN}` substitution in the Traefik `Host()` rule. Declare the `spec-doc-data` named volume at both the service level and the top-level `volumes:` block. Omit `ports:` — Traefik routes internally via container network. Do not include `version:` key (Compose v2 CLI ignores it; omitting avoids deprecation warnings in CI).

**File**: `docker-compose.coolify.yml` (new)

**Pattern**:
```yaml
services:
  api:
    build: .
    restart: unless-stopped
    environment:
      - FLASK_DEBUG=0
      - SPEC_DOC_DIR=/data/spec-doc
      - CORS_ORIGINS=${CORS_ORIGINS}
      - AI_PROVIDER=${AI_PROVIDER:-claude}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - spec-doc-data:/data/spec-doc
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3101/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 15s
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.spec-doc-api.rule=Host(`api.spec-doc.${DOMAIN}`)"
      - "traefik.http.routers.spec-doc-api.entrypoints=websecure"
      - "traefik.http.routers.spec-doc-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.spec-doc-api.loadbalancer.server.port=3101"

volumes:
  spec-doc-data:
```

**Verify**:
```bash
docker compose -f docker-compose.coolify.yml config --quiet
```
Expect: no output and exit code 0. If `${DOMAIN}` is unset, `docker compose config` may warn about variable substitution — this is expected and acceptable; the warning does not indicate a malformed file.

---

### Step 2: Add five Makefile targets

**Action**: Append five targets to the existing `Makefile` after the last existing target. Each target uses `-f docker-compose.yml` (local dev compose — the coolify file is not used locally). `docker-smoke` polls `/health` before asserting, matching the CI smoke job signal.

**File**: `Makefile` (modify — current targets: `dev`, `test`, `generate-dtos`, `check-dtos` per `spec-doc/api/CLAUDE.md`)

**Pattern** — append after existing targets:
```makefile
docker-build: ## Build the API container image
	docker compose -f docker-compose.yml build

docker-up: ## Start the API container in the background
	docker compose -f docker-compose.yml up -d

docker-down: ## Stop and remove the API container
	docker compose -f docker-compose.yml down

docker-logs: ## Tail API container logs
	docker compose -f docker-compose.yml logs -f api

docker-smoke: ## Smoke test the running container (run after docker-up)
	@echo "Polling /health (15 attempts, 2s interval)..."
	@for i in $$(seq 1 15); do \
		curl -sf http://localhost:3101/health > /dev/null 2>&1 && break; \
		echo "  attempt $$i/15..."; \
		sleep 2; \
		[ $$i -eq 15 ] && echo "ERROR: /health did not respond" && exit 1; \
	done
	@curl -sf http://localhost:3101/health
	@curl -sf http://localhost:3101/api/projects > /dev/null
	@echo "Smoke test passed."
```

**Verify**:
```bash
# Confirm all five targets are now parseable
make --dry-run docker-build
make --dry-run docker-up
make --dry-run docker-down
make --dry-run docker-logs
make --dry-run docker-smoke
```
Expect: each prints the command it would run and exits 0. No "No rule to make target" errors.

---

### Step 3: Add structural tests

**Action**: Create `tests/test_deploy_config.py` with six pytest tests. Tests assert the compose file's structure and the Makefile target inventory — they do not start containers. Uses only `pathlib`, `yaml`, and `re` from the standard library plus `pytest`; no new dependencies.

**File**: `tests/test_deploy_config.py` (new)

**Pattern**:
```python
import re
import pathlib
import yaml
import pytest

WORKSPACE = pathlib.Path(__file__).parent.parent  # resolves to spec-doc/api/

# ── compose file tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def coolify_doc():
    path = WORKSPACE / "docker-compose.coolify.yml"
    with open(path) as f:
        return yaml.safe_load(f)

def test_coolify_compose_is_valid_yaml(coolify_doc):
    ...  # full body below in §5 Tests

# ... (see §5 for complete bodies)
```

**Verify**:
```bash
python -m pytest tests/test_deploy_config.py -v
```
Expect: 6 passed, 0 failed, 0 errors.

---

## 5. Tests

File: `tests/test_deploy_config.py` (new). Framework: `pytest` (matches repo — `make test` runs `pytest`, 192 tests per `spec-doc/api/CLAUDE.md`). Dependencies: `pyyaml` (already in `requirements.txt` — used by existing DTO tooling).

```python
import re
import pathlib
import yaml
import pytest

WORKSPACE = pathlib.Path(__file__).parent.parent  # spec-doc/api/


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def coolify_doc():
    path = WORKSPACE / "docker-compose.coolify.yml"
    assert path.exists(), f"docker-compose.coolify.yml not found at {path}"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def makefile_content():
    path = WORKSPACE / "Makefile"
    assert path.exists(), f"Makefile not found at {path}"
    with open(path) as f:
        return f.read()


# ── compose file tests ────────────────────────────────────────────────────────

def test_coolify_compose_is_valid_yaml(coolify_doc):
    assert coolify_doc is not None, (
        "docker-compose.coolify.yml parsed as empty — file must contain a valid "
        "Compose document with at least a 'services' key"
    )
    assert "services" in coolify_doc, (
        "Top-level 'services' key missing from docker-compose.coolify.yml"
    )


def test_coolify_compose_has_traefik_labels(coolify_doc):
    labels = coolify_doc["services"]["api"].get("labels", [])
    assert labels, "api service must define at least one label"

    label_blob = " ".join(labels)

    assert "traefik.enable=true" in label_blob, (
        "Traefik must be enabled via 'traefik.enable=true' label"
    )
    assert "websecure" in label_blob, (
        "Traefik entrypoint must be 'websecure' (HTTPS) — found labels: " + label_blob
    )
    assert "letsencrypt" in label_blob, (
        "Traefik certresolver must reference 'letsencrypt' — found labels: " + label_blob
    )
    assert "3101" in label_blob, (
        "Traefik loadbalancer must target internal port 3101 — found labels: " + label_blob
    )


def test_coolify_compose_flask_debug_hardcoded_off(coolify_doc):
    env = coolify_doc["services"]["api"].get("environment", [])

    # Compose environment may be a list ["KEY=VAL", ...] or a dict {KEY: VAL}
    if isinstance(env, list):
        env_dict = {}
        for entry in env:
            if "=" in str(entry):
                k, v = str(entry).split("=", 1)
                env_dict[k] = v
    else:
        env_dict = {str(k): str(v) for k, v in env.items()}

    assert "FLASK_DEBUG" in env_dict, (
        "FLASK_DEBUG must be explicitly set in the production compose environment; "
        "omitting it risks defaulting to a debug-enabled image"
    )
    assert env_dict["FLASK_DEBUG"] == "0", (
        f"FLASK_DEBUG must be hardcoded to '0' in docker-compose.coolify.yml; "
        f"got '{env_dict['FLASK_DEBUG']}' — this value must not be an env var reference"
    )


def test_coolify_compose_named_volume_defined(coolify_doc):
    top_level_volumes = coolify_doc.get("volumes", {})
    assert "spec-doc-data" in top_level_volumes, (
        "Named volume 'spec-doc-data' must be declared at the top-level 'volumes:' key "
        "so Coolify creates it on first deploy"
    )

    service_volumes = coolify_doc["services"]["api"].get("volumes", [])
    mounted_names = [str(v).split(":")[0] for v in service_volumes]
    assert "spec-doc-data" in mounted_names, (
        "Named volume 'spec-doc-data' must be mounted in the api service; "
        f"found service volume sources: {mounted_names}"
    )


def test_coolify_compose_healthcheck_present(coolify_doc):
    healthcheck = coolify_doc["services"]["api"].get("healthcheck")
    assert healthcheck is not None, (
        "api service must define a 'healthcheck' stanza — "
        "Coolify and the CI smoke job both rely on it for liveness verification"
    )
    test_cmd = " ".join(str(part) for part in healthcheck.get("test", []))
    assert "/health" in test_cmd, (
        f"healthcheck 'test' command must probe the /health endpoint; got: {test_cmd!r}"
    )


# ── Makefile tests ────────────────────────────────────────────────────────────

def test_makefile_docker_targets_exist(makefile_content):
    required_targets = [
        "docker-build",
        "docker-up",
        "docker-down",
        "docker-logs",
        "docker-smoke",
    ]
    for target in required_targets:
        assert re.search(rf"^{re.escape(target)}:", makefile_content, re.MULTILINE), (
            f"Makefile must define target '{target}:' — "
            "all five docker-* targets are required by the architecture"
        )
```

---

## 6. Commit Plan

**Executor instruction**: run each `git commit` immediately after the corresponding step completes — not at the end of the task.

1. `chore(deploy): add docker-compose.coolify.yml` — after Step 1 — `docker-compose.coolify.yml`: production Traefik labels, named volume, FLASK_DEBUG=0
2. `chore(make): add docker-build/up/down/logs/smoke targets` — after Step 2 — `Makefile`: five new targets appended
3. `test(deploy): structural tests for compose config and Makefile targets` — after Step 3 tests pass — `tests/test_deploy_config.py`: 6 new tests

**Commit command template**:
```bash
git add <specific-files>
git commit -m "$(cat <<'EOF'
<message from above>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation before the `Co-Authored-By` line.

---

## 7. Verification

```bash
make test
```

**Expected delta**: 192 → 198 passing. Zero pre-existing tests broken.

```bash
# Optional end-to-end local container smoke (not part of make test)
make docker-build
make docker-up
make docker-smoke
make docker-down
```

Expect `docker-smoke` to print `Smoke test passed.` and exit 0.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # creates a new revert commit; does not rewrite history
  ```
- **Per-branch**: if verification fails catastrophically after all three commits, reset to the pre-task SHA:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destructive, discards all task commits
  ```
  Alternatively, delete the feature branch and re-open from the merge base.

---

## 9. Deviations Allowed

- **`docker-compose.coolify.yml` already exists** — compare its content against Step 1's pattern; if substantially different, flag it and do not overwrite without confirmation.
- **`pyyaml` not in `requirements.txt`** — add it there before committing `tests/test_deploy_config.py`; log this addition in the commit body. Do not use a separate `requirements-test.txt` without team approval.
- **Test framework is not bare `pytest`** (e.g., uses `pytest-flask` fixtures) — the new test file uses no Flask fixtures; no adaptation needed, but verify `WORKSPACE` path resolution matches the repo's `conftest.py` if one exists.
- **Coolify uses a different Traefik label schema** (e.g., `v2` vs `v3` label format) — stop, document the mismatch, and mark [REQUIRES APPROVAL] before adjusting labels.
- **`make --dry-run` is not available** on the executor's Make version — substitute `grep -n "docker-build:" Makefile` to verify target existence; log the substitution.

---

## 10. Out of Scope

This task ships exactly two files: the production compose file and the Makefile additions. It does not configure Coolify, modify the image, add pipeline jobs, or touch the data volume's contents. An eager executor might be tempted to wire up the Coolify service definition, add a `docker-compose.coolify.yml` lint step to CI, or validate that `spec-doc-data` is populated — all of those are out of scope here and belong to distinct tasks.

- **Coolify service UI configuration** (entering the compose file path, setting `DOMAIN`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY`) — deferred; requires access to the Coolify instance and the confirmed production domain; done after this task merges
- **`COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` GitHub Secrets provisioning** — deferred to the pipeline task; those secrets have no consumer until the deploy job exists
- **`spec-doc-live` worktree removal** — explicitly deferred in the architecture ("deferred until the container is proven stable in production"); do not touch it here
- **Gevent worker class migration** — deferred by architectural decision; gthread ships first
- **Staging environment compose file** — deferred; no second-environment trigger exists

**Rule for the executor**: if a change appears helpful but is listed here, stop and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale (Traefik vs. nginx, named volume contract, gthread decision)
- [Epic](./epic.md) – Task scope and sequencing
- [Timeline](./timeline.md) – Update status to ✅ after verification passes