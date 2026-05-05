"""Unit tests for modules.quality.lint — all nine rules + entry point.

No Flask, no threads, no I/O. Pure function tests only.

Naming convention notes:
- pyproject.toml sets python_functions = ["test_*", "*_*"]; module-level
  helpers and re-exports must be camelCase (no underscores) so they are
  not collected as tests. Aliases below replace the snake_case imports
  with collection-safe names.
"""
import textwrap

from modules.quality import lint as _lint

# Aliases without underscores avoid test collection.
EXPECTED_SECTION_COUNT = _lint.EXPECTED_SECTION_COUNT
Flag = _lint.Flag
lintTaskGuide = _lint.lint_task_guide


# ---------------------------------------------------------------------------
# Helpers — camelCase to avoid pytest collection
# ---------------------------------------------------------------------------

def makeCleanDoc(verify_line: str = "**Expected delta**: +5 passing.") -> str:
    """Return a minimal document that passes all nine rules."""
    sections = "\n".join(
        f"## {i}. {'Verification' if i == 7 else f'Section {i}'}\n"
        f"{verify_line if i == 7 else 'Body.'}\n"
        for i in range(1, 11)
    )
    code_block = textwrap.dedent("""\
        ```python
        def check_something():
            assert 1 + 1 == 2
        ```
    """)
    return f"# Task Guide\n\n{sections}\n{code_block}"


def flagsByRule(flags, rule):
    return [f for f in flags if f.rule == rule]


# ---------------------------------------------------------------------------
# Rule 1: hash-first
# ---------------------------------------------------------------------------

def hashFirst_docStartsWithHash_noFlag():
    doc = "# Title\n\n## 1. Section\nBody.\n"
    assert flagsByRule(lintTaskGuide(doc), "hash-first") == []


def hashFirst_leadingNewlineThenHash_noFlag():
    doc = "\n\n# Title\n## 1. Section\nBody.\n"
    assert flagsByRule(lintTaskGuide(doc), "hash-first") == []


def hashFirst_docStartsWithText_returnsWarning():
    doc = "Some leading prose\n# Title\n"
    flags = flagsByRule(lintTaskGuide(doc), "hash-first")
    assert len(flags) == 1
    assert flags[0].severity == "warning"
    assert flags[0].line == 1


# ---------------------------------------------------------------------------
# Rule 2: preamble-leak
# ---------------------------------------------------------------------------

def preambleLeak_noTextBeforeHash_noFlag():
    doc = "# Title\nContent."
    assert flagsByRule(lintTaskGuide(doc), "preamble-leak") == []


def preambleLeak_thinkingPhraseBeforeHash_returnsError():
    doc = "Let me think about this carefully.\n# Title\nContent."
    flags = flagsByRule(lintTaskGuide(doc), "preamble-leak")
    assert len(flags) == 1
    assert flags[0].severity == "error"
    assert flags[0].line == 1


def preambleLeak_neutralWordBeforeHash_noFlag():
    # "Context:" before # is not a thinking phrase
    doc = "Context: this guide covers X.\n# Title\nContent."
    assert flagsByRule(lintTaskGuide(doc), "preamble-leak") == []


# ---------------------------------------------------------------------------
# Rule 3: stale-attribution
# ---------------------------------------------------------------------------

def staleAttribution_noCoAuthor_noFlag():
    doc = "# Title\nNo attribution line here."
    assert flagsByRule(lintTaskGuide(doc), "stale-attribution") == []


def staleAttribution_coAuthorWithModel_returnsWarning():
    doc = "# Title\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>\n"
    flags = flagsByRule(lintTaskGuide(doc), "stale-attribution")
    assert len(flags) == 1
    assert flags[0].severity == "warning"
    assert flags[0].line == 3


def staleAttribution_twoCoAuthorLines_returnsTwoWarnings():
    doc = (
        "# Title\n"
        "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>\n"
        "Co-Authored-By: Claude Opus 4.0 <noreply@anthropic.com>\n"
    )
    flags = flagsByRule(lintTaskGuide(doc), "stale-attribution")
    assert len(flags) == 2


# ---------------------------------------------------------------------------
# Rule 4: absolute-test-counts
# ---------------------------------------------------------------------------

def absoluteTestCounts_noArrow_noFlag():
    doc = "# Title\n**Expected delta**: +5 passing.\n"
    assert flagsByRule(lintTaskGuide(doc), "absolute-test-counts") == []


def absoluteTestCounts_twoDigitBeforeArrow_returnsWarning():
    doc = "# Title\n**Expected delta**: 192 → 197 passing.\n"
    flags = flagsByRule(lintTaskGuide(doc), "absolute-test-counts")
    assert len(flags) == 1
    assert flags[0].severity == "warning"


def absoluteTestCounts_singleDigitBeforeArrow_noFlag():
    # One-digit baseline (e.g. "5 →") is not flagged — \d{2,} requires 2+ digits
    doc = "# Title\n5 → 10 passing.\n"
    assert flagsByRule(lintTaskGuide(doc), "absolute-test-counts") == []


# ---------------------------------------------------------------------------
# Rule 5: personal-path
# ---------------------------------------------------------------------------

def personalPath_noPersonalPath_noFlag():
    doc = "# Title\nSee `{WORKSPACE}/spec-doc/api/` for details.\n"
    assert flagsByRule(lintTaskGuide(doc), "personal-path") == []


def personalPath_usersPath_returnsError():
    doc = "# Title\nFile at /Users/sam/Projects/api/foo.py.\n"
    flags = flagsByRule(lintTaskGuide(doc), "personal-path")
    assert len(flags) == 1
    assert flags[0].severity == "error"


