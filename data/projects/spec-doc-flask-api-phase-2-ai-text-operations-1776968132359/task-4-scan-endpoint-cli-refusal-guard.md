# Task 4: Scan Endpoint + CLI-Refusal Guard

## 1. Context

This task wires `POST /api/ai/text/scan` into the Flask backend — the endpoint the Angular `CodebaseService` already calls but receives 404 on. The handler walks the workspace filesystem with stdlib `os.walk`, builds a prompt from the tree + source file heads + entry points, calls the chain adapter for a one-shot markdown summary, detects Claude CLI tool-permission stubs before persisting them, and writes the result to `codebase.md` via the existing `write_context("codebase", ...)` call. On a CLI refusal the route returns 502 with a structured error body; the Angular client retries from there.

**Trade-offs considered:**
- Defer to Node.js server.js for scan (keep two servers) — rejected; the Flask server is the production path and having scan on a different port is operationally fragile once the Node server is retired.
- Move `_looks_like_cli_refusal` into the chain adapter — rejected per architecture decision: the refusal pattern is `cli`-provider-specific and scan-specific; the adapter must remain provider-agnostic; route-level detection keeps the adapter clean.
- Port `server/walker.js` as a standalone Python module — rejected; the walk is ~30 lines of stdlib `os.walk`; a separate module adds a file for no reuse benefit (one consumer today).

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# Record working-tree state
git status
git diff HEAD -- flask/create_app.py flask/modules/ai/routes.py

# Verify Task 1 scaffold exists
ls flask/modules/ai/ 2>/dev/null || echo "MISSING — scaffold step required"

# Baseline test count — record the number before editing
cd flask && python -m pytest --tb=no -q 2>&1 | tail -3
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**If `flask/modules/ai/` is missing**: Task 1 has not merged yet. Create the scaffold in Step 1 of this guide before proceeding.

**Baseline recorded**: ___/___  passing (record actual number; expected ~60 based on 8 existing test files).

---

## 3. Files

### To Create (new)
- `flask/modules/ai/__init__.py` — module init; only needed if Task 1 scaffold is absent
- `flask/modules/ai/prompts/__init__.py` — prompts subpackage init; only needed if Task 1 scaffold is absent
- `flask/modules/ai/prompts/scan.py` — pure `scan_prompt(raw: dict) -> str` function; no I/O; ports `buildScanPrompt()` from `server.js:1245–1307`
- `flask/modules/ai/tests/__init__.py` — test subpackage init; only if absent
- `flask/modules/ai/tests/test_scan_prompts.py` — unit tests for `scan_prompt`; no HTTP fixture
- `flask/tests/test_scan_route.py` — route integration tests via Flask test client

### To Modify (cite CODEBASE CONTEXT)
- `flask/create_app.py` — `ENABLED_MODULES` list; add `('modules.ai.routes', 'ai_bp')` if absent (Task 1 may have already added it)
- `flask/modules/ai/routes.py` — if it exists (Task 1 scaffold), append `scan()`, `_walk()`, `_looks_like_cli_refusal()`; if absent, create it with blueprint + these three items only

### To Leave Alone
- `flask/modules/chain/adapter.py` — Task 4 consumes `chain.generate()`; never modifies it; adapter boundary is non-negotiable
- `flask/modules/context/service.py` — Task 4 calls `write_context("codebase", ...)` and `read_context`; never modifies them
- `flask/modules/context/routes.py` — context CRUD routes; untouched
- `server/walker.js` — Node.js reference; ported to Python here; do not modify the JS original

---

## 4. Implementation Steps

### Step 1: Scaffold (conditional — skip if already exists from Task 1)

**Action**: Create `flask/modules/ai/` and `flask/modules/ai/prompts/` packages if absent. Add the `ai_bp` entry to `ENABLED_MODULES` if missing.

**File**: `flask/modules/ai/__init__.py` (new if absent)

```python
# intentionally empty
```

