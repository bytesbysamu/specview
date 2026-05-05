"""Registers the spec_gen/bootstrap-project workflow plus three per-step
sub-workflows (analysis-only, epic-only, architecture-only) used by the
SaaS-Reliability retry route (Rel-T4).

Convention required by WorkflowRepositoryFs:
    Every workflow file must expose register_workflows(repo) at module level.
    The FS adapter calls this with a _PrefixedRepo that namespaces all saves
    under 'spec_gen/<workflow.ref.name>'.
"""
from __future__ import annotations

from dtos.models import BootstrapFile
from modules.ai.prompts import (
    BOOTSTRAP_ANALYSIS_SYSTEM,
    BOOTSTRAP_ANALYSIS_USER,
    BOOTSTRAP_ARCHITECTURE_SYSTEM,
    BOOTSTRAP_ARCHITECTURE_USER,
    BOOTSTRAP_EPIC_SYSTEM,
    BOOTSTRAP_EPIC_USER,
)
from modules.runtime.workflows.steps import registry as _registry
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.steps.base import StepContext
from modules.runtime.workflows.steps.compute import Compute
from modules.runtime.workflows.workflow import Workflow

_MARSHAL_FILES_NAME = "bootstrap.marshal_files"


def marshal_files(context: StepContext) -> list[BootstrapFile]:
    """Convert AICall ChainResult outputs into a BootstrapFile list."""
    return [
        BootstrapFile(filename="analysis.md", content=context.outputs["analysis"].text),
        BootstrapFile(filename="epic.md", content=context.outputs["epic"].text),
        BootstrapFile(filename="architecture.md", content=context.outputs["architecture"].text),
    ]


def _ensure_marshal_files_registered() -> None:
    """Idempotent registration — WorkflowRepositoryFs.from_modules_dir re-imports
    this file on every app factory invocation (tests + dev reloads)."""
    if _MARSHAL_FILES_NAME not in _registry.registered_names():
        _registry.register(_MARSHAL_FILES_NAME, marshal_files)


_ensure_marshal_files_registered()


# ── Shared step builders ──────────────────────────────────────────────────
#
# Each per-step sub-workflow registers a single AICall identical in shape
# to the corresponding step inside the parent bootstrap-project workflow.
# Building each step via a helper guarantees the parent and the sub-workflow
# stay byte-for-byte equivalent for that step (system prompt, template,
# input keys, model, max_tokens, stream flag).
#
# NB: AICall.input_keys lists ONLY workflow-level inputs (validated against
# context.inputs by AbstractStep._validate_inputs). Prior step outputs (e.g.
# "analysis", "epic") flow through prompt_template.format_map via the merged
# {**outputs, **inputs} dict at render time — see ai_call.py docstring.
# That mechanism is what lets each sub-workflow accept prior outputs as
# top-level workflow inputs without listing them under input_keys.


def _analysis_step() -> AICall:
    return AICall(
        name="analysis",
        system=BOOTSTRAP_ANALYSIS_SYSTEM,
        prompt_template=BOOTSTRAP_ANALYSIS_USER,
        input_keys=("braindump", "project_name", "builder"),
        model="claude-haiku-4-5",  # cheap, short prompt
    )


def _epic_step() -> AICall:
    return AICall(
        name="epic",
        system=BOOTSTRAP_EPIC_SYSTEM,
        prompt_template=BOOTSTRAP_EPIC_USER,
        input_keys=("braindump", "project_name", "builder", "principles"),
        model="claude-sonnet-4-5",  # default; explicit for auditability
    )


def _architecture_step() -> AICall:
    # stream=True: architecture is the longest step (16k tokens) and the
    # highest UX value for live progress; the polling endpoint reads the
    # rolling 500-char tail from context.outputs["_partials"]["architecture"]
    # (see ai_call.py and the SaaS-Reliability architecture doc).
    return AICall(
        name="architecture",
        system=BOOTSTRAP_ARCHITECTURE_SYSTEM,
        prompt_template=BOOTSTRAP_ARCHITECTURE_USER,
        input_keys=(
            "braindump",
            "project_name",
            "builder",
            "principles",
            "codebase",
            "references",
        ),
        model="claude-opus-4-7",  # quality matters most here
        max_tokens=16384,  # per braindump-raise-max-tokens.md
        stream=True,
    )


def _build_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-project")  # _PrefixedRepo prepends spec_gen/
        .inputs(
            "braindump",
            "project_name",
            "builder",
            "principles",
            "codebase",
            "references",
        )
        .outputs("analysis", "epic", "architecture", "files")
        .step(_analysis_step())
        .step(_epic_step())
        .step(_architecture_step())
        .step(Compute(name="files", fn_name=_MARSHAL_FILES_NAME))
        .build()
    )


def _build_analysis_only_workflow() -> Workflow:
    """Sub-workflow for analysis-only retry. Mirrors the parent's analysis step.

    Inputs match the parent workflow's analysis step exactly so the retry
    route can pass-through the same input keys.
    """
    return (
        Workflow.builder("bootstrap-analysis-only")
        .inputs("braindump", "project_name", "builder")
        .outputs("analysis")
        .step(_analysis_step())
        .build()
    )


def _build_epic_only_workflow() -> Workflow:
    """Sub-workflow for epic-only retry.

    The epic step's prompt template references {analysis.text}, so the retry
    route supplies "analysis" as a workflow input rather than re-running the
    analysis step. Declaring "analysis" in workflow inputs lets
    AbstractStep._validate_inputs accept the prompt's reference (the merged
    {**outputs, **inputs} dict makes inputs visible to format_map).
    """
    return (
        Workflow.builder("bootstrap-epic-only")
        .inputs("braindump", "project_name", "builder", "principles", "analysis")
        .outputs("epic")
        .step(_epic_step())
        .build()
    )


def _build_architecture_only_workflow() -> Workflow:
    """Sub-workflow for architecture-only retry.

    Both "analysis" and "epic" flow as workflow inputs (the prompt template
    references {epic.text}). The architecture step itself opts into streaming
    via _architecture_step()'s stream=True so the retry surface matches the
    parent workflow's live-preview behaviour.
    """
    return (
        Workflow.builder("bootstrap-architecture-only")
        .inputs(
            "braindump",
            "project_name",
            "builder",
            "principles",
            "codebase",
            "references",
            "analysis",
            "epic",
        )
        .outputs("architecture")
        .step(_architecture_step())
        .build()
    )


def register_workflows(repo) -> None:
    """Called by WorkflowRepositoryFs auto-discovery at app startup.

    Registers the parent bootstrap-project workflow plus three per-step
    sub-workflows used by the SaaS-Reliability retry route (Rel-T4). All four
    save under 'spec_gen/' via the _PrefixedRepo wrapper.
    """
    repo.save(_build_workflow())
    repo.save(_build_analysis_only_workflow())
    repo.save(_build_epic_only_workflow())
    repo.save(_build_architecture_only_workflow())
