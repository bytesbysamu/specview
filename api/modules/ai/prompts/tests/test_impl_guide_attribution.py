# modules/implementation_guide/tests/test_attribution.py
"""Unit tests for EXECUTOR_ATTRIBUTION and its injection into the impl-guide prompt.

No I/O. No snapshots. Fast property assertions only.
Naming convention: camelCaseSubject_condition (matches python_functions *_*).
"""
from modules.ai.prompts import impl_guide as _prompts
executorAttribution = _prompts.EXECUTOR_ATTRIBUTION
formatModelDisplay = _prompts._format_model_display
buildPrompt = _prompts.build_implementation_guide_prompt

_MINIMAL = dict(
    task_num="1", task_name="T", task_effort="1d",
    task_desc="desc", arch="arch",
)


# ---------------------------------------------------------------------------
# EXECUTOR_ATTRIBUTION constant — structural invariants
# ---------------------------------------------------------------------------

def executorAttribution_hasCoAuthorTrailerKey():
    assert "co_author_trailer" in executorAttribution, (
        "EXECUTOR_ATTRIBUTION must expose 'co_author_trailer'"
    )


def executorAttribution_hasModelIdKey():
    assert "model_id" in executorAttribution, (
        "EXECUTOR_ATTRIBUTION must expose 'model_id'"
    )
    assert executorAttribution["model_id"], "model_id must be non-empty"


def executorAttribution_trailerStartsWithCoAuthoredBy():
    trailer = executorAttribution["co_author_trailer"]
    assert trailer.startswith("Co-Authored-By: "), (
        f"Trailer must start with 'Co-Authored-By: ', got: {trailer!r}"
    )


def executorAttribution_trailerContainsClaude():
    assert "Claude" in executorAttribution["co_author_trailer"], (
        "Trailer must contain 'Claude' display name"
    )


def executorAttribution_trailerContainsEmail():
    assert "<noreply@anthropic.com>" in executorAttribution["co_author_trailer"], (
        "Trailer must contain the Anthropic no-reply email"
    )


# ---------------------------------------------------------------------------
# _format_model_display helper
# ---------------------------------------------------------------------------

def formatModelDisplay_canonicalSonnetId_returnsDisplayName():
    assert formatModelDisplay("claude-sonnet-4-5") == "Claude Sonnet 4.5", (
        "Expected 'Claude Sonnet 4.5' for canonical sonnet ID"
    )


def formatModelDisplay_opusId_returnsDisplayName():
    assert formatModelDisplay("claude-opus-4-5") == "Claude Opus 4.5", (
        "Expected 'Claude Opus 4.5' for opus model ID"
    )


def formatModelDisplay_haikuId_returnsDisplayName():
    assert formatModelDisplay("claude-haiku-3-5") == "Claude Haiku 3.5", (
        "Expected 'Claude Haiku 3.5' for haiku model ID"
    )


def formatModelDisplay_withoutClaudePrefix_returnsDisplayName():
    # CLAUDE_CODE_MODEL may omit the 'claude-' prefix on some platforms
    assert formatModelDisplay("sonnet-4-5") == "Claude Sonnet 4.5", (
        "Must handle model IDs without the 'claude-' prefix"
    )


# ---------------------------------------------------------------------------
# Attribution injection into build_implementation_guide_prompt()
# ---------------------------------------------------------------------------

def buildPrompt_userContainsExecutorAttributionSection():
    _, user = buildPrompt(**_MINIMAL)
    assert "EXECUTOR ATTRIBUTION" in user, (
        "User prompt must contain the EXECUTOR ATTRIBUTION section heading"
    )


def buildPrompt_userContainsCoAuthorTrailerVerbatim():
    _, user = buildPrompt(**_MINIMAL)
    trailer = executorAttribution["co_author_trailer"]
    assert trailer in user, (
        f"Expected co_author_trailer {trailer!r} to appear verbatim in user prompt"
    )


def buildPrompt_hardRuleProhibitsInventedModelVersion():
    # The prohibition must live in _USER_HEADER so it appears before any context section
    _, user = buildPrompt(**_MINIMAL)
    assert "Never invent" in user, (
        "Hard rule prohibiting invented model versions is missing from _USER_HEADER"
    )


def buildPrompt_attributionSection_appearsBeforeTaskHeader():
    _, user = buildPrompt(**_MINIMAL)
    attr_pos = user.index("EXECUTOR ATTRIBUTION")
    task_pos = user.index("# Task 1:")
    assert attr_pos < task_pos, (
        "EXECUTOR ATTRIBUTION section must appear before the task header so the "
        "model sees the attribution value before it writes the commit plan"
    )


def buildPrompt_attributionSection_alwaysPresentWithNoOptionalContext():
    """Attribution is injected even when all optional strings are empty."""
    _, user = buildPrompt(
        task_num="5", task_name="Any Task", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="", principles="", codebase="", references="", prior="",
    )
    assert "EXECUTOR ATTRIBUTION" in user, (
        "Attribution section must appear regardless of optional context"
    )
