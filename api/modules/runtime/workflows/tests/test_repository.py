"""Tests for WorkflowRepository port and WorkflowRepositoryFs adapter.

Uses the real Workflow aggregate (Tasks 1–3) for save/get/list paths.
The dynamic from_modules_dir tests write self-contained .py fixture files
that declare their own minimal classes, so those files do not depend on
the Workflow aggregate at import time.
"""
import pytest
from pathlib import Path

from modules.runtime.workflows.repository import WorkflowNotFound, WorkflowRepository
from modules.runtime.workflows.repository.fs_adapter import WorkflowRepositoryFs, _PrefixedRepo
from modules.runtime.workflows.steps import AbstractStep, StepContext
from modules.runtime.workflows.workflow import Workflow


# ── Helpers ───────────────────────────────────────────────────────────────────
# Note: pytest's python_functions glob (`*_*`) will treat any module-level or
# class-level function whose name contains an underscore as a test candidate.
# Helpers below use camelCase to stay out of that net.

class NoopStep(AbstractStep):
    """Minimal concrete AbstractStep used to satisfy WorkflowBuilder.build()."""

    def _invoke(self, context: StepContext):  # pragma: no cover - never executed
        return None


def makeWorkflow(name: str) -> Workflow:
    """Build a minimal valid Workflow under the given name (plain, unqualified)."""
    return (
        Workflow.builder(name)
        .inputs("x")
        .outputs("y")
        .step(NoopStep(name="s1"))
        .build()
    )


# ── Local fixtures ───────────────────────────────────────────────────────────
# tests/conftest.py only auto-applies inside tests/. Mirror its `app` fixture
# here so test_createApp_attaches_workflowRepository can use it.

@pytest.fixture()
def app(tmp_path, monkeypatch):
    """Create a fresh Flask app under per-test SPEC_DOC_DIR isolation."""
    monkeypatch.setenv("SPEC_DOC_DIR", str(tmp_path))
    from create_app import create_app
    return create_app({"TESTING": True})


# ── WorkflowNotFound ──────────────────────────────────────────────────────────

class TestWorkflowNotFound:
    def test_carries_name_attribute(self):
        exc = WorkflowNotFound("spec_gen/generate-spec")
        assert exc.name == "spec_gen/generate-spec", (
            "WorkflowNotFound.name must equal the argument passed to __init__"
        )

    def test_message_includes_name(self):
        exc = WorkflowNotFound("spec_gen/generate-spec")
        assert "spec_gen/generate-spec" in str(exc), (
            "WorkflowNotFound.__str__ must contain the missing workflow name"
        )


# ── Port is abstract ──────────────────────────────────────────────────────────

class TestWorkflowRepository_isAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            WorkflowRepository()  # type: ignore[abstract]


# ── WorkflowRepositoryFs.save ─────────────────────────────────────────────────

class TestWorkflowRepositoryFs_save:
    def test_storePersists_underWorkflowName(self):
        repo = WorkflowRepositoryFs()
        wf = makeWorkflow("alpha")
        repo.save(wf)
        assert repo.get("alpha") is wf, (
            "save() must make the workflow retrievable by its name"
        )

    def test_secondSave_overwritesFirst(self):
        repo = WorkflowRepositoryFs()
        wf1 = makeWorkflow("alpha")
        wf2 = makeWorkflow("alpha")
        repo.save(wf1)
        repo.save(wf2)
        assert repo.get("alpha") is wf2, (
            "second save() with the same name must overwrite the first"
        )


# ── WorkflowRepositoryFs.get ──────────────────────────────────────────────────

class TestWorkflowRepositoryFs_get:
    def test_knownName_returnsSavedInstance(self):
        repo = WorkflowRepositoryFs()
        wf = makeWorkflow("bravo")
        repo.save(wf)
        result = repo.get("bravo")
        assert result is wf, "get() must return the exact instance passed to save()"

    def test_unknownName_raisesWorkflowNotFound(self):
        repo = WorkflowRepositoryFs()
        with pytest.raises(WorkflowNotFound) as exc_info:
            repo.get("does-not-exist")
        assert exc_info.value.name == "does-not-exist", (
            "WorkflowNotFound raised by get() must carry the missing name"
        )


# ── WorkflowRepositoryFs.list ─────────────────────────────────────────────────

class TestWorkflowRepositoryFs_list:
    def test_empty_whenNothingSaved(self):
        repo = WorkflowRepositoryFs()
        assert repo.list() == [], "list() on an empty repo must return []"

    def test_returnsSorted_afterMultipleSaves(self):
        repo = WorkflowRepositoryFs()
        for name in ["gamma", "alpha", "beta"]:
            repo.save(makeWorkflow(name))
        assert repo.list() == ["alpha", "beta", "gamma"], (
            "list() must return workflow names in ascending lexicographic order"
        )

    def test_returnsCopy_mutationDoesNotAffectStore(self):
        repo = WorkflowRepositoryFs()
        repo.save(makeWorkflow("x"))
        names = repo.list()
        names.append("injected")
        assert "injected" not in repo.list(), (
            "list() must return a copy; mutating the returned list must not "
            "alter the repository's internal state"
        )


