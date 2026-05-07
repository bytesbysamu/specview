"""Background thread + in-process state for generate-task.

Public surface:
    _EXECUTIONS                     — module-level dict[slot_key -> WorkflowExecution]
    is_running(project_id, task_num) — predicate; task_num=None → any running
    snapshot(project_id)            — read-only summary for the GET route
    start(project_id, projects_dir, task_num=None) — spawn thread
    find_next_missing_task(...)     — pure helper, unit-testable
    extract_task_desc(...)          — pure helper, unit-testable
    collect_prior_task_contracts(...) — pure helper, unit-testable
    run_generation(...)             — thread body (steps 1–11 from epic.md)

Parallel generation: callers may pass a specific task_num to start().
Each (project_id, task_num) pair gets its own _EXECUTIONS slot so multiple
tasks for the same project can run concurrently.

State management was migrated from a flat ``STATE: dict[str, dict]`` to
``_EXECUTIONS: dict[str, WorkflowExecution]`` so the lifecycle is owned by
the WorkflowExecution state machine — see ``modules/workflows/execution.py``.
The route surface (``snapshot()`` / ``start()``) is unchanged; the dict
shape returned to the polling client is reconstructed from the execution's
status + outputs + error.

No Flask imports here. The route layer in routes.py wraps these.
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Optional

from modules.runtime.chain import adapter as chain_adapter
from modules.data.projects.service import get_project, update_file
from modules.quality.lint import lint_task_guide
from modules.runtime.workflows.execution import WorkflowExecution

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bootstrap task extraction (inlined from former modules.ai.prompts)
# ---------------------------------------------------------------------------

def bootstrap_extract_tasks(epic_content: str) -> list[dict]:
    """Parse task table rows from an epic.md document.

    Finds rows matching: | N | **Task Name** | ... | Effort | High/Medium/Low |
    Returns list of dicts with keys {num, name, effort}.
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


# ---------------------------------------------------------------------------
# In-process state — keyed by "{project_id}::{task_num}"
#
# Each slot owns a single WorkflowExecution. The execution's status enum
# (NEW → IN_PROGRESS → COMPLETED | ERROR) replaces the flat running/done
# booleans the old STATE dict carried; ``snapshot()`` projects the
# execution back to the dict shape the polling client expects.
# ---------------------------------------------------------------------------

_EXECUTIONS: dict[str, WorkflowExecution] = {}
_LOCK = threading.Lock()


def _slot(project_id: str, task_num: str) -> str:
    return f"{project_id}::{task_num}"


def _project_slots(project_id: str) -> dict[str, WorkflowExecution]:
    """All execution slots that belong to ``project_id``."""
    return {k: v for k, v in _EXECUTIONS.items() if k.startswith(f"{project_id}::")}


def is_running(project_id: str, task_num: Optional[str] = None) -> bool:
    """True if a thread is running for this project (or specific task_num)."""
    with _LOCK:
        if task_num is not None:
            exc = _EXECUTIONS.get(_slot(project_id, task_num))
            return exc is not None and exc.is_running
        return any(exc.is_running for exc in _project_slots(project_id).values())


def snapshot(project_id: str) -> dict:
    """Return status for the polling GET route.

    If multiple tasks are running, returns the most recently started.
    If none running, returns the most recently completed.
    Falls back to idle shape when no state exists.
    """
    with _LOCK:
        slots = _project_slots(project_id)

    if not slots:
        return {"running": False, "done": False}

    # Prefer running entry; fall back to last entry inserted
    running = [exc for exc in slots.values() if exc.is_running]
    exc = running[0] if running else list(slots.values())[-1]

    out: dict = {"running": exc.is_running, "done": exc.is_terminal}
    for key in ("filename", "taskNum", "taskName"):
        value = exc.outputs.get(key)
        if value is None:
            continue
        out[key] = value
    if exc.outputs.get("allDone"):
        out["allDone"] = True
    # Surface lint artefacts written by run_generation's gate.
    if exc.outputs.get("lintErrors"):
        out["lintErrors"] = exc.outputs["lintErrors"]
    if exc.outputs.get("warnings"):
        out["warnings"] = exc.outputs["warnings"]
    if exc.error is not None:
        out["error"] = exc.error
    return out


def _finish_with_error(execution: WorkflowExecution, message: str) -> None:
    """Move execution to ERROR (or record on already-terminal); idempotent."""
    if execution.is_terminal:
        return
    if execution.is_running:
        execution.fail(message)
        return
    # NEW (no transition through start yet) — coerce through start first
    execution.start()
    execution.fail(message)


