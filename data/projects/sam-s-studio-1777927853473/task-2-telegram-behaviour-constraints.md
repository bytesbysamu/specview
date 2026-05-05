# Task 2: Telegram Behaviour Constraints — Implementation Guide

---

## 1. Context

**What**: Author the Telegram behaviour constraints section of `sam-context/SKILL.md` — the instruction document OpenClaw loads at every session start. The constraints are: a hard 4096-character ceiling (with a defined split strategy), a markdown-table prohibition, a code-block length gate, and mobile-calibrated tone rules.

**Why**: Telegram is the primary interface Sam uses. Without formatting constraints, responses rendered on mobile will be unreadable (table columns collapse, wall-of-text paragraphs are unscrollable) or silently truncated by Telegram's own 4096-char limit. The architecture resolves the hook-vs-skill-instruction open question in favour of skill instruction for v1; this task closes that gap.

**Mechanism**: Pure SKILL.md authoring — no compiled code, no build step. The agent reads the file and applies the rules before composing any Telegram response. Hook-based enforcement is deferred to Task 5 if self-limiting proves insufficient in practice.

**Boundary with Task 1**: `sam-context/SKILL.md` also carries the boot snapshot definition (Task 1). This guide authors the Telegram section only. If Task 1 has already created the file, the executor appends; if not, the executor creates the file and leaves a clearly-labelled placeholder stub for Task 1 content (see Step 1).

---

## 2. Pre-flight

Run each check before touching a file. All must pass.

```bash
# 1. Confirm workspace root contains the plugin directory layout or is empty (both are valid start states)
ls sam-context/ 2>/dev/null && echo "EXISTS — will append" || echo "ABSENT — will create"

# 2. Python 3.8+ is available (needed for the validation test suite)
python3 --version   # must print Python 3.8.x or higher

# 3. pytest is available
python3 -m pytest --version   # must print pytest 7.x or higher; if absent: pip install pytest

# 4. No uncommitted changes that would interfere (clean working tree or only Task 1 work staged)
git status --short

# 5. Confirm OpenClaw documentation confirms SKILL.md is the correct filename (case-sensitive)
ls *.md openclaw.plugin.json 2>/dev/null || echo "No plugin root files yet — acceptable for Task 2"
```

**Blockers**: Steps 2 and 3 must succeed. Steps 1, 4, 5 are informational.

---

## 3. Files

| Path | Status | Purpose |
|------|--------|---------|
| `sam-context/SKILL.md` | new (or append if Task 1 already created it) | Primary deliverable — Telegram constraint rules consumed by the agent |
| `tests/test_telegram_constraints.py` | new | Content-validation suite; asserts all four constraint rules are present and that helper logic detects violations correctly |
| `tests/__init__.py` | new (empty) | Makes `tests/` a Python package so pytest discovers it without config changes |

No existing files are modified. No build artefacts are produced.

---

## 4. Implementation Steps

### Step 1 — Create or open `sam-context/SKILL.md`

If the directory does not exist:
```bash
mkdir -p sam-context
```

If `sam-context/SKILL.md` already exists (Task 1 content is present), open it and skip to Step 2. The Telegram section is additive.

If the file does not exist, create it with the following content in full. The `<!-- TASK 1 PLACEHOLDER -->` comment is intentional — Task 1 will replace it:

```markdown
# Sam Context

> Loaded by OpenClaw at every session start. Read this file before composing any response in any channel.

<!-- TASK 1 PLACEHOLDER: Boot snapshot definition goes here (session date, service health, git state). Author in Task 1. -->

---
```

### Step 2 — Append the Telegram Behaviour Constraints section

Append the following block to `sam-context/SKILL.md`, immediately after the last line of existing content:

