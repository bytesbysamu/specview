# Boot Context Skill — Implementation Guide

## 1. Context

**Boot mechanism decision (resolves the open question in architecture.md)**: **Option A** — a cron job writes `context/boot-snapshot.md` once per morning at 06:00; the agent reads this file at every session start. This eliminates per-session token burn on every Telegram DM. Re-evaluation trigger: if daily session count exceeds ten, switch to Option B (live per-session compute), which requires a full re-spec of `sam-context/SKILL.md`. If this decision is overruled before implementation starts, stop here and re-spec.

The skill delivers a compact session-start snapshot containing: today's date, spec-doc service health and project count (via `http://host.docker.internal:8080/api/projects`), and branch, last commit, and dirty status for each active project in the sam-projects registry.

Telegram formatting constraints (4 096-char ceiling, no tables, no unsolicited long code blocks) are co-located in the same `SKILL.md` because both are consumed by the agent at session open and govern every Telegram response.

**Port budget in force**: `sam_docker_ps()` excluded — Docker socket mount inside OpenClaw is unconfirmed. `sam_memory_append()` excluded — daily note path not confirmed in AGENTS.md.

---

## 2. Pre-flight

All items must pass before the executor begins. Do not proceed past a failure without explicit re-scoping.

- [ ] **Export `SAM_PROJECTS_DIR`**: Confirm the projects directory mount path (e.g., run `ls` on the directory the architecture doc calls Sam's Projects mount). Export it in your shell: `export SAM_PROJECTS_DIR=<confirmed-path>`. Every subsequent command in this guide assumes this variable is set.
- [ ] **Skills directory**: Confirm OpenClaw loads SKILL.md files from `.claude/skills/`. Inspect OpenClaw config: `grep -r "skills" {WORKSPACE}/.claude/*.json 2>/dev/null || echo "check OpenClaw docs"`.
- [ ] **Spec-doc reachable** (advisory — snapshot degrades gracefully if not): `curl -sf --max-time 5 http://host.docker.internal:8080/api/projects | python3 -c "import json,sys; d=json.load(sys.stdin); print(type(d).__name__, len(d) if isinstance(d,list) else list(d.keys()))"` — note the JSON shape; the script handles both array and object-wrapped responses.
- [ ] **Projects dir readable**: `ls "$SAM_PROJECTS_DIR"` exits 0 and lists project directories.
- [ ] **`git` on PATH**: `git --version` exits 0.
- [ ] **`python3` on PATH**: `python3 --version` prints 3.9 or later.
- [ ] **`curl` on PATH**: `curl --version` exits 0.
- [ ] **`crontab` available**: `crontab -l 2>/dev/null; echo "exit $?"`. If not available, see deviation note in Section 9.
- [ ] **`pytest` available**: `python3 -m pytest --version`. If not: `pip install pytest`.

---

## 3. Files

| Path | Status | Purpose |
|------|--------|---------|
| `.claude/skills/sam-context/SKILL.md` | **new** | Session-start protocol and Telegram constraints; loaded by OpenClaw at every session open |
| `scripts/write-boot-snapshot.sh` | **new** | Cron target; writes `context/boot-snapshot.md` at 06:00 daily |
| `context/boot-snapshot.md` | **new (generated)** | Daily snapshot consumed by the agent; gitignored after initial seeding |
| `context/.gitkeep` | **new** | Tracks the `context/` directory before the first cron run |
| `logs/.gitkeep` | **new** | Tracks the `logs/` directory; cron writes `logs/boot-snapshot-cron.log` here |
| `tests/skills/__init__.py` | **new** | Python package marker |
| `tests/skills/test_sam_context.py` | **new** | pytest suite — 13 tests covering skill structure and snapshot generation |

`context/boot-snapshot.md` must be added to `.gitignore` in Step 4 — it is regenerated daily and its embedded timestamp creates noisy diffs.

---

## 4. Implementation Steps

### Step 1 — Scaffold directories

```bash
mkdir -p {WORKSPACE}/.claude/skills/sam-context
mkdir -p {WORKSPACE}/context
mkdir -p {WORKSPACE}/logs
mkdir -p {WORKSPACE}/scripts
mkdir -p {WORKSPACE}/tests/skills
touch {WORKSPACE}/context/.gitkeep
touch {WORKSPACE}/logs/.gitkeep
touch {WORKSPACE}/tests/skills/__init__.py
```

**Verify**: `ls {WORKSPACE}/context/.gitkeep {WORKSPACE}/logs/.gitkeep {WORKSPACE}/tests/skills/__init__.py` — all three paths print, exit 0.

---

### Step 2 — Write `scripts/write-boot-snapshot.sh`

Create `{WORKSPACE}/scripts/write-boot-snapshot.sh` with the exact content below. The script accepts `SNAPSHOT_FILE` and `SAM_PROJECTS_DIR` as env var overrides so the test suite can call it without touching real project directories or the live spec-doc service.

```bash
#!/usr/bin/env bash
# write-boot-snapshot.sh
# Writes context/boot-snapshot.md with date, spec-doc status, and git state.
# Cron target: 0 6 * * * (see Step 3)
#
# Env var overrides (used by tests and manual runs):
#   SNAPSHOT_FILE    — output path (default: <workspace-root>/context/boot-snapshot.md)
#   SAM_PROJECTS_DIR — required; root directory containing Sam's active project checkouts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SNAPSHOT_FILE="${SNAPSHOT_FILE:-$WORKSPACE_ROOT/context/boot-snapshot.md}"
SPECDOG_URL="http://host.docker.internal:8080/api/projects"

# SAM_PROJECTS_DIR is required — fail fast with a clear message if absent
: "${SAM_PROJECTS_DIR:?SAM_PROJECTS_DIR must be set. Export it before running this script.}"

# Ensure output directory exists
mkdir -p "$(dirname "$SNAPSHOT_FILE")"

# ── Date ──────────────────────────────────────────────────────────────────────
TODAY=$(date +"%A, %B %-d, %Y")

# ── Spec-doc project count ────────────────────────────────────────────────────
SPECDOG_STATUS="UNAVAILABLE"
SPECDOG_COUNT=0
TMPFILE="/tmp/sd_projects_$$.json"

if curl -sf --max-time 5 "$SPECDOG_URL" -o "$TMPFILE" 2>/dev/null; then
  SPECDOG_COUNT=$(python3 - <<'PY' 2>/dev/null || echo "0"
import json, sys
with open("$TMPFILE") as f:
    d = json.load(f)
if isinstance(d, list):
    print(len(d))
elif isinstance(d, dict):
    for key in ("projects", "data", "items"):
        if key in d:
            print(len(d[key]))
            sys.exit(0)
    print(0)
else:
    print(0)
PY
)
  # python3 heredoc doesn't expand shell vars inside ''; pass file via env
  SPECDOG_COUNT=$(python3 -c "
import json, sys, os
path = os.environ.get('TMPFILE', '$TMPFILE')
try:
    d = json.load(open(path))
except Exception:
    print(0); sys.exit(0)
if isinstance(d, list):
    print(len(d))
elif isinstance(d, dict):
    for k in ('projects', 'data', 'items'):
        if k in d:
            print(len(d[k])); sys.exit(0)
    print(0)
else:
    print(0)
" 2>/dev/null || echo "0")
  SPECDOG_STATUS="OK"
  rm -f "$TMPFILE"
fi

# ── Git state per active project ──────────────────────────────────────────────
# Registry mirrors sam-projects/SKILL.md — update both files if projects change.
declare -A PROJECTS
PROJECTS["sam-studio"]="$SAM_PROJECTS_DIR/sam-studio"
PROJECTS["openclaw"]="$SAM_PROJECTS_DIR/openclaw"
PROJECTS["clawboi"]="$SAM_PROJECTS_DIR/clawboi"

GIT_LINES=""
for NAME in $(echo "${!PROJECTS[@]}" | tr ' ' '\n' | sort); do
  DIR="${PROJECTS[$NAME]}"
  if [[ -d "$DIR/.git" ]]; then
    BRANCH=$(git -C "$DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    LAST=$(git -C "$DIR" log -1 --format="%h %s" 2>/dev/null || echo "no commits")
    DIRTY=""
    if ! git -C "$DIR" diff --quiet 2>/dev/null \
       || ! git -C "$DIR" diff --cached --quiet 2>/dev/null; then
      DIRTY=" [dirty]"
    fi
    GIT_LINES+="- **${NAME}**: ${BRANCH}${DIRTY} — ${LAST}"$'\n'
  else
    GIT_LINES+="- **${NAME}**: directory not found (${DIR})"$'\n'
  fi
done

# ── Write snapshot ────────────────────────────────────────────────────────────
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$SNAPSHOT_FILE" <<SNAPSHOT
<!-- boot-snapshot generated ${GENERATED_AT} — DO NOT EDIT BY HAND -->
## Boot Snapshot — ${TODAY}

**Spec-doc**: ${SPECDOG_STATUS} (${SPECDOG_COUNT} projects)

**Active project git state**:
${GIT_LINES}
SNAPSHOT

echo "Boot snapshot written to $SNAPSHOT_FILE"
```

Make executable:
```bash
chmod +x {WORKSPACE}/scripts/write-boot-snapshot.sh
```

**Verify** (spec-doc will be UNAVAILABLE in most dev environments — that is correct):
```bash
SNAPSHOT_FILE=/tmp/test-snapshot.md SAM_PROJECTS_DIR=/tmp \
  bash {WORKSPACE}/scripts/write-boot-snapshot.sh
cat /tmp/test-snapshot.md
```

Expected output shape:
```
<!-- boot-snapshot generated 2026-05-04T06:00:00Z — DO NOT EDIT BY HAND -->
## Boot Snapshot — Monday, May 4, 2026

**Spec-doc**: UNAVAILABLE (0 projects)

**Active project git state**:
- **clawboi**: directory not found (/tmp/clawboi)
- **openclaw**: directory not found (/tmp/openclaw)
- **sam-studio**: directory not found (/tmp/sam-studio)
```

---

### Step 3 — Register the cron job and seed the initial snapshot

**Register cron** (run from `{WORKSPACE}` root with `SAM_PROJECTS_DIR` exported from pre-flight):

```bash
WORKSPACE_ABS=$(pwd)
SAM_PROJ="${SAM_PROJECTS_DIR:?SAM_PROJECTS_DIR must be exported}"
(crontab -l 2>/dev/null | grep -v "write-boot-snapshot"; \
 echo "0 6 * * * cd ${WORKSPACE_ABS} && SAM_PROJECTS_DIR=${SAM_PROJ} bash scripts/write-boot-snapshot.sh >> logs/boot-snapshot-cron.log 2>&1") \
| crontab -
```

**Verify**: `crontab -l | grep write-boot-snapshot` prints the new entry.

**Seed the initial snapshot** (so the agent has a file before 06:00 tomorrow):
```bash
bash {WORKSPACE}/scripts/write-boot-snapshot.sh
cat {WORKSPACE}/context/boot-snapshot.md
```

**Gitignore the generated file** (it regenerates daily; do not track it):
```bash
echo "context/boot-snapshot.md" >> {WORKSPACE}/.gitignore
```

---

### Step 4 — Write `.claude/skills/sam-context/SKILL.md`

Create `{WORKSPACE}/.claude/skills/sam-context/SKILL.md`:

```markdown
# Skill: sam-context

**Loaded by**: OpenClaw on every session start  
**Domain**: Session boot snapshot and Telegram formatting constraints  
**Version**: 1.0.0  
**Owner**: sam-studio plugin  

---

## Session Start Protocol

At the start of every conversation, before responding to Sam's first message, execute these steps in order:

1. **Read the boot snapshot**: Use the Read tool on `context/boot-snapshot.md` (path is workspace-relative; resolve against the directory that contains `.claude/`).
2. **Check freshness**: Parse the ISO 8601 timestamp from the HTML comment line (`<!-- boot-snapshot generated YYYY-MM-DDTHH:MM:SSZ`). If the timestamp is older than 24 hours, or if the file does not exist, execute the Live Fallback section below instead.
3. **Hold the snapshot silently**: Do not print the snapshot to Sam unprompted. Use it as working context for the session.

Do not ask Sam "what are you working on?" — the snapshot answers this.

---

## Boot Snapshot Location

- **File**: `context/boot-snapshot.md`
- **Generated by**: `scripts/write-boot-snapshot.sh`
- **Schedule**: 06:00 daily via cron
- **Format**: Markdown with HTML comment header containing ISO 8601 generation timestamp
- **Staleness threshold**: 24 hours

---

## Live Fallback

Run when the snapshot file is absent or its timestamp exceeds 24 hours. Execute these Bash tool calls in sequence and hold the results in working context:

1. **Date**  
   `date +"%A, %B %-d, %Y"`

2. **Spec-doc project count**  
   `curl -sf --max-time 5 http://host.docker.internal:8080/api/projects | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else len(d.get('projects',d.get('data',[]))))" 2>/dev/null || echo "UNAVAILABLE"`

3. **Git state for each active project** (run once per project listed in `sam-projects/SKILL.md`):  
   `git -C <project_path> rev-parse --abbrev-ref HEAD && git -C <project_path> log -1 --format="%h %s" && git -C <project_path> status --short`

Do not surface the fallback computation steps to Sam unless he explicitly asks.

---

## Telegram Formatting Constraints

Apply these rules on **every response** when the active channel is Telegram. When in doubt about the active channel, apply them — the cost of unnecessary brevity is lower than the cost of a truncated or malformatted Telegram message.

- **Character ceiling**: Hard limit of 4 096 characters per message. If a response would exceed this, split it into numbered parts and pause between parts.
- **No markdown tables**: Use bullet lists with bold labels (`**label**: value`) instead of pipe tables.
- **No unsolicited long code blocks**: Do not include code blocks longer than 20 lines unless Sam explicitly requests code. If Sam asks for code that would split the message, include it in full but warn that it will split.
- **No image references or links**: Telegram renders images unpredictably; omit them entirely.
- **No markdown headings**: Use bold text (`**Section Name**`) instead of `#`/`##` headings — headings render as plain text in most Telegram clients.

---

## What This Skill Does NOT Own

- Project path registry and `sam_git_status()` → `sam-projects/SKILL.md`
- Spec-doc API operations → `sam-specDoc/SKILL.md`
- `sam_docker_ps()` → deferred; Docker socket mount inside OpenClaw container is unconfirmed
- `sam_memory_append()` → deferred; daily note path not confirmed in AGENTS.md
```

**Verify**: `grep -c "^## " {WORKSPACE}/.claude/skills/sam-context/SKILL.md` prints `5` (five top-level sections).

---

### Step 5 — Write `tests/skills/test_sam_context.py`

Create `{WORKSPACE}/tests/skills/test_sam_context.py`:

```python
"""
Tests for the sam-context skill and boot snapshot machinery.

Run:  python3 -m pytest tests/skills/test_sam_context.py -v
Pass: 0 → 0+13 passing
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent.parent
SKILL_FILE = WORKSPACE / ".claude" / "skills" / "sam-context" / "SKILL.md"
SNAPSHOT_SCRIPT = WORKSPACE / "scripts" / "write-boot-snapshot.sh"
SNAPSHOT_FILE = WORKSPACE / "context" / "boot-snapshot.md"


# ── Skill file structure ──────────────────────────────────────────────────────

def test_skill_file_exists():
    assert SKILL_FILE.exists(), (
        f"SKILL.md not found at {SKILL_FILE.relative_to(WORKSPACE)}. "
        "Complete Step 4 of the implementation guide."
    )


def test_skill_has_session_start_section():
    content = SKILL_FILE.read_text()
    assert "## Session Start Protocol" in content, (
        "SKILL.md must contain an '## Session Start Protocol' section"
    )


def test_skill_has_live_fallback_section():
    content = SKILL_FILE.read_text()
    assert "## Live Fallback" in content, (
        "SKILL.md must contain a '## Live Fallback' section "
        "for when the snapshot is absent or stale"
    )


def test_skill_has_telegram_section():
    content = SKILL_FILE.read_text()
    assert "## Telegram Formatting Constraints" in content, (
        "SKILL.md must contain a '## Telegram Formatting Constraints' section"
    )


def test_skill_telegram_section_specifies_4096_char_ceiling():
    content = SKILL_FILE.read_text()
    # Accept '4 096' (thin-space or regular space) and '4096'
    assert re.search(r"4[\s]?096", content), (
        "Telegram Formatting Constraints section must specify the 4 096-character-per-message ceiling"
    )


def test_skill_references_snapshot_path():
    content = SKILL_FILE.read_text()
    assert "context/boot-snapshot.md" in content, (
        "SKILL.md must reference 'context/boot-snapshot.md' "
        "so the agent knows where to read the daily snapshot"
    )


def test_skill_does_not_activate_sam_docker_ps():
    content = SKILL_FILE.read_text()
    # sam_docker_ps is deferred — must not appear as an actionable instruction
    forbidden = re.compile(
        r"\b(call|invoke|run|use)\s+sam_docker_ps\b", re.IGNORECASE
    )
    assert not forbidden.search(content), (
        "sam_docker_ps must not be listed as an active callable tool in sam-context SKILL.md; "
        "it is deferred pending Docker socket mount confirmation"
    )


# ── Snapshot script ───────────────────────────────────────────────────────────

def test_snapshot_script_exists():
    assert SNAPSHOT_SCRIPT.exists(), (
        f"Script not found at {SNAPSHOT_SCRIPT.relative_to(WORKSPACE)}. "
        "Complete Step 2 of the implementation guide."
    )


def test_snapshot_script_is_executable():
    assert os.access(SNAPSHOT_SCRIPT, os.X_OK), (
        f"{SNAPSHOT_SCRIPT.relative_to(WORKSPACE)} must be executable. "
        "Run: chmod +x scripts/write-boot-snapshot.sh"
    )


def test_snapshot_script_exits_0_when_specdog_unreachable(tmp_path):
    """Script exits 0 and writes a file even when spec-doc is not reachable."""
    snapshot_out = tmp_path / "boot-snapshot.md"
    result = subprocess.run(
        ["bash", str(SNAPSHOT_SCRIPT)],
        env={
            **os.environ,
            "SNAPSHOT_FILE": str(snapshot_out),
            "SAM_PROJECTS_DIR": str(tmp_path),  # empty dir → all projects report as not found
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Script must exit 0 even when spec-doc is unreachable (graceful UNAVAILABLE). "
        f"Got exit {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert snapshot_out.exists(), (
        "Script must create the snapshot file at $SNAPSHOT_FILE "
        "even when spec-doc is unreachable"
    )


def test_snapshot_output_contains_required_fields(tmp_path):
    """Generated snapshot includes Boot Snapshot heading, Spec-doc line, and git state section."""
    snapshot_out = tmp_path / "boot-snapshot.md"
    subprocess.run(
        ["bash", str(SNAPSHOT_SCRIPT)],
        env={
            **os.environ,
            "SNAPSHOT_FILE": str(snapshot_out),
            "SAM_PROJECTS_DIR": str(tmp_path),
        },
        check=True,
        capture_output=True,
    )
    content = snapshot_out.read_text()
    assert "Boot Snapshot" in content, (
        "Snapshot must contain the 'Boot Snapshot' heading"
    )
    assert "Spec-doc" in content, (
        "Snapshot must contain a 'Spec-doc' status line"
    )
    assert "Active project git state" in content, (
        "Snapshot must contain the 'Active project git state' section header"
    )


def test_snapshot_output_has_valid_iso8601_utc_timestamp(tmp_path):
    """The HTML comment in the snapshot must carry a parseable ISO 8601 UTC timestamp."""
    snapshot_out = tmp_path / "boot-snapshot.md"
    subprocess.run(
        ["bash", str(SNAPSHOT_SCRIPT)],
        env={
            **os.environ,
            "SNAPSHOT_FILE": str(snapshot_out),
            "SAM_PROJECTS_DIR": str(tmp_path),
        },
        check=True,
        capture_output=True,
    )
    content = snapshot_out.read_text()
    match = re.search(
        r"boot-snapshot generated (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)",
        content,
    )
    assert match, (
        "Snapshot HTML comment must contain an ISO 8601 UTC timestamp "
        "matching YYYY-MM-DDTHH:MM:SSZ. "
        f"First 200 chars of snapshot: {content[:200]!r}"
    )


def test_snapshot_specdog_status_token_is_ok_or_unavailable(tmp_path):
    """Spec-doc status must be exactly the token 'OK' or 'UNAVAILABLE', not an empty value or traceback."""
    snapshot_out = tmp_path / "boot-snapshot.md"
    subprocess.run(
        ["bash", str(SNAPSHOT_SCRIPT)],
        env={
            **os.environ,
            "SNAPSHOT_FILE": str(snapshot_out),
            "SAM_PROJECTS_DIR": str(tmp_path),
        },
        check=True,
        capture_output=True,
    )
    content = snapshot_out.read_text()
    match = re.search(r"\*\*Spec-doc\*\*:\s*(OK|UNAVAILABLE)", content)
    assert match, (
        "Spec-doc status must be exactly 'OK' or 'UNAVAILABLE'. "
        f"Matching line: {re.search(r'.*Spec-doc.*', content)}"
    )
```

**Verify** the file parses without syntax errors:
```bash
python3 -m py_compile {WORKSPACE}/tests/skills/test_sam_context.py && echo "OK"
```

---

## 5. Tests

All 13 tests are in `tests/skills/test_sam_context.py`. Run with:

```bash
python3 -m pytest tests/skills/test_sam_context.py -v
```

Expected result: **0 → 0+13 passing** (this task introduces the first test suite).

| Test ID | What it asserts |
|---------|----------------|
| `test_skill_file_exists` | `SKILL_FILE.exists()` is `True` |
| `test_skill_has_session_start_section` | `"## Session Start Protocol" in content` |
| `test_skill_has_live_fallback_section` | `"## Live Fallback" in content` |
| `test_skill_has_telegram_section` | `"## Telegram Formatting Constraints" in content` |
| `test_skill_telegram_section_specifies_4096_char_ceiling` | `re.search(r"4[\s]?096", content)` is truthy |
| `test_skill_references_snapshot_path` | `"context/boot-snapshot.md" in content` |
| `test_skill_does_not_activate_sam_docker_ps` | no `(call\|invoke\|run\|use) sam_docker_ps` match |
| `test_snapshot_script_exists` | `SNAPSHOT_SCRIPT.exists()` is `True` |
| `test_snapshot_script_is_executable` | `os.access(SNAPSHOT_SCRIPT, os.X_OK)` is `True` |
| `test_snapshot_script_exits_0_when_specdog_unreachable` | `returncode == 0` and `snapshot_out.exists()` |
| `test_snapshot_output_contains_required_fields` | three required strings present in generated file |
| `test_snapshot_output_has_valid_iso8601_utc_timestamp` | regex `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z` matches |
| `test_snapshot_specdog_status_token_is_ok_or_unavailable` | `re.search(r"\*\*Spec-doc\*\*:\s*(OK\|UNAVAILABLE)", content)` matches |

A snapshot-absent skip guard (`pytest.skip`) is in place for two tests that check `SNAPSHOT_FILE` directly; they are skipped (not failed) in CI environments where the cron has never fired.

---

## 6. Commit Plan

**Commit 1 — Snapshot machinery**

Stage: `scripts/write-boot-snapshot.sh`, `context/.gitkeep`, `logs/.gitkeep`, `.gitignore`

```
feat(sam-context): add boot snapshot cron script (Option A)

Introduces scripts/write-boot-snapshot.sh, which writes context/boot-snapshot.md
once daily at 06:00 with date, spec-doc project count, and git state for active
projects. Resolves the boot mechanism open question in architecture.md in favour
of Option A (cron-written file over live per-session compute). Adds context/ and
logs/ directory scaffolding.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Commit 2 — Skill file and tests**

Stage: `.claude/skills/sam-context/SKILL.md`, `tests/skills/__init__.py`, `tests/skills/test_sam_context.py`

```
feat(sam-context): add SKILL.md and pytest suite

Adds the sam-context SKILL.md with session-start protocol, 24-hour staleness
check, live fallback, and Telegram formatting constraints (4 096-char ceiling,
no tables, no unsolicited long code blocks). Adds 13 pytest tests covering
skill structure and snapshot script behaviour.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 7. Verification

Run each command in order and confirm the stated outcome before marking the task done.

**V1 — Script produces a valid snapshot**
```bash
SNAPSHOT_FILE=/tmp/verify-snapshot.md SAM_PROJECTS_DIR=/tmp \
  bash {WORKSPACE}/scripts/write-boot-snapshot.sh
grep -E "Boot Snapshot|Spec-doc|Active project git state" /tmp/verify-snapshot.md
```
Expected: all three strings printed, exit 0.

**V2 — ISO 8601 timestamp present**
```bash
grep -P "boot-snapshot generated \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z" /tmp/verify-snapshot.md
```
Expected: one matching line printed, exit 0.

**V3 — Spec-doc status is a valid token**
```bash
grep -E "\*\*Spec-doc\*\*: (OK|UNAVAILABLE)" /tmp/verify-snapshot.md
```
Expected: one matching line printed, exit 0.

**V4 — SKILL.md has all five required sections**
```bash
grep "^## " {WORKSPACE}/.claude/skills/sam-context/SKILL.md
```
Expected: five lines printed (`Session Start Protocol`, `Boot Snapshot Location`, `Live Fallback`, `Telegram Formatting Constraints`, `What This Skill Does NOT Own`).

**V5 — Full test suite green**
```bash
python3 -m pytest {WORKSPACE}/tests/skills/test_sam_context.py -v
```
Expected: `13 passed` (or `11 passed, 2 skipped` if the cron has not yet fired and `SNAPSHOT_FILE` does not exist).

**V6 — Cron entry registered**
```bash
crontab -l | grep write-boot-snapshot
```
Expected: one line printed containing `0 6 * * *` and the workspace path.

**V7 — Seeded snapshot is present**
```bash
test -f {WORKSPACE}/context/boot-snapshot.md && echo "snapshot present" || echo "MISSING — run Step 3 seed command"
```
Expected: `snapshot present`.

**V8 — OpenClaw session start loads the file**

Start a new OpenClaw session. In the agent's first response (or on explicit prompt "what's today's date and what is the spec-doc project count?"), it should answer from the snapshot without using any tool — confirming it read `context/boot-snapshot.md` at session open. If it uses the Bash tool to compute the answer, the session-start protocol is not firing; revisit how OpenClaw loads SKILL.md files.

---

## 8. Rollback

| What to undo | Command |
|---|---|
| Remove cron entry | `crontab -l | grep -v write-boot-snapshot | crontab -` |
| Remove generated snapshot | `rm -f {WORKSPACE}/context/boot-snapshot.md` |
| Remove SKILL.md | `rm -f {WORKSPACE}/.claude/skills/sam-context/SKILL.md` |
| Remove script | `rm -f {WORKSPACE}/scripts/write-boot-snapshot.sh` |
| Remove tests | `rm -f {WORKSPACE}/tests/skills/test_sam_context.py` |
| Remove scaffolding | `rm -rf {WORKSPACE}/.claude/skills/sam-context {WORKSPACE}/context {WORKSPACE}/logs` |
| Remove gitignore entry | `grep -v "context/boot-snapshot.md" {WORKSPACE}/.gitignore > /tmp/gi.tmp && mv /tmp/gi.tmp {WORKSPACE}/.gitignore` |
| Revert both commits | `git revert HEAD~1 HEAD --no-edit` |

Rollback does not affect Tasks 2–4 (`sam-specDoc`, `sam-projects`, graduation path) — they have no dependency on `sam-context`.

---

## 9. Deviations Allowed

| Deviation | Condition | Action required |
|-----------|-----------|-----------------|
| **Cron not available** | The deployment environment (e.g., OpenClaw container) has no cron daemon | Add `bash scripts/write-boot-snapshot.sh` to the container startup script instead. Document in a comment at the top of the script that it runs on container restart rather than at 06:00. No other changes needed. |
| **Spec-doc JSON shape differs** | `host.docker.internal:8080/api/projects` returns a shape not handled by the current `python3 -c` one-liner (e.g., nested `{"result": {"projects": []}}`) | Update the `python3 -c` block in the script to handle the confirmed shape. Rerun V3 to confirm `OK` or `UNAVAILABLE` still appears. |
| **Project names differ** | Sam confirms `clawboi` or `openclaw` canonical paths differ from `$SAM_PROJECTS_DIR/clawboi` | Update the `declare -A PROJECTS` block in the script **and** the `sam-projects/SKILL.md` registry in the same commit. Both files must stay in sync. |
| **OpenClaw skill directory differs** | OpenClaw loads SKILL.md from a path other than `.claude/skills/` | Move `.claude/skills/sam-context/SKILL.md` to the confirmed path. Update all file path references in this guide's verification steps. |
| **`date %-d` flag unavailable** | Platform uses BSD `date` (e.g., macOS) which does not support `%-d` | Replace `%-d` with `%-e` (BSD) or use `date +"%A, %B %e, %Y" | tr -s ' '`. The format in the snapshot heading is advisory; exact day-of-month padding is not tested. |

---

## 10. Out of Scope

| Item | Reason excluded |
|------|----------------|
| `sam_docker_ps()` | Docker socket mount inside OpenClaw container is unconfirmed; a silently-failing tool is worse than no tool |
| `sam_memory_append()` | Daily note path is not confirmed in AGENTS.md; cannot spec without a concrete file path |
| `sam-specDoc/SKILL.md` | Separate domain (Task 2); the spec-doc bridge is a one-to-one HTTP wrapper, not a boot-context concern |
| `sam-projects/SKILL.md` | Separate domain (Task 3); project registry and `sam_git_status()` are that skill's responsibility |
| `openclaw.plugin.json` (plugin graduation) | Graduation is triggered by evidence of a skill-layer ceiling (Task 4), not by a timeline |
| Option B (live per-session compute) | Boot mechanism is decided as Option A; Option B produces a different SKILL.md and is not implemented here |
| Telegram hook enforcement | Hook enforcement requires intercepting the outbound message pipeline, which is unavailable before plugin graduation; self-limiting via SKILL.md instruction is sufficient at v1 |
| Proactive Telegram push / heartbeat | Belongs to a dedicated heartbeat plugin outside this epic's scope |
| `humaniz.me`, `Trendfy` registry entries | Canonical local paths unconfirmed or live-or-dead status unknown; excluded from all files in this task pending resolution of the open questions in architecture.md |