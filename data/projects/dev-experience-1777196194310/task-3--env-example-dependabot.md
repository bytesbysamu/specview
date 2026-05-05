# Task 3: .env.example + Dependabot — Implementation Guide

---

## 1. Context

This task makes the environment contract for spec-doc-api explicit and self-documenting. `.env.example` enumerates every variable the application reads — Flask flags, data path, CORS origins, AI provider selection, and API keys — with safe local defaults and commented-out secrets. Dependabot ships alongside CI/CD rather than after, because the interval between "pipeline exists" and "dependency updates are automated" is when supply-chain drift silently accumulates. Both files are infrastructure declarations only; no application code is modified.

**Trade-offs considered:**
- **CLAUDE.md env list as the sole source of truth** — rejected because CLAUDE.md may lag the actual code; grepping `os.getenv` / `os.environ` in pre-flight produces a ground-truth list the executor can cross-reference before writing the file.
- **Daily Dependabot schedule** — rejected for a single-developer project; daily pip updates generate PR noise that degrades signal. Weekly is the standard default and sufficient for this workload.
- **Grep-and-document approach over runtime introspection** — preferred because there is no running server in CI at the time `.env.example` is written; static grep is zero-dependency and reproducible.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# 1. Flag any unrelated changes
git status

# 2. Confirm target files are clean (or absent — they likely don't exist yet)
git diff HEAD -- .env.example .github/dependabot.yml tests/test_env_example.py

# 3. Discover every env var the application actually reads — this is your source of truth
grep -rn "os\.getenv\|os\.environ" . \
  --include="*.py" \
  --exclude-dir=__pycache__ \
  --exclude-dir=.git \
  --exclude-dir=.venv

# 4. Record baseline test count
make test
```

**If working tree is dirty on target files:** stash or commit unrelated changes before starting.

**Baseline recorded:** 192 / 192 passing (per `spec-doc/api/CLAUDE.md`).

> **Executor note on Step 3:** The grep output is ground truth. Cross-reference it against the variable list in Step 2 below before writing `.env.example`. If the grep reveals additional variables not listed in this guide, include them and log the addition as a deviation in the commit body.

---

## 3. Files

### To Create (new)

| Path | Purpose |
|---|---|
| `.env.example` | Documents every env var the app reads; safe local defaults; secrets commented out |
| `.github/dependabot.yml` | Weekly pip dependency update schedule |
| `tests/test_env_example.py` | Structural pytest tests asserting completeness and secret hygiene |

### To Modify

*None. This task makes no application code changes.*

### To Leave Alone

| Path | Reason |
|---|---|
| `create_app.py` | App factory — no changes in scope |
| `modules/chain/adapter.py` | AI adapter boundary — no changes in scope |
| `openapi.yaml` | API contract — no changes in scope |
| `dtos/models.py` | Generated; never hand-edit |
| `.env` | Gitignored developer-local file; executor must not create, modify, or read it |
| `modules/ai/routes.py` | Feature routes — no changes in scope |
| `modules/ai/prompts/__init__.py` | Prompt functions — no changes in scope |

---

## 4. Implementation Steps

### Step 1: Audit source for all env var reads

**Action:** Run the grep from Pre-flight Step 3. For each `os.getenv(...)` or `os.environ.get(...)` call, record the variable name and its call-site default. This list drives `.env.example` completeness. Do not edit any file in this step.

**File:** N/A — read-only audit

**Pattern:**
```bash
# Expected output will include lines such as:
# modules/chain/adapter.py:  AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")
# create_app.py:             os.getenv("CORS_ORIGINS", "http://localhost:4201")
# create_app.py:             os.getenv("FLASK_DEBUG", "0")
# modules/context/service.py: os.getenv("SPEC_DOC_DIR")
```

**Verify:** The grep returns at least `AI_PROVIDER`, `SPEC_DOC_DIR`, `CORS_ORIGINS`. If any of the four confirmed variables from `spec-doc/api/CLAUDE.md` (`SPEC_DOC_DIR`, `CORS_ORIGINS`) are absent from grep output, check whether they are read via a different pattern (e.g., `app.config.from_envvar`) and record the finding in the Step 2 commit body.

---

### Step 2: Create `.env.example`

**Action:** Create `.env.example` at the repository root. Enumerate all variables discovered in Step 1. Apply safe local defaults. Comment out secrets with an explicit note that they live in GitHub Secrets only.

**File:** `.env.example` (new)

**Pattern:**
```bash
# ── Flask ──────────────────────────────────────────────────────────────
# App factory entrypoint. Flask discovers create_app() automatically.
FLASK_APP=create_app

