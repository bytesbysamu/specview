"""spec_gen Blueprint — POST /api/spec-gen/generate.

The handler:
  1. Validates the request.
  2. Loads the named Workflow from app.workflow_repository.
  3. Constructs a WorkflowExecution and drains WorkflowRuntime.
  4. Returns the accumulated step outputs as a list of named files.

The handler inspects no steps and contains no AI call logic.
"""
from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request

from dtos.models import (
    BootstrapFile,
    BootstrapProjectRequest,
    BootstrapProjectResponse,
)
from modules.auth.decorators import require_auth
from modules.data.context.service import read_context
from modules.runtime.workflows.execution import WorkflowExecution
from modules.runtime.workflows.repository import WorkflowNotFound
from modules.runtime.workflows.runtime import WorkflowRuntime
from modules.runtime.workflows.steps import StepCompleted, StepFailed
from modules.usage.decorators import check_usage_limit

spec_gen_bp = Blueprint("spec_gen", __name__, url_prefix="/api/spec-gen")

_WORKFLOW_NAME = "spec_gen/generate-spec"

_STEP_TO_FILENAME: dict[str, str] = {
    "analysis": "analysis.md",
    "epic": "epic.md",
    "architecture": "architecture.md",
}


def _output_text(value: object) -> str:
    """AICall._invoke returns a ChainResult; templates need its .text.

    Tolerates plain strings for tests that stub StepCompleted.output directly.
    """
    text_attr = getattr(value, "text", None)
    if text_attr is not None:
        return str(text_attr)
    if value is None:
        return ""
    return str(value)


@spec_gen_bp.post("/generate")
@require_auth
@check_usage_limit("spec_gen")
def generate():
    req = BootstrapProjectRequest.model_validate(
        request.get_json(force=True, silent=False) or {}
    )

    inputs = {
        "braindump": req.braindump.strip(),
        "project_name": req.project_name.strip(),
        "builder": req.builder or read_context("builder"),
        "principles": req.principles or read_context("principles"),
        "codebase": req.codebase or read_context("codebase"),
        "references": req.references or read_context("references"),
    }

    repo = current_app.workflow_repository
    workflow = repo.get(_WORKFLOW_NAME)

    execution = WorkflowExecution(
        workflow_ref=_WORKFLOW_NAME,
        inputs=inputs,
    )

    t0 = time.monotonic()
    runtime = WorkflowRuntime()
    outputs: dict[str, str] = {}

    for event in runtime.run(execution, workflow):
        if isinstance(event, StepCompleted):
            outputs[event.step_name] = _output_text(event.output)
        elif isinstance(event, StepFailed):
            return (
                jsonify(
                    {
                        "error": event.error,
                        "step": event.step_name,
                        "status": 502,
                    }
                ),
                502,
            )

    latency_ms = int((time.monotonic() - t0) * 1000)
    files = [
        BootstrapFile(filename=filename, content=outputs.get(step_name, ""))
        for step_name, filename in _STEP_TO_FILENAME.items()
    ]
    return jsonify(
        BootstrapProjectResponse(files=files, latencyMs=latency_ms).model_dump()
    )


@spec_gen_bp.errorhandler(WorkflowNotFound)
def _workflow_not_found(exc: WorkflowNotFound):
    return jsonify({"error": str(exc), "status": 404}), 404
