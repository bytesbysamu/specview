# Task 1: Fix CLI Provider — Forward `--max-tokens`

**Purpose**: Add `--max-tokens` to the subprocess command in `modules/chain/providers/cli.py` so the Claude CLI binary honours the token ceiling passed by callers. Without this, every call runs at the binary's built-in default regardless of what the adapter thread through.

**Effort**: 0.5 days

**Dependencies**: None (code change only; binary prerequisite confirmed in pre-flight)

**Parallel With**: —

**Blocks**: Task 2 (ceiling raise at call sites), Task 3 (truncation heuristic), Task 4 (OpenAPI `warnings` contract)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The `chain/adapter.py` boundary correctly accepts `max_tokens` on all three public entry points (`generate`, `rewrite`, `stream`) and passes it verbatim to whichever provider is active. The CLI provider (`modules/chain/providers/cli.py`) accepts the parameter in its signature but never includes `--max-tokens` in the subprocess command list it builds — so the CLI binary always falls back to its built-in default ceiling regardless of what the caller requests. The fix is a single-line change to the `cmd` list inside `create_message`; because `stream_message` delegates directly to `create_message`, fixing one fixes both. No new abstractions are introduced; the provider remains invisible to all call sites.

**Trade-offs considered:**
- **Add flag only when `max_tokens` differs from the default** — rejected because conditional inclusion creates a gap: callers that rely on the default receiving a consistent ceiling cannot be certain the binary is running at 4 096 rather than its own built-in. Unconditional inclusion is the only guarantee.
- **Pass `--max-tokens` via environment variable** — rejected because the Claude CLI binary's documented interface for ceiling control is a flag, not an env var. Adding an undocumented env-var path would bypass the binary's own contract.
- **Unconditional `str(max_tokens)` appended to the initial `cmd` list** — preferred because the flag is always present, the binary receives an explicit ceiling on every call, and the change is a single token addition to one line.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm working tree state
git -C {WORKSPACE} status

# 2. Confirm target file is clean
git -C {WORKSPACE} diff HEAD -- modules/chain/providers/cli.py

# 3. CRITICAL: Confirm the deployed CLI binary accepts --max-tokens
#    Expected: one or more lines mentioning "max-tokens" or "max_tokens"
#    If output is empty: binary upgrade is a HARD PREREQUISITE — do NOT proceed
claude --help 2>&1 | grep -i "max.tokens"

# 4. Record baseline test count
cd {WORKSPACE} && make test 2>&1 | tail -5
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**If `claude --help | grep -i "max.tokens"` returns empty**: STOP. The binary does not expose `--max-tokens`. Adding the flag will cause every CLI call to exit non-zero. Raise a binary upgrade as a hard prerequisite before reopening this task.

**Baseline recorded**: record the passing count from `make test` output before proceeding (CLAUDE.md cites 192; verify live).

---

## 3. Files

### To Create (new)
- `modules/chain/tests/test_cli_provider.py` — unit tests asserting that `create_message` and `stream_message` include `--max-tokens` in the subprocess command; mocks `subprocess.run` via `monkeypatch.setattr`

### To Modify (cite CODEBASE CONTEXT)
- `modules/chain/providers/cli.py` — line 13: `cmd = ["claude", "-p", "--output-format", "text"]` → add `"--max-tokens", str(max_tokens)` to the initial list so the flag is present on every invocation

### To Leave Alone
- `modules/chain/adapter.py` — already correctly threads `max_tokens` to `provider.create_message` (lines 49, 68, 86); no change needed
- `modules/chain/providers/mock.py` — accepts `max_tokens` in its signature and does not need to forward it; mock behaviour is intentionally inert
- `modules/chain/providers/claude.py` — SDK provider already passes `max_tokens` to `client.messages.create`; no parity change needed (architecture explicitly out of scope)
- `modules/chain/tests/test_structural.py` — structural adapter-boundary test remains valid; new test file lives in `tests/` (excluded from the scan)
- `modules/chain/tests/test_adapter.py` — adapter-level tests remain valid; no behaviour change at the adapter layer

---

## 4. Implementation Steps

### Step 1: Add `--max-tokens` to the CLI subprocess command

**Action**: In `modules/chain/providers/cli.py`, append `"--max-tokens"` and `str(max_tokens)` to the `cmd` list on the same line it is constructed, so the flag is present unconditionally on every invocation.

**File**: `modules/chain/providers/cli.py` (CODEBASE CONTEXT — confirmed at line 13)

**Current state** (line 13):
```python
cmd = ["claude", "-p", "--output-format", "text"]
```

**Target state** (line 13 — one-line replacement):
```python
cmd = ["claude", "-p", "--output-format", "text", "--max-tokens", str(max_tokens)]
```

No other lines in this file change. `stream_message` delegates to `create_message` (line 34) and automatically inherits the fix.

