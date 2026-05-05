# modules/task_gen/tests/test_service_helpers.py
"""Unit tests for the pure helpers in modules.ai.services.task_gen.

Covers task-finding logic (next missing task, allDone detection),
task-description extraction, prior-task collection, and filename
derivation. No threads, no Flask, no I/O.
"""
from modules.ai.services import task_gen as _svc

findNextMissingTask = _svc.find_next_missing_task
extractTaskDesc = _svc.extract_task_desc
collectPriorContent = _svc.collect_prior_task_content
deriveFilename = _svc.derive_task_filename


# ---------------------------------------------------------------------------
# find_next_missing_task — the core "what should I generate next?" logic
# ---------------------------------------------------------------------------

def findNext_noFilesPresent_returnsFirstTask():
    tasks = [
        {"num": "1", "name": "Alpha", "effort": "1 day"},
        {"num": "2", "name": "Beta", "effort": "1 day"},
    ]
    assert findNextMissingTask(tasks, []) == tasks[0]


def findNext_firstTaskHasFile_returnsSecond():
    tasks = [
        {"num": "1", "name": "Alpha", "effort": "1 day"},
        {"num": "2", "name": "Beta", "effort": "1 day"},
    ]
    files = ["epic.md", "task-1-alpha.md"]
    assert findNextMissingTask(tasks, files) == tasks[1]


def findNext_allTasksHaveFiles_returnsNone():
    tasks = [
        {"num": "1", "name": "Alpha", "effort": "1 day"},
        {"num": "2", "name": "Beta", "effort": "1 day"},
    ]
    files = ["task-1-alpha.md", "task-2-beta.md", "epic.md"]
    assert findNextMissingTask(tasks, files) is None


def findNext_outOfOrderFiles_skipsByNum():
    # Task 2 has a file but task 1 does not — we should still pick task 1
    tasks = [
        {"num": "1", "name": "Alpha", "effort": "1d"},
        {"num": "2", "name": "Beta", "effort": "1d"},
    ]
    files = ["task-2-beta.md"]
    assert findNextMissingTask(tasks, files) == tasks[0]


def findNext_filenameWithoutTaskPrefix_ignored():
    tasks = [{"num": "1", "name": "Alpha", "effort": "1d"}]
    files = ["alpha.md", "task-overview.md", "epic.md"]
    # None of these match the task-{num}-*.md pattern → task 1 is still missing
    assert findNextMissingTask(tasks, files) == tasks[0]


def findNext_emptyTaskList_returnsNone():
    assert findNextMissingTask([], ["task-1-x.md"]) is None


# ---------------------------------------------------------------------------
# extract_task_desc — pull the `### Task N: ...` block from epic.md
# ---------------------------------------------------------------------------

def extractDesc_blockExists_returnsBlockContent():
    epic = (
        "# Epic\n\n"
        "### Task 1: Foo\n"
        "Foo description body.\n\n"
        "### Task 2: Bar\n"
        "Bar description body.\n"
    )
    desc = extractTaskDesc(epic, "1")
    assert "Task 1: Foo" in desc
    assert "Foo description body" in desc
    # Should stop at the next `#` heading
    assert "Bar description body" not in desc


def extractDesc_taskNumNotFound_returnsEmptyString():
    epic = "### Task 1: Only\nbody\n"
    assert extractTaskDesc(epic, "9") == ""


def extractDesc_lastTaskInDoc_capturesToEnd():
    epic = "### Task 1: Last\nbody line\nmore body\n"
    desc = extractTaskDesc(epic, "1")
    assert "more body" in desc


# ---------------------------------------------------------------------------
# collect_prior_task_content — concatenate task-N-*.md where N < current
# ---------------------------------------------------------------------------

def collectPrior_onlyEarlierTasksIncluded():
    specs = [
        {"filename": "epic.md", "content": "ignore"},
        {"filename": "task-1-alpha.md", "content": "alpha body"},
        {"filename": "task-2-beta.md", "content": "beta body"},
        {"filename": "task-3-gamma.md", "content": "gamma body"},
    ]
    out = collectPriorContent(specs, current_task_num="3")
    assert "alpha body" in out
    assert "beta body" in out
    assert "gamma body" not in out


def collectPrior_noEarlierTasks_returnsEmptyString():
    specs = [{"filename": "task-2-beta.md", "content": "beta body"}]
    assert collectPriorContent(specs, current_task_num="1") == ""


def collectPrior_truncatesEachTaskByLines():
    long_body = "\n".join(f"line {i}" for i in range(200))
    specs = [{"filename": "task-1-x.md", "content": long_body}]
    out = collectPriorContent(specs, current_task_num="2", lines_per_task=5)
    # Only the first 5 lines of the body survive
    assert "line 4" in out
    assert "line 5" not in out


# ---------------------------------------------------------------------------
# derive_task_filename — slug the task name into task-N-<slug>.md
# ---------------------------------------------------------------------------

def deriveFilename_simpleName_lowercaseHyphenated():
    assert deriveFilename("1", "Unify Context Services") == "task-1-unify-context-services.md"


def deriveFilename_nameWithPunctuation_strippedToSlug():
    assert deriveFilename("3", "Add CI/CD!?") == "task-3-add-ci-cd.md"


def deriveFilename_emptyName_fallsBackToTaskWord():
    assert deriveFilename("4", "") == "task-4-task.md"
