"""Workflow aggregate and builder tests — Layer C.

Uses a minimal `NoopStep(AbstractStep)` subclass as the test fixture. Tests
do not inspect step internals — they assert on Step identity and ordering only.
"""
from __future__ import annotations

import pytest

from modules.runtime.workflows import Workflow, WorkflowRef
from modules.runtime.workflows.steps import AbstractStep


# ── Test step fixture ─────────────────────────────────────────────────────────
# Minimal AbstractStep subclass; no provider, no I/O. Suitable as a placeholder
# in workflow-container tests that don't exercise step execution.

class NoopStep(AbstractStep):
    def _invoke(self, context):  # noqa: D401
        return None


_STEP_A = NoopStep(name="step-a")
_STEP_B = NoopStep(name="step-b")
_STEP_C = NoopStep(name="step-c")


# ── WorkflowRef ───────────────────────────────────────────────────────────────

def workflowRef_storesName():
    ref = WorkflowRef("spec_gen/generate-spec")
    assert ref.name == "spec_gen/generate-spec", (
        f"expected 'spec_gen/generate-spec', got {ref.name!r}"
    )


def workflowRef_strReturnsName():
    ref = WorkflowRef("spec_gen/generate-spec")
    assert str(ref) == "spec_gen/generate-spec", (
        f"__str__ returned {str(ref)!r}"
    )


def workflowRef_reprContainsName():
    ref = WorkflowRef("my/wf")
    assert "my/wf" in repr(ref), (
        f"__repr__ did not contain 'my/wf': {repr(ref)!r}"
    )


def workflowRef_isFrozen():
    ref = WorkflowRef("spec_gen/generate-spec")
    with pytest.raises((AttributeError, TypeError)):
        ref.name = "mutated"  # type: ignore[misc]


def workflowRef_equalByValue():
    assert WorkflowRef("a/b") == WorkflowRef("a/b"), (
        "Two WorkflowRefs with the same name must be equal"
    )


def workflowRef_differentNames_notEqual():
    assert WorkflowRef("a/b") != WorkflowRef("a/c"), (
        "WorkflowRefs with different names must not be equal"
    )


def workflowRef_hashableAndUsableInSet():
    refs = {WorkflowRef("a/b"), WorkflowRef("a/b"), WorkflowRef("c/d")}
    assert len(refs) == 2, (
        f"Expected 2 unique refs in set, got {len(refs)}"
    )


def workflowRef_emptyName_raisesValueError():
    with pytest.raises(ValueError):
        WorkflowRef("")


def workflowRef_blankName_raisesValueError():
    with pytest.raises(ValueError):
        WorkflowRef("   ")


# ── WorkflowBuilder — fluent API ──────────────────────────────────────────────

def builder_inputsReturnsSelf():
    b = Workflow.builder("a/wf")
    result = b.inputs("x")
    assert result is b, "inputs() must return the builder for chaining"


def builder_outputsReturnsSelf():
    b = Workflow.builder("a/wf")
    result = b.outputs("y")
    assert result is b, "outputs() must return the builder for chaining"


def builder_stepReturnsSelf():
    b = Workflow.builder("a/wf")
    result = b.step(_STEP_A)
    assert result is b, "step() must return the builder for chaining"


def builder_fullyChained_buildsSuccessfully():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf, Workflow), (
        f"build() must return a Workflow, got {type(wf)}"
    )


def builder_multipleInputs_allStored():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x", "y", "z")
        .outputs("out")
        .step(_STEP_A)
        .build()
    )
    assert wf.inputs == frozenset({"x", "y", "z"}), (
        f"expected inputs {{'x','y','z'}}, got {wf.inputs}"
    )


def builder_multipleOutputs_allStored():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("p", "q")
        .step(_STEP_A)
        .build()
    )
    assert wf.outputs == frozenset({"p", "q"}), (
        f"expected outputs {{'p','q'}}, got {wf.outputs}"
    )


def builder_multipleSteps_orderPreserved():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .step(_STEP_B)
        .step(_STEP_C)
        .build()
    )
    assert wf.steps == (_STEP_A, _STEP_B, _STEP_C), (
        f"Step order not preserved: {wf.steps}"
    )


def builder_stepCount_matchesStepsAdded():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .step(_STEP_B)
        .build()
    )
    assert wf.step_count == 2, (
        f"expected step_count=2, got {wf.step_count}"
    )


# ── WorkflowBuilder — validation ──────────────────────────────────────────────