def personalPath_homePath_returnsError():
    doc = "# Title\nFile at /home/deploy/app/config.yaml.\n"
    flags = flagsByRule(lintTaskGuide(doc), "personal-path")
    assert len(flags) == 1
    assert flags[0].severity == "error"


# ---------------------------------------------------------------------------
# Rule 6: placeholder-value
# ---------------------------------------------------------------------------

def placeholderValue_noPlaceholder_noFlag():
    doc = "# Title\nModify `spec-doc/api/modules/quality/lint.py`.\n"
    assert flagsByRule(lintTaskGuide(doc), "placeholder-value") == []


def placeholderValue_pathToWord_returnsError():
    doc = "# Title\nRun `cd path/to/project && make test`.\n"
    flags = flagsByRule(lintTaskGuide(doc), "placeholder-value")
    assert len(flags) == 1
    assert flags[0].severity == "error"


def placeholderValue_workspaceToken_returnsError():
    doc = "# Title\nModify `{workspace-relative-path}` — the service file.\n"
    flags = flagsByRule(lintTaskGuide(doc), "placeholder-value")
    assert len(flags) == 1
    assert flags[0].severity == "error"


# ---------------------------------------------------------------------------
# Rule 7: empty-test-body
# ---------------------------------------------------------------------------

def emptyTestBody_noCodeBlocks_noFlag():
    doc = "# Title\nNo code blocks here.\n"
    assert flagsByRule(lintTaskGuide(doc), "empty-test-body") == []


def emptyTestBody_stubSlashStarInBlock_returnsError():
    doc = textwrap.dedent("""\
        # Title
        ```javascript
        it('does something', () => {
          /* ... */
        });
        ```
    """)
    flags = flagsByRule(lintTaskGuide(doc), "empty-test-body")
    assert len(flags) == 1
    assert flags[0].severity == "error"


def emptyTestBody_concreteAssertionInBlock_noFlag():
    doc = textwrap.dedent("""\
        # Title
        ```python
        def verify_x():
            result = compute(42)
            assert result == 84, "compute should double the input"
        ```
    """)
    assert flagsByRule(lintTaskGuide(doc), "empty-test-body") == []


# ---------------------------------------------------------------------------
# Rule 8: section-count
# ---------------------------------------------------------------------------

def sectionCount_exactlyTen_noFlag():
    sections = "\n".join(f"## {i}. Section {i}\nBody.\n" for i in range(1, 11))
    doc = f"# Title\n\n{sections}"
    assert flagsByRule(lintTaskGuide(doc), "section-count") == []


def sectionCount_fewerThanTen_returnsWarning():
    sections = "\n".join(f"## {i}. Section {i}\nBody.\n" for i in range(1, 10))
    doc = f"# Title\n\n{sections}"
    flags = flagsByRule(lintTaskGuide(doc), "section-count")
    assert len(flags) == 1
    assert flags[0].severity == "warning"
    assert "9" in flags[0].message  # found count mentioned
    assert str(EXPECTED_SECTION_COUNT) in flags[0].message


def sectionCount_moreThanTen_returnsWarning():
    sections = "\n".join(f"## {i}. Section {i}\nBody.\n" for i in range(1, 12))
    doc = f"# Title\n\n{sections}"
    flags = flagsByRule(lintTaskGuide(doc), "section-count")
    assert len(flags) == 1
    assert flags[0].severity == "warning"


# ---------------------------------------------------------------------------
# Rule 9: test-claim-delta
# ---------------------------------------------------------------------------

def testClaimDelta_noVerifySection_noFlag():
    # Without a "## 7." section the rule returns [] (section-count covers absence)
    doc = "# Title\n## 1. Context\nBody.\n"
    assert flagsByRule(lintTaskGuide(doc), "test-claim-delta") == []


def testClaimDelta_positiveDelta_noFlag():
    doc = "# Title\n## 7. Verification\n**Expected delta**: +5 passing.\n## 8. Next\nBody.\n"
    assert flagsByRule(lintTaskGuide(doc), "test-claim-delta") == []


def testClaimDelta_missingDeltaClaim_returnsWarning():
    doc = "# Title\n## 7. Verification\nRun the suite.\n## 8. Next\nBody.\n"
    flags = flagsByRule(lintTaskGuide(doc), "test-claim-delta")
    assert len(flags) == 1
    assert flags[0].severity == "warning"


def testClaimDelta_zeroDelta_returnsWarning():
    doc = "# Title\n## 7. Verification\n**Expected delta**: +0 passing.\n## 8. Next\nBody.\n"
    flags = flagsByRule(lintTaskGuide(doc), "test-claim-delta")
    assert len(flags) == 1
    assert flags[0].severity == "warning"


# ---------------------------------------------------------------------------
# Entry point: lint_task_guide
# ---------------------------------------------------------------------------

def lint_cleanDoc_returnsEmptyList():
    doc = makeCleanDoc()
    assert lintTaskGuide(doc) == []


def lint_personalPathAndStaleAttribution_returnsBothFlags():
    doc = (
        "# Title\n"
        "File: /Users/sam/Projects/api/service.py\n"
        "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>\n"
    )
    flags = lintTaskGuide(doc)
    rules_hit = {f.rule for f in flags}
    assert "personal-path" in rules_hit
    assert "stale-attribution" in rules_hit


def lint_errorFlagSeverityIsError():
    doc = "# Title\nFile: /Users/sam/Projects/api/service.py\n"
    flags = lintTaskGuide(doc)
    personal = [f for f in flags if f.rule == "personal-path"]
    assert personal[0].severity == "error", "personal-path must be error severity"
