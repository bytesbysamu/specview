# Task 1: Context Block Loader

**Epic**: Text Chains — LoRA for Text
**Estimated effort**: 0.5 day (~300-400 lines)
**Dependencies**: None (parallel with Task 2)

---

## 1. Context

The chain adapter (`server/modules/chain/adapter.py`) currently injects context by reading `user.builder` and `user.principles` from the ORM row at call time. Text Chains needs a second context source: markdown files on disk (system prompts, rubrics) that any chain step can reference by name. The Context Block Loader is an adapter-shaped module that reads these files from `server/context/` via a `manifest.json` mapping, returning named blocks as `dict[str, str]`. Mock mode (`CONTEXT_PROVIDER=mock`) returns fixture strings for testing with zero file I/O.

This module owns the `server/context/` directory exclusively. A structural test (grep-based) enforces that no other module reads from `server/context/` directly.

### Trade-offs considered

- **Single manifest.json vs per-directory discovery**: Manifest chosen because it gives explicit naming (context-block names decouple from file paths), makes validation trivial (compare manifest keys against chain definition references), and avoids glob-based file discovery that couples to directory layout. Rejected: directory traversal (implicit, harder to validate).
- **Python module under `server/modules/context/` vs standalone `server/context/loader.py`**: Placed in `server/modules/context/` to match the existing module convention (`server/modules/chain/`, `server/modules/text/`). The content files stay at `server/context/` (outside any Python package) to avoid `.py`-file confusion. Rejected: flat `server/context/loader.py` (breaks module convention).
- **Env-flag mock (`CONTEXT_PROVIDER=mock`) vs pytest monkeypatch**: Env flag matches the chain adapter's existing `CHAIN_PROVIDER=mock` pattern. Same shape, same conftest fixture, same test runner ergonomics. Rejected: injecting a mock via constructor (no constructor — module-level functions match the adapter surface).

---

## 2. Pre-flight

```bash
cd /projects/bubls/server
git status
git diff HEAD
python -m pytest --tb=short -q 2>&1 | tail -5   # record baseline test count
```

Record the baseline test count before any edits. All existing tests must still pass after this task.

---

## 3. Files

### To Create

| File | Purpose |
|------|---------|
| `server/modules/context/__init__.py` | Package init; re-exports `load_block`, `load_blocks` |
| `server/modules/context/loader.py` | Adapter-shaped loader: manifest parse, file read, mock mode |
| `server/modules/context/tests/__init__.py` | Test package init |
| `server/modules/context/tests/conftest.py` | `autouse` fixture: `CONTEXT_PROVIDER=mock` |
| `server/modules/context/tests/test_loader.py` | Unit + structural tests for the loader |
| `server/context/manifest.json` | Name-to-path mapping for context blocks |
| `server/context/prompts/humanize-pass-1.md` | Placeholder prompt (real content in Task 3) |
| `server/context/rubrics/quality.md` | Placeholder rubric (real content in Task 5) |

### To Modify

None. This module is fully additive.

### To Leave Alone

| File | Reason |
|------|--------|
| `server/modules/chain/adapter.py` | Chain adapter unchanged; Task 2 wires context loader into the runner, not the adapter |
| `server/modules/chain/context.py` | Existing builder/principles injection unchanged |
| `server/modules/text/service.py` | Single-shot text service unchanged |
| `server/app.py` | Context module has no Blueprint; no registration needed |

---

## 4. Implementation Steps

### Step 1: Create the content directory scaffold

**Action**: Create `server/context/` directory with subdirectories `prompts/` and `rubrics/`, plus placeholder markdown files.

**File**: `server/context/manifest.json`

```json
{
  "humanize-pass-1": "prompts/humanize-pass-1.md",
  "humanize-pass-2": "prompts/humanize-pass-2.md",
  "humanize-pass-3": "prompts/humanize-pass-3.md",
  "braindump-lint": "prompts/braindump-lint.md",
  "braindump-to-docs": "prompts/braindump-to-docs.md",
  "builder": "prompts/builder.md",
  "principles": "prompts/principles.md",
  "references": "prompts/references.md",
  "quality-rubric": "rubrics/quality.md"
}
```

**File**: `server/context/prompts/humanize-pass-1.md`