def _finish_with_success(execution: WorkflowExecution) -> None:
    """Move execution to COMPLETED if still running."""
    if execution.is_running:
        execution.complete()


# ---------------------------------------------------------------------------
# Pure helpers — unit-testable
# ---------------------------------------------------------------------------

# Supports both integer (2) and decimal (1.1, 1.2) task numbers
_TASK_FILE_RE = re.compile(r"^task-([\d.]+)-.+\.md$")


def find_next_missing_task(tasks: list[dict], filenames: list[str]) -> Optional[dict]:
    """Return the first task whose num has no matching `task-{num}-*.md`.

    `tasks` is the list returned by bootstrap_extract_tasks(); each
    item has keys {num, name, effort}.

    `filenames` is the list of files that already exist in the project
    directory. Only `task-N-*.md` entries matter.

    Returns None when every task has a matching file → caller sets
    `allDone=True`.
    """
    have_nums: set[str] = set()
    for fn in filenames:
        m = _TASK_FILE_RE.match(fn)
        if m:
            have_nums.add(m.group(1))
    for task in tasks:
        if task["num"] not in have_nums:
            return task
    return None


def find_task_by_num(tasks: list[dict], task_num: str) -> Optional[dict]:
    """Return the task dict for a specific task_num, or None."""
    for task in tasks:
        if task["num"] == task_num:
            return task
    return None


def extract_task_desc(epic_content: str, task_num: str) -> str:
    """Extract the `### Task N: ...` block from epic.md."""
    pattern = rf"### Task {re.escape(task_num)}:[^#]*"
    m = re.search(pattern, epic_content, re.DOTALL)
    return m.group(0).strip() if m else ""


def _task_sort_key(num_str: str) -> tuple:
    """Sort key supporting both integer ('2') and decimal ('1.1') task nums."""
    try:
        parts = [float(p) for p in num_str.split(".")]
        return tuple(parts)
    except ValueError:
        return (float("inf"),)


_FILES_SECTION_RE = re.compile(
    r"^#{1,3}\s+(?:\d+\.\s+)?Files\b",
    re.MULTILINE | re.IGNORECASE,
)


def _looks_like_path(s: str) -> bool:
    """True if a backtick-quoted value looks like a file path, not a placeholder."""
    return "{" not in s and ("/" in s or bool(re.match(r"[\w\-]+\.\w{1,5}$", s)))


def _parse_task_contract(text: str) -> dict:
    """Extract declared file surfaces from §3 (Files) of a task guide.

    Parses 'To Create (new)' and 'To Modify' subsections, plus any
    standalone 'Exports' block anywhere in the document.

    Returns:
        creates: list[str] — backtick paths under 'To Create (new)'
        modifies: list[str] — backtick paths under 'To Modify'
        exports: list[str] — backtick paths under a standalone 'Exports' block
    """
    creates: list[str] = []
    modifies: list[str] = []
    exports: list[str] = []

    sec_m = _FILES_SECTION_RE.search(text)
    if not sec_m:
        return {"creates": creates, "modifies": modifies, "exports": exports}

    # Bound to the next H2 heading; search the tail after the section heading
    bound_m = re.search(r"^##\s+", text[sec_m.end():], re.MULTILINE)
    sec_end = sec_m.end() + bound_m.start() if bound_m else len(text)
    sec_text = text[sec_m.start():sec_end]

    sub_re = re.compile(r"^#{2,4}\s+To\s+(Create|Modify)", re.MULTILINE | re.IGNORECASE)
    # All H3+ headings inside the section — used to bound each Create/Modify
    # subsection so trailing siblings like "To Leave Alone" are not absorbed.
    any_sub_re = re.compile(r"^#{2,4}\s+", re.MULTILINE)
    boundaries = [b.start() for b in any_sub_re.finditer(sec_text)]
    sub_ms = list(sub_re.finditer(sec_text))
    for sub_m in sub_ms:
        next_bounds = [b for b in boundaries if b > sub_m.start()]
        sub_end = next_bounds[0] if next_bounds else len(sec_text)
        sub_text = sec_text[sub_m.start():sub_end]
        label = sub_m.group(1).lower()  # 'create' or 'modify'
        for line in sub_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            for pm in re.finditer(r"`([^`]+)`", stripped):
                path = pm.group(1)
                if _looks_like_path(path):
                    (creates if label == "create" else modifies).append(path)

    # Optional standalone Exports block (may appear anywhere in the document)
    exp_m = re.search(r"^#{2,4}\s+Exports?\b", text, re.MULTILINE | re.IGNORECASE)
    if exp_m:
        exp_bound = re.search(r"^#{2,4}\s+", text[exp_m.end():], re.MULTILINE)
        exp_end = exp_m.end() + exp_bound.start() if exp_bound else len(text)
        exp_text = text[exp_m.start():exp_end]
        for line in exp_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            for pm in re.finditer(r"`([^`]+)`", stripped):
                if _looks_like_path(pm.group(1)):
                    exports.append(pm.group(1))

    return {"creates": creates, "modifies": modifies, "exports": exports}


