"""Tests for modules/ai/services/text_prompts.py.

All functions are pure (no I/O, no Flask, no chain calls), so tests run
with no fixtures and no patches.
"""
from __future__ import annotations

import pytest

import modules.ai.services.text_prompts as _prompts


# ---------------------------------------------------------------------------
# Type contract: every public function returns a (str, str) tuple
# ---------------------------------------------------------------------------

def test_rewrite_prompt_returns_str_str_tuple():
    result = _prompts.rewrite_prompt("some text", "make it shorter")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


def test_iterate_prompt_returns_str_str_tuple():
    result = _prompts.iterate_prompt("base spec", "current doc", "builder", "principles")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


def test_lint_braindump_prompt_returns_str_str_tuple():
    result = _prompts.lint_braindump_prompt("here is my braindump")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


def test_generate_prompt_returns_str_str_tuple():
    result = _prompts.generate_prompt("write something", "builder ctx", "principles ctx", "formal")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


def test_bootstrap_analysis_prompt_returns_str_str_tuple():
    result = _prompts.bootstrap_analysis_prompt("braindump text", "My Project", "builder ctx")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


def test_bootstrap_epic_prompt_returns_str_str_tuple():
    result = _prompts.bootstrap_epic_prompt("braindump", "My Project", "analysis text", "builder", "principles")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


def test_bootstrap_architecture_prompt_returns_str_str_tuple():
    result = _prompts.bootstrap_architecture_prompt("braindump", "My Project", "epic text", "builder", "principles", "codebase", "references")
    assert isinstance(result, tuple) and len(result) == 2
    assert all(isinstance(s, str) for s in result)


# ---------------------------------------------------------------------------
# Non-empty contract: both strings must have content
# ---------------------------------------------------------------------------

def test_rewrite_prompt_returns_non_empty_strings():
    system, user = _prompts.rewrite_prompt("hello world", "rewrite it")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


def test_iterate_prompt_returns_non_empty_strings():
    system, user = _prompts.iterate_prompt("base", "current", "builder", "principles")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


def test_lint_braindump_prompt_returns_non_empty_strings():
    system, user = _prompts.lint_braindump_prompt("my braindump content")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


def test_generate_prompt_returns_non_empty_strings():
    system, user = _prompts.generate_prompt("write a spec", "", "", "")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


def test_bootstrap_analysis_prompt_returns_non_empty_strings():
    system, user = _prompts.bootstrap_analysis_prompt("bd", "Proj", "")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


def test_bootstrap_epic_prompt_returns_non_empty_strings():
    system, user = _prompts.bootstrap_epic_prompt("bd", "Proj", "analysis", "", "")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


def test_bootstrap_architecture_prompt_returns_non_empty_strings():
    system, user = _prompts.bootstrap_architecture_prompt("bd", "Proj", "epic", "", "", "", "")
    assert len(system.strip()) > 0
    assert len(user.strip()) > 0


# ---------------------------------------------------------------------------
# Content inclusion
# ---------------------------------------------------------------------------

def test_lint_braindump_prompt_includes_braindump_in_user_string():
    braindump = "unique-braindump-marker-xyzzy-42"
    _system, user = _prompts.lint_braindump_prompt(braindump)
    assert braindump in user, f"Braindump text must appear in user string; got: {user!r}"


def test_generate_prompt_includes_spec_content_in_user_string():
    prompt_text = "unique-generate-prompt-xyzzy-99"
    _system, user = _prompts.generate_prompt(prompt_text, "", "", "")
    assert prompt_text in user, f"Prompt text must appear in user string; got: {user!r}"


def test_bootstrap_analysis_prompt_includes_braindump_and_project_name():
    braindump = "unique-analysis-braindump-abc"
    project_name = "UniqueProjectAlpha"
    _system, user = _prompts.bootstrap_analysis_prompt(braindump, project_name, "")
    assert braindump in user, "braindump must be in user string"
    assert project_name in user, "project_name must be in user string"


def test_bootstrap_epic_prompt_includes_braindump_analysis_and_project_name():
    braindump = "unique-epic-braindump-def"
    analysis = "unique-analysis-text-ghi"
    project_name = "UniqueProjectBeta"
    _system, user = _prompts.bootstrap_epic_prompt(braindump, project_name, analysis, "", "")
    assert braindump in user, "braindump must be in user string"
    assert analysis in user, "analysis must be in user string"
    assert project_name in user, "project_name must be in user string"


def test_bootstrap_architecture_prompt_includes_braindump_epic_and_project_name():
    braindump = "unique-arch-braindump-jkl"
    epic = "unique-epic-text-mno"
    project_name = "UniqueProjectGamma"
    _system, user = _prompts.bootstrap_architecture_prompt(braindump, project_name, epic, "", "", "", "")
    assert braindump in user, "braindump must be in user string"
    assert epic in user, "epic must be in user string"
    assert project_name in user, "project_name must be in user string"


# ---------------------------------------------------------------------------
# No absolute personal paths in prompt output
# ---------------------------------------------------------------------------

def test_rewrite_prompt_no_absolute_personal_paths():
    system, user = _prompts.rewrite_prompt("text", "instruction")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user


def test_iterate_prompt_no_absolute_personal_paths():
    system, user = _prompts.iterate_prompt("base", "current", "builder", "principles")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user


def test_lint_braindump_prompt_no_absolute_personal_paths():
    system, user = _prompts.lint_braindump_prompt("braindump")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user


def test_generate_prompt_no_absolute_personal_paths():
    system, user = _prompts.generate_prompt("write", "builder", "principles", "formal")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user


def test_bootstrap_analysis_prompt_no_absolute_personal_paths():
    system, user = _prompts.bootstrap_analysis_prompt("bd", "Proj", "builder")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user


def test_bootstrap_epic_prompt_no_absolute_personal_paths():
    system, user = _prompts.bootstrap_epic_prompt("bd", "Proj", "analysis", "builder", "principles")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user


def test_bootstrap_architecture_prompt_no_absolute_personal_paths():
    system, user = _prompts.bootstrap_architecture_prompt("bd", "Proj", "epic", "builder", "principles", "codebase", "refs")
    assert "/Users/" not in system + user
    assert "/home/" not in system + user