def builder_noSteps_buildRaisesValueError():
    with pytest.raises(ValueError, match="step"):
        Workflow.builder("a/wf").inputs("x").outputs("y").build()


def builder_noInputs_buildRaisesValueError():
    with pytest.raises(ValueError, match="input"):
        Workflow.builder("a/wf").outputs("y").step(_STEP_A).build()


def builder_noOutputs_buildRaisesValueError():
    with pytest.raises(ValueError, match="output"):
        Workflow.builder("a/wf").inputs("x").step(_STEP_A).build()


def builder_allInvariantsUnmet_errorMessageListsAll():
    with pytest.raises(ValueError) as exc:
        Workflow.builder("a/wf").build()
    msg = str(exc.value)
    assert "input" in msg, f"error message missing 'input': {msg}"
    assert "output" in msg, f"error message missing 'output': {msg}"
    assert "step" in msg, f"error message missing 'step': {msg}"


def builder_emptyName_raisesValueError():
    with pytest.raises(ValueError):
        Workflow.builder("")


def builder_blankName_raisesValueError():
    with pytest.raises(ValueError):
        Workflow.builder("   ")


# ── Workflow aggregate ────────────────────────────────────────────────────────

def workflow_refMatchesBuilderName():
    wf = (
        Workflow.builder("spec_gen/generate-spec")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    assert wf.ref == WorkflowRef("spec_gen/generate-spec"), (
        f"ref mismatch: {wf.ref!r}"
    )


def workflow_isFrozen_refMutationRaises():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    with pytest.raises((AttributeError, TypeError)):
        wf.ref = WorkflowRef("other")  # type: ignore[misc]


def workflow_stepsIsTuple():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf.steps, tuple), (
        f"steps must be a tuple for immutability; got {type(wf.steps)}"
    )


def workflow_inputsIsFrozenset():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x", "y")
        .outputs("z")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf.inputs, frozenset), (
        f"inputs must be a frozenset; got {type(wf.inputs)}"
    )


def workflow_outputsIsFrozenset():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("z", "w")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf.outputs, frozenset), (
        f"outputs must be a frozenset; got {type(wf.outputs)}"
    )


# ── to_builder / variations ───────────────────────────────────────────────────

def toBuilder_producesEquivalentWorkflow():
    original = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    copy = original.to_builder().build()
    assert copy.ref == original.ref, f"ref mismatch: {copy.ref!r}"
    assert copy.inputs == original.inputs, f"inputs mismatch: {copy.inputs}"
    assert copy.outputs == original.outputs, f"outputs mismatch: {copy.outputs}"
    assert copy.steps == original.steps, f"steps mismatch: {copy.steps}"


def toBuilder_addingStep_doesNotMutateOriginal():
    original = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    variant = original.to_builder().step(_STEP_B).build()
    assert original.step_count == 1, (
        f"original.step_count mutated: expected 1, got {original.step_count}"
    )
    assert variant.step_count == 2, (
        f"variant.step_count wrong: expected 2, got {variant.step_count}"
    )


def toBuilder_addingInput_doesNotMutateOriginal():
    original = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    variant = original.to_builder().inputs("extra").build()
    assert "extra" not in original.inputs, (
        f"original.inputs was mutated: {original.inputs}"
    )
    assert "extra" in variant.inputs, (
        f"'extra' missing from variant.inputs: {variant.inputs}"
    )
    assert "x" in variant.inputs, (
        f"original input 'x' missing from variant.inputs: {variant.inputs}"
    )


# ── Structural ────────────────────────────────────────────────────────────────

def workflowModule_exportsWorkflowAndWorkflowRef():
    import modules.runtime.workflows as wf_mod
    assert hasattr(wf_mod, "Workflow"), (
        "modules.runtime.workflows must export Workflow"
    )
    assert hasattr(wf_mod, "WorkflowRef"), (
        "modules.runtime.workflows must export WorkflowRef"
    )
    assert wf_mod.Workflow is Workflow
    assert wf_mod.WorkflowRef is WorkflowRef


def workflowModule_allListsExactly():
    """__all__ must contain at least the Layer C surface; additional Layer B/D
    exports are permitted as those layers ship (Tasks 1.x and 3)."""
    import modules.runtime.workflows as wf_mod
    layer_c = {"Workflow", "WorkflowRef"}
    assert layer_c.issubset(set(wf_mod.__all__)), (
        f"__all__ must include Workflow and WorkflowRef; got {wf_mod.__all__}"
    )