def collect_prior_task_contracts(specs: list[dict], current_task_num: str) -> dict:
    """Parse file-surface contracts from all prior task guides.

    Returns a dict keyed by task number string in sort order:
        {"1": {"creates": [...], "modifies": [...], "exports": [...]}, ...}

    Only task-N-*.md files whose N sorts before current_task_num are included.
    """
    cur_key = _task_sort_key(current_task_num)
    pairs: list[tuple[tuple, str, str]] = []
    for spec in specs:
        m = _TASK_FILE_RE.match(spec.get("filename", ""))
        if not m:
            continue
        num = m.group(1)
        key = _task_sort_key(num)
        if key >= cur_key:
            continue
        pairs.append((key, num, spec.get("content") or ""))
    pairs.sort(key=lambda p: p[0])
    return {num: _parse_task_contract(content) for _, num, content in pairs}


def _format_contracts(contracts: dict) -> str:
    """Render prior-task contracts as a prompt-injectable string.

    Returns "" when contracts is empty or every entry declares no paths —
    PromptBuilder.section() will then omit the block entirely.
    """
    if not contracts:
        return ""
    lines: list[str] = [
        "The following files are already declared by prior tasks.",
        "Do NOT re-declare (new) files listed under Creates.",
        "",
    ]
    any_entry = False
    for task_num in sorted(contracts, key=_task_sort_key):
        c = contracts[task_num]
        creates = c.get("creates") or []
        modifies = c.get("modifies") or []
        exports_ = c.get("exports") or []
        if not creates and not modifies and not exports_:
            continue
        any_entry = True
        lines.append(f"## task-{task_num}")
        if creates:
            lines.append("**Creates (new)**: " + ", ".join(f"`{p}`" for p in creates))
        if modifies:
            lines.append("**Modifies**: " + ", ".join(f"`{p}`" for p in modifies))
        if exports_:
            lines.append("**Exports**: " + ", ".join(f"`{p}`" for p in exports_))
        lines.append("")
    return "\n".join(lines).strip() if any_entry else ""


def collect_prior_task_content(specs: list[dict], current_task_num: str, lines_per_task: int = 60) -> str:
    """Concatenate content of task files whose num sorts before current_task_num."""
    cur_key = _task_sort_key(current_task_num)
    chunks: list[str] = []
    pairs: list[tuple[tuple, str, str]] = []
    for spec in specs:
        m = _TASK_FILE_RE.match(spec.get("filename", ""))
        if not m:
            continue
        num = m.group(1)
        key = _task_sort_key(num)
        if key >= cur_key:
            continue
        pairs.append((key, num, spec.get("content") or ""))
    pairs.sort(key=lambda p: p[0])
    for _, num, content in pairs:
        truncated = "\n".join(content.splitlines()[:lines_per_task])
        chunks.append(f"## task-{num}\n{truncated}")
    return "\n\n".join(chunks)


def _epic_content(specs: list[dict]) -> str:
    for spec in specs:
        if spec.get("filename") == "epic.md":
            return spec.get("content") or ""
    return ""


def _arch_content(specs: list[dict]) -> str:
    for spec in specs:
        if spec.get("filename") == "architecture.md":
            return spec.get("content") or ""
    return ""


# ---------------------------------------------------------------------------
# Filename derivation
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "task"


def derive_task_filename(task_num: str, task_name: str) -> str:
    return f"task-{task_num}-{_slug(task_name)}.md"


# ---------------------------------------------------------------------------
# Background thread body
# ---------------------------------------------------------------------------

