import os
from pathlib import Path

# Primary: SPEC_DOC_DIR env var (loaded from .env by create_app.py at startup).
# Fallback: parent of flask/ — works when the repo checkout contains the workspace.
_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR: Path = Path(os.environ.get("SPEC_DOC_DIR") or _DEFAULT_BASE_DIR)

PROJECTS_DIR: Path = BASE_DIR / "projects"

# Static map: context type → filesystem path.
# Architecture decision: static map, no dynamic routing.
CONTEXT_PATHS: dict[str, Path] = {
    "builder":    BASE_DIR / "builder.md",
    "principles": BASE_DIR / "principles.md",
    "codebase":   BASE_DIR / "codebase.md",
    "references": BASE_DIR / "references.md",
    # Self-defensive context blocks — read_context returns "" when the file is
    # absent and PromptBuilder.section() skips empty content, so adding new keys
    # is backward-compatible: deployments without these files behave exactly as
    # before.
    "quality":    BASE_DIR / "quality.md",     # rendered linter + coherence rule list
    "versions":   BASE_DIR / "versions.md",    # deployment fact sheet (model, deps)
}

# Legacy string-keyed alias (for callers still using os.path-style strings).
CONTEXT_FILES: dict[str, str] = {k: str(v) for k, v in CONTEXT_PATHS.items()}
