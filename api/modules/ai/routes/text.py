import logging
import threading
import time
import uuid
from pathlib import Path

from flask import Blueprint, current_app, request, jsonify

from dtos.models import (
    BootstrapProjectRequest,
    BootstrapFile,
    RetryBootstrapRequest,
)
from pydantic import ValidationError
from modules.runtime.chain import adapter as chain_adapter
from config import PROJECTS_DIR
from modules.data.context.service import read_context
from modules.ai.services.task_gen import bootstrap_extract_tasks
from modules.data.templates.generators import generate_spec_index, generate_timeline, generate_readme
from modules.runtime.workflows.execution import ExecutionStatus, WorkflowExecution
from modules.runtime.workflows.runtime import WorkflowRuntime
from modules.auth.decorators import require_auth
from modules.usage.decorators import check_usage_limit

logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai/text")

# In-process job registry for the async bootstrap-project route.
# The dict owns lifetime; WorkflowExecution owns state. Architecture doc
# § In-Process Job Registry. Co-located with both handlers that mutate it.
_BOOTSTRAP_JOBS: dict[str, WorkflowExecution] = {}

# ---------------------------------------------------------------------------
# Bootstrap prompt builders (inlined from text_prompts.py — Thin API Phase 3)
# ---------------------------------------------------------------------------

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


