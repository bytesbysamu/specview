# Task 1: Resolve E2E Driver and Server Strategy

## 1. Context

This task locks the two architectural decisions that every subsequent E2E2 task depends on: which browser automation driver to use, and whether step definitions spin up real Express + Angular dev servers or interact with the filesystem directly. The architecture document has already reasoned through both choices; this task's job is to record them as a versioned ADR (≤30 lines), install and probe Playwright headless to confirm CI viability without a display dependency, and commit both artefacts so Task 2 can write its page objects and `e2e/conftest.py` against a stable contract. No Angular components, no conftest fixture, no page object skeletons, and no step definitions ship from this task.

**Trade-offs considered:**
- **Selenium over Playwright** — rejected: WebDriver protocol adds subprocess overhead; `Xvfb` is required for headless CI, introducing a display-server dependency the architecture explicitly wants to avoid; Playwright's auto-wait semantics match Angular 19's async rendering cycle and ship a bundled Chromium binary that eliminates display setup entirely
- **requests-only or filesystem-only over real servers** — rejected: Angular 19 renders in the browser; Monaco Editor initialises a full CodeMirror instance at runtime; the bootstrap flow writes project directories via Express; the edit-spec auto-save round-trip requires a real server response — none of these paths are exercisable without a real browser against real servers
- **Playwright Python + real servers, AI mocked at Express middleware** — chosen: full behavioural fidelity, CI-safe (no credentials, deterministic AI responses), single-process, no display server required, and consistent with the existing pytest-based backend test conventions already in place

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                              # flag any unrelated M/?? entries
git diff HEAD -- e2e/                                   # confirm e2e/ is clean (may not exist yet — that is expected)
cd {WORKSPACE} && npm test -- --watch=false 2>&1 | tail -5   # baseline Angular test count; record it
node --version                                          # confirm Node is available (Angular + Express require it)
python --version                                        # confirm Python 3.11+; probe requires it
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: N Angular tests passing from `npm test -- --watch=false`. Zero E2E tests exist yet — that is the expected starting state.

---

## 3. Files

### To Create (new)
- `e2e/requirements.txt` — (new) pinned Python dependencies for the E2E layer; consumed by the Step 2 probe and by Task 2's fixture setup
- `e2e/decisions/001-driver-and-server-strategy.md` — (new) ADR recording both decisions and the Step 2 probe result; the stable contract Task 2 and Task 3 executors reference by name

### To Modify
- None — this task creates only; no existing file is modified

### To Leave Alone
- `server.js` — Express projects API; not touched until Task 3 adds the AI mock middleware
- `src/` — Angular source; no `[data-test]` additions or component changes in this task
- `specs/` — existing spec documents; not modified
- `projects/` — persisted bootstrapped projects; not modified
- `package.json` / `package-lock.json` — no Node dependency changes; Playwright is installed as a Python package

---

## 4. Implementation Steps

### Step 1: Create `e2e/requirements.txt` with pinned dependencies

**Action**: Create `e2e/requirements.txt` pinning `playwright`, `pytest`, and `pytest-bdd` to exact minor versions. Pinning to minor (e.g., `==1.44.0`) is required — unpinned ranges (`>=1`) are not acceptable per the engineering principles.

**File**: `e2e/requirements.txt` (new)

**Pattern**:
```text
playwright==1.44.0
pytest==8.2.0
pytest-bdd==7.1.2
```

> Version note: run `pip index versions playwright` at execution time to confirm the latest stable patch. Substitute the patch version if a newer one is available; do not change the minor version without verifying pytest-bdd compatibility.

**Verify**:
```bash
pip install -r {WORKSPACE}/e2e/requirements.txt --dry-run 2>&1 | tail -5
```
Expect: all packages resolved, no conflict errors. (`--dry-run` is the safe local pre-check; CI and actual install happen in Step 2.)

---

### Step 2: Run the headless Playwright probe

**Action**: Install the pinned dependencies, install the Chromium browser binary, and run a one-shot headless probe script. This is an in-process verification step — no probe file is committed. Record the exact output line; it feeds into Step 3.

**File**: probe is a shell invocation; no file is created.

**Pattern**:
```bash
pip install -r {WORKSPACE}/e2e/requirements.txt
playwright install chromium

python - <<'EOF'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("about:blank")
    title = page.title()
    browser.close()
print(f"Playwright headless probe: PASS (title={title!r})")
EOF
```

