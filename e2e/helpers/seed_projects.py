"""Seed data helpers for E2E overview page tests.

Provisions eight projects across the four overview sections (Active, Ready to
Build, Specced, Braindumps) so every scenario starts from a deterministic,
known state without real AI calls.

Section classification is done on the Angular frontend by sectionFor() in
section-taxonomy.service.ts based solely on which .md files are present:
  - Active       — has an active background bootstrap job
  - Specced      — has implementation-guide.md
  - Ready to Build — has epic.md or architecture.md (but no implementation-guide.md)
  - Braindumps   — only braindump.md (or empty)

Projects are written directly to the filesystem so no API auth is required for
the bulk of seeding. The active project is provisioned via the bootstrap API
(POST /api/ai/text/bootstrap-project) using SKIP_AUTH=1 mode.

All project directories are named with a "e2e-seed-" prefix and a timestamp so
they are easy to identify and clean up without affecting real project data.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

import requests


# ---------------------------------------------------------------------------
# Section-to-file mapping
# ---------------------------------------------------------------------------

# Files that determine section membership (mirrors sectionFor() in Angular).
_SECTION_FILES: dict[str, list[tuple[str, str]]] = {
    "Specced": [
        ("braindump.md", "# Braindump\n\nThis project has been fully specced out.\n"),
        ("epic.md", "# Epic\n\nFull feature epic for specced project.\n"),
        ("architecture.md", "# Architecture\n\nSystem design for specced project.\n"),
        ("implementation-guide.md", "# Implementation Guide\n\nDetailed implementation tasks.\n"),
    ],
    "Ready to build": [
        ("braindump.md", "# Braindump\n\nThis project is ready to build.\n"),
        ("epic.md", "# Epic\n\nFeature epic for ready-to-build project.\n"),
        ("architecture.md", "# Architecture\n\nSystem design for ready-to-build project.\n"),
    ],
    "Braindumps": [
        ("braindump.md", "# Braindump\n\nRaw idea dump for this project.\n"),
    ],
}

# Matrix: section → list of project names to create.
_PROJECT_MATRIX: list[tuple[str, str]] = [
    # 3 Specced projects
    ("Specced", "E2E Seed Alpha"),
    ("Specced", "E2E Seed Beta"),
    ("Specced", "E2E Seed Gamma"),
    # 2 Ready to Build projects
    ("Ready to build", "E2E Seed Delta"),
    ("Ready to build", "E2E Seed Epsilon"),
    # 2 Braindumps projects
    ("Braindumps", "E2E Seed Zeta"),
    ("Braindumps", "E2E Seed Eta"),
    # 1 Active project (handled separately via bootstrap API)
    ("Active", "E2E Seed Active"),
]


class ProjectInfo(TypedDict):
    id: str
    name: str
    section: str
    created_at: str


class SeedMatrix(TypedDict):
    projects: list[ProjectInfo]
    by_section: dict[str, list[ProjectInfo]]
    active_job_id: str | None


def _resolve_projects_dir() -> Path:
    """Resolve the projects directory from SPEC_DOC_DIR env var or fallback."""
    spec_doc_dir = os.environ.get("SPEC_DOC_DIR")
    if spec_doc_dir:
        return Path(spec_doc_dir) / "projects"
    # Fallback: relative to repo root (api/ parent is the repo root)
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "data" / "projects"


def _make_slug(name: str) -> str:
    """Generate a filesystem-safe slug with millisecond timestamp suffix."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    timestamp = int(time.time() * 1000)
    return f"{slug}-{timestamp}"