**File**: `flask/modules/ai/prompts/__init__.py` (new if absent)

```python
# intentionally empty
```

**File**: `flask/modules/ai/tests/__init__.py` (new if absent)

```python
# intentionally empty
```

**File**: `flask/create_app.py` — add to `ENABLED_MODULES` list if absent (cite `flask/create_app.py:7-10`):

```python
ENABLED_MODULES = [
    ('modules.projects.routes', 'projects_bp'),
    ('modules.context.routes',  'context_bp'),
    ('modules.ai.routes',       'ai_bp'),        # ← add this line
]
```

**Verify**: `cd flask && python -c "from create_app import create_app; create_app()"` — no ImportError (the ai module import will fail until routes.py exists, so create it in Step 2 first).

---

### Step 2: Create `scan_prompt` pure function

**Action**: Create `flask/modules/ai/prompts/scan.py`. Ports `buildScanPrompt()` from `server.js:1245–1307`. Function takes the walker dict, returns a prompt string. No I/O, no module imports beyond stdlib.

**File**: `flask/modules/ai/prompts/scan.py` (new)

```python
"""Pure prompt function for POST /api/ai/text/scan.

Ports buildScanPrompt() from server.js:1245-1307.
INVARIANT: no I/O, no module imports outside stdlib.
INVARIANT: prompt must NOT mention writing files or output filenames —
  Claude CLI intercepts write-intent prompts with tool-permission stubs.
  Ported from server.js:1258-1261 comment.
"""
from __future__ import annotations
import os
from datetime import date


def scan_prompt(raw: dict) -> str:
    """Build the scan prompt from walker output.

    raw = {"tree": [...nodes], "sourceFiles": [...files], "entryPoints": {...}}
    """
    tree_lines = "\n".join(
        "  " * n["depth"]
        + ("\U0001f4c1 " if n["type"] == "dir" else "\U0001f4c4 ")
        + os.path.basename(n["path"])
        for n in raw["tree"]
    )
    files_section = "\n\n".join(
        f"### {f['path']} ({f['lines']} lines)\nFirst 10 lines:\n```\n{f['head']}\n```"
        for f in raw["sourceFiles"]
    )
    entries_section = "\n\n".join(
        f"### {name}\n```\n{content}\n```"
        for name, content in raw.get("entryPoints", {}).items()
    )
    today = date.today().isoformat()
    return (
        "You are an analyst summarizing a codebase for an AI code generation system."
        " You do NOT have file-system access."
        " Respond with markdown text only — no tool calls, no approval prompts, no preamble.\n\n"
        "## RAW DATA\n\n"
        f"### File Tree\n{tree_lines}\n\n"
        f"### Source Files\n{files_section}\n\n"
        f"### Entry Points\n{entries_section}\n\n"
        "## Respond with exactly this markdown document"
        " (fill in the placeholders, keep under 250 lines, terse and scannable):\n\n"
        f"# Codebase Context\n**Last scanned**: {today}\n\n"
        "## Active Workspace: {inferred project name}\n"
        "{1 sentence: what this project is}\n\n"
        "## Feature Modules\n"
        "For each feature module (bounded context), list:\n"
        "- **{name}**: {path} — {1-line purpose}\n"
        "  - Public interface: {exported symbols that other code imports}\n"
        "  - Tests: {path to spec file if exists}\n\n"
        "## Shared Services\n"
        "Same format — only services imported by multiple features.\n\n"
        "## Entry Points\n"
        "- {path}: {what it bootstraps}\n\n"
        "## Dependencies\n"
        "Group by purpose: UI framework, DB, AI, auth, testing, deploy.\n"
        "Only list key deps — skip @types, dev tools, small utils.\n\n"
        "## Patterns in Use\n"
        "Inferred from structure. Terse bullet list.\n\n"
        "Return the markdown document as your answer. Nothing else."
    )
```