def run_generation(
    project_id: str,
    projects_dir: Path,
    task_num: Optional[str] = None,
    execution: Optional[WorkflowExecution] = None,
) -> None:
    """Background-thread body. Walks steps 1–11 from epic.md verbatim.

    If task_num is provided, generates that specific task.
    Otherwise, finds the next missing task automatically.

    ``execution`` is the WorkflowExecution allocated by ``start()`` and is
    passed in so the thread mutates the same Command object the route layer
    can read via ``snapshot()``. Defaulted to None for callers that drive
    this synchronously in tests; in that case a transient execution is
    created and discarded.
    """
    if execution is None:
        execution = WorkflowExecution(
            workflow_ref=f"task_gen/{project_id}",
            inputs={"project_id": project_id, "task_num": task_num},
        )
        execution.start()

    resolved_num = task_num or "__pending__"
    try:
        # Step 1: load project
        project = get_project(projects_dir, project_id)
        if project is None:
            _finish_with_error(execution, "project not found")
            return
        specs = project.get("specs") or []

        # Step 2: find epic.md
        epic = _epic_content(specs)
        if not epic:
            _finish_with_error(execution, "epic.md missing")
            return

        # Step 3: parse tasks
        tasks = bootstrap_extract_tasks(epic)
        if not tasks:
            _finish_with_error(execution, "no tasks parsed from epic.md")
            return

        # Step 4: find task to generate
        filenames = [s.get("filename", "") for s in specs]
        if task_num:
            task = find_task_by_num(tasks, task_num)
            if task is None:
                _finish_with_error(execution, f"task {task_num} not found in epic.md")
                return
        else:
            task = find_next_missing_task(tasks, filenames)
            if task is None:
                execution.outputs["allDone"] = True
                _finish_with_success(execution)
                return

        # Once the task num is resolved, migrate the execution to the
        # numbered slot so the polling client sees per-task state and the
        # original "__pending__" slot does not linger as a stale running entry.
        if task_num is None:
            with _LOCK:
                pending_key = _slot(project_id, "__pending__")
                numbered_key = _slot(project_id, task["num"])
                if _EXECUTIONS.get(pending_key) is execution:
                    _EXECUTIONS.pop(pending_key, None)
                    _EXECUTIONS[numbered_key] = execution
        resolved_num = task["num"]

        # Step 5: extract task description block
        task_desc = extract_task_desc(epic, task["num"])

        # Step 6: collect prior task contracts (structured file declarations)
        contracts = collect_prior_task_contracts(specs, task["num"])
        prior = _format_contracts(contracts)

        # Step 7: build prompt
        project_dir = projects_dir / project_id
        prompt = (
            f"Generate task guide for task {task['num']} ({task['name']}) "
            f"in project at {project_dir}. Read epic.md and architecture.md."
        )
        if prior:
            prompt += f"\n\n{prior}"

        # Step 8: call chain adapter (the only AI call)
        result = chain_adapter.generate("", prompt)

        # Step 9: pre-emit lint — run before any disk write
        flags = lint_task_guide(result.text)
        error_flags = [f for f in flags if f.severity == "error"]
        if error_flags:
            execution.outputs["lintErrors"] = [
                {"rule": f.rule, "severity": f.severity,
                 "message": f.message, "line": f.line}
                for f in error_flags
            ]
            _finish_with_error(
                execution,
                f"lint blocked {len(error_flags)} error-severity flag(s)",
            )
            return
        warning_flags = [f for f in flags if f.severity == "warning"]

        # Step 10: write output file (only reached when no error flags)
        filename = derive_task_filename(task["num"], task["name"])
        update_file(projects_dir, project_id, filename, result.text)

        # Step 12: mark done
        execution.outputs["filename"] = filename
        execution.outputs["taskNum"] = task["num"]
        execution.outputs["taskName"] = task["name"]
        if warning_flags:
            execution.outputs["warnings"] = [
                {"rule": f.rule, "severity": f.severity,
                 "message": f.message, "line": f.line}
                for f in warning_flags
            ]
        _finish_with_success(execution)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("generate-task thread failed project_id=%s task_num=%s", project_id, resolved_num)
        _finish_with_error(execution, str(exc))


def start(project_id: str, projects_dir: Path, task_num: Optional[str] = None) -> bool:
    """Spawn the background thread for a specific task_num (or next missing).

    Returns False if a thread is already running for this exact
    (project_id, task_num) slot — different task_nums can run in parallel.
    """
    slot_key = _slot(project_id, task_num or "__pending__")
    with _LOCK:
        existing = _EXECUTIONS.get(slot_key)
        if existing and existing.is_running:
            return False
        execution = WorkflowExecution(
            workflow_ref=f"task_gen/{project_id}",
            inputs={
                "project_id": project_id,
                "task_num": task_num,
                "projects_dir": str(projects_dir),
            },
        )
        execution.start()  # NEW → IN_PROGRESS inside the lock
        _EXECUTIONS[slot_key] = execution

    thread = threading.Thread(
        target=run_generation,
        args=(project_id, projects_dir, task_num, execution),
        name=f"generate-task[{project_id}::{task_num or 'next'}]",
        daemon=True,
    )
    thread.start()
    return True
