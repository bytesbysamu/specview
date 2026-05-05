"""Prompt constants for the spec_gen generate-spec workflow.

Each constant is a Python format string. AICall renders it with:
    template.format_map({**context.outputs, **context.inputs})

Convention: SYSTEM strings end in ``_SYSTEM``; user prompt strings end in ``_USER``.
"""
from __future__ import annotations

# ── Shared ──────────────────────────────────────────────────────────────────

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
{braindump}""".format(
    _CONTENT_ROUTING=_CONTENT_ROUTING,
    builder="{builder}",
    project_name="{project_name}",
    braindump="{braindump}",
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
{braindump}""".format(
    _CONTENT_ROUTING=_CONTENT_ROUTING,
    builder="{builder}",
    principles="{principles}",
    analysis="{analysis}",
    project_name="{project_name}",
    braindump="{braindump}",
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
{braindump}""".format(
    _CONTENT_ROUTING=_CONTENT_ROUTING,
    builder="{builder}",
    principles="{principles}",
    epic="{epic}",
    codebase="{codebase}",
    references="{references}",
    project_name="{project_name}",
    braindump="{braindump}",
)