**Verify**: `cd flask && python -c "from modules.ai.prompts.scan import scan_prompt; print(scan_prompt({'tree':[], 'sourceFiles':[], 'entryPoints':{}})[:40])"` — prints the first 40 chars starting with "You are".

---

### Step 3: Add scan route, walker, and refusal guard to `routes.py`

**Action**: If `flask/modules/ai/routes.py` does not exist, create it. If it exists (Task 1 or Tasks 2/3 already ran), append the scan-specific private functions and the `scan()` handler. Ports `walkProject` from `server/walker.js:18–72` and `looksLikeCliRefusal` from `server.js:1231–1243`.

**File**: `flask/modules/ai/routes.py` (create or append)

Full file content if creating from scratch (if appending, add only the `_IGNORE_DIRS` through `scan()` blocks, merging any already-present constants):

```python
"""AI text operations blueprint — Phase 2 route handlers.

Protocol per handler: validate → (context) → adapter → envelope.
All AI calls go through chain.adapter. Never import from chain.providers.*.
"""
from __future__ import annotations
import logging
import os

from flask import Blueprint, jsonify, request
from modules.chain import adapter as chain
from modules.context.service import write_context

from .prompts.scan import scan_prompt

logger = logging.getLogger(__name__)
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai/text")

# ── Walker constants — port of server/walker.js:4-16 ──────────────────────────

_IGNORE_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "dist", "www", "ios", "android",
    ".angular", "__pycache__", ".venv", "build", ".next", ".cache",
    "migrations",
})
_SOURCE_EXTS: frozenset[str] = frozenset({".ts", ".tsx", ".js", ".jsx", ".py"})
_ENTRY_FILES: list[str] = [
    "package.json", "requirements.txt", "pyproject.toml",
    "src/app/app.routes.ts", "src/app/shell/feature-registry.ts",
    "server/app.py", "angular.json", "capacitor.config.ts",
]

# ── Refusal markers — port of server.js:1233-1241 ─────────────────────────────

_REFUSAL_MARKERS: tuple[str, ...] = (
    "has not approved",
    "waiting for approval",
    "ready to overwrite",
    "i cannot write",
    "i can't write",
    "requires your approval",
)


def _walk(workspace: str, max_depth: int = 3) -> dict:
    """Stdlib os.walk port of server/walker.js:walkProject.

    Returns {"tree": [...], "sourceFiles": [...], "entryPoints": {...}}.
    No third-party deps. Depth counts from 0 at workspace root.
    """
    tree: list[dict] = []
    source_files: list[dict] = []
    entry_points: dict[str, str] = {}

    for ef in _ENTRY_FILES:
        full = os.path.join(workspace, ef)
        if os.path.isfile(full):
            try:
                with open(full, encoding="utf-8") as fh:
                    entry_points[ef] = fh.read()[:2000]
            except OSError:
                pass

    for dirpath, dirnames, filenames in os.walk(workspace):
        rel = os.path.relpath(dirpath, workspace)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= max_depth:
            dirnames.clear()
            continue
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORE_DIRS)
        if rel != ".":
            tree.append({"path": rel, "type": "dir", "depth": depth})
        for fname in sorted(filenames):
            if os.path.splitext(fname)[1] not in _SOURCE_EXTS:
                continue
            full = os.path.join(dirpath, fname)
            file_rel = os.path.relpath(full, workspace)
            try:
                with open(full, encoding="utf-8") as fh:
                    lines = fh.readlines()
                source_files.append({
                    "path": file_rel,
                    "lines": len(lines),
                    "head": "".join(lines[:10]),
                })
                tree.append({"path": file_rel, "type": "file", "depth": depth})
            except OSError:
                pass

    return {"tree": tree, "sourceFiles": source_files, "entryPoints": entry_points}


def _looks_like_cli_refusal(text: str) -> bool:
    """Port of server.js:looksLikeCliRefusal (lines 1231-1243).

    Detects Claude CLI tool-permission stubs before they are persisted as
    codebase.md content. Empty text is treated as a refusal.
    """
    if not text:
        return True
    head = text.strip()[:300].lower()
    return any(m in head for m in _REFUSAL_MARKERS)


# ── /scan route ───────────────────────────────────────────────────────────────

@ai_bp.post("/scan")
def scan():
    """POST /api/ai/text/scan — walk workspace, summarize with AI, persist.

    Body: {"workspacePath": "<absolute-path>"}
    200: {"content": "<markdown>", "latencyMs": <int>}
    400: workspacePath missing or not a directory
    502: AI returned a CLI permission stub; caller should retry
    """
    body = request.get_json(force=True) or {}
    workspace = body.get("workspacePath")
    if not workspace or not os.path.isdir(workspace):
        return jsonify({"error": "workspacePath required and must be an existing directory"}), 400

    raw = _walk(workspace)
    result = chain.generate(
        system=(
            "You are a codebase analyst."
            " Return only markdown text — no tool calls, no preamble."
        ),
        prompt=scan_prompt(raw),
    )

    if _looks_like_cli_refusal(result.text):
        logger.error("[Scan] CLI refusal detected — not persisting")
        return jsonify({
            "error": "AI returned a refusal response rather than content. Retry the scan.",
            "sample": result.text[:200],
        }), 502

    write_context("codebase", result.text)
    logger.info("[Scan] Persisted %d chars to codebase.md", len(result.text))
    return jsonify({"content": result.text, "latencyMs": result.latency_ms})
```

