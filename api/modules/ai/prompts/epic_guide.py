# modules/ai/prompts/epic_guide.py
"""Prompt for whole-epic implementation guide generation.

build_epic_guide_prompt() is the sole public export.
Returns (system, user) that produces a single implementation-guide.md
covering every task with the same 10-section quality as individual task guides.
"""
from __future__ import annotations

from modules.ai.prompts.builder import PromptBuilder
from modules.ai.prompts.impl_guide import EXECUTOR_ATTRIBUTION, _USER_HEADER as _TASK_RULES

_SYSTEM = "You are a senior engineer writing executor-ready implementation guides."

_USER_HEADER = """\
## Your ONE Job
Produce a single implementation-guide.md covering every task in the epic. \
Each task gets its own section with exactly the same 10 sub-sections as a \
standalone task guide. The file opens with a shared overview and pre-flight \
that apply to all tasks.

## Required Structure
```
# Implementation Guide: {Epic Name}

## Overview
What the epic delivers. How tasks sequence and depend on each other.

## Shared Pre-flight
Setup steps that apply across all tasks (env vars, migrations, dependencies).

## Shared Files
Files touched by multiple tasks — declare once here, not repeated per task.

---

## Task 1: {Name}  [Effort: X]

### 1. Context
### 2. Pre-flight
### 3. Files
#### To Create (new)
#### To Modify
### 4. Implementation Steps
### 5. Tests
### 6. Commit Plan
### 7. Verification
### 8. Rollback
### 9. Deviations Allowed
### 10. Out of Scope

---

## Task 2: {Name}  [Effort: X]
...
```

## Hard Rules
- NO absolute personal paths (`/Users/...`, `/home/...`, `C:\\Users\\...`). \
Use `{WORKSPACE}` or workspace-relative paths.
- NO empty test bodies. Forbidden: `/* ... */`, `it(name, () => {})`, \
`def test_x(): pass`. Full assertions matching the repo's test framework.
- NO unfilled placeholders: `<placeholder>`, `<TBD>`, `TODO(executor)`, \
`path/to/whatever` — replace every bracket/brace token with a concrete value.
- Your entire response MUST begin with `#`. No preamble.
- The `Co-Authored-By` commit trailer in EVERY task's Commit Plan MUST be \
copied verbatim from the EXECUTOR ATTRIBUTION block.
- Use relative test-count deltas (`N → N+K passing`), never absolute baselines.
- Cover EVERY task in the epic table. Do not skip any.

## Output Gate
Your output is checked before disk write. \
Self-check every task section against the Hard Rules above before emitting.\
"""


def build_epic_guide_prompt(
    *,
    epic: str,
    arch: str,
    analysis: str = "",
    builder: str = "",
    principles: str = "",
    codebase: str = "",
    references: str = "",
    versions: str = "",
) -> tuple[str, str]:
    """Return (system, user) for whole-epic implementation guide generation.

    Args:
        epic:       Full epic.md content — task list is parsed from here.
        arch:       Full architecture.md content.
        analysis:   Full analysis.md content (optional).
        builder:    Builder profile context (optional).
        principles: Architecture principles (optional).
        codebase:   Codebase context (optional).
        references: Reference code context (optional).
        versions:   Deployment fact sheet (optional).
    """
    user = (
        PromptBuilder(_USER_HEADER)
        .section("BUILDER CONTEXT", builder)
        .section("ARCHITECTURE PRINCIPLES", principles)
        .section("CODEBASE CONTEXT", codebase)
        .section("REFERENCE CODE", references)
        .section("DEPLOYMENT VERSIONS", versions)
        .section("EXECUTOR ATTRIBUTION", EXECUTOR_ATTRIBUTION["co_author_trailer"])
        .raw("\n\n---\n\n")
        .raw(f"## EPIC\n{epic}\n\n")
        .raw(f"## ANALYSIS\n{analysis}\n\n" if analysis else "")
        .raw(f"## ARCHITECTURE\n{arch}\n\n")
        .raw(
            "Generate a single implementation-guide.md covering every task above. "
            "Follow the Required Structure exactly — one 10-section block per task."
        )
        .build()
    )
    return _SYSTEM, user
