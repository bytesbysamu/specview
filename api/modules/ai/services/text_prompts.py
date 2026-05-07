"""Prompt builder functions and constants for AI text generation routes.

Moved from modules.ai.routes.text (inline helpers) and
modules.ai.workflows.spec_gen.generate_spec (ANALYSIS/EPIC/ARCHITECTURE constants).
"""


# ---------------------------------------------------------------------------
# Fluent assembler
# ---------------------------------------------------------------------------

class _PromptBuilder:
    """Minimal fluent assembler for system prompts."""

    def __init__(self, base: str = "") -> None:
        self._parts: list[str] = [base] if base else []

    def section(self, heading: str, content: str) -> "_PromptBuilder":
        if content and content.strip():
            self._parts.append(f"\n\n## {heading}\n{content}")
        return self

    def raw(self, text: str) -> "_PromptBuilder":
        if text:
            self._parts.append(text)
        return self

    def build(self) -> str:
        return "".join(self._parts)


# ---------------------------------------------------------------------------
# Route prompt functions (formerly inlined in modules.ai.routes.text)
# ---------------------------------------------------------------------------

def rewrite_prompt(text: str, instructions: str) -> tuple[str, str]:
    system = (
        "You are a precise text editor. Apply the given instruction to rewrite "
        "the provided text. Return only the rewritten text — no preamble, no commentary."
    )
    return system, f"Instruction: {instructions}\n\nText:\n{text}"


def iterate_prompt(base_spec: str, current_content: str, builder: str, principles: str) -> tuple[str, str]:
    system = (
        _PromptBuilder(
            "You are a spec editor. Update the current document to reflect the intended "
            "changes while preserving canonical structure and section headings."
        )
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .build()
    )
    prompt = f"## Base specification\n{base_spec}\n\n## Current document\n{current_content}"
    return system, prompt


def lint_braindump_prompt(braindump: str) -> tuple[str, str]:
    system = (
        "You are a spec readiness checker. Analyse the brain dump for gaps and contradictions. "
        'Return ONLY valid JSON — no commentary, no markdown fences: '
        '{"ready":<true|false>,"flags":[{"severity":"error"|"warning"|"info","message":"..."}]}'
    )
    return system, _PromptBuilder().raw(braindump).build()


def review_prompt(documents: dict) -> tuple[str, str]:
    system = (
        "You are a spec reviewer. Score documents on six dimensions: "
        "clarity, completeness, actionability, consistency, specificity, feasibility. "
        'Return ONLY valid JSON — no commentary, no markdown fences: '
        '{"scores":{"clarity":<1-5>,"completeness":<1-5>,"actionability":<1-5>,'
        '"consistency":<1-5>,"specificity":<1-5>,"feasibility":<1-5>},"issues":["..."]}'
    )
    user = _PromptBuilder().raw(
        "\n\n".join(f"## {k}\n{v}" for k, v in documents.items())
    ).build()
    return system, user


def generate_prompt(prompt_text: str, builder: str, principles: str, tone: str) -> tuple[str, str]:
    system = (
        _PromptBuilder("You are a markdown spec writer producing documentation.")
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .raw(f"\n\nUse a {tone} tone." if tone else "")
        .build()
    )
    return system, prompt_text


def generate_spec_prompt(input_text: str, builder: str, principles: str) -> tuple[str, str]:
    base = """\
You are a specification document generator. Given a product brain dump, \
produce four specification files.

Output EXACTLY in this format — no text before the first marker, no text after the last:

===FILE: analysis.md===
[analysis content]

===FILE: epic.md===
[epic content]

===FILE: architecture.md===
[architecture content]

===FILE: spec-doc-spec.md===
[spec-doc-spec content]\
"""
    system = (
        _PromptBuilder(base)
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .build()
    )
    return system, input_text


_BOOTSTRAP_CONTENT_ROUTING = """\
## CONTENT ROUTING RULES (violations are failures)
- Status words (Done, In Progress, Completed) → ONLY in timeline.md
- Code blocks with implementation → ONLY in implementation guides
- Business value and market analysis → ONLY in epic.md
- Design decisions and tech stack → ONLY in architecture.md
- Step-by-step instructions → ONLY in implementation guides
- Problem identification → ONLY in analysis.md
- Cross-references MUST be bidirectional (if A→B then B→A)
- Always use "Solution Architecture" (not just "Architecture") in cross-references\
"""


def bootstrap_analysis_prompt(
    braindump: str,
    project_name: str,
    builder: str,
) -> tuple[str, str]:
    builder_block = f"\n## BUILDER CONTEXT (use to inform decisions)\n{builder}\n" if builder else ""
    user = f"""\
You are a filter between a messy brain dump and a structured epic. Your job: catch contradictions, surface undecided decisions, kill scope before the epic can inflate it.

Keep it SHORT — 30-40 lines max. No severity tables. No symptom lists. No analogies. No "evidence" columns.
{builder_block}
{_BOOTSTRAP_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble, no summary, no confirmation.

---

# \U0001f50d {project_name} \u2014 Analysis

## The Problem
[2-3 sentences. What exists today, why it's broken, what changes.]

## Hard Constraints
Decisions already made. Deadlines. Budget limits. Tech that MUST be used or avoided.
- [Constraint]

## Open Questions
Things the brain dump left ambiguous that the epic and architecture need answered.
- [Question \u2014 with the 2-3 possible answers]

## Dependencies & Sequencing
What blocks what. Not a task list \u2014 structural dependencies.
- [Dependency]

## Explicitly Out of Scope
Things the brain dump mentioned or implied that should NOT be in the epic.
- [Thing \u2014 reason it's out \u2014 trigger for re-scoping]

---

INPUT:
{braindump}"""
    return "You are a markdown spec writer.", user