**Verify**:
```bash
cd {WORKSPACE} && python -c "
from modules.chain.providers.cli import create_message
import subprocess, unittest.mock
with unittest.mock.patch('subprocess.run') as m:
    m.return_value.returncode = 0
    m.return_value.stdout = 'ok'
    m.return_value.stderr = ''
    create_message('sys', 'prompt', max_tokens=8192)
cmd = m.call_args[0][0]
assert '--max-tokens' in cmd and cmd[cmd.index('--max-tokens') + 1] == '8192', cmd
print('PASS:', cmd)
"
```
Expected output: `PASS: ['claude', '-p', '--output-format', 'text', '--max-tokens', '8192']`

> **Commit now** — see Commit Plan step 1 before proceeding to Step 2.

---

### Step 2: Write and run the CLI provider unit tests

**Action**: Create `modules/chain/tests/test_cli_provider.py` with four test functions that mock `subprocess.run` and assert `--max-tokens` presence, value accuracy, delegation through `stream_message`, and regression-safety of `--system-prompt`.

**File**: `modules/chain/tests/test_cli_provider.py` (new)

**Pattern** (full file — see Section 5 for complete assertions):
```python
"""CLI provider unit tests — subprocess flag forwarding."""
from __future__ import annotations
import subprocess
from unittest.mock import MagicMock
import pytest
from modules.chain.providers.cli import create_message, stream_message

def _fake_run(returncode=0, stdout="output", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m

def maxTokensFlag_isForwardedToSubprocess(monkeypatch): ...
def defaultMaxTokens_isForwardedWhenCallerOmitsIt(monkeypatch): ...
def streamMessage_forwardsMaxTokensViaDelegation(monkeypatch): ...
def systemPromptFlag_stillPresentAfterMaxTokensAddition(monkeypatch): ...
```

**Verify**:
```bash
cd {WORKSPACE} && python -m pytest modules/chain/tests/test_cli_provider.py -v
```
Expected: 4 passed, 0 failed, 0 errors.

> **Commit now** — see Commit Plan step 2 before proceeding to verification.

---

## 5. Tests

Framework: **pytest**. Collection rule: `python_functions = ["test_*", "*_*"]` (any function containing `_` is collected). Naming convention: `<subject>_<behavior>`. Uses `monkeypatch.setattr` to intercept `subprocess.run` without spawning a real process.

**File**: `modules/chain/tests/test_cli_provider.py`

```python
"""CLI provider unit tests — subprocess flag forwarding."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from modules.chain.providers.cli import create_message, stream_message


def _fake_subprocess_result(returncode: int = 0, stdout: str = "output text", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def maxTokensFlag_isForwardedToSubprocess(monkeypatch):
    """--max-tokens N appears in the subprocess command when max_tokens=N is passed."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _fake_subprocess_result(stdout="response body")

    monkeypatch.setattr(subprocess, "run", fake_run)
    create_message("system prompt", "user prompt", max_tokens=8192)

    cmd = captured["cmd"]
    assert "--max-tokens" in cmd, f"--max-tokens missing from cmd: {cmd}"
    idx = cmd.index("--max-tokens")
    assert cmd[idx + 1] == "8192", (
        f"expected value '8192' after --max-tokens, got {cmd[idx + 1]!r} in: {cmd}"
    )


def defaultMaxTokens_isForwardedWhenCallerOmitsIt(monkeypatch):
    """Default max_tokens=4096 is forwarded even when the caller omits the parameter."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _fake_subprocess_result(stdout="default response")

    monkeypatch.setattr(subprocess, "run", fake_run)
    create_message("sys", "prompt")  # max_tokens not supplied — uses default 4096

    cmd = captured["cmd"]
    assert "--max-tokens" in cmd, f"--max-tokens missing from default-call cmd: {cmd}"
    idx = cmd.index("--max-tokens")
    assert cmd[idx + 1] == "4096", (
        f"expected value '4096' (default) after --max-tokens, got {cmd[idx + 1]!r} in: {cmd}"
    )


def streamMessage_forwardsMaxTokensViaDelegation(monkeypatch):
    """stream_message delegates to create_message, so --max-tokens reaches the subprocess."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _fake_subprocess_result(stdout="streamed body")

    monkeypatch.setattr(subprocess, "run", fake_run)
    chunks = list(stream_message("sys", "prompt", max_tokens=16384))

    cmd = captured["cmd"]
    assert "--max-tokens" in cmd, f"--max-tokens missing from stream_message cmd: {cmd}"
    idx = cmd.index("--max-tokens")
    assert cmd[idx + 1] == "16384", (
        f"expected '16384' after --max-tokens, got {cmd[idx + 1]!r} in: {cmd}"
    )
    assert "".join(chunks) == "streamed body", (
        f"stream_message did not yield subprocess stdout; got: {chunks!r}"
    )


def systemPromptFlag_stillPresentAfterMaxTokensAddition(monkeypatch):
    """Regression: --system-prompt is still included when a system prompt is provided."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _fake_subprocess_result(stdout="ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    create_message("my system instruction", "user text", max_tokens=1024)

    cmd = captured["cmd"]
    assert "--system-prompt" in cmd, f"--system-prompt missing after max_tokens change: {cmd}"
    sp_idx = cmd.index("--system-prompt")
    assert cmd[sp_idx + 1] == "my system instruction", (
        f"system prompt value wrong: {cmd[sp_idx + 1]!r}"
    )
    assert "--max-tokens" in cmd, f"--max-tokens also missing: {cmd}"
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step — not at the end. Each boundary below maps to the step above. Run the commit before moving to the next step.

1. `fix(chain): forward --max-tokens to CLI subprocess` — after **Step 1** — `modules/chain/providers/cli.py`: adds `"--max-tokens", str(max_tokens)` to the `cmd` list

   ```bash
   git -C {WORKSPACE} add modules/chain/providers/cli.py
   git -C {WORKSPACE} commit -m "$(cat <<'EOF'
   fix(chain): forward --max-tokens to CLI subprocess

   The CLI provider accepted max_tokens in its signature but never passed
   --max-tokens to the subprocess. Every call ran at the binary's built-in
   default ceiling regardless of the caller's requested value. One-line fix:
   append ["--max-tokens", str(max_tokens)] to the initial cmd list so the
   flag is present unconditionally.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

