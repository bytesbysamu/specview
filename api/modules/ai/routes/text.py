import json
import re
import threading
import time
import uuid

from flask import Blueprint, current_app, request, jsonify

from dtos.models import (
    RewriteRequest,
    RewriteResponse,
    IterateRequest,
    IterateResponse,
    LintBraindumpRequest,
    LintBraindumpResponse,
    ReviewRequest,
    ReviewResponse,
    GenerateRequest,
    GenerateResponse,
    GenerateSpecRequest,
    GenerateSpecResponse,
    BootstrapProjectRequest,
    BootstrapFile,
    RetryBootstrapRequest,
)
from pydantic import ValidationError
from modules.runtime.chain import adapter as chain_adapter
from modules.runtime.chain.errors import ProviderError
from modules.ai.prompts import (
    rewrite_prompt,
    iterate_prompt,
    lint_braindump_prompt,
    review_prompt,
    generate_prompt,
    generate_spec_prompt,
    bootstrap_analysis_prompt,
    bootstrap_epic_prompt,
    bootstrap_architecture_prompt,
    bootstrap_extract_tasks,
)
from modules.data.context.service import read_context
from modules.data.templates.generators import generate_spec_index, generate_timeline, generate_readme
from modules.runtime.workflows.execution import ExecutionStatus, WorkflowExecution
from modules.runtime.workflows.runtime import WorkflowRuntime
from modules.ai.errors import AIProviderError
from modules.auth.decorators import require_auth
from modules.usage.decorators import check_usage_limit

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai/text")

# In-process job registry for the async bootstrap-project route.
# The dict owns lifetime; WorkflowExecution owns state. Architecture doc
# § In-Process Job Registry. Co-located with both handlers that mutate it.
_BOOTSTRAP_JOBS: dict[str, WorkflowExecution] = {}


