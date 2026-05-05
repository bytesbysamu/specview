# Task 2 — Auto-Detect SDK Provider in Adapter

**Effort**: 0.2 days

## 1. Context

After Task 1, the SDK provider is fully wired and surfaces token usage. But `_select_provider()` in `runtime/chain/adapter.py` still defaults to `"cli"` when `CHAIN_PROVIDER` is unset, which means a deploy container that has the API key but forgot to set `CHAIN_PROVIDER=claude` falls back to a CLI binary that does not exist. Crash on first AI call, not on startup.

This task makes the adapter auto-detect: if `CHAIN_PROVIDER` is unset and `ANTHROPIC_API_KEY` is present, choose `"claude"`; otherwise choose `"cli"`. An explicit `CHAIN_PROVIDER` always wins so tests (`mock`) and overrides keep working. Resolve the analysis open question by accepting `"anthropic"` as an alias for `"claude"` in the mapping, so the brain dump's naming and the existing module name both work.

The structural test that prevents feature modules from importing providers directly gets one new assertion: feature code must not contain `if CHAIN_PROVIDER == ...` style branches — provider selection happens in exactly one file.

---

## 2. Pre-flight

```bash
git status -- api/modules/runtime/chain/
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
```

Confirm Task 1 has merged and the recorded test count is `N+2 → call this M`. This task's success delta is expressed against `M`.

---

## 3. Files

### To Modify

- `{WORKSPACE}/api/modules/runtime/chain/adapter.py` — replace the literal `"cli"` default with an auto-detection helper; add `"anthropic"` as an alias in the mapping
- `{WORKSPACE}/api/modules/runtime/chain/tests/test_adapter.py` — add cases for the auto-detection branches and the alias
- `{WORKSPACE}/api/modules/runtime/chain/tests/test_structural.py` — add an assertion that no file under `modules/ai/` references `CHAIN_PROVIDER` in a conditional

### To Leave Alone

- `{WORKSPACE}/api/modules/runtime/chain/providers/*` — Task 1 finished the provider surface
- `{WORKSPACE}/api/modules/ai/**` — feature code is unchanged; the new alias does not require any caller update
- `{WORKSPACE}/api/openapi.yaml` — no contract change

---

## 4. Implementation Steps

### Step 1: Add the alias and auto-detection helper

**Action**: Replace the `name = os.environ.get("CHAIN_PROVIDER", "cli")` line with a helper that consults `ANTHROPIC_API_KEY`. Add `"anthropic"` to the mapping pointing at the same `providers.claude` module.

**File**: `{WORKSPACE}/api/modules/runtime/chain/adapter.py`

**Pattern**:

```python
def _resolve_provider_name() -> str:
    """Return the provider name to use given the current environment.

    Precedence:
      1. CHAIN_PROVIDER explicitly set → use it as-is.
      2. ANTHROPIC_API_KEY present → "claude" (production default).
      3. Otherwise → "cli" (developer fallback; assumes Claude Code subscription).
    """
    explicit = os.environ.get("CHAIN_PROVIDER")
    if explicit:
        return explicit
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return "cli"


def _select_provider():
    name = _resolve_provider_name()
    mapping = {
        "claude": providers.claude,
        "anthropic": providers.claude,  # alias — brain dump uses this name
        "cli": providers.cli,
        "mock": providers.mock,
    }
    if name not in mapping:
        raise ValueError(
            f"Unknown CHAIN_PROVIDER={name!r}; expected one of "
            f"{sorted(set(mapping))}"
        )
    return mapping[name]
```

The docstring is part of the change — it's the only place the precedence is documented.

---

### Step 2: Test the auto-detection branches

**File**: `{WORKSPACE}/api/modules/runtime/chain/tests/test_adapter.py`

**Pattern** (append):

```python
import importlib

from modules.runtime.chain import adapter
from modules.runtime.chain import providers


def test_resolve_provider_uses_explicit_chain_provider(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
    assert adapter._resolve_provider_name() == "mock"


def test_resolve_provider_picks_claude_when_api_key_present(monkeypatch):
    monkeypatch.delenv("CHAIN_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
    assert adapter._resolve_provider_name() == "claude"


def test_resolve_provider_falls_back_to_cli_without_key(monkeypatch):
    monkeypatch.delenv("CHAIN_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert adapter._resolve_provider_name() == "cli"


def test_anthropic_alias_resolves_to_claude_provider(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "anthropic")
    selected = adapter._select_provider()
    assert selected is providers.claude


def test_unknown_chain_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "openai")
    with pytest.raises(ValueError) as excinfo:
        adapter._select_provider()
    assert "openai" in str(excinfo.value)
```