```markdown

## Telegram Behaviour Constraints

Apply **all four rules** in this section whenever the active channel is Telegram. Do not apply them to web UI, IDE, or direct API sessions.

### Channel Detection

The active channel is Telegram when **any** of the following hold:
- The OpenClaw session context header contains `channel: telegram`
- The session was initiated via the Telegram bot integration (no web UI session token present)
- The conversation metadata field `interface` equals `telegram`

If channel cannot be determined, apply these rules as a safe default.

---

### Rule 1 — Character Ceiling (HARD LIMIT)

**Maximum 4096 characters per outbound message**, counted inclusive of all formatting markers (asterisks, backticks, underscores, newlines).

**Split strategy** when a full answer would exceed 4096 characters:
1. Split at the nearest paragraph boundary at or below 4096 characters.
2. Label the first message `(1/2)` at the end and the second `(2/2)` at the start.
3. For three parts, label `(1/3)`, `(2/3)`, `(3/3)` in the same positions.
4. Never split mid-sentence, mid-bullet-list, or mid-code-block.
5. Do not exceed three parts; if content would require four or more, summarise instead and offer detail on request.

---

### Rule 2 — No Markdown Tables

**Never use markdown table syntax** on Telegram. Pipe-delimited rows (`| col | col |`) collapse unpredictably on mobile clients and are prohibited without exception.

**Replacement — use a labelled bullet list:**
```
- **Project**: openclaw
- **Branch**: main
- **Last commit**: feat: add context skill
- **Status**: clean
```

When a comparison between two items would naturally be a table, use two headed bullet groups instead:
```
*Option A — cron file*
- Freshness: daily
- Token cost: zero per session

*Option B — live query*
- Freshness: real-time
- Token cost: one query per session start
```

---

### Rule 3 — No Unsolicited Long Code Blocks

A code block is **unsolicited** when Sam did not explicitly ask to see code, a file listing, or a diff in that message turn.

**Threshold**: 15 lines (newline-delimited, excluding the opening and closing fence lines).

**Constraint**: Do not render an unsolicited code block longer than 15 lines.

**When the threshold is reached on an unsolicited block:**
1. Show the first 15 lines inside the fence.
2. Close the fence.
3. Append on its own line: `_(15 of N lines shown — reply "show rest" for the remainder)_`

Inline code snippets (single-backtick) are **exempt** from this rule regardless of length.

Explicitly requested code (Sam asked "show me the file", "give me the diff", "print the config") is **exempt** from this rule; show the full content, subject only to Rule 1.

---

### Rule 4 — Mobile Tone

Calibrate every Telegram response for single-handed mobile reading:

- **Short paragraphs**: 3 sentences maximum per paragraph; break into a new paragraph or bullet if a fourth sentence is needed.
- **Answer first**: open with the direct answer or result; context, caveats, and explanation follow after a blank line.
- **Prefer bullets over prose blocks**: when listing more than two items, use a bullet list rather than a run-on sentence.
- **Bold sparingly**: maximum 2 bold spans per message; reserve bold for the single most important value or term in a response.
- **No headers inside short answers**: omit `###` headings when the total response is under 300 characters; headings add visual weight that is disproportionate on small screens.
```

### Step 3 — Create the test package

```bash
mkdir -p tests
touch tests/__init__.py
```

### Step 4 — Write `tests/test_telegram_constraints.py`

Create the file with the full content below:

```python
"""
Validation suite for Task 2: Telegram Behaviour Constraints.

Checks:
  - sam-context/SKILL.md exists and contains each of the four constraint rules.
  - Helper functions that model the constraint checks behave correctly on known inputs.

Run with: python3 -m pytest tests/test_telegram_constraints.py -v
"""

import re
import pathlib

SKILL_PATH = pathlib.Path("sam-context/SKILL.md")
CHAR_LIMIT = 4096
CODE_BLOCK_LINE_THRESHOLD = 15


# ── Shared helpers ────────────────────────────────────────────────────────────

def _skill_text() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _exceeds_char_limit(text: str) -> bool:
    return len(text) > CHAR_LIMIT


def _contains_markdown_table(text: str) -> bool:
    return bool(re.search(r"^\|.+\|", text, re.MULTILINE))


def _unsolicited_long_code_block(text: str) -> bool:
    """Return True if any fenced code block exceeds CODE_BLOCK_LINE_THRESHOLD lines."""
    blocks = re.findall(r"```[\s\S]*?```", text)
    for block in blocks:
        # Count interior newlines (exclude the fence lines themselves)
        interior = re.sub(r"^```[^\n]*\n", "", block)
        interior = re.sub(r"\n```$", "", interior)
        if interior.count("\n") >= CODE_BLOCK_LINE_THRESHOLD:
            return True
    return False


# ── File existence ─────────────────────────────────────────────────────────────

class TestSkillFileExists:
    def test_skill_file_present_on_disk(self):
        assert SKILL_PATH.exists(), (
            f"sam-context/SKILL.md not found at {SKILL_PATH.resolve()}; "
            "create it by following Step 1 of the implementation guide"
        )

    def test_skill_file_has_substantive_content(self):
        content = _skill_text()
        assert len(content) >= 200, (
            f"sam-context/SKILL.md is only {len(content)} characters; "
            "it must contain the full Telegram constraint section"
        )