# Set to 1 locally for auto-reload and detailed error pages.
# Hardcoded to 0 in docker-compose.coolify.yml — do not override in production.
FLASK_DEBUG=1

# ── Server ─────────────────────────────────────────────────────────────
PORT=3101

# ── Data ───────────────────────────────────────────────────────────────
# Absolute path to the sibling spec-doc/ repository on this machine.
# Example (macOS):  SPEC_DOC_DIR=/Users/<you>/Projects/spec-doc
# Container local:  set to /data/spec-doc via compose bind-mount; leave blank here.
SPEC_DOC_DIR=

# ── CORS ───────────────────────────────────────────────────────────────
# Comma-separated list of allowed origins.
# Local Angular dev servers run on 4201 (app) and 4202 (storybook).
CORS_ORIGINS=http://localhost:4201,http://localhost:4202

# ── AI Provider ────────────────────────────────────────────────────────
# Valid values: claude | cli | mock
#   claude  — live Anthropic API (requires ANTHROPIC_API_KEY)
#   cli     — local Claude CLI subprocess
#   mock    — static fixture responses; use for local dev and CI smoke tests
AI_PROVIDER=mock

# Required when AI_PROVIDER=claude. Leave empty for mock/cli modes.
# Never commit a real key — add it to your local .env only.
ANTHROPIC_API_KEY=

# ── Deployment secrets ─────────────────────────────────────────────────
# These variables MUST NOT appear in .env or be committed to source control.
# Provision them in GitHub → Settings → Secrets and variables → Actions.
# Reference only: document the names so the CI pipeline is self-describing.
# COOLIFY_WEBHOOK=
# COOLIFY_TOKEN=
```

**Verify:**
```bash
# All required uncommented keys are present
grep -E "^[A-Z_]+=.*" .env.example | cut -d= -f1 | sort

# Secrets are NOT present as uncommented assignments
grep -E "^COOLIFY_WEBHOOK=" .env.example && echo "FAIL: secret exposed" || echo "OK"
grep -E "^COOLIFY_TOKEN=" .env.example && echo "FAIL: secret exposed" || echo "OK"
```

Expected: `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` lines print `OK` (grep exits non-zero → no match).

---

### Step 3: Create `.github/dependabot.yml`

**Action:** Create the `.github/` directory if it does not exist, then create `dependabot.yml`. Scope the config to pip only; weekly cadence; no prefix or label customisation — defaults are sufficient.

**File:** `.github/dependabot.yml` (new)

**Pattern:**
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

**Verify:**
```bash
# File exists and is valid YAML
python3 -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/dependabot.yml').read_text()); print('OK')"

# Confirm the three required keys
grep -E "package-ecosystem|directory|interval" .github/dependabot.yml
```

Expected output from grep: three matching lines, each containing the correct value.

---

### Step 4: Write structural pytest tests

**Action:** Create `tests/test_env_example.py`. Tests assert that `.env.example` (a) exists, (b) contains all required non-secret variable names as uncommented assignments, and (c) contains no uncommented non-empty value for any secret key.

**File:** `tests/test_env_example.py` (new)

**Pattern:**
```python
import pathlib
import re

import pytest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
_ENV_EXAMPLE = _REPO_ROOT / ".env.example"

# Every variable the application reads that must be documented with a safe default.
# Update this list whenever a new os.getenv() call is added to the application.
REQUIRED_KEYS = [
    "FLASK_APP",
    "FLASK_DEBUG",
    "PORT",
    "SPEC_DOC_DIR",
    "CORS_ORIGINS",
    "AI_PROVIDER",
    "ANTHROPIC_API_KEY",
]

# Variables that must appear ONLY as comments — never as live assignments.
MUST_REMAIN_COMMENTED = [
    "COOLIFY_WEBHOOK",
    "COOLIFY_TOKEN",
]


def _parse_defined_keys(content: str) -> set[str]:
    """Return variable names that appear as uncommented KEY= lines."""
    return {
        m.group(1)
        for m in re.finditer(r"^([A-Z_][A-Z0-9_]*)=", content, re.MULTILINE)
    }