**Verify**: final output line is `Playwright headless probe: PASS (title='')` and the process exits 0. No `DISPLAY`, `Xvfb`, or `cannot connect to X server` errors appear. If the probe fails, see §9 Deviations Allowed — do NOT proceed to Step 3 until this passes.

---

### Step 3: Write the ADR

**Action**: Create `e2e/decisions/001-driver-and-server-strategy.md` using the template below. Substitute the `[PROBE RESULT]` placeholder with the exact output line from Step 2. The ADR must stay ≤30 lines (hard limit from the epic).

**File**: `e2e/decisions/001-driver-and-server-strategy.md` (new)

**Pattern** (write exactly this, substituting `[PROBE RESULT]`):
```markdown
# ADR 001 — E2E Driver and Server Strategy

**Date**: 2026-04-25
**Status**: Accepted
**Supersedes**: —

## Decision 1: Browser driver → Playwright Python (sync API, Chromium)

**Rejected**: Selenium — WebDriver overhead; Xvfb required for headless CI; brittle SPA polling.
**Rejected**: requests-only — Angular 19 renders in browser; Monaco Editor requires DOM; no real round-trips.
**Chosen**: `playwright` Python sync API, Chromium, headless in CI, headed locally for authoring.

**Probe result**: [PROBE RESULT]

## Decision 2: Server strategy → Real Express + Angular; AI mocked at Express middleware

**Rejected**: mocked Express — would test the mock, not the filesystem-backed project API.
**Rejected**: filesystem-only — Angular rendering never exercised; auto-save round-trip unverifiable.
**Chosen**: Real Angular dev server (port 4201) + real Express projects API (port 3100), session-scoped.
AI responses intercepted at Express `/api/ai/text` middleware; deterministic fixtures; no Claude credentials in CI.

## Implications for Task 2

- `e2e/conftest.py` encodes this strategy exactly once; no step-definition module embeds server-start logic.
- All four page object classes use `[data-test]` selectors exclusively — never class, tag, or text.
- AI mock fixture is registered before the browser session begins.
- Express test-mode env flag (`AI_PROVIDER=mock`) is wired in Task 3, not here.
```

**Verify**:
```bash
wc -l {WORKSPACE}/e2e/decisions/001-driver-and-server-strategy.md
```
Expect: ≤30 lines. Confirm `[PROBE RESULT]` has been replaced with the actual Step 2 output.

---

## 5. Tests

This task ships no pytest or Karma tests — the probe in Step 2 is the functional verification. The following shell assertion is the §5 substitute and must pass before the final commit:

```bash
python - <<'EOF'
import pathlib, sys

root = pathlib.Path("{WORKSPACE}")

# --- ADR exists and is within budget ---
adr = root / "e2e/decisions/001-driver-and-server-strategy.md"
assert adr.exists(), f"ADR missing: {adr}"
lines = adr.read_text().splitlines()
assert len(lines) <= 30, f"ADR exceeds 30 lines: {len(lines)} found"

content = adr.read_text()
assert "Playwright Python" in content,          "ADR missing driver decision"
assert "Real Express + Angular" in content,     "ADR missing server strategy decision"
assert "Probe result" in content,               "ADR missing probe result section"
assert "PASS" in content,                       "ADR probe result not recorded as PASS"
assert "[PROBE RESULT]" not in content,         "ADR still contains unreplaced placeholder"
assert "Task 2" in content,                     "ADR missing Task 2 implications"
assert "AI_PROVIDER=mock" in content,           "ADR missing env-flag reference"

# --- requirements.txt exists and is pinned ---
req = root / "e2e/requirements.txt"
assert req.exists(), f"requirements.txt missing: {req}"
req_text = req.read_text()
assert "playwright==" in req_text,   "playwright must be pinned (== not >=)"
assert "pytest==" in req_text,       "pytest must be pinned"
assert "pytest-bdd==" in req_text,   "pytest-bdd must be pinned"

print("All Task 1 assertions passed.")
EOF
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task. Run the commit before moving to the next step.

1. `chore(e2e): pin playwright, pytest, pytest-bdd in e2e/requirements.txt` — after Step 1 — files: `e2e/requirements.txt`
2. `docs(e2e): record ADR 001 — Playwright Python driver, real-servers + mocked-AI strategy` — after Step 3 (Step 2 is a probe; its result is captured in the ADR committed here) — files: `e2e/decisions/001-driver-and-server-strategy.md`

**Deviation logging**: if any step deviates from this guide (e.g., version pins differ, probe output format differs, ADR line count required trimming), prefix that commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Confirm no regressions in existing Angular tests
cd {WORKSPACE} && npm test -- --watch=false 2>&1 | tail -5

# Confirm artefacts exist and pass the §5 assertion
python - <<'EOF'
import pathlib
root = pathlib.Path("{WORKSPACE}")
adr = root / "e2e/decisions/001-driver-and-server-strategy.md"
req = root / "e2e/requirements.txt"
assert adr.exists() and req.exists(), "One or more artefacts missing"
assert len(adr.read_text().splitlines()) <= 30, "ADR exceeds 30-line budget"
assert "[PROBE RESULT]" not in adr.read_text(), "Placeholder not replaced"
print("Artefact verification: PASS")
EOF
```