```markdown
# Humanize Pass 1 — Sentence Structure

(Placeholder — real content ported from humanize-me in Task 3)

Rewrite the text to vary sentence length. Mix short punches with longer flows.
Break any two consecutive sentences that start the same way.
```

**File**: `server/context/rubrics/quality.md`

```markdown
# Quality Rubric

(Placeholder — real content authored in Task 5)

Score the text on: clarity (1-5), conciseness (1-5), accuracy (1-5).
Return JSON: { "scores": { "clarity": N, "conciseness": N, "accuracy": N }, "issues": [] }
```

Create matching placeholder files for every entry in `manifest.json` so the loader never hits a `FileNotFoundError` during development. Each placeholder is 2-4 lines of markdown with a `(Placeholder)` marker.

**Verify**:
```bash
python -c "import json; m = json.load(open('server/context/manifest.json')); [open(f'server/context/{v}') for v in m.values()]; print(f'OK: {len(m)} blocks, all files exist')"
```

### Step 2: Create the loader module

**Action**: Create `server/modules/context/loader.py` with `load_block(name)` and `load_blocks(names)` functions plus mock mode.

**File**: `server/modules/context/loader.py`

```python
"""Context Block Loader — adapter-shaped module for markdown prompt/rubric files.

Reads named context blocks from ``server/context/`` via ``manifest.json``.
Mock mode (``CONTEXT_PROVIDER=mock``) returns deterministic fixture strings.

Structural invariant: this is the ONLY module that reads from ``server/context/``.
Enforced by grep-based test in ``tests/test_loader.py``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# server/context/ lives two levels up from server/modules/context/
_CONTEXT_ROOT = Path(__file__).resolve().parent.parent.parent / "context"
_MANIFEST_PATH = _CONTEXT_ROOT / "manifest.json"

# Lazy-loaded manifest cache (populated on first call).
_manifest: dict[str, str] | None = None


def _get_manifest() -> dict[str, str]:
    """Load and cache manifest.json. Raises FileNotFoundError if missing."""
    global _manifest
    if _manifest is None:
        if not _MANIFEST_PATH.exists():
            raise FileNotFoundError(
                f"Context manifest not found: {_MANIFEST_PATH}. "
                f"Expected server/context/manifest.json."
            )
        with open(_MANIFEST_PATH) as f:
            _manifest = json.load(f)
    return _manifest


def _is_mock() -> bool:
    return os.environ.get("CONTEXT_PROVIDER", "").lower() == "mock"


# ── Mock fixtures ────────────────────────────────────────────────────────────
_MOCK_FIXTURES: dict[str, str] = {
    "humanize-pass-1": "MOCK_CONTEXT[humanize-pass-1]: vary sentence length",
    "humanize-pass-2": "MOCK_CONTEXT[humanize-pass-2]: remove AI tells",
    "humanize-pass-3": "MOCK_CONTEXT[humanize-pass-3]: add imperfections",
    "braindump-lint": "MOCK_CONTEXT[braindump-lint]: check structure",
    "braindump-to-docs": "MOCK_CONTEXT[braindump-to-docs]: generate docs",
    "builder": "MOCK_CONTEXT[builder]: solo founder, Flask stack",
    "principles": "MOCK_CONTEXT[principles]: always ORM, adapter pattern",
    "references": "MOCK_CONTEXT[references]: see architecture.md",
    "quality-rubric": "MOCK_CONTEXT[quality-rubric]: clarity, conciseness, accuracy",
}


def _mock_block(name: str) -> str:
    """Return a deterministic fixture string for the given block name."""
    if name in _MOCK_FIXTURES:
        return _MOCK_FIXTURES[name]
    return f"MOCK_CONTEXT[{name}]: (no fixture registered)"


# ── Public API ───────────────────────────────────────────────────────────────

def load_block(name: str) -> str:
    """Load a single context block by name.

    Raises:
        KeyError: block name not found in manifest.json
        FileNotFoundError: manifest entry exists but file missing on disk
    """
    if _is_mock():
        return _mock_block(name)

    manifest = _get_manifest()
    if name not in manifest:
        raise KeyError(
            f"Context block {name!r} not found in manifest.json. "
            f"Available: {sorted(manifest.keys())}"
        )
    file_path = _CONTEXT_ROOT / manifest[name]
    if not file_path.exists():
        raise FileNotFoundError(
            f"Context block {name!r} maps to {manifest[name]} "
            f"but file not found: {file_path}"
        )
    return file_path.read_text(encoding="utf-8").strip()


def load_blocks(names: list[str]) -> dict[str, str]:
    """Load multiple context blocks by name. Returns ``{name: content}``.

    Raises on the first missing name or file — fail loud, not partial.
    """
    return {name: load_block(name) for name in names}


def validate_manifest() -> list[str]:
    """Check every manifest entry has a corresponding file on disk.

    Returns a list of error strings (empty = valid). Used in structural
    tests to catch manifest/filesystem drift before runtime.
    """
    if _is_mock():
        return []
    manifest = _get_manifest()
    errors: list[str] = []
    for name, rel_path in manifest.items():
        full = _CONTEXT_ROOT / rel_path
        if not full.exists():
            errors.append(f"Block {name!r} → {rel_path}: file not found")
    return errors


def reset_cache() -> None:
    """Clear the manifest cache. Called in tests after modifying manifest.json."""
    global _manifest
    _manifest = None
```

