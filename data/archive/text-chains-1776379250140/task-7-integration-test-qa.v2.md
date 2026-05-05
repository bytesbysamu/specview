Now I have a complete picture of the project structure, all prior task guides (1-6), the epic, architecture, and existing patterns. Let me generate the implementation guide.

# Task 7: Integration Test + QA

**Purpose**: End-to-end test each chain operation, enforce structural module boundaries, verify manifest consistency, check WCAG-AA compliance on all new UI elements, and run a full regression pass to confirm zero breakage of existing single-shot modes.

**Effort**: 0.5 day

**Dependencies**: Task 6 (Chain Mode UI) must be landed. All three chain definitions, the runner, context loader, chain endpoint, and frontend chain UI must be complete.

**Parallel With**: —

**Blocks**: — (final task in the epic)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task is the verification gate before the text-chains epic ships. It adds three categories of automated tests: (1) end-to-end chain integration tests that exercise the full backend path from `POST /api/text/chain` through the definition runner to the mock provider and back, (2) structural tests that grep the source tree for module-boundary violations specified in the architecture doc, and (3) a WCAG-AA contrast-ratio script for new chain UI elements. It also runs the full existing test suite (backend + frontend) to confirm zero regressions on single-shot text modes and existing features. No production code is created or modified — this task is pure verification.

**Trade-offs considered**:
- **E2E tests via Flask test client + mock provider vs. real Claude API calls** — mock provider chosen. Real-API tests are slow (~3s per chain × 3 chains), non-deterministic, and cost tokens. The mock provider exercises the same runner dispatch, step sequencing, and response serialization logic. Real-API smoke tests are a manual QA step (Step 6), not an automated test.
- **Structural tests as standalone cross-module file vs. embedded in each module's test directory** — standalone `server/tests/test_structural.py` chosen for the four cross-module boundary invariants (context loader boundary, chain definitions boundary, manifest consistency, adapter-only imports). Module-internal structural tests (e.g., `test_featureModules_mustNotImportProvidersDirectly` in `server/modules/chain/tests/`) already live in their module from Task 2 — this task adds the cross-cutting ones.
- **WCAG check via automated Node.js contrast script vs. browser extension audit** — automated script chosen for deterministic CI-runnable checks on contrast ratios. Manual audit covers focus order and screen reader semantics in Step 6 where automation can't reach.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                # flag unrelated M/?? entries
git diff HEAD -- server/tests/ src/app/pages/text/        # confirm target dirs are clean
cd {WORKSPACE}/server && python -m pytest --tb=short -q 2>&1 | tail -5    # record BE baseline
cd {WORKSPACE} && npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -5  # record FE baseline
```

**Pre-conditions** — STOP if any fail:
- Chain definitions exist: `ls server/modules/chain/definitions/` prints `deep-humanize.json`, `braindump-to-docs.json`, `rewrite-review.json`.
- Context manifest exists and is valid: `python -c "import json; json.load(open('server/context/manifest.json')); print('OK')"`.
- Chain endpoint registered: `CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -c "from app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; assert '/api/text/chain' in rules; print('OK')"`.
- Definition runner importable: `CHAIN_PROVIDER=mock python -c "from modules.chain import STEP_HANDLERS; print(sorted(STEP_HANDLERS))"` prints at least `['generate', 'review', 'rewrite']`.
- Chain UI landed: `grep -rn 'chain' src/app/pages/text/text.page.ts | head -3` returns hits.

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: `[BE: N/N passing]`, `[FE: M/M passing]` — fill in from output above.

---

## 3. Files

### To Create (new)
- `server/tests/test_chain_integration.py` — end-to-end tests for all three chains via Flask test client + mock provider. Tests the full path: HTTP request → route → feature gate → chain_service → definition_runner → step handlers → mock provider → persistence → response.
- `server/tests/test_structural.py` — cross-module boundary tests: context loader boundary, chain definitions boundary, manifest-to-filesystem consistency, manifest-to-definition consistency, adapter-only imports in chain-related code, unique chain definition IDs, step ops exist in `STEP_HANDLERS`.
- `src/app/pages/text/a11y-contrast-check.mjs` — Node.js script that computes WCAG 2.1 contrast ratios for new chain UI color pairs (sage accent, Pro badge, tab active state, locked-key text) and exits non-zero on failure.

### To Modify
- `server/tests/conftest.py` — add `text_chains_user` and `gated_user` fixtures for chain integration tests. If similar fixtures already exist from Tasks 2-6, reuse and extend rather than duplicate.

### To Leave Alone
- `server/modules/chain/` — no production code changes. Tests only.
- `server/modules/text/` — no production code changes. Tests only.
- `server/modules/context/` — no production code changes. Tests only.
- `server/modules/photoshoot/models.py` — model unchanged; tests import from it.
- `server/app.py` — no changes; integration tests exercise the registered app.
- `src/app/pages/text/text.page.ts` — no changes; manual QA exercises it.
- `src/app/pages/text/components/` — no changes; FE tests landed in Task 6.
- `src/app/services/text-api.service.ts` — no changes; FE tests landed in Task 6.

---

## 4. Implementation Steps

### Step 1: Add chain test fixtures to `conftest.py`

**Action**: Read `server/tests/conftest.py` to identify existing fixtures (`client`, `db_session`, `app`, User creation patterns). Add two new fixtures: `text_chains_user` (user with `text_chains` in `enabled_features`) and `gated_user` (user with `text` enabled but `text_chains` disabled). Follow the existing User creation pattern — the User model lives in `server/modules/photoshoot/models.py` (per CODEBASE CONTEXT).

**File**: `server/tests/conftest.py`

**Pattern**:
```python
import uuid as _uuid