**Expected delta**: 0 → 0 new pytest or Karma tests (this task ships no test files). Zero pre-existing Angular tests broken. Playwright probe exits 0 and output is captured in the ADR.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` for the specific step's commit SHA.
- **Probe-only failure** (Step 2 fails, nothing committed yet): no rollback needed — resolve the probe failure per §9 before continuing.
- **Per-branch**: if verification fails, `git reset --hard <pre-task-sha>` to return to the baseline recorded in §2, then delete the feature branch and re-cut.

---

## 9. Deviations Allowed

- **Probe fails with `playwright install` CDN error** — check network access to `playwright.azureedge.net`; if blocked, try `PLAYWRIGHT_DOWNLOAD_HOST` env override. Note the workaround in the ADR and commit body.
- **Probe fails with `DISPLAY` / `Xvfb` error** — the chosen strategy is blocked; do NOT proceed to Step 3; STOP and raise a blocker. The ADR must not be committed with a FAIL probe result.
- **Version resolution conflict on `pip install --dry-run`** — substitute compatible patch versions; update `requirements.txt` accordingly; pin to minor at minimum; note in commit body.
- **`wc -l` reports > 30 lines on the ADR** — trim the "Implications for Task 2" section to the four bullets shown; cut any blank lines beyond one between sections; the 30-line budget is a hard limit from the epic.
- **`npm test -- --watch=false` reports a pre-existing failure** — record it in the §2 baseline; do not attempt to fix it; it is pre-existing and out of scope.
- **Step N unlocks an obvious simplification for Step N+1** — take it; log as a deviation in the commit body.
- **Prescribed path doesn't exist** — verify against CODEBASE CONTEXT; if still missing, flag it; do not invent.

---

## 10. Out of Scope

This task delivers exactly two files: the pinned `requirements.txt` and the ADR. The entire E2E infrastructure — fixture, page objects, feature files, step definitions, and CI wiring — is Task 2 and Task 3's scope. An executor who finds the decisions clear and obvious may be tempted to stub out the next layer; that temptation must be resisted, because Task 2's first job is to choose the exact fixture shape, which is calibrated by the ADR this task produces, not pre-empted by it.

- `e2e/conftest.py` — Task 2's deliverable; do not create even a stub
- `e2e/pages/` or any page object class (`EditorPage`, `PreviewPage`, `OperationBarPage`, `SidebarPage`) — Task 2's deliverable
- Any `.feature` file — Task 3's deliverable
- Any step-definition module — Task 3's deliverable
- Express AI mock middleware in `server.js` (the `AI_PROVIDER=mock` env flag wiring) — Task 3's deliverable; the ADR names the strategy but does not implement it
- `pytest.ini` or `pyproject.toml` pytest configuration — Task 2 creates pytest configuration when the first runnable test exists; creating it now pre-empts shape decisions Task 2 must own
- CI workflow changes (GitHub Actions job for E2E) — Task 3 addresses CI orchestration once the real-server strategy is confirmed viable locally
- Any `[data-test]` attribute additions to Angular components — pre-existing selector gaps; addressed only if a selector survey is explicitly scoped into a future task

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale this task records as an ADR
- [Epic](./epic.md) — task scope and 30-line port budget
- [Timeline](./timeline.md) — update Task 1 status to ✅ Done after §7 verification passes