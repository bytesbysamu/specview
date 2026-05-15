"""Project CRUD service — pure filesystem helpers.

Ported from server.js lines 469–612. No Flask imports.
All functions accept projects_dir: Path for test isolation.
"""
from __future__ import annotations

from typing import Optional
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from modules.data.templates.generators import (
    generate_readme,
    generate_spec_index,
    generate_timeline,
)


# ---------------------------------------------------------------------------
# Helpers — ported verbatim from server.js logic
# ---------------------------------------------------------------------------

def _filename_to_label(filename: str) -> str:
    """Port of server.js:484 label derivation.

    JS: f.replace('.md', '').replace(/-/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase())
    """
    return filename.replace(".md", "").replace("-", " ").title()


def _make_id(name: str) -> str:
    """Port of server.js:546–550 slug+timestamp ID.

    JS: slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
        id   = `${slug}-${Date.now()}`
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    timestamp = int(time.time() * 1000)  # milliseconds, matches Date.now()
    return f"{slug}-{timestamp}"


def _safe_path(projects_dir: Path, project_id: str) -> Path:
    """Resolve project path and reject traversal attempts.

    Express omits this check; Flask adds it as a security boundary.
    Raises ValueError if resolved path escapes projects_dir.
    """
    resolved = (projects_dir / project_id).resolve()
    if not str(resolved).startswith(str(projects_dir.resolve())):
        raise ValueError(f"Path traversal attempt: {project_id!r}")
    return resolved


def _read_specs(project_path: Path, *, include_content: bool, teaser_chars: int = 0) -> list[dict]:
    """Read .md files from a project directory and build specs list."""
    specs = []
    for f in sorted(project_path.glob("*.md")):
        spec: dict = {
            "filename": f.name,
            "label": _filename_to_label(f.name),
        }
        if include_content or teaser_chars > 0:
            content = f.read_text(encoding="utf-8")
            if include_content:
                spec["content"] = content
            if teaser_chars > 0 and not include_content:
                spec["teaser"] = content[:teaser_chars]
        specs.append(spec)
    return specs


# ---------------------------------------------------------------------------
# Public API — one function per route
# ---------------------------------------------------------------------------

def list_projects(projects_dir: Path) -> list[dict]:
    """GET /api/projects — port of server.js:469–503."""
    if not projects_dir.exists():
        return []
    results = []
    for d in projects_dir.iterdir():
        meta_path = d / "project.json"
        if not d.is_dir() or not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue  # skip corrupt/unreadable entries gracefully
        if meta.get("archived"):
            continue
        results.append({
            "id": d.name,
            "name": meta["name"],
            "createdAt": meta.get("createdAt", ""),
            "section": meta.get("section", ""),
            "priority": meta.get("priority", 99),
            "specs": _read_specs(d, include_content=False, teaser_chars=500),
        })
    # Sort by priority asc (1=highest), then newest first within same priority
    results.sort(key=lambda p: (p["priority"], p["createdAt"]))
    return results


def get_project(projects_dir: Path, project_id: str) -> Optional[dict]:
    """GET /api/projects/:id — port of server.js:506–534.

    Returns None if project not found (caller returns 404).
    """
    project_path = _safe_path(projects_dir, project_id)
    meta_path = project_path / "project.json"
    if not project_path.exists() or not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "id": project_id,
        "name": meta["name"],
        "createdAt": meta.get("createdAt", ""),
        "specs": _read_specs(project_path, include_content=True),
    }


def create_project(projects_dir: Path, name: str, files: list[dict]) -> dict:
    """POST /api/projects — port of server.js:537–578.

    files: [{"filename": str, "content": str}]
    Returns: {"id": str, "name": str, "createdAt": str}
    """
    project_id = _make_id(name)
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

    for f in files:
        (project_path / f["filename"]).write_text(f["content"], encoding="utf-8")

    return {"id": project_id, "name": name, "createdAt": created_at}


def update_file(projects_dir: Path, project_id: str, filename: str, content: str) -> bool:
    """PUT /api/projects/:id/files/:filename — port of server.js:581–596.

    Returns False if project directory not found (caller returns 404).
    """
    project_path = _safe_path(projects_dir, project_id)
    if not project_path.exists():
        return False
    (project_path / filename).write_text(content, encoding="utf-8")
    return True


def delete_project(projects_dir: Path, project_id: str) -> bool:
    """DELETE /api/projects/:id — port of server.js:599–613.

    Returns False if not found (caller returns 404).
    """
    project_path = _safe_path(projects_dir, project_id)
    if not project_path.exists():
        return False
    shutil.rmtree(project_path)
    return True


# Target filenames the repair endpoint is responsible for.
_REPAIR_TARGETS: list[str] = ["spec-index.md", "timeline.md", "README.md"]


def repair_project(projects_dir: Path, project_id: str) -> Optional[list[str]]:
    """POST /api/projects/:id/repair — idempotent deterministic file repair.

    Writes spec-index.md, timeline.md, and README.md if absent.
    Returns the list of filenames written (empty list if all already present),
    or None if the project directory or project.json does not exist.

    Idempotency: runs twice on the same project produce the same filesystem
    state. Files present on the first run are not overwritten on the second.
    """
    project_path = _safe_path(projects_dir, project_id)
    meta_path = project_path / "project.json"
    if not project_path.exists() or not meta_path.exists():
        return None

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    project_name = meta["name"]

    generators: dict[str, object] = {
        "spec-index.md": lambda: generate_spec_index(project_name),
        "timeline.md": lambda: generate_timeline(project_name, []),
        "README.md": lambda: generate_readme(project_name),
    }

    repaired: list[str] = []
    for filename in _REPAIR_TARGETS:
        if not (project_path / filename).exists():
            content = generators[filename]()
            (project_path / filename).write_text(content, encoding="utf-8")
            repaired.append(filename)

    return repaired