class TestEnvExample:
    def test_file_exists(self):
        assert _ENV_EXAMPLE.exists(), (
            ".env.example must exist at the repository root"
        )

    def test_required_keys_are_defined(self):
        content = _ENV_EXAMPLE.read_text()
        defined = _parse_defined_keys(content)
        missing = [k for k in REQUIRED_KEYS if k not in defined]
        assert missing == [], (
            f"These keys are missing from .env.example: {missing}"
        )

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_each_required_key_is_present(self, key):
        content = _ENV_EXAMPLE.read_text()
        defined = _parse_defined_keys(content)
        assert key in defined, (
            f"'{key}' must appear as an uncommented assignment in .env.example"
        )

    @pytest.mark.parametrize("secret_key", MUST_REMAIN_COMMENTED)
    def test_deployment_secrets_are_commented_out(self, secret_key):
        content = _ENV_EXAMPLE.read_text()
        # Must not appear as an uncommented KEY= line
        assert not re.search(
            rf"^{secret_key}=", content, re.MULTILINE
        ), (
            f"'{secret_key}' must be commented out in .env.example — "
            "it lives in GitHub Secrets only and must never be committed"
        )

    def test_anthropic_api_key_has_empty_value(self):
        content = _ENV_EXAMPLE.read_text()
        match = re.search(r"^ANTHROPIC_API_KEY=(.*)$", content, re.MULTILINE)
        assert match is not None, (
            "ANTHROPIC_API_KEY must be present in .env.example"
        )
        assert match.group(1).strip() == "", (
            f"ANTHROPIC_API_KEY must have an empty value in .env.example, "
            f"got: {match.group(1)!r}"
        )

    def test_ai_provider_default_is_mock(self):
        content = _ENV_EXAMPLE.read_text()
        match = re.search(r"^AI_PROVIDER=(.+)$", content, re.MULTILINE)
        assert match is not None, "AI_PROVIDER must be present in .env.example"
        assert match.group(1).strip() == "mock", (
            f"AI_PROVIDER local default must be 'mock' (safe for local dev without an API key), "
            f"got: {match.group(1)!r}"
        )

    def test_dependabot_yml_exists(self):
        dependabot = _REPO_ROOT / ".github" / "dependabot.yml"
        assert dependabot.exists(), (
            ".github/dependabot.yml must exist"
        )

    def test_dependabot_targets_pip(self):
        import yaml  # stdlib pyyaml is a dev dependency; present in all Python envs
        dependabot = _REPO_ROOT / ".github" / "dependabot.yml"
        config = yaml.safe_load(dependabot.read_text())
        ecosystems = [u["package-ecosystem"] for u in config.get("updates", [])]
        assert "pip" in ecosystems, (
            "dependabot.yml must include a pip update schedule"
        )

    def test_dependabot_schedule_is_weekly(self):
        import yaml
        dependabot = _REPO_ROOT / ".github" / "dependabot.yml"
        config = yaml.safe_load(dependabot.read_text())
        pip_entry = next(
            (u for u in config.get("updates", []) if u["package-ecosystem"] == "pip"),
            None,
        )
        assert pip_entry is not None, "No pip entry found in dependabot.yml"
        assert pip_entry["schedule"]["interval"] == "weekly", (
            "Dependabot pip schedule must be 'weekly'"
        )
