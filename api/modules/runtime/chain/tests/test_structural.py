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


def test_project_slug_routes_have_ownership_decorator():
    """Every route handler that accepts a slug path parameter must be wrapped
    with @require_project_ownership.

    The assertion works by parsing routes.py with the ast module and
    inspecting the decorator list of each function definition.  The listing
    route (list_projects_route) and the create route (create_project_route)
    accept no slug parameter and are explicitly excluded.  The internal
    helper _resolve_project also accepts project_id but is not a route
    handler and is excluded by the leading underscore convention.

    This test catches the case where a new slug-accepting route is added
    without the ownership decorator being applied — a class of bug that
    code review may miss.
    """
    import ast

    api_root = pathlib.Path(__file__).resolve().parents[4]  # api/
    routes_path = api_root / "modules" / "data" / "projects" / "routes.py"
    source = routes_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Route handlers that intentionally do NOT use @require_project_ownership
    # because they do not accept a per-project slug parameter:
    #   list_projects_route — lists all projects for the current user
    #   create_project_route — creates a new project (no slug yet)
    # Routes that intentionally skip ownership because ownership has not been
    # established yet:
    #   claim_project_route — transfers an anonymous project to the caller;
    #                         the project has no owner at call time so the
    #                         ownership check would always 403.
    # Internal helpers (leading underscore) are also excluded.
    excluded = {"list_projects_route", "create_project_route", "claim_project_route"}

    slug_param_names = {"id", "project_id"}

    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = node.name
        # Skip internal helpers (not route handlers).
        if name.startswith("_"):
            continue
        # Skip routes that legitimately omit the decorator.
        if name in excluded:
            continue
        # Only care about route handlers that accept a slug parameter.
        arg_names = {a.arg for a in node.args.args}
        if not arg_names & slug_param_names:
            continue

        # Collect the names of all decorators applied to this function.
        decorator_names: set[str] = set()
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorator_names.add(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorator_names.add(dec.attr)
            elif isinstance(dec, ast.Call):
                func = dec.func
                if isinstance(func, ast.Name):
                    decorator_names.add(func.id)
                elif isinstance(func, ast.Attribute):
                    decorator_names.add(func.attr)

        if "require_project_ownership" not in decorator_names:
            missing.append(name)

    assert missing == [], (
        "The following slug-accepting route handlers are missing "
        "@require_project_ownership: "
        f"{missing}. "
        "Add the decorator immediately after @require_auth on each handler."
    )
