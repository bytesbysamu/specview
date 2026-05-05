"""Tests for the spec_gen/bootstrap-project workflow definition."""
from __future__ import annotations

from dtos.models import BootstrapFile
from modules.runtime.chain.types import ChainResult
from modules.ai.workflows.spec_gen import bootstrap as bootstrapModule
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.steps.base import StepContext
from modules.runtime.workflows.steps.compute import Compute


buildWorkflow = bootstrapModule._build_workflow
marshalFiles = bootstrapModule.marshal_files
registerWorkflows = bootstrapModule.register_workflows


class TestBootstrapWorkflowShape:
    def test_step_count_is_four(self):
        wf = buildWorkflow()
        assert wf.step_count == 4, f"Expected 4 steps, got {wf.step_count}"

    def test_step_0_is_aicall_named_analysis(self):
        wf = buildWorkflow()
        step = wf.steps[0]
        assert isinstance(step, AICall)
        assert step.name == "analysis"

    def test_step_1_is_aicall_named_epic(self):
        wf = buildWorkflow()
        step = wf.steps[1]
        assert isinstance(step, AICall)
        assert step.name == "epic"

    def test_step_2_is_aicall_named_architecture_with_max_tokens_16384(self):
        wf = buildWorkflow()
        step = wf.steps[2]
        assert isinstance(step, AICall)
        assert step.name == "architecture"
        assert step.max_tokens == 16384, (
            f"architecture step must carry max_tokens=16384 per "
            f"braindump-raise-max-tokens.md; got {step.max_tokens}"
        )

    def test_step_3_is_compute_named_files(self):
        wf = buildWorkflow()
        step = wf.steps[3]
        assert isinstance(step, Compute)
        assert step.name == "files"
        assert step.fn_name == "bootstrap.marshal_files"

    def test_workflow_ref_name_is_bootstrap_project(self):
        wf = buildWorkflow()
        assert str(wf.ref) == "bootstrap-project"

    def test_workflow_inputs_are_complete(self):
        wf = buildWorkflow()
        assert wf.inputs == frozenset(
            {"braindump", "project_name", "builder", "principles", "codebase", "references"}
        )

    def test_analysis_input_keys(self):
        wf = buildWorkflow()
        step = wf.steps[0]
        assert set(step.input_keys) == {"braindump", "project_name", "builder"}

    def test_architecture_input_keys_include_codebase_and_references(self):
        wf = buildWorkflow()
        step = wf.steps[2]
        keys = set(step.input_keys)
        assert "codebase" in keys, "architecture step must declare codebase as required input"
        assert "references" in keys, "architecture step must declare references as required input"


class TestMarshalFiles:
    def makeContext(self, analysis="a", epic="b", arch="c") -> StepContext:
        return StepContext(
            run_id="test-run",
            inputs={},
            outputs={
                "analysis": ChainResult(text=analysis, latency_ms=1),
                "epic": ChainResult(text=epic, latency_ms=1),
                "architecture": ChainResult(text=arch, latency_ms=1),
            },
        )

    def test_returns_three_bootstrap_file_instances(self):
        result = marshalFiles(self.makeContext())
        assert len(result) == 3
        assert all(isinstance(f, BootstrapFile) for f in result)

    def test_filenames_in_order(self):
        result = marshalFiles(self.makeContext())
        assert result[0].filename == "analysis.md"
        assert result[1].filename == "epic.md"
        assert result[2].filename == "architecture.md"

    def test_content_comes_from_chainresult_text(self):
        result = marshalFiles(self.makeContext(analysis="alpha", epic="beta", arch="gamma"))
        assert result[0].content == "alpha"
        assert result[1].content == "beta"
        assert result[2].content == "gamma"


class TestWorkflowRegistration:
    def test_register_workflows_saves_under_bootstrap_project(self):
        saved: dict = {}

        class _MockRepo:
            def save(self, workflow) -> None:
                saved[str(workflow.ref)] = workflow

        registerWorkflows(_MockRepo())

        assert "bootstrap-project" in saved, (
            "register_workflows must save a workflow whose ref.name is 'bootstrap-project'"
        )
        wf = saved["bootstrap-project"]
        assert wf.step_count == 4