**Verify**:
```bash
cd /projects/bubls/server
CONTEXT_PROVIDER=mock python -c "from modules.context.loader import load_block; print(load_block('humanize-pass-1'))"
```

Expected output: `MOCK_CONTEXT[humanize-pass-1]: vary sentence length`

### Step 3: Create the package init

**Action**: Create `server/modules/context/__init__.py` re-exporting the public API.

**File**: `server/modules/context/__init__.py`

```python
"""Context block loader — adapter-shaped module for markdown prompt/rubric files.

Public surface:
- ``load_block(name)`` — single block
- ``load_blocks(names)`` — multiple blocks as dict
- ``validate_manifest()`` — filesystem consistency check

``CONTEXT_PROVIDER=mock`` in env → returns fixture strings, no file I/O.
"""
from .loader import load_block, load_blocks, validate_manifest

__all__ = ["load_block", "load_blocks", "validate_manifest"]
```

**Verify**:
```bash
cd /projects/bubls/server
CONTEXT_PROVIDER=mock python -c "from modules.context import load_block; print(load_block('builder'))"
```

### Step 4: Create tests

**Action**: Create the test package with conftest and full test file.

**File**: `server/modules/context/tests/conftest.py`

```python
"""Force mock context provider for all context-module tests."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_mock_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")
```

**File**: `server/modules/context/tests/test_loader.py` — see Section 5 (Tests) for the full file.

**Verify**:
```bash
cd /projects/bubls/server
python -m pytest modules/context/tests/ -v --tb=short
```

---

## 5. Tests

**File**: `server/modules/context/tests/test_loader.py`

