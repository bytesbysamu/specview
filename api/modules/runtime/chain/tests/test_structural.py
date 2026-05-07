"""Adapter-boundary structural test — ported verbatim from references.md:624–643.

INVARIANT: No file outside adapter.py, providers/, or tests/ may import providers directly.
This test greps the chain module tree and fails on any violation.
"""
import pathlib
from modules.runtime.chain import adapter as _adapter


def test_feature_modules_must_not_import_providers_directly():
    """Greps the chain module tree for direct provider imports.

    Any file outside adapter.py / providers/ / tests/ that imports from
    providers fails. Catches coupling that code review can miss.
    """
    infra_dir = pathlib.Path(_adapter.__file__).parent
    offenders = []
    for py in infra_dir.rglob("*.py"):
        rel = py.relative_to(infra_dir)
        # Skip: adapter.py (allowed), providers/ tree (allowed), tests/ tree (allowed)
        if rel.parts[0] in ("providers", "tests") or rel.name == "adapter.py":
            continue
        text = py.read_text()
        if "from .providers" in text or "from modules.runtime.chain.providers" in text:
            offenders.append(str(rel))
    assert offenders == [], (
        f"Adapter-boundary violation: {offenders}. "
        "Only adapter.py may import providers."
    )


def test_prompts_directory_does_not_exist():
    """Asserts that the legacy modules/ai/prompts/ directory has been fully deleted.

    This directory was removed as part of the Thin API Layer refactor. Any
    re-introduction of it would bypass the workflow-based prompt system.
    """
    api_root = pathlib.Path(__file__).resolve().parents[4]  # api/
    prompts_dir = api_root / "modules" / "ai" / "prompts"
    assert not prompts_dir.exists(), (
        f"Legacy prompts directory must not exist: {prompts_dir}. "
        "Prompts now live inside workflow step definitions."
    )


def test_feature_modules_must_not_branch_on_chain_provider():
    """ELA #1 - provider selection lives in adapter.py and nowhere else."""
    api_root = pathlib.Path(__file__).resolve().parents[4]  # api/
    feature_dirs = [api_root / "modules" / "ai", api_root / "modules" / "data"]
    offenders = []
    for root in feature_dirs:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if "/tests/" in str(py).replace("\\", "/"):
                continue
            text = py.read_text(encoding="utf-8")
            if "CHAIN_PROVIDER" in text:
                offenders.append(str(py.relative_to(api_root)))
    assert offenders == [], (
        "Feature modules must not reference CHAIN_PROVIDER directly; "
        f"violators: {offenders}"
    )
