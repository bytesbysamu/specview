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

When JWT_SECRET + E2E_USER_ID env vars are set (real server mode), projects are
provisioned via the POST /api/projects API so they are registered in the
database for the authenticated user. This is necessary because the real server's
GET /api/projects endpoint filters by user ID using the database.

When JWT_SECRET is not set (local dev / SKIP_AUTH=1 mode), projects are written
directly to the filesystem so no API auth is required.

The active project is always provisioned via the bootstrap API
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
    # Specced projects (includes named fixture required by OV-08 card-renders scenario)
    ("Specced", "E2E Seed Alpha"),
    ("Specced", "E2E Seed Beta"),
    ("Specced", "E2E Seed Gamma"),
    # "My Spec" is required by the OV-08 card-renders scenario which expects a
    # Specced project with exactly 4 spec files (braindump, epic, arch, impl-guide).
    ("Specced", "My Spec"),
    # 2 Ready to Build projects
    ("Ready to build", "E2E Seed Delta"),
    ("Ready to build", "E2E Seed Epsilon"),
    # 3 Braindumps projects (includes a named fixture for the search/card tests)
    ("Braindumps", "E2E Seed Zeta"),
    ("Braindumps", "E2E Seed Eta"),
    # "Alpha Project" is required by the case-insensitive search scenario (OV-07)
    # and the card-renders scenario (OV-08).  Use a Braindumps project so it
    # appears in the All view without needing mock generation.
    ("Braindumps", "Alpha Project"),
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


def _make_auth_token() -> str | None:
    """Create a signed JWT for API authentication using env vars.

    Returns None if JWT_SECRET is not set (local dev / SKIP_AUTH=1 mode).
    """
    jwt_secret = os.environ.get("JWT_SECRET")
    if not jwt_secret:
        return None
    try:
        import jwt as _jwt
        user_id = os.environ.get("E2E_USER_ID", "1")
        email = os.environ.get("E2E_USER_EMAIL", "test@test.com")
        payload = {
            "sub": str(user_id),
            "email": email,
            "iat": int(time.time()),
            "exp": int(time.time()) + 72 * 3600,
        }
        return _jwt.encode(payload, jwt_secret, algorithm="HS256")
    except Exception:
        return None


def _provision_project_via_api(
    api_base_url: str,
    name: str,
    files: list[tuple[str, str]],
    auth_token: str,
) -> ProjectInfo | None:
    """Create a project via the POST /api/projects endpoint.

    This registers the project in the database for the authenticated user so
    that GET /api/projects returns it (real server mode with user-filtered DB).

    Then, writes the additional spec files directly to the filesystem (the
    create endpoint only accepts braindump content, not arbitrary files).

    Returns a ProjectInfo on success, or None on failure.
    """
    # The create endpoint requires at least one file.
    file_dtos = [{"filename": fn, "content": content} for fn, content in files]
    try:
        resp = requests.post(
            f"{api_base_url}/api/projects",
            json={"name": name, "files": file_dtos},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10,
        )
    except requests.RequestException:
        return None

    if resp.status_code not in (200, 201):
        return None

    data = resp.json()
    project_id = data.get("id")
    if not project_id:
        return None

    created_at = data.get("createdAt", "")
    return ProjectInfo(id=project_id, name=name, section="", created_at=created_at)


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

    When JWT_SECRET is set (real server mode), uses a real JWT for auth.
    When SKIP_AUTH=1 is active (local dev mode), uses "Bearer test-token".

    Returns (ProjectInfo, job_id) on success, or (None, None) on failure.
    """
    auth_token = _make_auth_token()
    auth_header = f"Bearer {auth_token}" if auth_token else "Bearer test-token"
    try:
        resp = requests.post(
            f"{api_base_url}/api/ai/text/bootstrap-project",
            json={
                "project_name": name,
                "braindump": "This is an actively generating E2E seed project.",
            },
            headers={"Authorization": auth_header},
            timeout=10,
        )
    except requests.RequestException:
        # Server not available — skip active project seeding gracefully.
        return None, None

    if resp.status_code not in (200, 202):
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
    skip_active_project: bool = False,
) -> SeedMatrix:
    """Provision the eight-project seed matrix.

    When JWT_SECRET + E2E_USER_ID are set (real server mode), projects are
    created via POST /api/projects so they are registered in the database for
    the authenticated user. This is necessary because GET /api/projects filters
    by user ID when a real database is connected.

    Without JWT_SECRET (local SKIP_AUTH=1 mode), projects are written directly
    to the filesystem so no API auth is required.

    The Active project is provisioned via the bootstrap API using the available
    auth token. On a real server with CLI provider, the job starts a real
    generation — but the job is immediately "running" from the Angular app's
    perspective, so it appears in the Active section during the test.

    Args:
        api_base_url:         Base URL of the running Flask server.
        projects_dir:         Override the projects directory (for testing this module).
                              Defaults to the directory resolved from SPEC_DOC_DIR env var.
        skip_active_project:  When True, skip the Active project seeding entirely.
                              Only used when E2E_BASE_URL is not set (legacy local mode).

    Returns:
        A SeedMatrix dict with all created projects keyed by section.
    """
    if projects_dir is None:
        projects_dir = _resolve_projects_dir()

    projects_dir.mkdir(parents=True, exist_ok=True)

    # Attempt to get an auth token for API-based provisioning.
    auth_token = _make_auth_token()

    all_projects: list[ProjectInfo] = []
    active_job_id: str | None = None

    for section, name in _PROJECT_MATRIX:
        if section == "Active":
            if skip_active_project:
                continue
            info, job_id = _provision_active_project(api_base_url, projects_dir, name)
            if info is not None:
                info["section"] = "Active"
                all_projects.append(info)
                active_job_id = job_id
        else:
            files = _SECTION_FILES[section]
            if auth_token:
                # Real server: provision via API so the DB record is created.
                info = _provision_project_via_api(api_base_url, name, files, auth_token)
                if info is None:
                    # Fall back to filesystem write on API failure.
                    info = _write_project(projects_dir, name, files)
            else:
                # Local dev / SKIP_AUTH=1: write directly to filesystem.
                info = _write_project(projects_dir, name, files)
            info["section"] = section
            all_projects.append(info)
        # Small delay to ensure unique millisecond timestamps for project IDs.
        time.sleep(0.002)

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
    api_base_url: str | None = None,
) -> None:
    """Remove all seeded project directories created by seed_project_matrix.

    When JWT_SECRET is set (real server mode), deletes projects via the API so
    the DB records are also removed. Falls back to filesystem deletion for any
    projects that the API cannot reach.

    Args:
        seed_matrix:  The SeedMatrix returned by seed_project_matrix.
        projects_dir: Override the projects directory. Defaults to SPEC_DOC_DIR-based path.
        api_base_url: Base URL for API-based deletion (optional).
    """
    if projects_dir is None:
        projects_dir = _resolve_projects_dir()

    auth_token = _make_auth_token()

    for project in seed_matrix["projects"]:
        project_id = project["id"]

        # Attempt API deletion first when token is available.
        if auth_token and api_base_url:
            try:
                requests.delete(
                    f"{api_base_url}/api/projects/{project_id}",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=5,
                )
            except requests.RequestException:
                pass  # Fall through to filesystem deletion

        # Always attempt filesystem deletion as a safety net.
        project_path = projects_dir / project_id
        if project_path.exists() and project_path.is_dir():
            shutil.rmtree(project_path, ignore_errors=True)