```python
"""Unit + structural tests for the context block loader.

Mock mode is forced by the autouse conftest fixture. Tests that need real
file I/O explicitly unset CONTEXT_PROVIDER via monkeypatch.
"""
from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

from modules.context import loader as _loader


# ── Mock-mode tests ──────────────────────────────────────────────────────────

def test_loadBlock_mockMode_returnsFixtureString():
    result = _loader.load_block("humanize-pass-1")
    assert result == "MOCK_CONTEXT[humanize-pass-1]: vary sentence length"


def test_loadBlock_mockMode_unknownName_returnsFallbackFixture():
    result = _loader.load_block("nonexistent-block")
    assert result == "MOCK_CONTEXT[nonexistent-block]: (no fixture registered)"


def test_loadBlocks_mockMode_returnsDict():
    result = _loader.load_blocks(["builder", "quality-rubric"])
    assert isinstance(result, dict)
    assert set(result.keys()) == {"builder", "quality-rubric"}
    assert "solo founder" in result["builder"]
    assert "clarity" in result["quality-rubric"]


def test_loadBlocks_mockMode_emptyList_returnsEmptyDict():
    assert _loader.load_blocks([]) == {}


# ── Real file I/O tests ─────────────────────────────────────────────────────

def test_loadBlock_realMode_readsFileFromDisk(monkeypatch, tmp_path):
    monkeypatch.delenv("CONTEXT_PROVIDER", raising=False)
    _loader.reset_cache()

    # Build a minimal context directory with manifest
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test-block.md").write_text("# Test\nThis is test content.")
    manifest = {"test-block": "prompts/test-block.md"}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    monkeypatch.setattr(_loader, "_CONTEXT_ROOT", tmp_path)
    monkeypatch.setattr(_loader, "_MANIFEST_PATH", tmp_path / "manifest.json")
    _loader.reset_cache()

    result = _loader.load_block("test-block")
    assert result == "# Test\nThis is test content."


def test_loadBlock_realMode_unknownName_raisesKeyError(monkeypatch, tmp_path):
    monkeypatch.delenv("CONTEXT_PROVIDER", raising=False)
    _loader.reset_cache()

    (tmp_path / "manifest.json").write_text(json.dumps({"only-this": "x.md"}))
    monkeypatch.setattr(_loader, "_CONTEXT_ROOT", tmp_path)
    monkeypatch.setattr(_loader, "_MANIFEST_PATH", tmp_path / "manifest.json")
    _loader.reset_cache()

    with pytest.raises(KeyError, match="not-in-manifest"):
        _loader.load_block("not-in-manifest")


def test_loadBlock_realMode_fileMissing_raisesFileNotFoundError(monkeypatch, tmp_path):
    monkeypatch.delenv("CONTEXT_PROVIDER", raising=False)
    _loader.reset_cache()

    manifest = {"ghost": "prompts/ghost.md"}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(_loader, "_CONTEXT_ROOT", tmp_path)
    monkeypatch.setattr(_loader, "_MANIFEST_PATH", tmp_path / "manifest.json")
    _loader.reset_cache()

    with pytest.raises(FileNotFoundError, match="ghost.md"):
        _loader.load_block("ghost")


def test_validateManifest_realMode_allFilesExist_returnsEmpty(monkeypatch, tmp_path):
    monkeypatch.delenv("CONTEXT_PROVIDER", raising=False)
    _loader.reset_cache()

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "a.md").write_text("content a")
    (prompts_dir / "b.md").write_text("content b")
    manifest = {"block-a": "prompts/a.md", "block-b": "prompts/b.md"}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(_loader, "_CONTEXT_ROOT", tmp_path)
    monkeypatch.setattr(_loader, "_MANIFEST_PATH", tmp_path / "manifest.json")
    _loader.reset_cache()

    assert _loader.validate_manifest() == []


def test_validateManifest_realMode_missingFile_returnsErrors(monkeypatch, tmp_path):
    monkeypatch.delenv("CONTEXT_PROVIDER", raising=False)
    _loader.reset_cache()

    manifest = {"missing": "prompts/missing.md"}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(_loader, "_CONTEXT_ROOT", tmp_path)
    monkeypatch.setattr(_loader, "_MANIFEST_PATH", tmp_path / "manifest.json")
    _loader.reset_cache()

    errors = _loader.validate_manifest()
    assert len(errors) == 1
    assert "missing" in errors[0]


def test_validateManifest_mockMode_returnsEmpty():
    assert _loader.validate_manifest() == []


# ── Structural tests ─────────────────────────────────────────────────────────

def test_contextFiles_onlyReadByLoader():
    """Structural invariant: only context/loader.py reads from server/context/.

    Greps server/ for open()/read_text()/Path() calls referencing
    'server/context/' outside the context loader module. Catches coupling
    drift that code review misses.
    """
    server_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
    loader_path = server_root / "modules" / "context" / "loader.py"
    offenders: list[str] = []

    for py in server_root.rglob("*.py"):
        # Skip the loader itself, tests, venv, and migrations
        rel = py.relative_to(server_root)
        if str(rel).startswith((".venv", "migrations")):
            continue
        if py.resolve() == loader_path.resolve():
            continue
        if "tests" in rel.parts:
            continue

        text = py.read_text(encoding="utf-8", errors="ignore")
        # Check for direct file access to server/context/
        for marker in ["server/context/", "context/manifest", "context/prompts", "context/rubrics"]:
            if marker in text:
                # Allow relative imports like "from modules.context" (that's using the loader)
                lines_with_marker = [
                    line.strip() for line in text.splitlines()
                    if marker in line and not line.strip().startswith("#")
                    and "import" not in line
                ]
                if lines_with_marker:
                    offenders.append(f"{rel}: {lines_with_marker[0][:80]}")

    assert offenders == [], (
        "Only context/loader.py may read from server/context/. "
        f"Use loader.load_block(name) instead. Offenders: {offenders}"
    )


def test_manifestKeysAreAllLowerKebabCase():
    """Naming convention: all manifest keys must be lower-kebab-case."""
    import re
    manifest_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "context" / "manifest.json"
    if not manifest_path.exists():
        pytest.skip("manifest.json not yet created")
    manifest = json.loads(manifest_path.read_text())
    pattern = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
    bad = [k for k in manifest if not pattern.match(k)]
    assert bad == [], f"Manifest keys must be lower-kebab-case. Violations: {bad}"
```