# ── WorkflowRepositoryFs.from_modules_dir ────────────────────────────────────

class TestWorkflowRepositoryFs_fromModulesDir:
    """Each test uses tmp_path so no real modules/ directory is touched.

    Fixture .py files declare their own minimal class so they remain
    independent of the Workflow aggregate at import time. The adapter's
    _workflow_name() helper falls back to obj.name when obj.ref is absent.
    """

    def writeFeatureWorkflow(self, tmp_path: Path, feature: str, py_name: str, wf_name: str) -> None:
        """Helper: write a minimal workflow definition file under tmp_path/<feature>/workflows/."""
        d = tmp_path / feature / "workflows"
        d.mkdir(parents=True, exist_ok=True)
        (d / py_name).write_text(
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class _W:\n"
            "    name: str\n"
            "def register_workflows(repo):\n"
            f"    repo.save(_W(name={wf_name!r}))\n",
            encoding="utf-8",
        )

    def test_registersWorkflow_fromPythonFile(self, tmp_path: Path):
        self.writeFeatureWorkflow(tmp_path, "my_feature", "gen.py", "generate-spec")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        result = repo.get("my_feature/generate-spec")
        assert result.name == "generate-spec", (
            "from_modules_dir must load the workflow defined in the .py file"
        )

    def test_qualifiesName_withFeaturePrefix(self, tmp_path: Path):
        self.writeFeatureWorkflow(tmp_path, "feat_x", "w.py", "my-wf")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert "feat_x/my-wf" in repo.list(), (
            "from_modules_dir must register workflows under 'feature/workflow-name'"
        )

    def test_skipsDunderFiles(self, tmp_path: Path):
        d = tmp_path / "feat" / "workflows"
        d.mkdir(parents=True)
        (d / "__init__.py").write_text(
            "def register_workflows(repo):\n"
            "    raise RuntimeError('dunder file must not be loaded')\n",
            encoding="utf-8",
        )
        # Must not raise; dunder file must be silently skipped
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert repo.list() == [], "files beginning with '_' must be skipped"

    def test_noop_whenNoWorkflowsDir(self, tmp_path: Path):
        (tmp_path / "no_workflows_here").mkdir()
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert repo.list() == [], (
            "a feature module without a workflows/ directory must be silently skipped"
        )

    def test_noop_whenNoRegisterFunction(self, tmp_path: Path):
        d = tmp_path / "feat" / "workflows"
        d.mkdir(parents=True)
        (d / "constants.py").write_text("ANSWER = 42\n", encoding="utf-8")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert repo.list() == [], (
            "a workflow file without register_workflows() must be silently skipped"
        )

    def test_registersWorkflows_acrossMultipleFeatures(self, tmp_path: Path):
        self.writeFeatureWorkflow(tmp_path, "feat_a", "w.py", "wf-a")
        self.writeFeatureWorkflow(tmp_path, "feat_b", "w.py", "wf-b")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert "feat_a/wf-a" in repo.list(), "feat_a workflow must be registered"
        assert "feat_b/wf-b" in repo.list(), "feat_b workflow must be registered"
        assert len(repo.list()) == 2, "only the two registered workflows must be present"


# ── _PrefixedRepo ─────────────────────────────────────────────────────────────

class TestPrefixedRepo:
    def test_save_addsFeaturePrefix(self):
        base = WorkflowRepositoryFs()
        prefixed = _PrefixedRepo(base, "my_feature")
        wf = makeWorkflow("wf-1")
        prefixed.save(wf)
        # The base store must hold the qualified name
        retrieved = base.get("my_feature/wf-1")
        assert retrieved is wf, (
            "_PrefixedRepo.save() must store under 'feature/workflow.name' "
            "in the delegate repository"
        )

    def test_get_resolvesWithFeaturePrefix(self):
        base = WorkflowRepositoryFs()
        prefixed = _PrefixedRepo(base, "my_feature")
        wf = makeWorkflow("wf-1")
        prefixed.save(wf)
        result = prefixed.get("wf-1")
        assert result is wf, (
            "_PrefixedRepo.get('wf-1') must resolve to 'my_feature/wf-1' "
            "in the delegate and return the correct instance"
        )

    def test_list_stripsFeaturePrefix(self):
        base = WorkflowRepositoryFs()
        prefixed = _PrefixedRepo(base, "feat")
        prefixed.save(makeWorkflow("alpha"))
        prefixed.save(makeWorkflow("beta"))
        names = prefixed.list()
        assert names == ["alpha", "beta"], (
            "_PrefixedRepo.list() must return plain names without the feature prefix, "
            "sorted ascending; got: " + repr(names)
        )


# ── App factory wiring ────────────────────────────────────────────────────────

def test_createApp_attaches_workflowRepository(app):
    """create_app() must attach a WorkflowRepository instance to app.workflow_repository."""
    from modules.runtime.workflows.repository import WorkflowRepository
    assert hasattr(app, "workflow_repository"), (
        "app must have a workflow_repository attribute after create_app()"
    )
    assert isinstance(app.workflow_repository, WorkflowRepository), (
        "app.workflow_repository must be a WorkflowRepository instance; "
        f"got {type(app.workflow_repository)}"
    )