# ── Rule 1: Character ceiling ─────────────────────────────────────────────────

class TestCharacterCeiling:
    def test_4096_limit_stated_in_skill(self):
        content = _skill_text()
        assert "4096" in content, (
            "sam-context/SKILL.md must state the hard 4096-character ceiling explicitly"
        )

    def test_split_strategy_described_in_skill(self):
        content = _skill_text()
        pattern = re.compile(r"split|1/2|continu|part\s+1", re.IGNORECASE)
        assert pattern.search(content), (
            "sam-context/SKILL.md must describe a split/continuation strategy "
            "for responses that exceed 4096 characters"
        )

    def test_short_reply_passes_char_limit(self):
        reply = "The deployment is on port 3000. Run `curl localhost:3000/health` to confirm."
        assert not _exceeds_char_limit(reply), (
            f"Short reply ({len(reply)} chars) must not be flagged as exceeding the 4096-char ceiling"
        )

    def test_reply_of_4097_chars_is_flagged(self):
        reply = "a" * 4097
        assert _exceeds_char_limit(reply), (
            "A reply of 4097 characters must be detected as exceeding the ceiling"
        )

    def test_reply_of_exactly_4096_chars_passes(self):
        reply = "b" * 4096
        assert not _exceeds_char_limit(reply), (
            "A reply of exactly 4096 characters must NOT be flagged — the limit is inclusive"
        )


# ── Rule 2: No markdown tables ────────────────────────────────────────────────

class TestNoMarkdownTables:
    def test_table_prohibition_stated_in_skill(self):
        content = _skill_text()
        pattern = re.compile(
            r"(never|no|prohibit|avoid).{0,30}(table|pipe.{0,10}delimit)",
            re.IGNORECASE,
        )
        assert pattern.search(content), (
            "sam-context/SKILL.md must explicitly prohibit markdown tables on Telegram"
        )

    def test_bullet_list_alternative_stated_in_skill(self):
        content = _skill_text()
        assert re.search(r"bullet|labelled list|bullet list", content, re.IGNORECASE), (
            "sam-context/SKILL.md must nominate a bullet-list format as the table replacement"
        )

    def test_markdown_table_pattern_detected(self):
        sample = "| Header A | Header B |\n|----------|----------|\n| val 1    | val 2    |"
        assert _contains_markdown_table(sample), (
            "The table-detection helper must flag pipe-delimited rows"
        )

    def test_bullet_list_not_flagged_as_table(self):
        sample = "Here are the results:\n- **Project**: openclaw\n- **Branch**: main"
        assert not _contains_markdown_table(sample), (
            "A bullet list must not be flagged as a markdown table"
        )


# ── Rule 3: No unsolicited long code blocks ────────────────────────────────────

class TestCodeBlockConstraint:
    def test_code_block_rule_stated_in_skill(self):
        content = _skill_text()
        pattern = re.compile(r"unsolicited.{0,40}code|code.{0,40}block.{0,40}(line|length|limit|threshold)", re.IGNORECASE)
        assert pattern.search(content), (
            "sam-context/SKILL.md must state the unsolicited code block constraint"
        )

    def test_line_threshold_stated_in_skill(self):
        content = _skill_text()
        assert "15" in content, (
            "sam-context/SKILL.md must state the numeric line threshold (15) for code blocks"
        )

    def test_long_code_block_detected(self):
        lines = "\n".join(f"result_{i} = compute({i})" for i in range(20))
        block = f"```python\n{lines}\n```"
        assert _unsolicited_long_code_block(block), (
            "A fenced code block with 20 interior lines must be flagged as exceeding the threshold"
        )

    def test_short_code_block_not_flagged(self):
        block = "```bash\ncurl -s localhost:3000/health\n```"
        assert not _unsolicited_long_code_block(block), (
            "A two-line code snippet must not be flagged as a long code block"
        )

    def test_code_block_at_threshold_boundary_not_flagged(self):
        # Exactly CODE_BLOCK_LINE_THRESHOLD - 1 interior lines = 14 lines → should NOT be flagged
        lines = "\n".join(f"line_{i} = {i}" for i in range(CODE_BLOCK_LINE_THRESHOLD - 1))
        block = f"```python\n{lines}\n```"
        assert not _unsolicited_long_code_block(block), (
            f"A code block with {CODE_BLOCK_LINE_THRESHOLD - 1} interior lines must not be flagged"
        )