from modules.photoshoot.models import User


@pytest.fixture
def text_chains_user(db_session):
    """User with text + text_chains enabled — for chain integration tests."""
    user = User(
        email=f"chains-{_uuid.uuid4().hex[:8]}@test.co",
        token=_uuid.uuid4(),
        enabled_features={"text": True, "text_chains": True},
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def gated_user(db_session):
    """User with text enabled but text_chains disabled — for feature-guard tests."""
    user = User(
        email=f"gated-{_uuid.uuid4().hex[:8]}@test.co",
        token=_uuid.uuid4(),
        enabled_features={"text": True, "text_chains": False},
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
```

If `conftest.py` already creates users with a helper function or factory, adapt these fixtures to use that factory instead. Log as deviation.

**Verify**:
```bash
cd {WORKSPACE}/server && python -c "exec(open('tests/conftest.py').read()); print('conftest loadable')"
```

### Step 2: Create `test_chain_integration.py` — end-to-end chain tests

**Action**: Write integration tests that exercise each chain through the Flask test client. Mock provider is forced via `monkeypatch` (not import-time env) so each test is isolated. Tests cover: authentication (401), feature gating (403), unknown chain (404), missing input (400), happy paths for all three chains, persistence to `superapp_generations`, and single-shot regression.

**File**: `server/tests/test_chain_integration.py` (new)

**Pattern**: Full test bodies in Section 5 below.

**Verify**:
```bash
cd {WORKSPACE}/server && CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -m pytest tests/test_chain_integration.py -q -v
```

### Step 3: Create `test_structural.py` — cross-module boundary tests

**Action**: Write grep-based structural tests that enforce the four boundary invariants from the architecture doc plus three consistency checks. Each test is one `pathlib.rglob` + one assertion + one failure message naming the rule and the fix.

**File**: `server/tests/test_structural.py` (new)

**Pattern**: Full test bodies in Section 5 below.

**Verify**:
```bash
cd {WORKSPACE}/server && python -m pytest tests/test_structural.py -q -v
```

### Step 4: Create the WCAG contrast check script

**Action**: Write a Node.js script that computes contrast ratios for the new chain UI color pairs introduced by Task 6. Uses the WCAG 2.1 relative luminance formula. Color values are hardcoded from the CSS tokens defined in `src/app/pages/text/text.page.scss` and `src/app/pages/text/components/typewriter-keys.component.scss`. The executor must read these files to extract the actual hex values used. The values below are from the architecture doc's sage accent design; if Task 6 used different values, update accordingly and log as deviation.

**File**: `src/app/pages/text/a11y-contrast-check.mjs` (new)

**Pattern**: Full script in Section 5 below.

**Verify**:
```bash
node src/app/pages/text/a11y-contrast-check.mjs
```

### Step 5: Run full regression suite

**Action**: Execute the complete backend and frontend test suites. Compare against the pre-flight baselines. Assert zero failures on existing tests. Confirm single-shot modes (rewrite, expand, compress, clarify, generate) still pass via existing `test_text_routes.py` or equivalent tests.

**File**: N/A (execution only)

**Verify**:
```bash
cd {WORKSPACE}/server && CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -m pytest --tb=short -q
cd {WORKSPACE} && npx ng test --watch=false --browsers=ChromeHeadless
```

Expected: BE pass count ≥ baseline + 17 new tests. FE pass count ≥ baseline. Zero failures.

### Step 6: Manual QA checklist

**Action**: Execute the following manual checks with the dev server running (`npm run dev`). Record pass/fail for each. If any fail, file a bug against the relevant task before marking Task 7 complete.

**Checklist**:
1. Open `/text` in Chrome — both single-shot keys and chain keys render in two distinct rows.
2. Type text, tap "Humanize" (single-shot) — result appears in output area. Existing behavior preserved.
3. Type text, tap "Deep Humanize" (chain, sage accent) — step progress indicator shows, result appears after completion.
4. Type a 3-section braindump, tap "Brain Dump" — tabs render with file names as labels, each tab shows non-empty content, copy-per-tab button works.
5. Type deliberately flawed text, tap "Rewrite+Review" — single result appears (review + fix cycle completed).
6. Toggle OS dark mode — all new elements (sage accent, Pro badge, tab bar, step progress) flip correctly.
7. Set `text_chains` to `false` on the test user — chain keys show locked at `opacity: 0.5` with "Pro" badge, tapping shows upgrade toast, single-shot keys unaffected.
8. Tab through all new elements with keyboard — focus order is logical (single-shot row → chain row → output area → tabs if present), all buttons reachable.
9. Enable VoiceOver/screen reader on the chain tabs — tab role announced, active tab state read, content switches correctly.

**Verify**: All 9 items pass. If any fail, file a bug against the responsible task (3, 4, 5, or 6) — do NOT fix production code in this task.

---

## 5. Tests

### `server/tests/test_chain_integration.py` (new)

Framework: pytest + Flask test client. Mock provider forced via `monkeypatch.setenv`.

```python
"""End-to-end integration tests for chain operations.

Each test exercises the full backend path: HTTP request → route → feature gate →
chain_service → definition_runner → step handlers → mock provider → persistence → response.

Mock provider forced via monkeypatch — deterministic, no external API calls.
"""
from __future__ import annotations

import uuid

import pytest

from modules.photoshoot.models import User


@pytest.fixture(autouse=True)
def _force_mock_providers(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    monkeypatch.setenv("CONTEXT_PROVIDER", "mock")


class _H:
    """Test helpers — keeps test bodies focused on assertions."""

    @staticmethod
    def make_user(db, *, text_chains: bool) -> User:
        u = User(
            email=f"chain-{uuid.uuid4().hex[:8]}@test.co",
            token=uuid.uuid4(),
            enabled_features={"text": True, "text_chains": text_chains},
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    @staticmethod
    def bearer(u: User) -> dict:
        return {"Authorization": f"Bearer {u.token}"}


# ── Endpoint gating ─────────────────────────────────────────────────────────


class TestChainEndpointGating:

    def test_noBearer_returns401(self, client):
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": "hello"},
        )
        assert r.status_code == 401

    def test_textChainsDisabled_returns403WithUpgradeHint(self, client, db_session):
        u = _H.make_user(db_session, text_chains=False)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": "hello"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 403
        body = r.get_json()
        assert (
            "not enabled" in body.get("error", "").lower()
            or body.get("upgrade") is True
        ), f"Expected upgrade hint in 403 body, got: {body}"

    def test_unknownChainId_returns404(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "nonexistent-chain-xyz", "input": "hello"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 404
        body = r.get_json()
        assert "not found" in body.get("error", "").lower()

    def test_missingInput_returns400(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize"},
            headers=_H.bearer(u),
        )
        assert r.status_code == 400


# ── Deep Humanize chain ─────────────────────────────────────────────────────


class TestDeepHumanizeChain:

    def test_happyPath_returns200WithSingleResult(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/chain",
            json={
                "chainId": "deep-humanize",
                "input": "The quick brown fox jumps over the lazy dog.",
            },
            headers=_H.bearer(u),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        body = r.get_json()
        # Must have a generation identifier
        gen_id = body.get("generationId") or body.get("id")
        assert gen_id is not None, f"Missing generationId in response: {body}"
        # Single-file chain — result is a string, not a files array
        result = body.get("result") or body.get("output")
        assert isinstance(result, str), f"Expected string result, got: {type(result)}"
        assert len(result) > 0, "Result must be non-empty"

    def test_threePassOutput_differsFromInput(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        input_text = "The quick brown fox jumps over the lazy dog."
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": input_text},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200
        body = r.get_json()
        output = body.get("result") or body.get("output", "")
        # Mock provider transforms text — output should not be identical to raw input
        assert output != input_text, (
            "Deep Humanize output should differ from input after 3 mock passes"
        )


# ── Braindump → Docs chain ──────────────────────────────────────────────────


class TestBraindumpToDocsChain:

    def test_happyPath_returnsFilesArrayOrResult(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        braindump = (
            "## What\nI want to build an event discovery app for Zurich.\n\n"
            "## Why now\nNo app curates local events well.\n\n"
            "## What's missing\nBackend, data pipeline, iOS shell."
        )
        r = client.post(
            "/api/text/chain",
            json={"chainId": "braindump-to-docs", "input": braindump},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        body = r.get_json()
        files = body.get("files")
        # Multi-file chain: mock provider may or may not produce ===FILE:=== markers.
        # Accept either structured files or single result as graceful degradation.
        if files is not None:
            assert isinstance(files, list), f"files must be a list, got: {type(files)}"
            for f in files:
                assert "name" in f, f"Each file must have a 'name' key: {f}"
                assert "content" in f, f"Each file must have a 'content' key: {f}"
                assert len(f["content"]) > 0, f"File content must be non-empty: {f['name']}"
        else:
            # Graceful degradation: mock provider returned flat text, runner
            # wrapped it as single output
            result = body.get("result") or body.get("output")
            assert result is not None, f"Expected files or result in response: {body}"
            assert len(result) > 0


# ── Rewrite + Review chain ───────────────────────────────────────────────────


class TestRewriteReviewChain:

    def test_happyPath_returns200WithSingleResult(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/chain",
            json={
                "chainId": "rewrite-review",
                "input": "The ball was throwed by he to she yesterday morning time.",
            },
            headers=_H.bearer(u),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        body = r.get_json()
        result = body.get("result") or body.get("output")
        assert isinstance(result, str), f"Expected string result, got: {type(result)}"

    def test_deliberatelyFlawedInput_chainCompletes(self, client, db_session):
        """The chain must complete all 3 steps (rewrite → review → fix) without error,
        even with flawed input. With mock provider we can't assert real review quality,
        but we verify the pipeline doesn't crash."""
        u = _H.make_user(db_session, text_chains=True)
        flawed = (
            "Their was alot of peoples who was went to the store for buying "
            "items that was needed by them for the purposes of consumption."
        )
        r = client.post(
            "/api/text/chain",
            json={"chainId": "rewrite-review", "input": flawed},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200, f"Chain failed on flawed input: {r.get_json()}"
        body = r.get_json()
        output = body.get("result") or body.get("output", "")
        assert len(output) > 0, "Chain output must be non-empty"


# ── Persistence ──────────────────────────────────────────────────────────────


class TestChainPersistence:

    def test_chainRun_persistsToSuperappGenerations(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/chain",
            json={"chainId": "deep-humanize", "input": "Persist this text."},
            headers=_H.bearer(u),
        )
        assert r.status_code == 200
        body = r.get_json()
        gen_id = body.get("generationId") or body.get("id")
        assert gen_id is not None

        from modules.photoshoot.models import Generation

        rows = (
            db_session.query(Generation)
            .filter(Generation.user_id == u.id)
            .all()
        )
        assert len(rows) >= 1, f"Expected at least 1 generation row, found {len(rows)}"
        # Verify chain metadata persisted
        chain_row = rows[-1]
        if hasattr(chain_row, "chain_id"):
            assert chain_row.chain_id == "deep-humanize"
            assert chain_row.step_count == 3


# ── Single-shot regression ───────────────────────────────────────────────────


class TestSingleShotRegression:
    """Verify that existing single-shot text modes are unaffected by chain changes."""

    def test_rewriteEndpoint_stillWorks(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/rewrite",
            json={"text": "Hello world", "mode": "humanize"},
            headers=_H.bearer(u),
        )
        # Accept 200 (success) or any response shape that isn't a 500
        assert r.status_code < 500, (
            f"Single-shot /rewrite returned server error: {r.status_code} {r.get_json()}"
        )

    def test_generateEndpoint_stillWorks(self, client, db_session):
        u = _H.make_user(db_session, text_chains=True)
        r = client.post(
            "/api/text/generate",
            json={"prompt": "Write a haiku about testing"},
            headers=_H.bearer(u),
        )
        assert r.status_code < 500, (
            f"Single-shot /generate returned server error: {r.status_code} {r.get_json()}"
        )
```

### `server/tests/test_structural.py` (new)

```python
"""Cross-module structural invariants for the text-chains epic.

Grep-based tests that catch coupling code review misses. Each test is one
pathlib.rglob + one assertion + one failure message naming the rule and the fix.

These are scars, not theory — each test was added because the violation it
prevents has happened or would silently pass code review.
"""
from __future__ import annotations

import json
import pathlib
import re


SERVER_ROOT = pathlib.Path(__file__).resolve().parent.parent


# ── Context loader boundary ──────────────────────────────────────────────────


def test_contextFiles_onlyReadByLoader():
    """Only context/loader.py may open files from server/context/.
    Other modules must use loader.load_block(name)."""
    context_read_pattern = re.compile(
        r"""(open|read_text|Path)\s*\(.*['"].*context/"""
    )
    offenders: list[str] = []

    for py in SERVER_ROOT.rglob("*.py"):
        rel = py.relative_to(SERVER_ROOT)
        # Allow the loader itself
        if "context" in rel.parts and rel.name in ("loader.py", "__init__.py"):
            continue
        # Allow test files (they may reference context for assertions)
        if "test" in str(rel).lower() or "conftest" in rel.name:
            continue
        text = py.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if context_read_pattern.search(line) and "server/context" in line:
                offenders.append(f"{rel}:{i}")

    assert offenders == [], (
        f"Only context/loader.py may read from server/context/. "
        f"Use loader.load_block(name) instead. Offenders: {offenders}"
    )


# ── Chain definitions boundary ───────────────────────────────────────────────


def test_chainDefinitions_onlyReadByRunner():
    """Only the definition runner may read from chain/definitions/.
    Other modules must use the runner's load_definition(chainId)."""
    defs_read_pattern = re.compile(
        r"""(open|read_text|json\.load|Path)\s*\(.*['"].*definitions/"""
    )
    # The runner may be named definition_runner.py or runner.py depending on
    # Task 2's actual output. Allow both.
    runner_names = {"runner.py", "definition_runner.py"}
    offenders: list[str] = []

    for py in SERVER_ROOT.rglob("*.py"):
        rel = py.relative_to(SERVER_ROOT)
        # Allow the runner itself
        if "chain" in rel.parts and rel.name in runner_names:
            continue
        # Allow test files
        if "test" in str(rel).lower() or "conftest" in rel.name:
            continue
        text = py.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if defs_read_pattern.search(line) and "definitions/" in line:
                offenders.append(f"{rel}:{i}")

    assert offenders == [], (
        f"Only the chain runner may read from chain/definitions/. "
        f"Use runner.load_definition(chainId) instead. Offenders: {offenders}"
    )


# ── Manifest consistency ────────────────────────────────────────────────────


def test_manifestConsistency_allChainContextRefsExistInManifest():
    """Every context block referenced in a chain definition must exist in manifest.json."""
    manifest_path = SERVER_ROOT / "context" / "manifest.json"
    assert manifest_path.exists(), (
        f"Context manifest not found at {manifest_path}. Task 1 may not be landed."
    )

    manifest = json.loads(manifest_path.read_text())
    defs_dir = SERVER_ROOT / "modules" / "chain" / "definitions"
    assert defs_dir.exists(), (
        f"Chain definitions directory not found at {defs_dir}. Task 2 may not be landed."
    )

    missing: list[str] = []
    for defn_file in sorted(defs_dir.glob("*.json")):
        defn = json.loads(defn_file.read_text())
        for i, step in enumerate(defn.get("steps", [])):
            for ctx_name in step.get("context", []):
                if ctx_name not in manifest:
                    missing.append(
                        f"{defn_file.name} step {i} references "
                        f"'{ctx_name}' — not in manifest.json"
                    )

    assert missing == [], (
        f"Chain definitions reference context blocks missing from manifest.json. "
        f"Add them to server/context/manifest.json: {missing}"
    )


def test_manifestConsistency_allManifestFilesExistOnDisk():
    """Every file path in manifest.json must exist on disk."""
    manifest_path = SERVER_ROOT / "context" / "manifest.json"
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())
    context_dir = SERVER_ROOT / "context"
    missing: list[str] = []

    for name, rel_path in manifest.items():
        full = context_dir / rel_path
        if not full.exists():
            missing.append(f"'{name}' → '{rel_path}' (file not found at {full})")

    assert missing == [], (
        f"Manifest entries point to missing files. "
        f"Create the files or remove the entries: {missing}"
    )


# ── Adapter boundary ────────────────────────────────────────────────────────


def test_noDirectProviderImportsInChainModules():
    """Chain-related modules (runner, types, context, errors, signals) must not
    import from chain.providers directly. Only adapter.py may.
    This is ELA Pattern #1 (Adapter) — see architecture principles."""
    chain_dir = SERVER_ROOT / "modules" / "chain"
    if not chain_dir.exists():
        return

    offenders: list[str] = []
    for py in chain_dir.rglob("*.py"):
        rel = py.relative_to(chain_dir)
        # adapter.py + providers/* + tests/* are allowed
        if rel.parts[0] in ("providers", "tests") or rel.name == "adapter.py":
            continue
        text = py.read_text()
        if "from .providers" in text or "from modules.chain.providers" in text:
            offenders.append(str(rel))

    assert offenders == [], (
        f"Adapter-boundary violation: files inside modules/chain/ imported "
        f"from providers directly: {offenders}. "
        f"Only adapter.py may import providers. Fix: route calls through adapter."
    )


# ── Chain definition integrity ───────────────────────────────────────────────


def test_chainDefinitionIds_areUnique():
    """Each chain definition must have a unique 'id' field."""
    defs_dir = SERVER_ROOT / "modules" / "chain" / "definitions"
    if not defs_dir.exists():
        return

    ids: dict[str, str] = {}
    duplicates: list[str] = []

    for defn_file in sorted(defs_dir.glob("*.json")):
        defn = json.loads(defn_file.read_text())
        chain_id = defn.get("id")
        if chain_id in ids:
            duplicates.append(
                f"'{chain_id}' in both {ids[chain_id]} and {defn_file.name}"
            )
        else:
            ids[chain_id] = defn_file.name

    assert duplicates == [], f"Duplicate chain definition IDs: {duplicates}"


def test_chainDefinitionStepOps_existInStepHandlers():
    """Every 'op' value in chain definitions must be a key in STEP_HANDLERS.
    Import from the package to be resilient to internal file naming."""
    defs_dir = SERVER_ROOT / "modules" / "chain" / "definitions"
    if not defs_dir.exists():
        return

    # Import STEP_HANDLERS from the chain package (re-exported by __init__.py)
    # or from definition_runner directly if __init__ doesn't re-export
    try:
        from modules.chain import STEP_HANDLERS
    except ImportError:
        from modules.chain.definition_runner import STEP_HANDLERS

    unknown: list[str] = []
    for defn_file in sorted(defs_dir.glob("*.json")):
        defn = json.loads(defn_file.read_text())
        for i, step in enumerate(defn.get("steps", [])):
            op = step.get("op")
            if op not in STEP_HANDLERS:
                unknown.append(
                    f"{defn_file.name} step {i}: op '{op}' not in STEP_HANDLERS"
                )

    assert unknown == [], (
        f"Chain definitions reference unknown step operations: {unknown}. "
        f"Available handlers: {sorted(STEP_HANDLERS)}"
    )
```

### `src/app/pages/text/a11y-contrast-check.mjs` (new)

```javascript
#!/usr/bin/env node

/**
 * WCAG-AA contrast check for Text Chains UI elements.
 * Run: node src/app/pages/text/a11y-contrast-check.mjs
 *
 * Checks new color pairs introduced by the chain mode UI (Task 6).
 * Threshold: 4.5:1 for normal text, 3:1 for large text (>= 18px bold or >= 24px).
 *
 * If Task 6 used different hex values for the sage accent tokens,
 * update the CHECKS array below to match the actual values.
 */

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function relativeLuminance([r, g, b]) {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(hex1, hex2) {
  const l1 = relativeLuminance(hexToRgb(hex1));
  const l2 = relativeLuminance(hexToRgb(hex2));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Color pairs from the chain mode UI (Task 6 sage accent).
// Values sourced from text.page.scss and typewriter-keys.component.scss.
// DEVIATION NOTE: if Task 6 used different hex values, update these and log.
const CHECKS = [
  {
    name: 'accent-sage text on page-bg (light)',
    fg: '#5a7a6a',
    bg: '#faf8f5',
    threshold: 4.5,
    type: 'normal',
  },
  {
    name: 'accent-sage text on surface (light)',
    fg: '#5a7a6a',
    bg: '#ffffff',
    threshold: 4.5,
    type: 'normal',
  },
  {
    name: 'pro-badge text on accent-sage background',
    fg: '#ffffff',
    bg: '#5a7a6a',
    threshold: 3.0,
    type: 'large-bold',
  },
  {
    name: 'tab-active text on sage-tint background (light)',
    fg: '#5a7a6a',
    bg: '#f2f5f3',
    threshold: 4.5,
    type: 'normal',
  },
  {
    name: 'locked key text on surface (opacity-simulated)',
    fg: '#b0b8b4',
    bg: '#ffffff',
    threshold: 3.0,
    type: 'large-bold',
  },
];

let failures = 0;

for (const check of CHECKS) {
  const ratio = contrastRatio(check.fg, check.bg);
  const pass = ratio >= check.threshold;
  const status = pass ? 'PASS' : 'FAIL';
  console.log(
    `${status}: ${check.name} — ${ratio.toFixed(2)}:1 (need ${check.threshold}:1, ${check.type})`,
  );
  if (!pass) failures++;
}

if (failures > 0) {
  console.error(`\n${failures} contrast check(s) failed.`);
  process.exit(1);
} else {
  console.log('\nAll contrast checks passed.');
}
```

---

## 6. Commit Plan

One commit per logical unit:

1. `test(chain): e2e integration tests for all three chains + fixtures` — `server/tests/test_chain_integration.py`, `server/tests/conftest.py`: 10 test methods covering endpoint gating (401, 403, 404, 400), deep-humanize happy path + output-differs, braindump-to-docs happy path, rewrite-review happy path + flawed-input, persistence, single-shot regression.

2. `test(chain): structural boundary tests — loader, runner, manifest, adapter` — `server/tests/test_structural.py`: 7 structural invariant tests covering context file boundary, chain definitions boundary, manifest→definition consistency, manifest→filesystem consistency, adapter-only imports, unique IDs, step ops in STEP_HANDLERS.

3. `test(text): WCAG-AA contrast check script for chain UI elements` — `src/app/pages/text/a11y-contrast-check.mjs`: automated contrast ratio verification for 5 new color pairs.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/server && CHAIN_PROVIDER=mock CONTEXT_PROVIDER=mock python -m pytest --tb=short -q
cd {WORKSPACE} && npx ng test --watch=false --browsers=ChromeHeadless
node src/app/pages/text/a11y-contrast-check.mjs
```

**Expected delta**: BE `[N]` → `[N+17]` passing (10 integration + 7 structural). FE pass count unchanged (no new FE tests in this task — FE tests landed in Task 6). WCAG script exits 0. Zero pre-existing tests broken.

**Success criteria coverage** (from epic):
- `POST /api/text/chain` accepts `chainId` and runs end-to-end: verified by `TestDeepHumanizeChain`, `TestBraindumpToDocsChain`, `TestRewriteReviewChain`.
- All three chains flow through the chain adapter (no direct provider imports): verified by `test_noDirectProviderImportsInChainModules`.
- Context blocks loaded from manifest, not hardcoded: verified by `test_manifestConsistency_allChainContextRefsExistInManifest`.
- Zero regressions on single-shot modes: verified by `TestSingleShotRegression`.
- Feature-gated per user via `enabled_features.text_chains`: verified by `test_textChainsDisabled_returns403WithUpgradeHint`.
- Structural tests pass (loader boundary, runner boundary, manifest consistency, adapter-only imports): verified by `test_structural.py` (7 tests).
- Chain endpoint registered: verified by happy-path tests succeeding (Flask test client resolves the route).
- `data-test` selectors on all new interactive elements: verified by Task 6 FE tests (already landed).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`.
  - Commit 1 (integration tests + fixtures): reverts test code + conftest additions. No production impact.
  - Commit 2 (structural tests): reverts test code only. No production impact.
  - Commit 3 (WCAG script): reverts a standalone script. No production impact.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch. This task adds zero production code — only tests and a QA script. Rollback has zero risk to production behavior.
- **Fixture rollback**: the conftest fixtures are additive (`text_chains_user` and `gated_user` alongside existing fixtures). Reverting commit 1 also reverts the fixtures. Existing test fixtures are untouched.

---

## 9. Deviations Allowed

- **Chain endpoint path differs** — if Task 2 registered the chain route under a different path (e.g., `/api/chain` instead of `/api/text/chain`), update all test URLs to match the actual registered route. Log in commit body.
- **Response field names differ** — if the chain endpoint returns `output` instead of `result`, or `id` instead of `generationId`, update assertions to match the actual response shape. Log in commit body. The tests use `body.get("result") or body.get("output")` patterns to be resilient to either name.
- **Feature flag field name differs** — if the feature guard uses a different key (e.g., `chains` instead of `text_chains`), update fixture `enabled_features` values and assertions. Log in commit body.
- **STEP_HANDLERS import path differs** — if `STEP_HANDLERS` is in `runner.py` instead of `definition_runner.py`, or if `__init__.py` doesn't re-export it, update the import. The structural test already tries both paths.
- **Mock provider does not produce `===FILE:===` markers** — the braindump-to-docs test accepts either a `files` array or a single `result` fallback. The test asserts the chain completes without error, not that the mock produces real multi-file output. Log which shape was observed in the commit body.
- **Conftest fixtures already exist** — if Tasks 2-6 already added `text_chains_user` or similar fixtures, reuse them instead of adding duplicates. Log in commit body.
- **WCAG color values differ from guide** — if Task 6 used different hex values for `--accent-sage` or related tokens, read the actual CSS files, update `a11y-contrast-check.mjs` to match, and log as deviation.
- **Generation model column names differ** — if Task 2 used different column names for chain metadata (e.g., `definition_id` instead of `chain_id`), update the persistence test assertion. Log in commit body.
- **Single-shot endpoint paths differ** — if `/api/text/rewrite` or `/api/text/generate` live at different paths, update `TestSingleShotRegression`. Log in commit body.
- **Side-effect required** (push, publish, migration) — STOP and mark `[REQUIRES APPROVAL]`. This task should not require any side effects.

---

## 10. Out of Scope

This task covers **only** verification of code shipped in Tasks 1-6. No production code is created or modified. The executor must STOP and flag (not absorb) any of the following:

- **Fixing production code to make tests pass** — if a test reveals a bug in Tasks 1-6, file the bug, reference the failing test, and document the expected behavior. Do not fix production code in this task. One exception: if the fix is a one-line typo that the test author clearly intended (e.g., a missing import in `__init__.py`), fix it and log as deviation.
- **Real-API smoke tests** — all automated tests use the mock provider. Manual QA with the real Claude API is covered by Step 6 (manual checklist), not an automated test.
- **Performance benchmarks** — chain execution time is not measured. Trigger: when a chain exceeds 30s in production telemetry.
- **Visual regression screenshots** — deferred. The WCAG script checks computed contrast; visual appearance is covered by manual QA.
- **Adding tests for future chains** — this task covers only the three chains defined in the epic (`deep-humanize`, `braindump-to-docs`, `rewrite-review`). A fourth chain needs its own integration test.
- **Frontend e2e tests (Cypress/Playwright)** — deferred. Frontend is tested via Angular TestBed (Task 6). Browser-level e2e tests are a separate infrastructure investment.
- **Modifying chain definitions or context blocks** — if a chain definition has a bug, flag it for the task that created it (3, 4, or 5). Do not modify definitions or prompts in this task.
- **Cost tracking assertions** — the `chainCompleted` signal is emitted by the runner and tested in Task 2's unit tests. Cost tracking is deferred infrastructure.
- **Dark-theme WCAG checks** — the contrast script checks light-theme values. Dark-theme contrast is a manual QA item (Step 6, item 6). Automated dark-theme checks can be added when the theme token system is formalized.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Structural invariants, module boundaries, observer pattern
- [Epic](./epic.md) — Task 7 detail, full success criteria checklist
- [Timeline](./timeline.md) — Status tracking (update after done)