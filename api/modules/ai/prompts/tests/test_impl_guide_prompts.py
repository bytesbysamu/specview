# modules/implementation_guide/tests/test_impl_guide_prompts.py
"""Unit tests for build_implementation_guide_prompt().

No I/O. No snapshots. Fast property assertions only.
"""
from modules.ai.prompts import impl_guide as _prompts
# Aliases with no underscores avoid pytest collection under python_functions=["test_*", "*_*"]
buildPrompt = _prompts.build_implementation_guide_prompt


def buildPrompt_returnsSystemUserTuple():
    result = buildPrompt(
        task_num="1", task_name="Unify Context Services",
        task_effort="1 day", task_desc="### Task 1: details",
        arch="# Architecture", builder="", principles="", codebase="", references="", prior="",
    )
    assert isinstance(result, tuple)
    assert len(result) == 2


def buildPrompt_systemIsSeniorEngineerRole():
    system, _ = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
    )
    assert "senior engineer" in system
    assert "You are" in system


def buildPrompt_userContainsTaskNumAndName():
    _, user = buildPrompt(
        task_num="3", task_name="Extract Template Generators",
        task_effort="0.5 days", task_desc="desc", arch="arch",
    )
    assert "Task 3:" in user
    assert "Extract Template Generators" in user


def buildPrompt_userContainsEffort():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1.5 days",
        task_desc="desc", arch="arch",
    )
    assert "1.5 days" in user


def buildPrompt_userContainsRequiredSectionsHeader():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
    )
    assert "Required Sections" in user
    assert "Implementation Steps" in user


def buildPrompt_userContainsHardRules():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
    )
    assert "{WORKSPACE}" in user
    assert "NO empty test bodies" in user


def buildPrompt_embedsBuilderSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="I ship fast.",
    )
    assert "BUILDER CONTEXT" in user
    assert "I ship fast." in user


def buildPrompt_omitsBuilderSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="",
    )
    assert "BUILDER CONTEXT" not in user


def buildPrompt_embedsPrinciplesSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        principles="Ship fast, validate first.",
    )
    assert "ARCHITECTURE PRINCIPLES" in user
    assert "Ship fast, validate first." in user


def buildPrompt_omitsPrinciplesSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        principles="",
    )
    assert "ARCHITECTURE PRINCIPLES" not in user


def buildPrompt_embedsCodebaseSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        codebase="src/main.py",
    )
    assert "CODEBASE CONTEXT" in user
    assert "src/main.py" in user


def buildPrompt_embedsReferencesSection_whenProvided():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        references="# Reference\nExample code.",
    )
    assert "REFERENCE CODE" in user
    assert "Example code." in user


def buildPrompt_embedsPriorTasksSection_whenProvided():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        prior="### task-1-unify.md\nPrior task content.",
    )
    assert "PRIOR-TASK CONTRACTS" in user
    assert "Prior task content." in user


def buildPrompt_omitsPriorTasksSection_whenEmpty():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        prior="",
    )
    assert "PRIOR-TASK CONTRACTS" not in user


def buildPrompt_embedsArchInUser():
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc",
        arch="## Architecture Overview\nFluent builder pattern.",
    )
    assert "CONTEXT FROM ARCHITECTURE" in user
    assert "Fluent builder pattern." in user


def buildPrompt_embedsTaskDescInUser():
    _, user = buildPrompt(
        task_num="2", task_name="T", task_effort="1d",
        task_desc="### Task 2: Migrate Prompts\nCreate PromptBuilder.",
        arch="arch",
    )
    assert "CONTEXT FROM EPIC" in user
    assert "Create PromptBuilder." in user


def buildPrompt_allContextPresent_sectionsInCorrectOrder():
    """Context sections appear before the task header."""
    _, user = buildPrompt(
        task_num="1", task_name="T", task_effort="1d",
        task_desc="desc", arch="arch",
        builder="builder text",
        prior="prior text",
    )
    builder_pos = user.index("builder text")
    prior_pos = user.index("prior text")
    task_pos = user.index("# Task 1:")
    assert builder_pos < task_pos, "BUILDER CONTEXT must appear before task header"
    assert prior_pos < task_pos, "PRIOR-TASK CONTRACTS must appear before task header"
