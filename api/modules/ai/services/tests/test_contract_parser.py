# modules/task_gen/tests/test_contract_parser.py
"""Unit tests for the contract parser in modules.ai.services.task_gen.

Covers _parse_task_contract(), collect_prior_task_contracts(), and
_format_contracts(). No threads, no Flask, no I/O.
"""
from modules.ai.services import task_gen as _svc

parseContract = _svc._parse_task_contract
collectContracts = _svc.collect_prior_task_contracts
formatContracts = _svc._format_contracts

# ---------------------------------------------------------------------------
# Shared fixture text
# ---------------------------------------------------------------------------

_FULL_SECTION_THREE = """\
## 3. Files

### To Create (new)
- `modules/quality/lint.py` — pre-emit linter; no existing deps
- `modules/quality/__init__.py` — package init

### To Modify (cite CODEBASE CONTEXT)
- `modules/task_gen/service.py` — add contract parser calls

### To Leave Alone
- `modules/chain/adapter.py` — unchanged

## 4. Implementation Steps

Step content here.
"""

# ---------------------------------------------------------------------------
# _parse_task_contract
# ---------------------------------------------------------------------------


def parseContract_fullSectionThree_extractsCreatesAndModifies():
    result = parseContract(_FULL_SECTION_THREE)
    assert result["creates"] == [
        "modules/quality/lint.py",
        "modules/quality/__init__.py",
    ], "expected both (new) paths extracted in order"
    assert result["modifies"] == [
        "modules/task_gen/service.py",
    ], "expected single modify path extracted"
    assert result["exports"] == [], "no exports block present"


def parseContract_noFilesSectionInDoc_returnsEmptyLists():
    doc = (
        "# Task\n\n"
        "## 1. Context\n\nSome context.\n\n"
        "## 2. Pre-flight\n\nSome pre-flight.\n"
    )
    result = parseContract(doc)
    assert result == {"creates": [], "modifies": [], "exports": []}, (
        "document with no Files section must return all-empty lists"
    )


def parseContract_multiplePaths_inCreateSubsection_allExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Create (new)\n"
        "- `modules/quality/lint.py` — linter\n"
        "- `modules/quality/coherence.py` — coherence pass\n"
        "- `modules/quality/__init__.py` — package init\n"
    )
    result = parseContract(doc)
    assert result["creates"] == [
        "modules/quality/lint.py",
        "modules/quality/coherence.py",
        "modules/quality/__init__.py",
    ], "all three (new) paths must appear in order"


def parseContract_multiplePaths_inModifySubsection_allExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Modify (cite CODEBASE CONTEXT)\n"
        "- `modules/task_gen/service.py` — add contracts\n"
        "- `modules/implementation_guide/prompts.py` — rename section\n"
    )
    result = parseContract(doc)
    assert result["modifies"] == [
        "modules/task_gen/service.py",
        "modules/implementation_guide/prompts.py",
    ], "both modify paths must appear in order"


def parseContract_placeholderPaths_notExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Create (new)\n"
        "- `{workspace-relative-path}` — placeholder, not a real path\n"
    )
    result = parseContract(doc)
    assert result["creates"] == [], (
        "template placeholder containing '{' must be excluded from creates"
    )


def parseContract_exportsBlockPresent_exportsExtracted():
    doc = (
        "## 3. Files\n\n"
        "### To Create (new)\n"
        "- `modules/quality/lint.py` — linter\n\n"
        "## Exports\n\n"
        "- `modules/quality/lint.py` — lint_task_guide, Flag\n"
    )
    result = parseContract(doc)
    assert "modules/quality/lint.py" in result["exports"], (
        "path from Exports block must appear in exports list"
    )


def parseContract_onlyLeaveAloneSubsection_noCreatesOrModifies():
    doc = (
        "## 3. Files\n\n"
        "### To Leave Alone\n"
        "- `modules/chain/adapter.py` — no changes needed\n"
    )
    result = parseContract(doc)
    assert result["creates"] == [], "To Leave Alone must not populate creates"
    assert result["modifies"] == [], "To Leave Alone must not populate modifies"


# ---------------------------------------------------------------------------
# collect_prior_task_contracts
# ---------------------------------------------------------------------------

def collectContracts_multiplePriorTasks_dictKeyedByTaskNum():
    specs = [
        {"filename": "epic.md", "content": "ignore"},
        {"filename": "task-1-alpha.md", "content": _FULL_SECTION_THREE},
        {
            "filename": "task-2-beta.md",
            "content": (
                "## 3. Files\n\n"
                "### To Create (new)\n"
                "- `modules/new/thing.py` — new module\n"
            ),
        },
        {"filename": "task-3-gamma.md", "content": "not yet reached"},
    ]
    result = collectContracts(specs, current_task_num="3")
    assert set(result.keys()) == {"1", "2"}, (
        "only tasks 1 and 2 sort before current_task_num=3"
    )
    assert "modules/quality/lint.py" in result["1"]["creates"]
    assert "modules/new/thing.py" in result["2"]["creates"]


def collectContracts_noEarlierTasks_returnsEmptyDict():
    specs = [{"filename": "task-2-beta.md", "content": _FULL_SECTION_THREE}]
    result = collectContracts(specs, current_task_num="1")
    assert result == {}, "no task file sorts before task 1"


def collectContracts_currentTaskNotIncluded():
    specs = [
        {"filename": "task-1-alpha.md", "content": _FULL_SECTION_THREE},
        {
            "filename": "task-2-beta.md",
            "content": (
                "## 3. Files\n\n"
                "### To Create (new)\n"
                "- `x/y.py` — new\n"
            ),
        },
    ]
    result = collectContracts(specs, current_task_num="2")
    assert "2" not in result, "current task must be excluded even when its file is present"
    assert "1" in result, "prior task 1 must appear"


def collectContracts_priorTaskWithNoFileSection_emptyContractForThatTask():
    specs = [
        {"filename": "task-1-alpha.md", "content": "# Context only\nNo files section."}
    ]
    result = collectContracts(specs, current_task_num="2")
    assert result["1"] == {"creates": [], "modifies": [], "exports": []}, (
        "task with no §3 must produce an all-empty contract, not raise"
    )


# ---------------------------------------------------------------------------
# _format_contracts
# ---------------------------------------------------------------------------

def formatContracts_emptyDict_returnsEmptyString():
    assert formatContracts({}) == "", "empty dict must produce empty string"


def formatContracts_allEmptyContracts_returnsEmptyString():
    contracts = {"1": {"creates": [], "modifies": [], "exports": []}}
    assert formatContracts(contracts) == "", (
        "task with no declared paths must produce empty string "
        "so PromptBuilder.section() omits the block"
    )


def formatContracts_taskWithCreatesAndModifies_containsCorrectContent():
    contracts = {
        "1": {
            "creates": ["modules/quality/lint.py", "modules/quality/__init__.py"],
            "modifies": ["modules/task_gen/service.py"],
            "exports": [],
        }
    }
    out = formatContracts(contracts)
    assert "task-1" in out, "task header must appear"
    assert "modules/quality/lint.py" in out, "create path must appear"
    assert "modules/task_gen/service.py" in out, "modify path must appear"
    assert "Do NOT re-declare" in out, "instruction line must appear"
