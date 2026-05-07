"""Registers the spec_gen/generate-spec workflow.

Convention required by WorkflowRepositoryFs:
    Every workflow file must expose register_workflows(repo) at module level.
    The FS adapter calls this with a _PrefixedRepo that namespaces all saves
    under 'spec_gen/<workflow.ref.name>'.
"""
from __future__ import annotations

from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.workflow import Workflow
from modules.ai.services.text_prompts import (
    ANALYSIS_SYSTEM,
    ANALYSIS_USER,
    EPIC_SYSTEM,
    EPIC_USER,
    ARCHITECTURE_SYSTEM,
    ARCHITECTURE_USER,
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
