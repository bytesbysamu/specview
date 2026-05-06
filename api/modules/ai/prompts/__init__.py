"""Pure prompt-construction functions for the AI text module.

Each function returns (system_prompt, user_prompt). No I/O, no imports from
modules.data.context, no adapter calls. Unit tests call these directly.
"""
from __future__ import annotations

import re

from modules.ai.prompts.builder import PromptBuilder

# ── rewrite ──────────────────────────────────────────────────────────────────

_REWRITE_SYSTEM = (
    "You are a precise text editor. Apply the given instruction to rewrite "
    "the provided text. Return only the rewritten text — no preamble, no commentary."
)


def rewrite_prompt(text: str, instructions: str) -> tuple[str, str]:
    return _REWRITE_SYSTEM, f"Instruction: {instructions}\n\nText:\n{text}"


# ── generate ─────────────────────────────────────────────────────────────────

_GENERATE_BASE = "You are a markdown spec writer producing documentation."


def generate_prompt(prompt_text: str, builder: str, principles: str, tone: str) -> tuple[str, str]:
    system = (
        PromptBuilder(_GENERATE_BASE)
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .raw(f"\n\nUse a {tone} tone." if tone else "")
        .build()
    )
    return system, prompt_text


# ── iterate ───────────────────────────────────────────────────────────────────

_ITERATE_BASE = (
    "You are a spec editor. Update the current document to reflect the intended "
    "changes while preserving canonical structure and section headings."
)


def iterate_prompt(base_spec: str, current_content: str, builder: str, principles: str) -> tuple[str, str]:
    system = (
        PromptBuilder(_ITERATE_BASE)
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .build()
    )
    prompt = f"## Base specification\n{base_spec}\n\n## Current document\n{current_content}"
    return system, prompt


# ── generate-spec ─────────────────────────────────────────────────────────────

_GENERATE_SPEC_BASE = """\
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


def generate_spec_prompt(input_text: str, builder: str, principles: str) -> tuple[str, str]:
    system = (
        PromptBuilder(_GENERATE_SPEC_BASE)
        .section("Builder Profile", builder)
        .section("Principles", principles)
        .build()
    )
    return system, input_text


# ── review ────────────────────────────────────────────────────────────────────

_REVIEW_SYSTEM = (
    "You are a spec reviewer. Score documents on six dimensions: "
    "clarity, completeness, actionability, consistency, specificity, feasibility. "
    'Return ONLY valid JSON — no commentary, no markdown fences: '
    '{"scores":{"clarity":<1-5>,"completeness":<1-5>,"actionability":<1-5>,'
    '"consistency":<1-5>,"specificity":<1-5>,"feasibility":<1-5>},"issues":["..."]}'
)


def review_prompt(documents: dict) -> tuple[str, str]:
    user = PromptBuilder().raw(
        "\n\n".join(f"## {k}\n{v}" for k, v in documents.items())
    ).build()
    return _REVIEW_SYSTEM, user


# ── lint-braindump ────────────────────────────────────────────────────────────

_LINT_SYSTEM = (
    "You are a spec readiness checker. Analyse the brain dump for gaps and contradictions. "
    'Return ONLY valid JSON — no commentary, no markdown fences: '
    '{"ready":<true|false>,"flags":[{"severity":"error"|"warning"|"info","message":"..."}]}'
)


def lint_braindump_prompt(braindump: str) -> tuple[str, str]:
    return _LINT_SYSTEM, PromptBuilder().raw(braindump).build()


# ── scan ──────────────────────────────────────────────────────────────────────

_SCAN_SYSTEM = (
    "You are a codebase analyst. Summarise the provided filesystem tree as structured "
    "markdown: directory layout, key files, entry points, module boundaries. "
    "Do NOT include write instructions, code modifications, or tool invocations."
)


def scan_prompt(tree_text: str) -> tuple[str, str]:
    return _SCAN_SYSTEM, f"## Filesystem tree\n\n{tree_text}"


# ── bootstrap-project (chained: analysis → epic → architecture) ───────────────

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


# ── Bootstrap workflow prompt constants ───────────────────────────────────────
# Consumed by spec_gen/bootstrap-project AICall steps via str.format_map.
# Each USER constant is rendered with the merged {**outputs, **inputs} dict at
# step execution time. Prior-step outputs (analysis, epic) are ChainResult
# instances; .text attribute access works through format_map's getattr resolution.
#
# The original bootstrap_*_prompt functions below are NOT changed — they remain
# the supported call site for the synchronous route handler. These constants are
# unrolled equivalents that drop the "skip block when value is empty" optimisation
# (empty values produce empty section bodies, which the model handles cleanly).

BOOTSTRAP_ANALYSIS_SYSTEM = (
    "You are a filter that compresses messy brain dumps into tight problem statements. "
    "Your job is to surface contradictions and kill scope before the epic can inflate it. "
    "Brevity is a virtue — 30-40 lines max. No analogies, no severity tables."
)

BOOTSTRAP_ANALYSIS_USER = """\
You are a filter between a messy brain dump and a structured epic. Your job: catch contradictions, surface undecided decisions, kill scope before the epic can inflate it.