**Verify**: `cd flask && python -c "from modules.ai.routes import ai_bp, _walk, _looks_like_cli_refusal; print('ok')"` — prints `ok`.

---

### Step 4: Register blueprint in app factory (if Step 1 was skipped)

**Action**: Confirm `('modules.ai.routes', 'ai_bp')` is in `ENABLED_MODULES`. If it was added in Step 1, this is a no-op.

**File**: `flask/create_app.py` (cite `flask/create_app.py:7-10`)

**Verify**: `cd flask && python -c "from create_app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; assert '/api/ai/text/scan' in rules, rules; print('route registered')"` — prints `route registered`.

---

## 5. Tests

Framework: pytest + Flask test client. Pattern matches `flask/modules/chain/tests/test_adapter.py` (monkeypatch.setenv) and `flask/tests/test_context_files.py` (test client via conftest fixtures).

### `flask/tests/test_scan_route.py`

```python
"""Route integration tests for POST /api/ai/text/scan.

Uses Flask test client. Mock provider via CHAIN_PROVIDER=mock.
Covers: input validation, CLI-refusal guard, happy path, persistence.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from create_app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


# ── Input validation ──────────────────────────────────────────────────────────

def test_missingWorkspacePath_returns400(client):
    resp = client.post("/api/ai/text/scan", json={})
    assert resp.status_code == 400
    assert "workspacePath" in resp.get_json()["error"]


def test_nonexistentWorkspacePath_returns400(client):
    resp = client.post("/api/ai/text/scan", json={"workspacePath": "/tmp/does-not-exist-xyz99"})
    assert resp.status_code == 400
    assert "workspacePath" in resp.get_json()["error"]


def test_filePathInsteadOfDir_returns400(client, tmp_path):
    f = tmp_path / "somefile.txt"
    f.write_text("hello")
    resp = client.post("/api/ai/text/scan", json={"workspacePath": str(f)})
    assert resp.status_code == 400


# ── CLI-refusal guard ─────────────────────────────────────────────────────────

def test_cliRefusalText_returns502(client, tmp_path, monkeypatch):
    """Route returns 502 when adapter text matches a known refusal marker."""
    from modules.chain.types import ChainResult

    def mock_generate(system, prompt, **kwargs):
        return ChainResult(text="I cannot write files — waiting for approval.", latency_ms=10)

    monkeypatch.setattr("modules.ai.routes.chain.generate", mock_generate)
    resp = client.post("/api/ai/text/scan", json={"workspacePath": str(tmp_path)})
    assert resp.status_code == 502
    body = resp.get_json()
    assert "refusal" in body["error"].lower()
    assert "sample" in body
    assert len(body["sample"]) <= 200


def test_emptyAdapterText_returns502(client, tmp_path, monkeypatch):
    """Empty text from adapter (falsy check in guard) returns 502."""
    from modules.chain.types import ChainResult

    def mock_generate(system, prompt, **kwargs):
        return ChainResult(text="", latency_ms=5)

    monkeypatch.setattr("modules.ai.routes.chain.generate", mock_generate)
    resp = client.post("/api/ai/text/scan", json={"workspacePath": str(tmp_path)})
    assert resp.status_code == 502


def test_approvalRequiredMarker_returns502(client, tmp_path, monkeypatch):
    """'requires your approval' marker in head triggers guard."""
    from modules.chain.types import ChainResult

    def mock_generate(system, prompt, **kwargs):
        return ChainResult(
            text="This operation requires your approval before continuing.",
            latency_ms=5,
        )

    monkeypatch.setattr("modules.ai.routes.chain.generate", mock_generate)
    resp = client.post("/api/ai/text/scan", json={"workspacePath": str(tmp_path)})
    assert resp.status_code == 502


# ── Happy path ────────────────────────────────────────────────────────────────

def test_validWorkspace_returns200WithContentAndLatency(client, tmp_path, monkeypatch):
    """Valid workspace + mock provider returns 200, content string, latencyMs int."""
    monkeypatch.setattr("modules.ai.routes.write_context", lambda key, val: None)
    (tmp_path / "app.py").write_text("# entry\n")
    resp = client.post("/api/ai/text/scan", json={"workspacePath": str(tmp_path)})
    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body["content"], str)
    assert len(body["content"]) > 0
    assert isinstance(body["latencyMs"], int)
    assert body["latencyMs"] >= 0


def test_validWorkspace_persistsToCodebaseKey(client, tmp_path, monkeypatch):
    """Successful scan writes content to 'codebase' key via write_context."""
    written: dict[str, str] = {}

    def capture_write(key: str, content: str) -> None:
        written[key] = content

    monkeypatch.setattr("modules.ai.routes.write_context", capture_write)
    (tmp_path / "requirements.txt").write_text("flask\n")
    resp = client.post("/api/ai/text/scan", json={"workspacePath": str(tmp_path)})
    assert resp.status_code == 200
    assert "codebase" in written
    assert len(written["codebase"]) > 0


# ── Refusal guard unit tests (via private import) ─────────────────────────────

def test_looksLikeCliRefusal_detectsAllKnownMarkers():
    from modules.ai.routes import _looks_like_cli_refusal

    assert _looks_like_cli_refusal("I cannot write to that location.")
    assert _looks_like_cli_refusal("I can't write to the filesystem.")
    assert _looks_like_cli_refusal("This action requires your approval.")
    assert _looks_like_cli_refusal("Waiting for approval before proceeding.")
    assert _looks_like_cli_refusal("Has not approved this file operation.")
    assert _looks_like_cli_refusal("Ready to overwrite the file, please confirm.")
    assert _looks_like_cli_refusal("")


def test_looksLikeCliRefusal_acceptsValidMarkdown():
    from modules.ai.routes import _looks_like_cli_refusal

    valid = "# Codebase Context\n**Last scanned**: 2026-04-23\n\n## Active Workspace: spec-doc\n"
    assert not _looks_like_cli_refusal(valid)


# ── Walker unit tests ─────────────────────────────────────────────────────────

def test_walk_ignoresStandardExcludedDirs(tmp_path):
    from modules.ai.routes import _walk

    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.py").write_text("# should be ignored\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config.py").write_text("# should be ignored\n")
    (tmp_path / "app.py").write_text("# included\n")
    result = _walk(str(tmp_path))
    paths = [f["path"] for f in result["sourceFiles"]]
    assert any("app.py" in p for p in paths), "app.py must be included"
    assert not any("node_modules" in p for p in paths), "node_modules must be excluded"
    assert not any(".git" in p for p in paths), ".git must be excluded"


def test_walk_readsEntryPointFilesUpTo2000Chars(tmp_path):
    from modules.ai.routes import _walk

    long_content = "x" * 3000
    (tmp_path / "requirements.txt").write_text(long_content)
    result = _walk(str(tmp_path))
    assert "requirements.txt" in result["entryPoints"]
    assert len(result["entryPoints"]["requirements.txt"]) == 2000


def test_walk_capturesFirst10LinesOfSourceFiles(tmp_path):
    from modules.ai.routes import _walk

    content = "\n".join(f"line {i}" for i in range(20))
    (tmp_path / "big.py").write_text(content)
    result = _walk(str(tmp_path))
    src = next(f for f in result["sourceFiles"] if "big.py" in f["path"])
    head_lines = [ln for ln in src["head"].split("\n") if ln.strip()]
    assert len(head_lines) == 10, f"expected 10 lines, got {len(head_lines)}: {head_lines}"
    assert head_lines[0] == "line 0"
    assert head_lines[9] == "line 9"
```