def bootstrap_epic_prompt(
    braindump: str,
    project_name: str,
    analysis: str,
    builder: str,
    principles: str,
) -> tuple[str, str]:
    builder_block = f"\n## BUILDER CONTEXT\n{builder}\n" if builder else ""
    principles_block = f"\n## ARCHITECTURE PRINCIPLES (non-negotiable \u2014 follow these patterns)\n{principles}\n" if principles else ""
    analysis_block = f"\n## CONTEXT FROM ANALYSIS (generated in prior step)\n{analysis}\n\nUse the issues identified above to inform task scoping and business value.\n" if analysis else ""
    user = f"""\
You are generating an **Epic** document for a capability folder.
{builder_block}{principles_block}{analysis_block}
{_BOOTSTRAP_CONTENT_ROUTING}
## Your ONE Job
Define scope, tasks, and success criteria. NO implementation details. NO status.

## Task Table Rules
- Use **Priority** column (High/Low), NOT Status
- Task numbers = execution order
- 3-5 tasks for MVP
- Row format: | # | **Task Name** | Dependencies | Parallel | Effort | Priority |

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# \U0001f3af Epic: {project_name}

## Business Value
[2-3 paragraphs: Why build this? Market opportunity. Who pays.]

## Scope

### What This Epic Covers
- [Feature 1] \u2013 [context]

### What This Epic Does NOT Cover
- \u274c [Feature] \u2014 [Reason]

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **[Task Name]** | None | \u2014 | X days | High |

## Success Criteria

- \u2705 [Measurable criterion]

## Related Documents

- [Analysis](./analysis.md) \u2013 Problems driving this epic
- [Solution Architecture](./architecture.md) \u2013 System design
- [Timeline](./timeline.md) \u2013 Status tracking

---

INPUT:
{braindump}

Focus on MVP. 3-5 tasks. Be specific about scope."""
    return "You are a markdown spec writer.", user


def bootstrap_architecture_prompt(
    braindump: str,
    project_name: str,
    epic: str,
    builder: str,
    principles: str,
    codebase: str,
    references: str,
) -> tuple[str, str]:
    builder_block = f"\n## BUILDER CONTEXT\n{builder}\n" if builder else ""
    principles_block = f"\n## ARCHITECTURE PRINCIPLES (non-negotiable \u2014 follow these patterns)\n{principles}\n" if principles else ""
    epic_block = f"\n## CONTEXT FROM EPIC (generated in prior step)\n{epic}\n\nDesign the solution architecture to fulfill the tasks and scope defined above.\n" if epic else ""
    codebase_block = f"\n## CODEBASE CONTEXT (current project state \u2014 use real paths, reuse existing modules)\n{codebase}\n" if codebase else ""
    references_block = f"\n## REFERENCE CODE (port from, not code in the target repo)\n{references}\n" if references else ""
    user = f"""\
You are generating a **Solution Architecture** document for a capability folder.
{builder_block}{principles_block}{epic_block}{codebase_block}{references_block}
{_BOOTSTRAP_CONTENT_ROUTING}
## Your ONE Job
System design, decisions, trade-offs. NO code blocks. NO status.

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# \U0001f3d7\ufe0f Solution Architecture: {project_name}

## Architecture Overview
[2-3 paragraphs: Mental model. Key insight. How components fit.]

## Design Principles
| Principle | Application |
|-----------|-------------|
| [Principle] | [How we apply it] |

## Component Design
### [Component 1]
**Purpose**: [What it solves]

## Technology Stack
| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | [Tech] | [Why] |
| Backend | [Tech] | [Why] |

## Design Decisions
| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| [Choice] | [Why] | [What we gave up] |

## Related Documents
- [Analysis](./analysis.md) \u2013 Problems driving design
- [Epic](./epic.md) \u2013 Scope and tasks
- [Timeline](./timeline.md) \u2013 Status tracking

---

INPUT:
{braindump}

Focus on WHY. Explain trade-offs. No code blocks."""
    return "You are a markdown spec writer.", user


# ---------------------------------------------------------------------------
# Workflow-layer constants (formerly inlined in generate_spec.py)
# ---------------------------------------------------------------------------

_CONTENT_ROUTING = """\
## CONTENT ROUTING RULES
- Business value and market analysis → ONLY in epic.md
- Design decisions and tech stack → ONLY in architecture.md
- Problem identification → ONLY in analysis.md
- Cross-references MUST be bidirectional\
"""

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
