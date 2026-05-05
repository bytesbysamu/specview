from __future__ import annotations
"""Unit tests for bootstrap prompt functions in modules/ai/prompts/__init__.py."""
# Import via module alias so pytest's *_* collection rule doesn't treat the
# imported function names themselves as test cases (same pattern as test_prompts.py).
import modules.ai.prompts as _p

bootstrapAnalysis = _p.bootstrap_analysis_prompt
bootstrapEpic = _p.bootstrap_epic_prompt
bootstrapArchitecture = _p.bootstrap_architecture_prompt
bootstrapExtract = _p.bootstrap_extract_tasks

_EPIC_WITH_TASKS = """\
# Epic: Test

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Build the thing** | None | — | 1 day | High |
| 2 | **Write the tests** | Task 1 | — | 0.5 days | Medium |
| 3 | **Ship it** | Task 2 | — | 0.5 days | Low |
"""


# ---------------------------------------------------------------------------
# bootstrap_analysis_prompt
# ---------------------------------------------------------------------------

def bootstrapAnalysisPrompt_braindumpAppearsInUserPrompt():
    _, user = bootstrapAnalysis("my braindump text", "My Project", "")
    assert "my braindump text" in user


def bootstrapAnalysisPrompt_projectNameAppearsInUserPrompt():
    _, user = bootstrapAnalysis("braindump", "My Project", "")
    assert "My Project" in user


def bootstrapAnalysisPrompt_builderBlockIncluded_whenProvided():
    _, user = bootstrapAnalysis("braindump", "Proj", "I am a solo founder")
    assert "I am a solo founder" in user


def bootstrapAnalysisPrompt_builderBlockOmitted_whenEmpty():
    _, user = bootstrapAnalysis("braindump", "Proj", "")
    assert "BUILDER CONTEXT" not in user


def bootstrapAnalysisPrompt_returnsTupleOfStrings():
    result = bootstrapAnalysis("dump", "Proj", "")
    assert isinstance(result, tuple) and len(result) == 2
    system, user = result
    assert isinstance(system, str) and isinstance(user, str)


def bootstrapAnalysisPrompt_systemIsMarkdownSpecWriter():
    system, _ = bootstrapAnalysis("dump", "Proj", "")
    assert "markdown spec writer" in system.lower()


# ---------------------------------------------------------------------------
# bootstrap_epic_prompt
# ---------------------------------------------------------------------------

def bootstrapEpicPrompt_braindumpAppearsInUserPrompt():
    _, user = bootstrapEpic("my braindump", "My Project", "", "", "")
    assert "my braindump" in user


def bootstrapEpicPrompt_projectNameAppearsInUserPrompt():
    _, user = bootstrapEpic("dump", "My Project", "", "", "")
    assert "My Project" in user


def bootstrapEpicPrompt_analysisBlockIncluded_whenProvided():
    _, user = bootstrapEpic("dump", "Proj", "analysis output here", "", "")
    assert "analysis output here" in user


def bootstrapEpicPrompt_analysisBlockOmitted_whenEmpty():
    _, user = bootstrapEpic("dump", "Proj", "", "", "")
    assert "CONTEXT FROM ANALYSIS" not in user


def bootstrapEpicPrompt_principlesBlockIncluded_whenProvided():
    _, user = bootstrapEpic("dump", "Proj", "", "", "ship fast, no debt")
    assert "ship fast, no debt" in user


def bootstrapEpicPrompt_builderBlockIncluded_whenProvided():
    _, user = bootstrapEpic("dump", "Proj", "", "I am a solo founder", "")
    assert "I am a solo founder" in user


def bootstrapEpicPrompt_returnsTupleOfStrings():
    result = bootstrapEpic("dump", "Proj", "", "", "")
    assert isinstance(result, tuple) and len(result) == 2


# ---------------------------------------------------------------------------
# bootstrap_architecture_prompt
# ---------------------------------------------------------------------------

def bootstrapArchitecturePrompt_braindumpAppearsInUserPrompt():
    _, user = bootstrapArchitecture("my braindump", "Proj", "", "", "", "", "")
    assert "my braindump" in user


def bootstrapArchitecturePrompt_projectNameAppearsInUserPrompt():
    _, user = bootstrapArchitecture("dump", "My Project", "", "", "", "", "")
    assert "My Project" in user


def bootstrapArchitecturePrompt_epicBlockIncluded_whenProvided():
    _, user = bootstrapArchitecture("dump", "Proj", "epic content here", "", "", "", "")
    assert "epic content here" in user


def bootstrapArchitecturePrompt_epicBlockOmitted_whenEmpty():
    _, user = bootstrapArchitecture("dump", "Proj", "", "", "", "", "")
    assert "CONTEXT FROM EPIC" not in user


def bootstrapArchitecturePrompt_codebaseBlockIncluded_whenProvided():
    _, user = bootstrapArchitecture("dump", "Proj", "", "", "", "Flask + Angular codebase", "")
    assert "Flask + Angular codebase" in user


def bootstrapArchitecturePrompt_referencesBlockIncluded_whenProvided():
    _, user = bootstrapArchitecture("dump", "Proj", "", "", "", "", "see express server.js")
    assert "see express server.js" in user


def bootstrapArchitecturePrompt_allOptionalContextsOmitted_whenEmpty():
    # Check for section headers (## prefix), not bare strings — the routing
    # rules template mentions "REFERENCE CODE" without ## even when empty.
    _, user = bootstrapArchitecture("dump", "Proj", "", "", "", "", "")
    assert "## CODEBASE CONTEXT" not in user
    assert "## REFERENCE CODE" not in user
    assert "## ARCHITECTURE PRINCIPLES" not in user


def bootstrapArchitecturePrompt_returnsTupleOfStrings():
    result = bootstrapArchitecture("dump", "Proj", "", "", "", "", "")
    assert isinstance(result, tuple) and len(result) == 2


# ---------------------------------------------------------------------------
# bootstrap_extract_tasks
# ---------------------------------------------------------------------------

def bootstrapExtractTasks_parsesAllThreeRows():
    tasks = bootstrapExtract(_EPIC_WITH_TASKS)
    assert len(tasks) == 3


def bootstrapExtractTasks_taskNumIsString():
    tasks = bootstrapExtract(_EPIC_WITH_TASKS)
    assert tasks[0]["num"] == "1"
    assert tasks[1]["num"] == "2"
    assert tasks[2]["num"] == "3"


def bootstrapExtractTasks_taskNameStripped():
    tasks = bootstrapExtract(_EPIC_WITH_TASKS)
    assert tasks[0]["name"] == "Build the thing"
    assert tasks[1]["name"] == "Write the tests"
    assert tasks[2]["name"] == "Ship it"


def bootstrapExtractTasks_effortStripped():
    tasks = bootstrapExtract(_EPIC_WITH_TASKS)
    assert tasks[0]["effort"] == "1 day"
    assert tasks[1]["effort"] == "0.5 days"


def bootstrapExtractTasks_emptyEpic_returnsEmptyList():
    tasks = bootstrapExtract("")
    assert tasks == []


def bootstrapExtractTasks_noTableRows_returnsEmptyList():
    tasks = bootstrapExtract("# Epic\n\nNo tasks here.\n")
    assert tasks == []


def bootstrapExtractTasks_headerRowNotIncluded():
    """The separator row (|---|---...) must not appear in results."""
    tasks = bootstrapExtract(_EPIC_WITH_TASKS)
    for t in tasks:
        assert "---" not in t["num"]
        assert "---" not in t["name"]
