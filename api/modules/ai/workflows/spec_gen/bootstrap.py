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
        system="",
        prompt_template="Generate analysis for project '{project_name}' from braindump at {braindump_path}.",
        input_keys=("project_name", "braindump_path"),
        model="claude-haiku-4-5",  # cheap, short prompt
    )


def _epic_step() -> AICall:
    return AICall(
        name="epic",
        system="",
        prompt_template="Generate epic for project '{project_name}' from analysis at {analysis_path}.",
        input_keys=("project_name", "analysis_path"),
        model="claude-sonnet-4-5",  # default; explicit for auditability
    )


def _architecture_step() -> AICall:
    # stream=True: architecture is the longest step (16k tokens) and the
    # highest UX value for live progress; the polling endpoint reads the
    # rolling 500-char tail from context.outputs["_partials"]["architecture"]
    # (see ai_call.py and the SaaS-Reliability architecture doc).
    return AICall(
        name="architecture",
        system="",
        prompt_template="Generate architecture for project '{project_name}' from epic at {epic_path}.",
        input_keys=("project_name", "epic_path"),
        model="claude-opus-4-7",  # quality matters most here
        max_tokens=16384,  # per braindump-raise-max-tokens.md
        stream=True,
    )


def _build_workflow() -> Workflow:
    return (
        Workflow.builder("bootstrap-project")  # _PrefixedRepo prepends spec_gen/
        .inputs(
            "braindump_path",
            "project_name",
            "analysis_path",
            "epic_path",
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
        .inputs("project_name", "braindump_path")
        .outputs("analysis")
        .step(_analysis_step())
        .build()
    )


def _build_epic_only_workflow() -> Workflow:
    """Sub-workflow for epic-only retry.

    The epic step's prompt template references {analysis_path}, so the retry
    route supplies "analysis_path" as a workflow input. Declaring it in workflow
    inputs lets AbstractStep._validate_inputs accept the prompt's reference.
    """
    return (
        Workflow.builder("bootstrap-epic-only")
        .inputs("project_name", "analysis_path")
        .outputs("epic")
        .step(_epic_step())
        .build()
    )


def _build_architecture_only_workflow() -> Workflow:
    """Sub-workflow for architecture-only retry.

    The architecture step's prompt template references {epic_path}. The step
    opts into streaming via _architecture_step()'s stream=True so the retry
    surface matches the parent workflow's live-preview behaviour.
    """
    return (
        Workflow.builder("bootstrap-architecture-only")
        .inputs(
            "project_name",
            "epic_path",
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
