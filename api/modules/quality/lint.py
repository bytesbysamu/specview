"""modules/quality/lint.py — Pre-emit linter for task implementation guides.

Public surface:
    Flag                     — frozen dataclass: rule, severity, message, line
    EXPECTED_SECTION_COUNT   — coordination constant shared with the impl-guide template
    lint_task_guide(text)    — run all nine rules; caller enforces policy

Severity contract (structural, not configurable):
    "error"   — defect that can corrupt downstream executor behaviour; blocks the write
    "warning" — quality signal; file is written, flag surfaces in the polling response

Rules (run unconditionally, results accumulated):
    hash-first           (warning) — document must begin with a '#' heading
    preamble-leak        (error)   — model reasoning text before the first '#' heading
    stale-attribution    (warning) — hardcoded Co-Authored-By model version
    absolute-test-counts (warning) — absolute baseline count before a '→' arrow
    personal-path        (error)   — /Users/<name> or /home/<name> in document body
    placeholder-value    (error)   — unfilled template placeholders in document body
    empty-test-body      (error)   — stub test bodies in fenced code blocks
    section-count        (warning) — document has != EXPECTED_SECTION_COUNT '## N.' sections
    test-claim-delta     (warning) — Verification section missing or zero '+K passing' delta
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Public contract — Flag type is also imported by modules/quality/coherence.py
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Flag:
    """Immutable lint result.

    Attributes
    ----------
    rule      Short identifier matching one of the nine rule names above.
    severity  "error" (blocks write) or "warning" (file written, flag surfaced).
    message   Human-readable violation description.
    line      1-based line number of the first violation site, or None.
    """
    rule: str
    severity: str   # Literal["error", "warning"]
    message: str
    line: int | None = None


# ---------------------------------------------------------------------------
# Coordination constant — coupling point with the impl-guide prompt template.
#
# If the template's section count changes, this constant MUST change too.
# Search for EXPECTED_SECTION_COUNT to find all call sites before editing.
# ---------------------------------------------------------------------------

EXPECTED_SECTION_COUNT = 10


# ---------------------------------------------------------------------------
# Module-level compiled regexes — compiled once at import, reused per call
# ---------------------------------------------------------------------------

_PREAMBLE_PHRASES_RE = re.compile(
    r"(?i)\b(?:"
    r"let me\b|"
    r"now i\b|"
    r"i'?ll\b|"
    r"i will\b|"
    r"i need to\b|"
    r"i should\b|"
    r"i'?m going to\b|"
    r"alright,|"
    r"okay,?\s+let\b"
    r")",
)

_COAUTHOR_RE = re.compile(
    r"^[>\s]*Co-Authored-By:\s*Claude\s+\S+",
    re.IGNORECASE | re.MULTILINE,
)

_ABS_COUNT_RE = re.compile(r"\b\d{2,}\s*→")

_PERSONAL_PATH_RE = re.compile(r"/(?:Users|home)/[A-Za-z]")

_PLACEHOLDER_RE = re.compile(
    r"(?:"
    r"path/to/\w"                        # path/to/something
    r"|\{workspace-relative-path\}"      # unfilled template token (literal braces)
    r"|\[Step Name\]"                    # unfilled step heading
    r"|\[what to do,?\s+imperative\]"    # unfilled action block
    r"|\[current state\s*→"              # unfilled file state description
    r"|\[purpose;"                       # unfilled file purpose block
    r")",
    re.IGNORECASE,
)

_CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)

_STUB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"/\*\s*\.\.\.?\s*\*/"),           # /* ... */ or /* .. */
    re.compile(r"//\s+\.\.\."),                    # // ...
    re.compile(r"#\s+\.\.\."),                     # # ...
    re.compile(r"^\s+pass\s*$", re.MULTILINE),    # sole `pass` statement
]

_SECTION_RE = re.compile(r"^## \d+\.", re.MULTILINE)

_VERIFY_SECTION_RE = re.compile(
    r"^## 7\..*?(?=^## \d+\.|\Z)",
    re.DOTALL | re.MULTILINE,
)

_DELTA_CLAIM_RE = re.compile(r"\+(\d+)\s+passing")


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

def _rule_hash_first(text: str) -> list[Flag]:
    if not text.lstrip().startswith("#"):
        return [Flag(
            "hash-first", "warning",
            "Document does not begin with a '#' heading; executor may "
            "misparse leading content as spec body.",
            line=1,
        )]
    return []


def _rule_preamble_leak(text: str) -> list[Flag]:
    first_hash = text.find("#")
    preamble = text if first_hash == -1 else text[:first_hash]
    if preamble.strip() and _PREAMBLE_PHRASES_RE.search(preamble):
        return [Flag(
            "preamble-leak", "error",
            "Model reasoning text appears before the first '#' heading; "
            "the executor will read it as spec content.",
            line=1,
        )]
    return []


def _rule_stale_attribution(text: str) -> list[Flag]:
    flags: list[Flag] = []
    for i, line_text in enumerate(text.splitlines(), 1):
        if _COAUTHOR_RE.search(line_text):
            flags.append(Flag(
                "stale-attribution", "warning",
                f"Hardcoded Co-Authored-By model version on line {i}; "
                "inject from EXECUTOR_ATTRIBUTION block instead.",
                line=i,
            ))
    return flags


def _rule_absolute_test_counts(text: str) -> list[Flag]:
    flags: list[Flag] = []
    for i, line_text in enumerate(text.splitlines(), 1):
        if _ABS_COUNT_RE.search(line_text):
            flags.append(Flag(
                "absolute-test-counts", "warning",
                f"Absolute test-count baseline on line {i} (e.g. '192 →'); "
                "use a relative '+K passing' delta instead.",
                line=i,
            ))
    return flags


def _rule_personal_path(text: str) -> list[Flag]:
    flags: list[Flag] = []
    for i, line_text in enumerate(text.splitlines(), 1):
        if _PERSONAL_PATH_RE.search(line_text):
            flags.append(Flag(
                "personal-path", "error",
                f"Absolute personal filesystem path on line {i} "
                "(/Users/... or /home/...); use {{WORKSPACE}} or a repo-relative path.",
                line=i,
            ))
    return flags


def _rule_placeholder_value(text: str) -> list[Flag]:
    flags: list[Flag] = []
    for i, line_text in enumerate(text.splitlines(), 1):
        if _PLACEHOLDER_RE.search(line_text):
            flags.append(Flag(
                "placeholder-value", "error",
                f"Unfilled template placeholder on line {i}; "
                "replace every bracket/brace token with a concrete value.",
                line=i,
            ))
    return flags


def _rule_empty_test_body(text: str) -> list[Flag]:
    flags: list[Flag] = []
    for block_match in _CODE_BLOCK_RE.finditer(text):
        block_text = block_match.group(1)
        line_num = text[: block_match.start()].count("\n") + 1
        for stub_re in _STUB_PATTERNS:
            if stub_re.search(block_text):
                flags.append(Flag(
                    "empty-test-body", "error",
                    f"Stub test body in code block near line {line_num}; "
                    "write a complete assertion — no /* ... */ stubs.",
                    line=line_num,
                ))
                break  # one flag per code block, stop at first matching stub
    return flags


def _rule_section_count(text: str) -> list[Flag]:
    count = len(_SECTION_RE.findall(text))
    if count != EXPECTED_SECTION_COUNT:
        return [Flag(
            "section-count", "warning",
            f"Expected {EXPECTED_SECTION_COUNT} numbered '## N.' sections, "
            f"found {count}; check the impl-guide template for the required set.",
        )]
    return []


def _rule_test_claim_delta(text: str) -> list[Flag]:
    section_match = _VERIFY_SECTION_RE.search(text)
    if not section_match:
        return []  # absence of the section is caught by section-count rule
    section_text = section_match.group(0)
    delta_match = _DELTA_CLAIM_RE.search(section_text)
    if not delta_match:
        return [Flag(
            "test-claim-delta", "warning",
            "Verification section has no '+K passing' delta claim; "
            "add 'N → N+K passing' with K > 0.",
        )]
    if int(delta_match.group(1)) == 0:
        return [Flag(
            "test-claim-delta", "warning",
            "Verification section claims +0 new tests; delta must be positive.",
        )]
    return []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_RULES = [
    _rule_hash_first,
    _rule_preamble_leak,
    _rule_stale_attribution,
    _rule_absolute_test_counts,
    _rule_personal_path,
    _rule_placeholder_value,
    _rule_empty_test_body,
    _rule_section_count,
    _rule_test_claim_delta,
]


def lint_task_guide(text: str) -> list[Flag]:
    """Run all nine lint rules against ``text`` and return accumulated flags.

    All rules run unconditionally — the caller decides what to do with the
    flags. This function does not write, raise, or branch on severity.

    Returns an empty list when the document is clean.
    """
    flags: list[Flag] = []
    for rule_fn in _RULES:
        flags.extend(rule_fn(text))
    return flags
