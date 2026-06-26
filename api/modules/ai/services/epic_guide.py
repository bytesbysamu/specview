"""Background thread + in-process state for generate-epic-guide.

Generates a single implementation-guide.md covering every task in the epic.
One execution slot per project — only one epic guide generation runs at a time.

Public surface:
    is_running(project_id)  — predicate
    snapshot(project_id)    — read-only summary for the GET route
    start(project_id, projects_dir) — spawn thread
    run_generation(...)     — thread body
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from modules.runtime.chain import adapter as chain_adapter
from modules.data.projects.service import update_file
from modules.runtime.workflows.execution import WorkflowExecution

logger = logging.getLogger(__name__)

_EXECUTIONS: dict[str, WorkflowExecution] = {}
_LOCK = threading.Lock()

OUTPUT_FILENAME = "implementation-guide.md"


def is_running(project_id: str) -> bool:
    with _LOCK:
        exc = _EXECUTIONS.get(project_id)
        return exc is not None and exc.is_running


def snapshot(project_id: str) -> dict:
    with _LOCK:
        exc = _EXECUTIONS.get(project_id)
    if exc is None:
        return {"running": False, "done": False}
    out: dict = {"running": exc.is_running, "done": exc.is_terminal}
    if exc.outputs.get("filename"):
        out["filename"] = exc.outputs["filename"]
    if exc.error is not None:
        out["error"] = exc.error
    return out


def run_generation(
    project_id: str,
    projects_dir: Path,
    execution: WorkflowExecution,
) -> None:
    """Background thread: build prompt → call AI → write file."""
    try:
        project_dir = projects_dir / project_id

        # Empty system prompt is intentional: the CLI provider routes through
        # chain-agent (via CHAIN_AGENT env var) which supplies its own system
        # prompt from its agent definition. --add-dir grants /data/ access.
        prompt = f"""Read epic.md and architecture.md from {project_dir}.
Also read analysis.md from that directory if it exists.
Return ONLY the markdown document below — do not write any files, do not add preamble.

## Required structure (follow exactly)

# Implementation Guide: {{epic title}}

## Overview
One paragraph: what this epic delivers and how tasks sequence.

## Shared Pre-flight
Bullet list of setup steps that apply across all tasks. No more than 8 bullets.

---

## Task {{N}}: {{Name}}  [Effort: {{X}}]

### What
One to three sentences: what this task accomplishes and why.

### Files
- **Create**: `path/to/new-file.ts` — one-line description
- **Modify**: `path/to/existing.ts` — what changes and why

### Steps
Numbered prose steps. No code. Each step is one to two sentences.
Reference file paths and function names, but do not write their bodies.

### Verify
Two to four bullet points confirming the task is done.
Shell commands allowed (e.g. `ng build --configuration production`). No code logic.

---

## Hard rules — violations will cause a regeneration:
- Document MUST begin with `#`. No preamble.
- NO code blocks — no triple-backtick fences anywhere in the document.
- NO placeholders (`<TBD>`, `...`, `TODO`). Use real workspace-relative file paths.
- Cover EVERY task in the epic. Do not skip any.
- Every task section must have exactly the four subsections: What, Files, Steps, Verify.
- Steps prose only — describe what to do, not the code that does it.
"""
        result = chain_adapter.generate(
            "",
            prompt,
            max_tokens=8192,
        )

        update_file(projects_dir, project_id, OUTPUT_FILENAME, result.text)
        execution.outputs["filename"] = OUTPUT_FILENAME
        execution.complete()

    except Exception as exc:
        logger.exception(
            "generate-epic-guide thread failed project_id=%s", project_id
        )
        execution.fail(str(exc))


def start(project_id: str, projects_dir: Path) -> bool:
    """Spawn background thread. Returns False if already running."""
    with _LOCK:
        existing = _EXECUTIONS.get(project_id)
        if existing and existing.is_running:
            return False
        execution = WorkflowExecution(
            workflow_ref=f"epic_guide/{project_id}",
            inputs={"project_id": project_id, "projects_dir": str(projects_dir)},
        )
        execution.start()
        _EXECUTIONS[project_id] = execution

    thread = threading.Thread(
        target=run_generation,
        args=(project_id, projects_dir, execution),
        name=f"generate-epic-guide[{project_id}]",
        daemon=True,
    )
    thread.start()
    return True