# ── Rule 4: Mobile tone ───────────────────────────────────────────────────────

class TestMobileTone:
    def test_mobile_tone_guidance_present_in_skill(self):
        content = _skill_text()
        assert re.search(r"mobile|short.{0,20}paragraph|answer first", content, re.IGNORECASE), (
            "sam-context/SKILL.md must include mobile-calibrated tone guidance"
        )

    def test_bold_limit_stated_in_skill(self):
        content = _skill_text()
        assert re.search(r"bold.{0,30}(max|maximum|sparingly|limit|2)", content, re.IGNORECASE), (
            "sam-context/SKILL.md must state a limit on bold usage per message"
        )
```

### Step 5 — Run the tests

```bash
python3 -m pytest tests/test_telegram_constraints.py -v
```

All 15 tests must pass before proceeding to the commit step. If any test fails, the most common cause is a missing phrase in the SKILL.md — re-read the failing assertion message, which identifies the exact string or pattern that is absent, and add it to the appropriate rule section.

---

## 5. Tests

**File**: `tests/test_telegram_constraints.py` (shown in full in Step 4 above)

**Framework**: pytest (standard Python test runner; no custom plugins required)

**Test count delta**: N → N+15 passing

**Coverage matrix**:

| Test class | What it asserts |
|---|---|
| `TestSkillFileExists` (2 tests) | File exists at `sam-context/SKILL.md`; file is non-trivially populated |
| `TestCharacterCeiling` (5 tests) | SKILL.md states "4096"; SKILL.md describes split strategy; helper correctly passes short text, flags 4097-char text, and passes exactly-4096-char text |
| `TestNoMarkdownTables` (4 tests) | SKILL.md prohibits tables; SKILL.md names bullet lists as alternative; helper flags pipe-delimited rows; helper does not flag bullet lists |
| `TestCodeBlockConstraint` (5 tests) | SKILL.md mentions code block constraint; SKILL.md states "15"; helper flags 20-line block; helper passes 2-line snippet; helper passes 14-line block (at-threshold boundary) |
| `TestMobileTone` (2 tests) | SKILL.md contains mobile tone guidance; SKILL.md states a bold-usage limit |

**Run command**:
```bash
python3 -m pytest tests/test_telegram_constraints.py -v --tb=short
```

**Expected terminal output (last lines)**:
```
15 passed in 0.XXs
```

---

## 6. Commit Plan

**Two commits, in order:**

### Commit 1 — Test suite

Stage: `tests/__init__.py`, `tests/test_telegram_constraints.py`

```bash
git add tests/__init__.py tests/test_telegram_constraints.py
git commit -m "$(cat <<'EOF'
test: add Telegram constraint validation suite for Task 2

Adds 15 pytest tests covering the four Telegram behaviour rules
(character ceiling, table prohibition, code-block gate, mobile tone).
Tests will fail until sam-context/SKILL.md is authored in the next commit.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Commit 2 — SKILL.md authoring

Stage: `sam-context/SKILL.md`

```bash
git add sam-context/SKILL.md
git commit -m "$(cat <<'EOF'
feat: add Telegram behaviour constraints to sam-context skill

Authors the four Telegram formatting and tone rules in sam-context/SKILL.md:
hard 4096-char ceiling with split strategy, markdown-table prohibition,
unsolicited code-block gate at 15 lines, and mobile-calibrated tone guidance.
Skill-instruction enforcement only; hook enforcement deferred to Task 5.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## 7. Verification

Execute each check in order. All must pass before the task is considered done.

**V1 — Tests green**
```bash
python3 -m pytest tests/test_telegram_constraints.py -v --tb=short
# Expected: 15 passed, 0 failed, 0 errors
```

**V2 — Required phrases present**
```bash
grep -c "4096" sam-context/SKILL.md
# Expected: 1 or more

grep -ic "unsolicited" sam-context/SKILL.md
# Expected: 1 or more