---

## 6. Commit Plan

### Commit 1: `feat(context): add server/context/ directory scaffold with manifest.json`

**Scope**: `server/context/manifest.json`, all placeholder `.md` files under `server/context/prompts/` and `server/context/rubrics/`.

**Boundary**: Content files only. No Python code.

### Commit 2: `feat(context): add context block loader module with mock mode`

**Scope**: `server/modules/context/__init__.py`, `server/modules/context/loader.py`.

**Boundary**: Module code only. No tests.

### Commit 3: `test(context): add unit + structural tests for context block loader`

**Scope**: `server/modules/context/tests/__init__.py`, `server/modules/context/tests/conftest.py`, `server/modules/context/tests/test_loader.py`.

**Boundary**: Tests only. Run full suite after this commit.

---

## 7. Verification

```bash
cd /projects/bubls/server
python -m pytest --tb=short -q 2>&1 | tail -5
```

**Expected test-count delta**: +12 tests (4 mock-mode, 5 real-file-I/O, 1 validate-mock, 2 structural).

**Full-suite command**:
```bash
cd /projects/bubls/server
python -m pytest --tb=short -v
```

All pre-existing tests must pass unchanged. Zero regressions.

---

## 8. Rollback

### Per-step rollback

| Step | Rollback |
|------|----------|
| Step 1 (directory scaffold) | `rm -rf server/context/` |
| Step 2 (loader module) | `rm -rf server/modules/context/` |
| Step 3 (package init) | Already in `server/modules/context/`; same as Step 2 |
| Step 4 (tests) | `rm server/modules/context/tests/test_loader.py` |

### Per-branch rollback

```bash
git checkout main -- server/
git branch -D feat/context-block-loader
```

No migrations, no DB changes, no config changes. Full rollback is a clean directory delete.

---

## 9. Deviations Allowed

| Situation | Action |
|-----------|--------|
| `_CONTEXT_ROOT` path resolution differs on executor's machine | Adjust the `Path(__file__).resolve().parent` chain to match actual directory depth. Log the deviation in the commit body. |
| Additional context block names needed beyond the 9 listed in manifest.json | Add them to manifest + create placeholder files. Do not remove any of the 9 specified names. |
| Existing tests fail before any edits | STOP. Do not proceed. Report the failing test names and baseline status. |
| `pyproject.toml` test discovery does not pick up `modules/context/tests/` | Verify `testpaths` includes `"modules"` (it does per current config). If not, add `"modules"` to `testpaths`. |
| Structural test `test_contextFiles_onlyReadByLoader` finds false positives in comments or docstrings | Tighten the grep pattern to exclude comment lines. Log the false positive and the fix in the commit body. |

---

## 10. Out of Scope

The following are explicitly deferred. Executor must **STOP and flag** if implementation pulls toward any of these:

| Deferred Item | Trigger to build |
|---------------|-----------------|
| User-editable context blocks via API | When a user-facing "customize prompts" feature is scoped |
| Context block versioning / history | When A/B testing prompt variants becomes a real need |
| Context block caching beyond the manifest cache | When profiling shows file I/O is a measurable bottleneck (it will not be for 9 files) |
| Dynamic context block registration (auto-discover new files) | When the number of context blocks exceeds 30 and manual manifest maintenance becomes friction |
| Wiring the context loader into `chain.adapter._effective_system` | Task 2 (Chain Runner) wires the loader; this task only builds the module |
| Real prompt content for humanize passes, braindump, rubrics | Tasks 3, 4, 5 port real content into the placeholder files |
| Blueprint registration in `app.py` | Context module has no routes; no blueprint needed |