def _bootstrap_analysis_prompt(
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


def _bootstrap_epic_prompt(
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


def _bootstrap_architecture_prompt(
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


def _run_bootstrap_thread(execution: WorkflowExecution) -> None:
    """Background thread body. Drives the three-step chain; state machine via WorkflowExecution."""
    t0 = time.monotonic()
    inputs = execution.inputs
    try:
        execution.current_step_name = "analysis"
        system, prompt = _bootstrap_analysis_prompt(
            inputs["braindump"], inputs["project_name"], inputs["builder"]
        )
        analysis = chain_adapter.generate(system, prompt).text
        execution.outputs["analysis"] = analysis

        if execution.status is ExecutionStatus.CANCELLING:
            execution.cancel()
            execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
            return

        execution.current_step_name = "epic"
        system, prompt = _bootstrap_epic_prompt(
            inputs["braindump"], inputs["project_name"], analysis,
            inputs["builder"], inputs["principles"],
        )
        epic = chain_adapter.generate(system, prompt).text
        execution.outputs["epic"] = epic

        if execution.status is ExecutionStatus.CANCELLING:
            execution.cancel()
            execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
            return

        execution.current_step_name = "architecture"
        system, prompt = _bootstrap_architecture_prompt(
            inputs["braindump"], inputs["project_name"], epic,
            inputs["builder"], inputs["principles"],
            inputs["codebase"], inputs["references"],
        )
        architecture = chain_adapter.generate(system, prompt, max_tokens=16384).text
        execution.outputs["architecture"] = architecture

        execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
        execution.complete()
    except Exception as exc:
        logger.exception("bootstrap thread failed: %s", exc)
        execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
        if not execution.is_terminal:
            execution.fail(str(exc))


@ai_bp.post("/bootstrap-project")
@require_auth
@check_usage_limit("bootstrap")
def bootstrap_project():
    """Async bootstrap: returns 202 + job_id; chain runs in a daemon thread.

    Caller polls GET /bootstrap-project/status/{job_id} until done=true.
    Eliminates the held HTTP connection that 10–25 minute chain runs were
    losing to infrastructure-level connection termination.
    """
    req = BootstrapProjectRequest.model_validate(
        request.get_json(force=True, silent=False) or {}
    )
    project_name = req.project_name.strip()
    braindump = req.braindump.strip()
    if not project_name or not braindump:
        return jsonify({"error": "project_name and braindump are required"}), 400

    job_id = str(uuid.uuid4())
    _projects_dir = Path(PROJECTS_DIR)
    braindump_path = str(_projects_dir / job_id / "braindump.md")
    inputs = {
        "braindump": braindump,
        "braindump_path": braindump_path,
        "project_name": project_name,
        "analysis_path": str(_projects_dir / job_id / "analysis.md"),
        "epic_path": str(_projects_dir / job_id / "epic.md"),
        "builder": req.builder or read_context("builder"),
        "principles": req.principles or read_context("principles"),
        "codebase": req.codebase or read_context("codebase"),
        "references": req.references or read_context("references"),
    }
    execution = WorkflowExecution(workflow_ref="ai/bootstrap-project", inputs=inputs)
    execution.start()
    _BOOTSTRAP_JOBS[job_id] = execution
    threading.Thread(
        target=_run_bootstrap_thread,
        args=(execution,),
        name=f"bootstrap[{job_id[:8]}]",
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id}), 202


def _text_of(value) -> str:
    """ChainResult-or-str adapter for backward compat with sub-workflow outputs."""
    return value.text if hasattr(value, "text") else (value or "")


@ai_bp.get("/bootstrap-project/status/<job_id>")
@require_auth
def bootstrap_status(job_id: str):
    """Status snapshot for an async bootstrap job. Evicts on first terminal read."""
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None:
        return jsonify({"error": "job not found"}), 404

    done = execution.is_terminal
    partials = execution.outputs.get("_partials", {}) if isinstance(
        execution.outputs.get("_partials"), dict
    ) else {}
    body: dict = {
        "running": execution.is_running,
        "done": done,
        "status": execution.status.value,
        "current_step": execution.current_step_name,
        "partial": partials.get(execution.current_step_name, "") if execution.current_step_name else "",
        "warnings": list(execution.warnings),
    }

    # Expose completed steps as partial_files even before done=true so the
    # frontend can write each file to disk as soon as its step finishes.
    _PARTIAL_STEP_FILES = [
        ("analysis", "analysis.md"),
        ("epic", "epic.md"),
        ("architecture", "architecture.md"),
    ]
    partial_files = [
        {"filename": fname, "content": _text_of(execution.outputs[key])}
        for key, fname in _PARTIAL_STEP_FILES
        if key in execution.outputs and _text_of(execution.outputs[key])
    ]
    if partial_files:
        body["partial_files"] = partial_files

    if done:
        _BOOTSTRAP_JOBS.pop(job_id, None)  # purge-on-first-terminal-read
        if execution.status is ExecutionStatus.COMPLETED:
            outputs = execution.outputs
            project_name = execution.inputs["project_name"]
            epic = outputs.get("epic", "")
            epic_text = _text_of(epic)
            tasks = bootstrap_extract_tasks(epic_text)
            files = [
                BootstrapFile(filename="spec-index.md", content=generate_spec_index(project_name)),
                BootstrapFile(filename="analysis.md", content=_text_of(outputs.get("analysis", ""))),
                BootstrapFile(filename="epic.md", content=epic_text),
                BootstrapFile(filename="architecture.md", content=_text_of(outputs.get("architecture", ""))),
                BootstrapFile(filename="timeline.md", content=generate_timeline(project_name, tasks)),
                BootstrapFile(filename="README.md", content=generate_readme(project_name)),
            ]
            body["files"] = [f.model_dump() for f in files]
            body["latencyMs"] = outputs.get("latency_ms", 0)
        elif execution.status is ExecutionStatus.ERROR:
            if execution.error:
                body["error"] = execution.error
            body["failed_step"] = execution.current_step_name

    return jsonify(body)


# ---------------------------------------------------------------------------
# Cancel + retry — saas-reliability Task 4
# ---------------------------------------------------------------------------

@ai_bp.post("/bootstrap-project/<job_id>/cancel")
@require_auth
def bootstrap_cancel(job_id: str):
    """Request cooperative cancellation of an in-flight bootstrap job.

    Flips status NEW|IN_PROGRESS -> CANCELLING via WorkflowExecution.request_cancel().
    The runtime (Rel-T1) reads the flag between step boundaries and transitions
    CANCELLING -> CANCELLED on the next iteration. Subsequent polls of the status
    endpoint will surface the terminal CANCELLED state and evict the job.

    Returns 202 — the request has been accepted; cancellation is not yet final.
    """
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None:
        return jsonify({"error": "job not found"}), 404
    if execution.status not in (ExecutionStatus.NEW, ExecutionStatus.IN_PROGRESS):
        return jsonify({
            "error": "cannot cancel",
            "status": execution.status.value,
        }), 409
    execution.request_cancel()
    return jsonify({"status": execution.status.value}), 202


# Mapping of retry step name -> Rel-T3 sub-workflow ref.
# Each sub-workflow is a single-step Workflow registered by
# modules/ai/workflows/spec_gen/bootstrap.py (Rel-T3 lane).
_RETRY_WORKFLOW_REFS = {
    "analysis": "spec_gen/bootstrap-analysis-only",
    "epic": "spec_gen/bootstrap-epic-only",
    "architecture": "spec_gen/bootstrap-architecture-only",
}


def _run_bootstrap_via_runtime(execution: WorkflowExecution, workflow) -> None:
    """Background-thread body that drives WorkflowRuntime to completion.

    Used by the retry route to spawn a sub-workflow execution. The runtime
    owns the lifecycle transitions; we only need to drain the event stream.
    Unlike _run_bootstrap_thread (which calls chain_adapter directly), this
    function honours the Rel-T1 cooperative-cancellation seam because it
    delegates to WorkflowRuntime.run.
    """
    t0 = time.monotonic()
    try:
        for _event in WorkflowRuntime().run(execution, workflow):
            pass
    except Exception as exc:
        logger.exception("bootstrap thread failed: %s", exc)
        if not execution.is_terminal:
            execution.fail(str(exc))
    finally:
        execution.outputs.setdefault("latency_ms", int((time.monotonic() - t0) * 1000))


@ai_bp.post("/bootstrap-project/<job_id>/retry")
@require_auth
@check_usage_limit("bootstrap")
def bootstrap_retry(job_id: str):
    """Retry a single bootstrap step against the matching Rel-T3 sub-workflow.

    Body: {"step": "analysis" | "epic" | "architecture"}.

    The prior execution's outputs become inputs for the new run — epic retry
    re-uses the prior analysis text; architecture retry re-uses both. Returns
    202 + a fresh job_id; the caller resumes polling the status endpoint with
    the new id. Each retry counts against the daily bootstrap quota.
    """
    try:
        req = RetryBootstrapRequest.model_validate(
            request.get_json(force=True, silent=False) or {}
        )
    except ValidationError:
        return jsonify({
            "error": "invalid step",
            "allowed": sorted(_RETRY_WORKFLOW_REFS.keys()),
        }), 400
    step = req.step.value
    workflow_ref = _RETRY_WORKFLOW_REFS[step]

    prior = _BOOTSTRAP_JOBS.get(job_id)
    if prior is None:
        return jsonify({"error": "job not found"}), 404

    new_inputs = dict(prior.inputs)
    # Inject prior outputs as inputs so downstream steps have their dependencies.
    # epic retry needs analysis; architecture retry needs both.
    if step in ("epic", "architecture"):
        if "analysis" in prior.outputs:
            new_inputs["analysis"] = prior.outputs["analysis"].text
    if step == "architecture":
        if "epic" in prior.outputs:
            new_inputs["epic"] = prior.outputs["epic"].text

    try:
        workflow = current_app.workflow_repository.get(workflow_ref)
    except Exception as exc:
        return jsonify({
            "error": "sub-workflow unavailable",
            "workflow_ref": workflow_ref,
            "detail": str(exc),
        }), 503

    new_id = str(uuid.uuid4())
    new_execution = WorkflowExecution(workflow_ref=workflow_ref, inputs=new_inputs)
    _BOOTSTRAP_JOBS[new_id] = new_execution
    threading.Thread(
        target=_run_bootstrap_via_runtime,
        args=(new_execution, workflow),
        name=f"retry-{step}[{new_id[:8]}]",
        daemon=True,
    ).start()
    return jsonify({"job_id": new_id}), 202