grep -ic "mobile" sam-context/SKILL.md
# Expected: 1 or more
```

**V3 — File is UTF-8 clean and non-empty**
```bash
python3 -c "
import pathlib
text = pathlib.Path('sam-context/SKILL.md').read_text('utf-8')
assert len(text) >= 200, f'too short: {len(text)}'
print(f'OK — {len(text)} characters')
"
```

**V4 — No accidental pipe-table syntax introduced into the SKILL.md itself**
```bash
python3 -c "
import re, pathlib
text = pathlib.Path('sam-context/SKILL.md').read_text('utf-8')
# Exclude the replacement-example block (lines inside fenced code blocks)
outside_fences = re.sub(r'\x60{3}[\s\S]*?\x60{3}', '', text)
tables = re.findall(r'^\|.+\|', outside_fences, re.MULTILINE)
assert not tables, f'Found bare table rows outside fences: {tables}'
print('OK — no bare pipe-table rows in instructional prose')
"
```

**V5 — Git log confirms two clean commits**
```bash
git log --oneline -2
# Expected: two lines starting with "feat: add Telegram..." and "test: add Telegram..."
```

---

## 8. Rollback

**If the SKILL.md content causes problems in a live session** (agent misapplies rules, wrong channel detection):
```bash
# Revert only the SKILL.md commit (preserves test commit)
git revert HEAD --no-edit
```

**If both commits should be undone** (e.g. task is re-scoped before going live):
```bash
git revert HEAD HEAD~1 --no-edit
```

**Manual rollback** (if git revert cannot be used):
```bash
# Remove the Telegram section from SKILL.md — delete from the line
# "## Telegram Behaviour Constraints" to the end of the file,
# or to the start of the next section if Task 1 content follows it.
# Then run: python3 -m pytest tests/ to confirm tests fail cleanly (not error).
```

**Test-only rollback** (SKILL.md kept, tests removed):
```bash
git rm tests/test_telegram_constraints.py tests/__init__.py
git commit -m "revert: remove Telegram constraint tests (Task 2 rollback)"
```

No infrastructure changes, no database migrations, and no deployed services are affected by this rollback. The SKILL.md is a local file read by the OpenClaw process; removing or editing it takes effect on the next session start with no restart required.

---

## 9. Deviations Allowed

| Situation | Permitted deviation |
|---|---|
| Task 1 already created `sam-context/SKILL.md` with a different section header structure | Append the Telegram section using whatever heading level is consistent with the existing document; the tests assert content presence, not heading hierarchy |
| `pytest` is unavailable and cannot be installed in the executor's environment | Run the test file directly with `python3 -m unittest` after converting the classes to `unittest.TestCase` subclasses; assertions are structurally identical |
| OpenClaw uses a different SKILL filename convention (e.g. `SKILL.txt` or `skill.md`) | Rename the target file accordingly and update `SKILL_PATH` in `tests/test_telegram_constraints.py` to match |
| The line threshold for code blocks needs to be 20 instead of 15 to match a team convention | Change `15` to `20` in both `sam-context/SKILL.md` (Rule 3) and the `CODE_BLOCK_LINE_THRESHOLD` constant in the test file; all threshold tests will remain valid |
| Task 1 and Task 2 are merged into a single commit by the executor's git policy | Combine both staged sets and use the Task 2 commit message; note the merge in the commit body |

---

## 10. Out of Scope

The following are explicitly excluded from this task. Do not implement them here.

- **Hook-based enforcement** — intercepting the outbound message pipeline to programmatically truncate or reformat Telegram responses. This is deferred to Task 5 if skill-instruction self-limiting proves insufficient. Implementing it now would require a compiled plugin package that does not exist yet.
- **Channel detection via API call** — querying any service to confirm the active channel at runtime. Channel detection here is heuristic (session metadata inspection); live confirmation is a plugin graduation concern.
- **`sam-context` boot snapshot** — the session-start snapshot (date, service health, git state) that also lives in `sam-context/SKILL.md`. That is the domain of Task 1. This task leaves a `<!-- TASK 1 PLACEHOLDER -->` comment if the file is created fresh.
- **`sam-specDoc/SKILL.md` or `sam-projects/SKILL.md`** — separate skill files with separate owners; no edits to them are made here.
- **`openclaw.plugin.json`** — the plugin manifest is a graduation artefact; it is not created or modified in this task.
- **Automated session-level testing** — spinning up an OpenClaw instance and sending Telegram messages to verify agent behaviour end-to-end. That integration test belongs to a post-graduation QA phase.
- **Proactive formatting of existing MEMORY.md or USER.md content** — those files are outside this task's scope.