Keep it SHORT — 30-40 lines max. No severity tables. No symptom lists. No analogies. No "evidence" columns.

## BUILDER CONTEXT (use to inform decisions)
{builder}

""" + _BOOTSTRAP_CONTENT_ROUTING + """

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble, no summary, no confirmation.

---

# 🔍 {project_name} — Analysis

## The Problem
[2-3 sentences. What exists today, why it's broken, what changes.]

## Hard Constraints
Decisions already made. Deadlines. Budget limits. Tech that MUST be used or avoided. Cross-check against the builder context — if the brain dump contradicts a principle, flag it here.
- [Constraint]

## Open Questions
Things the brain dump left ambiguous that the epic and architecture need answered.
- [Question — with the 2-3 possible answers]

## Dependencies & Sequencing
What blocks what. Not a task list — structural dependencies.
- [Dependency]

## Explicitly Out of Scope
Things the brain dump mentioned or implied that should NOT be in the epic. Apply the Not-yet-built principle: speculative infrastructure deferred until a second consumer exists.
- [Thing — reason it's out — trigger for re-scoping]

---

INPUT:
{braindump}"""

BOOTSTRAP_EPIC_SYSTEM = (
    "You are a capability-scope writer. You ship 3-5 tasks for MVP, never more. "
    "Premature abstraction is your enemy: every component listed must have a named "
    "consumer or it moves to the not-built list."
)

BOOTSTRAP_EPIC_USER = """\
You are generating an **Epic** document for a capability folder.

## BUILDER CONTEXT
{builder}

## ARCHITECTURE PRINCIPLES (non-negotiable — follow these patterns)
{principles}

## CONTEXT FROM ANALYSIS (generated in prior step)
{analysis.text}

Use the issues identified above to inform task scoping and business value.

""" + _BOOTSTRAP_CONTENT_ROUTING + """

## Your ONE Job
Define scope, tasks, and success criteria. NO implementation details. NO status. Apply the Engineering Discipline rules: not-yet-built is the right state for infrastructure nobody's asked for; each task ships its concrete case, not abstractions.

## Cross-References (REQUIRED)
- Reference [Analysis](./analysis.md) – "Addresses issues in Analysis"
- Reference [Architecture](./architecture.md) – "See Architecture for design"
- Note: "Status tracked in [Timeline](./timeline.md)"

## Task Table Rules
- Use **Priority** column (High/Low), NOT Status
- Task numbers = execution order
- 3-5 tasks for MVP
- Row format: | # | **Task Name** | Dependencies | Parallel | Effort | Priority |

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🎯 Epic: {project_name}

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

[2-3 paragraphs: Why build this? Market opportunity. Who pays.]

**Value Proposition**: [One sentence]

---

## Scope

### What This Epic Covers

- [Feature 1] – [context]

### What This Epic Does NOT Cover

- ❌ [Feature] — [Reason]

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **[Task Name]** | None | — | X days | High |

### Task 1: [Name]

[2-3 sentences.]

**Port budget**: [rough size + deferrals]

---

## Success Criteria

- ✅ [Measurable criterion]

---

## Non-Goals

- ❌ [Non-goal] — [Why]

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview

---

INPUT:
{braindump}

Focus on MVP. 3-5 tasks. Be specific about scope."""

BOOTSTRAP_ARCHITECTURE_SYSTEM = (
    "You are a system designer. You explain decisions and trade-offs. "
    "Code blocks are forbidden — they belong in implementation guides. "
    "Every component you list must name at least one named consumer."
)

BOOTSTRAP_ARCHITECTURE_USER = """\
You are generating a **Solution Architecture** document for a capability folder.

## BUILDER CONTEXT
{builder}

## ARCHITECTURE PRINCIPLES (non-negotiable — follow these patterns)
{principles}

## CONTEXT FROM EPIC (generated in prior step)
{epic.text}

Design the solution architecture to fulfill the tasks and scope defined above.

## CODEBASE CONTEXT (current project state — use real paths, reuse existing modules)
{codebase}

## REFERENCE CODE (port from, not code in the target repo)
{references}

""" + _BOOTSTRAP_CONTENT_ROUTING + """

## Your ONE Job
System design, decisions, trade-offs. NO code blocks. NO status.

**Apply Engineering Discipline:**
- Don't design abstractions of one concrete case. If a component has exactly one consumer, describe the concrete case.
- For each component listed, name at least one named consumer. If no consumer exists, move it to "What This System Does NOT Include".
- If REFERENCE CODE is provided, the architecture should describe shapes that PORT those references.
- Shared AI infrastructure MUST follow ELA Pattern #1 (Adapter): one adapter boundary, provider implementations behind it.

## Cross-References (REQUIRED)
- Reference [Analysis](./analysis.md) – "Addresses issues in Analysis"
- Reference [Epic](./epic.md) – "See Epic for scope"

## Rules
- File/class references OK (e.g., `UserService.java`)
- Code blocks NOT OK (those go in Implementation docs)
- Explain WHY, not just WHAT

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🏗️ Solution Architecture: {project_name}

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

[2-3 paragraphs: Mental model. Key insight. How components fit.]

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| [Principle] | [How we apply it] |

---

## System Boundaries

### What This System Includes
- [Component/capability]

### What This System Does NOT Include
| Excluded | Reason |
|----------|--------|
| [Thing] | [Why] |

---

## Component Design

### [Component 1]
**Purpose**: [What it solves]
**Key Parts**:
- `ClassName` — [What it does]
**Patterns**: [Design patterns used]

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | [Tech] | [Why] |
| Backend | [Tech] | [Why] |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| [Choice] | [Why] | [What we gave up] |

---

## Execution Flow

```
[Phase 1]
  Task 1 ──→ Task 2
```

---

## Open Questions

Unresolved decisions that implementation guides MUST address before coding begins.
List the question, the options, and what triggers a re-decision later.
Empty list is acceptable only if every decision is genuinely settled — say so explicitly.

- [Question — options A/B/C — re-decision trigger]

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview

---

**Length budget**: target ≤ 250 lines including all tables. If you need more, the
architecture is doing too much — split into a follow-on capability.

INPUT:
{braindump}

Focus on WHY. Explain trade-offs. No code blocks."""


def bootstrap_analysis_prompt(
    braindump: str,
    project_name: str,
    builder: str,
) -> tuple[str, str]:
    """Step 1 of 3 in the bootstrap chain."""
    builder_block = f"\n## BUILDER CONTEXT (use to inform decisions)\n{builder}\n" if builder else ""
    user = f"""\
You are a filter between a messy brain dump and a structured epic. Your job: catch contradictions, surface undecided decisions, kill scope before the epic can inflate it.

Keep it SHORT — 30-40 lines max. No severity tables. No symptom lists. No analogies. No "evidence" columns.
{builder_block}
{_BOOTSTRAP_CONTENT_ROUTING}

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble, no summary, no confirmation.

---

# 🔍 {project_name} — Analysis

## The Problem
[2-3 sentences. What exists today, why it's broken, what changes.]

## Hard Constraints
Decisions already made. Deadlines. Budget limits. Tech that MUST be used or avoided. Cross-check against the builder context — if the brain dump contradicts a principle, flag it here.
- [Constraint]

## Open Questions
Things the brain dump left ambiguous that the epic and architecture need answered.
- [Question — with the 2-3 possible answers]

## Dependencies & Sequencing
What blocks what. Not a task list — structural dependencies.
- [Dependency]

## Explicitly Out of Scope
Things the brain dump mentioned or implied that should NOT be in the epic. Apply the Not-yet-built principle: speculative infrastructure deferred until a second consumer exists.
- [Thing — reason it's out — trigger for re-scoping]

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
    """Step 2 of 3. Receives analysis output from step 1."""
    builder_block = f"\n## BUILDER CONTEXT\n{builder}\n" if builder else ""
    principles_block = f"\n## ARCHITECTURE PRINCIPLES (non-negotiable — follow these patterns)\n{principles}\n" if principles else ""
    analysis_block = f"\n## CONTEXT FROM ANALYSIS (generated in prior step)\n{analysis}\n\nUse the issues identified above to inform task scoping and business value.\n" if analysis else ""
    user = f"""\
You are generating an **Epic** document for a capability folder.
{builder_block}{principles_block}{analysis_block}
{_BOOTSTRAP_CONTENT_ROUTING}
## Your ONE Job
Define scope, tasks, and success criteria. NO implementation details. NO status. Apply the Engineering Discipline rules: not-yet-built is the right state for infrastructure nobody's asked for; each task ships its concrete case, not abstractions.

## Cross-References (REQUIRED)
- Reference [Analysis](./analysis.md) – "Addresses issues in Analysis"
- Reference [Architecture](./architecture.md) – "See Architecture for design"
- Note: "Status tracked in [Timeline](./timeline.md)"

## Task Table Rules
- Use **Priority** column (High/Low), NOT Status
- Task numbers = execution order
- 3-5 tasks for MVP
- Row format: | # | **Task Name** | Dependencies | Parallel | Effort | Priority |

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🎯 Epic: {project_name}

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

[2-3 paragraphs: Why build this? Market opportunity. Who pays.]

**Value Proposition**: [One sentence]

---

## Scope

### What This Epic Covers

- [Feature 1] – [context]

### What This Epic Does NOT Cover

- ❌ [Feature] — [Reason]

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **[Task Name]** | None | — | X days | High |

### Task 1: [Name]

[2-3 sentences.]

**Port budget**: [rough size + deferrals]

---

## Success Criteria

- ✅ [Measurable criterion]

---

## Non-Goals

- ❌ [Non-goal] — [Why]

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview

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
    """Step 3 of 3. Receives epic output from step 2."""
    builder_block = f"\n## BUILDER CONTEXT\n{builder}\n" if builder else ""
    principles_block = f"\n## ARCHITECTURE PRINCIPLES (non-negotiable — follow these patterns)\n{principles}\n" if principles else ""
    epic_block = f"\n## CONTEXT FROM EPIC (generated in prior step)\n{epic}\n\nDesign the solution architecture to fulfill the tasks and scope defined above.\n" if epic else ""
    codebase_block = f"\n## CODEBASE CONTEXT (current project state — use real paths, reuse existing modules)\n{codebase}\n" if codebase else ""
    references_block = f"\n## REFERENCE CODE (port from, not code in the target repo)\n{references}\n" if references else ""
    user = f"""\
You are generating a **Solution Architecture** document for a capability folder.
{builder_block}{principles_block}{epic_block}{codebase_block}{references_block}
{_BOOTSTRAP_CONTENT_ROUTING}
## Your ONE Job
System design, decisions, trade-offs. NO code blocks. NO status.

**Apply Engineering Discipline:**
- Don't design abstractions of one concrete case. If a component has exactly one consumer, describe the concrete case.
- For each component listed, name at least one named consumer. If no consumer exists, move it to "What This System Does NOT Include".
- If REFERENCE CODE is provided, the architecture should describe shapes that PORT those references.
- Shared AI infrastructure MUST follow ELA Pattern #1 (Adapter): one adapter boundary, provider implementations behind it.

## Cross-References (REQUIRED)
- Reference [Analysis](./analysis.md) – "Addresses issues in Analysis"
- Reference [Epic](./epic.md) – "See Epic for scope"

## Rules
- File/class references OK (e.g., `UserService.java`)
- Code blocks NOT OK (those go in Implementation docs)
- Explain WHY, not just WHAT

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# 🏗️ Solution Architecture: {project_name}

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

[2-3 paragraphs: Mental model. Key insight. How components fit.]

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| [Principle] | [How we apply it] |

---

## System Boundaries

### What This System Includes
- [Component/capability]

### What This System Does NOT Include
| Excluded | Reason |
|----------|--------|
| [Thing] | [Why] |

---

## Component Design

### [Component 1]
**Purpose**: [What it solves]
**Key Parts**:
- `ClassName` — [What it does]
**Patterns**: [Design patterns used]

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | [Tech] | [Why] |
| Backend | [Tech] | [Why] |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| [Choice] | [Why] | [What we gave up] |

---

## Execution Flow

```
[Phase 1]
  Task 1 ──→ Task 2
```

---

## Open Questions

Unresolved decisions that implementation guides MUST address before coding begins.
List the question, the options, and what triggers a re-decision later.
Empty list is acceptable only if every decision is genuinely settled — say so explicitly.

- [Question — options A/B/C — re-decision trigger]

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview

---

**Length budget**: target ≤ 250 lines including all tables. If you need more, the
architecture is doing too much — split into a follow-on capability.

INPUT:
{braindump}

Focus on WHY. Explain trade-offs. No code blocks."""
    return "You are a markdown spec writer.", user


def bootstrap_combined_prompt(
    braindump: str,
    project_name: str,
    builder: str,
    principles: str,
    codebase: str,
    references: str,
) -> tuple[str, str]:
    """Single-call prompt that generates analysis + epic + architecture in one response.

    Output uses ===FILE: filename=== markers so the caller can split them.
    Generating all three docs in one call avoids consecutive per-minute token
    limit hits that occur when they are issued as three separate requests.
    """
    builder_block = f"\n## BUILDER CONTEXT\n{builder}\n" if builder else ""
    principles_block = f"\n## ARCHITECTURE PRINCIPLES\n{principles}\n" if principles else ""
    codebase_block = f"\n## CODEBASE CONTEXT\n{codebase}\n" if codebase else ""
    references_block = f"\n## REFERENCE CODE\n{references}\n" if references else ""

    user = f"""\
Generate three spec documents for **{project_name}** from the brain dump below.
Output ONLY the three files, each preceded by its marker. No preamble, no summary.
{builder_block}{principles_block}{codebase_block}{references_block}
{_BOOTSTRAP_CONTENT_ROUTING}

## Output format (exact)

===FILE: analysis.md===
[full analysis document]

===FILE: epic.md===
[full epic document — informed by the analysis you just wrote]

===FILE: architecture.md===
[full architecture document — informed by the epic you just wrote]

---

## Document specs

### analysis.md
30-40 lines. Sections: The Problem · Hard Constraints · Open Questions · Dependencies & Sequencing · Explicitly Out of Scope.
Start with: # 🔍 {project_name} — Analysis

### epic.md
Sections: Business Value · Scope (covers / does not cover) · Tasks (table + per-task detail) · Success Criteria · Non-Goals · Related Documents.
Task table columns: | # | Task | Dependencies | Parallel | Effort | Priority |
3-5 tasks. Priority = High/Low only.
Start with: # 🎯 Epic: {project_name}

### architecture.md
≤250 lines. Sections: Architecture Overview · Design Principles · System Boundaries · Component Design · Technology Stack · Design Decisions · Execution Flow · Open Questions · Related Documents.
No code blocks. Explain WHY, not just WHAT.
Start with: # 🏗️ Solution Architecture: {project_name}

---

INPUT:
{braindump}"""
    return "You are a markdown spec writer. Output only the requested file markers and their content.", user


def bootstrap_parse_combined(output: str) -> dict[str, str]:
    """Parse ===FILE: filename=== markers from a combined bootstrap response.

    Returns a dict mapping filename → content (stripped).
    Unknown or missing files return empty string.
    """
    files: dict[str, str] = {}
    current_file: str | None = None
    current_lines: list[str] = []

    for line in output.splitlines():
        if line.startswith("===FILE:") and line.endswith("==="):
            if current_file is not None:
                files[current_file] = "\n".join(current_lines).strip()
            current_file = line[len("===FILE:"):-len("===")].strip()
            current_lines = []
        elif current_file is not None:
            current_lines.append(line)

    if current_file is not None:
        files[current_file] = "\n".join(current_lines).strip()

    return files


def bootstrap_extract_tasks(epic_content: str) -> list[dict]:
    """Port of ImplementationGuideService.extractTasksFromEpic.

    Finds task table rows matching: | N | **Task Name** | ... | Effort | High/Medium/Low |
    """
    tasks = []
    for line in epic_content.splitlines():
        m = re.match(
            r'^\|\s*([\d.]+)\s*\|\s*\*\*([^*]+)\*\*\s*\|.*\|\s*([^|]+)\s*\|\s*(?:High|Medium|Low)\s*\|',
            line,
        )
        if m:
            tasks.append({"num": m.group(1), "name": m.group(2).strip(), "effort": m.group(3).strip()})
    return tasks