If the test file does not already import `pytest`, add it at the top.

---

### Step 3: Extend the structural test

**Action**: A new assertion ensures no file under `modules/ai/` (or any future feature module) reads `CHAIN_PROVIDER`. Selection lives in the adapter alone.

**File**: `{WORKSPACE}/api/modules/runtime/chain/tests/test_structural.py`

**Pattern** (append):

```python
import pathlib


def test_feature_modules_must_not_branch_on_chain_provider():
    """ELA #1 — provider selection lives in adapter.py and nowhere else."""
    api_root = pathlib.Path(__file__).resolve().parents[4]  # api/
    feature_dirs = [api_root / "modules" / "ai", api_root / "modules" / "data"]
    offenders = []
    for root in feature_dirs:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if "/tests/" in str(py).replace("\\", "/"):
                continue
            text = py.read_text(encoding="utf-8")
            if "CHAIN_PROVIDER" in text:
                offenders.append(str(py.relative_to(api_root)))
    assert offenders == [], (
        "Feature modules must not reference CHAIN_PROVIDER directly; "
        f"violators: {offenders}"
    )
```

If the path arithmetic is brittle for the layout, replace `parents[4]` with the directory two above `tests/` and re-derive — confirm by printing `api_root` once during initial run.

---

## 5. Tests

```bash
cd {WORKSPACE}/api && python -m pytest modules/runtime/chain/ -q
cd {WORKSPACE}/api && python -m pytest -q
```

**Expected delta**: `M → M+6 passing` (5 new adapter tests + 1 new structural test).

---

## 6. Commit Plan

```bash
cd {WORKSPACE}
git add api/modules/runtime/chain/adapter.py \
        api/modules/runtime/chain/tests/test_adapter.py \
        api/modules/runtime/chain/tests/test_structural.py

git commit -m "$(cat <<'EOF'
feat(chain): auto-detect SDK provider when ANTHROPIC_API_KEY is set

_resolve_provider_name() picks 'claude' when the API key is present and
no explicit CHAIN_PROVIDER override exists. 'anthropic' is accepted as an
alias for 'claude' so the brain dump's naming and the existing module
name both work. Structural test rejects any feature-side branch on
CHAIN_PROVIDER — selection lives only in the adapter.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: `M → M+6 passing`.

Post-merge spot check on a dev box (no API key set):

```bash
cd {WORKSPACE}/api && python -c "
import os
os.environ.pop('CHAIN_PROVIDER', None)
os.environ.pop('ANTHROPIC_API_KEY', None)
from modules.runtime.chain import adapter
assert adapter._resolve_provider_name() == 'cli'
os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-fake'
assert adapter._resolve_provider_name() == 'claude'
print('auto-detect OK')
"
```

---

## 8. Rollback

```bash
git revert <sha-of-this-task>
```

Reverting restores the literal `"cli"` default. No data implications. The Task 1 token plumbing keeps working because Task 1 did not depend on selection logic.

---

## 9. Deviations Allowed

- **`tests/test_structural.py` does not exist yet**: create it with a single `def test_feature_modules_must_not_branch_on_chain_provider():` body. Do not invent other structural assertions in this commit.
- **A future-proof feature module legitimately needs to know whether the SDK is active** (e.g., a UI widget that dims a "stream tokens" toggle): expose `get_active_provider_name()` from the adapter and have the feature module call it; do NOT read `CHAIN_PROVIDER` in the feature module.
- **`pytest` parametrize feels cleaner than five separate test functions**: that is a stylistic call; either is acceptable as long as every branch (explicit, key+default, no key+default, alias, unknown) has its own assertion path.

---

## 10. Out of Scope

- Cost accumulator and `/api/ai/stats` endpoint — Task 3
- Per-step model routing in workflow definitions — Task 4
- Production startup gate in `create_app.py` — Task 5
- Adding new providers (OpenAI, Gemini) — explicitly excluded by architecture
- Removing the CLI provider — kept indefinitely as a dev fallback

---

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
