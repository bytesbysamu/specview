"""Stateless markdown template generators.

Ported verbatim from new-project.component.ts:
- generateSpecIndex()  -> generate_spec_index(project_name, today=None)
- generateTimeline()   -> generate_timeline(project_name, tasks, today=None)
- generateReadme()     -> generate_readme(project_name, today=None)

No I/O. No AI calls. Deterministic given (project_name, tasks, today).

The TS helpers CAPABILITY_SLUG() and TODAY() are reproduced as
_capability_slug() and _today() below.
"""
from __future__ import annotations

import datetime
import re
from typing import Iterable, Mapping


def _capability_slug(project_name: str) -> str:
    """Mirror of new-project.component.ts: this.projectName.toLowerCase().replace(/\\s+/g, '-')."""
    return re.sub(r"\s+", "-", project_name.lower())


def _today() -> str:
    """Mirror of new-project.component.ts: new Date().toISOString().split('T')[0]."""
    return datetime.date.today().isoformat()


def generate_spec_index(project_name: str, today: str | None = None) -> str:
    """Return spec-index.md content. Verbatim port of generateSpecIndex()."""
    slug = _capability_slug(project_name)
    today_str = today if today is not None else _today()
    return (
        f"# \U0001f4cb Spec Index: {project_name}\n"
        "\n"
        "> Single source of truth for this capability's specifications.\n"
        "> Claude Code reads this to understand available context.\n"
        "\n"
        "---\n"
        "\n"
        "## Active Specs\n"
        "\n"
        "| Document | Purpose | Location |\n"
        "|----------|---------|----------|\n"
        "| Analysis | Problems driving this capability | [analysis.md](./analysis.md) |\n"
        "| Epic | Scope, tasks, success criteria | [epic.md](./epic.md) |\n"
        "| Architecture | System design & decisions | [architecture.md](./architecture.md) |\n"
        "| Timeline | Status tracking | [timeline.md](./timeline.md) |\n"
        "\n"
        "---\n"
        "\n"
        "## Document Flow\n"
        "\n"
        "```\n"
        "Analysis ──→ Epic ──→ Architecture ──→ Implementation\n"
        "(Problems)   (Scope)   (Design)        (How-to)\n"
        "```\n"
        "\n"
        "---\n"
        "\n"
        "## Quick Reference\n"
        "\n"
        "| When you need... | Read this |\n"
        "|------------------|-----------|\n"
        "| Why we're building this | [Analysis](./analysis.md) |\n"
        "| What we're building | [Epic](./epic.md) |\n"
        "| How it's designed | [Architecture](./architecture.md) |\n"
        "| Task status | [Timeline](./timeline.md) |\n"
        "\n"
        "---\n"
        "\n"
        "## For Claude Code\n"
        "\n"
        "To work on this capability:\n"
        "\n"
        "```\n"
        f"@{slug}/epic.md\n"
        f"@{slug}/architecture.md\n"
        "\n"
        "Implement the next task from the backlog.\n"
        "Follow patterns in architecture.md.\n"
        "```\n"
        "\n"
        "---\n"
        "\n"
        f"**Last Updated**: {today_str}\n"
    )


def generate_timeline(
    project_name: str,
    tasks: Iterable[Mapping[str, str]],
    today: str | None = None,
) -> str:
    """Return timeline.md content. Verbatim port of generateTimeline(tasks).

    tasks: iterable of {"num": str, "name": str, "effort": str}.
    """
    tasks_list = list(tasks)
    today_str = today if today is not None else _today()
    backlog_rows = "\n".join(
        f"| {t['num']} | **{t['name']}** | TBD | {t['effort']} | — |"
        for t in tasks_list
    )
    backlog_block = backlog_rows if backlog_rows else "| — | — | — | — | — |"
    return (
        f"# \U0001f4c5 Timeline: {project_name}\n"
        "\n"
        f"**Last Updated**: {today_str}\n"
        "\n"
        "> Status tracking for this capability. This is the ONLY place for status.\n"
        "> Epic and Architecture docs contain Priority, not Status.\n"
        "\n"
        "---\n"
        "\n"
        "## Done\n"
        "\n"
        "| # | Task | Completed | Effort | Notes |\n"
        "|---|------|-----------|--------|-------|\n"
        "| — | — | — | — | — |\n"
        "\n"
        "---\n"
        "\n"
        "## In Progress\n"
        "\n"
        "| # | Task | Started | Effort | Notes |\n"
        "|---|------|---------|--------|-------|\n"
        "| — | — | — | — | — |\n"
        "\n"
        "---\n"
        "\n"
        "## Backlog\n"
        "\n"
        "| # | Task | Due | Effort | Notes |\n"
        "|---|------|-----|--------|-------|\n"
        f"{backlog_block}\n"
        "\n"
        "---\n"
        "\n"
        "## Epic Progress\n"
        "\n"
        "| Metric | Count |\n"
        "|--------|-------|\n"
        "| Done | 0 |\n"
        "| In Progress | 0 |\n"
        f"| Backlog | {len(tasks_list)} |\n"
        f"| **Total** | **{len(tasks_list)}** |\n"
        "\n"
        "---\n"
        "\n"
        "## Related Documents\n"
        "\n"
        "- [Epic](./epic.md) – Task definitions and scope\n"
        "- [Solution Architecture](./architecture.md) – Design decisions\n"
        "- [Spec Index](./spec-index.md) – Document overview\n"
    )


def generate_readme(project_name: str, today: str | None = None) -> str:
    """Return README.md content. Verbatim port of generateReadme()."""
    today_str = today if today is not None else _today()
    return (
        f"# \U0001f4d6 {project_name}\n"
        "\n"
        "> Overview and quick start for this capability.\n"
        "\n"
        "---\n"
        "\n"
        "## What This Is\n"
        "\n"
        f"{project_name} is a capability defined by the following documents:\n"
        "\n"
        "| Document | Purpose |\n"
        "|----------|---------|\n"
        "| [Spec Index](./spec-index.md) | Entry point for Claude Code |\n"
        "| [Analysis](./analysis.md) | Problems we're solving |\n"
        "| [Epic](./epic.md) | Scope, tasks, success criteria |\n"
        "| [Architecture](./architecture.md) | System design |\n"
        "| [Timeline](./timeline.md) | Status tracking |\n"
        "\n"
        "---\n"
        "\n"
        "## Quick Start\n"
        "\n"
        "1. Read [Analysis](./analysis.md) to understand the problems\n"
        "2. Read [Epic](./epic.md) to understand scope and tasks\n"
        "3. Read [Architecture](./architecture.md) before implementing\n"
        "4. Track progress in [Timeline](./timeline.md)\n"
        "\n"
        "---\n"
        "\n"
        "## For Claude Code\n"
        "\n"
        "```\n"
        "Read this capability's docs and implement the next task:\n"
        "\n"
        "@spec-index.md\n"
        "@epic.md\n"
        "@architecture.md\n"
        "\n"
        "Implement Task 1 from the backlog. Follow architecture patterns.\n"
        "```\n"
        "\n"
        "---\n"
        "\n"
        "## Document Guidelines\n"
        "\n"
        "- **Status** belongs ONLY in [Timeline](./timeline.md)\n"
        "- **Reference, don't duplicate** — link to other docs\n"
        "- **Each doc has ONE job** — don't mix concerns\n"
        "\n"
        "---\n"
        "\n"
        f"**Created**: {today_str}\n"
    )