### `flask/modules/ai/tests/test_scan_prompts.py`

```python
"""Unit tests for scan_prompt — no HTTP fixture, no I/O.

Prompt purity: function takes dict, returns str. Assertions on content shape
and the write-intent invariant (must not trigger Claude CLI tool interception).
"""
from modules.ai.prompts.scan import scan_prompt


def test_scanPrompt_includesFileTreeSection():
    raw = {
        "tree": [{"path": "src", "type": "dir", "depth": 0}],
        "sourceFiles": [],
        "entryPoints": {},
    }
    result = scan_prompt(raw)
    assert "File Tree" in result
    assert "src" in result


def test_scanPrompt_includesSourceFilesWithLineCount():
    raw = {
        "tree": [],
        "sourceFiles": [{"path": "app.py", "lines": 42, "head": "# entry\n"}],
        "entryPoints": {},
    }
    result = scan_prompt(raw)
    assert "app.py" in result
    assert "42 lines" in result
    assert "# entry" in result


def test_scanPrompt_includesEntryPoints():
    raw = {
        "tree": [],
        "sourceFiles": [],
        "entryPoints": {"package.json": '{"name": "my-app"}'},
    }
    result = scan_prompt(raw)
    assert "package.json" in result
    assert "my-app" in result


def test_scanPrompt_doesNotContainWriteIntent():
    """Core invariant: prompt must not trigger Claude CLI write-tool interception.

    Phrases that cause the CLI to issue a tool-permission stub rather than
    returning text content. Ported from server.js:1258-1261 comment.
    """
    raw = {"tree": [], "sourceFiles": [], "entryPoints": {}}
    result = scan_prompt(raw).lower()
    for forbidden in ("write to", "save to", "output file", "create file", "write the file"):
        assert forbidden not in result, f"forbidden phrase found: {forbidden!r}"


def test_scanPrompt_returnsString():
    raw = {"tree": [], "sourceFiles": [], "entryPoints": {}}
    result = scan_prompt(raw)
    assert isinstance(result, str)
    assert len(result) > 100
```