@ai_bp.post("/rewrite")
@require_auth
def rewrite():
    req = RewriteRequest.model_validate(request.get_json(force=True, silent=False) or {})
    text = req.text.strip()
    instructions = (req.instructions or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    system, prompt = rewrite_prompt(text, instructions)
    try:
        try:
            result = chain_adapter.rewrite(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = RewriteResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


@ai_bp.post("/iterate")
@require_auth
def iterate():
    req = IterateRequest.model_validate(request.get_json(force=True, silent=False) or {})
    document = req.document.strip()
    instruction = (req.instruction or "").strip()
    if not document:
        return jsonify({"error": "document is required"}), 400
    system, prompt = iterate_prompt(instruction, document, "", "")
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = IterateResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


@ai_bp.post("/lint-braindump")
@require_auth
def lint_braindump():
    req = LintBraindumpRequest.model_validate(request.get_json(force=True, silent=False) or {})
    braindump = req.braindump.strip()
    if not braindump:
        return jsonify({"error": "braindump is required"}), 400
    system, prompt = lint_braindump_prompt(braindump)
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        try:
            parsed = json.loads(result.text)
        except (ValueError, KeyError) as exc:
            raise AIProviderError("lint_braindump_parse_failed") from exc
        response = LintBraindumpResponse(
            ready=parsed["ready"],
            flags=parsed.get("flags", []),
        )
        return jsonify(response.model_dump(mode="json"))
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


@ai_bp.post("/review")
@require_auth
def review():
    req = ReviewRequest.model_validate(request.get_json(force=True, silent=False) or {})
    system, prompt = review_prompt(req.documents)
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        raw = re.sub(r'```(?:json)?\n?|\n?```', '', result.text).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise AIProviderError("review_parse_failed")
        response = ReviewResponse(scores=parsed["scores"], issues=parsed["issues"])
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


@ai_bp.post("/generate")
@require_auth
def generate():
    req = GenerateRequest.model_validate(request.get_json(force=True, silent=False) or {})
    prompt_text = req.prompt.strip()
    if not prompt_text:
        return jsonify({"error": "prompt is required"}), 400
    # Express parity: inject builder context (principles NOT injected).
    builder = read_context("builder")
    tone = req.tone or ""
    system, user_prompt = generate_prompt(prompt_text, builder, "", tone)
    try:
        try:
            result = chain_adapter.generate(system, user_prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = GenerateResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


@ai_bp.post("/generate-spec")
@require_auth
def generate_spec():
    req = GenerateSpecRequest.model_validate(request.get_json(force=True, silent=False) or {})
    input_text = req.input.strip()
    if not input_text:
        return jsonify({"error": "input is required"}), 400
    builder = read_context("builder")
    principles = read_context("principles")
    system, prompt = generate_spec_prompt(input_text, builder, principles)
    try:
        try:
            result = chain_adapter.generate(system, prompt)
        except ProviderError as exc:
            raise AIProviderError(exc.message) from exc
        response = GenerateSpecResponse(text=result.text, latencyMs=result.latency_ms)
        return jsonify(response.model_dump())
    except AIProviderError as exc:
        return jsonify({"error": str(exc), "status": 502}), 502


def _run_bootstrap_thread(execution: WorkflowExecution) -> None:
    """Background thread body. Drives the three-step chain; state machine via WorkflowExecution."""
    t0 = time.monotonic()
    inputs = execution.inputs
    try:
        execution.current_step_name = "analysis"
        system, prompt = bootstrap_analysis_prompt(
            inputs["braindump"], inputs["project_name"], inputs["builder"]
        )
        analysis = chain_adapter.generate(system, prompt).text
        execution.outputs["analysis"] = analysis

        execution.current_step_name = "epic"
        system, prompt = bootstrap_epic_prompt(
            inputs["braindump"], inputs["project_name"], analysis,
            inputs["builder"], inputs["principles"],
        )
        epic = chain_adapter.generate(system, prompt).text
        execution.outputs["epic"] = epic

        execution.current_step_name = "architecture"
        system, prompt = bootstrap_architecture_prompt(
            inputs["braindump"], inputs["project_name"], epic,
            inputs["builder"], inputs["principles"],
            inputs["codebase"], inputs["references"],
        )
        architecture = chain_adapter.generate(system, prompt, max_tokens=16384).text
        execution.outputs["architecture"] = architecture

        execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
        execution.complete()
    except Exception as exc:
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
    inputs = {
        "braindump": braindump,
        "project_name": project_name,
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
        elif execution.error:
            body["error"] = execution.error
        elif execution.status is ExecutionStatus.CANCELLED:
            body["status"] = "cancelled"

    return jsonify(body)


# ---------------------------------------------------------------------------
# Cancel + retry — saas-reliability Task 4
# ---------------------------------------------------------------------------

@ai_bp.post("/bootstrap-project/<job_id>/cancel")
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
        if not execution.is_terminal:
            execution.fail(str(exc))
    finally:
        execution.outputs.setdefault("latency_ms", int((time.monotonic() - t0) * 1000))


@ai_bp.post("/bootstrap-project/<job_id>/retry")
def bootstrap_retry(job_id: str):
    """Retry a single bootstrap step against the matching Rel-T3 sub-workflow.

    Body: {"step": "analysis" | "epic" | "architecture"}.

    The prior execution's outputs become inputs for the new run — epic retry
    re-uses the prior analysis text; architecture retry re-uses both. Returns
    202 + a fresh job_id; the caller resumes polling the status endpoint with
    the new id. Counts as one bootstrap usage call (covered by the existing
    ``@check_usage_limit("bootstrap")`` decorator on the parent route).
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
    if step in ("epic", "architecture"):
        analysis = prior.outputs.get("analysis")
        new_inputs["analysis"] = _text_of(analysis) if analysis else ""
    if step == "architecture":
        epic = prior.outputs.get("epic")
        new_inputs["epic"] = _text_of(epic) if epic else ""

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
