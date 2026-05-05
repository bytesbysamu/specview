"""Domain exceptions for the projects module."""
from __future__ import annotations


class ProjectNotFoundError(Exception):
    """Raised when a project directory or project.json does not exist."""