```

**Verify:**
```bash
make test
# Expect 192 → 194 passing (2 test classes × parametrized = net +9 test cases,
# but pytest counts parametrized cases individually — see §7 for exact delta)
```

---

## 5. Tests

The complete test suite is in Step 4 above. No stubs. Summary of assertions:

| Test | Assertion |
|---|---|
| `test_file_exists` | `.env.example` exists at repo root |
| `test_required_keys_are_defined` | All 7 required keys present as uncommented assignments (bulk) |
| `test_each_required_key_is_present` (×7) | Each required key present individually (parametrized) |
| `test_deployment_secrets_are_commented_out` (×2) | `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` absent as live assignments |
| `test_anthropic_api_key_has_empty_value` | `ANTHROPIC_API_KEY=` has no value |
| `test_ai_provider_default_is_mock` | `AI_PROVIDER=mock` (safe offline default) |
| `test_dependabot_yml_exists` | `.github/dependabot.yml` exists |
| `test_dependabot_targets_pip` | YAML `package-ecosystem` includes `pip` |
| `test_dependabot_schedule_is_weekly` | pip entry `schedule.interval == "weekly"` |

---

## 6. Commit Plan

**Executor instruction:** commit after **each step** completes. Do not batch commits at the end.

1. **`chore(env): add .env.example with all declared env var defaults`** — after Step 2  
   Files: `.env.example`  
   Body: list any variables discovered via grep that were not in this guide

2. **`chore(ci): add dependabot weekly pip schedule`** — after Step 3  
   Files: `.github/dependabot.yml`

3. **`test(env): add structural tests for .env.example and dependabot completeness`** — after Step 4 + `make test` passes  
   Files: `tests/test_env_example.py`

**Deviation logging:** if any step departs from this guide, prefix the commit body with `Deviations:` followed by one line per deviation (e.g., `Deviations: added DATABASE_URL — found in modules/db/config.py:12 via grep audit`).

---

## 7. Verification

```bash
make test
```

**Expected delta:**

| Metric | Before | After |
|---|---|---|
| Total tests | 192 | 201 |
| New test cases | — | +9 (1 bulk + 7 parametrized key checks + 2 parametrized secret checks − 1 overlap = net 9 new `pytest` node IDs) |
| Pre-existing failures | 0 | 0 |

> Exact count depends on how pytest counts parametrized cases in the existing suite. The invariant is: zero pre-existing tests broken, all new assertions passing.

---

## 8. Rollback

- **Per-step:** each commit above is independently revertible without touching adjacent changes.
  ```bash
  git revert <sha>   # generates a new revert commit; does not rewrite history
  ```

- **Per-branch:** if verification fails and the branch cannot be salvaged:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destroys uncommitted work
  # or, if on a feature branch:
  git checkout main && git branch -D <feature-branch>
  ```

- **`.env.example` alone:** `git revert <step-2-sha>` removes the file without affecting dependabot or tests.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** — if `.github/` already contains files (e.g., from a prior task), create `dependabot.yml` inside it; do not modify existing files there.
- **Additional env vars found via grep** — add them to `.env.example` and to `REQUIRED_KEYS` in the test; log as a deviation in the commit body.
- **Test framework mismatch** — this guide uses plain `pytest` with `assert`. If the repo uses a custom base class or fixtures (inspect `tests/conftest.py` if it exists), match that convention and note the adaptation in the commit body.
- **`pyyaml` not installed** — if `import yaml` fails in the test, add `pyyaml` to `requirements-dev.txt` (or equivalent dev dependencies file) as part of Step 4, and include `requirements-dev.txt` in the Step 4 commit.
- **Side-effect required** (e.g., pushing `.env.example` triggers a secret scan that flags a false positive) — [REQUIRES APPROVAL] — stop and surface the finding before continuing.
- **Step N unlocks a simplification for Step N+1** — take it; log the deviation in the commit body.

---

## 10. Out of Scope

This task writes infrastructure declarations only. It does not validate that the application actually starts with the documented defaults, does not test AI provider switching behaviour, and does not touch the CI workflow, Dockerfile, or any compose file — those are the concerns of Tasks 4 and 5. The Dependabot configuration here is minimal by design; it does not pin reviewers, set labels, or group updates. Those are enhancements that belong in a future housekeeping task once the PR queue has a demonstrated pattern.

- **Reviewer assignment and PR labels in `dependabot.yml`** — deferred until a second contributor joins the project; adds noise with no benefit for a single-developer repo at this stage.
- **Dependabot for GitHub Actions** — deferred; no Actions workflows exist yet (Task 4). Re-evaluate after Task 4 ships.
- **`.env` validation at app startup** — deferred; a startup check that fails fast on missing required variables is a quality-of-life improvement but not a blocker for CI/CD. Revisit after the full pipeline is running.
- **`SPEC_DOC_DIR` defaulting to a resolved relative path** — deferred; the container compose files set this via bind-mount, and local developers must set it explicitly. Automating a relative-path resolution at startup is an application change outside this task's scope.
- **Secret scanning enforcement (e.g., `detect-secrets` pre-commit hook)** — deferred; the `.gitignore` on `.env` is the current enforcement mechanism. A pre-commit hook is a follow-up DevEx task.

**Rule for the executor:** if a change appears helpful but is listed above, stop and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, including the "Explicit over implicit" principle this task implements
- [Epic](./epic.md) – Full task scope and dependencies
- [Timeline](./timeline.md) – Update status to ✅ after verification passes