---

## 6. Commit Plan

One commit per logical unit. Executor must prefix commit body with `Deviations:` if any step differs from this guide.

1. **`feat(ai/scan): scaffold modules/ai if absent`** — `flask/modules/ai/__init__.py`, `flask/modules/ai/prompts/__init__.py`, `flask/modules/ai/tests/__init__.py`, `flask/create_app.py` — create package inits and register `ai_bp` in ENABLED_MODULES. Skip if Task 1 already merged these.

2. **`feat(ai/scan): add scan_prompt pure function`** — `flask/modules/ai/prompts/scan.py` — ports `buildScanPrompt()` from `server.js:1245–1307`; no I/O, no write-intent phrases.

3. **`feat(ai/scan): add POST /api/ai/text/scan route + walker + refusal guard`** — `flask/modules/ai/routes.py` — `_walk()` ports `server/walker.js:18–72`; `_looks_like_cli_refusal()` ports `server.js:1231–1243`; `scan()` handler calls adapter, guard, write_context.

4. **`test(ai/scan): route integration, prompt purity, and guard unit tests`** — `flask/tests/test_scan_route.py`, `flask/modules/ai/tests/test_scan_prompts.py` — 14 tests covering validation, refusal, happy path, walker, prompt invariants.

---

## 7. Verification