def _write_project(
    projects_dir: Path,
    name: str,
    files: list[tuple[str, str]],
) -> ProjectInfo:
    """Write a project directory with project.json and the given .md files.

    Returns a ProjectInfo dict with the project id, name, section, and creation
    timestamp.
    """
    project_id = _make_slug(name)
    project_path = projects_dir / project_id
    project_path.mkdir(parents=True, exist_ok=True)

    created_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    meta = {"name": name, "createdAt": created_at}
    (project_path / "project.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    for filename, content in files:
        (project_path / filename).write_text(content, encoding="utf-8")

    return ProjectInfo(id=project_id, name=name, section="", created_at=created_at)


def _provision_active_project(
    api_base_url: str,
    projects_dir: Path,
    name: str,
) -> tuple[ProjectInfo | None, str | None]:
    """Provision the Active project via the bootstrap API.

    With CHAIN_PROVIDER=mock and SKIP_AUTH=1, the POST /api/ai/text/bootstrap-project
    endpoint starts a background thread that completes quickly. The 202 response
    returns a job_id that is immediately registered in _BOOTSTRAP_JOBS — so at the
    moment the seed step runs, the job is "running" from the Angular frontend's
    perspective (it polls GET /bootstrap-project/status/{job_id}).

    Returns (ProjectInfo, job_id) on success, or (None, None) on failure.
    """
    try:
        resp = requests.post(
            f"{api_base_url}/api/ai/text/bootstrap-project",
            json={
                "project_name": name,
                "braindump": "This is an actively generating E2E seed project.",
            },
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )
    except requests.RequestException:
        # Server not available — skip active project seeding gracefully.
        return None, None

    if resp.status_code != 202:
        return None, None

    data = resp.json()
    job_id = data.get("job_id")
    if not job_id:
        return None, None

    # The bootstrap API creates the project directory under PROJECTS_DIR/{job_id}.
    # Construct the ProjectInfo from the known job_id.
    created_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    info = ProjectInfo(
        id=job_id,
        name=name,
        section="Active",
        created_at=created_at,
    )
    return info, job_id


def seed_project_matrix(
    api_base_url: str,
    projects_dir: Path | None = None,
) -> SeedMatrix:
    """Provision the eight-project seed matrix.

    Creates projects by writing directly to the filesystem for Braindumps, Ready
    to Build, and Specced sections (no API auth needed). The Active project is
    provisioned via the bootstrap API so a real job entry exists in the server's
    in-process registry.

    Args:
        api_base_url: Base URL of the running Flask server (e.g. "http://127.0.0.1:5001").
        projects_dir:  Override the projects directory (for testing this module).
                       Defaults to the directory resolved from SPEC_DOC_DIR env var.

    Returns:
        A SeedMatrix dict with all created projects keyed by section.
    """
    if projects_dir is None:
        projects_dir = _resolve_projects_dir()

    projects_dir.mkdir(parents=True, exist_ok=True)

    all_projects: list[ProjectInfo] = []
    active_job_id: str | None = None

    for section, name in _PROJECT_MATRIX:
        if section == "Active":
            info, job_id = _provision_active_project(api_base_url, projects_dir, name)
            if info is not None:
                info["section"] = "Active"
                all_projects.append(info)
                active_job_id = job_id
        else:
            files = _SECTION_FILES[section]
            info = _write_project(projects_dir, name, files)
            info["section"] = section
            all_projects.append(info)

    by_section: dict[str, list[ProjectInfo]] = {}
    for p in all_projects:
        by_section.setdefault(p["section"], []).append(p)

    return SeedMatrix(
        projects=all_projects,
        by_section=by_section,
        active_job_id=active_job_id,
    )


def teardown_seed_matrix(
    seed_matrix: SeedMatrix,
    projects_dir: Path | None = None,
) -> None:
    """Remove all seeded project directories created by seed_project_matrix.

    Deletes project directories directly from the filesystem so no API auth is
    needed for cleanup. This is safe because all seeded projects use the "e2e-seed-"
    name prefix, and teardown only touches directories listed in the seed_matrix.

    Args:
        seed_matrix:  The SeedMatrix returned by seed_project_matrix.
        projects_dir: Override the projects directory. Defaults to SPEC_DOC_DIR-based path.
    """
    if projects_dir is None:
        projects_dir = _resolve_projects_dir()

    for project in seed_matrix["projects"]:
        project_path = projects_dir / project["id"]
        if project_path.exists() and project_path.is_dir():
            shutil.rmtree(project_path, ignore_errors=True)
