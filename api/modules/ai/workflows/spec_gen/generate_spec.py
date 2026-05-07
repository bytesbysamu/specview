"""Registers the spec_gen/generate-spec workflow.

Convention required by WorkflowRepositoryFs:
    Every workflow file must expose register_workflows(repo) at module level.
    The FS adapter calls this with a _PrefixedRepo that namespaces all saves
    under 'spec_gen/<workflow.ref.name>'.
"""
from __future__ import annotations

from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.workflow import Workflow


# ── Shared content-routing block ─────────────────────────────────────────────

_CONTENT_ROUTING = """\
## CONTENT ROUTING RULES
- Business value and market analysis → ONLY in epic.md
- Design decisions and tech stack → ONLY in architecture.md
- Problem identification → ONLY in analysis.md
- Cross-references MUST be bidirectional\
"""

# ── Step 1: Analysis ─────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = "You are a markdown spec writer."

ANALYSIS_USER = """\
You are a filter between a messy brain dump and a structured epic.
Keep it SHORT — 30-40 lines max. No severity tables. No analogies.

## BUILDER CONTEXT
{builder}

{_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# Analysis: {project_name}

## The Problem
[2-3 sentences. What exists today, why it's broken, what changes.]

## Hard Constraints
[Decisions already made. Deadlines. Budget limits.]

## Open Questions
[Things the brain dump left ambiguous.]

## Dependencies & Sequencing
[What blocks what.]

## Explicitly Out of Scope
[Things mentioned that should NOT be in the epic.]

---

INPUT:
{{braindump}}""".format(
    _CONTENT_ROUTING=_CONTENT_ROUTING,
    builder="{builder}",
    project_name="{project_name}",
)

# ── Step 2: Epic ─────────────────────────────────────────────────────────────

EPIC_SYSTEM = "You are a markdown spec writer."

EPIC_USER = """\
You are generating an Epic document. Define scope, tasks, and success criteria.
NO implementation details. NO status. 3-5 tasks for MVP.

## BUILDER CONTEXT
{builder}

## PRINCIPLES
{principles}

## CONTEXT FROM ANALYSIS
{analysis}

{_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# Epic: {project_name}

## Business Value
[Why build this? Market opportunity.]

## Scope

### What This Epic Covers
- [Feature]

### What This Epic Does NOT Cover
- [Feature] - [Reason]

## Tasks

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | **[Name]** | None | Xd | High |

## Success Criteria
- [Measurable criterion]

---

INPUT:
{{braindump}}""".format(
    _CONTENT_ROUTING=_CONTENT_ROUTING,
    builder="{builder}",
    principles="{principles}",
    analysis="{analysis}",
    project_name="{project_name}",
)

# ── Step 3: Architecture ──────────────────────────────────────────────────────

ARCHITECTURE_SYSTEM = "You are a markdown spec writer."

ARCHITECTURE_USER = """\
Write a Solution Architecture document. Design decisions and tech stack ONLY.
No implementation steps. No status.

## BUILDER CONTEXT
{builder}

## PRINCIPLES
{principles}

## CONTEXT FROM EPIC
{epic}

## CODEBASE CONTEXT
{codebase}

## REFERENCES
{references}

{_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# Solution Architecture: {project_name}

## Overview
[2-3 sentences.]

## Component Design
[Key components and their responsibilities.]

## Technology Stack
| Layer | Choice | Rationale |

## Design Decisions
| Decision | Rationale | Trade-offs |

---

INPUT:
{{braindump}}""".format(
    _CONTENT_ROUTING=_CONTENT_ROUTING,
    builder="{builder}",
    principles="{principles}",
    epic="{epic}",
    codebase="{codebase}",
    references="{references}",
    project_name="{project_name}",
)


def _build_workflow() -> Workflow:
    return (
        Workflow.builder("generate-spec")
        .inputs(
            "braindump",
            "project_name",
            "builder",
            "principles",
            "codebase",
            "references",
        )
        .outputs("analysis", "epic", "architecture")
        .step(
            AICall(
                name="analysis",
                system=ANALYSIS_SYSTEM,
                prompt_template=ANALYSIS_USER,
                input_keys=("braindump", "project_name", "builder"),
                model="claude-haiku-4-5",  # cheap, short prompt
            )
        )
        .step(
            # NB: input_keys lists only workflow-level inputs (validated against
            # context.inputs by AbstractStep._validate_inputs). Prior-step
            # outputs ("analysis") are not declared here — they are resolved by
            # AICall._invoke via the merged {outputs, inputs} dict at render
            # time. See AICall docstring + test_epic_step_takes_analysis_output.
            AICall(
                name="epic",
                system=EPIC_SYSTEM,
                prompt_template=EPIC_USER,
                input_keys=(
                    "braindump",
                    "project_name",
                    "builder",
                    "principles",
                ),
                model="claude-sonnet-4-5",  # default; explicit for auditability
            )
        )
        .step(
            # See note above: "epic" comes from context.outputs, not inputs.
            AICall(
                name="architecture",
                system=ARCHITECTURE_SYSTEM,
                prompt_template=ARCHITECTURE_USER,
                input_keys=(
                    "braindump",
                    "project_name",
                    "builder",
                    "principles",
                    "codebase",
                    "references",
                ),
                model="claude-opus-4-7",  # quality matters most here
            )
        )
        .build()
    )


def register_workflows(repo) -> None:
    """Called by WorkflowRepositoryFs during app startup.

    The repo argument is a _PrefixedRepo that prepends 'spec_gen/' to all
    names; saving as 'generate-spec' becomes accessible as
    'spec_gen/generate-spec'.
    """
    repo.save(_build_workflow())