```bash
cd flask && python -m pytest --tb=short -q
```

**Expected delta**: N → N+14 passing. Zero pre-existing tests broken.

Spot-check the route is reachable:

```bash
cd flask && python -c "
from create_app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
assert '/api/ai/text/scan' in rules, f'missing — rules: {rules}'
print('✓ /api/ai/text/scan registered')
"
```

---

## 8. Rollback

**Per-step**: each commit is independently revertible. `git revert <sha>` — no commit has side effects beyond the local working tree (no push, no DB writes, no file system changes outside the repo).

**Per-branch**: if verification fails and the branch is unrecoverable, `git reset --hard <pre-task-sha>` to the SHA recorded in pre-flight, then delete any created files manually. `git stash drop` if a stash was taken in pre-flight.

---

## 9. Deviations Allowed

- **`flask/modules/ai/routes.py` already exists with conflicting content** — do not overwrite; append only the scan-specific constants and functions that are absent; log in commit body with a `Deviations:` line describing what was already present.
- **`CHAIN_PROVIDER` env var is not "mock" in the test environment** — monkeypatch in each test is the correct fix; do not change the default in `adapter.py`.
- **`write_context` signature differs from `flask/modules/context/service.py`** — re-read the service; adapt the call; log the deviation.
- **Test framework mismatch** — match whatever framework is in use (pytest confirmed by existing test files); translate assertions silently; note in commit body.
- **Side-effect required** (push, publish, schema change) — STOP, mark `[REQUIRES APPROVAL]`, and surface to user before proceeding.
- **Step N simplification** — if a step unlocks an obvious simplification for the next step, take it and log the deviation.

---

## 10. Out of Scope

This task wires the scan endpoint and its guard only. Everything below has been explicitly deferred in the architecture doc and must not be absorbed into this task.

- **Other six route handlers** (`/rewrite`, `/generate`, `/iterate`, `/generate-spec`, `/review`, `/lint-braindump`) — belong to Tasks 2 and 3; adding them here expands blast radius without authorization.
- **Streaming scan results** — no `text/event-stream` consumer exists in `src/app/services/ai.service.ts`; infrastructure before the caller is present.
- **Rate limiting / token counting** — one consumer today; re-scope when a second product lands or a usage cap is needed.
- **Partial-result caching** — the guard fires and the caller corrects the prompt; the 40-line port budget explicitly excludes this.
- **Retry / backoff in the route** — the `anthropic` SDK already handles `max_retries=2, timeout=60` at the provider layer; wrapping it adds application-level machinery over working infrastructure.
- **Walker as a standalone Python module** (`flask/modules/ai/walker.py`) — one consumer today; extract when a second route needs it.
- **`/api/ai/implement`** — SSE streaming + Docker container execution; no Angular caller in the normal editor flow; re-scope in Phase 3.

**Rule for the executor**: if a change appears helpful but is in this list, STOP, log it in the commit body as a flagged deviation, and do not implement it.

---

## Related Documents

- [Solution Architecture](./architecture.md) — CLI-refusal guard rationale, route protocol, scan design decisions
- [Epic](./epic.md) — Task 4 scope and port budget
- [Timeline](./timeline.md) — Update status to Done after verification passes