2. `test(chain): assert --max-tokens flag forwarding in cli provider` — after **Step 2** — `modules/chain/tests/test_cli_provider.py`: four unit tests covering explicit value, default value, stream delegation, and system-prompt regression

   ```bash
   git -C {WORKSPACE} add modules/chain/tests/test_cli_provider.py
   git -C {WORKSPACE} commit -m "$(cat <<'EOF'
   test(chain): assert --max-tokens flag forwarding in cli provider

   Adds test_cli_provider.py with four pytest functions:
   - maxTokensFlag_isForwardedToSubprocess
   - defaultMaxTokens_isForwardedWhenCallerOmitsIt
   - streamMessage_forwardsMaxTokensViaDelegation
   - systemPromptFlag_stillPresentAfterMaxTokensAddition

   All mock subprocess.run via monkeypatch.setattr to avoid spawning a
   real process.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE} && make test
```

**Expected delta**: baseline → baseline + 4 passing. Zero pre-existing tests broken.

Spot-check the new tests in isolation:
```bash
cd {WORKSPACE} && python -m pytest modules/chain/tests/test_cli_provider.py -v
```
Expected: exactly 4 tests collected, 4 passed.

Confirm the structural adapter-boundary test still passes (it must, since `test_cli_provider.py` lives in `tests/` which is exempt from the scan):
```bash
cd {WORKSPACE} && python -m pytest modules/chain/tests/test_structural.py -v
```
Expected: 1 passed, unchanged.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Revert the provider fix: `git -C {WORKSPACE} revert <sha-of-fix-commit>`
  - Revert the tests: `git -C {WORKSPACE} revert <sha-of-test-commit>`
- **Per-branch**: if verification fails catastrophically, reset to the pre-task state:
  ```bash
  git -C {WORKSPACE} reset --hard <pre-task-sha>
  ```
  Or, if working on a feature branch, delete it:
  ```bash
  git -C {WORKSPACE} branch -D <branch-name>  # [REQUIRES APPROVAL] — destructive
  ```

---

## 9. Deviations Allowed

- **`--max-tokens` not found in `claude --help`** → STOP immediately. Do not edit any file. The binary upgrade is a hard prerequisite. Raise it explicitly before reopening this task.
- **Prescribed path `modules/chain/providers/cli.py` not found** → verify via `ls modules/chain/providers/`; if still missing, flag and halt — do not invent an alternative path.
- **Test framework mismatch** (e.g., a future migration from bare pytest functions to class-based tests) → match the repo's current convention; translate silently and note in commit body with `Deviations:` prefix.
- **Side-effect required** (push to remote, publish, schema migration) → STOP, mark `[REQUIRES APPROVAL]`, and ask.
- **`subprocess.run` signature differs** (e.g., positional vs keyword `cmd`) → adjust the `captured["cmd"]` extraction in tests to match; log as a deviation.

---

## 10. Out of Scope

This task is deliberately scoped to the single provider fix described in the architecture. The following changes are excluded here because they either depend on this fix being deployed first, belong to a separate brain dump, or require design decisions not yet made.

- **Task 2 call-site ceiling raises** (`generate_spec.py`, `task_gen/service.py`) — sequentially dependent on this task being confirmed live in production; raising the ceiling before the provider forwards the flag is a silent no-op
- **Task 3 truncation heuristic** (`_looks_truncated`, `warnings` state in `task_gen/service.py`) — has no effect until larger output is actually being generated; sequentially dependent on Task 2
- **Task 4 OpenAPI `warnings` contract** (`openapi.yaml` → `dtos/models.py`) — meaningless until the heuristic in Task 3 populates the field
- **Timeout increases** — no concrete file inventory exists; scoping timeout work without one produces changes in the wrong places
- **`model` parameter forwarding** — `model` is also accepted but not forwarded in the subprocess command; not in scope for this fix and not identified in the analysis as a source of failures
- **Angular warning badge** — frontend consumer of the `warnings` API field; a separate deliverable after Task 4
- **Token-cost accounting** — cross-provider concern owned by a separate brain dump

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)